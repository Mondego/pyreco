__FILENAME__ = basics
#!/usr/bin/env python
from pyfb import Pyfb

#Your APP ID. It Needs to register your application on facebook
#http://developers.facebook.com/
FACEBOOK_APP_ID = '178358228892649'

facebook = Pyfb(FACEBOOK_APP_ID)

#Opens a new browser tab instance and authenticates with the facebook API
#It redirects to an url like http://www.facebook.com/connect/login_success.html#access_token=[access_token]&expires_in=0
facebook.authenticate()

#Copy the [access_token] and enter it below
token = raw_input("Enter the access_token\n")

#Sets the authentication token
facebook.set_access_token(token)

#Gets info about myself
me = facebook.get_myself()

print "-" * 40
print "Name: %s" % me.name
print "From: %s" % me.hometown.name
print

print "Speaks:"
for language in me.languages:
    print "- %s" % language.name

print
print "Worked at:"
for work in me.work:
    print "- %s" % work.employer.name

print "-" * 40
########NEW FILE########
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
__FILENAME__ = views
from pyfb import Pyfb
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render_to_response

from settings import FACEBOOK_APP_ID, FACEBOOK_SECRET_KEY, FACEBOOK_REDIRECT_URL

def index(request):
    return render_to_response("index.html", {"FACEBOOK_APP_ID": FACEBOOK_APP_ID})


#This view redirects the user to facebook in order to get the code that allows
#pyfb to obtain the access_token in the facebook_login_success view
def facebook_login(request):

    facebook = Pyfb(FACEBOOK_APP_ID)
    return HttpResponseRedirect(facebook.get_auth_code_url(redirect_uri=FACEBOOK_REDIRECT_URL))


#This view must be refered in your FACEBOOK_REDIRECT_URL. For example: http://www.mywebsite.com/facebook_login_success/
def facebook_login_success(request):

    code = request.GET.get('code')

    facebook = Pyfb(FACEBOOK_APP_ID)
    facebook.get_access_token(FACEBOOK_SECRET_KEY, code, redirect_uri=FACEBOOK_REDIRECT_URL)

    return _render_user(facebook)



#Login with the js sdk and backend queries with pyfb
def facebook_javascript_login_sucess(request):

    access_token = request.GET.get("access_token")

    facebook = Pyfb(FACEBOOK_APP_ID)
    facebook.set_access_token(access_token)

    return _render_user(facebook)


def _render_user(facebook):

    me = facebook.get_myself()

    welcome = "Welcome <b>%s</b>. Your Facebook login has been completed successfully!"
    return HttpResponse(welcome % me.name)



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
# Django settings for djangoapp project.
import os

DEBUG = True
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    # ('Your Name', 'your_email@example.com'),
)

MANAGERS = ADMINS

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.', # Add 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'oracle'.
        'NAME': '',                      # Or path to database file if using sqlite3.
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
TIME_ZONE = 'America/Chicago'

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
SECRET_KEY = 't8&e3(qophw+evikk5k#!*y3s6(-n=j!#xyth-71ouitv_73p%'

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

ROOT_URLCONF = 'djangoapp.urls'

# Facebook related Settings
FACEBOOK_APP_ID = '178358228892649'
FACEBOOK_SECRET_KEY = 'cc2fbfac64784491fd84fc275b700496'
FACEBOOK_REDIRECT_URL = 'http://localhost:8000/facebook_login_success'


TEMPLATE_DIRS = (
    # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
    os.path.join(os.getcwd(), "templates")
)

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # Uncomment the next line to enable the admin:
    # 'django.contrib.admin',
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

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import patterns, include, url

# Uncomment the next two lines to enable the admin:
# from django.contrib import admin
# admin.autodiscover()

urlpatterns = patterns('',
    # Examples:
    # url(r'^$', 'djangoapp.views.home', name='home'),
    # url(r'^djangoapp/', include('djangoapp.foo.urls')),

    # Uncomment the admin/doc line below to enable admin documentation:
    # url(r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    # url(r'^admin/', include(admin.site.urls)),

    (r'^$', 'djangoapp.django_pyfb.views.index'),
    (r'^facebook_login/$', 'djangoapp.django_pyfb.views.facebook_login'),
    (r'^facebook_login_success/$', 'djangoapp.django_pyfb.views.facebook_login_success'),
    (r'^facebook_javascript_login_sucess/$', 'djangoapp.django_pyfb.views.facebook_javascript_login_sucess'),
)

