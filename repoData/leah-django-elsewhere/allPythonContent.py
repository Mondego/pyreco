__FILENAME__ = admin
from django.contrib import admin

from models import *

class ProfileAdmin(admin.ModelAdmin):
    raw_id_fields = ['user']

class SocialNetworkProfileAdmin(ProfileAdmin):
    list_display = ('user', 'network_id', 'username') #, 'date_added')

class InstantMessengerProfileAdmin(ProfileAdmin):
    list_display = ('user', 'network_id', 'username') #, 'date_added')

class WebsiteProfileAdmin(ProfileAdmin):
    list_display = ('user', 'name', 'url') #, 'date_added')

## TODO Not sure why I can't grab date_added from the parent Profile model, need to figure this out.

admin.site.register(Network)
admin.site.register(SocialNetworkProfile, SocialNetworkProfileAdmin)
admin.site.register(WebsiteProfile, WebsiteProfileAdmin)
admin.site.register(InstantMessengerProfile, InstantMessengerProfileAdmin)
########NEW FILE########
__FILENAME__ = default_list
default_social_networks = [
    {
        'name': '43 Things',
        'url': 'http://www.43things.com/person/%s',
        'identifier': 'Username',
        'icon': 'fortythreethings.png',
        'network_type': 'sn'
    },
    {
        'name': 'Bebo',
        'url': 'http://www.bebo.com/Profile.jsp?MemberId=%s',
        'identifier': 'Member ID',
        'icon': 'bebo.png',
        'network_type': 'sn'
    },
    {
        'name': 'Blip.tv',
        'url': 'http://%s.blip.tv',
        'identifier': 'Username',
        'icon': 'blip.png',
        'network_type': 'sn'
    },
    {
        'name': 'Catster',
        'url': 'http://www.catster.com/cats/%s',
        'identifier': 'Cat ID',
        'icon': 'catster.png',
        'network_type': 'sn'
    },
    {
        'name': 'Corkd',
        'url': 'http://corkd.com/people/%s',
        'identifier': 'Username',
        'icon': 'corkd.png',
        'network_type': 'sn'
    },
    {
        'name': 'Delicious',
        'url': 'http://delicious.com/%s',
        'identifier': 'Username',
        'icon': 'delicious.png',
        'network_type': 'sn'
    },
    {
        'name': 'Digg',
        'url': 'http://digg.com/users/%s',
        'identifier': 'Username',
        'icon': 'digg.png',
        'network_type': 'sn'
    },
    {
        'name': 'Django People',
        'url': 'http://djangopeople.net/%s',
        'identifier': 'Username',
        'icon': 'djangopeople.png',
        'network_type': 'sn'
    },
    {
        'name': 'Dodgeball',
        'url': 'http://www.dodgeball.com/user?uid=%s',
        'identifier': 'User ID',
        'icon': 'dodgeball.png',
        'network_type': 'sn'
    },
    {
        'name': 'Dogster',
        'url': 'http://www.dogster.com/dogs/%s',
        'identifier': 'Dog ID',
        'icon': 'dogster.png',
        'network_type': 'sn'
    },
    {
        'name': 'Dopplr',
        'url': 'http://www.dopplr.com/traveller/%s',
        'identifier': 'Username',
        'icon': 'dopplr.png',
        'network_type': 'sn'
    },
    {
        'name': 'Facebook',
        'url': 'http://www.facebook.com/profile.php?id=%s',
        'identifier': 'User ID',
        'icon': 'facebook.png',
        'network_type': 'sn'
    },
    {
        'name': 'Flickr',
        'url': 'http://www.flickr.com/photos/%s/',
        'identifier': 'Flickr Alias',
        'icon': 'flickr.png',
        'network_type': 'sn'
    },
    {
        'name': 'foursquare',
        'url': 'http://playfoursquare.com/user?uid=%s',
        'identifier': 'User ID',
        'icon': 'foursquare.png',
        'network_type': 'sn'
    },
    {
        'name': 'Gamer Card',
        'url': 'http://live.xbox.com/en-US/profile/profile.aspx?pp=0&GamerTag=%s',
        'identifier': 'Gamertag',
        'icon': 'gamercard.png',
        'network_type': 'sn'
    },
    {
        'name': 'GitHub',
        'url': 'http://github.com/%s',
        'identifier': 'Username',
        'icon': 'github.png',
        'network_type': 'sn'
    },
    {
        'name': 'GoodReads',
        'url': 'http://www.goodreads.com/user/show/%s',
        'identifier': 'User ID',
        'icon': 'goodreads.png',
        'network_type': 'sn'
    },
    {
        'name': 'Hi5',
        'url': 'http://hi5.com/friend/profile/displayProfile.do?userid=%s',
        'identifier': 'User ID',
        'icon': 'hi5.png',
        'network_type': 'sn'
    },
    {
        'name': 'Instructables',
        'url': 'http://www.instructables.com/member/%s',
        'identifier': 'Username',
        'icon': 'instructables.png',
        'network_type': 'sn'
    },
    {
        'name': 'Jaiku',
        'url': 'http://%s.jaiku.com',
        'identifier': 'Username',
        'icon': 'jaiku.png',
        'network_type': 'sn'
    },
    {
        'name': 'Last.fm',
        'url': 'http://www.last.fm/user/%s',
        'identifier': 'Username',
        'icon': 'lastfm.png',
        'network_type': 'sn'
    },
    {
        'name': 'LibraryThing',
        'url': 'http://www.librarything.com/profile/%s',
        'identifier': 'Username',
        'icon': 'librarything.png',
        'network_type': 'sn'
    },
    {
        'name': 'LinkedIn',
        'url': 'http://www.linkedin.com/in/%s',
        'identifier': 'Full Name (without spaces)',
        'icon': 'linkedin.png',
        'network_type': 'sn'
    },
    {
        'name': 'LiveJournal',
        'url': 'http://%s.livejournal.com',
        'identifier': 'Username',
        'icon': 'lj.png',
        'network_type': 'sn'
    },
    {
        'name': 'Ma.gnolia',
        'url': 'http://ma.gnolia.com/people/%s',
        'identifier': 'Username',
        'icon': 'magnolia.png',
        'network_type': 'sn'
    },
    {
        'name': 'MetaFilter',
        'url': 'http://www.metafilter.com/user/%s',
        'identifier': 'User ID',
        'icon': 'metafilter.png',
        'network_type': 'sn'
    },
    {
        'name': 'MOG',
        'url': 'http://mog.com/%s',
        'identifier': 'Username',
        'icon': 'mog.png',
        'network_type': 'sn'
    },
    {
        'name': 'Multiply',
        'url': 'http://%s.multiply.com',
        'identifier': 'Username',
        'icon': 'multiply.png',
        'network_type': 'sn'
    },
    {
        'name': 'MySpace',
        'url': 'http://www.myspace.com/%s',
        'identifier': 'Username',
        'icon': 'myspace.png',
        'network_type': 'sn'
    },
    {
        'name': 'Netvibes',
        'url': 'http://www.netvibes.com/%s',
        'identifier': 'Username',
        'icon': 'netvibes.png',
        'network_type': 'sn'
    },
    {
        'name': 'Newsvine',
        'url': 'http://%s.newsvine.com',
        'identifier': 'Username',
        'icon': 'newsvine.png',
        'network_type': 'sn'
    },
    {
        'name': 'Ning',
        'url': 'http://%s.ning.com',
        'identifier': 'Network Name',
        'icon': 'ning.png',
        'network_type': 'sn'
    },
    {
        'name': 'Orkut',
        'url': 'http://www.orkut.com/Profile.aspx?uid=%s',
        'identifier': 'User ID',
        'icon': 'orkut.png',
        'network_type': 'sn'
    },
    {
        'name': 'Pandora',
        'url': 'http://pandora.com/people/%s',
        'identifier': 'Username',
        'icon': 'pandora.png',
        'network_type': 'sn'
    },
    {
        'name': 'Plaxo',
        'url': 'http://%s.myplaxo.com',
        'identifier': 'Public Profile ID',
        'icon': 'plaxo.png',
        'network_type': 'sn'
    },
    {
        'name': 'Pownce',
        'url': 'http://pownce.com/%s',
        'identifier': 'Username',
        'icon': 'pownce.png',
        'network_type': 'sn'
    },
    {
        'name': 'Readernaut',
        'url': 'http://readernaut.com/%s',
        'identifier': 'Username',
        'icon': 'readernaut.png',
        'network_type': 'sn'
    },
    {
        'name': 'RedBubble',
        'url': 'http://www.redbubble.com/people/%s',
        'identifier': 'Username',
        'icon': 'redbubble.png',
        'network_type': 'sn'
    },
    {
        'name': 'Reddit',
        'url': 'http://reddit.com/user/%s',
        'identifier': 'Username',
        'icon': 'reddit.png',
        'network_type': 'sn'
    },
    {
        'name': 'Seesmic',
        'url': 'http://seesmic.com/%s',
        'identifier': 'Username',
        'icon': 'seesmic.png',
        'network_type': 'sn'
    },
    {
        'name': 'Shelfworthy',
        'url': 'http://shelfworthy.com/%s',
        'identifier': 'Username',
        'icon': 'shelfworthy.png',
        'network_type': 'sn'
    },
    {
        'name': 'SonicLiving',
        'url': 'http://www.sonicliving.com/user/%s',
        'identifier': 'User ID',
        'icon': 'sonicliving.png',
        'network_type': 'sn'
    },
    {
        'name': 'StumbleUpon',
        'url': 'http://%s.stumbleupon.com',
        'identifier': 'Username',
        'icon': 'stumbleupon.png',
        'network_type': 'sn'
    },
    {
        'name': 'Tabblo',
        'url': 'http://www.tabblo.com/studio/person/%s',
        'identifier': 'Username',
        'icon': 'tabblo.png',
        'network_type': 'sn'
    },
    {
        'name': 'TagWorld',
        'url': 'http://www.tagworld.com/%s',
        'identifier': 'Username',
        'icon': '',
        'network_type': 'sn'
    },
    {
        'name': 'Technorati',
        'url': 'http://technorati.com/people/technorati/%s',
        'identifier': 'Username',
        'icon': 'technorati.png',
        'network_type': 'sn'
    },
    {
        'name': 'Tribe',
        'url': 'http://people.tribe.net/%s',
        'identifier': 'Username',
        'icon': 'tribe.png',
        'network_type': 'sn'
    },
    {
        'name': 'Tumblr',
        'url': 'http://%s.tumblr.com',
        'identifier': 'Username',
        'icon': 'tumblr.png',
        'network_type': 'sn'
    },
    {
        'name': 'Twitter',
        'url': 'http://twitter.com/%s',
        'identifier': 'Username',
        'icon': 'twitter.png',
        'network_type': 'sn'
    },
    {
        'name': 'Upcoming',
        'url': 'http://upcoming.yahoo.com/user/%s',
        'identifier': 'User ID',
        'icon': 'upcoming.png',
        'network_type': 'sn'
    },
    {
        'name': 'Ustream.TV',
        'url': 'http://www.ustream.tv/%s',
        'identifier': 'Username',
        'icon': 'ustream.png',
        'network_type': 'sn'
    },
    {
        'name': 'Virb',
        'url': 'http://www.virb.com/%s',
        'identifier': 'Username',
        'icon': 'virb.png',
        'network_type': 'sn'
    },
    {
        'name': 'Vox',
        'url': 'http://%s.vox.com',
        'identifier': 'Username',
        'icon': 'vox.png',
        'network_type': 'sn'
    },
    {
        'name': 'Wakoopa',
        'url': 'http://wakoopa.com/%s',
        'identifier': 'Username',
        'icon': 'wakoopa.png',
        'network_type': 'sn'
    },
    {
        'name': 'YouTube',
        'url': 'http://www.youtube.com/user/%s',
        'identifier': 'Username',
        'icon': 'youtube.png',
        'network_type': 'sn'
    },
    {
        'name': 'Zooomr',
        'url': 'http://www.zooomr.com/photos/%s',
        'identifier': 'Username',
        'icon': 'zooomr.png',
        'network_type': 'sn'
    },
    {
        'name': 'Zune',
        'url': 'http://social.zune.net/member/%s',
        'identifier': 'Username',
        'icon': 'zune.png',
        'network_type': 'sn'
    },
]

