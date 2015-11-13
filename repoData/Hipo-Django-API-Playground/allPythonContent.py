__FILENAME__ = admin
from django.contrib import admin
from apiplayground.models import Feedback


class FeedbackAdmin(admin.ModelAdmin):
    """Configures admin for Feedback model."""
    list_display = ('title', 'resource', 'status', 'date_created', )
    list_filter = ('status', )
    ordering = ('-date_created', )
admin.site.register(Feedback, FeedbackAdmin)
########NEW FILE########
__FILENAME__ = constants
from django.utils.translation import ugettext_lazy as _

STATUS_OPEN = 0
STATUS_CLOSED = 1

STATUS_CHOICES = (
    (STATUS_OPEN, _('Open')),
    (STATUS_CLOSED, _('Closed')),
)

########NEW FILE########
__FILENAME__ = forms
from django import forms
from django.utils.datastructures import SortedDict

from apiplayground.models import Feedback
from apiplayground.utils import tokenize_url_parameters


class FeedbackForm(forms.ModelForm):
    """
    A form that updates and creates feedbacks.
    """
    title = forms.CharField(widget=forms.TextInput(attrs={
        "required": "required"
    }))

    class Meta:
        model = Feedback
        exclude = ("duplicate", "status")

TYPE_WIDGET_MAPPING = {
    "string": forms.TextInput,
    "boolean": forms.CheckboxInput,
    "select": forms.Select,
    "integer": forms.IntegerField
}


def build_data_form(parameters):
    """
    Builds a form with given parameters as dynamically.
    """
    form_fields = SortedDict()
    for parameter in parameters:
        parameter_name = parameter.get("name")
        parameter_type = parameter.get("type", "string")
        choices = parameter.get("choices", [])
        is_required = parameter.get("is_required", False)
        default = parameter.get("default", None)
        form_widget = TYPE_WIDGET_MAPPING.get(parameter_type)

        assert "name" in parameter, "Parameter name is required"
        assert form_widget is not None, "Wrong field type."
        assert isinstance(choices, (list, tuple)), "Wrong choice type."

        widget = form_widget()

        if parameter_type == "select":
            form_fields[parameter_name] = forms.ChoiceField(
                label=parameter_name,
                widget=widget,
                initial=default,
                choices=choices)
        else:
            form_fields[parameter_name] = forms.CharField(
                label=parameter_name,
                widget=widget,
                initial=default)

        if is_required:
            widget.attrs["required"] = "required"

    return type("DataParameterForm", (forms.Form,), form_fields)


def build_url_form(url):
    """
    Builds a url parameter form from the given url.
    """
    form_fields = SortedDict()
    url_parameters = tokenize_url_parameters(url)
    for token, parameter in url_parameters:
        form_fields["url-parameter-%s" % parameter] = forms.CharField(
            label=parameter, widget=forms.TextInput(attrs={
                "required": "required",
                "data-token": token,
                }))

    return type("URLParameterForm", (forms.Form,), form_fields)

########NEW FILE########
__FILENAME__ = models
from django.db import models
from django.utils.encoding import smart_unicode

from apiplayground.constants import STATUS_CHOICES, STATUS_OPEN


