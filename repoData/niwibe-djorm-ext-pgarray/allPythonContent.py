__FILENAME__ = fields
# -*- coding: utf-8 -*-

import json

import django
from django import forms
from django.core.exceptions import ValidationError
from django.core.serializers.json import DjangoJSONEncoder
from django.db import models
from django.utils import six
from django.utils.encoding import force_text
from django.utils.translation import ugettext_lazy as _


TYPES = {
    'int': int,
    'smallint': int,
    'bigint': int,
    'text': str,
    'double precision': float,
    'varchar': str,
    'date': lambda x: x,
    'datetime': lambda x: x,
}


def _cast_to_unicode(data):
    if isinstance(data, (list, tuple)):
        return [_cast_to_unicode(x) for x in data]
    elif isinstance(data, str):
        return force_text(data)
    return data


def _cast_to_type(data, type_cast):
    if isinstance(data, (list, tuple)):
        return [_cast_to_type(x, type_cast) for x in data]
    if type_cast == str:
        return force_text(data)
    return type_cast(data)


def _unserialize(value):
    if not isinstance(value, six.string_types):
        return _cast_to_unicode(value)
    try:
        return _cast_to_unicode(json.loads(value))
    except ValueError:
        return _cast_to_unicode(value)


class ArrayField(six.with_metaclass(models.SubfieldBase, models.Field)):
    def __init__(self, *args, **kwargs):
        self._array_type = kwargs.pop('dbtype', 'int')
        type_key = self._array_type.split('(')[0]

        if "type_cast" in kwargs:
            self._type_cast = kwargs.pop("type_cast")
        elif type_key in TYPES:
            self._type_cast = TYPES[type_key]
        else:
            self._type_cast = lambda x: x

        self._dimension = kwargs.pop('dimension', 1)
        kwargs.setdefault('blank', True)
        kwargs.setdefault('null', True)
        kwargs.setdefault('default', None)
        super(ArrayField, self).__init__(*args, **kwargs)

    def get_db_prep_lookup(self, lookup_type, value, connection, prepared=False):
        if isinstance(value, (list, tuple)):
            return [value]
        return super(ArrayField, self).get_db_prep_lookup(lookup_type, value, connection, prepared)

    def formfield(self, **params):
        params.setdefault('form_class', ArrayFormField)
        return super(ArrayField, self).formfield(**params)

    def get_db_prep_value(self, value, connection, prepared=False):
        value = value if prepared else self.get_prep_value(value)
        if not value or isinstance(value, six.string_types):
            return value
        return _cast_to_type(value, self._type_cast)

    def get_prep_value(self, value):
        return value

    def to_python(self, value):
        return _unserialize(value)

    def value_to_string(self, obj):
        value = self._get_val_from_obj(obj)
        return json.dumps(self.get_prep_value(value),
                          cls=DjangoJSONEncoder)

    def validate(self, value, model_instance):
        for val in value:
            super(ArrayField, self).validate(val, model_instance)

    if django.VERSION[:2] >= (1, 7):
        def deconstruct(self):
            name, path, args, kwargs = super(ArrayField, self).deconstruct()
            kwargs["dbtype"] = self._array_type
            kwargs["type_cast"] = self._type_cast
            kwargs["dimension"] = self._dimension
            return name, path, args, kwargs

        def db_parameters(self, connection):
            return {
                'type': '{0}{1}'.format(self._array_type, "[]" * self._dimension),
                'check': None
            }
    else:
        def db_type(self, connection):
            return '{0}{1}'.format(self._array_type, "[]" * self._dimension)


# South support
try:
    from south.modelsinspector import add_introspection_rules
    add_introspection_rules([
        (
            [ArrayField], # class
            [],           # positional params
            {
                "dbtype": ["_array_type", {"default": "int"}],
                "dimension": ["_dimension", {"default": 1}],
            }
        )
    ], ['^djorm_pgarray\.fields\.ArrayField'])
