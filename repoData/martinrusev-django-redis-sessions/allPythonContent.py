__FILENAME__ = session
import redis

try:
    from django.utils.encoding import force_unicode
except ImportError:  # Python 3.*
    from django.utils.encoding import force_text as force_unicode
from django.contrib.sessions.backends.base import SessionBase, CreateError
from redis_sessions import settings


# Avoid new redis connection on each request

if settings.SESSION_REDIS_SENTINEL_LIST is not None:
    from redis.sentinel import Sentinel

    redis_server = Sentinel(settings.SESSION_REDIS_SENTINEL_LIST, socket_timeout=0.1) \
                    .master_for(settings.SESSION_REDIS_SENTINEL_MASTER_ALIAS, socket_timeout=0.1)

elif settings.SESSION_REDIS_URL is not None:

    redis_server = redis.StrictRedis.from_url(settings.SESSION_REDIS_URL)
elif settings.SESSION_REDIS_UNIX_DOMAIN_SOCKET_PATH is None:
    
    redis_server = redis.StrictRedis(
        host=settings.SESSION_REDIS_HOST,
        port=settings.SESSION_REDIS_PORT,
        db=settings.SESSION_REDIS_DB,
        password=settings.SESSION_REDIS_PASSWORD
    )
else:

    redis_server = redis.StrictRedis(
        unix_socket_path=settings.SESSION_REDIS_UNIX_DOMAIN_SOCKET_PATH,
        db=settings.SESSION_REDIS_DB,
        password=settings.SESSION_REDIS_PASSWORD,
    )


class SessionStore(SessionBase):
    """
    Implements Redis database session store.
    """
    def __init__(self, session_key=None):
        super(SessionStore, self).__init__(session_key)

        self.server = redis_server

    def load(self):
        try:
            session_data = self.server.get(
                self.get_real_stored_key(self._get_or_create_session_key())
            )
            return self.decode(force_unicode(session_data))
        except:
            self.create()
            return {}

    def exists(self, session_key):
        return self.server.exists(self.get_real_stored_key(session_key))

    def create(self):
        while True:
            self._session_key = self._get_new_session_key()

            try:
                self.save(must_create=True)
            except CreateError:
                continue
            self.modified = True
            return

    def save(self, must_create=False):
        if must_create and self.exists(self._get_or_create_session_key()):
            raise CreateError
        data = self.encode(self._get_session(no_load=must_create))
        if redis.VERSION[0] >= 2:
            self.server.setex(
                self.get_real_stored_key(self._get_or_create_session_key()),
                self.get_expiry_age(),
                data
            )
        else:
            self.server.set(
                self.get_real_stored_key(self._get_or_create_session_key()),
                data
            )
            self.server.expire(
                self.get_real_stored_key(self._get_or_create_session_key()),
                self.get_expiry_age()
            )

    def delete(self, session_key=None):
        if session_key is None:
            if self.session_key is None:
                return
            session_key = self.session_key
        try:
            self.server.delete(self.get_real_stored_key(session_key))
        except:
            pass

    def get_real_stored_key(self, session_key):
        """Return the real key name in redis storage
        @return string
        """
        prefix = settings.SESSION_REDIS_PREFIX
        if not prefix:
            return session_key
        return ':'.join([prefix, session_key])

########NEW FILE########
__FILENAME__ = settings
from django.conf import settings


SESSION_REDIS_HOST = getattr(settings, 'SESSION_REDIS_HOST', 'localhost')
SESSION_REDIS_PORT = getattr(settings, 'SESSION_REDIS_PORT', 6379)
SESSION_REDIS_DB = getattr(settings, 'SESSION_REDIS_DB', 0)
SESSION_REDIS_PREFIX = getattr(settings, 'SESSION_REDIS_PREFIX', '')
SESSION_REDIS_PASSWORD = getattr(settings, 'SESSION_REDIS_PASSWORD', None)
SESSION_REDIS_UNIX_DOMAIN_SOCKET_PATH = getattr(
    settings, 'SESSION_REDIS_UNIX_DOMAIN_SOCKET_PATH', None
)
SESSION_REDIS_URL = getattr(settings, 'SESSION_REDIS_URL', None)

# should be on the format [(host, port), (host, port), (host, port)]
SESSION_REDIS_SENTINEL_LIST = getattr(
	settings, 'SESSION_REDIS_SENTINEL_LIST', None
)
SESSION_REDIS_SENTINEL_MASTER_ALIAS = getattr(
	settings, 'SESSION_REDIS_SENTINEL_MASTER_ALIAS', None
)
########NEW FILE########
__FILENAME__ = tests
from redis_sessions.session import SessionStore
from redis_sessions import settings
import time
from nose.tools import eq_


##  Dev
import redis
import timeit

redis_session = SessionStore()


def test_modify_and_keys():
    eq_(redis_session.modified, False)
    redis_session['test'] = 'test_me'
    eq_(redis_session.modified, True)
    eq_(redis_session['test'], 'test_me')


def test_save_and_delete():
    redis_session['key'] = 'value'
    redis_session.save()
    eq_(redis_session.exists(redis_session.session_key), True)
    redis_session.delete(redis_session.session_key)
    eq_(redis_session.exists(redis_session.session_key), False)


def test_flush():
    redis_session['key'] = 'another_value'
    redis_session.save()
    key = redis_session.session_key
    redis_session.flush()
    eq_(redis_session.exists(key), False)


def test_items():
    redis_session['item1'], redis_session['item2'] = 1, 2
    redis_session.save()
    # Python 3.*
    eq_(list(redis_session.items()), [('item2', 2), ('item1', 1)])


def test_expiry():
    redis_session.set_expiry(1)
    # Test if the expiry age is set correctly
    eq_(redis_session.get_expiry_age(), 1)
    redis_session['key'] = 'expiring_value'
    redis_session.save()
    key = redis_session.session_key
    eq_(redis_session.exists(key), True)
    time.sleep(2)
    eq_(redis_session.exists(key), False)


def test_save_and_load():
    redis_session.set_expiry(60)
    redis_session.setdefault('item_test', 8)
    redis_session.save()
    session_data = redis_session.load()
    eq_(session_data.get('item_test'), 8)

def test_with_redis_url_config():
    settings.SESSION_REDIS_URL = 'redis://localhost'

    from redis_sessions.session import SessionStore

    redis_session = SessionStore()
    server = redis_session.server
    
    host = server.connection_pool.connection_kwargs.get('host')
    port = server.connection_pool.connection_kwargs.get('port')
    db = server.connection_pool.connection_kwargs.get('db')

    eq_(host, 'localhost')
    eq_(port, 6379)
    eq_(db, 0)

def test_with_unix_url_config():
    pass

    # Uncomment this in `redis.conf`:
    # 
    # unixsocket /tmp/redis.sock
    # unixsocketperm 755

    settings.SESSION_REDIS_URL = 'unix:///tmp/redis.sock'

    from redis_sessions.session import SessionStore

    redis_session = SessionStore()
    server = redis_session.server
    
    host = server.connection_pool.connection_kwargs.get('host')
    port = server.connection_pool.connection_kwargs.get('port')
    db = server.connection_pool.connection_kwargs.get('db')

    eq_(host, 'localhost')
    eq_(port, 6379)
    eq_(db, 0)

# def test_load():
#     redis_session.set_expiry(60)
#     redis_session['item1'], redis_session['item2'] = 1,2
#     redis_session.save()
#     session_data = redis_session.server.get(redis_session.session_key)
#     expiry, data = int(session_data[:15]), session_data[15:]

########NEW FILE########
