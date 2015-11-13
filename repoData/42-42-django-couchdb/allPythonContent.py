__FILENAME__ = base
"""
CouchDB backend for Django.

Requires couchdb Python library (http://couchdb-python.googlecode.com/).
"""

from django.core.exceptions import ImproperlyConfigured
from django.db.backends import *

try:
    import couchdb
except ImportError, e:
    raise ImproperlyConfigured, 'Error loading "couchdb" module: %s' % e


from creation import *
from introspection import *
from operations import *
from utils import *

class DatabaseFeatures(BaseDatabaseFeatures):
    """
    @summary: Database features of Django CouchDB backend.
    """
    can_use_chunked_reads = False
    needs_datetime_string_cast = False
    update_can_self_select = False
    uses_custom_query_class = True

class DatabaseWrapper(BaseDatabaseWrapper):
    """
    @summary: Database wrapper for Django CouchDB backend.
    """
    def __init__(self, *args, **kwargs):
        super(DatabaseWrapper, self).__init__(*args, **kwargs)

        self.creation = DatabaseCreation(self)
        self.features = DatabaseFeatures()
        self.introspection = DatabaseIntrospection(self)
        self.ops = DatabaseOperations()
        self.validation = BaseDatabaseValidation()

    def _cursor(self, settings=None):
        if self.connection is None:
            if settings is not None:
                from django.conf import settings
            if not settings.DATABASE_HOST:
                raise ImproperlyConfigured, \
                      'Please, fill out DATABASE_HOST in the settings module ' \
                      'before using the database.'
            self.connection = ConnectionWrapper(settings.DATABASE_HOST,
                                                settings.DATABASE_USER,
                                                settings.DATABASE_PASSWORD)
        return self.connection.cursor()

    def make_debug_cursor(self, cursor):
        return DebugCursorWrapper(cursor)



########NEW FILE########
__FILENAME__ = creation
from django.db.backends.creation import BaseDatabaseCreation
from utils import *


__all__ = ('DatabaseCreation',)


class DatabaseCreation(BaseDatabaseCreation):
    """
    @summary: Django CouchDB backend's implementation for Django's
    BaseDatabaseCreation class.
    """
    class DummyDataTypes:
        def __getitem__(self, key): return "type"

    data_types = DummyDataTypes()


    def sql_create_model(self, model, style, seen_models=set()):
        from django.db import models
        data, pending_references = {}, {}

        opts = model._meta


        # Browsing through fields to find references
        for field in opts.local_fields:
            col_type = field.db_type()

            if col_type is None:
                continue

            options = {}

            if not field.null:
                options['NOT NULL'] = True
            if field.primary_key:
                options['PRIMARY KEY'] = True
            if field.unique:
                options['UNIQUE'] = True
            if isinstance(field, models.BooleanField) or \
               isinstance(field, models.NullBooleanField):
                options['BOOLEAN'] = True

            if field.rel:
                ref_fake_sql, pending = \
                    self.sql_for_inline_foreign_key_references(field,
                                                               seen_models,
                                                               style)

                if pending:
                    pr = pending_references.setdefault(field.rel.to, []).\
                                            append((model, field))

            data.update({field.column: options})

        # Makes fake SQL
        fake_output = [SQL('create', (opts, data) )]

        return fake_output, pending_references

    def sql_for_inline_foreign_key_references(self, field, known_models, style):
        pending = field.rel.to in known_models
        return [], pending

    def sql_for_many_to_many_field(self, model, field, style):
        return []
        """
        """


    def sql_for_pending_references(self, model, style, pending_references):
        fake_output = []
        opts = model._meta
        if model in pending_references:
            for rel_class, f in pending_references[model]:
                rel_opts = rel_class._meta
                r_table = rel_opts.db_table
                r_col = f.column
                table = opts.db_table
                #~ col = opts.get_field(f.rel.field_name).column
                fake_output.append(SQL('add_foreign_key', (r_table, r_col, table)))
            del pending_references[model]
        return fake_output

