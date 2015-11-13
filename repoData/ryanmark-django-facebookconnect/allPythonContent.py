__FILENAME__ = admin
# Copyright 2008-2009 Brian Boyer, Ryan Mark, Angela Nitzke, Joshua Pollock,
# Stuart Tiffen, Kayla Webley and the Medill School of Journalism, Northwestern
# University.
#
# This file is part of django-facebookconnect.
#
# django-facebookconnect is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# django-facebookconnect is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
#You should have received a copy of the GNU General Public License
#along with django-facebookconnect.  If not, see <http://www.gnu.org/licenses/>.

from facebookconnect.models import FacebookProfile
from django.contrib import admin

admin.site.register(FacebookProfile)

########NEW FILE########
__FILENAME__ = forms
from django import forms
from django.utils.translation import ugettext as _
from django.contrib.auth.models import User

class FacebookUserCreationForm(forms.ModelForm):
    """
    A form that creates a user, with no privileges, from the given username and password.
    """
    username = forms.RegexField(label=_("Username"), max_length=30, regex=r'^\w+$',
        help_text = _("Required. 30 characters or fewer. Alphanumeric characters only (letters, digits and underscores)."),
        error_message = _("This value must contain only letters, numbers and underscores."))
    email = forms.EmailField(label=_("E-mail"), max_length=75,required=False)

    class Meta:
        model = User
        fields = ("username","email")

    def save(self, commit=True):
        user = super(FacebookUserCreationForm, self).save(commit=False)
        user.set_unusable_password()
        if commit:
            user.save()
        return user

########NEW FILE########
__FILENAME__ = fixemailfieldsize
# Copyright 2008-2009 Brian Boyer, Ryan Mark, Angela Nitzke, Joshua Pollock,
# Stuart Tiffen, Kayla Webley and the Medill School of Journalism, Northwestern
# University.
#
# This file is part of django-facebookconnect.
#
# django-facebookconnect is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# django-facebookconnect is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
#You should have received a copy of the GNU General Public License
#along with django-facebookconnect.  If not, see <http://www.gnu.org/licenses/>.

from django.conf import settings
from django.core.management import BaseCommand
from django.core.exceptions import ImproperlyConfigured

class Command(BaseCommand):
    def handle(self,*args,**options):
        """change the database schema to except big email addresses"""
        from django.db import connection, transaction
        cursor = connection.cursor()

        # Data modifying operation - commit required
        cursor.execute("ALTER TABLE `auth_user` CHANGE `email` `email` VARCHAR(255);")
        transaction.commit()
        
########NEW FILE########
__FILENAME__ = installfacebooktemplates
# Copyright 2008-2009 Brian Boyer, Ryan Mark, Angela Nitzke, Joshua Pollock,
# Stuart Tiffen, Kayla Webley and the Medill School of Journalism, Northwestern
# University.
#
# This file is part of django-facebookconnect.
#
# django-facebookconnect is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# django-facebookconnect is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
#You should have received a copy of the GNU General Public License
#along with django-facebookconnect.  If not, see <http://www.gnu.org/licenses/>.

from django.conf import settings
from django.core.management import BaseCommand
from django.core.exceptions import ImproperlyConfigured
from facebook import Facebook
from facebookconnect.models import FacebookTemplate

class Command(BaseCommand):
    def handle(self,*args,**options):
        """Load the templates into facebook (probably clear them out beforehand)"""
        facebook_obj = Facebook(settings.FACEBOOK_API_KEY, settings.FACEBOOK_SECRET_KEY)
        
        #blow up all templates
        current_templates = facebook_obj.feed.getRegisteredTemplateBundles()
        for t in current_templates:
            print "Deactivating old bundle #%i ..." % t['template_bundle_id']
            facebook_obj.feed.deactivateTemplateBundleByID(t['template_bundle_id'])
        
        #install templates from our facebook settings file
        for bundle in settings.FACEBOOK_TEMPLATES:
            name = bundle[0]
            one_line_template = bundle[1][0]
            short_template = bundle[1][1]
            full_template = bundle[1][2]
            action_template = bundle[1][3]
            response = facebook_obj.feed.registerTemplateBundle(one_line_template,short_template,full_template,action_template)
            try:
                template = FacebookTemplate.objects.get(name=name)
                #facebook_obj.feed.deactivateTemplateBundleByID(template.template_bundle_id)
                print "Replacing old '%s' bundle ..." % (name.capitalize())
            except FacebookTemplate.DoesNotExist:
                template = FacebookTemplate(name=name)
                print "Loading '%s' bundle ..." % (name.capitalize())
            template.template_bundle_id = response
            template.save()
        

########NEW FILE########
__FILENAME__ = middleware
# Copyright 2008-2009 Brian Boyer, Ryan Mark, Angela Nitzke, Joshua Pollock,
# Stuart Tiffen, Kayla Webley and the Medill School of Journalism, Northwestern
# University.
#
# This file is part of django-facebookconnect.
#
# django-facebookconnect is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# django-facebookconnect is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
#You should have received a copy of the GNU General Public License
#along with django-facebookconnect.  If not, see <http://www.gnu.org/licenses/>.

import logging
log = logging.getLogger('facebookconnect.middleware')
import warnings
from datetime import datetime
from django.core.urlresolvers import reverse
from django.contrib.auth import logout,login
from django.conf import settings
from facebook import Facebook,FacebookError
from django.template import TemplateSyntaxError
from django.http import HttpResponseRedirect,HttpResponse
from urllib2 import URLError
from facebookconnect.models import FacebookProfile

try:
    from threading import local
except ImportError:
    from django.utils._threading_local import local

_thread_locals = local()

