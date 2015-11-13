__FILENAME__ = connection
        
class Database(object):
    placeholder = '?'
    
    def connect(self, dbtype, *args, **kwargs):
        if dbtype == 'sqlite3':
            import sqlite3
            self.connection = sqlite3.connect(*args)
        elif dbtype == 'mysql':
            import MySQLdb
            self.connection = MySQLdb.connect(**kwargs)
            self.placeholder = '%s'

class DBConn(object):
    def __init__(self):
        self.b_debug = False
        self.b_commit = True
        self.conn = None

autumn_db = DBConn()
autumn_db.conn = Database()

########NEW FILE########
__FILENAME__ = query
from autumn.db import escape
from autumn.db.connection import autumn_db

class Query(object):
    '''
    Gives quick access to database by setting attributes (query conditions, et
    cetera), or by the sql methods.
    
    Instance Methods
    ----------------
    
    Creating a Query object requires a Model class at the bare minimum. The 
    doesn't run until results are pulled using a slice, ``list()`` or iterated
    over.
    
    For example::
    
        q = Query(model=MyModel)
        
    This sets up a basic query without conditions. We can set conditions using
    the ``filter`` method::
        
        q.filter(name='John', age=30)
        
    We can also chain the ``filter`` method::
    
        q.filter(name='John').filter(age=30)
        
    In both cases the ``WHERE`` clause will become::
    
        WHERE `name` = 'John' AND `age` = 30
    
    You can also order using ``order_by`` to sort the results::
    
        # The second arg is optional and will default to ``ASC``
        q.order_by('column', 'DESC')
    
    You can limit result sets by slicing the Query instance as if it were a 
    list. Query is smart enough to translate that into the proper ``LIMIT`` 
    clause when the query hasn't yet been run::
    
        q = Query(model=MyModel).filter(name='John')[:10]   # LIMIT 0, 10
        q = Query(model=MyModel).filter(name='John')[10:20] # LIMIT 10, 10
        q = Query(model=MyModel).filter(name='John')[0]    # LIMIT 0, 1
    
    Simple iteration::
    
        for obj in Query(model=MyModel).filter(name='John'):
            # Do something here
            
    Counting results is easy with the ``count`` method. If used on a ``Query``
    instance that has not yet retrieve results, it will perform a ``SELECT
    COUNT(*)`` instead of a ``SELECT *``. ``count`` returns an integer::
        
        count = Query(model=MyModel).filter=(name='John').count()
            
    Class Methods
    -------------
    
    ``Query.raw_sql(sql, values)`` returns a database cursor. Usage::
    
        query = 'SELECT * FROM `users` WHERE id = ?'
        values = (1,) # values must be a tuple or list
        
        # Now we have the database cursor to use as we wish
        cursor = Query.raw_swl(query, values)
        
    ``Query.sql(sql, values)`` has the same syntax as ``Query.raw_sql``, but 
    it returns a dictionary of the result, the field names being the keys.
    
    '''
    
    def __init__(self, query_type='SELECT *', conditions={}, model=None, db=None):
        from autumn.model import Model
        self.type = query_type
        self.conditions = conditions
        self.order = ''
        self.limit = ()
        self.cache = None
        if not issubclass(model, Model):
            raise Exception('Query objects must be created with a model class.')
        self.model = model
        if db:
            self.db = db
        elif model:
            self.db = model.db
        
    def __getitem__(self, k):
        if self.cache != None:
            return self.cache[k]
        
        if isinstance(k, (int, long)):
            self.limit = (k,1)
            lst = self.get_data()
            if not lst:
                return None
            return lst[0]
        elif isinstance(k, slice):
            if k.start is not None:
                assert k.stop is not None, "Limit must be set when an offset is present"
                assert k.stop >= k.start, "Limit must be greater than or equal to offset"
                self.limit = k.start, (k.stop - k.start)
            elif k.stop is not None:
                self.limit = 0, k.stop
        
        return self.get_data()
        
    def __len__(self):
        return len(self.get_data())
        
    def __iter__(self):
        return iter(self.get_data())
        
    def __repr__(self):
        return repr(self.get_data())
        
    def count(self):
        if self.cache is None:
            self.type = 'SELECT COUNT(*)'
            return self.execute_query().fetchone()[0]
        else:
            return len(self.cache)
        
    def filter(self, **kwargs):
        self.conditions.update(kwargs)
        return self
        
    def order_by(self, field, direction='ASC'):
        self.order = 'ORDER BY %s %s' % (escape(field), direction)
        return self
        
    def extract_condition_keys(self):
        if len(self.conditions):
            return 'WHERE %s' % ' AND '.join("%s=%s" % (escape(k), self.db.conn.placeholder) for k in self.conditions)
        
    def extract_condition_values(self):
        return list(self.conditions.itervalues())
        
    def query_template(self):
        return '%s FROM %s %s %s %s' % (
            self.type,
            self.model.Meta.table_safe,
            self.extract_condition_keys() or '',
            self.order,
            self.extract_limit() or '',
        )
        
    def extract_limit(self):
        if len(self.limit):
            return 'LIMIT %s' % ', '.join(str(l) for l in self.limit)
        
    def get_data(self):
        if self.cache is None:
            self.cache = list(self.iterator())
        return self.cache
        
    def iterator(self):        
        for row in self.execute_query().fetchall():
            obj = self.model(*row)
            obj._new_record = False
            yield obj
            
    def execute_query(self):
        values = self.extract_condition_values()
        return Query.raw_sql(self.query_template(), values, self.db)
        
    @classmethod
    def get_db(cls, db=None):
        if not db:
            db = getattr(cls, "db", autumn_db)
        return db
        
    @classmethod
    def get_cursor(cls, db=None):
        db = db or cls.get_db()
        return db.conn.connection.cursor()
        
    @classmethod
    def sql(cls, sql, values=(), db=None):
        db = db or cls.get_db()
        cursor = Query.raw_sql(sql, values, db)
        fields = [f[0] for f in cursor.description]
        return [dict(zip(fields, row)) for row in cursor.fetchall()]
            
    @classmethod
    def raw_sql(cls, sql, values=(), db=None):
        db = db or cls.get_db()
        cursor = cls.get_cursor(db)
        try:
            cursor.execute(sql, values)
            if db.b_commit:
                db.conn.connection.commit()
        except BaseException, ex:
            if db.b_debug:
                print "raw_sql: exception: ", ex
                print "sql:", sql
                print "values:", values
            raise
        return cursor

    @classmethod
    def raw_sqlscript(cls, sql, db=None):
        db = db or cls.get_db()
        cursor = cls.get_cursor(db)
        try:
            cursor.executescript(sql)
            if db.b_commit:
                db.conn.connection.commit()
        except BaseException, ex:
            if db.b_debug:
                print "raw_sqlscript: exception: ", ex
                print "sql:", sql
            raise
        return cursor



