__FILENAME__ = admin
from snipt.ad.models import Ad
from django.contrib import admin

class AdAdmin(admin.ModelAdmin):
    list_display = ('title','tags','url','image',)
    ordering = ('title',)
    
admin.site.register(Ad, AdAdmin)

########NEW FILE########
__FILENAME__ = 0001_initial
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding model 'Ad'
        db.create_table('ad_ad', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('title', self.gf('django.db.models.fields.TextField')()),
            ('url', self.gf('django.db.models.fields.TextField')()),
            ('image', self.gf('django.db.models.fields.files.ImageField')(max_length=100)),
            ('tags', self.gf('tagging.fields.TagField')(default='')),
        ))
        db.send_create_signal('ad', ['Ad'])


    def backwards(self, orm):
        
        # Deleting model 'Ad'
        db.delete_table('ad_ad')


    models = {
        'ad.ad': {
            'Meta': {'object_name': 'Ad'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'image': ('django.db.models.fields.files.ImageField', [], {'max_length': '100'}),
            'tags': ('tagging.fields.TagField', [], {'default': "''"}),
            'title': ('django.db.models.fields.TextField', [], {}),
            'url': ('django.db.models.fields.TextField', [], {})
        }
    }

    complete_apps = ['ad']

########NEW FILE########
__FILENAME__ = models
from tagging.fields import TagField
from tagging.models import Tag
from django.db import models
import tagging

class Ad(models.Model):
    title       = models.TextField()
    url         = models.TextField()
    image       = models.ImageField(upload_to='ads')
    tags        = TagField()
    
    def __unicode__(self):
        return u'%s' %(self.title)
    
    def get_tags(self):
        return Tag.objects.get_for_object(self)

tagging.register(Ad, tag_descriptor_attr='_tags') 

########NEW FILE########
__FILENAME__ = ads
from tagging.models import TaggedItem
from snipt.ad.models import Ad
from django import template

register = template.Library()

@register.simple_tag
def ad(tag):
    try:
        ads = TaggedItem.objects.get_by_model(Ad.objects.order_by('?'), tag)
        ad = ads[0]
    except:
        ads = Ad.objects.order_by('?')
        ad = ads[0]
        tag = ''
    return """
        <h1 style="margin-bottom: 20px; padding-top: 15px;">A good %s read</h1>
        <div class="amazon-book clearfix">
            <div class="amazon-title">
                <a href="%s" rel="nofollow" class="clearfix">
                    <img src="/media/%s" alt="%s" title="%s" />
                    %s
                </a>
            </div>
        </div>
        """ % (tag,
               ad.url,
               ad.image,
               ad.title,
               ad.title,
               ad.title)


########NEW FILE########
__FILENAME__ = views

########NEW FILE########
__FILENAME__ = handlers
from django.contrib.auth.models import User

from piston.handler import AnonymousBaseHandler, BaseHandler
from piston.utils import rc

from snippet.models import Snippet

from tagging.models import Tag, TaggedItem

from pygments import highlight
from pygments.lexers import get_lexer_by_name
from pygments.formatters import HtmlFormatter

class TagHandler(BaseHandler):

    def read(self, request, tag_id):
        try:
            tag = Tag.objects.get(id=tag_id)
        except:
            resp = rc.NOT_HERE
            resp.write(": Tag does not exist.")
            return resp
        
        snipts = TaggedItem.objects.get_by_model(Snippet.objects.filter(public='1'), tag)
        tag_count = snipts.count()
        snipt_ids = []
        
        for snipt in snipts:
            snipt_ids.append(snipt.id)
        
        users_with_tag = []
        users_tag_list = []
        
        for snipt in snipts:
            users_with_tag.append(snipt.user.id)
        
        users_with_tag = set(users_with_tag)
        
        for user in users_with_tag:
            users_tag_list.append(user)
        
        data = {
            'id': tag.id,
            'name': tag.name,
            'count': tag_count,
            'snipts': snipt_ids,
            'users_with_tag': users_tag_list
        }
        return data

class TagsHandler(BaseHandler):
    
    def read(self, request):
        tags = Tag.objects.usage_for_queryset(Snippet.objects.filter(public='1'), counts=True)
        tags_list = []
        for tag in tags:
            tags_list.append({
                'id': tag.id,
                'name': tag.name,
                'count': tag.count
            })
        data = {
            'tags': tags_list
        }
        return data

class UserHandler(BaseHandler):
    
    def read(self, request, username):
        try:
            user = User.objects.get(username=username)
        except:
            resp = rc.NOT_HERE
            resp.write(": User does not exist.")
            return resp
        
        snipts = Snippet.objects.filter(user=user.id, public='1')
        tags = Tag.objects.usage_for_queryset(snipts, counts=True)
        tags_list = []
        snipts_list = []
        
        for tag in tags:
            tags_list.append({'id': tag.id, 'name': tag.name, 'count': tag.count})
        
        for snipt in snipts:
            snipts_list.append(snipt.id)
        
        data = {
            'username': user.username,
            'id': user.id,
            'tags': tags_list,
            'snipts': snipts_list,
            'count': snipts.count()
        }
        return data

class SniptHandler(BaseHandler):
    
    def read(self, request, snipt_id):
        try:
            snipt = Snippet.objects.get(id=snipt_id)
        except:
            resp = rc.NOT_HERE
            resp.write(": Snipt does not exist.")
            return resp
    
        if snipt.public == False:
            resp = rc.FORBIDDEN
            resp.write(": You don\'t have permission to access this snipt.")
            return resp
    
        snipt_tags = Tag.objects.get_for_object(snipt)
        tags_list = []
    
        for tag in snipt_tags:
            tags_list.append({'id': tag.id, 'name': tag.name})
    
        try:
            style = request.GET['style']
        except:
            style = 'default'
    
        try:
            formatted_code = highlight(snipt.code.replace("\\\"","\\\\\""), get_lexer_by_name(snipt.lexer, encoding='UTF-8'), HtmlFormatter(style=style, noclasses=True))
        except:
            formatted_code = highlight(snipt.code.replace("\\\"","\\\\\""), get_lexer_by_name(snipt.lexer, encoding='UTF-8'), HtmlFormatter(style='default', noclasses=True))
    
        data = {
            'id': snipt.id,
            'code': snipt.code,
            'description': snipt.description,
            'created': snipt.created,
            'user': snipt.user.username,
            'tags': tags_list,
            'lexer': snipt.lexer,
            'public': snipt.public,
            'key': snipt.key,
            'slug': snipt.slug,
            'formatted_code': formatted_code,
        }
        return data


########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import *

from piston.authentication import HttpBasicAuthentication
from piston.resource import Resource

from snipt.api.handlers import *
from snipt.api.views import *

auth = HttpBasicAuthentication(realm="Snipt API")
ad = { 'authentication': auth }

tag_handler = Resource(TagHandler)
tags_handler = Resource(TagsHandler)
user_handler = Resource(UserHandler)
snipt_handler = Resource(SniptHandler)

urlpatterns = patterns('',
    (r'^/?$', home),
    url(r'^tags\.(?P<emitter_format>.+)$', tags_handler),
    url(r'^tags/(?P<tag_id>\d+)\.(?P<emitter_format>.+)$', tag_handler),
    url(r'^users/(?P<username>.+)\.(?P<emitter_format>.+)$', user_handler),
    url(r'^snipts/(?P<snipt_id>.+)\.(?P<emitter_format>.+)$', snipt_handler),
)

########NEW FILE########
__FILENAME__ = views
from django.shortcuts import render_to_response
from django.template import RequestContext

def home(request):
    api = True
    return render_to_response('api/home.html', locals(), context_instance=RequestContext(request))

########NEW FILE########
__FILENAME__ = debug_wsgi
import os
import sys
import site

parent = os.path.dirname
site_dir = parent(os.path.abspath(__file__))
project_dir = parent(parent(os.path.abspath(__file__)))

sys.path.insert(0, project_dir)
sys.path.insert(0, site_dir)

import local_settings
site.addsitedir(local_settings.VIRTUALENV_PATH)

from django.core.management import setup_environ
import settings
setup_environ(settings)

import django.core.handlers.wsgi
application = django.core.handlers.wsgi.WSGIHandler()

from werkzeug.debug import DebuggedApplication
application = DebuggedApplication(application, evalex=True)

def null_technical_500_response(request, exc_type, exc_value, tb):
    raise exc_type, exc_value, tb
from django.views import debug
debug.technical_500_response = null_technical_500_response

########NEW FILE########
__FILENAME__ = admin
# -*- coding: utf-8 -*-

from django.contrib import admin
from django_authopenid.models import UserAssociation


class UserAssociationAdmin(admin.ModelAdmin):
    """User association admin class"""
admin.site.register(UserAssociation, UserAssociationAdmin)
########NEW FILE########
__FILENAME__ = forms
# -*- coding: utf-8 -*-
# Copyright (c) 2007, 2008, Benoît Chesneau
# 
# All rights reserved.
# 
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are
# met:
# 
#      * Redistributions of source code must retain the above copyright
#      * notice, this list of conditions and the following disclaimer.
#      * Redistributions in binary form must reproduce the above copyright
#      * notice, this list of conditions and the following disclaimer in the
#      * documentation and/or other materials provided with the
#      * distribution.  Neither the name of the <ORGANIZATION> nor the names
#      * of its contributors may be used to endorse or promote products
#      * derived from this software without specific prior written
#      * permission.
# 
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS
# IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO,
# THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR
# PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR
# CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL,
# EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
# PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA,
# OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF
# THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.


from django import forms
from django.contrib.auth.models import User
from django.contrib.auth import authenticate
from django.utils.translation import ugettext as _
from django.conf import settings

import re


# needed for some linux distributions like debian
try:
    from openid.yadis import xri
except ImportError:
    from yadis import xri
    
from django_authopenid.util import clean_next

__all__ = ['OpenidSigninForm', 'OpenidAuthForm', 'OpenidVerifyForm',
        'OpenidRegisterForm', 'RegistrationForm', 'ChangepwForm',
        'ChangeemailForm', 'EmailPasswordForm', 'DeleteForm',
        'ChangeOpenidForm', 'ChangeEmailForm', 'ChangepwForm']

class OpenidSigninForm(forms.Form):
    """ signin form """
    openid_url = forms.CharField(max_length=255, 
            widget=forms.widgets.TextInput(attrs={'class': 'required openid'}))
    next = forms.CharField(max_length=255, widget=forms.HiddenInput(), 
            required=False)

    def clean_openid_url(self):
        """ test if openid is accepted """
        if 'openid_url' in self.cleaned_data:
            openid_url = self.cleaned_data['openid_url']
            if xri.identifierScheme(openid_url) == 'XRI' and getattr(
                settings, 'OPENID_DISALLOW_INAMES', False
                ):
                raise forms.ValidationError(_('i-names are not supported'))
            return self.cleaned_data['openid_url']

    def clean_next(self):
        """ validate next """
        if 'next' in self.cleaned_data and self.cleaned_data['next'] != "":
            self.cleaned_data['next'] = clean_next(self.cleaned_data['next'])
            return self.cleaned_data['next']


attrs_dict = { 'class': 'required login' }
username_re = re.compile(r'^\w+$')

class OpenidAuthForm(forms.Form):
    """ legacy account signin form """
    next = forms.CharField(max_length=255, widget=forms.HiddenInput(), 
            required=False)
    username = forms.CharField(max_length=30,  
            widget=forms.widgets.TextInput(attrs=attrs_dict))
    password = forms.CharField(max_length=128, 
            widget=forms.widgets.PasswordInput(attrs=attrs_dict))
       
    def __init__(self, data=None, files=None, auto_id='id_%s',
            prefix=None, initial=None): 
        super(OpenidAuthForm, self).__init__(data, files, auto_id,
                prefix, initial)
        self.user_cache = None
            
    def clean_username(self):
        """ validate username and test if it exists."""
        if 'username' in self.cleaned_data and \
                'openid_url' not in self.cleaned_data:
            if not username_re.search(self.cleaned_data['username']):
                raise forms.ValidationError(_("Usernames can only contain \
                    letters, numbers and underscores"))
            try:
                user = User.objects.get(
                        username__exact = self.cleaned_data['username']
                )
            except User.DoesNotExist:
                raise forms.ValidationError(_("This username does not exist \
                    in our database. Please choose another."))
            except User.MultipleObjectsReturned:
                raise forms.ValidationError(u'There is already more than one \
                    account registered with that username. Please try \
                    another.')
            return self.cleaned_data['username']

    def clean_password(self):
        """" test if password is valid for this username """
        if 'username' in self.cleaned_data and \
                'password' in self.cleaned_data:
            self.user_cache =  authenticate(
                    username=self.cleaned_data['username'], 
                    password=self.cleaned_data['password']
            )
            if self.user_cache is None:
                raise forms.ValidationError(_("Please enter a valid \
                    username and password. Note that both fields are \
                    case-sensitive."))
            elif self.user_cache.is_active == False:
                raise forms.ValidationError(_("This account is inactive."))
            return self.cleaned_data['password']

    def clean_next(self):
        """ validate next url """
        if 'next' in self.cleaned_data and \
                self.cleaned_data['next'] != "":
            self.cleaned_data['next'] = clean_next(self.cleaned_data['next'])
            return self.cleaned_data['next']
            
    def get_user(self):
        """ get authenticated user """
        return self.user_cache
            

class OpenidRegisterForm(forms.Form):
    """ openid signin form """
    next = forms.CharField(max_length=255, widget=forms.HiddenInput(), 
            required=False)
    username = forms.CharField(max_length=30, 
            widget=forms.widgets.TextInput(attrs=attrs_dict))
    email = forms.EmailField(widget=forms.TextInput(attrs=dict(attrs_dict, 
        maxlength=200)), label=u'Email address')
    
    def clean_username(self):
        """ test if username is valid and exist in database """
        if 'username' in self.cleaned_data:
            if not username_re.search(self.cleaned_data['username']):
                raise forms.ValidationError(_("Usernames can only contain \
                    letters, numbers and underscores"))
            try:
                user = User.objects.get(
                        username__exact = self.cleaned_data['username']
                        )
            except User.DoesNotExist:
                return self.cleaned_data['username']
            except User.MultipleObjectsReturned:
                raise forms.ValidationError(u'There is already more than one \
                    account registered with that username. Please try \
                    another.')
            raise forms.ValidationError(_("This username is already \
                taken. Please choose another."))
            
    def clean_email(self):
        """For security reason one unique email in database"""
        if 'email' in self.cleaned_data:
            try:
                user = User.objects.get(email = self.cleaned_data['email'])
            except User.DoesNotExist:
                return self.cleaned_data['email']
            except User.MultipleObjectsReturned:
                raise forms.ValidationError(u'There is already more than one \
                    account registered with that e-mail address. Please try \
                    another.')
            raise forms.ValidationError(_("This email is already \
                registered in our database. Please choose another."))
 
    
class OpenidVerifyForm(forms.Form):
    """ openid verify form (associate an openid with an account) """
    next = forms.CharField(max_length=255, widget = forms.HiddenInput(), 
            required=False)
    username = forms.CharField(max_length=30, 
            widget=forms.widgets.TextInput(attrs=attrs_dict))
    password = forms.CharField(max_length=128, 
            widget=forms.widgets.PasswordInput(attrs=attrs_dict))
    
    def __init__(self, data=None, files=None, auto_id='id_%s',
            prefix=None, initial=None): 
        super(OpenidVerifyForm, self).__init__(data, files, auto_id,
                prefix, initial)
        self.user_cache = None

    def clean_username(self):
        """ validate username """
        if 'username' in self.cleaned_data:
            if not username_re.search(self.cleaned_data['username']):
                raise forms.ValidationError(_("Usernames can only contain \
                    letters, numbers and underscores"))
            try:
                user = User.objects.get(
                        username__exact = self.cleaned_data['username']
                )
            except User.DoesNotExist:
                raise forms.ValidationError(_("This username don't exist. \
                        Please choose another."))
            except User.MultipleObjectsReturned:
                raise forms.ValidationError(u'Somehow, that username is in \
                    use for multiple accounts. Please contact us to get this \
                    problem resolved.')
            return self.cleaned_data['username']
            
    def clean_password(self):
        """ test if password is valid for this user """
        if 'username' in self.cleaned_data and \
                'password' in self.cleaned_data:
            self.user_cache =  authenticate(
                    username = self.cleaned_data['username'], 
                    password = self.cleaned_data['password']
            )
            if self.user_cache is None:
                raise forms.ValidationError(_("Please enter a valid \
                    username and password. Note that both fields are \
                    case-sensitive."))
            elif self.user_cache.is_active == False:
                raise forms.ValidationError(_("This account is inactive."))
            return self.cleaned_data['password']
            
    def get_user(self):
        """ get authenticated user """
        return self.user_cache


attrs_dict = { 'class': 'required' }
username_re = re.compile(r'^\w+$')

class RegistrationForm(forms.Form):
    """ legacy registration form """

    next = forms.CharField(max_length=255, widget=forms.HiddenInput(), 
            required=False)
    username = forms.CharField(max_length=30,
            widget=forms.TextInput(attrs=attrs_dict),
            label=u'Username')
    email = forms.EmailField(widget=forms.TextInput(attrs=dict(attrs_dict,
            maxlength=200)), label=u'Email address')
    password1 = forms.CharField(widget=forms.PasswordInput(attrs=attrs_dict),
            label=u'Password')
    password2 = forms.CharField(widget=forms.PasswordInput(attrs=attrs_dict),
            label=u'Password (again, to catch typos)')

    def clean_username(self):
        """
        Validates that the username is alphanumeric and is not already
        in use.
        
        """
        if 'username' in self.cleaned_data:
            if not username_re.search(self.cleaned_data['username']):
                raise forms.ValidationError(u'Usernames can only contain \
                        letters, numbers and underscores')
            try:
                user = User.objects.get(
                        username__exact = self.cleaned_data['username']
                )

            except User.DoesNotExist:
                return self.cleaned_data['username']
            except User.MultipleObjectsReturned:
                raise forms.ValidationError(u'Somehow, that username is in \
                    use for multiple accounts. Please contact us to get this \
                    problem resolved.')
            raise forms.ValidationError(u'This username is already taken. \
                    Please choose another.')

    def clean_email(self):
        """ validate if email exist in database
        :return: raise error if it exist """
        if 'email' in self.cleaned_data:
            try:
                user = User.objects.get(email = self.cleaned_data['email'])
            except User.DoesNotExist:
                return self.cleaned_data['email']
            except User.MultipleObjectsReturned:
                raise forms.ValidationError(u'There is already more than one \
                    account registered with that e-mail address. Please try \
                    another.')
            raise forms.ValidationError(u'This email is already registered \
                    in our database. Please choose another.')
        return self.cleaned_data['email']
    
    def clean_password2(self):
        """
        Validates that the two password inputs match.
        
        """
        if 'password1' in self.cleaned_data and \
                'password2' in self.cleaned_data and \
                self.cleaned_data['password1'] == \
                self.cleaned_data['password2']:
            return self.cleaned_data['password2']
        raise forms.ValidationError(u'You must type the same password each \
                time')


class ChangepwForm(forms.Form):
    """ change password form """
    oldpw = forms.CharField(widget=forms.PasswordInput(attrs=attrs_dict))
    password1 = forms.CharField(widget=forms.PasswordInput(attrs=attrs_dict))
    password2 = forms.CharField(widget=forms.PasswordInput(attrs=attrs_dict))

    def __init__(self, data=None, user=None, *args, **kwargs):
        if user is None:
            raise TypeError("Keyword argument 'user' must be supplied")
        super(ChangepwForm, self).__init__(data, *args, **kwargs)
        self.user = user

    def clean_oldpw(self):
        """ test old password """
        if not self.user.check_password(self.cleaned_data['oldpw']):
            raise forms.ValidationError(_("Old password is incorrect. \
                    Please enter the correct password."))
        return self.cleaned_data['oldpw']
    
    def clean_password2(self):
        """
        Validates that the two password inputs match.
        """
        if 'password1' in self.cleaned_data and \
                'password2' in self.cleaned_data and \
           self.cleaned_data['password1'] == self.cleaned_data['password2']:
            return self.cleaned_data['password2']
        raise forms.ValidationError(_("new passwords do not match"))
        
        
class ChangeemailForm(forms.Form):
    """ change email form """
    email = forms.EmailField(widget=forms.TextInput(attrs=dict(attrs_dict, 
        maxlength=200)), label=u'Email address')
    password = forms.CharField(widget=forms.PasswordInput(attrs=attrs_dict))

    def __init__(self, data=None, files=None, auto_id='id_%s', prefix=None, \
            initial=None, user=None):
        if user is None:
            raise TypeError("Keyword argument 'user' must be supplied")
        super(ChangeemailForm, self).__init__(data, files, auto_id, 
                prefix, initial)
        self.test_openid = False
        self.user = user
        
        
    def clean_email(self):
        """ check if email don't exist """
        if 'email' in self.cleaned_data:
            if self.user.email != self.cleaned_data['email']:
                try:
                    user = User.objects.get(email = self.cleaned_data['email'])
                except User.DoesNotExist:
                    return self.cleaned_data['email']
                except User.MultipleObjectsReturned:
                    raise forms.ValidationError(u'There is already more than one \
                        account registered with that e-mail address. Please try \
                        another.')
                raise forms.ValidationError(u'This email is already registered \
                    in our database. Please choose another.')
        return self.cleaned_data['email']
        

    def clean_password(self):
        """ check if we have to test a legacy account or not """
        if 'password' in self.cleaned_data:
            if not self.user.check_password(self.cleaned_data['password']):
                self.test_openid = True
        return self.cleaned_data['password']
                
class ChangeopenidForm(forms.Form):
    """ change openid form """
    openid_url = forms.CharField(max_length=255,
            widget=forms.TextInput(attrs={'class': "required" }))

    def __init__(self, data=None, user=None, *args, **kwargs):
        if user is None:
            raise TypeError("Keyword argument 'user' must be supplied")
        super(ChangeopenidForm, self).__init__(data, *args, **kwargs)
        self.user = user

class DeleteForm(forms.Form):
    """ confirm form to delete an account """
    confirm = forms.CharField(widget=forms.CheckboxInput(attrs=attrs_dict))
    password = forms.CharField(widget=forms.PasswordInput(attrs=attrs_dict))

    def __init__(self, data=None, files=None, auto_id='id_%s',
            prefix=None, initial=None, user=None):
        super(DeleteForm, self).__init__(data, files, auto_id, prefix, initial)
        self.test_openid = False
        self.user = user

    def clean_password(self):
        """ check if we have to test a legacy account or not """
        if 'password' in self.cleaned_data:
            if not self.user.check_password(self.cleaned_data['password']):
                self.test_openid = True
        return self.cleaned_data['password']


class EmailPasswordForm(forms.Form):
    """ send new password form """
    username = forms.CharField(max_length=30,
            widget=forms.TextInput(attrs={'class': "required" }))

    def __init__(self, data=None, files=None, auto_id='id_%s', prefix=None, 
            initial=None):
        super(EmailPasswordForm, self).__init__(data, files, auto_id, 
                prefix, initial)
        self.user_cache = None


    def clean_username(self):
        """ get user for this username """
        if 'username' in self.cleaned_data:
            try:
                self.user_cache = User.objects.get(
                        username = self.cleaned_data['username'])
            except:
                raise forms.ValidationError(_("Incorrect username."))
        return self.cleaned_data['username']

########NEW FILE########
__FILENAME__ = middleware
# -*- coding: utf-8 -*-
from django_authopenid import mimeparse
from django.http import HttpResponseRedirect
from django.core.urlresolvers import reverse

__all__ = ["OpenIDMiddleware"]

class OpenIDMiddleware(object):
    """
    Populate request.openid. This comes either from cookie or from
    session, depending on the presence of OPENID_USE_SESSIONS.
    """
    def process_request(self, request):
        request.openid = request.session.get('openid', None)
    
    def process_response(self, request, response):
        if response.status_code != 200 or len(response.content) < 200:
            return response
        path = request.get_full_path()
        if path == "/" and request.META.has_key('HTTP_ACCEPT') and \
                mimeparse.best_match(['text/html', 'application/xrds+xml'], 
                    request.META['HTTP_ACCEPT']) == 'application/xrds+xml':
            return HttpResponseRedirect(reverse('yadis_xrdf'))
        return response
########NEW FILE########
__FILENAME__ = mimeparse
"""MIME-Type Parser

This module provides basic functions for handling mime-types. It can handle
matching mime-types against a list of media-ranges. See section 14.1 of 
the HTTP specification [RFC 2616] for a complete explaination.

   http://www.w3.org/Protocols/rfc2616/rfc2616-sec14.html#sec14.1

Contents:
    - parse_mime_type():   Parses a mime-type into it's component parts.
    - parse_media_range(): Media-ranges are mime-types with wild-cards and a 'q' quality parameter.
    - quality():           Determines the quality ('q') of a mime-type when compared against a list of media-ranges.
    - quality_parsed():    Just like quality() except the second parameter must be pre-parsed.
    - best_match():        Choose the mime-type with the highest quality ('q') from a list of candidates. 
"""

__version__ = "0.1.1"
__author__ = 'Joe Gregorio'
__email__ = "joe@bitworking.org"
__credits__ = ""

def parse_mime_type(mime_type):
    """Carves up a mime_type and returns a tuple of the
       (type, subtype, params) where 'params' is a dictionary
       of all the parameters for the media range.
       For example, the media range 'application/xhtml;q=0.5' would
       get parsed into:

       ('application', 'xhtml', {'q', '0.5'})
       """
    parts = mime_type.split(";")
    params = dict([tuple([s.strip() for s in param.split("=")])\
            for param in parts[1:] ])
    (type, subtype) = parts[0].split("/")
    return (type.strip(), subtype.strip(), params)

def parse_media_range(range):
    """Carves up a media range and returns a tuple of the
       (type, subtype, params) where 'params' is a dictionary
       of all the parameters for the media range.
       For example, the media range 'application/*;q=0.5' would
       get parsed into:

       ('application', '*', {'q', '0.5'})

       In addition this function also guarantees that there 
       is a value for 'q' in the params dictionary, filling it
       in with a proper default if necessary.
       """
    (type, subtype, params) = parse_mime_type(range)
    if not params.has_key('q') or not params['q'] or \
            not float(params['q']) or float(params['q']) > 1\
            or float(params['q']) < 0:
        params['q'] = '1'
    return (type, subtype, params)

def quality_parsed(mime_type, parsed_ranges):
    """Find the best match for a given mime_type against 
       a list of media_ranges that have already been 
       parsed by parse_media_range(). Returns the 
       'q' quality parameter of the best match, 0 if no
       match was found. This function bahaves the same as quality()
       except that 'parsed_ranges' must be a list of
       parsed media ranges. """
    best_fitness = -1 
    best_match = ""
    best_fit_q = 0
    (target_type, target_subtype, target_params) =\
            parse_media_range(mime_type)
    for (type, subtype, params) in parsed_ranges:
        param_matches = reduce(lambda x, y: x+y, [1 for (key, value) in \
                target_params.iteritems() if key != 'q' and \
                params.has_key(key) and value == params[key]], 0)
        if (type == target_type or type == '*' or target_type == '*') and \
                (subtype == target_subtype or subtype == '*' or target_subtype == '*'):
            fitness = (type == target_type) and 100 or 0
            fitness += (subtype == target_subtype) and 10 or 0
            fitness += param_matches
            if fitness > best_fitness:
                best_fitness = fitness
                best_fit_q = params['q']
            
    return float(best_fit_q)
    
def quality(mime_type, ranges):
    """Returns the quality 'q' of a mime_type when compared
    against the media-ranges in ranges. For example:

    >>> quality('text/html','text/*;q=0.3, text/html;q=0.7, text/html;level=1, text/html;level=2;q=0.4, */*;q=0.5')
    0.7
    
    """ 
    parsed_ranges = [parse_media_range(r) for r in ranges.split(",")]
    return quality_parsed(mime_type, parsed_ranges)

def best_match(supported, header):
    """Takes a list of supported mime-types and finds the best
    match for all the media-ranges listed in header. The value of
    header must be a string that conforms to the format of the 
    HTTP Accept: header. The value of 'supported' is a list of
    mime-types.
    
    >>> best_match(['application/xbel+xml', 'text/xml'], 'text/*;q=0.5,*/*; q=0.1')
    'text/xml'
    """
    parsed_header = [parse_media_range(r) for r in header.split(",")]
    weighted_matches = [(quality_parsed(mime_type, parsed_header), mime_type)\
            for mime_type in supported]
    weighted_matches.sort()
    return weighted_matches[-1][0] and weighted_matches[-1][1] or ''

if __name__ == "__main__":
    import unittest

    class TestMimeParsing(unittest.TestCase):

        def test_parse_media_range(self):
            self.assert_(('application', 'xml', {'q': '1'}) == parse_media_range('application/xml;q=1'))
            self.assertEqual(('application', 'xml', {'q': '1'}), parse_media_range('application/xml'))
            self.assertEqual(('application', 'xml', {'q': '1'}), parse_media_range('application/xml;q='))
            self.assertEqual(('application', 'xml', {'q': '1'}), parse_media_range('application/xml ; q='))
            self.assertEqual(('application', 'xml', {'q': '1', 'b': 'other'}), parse_media_range('application/xml ; q=1;b=other'))
            self.assertEqual(('application', 'xml', {'q': '1', 'b': 'other'}), parse_media_range('application/xml ; q=2;b=other'))

        def test_rfc_2616_example(self):
            accept = "text/*;q=0.3, text/html;q=0.7, text/html;level=1, text/html;level=2;q=0.4, */*;q=0.5"
            self.assertEqual(1, quality("text/html;level=1", accept))
            self.assertEqual(0.7, quality("text/html", accept))
            self.assertEqual(0.3, quality("text/plain", accept))
            self.assertEqual(0.5, quality("image/jpeg", accept))
            self.assertEqual(0.4, quality("text/html;level=2", accept))
            self.assertEqual(0.7, quality("text/html;level=3", accept))

        def test_best_match(self):
            mime_types_supported = ['application/xbel+xml', 'application/xml']
            # direct match
            self.assertEqual(best_match(mime_types_supported, 'application/xbel+xml'), 'application/xbel+xml')
            # direct match with a q parameter
            self.assertEqual(best_match(mime_types_supported, 'application/xbel+xml; q=1'), 'application/xbel+xml')
            # direct match of our second choice with a q parameter
            self.assertEqual(best_match(mime_types_supported, 'application/xml; q=1'), 'application/xml')
            # match using a subtype wildcard
            self.assertEqual(best_match(mime_types_supported, 'application/*; q=1'), 'application/xml')
            # match using a type wildcard
            self.assertEqual(best_match(mime_types_supported, '*/*'), 'application/xml')

            mime_types_supported = ['application/xbel+xml', 'text/xml']
            # match using a type versus a lower weighted subtype
            self.assertEqual(best_match(mime_types_supported, 'text/*;q=0.5,*/*; q=0.1'), 'text/xml')
            # fail to match anything
            self.assertEqual(best_match(mime_types_supported, 'text/html,application/atom+xml; q=0.9'), '')

        def test_support_wildcards(self):
            mime_types_supported = ['image/*', 'application/xml']
            # match using a type wildcard
            self.assertEqual(best_match(mime_types_supported, 'image/png'), 'image/*')
            # match using a wildcard for both requested and supported 
            self.assertEqual(best_match(mime_types_supported, 'image/*'), 'image/*')

    unittest.main() 
########NEW FILE########
__FILENAME__ = models
# -*- coding: utf-8 -*-
from django.conf import settings
from django.contrib.auth.models import User
from django.db import models

import md5, random, sys, os, time

__all__ = ['Nonce', 'Association', 'UserAssociation', 
        'UserPasswordQueueManager', 'UserPasswordQueue']

class Nonce(models.Model):
    """ openid nonce """
    server_url = models.CharField(max_length=255)
    timestamp = models.IntegerField()
    salt = models.CharField(max_length=40)
    
    def __unicode__(self):
        return u"Nonce: %s" % self.id

    
class Association(models.Model):
    """ association openid url and lifetime """
    server_url = models.TextField(max_length=2047)
    handle = models.CharField(max_length=255)
    secret = models.TextField(max_length=255) # Stored base64 encoded
    issued = models.IntegerField()
    lifetime = models.IntegerField()
    assoc_type = models.TextField(max_length=64)
    
    def __unicode__(self):
        return u"Association: %s, %s" % (self.server_url, self.handle)

class UserAssociation(models.Model):
    """ 
    model to manage association between openid and user 
    """
    openid_url = models.CharField(blank=False, max_length=255)
    user = models.ForeignKey(User, unique=True)
    
    def __unicode__(self):
        return "Openid %s with user %s" % (self.openid_url, self.user)

class UserPasswordQueueManager(models.Manager):
    """ manager for UserPasswordQueue object """
    def get_new_confirm_key(self):
        "Returns key that isn't being used."
        # The random module is seeded when this Apache child is created.
        # Use SECRET_KEY as added salt.
        while 1:
            confirm_key = md5.new("%s%s%s%s" % (
                random.randint(0, sys.maxint - 1), os.getpid(),
                time.time(), settings.SECRET_KEY)).hexdigest()
            try:
                self.get(confirm_key=confirm_key)
            except self.model.DoesNotExist:
                break
        return confirm_key


class UserPasswordQueue(models.Model):
    """
    model for new password queue.
    """
    user = models.ForeignKey(User, unique=True)
    new_password = models.CharField(max_length=30)
    confirm_key = models.CharField(max_length=40)

    objects = UserPasswordQueueManager()

    def __unicode__(self):
        return self.user.username

########NEW FILE########
__FILENAME__ = urls
# -*- coding: utf-8 -*-
from django.conf.urls.defaults import patterns, url
from django.utils.translation import ugettext as _

urlpatterns = patterns('django_authopenid.views',
    # yadis rdf
    url(r'^yadis.xrdf$', 'xrdf', name='yadis_xrdf'),
     # manage account registration
    url(r'^%s$' % _('signin/'), 'signin', name='user_signin'),
    url(r'^%s$' % _('signout/'), 'signout', name='user_signout'),
    url(r'^%s%s$' % (_('signin/'), _('complete/')), 'complete_signin', 
        name='user_complete_signin'),
    url(r'^%s$' % _('register/'), 'register', name='user_register'),
    url(r'^%s$' % _('signup/'), 'signup', name='user_signup'),
    url(r'^%s$' % _('sendpw/'), 'sendpw', name='user_sendpw'),
    url(r'^%s%s$' % (_('password/'), _('confirm/')), 'confirmchangepw', 
        name='user_confirmchangepw'),

    # manage account settings
    url(r'^$', 'account_settings', name='user_account_settings'),
    url(r'^%s$' % _('password/'), 'changepw', name='user_changepw'),
    url(r'^%s$' % _('email/'), 'changeemail', name='user_changeemail'),
    url(r'^%s$' % _('openid/'), 'changeopenid', name='user_changeopenid'),
    url(r'^%s$' % _('delete/'), 'delete', name='user_delete'),
)

########NEW FILE########
__FILENAME__ = util
# -*- coding: utf-8 -*-
from openid.store.interface import OpenIDStore
from openid.association import Association as OIDAssociation
from openid.extensions import sreg
import openid.store

from django.db.models.query import Q
from django.conf import settings
from django.http import str_to_unicode


# needed for some linux distributions like debian
try:
    from openid.yadis import xri
except:
    from yadis import xri

import time, base64, md5, operator
import urllib

from models import Association, Nonce

__all__ = ['OpenID', 'DjangoOpenIDStore', 'from_openid_response', 'clean_next']

DEFAULT_NEXT = getattr(settings, 'OPENID_REDIRECT_NEXT', '/')
def clean_next(next):
    if next is None:
        return DEFAULT_NEXT
    next = str_to_unicode(urllib.unquote(next), 'utf-8')
    next = next.strip()
    if next.startswith('/'):
        return next
    return DEFAULT_NEXT

class OpenID:
    def __init__(self, openid_, issued, attrs=None, sreg_=None):
        self.openid = openid_
        self.issued = issued
        self.attrs = attrs or {}
        self.sreg = sreg_ or {}
        self.is_iname = (xri.identifierScheme(openid_) == 'XRI')
    
    def __repr__(self):
        return '<OpenID: %s>' % self.openid
    
    def __str__(self):
        return self.openid

class DjangoOpenIDStore(OpenIDStore):
    def __init__(self):
        self.max_nonce_age = 6 * 60 * 60 # Six hours
    
    def storeAssociation(self, server_url, association):
        assoc = Association(
            server_url = server_url,
            handle = association.handle,
            secret = base64.encodestring(association.secret),
            issued = association.issued,
            lifetime = association.issued,
            assoc_type = association.assoc_type
        )
        assoc.save()
    
    def getAssociation(self, server_url, handle=None):
        assocs = []
        if handle is not None:
            assocs = Association.objects.filter(
                server_url = server_url, handle = handle
            )
        else:
            assocs = Association.objects.filter(
                server_url = server_url
            )
        if not assocs:
            return None
        associations = []
        for assoc in assocs:
            association = OIDAssociation(
                assoc.handle, base64.decodestring(assoc.secret), assoc.issued,
                assoc.lifetime, assoc.assoc_type
            )
            if association.getExpiresIn() == 0:
                self.removeAssociation(server_url, assoc.handle)
            else:
                associations.append((association.issued, association))
        if not associations:
            return None
        return associations[-1][1]
    
    def removeAssociation(self, server_url, handle):
        assocs = list(Association.objects.filter(
            server_url = server_url, handle = handle
        ))
        assocs_exist = len(assocs) > 0
        for assoc in assocs:
            assoc.delete()
        return assocs_exist

    def useNonce(self, server_url, timestamp, salt):
        if abs(timestamp - time.time()) > openid.store.nonce.SKEW:
            return False
        
        query = [
                Q(server_url__exact=server_url),
                Q(timestamp__exact=timestamp),
                Q(salt__exact=salt),
        ]
        try:
            ononce = Nonce.objects.get(reduce(operator.and_, query))
        except Nonce.DoesNotExist:
            ononce = Nonce(
                    server_url=server_url,
                    timestamp=timestamp,
                    salt=salt
            )
            ononce.save()
            return True
        
        ononce.delete()

        return False
   
    def cleanupNonce(self):
        Nonce.objects.filter(timestamp<int(time.time()) - nonce.SKEW).delete()

    def cleanupAssociations(self):
        Association.objects.extra(where=['issued + lifetimeint<(%s)' % time.time()]).delete()

    def getAuthKey(self):
        # Use first AUTH_KEY_LEN characters of md5 hash of SECRET_KEY
        return md5.new(settings.SECRET_KEY).hexdigest()[:self.AUTH_KEY_LEN]
    
    def isDumb(self):
        return False

def from_openid_response(openid_response):
    """ return openid object from response """
    issued = int(time.time())
    sreg_resp = sreg.SRegResponse.fromSuccessResponse(openid_response) \
            or []
    
    return OpenID(
        openid_response.identity_url, issued, openid_response.signed_fields, 
         dict(sreg_resp)
    )

########NEW FILE########
__FILENAME__ = views
# -*- coding: utf-8 -*-
# Copyright (c) 2007, 2008, Benoît Chesneau
# Copyright (c) 2007 Simon Willison, original work on django-openid
# 
# All rights reserved.
# 
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are
# met:
# 
#      * Redistributions of source code must retain the above copyright
#      * notice, this list of conditions and the following disclaimer.
#      * Redistributions in binary form must reproduce the above copyright
#      * notice, this list of conditions and the following disclaimer in the
#      * documentation and/or other materials provided with the
#      * distribution.  Neither the name of the <ORGANIZATION> nor the names
#      * of its contributors may be used to endorse or promote products
#      * derived from this software without specific prior written
#      * permission.
# 
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS
# IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO,
# THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR
# PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR
# CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL,
# EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
# PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA,
# OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF
# THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from django.http import HttpResponseRedirect, get_host
from django.shortcuts import render_to_response as render
from django.template import RequestContext, loader, Context
from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.core.urlresolvers import reverse
from django.utils.encoding import smart_unicode
from django.utils.html import escape
from django.utils.translation import ugettext as _
from django.contrib.sites.models import Site
from django.utils.http import urlquote_plus
from django.core.mail import send_mail

from openid.consumer.consumer import Consumer, \
    SUCCESS, CANCEL, FAILURE, SETUP_NEEDED
from openid.consumer.discover import DiscoveryFailure
from openid.extensions import sreg
# needed for some linux distributions like debian
try:
    from openid.yadis import xri
except ImportError:
    from yadis import xri

import re
import urllib


from django_authopenid.util import OpenID, DjangoOpenIDStore, from_openid_response, clean_next
from django_authopenid.models import UserAssociation, UserPasswordQueue
from django_authopenid.forms import OpenidSigninForm, OpenidAuthForm, OpenidRegisterForm, \
        OpenidVerifyForm, RegistrationForm, ChangepwForm, ChangeemailForm, \
        ChangeopenidForm, DeleteForm, EmailPasswordForm

def get_url_host(request):
    if request.is_secure():
        protocol = 'https'
    else:
        protocol = 'http'
    host = escape(get_host(request))
    return '%s://%s' % (protocol, host)

def get_full_url(request):
    return get_url_host(request) + request.get_full_path()



def ask_openid(request, openid_url, redirect_to, on_failure=None,
        sreg_request=None):
    """ basic function to ask openid and return response """
    on_failure = on_failure or signin_failure
    
    trust_root = getattr(
        settings, 'OPENID_TRUST_ROOT', get_url_host(request) + '/'
    )
    if xri.identifierScheme(openid_url) == 'XRI' and getattr(
            settings, 'OPENID_DISALLOW_INAMES', False
    ):
        msg = _("i-names are not supported")
        return on_failure(request, msg)
    consumer = Consumer(request.session, DjangoOpenIDStore())
    try:
        auth_request = consumer.begin(openid_url)
    except DiscoveryFailure:
        msg = _("The OpenID %s was invalid" % openid_url)
        return on_failure(request, msg)

    if sreg_request:
        auth_request.addExtension(sreg_request)
    redirect_url = auth_request.redirectURL(trust_root, redirect_to)
    return HttpResponseRedirect(redirect_url)

def complete(request, on_success=None, on_failure=None, return_to=None):
    """ complete openid signin """
    on_success = on_success or default_on_success
    on_failure = on_failure or default_on_failure
    
    consumer = Consumer(request.session, DjangoOpenIDStore())
    # make sure params are encoded in utf8
    params = dict((k,smart_unicode(v)) for k, v in request.GET.items())
    openid_response = consumer.complete(params, return_to)
            
    
    if openid_response.status == SUCCESS:
        return on_success(request, openid_response.identity_url,
                openid_response)
    elif openid_response.status == CANCEL:
        return on_failure(request, 'The request was canceled')
    elif openid_response.status == FAILURE:
        return on_failure(request, openid_response.message)
    elif openid_response.status == SETUP_NEEDED:
        return on_failure(request, 'Setup needed')
    else:
        assert False, "Bad openid status: %s" % openid_response.status

def default_on_success(request, identity_url, openid_response):
    """ default action on openid signin success """
    request.session['openid'] = from_openid_response(openid_response)
    return HttpResponseRedirect(clean_next(request.GET.get('next')))

def default_on_failure(request, message):
    """ default failure action on signin """
    return render('openid_failure.html', {
        'message': message
    })


def not_authenticated(func):
    """ decorator that redirect user to next page if
    he is already logged."""
    def decorated(request, *args, **kwargs):
        if request.user.is_authenticated():
            next = request.GET.get("next", "/")
            return HttpResponseRedirect(next)
        return func(request, *args, **kwargs)
    return decorated

@not_authenticated
def signin(request):
    """
    signin page. It manage the legacy authentification (user/password) 
    and authentification with openid.

    url: /signin/
    
    template : authopenid/signin.htm
    """

    on_failure = signin_failure
    next = clean_next(request.GET.get('next'))

    form_signin = OpenidSigninForm(initial={'next':next})
    form_auth = OpenidAuthForm(initial={'next':next})

    if request.POST:   
        if 'bsignin' in request.POST.keys():
            form_signin = OpenidSigninForm(request.POST)
            if form_signin.is_valid():
                next = clean_next(form_signin.cleaned_data.get('next'))
                sreg_req = sreg.SRegRequest(optional=['nickname', 'email'])
                redirect_to = "%s%s?%s" % (
                        get_url_host(request),
                        reverse('user_complete_signin'), 
                        urllib.urlencode({'next':next})
                )

                return ask_openid(request, 
                        form_signin.cleaned_data['openid_url'], 
                        redirect_to, 
                        on_failure=signin_failure, 
                        sreg_request=sreg_req)

        elif 'blogin' in request.POST.keys():
            # perform normal django authentification
            form_auth = OpenidAuthForm(request.POST)
            if form_auth.is_valid():
                user_ = form_auth.get_user()
                login(request, user_)
                next = clean_next(form_auth.cleaned_data.get('next'))
                return HttpResponseRedirect(next)


    return render('authopenid/signin.html', {
        'form1': form_auth,
        'form2': form_signin,
        'msg':  request.GET.get('msg',''),
        'sendpw_url': reverse('user_sendpw'),
    }, context_instance=RequestContext(request))

def complete_signin(request):
    """ in case of complete signin with openid """
    return complete(request, signin_success, signin_failure,
            get_url_host(request) + reverse('user_complete_signin'))


def signin_success(request, identity_url, openid_response):
    """
    openid signin success.

    If the openid is already registered, the user is redirected to 
    url set par next or in settings with OPENID_REDIRECT_NEXT variable.
    If none of these urls are set user is redirectd to /.

    if openid isn't registered user is redirected to register page.
    """

    openid_ = from_openid_response(openid_response)
    request.session['openid'] = openid_
    try:
        rel = UserAssociation.objects.get(openid_url__exact = str(openid_))
    except:
        # try to register this new user
        return register(request)
    user_ = rel.user
    if user_.is_active:
        user_.backend = "django.contrib.auth.backends.ModelBackend"
        login(request, user_)
        
    next = clean_next(request.GET.get('next'))
    return HttpResponseRedirect(next)

def is_association_exist(openid_url):
    """ test if an openid is already in database """
    is_exist = True
    try:
        uassoc = UserAssociation.objects.get(openid_url__exact = openid_url)
    except:
        is_exist = False
    return is_exist

@not_authenticated
def register(request):
    """
    register an openid.

    If user is already a member he can associate its openid with 
    its account.

    A new account could also be created and automaticaly associated
    to the openid.

    url : /complete/

    template : authopenid/complete.html
    """

    is_redirect = False
    next = clean_next(request.GET.get('next'))
    openid_ = request.session.get('openid', None)
    if not openid_:
        return HttpResponseRedirect(reverse('user_signin') + next)

    nickname = openid_.sreg.get('nickname', '')
    email = openid_.sreg.get('email', '')
    
    form1 = OpenidRegisterForm(initial={
        'next': next,
        'username': nickname,
        'email': email,
    }) 
    form2 = OpenidVerifyForm(initial={
        'next': next,
        'username': nickname,
    })
    
    if request.POST:
        just_completed = False
        if 'bnewaccount' in request.POST.keys():
            form1 = OpenidRegisterForm(request.POST)
            if form1.is_valid():
                next = clean_next(form1.cleaned_data.get('next'))
                is_redirect = True
                tmp_pwd = User.objects.make_random_password()
                user_ = User.objects.create_user(form1.cleaned_data['username'],
                         form1.cleaned_data['email'], tmp_pwd)
                
                # make association with openid
                uassoc = UserAssociation(openid_url=str(openid_),
                        user_id=user_.id)
                uassoc.save()
                    
                # login 
                user_.backend = "django.contrib.auth.backends.ModelBackend"
                login(request, user_)
        elif 'bverify' in request.POST.keys():
            form2 = OpenidVerifyForm(request.POST)
            if form2.is_valid():
                is_redirect = True
                next = clean_next(form2.cleaned_data.get('next'))
                user_ = form2.get_user()

                uassoc = UserAssociation(openid_url=str(openid_),
                        user_id=user_.id)
                uassoc.save()
                login(request, user_)
        
        # redirect, can redirect only if forms are valid.
        if is_redirect:
            return HttpResponseRedirect(next) 
    
    return render('authopenid/complete.html', {
        'form1': form1,
        'form2': form2,
        'nickname': nickname,
        'email': email
    }, context_instance=RequestContext(request))

def signin_failure(request, message):
    """
    falure with openid signin. Go back to signin page.

    template : "authopenid/signin.html"
    """
    next = clean_next(request.GET.get('next'))
    form_signin = OpenidSigninForm(initial={'next': next})
    form_auth = OpenidAuthForm(initial={'next': next})

    return render('authopenid/signin.html', {
        'msg': message,
        'form1': form_auth,
        'form2': form_signin,
    }, context_instance=RequestContext(request))

@not_authenticated
def signup(request):
    """
    signup page. Create a legacy account

    url : /signup/"

    templates: authopenid/signup.html, authopenid/confirm_email.txt
    """
    action_signin = reverse('user_signin')
    next = clean_next(request.GET.get('next'))
    form = RegistrationForm(initial={'next':next})
    form_signin = OpenidSigninForm(initial={'next':next})
    
    if request.POST:
        form = RegistrationForm(request.POST)
        if form.is_valid():
            next = clean_next(form.cleaned_data.get('next'))
            user_ = User.objects.create_user( form.cleaned_data['username'],
                    form.cleaned_data['email'], form.cleaned_data['password1'])
           
            user_.backend = "django.contrib.auth.backends.ModelBackend"
            login(request, user_)
            
            # send email
            current_domain = Site.objects.get_current().domain
            subject = _("Welcome")
            message_template = loader.get_template(
                    'authopenid/confirm_email.txt'
            )
            message_context = Context({ 
                'site_url': 'http://%s/' % current_domain,
                'username': form.cleaned_data['username'],
                'password': form.cleaned_data['password1'] 
            })
            message = message_template.render(message_context)
            #send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, 
            #        [user_.email])
            
            return HttpResponseRedirect(next)
    
    return render('authopenid/signup.html', {
        'form': form,
        'form2': form_signin,
        }, context_instance=RequestContext(request))

@login_required
def signout(request):
    """
    signout from the website. Remove openid from session and kill it.

    url : /signout/"
    """
    try:
        del request.session['openid']
    except KeyError:
        pass
    next = clean_next(request.GET.get('next'))
    logout(request)
    
    return HttpResponseRedirect(next)
    
def xrdf(request):
    url_host = get_url_host(request)
    return_to = [
        "%s%s" % (url_host, reverse('user_complete_signin'))
    ]
    return render('authopenid/yadis.xrdf', { 
        'return_to': return_to 
        }, context_instance=RequestContext(request))

@login_required
def account_settings(request):
    """
    index pages to changes some basic account settings :
     - change password
     - change email
     - associate a new openid
     - delete account

    url : /

    template : authopenid/settings.html
    """
    msg = request.GET.get('msg', '')
    is_openid = True

    try:
        uassoc = UserAssociation.objects.get(
                user__username__exact=request.user.username
        )
    except:
        is_openid = False


    return render('authopenid/settings.html', {
        'msg': msg,
        'is_openid': is_openid
        }, context_instance=RequestContext(request))

@login_required
def changepw(request):
    """
    change password view.

    url : /changepw/
    template: authopenid/changepw.html
    """
    
    user_ = request.user
    
    if request.POST:
        form = ChangepwForm(request.POST, user=user_)
        if form.is_valid():
            user_.set_password(form.cleaned_data['password1'])
            user_.save()
            msg = _("Password changed.") 
            redirect = "%s?msg=%s" % (
                    reverse('user_account_settings'),
                    urlquote_plus(msg))
            return HttpResponseRedirect(redirect)
    else:
        form = ChangepwForm(user=user_)

    return render('authopenid/changepw.html', {'form': form },
                                context_instance=RequestContext(request))

@login_required
def changeemail(request):
    """ 
    changeemail view. It require password or openid to allow change.

    url: /changeemail/

    template : authopenid/changeemail.html
    """
    msg = request.GET.get('msg', '')
    extension_args = {}
    user_ = request.user
    
    redirect_to = get_url_host(request) + reverse('user_changeemail')

    if request.POST:
        form = ChangeemailForm(request.POST, user=user_)
        if form.is_valid():
            if not form.test_openid:
                user_.email = form.cleaned_data['email']
                user_.save()
                msg = _("Email changed.") 
                redirect = "%s?msg=%s" % (reverse('user_account_settings'),
                        urlquote_plus(msg))
                return HttpResponseRedirect(redirect)
            else:
                request.session['new_email'] = form.cleaned_data['email']
                return ask_openid(request, form.cleaned_data['password'], 
                        redirect_to, on_failure=emailopenid_failure)    
    elif not request.POST and 'openid.mode' in request.GET:
        return complete(request, emailopenid_success, 
                emailopenid_failure, redirect_to) 
    else:
        form = ChangeemailForm(initial={'email': user_.email},
                user=user_)
    
    return render('authopenid/changeemail.html', {
        'form': form,
        'msg': msg 
        }, context_instance=RequestContext(request))


def emailopenid_success(request, identity_url, openid_response):
    openid_ = from_openid_response(openid_response)

    user_ = request.user
    try:
        uassoc = UserAssociation.objects.get(
                openid_url__exact=identity_url
        )
    except:
        return emailopenid_failure(request, 
                _("No OpenID %s found associated in our database" % identity_url))

    if uassoc.user.username != request.user.username:
        return emailopenid_failure(request, 
                _("The OpenID %s isn't associated to current user logged in" % 
                    identity_url))
    
    new_email = request.session.get('new_email', '')
    if new_email:
        user_.email = new_email
        user_.save()
        del request.session['new_email']
    msg = _("Email Changed.")

    redirect = "%s?msg=%s" % (reverse('user_account_settings'),
            urlquote_plus(msg))
    return HttpResponseRedirect(redirect)
    

def emailopenid_failure(request, message):
    redirect_to = "%s?msg=%s" % (
            reverse('user_changeemail'), urlquote_plus(message))
    return HttpResponseRedirect(redirect_to)
 
@login_required
def changeopenid(request):
    """
    change openid view. Allow user to change openid 
    associated to its username.

    url : /changeopenid/

    template: authopenid/changeopenid.html
    """

    extension_args = {}
    openid_url = ''
    has_openid = True
    msg = request.GET.get('msg', '')
        
    user_ = request.user

    try:
        uopenid = UserAssociation.objects.get(user=user_)
        openid_url = uopenid.openid_url
    except:
        has_openid = False
    
    redirect_to = get_url_host(request) + reverse('user_changeopenid')
    if request.POST and has_openid:
        form = ChangeopenidForm(request.POST, user=user_)
        if form.is_valid():
            return ask_openid(request, form.cleaned_data['openid_url'],
                    redirect_to, on_failure=changeopenid_failure)
    elif not request.POST and has_openid:
        if 'openid.mode' in request.GET:
            return complete(request, changeopenid_success,
                    changeopenid_failure, redirect_to)    

    form = ChangeopenidForm(initial={'openid_url': openid_url }, user=user_)
    return render('authopenid/changeopenid.html', {
        'form': form,
        'has_openid': has_openid, 
        'msg': msg 
        }, context_instance=RequestContext(request))

def changeopenid_success(request, identity_url, openid_response):
    openid_ = from_openid_response(openid_response)
    is_exist = True
    try:
        uassoc = UserAssociation.objects.get(openid_url__exact=identity_url)
    except:
        is_exist = False
        
    if not is_exist:
        try:
            uassoc = UserAssociation.objects.get(
                    user__username__exact=request.user.username
            )
            uassoc.openid_url = identity_url
            uassoc.save()
        except:
            uassoc = UserAssociation(user=request.user, 
                    openid_url=identity_url)
            uassoc.save()
    elif uassoc.user.username != request.user.username:
        return changeopenid_failure(request, 
                _('This OpenID is already associated with another account.'))

    request.session['openids'] = []
    request.session['openids'].append(openid_)

    msg = _("OpenID %s is now associated with your account." % identity_url) 
    redirect = "%s?msg=%s" % (
            reverse('user_account_settings'), 
            urlquote_plus(msg))
    return HttpResponseRedirect(redirect)
    

def changeopenid_failure(request, message):
    redirect_to = "%s?msg=%s" % (
            reverse('user_changeopenid'), 
            urlquote_plus(message))
    return HttpResponseRedirect(redirect_to)
  
@login_required
def delete(request):
    """
    delete view. Allow user to delete its account. Password/openid are required to 
    confirm it. He should also check the confirm checkbox.

    url : /delete

    template : authopenid/delete.html
    """

    extension_args = {}
    
    user_ = request.user

    redirect_to = get_url_host(request) + reverse('user_delete') 
    if request.POST:
        form = DeleteForm(request.POST, user=user_)
        if form.is_valid():
            if not form.test_openid:
                user_.delete() 
                return signout(request)
            else:
                return ask_openid(request, form.cleaned_data['password'],
                        redirect_to, on_failure=deleteopenid_failure)
    elif not request.POST and 'openid.mode' in request.GET:
        return complete(request, deleteopenid_success, deleteopenid_failure,
                redirect_to) 
    
    form = DeleteForm(user=user_)

    msg = request.GET.get('msg','')
    return render('authopenid/delete.html', {
        'form': form, 
        'msg': msg, 
        }, context_instance=RequestContext(request))

def deleteopenid_success(request, identity_url, openid_response):
    openid_ = from_openid_response(openid_response)

    user_ = request.user
    try:
        uassoc = UserAssociation.objects.get(
                openid_url__exact=identity_url
        )
    except:
        return deleteopenid_failure(request,
                _("No OpenID %s found associated in our database" % identity_url))

    if uassoc.user.username == user_.username:
        user_.delete()
        return signout(request)
    else:
        return deleteopenid_failure(request,
                _("The OpenID %s isn't associated to current user logged in" % 
                    identity_url))
    
    msg = _("Account deleted.") 
    redirect = "/?msg=%s" % (urlquote_plus(msg))
    return HttpResponseRedirect(redirect)
    

def deleteopenid_failure(request, message):
    redirect_to = "%s?msg=%s" % (reverse('user_delete'), urlquote_plus(message))
    return HttpResponseRedirect(redirect_to)


def sendpw(request):
    """
    send a new password to the user. It return a mail with 
    a new pasword and a confirm link in. To activate the 
    new password, the user should click on confirm link.

    url : /sendpw/

    templates :  authopenid/sendpw_email.txt, authopenid/sendpw.html
    """

    msg = request.GET.get('msg','')
    if request.POST:
        form = EmailPasswordForm(request.POST)
        if form.is_valid():
            new_pw = User.objects.make_random_password()
            confirm_key = UserPasswordQueue.objects.get_new_confirm_key()
            try:
                uqueue = UserPasswordQueue.objects.get(
                        user=form.user_cache
                )
            except:
                uqueue = UserPasswordQueue(
                        user=form.user_cache
                )
            uqueue.new_password = new_pw
            uqueue.confirm_key = confirm_key
            uqueue.save()
            # send email 
            current_domain = Site.objects.get_current().domain
            subject = _("Request for new password")
            message_template = loader.get_template(
                    'authopenid/sendpw_email.txt')
            message_context = Context({ 
                'site_url': 'http://%s' % current_domain,
                'confirm_key': confirm_key,
                'username': form.user_cache.username,
                'password': new_pw,
                'url_confirm': reverse('user_confirmchangepw'),
            })
            message = message_template.render(message_context)
            #send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, 
            #        [form.user_cache.email])
            msg = _("A new password has been sent to your email address.")
    else:
        form = EmailPasswordForm()
        
    return render('authopenid/sendpw.html', {
        'form': form,
        'msg': msg 
        }, context_instance=RequestContext(request))


def confirmchangepw(request):
    """
    view to set new password when the user click on confirm link
    in its mail. Basically it check if the confirm key exist, then
    replace old password with new password and remove confirm
    ley from the queue. Then it redirect the user to signin
    page.

    url : /sendpw/confirm/?key

    """
    confirm_key = request.GET.get('key', '')
    if not confirm_key:
        return HttpResponseRedirect('/')

    try:
        uqueue = UserPasswordQueue.objects.get(
                confirm_key__exact=confirm_key
        )
    except:
        msg = _("Could not change password. Confirmation key '%s'\
                is not registered." % confirm_key) 
        redirect = "%s?msg=%s" % (
                reverse('user_sendpw'), urlquote_plus(msg))
        return HttpResponseRedirect(redirect)

    try:
        user_ = User.objects.get(id=uqueue.user.id)
    except:
        msg = _("Can not change password. User don't exist anymore \
                in our database.") 
        redirect = "%s?msg=%s" % (reverse('user_sendpw'), 
                urlquote_plus(msg))
        return HttpResponseRedirect(redirect)

    user_.set_password(uqueue.new_password)
    user_.save()
    uqueue.delete()
    msg = _("Password changed for %s. You may now sign in." % 
            user_.username) 
    redirect = "%s?msg=%s" % (reverse('user_signin'), 
                                        urlquote_plus(msg))

    return HttpResponseRedirect(redirect)

########NEW FILE########
__FILENAME__ = admin
from snipt.favsnipt.models import FavSnipt
from django.contrib import admin

class FavSniptAdmin(admin.ModelAdmin):
    list_display = ('snipt','user','created',)
    ordering = ('created',)
    
admin.site.register(FavSnipt, FavSniptAdmin)

########NEW FILE########
__FILENAME__ = 0001_initial
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding model 'FavSnipt'
        db.create_table('favsnipt_favsnipt', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('snipt', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['snippet.Snippet'])),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'])),
            ('created', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
        ))
        db.send_create_signal('favsnipt', ['FavSnipt'])


    def backwards(self, orm):
        
        # Deleting model 'FavSnipt'
        db.delete_table('favsnipt_favsnipt')


    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'ordering': "('content_type__app_label', 'codename')", 'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'favsnipt.favsnipt': {
            'Meta': {'object_name': 'FavSnipt'},
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'snipt': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['snippet.Snippet']"}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"})
        },
        'snippet.snippet': {
            'Meta': {'object_name': 'Snippet'},
            'code': ('django.db.models.fields.TextField', [], {}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'key': ('django.db.models.fields.TextField', [], {}),
            'lexer': ('django.db.models.fields.TextField', [], {}),
            'public': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '50', 'db_index': 'True'}),
            'tags': ('tagging.fields.TagField', [], {'default': "''"}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"})
        }
    }

    complete_apps = ['favsnipt']