########NEW FILE########
__FILENAME__ = paginated_lists
from pyfb import Pyfb

#Your APP ID. You Need to register the application on facebook
#http://developers.facebook.com/
FACEBOOK_APP_ID = 'YOUR_APP_ID'

pyfb = Pyfb(FACEBOOK_APP_ID)

#Opens a new browser tab instance and authenticates with the facebook API
#It redirects to an url like http://www.facebook.com/connect/login_success.html#access_token=[access_token]&expires_in=0
pyfb.authenticate()

#Copy the [access_token] and enter it below
token = raw_input("Enter the access_token\n")

#Sets the authentication token
pyfb.set_access_token(token)

photos = pyfb.get_photos()

print "These are my photos:\n"
for photo in photos:
    print photo.picture

#Just call the method next to get the next page of photos!
more_photos = photos.next()

print "\nMore photos:\n"
for photo in more_photos:
    print photo.picture

more_more_photos = more_photos.next()

print "\nDo you want more?:\n"
for photo in more_more_photos:
    print photo.picture
########NEW FILE########
__FILENAME__ = auth
"""
    $Id: auth.py

    This file is a mapper for the specified permissions in
    http://developers.facebook.com/docs/reference/api/permissions/
"""

#User related permissions

USER_ABOUT_ME = "user_about_me"
USER_ACTIVITIES = "user_activities"
USER_BIRTHDAY = "user_birthday"
USER_CHECKINS = "user_checkins"
USER_EDUCATION_HISTORY = "user_education_history"
USER_EVENTS = "user_events"
USER_GROUPS = "user_groups"
USER_HOMETOWN = "user_hometown"
USER_INTERESTS = "user_interests"
USER_LIKES = "user_likes"
USER_LOCATION = "user_location"
USER_NOTES = "user_notes"
USER_ONLINE_PRESENCE = "user_online_presence"
USER_PHOTO_VIDEO_TAGS = "user_photo_video_tags"
USER_PHOTOS = "user_photos"
USER_RELATIONSHIPS = "user_relationships"
USER_RELATIONSHIP_DETAILS = "user_relationship_details"
USER_RELIGION_POLITICS = "user_religion_politics"
USER_STATUS = "user_status"
USER_VIDEOS = "user_videos"
USER_WEBSITE = "user_website"
USER_WORK_HISTORY = "user_work_history"
USER_EMAIL = "email"
USER_READ_FRIENDLISTS = "read_friendlists"
USER_READ_INSIGHTS = "read_insights"
USER_READ_MAILBOX = "read_mailbox"
USER_READ_REQUESTS = "read_requests"
USER_READ_STREAM = "read_stream"
USER_XMPP_LOGIN = "xmpp_login"
USER_ADS_MANAGEMENT = "ads_management"

vars = locals().copy()
USER_ALL_PERMISSIONS = [value for key, value in vars.iteritems() if key.startswith("USER_")]

#Friends related permissions

FRIENDS_ABOUT_ME = "friends_about_me"
FRIENDS_ACTIVITIES = "friends_activities"
FRIENDS_BIRTHDAY = "friends_birthday"
FRIENDS_CHECKINS = "friends_checkins"
FRIENDS_EDUCATION_HISTORY = "friends_education_history"
FRIENDS_EVENTS = "friends_events"
FRIENDS_GROUPS = "friends_groups"
FRIENDS_HOMETOWN = "friends_hometown"
FRIENDS_INTERESTS = "friends_interests"
FRIENDS_LIKES = "friends_likes"
FRIENDS_LOCATION = "friends_location"
FRIENDS_NOTES = "friends_notes"
FRIENDS_ONLINE_PRESENCE = "friends_online_presence"
FRIENDS_PHOTO_VIDEO_TAGS = "friends_photo_video_tags"
FRIENDS_PHOTOS = "friends_photos"
FRIENDS_RELATIONSHIPS = "friends_relationships"
FRIENDS_RELATIONSHIP_DETAILS = "friends_relationship_details"
FRIENDS_RELIGION_POLITICS = "friends_religion_politics"
FRIENDS_STATUS = "friends_status"
FRIENDS_VIDEOS = "friends_videos"
FRIENDS_WEBSITE = "friends_website"
FRIENDS_WORK_HISTORY = "friends_work_history"

