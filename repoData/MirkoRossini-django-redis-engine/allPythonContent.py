__FILENAME__ = base
from django.core.exceptions import ImproperlyConfigured
from django.conf import settings

import redis
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
        raise NotImplementedError("django-redis-engine does not support %r "
                                      "aggregates" % type(aggregate))

    def sql_flush(self, style, tables, sequence_list):
        """
        Returns a list of SQL statements that have to be executed to drop
        all `tables`. Not implemented yes, returns an empty list.
        """
        
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
        return []#self.connection.db_connection.collection_names()

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
	
	try:
		return self._connection
	except:
		pass
        self._connect()
        return self._connection

    @property
    def db_connection(self):
        """
        Returns the db_connection instance
         
        """
	try:
		if self._connection is not None:
			return self._connection
	except:
	        self._connect()
        return self._db_connection

    def _connect(self):
	import traceback
	import sys
	#print '-------------------'
	#traceback.print_stack()
	#print '-------------------'
        if not self._connected:
            host = self.settings_dict['HOST'] or None
            port = self.settings_dict.get('PORT', None) or None
            user = self.settings_dict.get('USER', None)
            password = self.settings_dict.get('PASSWORD')
            self.db_name = self.settings_dict['NAME']
            try:
              self.exact_all = settings.REDIS_EXACT_ALL
            except AttributeError:
              self.exact_all = True

            self.safe_inserts = self.settings_dict.get('SAFE_INSERTS', False)

            self.wait_for_slaves = self.settings_dict.get('WAIT_FOR_SLAVES', 0)
            slave_okay = self.settings_dict.get('SLAVE_OKAY', False)

            try:
                if host is not None:
                    assert isinstance(host, basestring), \
                    'If set, HOST must be a string'

                if port:
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

            self._connection = redis.Redis(host=host,
                                                  port=port,
                                          #        slave_okay=slave_okay
						)

            if user and password:
                auth = self._connection[self.db_name].authenticate(user,
                                                                   password)
                if not auth:
                    raise ImproperlyConfigured("Username and/or password for "
                                               "the Redis db are not correct")

            self._db_connection = self._connection#[self.db_name]

            
            self._connected = True

        # TODO: signal! (see Alex' backend)

########NEW FILE########
__FILENAME__ = client
from django.db.backends import BaseDatabaseClient

class DatabaseClient(BaseDatabaseClient):
    executable_name = 'redis'

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
from redis_entity import RedisEntity,split_db_type,hash_for_redis,get_hash_key,get_set_key,get_list_key,enpickle,unpickle

from index_utils import get_indexes,create_indexes,delete_indexes,filter_with_index,isiterable

import pickle
import redis


from djangotoolbox.db.basecompiler import NonrelQuery, NonrelCompiler, \
    NonrelInsertCompiler, NonrelUpdateCompiler, NonrelDeleteCompiler



#TODO pipeline!!!!!!!!!!!!!!!!!!!!!

def safe_regex(regex, *re_args, **re_kwargs):
    def wrapper(value):
        return re.compile(regex % re.escape(value), *re_args, **re_kwargs)
    wrapper.__name__ = 'safe_regex (%r)' % regex
    return wrapper