class FacebookConnectMiddleware(object):
    """Middlware to provide a working facebook object"""
    def process_request(self,request):
        """process incoming request"""

        # clear out the storage of fb ids in the local thread
        if hasattr(_thread_locals,'fbids'):
            del _thread_locals.fbids

        try:
            # This is true if anyone has ever used the browser to log in to
            # facebook with an acount that has accepted this application.
            bona_fide = request.facebook.check_session(request)
            uid = request.facebook.uid
            if not request.path.startswith(settings.MEDIA_URL):
              log.debug("Bona Fide: %s, Logged in: %s" % (bona_fide, uid))

            if bona_fide and uid:
                user = request.user
                if user.is_anonymous():
                    # user should be in setup
                    setup_url = reverse('facebook_setup')
                    if request.path != setup_url:
                        request.facebook.session_key = None
                        request.facebook.uid = None
            else:
                # we have no fb info, so we shouldn't have a fb only
                # user logged in
                user = request.user
                if user.is_authenticated() and bona_fide:
                    try:
                        fbp = FacebookProfile.objects.get(user=user)

                        if fbp.facebook_only():
                            cur_user = request.facebook.users.getLoggedInUser()
                            if int(cur_user) != int(request.facebook.uid):
                                logout(request)
                                request.facebook.session_key = None
                                request.facebook.uid = None
                    except FacebookProfile.DoesNotExsist, ex:
                        # user doesnt have facebook :(
                        pass

        except Exception, ex:
            # Because this is a middleware, we can't assume the errors will
            # be caught anywhere useful.
            logout(request)
            request.facebook.session_key = None
            request.facebook.uid = None
            log.exception(ex)

        return None

    def process_exception(self,request,exception):
        my_ex = exception
        if type(exception) == TemplateSyntaxError:
            if getattr(exception,'exc_info',False):
                my_ex = exception.exc_info[1]

        if type(my_ex) == FacebookError:
            # we get this error if the facebook session is timed out
            # we should log out the user and send them to somewhere useful
            if my_ex.code is 102:
                logout(request)
                request.facebook.session_key = None
                request.facebook.uid = None
                log.error('102, session')
                return HttpResponseRedirect(reverse('facebookconnect.views.facebook_login'))
        elif type(my_ex) == URLError:
            if my_ex.reason is 104:
                log.error('104, connection reset?')
            elif my_ex.reason is 102:
                log.error('102, name or service not known')

########NEW FILE########
__FILENAME__ = models
# Copyright 2008-2009 Brian Boyer, Ryan Mark, Angela Nitzke, Joshua Pollock,
# Stuart Tiffen, Kayla Webley and the Medill School of Journalism, Northwestern
# University.
#
# This file is part of django-facebookconnect.
#
# django-facebookconnect is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# django-facebookconnect is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
#You should have received a copy of the GNU General Public License
#along with django-facebookconnect.  If not, see <http://www.gnu.org/licenses/>.

import datetime
import logging
log = logging.getLogger('facebookconnect.models')
import sha, random
from urllib2 import URLError

from facebook.djangofb import Facebook,get_facebook_client
from facebook import FacebookError

from django.db import models
from django.conf import settings
from django.contrib.auth.models import User
from django.core.cache import cache
from django.core.exceptions import ImproperlyConfigured
from django.db.models.signals import post_delete

try:
    from threading import local
except ImportError:
    from django.utils._threading_local import local

_thread_locals = local()

class FacebookBackend:
    def authenticate(self, request=None):
        fb = get_facebook_client()
        fb.check_session(request)
        if fb.uid:
            try:
                log.debug("Checking for Facebook Profile %s..." % fb.uid)
                fbprofile = FacebookProfile.objects.get(facebook_id=fb.uid)
                return fbprofile.user
            except FacebookProfile.DoesNotExist:
                log.debug("FB account hasn't been used before...")
                return None
            except User.DoesNotExist:
                log.error("FB account exists without an account.")
                return None
        else:
            log.debug("Invalid Facebook login for %s" % fb.__dict__)
            return None
        
    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None
        
class BigIntegerField(models.IntegerField):
    empty_strings_allowed=False
    def get_internal_type(self):
        return "BigIntegerField"
    
    def db_type(self):
        if settings.DATABASE_ENGINE == 'oracle':
            return "NUMBER(19)"
        else:
            return "bigint"

class FacebookTemplate(models.Model):
    name = models.SlugField(unique=True)
    template_bundle_id = BigIntegerField()
    
    def __unicode__(self):
        return self.name.capitalize()

