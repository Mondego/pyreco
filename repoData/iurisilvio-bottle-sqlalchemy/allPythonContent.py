__FILENAME__ = bottle_sqlalchemy
'''
This bottle-sqlalchemy plugin integrates SQLAlchemy with your Bottle
application. It connects to a database at the beginning of a request,
passes the database handle to the route callback and closes the connection
afterwards.

The plugin inject an argument to all route callbacks that require a `db`
keyword.

Usage Example::

    import bottle
    from bottle import HTTPError
    from bottle.ext import sqlalchemy
    from sqlalchemy import create_engine, Column, Integer, Sequence, String
    from sqlalchemy.ext.declarative import declarative_base

    Base = declarative_base()
    engine = create_engine('sqlite:///:memory:', echo=True)

    app = bottle.Bottle()
    plugin = sqlalchemy.Plugin(engine, Base.metadata, create=True)
    app.install(plugin)

    class Entity(Base):
        __tablename__ = 'entity'
        id = Column(Integer, Sequence('id_seq'), primary_key=True)
        name = Column(String(50))

        def __init__(self, name):
            self.name = name

        def __repr__(self):
            return "<Entity('%d', '%s')>" % (self.id, self.name)


    @app.get('/:name')
    def show(name, db):
        entity = db.query(Entity).filter_by(name=name).first()
        if entity:
            return {'id': entity.id, 'name': entity.name}
        return HTTPError(404, 'Entity not found.')

    @app.put('/:name')
    def put_name(name, db):
        entity = Entity(name)
        db.add(entity)


It is up to you create engine and metadata, because SQLAlchemy has
a lot of options to do it. The plugin just handles the SQLAlchemy
session.

Copyright (c) 2011-2012, Iuri de Silvio
License: MIT (see LICENSE for details)
'''

import inspect

import bottle
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm.scoping import ScopedSession

# PluginError is defined to bottle >= 0.10
if not hasattr(bottle, 'PluginError'):
    class PluginError(bottle.BottleException):
        pass
    bottle.PluginError = PluginError

class SQLAlchemyPlugin(object):

    name = 'sqlalchemy'
    api = 2

    def __init__(self, engine, metadata=None,
                 keyword='db', commit=True, create=False, use_kwargs=False, create_session=None):
        '''
        :param engine: SQLAlchemy engine created with `create_engine` function
        :param metadata: SQLAlchemy metadata. It is required only if `create=True`
        :param keyword: Keyword used to inject session database in a route
        :param create: If it is true, execute `metadata.create_all(engine)`
               when plugin is applied
        :param commit: If it is true, commit changes after route is executed.
        :param use_kwargs: plugin inject session database even if it is not
               explicitly defined, using **kwargs argument if defined.
        :param create_session: SQLAlchemy session maker created with the 
                'sessionmaker' function. Will create its own if undefined.
        '''
        self.engine = engine
        if create_session is None:
            create_session = sessionmaker()
        self.create_session = create_session
        self.metadata = metadata
        self.keyword = keyword
        self.create = create
        self.commit = commit
        self.use_kwargs = use_kwargs

    def setup(self, app):
        ''' Make sure that other installed plugins don't affect the same
            keyword argument and check if metadata is available.'''
        for other in app.plugins:
            if not isinstance(other, SQLAlchemyPlugin):
                continue
            if other.keyword == self.keyword:
                raise bottle.PluginError("Found another SQLAlchemy plugin with "\
                                  "conflicting settings (non-unique keyword).")
            elif other.name == self.name:
                self.name += '_%s' % self.keyword
        if self.create and not self.metadata:
            raise bottle.PluginError('Define metadata value to create database.')
    
    def apply(self, callback, route):
        # hack to support bottle v0.9.x
        if bottle.__version__.startswith('0.9'):
            config = route['config']
            _callback = route['callback']
        else:
            config = route.config
            _callback = route.callback

        if "sqlalchemy" in config:  # support for configuration before `ConfigDict` namespaces
            g = lambda key, default: config.get('sqlalchemy', {}).get(key, default)
        else:
            g = lambda key, default: config.get('sqlalchemy.' + key, default)

        keyword = g('keyword', self.keyword)
        create = g('create', self.create)
        commit = g('commit', self.commit)
        use_kwargs = g('use_kwargs', self.use_kwargs)

        argspec = inspect.getargspec(_callback)
        if not ((use_kwargs and argspec.keywords) or keyword in argspec.args):
            return callback

        if create:
            self.metadata.create_all(self.engine)

        def wrapper(*args, **kwargs):
            kwargs[keyword] = session = self.create_session(bind=self.engine)
            try:
                rv = callback(*args, **kwargs)
                if commit:
                    session.commit()
            except (SQLAlchemyError, bottle.HTTPError):
                session.rollback()
                raise
            except bottle.HTTPResponse:
                if commit:
                    session.commit()
                raise
            finally:
                if isinstance(self.create_session, ScopedSession):
                    self.create_session.remove()
                else:
                    session.close()
            return rv

        return wrapper
    

