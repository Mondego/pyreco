__FILENAME__ = base
#   Copyright 2010 BSN, Inc.
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

from django.db.utils import DatabaseError

from djangotoolbox.db.base import NonrelDatabaseFeatures, \
    NonrelDatabaseOperations, NonrelDatabaseWrapper, NonrelDatabaseClient, \
    NonrelDatabaseValidation, NonrelDatabaseIntrospection, \
    NonrelDatabaseCreation

import re
import time
from .creation import DatabaseCreation
from .introspection import DatabaseIntrospection
from .utils import CassandraConnection, CassandraConnectionError, CassandraAccessError
from thrift.transport import TTransport
from cassandra.ttypes import *


class DatabaseFeatures(NonrelDatabaseFeatures):
    string_based_auto_field = True
    
    def __init__(self, connection):
        super(DatabaseFeatures, self).__init__(connection)
        self.supports_deleting_related_objects = connection.settings_dict.get('CASSANDRA_ENABLE_CASCADING_DELETES', False)


class DatabaseOperations(NonrelDatabaseOperations):
    compiler_module = __name__.rsplit('.', 1)[0] + '.compiler'
    
    def pk_default_value(self):
        """
        Use None as the value to indicate to the insert compiler that it needs
        to auto-generate a guid to use for the id. The case where this gets hit
        is when you create a model instance with no arguments. We override from
        the default implementation (which returns 'DEFAULT') because it's possible
        that someone would explicitly initialize the id field to be that value and
        we wouldn't want to override that. But None would never be a valid value
        for the id.
        """
        return None
    
    def sql_flush(self, style, tables, sequence_list):
        for table_name in tables:
            self.connection.creation.flush_table(table_name)
        return ""
    
class DatabaseClient(NonrelDatabaseClient):
    pass

class DatabaseValidation(NonrelDatabaseValidation):
    pass

class DatabaseWrapper(NonrelDatabaseWrapper):
    def __init__(self, *args, **kwds):
        super(DatabaseWrapper, self).__init__(*args, **kwds)
        
        # Set up the associated backend objects
        self.features = DatabaseFeatures(self)
        self.ops = DatabaseOperations(self)
        self.client = DatabaseClient(self)
        self.creation = DatabaseCreation(self)
        self.validation = DatabaseValidation(self)
        self.introspection = DatabaseIntrospection(self)

        self.read_consistency_level = self.settings_dict.get('CASSANDRA_READ_CONSISTENCY_LEVEL', ConsistencyLevel.ONE)
        self.write_consistency_level = self.settings_dict.get('CASSANDRA_WRITE_CONSISTENCY_LEVEL', ConsistencyLevel.ONE)
        self.max_key_count = self.settings_dict.get('CASSANDRA_MAX_KEY_COUNT', 1000000)
        self.max_column_count = self.settings_dict.get('CASSANDRA_MAX_COLUMN_COUNT', 10000)
        self.column_family_def_defaults = self.settings_dict.get('CASSANDRA_COLUMN_FAMILY_DEF_DEFAULT_SETTINGS', {})

        self._db_connection = None
        self.determined_version = False
        
    def configure_connection(self, set_keyspace=False, login=False):
        
        if not self._db_connection.is_connected():
            self._db_connection.open(False, False)
            self.determined_version = False
            
        if not self.determined_version:
            # Determine which version of Cassandra we're connected to
            version_string = self._db_connection.get_client().describe_version()
            try:
                # FIXME: Should do some version check here to make sure that we're
                # talking to a cassandra daemon that supports the operations we require
                m = re.match('^([0-9]+)\.([0-9]+)\.([0-9]+)$', version_string)
                major_version = int(m.group(1))
                minor_version = int(m.group(2))
                patch_version = int(m.group(3))
                self.determined_version = True
            except Exception, e:
                raise DatabaseError('Invalid Thrift version string', e)
            
            # Determine supported features based on the API version
            self.supports_replication_factor_as_strategy_option = major_version >= 19 and minor_version >= 10
        
        if login:
            self._db_connection.login()
        
        if set_keyspace:
            try:
                self._db_connection.set_keyspace()
            except Exception, e:
                # Set up the default settings for the keyspace
                keyspace_def_settings = {
                    'name': self._db_connection.keyspace,
                    'strategy_class': 'org.apache.cassandra.locator.SimpleStrategy',
                    'strategy_options': {},
                    'cf_defs': []}
            
                # Apply any overrides for the keyspace settings
                custom_keyspace_def_settings = self.settings_dict.get('CASSANDRA_KEYSPACE_DEF_SETTINGS')
                if custom_keyspace_def_settings:
                    keyspace_def_settings.update(custom_keyspace_def_settings)
                
                # Apply any overrides for the replication strategy
                # Note: This could be done by the user using the 
                # CASSANDRA_KEYSPACE_DEF_SETTINGS, but the following customizations are
                # still supported for backwards compatibility with older versions of the backend
                strategy_class = self.settings_dict.get('CASSANDRA_REPLICATION_STRATEGY')
                if strategy_class:
                    keyspace_def_settings['strategy_class'] = strategy_class
                
                # Apply an override of the strategy options
                strategy_options = self.settings_dict.get('CASSANDRA_REPLICATION_STRATEGY_OPTIONS')
                if strategy_options:
                    if type(strategy_options) != dict:
                        raise DatabaseError('CASSANDRA_REPLICATION_STRATEGY_OPTIONS must be a dictionary')
                    keyspace_def_settings['strategy_options'].update(strategy_options)
                
                # Apply an override of the replication factor. Depending on the version of
                # Cassandra this may be applied to either the strategy options or the top-level
                # keyspace def settings
                replication_factor = self.settings_dict.get('CASSANDRA_REPLICATION_FACTOR')
                replication_factor_parent = keyspace_def_settings['strategy_options'] \
                    if self.supports_replication_factor_as_strategy_option else keyspace_def_settings
                if replication_factor:
                    replication_factor_parent['replication_factor'] = str(replication_factor)
                elif 'replication_factor' not in replication_factor_parent:
                    replication_factor_parent['replication_factor'] = '1'
                
                keyspace_def = KsDef(**keyspace_def_settings)
                self._db_connection.get_client().system_add_keyspace(keyspace_def)
                self._db_connection.set_keyspace()
                
    
    def get_db_connection(self, set_keyspace=False, login=False):
        if not self._db_connection:
            # Get the host and port specified in the database backend settings.
            # Default to the standard Cassandra settings.
            host = self.settings_dict.get('HOST')
            if not host or host == '':
                host = 'localhost'
                
            port = self.settings_dict.get('PORT')
            if not port or port == '':
                port = 9160
                
            keyspace = self.settings_dict.get('NAME')
            if keyspace == None:
                keyspace = 'django'
                
            user = self.settings_dict.get('USER')
            password = self.settings_dict.get('PASSWORD')
            
            # Create our connection wrapper
            self._db_connection = CassandraConnection(host, port, keyspace, user, password)
            
        try:
            self.configure_connection(set_keyspace, login)
        except TTransport.TTransportException, e:
            raise CassandraConnectionError(e)
        except Exception, e:
            raise CassandraAccessError(e)
        
        return self._db_connection
    
    @property
    def db_connection(self):
        return self.get_db_connection(True, True)

########NEW FILE########
__FILENAME__ = compiler
#   Copyright 2010 BSN, Inc.
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

import datetime
import sys
import traceback
import datetime
import decimal

from django.db.models import ForeignKey
from django.db.models.sql.where import AND, OR, WhereNode
from django.db.models.sql.constants import MULTI
from django.db.utils import DatabaseError

from functools import wraps

from djangotoolbox.db.basecompiler import NonrelQuery, NonrelCompiler, \
    NonrelInsertCompiler, NonrelUpdateCompiler, NonrelDeleteCompiler

from .utils import *
from .predicate import *

from uuid import uuid4
from cassandra import Cassandra
from cassandra.ttypes import *
from thrift.transport.TTransport import TTransportException