class FacebookProfile(models.Model):
    user = models.OneToOneField(User,related_name="facebook_profile")
    facebook_id = BigIntegerField(unique=True)
    
    __facebook_info = None
    dummy = True

    FACEBOOK_FIELDS = ['uid,name,first_name,last_name,pic_square_with_logo,affiliations,status,proxied_email']
    DUMMY_FACEBOOK_INFO = {
        'uid': 0,
        'name': '(Private)',
        'first_name': '(Private)',
        'last_name': '(Private)',
        'pic_square_with_logo': 'http://www.facebook.com/pics/t_silhouette.gif',
        'affiliations': None,
        'status': None,
        'proxied_email': None,
    }
    
    def __init__(self, *args, **kwargs):
        """reset local DUMMY info"""
        super(FacebookProfile,self).__init__(*args,**kwargs)
        try:
            self.DUMMY_FACEBOOK_INFO = settings.DUMMY_FACEBOOK_INFO
        except AttributeError:
            pass
        try:
            self.FACEBOOK_FIELDS = settings.FACEBOOK_FIELDS
        except AttributeError:
            pass
        
        if hasattr(_thread_locals,'fbids'):
            if ( self.facebook_id 
                    and self.facebook_id not in _thread_locals.fbids ):
                _thread_locals.fbids.append(str(self.facebook_id))
        else: _thread_locals.fbids = [self.facebook_id]
            
    def __get_picture_url(self):
        if self.__configure_me() and self.__facebook_info['pic_square_with_logo']:
            return self.__facebook_info['pic_square_with_logo']
        else:
            return self.DUMMY_FACEBOOK_INFO['pic_square_with_logo']
    picture_url = property(__get_picture_url)
    
    def __get_full_name(self):
        if self.__configure_me() and self.__facebook_info['name']:
            return u"%s" % self.__facebook_info['name']
        else:
            return self.DUMMY_FACEBOOK_INFO['name']
    full_name = property(__get_full_name)
    
    def __get_first_name(self):
        if self.__configure_me() and self.__facebook_info['first_name']:
            return u"%s" % self.__facebook_info['first_name']
        else:
            return self.DUMMY_FACEBOOK_INFO['first_name']
    first_name = property(__get_first_name)
    
    def __get_last_name(self):
        if self.__configure_me() and self.__facebook_info['last_name']:
            return u"%s" % self.__facebook_info['last_name']
        else:
            return self.DUMMY_FACEBOOK_INFO['last_name']
    last_name = property(__get_last_name)
    
    def __get_networks(self):
        if self.__configure_me():
            return self.__facebook_info['affiliations']
        else: return []
    networks = property(__get_networks)

    def __get_email(self):
        if self.__configure_me() and self.__facebook_info['proxied_email']:
            return self.__facebook_info['proxied_email']
        else:
            return ""
    email = property(__get_email)

    def facebook_only(self):
        """return true if this user uses facebook and only facebook"""
        if self.facebook_id and str(self.facebook_id) == self.user.username:
            return True
        else:
            return False
    
    def is_authenticated(self):
        """Check if this fb user is logged in"""
        _facebook_obj = get_facebook_client()
        if _facebook_obj.session_key and _facebook_obj.uid:
            try:
                fbid = _facebook_obj.users.getLoggedInUser()
                if int(self.facebook_id) == int(fbid):
                    return True
                else:
                    return False
            except FacebookError,ex:
                if ex.code == 102:
                    return False
                else:
                    raise

        else:
            return False

    def get_friends_profiles(self,limit=50):
        '''returns profile objects for this persons facebook friends'''
        friends = []
        friends_info = []
        friends_ids = []
        try:
            friends_ids = self.__get_facebook_friends()
        except (FacebookError,URLError), ex:
            log.error("Fail getting friends: %s" % ex)
        log.debug("Friends of %s %s" % (self.facebook_id,friends_ids))
        if len(friends_ids) > 0:
            #this will cache all the friends in one api call
            self.__get_facebook_info(friends_ids)
        for id in friends_ids:
            try:
                friends.append(FacebookProfile.objects.get(facebook_id=id))
            except (User.DoesNotExist, FacebookProfile.DoesNotExist):
                log.error("Can't find friend profile %s" % id)
        return friends

    def __get_facebook_friends(self):
        """returns an array of the user's friends' fb ids"""
        _facebook_obj = get_facebook_client()
        friends = []
        cache_key = 'fb_friends_%s' % (self.facebook_id)
    
        fb_info_cache = cache.get(cache_key)
        if fb_info_cache:
            friends = fb_info_cache
        else:
            log.debug("Calling for '%s'" % cache_key)
            friends = _facebook_obj.friends.getAppUsers()
            cache.set(
                cache_key, 
                friends, 
                getattr(settings,'FACEBOOK_CACHE_TIMEOUT',1800)
            )
        
        return friends        

    def __get_facebook_info(self,fbids):
        """
           Takes an array of facebook ids and caches all the info that comes
           back. Returns a tuple - an array of all facebook info, and info for
           self's fb id.
        """
        _facebook_obj = get_facebook_client()
        all_info = []
        my_info = None
        ids_to_get = []
        for fbid in fbids:
            if fbid == 0 or fbid is None:
                continue
            
            if _facebook_obj.uid is None:
                cache_key = 'fb_user_info_%s' % fbid
            else:
                cache_key = 'fb_user_info_%s_%s' % (_facebook_obj.uid, fbid)
        
            fb_info_cache = cache.get(cache_key)
            if fb_info_cache:
                log.debug("Found %s in cache" % fbid)
                all_info.append(fb_info_cache)
                if fbid == self.facebook_id:
                    my_info = fb_info_cache
            else:
                ids_to_get.append(fbid)
        
        if len(ids_to_get) > 0:
            log.debug("Calling for %s" % ids_to_get)
            tmp_info = _facebook_obj.users.getInfo(
                            ids_to_get, 
                            self.FACEBOOK_FIELDS
                        )
            
            all_info.extend(tmp_info)
            for info in tmp_info:
                if info['uid'] == self.facebook_id:
                    my_info = info
                
                if _facebook_obj.uid is None:
                    cache_key = 'fb_user_info_%s' % fbid
                else:
                    cache_key = 'fb_user_info_%s_%s' % (_facebook_obj.uid,info['uid'])

                cache.set(
                    cache_key, 
                    info, 
                    getattr(settings, 'FACEBOOK_CACHE_TIMEOUT', 1800)
                )
                
        return all_info, my_info

    def __configure_me(self):
        """Calls facebook to populate profile info"""
        try:
            log.debug( "Configure fb profile %s" % self.facebook_id )
            if self.dummy or self.__facebook_info is None:
                ids = getattr(_thread_locals, 'fbids', [self.facebook_id])
                all_info, my_info = self.__get_facebook_info(ids)
                if my_info:
                    self.__facebook_info = my_info
                    self.dummy = False
                    return True
            else:
                return True
        except ImproperlyConfigured, ex:
            log.error('Facebook not setup')
        except (FacebookError,URLError), ex:
            log.error('Fail loading profile: %s' % ex)
        # except IndexError, ex:
        #     log.error("Couldn't retrieve FB info for FBID: '%s' profile: '%s' user: '%s'" % (self.facebook_id, self.id, self.user_id))
        
        return False

    def get_absolute_url(self):
        return "http://www.facebook.com/profile.php?id=%s" % self.facebook_id

    def __unicode__(self):
        return "FacebookProfile for %s" % self.facebook_id