vars = locals().copy()
FRIENDS_ALL_PERMISSIONS = [value for key, value in vars.iteritems() if key.startswith("FRIENDS_")]

#Write related permissions

WRITE_PUBLISH_STREAM = "publish_stream"
WRITE_CREATE_EVENT = "create_event"
WRITE_RSVP_EVENT = "rsvp_event"
WRITE_SMS = "sms"
WRITE_OFFLINE_ACCESS = "offline_access"
WRITE_PUBLISH_CHECKINS = "publish_checkins"
WRITE_MANAGE_FRIENDLISTS = "manage_friendlists"

vars = locals().copy()
WRITE_ALL_PERMISSIONS = [value for key, value in vars.iteritems() if key.startswith("WRITE_")]

#Page related permissions

PAGE_MANAGE_PAGES = "manage_pages"

vars = locals().copy()
PAGE_ALL_PERMISSIONS = [value for key, value in vars.iteritems() if key.startswith("PAGE_")]

#All permisssions
ALL_PERMISSIONS = USER_ALL_PERMISSIONS + FRIENDS_ALL_PERMISSIONS + WRITE_ALL_PERMISSIONS + PAGE_ALL_PERMISSIONS


########NEW FILE########
__FILENAME__ = client
"""
    The implementation of the Facebook Client
"""

import urllib
import auth
from urlparse import parse_qsl
from utils import Json2ObjectsFactory

