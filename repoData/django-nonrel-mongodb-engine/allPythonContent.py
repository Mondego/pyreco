__FILENAME__ = aggregations
class MongoAggregate(object):
    is_ordinal = False
    is_computed = False
    reduce_template = NotImplemented
    finalize_template = ''

    def __init__(self, alias, lookup, source):
        self.alias = alias
        self.lookup = lookup
        self.field = self.source = source

    def format(self, template):
        alias = 'out.%s' % self.alias
        lookup = 'doc.%s' % self.lookup
        return template.format(alias=alias, lookup=lookup)

    def initial(self):
        return {self.alias: self.initial_value}

    def reduce(self):
        return self.format(self.reduce_template)

    def finalize(self):
        return self.format(self.finalize_template)

    def as_sql(self):
        raise NotImplementedError


class Count(MongoAggregate):
    is_ordinal = True
    initial_value = 0
    reduce_template = '{alias}++'


class Min(MongoAggregate):
    initial_value = float('inf')
    reduce_template = '{alias} = ({lookup} < {alias}) ? {lookup}: {alias}'


class Max(MongoAggregate):
    initial_value = float('-inf')
    reduce_template = '{alias} = ({lookup} > {alias}) ? {lookup}: {alias}'


class Avg(MongoAggregate):
    is_computed = True

    def initial(self):
        return {'%s__count' % self.alias: 0, '%s__total' % self.alias: 0}

    reduce_template = '{alias}__count++; {alias}__total += {lookup}'
    finalize_template = '{alias} = {alias}__total / {alias}__count'


class Sum(MongoAggregate):
    is_computed = True
    initial_value = 0

    reduce_template = '{alias} += {lookup}'


_AGGREGATION_CLASSES = dict((cls.__name__, cls)
                            for cls in MongoAggregate.__subclasses__())

def get_aggregation_class_by_name(name):
    return _AGGREGATION_CLASSES[name]

########NEW FILE########
__FILENAME__ = base
import copy
import datetime
import decimal
import sys
import warnings

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.db.backends.signals import connection_created
from django.db.utils import DatabaseError
from pymongo import ReadPreference

from pymongo.collection import Collection
from pymongo.mongo_client import MongoClient
from pymongo.mongo_replica_set_client import MongoReplicaSetClient

# handle pymongo backward compatibility
try:
    from bson.objectid import ObjectId
    from bson.errors import InvalidId
except ImportError:
    from pymongo.objectid import ObjectId, InvalidId

from djangotoolbox.db.base import (
    NonrelDatabaseClient,
    NonrelDatabaseFeatures,
    NonrelDatabaseIntrospection,
    NonrelDatabaseOperations,
    NonrelDatabaseValidation,
    NonrelDatabaseWrapper
)
from djangotoolbox.db.utils import decimal_to_string

from .creation import DatabaseCreation
from .utils import CollectionDebugWrapper


class DatabaseFeatures(NonrelDatabaseFeatures):
    supports_microsecond_precision = False
    supports_long_model_names = False


class DatabaseOperations(NonrelDatabaseOperations):
    compiler_module = __name__.rsplit('.', 1)[0] + '.compiler'

    def max_name_length(self):
        return 254

    def check_aggregate_support(self, aggregate):
        import aggregations
        try:
            getattr(aggregations, aggregate.__class__.__name__)
        except AttributeError:
            raise NotImplementedError("django-mongodb-engine doesn't support "
                                      "%r aggregates." % type(aggregate))

    def sql_flush(self, style, tables, sequence_list, allow_cascade=False):
        """
        Returns a list of SQL statements that have to be executed to
        drop all `tables`. No SQL in MongoDB, so just clear all tables
        here and return an empty list.
        """
        for table in tables:
            if table.startswith('system.'):
                # Do not try to drop system collections.
                continue
            self.connection.database[table].remove()
        return []

    def validate_autopk_value(self, value):
        """
        Mongo uses ObjectId-based AutoFields.
        """
        if value is None:
            return None
        return unicode(value)

    def _value_for_db(self, value, field, field_kind, db_type, lookup):
        """
        Allows parent to handle nonrel fields, convert AutoField
        keys to ObjectIds and date and times to datetimes.

        Let everything else pass to PyMongo -- when the value is used
        the driver will raise an exception if it got anything
        unacceptable.
        """
        if value is None:
            return None

        # Parent can handle iterable fields and Django wrappers.
        value = super(DatabaseOperations, self)._value_for_db(
            value, field, field_kind, db_type, lookup)

        # Convert decimals to strings preserving order.
        if field_kind == 'DecimalField':
            value = decimal_to_string(
                value, field.max_digits, field.decimal_places)

        # Anything with the "key" db_type is converted to an ObjectId.
        if db_type == 'key':
            try:
                return ObjectId(value)

            # Provide a better message for invalid IDs.
            except (TypeError, InvalidId):
                if isinstance(value, (str, unicode)) and len(value) > 13:
                    value = value[:10] + '...'
                msg = "AutoField (default primary key) values must be " \
                      "strings representing an ObjectId on MongoDB (got " \
                      "%r instead)." % value
                if field.model._meta.db_table == 'django_site':
                    # Also provide some useful tips for (very common) issues
                    # with settings.SITE_ID.
                    msg += " Please make sure your SITE_ID contains a " \
                           "valid ObjectId string."
                raise DatabaseError(msg)

        # PyMongo can only process datatimes?
        elif db_type == 'date':
            return datetime.datetime(value.year, value.month, value.day)
        elif db_type == 'time':
            return datetime.datetime(1, 1, 1, value.hour, value.minute,
                                     value.second, value.microsecond)

        return value

    def _value_from_db(self, value, field, field_kind, db_type):
        """
        Deconverts keys, dates and times (also in collections).
        """

        # It is *crucial* that this is written as a direct check --
        # when value is an instance of serializer.LazyModelInstance
        # calling its __eq__ method does a database query.
        if value is None:
            return None

        # All keys have been turned into ObjectIds.
        if db_type == 'key':
            value = unicode(value)

        # We've converted dates and times to datetimes.
        elif db_type == 'date':
            value = datetime.date(value.year, value.month, value.day)
        elif db_type == 'time':
            value = datetime.time(value.hour, value.minute, value.second,
                                  value.microsecond)

        # Revert the decimal-to-string encoding.
        if field_kind == 'DecimalField':
            value = decimal.Decimal(value)

        return super(DatabaseOperations, self)._value_from_db(
            value, field, field_kind, db_type)


class DatabaseClient(NonrelDatabaseClient):
    pass


class DatabaseValidation(NonrelDatabaseValidation):
    pass


class DatabaseIntrospection(NonrelDatabaseIntrospection):

    def table_names(self, cursor=None):
        return self.connection.database.collection_names()

    def sequence_list(self):
        # Only required for backends that use integer primary keys.
        pass


class DatabaseWrapper(NonrelDatabaseWrapper):
    """
    Public API: connection, database, get_collection.
    """

    def __init__(self, *args, **kwargs):
        self.collection_class = kwargs.pop('collection_class', Collection)
        super(DatabaseWrapper, self).__init__(*args, **kwargs)

        self.features = DatabaseFeatures(self)
        self.ops = DatabaseOperations(self)
        self.creation = DatabaseCreation(self)
        self.introspection = DatabaseIntrospection(self)
        self.validation = DatabaseValidation(self)
        self.connected = False
        del self.connection

    def get_collection(self, name, **kwargs):
        if (kwargs.pop('existing', False) and
                name not in self.connection.database.collection_names()):
            return None
        collection = self.collection_class(self.database, name, **kwargs)
        if settings.DEBUG:
            collection = CollectionDebugWrapper(collection, self.alias)
        return collection

    def __getattr__(self, attr):
        if attr in ['connection', 'database']:
            assert not self.connected
            self._connect()
            return getattr(self, attr)
        raise AttributeError(attr)

    def _connect(self):
        settings = copy.deepcopy(self.settings_dict)

        def pop(name, default=None):
            return settings.pop(name) or default

        db_name = pop('NAME')
        host = pop('HOST')
        port = pop('PORT', 27017)
        user = pop('USER')
        password = pop('PASSWORD')
        options = pop('OPTIONS', {})

        self.operation_flags = options.pop('OPERATIONS', {})
        if not any(k in ['save', 'delete', 'update']
                   for k in self.operation_flags):
            # Flags apply to all operations.
            flags = self.operation_flags
            self.operation_flags = {'save': flags, 'delete': flags,
                                    'update': flags}

        # Lower-case all OPTIONS keys.
        for key in options.iterkeys():
            options[key.lower()] = options.pop(key)

        read_preference = options.get('read_preference')
        replicaset = options.get('replicaset')

        if not read_preference:
            read_preference = options.get('slave_okay', options.get('slaveok'))
            if read_preference:
                options['read_preference'] = ReadPreference.SECONDARY
                warnings.warn("slave_okay has been deprecated. "
                              "Please use read_preference instead.")

        if replicaset:
            connection_class = MongoReplicaSetClient
        else:
            connection_class = MongoClient

        conn_options = dict(
            host=host,
            port=int(port),
            max_pool_size=None,
            document_class=dict,
            tz_aware=False,
            _connect=True,
            auto_start_request=True,
            safe=False
        )
        conn_options.update(options)

        try:
            self.connection = connection_class(**conn_options)
            self.database = self.connection[db_name]
        except TypeError:
            exc_info = sys.exc_info()
            raise ImproperlyConfigured, exc_info[1], exc_info[2]

        if user and password:
            if not self.database.authenticate(user, password):
                raise ImproperlyConfigured("Invalid username or password.")

        self.connected = True
        connection_created.send(sender=self.__class__, connection=self)

    def _reconnect(self):
        if self.connected:
            del self.connection
            del self.database
            self.connected = False
        self._connect()

    def _commit(self):
        pass

    def _rollback(self):
        pass

    def close(self):
        pass

########NEW FILE########
__FILENAME__ = compiler
from functools import wraps
import re
import sys

import django
from django.db.models import F, NOT_PROVIDED
from django.db.models.sql import aggregates as sqlaggregates
from django.db.models.sql.constants import MULTI
from django.db.models.sql.where import OR
from django.db.utils import DatabaseError, IntegrityError
from django.utils.encoding import smart_str
from django.utils.tree import Node

from pymongo import ASCENDING, DESCENDING
from pymongo.errors import PyMongoError, DuplicateKeyError

from djangotoolbox.db.basecompiler import (
    NonrelQuery,
    NonrelCompiler,
    NonrelInsertCompiler,
    NonrelUpdateCompiler,
    NonrelDeleteCompiler,
    EmptyResultSet)

from .aggregations import get_aggregation_class_by_name
from .query import A
from .utils import safe_regex


if django.VERSION >= (1, 6):
    def get_selected_fields(query):
        fields = None
        if query.select and not query.aggregates:
            fields = [info.field.column for info in query.select]
        return fields
else:
    def get_selected_fields(query):
        fields = None
        if query.select_fields and not query.aggregates:
            fields = [field.column for field in query.select_fields]
        return fields


OPERATORS_MAP = {
    'exact':  lambda val: val,
    'gt':     lambda val: {'$gt': val},
    'gte':    lambda val: {'$gte': val},
    'lt':     lambda val: {'$lt': val},
    'lte':    lambda val: {'$lte': val},
    'in':     lambda val: {'$in': val},
    'range':  lambda val: {'$gte': val[0], '$lte': val[1]},
    'isnull': lambda val: None if val else {'$ne': None},

    # Regex matchers.
    'iexact':      safe_regex('^%s$', re.IGNORECASE),
    'startswith':  safe_regex('^%s'),
    'istartswith': safe_regex('^%s', re.IGNORECASE),
    'endswith':    safe_regex('%s$'),
    'iendswith':   safe_regex('%s$', re.IGNORECASE),
    'contains':    safe_regex('%s'),
    'icontains':   safe_regex('%s', re.IGNORECASE),
    'regex':       lambda val: re.compile(val),
    'iregex':      lambda val: re.compile(val, re.IGNORECASE),

    # Date OPs.
    'year': lambda val: {'$gte': val[0], '$lt': val[1]},
}

NEGATED_OPERATORS_MAP = {
    'exact':  lambda val: {'$ne': val},
    'gt':     lambda val: {'$lte': val},
    'gte':    lambda val: {'$lt': val},
    'lt':     lambda val: {'$gte': val},
    'lte':    lambda val: {'$gt': val},
    'in':     lambda val: {'$nin': val},
    'isnull': lambda val: {'$ne': None} if val else None,
}


