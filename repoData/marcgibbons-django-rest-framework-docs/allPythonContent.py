__FILENAME__ = models
from django.db import models


class Cigar(models.Model):
    name = models.CharField(max_length=25)
    colour = models.CharField(max_length=30)
    gauge = models.IntegerField()
    length = models.IntegerField()
    price = models.DecimalField(decimal_places=2, max_digits=5)
    notes = models.TextField()
    manufacturer = models.ForeignKey('Manufacturer')

    def get_absolute_url(self):
        return "/api/cigars/%i/" % self.id


class Manufacturer(models.Model):
    name = models.CharField(max_length=25, null=False, blank=False)
    country = models.ForeignKey('Countries')

    def __unicode__(self):
        return self.name


class Countries(models.Model):
    name = models.CharField(max_length=25, null=False, blank=True)

    def __unicode__(self):
        return self.name

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
import views

# Uncomment the next two lines to enable the admin:
from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
    # Examples:
    url(r'^', include('rest_framework_docs.urls')),
    url(r'^api/docs/$', views.ApiDocumentation.as_view(), name='API-of-APIs'),
    url(r'^admin/', include(admin.site.urls)),
)

########NEW FILE########
__FILENAME__ = views
import json
from rest_framework.response import Response
from rest_framework.views import APIView
from cigar_example.restapi import urls
from rest_framework_docs.docs import DocumentationGenerator


class ApiDocumentation(APIView):
    """
    Gets the documentation for the API endpoints
    """
    def get(self, *args, **kwargs):
        docs = DocumentationGenerator(urls.urlpatterns).get_docs()
        return Response(json.loads(docs))




########NEW FILE########
__FILENAME__ = models
from django.db import models

# Create your models here.

########NEW FILE########
__FILENAME__ = serializers
from rest_framework import serializers
from rest_framework import fields
from cigar_example.app import models
from django.db.models.base import get_absolute_url


class CigarSerializer(serializers.ModelSerializer):
    manufacturer_id = fields.WritableField()
    url = fields.URLField(source='get_absolute_url', read_only=True)

    class Meta:
        model = models.Cigar


class ManufacturerSerializer(serializers.ModelSerializer):
    country_id = fields.WritableField()

    class Meta:
        model = models.Manufacturer


class CountrySerializer(serializers.ModelSerializer):

    class Meta:
        model = models.Countries

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

from cigar_example.restapi import views as api_views

# Uncomment the next two lines to enable the admin:
# from django.contrib import admin
# admin.autodiscover()

urlpatterns = patterns('',
    # Examples:
     url(r'custom$', api_views.MyCustomView.as_view(), name='a-custom-view'),
     url(r'cigars/?$', api_views.CigarList.as_view(), name='list_of_cigars'),
     url(r'cigars/(?P<pk>[^/]+)/?$', api_views.CigarDetails.as_view(), name='cigar_details'),

     url(r'manufacturers/?$', api_views.ManufacturerList.as_view(), name='list_of_manufacturers'),
     url(r'manufacturers/(?P<pk>[^/]+)/?$', api_views.ManufacturerDetails.as_view(), name='manufacturer_details'),

     url(r'countries/?$', api_views.CountryList.as_view(), name='list_of_countries'),
     url(r'countries/(?P<pk>[^/]+)/?$', api_views.CountryDetails.as_view(), name='countries_details'),

)

########NEW FILE########
__FILENAME__ = views
from rest_framework.views import Response, APIView
from rest_framework.generics import ListCreateAPIView, RetrieveUpdateDestroyAPIView
from cigar_example.app.models import Cigar, Manufacturer, Countries
from serializers import CigarSerializer, ManufacturerSerializer, CountrySerializer


class CigarList(ListCreateAPIView):
    """
    Lists and creates cigars from the database.
    """

    model = Cigar
    """ This is the model """
    serializer_class = CigarSerializer
    ordering = ("price", "length")
    filter_fields = ("colour",)
    search_fields = ("name", "manufacturer",)

class CigarDetails(RetrieveUpdateDestroyAPIView):
    """
    Gets a detailed view of an individual cigar record. Can be updated and deleted. Each cigar must
    be assigned to a manufacturer
    """
    model = Cigar
    serializer_class = CigarSerializer


class ManufacturerList(ListCreateAPIView):
    """
    Gets the list of cigar manufacturers from the database.
    """
    model = Manufacturer
    serializer_class = ManufacturerSerializer

class ManufacturerDetails(RetrieveUpdateDestroyAPIView):
    """
    Returns the details on a manufacturer
    """
    model = Manufacturer
    serializer_class = ManufacturerSerializer

class CountryList(ListCreateAPIView):
    """
    Gets a list of countries. Allows the creation of a new country.
    """
    model = Countries
    serializer_class = CountrySerializer

