__FILENAME__ = base
"Base key-value store abstract class."

from django.core.exceptions import ImproperlyConfigured

class InvalidKeyValueStoreBackendError(ImproperlyConfigured):
    pass

class BaseStorage(object):
    def __init__(self, *args, **kwargs):
        pass

    def set(self, key, value):
        """Set a value in the key-value store."""
        raise NotImplementedError

    def delete(self, key):
        """Delete a key from the key-value store. Fail silently."""
        raise NotImplementedError

    def has_key(self, key):
        """Returns True if the key is in the store."""
        return self.get(key) is not None

    def __contains__(self, key):
        """Returns true if the key is in the store."""
        return self.has_key(key)

########NEW FILE########
__FILENAME__ = db
"""
Database key-value store backend.

Example configuration for Django settings:

    KEY_VALUE_STORE_BACKEND = 'db://table_name'

You will need to create a database table for storing the key-value pairs
when using this backend. The table should have two columns, 'kee' - capable of
storing up to 255 characters, and 'value', which should be a text type
(character blob). You can declare a regular Django model for this table, if
you want Django's ``syncdb`` command to create it for you. Just make sure the
table name Django uses is the same table name provided in the
``KEY_VALUE_STORE_BACKEND`` setting.
"""

import base64
from django_kvstore.backends.base import BaseStorage
from django.db import connection, transaction, DatabaseError
try:
    import cPickle as pickle
except ImportError:
    import pickle

class StorageClass(BaseStorage):
    def __init__(self, table, params):
        BaseStorage.__init__(self, params)
        self._table = table

    def get(self, key):
        cursor = connection.cursor()
        cursor.execute("SELECT kee, value FROM %s WHERE kee = %%s" % self._table, [key])
        row = cursor.fetchone()
        if row is None:
            return None
        return pickle.loads(base64.decodestring(row[1]))

    def set(self, key, value):
        encoded = base64.encodestring(pickle.dumps(value, 2)).strip()
        cursor = connection.cursor()
        cursor.execute("SELECT kee FROM %s WHERE kee = %%s" % self._table, [key])
        try:
            if cursor.fetchone():
                cursor.execute("UPDATE %s SET value = %%s WHERE kee = %%s" % self._table, [encoded, key])
            else:
                cursor.execute("INSERT INTO %s (kee, value) VALUES (%%s, %%s)" % self._table, [key, encoded])
        except DatabaseError, e:
            # To be threadsafe, updates/inserts are allowed to fail silently
            return False
        else:
            transaction.commit_unless_managed()
            return True

    def delete(self, key):
        cursor = connection.cursor()
        cursor.execute("DELETE FROM %s WHERE kee = %%s" % self._table, [key])
        transaction.commit_unless_managed()

    def has_key(self, key):
        cursor = connection.cursor()
        cursor.execute("SELECT kee FROM %s WHERE kee = %%s" % self._table, [key])
        return cursor.fetchone() is not None

########NEW FILE########
__FILENAME__ = googleappengine
"""
A Google AppEngine key-value store backend.

Example configuration for Django settings:

    KEY_VALUE_STORE_BACKEND = 'appengine://'

"""

import base64
from base import BaseStorage, InvalidKeyValueStoreBackendError
try:
    import cPickle as pickle
except ImportError:
    import pickle

try:
    from google.appengine.ext import db
except ImportError:
    raise InvalidKeyValueStoreBackendError("googleappengine key-value store backend requires google.appengine.ext.db import")


class DjangoKVStore(db.Model):
    value = db.BlobProperty()


class StorageClass(BaseStorage):
    def __init__(self, table=None, params=None):
        BaseStorage.__init__(self, params)
        self._model = DjangoKVStore

    def _get(self, key):
        return self._model.get_by_key_name('k:' + key)

    def get(self, key):
        row = self._get(key)
        if row is None:
            return None
        return pickle.loads(base64.decodestring(row.value))

    def set(self, key, value):
        encoded = base64.encodestring(pickle.dumps(value, 2)).strip()
        row = self._get(key)
        if row is None:
            row = self._model(key_name='k:'+key)
        row.value = encoded
        row.save()
        return True

    def delete(self, key):
        row = self._get(key)
        if row is not None:
            row.delete()

    def has_key(self, key):
        return self._get(key) is not None

########NEW FILE########
__FILENAME__ = locmem
"""
Thread-safe in-memory key-value store backend.

Just for testing. This isn't persistent. Don't actually use it.

Example configuration for Django settings:

    KEY_VALUE_STORE_BACKEND = 'locmem://'

"""

try:
    import cPickle as pickle
except ImportError:
    import pickle

from base import BaseStorage
from django.utils.synch import RWLock

