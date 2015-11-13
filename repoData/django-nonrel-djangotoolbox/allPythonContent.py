__FILENAME__ = admin
from django import forms
from django.contrib import admin
from django.contrib.admin.sites import NotRegistered
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User, Group


class UserForm(forms.ModelForm):

    class Meta:
        model = User
        fields = ('username', 'email', 'first_name', 'last_name', 'is_active',
                  'is_staff', 'is_superuser')


class CustomUserAdmin(UserAdmin):
    fieldsets = None
    form = UserForm
    search_fields = ('=username',)
    list_filter = ('is_staff', 'is_superuser', 'is_active')

try:
    admin.site.unregister(User)
    admin.site.register(User, CustomUserAdmin)
except NotRegistered:
    pass

try:
    admin.site.unregister(Group)
except NotRegistered:
    pass

########NEW FILE########
__FILENAME__ = base
import cPickle as pickle
import datetime

from django.conf import settings
from django.db.backends import (
    BaseDatabaseFeatures,
    BaseDatabaseOperations,
    BaseDatabaseWrapper,
    BaseDatabaseClient,
    BaseDatabaseValidation,
    BaseDatabaseIntrospection)
from django.db.utils import DatabaseError
from django.utils.functional import Promise
from django.utils.safestring import EscapeString, EscapeUnicode, SafeString, \
    SafeUnicode
from django.utils import timezone

from .creation import NonrelDatabaseCreation


class NonrelDatabaseFeatures(BaseDatabaseFeatures):
    # Most NoSQL databases don't have true transaction support.
    supports_transactions = False

    # NoSQL databases usually return a key after saving a new object.
    can_return_id_from_insert = True

    # TODO: Doesn't seem necessary in general, move to back-ends.
    #       Mongo: see PyMongo's FAQ; GAE: see: http://timezones.appspot.com/.
    supports_date_lookup_using_string = False
    supports_timezones = False

    # Features that are commonly not available on nonrel databases.
    supports_joins = False
    supports_select_related = False
    supports_deleting_related_objects = False

    # Having to decide whether to use an INSERT or an UPDATE query is
    # specific to SQL-based databases.
    distinguishes_insert_from_update = False

    # Can primary_key be used on any field? Without encoding usually
    # only a limited set of types is acceptable for keys. This is a set
    # of all field kinds (internal_types) for which the primary_key
    # argument may be used.
    # TODO: Use during model validation.
    # TODO: Move to core and use to skip unsuitable Django tests.
    supports_primary_key_on = set(NonrelDatabaseCreation.data_types.keys()) - \
        set(('ForeignKey', 'OneToOneField', 'ManyToManyField', 'RawField',
             'AbstractIterableField', 'ListField', 'SetField', 'DictField',
             'EmbeddedModelField', 'BlobField'))

    # Django 1.4 compatibility
    def _supports_transactions(self):
        return False


class NonrelDatabaseOperations(BaseDatabaseOperations):
    """
    Override all database conversions normally done by fields (through
    `get_db_prep_value/save/lookup`) to make it possible to pass Python
    values directly to the database layer. On the other hand, provide a
    framework for making type-based conversions --  drivers of NoSQL
    database either can work with Python objects directly, sometimes
    representing one type using a another or expect everything encoded
    in some specific manner.

    Django normally handles conversions for the database by providing
    `BaseDatabaseOperations.value_to_db_*` / `convert_values` methods,
    but there are some problems with them:
    -- some preparations need to be done for all values or for values
       of a particular "kind" (e.g. lazy objects evaluation or casting
       strings wrappers to standard types);
    -- some conversions need more info about the field or model the
       value comes from (e.g. key conversions, embedded deconversion);
    -- there are no value_to_db_* methods for some value types (bools);
    -- we need to handle collecion fields (list, set, dict): they
       need to differentiate between deconverting from database and
       deserializing (so single to_python is inconvenient) and need to
       do some recursion, so a single `value_for_db` is better than one
       method for each field kind.
    Don't use these standard methods in nonrel, `value_for/from_db` are
    more elastic and keeping all conversions in one place makes the
    code easier to analyse.

    Please note, that after changes to type conversions, data saved
    using preexisting methods needs to be handled; and also that Django
    does not expect any special database driver exceptions, so any such
    exceptions should be reraised as django.db.utils.DatabaseError.

    TODO: Consider replacing all `value_to_db_*` and `convert_values`
          with just `BaseDatabaseOperations.value_for/from_db` and also
          moving there code from `Field.get_db_prep_lookup` (and maybe
          `RelatedField.get_db_prep_lookup`).
    """

    def pk_default_value(self):
        """
        Returns None, to be interpreted by back-ends as a request to
        generate a new key for an "inserted" object.
        """
        return None

    def quote_name(self, name):
        """
        Does not do any quoting, as it is not needed for most NoSQL
        databases.
        """
        return name

    def prep_for_like_query(self, value):
        """
        Does no conversion, parent string-cast is SQL specific.
        """
        return value

    def prep_for_iexact_query(self, value):
        """
        Does no conversion, parent string-cast is SQL specific.
        """
        return value

    def value_to_db_auto(self, value):
        """
        Assuming that the database has its own key type, leaves any
        conversions to the back-end.

        This method is added my nonrel to allow various types to be
        used for automatic primary keys. `AutoField.get_db_prep_value`
        calls it to prepare field's value for the database.

        Note that Django can pass a string representation of the value
        instead of the value itself (after receiving it as a query
        parameter for example), so you'll likely need to limit
        your `AutoFields` in a way that makes `str(value)` reversible.

        TODO: This could become a part of `value_for_db` if it makes
              to Django (with a `field_kind` condition).
        """
        return value

    def value_to_db_date(self, value):
        """
        Unlike with SQL database clients, it's better to assume that
        a date can be stored directly.
        """
        return value

    def value_to_db_datetime(self, value):
        """
        We may pass a datetime object to a database driver without
        casting it to a string.
        """
        return value

    def value_to_db_time(self, value):
        """
        Unlike with SQL database clients, we may assume that a time can
        be stored directly.
        """
        return value

    def value_to_db_decimal(self, value, max_digits, decimal_places):
        """
        We may assume that a decimal can be passed to a NoSQL database
        driver directly.
        """
        return value

    # Django 1.4 compatibility
    def year_lookup_bounds(self, value):
        return self.year_lookup_bounds_for_datetime_field(value)

    def year_lookup_bounds_for_date_field(self, value):
        """
        Converts year bounds to date bounds as these can likely be
        used directly, also adds one to the upper bound as it should be
        natural to use one strict inequality for BETWEEN-like filters
        for most nonrel back-ends.
        """
        first = datetime.date(value, 1, 1)
        second = datetime.date(value + 1, 1, 1)
        return [first, second]

    def year_lookup_bounds_for_datetime_field(self, value):
        """
        Converts year bounds to datetime bounds.
        """
        first = datetime.datetime(value, 1, 1, 0, 0, 0, 0)
        second = datetime.datetime(value + 1, 1, 1, 0, 0, 0, 0)
        if settings.USE_TZ:
            tz = timezone.get_current_timezone()
            first = timezone.make_aware(first, tz)
            second = timezone.make_aware(second, tz)
        return [first, second]

    def convert_values(self, value, field):
        """
        We may assume that values returned by the database are standard
        Python types suitable to be passed to fields.
        """
        return value

    def check_aggregate_support(self, aggregate):
        """
        Nonrel back-ends are only expected to implement COUNT in
        general.
        """
        from django.db.models.sql.aggregates import Count
        if not isinstance(aggregate, Count):
            raise NotImplementedError("This database does not support %r "
                                      "aggregates." % type(aggregate))

    def value_for_db(self, value, field, lookup=None):
        """
        Does type-conversions needed before storing a value in the
        the database or using it as a filter parameter.

        This is a convience wrapper that only precomputes field's kind
        and a db_type for the field (or the primary key of the related
        model for ForeignKeys etc.) and knows that arguments to the
        `isnull` lookup (`True` or `False`) should not be converted,
        while some other lookups take a list of arguments.
        In the end, it calls `_value_for_db` to do the real work; you
        should typically extend that method, but only call this one.

        :param value: A value to be passed to the database driver
        :param field: A field the value comes from
        :param lookup: None if the value is being prepared for storage;
                       lookup type name, when its going to be used as a
                       filter argument
        """
        field, field_kind, db_type = self._convert_as(field, lookup)

        # Argument to the "isnull" lookup is just a boolean, while some
        # other lookups take a list of values.
        if lookup == 'isnull':
            return value
        elif lookup in ('in', 'range', 'year'):
            return [self._value_for_db(subvalue, field,
                                       field_kind, db_type, lookup)
                    for subvalue in value]
        else:
            return self._value_for_db(value, field,
                                      field_kind, db_type, lookup)

    def value_from_db(self, value, field):
        """
        Performs deconversions defined by `_value_from_db`.

        :param value: A value received from the database client
        :param field: A field the value is meant for
        """
        return self._value_from_db(value, *self._convert_as(field))

    def _convert_as(self, field, lookup=None):
        """
        Computes parameters that should be used for preparing the field
        for the database or deconverting a database value for it.
        """
        # We need to compute db_type using the original field to allow
        # GAE to use different storage for primary and foreign keys.
        db_type = self.connection.creation.db_type(field)

        if field.rel is not None:
            field = field.rel.get_related_field()
        field_kind = field.get_internal_type()

        # Values for standard month / day queries are integers.
        if (field_kind in ('DateField', 'DateTimeField') and
                lookup in ('month', 'day')):
            db_type = 'integer'

        return field, field_kind, db_type

    def _value_for_db(self, value, field, field_kind, db_type, lookup):
        """
        Converts a standard Python value to a type that can be stored
        or processed by the database driver.

        This implementation only converts elements of iterables passed
        by collection fields, evaluates Django's lazy objects and
        marked strings and handles embedded models.
        Currently, we assume that dict keys and column, model, module
        names (strings) of embedded models require no conversion.

        We need to know the field for two reasons:
        -- to allow back-ends having separate key spaces for different
           tables to create keys refering to the right table (which can
           be the field model's table or the table of the model of the
           instance a ForeignKey or other relation field points to).
        -- to know the field of values passed by typed collection
           fields and to use the proper fields when deconverting values
           stored for typed embedding field.
        Avoid using the field in any other way than by inspecting its
        properties, it may not hold any value or hold a value other
        than the one you're asked to convert.

        You may want to call this method before doing other back-end
        specific conversions.

        :param value: A value to be passed to the database driver
        :param field: A field having the same properties as the field
                      the value comes from; instead of related fields
                      you'll get the related model primary key, as the
                      value usually needs to be converted using its
                      properties
        :param field_kind: Equal to field.get_internal_type()
        :param db_type: Same as creation.db_type(field)
        :param lookup: None if the value is being prepared for storage;
                       lookup type name, when its going to be used as a
                       filter argument
        """

        # Back-ends may want to store empty lists or dicts as None.
        if value is None:
            return None

        # Force evaluation of lazy objects (e.g. lazy translation
        # strings).
        # Some back-ends pass values directly to the database driver,
        # which may fail if it relies on type inspection and gets a
        # functional proxy.
        # This code relies on unicode cast in django.utils.functional
        # just evaluating the wrapped function and doing nothing more.
        # TODO: This has been partially fixed in vanilla with:
        #       https://code.djangoproject.com/changeset/17698, however
        #       still fails for proxies in lookups; reconsider in 1.4.
        #       Also research cases of database operations not done
        #       through the sql.Query.
        if isinstance(value, Promise):
            value = unicode(value)

        # Django wraps strings marked as safe or needed escaping,
        # convert them to just strings for type-inspecting back-ends.
        if isinstance(value, (SafeString, EscapeString)):
            value = str(value)
        elif isinstance(value, (SafeUnicode, EscapeUnicode)):
            value = unicode(value)

        # Convert elements of collection fields.
        if field_kind in ('ListField', 'SetField', 'DictField',):
            value = self._value_for_db_collection(value, field,
                                                  field_kind, db_type, lookup)

        # Store model instance fields' values.
        elif field_kind == 'EmbeddedModelField':
            value = self._value_for_db_model(value, field,
                                             field_kind, db_type, lookup)

        return value

    def _value_from_db(self, value, field, field_kind, db_type):
        """
        Converts a database type to a type acceptable by the field.

        If you encoded a value for storage in the database, reverse the
        encoding here. This implementation only recursively deconverts
        elements of collection fields and handles embedded models.

        You may want to call this method after any back-end specific
        deconversions.

        :param value: A value to be passed to the database driver
        :param field: A field having the same properties as the field
                      the value comes from
        :param field_kind: Equal to field.get_internal_type()
        :param db_type: Same as creation.db_type(field)

        Note: lookup values never get deconverted.
        """

        # We did not convert Nones.
        if value is None:
            return None

        # Deconvert items or values of a collection field.
        if field_kind in ('ListField', 'SetField', 'DictField',):
            value = self._value_from_db_collection(value, field,
                                                   field_kind, db_type)

        # Reinstatiate a serialized model.
        elif field_kind == 'EmbeddedModelField':
            value = self._value_from_db_model(value, field,
                                              field_kind, db_type)

        return value

    def _value_for_db_collection(self, value, field, field_kind, db_type,
                                 lookup):
        """
        Recursively converts values from AbstractIterableFields.

        Note that collection lookup values are plain values rather than
        lists, sets or dicts, but they still should be converted as a
        collection item (assuming all items or values are converted in
        the same way).

        We base the conversion on field class / kind and assume some
        knowledge about field internals (e.g. that the field has an
        "item_field" property that gives the right subfield for any of
        its values), to avoid adding a framework for determination of
        parameters for items' conversions; we do the conversion here
        rather than inside get_db_prep_save/lookup for symmetry with
        deconversion (which can't be in to_python because the method is
        also used for data not coming from the database).

        Returns a list, set, dict, string or bytes according to the
        db_type given.
        If the "list" db_type used for DictField, a list with keys and
        values interleaved will be returned (list of pairs is not good,
        because lists / tuples may need conversion themselves; the list
        may still be nested for dicts containing collections).
        The "string" and "bytes" db_types use serialization with pickle
        protocol 0 or 2 respectively.
        If an unknown db_type is specified, returns a generator
        yielding converted elements / pairs with converted values.
        """
        subfield, subkind, db_subtype = self._convert_as(field.item_field,
                                                         lookup)

        # Do convert filter parameters.
        if lookup:
            # Special case where we are looking for an empty list
            if lookup == 'exact' and db_type == 'list' and value == u'[]':
                return []
            value = self._value_for_db(value, subfield,
                                       subkind, db_subtype, lookup)

        # Convert list/set items or dict values.
        else:
            if field_kind == 'DictField':

                # Generator yielding pairs with converted values.
                value = (
                    (key, self._value_for_db(subvalue, subfield,
                                             subkind, db_subtype, lookup))
                    for key, subvalue in value.iteritems())

                # Return just a dict, a once-flattened list;
                if db_type == 'dict':
                    return dict(value)
                elif db_type == 'list':
                    return list(item for pair in value for item in pair)

            else:

                # Generator producing converted items.
                value = (
                    self._value_for_db(subvalue, subfield,
                                       subkind, db_subtype, lookup)
                    for subvalue in value)

                # "list" may be used for SetField.
                if db_type in 'list':
                    return list(value)
                elif db_type == 'set':
                    # assert field_kind != 'ListField'
                    return set(value)

            # Pickled formats may be used for all collection fields,
            # the fields "natural" type is serialized (something
            # concrete is needed, pickle can't handle generators :-)
            if db_type == 'bytes':
                return pickle.dumps(field._type(value), protocol=2)
            elif db_type == 'string':
                return pickle.dumps(field._type(value))

        # If nothing matched, pass the generator to the back-end.
        return value

    def _value_from_db_collection(self, value, field, field_kind, db_type):
        """
        Recursively deconverts values for AbstractIterableFields.

        Assumes that all values in a collection can be deconverted
        using a single field (Field.item_field, possibly a RawField).

        Returns a value in a format proper for the field kind (the
        value will normally not go through to_python).
        """
        subfield, subkind, db_subtype = self._convert_as(field.item_field)

        # Unpickle (a dict) if a serialized storage is used.
        if db_type == 'bytes' or db_type == 'string':
            value = pickle.loads(value)

        if field_kind == 'DictField':

            # Generator yielding pairs with deconverted values, the
            # "list" db_type stores keys and values interleaved.
            if db_type == 'list':
                value = zip(value[::2], value[1::2])
            else:
                value = value.iteritems()

            # DictField needs to hold a dict.
            return dict(
                (key, self._value_from_db(subvalue, subfield,
                                          subkind, db_subtype))
                for key, subvalue in value)
        else:

            # Generator yielding deconverted items.
            value = (
                self._value_from_db(subvalue, subfield,
                                    subkind, db_subtype)
                for subvalue in value)

            # The value will be available from the field without any
            # further processing and it has to have the right type.
            if field_kind == 'ListField':
                return list(value)
            elif field_kind == 'SetField':
                return set(value)

            # A new field kind? Maybe it can take a generator.
            return value

    def _value_for_db_model(self, value, field, field_kind, db_type, lookup):
        """
        Converts a field => value mapping received from an
        EmbeddedModelField the format chosen for the field storage.

        The embedded instance fields' values are also converted /
        deconverted using value_for/from_db, so any back-end
        conversions will be applied.

        Returns (field.column, value) pairs, possibly augmented with
        model info (to be able to deconvert the embedded instance for
        untyped fields) encoded according to the db_type chosen.
        If "dict" db_type is given a Python dict is returned.
        If "list db_type is chosen a list with columns and values
        interleaved will be returned. Note that just a single level of
        the list is flattened, so it still may be nested -- when the
        embedded instance holds other embedded models or collections).
        Using "bytes" or "string" pickles the mapping using pickle
        protocol 0 or 2 respectively.
        If an unknown db_type is used a generator yielding (column,
        value) pairs with values converted will be returned.

        TODO: How should EmbeddedModelField lookups work?
        """
        if lookup:
            # raise NotImplementedError("Needs specification.")
            return value

        # Convert using proper instance field's info, change keys from
        # fields to columns.
        # TODO/XXX: Arguments order due to Python 2.5 compatibility.
        value = (
            (subfield.column, self._value_for_db(
                subvalue, lookup=lookup, *self._convert_as(subfield, lookup)))
            for subfield, subvalue in value.iteritems())

        # Cast to a dict, interleave columns with values on a list,
        # serialize, or return a generator.
        if db_type == 'dict':
            value = dict(value)
        elif db_type == 'list':
            value = list(item for pair in value for item in pair)
        elif db_type == 'bytes':
            value = pickle.dumps(dict(value), protocol=2)
        elif db_type == 'string':
            value = pickle.dumps(dict(value))

        return value

    def _value_from_db_model(self, value, field, field_kind, db_type):
        """
        Deconverts values stored for EmbeddedModelFields.

        Embedded instances are stored as a (column, value) pairs in a
        dict, a single-flattened list or a serialized dict.

        Returns a tuple with model class and field.attname => value
        mapping.
        """

        # Separate keys from values and create a dict or unpickle one.
        if db_type == 'list':
            value = dict(zip(value[::2], value[1::2]))
        elif db_type == 'bytes' or db_type == 'string':
            value = pickle.loads(value)

        # Let untyped fields determine the embedded instance's model.
        embedded_model = field.stored_model(value)

        # Deconvert fields' values and prepare a dict that can be used
        # to initialize a model (by changing keys from columns to
        # attribute names).
        return embedded_model, dict(
            (subfield.attname, self._value_from_db(
                value[subfield.column], *self._convert_as(subfield)))
            for subfield in embedded_model._meta.fields
            if subfield.column in value)

    def _value_for_db_key(self, value, field_kind):
        """
        Converts value to be used as a key to an acceptable type.
        On default we do no encoding, only allowing key values directly
        acceptable by the database for its key type (if any).

        The conversion has to be reversible given the field type,
        encoding should preserve comparisons.

        Use this to expand the set of fields that can be used as
        primary keys, return value suitable for a key rather than
        a key itself.
        """
        raise DatabaseError(
            "%s may not be used as primary key field." % field_kind)

    def _value_from_db_key(self, value, field_kind):
        """
        Decodes a value previously encoded for a key.
        """
        return value