########NEW FILE########
__FILENAME__ = models
from django.contrib.auth.models import User
from django.db import models

from snippet.models import Snippet

class FavSnipt(models.Model):
    snipt    = models.ForeignKey(Snippet)
    user     = models.ForeignKey(User)
    created  = models.DateTimeField(auto_now_add=True)
    
    def __unicode__(self):
        return self.snipt.description

########NEW FILE########
__FILENAME__ = snipt_is_favorite
from django.template import Library
from tagging.models import Tag
 
register = Library()
 
@register.simple_tag
def snipt_is_favorite(snipt, user):
    return snipt.is_favorite(user)

########NEW FILE########
__FILENAME__ = tests
"""
This file demonstrates two different styles of tests (one doctest and one
unittest). These will both pass when you run "manage.py test".

Replace these with more appropriate tests for your application.
"""

from django.test import TestCase

class SimpleTest(TestCase):
    def test_basic_addition(self):
        """
        Tests that 1 + 1 always equals 2.
        """
        self.failUnlessEqual(1 + 1, 2)

__test__ = {"doctest": """
Another way to test that 1 + 1 is equal to 2.

>>> 1 + 1 == 2
True
"""}


########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import *

from snipt.favsnipt.views import *

urlpatterns = patterns('',
    url(r'^toggle/(?P<snipt>.*)$', toggle_fav),
)