def safe_call(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except DuplicateKeyError, e:
            raise IntegrityError, IntegrityError(smart_str(e)), sys.exc_info()[2]
        except PyMongoError, e:
            raise DatabaseError, DatabaseError(smart_str(e)), sys.exc_info()[2]
    return wrapper


class MongoQuery(NonrelQuery):

    def __init__(self, compiler, fields):
        super(MongoQuery, self).__init__(compiler, fields)
        self.ordering = []
        self.collection = self.compiler.get_collection()
        self.mongo_query = getattr(compiler.query, 'raw_query', {})

    def __repr__(self):
        return '<MongoQuery: %r ORDER %r>' % (self.mongo_query, self.ordering)

    def fetch(self, low_mark, high_mark):
        results = self.get_cursor()
        pk_column = self.query.get_meta().pk.column
        for entity in results:
            entity[pk_column] = entity.pop('_id')
            yield entity

    @safe_call
    def count(self, limit=None):
        results = self.get_cursor()
        if limit is not None:
            results.limit(limit)
        return results.count()

    @safe_call
    def order_by(self, ordering):
        if isinstance(ordering, bool):
            # No need to add {$natural: ASCENDING} as it's the default.
            if not ordering:
                self.ordering.append(('$natural', DESCENDING))
        else:
            for field, ascending in ordering:
                column = '_id' if field.primary_key else field.column
                direction = ASCENDING if ascending else DESCENDING
                self.ordering.append((column, direction))

    @safe_call
    def delete(self):
        options = self.connection.operation_flags.get('delete', {})
        self.collection.remove(self.mongo_query, **options)

    def get_cursor(self):
        if self.query.low_mark == self.query.high_mark:
            return []

        fields = get_selected_fields(self.query)
        cursor = self.collection.find(self.mongo_query, fields=fields)
        if self.ordering:
            cursor.sort(self.ordering)
        if self.query.low_mark > 0:
            cursor.skip(self.query.low_mark)
        if self.query.high_mark is not None:
            cursor.limit(int(self.query.high_mark - self.query.low_mark))
        return cursor

    def add_filters(self, filters, query=None):
        children = self._get_children(filters.children)

        if query is None:
            query = self.mongo_query

        if filters.connector == OR:
            assert '$or' not in query, "Multiple ORs are not supported."
            or_conditions = query['$or'] = []

        if filters.negated:
            self._negated = not self._negated

        for child in children:
            if filters.connector == OR:
                subquery = {}
            else:
                subquery = query

            if isinstance(child, Node):
                if filters.connector == OR and child.connector == OR:
                    if len(child.children) > 1:
                        raise DatabaseError("Nested ORs are not supported.")

                if filters.connector == OR and filters.negated:
                    raise NotImplementedError("Negated ORs are not supported.")

                self.add_filters(child, query=subquery)

                if filters.connector == OR and subquery:
                    or_conditions.extend(subquery.pop('$or', []))
                    if subquery:
                        or_conditions.append(subquery)

                continue

            field, lookup_type, value = self._decode_child(child)

            if lookup_type in ('month', 'day'):
                raise DatabaseError("MongoDB does not support month/day "
                                    "queries.")
            if self._negated and lookup_type == 'range':
                raise DatabaseError("Negated range lookups are not "
                                    "supported.")

            if field.primary_key:
                column = '_id'
            else:
                column = field.column

            existing = subquery.get(column)

            if isinstance(value, A):
                column, value = value.as_q(field)

            if self._negated and lookup_type in NEGATED_OPERATORS_MAP:
                op_func = NEGATED_OPERATORS_MAP[lookup_type]
                already_negated = True
            else:
                op_func = OPERATORS_MAP[lookup_type]
                if self._negated:
                    already_negated = False

            lookup = op_func(value)

            if existing is None:
                if self._negated and not already_negated:
                    lookup = {'$not': lookup}
                subquery[column] = lookup
                if filters.connector == OR and subquery:
                    or_conditions.append(subquery)
                continue

            if not isinstance(existing, dict):
                if not self._negated:
                    # {'a': o1} + {'a': o2} --> {'a': {'$all': [o1, o2]}}
                    assert not isinstance(lookup, dict)
                    subquery[column] = {'$all': [existing, lookup]}
                else:
                    # {'a': o1} + {'a': {'$not': o2}} -->
                    #     {'a': {'$all': [o1], '$nin': [o2]}}
                    if already_negated:
                        assert lookup.keys() == ['$ne']
                        lookup = lookup['$ne']
                    assert not isinstance(lookup, dict)
                    subquery[column] = {'$all': [existing], '$nin': [lookup]}
            else:
                not_ = existing.pop('$not', None)
                if not_:
                    assert not existing
                    if isinstance(lookup, dict):
                        assert lookup.keys() == ['$ne']
                        lookup = lookup.values()[0]
                    assert not isinstance(lookup, dict), (not_, lookup)
                    if self._negated:
                        # {'not': {'a': o1}} + {'a': {'not': o2}} -->
                        #     {'a': {'nin': [o1, o2]}}
                        subquery[column] = {'$nin': [not_, lookup]}
                    else:
                        # {'not': {'a': o1}} + {'a': o2} -->
                        #     {'a': {'nin': [o1], 'all': [o2]}}
                        subquery[column] = {'$nin': [not_], '$all': [lookup]}
                else:
                    if isinstance(lookup, dict):
                        if '$ne' in lookup:
                            if '$nin' in existing:
                                # {'$nin': [o1, o2]} + {'$ne': o3} -->
                                #     {'$nin': [o1, o2, o3]}
                                assert '$ne' not in existing
                                existing['$nin'].append(lookup['$ne'])
                            elif '$ne' in existing:
                                # {'$ne': o1} + {'$ne': o2} -->
                                #    {'$nin': [o1, o2]}
                                existing['$nin'] = [existing.pop('$ne'),
                                                    lookup['$ne']]
                            else:
                                existing.update(lookup)
                        else:
                            if '$in' in lookup and '$in' in existing:
                                # {'$in': o1} + {'$in': o2}
                                #    --> {'$in': o1 union o2}
                                existing['$in'] = list(
                                    set(lookup['$in'] + existing['$in']))
                            else:
                                # {'$gt': o1} + {'$lt': o2}
                                #    --> {'$gt': o1, '$lt': o2}
                                assert all(key not in existing
                                           for key in lookup.keys()), \
                                       [lookup, existing]
                                existing.update(lookup)
                    else:
                        key = '$nin' if self._negated else '$all'
                        existing.setdefault(key, []).append(lookup)

                if filters.connector == OR and subquery:
                    or_conditions.append(subquery)

        if filters.negated:
            self._negated = not self._negated


class SQLCompiler(NonrelCompiler):
    """
    Base class for all Mongo compilers.
    """
    query_class = MongoQuery

    def get_collection(self):
        return self.connection.get_collection(self.query.get_meta().db_table)

    def execute_sql(self, result_type=MULTI):
        """
        Handles aggregate/count queries.
        """
        collection = self.get_collection()
        aggregations = self.query.aggregate_select.items()

        if len(aggregations) == 1 and isinstance(aggregations[0][1],
                                                 sqlaggregates.Count):
            # Ne need for full-featured aggregation processing if we
            # only want to count().
            if result_type is MULTI:
                return [[self.get_count()]]
            else:
                return [self.get_count()]

        counts, reduce, finalize, order, initial = [], [], [], [], {}
        try:
            query = self.build_query()
        except EmptyResultSet:
            return []

        for alias, aggregate in aggregations:
            assert isinstance(aggregate, sqlaggregates.Aggregate)
            if isinstance(aggregate, sqlaggregates.Count):
                order.append(None)
                # Needed to keep the iteration order which is important
                # in the returned value.
                # XXX: This actually does a separate query... performance?
                counts.append(self.get_count())
                continue

            aggregate_class = get_aggregation_class_by_name(
                aggregate.__class__.__name__)
            lookup = aggregate.col
            if isinstance(lookup, tuple):
                # lookup is a (table_name, column_name) tuple.
                # Get rid of the table name as aggregations can't span
                # multiple tables anyway.
                if lookup[0] != collection.name:
                    raise DatabaseError("Aggregations can not span multiple "
                                        "tables (tried %r and %r)." %
                                        (lookup[0], collection.name))
                lookup = lookup[1]
            self.query.aggregates[alias] = aggregate = aggregate_class(
                alias, lookup, aggregate.source)
            order.append(alias) # Just to keep the right order.
            initial.update(aggregate.initial())
            reduce.append(aggregate.reduce())
            finalize.append(aggregate.finalize())

        reduce = 'function(doc, out){ %s }' % '; '.join(reduce)
        finalize = 'function(out){ %s }' % '; '.join(finalize)
        cursor = collection.group(None, query.mongo_query, initial, reduce,
                                  finalize)

        ret = []
        for alias in order:
            result = cursor[0][alias] if alias else counts.pop(0)
            if result_type is MULTI:
                result = [result]
            ret.append(result)
        return ret


class SQLInsertCompiler(NonrelInsertCompiler, SQLCompiler):

    @safe_call
    def insert(self, docs, return_id=False):
        """
        Stores a document using field columns as element names, except
        for the primary key field for which "_id" is used.

        If just a {pk_field: None} mapping is given a new empty
        document is created, otherwise value for a primary key may not
        be None.
        """
        for doc in docs:
            try:
                doc['_id'] = doc.pop(self.query.get_meta().pk.column)
            except KeyError:
                pass
            if doc.get('_id', NOT_PROVIDED) is None:
                if len(doc) == 1:
                    # insert with empty model
                    doc.clear()
                else:
                    raise DatabaseError("Can't save entity with _id set to None")

        collection = self.get_collection()
        options = self.connection.operation_flags.get('save', {})

        if return_id:
            return collection.save(doc, **options)
        else:
            collection.save(doc, **options)


# TODO: Define a common nonrel API for updates and add it to the nonrel
#       backend base classes and port this code to that API.
class SQLUpdateCompiler(NonrelUpdateCompiler, SQLCompiler):
    query_class = MongoQuery

    def update(self, values):
        multi = True
        spec = {}
        for field, value in values:
            if field.primary_key:
                raise DatabaseError("Can not modify _id.")
            if getattr(field, 'forbids_updates', False):
                raise DatabaseError("Updates on %ss are not allowed." %
                                    field.__class__.__name__)
            if hasattr(value, 'evaluate'):
                # .update(foo=F('foo') + 42) --> {'$inc': {'foo': 42}}
                lhs, rhs = value.children
                assert (value.connector in (value.ADD, value.SUB) and
                        not value.negated and
                        isinstance(lhs, F) and not isinstance(rhs, F) and
                        lhs.name == field.name)
                if value.connector == value.SUB:
                    rhs = -rhs
                action = '$inc'
                value = rhs
            else:
                # .update(foo=123) --> {'$set': {'foo': 123}}
                action = '$set'
            spec.setdefault(action, {})[field.column] = value

            if field.unique:
                multi = False

        return self.execute_update(spec, multi)

    @safe_call
    def execute_update(self, update_spec, multi=True, **kwargs):
        collection = self.get_collection()
        try:
            criteria = self.build_query().mongo_query
        except EmptyResultSet:
            return 0
        options = self.connection.operation_flags.get('update', {})
        options = dict(options, **kwargs)
        info = collection.update(criteria, update_spec, multi=multi, **options)
        if info is not None:
            return info.get('n')


class SQLDeleteCompiler(NonrelDeleteCompiler, SQLCompiler):
    pass

########NEW FILE########
__FILENAME__ = fields
from django.db import models

from .tokenizer import BaseTokenizer


__all__ = ['TokenizedField']


class TokenizedField(models.Field):

    def __init__(self, *args, **kwargs):
        super(TokenizedField, self).__init__(*args, **kwargs)
        as_textfield = kwargs.pop('as_textfield', False)
        self._tokenizer = kwargs.pop('tokenizer', BaseTokenizer)()
        self.parent_field = models.CharField(*args, **kwargs)

    def contribute_to_class(self, cls, name):
        super(TokenizedField, self).contribute_to_class(
            cls, '%s_tokenized' % name)
        setattr(self, 'parent_field_name', name)
        cls.add_to_class(name, self.parent_field)

    def get_db_prep_lookup(self, lookup_type, value, connection,
                           prepared=False):
        # If for some reason value is being converted to list by some
        # internal processing we'll convert it back to string.
        # For Example: When using the 'in' lookup type.
        if isinstance(value, list):
            value = ''.join(value)

        # When 'exact' is used we'll perform an exact_phrase query
        # using the $all operator otherwhise we'll just tokenized
        # the value. Djangotoolbox will do the remaining checks.
        if lookup_type == 'exact':
            return {'$all': self._tokenizer.tokenize(value)}
        return self._tokenizer.tokenize(value)

    def pre_save(self, model_instance, add):
        return self._tokenizer.tokenize(getattr(model_instance,
                                                self.parent_field_name))

########NEW FILE########
__FILENAME__ = tokenizer
import re


class BaseTokenizer(object):
    """
    Really simple tokenizer.
    """

    @staticmethod
    def tokenize(text):
        """
        Splits text into a list of words removing any symbol and
        converts it into lowercase.
        """
        tokens = []
        text = text.lower()
        for dot_item in BaseTokenizer.regex_split('\.(?=[a-zA-Z\s])', text):
            for comman_item in BaseTokenizer.regex_split(',(?=[a-zA-Z\s])',
                                                         dot_item):
                for item in comman_item.split(' '):
                    item = BaseTokenizer.tokenize_item(item)
                    if item:
                        tokens.append(item)
        return tokens

    @staticmethod
    def regex_split(regex, text):
        for item in re.split(regex, text, re.I):
            yield item

    @staticmethod
    def tokenize_item(item):
        """
        If it is an int/float it returns the item (there's no need to
        remove , or .).
        """
        item = item.strip()
        try:
            float(item)
            return item
        except ValueError:
            pass

        # This will keep underscores.
        return re.sub(r'[^\w]', '', item)

########NEW FILE########
__FILENAME__ = creation
from django.db.utils import DatabaseError

from pymongo import DESCENDING

from djangotoolbox.db.creation import NonrelDatabaseCreation

from .utils import make_index_list


class DatabaseCreation(NonrelDatabaseCreation):

    # We'll store decimals as strings, dates and times as datetimes,
    # sets as lists and automatic keys as ObjectIds.
    data_types = dict(NonrelDatabaseCreation.data_types, **{
        'SetField': 'list',
    })

    def db_type(self, field):
        """
        Returns the db_type of the field for non-relation fields, and
        the db_type of a primary key field of a related model for
        ForeignKeys, OneToOneFields and ManyToManyFields.
        """
        if field.rel is not None:
            field = field.rel.get_related_field()
        return field.db_type(connection=self.connection)

    def sql_indexes_for_model(self, model, termstyle):
        """Creates indexes for all fields in ``model``."""
        meta = model._meta

        if not meta.managed or meta.proxy:
            return []

        collection = self.connection.get_collection(meta.db_table)

        def ensure_index(*args, **kwargs):
            if ensure_index.first_index:
                print "Installing indices for %s.%s model." % \
                      (meta.app_label, meta.object_name)
                ensure_index.first_index = False
            return collection.ensure_index(*args, **kwargs)
        ensure_index.first_index = True

        newstyle_indexes = getattr(meta, 'indexes', None)
        if newstyle_indexes:
            self._handle_newstyle_indexes(ensure_index, meta, newstyle_indexes)
        else:
            self._handle_oldstyle_indexes(ensure_index, meta)

    def _handle_newstyle_indexes(self, ensure_index, meta, indexes):
        from djangotoolbox.fields import AbstractIterableField, \
            EmbeddedModelField

        # Django indexes.
        for field in meta.local_fields:
            if not (field.unique or field.db_index):
                # field doesn't need an index.
                continue
            column = '_id' if field.primary_key else field.column
            ensure_index(column, unique=field.unique)

        # Django unique_together indexes.
        indexes = list(indexes)

        for fields in getattr(meta, 'unique_together', []):
            assert isinstance(fields, (list, tuple))
            indexes.append({'fields': make_index_list(fields), 'unique': True})

        def get_column_name(field):
            opts = meta
            parts = field.split('.')
            for i, part in enumerate(parts):
                field = opts.get_field(part)
                parts[i] = field.column
                if isinstance(field, AbstractIterableField):
                    field = field.item_field
                if isinstance(field, EmbeddedModelField):
                    opts = field.embedded_model._meta
                else:
                    break
            return '.'.join(parts)

        for index in indexes:
            if isinstance(index, dict):
                kwargs = index.copy()
                fields = kwargs.pop('fields')
            else:
                fields, kwargs = index, {}
            fields = [(get_column_name(name), direction)
                      for name, direction in make_index_list(fields)]
            ensure_index(fields, **kwargs)

    def _handle_oldstyle_indexes(self, ensure_index, meta):
        from warnings import warn
        warn("'descending_indexes', 'sparse_indexes' and 'index_together' "
             "are deprecated and will be ignored as of version 0.6. "
             "Use 'indexes' instead.", DeprecationWarning)
        sparse_indexes = []
        descending_indexes = set(getattr(meta, 'descending_indexes', ()))

        # Lets normalize the sparse_index values changing [], set() to ().
        for idx in set(getattr(meta, 'sparse_indexes', ())):
            sparse_indexes.append(
                isinstance(idx, (tuple, set, list)) and tuple(idx) or idx)

        # Ordinary indexes.
        for field in meta.local_fields:
            if not (field.unique or field.db_index):
                # field doesn't need an index.
                continue
            column = '_id' if field.primary_key else field.column
            if field.name in descending_indexes:
                column = [(column, DESCENDING)]
            ensure_index(column, unique=field.unique,
                         sparse=field.name in sparse_indexes)

        def create_compound_indexes(indexes, **kwargs):
            # indexes: (field1, field2, ...).
            if not indexes:
                return
            kwargs['sparse'] = tuple(indexes) in sparse_indexes
            indexes = [(meta.get_field(name).column, direction) for
                       name, direction in make_index_list(indexes)]
            ensure_index(indexes, **kwargs)

        # Django unique_together indexes.
        for indexes in getattr(meta, 'unique_together', []):
            assert isinstance(indexes, (list, tuple))
            create_compound_indexes(indexes, unique=True)

        # MongoDB compound indexes.
        index_together = getattr(meta, 'mongo_index_together', [])
        if index_together:
            if isinstance(index_together[0], dict):
                # Assume index_together = [{'fields' : [...], ...}].
                for args in index_together:
                    kwargs = args.copy()
                    create_compound_indexes(kwargs.pop('fields'), **kwargs)
            else:
                # Assume index_together = ['foo', 'bar', ('spam', -1), etc].
                create_compound_indexes(index_together)

        return []

    def sql_create_model(self, model, *unused):
        """
        Creates a collection that will store instances of the model.

        Technically we only need to precreate capped collections, but
        we'll create them for all models, so database introspection
        knows about empty "tables".
        """
        name = model._meta.db_table
        if getattr(model._meta, 'capped', False):
            kwargs = {'capped': True}
            size = getattr(model._meta, 'collection_size', None)
            if size is not None:
                kwargs['size'] = size
            max_ = getattr(model._meta, 'collection_max', None)
            if max_ is not None:
                kwargs['max'] = max_
        else:
            kwargs = {}

        collection = self.connection.get_collection(name, existing=True)
        if collection is not None:
            opts = dict(collection.options())
            if opts != kwargs:
                raise DatabaseError("Can't change options of an existing "
                                    "collection: %s --> %s." % (opts, kwargs))

        # Initialize the capped collection:
        self.connection.get_collection(name, **kwargs)

        return [], {}

    def set_autocommit(self):
        """There's no such thing in MongoDB."""

    def create_test_db(self, verbosity=1, autoclobber=False):
        """
        No need to create databases in MongoDB :)
        but we can make sure that if the database existed is emptied.
        """
        test_database_name = self._get_test_db_name()

        self.connection.settings_dict['NAME'] = test_database_name
        # This is important. Here we change the settings so that all
        # other code thinks that the chosen database is now the test
        # database. This means that nothing needs to change in the test
        # code for working with connections, databases and collections.
        # It will appear the same as when working with non-test code.

        # Force a reconnect to ensure we're using the test database.
        self.connection._reconnect()

        # In this phase it will only drop the database if it already
        # existed which could potentially happen if the test database
        # was created but was never dropped at the end of the tests.
        self._drop_database(test_database_name)

        from django.core.management import call_command
        call_command('syncdb', verbosity=max(verbosity-1, 0),
                     interactive=False, database=self.connection.alias)

        return test_database_name

    def destroy_test_db(self, old_database_name, verbosity=1):
        if verbosity >= 1:
            print "Destroying test database for alias '%s'..." % \
                  self.connection.alias
        test_database_name = self.connection.settings_dict['NAME']
        self._drop_database(test_database_name)
        self.connection.settings_dict['NAME'] = old_database_name

    def _drop_database(self, database_name):
        for collection in self.connection.introspection.table_names():
            if not collection.startswith('system.'):
                self.connection.database.drop_collection(collection)

########NEW FILE########
__FILENAME__ = fields
from django.db import connections, models

from gridfs import GridFS
from gridfs.errors import NoFile

# handle pymongo backward compatibility
try:
    from bson.objectid import ObjectId
except ImportError:
    from pymongo.objectid import ObjectId 
    
        
from django_mongodb_engine.utils import make_struct


__all__ = ['GridFSField', 'GridFSString']


class GridFSField(models.Field):
    """
    GridFS field to store large chunks of data (blobs) in GridFS.

    Model instances keep references (ObjectIds) to GridFS files
    (:class:`gridfs.GridOut`) which are fetched on first attribute
    access.

    :param delete:
        Whether to delete the data stored in the GridFS (as GridFS
        files) when model instances are deleted (default: :const:`True`).

        Note that this doesn't have any influence on what happens if
        you update the blob value by assigning a new file, in which
        case the old file is always deleted.
    """
    forbids_updates = True

    def __init__(self, *args, **kwargs):
        self._versioning = kwargs.pop('versioning', False)
        self._autodelete = kwargs.pop('delete', not self._versioning)
        if self._versioning:
            import warnings
            warnings.warn("GridFSField versioning will be deprecated on "
                          "version 0.6. If you consider this option useful "
                          "please add a comment on issue #65 with your use "
                          "case.", PendingDeprecationWarning)

        kwargs['max_length'] = 24
        kwargs.setdefault('default', None)
        kwargs.setdefault('null', True)
        super(GridFSField, self).__init__(*args, **kwargs)

    def db_type(self, connection):
        return 'gridfs'

    def contribute_to_class(self, model, name):
        # GridFSFields are represented as properties in the model
        # class. Let 'foo' be an instance of a model that has the
        # GridFSField 'gridf'. 'foo.gridf' then calls '_property_get'
        # and 'foo.gridfs = bar' calls '_property_set(bar)'.
        super(GridFSField, self).contribute_to_class(model, name)
        setattr(model, self.attname, property(self._property_get,
                                              self._property_set))
        if self._autodelete:
            models.signals.pre_delete.connect(self._on_pre_delete,
                                              sender=model)

    def _property_get(self, model_instance):
        """
        Gets the file from GridFS using the id stored in the model.
        """
        meta = self._get_meta(model_instance)
        if meta.filelike is None and meta.oid is not None:
            gridfs = self._get_gridfs(model_instance)
            if self._versioning:
                try:
                    meta.filelike = gridfs.get_last_version(filename=meta.oid)
                    return meta.filelike
                except NoFile:
                    pass
            meta.filelike = gridfs.get(meta.oid)
        return meta.filelike

    def _property_set(self, model_instance, value):
        """
        Sets a new value.

        If value is an ObjectID it must be coming from Django's ORM
        internals being the value fetched from the database on query.
        In that case just update the id stored in the model instance.
        Otherwise it sets the value and checks whether a save is needed
        or not.
        """
        meta = self._get_meta(model_instance)
        if isinstance(value, ObjectId) and meta.oid is None:
            meta.oid = value
        else:
            meta.should_save = meta.filelike != value
            meta.filelike = value

    def pre_save(self, model_instance, add):
        meta = self._get_meta(model_instance)
        if meta.should_save:
            gridfs = self._get_gridfs(model_instance)
            if not self._versioning and meta.oid is not None:
                # We're putting a new GridFS file, so get rid of the
                # old one if we weren't explicitly asked to keep it.
                gridfs.delete(meta.oid)
            meta.should_save = False
            if not self._versioning or meta.oid is None:
                meta.oid = gridfs.put(meta.filelike)
            else:
                gridfs.put(meta.filelike, filename=meta.oid)
        return meta.oid

    def _on_pre_delete(self, sender, instance, using, signal, **kwargs):
        """
        Deletes the files associated with this isntance.

        If versioning is enabled all versions will be deleted.
        """
        gridfs = self._get_gridfs(instance)
        meta = self._get_meta(instance)
        try:
            while self._versioning and meta.oid:
                last = gridfs.get_last_version(filename=meta.oid)
                gridfs.delete(last._id)
        except NoFile:
            pass

        gridfs.delete(meta.oid)

    def _get_meta(self, model_instance):
        meta_name = '_%s_meta' % self.attname
        meta = getattr(model_instance, meta_name, None)
        if meta is None:
            meta_cls = make_struct('filelike', 'oid', 'should_save')
            meta = meta_cls(None, None, None)
            setattr(model_instance, meta_name, meta)
        return meta

    def _get_gridfs(self, model_instance):
        model = model_instance.__class__
        return GridFS(connections[model.objects.db].database,
                      model._meta.db_table)


class GridFSString(GridFSField):
    """
    Similar to :class:`GridFSField`, but the data is represented as a
    bytestring on Python side. This implies that all data has to be
    copied **into memory**, so :class:`GridFSString` is for smaller
    chunks of data only.
    """

    def _property_get(self, model):
        filelike = super(GridFSString, self)._property_get(model)
        if filelike is None:
            return ''
        if hasattr(filelike, 'read'):
            return filelike.read()
        return filelike


try:
    # Used to satisfy South when introspecting models that use
    # GridFSField/GridFSString fields. Custom rules could be added
    # if needed.
    from south.modelsinspector import add_introspection_rules
    add_introspection_rules(
        [], ['^django_mongodb_engine\.fields\.GridFSField'])
    add_introspection_rules(
        [], ['^django_mongodb_engine\.fields\.GridFSString'])
except ImportError:
    pass

########NEW FILE########
__FILENAME__ = tellsiteid
from django.core.management.base import NoArgsCommand


class Command(NoArgsCommand):
    help = "Tells the ID of the default Site object."

    def handle_noargs(self, **options):
        verbosity = int(options.get('verbosity', 1))
        site_id = self._get_site_id()
        if verbosity >= 1:
            self.stdout.write(
                "The default site's ID is %r. To use the sites framework, "
                "add this line to settings.py:\nSITE_ID=%r" %
                (site_id, site_id))
        else:
            self.stdout.write(site_id)

    def _get_site_id(self):
        from django.contrib.sites.models import Site
        return Site.objects.get().id

########NEW FILE########
__FILENAME__ = models
# If you wonder what this file is about please head over to '__init__.py' :-)

from django.db.models import signals


def class_prepared_mongodb_signal(sender, *args, **kwargs):
    mongo_meta = getattr(sender, 'MongoMeta', None)
    if mongo_meta is not None:
        for attr in dir(mongo_meta):
            if not attr.startswith('_'):
                if attr == 'index_together':
                    attr_name = 'mongo_index_together'
                else:
                    attr_name = attr
                setattr(sender._meta, attr_name, getattr(mongo_meta, attr))

signals.class_prepared.connect(class_prepared_mongodb_signal)

########NEW FILE########
__FILENAME__ = query
from warnings import warn
warn("A() queries are deprecated as of 0.5 and will be removed in 0.6.",
     DeprecationWarning)


from djangotoolbox.fields import RawField, AbstractIterableField, \
    EmbeddedModelField


__all__ = ['A']


DJANGOTOOLBOX_FIELDS = (RawField, AbstractIterableField, EmbeddedModelField)


class A(object):

    def __init__(self, op, value):
        self.op = op
        self.val = value

    def as_q(self, field):
        if isinstance(field, DJANGOTOOLBOX_FIELDS):
            return '%s.%s' % (field.column, self.op), self.val
        else:
            raise TypeError("Can not use A() queries on %s." %
                            field.__class__.__name__)

########NEW FILE########
__FILENAME__ = router
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured


_mongodbs = []

def _init_mongodbs():
    for name, options in settings.DATABASES.iteritems():
        if options['ENGINE'] != 'django_mongodb_engine':
            continue
        if options.get('IS_DEFAULT'):
            _mongodbs.insert(0, name)
        else:
            _mongodbs.append(name)

    if not _mongodbs:
        raise ImproperlyConfigured("No MongoDB database found in "
                                   "settings.DATABASES.")


class MongoDBRouter(object):
    """
    A Django router to manage models that should be stored in MongoDB.

    MongoDBRouter uses the MONGODB_MANAGED_APPS and MONGODB_MANAGED_MODELS
    settings to know which models/apps should be stored inside MongoDB.

    See: http://docs.djangoproject.com/en/dev/topics/db/multi-db/#topics-db-multi-db-routing
    """

    def __init__(self):
        if not _mongodbs:
            _init_mongodbs()
        self.managed_apps = [app.split('.')[-1] for app in
                             getattr(settings, 'MONGODB_MANAGED_APPS', [])]
        self.managed_models = getattr(settings, 'MONGODB_MANAGED_MODELS', [])

    def is_managed(self, model):
        """
        Returns True if the model passed is managed by Django MongoDB
        Engine.
        """
        if model._meta.app_label in self.managed_apps:
            return True
        full_name = '%s.%s' % (model._meta.app_label, model._meta.object_name)
        return full_name in self.managed_models

    def db_for_read(self, model, **hints):
        """
        Points all operations on MongoDB models to a MongoDB database.
        """
        if self.is_managed(model):
            return _mongodbs[0]

    db_for_write = db_for_read # Same algorithm.

    def allow_relation(self, obj1, obj2, **hints):
        """
        Allows any relation if a model in myapp is involved.
        """
        return self.is_managed(obj2) or None

    def allow_syncdb(self, db, model):
        """
        Makes sure that MongoDB models only appear on MongoDB databases.
        """
        if db in _mongodbs:
            return self.is_managed(model)
        elif self.is_managed(model):
            return db in _mongodbs
        return None

########NEW FILE########
__FILENAME__ = south
import warnings


warnings.warn(
    '`django_mongodb_engine.south.DatabaseOperations` south database backend '
    'is actually a dummy backend that does nothing at all. It will be '
    'removed in favor of the `django_mongodb_engine.south_adapter.DatabaseOperations` '
    'that provides the correct behavior.',
    DeprecationWarning
)

class DatabaseOperations(object):
    """
    MongoDB implementation of database operations.
    """

    backend_name = 'django_mongodb_engine'

    supports_foreign_keys = False
    has_check_constraints = False
    has_ddl_transactions = False

    def __init__(self, db_alias):
        pass

    def add_column(self, table_name, name, field, *args, **kwds):
        pass

    def alter_column(self, table_name, name, field, explicit_name=True):
        pass

    def delete_column(self, table_name, column_name):
        pass

    def rename_column(self, table_name, old, new):
        pass

    def create_unique(self, table_name, columns):
        pass

    def delete_unique(self, table_name, columns):
        pass

    def delete_primary_key(self, table_name):
        pass

    def delete_table(self, table_name, cascade=True):
        pass

    def connection_init(self):
        pass

    def send_pending_create_signals(self, verbosity=False, interactive=False):
        pass

    def get_pending_creates(self):
        pass

    def start_transaction(self):
        pass

    def rollback_transaction(self):
        pass

    def rollback_transactions_dry_run(self):
        pass

    def clear_run_data(self, pending_creates):
        pass

    def create_table(self, unique=True, null=True, blank=True):
        pass

    def send_create_signal(self, verbosity=False, interactive=False):
        pass

    def execute_deferred_sql(self):
        pass

    def commit_transaction(self):
        pass

########NEW FILE########
__FILENAME__ = south_adapter
# This is needed until the sibling south module is removed
from __future__ import absolute_import 

from django.core.exceptions import ImproperlyConfigured
from django.db.models.fields import NOT_PROVIDED
from django.db.utils import IntegrityError
from pymongo.errors import DuplicateKeyError

from .utils import make_index_list


try:
    from south.db.generic import DatabaseOperations
except ImportError:
    raise ImproperlyConfigured('Make sure to install south before trying to '
                               'import this module.')


class DatabaseOperations(DatabaseOperations):
    """
    MongoDB implementation of database operations.
    """

    backend_name = 'django_mongodb_engine'

    supports_foreign_keys = False
    has_check_constraints = False
    has_ddl_transactions = False

    def _get_collection(self, name):
        return self._get_connection().get_collection(name)

    def add_column(self, table_name, field_name, field, keep_default=True):
        # Make sure the field is correctly prepared
        field.set_attributes_from_name(field_name)
        if field.has_default():
            default = field.get_default()
            if default is not None:
                connection = self._get_connection()
                collection = self._get_collection(table_name)
                name = field.column
                db_prep_save = field.get_db_prep_save(default, connection=connection)
                default = connection.ops.value_for_db(db_prep_save, field)
                # Update all the documents that haven't got this field yet
                collection.update({name: {'$exists': False}},
                                  {'$set': {name: default}})
            if not keep_default:
                field.default = NOT_PROVIDED

    def alter_column(self, table_name, column_name, field, explicit_name=True):
        # Since MongoDB is schemaless there's no way to coerce field datatype
        pass

    def delete_column(self, table_name, name):
        collection = self._get_collection(table_name)
        collection.update({}, {'$unset': {name: 1}})

    def rename_column(self, table_name, old, new):
        collection = self._get_collection(table_name)
        collection.update({}, {'$rename': {old: new}})

    def create_unique(self, table_name, columns, drop_dups=False):
        collection = self._get_collection(table_name)
        try:
            index_list = list(make_index_list(columns))
            collection.create_index(index_list, unique=True, drop_dups=drop_dups)
        except DuplicateKeyError as e:
            raise IntegrityError(e)

    def delete_unique(self, table_name, columns):
        collection = self._get_collection(table_name)
        index_list = list(make_index_list(columns))
        collection.drop_index(index_list)

    def delete_primary_key(self, table_name):
        # MongoDB doesn't support primary key deletion
        pass

    def create_table(self, table_name, fields, **kwargs):
        # Collection creation is automatic but code calling this might expect
        # it to exist, thus we create it here. i.e. Calls to `rename_table` will
        # fail if the collection doesn't already exist.
        connection = self._get_connection()
        connection.database.create_collection(table_name, **kwargs)
    
    def rename_table(self, table_name, new_table_name):
        collection = self._get_collection(table_name)
        collection.rename(new_table_name)

    def delete_table(self, table_name, cascade=True):
        connection = self._get_connection()
        connection.database.drop_collection(table_name)

    def start_transaction(self):
        # MongoDB doesn't support transactions
        pass

    def rollback_transaction(self):
        # MongoDB doesn't support transactions
        pass

    def commit_transaction(self):
        # MongoDB doesn't support transactions
        pass
    
    def rollback_transactions_dry_run(self):
        # MongoDB doesn't support transactions
        pass

########NEW FILE########
__FILENAME__ = storage
import os
import urlparse

from django.core.exceptions import ImproperlyConfigured
from django.core.files.storage import Storage
from django.utils.encoding import filepath_to_uri

from gridfs import GridFS, NoFile


def _get_subcollections(collection):
    """
    Returns all sub-collections of `collection`.
    """
    # XXX: Use the MongoDB API for this once it exists.
    for name in collection.database.collection_names():
        cleaned = name[:name.rfind('.')]
        if cleaned != collection.name and cleaned.startswith(collection.name):
            yield cleaned


class GridFSStorage(Storage):
    """
    GridFS Storage backend for Django.

    This backend aims to add a GridFS storage to upload files to
    using Django's file fields.

    For performance, the file hirarchy is represented as a tree of
    MongoDB sub-collections.

    (One could use a flat list, but to list a directory '/this/path/'
    we would have to execute a search over the whole collection and
    then filter the results to exclude those not starting by
    '/this/path' using that model.)

    :param location:
       (optional) Name of the top-level node that holds the files. This
       value of `location` is prepended to all file paths, so it works
       like the `location` setting for Django's built-in
       :class:`~django.core.files.storage.FileSystemStorage`.
    :param collection:
        Name of the collection the file tree shall be stored in.
        Defaults to 'storage'.
    :param database:
        Alias of the Django database to use. Defaults to 'default' (the
        default Django database).
    :param base_url:
        URL that serves the files in GridFS (for instance, through
        nginx-gridfs).
        Defaults to None (file not accessible through a URL).
    """

    def __init__(self, location='', collection='storage', database='default',
                 base_url=None):
        self.location = location.strip(os.sep)
        self.collection = collection
        self.database = database
        self.base_url = base_url

        if not self.collection:
            raise ImproperlyConfigured("'collection' may not be empty.")

        if self.base_url and not self.base_url.endswith('/'):
            raise ImproperlyConfigured("If set, 'base_url' must end with a "
                                       "slash.")

    def _open(self, path, mode='rb'):
        """
        Returns a :class:`~gridfs.GridOut` file opened in `mode`, or
        raises :exc:`~gridfs.errors.NoFile` if the requested file
        doesn't exist and mode is not 'w'.
        """
        gridfs, filename = self._get_gridfs(path)
        try:
            return gridfs.get_last_version(filename)
        except NoFile:
            if 'w' in mode:
                return gridfs.new_file(filename=filename)
            else:
                raise

    def _save(self, path, content):
        """
        Saves `content` into the file at `path`.
        """
        gridfs, filename = self._get_gridfs(path)
        gridfs.put(content, filename=filename)
        return path

    def delete(self, path):
        """
        Deletes the file at `path` if it exists.
        """
        gridfs, filename = self._get_gridfs(path)
        try:
            gridfs.delete(gridfs.get_last_version(filename=filename)._id)
        except NoFile:
            pass

    def exists(self, path):
        """
        Returns `True` if the file at `path` exists in GridFS.
        """
        gridfs, filename = self._get_gridfs(path)
        return gridfs.exists(filename=filename)

    def listdir(self, path):
        """
        Returns a tuple (folders, lists) that are contained in the
        folder `path`.
        """
        gridfs, filename = self._get_gridfs(path)
        assert not filename
        subcollections = _get_subcollections(gridfs._GridFS__collection)
        return set(c.split('.')[-1] for c in subcollections), gridfs.list()

    def size(self, path):
        """
        Returns the size of the file at `path`.
        """
        gridfs, filename = self._get_gridfs(path)
        return gridfs.get_last_version(filename=filename).length

    def url(self, name):
        if self.base_url is None:
            raise ValueError("This file is not accessible via a URL.")
        return urlparse.urljoin(self.base_url, filepath_to_uri(name))

    def created_time(self, path):
        """
        Returns the datetime the file at `path` was created.
        """
        gridfs, filename = self._get_gridfs(path)
        return gridfs.get_last_version(filename=filename).upload_date

    def _get_gridfs(self, path):
        """
        Returns a :class:`~gridfs.GridFS` using the sub-collection for
        `path`.
        """
        path, filename = os.path.split(path)
        path = os.path.join(self.collection, self.location, path.strip(os.sep))
        collection_name = path.replace(os.sep, '.').strip('.')

        if not hasattr(self, '_db'):
            from django.db import connections
            self._db = connections[self.database].database

        return GridFS(self._db, collection_name), filename

########NEW FILE########
__FILENAME__ = utils
import re
import time

from django.conf import settings
from django.db.backends.util import logger

from pymongo import ASCENDING
from pymongo.cursor import Cursor


def first(test_func, iterable):
    for item in iterable:
        if test_func(item):
            return item


def safe_regex(regex, *re_args, **re_kwargs):

    def wrapper(value):
        return re.compile(regex % re.escape(value), *re_args, **re_kwargs)
    wrapper.__name__ = 'safe_regex (%r)' % regex

    return wrapper


def make_struct(*attrs):

    class _Struct(object):
        __slots__ = attrs

        def __init__(self, *args):
            for attr, arg in zip(self.__slots__, args):
                setattr(self, attr, arg)

    return _Struct


def make_index_list(indexes):
    if isinstance(indexes, basestring):
        indexes = [indexes]
    for index in indexes:
        if not isinstance(index, tuple):
            index = index, ASCENDING
        yield index


class CollectionDebugWrapper(object):

    def __init__(self, collection, db_alias):
        self.collection = collection
        self.alias = db_alias

    def __getattr__(self, attr):
        return getattr(self.collection, attr)

    def profile_call(self, func, args=(), kwargs={}):
        start = time.time()
        retval = func(*args, **kwargs)
        duration = time.time() - start
        return duration, retval

    def log(self, op, duration, args, kwargs=None):
        args = ' '.join(str(arg) for arg in args)
        msg = '%s.%s (%.2f) %s' % (self.collection.name, op, duration, args)
        kwargs = dict((k, v) for k, v in kwargs.iteritems() if v)
        if kwargs:
            msg += ' %s' % kwargs
        if len(settings.DATABASES) > 1:
            msg = self.alias + '.' + msg
        logger.debug(msg, extra={'duration': duration})

    def find(self, *args, **kwargs):
        if not 'slave_okay' in kwargs and self.collection.slave_okay:
            kwargs['slave_okay'] = True
        return DebugCursor(self, self.collection, *args, **kwargs)

    def logging_wrapper(method):

        def wrapper(self, *args, **kwargs):
            func = getattr(self.collection, method)
            duration, retval = self.profile_call(func, args, kwargs)
            self.log(method, duration, args, kwargs)
            return retval

        return wrapper

    save = logging_wrapper('save')
    remove = logging_wrapper('remove')
    update = logging_wrapper('update')
    map_reduce = logging_wrapper('map_reduce')
    inline_map_reduce = logging_wrapper('inline_map_reduce')

    del logging_wrapper


class DebugCursor(Cursor):

    def __init__(self, collection_wrapper, *args, **kwargs):
        self.collection_wrapper = collection_wrapper
        super(DebugCursor, self).__init__(*args, **kwargs)

    def _refresh(self):
        super_meth = super(DebugCursor, self)._refresh
        if self._Cursor__id is not None:
            return super_meth()
        # self.__id is None: first time the .find() iterator is
        # entered. find() profiling happens here.
        duration, retval = self.collection_wrapper.profile_call(super_meth)
        kwargs = {'limit': self._Cursor__limit, 'skip': self._Cursor__skip,
                  'sort': self._Cursor__ordering}
        self.collection_wrapper.log('find', duration, [self._Cursor__spec],
                                    kwargs)
        return retval

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
__FILENAME__ = models
from django.db import models

from django_mongodb_engine.contrib import MongoDBManager


class Article(models.Model):
    author = models.ForeignKey('Author')
    text = models.TextField()

    objects = MongoDBManager()


class Author(models.Model):
    pass

########NEW FILE########
__FILENAME__ = tests
mapfunc = """
function() {
  this.text.split(' ').forEach(
    function(word) { emit(word, 1) }
  )
}
"""

reducefunc = """
function reduce(key, values) {
  return values.length; /* == sum(values) */
}
"""

__test__ = {
    'mr': """
>>> from models import Author, Article

>>> bob = Author.objects.create()
>>> ann = Author.objects.create()

>>> bobs_article = Article.objects.create(author=bob, text="A B C")
>>> anns_article = Article.objects.create(author=ann, text="A B C D E")

Map/Reduce over all articles:
>>> for pair in Article.objects.map_reduce(mapfunc, reducefunc, 'wordcount'):
...     print pair.key, pair.value
A 2.0
B 2.0
C 2.0
D 1.0
E 1.0

Map/Reduce over Bob's articles:
>>> for pair in Article.objects.filter(author=bob).map_reduce(
            mapfunc, reducefunc, 'wordcount'):
...    print pair.key, pair.value
A 1.0
B 1.0
C 1.0
"""}

########NEW FILE########
__FILENAME__ = views
# Create your views here.

########NEW FILE########
__FILENAME__ = settings
DATABASES = {
    'default': {
        'ENGINE': 'django_mongodb_engine',
        'NAME': 'mapreduce',
    },
}

INSTALLED_APPS = ['mr']

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import patterns, include, url


# Uncomment the next two lines to enable the admin:
# from django.contrib import admin
# admin.autodiscover()

urlpatterns = patterns('',
    # Examples:
    # url(r'^$', 'v1.views.home', name='home'),
    # url(r'^v1/', include('v1.foo.urls')),

    # Uncomment the admin/doc line below to enable admin documentation:
    # url(r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    # url(r'^admin/', include(admin.site.urls)),
)

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
__FILENAME__ = models
from django.db import models

from djangotoolbox.fields import ListField


class Post(models.Model):
    title = models.CharField()
    text = models.TextField()
    tags = ListField()
    comments = ListField()

########NEW FILE########
__FILENAME__ = tests
__test__ = {'v1': """
>>> from nonrelblog.models import Post
>>> post = Post.objects.create(
...     title='Hello MongoDB!',
...     text='Just wanted to drop a note from Django. Cya!',
...     tags=['mongodb', 'django']
... )

Surely we want to add some comments.

>>> post.comments
[]
>>> post.comments.extend(['Great post!', 'Please, do more of these!'])
>>> post.save()

Look and see, it has actually been saved!

>>> Post.objects.get().comments
[u'Great post!', u'Please, do more of these!']
"""}

########NEW FILE########
__FILENAME__ = views
# Create your views here.

########NEW FILE########
__FILENAME__ = settings
DATABASES = {
    'default': {
        'ENGINE': 'django_mongodb_engine',
        'NAME': 'tutorial',
    },
}

INSTALLED_APPS = ['nonrelblog']

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import patterns, include, url


# Uncomment the next two lines to enable the admin:
# from django.contrib import admin
# admin.autodiscover()

urlpatterns = patterns('',
    # Examples:
    # url(r'^$', 'v1.views.home', name='home'),
    # url(r'^v1/', include('v1.foo.urls')),

    # Uncomment the admin/doc line below to enable admin documentation:
    # url(r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    # url(r'^admin/', include(admin.site.urls)),
)

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
__FILENAME__ = models
from django.db import models

from djangotoolbox.fields import ListField, EmbeddedModelField


class Post(models.Model):
    created_on = models.DateTimeField(auto_now_add=True, null=True)
    title = models.CharField()
    text = models.TextField()
    tags = ListField()
    comments = ListField(EmbeddedModelField('Comment')) # <---


class Comment(models.Model):
    created_on = models.DateTimeField(auto_now_add=True)
    author = EmbeddedModelField('Author')
    text = models.TextField()


class Author(models.Model):
    name = models.CharField()
    email = models.EmailField()

    def __unicode__(self):
        return '%s (%s)' % (self.name, self.email)

########NEW FILE########
__FILENAME__ = tests
__test__ = {
    'v4': """
>>> from nonrelblog.models import Post
>>> from nonrelblog.models import Comment, Author
>>> Comment(
...     author=Author(name='Bob', email='bob@example.org'),
...     text='The cake is a lie'
... ).save()
>>> comment = Comment.objects.get()
>>> comment.author
<Author: Bob (bob@example.org)>
>>> Post(
...     title='I like cake',
...     comments=[comment]
... ).save()
>>> post = Post.objects.get(title='I like cake')
>>> post.comments
[<Comment: Comment object>]
>>> post.comments[0].author.email
u'bob@example.org'
"""}

########NEW FILE########
__FILENAME__ = views
# Create your views here.

########NEW FILE########
__FILENAME__ = settings
DATABASES = {
    'default': {
        'ENGINE': 'django_mongodb_engine',
        'NAME': 'tutorial',
    },
}

INSTALLED_APPS = ['nonrelblog']

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import patterns, include, url


# Uncomment the next two lines to enable the admin:
# from django.contrib import admin
# admin.autodiscover()

urlpatterns = patterns('',
    # Examples:
    # url(r'^$', 'v1.views.home', name='home'),
    # url(r'^v1/', include('v1.foo.urls')),

    # Uncomment the admin/doc line below to enable admin documentation:
    # url(r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    # url(r'^admin/', include(admin.site.urls)),
)

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
__FILENAME__ = models
from django.db import models

from djangotoolbox.fields import ListField, EmbeddedModelField


class Post(models.Model):
    created_on = models.DateTimeField(auto_now_add=True, null=True)
    title = models.CharField(max_length=100)
    text = models.TextField()
    tags = ListField()
    comments = ListField(EmbeddedModelField('Comment')) # <---


class Comment(models.Model):
    created_on = models.DateTimeField(auto_now_add=True)
    author = EmbeddedModelField('Author')
    text = models.TextField()


class Author(models.Model):
    name = models.CharField(max_length=50)
    email = models.EmailField()

    def __unicode__(self):
        return '%s (%s)' % (self.name, self.email)

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import patterns, url
from django.views.generic import ListView, DetailView

from models import Post


post_detail = DetailView.as_view(model=Post)
post_list = ListView.as_view(model=Post)

urlpatterns = patterns('',
    url(r'^post/(?P<pk>[a-z\d]+)/$', post_detail, name='post_detail'),
    url(r'^$', post_list, name='post_list'),
)

########NEW FILE########
__FILENAME__ = settings
DATABASES = {
    'default': {
        'ENGINE': 'django_mongodb_engine',
        'NAME': 'tutorial',
    }
},

INSTALLED_APPS = ['nonrelblog']

ROOT_URLCONF = 'urls'

DEBUG = TEMPLATE_DEBUG = True

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import patterns, include, url

# Uncomment the next two lines to enable the admin:
# from django.contrib import admin
# admin.autodiscover()

urlpatterns = patterns('',
    # Uncomment the admin/doc line below to enable admin documentation:
    # url(r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    # url(r'^admin/', include(admin.site.urls)),

    url('', include('nonrelblog.urls')),
)

########NEW FILE########
__FILENAME__ = admin
from django.contrib.admin import site

from gridfsuploads.models import FileUpload


site.register(FileUpload)

########NEW FILE########
__FILENAME__ = models
from django.db import models

from gridfsuploads import gridfs_storage


class FileUpload(models.Model):
    created_on = models.DateTimeField(auto_now_add=True)
    file = models.FileField(storage=gridfs_storage, upload_to='/')

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import patterns, url


urlpatterns = patterns('gridfsuploads.views',
    ('^(?P<path>.+)', 'serve_from_gridfs'),
)

########NEW FILE########
__FILENAME__ = views
from mimetypes import guess_type

from django.conf import settings
from django.http import HttpResponse, Http404

from gridfs.errors import NoFile
from gridfsuploads import gridfs_storage
from gridfsuploads.models import FileUpload


if settings.DEBUG:

    def serve_from_gridfs(request, path):
        # Serving GridFS files through Django is inefficient and
        # insecure. NEVER USE IN PRODUCTION!
        try:
            gridfile = gridfs_storage.open(path)
        except NoFile:
            raise Http404
        else:
            return HttpResponse(gridfile, mimetype=guess_type(path)[0])

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
__FILENAME__ = models
from django.db import models

from djangotoolbox.fields import ListField, EmbeddedModelField


class Post(models.Model):
    created_on = models.DateTimeField(auto_now_add=True, null=True)
    title = models.CharField(max_length=100)
    text = models.TextField()
    tags = ListField()
    comments = ListField(EmbeddedModelField('Comment')) # <---


class Comment(models.Model):
    created_on = models.DateTimeField(auto_now_add=True)
    author = EmbeddedModelField('Author')
    text = models.TextField()


class Author(models.Model):
    name = models.CharField(max_length=50)
    email = models.EmailField()

    def __unicode__(self):
        return '%s (%s)' % (self.name, self.email)

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import patterns, url
from django.views.generic import ListView, DetailView

from models import Post


post_detail = DetailView.as_view(model=Post)
post_list = ListView.as_view(model=Post)

urlpatterns = patterns('',
    url(r'^post/(?P<pk>[a-z\d]+)/$', post_detail, name='post_detail'),
    url(r'^$', post_list, name='post_list'),
)

########NEW FILE########
__FILENAME__ = settings
DATABASES = {
    'default': {
        'ENGINE': 'django_mongodb_engine',
        'NAME': 'tutorial',
    },
}

INSTALLED_APPS = [
    'django.contrib.contenttypes',
    'django.contrib.auth',
    'django.contrib.admin',

    'nonrelblog',
    'gridfsuploads',
]

ROOT_URLCONF = 'urls'

DEBUG = TEMPLATE_DEBUG = True

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import patterns, include, url

# Uncomment the next two lines to enable the admin:
from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
    # Uncomment the admin/doc line below to enable admin documentation:
    # url(r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    url(r'^admin/', include(admin.site.urls)),

    url('^uploads/', include('gridfsuploads.urls')),
    url('', include('nonrelblog.urls')),
)

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
__FILENAME__ = models
from django.db import models

