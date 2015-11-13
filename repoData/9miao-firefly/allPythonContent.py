__FILENAME__ = dbpool
#coding:utf8
'''
Created on 2013-5-8

@author: lan (www.9miao.com)
'''
from DBUtils.PooledDB import PooledDB
import MySQLdb

DBCS = {'mysql':MySQLdb,}

class DBPool(object):
    '''
    '''
    def initPool(self,**kw):
        '''
        '''
        self.config = kw
        creator = DBCS.get(kw.get('engine','mysql'),MySQLdb)
        self.pool = PooledDB(creator,5,**kw)
        
    def connection(self):
        return self.pool.connection()

dbpool = DBPool()


########NEW FILE########
__FILENAME__ = dbutils
#coding:utf8
'''
Created on 2013-8-21

@author: lan (www.9miao.com)
'''
import itertools
import datetime


def safeunicode(obj, encoding='utf-8'):
    r"""
    Converts any given object to unicode string.
    
        >>> safeunicode('hello')
        u'hello'
        >>> safeunicode(2)
        u'2'
        >>> safeunicode('\xe1\x88\xb4')
        u'\u1234'
    """
    t = type(obj)
    if t is unicode:
        return obj
    elif t is str:
        return obj.decode(encoding)
    elif t in [int, float, bool]:
        return unicode(obj)
    elif hasattr(obj, '__unicode__') or isinstance(obj, unicode):
        return unicode(obj)
    else:
        return str(obj).decode(encoding)
    
def safestr(obj, encoding='utf-8'):
    r"""
    Converts any given object to utf-8 encoded string. 
    
        >>> safestr('hello')
        'hello'
        >>> safestr(u'\u1234')
        '\xe1\x88\xb4'
        >>> safestr(2)
        '2'
    """
    if isinstance(obj, unicode):
        return obj.encode(encoding)
    elif isinstance(obj, str):
        return obj
    elif hasattr(obj, 'next'): # iterator
        return itertools.imap(safestr, obj)
    else:
        return str(obj)
    
def sqlify(obj): 
    """
    converts `obj` to its proper SQL version

        >>> sqlify(None)
        'NULL'
        >>> sqlify(True)
        "'t'"
        >>> sqlify(3)
        '3'
    """
    # because `1 == True and hash(1) == hash(True)`
    # we have to do this the hard way...

    if obj is None:
        return 'NULL'
    elif obj is True:
        return "'t'"
    elif obj is False:
        return "'f'"
    elif datetime and isinstance(obj, datetime.datetime):
        return repr(obj.isoformat())
    else:
        if isinstance(obj, unicode): obj = obj.encode('utf8')
        return repr(obj)
    
def sqllist(lst): 
    """
    Converts the arguments for use in something like a WHERE clause.
    
        >>> sqllist(['a', 'b'])
        'a, b'
        >>> sqllist('a')
        'a'
        >>> sqllist(u'abc')
        u'abc'
    """
    if isinstance(lst, basestring): 
        return lst
    else:
        return ', '.join(lst)
    
def _sqllist(values):
    """
        >>> _sqllist([1, 2, 3])
        <sql: '(1, 2, 3)'>
    """
    items = []
    items.append('(')
    for i, v in enumerate(values):
        if i != 0:
            items.append(', ')
        items.append(sqlparam(v))
    items.append(')')
    return SQLQuery(items)
    
def sqlquote(a): 
    """
    Ensures `a` is quoted properly for use in a SQL query.

        >>> 'WHERE x = ' + sqlquote(True) + ' AND y = ' + sqlquote(3)
        <sql: "WHERE x = 't' AND y = 3">
        >>> 'WHERE x = ' + sqlquote(True) + ' AND y IN ' + sqlquote([2, 3])
        <sql: "WHERE x = 't' AND y IN (2, 3)">
    """
    if isinstance(a, list):
        return _sqllist(a)
    else:
        return sqlparam(a).sqlquery()
    
def _interpolate(sformat): 
    """
    Takes a format string and returns a list of 2-tuples of the form
    (boolean, string) where boolean says whether string should be evaled
    or not.

    from <http://lfw.org/python/Itpl.py> (public domain, Ka-Ping Yee)
    """
    from tokenize import tokenprog
    
    tokenprog = tokenprog

    def matchorfail(text, pos):
        match = tokenprog.match(text, pos)
        if match is None:
            raise _ItplError(text, pos)
        return match, match.end()

    namechars = "abcdefghijklmnopqrstuvwxyz" \
        "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_";
    chunks = []
    pos = 0

    while 1:
        dollar = sformat.find("$", pos)
        if dollar < 0: 
            break
        nextchar = sformat[dollar + 1]

        if nextchar == "{":
            chunks.append((0, sformat[pos:dollar]))
            pos, level = dollar + 2, 1
            while level:
                match, pos = matchorfail(sformat, pos)
                tstart, tend = match.regs[3]
                token = sformat[tstart:tend]
                if token == "{": 
                    level = level + 1
                elif token == "}":  
                    level = level - 1
            chunks.append((1, sformat[dollar + 2:pos - 1]))

        elif nextchar in namechars:
            chunks.append((0, sformat[pos:dollar]))
            match, pos = matchorfail(sformat, dollar + 1)
            while pos < len(sformat):
                if sformat[pos] == "." and \
                    pos + 1 < len(sformat) and sformat[pos + 1] in namechars:
                    match, pos = matchorfail(sformat, pos + 1)
                elif sformat[pos] in "([":
                    pos, level = pos + 1, 1
                    while level:
                        match, pos = matchorfail(sformat, pos)
                        tstart, tend = match.regs[3]
                        token = sformat[tstart:tend]
                        if token[0] in "([": 
                            level = level + 1
                        elif token[0] in ")]":  
                            level = level - 1
                else: 
                    break
            chunks.append((1, sformat[dollar + 1:pos]))
        else:
            chunks.append((0, sformat[pos:dollar + 1]))
            pos = dollar + 1 + (nextchar == "$")

    if pos < len(sformat): 
        chunks.append((0, sformat[pos:]))
    return chunks

def sqlwhere(dictionary, grouping=' AND '): 
    """
    Converts a `dictionary` to an SQL WHERE clause `SQLQuery`.
    
        >>> sqlwhere({'cust_id': 2, 'order_id':3})
        <sql: 'order_id = 3 AND cust_id = 2'>
        >>> sqlwhere({'cust_id': 2, 'order_id':3}, grouping=', ')
        <sql: 'order_id = 3, cust_id = 2'>
        >>> sqlwhere({'a': 'a', 'b': 'b'}).query()
        'a = %s AND b = %s'
    """
    return SQLQuery.join([k + ' = ' + sqlparam(v) for k, v in dictionary.items()], grouping)
    
def reparam(string_, dictionary): 
    """
    Takes a string and a dictionary and interpolates the string
    using values from the dictionary. Returns an `SQLQuery` for the result.

        >>> reparam("s = $s", dict(s=True))
        <sql: "s = 't'">
        >>> reparam("s IN $s", dict(s=[1, 2]))
        <sql: 's IN (1, 2)'>
    """
    dictionary = dictionary.copy() # eval mucks with it
    result = []
    for live, chunk in _interpolate(string_):
        if live:
            v = eval(chunk, dictionary)
            result.append(sqlquote(v))
        else: 
            result.append(chunk)
    return SQLQuery.join(result, '')

class UnknownParamstyle(Exception): 
    """
    raised for unsupported db paramstyles

    (currently supported: qmark, numeric, format, pyformat)
    """
    pass

class _ItplError(ValueError): 
    def __init__(self, text, pos):
        ValueError.__init__(self)
        self.text = text
        self.pos = pos
    def __str__(self):
        return "unfinished expression in %s at char %d" % (
            repr(self.text), self.pos)

class SQLParam(object):
    """
    Parameter in SQLQuery.
    
        >>> q = SQLQuery(["SELECT * FROM test WHERE name=", SQLParam("joe")])
        >>> q
        <sql: "SELECT * FROM test WHERE name='joe'">
        >>> q.query()
        'SELECT * FROM test WHERE name=%s'
        >>> q.values()
        ['joe']
    """
    __slots__ = ["value"]

    def __init__(self, value):
        self.value = value
        
    def get_marker(self, paramstyle='pyformat'):
        if paramstyle == 'qmark':
            return '?'
        elif paramstyle == 'numeric':
            return ':1'
        elif paramstyle is None or paramstyle in ['format', 'pyformat']:
            return '%s'
        raise UnknownParamstyle, paramstyle
        
    def sqlquery(self): 
        return SQLQuery([self])
        
    def __add__(self, other):
        return self.sqlquery() + other
        
    def __radd__(self, other):
        return other + self.sqlquery() 
            
    def __str__(self): 
        return str(self.value)
    
    def __repr__(self):
        return '<param: %s>' % repr(self.value)

sqlparam =  SQLParam

class SQLQuery(object):
    """
    You can pass this sort of thing as a clause in any db function.
    Otherwise, you can pass a dictionary to the keyword argument `vars`
    and the function will call reparam for you.

    Internally, consists of `items`, which is a list of strings and
    SQLParams, which get concatenated to produce the actual query.
    """
    __slots__ = ["items"]

    # tested in sqlquote's docstring
    def __init__(self, items=None):
        r"""Creates a new SQLQuery.
        
            >>> SQLQuery("x")
            <sql: 'x'>
            >>> q = SQLQuery(['SELECT * FROM ', 'test', ' WHERE x=', SQLParam(1)])
            >>> q
            <sql: 'SELECT * FROM test WHERE x=1'>
            >>> q.query(), q.values()
            ('SELECT * FROM test WHERE x=%s', [1])
            >>> SQLQuery(SQLParam(1))
            <sql: '1'>
        """
        if items is None:
            self.items = []
        elif isinstance(items, list):
            self.items = items
        elif isinstance(items, SQLParam):
            self.items = [items]
        elif isinstance(items, SQLQuery):
            self.items = list(items.items)
        else:
            self.items = [items]
            
        # Take care of SQLLiterals
        for i, item in enumerate(self.items):
            if isinstance(item, SQLParam) and isinstance(item.value, SQLLiteral):
                self.items[i] = item.value.v

    def append(self, value):
        self.items.append(value)

    def __add__(self, other):
        if isinstance(other, basestring):
            items = [other]
        elif isinstance(other, SQLQuery):
            items = other.items
        else:
            return NotImplemented
        return SQLQuery(self.items + items)

    def __radd__(self, other):
        if isinstance(other, basestring):
            items = [other]
        else:
            return NotImplemented
            
        return SQLQuery(items + self.items)

    def __iadd__(self, other):
        if isinstance(other, (basestring, SQLParam)):
            self.items.append(other)
        elif isinstance(other, SQLQuery):
            self.items.extend(other.items)
        else:
            return NotImplemented
        return self

    def __len__(self):
        return len(self.query())
        
    def query(self, paramstyle=None):
        """
        Returns the query part of the sql query.
            >>> q = SQLQuery(["SELECT * FROM test WHERE name=", SQLParam('joe')])
            >>> q.query()
            'SELECT * FROM test WHERE name=%s'
            >>> q.query(paramstyle='qmark')
            'SELECT * FROM test WHERE name=?'
        """
        s = []
        for x in self.items:
            if isinstance(x, SQLParam):
                x = x.get_marker(paramstyle)
                s.append(safestr(x))
            else:
                x = safestr(x)
                # automatically escape % characters in the query
                # For backward compatability, ignore escaping when the query looks already escaped
                if paramstyle in ['format', 'pyformat']:
                    if '%' in x and '%%' not in x:
                        x = x.replace('%', '%%')
                s.append(x)
        return "".join(s)
    
    def values(self):
        """
        Returns the values of the parameters used in the sql query.
            >>> q = SQLQuery(["SELECT * FROM test WHERE name=", SQLParam('joe')])
            >>> q.values()
            ['joe']
        """
        return [i.value for i in self.items if isinstance(i, SQLParam)]
        
    def join(items, sep=' ', prefix=None, suffix=None, target=None):
        """
        Joins multiple queries.
        
        >>> SQLQuery.join(['a', 'b'], ', ')
        <sql: 'a, b'>

        Optinally, prefix and suffix arguments can be provided.

        >>> SQLQuery.join(['a', 'b'], ', ', prefix='(', suffix=')')
        <sql: '(a, b)'>

        If target argument is provided, the items are appended to target instead of creating a new SQLQuery.
        """
        if target is None:
            target = SQLQuery()

        target_items = target.items

        if prefix:
            target_items.append(prefix)

        for i, item in enumerate(items):
            if i != 0:
                target_items.append(sep)
            if isinstance(item, SQLQuery):
                target_items.extend(item.items)
            else:
                target_items.append(item)

        if suffix:
            target_items.append(suffix)
        return target
    
    join = staticmethod(join)
    
    def _str(self):
        try:
            return self.query() % tuple([sqlify(x) for x in self.values()])            
        except (ValueError, TypeError):
            return self.query()
        
    def __str__(self):
        return safestr(self._str())
        
    def __unicode__(self):
        return safeunicode(self._str())

    def __repr__(self):
        return '<sql: %s>' % repr(str(self))
    