class NonrelDatabaseClient(BaseDatabaseClient):
    pass


class NonrelDatabaseValidation(BaseDatabaseValidation):
    pass


class NonrelDatabaseIntrospection(BaseDatabaseIntrospection):

    def table_names(self, cursor=None):
        """
        Returns a list of names of all tables that exist in the
        database.
        """
        return self.django_table_names()


class FakeCursor(object):

    def __getattribute__(self, name):
        raise Database.NotSupportedError("Cursors are not supported.")

    def __setattr__(self, name, value):
        raise Database.NotSupportedError("Cursors are not supported.")


class FakeConnection(object):

    def commit(self):
        pass

    def rollback(self):
        pass

    def cursor(self):
        return FakeCursor()

    def close(self):
        pass


class Database(object):
    class Error(StandardError):
        pass

    class InterfaceError(Error):
        pass

    class DatabaseError(Error):
        pass

    class DataError(DatabaseError):
        pass

    class OperationalError(DatabaseError):
        pass

    class IntegrityError(DatabaseError):
        pass

    class InternalError(DatabaseError):
        pass

    class ProgrammingError(DatabaseError):
        pass

    class NotSupportedError(DatabaseError):
        pass

class NonrelDatabaseWrapper(BaseDatabaseWrapper):

    Database = Database

    # These fake operators are required for SQLQuery.as_sql() support.
    operators = {
        'exact': '= %s',
        'iexact': '= UPPER(%s)',
        'contains': 'LIKE %s',
        'icontains': 'LIKE UPPER(%s)',
        'regex': '~ %s',
        'iregex': '~* %s',
        'gt': '> %s',
        'gte': '>= %s',
        'lt': '< %s',
        'lte': '<= %s',
        'startswith': 'LIKE %s',
        'endswith': 'LIKE %s',
        'istartswith': 'LIKE UPPER(%s)',
        'iendswith': 'LIKE UPPER(%s)',
    }

    def get_connection_params(self):
        return {}

    def get_new_connection(self, conn_params):
        return FakeConnection()

    def init_connection_state(self):
        pass

    def _set_autocommit(self, autocommit):
        pass

    def _cursor(self):
        return FakeCursor()

########NEW FILE########
__FILENAME__ = basecompiler
import datetime

import django
from django.conf import settings
from django.db.models.fields import NOT_PROVIDED
from django.db.models.query import QuerySet
from django.db.models.sql import aggregates as sqlaggregates
from django.db.models.sql.compiler import SQLCompiler
from django.db.models.sql.constants import MULTI, SINGLE
from django.db.models.sql.where import AND, OR
from django.db.utils import DatabaseError, IntegrityError
from django.utils.tree import Node
from django.db import connections

try:
    from django.db.models.sql.where import SubqueryConstraint
except ImportError:
    SubqueryConstraint = None

try:
    from django.db.models.sql.datastructures import EmptyResultSet
except ImportError:
    class EmptyResultSet(Exception):
        pass


if django.VERSION >= (1, 5):
    from django.db.models.constants import LOOKUP_SEP
else:
    from django.db.models.sql.constants import LOOKUP_SEP

if django.VERSION >= (1, 6):
    def get_selected_fields(query):
        if query.select:
            return [info.field for info in (query.select +
                        query.related_select_cols)]
        else:
            return query.model._meta.fields
else:
    def get_selected_fields(query):
        if query.select_fields:
            return (query.select_fields + query.related_select_fields)
        else:
            return query.model._meta.fields


EMULATED_OPS = {
    'exact': lambda x, y: y in x if isinstance(x, (list, tuple)) else x == y,
    'iexact': lambda x, y: x.lower() == y.lower(),
    'startswith': lambda x, y: x.startswith(y[0]),
    'istartswith': lambda x, y: x.lower().startswith(y[0].lower()),
    'isnull': lambda x, y: x is None if y else x is not None,
    'in': lambda x, y: x in y,
    'lt': lambda x, y: x < y,
    'lte': lambda x, y: x <= y,
    'gt': lambda x, y: x > y,
    'gte': lambda x, y: x >= y,
}