def unregister_fb_profile(sender, **kwargs):
    """call facebook and let them know to unregister the user"""
    fb = get_facebook_client()
    fb.connect.unregisterUser([fb.hash_email(kwargs['instance'].user.email)])

#post_delete.connect(unregister_fb_profile,sender=FacebookProfile)
########NEW FILE########
__FILENAME__ = facebook_tags
# Copyright 2008-2009 Brian Boyer, Ryan Mark, Angela Nitzke, Joshua Pollock,
# Stuart Tiffen, Kayla Webley and the Medill School of Journalism, Northwestern
# University.
#
# This file is part of django-facebookconnect.
#
# django-facebookconnect is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# django-facebookconnect is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
#You should have received a copy of the GNU General Public License
#along with django-facebookconnect.  If not, see <http://www.gnu.org/licenses/>.

from django import template
from django.conf import settings
from django.core.urlresolvers import reverse
from django.template.loader import render_to_string
from django.contrib.sites.models import Site
from django.contrib.auth import REDIRECT_FIELD_NAME

from facebook.djangofb import get_facebook_client
from facebookconnect.models import FacebookTemplate, FacebookProfile

register = template.Library()
    
@register.inclusion_tag('facebook/js.html')
def initialize_facebook_connect():
    return {'facebook_api_key': settings.FACEBOOK_API_KEY}

@register.inclusion_tag('facebook/show_string.html', takes_context=True)
def show_facebook_name(context, user):
    if isinstance(user, FacebookProfile):
        p = user
    else:
        p = user.facebook_profile
    if getattr(settings, 'WIDGET_MODE', None):
        #if we're rendering widgets, link direct to facebook
        return {'string':u'<fb:name uid="%s" />' % (p.facebook_id)}
    else:
        return {'string':u'<a href="%s">%s</a>' % (p.get_absolute_url(), p.full_name)}

@register.inclusion_tag('facebook/show_string.html', takes_context=True)
def show_facebook_first_name(context, user):
    if isinstance(user, FacebookProfile):
        p = user
    else:
        p = user.facebook_profile
    if getattr(settings, 'WIDGET_MODE', None):
        #if we're rendering widgets, link direct to facebook
        return {'string':u'<fb:name uid="%s" firstnameonly="true" />' % (p.facebook_id)}
    else:
        return {'string':u'<a href="%s">%s</a>' % (p.get_absolute_url(), p.first_name)}
    
@register.inclusion_tag('facebook/show_string.html', takes_context=True)
def show_facebook_possesive(context, user):
    if isinstance(user, FacebookProfile):
        p = user
    else:
        p = user.facebook_profile
    return {'string':u'<fb:name uid="%i" possessive="true" linked="false"></fb:name>' % p.facebook_id}

@register.inclusion_tag('facebook/show_string.html', takes_context=True)
def show_facebook_greeting(context, user):
    if isinstance(user, FacebookProfile):
        p = user
    else:
        p = user.facebook_profile
    if getattr(settings, 'WIDGET_MODE', None):
        #if we're rendering widgets, link direct to facebook
        return {'string':u'Hello, <fb:name uid="%s" useyou="false" firstnameonly="true" />' % (p.facebook_id)}
    else:
        return {'string':u'Hello, <a href="%s">%s</a>!' % (p.get_absolute_url(), p.first_name)}

@register.inclusion_tag('facebook/show_string.html', takes_context=True)
def show_facebook_status(context, user):
    if isinstance(user, FacebookProfile):
        p = user
    else:
        p = user.facebook_profile
    return {'string':p.status}

@register.inclusion_tag('facebook/show_string.html', takes_context=True)
def show_facebook_photo(context, user):
    if isinstance(user, FacebookProfile):
        p = user
    else:
        p = user.facebook_profile
    if p.get_absolute_url(): url = p.get_absolute_url()
    else: url = ""
    if p.picture_url: pic_url = p.picture_url
    else: pic_url = ""
    if p.full_name: name = p.full_name
    else: name = ""
    if getattr(settings, 'WIDGET_MODE', None):
        #if we're rendering widgets, link direct to facebook
        return {'string':u'<fb:profile_pic uid="%s" facebook-logo="true" />' % (p.facebook_id)}
    else:
        return {'string':u'<a href="%s"><img src="%s" alt="%s"/></a>' % (url, pic_url, name)}

@register.inclusion_tag('facebook/display.html', takes_context=True)
def show_facebook_info(context, user):
    if isinstance(user, FacebookProfile):
        p = user
    else:
        p = user.facebook_profile
    return {'profile_url':p.get_absolute_url(), 'picture_url':p.picture_url, 'full_name':p.full_name, 'networks':p.networks}

@register.inclusion_tag('facebook/mosaic.html')
def show_profile_mosaic(profiles):
    return {'profiles':profiles}

@register.inclusion_tag('facebook/connect_button.html', takes_context=True)
def show_connect_button(context):
    if REDIRECT_FIELD_NAME in context:
        redirect_url = context[REDIRECT_FIELD_NAME]
    else: redirect_url = False
    
    if ('user' in context and hasattr(context['user'], 'facebook_profile') and
         context['user'].facebook_profile and
         context['user'].facebook_profile.is_authenticated()):
        logged_in = True
    else: logged_in = False
    return {REDIRECT_FIELD_NAME:redirect_url, 'logged_in':logged_in}

