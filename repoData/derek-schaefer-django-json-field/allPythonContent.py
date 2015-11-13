__FILENAME__ = fields
from __future__ import unicode_literals

from json_field.utils import is_aware
from json_field.forms import JSONFormField

try:
    import json
except ImportError:  # python < 2.6
    from django.utils import simplejson as json

from django.db import models
from django.core import exceptions
from django.utils.translation import ugettext_lazy as _
from django.core.exceptions import ImproperlyConfigured

import re
import decimal
import datetime
import six
try:
    from dateutil import parser as date_parser
except ImportError:
    raise ImproperlyConfigured('The "dateutil" library is required and was not found.')

try:
    JSON_DECODE_ERROR = json.JSONDecodeError # simplejson
except AttributeError:
    JSON_DECODE_ERROR = ValueError # other

TIME_RE = re.compile(r'^\d{2}:\d{2}:\d{2}')
DATE_RE = re.compile(r'^\d{4}-\d{2}-\d{2}(?!T)')
DATETIME_RE = re.compile(r'^\d{4}-\d{2}-\d{2}T')

class JSONEncoder(json.JSONEncoder):
    """
    JSONEncoder subclass that knows how to encode date/time and decimal types.
    """
    def default(self, o):
        # See "Date Time String Format" in the ECMA-262 specification.
        if isinstance(o, datetime.datetime):
            r = o.isoformat()
            if o.microsecond:
                r = r[:23] + r[26:]
            if r.endswith('+00:00'):
                r = r[:-6] + 'Z'
            return r
        elif isinstance(o, datetime.date):
            return o.isoformat()
        elif isinstance(o, datetime.time):
            if is_aware(o):
                raise ValueError("JSON can't represent timezone-aware times.")
            r = o.isoformat()
            if o.microsecond:
                r = r[:12]
            return r
        elif isinstance(o, decimal.Decimal):
            return str(o)
        else:
            return super(JSONEncoder, self).default(o)

class JSONDecoder(json.JSONDecoder):
    """ Recursive JSON to Python deserialization. """

    _recursable_types = ([str] if six.PY3 else [str, unicode]) + [list, dict]

    def _is_recursive(self, obj):
        return type(obj) in JSONDecoder._recursable_types

    def decode(self, obj, *args, **kwargs):
        if not kwargs.get('recurse', False):
            obj = super(JSONDecoder, self).decode(obj, *args, **kwargs)
        if isinstance(obj, list):
            for i in six.moves.xrange(len(obj)):
                item = obj[i]
                if self._is_recursive(item):
                    obj[i] = self.decode(item, recurse=True)
        elif isinstance(obj, dict):
            for key, value in obj.items():
                if self._is_recursive(value):
                    obj[key] = self.decode(value, recurse=True)
        elif isinstance(obj, six.string_types):
            if TIME_RE.match(obj):
                try:
                    return date_parser.parse(obj).time()
                except ValueError:
                    pass
            if DATE_RE.match(obj):
                try:
                    return date_parser.parse(obj).date()
                except ValueError:
                    pass
            if DATETIME_RE.match(obj):
                try:
                    return date_parser.parse(obj)
                except ValueError:
                    pass
        return obj

class Creator(object):
    """
    Taken from django.db.models.fields.subclassing.
    """

    _state_key = '_json_field_state'

    def __init__(self, field, lazy):
        self.field = field
        self.lazy = lazy

    def __get__(self, obj, type=None):
        if obj is None:
            return self

        if self.lazy:
            state = getattr(obj, self._state_key, None)
            if state is None:
                state = {}
                setattr(obj, self._state_key, state)

            if state.get(self.field.name, False):
                return obj.__dict__[self.field.name]

            value = self.field.to_python(obj.__dict__[self.field.name])
            obj.__dict__[self.field.name] = value
            state[self.field.name] = True
        else:
            value = obj.__dict__[self.field.name]

        return value

    def __set__(self, obj, value):
        obj.__dict__[self.field.name] = value if self.lazy else self.field.to_python(value)