except ImportError:
    pass


class ArrayFormField(forms.Field):
    default_error_messages = {
        'invalid': _('Enter a list of values, joined by commas.  E.g. "a,b,c".'),
    }

    def __init__(self, max_length=None, min_length=None, delim=None,
                 strip=True, *args, **kwargs):
        if delim is not None:
            self.delim = delim
        else:
            self.delim = u','

        self.strip = strip

        super(ArrayFormField, self).__init__(*args, **kwargs)

    def clean(self, value):
        if not value:
            return []
        # If Django already parsed value to list
        if isinstance(value, list):
            return value
        try:
            if self.strip:
                return map(unicode.strip, value.split(self.delim))
            else:
                return value.split(self.delim)
        except Exception:
            raise ValidationError(self.error_messages['invalid'])

    def prepare_value(self, value):
        if value:
            return self.delim.join(force_text(v) for v in value)

        return super(ArrayFormField, self).prepare_value(value)

    def to_python(self, value):
        return value.split(self.delim)



if django.VERSION[:2] >= (1, 7):
    from django.db.models import Lookup

    class ContainsLookup(Lookup):
        lookup_name = 'contains'

        def as_sql(self, qn, connection):
            lhs, lhs_params = self.process_lhs(qn, connection)
            rhs, rhs_params = self.process_rhs(qn, connection)
            params = lhs_params + rhs_params
            return '%s @> %s' % (lhs, rhs), params

    class ContainedByLookup(Lookup):
        lookup_name = "contained_by"

        def as_sql(self, qn, connection):
            lhs, lhs_params = self.process_lhs(qn, connection)
            rhs, rhs_params = self.process_rhs(qn, connection)
            params = lhs_params + rhs_params
            return '%s <@ %s' % (lhs, rhs), params

    class OverlapLookip(Lookup):
        lookup_name = "overlap"

        def as_sql(self, qn, connection):
            lhs, lhs_params = self.process_lhs(qn, connection)
            rhs, rhs_params = self.process_rhs(qn, connection)
            params = lhs_params + rhs_params
            return '%s && %s' % (lhs, rhs), params

    from django.db.models.fields import Field
    Field.register_lookup(ContainedByLookup)
    Field.register_lookup(ContainsLookup)
    Field.register_lookup(OverlapLookip)

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
__FILENAME__ = admin
# -*- coding: utf-8 -*-

from django.contrib import admin

from . import models


class Admin(admin.ModelAdmin):
    pass

admin.site.register(models.IntModel, Admin)
admin.site.register(models.DoubleModel, Admin)

########NEW FILE########
__FILENAME__ = forms
# -*- coding: utf-8 -*-
from django.forms.models import ModelForm
from .models import IntModel


class IntArrayForm(ModelForm):
    class Meta:
        model = IntModel
        fields = ["lista"]

########NEW FILE########
__FILENAME__ = models
# -*- coding: utf-8 -*-

from django.db import models
from djorm_pgarray.fields import ArrayField

class Item(models.Model):
    tags = ArrayField(dbtype="text", default=lambda: [])

class Item2(models.Model):
    tags = ArrayField(dbtype="text", default=[])

class IntModel(models.Model):
    lista = ArrayField(dbtype='int')

class TextModel(models.Model):
    lista = ArrayField(dbtype='text')

class MacAddrModel(models.Model):
    lista = ArrayField(dbtype='macaddr', type_cast=str)

class DoubleModel(models.Model):
    lista = ArrayField(dbtype='double precision')

class MTextModel(models.Model):
    data = ArrayField(dbtype="text", dimension=2)

class MultiTypeModel(models.Model):
    smallints = ArrayField(dbtype="smallint")
    varchars = ArrayField(dbtype="varchar(30)")

class DateModel(models.Model):
    dates = ArrayField(dbtype="date")

class DateTimeModel(models.Model):
    dates = ArrayField(dbtype="timestamp")

