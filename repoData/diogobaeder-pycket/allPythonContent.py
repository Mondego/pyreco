__FILENAME__ = pycketdemo
"""
Cyclone Redis Demo

This demonstrates integrating pycket with cyclone, using a redis
backend (but easily switched to using memcached).

"""

import sys

import cyclone.auth
import cyclone.escape
import cyclone.web

from twisted.python import log
from twisted.internet import reactor
from pycket.session import SessionMixin


class Application(cyclone.web.Application):
    def __init__(self):
        handlers = [
            (r"/", MainHandler),
            (r"/auth/login", AuthHandler),
            (r"/auth/logout", LogoutHandler),
        ]
        settings = dict(
            cookie_secret="32oETzKXQAGaYdkL5gEmGeJJFuYh7EQnp2XdTP1o/Vo=",
            debug=True,
            login_url="/auth/login",
            logout_url="/auth/logout",
        )

        settings['pycket'] = {
            'engine': 'redis',
            'storage': {
                'host': 'localhost',
                'port': 6379,
                'db_sessions': 10,
                'db_notifications': 11
            }
        }

        cyclone.web.Application.__init__(self, handlers, **settings)


class BaseHandler(cyclone.web.RequestHandler, SessionMixin):
    def get_current_user(self):
        user = self.session.get('user')
        if not user:
            return None
        return user


class MainHandler(BaseHandler):
    @cyclone.web.authenticated
    def get(self):
        name = cyclone.escape.xhtml_escape(self.current_user)
        self.write("Hello, " + name)
        self.write("<br><br><a href=\"/auth/logout\">Log out</a>")


class AuthHandler(BaseHandler, SessionMixin):

    def get(self):
        self.write('<form method="post">'
                   'Enter your username: <input name="username" type="text">'
                   '<button type="submit" class="btn">Login</button></form>')

    def post(self):
        username = self.get_argument('username')
        if not username:
            self.write('<form method="post">Enter your username: '
                       '<input name="username" type="text">'
                       '<button type="submit" class="btn">Login</button>'
                       '</form>')
        else:
            self.session.set('user', username)
            self.redirect('/')


class LogoutHandler(BaseHandler, SessionMixin):
    def get(self):
        self.session.delete('user')
        self.redirect("/")


def main():
    log.startLogging(sys.stdout)
    reactor.listenTCP(8888, Application(), interface="127.0.0.1")
    reactor.run()


if __name__ == "__main__":
    main()

########NEW FILE########
__FILENAME__ = driver
'''
This module is for internal use, only. It contains datastore drivers to be used
with the session and notification managers.
'''
from copy import copy
import pickle


class Driver(object):
    EXPIRE_SECONDS = 24 * 60 * 60

    client = None

    def _to_dict(self, raw_session):
        if raw_session is None:
            return {}
        else:
            return pickle.loads(raw_session)

    def _setup_client(self):
        if self.client is None:
            self._create_client()

    def get(self, session_id):
        self._setup_client()
        raw_session = self.client.get(session_id)

        return self._to_dict(raw_session)

    def set(self, session_id, session):
        pickled_session = pickle.dumps(session)
        self._setup_client()

        self._set_and_expire(session_id, pickled_session)


class RedisDriver(Driver):
    DEFAULT_STORAGE_IDENTIFIERS = {
        'db_sessions': 0,
        'db_notifications': 1,
    }

    def __init__(self, settings):
        self.settings = settings

    def _set_and_expire(self, session_id, pickled_session):
        self.client.set(session_id, pickled_session)
        self.client.expire(session_id, self.EXPIRE_SECONDS)

    def _create_client(self):
        import redis
        if 'max_connections' in self.settings:
            connection_pool = redis.ConnectionPool(**self.settings)
            settings = copy(self.settings)
            del settings['max_connections']
            settings['connection_pool'] = connection_pool
        else:
            settings = self.settings
        self.client = redis.Redis(**settings)


class MemcachedDriver(Driver):
    def __init__(self, settings):
        self.settings = settings

    def _set_and_expire(self, session_id, pickled_session):
        self.client.set(session_id, pickled_session, self.EXPIRE_SECONDS)

    def _create_client(self):
        import memcache
        settings = copy(self.settings)
        default_servers = ('localhost:11211',)
        servers = settings.pop('servers', default_servers)
        self.client = memcache.Client(servers, **settings)


