__FILENAME__ = models
from django.db import models

# Create your models here.

########NEW FILE########
__FILENAME__ = tests
"""
This file demonstrates writing tests using the unittest module. These will pass
when you run "manage.py test".

Replace this with more appropriate tests for your application.
"""

from django.test import TestCase


class SimpleTest(TestCase):
    def test_basic_addition(self):
        """
        Tests that 1 + 1 always equals 2.
        """
        self.assertEqual(1 + 1, 2)

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import patterns, include, url

from app.views import dashboard, update_profile_image

urlpatterns = patterns('',
    url(r'^dashboard$', dashboard, name='dashboard'),
    url(r'^update_profile_image$', update_profile_image, name='update_profile_image'),
)

########NEW FILE########
__FILENAME__ = views
from django.core.urlresolvers import reverse
from django.template.context import Context, RequestContext
from django.http import HttpResponseRedirect
from django.shortcuts import render_to_response, get_object_or_404
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django import forms
from fanfouapi.models import FFUser
from django.conf import settings

def route(request):
    if request.user.is_authenticated():
        return HttpResponseRedirect(reverse('dashboard'))
    else:
        site_url = 'http://%s' % settings.FF_HOST
        return render_to_response('route.html',
                                  RequestContext(request,
                                                 locals()))

def signout(request):
    logout(request)
    return HttpResponseRedirect(reverse('route'))

@login_required
def update_profile_image(request):
    ffuser = FFUser.objects.get_by_user(request.user)
    api = ffuser.get_api()


    class ProfileImageForm(forms.Form):
        image = forms.ImageField()
        def save(self):
            img = self.cleaned_data['image']
            content = img.read()
            filename = img.name
            if isinstance(filename, unicode):
                filename = filename.encode('utf-8')
            return api.update_profile_image(filename=filename,
                                     content = content,
                                     file_type=img.content_type)
    if request.method == 'POST':
        img = request.FILES.get('image')
        form = ProfileImageForm(request.POST,
                                request.FILES)
        if form.is_valid():
            print form.save()
            return HttpResponseRedirect(reverse('update_profile_image'))
        else:
            print form.errors

    else:
        form = ProfileImageForm()
    u = api.verify_credentials()
    return render_to_response('update_profile_image.html',
                              RequestContext(request, locals()))

@login_required
def dashboard(request):
    return render_to_response('dashboard.html',
                              RequestContext(request,
                                             locals()))

########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python
from django.core.management import execute_manager
import imp
try:
    imp.find_module('settings') # Assumed to be in the same directory.
except ImportError:
    import sys
    sys.stderr.write("Error: Can't find the file 'settings.py' in the directory containing %r. It appears you've customized things.\nYou'll have to run django-admin.py, passing it your settings module.\n" % __file__)
    sys.exit(1)

import settings

if __name__ == "__main__":
    execute_manager(settings)

########NEW FILE########
__FILENAME__ = settings
# Django settings for apitestprj project.

DEBUG = True
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    # ('Your Name', 'your_email@example.com'),
)

MANAGERS = ADMINS

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3', # Add 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'oracle'.
        'NAME': 'fanfou.db',                      # Or path to database file if using sqlite3.
        'USER': '',                      # Not used with sqlite3.
        'PASSWORD': '',                  # Not used with sqlite3.
        'HOST': '',                      # Set to empty string for localhost. Not used with sqlite3.
        'PORT': '',                      # Set to empty string for default. Not used with sqlite3.
    }
}

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# On Unix systems, a value of None will cause Django to use the same
# timezone as the operating system.
# If running in a Windows environment this must be set to the same as your
# system time zone.
TIME_ZONE = 'Asia/Shanghai'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en-us'

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# If you set this to False, Django will not format dates, numbers and
# calendars according to the current locale
USE_L10N = True

# Absolute filesystem path to the directory that will hold user-uploaded files.
# Example: "/home/media/media.lawrence.com/media/"
MEDIA_ROOT = ''

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash.
# Examples: "http://media.lawrence.com/media/", "http://example.com/media/"
MEDIA_URL = ''

# Absolute path to the directory static files should be collected to.
# Don't put anything in this directory yourself; store your static files
# in apps' "static/" subdirectories and in STATICFILES_DIRS.
# Example: "/home/media/media.lawrence.com/static/"
STATIC_ROOT = ''

# URL prefix for static files.
# Example: "http://media.lawrence.com/static/"
STATIC_URL = '/static/'

# URL prefix for admin static files -- CSS, JavaScript and images.
# Make sure to use a trailing slash.
# Examples: "http://foo.com/static/admin/", "/static/admin/".
ADMIN_MEDIA_PREFIX = '/static/admin/'

# Additional locations of static files
STATICFILES_DIRS = (
    # Put strings here, like "/home/html/static" or "C:/www/django/static".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
)

# List of finder classes that know how to find static files in
# various locations.
STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
#    'django.contrib.staticfiles.finders.DefaultStorageFinder',
)

# Make this unique, and don't share it with anybody.
SECRET_KEY = 'k^l@nw5q7hf$7ufo9e7$=@hy9$c-0xpbeyv8=ki41)j9w*jf=p'

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
#     'django.template.loaders.eggs.Loader',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
)

ROOT_URLCONF = 'apitestprj.urls'

TEMPLATE_DIRS = (
    # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
)

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'fanfouapi',
    'app',
    # Uncomment the next line to enable the admin:
    'django.contrib.admin',
    # Uncomment the next line to enable admin documentation:
    # 'django.contrib.admindocs',
)

# A sample logging configuration. The only tangible logging
# performed by this configuration is to send an email to
# the site admins on every HTTP 500 error.
# See http://docs.djangoproject.com/en/dev/topics/logging for
# more details on how to customize your logging configuration.
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'mail_admins': {
            'level': 'ERROR',
            'class': 'django.utils.log.AdminEmailHandler'
        }
    },
    'loggers': {
        'django.request': {
            'handlers': ['mail_admins'],
            'level': 'ERROR',
            'propagate': True,
        },
    }
}

API_HOST = 'api.fanfou.com'
FF_HOST = 'fanfou.com'
SEARCH_HOST = 'fanfou.com'

# PUT key and value there
FF_API_KEY = '' 
FF_API_SECRET = ''

try:
    from  local_settings import *
except ImportError:
    pass


########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import patterns, include, url

from app.views import route, signout

# Uncomment the next two lines to enable the admin:
from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
    # Examples:
    # url(r'^$', 'apitest.views.home', name='home'),
    # url(r'^apitest/', include('apitest.foo.urls')),
    url(r'^logout$', signout, name='logout'),
    # Uncomment the admin/doc line below to enable admin documentation:
    url(r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    url(r'^admin/', include(admin.site.urls)),
                       
    url(r'^auth/', include('fanfouapi.urls')),
    url(r'^$', route, name='route'),
    url(r'^at/', include('app.urls')),
)

########NEW FILE########
__FILENAME__ = admin
from fanfouapi.models import FFUser
from django.contrib import admin


class FFUserAdmin(admin.ModelAdmin):
    """
    """
    list_display = ('loginname', 'screen_name', 'login_time',)
    search_fields = ('screen_name', 'loginname',)


admin.site.register(FFUser, FFUserAdmin)

########NEW FILE########
__FILENAME__ = api

# Copyright 2009-2010 Joshua Roesslein
# See LICENSE for details.

import os
import mimetypes

from django.conf import settings

from fanfouapi.binder import bind_api
from fanfouapi.error import WeibopError
from fanfouapi.parsers import ModelParser

API_HOST = getattr(settings, 'API_HOST', 'api.fanfou.com')
SEARCH_HOST = getattr(settings, 'SEARCH_HOST', 'api.fanfou.com')