########NEW FILE########
__FILENAME__ = views
from django.http import HttpResponse
from django.utils import simplejson
from django.shortcuts import get_object_or_404

from snipt.snippet.models import Snippet

from snipt.favsnipt.models import FavSnipt

def toggle_fav(request, snipt):
    """
    An AJAX view for adding favorite snipts.
    """
    
    try:
        favsnipt = FavSnipt.objects.get(user=request.user, snipt=snipt)
        favsnipt.delete()
        data = { 'success': True, 'favorited': False }
    except:
        snipt = get_object_or_404(Snippet, id__exact=snipt)
        if snipt.user != request.user:
            favsnipt = FavSnipt(user=request.user, snipt=snipt)
            favsnipt.save()
            data = { 'success': True, 'favorited': True }
        else:
            data = { 'success': False, 'error': 'Cannot favorite your own snipts.', 'favorited': False }
    return HttpResponse(simplejson.dumps(data), mimetype='application/javascript')

########NEW FILE########
__FILENAME__ = forms
from django.utils.translation import ugettext_lazy as _
from django.contrib.auth.models import User
from django.forms.models import ModelForm
from snipt.snippet.models import Snippet
from django import forms

class UserCreationForm(forms.ModelForm):
    """
    A form that creates a user, with no privileges, from the given username, password and email.
    """
    username = forms.RegexField(max_length=30, regex=r'^\w+$')
    password1 = forms.CharField(max_length=60, widget=forms.PasswordInput)
    password2 = forms.CharField(max_length=60, widget=forms.PasswordInput)
    email = forms.EmailField()
    
    class Meta:
        model = User
        fields = ("username",)
    
    def clean_username(self):
        username = self.cleaned_data["username"]
        try:
            User.objects.get(username=username)
        except User.DoesNotExist:
            return username
        raise forms.ValidationError(_("A user with that username already exists."))
    
    def clean_password2(self):
        try:
            password1 = self.cleaned_data["password1"]
        except KeyError:
            raise forms.ValidationError(_("The two password fields didn't match."))
        password2 = self.cleaned_data["password2"]
        if password1 != password2:
            raise forms.ValidationError(_("The two password fields didn't match."))
        return password2
    
    def save(self, commit=True):
        user = super(UserCreationForm, self).save(commit=False)
        user.set_password(self.cleaned_data["password1"])
        user.email = self.cleaned_data["email"]
        if commit:
            user.save()
        return user