class CountryDetails(RetrieveUpdateDestroyAPIView):
    """
    Detailed view of the country
    """
    model = Countries
    serializer_class = CountrySerializer

class MyCustomView(APIView):
    """
    This is a custom view that can be anything at all. It's not using a serializer class,
    but I can define my own parameters like so!

    horse -- the name of your horse

    """
    def get(self, *args, **kwargs):
        """ Docs there """
        return Response({'foo':'bar'})
    def post(self, *args, **kwargs):
        pass

########NEW FILE########
__FILENAME__ = settings
# Django settings for cigar_example project.

DEBUG = True
TEMPLATE_DEBUG = DEBUG

ADMINS = (
)

MANAGERS = ADMINS

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',  # Add 'postgresql_psycopg2', 'mysql', 'sqlite3' or 'oracle'.
        'NAME': 'db.sql',  # Or path to database file if using sqlite3.
        'USER': '',  # Not used with sqlite3.
        'PASSWORD': '',  # Not used with sqlite3.
        'HOST': '',  # Set to empty string for localhost. Not used with sqlite3.
        'PORT': '',  # Set to empty string for default. Not used with sqlite3.
    }
}

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# On Unix systems, a value of None will cause Django to use the same
# timezone as the operating system.
# If running in a Windows environment this must be set to the same as your
# system time zone.
TIME_ZONE = 'America/Montreal'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en-us'

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# If you set this to False, Django will not format dates, numbers and
# calendars according to the current locale.
USE_L10N = True

# If you set this to False, Django will not use timezone-aware datetimes.
USE_TZ = False

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
SECRET_KEY = ')(gpv*_6l+$vcscsox7=xwyfexxw^do!n8998a054wa450-tnl'

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
    # Uncomment the next line for simple clickjacking protection:
    # 'django.middleware.clickjacking.XFrameOptionsMiddleware',
)

ROOT_URLCONF = 'cigar_example.urls'

# Python dotted path to the WSGI application used by Django's runserver.
WSGI_APPLICATION = 'cigar_example.wsgi.application'

TEMPLATE_DIRS = (
    # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
    # '/home/marc/rest-documentation/cigar_example/cigar_example/templates',
)
TEST_RUNNER = 'django_nose.NoseTestSuiteRunner'
SOUTH_TESTS_MIGRATE = False
NOSE_ARGS = ['--nocapture', '--nologcapture']


INSTALLED_APPS = (
    'rest_framework_docs',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django_nose',
    'cigar_example.app',
    'cigar_example.restapi',
    'rest_framework',
    'rest_framework_docs',
    'django.contrib.admin',
)

# A sample logging configuration. The only tangible logging
# performed by this configuration is to send an email to
# the site admins on every HTTP 500 error when DEBUG=False.
# See http://docs.djangoproject.com/en/dev/topics/logging for
# more details on how to customize your logging configuration.
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse'
        }
    },
    'handlers': {
        'mail_admins': {
            'level': 'ERROR',
            'filters': ['require_debug_false'],
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
from django.conf.urls import patterns, include

urlpatterns = patterns('',
    (r'api/', include('cigar_example.restapi.urls')),
    (r'', include('cigar_example.app.urls')),
)

########NEW FILE########
__FILENAME__ = wsgi
"""
WSGI config for cigar_example project.

This module contains the WSGI application used by Django's development server
and any production WSGI deployments. It should expose a module-level variable
named ``application``. Django's ``runserver`` and ``runfcgi`` commands discover
this application via the ``WSGI_APPLICATION`` setting.

Usually you will have the standard Django WSGI application here, but it also
might make sense to replace the whole Django WSGI application with a custom one
that later delegates to the Django one. For example, you could introduce WSGI
middleware here, or combine a Django application with an application of another
framework.

"""
import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "cigar_example.settings")

# This application object is used by any WSGI server configured to use this
# file. This includes Django's development server, if the WSGI_APPLICATION
# setting points here.
from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()

# Apply WSGI middleware here.
# from helloworld.wsgi import HelloWorldApplication
# application = HelloWorldApplication(application)

########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python
import os
import sys

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "cigar_example.settings")

    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)

########NEW FILE########
__FILENAME__ = docs
import jsonpickle
import re
from django.conf import settings
from django.utils.importlib import import_module
from django.contrib.admindocs.utils import trim_docstring
from django.contrib.admindocs.views import simplify_regex
from django.core.urlresolvers import RegexURLResolver, RegexURLPattern
from rest_framework.views import APIView
from itertools import groupby
from django.test.client import RequestFactory
from django.contrib.auth import get_user_model