# begin() and commit() for SQL transaction control
# This has only been tested with SQLite3 with default isolation level.
# http://www.python.org/doc/2.5/lib/sqlite3-Controlling-Transactions.html

    @classmethod
    def begin(cls, db=None):
        """
        begin() and commit() let you explicitly specify an SQL transaction.
        Be sure to call commit() after you call begin().
        """
        db = db or cls.get_db()
        db.b_commit = False

    @classmethod
    def commit(cls, db=None):
        """
        begin() and commit() let you explicitly specify an SQL transaction.
        Be sure to call commit() after you call begin().
        """
        cursor = None
        try:
            db = db or cls.get_db()
            db.conn.connection.commit()
        finally:
            db.b_commit = True
        return cursor

########NEW FILE########
__FILENAME__ = relations
from autumn.db.query import Query
from autumn.model import cache

class Relation(object):
    
    def __init__(self, model, field=None):            
        self.model = model
        self.field = field
    
    def _set_up(self, instance, owner):
        if isinstance(self.model, basestring):
            self.model = cache.get(self.model)

class ForeignKey(Relation):
        
    def __get__(self, instance, owner):
        super(ForeignKey, self)._set_up(instance, owner)
        if not instance:
            return self.model
        if not self.field:
            self.field = '%s_id' % self.model.Meta.table
        conditions = {self.model.Meta.pk: getattr(instance, self.field)}
        return Query(model=self.model, conditions=conditions)[0]