class DriverFactory(object):
    STORAGE_CATEGORIES = ('db_sessions', 'db_notifications')

    def create(self, name, storage_settings, storage_category):
        method = getattr(self, '_create_%s' % name, None)
        if method is None:
            raise ValueError('Engine "%s" is not supported' % name)
        return method(storage_settings, storage_category)

    def _create_redis(self, storage_settings, storage_category):
        storage_settings = copy(storage_settings)
        default_storage_identifier = RedisDriver.DEFAULT_STORAGE_IDENTIFIERS[storage_category]
        storage_settings['db'] = storage_settings.get(storage_category, default_storage_identifier)
        for storage_category in self.STORAGE_CATEGORIES:
            if storage_category in storage_settings.keys():
                del storage_settings[storage_category]

        return RedisDriver(storage_settings)

    def _create_memcached(self, storage_settings, storage_category):
        return MemcachedDriver(storage_settings)

########NEW FILE########
__FILENAME__ = notification
'''
This module is the same as the sessions module, except that:
1. NotificationMixin sets a "notifications" property instead a "session" one,
and that the NotificationManager ("notifications") gets an object only once, and
deletes it from the database after retrieving;
2. The objects are stored in db 1 (for default) instead of 0 to avoid conflicts
with sessions. (You can change this setting with the "db_notifications" setting
in the "storage" setting.)
'''

from pycket.session import create_mixin, SessionManager


class NotificationManager(SessionManager):
    STORAGE_CATEGORY = 'db_notifications'

    def get(self, name, default=None):
        '''
        Retrieves the object with "name", like with SessionManager.get(), but
        removes the object from the database after retrieval, so that it can be
        retrieved only once
        '''

        session_object = super(NotificationManager, self).get(name, default)
        if session_object is not None:
            self.delete(name)
        return session_object


class NotificationMixin(object):
    @property
    def notifications(self):
        '''
        Returns a NotificationManager instance
        '''

        return create_mixin(self, '__notification_manager', NotificationManager)

########NEW FILE########
__FILENAME__ = session
'''
This module contains SessionMixin, which can be used in RequestHandlers, and
SessionManager, which is the real session manager, and is referenced by the
SessionMixin.

It's mandatory that you set the "cookie_secret" in your application settings,
because the session ID is stored in a secure manner. It's also mandatory that
you have a "pycket" dictionary containing at least an "engine" element that
tells which engine you want to use.

Supported engines, for now, are:
- Redis
- Memcache

If you want to change the settings that are passed to the storage client, set a
"storage" dictionary in the "pycket" settings with the intended storage settings
in your Tornado application settings. When you're using Redis, all these
settings are passed to the redis.Redis client, except for the "db_sessions" and
"db_notifications". These settings can contain numbers to change the datasets
used for persistence, if you don't want to use the default numbers.

If you want to change the cookie settings passed to the handler, set a
"cookies" setting in the "pycket" settings with the items you want.
This is also valid for "expires" and "expires_days", which, by default, will be
None, therefore making the sessions expire on browser close, but, if you set one
of them, your custom value will override the default behaviour.
'''

from uuid import uuid4

from pycket.driver import DriverFactory