@register.simple_tag
def facebook_js():
    return '<script src="http://static.ak.connect.facebook.com/js/api_lib/v0.4/FeatureLoader.js.php" type="text/javascript"></script>'

@register.simple_tag
def show_logout():
    o = reverse('facebook_logout')
    return '<a href="%s" onclick="FB.Connect.logoutAndRedirect(\'%s\');return false;">logout</a>' % (o, o) #hoot!

@register.filter()
def js_string(value):
    import re
    return re.sub(r'[\r\n]+', '', value)

@register.inclusion_tag('facebook/invite.html')
def show_invite_link(invitation_template="facebook/invitation.fbml", show_link=True):
    """display an invite friends link"""
    fb = get_facebook_client()
    current_site = Site.objects.get_current()
    
    content = render_to_string(invitation_template,
                               { 'inviter': fb.uid,
                                 'url': fb.get_add_url(),
                                 'site': current_site })
    
    from cgi import escape 
    content = escape(content, True) 

    facebook_uid = fb.uid
    fql = "SELECT uid FROM user WHERE uid IN (SELECT uid2 FROM friend WHERE uid1='%s') AND has_added_app = 1" % fb.uid
    result = fb.fql.query(fql)
    # Extract the user ID's returned in the FQL request into a new array.
    if result and isinstance(result, list):
        friends_list = map(lambda x: str(x['uid']), result)
    else: friends_list = []
    # Convert the array of friends into a comma-delimeted string.
    exclude_ids = ','.join(friends_list) 
    
    return {
        'exclude_ids':exclude_ids,
        'content':content,
        'action_url':'',
        'site':current_site,
        'show_link':show_link,
    }
########NEW FILE########
__FILENAME__ = tests

########NEW FILE########
__FILENAME__ = urls
# Copyright 2008-2009 Brian Boyer, Ryan Mark, Angela Nitzke, Joshua Pollock,
# Stuart Tiffen, Kayla Webley and the Medill School of Journalism, Northwestern
# University.
#
# This file is part of django-facebookconnect.
#
# django-facebookconnect is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# django-facebookconnect is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
#You should have received a copy of the GNU General Public License
#along with django-facebookconnect.  If not, see <http://www.gnu.org/licenses/>.

from django.conf.urls.defaults import *
from django.views.generic.simple import direct_to_template
from facebookconnect.views import facebook_login,facebook_logout,setup

urlpatterns = patterns('',
    url(r'^login/$',
        facebook_login,
        name="facebook_login"),
    url(r'^logout/$', 
        facebook_logout,
        name="facebook_logout"),
    url(r'^setup/$',
        setup,
        name="facebook_setup"),
    url(r'^xd_receiver.htm$',
        direct_to_template,
        {'template': 'facebook/xd_receiver.htm'},
        name="facebook_xd_receiver"),
)


########NEW FILE########
__FILENAME__ = views
# Copyright 2008-2009 Brian Boyer, Ryan Mark, Angela Nitzke, Joshua Pollock,
# Stuart Tiffen, Kayla Webley and the Medill School of Journalism, Northwestern
# University.
#
# This file is part of django-facebookconnect.
#
# django-facebookconnect is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# django-facebookconnect is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
#You should have received a copy of the GNU General Public License
#along with django-facebookconnect.  If not, see <http://www.gnu.org/licenses/>.

import logging
log = logging.getLogger('facebookconnect.views')

from django.http import HttpResponse, HttpResponseRedirect, Http404
from django.template import RequestContext
from django.core.urlresolvers import reverse
from django.shortcuts import render_to_response
from django.contrib.auth import authenticate, login, logout, REDIRECT_FIELD_NAME
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth.models import User
from django.conf import settings

from facebook.djangofb import require_login as require_fb_login

from facebookconnect.models import FacebookProfile
from facebookconnect.forms import FacebookUserCreationForm

def facebook_login(request, redirect_url=None,
                   template_name='facebook/login.html',
                   extra_context=None):
    """
    facebook_login
    ===============================
    
    Handles logging in a facebook user. Usually handles the django side of
    what happens when you click the facebook connect button. The user will get
    redirected to the 'setup' view if thier facebook account is not on file.
    If the user is on file, they will get redirected. You can specify the
    redirect url in the following order of presidence:
    
     1. whatever url is in the 'next' get parameter passed to the facebook_login url
     2. whatever url is passed to the facebook_login view when the url is defined
     3. whatever url is defined in the LOGIN_REDIRECT_URL setting directive
    
    Sending a user here without login will display a login template.
    
    If you define a url to use this view, you can pass the following parameters:
     * redirect_url: defines where to send the user after they are logged in. This
                     can get overridden by the url in the 'next' get param passed on 
                     the url.
     * template_name: Template to use if a user arrives at this page without submitting
                      to it. Uses 'facebook/login.html' by default.
     * extra_context: A context object whose contents will be passed to the template.
    """
    # User is logging in
    if request.method == "POST":
        log.debug("OK logging in...")
        url = reverse('facebook_setup')
        if request.POST.get(REDIRECT_FIELD_NAME,False):
            url += "?%s=%s" % (REDIRECT_FIELD_NAME, request.POST[REDIRECT_FIELD_NAME])
        elif redirect_url:
            url += "?%s=%s" % (REDIRECT_FIELD_NAME, redirect_url)
        user = authenticate(request=request)
        if user is not None:
            if user.is_active:
                login(request, user)
                # Redirect to a success page.
                log.debug("Redirecting to %s" % url)
                return HttpResponseRedirect(url)
            else:
                log.debug("This account is disabled.")
                raise FacebookAuthError('This account is disabled.')
        elif request.facebook.uid:
            #we have to set this user up
            log.debug("Redirecting to setup")
            return HttpResponseRedirect(url)
    
    # User is already logged in
    elif request.user.is_authenticated:
        if request.REQUEST.get(REDIRECT_FIELD_NAME,False):
            redirect_url = request.REQUEST[REDIRECT_FIELD_NAME]
        elif redirect_url is None:
            redirect_url = getattr(settings, "LOGIN_REDIRECT_URL", "/")
        
        HttpResponseRedirect(redirect_url)

    # User ain't logged in
    # here we handle extra_context like it is done in django-registration
    if extra_context is None:
        extra_context = {}
    context = RequestContext(request)
    for key, value in extra_context.items():
        context[key] = callable(value) and value() or value

    template_dict = {}
    # we only need to set next if its been passed in the querystring or post vars
    if request.REQUEST.get(REDIRECT_FIELD_NAME, False):
        template_dict.update({REDIRECT_FIELD_NAME:request.REQUEST[REDIRECT_FIELD_NAME]})

    return render_to_response(
        template_name,
        template_dict,
        context_instance=context)
    
    
