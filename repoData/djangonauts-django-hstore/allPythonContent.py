__FILENAME__ = apps
import sys

import django
from django.conf import settings
from django.db.backends.signals import connection_created

try:
    from django.apps import AppConfig
except ImportError:
    AppConfig = object

from .utils import register_hstore


class ConnectionCreateHandler(object):
    """
    Generic connection handlers manager.
    Executes attached functions when connection is created.
    With possibility of attaching single execution methods.
    """

    generic_handlers = []
    unique_handlers = []

    def __call__(self, sender, connection, **kwargs):
        handlers = set()

        if len(self.unique_handlers) > 0:
            handlers.update(self.unique_handlers)
            self.unique_handlers = []

        handlers.update(self.generic_handlers)

        # List comprehension is used instead of for statement
        # only for performance.
        [x(connection) for x in handlers]

    def attach_handler(self, func, vendor=None, unique=False):
        if unique:
            self.unique_handlers.append(func)
        else:
            self.generic_handlers.append(func)

connection_handler = ConnectionCreateHandler()


def register_hstore_handler(connection, **kwargs):
    # do not register hstore if DB is not postgres
    # do not register if HAS_HSTORE flag is set to false

    if connection.vendor != 'postgresql' or \
       connection.settings_dict.get('HAS_HSTORE', True) is False:
        return

    # if the ``NAME`` of the database in the connection settings is ``None``
    # defer hstore registration by setting up a new unique handler
    if connection.settings_dict['NAME'] is None:
        connection_handler.attach_handler(register_hstore_handler,
                                          vendor="postgresql", unique=True)
        return

    if sys.version_info[0] < 3:
        register_hstore(connection.connection, globally=True, unicode=True)
    else:
        register_hstore(connection.connection, globally=True)


# This allows users that introduce hstore to an existing
# production environment to set global registry to false for avoid
# strange behaviors when having hstore installed individually
# on each database instead of on template1.
HSTORE_GLOBAL_REGISTER = getattr(settings, "DJANGO_HSTORE_GLOBAL_REGISTER", True)

connection_handler.attach_handler(register_hstore_handler,
                                  vendor="postgresql", unique=HSTORE_GLOBAL_REGISTER)


class HStoreConfig(AppConfig):
    name = 'django_hstore'
    verbose = 'Django HStore'

    def ready(self):
        connection_created.connect(connection_handler,
                                   dispatch_uid="_connection_create_handler")

if django.get_version() < '1.7':
    HStoreConfig().ready()

########NEW FILE########
__FILENAME__ = compat
import sys


class UnicodeMixin(object):
  """
  Mixin class to handle defining the proper __str__/__unicode__
  methods in Python 2 or 3.
  """

  if sys.version_info[0] >= 3: # Python 3
      def __str__(self):
          return self.__unicode__()
  else:  # Python 2
      def __str__(self):
          return self.__unicode__().encode('utf8')

########NEW FILE########
__FILENAME__ = exceptions
from __future__ import unicode_literals, absolute_import


class HStoreDictException(Exception):
    json_error_message = None

    def __init__(self, *args, **kwargs):
        self.json_error_message = kwargs.pop('json_error_message', None)
        super(HStoreDictException, self).__init__(*args, **kwargs)

########NEW FILE########
__FILENAME__ = fields
from __future__ import unicode_literals, absolute_import

try:
    import simplejson as json
except ImportError:
    import json

from decimal import Decimal

import django
from django.db import models, connection
from django.utils import six
from django.utils.encoding import force_text
from django.utils.translation import ugettext_lazy as _

from . import forms, utils, exceptions
from .compat import UnicodeMixin


class HStoreDict(UnicodeMixin, dict):
    """
    A dictionary subclass which implements hstore support.
    """

    def __init__(self, value=None, field=None, instance=None, connection=None, **params):
        # if passed value is string
        # ensure is json formatted
        if isinstance(value, six.string_types):
            try:
                value = json.loads(value)
            except ValueError as e:
                raise exceptions.HStoreDictException(
                    'HStoreDict accepts only valid json formatted strings.',
                    json_error_message=force_text(e)
                )
        elif value is None:
            value = {}

        # allow dictionaries only
        if not isinstance(value, dict):
            raise exceptions.HStoreDictException(
                'HStoreDict accepts only dictionary objects, None and json formatted string representations of json objects'
            )

        # ensure values are acceptable
        for key, val in value.items():
            value[key] = self.ensure_acceptable_value(val)

        super(HStoreDict, self).__init__(value, **params)
        self.field = field
        self.instance = instance

        # attribute that make possible
        # to use django_hstore without a custom backend
        self.connection = connection

    def __setitem__(self, *args, **kwargs):
        args = (args[0], self.ensure_acceptable_value(args[1]))
        super(HStoreDict, self).__setitem__(*args, **kwargs)

    # This method is used both for python3 and python2
    # thanks to UnicodeMixin
    def __unicode__(self):
        if self:
            return force_text(json.dumps(self))
        return u''

    def __getstate__(self):
        if self.connection:
            d = dict(self.__dict__)
            d['connection'] = None
            return d
        return self.__dict__

    def __copy__(self):
        return self.__class__(self, self.field, self.connection)

    def update(self, *args, **kwargs):
        for key, value in dict(*args, **kwargs).iteritems():
            self[key] = value

    def ensure_acceptable_value(self, value):
        """
        - ensure booleans, integers, floats, Decimals, lists and dicts are
          converted to string
        - convert True and False objects to "true" and "false" so they can be
          decoded back with the json library if needed
        - convert lists and dictionaries to json formatted strings
        - leave alone all other objects because they might be representation of django models
        """
        if isinstance(value, bool):
            return force_text(value).lower()
        elif isinstance(value, (int, float, Decimal)):
            return force_text(value)
        elif isinstance(value, list) or isinstance(value, dict):
            return force_text(json.dumps(value))
        else:
            return value

    def prepare(self, connection):
        self.connection = connection

    def remove(self, keys):
        """
        Removes the specified keys from this dictionary.
        """
        queryset = self.instance._base_manager.get_query_set()
        queryset.filter(pk=self.instance.pk).hremove(self.field.name, keys)


class HStoreReferenceDictionary(HStoreDict):
    """
    A dictionary which adds support to storing references to models
    """
    def __getitem__(self, *args, **kwargs):
        value = super(self.__class__, self).__getitem__(*args, **kwargs)
        # if value is a string it needs to be converted to model instance
        if isinstance(value, six.string_types):
            reference = utils.acquire_reference(value)
            self.__setitem__(args[0], reference)
            return reference
        # otherwise just return the relation
        return value

    def get(self, key, default=None):
        try:
            return self.__getitem__(key)
        except KeyError:
            return default


class HStoreDescriptor(models.fields.subclassing.Creator):
    def __set__(self, obj, value):
        value = self.field.to_python(value)
        if isinstance(value, dict):
            value = HStoreDict(
                value=value, field=self.field, instance=obj
            )
        obj.__dict__[self.field.name] = value


class HStoreReferenceDescriptor(models.fields.subclassing.Creator):
    def __set__(self, obj, value):
        value = self.field.to_python(value)
        if isinstance(value, dict):
            value = HStoreReferenceDictionary(
                value=value, field=self.field, instance=obj
            )
        obj.__dict__[self.field.name] = value


class HStoreField(models.Field):
    """ HStore Base Field """

    def validate(self, value, *args):
        super(HStoreField, self).validate(value, *args)
        forms.validate_hstore(value)

    def contribute_to_class(self, cls, name):
        super(HStoreField, self).contribute_to_class(cls, name)
        setattr(cls, self.name, HStoreDescriptor(self))

    def get_default(self):
        """
        Returns the default value for this field.
        """
        if self.has_default():
            if callable(self.default):
                return HStoreDict(self.default(), self)
            elif isinstance(self.default, dict):
                return HStoreDict(self.default, self)
            return self.default
        if (not self.empty_strings_allowed or (self.null and not connection.features.interprets_empty_strings_as_nulls)):
            return None
        return HStoreDict({}, self)

    def get_prep_value(self, value):
        if isinstance(value, dict) and not isinstance(value, HStoreDict):
            return HStoreDict(value, self)
        else:
            return value

    def get_db_prep_value(self, value, connection, prepared=False):
        if not prepared:
            value = self.get_prep_value(value)
            if isinstance(value, HStoreDict):
                value.prepare(connection)
        return value

    def value_to_string(self, obj):
        return self._get_val_from_obj(obj)

    def db_type(self, connection=None):
        return 'hstore'

    def south_field_triple(self):
        from south.modelsinspector import introspector
        name = '%s.%s' % (self.__class__.__module__, self.__class__.__name__)
        args, kwargs = introspector(self)
        return name, args, kwargs


