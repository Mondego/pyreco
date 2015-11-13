__FILENAME__ = decorators
from functools import wraps

from django.shortcuts import render_to_response
from django.http import HttpResponse

def render_to(template=None, mobile_template=None, mimetype=None):
    """
    Based upon django-annoying: https://bitbucket.org/offline/django-annoying/

    Decorator for Django views that sends returned dict to render_to_response 
    function.

    Template name can be decorator parameter or TEMPLATE item in returned 
    dictionary.  RequestContext always added as context instance.
    If view doesn't return dict then decorator simply returns output.

    Parameters:
     - template: template name to use
     - mobile_template: template used when device is mobile device
     - mimetype: content type to send in response headers
    """
    def renderer(function):
        @wraps(function)
        def wrapper(request, *args, **kwargs):
            output = function(request, *args, **kwargs)
            if not isinstance(output, dict):
                return output
            if request.browser_info.get('ismobiledevice') and not request.session.get('force_desktop_version'):
                template = mobile_template
            tmpl = output.pop('TEMPLATE', template)
            return render_to_response(tmpl, output, \
                        context_instance=RequestContext(request), mimetype=mimetype)
        return wrapper
    return renderer
########NEW FILE########
__FILENAME__ = middleware
from smartagent.utils import detect_user_agent

NEEDED_VALUES = set(['browser', 'majorver', 'minorver', 'cookies',
'activexcontrols', 'cdf', 'parent_index', 'supportscss', 'aolversion',
'frames', 'cssversion', 'isbanned', 'tables', 'iframes', 'vbscript',
'ismobiledevice', 'platform', 'version', 'aol', 'javaapplets', 'parent',
'backgroundsounds', 'win64', 'javascript', 'beta', 'alpha',
'issyndicationreader', 'win32', 'depth', 'crawler', 'win16'])

class UserAgentDetectorMiddleware(object):

    def process_request(self, request):
        """
        Add browser features to request object
        """
        _user_agent = request.META.get('HTTP_USER_AGENT', 'Unknown')
        _user_agent = detect_user_agent(_user_agent)
        user_agent = _user_agent.copy()

        keys = user_agent.keys()
        for key in keys:
            if key not in NEEDED_VALUES:
                user_agent.pop(key)
        request.browser_info = user_agent

########NEW FILE########
__FILENAME__ = models
__author__ = 'James'
  
########NEW FILE########
__FILENAME__ = tests
from django.test import TestCase

from smartagent.utils import detect_user_agent

class BrowserDetectionTest(TestCase):

    def test_user_agent_recognition(self):

        user_agent_list = {
            "Mozilla/5.0 (iPad; U; CPU OS 4_2_1 like Mac OS X; en-us) AppleWebKit/533.17.9 (KHTML, like Gecko) Version/5.0.2 Mobile/8C148 Safari/6533.18.5":{
                'platform': 'iPhone OSX',
            }
        }

        for user_agent, user_agent_meta in user_agent_list.items():
            result = detect_user_agent(user_agent)
            self.assertEqual(result['platform'], user_agent_meta['platform'])

        


########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import *

from smartagent.views import force_desktop_version, unforce_desktop_version

urlpatterns = patterns('',
    url(r'^force_desktop_version/$', force_desktop_version, name="force_desktop_version"),
    url(r'^unforce_desktop_version/$', unforce_desktop_version, name="unforce_desktop_version"),
)
########NEW FILE########
__FILENAME__ = utils
from ConfigParser import SafeConfigParser
import cPickle as pickle
from copy import copy
import time
import re
import os

from django.conf import settings

APP_DIRNAME = os.path.abspath(os.path.dirname(__file__))

SMART_AGENT_SETTINGS = {
    'AGENT_DATASET_LOCATION': os.path.join(APP_DIRNAME, 'agents_basic.pkl'),
}

if hasattr(settings, 'SMART_AGENT_SETTINGS'):
    SMART_AGENT_SETTINGS.update(settings.SMART_AGENT_SETTINGS)

AGENT_DATASET_LOCATION = SMART_AGENT_SETTINGS['AGENT_DATASET_LOCATION']

try:
    agents = pickle.load(open(AGENT_DATASET_LOCATION, 'rb'))
except TypeError:
    raise Warning("User-Agent dataset cannot be found! Make sure that AGENT_DATASET_LOCATION is set.")
    agents = []

def load_agents():
    agents = pickle.load(open(SMART_AGENT_SETTINGS['AGENT_DATASET_LOCATION'], 'rb'))

def get_user_agent_characteristics(agent):
    """
    Get UserAgent's feature list
    """
    current_agent = agent
    while current_agent.has_key('parent'):
        index = current_agent['parent_index']
        parent = agents[index]
        current_agent = parent
        parent_copy = copy(parent)
        parent_copy.update(agent)
        agent = parent_copy
    return agent

