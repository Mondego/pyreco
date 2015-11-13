__FILENAME__ = fields
# The core of this module was adapted from Google AppEngine's
# GeoPt field, so I've included their copyright and license.
#
# Copyright 2007 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

from django.db import models
from django.core import exceptions

__all__ = ('AddressField', 'GeoLocationField')

def typename(obj):
    """Returns the type of obj as a string. More descriptive and specific than
    type(obj), and safe for any object, unlike __class__."""
    if hasattr(obj, '__class__'):
        return getattr(obj, '__class__').__name__
    else:
        return type(obj).__name__

class GeoPt(object):
    """A geographical point."""

    lat = None
    lon = None

    def __init__(self, lat, lon=None):
        """
        If the model field has 'blank=True' or 'null=True' then
        we can't always expect the GeoPt to be instantiated with
        a valid value. In this case we'll let GeoPt be instantiated
        as an empty item, and the string representation should be
        an empty string instead of 'lat,lon'.
        """
        if not lat:
            return

        if lon is None:
            lat, lon = self._split_geo_point(lat)
        self.lat = self._validate_geo_range(lat, 90)
        self.lon = self._validate_geo_range(lon, 180)

    def __unicode__(self):
        if self.lat is not None and self.lon is not None:
            return "%s,%s" % (self.lat, self.lon)
        return ''

    def __eq__(self, other):
        if isinstance(other, GeoPt):
            return bool(self.lat == other.lat and self.lon == other.lon)
        return False

    def __len__(self):
        return len(self.__unicode__())

    def _split_geo_point(self, geo_point):
        """splits the geo point into lat and lon"""
        try:
            return geo_point.split(',')
        except (AttributeError, ValueError):
            raise exceptions.ValidationError(
                'Expected a "lat,long" formatted string; received %s (a %s).' %
            (geo_point, typename(geo_point)))

    def _validate_geo_range(self, geo_part, range_val):
        try:
            geo_part = float(geo_part)
            if abs(geo_part) > range_val:
                raise exceptions.ValidationError(
                'Must be between -%s and %s; received %s' % (range_val, range_val, geo_part)
            )
        except (TypeError, ValueError):
            raise exceptions.ValidationError(
                'Expected float, received %s (a %s).' % (geo_part, typename(geo_part))
            )
        return geo_part

class AddressField(models.CharField):
    pass

class GeoLocationField(models.CharField):
    """
    A geographical point, specified by floating-point latitude and longitude
    coordinates. Often used to integrate with mapping sites like Google Maps.
    May also be used as ICBM coordinates.

    This is the georss:point element. In XML output, the coordinates are
    provided as the lat and lon attributes. See: http://georss.org/

    Serializes to '<lat>,<lon>'. Raises BadValueError if it's passed an invalid
    serialized string, or if lat and lon are not valid floating points in the
    ranges [-90, 90] and [-180, 180], respectively.
    """
    description = "A geographical point, specified by floating-point latitude and longitude coordinates."
    __metaclass__ = models.SubfieldBase

    def __init__(self, *args, **kwargs):
        kwargs['max_length'] = 100
        super(GeoLocationField, self).__init__(*args, **kwargs)

    def to_python(self, value):
        if isinstance(value, GeoPt):
            return value
        return GeoPt(value)

    def get_prep_value(self, value):
        """prepare the value for database query"""
        if value is None:
            return None
        return unicode(value)

    def get_prep_lookup(self, lookup_type, value):
        # We only handle 'exact' and 'in'. All others are errors.
        if lookup_type == 'exact':
            return self.get_prep_value(value)
        elif lookup_type == 'in':
            return [self.get_prep_value(v) for v in value]
        else:
            raise TypeError('Lookup type %r not supported.' % lookup_type)

    def value_to_string(self, obj):
        value = self._get_val_from_obj(obj)
        return self.get_prep_value(value)

try:
    from south.modelsinspector import add_introspection_rules
    add_introspection_rules([], ["^django_google_maps\.fields\.GeoLocationField"])
    add_introspection_rules([], ["^django_google_maps\.fields\.AddressField"])