default_im_networks = [
    {
        'name': 'AIM',
        'url': 'aim:goim?screenname=%s',
        'icon': 'aim.png',
        'network_type': 'im'
    },
    {
        'name': 'GTalk',
        'url': 'gtalk:chat?jid=%s',
        'icon': 'gtalk.png',
        'network_type': 'im'
    },
    {
        'name': 'ICQ',
        'url': 'http://www.icq.com/people/about_me.php?to=%s',
        'icon': 'icq.png',
        'network_type': 'im'
    },
    {
        'name': 'MSN',
        'url': 'msnim:chat?contact=%s',
        'icon': 'msn.png',
        'network_type': 'im'
    },
    {
        'name': 'Skype',
        'url': 'skype:%s?chat',
        'icon': 'skype.png',
        'network_type': 'im'
    },
    {
        'name': 'Y!',
        'url': 'ymsgr:sendim?%s',
        'icon': 'yahoo.png',
        'network_type': 'im'
    },
]

########NEW FILE########
__FILENAME__ = management
from django.db.models import signals

from elsewhere.default_list import *
from elsewhere.models import SocialNetwork, InstantMessenger

# this function will fill the database with default data (stored in default_lists.py)

def fill_db(sender=None, **kwargs):
    for item in default_social_networks: # fill social networks
        if item.has_key('identifier'):
            ident = item['identifier']
        else:
            ident = ''

        SocialNetwork.objects.get_or_create(name=item['name'], defaults={
            'url': item['url'],
            'identifier': ident,
            'icon': item['icon']
        })

    for item in default_im_networks: # fill IM networks
        if item.has_key('identifier'):
            ident = item['identifier']
        else:
            ident = ''

        InstantMessenger.objects.get_or_create(name=item['name'], defaults={
            'url': item['url'],
            'identifier': ident,
            'icon': item['icon']
        })