def safe_call(func):
    @wraps(func)
    def _func(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception, e:
            raise DatabaseError, DatabaseError(*tuple(e)), sys.exc_info()[2]
    return _func

class CassandraQuery(NonrelQuery):
    
    # FIXME: How do we set this value? What's the maximum value it can be?
    #MAX_FETCH_COUNT = 0x7ffffff
    MAX_FETCH_COUNT = 10000
    
    def __init__(self, compiler, fields):
        super(CassandraQuery, self).__init__(compiler, fields)

        self.pk_column = self.query.get_meta().pk.column
        self.column_family = self.query.get_meta().db_table
        self.root_predicate = None
        self.ordering_spec = None
        self.cached_results = None
        
        self.indexed_columns = []
        self.field_name_to_column_name = {}
        for field in fields:
            column_name = field.db_column if field.db_column else field.column
            if field.db_index:
                self.indexed_columns.append(column_name)
            self.field_name_to_column_name[field.name] = column_name
                
    # This is needed for debugging
    def __repr__(self):
        # TODO: add some meaningful query string for debugging
        return '<CassandraQuery: ...>'

    def _convert_key_slice_to_rows(self, key_slice):
        rows = []
        for element in key_slice:
            if element.columns:
                row = self._convert_column_list_to_row(element.columns, self.pk_column, element.key)
                rows.append(row)
        return rows
    
    def _convert_column_list_to_row(self, column_list, pk_column_name, pk_value):
        row = {}
        # FIXME: When we add code to allow primary keys that also are indexed,
        # then we can change this to not set the primary key column in that case.
        # row[pk_column_name] = pk_value
        for column in column_list:
            row[column.column.name] = column.column.value
        return row


    def _get_rows_by_pk(self, range_predicate):

        db_connection = self.connection.db_connection
        column_parent = ColumnParent(column_family=self.column_family)
        slice_predicate = SlicePredicate(slice_range=SliceRange(start='',
            finish='', count=self.connection.max_column_count))
        
        if range_predicate._is_exact():
            column_list = call_cassandra_with_reconnect(db_connection,
               Cassandra.Client.get_slice, range_predicate.start,
                column_parent, slice_predicate, self.connection.read_consistency_level)
            if column_list:
                row = self._convert_column_list_to_row(column_list, self.pk_column, range_predicate.start)
                rows = [row]
            else:
                rows = []
        else:
            if range_predicate.start != None:
                key_start = range_predicate.start
                if not range_predicate.start_inclusive:
                    key_start = key_start + chr(1)
            else:
                key_start = ''
             
            if range_predicate.end != None:
                key_end = range_predicate.end
                if not range_predicate.end_inclusive:
                    key_end = key_end[:-1] + chr(ord(key_end[-1])-1) + (chr(126) * 16)
            else:
                key_end = ''
            
            key_range = KeyRange(start_key=key_start, end_key=key_end,
                count=self.connection.max_key_count)
            key_slice = call_cassandra_with_reconnect(db_connection,
                Cassandra.Client.get_range_slices, column_parent,
                slice_predicate, key_range, self.connection.read_consistency_level)
            
            rows = self._convert_key_slice_to_rows(key_slice)
                
        return rows
    
    def _get_rows_by_indexed_column(self, range_predicate):
        # Construct the index expression for the range predicate
        index_expressions = []
        if ((range_predicate.start != None) and
            (range_predicate.end == range_predicate.start) and
            range_predicate.start_inclusive and
            range_predicate.end_inclusive):
            index_expression = IndexExpression(range_predicate.column, IndexOperator.EQ, unicode(range_predicate.start))
            index_expressions.append(index_expression)
        else:
            # NOTE: These range queries don't work with the current version of cassandra
            # that I'm using (0.7 beta3)
            # It looks like there are cassandra tickets to add support for this, but it's
            # unclear how soon it will be supported. We shouldn't hit this code for now,
            # though, because can_evaluate_efficiently was changed to disable range queries
            # on indexed columns (they still can be performed, just inefficiently).
            if range_predicate.start:
                index_op = IndexOperator.GTE if range_predicate.start_inclusive else IndexOperator.GT
                index_expression = IndexExpression(unicode(range_predicate.column), index_op, unicode(range_predicate.start))
                index_expressions.append(index_expression)
            if range_predicate.end:
                index_op = IndexOperator.LTE if range_predicate.end_inclusive else IndexOperator.LT
                index_expression = IndexExpression(unicode(range_predicate.column), index_op, unicode(range_predicate.end))
                index_expressions.append(index_expression)
                
        assert(len(index_expressions) > 0)
               
        # Now make the call to cassandra to get the key slice
        db_connection = self.connection.db_connection
        column_parent = ColumnParent(column_family=self.column_family)
        index_clause = IndexClause(index_expressions, '', self.connection.max_key_count)
        slice_predicate = SlicePredicate(slice_range=SliceRange(start='', finish='', count=self.connection.max_column_count))
        
        key_slice = call_cassandra_with_reconnect(db_connection,
            Cassandra.Client.get_indexed_slices,
            column_parent, index_clause, slice_predicate,
            self.connection.read_consistency_level)
        rows = self._convert_key_slice_to_rows(key_slice)
        
        return rows
    
    def get_row_range(self, range_predicate):
        pk_column = self.query.get_meta().pk.column
        if range_predicate.column == pk_column:
            rows = self._get_rows_by_pk(range_predicate)
        else:
            assert(range_predicate.column in self.indexed_columns)
            rows = self._get_rows_by_indexed_column(range_predicate)
        return rows
    
    def get_all_rows(self):
        # TODO: Could factor this code better
        db_connection = self.connection.db_connection
        column_parent = ColumnParent(column_family=self.column_family)
        slice_predicate = SlicePredicate(slice_range=SliceRange(start='', finish='', count=self.connection.max_column_count))
        key_range = KeyRange(start_token = '0', end_token = '0', count=self.connection.max_key_count)
        #end_key = u'\U0010ffff'.encode('utf-8')
        #key_range = KeyRange(start_key='\x01', end_key=end_key, count=self.connection.max_key_count)
        
        key_slice = call_cassandra_with_reconnect(db_connection,
            Cassandra.Client.get_range_slices, column_parent,
            slice_predicate, key_range, self.connection.read_consistency_level)
        rows = self._convert_key_slice_to_rows(key_slice)
        
        return rows
    
    def _get_query_results(self):
        if self.cached_results == None:
            assert(self.root_predicate != None)
            self.cached_results = self.root_predicate.get_matching_rows(self)
            if self.ordering_spec:
                sort_rows(self.cached_results, self.ordering_spec)
        return self.cached_results
    
    @safe_call
    def fetch(self, low_mark, high_mark):
        
        if self.root_predicate == None:
            raise DatabaseError('No root query node')
        
        try:
            if high_mark is not None and high_mark <= low_mark:
                return
            
            results = self._get_query_results()
            if low_mark is not None or high_mark is not None:
                results = results[low_mark:high_mark]
        except Exception, e:
            # FIXME: Can get rid of this exception handling code eventually,
            # but it's useful for debugging for now.
            #traceback.print_exc()
            raise e
        
        for entity in results:
            yield entity

    @safe_call
    def count(self, limit=None):
        # TODO: This could be implemented more efficiently for simple predicates
        # where we could call the count method in the Cassandra Thrift API.
        # We can optimize for that later
        results = self._get_query_results()
        return len(results)
    
    @safe_call
    def delete(self):
        results = self._get_query_results()
        timestamp = get_next_timestamp()
        column_family = self.query.get_meta().db_table
        mutation_map = {}
        for item in results:
            mutation_map[item[self.pk_column]] = {column_family: [Mutation(deletion=Deletion(timestamp=timestamp))]}
        db_connection = self.connection.db_connection
        call_cassandra_with_reconnect(db_connection,
            Cassandra.Client.batch_mutate, mutation_map,
            self.connection.write_consistency_level)
        

    @safe_call
    def order_by(self, ordering):
        self.ordering_spec = []
        for order in ordering:
            if order.startswith('-'):
                field_name = order[1:]
                reversed = True
            else:
                field_name = order
                reversed = False
            column_name = self.field_name_to_column_name.get(field_name, field_name)
            #if column in self.foreign_key_columns:
            #    column = column + '_id'
            self.ordering_spec.append((column_name, reversed))
            
    def init_predicate(self, parent_predicate, node):
        if isinstance(node, WhereNode):
            if node.connector == OR:
                compound_op = COMPOUND_OP_OR
            elif node.connector == AND:
                compound_op = COMPOUND_OP_AND
            else:
                raise InvalidQueryOpException()
            predicate = CompoundPredicate(compound_op, node.negated)
            for child in node.children:
                child_predicate = self.init_predicate(predicate, child)
            if parent_predicate:
                parent_predicate.add_child(predicate)
        else:
            column, lookup_type, db_type, value = self._decode_child(node)
            db_value = self.convert_value_for_db(db_type, value)
            assert parent_predicate
            parent_predicate.add_filter(column, lookup_type, db_value)
            predicate = None
            
        return predicate
    
    # FIXME: This is bad. We're modifying the WhereNode object that's passed in to us
    # from the Django ORM. We should do the pruning as we build our predicates, not
    # munge the WhereNode.
    def remove_unnecessary_nodes(self, node, retain_root_node):
        if isinstance(node, WhereNode):
            child_count = len(node.children)
            for i in range(child_count):
                node.children[i] = self.remove_unnecessary_nodes(node.children[i], False)
            if (not retain_root_node) and (not node.negated) and (len(node.children) == 1):
                node = node.children[0]
        return node
        
    @safe_call
    def add_filters(self, filters):
        """
        Traverses the given Where tree and adds the filters to this query
        """
        
        #if filters.negated:
        #    raise InvalidQueryOpException('Exclude queries not implemented yet.')
        assert isinstance(filters,WhereNode)
        self.remove_unnecessary_nodes(filters, True)
        self.root_predicate = self.init_predicate(None, filters)
        
class SQLCompiler(NonrelCompiler):
    query_class = CassandraQuery

    SPECIAL_NONE_VALUE = "\b"

    # Override this method from NonrelCompiler to get around problem with
    # mixing the field default values with the field format as its stored
    # in the database (i.e. convert_value_from_db should only be passed
    # the database-specific storage format not the field default value.
    def _make_result(self, entity, fields):
        result = []
        for field in fields:
            value = entity.get(field.column)
            if value is not None:
                value = self.convert_value_from_db(
                    field.db_type(connection=self.connection), value)
            else:
                value = field.get_default()
            if not field.null and value is None:
                raise DatabaseError("Non-nullable field %s can't be None!" % field.name)
            result.append(value)
            
        return result
    
    # This gets called for each field type when you fetch() an entity.
    # db_type is the string that you used in the DatabaseCreation mapping
    def convert_value_from_db(self, db_type, value):
        
        if value == self.SPECIAL_NONE_VALUE or value is None:
            return None
        
        if  db_type.startswith('ListField:'):
            db_sub_type = db_type.split(':', 1)[1]
            value = convert_string_to_list(value)
            if isinstance(value, (list, tuple)) and len(value):
                value = [self.convert_value_from_db(db_sub_type, subvalue)
                         for subvalue in value]
        elif db_type == 'date':
            dt = datetime.datetime.strptime(value, '%Y-%m-%d')
            value = dt.date()
        elif db_type == 'datetime':
            value = datetime.datetime.strptime(value, '%Y-%m-%d %H:%M:%S.%f')
        elif db_type == 'time':
            dt = datetime.datetime.strptime(value, '%H:%M:%S.%f')
            value = dt.time()
        elif db_type == 'bool':
            value = value.lower() == 'true'
        elif db_type == 'int':
            value = int(value)
        elif db_type == 'long':
            value = long(value)
        elif db_type == 'float':
            value = float(value)
        #elif db_type == 'id':
        #    value = unicode(value).decode('utf-8')
        elif db_type.startswith('decimal'):
            value = decimal.Decimal(value)
        elif isinstance(value, str):
            # always retrieve strings as unicode (it is possible that old datasets
            # contain non unicode strings, nevertheless work with unicode ones)
            value = value.decode('utf-8')
            
        return value

    # This gets called for each field type when you insert() an entity.
    # db_type is the string that you used in the DatabaseCreation mapping
    def convert_value_for_db(self, db_type, value):
        if value is None:
            return self.SPECIAL_NONE_VALUE
        
        if db_type.startswith('ListField:'):
            db_sub_type = db_type.split(':', 1)[1]
            if isinstance(value, (list, tuple)) and len(value):
                value = [self.convert_value_for_db(db_sub_type, subvalue) for subvalue in value]
            value = convert_list_to_string(value)
        elif type(value) is list:
            value = [self.convert_value_for_db(db_type, item) for item in value]
        elif db_type == 'datetime':
            value = value.strftime('%Y-%m-%d %H:%M:%S.%f')
        elif db_type == 'time':
            value = value.strftime('%H:%M:%S.%f')
        elif db_type == 'bool':
            value = str(value).lower()
        elif (db_type == 'int') or (db_type == 'long') or (db_type == 'float'):
            value = str(value)
        elif db_type == 'id':
            value = unicode(value)
        elif (type(value) is not unicode) and (type(value) is not str):
            value = unicode(value)
        
        # always store strings as utf-8
        if type(value) is unicode:
            value = value.encode('utf-8')
            
        return value

# This handles both inserts and updates of individual entities
class SQLInsertCompiler(NonrelInsertCompiler, SQLCompiler):
    
    @safe_call
    def insert(self, data, return_id=False):
        pk_column = self.query.get_meta().pk.column
        model = self.query.model
        compound_key_fields = None
        if hasattr(model, 'CassandraSettings'):
            if hasattr(model.CassandraSettings, 'ADJUSTED_COMPOUND_KEY_FIELDS'):
                compound_key_fields = model.CassandraSettings.ADJUSTED_COMPOUND_KEY_FIELDS
            elif hasattr(model.CassandraSettings, 'COMPOUND_KEY_FIELDS'):
                compound_key_fields = []
                for field_name in model.CassandraSettings.COMPOUND_KEY_FIELDS:
                    field_class = None
                    for lf in model._meta.local_fields:
                        if lf.name == field_name:
                            field_class = lf
                            break
                    if field_class is None:
                        raise DatabaseError('Invalid compound key field')
                    if type(field_class) is ForeignKey:
                        field_name += '_id'
                    compound_key_fields.append(field_name)
                model.CassandraSettings.ADJUSTED_COMPOUND_KEY_FIELDS = compound_key_fields
            separator = model.CassandraSettings.COMPOUND_KEY_SEPARATOR \
                if hasattr(model.CassandraSettings, 'COMPOUND_KEY_SEPARATOR') \
                else self.connection.settings_dict.get('CASSANDRA_COMPOUND_KEY_SEPARATOR', '|')
        # See if the data arguments contain a value for the primary key.
        # FIXME: For now we leave the key data as a column too. This is
        # suboptimal, since the data is duplicated, but there are a couple of cases
        # where you need to keep the column. First, if you have a model with only
        # a single field that's the primary key (admittedly a semi-pathological case,
        # but I can imagine valid use cases where you have this), then it doesn't
        # work if the column is removed, because then there are no columns and that's
        # interpreted as a deleted row (i.e. the usual Cassandra tombstone issue).
        # Second, if there's a secondary index configured for the primary key field
        # (not particularly useful with the current Cassandra, but would be valid when
        # you can do a range query on indexed column) then you'd want to keep the
        # column. So for now, we just leave the column in there so these cases work.
        # Eventually we can optimize this and remove the column where it makes sense.
        key = data.get(pk_column)
        if key:
            if compound_key_fields is not None:
                compound_key_values = key.split(separator)
                for field_name, compound_key_value in zip(compound_key_fields, compound_key_values):
                    if field_name in data and data[field_name] != compound_key_value:
                        raise DatabaseError("The value of the compound key doesn't match the values of the individual fields")
        else:
            if compound_key_fields is not None:
                try:
                    compound_key_values = [data.get(field_name) for field_name in compound_key_fields]
                    key = separator.join(compound_key_values)
                except Exception, e:
                    raise DatabaseError('The values of the fields used to form a compound key must be specified and cannot be null')
            else:
                key = str(uuid4())
            # Insert the key as column data too
            # FIXME. See the above comment. When the primary key handling is optimized,
            # then we would not always add the key to the data here.
            data[pk_column] = key
        
        timestamp = get_next_timestamp()
        
        mutation_list = []
        for name, value in data.items():
            # FIXME: Do we need this check here? Or is the name always already a str instead of unicode.
            if type(name) is unicode:
                name = name.decode('utf-8')
            mutation = Mutation(column_or_supercolumn=ColumnOrSuperColumn(column=Column(name=name, value=value, timestamp=timestamp)))
            mutation_list.append(mutation)
        
        db_connection = self.connection.db_connection
        column_family = self.query.get_meta().db_table
        call_cassandra_with_reconnect(db_connection,
            Cassandra.Client.batch_mutate, {key: {column_family: mutation_list}},
            self.connection.write_consistency_level)
        
        if return_id:
            return key

class SQLUpdateCompiler(NonrelUpdateCompiler, SQLCompiler):
    def __init__(self, *args, **kwargs):
        super(SQLUpdateCompiler, self).__init__(*args, **kwargs)
        
    def execute_sql(self, result_type=MULTI):
        data = {}
        for field, model, value in self.query.values:
            assert field is not None
            if not field.null and value is None:
                raise DatabaseError("You can't set %s (a non-nullable "
                                    "field) to None!" % field.name)
            db_type = field.db_type(connection=self.connection)
            value = self.convert_value_for_db(db_type, value)
            data[field.column] = value
        
        # TODO: Add compound key check here -- ensure that we're not updating
        # any of the fields that are components in the compound key.
        
        # TODO: This isn't super efficient because executing the query will
        # fetch all of the columns for each row even though all we really need
        # is the key for the row. Should be pretty straightforward to change
        # the CassandraQuery class to support custom slice predicates.
        
        #model = self.query.model
        pk_column = self.query.get_meta().pk.column
        
        pk_index = -1
        fields = self.get_fields()
        for index in range(len(fields)):
            if fields[index].column == pk_column:
                pk_index = index;
                break
        if pk_index == -1:
            raise DatabaseError('Invalid primary key column')
        
        row_count = 0
        column_family = self.query.get_meta().db_table
        timestamp = get_next_timestamp()
        batch_mutate_data = {}
        for result in self.results_iter():
            row_count += 1
            mutation_list = []
            key = result[pk_index]
            for name, value in data.items():
                # FIXME: Do we need this check here? Or is the name always already a str instead of unicode.
                if type(name) is unicode:
                    name = name.decode('utf-8')
                mutation = Mutation(column_or_supercolumn=ColumnOrSuperColumn(column=Column(name=name, value=value, timestamp=timestamp)))
                mutation_list.append(mutation)
            batch_mutate_data[key] = {column_family: mutation_list}
        
        db_connection = self.connection.db_connection
        call_cassandra_with_reconnect(db_connection,
            Cassandra.Client.batch_mutate, batch_mutate_data,
            self.connection.write_consistency_level)
        
        return row_count
    
class SQLDeleteCompiler(NonrelDeleteCompiler, SQLCompiler):
    pass

########NEW FILE########
__FILENAME__ = creation
#   Copyright 2010 BSN, Inc.
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

from django.db.backends.creation import TEST_DATABASE_PREFIX
from django.db.utils import DatabaseError
from djangotoolbox.db.creation import NonrelDatabaseCreation
from cassandra import Cassandra
from cassandra.ttypes import *
from django.core.management import call_command
from .utils import get_next_timestamp

class DatabaseCreation(NonrelDatabaseCreation):

    data_types = {
        'AutoField':         'text',
        'BigIntegerField':   'long',
        'BooleanField':      'bool',
        'CharField':         'text',
        'CommaSeparatedIntegerField': 'text',
        'DateField':         'date',
        'DateTimeField':     'datetime',
        'DecimalField':      'decimal:%(max_digits)s,%(decimal_places)s',
        'EmailField':        'text',
        'FileField':         'text',
        'FilePathField':     'text',
        'FloatField':        'float',
        'ImageField':        'text',
        'IntegerField':      'int',
        'IPAddressField':    'text',
        'NullBooleanField':  'bool',
        'OneToOneField':     'integer',
        'PositiveIntegerField': 'int',
        'PositiveSmallIntegerField': 'int',
        'SlugField':         'text',
        'SmallIntegerField': 'integer',
        'TextField':         'text',
        'TimeField':         'time',
        'URLField':          'text',
        'XMLField':          'text',
        'GenericAutoField':  'id',
        'StringForeignKey':  'id',
        'AutoField':         'id',
        'RelatedAutoField':  'id',
    }
    
    def sql_create_model(self, model, style, known_models=set()):
        
        db_connection = self.connection.db_connection
        keyspace = self.connection.settings_dict['NAME']
        
        opts = model._meta
        column_metadata = []

        # Browsing through fields to find indexed fields
        for field in opts.local_fields:
            if field.db_index:
                column_name = str(field.db_column if field.db_column else field.column)
                column_def = ColumnDef(name=column_name, validation_class='BytesType',
                                       index_type=IndexType.KEYS)
                column_metadata.append(column_def)
        
        cfdef_settings = self.connection.column_family_def_defaults.copy()
        
        if hasattr(model, 'CassandraSettings') and \
            hasattr(model.CassandraSettings, 'COLUMN_FAMILY_DEF_SETTINGS'):
            cfdef_overrides = model.CassandraSettings.COLUMN_FAMILY_DEF_SETTINGS
            if type(cfdef_overrides) is not dict:
                raise DatabaseError('The value of COLUMN_FAMILY_DEF_SETTINGS in the '
                    'CassandraSettings class must be a dictionary of the optional '
                    'settings to use when creating the column family.')
            cfdef_settings.update(cfdef_overrides)

        cfdef_settings['keyspace'] = keyspace
        if not cfdef_settings.get('name'):
            cfdef_settings['name'] = opts.db_table
        if not cfdef_settings.get('comparator_type'):
            cfdef_settings['comparator_type'] = 'UTF8Type'
        cfdef_settings['column_metadata'] = column_metadata
        
        column_family_def = CfDef(**cfdef_settings)
        
        db_connection.get_client().system_add_column_family(column_family_def)
        
        return [], {}

    def drop_keyspace(self, keyspace_name, verbosity=1):
        """
        Drop the specified keyspace from the cluster.
        """
        
        db_connection = self.connection.get_db_connection(False, False)
        
        try:
            db_connection.get_client().system_drop_keyspace(keyspace_name)
        except Exception, e:
            # We want to succeed without complaining if the test db doesn't
            # exist yet, so we just assume that any exception that's raised
            # was for that reason and ignore it, except for printing a
            # message if verbose output is enabled
            # FIXME: Could probably be more specific about the Thrift
            # exception that we catch here.
            #if verbosity >= 1:
            #    print "Exception thrown while trying to drop the test database/keyspace: ", e
            pass
        
    def create_test_db(self, verbosity, autoclobber):
        """
        Create a new test database/keyspace.
        """
        
        if verbosity >= 1:
            print "Creating test database '%s'..." % self.connection.alias

        # Replace the NAME field in the database settings with the test keyspace name
        settings_dict = self.connection.settings_dict
        if settings_dict.get('TEST_NAME'):
            test_keyspace_name = settings_dict['TEST_NAME']
        else:
            test_keyspace_name = TEST_DATABASE_PREFIX + settings_dict['NAME']

        settings_dict['NAME'] = test_keyspace_name
        
        # First make sure we've destroyed an existing test keyspace
        # FIXME: Should probably do something with autoclobber here, but why
        # would you ever not want to autoclobber when running the tests?
        self.drop_keyspace(test_keyspace_name, verbosity)
        
        # Call syncdb to create the necessary tables/column families
        call_command('syncdb', verbosity=False, interactive=False, database=self.connection.alias)
    
        return test_keyspace_name
    
    def destroy_test_db(self, old_database_name, verbosity=1):
        """
        Destroy the test database/keyspace.
        """

        if verbosity >= 1:
            print "Destroying test database '%s'..." % self.connection.alias
            
        settings_dict = self.connection.settings_dict
        test_keyspace_name = settings_dict.get('NAME')
        settings_dict['NAME'] = old_database_name
        
        self.drop_keyspace(test_keyspace_name, verbosity)
        
    def flush_table(self, table_name):
        
        db_connection = self.connection.db_connection

        # FIXME: Calling truncate here seems to corrupt the secondary indexes,
        # so for now the truncate call has been replaced with removing the
        # row one by one. When the truncate bug has been fixed in Cassandra
        # this should be switched back to use truncate.
        # NOTE: This should be fixed as of the 0.7.0-rc2 build, so we should
        # try this out again to see if it works now.
        # UPDATE: Tried it with rc2 and it worked calling truncate but it was
        # slower than using remove (at least for the unit tests), so for now
        # I'm leaving it alone pending further investigation.
        #db_connection.get_client().truncate(table_name)
        
        column_parent = ColumnParent(column_family=table_name)
        slice_predicate = SlicePredicate(column_names=[])
        key_range = KeyRange(start_token = '0', end_token = '0', count = 1000)
        key_slice_list = db_connection.get_client().get_range_slices(column_parent, slice_predicate, key_range, ConsistencyLevel.ONE)
        column_path = ColumnPath(column_family=table_name)
        timestamp = get_next_timestamp()
        for key_slice in key_slice_list:
            db_connection.get_client().remove(key_slice.key, column_path, timestamp, ConsistencyLevel.ONE)

        
    def sql_indexes_for_model(self, model, style):
        """
        We already handle creating the indexes in sql_create_model (above) so
        we don't need to do anything more here.
        """
        return []
    
    def set_autocommit(self):
        pass
    

########NEW FILE########
__FILENAME__ = introspection
#   Copyright 2010 BSN, Inc.
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

from djangotoolbox.db.base import NonrelDatabaseIntrospection
from django.db.backends import BaseDatabaseIntrospection

class DatabaseIntrospection(NonrelDatabaseIntrospection):
    def get_table_list(self, cursor):
        "Returns a list of names of all tables that exist in the database."
        db_connection = self.connection.db_connection
        ks_def = db_connection.get_client().describe_keyspace(db_connection.keyspace)
        result = [cf_def.name for cf_def in ks_def.cf_defs]
        return result
    
    def table_names(self):
        # NonrelDatabaseIntrospection has an implementation of this that returns
        # that all of the tables for the models already exist in the database,
        # so the DatabaseCreation code never gets called to create new tables,
        # which isn't how we want things to work for Cassandra, so we bypass the
        # nonrel implementation and go directly to the base introspection code.
        return BaseDatabaseIntrospection.table_names(self)

    def sequence_list(self):
        return []
    
# TODO: Implement these things eventually
#===============================================================================
#    def get_table_description(self, cursor, table_name):
#        "Returns a description of the table, with the DB-API cursor.description interface."
#        return ""
# 
#    def get_relations(self, cursor, table_name):
#        """
#        Returns a dictionary of {field_index: (field_index_other_table, other_table)}
#        representing all relationships to the given table. Indexes are 0-based.
#        """
#        relations = {}
#        return relations
#    
#    def get_indexes(self, cursor, table_name):
#        """
#        Returns a dictionary of fieldname -> infodict for the given table,
#        where each infodict is in the format:
#            {'primary_key': boolean representing whether it's the primary key,
#             'unique': boolean representing whether it's a unique index}
#        """
#        indexes = {}
#        return indexes
#===============================================================================

########NEW FILE########
__FILENAME__ = predicate
#   Copyright 2010 BSN, Inc.
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

import re
from .utils import combine_rows

SECONDARY_INDEX_SUPPORT_ENABLED = True

class InvalidSortSpecException(Exception):
    def __init__(self):
        super(InvalidSortSpecException, self).__init__('The row sort spec must be a sort spec tuple/list or a tuple/list of sort specs')

class InvalidRowCombinationOpException(Exception):
    def __init__(self):
        super(InvalidRowCombinationOpException, self).__init__('Invalid row combination operation')

class InvalidPredicateOpException(Exception):
    def __init__(self):
        super(InvalidPredicateOpException, self).__init__('Invalid/unsupported query predicate operation')


COMPOUND_OP_AND = 1
COMPOUND_OP_OR = 2

class RangePredicate(object):
    
    def __init__(self, column, start=None, start_inclusive=True, end=None, end_inclusive=True):
        self.column = column
        self.start = start
        self.start_inclusive = start_inclusive
        self.end = end
        self.end_inclusive = end_inclusive
    
    def __repr__(self):
        s = '(RANGE: '
        if self.start:
            op = '<=' if self.start_inclusive else '<'
            s += (unicode(self.start) + op)
        s += self.column
        if self.end:
            op = '>=' if self.end_inclusive else '>'
            s += (op + unicode(self.end))
        s += ')'
        return s

    def _is_exact(self):
        return (self.start != None) and (self.start == self.end) and self.start_inclusive and self.end_inclusive
    
    def can_evaluate_efficiently(self, pk_column, indexed_columns):
        # FIXME: There's some problem with secondary index support currently.
        # I'm suspicious that this is a bug in Cassandra but I haven't really verified that yet.
        # Anyway disabling the secondary index support for now.
        return ((self.column == pk_column) or
                (SECONDARY_INDEX_SUPPORT_ENABLED and ((self.column in indexed_columns) and self._is_exact())))
    
    def incorporate_range_op(self, column, op, value, parent_compound_op):
        if column != self.column:
            return False
        
        # FIXME: The following logic could probably be tightened up a bit
        # (although perhaps at the expense of clarity?)
        if parent_compound_op == COMPOUND_OP_AND:
            if op == 'gt':
                if self.start == None or value >= self.start:
                    self.start = value
                    self.start_inclusive = False
                    return True
            elif op == 'gte':
                if self.start == None or value > self.start:
                    self.start = value
                    self.start_inclusive = True
                    return True
            elif op == 'lt':
                if self.end == None or value <= self.end:
                    self.end = value
                    self.end_inclusive = False
                    return True
            elif op == 'lte':
                if self.end == None or value < self.end:
                    self.end = value
                    self.end_inclusive = True
                    return True
            elif op == 'exact':
                if self._matches_value(value):
                    self.start = self.end = value
                    self.start_inclusive = self.end_inclusive = True
                    return True
            elif op == 'startswith':
                # For the end value we increment the ordinal value of the last character
                # in the start value and make the end value not inclusive
                end_value = value[:-1] + chr(ord(value[-1])+1)
                if (((self.start == None) or (value > self.start)) and
                    ((self.end == None) or (end_value <= self.end))):
                    self.start = value
                    self.end = end_value
                    self.start_inclusive = True
                    self.end_inclusive = False
                    return True
            else:
                raise InvalidPredicateOpException()
        elif parent_compound_op == COMPOUND_OP_OR:
            if op == 'gt':
                if self.start == None or value < self.start:
                    self.start = value
                    self.start_inclusive = False
                    return True
            elif op == 'gte':
                if self.start == None or value <= self.start:
                    self.start = value
                    self.start_inclusive = True
                    return True
            elif op == 'lt':
                if self.end == None or value > self.end:
                    self.end = value
                    self.end_inclusive = False
                    return True
            elif op == 'lte':
                if self.end == None or value >= self.end:
                    self.end = value
                    self.end_inclusive = True
                    return True
            elif op == 'exact':
                if self._matches_value(value):
                    return True
            elif op == 'startswith':
                # For the end value we increment the ordinal value of the last character
                # in the start value and make the end value not inclusive
                end_value = value[:-1] + chr(ord(value[-1])+1)
                if (((self.start == None) or (value <= self.start)) and
                    ((self.end == None) or (end_value > self.end))):
                    self.start = value
                    self.end = end_value
                    self.start_inclusive = True
                    self.end_inclusive = False
                    return True
        else:
            raise InvalidPredicateOpException()
    
        return False
    
    def _matches_value(self, value):
        if value == None:
            return False
        if self.start != None:
            if self.start_inclusive:
                if value < self.start:
                    return False
            elif value <= self.start:
                return False
        if self.end != None:
            if self.end_inclusive:
                if value > self.end:
                    return False
            elif value >= self.end:
                return False
        return True
    
    def row_matches(self, row):
        value = row.get(self.column, None)
        return self._matches_value(value)
    
    def get_matching_rows(self, query):
        rows = query.get_row_range(self)
        return rows
    
class OperationPredicate(object):
    def __init__(self, column, op, value=None):
        self.column = column
        self.op = op
        self.value = value
        if op == 'regex' or op == 'iregex':
            flags = re.I if op == 'iregex' else 0
            self.pattern = re.compile(value, flags)
    
    def __repr__(self):
        return '(OP: ' + self.op + ':' + unicode(self.value) + ')'
    
    def can_evaluate_efficiently(self, pk_column, indexed_columns):
        return False

    def row_matches(self, row):
        row_value = row.get(self.column, None)
        if self.op == 'isnull':
            return row_value == None
        # FIXME: Not sure if the following test is correct in all cases
        if (row_value == None) or (self.value == None):
            return False
        if self.op == 'in':
            return row_value in self.value
        if self.op == 'istartswith':
            return row_value.lower().startswith(self.value.lower())
        elif self.op == 'endswith':
            return row_value.endswith(self.value)
        elif self.op == 'iendswith':
            return row_value.lower().endswith(self.value.lower())
        elif self.op == 'iexact':
            return row_value.lower() == self.value.lower()
        elif self.op == 'contains':
            return row_value.find(self.value) >= 0
        elif self.op == 'icontains':
            return row_value.lower().find(self.value.lower()) >= 0
        elif self.op == 'regex' or self.op == 'iregex':
            return self.pattern.match(row_value) != None
        else:
            raise InvalidPredicateOpException()
    
    def incorporate_range_op(self, column, op, value, parent_compound_op):
        return False
    
    def get_matching_rows(self, query):
        # get_matching_rows should only be called for predicates that can
        # be evaluated efficiently, which is not the case for OperationPredicate's
        raise NotImplementedError('get_matching_rows() called for inefficient predicate')
    
class CompoundPredicate(object):
    def __init__(self, op, negated=False, children=None):
        self.op = op
        self.negated = negated
        self.children = children
        if self.children == None:
            self.children = []
    
    def __repr__(self):
        s = '('
        if self.negated:
            s += 'NOT '
        s += ('AND' if self.op == COMPOUND_OP_AND else 'OR')
        s += ': '
        first_time = True
        if self.children:
            for child_predicate in self.children:
                if first_time:
                    first_time = False
                else:
                    s += ','
                s += unicode(child_predicate)
        s += ')'
        return s
    
    def can_evaluate_efficiently(self, pk_column, indexed_columns):
        if self.negated:
            return False
        if self.op == COMPOUND_OP_AND:
            for child in self.children:
                if child.can_evaluate_efficiently(pk_column, indexed_columns):
                    return True
            else:
                return False
        elif self.op == COMPOUND_OP_OR:
            for child in self.children:
                if not child.can_evaluate_efficiently(pk_column, indexed_columns):
                    return False
            else:
                return True
        else:
            raise InvalidPredicateOpException()

    def row_matches_subset(self, row, subset):
        if self.op == COMPOUND_OP_AND:
            for predicate in subset:
                if not predicate.row_matches(row):
                    matches = False
                    break
            else:
                matches = True
        elif self.op == COMPOUND_OP_OR:
            for predicate in subset:
                if predicate.row_matches(row):
                    matches =  True
                    break
            else:
                matches = False
        else:
            raise InvalidPredicateOpException()
        
        if self.negated:
            matches = not matches
            
        return matches
        
    def row_matches(self, row):
        return self.row_matches_subset(row, self.children)
    
    def incorporate_range_op(self, column, op, value, parent_predicate):
        return False
    
    def add_filter(self, column, op, value):
        if op in ('lt', 'lte', 'gt', 'gte', 'exact', 'startswith'):
            for child in self.children:
                if child.incorporate_range_op(column, op, value, self.op):
                    return
            else:
                child = RangePredicate(column)
                incorporated = child.incorporate_range_op(column, op, value, COMPOUND_OP_AND)
                assert incorporated
                self.children.append(child)
        else:
            child = OperationPredicate(column, op, value)
            self.children.append(child)
    
    def add_child(self, child_query_node):
        self.children.append(child_query_node)
    
    def get_matching_rows(self, query):
        pk_column = query.query.get_meta().pk.column
        #indexed_columns = query.indexed_columns
        
        # In the first pass we handle the query nodes that can be processed
        # efficiently. Hopefully, in most cases, this will result in a
        # subset of the rows that is much smaller than the overall number
        # of rows so we only have to run the inefficient query predicates
        # over this smaller number of rows.
        if self.can_evaluate_efficiently(pk_column, query.indexed_columns):
            inefficient_predicates = []
            result = None
            for predicate in self.children:
                if predicate.can_evaluate_efficiently(pk_column, query.indexed_columns):
                    rows = predicate.get_matching_rows(query)
                            
                    if result == None:
                        result = rows
                    else:
                        result = combine_rows(result, rows, self.op, pk_column)
                else:
                    inefficient_predicates.append(predicate)
        else:
            inefficient_predicates = self.children
            result = query.get_all_rows()
        
        if result == None:
            result = []
            
        # Now 
        if len(inefficient_predicates) > 0:
            result = [row for row in result if self.row_matches_subset(row, inefficient_predicates)]
            
        return result


########NEW FILE########
__FILENAME__ = utils
#   Copyright 2010 BSN, Inc.
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

import time
from thrift import Thrift
from thrift.transport import TTransport
from thrift.transport import TSocket
from thrift.protocol import TBinaryProtocol
from cassandra import Cassandra
#from cassandra.ttypes import *
from django.db.utils import DatabaseError

def _cmp_to_key(comparison_function):
    """
    Convert a cmp= function into a key= function.
    This is built in to Python 2.7, but we define it ourselves
    to work with older versions of Python
    """
    class K(object):
        def __init__(self, obj, *args):
            self.obj = obj
        def __lt__(self, other):
            return comparison_function(self.obj, other.obj) < 0
        def __gt__(self, other):
            return comparison_function(self.obj, other.obj) > 0
        def __eq__(self, other):
            return comparison_function(self.obj, other.obj) == 0
        def __le__(self, other):
            return comparison_function(self.obj, other.obj) <= 0
        def __ge__(self, other):
            return comparison_function(self.obj, other.obj) >= 0
        def __ne__(self, other):
            return comparison_function(self.obj, other.obj) != 0
    return K

def _compare_rows(row1, row2, sort_spec_list):
    for sort_spec in sort_spec_list:
        column_name = sort_spec[0]
        reverse = sort_spec[1] if len(sort_spec) > 1 else False
        row1_value = row1.get(column_name, None)
        row2_value = row2.get(column_name, None)
        result = cmp(row1_value, row2_value)
        if result != 0:
            if reverse:
                result = -result
            break;
    else:
        result = 0
    return result

def sort_rows(rows, sort_spec):
    if sort_spec == None:
        return rows

    if (type(sort_spec) != list) and (type(sort_spec) != tuple):
        raise InvalidSortSpecException()
    
    # The sort spec can be either a single sort spec tuple or a list/tuple
    # of sort spec tuple. To simplify the code below we convert the case
    # where it's a single sort spec tuple to a 1-element tuple containing
    # the sort spec tuple here.
    if (type(sort_spec[0]) == list) or (type(sort_spec[0]) == tuple):
        sort_spec_list = sort_spec
    else:
        sort_spec_list = (sort_spec,)
    
    rows.sort(key=_cmp_to_key(lambda row1, row2: _compare_rows(row1, row2, sort_spec_list)))

COMBINE_INTERSECTION = 1
COMBINE_UNION = 2

def combine_rows(rows1, rows2, op, primary_key_column):
    # Handle cases where rows1 and/or rows2 are None or empty
    if not rows1:
        return list(rows2) if rows2 and (op == COMBINE_UNION) else []
    if not rows2:
        return list(rows1) if (op == COMBINE_UNION) else []
    
    # We're going to iterate over the lists in parallel and
    # compare the elements so we need both lists to be sorted
    # Note that this means that the input arguments will be modified.
    # We could optionally clone the rows first, but then we'd incur
    # the overhead of the copy. For now, we'll just always sort
    # in place, and if it turns out to be a problem we can add the
    # option to copy
    sort_rows(rows1,(primary_key_column,))
    sort_rows(rows2,(primary_key_column,))
    
    combined_rows = []
    iter1 = iter(rows1)
    iter2 = iter(rows2)
    update1 = update2 = True
    
    while True:
        # Get the next element from one or both of the lists
        if update1:
            try:
                row1 = iter1.next()
            except:
                row1 = None
            value1 = row1.get(primary_key_column, None) if row1 != None else None
        if update2:
            try:
                row2 = iter2.next()
            except:
                row2 = None
            value2 = row2.get(primary_key_column, None) if row2 != None else None
        
        if (op == COMBINE_INTERSECTION):
            # If we've reached the end of either list and we're doing an intersection,
            # then we're done
            if (row1 == None) or (row2 == None):
                break
        
            if value1 == value2:
                combined_rows.append(row1)
        elif (op == COMBINE_UNION):
            if row1 == None:
                if row2 == None:
                    break;
                combined_rows.append(row2)
            elif (row2 == None) or (value1 <= value2):
                combined_rows.append(row1)
            else:
                combined_rows.append(row2)
        else:
            raise InvalidCombineRowsOpException()
        
        update1 = (row2 == None) or (value1 <= value2)
        update2 = (row1 == None) or (value2 <= value1)
    
    return combined_rows

_last_timestamp = None
    
def get_next_timestamp():
    # The timestamp is a 64-bit integer
    # We now use the standard Cassandra timestamp format of the
    # current system time in microseconds. We also keep track of the
    # last timestamp we returned and if the current time is less than
    # that, then we just advance the timestamp by 1 to make sure we
    # return monotonically increasing timestamps. Note that this isn't
    # guaranteed to handle the fairly common Django deployment model of
    # having multiple Django processes that are dispatched to from a
    # web server like Apache. In practice I don't think that case will be
    # a problem though (at least with current hardware) because I don't
    # think you could have two consecutive calls to Django from another
    # process that would be dispatched to two different Django processes
    # that would happen in the same microsecond.

    global _last_timestamp

    timestamp = int(time.time() * 1000000)
    
    if (_last_timestamp != None) and (timestamp <= _last_timestamp):
        timestamp = _last_timestamp + 1

    _last_timestamp = timestamp
    
    return timestamp

def convert_string_to_list(s):
    # FIXME: Shouldn't use eval here, because of security considerations
    # (i.e. if someone could modify the data in Cassandra they could
    # insert arbitrary Python code that would then get evaluated on
    # the client machine. Should have code that parses the list string
    # to construct the list or else validate the string before calling eval.
    # But for now, during development, we'll just use the quick & dirty eval.
    return eval(s)

def convert_list_to_string(l):
    return unicode(l)


class CassandraConnection(object):
    def __init__(self, host, port, keyspace, user, password):
        self.host = host
        self.port = port
        self.keyspace = keyspace
        self.user = user
        self.password = password
        self.transport = None
        self.client = None
        self.keyspace_set = False
        self.logged_in = False
        
    def commit(self):
        pass

    def set_keyspace(self):
        if not self.keyspace_set:
            try:
                if self.client:
                    self.client.set_keyspace(self.keyspace)
                    self.keyspace_set = True
            except Exception, e:
                # In this case we won't have set keyspace_set to true, so we'll throw the
                # exception below where it also handles the case that self.client
                # is not valid yet.
                pass
            if not self.keyspace_set:
                raise DatabaseError('Error setting keyspace: %s; %s' % (self.keyspace, str(e)))
    
    def login(self):
        # TODO: This user/password auth code hasn't been tested
        if not self.logged_in:
            if self.user:
                try:
                    if self.client:
                        credentials = {'username': self.user, 'password': self.password}
                        self.client.login(AuthenticationRequest(credentials))
                        self.logged_in = True
                except Exception, e:
                    # In this case we won't have set logged_in to true, so we'll throw the
                    # exception below where it also handles the case that self.client
                    # is not valid yet.
                    pass
                if not self.logged_in:
                    raise DatabaseError('Error logging in to keyspace: %s; %s' % (self.keyspace, str(e)))
            else:
                self.logged_in = True
            
    def open(self, set_keyspace=False, login=False):
        if self.transport == None:
            # Create the client connection to the Cassandra daemon
            socket = TSocket.TSocket(self.host, int(self.port))
            transport = TTransport.TFramedTransport(TTransport.TBufferedTransport(socket))
            protocol = TBinaryProtocol.TBinaryProtocolAccelerated(transport)
            transport.open()
            self.transport = transport
            self.client = Cassandra.Client(protocol)
            
        if login:
            self.login()
        
        if set_keyspace:
            self.set_keyspace()
                
    def close(self):
        if self.transport != None:
            try:
                self.transport.close()
            except Exception, e:
                pass
            self.transport = None
            self.client = None
            self.keyspace_set = False
            self.logged_in = False
            
    def is_connected(self):
        return self.transport != None
    
    def get_client(self):
        if self.client == None:
            self.open(True, True)
        return self.client
    
    def reopen(self):
        self.close()
        self.open(True, True)
            

class CassandraConnectionError(DatabaseError):
    def __init__(self, message=None):
        msg = 'Error connecting to Cassandra database'
        if message:
            msg += '; ' + str(message)
        super(CassandraConnectionError,self).__init__(msg)


class CassandraAccessError(DatabaseError):
    def __init__(self, message=None):
        msg = 'Error accessing Cassandra database'
        if message:
            msg += '; ' + str(message)
        super(CassandraAccessError,self).__init__(msg)


def call_cassandra_with_reconnect(connection, fn, *args, **kwargs):
    try:
        try:
            results = fn(connection.get_client(), *args, **kwargs)
        except TTransport.TTransportException:
            connection.reopen()
            results = fn(connection.get_client(), *args, **kwargs)
    except TTransport.TTransportException, e:
        raise CassandraConnectionError(e)
    except Exception, e:
        raise CassandraAccessError(e)

    return results



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
# Django settings for test_db_backend project.

DEBUG = True
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    # ('Your Name', 'your_email@domain.com'),
)