class SessionManager(object):
    '''
    This is the real class that manages sessions. All session objects are
    persisted in a Redis or Memcache store (depending on your settings).
    After 1 day without changing a session, it's purged from the datastore,
    to avoid it to grow out-of-control.

    When a session is started, a cookie named 'PYCKET_ID' is set, containing the
    encrypted session id of the user. By default, it's cleaned every time the
    user closes the browser.

    The recommendation is to use the manager instance that comes with the
    SessionMixin (using the "session" property of the handler instance), but it
    can be instantiated ad-hoc.
    '''

    SESSION_ID_NAME = 'PYCKET_ID'
    STORAGE_CATEGORY = 'db_sessions'

    driver = None

    def __init__(self, handler):
        '''
        Expects a tornado.web.RequestHandler
        '''

        self.handler = handler
        self.settings = {}
        self.__setup_driver()

    def __setup_driver(self):
        self.__setup_settings()
        storage_settings = self.settings.get('storage', {})
        factory = DriverFactory()
        self.driver = factory.create(self.settings.get('engine'), storage_settings, self.STORAGE_CATEGORY)

    def __setup_settings(self):
        pycket_settings = self.handler.settings.get('pycket')
        if not pycket_settings:
            raise ConfigurationError('The "pycket" configurations are missing')
        engine = pycket_settings.get('engine')
        if not engine:
            raise ConfigurationError('You must define an engine to be used with pycket')
        self.settings = pycket_settings

    def set(self, name, value):
        '''
        Sets a value for "name". It may be any pickable (see "pickle" module
        documentation) object.
        '''

        def change(session):
            session[name] = value
        self.__change_session(change)

    def get(self, name, default=None):
        '''
        Gets the object for "name", or None if there's no such object. If
        "default" is provided, return it if no object is found.
        '''

        session = self.__get_session_from_db()

        return session.get(name, default)

    def delete(self, *names):
        '''
        Deletes the object with "name" from the session, if exists.
        '''

        def change(session):
            keys = session.keys()
            names_in_common = [name for name in names if name in keys]
            for name in names_in_common:
                del session[name]
        self.__change_session(change)
    __delitem__ = delete

    def keys(self):
        session = self.__get_session_from_db()
        return session.keys()

    def iterkeys(self):
        session = self.__get_session_from_db()
        return iter(session)
    __iter__ = iterkeys

    def __getitem__(self, key):
        value = self.get(key)
        if value is None:
            raise KeyError('%s not found in session' % key)
        return value

    def __setitem__(self, key, value):
        self.set(key, value)

    def __contains__(self, key):
        session = self.__get_session_from_db()
        return key in session

    def __set_session_in_db(self, session):
        session_id = self.__get_session_id()
        self.driver.set(session_id, session)

    def __get_session_from_db(self):
        session_id = self.__get_session_id()
        return self.driver.get(session_id)

    def __get_session_id(self):
        session_id = self.handler.get_secure_cookie(self.SESSION_ID_NAME)
        if session_id is None:
            session_id = self.__create_session_id()
        return session_id

    def __create_session_id(self):
        session_id = str(uuid4())
        self.handler.set_secure_cookie(self.SESSION_ID_NAME, session_id,
                                       **self.__cookie_settings())
        return session_id

    def __change_session(self, callback):
        session = self.__get_session_from_db()

        callback(session)
        self.__set_session_in_db(session)

    def __cookie_settings(self):
        cookie_settings = self.settings.get('cookies', {})
        cookie_settings.setdefault('expires', None)
        cookie_settings.setdefault('expires_days', None)
        return cookie_settings


class SessionMixin(object):
    '''
    This mixin must be included in the request handler inheritance list, so that
    the handler can support sessions.

    Example:
    >>> class MyHandler(tornado.web.RequestHandler, SessionMixin):
    ...    def get(self):
    ...        print type(self.session) # SessionManager

    Refer to SessionManager documentation in order to know which methods are
    available.
    '''

    @property
    def session(self):
        '''
        Returns a SessionManager instance
        '''

        return create_mixin(self, '__session_manager', SessionManager)


class ConfigurationError(Exception):
    pass


def create_mixin(context, manager_property, manager_class):
    if not hasattr(context, manager_property):
        setattr(context, manager_property, manager_class(context))
    return getattr(context, manager_property)

########NEW FILE########
__FILENAME__ = test_driver
import pickle
from unittest import TestCase

from nose.tools import istest, raises
import redis

from pycket.driver import DriverFactory, MemcachedDriver, RedisDriver


class RedisTestCase(TestCase):
    client = None

    def setUp(self):
        if self.client is None:
            self.client = redis.Redis(db=0)
        self.client.flushall()