class SnippetForm(ModelForm):
    class Meta:
        model = Snippet
        fields = ('code','description','tags','lexer','public',)

########NEW FILE########
__FILENAME__ = gunicorn.conf
bind = "unix:/tmp/gunicorn.snipt.sock"
daemon = True                    # Whether work in the background
debug = False                    # Some extra logging
logfile = ".gunicorn.log"        # Name of the log file
loglevel = "info"                # The level at which to log
pidfile = ".gunicorn.pid"        # Path to a PID file
workers = 1                      # Number of workers to initialize
umask = 0                        # Umask to set when daemonizing
user = None                      # Change process owner to user
group = None                     # Change process group to group
proc_name = "gunicorn-snipt"    # Change the process name
tmp_upload_dir = None            # Set path used to store temporary uploads


def post_fork(server, worker):
    server.log.info("Worker spawned (pid: %s)" % worker.pid)
    
    import local_settings, monitor
    if local_settings.DEBUG:
        server.log.info("Starting change monitor.")
        monitor.start(interval=1.0)


########NEW FILE########
__FILENAME__ = gunicorn.server.conf
import os

bind = "localhost:1338"
daemon = False                    # Whether work in the background
debug = False                     # Some extra logging
logfile = "./logs/gunicorn.log"                     # Name of the log file
loglevel = "info"                 # The level at which to log
pidfile = ".gunicorn.pid"     # Path to a PID file
workers = 2                       # Number of workers to initialize
umask = 0                         # Umask to set when daemonizing
user = None                       # Change process owner to user
group = None                      # Change process group to group
tmp_upload_dir = None             # Set path used to store temporary uploads