from djangotoolbox.fields import ListField, EmbeddedModelField

from django_mongodb_engine.contrib import MongoDBManager


class Post(models.Model):
    created_on = models.DateTimeField(auto_now_add=True, null=True)
    title = models.CharField(max_length=100)
    text = models.TextField()
    tags = ListField()
    comments = ListField(EmbeddedModelField('Comment')) # <---

    objects = MongoDBManager()


class Comment(models.Model):
    created_on = models.DateTimeField(auto_now_add=True)
    author = EmbeddedModelField('Author')
    text = models.TextField()


class Author(models.Model):
    name = models.CharField(max_length=50)
    email = models.EmailField()

    def __unicode__(self):
        return '%s (%s)' % (self.name, self.email)

########NEW FILE########
__FILENAME__ = tests
mapfunc = """
function map() {
  /* `this` refers to the current document */
  this.comments.forEach(function(comment) {
    emit(comment.author.name, 1);
  });
}
"""

reducefunc = """
function reduce(id, values) {
  /* [1, 1, ..., 1].length is the same as sum([1, 1, ..., 1]) */
  return values.length;
}
"""

__test__ = {'mapreduce': """
>>> from nonrelblog.models import *

Add some data so we can actually mapreduce anything.
Bob:   3 comments
Ann:   6 comments
Alice: 9 comments
>>> authors = [Author(name='Bob', email='bob@example.org'),
...            Author(name='Ann', email='ann@example.org'),
...            Author(name='Alice', email='alice@example.org')]
>>> for distribution in [(0, 1, 2), (1, 2, 3), (2, 3, 4)]:
...     comments = []
...     for author, ncomments in zip(authors, distribution):
...         comments.extend([Comment(author=author)
...                         for i in xrange(ncomments)])
...     Post(comments=comments).save()

------------------------
Kick off the Map/Reduce:
------------------------
>>> pairs = Post.objects.map_reduce(mapfunc, reducefunc, out='temp',
...                                 delete_collection=True)
>>> for pair in pairs:
...     print pair.key, pair.value
Alice 9.0
Ann 6.0
Bob 3.0
"""}

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import patterns, url
from django.views.generic import ListView, DetailView
from models import Post

post_detail = DetailView.as_view(model=Post)
post_list = ListView.as_view(model=Post)

urlpatterns = patterns('',
    url(r'^post/(?P<pk>[a-z\d]+)/$', post_detail, name='post_detail'),
    url(r'^$', post_list, name='post_list'),
)

########NEW FILE########
__FILENAME__ = settings
DATABASES = {
    'default': {
        'ENGINE': 'django_mongodb_engine',
        'NAME': 'tutorial',
    },
}

INSTALLED_APPS = [
    'django.contrib.contenttypes',
    'django.contrib.auth',
    'django.contrib.admin',

    'nonrelblog',
]

ROOT_URLCONF = 'urls'

DEBUG = TEMPLATE_DEBUG = True

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import patterns, include, url
from django.contrib import admin


admin.autodiscover()

urlpatterns = patterns('',
    # Uncomment the admin/doc line below to enable admin documentation:
    # url(r'^admin/doc/', include('django.contrib.admindocs.urls')),

    url(r'^admin/', include(admin.site.urls)),

    url('', include('nonrelblog.urls')),
)

########NEW FILE########
__FILENAME__ = conf
# coding: utf-8
import sys; sys.path.append('.')
from .utils import get_current_year, get_git_head

project = 'Django MongoDB Engine'
copyright = '2010-%d, Jonas Haag, Flavio Percoco Premoli and contributors' % \
            get_current_year()

extensions = ['sphinx.ext.autodoc', 'sphinx.ext.intersphinx']

master_doc = 'index'
exclude_patterns = ['_build']

pygments_style = 'friendly'

intersphinx_mapping = {
    'python':  ('http://docs.python.org', None),
    'pymongo': ('http://api.mongodb.org/python/current/', None),
    'django':  ('http://docs.djangoproject.com/en/dev/',
                'http://docs.djangoproject.com/en/dev/_objects/'),
}

# -- Options for HTML output ---------------------------------------------------

html_title = project

html_last_updated_fmt = '%b %d, %Y'
git_head = get_git_head()
if git_head:
    html_last_updated_fmt += ' (%s)' % git_head[:7]

html_theme = 'mongodbtheme'
html_theme_path = ['mongodbtheme', '.']
html_show_copyright = False

# Custom sidebar templates, maps document names to template names.
html_sidebars = {'**': ['localtoc.html', 'sidebar.html']}

# If false, no module index is generated.
html_domain_indices = False

# If false, no index is generated.
html_use_index = False

########NEW FILE########
__FILENAME__ = utils
from datetime import datetime
from subprocess import CalledProcessError, check_output


def get_current_year():
    return datetime.utcnow().year


def get_git_head():
    try:
        return check_output(['git', 'rev-parse', 'HEAD'])
    except CalledProcessError:
        pass
    except OSError, exc:
        if exc.errno != 2:
            raise

########NEW FILE########
__FILENAME__ = models
from django.db import models


class Person(models.Model):
    age = models.IntegerField()
    birthday = models.DateTimeField()

########NEW FILE########
__FILENAME__ = tests
from datetime import datetime

from django.db.models.aggregates import Count, Sum, Max, Min, Avg

from .utils import TestCase
from models import Person


class SimpleTest(TestCase):

    def test_aggregations(self):
        for age, birthday in (
            [4, (2007, 12, 25)],
            [4, (2006, 1, 1)],
            [1, (2008, 12, 1)],
            [4, (2006, 6, 1)],
            [12, (1998, 9, 1)],
        ):
            Person.objects.create(age=age, birthday=datetime(*birthday))

        aggregates = Person.objects.aggregate(Min('age'), Max('age'),
                                              avgage=Avg('age'))
        self.assertEqual(aggregates, {'age__min': 1, 'age__max': 12,
                                      'avgage': 5.0})

        # With filters and testing the sqlaggregates->mongoaggregate
        # conversion.
        aggregates = Person.objects.filter(age__gte=4).aggregate(
            Min('birthday'), Max('birthday'), Avg('age'), Count('id'))
        self.assertEqual(aggregates, {
            'birthday__max': datetime(2007, 12, 25, 0, 0),
            'birthday__min': datetime(1998, 9, 1, 0, 0),
            'age__avg': 6.0,
            'id__count': 4,
        })

########NEW FILE########
__FILENAME__ = utils
../utils.py
########NEW FILE########
__FILENAME__ = views

########NEW FILE########
__FILENAME__ = models
from django.conf import settings
from django.db import models
from django.utils.translation import ugettext_lazy as _

from django_mongodb_engine.contrib import MongoDBManager
from django_mongodb_engine.contrib.search.fields import TokenizedField


class MapReduceModel(models.Model):
    n = models.IntegerField()
    m = models.IntegerField()

    objects = MongoDBManager()


class MapReduceModelWithCustomPrimaryKey(models.Model):
    primarykey = models.CharField(max_length=100, primary_key=True)
    data = models.CharField(max_length=100)
    objects = MongoDBManager()


class Post(models.Model):
    content = TokenizedField(max_length=255)

    def __unicode__(self):
        return "Post"

########NEW FILE########
__FILENAME__ = tests
from __future__ import with_statement

from functools import partial

from django.db.models import Q
from django.db.utils import DatabaseError

from django_mongodb_engine.contrib import MapReduceResult

from models import *
from utils import TestCase, get_collection, skip


class MapReduceTests(TestCase):

    def test_map_reduce(self, inline=False):
        mapfunc = """
            function map() {
                for(i=0; i<this.n; ++i) {
                    emit(this._id, this.m)
                }
            }
        """

        reducefunc = """
            function reduce(key, values) {
                var res = 0
                values.forEach(function(x) { res += x})
                return res
            }
        """

        if inline:
            map_reduce = MapReduceModel.objects.inline_map_reduce
        else:
            map_reduce = partial(MapReduceModel.objects.map_reduce,
                                 out='m/r-out')
        map_reduce = partial(map_reduce, mapfunc, reducefunc)

        random_numbers = [
            (3, 4),
            (6, 19),
            (5, 8),
            (0, 20), # This instance won't be emitted by `map`.
            (2, 77),
            (300, 10),
        ]

        for n, m in random_numbers:
            MapReduceModel(n=n, m=m).save()

        # Test mapfunc + reducefunc.
        documents = map_reduce()
        documents = list(documents)
        self.assertEqual(len(documents), len(random_numbers) - 1)
        self.assertEqual(sum(doc.value for doc in documents),
                         sum(n * m for n, m in random_numbers))

        # Test MapReduceResult.
        obj = documents[0].model.objects.get(id=documents[0].key)
        self.assert_(isinstance(obj, MapReduceModel))
        self.assertEqual((obj.n, obj.m), random_numbers[0])
        self.assert_(obj.id)

        # Collection should not have been perished.
        if not inline:
            result_collection = get_collection('m/r-out')
            self.assertEqual(result_collection.count(),
                             len(random_numbers) - 1)

            # Test drop_collection.
            map_reduce(drop_collection=True).next()
            self.assertEqual(get_collection('m/r-out').count(), 0)

        # Test arbitrary kwargs.
        documents = list(map_reduce(limit=3))
        self.assertEqual(len(documents), 3)
        self.assertEqual(sum(doc.value for doc in documents),
                         sum(n * m for n, m in random_numbers[:3]))

        # Test with .filter(...).
        qs = MapReduceModel.objects.filter(n__lt=300).filter(~Q(m__in=[4]))
        if inline:
            documents = qs.inline_map_reduce(mapfunc, reducefunc)
        else:
            documents = list(qs.map_reduce(mapfunc,
                                           reducefunc, out='m/r-out'))
        self.assertEqual(len(documents), len(random_numbers) - 2 - 1)
        self.assertEqual(sum(doc.value for doc in documents),
                         sum(n * m for n, m in random_numbers[1:-1]))

    def test_inline_map_reduce(self):
        self.test_map_reduce(inline=True)
        self.test_map_reduce_with_custom_primary_key(inline=True)

    def test_map_reduce_with_custom_primary_key(self, inline=False):
        mapfunc = """ function() { emit(this._id, null) } """
        reducefunc = """ function(key, values) { return null } """
        for pk, data in [
            ('foo', 'hello!'),
            ('bar', 'yo?'),
            ('blurg', 'wuzzup'),
        ]:
            MapReduceModelWithCustomPrimaryKey(
                primarykey=pk, data=data).save()

        if inline:
            somedoc = MapReduceModelWithCustomPrimaryKey.objects \
                            .inline_map_reduce(mapfunc, reducefunc)[0]
        else:
            somedoc = MapReduceModelWithCustomPrimaryKey.objects.map_reduce(
                            mapfunc, reducefunc, out='m/r-out').next()
        self.assertEqual(somedoc.key, 'bar') # Ordered by pk.
        self.assertEqual(somedoc.value, None)
        obj = somedoc.model.objects.get(pk=somedoc.key)
        self.assert_(not hasattr(obj, 'id') and not hasattr(obj, '_id'))
        self.assertEqual(obj, MapReduceModelWithCustomPrimaryKey(pk='bar',
                                                                 data='yo?'))