########NEW FILE########
__FILENAME__ = introspection
from django.db.backends import BaseDatabaseIntrospection


__all__ = ('DatabaseIntrospection',)

class DatabaseIntrospection(BaseDatabaseIntrospection):
    """
    @summary: Django CouchDB backend's implementation for Django's
    BaseDatabaseIntrospection class.
    """
    def get_table_list(self, cursor):
        return list(cursor.server.__iter__())

    def get_table_description(self, cursor, table_name):
        return cursor.server[table_name]['_meta']

########NEW FILE########
__FILENAME__ = nodes
def unquote_name(name):
    if name.startswith('"') and name.endswith('"'):
        return name[1:-1]
    return name

def process_name(name):
    if name =='id':
        return '_id'
    else:
        return name

def operator_lookup(table_alias, name, operator, params):
    return "(typeof "+table_alias+" == \"undefined\" || " + \
                table_alias+ "."+process_name(name) + " %s " % (operator,) + "\"%s\")" % tuple(params)

class Lookup(object):
    operators = {
        'exact': '==',
        #~ 'iexact': '= UPPER(%s)',
        #~ 'contains': 'LIKE %s',
        #~ 'icontains': 'LIKE UPPER(%s)',
        #~ 'regex': '~ %s',
        #~ 'iregex': '~* %s',
        'gt': '>',
        'gte': '>=',
        'lt': '<',
        'lte': '<=',
        #~ 'startswith': 'LIKE %s',
        #~ 'endswith': 'LIKE %s',
        #~ 'istartswith': 'LIKE UPPER(%s)',
        #~ 'iendswith': 'LIKE UPPER(%s)',
    }

    def __init__(self, table_alias, name, db_type, lookup_type, value_annot, params):
        if table_alias is None:
            self.table_alias = '_d'
        else:
            self.table_alias = unquote_name(table_alias)
        self.name = name
        self.db_type = db_type
        self.lookup_type = lookup_type
        self.value_annot = value_annot
        self.params = params

        self.as_sql = getattr(self,'lookup_'+lookup_type, None)
        if self.as_sql is None:
            if lookup_type in self.operators:
                self.as_sql = lambda : operator_lookup(self.table_alias,
                                                       self.name,
                                                       self.operators[lookup_type],
                                                       self.params)
            else:
                self.as_sql = self.dummy_lookup

    def dummy_lookup(self, *args):
        raise TypeError('Invalid lookup_type: %r' % self.lookup_type)


    def lookup_in(self):
        params = '{'+','.join('%s: 1' % x for x in self.params) + '}'
        return "(typeof "+self.table_alias+" == \"undefined\" || " + \
                self.table_alias+ "." + process_name(self.name) + " in %s)" % params


def get_where_node(BaseNode):
    class WhereNode(BaseNode):
        def make_atom(self, child, qn):
            #~ table_alias, name, db_type, lookup_type, value_annot, params = child
            lookup = Lookup(*child)
            return lookup.as_sql(), []
    return WhereNode


########NEW FILE########
__FILENAME__ = operations
from django.db.backends import BaseDatabaseOperations
from utils import *
from queries import *
from nodes import *

__all__ = ('DatabaseOperations',)