class Feedback(models.Model):
    """
    Holds Feedback data.
    """
    title = models.CharField(max_length=255)
    resource = models.CharField(max_length=255, null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    status = models.IntegerField(choices=STATUS_CHOICES, default=STATUS_OPEN)
    duplicate = models.ForeignKey("self", null=True, blank=True)
    date_created = models.DateTimeField(auto_now_add=True)
    date_modified = models.DateTimeField(auto_now=True)

    def __unicode__(self):
        return smart_unicode(self.title)

########NEW FILE########
__FILENAME__ = playground
import json
import markdown

from django.conf.urls import url
from django.http import HttpResponse, HttpResponseBadRequest
from django.shortcuts import render_to_response
from django.template import RequestContext

from apiplayground.forms import FeedbackForm
from apiplayground.settings import API_PLAYGROUND_SCHEMA_PATH, \
    API_PLAYGROUND_FEEDBACK


class APIPlayground(object):
    """
    A base class that encapsulates all api browser options.
    """
    index_template = "api_browser/index.html"
    feedback_template = "api_browser/submit_feedback.html"
    feedback_form = FeedbackForm
    schema = None

    def get_serializer(self):
        """
        Returns serialization class or module.
        You can override this method for using other serialization libraries.
        Example:

            # import yaml library at the top of python script.
            def get_serializer(self):
                return yaml

        """
        return json

    def get_schema(self):
        """
        Loads schema file if schema is not defined on the subclass.
        Otherwise, returns the overridden schema from the subclass (example)
        """
        if self.schema is None:
            return self.load_schema()
        return self.schema

    def load_schema(self):
        """
        Loads the schema from file with defined deserialization module.
        """
        return self.get_serializer().load(API_PLAYGROUND_SCHEMA_PATH)

    def browser_index(self, request):
        """
        A view that returns api browser index.
        """
        self.build_full_description()
        return render_to_response(self.index_template, {
            "schema": self.get_schema(),
            "feedback_form_toggle": API_PLAYGROUND_FEEDBACK,
            "feedback_form": self.get_feedback_form(request)
        }, context_instance=RequestContext(request))

    def save_feedback_form(self, request, form):
        """
        Saves feedback data.
        """
        form.save()

    def get_feedback_form(self, request):
        """
        Instantiates feedback form from request.
        """
        return self.feedback_form(request.POST or None)

    def submit_feedback(self, request):
        """
        A view that saves feedback form.
        Returns JSON response.
        """
        form = self.get_feedback_form(request)
        if form.is_valid():
            self.save_feedback_form(request, form)
        if form.errors:
            return self.create_json_response({
                "errors": form.errors
            }, response_class=HttpResponseBadRequest)
        return self.create_json_response({
            "success": True
        })

    def create_json_response(self, data, response_class=HttpResponse):
        """
        A utility method for creating json responses.
        """
        return response_class(json.dumps(data))

    def get_urls(self):
        """
        Returns API Browser URLs.
        You can override method for adding extra views.
        """
        return [
            url("^$", self.browser_index, name="api_playground_index"),
            url("^submit-feedback$", self.submit_feedback, name="api_playground_submit_feedback"),
        ]

    def build_full_description(self):
        schema = self.get_schema()
        for resource in schema['resources']:
            for endpoint in resource.get('endpoints', []):
                if endpoint.get('full_description', ""):
                    endpoint['full_description'] = markdown.markdown(
                        endpoint['full_description'].strip())

    @property
    def urls(self):
        """
        A shortcut property for reaching the urls.
        """
        return self.get_urls()

########NEW FILE########
__FILENAME__ = settings
from django.conf import settings

API_PLAYGROUND_SCHEMA_PATH = getattr(settings,
    "API_PLAYGROUND_SCHEMA_PATH", "api_playground_schema.json")

# Toggle the feedback form
API_PLAYGROUND_FEEDBACK = getattr(settings,
    "API_PLAYGROUND_FEEDBACK", True)

########NEW FILE########
__FILENAME__ = api_browser_tags
from django import template
from apiplayground.forms import build_url_form, build_data_form

register = template.Library()


@register.assignment_tag()
def get_global_forms(schema):
    data_parameter_form = build_data_form(schema.get("parameters", []))

    return {
        "data_parameter_form": data_parameter_form
    }


@register.assignment_tag()
def get_endpoint_forms(endpoint):
    url_parameter_form = build_url_form(endpoint.get("url", ""))
    data_parameter_form = build_data_form(endpoint.get("parameters", []))

    return {
        "url_parameter_form": url_parameter_form,
        "data_parameter_form": data_parameter_form
    }


@register.filter()
def render_url(url):
    """
    Removes GET parameters from URL.
    """
    return url.split("?")[0]
########NEW FILE########
__FILENAME__ = utils
import re

def tokenize_url_parameters(url):
    """
    A function that tokenize parameters from the provided url.

    >>> tokenize_url_parameters("/test/{object_id}")
    [('{object_id}', 'object_id')]

    >>> tokenize_url_parameters("/tests/")
    []
    """
    pattern = re.compile("(\{([a-z-_]+)\})")
    return pattern.findall(url) or []
########NEW FILE########
__FILENAME__ = playgrounds
from apiplayground import APIPlayground

class ExampleAPIPlayground(APIPlayground):

    schema = {
        "title": "API Playground",
        "base_url": "http://localhost/api/",
        "resources": [
            {
                "name": "/todos",
                "description": "This resource allows you to manage todo items.",
                "endpoints": [
                    {
                        "method": "GET",
                        "url": "/api/todos/",
                        "description": "Returns all to-do items",
                        "parameters": [{
                            "name": "order_by",
                            "type": "select",
                            "choices": [["", "None"], ["id", "id"], ["-id", "-id"]],
                            "default": "id"
                        }]
                    },
                    {
                        "method": "GET",
                        "url": "/api/todos/{todo-id}",
                        "description": "Returns specific todo item."
                    },
                    {
                        "method": "POST",
                        "url": "/api/todos/",
                        "description": "Creates new to-do item",
                        "parameters": [{
                            "name": "description",
                            "type": "string",
                            "is_required": True
                        }, {
                            "name": "is_completed",
                            "type": "boolean"
                        }]
                    },
                    {
                        "method": "PUT",
                        "url": "/api/todos/{todo-id}",
                        "description": "Replaces specific todo item",
                        "parameters": [{
                            "name": "description",
                            "type": "string",
                            "is_required": True,
                            "description": "the to-do item"
                            }, {
                            "name": "is_completed",
                            "type": "boolean",
                            "description": "status of to-do item"
                       }]
                    },
                    {
                        "method": "PATCH",
                        "url": "/api/todos/{todo-id}",
                        "description": "Updates specific todo items",
                        "parameters": [{
                                           "name": "is_completed",
                                           "type": "boolean",
                                           "description": "status of to-do item"
                                       }]
                    },
                    {
                        "method": "DELETE",
                        "url": "/api/todos/",
                        "description": "Removes all to-do items"
                    },
                    {
                        "method": "DELETE",
                        "url": "/api/todos/{todo-id}",
                        "description": "Removes specific to-do item"
                    },
                ]
            },
            {
                "name": "/feedbacks",
                "description": "This resource allows you to manage feedbacks.",
                "endpoints": [
                    {
                        "method": "GET",
                        "url": "/api/feedbacks/",
                        "description": "Returns all feedback items"
                    },
                    {
                        "method": "POST",
                        "url": "/api/feedbacks/",
                        "description": "Creates new feedback item",
                        "parameters": [{
                            "name": "title",
                            "type": "string"
                        },
                        {
                            "name": "resource",
                            "type": "string"
                        },
                        {
                           "name": "description",
                           "type": "string"
                        }]
                    }
                ]
            }
        ]
    }

########NEW FILE########
__FILENAME__ = resources
from tastypie.authorization import Authorization
from tastypie.resources import ModelResource

from api.serializers import PrettyJSONSerializer
from apiplayground.models import Feedback


class FeedbackResource(ModelResource):

    class Meta:
        resource_name = "feedbacks"
        queryset = Feedback.objects.all()
        authorization = Authorization()
        serializer = PrettyJSONSerializer()
        always_return_data = True

########NEW FILE########
__FILENAME__ = serializers
from django.core.serializers import json
from django.utils import simplejson

from tastypie.serializers import Serializer

class PrettyJSONSerializer(Serializer):
    json_indent = 2

    def to_json(self, data, options=None):
        options = options or {}
        data = self.to_simple(data, options)
        return simplejson.dumps(data, cls=json.DjangoJSONEncoder,
            sort_keys=True, ensure_ascii=False, indent=self.json_indent)
########NEW FILE########
__FILENAME__ = urls
from django.conf.urls import include, patterns

from todos.resources import ToDoResource
from api.resources import FeedbackResource


urlpatterns = patterns('',

    (r'^', include(FeedbackResource().urls)),
    (r'^', include(ToDoResource().urls)),

)
########NEW FILE########
__FILENAME__ = settings
# Django settings for example project.

DEBUG = True
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    # ('Your Name', 'your_email@example.com'),
)