class OneToMany(Relation):
    
    def __get__(self, instance, owner):
        super(OneToMany, self)._set_up(instance, owner)
        if not instance:
            return self.model
        if not self.field:
            self.field = '%s_id' % instance.Meta.table
        conditions = {self.field: getattr(instance, instance.Meta.pk)}
        return Query(model=self.model, conditions=conditions)
########NEW FILE########
__FILENAME__ = model
from autumn.db.query import Query
from autumn.db import escape
from autumn.db.connection import autumn_db, Database
from autumn.validators import ValidatorChain
    
class ModelCache(object):
    models = {}
    
    def add(self, model):
        self.models[model.__name__] = model
        
    def get(self, model_name):
        return self.models[model_name]
   
cache = ModelCache()
    
class Empty:
    pass

class ModelBase(type):
    '''
    Metaclass for Model
    
    Sets up default table name and primary key
    Adds fields from table as attributes
    Creates ValidatorChains as necessary
    
    '''
    def __new__(cls, name, bases, attrs):
        if name == 'Model':
            return super(ModelBase, cls).__new__(cls, name, bases, attrs)
            
        new_class = type.__new__(cls, name, bases, attrs)
        
        if not getattr(new_class, 'Meta', None):
            new_class.Meta = Empty
        
        if not getattr(new_class.Meta, 'table', None):
            new_class.Meta.table = name.lower()
        new_class.Meta.table_safe = escape(new_class.Meta.table)
        
        # Assume id is the default 
        if not getattr(new_class.Meta, 'pk', None):
            new_class.Meta.pk = 'id'
        
        # Create function to loop over iterable validations
        for k, v in getattr(new_class.Meta, 'validations', {}).iteritems():
            if isinstance(v, (list, tuple)):
                new_class.Meta.validations[k] = ValidatorChain(*v)
        
        # See cursor.description
        # http://www.python.org/dev/peps/pep-0249/
        if not hasattr(new_class, "db"):
            new_class.db = autumn_db
        db = new_class.db
        q = Query.raw_sql('SELECT * FROM %s LIMIT 1' % new_class.Meta.table_safe, db=new_class.db)
        new_class._fields = [f[0] for f in q.description]
        
        cache.add(new_class)
        return new_class