class DatabaseOperations(BaseDatabaseOperations):
    """
    @summary: Django CouchDB backend's implementation for Django's
    BaseDatabaseOperations class.
    """
    def quote_name(self, name):
        if name.startswith('"') and name.endswith('"'):
            return name # Quoting once is enough.
        return '"%s"' % name

    def last_insert_id(self, cursor, table_name, pk_name):
        s = Sequence(cursor.server, '%s_seq' % (table_name, ))
        return s.currval()

    def query_class(self, DefaultQueryClass):
        class CustomQuery(DefaultQueryClass):
            def clone(self, klass=None, **kwargs):
                if klass:
                    if klass.__name__ == 'InsertQuery':
                        klass = get_insert_query(klass)
                    elif klass.__name__ == 'UpdateQuery':
                        klass = get_update_query(klass) # update == insert
                    elif klass.__name__ == 'DeleteQuery':
                        klass = get_delete_query(klass)
                return super(CustomQuery, self).clone(klass, **kwargs)
            def __new__(cls, *args, **kwargs):
                if cls.__name__ == 'InsertQuery':
                    NewInsertQuery = get_insert_query(cls)
                    obj =  super(CustomQuery, NewInsertQuery).__new__(NewInsertQuery, *args, **kwargs)
                elif cls.__name__ == 'UpdateQuery':
                    NewUpdateQuery = get_update_query(cls) # update == insert
                    obj =  super(CustomQuery, NewUpdateQuery).__new__(NewUpdateQuery, *args, **kwargs)
                elif cls.__name__ == 'DeleteQuery':
                    NewDeleteQuery = get_delete_query(cls)
                    obj =  super(CustomQuery, NewDeleteQuery).__new__(NewDeleteQuery, *args, **kwargs)
                else:
                    obj =  super(CustomQuery, cls).__new__(cls, *args, **kwargs)
                return obj
            def __init__(self, model, connection, where=None):
                from django.db.models.sql.where import WhereNode
                where = where or WhereNode
                NewWhereNode = get_where_node(where)
                super(CustomQuery, self).__init__(model, connection, where=NewWhereNode)
            def as_sql(self, with_limits=True, with_col_aliases=False):
                """
                Creates the SQL for this query. Returns the SQL string and list of
                parameters.

                If 'with_limits' is False, any limit/offset information is not included
                in the query.
                """
                self.pre_sql_setup()
                out_cols = self.get_columns(with_col_aliases)
                ordering = self.get_ordering()

                # This must come after 'select' and 'ordering' -- see docstring of
                # get_from_clause() for details.
                from_, f_params = self.get_from_clause()

                where, w_params = self.where.as_sql(qn=self.quote_name_unless_alias)
                params = []
                for val in self.extra_select.itervalues():
                    params.extend(val[1])

                SQL_params = []
                #~ result = ['SELECT']
                if self.distinct:
                    #~ result.append('DISTINCT')
                    SQL_params.append(True)
                else:
                    SQL_params.append(False)

                SQL_params.append(out_cols + self.ordering_aliases)
                SQL_params.append(from_)

                params.extend(f_params)

                if where:
                    SQL_params.append(where)
                    params.extend(w_params)
                else:
                    SQL_params.append(None)
                if self.extra_where:
                    SQL_params.append(self.extra_where)
                else:
                    SQL_params.append(None)

                if self.group_by:
                    grouping = self.get_grouping()
                    SQL_params.append(grouping)
                else:
                    SQL_params.append(None)

                if self.having:
                    having, h_params = self.get_having()
                    SQL_params.append(having)
                    params.extend(h_params)
                else:
                    SQL_params.append(None)

                if ordering:
                    SQL_params.append(ordering)
                else:
                    SQL_params.append(None)

                if with_limits:
                    SQL_params.append((self.low_mark, self.high_mark))
                else:
                    SQL_params.append(None)

                params.extend(self.extra_params)
                return SQL('select', SQL_params), tuple(params)

        return CustomQuery


########NEW FILE########
__FILENAME__ = queries
from utils import *

def get_insert_query(BaseQuery):
    class InsertQuery(BaseQuery):
        def as_sql(self):
            return SQL('insert',(self.model._meta.db_table, self.columns, self.values)), self.params
    return InsertQuery

def get_update_query(BaseQuery):
    class UpdateQuery(BaseQuery):
        def as_sql(self):
            where, w_params = self.where.as_sql(qn=self.quote_name_unless_alias)
            return SQL('update',(self.model._meta.db_table, self.values, where)), w_params
    return UpdateQuery


def get_delete_query(BaseQuery):
    class DeleteQuery(BaseQuery):
        def as_sql(self):
            assert len(self.tables) == 1, \
                    "Can only delete from one table at a time."
            where, params = self.where.as_sql()
            return SQL('delete',(self.quote_name_unless_alias(self.tables[0]), where)), tuple(params)
    return DeleteQuery