class DocumentationGenerator():
    """
    Creates documentation for a list of URL patterns pointing to
    Django REST Framework v.2.0, 2.1.3 APIView instances. The
    documentation is created by looking at the view's docstrings,
    the URL pattern objects, the view's serializers and other properties
    """

    def __init__(self, urlpatterns=None):
        """
        Sets urlpatterns
        urlpatterns -- List of UrlPatterns
        """
        if urlpatterns is None:
            urlpatterns = self.get_url_patterns()
        else:
            urlpatterns = self._flatten_patterns_tree(urlpatterns)

        self.urlpatterns = urlpatterns

    def get_docs(self, as_objects=False):
        """
        Gets the documentation as a list of objects or a JSON string

        as_objects -- (bool) default=False. Set to true to return objects instead of JSON
        """
        docs = self.__process_urlpatterns()
        docs.sort(key=lambda x: x.path)  # Sort by path

        if as_objects:
            return docs
        else:
            return jsonpickle.encode(docs, unpicklable=False)

    def get_url_patterns(self):

        urls = import_module(settings.ROOT_URLCONF)
        patterns = urls.urlpatterns

        api_url_patterns = []
        patterns = self._flatten_patterns_tree(patterns)

        for pattern in patterns:
            # If this is a CBV, check if it is an APIView
            if self._get_api_callback(pattern):
                api_url_patterns.append(pattern)

        # get only unique-named patterns, its, because rest_framework can add
        # additional patterns to distinguish format
        #api_url_patterns = self._filter_unique_patterns(api_url_patterns)
        return api_url_patterns

    def _get_api_callback(self, pattern):
        """
        Verifies that pattern callback is a subclass of APIView, and returns the class
        Handles older django & django rest 'cls_instance'
        """
        if not hasattr(pattern, 'callback'):
            return

        if (hasattr(pattern.callback, 'cls') and issubclass(pattern.callback.cls, APIView)):
            return pattern.callback.cls
        elif (hasattr(pattern.callback, 'cls_instance') and isinstance(pattern.callback.cls_instance, APIView)):
            return pattern.callback.cls_instance

    def _flatten_patterns_tree(self, patterns, prefix=''):
        """
        Uses recursion to flatten url tree.

        patterns -- urlpatterns list
        prefix -- (optional) Prefix for URL pattern
        """
        pattern_list = []
        for pattern in patterns:
            if isinstance(pattern, RegexURLPattern):
                pattern.__path = prefix + pattern._regex
                pattern_list.append(pattern)
            elif isinstance(pattern, RegexURLResolver):
                resolver_prefix = pattern._regex
                pattern_list.extend(self._flatten_patterns_tree(pattern.url_patterns, resolver_prefix))
        return pattern_list

    def _filter_unique_patterns(self, patterns):
        """
        Gets only unique patterns by its names
        """
        unique_patterns = []
        # group patterns by its names
        grouped_patterns = groupby(patterns, lambda pattern: pattern.name)
        for name, group in grouped_patterns:
            group_list = list(group)
            # choose from group pattern with shortest regex
            unique = min(group_list, key=lambda pattern: len(pattern.regex.pattern))
            unique_patterns.append(unique)

        return unique_patterns

    def __process_urlpatterns(self):
        """ Assembles ApiDocObject """
        docs = []

        for endpoint in self.urlpatterns:

            # Skip if callback isn't an APIView
            callback = self._get_api_callback(endpoint)
            if callback is None:
                continue

            # Build object and add it to the list
            doc = self.ApiDocObject()
            doc.title = self.__get_title__(endpoint)
            docstring = self.__get_docstring__(endpoint)
            docstring_meta = self.__parse_docstring__(docstring)
            doc.description = docstring_meta['description']
            doc.params = docstring_meta['params']
            doc.path = self.__get_path__(endpoint)
            doc.model = self.__get_model__(callback)
            doc.allowed_methods = self.__get_allowed_methods__(callback)
            doc.fields = self.__get_serializer_fields__(callback)
            doc.filter_fields = self.__get_filter_fields__(callback)
            doc.search_fields = self.__get_search_fields__(callback)
            doc.ordering = self.__get_ordering__(callback)
            docs.append(doc)
            del(doc)  # Clean up

        return docs

    def __get_title__(self, endpoint):
        """
        Gets the URL Pattern name and make it the title
        """
        title = ''
        if endpoint.name is None:
            return title

        name = endpoint.name
        title = re.sub('[-_]', ' ', name)

        return title.title()

    def __get_docstring__(self, endpoint):
        """
        Parses the view's docstring and creates a description
        and a list of parameters
        Example of a parameter:

            myVar -- a variable
        """

        if not hasattr(endpoint, 'callback'):
            return

        return endpoint.callback.__doc__

    def __parse_docstring__(self, docstring):

        docstring = self.__trim(docstring)
        split_lines = docstring.split('\n')
        trimmed = False  # Flag if string needs to be trimmed
        _params = []
        description = docstring

        for line in split_lines:
            if not trimmed:
                needle = line.find('--')
                if needle != -1:
                    trim_at = docstring.find(line)
                    description = docstring[:trim_at]
                    trimmed = True

            params = line.split(' -- ')
            if len(params) == 2:
                _params.append([params[0].strip(), params[1].strip()])

        return {'description': description, 'params': _params}


    def __get_path__(self, endpoint):
        """
        Gets the endpoint path based on the regular expression
        pattern of the URL pattern. Cleans out the regex characters
        and replaces with RESTful URL descriptors
        """
        #return simplify_regex(endpoint.regex.pattern)
        return simplify_regex(endpoint.__path)

    def __get_model__(self, endpoint):
        """
        Gets associated model from the view
        """
        api_view = self._get_api_callback(endpoint)
        if hasattr(api_view, 'model'):
            return api_view.model.__name__

    def __get_allowed_methods__(self, callback):
        """
        Gets allowed methods for the API. (ie. POST, PUT, GET)
        """
        if hasattr(callback, '__call__'):
            return callback().allowed_methods
        else:
            return callback.allowed_methods

    def __get_serializer_fields__(self, callback):
        """
        Gets serializer fields if set in the view. Returns dictionaries
        with field properties (read-only, default, min and max length)
        """
        data = []
        if not hasattr(callback, 'get_serializer_class'):
            return data

        factory = RequestFactory()
        request = factory.get('')
        request.user = get_user_model()()

        if hasattr(callback, '__call__'):
            callback = callback()

        callback.request = request
        serializer = callback.get_serializer_class()

        try:
            fields = serializer().get_fields()
        except:
            return

        for name, field in fields.items():
            field_data = {}
            field_data['type'] = self.__camelcase_to_spaces(field.__class__.__name__)

            for key in ('read_only', 'default', 'max_length', 'min_length'):
                if hasattr(field, key):
                    field_data[key] = getattr(field, key)

            data.append({name: field_data})

        return data

    def __get_filter_fields__(self, callback):
        """Gets filter fields if described in API view"""
        return getattr(callback, 'filter_fields', None)

    def __get_search_fields__(self, callback):
        """Gets search fields if described in API view"""
        return getattr(callback, 'search_fields', None)

    def __get_ordering__(self, callback):
        """Gets ordering fields if described in API view"""
        return getattr(callback, 'ordering', None)

    def __trim(self, docstring):
        """
        Trims whitespace from docstring
        """
        return trim_docstring(docstring)

    def __camelcase_to_spaces(self, camel_string):
        CAMELCASE_BOUNDARY = '(((?<=[a-z])[A-Z])|([A-Z](?![A-Z]|$)))'
        return re.sub(CAMELCASE_BOUNDARY, ' \\1', camel_string)

    class ApiDocObject(object):
        """ API Documentation Object """
        path = None
        title = None
        description = None
        params = []
        allowed_methods = []
        model = None