def facebook_logout(request, redirect_url=None):
    """
    facebook_logout
    ============================
    
    Logs the user out of facebook and django.
    
    If you define a url to use this view, you can pass the following
    parameters:
     * redirect_url: defines where to send the user after they are logged out.
                     If no url is pass, it defaults to using the 
                     'LOGOUT_REDIRECT_URL' setting.
    
    """
    logout(request)
    if getattr(request,'facebook',False):
        request.facebook.session_key = None
        request.facebook.uid = None
    url = getattr(settings,'LOGOUT_REDIRECT_URL',redirect_url) or '/'
    return HttpResponseRedirect(url)
    
def setup(request,redirect_url=None,
          registration_form_class=FacebookUserCreationForm,
          template_name='facebook/setup.html',
          extra_context=None):
    """
    setup
    ===============================
    
    Handles a new facebook user. There are three ways to setup a new facebook user.
     1. Link the facebook account with an existing django account.
     2. Create a dummy django account to attach to facebook. The user must always use
        facebook to login.
     3. Ask the user to create a new django account
     
    The built in template presents the user with all three options. Once setup is 
    complete the user will get redirected. The url used in the following order of 
    presidence:

      1. whatever url is in the 'next' get parameter passed to the setup url
      2. whatever url is passed to the setup view when the url is defined
      3. whatever url is defined in the LOGIN_REDIRECT_URL setting directive
    
    If you define a url to use this view, you can pass the following parameters:
     * redirect_url: Defines where to send the user after they are setup. This
                     can get overridden by the url in the 'next' get param passed on 
                     the url.
     * registration_form_class: Django form class to use for new user way #3 explained
                                above. The form should create a new user.
     * template_name: Template to use. Uses 'facebook/setup.html' by default.
     * extra_context: A context object whose contents will be passed to the template.
    """
    log.debug('in setup view')
    #you need to be logged into facebook.
    if not request.facebook.uid:
        log.debug('Need to be logged into facebook')
        url = reverse(facebook_login)
        if request.REQUEST.get(REDIRECT_FIELD_NAME,False):
            url += "?%s=%s" % (REDIRECT_FIELD_NAME, request.REQUEST[REDIRECT_FIELD_NAME])
        return HttpResponseRedirect(url)

    #setup forms
    login_form = AuthenticationForm()
    registration_form = registration_form_class()

    #figure out where to go after setup
    if request.REQUEST.get(REDIRECT_FIELD_NAME,False):
        redirect_url = request.REQUEST[REDIRECT_FIELD_NAME]
    elif redirect_url is None:
        redirect_url = getattr(settings, "LOGIN_REDIRECT_URL", "/")

    #check that this fb user is not already in the system
    try:
        FacebookProfile.objects.get(facebook_id=request.facebook.uid)
        # already setup, move along please
        return HttpResponseRedirect(redirect_url)
    except FacebookProfile.DoesNotExist, e:
        # not in the db, ok to continue
        pass

    #user submitted a form - which one?
    if request.method == "POST":
        log.debug('Submitted form')
        #lets setup a facebook only account. The user will have to use
        #facebook to login.
        if request.POST.get('facebook_only',False):
            log.debug('Facebook Only')
            profile = FacebookProfile(facebook_id=request.facebook.uid)
            user = User(username=request.facebook.uid,
                        email=profile.email)
            user.set_unusable_password()
            user.save()
            profile.user = user
            profile.save()
            log.info("Added user and profile for %s!" % request.facebook.uid)
            user = authenticate(request=request)
            login(request, user)
            return HttpResponseRedirect(redirect_url)
        
        # user setup his/her own local account in addition to their facebook
        # account. The user will have to login with facebook unless they 
        # reset their password.
        elif request.POST.get('register',False):
            log.debug('Register a new account')
            profile = FacebookProfile(facebook_id=request.facebook.uid)
            if profile.first_name != "(Private)":
                fname = profile.first_name
            if profile.last_name != "(Private)":
                lname = profile.last_name
            user = User(first_name=fname, last_name=lname)
            registration_form = registration_form_class(
                                        data=request.POST, instance=user)
            if registration_form.is_valid():
                user = registration_form.save()
                profile.user = user
                profile.save()
                log.info("Added user and profile for %s!" % request.facebook.uid)
                login(request, authenticate(request=request))
                return HttpResponseRedirect(redirect_url)
            else:
                request.user = User()
                request.user.facebook_profile = FacebookProfile(facebook_id=request.facebook.uid)
    
        #user logs in in with an existing account, and the two are linked.
        elif request.POST.get('login',False):
            login_form = AuthenticationForm(data=request.POST)

            if login_form.is_valid():
                user = login_form.get_user()
                log.debug("Trying to setup FB: %s, %s" % (user,request.facebook.uid))
                if user and user.is_active:
                    FacebookProfile.objects.get_or_create(user=user, facebook_id=request.facebook.uid)
                    log.info("Attached facebook profile %s to user %s!" % (request.facebook.uid, user))
                    login(request, user)
                    return HttpResponseRedirect(redirect_url)
            else:
                request.user = User()
                request.user.facebook_profile = FacebookProfile(facebook_id=request.facebook.uid)
    
    #user didn't submit a form, but is logged in already. We'll just link up their facebook
    #account automatically.
    elif request.user.is_authenticated():
        log.debug('Already logged in')
        try:
            request.user.facebook_profile
        except FacebookProfile.DoesNotExist:
            profile = FacebookProfile(facebook_id=request.facebook.uid)
            profile.user = request.user
            profile.save()
            log.info("Attached facebook profile %s to user %s!" % (profile.facebook_id,profile.user))

        return HttpResponseRedirect(redirect_url)
    
    # user just showed up
    else:
        log.debug('Setting up form...')
        request.user.facebook_profile = profile = FacebookProfile(facebook_id=request.facebook.uid)
        login_form = AuthenticationForm(request)
        log.debug('creating a dummy user')
        fname = lname = ''
        if profile.first_name != "(Private)":
            fname = profile.first_name
        if profile.last_name != "(Private)":
            lname = profile.last_name
        user = User(first_name=fname, last_name=lname)
        registration_form = registration_form_class(instance=user)
    
    log.debug('going all the way...')
    
    # add the extra_context to this one
    if extra_context is None:
        extra_context = {}
    context = RequestContext(request)
    for key, value in extra_context.items():
        context[key] = callable(value) and value() or value

    template_dict = {
        "login_form":login_form,
        "registration_form":registration_form
    }
    
    # we only need to set next if its been passed in the querystring or post vars
    if request.REQUEST.get(REDIRECT_FIELD_NAME, False):
        template_dict.update( {REDIRECT_FIELD_NAME: request.REQUEST[REDIRECT_FIELD_NAME]})
        
    return render_to_response(
        template_name,
        template_dict,
        context_instance=context)