if django.get_version() >= '1.7':
    from .lookups import *

    HStoreField.register_lookup(HStoreGreaterThan)
    HStoreField.register_lookup(HStoreGreaterThanOrEqual)
    HStoreField.register_lookup(HStoreLessThan)
    HStoreField.register_lookup(HStoreLessThanOrEqual)
    HStoreField.register_lookup(HStoreContains)
    HStoreField.register_lookup(HStoreIContains)


class DictionaryField(HStoreField):
    description = _("A python dictionary in a postgresql hstore field.")

    def formfield(self, **params):
        params['form_class'] = forms.DictionaryField
        return super(DictionaryField, self).formfield(**params)

    def _value_to_python(self, value):
        return value


class ReferencesField(HStoreField):
    description = _("A python dictionary of references to model instances in an hstore field.")

    def contribute_to_class(self, cls, name):
        super(ReferencesField, self).contribute_to_class(cls, name)
        setattr(cls, self.name, HStoreReferenceDescriptor(self))

    def formfield(self, **params):
        params['form_class'] = forms.ReferencesField
        return super(ReferencesField, self).formfield(**params)

    def get_prep_lookup(self, lookup, value):
        if isinstance(value, dict):
            return utils.serialize_references(value)
        return value

    def get_prep_value(self, value):
        return utils.serialize_references(value)

    def to_python(self, value):
        return value if isinstance(value, dict) else HStoreReferenceDictionary({})

    def _value_to_python(self, value):
        return utils.acquire_reference(value)


# south compatibility
try:
    from south.modelsinspector import add_introspection_rules
    add_introspection_rules(rules=[], patterns=['django_hstore\.hstore'])
except ImportError:
    pass

########NEW FILE########
__FILENAME__ = forms
from __future__ import unicode_literals, absolute_import

try:
    import simplejson as json
except ImportError:
    import json

from django.forms import Field
from django.utils import six
from django.contrib.admin.widgets import AdminTextareaWidget
from django.utils.translation import ugettext_lazy as _
from django.utils.translation import ugettext
from django.core.exceptions import ValidationError

from .widgets import AdminHStoreWidget
from . import utils


def validate_hstore(value):
    """ HSTORE validation """
    # if empty
    if value == '' or value == 'null':
        value = '{}'

    # ensure valid JSON
    try:
        # convert strings to dictionaries
        if isinstance(value, six.string_types):
            dictionary = json.loads(value)
        # if not a string we'll check at the next control if it's a dict
        else:
            dictionary = value
    except ValueError as e:
        raise ValidationError(ugettext(u'Invalid JSON: {0}').format(e))

    # ensure is a dictionary
    if not isinstance(dictionary, dict):
        raise ValidationError(ugettext(u'No lists or values allowed, only dictionaries'))

    # convert any non string object into string
    for key, value in dictionary.items():
        if isinstance(value, dict) or isinstance(value, list):
            dictionary[key] = json.dumps(value)
        elif isinstance(value, bool) or isinstance(value, int) or isinstance(value, float):
            dictionary[key] = unicode(value).lower()

    return dictionary


class JsonMixin(object):

    def to_python(self, value):
        return validate_hstore(value)

    def render(self, name, value, attrs=None):
        # return json representation of a meaningful value
        # doesn't show anything for None, empty strings or empty dictionaries
        if value and not isinstance(value, six.string_types):
            value = json.dumps(value, sort_keys=True, indent=4)
        return super(JsonMixin, self).render(name, value, attrs)


class DictionaryFieldWidget(JsonMixin, AdminHStoreWidget):
    pass


class ReferencesFieldWidget(JsonMixin, AdminHStoreWidget):

    def render(self, name, value, attrs=None):
        value = utils.serialize_references(value)
        return super(ReferencesFieldWidget, self).render(name, value, attrs)


class DictionaryField(JsonMixin, Field):
    """
    A dictionary form field.
    """
    def __init__(self, **params):
        params['widget'] = params.get('widget', DictionaryFieldWidget)
        super(DictionaryField, self).__init__(**params)


class ReferencesField(JsonMixin, Field):
    """
    A references form field.
    """
    def __init__(self, **params):
        params['widget'] = params.get('widget', ReferencesFieldWidget)
        super(ReferencesField, self).__init__(**params)

    def to_python(self, value):
        value = super(ReferencesField, self).to_python(value)
        return utils.unserialize_references(value)

########NEW FILE########
__FILENAME__ = hstore
from django_hstore.fields import DictionaryField, ReferencesField
from django_hstore.managers import HStoreManager

try:
    from django_hstore.managers import HStoreGeoManager
except:
    # django.contrib.gis is not configured properly
    pass

########NEW FILE########
__FILENAME__ = lookups
from __future__ import unicode_literals, absolute_import

from django.db.models.fields import Field
from django.db.models.lookups import GreaterThan
from django.db.models.lookups import GreaterThanOrEqual
from django.db.models.lookups import LessThan
from django.db.models.lookups import LessThanOrEqual
from django.db.models.lookups import Contains
from django.db.models.lookups import IContains
from django.utils import six


class HStoreComparisonLookupMixin(object):
    """
    Mixin for hstore comparison custom lookups.
    """

    def as_postgresql(self, qn , connection):
        lhs, lhs_params = self.process_lhs(qn, connection)
        rhs, rhs_params = self.process_rhs(qn, connection)
        if len(rhs_params) == 1 and isinstance(rhs_params[0], dict):
            param = rhs_params[0]
            sign = (self.lookup_name[0] == 'g' and '>%s' or '<%s') % (self.lookup_name[-1] == 'e' and '=' or '')
            param_keys = list(param.keys())
            return '%s->\'%s\' %s %%s' % (lhs, param_keys[0], sign), param.values()
        raise ValueError('invalid value')


class HStoreGreaterThan(HStoreComparisonLookupMixin, GreaterThan):
    pass


class HStoreGreaterThanOrEqual(HStoreComparisonLookupMixin, GreaterThanOrEqual):
    pass


class HStoreLessThan(HStoreComparisonLookupMixin, LessThan):
    pass


class HStoreLessThanOrEqual(HStoreComparisonLookupMixin, LessThanOrEqual):
    pass


class HStoreContains(Contains):

    def as_postgresql(self, qn, connection):
        lhs, lhs_params = self.process_lhs(qn, connection)

        #FIXME: ::text cast is added by ``django.db.backends.postgresql_psycopg2.DatabaseOperations.lookup_cast``;
        # maybe there's a cleaner way to fix the cast for hstore columns
        if lhs.endswith('::text'):
            lhs = lhs[:-4] + 'hstore'

        param = self.rhs

        if isinstance(param, dict):
            values = list(param.values())
            keys = list(param.keys())

            if len(values) == 1 and isinstance(values[0], (list, tuple)):
                return '%s->\'%s\' = ANY(%%s)' % (lhs, keys[0]), [[str(x) for x in values[0]]]

            return '%s @> %%s' % lhs, [param]

        elif isinstance(param, (list, tuple)):
            if len(param) == 0:
                raise ValueError('invalid value')

            if len(param) < 2:
                return '%s ? %%s' % lhs, [param[0]]

            if param:
                return '%s ?& %%s' % lhs, [param]

        elif isinstance(param, six.string_types):
            # if looking for a string perform the normal text lookup
            # that is: look for occurence of string in all the keys
            pass
        else:
            raise ValueError('invalid value')
        return super(HStoreContains, self).as_sql(qn, connection)


class HStoreIContains(IContains, HStoreContains):
    pass
########NEW FILE########
__FILENAME__ = managers
from __future__ import unicode_literals, absolute_import

from django.db import models

from django_hstore.query import HStoreQuerySet

try:
    from django.contrib.gis.db import models as geo_models
    from django_hstore.query import HStoreGeoQuerySet
    GEODJANGO_INSTALLED = True
except:
    GEODJANGO_INSTALLED = False


