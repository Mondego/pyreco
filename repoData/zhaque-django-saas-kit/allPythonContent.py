__FILENAME__ = manage
#!/usr/bin/env python
import sys, os.path
sys.path.insert(0, os.path.realpath(os.path.join(os.path.dirname(__file__), "..", "site-python")))

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
# Django settings for project project.

DEBUG = True
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    # ('Your Name', 'your_email@domain.com'),
)

MANAGERS = ADMINS

DATABASE_ENGINE = 'sqlite3'           # 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'oracle'.
DATABASE_NAME = 'django-saas-kit.db'  # Or path to database file if using sqlite3.
DATABASE_USER = ''             # Not used with sqlite3.
DATABASE_PASSWORD = ''         # Not used with sqlite3.
DATABASE_HOST = ''             # Set to empty string for localhost. Not used with sqlite3.
DATABASE_PORT = ''             # Set to empty string for default. Not used with sqlite3.

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
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

# Absolute path to the directory that holds media.
# Example: "/home/media/media.lawrence.com/"
MEDIA_ROOT = ''

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash if there is a path component (optional in other cases).
# Examples: "http://media.lawrence.com", "http://example.com/media/"
MEDIA_URL = ''

# URL prefix for admin media -- CSS, JavaScript and images. Make sure to use a
# trailing slash.
# Examples: "http://foo.com/media/", "/media/".
ADMIN_MEDIA_PREFIX = '/media/'

# Make this unique, and don't share it with anybody.
SECRET_KEY = '+*q3$z(d1@hi^p%645&636$n7r@=w!m)(z9@k9&9s9_7uh%a+s'

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.load_template_source',
    'django.template.loaders.app_directories.load_template_source',
#     'django.template.loaders.eggs.load_template_source',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'muaccounts.middleware.MUAccountsMiddleware',
)

ROOT_URLCONF = 'project.urls'

import os.path
TEMPLATE_DIRS = (
    # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
    os.path.normpath((os.path.join(os.path.dirname(__file__),'..','templates'))),
)

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.admin',
    'django.contrib.admindocs',
    'paypal.pro',
    'paypal.standard.ipn',
    'registration',
    'muaccounts',
    'subscription',
)

from django.conf import global_settings
TEMPLATE_CONTEXT_PROCESSORS = global_settings.TEMPLATE_CONTEXT_PROCESSORS + (
    'django.core.context_processors.request', )

PAYPAL_TEST = True
PAYPAL_RECEIVER_EMAIL='example@example.com'
ACCOUNT_ACTIVATION_DAYS=7
LOGIN_REDIRECT_URL = '/'
SUBSCRIPTION_PAYPAL_SETTINGS = {
    'business' : PAYPAL_RECEIVER_EMAIL,
    }

# Website payments Pro settings
PAYPAL_WPP_USER = ""
PAYPAL_WPP_PASSWORD = ""
PAYPAL_WPP_SIGNATURE = ""

MUACCOUNTS_ROOT_DOMAIN = 'example.com'
MUACCOUNTS_DEFAULT_DOMAIN = 'www.example.com'
MUACCOUNTS_PORT=8000
MUACCOUNTS_ACCOUNT_URLCONF = 'project.urls_muaccount'
MUACCOUNTS_IP = '127.0.0.1'

########NEW FILE########
__FILENAME__ = signal_handlers
import subscription.signals

def impossible_downgrade(sender, subscription, **kwargs):
    before = sender.subscription
    after = subscription
    if not after.price:
        if before.price: return "You cannot downgrade to a free plan."
        else: return None
        
    if before.recurrence_unit:
        if not after.recurrence_unit:
            return "You cannot downgrade from recurring subscription to one-time."
        else:
            if after.price_per_day() > before.price_per_day(): return None
            else: return "You cannot downgrade to a cheaper plan."
    else:
        if not after.recurrence_unit:
            if after.price > before.price: return None
            else: return "You cannot downgrade to a cheaper plan."

__installed = False
def install():
    global __installed
    if not __installed:
        subscription.signals.change_check.connect(impossible_downgrade)
        __installed = True

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import *

from django.contrib import admin
admin.autodiscover()

import signal_handlers
signal_handlers.install()

urlpatterns = patterns('',
    (r'^$', 'django.views.generic.simple.direct_to_template', dict(template='index.html')),
    (r'^accounts/', include('registration.urls')),
    (r'^accounts/mua/', include('muaccounts.urls')),
    (r'^sub/', include('subscription.urls')),
    (r'^admin/doc/', include('django.contrib.admindocs.urls')),
    (r'^admin/(.*)', admin.site.root),
)

########NEW FILE########
__FILENAME__ = urls_muaccount
from django.conf.urls.defaults import *

urlpatterns = patterns('',
    (r'^$', 'django.views.generic.simple.direct_to_template', dict(template='account_index.html')),
    (r'^sorry/$', 'django.views.generic.simple.direct_to_template', dict(template='account_nam.html'), 'muaccounts_not_a_member'),
    (r'^accounts/', include('registration.urls')),
    (r'^admin/', include('muaccounts.urls')),
)

########NEW FILE########