class FacebookAuthError(Exception):
    def __init__(self, message):
        self.message = message
    def __str__(self):
        return repr(self.message)
    
########NEW FILE########
__FILENAME__ = settings.EXAMPLE
# Copyright 2008-2009 Brian Boyer, Ryan Mark, Angela Nitzke, Joshua Pollock,
# Stuart Tiffen, Kayla Webley and the Medill School of Journalism, Northwestern
# University.
#
# This file is part of django-facebookconnect.
#
# django-facebookconnect is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# django-facebookconnect is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
#You should have received a copy of the GNU General Public License
#along with django-facebookconnect.  If not, see <http://www.gnu.org/licenses/>.

"""
These are all the available settings for the django-facebookconnect pluggable.
Set your key, caching, debugging and template settings with these directives.

Below is an example of how to format the facebook templates to get them shoved
into facebook. The first element of each tuple is the name of the template. 
Use the name to look up the template's id with the FacebookTemplate class. The
format of this thing follows facebook's API for installing templates. When in
doubt check the facebook API docs. Calling  'manage.py installfacebooktemplates' 
will install these templates to the local DB and facebook.
"""

# Replace with keys from Facebook
FACEBOOK_API_KEY = '00000000000000000000000000000000'
FACEBOOK_SECRET_KEY = '00000000000000000000000000000000'
FACEBOOK_INTERNAL = True

#Cache facebook info for x seconds
FACEBOOK_CACHE_TIMEOUT = 1800

#setting this to true will cause facebook to fail randomly
#only for the masochistic
RANDOM_FACEBOOK_FAIL = False