class RedisDriverTest(RedisTestCase):
    @istest
    def inserts_pickable_object_into_session(self):
        driver = RedisDriver(dict(db=0))

        foo = dict(foo='bar')

        driver.set('session-id', foo)

        result = self.client.get('session-id')

        self.assertEqual(pickle.loads(result), foo)

    @istest
    def retrieves_a_pickled_object_from_session(self):
        driver = RedisDriver(dict(db=0))

        foo = dict(foo='bar')

        self.client.set('session-id', pickle.dumps(foo))

        result = driver.get('session-id')

        self.assertEqual(result, foo)

    @istest
    def makes_session_expire_in_one_day_in_the_client(self):
        driver = RedisDriver(dict(db=0))

        foo = dict(foo='bar')

        test_case = self

        class StubClient(object):
            def set(self, session_id, pickled_session):
                pass

            def expire(self, session_id, expiration):
                test_case.assertEqual(expiration, RedisDriver.EXPIRE_SECONDS)

        driver.client = StubClient()

        driver.set('session-id', foo)

    @istest
    def starts_with_1_day_to_expire_in_database(self):
        driver = RedisDriver(dict(db=0))

        one_day = 24 * 60 * 60

        self.assertEqual(driver.EXPIRE_SECONDS, one_day)

    @istest
    def starts_with_max_connections(self):
        driver = RedisDriver(dict(db=0, max_connections=123))
        driver.get('some session')

        self.assertEqual(driver.client.connection_pool.max_connections, 123)


class MemcachedTestCase(TestCase):
    client = None

    def setUp(self):
        if self.client is None:
            import memcache
            self.client = memcache.Client(servers=('localhost:11211',))
        self.client.flush_all()


class MemcachedDriverTest(MemcachedTestCase):
    @istest
    def inserts_pickable_object_into_session(self):
        driver = MemcachedDriver({
            'servers': ('localhost:11211',)
        })

        foo = dict(foo='bar')

        driver.set('session-id', foo)

        result = self.client.get('session-id')

        self.assertEqual(pickle.loads(result), foo)

    @istest
    def retrieves_a_pickled_object_from_session(self):
        driver = MemcachedDriver({
            'servers': ('localhost:11211',)
        })

        foo = dict(foo='bar')

        self.client.set('session-id', pickle.dumps(foo))

        result = driver.get('session-id')

        self.assertEqual(result, foo)

    @istest
    def makes_session_expire_in_one_day_in_the_client(self):
        driver = MemcachedDriver({
            'servers': ('localhost:11211',)
        })

        foo = dict(foo='bar')

        test_case = self

        class StubClient(object):
            def set(self, session_id, pickled_session, expiration):
                test_case.assertEqual(expiration, MemcachedDriver.EXPIRE_SECONDS)

        driver.client = StubClient()

        driver.set('session-id', foo)

    @istest
    @raises(OverflowError)
    def fails_to_load_if_storage_settings_contain_wrong_host(self):
        driver = MemcachedDriver({
            'servers': ('255.255.255.255:99999',)
        })

        driver.set('session-id', 'foo')

    @istest
    def starts_with_1_day_to_expire_in_database(self):
        driver = MemcachedDriver({
            'servers': ('localhost:11211',)
        })

        one_day = 24 * 60 * 60

        self.assertEqual(driver.EXPIRE_SECONDS, one_day)


class DriverFactoryTest(TestCase):
    @istest
    def creates_instance_for_redis_session(self):
        factory = DriverFactory()

        instance = factory.create('redis', storage_settings={}, storage_category='db_sessions')

        self.assertIsInstance(instance, RedisDriver)

        instance.get('client-is-lazy-loaded')

        self.assertEqual(instance.client.connection_pool._available_connections[0].db, 0)

    @istest
    def creates_instance_for_memcached_session(self):
        factory = DriverFactory()

        instance = factory.create('memcached', storage_settings={}, storage_category='db_sessions')

        self.assertIsInstance(instance, MemcachedDriver)

        instance.get('client-is-lazy-loaded')

        self.assertIsNotNone(instance.client.get_stats())

    @istest
    @raises(ValueError)
    def cannot_create_a_driver_for_not_supported_engine(self):
        factory = DriverFactory()

        factory.create('cassete-tape', storage_settings={}, storage_category='db_sessions')

########NEW FILE########
__FILENAME__ = test_functional
import pickle

from nose.tools import istest
import redis
from tornado.testing import AsyncHTTPTestCase
from tornado.web import Application, RequestHandler

from pycket.driver import RedisDriver
from pycket.notification import NotificationMixin
from pycket.session import SessionMixin