class JSONField(models.TextField):
    """ Stores and loads valid JSON objects. """

    description = 'JSON object'

    def __init__(self, *args, **kwargs):
        self.default_error_messages = {
            'invalid': _('Enter a valid JSON object')
        }
        self._db_type = kwargs.pop('db_type', None)
        self.evaluate_formfield = kwargs.pop('evaluate_formfield', False)

        self.lazy = kwargs.pop('lazy', True)
        encoder = kwargs.pop('encoder', JSONEncoder)
        decoder = kwargs.pop('decoder', JSONDecoder)
        encoder_kwargs = kwargs.pop('encoder_kwargs', {})
        decoder_kwargs = kwargs.pop('decoder_kwargs', {})
        if not encoder_kwargs and encoder:
            encoder_kwargs.update({'cls':encoder})
        if not decoder_kwargs and decoder:
            decoder_kwargs.update({'cls':decoder, 'parse_float':decimal.Decimal})
        self.encoder_kwargs = encoder_kwargs
        self.decoder_kwargs = decoder_kwargs

        kwargs['default'] = kwargs.get('default', 'null')
        kwargs['help_text'] = kwargs.get('help_text', self.default_error_messages['invalid'])

        super(JSONField, self).__init__(*args, **kwargs)

    def db_type(self, *args, **kwargs):
        if self._db_type:
            return self._db_type
        return super(JSONField, self).db_type(*args, **kwargs)

    def to_python(self, value):
        if value is None: # allow blank objects
            return None
        if isinstance(value, six.string_types):
            try:
                value = json.loads(value, **self.decoder_kwargs)
            except JSON_DECODE_ERROR:
                pass
        return value

    def get_db_prep_value(self, value, *args, **kwargs):
        if self.null and value is None and not kwargs.get('force'):
            return None
        return json.dumps(value, **self.encoder_kwargs)

    def value_to_string(self, obj):
        return self.get_db_prep_value(self._get_val_from_obj(obj))

    def value_from_object(self, obj):
        return json.dumps(super(JSONField, self).value_from_object(obj), **self.encoder_kwargs)

    def formfield(self, **kwargs):
        defaults = {
            'form_class': kwargs.get('form_class', JSONFormField),
            'evaluate': self.evaluate_formfield,
            'encoder_kwargs': self.encoder_kwargs,
            'decoder_kwargs': self.decoder_kwargs,
        }
        defaults.update(kwargs)
        return super(JSONField, self).formfield(**defaults)

    def contribute_to_class(self, cls, name):
        super(JSONField, self).contribute_to_class(cls, name)

        def get_json(model_instance):
            return self.get_db_prep_value(getattr(model_instance, self.attname, None), force=True)
        setattr(cls, 'get_%s_json' % self.name, get_json)

        def set_json(model_instance, value):
            return setattr(model_instance, self.attname, self.to_python(value))
        setattr(cls, 'set_%s_json' % self.name, set_json)

        setattr(cls, name, Creator(self, lazy=self.lazy)) # deferred deserialization

try:
    # add support for South migrations
    from south.modelsinspector import add_introspection_rules
    rules = [
        (
            (JSONField,),
            [],
            {
                'db_type': ['_db_type', {'default': None}]
            }
        )
    ]
    add_introspection_rules(rules, ['^json_field\.fields\.JSONField'])
except ImportError:
    pass

########NEW FILE########
__FILENAME__ = forms
try:
    import json
except ImportError:  # python < 2.6
    from django.utils import simplejson as json
from django.forms import fields, util

import datetime
from decimal import Decimal

class JSONFormField(fields.Field):

    def __init__(self, *args, **kwargs):
        from .fields import JSONEncoder, JSONDecoder
        self.evaluate = kwargs.pop('evaluate', False)
        self.encoder_kwargs = kwargs.pop('encoder_kwargs', {'cls':JSONEncoder})
        self.decoder_kwargs = kwargs.pop('decoder_kwargs', {'cls':JSONDecoder, 'parse_float':Decimal})
        super(JSONFormField, self).__init__(*args, **kwargs)

    def clean(self, value):
        # Have to jump through a few hoops to make this reliable
        value = super(JSONFormField, self).clean(value)

        # allow an empty value on an optional field
        if value is None:
            return value

        ## Got to get rid of newlines for validation to work
        # Data newlines are escaped so this is safe
        value = value.replace('\r', '').replace('\n', '')

        if self.evaluate:
            json_globals = { # "safety" first!
                '__builtins__': None,
                'datetime': datetime,
            }
            json_locals = { # value compatibility
                'null': None,
                'true': True,
                'false': False,
            }
            try:
                value = json.dumps(eval(value, json_globals, json_locals), **self.encoder_kwargs)
            except Exception as e: # eval can throw many different errors
                raise util.ValidationError(str(e))

        try:
            return json.loads(value, **self.decoder_kwargs)
        except ValueError as e:
            raise util.ValidationError(str(e))

