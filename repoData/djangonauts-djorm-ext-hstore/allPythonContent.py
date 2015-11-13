__FILENAME__ = expressions
# -*- coding: utf-8 -*-

import sys
if sys.version_info[0] > 2:
    basestring = str

from djorm_expressions.base import SqlExpression

class HstoreExpression(object):
    def __init__(self, field):
        self.field = field

    def contains(self, value):
        if isinstance(value, dict):
            expression = SqlExpression(
                self.field, "@>", value
            )
        elif isinstance(value, (list,tuple)):
            expression = SqlExpression(
                self.field, "?&", value
            )
        elif isinstance(value, basestring):
            expression = SqlExpression(
                self.field, "?", value
            )
        else:
            raise ValueError("Invalid value")
        return expression

    def exact(self, value):
        return SqlExpression(
            self.field, "=", value
        )

    def as_sql(self, qn, queryset):
        raise NotImplementedError

########NEW FILE########
__FILENAME__ = fields
# -*- coding: utf-8 -*-
import sys
import json

from django.db import models
from django.utils.translation import ugettext_lazy as _

from . import forms, util

if sys.version_info[0] < 3:
    text_type = unicode
    binary_type = str
else:
    text_type = str
    binary_type = bytes


class HStoreDictionary(dict):
    """
    A dictionary subclass which implements hstore support.
    """
    def __init__(self, value=None, field=None, instance=None, **params):
        super(HStoreDictionary, self).__init__(value, **params)
        self.field = field
        self.instance = instance

    def remove(self, keys):
        """
        Removes the specified keys from this dictionary.
        """
        queryset = self.instance._base_manager.get_query_set()
        queryset.filter(pk=self.instance.pk).hremove(self.field.name, keys)

    def __getstate__(self):
        """
        Returns pickable Python dict.
        """
        return dict(self)


class HStoreDescriptor(models.fields.subclassing.Creator):
    def __set__(self, obj, value):
        value = self.field.to_python(value)

        if isinstance(value, dict):
            value = self.field._attribute_class(value, self.field, obj)

        obj.__dict__[self.field.name] = value

    def __getstate__(self):
        """
        Returns pickable Python dict.
        """
        to_pickle = self.__dict__.copy()
        del to_pickle['default']
        return to_pickle


class HStoreField(models.Field):
    _attribute_class = HStoreDictionary
    _descriptor_class = HStoreDescriptor

    def __init__(self, *args, **kwargs):
        super(HStoreField, self).__init__(*args, **kwargs)

    def contribute_to_class(self, cls, name):
        super(HStoreField, self).contribute_to_class(cls, name)
        setattr(cls, self.name, self._descriptor_class(self))

    def db_type(self, connection=None):
        return 'hstore'

    def get_prep_value(self, data):
        if not isinstance(data, (dict, HStoreDictionary)):
            return data

        for key in data:
            if data[key] is None:
                continue
            if not isinstance(data[key], (util.string_type, util.bytes_type)):
                data[key] = util.string_type(data[key])

        return data


class DictionaryField(HStoreField):
    description = _("A python dictionary in a postgresql hstore field.")

    def formfield(self, **params):
        params.setdefault("form_class", forms.DictionaryField)
        return super(DictionaryField, self).formfield(**params)

    def value_from_object(self, obj):
        """
        Return a sorted JSON string.
        """
        value = super(DictionaryField, self).value_from_object(obj)
        if value is not None:
            return json.dumps(value, sort_keys=True)

    def get_prep_lookup(self, lookup, value):
        return value

    def to_python(self, value):
        if value is None:
            return None

        if isinstance(value, util.string_type) and value:
            try:
                return json.loads(value)
            except ValueError:
                return {}

        return value or {}

    def value_to_string(self, obj):
        value = self._get_val_from_obj(obj)
        prepped = self.get_prep_value(value)
        return json.dumps(prepped)

    def _value_to_python(self, value):
        return value