class RawQueryTests(TestCase):

    def setUp(self):
        for i in xrange(10):
            MapReduceModel.objects.create(n=i, m=i * 2)

    def test_raw_query(self):
        len(MapReduceModel.objects.raw_query({'n': {'$gt': 5}})) # 11
        self.assertEqual(
            list(MapReduceModel.objects.filter(n__gt=5)),
            list(MapReduceModel.objects.raw_query({'n': {'$gt': 5}})))
        self.assertEqual(
            list(MapReduceModel.objects.filter(n__lt=9, n__gt=5)),
            list(MapReduceModel.objects.raw_query({'n': {'$lt': 9}})
                    .filter(n__gt=5)))

        MapReduceModel.objects.raw_query({'n': {'$lt': 3}}).update(m=42)
        self.assertEqual(
            list(MapReduceModel.objects.raw_query({'n': {'$gt': 0}})
                    .filter(n__lt=3)),
            list(MapReduceModel.objects.all()[1:3]))
        self.assertEqual(
            list(MapReduceModel.objects.values_list('m')[:5]),
            [(42,), (42,), (42,), (6,), (8,)])

    def test_raw_update(self):
        from django.db.models import Q
        MapReduceModel.objects.raw_update(Q(n__lte=3), {'$set': {'n': -1}})
        self.assertEqual([o.n for o in MapReduceModel.objects.all()],
                         [-1, -1, -1, -1, 4, 5, 6, 7, 8, 9])
        MapReduceModel.objects.raw_update({'n': -1}, {'$inc': {'n': 2}})
        self.assertEqual([o.n for o in MapReduceModel.objects.all()],
                         [1, 1, 1, 1, 4, 5, 6, 7, 8, 9])


# TODO: Line breaks.
class FullTextTest(TestCase):

    def test_simple_fulltext(self):
        blog = Post(content="simple, full text.... search? test")
        blog.save()

        self.assertEqual(
            Post.objects.get(content="simple, full text.... search? test"),
            blog)
        self.assertEqual(
            Post.objects.get(content_tokenized="simple, search? test"),
            blog)

    def test_simple_fulltext_filter(self):
        Post(content="simple, fulltext search test").save()
        Post(content="hey, how's, it, going.").save()
        Post(content="this full text search... seems to work... "
                     "pretty? WELL").save()
        Post(content="I would like to use MongoDB for FULL "
                     "text search").save()

        self.assertEqual(
            len(Post.objects.filter(content_tokenized="full text")), 2)
        self.assertEqual(
            len(Post.objects.filter(content_tokenized="search")), 3)
        self.assertEqual(
            len(Post.objects.filter(content_tokenized="It-... GoiNg")), 1)

    def test_int_fulltext_lookup(self):
        Post(content="this full text search... seems to work... "
                     "pretty? WELL").save()
        Post(content="I would like to use MongoDB for FULL "
                     "text search").save()
        Post(content="just some TEXT without the f u l l  word").save()

        self.assertEqual(
            len(Post.objects.filter(content_tokenized__in="full text")), 3)

    def test_or_fulltext_queries(self):
        Post(content="Happy New Year Post.... Enjoy").save()
        Post(content="So, Django is amazing, we all know that but django and "
                     "mongodb is event better ;)").save()
        Post(content="Testing the full text django + mongodb "
                     "implementation").save()

        self.assertEqual(
            len(Post.objects.filter(
                Q(content_tokenized="django mongodb better?") |
                Q(content_tokenized="full text mongodb"))),
            2)

    @skip("Broken.")
    def test_and_fulltext_queries(self):
        Post(content="Happy New Year Post.... Enjoy").save()
        Post(content="So, Django is amazing, we all know that but django and "
                     "mongodb is event better ;)").save()
        post = Post(content="Testing the full text django + mongodb "
                            "implementation")
        post.save()

        self.assertEqual(
            Post.objects.get(
                Q(content_tokenized="django mongodb") &
                Q(content_tokenized="testing")).pk,
            post.pk)

    def test_for_wrong_lookups(self):
        # This is because full text queries run over a list of
        # tokenized values so djangotoolbox will complain.
        # We should find a workaround for this.
        # For example: Using the iexact lookup could be useful because
        # it could be passed to the tokenizer in order to support Case
        # Sensitive Case Insensitive queries.
        with self.assertRaises(DatabaseError):
            Post.objects.get(content_tokenized__iexact="django mongodb")
            Post.objects.get(content_tokenized__icontains="django mongodb")


class DistinctTests(TestCase):

    def test_distinct(self):
        for i in xrange(10):
            for j in xrange(i):
                MapReduceModel.objects.create(n=i, m=i * 2)

        self.assertEqual(MapReduceModel.objects.distinct('m'),
                         [2, 4, 6, 8, 10, 12, 14, 16, 18])

        self.assertEqual(MapReduceModel.objects.filter(n=6).distinct('m'), [12])

########NEW FILE########
__FILENAME__ = utils
../utils.py
########NEW FILE########
__FILENAME__ = views

########NEW FILE########
__FILENAME__ = dbindexes

########NEW FILE########
__FILENAME__ = models
from django.db import models

from djangotoolbox.fields import DictField, EmbeddedModelField


class EmbeddedModel(models.Model):
    charfield = models.CharField(max_length=3, blank=False)
    datetime = models.DateTimeField(null=True)
    datetime_auto_now_add = models.DateTimeField(auto_now_add=True)
    datetime_auto_now = models.DateTimeField(auto_now=True)


class Model(models.Model):
    x = models.IntegerField()
    em = EmbeddedModelField(EmbeddedModel)
    dict_emb = DictField(EmbeddedModelField(EmbeddedModel))


# Docstring example copy.
class Address(models.Model):
    street = models.CharField(max_length=200)
    postal_code = models.IntegerField()
    city = models.CharField(max_length=100)


class Customer(models.Model):
    name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    address = EmbeddedModelField(Address)

########NEW FILE########
__FILENAME__ = tests
from django_mongodb_engine.query import A

from models import *
from utils import TestCase, get_collection


class EmbeddedModelFieldTestCase(TestCase):

    def test_query_embedded(self):
        Model(x=3, em=EmbeddedModel(charfield='foo')).save()
        obj = Model(x=3, em=EmbeddedModel(charfield='blurg'))
        obj.save()
        Model(x=3, em=EmbeddedModel(charfield='bar')).save()
        obj_from_db = Model.objects.get(em=A('charfield', 'blurg'))
        self.assertEqual(obj, obj_from_db)

########NEW FILE########
__FILENAME__ = utils
../utils.py
########NEW FILE########
__FILENAME__ = views

########NEW FILE########
__FILENAME__ = models
"""
7. The lookup API

This demonstrates features of the database API.
"""

from django.conf import settings
from django.db import models, DEFAULT_DB_ALIAS, connection


class Author(models.Model):
    name = models.CharField(max_length=100)

    class Meta:
        ordering = ('name', )


class Article(models.Model):
    headline = models.CharField(max_length=100)
    pub_date = models.DateTimeField()
    author = models.ForeignKey(Author, blank=True, null=True)

    class Meta:
        ordering = ('-pub_date', 'headline')

    def __unicode__(self):
        return self.headline


class Tag(models.Model):
    articles = models.ManyToManyField(Article)
    name = models.CharField(max_length=100)

    class Meta:
        ordering = ('name', )

########NEW FILE########
__FILENAME__ = tests
from datetime import datetime
from operator import attrgetter

from django.core.exceptions import FieldError
from django.db import connection
from django.db.utils import DatabaseError
from django.test import TestCase, skipUnlessDBFeature

# handle pymongo backward compatibility
try:
    from bson.objectid import ObjectId
except ImportError:
    from pymongo.objectid import ObjectId

from models import Author, Article, Tag


class LookupTests(TestCase):

    def setUp(self):
        # Create a few Authors.
        self.au1 = Author(name='Author 1')
        self.au1.save()
        self.au2 = Author(name='Author 2')
        self.au2.save()
        # Create a couple of Articles.
        self.a1 = Article(headline='Article 1',
                          pub_date=datetime(2005, 7, 26), author=self.au1)
        self.a1.save()
        self.a2 = Article(headline='Article 2',
                          pub_date=datetime(2005, 7, 27), author=self.au1)
        self.a2.save()
        self.a3 = Article(headline='Article 3',
                          pub_date=datetime(2005, 7, 27), author=self.au1)
        self.a3.save()
        self.a4 = Article(headline='Article 4',
                          pub_date=datetime(2005, 7, 28), author=self.au1)
        self.a4.save()
        self.a5 = Article(headline='Article 5',
                          pub_date=datetime(2005, 8, 1, 9, 0),
                          author=self.au2)
        self.a5.save()
        self.a6 = Article(headline='Article 6',
                          pub_date=datetime(2005, 8, 1, 8, 0),
                          author=self.au2)
        self.a6.save()
        self.a7 = Article(headline='Article 7',
                          pub_date=datetime(2005, 7, 27), author=self.au2)
        self.a7.save()
        # Create a few Tags.
        self.t1 = Tag(name='Tag 1')
        self.t1.save()
        self.t1.articles.add(self.a1, self.a2, self.a3)
        self.t2 = Tag(name='Tag 2')
        self.t2.save()
        self.t2.articles.add(self.a3, self.a4, self.a5)
        self.t3 = Tag(name='Tag 3')
        self.t3.save()
        self.t3.articles.add(self.a5, self.a6, self.a7)

    def test_exists(self):
        # We can use .exists() to check that there are some.
        self.assertTrue(Article.objects.exists())
        for a in Article.objects.all():
            a.delete()
        # There should be none now!
        self.assertFalse(Article.objects.exists())

    @skipUnlessDBFeature('supports_date_lookup_using_string')
    def test_lookup_date_as_str(self):
        # A date lookup can be performed using a string search.
        self.assertQuerysetEqual(
            Article.objects.filter(pub_date__startswith='2005'),
            [
                '<Article: Article 5>',
                '<Article: Article 6>',
                '<Article: Article 4>',
                '<Article: Article 2>',
                '<Article: Article 3>',
                '<Article: Article 7>',
                '<Article: Article 1>',
            ])

    def test_iterator(self):
        # Each QuerySet gets iterator(), which is a generator that
        # "lazily" returns results using database-level iteration.
        self.assertQuerysetEqual(
            Article.objects.iterator(),
            [
                'Article 5',
                'Article 6',
                'Article 4',
                'Article 2',
                'Article 3',
                'Article 7',
                'Article 1',
            ],
            transform=attrgetter('headline'))
        # iterator() can be used on any QuerySet.
        self.assertQuerysetEqual(
            Article.objects.filter(headline__endswith='4').iterator(),
            ['Article 4'],
            transform=attrgetter('headline'))

    def test_count(self):
        # count() returns the number of objects matching search criteria.
        self.assertEqual(Article.objects.count(), 7)
        self.assertEqual(
            Article.objects.filter(pub_date__exact=datetime(2005, 7, 27))
                .count(), 3)
        self.assertEqual(
            Article.objects.filter(headline__startswith='Blah blah')
                .count(), 0)

        # count() should respect sliced query sets.
        articles = Article.objects.all()
        self.assertEqual(articles.count(), 7)
        self.assertEqual(articles[:4].count(), 4)
        self.assertEqual(articles[1:100].count(), 6)
        self.assertEqual(articles[10:100].count(), 0)

        # Date and date/time lookups can also be done with strings.
        self.assertEqual(
            Article.objects.filter(pub_date__exact='2005-07-27 00:00:00')
                .count(), 3)

    def test_in_bulk(self):
        # in_bulk() takes a list of IDs and returns a dictionary
        # mapping IDs to objects.
        arts = Article.objects.in_bulk([self.a1.id, self.a2.id])
        self.assertEqual(arts[self.a1.id], self.a1)
        self.assertEqual(arts[self.a2.id], self.a2)
        self.assertEqual(
            Article.objects.in_bulk([self.a3.id]), {self.a3.id: self.a3})
        self.assertEqual(
            Article.objects.in_bulk(set([self.a3.id])), {self.a3.id: self.a3})
        self.assertEqual(
            Article.objects.in_bulk(frozenset([self.a3.id])),
            {self.a3.id: self.a3})
        self.assertEqual(
            Article.objects.in_bulk((self.a3.id,)), {self.a3.id: self.a3})
        self.assertEqual(Article.objects.in_bulk([ObjectId()]), {})
        self.assertEqual(Article.objects.in_bulk([]), {})
        self.assertRaises(DatabaseError, Article.objects.in_bulk, 'foo')
        self.assertRaises(TypeError, Article.objects.in_bulk)
        self.assertRaises(TypeError, Article.objects.in_bulk,
                          headline__startswith='Blah')

    def test_values(self):
        # values() returns a list of dictionaries instead of object
        # instances -- and you can specify which fields you want to
        # retrieve.
        identity = lambda x: x
        self.assertQuerysetEqual(
            Article.objects.values('headline'),
            [
                {'headline': u'Article 5'},
                {'headline': u'Article 6'},
                {'headline': u'Article 4'},
                {'headline': u'Article 2'},
                {'headline': u'Article 3'},
                {'headline': u'Article 7'},
                {'headline': u'Article 1'},
            ],
            transform=identity)
        self.assertQuerysetEqual(
            Article.objects.filter(pub_date__exact=datetime(2005, 7, 27))
                .values('id'),
            [{'id': self.a2.id}, {'id': self.a3.id}, {'id': self.a7.id}],
            transform=identity)
        self.assertQuerysetEqual(
            Article.objects.values('id', 'headline'),
            [
                {'id': self.a5.id, 'headline': 'Article 5'},
                {'id': self.a6.id, 'headline': 'Article 6'},
                {'id': self.a4.id, 'headline': 'Article 4'},
                {'id': self.a2.id, 'headline': 'Article 2'},
                {'id': self.a3.id, 'headline': 'Article 3'},
                {'id': self.a7.id, 'headline': 'Article 7'},
                {'id': self.a1.id, 'headline': 'Article 1'},
            ],
            transform=identity)
        # You can use values() with iterator() for memory savings,
        # because iterator() uses database-level iteration.
        self.assertQuerysetEqual(
            Article.objects.values('id', 'headline').iterator(),
            [
                {'headline': u'Article 5', 'id': self.a5.id},
                {'headline': u'Article 6', 'id': self.a6.id},
                {'headline': u'Article 4', 'id': self.a4.id},
                {'headline': u'Article 2', 'id': self.a2.id},
                {'headline': u'Article 3', 'id': self.a3.id},
                {'headline': u'Article 7', 'id': self.a7.id},
                {'headline': u'Article 1', 'id': self.a1.id},
            ],
            transform=identity)

    def test_values_list(self):
        # values_list() is similar to values(), except that the results
        # are returned as a list of tuples, rather than a list of
        # dictionaries. Within each tuple, the order of the elements is
        # the same as the order of fields in the values_list() call.
        identity = lambda x: x
        self.assertQuerysetEqual(
            Article.objects.values_list('headline'),
            [
                (u'Article 5',),
                (u'Article 6',),
                (u'Article 4',),
                (u'Article 2',),
                (u'Article 3',),
                (u'Article 7',),
                (u'Article 1',),
            ], transform=identity)
        self.assertQuerysetEqual(
            Article.objects.values_list('id').order_by('id'),
            [(self.a1.id,), (self.a2.id,), (self.a3.id,), (self.a4.id,),
             (self.a5.id,), (self.a6.id,), (self.a7.id,)],
            transform=identity)
        self.assertQuerysetEqual(
            Article.objects.values_list('id', flat=True).order_by('id'),
            [self.a1.id, self.a2.id, self.a3.id, self.a4.id, self.a5.id,
             self.a6.id, self.a7.id],
            transform=identity)
        self.assertRaises(TypeError, Article.objects.values_list, 'id',
                          'headline', flat=True)

    def test_get_next_previous_by(self):
        # Every DateField and DateTimeField creates get_next_by_FOO()
        # and get_previous_by_FOO() methods. In the case of identical
        # date values, these methods will use the ID as a fallback
        # check. This guarantees that no records are skipped or
        # duplicated.
        self.assertEqual(repr(self.a1.get_next_by_pub_date()),
                         '<Article: Article 2>')
        self.assertEqual(repr(self.a2.get_next_by_pub_date()),
                         '<Article: Article 3>')
        self.assertEqual(
            repr(self.a2.get_next_by_pub_date(headline__endswith='6')),
            '<Article: Article 6>')
        self.assertEqual(repr(self.a3.get_next_by_pub_date()),
                         '<Article: Article 7>')
        self.assertEqual(repr(self.a4.get_next_by_pub_date()),
                         '<Article: Article 6>')
        self.assertRaises(Article.DoesNotExist, self.a5.get_next_by_pub_date)
        self.assertEqual(repr(self.a6.get_next_by_pub_date()),
                         '<Article: Article 5>')
        self.assertEqual(repr(self.a7.get_next_by_pub_date()),
                         '<Article: Article 4>')

        self.assertEqual(repr(self.a7.get_previous_by_pub_date()),
                         '<Article: Article 3>')
        self.assertEqual(repr(self.a6.get_previous_by_pub_date()),
                         '<Article: Article 4>')
        self.assertEqual(repr(self.a5.get_previous_by_pub_date()),
                         '<Article: Article 6>')
        self.assertEqual(repr(self.a4.get_previous_by_pub_date()),
                         '<Article: Article 7>')
        self.assertEqual(repr(self.a3.get_previous_by_pub_date()),
                         '<Article: Article 2>')
        self.assertEqual(repr(self.a2.get_previous_by_pub_date()),
                         '<Article: Article 1>')

    def test_escaping(self):
        # Underscores, percent signs and backslashes have special
        # meaning in the underlying SQL code, but Django handles
        # the quoting of them automatically.
        a8 = Article(headline='Article_ with underscore',
                     pub_date=datetime(2005, 11, 20))
        a8.save()
        self.assertQuerysetEqual(
            Article.objects.filter(headline__startswith='Article'),
            [
                '<Article: Article_ with underscore>',
                '<Article: Article 5>',
                '<Article: Article 6>',
                '<Article: Article 4>',
                '<Article: Article 2>',
                '<Article: Article 3>',
                '<Article: Article 7>',
                '<Article: Article 1>',
            ])
        self.assertQuerysetEqual(
            Article.objects.filter(headline__startswith='Article_'),
            ['<Article: Article_ with underscore>'])
        a9 = Article(headline='Article% with percent sign',
                     pub_date=datetime(2005, 11, 21))
        a9.save()
        self.assertQuerysetEqual(
            Article.objects.filter(headline__startswith='Article'),
            [
                '<Article: Article% with percent sign>',
                '<Article: Article_ with underscore>',
                '<Article: Article 5>',
                '<Article: Article 6>',
                '<Article: Article 4>',
                '<Article: Article 2>',
                '<Article: Article 3>',
                '<Article: Article 7>',
                '<Article: Article 1>',
            ])
        self.assertQuerysetEqual(
            Article.objects.filter(headline__startswith='Article%'),
            ['<Article: Article% with percent sign>'])
        a10 = Article(headline='Article with \\ backslash',
                      pub_date=datetime(2005, 11, 22))
        a10.save()
        self.assertQuerysetEqual(
            Article.objects.filter(headline__contains='\\'),
            ['<Article: Article with \ backslash>'])

    def test_exclude(self):
        a8 = Article.objects.create(headline='Article_ with underscore',
                                    pub_date=datetime(2005, 11, 20))
        a9 = Article.objects.create(headline='Article% with percent sign',
                                    pub_date=datetime(2005, 11, 21))
        a10 = Article.objects.create(headline='Article with \\ backslash',
                                     pub_date=datetime(2005, 11, 22))

        # exclude() is the opposite of filter() when doing lookups:
        self.assertQuerysetEqual(
            Article.objects.filter(headline__contains='Article')
                .exclude(headline__contains='with'),
            [
                '<Article: Article 5>',
                '<Article: Article 6>',
                '<Article: Article 4>',
                '<Article: Article 2>',
                '<Article: Article 3>',
                '<Article: Article 7>',
                '<Article: Article 1>',
            ])
        self.assertQuerysetEqual(
            Article.objects.exclude(headline__startswith='Article_'),
            [
                '<Article: Article with \\ backslash>',
                '<Article: Article% with percent sign>',
                '<Article: Article 5>',
                '<Article: Article 6>',
                '<Article: Article 4>',
                '<Article: Article 2>',
                '<Article: Article 3>',
                '<Article: Article 7>',
                '<Article: Article 1>',
            ])
        self.assertQuerysetEqual(
            Article.objects.exclude(headline='Article 7'),
            [
                '<Article: Article with \\ backslash>',
                '<Article: Article% with percent sign>',
                '<Article: Article_ with underscore>',
                '<Article: Article 5>',
                '<Article: Article 6>',
                '<Article: Article 4>',
                '<Article: Article 2>',
                '<Article: Article 3>',
                '<Article: Article 1>',
            ])

    def test_none(self):
        # none() returns an EmptyQuerySet that behaves like any other
        # QuerySet object.
        self.assertQuerysetEqual(Article.objects.none(), [])
        self.assertQuerysetEqual(
            Article.objects.none().filter(headline__startswith='Article'), [])
        self.assertQuerysetEqual(
            Article.objects.filter(headline__startswith='Article').none(), [])
        self.assertEqual(Article.objects.none().count(), 0)
        self.assertEqual(
            Article.objects.none()
                .update(headline="This should not take effect"), 0)
        self.assertQuerysetEqual(
            [article for article in Article.objects.none().iterator()],
            [])

    def test_in(self):
        # using __in with an empty list should return an
        # empty query set.
        self.assertQuerysetEqual(Article.objects.filter(id__in=[]), [])
        self.assertQuerysetEqual(
            Article.objects.exclude(id__in=[]),
            [
                '<Article: Article 5>',
                '<Article: Article 6>',
                '<Article: Article 4>',
                '<Article: Article 2>',
                '<Article: Article 3>',
                '<Article: Article 7>',
                '<Article: Article 1>',
            ])

    def test_error_messages(self):
        # Programming errors are pointed out with nice error messages.
        try:
            Article.objects.filter(pub_date_year='2005').count()
            self.fail("FieldError not raised.")
        except FieldError, ex:
            self.assertEqual(
                str(ex),
                "Cannot resolve keyword 'pub_date_year' into field. "
                "Choices are: author, headline, id, pub_date, tag")
        try:
            Article.objects.filter(headline__starts='Article')
            self.fail("FieldError not raised.")
        except FieldError, ex:
            self.assertEqual(
                str(ex),
                "Join on field 'headline' not permitted. "
                "Did you misspell 'starts' for the lookup type?")

    def test_regex(self):
        # Create some articles with a bit more interesting headlines
        # for testing field lookups:
        for a in Article.objects.all():
            a.delete()
        now = datetime.now()
        a1 = Article(pub_date=now, headline='f')
        a1.save()
        a2 = Article(pub_date=now, headline='fo')
        a2.save()
        a3 = Article(pub_date=now, headline='foo')
        a3.save()
        a4 = Article(pub_date=now, headline='fooo')
        a4.save()
        a5 = Article(pub_date=now, headline='hey-Foo')
        a5.save()
        a6 = Article(pub_date=now, headline='bar')
        a6.save()
        a7 = Article(pub_date=now, headline='AbBa')
        a7.save()
        a8 = Article(pub_date=now, headline='baz')
        a8.save()
        a9 = Article(pub_date=now, headline='baxZ')
        a9.save()
        # Zero-or-more.
        self.assertQuerysetEqual(
            Article.objects.filter(headline__regex=r'fo*'),
            ['<Article: f>', '<Article: fo>', '<Article: foo>',
             '<Article: fooo>'])
        self.assertQuerysetEqual(
            Article.objects.filter(headline__iregex=r'fo*'),
            [
                '<Article: f>',
                '<Article: fo>',
                '<Article: foo>',
                '<Article: fooo>',
                '<Article: hey-Foo>',
            ])
        # One-or-more.
        self.assertQuerysetEqual(
            Article.objects.filter(headline__regex=r'fo+'),
            ['<Article: fo>', '<Article: foo>', '<Article: fooo>'])
        # Wildcard.
        self.assertQuerysetEqual(
            Article.objects.filter(headline__regex=r'fooo?'),
            ['<Article: foo>', '<Article: fooo>'])
        # Leading anchor.
        self.assertQuerysetEqual(
            Article.objects.filter(headline__regex=r'^b'),
            ['<Article: bar>', '<Article: baxZ>', '<Article: baz>'])
        self.assertQuerysetEqual(
            Article.objects.filter(headline__iregex=r'^a'),
            ['<Article: AbBa>'])
        # Trailing anchor.
        self.assertQuerysetEqual(
            Article.objects.filter(headline__regex=r'z$'),
            ['<Article: baz>'])
        self.assertQuerysetEqual(
            Article.objects.filter(headline__iregex=r'z$'),
            ['<Article: baxZ>', '<Article: baz>'])
        # Character sets.
        self.assertQuerysetEqual(
            Article.objects.filter(headline__regex=r'ba[rz]'),
            ['<Article: bar>', '<Article: baz>'])
        self.assertQuerysetEqual(
            Article.objects.filter(headline__regex=r'ba.[RxZ]'),
            ['<Article: baxZ>'])
        self.assertQuerysetEqual(
            Article.objects.filter(headline__iregex=r'ba[RxZ]'),
            ['<Article: bar>', '<Article: baxZ>', '<Article: baz>'])

        # And more articles:
        a10 = Article(pub_date=now, headline='foobar')
        a10.save()
        a11 = Article(pub_date=now, headline='foobaz')
        a11.save()
        a12 = Article(pub_date=now, headline='ooF')
        a12.save()
        a13 = Article(pub_date=now, headline='foobarbaz')
        a13.save()
        a14 = Article(pub_date=now, headline='zoocarfaz')
        a14.save()
        a15 = Article(pub_date=now, headline='barfoobaz')
        a15.save()
        a16 = Article(pub_date=now, headline='bazbaRFOO')
        a16.save()

        # alternation
        self.assertQuerysetEqual(
            Article.objects.filter(headline__regex=r'oo(f|b)'),
            [
                '<Article: barfoobaz>',
                '<Article: foobar>',
                '<Article: foobarbaz>',
                '<Article: foobaz>',
            ])
        self.assertQuerysetEqual(
            Article.objects.filter(headline__iregex=r'oo(f|b)'),
            [
                '<Article: barfoobaz>',
                '<Article: foobar>',
                '<Article: foobarbaz>',
                '<Article: foobaz>',
                '<Article: ooF>',
            ])
        self.assertQuerysetEqual(
            Article.objects.filter(headline__regex=r'^foo(f|b)'),
            ['<Article: foobar>', '<Article: foobarbaz>',
             '<Article: foobaz>'])

        # Greedy matching.
        self.assertQuerysetEqual(
            Article.objects.filter(headline__regex=r'b.*az'),
            [
                '<Article: barfoobaz>',
                '<Article: baz>',
                '<Article: bazbaRFOO>',
                '<Article: foobarbaz>',
                '<Article: foobaz>',
            ])
        self.assertQuerysetEqual(
            Article.objects.filter(headline__iregex=r'b.*ar'),
            [
                '<Article: bar>',
                '<Article: barfoobaz>',
                '<Article: bazbaRFOO>',
                '<Article: foobar>',
                '<Article: foobarbaz>',
            ])

    @skipUnlessDBFeature('supports_regex_backreferencing')
    def test_regex_backreferencing(self):
        # Grouping and backreferences.
        now = datetime.now()
        a10 = Article(pub_date=now, headline='foobar')
        a10.save()
        a11 = Article(pub_date=now, headline='foobaz')
        a11.save()
        a12 = Article(pub_date=now, headline='ooF')
        a12.save()
        a13 = Article(pub_date=now, headline='foobarbaz')
        a13.save()
        a14 = Article(pub_date=now, headline='zoocarfaz')
        a14.save()
        a15 = Article(pub_date=now, headline='barfoobaz')
        a15.save()
        a16 = Article(pub_date=now, headline='bazbaRFOO')
        a16.save()
        self.assertQuerysetEqual(
            Article.objects.filter(headline__regex=r'b(.).*b\1'),
            ['<Article: barfoobaz>', '<Article: bazbaRFOO>',
             '<Article: foobarbaz>'])

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
__FILENAME__ = models
from django.db import models