def after_fork(server, worker):
    server.log.info("Worker spawned (pid: %s)" % worker.pid)

before_fork=lambda server, worker: server.log.debug("Worker ready to fork!")
before_exec=lambda server: server.log.debug("Forked child, reexecuting")

########NEW FILE########
__FILENAME__ = local_settings-template
from settings import INSTALLED_APPS

DEBUG = False

DATABASE_ENGINE = ''
DATABASE_NAME = ''
DATABASE_USER = ''
DATABASE_PASSWORD = ''

TIME_ZONE = ''

SECRET_KEY = ''

INSTALLED_APPS += ('gunicorn',)

########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python
from django.core.management import execute_manager
try:
    import settings # Assumed to be in the same directory.
except ImportError:
    import sys
    sys.stderr.write("Error: Can't find the file 'settings.py' in the directory containing %r. It appears you've customized things.\nYou'll have to run django-admin.py, passing it your settings module.\n(If the file settings.py does indeed exist, it's causing an ImportError somehow.)\n" % __file__)
    sys.exit(1)

if __name__ == "__main__":
    execute_manager(settings)

########NEW FILE########
__FILENAME__ = monitor
import os
import sys
import time
import signal
import threading
import atexit
import Queue

_interval = 1.0
_times = {}
_files = []

_running = False
_queue = Queue.Queue()
_lock = threading.Lock()