MANAGERS = ADMINS

DATABASES = {
     'default': {
        'ENGINE': 'django_cassandra.db', # Add 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'oracle'.
        'NAME': 'DjangoTest',            # Or path to database file if using sqlite3.
        'USER': '',                      # Not used with sqlite3.
        'PASSWORD': '',                  # Not used with sqlite3.
        'HOST': 'localhost',                      # Set to empty string for localhost. Not used with sqlite3.
        'PORT': '9160',                      # Set to empty string for default. Not used with sqlite3.
        'SUPPORTS_TRANSACTIONS': False,
        'CASSANDRA_REPLICATION_FACTOR': 1,
        'CASSANDRA_ENABLE_CASCADING_DELETES': True
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
SECRET_KEY = 'b^%)yd-d6s%pk16+1m@fx!jsry!alaes%)nmb^ma#rxz8+i_to'

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
#     'django.template.loaders.eggs.Loader',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    #'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    #'django.contrib.messages.middleware.MessageMiddleware',
)

ROOT_URLCONF = 'django_cassandra_backend.urls'

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
    #'django.contrib.messages',
    'django_cassandra_backend.django_cassandra',
    # Uncomment the next line to enable the admin:
    'django.contrib.admin',
    'django_cassandra_backend.tests',
    #'django_cassandra_backend.djangotoolbox'
)