########NEW FILE########
__FILENAME__ = models

########NEW FILE########
__FILENAME__ = tests

########NEW FILE########
__FILENAME__ = utils
def is_aware(value): # taken from django/utils/timezone.py
    """
    Determines if a given datetime.datetime is aware.

    The logic is described in Python's docs:
    http://docs.python.org/library/datetime.html#datetime.tzinfo
    """
    return value.tzinfo is not None and value.tzinfo.utcoffset(value) is not None

########NEW FILE########
__FILENAME__ = views

########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python
import os
import sys

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "test_project.settings")

    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)

########NEW FILE########
__FILENAME__ = admin
from django.contrib import admin

from test_project.app.models import Test
admin.site.register(Test)

########NEW FILE########
__FILENAME__ = forms
from __future__ import unicode_literals

from .models import Test

from django import forms
from json_field.forms import JSONFormField

class ModelForm(forms.ModelForm):
    class Meta:
        model = Test

class TestForm(forms.Form):
    json = JSONFormField()

class OptionalForm(forms.Form):
    json = JSONFormField(required=False)

class EvalForm(forms.Form):
    json = JSONFormField(evaluate=True)

########NEW FILE########
__FILENAME__ = models
from json_field import JSONField

from django.db import models

class Test(models.Model):

    json = JSONField()
    json_eager = JSONField(lazy=False)
    json_null = JSONField(blank=True, null=True, evaluate_formfield=True)

########NEW FILE########
__FILENAME__ = tests
from __future__ import unicode_literals, division

import inspect

from json_field.fields import JSON_DECODE_ERROR

from test_project.app.models import Test
from test_project.app.forms import TestForm, OptionalForm, \
    EvalForm, ModelForm

from django.test import TestCase
from django.db.utils import IntegrityError
from django.utils import simplejson as json

import datetime
from decimal import Decimal

try:
    from django.utils import unittest
except ImportError:
    import unittest

