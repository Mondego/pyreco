__FILENAME__ = base
from django.core.exceptions import ImproperlyConfigured

from .creation import DatabaseCreation
from .serializer import Decoder, Encoder
from pyes import ES

from djangotoolbox.db.base import NonrelDatabaseFeatures, \
    NonrelDatabaseWrapper, NonrelDatabaseClient, \
    NonrelDatabaseValidation, NonrelDatabaseIntrospection

from djangotoolbox.db.base import NonrelDatabaseOperations

class DatabaseOperations(NonrelDatabaseOperations):
    compiler_module = __name__.rsplit('.', 1)[0] + '.compiler'

    def sql_flush(self, style, tables, sequence_list):
        for table in tables:
            self.connection.db_connection.delete_mapping(self.connection.db_name, table)
        return []

    def check_aggregate_support(self, aggregate):
        """
        This function is meant to raise exception if backend does
        not support aggregation.
        """
        pass
    
class DatabaseFeatures(NonrelDatabaseFeatures):
    string_based_auto_field = True

class DatabaseClient(NonrelDatabaseClient):
    pass

class DatabaseValidation(NonrelDatabaseValidation):
    pass

class DatabaseIntrospection(NonrelDatabaseIntrospection):
    def table_names(self):
        """
        Show defined models
        """
        # TODO: get indices
        return []

    def sequence_list(self):
        # TODO: check if it's necessary to implement that
        pass

class DatabaseWrapper(NonrelDatabaseWrapper):
    def _cursor(self):
        self._ensure_is_connected()
        return self._connection

    def __init__(self, *args, **kwds):
        super(DatabaseWrapper, self).__init__(*args, **kwds)
        self.features = DatabaseFeatures(self)
        self.ops = DatabaseOperations(self)
        self.client = DatabaseClient(self)
        self.creation = DatabaseCreation(self)
        self.validation = DatabaseValidation(self)
        self.introspection = DatabaseIntrospection(self)
        self._is_connected = False

    @property
    def db_connection(self):
        self._ensure_is_connected()
        return self._db_connection

    def _ensure_is_connected(self):
        if not self._is_connected:
            try:
                port = int(self.settings_dict['PORT'])
            except ValueError:
                raise ImproperlyConfigured("PORT must be an integer")

            self.db_name = self.settings_dict['NAME']

            self._connection = ES("%s:%s" % (self.settings_dict['HOST'], port),
                                  decoder=Decoder,
                                  encoder=Encoder,
                                  autorefresh=True,
                                  default_indices=[self.db_name])

            self._db_connection = self._connection
            #auto index creation: check if to remove
            try:
                self._connection.create_index(self.db_name)
            except:
                pass
            # We're done!
            self._is_connected = True

########NEW FILE########
__FILENAME__ = compiler
import sys
import re

from datetime import datetime
from functools import wraps

from django.conf import settings
from django.db import models
from django.db.models.sql import aggregates as sqlaggregates
from django.db.models.sql.compiler import SQLCompiler
from django.db.models.sql import aggregates as sqlaggregates
from django.db.models.sql.constants import LOOKUP_SEP, MULTI, SINGLE
from django.db.models.sql.where import AND, OR
from django.db.utils import DatabaseError, IntegrityError
from django.db.models.sql.where import WhereNode
from django.db.models.fields import NOT_PROVIDED
from django.utils.tree import Node
from pyes import MatchAllQuery, FilteredQuery, BoolQuery, StringQuery, \
                WildcardQuery, RegexTermQuery, RangeQuery, ESRange, \
                TermQuery, ConstantScoreQuery, TermFilter, TermsFilter, NotFilter, RegexTermFilter
from djangotoolbox.db.basecompiler import NonrelQuery, NonrelCompiler, \
    NonrelInsertCompiler, NonrelUpdateCompiler, NonrelDeleteCompiler
from django.db.models.fields import AutoField
import logging

TYPE_MAPPING_FROM_DB = {
    'unicode':  lambda val: unicode(val),
    'int':      lambda val: int(val),
    'float':    lambda val: float(val),
    'bool':     lambda val: bool(val),
}

TYPE_MAPPING_TO_DB = {
    'unicode':  lambda val: unicode(val),
    'int':      lambda val: int(val),
    'float':    lambda val: float(val),
    'bool':     lambda val: bool(val),
    'date':     lambda val: datetime(val.year, val.month, val.day),
    'time':     lambda val: datetime(2000, 1, 1, val.hour, val.minute,
                                     val.second, val.microsecond),
}

OPERATORS_MAP = {
    'exact':    lambda val: val,
    'iexact':    lambda val: val, #tofix
    'startswith':    lambda val: r'^%s' % re.escape(val),
    'istartswith':    lambda val: r'^%s' % re.escape(val),
    'endswith':    lambda val: r'%s$' % re.escape(val),
    'iendswith':    lambda val: r'%s$' % re.escape(val),
    'contains':    lambda val: r'%s' % re.escape(val),
    'icontains':    lambda val: r'%s' % re.escape(val),
    'regex':    lambda val: val,
    'iregex':   lambda val: re.compile(val, re.IGNORECASE),
    'gt':       lambda val: {"_from" : val, "include_lower" : False},
    'gte':      lambda val: {"_from" : val, "include_lower" : True},
    'lt':       lambda val: {"_to" : val, "include_upper": False},
    'lte':      lambda val: {"_to" : val, "include_upper": True},
    'range':    lambda val: {"_from" : val[0], "_to" : val[1], "include_lower" : True, "include_upper": True},
    'year':     lambda val: {"_from" : val[0], "_to" : val[1], "include_lower" : True, "include_upper": False},
    'isnull':   lambda val: None if val else {'$ne': None},
    'in':       lambda val: val,
}

NEGATED_OPERATORS_MAP = {
    'exact':    lambda val: {'$ne': val},
    'gt':       lambda val: {"_to" : val, "include_upper": True},
    'gte':      lambda val: {"_to" : val, "include_upper": False},
    'lt':       lambda val: {"_from" : val, "include_lower" : True},
    'lte':      lambda val: {"_from" : val, "include_lower" : False},
    'isnull':   lambda val: {'$ne': None} if val else None,
    'in':       lambda val: {'$nin': val},
}

def _get_mapping(db_type, value, mapping):
    # TODO - comments. lotsa comments

    if value == NOT_PROVIDED:
        return None

    if value is None:
        return None

    if db_type in mapping:
        _func = mapping[db_type]
    else:
        _func = lambda val: val
    # TODO - what if the data is represented as list on the python side?
    if isinstance(value, list):
        return map(_func, value)

    return _func(value)

def python2db(db_type, value):
    return _get_mapping(db_type, value, TYPE_MAPPING_TO_DB)

def db2python(db_type, value):
    return _get_mapping(db_type, value, TYPE_MAPPING_FROM_DB)