class ReferencesField(HStoreField):
    description = _("A python dictionary of references to model instances in an hstore field.")

    def formfield(self, **params):
        params.setdefault("form_class", forms.ReferencesField)
        return super(ReferencesField, self).formfield(**params)

    def get_prep_lookup(self, lookup, value):
        return util.serialize_references(value) if isinstance(value, dict) else value

    def get_prep_value(self, value):
        return util.serialize_references(value) if value else {}

    def to_python(self, value):
        return util.unserialize_references(value) if value else {}

    def _value_to_python(self, value):
        return util.acquire_reference(value) if value else None

try:
    from south.modelsinspector import add_introspection_rules
    add_introspection_rules(rules=[], patterns=['djorm_hstore.fields\.DictionaryField'])
    add_introspection_rules(rules=[], patterns=['djorm_hstore.fields\.ReferencesField'])
except ImportError:
    pass

########NEW FILE########
__FILENAME__ = forms
from django.forms import Field
from django.contrib.admin.widgets import AdminTextareaWidget
from django.core.exceptions import ValidationError
from django.utils.translation import ugettext_lazy as _

from . import util
from .widgets import KeyValueWidget
import json


class JsonMixin(object):
    def to_python(self, value):
        try:
            if value is not None:
                return json.loads(value)
        except TypeError:
            raise ValidationError(_(u'String type is required.'))
        except ValueError:
            raise ValidationError(_(u'Enter a valid value.'))

    def value_from_datadict(self, data, files, name):
        value = data.get(name, None)
        try:
            # load/re-dump to sort by key for has_changed comparison
            value = json.dumps(json.loads(value), sort_keys=True)
        except (TypeError, ValueError):
            pass
        return value


class DictionaryFieldWidget(JsonMixin, AdminTextareaWidget):
    def render(self, name, value, attrs=None):
        if value:
            # a DictionaryField (model field) returns a string value via
            # value_from_object(), load and re-dump for indentation
            try:
                value = json.dumps(json.loads(value), sort_keys=True, indent=2)
            except ValueError:
                # Skip formatting if value is not valid JSON
                pass
        return super(JsonMixin, self).render(name, value, attrs)


class ReferencesFieldWidget(JsonMixin, AdminTextareaWidget):
    def render(self, name, value, attrs=None):
        value = util.serialize_references(value)
        return super(ReferencesFieldWidget, self).render(name, value, attrs)


class DictionaryField(JsonMixin, Field):
    """
    A dictionary form field.
    """
    def __init__(self, **params):
        defaults = {
            'widget': KeyValueWidget,
            'initial': u'{}',
        }
        defaults.update(params)
        super(DictionaryField, self).__init__(**defaults)


class ReferencesField(JsonMixin, Field):
    """
    A references form field.
    """
    def __init__(self, **params):
        params['widget'] = ReferencesFieldWidget
        super(ReferencesField, self).__init__(**params)

    def to_python(self, value):
        value = super(ReferencesField, self).to_python(value)
        return util.unserialize_references(value)

########NEW FILE########
__FILENAME__ = functions
# -*- coding: utf-8 -*-

from djorm_expressions.base import SqlFunction


class HstoreSlice(SqlFunction):
    """
    Obtain dictionary with only selected keys.

    Usage example::

        queryset = SomeModel.objects\
            .inline_annotate(sliced=HstoreSlice("data").as_aggregate(['v']))
    """

    sql_template = '%(function)s(%(field)s, %%s)'
    sql_function = 'slice'


class HstorePeek(SqlFunction):
    """
    Obtain values from hstore field.
    Usage example::

        queryset = SomeModel.objects\
            .inline_annotate(peeked=HstorePeek("data").as_aggregate("v"))
    """

    sql_template = '%(field)s -> %%s'


class HstoreKeys(SqlFunction):
    """
    Obtain keys from hstore fields.
    Usage::

        queryset = SomeModel.objects\
            .inline_annotate(keys=HstoreKeys("somefield").as_aggregate())
    """

    sql_function = 'akeys'