class ChoicesModel(models.Model):
    choices = ArrayField(dbtype='text', choices=[('A', 'A'), ('B', 'B')])

########NEW FILE########
__FILENAME__ = tests
# -*- coding: utf-8 -*-

import datetime

import django
from django.contrib.admin import AdminSite, ModelAdmin
from django.core.serializers import serialize, deserialize
from django.db import connection
from django.test import TestCase

from djorm_pgarray.fields import ArrayField, ArrayFormField

from .forms import IntArrayForm
from .models import (IntModel,
                     TextModel,
                     DoubleModel,
                     MTextModel,
                     MultiTypeModel,
                     ChoicesModel,
                     Item,
                     Item2,
                     DateModel,
                     DateTimeModel,
                     MacAddrModel)

import psycopg2.extensions

class MacAddr(str):
    pass


def get_type_oid(sql_expression):
    """Query the database for the OID of the type of sql_expression."""
    cursor = connection.cursor()
    try:
        cursor.execute("SELECT " + sql_expression)
        return cursor.description[0][1]
    finally:
        cursor.close()

def cast_macaddr(val, cur):
    return MacAddr(val)


def adapt_macaddr(maddr):
    from psycopg2.extensions import adapt, AsIs
    return AsIs("{0}::macaddr".format(adapt(str(maddr))))


def register_macaddr_type():
    from psycopg2.extensions import register_adapter, new_type, register_type, new_array_type
    import psycopg2

    oid = get_type_oid("NULL::macaddr")
    PGTYPE = new_type((oid,), "macaddr", cast_macaddr)
    register_type(PGTYPE)
    register_adapter(MacAddr, adapt_macaddr)

    mac_array_oid = get_type_oid("'{}'::macaddr[]")
    array_of_mac = new_array_type((mac_array_oid, ), 'macaddr', psycopg2.STRING)
    psycopg2.extensions.register_type(array_of_mac)