def safe_call(func):
    @wraps(func)
    def _func(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception, e:
            import traceback
            traceback.print_exc()
            raise DatabaseError, DatabaseError(str(e)), sys.exc_info()[2]
    return _func

class DBQuery(NonrelQuery):
    # ----------------------------------------------
    # Public API
    # ----------------------------------------------
    def __init__(self, compiler, fields):
        super(DBQuery, self).__init__(compiler, fields)
        self._connection = self.connection.db_connection
        self._ordering = []
        self.db_query = ConstantScoreQuery()

    # This is needed for debugging
    def __repr__(self):
        return '<DBQuery: %r ORDER %r>' % (self.db_query, self._ordering)

    @safe_call
    def fetch(self, low_mark, high_mark):
        results = self._get_results()

        if low_mark > 0:
            results = results[low_mark:]
        if high_mark is not None:
            results = results[low_mark:high_mark - low_mark]

        for hit in results:
            entity = hit.get_data()
            entity['id'] = hit.meta.id
            yield entity

    @safe_call
    def count(self, limit=None):
        query = self.db_query
        if self.db_query.is_empty():
            query = MatchAllQuery()

        res = self._connection.count(query, doc_types=self.query.model._meta.db_table)
        return res["count"]

    @safe_call
    def delete(self):
        self._collection.remove(self.db_query)

    @safe_call
    def order_by(self, ordering):
        for order in ordering:
            if order.startswith('-'):
                order, direction = order[1:], {"reverse" : True}
            else:
                direction = 'desc'
            self._ordering.append({order: direction})

    # This function is used by the default add_filters() implementation
    @safe_call
    def add_filter(self, column, lookup_type, negated, db_type, value):
        if column == self.query.get_meta().pk.column:
            column = '_id'
        # Emulated/converted lookups

        if negated and lookup_type in NEGATED_OPERATORS_MAP:
            op = NEGATED_OPERATORS_MAP[lookup_type]
            negated = False
        else:
            op = OPERATORS_MAP[lookup_type]
        value = op(self.convert_value_for_db(db_type, value))

        queryf = self._get_query_type(column, lookup_type, db_type, value)

        if negated:
            self.db_query.add([NotFilter(queryf)])
        else:
            self.db_query.add([queryf])

    def _get_query_type(self, column, lookup_type, db_type, value):
        if db_type == "unicode":
            if (lookup_type == "exact" or lookup_type == "iexact"):
                q = TermQuery(column, value)
                return q
            if (lookup_type == "startswith" or lookup_type == "istartswith"):
                return RegexTermFilter(column, value)
            if (lookup_type == "endswith" or lookup_type == "iendswith"):
                return RegexTermFilter(column, value)
            if (lookup_type == "contains" or lookup_type == "icontains"):
                return RegexTermFilter(column, value)
            if (lookup_type == "regex" or lookup_type == "iregex"):
                return RegexTermFilter(column, value)

        if db_type == "datetime" or db_type == "date":
            if (lookup_type == "exact" or lookup_type == "iexact"):
                return TermFilter(column, value)

        #TermFilter, TermsFilter
        if lookup_type in ["gt", "gte", "lt", "lte", "range", "year"]:
            value['field'] = column
            return RangeQuery(ESRange(**value))
        if lookup_type == "in":
#            terms = [TermQuery(column, val) for val in value]
#            if len(terms) == 1:
#                return terms[0]
#            return BoolQuery(should=terms)
            return TermsFilter(field=column, values=value)
        raise NotImplemented

    def _get_results(self):
        """
        @returns: elasticsearch iterator over results
        defined by self.query
        """
        query = self.db_query
        if self.db_query.is_empty():
            query = MatchAllQuery()
        if self._ordering:
            query.sort = self._ordering
        #print "query", self.query.tables, query
        return self._connection.search(query, indices=[self.connection.db_name], doc_types=self.query.model._meta.db_table)

class SQLCompiler(NonrelCompiler):
    """
    A simple query: no joins, no distinct, etc.
    """
    query_class = DBQuery

    def convert_value_from_db(self, db_type, value):
        # Handle list types
        if db_type is not None and \
                isinstance(value, (list, tuple)) and len(value) and \
                db_type.startswith('ListField:'):
            db_sub_type = db_type.split(':', 1)[1]
            value = [self.convert_value_from_db(db_sub_type, subvalue)
                     for subvalue in value]
        else:
            value = db2python(db_type, value)
        return value

    # This gets called for each field type when you insert() an entity.
    # db_type is the string that you used in the DatabaseCreation mapping
    def convert_value_for_db(self, db_type, value):
        if db_type is not None and \
                isinstance(value, (list, tuple)) and len(value) and \
                db_type.startswith('ListField:'):
            db_sub_type = db_type.split(':', 1)[1]
            value = [self.convert_value_for_db(db_sub_type, subvalue)
                     for subvalue in value]
        else:
            value = python2db(db_type, value)
        return value

    def insert_params(self):
        conn = self.connection

        params = {
            'safe': conn.safe_inserts,
        }

        if conn.w:
            params['w'] = conn.w

        return params

    def _get_ordering(self):
        if not self.query.default_ordering:
            ordering = self.query.order_by
        else:
            ordering = self.query.order_by or self.query.get_meta().ordering
        result = []
        for order in ordering:
            if LOOKUP_SEP in order:
                #raise DatabaseError("Ordering can't span tables on non-relational backends (%s)" % order)
                print "Ordering can't span tables on non-relational backends (%s):skipping" % order
                continue
            if order == '?':
                raise DatabaseError("Randomized ordering isn't supported by the backend")

            order = order.lstrip('+')

            descending = order.startswith('-')
            name = order.lstrip('-')
            if name == 'pk':
                name = self.query.get_meta().pk.name
                order = '-' + name if descending else name

            if self.query.standard_ordering:
                result.append(order)
            else:
                if descending:
                    result.append(name)
                else:
                    result.append('-' + name)
        return result


class SQLInsertCompiler(NonrelInsertCompiler, SQLCompiler):
    @safe_call
    def insert(self, data, return_id=False):
        pk_column = self.query.get_meta().pk.column
        pk = None
        if pk_column in data:
            pk = data[pk_column]
        db_table = self.query.get_meta().db_table
        logging.debug("Insert data %s: %s" % (db_table, data))
        #print("Insert data %s: %s" % (db_table, data))
        res = self.connection.db_connection.index(data, self.connection.db_name, db_table, id=pk)
        #print "Insert result", res
        return res['_id']

# TODO: Define a common nonrel API for updates and add it to the nonrel
# backend base classes and port this code to that API
class SQLUpdateCompiler(SQLCompiler):
    def execute_sql(self, return_id=False):
        """
        self.query - the data that should be inserted
        """
        data = {}
        for (field, value), column in zip(self.query.values, self.query.columns):
            data[column] = python2db(field.db_type(connection=self.connection), value)
        # every object should have a unique pk
        pk_field = self.query.model._meta.pk
        pk_name = pk_field.attname

        db_table = self.query.get_meta().db_table
        res = self.connection.db_connection.index(data, self.connection.db_name, db_table, id=pk)

        return res['_id']

class SQLDeleteCompiler(NonrelDeleteCompiler, SQLCompiler):
    def execute_sql(self, return_id=False):
        """
        self.query - the data that should be inserted
        """
        db_table = self.query.get_meta().db_table
        if len(self.query.where.children) == 1 and isinstance(self.query.where.children[0][0].field, AutoField) and  self.query.where.children[0][1] == "in":
            for pk in self.query.where.children[0][3]:
                self.connection.db_connection.delete(self.connection.db_name, db_table, pk)
        return

########NEW FILE########
__FILENAME__ = creation
from djangotoolbox.db.base import NonrelDatabaseCreation
from pyes.exceptions import NotFoundException
TEST_DATABASE_PREFIX = 'test_'

class DatabaseCreation(NonrelDatabaseCreation):
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
        'GenericAutoField':             'unicode',
        'StringForeignKey':             'unicode',
        'AutoField':                    'unicode',
        'RelatedAutoField':             'unicode',
        'OneToOneField':                'int',
        'DecimalField':                 'float',
    }

    def sql_indexes_for_field(self, model, f, style):
        """Not required. In ES all is index!!"""
        return []

    def index_fields_group(self, model, group, style):
        """Not required. In ES all is index!!"""
        return []

    def sql_indexes_for_model(self, model, style):
        """Not required. In ES all is index!!"""
        return []

    def sql_create_model(self, model, style, known_models=set()):
        from mapping import model_to_mapping
        mappings = model_to_mapping(model)
        self.connection.db_connection.put_mapping(model._meta.db_table, {mappings.name:mappings.as_dict()})
        return [], {}

    def set_autocommit(self):
        "Make sure a connection is in autocommit mode."
        pass

    def create_test_db(self, verbosity=1, autoclobber=False):
        # No need to create databases in mongoDB :)
        # but we can make sure that if the database existed is emptied
        from django.core.management import call_command
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
        try:
            self._drop_database(test_database_name)
        except NotFoundException:
            pass

        self.connection.db_connection.create_index(test_database_name)
        self.connection.db_connection.cluster_health(wait_for_status='green')

        call_command('syncdb', verbosity=max(verbosity - 1, 0), interactive=False, database=self.connection.alias)


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
        try:
            self.connection.db_connection.delete_index(database_name)
        except NotFoundException:
            pass
        self.connection.db_connection.cluster_health(wait_for_status='green')

    def sql_destroy_model(self, model, references_to_delete, style):
        print model

########NEW FILE########
__FILENAME__ = fields
import django
from django.conf import settings
from django.db import models
from django.core import exceptions, serializers
from django.db.models import Field, CharField
from django.db.models.fields import FieldDoesNotExist
from django.utils.translation import ugettext_lazy as _
from django.db.models.fields import AutoField as DJAutoField
from django.db.models import signals
import uuid
from .manager import Manager
__all__ = ["EmbeddedModel"]
__doc__ = "ES special fields"

class EmbeddedModel(models.Model):
    _embedded_in = None
    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        if self.pk is None:
            self.pk = str(uuid.uuid4())
        if self._embedded_in  is None:
            raise RuntimeError("Invalid save")
        self._embedded_in.save()

    def serialize(self):
        if self.pk is None:
            self.pk = "TODO"
            self.id = self.pk
        result = {'_app':self._meta.app_label,
            '_model':self._meta.module_name,
            '_id':self.pk}
        for field in self._meta.fields:
            result[field.attname] = getattr(self, field.attname)
        return result

class ElasticField(CharField):

    def __init__(self, *args, **kwargs):
        self.doc_type = kwargs.pop("doc_type", None)

        # This field stores the document id and has to be unique
        kwargs["unique"] = True

        # Let's force the field as db_index so we can get its value faster.
        kwargs["db_index"] = True
        kwargs["max_length"] = 255

        super(ElasticField, self).__init__(*args, **kwargs)

    def contribute_to_class(self, cls, name):
        super(ElasticField, self).contribute_to_class(cls, name)


        index = cls._meta.db_table
        doc_type = self.doc_type
        att_id_name = "_%s_id" % name
        att_cache_name = "_%s_cache" % name
        att_val_name = "_%s_val" % name

        def _get(self):
            """
            self is the model instance not the field instance
            """
            from django.db import connections
            elst = connections[self._meta.elst_connection]
            if not hasattr(self, att_cache_name) and not getattr(self, att_val_name, None) and getattr(self, att_id_name, None):
                elst = ES('http://127.0.0.1:9200/')
                val = elst.get(index, doc_type, id=getattr(self, att_id_name)).get("_source", None)
                setattr(self, att_cache_name, val)
                setattr(self, att_val_name, val)
            return getattr(self, att_val_name, None)

        def _set(self, val):
            """
            self is the model instance not the field instance
            """
            if isinstance(val, basestring) and not hasattr(self, att_id_name):
                setattr(self, att_id_name, val)
            else:
                setattr(self, att_val_name, val or None)

        setattr(cls, self.attname, property(_get, _set))