class StorageClass(BaseStorage):
    def __init__(self, _, params):
        BaseStorage.__init__(self, params)
        self._db = {}
        self._lock = RWLock()

    def set(self, key, value):
        self._lock.writer_enters()
        try:
            self._db[key] = pickle.dumps(value)
        finally:
            self._lock.writer_leaves()

    def get(self, key):
        self._lock.reader_enters()
        # Python 2.3 and 2.4 don't allow combined try-except-finally blocks.
        try:
            try:
                return pickle.loads(self._db[key])
            except KeyError:
                return None
        finally:
            self._lock.reader_leaves()

    def delete(self, key):
        self._lock.write_enters()
        # Python 2.3 and 2.4 don't allow combined try-except-finally blocks.
        try:
            try:
                del self._db[key]
            except KeyError:
                pass
        finally:
            self._lock.writer_leaves()

    def has_key(self, key):
        self._lock.reader_enters()
        try:
            return key in self._db
        finally:
            self._lcok.reader_leaves()

########NEW FILE########
__FILENAME__ = memcached
"""
Memcache key-value store backend

Just for testing. This isn't persistent. Don't actually use it.

Example configuration for Django settings:

    KEY_VALUE_STORE_BACKEND = 'memcached://hostname:port'

"""

from base import BaseStorage, InvalidKeyValueStoreBackendError
from django.utils.encoding import smart_unicode, smart_str

try:
    import cmemcache as memcache
except ImportError:
    try:
        import memcache
    except:
        raise InvalidKeyValueStoreBackendError("Memcached key-value store backend requires either the 'memcache' or 'cmemcache' library")

class StorageClass(BaseStorage):
    def __init__(self, server, params):
        BaseStorage.__init__(self, params)
        self._db = memcache.Client(server.split(';'))

    def set(self, key, value):
        if isinstance(value, unicode):
            value = value.encode('utf-8')
        self._db.set(smart_str(key), value, 0)

    def get(self, key):
        val = self._db.get(smart_str(key))
        if isinstance(val, basestring):
            return smart_unicode(val)
        else:
            return val

    def delete(self, key):
        self._db.delete(smart_str(key))

    def close(self, **kwargs):
        self._db.disconnect_all()

########NEW FILE########
__FILENAME__ = redisdj
"""
Redis key-value store backend.

Example configuration for Django settings:

    KEY_VALUE_STORE_BACKEND = 'redis://hostname:port'

port is optional. If none is given, the port specified in redis.conf will be used.

"""
import base64
from base import BaseStorage, InvalidKeyValueStoreBackendError
from django.utils.encoding import smart_unicode, smart_str

try:
    import redis
except ImportError:
    raise InvalidKeyValueStoreBackendError("The Redis key-value store backend requires the Redis python client.")

try:
    import cPickle as pickle
except ImportError:
    import pickle

class StorageClass(BaseStorage):

    def __init__(self, server, params):
        if ':' in server:
            host, port = server.split(':')
            port = int(port)
        else:
            host, port = server, None
        params['port'] = port
        BaseStorage.__init__(self, params)
        self._db = redis.Redis(host=host, **params)

    def set(self, key, value):
        encoded = base64.encodestring(pickle.dumps(value, 2)).strip()
        self._db.set(smart_str(key), encoded)

    def get(self, key):
        val = self._db.get(smart_str(key))
        if val is None:
            return None
        return pickle.loads(base64.decodestring(val))

    def delete(self, key):
        self._db.delete(smart_str(key))

    def close(self, **kwargs):
        pass

########NEW FILE########
__FILENAME__ = sdb
"""
Amazon SimpleDB key-value store backend

Example configuration for Django settings:

    KEY_VALUE_STORE_BACKEND = 'sdb://<simpledb_domain>?aws_access_key=<access_key>&aws_secret_access_key=<secret_key>'

"""


from base import BaseStorage, InvalidKeyValueStoreBackendError
from django.core.exceptions import ImproperlyConfigured
from django.utils.encoding import smart_unicode, smart_str
from django.utils import simplejson

try:
    import simpledb
except ImportError:
    raise InvalidKeyValueStoreBackendError("SipmleDB key-value store backend requires the 'python-simpledb' library")

class StorageClass(BaseStorage):
    def __init__(self, domain, params):
        BaseStorage.__init__(self, params)
        params = dict(params)
        try:
            aws_access_key = params['aws_access_key']
            aws_secret_access_key = params['aws_secret_access_key']
        except KeyError:
            raise ImproperlyConfigured("Incomplete configuration of SimpleDB key-value store. Required parameters: 'aws_access_key', and 'aws_secret_access_key'.")
        self._db = simpledb.SimpleDB(aws_access_key, aws_secret_access_key)
        self._domain = self._db[domain]

    def set(self, key, value):
        if isinstance(value, unicode):
            value = value.encode('utf-8')
        self._domain[smart_str(key)] = {'value': simplejson.dumps(value)}

    def get(self, key):
        val = self._domain[smart_str(key)].get('value', None)
        if isinstance(val, basestring):
            return simplejson.loads(val)
        else:
            return val

    def delete(self, key):
        del self._domain[smart_str(key)]

    def close(self, **kwargs):
        pass