class API(object):
    """Fanfou API"""

    def __init__(self, auth_handler=None,
            host=API_HOST, search_host=SEARCH_HOST,
             cache=None, secure=False, api_root='', search_root='',
            retry_count=0, retry_delay=0, retry_errors=None,source=None,
            parser=None, log = None):
        self.auth = auth_handler
        self.host = host
        self.source = source
        if source == None:
            if auth_handler != None:
                self.source = self.auth._consumer.key
        self.search_host = search_host
        self.api_root = api_root
        self.search_root = search_root
        self.cache = cache
        self.secure = secure
        self.retry_count = retry_count
        self.retry_delay = retry_delay
        self.retry_errors = retry_errors
        self.parser = parser or ModelParser()
        self.log = log

    """ statuses/public_timeline """
    public_timeline = bind_api(
        path = '/statuses/public_timeline.json',
        payload_type = 'status', payload_list = True,
        allowed_param = []
    )

    """ statuses/home_timeline """
    home_timeline = bind_api(
        path = '/statuses/home_timeline.json',
        payload_type = 'status', payload_list = True,
        allowed_param = ['since_id', 'max_id', 'count', 'page'],
        require_auth = True
    )

    """ statuses/friends_timeline """
    friends_timeline = bind_api(
        path = '/statuses/friends_timeline.json',
        payload_type = 'status', payload_list = True,
        allowed_param = ['since_id', 'max_id', 'count', 'page'],
        require_auth = True
    )
    """ statuses/comment """
    comment = bind_api(
        path = '/statuses/comment.json',
        method = 'POST',
        payload_type = 'comments',
        allowed_param = ['id', 'cid', 'comment'],
        require_auth = True
    )

    """ statuses/comment_destroy """
    comment_destroy  = bind_api(
        path = '/statuses/comment_destroy/{id}.json',
        method = 'POST',
        payload_type = 'comments',
        allowed_param = ['id'],
        require_auth = True
    )

    """ statuses/comments_timeline """
    comments = bind_api(
        path = '/statuses/comments.json',
        payload_type = 'comments', payload_list = True,
        allowed_param = ['id', 'count', 'page'],
        require_auth = True
    )

    """ statuses/comments_timeline """
    comments_timeline = bind_api(
        path = '/statuses/comments_timeline.json',
        payload_type = 'comments', payload_list = True,
        allowed_param = ['since_id', 'max_id', 'count', 'page'],
        require_auth = True
    )

    """ statuses/comments_by_me """
    comments_by_me = bind_api(
        path = '/statuses/comments_by_me.json',
        payload_type = 'comments', payload_list = True,
        allowed_param = ['since_id', 'max_id', 'count', 'page'],
        require_auth = True
    )

    """ statuses/user_timeline """
    user_timeline = bind_api(
        path = '/statuses/user_timeline.json',
        payload_type = 'status', payload_list = True,
        allowed_param = ['id', 'user_id', 'screen_name', 'since_id',
                          'max_id', 'count', 'page']
    )

    """ statuses/mentions """
    mentions = bind_api(
        path = '/statuses/mentions.json',
        payload_type = 'status', payload_list = True,
        allowed_param = ['since_id', 'max_id', 'count', 'page'],
        require_auth = True
    )

    """ statuses/counts """
    counts = bind_api(
        path = '/statuses/counts.json',
        payload_type = 'counts', payload_list = True,
        allowed_param = ['ids'],
        require_auth = True
    )

    """ statuses/unread """
    unread = bind_api(
        path = '/statuses/unread.json',
        payload_type = 'counts'
    )

    """ statuses/retweeted_by_me """
    retweeted_by_me = bind_api(
        path = '/statuses/retweeted_by_me.json',
        payload_type = 'status', payload_list = True,
        allowed_param = ['since_id', 'max_id', 'count', 'page'],
        require_auth = True
    )

    """ statuses/retweeted_to_me """
    retweeted_to_me = bind_api(
        path = '/statuses/retweeted_to_me.json',
        payload_type = 'status', payload_list = True,
        allowed_param = ['since_id', 'max_id', 'count', 'page'],
        require_auth = True
    )

    """ statuses/retweets_of_me """
    retweets_of_me = bind_api(
        path = '/statuses/retweets_of_me.json',
        payload_type = 'status', payload_list = True,
        allowed_param = ['since_id', 'max_id', 'count', 'page'],
        require_auth = True
    )

    """ statuses/show """
    get_status = bind_api(
        path = '/statuses/show/{id}.json',
        payload_type = 'status',
        allowed_param = ['id']
    )

    """ statuses/update """
    update_status = bind_api(
        path = '/statuses/update.json',
        method = 'POST',
        payload_type = 'status',
        allowed_param = ['status', 'lat', 'long', 'source', 'in_reply_to_status_id', 'repost_status_id'],
        require_auth = True
    )
    """ statuses/upload """
    def upload(self, filename, status, lat=None, long=None, source=None):
        #if source is None:
        #    source=self.source
        headers, post_data = API._pack_image(filename, 1024, status=status, lat=lat, long=long, contentname="photo")
        #args = [status]
        #allowed_param = ['status']
        args = []
        allowed_param = []

        if lat is not None:
            args.append(lat)
            allowed_param.append('lat')

        if long is not None:
            args.append(long)
            allowed_param.append('long')

        if source is not None:
            pass
            #args.append(source)
            #allowed_param.append('source')
        return bind_api(
            path = '/photos/upload.json',
            method = 'POST',
            payload_type = 'status',
            require_auth = True,
            allowed_param = allowed_param
        )(self, *args, post_data=post_data, headers=headers)

    """ statuses/reply """
    reply = bind_api(
        path = '/statuses/reply.json',
        method = 'POST',
        payload_type = 'status',
        allowed_param = ['id', 'cid','comment'],
        require_auth = True
    )

    """ statuses/repost """
    repost = bind_api(
        path = '/statuses/repost.json',
        method = 'POST',
        payload_type = 'status',
        allowed_param = ['id', 'status'],
        require_auth = True
    )

    """ statuses/destroy """
    destroy_status = bind_api(
        path = '/statuses/destroy/{id}.json',
        method = 'DELETE',
        payload_type = 'status',
        allowed_param = ['id'],
        require_auth = True
    )

    """ statuses/retweet """
    retweet = bind_api(
        path = '/statuses/retweet/{id}.json',
        method = 'POST',
        payload_type = 'status',
        allowed_param = ['id'],
        require_auth = True
    )

    """ statuses/retweets """
    retweets = bind_api(
        path = '/statuses/retweets/{id}.json',
        payload_type = 'status', payload_list = True,
        allowed_param = ['id', 'count'],
        require_auth = True
    )

    """ users/show """
    get_user = bind_api(
        path = '/users/show.json',
        payload_type = 'user',
        allowed_param = ['id', 'user_id', 'screen_name']
    )

    """ Get the authenticated user """
    def me(self):
        return self.get_user(screen_name=self.auth.get_username())

    """ users/search """
    search_users = bind_api(
        path = '/users/search.json',
        payload_type = 'user', payload_list = True,
        require_auth = True,
        allowed_param = ['q', 'per_page', 'page']
    )

    """ statuses/friends """
    friends = bind_api(
        path = '/users/friends.json',
        payload_type = 'user', payload_list = True,
        allowed_param = ['id', 'user_id', 'screen_name', 'page', 'cursor']
    )

    """ statuses/followers """
    followers = bind_api(
        path = '/statuses/followers.json',
        payload_type = 'user', payload_list = True,
        allowed_param = ['id', 'user_id', 'screen_name', 'page', 'cursor']
    )

    """ direct_messages """
    direct_messages = bind_api(
        path = '/direct_messages.json',
        payload_type = 'direct_message', payload_list = True,
        allowed_param = ['since_id', 'max_id', 'count', 'page'],
        require_auth = True
    )

    """ direct_messages/sent """
    sent_direct_messages = bind_api(
        path = '/direct_messages/sent.json',
        payload_type = 'direct_message', payload_list = True,
        allowed_param = ['since_id', 'max_id', 'count', 'page'],
        require_auth = True
    )
    """ direct_messages/new """
    new_direct_message = bind_api(
        path = '/direct_messages/new.json',
        method = 'POST',
        payload_type = 'direct_message',
        allowed_param = ['id', 'screen_name', 'user_id', 'text'],
        require_auth = True
    )

    """ direct_messages/destroy """
    destroy_direct_message = bind_api(
        path = '/direct_messages/destroy/{id}.json',
        method = 'DELETE',
        payload_type = 'direct_message',
        allowed_param = ['id'],
        require_auth = True
    )

    """ friendships/create """
    create_friendship = bind_api(
        path = '/friendships/create.json',
        method = 'POST',
        payload_type = 'user',
        allowed_param = ['id', 'user_id', 'screen_name', 'follow'],
        require_auth = True
    )

    """ friendships/destroy """
    destroy_friendship = bind_api(
        path = '/friendships/destroy.json',
        method = 'DELETE',
        payload_type = 'user',
        allowed_param = ['id', 'user_id', 'screen_name'],
        require_auth = True
    )

    """ friendships/exists """
    exists_friendship = bind_api(
        path = '/friendships/exists.json',
        payload_type = 'json',
        allowed_param = ['user_a', 'user_b']
    )

    """ friendships/show """
    show_friendship = bind_api(
        path = '/friendships/show.json',
        payload_type = 'friendship',
        allowed_param = ['source_id', 'source_screen_name',
                          'target_id', 'target_screen_name']
    )

    user_friends = bind_api(
        path = "/users/friends.json",
        payload_type = 'user',
        allowed_param = ['id', 'user_id', 'screen_name', 'cursor', 'count'],
        require_auth = True
    )

    """ friends/ids """
    friends_ids = bind_api(
        path = '/friends/ids.json',
        payload_type = 'user',
        allowed_param = ['id', 'user_id', 'screen_name', 'cursor', 'count'],
        require_auth = True
    )

    """ followers/ids """
    followers_ids = bind_api(
        path = '/followers/ids.json',
        payload_type = 'json',
        allowed_param = ['id', 'page'],
    )

    """ account/verify_credentials """
    def verify_credentials(self):
        try:
            return bind_api(
                path = '/account/verify_credentials.json',
                payload_type = 'user',
                require_auth = True
            )(self)
        except WeibopError:
            return False

    """ account/rate_limit_status """
    rate_limit_status = bind_api(
        path = '/account/rate_limit_status.json',
        payload_type = 'json'
    )

    """ account/update_delivery_device """
    set_delivery_device = bind_api(
        path = '/account/update_delivery_device.json',
        method = 'POST',
        allowed_param = ['device'],
        payload_type = 'user',
        require_auth = True
    )

    """ account/update_profile_colors """
    update_profile_colors = bind_api(
        path = '/account/update_profile_colors.json',
        method = 'POST',
        payload_type = 'user',
        allowed_param = ['profile_background_color', 'profile_text_color',
                          'profile_link_color', 'profile_sidebar_fill_color',
                          'profile_sidebar_border_color'],
        require_auth = True
    )

    """ account/update_profile_image """
    def update_profile_image(self, filename, content=None, file_type='image/jpeg'):
        if content is None:
            headers, post_data = API._pack_image(filename=filename, max_size=1024, source=self.source)
        else:
            headers, post_data = API._pack_image_content(filename=filename, content=content, max_size=1024, 
                                                         source=self.source,
                                                         file_type=file_type)
        return bind_api(
            path = '/account/update_profile_image.json',
            method = 'POST',
            payload_type = 'user',
            require_auth = True
        )(self, post_data=post_data, headers=headers)

    """ account/update_profile_background_image """
    def update_profile_background_image(self, filename, *args, **kargs):
        headers, post_data = API._pack_image(filename, 800)
        bind_api(
            path = '/account/update_profile_background_image.json',
            method = 'POST',
            payload_type = 'user',
            allowed_param = ['tile'],
            require_auth = True
        )(self, post_data=post_data, headers=headers)

    """ account/update_profile """
    update_profile = bind_api(
        path = '/account/update_profile.json',
        method = 'POST',
        payload_type = 'user',
        allowed_param = ['name', 'url', 'location', 'description'],
        require_auth = True
    )

    """ favorites """
    favorites = bind_api(
        path = '/favorites.json',
        payload_type = 'status', payload_list = True,
        allowed_param = ['id', 'page']
    )

    """ favorites/create """
    create_favorite = bind_api(
        path = '/favorites/create/{id}.json',
        method = 'POST',
        payload_type = 'status',
        allowed_param = ['id'],
        require_auth = True
    )

    """ favorites/destroy """
    destroy_favorite = bind_api(
        path = '/favorites/destroy/{id}.json',
        method = 'DELETE',
        payload_type = 'status',
        allowed_param = ['id'],
        require_auth = True
    )

    """ notifications/follow """
    enable_notifications = bind_api(
        path = '/notifications/follow.json',
        method = 'POST',
        payload_type = 'user',
        allowed_param = ['id', 'user_id', 'screen_name'],
        require_auth = True
    )

    """ notifications/leave """
    disable_notifications = bind_api(
        path = '/notifications/leave.json',
        method = 'POST',
        payload_type = 'user',
        allowed_param = ['id', 'user_id', 'screen_name'],
        require_auth = True
    )

    """ blocks/create """
    create_block = bind_api(
        path = '/blocks/create.json',
        method = 'POST',
        payload_type = 'user',
        allowed_param = ['id', 'user_id', 'screen_name'],
        require_auth = True
    )

    """ blocks/destroy """
    destroy_block = bind_api(
        path = '/blocks/destroy.json',
        method = 'DELETE',
        payload_type = 'user',
        allowed_param = ['id', 'user_id', 'screen_name'],
        require_auth = True
    )

    """ blocks/exists """
    def exists_block(self, *args, **kargs):
        try:
            bind_api(
                path = '/blocks/exists.json',
                allowed_param = ['id', 'user_id', 'screen_name'],
                require_auth = True
            )(self, *args, **kargs)
        except WeibopError:
            return False
        return True

    """ blocks/blocking """
    blocks = bind_api(
        path = '/blocks/blocking.json',
        payload_type = 'user', payload_list = True,
        allowed_param = ['page'],
        require_auth = True
    )

    """ blocks/blocking/ids """
    blocks_ids = bind_api(
        path = '/blocks/blocking/ids.json',
        payload_type = 'json',
        require_auth = True
    )

    """ statuses/repost """
    report_spam = bind_api(
        path = '/report_spam.json',
        method = 'POST',
        payload_type = 'user',
        allowed_param = ['id', 'user_id', 'screen_name'],
        require_auth = True
    )

    """ saved_searches """
    saved_searches = bind_api(
        path = '/saved_searches.json',
        payload_type = 'saved_search', payload_list = True,
        require_auth = True
    )

    """ saved_searches/show """
    get_saved_search = bind_api(
        path = '/saved_searches/show/{id}.json',
        payload_type = 'saved_search',
        allowed_param = ['id'],
        require_auth = True
    )

    """ saved_searches/create """
    create_saved_search = bind_api(
        path = '/saved_searches/create.json',
        method = 'POST',
        payload_type = 'saved_search',
        allowed_param = ['query'],
        require_auth = True
    )

    """ saved_searches/destroy """
    destroy_saved_search = bind_api(
        path = '/saved_searches/destroy/{id}.json',
        method = 'DELETE',
        payload_type = 'saved_search',
        allowed_param = ['id'],
        require_auth = True
    )

    """ help/test """
    def test(self):
        try:
            bind_api(
                path = '/help/test.json',
            )(self)
        except WeibopError:
            return False
        return True

    def create_list(self, *args, **kargs):
        return bind_api(
            path = '/%s/lists.json' % self.auth.get_username(),
            method = 'POST',
            payload_type = 'list',
            allowed_param = ['name', 'mode', 'description'],
            require_auth = True
        )(self, *args, **kargs)

    def destroy_list(self, slug):
        return bind_api(
            path = '/%s/lists/%s.json' % (self.auth.get_username(), slug),
            method = 'DELETE',
            payload_type = 'list',
            require_auth = True
        )(self)

    def update_list(self, slug, *args, **kargs):
        return bind_api(
            path = '/%s/lists/%s.json' % (self.auth.get_username(), slug),
            method = 'POST',
            payload_type = 'list',
            allowed_param = ['name', 'mode', 'description'],
            require_auth = True
        )(self, *args, **kargs)

    lists = bind_api(
        path = '/{user}/lists.json',
        payload_type = 'list', payload_list = True,
        allowed_param = ['user', 'cursor'],
        require_auth = True
    )

    lists_memberships = bind_api(
        path = '/{user}/lists/memberships.json',
        payload_type = 'list', payload_list = True,
        allowed_param = ['user', 'cursor'],
        require_auth = True
    )

    lists_subscriptions = bind_api(
        path = '/{user}/lists/subscriptions.json',
        payload_type = 'list', payload_list = True,
        allowed_param = ['user', 'cursor'],
        require_auth = True
    )

    list_timeline = bind_api(
        path = '/{owner}/lists/{slug}/statuses.json',
        payload_type = 'status', payload_list = True,
        allowed_param = ['owner', 'slug', 'since_id', 'max_id', 'count', 'page']
    )

    get_list = bind_api(
        path = '/{owner}/lists/{slug}.json',
        payload_type = 'list',
        allowed_param = ['owner', 'slug']
    )

    def add_list_member(self, slug, *args, **kargs):
        return bind_api(
            path = '/%s/%s/members.json' % (self.auth.get_username(), slug),
            method = 'POST',
            payload_type = 'list',
            allowed_param = ['id'],
            require_auth = True
        )(self, *args, **kargs)

    def remove_list_member(self, slug, *args, **kargs):
        return bind_api(
            path = '/%s/%s/members.json' % (self.auth.get_username(), slug),
            method = 'DELETE',
            payload_type = 'list',
            allowed_param = ['id'],
            require_auth = True
        )(self, *args, **kargs)

    list_members = bind_api(
        path = '/{owner}/{slug}/members.json',
        payload_type = 'user', payload_list = True,
        allowed_param = ['owner', 'slug', 'cursor']
    )

    def is_list_member(self, owner, slug, user_id):
        try:
            return bind_api(
                path = '/%s/%s/members/%s.json' % (owner, slug, user_id),
                payload_type = 'user'
            )(self)
        except WeibopError:
            return False

    subscribe_list = bind_api(
        path = '/{owner}/{slug}/subscribers.json',
        method = 'POST',
        payload_type = 'list',
        allowed_param = ['owner', 'slug'],
        require_auth = True
    )

    unsubscribe_list = bind_api(
        path = '/{owner}/{slug}/subscribers.json',
        method = 'DELETE',
        payload_type = 'list',
        allowed_param = ['owner', 'slug'],
        require_auth = True
    )

    list_subscribers = bind_api(
        path = '/{owner}/{slug}/subscribers.json',
        payload_type = 'user', payload_list = True,
        allowed_param = ['owner', 'slug', 'cursor']
    )

    def is_subscribed_list(self, owner, slug, user_id):
        try:
            return bind_api(
                path = '/%s/%s/subscribers/%s.json' % (owner, slug, user_id),
                payload_type = 'user'
            )(self)
        except WeibopError:
            return False

    """ trends/available """
    trends_available = bind_api(
        path = '/trends/available.json',
        payload_type = 'json',
        allowed_param = ['lat', 'long']
    )

    """ trends/location """
    trends_location = bind_api(
        path = '/trends/{woeid}.json',
        payload_type = 'json',
        allowed_param = ['woeid']
    )

    """ search """
    search = bind_api(
        search_api = True,
        path = '/search.json',
        payload_type = 'search_result', payload_list = True,
        allowed_param = ['q', 'lang', 'locale', 'rpp', 'page', 'since_id', 'geocode', 'show_user']
    )
    search.pagination_mode = 'page'

    """ trends """
    trends = bind_api(
        search_api = True,
        path = '/trends.json',
        payload_type = 'json'
    )

    """ trends/current """
    trends_current = bind_api(
        search_api = True,
        path = '/trends/current.json',
        payload_type = 'json',
        allowed_param = ['exclude']
    )

    """ trends/daily """
    trends_daily = bind_api(
        search_api = True,
        path = '/trends/daily.json',
        payload_type = 'json',
        allowed_param = ['date', 'exclude']
    )

    """ trends/weekly """
    trends_weekly = bind_api(
        search_api = True,
        path = '/trends/weekly.json',
        payload_type = 'json',
        allowed_param = ['date', 'exclude']
    )

    """ provinces """
    provinces = bind_api(
        path = '/provinces.json',
        payload_type = 'json'
    )

    """ Internal use only """
    @staticmethod
    def _pack_image(filename, max_size, source=None, status=None, lat=None, long=None, contentname="image"):
        """Pack image from file into multipart-formdata post body"""
        # image must be less than 700kb in size
        try:
            if os.path.getsize(filename) > (max_size * 1024):
                raise WeibopError('File is too big, must be less than 700kb.')
        #except os.error, e:
        except os.error:
            raise WeibopError('Unable to access file')

        # image must be gif, jpeg, or png
        file_type = mimetypes.guess_type(filename)
        if file_type is None:
            raise WeibopError('Could not determine file type')
        file_type = file_type[0]
        if file_type not in ['image/gif', 'image/jpeg', 'image/png']:
            raise WeibopError('Invalid file type for image: %s' % file_type)
        fp = open(filename, 'rb')
        content = fp.read()
        r = API._pack_image_content(filename, content, max_size, source=source,
                                    status=status, lat=lat, long=long, contentname=contentname,
                                    file_type=file_type)
        fp.close()
        return r
        
    @staticmethod
    def _pack_image_content(filename, content, max_size, source=None, status=None, lat=None, long=None, contentname="image", file_type=None):
        # build the mulitpart-formdata body
        BOUNDARY = 'Fanfouff3ePy--'
        body = []
        if status is not None:
            body.append('--' + BOUNDARY)
            body.append('Content-Disposition: form-data; name="status"')
            body.append('Content-Type: text/plain; charset=US-ASCII')
            body.append('Content-Transfer-Encoding: 8bit')
            body.append('')
            body.append(status)
        if source is not None:
            body.append('--' + BOUNDARY)
            body.append('Content-Disposition: form-data; name="source"')
            body.append('Content-Type: text/plain; charset=US-ASCII')
            body.append('Content-Transfer-Encoding: 8bit')
            body.append('')
            body.append(source)
        if lat is not None:
            body.append('--' + BOUNDARY)
            body.append('Content-Disposition: form-data; name="lat"')
            body.append('Content-Type: text/plain; charset=US-ASCII')
            body.append('Content-Transfer-Encoding: 8bit')
            body.append('')
            body.append(lat)
        if long is not None:
            body.append('--' + BOUNDARY)
            body.append('Content-Disposition: form-data; name="long"')
            body.append('Content-Type: text/plain; charset=US-ASCII')
            body.append('Content-Transfer-Encoding: 8bit')
            body.append('')
            body.append(long)
        body.append('--' + BOUNDARY)
        body.append('Content-Disposition: form-data; name="'+ contentname +'"; filename="%s"' % filename)
        body.append('Content-Type: %s' % file_type)
        body.append('Content-Transfer-Encoding: binary')
        body.append('')
        body.append(content)
        body.append('--' + BOUNDARY + '--')
        body.append('')
        body.append('--' + BOUNDARY + '--')
        body.append('')
        body = '\r\n'.join(body)
        # build headers
        headers = {
            'Content-Type': 'multipart/form-data; boundary=' + BOUNDARY,
            'Content-Length': len(body)
        }
        return headers, body