class ArrayFieldTests(TestCase):
    def setUp(self):
        IntModel.objects.all().delete()
        TextModel.objects.all().delete()
        DoubleModel.objects.all().delete()
        MultiTypeModel.objects.all().delete()

    def test_default_value_1(self):
        obj = Item.objects.create()
        self.assertEqual(obj.tags, [])

    def test_default_value_2(self):
        obj = Item2.objects.create()
        self.assertEqual(obj.tags, [])

    def test_date(self):
        d = datetime.date(2011, 11, 11)
        instance = DateModel.objects.create(dates=[d])

        instance = DateModel.objects.get(pk=instance.pk)
        self.assertEqual(instance.dates[0], d)

    def test_datetime(self):
        d = datetime.datetime(2011, 11, 11, 11, 11, 11)
        instance = DateTimeModel.objects.create(dates=[d])
        instance = DateTimeModel.objects.get(pk=instance.pk)
        self.assertEqual(instance.dates[0], d)

    def test_empty_create(self):
        instance = IntModel.objects.create(lista=[])
        instance = IntModel.objects.get(pk=instance.pk)
        self.assertEqual(instance.lista, [])

    def test_macaddr_model(self):
        register_macaddr_type()
        instance = MacAddrModel.objects.create()
        instance.lista = [MacAddr('00:24:d6:54:ff:c6'), MacAddr('00:24:d6:54:ff:c4')]
        instance.save()

        instance = MacAddrModel.objects.get(pk=instance.pk)
        self.assertEqual(instance.lista, ['00:24:d6:54:ff:c6', '00:24:d6:54:ff:c4'])

    def test_correct_behavior_with_text_arrays_01(self):
        obj = TextModel.objects.create(lista=[[1,2],[3,4]])
        obj = TextModel.objects.get(pk=obj.pk)
        self.assertEqual(obj.lista, [[u'1', u'2'], [u'3', u'4']])

    def test_correct_behavior_with_text_arrays_02(self):
        obj = MTextModel.objects.create(data=[[u"1",u"2"],[u"3",u"ñ"]])
        obj = MTextModel.objects.get(pk=obj.pk)
        self.assertEqual(obj.data, [[u"1",u"2"],[u"3",u"ñ"]])

    def test_correct_behavior_with_int_arrays(self):
        obj = IntModel.objects.create(lista=[1,2,3])
        obj = IntModel.objects.get(pk=obj.pk)
        self.assertEqual(obj.lista, [1, 2, 3])

    def test_correct_behavior_with_float_arrays(self):
        obj = DoubleModel.objects.create(lista=[1.2,2.4,3])
        obj = DoubleModel.objects.get(pk=obj.pk)
        self.assertEqual(obj.lista, [1.2, 2.4, 3])

    def test_value_to_string_serializes_correctly(self):
        obj = MTextModel.objects.create(data=[[u"1",u"2"],[u"3",u"ñ"]])
        obj_int = IntModel.objects.create(lista=[1,2,3])

        serialized_obj = serialize('json', MTextModel.objects.filter(pk=obj.pk))
        serialized_obj_int = serialize('json', IntModel.objects.filter(pk=obj_int.pk))

        obj.delete()
        obj_int.delete()

        deserialized_obj = list(deserialize('json', serialized_obj))[0]
        deserialized_obj_int = list(deserialize('json', serialized_obj_int))[0]

        obj = deserialized_obj.object
        obj_int = deserialized_obj_int.object
        obj.save()
        obj_int.save()

        self.assertEqual(obj.data, [[u"1",u"2"],[u"3",u"ñ"]])
        self.assertEqual(obj_int.lista, [1,2,3])

    def test_to_python_serializes_xml_correctly(self):
        obj = MTextModel.objects.create(data=[[u"1",u"2"],[u"3",u"ñ"]])
        obj_int = IntModel.objects.create(lista=[1,2,3])

        serialized_obj = serialize('xml', MTextModel.objects.filter(pk=obj.pk))
        serialized_obj_int = serialize('xml', IntModel.objects.filter(pk=obj_int.pk))

        obj.delete()
        obj_int.delete()
        deserialized_obj = list(deserialize('xml', serialized_obj))[0]
        deserialized_obj_int = list(deserialize('xml', serialized_obj_int))[0]
        obj = deserialized_obj.object
        obj_int = deserialized_obj_int.object
        obj.save()
        obj_int.save()

        self.assertEqual(obj.data, [[u"1",u"2"],[u"3",u"ñ"]])
        self.assertEqual(obj_int.lista, [1,2,3])

    def test_can_override_formfield(self):
        model_field = ArrayField()
        class FakeFieldClass(object):
            def __init__(self, *args, **kwargs):
                pass
        form_field = model_field.formfield(form_class=FakeFieldClass)
        self.assertIsInstance(form_field, FakeFieldClass)

    def test_other_types_properly_casted(self):
        obj = MultiTypeModel.objects.create(
            smallints=[1, 2, 3],
            varchars=['One', 'Two', 'Three']
        )
        obj = MultiTypeModel.objects.get(pk=obj.pk)

        self.assertEqual(obj.smallints, [1, 2, 3])
        self.assertEqual(obj.varchars, ['One', 'Two', 'Three'])

    def test_choices_validation(self):
        obj = ChoicesModel(choices=['A'])
        obj.full_clean()
        obj.save()