class FacebookClient(object):
    """
        This class implements the interface to the Facebook Graph API
    """

    FACEBOOK_URL = "https://www.facebook.com/"
    GRAPH_URL = "https://graph.facebook.com/"
    API_URL = "https://api.facebook.com/"

    BASE_AUTH_URL = "%sdialog/oauth?" % FACEBOOK_URL 
    DIALOG_BASE_URL = "%sdialog/feed?" % FACEBOOK_URL
    FBQL_BASE_URL = "%sfql?" % GRAPH_URL
    BASE_TOKEN_URL = "%soauth/access_token?" % GRAPH_URL

    DEFAULT_REDIRECT_URI = "http://www.facebook.com/connect/login_success.html"
    DEFAULT_SCOPE = [auth.USER_ABOUT_ME]
    DEFAULT_DIALOG_URI = "http://www.example.com/response/"

     #A factory to make objects from a json
    factory = Json2ObjectsFactory()

    def __init__(self, app_id, access_token=None, raw_data=False, permissions=None):

        self.app_id = app_id
        self.access_token = access_token
        self.raw_data = raw_data

        if permissions is None:
            self.permissions = self.DEFAULT_SCOPE
        else:
            self.permissions = permissions

        self.expires = None

    def _make_request(self, url, data=None):
        """
            Makes a simple request. If not data is a GET else is a POST.
        """
        if not data:
            data = None
        return urllib.urlopen(url, data).read()

    def _make_auth_request(self, path, **data):
        """
            Makes a request to the facebook Graph API.
            This method requires authentication!
            Don't forget to get the access token before use it.
        """
        if self.access_token is None:
            raise PyfbException("Must Be authenticated. Did you forget to get the access token?")

        token_url = "?access_token=%s" % self.access_token
        url = "%s%s%s" % (self.GRAPH_URL, path, token_url)
        if data:
            post_data = urllib.urlencode(data)
        else:
            post_data = None
        return self._make_request(url, post_data)

    def _make_object(self, name, data):
        """
            Uses the factory to make an object from a json
        """
        if not self.raw_data:
            return self.factory.make_object(name, data)
        return self.factory.loads(data)

    def _get_url_path(self, dic):

        return urllib.urlencode(dic)

    def _get_auth_url(self, params, redirect_uri):
        """
            Returns the authentication url
        """
        if redirect_uri is None:
            redirect_uri = self.DEFAULT_REDIRECT_URI
        params['redirect_uri'] = redirect_uri

        url_path = self._get_url_path(params)
        url = "%s%s" % (self.BASE_AUTH_URL, url_path)
        return url

    def _get_permissions(self):

        return ",".join(self.permissions)

    def get_auth_token_url(self, redirect_uri):
        """
            Returns the authentication token url
        """
        params = {
            "client_id": self.app_id,
            "type": "user_agent",
            "scope": self._get_permissions(),
        }
        return self._get_auth_url(params, redirect_uri)

    def get_auth_code_url(self, redirect_uri, state=None):
        """
            Returns the url to get a authentication code
        """
        params = {
            "client_id": self.app_id,
            "scope": self._get_permissions(),
        }

        if state:
            params['state'] = state

        return self._get_auth_url(params, redirect_uri)

    def get_access_token(self, app_secret_key, secret_code, redirect_uri):

        if redirect_uri is None:
            redirect_uri = self.DEFAULT_REDIRECT_URI

        self.secret_key = app_secret_key

        url_path = self._get_url_path({
            "client_id": self.app_id,
            "client_secret" : app_secret_key,
            "redirect_uri" : redirect_uri,
            "code" : secret_code,
        })
        url = "%s%s" % (self.BASE_TOKEN_URL, url_path)

        data = self._make_request(url)

        if not "access_token" in data:
            ex = self.factory.make_object('Error', data)
            raise PyfbException(ex.error.message)

        data = dict(parse_qsl(data))
        self.access_token = data.get('access_token')
        self.expires = data.get('expires')
        return self.access_token

    def exchange_token(self, app_secret_key, exchange_token):

        self.secret_key = app_secret_key

        url_path = self._get_url_path({
            "grant_type": 'fb_exchange_token',
            "client_id": self.app_id,
            "client_secret" : app_secret_key,
            "fb_exchange_token" : exchange_token,
            })
        url = "%s%s" % (self.BASE_TOKEN_URL, url_path)

        data = self._make_request(url)

        if not "access_token" in data:
            ex = self.factory.make_object('Error', data)
            raise PyfbException(ex.error.message)

        data = dict(parse_qsl(data))
        self.access_token = data.get('access_token')
        self.expires = data.get('expires')
        return self.access_token, self.expires

    def get_dialog_url(self, redirect_uri):

        if redirect_uri is None:
            redirect_uri = self.DEFAULT_DIALOG_URI

        url_path = self._get_url_path({
            "app_id" : self.app_id,
            "redirect_uri": redirect_uri,
        })
        url = "%s%s" % (self.DIALOG_BASE_URL, url_path)
        return url

    def get_one(self, path, object_name):
        """
            Gets one object
        """
        data = self._make_auth_request(path)
        obj = self._make_object(object_name, data)

        if hasattr(obj, 'error'):
            raise PyfbException(obj.error.message)

        return obj

    def get_list(self, id, path, object_name=None):
        """
            Gets A list of objects
        """
        if id is None:
            id = "me"
        if object_name is None:
            object_name = path
        path = "%s/%s" % (id, path.lower())
        
        obj = self.get_one(path, object_name)
        obj_list = self.factory.make_paginated_list(obj, object_name)

        if obj_list == False:
            obj_list = obj.get("data")

        return obj_list

    def push(self, id, path, **data):
        """
            Pushes data to facebook
        """
        if id is None:
            id = "me"
        path = "%s/%s" % (id, path)
        response = self._make_auth_request(path, **data)
        return self._make_object("response", response)

    def delete(self, id):
        """
            Deletes a object by id
        """
        data = {"method": "delete"}
        response = self._make_auth_request(id, **data)
        return self._make_object("response", response)

    def _get_table_name(self, query):
        """
            Try to get the table name from a fql query
        """
        KEY = "FROM"
        try:
            index = query.index(KEY) + len(KEY) + 1
            table = query[index:].strip().split(" ")[0]
            return table
        except Exception, e:
            raise PyfbException("Invalid FQL Syntax")

    def execute_fql_query(self, query):
        """
            Executes a FBQL query and return a list of objects
        """
        table = self._get_table_name(query)
        url_path = self._get_url_path({'q' : query, 'access_token' : self.access_token, 'format' : 'json'})
        url = "%s%s" % (self.FBQL_BASE_URL, url_path)
        data = self._make_request(url)

        objs = self.factory.make_objects_list(table, data)
        
        if hasattr(objs, 'error'):
            raise PyfbException(objs.error.message)

        return objs


class PyfbException(Exception):
    """
        A PyFB Exception class
    """

    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)

########NEW FILE########
__FILENAME__ = pyfb
"""
    This is an Easy to Use Python Interface to the Facebook Graph API

    It gives you methods to access your data on facebook and
    provides objects instead of json dictionaries!
"""

import webbrowser
from client import FacebookClient, PyfbException