class HStoreManager(models.Manager):
    """
    Object manager which enables hstore features.
    """
    use_for_related_fields = True

    def get_queryset(self):
        return HStoreQuerySet(self.model, using=self._db)

    get_query_set = get_queryset

    def hkeys(self, attr, **params):
        return self.filter(**params).hkeys(attr)

    def hpeek(self, attr, key, **params):
        return self.filter(**params).hpeek(attr, key)

    def hslice(self, attr, keys, **params):
        return self.filter(**params).hslice(attr, keys)


if GEODJANGO_INSTALLED:
    class HStoreGeoManager(geo_models.GeoManager, HStoreManager):
        """
        Object manager combining Geodjango and hstore.
        """
        def get_queryset(self):
            return HStoreGeoQuerySet(self.model, using=self._db)

        get_query_set = get_queryset

########NEW FILE########
__FILENAME__ = models
import django

if django.get_version() < '1.7':
    from .apps import *


########NEW FILE########
__FILENAME__ = query
from __future__ import unicode_literals, absolute_import

from django import VERSION
from django.db import transaction
from django.utils import six
from django.db.models.query import QuerySet
from django.db.models.sql.constants import SINGLE
from django.db.models.sql.datastructures import EmptyResultSet
from django.db.models.sql.query import Query
from django.db.models.sql.subqueries import UpdateQuery
from django.db.models.sql.where import EmptyShortCircuit, WhereNode

try:
    from django.contrib.gis.db.models.query import GeoQuerySet
    from django.contrib.gis.db.models.sql.query import GeoQuery
    from django.contrib.gis.db.models.sql.where import \
        GeoWhereNode, GeoConstraint
    GEODJANGO_INSTALLED = True
except:
    GEODJANGO_INSTALLED = False


class literal_clause(object):
    def __init__(self, sql, params):
        self.clause = (sql, params)

    def as_sql(self, qn, connection):
        return self.clause


try:
    from django.db.models.query_utils import QueryWrapper  # django >= 1.4
except ImportError:
    from django.db.models.sql.where import QueryWrapper  # django <= 1.3


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
        query = method(self, self.query.clone(UpdateQuery), *args, **params)
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


class HStoreWhereNode(WhereNode):

    # FIXME: this method shuld be more clear.
    def make_atom(self, child, qn, connection):
        lvalue, lookup_type, value_annot, param = child
        kwargs = {'connection': connection} if VERSION[:2] >= (1, 3) else {}

        if lvalue and lvalue.field and hasattr(lvalue.field, 'db_type') and lvalue.field.db_type(**kwargs) == 'hstore':
            try:
                lvalue, params = lvalue.process(lookup_type, param, connection)
            except EmptyShortCircuit:
                raise EmptyResultSet()

            field = self.sql_for_columns(lvalue, qn, connection)

            if lookup_type == 'exact':
                if isinstance(param, dict):
                    return ('{0} = %s'.format(field), [param])

                raise ValueError('invalid value')

            elif lookup_type in ('gt', 'gte', 'lt', 'lte'):
                if isinstance(param, dict) and len(param) == 1:
                    sign = (lookup_type[0] == 'g' and '>%s' or '<%s') % (lookup_type[-1] == 'e' and '=' or '')
                    param_keys = list(param.keys())
                    return ('%s->\'%s\' %s %%s' % (field, param_keys[0], sign), param.values())

                raise ValueError('invalid value')

            elif lookup_type in ['contains', 'icontains']:
                if isinstance(param, dict):
                    values = list(param.values())
                    keys = list(param.keys())

                    if len(values) == 1 and isinstance(values[0], (list, tuple)):
                        return ('%s->\'%s\' = ANY(%%s)' % (field, keys[0]), [[str(x) for x in values[0]]])

                    return ('%s @> %%s' % field, [param])

                elif isinstance(param, (list, tuple)):
                    if len(param) == 0:
                        raise ValueError('invalid value')
                    
                    if len(param) < 2:
                        return ('%s ? %%s' % field, [param[0]])

                    if param:
                        return ('%s ?& %%s' % field, [param])

                    raise ValueError('invalid value')

                elif isinstance(param, six.string_types):
                    # if looking for a string perform the normal text lookup
                    # that is: look for occurence of string in all the keys
                    pass

                else:
                    raise ValueError('invalid value')

            elif lookup_type == 'isnull':
                # do not perform any special format
                return super(HStoreWhereNode, self).make_atom(child, qn, connection)

            else:
                raise TypeError('invalid lookup type')

        return super(HStoreWhereNode, self).make_atom(child, qn, connection)

    make_hstore_atom = make_atom


if GEODJANGO_INSTALLED:
    class HStoreGeoWhereNode(HStoreWhereNode, GeoWhereNode):

        def make_atom(self, child, qn, connection):
            lvalue, lookup_type, value_annot, params_or_value = child

            # if spatial query
            if isinstance(lvalue, GeoConstraint):
                return GeoWhereNode.make_atom(self, child, qn, connection)

            # else might be an HSTORE query
            return HStoreWhereNode.make_atom(self, child, qn, connection)


class HStoreQuery(Query):

    def __init__(self, model):
        super(HStoreQuery, self).__init__(model, HStoreWhereNode)


if GEODJANGO_INSTALLED:
    class HStoreGeoQuery(GeoQuery, Query):

        def __init__(self, *args, **kwargs):
            model = kwargs.pop('model', None) or args[0]
            super(HStoreGeoQuery, self).__init__(model, HStoreGeoWhereNode)


class HStoreQuerySet(QuerySet):

    def __init__(self, model=None, query=None, using=None, *args, **kwargs):
        query = query or HStoreQuery(model)
        super(HStoreQuerySet, self).__init__(model=model, query=query, using=using, *args, **kwargs)

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


if GEODJANGO_INSTALLED:
    class HStoreGeoQuerySet(HStoreQuerySet, GeoQuerySet):

        def __init__(self, model=None, query=None, using=None, **kwargs):
            query = query or HStoreGeoQuery(model)
            super(HStoreGeoQuerySet, self).__init__(model=model, query=query, using=using, **kwargs)

########NEW FILE########
__FILENAME__ = utils
from __future__ import unicode_literals, absolute_import

from django.core.exceptions import ObjectDoesNotExist
from django.utils import six


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
    # if None or string return empty dict
    if references is None or isinstance(references, six.string_types):
        return {}
    # if dictionary do serialization
    elif isinstance(references, dict):
        for key, instance in references.items():
            if not isinstance(instance, six.string_types):
                refs[key] = identify_instance(instance)
            else:
                refs[key] = instance
        else:
            return refs
    # else just return the object, might be doing some other operation and we don't want to interfere
    else:
        return references


def unserialize_references(references):
    refs = {}
    if references is None:
        return refs
    for key, reference in references.items():
        if isinstance(reference, six.string_types):
            refs[key] = acquire_reference(reference)
        else:
            refs[key] = reference
    else:
        return refs


def register_hstore(conn_or_curs, globally=False, unicode=False,
        oid=None, array_oid=None):
    from psycopg2.extras import HstoreAdapter
    from psycopg2 import extensions as _ext
    import psycopg2
    import sys
    import re as regex
    from .fields import HStoreDict

    def cast(s, cur, _bsdec=regex.compile(r"\\(.)")):
        if sys.version_info[0] < 3 and unicode:
            result = HstoreAdapter.parse_unicode(s, cur)
        else:
            result = HstoreAdapter.parse(s, cur, _bsdec)
        return HStoreDict(result)

    if oid is None:
        oid = HstoreAdapter.get_oids(conn_or_curs)
        if oid is None or not oid[0]:
            raise psycopg2.ProgrammingError(
                "hstore type not found in the database. "
                "please install it from your 'contrib/hstore.sql' file")
        else:
            array_oid = oid[1]
            oid = oid[0]

    if isinstance(oid, int):
        oid = (oid,)

    if array_oid is not None:
        if isinstance(array_oid, int):
            array_oid = (array_oid,)
        else:
            array_oid = tuple([x for x in array_oid if x])

    HSTORE = _ext.new_type(oid, str("HSTORE"), cast)
    _ext.register_type(HSTORE, not globally and conn_or_curs or None)
    _ext.register_adapter(dict, HstoreAdapter)

    if array_oid:
        HSTOREARRAY = _ext.new_array_type(array_oid, str("HSTOREARRAY"), HSTORE)
        _ext.register_type(HSTOREARRAY, not globally and conn_or_curs or None)

########NEW FILE########
__FILENAME__ = widgets
from __future__ import unicode_literals, absolute_import