from djangotoolbox.fields import RawField, ListField, DictField, \
    EmbeddedModelField

from django_mongodb_engine.fields import GridFSField, GridFSString

# ensures class_prepared signal handler is installed
from django_mongodb_engine import models as mongo_models

from query.models import Post


class DescendingIndexModel(models.Model):
    desc = models.IntegerField()

    class MongoMeta:
        descending_indexes = ['desc']


class DateModel(models.Model):
    date = models.DateField()


class DateTimeModel(models.Model):
    datetime = models.DateTimeField()


class RawModel(models.Model):
    raw = RawField()


class IndexTestModel(models.Model):
    regular_index = models.IntegerField(db_index=True)
    custom_column = models.IntegerField(db_column='foo', db_index=True)
    descending_index = models.IntegerField(db_index=True)
    descending_index_custom_column = models.IntegerField(db_column='bar',
                                                         db_index=True)
    foreignkey_index = models.ForeignKey(RawModel, db_index=True, on_delete=models.DO_NOTHING)
    foreignkey_custom_column = models.ForeignKey('DateModel',
                                                 db_column='spam')
    sparse_index = models.IntegerField(db_index=True)
    sparse_index_unique = models.IntegerField(db_index=True, unique=True)
    sparse_index_cmp_1 = models.IntegerField(db_index=True)
    sparse_index_cmp_2 = models.IntegerField(db_index=True)

    class MongoMeta:
        sparse_indexes = ['sparse_index', 'sparse_index_unique',
                          ('sparse_index_cmp_1', 'sparse_index_cmp_2')]
        descending_indexes = ['descending_index',
                              'descending_index_custom_column']
        index_together = [
            {'fields': ['regular_index', 'custom_column']},
            {'fields': ('sparse_index_cmp_1', 'sparse_index_cmp_2')}]


class IndexTestModel2(models.Model):
    a = models.IntegerField(db_index=True)
    b = models.IntegerField(db_index=True)

    class MongoMeta:
        index_together = ['a', ('b', -1)]


class CustomColumnEmbeddedModel(models.Model):
    a = models.IntegerField(db_column='a2')


class NewStyleIndexesTestModel(models.Model):
    f1 = models.IntegerField()
    f2 = models.IntegerField()
    f3 = models.IntegerField()

    db_index = models.IntegerField(db_index=True)
    unique = models.IntegerField(unique=True)
    custom_column = models.IntegerField(db_column='custom')
    geo = models.IntegerField()
    geo_custom_column = models.IntegerField(db_column='geo')

    dict1 = DictField()
    dict_custom_column = DictField(db_column='dict_custom')
    embedded = EmbeddedModelField(CustomColumnEmbeddedModel)
    embedded_list = ListField(EmbeddedModelField(CustomColumnEmbeddedModel))

    class Meta:
        unique_together = [('f2', 'custom_column'), ('f2', 'f3')]

    class MongoMeta:
        indexes = [
            [('f1', -1)],
            {'fields': 'f2', 'sparse': True},
            {'fields': [('custom_column', -1), 'f3']},
            [('geo', '2d')],
            {'fields': [('geo_custom_column', '2d'), 'f2'],
             'min': 42, 'max': 21},
            {'fields': [('dict1.foo', 1)]},
            {'fields': [('dict_custom_column.foo', 1)]},
            {'fields': [('embedded.a', 1)]},
            {'fields': [('embedded_list.a', 1)]},
        ]


class GridFSFieldTestModel(models.Model):
    gridfile = GridFSField()
    gridfile_nodelete = GridFSField(delete=False)
    gridfile_versioned = GridFSField(versioning=True)
    gridfile_versioned_delete = GridFSField(versioning=True, delete=True)
    gridstring = GridFSString()


class Issue47Model(models.Model):
    foo = ListField(EmbeddedModelField(Post))


class CustomIDModel(models.Model):
    id = models.IntegerField()
    primary = models.IntegerField(primary_key=True)


class CustomIDModel2(models.Model):
    id = models.IntegerField(primary_key=True, db_column='blah')


class CappedCollection(models.Model):
    n = models.IntegerField(default=42)

    class MongoMeta:
        capped = True
        collection_size = 10


class CappedCollection2(models.Model):

    class MongoMeta:
        capped = True
        collection_size = 1000
        collection_max = 2


class CappedCollection3(models.Model):
    n = models.IntegerField(default=43)

    class MongoMeta:
        capped = True
        collection_size = 1000

########NEW FILE########
__FILENAME__ = tests
from __future__ import with_statement
from cStringIO import StringIO

from django.core.management import call_command
from django.contrib.sites.models import Site
from django.db import connection, connections
from django.db.utils import DatabaseError, IntegrityError
from django.db.models import Q

from gridfs import GridOut
from pymongo import ASCENDING, DESCENDING

from django_mongodb_engine.base import DatabaseWrapper

from models import *
from utils import *


class MongoDBEngineTests(TestCase):
    """Tests for mongodb-engine specific features."""

    def test_mongometa(self):
        self.assertEqual(DescendingIndexModel._meta.descending_indexes,
                        ['desc'])

    def test_A_query(self):
        from django_mongodb_engine.query import A
        obj1 = RawModel.objects.create(raw=[{'a': 1, 'b': 2}])
        obj2 = RawModel.objects.create(raw=[{'a': 1, 'b': 3}])
        self.assertEqualLists(RawModel.objects.filter(raw=A('a', 1)),
                              [obj1, obj2])
        self.assertEqual(RawModel.objects.get(raw=A('b', 2)), obj1)
        self.assertEqual(RawModel.objects.get(raw=A('b', 3)), obj2)

    def test_nice_monthday_query_exception(self):
        with self.assertRaisesRegexp(DatabaseError, "not support month/day"):
            DateModel.objects.get(date__month=1)
        with self.assertRaisesRegexp(DatabaseError, "not support month/day"):
            len(DateTimeModel.objects.filter(datetime__day=1))

    def test_nice_int_objectid_exception(self):
        msg = "AutoField \(default primary key\) values must be strings " \
              "representing an ObjectId on MongoDB \(got u?'%s' instead\)."
        self.assertRaisesRegexp(
                DatabaseError, msg % u'helloworld...',
                RawModel.objects.create, id='helloworldwhatsup')
        self.assertRaisesRegexp(
            DatabaseError, (msg % '5') +
                " Please make sure your SITE_ID contains a valid ObjectId string.",
            Site.objects.get, id='5')

    def test_generic_field(self):
        for obj in [['foo'], {'bar': 'buzz'}]:
            id = RawModel.objects.create(raw=obj).id
            self.assertEqual(RawModel.objects.get(id=id).raw, obj)

    def test_databasewrapper_api(self):
        from pymongo.mongo_client import MongoClient
        from pymongo.database import Database
        from pymongo.collection import Collection
        from random import shuffle

        if settings.DEBUG:
            from django_mongodb_engine.utils import \
                CollectionDebugWrapper as Collection

        for wrapper in [connection,
                        DatabaseWrapper(connection.settings_dict)]:
            calls = [
                lambda: self.assertIsInstance(wrapper.get_collection('foo'),
                                              Collection),
                lambda: self.assertIsInstance(wrapper.database, Database),
                lambda: self.assertIsInstance(wrapper.connection, MongoClient),
            ]
            shuffle(calls)
            for call in calls:
                call()

    def test_tellsiteid(self):
        from django.contrib.sites.models import Site
        site_id = Site.objects.create().id
        for kwargs in [{}, {'verbosity': 1}]:
            stdout = StringIO()
            call_command('tellsiteid', stdout=stdout, **kwargs)
            self.assertIn(site_id, stdout.getvalue())


class RegressionTests(TestCase):
    def test_djangononrel_issue_8(self):
        """
        ForeignKeys should be ObjectIds, not unicode.
        """
        from bson.objectid import ObjectId
        from query.models import Blog, Post

        post = Post.objects.create(blog=Blog.objects.create())
        collection = get_collection(Post)
        assert collection.count() == 1
        doc = collection.find_one()
        self.assertIsInstance(doc['blog_id'], ObjectId)

    def test_issue_47(self):
        """
        ForeignKeys in subobjects should be ObjectIds, not unicode.
        """
        # handle pymongo backward compatibility
        try:
            from bson.objectid import ObjectId
        except ImportError:
            from pymongo.objectid import ObjectId
        from query.models import Blog, Post
        post = Post.objects.create(blog=Blog.objects.create())
        Issue47Model.objects.create(foo=[post])
        collection = get_collection(Issue47Model)
        assert collection.count() == 1
        doc = collection.find_one()
        self.assertIsInstance(doc['foo'][0]['blog_id'], ObjectId)

    def test_djangotoolbox_issue_7(self):
        """Subobjects should not have an id field."""
        from query.models import Post
        Issue47Model.objects.create(foo=[Post(title='a')])
        collection = get_collection(Issue47Model)
        assert collection.count() == 1
        doc = collection.find_one()
        self.assertNotIn('id', doc['foo'][0])

    def test_custom_id_field(self):
        """Everything should work fine with custom primary keys."""
        CustomIDModel.objects.create(id=42, primary=666)
        self.assertDictContainsSubset(
            {'_id': 666, 'id': 42},
            get_collection(CustomIDModel).find_one())
        CustomIDModel2.objects.create(id=42)
        self.assertDictContainsSubset(
            {'_id': 42},
            get_collection(CustomIDModel2).find_one())
        obj = CustomIDModel2.objects.create(id=41)
        self.assertEqualLists(
            CustomIDModel2.objects.order_by('id').values('id'),
            [{'id': 41}, {'id': 42}])
        self.assertEqualLists(
            CustomIDModel2.objects.order_by('-id').values('id'),
            [{'id': 42}, {'id': 41}])
        self.assertEqual(obj, CustomIDModel2.objects.get(id=41))

    def test_multiple_exclude(self):
        objs = [RawModel.objects.create(raw=i) for i in xrange(1, 6)]
        self.assertEqual(
            objs[-1],
            RawModel.objects.exclude(raw=1).exclude(raw=2)
                            .exclude(raw=3).exclude(raw=4).get())
        list(RawModel.objects.filter(raw=1).filter(raw=2))
        list(RawModel.objects.filter(raw=1).filter(raw=2)
                             .exclude(raw=3))
        list(RawModel.objects.filter(raw=1).filter(raw=2)
                             .exclude(raw=3).exclude(raw=4))
        list(RawModel.objects.filter(raw=1).filter(raw=2)
                             .exclude(raw=3).exclude(raw=4).filter(raw=5))

    def test_multiple_exclude_random(self):
        from random import randint

        for i in xrange(20):
            RawModel.objects.create(raw=i)

        for i in xrange(10):
            q = RawModel.objects.all()
            for i in xrange(randint(0, 20)):
                q = getattr(q, 'filter' if randint(0, 1) else 'exclude')(raw=i)
            list(q)

    def test_issue_89(self):
        query = [Q(raw='a') | Q(raw='b'),
                 Q(raw='c') | Q(raw='d')]
        self.assertRaises(AssertionError, RawModel.objects.get, *query)


class DatabaseOptionTests(TestCase):
    """Tests for MongoDB-specific database options."""

    class custom_database_wrapper(object):

        def __init__(self, settings, **kwargs):
            self.new_wrapper = DatabaseWrapper(
                dict(connection.settings_dict, **settings),
                **kwargs)

        def __enter__(self):
            self._old_connection = getattr(connections._connections, 'default')
            connections._connections.default = self.new_wrapper
            self.new_wrapper._connect()
            return self.new_wrapper

        def __exit__(self, *exc_info):
            self.new_wrapper.connection.disconnect()
            connections._connections.default = self._old_connection

    def test_pymongo_connection_args(self):

        class foodict(dict):
            pass

        with self.custom_database_wrapper({
                'OPTIONS': {
                    'SLAVE_OKAY': True,
                    'TZ_AWARE': True,
                    'DOCUMENT_CLASS': foodict,
                }}) as connection:
            for name, value in connection.settings_dict[
                    'OPTIONS'].iteritems():
                name = '_Connection__%s' % name.lower()
                if name not in connection.connection.__dict__:
                    # slave_okay was moved into BaseObject in PyMongo 2.0.
                    name = name.replace('Connection', 'BaseObject')
                if name not in connection.connection.__dict__:
                    # document_class was moved into MongoClient in PyMongo 2.4.
                    name = name.replace('BaseObject', 'MongoClient')
                self.assertEqual(connection.connection.__dict__[name], value)

    def test_operation_flags(self):
        def test_setup(flags, **method_kwargs):
            cls_code = [
                'from pymongo.collection import Collection',
                'class Collection(Collection):',
                '    _method_kwargs = {}',
            ]
            for name in method_kwargs:
                for line in [
                    'def %s(self, *args, **kwargs):',
                    '    assert %r not in self._method_kwargs',
                    '    self._method_kwargs[%r] = kwargs',
                    '    return super(self.__class__, self).%s(*args, **kwargs)\n',
                ]:
                    cls_code.append('    ' + line % name)

            exec '\n'.join(cls_code) in locals()

            options = {'OPTIONS': {'OPERATIONS': flags}}
            with self.custom_database_wrapper(options,
                                              collection_class=Collection):
                RawModel.objects.create(raw='foo')
                update_count = RawModel.objects.update(raw='foo'), \
                               RawModel.objects.count()
                RawModel.objects.all().delete()

            for name in method_kwargs:
                self.assertEqual(method_kwargs[name],
                                 Collection._method_kwargs[name])

            if Collection._method_kwargs['update'].get('safe'):
                self.assertEqual(*update_count)

        test_setup({}, save={}, update={'multi': True}, remove={})
        test_setup({
            'safe': True},
            save={'safe': True},
            update={'safe': True, 'multi': True},
            remove={'safe': True})
        test_setup({
            'delete': {'safe': True}, 'update': {}},
            save={},
            update={'multi': True},
            remove={'safe': True})
        test_setup({
            'insert': {'fsync': True}, 'delete': {'fsync': True}},
            save={},
            update={'multi': True},
            remove={'fsync': True})

    def test_unique(self):
        with self.custom_database_wrapper({'OPTIONS': {}}):
            Post.objects.create(title='a', content='x')
            Post.objects.create(title='a', content='y')
            self.assertEqual(Post.objects.count(), 1)
            self.assertEqual(Post.objects.get().content, 'x')

    def test_unique_safe(self):
        Post.objects.create(title='a')
        self.assertRaises(IntegrityError, Post.objects.create, title='a')


class IndexTests(TestCase):

    def assertHaveIndex(self, field_name, direction=ASCENDING):
        info = get_collection(IndexTestModel).index_information()
        index_name = field_name + ['_1', '_-1'][direction == DESCENDING]
        self.assertIn(index_name, info)
        self.assertIn((field_name, direction), info[index_name]['key'])

    # Assumes fields as [(name, direction), (name, direction)].
    def assertCompoundIndex(self, fields, model=IndexTestModel):
        info = get_collection(model).index_information()
        index_names = [field[0] + ['_1', '_-1'][field[1] == DESCENDING]
                       for field in fields]
        index_name = '_'.join(index_names)
        self.assertIn(index_name, info)
        self.assertEqual(fields, info[index_name]['key'])

    def assertIndexProperty(self, field_name, name, direction=ASCENDING):
        info = get_collection(IndexTestModel).index_information()
        index_name = field_name + ['_1', '_-1'][direction == DESCENDING]
        self.assertTrue(info.get(index_name, {}).get(name, False))

    def test_regular_indexes(self):
        self.assertHaveIndex('regular_index')

    def test_custom_columns(self):
        self.assertHaveIndex('foo')
        self.assertHaveIndex('spam')

    def test_sparse_index(self):
        self.assertHaveIndex('sparse_index')
        self.assertIndexProperty('sparse_index', 'sparse')

        self.assertHaveIndex('sparse_index_unique')
        self.assertIndexProperty('sparse_index_unique', 'sparse')
        self.assertIndexProperty('sparse_index_unique', 'unique')

        self.assertCompoundIndex([('sparse_index_cmp_1', 1),
                                  ('sparse_index_cmp_2', 1)])
        self.assertCompoundIndex([('sparse_index_cmp_1', 1),
                                  ('sparse_index_cmp_2', 1)])

    def test_compound(self):
        self.assertCompoundIndex([('regular_index', 1), ('foo', 1)])
        self.assertCompoundIndex([('a', 1), ('b', -1)], IndexTestModel2)

    def test_foreignkey(self):
        self.assertHaveIndex('foreignkey_index_id')

    def test_descending(self):
        self.assertHaveIndex('descending_index', DESCENDING)
        self.assertHaveIndex('bar', DESCENDING)


class NewStyleIndexTests(TestCase):

    class order_doesnt_matter(list):

        def __eq__(self, other):
            return sorted(self) == sorted(other)

    def assertHaveIndex(self, key, **properties):
        info = get_collection(NewStyleIndexesTestModel).index_information()
        index_name = '_'.join('%s_%s' % pair for pair in key)
        default_properties = {'key': self.order_doesnt_matter(key), 'v': 1}
        self.assertIn(index_name, info)
        self.assertEqual(info[index_name],
                         dict(default_properties, **properties))

    def test_indexes(self):
        self.assertHaveIndex([('db_index', 1)])
        self.assertHaveIndex([('unique', 1)], unique=True)
        self.assertHaveIndex([('f2', 1), ('custom', 1)], unique=True)
        self.assertHaveIndex([('f2', 1), ('f3', 1)], unique=True)
        self.assertHaveIndex([('f1', -1)])
        self.assertHaveIndex([('f2', 1)], sparse=True)
        self.assertHaveIndex([('custom', -1), ('f3', 1)])
        self.assertHaveIndex([('geo', '2d')])
        self.assertHaveIndex([('geo', '2d'), ('f2', 1)], min=42, max=21)
        self.assertHaveIndex([('dict1.foo', 1)])
        self.assertHaveIndex([('dict_custom.foo', 1)])
        self.assertHaveIndex([('embedded.a2', 1)])
        self.assertHaveIndex([('embedded_list.a2', 1)])


class GridFSFieldTests(TestCase):

    def tearDown(self):
        get_collection(GridFSFieldTestModel).files.remove()

    def test_empty(self):
        obj = GridFSFieldTestModel.objects.create()
        self.assertEqual(obj.gridfile, None)
        self.assertEqual(obj.gridstring, '')

    def test_gridfile(self):
        fh = open(__file__)
        fh.seek(42)
        obj = GridFSFieldTestModel(gridfile=fh)
        self.assert_(obj.gridfile is fh)
        obj.save()
        self.assert_(obj.gridfile is fh)
        obj = GridFSFieldTestModel.objects.get()
        self.assertIsInstance(obj.gridfile, GridOut)
        fh.seek(42)
        self.assertEqual(obj.gridfile.read(), fh.read())

    def test_gridstring(self):
        data = open(__file__).read()
        obj = GridFSFieldTestModel(gridstring=data)
        self.assert_(obj.gridstring is data)
        obj.save()
        self.assert_(obj.gridstring is data)
        obj = GridFSFieldTestModel.objects.get()
        self.assertEqual(obj.gridstring, data)

    def test_caching(self):
        """Make sure GridFS files are read only once."""
        GridFSFieldTestModel.objects.create(gridfile=open(__file__))
        obj = GridFSFieldTestModel.objects.get()
        meta = GridFSFieldTestModel._meta.fields[1]._get_meta(obj)
        self.assertEqual(meta.filelike, None)
        obj.gridfile # Fetches the file from GridFS.
        self.assertNotEqual(meta.filelike, None)
        # From now on, the file should be looked up in the cache.
        # To verify this, we compromise the cache with a sentinel object:
        sentinel = object()
        meta.filelike = sentinel
        self.assertEqual(obj.gridfile, sentinel)

    def _test_versioning_delete(self, field, versioning, delete):
        col = get_collection(GridFSFieldTestModel).files
        get_meta = GridFSFieldTestModel._meta.get_field(field)._get_meta

        obj = GridFSFieldTestModel.objects.create()
        self.assertEqual(col.count(), 0)
        obj.delete()

        obj = GridFSFieldTestModel.objects.create(**{field: 'a'})
        self.assertEqual(col.count(), 1)

        old_oid = get_meta(obj).oid
        self.assertNotEqual(old_oid, None)
        setattr(obj, field, 'a')
        obj.save()
        self.assertEqual(get_meta(obj).oid, old_oid)
        self.assertEqual(col.count(), 1)

        obj = GridFSFieldTestModel.objects.get()
        self.assertEqual(getattr(obj, field).read(), 'a')
        setattr(obj, field, 'b')
        obj.save()
        self.assertEqual(col.count(), 2 if versioning else 1)

        old_oid = get_meta(obj).oid
        setattr(obj, field, 'b')
        obj.save()
        self.assertEqual(get_meta(obj).oid, old_oid)
        self.assertEqual(col.count(), 2 if versioning else 1)

        setattr(obj, field, 'c')
        obj.save()
        self.assertEqual(col.count(), 3 if versioning else 1)

        setattr(obj, field, 'd')
        obj.save()
        self.assertEqual(col.count(), 4 if versioning else 1)

        obj = GridFSFieldTestModel.objects.get()
        self.assertEqual(getattr(obj, field).read(), 'd')

        setattr(obj, field, 'e')
        obj.save()
        self.assertEqual(col.count(), 5 if versioning else 1)

        setattr(obj, field, 'f')
        obj.save()
        self.assertEqual(col.count(), 6 if versioning else 1)

        obj.delete()
        self.assertEqual(col.count(),
                         0 if delete else (6 if versioning else 1))

    def test_delete(self):
        self._test_versioning_delete('gridfile', versioning=False,
                                     delete=True)

    def test_nodelete(self):
        self._test_versioning_delete('gridfile_nodelete', versioning=False,
                                     delete=False)

    def test_versioning(self):
        self._test_versioning_delete('gridfile_versioned', versioning=True,
                                     delete=False)

    def test_versioning_delete(self):
        self._test_versioning_delete('gridfile_versioned_delete',
                                     versioning=True, delete=True)

    def test_multiple_save_regression(self):
        col = get_collection(GridFSFieldTestModel).files
        o = GridFSFieldTestModel.objects.create(gridfile='asd')
        self.assertEqual(col.count(), 1)
        o.save()
        self.assertEqual(col.count(), 1)
        o = GridFSFieldTestModel.objects.get()
        o.save()
        self.assertEqual(col.count(), 1)

    def test_update(self):
        self.assertRaisesRegexp(
            DatabaseError, "Updates on GridFSFields are not allowed.",
            GridFSFieldTestModel.objects.update, gridfile='x')


class CappedCollectionTests(TestCase):

    def test_collection_size(self):
        for _ in range(100):
            CappedCollection.objects.create()
        self.assertLess(CappedCollection.objects.count(), 100)

    def test_collection_max(self):
        for _ in range(100):
            CappedCollection2.objects.create()
        self.assertEqual(CappedCollection2.objects.count(), 2)

    def test_reverse_natural(self):
        for n in [1, 2, 3]:
            CappedCollection3.objects.create(n=n)

        self.assertEqualLists(
            CappedCollection3.objects.values_list('n', flat=True),
            [1, 2, 3])

        self.assertEqualLists(
            CappedCollection3.objects.reverse().values_list('n', flat=True),
            [3, 2, 1])

########NEW FILE########
__FILENAME__ = utils
../utils.py
########NEW FILE########
__FILENAME__ = models
from django.conf import settings
from django.contrib.auth.models import User
from django.db import models

class Review(models.Model):
    source = models.CharField(max_length=100)
    object_id = models.PositiveIntegerField()

    def __unicode__(self):
        return self.source

    class Meta:
        ordering = ('source',)

class PersonManager(models.Manager):
    def get_by_natural_key(self, name):
        return self.get(name=name)