########NEW FILE########
__FILENAME__ = tokyotyrant
"""
Memcache key-value store backend

Just for testing. This isn't persistent. Don't actually use it.

Example configuration for Django settings:

    KEY_VALUE_STORE_BACKEND = 'tokyotyrant://hostname:port

"""

from base import BaseStorage, InvalidKeyValueStoreBackendError
from django.core.exceptions import ImproperlyConfigured
from django.utils.encoding import smart_unicode, smart_str
from django.utils import simplejson

try:
    import pytyrant
except ImportError:
    raise InvalidKeyValueStoreBackendError("Tokyotyrant key-value store backend requires the 'pytyrant' library")

class StorageClass(BaseStorage):
    def __init__(self, server, params):
        BaseStorage.__init__(self, params)
        host, port = server.split(':')
        try:
            port = int(port)
        except ValueError:
            raise ImproperlyConfigured("Invalid port provided for tokyo-tyrant key-value store backend")
        self._db = pytyrant.PyTyrant.open(host, port)

    def set(self, key, value):
        if isinstance(value, unicode):
            value = value.encode('utf-8')
        self._db[smart_str(key)] = simplejson.dumps(value)

    def get(self, key):
        val = self._db.get(smart_str(key))
        if isinstance(val, basestring):
            return simplejson.loads(val)
        else:
            return val

    def delete(self, key):
        del self._db[smart_str(key)]

    def close(self, **kwargs):
        pass
        # Er, should be closing after each request..? But throws
        # a 'Bad File Descriptor' exception if we do (presumably because
        # something's trying to use a connection that's already been
        # closed...
        #self._db.close()

########NEW FILE########
__FILENAME__ = models
from django_kvstore import kvstore


class FieldError(Exception): pass

KV_PREFIX = '__KV_STORE_::'

def generate_key(cls, pk):
    return str('%s%s.%s:%s' % (KV_PREFIX, cls.__module__, cls.__name__, pk))


class Field(object):
    def __init__(self, default=None, pk=False):
        self.default = default
        self.pk = pk

    def install(self, name, cls):
        setattr(cls, name, self.default)

    def decode(self, value):
        """Decodes an object from the datastore into a python object."""
        return value
    
    def encode(self, value):
        """Encodes an object into a value suitable for the backend datastore."""
        return value


class ModelMetaclass(type):
    """
    Metaclass for `kvstore.models.Model` instances. Installs 
    `kvstore.models.Field` and `kvstore.models.Key` instances
    declared as attributes of the new class.

    """

    def __new__(cls, name, bases, attrs):
        fields = {}

        for base in bases:
            if isinstance(base, ModelMetaclass):
                fields.update(base.fields)

        new_fields = {}
        # Move all the class's attributes that are Fields to the fields set.
        for attrname, field in attrs.items():
            if isinstance(field, Field):
                new_fields[attrname] = field
                if field.pk:
                    # Add key_field attr so we know what the key is
                    if 'key_field' in attrs:
                        raise FieldError("Multiple key fields defined for model '%s'" % name)
                    attrs['key_field'] = attrname
            elif attrname in fields:
                # Throw out any parent fields that the subclass defined as
                # something other than a field
                del fields[attrname]

        fields.update(new_fields)
        attrs['fields'] = fields
        new_cls = super(ModelMetaclass, cls).__new__(cls, name, bases, attrs)

        for field, value in new_fields.items():
            new_cls.add_to_class(field, value)

        return new_cls

    def add_to_class(cls, name, value):
        if hasattr(value, 'install'):
            value.install(name, cls)
        else:
            setattr(cls, name, value)


class Model(object):

    __metaclass__ = ModelMetaclass

    def __init__(self, **kwargs):
        for name, value in kwargs.items():
            setattr(self, name, value)

    def to_dict(self):
        d = {}
        for name, field in self.fields.items():
            d[name] = field.encode(getattr(self, name))
        return d

    def save(self):
        d = self.to_dict()
        kvstore.set(generate_key(self.__class__, self._get_pk_value()), d)

    def delete(self):
        kvstore.delete(generate_key(self.__class__, self._get_pk_value()))

    def _get_pk_value(self):
        return getattr(self, self.key_field)

    @classmethod
    def from_dict(cls, fields):
        for name, value in fields.items():
            # Keys can't be unicode to work as **kwargs. Must delete and re-add
            # otherwise the dict won't change the type of the key.
            if name in cls.fields:
                if isinstance(name, unicode):
                    del fields[name]
                    name = name.encode('utf-8')
                fields[name] = cls.fields[name].decode(value)
            else:
                del fields[name]
        return cls(**fields)

    @classmethod
    def get(cls, id):
        fields = kvstore.get(generate_key(cls, id))
        if fields is None:
            return None
        return cls.from_dict(fields)


########NEW FILE########