class JSONFieldTest(TestCase):

    def test_simple(self):
        t1 = Test.objects.create(json=123)
        self.assertEqual(123, Test.objects.get(pk=t1.pk).json)
        t2 = Test.objects.create(json='123')
        self.assertEqual(123, Test.objects.get(pk=t2.pk).json)
        t3 = Test.objects.create(json=[123])
        self.assertEqual([123], Test.objects.get(pk=t3.pk).json)
        t4 = Test.objects.create(json='[123]')
        self.assertEqual([123], Test.objects.get(pk=t4.pk).json)
        t5 = Test.objects.create(json={'test':[1,2,3]})
        self.assertEqual({'test':[1,2,3]}, Test.objects.get(pk=t5.pk).json)
        t6 = Test.objects.create(json='{"test":[1,2,3]}')
        self.assertEqual({'test':[1,2,3]}, Test.objects.get(pk=t6.pk).json)
        t7 = Test.objects.create(json=[1,2,3])
        t7.json = {'asdf':123}
        self.assertEqual({'asdf':123}, t7.json)
        t8 = Test.objects.get(pk=t7.pk)
        t8.json = {'asdf':123}
        self.assertEqual({'asdf':123}, t8.json)

    def test_eager(self):
        t1 = Test.objects.create(json_eager=123)
        self.assertEqual(123, Test.objects.get(pk=t1.pk).json_eager)
        t2 = Test.objects.create(json_eager='123')
        self.assertEqual(123, Test.objects.get(pk=t2.pk).json_eager)
        t3 = Test.objects.create(json_eager=[123])
        self.assertEqual([123], Test.objects.get(pk=t3.pk).json_eager)
        t4 = Test.objects.create(json_eager='[123]')
        self.assertEqual([123], Test.objects.get(pk=t4.pk).json_eager)
        t5 = Test.objects.create(json_eager={'test':[1,2,3]})
        self.assertEqual({'test':[1,2,3]}, Test.objects.get(pk=t5.pk).json_eager)
        t6 = Test.objects.create(json_eager='{"test":[1,2,3]}')
        self.assertEqual({'test':[1,2,3]}, Test.objects.get(pk=t6.pk).json_eager)
        t7 = Test.objects.create(json_eager=[1,2,3])
        t7.json_eager = {'asdf':123}
        self.assertEqual({'asdf':123}, t7.json_eager)
        t8 = Test.objects.get(pk=t7.pk)
        t8.json_eager = {'asdf':123}
        self.assertEqual({'asdf':123}, t8.json_eager)

    def test_null(self):
        t1 = Test.objects.create(json=None)
        self.assertEqual(None, t1.json)
        self.assertEqual('null', t1.get_json_json())
        t2 = Test.objects.create(json='')
        self.assertEqual('', t2.json)
        self.assertEqual('""', t2.get_json_json())
        t3 = Test.objects.create(json_null=None)
        self.assertEqual(None, t3.json_null)
        self.assertEqual('null', t3.get_json_null_json())
        t4 = Test.objects.create(json_null='')
        self.assertEqual('', t4.json_null)
        self.assertEqual('""', t4.get_json_null_json())

    def test_decimal(self):
        t1 = Test.objects.create(json=1.24)
        self.assertEqual(Decimal('1.24'), Test.objects.get(pk=t1.pk).json)
        t2 = Test.objects.create(json=Decimal(1.24))
        self.assertEqual(str(Decimal(1.24)), Test.objects.get(pk=t2.pk).json)
        t3 = Test.objects.create(json={'test':[{'test':Decimal(1.24)}]})
        self.assertEqual({'test':[{'test':str(Decimal(1.24))}]}, Test.objects.get(pk=t3.pk).json)

    def test_time(self):
        now = datetime.datetime.now().time()
        t1 = Test.objects.create(json=now)
        # JSON does not have microsecond precision, round to millisecond
        now_rounded = now.replace(microsecond=(int(now.microsecond) // 1000) * 1000)
        self.assertEqual(now_rounded, Test.objects.get(pk=t1.pk).json)
        t2 = Test.objects.create(json={'time':[now]})
        self.assertEqual({'time':[now_rounded]}, Test.objects.get(pk=t2.pk).json)

    def test_date(self):
        today = datetime.date.today()
        t1 = Test.objects.create(json=today)
        self.assertEqual(today, Test.objects.get(pk=t1.pk).json)
        t2 = Test.objects.create(json={'today':today})
        self.assertEqual({'today':today}, Test.objects.get(pk=t2.pk).json)

    def test_datetime(self):
        now = datetime.datetime.now()
        t1 = Test.objects.create(json=now)
        # JSON does not have microsecond precision, round to millisecond
        now_rounded = now.replace(microsecond=(int(now.microsecond) // 1000) * 1000)
        self.assertEqual(now_rounded, Test.objects.get(pk=t1.pk).json)
        t2 = Test.objects.create(json={'test':[{'test':now}]})
        self.assertEqual({'test':[{'test':now_rounded}]}, Test.objects.get(pk=t2.pk).json)

    def test_numerical_strings(self):
        t1 = Test.objects.create(json='"555"')
        self.assertEqual('555', Test.objects.get(pk=t1.pk).json)
        t2 = Test.objects.create(json='"123.98712634789162349781264"')
        self.assertEqual('123.98712634789162349781264', Test.objects.get(pk=t2.pk).json)

    def test_get_set_json(self):
        t1 = Test.objects.create(json={'test':123})
        self.assertEqual({'test':123}, t1.json)
        self.assertEqual('{"test": 123}', t1.get_json_json())
        t2 = Test.objects.create(json='')
        self.assertEqual('', t2.json)
        self.assertEqual('""', t2.get_json_json())
        self.assertEqual(None, t2.json_null)
        self.assertEqual('null', t2.get_json_null_json())
        t3 = Test.objects.create(json=[1,2,3])
        self.assertEqual([1,2,3], t3.json)
        self.assertEqual('[1, 2, 3]', t3.get_json_json())
        t3.set_json_json('[1, 2, 3, 4, 5]')
        self.assertEqual([1, 2, 3, 4, 5], t3.json)
        self.assertEqual('[1, 2, 3, 4, 5]', t3.get_json_json())
        t3.set_json_json(123)
        self.assertEqual(123, t3.json)
        self.assertEqual('123', t3.get_json_json())

    def test_strings(self):
        t1 = Test.objects.create(json='a')
        self.assertEqual('a', t1.json)
        self.assertEqual('"a"', t1.get_json_json())
        t2 = Test.objects.create(json='"a"')
        self.assertEqual('a', t2.json)
        self.assertEqual('"a"', t2.get_json_json())
        t3 = Test.objects.create(json_null='a')
        self.assertEqual('a', t3.json_null)
        self.assertEqual('"a"', t3.get_json_null_json())
        t4 = Test.objects.create(json='"a')
        self.assertEqual('"a', t4.json)
        self.assertEqual('"\\"a"', t4.get_json_json())

    def test_formfield(self):
        data = {'json': '{"asdf":42}'}
        f1 = TestForm(data)
        self.assertTrue(f1.is_valid())
        self.assertEqual(f1.cleaned_data, {'json': {'asdf':42}})
        f2 = TestForm({})
        self.assertFalse(f2.is_valid())
        f3 = OptionalForm({})
        self.assertTrue(f3.is_valid())
        self.assertEqual(f3.cleaned_data, {'json': None})
        f4 = TestForm({'json':'{"time": datetime.datetime.now()}'})
        self.assertFalse(f4.is_valid())
        f5 = EvalForm({'json':'{"time": datetime.datetime.now()}'})
        self.assertTrue(f5.is_valid())
        f6 = ModelForm({'json':'{"time": datetime.datetime.now()}'})
        self.assertFalse(f6.is_valid())
        f7 = ModelForm({'json':'{"time": datetime.datetime.now()}'})
        self.assertFalse(f7.is_valid())

    def test_creator_plays_nice_with_module_inspect(self):
        """
        From upstream, based on:
        https://code.djangoproject.com/ticket/12568
        and corresponding patch:
        https://code.djangoproject.com/changeset/50633e7353694ff54f14b04469be3792f286182f


        Custom fields should play nice with python standard module inspect.

        http://users.rcn.com/python/download/Descriptor.htm#properties
        """
        # The custom Creator's non property like behaviour made the properties
        # invisible for inspection.
        data = dict(inspect.getmembers(Test))
        self.assertIn('json', data)

########NEW FILE########
__FILENAME__ = views
# Create your views here.

########NEW FILE########
__FILENAME__ = settings
# Django settings for test_project project.

DEBUG = True
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    # ('Your Name', 'your_email@example.com'),
)

MANAGERS = ADMINS

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': 'test.db',
        'USER': '',
        'PASSWORD': '',
        'HOST': '',
        'PORT': '',
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

# Make this unique, and don't share it with anybody.
SECRET_KEY = 'gnf&amp;#+&amp;u0^00fs*vmxr_e#t9!rkoa3t8gm=b@j##z=1_bu*6&amp;5'

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

ROOT_URLCONF = 'test_project.urls'

# Python dotted path to the WSGI application used by Django's runserver.
WSGI_APPLICATION = 'test_project.wsgi.application'

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
    'django.contrib.admin',
    'django.contrib.admindocs',
    'json_field',
    'test_project.app',
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
from django.conf.urls import patterns, include, url

from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
    url(r'^admin/doc/', include('django.contrib.admindocs.urls')),
    url(r'^admin/', include(admin.site.urls)),
)

########NEW FILE########
__FILENAME__ = wsgi
"""
WSGI config for test_project project.

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

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "test_project.settings")

# This application object is used by any WSGI server configured to use this
# file. This includes Django's development server, if the WSGI_APPLICATION
# setting points here.
from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()

# Apply WSGI middleware here.
# from helloworld.wsgi import HelloWorldApplication
# application = HelloWorldApplication(application)

########NEW FILE########