class NonrelQuery(object):
    """
    Base class for nonrel queries.

    Compilers build a nonrel query when they want to fetch some data.
    They work by first allowing sql.compiler.SQLCompiler to partly build
    a sql.Query, constructing a NonrelQuery query on top of it, and then
    iterating over its results.

    This class provides in-memory filtering and ordering and a
    framework for converting SQL constraint tree built by Django to a
    "representation" more suitable for most NoSQL databases.

    TODO: Replace with FetchCompiler, there are too many query concepts
          around, and it isn't a good abstraction for NoSQL databases.

    TODO: Nonrel currently uses constraint's tree built by Django for
          its SQL back-ends to handle filtering. However, Django
          intermingles translating its lookup / filtering abstraction
          to a logical formula with some preprocessing for joins and
          this results in hacks in nonrel. It would be a better to pull
          out SQL-specific parts from the constraints preprocessing.
    """

    # ----------------------------------------------
    # Public API
    # ----------------------------------------------

    def __init__(self, compiler, fields):
        self.compiler = compiler
        self.connection = compiler.connection
        self.ops = compiler.connection.ops
        self.query = compiler.query # sql.Query
        self.fields = fields
        self._negated = False

    def fetch(self, low_mark=0, high_mark=None):
        """
        Returns an iterator over some part of query results.
        """
        raise NotImplementedError

    def count(self, limit=None):
        """
        Returns the number of objects that would be returned, if
        this query was executed, up to `limit`.
        """
        raise NotImplementedError

    def delete(self):
        """
        Called by NonrelDeleteCompiler after it builds a delete query.
        """
        raise NotImplementedError

    def order_by(self, ordering):
        """
        Reorders query results or execution order. Called by
        NonrelCompilers during query building.

        :param ordering: A list with (field, ascending) tuples or a
                         boolean -- use natural ordering, if any, when
                         the argument is True and its reverse otherwise
        """
        raise NotImplementedError

    def add_filter(self, field, lookup_type, negated, value):
        """
        Adds a single constraint to the query. Called by add_filters for
        each constraint leaf in the WHERE tree built by Django.

        :param field: Lookup field (instance of Field); field.column
                      should be used for database keys
        :param lookup_type: Lookup name (e.g. "startswith")
        :param negated: Is the leaf negated
        :param value: Lookup argument, such as a value to compare with;
                      already prepared for the database
        """
        raise NotImplementedError

    def add_filters(self, filters):
        """
        Converts a constraint tree (sql.where.WhereNode) created by
        Django's SQL query machinery to nonrel style filters, calling
        add_filter for each constraint.

        This assumes the database doesn't support alternatives of
        constraints, you should override this method if it does.

        TODO: Simulate both conjunctions and alternatives in general
              let GAE override conjunctions not to split them into
              multiple queries.
        """
        if filters.negated:
            self._negated = not self._negated

        if not self._negated and filters.connector != AND:
            raise DatabaseError("Only AND filters are supported.")

        # Remove unneeded children from the tree.
        children = self._get_children(filters.children)

        if self._negated and filters.connector != OR and len(children) > 1:
            raise DatabaseError("When negating a whole filter subgroup "
                                "(e.g. a Q object) the subgroup filters must "
                                "be connected via OR, so the non-relational "
                                "backend can convert them like this: "
                                "'not (a OR b) => (not a) AND (not b)'.")

        # Recursively call the method for internal tree nodes, add a
        # filter for each leaf.
        for child in children:
            if isinstance(child, Node):
                self.add_filters(child)
                continue
            field, lookup_type, value = self._decode_child(child)
            self.add_filter(field, lookup_type, self._negated, value)

        if filters.negated:
            self._negated = not self._negated

    # ----------------------------------------------
    # Internal API for reuse by subclasses
    # ----------------------------------------------

    def _decode_child(self, child):
        """
        Produces arguments suitable for add_filter from a WHERE tree
        leaf (a tuple).
        """

        # TODO: Call get_db_prep_lookup directly, constraint.process
        #       doesn't do much more.
        constraint, lookup_type, annotation, value = child
        packed, value = constraint.process(lookup_type, value, self.connection)
        alias, column, db_type = packed
        field = constraint.field

        opts = self.query.model._meta
        if alias and alias != opts.db_table:
            raise DatabaseError("This database doesn't support JOINs "
                                "and multi-table inheritance.")

        # For parent.child_set queries the field held by the constraint
        # is the parent's primary key, while the field the filter
        # should consider is the child's foreign key field.
        if column != field.column:
            if not field.primary_key:
                raise DatabaseError("This database doesn't support filtering "
                                    "on non-primary key ForeignKey fields.")

            field = (f for f in opts.fields if f.column == column).next()
            assert field.rel is not None

        value = self._normalize_lookup_value(
            lookup_type, value, field, annotation)

        return field, lookup_type, value

    def _normalize_lookup_value(self, lookup_type, value, field, annotation):
        """
        Undoes preparations done by `Field.get_db_prep_lookup` not
        suitable for nonrel back-ends and passes the lookup argument
        through nonrel's `value_for_db`.

        TODO: Blank `Field.get_db_prep_lookup` and remove this method.
        """

        # Undo Field.get_db_prep_lookup putting most values in a list
        # (a subclass may override this, so check if it's a list) and
        # losing the (True / False) argument to the "isnull" lookup.
        if lookup_type not in ('in', 'range', 'year') and \
           isinstance(value, (tuple, list)):
            if len(value) > 1:
                raise DatabaseError("Filter lookup type was %s; expected the "
                                    "filter argument not to be a list. Only "
                                    "'in'-filters can be used with lists." %
                                    lookup_type)
            elif lookup_type == 'isnull':
                value = annotation
            else:
                value = value[0]

        # Remove percents added by Field.get_db_prep_lookup (useful
        # if one were to use the value in a LIKE expression).
        if lookup_type in ('startswith', 'istartswith'):
            value = value[:-1]
        elif lookup_type in ('endswith', 'iendswith'):
            value = value[1:]
        elif lookup_type in ('contains', 'icontains'):
            value = value[1:-1]

        # Prepare the value for a database using the nonrel framework.
        return self.ops.value_for_db(value, field, lookup_type)

    def _get_children(self, children):
        """
        Filters out nodes of the given contraint tree not needed for
        nonrel queries; checks that given constraints are supported.
        """
        result = []
        for child in children:

            if SubqueryConstraint is not None \
              and isinstance(child, SubqueryConstraint):
                raise DatabaseError("Subqueries are not supported.")

            if isinstance(child, tuple):
                constraint, lookup_type, _, value = child

                # When doing a lookup using a QuerySet Django would use
                # a subquery, but this won't work for nonrel.
                # TODO: Add a supports_subqueries feature and let
                #       Django evaluate subqueries instead of passing
                #       them as SQL strings (QueryWrappers) to
                #       filtering.
                if isinstance(value, QuerySet):
                    raise DatabaseError("Subqueries are not supported.")

                # Remove leafs that were automatically added by
                # sql.Query.add_filter to handle negations of outer
                # joins.
                if lookup_type == 'isnull' and constraint.field is None:
                    continue

            result.append(child)
        return result

    def _matches_filters(self, entity, filters):
        """
        Checks if an entity returned by the database satisfies
        constraints in a WHERE tree (in-memory filtering).
        """

        # Filters without rules match everything.
        if not filters.children:
            return True

        result = filters.connector == AND

        for child in filters.children:

            # Recursively check a subtree,
            if isinstance(child, Node):
                submatch = self._matches_filters(entity, child)

            # Check constraint leaf, emulating a database condition.
            else:
                field, lookup_type, lookup_value = self._decode_child(child)
                entity_value = entity[field.column]

                if entity_value is None:
                    if isinstance(lookup_value, (datetime.datetime, datetime.date,
                                          datetime.time)):
                        submatch = lookup_type in ('lt', 'lte')
                    elif lookup_type in (
                            'startswith', 'contains', 'endswith', 'iexact',
                            'istartswith', 'icontains', 'iendswith'):
                        submatch = False
                    else:
                        submatch = EMULATED_OPS[lookup_type](
                            entity_value, lookup_value)
                else:
                    submatch = EMULATED_OPS[lookup_type](
                        entity_value, lookup_value)

            if filters.connector == OR and submatch:
                result = True
                break
            elif filters.connector == AND and not submatch:
                result = False
                break

        if filters.negated:
            return not result
        return result

    def _order_in_memory(self, lhs, rhs):
        for field, ascending in self.compiler._get_ordering():
            column = field.column
            result = cmp(lhs.get(column), rhs.get(column))
            if result != 0:
                return result if ascending else -result
        return 0


class NonrelCompiler(SQLCompiler):
    """
    Base class for data fetching back-end compilers.

    Note that nonrel compilers derive from sql.compiler.SQLCompiler and
    thus hold a reference to a sql.Query, not a NonrelQuery.

    TODO: Separate FetchCompiler from the abstract NonrelCompiler.
    """

    def __init__(self, query, connection, using):
        """
        Initializes the underlying SQLCompiler.
        """
        super(NonrelCompiler, self).__init__(query, connection, using)
        self.ops = self.connection.ops

    # ----------------------------------------------
    # Public API
    # ----------------------------------------------

    def results_iter(self):
        """
        Returns an iterator over the results from executing query given
        to this compiler. Called by QuerySet methods.
        """
        fields = self.get_fields()
        try:
            results = self.build_query(fields).fetch(
                self.query.low_mark, self.query.high_mark)
        except EmptyResultSet:
            results = []

        for entity in results:
            yield self._make_result(entity, fields)

    def has_results(self):
        return self.get_count(check_exists=True)

    def execute_sql(self, result_type=MULTI):
        """
        Handles SQL-like aggregate queries. This class only emulates COUNT
        by using abstract NonrelQuery.count method.
        """
        aggregates = self.query.aggregate_select.values()

        # Simulate a count().
        if aggregates:
            assert len(aggregates) == 1
            aggregate = aggregates[0]
            assert isinstance(aggregate, sqlaggregates.Count)
            opts = self.query.get_meta()
            if aggregate.col != '*' and \
                aggregate.col != (opts.db_table, opts.pk.column):
                raise DatabaseError("This database backend only supports "
                                    "count() queries on the primary key.")

            count = self.get_count()
            if result_type is SINGLE:
                return [count]
            elif result_type is MULTI:
                return [[count]]

        raise NotImplementedError("The database backend only supports "
                                  "count() queries.")

    # ----------------------------------------------
    # Additional NonrelCompiler API
    # ----------------------------------------------

    def _make_result(self, entity, fields):
        """
        Decodes values for the given fields from the database entity.

        The entity is assumed to be a dict using field database column
        names as keys. Decodes values using `value_from_db` as well as
        the standard `convert_values`.
        """
        result = []
        for field in fields:
            value = entity.get(field.column, NOT_PROVIDED)
            if value is NOT_PROVIDED:
                value = field.get_default()
            else:
                value = self.ops.value_from_db(value, field)
                value = self.query.convert_values(value, field,
                                                  self.connection)
            if value is None and not field.null:
                raise IntegrityError("Non-nullable field %s can't be None!" %
                                     field.name)
            result.append(value)
        return result

    def check_query(self):
        """
        Checks if the current query is supported by the database.

        In general, we expect queries requiring JOINs (many-to-many
        relations, abstract model bases, or model spanning filtering),
        using DISTINCT (through `QuerySet.distinct()`, which is not
        required in most situations) or using the SQL-specific
        `QuerySet.extra()` to not work with nonrel back-ends.
        """
        if hasattr(self.query, 'is_empty') and self.query.is_empty():
            raise EmptyResultSet()
        if (len([a for a in self.query.alias_map if
                 self.query.alias_refcount[a]]) > 1 or
            self.query.distinct or self.query.extra or self.query.having):
            raise DatabaseError("This query is not supported by the database.")

    def get_count(self, check_exists=False):
        """
        Counts objects matching the current filters / constraints.

        :param check_exists: Only check if any object matches
        """
        if check_exists:
            high_mark = 1
        else:
            high_mark = self.query.high_mark
        try:
            return self.build_query().count(high_mark)
        except EmptyResultSet:
            return 0

    def build_query(self, fields=None):
        """
        Checks if the underlying SQL query is supported and prepares
        a NonrelQuery to be executed on the database.
        """
        self.check_query()
        if fields is None:
            fields = self.get_fields()
        query = self.query_class(self, fields)
        query.add_filters(self.query.where)
        query.order_by(self._get_ordering())

        # This at least satisfies the most basic unit tests.
        if connections[self.using].use_debug_cursor or (connections[self.using].use_debug_cursor is None and settings.DEBUG):
            self.connection.queries.append({'sql': repr(query)})
        return query

    def get_fields(self):
        """
        Returns fields which should get loaded from the back-end by the
        current query.
        """

        # We only set this up here because related_select_fields isn't
        # populated until execute_sql() has been called.
        fields = get_selected_fields(self.query)

        # If the field was deferred, exclude it from being passed
        # into `resolve_columns` because it wasn't selected.
        only_load = self.deferred_to_columns()
        if only_load:
            db_table = self.query.model._meta.db_table
            only_load = dict((k, v) for k, v in only_load.items()
                             if v or k == db_table)
            if len(only_load.keys()) > 1:
                raise DatabaseError("Multi-table inheritance is not "
                                    "supported by non-relational DBs %s." %
                                    repr(only_load))
            fields = [f for f in fields if db_table in only_load and
                      f.column in only_load[db_table]]

        query_model = self.query.model
        if query_model._meta.proxy:
            query_model = query_model._meta.proxy_for_model

        for field in fields:
            if field.model._meta != query_model._meta:
                raise DatabaseError("Multi-table inheritance is not "
                                    "supported by non-relational DBs.")
        return fields

    def _get_ordering(self):
        """
        Returns a list of (field, ascending) tuples that the query
        results should be ordered by. If there is no field ordering
        defined returns just the standard_ordering (a boolean, needed
        for MongoDB "$natural" ordering).
        """
        opts = self.query.get_meta()
        if not self.query.default_ordering:
            ordering = self.query.order_by
        else:
            ordering = self.query.order_by or opts.ordering

        if not ordering:
            return self.query.standard_ordering

        field_ordering = []
        for order in ordering:
            if LOOKUP_SEP in order:
                raise DatabaseError("Ordering can't span tables on "
                                    "non-relational backends (%s)." % order)
            if order == '?':
                raise DatabaseError("Randomized ordering isn't supported by "
                                    "the backend.")

            ascending = not order.startswith('-')
            if not self.query.standard_ordering:
                ascending = not ascending

            name = order.lstrip('+-')
            if name == 'pk':
                name = opts.pk.name

            field_ordering.append((opts.get_field(name), ascending))
        return field_ordering


