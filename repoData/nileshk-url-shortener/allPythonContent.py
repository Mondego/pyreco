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
# Django settings for urlweb project.
import os, logging
#from django.conf.global_settings import TEMPLATE_CONTEXT_PROCESSORS

logging.basicConfig(
    level = logging.DEBUG,
    format = '%(asctime)s %(levelname)s %(message)s',
)

logging.debug("Reading settings...")

PROJECT_PATH = os.path.abspath(os.path.dirname(__file__))

DEBUG = True
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    # ('Your Name', 'your_email@domain.com'),
)

MANAGERS = ADMINS

DATABASE_ENGINE = 'sqlite3'           # 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'oracle'.
#DATABASE_NAME = ''             # Or path to database file if using sqlite3.
DATABASE_NAME = os.path.join(PROJECT_PATH, 'database.sqlite')
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
SECRET_KEY = '#### CHANGE_ME ####'

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
#    'django.middleware.transaction.TransactionMiddleware',    
)

ROOT_URLCONF = 'urlweb.urls'

TEMPLATE_DIRS = (
    os.path.join(PROJECT_PATH, 'templates')    
)

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.admin',
    'urlweb.shortener',
)

STATIC_DOC_ROOT = os.path.join(PROJECT_PATH, 'static')
LOGIN_REDIRECT_URL = '/'

#TEMPLATE_CONTEXT_PROCESSORS += (
#    'django.core.context_processors.request',
#    ) 

SITE_NAME = 'localhost:8000'
SITE_BASE_URL = 'http://' + SITE_NAME + '/'
REQUIRE_LOGIN = True

########NEW FILE########
__FILENAME__ = admin
from django.contrib import admin

from urlweb.shortener.models import Link

class LinkAdmin(admin.ModelAdmin):
    model = Link
    extra = 3

admin.site.register(Link, LinkAdmin)

########NEW FILE########
__FILENAME__ = baseconv
"""
Convert numbers from base 10 integers to base X strings and back again.

Original: http://www.djangosnippets.org/snippets/1431/

Sample usage:

>>> base20 = BaseConverter('0123456789abcdefghij')
>>> base20.from_decimal(1234)
'31e'
>>> base20.to_decimal('31e')
1234
"""

class BaseConverter(object):
    decimal_digits = "0123456789"
    
    def __init__(self, digits):
        self.digits = digits
    
    def from_decimal(self, i):
        return self.convert(i, self.decimal_digits, self.digits)
    
    def to_decimal(self, s):
        return int(self.convert(s, self.digits, self.decimal_digits))
    
    def convert(number, fromdigits, todigits):
        # Based on http://code.activestate.com/recipes/111286/
        if str(number)[0] == '-':
            number = str(number)[1:]
            neg = 1
        else:
            neg = 0

        # make an integer out of the number
        x = 0
        for digit in str(number):
           x = x * len(fromdigits) + fromdigits.index(digit)
    
        # create the result in base 'len(todigits)'
        if x == 0:
            res = todigits[0]
        else:
            res = ""
            while x > 0:
                digit = x % len(todigits)
                res = todigits[digit] + res
                x = int(x / len(todigits))
            if neg:
                res = '-' + res
        return res
    convert = staticmethod(convert)

bin = BaseConverter('01')
hexconv = BaseConverter('0123456789ABCDEF')
base62 = BaseConverter(
    'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789abcdefghijklmnopqrstuvwxyz'
)

########NEW FILE########
__FILENAME__ = models
import datetime

from django.db import models
from django.conf import settings
#from django.contrib.auth.models import User
from django import forms

from urlweb.shortener.baseconv import base62

class Link(models.Model):
    """
    Model that represents a shortened URL

    # Initialize by deleting all Link objects
    >>> Link.objects.all().delete()
    
    # Create some Link objects
    >>> link1 = Link.objects.create(url="http://www.google.com/")
    >>> link2 = Link.objects.create(url="http://www.nileshk.com/")

    # Get base 62 representation of id
    >>> link1.to_base62()
    'B'
    >>> link2.to_base62()
    'C'
    
    # Set SITE_BASE_URL to something specific
    >>> settings.SITE_BASE_URL = 'http://uu4.us/'

    # Get short URL's
    >>> link1.short_url()
    'http://uu4.us/B'
    >>> link2.short_url()
    'http://uu4.us/C'

    # Test usage_count
    >>> link1.usage_count
    0
    >>> link1.usage_count += 1
    >>> link1.usage_count
    1

    """
    url = models.URLField(verify_exists=True, unique=True)
    date_submitted = models.DateTimeField(auto_now_add=True)
    usage_count = models.IntegerField(default=0)

    def to_base62(self):
        return base62.from_decimal(self.id)

    def short_url(self):
        return settings.SITE_BASE_URL + self.to_base62()
    
    def __unicode__(self):
        return self.to_base62() + ' : ' + self.url

class LinkSubmitForm(forms.Form):
    u = forms.URLField(verify_exists=True,
                       label='URL to be shortened:',
                       )

########NEW FILE########
__FILENAME__ = tests
"""
Tests for views
"""

