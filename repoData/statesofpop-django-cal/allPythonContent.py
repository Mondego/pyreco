__FILENAME__ = views
import vobject
from django.db.models import ObjectDoesNotExist
from django.http import HttpResponse, Http404
from django.utils.encoding import force_unicode
from django.conf import settings

from django.contrib.syndication.views import add_domain
if add_domain.func_code.co_argcount < 3:
    # Django <= 1.2
    # Source: Django 1.4 django.contrib.syndication.views
    from django.utils.encoding import iri_to_uri

    def add_domain(domain, url, secure=False):
        protocol = 'https' if secure else 'http'
        if url.startswith('//'):
            # Support network-path reference (see #16753) - RSS requires a protocol
            url = '%s:%s' % (protocol, url)
        elif not (url.startswith('http://')
                or url.startswith('https://')
                or url.startswith('mailto:')):
            # 'url' must already be ASCII and URL-quoted, so no need for encoding
            # conversions here.
            url = iri_to_uri(u'%s://%s%s' % (protocol, domain, url))
        return url

if 'django.contrib.sites' in settings.INSTALLED_APPS:
    try:
        # Django > 1.2
        from django.contrib.sites.models import get_current_site
    except ImportError:
        # Django <= 1.2
        # Source: Django 1.4 django.contrib.sites.models
        from django.contrib.sites.models import Site, RequestSite

        def get_current_site(request):
            """
            Checks if contrib.sites is installed and returns either the current
            ``Site`` object or a ``RequestSite`` object based on the request.
            """
            if Site._meta.installed:
                current_site = Site.objects.get_current()
            else:
                current_site = RequestSite(request)
            return current_site
else:
    get_current_site = None


# Mapping of iCalendar event attributes to prettier names.
EVENT_ITEMS = (
    ('uid', 'item_uid'),
    ('dtstart', 'item_start'),
    ('dtend', 'item_end'),
    ('duration', 'item_duration'),
    ('summary', 'item_summary'),
    ('description', 'item_description'),
    ('location', 'item_location'),
    ('url', 'item_url'),
    ('comment', 'item_comment'),
    ('last-modified', 'item_last_modified'),
    ('created', 'item_created'),
    ('categories', 'item_categories'),
    ('rruleset', 'item_rruleset')
)

class Events(object):
    def __call__(self, request, *args, **kwargs):
        """ Makes Events callable for easy use in your urls.py """
        try:
            obj = self.get_object(request, *args, **kwargs)
        except ObjectDoesNotExist:
            raise Http404('Events object does not exist.')
        ical = self.get_ical(obj, request)
        response = HttpResponse(ical.serialize(),
            mimetype='text/calendar;charset=' + settings.DEFAULT_CHARSET)
        filename = self.__get_dynamic_attr('filename', obj)
        # following added for IE, see
        # http://blog.thescoop.org/archives/2007/07/31/django-ical-and-vobject/
        response['Filename'] = filename 
        response['Content-Disposition'] = 'attachment; filename=%s' % filename
        return response


    def __get_dynamic_attr(self, attname, obj, default=None):
        """ Returns first defined occurence of the following: 
                self.$attname(obj)
                self.$attname()
                self.$attname
                default
            Taken from django.contrib.syndication.views.Feed
        """
        try:
            attr = getattr(self, attname)
        except AttributeError:
            return default
        if callable(attr):
            # Check func_code.co_argcount rather than try/excepting the
            # function and catching the TypeError, because something inside
            # the function may raise the TypeError. This technique is more
            # accurate.
            if hasattr(attr, 'func_code'):
                argcount = attr.func_code.co_argcount
            else:
                argcount = attr.__call__.func_code.co_argcount
            if argcount == 2: # one argument is 'self'
                return attr(obj)
            else:
                return attr()
        return attr

    def get_ical(self, obj, request):
        """ Returns a populated iCalendar instance. """
        cal = vobject.iCalendar()
        cal.add('method').value = 'PUBLISH'  # IE/Outlook needs this
        items = self.__get_dynamic_attr("items", obj)
        cal_name = self.__get_dynamic_attr("cal_name", obj)
        cal_desc = self.__get_dynamic_attr("cal_desc", obj)
        # Add calendar name and description if set 
        if cal_name:
            cal.add('x-wr-calname').value = cal_name
        if cal_desc:
            cal.add('x-wr-caldesc').value = cal_desc

        if get_current_site:
            current_site = get_current_site(request)
        else:
            current_site = None

        for item in items:
            event = cal.add('vevent')
            for vkey, key in EVENT_ITEMS:
                value = self.__get_dynamic_attr(key, item)
                if value:
                    if vkey == 'rruleset':
                        event.rruleset = value
                    else:
                        if vkey == 'url' and current_site:
                            value = add_domain(
                                current_site.domain,
                                value,
                                request.is_secure(),
                            )
                        event.add(vkey).value = value
        return cal

    # ONLY DEFAULT PARAMETERS FOLLOW #

    def get_object(self, request, *args, **kwargs):
        return None

    def item_summary(self, item):
        return force_unicode(item)

    def item_url(self, item):
        return getattr(item, 'get_absolute_url', lambda: None)()

    def filename(self, item):
        return u"events.ics"

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
# Django settings for example_project project.

DEBUG = True
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    # ('Your Name', 'your_email@domain.com'),
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
SECRET_KEY = 'ax^g3)3w94ufy@6nl-$0=hq#44aced+iox(qq9x*uxi^cx%^nx'

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

ROOT_URLCONF = 'example_project.urls'

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
    'testapp',
    'django_cal',
    # Uncomment the next line to enable the admin:
    # 'django.contrib.admin',
    # Uncomment the next line to enable admin documentation:
    # 'django.contrib.admindocs',
)

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
import datetime
import django_cal
from django_cal.views import Events
import dateutil.rrule as rrule

class Testevents(Events):
    def items(self):
        return ["Whattaday!", "meow"]

    def cal_name(self):
        return "a pretty calendar."

    def cal_desc(self):
        return "Lorem ipsum tralalala."

    def item_summary(self, item):
        return "That was suchaday!"

    def item_start(self, item):
        return datetime.date(year=2011, month=1, day=24)

    def item_end(self, item):
        return datetime.date(year=2011, month=1, day=26)

    def item_rruleset(self, item):
        rruleset = rrule.rruleset()
        rruleset.rrule(rrule.YEARLY, count=10, dtstart=self.item_start(item))
        return rruleset

    def item_categories(self, item):
        return ["Family", "Birthdays"]

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import *
from testapp.views import Testevents
# Uncomment the next two lines to enable the admin:
# from django.contrib import admin
# admin.autodiscover()

urlpatterns = patterns('',
    # Example:
    # (r'^example_project/', include('example_project.foo.urls')),
    (r'^ical$', Testevents()),

    # Uncomment the admin/doc line below to enable admin documentation:
    # (r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    # (r'^admin/', include(admin.site.urls)),
)

########NEW FILE########