class Person(models.Model):
    objects = PersonManager()
    name = models.CharField(max_length=100)

    def __unicode__(self):
        return self.name

    class Meta:
        ordering = ('name',)

# This book manager doesn't do anything interesting; it just
# exists to strip out the 'extra_arg' argument to certain
# calls. This argument is used to establish that the BookManager
# is actually getting used when it should be.
class BookManager(models.Manager):
    def create(self, *args, **kwargs):
        kwargs.pop('extra_arg', None)
        return super(BookManager, self).create(*args, **kwargs)

    def get_or_create(self, *args, **kwargs):
        kwargs.pop('extra_arg', None)
        return super(BookManager, self).get_or_create(*args, **kwargs)

class Book(models.Model):
    objects = BookManager()
    title = models.CharField(max_length=100)
    published = models.DateField()
    editor = models.ForeignKey(Person, null=True, related_name='edited')
    pages = models.IntegerField(default=100)

    def __unicode__(self):
        return self.title

    class Meta:
        ordering = ('title',)

class Pet(models.Model):
    name = models.CharField(max_length=100)
    owner = models.ForeignKey(Person)

    def __unicode__(self):
        return self.name

    class Meta:
        ordering = ('name',)

class UserProfile(models.Model):
    user = models.OneToOneField(User, null=True)
    flavor = models.CharField(max_length=100)

    class Meta:
        ordering = ('flavor',)

########NEW FILE########
__FILENAME__ = tests
import datetime
import pickle
import sys
from StringIO import StringIO

from django.conf import settings
from django.contrib.auth.models import User
from django.core import management
from django.db import connections, router, DEFAULT_DB_ALIAS
from django.db.models import signals
from django.db.utils import ConnectionRouter, DatabaseError

from models import Book, Person, Pet, Review, UserProfile

try:
    # we only have these models if the user is using multi-db, it's safe the
    # run the tests without them though.
    from models import Article, article_using
except ImportError:
    pass

from .utils import TestCase

class QueryTestCase(TestCase):
    multi_db = True

    def test_db_selection(self):
        "Check that querysets will use the default database by default"
        self.assertEqual(Book.objects.db, DEFAULT_DB_ALIAS)
        self.assertEqual(Book.objects.all().db, DEFAULT_DB_ALIAS)

        self.assertEqual(Book.objects.using('other').db, 'other')

        self.assertEqual(Book.objects.db_manager('other').db, 'other')
        self.assertEqual(Book.objects.db_manager('other').all().db, 'other')

    def test_default_creation(self):
        "Objects created on the default database don't leak onto other databases"
        # Create a book on the default database using create()
        Book.objects.create(title="Pro Django",
                            published=datetime.date(2008, 12, 16))

        # Create a book on the default database using a save
        dive = Book()
        dive.title="Dive into Python"
        dive.published = datetime.date(2009, 5, 4)
        dive.save()

        # Check that book exists on the default database, but not on other database
        try:
            Book.objects.get(title="Pro Django")
            Book.objects.using('default').get(title="Pro Django")
        except Book.DoesNotExist:
            self.fail('"Dive Into Python" should exist on default database')

        self.assertRaises(Book.DoesNotExist,
            Book.objects.using('other').get,
            title="Pro Django"
        )

        try:
            Book.objects.get(title="Dive into Python")
            Book.objects.using('default').get(title="Dive into Python")
        except Book.DoesNotExist:
            self.fail('"Dive into Python" should exist on default database')

        self.assertRaises(Book.DoesNotExist,
            Book.objects.using('other').get,
            title="Dive into Python"
        )


    def test_other_creation(self):
        "Objects created on another database don't leak onto the default database"
        # Create a book on the second database
        Book.objects.using('other').create(title="Pro Django",
                                           published=datetime.date(2008, 12, 16))

        # Create a book on the default database using a save
        dive = Book()
        dive.title="Dive into Python"
        dive.published = datetime.date(2009, 5, 4)
        dive.save(using='other')

        # Check that book exists on the default database, but not on other database
        try:
            Book.objects.using('other').get(title="Pro Django")
        except Book.DoesNotExist:
            self.fail('"Dive Into Python" should exist on other database')

        self.assertRaises(Book.DoesNotExist,
            Book.objects.get,
            title="Pro Django"
        )
        self.assertRaises(Book.DoesNotExist,
            Book.objects.using('default').get,
            title="Pro Django"
        )

        try:
            Book.objects.using('other').get(title="Dive into Python")
        except Book.DoesNotExist:
            self.fail('"Dive into Python" should exist on other database')

        self.assertRaises(Book.DoesNotExist,
            Book.objects.get,
            title="Dive into Python"
        )
        self.assertRaises(Book.DoesNotExist,
            Book.objects.using('default').get,
            title="Dive into Python"
        )

    def test_basic_queries(self):
        "Queries are constrained to a single database"
        dive = Book.objects.using('other').create(title="Dive into Python",
                                                  published=datetime.date(2009, 5, 4))

        dive =  Book.objects.using('other').get(published=datetime.date(2009, 5, 4))
        self.assertEqual(dive.title, "Dive into Python")
        self.assertRaises(Book.DoesNotExist, Book.objects.using('default').get, published=datetime.date(2009, 5, 4))

        dive = Book.objects.using('other').get(title__icontains="dive")
        self.assertEqual(dive.title, "Dive into Python")
        self.assertRaises(Book.DoesNotExist, Book.objects.using('default').get, title__icontains="dive")

        dive = Book.objects.using('other').get(title__iexact="dive INTO python")
        self.assertEqual(dive.title, "Dive into Python")
        self.assertRaises(Book.DoesNotExist, Book.objects.using('default').get, title__iexact="dive INTO python")

    def test_foreign_key_separation(self):
        "FK fields are constrained to a single database"
        # Create a book and author on the default database
        pro = Book.objects.create(title="Pro Django",
                                  published=datetime.date(2008, 12, 16))

        marty = Person.objects.create(name="Marty Alchin")
        george = Person.objects.create(name="George Vilches")

        # Create a book and author on the other database
        dive = Book.objects.using('other').create(title="Dive into Python",
                                                  published=datetime.date(2009, 5, 4))

        mark = Person.objects.using('other').create(name="Mark Pilgrim")
        chris = Person.objects.using('other').create(name="Chris Mills")

        # Save the author's favourite books
        pro.editor = george
        pro.save()

        dive.editor = chris
        dive.save()

        pro = Book.objects.using('default').get(title="Pro Django")
        self.assertEqual(pro.editor.name, "George Vilches")

        dive = Book.objects.using('other').get(title="Dive into Python")
        self.assertEqual(dive.editor.name, "Chris Mills")

        # Reget the objects to clear caches
        chris = Person.objects.using('other').get(name="Chris Mills")
        dive = Book.objects.using('other').get(title="Dive into Python")

        # Retrieve related object by descriptor. Related objects should be database-bound
        self.assertEqual(list(chris.edited.values_list('title', flat=True)),
                          [u'Dive into Python'])

    def test_foreign_key_cross_database_protection(self):
        "Operations that involve sharing FK objects across databases raise an error"
        # Create a book and author on the default database
        pro = Book.objects.create(title="Pro Django",
                                  published=datetime.date(2008, 12, 16))

        marty = Person.objects.create(name="Marty Alchin")

        # Create a book and author on the other database
        dive = Book.objects.using('other').create(title="Dive into Python",
                                                  published=datetime.date(2009, 5, 4))

        mark = Person.objects.using('other').create(name="Mark Pilgrim")

        # Set a foreign key with an object from a different database
        try:
            dive.editor = marty
            self.fail("Shouldn't be able to assign across databases")
        except ValueError:
            pass

        # Set a foreign key set with an object from a different database
        try:
            marty.edited = [pro, dive]
            self.fail("Shouldn't be able to assign across databases")
        except ValueError:
            pass

        # Add to a foreign key set with an object from a different database
        try:
            marty.edited.add(dive)
            self.fail("Shouldn't be able to assign across databases")
        except ValueError:
            pass

        # BUT! if you assign a FK object when the base object hasn't
        # been saved yet, you implicitly assign the database for the
        # base object.
        chris = Person(name="Chris Mills")
        html5 = Book(title="Dive into HTML5", published=datetime.date(2010, 3, 15))
        # initially, no db assigned
        self.assertEqual(chris._state.db, None)
        self.assertEqual(html5._state.db, None)

        # old object comes from 'other', so the new object is set to use 'other'...
        dive.editor = chris
        html5.editor = mark
        self.assertEqual(chris._state.db, 'other')
        self.assertEqual(html5._state.db, 'other')
        # ... but it isn't saved yet
        self.assertEqual(list(Person.objects.using('other').values_list('name',flat=True)),
                          [u'Mark Pilgrim'])
        self.assertEqual(list(Book.objects.using('other').values_list('title',flat=True)),
                           [u'Dive into Python'])

        # When saved (no using required), new objects goes to 'other'
        chris.save()
        html5.save()
        self.assertEqual(list(Person.objects.using('default').values_list('name',flat=True)),
                          [u'Marty Alchin'])
        self.assertEqual(list(Person.objects.using('other').values_list('name',flat=True)),
                          [u'Chris Mills', u'Mark Pilgrim'])
        self.assertEqual(list(Book.objects.using('default').values_list('title',flat=True)),
                          [u'Pro Django'])
        self.assertEqual(list(Book.objects.using('other').values_list('title',flat=True)),
                          [u'Dive into HTML5', u'Dive into Python'])

        # This also works if you assign the FK in the constructor
        water = Book(title="Dive into Water", published=datetime.date(2001, 1, 1), editor=mark)
        self.assertEqual(water._state.db, 'other')
        # ... but it isn't saved yet
        self.assertEqual(list(Book.objects.using('default').values_list('title',flat=True)),
                          [u'Pro Django'])
        self.assertEqual(list(Book.objects.using('other').values_list('title',flat=True)),
                          [u'Dive into HTML5', u'Dive into Python'])

        # When saved, the new book goes to 'other'
        water.save()
        self.assertEqual(list(Book.objects.using('default').values_list('title',flat=True)),
                          [u'Pro Django'])
        self.assertEqual(list(Book.objects.using('other').values_list('title',flat=True)),
                          [u'Dive into HTML5', u'Dive into Python', u'Dive into Water'])

    def test_foreign_key_validation(self):
        "ForeignKey.validate() uses the correct database"
        mickey = Person.objects.using('other').create(name="Mickey")
        pluto = Pet.objects.using('other').create(name="Pluto", owner=mickey)
        self.assertEqual(None, pluto.full_clean())

    def test_o2o_separation(self):
        "OneToOne fields are constrained to a single database"
        # Create a user and profile on the default database
        alice = User.objects.db_manager('default').create_user('alice', 'alice@example.com')
        alice_profile = UserProfile.objects.using('default').create(user=alice, flavor='chocolate')

        # Create a user and profile on the other database
        bob = User.objects.db_manager('other').create_user('bob', 'bob@example.com')
        bob_profile = UserProfile.objects.using('other').create(user=bob, flavor='crunchy frog')

        # Retrieve related objects; queries should be database constrained
        alice = User.objects.using('default').get(username="alice")
        self.assertEqual(alice.userprofile.flavor, "chocolate")

        bob = User.objects.using('other').get(username="bob")
        self.assertEqual(bob.userprofile.flavor, "crunchy frog")

        # Reget the objects to clear caches
        alice_profile = UserProfile.objects.using('default').get(flavor='chocolate')
        bob_profile = UserProfile.objects.using('other').get(flavor='crunchy frog')

        # Retrive related object by descriptor. Related objects should be database-baound
        self.assertEqual(alice_profile.user.username, 'alice')
        self.assertEqual(bob_profile.user.username, 'bob')

    def test_o2o_cross_database_protection(self):
        "Operations that involve sharing FK objects across databases raise an error"
        # Create a user and profile on the default database
        alice = User.objects.db_manager('default').create_user('alice', 'alice@example.com')

        # Create a user and profile on the other database
        bob = User.objects.db_manager('other').create_user('bob', 'bob@example.com')

        # Set a one-to-one relation with an object from a different database
        alice_profile = UserProfile.objects.using('default').create(user=alice, flavor='chocolate')
        try:
            bob.userprofile = alice_profile
            self.fail("Shouldn't be able to assign across databases")
        except ValueError:
            pass

        # BUT! if you assign a FK object when the base object hasn't
        # been saved yet, you implicitly assign the database for the
        # base object.
        bob_profile = UserProfile.objects.using('other').create(user=bob, flavor='crunchy frog')

        new_bob_profile = UserProfile(flavor="spring surprise")
        new_bob_profile.save(using='other')

        charlie = User(username='charlie',email='charlie@example.com')
        charlie.set_unusable_password()
        charlie.save(using='other')

        # old object comes from 'other', so the new object is set to use 'other'...
        new_bob_profile.user = bob
        charlie.userprofile = bob_profile
        self.assertEqual(new_bob_profile._state.db, 'other')
        self.assertEqual(charlie._state.db, 'other')

        # When saved (no using required), new objects goes to 'other'
        bob_profile.save()
        self.assertEqual(list(User.objects.using('default').values_list('username',flat=True)),
                          [u'alice'])
        self.assertEqual(list(User.objects.using('other').values_list('username',flat=True)),
                          [u'bob', u'charlie'])
        self.assertEqual(list(UserProfile.objects.using('default').values_list('flavor',flat=True)),
                           [u'chocolate'])
        self.assertEqual(list(UserProfile.objects.using('other').values_list('flavor',flat=True)),
                           [u'crunchy frog', u'spring surprise'])

        # This also works if you assign the O2O relation in the constructor
        denise = User.objects.db_manager('other').create_user('denise','denise@example.com')
        denise_profile = UserProfile(flavor="tofu", user=denise)

        self.assertEqual(denise_profile._state.db, 'other')
        # ... but it isn't saved yet
        self.assertEqual(list(UserProfile.objects.using('default').values_list('flavor',flat=True)),
                           [u'chocolate'])
        self.assertEqual(list(UserProfile.objects.using('other').values_list('flavor',flat=True)),
                           [u'crunchy frog', u'spring surprise'])

        # When saved, the new profile goes to 'other'
        denise_profile.save()
        self.assertEqual(list(UserProfile.objects.using('default').values_list('flavor',flat=True)),
                           [u'chocolate'])
        self.assertEqual(list(UserProfile.objects.using('other').values_list('flavor',flat=True)),
                           [u'crunchy frog', u'spring surprise', u'tofu'])

    def test_ordering(self):
        "get_next_by_XXX commands stick to a single database"
        pro = Book.objects.create(title="Pro Django",
                                  published=datetime.date(2008, 12, 16))

        dive = Book.objects.using('other').create(title="Dive into Python",
                                                  published=datetime.date(2009, 5, 4))

        learn = Book.objects.using('other').create(title="Learning Python",
                                                   published=datetime.date(2008, 7, 16))

        self.assertEqual(learn.get_next_by_published().title, "Dive into Python")
        self.assertEqual(dive.get_previous_by_published().title, "Learning Python")

    def test_subquery(self):
        """Make sure as_sql works with subqueries and master/slave."""
        sub = Person.objects.using('other').filter(name='fff')
        qs = Book.objects.filter(editor__in=sub)

        # When you call __str__ on the query object, it doesn't know about using
        # so it falls back to the default. If the subquery explicitly uses a
        # different database, an error should be raised.
        self.assertRaises(ValueError, str, qs.query)

        # Evaluating the query shouldn't work, either
        try:
            for obj in qs:
                pass
            self.fail('Iterating over query should raise DatabaseError')
        except DatabaseError:
            pass

    def test_related_manager(self):
        "Related managers return managers, not querysets"
        mark = Person.objects.using('other').create(name="Mark Pilgrim")

        # extra_arg is removed by the BookManager's implementation of
        # create(); but the BookManager's implementation won't get called
        # unless edited returns a Manager, not a queryset
        mark.edited.create(title="Dive into Water",
                           published=datetime.date(2009, 5, 4),
                           extra_arg=True)

        mark.edited.get_or_create(title="Dive into Water",
                                  published=datetime.date(2009, 5, 4),
                                  extra_arg=True)

class TestRouter(object):
    # A test router. The behaviour is vaguely master/slave, but the
    # databases aren't assumed to propagate changes.
    def db_for_read(self, model, instance=None, **hints):
        if instance:
            return instance._state.db or 'other'
        return 'other'

    def db_for_write(self, model, **hints):
        return DEFAULT_DB_ALIAS

    def allow_relation(self, obj1, obj2, **hints):
        return obj1._state.db in ('default', 'other') and obj2._state.db in ('default', 'other')

    def allow_syncdb(self, db, model):
        return True

class AuthRouter(object):
    """A router to control all database operations on models in
    the contrib.auth application"""

    def db_for_read(self, model, **hints):
        "Point all read operations on auth models to 'default'"
        if model._meta.app_label == 'auth':
            # We use default here to ensure we can tell the difference
            # between a read request and a write request for Auth objects
            return 'default'
        return None

    def db_for_write(self, model, **hints):
        "Point all operations on auth models to 'other'"
        if model._meta.app_label == 'auth':
            return 'other'
        return None

    def allow_relation(self, obj1, obj2, **hints):
        "Allow any relation if a model in Auth is involved"
        if obj1._meta.app_label == 'auth' or obj2._meta.app_label == 'auth':
            return True
        return None

    def allow_syncdb(self, db, model):
        "Make sure the auth app only appears on the 'other' db"
        if db == 'other':
            return model._meta.app_label == 'auth'
        elif model._meta.app_label == 'auth':
            return False
        return None

class WriteRouter(object):
    # A router that only expresses an opinion on writes
    def db_for_write(self, model, **hints):
        return 'writer'

class RouterTestCase(TestCase):
    multi_db = True

    def setUp(self):
        # Make the 'other' database appear to be a slave of the 'default'
        self.old_routers = router.routers
        router.routers = [TestRouter()]

    def tearDown(self):
        # Restore the 'other' database as an independent database
        router.routers = self.old_routers

    def test_db_selection(self):
        "Check that querysets obey the router for db suggestions"
        self.assertEqual(Book.objects.db, 'other')
        self.assertEqual(Book.objects.all().db, 'other')

        self.assertEqual(Book.objects.using('default').db, 'default')

        self.assertEqual(Book.objects.db_manager('default').db, 'default')
        self.assertEqual(Book.objects.db_manager('default').all().db, 'default')

    def test_syncdb_selection(self):
        "Synchronization behaviour is predicatable"

        self.assertTrue(router.allow_syncdb('default', User))
        self.assertTrue(router.allow_syncdb('default', Book))

        self.assertTrue(router.allow_syncdb('other', User))
        self.assertTrue(router.allow_syncdb('other', Book))

        # Add the auth router to the chain.
        # TestRouter is a universal synchronizer, so it should have no effect.
        router.routers = [TestRouter(), AuthRouter()]

        self.assertTrue(router.allow_syncdb('default', User))
        self.assertTrue(router.allow_syncdb('default', Book))

        self.assertTrue(router.allow_syncdb('other', User))
        self.assertTrue(router.allow_syncdb('other', Book))

        # Now check what happens if the router order is the other way around
        router.routers = [AuthRouter(), TestRouter()]

        self.assertFalse(router.allow_syncdb('default', User))
        self.assertTrue(router.allow_syncdb('default', Book))

        self.assertTrue(router.allow_syncdb('other', User))
        self.assertFalse(router.allow_syncdb('other', Book))

    def test_partial_router(self):
        "A router can choose to implement a subset of methods"
        dive = Book.objects.using('other').create(title="Dive into Python",
                                                  published=datetime.date(2009, 5, 4))

        # First check the baseline behaviour

        self.assertEqual(router.db_for_read(User), 'other')
        self.assertEqual(router.db_for_read(Book), 'other')

        self.assertEqual(router.db_for_write(User), 'default')
        self.assertEqual(router.db_for_write(Book), 'default')

        self.assertTrue(router.allow_relation(dive, dive))

        self.assertTrue(router.allow_syncdb('default', User))
        self.assertTrue(router.allow_syncdb('default', Book))

        router.routers = [WriteRouter(), AuthRouter(), TestRouter()]

        self.assertEqual(router.db_for_read(User), 'default')
        self.assertEqual(router.db_for_read(Book), 'other')

        self.assertEqual(router.db_for_write(User), 'writer')
        self.assertEqual(router.db_for_write(Book), 'writer')

        self.assertTrue(router.allow_relation(dive, dive))

        self.assertFalse(router.allow_syncdb('default', User))
        self.assertTrue(router.allow_syncdb('default', Book))


    def test_database_routing(self):
        marty = Person.objects.using('default').create(name="Marty Alchin")
        pro = Book.objects.using('default').create(title="Pro Django",
                                                   published=datetime.date(2008, 12, 16),
                                                   editor=marty)
        pro.authors = [marty]

        # Create a book and author on the other database
        dive = Book.objects.using('other').create(title="Dive into Python",
                                                  published=datetime.date(2009, 5, 4))

        # An update query will be routed to the default database
        Book.objects.filter(title='Pro Django').update(pages=200)

        try:
            # By default, the get query will be directed to 'other'
            Book.objects.get(title='Pro Django')
            self.fail("Shouldn't be able to find the book")
        except Book.DoesNotExist:
            pass

        # But the same query issued explicitly at a database will work.
        pro = Book.objects.using('default').get(title='Pro Django')

        # Check that the update worked.
        self.assertEqual(pro.pages, 200)

        # An update query with an explicit using clause will be routed
        # to the requested database.
        Book.objects.using('other').filter(title='Dive into Python').update(pages=300)
        self.assertEqual(Book.objects.get(title='Dive into Python').pages, 300)

        # Related object queries stick to the same database
        # as the original object, regardless of the router
        self.assertEqual(pro.editor.name, u'Marty Alchin')

        # get_or_create is a special case. The get needs to be targetted at
        # the write database in order to avoid potential transaction
        # consistency problems
        book, created = Book.objects.get_or_create(title="Pro Django")
        self.assertFalse(created)

        book, created = Book.objects.get_or_create(title="Dive Into Python",
                                                   defaults={'published':datetime.date(2009, 5, 4)})
        self.assertTrue(created)

        # Check the head count of objects
        self.assertEqual(Book.objects.using('default').count(), 2)
        self.assertEqual(Book.objects.using('other').count(), 1)
        # If a database isn't specified, the read database is used
        self.assertEqual(Book.objects.count(), 1)

        # A delete query will also be routed to the default database
        Book.objects.filter(pages__gt=150).delete()

        # The default database has lost the book.
        self.assertEqual(Book.objects.using('default').count(), 1)
        self.assertEqual(Book.objects.using('other').count(), 1)

    def test_foreign_key_cross_database_protection(self):
        "Foreign keys can cross databases if they two databases have a common source"
        # Create a book and author on the default database
        pro = Book.objects.using('default').create(title="Pro Django",
                                                   published=datetime.date(2008, 12, 16))

        marty = Person.objects.using('default').create(name="Marty Alchin")

        # Create a book and author on the other database
        dive = Book.objects.using('other').create(title="Dive into Python",
                                                  published=datetime.date(2009, 5, 4))

        mark = Person.objects.using('other').create(name="Mark Pilgrim")

        # Set a foreign key with an object from a different database
        try:
            dive.editor = marty
        except ValueError:
            self.fail("Assignment across master/slave databases with a common source should be ok")

        # Database assignments of original objects haven't changed...
        self.assertEqual(marty._state.db, 'default')
        self.assertEqual(pro._state.db, 'default')
        self.assertEqual(dive._state.db, 'other')
        self.assertEqual(mark._state.db, 'other')

        # ... but they will when the affected object is saved.
        dive.save()
        self.assertEqual(dive._state.db, 'default')

        # ...and the source database now has a copy of any object saved
        try:
            Book.objects.using('default').get(title='Dive into Python').delete()
        except Book.DoesNotExist:
            self.fail('Source database should have a copy of saved object')

        # This isn't a real master-slave database, so restore the original from other
        dive = Book.objects.using('other').get(title='Dive into Python')
        self.assertEqual(dive._state.db, 'other')

        # Set a foreign key set with an object from a different database
        try:
            marty.edited = [pro, dive]
        except ValueError:
            self.fail("Assignment across master/slave databases with a common source should be ok")

        # Assignment implies a save, so database assignments of original objects have changed...
        self.assertEqual(marty._state.db, 'default')
        self.assertEqual(pro._state.db, 'default')
        self.assertEqual(dive._state.db, 'default')
        self.assertEqual(mark._state.db, 'other')

        # ...and the source database now has a copy of any object saved
        try:
            Book.objects.using('default').get(title='Dive into Python').delete()
        except Book.DoesNotExist:
            self.fail('Source database should have a copy of saved object')

        # This isn't a real master-slave database, so restore the original from other
        dive = Book.objects.using('other').get(title='Dive into Python')
        self.assertEqual(dive._state.db, 'other')

        # Add to a foreign key set with an object from a different database
        try:
            marty.edited.add(dive)
        except ValueError:
            self.fail("Assignment across master/slave databases with a common source should be ok")

        # Add implies a save, so database assignments of original objects have changed...
        self.assertEqual(marty._state.db, 'default')
        self.assertEqual(pro._state.db, 'default')
        self.assertEqual(dive._state.db, 'default')
        self.assertEqual(mark._state.db, 'other')

        # ...and the source database now has a copy of any object saved
        try:
            Book.objects.using('default').get(title='Dive into Python').delete()
        except Book.DoesNotExist:
            self.fail('Source database should have a copy of saved object')

        # This isn't a real master-slave database, so restore the original from other
        dive = Book.objects.using('other').get(title='Dive into Python')

        # If you assign a FK object when the base object hasn't
        # been saved yet, you implicitly assign the database for the
        # base object.
        chris = Person(name="Chris Mills")
        html5 = Book(title="Dive into HTML5", published=datetime.date(2010, 3, 15))
        # initially, no db assigned
        self.assertEqual(chris._state.db, None)
        self.assertEqual(html5._state.db, None)

        # old object comes from 'other', so the new object is set to use the
        # source of 'other'...
        self.assertEqual(dive._state.db, 'other')
        dive.editor = chris
        html5.editor = mark

        self.assertEqual(dive._state.db, 'other')
        self.assertEqual(mark._state.db, 'other')
        self.assertEqual(chris._state.db, 'default')
        self.assertEqual(html5._state.db, 'default')

        # This also works if you assign the FK in the constructor
        water = Book(title="Dive into Water", published=datetime.date(2001, 1, 1), editor=mark)
        self.assertEqual(water._state.db, 'default')

        # If you create an object through a FK relation, it will be
        # written to the write database, even if the original object
        # was on the read database
        cheesecake = mark.edited.create(title='Dive into Cheesecake', published=datetime.date(2010, 3, 15))
        self.assertEqual(cheesecake._state.db, 'default')

        # Same goes for get_or_create, regardless of whether getting or creating
        cheesecake, created = mark.edited.get_or_create(title='Dive into Cheesecake', published=datetime.date(2010, 3, 15))
        self.assertEqual(cheesecake._state.db, 'default')

        puddles, created = mark.edited.get_or_create(title='Dive into Puddles', published=datetime.date(2010, 3, 15))
        self.assertEqual(puddles._state.db, 'default')

    def test_o2o_cross_database_protection(self):
        "Operations that involve sharing FK objects across databases raise an error"
        # Create a user and profile on the default database
        alice = User.objects.db_manager('default').create_user('alice', 'alice@example.com')

        # Create a user and profile on the other database
        bob = User.objects.db_manager('other').create_user('bob', 'bob@example.com')

        # Set a one-to-one relation with an object from a different database
        alice_profile = UserProfile.objects.create(user=alice, flavor='chocolate')
        try:
            bob.userprofile = alice_profile
        except ValueError:
            self.fail("Assignment across master/slave databases with a common source should be ok")

        # Database assignments of original objects haven't changed...
        self.assertEqual(alice._state.db, 'default')
        self.assertEqual(alice_profile._state.db, 'default')
        self.assertEqual(bob._state.db, 'other')

        # ... but they will when the affected object is saved.
        bob.save()
        self.assertEqual(bob._state.db, 'default')