class SQLLiteral: 
    """
    Protects a string from `sqlquote`.

        >>> sqlquote('NOW()')
        <sql: "'NOW()'">
        >>> sqlquote(SQLLiteral('NOW()'))
        <sql: 'NOW()'>
    """
    def __init__(self, v): 
        self.v = v

    def __repr__(self): 
        return self.v

class SQLProducer: 
    """Database"""
    def __init__(self):
        """Creates a database.
        """
        pass
    
    def query(self, sql_query,processed=False, svars=None): 
        """
        Execute SQL query `sql_query` using dictionary `vars` to interpolate it.
        If `processed=True`, `vars` is a `reparam`-style list to use 
        instead of interpolating.
        
            >>> db = DB(None, {})
            >>> db.query("SELECT * FROM foo", _test=True)
            <sql: 'SELECT * FROM foo'>
            >>> db.query("SELECT * FROM foo WHERE x = $x", vars=dict(x='f'), _test=True)
            <sql: "SELECT * FROM foo WHERE x = 'f'">
            >>> db.query("SELECT * FROM foo WHERE x = " + sqlquote('f'), _test=True)
            <sql: "SELECT * FROM foo WHERE x = 'f'">
        """
        if svars is None:
            svars = {}
            
        if not processed and not isinstance(sql_query, SQLQuery):
            sql_query = reparam(sql_query, svars)
            
        return sql_query
    
    def sql_clauses(self, what, tables, where, group, order, limit, offset): 
        return (
            ('SELECT', what),
            ('FROM', sqllist(tables)),
            ('WHERE', where),
            ('GROUP BY', group),
            ('ORDER BY', order),
            ('LIMIT', limit),
            ('OFFSET', offset))
    
    def gen_clause(self, sql, val, svars): 
        if isinstance(val, (int, long)):
            if sql == 'WHERE':
                nout = 'id = ' + sqlquote(val)
            else:
                nout = SQLQuery(val)
                
        elif isinstance(val, (list, tuple)) and len(val) == 2:
            nout = SQLQuery(val[0], val[1]) # backwards-compatibility
        elif isinstance(val, SQLQuery):
            nout = val
        else:
            nout = reparam(val, svars)

        def xjoin(a, b):
            if a and b: return a + ' ' + b
            else: return a or b

        return xjoin(sql, nout)
    
    def _where(self, where, svars): 
        if isinstance(where, (int, long)):
            where = "id = " + sqlparam(where)
        elif isinstance(where, (list, tuple)) and len(where) == 2:
            where = SQLQuery(where[0], where[1])
        elif isinstance(where, SQLQuery):
            pass
        else:
            where = reparam(where, svars)        
        return where
    
    def select(self, tables, svars=None, what='*', where=None, order=None, group=None, 
               limit=None, offset=None, _test=False): 
        """
        Selects `what` from `tables` with clauses `where`, `order`, 
        `group`, `limit`, and `offset`. Uses vars to interpolate. 
        Otherwise, each clause can be a SQLQuery.
        
            >>> db = DB(None, {})
            >>> db.select('foo', _test=True)
            <sql: 'SELECT * FROM foo'>
            >>> db.select(['foo', 'bar'], where="foo.bar_id = bar.id", limit=5, _test=True)
            <sql: 'SELECT * FROM foo, bar WHERE foo.bar_id = bar.id LIMIT 5'>
        """
        if svars is None: svars = {}
        sql_clauses = self.sql_clauses(what, tables, where, group, order, limit, offset)
        clauses = [self.gen_clause(sql, val, svars) for sql, val in sql_clauses if val is not None]
        qout = SQLQuery.join(clauses)
        if _test: return qout
        return self.query(qout, processed=True)

    def insert(self, tablename, seqname=None, _test=False, **values): 
        """
        Inserts `values` into `tablename`. Returns current sequence ID.
        Set `seqname` to the ID if it's not the default, or to `False`
        if there isn't one.
        
            >>> db = DB(None, {})
            >>> q = db.insert('foo', name='bob', age=2, created=SQLLiteral('NOW()'), _test=True)
            >>> q
            <sql: "INSERT INTO foo (age, name, created) VALUES (2, 'bob', NOW())">
            >>> q.query()
            'INSERT INTO foo (age, name, created) VALUES (%s, %s, NOW())'
            >>> q.values()
            [2, 'bob']
        """
        def q(x): return "(" + x + ")"
        
        if values:
            _keys = SQLQuery.join(values.keys(), ', ')
            _values = SQLQuery.join([sqlparam(v) for v in values.values()], ', ')
            sql_query = "INSERT INTO %s " % tablename + q(_keys) + ' VALUES ' + q(_values)
        else:
            sql_query = SQLQuery(self._get_insert_default_values_query(tablename))

        return sql_query
        
    def _get_insert_default_values_query(self, table):
        return "INSERT INTO %s DEFAULT VALUES" % table

    def multiple_insert(self, tablename, values, seqname=None, _test=False):
        """
        Inserts multiple rows into `tablename`. The `values` must be a list of dictioanries, 
        one for each row to be inserted, each with the same set of keys.
        Returns the list of ids of the inserted rows.        
        Set `seqname` to the ID if it's not the default, or to `False`
        if there isn't one.
        
            >>> db = DB(None, {})
            >>> db.supports_multiple_insert = True
            >>> values = [{"name": "foo", "email": "foo@example.com"}, {"name": "bar", "email": "bar@example.com"}]
            >>> db.multiple_insert('person', values=values, _test=True)
            <sql: "INSERT INTO person (name, email) VALUES ('foo', 'foo@example.com'), ('bar', 'bar@example.com')">
        """        
        if not values:
            return []
            
        if not self.supports_multiple_insert:
            out = [self.insert(tablename, seqname=seqname, _test=_test, **v) for v in values]
            if seqname is False:
                return None
            else:
                return out
                
        keys = values[0].keys()
        #@@ make sure all keys are valid

        # make sure all rows have same keys.
        for v in values:
            if v.keys() != keys:
                raise ValueError, 'Bad data'

        sql_query = SQLQuery('INSERT INTO %s (%s) VALUES ' % (tablename, ', '.join(keys)))

        for i, row in enumerate(values):
            if i != 0:
                sql_query.append(", ")
            SQLQuery.join([SQLParam(row[k]) for k in keys], sep=", ", target=sql_query, prefix="(", suffix=")")
        
        if _test: return sql_query

        db_cursor = self._db_cursor()
        if seqname is not False: 
            sql_query = self._process_insert_query(sql_query, tablename, seqname)

        if isinstance(sql_query, tuple):
            # for some databases, a separate query has to be made to find 
            # the id of the inserted row.
            q1, q2 = sql_query
            self._db_execute(db_cursor, q1)
            self._db_execute(db_cursor, q2)
        else:
            self._db_execute(db_cursor, sql_query)

        try: 
            out = db_cursor.fetchone()[0]
            out = range(out-len(values)+1, out+1)        
        except Exception: 
            out = None

        if not self.ctx.transactions: 
            self.ctx.commit()
        return out

    
    def update(self, tables, where, svars=None, _test=False, **values): 
        """
        Update `tables` with clause `where` (interpolated using `vars`)
        and setting `values`.

            >>> db = DB(None, {})
            >>> name = 'Joseph'
            >>> q = db.update('foo', where='name = $name', name='bob', age=2,
            ...     created=SQLLiteral('NOW()'), vars=locals(), _test=True)
            >>> q
            <sql: "UPDATE foo SET age = 2, name = 'bob', created = NOW() WHERE name = 'Joseph'">
            >>> q.query()
            'UPDATE foo SET age = %s, name = %s, created = NOW() WHERE name = %s'
            >>> q.values()
            [2, 'bob', 'Joseph']
        """
        if svars is None: svars = {}
        where = self._where(where, svars)

        query = (
          "UPDATE " + sqllist(tables) + 
          " SET " + sqlwhere(values, ', ') + 
          " WHERE " + where)

        if _test: return query
        
        db_cursor = self._db_cursor()
        self._db_execute(db_cursor, query)
        if not self.ctx.transactions: 
            self.ctx.commit()
        return db_cursor.rowcount
    
    def delete(self, table, where, using=None, svars=None, _test=False): 
        """
        Deletes from `table` with clauses `where` and `using`.

            >>> db = DB(None, {})
            >>> name = 'Joe'
            >>> db.delete('foo', where='name = $name', vars=locals(), _test=True)
            <sql: "DELETE FROM foo WHERE name = 'Joe'">
        """
        if svars is None:
            svars = {}
        where = self._where(where, svars)

        q = 'DELETE FROM ' + table
        if using:
            q += ' USING ' + sqllist(using)
        if where:
            q += ' WHERE ' + where

        return q
    
sqlproducer = SQLProducer()


print sqlproducer.delete("tb_item", where="id=123")
    

########NEW FILE########
__FILENAME__ = madminanager
#coding:utf8
'''
Created on 2013-5-22

@author: lan (www.9miao.com)
'''
from firefly.utils.singleton import Singleton

class MAdminManager:
    __metaclass__ = Singleton
    
    def __init__(self):
        """
        """
        self.admins = {}
        
    def registe(self,admin):
        """
        """
        self.admins[admin._name] = admin
        
    def dropAdmin(self,adminname):
        """
        """
        if self.admins.has_key(adminname):
            del self.admins[adminname]
    
    def getAdmin(self,adminname):
        """
        """
        return self.admins.get(adminname)
    
    def checkAdmins(self):
        """
        """
        for admin in self.admins.values():
            admin.checkAll()
    
    
    
        
########NEW FILE########
__FILENAME__ = memclient
#coding:utf8
'''
Created on 2013-7-10
memcached client
@author: lan (www.9miao.com)
'''
import memcache

class MemConnError(Exception): 
    """
    """
    def __str__(self):
        return "memcache connect error"

class MemClient:
    '''memcached
    '''
    
    def __init__(self,timeout = 0):
        '''
        '''
        self._hostname = ""
        self._urls = []
        self.connection = None
        
    def connect(self,urls,hostname):
        '''memcached connect
        '''
        self._hostname = hostname
        self._urls = urls
        self.connection = memcache.Client(self._urls,debug=0)
        if not self.connection.set("__testkey__",1):
            raise MemConnError()
        
    def produceKey(self,keyname):
        '''
        '''
        if isinstance(keyname, basestring):
            return ''.join([self._hostname,':',keyname])
        else:
            raise "type error"
        
    def get(self,key):
        '''
        '''
        key = self.produceKey(key)
        return self.connection.get(key)
    
    def get_multi(self,keys):
        '''
        '''
        keynamelist = [self.produceKey(keyname) for keyname in keys]
        olddict = self.connection.get_multi(keynamelist)
        newdict = dict(zip([keyname.split(':')[-1] for keyname in olddict.keys()],
                              olddict.values()))
        return newdict
        
    def set(self,keyname,value):
        '''
        '''
        key = self.produceKey(keyname)
        result = self.connection.set(key,value)
        if not result:#如果写入失败
            self.connect(self._urls,self._hostname)#重新连接
            return self.connection.set(key,value)
        return result
    
    def set_multi(self,mapping):
        '''
        '''
        newmapping = dict(zip([self.produceKey(keyname) for keyname in mapping.keys()],
                              mapping.values()))
        result = self.connection.set_multi(newmapping)
        if result:#如果写入失败
            self.connect(self._urls,self._hostname)#重新连接
            return self.connection.set_multi(newmapping)
        return result
        
    def incr(self,key,delta):
        '''
        '''
        key = self.produceKey(key)
        return self.connection.incr(key, delta)
        
    def delete(self,key):
        '''
        '''
        key = self.produceKey(key)
        return self.connection.delete(key)
    
    def delete_multi(self,keys):
        """
        """
        keys = [self.produceKey(key) for key in keys]
        return self.connection.delete_multi(keys)
        
    def flush_all(self):
        '''
        '''
        self.connection.flush_all()
        