class FunctionalTest(AsyncHTTPTestCase):
    session_dataset = None
    notification_dataset = None

    def setUp(self):
        super(FunctionalTest, self).setUp()
        self.session_dataset.flushall()
        self.notification_dataset.flushall()

    def get_app(self):
        if self.session_dataset is None or self.notification_dataset is None:
            self.session_dataset = redis.Redis(db=RedisDriver.DEFAULT_STORAGE_IDENTIFIERS['db_sessions'])
            self.notification_dataset = redis.Redis(db=RedisDriver.DEFAULT_STORAGE_IDENTIFIERS['db_notifications'])

        class SimpleHandler(RequestHandler, SessionMixin, NotificationMixin):
            def get(self):
                self.session.set('foo', 'bar')
                self.notifications.set('foo', 'bar2')
                self.write('%s-%s' % (self.session.get('foo'), self.notifications.get('foo')))

            def get_secure_cookie(self, *args, **kwargs):
                return 'some-generated-cookie'

        return Application([
            (r'/', SimpleHandler),
        ], **{
            'cookie_secret': 'Python rocks!',
            'pycket': {
                'engine': 'redis',
                'storage': {
                    'max_connections': 10,
                },
            }
        })

    @istest
    def works_with_request_handlers(self):
        self.assertEqual(len(self.session_dataset.keys()), 0)

        response = self.fetch('/')

        self.assertEqual(response.code, 200)
        self.assertIn('bar-bar2', str(response.body))

        session_data = pickle.loads(self.session_dataset['some-generated-cookie'])
        notification_data = pickle.loads(self.notification_dataset['some-generated-cookie'])
        self.assertEqual(session_data, {'foo': 'bar'})
        self.assertEqual(notification_data, {})

########NEW FILE########
__FILENAME__ = test_notification
import pickle
from unittest import TestCase

from nose.tools import istest
import redis

from pycket.driver import RedisDriver
from pycket.session import SessionMixin
from pycket.notification import NotificationManager, NotificationMixin


class RedisTestCase(TestCase):
    client = None

    def setUp(self):
        if self.client is None:
            self.client = redis.Redis(db=RedisDriver.DEFAULT_STORAGE_IDENTIFIERS['db_notifications'])
        self.client.flushall()


class NotificationMixinTest(TestCase):
    @istest
    def starts_handler_with_session_manager(self):
        class StubHandler(NotificationMixin):
            settings = {
                'pycket': {
                    'engine': 'redis',
                }
            }

        self.assertIsInstance(StubHandler().notifications, NotificationManager)


class NotificationManagerTest(RedisTestCase):
    @istest
    def persists_in_a_different_name_from_session_manager(self):
        self.assertNotEqual(RedisDriver.DEFAULT_STORAGE_IDENTIFIERS['db_notifications'], RedisDriver.DEFAULT_STORAGE_IDENTIFIERS['db_sessions'])

    @istest
    def gets_a_notification_only_once(self):
        handler = StubHandler()
        manager = NotificationManager(handler)

        manager.set('foo', 'bar')

        self.assertEqual(manager.get('foo'), 'bar')
        self.assertIsNone(manager.get('foo'))

    @istest
    def removes_notification_from_database_after_retrieval(self):
        handler = StubHandler()
        manager = NotificationManager(handler)

        manager.set('foo', 'bar')

        raw_notifications = self.client.get(handler.session_id)
        notifications = pickle.loads(raw_notifications)

        self.assertEqual(list(notifications.keys()), ['foo'])

        manager.get('foo')

        raw_notifications = self.client.get(handler.session_id)
        notifications = pickle.loads(raw_notifications)

        self.assertEqual(list(notifications.keys()), [])

    @istest
    def gets_default_value_if_provided_and_not_in_client(self):
        handler = StubHandler()
        manager = NotificationManager(handler)

        value = manager.get('foo', 'Default')

        self.assertEqual(value, 'Default')

    @istest
    def sets_object_with_dict_key(self):
        handler = StubHandler()
        manager = NotificationManager(handler)

        manager['foo'] = 'bar'

        self.assertEqual(manager['foo'], 'bar')

    @istest
    def doesnt_conflict_with_sessions(self):
        test_case = self

        class StubHandler(SessionMixin, NotificationMixin):
            session_id = 'session-id'
            settings = {
                'pycket': {
                    'engine': 'redis',
                }
            }

            def get_secure_cookie(self, name):
                return self.session_id

            def test(self):
                self.session.set('foo', 'foo-session')
                self.notifications.set('foo', 'foo-notification')

                test_case.assertEqual(self.session.get('foo'), 'foo-session')
                test_case.assertEqual(self.notifications.get('foo'), 'foo-notification')
                test_case.assertIsNone(self.notifications.get('foo'))

        handler = StubHandler()

        handler.test()

    @istest
    def uses_custom_notifications_database_if_provided(self):
        handler = StubHandler()
        handler.settings = {
            'pycket': {
                'engine': 'redis',
                'storage': {
                    'db_sessions': 10,
                    'db_notifications': 11,
                }
            }
        }
        manager = NotificationManager(handler)
        manager.set('foo', 'bar')
        self.assertEqual(manager.driver.client.connection_pool._available_connections[0].db, 11)