AUTHENTICATION_BACKENDS = (
    'django.contrib.auth.backends.ModelBackend',
)


########NEW FILE########
__FILENAME__ = admin
from .models import Host, Slice, Tag
from django.contrib import admin

admin.site.register(Host)
admin.site.register(Slice)
admin.site.register(Tag)

########NEW FILE########
__FILENAME__ = models
from django.db import models
from djangotoolbox.fields import ListField

class Slice(models.Model):
    name = models.CharField(max_length=64)
    
    class Meta:
        db_table = 'Slice'
        ordering = ['id']
        
class Host(models.Model):
    mac = models.CharField(max_length=20, db_index=True)
    ip = models.CharField(max_length=20, db_index = True)
    slice = models.ForeignKey(Slice, db_index=True)
    
    class Meta:
        db_table = 'Host'
        ordering = ['id']
        
class Tag(models.Model):
    name = models.CharField(max_length=64)
    value = models.CharField(max_length=256)
    host = models.ForeignKey(Host, db_index=True)
    
    class Meta:
        db_table = 'Tag'
        ordering = ['id']

class Test(models.Model):
    test_date = models.DateField(null=True)
    test_datetime = models.DateTimeField(null=True)
    test_time = models.TimeField(null=True)
    test_decimal = models.DecimalField(null=True, max_digits=10, decimal_places=3)
    test_text = models.TextField(null=True)
    #test_list = ListField(models.CharField(max_length=500))
    
    class Meta:
        db_table = 'Test'
        ordering = ['id']