mclient = MemClient()



########NEW FILE########
__FILENAME__ = memobject
#coding:utf8
'''
Created on 2012-7-10
memcached 关系对象
通过key键的名称前缀来建立
各个key-value 直接的关系
@author: lan (www.9miao.com)
'''

class MemObject:
    '''memcached 关系对象
    '''
    
    def __init__(self,name,mc):
        '''
        @param name: str 对象的名称
        @param _lock: int 对象锁  为1时表示对象被锁定无法进行修改
        '''
        self._client = mc
        self._name = name
        self._lock = 0
        
    def produceKey(self,keyname):
        '''重新生成key
        '''
        if isinstance(keyname, basestring):
            return ''.join([self._name,':',keyname])
        else:
            raise "type error"
        
    def locked(self):
        '''检测对象是否被锁定
        '''
        key = self.produceKey('_lock')
        return self._client.get(key)
    
    def lock(self):
        '''锁定对象
        '''
        key = self.produceKey('_lock')
        self._client.set(key, 1)
        
    def release(self):
        '''释放锁
        '''
        key = self.produceKey('_lock')
        self._client.set(key, 0)
        
    def get(self,key):
        '''获取对象值
        '''
        key = self.produceKey(key)
        return self._client.get(key)
    
    def get_multi(self,keys):
        '''一次获取多个key的值
        @param keys: list(str) key的列表
        '''
        keynamelist = [self.produceKey(keyname) for keyname in keys]
        olddict = self._client.get_multi(keynamelist)
        newdict = dict(zip([keyname.split(':')[-1] for keyname in olddict.keys()],
                              olddict.values()))
        return newdict

    def update(self,key,values):
        '''修改对象的值
        '''
        if self.locked():
            return False
        key = self.produceKey(key)
        return self._client.set(key,values)
            
    def update_multi(self,mapping):
        '''同时修改多个key值
        '''
        if self.locked():
            return False
        newmapping = dict(zip([self.produceKey(keyname) for keyname in mapping.keys()],
                              mapping.values()))
        return self._client.set_multi(newmapping)
        
    def mdelete(self):
        '''删除memcache中的数据
        '''
        nowdict = dict(self.__dict__)
        del nowdict['_client']
        keys = nowdict.keys()
        keys = [self.produceKey(key) for key in keys]
        self._client.delete_multi(keys)
            
    def incr(self, key, delta):
        '''自增
        '''
        key = self.produceKey(key)
        return self._client.incr( key, delta)
        
    def insert(self):
        '''插入对象记录
        '''
        nowdict = dict(self.__dict__)
        del nowdict['_client']
        newmapping = dict(zip([self.produceKey(keyname) for keyname in nowdict.keys()],
                              nowdict.values()))
        self._client.set_multi(newmapping)
        
        
        
        

########NEW FILE########
__FILENAME__ = mmode
#coding:utf8
'''
Created on 2013-5-8

@author: lan (www.9miao.com)
'''
from memclient import mclient
from memobject import MemObject
import util
import time

MMODE_STATE_ORI = 0     #未变更
MMODE_STATE_NEW = 1     #创建
MMODE_STATE_UPDATE = 2  #更新
MMODE_STATE_DEL = 3     #删除



TIMEOUT = 1800

def _insert(args):
    record,pkname,mmname,cls =  args
    pk = record[pkname]
    mm = cls(mmname+':%s'%pk,pkname,data=record)
    mm.insert()
    return pk

class PKValueError(ValueError): 
    """
    """
    def __init__(self, data):
        ValueError.__init__(self)
        self.data = data
    def __str__(self):
        return "new record has no 'PK': %s" % (self.data)

class MMode(MemObject):
    """内存数据模型
    """
    def __init__(self, name,pk,data={}):
        """
        """
        MemObject.__init__(self, name, mclient)
        self._state = MMODE_STATE_ORI#对象的状态 0未变更  1新建 2更新 3删除
        self._pk = pk
        self.data = data
        self._time = time.time()
        
    def update(self, key, values):
        data = self.get_multi(['data','_state'])
        ntime = time.time()
        data['data'].update({key:values})
        if data.get('_state')==MMODE_STATE_NEW:
            props = {'data':data.get('data'),'_time':ntime}
        else:
            props = {'_state':MMODE_STATE_UPDATE,'data':data.get('data'),'_time':ntime}
        return MemObject.update_multi(self, props)
    
    def update_multi(self, mapping):
        ntime = time.time()
        data = self.get_multi(['data','_state'])
        data['data'].update(mapping)
        if data.get('_state')==MMODE_STATE_NEW:
            props = {'data':data.get('data'),'_time':ntime}
        else:
            props = {'_state':MMODE_STATE_UPDATE,'data':data.get('data'),'_time':ntime}
        return MemObject.update_multi(self, props)
    
    def get(self, key):
        ntime = time.time()
        MemObject.update(self, "_time", ntime)
        return MemObject.get(self, key)
    
    def get_multi(self, keys):
        ntime = time.time()
        MemObject.update(self, "_time", ntime)
        return MemObject.get_multi(self, keys)
    
    def delete(self):
        '''删除对象
        '''
        return MemObject.update(self,'_state',MMODE_STATE_DEL)
    
    def mdelete(self):
        """清理对象
        """
        self.syncDB()
        MemObject.mdelete(self)
    
    def IsEffective(self):
        '''检测对象是否有效
        '''
        if self.get('_state')==MMODE_STATE_DEL:
            return False
        return True
        
    def syncDB(self):
        """同步到数据库
        """
        state = self.get('_state')
        tablename = self._name.split(':')[0]
        if state==MMODE_STATE_ORI:
            return
        elif state==MMODE_STATE_NEW:
            props = self.get('data')
            pk = self.get('_pk')
            result = util.InsertIntoDB(tablename, props)
        elif state==MMODE_STATE_UPDATE:
            props = self.get('data')
            pk = self.get('_pk')
            prere = {pk:props.get(pk)}
            util.UpdateWithDict(tablename, props, prere)
            result = True
        else:
            pk = self.get('_pk')
            props = self.get('data')
            prere = {pk:props.get(pk)}
            result = util.DeleteFromDB(tablename,prere)
        if result:
            MemObject.update(self,'_state', MMODE_STATE_ORI)
            
    def checkSync(self,timeout=TIMEOUT):
        """检测同步
        """
        ntime = time.time()
        objtime = MemObject.get(self, '_time')
        if ntime  -objtime>=timeout and timeout:
            self.mdelete()
        else:
            self.syncDB()
        
        
class MFKMode(MemObject):
    """内存数据模型
    """
    def __init__(self, name,pklist = []):
        MemObject.__init__(self, name, mclient)
        self.pklist = pklist
        
class MAdmin(MemObject):
    
    def __init__(self, name,pk,timeout=TIMEOUT,**kw):
        MemObject.__init__(self, name, mclient)
        self._pk = pk
        self._fk = kw.get('fk','')
        self._incrkey = kw.get('incrkey','')
        self._incrvalue = kw.get('incrvalue',0)
        self._timeout = timeout
        
    def insert(self):
        if self._incrkey and not self.get("_incrvalue"):
            self._incrvalue = util.GetTableIncrValue(self._name)
        MemObject.insert(self)
        
    def load(self):
        '''读取数据到数据库中
        '''
        mmname = self._name
        recordlist = util.ReadDataFromDB(mmname)
        for record in recordlist:
            pk = record[self._pk]
            mm = MMode(self._name+':%s'%pk,self._pk,data=record)
            mm.insert()
    
    @property
    def madmininfo(self):
        keys = self.__dict__.keys()
        info = self.get_multi(keys)
        return info
    
    def getAllPkByFk(self,fk):
        '''根据外键获取主键列表
        '''
        name = '%s_fk:%s'%(self._name,fk)
        fkmm = MFKMode(name)
        pklist = fkmm.get('pklist')
        if pklist is not None:
            return pklist
        props = {self._fk:fk}
        dbkeylist = util.getAllPkByFkInDB(self._name, self._pk, props)
        name = '%s_fk:%s'%(self._name,fk)
        fkmm = MFKMode(name, pklist = dbkeylist)
        fkmm.insert()
        return dbkeylist
        
    def getObj(self,pk):
        '''
        '''
        mm = MMode(self._name+':%s'%pk,self._pk)
        if not mm.IsEffective():
            return None
        if mm.get('data'):
            return mm
        props = {self._pk:pk}
        record = util.GetOneRecordInfo(self._name,props)
        if not record:
            return None
        mm =  MMode(self._name+':%s'%pk,self._pk,data = record)
        mm.insert()
        return mm
    
    def getObjData(self,pk):
        '''
        '''
        mm = MMode(self._name+':%s'%pk,self._pk)
        if not mm.IsEffective():
            return None
        data = mm.get('data')
        if mm.get('data'):
            return data
        props = {self._pk:pk}
        record = util.GetOneRecordInfo(self._name,props)
        if not record:
            return None
        mm =  MMode(self._name+':%s'%pk,self._pk,data = record)
        mm.insert()
        return record
        
    
    def getObjList(self,pklist):
        '''
        '''
        _pklist = []
        objlist = []
        for pk in pklist:
            mm = MMode(self._name+':%s'%pk,self._pk)
            if not mm.IsEffective():
                continue
            if mm.get('data'):
                objlist.append(mm)
            else:
                _pklist.append(pk)
        if _pklist:
            recordlist = util.GetRecordList(self._name, self._pk,_pklist)
            for record in recordlist:
                pk = record[self._pk]
                mm =  MMode(self._name+':%s'%pk,self._pk,data = record)
                mm.insert()
                objlist.append(mm)
        return objlist
    
    def deleteMode(self,pk):
        '''
        '''
        mm = self.getObj(pk)
        if mm:
            if self._fk:
                data = mm.get('data')
                if data:
                    fk = data.get(self._fk,0)
                    name = '%s_fk:%s'%(self._name,fk)
                    fkmm = MFKMode(name)
                    pklist = fkmm.get('pklist')
                    if pklist and pk in pklist:
                        pklist.remove(pk)
                    fkmm.update('pklist', pklist)
            mm.delete()
        return True
    
    def checkAll(self):
        key = '%s:%s:'%(mclient._hostname,self._name)
        _pklist = util.getallkeys(key, mclient.connection)
        for pk in _pklist:
            mm = MMode(self._name+':%s'%pk,self._pk)
            if not mm.IsEffective():
                mm.mdelete()
                continue
            if not mm.get('data'):
                continue
            mm.checkSync(timeout=self._timeout)
        self.deleteAllFk()
        
    def deleteAllFk(self):
        """删除所有的外键
        """
        key = '%s:%s_fk:'%(mclient._hostname,self._name)
        _fklist = util.getallkeys(key, mclient.connection)
        for fk in _fklist:
            name = '%s_fk:%s'%(self._name,fk)
            fkmm = MFKMode(name)
            fkmm.mdelete()
        
    def new(self,data):
        """创建一个新的对象
        """
        incrkey = self._incrkey
        if incrkey:
            incrvalue = self.incr('_incrvalue', 1)
            data[incrkey] = incrvalue - 1 
            pk = data.get(self._pk)
            if pk is None:
                raise PKValueError(data)
            mm = MMode(self._name+':%s'%pk,self._pk,data=data)
            setattr(mm,incrkey,pk)
        else:
            pk = data.get(self._pk)
            mm = MMode(self._name+':%s'%pk,self._pk,data=data)
        if self._fk:
            fk = data.get(self._fk,0)
            name = '%s_fk:%s'%(self._name,fk)
            fkmm = MFKMode(name)
            pklist = fkmm.get('pklist')
            if pklist is None:
                pklist = self.getAllPkByFk(fk)
            pklist.append(pk)
            fkmm.update('pklist', pklist)
        setattr(mm,'_state',MMODE_STATE_NEW)
        mm.insert()
        return mm
        

########NEW FILE########
__FILENAME__ = util
#coding:utf8
'''
Created on 2013-5-8

@author: lan (www.9miao.com)
'''

from dbpool import dbpool
from MySQLdb.cursors import DictCursor
from numbers import Number
from twisted.python import log


def forEachPlusInsertProps(tablename,props):
    assert type(props) == dict
    pkeysstr = str(tuple(props.keys())).replace('\'','`')
    pvaluesstr = ["%s,"%val if isinstance(val,Number) else 
                  "'%s',"%str(val).replace("'", "\\'") for val in props.values()]
    pvaluesstr = ''.join(pvaluesstr)[:-1]
    sqlstr = """INSERT INTO `%s` %s values (%s);"""%(tablename,pkeysstr,pvaluesstr)
    return sqlstr