########NEW FILE########
__FILENAME__ = auth
# Copyright 2009-2010 Joshua Roesslein
# See LICENSE for details.
import sys
import re
from urllib2 import Request, urlopen
import base64

from django.conf import settings

from fanfouapi import oauth
from fanfouapi.error import WeibopError
from fanfouapi.api import API

API_HOST = getattr(settings, 'API_HOST', 'api.fanfou.com')
SEARCH_HOST = getattr(settings, 'SEARCH_HOST', 'api.fanfou.com')
FF_HOST = getattr(settings, 'FF_HOST', 'fanfou.com')
OAUTH_HOST = getattr(settings, 'OAUTH_HOST', FF_HOST)
OAUTH_ROOT = getattr(settings, 'OAUTH_ROOT', '/oauth/')

class AuthHandler(object):
    def apply_auth(self, url, method, headers, parameters):
        """Apply authentication headers to request"""
        raise NotImplementedError

    def get_username(self):
        """Return the username of the authenticated user"""
        raise NotImplementedError

class BasicAuthHandler(AuthHandler):
    def __init__(self, username, password):
        self.username = username
        self._b64up = base64.b64encode('%s:%s' % (username, password))

    def apply_auth(self, url, method, headers, parameters):
        headers['Authorization'] = 'Basic %s' % self._b64up
        
    def get_username(self):
        return self.username


class OAuthHandler(AuthHandler):
    """OAuth authentication handler"""

    def __init__(self, consumer_key, consumer_secret, callback=None, secure=False):
        self._consumer = oauth.OAuthConsumer(consumer_key, consumer_secret)
        self._sigmethod = oauth.OAuthSignatureMethod_HMAC_SHA1()
        self.request_token = None
        self.access_token = None
        self.callback = callback
        self.username = None
        self.secure = secure

    def _get_oauth_url(self, endpoint):
        if self.secure:
            prefix = 'https://'
        else:
            prefix = 'http://'

        return prefix + OAUTH_HOST + OAUTH_ROOT + endpoint

    def apply_auth(self, url, method, headers, parameters):
        request = oauth.OAuthRequest.from_consumer_and_token(
            self._consumer, http_url=url, http_method=method,
            token=self.access_token, parameters=parameters
        )
        request.sign_request(self._sigmethod, self._consumer, self.access_token)
        headers.update(request.to_header())

    def _get_request_token(self):
        try:
            url = self._get_oauth_url('request_token')
            request = oauth.OAuthRequest.from_consumer_and_token(
                self._consumer, http_url=url, callback=self.callback
            )
            request.sign_request(self._sigmethod, self._consumer, None)
            resp = urlopen(Request(url, headers=request.to_header()))
            data = resp.read()
            return oauth.OAuthToken.from_string(data)
        except Exception, e:
            import traceback
            traceback.print_exc()
            print >>sys.stderr, url
            raise WeibopError(e)

    def set_request_token(self, key, secret):
        self.request_token = oauth.OAuthToken(key, secret)

    def set_access_token(self, key, secret):
        self.access_token = oauth.OAuthToken(key, secret)

    def get_authorization_url(self, signin_with_twitter=False, callback=None):
        """Get the authorization URL to redirect the user"""
        try:
            # get the request token
            self.request_token = self._get_request_token()
            # build auth request and return as url
            if signin_with_twitter:
                url = self._get_oauth_url('authenticate')
            else:
                url = self._get_oauth_url('authorize')
            request = oauth.OAuthRequest.from_token_and_callback(
                token=self.request_token, http_url=url,
                callback=callback
            )

            return request.to_url()
        except Exception, e:
            import traceback
            traceback.print_exc()
            raise WeibopError(e)

    def get_access_token(self, verifier=None):
        """
        After user has authorized the request token, get access token
        with user supplied verifier.
        """
        try:
            url = self._get_oauth_url('access_token')

            # build request
            request = oauth.OAuthRequest.from_consumer_and_token(
                self._consumer,
                token=self.request_token, http_url=url,
                verifier=str(verifier)
            )
            request.sign_request(self._sigmethod, self._consumer, self.request_token)
            # send request                        
            resp = urlopen(Request(url, headers=request.to_header()))
            data = resp.read()
            self.access_token = oauth.OAuthToken.from_string(data)
            return self.access_token
        except Exception, e:
            import traceback
            traceback.print_exc()
            raise WeibopError(e)
        
    def setToken(self, token, tokenSecret):
        self.access_token = oauth.OAuthToken(token, tokenSecret)
        
    def get_username(self):
        if self.username is None:
            api = API(self)
            user = api.verify_credentials()
            if user:
                self.username = user.screen_name
            else:
                raise WeibopError("Unable to get username, invalid oauth token!")
        return self.username

def xauth_request_to_header(request, realm=''):
    """Serialize as a header for an HTTPAuth request."""
    auth_header = 'OAuth realm="%s"' % realm
    # Add the oauth parameters.
    if request.parameters:
        for k, v in request.parameters.iteritems():
            if k.startswith('oauth_') or k.startswith('x_auth_'):
                auth_header += ', %s="%s"' % (k, oauth.escape(str(v)))
    if settings.DEBUG:
        print '[DEBUG]', 'OAuth header:', auth_header
    return {'Authorization': auth_header}