class AuthTestCase(TestCase):
    multi_db = True

    def setUp(self):
        # Make the 'other' database appear to be a slave of the 'default'
        self.old_routers = router.routers
        router.routers = [AuthRouter()]

    def tearDown(self):
        # Restore the 'other' database as an independent database
        router.routers = self.old_routers

    def test_auth_manager(self):
        "The methods on the auth manager obey database hints"
        # Create one user using default allocation policy
        User.objects.create_user('alice', 'alice@example.com')

        # Create another user, explicitly specifying the database
        User.objects.db_manager('default').create_user('bob', 'bob@example.com')

        # The second user only exists on the other database
        alice = User.objects.using('other').get(username='alice')

        self.assertEqual(alice.username, 'alice')
        self.assertEqual(alice._state.db, 'other')

        self.assertRaises(User.DoesNotExist, User.objects.using('default').get, username='alice')

        # The second user only exists on the default database
        bob = User.objects.using('default').get(username='bob')

        self.assertEqual(bob.username, 'bob')
        self.assertEqual(bob._state.db, 'default')

        self.assertRaises(User.DoesNotExist, User.objects.using('other').get, username='bob')

        # That is... there is one user on each database
        self.assertEqual(User.objects.using('default').count(), 1)
        self.assertEqual(User.objects.using('other').count(), 1)

    def test_dumpdata(self):
        "Check that dumpdata honors allow_syncdb restrictions on the router"
        User.objects.create_user('alice', 'alice@example.com')
        User.objects.db_manager('default').create_user('bob', 'bob@example.com')

        # Check that dumping the default database doesn't try to include auth
        # because allow_syncdb prohibits auth on default
        new_io = StringIO()
        try:
            management.call_command('dumpdata', 'auth', format='json', database='default', stdout=new_io)
        except:
            import traceback; traceback.print_exc()
            raise
        command_output = new_io.getvalue().strip()
        self.assertEqual(command_output, '[]')

        # Check that dumping the other database does include auth
        new_io = StringIO()
        management.call_command('dumpdata', 'auth', format='json', database='other', stdout=new_io)
        command_output = new_io.getvalue().strip()
        self.assertTrue('"email": "alice@example.com",' in command_output)

_missing = object()
class UserProfileTestCase(TestCase):
    def setUp(self):
        self.old_auth_profile_module = getattr(settings, 'AUTH_PROFILE_MODULE', _missing)
        settings.AUTH_PROFILE_MODULE = 'multiple_database.UserProfile'

    def tearDown(self):
        if self.old_auth_profile_module is _missing:
            del settings.AUTH_PROFILE_MODULE
        else:
            settings.AUTH_PROFILE_MODULE = self.old_auth_profile_module

    def test_user_profiles(self):

        alice = User.objects.create_user('alice', 'alice@example.com')
        bob = User.objects.db_manager('other').create_user('bob', 'bob@example.com')

        alice_profile = UserProfile(user=alice, flavor='chocolate')
        alice_profile.save()

        bob_profile = UserProfile(user=bob, flavor='crunchy frog')
        bob_profile.save()

        self.assertEqual(alice.get_profile().flavor, 'chocolate')
        self.assertEqual(bob.get_profile().flavor, 'crunchy frog')

class AntiPetRouter(object):
    # A router that only expresses an opinion on syncdb,
    # passing pets to the 'other' database

    def allow_syncdb(self, db, model):
        "Make sure the auth app only appears on the 'other' db"
        if db == 'other':
            return model._meta.object_name == 'Pet'
        else:
            return model._meta.object_name != 'Pet'
        return None

class FixtureTestCase(TestCase):
    multi_db = True
    fixtures = ['multidb-common', 'multidb']

    def setUp(self):
        # Install the anti-pet router
        self.old_routers = router.routers
        router.routers = [AntiPetRouter()]

    def tearDown(self):
        # Restore the 'other' database as an independent database
        router.routers = self.old_routers

    def test_fixture_loading(self):
        "Multi-db fixtures are loaded correctly"
        # Check that "Pro Django" exists on the default database, but not on other database
        try:
            Book.objects.get(title="Pro Django")
            Book.objects.using('default').get(title="Pro Django")
        except Book.DoesNotExist:
            self.fail('"Pro Django" should exist on default database')

        self.assertRaises(Book.DoesNotExist,
            Book.objects.using('other').get,
            title="Pro Django"
        )

        # Check that "Dive into Python" exists on the default database, but not on other database
        try:
            Book.objects.using('other').get(title="Dive into Python")
        except Book.DoesNotExist:
            self.fail('"Dive into Python" should exist on other database')

        self.assertRaises(Book.DoesNotExist,
            Book.objects.get,
            title="Dive into Python"
        )
        self.assertRaises(Book.DoesNotExist,
            Book.objects.using('default').get,
            title="Dive into Python"
        )

        # Check that "Definitive Guide" exists on the both databases
        try:
            Book.objects.get(title="The Definitive Guide to Django")
            Book.objects.using('default').get(title="The Definitive Guide to Django")
            Book.objects.using('other').get(title="The Definitive Guide to Django")
        except Book.DoesNotExist:
            self.fail('"The Definitive Guide to Django" should exist on both databases')

    def test_pseudo_empty_fixtures(self):
        "A fixture can contain entries, but lead to nothing in the database; this shouldn't raise an error (ref #14068)"
        new_io = StringIO()
        management.call_command('loaddata', 'pets', stdout=new_io, stderr=new_io)
        command_output = new_io.getvalue().strip()
        # No objects will actually be loaded
        self.assertEqual(command_output, "Installed 0 object(s) (of 2) from 1 fixture(s)")

class PickleQuerySetTestCase(TestCase):
    multi_db = True

    def test_pickling(self):
        for db in connections:
            Book.objects.using(db).create(title='Dive into Python', published=datetime.date(2009, 5, 4))
            qs = Book.objects.all()
            self.assertEqual(qs.db, pickle.loads(pickle.dumps(qs)).db)


class DatabaseReceiver(object):
    """
    Used in the tests for the database argument in signals (#13552)
    """
    def __call__(self, signal, sender, **kwargs):
        self._database = kwargs['using']

class WriteToOtherRouter(object):
    """
    A router that sends all writes to the other database.
    """
    def db_for_write(self, model, **hints):
        return "other"

class SignalTests(TestCase):
    multi_db = True

    def setUp(self):
        self.old_routers = router.routers

    def tearDown(self):
        router.routser = self.old_routers

    def _write_to_other(self):
        "Sends all writes to 'other'."
        router.routers = [WriteToOtherRouter()]

    def _write_to_default(self):
        "Sends all writes to the default DB"
        router.routers = self.old_routers

    def test_database_arg_save_and_delete(self):
        """
        Tests that the pre/post_save signal contains the correct database.
        (#13552)
        """
        # Make some signal receivers
        pre_save_receiver = DatabaseReceiver()
        post_save_receiver = DatabaseReceiver()
        pre_delete_receiver = DatabaseReceiver()
        post_delete_receiver = DatabaseReceiver()
        # Make model and connect receivers
        signals.pre_save.connect(sender=Person, receiver=pre_save_receiver)
        signals.post_save.connect(sender=Person, receiver=post_save_receiver)
        signals.pre_delete.connect(sender=Person, receiver=pre_delete_receiver)
        signals.post_delete.connect(sender=Person, receiver=post_delete_receiver)
        p = Person.objects.create(name='Darth Vader')
        # Save and test receivers got calls
        p.save()
        self.assertEqual(pre_save_receiver._database, DEFAULT_DB_ALIAS)
        self.assertEqual(post_save_receiver._database, DEFAULT_DB_ALIAS)
        # Delete, and test
        p.delete()
        self.assertEqual(pre_delete_receiver._database, DEFAULT_DB_ALIAS)
        self.assertEqual(post_delete_receiver._database, DEFAULT_DB_ALIAS)
        # Save again to a different database
        p.save(using="other")
        self.assertEqual(pre_save_receiver._database, "other")
        self.assertEqual(post_save_receiver._database, "other")
        # Delete, and test
        p.delete(using="other")
        self.assertEqual(pre_delete_receiver._database, "other")
        self.assertEqual(post_delete_receiver._database, "other")

class AttributeErrorRouter(object):
    "A router to test the exception handling of ConnectionRouter"
    def db_for_read(self, model, **hints):
        raise AttributeError

    def db_for_write(self, model, **hints):
        raise AttributeError

class RouterAttributeErrorTestCase(TestCase):
    multi_db = True

    def setUp(self):
        self.old_routers = router.routers
        router.routers = [AttributeErrorRouter()]

    def tearDown(self):
        router.routers = self.old_routers

    def test_attribute_error_read(self):
        "Check that the AttributeError from AttributeErrorRouter bubbles up"
        router.routers = [] # Reset routers so we can save a Book instance
        b = Book.objects.create(title="Pro Django",
                                published=datetime.date(2008, 12, 16))
        router.routers = [AttributeErrorRouter()] # Install our router
        self.assertRaises(AttributeError, Book.objects.get, pk=b.pk)

    def test_attribute_error_save(self):
        "Check that the AttributeError from AttributeErrorRouter bubbles up"
        dive = Book()
        dive.title="Dive into Python"
        dive.published = datetime.date(2009, 5, 4)
        self.assertRaises(AttributeError, dive.save)

    def test_attribute_error_delete(self):
        "Check that the AttributeError from AttributeErrorRouter bubbles up"
        router.routers = [] # Reset routers so we can save our Book, Person instances
        b = Book.objects.create(title="Pro Django",
                                published=datetime.date(2008, 12, 16))
        p = Person.objects.create(name="Marty Alchin")
        b.authors = [p]
        b.editor = p
        router.routers = [AttributeErrorRouter()] # Install our router
        self.assertRaises(AttributeError, b.delete)

class ModelMetaRouter(object):
    "A router to ensure model arguments are real model classes"
    def db_for_write(self, model, **hints):
        if not hasattr(model, '_meta'):
            raise ValueError

class RouterModelArgumentTestCase(TestCase):
    multi_db = True

    def setUp(self):
        self.old_routers = router.routers
        router.routers = [ModelMetaRouter()]

    def tearDown(self):
        router.routers = self.old_routers

    def test_foreignkey_collection(self):
        person = Person.objects.create(name='Bob')
        pet = Pet.objects.create(owner=person, name='Wart')
        # test related FK collection
        person.delete()

########NEW FILE########
__FILENAME__ = utils
../utils.py
########NEW FILE########
__FILENAME__ = models
from django.db import models
from django.conf import settings

from djangotoolbox.fields import ListField, RawField


class RawModel(models.Model):
    raw = RawField()


class Empty(models.Model):
    pass


class IntegerModel(models.Model):
    integer = models.IntegerField()


class Blog(models.Model):
    title = models.CharField(max_length=200, db_index=True)

    class Meta:
        ordering = ['id']


class Post(models.Model):
    title = models.CharField(max_length=200, db_index=True, unique=True)
    content = models.CharField(max_length=1000, db_column='text')
    date_published = models.DateTimeField(null=True, blank=True)
    blog = models.ForeignKey(Blog, null=True, blank=True)


# TODO: Get rid of this model.
class Person(models.Model):
    name = models.CharField(max_length=20)
    surname = models.CharField(max_length=20)
    age = models.IntegerField(null=True, blank=True)
    another_age = models.IntegerField(null=True, blank=True, db_column='age2')

    class Meta:
        unique_together = ('name', 'surname')


class DateModel(models.Model):
    datetime = models.DateTimeField(auto_now_add=True)
    time = models.TimeField(null=True)
    date = models.DateField(null=True)
    _datelist_default = []
    datelist = ListField(models.DateField(), default=_datelist_default)


class Article(models.Model):
    headline = models.CharField(max_length=50)
    pub_date = models.DateTimeField()

########NEW FILE########
__FILENAME__ = tests
import datetime
from operator import attrgetter

from django.db.models import F, Q
from django.db.utils import DatabaseError
# handle pymongo backward compatibility
try:
    from bson.objectid import ObjectId
except ImportError:
    from pymongo.objectid import ObjectId

from models import *
from utils import *


class BasicQueryTests(TestCase):
    """Backend-agnostic query tests."""

    def test_add_and_delete_blog(self):
        Blog.objects.create(title='blog1')
        self.assertEqual(Blog.objects.count(), 1)
        blog2 = Blog.objects.create(title='blog2')
        self.assertIsInstance(blog2.pk, unicode)
        self.assertEqual(Blog.objects.count(), 2)
        blog2.delete()
        self.assertEqual(Blog.objects.count(), 1)
        Blog.objects.filter(title='blog1').delete()
        self.assertEqual(Blog.objects.count(), 0)

    def test_simple_filter(self):
        blog1 = Blog.objects.create(title="same title")
        Blog.objects.create(title="same title")
        Blog.objects.create(title="another title")
        self.assertEqual(Blog.objects.count(), 3)
        self.assertEqual(Blog.objects.get(pk=blog1.pk), blog1)
        self.assertEqual(Blog.objects.filter(title="same title").count(), 2)
        self.assertEqual(
            Blog.objects.filter(title="same title").filter(pk=blog1.pk)
                .count(), 1)
        self.assertEqual(
            Blog.objects.filter(title__startswith="same").count(), 2)
        self.assertEqual(
            Blog.objects.filter(title__istartswith="SAME").count(), 2)
        self.assertEqual(
            Blog.objects.filter(title__endswith="title").count(), 3)
        self.assertEqual(
            Blog.objects.filter(title__iendswith="Title").count(), 3)
        self.assertEqual(
            Blog.objects.filter(title__icontains="same").count(), 2)
        self.assertEqual(
            Blog.objects.filter(title__contains="same").count(), 2)
        self.assertEqual(
            Blog.objects.filter(title__iexact="same Title").count(), 2)
        self.assertEqual(
            Blog.objects.filter(title__regex="s.me.*").count(), 2)
        self.assertEqual(
            Blog.objects.filter(title__iregex="S.me.*").count(), 2)

        for record in [{'name': 'igor', 'surname': 'duck', 'age': 39},
                       {'name': 'andrea', 'surname': 'duck', 'age': 29}]:
            Person.objects.create(**record)
        self.assertEqual(
            Person.objects.filter(name="igor", surname="duck").count(), 1)
        self.assertEqual(
            Person.objects.filter(age__gte=20, surname="duck").count(), 2)

    def test_isnull(self):
        p1 = Post.objects.create(title='a')
        p2 = Post.objects.create(title='b',
                                 date_published=datetime.datetime.now())
        self.assertEqual(Post.objects.get(date_published__isnull=True), p1)
        self.assertEqual(Post.objects.get(date_published__isnull=False), p2)

    def test_range(self):
        i1 = IntegerModel.objects.create(integer=3)
        i2 = IntegerModel.objects.create(integer=10)
        self.assertEqual(IntegerModel.objects.get(integer__range=(2, 4)), i1)

    def test_change_model(self):
        blog1 = Blog.objects.create(title="blog 1")
        self.assertEqual(Blog.objects.count(), 1)
        blog1.title = "new title"
        blog1.save()
        self.assertEqual(Blog.objects.count(), 1)
        self.assertEqual(blog1.title, Blog.objects.all()[0].title)

    def test_skip_limit(self):
        now = datetime.datetime.now()
        before = now - datetime.timedelta(days=1)

        Post(title="entry 1", date_published=now).save()
        Post(title="entry 2", date_published=before).save()
        Post(title="entry 3", date_published=before).save()

        self.assertEqual(len(Post.objects.order_by('-date_published')[:2]), 2)
        # With step.
        self.assertEqual(
            len(Post.objects.order_by('date_published')[1:2:1]), 1)
        self.assertEqual(len(Post.objects.order_by('date_published')[1:2]), 1)

    def test_date_datetime_and_time(self):
        self.assertEqual(DateModel().datelist, DateModel._datelist_default)
        self.assert_(DateModel().datelist is not DateModel._datelist_default)
        DateModel.objects.create()
        self.assertNotEqual(DateModel.objects.get().datetime, None)
        DateModel.objects.update(
            time=datetime.time(hour=3, minute=5, second=7),
            date=datetime.date(year=2042, month=3, day=5),
            datelist=[datetime.date(2001, 1, 2)])
        self.assertEqual(
            DateModel.objects.values_list('time', 'date', 'datelist').get(),
            (datetime.time(hour=3, minute=5, second=7),
             datetime.date(year=2042, month=3, day=5),
             [datetime.date(year=2001, month=1, day=2)]))

    def test_dates_less_and_more_than(self):
        now = datetime.datetime.now()
        before = now + datetime.timedelta(days=1)
        after = now - datetime.timedelta(days=1)

        entry1 = Post.objects.create(title="entry 1", date_published=now)
        entry2 = Post.objects.create(title="entry 2", date_published=before)
        entry3 = Post.objects.create(title="entry 3", date_published=after)

        self.assertEqualLists(Post.objects.filter(date_published=now),
                              [entry1])
        self.assertEqualLists(Post.objects.filter(date_published__lt=now),
                              [entry3])
        self.assertEqualLists(Post.objects.filter(date_published__gt=now),
                              [entry2])

    def test_year_date(self):
        now = datetime.datetime.now()
        before = now - datetime.timedelta(days=365)

        entry1 = Post.objects.create(title="entry 1", date_published=now)
        entry2 = Post.objects.create(title="entry 2", date_published=before)

        self.assertEqualLists(
            Post.objects.filter(date_published__year=now.year), [entry1])
        self.assertEqualLists(
            Post.objects.filter(date_published__year=before.year), [entry2])

    def test_simple_foreign_keys(self):
        blog1 = Blog.objects.create(title="Blog")
        entry1 = Post.objects.create(title="entry 1", blog=blog1)
        entry2 = Post.objects.create(title="entry 2", blog=blog1)
        self.assertEqual(Post.objects.count(), 2)
        for entry in Post.objects.all():
            self.assertEqual(
                blog1,
                entry.blog)
        blog2 = Blog.objects.create(title="Blog")
        Post.objects.create(title="entry 3", blog=blog2)
        self.assertEqualLists(
            Post.objects.filter(blog=blog1.pk).order_by('pk'),
            [entry1, entry2])
        # XXX: Uncomment this if the corresponding Django has been fixed.
        # entry_without_blog = Post.objects.create(title='x')
        # self.assertEqual(Post.objects.get(blog=None), entry_without_blog)
        # self.assertEqual(Post.objects.get(blog__isnull=True),
        #                                   entry_without_blog)

    def test_foreign_keys_bug(self):
        blog1 = Blog.objects.create(title="Blog")
        entry1 = Post.objects.create(title="entry 1", blog=blog1)
        self.assertEqualLists(Post.objects.filter(blog=blog1), [entry1])

    def test_regex_matchers(self):
        # (startswith, contains, ... uses regex on MongoDB).
        blogs = [Blog.objects.create(title=title) for title in
                 ('Hello', 'worLd', 'D', '[(', '**', '\\')]
        for lookup, value, objs in [
            ('startswith', 'h', []),
            ('istartswith', 'h', [0]),
            ('contains', '(', [3]),
            ('icontains', 'l', [0, 1]),
            ('endswith', '\\', [5]),
            ('iendswith', 'D', [1, 2]),
        ]:
            self.assertEqualLists(
                [blog for i, blog in enumerate(blogs) if i in objs],
                Blog.objects.filter(**{'title__%s' % lookup: value})
                    .order_by('pk'))
            self.assertEqualLists(
                [blog for i, blog in enumerate(blogs) if i not in objs],
                Blog.objects.filter(
                    ~Q(**{'title__%s' % lookup: value})).order_by('pk'))

    def test_multiple_regex_matchers(self):
        posts = [
            {'title': 'Title A', 'content': 'Content A'},
            {'title': 'Title B', 'content': 'Content B'},
            {'title': 'foo bar', 'content': 'spam eggs'},
            {'title': 'asd asd', 'content': 'fghj fghj'},
        ]
        posts = [Post.objects.create(**post) for post in posts]

        # Test that we can combine multiple regex matchers:
        self.assertEqualLists(
            Post.objects.filter(title='Title A'),
            Post.objects.filter(title__startswith='T', title__istartswith='t')
                        .filter(title__endswith='A', title__iendswith='a')
                        .filter(title__contains='l', title__icontains='L'))

        # Test that multiple regex matchers can be used on more
        # than one field.
        self.assertEqualLists(
            Post.objects.all()[:3],
            Post.objects.filter(title__contains=' ', content__icontains='e'))

        # Test multiple negated regex matchers.
        self.assertEqual(
            Post.objects.filter(~Q(title__icontains='I'))
                        .get(~Q(title__endswith='d')),
            Post.objects.all()[2])
        self.assertEqual(
            Post.objects.filter(~Q(title__startswith='T'))
                        .get(~Q(content__startswith='s')),
            Post.objects.all()[3])

        # Test negated regex matchers combined with non-negated
        # regex matchers.
        self.assertEqual(
            Post.objects.filter(title__startswith='Title')
                        .get(~Q(title__startswith='Title A')),
            Post.objects.all()[1])
        self.assertEqual(
            Post.objects.filter(title__startswith='T', title__contains=' ')
                        .filter(content__startswith='C')
                        .get(~Q(content__contains='Y',
                                content__icontains='B')),
            Post.objects.all()[0])

        self.assertEqualLists(
            Post.objects.filter(title__startswith='T')
                        .exclude(title='Title A'),
            [posts[1]])
        self.assertEqual(
            Post.objects.exclude(title='asd asd')
                        .exclude(title__startswith='T').get(),
            posts[2])
        self.assertEqual(
            Post.objects.exclude(title__startswith='T')
                        .exclude(title='asd asd').get(),
            posts[2])

    def test_multiple_filter_on_same_name(self):
        Blog.objects.create(title='a')
        self.assertEqual(
            Blog.objects.filter(title='a').filter(title='a')
                        .filter(title='a').get(),
            Blog.objects.get())
        self.assertEqualLists(
            Blog.objects.filter(title='a').filter(title='b')
                        .filter(title='a'),
            [])

        # Tests chaining on primary keys.
        blog_id = Blog.objects.get().id
        self.assertEqual(
            Blog.objects.filter(pk=blog_id).filter(pk=blog_id).get(),
            Blog.objects.get())

    def test_negated_Q(self):
        blogs = [Blog.objects.create(title=title) for title in
                 ('blog', 'other blog', 'another blog')]
        self.assertEqualLists(
            Blog.objects.filter(title='blog') |
                Blog.objects.filter(~Q(title='another blog')),
            [blogs[0], blogs[1]])
        self.assertEqual(
            blogs[2],
            Blog.objects.get(~Q(title='blog') & ~Q(title='other blog')))
        self.assertEqualLists(
            Blog.objects.filter(~Q(title='another blog') | ~Q(title='blog') |
                                ~Q(title='aaaaa') | ~Q(title='fooo') |
                                Q(title__in=[b.title for b in blogs])),
            blogs)
        self.assertEqual(
            Blog.objects.filter(Q(title__in=['blog', 'other blog']),
                                ~Q(title__in=['blog'])).get(),
            blogs[1])
        self.assertEqual(
            Blog.objects.filter().exclude(~Q(title='blog')).get(),
            blogs[0])

    def test_exclude_plus_filter(self):
        objs = [IntegerModel.objects.create(integer=i) for i in (1, 2, 3, 4)]
        self.assertEqual(
            IntegerModel.objects.exclude(integer=1)
                                .exclude(integer=2)
                                .get(integer__gt=3),
            objs[3])
        self.assertEqual(
            IntegerModel.objects.exclude(integer=1)
                                .exclude(integer=2)
                                .get(integer=3),
            objs[2])

    def test_nin(self):
        Blog.objects.create(title='a')
        Blog.objects.create(title='b')
        self.assertEqual(Blog.objects.get(~Q(title__in='b')),
                         Blog.objects.get(title='a'))

    def test_simple_or_queries(self):
        obj1 = Blog.objects.create(title='1')
        obj2 = Blog.objects.create(title='1')
        obj3 = Blog.objects.create(title='2')
        obj4 = Blog.objects.create(title='3')

        self.assertEqualLists(
            Blog.objects.filter(title='1'),
            [obj1, obj2])
        self.assertEqualLists(
            Blog.objects.filter(title='1') | Blog.objects.filter(title='2'),
            [obj1, obj2, obj3])
        self.assertEqualLists(
            Blog.objects.filter(Q(title='2') | Q(title='3')),
            [obj3, obj4])

        self.assertEqualLists(
            Blog.objects.filter(Q(Q(title__lt='4') & Q(title__gt='2')) |
                                  Q(title='1')).order_by('id'),
            [obj1, obj2, obj4])

    def test_can_save_empty_model(self):
        obj = Empty.objects.create()
        self.assertNotEqual(obj.id, None)
        self.assertNotEqual(obj.id, 'None')
        self.assertEqual(obj, Empty.objects.get(id=obj.id))

    def test_values_query(self):
        blog = Blog.objects.create(title='fooblog')
        entry = Post.objects.create(blog=blog, title='footitle',
                                    content='foocontent')
        entry2 = Post.objects.create(blog=blog, title='footitle2',
                                     content='foocontent2')
        self.assertEqualLists(
            Post.objects.values(),
            [{'blog_id': blog.id, 'title': u'footitle', 'id': entry.id,
              'content': u'foocontent', 'date_published': None},
             {'blog_id': blog.id, 'title': u'footitle2', 'id': entry2.id,
              'content': u'foocontent2', 'date_published': None}])
        self.assertEqualLists(
            Post.objects.values('blog'),
            [{'blog': blog.id}, {'blog': blog.id}])
        self.assertEqualLists(
            Post.objects.values_list('blog_id', 'date_published'),
            [(blog.id, None), (blog.id, None)])
        self.assertEqualLists(
            Post.objects.values('title', 'content'),
            [{'title': u'footitle', 'content': u'foocontent'},
             {'title': u'footitle2', 'content': u'foocontent2'}])