########NEW FILE########
__FILENAME__ = models
# -*- coding: utf-8 -*-

import sys

from django.db.models.sql.constants import SINGLE
from django.db.models.query_utils import QueryWrapper
from django.db.models.query import QuerySet
from django.db import models

from djorm_expressions.models import ExpressionQuerySetMixin, ExpressionManagerMixin

from .query_utils import select_query, update_query


class HStoreQuerysetMixin(object):
    @select_query
    def hkeys(self, query, attr):
        """
        Enumerates the keys in the specified hstore.
        """
        query.add_extra({'_': 'akeys("%s")' % attr}, None, None, None, None, None)
        result = query.get_compiler(self.db).execute_sql(SINGLE)
        return (result[0] if result else [])

    @select_query
    def hpeek(self, query, attr, key):
        """
        Peeks at a value of the specified key.
        """
        query.add_extra({'_': '%s -> %%s' % attr}, [key], None, None, None, None)
        result = query.get_compiler(self.db).execute_sql(SINGLE)
        if result and result[0]:
            field = self.model._meta.get_field_by_name(attr)[0]
            return field._value_to_python(result[0])

    @select_query
    def hslice(self, query, attr, keys):
        """
        Slices the specified key/value pairs.
        """
        query.add_extra({'_': 'slice("%s", %%s)' % attr}, [keys], None, None, None, None)
        result = query.get_compiler(self.db).execute_sql(SINGLE)
        if result and result[0]:
            field = self.model._meta.get_field_by_name(attr)[0]
            return dict((key, field._value_to_python(value)) for key, value in result[0].items())
        return {}

    @update_query
    def hremove(self, query, attr, keys):
        """
        Removes the specified keys in the specified hstore.
        """
        value = QueryWrapper('delete("%s", %%s)' % attr, [keys])
        field, model, direct, m2m = self.model._meta.get_field_by_name(attr)
        query.add_update_fields([(field, None, value)])
        return query

    @update_query
    def hupdate(self, query, attr, updates):
        """
        Updates the specified hstore.
        """
        value = QueryWrapper('"%s" || %%s' % attr, [updates])
        field, model, direct, m2m = self.model._meta.get_field_by_name(attr)
        query.add_update_fields([(field, None, value)])
        return query


class HStoreQueryset(HStoreQuerysetMixin, ExpressionQuerySetMixin, QuerySet):
    pass


class HStoreManagerMixin(object):
    """
    Object manager which enables hstore features.
    """
    use_for_related_fields = True

    def hkeys(self, attr):
        return self.get_query_set().hkeys(attr)

    def hpeek(self, attr, key):
        return self.get_query_set().hpeek(attr, key)

    def hslice(self, attr, keys, **params):
        return self.get_query_set().hslice(attr, keys)


class HStoreManager(HStoreManagerMixin, ExpressionManagerMixin, models.Manager):
    def get_query_set(self):
        return HStoreQueryset(self.model, using=self._db)


# Signal attaching
from psycopg2.extras import register_hstore

def register_hstore_handler(connection, **kwargs):
    if not connection.settings_dict.get('HAS_HSTORE', True):
        return
    if sys.version_info[0] < 3:
        register_hstore(connection.connection, globally=True, unicode=True)
    else:
        register_hstore(connection.connection, globally=True)

from djorm_core.models import connection_handler
connection_handler.attach_handler(register_hstore_handler, vendor="postgresql", unique=True)

########NEW FILE########
__FILENAME__ = query_utils
# -*- coding: utf-8 -*-

from django.db import transaction
from django.db.models.sql.subqueries import UpdateQuery

def select_query(method):
    def selector(self, *args, **params):
        query = self.query.clone()
        query.default_cols = False
        query.clear_select_fields()
        return method(self, query, *args, **params)
    return selector