#    def db_type(self, connection):
#        return "elst"

    def pre_save(self, model_instance, add):
        from django.db import connections
        elst = connections[model_instance._meta.elst_connection]

        id = getattr(model_instance, "_%s_id" % self.attname, None)
        value = getattr(model_instance, "_%s_val" % self.attname, None)
        index = model_instance._meta.db_table
        doc_type = self.doc_type

        if value == getattr(model_instance, "_%s_cache" % self.attname, None) and id:
            return id

        if value:
#            elst = ES('http://127.0.0.1:9200/')
            result = elst.index(doc=value, index=index, doc_type=doc_type, id=id or None)
            setattr(model_instance, "_%s_id" % self.attname, result["_id"])
            setattr(model_instance, "_%s_cache" % self.attname, value)
        return getattr(model_instance, "_%s_id" % self.attname, u"")

#
# Fix standard models to work with elasticsearch
#

def autofield_to_python(value):
    if value is None:
        return value
    try:
        return str(value)
    except (TypeError, ValueError):
        raise exceptions.ValidationError(self.error_messages['invalid'])

def autofield_get_prep_value(value):
    if value is None:
        return None
    return unicode(value)

def pre_init_mongodb_signal(sender, args, **kwargs):
    if sender._meta.abstract:
        return

    from django.conf import settings

    database = settings.DATABASES[sender.objects.db]
    if not 'elasticsearch' in database['ENGINE']:
        return

    if not hasattr(django, 'MODIFIED') and isinstance(sender._meta.pk, DJAutoField):
        pk = sender._meta.pk
        setattr(pk, "to_python", autofield_to_python)
        setattr(pk, "get_prep_value", autofield_get_prep_value)

class ESMeta(object):
    pass

def add_elasticsearch_manager(sender, **kwargs):
    """
    Fix autofield
    """
    from django.conf import settings

    cls = sender
    database = settings.DATABASES[cls.objects.db]
    if 'elasticsearch' in database['ENGINE']:
        if cls._meta.abstract:
            return

        if getattr(cls, 'es', None) is None:
            # Create the default manager, if needed.
            try:
                cls._meta.get_field('es')
                raise ValueError("Model %s must specify a custom Manager, because it has a field named 'objects'" % cls.__name__)
            except FieldDoesNotExist:
                pass
            setattr(cls, 'es', Manager())

            es_meta = getattr(cls, "ESMeta", ESMeta).__dict__.copy()
#            setattr(cls, "_meta", ESMeta())
            for attr in es_meta:
                if attr.startswith("_"):
                    continue
                setattr(cls._meta, attr, es_meta[attr])


########NEW FILE########
__FILENAME__ = manager
from django.db import connections
from django.db.models.manager import Manager as DJManager

import re
import copy
from .utils import dict_keys_to_str
try:
    from django.core.exceptions import MultipleObjectsReturned, ObjectDoesNotExist
except ImportError:
    class ObjectDoesNotExist(Exception):
        pass
    class MultipleObjectsReturned(Exception):
        pass
    
DoesNotExist = ObjectDoesNotExist

__all__ = ['queryset_manager', 'Q', 'InvalidQueryError',
           'InvalidCollectionError']

# The maximum number of items to display in a QuerySet.__repr__
REPR_OUTPUT_SIZE = 20

class InvalidQueryError(Exception):
    pass


class OperationError(Exception):
    pass

class InvalidCollectionError(Exception):
    pass

DoesNotExist = ObjectDoesNotExist
RE_TYPE = type(re.compile(''))


class Q(object):

    OR = '||'
    AND = '&&'
    OPERATORS = {
        'eq': 'this.%(field)s == %(value)s',
        'ne': 'this.%(field)s != %(value)s',
        'gt': 'this.%(field)s > %(value)s',
        'gte': 'this.%(field)s >= %(value)s',
        'lt': 'this.%(field)s < %(value)s',
        'lte': 'this.%(field)s <= %(value)s',
        'lte': 'this.%(field)s <= %(value)s',
        'in': '%(value)s.indexOf(this.%(field)s) != -1',
        'nin': '%(value)s.indexOf(this.%(field)s) == -1',
        'mod': '%(field)s %% %(value)s',
        'all': ('%(value)s.every(function(a){'
                'return this.%(field)s.indexOf(a) != -1 })'),
        'size': 'this.%(field)s.length == %(value)s',
        'exists': 'this.%(field)s != null',
        'regex_eq': '%(value)s.test(this.%(field)s)',
        'regex_ne': '!%(value)s.test(this.%(field)s)',
    }

    def __init__(self, **query):
        self.query = [query]

    def _combine(self, other, op):
        obj = Q()
        obj.query = ['('] + copy.deepcopy(self.query) + [op]
        obj.query += copy.deepcopy(other.query) + [')']
        return obj

    def __or__(self, other):
        return self._combine(other, self.OR)

    def __and__(self, other):
        return self._combine(other, self.AND)

    def as_js(self, document):
        js = []
        js_scope = {}
        for i, item in enumerate(self.query):
            if isinstance(item, dict):
                item_query = QuerySet._transform_query(document, **item)
                # item_query will values will either be a value or a dict
                js.append(self._item_query_as_js(item_query, js_scope, i))
            else:
                js.append(item)
        return pymongo.code.Code(' '.join(js), js_scope)

    def _item_query_as_js(self, item_query, js_scope, item_num):
        # item_query will be in one of the following forms
        #    {'age': 25, 'name': 'Test'}
        #    {'age': {'$lt': 25}, 'name': {'$in': ['Test', 'Example']}
        #    {'age': {'$lt': 25, '$gt': 18}}
        js = []
        for i, (key, value) in enumerate(item_query.items()):
            op = 'eq'
            # Construct a variable name for the value in the JS
            value_name = 'i%sf%s' % (item_num, i)
            if isinstance(value, dict):
                # Multiple operators for this field
                for j, (op, value) in enumerate(value.items()):
                    # Create a custom variable name for this operator
                    op_value_name = '%so%s' % (value_name, j)
                    # Construct the JS that uses this op
                    value, operation_js = self._build_op_js(op, key, value,
                                                            op_value_name)
                    # Update the js scope with the value for this op
                    js_scope[op_value_name] = value
                    js.append(operation_js)
            else:
                # Construct the JS for this field
                value, field_js = self._build_op_js(op, key, value, value_name)
                js_scope[value_name] = value
                js.append(field_js)
        return ' && '.join(js)

    def _build_op_js(self, op, key, value, value_name):
        """Substitute the values in to the correct chunk of Javascript.
        """
        if isinstance(value, RE_TYPE):
            # Regexes are handled specially
            if op.strip('$') == 'ne':
                op_js = Q.OPERATORS['regex_ne']
            else:
                op_js = Q.OPERATORS['regex_eq']
        else:
            op_js = Q.OPERATORS[op.strip('$')]

        # Perform the substitution
        operation_js = op_js % {
            'field': key, 
            'value': value_name
        }
        return value, operation_js

class InternalMetadata:
    def __init__(self, meta):
        self.object_name  = meta["object_name"]

class InternalModel:
    """
    An internal queryset model to be embedded in a query set for django compatibility.
    """
    def __init__(self, document):
        self.document = document
        self._meta = InternalMetadata(document._meta)
        self.DoesNotExist = ObjectDoesNotExist

class QuerySet(object):
    """A set of results returned from a query. Wraps a ES cursor,
    providing :class:`~mongoengine.Document` objects as the results.
    """

    def __init__(self, document, collection):
        self._document = document
        self._collection_obj = collection
        self._accessed_collection = False
        self._query = {}
        self._where_clause = None
        self._loaded_fields = []
        self._ordering = []
        self.transform = TransformDjango()
        
        # If inheritance is allowed, only return instances and instances of
        # subclasses of the class being used
        #if document._meta.get('allow_inheritance'):
            #self._query = {'_types': self._document._class_name}
        self._cursor_obj = None
        self._limit = None
        self._skip = None

        #required for compatibility with django
        #self.model = InternalModel(document)

    def __call__(self, q_obj=None, **query):
        """Filter the selected documents by calling the
        :class:`~mongoengine.queryset.QuerySet` with a query.

        :param q_obj: a :class:`~mongoengine.queryset.Q` object to be used in
            the query; the :class:`~mongoengine.queryset.QuerySet` is filtered
            multiple times with different :class:`~mongoengine.queryset.Q`
            objects, only the last one will be used
        :param query: Django-style query keyword arguments
        """
        if q_obj:
            self._where_clause = q_obj.as_js(self._document)
        query = QuerySet._transform_query(_doc_cls=self._document, **query)
        self._query.update(query)
        return self

    def filter(self, *q_objs, **query):
        """An alias of :meth:`~mongoengine.queryset.QuerySet.__call__`
        """
        return self.__call__(*q_objs, **query)

    def find(self, query):
        self._query.update(self.transform.transform_incoming(query, self._collection))
        return self

    def exclude(self, *q_objs, **query):
        """An alias of :meth:`~mongoengine.queryset.QuerySet.__call__`
        """
        query["not"] = True
        return self.__call__(*q_objs, **query)

    def all(self):
        """An alias of :meth:`~mongoengine.queryset.QuerySet.__call__`
        """
        return self.__call__()
    
    def distinct(self, *args, **kwargs):
        """
        Distinct method
        """
        return self._cursor.distinct(*args, **kwargs)

    @property
    def _collection(self):
        """Property that returns the collection object. This allows us to
        perform operations only if the collection is accessed.
        """
        return self._collection_obj
    
    def values(self, *args):
        return (args and [dict(zip(args,[getattr(doc, key) for key in args])) for doc in self]) or [obj for obj in self._cursor.clone()]
        
    def values_list(self, *args, **kwargs):
        flat = kwargs.pop("flat", False)
        if flat and len(args) != 1:
            raise Exception("args len must be 1 when flat=True")
        
        return (flat and self.distinct(args[0] if not args[0] in ["id", "pk"] else "_id")) or zip(*[self.distinct(field if not field in ["id", "pk"] else "_id") for field in args])

    @property
    def _cursor(self):
        if self._cursor_obj is None:
            cursor_args = {}
            if self._loaded_fields:
                cursor_args = {'fields': self._loaded_fields}
            self._cursor_obj = self._collection.find(self._query, 
                                                     **cursor_args)
            # Apply where clauses to cursor
            if self._where_clause:
                self._cursor_obj.where(self._where_clause)

            # apply default ordering