class NonrelInsertCompiler(NonrelCompiler):
    """
    Base class for all compliers that create new entities or objects
    in the database. It has to define execute_sql method due to being
    used in place of a SQLInsertCompiler.

    TODO: Analyze if it's always true that when field is None we should
          use the PK from self.query (check if the column assertion
          below ever fails).
    """

    def execute_sql(self, return_id=False):
        to_insert = []
        pk_field = self.query.get_meta().pk
        for obj in self.query.objs:
            field_values = {}
            for field in self.query.fields:
                value = field.get_db_prep_save(
                    getattr(obj, field.attname) if self.query.raw else field.pre_save(obj, obj._state.adding),
                    connection=self.connection
                )
                if value is None and not field.null and not field.primary_key:
                    raise IntegrityError("You can't set %s (a non-nullable "
                                         "field) to None!" % field.name)

                # Prepare value for database, note that query.values have
                # already passed through get_db_prep_save.
                value = self.ops.value_for_db(value, field)

                field_values[field.column] = value
            to_insert.append(field_values)

        key = self.insert(to_insert, return_id=return_id)

        # Pass the key value through normal database deconversion.
        return self.ops.convert_values(self.ops.value_from_db(key, pk_field), pk_field)

    def insert(self, values, return_id):
        """
        Creates a new entity to represent a model.

        Note that the returned key will go through the same database
        deconversions that every value coming from the database does
        (`convert_values` and `value_from_db`).

        :param values: The model object as a list of (field, value)
                       pairs; each value is already prepared for the
                       database
        :param return_id: Whether to return the id or key of the newly
                          created entity
        """
        raise NotImplementedError


class NonrelUpdateCompiler(NonrelCompiler):

    def execute_sql(self, result_type):
        values = []
        for field, _, value in self.query.values:
            if hasattr(value, 'prepare_database_save'):
                value = value.prepare_database_save(field)
            else:
                value = field.get_db_prep_save(value,
                                               connection=self.connection)
            value = self.ops.value_for_db(value, field)
            values.append((field, value))
        return self.update(values)

    def update(self, values):
        """
        Changes an entity that already exists in the database.

        :param values: A list of (field, new-value) pairs
        """
        raise NotImplementedError


class NonrelDeleteCompiler(NonrelCompiler):

    def execute_sql(self, result_type=MULTI):
        try:
            self.build_query([self.query.get_meta().pk]).delete()
        except EmptyResultSet:
            pass


class NonrelAggregateCompiler(NonrelCompiler):
    pass


class NonrelDateCompiler(NonrelCompiler):
    pass


class NonrelDateTimeCompiler(NonrelCompiler):
    pass

########NEW FILE########
__FILENAME__ = creation
from django.db.backends.creation import BaseDatabaseCreation


class NonrelDatabaseCreation(BaseDatabaseCreation):

    # "Types" used by database conversion methods to decide how to
    # convert data for or from the database. Type is understood here
    # a bit differently than in vanilla Django -- it should be read
    # as an identifier of an encoding / decoding procedure rather than
    # just a database column type.
    data_types = {

        # NoSQL databases often have specific concepts of entity keys.
        # For example, GAE has the db.Key class, MongoDB likes to use
        # ObjectIds, Redis uses strings, while Cassandra supports
        # different types (including binary data).
        'AutoField':                  'key',
        'RelatedAutoField':           'key',
        'ForeignKey':                 'key',
        'OneToOneField':              'key',
        'ManyToManyField':            'key',

        # Standard field types, more or less suitable for a database
        # (or its client / driver) being able to directly store or
        # process Python objects.
        'BigIntegerField':            'long',
        'BooleanField':               'bool',
        'CharField':                  'string',
        'CommaSeparatedIntegerField': 'string',
        'DateField':                  'date',
        'DateTimeField':              'datetime',
        'DecimalField':               'decimal',
        'EmailField':                 'string',
        'FileField':                  'string',
        'FilePathField':              'string',
        'FloatField':                 'float',
        'ImageField':                 'string',
        'IntegerField':               'integer',
        'IPAddressField':             'string',
        'NullBooleanField':           'bool',
        'PositiveIntegerField':       'integer',
        'PositiveSmallIntegerField':  'integer',
        'SlugField':                  'string',
        'SmallIntegerField':          'integer',
        'TextField':                  'string',
        'TimeField':                  'time',
        'URLField':                   'string',

        # You may use "list" for SetField, or even DictField and
        # EmbeddedModelField (if your database supports nested lists).
        # All following fields also support "string" and "bytes" as
        # their storage types -- which work by serializing using pickle
        # protocol 0 or 2 respectively.
        # Please note that if you can't support the "natural" storage
        # type then the order of field values will be undetermined, and
        # lookups or filters may not work as specified (e.g. the same
        # set or dict may be represented by different lists, with
        # elements in different order, so the same two instances may
        # compare one way or the other).
        'AbstractIterableField':      'list',
        'ListField':                  'list',
        'SetField':                   'set',
        'DictField':                  'dict',
        'EmbeddedModelField':         'dict',

        # RawFields ("raw" db_type) are used when type is not known
        # (untyped collections) or for values that do not come from
        # a field at all (model info serialization), only do generic
        # processing for them (if any). On the other hand, anything
        # using the "bytes" db_type should be converted to a database
        # blob type or stored as binary data.
        'RawField':                   'raw',
        'BlobField':                  'bytes',
    }

    def db_type(self, field):
        """
        Allows back-ends to override db_type determined by the field.

        This has to be called instead of the Field.db_type, because we
        may need to override a db_type a custom field returns directly,
        and need more freedom in handling types of primary keys and
        related fields.

        :param field: A field we want to know the storage type of

        TODO: Field.db_type (as of 1.3.1) is used mostly for generating
              SQL statements (through a couple of methods in
              DatabaseCreation and DatabaseOperations.field_cast_sql)
              or within back-end implementations -- nonrel is not
              dependend on any of these; but there are two cases that
              might need to be fixed, namely:
              -- management/createcachetable (calls field.db_type),
              -- and contrib/gis (defines its own geo_db_type method).
        """
        return field.db_type(connection=self.connection)

    def sql_create_model(self, model, style, known_models=set()):
        """
        Most NoSQL databases are mostly schema-less, no data
        definitions are needed.
        """
        return [], {}

    def sql_indexes_for_model(self, model, style):
        """
        Creates all indexes needed for local (not inherited) fields of
        a model.
        """
        return []

########NEW FILE########
__FILENAME__ = utils
from django.db.backends.util import format_number


def decimal_to_string(value, max_digits=16, decimal_places=0):
    """
    Converts decimal to a unicode string for storage / lookup by nonrel
    databases that don't support decimals natively.

    This is an extension to `django.db.backends.util.format_number`
    that preserves order -- if one decimal is less than another, their
    string representations should compare the same (as strings).

    TODO: Can't this be done using string.format()?
          Not in Python 2.5, str.format is backported to 2.6 only.
    """

    # Handle sign separately.
    if value.is_signed():
        sign = u'-'
        value = abs(value)
    else:
        sign = u''

    # Let Django quantize and cast to a string.
    value = format_number(value, max_digits, decimal_places)

    # Pad with zeroes to a constant width.
    n = value.find('.')
    if n < 0:
        n = len(value)
    if n < max_digits - decimal_places:
        value = u'0' * (max_digits - decimal_places - n) + value
    return sign + value

########NEW FILE########
__FILENAME__ = errorviews
from django import http
from django.template import RequestContext, loader


def server_error(request, template_name='500.html'):
    """
    500 error handler.

    Templates: `500.html`
    Context:
        request_path
            The path of the requested URL (e.g., '/app/pages/bad_page/')
    """

    # You need to create a 500.html template.
    t = loader.get_template(template_name)

    return http.HttpResponseServerError(
        t.render(RequestContext(request, {'request_path': request.path})))

########NEW FILE########
__FILENAME__ = fields
# All fields except for BlobField written by Jonas Haag <jonas@lophus.org>

from django.core.exceptions import ValidationError
from django.utils.importlib import import_module
from django.db import models
from django.db.models.fields.subclassing import Creator
from django.db.utils import IntegrityError
from django.db.models.fields.related import add_lazy_relation


__all__ = ('RawField', 'ListField', 'SetField', 'DictField',
           'EmbeddedModelField', 'BlobField')


EMPTY_ITER = ()


class _FakeModel(object):
    """
    An object of this class can pass itself off as a model instance
    when used as an arguments to Field.pre_save method (item_fields
    of iterable fields are not actually fields of any model).
    """

    def __init__(self, field, value):
        setattr(self, field.attname, value)


class RawField(models.Field):
    """
    Generic field to store anything your database backend allows you
    to. No validation or conversions are done for this field.
    """

    def get_internal_type(self):
        """
        Returns this field's kind. Nonrel fields are meant to extend
        the set of standard fields, so fields subclassing them should
        get the same internal type, rather than their own class name.
        """
        return 'RawField'


class AbstractIterableField(models.Field):
    """
    Abstract field for fields for storing iterable data type like
    ``list``, ``set`` and ``dict``.

    You can pass an instance of a field as the first argument.
    If you do, the iterable items will be piped through the passed
    field's validation and conversion routines, converting the items
    to the appropriate data type.
    """

    def __init__(self, item_field=None, *args, **kwargs):
        default = kwargs.get(
            'default', None if kwargs.get('null') else EMPTY_ITER)

        # Ensure a new object is created every time the default is
        # accessed.
        if default is not None and not callable(default):
            kwargs['default'] = lambda: self._type(default)

        super(AbstractIterableField, self).__init__(*args, **kwargs)

        # Either use the provided item_field or a RawField.
        if item_field is None:
            item_field = RawField()
        elif callable(item_field):
            item_field = item_field()
        self.item_field = item_field

        # We'll be pretending that item_field is a field of a model
        # with just one "value" field.
        assert not hasattr(self.item_field, 'attname')
        self.item_field.set_attributes_from_name('value')

    def contribute_to_class(self, cls, name):
        self.item_field.model = cls
        self.item_field.name = name
        super(AbstractIterableField, self).contribute_to_class(cls, name)

        # If items' field uses SubfieldBase we also need to.
        item_metaclass = getattr(self.item_field, '__metaclass__', None)
        if item_metaclass and issubclass(item_metaclass, models.SubfieldBase):
            setattr(cls, self.name, Creator(self))

        if isinstance(self.item_field, models.ForeignKey) and isinstance(self.item_field.rel.to, basestring):
            """
            If rel.to is a string because the actual class is not yet defined, look up the
            actual class later.  Refer to django.models.fields.related.RelatedField.contribute_to_class.
            """
            def _resolve_lookup(_, resolved_model, __):
                self.item_field.rel.to = resolved_model
                self.item_field.do_related_class(self, cls)

            add_lazy_relation(cls, self, self.item_field.rel.to, _resolve_lookup)

    def _map(self, function, iterable, *args, **kwargs):
        """
        Applies the function to items of the iterable and returns
        an iterable of the proper type for the field.

        Overriden by DictField to only apply the function to values.
        """
        return self._type(function(element, *args, **kwargs)
                          for element in iterable)

    def to_python(self, value):
        """
        Passes value items through item_field's to_python.
        """
        if value is None:
            return None
        return self._map(self.item_field.to_python, value)

    def pre_save(self, model_instance, add):
        """
        Gets our value from the model_instance and passes its items
        through item_field's pre_save (using a fake model instance).
        """
        value = getattr(model_instance, self.attname)
        if value is None:
            return None
        return self._map(
            lambda item: self.item_field.pre_save(
                _FakeModel(self.item_field, item), add),
            value)

    def get_db_prep_save(self, value, connection):
        """
        Applies get_db_prep_save of item_field on value items.
        """
        if value is None:
            return None
        return self._map(self.item_field.get_db_prep_save, value,
                         connection=connection)

    def get_db_prep_lookup(self, lookup_type, value, connection,
                           prepared=False):
        """
        Passes the value through get_db_prep_lookup of item_field.
        """

        # TODO/XXX: Remove as_lookup_value() once we have a cleaner
        # solution for dot-notation queries.
        # See: https://groups.google.com/group/django-non-relational/browse_thread/thread/6056f8384c9caf04/89eeb9fb22ad16f3).
        if hasattr(value, 'as_lookup_value'):
            value = value.as_lookup_value(self, lookup_type, connection)

        return self.item_field.get_db_prep_lookup(
            lookup_type, value, connection=connection, prepared=prepared)

    def validate(self, values, model_instance):
        try:
            iter(values)
        except TypeError:
            raise ValidationError("Value of type %r is not iterable." %
                                  type(values))

    def formfield(self, **kwargs):
        raise NotImplementedError("No form field implemented for %r." %
                                  type(self))