from django import forms
from django.contrib.admin.widgets import AdminTextareaWidget
from django.contrib.admin.templatetags.admin_static import static
from django.template import Context
from django.template.loader import get_template
from django.utils.safestring import mark_safe
from django.conf import settings


__all__ = [
    'AdminHStoreWidget'
]


class BaseAdminHStoreWidget(AdminTextareaWidget):
    """
    Base admin widget class for default-admin and grappelli-admin widgets
    """
    admin_style = 'default'

    @property
    def media(self):
        # load underscore from CDNJS (popular javascript content delivery network)
        external_js = [
            "//cdnjs.cloudflare.com/ajax/libs/underscore.js/1.5.2/underscore-min.js"
        ]

        internal_js = [
            "django_hstore/hstore-widget.js"
        ]

        js = external_js + [static("admin/js/%s" % path) for path in internal_js]

        return forms.Media(js=js)

    def render(self, name, value, attrs=None):
        if attrs is None:
            attrs = {}
        # it's called "original" because it will be replaced by a copy
        attrs['class'] = 'hstore-original-textarea'

        # get default HTML from AdminTextareaWidget
        html = super(BaseAdminHStoreWidget, self).render(name, value, attrs)

        # prepare template context
        template_context = Context({
            'field_name': name,
            'STATIC_URL': settings.STATIC_URL
        })
        # get template object
        template = get_template('hstore_%s_widget.html' % self.admin_style)
        # render additional html
        additional_html = template.render(template_context)

        # append additional HTML and mark as safe
        html = html + additional_html
        html = mark_safe(html)

        return html


class DefaultAdminHStoreWidget(BaseAdminHStoreWidget):
    """
    Widget that displays the HStore contents
    in the default django-admin with a nice interactive UI
    """
    admin_style = 'default'


class GrappelliAdminHStoreWidget(BaseAdminHStoreWidget):
    """
    Widget that displays the HStore contents
    in the django-admin with a nice interactive UI
    designed for django-grappelli
    """
    admin_style = 'grappelli'


if 'grappelli' in settings.INSTALLED_APPS:
    AdminHStoreWidget = GrappelliAdminHStoreWidget
else:
    AdminHStoreWidget = DefaultAdminHStoreWidget

########NEW FILE########
__FILENAME__ = runtests
#!/usr/bin/env python
# -*- coding: utf-8 -*-


import os, sys
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")
sys.path.insert(0, "tests")

if __name__ == "__main__":
    from django.core.management import execute_from_command_line
    args = sys.argv
    args.insert(1, "test")
    execute_from_command_line(args)

########NEW FILE########
__FILENAME__ = admin
from django.contrib import admin
from .models import *


class DataBagAdmin(admin.ModelAdmin):
    pass


class DefaultsInlineAdmin(admin.StackedInline):
    model = DefaultsInline
    extra = 0


class DefaultsModelAdmin(admin.ModelAdmin):
    inlines = [DefaultsInlineAdmin]


class RefsBagAdmin(admin.ModelAdmin):
    pass


admin.site.register(DataBag, DataBagAdmin)
admin.site.register(DefaultsModel, DefaultsModelAdmin)
admin.site.register(RefsBag, RefsBagAdmin)
########NEW FILE########
__FILENAME__ = models
from django.db import models
from django.conf import settings

from django_hstore import hstore

# determine if geodjango is in use
GEODJANGO = settings.DATABASES['default']['ENGINE'] == 'django.contrib.gis.db.backends.postgis'


__all__ = [
    'Ref',
    'DataBag',
    'NullableDataBag',
    'RefsBag',
    'NullableRefsBag',
    'DefaultsModel',
    'BadDefaultsModel',
    'DefaultsInline',
    'NumberedDataBag',
    'GEODJANGO'
]


class Ref(models.Model):
    name = models.CharField(max_length=32)


class HStoreModel(models.Model):
    objects = hstore.HStoreManager()

    class Meta:
        abstract = True


class DataBag(HStoreModel):
    name = models.CharField(max_length=32)
    data = hstore.DictionaryField()


class NullableDataBag(HStoreModel):
    name = models.CharField(max_length=32)
    data = hstore.DictionaryField(null=True)

class RefsBag(HStoreModel):
    name = models.CharField(max_length=32)
    refs = hstore.ReferencesField()


class NullableRefsBag(HStoreModel):
    name = models.CharField(max_length=32)
    refs = hstore.ReferencesField(null=True, blank=True)


class DefaultsModel(models.Model):
    a = hstore.DictionaryField(default={})
    b = hstore.DictionaryField(default=None, null=True)
    c = hstore.DictionaryField(default={'x': '1'})


class BadDefaultsModel(models.Model):
    a = hstore.DictionaryField(default=None)


class DefaultsInline(models.Model):
    parent = models.ForeignKey(DefaultsModel)
    d = hstore.DictionaryField(default={ 'default': 'yes' })


class NumberedDataBag(HStoreModel):
    name = models.CharField(max_length=32)
    data = hstore.DictionaryField()
    number = models.IntegerField()


# if geodjango is in use define Location model, which contains GIS data
if GEODJANGO:
    from django.contrib.gis.db import models as geo_models
    class Location(geo_models.Model):
        name = geo_models.CharField(max_length=32)
        data = hstore.DictionaryField()
        point = geo_models.GeometryField()
    
        objects = hstore.HStoreGeoManager()
    
    __all__.append('Location')

########NEW FILE########
__FILENAME__ = tests
import json
import pickle
from decimal import Decimal

from django.db import transaction
from django.db.models.aggregates import Count
from django.db.utils import IntegrityError, DatabaseError
from django import forms
from django.core.urlresolvers import reverse
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.contrib.auth.models import User
from django.utils.encoding import force_text

from django_hstore import get_version
from django_hstore.forms import DictionaryFieldWidget, ReferencesFieldWidget
from django_hstore.fields import HStoreDict
from django_hstore.exceptions import HStoreDictException
from django_hstore.utils import unserialize_references, serialize_references, acquire_reference

from django_hstore_tests.models import *