#            if self._document._meta['ordering']:
#                self.order_by(*self._document._meta['ordering'])

        return self._cursor_obj.clone()

    @classmethod
    def _lookup_field(cls, document, fields):
        """
        Looks for "field" in "document"
        """
        if isinstance(fields, (tuple, list)):
            return [document._meta.get_field_by_name((field == "pk" and "id") or field)[0] for field in fields]
        return document._meta.get_field_by_name((fields == "pk" and "id") or fields)[0]

    @classmethod
    def _translate_field_name(cls, doc_cls, field, sep='.'):
        """Translate a field attribute name to a database field name.
        """
        parts = field.split(sep)
        parts = [f.attname for f in QuerySet._lookup_field(doc_cls, parts)]
        return '.'.join(parts)

    @classmethod
    def _transform_query(self,  _doc_cls=None, **parameters):
        """
        Converts parameters to elasticsearch queries. 
        """
        spec = {}
        operators = ['ne', 'gt', 'gte', 'lt', 'lte', 'in', 'nin', 'mod', 'all', 'size', 'exists']
        match_operators = ['contains', 'icontains', 'startswith', 'istartswith', 'endswith', 'iendswith', 'exact', 'iexact']
        exclude = parameters.pop("not", False)
        
        for key, value in parameters.items():
            
            
            parts  = key.split("__")
            lookup_type = (len(parts)>=2) and ( parts[-1] in operators + match_operators and parts.pop()) or ""
            
            # Let's get the right field and be sure that it exists
            parts[0] = QuerySet._lookup_field(_doc_cls, parts[0]).attname
            
            if not lookup_type and len(parts)==1:
                if exclude:
                    value = {"$ne" : value}
                spec.update({parts[0] : value})
                continue
            
            if parts[0] == "id":
                parts[0] = "_id"
                value = [isinstance(par, basestring) or par for par in value]
                
            if lookup_type in ['contains', 'icontains',
                                 'startswith', 'istartswith',
                                 'endswith', 'iendswith',
                                 'exact', 'iexact']:
                flags = 0
                if lookup_type.startswith('i'):
                    flags = re.IGNORECASE
                    lookup_type = lookup_type.lstrip('i')
                    
                regex = r'%s'
                if lookup_type == 'startswith':
                    regex = r'^%s'
                elif lookup_type == 'endswith':
                    regex = r'%s$'
                elif lookup_type == 'exact':
                    regex = r'^%s$'
                    
                value = re.compile(regex % value, flags)
                
            elif lookup_type in operators:
                value = { "$" + lookup_type : value}
            elif lookup_type and len(parts)==1:
                raise DatabaseError("Unsupported lookup type: %r" % lookup_type)
    
            key = '.'.join(parts)
            if exclude:
                value = {"$ne" : value}
            spec.update({key : value})
            
        return spec
    
    def get(self, *q_objs, **query):
        """Retrieve the the matching object raising id django is available
        :class:`~django.core.exceptions.MultipleObjectsReturned` or
        :class:`~django.core.exceptions.ObjectDoesNotExist` exceptions if multiple or
        no results are found.
        If django is not available:
        :class:`~mongoengine.queryset.MultipleObjectsReturned` or
        `DocumentName.MultipleObjectsReturned` exception if multiple results and
        :class:`~mongoengine.queryset.DoesNotExist` or `DocumentName.DoesNotExist`
        if no results are found.

        .. versionadded:: 0.3
        """
        self.__call__(*q_objs, **query)
        count = self.count()
        if count == 1:
            return self[0]
        elif count > 1:
            message = u'%d items returned, instead of 1' % count
            raise self._document.MultipleObjectsReturned(message)
        else:
            raise self._document.DoesNotExist("%s matching query does not exist."
                                              % self._document._meta.object_name)

    def get_or_create(self, *q_objs, **query):
        """Retrieve unique object or create, if it doesn't exist. Returns a tuple of 
        ``(object, created)``, where ``object`` is the retrieved or created object 
        and ``created`` is a boolean specifying whether a new object was created. Raises
        :class:`~mongoengine.queryset.MultipleObjectsReturned` or
        `DocumentName.MultipleObjectsReturned` if multiple results are found.
        A new document will be created if the document doesn't exists; a
        dictionary of default values for the new document may be provided as a
        keyword argument called :attr:`defaults`.

        .. versionadded:: 0.3
        """
        defaults = query.get('defaults', {})
        if 'defaults' in query:
            del query['defaults']

        self.__call__(*q_objs, **query)
        count = self.count()
        if count == 0:
            query.update(defaults)
            doc = self._document(**query)
            doc.save()
            return doc, True
        elif count == 1:
            return self.first(), False
        else:
            message = u'%d items returned, instead of 1' % count
            raise self._document.MultipleObjectsReturned(message)

    def first(self):
        """Retrieve the first object matching the query.
        """
        try:
            result = self[0]
        except IndexError:
            result = None
        return result

    def with_id(self, object_id):
        """Retrieve the object matching the id provided.

        :param object_id: the value for the id of the document to look up
        """
        id_field = self._document._meta['id_field']
        object_id = self._document._fields[id_field].to_mongo(object_id)

        result = self._collection.find_one({'_id': (not isinstance(object_id, ObjectId) and ObjectId(object_id)) or object_id})
        if result is not None:
            result = self._document(**dict_keys_to_str(result))
        return result

    def in_bulk(self, object_ids):
        """Retrieve a set of documents by their ids.
        
        :param object_ids: a list or tuple of id's
        :rtype: dict of ids as keys and collection-specific
                Document subclasses as values.

        .. versionadded:: 0.3
        """
        doc_map = {}

        docs = self._collection.find({'_id': {'$in': [ (not isinstance(id, ObjectId) and ObjectId(id)) or id for id in object_ids]}})
        for doc in docs:
            doc_map[str(doc['id'])] = self._document(**dict_keys_to_str(doc))
 
        return doc_map
    
    def count(self):
        """Count the selected elements in the query.
        """
        if self._limit == 0:
            return 0
        return self._cursor.count(with_limit_and_skip=False)

    def __len__(self):
        return self.count()

    def map_reduce(self, map_f, reduce_f, finalize_f=None, limit=None,
                   scope=None, keep_temp=False):
        """Perform a map/reduce query using the current query spec
        and ordering. While ``map_reduce`` respects ``QuerySet`` chaining,
        it must be the last call made, as it does not return a maleable
        ``QuerySet``.

        See the :meth:`~mongoengine.tests.QuerySetTest.test_map_reduce`
        and :meth:`~mongoengine.tests.QuerySetTest.test_map_advanced`
        tests in ``tests.queryset.QuerySetTest`` for usage examples.

        :param map_f: map function, as :class:`~pymongo.code.Code` or string
        :param reduce_f: reduce function, as
                         :class:`~pymongo.code.Code` or string
        :param finalize_f: finalize function, an optional function that
                           performs any post-reduction processing.
        :param scope: values to insert into map/reduce global scope. Optional.
        :param limit: number of objects from current query to provide
                      to map/reduce method
        :param keep_temp: keep temporary table (boolean, default ``True``)

        Returns an iterator yielding
        :class:`~mongoengine.document.MapReduceDocument`.

        .. note:: Map/Reduce requires server version **>= 1.1.1**. The PyMongo
           :meth:`~pymongo.collection.Collection.map_reduce` helper requires
           PyMongo version **>= 1.2**.

        .. versionadded:: 0.3
        """
        #from document import MapReduceDocument
        
        if not hasattr(self._collection, "map_reduce"):
            raise NotImplementedError("Requires MongoDB >= 1.1.1")

        map_f_scope = {}
        if isinstance(map_f, pymongo.code.Code):
            map_f_scope = map_f.scope
            map_f = unicode(map_f)
#        map_f = pymongo.code.Code(self._sub_js_fields(map_f), map_f_scope)
        map_f = pymongo.code.Code(map_f, map_f_scope)

        reduce_f_scope = {}
        if isinstance(reduce_f, pymongo.code.Code):
            reduce_f_scope = reduce_f.scope
            reduce_f = unicode(reduce_f)
#        reduce_f_code = self._sub_js_fields(reduce_f)
        reduce_f_code = reduce_f
        reduce_f = pymongo.code.Code(reduce_f_code, reduce_f_scope)

        mr_args = {'query': self._query, 'keeptemp': keep_temp}

        if finalize_f:
            finalize_f_scope = {}
            if isinstance(finalize_f, pymongo.code.Code):
                finalize_f_scope = finalize_f.scope
                finalize_f = unicode(finalize_f)