signals.post_syncdb.connect(fill_db)
########NEW FILE########
__FILENAME__ = models
from datetime import datetime

from django import forms
from django.db import models
from django.core.cache import cache
from django.contrib import admin
from django.contrib.auth.models import User
from django.utils.translation import ugettext_lazy as _
from django.template.defaultfilters import slugify
from django.core.urlresolvers import reverse

GOOGLE_PROFILE_URL = 'http://www.google.com/s2/favicons?domain_url=%s'
SN_CACHE_KEY = 'elsewhere_sn_data'
IM_CACHE_KEY = 'elsewhere_im_data'


class Network(models.Model):
    """ Model for storing networks. """

    name = models.CharField(max_length=100)
    url = models.URLField()
    identifier = models.CharField(max_length=100)
    icon = models.CharField(max_length=100, blank=True)

    class Meta:
        abstract = True

    def __unicode__(self):
        return self.name

class SocialNetwork(Network):
    class Meta:
        verbose_name_plural = 'social networks'

    def save(self, *args, **kwargs):
        cache.delete(SN_CACHE_KEY)
        super(SocialNetwork, self).save(*args, **kwargs)

class InstantMessenger(Network):
    class Meta:
        verbose_name_plural = 'instant messanger networks'

    def save(self, *args, **kwargs):
        cache.delete(IM_CACHE_KEY)
        super(InstantMessenger, self).save(*args, **kwargs)