class TestDictionaryField(TestCase):
    def setUp(self):
        DataBag.objects.all().delete()
        Ref.objects.all().delete()
        RefsBag.objects.all().delete()

    def _create_bags(self):
        alpha = DataBag.objects.create(name='alpha', data={'v': '1', 'v2': '3'})
        beta = DataBag.objects.create(name='beta', data={'v': '2', 'v2': '4'})
        return alpha, beta

    def _create_bitfield_bags(self):
        # create dictionaries with bits as dictionary keys (i.e. bag5 = { 'b0':'1', 'b2':'1'})
        for i in range(10):
            DataBag.objects.create(name='bag%d' % (i,),
                                   data=dict(('b%d' % (bit,), '1') for bit in range(4) if (1 << bit) & i))

    def test_hstore_dict(self):
        alpha, beta = self._create_bags()
        self.assertEqual(alpha.data, {'v': '1', 'v2': '3'})
        self.assertEqual(beta.data, {'v': '2', 'v2': '4'})

    def test_decimal(self):
        databag = DataBag(name='decimal')
        databag.data['dec'] = Decimal('1.01')
        self.assertEqual(databag.data['dec'], force_text(Decimal('1.01')))

        databag.save()
        databag = DataBag.objects.get(name='decimal')
        self.assertEqual(databag.data['dec'], force_text(Decimal('1.01')))

        databag = DataBag(name='decimal', data={'dec': Decimal('1.01')})
        self.assertEqual(databag.data['dec'], force_text(Decimal('1.01')))

    def test_number(self):
        databag = DataBag(name='number')
        databag.data['num'] = 1
        self.assertEqual(databag.data['num'], '1')

        databag.save()
        databag = DataBag.objects.get(name='number')
        self.assertEqual(databag.data['num'], '1')

        databag = DataBag(name='number', data={ 'num': 1 })
        self.assertEqual(databag.data['num'], '1')

    def test_list(self):
        databag = DataBag.objects.create(name='list', data={ 'list': ['a', 'b', 'c'] })
        databag = DataBag.objects.get(name='list')
        self.assertEqual(json.loads(databag.data['list']), ['a', 'b', 'c'])

    def test_dictionary(self):
        databag = DataBag.objects.create(name='dict', data={ 'dict': {'subkey': 'subvalue'} })
        databag = DataBag.objects.get(name='dict')
        self.assertEqual(json.loads(databag.data['dict']), {'subkey': 'subvalue'})

        databag.data['dict'] = {'subkey': True, 'list': ['a', 'b', False]}
        databag.save()
        self.assertEqual(json.loads(databag.data['dict']), {'subkey': True, 'list': ['a', 'b', False]})

    def test_boolean(self):
        databag = DataBag.objects.create(name='boolean', data={ 'boolean': True })
        databag = DataBag.objects.get(name='boolean')
        self.assertEqual(json.loads(databag.data['boolean']), True)

    def test_is_pickable(self):
        m = DefaultsModel()
        m.save()
        try:
            pickle.dumps(m)
        except TypeError as e:
            self.fail('pickle of DefaultsModel failed: %s' % e)

    def test_empty_instantiation(self):
        bag = DataBag.objects.create(name='bag')
        self.assertTrue(isinstance(bag.data, dict))
        self.assertEqual(bag.data, {})

    def test_empty_querying(self):
        DataBag.objects.create(name='bag')
        self.assertTrue(DataBag.objects.get(data={}))
        self.assertTrue(DataBag.objects.filter(data={}))
        self.assertTrue(DataBag.objects.filter(data__contains={}))

    def test_nullable_queryinig(self):
        NullableDataBag.objects.create(name='nullable')
        self.assertTrue(NullableDataBag.objects.get(data=None))
        self.assertTrue(NullableDataBag.objects.filter(data__exact=None))
        self.assertTrue(NullableDataBag.objects.filter(data__isnull=True))
        self.assertFalse(NullableDataBag.objects.filter(data__isnull=False))

    def test_named_querying(self):
        alpha, beta = self._create_bags()
        self.assertEqual(DataBag.objects.get(name='alpha'), alpha)
        self.assertEqual(DataBag.objects.filter(name='beta')[0], beta)

    def test_aggregates(self):
        self._create_bitfield_bags()

        self.assertEqual(DataBag.objects.filter(data__contains={'b0': '1'}).aggregate(Count('id'))['id__count'], 5)
        self.assertEqual(DataBag.objects.filter(data__contains={'b1': '1'}).aggregate(Count('id'))['id__count'], 4)

    def test_annotations(self):
        self._create_bitfield_bags()

        self.assertEqual(DataBag.objects.annotate(num_id=Count('id')).filter(num_id=1)[0].num_id, 1)

    def test_nested_filtering(self):
        self._create_bitfield_bags()

        # Test cumulative successive filters for both dictionaries and other fields
        f = DataBag.objects.all()
        self.assertEqual(10, f.count())
        f = f.filter(data__contains={'b0': '1'})
        self.assertEqual(5, f.count())
        f = f.filter(data__contains={'b1': '1'})
        self.assertEqual(2, f.count())
        f = f.filter(name='bag3')
        self.assertEqual(1, f.count())

    def test_unicode_processing(self):
        greets = {
            u'de': u'Gr\xfc\xdfe, Welt',
            u'en': u'hello, world',
            u'es': u'hola, ma\xf1ana',
            u'he': u'\u05e9\u05dc\u05d5\u05dd, \u05e2\u05d5\u05dc\u05dd',
            u'jp': u'\u3053\u3093\u306b\u3061\u306f\u3001\u4e16\u754c',
            u'zh': u'\u4f60\u597d\uff0c\u4e16\u754c',
        }
        DataBag.objects.create(name='multilang', data=greets)
        self.assertEqual(greets, DataBag.objects.get(name='multilang').data)

    def test_query_escaping(self):
        me = self

        def readwrite(s):
            # try create and query with potentially illegal characters in the field and dictionary key/value
            o = DataBag.objects.create(name=s, data={s: s})
            me.assertEqual(o, DataBag.objects.get(name=s, data={s: s}))
        readwrite('\' select')
        readwrite('% select')
        readwrite('\\\' select')
        readwrite('-- select')
        readwrite('\n select')
        readwrite('\r select')
        readwrite('* select')

    def test_replace_full_dictionary(self):
        DataBag.objects.create(name='foo', data={'change': 'old value', 'remove': 'baz'})

        replacement = {'change': 'new value', 'added': 'new'}
        DataBag.objects.filter(name='foo').update(data=replacement)
        self.assertEqual(replacement, DataBag.objects.get(name='foo').data)

    def test_equivalence_querying(self):
        alpha, beta = self._create_bags()
        for bag in (alpha, beta):
            data = {'v': bag.data['v'], 'v2': bag.data['v2']}
            self.assertEqual(DataBag.objects.get(data=data), bag)
            r = DataBag.objects.filter(data=data)
            self.assertEqual(len(r), 1)
            self.assertEqual(r[0], bag)

    def test_key_value_subset_querying(self):
        alpha, beta = self._create_bags()
        for bag in (alpha, beta):
            r = DataBag.objects.filter(data__contains={'v': bag.data['v']})
            self.assertEqual(len(r), 1)
            self.assertEqual(r[0], bag)
            r = DataBag.objects.filter(data__contains={'v': bag.data['v'], 'v2': bag.data['v2']})
            self.assertEqual(len(r), 1)
            self.assertEqual(r[0], bag)

    def test_value_in_subset_querying(self):
        alpha, beta = self._create_bags()
        res = DataBag.objects.filter(data__contains={'v': [alpha.data['v']]})
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0], alpha)
        res = DataBag.objects.filter(data__contains={'v': [alpha.data['v'], beta.data['v']]})
        self.assertEqual(len(res), 2)
        self.assertEqual(set(res), set([alpha, beta]))

        # int values are ok
        r = DataBag.objects.filter(data__contains={'v': [int(alpha.data['v'])]})
        self.assertEqual(len(r), 1)
        self.assertEqual(r[0], alpha)

    def test_key_value_gt_querying(self):
        alpha, beta = self._create_bags()
        self.assertGreater(beta.data['v'], alpha.data['v'])
        r = DataBag.objects.filter(data__gt={'v': alpha.data['v']})
        self.assertEqual(len(r), 1)
        self.assertEqual(r[0], beta)
        r = DataBag.objects.filter(data__gte={'v': alpha.data['v']})
        self.assertEqual(len(r), 2)

    def test_key_value_lt_querying(self):
        alpha, beta = self._create_bags()
        self.assertLess(alpha.data['v'], beta.data['v'])
        r = DataBag.objects.filter(data__lt={'v': beta.data['v']})
        self.assertEqual(len(r), 1)
        self.assertEqual(r[0], alpha)
        r = DataBag.objects.filter(data__lte={'v': beta.data['v']})
        self.assertEqual(len(r), 2)

    def test_multiple_key_subset_querying(self):
        alpha, beta = self._create_bags()
        for keys in (['v'], ['v', 'v2']):
            self.assertEqual(DataBag.objects.filter(data__contains=keys).count(), 2)
        for keys in (['v', 'nv'], ['n1', 'n2']):
            self.assertEqual(DataBag.objects.filter(data__contains=keys).count(), 0)

    def test_single_key_querying(self):
        alpha, beta = self._create_bags()
        for key in ('v', 'v2'):
            self.assertEqual(DataBag.objects.filter(data__contains=[key]).count(), 2)
        for key in ('n1', 'n2'):
            self.assertEqual(DataBag.objects.filter(data__contains=[key]).count(), 0)

    def test_simple_text_icontains_querying(self):
        alpha, beta = self._create_bags()
        gamma = DataBag.objects.create(name='gamma', data={'theKey': 'someverySpecialValue', 'v2': '3'})

        self.assertEqual(DataBag.objects.filter(data__contains='very').count(), 1)
        self.assertEqual(DataBag.objects.filter(data__contains='very')[0].name, 'gamma')
        self.assertEqual(DataBag.objects.filter(data__icontains='specialvalue').count(), 1)
        self.assertEqual(DataBag.objects.filter(data__icontains='specialvalue')[0].name, 'gamma')

        self.assertEqual(DataBag.objects.filter(data__contains='the').count(), 1)
        self.assertEqual(DataBag.objects.filter(data__contains='the')[0].name, 'gamma')
        self.assertEqual(DataBag.objects.filter(data__icontains='eke').count(), 1)
        self.assertEqual(DataBag.objects.filter(data__icontains='eke')[0].name, 'gamma')

    def test_invalid_containment_lookup_values(self):
        alpha, beta = self._create_bags()
        with self.assertRaises(ValueError):
            DataBag.objects.filter(data__contains=99)[0]
        with self.assertRaises(ValueError):
            DataBag.objects.filter(data__icontains=99)[0]
        with self.assertRaises(ValueError):
            DataBag.objects.filter(data__icontains=[])[0]

    def test_invalid_comparison_lookup_values(self):
        alpha, beta = self._create_bags()
        with self.assertRaises(ValueError):
            DataBag.objects.filter(data__lt=[1,2])[0]
        with self.assertRaises(ValueError):
            DataBag.objects.filter(data__lt=99)[0]
        with self.assertRaises(ValueError):
            DataBag.objects.filter(data__lte=[1,2])[0]
        with self.assertRaises(ValueError):
            DataBag.objects.filter(data__lte=99)[0]
        with self.assertRaises(ValueError):
            DataBag.objects.filter(data__gt=[1,2])[0]
        with self.assertRaises(ValueError):
            DataBag.objects.filter(data__gt=99)[0]
        with self.assertRaises(ValueError):
            DataBag.objects.filter(data__gte=[1,2])[0]
        with self.assertRaises(ValueError):
            DataBag.objects.filter(data__gte=99)[0]

    def test_hkeys(self):
        alpha, beta = self._create_bags()
        self.assertEqual(DataBag.objects.hkeys(id=alpha.id, attr='data'), ['v', 'v2'])
        self.assertEqual(DataBag.objects.hkeys(id=beta.id, attr='data'), ['v', 'v2'])

    def test_hpeek(self):
        alpha, beta = self._create_bags()
        self.assertEqual(DataBag.objects.hpeek(id=alpha.id, attr='data', key='v'), '1')
        self.assertEqual(DataBag.objects.filter(id=alpha.id).hpeek(attr='data', key='v'), '1')
        self.assertEqual(DataBag.objects.hpeek(id=alpha.id, attr='data', key='invalid'), None)

    def test_hremove(self):
        alpha, beta = self._create_bags()
        self.assertEqual(DataBag.objects.get(name='alpha').data, alpha.data)
        DataBag.objects.filter(name='alpha').hremove('data', 'v2')
        self.assertEqual(DataBag.objects.get(name='alpha').data, {'v': '1'})

        self.assertEqual(DataBag.objects.get(name='beta').data, beta.data)
        DataBag.objects.filter(name='beta').hremove('data', ['v', 'v2'])
        self.assertEqual(DataBag.objects.get(name='beta').data, {})

    def test_hslice(self):
        alpha, beta = self._create_bags()
        self.assertEqual(DataBag.objects.hslice(id=alpha.id, attr='data', keys=['v']), {'v': '1'})
        self.assertEqual(DataBag.objects.filter(id=alpha.id).hslice(attr='data', keys=['v']), {'v': '1'})
        self.assertEqual(DataBag.objects.hslice(id=alpha.id, attr='data', keys=['ggg']), {})

    def test_hupdate(self):
        alpha, beta = self._create_bags()
        self.assertEqual(DataBag.objects.get(name='alpha').data, alpha.data)
        DataBag.objects.filter(name='alpha').hupdate('data', {'v2': '10', 'v3': '20'})
        self.assertEqual(DataBag.objects.get(name='alpha').data, {'v': '1', 'v2': '10', 'v3': '20'})

    def test_default(self):
        m = DefaultsModel()
        m.save()

    def test_bad_default(self):
        m = BadDefaultsModel()
        try:
            m.save()
        except IntegrityError:
            transaction.rollback()
        else:
            self.assertTrue(False)

    def test_serialization_deserialization(self):
        alpha, beta = self._create_bags()
        self.assertEqual(json.loads(str(DataBag.objects.get(name='alpha').data)), json.loads(str(alpha.data)))
        self.assertEqual(json.loads(str(DataBag.objects.get(name='beta').data)), json.loads(str(beta.data)))

    def test_hstoredictionaryexception(self):
        # ok
        HStoreDict({})

        # json object string allowed
        HStoreDict('{}')

        # None is ok, will be converted to empty dict
        HStoreDict(None)
        HStoreDict()

        # non-json string not allowed
        with self.assertRaises(HStoreDictException):
            HStoreDict('wrong')

        # list not allowed
        with self.assertRaises(HStoreDictException):
            HStoreDict(['wrong'])

        # json array string representation not allowed
        with self.assertRaises(HStoreDictException):
            HStoreDict('["wrong"]')

        # number not allowed
        with self.assertRaises(HStoreDictException):
            HStoreDict(3)

    def test_hstoredictionary_unicoce_vs_str(self):
        d = HStoreDict({ 'test': 'test' })
        self.assertEqual(d.__str__(), d.__unicode__())

    def test_hstore_model_field_validation(self):
        d = DataBag()

        with self.assertRaises(ValidationError):
            d.full_clean()

        d.data = 'test'

        with self.assertRaises(ValidationError):
            d.full_clean()

        d.data = '["test"]'

        with self.assertRaises(ValidationError):
            d.full_clean()

        d.data = ["test"]

        with self.assertRaises(ValidationError):
            d.full_clean()

        d.data = {
            'a': 1,
            'b': 2.2,
            'c': ['a', 'b'],
            'd': { 'test': 'test' }
        }

        with self.assertRaises(ValidationError):
            d.full_clean()

    def test_admin_widget(self):
        alpha, beta = self._create_bags()

        # create admin user
        admin = User.objects.create(username='admin', password='tester', is_staff=True, is_superuser=True, is_active=True)
        admin.set_password('tester')
        admin.save()
        # login as admin
        self.client.login(username='admin', password='tester')

        # access admin change form page
        url = reverse('admin:django_hstore_tests_databag_change', args=[alpha.id])
        response = self.client.get(url)
        # ensure textarea with id="id_data" is there
        self.assertContains(response, 'textarea')
        self.assertContains(response, 'id_data')

    def test_dictionary_default_admin_widget(self):
        class HForm(forms.ModelForm):
            class Meta:
                model = DataBag
                exclude = []

        form = HForm()
        self.assertEqual(form.fields['data'].widget.__class__, DictionaryFieldWidget)

    def test_dictionary_custom_admin_widget(self):
        class CustomWidget(forms.Widget):
            pass

        class HForm(forms.ModelForm):
            class Meta:
                model = DataBag
                widgets = {'data': CustomWidget}
                exclude = []

        form = HForm()
        self.assertEqual(form.fields['data'].widget.__class__, CustomWidget)

    def test_references_default_admin_widget(self):
        class HForm(forms.ModelForm):
            class Meta:
                model = RefsBag
                exclude = []

        form = HForm()
        self.assertEqual(form.fields['refs'].widget.__class__, ReferencesFieldWidget)

    def test_references_custom_admin_widget(self):
        class CustomWidget(forms.Widget):
            pass

        class HForm(forms.ModelForm):
            class Meta:
                model = RefsBag
                widgets = {'refs': CustomWidget}
                exclude = []

        form = HForm()
        self.assertEqual(form.fields['refs'].widget.__class__, CustomWidget)

    def test_get_version(self):
        get_version()


