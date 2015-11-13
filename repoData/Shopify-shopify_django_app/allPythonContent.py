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
from django.conf.urls import patterns, include, url

urlpatterns = patterns('',
        url(r'^$', 'home.views.index', name='root_path'),
        url(r'^design/$', 'home.views.design'),
        url(r'^welcome/$', 'home.views.welcome'),
)

########NEW FILE########
__FILENAME__ = views
from django.shortcuts import render_to_response
from django.template import RequestContext
import shopify
from shopify_app.decorators import shop_login_required

def welcome(request):
    return render_to_response('home/welcome.html', {
        'callback_url': "http://%s/login/finalize" % (request.get_host()),
    }, context_instance=RequestContext(request))

@shop_login_required
def index(request):
    products = shopify.Product.find(limit=3)
    orders = shopify.Order.find(limit=3, order="created_at DESC")
    return render_to_response('home/index.html', {
        'products': products,
        'orders': orders,
    }, context_instance=RequestContext(request))

def design(request):
    return render_to_response('home/design.html', {},
                              context_instance=RequestContext(request))

########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python
import os
import sys

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")

    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)

########NEW FILE########
__FILENAME__ = settings
import os
from shopify_settings import *

SITE_ROOT = os.path.dirname(os.path.realpath(__file__))

try:
    from djangoappengine.settings_base import *
    USING_APP_ENGINE = True
except ImportError:
    USING_APP_ENGINE = False

    DEBUG = True
    TEMPLATE_DEBUG = DEBUG

    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3', # Add 'postgresql_psycopg2', 'postgresql', '
            'NAME': os.path.join(SITE_ROOT, 'db-development.sqlite3'),
            'USER': '',                      # Not used with sqlite3.
            'PASSWORD': '',                  # Not used with sqlite3.
            'HOST': '',                      # Set to empty string for localhost. Not used with 
            'PORT': '',                      # Set to empty string for default. Not used with sq
        }
    }

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
    os.path.join(SITE_ROOT, 'static'),
)

# Absolute path to the directory static files should be collected to.
# Don't put anything in this directory yourself; store your static files
# in apps' "static/" subdirectories and in STATICFILES_DIRS.
# Example: "/home/media/media.lawrence.com/static/"
STATIC_ROOT = ''

# URL prefix for static files.
# Example: "http://media.lawrence.com/static/"
STATIC_URL = '/static/'

# Make this unique, and don't share it with anybody.
SECRET_KEY = '#w%yp9_5wnupojr=4o0mwap#!)y=q9ovu=o#xnytga7u5^bf27'

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
)

TEMPLATE_CONTEXT_PROCESSORS = (
    'django.contrib.auth.context_processors.auth',
    'django.core.context_processors.debug',
    'django.core.context_processors.i18n',
    'django.core.context_processors.media',
    'django.core.context_processors.request',
    'django.contrib.messages.context_processors.messages',
    'shopify_app.context_processors.current_shop',
)
if not USING_APP_ENGINE:
    TEMPLATE_CONTEXT_PROCESSORS += (
            'django.core.context_processors.static',
    )

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'shopify_app.middleware.LoginProtection',
)

ROOT_URLCONF = 'urls'

TEMPLATE_DIRS = (
    os.path.join(SITE_ROOT, 'templates'),
)

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'home',
    'shopify_app',
)
if USING_APP_ENGINE:
    INSTALLED_APPS += (
        'djangoappengine',
        'djangotoolbox',
    )