def xauth(username, passwd):
    """
    returns {'key': ..., 'secret': '...'} if successed
    or 
    None if xauth failed 
    """
    access_token_url = 'http://' + FF_HOST + '/oauth/access_token'
    verify_url = 'http://' + API_HOST+ '/account/verify_credentials.xml'

    consumer = oauth.OAuthConsumer(settings.FF_API_KEY,
                                   settings.FF_API_SECRET)
    params = {}
    params["x_auth_username"] = username
    params["x_auth_password"] = passwd
    params["x_auth_mode"] = 'client_auth'
    request = oauth.OAuthRequest.from_consumer_and_token(consumer,
                                                         http_url=access_token_url,
                                                         parameters=params)
    signature_method = oauth.OAuthSignatureMethod_HMAC_SHA1()
    request.sign_request(signature_method, consumer, None)
    headers=xauth_request_to_header(request)
    resp = urlopen(Request(access_token_url, headers=headers))
    token = resp.read()
    m = re.match(r'oauth_token=(?P<key>.+?)&oauth_token_secret=(?P<secret>.+)', token)
    if m:
        return m.groupdict()

########NEW FILE########
__FILENAME__ = binder

# Copyright 2009-2010 Joshua Roesslein
# See LICENSE for details.

import httplib
import urllib
import time
import re
from fanfouapi.error import WeibopError
from fanfouapi.utils import convert_to_utf8_str

re_path_template = re.compile('{\w+}')


def bind_api(**config):

    class APIMethod(object):

        path = config['path']
        payload_type = config.get('payload_type', None)
        payload_list = config.get('payload_list', False)
        allowed_param = config.get('allowed_param', [])
        method = config.get('method', 'GET')
        require_auth = config.get('require_auth', False)
        search_api = config.get('search_api', False)

        def __init__(self, api, args, kargs):
            # If authentication is required and no credentials
            # are provided, throw an error.
            if self.require_auth and not api.auth:
                raise WeibopError('Authentication required!')

            self.api = api
            self.post_data = kargs.pop('post_data', None)
            self.retry_count = kargs.pop('retry_count', api.retry_count)
            self.retry_delay = kargs.pop('retry_delay', api.retry_delay)
            self.retry_errors = kargs.pop('retry_errors', api.retry_errors)
            self.headers = kargs.pop('headers', {})
            self.build_parameters(args, kargs)
            # Pick correct URL root to use
            if self.search_api:
                self.api_root = api.search_root
            else:
                self.api_root = api.api_root

            # Perform any path variable substitution
            self.build_path()

            if api.secure:
                self.scheme = 'https://'
            else:
                self.scheme = 'http://'

            if self.search_api:
                self.host = api.search_host
            else:
                self.host = api.host

            # Manually set Host header to fix an issue in python 2.5
            # or older where Host is set including the 443 port.
            # This causes Twitter to issue 301 redirect.
            # See Issue http://github.com/joshthecoder/tweepy/issues/#issue/12
            self.headers['Host'] = self.host

        def build_parameters(self, args, kargs):
            self.parameters = {}
            for idx, arg in enumerate(args):
                try:
                    self.parameters[self.allowed_param[idx]] = convert_to_utf8_str(arg)
                except IndexError:
                    raise WeibopError('Too many parameters supplied!')

            for k, arg in kargs.items():
                if arg is None:
                    continue
                if k in self.parameters:
                    raise WeibopError('Multiple values for parameter %s supplied!' % k)

                self.parameters[k] = convert_to_utf8_str(arg)

        def build_path(self):
            for variable in re_path_template.findall(self.path):
                name = variable.strip('{}')

                if name == 'user' and self.api.auth:
                    value = self.api.auth.get_username()
                else:
                    try:
                        value = urllib.quote(self.parameters[name])
                    except KeyError:
                        raise WeibopError('No parameter value found for path variable: %s' % name)
                    del self.parameters[name]

                self.path = self.path.replace(variable, value)

        def execute(self):
            # Build the request URL
            url = self.api_root + self.path
            #if self.api.source is not None:
            #    self.parameters.setdefault('source',self.api.source)

            if len(self.parameters):
                if self.method == 'GET':
                    url = '%s?%s' % (url, urllib.urlencode(self.parameters))
                else:
                    self.headers.setdefault("User-Agent","python")
                    if self.post_data is None:
                        self.headers.setdefault("Accept","text/html")
                        self.headers.setdefault("Content-Type","application/x-www-form-urlencoded")
                        self.post_data = urllib.urlencode(self.parameters)
            # Query the cache if one is available
            # and this request uses a GET method.
            if self.api.cache and self.method == 'GET':
                cache_result = self.api.cache.get(url)
                # if cache result found and not expired, return it
                if cache_result:
                    # must restore api reference
                    if isinstance(cache_result, list):
                        for result in cache_result:
                            result._api = self.api
                    else:
                        cache_result._api = self.api
                    return cache_result
                #urllib.urlencode(self.parameters)
            # Continue attempting request until successful
            # or maximum number of retries is reached.
            sTime = time.time()
            retries_performed = 0
            while retries_performed < self.retry_count + 1:
                # Open connection
                # FIXME: add timeout
                if self.api.secure:
                    conn = httplib.HTTPSConnection(self.host)
                else:
                    conn = httplib.HTTPConnection(self.host)
                # Apply authentication
                if self.api.auth:
                    self.api.auth.apply_auth(
                            self.scheme + self.host + url,
                            self.method, self.headers, self.parameters
                    )
                # Execute request
                try:
                    conn.request(self.method, url, headers=self.headers, body=self.post_data)
                    resp = conn.getresponse()
                except Exception, e:
                    import traceback
                    traceback.print_exc()
                    raise WeibopError('Failed to send request: %s' % e + "url=" + str(url) +",self.headers="+ str(self.headers))

                # Exit request loop if non-retry error code
                if self.retry_errors:
                    if resp.status not in self.retry_errors: break
                else:
                    if resp.status == 200: break

                # Sleep before retrying request again
                time.sleep(self.retry_delay)
                retries_performed += 1

            # If an error was returned, throw an exception
            body = resp.read()
            self.api.last_response = resp
            if self.api.log is not None:
                requestUrl = "URL:http://"+ self.host + url
                eTime = '%.0f' % ((time.time() - sTime) * 1000)
                postData = ""
                if self.post_data is not None:
                    postData = ",post:"+ self.post_data[0:500]
                self.api.log.debug(requestUrl +",time:"+ str(eTime)+ postData+",result:"+ body )
            if resp.status != 200:
                try:
                    print body
                    json = self.api.parser.parse_error(self, body)
                    error_code =  json['error_code']
                    error =  json['error']
                    error_msg = 'error_code:' + error_code +','+ error
                except Exception:
                    error_msg = "Fanfou error response: status code = %s" % resp.status
                raise WeibopError(error_msg)

            # Parse the response payload
            result = self.api.parser.parse(self, body)
            conn.close()

            # Store result into cache if one is available.
            if self.api.cache and self.method == 'GET' and result:
                self.api.cache.store(url, result)
            return result

    def _call(api, *args, **kargs):

        method = APIMethod(api, args, kargs)
        return method.execute()


    # Set pagination mode
    if 'cursor' in APIMethod.allowed_param:
        _call.pagination_mode = 'cursor'
    elif 'page' in APIMethod.allowed_param:
        _call.pagination_mode = 'page'

    return _call


########NEW FILE########
__FILENAME__ = cache

# Copyright 2009-2010 Joshua Roesslein
# See LICENSE for details.

import time
import threading
import os
import cPickle as pickle

try:
    import hashlib
except ImportError:
    # python 2.4
    import md5 as hashlib

try:
    import fcntl
except ImportError:
    # Probably on a windows system
    # TODO: use win32file
    pass


class Cache(object):
    """Cache interface"""

    def __init__(self, timeout=60):
        """Initialize the cache
            timeout: number of seconds to keep a cached entry
        """
        self.timeout = timeout

    def store(self, key, value):
        """Add new record to cache
            key: entry key
            value: data of entry
        """
        raise NotImplementedError

    def get(self, key, timeout=None):
        """Get cached entry if exists and not expired
            key: which entry to get
            timeout: override timeout with this value [optional]
        """
        raise NotImplementedError

    def count(self):
        """Get count of entries currently stored in cache"""
        raise NotImplementedError

    def cleanup(self):
        """Delete any expired entries in cache."""
        raise NotImplementedError

    def flush(self):
        """Delete all cached entries"""
        raise NotImplementedError


class MemoryCache(Cache):
    """In-memory cache"""

    def __init__(self, timeout=60):
        Cache.__init__(self, timeout)
        self._entries = {}
        self.lock = threading.Lock()

    def __getstate__(self):
        # pickle
        return {'entries': self._entries, 'timeout': self.timeout}

    def __setstate__(self, state):
        # unpickle
        self.lock = threading.Lock()
        self._entries = state['entries']
        self.timeout = state['timeout']

    def _is_expired(self, entry, timeout):
        return timeout > 0 and (time.time() - entry[0]) >= timeout

    def store(self, key, value):
        self.lock.acquire()
        self._entries[key] = (time.time(), value)
        self.lock.release()

    def get(self, key, timeout=None):
        self.lock.acquire()
        try:
            # check to see if we have this key
            entry = self._entries.get(key)
            if not entry:
                # no hit, return nothing
                return None

            # use provided timeout in arguments if provided
            # otherwise use the one provided during init.
            if timeout is None:
                timeout = self.timeout

            # make sure entry is not expired
            if self._is_expired(entry, timeout):
                # entry expired, delete and return nothing
                del self._entries[key]
                return None

            # entry found and not expired, return it
            return entry[1]
        finally:
            self.lock.release()

    def count(self):
        return len(self._entries)

    def cleanup(self):
        self.lock.acquire()
        try:
            for k, v in self._entries.items():
                if self._is_expired(v, self.timeout):
                    del self._entries[k]
        finally:
            self.lock.release()

    def flush(self):
        self.lock.acquire()
        self._entries.clear()
        self.lock.release()


class FileCache(Cache):
    """File-based cache"""

    # locks used to make cache thread-safe
    cache_locks = {}

    def __init__(self, cache_dir, timeout=60):
        Cache.__init__(self, timeout)
        if os.path.exists(cache_dir) is False:
            os.mkdir(cache_dir)
        self.cache_dir = cache_dir
        if cache_dir in FileCache.cache_locks:
            self.lock = FileCache.cache_locks[cache_dir]
        else:
            self.lock = threading.Lock()
            FileCache.cache_locks[cache_dir] = self.lock

        if os.name == 'posix':
            self._lock_file = self._lock_file_posix
            self._unlock_file = self._unlock_file_posix
        elif os.name == 'nt':
            self._lock_file = self._lock_file_win32
            self._unlock_file = self._unlock_file_win32
        else:
            print 'Warning! FileCache locking not supported on this system!'
            self._lock_file = self._lock_file_dummy
            self._unlock_file = self._unlock_file_dummy

    def _get_path(self, key):
        md5 = hashlib.md5()
        md5.update(key)
        return os.path.join(self.cache_dir, md5.hexdigest())

    def _lock_file_dummy(self, path, exclusive=True):
        return None

    def _unlock_file_dummy(self, lock):
        return

    def _lock_file_posix(self, path, exclusive=True):
        lock_path = path + '.lock'
        if exclusive is True:
            f_lock = open(lock_path, 'w')
            fcntl.lockf(f_lock, fcntl.LOCK_EX)
        else:
            f_lock = open(lock_path, 'r')
            fcntl.lockf(f_lock, fcntl.LOCK_SH)
        if os.path.exists(lock_path) is False:
            f_lock.close()
            return None
        return f_lock

    def _unlock_file_posix(self, lock):
        lock.close()

    def _lock_file_win32(self, path, exclusive=True):
        # TODO: implement
        return None

    def _unlock_file_win32(self, lock):
        # TODO: implement
        return

    def _delete_file(self, path):
        os.remove(path)
        if os.path.exists(path + '.lock'):
            os.remove(path + '.lock')

    def store(self, key, value):
        path = self._get_path(key)
        self.lock.acquire()
        try:
            # acquire lock and open file
            f_lock = self._lock_file(path)
            datafile = open(path, 'wb')

            # write data
            pickle.dump((time.time(), value), datafile)

            # close and unlock file
            datafile.close()
            self._unlock_file(f_lock)
        finally:
            self.lock.release()

    def get(self, key, timeout=None):
        return self._get(self._get_path(key), timeout)

    def _get(self, path, timeout):
        if os.path.exists(path) is False:
            # no record
            return None
        self.lock.acquire()
        try:
            # acquire lock and open
            f_lock = self._lock_file(path, False)
            datafile = open(path, 'rb')

            # read pickled object
            created_time, value = pickle.load(datafile)
            datafile.close()

            # check if value is expired
            if timeout is None:
                timeout = self.timeout
            if timeout > 0 and (time.time() - created_time) >= timeout:
                # expired! delete from cache
                value = None
                self._delete_file(path)

            # unlock and return result
            self._unlock_file(f_lock)
            return value
        finally:
            self.lock.release()

    def count(self):
        c = 0
        for entry in os.listdir(self.cache_dir):
            if entry.endswith('.lock'):
                continue
            c += 1
        return c

    def cleanup(self):
        for entry in os.listdir(self.cache_dir):
            if entry.endswith('.lock'):
                continue
            self._get(os.path.join(self.cache_dir, entry), None)

    def flush(self):
        for entry in os.listdir(self.cache_dir):
            if entry.endswith('.lock'):
                continue
            self._delete_file(os.path.join(self.cache_dir, entry))