########NEW FILE########
__FILENAME__ = utils
from time import time
from itertools import izip
from nodes import Lookup
import couchdb


__all__ = ('ConnectionWrapper', 'CursorWrapper', 'DatabaseError',
           'DebugCursorWrapper', 'IntegrityError', 'InternalError',
           'SQL', 'Sequence')

DatabaseError = couchdb.ServerError
IntegrityError = couchdb.ResourceConflict

class Sequence(object):
    def __init__(self, server, name):
        if not 'sequences' in server.__iter__():
            table = server.create('sequences')
        else:
            table = server['sequences']

        try:
            seq = table[name]
        except couchdb.ResourceNotFound:
            seq = {'nextval': 1}
        self._nextval = seq['nextval']
        seq['nextval']=seq['nextval'] + 1
        table[name] = seq

    def nextval(self): # doesn't increment
        return self._nextval

    def currval(self):
        return self._nextval - 1

class InternalError(DatabaseError):
    """
    @summary: Exception raised when the database encounters an internal error,
    e.g. the cursor is not valid anymore, the transaction is out of sync, etc.
    It must be a subclass of DatabaseError.
    """

def unquote_name(name):
    if name.startswith('"') and name.endswith('"'):
        return name[1:-1]
    return name

WHERE_REPLACEMENTS = {'AND': '&&', 'OR': '||', 'NOT': '!'}

def process_where(where):
    for key,val in WHERE_REPLACEMENTS.iteritems():
        where = where.replace(key, val) # it is dangerous !!!
    return where

def process_views(meta, columns, views):
    for column, view in izip(columns, views):
        options = meta.get(column, [])
        if 'BOOLEAN' in options:
            yield '__RAW__'
        else:
            yield view