class UpdateTests(TestCase):

    def test_update(self):
        blog1 = Blog.objects.create(title="Blog")
        blog2 = Blog.objects.create(title="Blog 2")
        entry1 = Post.objects.create(title="entry 1", blog=blog1)

        Post.objects.filter(pk=entry1.pk).update(blog=blog2)
        self.assertEqualLists(Post.objects.filter(blog=blog2), [entry1])

        Post.objects.filter(blog=blog2).update(title="Title has been updated")
        self.assertEqualLists(Post.objects.filter()[0].title,
                              "Title has been updated")

        Post.objects.filter(blog=blog2).update(title="Last Update Test",
                                               blog=blog1)
        self.assertEqualLists(Post.objects.filter()[0].title,
                              "Last Update Test")

        self.assertEqual(Post.objects.filter(blog=blog1).count(), 1)
        self.assertEqual(Blog.objects.filter(title='Blog').count(), 1)
        Blog.objects.update(title='Blog')
        self.assertEqual(Blog.objects.filter(title='Blog').count(), 2)

    def test_update_id(self):
        self.assertRaisesRegexp(DatabaseError, "Can not modify _id",
                                Post.objects.update, id=ObjectId())

    def test_update_with_F(self):
        john = Person.objects.create(name='john', surname='nhoj', age=42)
        andy = Person.objects.create(name='andy', surname='ydna', age=-5)
        Person.objects.update(age=F('age') + 7)
        self.assertEqual(Person.objects.get(pk=john.id).age, 49)
        self.assertEqual(Person.objects.get(id=andy.pk).age, 2)
        Person.objects.filter(name='john').update(age=F('age')-10)
        self.assertEqual(Person.objects.get(name='john').age, 39)

    def test_update_with_F_and_db_column(self):
        # This test is simmilar to test_update_with_F but tests
        # the update with a column that has a db_column set.
        john = Person.objects.create(name='john', surname='nhoj',
                                     another_age=42)
        andy = Person.objects.create(name='andy', surname='ydna',
                                     another_age=-5)
        Person.objects.update(another_age=F('another_age') + 7)
        self.assertEqual(Person.objects.get(pk=john.id).another_age, 49)
        self.assertEqual(Person.objects.get(id=andy.pk).another_age, 2)
        Person.objects.filter(name='john').update(
            another_age=F('another_age') - 10)
        self.assertEqual(Person.objects.get(name='john').another_age, 39)

    def test_invalid_update_with_F(self):
        self.assertRaises(AssertionError, Person.objects.update,
                          age=F('name') + 1)


class OrderingTests(TestCase):

    def test_dates_ordering(self):
        now = datetime.datetime.now()
        before = now - datetime.timedelta(days=1)

        entry1 = Post.objects.create(title="entry 1", date_published=now)
        entry2 = Post.objects.create(title="entry 2", date_published=before)

        self.assertEqualLists(Post.objects.order_by('-date_published'),
                              [entry1, entry2])
        self.assertEqualLists(Post.objects.order_by('date_published'),
                              [entry2, entry1])


class OrLookupsTests(TestCase):
    """Stolen from the Django test suite, shaked down for m2m tests."""

    def setUp(self):
        self.a1 = Article.objects.create(
            headline='Hello', pub_date=datetime.datetime(2005, 11, 27)).pk
        self.a2 = Article.objects.create(
            headline='Goodbye', pub_date=datetime.datetime(2005, 11, 28)).pk
        self.a3 = Article.objects.create(
            headline='Hello and goodbye',
            pub_date=datetime.datetime(2005, 11, 29)).pk

    def test_filter_or(self):
        self.assertQuerysetEqual(
            Article.objects.filter(headline__startswith='Hello') |
                Article.objects.filter(headline__startswith='Goodbye'),
            ['Hello', 'Goodbye', 'Hello and goodbye'],
            attrgetter('headline'), ordered=False)

        self.assertQuerysetEqual(
            Article.objects.filter(headline__contains='Hello') |
                Article.objects.filter(headline__contains='bye'),
            ['Hello', 'Goodbye', 'Hello and goodbye'],
            attrgetter('headline'), ordered=False)

        self.assertQuerysetEqual(
            Article.objects.filter(headline__iexact='Hello') |
                Article.objects.filter(headline__contains='ood'),
            ['Hello', 'Goodbye', 'Hello and goodbye'],
            attrgetter('headline'), ordered=False)

        self.assertQuerysetEqual(
            Article.objects.filter(Q(headline__startswith='Hello') |
                                   Q(headline__startswith='Goodbye')),
            ['Hello', 'Goodbye', 'Hello and goodbye'],
            attrgetter('headline'), ordered=False)

    def test_stages(self):
        # You can shorten this syntax with code like the following,
        # which is especially useful if building the query in stages:
        articles = Article.objects.all()
        self.assertQuerysetEqual(
            articles.filter(headline__startswith='Hello') &
                articles.filter(headline__startswith='Goodbye'),
            [])
        self.assertQuerysetEqual(
            articles.filter(headline__startswith='Hello') &
                articles.filter(headline__contains='bye'),
            ['Hello and goodbye'],
            attrgetter('headline'))

    def test_pk_q(self):
        self.assertQuerysetEqual(
            Article.objects.filter(Q(pk=self.a1) | Q(pk=self.a2)),
            ['Hello', 'Goodbye'],
            attrgetter('headline'), ordered=False)

        self.assertQuerysetEqual(
            Article.objects.filter(Q(pk=self.a1) | Q(pk=self.a2) |
                                   Q(pk=self.a3)),
            ['Hello', 'Goodbye', 'Hello and goodbye'],
            attrgetter('headline'), ordered=False)

    def test_pk_in(self):
        self.assertQuerysetEqual(
            Article.objects.filter(pk__in=[self.a1, self.a2, self.a3]),
            ['Hello', 'Goodbye', 'Hello and goodbye'],
            attrgetter('headline'), ordered=False)

        self.assertQuerysetEqual(
            Article.objects.filter(pk__in=(self.a1, self.a2, self.a3)),
            ['Hello', 'Goodbye', 'Hello and goodbye'],
            attrgetter('headline'), ordered=False)

        self.assertQuerysetEqual(
            Article.objects.filter(pk__in=[self.a1, self.a2, self.a3]),
            ['Hello', 'Goodbye', 'Hello and goodbye'],
            attrgetter('headline'), ordered=False)

    def test_q_negated(self):
        # Q objects can be negated.
        self.assertQuerysetEqual(
            Article.objects.filter(Q(pk=self.a1) | ~Q(pk=self.a2)),
            ['Hello', 'Hello and goodbye'],
            attrgetter('headline'), ordered=False)

        self.assertQuerysetEqual(
            Article.objects.filter(~Q(pk=self.a1) & ~Q(pk=self.a2)),
            ['Hello and goodbye'],
            attrgetter('headline'), ordered=False)

        # This allows for more complex queries than filter() and
        # exclude() alone would allow.
        self.assertQuerysetEqual(
            Article.objects.filter(Q(pk=self.a1) & (~Q(pk=self.a2) |
                                   Q(pk=self.a3))),
            ['Hello'],
            attrgetter('headline'), ordered=False)

    def test_complex_filter(self):
        # The 'complex_filter' method supports framework features such
        # as 'limit_choices_to' which normally take a single dictionary
        # of lookup arguments but need to support arbitrary queries via
        # Q objects too.
        self.assertQuerysetEqual(
            Article.objects.complex_filter({'pk': self.a1}),
            ['Hello'],
            attrgetter('headline'), ordered=False)

        self.assertQuerysetEqual(
            Article.objects.complex_filter(Q(pk=self.a1) | Q(pk=self.a2)),
            ['Hello', 'Goodbye'],
            attrgetter('headline'), ordered=False)

    def test_empty_in(self):
        # Passing "in" an empty list returns no results ...
        self.assertQuerysetEqual(
            Article.objects.filter(pk__in=[]),
            [], ordered=False)
        # ... but can return results if we OR it with another query.
        self.assertQuerysetEqual(
            Article.objects.filter(Q(pk__in=[]) |
                                   Q(headline__icontains='goodbye')),
            ['Goodbye', 'Hello and goodbye'],
            attrgetter('headline'), ordered=False)

    def test_q_and(self):
        # Q arg objects are ANDed.
        self.assertQuerysetEqual(
            Article.objects.filter(Q(headline__startswith='Hello'),
                                   Q(headline__contains='bye')),
            ['Hello and goodbye'],
            attrgetter('headline'))
        # Q arg AND order is irrelevant.
        self.assertQuerysetEqual(
            Article.objects.filter(Q(headline__contains='bye'),
                                     headline__startswith='Hello'),
            ['Hello and goodbye'],
            attrgetter('headline'))

        self.assertQuerysetEqual(
            Article.objects.filter(Q(headline__startswith='Hello') &
                                   Q(headline__startswith='Goodbye')),
            [])

    def test_q_exclude(self):
        self.assertQuerysetEqual(
            Article.objects.exclude(Q(headline__startswith='Hello')),
            ['Goodbye'],
            attrgetter('headline'))

    def test_other_arg_queries(self):
        # Try some arg queries with operations other than filter.
        self.assertEqual(
            Article.objects.get(Q(headline__startswith='Hello'),
                                Q(headline__contains='bye')).headline,
            'Hello and goodbye')

        self.assertEqual(
            Article.objects.filter(Q(headline__startswith='Hello') |
                                   Q(headline__contains='bye')).count(),
            3)

        self.assertQuerysetEqual(
            Article.objects.filter(Q(headline__startswith='Hello'),
                                   Q(headline__contains='bye')).values(),
            [{'headline': "Hello and goodbye", 'id': self.a3,
              'pub_date': datetime.datetime(2005, 11, 29)}],
            lambda o: o)

        self.assertEqual(
            Article.objects.filter(Q(headline__startswith='Hello'))
                           .in_bulk([self.a1, self.a2]),
            {self.a1: Article.objects.get(pk=self.a1)})

########NEW FILE########
__FILENAME__ = utils
../utils.py
########NEW FILE########
__FILENAME__ = models
from django.db.models import Model

from djangotoolbox.fields import RawField


class SQLiteModel(Model):
    pass


class MongoDBModel(Model):
    # Wnsure this goes to MongoDB on syncdb: SQLite can't
    # handle RawFields.
    o = RawField()

########NEW FILE########
__FILENAME__ = tests
from django.db.utils import DatabaseError
from django.test import TestCase


class RouterTest(TestCase):

    def test_managed_apps(self):
        # MONGODB_MANAGED_APPS = ['query'] : Any 'query' model resides
        # in the MongoDB 'other'.
        from query.models import Blog
        Blog.objects.create()
        self.assertEqual(Blog.objects.using('other').count(), 1)
        self.assertRaisesRegexp(DatabaseError, "no such table",
            Blog.objects.using('default').count)

    def test_managed_models(self):
        # MONGODB_MANAGED_MODELS = ['router.MongoDBModel']:
        # router.models.MongoDBModel resides in MongoDB,
        # .SQLiteModel in SQLite.
        from router.models import MongoDBModel, SQLiteModel
        mongo_obj = MongoDBModel.objects.create()
        sql_obj = SQLiteModel.objects.create()

        self.assertEqual(MongoDBModel.objects.get(), mongo_obj)
        self.assertEqual(SQLiteModel.objects.get(), sql_obj)

        self.assertEqual(MongoDBModel.objects.using('other').get(), mongo_obj)
        self.assertEqual(SQLiteModel.objects.using('default').get(), sql_obj)

        self.assertEqual(SQLiteModel.objects.using('other').count(), 0)
        self.assertRaisesRegexp(DatabaseError, "no such table",
                                MongoDBModel.objects.using('default').count)

########NEW FILE########
__FILENAME__ = runtests
#!/usr/bin/env python
import os
import sys
from types import ModuleType


def runtests(foo, settings='settings', extra=[], test_builtin=False):
    if isinstance(foo, ModuleType):
        settings = foo.__name__
        apps = foo.INSTALLED_APPS
    else:
        apps = foo
    if not test_builtin:
        apps = filter(lambda name: not name.startswith('django.contrib.'),
                      apps)
    # pre-1.6 test runners don't understand full module names
    import django
    if django.VERSION < (1, 6):
        apps = [app.replace('django.contrib.', '') for app in apps]
    execute(['./manage.py', 'test', '--settings', settings] + extra + apps)


def execute_python(lines):
    from textwrap import dedent
    return execute(
        [sys.executable, '-c', dedent(lines)],
        env=dict(os.environ, DJANGO_SETTINGS_MODULE='settings',
                 PYTHONPATH='..'))


def main(short):
    # Run some basic tests outside Django's test environment.
    execute_python('''
        from mongodb.models import RawModel
        RawModel.objects.create(raw=41)
        RawModel.objects.update(raw=42)
        RawModel.objects.all().delete()
        RawModel.objects.create(raw=42)
    ''')

    import settings
    import settings.dbindexer
    import settings.slow_tests

    runtests(settings, extra=['--failfast'] if short else [])

    # Assert we didn't touch the production database.
    execute_python('''
        from mongodb.models import RawModel
        assert RawModel.objects.get().raw == 42
    ''')

    if short:
        exit()

    # Make sure we can syncdb.
    execute(['./manage.py', 'syncdb', '--noinput'])

    runtests(settings.dbindexer)
    runtests(['router'], 'settings.router')
    runtests(settings.INSTALLED_APPS, 'settings.debug')
    runtests(settings.slow_tests, test_builtin=True)


if __name__ == '__main__':
    import sys
    if 'ignorefailures' in sys.argv:
        from subprocess import call as execute
    else:
        from subprocess import check_call as execute
    if 'coverage' in sys.argv:

        def _new_check_call_closure(old_check_call):

            def _new_check_call(cmd, **kwargs):
                if not cmd[0].endswith('python'):
                    cmd = ['coverage', 'run', '-a', '--source',
                           '../django_mongodb_engine'] + cmd
                return old_check_call(cmd, **kwargs)

            return _new_check_call

        execute = _new_check_call_closure(execute)
    main('short' in sys.argv)

########NEW FILE########
__FILENAME__ = dbindexer
from settings import *


DATABASES['mongodb'] = DATABASES['default']
DATABASES['default'] = {'ENGINE': 'dbindexer', 'TARGET': 'mongodb'}

ROOT_URLCONF = ''
DBINDEXER_SITECONF = 'dbindexes'

INSTALLED_APPS = INSTALLED_APPS + ['dbindexer']

########NEW FILE########
__FILENAME__ = debug
from . import *


TEST_DEBUG = True

LOGGING = {
    'version': 1,
    'formatters': {'simple': {'format': '%(levelname)s %(message)s'}},
    'handlers': {
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        }
    },
    'loggers': {
        'django.db.backends': {
            'level': 'DEBUG',
            'handlers': ['console'],
        },
    },
}

########NEW FILE########
__FILENAME__ = router
from settings import *


INSTALLED_APPS = ['query', 'router']

DATABASES['default'] = {'ENGINE': 'django.db.backends.sqlite3', 'NAME': '/tmp/db.sql'}

DATABASE_ROUTERS = ['django_mongodb_engine.router.MongoDBRouter']
MONGODB_MANAGED_APPS = ['query']
MONGODB_MANAGED_MODELS = ['router.MongoDBModel']

########NEW FILE########
__FILENAME__ = serializer
from django_mongodb_engine.creation import DatabaseCreation
from django.core.serializers.json import \
    Serializer, Deserializer as JSONDeserializer


def get_objectid_fields(modelopts, typemap=DatabaseCreation.data_types):
    return [field for field in modelopts.fields if
            typemap.get(field.__class__.__name__) == 'key']


def Deserializer(*args, **kwargs):
    for objwrapper in JSONDeserializer(*args, **kwargs):
        obj = objwrapper.object
        for field in get_objectid_fields(obj._meta):
            value = getattr(obj, field.attname)
            try:
                int(value)
            except (TypeError, ValueError):
                pass
            else:
                setattr(obj, field.attname, int_to_objectid(value))
        yield objwrapper


def int_to_objectid(i):
    return str(i).rjust(24, '0')

########NEW FILE########
__FILENAME__ = settings_base
DATABASES = {
    'default': {
        'ENGINE': 'django_mongodb_engine',
        'NAME': 'test',
        'OPTIONS': {'OPERATIONS': {'safe': True}},
    },
    'other': {
        'ENGINE': 'django_mongodb_engine',
        'NAME': 'test2',
    },
}

SERIALIZATION_MODULES = {'json': 'settings.serializer'}

SECRET_KEY = 'super secret'

try:
    from local_settings import *
except ImportError:
    pass

########NEW FILE########
__FILENAME__ = slow_tests
from settings import *


INSTALLED_APPS = DEFAULT_APPS + ['django.contrib.contenttypes', 'multiple_database']
ROOT_URLCONF = ''
TEST_RUNNER = 'djangotoolbox.test.NonrelTestSuiteRunner'

########NEW FILE########
__FILENAME__ = sqlite
from settings import *


DATABASES = {
    'default': {
        'NAME': 'test',
        'ENGINE': 'sqlite3',
    },
}
for app in ['embedded', 'storage']:
    INSTALLED_APPS.remove(app)

DATABASES['mongodb'] = {'NAME': 'mongodb', 'ENGINE': 'django_mongodb_engine'}

########NEW FILE########
__FILENAME__ = models

########NEW FILE########
__FILENAME__ = tests
# -*- coding: utf-8 -*-
from datetime import datetime, timedelta
import os
import tempfile

from django.core.files.base import ContentFile, File

from django_mongodb_engine.storage import GridFSStorage

from .utils import TestCase


class GridFSStorageTest(TestCase):
    storage_class = GridFSStorage
    temp_dir = tempfile.mktemp()

    def setUp(self):
        self.storage = self.get_storage(self.temp_dir)

    def tearDown(self):
        if hasattr(self.storage, '_db'):
            for collection in self.storage._db.collection_names():
                if not collection.startswith('system.'):
                    self.storage._db.drop_collection(collection)

    def get_storage(self, location, **kwargs):
        return self.storage_class(location=location, **kwargs)

    def test_file_access_options(self):
        """
        Standard file access options are available, and work as
        expected.
        """
        self.assertFalse(self.storage.exists('storage_test'))
        f = self.storage.open('storage_test', 'w')
        f.write('storage contents')
        f.close()
        self.assert_(self.storage.exists('storage_test'))

        test_file = self.storage.open('storage_test', 'r')
        self.assertEqual(test_file.read(), 'storage contents')

        self.storage.delete('storage_test')
        self.assertFalse(self.storage.exists('storage_test'))

    # def test_file_accessed_time(self):
    #     """
    #     File storage returns a Datetime object for the last accessed
    #     time of a file.
    #     """
    #     self.assertFalse(self.storage.exists('test.file'))
    #
    #     f = ContentFile('custom contents')
    #     f_name = self.storage.save('test.file', f)
    #     atime = self.storage.accessed_time(f_name)
    #
    #     self.assertEqual(atime, datetime.fromtimestamp(
    #         os.path.getatime(self.storage.path(f_name))))
    #     self.assertTrue(datetime.now() - self.storage.accessed_time(f_name) <
    #                     timedelta(seconds=2))
    #     self.storage.delete(f_name)

    def test_file_created_time(self):
        """
        File storage returns a Datetime object for the creation time of
        a file.
        """
        self.assertFalse(self.storage.exists('test.file'))

        f = ContentFile('custom contents')
        f_name = self.storage.save('test.file', f)
        ctime = self.storage.created_time(f_name)

        self.assertTrue(datetime.now() - self.storage.created_time(f_name) <
                        timedelta(seconds=2))
        self.storage.delete(f_name)

    # def test_file_modified_time(self):
    #     """
    #     File storage returns a Datetime object for the last modified
    #     time of a file.
    #     """
    #     self.assertFalse(self.storage.exists('test.file'))
    #
    #     f = ContentFile('custom contents')
    #     f_name = self.storage.save('test.file', f)
    #     mtime = self.storage.modified_time(f_name)
    #
    #     self.assertTrue(datetime.now() - self.storage.modified_time(f_name) <
    #                     timedelta(seconds=2))
    #
    #     self.storage.delete(f_name)

    def test_file_save_without_name(self):
        """
        File storage extracts the filename from the content object if
        no name is given explicitly.
        """
        self.assertFalse(self.storage.exists('test.file'))

        f = ContentFile('custom contents')
        f.name = 'test.file'

        storage_f_name = self.storage.save(None, f)

        self.assertEqual(storage_f_name, f.name)

        self.storage.delete(storage_f_name)

    # def test_file_path(self):
    #     """
    #     File storage returns the full path of a file
    #     """
    #     self.assertFalse(self.storage.exists('test.file'))
    #
    #     f = ContentFile('custom contents')
    #     f_name = self.storage.save('test.file', f)
    #
    #     self.assertEqual(self.storage.path(f_name),
    #         os.path.join(self.temp_dir, f_name))
    #
    #     self.storage.delete(f_name)

    def test_file_url(self):
        """
        File storage returns a url to access a given file from the Web.
        """
        self.assertRaises(ValueError, self.storage.url, 'test.file')

        self.storage = self.get_storage(self.storage.location,
                                        base_url='foo/')
        self.assertEqual(self.storage.url('test.file'),
            '%s%s' % (self.storage.base_url, 'test.file'))

    def test_listdir(self):
        """
        File storage returns a tuple containing directories and files.
        """
        self.assertEqual(self.storage.listdir(''), (set(), []))
        self.assertFalse(self.storage.exists('storage_test_1'))
        self.assertFalse(self.storage.exists('storage_test_2'))
        self.assertFalse(self.storage.exists('storage_dir_1'))

        self.storage.save('storage_test_1', ContentFile('custom content'))
        self.storage.save('storage_test_2', ContentFile('custom content'))
        storage = self.get_storage(location=os.path.join(self.temp_dir,
                                                         'storage_dir_1'))
        storage.save('storage_test_3', ContentFile('custom content'))

        dirs, files = self.storage.listdir('')
        self.assertEqual(set(dirs), set([u'storage_dir_1']))
        self.assertEqual(set(files),
                         set([u'storage_test_1', u'storage_test_2']))


class GridFSStorageTestWithoutLocation(GridFSStorageTest):
    # Now test everything without passing a location argument.
    temp_dir = ''

########NEW FILE########
__FILENAME__ = utils
../utils.py
########NEW FILE########
__FILENAME__ = utils
from django.conf import settings
from django.db import connections
from django.db.models import Model
from django.test import TestCase
from django.utils.unittest import skip


class TestCase(TestCase):

    def setUp(self):
        super(TestCase, self).setUp()
        if getattr(settings, 'TEST_DEBUG', False):
            settings.DEBUG = True

    def assertEqualLists(self, a, b):
        self.assertEqual(list(a), list(b))


def skip_all_except(*tests):

    class meta(type):

        def __new__(cls, name, bases, dict):
            for attr in dict.keys():
                if attr.startswith('test_') and attr not in tests:
                    del dict[attr]
            return type.__new__(cls, name, bases, dict)

    return meta


def get_collection(model_or_name):
    if isinstance(model_or_name, type) and issubclass(model_or_name, Model):
        model_or_name = model_or_name._meta.db_table
    return connections['default'].get_collection(model_or_name)

########NEW FILE########
