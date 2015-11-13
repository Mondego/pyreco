__FILENAME__ = base
from django.core.exceptions import ImproperlyConfigured
from django.conf import settings

import pymongo
from .creation import DatabaseCreation
from .client import DatabaseClient

from djangotoolbox.db.base import (
    NonrelDatabaseFeatures,
    NonrelDatabaseWrapper,
    NonrelDatabaseValidation,
    NonrelDatabaseIntrospection,
    NonrelDatabaseOperations
)

from datetime import datetime

class ImproperlyConfiguredWarning(Warning):
    pass

class DatabaseFeatures(NonrelDatabaseFeatures):
    string_based_auto_field = True
    supports_dicts = True

class DatabaseOperations(NonrelDatabaseOperations):
    compiler_module = __name__.rsplit('.', 1)[0] + '.compiler'

    def max_name_length(self):
        return 254

    def check_aggregate_support(self, aggregate):
        from django.db.models.sql.aggregates import Count
        from .contrib.aggregations import MongoAggregate
        if not isinstance(aggregate, (Count, MongoAggregate)):
            raise NotImplementedError("django-mongodb-engine does not support %r "
                                      "aggregates" % type(aggregate))

    def sql_flush(self, style, tables, sequence_list):
        """
        Returns a list of SQL statements that have to be executed to drop
        all `tables`. No SQL in MongoDB, so just drop all tables here and
        return an empty list.
        """
        tables = self.connection.db_connection.collection_names()
        for table in tables:
            if table.startswith('system.'):
                # no do not system collections
                continue
            self.connection.db_connection.drop_collection(table)
        return []

    def value_to_db_date(self, value):
        if value is None:
            return None
        return datetime(value.year, value.month, value.day)

    def value_to_db_time(self, value):
        if value is None:
            return None
        return datetime(1, 1, 1, value.hour, value.minute, value.second,
                                 value.microsecond)


class DatabaseValidation(NonrelDatabaseValidation):
    pass


class DatabaseIntrospection(NonrelDatabaseIntrospection):
    """Database Introspection"""

    def table_names(self):
        """ Show defined models """
        return self.connection.db_connection.collection_names()

    def sequence_list(self):
        # Only required for backends that support ManyToMany relations
        pass


class DatabaseWrapper(NonrelDatabaseWrapper):
    safe_inserts = False
    wait_for_slaves = 0
    _connected = False

    def __init__(self, *args, **kwargs):
        super(DatabaseWrapper, self).__init__(*args, **kwargs)
        self.features = DatabaseFeatures(self)
        self.ops = DatabaseOperations(self)
        self.client = DatabaseClient(self)
        self.creation = DatabaseCreation(self)
        self.validation = DatabaseValidation(self)
        self.introspection = DatabaseIntrospection(self)

    def _cursor(self):
        self._connect()
        return self._connection

    @property
    def db_connection(self):
        """
        Returns the db_connection instance
         (a :class:`pymongo.database.Database`)
        """
        self._connect()
        return self._db_connection

    def _connect(self):
        if not self._connected:
            host = self.settings_dict['HOST'] or None
            port = self.settings_dict['PORT'] or None
            user = self.settings_dict.get('USER', None)
            password = self.settings_dict.get('PASSWORD')
            self.db_name = self.settings_dict['NAME']
            self.safe_inserts = self.settings_dict.get('SAFE_INSERTS', False)
            self.wait_for_slaves = self.settings_dict.get('WAIT_FOR_SLAVES', 0)
            slave_okay = self.settings_dict.get('SLAVE_OKAY', False)

            try:
                if host is not None:
                    if pymongo.version >= '1.8':
                        assert isinstance(host, (basestring, list)), \
                        'If set, HOST must be a string or a list of strings'
                    else:
                        assert isinstance(host, basestring), \
                        'If set, HOST must be a string'

                if port:
                    if isinstance(host, basestring) and \
                            host.startswith('mongodb://'):
                        # If host starts with mongodb:// the port will be
                        # ignored so lets make sure it is None
                        port = None
                        import warnings
                        warnings.warn(
                        "If 'HOST' is a mongodb:// URL, the 'PORT' setting "
                        "will be ignored", ImproperlyConfiguredWarning
                        )
                    else:
                        try:
                            port = int(port)
                        except ValueError:
                            raise ImproperlyConfigured(
                            'If set, PORT must be an integer')

                assert isinstance(self.safe_inserts, bool), \
                'If set, SAFE_INSERTS must be True or False'
                assert isinstance(self.wait_for_slaves, int), \
                'If set, WAIT_FOR_SLAVES must be an integer'
            except AssertionError, e:
                raise ImproperlyConfigured(e)

            self._connection = pymongo.Connection(host=host,
                                                  port=port,
                                                  slave_okay=slave_okay)

            if user and password:
                auth = self._connection[self.db_name].authenticate(user,
                                                                   password)
                if not auth:
                    raise ImproperlyConfigured("Username and/or password for "
                                               "the MongoDB are not correct")

            self._db_connection = self._connection[self.db_name]

            enable_referencing = getattr(settings, 'MONGODB_AUTOMATIC_REFERENCING', False)
            if not enable_referencing:
                # backwards compatibility
                enable_referencing = getattr(settings, 'MONGODB_ENGINE_ENABLE_MODEL_SERIALIZATION', False)
            if enable_referencing:
                from .serializer import TransformDjango
                self._db_connection.add_son_manipulator(TransformDjango())

            # We're done!
            self._connected = True

        # TODO: signal! (see Alex' backend)

########NEW FILE########
__FILENAME__ = client
from django.db.backends import BaseDatabaseClient

class DatabaseClient(BaseDatabaseClient):
    executable_name = 'mongo'

########NEW FILE########
__FILENAME__ = compiler
import sys
import re
import datetime

from functools import wraps

from django.db.utils import DatabaseError
from django.db.models.fields import NOT_PROVIDED
from django.db.models import F

from django.db.models.sql import aggregates as sqlaggregates
from django.db.models.sql.constants import MULTI, SINGLE
from django.db.models.sql.where import AND, OR
from django.utils.tree import Node

import pymongo
from pymongo.objectid import ObjectId

from djangotoolbox.db.basecompiler import NonrelQuery, NonrelCompiler, \
    NonrelInsertCompiler, NonrelUpdateCompiler, NonrelDeleteCompiler

from .query import A
from .contrib import RawQuery, RawSpec

def safe_regex(regex, *re_args, **re_kwargs):
    def wrapper(value):
        return re.compile(regex % re.escape(value), *re_args, **re_kwargs)
    wrapper.__name__ = 'safe_regex (%r)' % regex
    return wrapper

OPERATORS_MAP = {
    'exact':        lambda val: val,
    'iexact':       safe_regex('^%s$', re.IGNORECASE),
    'startswith':   safe_regex('^%s'),
    'istartswith':  safe_regex('^%s', re.IGNORECASE),
    'endswith':     safe_regex('%s$'),
    'iendswith':    safe_regex('%s$', re.IGNORECASE),
    'contains':     safe_regex('%s'),
    'icontains':    safe_regex('%s', re.IGNORECASE),
    'regex':    lambda val: re.compile(val),
    'iregex':   lambda val: re.compile(val, re.IGNORECASE),
    'gt':       lambda val: {'$gt': val},
    'gte':      lambda val: {'$gte': val},
    'lt':       lambda val: {'$lt': val},
    'lte':      lambda val: {'$lte': val},
    'range':    lambda val: {'$gte': val[0], '$lte': val[1]},
#    'year':     lambda val: {'$gte': val[0], '$lt': val[1]},
    'isnull':   lambda val: None if val else {'$ne': None},
    'in':       lambda val: {'$in': val},
}

NEGATED_OPERATORS_MAP = {
    'exact':    lambda val: {'$ne': val},
    'gt':       lambda val: {'$lte': val},
    'gte':      lambda val: {'$lt': val},
    'lt':       lambda val: {'$gte': val},
    'lte':      lambda val: {'$gt': val},
    'isnull':   lambda val: {'$ne': None} if val else None,
    'in':       lambda val: val
}


def first(test_func, iterable):
    for item in iterable:
        if test_func(item):
            return item