class CompoundKeyModel(models.Model):
    name = models.CharField(max_length=64)
    index = models.IntegerField()
    extra = models.CharField(max_length=32, default='test')
    
    class CassandraSettings:
        COMPOUND_KEY_FIELDS = ('name', 'index')


class CompoundKeyModel2(models.Model):
    slice = models.ForeignKey(Slice)
    name = models.CharField(max_length=64)
    index = models.IntegerField()
    extra = models.CharField(max_length=32)
    
    class CassandraSettings:
        COMPOUND_KEY_FIELDS = ('slice', 'name', 'index')
        COMPOUND_KEY_SEPARATOR = '#'

class CompoundKeyModel3(models.Model):
    name = models.CharField(max_length=32)

    class CassandraSettings:
        COMPOUND_KEY_FIELDS = ('name')

########NEW FILE########
__FILENAME__ = tests
#   Copyright 2010 BSN, Inc.
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

from django.test import TestCase
from .models import *
import datetime
import decimal
from django.db.models.query import Q
from django.db.utils import DatabaseError

class FieldsTest(TestCase):
    
    TEST_DATE = datetime.date(2007,3,5)
    TEST_DATETIME = datetime.datetime(2010,5,4,9,34,25)
    TEST_DATETIME2 = datetime.datetime(2010, 6, 6, 6, 20)
    TEST_TIME = datetime.time(10,14,29)
    TEST_DECIMAL = decimal.Decimal('33.55')
    TEST_TEXT = "Practice? We're talking about practice?"
    TEST_TEXT2 = "I'm a man. I'm 40."
    #TEST_LIST = [u'aaa',u'bbb',u'foobar',u'snafu',u'hello',u'goodbye']
    
    def setUp(self):
        self.test = Test(id='key1',
                          test_date=self.TEST_DATE,
                          test_datetime=self.TEST_DATETIME,
                          test_time=self.TEST_TIME,
                          test_decimal=self.TEST_DECIMAL,
                          test_text=self.TEST_TEXT
                          #,test_list=self.TEST_LIST
			  )
        self.test.save()
    
    def test_fields(self):
        test1 = Test.objects.get(id='key1')
        self.assertEqual(test1.test_date, self.TEST_DATE)
        self.assertEqual(test1.test_datetime, self.TEST_DATETIME)
        self.assertEqual(test1.test_time, self.TEST_TIME)
        self.assertEqual(test1.test_decimal, self.TEST_DECIMAL)
        self.assertEqual(test1.test_text, self.TEST_TEXT)
        #self.assertEqual(test1.test_list, self.TEST_LIST)
        
        test1.test_datetime = self.TEST_DATETIME2
        test1.test_text = self.TEST_TEXT2
        test1.save()
        
        test1 = Test.objects.get(id='key1')
        self.assertEqual(test1.test_datetime, self.TEST_DATETIME2)
        self.assertEqual(test1.test_text, self.TEST_TEXT2)
        