class RegressionTests(TestCase):
    def test_properties_hstore(self):
        """
        Make sure the hstore field does what it is supposed to.
        """
        from django_hstore.fields import HStoreDict

        instance = DataBag()
        test_props = {'foo':'bar', 'size': '3'}

        instance.name = "foo"
        instance.data = test_props
        instance.save()

        self.assertEqual(type(instance.data), HStoreDict)
        self.assertEqual(instance.data, test_props)
        instance = DataBag.objects.get(pk=instance.pk)

        self.assertEqual(type(instance.data), HStoreDict) # TEST FAILS HERE

        self.assertEqual(instance.data, test_props)
        self.assertEqual(instance.data['size'], '3')
        self.assertIn('foo', instance.data)


class TestReferencesField(TestCase):

    def setUp(self):
        Ref.objects.all().delete()
        RefsBag.objects.all().delete()

    def _create_bags(self):
        refs = [Ref.objects.create(name=str(i)) for i in range(4)]
        alpha = RefsBag.objects.create(name='alpha', refs={'0': refs[0], '1': refs[1]})
        beta = RefsBag.objects.create(name='beta', refs={'0': refs[2], '1': refs[3]})
        return alpha, beta, refs

    def test_empty_instantiation(self):
        bag = RefsBag.objects.create(name='bag')
        self.assertTrue(isinstance(bag.refs, dict))
        self.assertEqual(bag.refs, {})

    def test_unsaved_empty_instantiation(self):
        bag = RefsBag(name='bag')
        self.assertEqual(bag.refs.get('idontexist', 'default'), 'default')
        self.assertTrue(isinstance(bag.refs, dict))

    def test_unsave_empty_instantiation_of_nullable_ref(self):
        bag = NullableRefsBag(name='bag')
        self.assertEqual(bag.refs.get('idontexist', 'default'), 'default')
        self.assertTrue(isinstance(bag.refs, dict))

    def test_simple_retrieval(self):
        alpha, beta, refs = self._create_bags()
        alpha = RefsBag.objects.get(name='alpha')
        self.assertEqual(Ref.objects.get(name='0'), alpha.refs['0'])

    def test_simple_retrieval_get(self):
        alpha, beta, refs = self._create_bags()
        alpha = RefsBag.objects.get(name='alpha')
        self.assertEqual(Ref.objects.get(name='0'), alpha.refs.get('0'))

        # try getting a non existent key
        self.assertEqual(alpha.refs.get('idontexist', 'default'), 'default')
        self.assertEqual(alpha.refs.get('idontexist'), None)

    def test_empty_querying(self):
        RefsBag.objects.create(name='bag')
        self.assertTrue(RefsBag.objects.get(refs={}))
        self.assertTrue(RefsBag.objects.filter(refs={}))
        self.assertTrue(RefsBag.objects.filter(refs__contains={}))

    def test_equivalence_querying(self):
        alpha, beta, refs = self._create_bags()
        for bag in (alpha, beta):
            refs = {'0': bag.refs['0'], '1': bag.refs['1']}
            self.assertEqual(RefsBag.objects.get(refs=refs), bag)
            r = RefsBag.objects.filter(refs=refs)
            self.assertEqual(len(r), 1)
            self.assertEqual(r[0], bag)

    def test_key_value_subset_querying(self):
        alpha, beta, refs = self._create_bags()
        for bag in (alpha, beta):
            r = RefsBag.objects.filter(refs__contains={'0': bag.refs['0']})
            self.assertEqual(len(r), 1)
            self.assertEqual(r[0], bag)
            r = RefsBag.objects.filter(refs__contains={'0': bag.refs['0'], '1': bag.refs['1']})
            self.assertEqual(len(r), 1)
            self.assertEqual(r[0], bag)

    def test_multiple_key_subset_querying(self):
        alpha, beta, refs = self._create_bags()
        for keys in (['0'], ['0', '1']):
            self.assertEqual(RefsBag.objects.filter(refs__contains=keys).count(), 2)
        for keys in (['0', 'nv'], ['n1', 'n2']):
            self.assertEqual(RefsBag.objects.filter(refs__contains=keys).count(), 0)

    def test_single_key_querying(self):
        alpha, beta, refs = self._create_bags()
        for key in ('0', '1'):
            self.assertEqual(RefsBag.objects.filter(refs__contains=[key]).count(), 2)
        for key in ('n1', 'n2'):
            self.assertEqual(RefsBag.objects.filter(refs__contains=[key]).count(), 0)

    def test_hkeys(self):
        alpha, beta, refs = self._create_bags()
        self.assertEqual(RefsBag.objects.hkeys(id=alpha.id, attr='refs'), ['0', '1'])

    def test_hpeek(self):
        alpha, beta, refs = self._create_bags()
        self.assertEqual(RefsBag.objects.hpeek(id=alpha.id, attr='refs', key='0'), refs[0])
        self.assertEqual(RefsBag.objects.filter(id=alpha.id).hpeek(attr='refs', key='0'), refs[0])
        self.assertEqual(RefsBag.objects.hpeek(id=alpha.id, attr='refs', key='invalid'), None)

    def test_hremove(self):
        alpha, beta, refs = self._create_bags()
        self.assertEqual(RefsBag.objects.get(name='alpha').refs['0'], alpha.refs['0'])
        self.assertEqual(RefsBag.objects.get(name='alpha').refs['1'], alpha.refs['1'])
        self.assertIn("0", RefsBag.objects.get(name='alpha').refs)
        RefsBag.objects.filter(name='alpha').hremove('refs', '0')
        self.assertNotIn("0", RefsBag.objects.get(name='alpha').refs)
        self.assertIn("1", RefsBag.objects.get(name='alpha').refs)

        self.assertEqual(RefsBag.objects.get(name='beta').refs['0'], beta.refs['0'])
        self.assertEqual(RefsBag.objects.get(name='beta').refs['1'], beta.refs['1'])
        RefsBag.objects.filter(name='beta').hremove('refs', ['0', '1'])
        self.assertEqual(RefsBag.objects.get(name='beta').refs, {})

    def test_hslice(self):
        alpha, beta, refs = self._create_bags()
        self.assertEqual(RefsBag.objects.hslice(id=alpha.id, attr='refs', keys=['0']), {'0': refs[0]})
        self.assertEqual(RefsBag.objects.filter(id=alpha.id).hslice(attr='refs', keys=['0']), {'0': refs[0]})
        self.assertEqual(RefsBag.objects.hslice(id=alpha.id, attr='refs', keys=['invalid']), {})

    def test_admin_reference_field(self):
        alpha, beta, refs = self._create_bags()

        # create admin user
        admin = User.objects.create(username='admin', password='tester', is_staff=True, is_superuser=True, is_active=True)
        admin.set_password('tester')
        admin.save()
        # login as admin
        self.client.login(username='admin', password='tester')

        # access admin change form page
        url = reverse('admin:django_hstore_tests_refsbag_change', args=[alpha.id])
        response = self.client.get(url)
        # ensure textarea with id="id_data" is there
        self.assertContains(response, 'textarea')
        self.assertContains(response, 'id_refs')

    def test_unserialize_references_edge_cases(self):
        alpha, beta, refs = self._create_bags()

        refs = unserialize_references(alpha.refs)
        # repeat
        refs = unserialize_references(alpha.refs)
        self.assertEqual(len(unserialize_references(refs).keys()), 2)
        self.assertEqual(unserialize_references(None), {})

    def test_serialize_references_edge_cases(self):
        self.assertEqual(serialize_references(None), {})
        self.assertEqual(serialize_references({ 'test': 'test' }), { 'test': 'test' })

    def test_acquire_references_edge_cases(self):
        with self.assertRaises(ValueError):
            acquire_reference(None)
        with self.assertRaises(ValueError):
            acquire_reference(None)

    def test_native_contains(self):
        d = DataBag()
        d.name = "A bag of data"
        d.data = {
            'd1': '1',
            'd2': '2'
        }
        d.save()
        result = DataBag.objects.filter(name__contains='of data')
        self.assertEquals(result.count(), 1)
        self.assertEquals(result[0].pk, d.pk)
        result = DataBag.objects.filter(name__contains='OF data')
        self.assertEquals(result.count(), 0)

    def test_native_icontains(self):
        d = DataBag()
        d.name = "A bag of data"
        d.data = {
            'd1': '1',
            'd2': '2'
        }
        d.save()
        result = DataBag.objects.filter(name__icontains='A bAg')
        self.assertEquals(result.count(), 1)
        self.assertEquals(result[0].pk, d.pk)

    def test_native_gt(self):
        d = NumberedDataBag()
        d.name = "A bag of data"
        d.number = 12
        d.save()
        result = NumberedDataBag.objects.filter(number__gt=12)
        self.assertEquals(result.count(), 0)
        result = NumberedDataBag.objects.filter(number__gt=1)
        self.assertEquals(result.count(), 1)
        self.assertEquals(result[0].pk, d.pk)
        result = NumberedDataBag.objects.filter(number__gt=13)
        self.assertEquals(result.count(), 0)

    def test_native_gte(self):
        d = NumberedDataBag()
        d.name = "A bag of data"
        d.number = 12
        d.save()
        result = NumberedDataBag.objects.filter(number__gte=12)
        self.assertEquals(result.count(), 1)
        self.assertEquals(result[0].pk, d.pk)
        result = NumberedDataBag.objects.filter(number__gte=1)
        self.assertEquals(result.count(), 1)
        self.assertEquals(result[0].pk, d.pk)
        result = NumberedDataBag.objects.filter(number__gte=13)
        self.assertEquals(result.count(), 0)

    def test_native_lt(self):
        d = NumberedDataBag()
        d.name = "A bag of data"
        d.number = 12
        d.save()
        result = NumberedDataBag.objects.filter(number__lt=20)
        self.assertEquals(result.count(), 1)
        self.assertEquals(result[0].pk, d.pk)
        result = NumberedDataBag.objects.filter(number__lt=12)
        self.assertEquals(result.count(), 0)
        result = NumberedDataBag.objects.filter(number__lt=1)
        self.assertEquals(result.count(), 0)


    def test_native_lte(self):
        d = NumberedDataBag()
        d.name = "A bag of data"
        d.number = 12
        d.save()
        result = NumberedDataBag.objects.filter(number__lte=12)
        self.assertEquals(result.count(), 1)
        self.assertEquals(result[0].pk, d.pk)
        result = NumberedDataBag.objects.filter(number__lte=13)
        self.assertEquals(result.count(), 1)
        self.assertEquals(result[0].pk, d.pk)
        result = NumberedDataBag.objects.filter(number__lte=1)
        self.assertEquals(result.count(), 0)