########NEW FILE########
__FILENAME__ = cursor

# Copyright 2009-2010 Joshua Roesslein
# See LICENSE for details.

from fanfouapi.error import WeibopError

class Cursor(object):
    """Pagination helper class"""

    def __init__(self, method, *args, **kargs):
        if hasattr(method, 'pagination_mode'):
            if method.pagination_mode == 'cursor':
                self.iterator = CursorIterator(method, args, kargs)
            else:
                self.iterator = PageIterator(method, args, kargs)
        else:
            raise WeibopError('This method does not perform pagination')

    def pages(self, limit=0):
        """Return iterator for pages"""
        if limit > 0:
            self.iterator.limit = limit
        return self.iterator

    def items(self, limit=0):
        """Return iterator for items in each page"""
        i = ItemIterator(self.iterator)
        i.limit = limit
        return i

class BaseIterator(object):

    def __init__(self, method, args, kargs):
        self.method = method
        self.args = args
        self.kargs = kargs
        self.limit = 0

    def next(self):
        raise NotImplementedError

    def prev(self):
        raise NotImplementedError

    def __iter__(self):
        return self

class CursorIterator(BaseIterator):

    def __init__(self, method, args, kargs):
        BaseIterator.__init__(self, method, args, kargs)
        self.next_cursor = -1
        self.prev_cursor = 0
        self.count = 0

    def next(self):
        if self.next_cursor == 0 or (self.limit and self.count == self.limit):
            raise StopIteration
        data, cursors = self.method(
                cursor=self.next_cursor, *self.args, **self.kargs
        )
        self.prev_cursor, self.next_cursor = cursors
        if len(data) == 0:
            raise StopIteration
        self.count += 1
        return data

    def prev(self):
        if self.prev_cursor == 0:
            raise WeibopError('Can not page back more, at first page')
        data, self.next_cursor, self.prev_cursor = self.method(
                cursor=self.prev_cursor, *self.args, **self.kargs
        )
        self.count -= 1
        return data

class PageIterator(BaseIterator):

    def __init__(self, method, args, kargs):
        BaseIterator.__init__(self, method, args, kargs)
        self.current_page = 0

    def next(self):
        self.current_page += 1
        items = self.method(page=self.current_page, *self.args, **self.kargs)
        if len(items) == 0 or (self.limit > 0 and self.current_page > self.limit):
            raise StopIteration
        return items

    def prev(self):
        if (self.current_page == 1):
            raise WeibopError('Can not page back more, at first page')
        self.current_page -= 1
        return self.method(page=self.current_page, *self.args, **self.kargs)

class ItemIterator(BaseIterator):

    def __init__(self, page_iterator):
        self.page_iterator = page_iterator
        self.limit = 0
        self.current_page = None
        self.page_index = -1
        self.count = 0

    def next(self):
        if self.limit > 0 and self.count == self.limit:
            raise StopIteration
        if self.current_page is None or self.page_index == len(self.current_page) - 1:
            # Reached end of current page, get the next page...
            self.current_page = self.page_iterator.next()
            self.page_index = -1
        self.page_index += 1
        self.count += 1
        return self.current_page[self.page_index]

    def prev(self):
        if self.current_page is None:
            raise WeibopError('Can not go back more, at first page')
        if self.page_index == 0:
            # At the beginning of the current page, move to next...
            self.current_page = self.page_iterator.prev()
            self.page_index = len(self.current_page)
            if self.page_index == 0:
                raise WeibopError('No more items')
        self.page_index -= 1
        self.count -= 1
        return self.current_page[self.page_index]


########NEW FILE########
__FILENAME__ = error

# Copyright 2009-2010 Joshua Roesslein
# See LICENSE for details.

class WeibopError(Exception):
    """Weibopy exception"""

    def __init__(self, reason):
        if isinstance(reason, basestring):
            self.reason = reason.encode('utf-8')
        else:
            self.reason = str(reason)

    def __str__(self):
        return self.reason


########NEW FILE########
__FILENAME__ = callapi
from django.core.management.base import BaseCommand
from django.conf import settings
from django.utils.encoding import smart_str
import sys, urllib, re
from fanfouapi import oauth, auth, api

from urllib2 import Request, urlopen
from urlparse import urljoin
import getpass

def get_api(oauth_token=settings.PUBLISHER_OAUTH_TOKEN,
            oauth_secret=settings.PUBLISHER_OAUTH_SECRET):
    handler = auth.OAuthHandler(settings.FF_API_KEY, settings.FF_API_SECRET)
    handler.set_access_token(oauth_token, oauth_secret)
    return api.API(handler)
                                            
class Command(BaseCommand):
    help = "Call API"
    def handle(self, action, *args, **options):
        a = get_api()
        if action == 'statuses/update':
            if len(args) > 0:
                print a.update_status(status=args[0])
            else:
                print >>sys.stderr, 'statuses/update <status>'
        elif action == 'statuses/repost':
            if len(args) == 0:
                print >>sys.stderr, 'statuses/repost <statusid> <status>'
            else:
                repost_status_id = args[0]
                repost_status = a.get_status(repost_status_id)
                print repost_status.get_text()
                if len(args) > 1:
                    status = args[1]
                else:
                    status = '\xe8\xbd\xac@' + smart_str(repost_status.user.screen_name + ' ' + repost_status.get_text())
                    #status = prefix + msg.sendFromRealName
                a.update_status(status=status, repost_status_id=repost_status_id)                
        elif action == 'friendships/exists':
            if len(args) >= 2:
                v = a.exists_friendship(user_a=args[0], user_b=args[1])
                print v.value
            else:
                print >>sys.stderr, 'friendships/exists <user_a> <user_b>'
        elif action == 'photos/upload':
            if len(args) > 1:
                print a.upload(args[0], args[1])
            else:
                print >>sys.stderr, 'photos/upload <imgfile> <status>'
        elif action in ('statuses/friends_timeline',
                        'statuses/home_timeline'):
            print a.friends_timeline()
        elif action == 'statuses/public_timeline':
            print a.public_timeline()
        elif action in ('statuses/user_timeline',):
            if len(args) > 0:
                print a.user_timeline(user_id=args[0])
            else:
                print >>sys.stderr, 'statuses/user_timeline <user_id>'
        else:
            print >>sys.stderr, 'Unknown action', action

########NEW FILE########
__FILENAME__ = oauth_pin
from django.core.management.base import BaseCommand
from django.conf import settings
import sys, urllib, re
from fanfouapi import auth
from fanfouapi.auth import OAuthHandler
import getpass

class Command(BaseCommand):
    help = "Make OAuth with pin"
    def handle(self, **options):
        handler = OAuthHandler(settings.FF_API_KEY, settings.FF_API_SECRET)
        url = handler.get_authorization_url(callback='oob')
        request_token = handler.request_token
        print 'Open the url', url, 'to get pin code.'
        verifier = raw_input('PIN Code: ')
        handler = OAuthHandler(settings.FF_API_KEY, settings.FF_API_SECRET)
        handler.request_token = request_token
        access_token = handler.get_access_token(verifier=verifier)
        if access_token:
            print '# Put the following lines into settings.py'
            print "PUBLISHER_OAUTH_TOKEN = '%s'" % access_token.key
            print "PUBLISHER_OAUTH_SECRET = '%s'" % access_token.secret

        
        
        

########NEW FILE########
__FILENAME__ = posturl
from django.core.management.base import BaseCommand
from django.conf import settings
import sys, urllib, re
from fanfouapi import oauth, auth, api

from urllib2 import Request, urlopen
from urlparse import urljoin
import getpass

USER_AGENT = getattr(settings, 'USER_AGENT', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_6_8) AppleWebKit/535.1 (KHTML, like Gecko) Chrome/14.0.835.109 Safari/535.1')

def get_api(oauth_token=settings.PUBLISHER_OAUTH_TOKEN,
            oauth_secret=settings.PUBLISHER_OAUTH_SECRET):
    handler = auth.OAuthHandler(settings.FF_API_KEY, settings.FF_API_SECRET)
    handler.set_access_token(oauth_token, oauth_secret)
    return api.API(handler)

class Command(BaseCommand):
    help = "Update URL"
    def handle(self, url, *args, **kw):
        print 'getting url', url, '...'
        req = Request(url, None, headers={'User-Agent': USER_AGENT})
        resp = urlopen(req, None, 30)
        info = resp.info()
        charset = info.getparam('charset')
        if charset is None:
            charset = 'utf-8'
        charset = charset.lower()
        ttype = info.gettype()
        if ttype in ('text/html', ):
            data = resp.read()
            m = re.search(r'<title>(.*?)</title>', data)
            if m:
                title = unicode(m.group(1), charset).encode('utf-8')
                api = get_api()
                content = '%s %s' % (title, url)
                print content
                #print api.update_status(content)

########NEW FILE########
__FILENAME__ = xauth
from django.core.management.base import BaseCommand
from django.conf import settings
import sys, urllib, re
from fanfouapi import auth
import getpass

class Command(BaseCommand):
    help = "Make XAuth"
    def handle(self, username, **options):
        passwd = getpass.getpass('Password: ')
        m = auth.xauth(username, passwd)
        if m:
            print '# Put the following lines into settings.py'
            print '# User name: %s' % username
            print "PUBLISHER_OAUTH_TOKEN = '%s'" % m['key']
            print "PUBLISHER_OAUTH_SECRET = '%s'" % m['secret']

########NEW FILE########
__FILENAME__ = models
# -*- encoding: utf-8 -*-
import re
import urllib
import urlparse
from django.db import models
from django.conf import settings
from django.contrib.auth.models import User
from fanfouapi import oauth, auth, api
from django.utils.encoding import smart_str, force_unicode
from django.conf import settings

class FFUserManager(models.Manager):
    def get_or_create_from_api(self, api):
        objuser = api.verify_credentials()
        uname = self.model.unquote_name(objuser.id)
        u, c = self.get_or_create(loginname=uname)
        u.objuser = objuser
        u.screen_name = objuser.name
        u.profile_image = objuser.profile_image_url
        try:
            u.created_at = objuser.created_at
        except Exception, e:
            print e
        u.save()
        return u

    def get_from_api(self, api):
        objuser = api.verify_credentials()
        uname = self.model.unquote_name(objuser.id)
        u = self.get(loginname=uname)
        u.objuser = objuser
        u.screen_name = objuser.name
        u.profile_image = objuser.profile_image_url
        u.save()
        return u

    def get_by_user(self, user):
        uname = self.model.unquote_name(user.username)
        return self.get(loginname=force_unicode(uname))