class Pyfb(object):
    """
        This class is Facade for FacebookClient
    """

    def __init__(self, app_id, access_token=None, raw_data=False, permissions=None):

        self._client = FacebookClient(app_id, access_token=access_token, raw_data=raw_data, permissions=permissions)

    def authenticate(self):
        """
            Open your prefered web browser to make the authentication request
        """
        self._show_in_browser(self.get_auth_url())

    def get_authentication_code(self):
        """
            Open your prefered web browser to make the authentication request
        """
        self._show_in_browser(self.get_auth_code_url())

    def get_auth_url(self, redirect_uri=None):
        """
            Returns the authentication url
        """
        return self._client.get_auth_token_url(redirect_uri)

    def get_auth_code_url(self, redirect_uri=None, state=None):
        """
            Returns the url to get a authentication code
        """
        return self._client.get_auth_code_url(redirect_uri, state=state)

    def get_access_token(self, app_secret_key, secret_code, redirect_uri=None):
        """
            Gets the access token
        """
        return self._client.get_access_token(app_secret_key, secret_code, redirect_uri)

    def exchange_token(self, app_secret_key, exchange_token):
        """
             Exchanges a short-lived access token (like those obtained from client-side JS api)
             for a longer-lived access token
        """
        return self._client.exchange_token(app_secret_key, exchange_token)

    def show_dialog(self, redirect_uri=None):
        """
            Open your prefered web browser to make the authentication request
        """
        self._show_in_browser(self.get_dialog_url(redirect_uri=redirect_uri))

    def get_dialog_url(self, redirect_uri=None):
        """
            Returns a url inside facebook that shows a dialog allowing
            users to publish contents.
        """
        return self._client.get_dialog_url(redirect_uri)

    def _show_in_browser(self, url):
        """
            Opens your prefered web browser to make the authentication request
        """
        webbrowser.open(url)

    def set_access_token(self, token):
        """
            Sets the access token. Necessary to make the requests that requires autenthication
        """
        self._client.access_token = token

    def set_permissions(self, permissions):
        """
            Sets a list of data access permissions that the user must give to the application
            e.g:
                permissions = [auth.USER_ABOUT_ME, auth.USER_LOCATION, auth.FRIENDS_PHOTOS, ...]
        """
        self._client.permissions = permissions

    def get_myself(self):
        """
            Gets myself data
        """
        return self._client.get_one("me", "FBUser")

    def get_user_by_id(self, id=None):
        """
            Gets an user by the id
        """
        if id is None:
            id = "me"
        return self._client.get_one(id, "FBUser")

    def get_friends(self, id=None):
        """
            Gets a list with your friends
        """
        return self._client.get_list(id, "Friends")

    def get_statuses(self, id=None):
        """
            Gets a list of status objects
        """
        return self._client.get_list(id, "Statuses")

    def get_photos(self, id=None):
        """
            Gets a list of photos objects
        """
        return self._client.get_list(id, "Photos")

    def get_comments(self, id=None):
        """
            Gets a list of photos objects
        """
        return self._client.get_list(id, "Comments")

    def publish(self, message, id=None, **kwargs):
        """
            Publishes a message on the wall
        """
        return self._client.push(id, "feed", message=message, **kwargs)

    def comment(self, message, id=None, **kwargs):
        """
            Publishes a message on the wall
        """
        return self._client.push(id, "comments", message=message, **kwargs)

    def get_likes(self, id=None):
        """
            Get a list of liked objects
        """
        return self._client.get_list(id, "likes")

    def get_pages(self, id=None):
        """
            Get a list of Facebook Pages user has access to
        """
        return self._client.get_list(id, 'accounts', 'FBPage')

    def like(self, id):
        """
            LIKE: It Doesn't work. Seems to be a bug on the Graph API
            http://bugs.developers.facebook.net/show_bug.cgi?id=10714
        """
        print self.like.__doc__
        return self._client.push(id, "likes")

    def delete(self, id):
        """
            Deletes a object
        """
        return self._client.delete(id)

    def fql_query(self, query):
        """
            Executes a FBQL query
        """
        return self._client.execute_fql_query(query)

########NEW FILE########
__FILENAME__ = utils
"""
    $Id: utils.py

    This file provides utilities to the pyfb library
"""

try:
    import json as simplejson
except ImportError:
    import simplejson

import urllib2