def FormatCondition(props):
    """生成查询条件字符串
    """
    items = props.items()
    itemstrlist = []
    for _item in items:
        if isinstance(_item[1],Number):
            sqlstr = " `%s`=%s AND"%_item
        else:
            sqlstr = " `%s`='%s' AND "%(_item[0],str(_item[1]).replace("'", "\\'"))
        itemstrlist.append(sqlstr)
    sqlstr = ''.join(itemstrlist)
    return sqlstr[:-4]

def FormatUpdateStr(props):
    """生成更新语句
    """
    items = props.items()
    itemstrlist = []
    for _item in items:
        if isinstance(_item[1],Number):
            sqlstr = " `%s`=%s,"%_item
        else:
            sqlstr = " `%s`='%s',"%(_item[0],str(_item[1]).replace("'", "\\'"))
        itemstrlist.append(sqlstr)
    sqlstr = ''.join(itemstrlist)
    return sqlstr[:-1]
    
def forEachUpdateProps(tablename,props,prere):
    '''遍历所要修改的属性，以生成sql语句'''
    assert type(props) == dict
    pro = FormatUpdateStr(props)
    pre = FormatCondition(prere)
    sqlstr = """UPDATE `%s` SET %s WHERE %s;"""%(tablename,pro,pre) 
    return sqlstr

def EachQueryProps(props):
    '''遍历字段列表生成sql语句
    '''
    sqlstr = ""
    if props == '*':
        return '*'
    elif type(props) == type([0]):
        for prop in props:
            sqlstr = sqlstr + prop +','
        sqlstr = sqlstr[:-1]
        return sqlstr
    else:
        raise Exception('props to query must be dict')
        return

def forEachQueryProps(sqlstr, props):
    '''遍历所要查询属性，以生成sql语句'''
    if props == '*':
        sqlstr += ' *'
    elif type(props) == type([0]):
        i = 0
        for prop in props:
            if(i == 0):
                sqlstr += ' ' + prop
            else:
                sqlstr += ', ' + prop
            i += 1
    else:
        raise Exception('props to query must be list')
        return
    return sqlstr

def GetTableIncrValue(tablename):
    """
    """
    database = dbpool.config.get('db')
    sql = """SELECT AUTO_INCREMENT FROM information_schema.`TABLES` \
    WHERE TABLE_SCHEMA='%s' AND TABLE_NAME='%s';"""%(database,tablename)
    conn = dbpool.connection()
    cursor = conn.cursor()
    cursor.execute(sql)
    result = cursor.fetchone()
    cursor.close()
    conn.close()
    if result:
        return result[0]
    return result

def ReadDataFromDB(tablename):
    """
    """
    sql = """select * from %s"""%tablename
    conn = dbpool.connection()
    cursor = conn.cursor(cursorclass = DictCursor)
    cursor.execute(sql)
    result=cursor.fetchall()
    cursor.close()
    conn.close()
    return result

def DeleteFromDB(tablename,props):
    '''从数据库中删除
    '''
    prers = FormatCondition(props)
    sql = """DELETE FROM %s WHERE %s ;"""%(tablename,prers)
    conn = dbpool.connection()
    cursor = conn.cursor()
    count = 0
    try:
        count = cursor.execute(sql)
        conn.commit()
    except Exception,e:
        log.err(e)
        log.err(sql)
    cursor.close()
    conn.close()
    return bool(count)

def InsertIntoDB(tablename,data):
    """写入数据库
    """
    sql = forEachPlusInsertProps(tablename,data)
    conn = dbpool.connection()
    cursor = conn.cursor()
    count = 0
    try:
        count = cursor.execute(sql)
        conn.commit()
    except Exception,e:
        log.err(e)
        log.err(sql)
    cursor.close()
    conn.close()
    return bool(count)

def UpdateWithDict(tablename,props,prere):
    """更新记录
    """
    sql = forEachUpdateProps(tablename, props, prere)
    conn = dbpool.connection()
    cursor = conn.cursor()
    count = 0
    try:
        count = cursor.execute(sql)
        conn.commit()
    except Exception,e:
        log.err(e)
        log.err(sql)
    cursor.close()
    conn.close()
    if(count >= 1):
        return True
    return False

def getAllPkByFkInDB(tablename,pkname,props):
    """根据所有的外键获取主键ID
    """
    props = FormatCondition(props)
    sql = """Select `%s` from `%s` where %s"""%(pkname,tablename,props)
    conn = dbpool.connection()
    cursor = conn.cursor()
    cursor.execute(sql)
    result = cursor.fetchall()
    cursor.close()
    conn.close()
    return [key[0] for key in result]

def GetOneRecordInfo(tablename,props):
    '''获取单条数据的信息
    '''
    props = FormatCondition(props)
    sql = """Select * from `%s` where %s"""%(tablename,props)
    conn = dbpool.connection()
    cursor = conn.cursor(cursorclass = DictCursor)
    cursor.execute(sql)
    result = cursor.fetchone()
    cursor.close()
    conn.close()
    return result

def GetRecordList(tablename,pkname,pklist):
    """
    """
    pkliststr = ""
    for pkid in pklist:
        pkliststr+="%s,"%pkid
    pkliststr = "(%s)"%pkliststr[:-1]
    sql = """SELECT * FROM `%s` WHERE `%s` IN %s;"""%(tablename,pkname,pkliststr)
    conn = dbpool.connection()
    cursor = conn.cursor(cursorclass = DictCursor)
    cursor.execute(sql)
    result = cursor.fetchall()
    cursor.close()
    conn.close()
    return result

def DBTest():
    sql = """SELECT * FROM tb_item WHERE characterId=1000001;"""
    conn = dbpool.connection()
    cursor = conn.cursor(cursorclass = DictCursor)
    cursor.execute(sql)
    result=cursor.fetchall()
    cursor.close()
    conn.close()
    return result

def getallkeys(key,mem):
    itemsinfo = mem.get_stats('items')
    itemindex = []
    for items in itemsinfo:
        itemindex += [ _key.split(':')[1] for _key in items[1].keys()]
    s =  set(itemindex)
    itemss = [mem.get_stats('cachedump %s 0'%i) for i in s]
    allkeys = set([])
    for item in itemss:
        for _item in item:
            nowlist = set([])
            for _key in _item[1].keys():
                try:
                    keysplit = _key.split(':')
                    pk = keysplit[2]
                except:
                    continue
                if _key.startswith(key) and not pk.startswith('_'):
                    nowlist.add(pk)
            allkeys = allkeys.union(nowlist)
    return allkeys

def getAllPkByFkInMEM(key,fk,mem):
    
    pass

########NEW FILE########
__FILENAME__ = child
#coding:utf8
'''
Created on 2013-8-14

@author: lan (www.9miao.com)
'''
class Child(object):
    '''子节点对象'''
    
    def __init__(self,cid,name):
        '''初始化子节点对象
        '''
        self._id = cid
        self._name = name
        self._transport = None
        
    def getName(self):
        '''获取子节点的名称'''
        return self._name
        
    def setTransport(self,transport):
        '''设置子节点的通道'''
        self._transport = transport
        
    def callbackChild(self,*args,**kw):
        '''回调子节点的接口
        return a Defered Object (recvdata)
        '''
        recvdata = self._transport.callRemote('callChild',*args,**kw)
        return recvdata
        
        
        
        
        
########NEW FILE########
__FILENAME__ = manager
#coding:utf8
'''
Created on 2013-8-14

@author: lan (www.9miao.com)
'''
from twisted.python import log

from zope.interface import Interface
from zope.interface import implements

class _ChildsManager(Interface):
    '''节点管理器接口'''
    
    def __init__(self):
        '''初始化接口'''
        
    def getChildById(self,childId):
        '''根据节点id获取节点实例'''
        
    def getChildByName(self,childname):
        '''根据节点的名称获取节点实例'''
        
    def addChild(self,child):
        '''添加一个child节点
        @param child: Child object
        '''
    
    def dropChild(self,*arg,**kw):
        '''删除一个节点'''
        
    def callChild(self,*args,**kw):
        '''调用子节点的接口'''
        
    def callChildByName(self,*args,**kw):
        '''调用子节点的接口
        @param childname: str 子节点的名称
        '''
    
    def dropChildByID(self,childId):
        '''删除一个child 节点
        @param childId: Child ID 
        '''
        
    def dropChildSessionId(self, session_id):
        """根据session_id删除child节点
        """

class ChildsManager(object):
    '''子节点管理器'''
    
    implements(_ChildsManager)
    
    def __init__(self):
        '''初始化子节点管理器'''
        self._childs = {}
        
    def getChildById(self,childId):
        '''根据节点的ID获取节点实例'''
        return self._childs.get(childId)
    
    def getChildByName(self,childname):
        '''根据节点的名称获取节点实例'''
        for key,child in self._childs.items():
            if child.getName() == childname:
                return self._childs[key]
        return None
        
    def addChild(self,child):
        '''添加一个child节点
        @param child: Child object
        '''
        key = child._id
        if self._childs.has_key(key):
            raise "child node %s exists"% key
        self._childs[key] = child
        
    def dropChild(self,child):
        '''删除一个child 节点
        @param child: Child Object 
        '''
        key = child._id
        try:
            del self._childs[key]
        except Exception,e:
            log.msg(str(e))
            
    def dropChildByID(self,childId):
        '''删除一个child 节点
        @param childId: Child ID 
        '''
        try:
            del self._childs[childId]
        except Exception,e:
            log.msg(str(e))
            
    def callChild(self,childId,*args,**kw):
        '''调用子节点的接口
        @param childId: int 子节点的id
        '''
        child = self._childs.get(childId,None)
        if not child:
            log.err("child %s doesn't exists"%childId)
            return
        return child.callbackChild(*args,**kw)
    
    def callChildByName(self,childname,*args,**kw):
        '''调用子节点的接口
        @param childname: str 子节点的名称
        '''
        child = self.getChildByName(childname)
        if not child:
            log.err("child %s doesn't exists"%childname)
            return
        return child.callbackChild(*args,**kw)
    
    def getChildBYSessionId(self, session_id):
        """根据sessionID获取child节点信息
        """
        for child in self._childs.values():
            if child._transport.broker.transport.sessionno == session_id:
                return child
        return None

        
########NEW FILE########
__FILENAME__ = node
#coding:utf8
'''
Created on 2013-8-14

@author: lan (www.9miao.com)
'''
from twisted.spread import pb
from twisted.internet import reactor
reactor = reactor
from reference import ProxyReference

def callRemote(obj,funcName,*args,**kw):
    '''远程调用
    @param funcName: str 远程方法
    '''
    return obj.callRemote(funcName, *args,**kw)
    
    
class RemoteObject(object):
    '''远程调用对象'''
    
    def __init__(self,name):
        '''初始化远程调用对象
        @param port: int 远程分布服的端口号
        @param rootaddr: 根节点服务器地址
        '''
        self._name = name
        self._factory = pb.PBClientFactory()
        self._reference = ProxyReference()
        self._addr = None
        
    def setName(self,name):
        '''设置节点的名称'''
        self._name = name
        
    def getName(self):
        '''获取节点的名称'''
        return self._name
        
    def connect(self,addr):
        '''初始化远程调用对象'''
        self._addr = addr
        reactor.connectTCP(addr[0], addr[1], self._factory)
        self.takeProxy()
        
    def reconnect(self):
        '''重新连接'''
        self.connect(self._addr)
        
    def addServiceChannel(self,service):
        '''设置引用对象'''
        self._reference.addService(service)
        
    def takeProxy(self):
        '''像远程服务端发送代理通道对象
        '''
        deferedRemote = self._factory.getRootObject()
        deferedRemote.addCallback(callRemote,'takeProxy',self._name,self._reference)
    
    def callRemote(self,commandId,*args,**kw):
        '''远程调用'''
        deferedRemote = self._factory.getRootObject()
        return deferedRemote.addCallback(callRemote,'callTarget',commandId,*args,**kw)
    
    
    
    
########NEW FILE########
__FILENAME__ = reference
#coding:utf8
'''
Created on 2013-8-14

@author: lan (www.9miao.com)
'''
from twisted.spread import pb
from firefly.utils.services import Service


class ProxyReference(pb.Referenceable):
    '''代理通道'''
    
    def __init__(self):
        '''初始化'''
        self._service = Service('proxy')
        
    def addService(self,service):
        '''添加一条服务通道'''
        self._service = service
    
    def remote_callChild(self, command,*arg,**kw):
        '''代理发送数据
        '''
        return self._service.callTarget(command,*arg,**kw)
    
    
    
        