class BasicFunctionalityTest(TestCase):
    
    HOST_COUNT = 5
    
    def get_host_params_for_index(self, index):
        decimal_index = str(index)
        hex_index = hex(index)[2:]
        if len(hex_index) == 1:
            hex_index = '0' + hex_index
        id = 'key'+decimal_index
        mac = '00:01:02:03:04:'+hex_index
        ip = '10.0.0.'+decimal_index
        slice = self.s0 if index % 2 else self.s1
        
        return id, mac, ip, slice
    
    def setUp(self):
        # Create a couple slices
        self.s0 = Slice(id='key0',name='slice0')
        self.s0.save()
        self.s1 = Slice(id='key1',name='slice1')
        self.s1.save()
        
        # Create some hosts
        for i in range(self.HOST_COUNT):
            id, mac, ip, slice = self.get_host_params_for_index(i)
            h = Host(id=id, mac=mac,ip=ip,slice=slice)
            h.save()
    
            
    def test_create(self):
        """
        Tests that we correctly created the model instances
        """
        
        # Test that we have the slices we expect
        slice_query_set = Slice.objects.all()
        index = 0
        for slice in slice_query_set:
            self.assertEqual(slice.id, 'key' + str(index))
            self.assertEqual(slice.name, 'slice' + str(index))
            index += 1

        # There should have been exactly 2 slices created
        self.assertEqual(index, 2)
        
        host_query_set = Host.objects.all()
        index = 0
        for host in host_query_set:
            id, mac, ip, slice = self.get_host_params_for_index(index)
            index += 1

        # There should have been exactly 2 slices created
        self.assertEqual(index, self.HOST_COUNT)

    def test_update(self):
        s = Slice.objects.get(id='key0')
        s.name = 'foobar'
        s.save()
        #import time
        #time.sleep(5)
        s1 = Slice.objects.get(id='key0')
        #s2 = Slice.objects.get(id='key0')
        self.assertEqual(s1.name, 'foobar')
        #self.assertEqual(s2.name, 'foobar')
    
    def test_delete(self):
        host = Host.objects.get(id='key1')
        host.delete()
        hqs = Host.objects.filter(id='key1')
        count = hqs.count()
        self.assertEqual(count,0)
    
    def test_query_update(self):
        slice0 = Slice.objects.get(pk='key0')
        qs = Host.objects.filter(slice=slice0)
        qs.update(ip='192.168.1.1')
        qs = Host.objects.all()
        for host in qs:
            if host.slice.pk == 'key0':
                self.assertEqual(host.ip, '192.168.1.1')
            else:
                self.assertNotEqual(host.ip, '192.168.1.1')
    
    def test_cascading_delete(self):
        slice0 = Slice.objects.get(pk='key0')
        slice0.delete()
        hqs = Host.objects.all()
        count = hqs.count()
        self.assertEqual(count, 3)
        for host in hqs:
            self.assertEqual(host.slice_id, 'key1')
            
    def test_default_id(self):
        s = Slice(name='slice2')
        s.save()
        s2 = Slice.objects.get(name='slice2')
        self.assertEqual(s2.name, 'slice2')
        