Plugin = SQLAlchemyPlugin
########NEW FILE########
__FILENAME__ = basic
#!/usr/bin/python
import bottle
from bottle import route, redirect, put, delete
from bottle.ext.sqlalchemy import SQLAlchemyPlugin

from sqlalchemy import create_engine, Column, Integer, Sequence, String
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()
engine = create_engine('sqlite:///:memory:', echo=True)

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, Sequence('user_id_seq'), primary_key=True)
    name = Column(String(50))
    fullname = Column(String(50))
    password = Column(String(12))

    def __init__(self, name, fullname, password):
        self.name = name
        self.fullname = fullname
        self.password = password

    def __repr__(self):
        return "<User('%s','%s', '%s')>" % (self.name, self.fullname, self.password)


@route('/')
def listing(db):
    users = db.query(User)
    result = "".join(["<li>%s</li>" % user.name for user in users])
    return "<ul>%s</ul>" % result

@put('/:name')
def put_name(name, db):
    user = User(name, fullname=name, password=name)
    db.add(user)

# imports to delete_name function
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError
create_session = sessionmaker(bind=engine)

@delete('/:name')
def delete_name(name):
    ''' This function don't use the plugin. '''
    session = create_session()
    try:
        user = session.query(User).filter_by(name=name).first()
        session.delete(user)
        session.commit()
    except SQLAlchemyError, e:
        session.rollback()
        raise bottle.HTTPError(500, "Database Error", e)
    finally:
        session.close()


bottle.install(SQLAlchemyPlugin(engine, Base.metadata, create=True, create_session = create_session))

if __name__ == '__main__':
    bottle.debug(True)
    bottle.run(reloader=True)

########NEW FILE########
__FILENAME__ = test
import unittest

from sqlalchemy import create_engine, Column, Integer, Sequence
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm.session import Session

import bottle
from bottle.ext import sqlalchemy

Base = declarative_base()

def accept_only_kwargs(route):
    def wrapper(**kwargs):
        return route(**kwargs)
    return wrapper

class Entity(Base):
    __tablename__ = 'entity'
    id = Column(Integer, Sequence('id_seq'), primary_key=True)


class AnotherPlugin(object):
    def apply(self, callback, route):
        def wrapper(*args, **kwargs):
            return callback(param=1, *args, **kwargs)
        return wrapper