class SQL(object):
    def __init__(self, command, params):
        self.command = command
        self.params = params

    def execute_create(self, server):
        # self.params --- (model opts, field_params)
        opts = self.params[0]
        table = server.create(opts.db_table)
        meta = {'_id': '_meta'}
        if opts.unique_together:
            meta['UNIQUE'] = list(opts.unique_together)
        for field, field_params in self.params[1].iteritems():
            params_list = []
            for param, value in field_params.iteritems():
                if value:
                    params_list.append(param)
            meta[field] = params_list
        table['_meta'] = meta

    def execute_add_foreign_key(self, server):
        # self.params - (r_table, r_col, table)
        table = server[self.params[0]]
        meta = table['_meta']
        try:
            refs = meta['REFERENCES']
        except KeyError:
            refs = []
        refs.append('%s=%s' % (self.params[1], self.params[2]))
        meta['REFERENCES'] = refs
        table['_meta'] = meta

    def execute_insert(self, server, params):
        # self.params --- (table name, columns, values)
        table = server[self.params[0]]
        if not 'id' in self.params[1]:
            seq = Sequence(server, ("%s_seq"% (self.params[0], )))
            id = str(seq.nextval())
            obj = {'_id': id}
        else:
            obj = {}

        views = process_views(table['_meta'], self.params[1], self.params[2])
        for key, view, val in izip(self.params[1], views, params):
            if key=='id':
                key = '_id'
            if view == '__RAW__':
                obj[key] = val
            else:
                obj[key] = view % val
        table[obj['_id']] = obj

    def execute_update(self, server, params):
        # self.params --- (table name, column-values, where)
        table_name = self.params[0]
        table = server[table_name]
        view = self.simple_select(server, table, (table_name+'.'+'"id"',),
                                  self.params[2], params)
        columns, values, views = [], [], []
        for col,val,v in self.params[1]:
            columns.append(unquote_name(col))
            values.append(val)
            views.append(v)
        views = process_views(table['_meta'], columns, views)
        for d in view:
            obj = table[d.id]
            for key, view, val in izip(columns, views, values):
                if key=='id':
                    key = '_id'
                if view == '__RAW__':
                    obj[key] = val
                else:
                    obj[key] = view % val
            table[obj['_id']] = obj

    def simple_select(self,server, table, columns, where, params, alias = None):
        if alias:
            table_name = alias
        else:
            table_name = table.name
        map_fun = "function ("+table_name+") { var _d = " + table_name+ ";"
        map_fun += "if ("+table_name+"._id!=\"_meta\") {"
        if where:
            map_fun += "if ("+process_where(where)+") {"

        # just selecting, not where
        map_fun += "result = ["
        processed_columns = []
        for x in columns:
            if 'AS' in x:
                x = x[:x.find('AS')]
            if '.' in x: # bad usage. Dot can occur in arithmetic operations!!!
                left, right = x.split('.')
                left = unquote_name(left)
                right = unquote_name(right)
                if right=='id':
                    right = '_id'
                if left==table_name:
                    if right=='_id':
                        processed_columns.append('parseInt('+left + '.' + right+')')
                    else:
                        processed_columns.append(left + '.' + right)
            else:
                processed_columns.append(x)
        str_columns = ','.join(processed_columns)
        map_fun += str_columns;
        map_fun += "] ;emit("+table_name+"._id, result);"
        map_fun += "}}"
        if where:
            map_fun += '}'
        #~ print "MAP_FUN:", map_fun
        view = table.query(map_fun)
        return view

    def execute_simple_select(self, server, cursor, params):
        # self.params --- (distinct flag, table columns, from, where, extra where,
        #             group by, having, ordering, limits)
        table_name = self.params[2][0]
        table = server[unquote_name(table_name)]
        if len(self.params[1])==1 and self.params[1][0]=='COUNT(*)':
            view = self.simple_select(server, table,
                                      (table_name+'.'+'"id"',), self.params[3], params)
            cursor.save_one(len(view))
        else:
            cursor.save_view(self.simple_select(server, table,
                                           self.params[1], self.params[3], params))


    def execute_select(self, server, cursor, params):
        # self.params --- (distinct flag, table columns, from, where, extra where,
        #             group by, having, ordering, limits)
        if len(self.params[2]) == 1:
            return self.execute_simple_select(server,cursor,params)
        else:
            leftmost_table_name = self.params[2][0]
            lookups = []
            for x in self.params[2][1:]:
                left, right = x.split('ON')
                left = left.split()
                right = right[2:-1].split()
                if left[0] == 'INNER':
                    if len(left) == 4: # in case of alias
                        table_name = left[2]
                        alias = left[3]
                    else:
                        table_name = left[2]
                        alias = unquote_name(left[2])
                    table = server[unquote_name(table_name)]
                    view = self.simple_select(server, table,
                                              (table_name+'.'+'"id"',),
                                              self.params[3], params, alias=alias)
                    ids = (d.id for d in view)
                    # table_alias, name, db_type, lookup_type, value_annot, params
                    l = Lookup(leftmost_table_name, unquote_name(right[0].split('.')[1]),
                               None, 'in', None, ids)
                    lookups.append(l.as_sql())
            lookup_str = ' AND '.join(lookups)
            table = server[unquote_name(leftmost_table_name)]
            if len(self.params[1])==1 and self.params[1][0]=='COUNT(*)':
                joined_view = self.simple_select(server, table,
                                                 (leftmost_table_name+'.'+'"id"',),
                                                 lookup_str, params)
                cursor.save_one(len(joined_view))
            else:
                joined_view = self.simple_select(server, table,
                                                 self.params[1],
                                                 lookup_str, params)
                cursor.save_view(joined_view)

    def execute_delete(self, server, params):
        # self.params ---(table_name, where)
        table_name = self.params[0]
        where = self.params[1]
        table = server[unquote_name(table_name)]
        view = self.simple_select(server, table, (table_name+'.'+'"id"',),
                                  where, params)
        for x in view:
            del table[x.id]

    def execute_sql(self, cursor, params):
        server = cursor.server
        if self.command == 'create':
            return self.execute_create(server)
        elif self.command == 'add_foreign_key':
            return self.execute_add_foreign_key(server)
        elif self.command == 'insert':
            return self.execute_insert(server, params)
        elif self.command == 'update':
            return self.execute_update(server, params)
        elif self.command == 'select':
            return self.execute_select(server, cursor, params)
        elif self.command == 'delete':
            return self.execute_delete(server, params)

    def __unicode__(self):
        return u"command %s with params = %s" % (self.command, self.params)