class ListField(AbstractIterableField):
    """
    Field representing a Python ``list``.

    If the optional keyword argument `ordering` is given, it must be a
    callable that is passed to :meth:`list.sort` as `key` argument. If
    `ordering` is given, the items in the list will be sorted before
    sending them to the database.
    """
    _type = list

    def __init__(self, *args, **kwargs):
        self.ordering = kwargs.pop('ordering', None)
        if self.ordering is not None and not callable(self.ordering):
            raise TypeError("'ordering' has to be a callable or None, "
                            "not of type %r." % type(self.ordering))
        super(ListField, self).__init__(*args, **kwargs)

    def get_internal_type(self):
        return 'ListField'

    def pre_save(self, model_instance, add):
        value = getattr(model_instance, self.attname)
        if value is None:
            return None
        if value and self.ordering:
            value.sort(key=self.ordering)
        return super(ListField, self).pre_save(model_instance, add)


class SetField(AbstractIterableField):
    """
    Field representing a Python ``set``.
    """
    _type = set

    def get_internal_type(self):
        return 'SetField'

    def value_to_string(self, obj):
        """
        Custom method for serialization, as JSON doesn't support
        serializing sets.
        """
        return list(self._get_val_from_obj(obj))


class DictField(AbstractIterableField):
    """
    Field representing a Python ``dict``.

    Type conversions described in :class:`AbstractIterableField` only
    affect values of the dictionary, not keys. Depending on the
    back-end, keys that aren't strings might not be allowed.
    """
    _type = dict

    def get_internal_type(self):
        return 'DictField'

    def _map(self, function, iterable, *args, **kwargs):
        return self._type((key, function(value, *args, **kwargs))
                          for key, value in iterable.iteritems())

    def validate(self, values, model_instance):
        if not isinstance(values, dict):
            raise ValidationError("Value is of type %r. Should be a dict." %
                                  type(values))


class EmbeddedModelField(models.Field):
    """
    Field that allows you to embed a model instance.

    :param embedded_model: (optional) The model class of instances we
                           will be embedding; may also be passed as a
                           string, similar to relation fields

    TODO: Make sure to delegate all signals and other field methods to
          the embedded instance (not just pre_save, get_db_prep_* and
          to_python).
    """
    __metaclass__ = models.SubfieldBase

    def __init__(self, embedded_model=None, *args, **kwargs):
        self.embedded_model = embedded_model
        kwargs.setdefault('default', None)
        super(EmbeddedModelField, self).__init__(*args, **kwargs)

    def get_internal_type(self):
        return 'EmbeddedModelField'


    def _set_model(self, model):
        """
        Resolves embedded model class once the field knows the model it
        belongs to.

        If the model argument passed to __init__ was a string, we need
        to make sure to resolve that string to the corresponding model
        class, similar to relation fields.
        However, we need to know our own model to generate a valid key
        for the embedded model class lookup and EmbeddedModelFields are
        not contributed_to_class if used in iterable fields. Thus we
        rely on the collection field telling us its model (by setting
        our "model" attribute in its contribute_to_class method).
        """
        self._model = model
        if model is not None and isinstance(self.embedded_model, basestring):

            def _resolve_lookup(self_, resolved_model, model):
                self.embedded_model = resolved_model

            add_lazy_relation(model, self, self.embedded_model, _resolve_lookup)

    model = property(lambda self: self._model, _set_model)


    def stored_model(self, column_values):
        """
        Returns the fixed embedded_model this field was initialized
        with (typed embedding) or tries to determine the model from
        _module / _model keys stored together with column_values
        (untyped embedding).

        We give precedence to the field's definition model, as silently
        using a differing serialized one could hide some data integrity
        problems.

        Note that a single untyped EmbeddedModelField may process
        instances of different models (especially when used as a type
        of a collection field).
        """
        module = column_values.pop('_module', None)
        model = column_values.pop('_model', None)
        if self.embedded_model is not None:
            return self.embedded_model
        elif module is not None:
            return getattr(import_module(module), model)
        else:
            raise IntegrityError("Untyped EmbeddedModelField trying to load "
                                 "data without serialized model class info.")

    def to_python(self, value):
        """
        Passes embedded model fields' values through embedded fields
        to_python methods and reinstiatates the embedded instance.

        We expect to receive a field.attname => value dict together
        with a model class from back-end database deconversion (which
        needs to know fields of the model beforehand).
        """

        # Either the model class has already been determined during
        # deconverting values from the database or we've got a dict
        # from a deserializer that may contain model class info.
        if isinstance(value, tuple):
            embedded_model, attribute_values = value
        elif isinstance(value, dict):
            embedded_model = self.stored_model(value)
            attribute_values = value
        else:
            return value

        # Pass values through respective fields' to_python, leaving
        # fields for which no value is specified uninitialized.
        attribute_values = dict(
            (field.attname, field.to_python(attribute_values[field.attname]))
            for field in embedded_model._meta.fields
            if field.attname in attribute_values)

        # Create the model instance.
        instance = embedded_model(**attribute_values)
        instance._state.adding = False
        return instance

    def get_db_prep_save(self, embedded_instance, connection):
        """
        Applies pre_save and get_db_prep_save of embedded instance
        fields and passes a field => value mapping down to database
        type conversions.

        The embedded instance will be saved as a column => value dict
        in the end (possibly augmented with info about instance's model
        for untyped embedding), but because we need to apply database
        type conversions on embedded instance fields' values and for
        these we need to know fields those values come from, we need to
        entrust the database layer with creating the dict.
        """
        if embedded_instance is None:
            return None

        # The field's value should be an instance of the model given in
        # its declaration or at least of some model.
        embedded_model = self.embedded_model or models.Model
        if not isinstance(embedded_instance, embedded_model):
            raise TypeError("Expected instance of type %r, not %r." %
                            (embedded_model, type(embedded_instance)))

        # Apply pre_save and get_db_prep_save of embedded instance
        # fields, create the field => value mapping to be passed to
        # storage preprocessing.
        field_values = {}
        add = embedded_instance._state.adding
        for field in embedded_instance._meta.fields:
            value = field.get_db_prep_save(
                field.pre_save(embedded_instance, add), connection=connection)

            # Exclude unset primary keys (e.g. {'id': None}).
            if field.primary_key and value is None:
                continue

            field_values[field] = value

        # Let untyped fields store model info alongside values.
        # We use fake RawFields for additional values to avoid passing
        # embedded_instance to database conversions and to give
        # back-ends a chance to apply generic conversions.
        if self.embedded_model is None:
            module_field = RawField()
            module_field.set_attributes_from_name('_module')
            model_field = RawField()
            model_field.set_attributes_from_name('_model')
            field_values.update(
                ((module_field, embedded_instance.__class__.__module__),
                 (model_field, embedded_instance.__class__.__name__)))

        # This instance will exist in the database soon.
        # TODO.XXX: Ensure that this doesn't cause race conditions.
        embedded_instance._state.adding = False

        return field_values

    # TODO/XXX: Remove this once we have a cleaner solution.
    def get_db_prep_lookup(self, lookup_type, value, connection,
                           prepared=False):
        if hasattr(value, 'as_lookup_value'):
            value = value.as_lookup_value(self, lookup_type, connection)
        return value


class BlobField(models.Field):
    """
    A field for storing blobs of binary data.

    The value might either be a string (or something that can be
    converted to a string), or a file-like object.

    In the latter case, the object has to provide a ``read`` method
    from which the blob is read.
    """

    def get_internal_type(self):
        return 'BlobField'

    def formfield(self, **kwargs):
        """
        A file widget is provided, but use model FileField or
        ImageField for storing specific files most of the time.
        """
        from .widgets import BlobWidget
        from django.forms import FileField
        defaults = {'form_class': FileField, 'widget': BlobWidget}
        defaults.update(kwargs)
        return super(BlobField, self).formfield(**defaults)

    def get_db_prep_save(self, value, connection):
        if hasattr(value, 'read'):
            return value.read()
        else:
            return str(value)

    def get_db_prep_lookup(self, lookup_type, value, connection,
                           prepared=False):
        raise TypeError("BlobFields do not support lookups.")

    def value_to_string(self, obj):
        return str(self._get_val_from_obj(obj))

########NEW FILE########
__FILENAME__ = http
from django.conf import settings
from django.core.serializers.json import DjangoJSONEncoder
from django.http import HttpResponse
from django.utils import simplejson
from django.utils.encoding import force_unicode
from django.utils.functional import Promise


class LazyEncoder(DjangoJSONEncoder):

    def default(self, obj):
        if isinstance(obj, Promise):
            return force_unicode(obj)
        return super(LazyEncoder, self).default(obj)


class JSONResponse(HttpResponse):

    def __init__(self, pyobj, **kwargs):
        super(JSONResponse, self).__init__(
            simplejson.dumps(pyobj, cls=LazyEncoder),
            content_type='application/json; charset=%s' %
                             settings.DEFAULT_CHARSET,
            **kwargs)


class TextResponse(HttpResponse):

    def __init__(self, string='', **kwargs):
        super(TextResponse, self).__init__(
            string,
            content_type='text/plain; charset=%s' % settings.DEFAULT_CHARSET,
            **kwargs)

########NEW FILE########
__FILENAME__ = middleware
from django.conf import settings
from django.http import HttpResponseRedirect
from django.utils.cache import patch_cache_control


LOGIN_REQUIRED_PREFIXES = getattr(settings, 'LOGIN_REQUIRED_PREFIXES', ())
NO_LOGIN_REQUIRED_PREFIXES = getattr(settings,
                                     'NO_LOGIN_REQUIRED_PREFIXES', ())

ALLOWED_DOMAINS = getattr(settings, 'ALLOWED_DOMAINS', None)
NON_REDIRECTED_PATHS = getattr(settings, 'NON_REDIRECTED_PATHS', ())
NON_REDIRECTED_BASE_PATHS = tuple(path.rstrip('/') + '/'
                                  for path in NON_REDIRECTED_PATHS)


class LoginRequiredMiddleware(object):
    """
    Redirects to login page if request path begins with a
    LOGIN_REQURED_PREFIXES prefix. You can also specify
    NO_LOGIN_REQUIRED_PREFIXES which take precedence.
    """

    def process_request(self, request):
        for prefix in NO_LOGIN_REQUIRED_PREFIXES:
            if request.path.startswith(prefix):
                return None
        for prefix in LOGIN_REQUIRED_PREFIXES:
            if request.path.startswith(prefix) and \
                    not request.user.is_authenticated():
                from django.contrib.auth.views import redirect_to_login
                return redirect_to_login(request.get_full_path())
        return None


class RedirectMiddleware(object):
    """
    A static redirect middleware. Mostly useful for hosting providers
    that automatically setup an alternative domain for your website.
    You might not want anyone to access the site via those possibly
    well-known URLs.
    """

    def process_request(self, request):
        host = request.get_host().split(':')[0]
        # Turn off redirects when in debug mode, running unit tests, or
        # when handling an App Engine cron job.
        if (settings.DEBUG or host == 'testserver' or
                not ALLOWED_DOMAINS or
                request.META.get('HTTP_X_APPENGINE_CRON') == 'true' or
                request.path.startswith('/_ah/') or
                request.path in NON_REDIRECTED_PATHS or
                request.path.startswith(NON_REDIRECTED_BASE_PATHS)):
            return
        if host not in settings.ALLOWED_DOMAINS:
            return HttpResponseRedirect(
                'http://' + settings.ALLOWED_DOMAINS[0] + request.path)


class NoHistoryCacheMiddleware(object):
    """
    If user is authenticated we disable browser caching of pages in
    history.
    """

    def process_response(self, request, response):
        if 'Expires' not in response and \
                'Cache-Control' not in response and \
                hasattr(request, 'session') and \
                request.user.is_authenticated():
            patch_cache_control(response,
                no_store=True, no_cache=True, must_revalidate=True, max_age=0)
        return response

########NEW FILE########
__FILENAME__ = models