# the following makes the social / IM networks data act as lists.

def SocialNetworkData():
    cache_key = SN_CACHE_KEY
    data = cache.get(cache_key)

    if not data:
        data = []

        try:
            for network in SocialNetwork.objects.all():
                data.append({
                    'id': slugify(network.name),
                    'name': network.name,
                    'url': network.url,
                    'identifier': network.identifier,
                    'icon': network.icon
                })
            cache.set(cache_key, data, 60*60*24)
        except:
            # if we haven't yet synced the database, don't worry about this yet
            pass

    return data

def InstantMessengerData():
    cache_key = IM_CACHE_KEY
    data = cache.get(cache_key)

    if not data:
        data = []
        try:
            for network in InstantMessenger.objects.all():
                data.append({
                    'id': slugify(network.name),
                    'name': network.name,
                    'url': network.url,
                    'icon': network.icon
                })
            cache.set(cache_key, data, 60*60*24)
        except:
            # if we haven't yet synced the database, don't worry about this yet
            pass

    return data

class ProfileManager:
    """ Handle raw data for lists of profiles."""
    data = {}

    def _get_choices(self):
        """ List of choices for profile select fields. """
        return [(props['id'], props['name']) for props in self.data]
    choices = property(_get_choices)

class SocialNetworkManager(ProfileManager):
    data = SocialNetworkData()
sn_manager = SocialNetworkManager()

class InstantMessengerManager(ProfileManager):
    data = InstantMessengerData()
im_manager = InstantMessengerManager()

class Profile(models.Model):
    """ Common profile model pieces. """
    data_manager = None

    date_added = models.DateTimeField(_('date added'), auto_now_add=True)
    date_verified = models.DateTimeField(_('date verified'), default=datetime.now)
    is_verified = models.BooleanField(default=False)

    class Meta:
        abstract = True

    def _get_data_item(self):
        # Find profile data for this profile id
        for network in self.data_manager.data:
            if network['id'] == self.network_id:
                return network
        return None
    data_item = property(_get_data_item)

    def _get_name(self):
        # Profile display name
        return self.data_item['name']
    name = property(_get_name)
 
    def _get_url(self):
        # Profile URL with username
        return self.data_item['url'] % self.username
    url = property(_get_url)
    
    def _get_icon_name(self):
        # Icon name
        return self.data_item['icon']
    icon_name = property(_get_icon_name)
 
    def _get_icon(self):
        # Icon URL or link to Google icon service
        if self.icon_name:
            print reverse('elsewhere_img', args=[self.icon_name])
            print self.icon_name
            return reverse('elsewhere_img', args=[self.icon_name])
        return GOOGLE_PROFILE_URL % self.url
    icon = property(_get_icon)