#            finalize_f_code = self._sub_js_fields(finalize_f)
            finalize_f_code = finalize_f
            finalize_f = pymongo.code.Code(finalize_f_code, finalize_f_scope)
            mr_args['finalize'] = finalize_f

        if scope:
            mr_args['scope'] = scope

        if limit:
            mr_args['limit'] = limit

        results = self._collection.map_reduce(map_f, reduce_f, **mr_args)
        results = results.find()

        if self._ordering:
            results = results.sort(self._ordering)

        for doc in results:
            yield self._document.objects.with_id(doc['value'])

    def limit(self, n):
        """Limit the number of returned documents to `n`. This may also be
        achieved using array-slicing syntax (e.g. ``User.objects[:5]``).

        :param n: the maximum number of objects to return
        """
        if n == 0:
            self._cursor.limit(1)
        else:
            self._cursor.limit(n)
        self._limit = n

        # Return self to allow chaining
        return self

    def skip(self, n):
        """Skip `n` documents before returning the results. This may also be
        achieved using array-slicing syntax (e.g. ``User.objects[5:]``).

        :param n: the number of objects to skip before returning results
        """
        self._cursor.skip(n)
        self._skip = n
        return self

    def __getitem__(self, key):
        """Support skip and limit using getitem and slicing syntax.
        """
        # Slice provided
        if isinstance(key, slice):
            try:
                self._cursor_obj = self._cursor[key]
                self._skip, self._limit = key.start, key.stop
            except IndexError, err:
                # PyMongo raises an error if key.start == key.stop, catch it,
                # bin it, kill it. 
                start = key.start or 0
                if start >= 0 and key.stop >= 0 and key.step is None:
                    if start == key.stop:
                        self.limit(0)
                        self._skip, self._limit = key.start, key.stop - start
                        return self
                raise err
            # Allow further QuerySet modifications to be performed
            return self
        # Integer index provided
        elif isinstance(key, int):
            return self._document(**dict_keys_to_str(self._cursor[key]))

    def only(self, *fields):
        """Load only a subset of this document's fields. ::
        
            post = BlogPost.objects(...).only("title")
        
        :param fields: fields to include

        .. versionadded:: 0.3
        """
        self._loaded_fields = []
        for field in fields:
            if '.' in field:
                raise InvalidQueryError('Subfields cannot be used as '
                                        'arguments to QuerySet.only')
            # Translate field name
            field = QuerySet._lookup_field(self._document, field)[-1].db_field
            self._loaded_fields.append(field)

        # _cls is needed for polymorphism
        if self._document._meta.get('allow_inheritance'):
            self._loaded_fields += ['_cls']
        return self

    def order_by(self, *args):
        """Order the :class:`~mongoengine.queryset.QuerySet` by the keys. The
        order may be specified by prepending each of the keys by a + or a -.
        Ascending order is assumed.

        :param keys: fields to order the query results by; keys may be
            prefixed with **+** or **-** to determine the ordering direction
        """
        
        self._ordering = []
        for col in args:
            self._ordering.append(( (col.startswith("-") and col[1:]) or col, (col.startswith("-") and -1) or 1 ))
            
        self._cursor.sort(self._ordering)
        return self

    def explain(self, format=False):
        """Return an explain plan record for the
        :class:`~mongoengine.queryset.QuerySet`\ 's cursor.

        :param format: format the plan before returning it
        """

        plan = self._cursor.explain()
        if format:
            import pprint
            plan = pprint.pformat(plan)
        return plan

    def delete(self, safe=False):
        """Delete the documents matched by the query.

        :param safe: check if the operation succeeded before returning
        """
        self._collection.remove(self._query, safe=safe)

    @classmethod
    def _transform_update(cls, _doc_cls=None, **update):
        """Transform an update spec from Django-style format to Mongo format.
        """
        operators = ['set', 'unset', 'inc', 'dec', 'push', 'push_all', 'pull',
                     'pull_all']

        mongo_update = {}
        for key, value in update.items():
            parts = key.split('__')
            # Check for an operator and transform to mongo-style if there is
            op = None
            if parts[0] in operators:
                op = parts.pop(0)
                # Convert Pythonic names to Mongo equivalents
                if op in ('push_all', 'pull_all'):
                    op = op.replace('_all', 'All')
                elif op == 'dec':
                    # Support decrement by flipping a positive value's sign
                    # and using 'inc'
                    op = 'inc'
                    if value > 0:
                        value = -value

            if _doc_cls:
                # Switch field names to proper names [set in Field(name='foo')]
                fields = QuerySet._lookup_field(_doc_cls, parts)
                parts = [field.db_field for field in fields]

                # Convert value to proper value
                field = fields[-1]
                if op in (None, 'set', 'unset', 'push', 'pull'):
                    value = field.prepare_query_value(op, value)
                elif op in ('pushAll', 'pullAll'):
                    value = [field.prepare_query_value(op, v) for v in value]

            key = '.'.join(parts)

            if op:
                value = {key: value}
                key = '$' + op

            if op is None or key not in mongo_update:
                mongo_update[key] = value
            elif key in mongo_update and isinstance(mongo_update[key], dict):
                mongo_update[key].update(value)

        return mongo_update

    def update(self, safe_update=True, upsert=False, **update):
        """Perform an atomic update on the fields matched by the query.

        :param safe: check if the operation succeeded before returning
        :param update: Django-style update keyword arguments

        .. versionadded:: 0.2
        """
        if pymongo.version < '1.1.1':
            raise OperationError('update() method requires PyMongo 1.1.1+')

        update = QuerySet._transform_update(self._document, **update)
        try:
            self._collection.update(self._query, update, safe=safe_update, 
                                    upsert=upsert, multi=True)
        except pymongo.errors.OperationFailure, err:
            if unicode(err) == u'multi not coded yet':
                message = u'update() method requires MongoDB 1.1.3+'
                raise OperationError(message)
            raise OperationError(u'Update failed (%s)' % unicode(err))

    def update_one(self, safe_update=True, upsert=False, **update):
        """Perform an atomic update on first field matched by the query.

        :param safe: check if the operation succeeded before returning
        :param update: Django-style update keyword arguments

        .. versionadded:: 0.2
        """
        update = QuerySet._transform_update(self._document, **update)
        try:
            # Explicitly provide 'multi=False' to newer versions of PyMongo
            # as the default may change to 'True'
            if pymongo.version >= '1.1.1':
                self._collection.update(self._query, update, safe=safe_update, 
                                        upsert=upsert, multi=False)
            else:
                # Older versions of PyMongo don't support 'multi'
                self._collection.update(self._query, update, safe=safe_update)
        except pymongo.errors.OperationFailure, e:
            raise OperationError(u'Update failed [%s]' % unicode(e))

    def __iter__(self, *args, **kwargs):
        for obj in self._cursor:
            data = dict_keys_to_str(obj)
            if '_id' in data:
                data['id']=data.pop('_id')
            yield self._document(**data)

    def _sub_js_fields(self, code):
        """When fields are specified with [~fieldname] syntax, where 
        *fieldname* is the Python name of a field, *fieldname* will be 
        substituted for the MongoDB name of the field (specified using the
        :attr:`name` keyword argument in a field's constructor).
        """
        def field_sub(match):
            # Extract just the field name, and look up the field objects
            field_name = match.group(1).split('.')
            fields = QuerySet._lookup_field(self._document, field_name)
            # Substitute the correct name for the field into the javascript
            return u'["%s"]' % fields[-1].db_field

        return re.sub(u'\[\s*~([A-z_][A-z_0-9.]+?)\s*\]', field_sub, code)

    def exec_js(self, code, *fields, **options):
        """
        Execute a Javascript function on the server. A list of fields may be
        provided, which will be translated to their correct names and supplied
        as the arguments to the function. A few extra variables are added to
        the function's scope: ``collection``, which is the name of the
        collection in use; ``query``, which is an object representing the
        current query; and ``options``, which is an object containing any
        options specified as keyword arguments.

        As fields in MongoEngine may use different names in the database (set
        using the :attr:`db_field` keyword argument to a :class:`Field` 
        constructor), a mechanism exists for replacing MongoEngine field names
        with the database field names in Javascript code. When accessing a 
        field, use square-bracket notation, and prefix the MongoEngine field
        name with a tilde (~).

        :param code: a string of Javascript code to execute
        :param fields: fields that you will be using in your function, which
            will be passed in to your function as arguments
        :param options: options that you want available to the function
            (accessed in Javascript through the ``options`` object)
        """