########NEW FILE########
__FILENAME__ = dynamicsite
from django.conf import settings
from django.core.cache import cache
from django.contrib.sites.models import Site
from djangotoolbox.utils import make_tls_property


_default_site_id = getattr(settings, 'SITE_ID', None)
SITE_ID = settings.__class__.SITE_ID = make_tls_property()


class DynamicSiteIDMiddleware(object):
    """Sets settings.SITE_ID based on request's domain."""

    def process_request(self, request):
        # Ignore port if it's 80 or 443
        if ':' in request.get_host():
            domain, port = request.get_host().split(':')
            if int(port) not in (80, 443):
                domain = request.get_host()
        else:
            domain = request.get_host().split(':')[0]

        # Domains are case insensitive
        domain = domain.lower()

        # We cache the SITE_ID
        cache_key = 'Site:domain:%s' % domain
        site = cache.get(cache_key)
        if site:
            SITE_ID.value = site
        else:
            try:
                site = Site.objects.get(domain=domain)
            except Site.DoesNotExist:
                site = None

            if not site:
                # Fall back to with/without 'www.'
                if domain.startswith('www.'):
                    fallback_domain = domain[4:]
                else:
                    fallback_domain = 'www.' + domain

                try:
                    site = Site.objects.get(domain=fallback_domain)
                except Site.DoesNotExist:
                    site = None

            # Add site if it doesn't exist
            if not site and getattr(settings, 'CREATE_SITES_AUTOMATICALLY',
                                    True):
                site = Site(domain=domain, name=domain)
                site.save()

            # Set SITE_ID for this thread/request
            if site:
                SITE_ID.value = site.pk
            else:
                SITE_ID.value = _default_site_id

            cache.set(cache_key, SITE_ID.value, 5 * 60)

########NEW FILE########
__FILENAME__ = test
from django.test import TestCase
from django.utils.unittest import TextTestResult, TextTestRunner

try:
    from django.test.runner import DiscoverRunner as TestRunner
except ImportError:
    from django.test.simple import DjangoTestSuiteRunner as TestRunner

from .utils import object_list_to_table

import re


class ModelTestCase(TestCase):
    """
    A test case for models that provides an easy way to validate the DB
    contents against a given list of row-values.

    You have to specify the model to validate using the 'model'
    attribute:

    class MyTestCase(ModelTestCase):
        model = MyModel
    """

    def validate_state(self, columns, *state_table):
        """
        Validates that the DB contains exactly the values given in the
        state table. The list of columns is given in the columns tuple.

        Example:
        self.validate_state(
            ('a', 'b', 'c'),
            (1, 2, 3),
            (11, 12, 13),
        )
        validates that the table contains exactly two rows and that
        their 'a', 'b', and 'c' attributes are 1, 2, 3 for one row and
        11, 12, 13 for the other row. The order of the rows doesn't
        matter.
        """
        current_state = object_list_to_table(
            columns, self.model.all())[1:]
        if not equal_lists(current_state, state_table):
            print "DB state not valid:"
            print "Current state:"
            print columns
            for state in current_state:
                print state
            print "Should be:"
            for state in state_table:
                print state
            self.fail("DB state not valid.")


class CapturingTestSuiteRunner(TestRunner):
    """
    Captures stdout/stderr during test and shows them next to
    tracebacks.
    """

    def run_suite(self, suite, **kwargs):
        return TextTestRunner(verbosity=self.verbosity,
                              failfast=self.failfast,
                              buffer=True).run(suite)

_EXPECTED_ERRORS = [
    r"This query is not supported by the database\.",
    r"Multi-table inheritance is not supported by non-relational DBs\.",
    r"TextField is not indexed, by default, so you can't filter on it\.",
    r"First ordering property must be the same as inequality filter property",
    r"This database doesn't support filtering on non-primary key ForeignKey fields\.",
    r"Only AND filters are supported\.",
    r"MultiQuery does not support keys_only\.",
    r"You can't query against more than 30 __in filter value combinations\.",
    r"Only strings and positive integers may be used as keys on GAE\.",
    r"This database does not support <class '.*'> aggregates\.",
    r"Subqueries are not supported \(yet\)\.",
    r"Cursors are not supported\.",
    r"This database backend only supports count\(\) queries on the primary key\.",
    r"AutoField \(default primary key\) values must be strings representing an ObjectId on MongoDB",
]


class NonrelTestResult(TextTestResult):
    def __init__(self, *args, **kwargs):
        super(NonrelTestResult, self).__init__(*args, **kwargs)
        self._compiled_exception_matchers = [re.compile(expr) for expr in _EXPECTED_ERRORS]

    def __match_exception(self, exc):
        for exc_match in self._compiled_exception_matchers:
            if exc_match.search(str(exc)):
                return True
        return False

    def addError(self, test, err):
        exc = err[1]
        if self.__match_exception(exc):
            super(NonrelTestResult, self).addExpectedFailure(test, err)
        else:
            super(NonrelTestResult, self).addError(test, err)


class NonrelTestSuiteRunner(TestRunner):
    def run_suite(self, suite, **kwargs):
        return TextTestRunner(
            verbosity=self.verbosity,
            failfast=self.failfast,
            resultclass=NonrelTestResult,
            buffer=False
        ).run(suite)

########NEW FILE########
__FILENAME__ = tests
from __future__ import with_statement
from decimal import Decimal, InvalidOperation
import time

from django.core import serializers
from django.db import models
from django.db.models import Q
from django.db.models.signals import post_save
from django.db.utils import DatabaseError
from django.dispatch.dispatcher import receiver
from django.test import TestCase
from django.utils.unittest import expectedFailure, skip

from .fields import ListField, SetField, DictField, EmbeddedModelField


def count_calls(func):

    def wrapper(*args, **kwargs):
        wrapper.calls += 1
        return func(*args, **kwargs)
    wrapper.calls = 0

    return wrapper


class Target(models.Model):
    index = models.IntegerField()


class Source(models.Model):
    target = models.ForeignKey(Target)
    index = models.IntegerField()


class DecimalModel(models.Model):
    decimal = models.DecimalField(max_digits=9, decimal_places=2)


class DecimalKey(models.Model):
    decimal = models.DecimalField(max_digits=9, decimal_places=2, primary_key=True)


class DecimalParent(models.Model):
    child = models.ForeignKey(DecimalKey)


class DecimalsList(models.Model):
    decimals = ListField(models.ForeignKey(DecimalKey))


class ListModel(models.Model):
    integer = models.IntegerField(primary_key=True)
    floating_point = models.FloatField()
    names = ListField(models.CharField)
    names_with_default = ListField(models.CharField(max_length=500),
                                   default=[])
    names_nullable = ListField(models.CharField(max_length=500), null=True)


class OrderedListModel(models.Model):
    ordered_ints = ListField(models.IntegerField(max_length=500), default=[],
                             ordering=count_calls(lambda x: x), null=True)
    ordered_nullable = ListField(ordering=lambda x: x, null=True)


class SetModel(models.Model):
    setfield = SetField(models.IntegerField())


class DictModel(models.Model):
    dictfield = DictField(models.IntegerField)
    dictfield_nullable = DictField(null=True)
    auto_now = DictField(models.DateTimeField(auto_now=True))


class EmbeddedModelFieldModel(models.Model):
    simple = EmbeddedModelField('EmbeddedModel', null=True)
    simple_untyped = EmbeddedModelField(null=True)
    decimal_parent = EmbeddedModelField(DecimalParent, null=True)
    typed_list = ListField(EmbeddedModelField('SetModel'))
    typed_list2 = ListField(EmbeddedModelField('EmbeddedModel'))
    untyped_list = ListField(EmbeddedModelField())
    untyped_dict = DictField(EmbeddedModelField())
    ordered_list = ListField(EmbeddedModelField(),
                             ordering=lambda obj: obj.index)


class EmbeddedModel(models.Model):
    some_relation = models.ForeignKey(DictModel, null=True)
    someint = models.IntegerField(db_column='custom')
    auto_now = models.DateTimeField(auto_now=True)
    auto_now_add = models.DateTimeField(auto_now_add=True)


class IterableFieldsTest(TestCase):
    floats = [5.3, 2.6, 9.1, 1.58]
    names = [u'Kakashi', u'Naruto', u'Sasuke', u'Sakura']
    unordered_ints = [4, 2, 6, 1]

    def setUp(self):
        for i, float in zip(range(1, 5), IterableFieldsTest.floats):
            ListModel(integer=i, floating_point=float,
                      names=IterableFieldsTest.names[:i]).save()

    def test_startswith(self):
        self.assertEquals(
            dict([(entity.pk, entity.names) for entity in
                  ListModel.objects.filter(names__startswith='Sa')]),
            dict([(3, ['Kakashi', 'Naruto', 'Sasuke']),
                  (4, ['Kakashi', 'Naruto', 'Sasuke', 'Sakura']), ]))

    def test_options(self):
        self.assertEqual([entity.names_with_default for entity in
                          ListModel.objects.filter(names__startswith='Sa')],
                         [[], []])

        self.assertEqual([entity.names_nullable for entity in
                          ListModel.objects.filter(names__startswith='Sa')],
                         [None, None])

    def test_default_value(self):
        # Make sure default value is copied.
        ListModel().names_with_default.append(2)
        self.assertEqual(ListModel().names_with_default, [])

    def test_ordering(self):
        f = OrderedListModel._meta.fields[1]
        f.ordering.calls = 0

        # Ensure no ordering happens on assignment.
        obj = OrderedListModel()
        obj.ordered_ints = self.unordered_ints
        self.assertEqual(f.ordering.calls, 0)

        obj.save()
        self.assertEqual(OrderedListModel.objects.get().ordered_ints,
                         sorted(self.unordered_ints))
        # Ordering should happen only once, i.e. the order function may
        # be called N times at most (N being the number of items in the
        # list).
        self.assertLessEqual(f.ordering.calls, len(self.unordered_ints))

    def test_gt(self):
        self.assertEquals(
            dict([(entity.pk, entity.names) for entity in
                  ListModel.objects.filter(names__gt='Kakashi')]),
            dict([(2, [u'Kakashi', u'Naruto']),
                  (3, [u'Kakashi', u'Naruto', u'Sasuke']),
                  (4, [u'Kakashi', u'Naruto', u'Sasuke', u'Sakura']), ]))

    def test_lt(self):
        self.assertEquals(
            dict([(entity.pk, entity.names) for entity in
                  ListModel.objects.filter(names__lt='Naruto')]),
            dict([(1, [u'Kakashi']),
                  (2, [u'Kakashi', u'Naruto']),
                  (3, [u'Kakashi', u'Naruto', u'Sasuke']),
                  (4, [u'Kakashi', u'Naruto', u'Sasuke', u'Sakura']), ]))

    def test_gte(self):
        self.assertEquals(
            dict([(entity.pk, entity.names) for entity in
                  ListModel.objects.filter(names__gte='Sakura')]),
            dict([(3, [u'Kakashi', u'Naruto', u'Sasuke']),
                  (4, [u'Kakashi', u'Naruto', u'Sasuke', u'Sakura']), ]))

    def test_lte(self):
        self.assertEquals(
            dict([(entity.pk, entity.names) for entity in
                  ListModel.objects.filter(names__lte='Kakashi')]),
            dict([(1, [u'Kakashi']),
                  (2, [u'Kakashi', u'Naruto']),
                  (3, [u'Kakashi', u'Naruto', u'Sasuke']),
                  (4, [u'Kakashi', u'Naruto', u'Sasuke', u'Sakura']), ]))

    def test_equals(self):
        self.assertEquals([entity.names for entity in
                           ListModel.objects.filter(names='Sakura')],
                          [[u'Kakashi', u'Naruto', u'Sasuke', u'Sakura']])

        # Test with additonal pk filter (for DBs that have special pk
        # queries).
        query = ListModel.objects.filter(names='Sakura')
        self.assertEquals(query.get(pk=query[0].pk).names,
                          [u'Kakashi', u'Naruto', u'Sasuke', u'Sakura'])

    def test_is_null(self):
        self.assertEquals(ListModel.objects.filter(
            names__isnull=True).count(), 0)

    def test_exclude(self):
        self.assertEquals(
            dict([(entity.pk, entity.names) for entity in
                  ListModel.objects.all().exclude(names__lt='Sakura')]),
            dict([(3, [u'Kakashi', u'Naruto', u'Sasuke']),
                  (4, [u'Kakashi', u'Naruto', u'Sasuke', u'Sakura']), ]))

    def test_chained_filter(self):
        self.assertEquals(
            [entity.names for entity in ListModel.objects
                .filter(names='Sasuke').filter(names='Sakura')],
            [['Kakashi', 'Naruto', 'Sasuke', 'Sakura'], ])

        self.assertEquals(
            [entity.names for entity in ListModel.objects
                .filter(names__startswith='Sa').filter(names='Sakura')],
            [['Kakashi', 'Naruto', 'Sasuke', 'Sakura']])

        # Test across multiple columns. On app engine only one filter
        # is allowed to be an inequality filter.
        self.assertEquals(
            [entity.names for entity in ListModel.objects
                .filter(floating_point=9.1).filter(names__startswith='Sa')],
            [['Kakashi', 'Naruto', 'Sasuke'], ])

    def test_setfield(self):
        setdata = [1, 2, 3, 2, 1]
        # At the same time test value conversion.
        SetModel(setfield=map(str, setdata)).save()
        item = SetModel.objects.filter(setfield=3)[0]
        self.assertEqual(item.setfield, set(setdata))
        # This shouldn't raise an error because the default value is
        # an empty list.
        SetModel().save()

    def test_dictfield(self):
        DictModel(dictfield=dict(a=1, b='55', foo=3.14),
                  auto_now={'a': None}).save()
        item = DictModel.objects.get()
        self.assertEqual(item.dictfield, {u'a': 1, u'b': 55, u'foo': 3})

        dt = item.auto_now['a']
        self.assertNotEqual(dt, None)
        item.save()
        time.sleep(0.5) # Sleep to avoid false positive failure on the assertion below
        self.assertGreater(DictModel.objects.get().auto_now['a'], dt)
        item.delete()

        # Saving empty dicts shouldn't throw errors.
        DictModel().save()
        # Regression tests for djangoappengine issue #39.
        DictModel.add_to_class('new_dict_field', DictField())
        DictModel.objects.get()

    @skip("GAE specific?")
    def test_Q_objects(self):
        self.assertEquals(
            [entity.names for entity in ListModel.objects
                .exclude(Q(names__lt='Sakura') | Q(names__gte='Sasuke'))],
            [['Kakashi', 'Naruto', 'Sasuke', 'Sakura']])

    def test_list_with_foreignkeys(self):

        class ReferenceList(models.Model):
            keys =  ListField(models.ForeignKey('Model'))

        class Model(models.Model):
            pass

        model1 = Model.objects.create()
        model2 = Model.objects.create()
        ReferenceList.objects.create(keys=[model1.pk, model2.pk])

        self.assertEqual(ReferenceList.objects.get().keys[0], model1.pk)
        self.assertEqual(ReferenceList.objects.filter(keys=model1.pk).count(), 1)

    def test_list_with_foreign_conversion(self):
        decimal = DecimalKey.objects.create(decimal=Decimal('1.5'))
        DecimalsList.objects.create(decimals=[decimal.pk])

    @expectedFailure
    def test_nested_list(self):
        """
        Some back-ends expect lists to be strongly typed or not contain
        other lists (e.g. GAE), this limits how the ListField can be
        used (unless the back-end were to serialize all lists).
        """

        class UntypedListModel(models.Model):
            untyped_list = ListField()

        UntypedListModel.objects.create(untyped_list=[1, [2, 3]])