def update_query(method):
    def updater(self, *args, **params):
        self._for_write = True
        temporal_update_query = self.query.clone(UpdateQuery)
        query = method(self, temporal_update_query, *args, **params)

        forced_managed = False
        if not transaction.is_managed(using=self.db):
            transaction.enter_transaction_management(using=self.db)
            forced_managed = True

        try:
            rows = query.get_compiler(self.db).execute_sql(None)
            if forced_managed:
                transaction.commit(using=self.db)
            else:
                transaction.commit_unless_managed(using=self.db)
        finally:
            if forced_managed:
                transaction.leave_transaction_management(using=self.db)

        self._result_cache = None
        return rows

    updater.alters_data = True
    return updater

########NEW FILE########
__FILENAME__ = forms

from django.forms import ModelForm

from .models import DataBag


class DataBagForm(ModelForm):
    class Meta:
        model = DataBag

########NEW FILE########
__FILENAME__ = models

from django.db import models

from ..fields import DictionaryField, ReferencesField
from ..models import HStoreManager

class Ref(models.Model):
    name = models.CharField(max_length=32)

    def __unicode__(self):
        return self.name

    _options = {
        'manager': False,
    }


class DataBag(models.Model):
    name = models.CharField(max_length=32)
    data = DictionaryField(db_index=True)

    objects = HStoreManager()

    _options = {
        'manager': False
    }

    def __unicode__(self):
        return self.name


class DataBagNullable(models.Model):
    name = models.CharField(max_length=32)
    data = DictionaryField(db_index=True, null=True)

    objects = HStoreManager()

    _options = {
        'manager': False
    }

    def __unicode__(self):
        return self.name


class RefsBag(models.Model):
    name = models.CharField(max_length=32)
    refs = ReferencesField(db_index=True)

    objects = HStoreManager()

    _options = {
        'manager': False
    }

    def __unicode__(self):
        return self.name


########NEW FILE########
__FILENAME__ = util
# -*- coding: utf-8 -*-

from django.core.exceptions import ObjectDoesNotExist

import sys

if sys.version_info[0] == 3:
    string_type = str
    bytes_type = bytes
    basestring = (str,)

else:
    string_type = unicode
    bytes_type = str
    basestring = (str, unicode)


def acquire_reference(reference):
    try:
        implementation, identifier = reference.split(':')
        module, sep, attr = implementation.rpartition('.')
        implementation = getattr(__import__(module, fromlist=(attr,)), attr)
        return implementation.objects.get(pk=identifier)
    except ObjectDoesNotExist:
        return None
    except Exception:
        raise ValueError


def identify_instance(instance):
    implementation = type(instance)
    return '%s.%s:%s' % (implementation.__module__, implementation.__name__, instance.pk)


def serialize_references(references):
    refs = {}
    for key, instance in references.items():
        if not isinstance(instance, basestring):
            refs[key] = identify_instance(instance)
        else:
            refs[key] = instance
    else:
        return refs


def unserialize_references(references):
    refs = {}
    for key, reference in references.items():
        if isinstance(reference, basestring):
            refs[key] = acquire_reference(reference)
        else:
            refs[key] = reference
    else:
        return refs

########NEW FILE########
__FILENAME__ = widgets
# -*- coding: utf-8 -*-

import json

from django import forms
from django.forms import widgets
from django.contrib.admin.templatetags.admin_static import static
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext as _