########NEW FILE########
__FILENAME__ = root
#coding:utf8
'''
Created on 2013-8-14
分布式根节点
@author: lan (www.9miao.com)
'''
from twisted.python import log
from twisted.spread import pb
from manager import ChildsManager
from child import Child

class BilateralBroker(pb.Broker):
    
    def connectionLost(self, reason):
        clientID = self.transport.sessionno
        log.msg("node [%d] lose"%clientID)
        self.factory.root.dropChildSessionId(clientID)
        pb.Broker.connectionLost(self, reason)
        
    
        
class BilateralFactory(pb.PBServerFactory):
    
    protocol = BilateralBroker
    
    

class PBRoot(pb.Root):
    '''PB 协议'''
    
    def __init__(self,dnsmanager = ChildsManager()):
        '''初始化根节点
        '''
        self.service = None
        self.childsmanager = dnsmanager
    
    def addServiceChannel(self,service):
        '''添加服务通道
        @param service: Service Object(In bilateral.services)
        '''
        self.service = service
    
    def remote_takeProxy(self,name,transport):
        '''设置代理通道
        @param addr: (hostname,port)hostname 根节点的主机名,根节点的端口
        '''
        log.msg('node [%s] takeProxy ready'%name)
        child = Child(name,name)
        self.childsmanager.addChild(child)
        child.setTransport(transport)
        self.doChildConnect(name, transport)
        
    def doChildConnect(self,name,transport):
        """当node节点连接时的处理
        """
        pass
        
    def remote_callTarget(self,command,*args,**kw):
        '''远程调用方法
        @param commandId: int 指令号
        @param data: str 调用参数
        '''
        data = self.service.callTarget(command,*args,**kw)
        return data
    
    def dropChild(self,*args,**kw):
        '''删除子节点记录'''
        self.childsmanager.dropChild(*args,**kw)
        
    def dropChildByID(self,childId):
        '''删除子节点记录'''
        self.doChildLostConnect(childId)
        self.childsmanager.dropChildByID(childId)
        
    def dropChildSessionId(self, session_id):
        '''删除子节点记录'''
        child = self.childsmanager.getChildBYSessionId(session_id)
        if not child:
            return
        child_id = child._id
        self.doChildLostConnect(child_id)
        self.childsmanager.dropChildByID(child_id)
        
    def doChildLostConnect(self,childId):
        """当node节点连接时的处理
        """
        pass
    
    def callChild(self,key,*args,**kw):
        '''调用子节点的接口
        @param childId: int 子节点的id
        return Defered Object
        '''
        return self.childsmanager.callChild(key,*args,**kw)
    
    def callChildByName(self,childname,*args,**kw):
        '''调用子节点的接口
        @param childId: int 子节点的id
        return Defered Object
        '''
        return self.childsmanager.callChildByName(childname,*args,**kw)
    

########NEW FILE########
__FILENAME__ = createproject
#coding:utf8
'''
Created on 2013-8-8

@author: lan (www.9miao.com)
'''
import sys,os
startmasterfile =['#coding:utf8\n', '\n', 'import os\n', "if os.name!='nt' and os.name!='posix':\n", '    from twisted.internet import epollreactor\n', '    epollreactor.install()\n', '\n', 'if __name__=="__main__":\n', '    from firefly.master.master import Master\n', '    master = Master()\n', "    master.config('config.json','appmain.py')\n", '    master.start()\n', '    \n', '    ']
configfile = ['{\n', 
              '"master":{"roothost":"localhost","rootport":9999,"webport":9998},\n',
               '"servers":{\n', '"net":{"netport":1000,"name":"gate","remoteport":[{"rootport":20001,"rootname":"gate"}],"app":"app.apptest"},\n',
               '"gate":{"rootport":20001,"name":"gate"}\n',
                '},\n', '"db":{\n', '"host":"localhost",\n',
                 '"user":"root",\n', '"passwd":"111",\n',
                  '"port":3306,\n',
                   '"db":"test",\n',
                    '"charset":"utf8"\n',
                     '},\n',
                     '"memcached":{\n',
                     '"urls":["127.0.0.1:11211"],\n',
                     '"hostname":"test"\n',
                     '}\n',
                      '}\n']
appmainfile = ['#coding:utf8\n', '\n','import os\n', "if os.name!='nt' and os.name!='posix':\n", '    from twisted.internet import epollreactor\n', '    epollreactor.install()\n', '\n', 'import json,sys\n', 'from firefly.server.server import FFServer\n', '\n', 'if __name__=="__main__":\n', '    args = sys.argv\n', '    servername = None\n', '    config = None\n', '    if len(args)>2:\n', '        servername = args[1]\n', "        config = json.load(open(args[2],'r'))\n", '    else:\n', '        raise ValueError\n', "    dbconf = config.get('db')\n", "    memconf = config.get('memcached')\n", "    sersconf = config.get('servers',{})\n", "    masterconf = config.get('master',{})\n", '    serconfig = sersconf.get(servername)\n', '    ser = FFServer()\n', '    ser.config(serconfig, servername=servername, dbconfig=dbconf, memconfig=memconf, masterconf=masterconf)\n', '    ser.start()\n', '    \n', '    ']
apptestfile = ['#coding:utf8\n', '\n', 'from firefly.server.globalobject import netserviceHandle\n', '\n', '@netserviceHandle\n', 'def echo_1(_conn,data):\n', '    return data\n', '\n', '    \n', '\n', '\n']
clientfile = ['#coding:utf8\n', '\n', 'import time\n', '\n', 'from socket import AF_INET,SOCK_STREAM,socket\n', 'from thread import start_new\n', 'import struct\n', "HOST='localhost'\n", 'PORT=1000\n', 'BUFSIZE=1024\n', 'ADDR=(HOST , PORT)\n', 'client = socket(AF_INET,SOCK_STREAM)\n', 'client.connect(ADDR)\n', '\n', 'def sendData(sendstr,commandId):\n', '    HEAD_0 = chr(0)\n', '    HEAD_1 = chr(0)\n', '    HEAD_2 = chr(0)\n', '    HEAD_3 = chr(0)\n', '    ProtoVersion = chr(0)\n', '    ServerVersion = 0\n', '    sendstr = sendstr\n', "    data = struct.pack('!sssss3I',HEAD_0,HEAD_1,HEAD_2,\\\n", '                       HEAD_3,ProtoVersion,ServerVersion,\\\n', '                       len(sendstr)+4,commandId)\n', '    senddata = data+sendstr\n', '    return senddata\n', '\n', 'def resolveRecvdata(data):\n', "    head = struct.unpack('!sssss3I',data[:17])\n", '    length = head[6]\n', '    data = data[17:17+length]\n', '    return data\n', '\n', 's1 = time.time()\n', '\n', 'def start():\n', '    for i in xrange(10):\n', "        client.sendall(sendData('asdfe',1))\n", '\n', 'for i in range(10):\n', '    start_new(start,())\n', 'while True:\n', '    pass\n', '\n']


def createfile(rootpath,path,filecontent):
    '''
    '''
    mfile = open(rootpath+'/'+path,'w')
    mfile.writelines(filecontent)
    mfile.close()


def execute(*args):
    if not args:
        sys.stdout.write("command error \n")
    projectname = args[0]
    sys.stdout.write("create dir %s \n"%projectname)
    rootpath = projectname
    os.mkdir(rootpath)
    createfile(rootpath,'startmaster.py',startmasterfile)
    createfile(rootpath,'config.json',configfile)
    createfile(rootpath,'appmain.py',appmainfile)
    
    rootpath = projectname+'/'+'app'
    os.mkdir(rootpath)
    createfile(rootpath,'__init__.py',[])
    createfile(rootpath,'apptest.py',apptestfile)
    
    rootpath = projectname+'/'+'tool'
    os.mkdir(rootpath)
    createfile(rootpath,'__init__.py',[])
    createfile(rootpath,'clienttest.py',clientfile)
    
    sys.stdout.write("create success \n")
    
    
########NEW FILE########
__FILENAME__ = reloadmodule
#coding:utf8
'''
Created on 2013-8-12

@author: lan (www.9miao.com)
'''
import urllib,sys

def execute(*args):
    """
    """
    if not args:
        masterport =9998
    else:
        masterport = int(args[0])
    url = "http://localhost:%s/reloadmodule"%masterport
    try:
        response = urllib.urlopen(url)
    except:
        response = None
    if response:
        sys.stdout.write("reload module success \n")
    else:
        sys.stdout.write("reload module failed \n")
########NEW FILE########
__FILENAME__ = stopservice
#coding:utf8
'''
Created on 2013-8-11

@author: lan (www.9miao.com)
'''
import urllib,sys

def execute(*args):
    """
    """
    if not args:
        masterport =9998
        hostname = "localhost"
    else:
        if len(args)>1:
            hostname = args[0]
            masterport = int(args[1])
        else:
            hostname = "localhost"
            masterport = int(args[0])
        
    url = "http://%s:%s/stop"%(hostname, masterport)
    try:
        response = urllib.urlopen(url)
    except:
        response = None
    if response:
        sys.stdout.write("stop service success \n")
    else:
        sys.stdout.write("stop service failed \n")
    
    
########NEW FILE########
__FILENAME__ = master
#coding:utf8
'''
Created on 2013-8-2

@author: lan (www.9miao.com)
'''
import subprocess,json,sys
from twisted.internet import reactor
from firefly.utils import  services
from firefly.distributed.root import PBRoot,BilateralFactory
from firefly.server.globalobject import GlobalObject
from twisted.web import vhost
from firefly.web.delayrequest import DelaySite
from twisted.python import log
from firefly.server.logobj import loogoo

reactor = reactor

MULTI_SERVER_MODE = 1
SINGLE_SERVER_MODE = 2
MASTER_SERVER_MODE = 3



class Master:
    """
    """
    
    def __init__(self):
        """
        """
        self.configpath = None
        self.mainpath = None
        self.root = None
        self.webroot = None
        
    def config(self,configpath,mainpath):
        """
        """
        self.configpath = configpath
        self.mainpath = mainpath
        
    def masterapp(self):
        """
        """
        config = json.load(open(self.configpath,'r'))
        GlobalObject().json_config = config
        mastercnf = config.get('master')
        rootport = mastercnf.get('rootport')
        webport = mastercnf.get('webport')
        masterlog = mastercnf.get('log')
        self.root = PBRoot()
        rootservice = services.Service("rootservice")
        self.root.addServiceChannel(rootservice)
        self.webroot = vhost.NameVirtualHost()
        self.webroot.addHost('0.0.0.0', './')
        GlobalObject().root = self.root
        GlobalObject().webroot = self.webroot
        if masterlog:
            log.addObserver(loogoo(masterlog))#日志处理
        log.startLogging(sys.stdout)
        import webapp
        import rootapp
        reactor.listenTCP(webport, DelaySite(self.webroot))
        reactor.listenTCP(rootport, BilateralFactory(self.root))
        
    def start(self):
        '''
        '''
        sys_args = sys.argv
        if len(sys_args)>2 and sys_args[1] == "single":
            server_name = sys_args[2]
            if server_name == "master":
                mode = MASTER_SERVER_MODE
            else:
                mode = SINGLE_SERVER_MODE
        else:
            mode = MULTI_SERVER_MODE
            server_name = ""
            
        if mode == MULTI_SERVER_MODE:
            self.masterapp()
            config = json.load(open(self.configpath,'r'))
            sersconf = config.get('servers')
            for sername in sersconf.keys():
                cmds = 'python %s %s %s'%(self.mainpath,sername,self.configpath)
                subprocess.Popen(cmds,shell=True)
            reactor.run()
        elif mode == SINGLE_SERVER_MODE:
            config = json.load(open(self.configpath,'r'))
            sername = server_name
            cmds = 'python %s %s %s'%(self.mainpath,sername,self.configpath)
            subprocess.Popen(cmds,shell=True)
        else:
            self.masterapp()
            reactor.run()
            
            

########NEW FILE########
__FILENAME__ = rootapp
#coding:utf8
'''
Created on 2013-8-7

@author: lan (www.9miao.com)
'''
from firefly.server.globalobject import GlobalObject
from twisted.python import log