def safe_call(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except pymongo.errors.PyMongoError, e:
            raise DatabaseError, DatabaseError(str(e)), sys.exc_info()[2]
    return wrapper


class DBQuery(NonrelQuery):
    # ----------------------------------------------
    # Public API
    # ----------------------------------------------
    def __init__(self, compiler, fields):
        super(DBQuery, self).__init__(compiler, fields)
        db_table = self.query.get_meta().db_table
        self._collection = self.connection.db_connection[db_table]
        self._ordering = []
        self.db_query = {}

    # This is needed for debugging
    def __repr__(self):
        return '<DBQuery: %r ORDER %r>' % (self.db_query, self._ordering)

    @property
    def collection(self):
        return self._collection

    def fetch(self, low_mark, high_mark):
        results = self._get_results()
        primarykey_column = self.query.get_meta().pk.column
        for entity in results:
            entity[primarykey_column] = entity.pop('_id')
            yield entity

    @safe_call
    def count(self, limit=None):
        results = self._get_results()
        if limit is not None:
            results.limit(limit)
        return results.count()

    @safe_call
    def delete(self):
        self._collection.remove(self.db_query)

    @safe_call
    def order_by(self, ordering):
        for order in ordering:
            if order.startswith('-'):
                order, direction = order[1:], pymongo.DESCENDING
            else:
                direction = pymongo.ASCENDING
            if order == self.query.get_meta().pk.column:
                order = '_id'
            self._ordering.append((order, direction))
        return self

    def add_filters(self, filters, query=None):
        children = self._get_children(filters.children)

        if query is None:
            query = self.db_query

            if len(children) == 1 and isinstance(children[0], RawQuery):
                self.db_query = children[0].query
                return

        if filters.connector is OR:
            or_conditions = query['$or'] = []

        if filters.negated:
            self._negated = not self._negated

        for child in children:
            if filters.connector is OR:
                subquery = {}
            else:
                subquery = query

            if isinstance(child, RawQuery):
                raise TypeError("Can not combine raw queries with regular filters")

            if isinstance(child, Node):
                if filters.connector is OR and child.connector is OR:
                   if len(child.children) > 1:
                        raise DatabaseError("Nested ORs are not supported")

                if filters.connector is OR and filters.negated:
                    raise NotImplementedError("Negated ORs are not implemented")

                self.add_filters(child, query=subquery)

                if filters.connector is OR and subquery:
                    or_conditions.extend(subquery.pop('$or', []))
                    or_conditions.append(subquery)
            else:
                column, lookup_type, db_type, value = self._decode_child(child)
                if column == self.query.get_meta().pk.column:
                    column = '_id'

                existing = subquery.get(column)

                if self._negated and isinstance(existing, dict) and '$ne' in existing:
                    raise DatabaseError(
                        "Negated conditions can not be used in conjunction ( ~Q1 & ~Q2 )\n"
                        "Try replacing your condition with  ~Q(foo__in=[...])"
                    )

                if isinstance(value, A):
                    field = first(lambda field: field.attname == column, self.fields)
                    column, value = value.as_q(field)

                if self._negated:
                    if lookup_type in NEGATED_OPERATORS_MAP:
                        op_func = NEGATED_OPERATORS_MAP[lookup_type]
                    else:
                        def op_func(value):
                            return {'$not' : OPERATORS_MAP[lookup_type](value)}
                else:
                    op_func = OPERATORS_MAP[lookup_type]
                value = op_func(self.convert_value_for_db(db_type, value))

                if existing is not None:
                    key = '$all' if not self._negated else '$nin'
                    if isinstance(value, dict):
                        assert isinstance(existing, dict)
                        existing.update(value)
                    else:
                        if isinstance(existing, dict) and key in existing:
                            existing[key].append(value)
                        else:
                            if isinstance(existing, dict):
                                existing.update({key: value})
                            else:
                                subquery[column] = {key: [existing, value]}
                else:
                    subquery[column] = value

                query.update(subquery)

        if filters.negated:
            self._negated = not self._negated

    def _get_results(self):
        if self.query.select_fields:
            fields = dict((field.attname, 1) for field in self.query.select_fields)
        else:
            fields = None
        results = self._collection.find(self.db_query, fields=fields)
        if self._ordering:
            results.sort(self._ordering)
        if self.query.low_mark > 0:
            results.skip(self.query.low_mark)
        if self.query.high_mark is not None:
            results.limit(self.query.high_mark - self.query.low_mark)
        return results

class SQLCompiler(NonrelCompiler):
    """
    A simple query: no joins, no distinct, etc.
    """
    query_class = DBQuery

    def _split_db_type(self, db_type):
        try:
            db_type, db_subtype = db_type.split(':', 1)
        except ValueError:
            db_subtype = None
        return db_type, db_subtype

    def convert_value_for_db(self, db_type, value):
        if db_type is None or value is None:
            return value

        db_type, db_subtype = self._split_db_type(db_type)
        if db_subtype is not None:
            if isinstance(value, (set, list, tuple)):
                # Sets are converted to lists here because MongoDB has not sets.
                return [self.convert_value_for_db(db_subtype, subvalue)
                        for subvalue in value]
            elif isinstance(value, dict):
                return dict((key, self.convert_value_for_db(db_subtype, subvalue))
                            for key, subvalue in value.iteritems())

        if isinstance(value, (set, list, tuple)):
            # most likely a list of ObjectIds when doing a .delete() query
            return [self.convert_value_for_db(db_type, val) for val in value]

        if db_type == 'objectid':
            return ObjectId(value)

        # Pass values of any type not covered above as they are.
        # PyMongo will complain if they can't be encoded.
        return value

    def convert_value_from_db(self, db_type, value):
        if db_type is None:
            return value

        if value is None or value is NOT_PROVIDED:
            # ^^^ it is *crucial* that this is not written as 'in (None, NOT_PROVIDED)'
            # because that would call value's __eq__ method, which in case value
            # is an instance of serializer.LazyModelInstance does a database query.
            return None

        db_type, db_subtype = self._split_db_type(db_type)
        if db_subtype is not None:
            for field, type_ in [('SetField', set), ('ListField', list)]:
                if db_type == field:
                    return type_(self.convert_value_from_db(db_subtype, subvalue)
                                 for subvalue in value)
            if db_type == 'DictField':
                return dict((key, self.convert_value_from_db(db_subtype, subvalue))
                            for key, subvalue in value.iteritems())

        if db_type == 'objectid':
            return unicode(value)

        if db_type == 'date':
            return datetime.date(value.year, value.month, value.day)

        if db_type == 'time':
            return datetime.time(value.hour, value.minute, value.second,
                                 value.microsecond)
        return value

    def insert_params(self):
        conn = self.connection
        params = {'safe': conn.safe_inserts}
        if conn.wait_for_slaves:
            params['w'] = conn.wait_for_slaves
        return params

    @property
    def _collection(self):
        connection = self.connection.db_connection
        db_table = self.query.get_meta().db_table
        return connection[db_table]

    def _save(self, data, return_id=False):
        primary_key = self._collection.save(data, **self.insert_params())
        if return_id:
            return unicode(primary_key)

    def execute_sql(self, result_type=MULTI):
        """
        Handles aggregate/count queries
        """
        aggregations = self.query.aggregate_select.items()

        if len(aggregations) == 1 and isinstance(aggregations[0][1], sqlaggregates.Count):
            # Ne need for full-featured aggregation processing if we only
            # want to count() -- let djangotoolbox's simple Count aggregation
            # implementation handle this case.
            return super(SQLCompiler, self).execute_sql(result_type)

        from .contrib import aggregations as aggregations_module
        sqlagg, reduce, finalize, order, initial = [], [], [], [], {}
        query = self.build_query()

        # First aggregations implementation
        # THIS CAN/WILL BE IMPROVED!!!
        for alias, aggregate in aggregations:
            if isinstance(aggregate, sqlaggregates.Aggregate):
                if isinstance(aggregate, sqlaggregates.Count):
                    order.append(None)
                    # Needed to keep the iteration order which is important in the returned value.
                    sqlagg.append(self.get_count())
                    continue

                aggregate_class = getattr(aggregations_module, aggregate.__class__.__name__)
                # aggregation availability has been checked in check_aggregate_support in base.py

                field = aggregate.source.name if aggregate.source else '_id'
                if alias is None:
                    alias = '_id__%s' % cls_name
                aggregate = aggregate_class(field, **aggregate.extra)
                aggregate.add_to_query(self.query, alias, aggregate.col, aggregate.source,
                                       aggregate.extra.get("is_summary", False))

            order.append(aggregate.alias) # just to keep the right order
            initial_, reduce_, finalize_ = aggregate.as_query(query)
            initial.update(initial_)
            reduce.append(reduce_)
            finalize.append(finalize_)

        cursor = query.collection.group(None,
                            query.db_query,
                            initial,
                            reduce="function(doc, out){ %s }" % "; ".join(reduce),
                            finalize="function(out){ %s }" % "; ".join(finalize))

        ret = []
        for alias in order:
            result = cursor[0][alias] if alias else sqlagg.pop(0)
            if result_type is MULTI:
                result = [result]
            ret.append(result)
        return ret

class SQLInsertCompiler(NonrelInsertCompiler, SQLCompiler):
    @safe_call
    def insert(self, data, return_id=False):
        pk_column = self.query.get_meta().pk.column
        try:
            data['_id'] = data.pop(pk_column)
        except KeyError:
            pass
        return self._save(data, return_id)

# TODO: Define a common nonrel API for updates and add it to the nonrel
# backend base classes and port this code to that API
class SQLUpdateCompiler(NonrelUpdateCompiler, SQLCompiler):
    query_class = DBQuery

    @safe_call
    def execute_sql(self, return_id=False):
        values = self.query.values
        if len(values) == 1 and isinstance(values[0][2], RawSpec):
            spec, kwargs = values[0][2].spec, values[0][2].kwargs
            kwargs['multi'] = True
        else:
            spec, kwargs = self._get_update_spec()
        return self._collection.update(self.build_query().db_query, spec, **kwargs)

    def _get_update_spec(self):
        multi = True
        spec = {}
        for field, o, value in self.query.values:
            if field.unique:
                multi = False
            if hasattr(value, 'prepare_database_save'):
                value = value.prepare_database_save(field)
            else:
                value = field.get_db_prep_save(value, connection=self.connection)

            value = self.convert_value_for_db(field.db_type(), value)
            if hasattr(value, "evaluate"):
                assert value.connector in (value.ADD, value.SUB)
                assert not value.negated
                assert not value.subtree_parents
                lhs, rhs = value.children
                if isinstance(lhs, F):
                    assert not isinstance(rhs, F)
                    if value.connector == value.SUB:
                        rhs = -rhs
                else:
                    assert value.connector == value.ADD
                    rhs, lhs = lhs, rhs
                spec.setdefault("$inc", {})[lhs.name] = rhs
            else:
                spec.setdefault("$set", {})[field.column] = value

        return spec, {'multi' : multi}

class SQLDeleteCompiler(NonrelDeleteCompiler, SQLCompiler):
    pass

########NEW FILE########
__FILENAME__ = aggregations
from django.db.models import Aggregate

class MongoAggregate(Aggregate):
    is_ordinal = False
    is_computed = False

    def add_to_query(self, query, alias, col, source, is_summary):
        """Add the aggregate to the nominated query.

        This method is used to convert the generic Aggregate definition into a
        backend-specific definition.

         * query is the backend-specific query instance to which the aggregate
           is to be added.
         * col is a column reference describing the subject field
           of the aggregate. It can be an alias, or a tuple describing
           a table and column name.
         * source is the underlying field or aggregate definition for
           the column reference. If the aggregate is not an ordinal or
           computed type, this reference is used to determine the coerced
           output type of the aggregate.
         * is_summary is a boolean that is set True if the aggregate is a
           summary value rather than an annotation.
        """
        self.alias = alias
        self.field = self.source = source

        if self.valid_field_types and not self.source.get_internal_type() in self.valid_field_types:
            raise RuntimeError()
        query.aggregates[alias] = self

    def as_sql(self):
        pass

class Count(MongoAggregate):
    name = "Count"
    valid_field_types = None

    def as_query(self, query):
        return {self.alias : 0}, \
               "out.%s++" % (self.alias), \
               ""

class Min(MongoAggregate):
    name = "Min"
    valid_field_types = ("IntegerField", "FloatField", 'DateField', 'DateTimeField', 'TimeField')

    def as_query(self, query):
        return {self.alias : "null"}, \
               "out.%s = (out.%s == 'null' || doc.%s < out.%s) ? doc.%s: out.%s" % (self.alias, self.alias, self.lookup, self.alias, self.lookup, self.alias), \
               ""

class Max(MongoAggregate):
    name = "Max"
    valid_field_types = ("IntegerField", "FloatField", 'DateField', 'DateTimeField', 'TimeField')

    def as_query(self, query):
        return {self.alias : "null"}, \
               "out.%s = (out.%s == 'null' || doc.%s > out.%s) ? doc.%s: out.%s" % (self.alias, self.alias, self.lookup, self.alias, self.lookup, self.alias), \
               ""

class Avg(MongoAggregate):
    name = "Avg"
    is_computed = True
    valid_field_types = ("IntegerField", "FloatField")

    def as_query(self, query):
        return {"%s__count" % self.alias : 0, "%s__total" % self.alias : 0}, \
                "out.%s__count++; out.%s__total+=doc.%s" % (self.alias, self.alias, self.lookup), \
                "out.%s = out.%s__total / out.%s__count" % (self.alias, self.alias, self.alias)
########NEW FILE########
__FILENAME__ = mapreduce
from django.db import connections

class MapReduceResult(object):
    """
    Represents one item of a MapReduce result array.

    :param model: the model on that query the MapReduce was performed
    :param key: the *key* from the result item
    :param value: the *value* from the result item
    """
    def __init__(self, model, key, value):
        self.model = model
        self.key = key
        self.value = value

    def get_object(self):
        """
        Fetches the model instance with ``self.key`` as primary key from the
        database (doing a database query).
        """
        return self.model.objects.get(**{self.model._meta.pk.attname : self.key})

    def __repr__(self):
        return '<%s model=%r key=%r value=%r>' % \
                (self.__class__.__name__, self.model.__name__, self.key, self.value)

# TODO:
# - Query support
# - Field name substitution (e.g. id -> _id)
class MapReduceMixin(object):
    """
    Mixes MapReduce support into your manager.
    """
    def _get_collection(self):
        return connections[self.db].db_connection[self.model._meta.db_table]

    def map_reduce(self, map_func, reduce_func, finalize_func=None,
                   limit=None, scope=None, keeptemp=False):
        """
        Performs a MapReduce on the server using `map_func`, `reduce_func` and
        (optionally) `finalize_func`.

        Returns a list of :class:`.MapReduceResult` instances, one instance for
        each item in the array the MapReduce query returns.

        MongoDB >= 1.1 and PyMongo >= 1.2 are required for using this feature.

        :param map_func: JavaScript map function as string
        :param reduce_func: The JavaScript reduce function as string
        :param finalize_func: (optional) JavaScript finalize function as string
        :param limit: (optional) Maximum number of entries to be processed
        :param scope: (optional) Variable scope to pass the functions (:class:`dict`)
        :param keeptemp: Whether to keep the temporarily created collection
                         (boolean, defaults to :const:`False`)
        """
        collection = self._get_collection()

        if not hasattr(collection, 'map_reduce'):
            raise NotImplementedError('map/reduce requires MongoDB >= 1.1.1')

        mapreduce_kwargs = {'keeptemp' : keeptemp}

        if finalize_func is not None:
            mapreduce_kwargs['finalize'] = finalize_func
        if limit is not None:
            mapreduce_kwargs['limit'] = limit
        if scope is not None:
            mapreduce_kwargs['scope'] = scope

        result_collection = collection.map_reduce(map_func, reduce_func, **mapreduce_kwargs)
        return [MapReduceResult(self.model, doc['_id'], doc['value'])
                for doc in result_collection.find()]

########NEW FILE########
__FILENAME__ = creation
from pymongo.collection import Collection
from djangotoolbox.db.base import NonrelDatabaseCreation

TEST_DATABASE_PREFIX = 'test_'

class DatabaseCreation(NonrelDatabaseCreation):
    """Database Creation class.
    """
    data_types = {
        'DateTimeField':                'datetime',
        'DateField':                    'date',
        'TimeField':                    'time',
        'FloatField':                   'float',
        'EmailField':                   'unicode',
        'URLField':                     'unicode',
        'BooleanField':                 'bool',
        'NullBooleanField':             'bool',
        'CharField':                    'unicode',
        'CommaSeparatedIntegerField':   'unicode',
        'IPAddressField':               'unicode',
        'SlugField':                    'unicode',
        'FileField':                    'unicode',
        'FilePathField':                'unicode',
        'TextField':                    'unicode',
        'XMLField':                     'unicode',
        'IntegerField':                 'int',
        'SmallIntegerField':            'int',
        'PositiveIntegerField':         'int',
        'PositiveSmallIntegerField':    'int',
        'BigIntegerField':              'int',
        'GenericAutoField':             'objectid',
        'StringForeignKey':             'objectid',
        'AutoField':                    'objectid',
        'RelatedAutoField':             'objectid',
        'OneToOneField':                'int',
        'DecimalField':                 'float',
    }

    def sql_indexes_for_field(self, model, field, **kwargs):
        """Create Indexes for field in model. Returns an empty List. (Django Compatibility)

        :param model: The model containing field
        :param f: The field to create indexes to.
        :param \*\*kwargs: Extra kwargs not used in this engine.
        """

        if field.db_index:
            kwargs = {}
            opts = model._meta
            col = getattr(self.connection.db_connection, opts.db_table)
            descending = getattr(opts, "descending_indexes", [])
            direction =  (field.attname in descending and -1) or 1
            kwargs["unique"] = field.unique
            col.ensure_index([(field.name, direction)], **kwargs)
        return []

    def index_fields_group(self, model, group, **kwargs):
        """Create indexes for fields in group that belong to model.
            This method is used to do compound indexes.

        :param model: The model containing the fields inside group.
        :param group: A ``dict`` containing the fields map to index.
        :param \*\*kwargs: Extra kwargs not used in this engine.


        Example

            >>> class TestFieldModel(Task):
            ...
            ...     class MongoMeta:
            ...         index_together = [{
            ...             'fields' : [ ('title', False), 'mlist']
            ...             }]
            ...
        """
        if not isinstance(group, dict):
            raise TypeError("Indexes group has to be instance of dict")

        fields = group.pop("fields")

        if not isinstance(fields, (list, tuple)):
            raise TypeError("index_together fields has to be instance of list")

        opts = model._meta
        col = getattr(self.connection.db_connection, opts.db_table)
        checked_fields = []
        model_fields = [ f.name for f in opts.local_fields]

        for field in fields:
            field_name = field
            direction = 1
            if isinstance(field, (tuple, list)):
                field_name = field[0]
                direction = (field[1] and 1) or -1
            if not field_name in model_fields:
                from django.db.models.fields import FieldDoesNotExist
                raise FieldDoesNotExist('%s has no field named %r' % (opts.object_name, field_name))
            checked_fields.append((field_name, direction))
        col.ensure_index(checked_fields, **group)

    def sql_indexes_for_model(self, model, *args, **kwargs):
        """Creates ``model`` indexes.

        :param model: The model containing the fields inside group.
        :param \*args: Extra args not used in this engine.
        :param \*\*kwargs: Extra kwargs not used in this engine.
        """
        if not model._meta.managed or model._meta.proxy:
            return []
        fields = [f for f in model._meta.local_fields if f.db_index]
        if not fields and not hasattr(model._meta, "index_together") and not hasattr(model._meta, "unique_together"):
            return []
        print "Installing index for %s.%s model" % (model._meta.app_label, model._meta.object_name)
        for field in fields:
            self.sql_indexes_for_field(model, field)
        for group in getattr(model._meta, "index_together", []):
            self.index_fields_group(model, group)

        #unique_together support
        unique_together = getattr(model._meta, "unique_together", [])
        # Django should do this, I just wanted to be REALLY sure.
        if len(unique_together) > 0 and isinstance(unique_together[0], basestring):
            unique_together = (unique_together,)
        for fields in unique_together:
            group = { "fields" : fields, "unique" : True}
            self.index_fields_group(model, group)
        return []

    def sql_create_model(self, model, *args, **kwargs):
        """Creates the collection for model. Mostly used for capped collections.

        :param model: The model that should be created.
        :param \*args: Extra args not used in this engine.
        :param \*\*kwargs: Extra kwargs not used in this engine.

        Example

            >>> class TestFieldModel(Task):
            ...
            ...     class MongoMeta:
            ...         capped = True
            ...         collection_max = 100000
            ...         collection_size = 10
        """
        opts = model._meta
        kwargs = {}
        kwargs["capped"] = getattr(opts, "capped", False)
        if hasattr(opts, "collection_max") and opts.collection_max:
            kwargs["max"] = opts.collection_max
        if hasattr(opts, "collection_size") and opts.collection_size:
            kwargs["size"] = opts.collection_size
        col = Collection(self.connection.db_connection, model._meta.db_table, **kwargs)
        return [], {}

    def set_autocommit(self):
        "Make sure a connection is in autocommit mode."
        pass

    def create_test_db(self, verbosity=1, autoclobber=False):
        # No need to create databases in mongoDB :)
        # but we can make sure that if the database existed is emptied
        if self.connection.settings_dict.get('TEST_NAME'):
            test_database_name = self.connection.settings_dict['TEST_NAME']
        elif 'NAME' in self.connection.settings_dict:
            test_database_name = TEST_DATABASE_PREFIX + self.connection.settings_dict['NAME']
        elif 'DATABASE_NAME' in self.connection.settings_dict:
            if self.connection.settings_dict['DATABASE_NAME'].startswith(TEST_DATABASE_PREFIX):
                # already been set up
                # must be because this is called from a setUp() instead of something formal.
                # suspect this Django 1.1
                test_database_name = self.connection.settings_dict['DATABASE_NAME']
            else:
                test_database_name = TEST_DATABASE_PREFIX + \
                  self.connection.settings_dict['DATABASE_NAME']
        else:
            raise ValueError("Name for test database not defined")

        self.connection.settings_dict['NAME'] = test_database_name
        # This is important. Here we change the settings so that all other code
        # things that the chosen database is now the test database. This means
        # that nothing needs to change in the test code for working with
        # connections, databases and collections. It will appear the same as
        # when working with non-test code.

        # In this phase it will only drop the database if it already existed
        # which could potentially happen if the test database was created but
        # was never dropped at the end of the tests
        self._drop_database(test_database_name)

    def destroy_test_db(self, old_database_name, verbosity=1):
        """
        Destroy a test database, prompting the user for confirmation if the
        database already exists. Returns the name of the test database created.
        """
        if verbosity >= 1:
            print "Destroying test database '%s'..." % self.connection.alias
        test_database_name = self.connection.settings_dict['NAME']
        self._drop_database(test_database_name)
        self.connection.settings_dict['NAME'] = old_database_name

    def _drop_database(self, database_name):
        """Drops the database with name database_name

        :param database_name: The name of the database to drop.
        """
        self.connection._cursor().drop_database(database_name)

########NEW FILE########
__FILENAME__ = fields
from django.db import models
from pymongo.objectid import ObjectId
from gridfs import GridFS
try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO

from djangotoolbox.fields import *

__all__ = ['GridFSField', 'EmbeddedModelField']

class LegacyEmbeddedModelField(EmbeddedModelField):
    """
    Wrapper around djangotoolbox' ``EmbeddedModelField` that keeps
    backwards compatibility with data generated by django-mongodb-engine < 0.3.
    """
    def to_python(self, values):
        if isinstance(values, dict):
            # In version 0.2, the layout of the serialized model instance changed.
            # Cleanup up old instances from keys that aren't used any more.
            for key in ('_app', '_model'):
                values.pop(key, None)

            # Up to version 0.2, '_id's were added automatically.
            # Keep backwards compatibility to old data records.
            if "_id" in values:
                values["id"] = values.pop("_id")
        return super(LegacyEmbeddedModelField, self).to_python(values)


class GridFSField(models.CharField):

    def __init__(self, *args, **kwargs):
        self._as_string = kwargs.pop("as_string", False)
        self._versioning = kwargs.pop("versioning", False)
        kwargs["max_length"] = 255
        super(GridFSField, self).__init__(*args, **kwargs)


    def contribute_to_class(self, cls, name):
        super(GridFSField, self).contribute_to_class(cls, name)

        att_oid_name = "_%s_oid" % name
        att_cache_name = "_%s_cache" % name
        att_val_name = "_%s_val" % name
        as_string = self._as_string

        def _get(self):
            from django.db import connections
            gdfs = GridFS(connections[self.__class__.objects.db].db_connection.db)
            if not hasattr(self, att_cache_name) and not getattr(self, att_val_name, None) and getattr(self, att_oid_name, None):
                val = gdfs.get(getattr(self, att_oid_name))
                if as_string:
                    val = val.read()
                setattr(self, att_cache_name, val)
                setattr(self, att_val_name, val)
            return getattr(self, att_val_name, None)

        def _set(self, val):
            if isinstance(val, ObjectId) and not hasattr(self, att_oid_name):
                setattr(self, att_oid_name, val)
            else:
                if isinstance(val, unicode):
                    val = val.encode('utf8', 'ignore')

                if isinstance(val, basestring) and not as_string:
                    val = StringIO(val)

                setattr(self, att_val_name, val)

        setattr(cls, self.attname, property(_get, _set))


    def db_type(self, connection):
        return "gridfs"

    def pre_save(self, model_instance, add):
        oid = getattr(model_instance, "_%s_oid" % self.attname, None)
        value = getattr(model_instance, "_%s_val" % self.attname, None)

        if not getattr(model_instance, "id"):
            return u''

        if value == getattr(model_instance, "_%s_cache" % self.attname, None):
            return oid

        from django.db import connections
        gdfs = GridFS(connections[self.model.objects.db].db_connection.db)


        if not self._versioning and not oid is None:
            gdfs.delete(oid)

        if not self._as_string:
            value.seek(0)
            value = value.read()

        oid = gdfs.put(value)
        setattr(self, "_%s_oid" % self.attname, oid)
        setattr(self, "_%s_cache" % self.attname, value)

        return oid

########NEW FILE########
__FILENAME__ = models

# If you wonder what this file is about please head over to '__init__.py' :-)

from django.db.models import signals

def class_prepared_mongodb_signal(sender, *args, **kwargs):
    mongo_meta = getattr(sender, 'MongoMeta', None)
    if mongo_meta is not None:
        for attr in dir(mongo_meta):
            if not attr.startswith('_'):
                setattr(sender._meta, attr, getattr(mongo_meta, attr))

signals.class_prepared.connect(class_prepared_mongodb_signal)

########NEW FILE########
__FILENAME__ = query
from djangotoolbox.fields import AbstractIterableField, EmbeddedModelField

class A(object):
    def __init__(self, op, value):
        self.op = op
        self.val = value

    def as_q(self, field):
        if isinstance(field, (AbstractIterableField, EmbeddedModelField)):
            return "%s.%s" % (field.attname, self.op), self.val
        else:
            raise TypeError("Can not use A() queries on %s" % field.__class__.__name__)

########NEW FILE########
__FILENAME__ = router
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

from django_mongodb_engine.utils import get_databases

def model_label(model):
    return '%s.%s' % (model._meta.app_label, model._meta.module_name)

class MongoDBRouter(object):
    """
    A router to control all database operations on models in the myapp application
    """
    def __init__(self):
        self.managed_apps = [app.split('.')[-1] for app in getattr(settings, 'MONGODB_MANAGED_APPS', [])]
        self.managed_models = getattr(settings, 'MONGODB_MANAGED_MODELS', [])
        self.mongodb_database, self.mongodb_databases = get_databases()

    def model_app_is_managed(self, model):
        return model._meta.app_label in self.managed_apps

    def model_is_managed(self, model):
        return model_label(model) in self.managed_models

    def is_managed(self, model):
        return self.model_app_is_managed(model) or self.model_is_managed(model)

    def db_for_read(self, model, **hints):
        """Point all operations on mongodb models to a mongodb database"""
        if self.is_managed(model):
            return self.mongodb_database

    db_for_write = db_for_read # same algorithm

    def allow_relation(self, obj1, obj2, **hints):
        """Allow any relation if a model in myapp is involved"""
        return self.is_managed(obj2) or None

    def allow_syncdb(self, db, model):
        """Make sure that a mongodb model appears on a mongodb database"""

        if db in self.mongodb_databases:
            return self.is_managed(model)
        elif self.is_managed(model):
            return db in self.mongodb_databases

        return None

    def valid_for_db_engine(self, driver, model):
        """Make sure that a model is valid for a database provider"""
        if driver != 'mongodb':
            return False
        return self.is_managed(model)

########NEW FILE########
__FILENAME__ = serializer
from django.db import models
from django.db.models.query import QuerySet
from django.utils.functional import SimpleLazyObject
from django.utils.importlib import import_module
from pymongo.son_manipulator import SONManipulator

def get_model_by_meta(model_meta):
    app, model = model_meta['_app'], model_meta['_model']
    try:
        module = import_module(app + '.models')
    except ImportError:
        return models.get_model(app, model)
    else:
        try:
            return getattr(module, model)
        except AttributeError:
            raise AttributeError("Could not find model %r in module %r" % (model, module))

class LazyModelInstance(SimpleLazyObject):
    """
    Lazy model instance.
    """
    def __init__(self, model, pk):
        self.__dict__['_pk'] = pk
        self.__dict__['_model'] = model
        super(LazyModelInstance, self).__init__(self._load_data)

    def _load_data(self):
        return self._model.objects.get(pk=self._pk)

    def __eq__(self, other):
        if isinstance(other, LazyModelInstance):
            return self.__dict__['_pk'] == other.__dict__['_pk'] and \
                   self.__dict__['_model'] == other.__dict__['_model']
        return super(LazyModelInstance, self).__eq__(other)


class TransformDjango(SONManipulator):
    def transform_incoming(self, value, collection):
        if isinstance(value, (list, tuple, set, QuerySet)):
            return [self.transform_incoming(item, collection) for item in value]

        if isinstance(value, dict):
            return dict((key, self.transform_incoming(subvalue, collection))
                        for key, subvalue in value.iteritems())

        if isinstance(value, models.Model):
            value.save()
            return {
                '_app' : value._meta.app_label,
                '_model' : value._meta.object_name,
                'pk' : value.pk,
                '_type' : 'django'
            }

        return value

    def transform_outgoing(self, son, collection):
        if isinstance(son, (list, tuple, set)):
            return [self.transform_outgoing(value, collection) for value in son]

        if isinstance(son, dict):
            if son.get('_type') == 'django':
                return LazyModelInstance(get_model_by_meta(son), son['pk'])
            else:
                return dict((key, self.transform_outgoing(value, collection))
                             for key, value in son.iteritems())
        return son

########NEW FILE########
__FILENAME__ = south
class DatabaseOperations(object):
    """
    MongoDB implementation of database operations.
    """

    backend_name = 'django_mongodb_engine'

    supports_foreign_keys = False
    has_check_constraints = False

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

########NEW FILE########
__FILENAME__ = utils
from django.conf import settings
from django.db import connections

def get_databases():
    default_database = None
    databases = []
    for name, databaseopt in settings.DATABASES.iteritems():
        if databaseopt['ENGINE'] == 'django_mongodb_engine':
            databases.append(name)
            if databaseopt.get('IS_DEFAULT'):
                if default_database is None:
                    default_database = name
                else:
                    raise ImproperlyConfigured("There can be only one default MongoDB database")

    if not databases:
        raise ImproperlyConfigured("No MongoDB database found in settings.DATABASES")

    if default_database is None:
        default_database = databases[0]

    return default_database, databases

def get_default_database():
    return get_databases()[0]

def get_default_db_connection():
    return connections[get_default_database()].db_connection
########NEW FILE########
__FILENAME__ = widgets
from django.conf import settings
from django.forms import widgets
from django.db import models

from django.utils.safestring import mark_safe

class DictWidget(widgets.Widget):
    def value_from_datadict(self, data, files, name):
        if data.has_key("%s_rows" % name):
            returnlist ={}
            rows= int( data["%s_rows" % name])
            while rows > 0:
                rows -= 1
                rowname = "%s_%d" % (name, rows )
                if data.has_key("%s_key" % rowname ) :
                    k = data["%s_key" % rowname]
                    if k != "":
                        v = None
                        if data.has_key("%s_value" % rowname ) :
                            v = data["%s_value"%rowname]
                        returnlist[k]=v
            rowname = "%s_new" % name
            if data.has_key("%s_key" % rowname ) :
                k = data["%s_key" % rowname]
                if k != "":
                    v = None
                    if data.has_key("%s_value" % rowname ) :
                        v = data["%s_value"%rowname]
                    returnlist[k]=v

            return returnlist
        else:
            return None

    def render(self, name, value, attrs=None):

        htmlval="<table><tr><td>#</td><td>Key</td><td>Value</td></tr>"

        linenum=0
        idname = attrs['id']
        if (value is not None) and (type(value).__name__=='dict') :
            for key, val in value.items():
                idname_row = "%s_%d" % ( idname, linenum )

                htmlval += '<tr><td><label for="%s_key">%d</label></td><td><input type="txt" id="%s_key" name="%s_%d_key" value="%s" /></td>' % (
                        idname_row, linenum ,idname_row, name,linenum, key )
                htmlval += '<td><input type="txt" id="%s_value" name="%s_%d_value" value="%s" /></td></tr>' % (
                        idname_row, name,linenum, val)
                linenum += 1
        idname_row = "%s_new" % ( idname )

        htmlval += '<tr><td><label for="%s_key">new</label></td><td><input type="txt" id="%s_key" name="%s_new_key" value="" /></td>' % (
                idname_row, idname_row, name)
        htmlval += '<td><input type="txt" id="%s_value" name="%s_new_value" value="" /></td></tr>' % (
                idname_row, name )

        htmlval += "</table>"
        htmlval += "<input type='hidden' name='%s_rows' value='%d'>" % ( name, linenum )
        return mark_safe(htmlval)

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-

import sys
import os

this = os.path.dirname(os.path.abspath(__file__))

# If your extensions are in another directory, add it here. If the directory
# is relative to the documentation root, use os.path.abspath to make it
# absolute, like shown here.
sys.path.append(os.path.join(os.pardir, "tests"))
sys.path.append(os.path.join(this, "_ext"))
import django_mongodb_engine

# General configuration
# ---------------------

extensions = ['sphinx.ext.autodoc',
              'sphinx.ext.coverage',
              #'sphinxcontrib.issuetracker',
              'sphinx.ext.todo',
              'sphinx.ext.intersphinx',
              'django_mongodb_engine_docs',
              ]

# Add any paths that contain templates here, relative to this directory.
# templates_path = ['.templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'django-mongodb-engine'
copyright = u'2009-2010: Flavio Percoco, Alberto Paro, Jonas Haag & contributors'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = ".".join(map(str, django_mongodb_engine.__version__[0:2]))
# The full version, including alpha/beta/rc tags.
release = '.'.join(map(str, django_mongodb_engine.__version__))

exclude_trees = ['.build']

# If true, '()' will be appended to :func: etc. cross-reference text.
add_function_parentheses = True

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = 'trac'

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['.static']

html_use_smartypants = True

# If false, no module index is generated.
html_use_modindex = True

# If false, no index is generated.
html_use_index = True

latex_documents = [
  ('index', 'django_mongodb_engine.tex', ur'django-mongodb-engine Documentation',
   ur'Flavio Percoco, Alberto Paro, Jonas Haag', 'manual'),
]

html_theme = 'nature'
html_theme_options = {'nosidebar' : 'true'}
# html_theme_path = ["_theme"]
# html_sidebars = {
#     'index': ['sidebarintro.html', 'sourcelink.html', 'searchbox.html'],
#     '**': ['sidebarlogo.html', 'relations.html',
#            'sourcelink.html', 'searchbox.html'],
# }

### Issuetracker

issuetracker = "github"
issuetracker_user = "django-mongodb-engine"
issuetracker_project = "mongodb-engine"
issuetracker_issue_pattern = r'[Ii]ssue #(\d+)'

intersphinx_mapping = {'python' : ('http://docs.python.org', None),
                       'django' : ('http://docs.djangoproject.com/en/dev/_objects/', None)}

########NEW FILE########
__FILENAME__ = applyxrefs
"""Adds xref targets to the top of files."""

import sys
import os

testing = False

DONT_TOUCH = (
        './index.txt',
        )


def target_name(fn):
    if fn.endswith('.txt'):
        fn = fn[:-4]
    return '_' + fn.lstrip('./').replace('/', '-')


def process_file(fn, lines):
    lines.insert(0, '\n')
    lines.insert(0, '.. %s:\n' % target_name(fn))
    try:
        f = open(fn, 'w')
    except IOError:
        print("Can't open %s for writing. Not touching it." % fn)
        return
    try:
        f.writelines(lines)
    except IOError:
        print("Can't write to %s. Not touching it." % fn)
    finally:
        f.close()


def has_target(fn):
    try:
        f = open(fn, 'r')
    except IOError:
        print("Can't open %s. Not touching it." % fn)
        return (True, None)
    readok = True
    try:
        lines = f.readlines()
    except IOError:
        print("Can't read %s. Not touching it." % fn)
        readok = False
    finally:
        f.close()
        if not readok:
            return (True, None)

    #print fn, len(lines)
    if len(lines) < 1:
        print("Not touching empty file %s." % fn)
        return (True, None)
    if lines[0].startswith('.. _'):
        return (True, None)
    return (False, lines)


def main(argv=None):
    if argv is None:
        argv = sys.argv

    if len(argv) == 1:
        argv.extend('.')

    files = []
    for root in argv[1:]:
        for (dirpath, dirnames, filenames) in os.walk(root):
            files.extend([(dirpath, f) for f in filenames])
    files.sort()
    files = [os.path.join(p, fn) for p, fn in files if fn.endswith('.txt')]
    #print files

    for fn in files:
        if fn in DONT_TOUCH:
            print("Skipping blacklisted file %s." % fn)
            continue

        target_found, lines = has_target(fn)
        if not target_found:
            if testing:
                print '%s: %s' % (fn, lines[0]),
            else:
                print "Adding xref to %s" % fn
                process_file(fn, lines)
        else:
            print "Skipping %s: already has a xref" % fn

if __name__ == '__main__':
    sys.exit(main())

########NEW FILE########
__FILENAME__ = django_mongodb_engine_docs
def setup(app):
    from docutils.parsers.rst.directives.admonitions import Note

    app.add_directive('forthelazy', Note) # for now

    app.add_crossref_type(
        directivename="setting",
        rolename="setting",
        indextemplate="pair: %s; setting",
    )
    app.add_crossref_type(
        directivename="sig",
        rolename="sig",
        indextemplate="pair: %s; sig",
    )
    app.add_crossref_type(
        directivename="state",
        rolename="state",
        indextemplate="pair: %s; state",
    )
    app.add_crossref_type(
        directivename="control",
        rolename="control",
        indextemplate="pair: %s; control",
    )

# the following code is stolen from github-tools (Damien Lebrun, BSD-style license)

    app.connect('html-page-context', change_pathto)
    app.connect('build-finished', move_private_folders)

import os
import shutil

def change_pathto(app, pagename, templatename, context, doctree):
    """
    Replace pathto helper to change paths to folders with a leading underscore.
    """
    pathto = context.get('pathto')
    def gh_pathto(otheruri, *args, **kw):
        if otheruri.startswith('_'):
            otheruri = otheruri[1:]
        return pathto(otheruri, *args, **kw)
    context['pathto'] = gh_pathto

def move_private_folders(app, e):
    """
    remove leading underscore from folders in in the output folder.

    :todo: should only affect html built
    """
    def join(dir):
        return os.path.join(app.builder.outdir, dir)

    for item in os.listdir(app.builder.outdir):
        if item.startswith('_') and os.path.isdir(join(item)):
            shutil.move(join(item), join(item[1:]))

########NEW FILE########
__FILENAME__ = literals_to_xrefs
"""
Runs through a reST file looking for old-style literals, and helps replace them
with new-style references.
"""

import re
import sys
import shelve

refre = re.compile(r'``([^`\s]+?)``')

ROLES = (
    'attr',
    'class',
    "djadmin",
    'data',
    'exc',
    'file',
    'func',
    'lookup',
    'meth',
    'mod',
    "djadminopt",
    "ref",
    "setting",
    "term",
    "tfilter",
    "ttag",

    # special
    "skip",
)

ALWAYS_SKIP = [
    "NULL",
    "True",
    "False",
]


def fixliterals(fname):
    data = open(fname).read()

    last = 0
    new = []
    storage = shelve.open("/tmp/literals_to_xref.shelve")
    lastvalues = storage.get("lastvalues", {})

    for m in refre.finditer(data):

        new.append(data[last:m.start()])
        last = m.end()

        line_start = data.rfind("\n", 0, m.start())
        line_end = data.find("\n", m.end())
        prev_start = data.rfind("\n", 0, line_start)
        next_end = data.find("\n", line_end + 1)

        # Skip always-skip stuff
        if m.group(1) in ALWAYS_SKIP:
            new.append(m.group(0))
            continue

        # skip when the next line is a title
        next_line = data[m.end():next_end].strip()
        if next_line[0] in "!-/:-@[-`{-~" and \
                all(c == next_line[0] for c in next_line):
            new.append(m.group(0))
            continue

        sys.stdout.write("\n" + "-" * 80 + "\n")
        sys.stdout.write(data[prev_start + 1:m.start()])
        sys.stdout.write(colorize(m.group(0), fg="red"))
        sys.stdout.write(data[m.end():next_end])
        sys.stdout.write("\n\n")

        replace_type = None
        while replace_type is None:
            replace_type = raw_input(
                colorize("Replace role: ", fg="yellow")).strip().lower()
            if replace_type and replace_type not in ROLES:
                replace_type = None

        if replace_type == "":
            new.append(m.group(0))
            continue

        if replace_type == "skip":
            new.append(m.group(0))
            ALWAYS_SKIP.append(m.group(1))
            continue

        default = lastvalues.get(m.group(1), m.group(1))
        if default.endswith("()") and \
                replace_type in ("class", "func", "meth"):
            default = default[:-2]
        replace_value = raw_input(
            colorize("Text <target> [", fg="yellow") + default + \
                    colorize("]: ", fg="yellow")).strip()
        if not replace_value:
            replace_value = default
        new.append(":%s:`%s`" % (replace_type, replace_value))
        lastvalues[m.group(1)] = replace_value

    new.append(data[last:])
    open(fname, "w").write("".join(new))

    storage["lastvalues"] = lastvalues
    storage.close()


def colorize(text='', opts=(), **kwargs):
    """
    Returns your text, enclosed in ANSI graphics codes.

    Depends on the keyword arguments 'fg' and 'bg', and the contents of
    the opts tuple/list.

    Returns the RESET code if no parameters are given.

    Valid colors:
        'black', 'red', 'green', 'yellow', 'blue', 'magenta', 'cyan', 'white'

    Valid options:
        'bold'
        'underscore'
        'blink'
        'reverse'
        'conceal'
        'noreset' - string will not be auto-terminated with the RESET code

    Examples:
        colorize('hello', fg='red', bg='blue', opts=('blink',))
        colorize()
        colorize('goodbye', opts=('underscore',))
        print colorize('first line', fg='red', opts=('noreset',))
        print 'this should be red too'
        print colorize('and so should this')
        print 'this should not be red'
    """
    color_names = ('black', 'red', 'green', 'yellow',
                   'blue', 'magenta', 'cyan', 'white')
    foreground = dict([(color_names[x], '3%s' % x) for x in range(8)])
    background = dict([(color_names[x], '4%s' % x) for x in range(8)])

    RESET = '0'
    opt_dict = {'bold': '1',
                'underscore': '4',
                'blink': '5',
                'reverse': '7',
                'conceal': '8'}

    text = str(text)
    code_list = []
    if text == '' and len(opts) == 1 and opts[0] == 'reset':
        return '\x1b[%sm' % RESET
    for k, v in kwargs.iteritems():
        if k == 'fg':
            code_list.append(foreground[v])
        elif k == 'bg':
            code_list.append(background[v])
    for o in opts:
        if o in opt_dict:
            code_list.append(opt_dict[o])
    if 'noreset' not in opts:
        text = text + '\x1b[%sm' % RESET
    return ('\x1b[%sm' % ';'.join(code_list)) + text

if __name__ == '__main__':
    try:
        fixliterals(sys.argv[1])
    except (KeyboardInterrupt, SystemExit):
        print

########NEW FILE########
__FILENAME__ = models
from django.db import models

class Person(models.Model):
    age = models.IntegerField()
    birthday = models.DateTimeField()

########NEW FILE########
__FILENAME__ = tests
from django.test import TestCase
from datetime import datetime
from models import Person

class SimpleTest(TestCase):
    def test_aggregations(self):
        for age, birthday in (
            [4,  (2007, 12, 25)],
            [4,  (2006, 1, 1)],
            [1,  (2008, 12, 1)],
            [4,  (2006, 6, 1)],
            [12, (1998, 9, 1)]
        ):
            Person.objects.create(age=age, birthday=datetime(*birthday))

        from django.db.models.aggregates import Count, Sum
        from django_mongodb_engine.contrib.aggregations import Max, Min, Avg

        aggregates = Person.objects.aggregate(Min("age"), Max("age"), Avg("age"))
        self.assertEqual(aggregates, {'age__min': 1, 'age__avg': 5.0, 'age__max': 12})

        #with filters and testing the sqlaggregates->mongoaggregate conversion
        aggregates = Person.objects.filter(age__gte=4).aggregate(Min("birthday"), Max("birthday"), Avg("age"), Count("id"))
        self.assertEqual(aggregates, {'birthday__max': datetime(2007, 12, 25, 0, 0),
                                      'birthday__min': datetime(1998, 9, 1, 0, 0),
                                      'age__avg': 6.0,
                                      'id__count': 4})

        self.assertRaises(NotImplementedError, Person.objects.aggregate, Sum('age'))

########NEW FILE########
__FILENAME__ = views
# Create your views here.

########NEW FILE########
__FILENAME__ = models
from django.db import models
from django_mongodb_engine.contrib import MongoDBManager

class MapReduceModel(models.Model):
    n = models.IntegerField()
    m = models.IntegerField()

    objects = MongoDBManager()

class MapReduceModelWithCustomPrimaryKey(models.Model):
    primarykey = models.CharField(max_length=100, primary_key=True)
    data = models.CharField(max_length=100)
    objects = MongoDBManager()

########NEW FILE########
__FILENAME__ = tests
from django.test import TestCase
from .models import *
from django_mongodb_engine.contrib.mapreduce import MapReduceResult

class SimpleTest(TestCase):
    #def test_mixin(self):
    #    self.assert_(MapReduceModel.mongodb.model is not None)
    #    self.assertNotEqual(MapReduceModel._default_manager,
    #                        MapReduceModel.mongodb)

    def test_map_reduce(self):
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

        finalizefunc = """ function(key, value) { return value * 2 } """

        random_numbers = [
            (3, 4),
            (6, 19),
            (5, 8),
            (0, 20), # this instance won't be emitted by `map`
            (300, 10),
            (2, 77)
        ]

        for n, m in random_numbers:
            MapReduceModel(n=n, m=m).save()

        # Test mapfunc + reducefunc
        documents = list(MapReduceModel.objects.map_reduce(mapfunc, reducefunc))
        self.assertEqual(len(documents), len(random_numbers)-1)
        self.assertEqual(sum(doc.value for doc in documents),
                         sum(n*m for n, m in random_numbers))

        obj = documents[0].get_object()
        self.assert_(isinstance(obj, MapReduceModel))
        self.assertEqual((obj.n, obj.m), random_numbers[0])
        self.assert_(obj.id)

        # Test finalizefunc and limit
        documents = list(MapReduceModel.objects.map_reduce(
                            mapfunc, reducefunc, finalizefunc, limit=3))
        self.assertEqual(len(documents), 3)
        self.assertEqual(sum(doc.value for doc in documents),
                         sum((n*m)*2 for n, m in random_numbers[:3]))

        # Test scope
        mapfunc = """
            function() { emit(this._id, this.n * x) } """
        reducefunc = """
            function(key, values) { return values[0] * y } """
        scope = {'x' : 5, 'y' : 10}
        documents = list(MapReduceModel.objects.map_reduce(mapfunc, reducefunc,
                                                           scope=scope))
        self.assertEqual([document.value for document in documents],
                         [(n*scope['x']) * scope['y'] for n, m in random_numbers])

    def test_map_reduce_with_custom_primary_key(self):
        mapfunc = """ function() { emit(this._id, null) } """
        reducefunc = """ function(key, values) { return null } """
        for pk, data in [
            ('foo', 'hello!'),
            ('bar', 'yo?'),
            ('blurg', 'wuzzup')
        ]:
            MapReduceModelWithCustomPrimaryKey(primarykey=pk, data=data).save()

        documents = MapReduceModelWithCustomPrimaryKey.objects.map_reduce(
            mapfunc, reducefunc)
        somedoc = documents[0]
        self.assertEqual(somedoc.key, 'bar') # ordered by pk
        self.assertEqual(somedoc.value, None)
        obj = somedoc.get_object()
        self.assert_(not hasattr(obj, 'id') and not hasattr(obj, '_id'))
        self.assertEqual(obj, MapReduceModelWithCustomPrimaryKey(pk='bar', data='yo?'))

    def test_raw_query(self):
        for i in xrange(10):
            MapReduceModel.objects.create(n=i, m=i*2)

        self.assertEqual(
            list(MapReduceModel.objects.filter(n__gt=5)),
            list(MapReduceModel.objects.raw_query({'n' : {'$gt' : 5}}))
        )

        self.assertRaises(TypeError,
            lambda: len(MapReduceModel.objects.raw_query().filter(n__gt=5))
        )

        from django.db.models import Q
        MapReduceModel.objects.raw_update(Q(n__lte=3), {'$set' : {'n' : -1}})
        self.assertEqual([o.n for o in MapReduceModel.objects.all()],
                         [-1, -1, -1, -1, 4, 5, 6, 7, 8, 9])
        MapReduceModel.objects.raw_update({'n' : -1}, {'$inc' : {'n' : 2}})
        self.assertEqual([o.n for o in MapReduceModel.objects.all()],
                         [1, 1, 1, 1, 4, 5, 6, 7, 8, 9])

########NEW FILE########
__FILENAME__ = views
# Create your views here.

########NEW FILE########
__FILENAME__ = models
from django.db import models
from djangotoolbox.fields import DictField, EmbeddedModelField
from django_mongodb_engine.fields import LegacyEmbeddedModelField

class EmbeddedModel(models.Model):
    charfield = models.CharField(max_length=3, blank=False)
    datetime = models.DateTimeField(null=True)
    datetime_auto_now_add = models.DateTimeField(auto_now_add=True)
    datetime_auto_now = models.DateTimeField(auto_now=True)

class Model(models.Model):
    x = models.IntegerField()
    em = EmbeddedModelField(EmbeddedModel)
    dict_emb = DictField(EmbeddedModelField(EmbeddedModel))

class LegacyModel(models.Model):
    legacy = LegacyEmbeddedModelField(EmbeddedModel)

# docstring example copy
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
from django.test import TestCase
from django.db.utils import DatabaseError
from .models import *
from datetime import datetime
import time
from django_mongodb_engine.query import A

class EmbeddedModelFieldTestCase(TestCase):
    def test_field_docstring(self):
        # This is a 1:1 copy of EmbeddedModelField's doctest
        bob = Customer(
            name='Bob', last_name='Laxley',
            address=Address(street='Behind the Mountains 23',
                            postal_code=1337, city='Blurginson')
        )
        self.assertEqual(bob.address.postal_code, 1337)
        bob.save()
        bob_from_db = Customer.objects.get(name='Bob')
        self.assertEqual(bob.address.city, 'Blurginson')

    def test_empty(self):
        obj = Model(x=5)
        self.assertRaises(DatabaseError, obj.save)

    def test_empty_embedded(self):
        obj = Model(x=5)
        self.assertRaises(DatabaseError, obj.save)

    def test_simple(self):
        obj = Model(x=5, em=EmbeddedModel(charfield='foo'))
        assert obj.em
        obj.save()
        obj = Model.objects.get()
        self.assertTrue(isinstance(obj.em, EmbeddedModel))
        self.assertEqual(obj.em.charfield, 'foo')
        self.assertNotEqual(obj.em.datetime_auto_now, None)
        self.assertNotEqual(obj.em.datetime_auto_now_add, None)
        obj.save()
        auto_now_before = obj.em.datetime_auto_now
        obj = Model.objects.get()
        self.assertNotEqual(obj.em.datetime_auto_now,
                            auto_now_before)

    def test_in_dictfield(self):
        foodate = datetime(year=2003, month=9, day=23)
        obj = Model(
            x=5,
            em=EmbeddedModel(charfield='hello', datetime=foodate),
            dict_emb={'blah' : EmbeddedModel(charfield='blurg')}
        )
        obj.dict_emb['lala'] = EmbeddedModel(charfield='blubb',
                                             datetime=foodate)
        obj.save()
        obj = Model.objects.get()
        self.assertEqual(obj.em.datetime, foodate)
        self.assertEqual(obj.dict_emb['blah'].charfield, 'blurg')
        self.assertEqual(obj.dict_emb['lala'].datetime, foodate)
        obj.dict_emb['blah'].charfield = "Some Change"
        obj.dict_emb['foo'] = EmbeddedModel(charfield='bar')
        obj.save()
        obj = Model.objects.get()
        obj.save()
        self.assertEqual(obj.dict_emb['blah'].charfield, 'Some Change')
        self.assertNotEqual(obj.dict_emb['blah'].datetime_auto_now_add, obj.dict_emb['blah'].datetime_auto_now)
        self.assertEqual(obj.dict_emb['foo'].charfield, 'bar')

    def test_legacy_field(self):
        # LegacyLegacyModelField should behave like EmbeddedLegacyModelField for
        # "new-style" data sets
        LegacyModel.objects.create(legacy=EmbeddedModel(charfield='blah'))
        self.assertEqual(LegacyModel.objects.get().legacy.charfield, u'blah')

        # LegacyLegacyModelField should keep the embedded model's 'id' if the data
        # set contains it. To add one, we have to do a manual update here:
        from utils import get_pymongo_collection
        collection = get_pymongo_collection('embedded_legacymodel')
        collection.update({}, {'$set' : {'legacy._id' : 42}}, safe=True)
        self.assertEqual(LegacyModel.objects.get().legacy.id, 42)

        # If the data record contains '_app' or '_model', they should be
        # stripped out so the resulting model instance is not populated with them.
        collection.update({}, {'$set' : {'legacy._model' : 'a', 'legacy._app' : 'b'}}, safe=True)
        self.assertFalse(hasattr(LegacyModel.objects.get().legacy, '_model'))
        self.assertFalse(hasattr(LegacyModel.objects.get().legacy, '_app'))

    def test_query_embedded(self):
        Model(x=3, em=EmbeddedModel(charfield='foo')).save()
        obj = Model(x=3, em=EmbeddedModel(charfield='blurg'))
        obj.save()
        Model(x=3, em=EmbeddedModel(charfield='bar')).save()
        obj_from_db = Model.objects.get(em=A('charfield', 'blurg'))
        self.assertEqual(obj, obj_from_db)

########NEW FILE########
__FILENAME__ = utils
from pymongo import Connection
from django.conf import settings

def get_pymongo_collection(collection):
    # TODO: How do I find out which host/port/name the test DB has?
    connection = Connection(settings.DATABASES['default']['HOST'],
                            int(settings.DATABASES['default']['PORT']))
    database = connection['test_test']
    return database[collection]


########NEW FILE########
__FILENAME__ = views
# Create your views here.

########NEW FILE########
__FILENAME__ = models
from django.db import models
from django.conf import settings
from django.utils.translation import ugettext_lazy as _
from djangotoolbox.fields import ListField, DictField, SetField, RawField

class Blog(models.Model):
    title = models.CharField(max_length=200, db_index=True)

    def __unicode__(self):
        return "Blog: %s" % self.title

class Simple(models.Model):
    a = models.IntegerField()

class Entry(models.Model):
    title = models.CharField(max_length=200, db_index=True, unique=True)
    content = models.CharField(max_length=1000)
    date_published = models.DateTimeField(null=True, blank=True)
    blog = models.ForeignKey(Blog, null=True, blank=True)

    class MongoMeta:
        descending_indexes = ['title']

    def __unicode__(self):
        return "Entry: %s" % (self.title)

class Person(models.Model):
    name = models.CharField(max_length=20)
    surname = models.CharField(max_length=20)
    age = models.IntegerField(null=True, blank=True)

    class Meta:
        unique_together = ("name", "surname")

    def __unicode__(self):
        return u"Person: %s %s" % (self.name, self.surname)

class StandardAutoFieldModel(models.Model):
    title = models.CharField(max_length=200)

    def __unicode__(self):
        return "Standard model: %s" % (self.title)

class DateModel(models.Model):
    datetime = models.DateTimeField(auto_now_add=True)
    time = models.TimeField(null=True)
    date = models.DateField(null=True)
    if not settings.USE_SQLITE:
        _datelist_default = []
        datelist = ListField(models.DateField(), default=_datelist_default)

class DynamicModel(models.Model):
    gen = RawField()

    def __unicode__(self):
        return "Test special field model: %s" % (self.gen)

if not settings.USE_SQLITE:
    class TestFieldModel(models.Model):
        title = models.CharField(max_length=200)
        mlist = ListField()
        mlist_default = ListField(default=["a", "b"])
        slist = ListField(ordering=lambda x:x)
        slist_default = ListField(default=["b", "a"], ordering=lambda x:x)
        mdict = DictField()
        mdict_default = DictField(default={"a": "a", 'b':1})
        mset = SetField()
        mset_default = SetField(default=set(["a", 'b']))

        class MongoMeta:
            index_together = [{
                                'fields' : [ ('title', False), 'mlist']
                                }]
        def __unicode__(self):
            return "Test special field model: %s" % (self.title)

else:
    class TestFieldModel(models.Model):
        pass

########NEW FILE########
__FILENAME__ = tests
"""
Test suite for django-mongodb-engine.
"""
import datetime
from django.test import TestCase
from django.db.models import F, Q
from django.db.utils import DatabaseError

from pymongo.objectid import ObjectId
from django_mongodb_engine.serializer import LazyModelInstance

from models import *


def skip_all_except(*tests):
    class meta(type):
        def __new__(cls, name, bases, dict):
            for attr in dict.keys():
                if attr.startswith('test_') and attr not in tests:
                    del dict[attr]
            return type.__new__(cls, name, bases, dict)
    return meta

class MongoDjTest(TestCase):
    multi_db = True

    def assertEqualQueryset(self, a, b):
        self.assertEqual(list(a), list(b))

    def test_mongometa(self):
        self.assertEqual(Entry._meta.descending_indexes, ['title'])

    def test_add_and_delete_blog(self):
        blog1 = Blog(title="blog1")
        blog1.save()
        self.assertEqual(Blog.objects.count(), 1)
        blog2 = Blog(title="blog2")
        self.assertEqual(blog2.pk, None)
        blog2.save()
        self.assertNotEqual(blog2.pk, None)
        self.assertEqual(Blog.objects.count(), 2)
        blog2.delete()
        self.assertEqual(Blog.objects.count(), 1)
        blog1.delete()
        self.assertEqual(Blog.objects.count(), 0)

    def test_simple_get(self):
        blog1 = Blog(title="blog1")
        blog1.save()
        blog2 = Blog(title="blog2")
        blog2.save()
        self.assertEqual(Blog.objects.count(), 2)
        self.assertEqual(
            Blog.objects.filter(title="blog2").filter(title="blog2")[0],
            blog2
        )
        self.assertEqual(
            Blog.objects.get(title="blog1"),
            blog1
        )

    def test_simple_filter(self):
        blog1 = Blog(title="same title")
        blog1.save()
        blog2 = Blog(title="same title")
        blog2.save()
        blog3 = Blog(title="another title")
        blog3.save()
        self.assertEqual(Blog.objects.count(), 3)
        self.assertEqual(Blog.objects.get(pk=blog1.pk), blog1)
        self.assertEqual(
            Blog.objects.filter(title="same title").count(),
            2
        )
        self.assertEqual(
            Blog.objects.filter(title="same title").filter(pk=blog1.pk).count(),
            1
        )
        self.assertEqual(
            Blog.objects.filter(title__startswith="same").count(),
            2
        )
        self.assertEqual(
            Blog.objects.filter(title__istartswith="SAME").count(),
            2
        )
        self.assertEqual(
            Blog.objects.filter(title__endswith="title").count(),
            3
        )
        self.assertEqual(
            Blog.objects.filter(title__iendswith="Title").count(),
            3
        )
        self.assertEqual(
            Blog.objects.filter(title__icontains="same").count(),
            2
        )
        self.assertEqual(
            Blog.objects.filter(title__contains="same").count(),
            2
        )
        self.assertEqual(
            Blog.objects.filter(title__iexact="same Title").count(),
            2
        )

        self.assertEqual(
            Blog.objects.filter(title__regex="s.me.*").count(),
            2
        )
        self.assertEqual(
            Blog.objects.filter(title__iregex="S.me.*").count(),
            2
        )

    def test_change_model(self):
        blog1 = Blog(title="blog 1")
        blog1.save()
        self.assertEqual(Blog.objects.count(), 1)
        blog1.title = "new title"
        blog1.save()
        self.assertEqual(Blog.objects.count(), 1)
        self.assertEqual(blog1.title, Blog.objects.all()[0].title)

    def test_dates_ordering(self):
        now = datetime.datetime.now()
        before = now - datetime.timedelta(days=1)

        entry1 = Entry(title="entry 1", date_published=now)
        entry1.save()

        entry2 = Entry(title="entry 2", date_published=before)
        entry2.save()

        self.assertEqual(
            list(Entry.objects.order_by('-date_published')),
            [entry1, entry2]
        )

        self.assertEqual(
            list(Entry.objects.order_by('date_published')),
            [entry2, entry1]
        )

    def test_skip_limit(self):
        now = datetime.datetime.now()
        before = now - datetime.timedelta(days=1)

        Entry(title="entry 1", date_published=now).save()
        Entry(title="entry 2", date_published=before).save()
        Entry(title="entry 3", date_published=before).save()

        self.assertEqual(
            len(Entry.objects.order_by('-date_published')[:2]),
            2
        )

        # With step
        self.assertEqual(
            len(Entry.objects.order_by('date_published')[1:2:1]),
            1
        )

        self.assertEqual(
            len(Entry.objects.order_by('date_published')[1:2]),
            1
        )

    def test_values_query(self):
        blog = Blog.objects.create(title='fooblog')
        entry = Entry.objects.create(blog=blog, title='footitle', content='foocontent')
        entry2 = Entry.objects.create(blog=blog, title='footitle2', content='foocontent2')
        self.assertEqual(
            list(Entry.objects.values()),
            [{'blog_id' : blog.id, 'title' : u'footitle', 'id' : entry.id,
              'content' : u'foocontent', 'date_published' : None},
             {'blog_id' : blog.id, 'title' : u'footitle2', 'id' : entry2.id,
              'content' : u'foocontent2', 'date_published' : None}
            ]
        )
        self.assertEqual(
            list(Entry.objects.values('blog')),
            [{'blog' : blog.id}, {'blog' : blog.id}]
        )
        self.assertEqual(
            list(Entry.objects.values_list('blog_id', 'date_published')),
            [(blog.id, None), (blog.id, None)]
        )
        self.assertEqual(
            list(Entry.objects.values('title', 'content')),
            [{'title' : u'footitle', 'content' : u'foocontent'},
             {'title' : u'footitle2', 'content' : u'foocontent2'}]
        )

    def test_dates_less_and_more_than(self):
        now = datetime.datetime.now()
        before = now + datetime.timedelta(days=1)
        after = now - datetime.timedelta(days=1)

        entry1 = Entry(title="entry 1", date_published=now)
        entry1.save()

        entry2 = Entry(title="entry 2", date_published=before)
        entry2.save()

        entry3 = Entry(title="entry 3", date_published=after)
        entry3.save()

        a = list(Entry.objects.filter(date_published=now))
        self.assertEqual(
            list(Entry.objects.filter(date_published=now)),
            [entry1]
        )
        self.assertEqual(
            list(Entry.objects.filter(date_published__lt=now)),
            [entry3]
        )
        self.assertEqual(
            list(Entry.objects.filter(date_published__gt=now)),
            [entry2]
        )
    def test_complex_queries(self):
        p1 = Person(name="igor", surname="duck", age=39)
        p1.save()
        p2 = Person(name="andrea", surname="duck", age=29)
        p2.save()
        self.assertEqual(
            Person.objects.filter(name="igor", surname="duck").count(),
            1
        )
        self.assertEqual(
            Person.objects.filter(age__gte=20, surname="duck").count(),
            2
        )

    def test_fields(self):
        t1 = TestFieldModel(title="p1",
                            mlist=["ab", {'a':23, "b":True  }],
                            slist=["bc", "ab"],
                            mdict = {'a':23, "b":True  },
                            mset=["a", 'b', "b"]
                            )
        t1.save()

        t = TestFieldModel.objects.get(id=t1.id)
        self.assertEqual(t.mlist, ["ab", {'a':23, "b":True  }])
        self.assertEqual(t.mlist_default, ["a", "b"])
        self.assertEqual(t.slist, ["ab", "bc"])
        self.assertEqual(t.slist_default, ["a", "b"])
        self.assertEqual(t.mdict, {'a':23, "b":True  })
        self.assertEqual(t.mdict_default, {"a": "a", 'b':1})
        self.assertEqual(sorted(t.mset), ["a", 'b'])
        self.assertEqual(sorted(t.mset_default), ["a", 'b'])

        from django_mongodb_engine.query import A
        t2 = TestFieldModel.objects.get(mlist=A("a", 23))
        self.assertEqual(t1.pk, t2.pk)

    def test_simple_foreign_keys(self):
        blog1 = Blog(title="Blog")
        blog1.save()
        entry1 = Entry(title="entry 1", blog=blog1)
        entry1.save()
        entry2 = Entry(title="entry 2", blog=blog1)
        entry2.save()
        self.assertEqual(Entry.objects.count(), 2)

        for entry in Entry.objects.all():
            self.assertEqual(
                blog1,
                entry.blog
            )

        blog2 = Blog(title="Blog")
        blog2.save()
        entry3 = Entry(title="entry 3", blog=blog2)
        entry3.save()
        self.assertEqual(
            # it's' necessary to explicitly state the pk here
            list(Entry.objects.filter(blog=blog1.pk)),
            [entry1, entry2]
        )


    def test_foreign_keys_bug(self):
        blog1 = Blog(title="Blog")
        blog1.save()
        entry1 = Entry(title="entry 1", blog=blog1)
        entry1.save()
        self.assertEqual(
            # this should work too
            list(Entry.objects.filter(blog=blog1)),
            [entry1]
        )

    def test_standard_autofield(self):

        sam1 = StandardAutoFieldModel(title="title 1")
        sam1.save()
        sam2 = StandardAutoFieldModel(title="title 2")
        sam2.save()

        self.assertEqual(
            StandardAutoFieldModel.objects.count(),
            2
        )

        sam1_query = StandardAutoFieldModel.objects.get(title="title 1")
        self.assertEqual(
            sam1_query.pk,
            sam1.pk
        )

        sam1_query = StandardAutoFieldModel.objects.get(pk=sam1.pk)


    def test_generic_field(self):

        dyn = DynamicModel(gen=u"title 1")
        dyn.save()

        dyn = DynamicModel.objects.get(gen=u"title 1")


        self.assertTrue(isinstance(
            dyn.gen,
            unicode
        ))

        dyn.gen = 1
        dyn.save()
        dyn = DynamicModel.objects.get(gen=1)

        self.assertTrue(isinstance(
            dyn.gen,
            int
        ))

        dyn.gen = { "type" : "This is a dict"}
        dyn.save()
        dyn = DynamicModel.objects.get(gen={ "type" : "This is a dict"})

        self.assertTrue(isinstance(
            dyn.gen,
            dict
        ))


    def test_update(self):
        blog1 = Blog(title="Blog")
        blog1.save()
        blog2 = Blog(title="Blog 2")
        blog2.save()
        entry1 = Entry(title="entry 1", blog=blog1)
        entry1.save()

        Entry.objects.filter(pk=entry1.pk).update(blog=blog2)

        self.assertEqual(
            # this should work too
            list(Entry.objects.filter(blog=blog2)),
            [entry1]
        )


        Entry.objects.filter(blog=blog2).update(title="Title has been updated")

        self.assertEqual(
            # this should work too
            Entry.objects.filter()[0].title,
            "Title has been updated"
        )

        Entry.objects.filter(blog=blog2).update(title="Last Update Test", blog=blog1)

        self.assertEqual(
            # this should work too
            Entry.objects.filter()[0].title,
            "Last Update Test"
        )

        self.assertEqual(
            # this should work too
            Entry.objects.filter(blog=blog1).count(),
            1
        )

        self.assertEqual(Blog.objects.filter(title='Blog').count(), 1)
        Blog.objects.update(title='Blog')
        self.assertEqual(Blog.objects.filter(title='Blog').count(), 2)

    def test_update_id(self):
        Entry.objects.filter(title='Last Update Test').update(id=ObjectId())

    def test_update_with_F(self):
        john = Person.objects.create(name='john', surname='nhoj', age=42)
        andy = Person.objects.create(name='andy', surname='ydna', age=-5)
        Person.objects.update(age=F('age')+7)
        self.assertEqual(Person.objects.get(pk=john.id).age, 49)
        self.assertEqual(Person.objects.get(id=andy.pk).age, 2)

    def test_lazy_model_instance(self):
        l1 = LazyModelInstance(Entry, 'some-pk')
        l2 = LazyModelInstance(Entry, 'some-pk')

        self.assertEqual(l1, l2)

        obj = Entry(title='foobar')
        obj.save()

        l3 = LazyModelInstance(Entry, obj.id)
        self.assertEqual(l3._wrapped, None)
        self.assertEqual(obj, l3)
        self.assertNotEqual(l3._wrapped, None)

    def test_lazy_model_instance_in_list(self):
        from django.conf import settings
        obj = TestFieldModel()
        related = DynamicModel(gen=42)
        obj.mlist.append(related)
        if settings.MONGODB_AUTOMATIC_REFERENCING:
            obj.save()
            self.assertNotEqual(related.id, None)
            obj = TestFieldModel.objects.get()
            self.assertEqual(obj.mlist[0]._wrapped, None)
            # query will be done NOW:
            self.assertEqual(obj.mlist[0].gen, 42)
            self.assertNotEqual(obj.mlist[0]._wrapped, None)
        else:
            from bson.errors import InvalidDocument
            self.assertRaises(InvalidDocument, obj.save)

    def test_regex_matchers(self):
        objs = [Blog.objects.create(title=title) for title in
                ('Hello', 'worLd', '[(', '**', '\\')]
        self.assertEqual(list(Blog.objects.filter(title__startswith='h')), [])
        self.assertEqual(list(Blog.objects.filter(title__istartswith='h')), [objs[0]])
        self.assertEqual(list(Blog.objects.filter(title__contains='(')), [objs[2]])
        self.assertEqual(list(Blog.objects.filter(title__endswith='\\')), [objs[4]])

    def test_multiple_regex_matchers(self):
        objs = [Person.objects.create(name=a, surname=b) for a, b in
                (name.split() for name in ['donald duck', 'dagobert duck', 'daisy duck'])]

        filters = dict(surname__startswith='duck', surname__istartswith='duck',
                       surname__endswith='duck', surname__iendswith='duck',
                       surname__contains='duck', surname__icontains='duck')
        base_query = Person.objects \
                        .filter(**filters) \
                        .filter(~Q(surname__contains='just-some-random-condition',
                                   surname__endswith='hello world'))
        #base_query = base_query | base_query

        self.assertEqual(base_query.filter(name__iendswith='d')[0], objs[0])
        self.assertEqual(base_query.filter(name='daisy').get(), objs[2])

    def test_multiple_filter_on_same_name(self):
        Blog.objects.create(title='a')
        self.assertEqual(
            Blog.objects.filter(title='a').filter(title='a').filter(title='a').get(),
            Blog.objects.get()
        )
        self.assertEqual([], list(Blog.objects.filter(title='a')
                                              .filter(title='b')
                                              .filter(title='a')))

    def test_negated_Q(self):
        blogs = [Blog.objects.create(title=title) for title in
                 ('blog', 'other blog', 'another blog')]
        self.assertEqual(
            list(Blog.objects.filter(title='blog')
                 | Blog.objects.filter(~Q(title='another blog'))),
            [blogs[0], blogs[1]]
        )
        self.assertRaises(
            DatabaseError,
            lambda: Blog.objects.filter(~Q(title='blog') & ~Q(title='other blog')).get()
        )
        self.assertEqual(
            list(Blog.objects.filter(~Q(title='another blog')
                                     | ~Q(title='blog')
                                     | ~Q(title='aaaaa')
                                     | ~Q(title='fooo')
                                     | Q(title__in=[b.title for b in blogs]))),
            blogs
        )
        self.assertEqual(
            Blog.objects.filter(Q(title__in=['blog', 'other blog']),
                                ~Q(title__in=['blog'])).get(),
            blogs[1]
        )
        self.assertEqual(
            Blog.objects.filter().exclude(~Q(title='blog')).get(),
            blogs[0]
        )

    def test_simple_or_queries(self):
        obj1 = Simple.objects.create(a=1)
        obj2 = Simple.objects.create(a=1)
        obj3 = Simple.objects.create(a=2)
        obj4 = Simple.objects.create(a=3)

        self.assertEqualQueryset(
            Simple.objects.filter(a=1),
            [obj1, obj2]
        )
        self.assertEqualQueryset(
            Simple.objects.filter(a=1) | Simple.objects.filter(a=2),
            [obj1, obj2, obj3]
        )
        self.assertEqualQueryset(
            Simple.objects.filter(Q(a=2) | Q(a=3)),
            [obj3, obj4]
        )

        self.assertEqualQueryset(
            Simple.objects.filter(Q(Q(a__lt=4) & Q(a__gt=2)) | Q(a=1)).order_by('id'),
            [obj1, obj2, obj4]
        )

    def test_date_datetime_and_time(self):
        self.assertEqual(DateModel().datelist, DateModel._datelist_default)
        self.assert_(DateModel().datelist is not DateModel._datelist_default)
        DateModel.objects.create()
        self.assertNotEqual(DateModel.objects.get().datetime, None)
        DateModel.objects.update(
            time=datetime.time(hour=3, minute=5, second=7),
            date=datetime.date(year=2042, month=3, day=5),
            datelist=[datetime.date(2001, 1, 2)]
        )
        self.assertEqual(
            DateModel.objects.values_list('time', 'date', 'datelist').get(),
            (datetime.time(hour=3, minute=5, second=7),
             datetime.date(year=2042, month=3, day=5),
             [datetime.date(year=2001, month=1, day=2)])
        )

########NEW FILE########
__FILENAME__ = views
# Create your views here.

########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python
import os, sys
from django.core.management import execute_manager
# dirty hack to get the backend working.
sys.path.insert(0, os.path.abspath('./..'))
sys.path.insert(0, os.path.abspath('./../..'))

try:
    import settings # Assumed to be in the same directory.
except ImportError:
    import sys
    sys.stderr.write("Error: Can't find the file 'settings.py' in the directory containing %r. It appears you've customized things.\nYou'll have to run django-admin.py, passing it your settings module.\n(If the file settings.py does indeed exist, it's causing an ImportError somehow.)\n" % __file__)
    sys.exit(1)

os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'
# import django_mongodb_engine._bootstrap

if __name__ == "__main__":
    execute_manager(settings)

########NEW FILE########
__FILENAME__ = models
"""
19. OR lookups

To perform an OR lookup, or a lookup that combines ANDs and ORs, combine
``QuerySet`` objects using ``&`` and ``|`` operators.

Alternatively, use positional arguments, and pass one or more expressions of
clauses using the variable ``django.db.models.Q`` (or any object with an
``add_to_query`` method).
"""

from django.db import models

class Article(models.Model):
    headline = models.CharField(max_length=50)
    pub_date = models.DateTimeField()

    class Meta:
       ordering = ('pub_date',)

    def __unicode__(self):
        return self.headline

########NEW FILE########
__FILENAME__ = tests
from datetime import datetime
from operator import attrgetter

from django.db.models import Q
from django.test import TestCase

from models import Article


class OrLookupsTests(TestCase):

    def setUp(self):
        self.a1 = Article.objects.create(
            headline='Hello', pub_date=datetime(2005, 11, 27)
        ).pk
        self.a2 = Article.objects.create(
            headline='Goodbye', pub_date=datetime(2005, 11, 28)
        ).pk
        self.a3 = Article.objects.create(
            headline='Hello and goodbye', pub_date=datetime(2005, 11, 29)
        ).pk

    def test_filter_or(self):
        self.assertQuerysetEqual(
            Article.objects.filter(headline__startswith='Hello') |  Article.objects.filter(headline__startswith='Goodbye'), [
                'Hello',
                'Goodbye',
                'Hello and goodbye'
            ],
            attrgetter("headline")
        )

        self.assertQuerysetEqual(
            Article.objects.filter(headline__contains='Hello') | Article.objects.filter(headline__contains='bye'), [
                'Hello',
                'Goodbye',
                'Hello and goodbye'
            ],
            attrgetter("headline")
        )

        self.assertQuerysetEqual(
            Article.objects.filter(headline__iexact='Hello') | Article.objects.filter(headline__contains='ood'), [
                'Hello',
                'Goodbye',
                'Hello and goodbye'
            ],
            attrgetter("headline")
        )

        self.assertQuerysetEqual(
            Article.objects.filter(Q(headline__startswith='Hello') | Q(headline__startswith='Goodbye')), [
                'Hello',
                'Goodbye',
                'Hello and goodbye'
            ],
            attrgetter("headline")
        )


    def test_stages(self):
        # You can shorten this syntax with code like the following,  which is
        # especially useful if building the query in stages:
        articles = Article.objects.all()
        self.assertQuerysetEqual(
            articles.filter(headline__startswith='Hello') & articles.filter(headline__startswith='Goodbye'),
            []
        )
        self.assertQuerysetEqual(
            articles.filter(headline__startswith='Hello') & articles.filter(headline__contains='bye'), [
                'Hello and goodbye'
            ],
            attrgetter("headline")
        )

    def test_pk_q(self):
        self.assertQuerysetEqual(
            Article.objects.filter(Q(pk=self.a1) | Q(pk=self.a2)), [
                'Hello',
                'Goodbye'
            ],
            attrgetter("headline")
        )

        self.assertQuerysetEqual(
            Article.objects.filter(Q(pk=self.a1) | Q(pk=self.a2) | Q(pk=self.a3)), [
                'Hello',
                'Goodbye',
                'Hello and goodbye'
            ],
            attrgetter("headline"),
        )

    def test_pk_in(self):
        self.assertQuerysetEqual(
            Article.objects.filter(pk__in=[self.a1, self.a2, self.a3]), [
                'Hello',
                'Goodbye',
                'Hello and goodbye'
            ],
            attrgetter("headline"),
        )

        self.assertQuerysetEqual(
            Article.objects.filter(pk__in=(self.a1, self.a2, self.a3)), [
                'Hello',
                'Goodbye',
                'Hello and goodbye'
            ],
            attrgetter("headline"),
        )

        self.assertQuerysetEqual(
            Article.objects.filter(pk__in=[self.a1, self.a2, self.a3]), [
                'Hello',
                'Goodbye',
                'Hello and goodbye'
            ],
            attrgetter("headline"),
        )

    def test_q_negated(self):
        # Q objects can be negated
        self.assertQuerysetEqual(
            Article.objects.filter(Q(pk=self.a1) | ~Q(pk=self.a2)), [
                'Hello',
                'Hello and goodbye'
            ],
            attrgetter("headline")
        )

        # Does not work on MongoDB:
        #self.assertQuerysetEqual(
        #    Article.objects.filter(~Q(pk=self.a1) & ~Q(pk=self.a2)), [
        #        'Hello and goodbye'
        #    ],
        #    attrgetter("headline"),
        #)

        # This allows for more complex queries than filter() and exclude()
        # alone would allow
        self.assertQuerysetEqual(
            Article.objects.filter(Q(pk=self.a1) & (~Q(pk=self.a2) | Q(pk=self.a3))), [
                'Hello'
            ],
            attrgetter("headline"),
        )

    def test_complex_filter(self):
        # The 'complex_filter' method supports framework features such as
        # 'limit_choices_to' which normally take a single dictionary of lookup
        # arguments but need to support arbitrary queries via Q objects too.
        self.assertQuerysetEqual(
            Article.objects.complex_filter({'pk': self.a1}), [
                'Hello'
            ],
            attrgetter("headline"),
        )

        self.assertQuerysetEqual(
            Article.objects.complex_filter(Q(pk=self.a1) | Q(pk=self.a2)), [
                'Hello',
                'Goodbye'
            ],
            attrgetter("headline"),
        )

    def test_empty_in(self):
        # Passing "in" an empty list returns no results ...
        self.assertQuerysetEqual(
            Article.objects.filter(pk__in=[]),
            []
        )
        # ... but can return results if we OR it with another query.
        self.assertQuerysetEqual(
            Article.objects.filter(Q(pk__in=[]) | Q(headline__icontains='goodbye')), [
                'Goodbye',
                'Hello and goodbye'
            ],
            attrgetter("headline"),
        )

    def test_q_and(self):
        # Q arg objects are ANDed
        self.assertQuerysetEqual(
            Article.objects.filter(Q(headline__startswith='Hello'), Q(headline__contains='bye')), [
                'Hello and goodbye'
            ],
            attrgetter("headline")
        )
        # Q arg AND order is irrelevant
        self.assertQuerysetEqual(
            Article.objects.filter(Q(headline__contains='bye'), headline__startswith='Hello'), [
                'Hello and goodbye'
            ],
            attrgetter("headline"),
        )

        self.assertQuerysetEqual(
            Article.objects.filter(Q(headline__startswith='Hello') & Q(headline__startswith='Goodbye')),
            []
        )

    def test_q_exclude(self):
        self.assertQuerysetEqual(
            Article.objects.exclude(Q(headline__startswith='Hello')), [
                'Goodbye'
            ],
            attrgetter("headline")
        )

    def test_other_arg_queries(self):
        # Try some arg queries with operations other than filter.
        self.assertEqual(
            Article.objects.get(Q(headline__startswith='Hello'),
                                Q(headline__contains='bye')).headline,
            'Hello and goodbye'
        )

        self.assertEqual(
            Article.objects.filter(Q(headline__startswith='Hello') | Q(headline__contains='bye')).count(),
            3
        )

        self.assertQuerysetEqual(
            Article.objects.filter(Q(headline__startswith='Hello'), Q(headline__contains='bye')).values(), [
                {"headline": "Hello and goodbye", "id": self.a3, "pub_date": datetime(2005, 11, 29)},
            ],
            lambda o: o,
        )

        self.assertEqual(
            Article.objects.filter(Q(headline__startswith='Hello')).in_bulk([self.a1, self.a2]),
            {self.a1: Article.objects.get(pk=self.a1)}
        )

########NEW FILE########
__FILENAME__ = run-all
#!/usr/bin/python
import os
import settings

for app in settings.INSTALLED_APPS:
    os.system('./manage.py test %s' % app)

########NEW FILE########
__FILENAME__ = settings
# Run the test for 'myapp' with this setting on and off
MONGODB_AUTOMATIC_REFERENCING = True

DATABASES = {
    'default': {
        'ENGINE': 'django_mongodb_engine',
        'NAME': 'test',
        'USER': '',
        'PASSWORD': '',
        'HOST': 'localhost',
        'PORT': '27017',
        'SUPPORTS_TRANSACTIONS': False,
    },
}

INSTALLED_APPS = 'aggregations contrib embedded general or_lookups'.split()

# shortcut to check whether tests would pass using an SQL backend
USE_SQLITE = False

if USE_SQLITE:
    DATABASES = {'default' : {'ENGINE' : 'sqlite3'}}
    INSTALLED_APPS.remove('embedded')

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import *
from django.conf import settings
from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
    # Example:

    # Uncomment the admin/doc line below and add 'django.contrib.admindocs'
    # to INSTALLED_APPS to enable admin documentation:
    # (r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    (r'^admin/', include(admin.site.urls)),
)
########NEW FILE########
__FILENAME__ = __pkginfo__
#!/usr/bin/env python
# -*- coding: utf-8 -*-
import codecs
import django_mongodb_engine as distmeta

distname = 'django_mongodb_engine'
numversion = distmeta.__version__
version = '.'.join(map(str, numversion))
license = '2-clause BSD'
author = distmeta.__author__
author_email = distmeta.__contact__
web = distmeta.__homepage__

short_desc = "A MongoDB backend standing outside django."
long_desc = codecs.open('README.rst', 'r', 'utf-8').read()

install_requires = ['pymongo', 'django>=1.2', 'djangotoolbox']
pyversions = ['2', '2.4', '2.5', '2.6', '2.7']
docformat = distmeta.__docformat__
include_dirs = []

########NEW FILE########