class StubHandler(object):
    session_id = 'session-id'

    def __init__(self, settings=None):
        default_settings = {
            'pycket': {
                'engine': 'redis',
            }
        }
        self.settings = settings if settings is not None else default_settings

    def get_secure_cookie(self, name):
        return self.session_id

########NEW FILE########
__FILENAME__ = test_session
import pickle
import time
from unittest import skipIf, TestCase

from nose.tools import istest, raises
import redis

from pycket.driver import MemcachedDriver, RedisDriver
from pycket.session import ConfigurationError, SessionManager, SessionMixin


skip_slow_tests = False


class SessionMixinTest(TestCase):
    @istest
    def starts_handler_with_session_manager(self):
        class StubHandler(SessionMixin):
            settings = {
                'pycket': {
                    'engine': 'redis',
                }
            }

        self.assertIsInstance(StubHandler().session, SessionManager)

    @istest
    @raises(ConfigurationError)
    def cannot_start_driver_without_pycket_settings(self):
        class StubHandler(SessionMixin):
            settings = {}

        StubHandler().session.get('something')

    @istest
    @raises(ConfigurationError)
    def cannot_start_driver_without_pycket_engine(self):
        class StubHandler(SessionMixin):
            settings = {
                'pycket': {
                    'not-an-engine': 'something-useless',
                }
            }

        StubHandler().session.get('something')

    @istest
    def creates_session_for_redis(self):
        class StubHandler(SessionMixin):
            settings = {
                'pycket': {
                    'engine': 'redis',
                }
            }

        self.assertIsInstance(StubHandler().session.driver, RedisDriver)

    @istest
    def creates_session_for_memcached(self):
        class StubHandler(SessionMixin):
            settings = {
                'pycket': {
                    'engine': 'memcached',
                }
            }

        self.assertIsInstance(StubHandler().session.driver, MemcachedDriver)


class RedisTestCase(TestCase):
    client = None

    def setUp(self):
        if self.client is None:
            self.client = redis.Redis(db=RedisDriver.DEFAULT_STORAGE_IDENTIFIERS['db_sessions'])
        self.client.flushall()