class Model(object):
    '''
    Allows for automatic attributes based on table columns.
    
    Syntax::
    
        from autumn.model import Model
        class MyModel(Model):
            class Meta:
                # If field is blank, this sets a default value on save
                defaults = {'field': 1}
            
                # Each validation must be callable
                # You may also place validations in a list or tuple which is
                # automatically converted int a ValidationChain
                validations = {'field': lambda v: v > 0}
            
                # Table name is lower-case model name by default
                # Or we can set the table name
                table = 'mytable'
        
        # Create new instance using args based on the order of columns
        m = MyModel(1, 'A string')
        
        # Or using kwargs
        m = MyModel(field=1, text='A string')
        
        # Saving inserts into the database (assuming it validates [see below])
        m.save()
        
        # Updating attributes
        m.field = 123
        
        # Updates database record
        m.save()
        
        # Deleting removes from the database 
        m.delete()
        
        # Purely saving with an improper value, checked against 
        # Model.Meta.validations[field_name] will raise Model.ValidationError
        m = MyModel(field=0)
        
        # 'ValidationError: Improper value "0" for "field"'
        m.save()
        
        # Or before saving we can check if it's valid
        if m.is_valid():
            m.save()
        else:
            # Do something to fix it here
        
        # Retrieval is simple using Model.get
        # Returns a Query object that can be sliced
        MyModel.get()
        
        # Returns a MyModel object with an id of 7
        m = MyModel.get(7)
        
        # Limits the query results using SQL's LIMIT clause
        # Returns a list of MyModel objects
        m = MyModel.get()[:5]   # LIMIT 0, 5
        m = MyModel.get()[10:15] # LIMIT 10, 5
        
        # We can get all objects by slicing, using list, or iterating
        m = MyModel.get()[:]
        m = list(MyModel.get())
        for m in MyModel.get():
            # do something here...
            
        # We can filter our Query
        m = MyModel.get(field=1)
        m = m.filter(another_field=2)
        
        # This is the same as
        m = MyModel.get(field=1, another_field=2)
        
        # Set the order by clause
        m = MyModel.get(field=1).order_by('field', 'DESC')
        # Removing the second argument defaults the order to ASC
        
    '''
    __metaclass__ = ModelBase
    
    debug = False

    def __init__(self, *args, **kwargs):
        'Allows setting of fields using kwargs'
        self.__dict__[self.Meta.pk] = None
        self._new_record = True
        [setattr(self, self._fields[i], arg) for i, arg in enumerate(args)]
        [setattr(self, k, v) for k, v in kwargs.iteritems()]
        self._changed = set()
        
    def __setattr__(self, name, value):
        'Records when fields have changed'
        if name != '_changed' and name in self._fields and hasattr(self, '_changed'):
            self._changed.add(name)
        self.__dict__[name] = value
        
    def _get_pk(self):
        'Sets the current value of the primary key'
        return getattr(self, self.Meta.pk, None)

    def _set_pk(self, value):
        'Sets the primary key'
        return setattr(self, self.Meta.pk, value)
        
    def _update(self):
        'Uses SQL UPDATE to update record'
        query = 'UPDATE %s SET ' % self.Meta.table_safe
        query += ', '.join(['%s = %s' % (escape(f), self.db.conn.placeholder) for f in self._changed])
        query += ' WHERE %s = %s ' % (escape(self.Meta.pk), self.db.conn.placeholder)
        
        values = [getattr(self, f) for f in self._changed]
        values.append(self._get_pk())
        
        cursor = Query.raw_sql(query, values, self.db)
        
    def _new_save(self):
        'Uses SQL INSERT to create new record'
        # if pk field is set, we want to insert it too
        # if pk field is None, we want to auto-create it from lastrowid
        auto_pk = 1 and (self._get_pk() is None) or 0
        fields=[
            escape(f) for f in self._fields 
            if f != self.Meta.pk or not auto_pk
        ]
        query = 'INSERT INTO %s (%s) VALUES (%s)' % (
               self.Meta.table_safe,
               ', '.join(fields),
               ', '.join([self.db.conn.placeholder] * len(fields) )
        )
        values = [getattr(self, f, None) for f in self._fields
               if f != self.Meta.pk or not auto_pk]
        cursor = Query.raw_sql(query, values, self.db)
       
        if self._get_pk() is None:
            self._set_pk(cursor.lastrowid)
        return True
        
    def _get_defaults(self):
        'Sets attribute defaults based on ``defaults`` dict'
        for k, v in getattr(self.Meta, 'defaults', {}).iteritems():
            if not getattr(self, k, None):
                if callable(v):
                    v = v()
                setattr(self, k, v)
        
    def delete(self):
        'Deletes record from database'
        query = 'DELETE FROM %s WHERE %s = %s' % (self.Meta.table_safe, self.Meta.pk, self.db.conn.placeholder)
        values = [getattr(self, self.Meta.pk)]
        Query.raw_sql(query, values, self.db)
        return True
        
    def is_valid(self):
        'Returns boolean on whether all ``validations`` pass'
        try:
            self._validate()
            return True
        except Model.ValidationError:
            return False
    
    def _validate(self):
        'Tests all ``validations``, raises ``Model.ValidationError``'
        for k, v in getattr(self.Meta, 'validations', {}).iteritems():
            assert callable(v), 'The validator must be callable'
            value = getattr(self, k)
            if not v(value):
                raise Model.ValidationError, 'Improper value "%s" for "%s"' % (value, k)
        
    def save(self):
        'Sets defaults, validates and inserts into or updates database'
        self._get_defaults()
        self._validate()
        if self._new_record:
            self._new_save()
            self._new_record = False
            return True
        else:
            return self._update()
            
    @classmethod
    def get(cls, _obj_pk=None, **kwargs):
        'Returns Query object'
        if _obj_pk is not None:
            return cls.get(**{cls.Meta.pk: _obj_pk})[0]

        return Query(model=cls, conditions=kwargs)
        
        
    class ValidationError(Exception):
        pass

########NEW FILE########
__FILENAME__ = models
from autumn.db.connection import autumn_db
from autumn.model import Model
from autumn.db.relations import ForeignKey, OneToMany
from autumn import validators
import datetime

#autumn_db.conn.connect('sqlite3', '/tmp/example.db')
autumn_db.conn.connect('mysql', user='root', db='autumn')
    