class SQLAlchemyPluginTest(unittest.TestCase):

    def setUp(self):
        self.engine = create_engine('sqlite:///:memory:')
        self.app = bottle.Bottle(catchall=False)

    def test_without_metadata(self):
        sqlalchemy.Plugin(self.engine, create=False)

    def test_without_metadata_create_table_raises(self):
        plugin = sqlalchemy.Plugin(self.engine, create=True)
        self.assertRaises(bottle.PluginError, self.app.install, plugin)

    def test_with_commit(self):
        @self.app.get('/')
        def test(db):
            entity = Entity()
            db.add(entity)
            self._db = db

        self._install_plugin(self.engine, Base.metadata, create=True)
        self._request_path('/')
        self.assertEqual(self._db.query(Entity).count(), 1)

    def test_with_keyword(self):
        @self.app.get('/')
        def test(db):
            self.assertTrue(isinstance(db, Session))

        self._install_plugin(self.engine)
        self._request_path('/')

    def test_without_keyword(self):
        @self.app.get('/', sqlalchemy=dict(use_kwargs=True))
        def test():
            pass

        @self.app.get('/2')
        @accept_only_kwargs
        def test(db):
            pass

        @self.app.get('/3', sqlalchemy=dict(use_kwargs=True))
        @accept_only_kwargs
        def test(db):
            pass

        self._install_plugin(self.engine)
        self._request_path('/')
        self.assertRaises(TypeError, self._request_path, '/2')
        self._request_path('/3')

    def test_install_conflicts(self):
        self._install_plugin(self.engine)
        self._install_plugin(self.engine, keyword='db2')

        @self.app.get('/')
        def test(db, db2):
            pass

        # I have two plugins working with different names
        self._request_path('/')

    def test_route_with_view(self):
        @self.app.get('/', apply=[accept_only_kwargs])
        def test(db):
            pass

        self.app.install(sqlalchemy.Plugin(self.engine, Base.metadata))
        self._request_path('/')

    def test_route_based_keyword_config(self):
        @self.app.get('/', sqlalchemy=dict(keyword='db_keyword'))
        def test(db_keyword):
            pass

        self._install_plugin(self.engine, create=False)
        self._request_path('/')

    def test_route_based_commit_config(self):
        @self.app.get('/', sqlalchemy=dict(commit=False))
        def test(db):
            entity = Entity()
            db.add(entity)
            self._db = db

        self._install_plugin(self.engine, Base.metadata, create=True)
        self._request_path('/')
        self.assertEqual(self._db.query(Entity).count(), 0)

    def test_route_based_create_config(self):
        @self.app.get('/', sqlalchemy=dict(create=True))
        def test(db):
            entity = Entity()
            db.add(entity)

        self._install_plugin(self.engine, Base.metadata, create=False)
        self._request_path('/')

    def test_commit_on_redirect(self):
        @self.app.get('/')
        def test(db):
            entity = Entity()
            db.add(entity)
            self._db = db
            bottle.redirect('/')

        self._install_plugin(self.engine, Base.metadata, create=True)
        self._request_path('/')
        self.assertEqual(self._db.query(Entity).count(), 1)

    def test_commit_on_abort(self):
        @self.app.get('/')
        def test(db):
            entity = Entity()
            db.add(entity)
            self._db = db
            bottle.abort()

        self._install_plugin(self.engine, Base.metadata, create=True)
        self._request_path('/')
        self.assertEqual(self._db.query(Entity).count(), 0)

    def test_install_other_plugin_after(self):
        self._install_plugin(self.engine)
        self.app.install(AnotherPlugin())

        @self.app.get('/')
        def test(db, param):
            self.assertTrue(db is not None)
            self.assertEqual(param, 1)

        self._request_path('/')

    def test_install_other_plugin_before(self):
        self.app.install(AnotherPlugin())
        self._install_plugin(self.engine)

        @self.app.get('/')
        def test(db, param):
            self.assertTrue(db is not None)
            self.assertEqual(param, 1)

        self._request_path('/')

    def _request_path(self, path, method='GET'):
        self.app({'PATH_INFO': path, 'REQUEST_METHOD': method},
            lambda x, y: None)

    def _install_plugin(self, *args, **kwargs):
        self.app.install(sqlalchemy.Plugin(*args, **kwargs))


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