class ConnectionWrapper(object):
    """
    @summary: DB-API 2.0 Connection object for Django CouchDB backend.
    """
    def __init__(self, host, username, password, cache=None, timeout=None):
        self._cursor = None
        self._server = couchdb.Server(host, cache, timeout)
        self._username, self._password = username, password

    def close(self):
        if self._server is not None:
            self._server = None

    def commit(self):
        #~ raise NotImplementedError
        pass

    def cursor(self):
        if self._server is None:
            raise InternalError, 'Connection to server was closed.'

        if self._cursor is None:
            self._cursor = CursorWrapper(self._server,
                                         self._username,
                                         self._password)
        return self._cursor

    def rollback(self):
        #~ raise NotImplementedError
        pass

class CursorWrapper(object):
    """
    @summary: DB-API 2.0 Cursor object for Django CouchDB backend.
    """
    def __init__(self, server, username=None, password=None):
        assert isinstance(server, couchdb.Server), \
            'Please, supply ``couchdb.Server`` instance as first argument.'

        self.server = server
        self._username, self._password = username, password
        self.saved_view = None
        self.saved_one = None

    def execute(self, sql, params=()):
        if isinstance(sql, SQL):
            sql.execute_sql(self, params)

    def save_view(self, view): # fetch here?
        self.saved_view = view
        self.saved_view_offset = 0

    @property
    def rowcount(self):
        if self.saved_view:
            return len(self.saved_view)
        else:
            return 0

    def save_one(self, one):
        self.saved_one = one

    def fetchone(self):
        return [self.saved_one]

    def fetchmany(self, count):
        ret = list(self.saved_view)[self.saved_view_offset:self.saved_view_offset+count]
        self.saved_view_offset += count
        return map(lambda x:x.value,ret)

class DebugCursorWrapper(CursorWrapper):
    """
    @summary: Special cursor class, that stores all queries to database for
    current session.
    """
    def __init__(self, cursor):
        super(DebugCursorWrapper, self).__init__(cursor.server,
                                                 cursor._username,
                                                 cursor._password)

    def execute(self, sql, params=()):
        start = time()
        try:
            #~ print "SQL:", unicode(sql)
            #~ print "PARAMS:", params
            super(DebugCursorWrapper, self).execute(sql, params)
        finally:
            stop = time()
            #~ sql = self.db.ops.last_executed_query(self.cursor, sql, params)
            #~ self.db.queries.append({
                #~ 'sql': sql,
                #~ 'time': "%.3f" % (stop - start),
            #~ })




########NEW FILE########
__FILENAME__ = admin
from django.contrib import admin

from djcouchtest.core.models import *


admin.site.register(Foo)
admin.site.register(Boo)

########NEW FILE########
__FILENAME__ = models
from django.db import models

# Create your models here.

class Boo(models.Model):
    title = models.CharField(max_length=20)
    slug = models.SlugField()
    class Meta:
        unique_together = ('title', 'slug')

class Foo(models.Model):
    boo = models.ForeignKey(Boo)
    boo2 = models.ForeignKey(Boo, related_name="foo2_set")


class Boo2(models.Model):
    flag = models.BooleanField()

########NEW FILE########
__FILENAME__ = test_auth
from django.core.management import call_command
from django.contrib.auth.models import User
from django.contrib.auth import authenticate
from django.conf import settings
from nose.tools import assert_equal
from couchdb import *


from djcouchtest.core.tests.utils import CouchDBMock