#        code = self._sub_js_fields(code)

        fields = [QuerySet._translate_field_name(self._document, f) for f in fields]
        collection = self._collection

        scope = {
            'collection': collection.name,
            'options': options or {},
        }

        query = self._query
        if self._where_clause:
            query['$where'] = self._where_clause

        scope['query'] = query
        code = pymongo.code.Code(code, scope=scope)

        return collection.database.eval(code, *fields)

    def sum(self, field):
        """Sum over the values of the specified field.

        :param field: the field to sum over; use dot-notation to refer to
            embedded document fields
        """
        sum_func = """
            function(sumField) {
                var total = 0.0;
                db[collection].find(query).forEach(function(doc) {
                    total += (doc[sumField] || 0.0);
                });
                return total;
            }
        """
        return self.exec_js(sum_func, field)

    def average(self, field):
        """Average over the values of the specified field.

        :param field: the field to average over; use dot-notation to refer to
            embedded document fields
        """
        average_func = """
            function(averageField) {
                var total = 0.0;
                var num = 0;
                db[collection].find(query).forEach(function(doc) {
                    if (doc[averageField]) {
                        total += doc[averageField];
                        num += 1;
                    }
                });
                return total / num;
            }
        """
        return self.exec_js(average_func, field)

    def item_frequencies(self, list_field, normalize=False):
        """Returns a dictionary of all items present in a list field across
        the whole queried set of documents, and their corresponding frequency.
        This is useful for generating tag clouds, or searching documents.

        :param list_field: the list field to use
        :param normalize: normalize the results so they add to 1.0
        """
        freq_func = """
            function(listField) {
                if (options.normalize) {
                    var total = 0.0;
                    db[collection].find(query).forEach(function(doc) {
                        total += doc[listField].length;
                    });
                }

                var frequencies = {};
                var inc = 1.0;
                if (options.normalize) {
                    inc /= total;
                }
                db[collection].find(query).forEach(function(doc) {
                    doc[listField].forEach(function(item) {
                        frequencies[item] = inc + (frequencies[item] || 0);
                    });
                });
                return frequencies;
            }
        """
        return self.exec_js(freq_func, list_field, normalize=normalize)

    def __repr__(self):
        limit = REPR_OUTPUT_SIZE + 1
        if self._limit is not None and self._limit < limit:
            limit = self._limit
        data = list(self[self._skip:limit])
        if len(data) > REPR_OUTPUT_SIZE:
            data[-1] = "...(remaining elements truncated)..."
        return repr(data)

    def _clone(self):
        return self


class Manager(DJManager):

    def __init__(self, manager_func=None):
        super(Manager, self).__init__()
        self._manager_func = manager_func
        self._collection = None

    def contribute_to_class(self, model, name):
        # TODO: Use weakref because of possible memory leak / circular reference.
        self.model = model
#        setattr(model, name, ManagerDescriptor(self))
        if model._meta.abstract or (self._inherited and not self.model._meta.proxy):
            model._meta.abstract_managers.append((self.creation_counter, name,
                    self))
        else:
            model._meta.concrete_managers.append((self.creation_counter, name,
                self))
            
    def __get__(self, instance, owner):
        """Descriptor for instantiating a new QuerySet object when
        Document.objects is accessed.
        """
        self.model = owner #We need to set the model to get the db

        if instance is not None:
            # Document class being used rather than a document object
            return self

        if self._collection is None:
            self._collection = connections[self.db].db_connection[owner._meta.db_table]

        # owner is the document that contains the QuerySetManager
        queryset = QuerySet(owner, self._collection)
        if self._manager_func:
            if self._manager_func.func_code.co_argcount == 1:
                queryset = self._manager_func(queryset)
            else:
                queryset = self._manager_func(owner, queryset)
        return queryset


def queryset_manager(func):
    """Decorator that allows you to define custom QuerySet managers on
    :class:`~mongoengine.Document` classes. The manager must be a function that
    accepts a :class:`~mongoengine.Document` class as its first argument, and a
    :class:`~mongoengine.queryset.QuerySet` as its second argument. The method
    function should return a :class:`~mongoengine.queryset.QuerySet`, probably
    the same one that was passed in, but modified in some way.
    """
    if func.func_code.co_argcount == 1:
        import warnings
        msg = 'Methods decorated with queryset_manager should take 2 arguments'
        warnings.warn(msg, DeprecationWarning)
    return QuerySetManager(func)

########NEW FILE########
__FILENAME__ = mapping
#!/usr/bin/env python
# -*- coding: utf-8 -*-

from pyes import mappings
from django.conf import settings
import time
from django.db.models.manager import Manager

def model_to_mapping(model, depth=1):
    """
    Given a model return a mapping
    """
    meta = model._meta
    indexoptions = getattr(model, "indexeroptions", {})
    ignore = indexoptions.get("ignore", [])
    fields_options = indexoptions.get("fields", {})
    extra_fields = indexoptions.get("extra_fields", {})
    mapper = mappings.ObjectField(meta.module_name)
    for field in meta.fields + meta.many_to_many:
        name = field.name
        if name in ignore:
            continue
        mapdata = get_mapping_for_field(field, depth=depth, **fields_options.get(name, {}))
        if mapdata:
            mapper.add_property(mapdata)
    for name, options in extra_fields.items():
        type = options.pop("type", "string")
        if type == "string":
            data = dict(name=name, store=True,
                           index="analyzed",
                           term_vector="with_positions_offsets"
                           )
            data.update(options)

            if  data['index'] == 'not_analyzed':
                del data['term_vector']

            mapper.add_property(mappings.StringField(**data))
            continue

    return mapper

def get_mapping_for_field(field, depth=1, **options):
    """Given a field returns a mapping"""
    ntype = type(field).__name__
    if ntype in ["AutoField"]:
#        return mappings.MultiField(name=field.name,
#                                   fields={field.name:mappings.StringField(name=field.name, store=True),
#                                           "int":mappings.IntegerField(name="int", store=True)}
#                                   )
        return mappings.StringField(name=field.name, store=True)
    elif ntype in ["IntegerField",
                   "PositiveSmallIntegerField",
                   "SmallIntegerField",
                   "PositiveIntegerField",
                   "PositionField",
                   ]:
        return mappings.IntegerField(name=field.name, store=True)
    elif ntype in ["FloatField",
                   "DecimalField",
                   ]:
        return mappings.DoubleField(name=field.name, store=True)
    elif ntype in ["BooleanField",
                   "NullBooleanField",
                   ]:
        return mappings.BooleanField(name=field.name, store=True)
    elif ntype in ["DateField",
                   "DateTimeField",
                   "CreationDateTimeField",
                   "ModificationDateTimeField",
                   "AddedDateTimeField",
                   "ModifiedDateTimeField",
                   "brainaetic.djangoutils.db.fields.CreationDateTimeField",
                   "brainaetic.djangoutils.db.fields.ModificationDateTimeField",
                   ]:
        return mappings.DateField(name=field.name, store=True)
    elif ntype in ["SlugField",
                   "EmailField",
                   "TagField",
                   "URLField",
                   "CharField",
                   "ImageField",
                   "FileField",
                   ]:
        return mappings.MultiField(name=field.name,
                                   fields={field.name:mappings.StringField(name=field.name, index="not_analyzed", store=True),
                                           "tk":mappings.StringField(name="tk", store=True,
                                                                index="analyzed",
                                                                term_vector="with_positions_offsets")}

                                   )
    elif ntype in ["TextField",
                   ]:
        data = dict(name=field.name, store=True,
                       index="analyzed",
                       term_vector="with_positions_offsets"
                       )
        if field.unique:
            data['index'] = 'not_analyzed'

        data.update(options)

        if  data['index'] == 'not_analyzed':
            del data['term_vector']

        return mappings.StringField(**data)
    elif ntype in ["ForeignKey",
                   "TaggableManager",
                   "GenericRelation",
                   ]:
        if depth >= 0:
            mapper = model_to_mapping(field.rel.to, depth - 1)
            if mapper:
                mapper.name = field.name
                return mapper
            return None
        return get_mapping_for_field(field.rel.to._meta.pk, depth - 1)

#                   "IPAddressField",
#                   'PickledObjectField'

    elif ntype in ["ManyToManyField",
                   ]:
        if depth > 0:
            mapper = model_to_mapping(field.rel.to, depth - 1)
            mapper.name = field.name
            return mapper
        if depth == 0:
            mapper = get_mapping_for_field(field.rel.to._meta.pk, depth - 1)
            if mapper:
                mapper.name = field.name
                return mapper
            return None
        if depth < 0:
            return None
    print ntype
    return None


########NEW FILE########
__FILENAME__ = models
from django.db.models import signals
from .fields import add_elasticsearch_manager

signals.class_prepared.connect(add_elasticsearch_manager)
########NEW FILE########
__FILENAME__ = router

class ESRouter(object):
    """A router to control all database operations on models in
    the myapp application"""
    def __init__(self):
        from django.conf import settings
        self.managed_apps = [app.split('.')[-1] for app in getattr(settings, "ELASTICSEARCH_MANAGED_APPS", [])]
        self.managed_models = getattr(settings, "ELASTICSEARCH_MANAGED_MODELS", [])
        self.elasticsearch_database = None
        self.elasticsearch_databases = []
        for name, databaseopt in settings.DATABASES.items():
            if databaseopt["ENGINE"]=='django_elasticsearch':
                self.elasticsearch_database = name
                self.elasticsearch_databases.append(name)
        if self.elasticsearch_database is None:
            raise RuntimeError("A elasticsearch database must be set")

    def db_for_read(self, model, **hints):
        "Point all operations on elasticsearch models to a elasticsearch database"
        if model._meta.app_label in self.managed_apps:
            return self.elasticsearch_database
        key = "%s.%s"%(model._meta.app_label, model._meta.module_name)
        if key in self.managed_models:
            return self.elasticsearch_database
        return None

    def db_for_write(self, model, **hints):
        "Point all operations on elasticsearch models to a elasticsearch database"
        if model._meta.app_label in self.managed_apps:
            return self.elasticsearch_database
        key = "%s.%s"%(model._meta.app_label, model._meta.module_name)
        if key in self.managed_models:
            return self.elasticsearch_database
        return None

    def allow_relation(self, obj1, obj2, **hints):
        "Allow any relation if a model in myapp is involved"

        #key1 = "%s.%s"%(obj1._meta.app_label, obj1._meta.module_name)
        key2 = "%s.%s"%(obj2._meta.app_label, obj2._meta.module_name)

        # obj2 is the model instance so, mongo_serializer should take care
        # of the related object. We keep trac of the obj1 db so, don't worry
        # about the multi-database management
        if obj2._meta.app_label in self.managed_apps or key2 in self.managed_models:
            return True

        return None

    def allow_syncdb(self, db, model):
        "Make sure that a elasticsearch model appears on a elasticsearch database"
        key = "%s.%s"%(model._meta.app_label, model._meta.module_name)
        if db in self.elasticsearch_databases:
            return model._meta.app_label  in self.managed_apps or key in self.managed_models
        elif model._meta.app_label in self.managed_apps or key in self.managed_models:
            if db in self.elasticsearch_databases:
                return True
            else:
                return False
        return None

    def valid_for_db_engine(self, driver, model):
        "Make sure that a model is valid for a database provider"
        if driver!="elasticsearch":
            return None
        if model._meta.app_label in self.managed_apps:
            return True
        key = "%s.%s"%(model._meta.app_label, model._meta.module_name)
        if key in self.managed_models:
            return True
        return None
        