except ImportError:
    pass

########NEW FILE########
__FILENAME__ = models

########NEW FILE########
__FILENAME__ = tests
from mock import patch, Mock

from django import test
from django.core import exceptions

from django_google_maps import fields

class GeoPtFieldTests(test.TestCase):

    def test_sets_lat_lon_on_initialization(self):
        geo_pt = fields.GeoPt("15.001,32.001")
        self.assertEqual(15.001, geo_pt.lat)
        self.assertEqual(32.001, geo_pt.lon)

    def test_uses_lat_comma_lon_as_unicode_representation(self):
        lat_lon_string = "15.001,32.001"
        geo_pt = fields.GeoPt(lat_lon_string)
        self.assertEqual(lat_lon_string, unicode(geo_pt))

    def test_two_GeoPts_with_same_lat_lon_should_be_equal(self):
        geo_pt_1 = fields.GeoPt("15.001,32.001")
        geo_pt_2 = fields.GeoPt("15.001,32.001")
        self.assertEqual(geo_pt_1, geo_pt_2)

    def test_two_GeoPts_with_different_lat_should_not_be_equal(self):
        geo_pt_1 = fields.GeoPt("15.001,32.001")
        geo_pt_2 = fields.GeoPt("20.001,32.001")
        self.assertNotEqual(geo_pt_1, geo_pt_2)

    def test_two_GeoPts_with_different_lon_should_not_be_equal(self):
        geo_pt_1 = fields.GeoPt("15.001,32.001")
        geo_pt_2 = fields.GeoPt("15.001,62.001")
        self.assertNotEqual(geo_pt_1, geo_pt_2)

    def test_is_not_equal_when_comparison_is_not_GeoPt_object(self):
        geo_pt_1 = fields.GeoPt("15.001,32.001")
        geo_pt_2 = "15.001,32.001"
        self.assertNotEqual(geo_pt_1, geo_pt_2)

    def test_allows_GeoPt_instantiated_with_empty_string(self):
        geo_pt = fields.GeoPt('')
        self.assertEqual(None, geo_pt.lat)
        self.assertEqual(None, geo_pt.lon)

    def test_uses_empty_string_as_unicode_representation_for_empty_GeoPt(self):
        geo_pt = fields.GeoPt('')
        self.assertEqual('', unicode(geo_pt))

    @patch("django_google_maps.fields.GeoPt.__init__", Mock(return_value=None))
    def test_splits_geo_point_on_comma(self):
        lat, lon = fields.GeoPt(Mock())._split_geo_point("15.001,32.001")
        self.assertEqual('15.001', lat)
        self.assertEqual('32.001', lon)

    @patch("django_google_maps.fields.GeoPt.__init__", Mock(return_value=None))
    def test_raises_error_when_attribute_error_on_split(self):
        geo_point = Mock()
        geo_point.split.side_effect = AttributeError

        geo_pt = fields.GeoPt(Mock())
        self.assertRaises(exceptions.ValidationError, geo_pt._split_geo_point, geo_point)

    @patch("django_google_maps.fields.GeoPt.__init__", Mock(return_value=None))
    def test_raises_error_when_type_error_on_split(self):
        geo_point = Mock()
        geo_point.split.side_effect = ValueError

        geo_pt = fields.GeoPt(Mock())
        self.assertRaises(exceptions.ValidationError, geo_pt._split_geo_point, geo_point)

    @patch("django_google_maps.fields.GeoPt.__init__", Mock(return_value=None))
    def test_returns_float_value_when_valid_value(self):
        geo_pt = fields.GeoPt(Mock())
        val = geo_pt._validate_geo_range('45.005', 90)
        self.assertEqual(45.005, val)
        self.assertIsInstance(val, float)

    @patch("django_google_maps.fields.GeoPt.__init__", Mock(return_value=None))
    def test_raises_exception_when_type_error(self):
        geo_pt = fields.GeoPt(Mock())
        self.assertRaises(exceptions.ValidationError, geo_pt._validate_geo_range, object, 90)

    @patch("django_google_maps.fields.GeoPt.__init__", Mock(return_value=None))
    def test_raises_exception_when_value_error(self):
        geo_pt = fields.GeoPt(Mock())
        self.assertRaises(exceptions.ValidationError, geo_pt._validate_geo_range, 'a', 90)

    @patch("django_google_maps.fields.GeoPt.__init__", Mock(return_value=None))
    def test_raises_exception_when_value_is_out_of_upper_range(self):
        geo_pt = fields.GeoPt(Mock())
        self.assertRaises(exceptions.ValidationError, geo_pt._validate_geo_range, '90.01', 90)

    @patch("django_google_maps.fields.GeoPt.__init__", Mock(return_value=None))
    def test_raises_exception_when_value_is_out_of_lower_range(self):
        geo_pt = fields.GeoPt(Mock())
        self.assertRaises(exceptions.ValidationError, geo_pt._validate_geo_range, '-90.01', 90)