class TestAuthBackend(CouchDBMock):
    def test_syncdb(self):
        s = Server(settings.DATABASE_HOST)
        if 'auth_user' in s:
            del s['auth_user'] # can not use User.objects.all().delete() due to ManyToMany fields
        call_command('syncdb', interactive=False, verbosity=0)
        user = User.objects.create_user('foo', 'foo@gmail.com', 'foobardummy')
        user.save()
        new_user = authenticate(username='foo', password='foobardummy')
        assert new_user, "User can't be authenticated"
        assert_equal(user, new_user)


########NEW FILE########
__FILENAME__ = test_creation
from django.core.management import call_command
from django.db.models import Q
from nose.tools import assert_equal

from djcouchtest.core.models import Boo, Foo
from djcouchtest.core.tests.utils import CouchDBMock

class TestCreation(CouchDBMock):
    def test_syncdb(self):
        call_command('syncdb', interactive=False, verbosity=0)
        from django.db import connection
        cursor = connection.cursor()
        assert "core_boo" in connection.introspection.get_table_list(cursor)
        assert "core_foo" in connection.introspection.get_table_list(cursor)
        description = connection.introspection.get_table_description(
            cursor, 'core_boo')
        assert description, "Description for core_boo must not be None"
        assert 'id' in description, description
        assert 'title' in description, description
        assert 'NOT NULL' in description['title']
        assert 'PRIMARY KEY' in description['id']
        assert_equal(description['UNIQUE'],[[u'title', u'slug']])
        description = connection.introspection.get_table_description(
            cursor, 'core_foo')
        assert description, "Description for core_foo must not be None"
        assert 'boo_id' in description, description
        assert_equal(description['REFERENCES'],
                     [u'boo_id=core_boo', u'boo2_id=core_boo'])

    def test_fixtures(self):
        call_command('syncdb', interactive=False, verbosity=0)
        Boo.objects.all().delete()
        Foo.objects.all().delete()
        call_command('loaddata', 'test_fixtures.json', verbosity=0)
        assert_equal(Boo.objects.filter(slug="1").count(), 2)
        assert_equal(
            Foo.objects.filter(Q(boo__title="1") & Q(boo2__title="2")).count(),
            1)

########NEW FILE########
__FILENAME__ = test_queries
from django.core.management import call_command
from django.db.models import Q
from nose.tools import assert_equal

from djcouchtest.core.models import *
from djcouchtest.core.tests.utils import CouchDBMock