MANAGERS = ADMINS

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3', # Add 'postgresql_psycopg2', 'mysql', 'sqlite3' or 'oracle'.
        'NAME': './test.db',                      # Or path to database file if using sqlite3.
        'USER': '',                      # Not used with sqlite3.
        'PASSWORD': '',                  # Not used with sqlite3.
        'HOST': '',                      # Set to empty string for localhost. Not used with sqlite3.
        'PORT': '',                      # Set to empty string for default. Not used with sqlite3.
    }
}



# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# In a Windows environment this must be set to your system time zone.
TIME_ZONE = 'America/Chicago'

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
USE_TZ = True

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

ROOT_URLCONF = 'example.urls'

# Python dotted path to the WSGI application used by Django's runserver.
WSGI_APPLICATION = 'example.wsgi.application'

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
    # 'django.contrib.admin',
    # Uncomment the next line to enable admin documentation:
    # 'django.contrib.admindocs',

    'apiplayground',
    'todos',

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

try:
    from settings_local import *
except ImportError:
    pass

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls import patterns, include, url

from api.playgrounds import ExampleAPIPlayground


urlpatterns = patterns('',

    (r'^api/', include("api.urls")),

    # api playground
    (r'^', include(ExampleAPIPlayground().urls)),

)

########NEW FILE########
__FILENAME__ = wsgi
"""
WSGI config for example project.

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

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "example.settings")

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

    sys.path.append("../")

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "example.settings")

    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)

########NEW FILE########
__FILENAME__ = models
from django.db import models
from django.utils.encoding import smart_unicode

class ToDo(models.Model):
    """
    Holds To-do data
    """
    description = models.CharField(max_length=255)
    is_completed = models.BooleanField()

    def __unicode__(self):
        return smart_unicode(self.description)
########NEW FILE########
__FILENAME__ = resources
from tastypie.authorization import Authorization
from tastypie.resources import ModelResource

from api.serializers import PrettyJSONSerializer
from todos.models import ToDo


class ToDoResource(ModelResource):

    class Meta:
        resource_name = "todos"
        queryset = ToDo.objects.all()
        authorization = Authorization()
        serializer = PrettyJSONSerializer()
        always_return_data = True
        ordering = ["id"]

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