########NEW FILE########
__FILENAME__ = serializer
from django.utils.importlib import import_module
from datetime import datetime, date, time
#TODO Add content type cache
from utils import ModelLazyObject
from json import JSONDecoder, JSONEncoder
import uuid

class Decoder(JSONDecoder):
    """Extends the base simplejson JSONDecoder for Dejavu."""
    def __init__(self, arena=None, encoding=None, object_hook=None, **kwargs):
        JSONDecoder.__init__(self, encoding, object_hook, **kwargs)
        if not self.object_hook:
            self.object_hook = self.json_to_python
        self.arena = arena

    def json_to_python(self, son):
        
        if isinstance(son, dict):
            if "_type" in son and son["_type"] in [u"django", u'emb']:
                son = self.decode_django(son)
            else:
                for (key, value) in son.items():
                    if isinstance(value, dict):
                        if "_type" in value and value["_type"] in [u"django", u'emb']:
                            son[key] = self.decode_django(value)
                        else:
                            son[key] = self.json_to_python(value)
                    elif hasattr(value, "__iter__"): # Make sure we recurse into sub-docs
                        son[key] = [self.json_to_python(item) for item in value]
                    else: # Again, make sure to recurse into sub-docs
                        son[key] = self.json_to_python(value)
        elif hasattr(son, "__iter__"): # Make sure we recurse into sub-docs
            son = [self.json_to_python(item) for item in son]
        return son

    def decode_django(self, data):
        from django.contrib.contenttypes.models import ContentType
        if data['_type']=="django":
            model = ContentType.objects.get(app_label=data['_app'], model=data['_model'])
            return ModelLazyObject(model.model_class(), data['pk'])
        elif data['_type']=="emb":
            try:
                model = ContentType.objects.get(app_label=data['_app'], model=data['_model']).model_class()
            except:
                module = import_module(data['_app'])
                model = getattr(module, data['_model'])            
            
            del data['_type']
            del data['_app']
            del data['_model']
            data.pop('_id', None)
            values = {}
            for k,v in data.items():
                values[str(k)] = self.json_to_python(v)
            return model(**values)

class Encoder(JSONEncoder):
    def __init__(self, *args, **kwargs):
        JSONEncoder.__init__(self, *args, **kwargs)
        

    def encode_django(self, model):
        """
        Encode ricorsive embedded models and django models
        """
        from django_elasticsearch.fields import EmbeddedModel
        if isinstance(model, EmbeddedModel):
            if model.pk is None:
                model.pk = str(uuid.uuid4())
            res = {'_app':model._meta.app_label, 
                   '_model':model._meta.module_name,
                   '_id':model.pk}
            for field in model._meta.fields:
                res[field.attname] = self.default(getattr(model, field.attname))
            res["_type"] = "emb"
            from django.contrib.contenttypes.models import ContentType
            try:
                ContentType.objects.get(app_label=res['_app'], model=res['_model'])
            except:
                res['_app'] = model.__class__.__module__
                res['_model'] = model._meta.object_name
                
            return res
        if not model.pk:
            model.save()
        return {'_app':model._meta.app_label, 
                '_model':model._meta.module_name,
                'pk':model.pk,
                '_type':"django"}

    def default(self, value):
        """Convert rogue and mysterious data types.
        Conversion notes:
        
        - ``datetime.date`` and ``datetime.datetime`` objects are
        converted into datetime strings.
        """
        from django.db.models import Model
        from django_elasticsearch.fields import EmbeddedModel

        if isinstance(value, datetime):
            return value.strftime("%Y-%m-%dT%H:%M:%S")
        elif isinstance(value, date):
            dt = datetime(value.year, value.month, value.day, 0, 0, 0)
            return dt.strftime("%Y-%m-%dT%H:%M:%S")
#        elif isinstance(value, dict):
#            for (key, value) in value.items():
#                if isinstance(value, (str, unicode)):
#                    continue
#                if isinstance(value, (Model, EmbeddedModel)):
#                    value[key] = self.encode_django(value, collection)
#                elif isinstance(value, dict): # Make sure we recurse into sub-docs
#                    value[key] = self.transform_incoming(value)
#                elif hasattr(value, "__iter__"): # Make sure we recurse into sub-docs
#                    value[key] = [self.transform_incoming(item) for item in value]
        elif isinstance(value, (str, unicode)):
            pass
        elif hasattr(value, "__iter__"): # Make sure we recurse into sub-docs
            value = [self.transform_incoming(item, collection) for item in value]
        elif isinstance(value, (Model, EmbeddedModel)):
            value = self.encode_django(value)
        return value

########NEW FILE########
__FILENAME__ = south
class DatabaseOperations(object):
    """
    ES implementation of database operations.
    """
    
    backend_name = "django.db.backends.elasticsearch"

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
from django.utils.functional import SimpleLazyObject

def dict_keys_to_str(dictionary, recursive=False):
    res = dict([(str(k), (not isinstance(v, dict) and v) or (recursive and dict_keys_to_str(v)) or v) for k,v in dictionary.items()])
    if '_id' in res:
        res["id"] = res.pop("_id")
    return res 

class ModelLazyObject(SimpleLazyObject):
    """
    A lazy object initialised a model.
    """
    def __init__(self, model, pk):
        """
        Pass in a callable that returns the object to be wrapped.

        If copies are made of the resulting SimpleLazyObject, which can happen
        in various circumstances within Django, then you must ensure that the
        callable can be safely run more than once and will return the same
        value.
        """
        # For some reason, we have to inline LazyObject.__init__ here to avoid
        # recursion
        self._wrapped = None
        self.__dict__['_pk'] = pk
        self.__dict__['_model'] = model
        super(ModelLazyObject, self).__init__(self._load_data)

    def _load_data(self):
        return self._model.objects.get(pk=self._pk)

########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python
import os, sys
from django.core.management import execute_manager
# dirty hack to get the backend working.
#sys.path.insert(0, os.path.abspath('./..'))
#sys.path.insert(0, os.path.abspath('./../..'))
#example_dir = os.path.dirname(__file__)
#sys.path.insert(0, os.path.join(example_dir, '..'))
try:
    import settings # Assumed to be in the same directory.
except ImportError:
    import sys
    sys.stderr.write("Error: Can't find the file 'settings.py' in the directory containing %r. It appears you've customized things.\nYou'll have to run django-admin.py, passing it your settings module.\n(If the file settings.py does indeed exist, it's causing an ImportError somehow.)\n" % __file__)
    sys.exit(1)

if __name__ == "__main__":
    execute_manager(settings)

########NEW FILE########
__FILENAME__ = models
from django.db import models

class Post(models.Model):
    title = models.CharField(max_length=200, db_index=True)
    
    def __unicode__(self):
        return "Post: %s" % self.title

class Record(models.Model):
    title = models.CharField(max_length=200, db_index=True)
    
    def __unicode__(self):
        return "Record: %s" % self.title
    
########NEW FILE########
__FILENAME__ = tests
"""
This file demonstrates two different styles of tests (one doctest and one
unittest). These will both pass when you run "manage.py test".

Replace these with more appropriate tests for your application.
"""

from django.test import TestCase

class SimpleTest(TestCase):
    def test_basic_addition(self):
        """
        Tests that 1 + 1 always equals 2.
        """
        self.failUnlessEqual(1 + 1, 2)

__test__ = {"doctest": """
Another way to test that 1 + 1 is equal to 2.

>>> 1 + 1 == 2
True
"""}


########NEW FILE########
__FILENAME__ = views
# Create your views here.

########NEW FILE########
__FILENAME__ = models
from django.db import models
from django.utils.translation import ugettext_lazy as _
from django_elasticsearch.fields import EmbeddedModel
from djangotoolbox.fields import ListField, DictField

class Blog(models.Model):
    title = models.CharField(max_length=200, db_index=True)
    
    def __unicode__(self):
        return "Blog: %s" % self.title

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
    
    def __unicode__(self):
        return u"Person: %s %s" % (self.name, self.surname)

class StandardAutoFieldModel(models.Model):
    title = models.CharField(max_length=200)
    
    def __unicode__(self):
        return "Standard model: %s" % (self.title)

class EModel(EmbeddedModel):
    title = models.CharField(max_length=200)
    pos = models.IntegerField(default = 10)

    def test_func(self):
        return self.pos