class TestQueries(CouchDBMock):
    def test_save_and_get(self):
        call_command('syncdb', interactive=False, verbosity=0)
        Boo.objects.all().delete()
        Foo.objects.all().delete()
        assert_equal(Boo.objects.all().count(), 0)
        b = Boo()
        b.title = "First Title"
        b.slug = "first_title"
        b.save()
        b2 = Boo()
        b2.title = "Second Title"
        b2.slug = "second_title"
        b2.save()
        assert_equal(Boo.objects.all().count(), 2)
        assert_equal(Boo.objects.filter(slug="first_title").count(),1)
        f = Foo(boo=b)
        f.save()
        assert_equal(b.foo_set.count(), 1)
        assert_equal(b2.foo_set.count(), 0)
        f2 = Foo(boo=b2)
        f2.save()
        new_f = Foo.objects.filter(boo=b)[0]
        assert new_f.boo.title == "First Title"

    def test_complicated_where(self):
        call_command('syncdb', interactive=False, verbosity=0)
        Boo.objects.all().delete()
        assert_equal(Boo.objects.all().count(), 0)
        b1 = Boo(title="1", slug="1")
        b1.save()
        b11 = Boo(title="11", slug="1")
        b11.save()
        b2 = Boo(title="2", slug="2")
        b2.save()
        assert_equal(Boo.objects.filter(slug="1").count(), 2)
        assert_equal(Boo.objects.filter(slug="1").filter(title="1").count(), 1)
        assert_equal(Boo.objects.filter(Q(title="1") | Q(title="2")).count(), 2)

    def test_joins(self):
        call_command('syncdb', interactive=False, verbosity=0)
        Boo.objects.all().delete()
        Foo.objects.all().delete()
        b1 = Boo(title="1", slug="1")
        b1.save()
        b11 = Boo(title="11", slug="1")
        b11.save()
        b2 = Boo(title="2", slug="2")
        b2.save()
        f1 = Foo(boo=b1)
        f1.save()
        f2 = Foo(boo=b2)
        f2.save()
        f3 = Foo(boo=b1,boo2=b2)
        f3.save()
        assert_equal(Foo.objects.filter(boo__title="1").count(), 2)
        assert_equal(Foo.objects.filter(boo__title="11").count(), 0)
        assert_equal(Foo.objects.filter(Q(boo__title="1") | Q(boo__slug="2")).count(), 3)

        assert_equal(Foo.objects.filter(Q(boo__title="1") & Q(boo2__title="2")).count(), 1)
        assert_equal(Foo.objects.filter(Q(boo__title="1") & Q(boo2__title="11")).count(), 0)

    def test_booleans(self):
        call_command('syncdb', interactive=False, verbosity=0)
        b2 = Boo2.objects.create(flag=True)
        theb2 = Boo2.objects.get(pk=b2.id)
        assert theb2.flag is True, theb2.flag

    def test_update_query(self):
        call_command('syncdb', interactive=False, verbosity=0)
        b2 = Boo2.objects.create(flag=True)
        assert b2.flag is True, b2.flag
        b2.flag = False
        b2.save()
        theb2 = Boo2.objects.get(pk=b2.id)
        assert theb2.flag is False, theb2.flag

        b1 = Boo(title="1", slug="1")
        b1.save()
        b2 = Boo(title="2", slug="2")
        b2.save()
        f1 = Foo(boo=b1)
        f1.save()
        f1.boo=b2
        f1.save()
        assert_equal(f1.boo, b2)
        assert_equal(f1.boo.title, "2")





########NEW FILE########
__FILENAME__ = utils
import couchdb
from django.conf import settings


class CouchDBMock:
    def setup(self):
        self.server = couchdb.Server(settings.DATABASE_HOST)
        self.dbs = list(self.server)

    def teardown(self):
        for x in self.server:
            if not x in self.dbs:
                del self.server[x]

########NEW FILE########
__FILENAME__ = views
# Create your views here.

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
# Django settings for djcouchtest project.

DEBUG = True
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    # ('Your Name', 'your_email@domain.com'),
)

MANAGERS = ADMINS
DATABASE_ENGINE = 'django_couchdb.backends.couchdb'
#DATABASE_ENGINE = ''           # 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'oracle'.
DATABASE_NAME = ''      # Or path to database file if using sqlite3.
DATABASE_USER = ''             # Not used with sqlite3.
DATABASE_PASSWORD = ''         # Not used with sqlite3.
DATABASE_HOST = 'http://localhost:5984/'   # Set to empty string for localhost. Not used with sqlite3.
DATABASE_PORT = '5984'             # Set to empty string for default. Not used with sqlite3.

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
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
SECRET_KEY = '+#g!a#r4m%^2jvc!o1vl%g4(^-o8kt@+7lldspr3lts_r7kglr'

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.load_template_source',
    'django.template.loaders.app_directories.load_template_source',
#     'django.template.loaders.eggs.load_template_source',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
)

ROOT_URLCONF = 'djcouchtest.urls'

TEMPLATE_DIRS = (
    # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
)
SESSION_ENGINE = "django.contrib.sessions.backends.cache"
INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.admin',
    'djcouchtest.core'
)

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import *

# Uncomment the next two lines to enable the admin:
from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
    # Example:
    # (r'^djcouchtest/', include('djcouchtest.foo.urls')),

    # Uncomment the admin/doc line below and add 'django.contrib.admindocs'
    # to INSTALLED_APPS to enable admin documentation:
    # (r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    (r'^admin/(.*)', admin.site.root),
)

########NEW FILE########
