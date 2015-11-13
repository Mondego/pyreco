__FILENAME__ = actions
from django.http import HttpResponse
from django.utils.encoding import smart_str
from django.utils.translation import ugettext as _

from django_tablib.datasets import SimpleDataset
from django_tablib.base import mimetype_map


def tablib_export_action(modeladmin, request, queryset, format="xls"):
    """
    Allow the user to download the current filtered list of items

    :param format:
        One of the formats supported by tablib (e.g. "xls", "csv", "html",
        etc.)
    """

    dataset = SimpleDataset(queryset, headers=None)
    filename = '%s.%s' % (
        smart_str(modeladmin.model._meta.verbose_name_plural), format)
    response = HttpResponse(
        getattr(dataset, format), mimetype=mimetype_map.get(
            format, 'application/octet-stream'))
    response['Content-Disposition'] = 'attachment; filename=%s' % filename
    return response


def xls_export_action(*args, **kwargs):
    return tablib_export_action(format="xls", *args, **kwargs)
xls_export_action.__doc__ = tablib_export_action.__doc__
xls_export_action.short_description = _("Export to Excel")


def csv_export_action(*args, **kwargs):
    return tablib_export_action(format="csv", *args, **kwargs)
csv_export_action.__doc__ = tablib_export_action.__doc__
csv_export_action.short_description = _("Export to CSV")

########NEW FILE########
__FILENAME__ = base
import datetime
import tablib

from django.template.defaultfilters import date
from django.utils.encoding import smart_unicode
from django.utils.translation import ugettext_lazy as _

mimetype_map = {
    'xls': 'application/vnd.ms-excel',
    'csv': 'text/csv',
    'html': 'text/html',
    'yaml': 'text/yaml',
    'json': 'application/json',
}


class BaseDataset(tablib.Dataset):

    encoding = 'utf-8'

    def __init__(self):
        data = map(self._getattrs, self.queryset)
        super(BaseDataset, self).__init__(headers=self.header_list, *data)

    def _cleanval(self, value, attr):
        if callable(value):
            value = value()
        elif value is None or unicode(value) == u"None":
            value = ""

        t = type(value)
        if t is str:
            return value
        elif t is bool:
            value = _("Y") if value else _("N")
            return smart_unicode(value).encode(self.encoding)
        elif t in [datetime.date, datetime.datetime]:
            return date(value, 'SHORT_DATE_FORMAT').encode(self.encoding)

        return smart_unicode(value).encode(self.encoding)

    def _getattrs(self, obj):
        attrs = []
        for attr in self.attr_list:
            if callable(attr):
                attr = self._cleanval(attr(obj), attr)
            else:
                if hasattr(obj, 'get_%s_display' % attr):
                    value = getattr(obj, 'get_%s_display' % attr)()
                else:
                    value = getattr(obj, attr)
                attr = self._cleanval(value, attr)
            attrs.append(attr)
        return attrs

    def append(self, *args, **kwargs):
        # Thanks to my previous decision to simply not support columns, this
        # dumb conditional is necessary to preserve backwards compatibility.
        if len(args) == 1:
            # if using old syntax, just set django_object to args[0] and
            # col to None
            django_object = args[0]
            col = None
        else:
            # otherwise assume both row and col may have been passed and
            # handle appropriately
            django_object = kwargs.get('row', None)
            col = kwargs.get('col', None)

        # make sure that both row and col are in a format that can be passed
        # straight to tablib
        if django_object is not None:
            row = self._getattrs(django_object)
        else:
            row = django_object

        super(BaseDataset, self).append(row=row, col=col)

########NEW FILE########
__FILENAME__ = datasets
from __future__ import absolute_import

from .base import BaseDataset


class SimpleDataset(BaseDataset):
    def __init__(self, queryset, headers=None, encoding='utf-8'):
        self.queryset = queryset
        self.encoding = encoding
        if headers is None:
            # We'll set the queryset to include all fields including calculated
            # aggregates using the same names as a values() queryset:
            v_qs = queryset.values()
            headers = []
            headers.extend(v_qs.query.extra_select)
            headers.extend(v_qs.field_names)
            headers.extend(v_qs.query.aggregate_select)

            self.header_list = headers
            self.attr_list = headers
        elif isinstance(headers, dict):
            self.header_dict = headers
            self.header_list = self.header_dict.keys()
            self.attr_list = self.header_dict.values()
        elif isinstance(headers, (tuple, list)):
            self.header_list = headers
            self.attr_list = headers
        super(SimpleDataset, self).__init__()