class TestFieldModel(models.Model):
    title = models.CharField(max_length=200)
    mlist = ListField()
    mlist_default = ListField(default=["a", "b"])
    mdict = DictField()
    mdict_default = DictField(default={"a": "a", 'b':1})

    class MongoMeta:
        index_together = [{
                            'fields' : [ ('title', False), 'mlist']
                            }]
    def __unicode__(self):
        return "Test special field model: %s" % (self.title)

########NEW FILE########
__FILENAME__ = tests
"""
Test suite for django-elasticsearch.
"""

from django.test import TestCase
from testproj.myapp.models import Entry, Blog, StandardAutoFieldModel, Person, TestFieldModel, EModel
import datetime
import time

class DjangoESTest(TestCase):
#    multi_db = True

#    def test_add_and_delete_blog(self):
#        blog1 = Blog(title="blog1")
#        blog1.save()
#        self.assertEqual(Blog.objects.count(), 1)
#        blog2 = Blog(title="blog2")
#        self.assertEqual(blog2.pk, None)
#        blog2.save()
#        self.assertNotEqual(blog2.pk, None)
#        self.assertEqual(Blog.objects.count(), 2)
#        blog2.delete()
#        self.assertEqual(Blog.objects.count(), 1)
#        blog1.delete()
#        self.assertEqual(Blog.objects.count(), 0)

    def test_simple_get(self):
        blog1 = Blog(title="blog1")
        blog1.save()
        blog2 = Blog(title="blog2")
        blog2.save()
        self.assertEqual(Blog.objects.count(), 2)
        self.assertEqual(
            Blog.objects.get(title="blog2"),
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
        blog4 = Blog.objects.get(pk=blog1.pk)
        self.assertEqual(blog4, blog1)
        self.assertEqual(
            Blog.objects.filter(title="same title").count(),
            2
        )
        self.assertEqual(
            Blog.objects.filter(title="same title", pk=blog1.pk).count(),
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
        bl = Blog.objects.all()[0]
        self.assertEqual(blog1.title, bl.title)
        bl.delete()

#    def test_dates_ordering(self):
#        now = datetime.datetime.now()
#        before = now - datetime.timedelta(days=1)
#        
#        entry1 = Entry(title="entry 1", date_published=now)
#        entry1.save()
#
#        entry2 = Entry(title="entry 2", date_published=before)
#        entry2.save()
#    
#        self.assertEqual(
#            list(Entry.objects.order_by('-date_published')),
#            [entry1, entry2]
#        )
#
##        self.assertEqual(
##            list(Entry.objects.order_by('date_published')),
##            [entry2, entry1]
##        )
#
#
##    def test_dates_less_and_more_than(self):
##        now = datetime.datetime.now()
##        before = now + datetime.timedelta(days=1)
##        after = now - datetime.timedelta(days=1)
##        
##        entry1 = Entry(title="entry 1", date_published=now)
##        entry1.save()
##
##        entry2 = Entry(title="entry 2", date_published=before)
##        entry2.save()
##
##        entry3 = Entry(title="entry 3", date_published=after)
##        entry3.save()
##
##        a = list(Entry.objects.filter(date_published=now))
##        self.assertEqual(
##            list(Entry.objects.filter(date_published=now)),
##            [entry1]
##        )
##        self.assertEqual(
##            list(Entry.objects.filter(date_published__lt=now)),
##            [entry3]
##        )
##        self.assertEqual(
##            list(Entry.objects.filter(date_published__gt=now)),
##            [entry2]
##        )
#
#    def test_complex_queries(self):
#        p1 = Person(name="igor", surname="duck", age=39)
#        p1.save()
#        p2 = Person(name="andrea", surname="duck", age=29)
#        p2.save()
#        self.assertEqual(
#            Person.objects.filter(name="igor", surname="duck").count(),
#            1
#        )
#        self.assertEqual(
#            Person.objects.filter(age__gte=20, surname="duck").count(),
#            2
#        )
#
#    def test_fields(self):
#        t1 = TestFieldModel(title="p1", 
#                            mlist=["ab", "bc"],
#                            mdict = {'a':23, "b":True  },
#                            )
#        t1.save()
#        
#        t = TestFieldModel.objects.get(id=t1.id)
#        self.assertEqual(t.mlist, ["ab", "bc"])
#        self.assertEqual(t.mlist_default, ["a", "b"])
#        self.assertEqual(t.mdict, {'a':23, "b":True  })
#        self.assertEqual(t.mdict_default, {"a": "a", 'b':1})
#
#
#    def test_embedded_model(self):
#        em = EModel(title="1", pos = 1)
#        em2 = EModel(title="2", pos = 2)
#        t1 = TestFieldModel(title="p1", 
#                            mlist=[em, em2],
#                            mdict = {'a':em, "b":em2  },
#                            )
#        t1.save()
#        
#        t = TestFieldModel.objects.get(id=t1.id)
#        self.assertEqual(len(t.mlist), 2)
#        self.assertEqual(t.mlist[0].test_func(), 1)
#        self.assertEqual(t.mlist[1].test_func(), 2)
#
#    def test_simple_foreign_keys(self):
#        now = datetime.datetime.now()
#
#        blog1 = Blog(title="Blog")
#        blog1.save()
#        entry1 = Entry(title="entry 1", blog=blog1)
#        entry1.save()
#        entry2 = Entry(title="entry 2", blog=blog1)
#        entry2.save()
#        self.assertEqual(Entry.objects.count(), 2)
#
#        for entry in Entry.objects.all():
#            self.assertEqual(
#                blog1,
#                entry.blog
#            )
#
#        blog2 = Blog(title="Blog")
#        blog2.save()
#        entry3 = Entry(title="entry 3", blog=blog2)
#        entry3.save()
#        self.assertEqual(
#            # it's' necessary to explicitly state the pk here
#           len( list(Entry.objects.filter(blog=blog1.pk))),
#            len([entry1, entry2])
#        )
#        
#
##    def test_foreign_keys_bug(self):
##        blog1 = Blog(title="Blog")
##        blog1.save()
##        entry1 = Entry(title="entry 1", blog=blog1)
##        entry1.save()
##        self.assertEqual(
##            # this should work too
##            list(Entry.objects.filter(blog=blog1)),
##            [entry1]
##        )
#
##    def test_standard_autofield(self):
##
##        sam1 = StandardAutoFieldModel(title="title 1")
##        sam1.save()
##        sam2 = StandardAutoFieldModel(title="title 2")
##        sam2.save()
##
##        self.assertEqual(
##            StandardAutoFieldModel.objects.count(),
##            2
##        )
##
##        sam1_query = StandardAutoFieldModel.objects.get(title="title 1")
##        self.assertEqual(
##            sam1_query.pk,
##            sam1.pk
##        )
##
##        sam1_query = StandardAutoFieldModel.objects.get(pk=sam1.pk)
##        
#

########NEW FILE########
__FILENAME__ = views
# Create your views here.

########NEW FILE########
__FILENAME__ = settings
# Django settings for testproj2 project.

DEBUG = True
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    # ('Your Name', 'your_email@domain.com'),
)

MANAGERS = ADMINS

DATABASES = {
#    'default': {
#        'ENGINE': 'sqlite3', # Add 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'oracle'.
#        'NAME': 'test.db',                      # Or path to database file if using sqlite3.
#        'USER': '',                      # Not used with sqlite3.
#        'PASSWORD': '',                  # Not used with sqlite3.
#        'HOST': '',                      # Set to empty string for localhost. Not used with sqlite3.
#        'PORT': '',                      # Set to empty string for default. Not used with sqlite3.
#    },
    'default': {
        'ENGINE': 'django_elasticsearch',
        'NAME': 'test',
        'USER': '',
        'PASSWORD': '',
        'HOST': 'localhost',
        'PORT': '9200',
        'SUPPORTS_TRANSACTIONS': False,
    },
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
# calendars according to the current locale
USE_L10N = True

# Absolute path to the directory that holds media.
# Example: "/home/media/media.lawrence.com/"
MEDIA_ROOT = ''

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash if there is a path component (optional in other cases).
# Examples: "http://media.lawrence.com", "http://example.com/media/"
MEDIA_URL = ''

# URL prefix for admin media -- CSS, JavaScript and images. Make sure to use a
# trailing slash.
# Examples: "http://foo.com/media/", "/media/".
ADMIN_MEDIA_PREFIX = '/media/'

# Make this unique, and don't share it with anybody.
SECRET_KEY = 'ju^y4b6j4w%)346pf8oxbw=po8)-)hd3ugq=jjw4x38ugf#_0c'

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
)

ROOT_URLCONF = 'testproj.urls'

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
    'testproj.myapp',
    'testproj.mixed',
    #'south',
    # Uncomment the next line to enable the admin:
    'django.contrib.admin',
)

#DATABASE_ROUTERS = ['django_elasticsearch.router.ESRouter']
ELASTICSEARCH_MANAGED_APPS = ['testproj.myapp', ]
ELASTICSEARCH_MANAGED_MODELS = ['mixed.record', ]

#SOUTH_DATABASE_ADAPTERS = { "default" : "django_elasticsearch.south"}

########NEW FILE########
__FILENAME__ = tests
import os
os.environ["DJANGO_SETTINGS_MODULE"] = "notsqltestproj.settings"

from myapp.models import Entry, Person

doc, c = Person.elasticsearch.get_or_create(name="Pippo", defaults={'surname' : "Pluto", 'age' : 10})
print doc.pk
print doc.surname
print doc.age

cursor = Person.elasticsearch.filter(age=10)
print cursor[0]
########NEW FILE########