def _restart(path):
    _queue.put(True)
    prefix = 'monitor (pid=%d):' % os.getpid()
    print >> sys.stderr, '%s Change detected to \'%s\'.' % (prefix, path)
    print >> sys.stderr, '%s Triggering process restart.' % prefix
    os.kill(os.getpid(), signal.SIGINT)

def _modified(path):
    try:
        # If path doesn't denote a file and were previously
        # tracking it, then it has been removed or the file type
        # has changed so force a restart. If not previously
        # tracking the file then we can ignore it as probably
        # pseudo reference such as when file extracted from a
        # collection of modules contained in a zip file.

        if not os.path.isfile(path):
            return path in _times

        # Check for when file last modified.

        mtime = os.stat(path).st_mtime
        if path not in _times:
            _times[path] = mtime

        # Force restart when modification time has changed, even
        # if time now older, as that could indicate older file
        # has been restored.

        if mtime != _times[path]:
            return True
    except:
        # If any exception occured, likely that file has been
        # been removed just before stat(), so force a restart.

        return True

    return False

def _monitor():
    while 1:
        # Check modification times on all files in sys.modules.

        for module in sys.modules.values():
            if not hasattr(module, '__file__'):
                continue
            path = getattr(module, '__file__')
            if not path:
                continue
            if os.path.splitext(path)[1] in ['.pyc', '.pyo', '.pyd']:
                path = path[:-1]
            if _modified(path):
                return _restart(path)

        # Check modification times on files which have
        # specifically been registered for monitoring.

        for path in _files:
            if _modified(path):
                return _restart(path)

        # Go to sleep for specified interval.

        try:
            return _queue.get(timeout=_interval)
        except:
            pass

_thread = threading.Thread(target=_monitor)
_thread.setDaemon(True)

def _exiting():
    try:
        _queue.put(True)
    except:
        pass
    _thread.join()

atexit.register(_exiting)

def track(path):
    if not path in _files:
        _files.append(path)

def start(interval=1.0):
    global _interval
    if interval < _interval:
        _interval = interval

    global _running
    _lock.acquire()
    if not _running:
        prefix = 'monitor (pid=%d):' % os.getpid()
        print >> sys.stderr, '%s Starting change monitor.' % prefix
        _running = True
        _thread.start()
    _lock.release()

########NEW FILE########
__FILENAME__ = settings
# Django settings for snipt project.
import os.path

DEBUG = False

TEMPLATE_DEBUG = DEBUG

FORCE_LOWERCASE_TAGS = True

LOGIN_URL = '/login'
LOGIN_REDIRECT_URL = '/'

ADMINS = ()

MANAGERS = ADMINS

DATABASE_ENGINE = ''            # 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'oracle'.
DATABASE_NAME = ''         # Or path to database file if using sqlite3.
DATABASE_USER = ''             # Not used with sqlite3.
DATABASE_PASSWORD = ''  # Not used with sqlite3.sqlite3.
DATABASE_HOST = ''                   # Set to empty string for localhost. Not used with sqlite3.
DATABASE_PORT = ''                   # Set to empty string for default. Not used with sqlite3.

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# If running in a Windows environment this must be set to the same as your
# system time zone.
TIME_ZONE = 'America/New_York'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en-us'

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# Absolute path to the directory that holds media.
MEDIA_ROOT = ''

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash if there is a path component (optional in other cases).
# Examples: "http://media.lawrence.com", "http://example.com/media/"

MEDIA_URL = '/media/'

# URL prefix for admin media -- CSS, JavaScript and images. Make sure to use a
# trailing slash.
ADMIN_MEDIA_PREFIX = '/media/admin/'

# Make this unique, and don't share it with anybody.
SECRET_KEY = ''

TEMPLATE_CONTEXT_PROCESSORS = (
    "django.core.context_processors.auth",
    "django.core.context_processors.debug",
    "django.core.context_processors.i18n",
    "django.core.context_processors.media",
    "django.core.context_processors.request",
)

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.load_template_source',
    'django.template.loaders.app_directories.load_template_source',
#     'django.template.loaders.eggs.load_template_source',
)

MIDDLEWARE_CLASSES = (
    #'django.middleware.cache.UpdateCacheMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django_authopenid.middleware.OpenIDMiddleware',
    'pagination.middleware.PaginationMiddleware',
    #'django.middleware.cache.FetchFromCacheMiddleware',
)

ROOT_URLCONF = 'snipt.urls'

TEMPLATE_DIRS = (
    os.path.join(os.path.dirname(__file__), 'templates').replace('\\','/'),
)

SESSION_COOKIE_AGE = 5259488

INSTALLED_APPS = (
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.comments',
    'django.contrib.sites',
    'django_authopenid',
    'django_extensions',
    'piston',
    'snippet',
    'pagination',
    'compress',
    'snipt.ad',
    'snipt.api',
    'tagging',
    'favsnipt',
    'south',
)

# cache requires these middleware items (in this order)
# 'django.middleware.cache.FetchFromCacheMiddleware',
# 'django.middleware.cache.UpdateCacheMiddleware',

# process: /usr/bin/memcached -m 64 -p 11211 -u nobody -l 127.0.0.1 
#CACHE_BACKEND = 'memcached://127.0.0.1:11211/'
#CACHE_MIDDLEWARE_SECONDS = 600 # 10 mins
#CACHE_MIDDLEWARE_KEY_PREFIX = 'snipt' # set this if your cache is used across multiple sites
#CACHE_MIDDLEWARE_ANONYMOUS_ONLY = False # only shows cached stuff to non-logged-in users

COMMENTS_ALLOW_PROFANITIES = True

COMPRESS_VERSION = True
COMPRESS_CSS = {'all': {'source_filenames': ('style.css',), 'output_filename': 'snipt.r?.css'}}
COMPRESS_JS =  {'all': {'source_filenames': ('jquery.js','jquery.ui.js','jquery.autogrow.js','jquery.livequery.js','zero-clipboard.js','script.js',), 'output_filename': 'snipt.r?.js'}}

FIXTURE_DIRS = (
    os.path.join(os.path.dirname(__file__), 'fixtures').replace('\\','/'),
)

# Override with settings in local_settings.py if it exists.
from local_settings import *

########NEW FILE########
__FILENAME__ = admin
from snipt.snippet.models import Snippet
from django.contrib import admin

class SnippetAdmin(admin.ModelAdmin):
    list_display = ('description','user','slug','created',)
    ordering = ('created',)
    prepopulated_fields = {'slug': ('description',)}
    
admin.site.register(Snippet, SnippetAdmin)