class KeyValueWidget(widgets.MultiWidget):
    input_widget_class = widgets.TextInput
    row_template = '<div class="form-row" %s>%s </div>'
    input_template = '<div class="field-box"><label for="%(label_for)s">%(label)s: %(input)s</label></div>'
    widget_template = '<ul id="%s" class="keyvaluewidget">%s</ul>'
    add_button_template = '<a href="javascript:void(0)" class="add_keyvaluewidget">' +\
                          '<img src="%(icon_url)s" width="10" height="10"> %(name)s</a>'
    remove_button_template = '<div class="field-box"><a class="inline-deletelink" href="javascript:void(0)">%s</a></div>'

    @property
    def media(self):
        return forms.Media(js=[static("djorm_hstore/js/djorm_hstore.js")])

    def __init__(self, attrs=None, key_attrs=None, value_attrs=None):
        self.key_attrs = key_attrs or {}
        self.value_attrs = value_attrs or {}
        attrs = attrs or {}
        attrs.setdefault('class', 'vTextField')
        self.attrs = attrs
        self.input_widget = self.input_widget_class(attrs)
        super(KeyValueWidget, self).__init__([], attrs)

    def render(self, name, value, attrs=None):
        final_attrs = self.build_attrs(attrs)
        main_id = self.id_for_label(final_attrs.get('id', None))
        if value:
            values = json.loads(value).items()
            empty_row = ''.join([  # row for cloning in js
                self.make_input_widget('key', name, '', main_id, '', final_attrs),
                self.make_input_widget('value', name, '', main_id, '', final_attrs),
                self.make_del_link(name, main_id, ''),
            ])
            output = [
                self.row_template % (
                    'style="display:none;"',
                    empty_row
                )
            ]
            for i, (key, val) in enumerate(values, start=1):
                output.extend(self.row_template % ('', ''.join([
                    self.make_input_widget('key', name, key, main_id, i, final_attrs),
                    self.make_input_widget('value', name, val, main_id, i, final_attrs),
                    self.make_del_link(name, main_id, i),
                ])))
            return mark_safe(self.format_output(name, main_id, output))
        return ''

    def make_input_widget(self, widget_type, name, value, main_id, index, attrs):
        id_ = '%s_%s_%s' % (main_id, widget_type, index)
        attrs = dict(attrs, id=id_, name="%s_%s_%s" % (name, widget_type, index))
        return self.input_template % {
            'label_for': id_,
            'label': _(widget_type.title()),
            'input': self.input_widget.render(name + '_%s' % index, value, attrs)
        }

    def make_del_link(self, name, main_id, index):
        return self.remove_button_template % _('Remove')

    def format_output(self, name, widget_id, rendered_widgets):
        add_button = self.add_button_template % {
            'name': _("Add another pair"),
            'icon_url': self.media.absolute_path('admin/img/icon_addlink.gif')
        }
        rendered_widgets.append(self.row_template % ('', add_button))
        html = self.widget_template % (widget_id, ''.join(rendered_widgets))
        return html

    def value_from_datadict(self, data, files, name):
        value = {}
        for key_fieldname in sorted([i for i in data if i.startswith(name + "_key_")]):
            key = data.get(key_fieldname, '')
            if not key:
                continue
            val = data.get(key_fieldname.replace('_key_', '_value_'), '')
            value[key] = val
        return json.dumps(value)

    def decompress(self, value):
        return json.loads(value).items()

########NEW FILE########
__FILENAME__ = runtests
# -*- coding: utf-8 -*-

import os, sys
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")
sys.path.insert(0, '..')

from django.core.management import call_command

if __name__ == "__main__":
    args = sys.argv[1:]
    call_command("test", *args, verbosity=2)

########NEW FILE########
__FILENAME__ = settings
import os, sys

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
    },
    'other': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': 'test2',
        'USER': '',
        'PASSWORD': '',
        'HOST': 'localhost',
        'PORT': '',
    }
}

TIME_ZONE = 'America/Chicago'
LANGUAGE_CODE = 'en-us'
ADMIN_MEDIA_PREFIX = '/static/admin/'
STATICFILES_DIRS = ()

SECRET_KEY = 'di!n($kqa3)nd%ikad#kcjpkd^uw*h%*kj=*pm7$vbo6ir7h=l'
INSTALLED_APPS = (
    'djorm_core',
    'djorm_expressions',
    'djorm_hstore',
    'djorm_hstore.tests',
)

########NEW FILE########