class Child(models.Model):
    pass


class Parent(models.Model):
    id = models.IntegerField(primary_key=True)
    integer_list = ListField(models.IntegerField)
    integer_dict = DictField(models.IntegerField)
    embedded_list = ListField(EmbeddedModelField(Child))
    embedded_dict = DictField(EmbeddedModelField(Child))


class EmbeddedModelFieldTest(TestCase):

    def assertEqualDatetime(self, d1, d2):
        """Compares d1 and d2, ignoring microseconds."""
        self.assertEqual(d1.replace(microsecond=0),
                         d2.replace(microsecond=0))

    def assertNotEqualDatetime(self, d1, d2):
        self.assertNotEqual(d1.replace(microsecond=0),
                            d2.replace(microsecond=0))

    def _simple_instance(self):
        EmbeddedModelFieldModel.objects.create(
            simple=EmbeddedModel(someint='5'))
        return EmbeddedModelFieldModel.objects.get()

    def test_simple(self):
        instance = self._simple_instance()
        self.assertIsInstance(instance.simple, EmbeddedModel)
        # Make sure get_prep_value is called.
        self.assertEqual(instance.simple.someint, 5)
        # Primary keys should not be populated...
        self.assertEqual(instance.simple.id, None)
        # ... unless set explicitly.
        instance.simple.id = instance.id
        instance.save()
        instance = EmbeddedModelFieldModel.objects.get()
        self.assertEqual(instance.simple.id, instance.id)

    def _test_pre_save(self, instance, get_field):
        # Make sure field.pre_save is called for embedded objects.
        from time import sleep
        instance.save()
        auto_now = get_field(instance).auto_now
        auto_now_add = get_field(instance).auto_now_add
        self.assertNotEqual(auto_now, None)
        self.assertNotEqual(auto_now_add, None)

        sleep(1) # FIXME
        instance.save()
        self.assertNotEqualDatetime(get_field(instance).auto_now,
                                    get_field(instance).auto_now_add)

        instance = EmbeddedModelFieldModel.objects.get()
        instance.save()
        # auto_now_add shouldn't have changed now, but auto_now should.
        self.assertEqualDatetime(get_field(instance).auto_now_add,
                                 auto_now_add)
        self.assertGreater(get_field(instance).auto_now, auto_now)

    def test_pre_save(self):
        obj = EmbeddedModelFieldModel(simple=EmbeddedModel())
        self._test_pre_save(obj, lambda instance: instance.simple)

    def test_pre_save_untyped(self):
        obj = EmbeddedModelFieldModel(simple_untyped=EmbeddedModel())
        self._test_pre_save(obj, lambda instance: instance.simple_untyped)

    def test_pre_save_in_list(self):
        obj = EmbeddedModelFieldModel(untyped_list=[EmbeddedModel()])
        self._test_pre_save(obj, lambda instance: instance.untyped_list[0])

    def test_pre_save_in_dict(self):
        obj = EmbeddedModelFieldModel(untyped_dict={'a': EmbeddedModel()})
        self._test_pre_save(obj, lambda instance: instance.untyped_dict['a'])

    def test_pre_save_list(self):
        # Also make sure auto_now{,add} works for embedded object *lists*.
        EmbeddedModelFieldModel.objects.create(typed_list2=[EmbeddedModel()])
        instance = EmbeddedModelFieldModel.objects.get()

        auto_now = instance.typed_list2[0].auto_now
        auto_now_add = instance.typed_list2[0].auto_now_add
        self.assertNotEqual(auto_now, None)
        self.assertNotEqual(auto_now_add, None)

        instance.typed_list2.append(EmbeddedModel())
        instance.save()
        instance = EmbeddedModelFieldModel.objects.get()

        self.assertEqualDatetime(instance.typed_list2[0].auto_now_add,
                                 auto_now_add)
        self.assertGreater(instance.typed_list2[0].auto_now, auto_now)
        self.assertNotEqual(instance.typed_list2[1].auto_now, None)
        self.assertNotEqual(instance.typed_list2[1].auto_now_add, None)

    def test_error_messages(self):
        for kwargs, expected in (
                ({'simple': 42}, EmbeddedModel),
                ({'simple_untyped': 42}, models.Model),
                ({'typed_list': [EmbeddedModel()]}, SetModel)):
            self.assertRaisesRegexp(
                TypeError, "Expected instance of type %r." % expected,
                EmbeddedModelFieldModel(**kwargs).save)

    def test_typed_listfield(self):
        EmbeddedModelFieldModel.objects.create(
            typed_list=[SetModel(setfield=range(3)),
                        SetModel(setfield=range(9))],
            ordered_list=[Target(index=i) for i in xrange(5, 0, -1)])
        obj = EmbeddedModelFieldModel.objects.get()
        self.assertIn(5, obj.typed_list[1].setfield)
        self.assertEqual([target.index for target in obj.ordered_list],
                         range(1, 6))

    def test_untyped_listfield(self):
        EmbeddedModelFieldModel.objects.create(untyped_list=[
            EmbeddedModel(someint=7),
            OrderedListModel(ordered_ints=range(5, 0, -1)),
            SetModel(setfield=[1, 2, 2, 3])])
        instances = EmbeddedModelFieldModel.objects.get().untyped_list
        for instance, cls in zip(instances,
                                 [EmbeddedModel, OrderedListModel, SetModel]):
            self.assertIsInstance(instance, cls)
        self.assertNotEqual(instances[0].auto_now, None)
        self.assertEqual(instances[1].ordered_ints, range(1, 6))

    def test_untyped_dict(self):
        EmbeddedModelFieldModel.objects.create(untyped_dict={
            'a': SetModel(setfield=range(3)),
            'b': DictModel(dictfield={'a': 1, 'b': 2}),
            'c': DictModel(dictfield={}, auto_now={'y': 1})})
        data = EmbeddedModelFieldModel.objects.get().untyped_dict
        self.assertIsInstance(data['a'], SetModel)
        self.assertNotEqual(data['c'].auto_now['y'], None)

    def test_foreignkey_in_embedded_object(self):
        simple = EmbeddedModel(some_relation=DictModel.objects.create())
        obj = EmbeddedModelFieldModel.objects.create(simple=simple)
        simple = EmbeddedModelFieldModel.objects.get().simple
        self.assertNotIn('some_relation', simple.__dict__)
        self.assertIsInstance(simple.__dict__['some_relation_id'],
                              type(obj.id))
        self.assertIsInstance(simple.some_relation, DictModel)

    def test_embedded_field_with_foreign_conversion(self):
        decimal = DecimalKey.objects.create(decimal=Decimal('1.5'))
        decimal_parent = DecimalParent.objects.create(child=decimal)
        EmbeddedModelFieldModel.objects.create(decimal_parent=decimal_parent)

    def test_update(self):
        """
        Test that update can be used on an a subset of objects
        containing collections of embedded instances; see issue #13.
        Also ensure that updated values are coerced according to
        collection field.
        """
        child1 = Child.objects.create()
        child2 = Child.objects.create()
        parent = Parent.objects.create(pk=1,
            integer_list=[1], integer_dict={'a': 2},
            embedded_list=[child1], embedded_dict={'a': child2})
        Parent.objects.filter(pk=1).update(
            integer_list=['3'], integer_dict={'b': '3'},
            embedded_list=[child2], embedded_dict={'b': child1})
        parent = Parent.objects.get()
        self.assertEqual(parent.integer_list, [3])
        self.assertEqual(parent.integer_dict, {'b': 3})
        self.assertEqual(parent.embedded_list, [child2])
        self.assertEqual(parent.embedded_dict, {'b': child1})


class BaseModel(models.Model):
    pass


class ExtendedModel(BaseModel):
    name = models.CharField(max_length=20)


class BaseModelProxy(BaseModel):

    class Meta:
        proxy = True


class ExtendedModelProxy(ExtendedModel):

    class Meta:
        proxy = True


class ProxyTest(TestCase):

    def test_proxy(self):
        list(BaseModelProxy.objects.all())

    def test_proxy_with_inheritance(self):
        self.assertRaises(DatabaseError,
                          lambda: list(ExtendedModelProxy.objects.all()))


class SignalTest(TestCase):

    def test_post_save(self):
        created = []

        @receiver(post_save, sender=SetModel)
        def handle(**kwargs):
            created.append(kwargs['created'])

        SetModel().save()
        self.assertEqual(created, [True])
        SetModel.objects.get().save()
        self.assertEqual(created, [True, False])
        qs = SetModel.objects.all()
        list(qs)[0].save()
        self.assertEqual(created, [True, False, False])
        list(qs)[0].save()
        self.assertEqual(created, [True, False, False, False])
        list(qs.select_related())[0].save()
        self.assertEqual(created, [True, False, False, False, False])


class SelectRelatedTest(TestCase):

    def test_select_related(self):
        target = Target(index=5)
        target.save()
        Source(target=target, index=8).save()
        source = Source.objects.all().select_related()[0]
        self.assertEqual(source.target.pk, target.pk)
        self.assertEqual(source.target.index, target.index)
        source = Source.objects.all().select_related('target')[0]
        self.assertEqual(source.target.pk, target.pk)
        self.assertEqual(source.target.index, target.index)


class DBColumn(models.Model):
    a = models.IntegerField(db_column='b')