class FFUser(models.Model):
    loginname = models.CharField(max_length=100,  unique=True)
    screen_name = models.CharField(max_length=100,  db_index=True)
    profile_image = models.CharField(max_length=100, db_index=False)

    oauth_token_secret = models.CharField(max_length=60, null=True, blank=True)
    oauth_token = models.CharField(max_length=60, db_index=True, null=True, blank=True)

    login_time = models.DateTimeField(auto_now=True, null=True)
    created_at = models.DateTimeField(auto_now=False, null=True)

    objects = FFUserManager()

    class Meta:
        ordering=['-login_time']
        verbose_name = u'饭否用户'
        verbose_name_plural = verbose_name

    def __unicode__(self):
        return self.loginname

    def get_absolute_url(self):
        return urlparse.urljoin('http://%s' % settings.FF_HOST, self.loginname)

    def get_invite_token(self):
        if self.invite_token:
            return self.invite_token

        while True:
            token_str = ''.join(random.choice(string.letters + string.digits) for i in xrange(10))

            #check if exists in email/sms express
            if FFUser.objects.filter(invite_token=token_str).count():
                continue
            else:
                self.invite_token = token_str
                self.save()
                return token_str
    @classmethod
    def quote_name(cls, username):
        username = force_unicode(username)
        s = ''
        for c in username:
            d = ord(c)
            if c == '~':
                s += '-%02x' % d
            elif d < 128:
                s += c
            else:
                s += '+%04x' % d
        return s

    @classmethod
    def unquote_name(cls, username):
        def to_unicode(m):
            a = int(m.group(1), 16)
            return unichr(a)
        username = re.sub(r'\+([a-zA-Z0-9]{4})', to_unicode, username)
        username = re.sub(r'\-([a-zA-A0-9]{2})', to_unicode, username)
        return username

    def get_or_create_user(self, oauth_token=None, oauth_token_secret=None):
        self.oauth_token = oauth_token
        self.oauth_token_secret = oauth_token_secret
        self.save()
        
        u, c = User.objects.get_or_create(username=self.quote_name(self.loginname))
        if c:
            u.email = '%s@fanfou.cc' % u.username
            u.set_password('1111')
            u.save()
        return u

    def get_api(self):
        handler = auth.OAuthHandler(settings.FF_API_KEY, settings.FF_API_SECRET)
        handler.set_access_token(self.oauth_token, self.oauth_token_secret)
        return api.API(handler)
        

########NEW FILE########
__FILENAME__ = oauth
"""
The MIT License

Copyright (c) 2007 Leah Culver

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.
"""

import cgi
import urllib
import time
import random
import urlparse
import hmac
import binascii
from django.conf import settings

VERSION = '1.0' # Hi Blaine!
HTTP_METHOD = 'GET'
SIGNATURE_METHOD = 'PLAINTEXT'


class OAuthError(RuntimeError):
    """Generic exception class."""
    def __init__(self, message='OAuth error occured.'):
        self.message = message

def build_authenticate_header(realm=''):
    """Optional WWW-Authenticate header (401 error)"""
    return {'WWW-Authenticate': 'OAuth realm="%s"' % realm}

def escape(s):
    """Escape a URL including any /."""
    return urllib.quote(s, safe='~')

def _utf8_str(s):
    """Convert unicode to utf-8."""
    if isinstance(s, unicode):
        return s.encode("utf-8")
    else:
        return str(s)

def generate_timestamp():
    """Get seconds since epoch (UTC)."""
    return int(time.time())

def generate_nonce(length=8):
    """Generate pseudorandom number."""
    return ''.join([str(random.randint(0, 9)) for i in range(length)])

def generate_verifier(length=8):
    """Generate pseudorandom number."""
    return ''.join([str(random.randint(0, 9)) for i in range(length)])


class OAuthConsumer(object):
    """Consumer of OAuth authentication.

    OAuthConsumer is a data type that represents the identity of the Consumer
    via its shared secret with the Service Provider.

    """
    key = None
    secret = None

    def __init__(self, key, secret):
        self.key = key
        self.secret = secret


class OAuthToken(object):
    """OAuthToken is a data type that represents an End User via either an access
    or request token.
    
    key -- the token
    secret -- the token secret

    """
    key = None
    secret = None
    callback = None
    callback_confirmed = None
    verifier = None

    def __init__(self, key, secret):
        self.key = key
        self.secret = secret

    def set_callback(self, callback):
        self.callback = callback
        self.callback_confirmed = 'true'

    def set_verifier(self, verifier=None):
        if verifier is not None:
            self.verifier = verifier
        else:
            self.verifier = generate_verifier()
            
    def get_callback_url(self):
        if self.callback and self.verifier:
            # Append the oauth_verifier.
            parts = urlparse.urlparse(self.callback)
            scheme, netloc, path, params, query, fragment = parts[:6]
            if query:
                query = '%s&oauth_verifier=%s' % (query, self.verifier)
            else:
                query = 'oauth_verifier=%s' % self.verifier
            return urlparse.urlunparse((scheme, netloc, path, params,
                query, fragment))
        return self.callback

    def to_string(self):
        data = {
            'oauth_token': self.key,
            'oauth_token_secret': self.secret,
        }
        if self.callback_confirmed is not None:
            data['oauth_callback_confirmed'] = self.callback_confirmed
        return urllib.urlencode(data)
 
    def from_string(s):
        """ Returns a token from something like:
        oauth_token_secret=xxx&oauth_token=xxx
        """
        params = cgi.parse_qs(s, keep_blank_values=False)
        key = params['oauth_token'][0]
        secret = params['oauth_token_secret'][0]
        token = OAuthToken(key, secret)
        try:
            token.callback_confirmed = params['oauth_callback_confirmed'][0]
        except KeyError:
            pass # 1.0, no callback confirmed.
        return token
    from_string = staticmethod(from_string)

    def __str__(self):
        return self.to_string()


class OAuthRequest(object):
    """OAuthRequest represents the request and can be serialized.

    OAuth parameters:
        - oauth_consumer_key 
        - oauth_token
        - oauth_signature_method
        - oauth_signature 
        - oauth_timestamp 
        - oauth_nonce
        - oauth_version
        - oauth_verifier
        ... any additional parameters, as defined by the Service Provider.
    """
    parameters = None # OAuth parameters.
    http_method = HTTP_METHOD
    http_url = None
    version = VERSION

    def __init__(self, http_method=HTTP_METHOD, http_url=None, parameters=None):
        self.http_method = http_method
        self.http_url = http_url
        self.parameters = parameters or {}
    def set_parameter(self, parameter, value):
        self.parameters[parameter] = value

    def get_parameter(self, parameter):
        try:
            return self.parameters[parameter]
        except:
            raise OAuthError('Parameter not found: %s' % parameter)

    def _get_timestamp_nonce(self):
        return self.get_parameter('oauth_timestamp'), self.get_parameter(
            'oauth_nonce')

    def get_nonoauth_parameters(self):
        """Get any non-OAuth parameters."""
        parameters = {}
        for k, v in self.parameters.iteritems():
            # Ignore oauth parameters.
            if k.find('oauth_') < 0:
                parameters[k] = v
        return parameters

    def to_header(self, realm=''):
        """Serialize as a header for an HTTPAuth request."""
        auth_header = 'OAuth realm="%s"' % realm
        # Add the oauth parameters.
        if self.parameters:
            for k, v in self.parameters.iteritems():
                if k[:6] == 'oauth_':
                    auth_header += ', %s="%s"' % (k, escape(str(v)))
        return {'Authorization': auth_header}

    def to_postdata(self):
        """Serialize as post data for a POST request."""
        return '&'.join(['%s=%s' % (escape(str(k)), escape(str(v))) \
            for k, v in self.parameters.iteritems()])

    def to_url(self):
        """Serialize as a URL for a GET request."""
        return '%s?%s' % (self.get_normalized_http_url(), self.to_postdata())

    def get_normalized_parameters(self):
        """Return a string that contains the parameters that must be signed."""
        params = self.parameters
        try:
            # Exclude the signature if it exists.
            del params['oauth_signature']
        except:
            pass
        # Escape key values before sorting.
        key_values = [(escape(_utf8_str(k)), escape(_utf8_str(v))) \
            for k,v in params.items()]
        # Sort lexicographically, first after key, then after value.
        key_values.sort()
        # Combine key value pairs into a string.
        return '&'.join(['%s=%s' % (k, v) for k, v in key_values])

    def get_normalized_http_method(self):
        """Uppercases the http method."""
        return self.http_method.upper()

    def get_normalized_http_url(self):
        """Parses the URL and rebuilds it to be scheme://host/path."""
        parts = urlparse.urlparse(self.http_url)
        scheme, netloc, path = parts[:3]
        # Exclude default port numbers.
        if scheme == 'http' and netloc[-3:] == ':80':
            netloc = netloc[:-3]
        elif scheme == 'https' and netloc[-4:] == ':443':
            netloc = netloc[:-4]
        return '%s://%s%s' % (scheme, netloc, path)

    def sign_request(self, signature_method, consumer, token):
        """Set the signature parameter to the result of build_signature."""
        # Set the signature method.
        self.set_parameter('oauth_signature_method',
            signature_method.get_name())
        # Set the signature.
        self.set_parameter('oauth_signature',self.build_signature(signature_method, consumer, token))

    def build_signature(self, signature_method, consumer, token):
        """Calls the build signature method within the signature method."""
        return signature_method.build_signature(self, consumer, token)

    def from_request(http_method, http_url, headers=None, parameters=None,
            query_string=None):
        """Combines multiple parameter sources."""
        if parameters is None:
            parameters = {}

        # Headers
        if headers and 'Authorization' in headers:
            auth_header = headers['Authorization']
            # Check that the authorization header is OAuth.
            if auth_header[:6] == 'OAuth ':
                auth_header = auth_header[6:]
                try:
                    # Get the parameters from the header.
                    header_params = OAuthRequest._split_header(auth_header)
                    parameters.update(header_params)
                except:
                    raise OAuthError('Unable to parse OAuth parameters from '
                        'Authorization header.')

        # GET or POST query string.
        if query_string:
            query_params = OAuthRequest._split_url_string(query_string)
            parameters.update(query_params)

        # URL parameters.
        param_str = urlparse.urlparse(http_url)[4] # query
        url_params = OAuthRequest._split_url_string(param_str)
        parameters.update(url_params)

        if parameters:
            return OAuthRequest(http_method, http_url, parameters)

        return None
    from_request = staticmethod(from_request)

    def from_consumer_and_token(oauth_consumer, token=None,
            callback=None, verifier=None, http_method=HTTP_METHOD,
            http_url=None, parameters=None):
        if not parameters:
            parameters = {}

        defaults = {
            'oauth_consumer_key': oauth_consumer.key,
            'oauth_timestamp': generate_timestamp(),
            'oauth_nonce': generate_nonce(),
            'oauth_version': OAuthRequest.version,
        }

        defaults.update(parameters)
        parameters = defaults

        if token:
            parameters['oauth_token'] = token.key
            if token.callback:
                parameters['oauth_callback'] = token.callback
            # 1.0a support for verifier.
            if verifier:
                parameters['oauth_verifier'] = verifier
        elif callback:
            # 1.0a support for callback in the request token request.
            parameters['oauth_callback'] = callback

        return OAuthRequest(http_method, http_url, parameters)
    from_consumer_and_token = staticmethod(from_consumer_and_token)

    def from_token_and_callback(token, callback=None, http_method=HTTP_METHOD,
            http_url=None, parameters=None):
        if not parameters:
            parameters = {}

        parameters['oauth_token'] = token.key

        if callback:
            parameters['oauth_callback'] = callback

        return OAuthRequest(http_method, http_url, parameters)
    from_token_and_callback = staticmethod(from_token_and_callback)

    def _split_header(header):
        """Turn Authorization: header into parameters."""
        params = {}
        parts = header.split(',')
        for param in parts:
            # Ignore realm parameter.
            if param.find('realm') > -1:
                continue
            # Remove whitespace.
            param = param.strip()
            # Split key-value.
            param_parts = param.split('=', 1)
            # Remove quotes and unescape the value.
            params[param_parts[0]] = urllib.unquote(param_parts[1].strip('\"'))
        return params
    _split_header = staticmethod(_split_header)

    def _split_url_string(param_str):
        """Turn URL string into parameters."""
        parameters = cgi.parse_qs(param_str, keep_blank_values=False)
        for k, v in parameters.iteritems():
            parameters[k] = urllib.unquote(v[0])
        return parameters
    _split_url_string = staticmethod(_split_url_string)