else:
    INSTALLED_APPS += (
        'django.contrib.sites',
        'django.contrib.staticfiles',
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
__FILENAME__ = context_processors
import shopify

def current_shop(request):
    if not shopify.ShopifyResource.site:
        return {'current_shop': None}
    return {'current_shop': shopify.Shop.current()}

########NEW FILE########
__FILENAME__ = decorators
from django.shortcuts import redirect
from django.core.urlresolvers import reverse
from django.conf import settings

def shop_login_required(func):
    def wrapper(request, *args, **kwargs):
        if not hasattr(request, 'session') or 'shopify' not in request.session:
            request.session['return_to'] = request.get_full_path()
            return redirect(reverse('shopify_app.views.login'))
        return func(request, *args, **kwargs)
    wrapper.__name__ = func.__name__
    return wrapper

########NEW FILE########
__FILENAME__ = middleware
from django.conf import settings
from django.core.urlresolvers import reverse
import shopify

class ConfigurationError(StandardError):
    pass

class LoginProtection(object):
    def __init__(self):
        if not settings.SHOPIFY_API_KEY or not settings.SHOPIFY_API_SECRET:
            raise ConfigurationError("SHOPIFY_API_KEY and SHOPIFY_API_SECRET must be set in settings")
        shopify.Session.setup(api_key=settings.SHOPIFY_API_KEY,
                              secret=settings.SHOPIFY_API_SECRET)

    def process_view(self, request, view_func, view_args, view_kwargs):
        if hasattr(request, 'session') and 'shopify' in request.session:
            shopify_session = shopify.Session(request.session['shopify']['shop_url'])
            shopify_session.token = request.session['shopify']['access_token']
            shopify.ShopifyResource.activate_session(shopify_session)

    def process_response(self, request, response):
        shopify.ShopifyResource.clear_session()
        return response

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls import patterns, include, url

urlpatterns = patterns('',
        url(r'^$', 'shopify_app.views.login'),
        url(r'^authenticate/$', 'shopify_app.views.authenticate'),
        url(r'^finalize/$', 'shopify_app.views.finalize'),
        url(r'^logout/$', 'shopify_app.views.logout'),
)

########NEW FILE########
__FILENAME__ = views
from django.shortcuts import render_to_response, redirect
from django.contrib import messages
from django.core.urlresolvers import reverse
from django.template import RequestContext
from django.conf import settings
import shopify

def _return_address(request):
    return request.session.get('return_to') or reverse('root_path')

def login(request):
    # Ask user for their ${shop}.myshopify.com address

    # If the ${shop}.myshopify.com address is already provided in the URL,
    # just skip to authenticate
    if request.REQUEST.get('shop'):
        return authenticate(request)
    return render_to_response('shopify_app/login.html', {},
                              context_instance=RequestContext(request))

def authenticate(request):
    shop = request.REQUEST.get('shop')
    if shop:
        scope = settings.SHOPIFY_API_SCOPE
        redirect_uri = request.build_absolute_uri(reverse('shopify_app.views.finalize'))
        permission_url = shopify.Session(shop.strip()).create_permission_url(scope, redirect_uri)
        return redirect(permission_url)

    return redirect(_return_address(request))

def finalize(request):
    shop_url = request.REQUEST.get('shop')
    try:
        shopify_session = shopify.Session(shop_url)
        request.session['shopify'] = {
            "shop_url": shop_url,
            "access_token": shopify_session.request_token(request.REQUEST)
        }

    except Exception:
        messages.error(request, "Could not log in to Shopify store.")
        return redirect(reverse('shopify_app.views.login'))

    messages.info(request, "Logged in to shopify store.")

    response = redirect(_return_address(request))
    request.session.pop('return_to', None)
    return response

def logout(request):
    request.session.pop('shopify', None)
    messages.info(request, "Successfully logged out.")

    return redirect(reverse('shopify_app.views.login'))

########NEW FILE########
__FILENAME__ = shopify_settings
# Replace the API Key and Shared Secret with the one given for your
# App by Shopify.
#
# To create an application, or find the API Key and Secret, visit:
# - for private Apps:
#     https://${YOUR_SHOP_NAME}.myshopify.com/admin/api
# - for partner Apps:
#     https://www.shopify.com/services/partners/api_clients
#
# You can ignore this file in git using the following command:
#   git update-index --assume-unchanged shopify_settings.py
import os
SHOPIFY_API_KEY = os.environ.get('SHOPIFY_API_KEY')
SHOPIFY_API_SECRET = os.environ.get('SHOPIFY_API_SECRET')

# See http://api.shopify.com/authentication.html for available scopes
# to determine the permisssions your app will need.
SHOPIFY_API_SCOPE = ['read_products', 'read_orders']

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls import patterns, include, url

urlpatterns = patterns('',
    url(r'^login/', include('shopify_app.urls')),
    url(r'^', include('home.urls'), name='root_path'),
)

########NEW FILE########