def _doChildConnect(name,transport):
    """当server节点连接到master的处理
    """
    server_config = GlobalObject().json_config.get('servers',{}).get(name,{})
    remoteport = server_config.get('remoteport',[])
    child_host = transport.broker.transport.client[0]
    root_list = [rootport.get('rootname') for rootport in remoteport]
    GlobalObject().remote_map[name] = {"host":child_host,"root_list":root_list}
    #通知有需要连的node节点连接到此root节点
    for servername,remote_list in GlobalObject().remote_map.items():
        remote_host = remote_list.get("host","")
        remote_name_host = remote_list.get("root_list","")
        if name in remote_name_host:
            GlobalObject().root.callChild(servername,"remote_connect",name,remote_host)
    #查看当前是否有可供连接的root节点
    master_node_list = GlobalObject().remote_map.keys()
    for root_name in root_list:
        if root_name in master_node_list:
            root_host = GlobalObject().remote_map[root_name]['host']
            GlobalObject().root.callChild(name,"remote_connect",root_name,root_host)
    
def _doChildLostConnect(childId):
    """
    """
    try:
        del GlobalObject().remote_map[childId]
    except Exception,e:
        log.msg(str(e))

GlobalObject().root.doChildConnect = _doChildConnect
GlobalObject().root.doChildLostConnect = _doChildLostConnect
########NEW FILE########
__FILENAME__ = webapp
#coding:utf8
'''
Created on 2013-8-7

@author: lan (www.9miao.com)
'''
from twisted.web import resource
from twisted.internet import reactor
from firefly.server.globalobject import GlobalObject
root = GlobalObject().webroot
reactor = reactor
def ErrorBack(reason):
    pass

def masterwebHandle(cls):
    '''
    '''
    root.putChild(cls.__name__, cls())

@masterwebHandle
class stop(resource.Resource):
    '''stop service'''
    
    def render(self, request):
        '''
        '''
        for child in GlobalObject().root.childsmanager._childs.values():
            d = child.callbackChild('serverStop')
            d.addCallback(ErrorBack)
        reactor.callLater(0.5,reactor.stop)
        return "stop"

@masterwebHandle
class reloadmodule(resource.Resource):
    '''reload module'''
    
    def render(self, request):
        '''
        '''
        for child in GlobalObject().root.childsmanager._childs.values():
            d = child.callbackChild('sreload')
            d.addCallback(ErrorBack)
        return "reload"





########NEW FILE########
__FILENAME__ = connection
#coding:utf8
'''
Created on 2010-12-31

@author: sean_lan
'''

class Connection:
    '''
    '''
    def __init__(self, _conn):
        '''
        id 连接的ID
        transport 连接的通道
        '''
        self.id = _conn.transport.sessionno
        self.instance = _conn
        
    def loseConnection(self):
        '''断开与客户端的连接
        '''
        self.instance.transport.loseConnection()
    
    def safeToWriteData(self,topicID,msg):
        """发送消息
        """
        self.instance.safeToWriteData(msg,topicID)
        
        

########NEW FILE########
__FILENAME__ = datapack
#coding:utf8
'''
Created on 2013-8-1

@author: lan (www.9miao.com)
'''
from twisted.python import log
import struct

class DataPackError(Exception):
    """An error occurred binding to an interface"""

    def __str__(self):
        s = self.__doc__
        if self.args:
            s = '%s: %s' % (s, ' '.join(self.args))
        s = '%s.' % s
        return s

class DataPackProtoc:
    """数据包协议
    """
    def __init__(self,HEAD_0 = 0,HEAD_1=0,HEAD_2=0,HEAD_3=0,protoVersion= 0,serverVersion=0):
        '''初始化
        @param HEAD_0: int 协议头0
        @param HEAD_1: int 协议头1
        @param HEAD_2: int 协议头2
        @param HEAD_3: int 协议头3
        @param protoVersion: int 协议头版本号
        @param serverVersion: int 服务版本号
        '''
        self.HEAD_0 = HEAD_0
        self.HEAD_1 = HEAD_1
        self.HEAD_2 = HEAD_2
        self.HEAD_3 = HEAD_3
        self.protoVersion = protoVersion
        self.serverVersion = serverVersion
        
    def setHEAD_0(self, HEAD_0):
        self.HEAD_0 = HEAD_0
        
    def setHEAD_1(self, HEAD_1):
        self.HEAD_1 = HEAD_1
    
    def setHEAD_2(self, HEAD_2):
        self.HEAD_2 = HEAD_2
        
    def setHEAD_3(self, HEAD_3):
        self.HEAD_3 = HEAD_3
        
    def setprotoVersion(self, protoVersion):
        self.protoVersion = protoVersion
    
    def setserverVersion(self, serverVersion):
        self.serverVersion = serverVersion
        
    def getHeadlength(self):
        """获取数据包的长度
        """
        return 17
        
    def unpack(self,dpack):
        '''解包
        '''
        try:
            ud = struct.unpack('!sssss3I',dpack)
        except DataPackError,de:
            log.err(de)
            return {'result':False,'command':0,'length':0}
        HEAD_0 = ord(ud[0])
        HEAD_1 = ord(ud[1])
        HEAD_2 = ord(ud[2])
        HEAD_3 = ord(ud[3])
        protoVersion = ord(ud[4])
        serverVersion = ud[5]
        length = ud[6]-4
        command = ud[7]
        if HEAD_0 <>self.HEAD_0 or HEAD_1<>self.HEAD_1 or\
             HEAD_2<>self.HEAD_2 or HEAD_3<>self.HEAD_3 or\
              protoVersion<>self.protoVersion or serverVersion<>self.serverVersion:
            return {'result':False,'command':0,'length':0}
        return {'result':True,'command':command,'length':length}
        
    def pack(self,response,command):
        '''打包数据包
        '''
        HEAD_0 = chr(self.HEAD_0)
        HEAD_1 = chr(self.HEAD_1)
        HEAD_2 = chr(self.HEAD_2)
        HEAD_3 = chr(self.HEAD_3)
        protoVersion = chr(self.protoVersion)
        serverVersion = self.serverVersion
        length = response.__len__()+4
        commandID = command
        data = struct.pack('!sssss3I',HEAD_0,HEAD_1,HEAD_2,HEAD_3,\
                           protoVersion,serverVersion,length,commandID)
        data = data + response
        return data
        
    
    
########NEW FILE########
__FILENAME__ = manager
#coding:utf8
'''
Created on 2010-12-31
连接管理器
@author: sean_lan
'''

from twisted.python import log
from connection import Connection

class ConnectionManager:
    ''' 连接管理器
    @param _connections: dict {connID:conn Object}管理的所有连接
    '''
    
    def __init__(self):
        '''初始化
        @param _connections: dict {connID:conn Object}
        '''
        self._connections = {}
        
    def getNowConnCnt(self):
        '''获取当前连接数量'''
        return len(self._connections.items())
    
    def addConnection(self, conn):
        '''加入一条连接
        @param _conn: Conn object
        '''
        _conn = Connection(conn)
        if self._connections.has_key(_conn.id):
            raise Exception("系统记录冲突")
        self._connections[_conn.id] = _conn
            
    def dropConnectionByID(self, connID):
        '''更加连接的id删除连接实例
        @param connID: int 连接的id
        '''
        try:
            del self._connections[connID]
        except Exception as e:
            log.msg(str(e))
        
    def getConnectionByID(self, connID):
        """根据ID获取一条连接
        @param connID: int 连接的id
        """
        return self._connections.get(connID,None)
    
    def loseConnection(self,connID):
        """根据连接ID主动端口与客户端的连接
        """
        conn = self.getConnectionByID(connID)
        if conn:
            conn.loseConnection()
        
    def pushObject(self,topicID , msg, sendList):
        """主动推送消息
        """
        for target in sendList:
            try:
                conn = self.getConnectionByID(target)
                if conn:
                    conn.safeToWriteData(topicID,msg)
            except Exception,e:
                log.err(str(e))



########NEW FILE########
__FILENAME__ = protoc
#coding:utf8
'''
Created on 2011-9-20
登陆服务器协议
@author: lan (www.9miao.com)
'''
from twisted.internet import protocol,reactor
from twisted.python import log
from manager import ConnectionManager
from datapack import DataPackProtoc
reactor = reactor

def DefferedErrorHandle(e):
    '''延迟对象的错误处理'''
    log.err(str(e))
    return

class LiberateProtocol(protocol.Protocol):
    '''协议'''
    
    buff = ""
    
    def connectionMade(self):
        '''连接建立处理
        '''
        log.msg('Client %d login in.[%s,%d]'%(self.transport.sessionno,\
                self.transport.client[0],self.transport.client[1]))
        self.factory.connmanager.addConnection(self)
        self.factory.doConnectionMade(self)
        self.datahandler=self.dataHandleCoroutine()
        self.datahandler.next()
        
    def connectionLost(self,reason):
        '''连接断开处理
        '''
        log.msg('Client %d login out.'%(self.transport.sessionno))
        self.factory.doConnectionLost(self)
        self.factory.connmanager.dropConnectionByID(self.transport.sessionno)
        
    def safeToWriteData(self,data,command):
        '''线程安全的向客户端发送数据
        @param data: str 要向客户端写的数据
        '''
        if not self.transport.connected or data is None:
            return
        senddata = self.factory.produceResult(data,command)
        reactor.callFromThread(self.transport.write,senddata)
        
    def dataHandleCoroutine(self):
        """
        """
        length = self.factory.dataprotocl.getHeadlength()#获取协议头的长度
        while True:
            data = yield
            self.buff += data
            while self.buff.__len__() >= length: 
                unpackdata = self.factory.dataprotocl.unpack(self.buff[:length])
                if not unpackdata.get('result'):
                    log.msg('illegal data package --')
                    self.transport.loseConnection()
                    break
                command = unpackdata.get('command')
                rlength = unpackdata.get('length')
                request = self.buff[length:length+rlength]
                if request.__len__()< rlength:
                    log.msg('some data lose')
                    break
                self.buff = self.buff[length+rlength:]
                d = self.factory.doDataReceived(self,command,request)
                if not d:
                    continue
                d.addCallback(self.safeToWriteData,command)
                d.addErrback(DefferedErrorHandle)

            
        
    def dataReceived(self, data):
        '''数据到达处理
        @param data: str 客户端传送过来的数据
        '''
        self.datahandler.send(data)
            
class LiberateFactory(protocol.ServerFactory):
    '''协议工厂'''
    
    protocol = LiberateProtocol
    
    def __init__(self,dataprotocl=DataPackProtoc()):
        '''初始化
        '''
        self.service = None
        self.connmanager = ConnectionManager()
        self.dataprotocl = dataprotocl
        
    def setDataProtocl(self,dataprotocl):
        '''
        '''
        self.dataprotocl = dataprotocl
        
    def doConnectionMade(self,conn):
        '''当连接建立时的处理'''
        pass
    
    def doConnectionLost(self,conn):
        '''连接断开时的处理'''
        pass
    
    def addServiceChannel(self,service):
        '''添加服务通道'''
        self.service = service
    
    def doDataReceived(self,conn,commandID,data):
        '''数据到达时的处理'''
        defer_tool = self.service.callTarget(commandID,conn,data)
        return defer_tool
    
    def produceResult(self,command,response):
        '''产生客户端需要的最终结果
        @param response: str 分布式客户端获取的结果
        '''
        return self.dataprotocl.pack(command,response)
    
    def loseConnection(self,connID):
        """主动端口与客户端的连接
        """
        self.connmanager.loseConnection(connID)
    
    def pushObject(self,topicID , msg, sendList):
        '''服务端向客户端推消息
        @param topicID: int 消息的主题id号
        @param msg: 消息的类容，protobuf结构类型
        @param sendList: 推向的目标列表(客户端id 列表)
        '''
        self.connmanager.pushObject(topicID, msg, sendList)


########NEW FILE########
__FILENAME__ = firefly-admin
#coding:utf8
'''
Created on 2013-8-8

@author: lan (www.9miao.com)
'''
from firefly import management
import sys

if __name__ == "__main__":
    args = sys.argv
    management.execute_commands(*args)
########NEW FILE########
__FILENAME__ = admin
#coding:utf8
'''
Created on 2013-8-12

@author: lan (www.9miao.com)
'''
from globalobject import GlobalObject,masterserviceHandle
from twisted.internet import reactor
from twisted.python import log

reactor = reactor


@masterserviceHandle
def serverStop():
    """
    """
    log.msg('stop')
    if GlobalObject().stophandler:
        GlobalObject().stophandler()
    reactor.callLater(0.5,reactor.stop)
    return True

@masterserviceHandle
def sreload():
    """
    """
    log.msg('reload')
    if GlobalObject().reloadmodule:
        reload(GlobalObject().reloadmodule)
    return True