########NEW FILE########
__FILENAME__ = 0001_initial
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding model 'Snippet'
        db.create_table('snippet_snippet', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('code', self.gf('django.db.models.fields.TextField')()),
            ('description', self.gf('django.db.models.fields.TextField')()),
            ('slug', self.gf('django.db.models.fields.SlugField')(max_length=50, db_index=True)),
            ('lexer', self.gf('django.db.models.fields.TextField')()),
            ('key', self.gf('django.db.models.fields.TextField')()),
            ('created', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'])),
            ('public', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('tags', self.gf('tagging.fields.TagField')(default='')),
        ))
        db.send_create_signal('snippet', ['Snippet'])

        # Adding model 'Referer'
        db.create_table('snippet_referer', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('url', self.gf('django.db.models.fields.URLField')(max_length=200)),
            ('snippet', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['snippet.Snippet'])),
        ))
        db.send_create_signal('snippet', ['Referer'])


    def backwards(self, orm):
        
        # Deleting model 'Snippet'
        db.delete_table('snippet_snippet')

        # Deleting model 'Referer'
        db.delete_table('snippet_referer')


    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'ordering': "('content_type__app_label', 'codename')", 'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'snippet.referer': {
            'Meta': {'object_name': 'Referer'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'snippet': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['snippet.Snippet']"}),
            'url': ('django.db.models.fields.URLField', [], {'max_length': '200'})
        },
        'snippet.snippet': {
            'Meta': {'object_name': 'Snippet'},
            'code': ('django.db.models.fields.TextField', [], {}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'key': ('django.db.models.fields.TextField', [], {}),
            'lexer': ('django.db.models.fields.TextField', [], {}),
            'public': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '50', 'db_index': 'True'}),
            'tags': ('tagging.fields.TagField', [], {'default': "''"}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"})
        }
    }

    complete_apps = ['snippet']

########NEW FILE########
__FILENAME__ = models
from django.contrib.auth.models import User
from tagging.fields import TagField
from tagging.models import Tag
from django.db import models
import tagging

class Snippet(models.Model):
    code         = models.TextField()
    description  = models.TextField()
    slug         = models.SlugField()
    lexer        = models.TextField()
    key          = models.TextField()
    created      = models.DateTimeField(auto_now_add=True)
    user         = models.ForeignKey(User)
    public       = models.BooleanField()
    tags         = TagField()
    
    def __unicode__(self):
        return u'%s' %(self.description)
    
    def get_tags(self):
        return Tag.objects.get_for_object(self) 
    
    def get_absolute_url(self):
        return "/%s/%s/" % (self.user.username, self.slug)
    
    def is_favorite(self, user):
        from snipt.favsnipt.models import FavSnipt
        try:
            FavSnipt.objects.get(snipt=self, user=user)
            return 'favorited'
        except:
            return ''

try:
    tagging.register(Snippet, tag_descriptor_attr='_tags') 
except tagging.AlreadyRegistered:
    pass

class Referer(models.Model):
    url          = models.URLField()
    snippet      = models.ForeignKey(Snippet)
    
    def __unicode__(self):
        return u'%s' %(self.url)
########NEW FILE########
__FILENAME__ = code_stylized
from django import template
from pygments import highlight
from pygments.lexers import get_lexer_by_name
from pygments.formatters import HtmlFormatter

register = template.Library()

def code_stylized(value):
    # Stylize the code.
    code_stylized = highlight(value.code, get_lexer_by_name(value.lexer, encoding='UTF-8'), HtmlFormatter())
    return code_stylized

register.filter('code_stylized', code_stylized)

########NEW FILE########
__FILENAME__ = snippet_extras
from snipt.snippet.models import Snippet
from django.template import Library
from tagging.models import Tag
 
register = Library()
 
@register.simple_tag
def snipt_count(user):
    return Snippet.objects.filter(user=user).count()

@register.simple_tag
def tag_count(user):
    return len(Tag.objects.usage_for_queryset(Snippet.objects.filter(user=user)))

########NEW FILE########
__FILENAME__ = utils
from django.template.defaultfilters import slugify
from django.db.models import Q
import re

def SlugifyUniquely(value, model, slugfield="slug"):
        """Returns a slug on a name which is unique within a model's table

        This code suffers a race condition between when a unique
        slug is determined and when the object with that slug is saved.
        It's also not exactly database friendly if there is a high
        likelyhood of common slugs being attempted.

        A good usage pattern for this code would be to add a custom save()
        method to a model with a slug field along the lines of:

                from django.template.defaultfilters import slugify

                def save(self):
                    if not self.id:
                        # replace self.name with your prepopulate_from field
                        self.slug = SlugifyUniquely(self.name, self.__class__)
                super(self.__class__, self).save()

        Original pattern discussed at
        http://www.b-list.org/weblog/2006/11/02/django-tips-auto-populated-fields
        """
        suffix = 0
        potential = base = slugify(value)
        while True:
                if suffix:
                        potential = "-".join([base, str(suffix)])
                if not model.objects.filter(**{slugfield: potential}).count():
                        return potential
                # we hit a conflicting slug, so bump the suffix & try again
                suffix += 1

def normalize_query(query_string,
                    findterms=re.compile(r'"([^"]+)"|(\S+)').findall,
                    normspace=re.compile(r'\s{2,}').sub):
    ''' Splits the query string in invidual keywords, getting rid of unecessary spaces
        and grouping quoted words together.
        Example:

        >>> normalize_query('  some random  words "with   quotes  " and   spaces')
        ['some', 'random', 'words', 'with quotes', 'and', 'spaces']

    '''
    return [normspace(' ', (t[0] or t[1]).strip()) for t in findterms(query_string)] 

def get_query(query_string, search_fields):
    ''' Returns a query, that is a combination of Q objects. That combination
        aims to search keywords within a model by testing the given search fields.

    '''
    query = None # Query to search for every search term        
    terms = normalize_query(query_string)
    for term in terms:
        or_query = None # Query to search for a given term in each field
        for field_name in search_fields:
            q = Q(**{"%s__icontains" % field_name: term})
            if or_query is None:
                or_query = q
            else:
                or_query = or_query | q
        if query is None:
            query = or_query
        else:
            query = query & or_query
    return query

########NEW FILE########
__FILENAME__ = views
# Create your views here.

########NEW FILE########
__FILENAME__ = urls
from django.views.generic.simple import direct_to_template
from django.utils.translation import ugettext as _
from django.conf.urls.defaults import *
from django.contrib.auth.views import *
from django.contrib import admin
from django.conf import settings
from snipt.views import *
import os

admin.autodiscover()

import useradmin

urlpatterns = patterns('',
    (r'^api/?', include('snipt.api.urls')),
    (r'^admin/?(.*)', admin.site.root),
    (r'^message/toggle?$', message),
    (r'^wrap/toggle?$', wrap),
    (r'^tags/list/?$', tags),
    (r'^public/tags?$', all_public_tags),
    (r'^delete/?$', delete),
    (r'^save/?$', save),
    (r'^search/?$', search),
    (r'^embed/(?P<snipt>[^/]+)$', embed),
    (r'^password/reset', password_reset),
    (r'^account/set-openid/??$', direct_to_template, {'template': 'registration/set_openid.html'}),
    (r'^comments/', include('django.contrib.comments.urls')),
    (r'^favs/', include('snipt.favsnipt.urls')),
)

urlpatterns += patterns('django_authopenid.views',
    url(r'^yadis.xrdf$', 'xrdf', name='yadis_xrdf'),
    url(r'^%s$' % _('login/?'), 'signin', name='user_signin'),
    url(r'^%s$' % _('logout/?'), 'signout', name='user_signout'),
    url(r'^%s%s$' % (_('signin/'), _('complete/?')), 'complete_signin', name='user_complete_signin'),
    url(r'^%s$' % _('register/'), 'register', name='user_register'),
    url(r'^%s$' % _('signup/?'), 'signup', name='user_signup'),
    url(r'^account/?$', 'account_settings', name='user_account_settings'),
    url(r'^%s$' % _('account/request-password/'), 'sendpw', name='user_sendpw'),
    url(r'^%s%s$' % (_('account/change-password/'), _('confirm/')), 'confirmchangepw', name='user_confirmchangepw'),
    url(r'^%s$' % _('account/change-password/'), 'changepw', name='user_changepw'),
    url(r'^%s$' % _('account/change-email/'), 'changeemail', name='user_changeemail'),
    url(r'^%s$' % _('account/change-openid/'), 'changeopenid', name='user_changeopenid'),
    url(r'^%s$' % _('account/delete/'), 'delete', name='user_delete'),
)

if settings.DEBUG:
    urlpatterns += patterns('',
        (r'^media/(?P<path>.*)$', 'django.views.static.serve', {'document_root': os.path.join(os.path.dirname(__file__), 'media').replace('\\','/')}),
    )

urlpatterns += patterns('',
    (r'^(?P<user>[^/]+)?/?(?P<slug>tag/[^/]+)?/?(?P<snipt_id>[^/]+)?/?(all)?$', dispatcher),
)

########NEW FILE########
__FILENAME__ = useradmin
from django.contrib.auth.models import User
from django.contrib import admin

class UserAdmin(admin.ModelAdmin):
    list_display = ('username', 'email', 'is_staff', 'date_joined', 'last_login')
    list_filter = ('is_superuser', 'date_joined')
    search_fields = ['username', 'email']

admin.site.unregister(User)
admin.site.register(User, UserAdmin)

########NEW FILE########
__FILENAME__ = views
from django.contrib.auth import authenticate, login as auth_login
from django.contrib.auth.models import User
from django.contrib.comments.signals import comment_was_posted
from django.http import HttpResponse, HttpResponseRedirect
from django.contrib.auth.decorators import login_required
from django.shortcuts import render_to_response
from tagging.models import Tag, TaggedItem
from django.template import RequestContext
from snipt.snippet.models import Snippet, Referer
from django.utils.html import escape
from django.utils import simplejson
from tagging.utils import get_tag
from snipt.snippet.utils import *
from django.http import Http404
from settings import DEBUG
from snipt.forms import *
import md5

from pygments import highlight
from pygments.lexers import get_lexer_by_name
from pygments.formatters import HtmlFormatter

def dispatcher(request, user, slug, snipt_id):
    if not user and not slug and not snipt_id:
        return home_page(request)
    elif user and snipt_id:
        if snipt_id == 'feed':
            return user_page(request, user, slug, True)
        else:
            return snipt_page(request, user, snipt_id)
    else:
        return user_page(request, user, slug)

def search(request):
    query_string = ''
    found_snipts = None
    if ('q' in request.GET) and request.GET['q'].strip():
        query_string = request.GET['q']
        entry_query = get_query(query_string, ['code', 'description', 'tags',])
        snipts = Snippet.objects.filter(entry_query).filter(Q(public=1) | Q(user=request.user.id)).order_by('-created')
        disable_wrap = request.session.get('disable_wrap')
        disable_message = request.session.get('disable_message')
        snipts_count = snipts.count()
    search = True
    return render_to_response('search.html', locals(), context_instance=RequestContext(request))

def feed(request, user, slug):
    return render_to_response('feed.html', locals(), context_instance=RequestContext(request))

def embed(request, snipt):
    try:
        snipt = Snippet.objects.get(key=snipt)
        snipt.code_stylized = highlight(snipt.code.replace("\\\"","\\\\\""), get_lexer_by_name(snipt.lexer, encoding='UTF-8'), HtmlFormatter(style="native", noclasses=True, prestyles="-moz-border-radius: 5px; border-radius: 5px; -webkit-border-radius: 5px; margin: 0; display: block; font: 11px Monaco, monospace !important; padding: 15px; background-color: #1C1C1C; overflow: auto; color: #D0D0D0;"))
        snipt.code_stylized = snipt.code_stylized.split('\n')
        snipt.referer = request.META.get('HTTP_REFERER', '')
        i = 0;
        for sniptln in snipt.code_stylized:
            snipt.code_stylized[i] = snipt.code_stylized[i].replace(" font-weight: bold", " font-weight: normal").replace('\'','\\\'').replace('\\n','\\\\n').replace("\\x", "\\\\x").replace('\\&#39;', '\\\\&#39;').replace('\\s', '\\\\s')
            i = i + 1
    except Snippet.DoesNotExist:
        raise Http404
    
    if(snipt.referer):
        try:
            Referer.objects.get(url=snipt.referer, snippet=snipt.id)
        except Referer.DoesNotExist:
            referrer = Referer(None, snipt.referer, snipt.id)
            referrer.save()
        
    return render_to_response('embed.html', locals(), context_instance=RequestContext(request), mimetype="application/javascript")

def password_reset(request):
  request.session['msg'] = "";
  if request.POST:
    try:
      # check to see if a user by the email address exists in the system
      email = request.POST['email']
      user = User.objects.get(email=email)
    
      # generate a new password
      from random import choice
      new_password = ''.join([choice('abcdefghijklmnopqrstuvwxyz0123456789!@#$%^&*(-_=+)') for i in range(16)])

      # assign the new password to the user account
      user.set_password(new_password)
      user.save()

      # send the new password to that e-mail address & tell them to change their pass immediately!
      from django.core.mail import send_mail
      
      subject = '[Snipt] Here\'s a temporary password'
      message = 'Log-in using %s\r\n\r\nPlease update your password immediately after that!\r\n\r\n- Snipt.net admins' % new_password
      
      send_mail(subject, message, 'no-reply@snipt.net', [email], fail_silently=False)
      
      request.session['msg'] = "We've sent you a temporary password. Check your e-mail!"
      
    except User.DoesNotExist:
      request.session['msg'] = "We didn't find anyone registered under %s" % request.POST['email']
    
    # or asset false
    # assert False
    
  return render_to_response('password_reset.html', locals(), context_instance=RequestContext(request))
  # request.session.msg = 'your password is being worked on by the locals.'
  # home_page(request)