class SocialNetworkProfile(Profile):
    data_manager = sn_manager

    user = models.ForeignKey(User, db_index=True, related_name='social_network_profiles')
    network_id = models.CharField(max_length=16, choices=data_manager.choices, db_index=True)
    username = models.CharField(max_length=64)
    
    def __unicode__(self):
        return self.network_id

class SocialNetworkForm(forms.ModelForm):

    class Meta:
        model = SocialNetworkProfile
        fields = ('network_id', 'username')


class InstantMessengerProfile(Profile):
    data_manager = im_manager

    user = models.ForeignKey(User, db_index=True, related_name='instant_messenger_profiles')
    network_id = models.CharField(max_length=16, choices=data_manager.choices, db_index=True)
    username = models.CharField(max_length=64)

    def __unicode__(self):
        return self.username

class InstantMessengerForm(forms.ModelForm):

    class Meta:
        model = InstantMessengerProfile
        fields = ('network_id', 'username')


class WebsiteProfile(models.Model):
    user = models.ForeignKey(User, db_index=True, related_name='website_profiles')
    name = models.CharField(max_length=64)
    url = models.URLField(verify_exists=True)

    def __unicode__(self):
        return self.url

    def _get_icon(self):
        # No known icons! Just return the Google service URL.
        return GOOGLE_PROFILE_URL % self.url
    icon = property(_get_icon)


class WebsiteForm(forms.ModelForm):

    class Meta:
        model = WebsiteProfile
        fields = ('name', 'url')
########NEW FILE########
__FILENAME__ = urls
import settings
import os

from django.conf.urls.defaults import *
from django.contrib import admin

admin.autodiscover()

urlpatterns = patterns('elsewhere.views',
    (r'^$', 'example'),
)

if settings.DEBUG:
    CUR_DIR = os.path.dirname(__file__)
    IMG_PATH = 'img/'
    IMG_DIR = os.path.join(CUR_DIR, "img")

    urlpatterns += patterns('django.views',
        url(r'^%s(?P<path>.*)' % IMG_PATH, 'static.serve', {'document_root': IMG_DIR}, name='elsewhere_img')
    )
########NEW FILE########
__FILENAME__ = views
from django.http import HttpResponse, HttpResponseRedirect, HttpResponseServerError
from django.template import RequestContext
from django.contrib.auth.decorators import login_required
from django.shortcuts import render_to_response

from elsewhere.models import *


@login_required
def example(request):
    if request.method == 'POST':

        new_data = request.POST.copy()

        # Add forms
        if new_data.get('sn-form') or new_data.get('im-form') or new_data.get('w-form'):

            if new_data.get('sn-form'):
                form = SocialNetworkForm(new_data)
            elif new_data.get('im-form'):
                form = InstantMessengerForm(new_data)
            elif new_data.get('w-form'):
                form = WebsiteForm(new_data)

            if form.is_valid():
                profile = form.save(commit=False)
                profile.user = request.user
                profile.save()
                return HttpResponseRedirect(request.path)
            else:
                ## TODO should probably show the errors
                print form.errors

        # Delete forms
        elif new_data.get('delete-sn-form') or new_data.get('delete-im-form') or new_data.get('delete-w-form'):
            delete_id = request.POST['delete_id']

            if new_data.get('delete-sn-form'):
                request.user.social_network_profiles.get(id=delete_id).delete()
            elif new_data.get('delete-im-form'):
                request.user.instant_messenger_profiles.get(id=delete_id).delete()
            elif new_data.get('delete-w-form'):
                request.user.website_profiles.get(id=delete_id).delete()

            return HttpResponseRedirect(request.path)

        # WTF?
        else:
            return HttpResponseServerError

    # Create blank forms
    sn_form = SocialNetworkForm()
    im_form = InstantMessengerForm()
    w_form = WebsiteForm()

    return render_to_response('elsewhere/example.html', {
        'sn_form': sn_form, 'im_form': im_form, 'w_form': w_form,
    }, context_instance=RequestContext(request))
########NEW FILE########