SLICE_DATA_1 = ('key1', 'PCI')
SLICE_DATA_2 = ('key2', 'Eng1')
SLICE_DATA_3 = ('key3', 'Finance')
SLICE_DATA_4 = ('key4', 'blue')
SLICE_DATA_5 = ('key5', 'bluf')
SLICE_DATA_6 = ('key6', 'BLTSE')
SLICE_DATA_7 = ('key7', 'ZNCE')
SLICE_DATA_8 = ('key8', 'UNCLE')
SLICE_DATA_9 = ('key9', 'increment')

HOST_DATA_1 = ('key1', '00:01:02:03:04:05', '10.0.0.1', 'key1', (('foo3', 'bar3'), ('foo1','hello'), ('aaa', 'bbb')))
HOST_DATA_2 = ('key2', 'ff:fc:02:33:04:05', '192.168.0.55', 'key2', None)
HOST_DATA_3 = ('key3', 'ff:fc:02:03:04:01', '192.168.0.1', 'key2', (('cfoo3', 'bar3'), ('cfoo1','hello'), ('ddd', 'bbb')))
HOST_DATA_4 = ('key4', '55:44:33:03:04:05', '10.0.0.6', 'key1',None)
HOST_DATA_5 = ('key5', '10:01:02:03:04:05', '10.0.0.2', 'key1', None)
HOST_DATA_6 = ('key6', '33:44:55:03:04:05', '10.0.0.7', 'key3',None)
HOST_DATA_7 = ('key7', '10:01:02:03:04:05', '192.168.0.44', 'key1', None)

def create_slices(slice_data_list):
    for sd in slice_data_list:
        id, name = sd
        s = Slice(id=id,name=name)
        s.save()

def create_hosts(host_data_list):
    for hd in host_data_list:
        id,mac,ip,slice_id,tag_list = hd
        slice = Slice.objects.get(id=slice_id)
        h = Host(id=id,mac=mac,ip=ip,slice=slice)
        h.save()
        if tag_list != None:
            for tag in tag_list:
                name, value = tag
                t = Tag(name=name,value=value,host=h)
                t.save()
    
class QueryTest(TestCase):

    def setUp(self):
        create_slices((SLICE_DATA_1, SLICE_DATA_2, SLICE_DATA_3))
        create_hosts((HOST_DATA_1, HOST_DATA_6, HOST_DATA_5, HOST_DATA_7, HOST_DATA_3, HOST_DATA_2, HOST_DATA_4))
        
    def check_host_data(self, host, data):
        expected_id, expected_mac, expected_ip, expected_slice, expected_tag_list = data
        self.assertEqual(host.id, expected_id)
        self.assertEqual(host.mac, expected_mac)
        self.assertEqual(host.ip, expected_ip)
        self.assertEqual(host.slice.id, expected_slice)
        # TODO: For now we don't check the tag list
        
    def test_pk_query(self):
        h = Host.objects.get(id='key3')
        self.check_host_data(h, HOST_DATA_3)
    
        hqs = Host.objects.filter(id='key6')
        count = hqs.count()
        self.assertEqual(count, 1)
        h6 = hqs[0]
        self.check_host_data(h6, HOST_DATA_6)
    
        hqs = Host.objects.filter(id__gt='key4')
        count = hqs.count()
        self.assertEqual(count, 3)
        h5, h6, h7 = hqs[:]
        self.check_host_data(h5, HOST_DATA_5)
        self.check_host_data(h6, HOST_DATA_6)
        self.check_host_data(h7, HOST_DATA_7)
        
        hqs = Host.objects.filter(id__lte='key3')
        count = hqs.count()
        self.assertEqual(count, 3)
        h1, h2, h3 = hqs[:]
        self.check_host_data(h1, HOST_DATA_1)
        self.check_host_data(h2, HOST_DATA_2)
        self.check_host_data(h3, HOST_DATA_3)
        
        hqs = Host.objects.filter(id__gte='key3', id__lt='key7')
        count = hqs.count()
        self.assertEqual(count, 4)
        h3, h4, h5, h6 = hqs[:]
        self.check_host_data(h3, HOST_DATA_3)
        self.check_host_data(h4, HOST_DATA_4)
        self.check_host_data(h5, HOST_DATA_5)
        self.check_host_data(h6, HOST_DATA_6)
        
    def test_indexed_query(self):
        h = Host.objects.get(ip='10.0.0.7')
        self.check_host_data(h, HOST_DATA_6)
        
        hqs = Host.objects.filter(ip='192.168.0.1')
        h = hqs[0]
        self.check_host_data(h, HOST_DATA_3)
    
    def test_complex_query(self):
        hqs = Host.objects.filter(Q(id='key1') | Q(id='key3') | Q(id='key4')).order_by('id')
        count = hqs.count()
        self.assertEqual(count, 3)
        h1, h3, h4 = hqs[:]
        self.check_host_data(h1, HOST_DATA_1)
        self.check_host_data(h3, HOST_DATA_3)
        self.check_host_data(h4, HOST_DATA_4)

        s1 = Slice.objects.get(id='key1')
        
        hqs = Host.objects.filter(ip__startswith='10.', slice=s1)
        count = hqs.count()
        self.assertEqual(count, 3)
        h1, h4, h5 = hqs[:]
        self.check_host_data(h1, HOST_DATA_1)
        self.check_host_data(h4, HOST_DATA_4)
        self.check_host_data(h5, HOST_DATA_5)

        hqs = Host.objects.filter(ip='10.0.0.6', slice=s1)
        count = hqs.count()
        self.assertEqual(count, 1)
        h4 = hqs[0]
        self.check_host_data(h4, HOST_DATA_4)

        tqs = Tag.objects.filter(name='foo3', value='bar3')
        self.assertEqual(tqs.count(), 1)
        t = tqs[0]
        self.assertEqual(t.name, 'foo3')
        self.assertEqual(t.value, 'bar3')
        self.assertEqual(t.host_id, 'key1')
        
        hqs = Host.objects.filter((Q(ip__startswith='10.0') & Q(slice=s1)) | Q(mac__startswith='ff')).order_by('id')
        count = hqs.count()
        self.assertEqual(count, 5)
        h1, h2, h3, h4, h5 = hqs[:]
        self.check_host_data(h1, HOST_DATA_1)
        self.check_host_data(h2, HOST_DATA_2)
        self.check_host_data(h3, HOST_DATA_3)
        self.check_host_data(h4, HOST_DATA_4)
        self.check_host_data(h5, HOST_DATA_5)

    def test_exclude_query(self):
        hqs = Host.objects.exclude(ip__startswith="10")
        count = hqs.count()
        self.assertEqual(count,3)
        h2, h3, h7 = hqs[:]
        self.check_host_data(h2, HOST_DATA_2)
        self.check_host_data(h3, HOST_DATA_3)
        self.check_host_data(h7, HOST_DATA_7)

    def test_count(self):
        
        count = Host.objects.count()
        self.assertEqual(count, 7)
        
        count = Host.objects.all().count()
        self.assertEqual(count, 7)
        
        slice1 = Slice.objects.get(id='key1')
        qs = Host.objects.filter(slice=slice1)
        count = qs.count()
        #if count == 4:
        #    h1,h4,h5,h7 = qs[:]
        #else:
        #    h1,h4,h5,h7,h = qs[:]
        self.assertEqual(count, 4)

        qs = Slice.objects.filter(name__startswith='P')
        count = qs.count()
        self.assertEqual(count, 1)
        
        qs = Host.objects.filter(ip__startswith='10').order_by('slice_id')
        count = qs.count()
        self.assertEqual(count, 4)
    
    def test_query_set_slice(self):
        hqs = Host.objects.all()[2:6]
        count = hqs.count()
        h3, h4, h5, h6 = hqs[:]
        self.assertEqual(h3.id, 'key3')
        self.assertEqual(h4.id, 'key4')
        self.assertEqual(h5.id, 'key5')
        self.assertEqual(h6.id, 'key6')
        
    def test_order_by(self):
        # Test ascending order of all of the hosts
        qs = Host.objects.all().order_by('ip')
        h1, h2, h3, h4, h5, h6, h7 = qs[:]
        self.assertEqual(h1.id, 'key1')
        self.assertEqual(h2.id, 'key5')
        self.assertEqual(h3.id, 'key4')
        self.assertEqual(h4.id, 'key6')
        self.assertEqual(h5.id, 'key3')
        self.assertEqual(h6.id, 'key7')
        self.assertEqual(h7.id, 'key2')
        
        # Test descending order of all of the hosts
        qs = Host.objects.all().order_by('-ip')
        h1, h2, h3, h4, h5, h6, h7 = qs[:]
        self.assertEqual(h1.id, 'key2')
        self.assertEqual(h2.id, 'key7')
        self.assertEqual(h3.id, 'key3')
        self.assertEqual(h4.id, 'key6')
        self.assertEqual(h5.id, 'key4')
        self.assertEqual(h6.id, 'key5')
        self.assertEqual(h7.id, 'key1')

        # Test multiple ordering criteria
        qs = Host.objects.all().order_by('slice_id', 'ip')
        h1, h2, h3, h4, h5, h6, h7 = qs[:]
        self.assertEqual(h1.id, 'key1')
        self.assertEqual(h2.id, 'key5')
        self.assertEqual(h3.id, 'key4')
        self.assertEqual(h4.id, 'key7')
        self.assertEqual(h5.id, 'key3')
        self.assertEqual(h6.id, 'key2')
        self.assertEqual(h7.id, 'key6')

        # Test multiple ordering criteria
        qs = Host.objects.all().order_by('-slice_id', 'ip')
        h1, h2, h3, h4, h5, h6, h7 = qs[:]
        self.assertEqual(h1.id, 'key6')
        self.assertEqual(h2.id, 'key3')
        self.assertEqual(h3.id, 'key2')
        self.assertEqual(h4.id, 'key1')
        self.assertEqual(h5.id, 'key5')
        self.assertEqual(h6.id, 'key4')
        self.assertEqual(h7.id, 'key7')

        # Currently the nonrel code doesn't handle ordering that spans tables/column families
        #=======================================================================
        # qs = Host.objects.all().order_by('slice__name', 'id')
        # h2, h3, h6, h1, h5, h4, h7 = qs[:]
        # self.assertEqual(h2.id, 'key2')
        # self.assertEqual(h3.id, 'key3')
        # self.assertEqual(h6.id, 'key6')
        # self.assertEqual(h1.id, 'key1')
        # self.assertEqual(h5.id, 'key5')
        # self.assertEqual(h4.id, 'key4')
        # self.assertEqual(h7.id, 'key7')
        #=======================================================================