__test__ = {"doctest": """

# Initialize by deleting all Link objects
>>> from models import Link
>>> Link.objects.all().delete()

>>> from django.test import Client
>>> client = Client()

# Index page
>>> r = client.get('/')
>>> r.status_code # /
200
>>> r.template[0].name
'shortener/index.html'

# Turn off logged-in requirement and set base URL
>>> from django.conf import settings
>>> settings.REQUIRE_LOGIN = False
>>> settings.SITE_BASE_URL = 'http://uu4.us/'

# Empty submission should forward to error page
>>> r = client.get('/submit/')
>>> r.status_code # /submit/
200
>>> r.template[0].name # /submit/
'shortener/submit_failed.html'

# Submit a URL
>>> url = 'http://www.google.com/'
>>> r = client.get('/submit/', {'u': url})
>>> r.status_code # /submit/u?=http%3A%2F%2Fwww.google.com%2F
200
>>> r.template[0].name
'shortener/submit_success.html'
>>> link = r.context[0]['link']
>>> link.to_base62()
'B'
>>> link.short_url()
'http://uu4.us/B'
>>> link_from_db = Link.objects.get(url = url)
>>> base62 = link_from_db.to_base62()
>>> base62
'B'
>>> link_from_db.usage_count
0

# Short URL for previously submitted URL
>>> r = client.get('/' + base62)
>>> r.status_code # '/' + base62
301
>>> r['Location']
'http://www.google.com/'

# Invalid URL should get a 404
>>> r = client.get('/INVALID')
>>> r.status_code # /INVALID
404

# Index now shows link in recent_links / most_popular_links
>>> r = client.get('/')
>>> r.status_code # /
200
>>> r.template[0].name
'shortener/index.html'
>>> context = r.context[0]
>>> len(context['recent_links'])
1
>>> len(context['most_popular_links'])
1

# Get info on Link
>>> r = client.get('/info/' + base62)
>>> r.status_code # info
200
>>> r.template[0].name
'shortener/link_info.html'
>>> link = r.context[0]['link']
>>> link.url
u'http://www.google.com/'
>>> link.usage_count # Usage count should be 1 now
1

"""}


########NEW FILE########
__FILENAME__ = views
import logging

from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate
from django.views.generic import list_detail
from django.shortcuts import get_object_or_404, get_list_or_404, render_to_response
from django.http import HttpResponse, Http404, HttpResponseRedirect, HttpResponsePermanentRedirect
from django.utils import simplejson
from django.template import RequestContext
from django.views.decorators.http import require_POST
from django.db import transaction
from django.conf import settings

from urlweb.shortener.baseconv import base62
from urlweb.shortener.models import Link, LinkSubmitForm

def follow(request, base62_id):
    """ 
    View which gets the link for the given base62_id value
    and redirects to it.
    """
    key = base62.to_decimal(base62_id)
    link = get_object_or_404(Link, pk = key)
    link.usage_count += 1
    link.save()
    return HttpResponsePermanentRedirect(link.url)

def default_values(request, link_form=None):
    """ 
    Return a new object with the default values that are typically
    returned in a request.
    """
    if not link_form:
        link_form = LinkSubmitForm()
    allowed_to_submit = is_allowed_to_submit(request)
    return { 'show_bookmarklet': allowed_to_submit,
             'show_url_form': allowed_to_submit,
             'site_name': settings.SITE_NAME,
             'site_base_url': settings.SITE_BASE_URL,
             'link_form': link_form,
             }

def info(request, base62_id):
    """
    View which shows information on a particular link
    """
    key = base62.to_decimal(base62_id)
    link = get_object_or_404(Link, pk = key)
    values = default_values(request)
    values['link'] = link
    return render_to_response(
        'shortener/link_info.html',
        values,
        context_instance=RequestContext(request))

def submit(request):
    """
    View for submitting a URL
    """
    if settings.REQUIRE_LOGIN and not request.user.is_authenticated():
        # TODO redirect to an error page
        raise Http404
    url = None
    link_form = None
    if request.GET:
        link_form = LinkSubmitForm(request.GET)
    elif request.POST:
        link_form = LinkSubmitForm(request.POST)
    if link_form and link_form.is_valid():
        url = link_form.cleaned_data['u']
        link = None
        try:
            link = Link.objects.get(url = url)
        except Link.DoesNotExist:
            pass
        if link == None:
            new_link = Link(url = url)
            new_link.save()
            link = new_link
        values = default_values(request)
        values['link'] = link
        return render_to_response(
            'shortener/submit_success.html',
            values,
            context_instance=RequestContext(request))
    values = default_values(request, link_form=link_form)
    return render_to_response(
        'shortener/submit_failed.html',
        values,
        context_instance=RequestContext(request))

def index(request):
    """
    View for main page (lists recent and popular links)
    """
    values = default_values(request)
    values['recent_links'] = Link.objects.all().order_by('-date_submitted')[0:10]
    values['most_popular_links'] = Link.objects.all().order_by('-usage_count')[0:10]
    return render_to_response(
        'shortener/index.html',
        values,
        context_instance=RequestContext(request))

def is_allowed_to_submit(request):
    """
    Return true if user is allowed to submit URLs
    """
    return not settings.REQUIRE_LOGIN or request.user.is_authenticated()

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import *
from django.contrib import admin
from django.conf import settings

admin.autodiscover()

urlpatterns = patterns(
    '',
    (r'^$', 'shortener.views.index'),    
    (r'^admin/(.*)', admin.site.root),    
    (r'^submit/$', 'shortener.views.submit'),
    (r'^(?P<base62_id>\w+)$', 'shortener.views.follow'),
    (r'^info/(?P<base62_id>\w+)$', 'shortener.views.info'),    

    (r'^static/(?P<path>.*)$', 'django.views.static.serve',
      {'document_root': settings.STATIC_DOC_ROOT}),
)

########NEW FILE########