OPERATORS_MAP = {
    'exact':        lambda val: val,
#    'iexact':       safe_regex('^%s$', re.IGNORECASE),
#    'startswith':   safe_regex('^%s'),
#    'istartswith':  safe_regex('^%s', re.IGNORECASE),
#    'endswith':     safe_regex('%s$'),
#    'iendswith':    safe_regex('%s$', re.IGNORECASE),
#    'contains':     safe_regex('%s'),
#    'icontains':    safe_regex('%s', re.IGNORECASE),
#    'regex':    lambda val: re.compile(val),
#    'iregex':   lambda val: re.compile(val, re.IGNORECASE),
#    'gt':       lambda val: {'$gt': val},
#    'gte':      lambda val: {'$gte': val},
#    'lt':       lambda val: {'$lt': val},
#    'lte':      lambda val: {'$lte': val},
#    'range':    lambda val: {'$gte': val[0], '$lte': val[1]},
#    'year':     lambda val: {'$gte': val[0], '$lt': val[1]},
#    'isnull':   lambda val: None if val else {'$ne': None},
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
        except Exception,e:
            raise DatabaseError, DatabaseError(str(e)), sys.exc_info()[2]
    return wrapper


class DBQuery(NonrelQuery):
    # ----------------------------------------------
    # Public API
    # ----------------------------------------------
    def __init__(self, compiler, fields):
        super(DBQuery, self).__init__(compiler, fields)
	#print fields
	#print dir(self.query.get_meta())
        self.db_table = self.query.get_meta().db_table
	self.indexes = get_indexes()
	self.indexes_for_model =  self.indexes.get(self.query.model,{})
	self._collection = self.connection.db_connection
	self.db_name = self.connection.db_name
	#self.connection.exact_all
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
	#print 'here results ',results
        primarykey_column = self.query.get_meta().pk.column
        for e_id in results:
            yield RedisEntity(e_id,self._collection,self.db_table,primarykey_column,self.query.get_meta(),self.db_name)

    @safe_call
    def count(self, limit=None): #TODO is this right?
        results = self._get_results()
        if limit is not None:
            results = results[:limit]
        return len(results)

    @safe_call
    def delete(self):

	db_table = self.query.get_meta().db_table
	results = self._get_results()
	
	pipeline = self._collection.pipeline(transaction = False)
	for res in results:
		pipeline.hgetall(get_hash_key(self.db_name,db_table,res))
	hmaps_ret = pipeline.execute()
	hmaps = ((results[n],hmaps_ret[n]) for n in range(len(hmaps_ret)))

	pipeline = self._collection.pipeline(transaction = False)
	for res,hmap in hmaps:
		pipeline.delete(get_hash_key(self.db_name,db_table,res))
		for field,val in hmap.iteritems():
			val = unpickle(val)
			if val is not None:
				#INDEXES
				if field in self.indexes_for_model or self.connection.exact_all:
					try:
						indexes_for_field = self.indexes_for_model[field]
					except KeyError:
						indexes_for_field = ()
					if 'exact' not in indexes_for_field and self.connection.exact_all:
						indexes_for_field += 'exact',
					delete_indexes(	field,
							val,
							indexes_for_field,
							pipeline,
							get_hash_key(self.db_name,db_table,res),
							db_table,
							res,
							self.db_name,
							)
		pipeline.srem(self.db_name+'_'+db_table+'_ids' ,res)
	pipeline.execute()


    @safe_call
    def order_by(self, ordering):
        if len(ordering) > 1:
		raise DatabaseError('Only one order is allowed')
        for order in ordering:
            if order.startswith('-'):
                order, direction = order[1:], 'desc'
            else:
                direction = 'asc'
            if order == self.query.get_meta().pk.column:
                order = '_id'
            else:
		pass #raise DatabaseError('You can only order by PK') TODO check when order index support is active
            self._ordering.append((order, direction))
        return self

    @safe_call
    def add_filter(self, column, lookup_type, negated, db_type, value):
	"""add filter
		used by default add_filters implementation
	
	"""
	#print "ADD FILTER  --  ",column, lookup_type, negated, db_type, value
	if column == self.query.get_meta().pk.column:
		if lookup_type in ('exact','in'):
			#print "cisiamo"
			#print "db_query?"
			#print self.db_query
			try:
				self.db_query[column][lookup_type]
				raise DatabaseError("You can't apply multiple AND filters " #Double filter on pk
                                        "on the primary key. "
                                        "Did you mean __in=[...]?")

			except KeyError:
				self.db_query.update({column:{lookup_type:value}})
	
	else:
		if lookup_type in ('exact','in'):
			if not self.connection.exact_all and 'exact' not  in self.indexes_for_model.get(column,()):
				raise DatabaseError('Lookup %s on column %s is not allowed (have you tried redis_indexes? )' % (lookup_type,column))
			else:self.db_query.update({column:{lookup_type:value}})
		else:
			if lookup_type  in self.indexes_for_model.get(column,()):
				self.db_query.update({column:{lookup_type:value}})
			
			else:
				raise DatabaseError('Lookup %s on column %s is not allowed (have you tried redis_indexes? )' % (lookup_type,column))
        

    def _get_results(self):
	"""
	see self.db_query, lookup parameters format: {'column': {lookup:value}}
	
	"""
	pk_column = self.query.get_meta().pk.column
	db_table = self.query.get_meta().db_table	
	
	results = self._collection.smembers(self.db_name+'_'+db_table+'_ids')


	for column,filteradd in self.db_query.iteritems():
		lookup,value = filteradd.popitem()#TODO tuple better?

		if pk_column == column:
			if lookup == 'in': #TODO meglio??
				results = results & set(value)   #IN filter
			elif lookup == 'exact':
				results = results & set([value,])
				
		else:
			if lookup == 'exact':
				results = results & self._collection.smembers(get_set_key(self.db_name,db_table,column,value))
			elif lookup == 'in': #ListField or empty
				tempset = set()
				for v in value:
					tempset = tempset.union(self._collection.smembers(get_set_key(self.db_name,db_table,column,v) ) )
				results = results & tempset
			else:
				tempset = filter_with_index(lookup,value,self._collection,db_table,column,self.db_name)
				if tempset is not None:
					results = results & tempset
				else:
					results = set()
								

        if self._ordering:
	    if self._ordering[0][1] == 'desc': 
		results.reverse()
	
	if self.query.low_mark > 0 and self.query.high_mark is not None:
		results = list(results)[self.query.low_mark:self.query.high_mark]
        elif self.query.low_mark > 0:

            results = list(results)[self.query.low_mark:]

        elif self.query.high_mark is not None:
            results = list(results)[:self.query.high_mark]

        return list(results)

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

    @safe_call # see #7
    def convert_value_for_db(self, db_type, value):
	#print db_type,'   ',value
        if db_type is None or value is None:
            return value

        db_type, db_subtype = self._split_db_type(db_type)
        if db_subtype is not None:
            if isinstance(value, (set, list, tuple)):
                
                return [self.convert_value_for_db(db_subtype, subvalue)
                        for subvalue in value]
            elif isinstance(value, dict):
                return dict((key, self.convert_value_for_db(db_subtype, subvalue))
                            for key, subvalue in value.iteritems())

        if isinstance(value, (set, list, tuple)):
            # most likely a list of ObjectIds when doing a .delete() query
            return [self.convert_value_for_db(db_type, val) for val in value]

        if db_type == 'objectid':
            return value
        return value

    @safe_call # see #7
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
        #TODO multi db
	return self.connection.db_connection
    @property
    def db_name(self):
        return self.connection.db_name

    def _save(self, data, return_id=False):

	db_table = self.query.get_meta().db_table
	indexes = get_indexes()
	indexes_for_model =  indexes.get(self.query.model,{})

	pipeline = self._collection.pipeline(transaction = False)

	h_map = {}
	h_map_old = {}

	if '_id' in data:
		pk = data['_id']
		new = False
		h_map_old = self._collection.hgetall(get_hash_key(self.db_name,db_table,pk))
	else:
		pk = self._collection.incr(self.db_name+'_'+db_table+"_id")
		new = True		
	
	for key,value in data.iteritems():
		
		if new:
			old = None
			h_map[key] = pickle.dumps(value)			
		else:
			if key == "_id": continue
			old = pickle.loads(h_map_old[key])

			if old != value:
				h_map[key] = pickle.dumps(value)

		if key in indexes_for_model or self.connection.exact_all:
			try:
				indexes_for_field = indexes_for_model[key]
			except KeyError:
				indexes_for_field = ()
			if 'exact' not in indexes_for_field and self.connection.exact_all:
				indexes_for_field += 'exact',
			create_indexes(	key,
					value,
					old,
					indexes_for_field,
					pipeline,
					db_table+'_'+str(pk),
					db_table,
					pk,
					self.db_name,
					)
	
        if '_id' not in data: pipeline.sadd(self.db_name+'_'+db_table+"_ids" ,pk)
	
	pipeline.hmset(get_hash_key(self.db_name,db_table,pk),h_map)			
	pipeline.execute()
        if return_id:
            return unicode(pk)

    def execute_sql(self, result_type=MULTI):
        """
        Handles aggregate/count queries
        """
	
	
	raise NotImplementedError('Not implemented')
	

class SQLInsertCompiler(NonrelInsertCompiler, SQLCompiler):
    @safe_call
    def insert(self, data, return_id=False):
        pk_column = self.query.get_meta().pk.column
        try:
            data['_id'] = data.pop(pk_column)
        except KeyError:
            pass
        return self._save(data, return_id)

class SQLUpdateCompiler(NonrelUpdateCompiler, SQLCompiler):
    pass
class SQLDeleteCompiler(NonrelDeleteCompiler, SQLCompiler):
    pass

########NEW FILE########
__FILENAME__ = creation
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
        """Create Indexes for field in model. 

        Indexes are created rundime, no need for this.
	Returns an empty List. (Django Compatibility)
        """

        """if field.db_index:
            kwargs = {}
            opts = model._meta
            col = getattr(self.connection.db_connection, opts.db_table)
            descending = getattr(opts, "descending_indexes", [])
            direction =  (field.attname in descending and -1) or 1
            kwargs["unique"] = field.unique
            col.ensure_index([(field.name, direction)], **kwargs)"""
        return []

    def index_fields_group(self, model, group, **kwargs):
        """Create indexes for fields in group that belong to model.
            TODO: Necessary?
        """
        """if not isinstance(group, dict):
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
        col.ensure_index(checked_fields, **group)"""

    def sql_indexes_for_model(self, model, *args, **kwargs):
        """Creates ``model`` indexes.

        Probably not necessary 
	TODO Erase?
        """
        """if not model._meta.managed or model._meta.proxy:
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
            self.index_fields_group(model, group)"""
        return []

    def sql_create_model(self, model, *args, **kwargs):
        """TODO delete...
        """
	return [], {}
        

    def set_autocommit(self):
        "Make sure a connection is in autocommit mode."
        pass

    def create_test_db(self, verbosity=1, autoclobber=False):
        if self.connection.settings_dict.get('TEST_NAME'):
            test_database_name = self.connection.settings_dict['TEST_NAME']
        elif 'NAME' in self.connection.settings_dict:
            test_database_name = TEST_DATABASE_PREFIX + self.connection.settings_dict['NAME']
        elif 'DATABASE_NAME' in self.connection.settings_dict:
            if self.connection.settings_dict['DATABASE_NAME'].startswith(TEST_DATABASE_PREFIX):
                test_database_name = self.connection.settings_dict['DATABASE_NAME']
            else:
                test_database_name = TEST_DATABASE_PREFIX + \
                  self.connection.settings_dict['DATABASE_NAME']
        else:
            raise ValueError("Name for test database not defined")

        self.connection.settings_dict['NAME'] = test_database_name
        # This is important. Here we change the settings so that all other code
        # thinks that the chosen database is now the test database. This means
        # that nothing needs to change in the test code for working with
        # connections, databases and collections. It will appear the same as
        # when working with non-test code.

        # In this phase it will only drop the database if it already existed
        # which could potentially happen if the test database was created but
        # was never dropped at the end of the tests
        self._drop_database(test_database_name)

        return test_database_name

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
	
        """
        for k in self.connection._cursor().keys(database_name+'*'):
		del self.connection._cursor()[k]

########NEW FILE########
__FILENAME__ = index_utils
from django.conf import settings
from django.utils.importlib import import_module
from md5 import md5
from redis_entity import *
_MODULE_NAMES = getattr(settings, 'REDIS_SETTINGS_MODULES', ())
from redis.exceptions import WatchError

#TODO update might overwrite field indexes

INDEX_KEY_INFIX = "redis_index"

SWITH_INDEX_SEPARATOR = '\x00'

isiterable = lambda obj: getattr(obj, '__iter__', False)

import datetime

def val_for_insert(d):
	if isinstance(d,unicode):
	  d = d
	elif isinstance(d,basestring) : d = unicode(d.decode('utf-8'))
	else: d = unicode(d)
        return d


def get_indexes():
        indexes = {}
        for name in _MODULE_NAMES:
            try:
                indexes.update(import_module(name).INDEXES)
            except (ImportError, AttributeError):
                pass
        
	return indexes

def prepare_value_for_index(index,val):
	if index == 'startswith': return val
	if index == 'istartswith': return val.lower()
	if index == 'endswith': return val[::-1]
	if index == 'iendswith': return val.lower()[::-1]
	if index in ('gt','gte','lt','lte'):
		if isinstance(val,datetime.datetime):
			return "%04d%02d%02d%02d%02d" % (val.year,val.month,val.day,val.hour,val.minute)
		if isinstance(val,datetime.time):
			return "%02d%02d" % (val.hour,val.minute)
		if isinstance(val,datetime.date):
			return "%04d%02d%02d" % (val.year,val.month,val.day)
		if isinstance(val,int):
			return "%20d" % val
	return val
	


def create_indexes(column,data,old,indexes,conn,hash_record,table,pk,db_name):
		for index in indexes:
			if index in ('startswith','istartswith','endswith','iendswith','gt','gte','lt','lte'):
				if old is not None:
					if not isiterable(old):
						old = (old,)	
					for d in old:
						d = prepare_value_for_index(index,d)
						conn.zrem(get_zset_index_key(db_name,table,INDEX_KEY_INFIX,column,index),
										d+SWITH_INDEX_SEPARATOR+str(pk))
				if not isiterable(data):
					data = (data,)
				for d in data:
					d = val_for_insert(d)
					d = prepare_value_for_index(index,d)						
					conn.zadd(get_zset_index_key(db_name,table,INDEX_KEY_INFIX,column,index),
										d+SWITH_INDEX_SEPARATOR+str(pk),0)
			if index == 'exact':
				if old is not None:
					if not isiterable(old):
						old = (old,)	
					for d in old:
						conn.srem(get_set_key(db_name,table,column,d),str(pk))
				if not isiterable(data):
					data = (data,)
				for d in data:
					d = val_for_insert(d)
					conn.sadd(get_set_key(db_name,table,column,d),pk)


def delete_indexes(column,data,indexes,conn,hash_record,table,pk,db_name):
		for index in indexes:
			if index in ('startswith','istartswith','endswith','iendswith','gt','gte','lt','lte'):
				if not isiterable(data):
					data = (data,)
				for d in data:
					d = val_for_insert(d)
					d = prepare_value_for_index(index,d)
					conn.zrem(get_zset_index_key(db_name,table,INDEX_KEY_INFIX,column,index),
									d+SWITH_INDEX_SEPARATOR+str(pk))
			if index == 'exact':
				if not isiterable(data):
					data = (data,)
				for d in data:
					d = val_for_insert(d)
					conn.srem(get_set_key(db_name,table,column,d),str(pk))

def filter_with_index(lookup,value,conn,table,column,db_name):
	if lookup in ('startswith','istartswith','endswith','iendswith',):
		value = val_for_insert(value)
		v = prepare_value_for_index(lookup,value)
		
		#v2 = v[:-1]+chr(ord(v[-1])+1) #last letter=next(last letter)
		key = get_zset_index_key(db_name,table,INDEX_KEY_INFIX,column,lookup)

		pipeline = conn.pipeline()		
		conn.zadd(key,v,0)
		#pipeline.zadd(key,v2,0)
		#pipeline.execute()
		while True:
			try:
				conn.watch(key)
				up = conn.zrank(key,v)
				#down = conn.zrank(key,v2)

				pipeline.zrange(key,up+1,-1)#down-1)
				pipeline.zrem(key,v)
				#pipeline.zrem(key,v2)
		
				l = pipeline.execute()
				#print l
				r = l[0]
				#print l
				#print 'erre: ',r
				#print 'second pipeline',pipeline.execute()
				ret = set()
				for i in r:
					i = unicode(i.decode('utf8'))
					if i.startswith(v):
						splitted_string = i.split(SWITH_INDEX_SEPARATOR)
						if len(splitted_string) > 1:
							ret.add(splitted_string[-1])
					else:
						break
				return ret
			except WatchError:
				pass
#		print pipeline.execute()

	elif lookup in ('gt','gte','lt','lte'):
		value = val_for_insert(value)
		v = prepare_value_for_index(lookup,value)
		key = get_zset_index_key(db_name,table,INDEX_KEY_INFIX,column,lookup)
		pipeline = conn.pipeline()
		conn.zadd(key,v,0)
		while True:
			try:
				conn.watch(key)
				up = conn.zrank(key,v)
				if lookup in ('lt','lte'):
					pipeline.zrange(key,0,up+1)
				else:
					pipeline.zrange(key,up+1,-1)
				pipeline.zrem(key,v)
				l = pipeline.execute()
				r = l[0]
				ret = set()
				for i in r:
					i = unicode(i.decode('utf8'))
					splitted_string = i.split(SWITH_INDEX_SEPARATOR)
					if len(splitted_string) > 0 and\
						 (lookup in ('gte','lte') or\
							"".join(splitted_string[:-1]) != value):
							ret.add(splitted_string[-1])
				return ret
			except WatchError:
				pass
	else:
		raise Exception('Lookup type not supported') #TODO check at index creation?
	


# 

########NEW FILE########
__FILENAME__ = redis_entity
from django.db.models.fields import FieldDoesNotExist
from md5 import md5
import pickle

class RedisEntity(object):
	def __init__(self,e_id,connection,db_table, pkcolumn, querymeta, db_name,empty):
		self.id = e_id
		self.connection = connection
		self.db_table = db_table
		self.pkcolumn = pkcolumn
		self.querymeta = querymeta
		self.db_name = db_name
		self.empty = empty
		if not empty:
			self.data = self.connection.hgetall(get_hash_key(self.db_name,self.db_table,self.id))
		
		
	def get(self,what,value):
		
		if self.empty: return ''
		if what in self.data:
			#print self.data,self.data[what]
			return unpickle(self.data[what])
		if what == self.pkcolumn:
			return self.id
		else:
			return unpickle(self.connection.hget(get_hash_key(self.db_name,self.db_table,self.id), what))				


def split_db_type(db_type):
	#TODO move somewhere else
        try:
            db_type, db_subtype = db_type.split(':', 1)
        except ValueError:
            db_subtype = None
        return db_type, db_subtype

def get_hash_key(db_name,db_table,pk):
	return db_name+'_'+db_table+'_'+str(pk)

def get_zset_index_key(db_name,db_table,infix,column,index):
	return db_name+'_'+db_table +'_' + infix + '_' + column + '_'+index

def get_list_key(db_name,db_table,key,pk):
	return db_name+'_'+db_table+'_'+key+'_'+str(pk)


def get_set_key(db_name,db_table,key,value):
	return db_name+'_'+db_table+'_'+key+'_'+hash_for_redis(value)

def unpickle(val):
	if val is None:
		return None
	else:
		return pickle.loads(val)

def enpickle(val):
	if val is None:
		return None
	else:
		return pickle.dumps(val)


def hash_for_redis(val):
	if isinstance(val,unicode):
		return md5(val.encode('utf-8')).hexdigest()
	return md5(str(val)).hexdigest()

########NEW FILE########
__FILENAME__ = redis_transaction
"""
This module implements a transaction manager that can be used to define
transaction handling in a request or view function. It is used by transaction
control middleware and decorators.

The transaction manager can be in managed or in auto state. Auto state means the
system is using a commit-on-save strategy (actually it's more like
commit-on-change). As soon as the .save() or .delete() (or related) methods are
called, a commit is made.

Managed transactions don't do those commits, but will need some kind of manual
or implicit commits or rollbacks.
"""
import sys

try:
    from functools import wraps
except ImportError:
    from django.utils.functional import wraps  # Python 2.4 fallback.

from django.conf import settings
from django.db import connections, DEFAULT_DB_ALIAS


class RedisTransactionManagementError(Exception):
    """
    This exception is thrown when something bad happens with transaction
    management.
    """
    pass

def redis_enter_transaction_management(managed=True, using=None):
    """
    Enters transaction management for a running thread. It must be balanced with
    the appropriate redis_leave_transaction_management call, since the actual state is
    managed as a stack.

    The state and dirty flag are carried over from the surrounding block or
    from the settings, if there is no surrounding block (dirty is always false
    when no current block is running).
    """
    if using is None:
        using = DEFAULT_DB_ALIAS
    connection = connections[using]
    connection.redis_enter_transaction_management(managed)

def redis_leave_transaction_management(using=None):
    """
    Leaves transaction management for a running thread. A dirty flag is carried
    over to the surrounding block, as a commit will commit all changes, even
    those from outside. (Commits are on connection level.)
    """
    if using is None:
        using = DEFAULT_DB_ALIAS
    connection = connections[using]
    connection.redis_leave_transaction_management(using)

def is_dirty(using=None):
    """
    Returns True if the current transaction requires a commit for changes to
    happen.
    """
    if using is None:
        using = DEFAULT_DB_ALIAS
    connection = connections[using]
    return connection.is_dirty()

def set_dirty(using=None):
    """
    Sets a dirty flag for the current thread and code streak. This can be used
    to decide in a managed block of code to decide whether there are open
    changes waiting for commit.
    """
    if using is None:
        using = DEFAULT_DB_ALIAS
    connection = connections[using]
    connection.set_dirty()

def set_clean(using=None):
    """
    Resets a dirty flag for the current thread and code streak. This can be used
    to decide in a managed block of code to decide whether a commit or rollback
    should happen.
    """
    if using is None:
        using = DEFAULT_DB_ALIAS
    connection = connections[using]
    connection.set_clean()

def clean_savepoints(using=None):
    if using is None:
        using = DEFAULT_DB_ALIAS
    connection = connections[using]
    connection.clean_savepoints()

def is_managed(using=None):
    """
    Checks whether the transaction manager is in manual or in auto state.
    """
    if using is None:
        using = DEFAULT_DB_ALIAS
    connection = connections[using]
    return connection.is_managed()

def managed(flag=True, using=None):
    """
    Puts the transaction manager into a manual state: managed transactions have
    to be committed explicitly by the user. If you switch off transaction
    management and there is a pending commit/rollback, the data will be
    commited.
    """
    if using is None:
        using = DEFAULT_DB_ALIAS
    connection = connections[using]
    connection.redis_managed(flag)

def commit_unless_managed(using=None):
    """
    Commits changes if the system is not in managed transaction mode.
    """
    if using is None:
        using = DEFAULT_DB_ALIAS
    connection = connections[using]
    connection.commit_unless_managed()

def rollback_unless_managed(using=None):
    """
    Rolls back changes if the system is not in managed transaction mode.
    """
    if using is None:
        using = DEFAULT_DB_ALIAS
    connection = connections[using]
    connection.rollback_unless_managed()

def commit(using=None):
    """
    Does the commit itself and resets the dirty flag.
    """
    if using is None:
        using = DEFAULT_DB_ALIAS
    connection = connections[using]
    connection.redis_commit()

def rollback(using=None):
    """
    This function does the rollback itself and resets the dirty flag.
    """
    if using is None:
        using = DEFAULT_DB_ALIAS
    connection = connections[using]
    connection.rollback()

def savepoint(using=None):
    """
    Creates a savepoint (if supported and required by the backend) inside the
    current transaction. Returns an identifier for the savepoint that will be
    used for the subsequent rollback or commit.
    """
    if using is None:
        using = DEFAULT_DB_ALIAS
    connection = connections[using]
    return connection.savepoint()

def savepoint_rollback(sid, using=None):
    """
    Rolls back the most recent savepoint (if one exists). Does nothing if
    savepoints are not supported.
    """
    if using is None:
        using = DEFAULT_DB_ALIAS
    connection = connections[using]
    connection.savepoint_rollback(sid)

def savepoint_redis_commit(sid, using=None):
    """
    Commits the most recent savepoint (if one exists). Does nothing if
    savepoints are not supported.
    """
    if using is None:
        using = DEFAULT_DB_ALIAS
    connection = connections[using]
    connection.savepoint_redis_commit(sid)

##############
# DECORATORS #
##############

class RedisTransaction(object):
    """
    Acts as either a decorator, or a context manager.  If it's a decorator it
    takes a function and returns a wrapped function.  If it's a contextmanager
    it's used with the ``with`` statement.  In either event entering/exiting
    are called before and after, respectively, the function/block is executed.

    autocommit, commit_on_success, and commit_manually contain the
    implementations of entering and exiting.
    """
    def __init__(self, entering, exiting, using):
        self.entering = entering
        self.exiting = exiting
        self.using = using

    def __enter__(self):
        self.entering(self.using)

    def __exit__(self, exc_type, exc_value, traceback):
        self.exiting(exc_value, self.using)

    def __call__(self, func):
        @wraps(func)
        def inner(*args, **kwargs):
            # Once we drop support for Python 2.4 this block should become:
            # with self:
            #     func(*args, **kwargs)
            self.__enter__()
            try:
                res = func(*args, **kwargs)
            except:
                self.__exit__(*sys.exc_info())
                raise
            else:
                self.__exit__(None, None, None)
                return res
        return inner

def _transaction_func(entering, exiting, using):
    """
    Takes 3 things, an entering function (what to do to start this block of
    transaction management), an exiting function (what to do to end it, on both
    success and failure, and using which can be: None, indiciating using is
    DEFAULT_DB_ALIAS, a callable, indicating that using is DEFAULT_DB_ALIAS and
    to return the function already wrapped.

    Returns either a RedisTransaction objects, which is both a decorator and a
    context manager, or a wrapped function, if using is a callable.
    """
    # Note that although the first argument is *called* `using`, it
    # may actually be a function; @autocommit and @autoredis_commit('foo')
    # are both allowed forms.
    if using is None:
        using = DEFAULT_DB_ALIAS
    if callable(using):
        return RedisTransaction(entering, exiting, DEFAULT_DB_ALIAS)(using)
    return RedisTransaction(entering, exiting, using)


def autoredis_commit(using=None):
    """
    Decorator that activates commit on save. This is Django's default behavior;
    this decorator is useful if you globally activated transaction management in
    your settings file and want the default behavior in some view functions.
    """
    def entering(using):
        redis_enter_transaction_management(managed=False, using=using)
        managed(False, using=using)

    def exiting(exc_value, using):
        redis_leave_transaction_management(using=using)

    return _transaction_func(entering, exiting, using)

def commit_on_success(using=None):
    """
    This decorator activates commit on response. This way, if the view function
    runs successfully, a commit is made; if the viewfunc produces an exception,
    a rollback is made. This is one of the most common ways to do transaction
    control in Web apps.
    """
    def entering(using):
        redis_enter_transaction_management(using=using)
        managed(True, using=using)

    def exiting(exc_value, using):
        try:
            if exc_value is not None:
                if is_dirty(using=using):
                    rollback(using=using)
            else:
                if is_dirty(using=using):
                    try:
                        redis_commit(using=using)
                    except:
                        rollback(using=using)
                        raise
        finally:
            redis_leave_transaction_management(using=using)

    return _transaction_func(entering, exiting, using)

def commit_manually(using=None):
    """
    Decorator that activates manual transaction control. It just disables
    automatic transaction control and doesn't do any commit/rollback of its
    own -- it's up to the user to call the commit and rollback functions
    themselves.
    """
    def entering(using):
        redis_enter_transaction_management(using=using)
        #managed(True, using=using)

    def exiting(exc_value, using):
        redis_leave_transaction_management(using=using)

    return _transaction_func(entering, exiting, using)

########NEW FILE########
__FILENAME__ = serializer
from django.db import models
from django.db.models.query import QuerySet
from django.utils.functional import SimpleLazyObject
from django.utils.importlib import import_module

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
__FILENAME__ = dbindexes
# dbindexes.py:
import dbindexer
dbindexer.autodiscover()

########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python
from django.core.management import execute_manager
try:
    import settings # Assumed to be in the same directory.
except ImportError:
    import sys
    sys.stderr.write("Error: Can't find the file 'settings.py' in the directory containing %r. It appears you've customized things.\nYou'll have to run django-admin.py, passing it your settings module.\n(If the file settings.py does indeed exist, it's causing an ImportError somehow.)\n" % __file__)
    sys.exit(1)

if __name__ == "__main__":
    execute_manager(settings)

########NEW FILE########
__FILENAME__ = settings
# Initialize App Engine and import the default settings (DB backend, etc.).
# If you want to use a different backend you have to remove all occurences
# of "djangoappengine" from this file.
#from djangoappengine.settings_base import *
import django.conf.global_settings as DEFAULT_SETTINGS
import os

SECRET_KEY = '=r-$b*8hglm+858&9t043hlm6-&6-3d3vfc4((7yd0dbrakhvi'

DATABASES = {
    'default': {
        'ENGINE': 'django_redis_engine',
        'NAME': '',
        'USER': '',
        'PASSWORD': '',
        'HOST': 'localhost',
        'PORT': 6379,
       
    }
}


DBINDEXER_SITECONF = 'dbindexes'

DBINDEXER_BACKENDS = (
    'dbindexer.backends.FKNullFix',
    'dbindexer.backends.BaseResolver',
    'dbindexer.backends.InMemoryJOINResolver',
)



INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'djangotoolbox',
    'testapp',

)

# This test runner captures stdout and associates tracebacks with their
# corresponding output. Helps a lot with print-debugging.
TEST_RUNNER = 'djangotoolbox.test.CapturingTestSuiteRunner'

TIME_ZONE = 'America/Chicago'

LANGUAGE_CODE = 'en-us'

ADMIN_MEDIA_PREFIX = '/media/admin/'


MEDIA_URL = '/media/'
TEMPLATE_DIRS = (
     os.path.join(os.path.dirname(__file__), 'templates'),
     os.path.join(os.path.dirname(__file__), 'unimia/templates'),

)


REDIS_SETTINGS_MODULES = ('testapp.redis_settings',)


ROOT_URLCONF = 'urls'

SITE_ID = 1

#GAE_SETTINGS_MODULES = (
#    'unimia.gae_settings',
#)

TEMPLATE_CONTEXT_PROCESSORS = DEFAULT_SETTINGS.TEMPLATE_CONTEXT_PROCESSORS + (
	'django.core.context_processors.request',
)

MIDDLEWARE_CLASSES = (
 'django.middleware.common.CommonMiddleware',
 'django.contrib.sessions.middleware.SessionMiddleware',
 'django.middleware.csrf.CsrfViewMiddleware',
 'django.contrib.auth.middleware.AuthenticationMiddleware',
 'dbindexer.middleware.DBIndexerMiddleware',
)   
#) + DEFAULT_SETTINGS.MIDDLEWARE_CLASSES


# Activate django-dbindexer if available
try:
	import dbindexer
	DATABASES['native'] = DATABASES['default']
	DATABASES['default'] = {'ENGINE': 'dbindexer', 'TARGET': 'native'}
	INSTALLED_APPS += ('dbindexer',)
except ImportError,e:
	import traceback
	traceback.print_exc(20)


DEBUG = True

########NEW FILE########
__FILENAME__ = dbindexes
from models import Post
from dbindexer.api import register_index


register_index(Post, {'title': 'contains',})

########NEW FILE########
__FILENAME__ = forms
from django import forms
from models import *


class MyForm(forms.ModelForm):
	class Meta:
		model = Post


class AnswerForm(forms.ModelForm):
	class Meta:
		model = Answer
		exclude = ("post")


########NEW FILE########
__FILENAME__ = models
from django.db import models
from django.contrib.auth.models import User
# Create your models here.

class Post(models.Model):
	title = models.CharField(max_length = 100)
	text = models.TextField()
	time = models.DateTimeField(auto_now_add = True,auto_now = True)

class Answer(models.Model):
	text = models.TextField()
	post = models.ForeignKey(Post)

########NEW FILE########
__FILENAME__ = redis_settings
from models import Post
from django.contrib.sessions.models import Session


INDEXES = {
    Post: {'idxf_title_l_contains': ('startswith',),
	'text':('iendswith',),
	'title':('startswith','endswith'),
	'time':('gt','lte'),
	},
    Session : {'expire_date' : ('gt',)
	},
    
}


########NEW FILE########
__FILENAME__ = tests
#-*- encoding:utf-8 -*-

from django.test import TestCase
from models import *
from md5 import md5
import random

from django_redis_engine import redis_transaction
from django.db import transaction
class SimpleTest(TestCase):

    def test_update_and_filters(self):
	"""
	test effects of updates on filters
	"""
	post = Post.objects.create(
                                text = "to be updated text",
                                title = "to be updated title"
                                )
	post.text = "updated text"
	post.save()
	posts = Post.objects.filter(text = "to be updated text")
	self.failUnlessEqual(len(posts), 0)
	posts = Post.objects.filter(text = "updated text")
	self.failUnlessEqual(len(posts), 1)
	post.title = "updated title"
	post.save()
	posts = Post.objects.filter(title__contains = "to be updated title")
        self.failUnlessEqual(len(posts), 0)
        posts = Post.objects.filter(title__contains = "updated title")
        self.failUnlessEqual(len(posts), 1)
	post.delete()
	
    def atest_insert_transaction(self):
	"""
	stress test, used to find out how much network latency
	affects performance using transactions.
	"""
	n = 100
	ng = 100
	ngc = 100
	l = []
	#print redis_transaction.commit_manually(using = 'native')
	#print transaction.commit_manually()
	with redis_transaction.commit_manually(using = 'native'):
		print "begin"
		for i in range(n):
			tit = md5(str(random.random())+str(i)).hexdigest()
			l.append(tit)
			Post.objects.create(
					title = tit,
					text = " ".join(
							[md5(
								str(random.random())+\
								str(t)+\
								str(i)).hexdigest() for t in range(20)]
							)
					)
		redis_transaction.commit()
	for i in range(ng):
		p = Post.objects.get(title = l[random.randint(0,n-1)] )
	for i in range(ngc):
		Post.objects.filter(title__contains = l[random.randint(0,n-1)])
		#self.failUnlessEqual(len(posts), 1)

    def test_add_post_answers_and_filters(self):
        """
        Create some posts, create answers to them,
	test contains filter on post title
	test startswith filter on post title
	test endswith filter on post title
	test iendswith filter on post text
	test exact filter on all fields
	test gt and lte filters
	test deletion of objects and indexes 
        """
        post1 = Post.objects.create(
				text = "text1",
				title = "title1"
				)

        post2 = Post.objects.create(
				text = "text2",
				title = "title2"
				)
        post3 = Post.objects.create(
				text = "RrRQqà",
				title = "AaABbB"
				)
	answer1 = Answer.objects.create(
				text= "answer1 to post 1",
				post = post1
				)
	answer2 = Answer.objects.create(
				text= "answer2 to post 1",
				post = post1
				)
	answer3 = Answer.objects.create(
				text= "answer1 to post 2",
				post = post2
				)
	posts = Post.objects.all()
	self.failUnlessEqual(len(posts), 3)
	posts = Post.objects.filter(title__contains = 'title')
	self.failUnlessEqual(len(posts), 2)
	p = Post.objects.get(title = 'title1')
	self.failUnlessEqual(p.pk, post1.pk)
	p = Post.objects.get(text = 'text2')
	self.failUnlessEqual(p.pk, post2.pk)
	a = Answer.objects.get(text = 'answer2 to post 1')
	self.failUnlessEqual(a.pk, answer2.pk)
	
	p.delete()
	posts = Post.objects.all()
        self.failUnlessEqual(len(posts), 2)
        posts = Post.objects.filter(title__contains = 'title')
        self.failUnlessEqual(len(posts), 1)
        posts = Post.objects.filter(title__startswith = 'Aa')
        self.failUnlessEqual(len(posts), 1)
        posts = Post.objects.filter(title__startswith = 'AA')
        self.failUnlessEqual(len(posts), 0)

        posts = Post.objects.filter(title__endswith = 'bB')
        self.failUnlessEqual(len(posts), 1)

        posts = Post.objects.filter(title__endswith = 'BB')
        self.failUnlessEqual(len(posts), 0)
	posts = Post.objects.filter(text__iendswith = 'qqà')
        self.failUnlessEqual(len(posts), 1)
        posts = Post.objects.filter(text__iendswith = 'QQÀ')
        self.failUnlessEqual(len(posts), 1)

	
	a.delete()
	answers = Answer.objects.filter(text = 'answer2 to post 1')
	self.failUnlessEqual(len(answers), 0)
	
	import datetime
	posts = Post.objects.filter(text__iendswith = 'QQÀ',
				time__gt = datetime.datetime.now() - datetime.timedelta(minutes = 10))
	self.failUnlessEqual(len(posts), 1)
	posts = Post.objects.filter(time__gt = datetime.datetime.now() - datetime.timedelta(minutes = 10))
	self.failUnlessEqual(len(posts), 2)

	posts = Post.objects.filter(time__lte = posts[0].time)
	self.failUnlessEqual(len(posts), 1)

	posts = Post.objects.filter(time__lte = posts[0].time + datetime.timedelta(minutes = 10))
	self.failUnlessEqual(len(posts), 2)






########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import *


urlpatterns = patterns('',


url(r'^add_post/$', 'testapp.views.add_post', {},name = 'testapp_add_post'),

url(r'^add_answer/(?P<post_id>\d+)/$', 'testapp.views.add_answer', {},name = 'testapp_add_answer'),

url(r'^posts/$', 'testapp.views.posts', {},name = 'testapp_posts'),

)

########NEW FILE########
__FILENAME__ = views
# Create your views here.
from models import Post, Answer
from django.shortcuts import render_to_response
from forms import *
from django.template import RequestContext
from django.http import HttpResponseRedirect

def add_post(request,):
  #VIEW CODE  
  if request.method == 'POST':
    form = MyForm(request.POST)
    if form.is_valid():
      # Process the data in form.cleaned_data
      form.save()
      return HttpResponseRedirect('/posts/')
  else:
    form = MyForm()
  ret_dict = {
              'form':form,
              } 
  return render_to_response("testapp/add_post.html", 
                        ret_dict,
                        context_instance = RequestContext(request),)



def add_answer(request,post_id):
  #VIEW CODE  
  if request.method == 'POST':
    form = AnswerForm(request.POST)
    post = Post.objects.get(pk = post_id)
    if form.is_valid():
      # Process the data in form.cleaned_data
      form.instance.post = post
      form.save()
      return HttpResponseRedirect('/posts/')
  else:
    form = AnswerForm()
  ret_dict = {
              'form':form,
              } 
  return render_to_response("testapp/add_answer.html", 
                        ret_dict,
                        context_instance = RequestContext(request),)



def posts(request,):
  ret_dict = {}
  if request.method == 'POST' and request.POST['title_filter'] is not None and request.POST['title_filter'] != '':
    posts = Post.objects.filter(title__contains = request.POST['title_filter'])
    ret_dict['filter'] = request.POST['title_filter']
  else:
    posts = Post.objects.all()
  
  ret_dict['posts'] = posts
    
  return render_to_response("testapp/posts.html", 
                        ret_dict,
                        context_instance = RequestContext(request),)



########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import *

#handler500 = 'djangotoolbox.errorviews.server_error'

urlpatterns = patterns('',

    ('', include('testapp.urls')),


)

########NEW FILE########
__FILENAME__ = __pkginfo__
#!/usr/bin/env python
# -*- coding: utf-8 -*-
import codecs
import django_redis_engine as distmeta

distname = 'django_redis_engine'
numversion = distmeta.__version__
version = '.'.join(map(str, numversion))
license = '2-clause BSD'
author = distmeta.__author__
author_email = distmeta.__contact__

short_desc = "A Redis django db backend."
long_desc = codecs.open('README.rst', 'r', 'utf-8').read()

install_requires = [ 'django>=1.2', 'djangotoolbox']
pyversions = ['2', '2.4', '2.5', '2.6', '2.7']
docformat = distmeta.__docformat__
include_dirs = []

########NEW FILE########