class FacebookObject(object):
    """
        Builds an object of a runtime generated class with a name
        passed by argument.
    """
    def __new__(cls, name):
        return type(str(name), (object, ), {})


class PaginatedList(list):

    def __init__(self, objs=None, parent=None, object_name=None):

        if objs is not None:
            self.extend(objs)

        factory = Json2ObjectsFactory()

        def _get_page(page):

            paging = getattr(parent, "paging", False)
            if not paging:
                return PaginatedList()

            url = getattr(paging, page, False)
            if not url:
                return PaginatedList()

            obj = factory.make_object(object_name, urllib2.urlopen(url).read())
            objs_list = factory.make_paginated_list(obj, object_name)

            if not objs_list:
                return PaginatedList()

            return objs_list

        self.next = lambda: _get_page("next")
        self.previous = lambda: _get_page("previous")


class Json2ObjectsFactory(object):
    """
        Converts a json-like dictionary into an object.

        It navigates recursively into the dictionary turning
        everything into an object.
    """

    def loads(self, data):
        return simplejson.loads(data)

    def make_object(self, name, data):
        raw = self.loads(data)
        return self._make_object(name, raw)

    def make_objects_list(self, name, data):
        raw = self.loads(data)
        return self._make_objects_list(name, raw)

    def make_paginated_list(self, obj, object_name):

        objs = getattr(obj, object_name, False)
        if objs == False:
            return False

        objs_list = PaginatedList(objs, obj, object_name)
        return objs_list

    def _make_objects_list(self, name, values):
        objs = []
        for data in values:
            if isinstance(data, dict):
                objs.append(self._make_object(name, data))
            else:
                objs.append(data)
        return objs

    def _make_object(self, name, dic):
        #Life's easy. For Python Programmers BTW ;-).
        obj = FacebookObject(name)
        for key, value in dic.iteritems():
            if key == 'data':
                key = obj.__name__
            if isinstance(value, list):
                value = self._make_objects_list(key, value)
            elif isinstance(value, dict):
                value = self._make_object(key, value)
            setattr(obj, key, value)
        return obj

########NEW FILE########
__FILENAME__ = test
import unittest
try:
	import simplejson as json
except ImportError:
	import json

from pyfb import Pyfb

try:
    from test_data import config
except:
	print "\nERROR! You must have a test_data.py file providing the facebook app id and the access token."
	print "\nExample:"
	print '\tconfig = {\n\t\t"FACEBOOK_APP_ID": "your_app_id"\n\t\t"FACEBOOK_TOKEN": "your_token"\n\t}\n'
	exit(1)


class PyfbTests(unittest.TestCase):

    pyfb_args = {}

    def setUp(self):
        self.pyfb = Pyfb(config["FACEBOOK_APP_ID"], **self.pyfb_args)
        self.pyfb.set_access_token(config["FACEBOOK_TOKEN"])
        self.me = self.pyfb.get_myself()

    def test_auth(self):
        self.assertEquals(type(self.me.name), type(unicode()))

    def test_get_friends(self):
        self.assertTrue(isinstance(self.pyfb.get_friends(self.me.id), list))

    def test_get_photos_paging(self):    	
        photos = self.pyfb.get_photos()
        more_photos = photos.next()
        more_more_photos = more_photos.next()

        if len(photos) < 25 and len(more_photos) > 0:
        	raise Exception()
        
        if len(photos) == 25 and len(more_photos) < 25 and len(more_more_photos) > 0:
        	raise Exception()

        self.assertTrue(isinstance(photos, list))
        self.assertTrue(isinstance(more_photos, list))
        self.assertTrue(isinstance(more_more_photos, list))

        self.assertEquals(len(photos), len(more_photos.previous()))
        self.assertEquals(photos.previous(), [])


class PyfbTestRawDataTests(PyfbTests):

    pyfb_args = {"raw_data": True }

    def test_auth(self):
        self.assertEquals(type(self.me["name"]), type(unicode()))

    def test_get_friends(self):
        friends = self.pyfb.get_friends(self.me["id"])
        self.assertTrue(isinstance(friends, list))
        for friend in friends:
            self.assertTrue(isinstance(friend, dict))

    def test_get_photos_paging(self):       
        """
            pagination is not supported by raw data since it returns a dictionary instead 
            of an object.
        """
        pass


if __name__ == "__main__":

    unittest.main()


########NEW FILE########