@masterserviceHandle
def remote_connect(rname, rhost):
    """
    """
    GlobalObject().remote_connect(rname, rhost)


########NEW FILE########
__FILENAME__ = globalobject
#coding:utf8
'''
Created on 2013-8-2

@author: lan (www.9miao.com)
'''
from firefly.utils.singleton import Singleton

class GlobalObject:
    
    __metaclass__ = Singleton
    
    def __init__(self):
        self.netfactory = None#net前端
        self.root = None#分布式root节点
        self.remote = {}#remote节点
        self.db = None
        self.stophandler = None
        self.webroot = None
        self.masterremote = None
        self.reloadmodule = None
        self.remote_connect = None
        self.json_config = {}
        self.remote_map = {}
        
    def config(self,netfactory=None,root = None,remote=None,db=None):
        self.netfactory = netfactory
        self.root = root
        self.remote = remote
        self.db = db
        
def masterserviceHandle(target):
    """
    """
    GlobalObject().masterremote._reference._service.mapTarget(target)
        
def netserviceHandle(target):
    """
    """
    GlobalObject().netfactory.service.mapTarget(target)
        
def rootserviceHandle(target):
    """
    """
    GlobalObject().root.service.mapTarget(target)
    
class webserviceHandle:
    """这是一个修饰符对象
    """
    
    def __init__(self,url=None):
        """
        @param url: str http 访问的路径
        """
        self._url = url
        
    def __call__(self,cls):
        """
        """
        from twisted.web.resource import Resource
        if self._url:
            child_name = self._url
        else:
            child_name = cls.__name__
        path_list = child_name.split('/')
        temp_res = None
        path_list = [path for path in path_list if path]
        patn_len = len(path_list)
        for index,path in enumerate(path_list):
            if index==0:
                temp_res = GlobalObject().webroot
            if index==patn_len-1:
                res = cls()
                temp_res.putChild(path, res)
                return
            else:
                res = temp_res.children.get(path)
                if not res:
                    res = Resource()
                    temp_res.putChild(path, res)
            temp_res=res
    

    
class remoteserviceHandle:
    """
    """
    def __init__(self,remotename):
        """
        """
        self.remotename = remotename
        
    def __call__(self,target):
        """
        """
        GlobalObject().remote[self.remotename]._reference._service.mapTarget(target)
        

########NEW FILE########
__FILENAME__ = logobj
#coding:utf8
'''
Created on 2013-8-6

@author: lan (www.9miao.com)
'''
from twisted.python import log
from zope.interface import implements
import datetime


class loogoo:
    '''日志处理
    '''
    implements(log.ILogObserver)
    
    def __init__(self,logpath):
        '''配置日志路径
        '''
        self.file = file(logpath, 'w')
        
    def __call__(self, eventDict):
        '''日志处理
        '''
        if 'logLevel' in eventDict:
            level = eventDict['logLevel']
        elif eventDict['isError']:
            level = 'ERROR'
        else:
            level = 'INFO'
        text = log.textFromEventDict(eventDict)
        if text is None or level != 'ERROR':
            return
        nowdate = datetime.datetime.now()
        self.file.write('['+str(nowdate)+']\n'+str(level)+ '\n\t' + text + '\r\n')
        self.file.flush()
        

########NEW FILE########
__FILENAME__ = server
#coding:utf8
'''
Created on 2013-8-2

@author: lan (www.9miao.com)
'''
from firefly.netconnect.protoc import LiberateFactory
from twisted.web import vhost
from firefly.web.delayrequest import DelaySite
from firefly.distributed.root import PBRoot,BilateralFactory
from firefly.distributed.node import RemoteObject
from firefly.dbentrust.dbpool import dbpool
from firefly.dbentrust.memclient import mclient
from logobj import loogoo
from globalobject import GlobalObject
from twisted.python import log
from twisted.internet import reactor
from firefly.utils import services
import os,sys,affinity

reactor = reactor

def serverStop():
    log.msg('stop')
    if GlobalObject().stophandler:
        GlobalObject().stophandler()
    reactor.callLater(0.5,reactor.stop)
    return True

class FFServer:
    
    def __init__(self):
        '''
        '''
        self.netfactory = None#net前端
        self.root = None#分布式root节点
        self.webroot = None#http服务
        self.remote = {}#remote节点
        self.master_remote = None
        self.db = None
        self.mem = None
        self.servername = None
        self.remoteportlist = []
        
    def config(self, config, servername=None, dbconfig=None,
                memconfig=None, masterconf=None):
        '''配置服务器
        '''
        GlobalObject().json_config = config
        netport = config.get('netport')#客户端连接
        webport = config.get('webport')#http连接
        rootport = config.get('rootport')#root节点配置
        self.remoteportlist = config.get('remoteport',[])#remote节点配置列表
        if not servername:
            servername = config.get('name')#服务器名称
        logpath = config.get('log')#日志
        hasdb = config.get('db')#数据库连接
        hasmem = config.get('mem')#memcached连接
        app = config.get('app')#入口模块名称
        cpuid = config.get('cpu')#绑定cpu
        mreload = config.get('reload')#重新加载模块名称
        self.servername = servername
            
        if netport:
            self.netfactory = LiberateFactory()
            netservice = services.CommandService("netservice")
            self.netfactory.addServiceChannel(netservice)
            reactor.listenTCP(netport,self.netfactory)
            
        if webport:
            self.webroot = vhost.NameVirtualHost()
            GlobalObject().webroot = self.webroot
            reactor.listenTCP(webport, DelaySite(self.webroot))
            
        if rootport:
            self.root = PBRoot()
            rootservice = services.Service("rootservice")
            self.root.addServiceChannel(rootservice)
            reactor.listenTCP(rootport, BilateralFactory(self.root))
            
        for cnf in self.remoteportlist:
            rname = cnf.get('rootname')
            self.remote[rname] = RemoteObject(self.servername)
            
        if hasdb and dbconfig:
            log.msg(str(dbconfig))
            dbpool.initPool(**dbconfig)
            
        if hasmem and memconfig:
            urls = memconfig.get('urls')
            hostname = str(memconfig.get('hostname'))
            mclient.connect(urls, hostname)
            
        if logpath:
            log.addObserver(loogoo(logpath))#日志处理
        log.startLogging(sys.stdout)
        
        if cpuid:
            affinity.set_process_affinity_mask(os.getpid(), cpuid)
        GlobalObject().config(netfactory = self.netfactory, root=self.root,
                    remote = self.remote)
        if app:
            __import__(app)
        if mreload:
            _path_list = mreload.split(".")
            GlobalObject().reloadmodule = __import__(mreload,fromlist=_path_list[:1])
        GlobalObject().remote_connect = self.remote_connect
        if masterconf:
            masterport = masterconf.get('rootport')
            masterhost = masterconf.get('roothost')
            self.master_remote = RemoteObject(servername)
            addr = ('localhost',masterport) if not masterhost else (masterhost,masterport)
            self.master_remote.connect(addr)
            GlobalObject().masterremote = self.master_remote
        import admin
        
    def remote_connect(self, rname, rhost):
        """
        """
        for cnf in self.remoteportlist:
            _rname = cnf.get('rootname')
            if rname == _rname:
                rport = cnf.get('rootport')
                if not rhost:
                    addr = ('localhost',rport)
                else:
                    addr = (rhost,rport)
                self.remote[rname].connect(addr)
                break
        
    def start(self):
        '''启动服务器
        '''
        log.msg('%s start...'%self.servername)
        log.msg('%s pid: %s'%(self.servername,os.getpid()))
        reactor.run()
        
        

########NEW FILE########
__FILENAME__ = test_dbentrust
#coding:utf8
'''
Created on 2013-7-31

@author: lan (www.9miao.com)
'''
from firefly.dbentrust.dbpool import dbpool
from firefly.dbentrust.madminanager import MAdminManager
from firefly.dbentrust import mmode 
from firefly.dbentrust.memclient import mclient
import time


if __name__=="__main__":

    
#    CREATE TABLE `tb_register` (
#   `id` int(11) NOT NULL AUTO_INCREMENT COMMENT 'id',
#   `username` varchar(255) CHARACTER SET utf8 COLLATE utf8_bin NOT NULL DEFAULT '' COMMENT '用户名',
#   `password` varchar(255) CHARACTER SET utf8 COLLATE utf8_bin NOT NULL DEFAULT '' COMMENT '用户密码',
#   PRIMARY KEY (`id`,`username`)
#   ) ENGINE=MyISAM AUTO_INCREMENT=1 DEFAULT CHARSET=utf8
#
    hostname = "localhost"
    username = 'root'
    password = '111'
    dbname = 'test'
    charset = 'utf8'
    tablename = "test1"#
    aa = {'host':"localhost",
    'user':'root',
    'passwd':'111',
    'db':'test',
    'port':3306,
    'charset':'utf8'}
    dbpool.initPool(**aa)
    mclient.connect(['127.0.0.1:11211'], "test")

    mmanager = MAdminManager()
    m1 = mmode.MAdmin( 'test1', 'id', incrkey='id')
    m1.insert()
    print m1.get('_incrvalue')
    m2 = mmode.MAdmin( 'test1', 'id', incrkey='id')
    print m2.get('_incrvalue')


########NEW FILE########
__FILENAME__ = test_distributed_node
#coding:utf8
'''
Created on 2011-10-17

@author: lan (www.9miao.com)
'''
from firefly.utils import services
from firefly.distributed.node import RemoteObject
from twisted.internet import reactor
from twisted.python import util,log
import sys

log.startLogging(sys.stdout)

reactor = reactor

addr = ('localhost',1000)#目标主机的地址
remote = RemoteObject('test_node')#实例化远程调用对象

service = services.Service('reference',services.Service.SINGLE_STYLE)#实例化一条服务对象
remote.addServiceChannel(service)


def serviceHandle(target):
    '''服务处理
    @param target: func Object
    '''
    service.mapTarget(target)

@serviceHandle
def printOK(data):
    print data
    print "############################"
    return "call printOK_01"
    
def apptest(commandID,*args,**kw):
    d = remote.callRemote(commandID,*args,**kw)
    d.addCallback(lambda a:util.println(a))
    return d

def startClient():
    reactor.callLater(1,apptest,'printData1',u"node测试1",u"node测试2")
    remote.connect(addr)#连接远程主机
    reactor.run()

if __name__=='__main__':
    startClient()


########NEW FILE########
__FILENAME__ = test_distributed_root
#coding:utf8
'''
Created on 2011-10-17

@author: lan (www.9miao.com)
'''
from firefly.utils import  services
from firefly.distributed.root import PBRoot,BilateralFactory
from twisted.internet import reactor
from twisted.python import log
import sys
reactor = reactor
log.startLogging(sys.stdout)
    
root = PBRoot()
ser = services.Service('test')
root.addServiceChannel(ser)


def serviceHandle(target):
    '''服务处理
    @param target: func Object
    '''
    ser.mapTarget(target)

@serviceHandle
def printData1(data,data1):
    print data,data1
    print "############################"
#    d = root.callChildByName("test_node",1,u'Root测试')
    return data

@serviceHandle
def printData2(data,data1):
    print data,data1
    print "############################"
#    d = root.callChildByName("test_node",1,u'Root测试')
    return data

if __name__=='__main__':
    reactor.listenTCP(1000, BilateralFactory(root))
    reactor.callLater(5,root.callChildByName,'test_node','printOK','asdfawefasdf')
    reactor.run()

########NEW FILE########
__FILENAME__ = test_netconnect_client
#coding:utf8
'''
Created on 2011-10-12

@author: lan (www.9miao.com)
'''
import time

from socket import AF_INET,SOCK_STREAM,socket
from thread import start_new
import struct
HOST='localhost'
PORT=1000
BUFSIZE=1024
ADDR=(HOST , PORT)
client = socket(AF_INET,SOCK_STREAM)
client.connect(ADDR)

def sendData(sendstr,commandId):
    HEAD_0 = chr(0)
    HEAD_1 = chr(0)
    HEAD_2 = chr(0)
    HEAD_3 = chr(0)
    ProtoVersion = chr(0)
    ServerVersion = 0
    sendstr = sendstr
    data = struct.pack('!sssss3I',HEAD_0,HEAD_1,HEAD_2,\
                       HEAD_3,ProtoVersion,ServerVersion,\
                       len(sendstr)+4,commandId)
    senddata = data+sendstr
    return senddata

def resolveRecvdata(data):
    head = struct.unpack('!sssss3I',data[:17])
    length = head[6]
    data = data[17:17+length]
    return data