if django.VERSION[:2] >= (1, 7):
    class ArrayFieldTests(TestCase):
        def setUp(self):
            IntModel.objects.all().delete()

        def test_contains_lookup(self):
            obj1 = IntModel.objects.create(lista=[1,4,3])
            obj2 = IntModel.objects.create(lista=[0,10,50])

            qs = IntModel.objects.filter(lista__contains=[1,3])
            self.assertEqual(qs.count(), 1)

        def test_contained_by_lookup(self):
            obj1 = IntModel.objects.create(lista=[2,7])
            obj2 = IntModel.objects.create(lista=[0,10,50])

            qs = IntModel.objects.filter(lista__contained_by=[1,7,4,2,6])
            self.assertEqual(qs.count(), 1)

        def test_overlap_lookup(self):
            obj1 = IntModel.objects.create(lista=[1,4,3])
            obj2 = IntModel.objects.create(lista=[0,10,50])

            qs = IntModel.objects.filter(lista__overlap=[2,1])
            self.assertEqual(qs.count(), 1)

        def test_contains_unicode(self):
            obj = TextModel.objects.create(lista=[u"Fóö", u"Пример", u"test"])
            qs = TextModel.objects.filter(lista__contains=[u"Пример"])
            self.assertEqual(qs.count(), 1)


class ArrayFormFieldTests(TestCase):
    def test_regular_forms(self):
        form = IntArrayForm()
        self.assertFalse(form.is_valid())
        form = IntArrayForm({'lista':u'[1,2]'})
        self.assertTrue(form.is_valid())

    def test_empty_value(self):
        form = IntArrayForm({'lista':u''})
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data['lista'], [])

    def test_admin_forms(self):
        site = AdminSite()
        model_admin = ModelAdmin(IntModel, site)
        form_clazz = model_admin.get_form(None)
        form_instance = form_clazz()

        try:
            form_instance.as_table()
        except TypeError:
            self.fail('HTML Rendering of the form caused a TypeError')

    def test_unicode_data(self):
        field = ArrayFormField()
        result = field.prepare_value([u"Клиент",u"こんにちは"])
        self.assertEqual(result, u"Клиент,こんにちは")

    def test_invalid_error(self):
        form = IntArrayForm({'lista':1})
        self.assertFalse(form.is_valid())
        self.assertEqual(
            form.errors['lista'],
            [u'Enter a list of values, joined by commas.  E.g. "a,b,c".']
            )

########NEW FILE########
__FILENAME__ = runtests
# -*- coding: utf-8 -*-

import os, sys
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")

from django.core.management import call_command

if __name__ == "__main__":
    args = sys.argv[1:]
    if len(args) == 0:
        args.append("pg_array_fields")
    call_command("test", *args, verbosity=2)

########NEW FILE########
__FILENAME__ = settings
import os, sys

sys.path.insert(0, '..')
sys.path.insert(0, '/home/niwi/devel/djorm-ext-expressions')

PROJECT_ROOT = os.path.dirname(__file__)
DEBUG = True
TEMPLATE_DEBUG = DEBUG

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': 'test',
        'USER': '',
        'PASSWORD': '',
        'HOST': 'localhost',
        'PORT': '',
    }
}

STATICFILES_FINDERS = [
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
]

STATIC_URL = "/static/"
SITE_ID = 1

TIME_ZONE = 'America/Chicago'
LANGUAGE_CODE = 'en-us'
ADMIN_MEDIA_PREFIX = '/static/admin/'
STATICFILES_DIRS = ()

SECRET_KEY = 'di!n($kqa3)nd%ikad#kcjpkd^uw*h%*kj=*pm7$vbo6ir7h=l'
ROOT_URLCONF = "urls"

MIDDLEWARE_CLASSES = [
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
]

INSTALLED_APPS = [
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sites',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.admin',
    'django.contrib.staticfiles',
    'pg_array_fields',
]

TEST_RUNNER = 'django.test.simple.DjangoTestSuiteRunner'

########NEW FILE########
__FILENAME__ = urls
# -*- coding: utf-8 -*-

from django.conf import settings
from django.conf.urls import patterns, include, url
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.contrib import admin

admin.autodiscover()

urlpatterns = patterns('',
    url(r'^', include(admin.site.urls)),
)

urlpatterns += staticfiles_urlpatterns()

########NEW FILE########