########NEW FILE########
__FILENAME__ = tests
from django_nose import FastFixtureTestCase
from django.conf.urls import url
from rest_framework_docs.docs import DocumentationGenerator


class DocsTests(FastFixtureTestCase):

    def test_urls(self):
        obj = DocumentationGenerator()
        obj.get_url_patterns()

    def test_get_title(self):
        """
        Tests formatting of title string:
         - Removes dashes and underscores
         - Puts in title case
        """
        endpoint = url(r'^/?$', 'url', name='my_api-documentation')
        obj = DocumentationGenerator()
        result = obj.__get_title__(endpoint)
        self.assertEquals('My Api Documentation', result)

    def test_parse_docstring(self):
        docstring = """
        This is my description

        myvar1 -- a beautiful var
        """
        obj = DocumentationGenerator()
        docstring_meta = obj.__parse_docstring__(docstring)

        self.assertEquals([['myvar1', 'a beautiful var']],
                          docstring_meta['params'])
        self.assertEquals('This is my description\n\n',
                          docstring_meta['description'])


########NEW FILE########
__FILENAME__ = urls
from django.conf.urls import patterns, include, url
from views import documentation

# Uncomment the next two lines to enable the admin:
# from django.contrib import admin
# admin.autodiscover()

urlpatterns = patterns('',
    # Examples:
    url(r'^/?$', documentation, name='api-documentation'),
)

########NEW FILE########
__FILENAME__ = views
from docs import DocumentationGenerator
from django.shortcuts import render_to_response
from django.template.context import RequestContext


def documentation(request, *args, **kwargs):
    docs = DocumentationGenerator().get_docs(as_objects=True)
    return render_to_response("rest_framework_docs/docs.html", {'docs': docs},
                              context_instance=RequestContext(request))

########NEW FILE########