class Author(Model):
    books = OneToMany('Book')
    
    class Meta:
        defaults = {'bio': 'No bio available'}
        validations = {'first_name': validators.Length(),
                       'last_name': (validators.Length(), lambda x: x != 'BadGuy!')}
    
class Book(Model):
    author = ForeignKey(Author)
    
    class Meta:
        table = 'books'

########NEW FILE########
__FILENAME__ = run
#!/usr/bin/env python
import unittest
import datetime
from autumn.model import Model
from autumn.tests.models import Book, Author
from autumn.db.query import Query
from autumn.db import escape
from autumn import validators

class TestModels(unittest.TestCase):
        
    def testmodel(self):
        # Create tables
        
        ### MYSQL ###
        #
        # DROP TABLE IF EXISTS author;
        # CREATE TABLE author (
        #     id INT(11) NOT NULL auto_increment,
        #     first_name VARCHAR(40) NOT NULL,
        #     last_name VARCHAR(40) NOT NULL,
        #     bio TEXT,
        #     PRIMARY KEY (id)
        # );
        # DROP TABLE IF EXISTS books;
        # CREATE TABLE books (
        #     id INT(11) NOT NULL auto_increment,
        #     title VARCHAR(255),
        #     author_id INT(11),
        #     FOREIGN KEY (author_id) REFERENCES author(id),
        #     PRIMARY KEY (id)
        # );
        
        ### SQLITE ###
        #
        # DROP TABLE IF EXISTS author;
        # DROP TABLE IF EXISTS books;
        # CREATE TABLE author (
        #   id INTEGER PRIMARY KEY AUTOINCREMENT,
        #   first_name VARCHAR(40) NOT NULL,
        #   last_name VARCHAR(40) NOT NULL,
        #   bio TEXT
        # );
        # CREATE TABLE books (
        #   id INTEGER PRIMARY KEY AUTOINCREMENT,
        #   title VARCHAR(255),
        #   author_id INT(11),
        #   FOREIGN KEY (author_id) REFERENCES author(id)
        # );
        
        for table in ('author', 'books'):
            Query.raw_sql('DELETE FROM %s' % escape(table))
        
        # Test Creation
        james = Author(first_name='James', last_name='Joyce')
        james.save()
        
        kurt = Author(first_name='Kurt', last_name='Vonnegut')
        kurt.save()
        
        tom = Author(first_name='Tom', last_name='Robbins')
        tom.save()
        
        Book(title='Ulysses', author_id=james.id).save()
        Book(title='Slaughter-House Five', author_id=kurt.id).save()
        Book(title='Jitterbug Perfume', author_id=tom.id).save()
        slww = Book(title='Still Life with Woodpecker', author_id=tom.id)
        slww.save()
        
        # Test ForeignKey
        self.assertEqual(slww.author.first_name, 'Tom')
        
        # Test OneToMany
        self.assertEqual(len(list(tom.books)), 2)
        
        kid = kurt.id
        del(james, kurt, tom, slww)
        
        # Test retrieval
        b = Book.get(title='Ulysses')[0]
        
        a = Author.get(id=b.author_id)[0]
        self.assertEqual(a.id, b.author_id)
        
        a = Author.get(id=b.id)[:]
        self.assert_(isinstance(a, list))
        
        # Test update
        new_last_name = 'Vonnegut, Jr.'
        a = Author.get(id=kid)[0]
        a.last_name = new_last_name
        a.save()
        
        a = Author.get(kid)
        self.assertEqual(a.last_name, new_last_name)
        
        # Test count
        self.assertEqual(Author.get().count(), 3)
        
        self.assertEqual(len(Book.get()[1:4]), 3)
        
        # Test delete
        a.delete()
        self.assertEqual(Author.get().count(), 2)
        
        # Test validation
        a = Author(first_name='', last_name='Ted')
        try:
            a.save()
            raise Exception('Validation not caught')
        except Model.ValidationError:
            pass
        
        # Test defaults
        a.first_name = 'Bill and'
        a.save()
        self.assertEqual(a.bio, 'No bio available')
        
        try:
            Author(first_name='I am a', last_name='BadGuy!').save()
            raise Exception('Validation not caught')
        except Model.ValidationError:
            pass
            
    def testvalidators(self):
        ev = validators.Email()
        assert ev('test@example.com')
        assert not ev('adsf@.asdf.asdf')
        assert validators.Length()('a')
        assert not validators.Length(2)('a')
        assert validators.Length(max_length=10)('abcdegf')
        assert not validators.Length(max_length=3)('abcdegf')

        n = validators.Number(1, 5)
        assert n(2)
        assert not n(6)
        assert validators.Number(1)(100.0)
        assert not validators.Number()('rawr!')

        vc = validators.ValidatorChain(validators.Length(8), validators.Email())
        assert vc('test@example.com')
        assert not vc('a@a.com')
        assert not vc('asdfasdfasdfasdfasdf')
        