class OperationTest(TestCase):

    def setUp(self):
        create_slices((SLICE_DATA_1, SLICE_DATA_2, SLICE_DATA_3, SLICE_DATA_4, SLICE_DATA_5,
                       SLICE_DATA_6, SLICE_DATA_7, SLICE_DATA_8, SLICE_DATA_9))
    
    def test_range_ops(self):
        qs = Slice.objects.filter(name__gt='PCI')
        count = qs.count()
        self.assertEqual(count, 5)
        s4,s5,s7,s8,s9 = qs[:]
        self.assertEqual(s4.id,'key4')
        self.assertEqual(s5.id,'key5')
        self.assertEqual(s7.id,'key7')
        self.assertEqual(s8.id,'key8')
        self.assertEqual(s9.id,'key9')
        
        qs = Slice.objects.filter(name__gte='bluf',name__lte='bluf')
        count = qs.count()
        self.assertEqual(count, 1)
        s5 = qs[0]
        self.assertEqual(s5.id, 'key5')
        
        qs = Slice.objects.filter(name__gt='blue', name__lte='bluf')
        count = qs.count()
        self.assertEqual(count, 1)
        s5 = qs[0]
        self.assertEqual(s5.id, 'key5')
        
        qs = Slice.objects.filter(name__exact='blue')
        count = qs.count()
        self.assertEqual(count, 1)
        s4 = qs[0]
        self.assertEqual(s4.id, 'key4')

    def test_other_ops(self):
        
        qs = Slice.objects.filter(id__in=['key1','key4','key6','key9'])
        count = qs.count()
        self.assertEqual(count, 4)
        s1,s4,s6,s9 = qs[:]
        self.assertEqual(s1.id,'key1')
        self.assertEqual(s4.id,'key4')
        self.assertEqual(s6.id,'key6')
        self.assertEqual(s9.id,'key9')
        
        qs = Slice.objects.filter(name__startswith='bl')
        count = qs.count()
        self.assertEqual(count, 2)
        s4,s5 = qs[:]
        self.assertEqual(s4.id,'key4')
        self.assertEqual(s5.id,'key5')
        
        qs = Slice.objects.filter(name__endswith='E')
        count = qs.count()
        self.assertEqual(count, 3)
        s6,s7,s8 = qs[:]
        self.assertEqual(s6.id,'key6')
        self.assertEqual(s7.id,'key7')
        self.assertEqual(s8.id,'key8')
        
        qs = Slice.objects.filter(name__contains='NC')
        count = qs.count()
        self.assertEqual(count, 2)
        s7,s8 = qs[:]
        self.assertEqual(s7.id,'key7')
        self.assertEqual(s8.id,'key8')

        qs = Slice.objects.filter(name__istartswith='b')
        count = qs.count()
        self.assertEqual(count, 3)
        s4,s5,s6 = qs[:]
        self.assertEqual(s4.id,'key4')
        self.assertEqual(s5.id,'key5')
        self.assertEqual(s6.id,'key6')

        qs = Slice.objects.filter(name__istartswith='B')
        count = qs.count()
        self.assertEqual(count, 3)
        s4,s5,s6 = qs[:]
        self.assertEqual(s4.id,'key4')
        self.assertEqual(s5.id,'key5')
        self.assertEqual(s6.id,'key6')

        qs = Slice.objects.filter(name__iendswith='e')
        count = qs.count()
        self.assertEqual(count, 5)
        s3,s4,s6,s7,s8 = qs[:]
        self.assertEqual(s3.id,'key3')
        self.assertEqual(s4.id,'key4')
        self.assertEqual(s6.id,'key6')
        self.assertEqual(s7.id,'key7')
        self.assertEqual(s8.id,'key8')

        qs = Slice.objects.filter(name__icontains='nc')
        count = qs.count()
        self.assertEqual(count, 4)
        s3,s7,s8,s9 = qs[:]
        self.assertEqual(s3.id,'key3')
        self.assertEqual(s7.id,'key7')
        self.assertEqual(s8.id,'key8')
        self.assertEqual(s9.id,'key9')

        qs = Slice.objects.filter(name__regex='[PEZ].*')
        count = qs.count()
        self.assertEqual(count, 3)
        s1,s2,s7 = qs[:]
        self.assertEqual(s1.id,'key1')
        self.assertEqual(s2.id,'key2')
        self.assertEqual(s7.id,'key7')

        qs = Slice.objects.filter(name__iregex='bl.*e')
        count = qs.count()
        self.assertEqual(count, 2)
        s4,s6 = qs[:]
        self.assertEqual(s4.id,'key4')
        self.assertEqual(s6.id,'key6')

class Department(models.Model):
    name = models.CharField(primary_key=True, max_length=256)
    
    def __unicode__(self):
            return self.title

class DepartmentRequest(models.Model):
    from_department = models.ForeignKey(Department, related_name='froms')
    to_department = models.ForeignKey(Department, related_name='tos')

class RestTestMultipleForeignKeys(TestCase):

    def test_it(self):
    
        for i in range(0,4):
            department = Department()
            department.name = "id_" + str(i)
            department.save()
            
        departments = Department.objects.order_by('name')
        d0 = departments[0]
        d1 = departments[1]
        d2 = departments[2]
        d3 = departments[3]
    
        req = DepartmentRequest()
        req.from_department = d0
        req.to_department = d1
        req.save()
    
        req = DepartmentRequest()
        req.from_department = d2
        req.to_department = d1
        req.save()
    
        rs = DepartmentRequest.objects.filter(from_department = d3, to_department = d1)
        self.assertEqual(rs.count(), 0)

        rs = DepartmentRequest.objects.filter(from_department=d0, to_department=d1)
        self.assertEqual(rs.count(), 1)
        req = rs[0]
        self.assertEqual(req.from_department, d0)
        self.assertEqual(req.to_department, d1)

        rs = DepartmentRequest.objects.filter(to_department=d1).order_by('from_department')
        self.assertEqual(rs.count(), 2)
        req = rs[0]
        self.assertEqual(req.from_department, d0)
        self.assertEqual(req.to_department, d1)
        req = rs[1]
        self.assertEqual(req.from_department, d2)
        self.assertEqual(req.to_department, d1)


class EmptyModel(models.Model):
    pass

class EmptyModelTest(TestCase):
    
    def test_empty_model(self):
        em = EmptyModel()
        em.save()
        qs = EmptyModel.objects.all()
        self.assertEqual(qs.count(), 1)
        em2 = qs[0]
        self.assertEqual(em.id, em2.id)

class CompoundKeyTest(TestCase):
    
    def test_construct_with_no_id(self):
        ckm = CompoundKeyModel(name='foo', index=6, extra='hello')
        ckm.save();
        ckm = CompoundKeyModel.objects.all()[0]
        self.assertEqual(ckm.id, 'foo|6')
    
    def test_construct_with_id(self):
        ckm = CompoundKeyModel(id='foo|6', name='foo', index=6, extra='hello')
        ckm.save();
        ckm = CompoundKeyModel.objects.all()[0]
        self.assertEqual(ckm.id, 'foo|6')

    def test_malformed_id(self):
        ckm = CompoundKeyModel(id='abc', name='foo', index=6, extra='hello')
        self.failUnlessRaises(DatabaseError, ckm.save)
        
    def test_construct_mismatched_id(self):
        ckm = CompoundKeyModel(id='foo|5', name='foo', index=6, extra='hello')
        self.failUnlessRaises(DatabaseError, ckm.save)
        
    def test_update_non_key_field(self):
        ckm = CompoundKeyModel(name='foo', index=6, extra='hello')
        ckm.save();
        ckm = CompoundKeyModel.objects.all()[0]
        ckm.extra = 'goodbye'
        ckm.save();
        ckm = CompoundKeyModel.objects.all()[0]
        self.assertEqual(ckm.extra, 'goodbye')

    def test_update_no_id(self):
        ckm = CompoundKeyModel(id='foo|6', name='foo', index=6, extra='hello')
        ckm.save();
        ckm = CompoundKeyModel(name='foo', index=6, extra='goodbye')
        ckm.save();
        ckm = CompoundKeyModel.objects.all()[0]
        self.assertEqual(ckm.extra, 'goodbye')
        
    def test_update_mismatched_id(self):
        ckm = CompoundKeyModel(name='foo', index=6, extra='hello')
        ckm.save();
        ckm = CompoundKeyModel.objects.all()[0]
        ckm.name = 'bar'
        self.failUnlessRaises(DatabaseError, ckm.save)

    def test_delete_by_id(self):
        ckm = CompoundKeyModel(name='foo', index=6, extra='hello')
        ckm.save();
        ckm = CompoundKeyModel.objects.get(pk='foo|6')
        ckm.delete()
        qs = CompoundKeyModel.objects.all()
        self.assertEqual(len(qs), 0)
    
    def test_delete_by_fields(self):
        ckm = CompoundKeyModel(name='foo', index=6, extra='hello')
        ckm.save()
        qs = CompoundKeyModel.objects.filter(name='foo', index=6)
        qs.delete()
        qs = CompoundKeyModel.objects.all()
        self.assertEqual(len(qs), 0)
        
        
    def test_custom_separator(self):
        s = Slice(id='default')
        s.save()
        ckm = CompoundKeyModel2(slice=s, name='foo', index=6, extra='hello')
        ckm.save();
        ckm = CompoundKeyModel2.objects.all()[0]
        self.assertEqual(ckm.id, 'default#foo#6')
        
########NEW FILE########
__FILENAME__ = views
# Create your views here.

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import *

# Uncomment the next two lines to enable the admin:
from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
    # Example:
    # (r'^django_cassandra_backend/', include('test_db_backend.foo.urls')),

    # Uncomment the admin/doc line below and add 'django.contrib.admindocs' 
    # to INSTALLED_APPS to enable admin documentation:
    # (r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    (r'^admin/', include(admin.site.urls)),
)

########NEW FILE########