if GEODJANGO:
    from django.contrib.gis.geos import GEOSGeometry

    class TestDictionaryFieldPlusGIS(TestCase):
        """ Test DictionaryField with gis backend """

        def setUp(self):
            Location.objects.all().delete()

        pnt1 = GEOSGeometry('POINT(65.5758316 57.1345383)')
        pnt2 = GEOSGeometry('POINT(65.2316 57.3423233)')

        def _create_locations(self):
            loc1 = Location.objects.create(name='Location1', data={'prop1': '1', 'prop2': 'test_value'}, point=self.pnt1)
            loc2 = Location.objects.create(name='Location2', data={'prop1': '2', 'prop2': 'test_value'}, point=self.pnt2)
            return loc1, loc2

        def test_location_create(self):
            l1, l2 = self._create_locations()
            other_loc = Location.objects.get(point__contains=self.pnt1)
            self.assertEqual(other_loc.data, {'prop1': '1', 'prop2': 'test_value'})

        def test_location_hupdate(self):
            l1, l2 = self._create_locations()
            Location.objects.filter(point__contains=self.pnt1).hupdate('data', {'prop1': '2'})
            loc = Location.objects.exclude(point__contains=self.pnt2)[0]
            self.assertEqual(loc.data, {'prop1': '2', 'prop2': 'test_value'})
            loc = Location.objects.get(point__contains=self.pnt2)
            self.assertNotEqual(loc.data, {'prop1': '1', 'prop2': 'test_value'})

        def test_location_contains(self):
            l1, l2 = self._create_locations()
            self.assertEqual(Location.objects.filter(data__contains={'prop1': '1'}).count(), 1)
            self.assertEqual(Location.objects.filter(data__contains={'prop1': '2'}).count(), 1)

        def test_location_geomanager(self):
            l1, l2 = self._create_locations()
            d1 = Location.objects.filter(point__distance_lte=(self.pnt1, 70000))
            self.assertEqual(d1.count(), 2)


    class TestReferencesFieldPlusGIS(TestDictionaryFieldPlusGIS):
        """ Test ReferenceField with gis backend """

        def _create_locations(self):
            loc1 = Location.objects.create(name='Location1', data={'prop1': '1', 'prop2': 'test_value'}, point=self.pnt1)
            loc2 = Location.objects.create(name='Location2', data={'prop1': '2', 'prop2': 'test_value'}, point=self.pnt2)
            return loc1, loc2

        def test_location_create(self):
            l1, l2 = self._create_locations()
            loc_1 = Location.objects.get(point__contains=self.pnt1)
            self.assertEqual(loc_1.data, {'prop1': '1', 'prop2': 'test_value'})
            loc_2 = Location.objects.get(point__contains=self.pnt2)
            self.assertEqual(loc_2.data, {'prop1': '2', 'prop2': 'test_value'})

        def test_location_hupdate(self):
            l1, l2 = self._create_locations()
            Location.objects.filter(point__contains=self.pnt1).hupdate('data', {'prop1': '2'})
            loc = Location.objects.exclude(point__contains=self.pnt2)[0]
            self.assertEqual(loc.data, {'prop1': '2', 'prop2': 'test_value'})
            loc = Location.objects.get(point__contains=self.pnt2)
            self.assertNotEqual(loc.data, {'prop1': '1', 'prop2': 'test_value'})