class OrderByTest(TestCase):

    def test_foreign_keys(self):
        target1 = Target.objects.create(index=1)
        target2 = Target.objects.create(index=2)
        source1 = Source.objects.create(target=target1, index=3)
        source2 = Source.objects.create(target=target2, index=4)
        self.assertEqual(list(Source.objects.all().order_by('target')),
                         [source1, source2])
        self.assertEqual(list(Source.objects.all().order_by('-target')),
                         [source2, source1])

    def test_db_column(self):
        model1 = DBColumn.objects.create(a=1)
        model2 = DBColumn.objects.create(a=2)
        self.assertEqual(list(DBColumn.objects.all().order_by('a')),
                         [model1, model2])
        self.assertEqual(list(DBColumn.objects.all().order_by('-a')),
                         [model2, model1])

    def test_reverse(self):
        model1 = DBColumn.objects.create(a=1)
        model2 = DBColumn.objects.create(a=2)
        self.assertEqual(list(DBColumn.objects.all().order_by('a').reverse()),
                         [model2, model1])
        self.assertEqual(list(DBColumn.objects.all().order_by('-a').reverse()),
                         [model1, model2])

    def test_chain(self):
        model1 = Target.objects.create(index=1)
        model2 = Target.objects.create(index=2)
        self.assertEqual(
            list(Target.objects.all().order_by('index').order_by('-index')),
            [model2, model1])


class SerializableSetModel(models.Model):
    setfield = SetField(models.IntegerField())
    setcharfield = SetField(models.CharField(), null=True)


class SerializationTest(TestCase):
    """
    JSON doesn't support sets, so they need to be converted to lists
    for serialization; see issue #12.

    TODO: Check if the fix works with embedded models / nested sets.
    """
    names = ['foo', 'bar', 'baz', 'monkey']

    def test_json_listfield(self):
        for i in range(1, 5):
            ListModel(integer=i, floating_point=0,
                      names=SerializationTest.names[:i]).save()
        objects = ListModel.objects.all()
        serialized = serializers.serialize('json', objects)
        deserialized = serializers.deserialize('json', serialized)
        for m in deserialized:
            integer = m.object.integer
            names = m.object.names
            self.assertEqual(names, SerializationTest.names[:integer])

    def test_json_setfield(self):
        for i in range(1, 5):
            SerializableSetModel(
                setfield=set([i - 1]),
                setcharfield=set(SerializationTest.names[:i])).save()
        objects = SerializableSetModel.objects.all()
        serialized = serializers.serialize('json', objects)
        deserialized = serializers.deserialize('json', serialized)
        for m in deserialized:
            integer = m.object.setfield.pop()
            names = m.object.setcharfield
            self.assertEqual(names, set(SerializationTest.names[:integer + 1]))


class String(models.Model):
    s = models.CharField(max_length=20)


class LazyObjectsTest(TestCase):

    def test_translation(self):
        """
        Using a lazy translation call should work just the same as
        a non-lazy one (or a plain string).
        """
        from django.utils.translation import ugettext_lazy

        a = String.objects.create(s='a')
        b = String.objects.create(s=ugettext_lazy('b'))

        self.assertEqual(String.objects.get(s='a'), a)
        self.assertEqual(list(String.objects.filter(s='a')), [a])
        self.assertEqual(list(String.objects.filter(s__lte='a')), [a])
        self.assertEqual(String.objects.get(s=ugettext_lazy('a')), a)
        self.assertEqual(
            list(String.objects.filter(s__lte=ugettext_lazy('a'))), [a])

        self.assertEqual(String.objects.get(s='b'), b)
        self.assertEqual(list(String.objects.filter(s='b')), [b])
        self.assertEqual(list(String.objects.filter(s__gte='b')), [b])
        self.assertEqual(String.objects.get(s=ugettext_lazy('b')), b)
        self.assertEqual(
            list(String.objects.filter(s__gte=ugettext_lazy('b'))), [b])

    def test_marked_strings(self):
        """
        Check that strings marked as safe or needing escaping do not
        confuse the back-end.
        """
        from django.utils.safestring import mark_safe, mark_for_escaping

        a = String.objects.create(s='a')
        b = String.objects.create(s=mark_safe('b'))
        c = String.objects.create(s=mark_for_escaping('c'))

        self.assertEqual(String.objects.get(s='a'), a)
        self.assertEqual(list(String.objects.filter(s__startswith='a')), [a])
        self.assertEqual(String.objects.get(s=mark_safe('a')), a)
        self.assertEqual(
            list(String.objects.filter(s__startswith=mark_safe('a'))), [a])
        self.assertEqual(String.objects.get(s=mark_for_escaping('a')), a)
        self.assertEqual(
            list(String.objects.filter(s__startswith=mark_for_escaping('a'))),
            [a])

        self.assertEqual(String.objects.get(s='b'), b)
        self.assertEqual(list(String.objects.filter(s__startswith='b')), [b])
        self.assertEqual(String.objects.get(s=mark_safe('b')), b)
        self.assertEqual(
            list(String.objects.filter(s__startswith=mark_safe('b'))), [b])
        self.assertEqual(String.objects.get(s=mark_for_escaping('b')), b)
        self.assertEqual(
            list(String.objects.filter(s__startswith=mark_for_escaping('b'))),
            [b])

        self.assertEqual(String.objects.get(s='c'), c)
        self.assertEqual(list(String.objects.filter(s__startswith='c')), [c])
        self.assertEqual(String.objects.get(s=mark_safe('c')), c)
        self.assertEqual(
            list(String.objects.filter(s__startswith=mark_safe('c'))), [c])
        self.assertEqual(String.objects.get(s=mark_for_escaping('c')), c)
        self.assertEqual(
            list(String.objects.filter(s__startswith=mark_for_escaping('c'))),
            [c])


class FeaturesTest(TestCase):
    """
    Some things are unlikely to cause problems for SQL back-ends, but
    require special handling in nonrel.
    """

    def test_subqueries(self):
        """
        Django includes SQL statements as WHERE tree values when
        filtering using a QuerySet -- this won't "just work" with
        nonrel back-ends.

        TODO: Subqueries handling may require a bit of Django
              changing, but should be easy to support.
        """
        target = Target.objects.create(index=1)
        source = Source.objects.create(index=2, target=target)
        targets = Target.objects.all()
        with self.assertRaises(DatabaseError):
            Source.objects.get(target__in=targets)
        self.assertEqual(
            Source.objects.get(target__in=list(targets)),
            source)


class DecimalFieldTest(TestCase):
    """
    Some NoSQL databases can't handle Decimals, so respective back-ends
    convert them to strings or floats. This can cause some precision
    and sorting problems.
    """

    def setUp(self):
        for d in (Decimal('12345.6789'), Decimal('5'), Decimal('345.67'),
                  Decimal('45.6'), Decimal('2345.678'),):
            DecimalModel(decimal=d).save()

    def test_filter(self):
        d = DecimalModel.objects.get(decimal=Decimal('5.0'))

        self.assertTrue(isinstance(d.decimal, Decimal))
        self.assertEquals(str(d.decimal), '5.00')

        d = DecimalModel.objects.get(decimal=Decimal('45.60'))
        self.assertEquals(str(d.decimal), '45.60')

        # Filter argument should be converted to Decimal with 2 decimal
        #_places.
        d = DecimalModel.objects.get(decimal='0000345.67333333333333333')
        self.assertEquals(str(d.decimal), '345.67')

    def test_order(self):
        """
        Standard Django decimal-to-string conversion isn't monotonic
        (see `django.db.backends.util.format_number`).
        """
        rows = DecimalModel.objects.all().order_by('decimal')
        values = list(d.decimal for d in rows)
        self.assertEquals(values, sorted(values))

    def test_sign_extend(self):
        DecimalModel(decimal=Decimal('-0.0')).save()

        try:
            # If we've written a valid string we should be able to
            # retrieve the DecimalModel object without error.
            DecimalModel.objects.filter(decimal__lt=1)[0]
        except InvalidOperation:
            self.assertTrue(False)


class DeleteModel(models.Model):
    key = models.IntegerField(primary_key=True)
    deletable = models.BooleanField()

class BasicDeleteTest(TestCase):

    def setUp(self):
        for i in range(1, 10):
            DeleteModel(key=i, deletable=i % 2 == 0).save()

    def test_model_delete(self):
        d = DeleteModel.objects.get(pk=1)
        d.delete()

        with self.assertRaises(DeleteModel.DoesNotExist):
            DeleteModel.objects.get(pk=1)

    def test_delete_all(self):
        DeleteModel.objects.all().delete()

        self.assertEquals(0, DeleteModel.objects.all().count())

    def test_delete_filtered(self):
        DeleteModel.objects.filter(deletable=True).delete()

        self.assertEquals(5, DeleteModel.objects.all().count())


class M2MDeleteChildModel(models.Model):
    key = models.IntegerField(primary_key=True)

class M2MDeleteModel(models.Model):
    key = models.IntegerField(primary_key=True)
    deletable = models.BooleanField()
    children = models.ManyToManyField(M2MDeleteChildModel, blank=True)

class ManyToManyDeleteTest(TestCase):
    """
    Django-nonrel doesn't support many-to-many, but there may be
    models that are used which contain them, even if they're not
    accessed. This test ensures they can be deleted.
    """

    def setUp(self):
        for i in range(1, 10):
            M2MDeleteModel(key=i, deletable=i % 2 == 0).save()

    def test_model_delete(self):
        d = M2MDeleteModel.objects.get(pk=1)
        d.delete()

        with self.assertRaises(M2MDeleteModel.DoesNotExist):
            M2MDeleteModel.objects.get(pk=1)

    @expectedFailure
    def test_delete_all(self):
        M2MDeleteModel.objects.all().delete()

        self.assertEquals(0, M2MDeleteModel.objects.all().count())

    @expectedFailure
    def test_delete_filtered(self):
        M2MDeleteModel.objects.filter(deletable=True).delete()

        self.assertEquals(5, M2MDeleteModel.objects.all().count())


class QuerysetModel(models.Model):
    key = models.IntegerField(primary_key=True)

class QuerysetTest(TestCase):
    """
    Django 1.6 changes how
    """

    def setUp(self):
        for i in range(10):
            QuerysetModel.objects.create(key=i + 1)

    def test_all(self):
        self.assertEqual(10, len(QuerysetModel.objects.all()))

    def test_none(self):
        self.assertEqual(0, len(QuerysetModel.objects.none()))

########NEW FILE########
__FILENAME__ = utils
def make_tls_property(default=None):
    """
    Creates a class-wide instance property with a thread-specific
    value.
    """

    class TLSProperty(object):

        def __init__(self):
            from threading import local
            self.local = local()

        def __get__(self, instance, cls):
            if not instance:
                return self
            return self.value

        def __set__(self, instance, value):
            self.value = value

        def _get_value(self):
            return getattr(self.local, 'value', default)

        def _set_value(self, value):
            self.local.value = value
        value = property(_get_value, _set_value)

    return TLSProperty()


def getattr_by_path(obj, attr, *default):
    """
    Like getattr(), but can go down a hierarchy like "attr.subattr".
    """
    value = obj
    for part in attr.split('.'):
        if not hasattr(value, part) and len(default):
            return default[0]
        value = getattr(value, part)
        if callable(value):
            value = value()
    return value


def subdict(data, *attrs):
    """Returns a subset of the keys of a dictionary."""
    result = {}
    result.update([(key, data[key]) for key in attrs])
    return result


def equal_lists(left, right):
    """
    Compares two lists and returs True if they contain the same
    elements, but doesn't require that they have the same order.
    """
    right = list(right)
    if len(left) != len(right):
        return False
    for item in left:
        if item in right:
            del right[right.index(item)]
        else:
            return False
    return True


def object_list_to_table(headings, dict_list):
    """
    Converts objects to table-style list of rows with heading:

    Example:
    x.a = 1
    x.b = 2
    x.c = 3
    y.a = 11
    y.b = 12
    y.c = 13
    object_list_to_table(('a', 'b', 'c'), [x, y])
    results in the following (dict keys reordered for better readability):
    [
        ('a', 'b', 'c'),
        (1, 2, 3),
        (11, 12, 13),
    ]
    """
    return [headings] + [tuple([getattr_by_path(row, heading, None)
                                for heading in headings])
                         for row in dict_list]


def dict_list_to_table(headings, dict_list):
    """
    Converts dict to table-style list of rows with heading:

    Example:
    dict_list_to_table(('a', 'b', 'c'),
        [{'a': 1, 'b': 2, 'c': 3}, {'a': 11, 'b': 12, 'c': 13}])
    results in the following (dict keys reordered for better readability):
    [
        ('a', 'b', 'c'),
        (1, 2, 3),
        (11, 12, 13),
    ]
    """
    return [headings] + [tuple([row[heading] for heading in headings])
                         for row in dict_list]

########NEW FILE########
__FILENAME__ = widgets
from django.forms import widgets
from django.template.defaultfilters import filesizeformat
from django.utils.safestring import mark_safe


class BlobWidget(widgets.FileInput):

    def render(self, name, value, attrs=None):
        try:
            blob_size = len(value)
        except:
            blob_size = 0

        blob_size = filesizeformat(blob_size)
        original = super(BlobWidget, self).render(name, value, attrs=None)
        return mark_safe("%s<p>Current size: %s</p>" % (original, blob_size))

########NEW FILE########