########NEW FILE########
__FILENAME__ = fields
class Field(object):
    def __init__(self, attribute=None, header=None):
        self.attribute = attribute
        self.header = header

########NEW FILE########
__FILENAME__ = models
from __future__ import absolute_import
from copy import deepcopy

from .base import BaseDataset
from .fields import Field


class NoObjectsException(Exception):
    pass


class DatasetOptions(object):
    def __init__(self, options=None):
        self.model = getattr(options, 'model', None)
        self.queryset = getattr(options, 'queryset', None)
        self.fields = getattr(options, 'fields', [])
        self.exclude = getattr(options, 'exclude', [])


class DatasetMetaclass(type):
    def __new__(cls, name, bases, attrs):
        attrs['base_fields'] = {}
        declared_fields = {}

        try:
            parents = [b for b in bases if issubclass(b, ModelDataset)]
            parents.reverse()

            for p in parents:
                parent_fields = getattr(p, 'base_fields', {})

                for field_name, field_object in parent_fields.items():
                    attrs['base_fields'][field_name] = deepcopy(field_object)
        except NameError:
            pass

        for field_name, obj in attrs.copy().items():
            if issubclass(type(obj), Field):
                field = attrs.pop(field_name)
                declared_fields[field_name] = field

        attrs['base_fields'].update(declared_fields)
        attrs['declared_fields'] = declared_fields

        new_class = super(DatasetMetaclass, cls).__new__(cls, name,
                                                         bases, attrs)
        opts = new_class._meta = DatasetOptions(getattr(new_class,
                                                        'Meta', None))

        if new_class.__name__ == 'ModelDataset':
            return new_class

        if not opts.model and not opts.queryset:
            raise NoObjectsException("You must set a model or non-empty "
                                     "queryset for each Dataset subclass")
        if opts.queryset is not None:
            queryset = opts.queryset
            model = queryset.model
            new_class.queryset = queryset
            new_class.model = model
        else:
            model = opts.model
            queryset = model.objects.all()
            new_class.model = model
            new_class.queryset = queryset

        return new_class


class ModelDataset(BaseDataset):
    __metaclass__ = DatasetMetaclass

    def __init__(self, *args, **kwargs):
        included = [field.name for field in self.model._meta.fields]
        if self._meta.fields:
            included = filter(lambda x: x in self._meta.fields, included)
        if self._meta.exclude:
            included = filter(lambda x: x not in self._meta.exclude, included)

        self.fields = {field: Field() for field in included}
        self.fields.update(deepcopy(self.base_fields))

        fields = [
            field.attribute or name for name, field in self.fields.items()
        ]
        header_dict = {
            field.header or name: field.attribute or name
            for name, field in self.fields.items()
        }
        header_list = header_dict.keys()

        self.attr_list = fields
        self.header_dict = header_dict
        self.header_list = header_list
        super(ModelDataset, self).__init__(*args, **kwargs)

########NEW FILE########
__FILENAME__ = views
from __future__ import absolute_import

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.http import Http404, HttpResponse, HttpResponseBadRequest
from django.db.models.loading import get_model

from .base import mimetype_map
from .datasets import SimpleDataset


def export(request, queryset=None, model=None, headers=None, format='xls',
           filename='export'):
    if queryset is None:
        queryset = model.objects.all()

    dataset = SimpleDataset(queryset, headers=headers)
    filename = '%s.%s' % (filename, format)
    if not hasattr(dataset, format):
        raise Http404
    response = HttpResponse(
        getattr(dataset, format),
        mimetype=mimetype_map.get(format, 'application/octet-stream')
    )
    response['Content-Disposition'] = 'attachment; filename=%s' % filename
    return response


def generic_export(request, model_name=None):
    """
    Generic view configured through settings.TABLIB_MODELS

    Usage:
        1. Add the view to ``urlpatterns`` in ``urls.py``::
            url(r'export/(?P<model_name>[^/]+)/$', "django_tablib.views.generic_export"),
        2. Create the ``settings.TABLIB_MODELS`` dictionary using model names
           as keys the allowed lookup operators as values, if any::

           TABLIB_MODELS = {
               'myapp.simple': None,
               'myapp.related': {'simple__title': ('exact', 'iexact')},
           }
        3. Open ``/export/myapp.simple`` or
           ``/export/myapp.related/?simple__title__iexact=test``
    """

    if model_name not in settings.TABLIB_MODELS:
        raise Http404()

    model = get_model(*model_name.split(".", 2))
    if not model:
        raise ImproperlyConfigured(
            "Model %s is in settings.TABLIB_MODELS but"
            " could not be loaded" % model_name)

    qs = model._default_manager.all()

    # Filtering may be allowed based on TABLIB_MODELS:
    filter_settings = settings.TABLIB_MODELS[model_name]
    filters = {}

    for k, v in request.GET.items():
        try:
            # Allow joins (they'll be checked below) but chop off the trailing
            # lookup operator:
            rel, lookup_type = k.rsplit("__", 1)
        except ValueError:
            rel = k
            lookup_type = "exact"

        allowed_lookups = filter_settings.get(rel, None)

        if allowed_lookups is None:
            return HttpResponseBadRequest(
                "Filtering on %s is not allowed" % rel
            )
        elif lookup_type not in allowed_lookups:
            return HttpResponseBadRequest(
                "%s may only be filtered using %s"
                % (k, " ".join(allowed_lookups)))
        else:
            filters[str(k)] = v

    if filters:
        qs = qs.filter(**filters)

    return export(request, model=model, queryset=qs)