#define the templates to publish to the facebook feed
FACEBOOK_TEMPLATES = (
    ('question',(
        #one-line
        ['{*actor*} <a href="{*url*}">asked a question about the article</a>: {*headline*}.'],
        [{#short story
            'template_title': '{*actor*} <a href="{*url*}">asked a question about the article</a>: {*headline*}.',
            'template_body': '<b>"{*question*}"</b>'
        }],
        {#full story
            'template_title': '{*actor*} <a href="{*url*}">asked a question about the article</a>: {*headline*}.',
            'template_body': '''<div style="font-size:1.5em;margin-bottom:0.4em;">"{*question*}"</div>
                <div style="font-weight:bold;margin-bottom:0.2em;">{*headline*}</div>
                <div>{*article*} ...</div>'''
        },
        [{#action
            'text': "Answer {*actor*}'s question",
            'href': '{*url*}'
        }],
    )),
    ('answer',(
        #one-line
        ['{*actor*} <a href="{*url*}">answered a question about the article</a>: {*headline*}.'],
        [{#short story
            'template_title': '{*actor*} <a href="{*url*}">answered a question about the article</a>: {*headline*}.',
            'template_body': '''Q: "{*question*}" - <fb:name uid="{*asker*}" /><br/>
            A: <b>"{*answer*}"</b> - {*actor*}'''
        }],
        {#full story
            'template_title': '{*actor*} <a href="{*url*}">answered a question about the article</a>: {*headline*}.',
            'template_body': '''<div style="margin-bottom:0.4em;">Q: "{*question*}" - <fb:name uid="{*asker*}" /></div>
            <div style="font-size:1.5em;margin-bottom:0.2em;">A: "{*answer*}"</div>
            <div style="font-size:1.5em;margin-bottom:0.4em;text-align:right;">- {*actor*}</div>
            <div style="font-weight:bold;margin-bottom:0.2em;">{*headline*}</div>
            <div>{*article*}</div>'''
        },
        [{#action
            'text': "Read {*actor*}'s answer",
            'href': '{*url*}'
        }],
    )),
    ('quip',(
        #one-line
        ['{*actor*} <a href="{*url*}">quipped about the article</a>: {*headline*}.'],
        [{#short story
            'template_title': '{*actor*} <a href="{*url*}">quipped about the article</a>: {*headline*}.',
            'template_body': '<b>{*actor*} {*verb*} {*quip*}</b>'
        }],
        {#full story
            'template_title': '{*actor*} <a href="{*url*}">quipped about the article</a>: {*headline*}.',
            'template_body': '''<div style="font-size:1.5em;margin-bottom:0.4em;margin-top:2px;"><span style="border:solid 2px lightblue;text-transform:uppercase;padding:0 2px;">{*actor*}</span> <span style="border:solid 2px blue;background-color:{*verb_color*};color:white;text-transform:uppercase;padding:0 2px;">{*verb*}</span> {*quip*}</div>
            <div style="font-weight:bold;margin-bottom:0.2em;">{*headline*}</div>
            <div>{*article*}</div>'''
        },
        [{#action
            'text': "Quip back!",
            'href': '{*url*}'
        }],
    )),
    ('letter',(
        #one-line
        ['{*actor*} wrote a letter to the editor: <a href="{*url*}">{*title*}</a>.'],
        [{#short story
            'template_title': '{*actor*} wrote a letter to the editor: <a href="{*url*}">{*title*}</a>.',
            'template_body': '<b>{*title*}</b><br/>{*body*}'
        }],
        {#full story
            'template_title': '{*actor*} wrote a letter to the editor: <a href="{*url*}">{*title*}</a>.',
            'template_body': '''<div style="font-size:1.5em;margin-bottom:0.2em;">{*title*}</div>
            <div>{*body*}</div>'''
        },
        [{#action
            'text': "Read {*actor*}'s letter",
            'href': '{*url*}'
        }],
    )),
    ('letter_re_article',(
        #one-line
        ['{*actor*} <a href="{*url*}">wrote a letter to the editor</a> in response to the article: {*headline*}'],
        [{#short story
            'template_title': '{*actor*} <a href="{*url*}">wrote a letter to the editor</a> in response to the article: {*headline*}',
            'template_body': '<b>{*title*}</b><br/>{*body*}'
        }],
        {#full story
            'template_title': '{*actor*} <a href="{*url*}">wrote a letter to the editor</a> in response to the article: {*headline*}',
            'template_body': '''<div style="margin-top:0.8em;">{*actor*} wrote:</div>
            <div style="font-size:1.5em;margin-bottom:0.2em;">{*title*}</div>
            <div>{*body*}</div>
            <div style="margin-bottom:0.2em;margin-top:1em;">In response to:</div>
            <div style="font-weight:bold;margin-bottom:0.2em;">{*headline*}</div>
            <div>{*article*}</div>'''
        },
        [{#action
            'text': "Read {*actor*}'s letter",
            'href': '{*url*}'
        }],
    )),
    ('letter_re_letter',(
        #one-line
        ['{*actor*} responded to a letter to the editor: <a href="{*url*}">{*title*}</a>'],
        [{#short story
            'template_title': '{*actor*} responded to a letter to the editor: <a href="{*url*}">{*title*}</a>',
            'template_body': '''In response to <fb:name uid="{*original_user*}" possessive="true"/> letter, {*actor*} wrote:<br/>
            <b>{*title*}</b><br/>{*body*}'''
        }],
        {#full story
            'template_title': '{*actor*} responded to a letter to the editor: <a href="{*url*}">{*title*}</a>',
            'template_body': '''<div style="margin-top:0.8em;">{*actor*} wrote:</div>
            <div style="font-size:1.5em;margin-bottom:0.2em;">{*title*}</div>
            <div>{*body*}</div>
            <div style="margin-bottom:0.2em;margin-top:1em;">In response to <fb:name uid="{*original_user*}" possessive="true"/> letter:</div>
            <div style="font-weight:bold;margin-bottom:0.2em;">{*original_title*}</div>
            <div>{*original_body*}</div>'''
        },
        [{#action
            'text': "Read {*actor*}'s letter",
            'href': '{*url*}'
        }],
    )),
    ('letter_re_letter_re_article',(
        #one-line
        ['{*actor*} <a href="{*url*}">responded to a letter to the editor</a> about the article: {*headline*}'],
        [{#short story
            'template_title': '{*actor*} <a href="{*url*}">responded to a letter to the editor</a> about the article: {*headline*}',
            'template_body': '''In response to <fb:name uid="{*original_user*}" possessive="true"/> letter, {*actor*} wrote:<br/>
            <b>{*title*}</b><br/>{*body*}'''
        }],
        {#full story
            'template_title': '{*actor*} <a href="{*url*}">responded to a letter to the editor</a> about the article: {*headline*}',
            'template_body': '''<div style="margin-top:0.8em;">{*actor*} wrote:</div>
            <div style="font-size:1.5em;margin-bottom:0.2em;">{*title*}</div>
            <div>{*body*}</div>
            <div style="margin-bottom:0.2em;margin-top:1em;">In response to <fb:name uid="{*original_user*}" possessive="true"/> letter about {*headline*}:</div>
            <div style="font-weight:bold;margin-bottom:0.2em;">{*original_title*}</div>
            <div>{*original_body*}</div>'''
        },
        [{#action
            'text': "Read {*actor*}'s letter",
            'href': '{*url*}'
        }],
    )),
)

########NEW FILE########