class SessionManagerTest(RedisTestCase):
    @istest
    def sets_session_id_on_cookies(self):
        test_case = self

        class StubHandler(SessionMixin):
            settings = {
                'pycket': {
                    'engine': 'redis',
                }
            }

            def get_secure_cookie(self, name):
                test_case.assertEqual(name, 'PYCKET_ID')
                self.cookie_set = True
                return None

            def set_secure_cookie(self, name, value, expires_days, expires):
                test_case.assertEqual(name, 'PYCKET_ID')
                test_case.assertIsInstance(value, str)
                test_case.assertGreater(len(value), 0)
                self.cookie_retrieved = True

        handler = StubHandler()
        session_manager = SessionManager(handler)
        session_manager.set('some-object', 'Some object')

        self.assertTrue(handler.cookie_retrieved)
        self.assertTrue(handler.cookie_set)

    @istest
    def does_not_set_session_id_if_already_exists(self):
        class StubHandler(SessionMixin):
            settings = {
                'pycket': {
                    'engine': 'redis',
                }
            }

            def get_secure_cookie(self, name):
                self.cookie_retrieved = True
                return 'some-id'

        handler = StubHandler()
        manager = SessionManager(handler)
        manager.set('some-object', 'Some object')

        self.assertTrue(handler.cookie_retrieved)

    @istest
    def saves_session_object_on_redis_with_same_session_id_as_cookie(self):
        handler = StubHandler()
        manager = SessionManager(handler)

        manager.set('some-object', {'foo': 'bar'})

        raw_session = self.client.get(handler.session_id)
        session = pickle.loads(raw_session)

        self.assertEqual(session['some-object']['foo'], 'bar')

    @istest
    def retrieves_session_with_same_data_as_saved(self):
        handler = StubHandler()
        manager = SessionManager(handler)

        manager.set('some-object', {'foo': 'bar'})

        self.assertEqual(manager.get('some-object')['foo'], 'bar')

    @istest
    def keeps_previous_items_when_setting_new_ones(self):
        handler = StubHandler()
        manager = SessionManager(handler)

        manager.set('some-object', {'foo': 'bar'})
        manager.set('some-object2', {'foo2': 'bar2'})

        self.assertEqual(manager.get('some-object')['foo'], 'bar')
        self.assertEqual(manager.get('some-object2')['foo2'], 'bar2')

    @istest
    def retrieves_none_if_session_object_not_previously_set(self):
        handler = StubHandler()
        manager = SessionManager(handler)

        self.assertIsNone(manager.get('unexistant-object'))

    @istest
    def deletes_objects_from_session(self):
        handler = StubHandler()
        manager = SessionManager(handler)

        manager.set('some-object', {'foo': 'bar'})
        manager.set('some-object2', {'foo2': 'bar2'})
        manager.delete('some-object')

        raw_session = self.client.get(handler.session_id)
        session = pickle.loads(raw_session)

        self.assertEqual(list(session.keys()), ['some-object2'])

    @istest
    @skipIf(skip_slow_tests, 'This test is too slow')
    def still_retrieves_object_if_not_passed_from_expiration(self):
        handler = StubHandler()
        manager = SessionManager(handler)

        manager.set('foo', 'bar')

        time.sleep(1)

        self.assertEqual(manager.get('foo'), 'bar')

    @istest
    @skipIf(skip_slow_tests, 'This test is too slow')
    def cannot_retrieve_object_if_passed_from_expiration(self):
        handler = StubHandler()
        manager = SessionManager(handler)
        manager.driver.EXPIRE_SECONDS = 1

        manager.set('foo', 'bar')

        time.sleep(manager.driver.EXPIRE_SECONDS + 1)

        self.assertIsNone(manager.get('foo'))

    @istest
    def retrieves_object_with_dict_key(self):
        handler = StubHandler()
        manager = SessionManager(handler)

        manager.set('foo', 'bar')

        self.assertEqual(manager['foo'], 'bar')

    @istest
    @raises(KeyError)
    def raises_key_error_if_object_doesnt_exist(self):
        handler = StubHandler()
        manager = SessionManager(handler)

        manager['foo']

    @istest
    def sets_object_with_dict_key(self):
        handler = StubHandler()
        manager = SessionManager(handler)

        manager['foo'] = 'bar'

        self.assertEqual(manager['foo'], 'bar')

    @istest
    def gets_default_value_if_provided_and_not_in_client(self):
        handler = StubHandler()
        manager = SessionManager(handler)

        value = manager.get('foo', 'Default')

        self.assertEqual(value, 'Default')

    @istest
    def sets_session_id_to_last_a_browser_session_as_default(self):
        test_case = self

        class StubHandler(SessionMixin):
            settings = {
                'pycket': {
                    'engine': 'redis',
                }
            }

            def get_secure_cookie(self, name):
                return None

            def set_secure_cookie(self, name, value, expires_days, expires):
                test_case.assertIsNone(expires_days)
                test_case.assertIsNone(expires)

        handler = StubHandler()
        manager = SessionManager(handler)
        manager.set('some-object', 'Some object')

    @istest
    def repasses_cookies_options(self):
        test_case = self

        class StubHandler(SessionMixin):
            settings = {
                'pycket': {
                    'engine': 'redis',
                    'cookies': {
                        'foo': 'bar',
                    }
                },
            }

            def get_secure_cookie(self, name):
                return None

            def set_secure_cookie(self, *args, **kwargs):
                test_case.assertEqual(kwargs['foo'], 'bar')

        handler = StubHandler()
        manager = SessionManager(handler)
        manager.set('some-object', 'Some object')

    @istest
    def uses_custom_expires_if_provided(self):
        test_case = self

        class StubHandler(SessionMixin):
            settings = {
                'pycket': {
                    'engine': 'redis',
                    'cookies': {
                        'expires': 'St. Neversday',
                    }
                },
            }

            def get_secure_cookie(self, name):
                return None

            def set_secure_cookie(self, *args, **kwargs):
                test_case.assertEqual(kwargs['expires'], 'St. Neversday')

        handler = StubHandler()
        manager = SessionManager(handler)
        manager.set('some-object', 'Some object')

    @istest
    def uses_custom_expires_days_if_provided(self):
        test_case = self

        class StubHandler(SessionMixin):
            settings = {
                'pycket': {
                    'engine': 'redis',
                    'cookies': {
                        'expires_days': 'St. Neversday',
                    }
                },
            }

            def get_secure_cookie(self, name):
                return None

            def set_secure_cookie(self, *args, **kwargs):
                test_case.assertEqual(kwargs['expires_days'], 'St. Neversday')

        handler = StubHandler()
        manager = SessionManager(handler)
        manager.set('some-object', 'Some object')

    @istest
    def uses_custom_sessions_database_if_provided(self):
        handler = StubHandler()
        handler.settings = {
            'pycket': {
                'engine': 'redis',
                'storage': {
                    'db_sessions': 10,
                    'db_notifications': 11,
                }
            },
        }
        manager = SessionManager(handler)
        manager.set('foo', 'bar')
        self.assertEqual(manager.driver.client.connection_pool._available_connections[0].db, 10)

    @istest
    def deletes_multiple_session_objects_at_once(self):
        handler = StubHandler()
        manager = SessionManager(handler)

        manager.set('some-object', {'foo': 'bar'})
        manager.set('some-object2', {'foo2': 'bar2'})
        manager.delete('some-object', 'some-object2')

        raw_session = self.client.get(handler.session_id)
        session = pickle.loads(raw_session)

        self.assertEqual(list(session.keys()), [])

    @istest
    def deletes_item_using_command(self):
        handler = StubHandler()
        manager = SessionManager(handler)

        manager.set('some-object', {'foo': 'bar'})

        del manager['some-object']

        self.assertIsNone(manager.get('some-object'))

    @istest
    def verifies_if_a_session_exist(self):
        handler = StubHandler()
        manager = SessionManager(handler)

        self.assertFalse('foo' in manager)

        manager['foo'] = 'bar'

        self.assertTrue('foo' in manager)

    @istest
    def gets_all_available_keys_from_session(self):
        handler = StubHandler()
        manager = SessionManager(handler)

        manager.set('foo', 'FOO')
        manager.set('bar', 'BAR')

        self.assertListEqual(sorted(manager.keys()), sorted(['foo', 'bar']))

    @istest
    def iterates_with_method_over_keys(self):
        handler = StubHandler()
        manager = SessionManager(handler)

        manager.set('foo', 'FOO')
        manager.set('bar', 'BAR')

        iterations = 0

        for key in manager.iterkeys():
            self.assertTrue(key in manager)
            iterations += 1

        self.assertEqual(iterations, 2)

    @istest
    def iterates_without_method_over_keys(self):
        handler = StubHandler()
        manager = SessionManager(handler)

        manager.set('foo', 'FOO')
        manager.set('bar', 'BAR')

        iterations = 0

        for key in manager:
            self.assertTrue(key in manager)
            iterations += 1

        self.assertEqual(iterations, 2)


class StubHandler(object):
    session_id = 'session-id'

    def __init__(self, settings=None):
        default_settings = {
            'pycket': {
                'engine': 'redis',
            }
        }
        self.settings = settings if settings is not None else default_settings

    def get_secure_cookie(self, name):
        return self.session_id

########NEW FILE########