def detect_user_agent(user_agent_string):
    """
    >>> r = detect_user_agent("Mozilla/5.0 (iPad; U; CPU OS 4_2_1 like Mac OS X; en-us) AppleWebKit/533.17.9 (KHTML, like Gecko) Version/5.0.2 Mobile/8C148 Safari/6533.18.5")
    >>> r['platform'] == 'iPhone OSX'
    True
    """

    start = time.time()
    candidates = []
    for agent in agents:
        if agent['regex'].match(user_agent_string):
            candidates.append(agent)

    start = time.time()
    candidates.sort(key=lambda x: len(x['name']))

    start = time.time()
    result = get_user_agent_characteristics(candidates[-1])
    return result

def all_possible_matches(user_agent_string):
    candidates = []
    for agent in agents:
        if agent['regex'].match(user_agent_string):
            candidates.append(agent)
            
    candidates.sort(key=lambda x: len(x['name']))
    return [(item['name'], item['depth']) for item in candidates]

if __name__=="__main__":
    ua = "Mozilla/5.0 (iPad; U; CPU OS 4_2_1 like Mac OS X; en-us) AppleWebKit/533.17.9 (KHTML, like Gecko) Version/5.0.2 Mobile/8C148 Safari/6533.18.5"
    print detect_user_agent(ua)['ismobiledevice']

    ua = "Mozilla/5.0 (Windows; U; Windows NT 6.1; en-US) AppleWebKit/534.16 (KHTML, like Gecko) Chrome/10.0.648.204 Safari/534.16"
    print detect_user_agent(ua)['browser']

    ua = "Mozilla/5.0 (Windows NT 6.1; WOW64; rv:2.0) Gecko/20100101 Firefox/4.0"
    print detect_user_agent(ua)['browser']
########NEW FILE########
__FILENAME__ = views
from django.http import HttpResponseRedirect

def force_desktop_version(request):
    """
    Adds a session variable marking if the user wishes to view the desktop version
    """
    request.session['force_desktop_version'] = True
    return HttpResponseRedirect(request.META['HTTP_REFERER'])

def unforce_desktop_version(request):
    """
    Adds a session variable marking if the user does not wish to view the desktop version
    """
    request.session['force_desktop_version'] = False
    return HttpResponseRedirect(request.META['HTTP_REFERER'])
########NEW FILE########
__FILENAME__ = models
from django.db import models

# Create your models here.

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
__FILENAME__ = views
# Create your views here.

from django.template import RequestContext
from django.shortcuts import render_to_response


def browser_data(request):
    return render_to_response('browser_data.html', {'browser_data': request.browser_info}, context_instance=RequestContext(request))



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
__FILENAME__ = settings
# Django settings for test_site project.
import os
import re
PROJECT_DIR = os.path.dirname(__file__)

DEBUG = True
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    # ('Your Name', 'your_email@example.com'),
)

MANAGERS = ADMINS

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3', # Add 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'oracle'.
        'NAME': 'dev.db',                      # Or path to database file if using sqlite3.
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
# trailing slash if there is a path component (optional in other cases).
# Examples: "http://media.lawrence.com/media/", "http://example.com/media/"
MEDIA_URL = ''

# Absolute path to the directory that holds static files.
# Example: "/home/media/media.lawrence.com/static/"
STATIC_ROOT = ''

# URL that handles the static files served from STATIC_ROOT.
# Example: "http://media.lawrence.com/static/"
STATIC_URL = '/static/'

# URL prefix for admin media -- CSS, JavaScript and images.
# Make sure to use a trailing slash.
# Examples: "http://foo.com/static/admin/", "/static/admin/".
ADMIN_MEDIA_PREFIX = '/static/admin/'

# A list of locations of additional static files
STATICFILES_DIRS = ()

# List of finder classes that know how to find static files in
# various locations.
STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
#    'django.contrib.staticfiles.finders.DefaultStorageFinder',
)

# Make this unique, and don't share it with anybody.
SECRET_KEY = '#7#ef5vxw8xslg#%nct)j*93(h$c!tw$6vy&or@z_8rt6(n+)%'

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

    'smartagent.middleware.UserAgentDetectorMiddleware',
)

ROOT_URLCONF = 'test_site.urls'

TEMPLATE_DIRS = (
    os.path.join(PROJECT_DIR, 'templates'),
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
    #'django.contrib.staticfiles',

    'smartagent',
    # Uncomment the next line to enable the admin:
    # 'django.contrib.admin',
    # Uncomment the next line to enable admin documentation:
    # 'django.contrib.admindocs',
)

#SMART_AGENT_SETTINGS = {
#    'AGENT_DATASET_LOCATION': 'agents_basic.pkl',
#}

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
        'django.request':{
            'handlers': ['mail_admins'],
            'level': 'ERROR',
            'propagate': True,
        },
    }
}

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import *

# Uncomment the next two lines to enable the admin:
# from django.contrib import admin
# admin.autodiscover()

urlpatterns = patterns('',
    # Example:
    # (r'^test_site/', include('test_site.foo.urls')),

    # Uncomment the admin/doc line below to enable admin documentation:
    # (r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    # (r'^admin/', include(admin.site.urls)),
    url(r'^browser_data/$', 'core.views.browser_data'),
)

########NEW FILE########