class OAuthServer(object):
    """A worker to check the validity of a request against a data store."""
    timestamp_threshold = 300 # In seconds, five minutes.
    version = VERSION
    signature_methods = None
    data_store = None

    def __init__(self, data_store=None, signature_methods=None):
        self.data_store = data_store
        self.signature_methods = signature_methods or {}

    def set_data_store(self, data_store):
        self.data_store = data_store

    def get_data_store(self):
        return self.data_store

    def add_signature_method(self, signature_method):
        self.signature_methods[signature_method.get_name()] = signature_method
        return self.signature_methods

    def fetch_request_token(self, oauth_request):
        """Processes a request_token request and returns the
        request token on success.
        """
        try:
            # Get the request token for authorization.
            token = self._get_token(oauth_request, 'request')
        except OAuthError:
            # No token required for the initial token request.
            version = self._get_version(oauth_request)
            consumer = self._get_consumer(oauth_request)
            try:
                callback = self.get_callback(oauth_request)
            except OAuthError:
                callback = None # 1.0, no callback specified.
            self._check_signature(oauth_request, consumer, None)
            # Fetch a new token.
            token = self.data_store.fetch_request_token(consumer, callback)
        return token

    def fetch_access_token(self, oauth_request):
        """Processes an access_token request and returns the
        access token on success.
        """
        version = self._get_version(oauth_request)
        consumer = self._get_consumer(oauth_request)
        try:
            verifier = self._get_verifier(oauth_request)
        except OAuthError:
            verifier = None
        # Get the request token.
        token = self._get_token(oauth_request, 'request')
        self._check_signature(oauth_request, consumer, token)
        new_token = self.data_store.fetch_access_token(consumer, token, verifier)
        return new_token

    def verify_request(self, oauth_request):
        """Verifies an api call and checks all the parameters."""
        # -> consumer and token
        version = self._get_version(oauth_request)
        consumer = self._get_consumer(oauth_request)
        # Get the access token.
        token = self._get_token(oauth_request, 'access')
        self._check_signature(oauth_request, consumer, token)
        parameters = oauth_request.get_nonoauth_parameters()
        return consumer, token, parameters

    def authorize_token(self, token, user):
        """Authorize a request token."""
        return self.data_store.authorize_request_token(token, user)

    def get_callback(self, oauth_request):
        """Get the callback URL."""
        return oauth_request.get_parameter('oauth_callback')
 
    def build_authenticate_header(self, realm=''):
        """Optional support for the authenticate header."""
        return {'WWW-Authenticate': 'OAuth realm="%s"' % realm}

    def _get_version(self, oauth_request):
        """Verify the correct version request for this server."""
        try:
            version = oauth_request.get_parameter('oauth_version')
        except:
            version = VERSION
        if version and version != self.version:
            raise OAuthError('OAuth version %s not supported.' % str(version))
        return version

    def _get_signature_method(self, oauth_request):
        """Figure out the signature with some defaults."""
        try:
            signature_method = oauth_request.get_parameter(
                'oauth_signature_method')
        except:
            signature_method = SIGNATURE_METHOD
        try:
            # Get the signature method object.
            signature_method = self.signature_methods[signature_method]
        except:
            signature_method_names = ', '.join(self.signature_methods.keys())
            raise OAuthError('Signature method %s not supported try one of the '
                'following: %s' % (signature_method, signature_method_names))

        return signature_method

    def _get_consumer(self, oauth_request):
        consumer_key = oauth_request.get_parameter('oauth_consumer_key')
        consumer = self.data_store.lookup_consumer(consumer_key)
        if not consumer:
            raise OAuthError('Invalid consumer.')
        return consumer

    def _get_token(self, oauth_request, token_type='access'):
        """Try to find the token for the provided request token key."""
        token_field = oauth_request.get_parameter('oauth_token')
        token = self.data_store.lookup_token(token_type, token_field)
        if not token:
            raise OAuthError('Invalid %s token: %s' % (token_type, token_field))
        return token
    
    def _get_verifier(self, oauth_request):
        return oauth_request.get_parameter('oauth_verifier')

    def _check_signature(self, oauth_request, consumer, token):
        timestamp, nonce = oauth_request._get_timestamp_nonce()
        self._check_timestamp(timestamp)
        self._check_nonce(consumer, token, nonce)
        signature_method = self._get_signature_method(oauth_request)
        try:
            signature = oauth_request.get_parameter('oauth_signature')
        except:
            raise OAuthError('Missing signature.')
        # Validate the signature.
        valid_sig = signature_method.check_signature(oauth_request, consumer,
            token, signature)
        if not valid_sig:
            key, base = signature_method.build_signature_base_string(
                oauth_request, consumer, token)
            raise OAuthError('Invalid signature. Expected signature base '
                'string: %s' % base)
        built = signature_method.build_signature(oauth_request, consumer, token)

    def _check_timestamp(self, timestamp):
        """Verify that timestamp is recentish."""
        timestamp = int(timestamp)
        now = int(time.time())
        lapsed = abs(now - timestamp)
        if lapsed > self.timestamp_threshold:
            raise OAuthError('Expired timestamp: given %d and now %s has a '
                'greater difference than threshold %d' %
                (timestamp, now, self.timestamp_threshold))

    def _check_nonce(self, consumer, token, nonce):
        """Verify that the nonce is uniqueish."""
        nonce = self.data_store.lookup_nonce(consumer, token, nonce)
        if nonce:
            raise OAuthError('Nonce already used: %s' % str(nonce))


class OAuthClient(object):
    """OAuthClient is a worker to attempt to execute a request."""
    consumer = None
    token = None

    def __init__(self, oauth_consumer, oauth_token):
        self.consumer = oauth_consumer
        self.token = oauth_token

    def get_consumer(self):
        return self.consumer

    def get_token(self):
        return self.token

    def fetch_request_token(self, oauth_request):
        """-> OAuthToken."""
        raise NotImplementedError

    def fetch_access_token(self, oauth_request):
        """-> OAuthToken."""
        raise NotImplementedError

    def access_resource(self, oauth_request):
        """-> Some protected resource."""
        raise NotImplementedError


class OAuthDataStore(object):
    """A database abstraction used to lookup consumers and tokens."""

    def lookup_consumer(self, key):
        """-> OAuthConsumer."""
        raise NotImplementedError

    def lookup_token(self, oauth_consumer, token_type, token_token):
        """-> OAuthToken."""
        raise NotImplementedError

    def lookup_nonce(self, oauth_consumer, oauth_token, nonce):
        """-> OAuthToken."""
        raise NotImplementedError

    def fetch_request_token(self, oauth_consumer, oauth_callback):
        """-> OAuthToken."""
        raise NotImplementedError

    def fetch_access_token(self, oauth_consumer, oauth_token, oauth_verifier):
        """-> OAuthToken."""
        raise NotImplementedError

    def authorize_request_token(self, oauth_token, user):
        """-> OAuthToken."""
        raise NotImplementedError


class OAuthSignatureMethod(object):
    """A strategy class that implements a signature method."""
    def get_name(self):
        """-> str."""
        raise NotImplementedError

    def build_signature_base_string(self, oauth_request, oauth_consumer, oauth_token):
        """-> str key, str raw."""
        raise NotImplementedError

    def build_signature(self, oauth_request, oauth_consumer, oauth_token):
        """-> str."""
        raise NotImplementedError

    def check_signature(self, oauth_request, consumer, token, signature):
        built = self.build_signature(oauth_request, consumer, token)
        return built == signature


class OAuthSignatureMethod_HMAC_SHA1(OAuthSignatureMethod):

    def get_name(self):
        return 'HMAC-SHA1'
        
    def build_signature_base_string(self, oauth_request, consumer, token):
        sig = (
            escape(oauth_request.get_normalized_http_method()),
            escape(oauth_request.get_normalized_http_url()),
            escape(oauth_request.get_normalized_parameters()),
        )

        key = '%s&' % escape(consumer.secret)
        if token:
            key += escape(token.secret)
        #print "OAuth base string:" + str(sig)
        raw = '&'.join(sig)
        return key, raw

    def build_signature(self, oauth_request, consumer, token):
        """Builds the base signature string."""
        key, raw = self.build_signature_base_string(oauth_request, consumer,
            token)
        if settings.DEBUG:
            print '[DEBUG]', 'Base string: ', raw
        # HMAC object.
        try:
            import hashlib # 2.5
            hashed = hmac.new(key, raw, hashlib.sha1)
        except:
            import sha # Deprecated
            hashed = hmac.new(key, raw, sha)

        # Calculate the digest base 64.
        return binascii.b2a_base64(hashed.digest())[:-1]


class OAuthSignatureMethod_PLAINTEXT(OAuthSignatureMethod):

    def get_name(self):
        return 'PLAINTEXT'

    def build_signature_base_string(self, oauth_request, consumer, token):
        """Concatenates the consumer key and secret."""
        sig = '%s&' % escape(consumer.secret)
        if token:
            sig = sig + escape(token.secret)
        return sig, sig

    def build_signature(self, oauth_request, consumer, token):
        key, raw = self.build_signature_base_string(oauth_request, consumer,
            token)
        return key

########NEW FILE########
__FILENAME__ = objs

# Copyright 2009-2010 Joshua Roesslein
# See LICENSE for details.

from fanfouapi.utils import parse_datetime, parse_html_value, parse_a_href, \
        parse_search_datetime, unescape_html

class ResultSet(list):
    """A list like object that holds results from a Twitter API query."""


class Model(object):

    def __init__(self, api=None):
        self._api = api

    def __getstate__(self):
        # pickle
        pickle = dict(self.__dict__)
        del pickle['_api']  # do not pickle the API reference
        return pickle

    @classmethod
    def parse(cls, api, json):
        """Parse a JSON object into a model instance."""
        raise NotImplementedError

    @classmethod
    def parse_list(cls, api, json_list):
        """Parse a list of JSON objects into a result set of model instances."""
        results = ResultSet()
        for obj in json_list:
            results.append(cls.parse(api, obj))
        return results


class Status(Model):

    @classmethod
    def parse(cls, api, json):
        status = cls(api)
        for k, v in json.items():
            if k == 'user':
                user = User.parse(api, v)
                setattr(status, 'author', user)
                setattr(status, 'user', user)  # DEPRECIATED
            elif k == 'screen_name':
                setattr(status, k, v)
            elif k == 'created_at':
                setattr(status, k, parse_datetime(v))
            elif k == 'source':
                if '<' in v:
                    setattr(status, k, parse_html_value(v))
                    setattr(status, 'source_url', parse_a_href(v))
                else:
                    setattr(status, k, v)
            elif k == 'repost_status':
                setattr(status, k, Status.parse(api, v))
            elif k == 'geo':
                setattr(status, k, Geo.parse(api, v))
            else:
                setattr(status, k, v)
        return status

    def get_text(self):
        return self.text
        #text = self.text
        #if hasattr(self, 'photo') and 'url' in self.photo:
        #    text += ' ' + self.photo['url']
        #return text
            
    def destroy(self):
        return self._api.destroy_status(self.id)

    def retweet(self):
        return self._api.retweet(self.id)

    def retweets(self):
        return self._api.retweets(self.id)

    def favorite(self):
        return self._api.create_favorite(self.id)
class Geo(Model):

    @classmethod
    def parse(cls, api, json):
        geo = cls(api)
        if json is not None:
            for k, v in json.items():
                setattr(geo, k, v)
        return geo
    
class Comments(Model):

    @classmethod
    def parse(cls, api, json):
        comments = cls(api)
        for k, v in json.items():
            if k == 'user':
                user = User.parse(api, v)
                setattr(comments, 'author', user)
                setattr(comments, 'user', user)
            elif k == 'status':
                status = Status.parse(api, v)
                setattr(comments, 'user', status)
            elif k == 'created_at':
                setattr(comments, k, parse_datetime(v))
            elif k == 'reply_comment':
                setattr(comments, k, User.parse(api, v))
            else:
                setattr(comments, k, v)
        return comments

    def destroy(self):
        return self._api.destroy_status(self.id)

    def retweet(self):
        return self._api.retweet(self.id)

    def retweets(self):
        return self._api.retweets(self.id)

    def favorite(self):
        return self._api.create_favorite(self.id)