s1 = time.time()

def start():
    for i in xrange(10):
        client.sendall(sendData('asdfe',1))

for i in range(10):
    start_new(start,())
while True:
    pass


########NEW FILE########
__FILENAME__ = test_netconnect_server
#coding:utf8
'''
Created on 2011-10-3

@author: lan (www.9miao.com)
'''
import sys,os

if os.name!='nt':#对系统的类型的判断，如果不是NT系统的话使用epoll
    from twisted.internet import epollreactor
    epollreactor.install()
        
from twisted.internet import reactor
from twisted.python import log
from firefly.utils import services
from firefly.netconnect.protoc import LiberateFactory

reactor = reactor
service = services.CommandService("loginService",runstyle= services.Service.PARALLEL_STYLE)

def serviceHandle(target):
    '''服务处理
    @param target: func Object
    '''
    service.mapTarget(target)
    
factory = LiberateFactory()

def doConnectionLost(conn):
    print conn.transport

factory.doConnectionLost = doConnectionLost

def serverstart():
    '''服务配置
    '''
    log.startLogging(sys.stdout)
    factory.addServiceChannel(service)
    reactor.callLater(10,factory.pushObject,111,'asdfe',[0])
    reactor.callLater(15,factory.loseConnection,0)
    reactor.listenTCP(1000,factory)
    reactor.run()
    
@serviceHandle
def echo_1(_conn,data):
    addr = _conn.transport.client
    print addr
    return "欢迎"

if __name__ == "__main__":
    
    serverstart()


########NEW FILE########
__FILENAME__ = test_server_apptest
#coding:utf8
'''
Created on 2013-8-2

@author: lan (www.9miao.com)
'''
from server.globalobject import GlobalObject

def netserviceHandle(target):
    '''服务处理
    @param target: func Object
    '''
    GlobalObject().netfactory.service.mapTarget(target)
    
@netserviceHandle
def echo_111(_conn,data):
    return data




########NEW FILE########
__FILENAME__ = test_server_main
#coding:utf8
'''
Created on 2013-8-6

@author: lan (www.9miao.com)
'''
import json,sys
from firefly.server.server import FFServer

if __name__=="__main__":
    args = sys.argv
    servername = None
    config = None
    if len(args)>2:
        servername = args[1]
        config = json.load(open(args[2],'r'))
    else:
        raise ValueError
    dbconf = config.get('db')
    memconf = config.get('memcached')
    sersconf = config.get('servers',{})
    masterconf = config.get('master',{})
    serconfig = sersconf.get(servername)
    ser = FFServer()
    ser.config(serconfig, dbconfig=dbconf, memconfig=memconf,masterconf=masterconf)
    ser.start()
    
    
########NEW FILE########
__FILENAME__ = test_server_master
#coding:utf8
'''
Created on 2013-8-2

@author: lan (www.9miao.com)
'''
import os
if os.name!='nt':
    from twisted.internet import epollreactor
    epollreactor.install()
    
def println(a):
    print a

if __name__=="__main__":
    from firefly.master.master import Master
    master = Master()
    master.config('config.json','test_server_main.py')
    master.start()
    
    
########NEW FILE########
__FILENAME__ = interfaces
#coding:utf8
'''
Created on 2013-10-17

@author: lan (www.9miao.com)
'''
from __future__ import division, absolute_import
from zope.interface import Interface


class IDataPackProtoc(Interface):
    
    def getHeadlength():
        """获取数据包的长度
        """
        pass
        
    def unpack():
        '''解包
        '''
        
    def pack():
        '''打包数据包
        '''
        
    
    


########NEW FILE########
__FILENAME__ = services
#coding:utf8
'''
Created on 2011-1-3
服务类
@author: sean_lan
'''
import threading
from twisted.internet import defer,threads
from twisted.python import log


class Service(object):
    """A remoting service 
    
    attributes:
    ============
     * name - string, service name.
     * runstyle 
    """
    SINGLE_STYLE = 1
    PARALLEL_STYLE = 2

    def __init__(self, name,runstyle = SINGLE_STYLE):
        self._name = name
        self._runstyle = runstyle
        self.unDisplay = set()
        self._lock = threading.RLock()
        self._targets = {} # Keeps track of targets internally

    def __iter__(self):
        return self._targets.itervalues()
    
    def addUnDisplayTarget(self,command):
        '''Add a target unDisplay when client call it.'''
        self.unDisplay.add(command)

    def mapTarget(self, target):
        """Add a target to the service."""
        self._lock.acquire()
        try:
            key = target.__name__
            if self._targets.has_key(key):
                exist_target = self._targets.get(key)
                raise "target [%d] Already exists,\
                Conflict between the %s and %s"%(key,exist_target.__name__,target.__name__)
            self._targets[key] = target
        finally:
            self._lock.release()

    def unMapTarget(self, target):
        """Remove a target from the service."""
        self._lock.acquire()
        try:
            key = target.__name__
            if key in self._targets:
                del self._targets[key]
        finally:
            self._lock.release()
            
    def unMapTargetByKey(self,targetKey):
        """Remove a target from the service."""
        self._lock.acquire()
        try:
            del self._targets[targetKey]
        finally:
            self._lock.release()
            
    def getTarget(self, targetKey):
        """Get a target from the service by name."""
        self._lock.acquire()
        try:
            target = self._targets.get(targetKey, None)
        finally:
            self._lock.release()
        return target
    
    def callTarget(self,targetKey,*args,**kw):
        '''call Target
        @param conn: client connection
        @param targetKey: target ID
        @param data: client data
        '''
        if self._runstyle == self.SINGLE_STYLE:
            result = self.callTargetSingle(targetKey,*args,**kw)
        else:
            result = self.callTargetParallel(targetKey,*args,**kw)
        return result
    
    def callTargetSingle(self,targetKey,*args,**kw):
        '''call Target by Single
        @param conn: client connection
        @param targetKey: target ID
        @param data: client data
        '''
        target = self.getTarget(targetKey)
        
        self._lock.acquire()
        try:
            if not target:
                log.err('the command '+str(targetKey)+' not Found on service')
                return None
            if targetKey not in self.unDisplay:
                log.msg("call method %s on service[single]"%target.__name__)
            defer_data = target(*args,**kw)
            if not defer_data:
                return None
            if isinstance(defer_data,defer.Deferred):
                return defer_data
            d = defer.Deferred()
            d.callback(defer_data)
        finally:
            self._lock.release()
        return d
    
    def callTargetParallel(self,targetKey,*args,**kw):
        '''call Target by Single
        @param conn: client connection
        @param targetKey: target ID
        @param data: client data
        '''
        self._lock.acquire()
        try:
            target = self.getTarget(targetKey)
            if not target:
                log.err('the command '+str(targetKey)+' not Found on service')
                return None
            log.msg("call method %s on service[parallel]"%target.__name__)
            d = threads.deferToThread(target,*args,**kw)
        finally:
            self._lock.release()
        return d
    

class CommandService(Service):
    """A remoting service 
    According to Command ID search target
    """
    def mapTarget(self, target):
        """Add a target to the service."""
        self._lock.acquire()
        try:
            key = int((target.__name__).split('_')[-1])
            if self._targets.has_key(key):
                exist_target = self._targets.get(key)
                raise "target [%d] Already exists,\
                Conflict between the %s and %s"%(key,exist_target.__name__,target.__name__)
            self._targets[key] = target
        finally:
            self._lock.release()
            
    def unMapTarget(self, target):
        """Remove a target from the service."""
        self._lock.acquire()
        try:
            key = int((target.__name__).split('_')[-1])
            if key in self._targets:
                del self._targets[key]
        finally:
            self._lock.release()
    

    
    
    
            
########NEW FILE########
__FILENAME__ = singleton
# coding: utf-8

class Singleton(type):
    """Singleton Metaclass"""
    
    def __init__(self, name, bases, dic):
        super(Singleton, self).__init__(name, bases, dic)
        self.instance = None
        
    def __call__(self, *args, **kwargs):
        if self.instance is None:
            self.instance = super(Singleton, self).__call__(*args, **kwargs)
        return self.instance
        
########NEW FILE########
__FILENAME__ = delayrequest
#coding:utf8
'''
Created on 2013-9-3

@author: lan
'''
from twisted.web.server import Request,Site
from twisted.internet import defer
from twisted.web import http,html
from twisted.python import log, reflect
from twisted.web import resource
from twisted.web.error import UnsupportedMethod
from twisted.web.microdom import escape

import string,types

NOT_DONE_YET = 1

# backwards compatability
date_time_string = http.datetimeToString
string_date_time = http.stringToDatetime

# Support for other methods may be implemented on a per-resource basis.
supportedMethods = ('GET', 'HEAD', 'POST')


class DelayRequest(Request):
    
    def __init__(self, *args, **kw):
        Request.__init__(self,*args, **kw)
        
    def render(self, resrc):
        """
        Ask a resource to render itself.

        @param resrc: a L{twisted.web.resource.IResource}.
        """
        try:
            body = resrc.render(self)
        except UnsupportedMethod, e:
            allowedMethods = e.allowedMethods
            if (self.method == "HEAD") and ("GET" in allowedMethods):
                # We must support HEAD (RFC 2616, 5.1.1).  If the
                # resource doesn't, fake it by giving the resource
                # a 'GET' request and then return only the headers,
                # not the body.
                log.msg("Using GET to fake a HEAD request for %s" %
                        (resrc,))
                self.method = "GET"
                self._inFakeHead = True
                body = resrc.render(self)

                if body is NOT_DONE_YET:
                    log.msg("Tried to fake a HEAD request for %s, but "
                            "it got away from me." % resrc)
                    # Oh well, I guess we won't include the content length.
                else:
                    self.setHeader('content-length', str(len(body)))

                self._inFakeHead = False
                self.method = "HEAD"
                self.write('')
                self.finish()
                return

            if self.method in (supportedMethods):
                # We MUST include an Allow header
                # (RFC 2616, 10.4.6 and 14.7)
                self.setHeader('Allow', ', '.join(allowedMethods))
                s = ('''Your browser approached me (at %(URI)s) with'''
                     ''' the method "%(method)s".  I only allow'''
                     ''' the method%(plural)s %(allowed)s here.''' % {
                    'URI': escape(self.uri),
                    'method': self.method,
                    'plural': ((len(allowedMethods) > 1) and 's') or '',
                    'allowed': string.join(allowedMethods, ', ')
                    })
                epage = resource.ErrorPage(http.NOT_ALLOWED,
                                           "Method Not Allowed", s)
                body = epage.render(self)
            else:
                epage = resource.ErrorPage(
                    http.NOT_IMPLEMENTED, "Huh?",
                    "I don't know how to treat a %s request." %
                    (escape(self.method),))
                body = epage.render(self)
        # end except UnsupportedMethod

        if body == NOT_DONE_YET:
            return
        if not isinstance(body, defer.Deferred) and type(body) is not types.StringType:
            body = resource.ErrorPage(
                http.INTERNAL_SERVER_ERROR,
                "Request did not return a string",
                "Request: " + html.PRE(reflect.safe_repr(self)) + "<br />" +
                "Resource: " + html.PRE(reflect.safe_repr(resrc)) + "<br />" +
                "Value: " + html.PRE(reflect.safe_repr(body))).render(self)

        if self.method == "HEAD":
            if len(body) > 0:
                # This is a Bad Thing (RFC 2616, 9.4)
                log.msg("Warning: HEAD request %s for resource %s is"
                        " returning a message body."
                        "  I think I'll eat it."
                        % (self, resrc))
                self.setHeader('content-length', str(len(body)))
            self.write('')
            self.finish()
        else:
            if isinstance(body, defer.Deferred):
                body.addCallback(self._deferwrite)
            else:
                self.setHeader('content-length', str(len(body)))
                self.write(body)
                self.finish()
                
    def _deferwrite(self,body):
        '''延迟等待数据返回
        '''
        self.setHeader('content-length', str(len(body)))
        self.write(body)
        self.finish()
        
        
class DelaySite(Site):
    
    def __init__(self, resource, logPath=None, timeout=60*60*12):
        Site.__init__(self, resource, logPath=logPath, timeout=timeout)
        self.requestFactory = DelayRequest
        
    
    
########NEW FILE########
__FILENAME__ = _version
#coding:utf8
'''
Created on 2013-10-21

@author: lan (www.9miao.com)
'''

from twisted.python import versions
version = versions.Version('firefly', 1, 3, 3)
########NEW FILE########