if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = util
# autumn.util.py


from threading import local as threading_local

# Autumn ORM
from autumn.model import Model
from autumn.db.relations import ForeignKey, OneToMany
from autumn.db.query import Query
from autumn.db.connection import Database


"""
Convenience functions for the Autumn ORM.
"""

def table_exists(db, table_name):
    """
    Given an Autumn model, check to see if its table exists.
    """
    try:
        s_sql = "SELECT * FROM %s LIMIT 1;" % table_name
        Query.raw_sql(s_sql, db=db)
    except Exception:
        return False

    # if no exception, the table exists and we are done
    return True


def create_table(db, s_create_sql):
    """
    Create a table for an Autumn class.
    """
    Query.begin(db=db)
    Query.raw_sqlscript(s_create_sql, db=db)
    Query.commit(db=db)


def create_table_if_needed(db, table_name, s_create_sql):
    """
    Check to see if an Autumn class has its table created; create if needed.
    """
    if not table_exists(db, table_name):
        create_table(db, s_create_sql)


class AutoConn(object):
    """
    A container that will automatically create a database connection object
    for each thread that accesses it.  Useful with SQLite, because the Python
    modules for SQLite require a different connection object for each thread.
    """
    def __init__(self, db_name, container=None):
        self.b_debug = False
        self.b_commit = True
        self.db_name = db_name
        self.container = threading_local()
    def __getattr__(self, name):
        try:
            if "conn" == name:
                return self.container.conn
        except BaseException:
            self.container.conn = Database()
            self.container.conn.connect('sqlite3', self.db_name)
            return self.container.conn
        raise AttributeError


# examples of usage:
#
# class FooClass(object):
#     db = autumn.util.AutoConn("foo.db")
#
# _create_sql = "_create_sql = """\
# DROP TABLE IF EXISTS bar;
# CREATE TABLE bar (
#     id INTEGER PRIMARY KEY,
#     value VARCHAR(128) NOT NULL,
#     UNIQUE (value));
# CREATE INDEX idx_bar0 ON bar (value);"""
#
# autumn.util.create_table_if_needed(FooClass.db, "bar", _create_sql)
#
# class Bar(FooClass, Model):
#    ...standard Autumn class stuff goes here...

########NEW FILE########
__FILENAME__ = validators
import re

class Validator(object):
    pass
        
class Regex(Validator):        
    def __call__(self, value):
        return bool(self.regex.match(value))
        
class Email(Regex):
    regex = re.compile(r'^[A-Z0-9._%+-]+@[A-Z0-9.-]+\.(?:[A-Z]{2}|com|org|net|gov|mil|biz|info|mobi|name|aero|jobs|museum)$', re.I)

class Length(Validator):
    def __init__(self, min_length=1, max_length=None):
        if max_length is not None:
            assert max_length >= min_length, "max_length must be greater than or equal to min_length"
        self.min_length = min_length
        self.max_length = max_length
        
    def __call__(self, string):
        l = len(str(string))
        return (l >= self.min_length) and \
               (self.max_length is None or l <= self.max_length)

class Number(Validator):
    def __init__(self, minimum=None, maximum=None):
        if None not in (minimum, maximum):
            assert maximum >= minimum, "maximum must be greater than or equal to minimum"
        self.minimum = minimum
        self.maximum = maximum
        
    def __call__(self, number):
        return isinstance(number, (int, long, float, complex)) and \
               (self.minimum is None or number >= self.minimum) and \
               (self.maximum is None or number <= self.maximum)
               
class ValidatorChain(object):
    def __init__(self, *validators):
        self.validators = validators
    
    def __call__(self, value):
        for validator in self.validators:
            if not validator(value): return False
        return True

########NEW FILE########