class User(Model):

    @classmethod
    def parse(cls, api, json):
        user = cls(api)
        for k, v in json.items():
            if k == 'created_at':
                setattr(user, k, parse_datetime(v))
            elif k == 'status':
                setattr(user, k, Status.parse(api, v))
            elif k == 'screen_name':
                setattr(user, k, v)
            elif k == 'following':
                # twitter sets this to null if it is false
                if v is True:
                    setattr(user, k, True)
                else:
                    setattr(user, k, False)
            else:
                setattr(user, k, v)
        return user

    @classmethod
    def parse_list(cls, api, json_list):
        if isinstance(json_list, list):
            item_list = json_list
        else:
            item_list = json_list['users']

        results = ResultSet()
        for obj in item_list:
            results.append(cls.parse(api, obj))
        return results

    def timeline(self, **kargs):
        return self._api.user_timeline(user_id=self.id, **kargs)

    def friends(self, **kargs):
        return self._api.friends(user_id=self.id, **kargs)

    def followers(self, **kargs):
        return self._api.followers(user_id=self.id, **kargs)

    def follow(self):
        self._api.create_friendship(user_id=self.id)
        self.following = True

    def unfollow(self):
        self._api.destroy_friendship(user_id=self.id)
        self.following = False

    def lists_memberships(self, *args, **kargs):
        return self._api.lists_memberships(user=self.screen_name, *args, **kargs)

    def lists_subscriptions(self, *args, **kargs):
        return self._api.lists_subscriptions(user=self.screen_name, *args, **kargs)

    def lists(self, *args, **kargs):
        return self._api.lists(user=self.screen_name, *args, **kargs)

    def followers_ids(self, *args, **kargs):
        return self._api.followers_ids(user_id=self.id, *args, **kargs)




class DirectMessage(Model):
    @classmethod
    def parse(cls, api, json):
        dm = cls(api)
        for k, v in json.items():
            if k == 'sender' or k == 'recipient':
                setattr(dm, k, User.parse(api, v))
            elif k == 'created_at':
                setattr(dm, k, parse_datetime(v))
            else:
                setattr(dm, k, v)
        return dm

class Friendship(Model):

    @classmethod
    def parse(cls, api, json):
       
        source = cls(api)
        for k, v in json['source'].items():
            setattr(source, k, v)

        # parse target
        target = cls(api)
        for k, v in json['target'].items():
            setattr(target, k, v)

        return source, target


class SavedSearch(Model):

    @classmethod
    def parse(cls, api, json):
        ss = cls(api)
        for k, v in json.items():
            if k == 'created_at':
                setattr(ss, k, parse_datetime(v))
            else:
                setattr(ss, k, v)
        return ss

    def destroy(self):
        return self._api.destroy_saved_search(self.id)


class SearchResult(Model):

    @classmethod
    def parse(cls, api, json):
        result = cls()
        for k, v in json.items():
            if k == 'created_at':
                setattr(result, k, parse_search_datetime(v))
            elif k == 'source':
                setattr(result, k, parse_html_value(unescape_html(v)))
            else:
                setattr(result, k, v)
        return result

    @classmethod
    def parse_list(cls, api, json_list, result_set=None):
        results = ResultSet()
        results.max_id = json_list.get('max_id')
        results.since_id = json_list.get('since_id')
        results.refresh_url = json_list.get('refresh_url')
        results.next_page = json_list.get('next_page')
        results.results_per_page = json_list.get('results_per_page')
        results.page = json_list.get('page')
        results.completed_in = json_list.get('completed_in')
        results.query = json_list.get('query')

        for obj in json_list['results']:
            results.append(cls.parse(api, obj))
        return results

class List(Model):

    @classmethod
    def parse(cls, api, json):
        lst = List(api)
        for k,v in json.items():
            if k == 'user':
                setattr(lst, k, User.parse(api, v))
            else:
                setattr(lst, k, v)
        return lst

    @classmethod
    def parse_list(cls, api, json_list, result_set=None):
        results = ResultSet()
        for obj in json_list['lists']:
            results.append(cls.parse(api, obj))
        return results

    def update(self, **kargs):
        return self._api.update_list(self.slug, **kargs)

    def destroy(self):
        return self._api.destroy_list(self.slug)

    def timeline(self, **kargs):
        return self._api.list_timeline(self.user.screen_name, self.slug, **kargs)

    def add_member(self, id):
        return self._api.add_list_member(self.slug, id)

    def remove_member(self, id):
        return self._api.remove_list_member(self.slug, id)

    def members(self, **kargs):
        return self._api.list_members(self.user.screen_name, self.slug, **kargs)

    def is_member(self, id):
        return self._api.is_list_member(self.user.screen_name, self.slug, id)

    def subscribe(self):
        return self._api.subscribe_list(self.user.screen_name, self.slug)

    def unsubscribe(self):
        return self._api.unsubscribe_list(self.user.screen_name, self.slug)

    def subscribers(self, **kargs):
        return self._api.list_subscribers(self.user.screen_name, self.slug, **kargs)

    def is_subscribed(self, id):
        return self._api.is_subscribed_list(self.user.screen_name, self.slug, id)

class JSONModel(Model):

    @classmethod
    def parse(cls, api, json):
        lst = JSONModel(api)
        if isinstance(json, dict):
            for k,v in json.iteritems():
                setattr(lst, k, v)
        else:
            lst.value = json
        return lst

class IDSModel(Model):
    @classmethod
    def parse(cls, api, json):
        ids = IDSModel(api)
        for k, v in json.items():            
            setattr(ids, k, v)
        return ids
    
class Counts(Model):
    @classmethod
    def parse(cls, api, json):
        ids = Counts(api)
        for k, v in json.items():            
            setattr(ids, k, v)
        return ids
    
class ModelFactory(object):
    """
    Used by parsers for creating instances
    of models. You may subclass this factory
    to add your own extended models.
    """

    status = Status
    comments = Comments
    user = User
    direct_message = DirectMessage
    friendship = Friendship
    saved_search = SavedSearch
    search_result = SearchResult
    list = List
    json = JSONModel
    ids_list = IDSModel
    counts = Counts

########NEW FILE########
__FILENAME__ = parsers

# Copyright 2009-2010 Joshua Roesslein
# See LICENSE for details.

from fanfouapi.objs import ModelFactory
from fanfouapi.utils import import_simplejson
from fanfouapi.error import WeibopError

class Parser(object):

    def parse(self, method, payload):
        """
        Parse the response payload and return the result.
        Returns a tuple that contains the result data and the cursors
        (or None if not present).
        """
        raise NotImplementedError

    def parse_error(self, method, payload):
        """
        Parse the error message from payload.
        If unable to parse the message, throw an exception
        and default error message will be used.
        """
        raise NotImplementedError


class JSONParser(Parser):

    payload_format = 'json'

    def __init__(self):
        self.json_lib = import_simplejson()

    def parse(self, method, payload):
        try:
            json = self.json_lib.loads(payload)
        except Exception, e:
            print "Failed to parse JSON payload:"+ str(payload)
            raise WeibopError('Failed to parse JSON payload: %s' % e)

        #if isinstance(json, dict) and 'previous_cursor' in json and 'next_cursor' in json:
        #    cursors = json['previous_cursor'], json['next_cursor']
        #    return json, cursors
        #else:
        return json

    def parse_error(self, method, payload):
        return self.json_lib.loads(payload)


class ModelParser(JSONParser):

    def __init__(self, model_factory=None):
        JSONParser.__init__(self)
        self.model_factory = model_factory or ModelFactory

    def parse(self, method, payload):
        try:
            if method.payload_type is None: return
            model = getattr(self.model_factory, method.payload_type)
        except AttributeError:
            raise WeibopError('No model for this payload type: %s' % method.payload_type)

        json = JSONParser.parse(self, method, payload)
        if isinstance(json, tuple):
            json, cursors = json
        else:
            cursors = None

        if method.payload_list:
            result = model.parse_list(method.api, json)
        else:
            result = model.parse(method.api, json)
        if cursors:
            return result, cursors
        else:
            return result


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
from django.conf.urls.defaults import patterns, include, url
from fanfouapi.views import api_auth, api_authcb

urlpatterns = patterns('',
                       url(r'^$', api_auth, name='fanfou_oauth'),
                       url(r'^cb$', api_authcb, name='fanfou_oauth_callback'),
)

########NEW FILE########
__FILENAME__ = utils

# Copyright 2010 Joshua Roesslein
# See LICENSE for details.

from datetime import datetime
import time
import htmlentitydefs
import re


def parse_datetime(str):

    # We must parse datetime this way to work in python 2.4
    return datetime(*(time.strptime(str, '%a %b %d %H:%M:%S +0000 %Y')[0:6]))


def parse_html_value(html):

    return html[html.find('>')+1:html.rfind('<')]


def parse_a_href(atag):

    start = atag.find('"') + 1
    end = atag.find('"', start)
    return atag[start:end]


def parse_search_datetime(str):

    # python 2.4
    return datetime(*(time.strptime(str, '%a, %d %b %Y %H:%M:%S +0000')[0:6]))


def unescape_html(text):
    """Created by Fredrik Lundh (http://effbot.org/zone/re-sub.htm#unescape-html)"""
    def fixup(m):
        text = m.group(0)
        if text[:2] == "&#":
            # character reference
            try:
                if text[:3] == "&#x":
                    return unichr(int(text[3:-1], 16))
                else:
                    return unichr(int(text[2:-1]))
            except ValueError:
                pass
        else:
            # named entity
            try:
                text = unichr(htmlentitydefs.name2codepoint[text[1:-1]])
            except KeyError:
                pass
        return text # leave as is
    return re.sub("&#?\w+;", fixup, text)


def convert_to_utf8_str(arg):
    # written by Michael Norton (http://docondev.blogspot.com/)
    if isinstance(arg, unicode):
        arg = arg.encode('utf-8')
    elif not isinstance(arg, str):
        arg = str(arg)
    return arg



def import_simplejson():
    try:
        import simplejson as json
    except ImportError:
        try:
            import json  # Python 2.6+
        except ImportError:
            try:
                from django.utils import simplejson as json  # Google App Engine
            except ImportError:
                raise ImportError, "Can't load a json library"

    return json


########NEW FILE########
__FILENAME__ = views
import urllib
from django.core.urlresolvers import reverse
from django.conf import settings
from django.http import HttpResponseRedirect, HttpResponse
from fanfouapi.auth import OAuthHandler
from fanfouapi.api import API
from fanfouapi.models import FFUser

from django.contrib.auth.models import User
from django.contrib.auth import login, authenticate
from django.contrib.auth import logout

def api_auth(request):
    handler = OAuthHandler(settings.FF_API_KEY, settings.FF_API_SECRET)
    callback_url = request.GET.get('oauth_callback')
    if not callback_url:
        callback_url = request.build_absolute_uri(reverse('fanfou_oauth_callback'))
    url = handler.get_authorization_url(callback=callback_url)
    request.session['reqtoken'] = handler.request_token
    print handler.request_token
    return HttpResponseRedirect(url)

def get_user(api, **token_dict):
    ffuser = FFUser.objects.get_or_create_from_api(api)
    user = ffuser.get_or_create_user(**token_dict)
    return user

def api_authcb(request):
    try:
        handler = OAuthHandler(settings.FF_API_KEY, settings.FF_API_SECRET)
        request_token = request.session.get('reqtoken', '')
        print 'request token', request_token
        handler.request_token = request_token
        token = handler.get_access_token(verifier=request.GET.get('verifier'))
        api = API(handler)
        u = get_user(api, oauth_token=token.key, oauth_token_secret=token.secret)
        u = authenticate(username=u.username, password='1111')
        login(request, u)
        request.user = u
    except Exception, e:
        print 'got error ', e
        import traceback
        traceback.print_exc()
        logout(request)
    #return HttpResponse('%s' % req_token)
    return HttpResponseRedirect(reverse('route'))

########NEW FILE########