########NEW FILE########
__FILENAME__ = widgets

from django.conf import settings
from django.forms import widgets
from django.utils.encoding import force_unicode
from django.utils.safestring import mark_safe
from django.forms.util import flatatt

class GoogleMapsAddressWidget(widgets.TextInput):
    "a widget that will place a google map right after the #id_address field"
    
    class Media:
        css = {'all': (settings.STATIC_URL + 'django_google_maps/css/google-maps-admin.css',),}
        js = (
            'https://ajax.googleapis.com/ajax/libs/jquery/1.4.4/jquery.min.js',
            'https://maps.google.com/maps/api/js?sensor=false',
            settings.STATIC_URL + 'django_google_maps/js/google-maps-admin.js',
        )

    def render(self, name, value, attrs=None):
        if value is None:
            value = ''
        final_attrs = self.build_attrs(attrs, type=self.input_type, name=name)
        if value != '':
            # Only add the 'value' attribute if a value is non-empty.
            final_attrs['value'] = force_unicode(self._format_value(value))
        return mark_safe(u'<input%s /><div class="map_canvas_wrapper"><div id="map_canvas"></div></div>' % flatatt(final_attrs))

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
__FILENAME__ = admin

from django.contrib import admin
from django.forms.widgets import TextInput

from django_google_maps.widgets import GoogleMapsAddressWidget
from django_google_maps.fields import AddressField, GeoLocationField

from sample import models

class SampleModelAdmin(admin.ModelAdmin):
    formfield_overrides = {
        AddressField: {'widget': GoogleMapsAddressWidget},
        GeoLocationField: {'widget': TextInput(attrs={'readonly': 'readonly'})},
    }

admin.site.register(models.SampleModel, SampleModelAdmin)
########NEW FILE########
__FILENAME__ = models
from django.db import models

from django_google_maps.fields import AddressField, GeoLocationField

# Create your models here.
class SampleModel(models.Model):
    address = AddressField(max_length=100)
    geolocation = GeoLocationField(blank=True)

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
# Create your views here.

########NEW FILE########
__FILENAME__ = settings
# Django settings for google_maps project.

DEBUG = True
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    # ('Your Name', 'your_email@example.com'),
)

MANAGERS = ADMINS

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3', # Add 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'oracle'.
        'NAME': 'sample_db',                      # Or path to database file if using sqlite3.
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
SECRET_KEY = '%hi+eb@u)t)o_qk^#y&eje%*65ghba=1xulgk$_zfx5#&b3$g4'

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

ROOT_URLCONF = 'urls'

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
    # Uncomment the next line to enable the admin:
    'django.contrib.admin',
    # Uncomment the next line to enable admin documentation:
    # 'django.contrib.admindocs',
    'django_google_maps',
    'sample',
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
from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
    # Examples:
    # url(r'^$', 'google_maps.views.home', name='home'),
#    url(r'^google_maps/', include('google_maps.foo.urls')),

    # Uncomment the admin/doc line below to enable admin documentation:
    # url(r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    url(r'^admin/', include(admin.site.urls)),
)

########NEW FILE########