def home_page(request):
    if request.user.is_authenticated():
        return HttpResponseRedirect('/' + request.user.username)
    else:
        is_home = True
        return render_to_response('home.html', locals(), context_instance=RequestContext(request))

def all_public_tags(request):
    tags = Tag.objects.usage_for_queryset(Snippet.objects.filter(public='1'), counts=True)
    return render_to_response('all-public-tags.html', locals(), context_instance=RequestContext(request))

    from django.contrib.comments.signals import comment_was_posted

def email_owner_on_comment(sender, comment, request, *args, **kwargs):
    from django.core.mail import EmailMultiAlternatives
    snipt = Snippet.objects.get(id=request.POST['object_pk'])
    if snipt.user.username != comment.name:
        text_content = """
            %s has posted a comment on your snipt "%s" at http://snipt.net%s#comment-%s.
        
            Just thought you'd like to know!
        
            The Snipt team at Lion Burger.
        """ % (comment.name, snipt.description, snipt.get_absolute_url(), comment.id)
        html_content = """
            <a href="http://snipt.net/%s">%s</a> has posted a comment on your snipt "<a href="http://snipt.net%s#comment-%s">%s</a>".<br />
            <br />
            Just thought you'd like to know!<br />
            <br />
            The <a href="http://snipt.net">Snipt</a> team at <a href="http://lionburger.com">Lion Burger</a>.
        """ % (comment.name, comment.name, snipt.get_absolute_url(), comment.id, snipt.description)
        msg = EmailMultiAlternatives("""A new comment on "%s".""" % snipt.description, text_content, 'Snipt <info@snipt.net>', [snipt.user.email])
        msg.attach_alternative(html_content, "text/html")
        msg.send()

comment_was_posted.connect(email_owner_on_comment)

def snipt_page(request, user, snipt_id):
    try:
        snipt = Snippet.objects.get(slug=snipt_id)
        if 'c' in request.GET:
            return HttpResponseRedirect(snipt.get_absolute_url() + '#comment-' + request.GET['c'])
    except:
        return HttpResponseRedirect('/' + user + '/tag/' + snipt_id)
    context_user = User.objects.get(id=snipt.user.id)
    
    if request.user.id == context_user.id:
        mine = True
    else:
        mine = False
    
    if not snipt.public and not mine:
        try:
            if request.GET['key'] != snipt.key:
                raise Http404()
            else:
                key = True
        except:
            raise Http404()
    
    disable_wrap = request.session.get('disable_wrap')
    disable_message = request.session.get('disable_message')
    
    return render_to_response('snipt.html', locals(), context_instance=RequestContext(request))

def user_page(request, user, slug, feed=False):
    
    # Set disable message to false.
    # request.session['disable_message'] = False
    
    # If the user has requested a tag listing page, handle accordingly, otherwise serve latest snipts.
    if request.user.username != user:
        mine = False
        try:
            context_user = User.objects.get(username=user)
            if context_user.username == 'public':
                public = True
            else:
                public = False
        except:
            raise Http404()
    else:
        mine = True
        context_user = request.user
    if slug is not None:
        slug = slug.replace('tag/','')

        """
        Attempt to retrieve the tag for this particular slug.  In the event that there is no tag
        associated with this slug, set tag to 'None'.
        """
        try:
            tag = Tag.objects.get(name = slug)
        except:
            tag = None

        # If the tag exists, retrieve the snipts that this user has tagged with this particular tag.
        if tag is not None:
            if mine:
                snipts = TaggedItem.objects.get_by_model(Snippet.objects.filter(user=context_user.id).order_by('-created'), tag)
                
                from snipt.favsnipt.models import FavSnipt
                favsnipts = FavSnipt.objects.filter(user=context_user.id)
                favrd = []
                for fs in favsnipts:
                    fs.snipt.favrd = True
                    fs.snipt.created = fs.created
                    if str(tag) in fs.snipt.tags:
                        favrd.append(fs.snipt)

                from operator import attrgetter
                from itertools import chain
                snipts = sorted(
                    chain(snipts, favrd),
                    key=attrgetter('created'), reverse=True)
                
            elif not public:
                snipts = TaggedItem.objects.get_by_model(Snippet.objects.filter(user=context_user.id, public='1').order_by('-created'), tag)
            else:
                snipts = TaggedItem.objects.get_by_model(Snippet.objects.filter(public='1').order_by('-created'), tag)

        # If the tag does not exist, raise 404.
        else:
            raise Http404()

        # If the tag exists, but the user has no snipts for this particular tag, raise 404.
        if len(snipts) == 0:
            raise Http404()

    # If the user is at the homepage (no tag specified).
    else:

        # Retrieve latest 20 snipts for user.
        if mine:
            snipts = Snippet.objects.filter(user=context_user.id).order_by('-created')
            
            from snipt.favsnipt.models import FavSnipt
            favsnipts = FavSnipt.objects.filter(user=context_user.id)
            favrd = []
            for fs in favsnipts:
                fs.snipt.favrd = True
                fs.snipt.created = fs.created
                favrd.append(fs.snipt)
            
            from operator import attrgetter
            from itertools import chain
            snipts = sorted(
                chain(snipts, favrd),
                key=attrgetter('created'), reverse=True)
            
        elif not public:
            snipts = Snippet.objects.filter(user=context_user.id, public='1').order_by('-created')
        else:
            snipts = Snippet.objects.filter(public='1').order_by('-created')[:100]

    # Compile the list of tags that this user has used.
    if mine:
        user_tags_list = Tag.objects.usage_for_queryset(Snippet.objects.filter(user=context_user.id).order_by('-created'), counts=True)
    elif not public:
        user_tags_list = Tag.objects.usage_for_queryset(Snippet.objects.filter(user=context_user.id, public='1').order_by('-created'), counts=True)
    else:
        user_tags_list = Tag.objects.usage_for_queryset(Snippet.objects.filter(public='1'), counts=True)
        if not DEBUG:
            user_tags_list.sort(key=lambda x: x.count, reverse=True)
        user_tags_list = user_tags_list[:40]
    
    for usertag in user_tags_list:
        usertag.slug = str(usertag)

    disable_wrap = request.session.get('disable_wrap')
    disable_message = request.session.get('disable_message')

    if mine:
        total_count = Snippet.objects.filter(user=context_user.id).count()
    elif not public:
        total_count = Snippet.objects.filter(user=context_user.id, public='1').count()
    else:
        total_count = Snippet.objects.filter(public='1').count()

    if total_count > 0:
        # Get the last lexer used so we can auto-select that one.
        if mine:
            last_lexer = Snippet.objects.filter(user=context_user.id).order_by('-created')[0].lexer
            
    snipts_count = len(snipts)
    
    # Send a modified version of the request path so we may compare it to the list of tag slugs (to identify current page).
    if mine:
        request_tag = request.path.replace('/' + request.user.username + '/tag/','')
    else:
        request_tag = request.path.replace('/' + context_user.username + '/tag/','')

    if feed:
        try:
            snipts = TaggedItem.objects.get_by_model(Snippet.objects.filter(user=context_user.id, public='1').order_by('-created'), tag)
        except:
            snipts = Snippet.objects.filter(user=context_user.id, public='1').order_by('-created')
        real_path = request.path.replace('/feed', '')
        if '/all' not in request.path:
            snipts = snipts.filter()[:20]
        return render_to_response('feed.xml', locals(), context_instance=RequestContext(request), mimetype="application/rss+xml")
    else:
        return render_to_response('home_user.html', locals(), context_instance=RequestContext(request))

def signup(request):
    """
    Handle new user signups.
    """
    signup_form = UserCreationForm(request.POST)
    
    # If the signup form has been submitted and is valid, save the new user and log the user in, otherwise present the form (with errors, if necessary).
    if signup_form.is_valid():
        signup_form.save()
        
        # Go ahead and log the new user in after we've created them.  Convenience!
        user = authenticate(username=request.POST['username'], password=request.POST['password1'])
        auth_login(request, user)

        return HttpResponseRedirect('/')
    else:
        return render_to_response("registration/signup.html", {
            'signup_form' : signup_form,
            'signup' : True,
            'data': request.POST
        }, context_instance=RequestContext(request))

@login_required
def tags(request):
    """
    Return a list of tags that the user has used.
    """
    user_tags_list = Tag.objects.usage_for_queryset(Snippet.objects.filter(user=request.user.id).order_by('-created'), counts=True)
    
    """
    For each tag, append the details of this tag to a new list which will be appended to the JSON response.
    
    Why?  Because if we simply send along the list of tag objects, simplejson won't know how to serialize it (rightly so).
    """
    tags_list = []
    for tag in user_tags_list:
        tags_list.append({
            'id': tag.id,
            'tag': escape(str(tag)),
            'count': escape(str(tag.count))
        })
    data = {
        'tags_list': tags_list
    }
    return HttpResponse(simplejson.dumps(data), mimetype='application/json')

@login_required
def save(request):
    """
    An AJAX view for saving new snipts.
    
    If we sent along an id of '0', it means we're adding a new snipt, so use the appropriate form.
    Otherwise, create an instance form from the model for that specific id.
    """
    try:
        request.POST['id']
    except:
        raise Http404()
    if request.POST['id'] != '0':
        submitted_snippet = SnippetForm(request.POST, instance=Snippet.objects.get(id=request.POST['id'], user=request.user.id))
    else:
        submitted_snippet = SnippetForm(request.POST)
    if submitted_snippet.is_valid():
        
        # Halt the form submission until we add the proper user to the values.
        submitted_snippet = submitted_snippet.save(commit=False)
        submitted_snippet.user = request.user
        if request.POST['id'] == '0':
            submitted_snippet.slug = SlugifyUniquely(submitted_snippet.description, Snippet)
            submitted_snippet.key = md5.new(submitted_snippet.slug).hexdigest()
        
        submitted_snippet.save()
        
        """
        Grab the tags for the newly created snippet.
        For each tag, append the details of this tag to a new list which will be appended to the JSON response.
        
        Why?  Because if we simply send along the list of tag objects, simplejson won't know how to serialize it (rightly so).
        """
        submitted_snippet.tags_list = []
        tags_list = submitted_snippet.get_tags()
        for tag in tags_list:
            submitted_snippet.tags_list.append({
                'id': tag.id,
                'tag': escape(str(tag)),
            })
        
        # Construct the data object we'll send back to the client so the new snipt can appear immediately.
        data = {
            'success': True,
            'id': submitted_snippet.id,
            'code': escape(submitted_snippet.code),
            'code_stylized': stylize(submitted_snippet.code, submitted_snippet.lexer),
            'description': escape(submitted_snippet.description),
            'tags': escape(submitted_snippet.tags),
            'tags_list': submitted_snippet.tags_list,
            'lexer': submitted_snippet.lexer,
            'public': submitted_snippet.public,
            'key': submitted_snippet.key,
            'slug': submitted_snippet.slug,
            'username': request.user.username,
            'created_date': submitted_snippet.created.strftime("%b %d"),
            'created_time': submitted_snippet.created.strftime("%I:%M %p").replace("AM","a.m.").replace("PM","p.m.")
        }
    else:
        data = {
            'success': False
        }
        
    # Use simplejson to convert the Python object to a true JSON object (though it's already pretty close).
    return HttpResponse(simplejson.dumps(data), mimetype='application/json')

def stylize(code, lexer):
    return highlight(code, get_lexer_by_name(lexer, encoding='UTF-8'), HtmlFormatter())

def wrap(request):
    if request.session.get('disable_wrap') == True:
        request.session['disable_wrap'] = False
    else:
        request.session['disable_wrap'] = True
    data = {
        'disable_wrap': str(request.session['disable_wrap'])
    }
    return HttpResponse(simplejson.dumps(data), mimetype='application/json')

def message(request):
    if request.session.get('disable_message') == True:
        request.session['disable_message'] = False
    else:
        request.session['disable_message'] = True
    data = {
        'disable_message': str(request.session['disable_message'])
    }
    return HttpResponse(simplejson.dumps(data), mimetype='application/json')

@login_required
def delete(request):
    """
    An AJAX view for deleting snipts.
    """
    deleting = Snippet.objects.get(id=request.POST['id'])
    
    # Make sure no one's trying to pull a fast one on us (or another user).
    if deleting.user_id == request.user.id:
        delid = deleting.id
        deleting.delete()
        
        # Return the deleted id to the client so that the snipt can be deleted from the page immediately.
        data = {
            'success': True,
            'id': delid
        }
    else:
        data = {
            'success': False
        }
    return HttpResponse(simplejson.dumps(data), mimetype='application/json')

########NEW FILE########