########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python
import os
import sys

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "testproject.settings")

    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)

########NEW FILE########
__FILENAME__ = admin
from django.contrib import admin

from django_tablib import TablibAdmin
from django_tablib.admin.actions import xls_export_action, csv_export_action

from .models import TestModel


class TestModelAdmin(TablibAdmin):
    actions = [xls_export_action, csv_export_action]

admin.site.register(TestModel, TestModelAdmin)

########NEW FILE########
__FILENAME__ = models
from django.db import models


class TestModel(models.Model):
    field1 = models.TextField()

########NEW FILE########
__FILENAME__ = tests
from django.test import TestCase

from django_tablib import ModelDataset, Field

from .models import TestModel


class DjangoTablibTestCase(TestCase):
    def setUp(self):
        TestModel.objects.create(field1='value')

    def test_declarative_fields(self):
        class TestModelDataset(ModelDataset):
            field1 = Field(header='Field 1')
            field2 = Field(attribute='field1')

            class Meta:
                model = TestModel

        data = TestModelDataset()

        self.assertEqual(len(data.headers), 3)
        self.assertTrue('id' in data.headers)
        self.assertFalse('field1' in data.headers)
        self.assertTrue('field2' in data.headers)
        self.assertTrue('Field 1' in data.headers)

        self.assertEqual(data[0][0], data[0][1])

    def test_meta_fields(self):
        class TestModelDataset(ModelDataset):
            class Meta:
                model = TestModel
                fields = ['field1']

        data = TestModelDataset()

        self.assertEqual(len(data.headers), 1)
        self.assertFalse('id' in data.headers)
        self.assertTrue('field1' in data.headers)

    def test_meta_exclude(self):
        class TestModelDataset(ModelDataset):
            class Meta:
                model = TestModel
                exclude = ['id']

        data = TestModelDataset()

        self.assertEqual(len(data.headers), 1)
        self.assertFalse('id' in data.headers)
        self.assertTrue('field1' in data.headers)

    def test_meta_both(self):
        class TestModelDataset(ModelDataset):
            class Meta:
                model = TestModel
                fields = ['id', 'field1']
                exclude = ['id']

        data = TestModelDataset()

        self.assertEqual(len(data.headers), 1)
        self.assertFalse('id' in data.headers)
        self.assertTrue('field1' in data.headers)

########NEW FILE########
__FILENAME__ = settings
"""
Django settings for testproject project.

For more information on this file, see
https://docs.djangoproject.com/en/1.6/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.6/ref/settings/
"""

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
import os
BASE_DIR = os.path.dirname(os.path.dirname(__file__))


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.6/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = '6icxf))9*4&n$v+^71klqfmb2o8^0ap4v3ja_nl=l=m_shs@2r'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

TEMPLATE_DEBUG = True

ALLOWED_HOSTS = []


# Application definition

INSTALLED_APPS = (
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django_tablib',
    'tablib_test',
)

MIDDLEWARE_CLASSES = (
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
)

ROOT_URLCONF = 'testproject.urls'

WSGI_APPLICATION = 'testproject.wsgi.application'


# Database
# https://docs.djangoproject.com/en/1.6/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
    }
}

# Internationalization
# https://docs.djangoproject.com/en/1.6/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.6/howto/static-files/

STATIC_URL = '/static/'

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls import patterns, include, url

from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
    # Examples:
    # url(r'^$', 'testproject.views.home', name='home'),
    # url(r'^blog/', include('blog.urls')),

    url(r'^admin/', include(admin.site.urls)),
)

########NEW FILE########
__FILENAME__ = wsgi
"""
WSGI config for testproject project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/1.6/howto/deployment/wsgi/
"""

import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "testproject.settings")

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()

########NEW FILE########