########NEW FILE########
__FILENAME__ = settings
from __future__ import print_function

import os
import sys
import django

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
DEBUG = True
TEMPLATE_DEBUG = DEBUG

SECRET_KEY = '!5myuh^d23p9$$lo5k$39x&ji!vceayg+wwt472!bgs$0!i3k4'

DATABASES = {
    'default': {
        # possible backends are:
        #   * django.db.backends.postgresql_psycopg2
        #   * django.contrib.gis.db.backends.postgis
        'ENGINE': 'django.contrib.gis.db.backends.postgis',
        'NAME': 'django_hstore',
        'USER': '',
        'PASSWORD': '',
        'HOST': '',
        'PORT': ''
    },
}

ALLOWED_HOSTS = []


if django.VERSION[:2] >= (1, 7):
    INSTALLED_APPS = (
        'django.contrib.admin.apps.AdminConfig',
        'django.contrib.auth',
        'django.contrib.contenttypes',
        'django.contrib.sessions',
        'django.contrib.messages',
        'django.contrib.staticfiles',
        'django_hstore',
        'django_hstore_tests',
    )
else:
    INSTALLED_APPS = (
        'django.contrib.admin',
        'django.contrib.auth',
        'django.contrib.contenttypes',
        'django.contrib.sessions',
        'django.contrib.messages',
        'django.contrib.staticfiles',
        'django_hstore',
        'django_hstore_tests',
    )

MIDDLEWARE_CLASSES = (
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
)

ROOT_URLCONF = 'urls'
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_L10N = True
USE_TZ = True
STATIC_URL = '/static/'

# local settings must be imported before test runner otherwise they'll be ignored
try:
    from local_settings import *
except ImportError:
    pass

if django.VERSION[:2] >= (1, 6):
    TEST_RUNNER = 'django.test.runner.DiscoverRunner'
else:
    try:
        import discover_runner
        TEST_RUNNER = "discover_runner.DiscoverRunner"
    except ImportError:
        print("For run tests with django <= 1.5 you should install "
              "django-discover-runner.")
        sys.exit(-1)

########NEW FILE########
__FILENAME__ = settings_psycopg
from __future__ import print_function

import os
import sys
import django

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
DEBUG = True
TEMPLATE_DEBUG = DEBUG

SECRET_KEY = '!5myuh^d23p9$$lo5k$39x&ji!vceayg+wwt472!bgs$0!i3k4'

DATABASES = {
    'default': {
        # possible backends are:
        #   * django.db.backends.postgresql_psycopg2
        #   * django.contrib.gis.db.backends.postgis
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': 'django_hstore_psycopg2',
        'USER': '',
        'PASSWORD': '',
        'HOST': '',
        'PORT': ''
    },
}

ALLOWED_HOSTS = []


if django.VERSION[:2] >= (1, 7):
    INSTALLED_APPS = (
        'django.contrib.admin.apps.AdminConfig',
        'django.contrib.auth',
        'django.contrib.contenttypes',
        'django.contrib.sessions',
        'django.contrib.messages',
        'django.contrib.staticfiles',
        'django_hstore',
        'django_hstore_tests',
    )
else:
    INSTALLED_APPS = (
        'django.contrib.admin',
        'django.contrib.auth',
        'django.contrib.contenttypes',
        'django.contrib.sessions',
        'django.contrib.messages',
        'django.contrib.staticfiles',
        'django_hstore',
        'django_hstore_tests',
    )

MIDDLEWARE_CLASSES = (
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
)

ROOT_URLCONF = 'urls'
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_L10N = True
USE_TZ = True
STATIC_URL = '/static/'

# local settings must be imported before test runner otherwise they'll be ignored
try:
    from local_settings_psycopg import *
except ImportError:
    pass

if django.VERSION[:2] >= (1, 6):
    TEST_RUNNER = 'django.test.runner.DiscoverRunner'
else:
    try:
        import discover_runner
        TEST_RUNNER = "discover_runner.DiscoverRunner"
    except ImportError:
        print("For run tests with django <= 1.5 you should install "
              "django-discover-runner.")
        sys.exit(-1)

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls import patterns, include, url
from django.conf import settings
from django.contrib import admin
admin.autodiscover()


urlpatterns = patterns('',
    # Uncomment the next line to enable the admin:
    url(r'^admin/', include(admin.site.urls)),
)


if 'grappelli' in settings.INSTALLED_APPS:
    urlpatterns = urlpatterns + patterns('',
        url(r'^grappelli/', include('grappelli.urls')),
    )
########NEW FILE########
