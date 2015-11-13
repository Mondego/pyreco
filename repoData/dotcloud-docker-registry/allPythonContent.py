__FILENAME__ = gunicorn_config
## Gunicorn config file

import os

flavor = os.environ.get('SETTINGS_FLAVOR', 'dev')

reload = True
bind = '0.0.0.0:{0}'.format(os.environ.get('PORT_WWW', 8000))
graceful_timeout = 3600
timeout = 3600
worker_class = 'gevent'
max_requests = 100
workers = 4
log_level = 'debug'
debug = True
accesslog = '-'
access_log_format = ('%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" '
                     '"%(a)s" %(D)s %({X-Docker-Size}o)s')

if flavor == 'prod' or flavor == 'staging':
    reload = False
    workers = 8
    debug = False
    log_level = 'info'
    accesslog = '/var/log/supervisor/access.log'

########NEW FILE########
__FILENAME__ = boto
# -*- coding: utf-8 -*-
# Copyright (c) 2014 Docker.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
docker_registry.core.boto
~~~~~~~~~~~~~~~~~~~~~~~~~~

Might be useful for
 * Amazon Simple Storage Service (S3)
 * Google Cloud Storage
 * Amazon Glacier
 * Amazon Elastic Block Store (EBS)

"""

import gevent.monkey
gevent.monkey.patch_all()

import copy
import logging
import math
import os
import tempfile

from . import driver
from . import lru

from .exceptions import FileNotFoundError

logger = logging.getLogger(__name__)


class ParallelKey(object):

    """This class implements parallel transfer on a key to improve speed."""

    CONCURRENCY = 5

    def __init__(self, key):
        logger.info('ParallelKey: {0}; size={1}'.format(key, key.size))
        self._boto_key = key
        self._cursor = 0
        self._max_completed_byte = 0
        self._max_completed_index = 0
        self._tmpfile = tempfile.NamedTemporaryFile(mode='rb')
        self._completed = [0] * self.CONCURRENCY
        self._spawn_jobs()

    def __del__(self):
        self._tmpfile.close()

    def _generate_bytes_ranges(self, num_parts):
        size = self._boto_key.size
        chunk_size = int(math.ceil(1.0 * size / num_parts))
        for i in range(num_parts):
            yield (i, chunk_size * i, min(chunk_size * (i + 1) - 1, size - 1))

    def _fetch_part(self, fname, index, min_cur, max_cur):
        boto_key = copy.copy(self._boto_key)
        with open(fname, 'wb') as f:
            f.seek(min_cur)
            brange = 'bytes={0}-{1}'.format(min_cur, max_cur)
            boto_key.get_contents_to_file(f, headers={'Range': brange})
            boto_key.close()
        self._completed[index] = (index, max_cur)
        self._refresh_max_completed_byte()

    def _spawn_jobs(self):
        bytes_ranges = self._generate_bytes_ranges(self.CONCURRENCY)
        for i, min_cur, max_cur in bytes_ranges:
            gevent.spawn(self._fetch_part, self._tmpfile.name,
                         i, min_cur, max_cur)

    def _refresh_max_completed_byte(self):
        for v in self._completed[self._max_completed_index:]:
            if v == 0:
                return
            self._max_completed_index = v[0]
            self._max_completed_byte = v[1]
            if self._max_completed_index >= len(self._completed) - 1:
                percent = round(
                    (100.0 * self._cursor) / self._boto_key.size, 1)
                logger.info('ParallelKey: {0}; buffering complete at {1}% of '
                            'the total transfer; now serving straight from '
                            'the tempfile'.format(self._boto_key, percent))

    def read(self, size):
        if self._cursor >= self._boto_key.size:
            # Read completed
            return ''
        sz = size
        if self._max_completed_index < len(self._completed) - 1:
            # Not all data arrived yet
            if self._cursor + size > self._max_completed_byte:
                while self._cursor >= self._max_completed_byte:
                    # We're waiting for more data to arrive
                    gevent.sleep(0.2)
            if self._cursor + sz > self._max_completed_byte:
                sz = self._max_completed_byte - self._cursor
        # Use a low-level read to avoid any buffering (makes sure we don't
        # read more than `sz' bytes).
        buf = os.read(self._tmpfile.file.fileno(), sz)
        self._cursor += len(buf)
        if not buf:
            message = ('ParallelKey: {0}; got en empty read on the buffer! '
                       'cursor={1}, size={2}; Transfer interrupted.'.format(
                           self._boto_key, self._cursor, self._boto_key.size))
            logging.error(message)
            raise RuntimeError(message)
        return buf


class Base(driver.Base):

    supports_bytes_range = True

    def __init__(self, path=None, config=None):
        self._config = config
        self._root_path = config.get('storage_path', '/test')
        self._boto_conn = self.makeConnection()
        self._boto_bucket = self._boto_conn.get_bucket(
            self._config.boto_bucket)
        logger.info("Boto based storage initialized")

    def _build_connection_params(self):
        kwargs = {'is_secure': (self._config.boto_secure is True)}
        config_args = [
            'host', 'port', 'debug',
            'proxy', 'proxy_port',
            'proxy_user', 'proxy_pass'
        ]
        for arg in config_args:
            confkey = 'boto_' + arg
            if getattr(self._config, confkey, None) is not None:
                kwargs[arg] = getattr(self._config, confkey)
        return kwargs

    def _debug_key(self, key):
        """Used for debugging only."""
        orig_meth = key.bucket.connection.make_request

        def new_meth(*args, **kwargs):
            print('#' * 16)
            print(args)
            print(kwargs)
            print('#' * 16)
            return orig_meth(*args, **kwargs)
        key.bucket.connection.make_request = new_meth

    def _init_path(self, path=None):
        path = os.path.join(self._root_path, path) if path else self._root_path
        if path and path[0] == '/':
            return path[1:]
        return path

    def stream_read(self, path, bytes_range=None):
        path = self._init_path(path)
        headers = None
        if bytes_range:
            headers = {'Range': 'bytes={0}-{1}'.format(*bytes_range)}
        key = self._boto_bucket.lookup(path, headers=headers)
        if not key:
            raise FileNotFoundError('%s is not there' % path)
        if not bytes_range and key.size > 1024 * 1024:
            # Use the parallel key only if the key size is > 1MB
            # And if bytes_range is not enabled (since ParallelKey is already
            # using bytes range)
            key = ParallelKey(key)
        while True:
            buf = key.read(self.buffer_size)
            if not buf:
                break
            yield buf

    def list_directory(self, path=None):
        path = self._init_path(path)
        if not path.endswith('/'):
            path += '/'
        ln = 0
        if self._root_path != '/':
            ln = len(self._root_path)
        exists = False
        for key in self._boto_bucket.list(prefix=path, delimiter='/'):
            if '%s/' % key.name == path:
                continue
            exists = True
            name = key.name
            if name.endswith('/'):
                yield name[ln:-1]
            else:
                yield name[ln:]
        if not exists:
            raise FileNotFoundError('%s is not there' % path)

    def get_size(self, path):
        path = self._init_path(path)
        # Lookup does a HEAD HTTP Request on the object
        key = self._boto_bucket.lookup(path)
        if not key:
            raise FileNotFoundError('%s is not there' % path)
        return key.size

    @lru.get
    def get_content(self, path):
        path = self._init_path(path)
        key = self.makeKey(path)
        if not key.exists():
            raise FileNotFoundError('%s is not there' % path)
        return key.get_contents_as_string()

    def exists(self, path):
        path = self._init_path(path)
        key = self.makeKey(path)
        return key.exists()

    @lru.remove
    def remove(self, path):
        path = self._init_path(path)
        key = self.makeKey(path)
        if key.exists():
            # It's a file
            key.delete()
            return
        # We assume it's a directory
        if not path.endswith('/'):
            path += '/'
        exists = False
        for key in self._boto_bucket.list(prefix=path, delimiter='/'):
            if '%s/' % key.name == path:
                continue
            exists = True
            key.delete()
        if not exists:
            raise FileNotFoundError('%s is not there' % path)

########NEW FILE########
__FILENAME__ = compat
# -*- coding: utf-8 -*-
# Copyright (c) 2014 Docker.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
docker_registry.core.compat
~~~~~~~~~~~~~~~~~~~~~~

This file defines a collection of properties to quickly identify what python
runtime/version we are working with, and handles the import of problematic
modules, hence hiding import gymnastics from other components.

Use imports from here to ensure portability.

Largely stolen from requests (http://docs.python-requests.org/en/latest/)
under Apache2 license
"""

import logging
import sys

__all__ = ['builtin_str', 'str', 'bytes', 'basestring', 'json', 'quote_plus',
           'StringIO']

logger = logging.getLogger(__name__)

# -------
# Pythons
# -------

_ver = sys.version_info

is_py2 = (_ver[0] == 2)
is_py3 = (_ver[0] == 3)

is_py26 = (is_py2 and _ver[1] == 6)
# is_py27 = (is_py2 and _ver[1] == 7)
# is_py30 = (is_py3 and _ver[1] == 0)
# is_py31 = (is_py3 and _ver[1] == 1)
# is_py32 = (is_py3 and _ver[1] == 2)
# is_py33 = (is_py3 and _ver[1] == 3)
# is_py34 = (is_py3 and _ver[1] == 4)

# ---------
# Platforms
# ---------

# _ver = sys.version.lower()

# is_pypy = ('pypy' in _ver)
# is_jython = ('jython' in _ver)
# is_ironpython = ('iron' in _ver)
# is_cpython = not any((is_pypy, is_jython, is_ironpython))

# is_windows = 'win32' in str(sys.platform).lower()
# is_linux = ('linux' in str(sys.platform).lower())
# is_osx = ('darwin' in str(sys.platform).lower())
# is_hpux = ('hpux' in str(sys.platform).lower())   # Complete guess.
# is_solaris = ('solar' in str(sys.platform).lower())   # Complete guess.

if is_py26:
    logger.debug("Old python! Using simplejson.")
    import simplejson as json  # noqa
else:
    import json  # noqa

# ---------
# Specifics
# ---------

if is_py2:
    logger.debug("This is python2")
    from urllib import quote_plus  # noqa

    builtin_str = str
    bytes = str
    str = unicode
    basestring = basestring
    # numeric_types = (int, long, float)

    from cStringIO import StringIO  # noqa

elif is_py3:
    logger.debug("This is python3")
    from urllib.parse import quote_plus  # noqa

    builtin_str = str
    str = str
    bytes = bytes
    basestring = (str, bytes)
    # numeric_types = (int, float)

    from io import BytesIO as StringIO  # noqa

########NEW FILE########
__FILENAME__ = driver
# -*- coding: utf-8 -*-
# Copyright (c) 2014 Docker.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
docker_registry.core.driver
~~~~~~~~~~~~~~~~~~~~~~~~~~

This file defines:
 * a generic interface that describes a uniform "driver"
 * methods to register / get these "connections"

Pretty much, the purpose of this is just to abstract the underlying storage
implementation, for a given scheme.
"""

__all__ = ["fetch", "available", "Base"]

import logging
import pkgutil

import docker_registry.drivers

from .compat import json
from .exceptions import NotImplementedError

logger = logging.getLogger(__name__)


class Base(object):

    """Storage is a convenience class that describes methods that must be
    implemented by any backend.
    You should inherit (or duck type) this if you are implementing your own.

    :param host: host name
    :type host: unicode
    :param port: port number
    :type port: int
    :param basepath: base path (will be prepended to actual requests)
    :type basepath: unicode
    """

    # Useful if we want to change those locations later without rewriting
    # the code which uses Storage
    repositories = 'repositories'
    images = 'images'

    # Set the IO buffer to 128kB
    buffer_size = 128 * 1024
    # By default no storage plugin supports it
    supports_bytes_range = False

    # FIXME(samalba): Move all path resolver in each module (out of the base)
    def images_list_path(self, namespace, repository):
        repository_path = self.repository_path(
            namespace=namespace, repository=repository)
        return '{0}/_images_list'.format(repository_path)

    def image_json_path(self, image_id):
        return '{0}/{1}/json'.format(self.images, image_id)

    def image_mark_path(self, image_id):
        return '{0}/{1}/_inprogress'.format(self.images, image_id)

    def image_checksum_path(self, image_id):
        return '{0}/{1}/_checksum'.format(self.images, image_id)

    def image_layer_path(self, image_id):
        return '{0}/{1}/layer'.format(self.images, image_id)

    def image_ancestry_path(self, image_id):
        return '{0}/{1}/ancestry'.format(self.images, image_id)

    def image_files_path(self, image_id):
        return '{0}/{1}/_files'.format(self.images, image_id)

    def image_diff_path(self, image_id):
        return '{0}/{1}/_diff'.format(self.images, image_id)

    def repository_path(self, namespace, repository):
        return '{0}/{1}/{2}'.format(
            self.repositories, namespace, repository)

    def tag_path(self, namespace, repository, tagname=None):
        repository_path = self.repository_path(
            namespace=namespace, repository=repository)
        if not tagname:
            return repository_path
        return '{0}/tag_{1}'.format(repository_path, tagname)

    def repository_json_path(self, namespace, repository):
        repository_path = self.repository_path(
            namespace=namespace, repository=repository)
        return '{0}/json'.format(repository_path)

    def repository_tag_json_path(self, namespace, repository, tag):
        repository_path = self.repository_path(
            namespace=namespace, repository=repository)
        return '{0}/tag{1}_json'.format(repository_path, tag)

    def index_images_path(self, namespace, repository):
        repository_path = self.repository_path(
            namespace=namespace, repository=repository)
        return '{0}/_index_images'.format(repository_path)

    def private_flag_path(self, namespace, repository):
        repository_path = self.repository_path(
            namespace=namespace, repository=repository)
        return '{0}/_private'.format(repository_path)

    def is_private(self, namespace, repository):
        return self.exists(self.private_flag_path(namespace, repository))

    def content_redirect_url(self, path):
        """Get a URL for content at path

        Get a URL to which client can be redirected to get the content from
        the path. Return None if not supported by this engine.

        Note, this feature will only be used if the `storage_redirect`
        configuration key is set to `True`.
        """
        return None

    def get_json(self, path):
        return json.loads(self.get_unicode(path))

    def put_json(self, path, content):
        return self.put_unicode(path, json.dumps(content))

    def get_unicode(self, path):
        return self.get_bytes(path).decode('utf8')

    def put_unicode(self, path, content):
        return self.put_bytes(path, content.encode('utf8'))

    def get_bytes(self, path):
        return self.get_content(path)

    def put_bytes(self, path, content):
        return self.put_content(path, content)

    def get_content(self, path):
        """Method to get content
        """
        raise NotImplementedError(
            "You must implement get_content(self, path) on your storage %s" %
            self.__class__.__name__)

    def put_content(self, path, content):
        """Method to put content
        """
        raise NotImplementedError(
            "You must implement put_content(self, path, content) on %s" %
            self.__class__.__name__)

    def stream_read(self, path, bytes_range=None):
        """Method to stream read
        """
        raise NotImplementedError(
            "You must implement stream_read(self, path, , bytes_range=None) " +
            "on your storage %s" %
            self.__class__.__name__)

    def stream_write(self, path, fp):
        """Method to stream write
        """
        raise NotImplementedError(
            "You must implement stream_write(self, path, fp) " +
            "on your storage %s" %
            self.__class__.__name__)

    def list_directory(self, path=None):
        """Method to list directory
        """
        raise NotImplementedError(
            "You must implement list_directory(self, path=None) " +
            "on your storage %s" %
            self.__class__.__name__)

    def exists(self, path):
        """Method to test exists
        """
        raise NotImplementedError(
            "You must implement exists(self, path) on your storage %s" %
            self.__class__.__name__)

    def remove(self, path):
        """Method to remove
        """
        raise NotImplementedError(
            "You must implement remove(self, path) on your storage %s" %
            self.__class__.__name__)

    def get_size(self, path):
        """Method to get the size
        """
        raise NotImplementedError(
            "You must implement get_size(self, path) on your storage %s" %
            self.__class__.__name__)


def fetch(name):
    """The only public method you should access if you are not implementing
    your own driver. - use this to get a backend
    instance to which you can delegate actual requests.

    :param host: host name
    :type host: unicode
    :param port: port number
    :type port: int
    :param basepath: base path (will be prepended to actual requests)
    :type basepath: unicode
    :returns: a docker connection instance usable for the requested scheme
    :rtype: DockerConnection
    """
    try:
        # XXX The noqa below is because of hacking being non-sensical on this
        module = __import__('docker_registry.drivers.%s' % name, globals(),
                            locals(), ['Storage'], 0)  # noqa
        logger.debug("Will return docker-registry.drivers.%s.Storage" % name)
    except ImportError:
        raise NotImplementedError(
            """You requested storage driver docker_registry.drivers.%s
which is not installed. Try `pip install docker-registry-driver-%s`
or check your configuration. The following are currently
available on your system: %s"""
            % (name, name, available())
        )
    module.Storage.scheme = name
    return module.Storage


def available():
    return [modname for importer, modname, ispkg
            in pkgutil.iter_modules(docker_registry.drivers.__path__)]

########NEW FILE########
__FILENAME__ = exceptions
# -*- coding: utf-8 -*-
# Copyright (c) 2014 Docker.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
docker_registry.core.exceptions
~~~~~~~~~~~~~~~~~~~~~

Provide docker_registry exceptions to be used consistently in the drivers
and registry.
"""

__all__ = [
    "UnspecifiedError",
    "UsageError",
    "NotImplementedError", "FileNotFoundError", "WrongArgumentsError",
    "ConfigError",
    "ConnectionError",
    "UnreachableError", "MissingError", "BrokenError"
]


class UnspecifiedError(Exception):

    """Base class for all exceptions in docker_registry
    """

    def __init__(self, *args, **kwargs):
        self.message = kwargs.pop('message', 'No details')
        super(UnspecifiedError, self).__init__(*args, **kwargs)


class UsageError(UnspecifiedError):

    """Exceptions related to use of the library, like missing files,
    wrong argument type, etc.
    """


class NotImplementedError(UsageError):

    """The requested feature is not supported / not implemented."""


class FileNotFoundError(UsageError):

    """The requested (config) file is missing."""


class WrongArgumentsError(UsageError):

    """Expected arguments type not satisfied."""


class ConfigError(UsageError):

    """The provided configuration has problems."""


class ConnectionError(UnspecifiedError):

    """Network communication related errors all inherit this."""


class UnreachableError(ConnectionError):

    """The requested server is not reachable."""


class MissingError(ConnectionError):

    """The requested ressource is not to be found on the server."""


class BrokenError(ConnectionError):

    """Something died on our hands, that the server couldn't digest..."""

########NEW FILE########
__FILENAME__ = lru
# -*- coding: utf-8 -*-
# Copyright (c) 2014 Docker.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
docker_registry.core.lru
~~~~~~~~~~~~~~~~~~~~~~~~~~

Redis based LRU.
Can be activated or de-activated globally.
Drivers are largely encouraged to use it.
By default, doesn't run, until one calls init().
"""

import functools
import logging
import redis

logger = logging.getLogger(__name__)

redis_conn = None
cache_prefix = None


def init(enable=True,
         host='localhost', port=6379, db=0, password=None, path='/'):
    global redis_conn, cache_prefix
    if not enable:
        redis_conn = None
        return
    logging.info('Enabling storage cache on Redis')
    logging.info('Redis config: {0}'.format({
        'host': host,
        'port': port,
        'db': db,
        'password': password,
        'path': path
    }))
    redis_conn = redis.StrictRedis(host=host,
                                   port=int(port),
                                   db=int(db),
                                   password=password)
    cache_prefix = 'cache_path:{0}'.format(path)


def cache_key(key):
    return cache_prefix + key


def set(f):
    @functools.wraps(f)
    def wrapper(*args):
        content = args[-1]
        key = args[-2]
        key = cache_key(key)
        redis_conn.set(key, content)
        return f(*args)
    if redis_conn is None:
        return f
    return wrapper


def get(f):
    @functools.wraps(f)
    def wrapper(*args):
        key = args[-1]
        key = cache_key(key)
        content = redis_conn.get(key)
        if content is not None:
            return content
        # Refresh cache
        content = f(*args)
        if content is not None:
            redis_conn.set(key, content)
        return content
    if redis_conn is None:
        return f
    return wrapper


def remove(f):
    @functools.wraps(f)
    def wrapper(*args):
        key = args[-1]
        key = cache_key(key)
        redis_conn.delete(key)
        return f(*args)
    if redis_conn is None:
        return f
    return wrapper

########NEW FILE########
__FILENAME__ = dumb
# -*- coding: utf-8 -*-
# Copyright (c) 2014 Docker.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
docker_registry.drivers.dumb
~~~~~~~~~~~~~~~~~~~~~~~~~~

This is a very dumb driver, which uses memory to store data.
It obviously won't work out of very simple tests.
Should only be used for inspiration and tests.

"""

from ..core import compat
from ..core import driver
from ..core import exceptions


class Storage(driver.Base):

    _storage = {}

    def __init__(self, path=None, config=None):
        self.supports_bytes_range = True

    def exists(self, path):
        return path in self._storage

    def get_size(self, path):
        if path not in self._storage:
            raise exceptions.FileNotFoundError('%s is not there' % path)
        return len(self._storage[path])

    def get_content(self, path):
        if path not in self._storage:
            raise exceptions.FileNotFoundError('%s is not there' % path)
        return self._storage[path]

    def put_content(self, path, content):
        self._storage[path] = content

    def remove(self, path):
        if path not in self._storage:
            raise exceptions.FileNotFoundError('%s is not there' % path)
        del self._storage[path]

    def stream_read(self, path, bytes_range=None):
        if path not in self._storage:
            raise exceptions.FileNotFoundError('%s is not there' % path)

        f = self._storage[path]
        nb_bytes = 0
        total_size = 0
        if bytes_range:
            f.seek(bytes_range[0])
            total_size = bytes_range[1] - bytes_range[0] + 1
        else:
            f.seek(0)
        while True:
            buf = None
            if bytes_range:
                # Bytes Range is enabled
                buf_size = self.buffer_size
                if nb_bytes + buf_size > total_size:
                    # We make sure we don't read out of the range
                    buf_size = total_size - nb_bytes
                if buf_size > 0:
                    buf = f.read(buf_size)
                    nb_bytes += len(buf)
                else:
                    # We're at the end of the range
                    buf = ''
            else:
                buf = f.read(self.buffer_size)
            if not buf:
                break
            yield buf

    def stream_write(self, path, fp):
        # Size is mandatory
        if path not in self._storage:
            self._storage[path] = compat.StringIO()

        f = self._storage[path]
        try:
            while True:
                buf = fp.read(self.buffer_size)
                if not buf:
                    break
                f.write(buf)
        except IOError:
            pass

    def list_directory(self, path=None):
        # if path not in self._storage:
        #     raise exceptions.FileNotFoundError('%s is not there' % path)

        ls = []
        for k in self._storage.keys():
            if (not k == path) and k.startswith(path or ''):
                ls.append(k)

        if not len(ls):
            raise exceptions.FileNotFoundError('%s is not there' % path)

        return ls

########NEW FILE########
__FILENAME__ = file
# -*- coding: utf-8 -*-
# Copyright (c) 2014 Docker.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
docker_registry.drivers.file
~~~~~~~~~~~~~~~~~~~~~~~~~~

This is a simple filesystem based driver.

"""

import os
import shutil

from ..core import driver
from ..core import exceptions
from ..core import lru


class Storage(driver.Base):

    supports_bytes_range = True

    def __init__(self, path=None, config=None):
        self._root_path = path or './tmp'

    def _init_path(self, path=None, create=False):
        path = os.path.join(self._root_path, path) if path else self._root_path
        if create is True:
            dirname = os.path.dirname(path)
            if not os.path.exists(dirname):
                os.makedirs(dirname)
        return path

    @lru.get
    def get_content(self, path):
        path = self._init_path(path)
        try:
            with open(path, mode='rb') as f:
                d = f.read()
        except Exception:
            raise exceptions.FileNotFoundError('%s is not there' % path)

        return d

    @lru.set
    def put_content(self, path, content):
        path = self._init_path(path, create=True)
        with open(path, mode='wb') as f:
            f.write(content)
        return path

    def stream_read(self, path, bytes_range=None):
        path = self._init_path(path)
        nb_bytes = 0
        total_size = 0
        try:
            with open(path, mode='rb') as f:
                if bytes_range:
                    f.seek(bytes_range[0])
                    total_size = bytes_range[1] - bytes_range[0] + 1
                while True:
                    buf = None
                    if bytes_range:
                        # Bytes Range is enabled
                        buf_size = self.buffer_size
                        if nb_bytes + buf_size > total_size:
                            # We make sure we don't read out of the range
                            buf_size = total_size - nb_bytes
                        if buf_size > 0:
                            buf = f.read(buf_size)
                            nb_bytes += len(buf)
                        else:
                            # We're at the end of the range
                            buf = ''
                    else:
                        buf = f.read(self.buffer_size)
                    if not buf:
                        break
                    yield buf
        except IOError:
            raise exceptions.FileNotFoundError('%s is not there' % path)

    def stream_write(self, path, fp):
        # Size is mandatory
        path = self._init_path(path, create=True)
        with open(path, mode='wb') as f:
            try:
                while True:
                    buf = fp.read(self.buffer_size)
                    if not buf:
                        break
                    f.write(buf)
            except IOError:
                pass

    def list_directory(self, path=None):
        prefix = ''
        if path:
            prefix = '%s/' % path
        path = self._init_path(path)
        exists = False
        try:
            for d in os.listdir(path):
                exists = True
                yield prefix + d
        except Exception:
            pass
        if not exists:
            raise exceptions.FileNotFoundError('%s is not there' % path)

    def exists(self, path):
        path = self._init_path(path)
        return os.path.exists(path)

    @lru.remove
    def remove(self, path):
        path = self._init_path(path)
        if os.path.isdir(path):
            shutil.rmtree(path)
            return
        try:
            os.remove(path)
        except OSError:
            raise exceptions.FileNotFoundError('%s is not there' % path)

    def get_size(self, path):
        path = self._init_path(path)
        try:
            return os.path.getsize(path)
        except OSError:
            raise exceptions.FileNotFoundError('%s is not there' % path)

########NEW FILE########
__FILENAME__ = driver
# -*- coding: utf-8 -*-
# Copyright (c) 2014 Docker.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import logging
import math
import random
import string

from nose import tools

from ..core import compat
from ..core import driver
from ..core import exceptions

logger = logging.getLogger(__name__)


class Driver(object):

    def __init__(self, scheme=None, path=None, config=None):
        self.scheme = scheme
        self.path = path
        self.config = config

    # Load the requested driver
    def setUp(self):
        storage = driver.fetch(self.scheme)
        self._storage = storage(self.path, self.config)

    def tearDown(self):
        pass

    def gen_random_string(self, length=16):
        return ''.join([random.choice(string.ascii_uppercase + string.digits)
                        for x in range(length)]).lower()

    def simplehelp(self, path, content, expected, size=0):
        self._storage.put_content(path, content)
        assert self._storage.get_content(path) == expected
        assert self._storage.get_content(path) == expected
        if size:
            assert self._storage.get_size(path) == size

    def unicodehelp(self, path, content, expected):
        self._storage.put_unicode(path, content)
        assert self._storage.get_unicode(path) == expected
        assert self._storage.get_unicode(path) == expected

    def jsonhelp(self, path, content, expected):
        self._storage.put_json(path, content)
        assert self._storage.get_json(path) == expected
        assert self._storage.get_json(path) == expected

    def test_exists_non_existent(self):
        filename = self.gen_random_string()
        assert not self._storage.exists(filename)

    def test_exists_existent(self):
        filename = self.gen_random_string()
        self._storage.put_content(filename, b'')
        assert self._storage.exists(filename)

    # get / put
    def test_write_read_1(self):
        filename = self.gen_random_string()
        content = b'a'
        expected = b'a'
        self.simplehelp(filename, content, expected, len(expected))

    def test_write_read_2(self):
        filename = self.gen_random_string()
        content = b'\xc3\x9f'
        expected = b'\xc3\x9f'
        self.simplehelp(filename, content, expected, len(expected))

    def test_write_read_3(self):
        filename = self.gen_random_string()
        content = u'ß'.encode('utf8')
        expected = b'\xc3\x9f'
        self.simplehelp(filename, content, expected, len(expected))

    def test_write_read_4(self):
        filename = self.gen_random_string()
        content = 'ß'
        if compat.is_py2:
            content = content.decode('utf8')
        content = content.encode('utf8')
        expected = b'\xc3\x9f'
        self.simplehelp(filename, content, expected, len(expected))

    def test_write_read_5(self):
        filename = self.gen_random_string()
        content = self.gen_random_string().encode('utf8')
        expected = content
        self.simplehelp(filename, content, expected, len(expected))

    def test_write_read_6(self):
        filename = self.gen_random_string()
        content = self.gen_random_string(1024 * 1024).encode('utf8')
        expected = content
        self.simplehelp(filename, content, expected, len(expected))

    # get / put unicode
    def test_unicode_1(self):
        filename = self.gen_random_string()
        content = 'a'
        expected = u'a'
        self.unicodehelp(filename, content, expected)

    def test_unicode_2(self):
        filename = self.gen_random_string()
        content = b'\xc3\x9f'.decode('utf8')
        expected = u'ß'
        self.unicodehelp(filename, content, expected)

    def test_unicode_3(self):
        filename = self.gen_random_string()
        content = u'ß'
        expected = u'ß'
        self.unicodehelp(filename, content, expected)

    def test_unicode_4(self):
        filename = self.gen_random_string()
        content = 'ß'
        if compat.is_py2:
            content = content.decode('utf8')
        expected = u'ß'
        self.unicodehelp(filename, content, expected)

    def test_unicode_5(self):
        filename = self.gen_random_string()
        content = self.gen_random_string()
        expected = content
        self.unicodehelp(filename, content, expected)

    def test_unicode_6(self):
        filename = self.gen_random_string()
        content = self.gen_random_string(1024 * 1024)
        expected = content
        self.unicodehelp(filename, content, expected)

    # JSON
    def test_json(self):
        filename = self.gen_random_string()
        content = {u"ß": u"ß"}
        expected = {u"ß": u"ß"}
        self.jsonhelp(filename, content, expected)

    # Removes
    def test_remove_existent(self):
        filename = self.gen_random_string()
        content = self.gen_random_string().encode('utf8')
        self._storage.put_content(filename, content)
        self._storage.remove(filename)
        assert not self._storage.exists(filename)

    @tools.raises(exceptions.FileNotFoundError)
    def test_remove_inexistent(self):
        filename = self.gen_random_string()
        self._storage.remove(filename)

    @tools.raises(exceptions.FileNotFoundError)
    def test_read_inexistent(self):
        filename = self.gen_random_string()
        self._storage.get_content(filename)

    @tools.raises(exceptions.FileNotFoundError)
    def test_get_size_inexistent(self):
        filename = self.gen_random_string()
        self._storage.get_size(filename)

    def test_stream(self):
        filename = self.gen_random_string()
        # test 7MB
        content = self.gen_random_string(7).encode('utf8')  # * 1024 * 1024
        # test exists
        io = compat.StringIO(content)
        logger.debug("%s should NOT exists still" % filename)
        assert not self._storage.exists(filename)

        self._storage.stream_write(filename, io)
        io.close()

        logger.debug("%s should exist now" % filename)
        assert self._storage.exists(filename)

        # test read / write
        data = compat.bytes()
        for buf in self._storage.stream_read(filename):
            data += buf

        assert content == data

        # test bytes_range only if the storage backend suppports it
        if self._storage.supports_bytes_range:
            b = random.randint(0, math.floor(len(content) / 2))
            bytes_range = (b, random.randint(b + 1, len(content) - 1))
            data = compat.bytes()
            for buf in self._storage.stream_read(filename, bytes_range):
                data += buf
            expected_content = content[bytes_range[0]:bytes_range[1] + 1]
            assert data == expected_content

        # logger.debug("Content length is %s" % len(content))
        # logger.debug("And retrieved content length should equal it: %s" %
        #              len(data))
        # logger.debug("got content %s" % content)
        # logger.debug("got data %s" % data)

        # test remove
        self._storage.remove(filename)
        assert not self._storage.exists(filename)

    @tools.raises(exceptions.FileNotFoundError)
    def test_stream_read_inexistent(self):
        filename = self.gen_random_string()
        data = compat.bytes()
        for buf in self._storage.stream_read(filename):
            data += buf

    @tools.raises(exceptions.FileNotFoundError)
    def test_inexistent_list_directory(self):
        notexist = self.gen_random_string()
        iterator = self._storage.list_directory(notexist)
        next(iterator)

    # XXX only elliptics return StopIteration for now - though we should
    # return probably that for all
    @tools.raises(exceptions.FileNotFoundError, StopIteration)
    def test_empty_list_directory(self):
        path = self.gen_random_string()
        content = self.gen_random_string().encode('utf8')
        self._storage.put_content(path, content)

        iterator = self._storage.list_directory(path)
        next(iterator)

    def test_list_directory(self):
        base = self.gen_random_string()
        filename1 = self.gen_random_string()
        filename2 = self.gen_random_string()
        fb1 = '%s/%s' % (base, filename1)
        fb2 = '%s/%s' % (base, filename2)
        content = self.gen_random_string().encode('utf8')
        self._storage.put_content(fb1, content)
        self._storage.put_content(fb2, content)
        assert sorted([fb1, fb2]
                      ) == sorted(list(self._storage.list_directory(base)))

    # def test_root_list_directory(self):
    #     fb1 = self.gen_random_string()
    #     fb2 = self.gen_random_string()
    #     content = self.gen_random_string()
    #     self._storage.put_content(fb1, content)
    #     self._storage.put_content(fb2, content)
    #     print(list(self._storage.list_directory()))
    #     assert sorted([fb1, fb2]
    #                   ) == sorted(list(self._storage.list_directory()))

    @tools.raises(exceptions.FileNotFoundError, StopIteration)
    def test_empty_after_remove_list_directory(self):
        base = self.gen_random_string()
        filename1 = self.gen_random_string()
        filename2 = self.gen_random_string()
        fb1 = '%s/%s' % (base, filename1)
        fb2 = '%s/%s' % (base, filename2)
        content = self.gen_random_string().encode('utf8')
        self._storage.put_content(fb1, content)
        self._storage.put_content(fb2, content)

        self._storage.remove(fb1)
        self._storage.remove(fb2)

        iterator = self._storage.list_directory(base)
        next(iterator)

    def test_paths(self):
        namespace = 'namespace'
        repository = 'repository'
        tag = 'sometag'
        image_id = 'imageid'
        p = self._storage.images_list_path(namespace, repository)
        assert not self._storage.exists(p)
        p = self._storage.image_json_path(image_id)
        assert not self._storage.exists(p)
        p = self._storage.image_mark_path(image_id)
        assert not self._storage.exists(p)
        p = self._storage.image_checksum_path(image_id)
        assert not self._storage.exists(p)
        p = self._storage.image_layer_path(image_id)
        assert not self._storage.exists(p)
        p = self._storage.image_ancestry_path(image_id)
        assert not self._storage.exists(p)
        p = self._storage.image_files_path(image_id)
        assert not self._storage.exists(p)
        p = self._storage.image_diff_path(image_id)
        assert not self._storage.exists(p)
        p = self._storage.repository_path(namespace, repository)
        assert not self._storage.exists(p)
        p = self._storage.tag_path(namespace, repository)
        assert not self._storage.exists(p)
        p = self._storage.tag_path(namespace, repository, tag)
        assert not self._storage.exists(p)
        p = self._storage.repository_json_path(namespace, repository)
        assert not self._storage.exists(p)
        p = self._storage.repository_tag_json_path(namespace, repository, tag)
        assert not self._storage.exists(p)
        p = self._storage.index_images_path(namespace, repository)
        assert not self._storage.exists(p)
        p = self._storage.private_flag_path(namespace, repository)
        assert not self._storage.exists(p)

########NEW FILE########
__FILENAME__ = mock_boto
# -*- coding: utf-8 -*-
# Copyright (c) 2014 Docker.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

'''Monkeypatch s3 boto library for unittesting.
XXX this mock is crass and break gcs.
Look into moto instead.'''

import boto.s3.bucket
import boto.s3.connection
import boto.s3.key

from . import mock_dict
from . import utils

Bucket__init__ = boto.s3.bucket.Bucket.__init__


class MultiPartUpload(boto.s3.multipart.MultiPartUpload):
    __metaclass__ = utils.monkeypatch_class

    def upload_part_from_file(self, io, num_part):
        if num_part == 1:
            self.bucket._bucket[self.bucket.name][self._tmp_key] = io.read()
        else:
            self.bucket._bucket[self.bucket.name][self._tmp_key] += io.read()

    def complete_upload(self):
        return None


class S3Connection(boto.s3.connection.S3Connection):
    __metaclass__ = utils.monkeypatch_class

    def __init__(self, *args, **kwargs):
        return None

    def get_bucket(self, name, **kwargs):
        # Create a bucket for testing
        bucket = Bucket(connection=self, name=name, key_class=Key)
        return bucket

    def make_request(self, *args, **kwargs):
        return 'request result'


class Bucket(boto.s3.bucket.Bucket):
    __metaclass__ = utils.monkeypatch_class

    _bucket = mock_dict.MockDict()
    _bucket.add_dict_methods()

    @property
    def _bucket_dict(self):
        if self.name in Bucket._bucket:
            return Bucket._bucket[self.name]._mock_dict

    def __init__(self, *args, **kwargs):
        Bucket__init__(self, *args, **kwargs)
        Bucket._bucket[self.name] = mock_dict.MockDict()
        Bucket._bucket[self.name].add_dict_methods()

    def delete(self):
        if self.name in Bucket._bucket:
            Bucket._bucket[self.name] = mock_dict.MockDict()
            Bucket._bucket[self.name].add_dict_methods()

    def list(self, **kwargs):
        return ([self.lookup(k) for k in self._bucket_dict.keys()]
                if self._bucket_dict else [])

    def lookup(self, key_name, **kwargs):
        if self._bucket_dict and key_name in self._bucket_dict:
            value = Bucket._bucket[self.name][key_name]
            k = Key(self)
            k.name = key_name
            k.size = len(value)
            return k

    def initiate_multipart_upload(self, key_name, **kwargs):
        # Pass key_name to MultiPartUpload
        mp = MultiPartUpload(self)
        mp._tmp_key = key_name
        return mp


class Key(boto.s3.key.Key):
    __metaclass__ = utils.monkeypatch_class

    def exists(self):
        bucket_dict = self.bucket._bucket_dict
        return self.name in bucket_dict if bucket_dict else False

    def delete(self):
        del self.bucket._bucket_dict[self.name]

    def set_contents_from_string(self, value, **kwargs):
        self.size = len(value)
        self.bucket._bucket_dict[self.name] = value

    def get_contents_as_string(self, *args, **kwargs):
        return self.bucket._bucket_dict[self.name]

    def get_contents_to_file(self, fp, **kwargs):
        min_cur, max_cur = (kwargs['headers']['Range'].replace('bytes=', '')
                            .split('-'))
        value = self.bucket._bucket_dict[self.name]
        fp.write(value[int(min_cur):int(max_cur) + 1])
        fp.flush()

    def read(self, buffer_size):
        # fetch read status
        lp = getattr(self, '_last_position', 0)
        self._last_position = lp + buffer_size
        return self.bucket._bucket_dict[self.name][lp:lp + buffer_size]

########NEW FILE########
__FILENAME__ = mock_dict
# -*- coding: utf-8 -*-
# Copyright (c) 2014 Docker.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

'''Extend Mock class with dictionary behavior.
   Call it as:
       mocked_dict = MockDict()
       mocked_dict.add_dict_methods()'''

import mock

MagicMock__init__ = mock.MagicMock.__init__


class MockDict(mock.MagicMock):

    def __init__(self, *args, **kwargs):
        MagicMock__init__(self, *args, **kwargs)
        self._mock_dict = {}

    @property
    def get_dict(self):
        return self._mock_dict

    def add_dict_methods(self):
        def setitem(key, value):
            self._mock_dict[key] = value

        def delitem(key):
            del self._mock_dict[key]

        self.__getitem__.side_effect = lambda key: self._mock_dict[key]
        self.__setitem__.side_effect = setitem
        self.__delitem__.side_effect = delitem
        self.__contains__.side_effect = lambda key: key in self._mock_dict

########NEW FILE########
__FILENAME__ = query
# -*- coding: utf-8 -*-
# Copyright (c) 2014 Docker.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from nose import tools

from ..core import driver
from ..core import exceptions


class Query(object):

    def __init__(self, scheme=None):
        self.scheme = scheme

    def testDriverIsAvailable(self):
        drvs = driver.available()
        assert self.scheme in drvs

    def testFetchingDriver(self):
        resultdriver = driver.fetch(self.scheme)
        # XXX hacking is sick
        storage = __import__('docker_registry.drivers.%s' % self.scheme,
                             globals(), locals(), ['Storage'], 0)  # noqa

        assert resultdriver == storage.Storage
        assert issubclass(resultdriver, driver.Base)
        assert resultdriver.scheme == self.scheme

    @tools.raises(exceptions.NotImplementedError)
    def testFetchingNonExistentDriver(self):
        driver.fetch("nonexistentstupidlynameddriver")

########NEW FILE########
__FILENAME__ = utils
# -*- coding: utf-8 -*-
# Copyright (c) 2014 Docker.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.


def monkeypatch_method(cls):
    '''Guido's monkeypatch decorator.'''
    def decorator(func):
        setattr(cls, func.__name__, func)
        return func
    return decorator


def monkeypatch_class(name, bases, namespace):
    '''Guido's monkeypatch metaclass.'''
    assert len(bases) == 1, "Exactly one base class required"
    base = bases[0]
    for name, value in namespace.iteritems():
        if name != "__metaclass__":
            setattr(base, name, value)
    return base


class Config(object):

    def __init__(self, config):
        self._config = config

    def __repr__(self):
        return repr(self._config)

    def __getattr__(self, key):
        if key in self._config:
            return self._config[key]

    def get(self, *args, **kwargs):
        return self._config.get(*args, **kwargs)

########NEW FILE########
__FILENAME__ = test_driver
# -*- coding: utf-8 -*-
# Copyright (c) 2014 Docker.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from docker_registry import testing


class TestQueryDumb(testing.Query):
    def __init__(self):
        self.scheme = 'dumb'


class TestDriverDumb(testing.Driver):
    def __init__(self):
        self.scheme = 'dumb'
        self.path = ''
        self.config = testing.Config({})


class TestQueryFile(testing.Query):
    def __init__(self):
        self.scheme = 'file'


class TestDriverFile(testing.Driver):
    def __init__(self):
        self.scheme = 'file'
        self.path = ''
        self.config = testing.Config({})

########NEW FILE########
__FILENAME__ = test_lru
# -*- coding: utf-8 -*-
# Copyright (c) 2014 Docker.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from docker_registry.core import compat
from docker_registry.core import lru

# In case you want to mock (and that doesn't work well)
# import mock
# import mockredis
# @mock.patch('docker_registry.core.lru.redis.StrictRedis',
#             mockredis.mock_strict_redis_client)
# def boot():
#     lru.init()

# boot()

lru.init()


class Dumb(object):

    value = {}

    @lru.get
    def get(self, key):
        if key not in self.value:
            return None
        return self.value[key]

    @lru.set
    def set(self, key, value):
        self.value[key] = value

    @lru.remove
    def remove(self, key):
        if key not in self.value:
            return
        del self.value[key]


class TestLru(object):

    def setUp(self):
        self._dumb = Dumb()

    def testNonExistentGet(self):
        assert not self._dumb.get('nonexistent')
        assert not self._dumb.get('nonexistent')

    def testSetSimple1(self):
        content = 'bar'
        result = b'bar'
        self._dumb.set('foo', content)
        assert self._dumb.get('foo') == result
        assert self._dumb.get('foo') == result

    def testSetBytes1(self):
        content = b'foo'
        result = b'foo'
        self._dumb.set('foo', content)
        assert self._dumb.get('foo') == result

    def testSetBytes2(self):
        content = b'\xc3\x9f'
        result = b'\xc3\x9f'
        self._dumb.set('foo', content)
        assert self._dumb.get('foo') == result

    def testSetUnicode1(self):
        content = u'foo'
        result = b'foo'
        self._dumb.set('foo', content)
        assert self._dumb.get('foo') == result

    def testSetUnicode2(self):
        content = u'ß'
        result = b'\xc3\x9f'
        self._dumb.set('foo', content)
        assert self._dumb.get('foo') == result

    def testSetUnicode3(self):
        content = u'ß'.encode('utf8')
        result = b'\xc3\x9f'
        self._dumb.set('foo', content)
        assert self._dumb.get('foo') == result

    def testSetUnicode4(self):
        content = 'ß'
        if compat.is_py2:
            content = content.decode('utf8')
        content = content.encode('utf8')
        result = b'\xc3\x9f'
        self._dumb.set('foo', content)
        assert self._dumb.get('foo') == result

    def testRemove(self):
        self._dumb.set('foo', 'bar')
        assert self._dumb.get('foo')
        self._dumb.remove('foo')
        assert not self._dumb.get('foo')
        assert not self._dumb.get('foo')

########NEW FILE########
__FILENAME__ = app
# -*- coding: utf-8 -*-

import logging
import logging.handlers
import os

try:
    import bugsnag
    import bugsnag.flask
except ImportError as e:
    _bugsnag_import_error = e
    bugsnag = None
import flask

from . import toolkit
from .lib import config

VERSION = '0.7.0'
app = flask.Flask('docker-registry')
cfg = config.load()
loglevel = getattr(logging, cfg.get('loglevel', 'INFO').upper())
logging.basicConfig(format='%(asctime)s %(levelname)s: %(message)s',
                    level=loglevel)


@app.route('/_ping')
@app.route('/v1/_ping')
def ping():
    return toolkit.response(headers={
        'X-Docker-Registry-Standalone': cfg.standalone is not False
    })


@app.route('/')
def root():
    return toolkit.response('docker-registry server ({0}) (v{1})'
                            .format(cfg.flavor, VERSION))


@app.after_request
def after_request(response):
    response.headers['X-Docker-Registry-Version'] = VERSION
    response.headers['X-Docker-Registry-Config'] = cfg.flavor
    return response


def init():
    # Configure the email exceptions
    info = cfg.email_exceptions
    if info and 'smtp_host' in info:
        mailhost = info['smtp_host']
        mailport = info.get('smtp_port')
        if mailport:
            mailhost = (mailhost, mailport)
        smtp_secure = info.get('smtp_secure', None)
        secure_args = _adapt_smtp_secure(smtp_secure)
        mail_handler = logging.handlers.SMTPHandler(
            mailhost=mailhost,
            fromaddr=info['from_addr'],
            toaddrs=[info['to_addr']],
            subject='Docker registry exception',
            credentials=(info['smtp_login'],
                         info['smtp_password']),
            secure=secure_args)
        mail_handler.setLevel(logging.ERROR)
        app.logger.addHandler(mail_handler)
    # Configure bugsnag
    info = cfg.bugsnag
    if info:
        if not bugsnag:
            raise _bugsnag_import_error
        root_path = os.path.abspath(os.path.join(os.path.dirname(__file__),
                                                 '..'))
        bugsnag.configure(api_key=info,
                          project_root=root_path,
                          release_stage=cfg.flavor,
                          notify_release_stages=[cfg.flavor],
                          app_version=VERSION
                          )
        bugsnag.flask.handle_exceptions(app)


def _adapt_smtp_secure(value):
    """Adapt the value to arguments of ``SMTP.starttls()``

    .. seealso:: <http://docs.python.org/2/library/smtplib.html\
#smtplib.SMTP.starttls>

    """
    if isinstance(value, basestring):
        # a string - wrap it in the tuple
        return (value,)
    if isinstance(value, dict):
        assert set(value.keys()) <= set(['keyfile', 'certfile'])
        return (value['keyfile'], value.get('certfile', None))
    if value:
        return ()


init()

########NEW FILE########
__FILENAME__ = s3
# -*- coding: utf-8 -*-
"""
docker_registry.drivers.s3
~~~~~~~~~~~~~~~~~~~~~~~~~~

This is a s3 based driver.

"""

import gevent.monkey
gevent.monkey.patch_all()

import docker_registry.core.boto as coreboto
# from docker_registry.core import exceptions
from docker_registry.core import compat
from docker_registry.core import lru

import logging
import os
import re
import time

import boto.exception
import boto.s3
import boto.s3.connection
import boto.s3.key

logger = logging.getLogger(__name__)


class Cloudfront():
    def __init__(self, awsaccess, awssecret, base, keyid, privatekey):
        boto.connect_cloudfront(
            awsaccess,
            awssecret
        )
        host = re.compile('^https?://([^/]+)').findall(base)
        self.dist = boto.cloudfront.distribution.Distribution(domain_name=host)
        self.base = base
        self.keyid = keyid
        self.privatekey = privatekey
        try:
            self.privatekey = open(privatekey).read()
        except Exception:
            logger.debug('Passed private key is not readable. Assume string.')

    def sign(self, url, expire_time=0):
        path = os.path.join(self.base, url)
        if expire_time:
            expire_time = time.time() + expire_time
        return self.dist.create_signed_url(
            path,
            self.keyid,
            private_key_string=self.privatekey,
            expire_time=int(expire_time)
        )

    def pub(self, path):
        return os.path.join(self.base, path)


class Storage(coreboto.Base):

    def __init__(self, path, config):
        super(Storage, self).__init__(path, config)

    def _build_connection_params(self):
        kwargs = super(Storage, self)._build_connection_params()
        if self._config.s3_secure is not None:
            kwargs['is_secure'] = (self._config.s3_secure is True)
        return kwargs

    def makeConnection(self):
        kwargs = self._build_connection_params()
        if self._config.s3_region is not None:
            return boto.s3.connect_to_region(
                region_name=self._config.s3_region,
                aws_access_key_id=self._config.s3_access_key,
                aws_secret_access_key=self._config.s3_secret_key,
                **kwargs)
        logger.warn("No S3 region specified, using boto default region, " +
                    "this may affect performance and stability.")
        # Connect cloudfront if we are required to
        if self._config.cloudfront:
            self.signer = Cloudfront(
                self._config.s3_access_key,
                self._config.s3_secret_key,
                self._config.cloudfront['base'],
                self._config.cloudfront['keyid'],
                self._config.cloudfront['keysecret']
            ).sign

        return boto.s3.connection.S3Connection(
            self._config.s3_access_key,
            self._config.s3_secret_key,
            **kwargs)

    def makeKey(self, path):
        return boto.s3.key.Key(self._boto_bucket, path)

    @lru.set
    def put_content(self, path, content):
        path = self._init_path(path)
        key = self.makeKey(path)
        key.set_contents_from_string(
            content, encrypt_key=(self._config.s3_encrypt is True))
        return path

    def stream_write(self, path, fp):
        # Minimum size of upload part size on S3 is 5MB
        buffer_size = 5 * 1024 * 1024
        if self.buffer_size > buffer_size:
            buffer_size = self.buffer_size
        path = self._init_path(path)
        mp = self._boto_bucket.initiate_multipart_upload(
            path, encrypt_key=(self._config.s3_encrypt is True))
        num_part = 1
        try:
            while True:
                buf = fp.read(buffer_size)
                if not buf:
                    break
                io = compat.StringIO(buf)
                mp.upload_part_from_file(io, num_part)
                num_part += 1
                io.close()
        except IOError as e:
            raise e
        mp.complete_upload()

    def content_redirect_url(self, path):
        path = self._init_path(path)
        key = self.makeKey(path)
        if not key.exists():
            raise IOError('No such key: \'{0}\''.format(path))

        # No cloudfront? Sign to the bucket
        if not self.signer:
            return key.generate_url(
                expires_in=1200,
                method='GET',
                query_auth=True)

        # Have cloudfront? Sign it
        return self.signer(path, expire_time=60)

########NEW FILE########
__FILENAME__ = images
# -*- coding: utf-8 -*-

import datetime
import functools
import logging
import tarfile
import time

import flask

from docker_registry.core import compat
from docker_registry.core import exceptions
json = compat.json

from . import storage
from . import toolkit
from .app import app
from .app import cfg
from .lib import cache
from .lib import checksums
from .lib import layers
from .lib import mirroring


store = storage.load()
logger = logging.getLogger(__name__)


def require_completion(f):
    """This make sure that the image push correctly finished."""
    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        if store.exists(store.image_mark_path(kwargs['image_id'])):
            return toolkit.api_error('Image is being uploaded, retry later')
        return f(*args, **kwargs)
    return wrapper


def set_cache_headers(f):
    """Returns HTTP headers suitable for caching."""
    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        # Set TTL to 1 year by default
        ttl = 31536000
        expires = datetime.datetime.fromtimestamp(int(time.time()) + ttl)
        expires = expires.strftime('%a, %d %b %Y %H:%M:%S GMT')
        headers = {
            'Cache-Control': 'public, max-age={0}'.format(ttl),
            'Expires': expires,
            'Last-Modified': 'Thu, 01 Jan 1970 00:00:00 GMT',
        }
        if 'If-Modified-Since' in flask.request.headers:
            return flask.Response(status=304, headers=headers)
        kwargs['headers'] = headers
        # Prevent the Cookie to be sent when the object is cacheable
        return f(*args, **kwargs)
    return wrapper


def _get_image_layer(image_id, headers=None, bytes_range=None):
    if headers is None:
        headers = {}

    headers['Content-Type'] = 'application/octet-stream'
    accel_uri_prefix = cfg.nginx_x_accel_redirect
    path = store.image_layer_path(image_id)
    if accel_uri_prefix:
        if store.scheme == 'file':
            accel_uri = '/'.join([accel_uri_prefix, path])
            headers['X-Accel-Redirect'] = accel_uri
            logger.debug('send accelerated {0} ({1})'.format(
                accel_uri, headers))
            return flask.Response('', headers=headers)
        else:
            logger.warn('nginx_x_accel_redirect config set,'
                        ' but storage is not LocalStorage')

    # If store allows us to just redirect the client let's do that, we'll
    # offload a lot of expensive I/O and get faster I/O
    if cfg.storage_redirect:
        try:
            content_redirect_url = store.content_redirect_url(path)
            if content_redirect_url:
                return flask.redirect(content_redirect_url, 302)
        except IOError as e:
            logger.debug(str(e))

    status = None
    layer_size = 0

    if not store.exists(path):
        raise exceptions.FileNotFoundError("Image layer absent from store")
    try:
        layer_size = store.get_size(path)
    except exceptions.FileNotFoundError:
        # XXX why would that fail given we know the layer exists?
        pass
    if bytes_range and bytes_range[1] == -1 and not layer_size == 0:
        bytes_range = (bytes_range[0], layer_size)

    if bytes_range:
        content_length = bytes_range[1] - bytes_range[0] + 1
        if not _valid_bytes_range(bytes_range):
            return flask.Response(status=416, headers=headers)
        status = 206
        content_range = (bytes_range[0], bytes_range[1], layer_size)
        headers['Content-Range'] = '{0}-{1}/{2}'.format(*content_range)
        headers['Content-Length'] = content_length
    elif layer_size > 0:
        headers['Content-Length'] = layer_size
    else:
        return flask.Response(status=416, headers=headers)
    return flask.Response(store.stream_read(path, bytes_range),
                          headers=headers, status=status)


def _get_image_json(image_id, headers=None):
    if headers is None:
        headers = {}
    data = store.get_content(store.image_json_path(image_id))
    try:
        size = store.get_size(store.image_layer_path(image_id))
        headers['X-Docker-Size'] = str(size)
    except exceptions.FileNotFoundError:
        pass
    try:
        csums = load_checksums(image_id)
        headers['X-Docker-Payload-Checksum'] = csums
    except exceptions.FileNotFoundError:
        pass
    return toolkit.response(data, headers=headers, raw=True)


def _parse_bytes_range():
    headers = flask.request.headers
    range_header = headers.get('range')
    if not range_header:
        return
    log_msg = ('_parse_bytes_range: Malformed bytes range request header: '
               '{0}'.format(range_header))
    if not range_header.startswith('bytes='):
        logger.debug(log_msg)
        return
    bytes_range = range_header[6:].split('-')
    if len(bytes_range) != 2 and not range_header[-1] == '-':
        logger.debug(log_msg)
        return
    if len(bytes_range) == 1 or bytes_range[1] == '':
        bytes_range = (bytes_range[0], -1)
        try:
            return (int(bytes_range[0]), -1)
        except ValueError:
            logger.debug(log_msg)
    try:
        return (int(bytes_range[0]), int(bytes_range[1]))
    except ValueError:
        logger.debug(log_msg)


def _valid_bytes_range(bytes_range):
    length = bytes_range[1] - bytes_range[0] + 1
    if bytes_range[0] < 0 or bytes_range[1] < 1:
        return False
    if length < 2:
        return False
    return True


@app.route('/v1/private_images/<image_id>/layer', methods=['GET'])
@toolkit.requires_auth
@require_completion
def get_private_image_layer(image_id):
    try:
        headers = None
        bytes_range = None
        if store.supports_bytes_range:
            headers['Accept-Ranges'] = 'bytes'
            bytes_range = _parse_bytes_range()
        repository = toolkit.get_repository()
        if not repository:
            # No auth token found, either standalone registry or privileged
            # access. In both cases, private images are "disabled"
            return toolkit.api_error('Image not found', 404)
        if not store.is_private(*repository):
            return toolkit.api_error('Image not found', 404)
        return _get_image_layer(image_id, headers, bytes_range)
    except exceptions.FileNotFoundError:
        return toolkit.api_error('Image not found', 404)


@app.route('/v1/images/<image_id>/layer', methods=['GET'])
@toolkit.requires_auth
@require_completion
@set_cache_headers
@mirroring.source_lookup(cache=True, stream=True)
def get_image_layer(image_id, headers):
    try:
        bytes_range = None
        if store.supports_bytes_range:
            headers['Accept-Ranges'] = 'bytes'
            bytes_range = _parse_bytes_range()
        repository = toolkit.get_repository()
        if repository and store.is_private(*repository):
            return toolkit.api_error('Image not found', 404)
        # If no auth token found, either standalone registry or privileged
        # access. In both cases, access is always "public".
        return _get_image_layer(image_id, headers, bytes_range)
    except exceptions.FileNotFoundError:
        return toolkit.api_error('Image not found', 404)


@app.route('/v1/images/<image_id>/layer', methods=['PUT'])
@toolkit.requires_auth
def put_image_layer(image_id):
    try:
        json_data = store.get_content(store.image_json_path(image_id))
    except exceptions.FileNotFoundError:
        return toolkit.api_error('Image not found', 404)
    layer_path = store.image_layer_path(image_id)
    mark_path = store.image_mark_path(image_id)
    if store.exists(layer_path) and not store.exists(mark_path):
        return toolkit.api_error('Image already exists', 409)
    input_stream = flask.request.stream
    if flask.request.headers.get('transfer-encoding') == 'chunked':
        # Careful, might work only with WSGI servers supporting chunked
        # encoding (Gunicorn)
        input_stream = flask.request.environ['wsgi.input']
    # compute checksums
    csums = []
    sr = toolkit.SocketReader(input_stream)
    if toolkit.DockerVersion() < '0.10':
        tmp, store_hndlr = storage.temp_store_handler()
        sr.add_handler(store_hndlr)
    h, sum_hndlr = checksums.simple_checksum_handler(json_data)
    sr.add_handler(sum_hndlr)
    store.stream_write(layer_path, sr)
    csums.append('sha256:{0}'.format(h.hexdigest()))

    if toolkit.DockerVersion() < '0.10':
        # NOTE(samalba): After docker 0.10, the tarsum is not used to ensure
        # the image has been transfered correctly.
        logger.debug('put_image_layer: Tarsum is enabled')
        tar = None
        tarsum = checksums.TarSum(json_data)
        try:
            tmp.seek(0)
            tar = tarfile.open(mode='r|*', fileobj=tmp)
            tarfilesinfo = layers.TarFilesInfo()
            for member in tar:
                tarsum.append(member, tar)
                tarfilesinfo.append(member)
            layers.set_image_files_cache(image_id, tarfilesinfo.json())
        except (IOError, tarfile.TarError) as e:
            logger.debug('put_image_layer: Error when reading Tar stream '
                         'tarsum. Disabling TarSum, TarFilesInfo. '
                         'Error: {0}'.format(e))
        finally:
            if tar:
                tar.close()
            # All data have been consumed from the tempfile
            csums.append(tarsum.compute())
            tmp.close()

    # We store the computed checksums for a later check
    save_checksums(image_id, csums)
    return toolkit.response()


@app.route('/v1/images/<image_id>/checksum', methods=['PUT'])
@toolkit.requires_auth
def put_image_checksum(image_id):
    if toolkit.DockerVersion() < '0.10':
        checksum = flask.request.headers.get('X-Docker-Checksum')
    else:
        checksum = flask.request.headers.get('X-Docker-Checksum-Payload')
    if not checksum:
        return toolkit.api_error('Missing Image\'s checksum')
    if not store.exists(store.image_json_path(image_id)):
        return toolkit.api_error('Image not found', 404)
    mark_path = store.image_mark_path(image_id)
    if not store.exists(mark_path):
        return toolkit.api_error('Cannot set this image checksum', 409)
    checksums = load_checksums(image_id)
    if checksum not in checksums:
        logger.debug('put_image_checksum: Wrong checksum. '
                     'Provided: {0}; Expected: {1}'.format(
                         checksum, checksums))
        return toolkit.api_error('Checksum mismatch')
    # Checksum is ok, we remove the marker
    store.remove(mark_path)
    # We trigger a task on the diff worker if it's running
    if cache.redis_conn:
        layers.diff_queue.push(image_id)
    return toolkit.response()


@app.route('/v1/private_images/<image_id>/json', methods=['GET'])
@toolkit.requires_auth
@require_completion
def get_private_image_json(image_id):
    repository = toolkit.get_repository()
    if not repository:
        # No auth token found, either standalone registry or privileged access
        # In both cases, private images are "disabled"
        return toolkit.api_error('Image not found', 404)
    try:
        if not store.is_private(*repository):
            return toolkit.api_error('Image not found', 404)
        return _get_image_json(image_id)
    except exceptions.FileNotFoundError:
        return toolkit.api_error('Image not found', 404)


@app.route('/v1/images/<image_id>/json', methods=['GET'])
@toolkit.requires_auth
@require_completion
@set_cache_headers
@mirroring.source_lookup(cache=True, stream=False)
def get_image_json(image_id, headers):
    try:
        repository = toolkit.get_repository()
        if repository and store.is_private(*repository):
            return toolkit.api_error('Image not found', 404)
        # If no auth token found, either standalone registry or privileged
        # access. In both cases, access is always "public".
        return _get_image_json(image_id, headers)
    except exceptions.FileNotFoundError:
        return toolkit.api_error('Image not found', 404)


@app.route('/v1/images/<image_id>/ancestry', methods=['GET'])
@toolkit.requires_auth
@require_completion
@set_cache_headers
@mirroring.source_lookup(cache=True, stream=False)
def get_image_ancestry(image_id, headers):
    ancestry_path = store.image_ancestry_path(image_id)
    try:
        # Note(dmp): unicode patch
        data = store.get_json(ancestry_path)
    except exceptions.FileNotFoundError:
        return toolkit.api_error('Image not found', 404)
    return toolkit.response(data, headers=headers)


def check_images_list(image_id):
    if cfg.disable_token_auth is True or cfg.standalone is not False:
        # We enforce the check only when auth is enabled so we have a token.
        return True
    repository = toolkit.get_repository()
    try:
        path = store.images_list_path(*repository)
        # Note(dmp): unicode patch
        images_list = store.get_json(path)
    except exceptions.FileNotFoundError:
        return False
    return (image_id in images_list)


def save_checksums(image_id, checksums):
    for checksum in checksums:
        checksum_parts = checksum.split(':')
        if len(checksum_parts) != 2:
            return 'Invalid checksum format'
    # We store the checksum
    checksum_path = store.image_checksum_path(image_id)
    store.put_content(checksum_path, json.dumps(checksums))


def load_checksums(image_id):
    checksum_path = store.image_checksum_path(image_id)
    data = store.get_content(checksum_path)
    try:
        # Note(dmp): unicode patch NOT applied here
        return json.loads(data)
    except ValueError:
        # NOTE(sam): For backward compatibility only, existing data may not be
        # a valid json but a simple string.
        return [data]


@app.route('/v1/images/<image_id>/json', methods=['PUT'])
@toolkit.requires_auth
def put_image_json(image_id):
    try:
        # Note(dmp): unicode patch
        data = json.loads(flask.request.data.decode('utf8'))
    except ValueError:
        pass
    if not data or not isinstance(data, dict):
        return toolkit.api_error('Invalid JSON')
    if 'id' not in data:
        return toolkit.api_error('Missing key `id\' in JSON')
    if image_id != data['id']:
        return toolkit.api_error('JSON data contains invalid id')
    if check_images_list(image_id) is False:
        return toolkit.api_error('This image does not belong to the '
                                 'repository')
    parent_id = data.get('parent')
    if parent_id and not store.exists(store.image_json_path(data['parent'])):
        return toolkit.api_error('Image depends on a non existing parent')
    elif parent_id and not toolkit.validate_parent_access(parent_id):
        return toolkit.api_error('Image depends on an unauthorized parent')
    json_path = store.image_json_path(image_id)
    mark_path = store.image_mark_path(image_id)
    if store.exists(json_path) and not store.exists(mark_path):
        return toolkit.api_error('Image already exists', 409)
    # If we reach that point, it means that this is a new image or a retry
    # on a failed push
    store.put_content(mark_path, 'true')
    # We cleanup any old checksum in case it's a retry after a fail
    try:
        store.remove(store.image_checksum_path(image_id))
    except Exception:
        pass
    store.put_content(json_path, flask.request.data)
    layers.generate_ancestry(image_id, parent_id)
    return toolkit.response()


@app.route('/v1/private_images/<image_id>/files', methods=['GET'])
@toolkit.requires_auth
@require_completion
def get_private_image_files(image_id, headers):
    repository = toolkit.get_repository()
    if not repository:
        # No auth token found, either standalone registry or privileged access
        # In both cases, private images are "disabled"
        return toolkit.api_error('Image not found', 404)
    try:
        if not store.is_private(*repository):
            return toolkit.api_error('Image not found', 404)
        data = layers.get_image_files_json(image_id)
        return toolkit.response(data, headers=headers, raw=True)
    except exceptions.FileNotFoundError:
        return toolkit.api_error('Image not found', 404)
    except tarfile.TarError:
        return toolkit.api_error('Layer format not supported', 400)


@app.route('/v1/images/<image_id>/files', methods=['GET'])
@toolkit.requires_auth
@require_completion
@set_cache_headers
def get_image_files(image_id, headers):
    try:
        repository = toolkit.get_repository()
        if repository and store.is_private(*repository):
            return toolkit.api_error('Image not found', 404)
        # If no auth token found, either standalone registry or privileged
        # access. In both cases, access is always "public".
        data = layers.get_image_files_json(image_id)
        return toolkit.response(data, headers=headers, raw=True)
    except exceptions.FileNotFoundError:
        return toolkit.api_error('Image not found', 404)
    except tarfile.TarError:
        return toolkit.api_error('Layer format not supported', 400)


@app.route('/v1/images/<image_id>/diff', methods=['GET'])
@toolkit.requires_auth
@require_completion
@set_cache_headers
def get_image_diff(image_id, headers):
    try:
        if not cache.redis_conn:
            return toolkit.api_error('Diff queue is disabled', 400)
        repository = toolkit.get_repository()
        if repository and store.is_private(*repository):
            return toolkit.api_error('Image not found', 404)

        # first try the cache
        diff_json = layers.get_image_diff_cache(image_id)
        # it the cache misses, request a diff from a worker
        if not diff_json:
            layers.diff_queue.push(image_id)
            # empty response
            diff_json = ""

        return toolkit.response(diff_json, headers=headers, raw=True)
    except exceptions.FileNotFoundError:
        return toolkit.api_error('Image not found', 404)
    except tarfile.TarError:
        return toolkit.api_error('Layer format not supported', 400)

########NEW FILE########
__FILENAME__ = index
# -*- coding: utf-8 -*-

import logging

import flask
import flask_cors

from docker_registry.core import compat
from docker_registry.core import exceptions
json = compat.json

from . import storage
from . import toolkit
from .lib import mirroring
from .lib import signals

from .app import app


store = storage.load()
logger = logging.getLogger(__name__)

"""Those routes are loaded only when `standalone' is enabled in the config
   file. The goal is to make the Registry working without the central Index
   It's then possible to push images from Docker without talking to any other
   entities. This module mimics the Index.
"""


def generate_headers(namespace, repository, access):
    registry_endpoints = toolkit.get_endpoints()
    # The token generated will be invalid against a real Index behind.
    token = 'Token signature={0},repository="{1}/{2}",access={3}'.format(
            toolkit.gen_random_string(), namespace, repository, access)
    return {'X-Docker-Endpoints': registry_endpoints,
            'WWW-Authenticate': token,
            'X-Docker-Token': token}


@app.route('/v1/users', methods=['GET', 'POST'])
@app.route('/v1/users/', methods=['GET', 'POST'])
def get_post_users():
    if flask.request.method == 'GET':
        return toolkit.response('OK', 200)
    try:
        # Note(dmp): unicode patch
        json.loads(flask.request.data.decode('utf8'))
    except ValueError:
        return toolkit.api_error('Error Decoding JSON', 400)
    return toolkit.response('User Created', 201)


@app.route('/v1/users/<username>/', methods=['PUT'])
def put_username(username):
    return toolkit.response('', 204)


def update_index_images(namespace, repository, data):
    path = store.index_images_path(namespace, repository)
    sender = flask.current_app._get_current_object()
    try:
        images = {}
        # Note(dmp): unicode patch
        data = json.loads(data.decode('utf8')) + store.get_json(path)
        for i in data:
            iid = i['id']
            if iid in images and 'checksum' in images[iid]:
                continue
            i_data = {'id': iid}
            for key in ['checksum']:
                if key in i:
                    i_data[key] = i[key]
            images[iid] = i_data
        data = images.values()
        # Note(dmp): unicode patch
        store.put_json(path, data)
        signals.repository_updated.send(
            sender, namespace=namespace, repository=repository, value=data)
    except exceptions.FileNotFoundError:
        signals.repository_created.send(
            sender, namespace=namespace, repository=repository,
            # Note(dmp): unicode patch
            value=json.loads(data.decode('utf8')))
        store.put_content(path, data)


@app.route('/v1/repositories/<path:repository>', methods=['PUT'])
@app.route('/v1/repositories/<path:repository>/images',
           defaults={'images': True},
           methods=['PUT'])
@toolkit.parse_repository_name
@toolkit.requires_auth
def put_repository(namespace, repository, images=False):
    data = None
    try:
        # Note(dmp): unicode patch
        data = json.loads(flask.request.data.decode('utf8'))
    except ValueError:
        return toolkit.api_error('Error Decoding JSON', 400)
    if not isinstance(data, list):
        return toolkit.api_error('Invalid data')
    update_index_images(namespace, repository, flask.request.data)
    headers = generate_headers(namespace, repository, 'write')
    code = 204 if images is True else 200
    return toolkit.response('', code, headers)


@app.route('/v1/repositories/<path:repository>/images', methods=['GET'])
@flask_cors.cross_origin(methods=['GET'])  # allow all origins (*)
@toolkit.parse_repository_name
@toolkit.requires_auth
@mirroring.source_lookup(index_route=True)
def get_repository_images(namespace, repository):
    data = None
    try:
        path = store.index_images_path(namespace, repository)
        data = store.get_content(path)
    except exceptions.FileNotFoundError:
        return toolkit.api_error('images not found', 404)
    headers = generate_headers(namespace, repository, 'read')
    return toolkit.response(data, 200, headers, True)


@app.route('/v1/repositories/<path:repository>/images', methods=['DELETE'])
@toolkit.parse_repository_name
@toolkit.requires_auth
def delete_repository_images(namespace, repository):
    # Does nothing, this file will be removed when DELETE on repos
    headers = generate_headers(namespace, repository, 'delete')
    return toolkit.response('', 204, headers)


@app.route('/v1/repositories/<path:repository>/auth', methods=['PUT'])
@toolkit.parse_repository_name
def put_repository_auth(namespace, repository):
    return toolkit.response('OK')

########NEW FILE########
__FILENAME__ = cache
# -*- coding: utf-8 -*-

import logging

import redis

from docker_registry.core import lru

from . import config


# Default options

redis_opts = {
    'host': 'localhost',
    'port': 6379,
    'db': 0,
    'password': None
}
redis_conn = None
cache_prefix = None


def init():
    global redis_conn, cache_prefix
    cfg = config.load()
    cache = cfg.cache
    if not cache:
        return

    logging.info('Enabling storage cache on Redis')
    if not isinstance(cache, dict):
        cache = {}
    for k, v in cache.iteritems():
        redis_opts[k] = v
    logging.info('Redis config: {0}'.format(redis_opts))
    redis_conn = redis.StrictRedis(host=redis_opts['host'],
                                   port=int(redis_opts['port']),
                                   db=int(redis_opts['db']),
                                   password=redis_opts['password'])
    cache_prefix = 'cache_path:{0}'.format(cfg.get('storage_path', '/'))

    # Enable the LRU as well
    lru.init(
        host=redis_opts['host'],
        port=int(redis_opts['port']),
        db=int(redis_opts['db']),
        password=redis_opts['password'],
        path=cfg.get('storage_path', '/')
    )

init()

########NEW FILE########
__FILENAME__ = checksums
# -*- coding: utf-8 -*-

import hashlib
import logging


logger = logging.getLogger(__name__)


def sha256_file(fp, data=None):
    h = hashlib.sha256(data or '')
    if not fp:
        return h.hexdigest()
    while True:
        buf = fp.read(4096)
        if not buf:
            break
        h.update(buf)
    return h.hexdigest()


def sha256_string(s):
    return hashlib.sha256(s).hexdigest()


class TarSum(object):

    def __init__(self, json_data):
        self.json_data = json_data
        self.header_fields = ('name', 'mode', 'uid', 'gid', 'size', 'mtime',
                              'type', 'linkname', 'uname', 'gname', 'devmajor',
                              'devminor')
        self.hashes = []

    def append(self, member, tarobj):
        header = ''
        for field in self.header_fields:
            value = getattr(member, field)
            if field == 'type':
                field = 'typeflag'
            elif field == 'name':
                if member.isdir() and not value.endswith('/'):
                    value += '/'
            header += '{0}{1}'.format(field, value)
        h = None
        try:
            if member.size > 0:
                f = tarobj.extractfile(member)
                h = sha256_file(f, header)
            else:
                h = sha256_string(header)
        except KeyError:
            h = sha256_string(header)
        self.hashes.append(h)

    def compute(self):
        self.hashes.sort()
        data = self.json_data + ''.join(self.hashes)
        tarsum = 'tarsum+sha256:{0}'.format(sha256_string(data))
        logger.debug('checksums.compute_tarsum: return {0}'.format(tarsum))
        return tarsum


def simple_checksum_handler(json_data):
    h = hashlib.sha256(json_data + '\n')

    def fn(buf):
        h.update(buf)
    return h, fn


def compute_simple(fp, json_data):
    data = json_data + '\n'
    return 'sha256:{0}'.format(sha256_file(fp, data))


if __name__ == '__main__':
    import sys
    if len(sys.argv) < 3:
        print('Usage: {0} json_file layer_file'.format(sys.argv[0]))
        sys.exit(1)
    json_data = file(sys.argv[1]).read()
    fp = open(sys.argv[2])
    print(compute_simple(fp, json_data))
    #print compute_tarsum(fp, json_data)

########NEW FILE########
__FILENAME__ = config
# -*- coding: utf-8 -*-

import os
import rsa
import yaml

from docker_registry.core import exceptions


class Config(object):

    def __init__(self, config):
        self._config = config

    def __repr__(self):
        return repr(self._config)

    def __getattr__(self, key):
        if key in self._config:
            return self._config[key]

    def get(self, *args, **kwargs):
        return self._config.get(*args, **kwargs)


def _walk_object(obj, callback):
    if not hasattr(obj, '__iter__'):
        return callback(obj)
    obj_new = {}
    if isinstance(obj, dict):
        for i, value in obj.iteritems():
            value = _walk_object(value, callback)
            if value or value == '':
                obj_new[i] = value
        return obj_new
    for i, value in enumerate(obj):
        value = _walk_object(value, callback)
        if value or value == '':
            obj_new[i] = value
    return obj_new


def convert_env_vars(config):
    def _replace_env(s):
        if isinstance(s, basestring) and s.startswith('_env:'):
            parts = s.split(':', 2)
            varname = parts[1]
            vardefault = None if len(parts) < 3 else parts[2]
            return os.environ.get(varname, vardefault)
        return s

    return _walk_object(config, _replace_env)


_config = None


def load():
    global _config
    if _config is not None:
        return _config
    data = None
    config_path = os.environ.get('DOCKER_REGISTRY_CONFIG', 'config.yml')
    if not os.path.isabs(config_path):
        config_path = os.path.join(os.path.dirname(__file__), '../../',
                                   'config', config_path)
    try:
        f = open(config_path)
    except Exception:
        raise exceptions.FileNotFoundError(
            'Heads-up! File is missing: %s' % config_path)

    try:
        data = yaml.load(f)
    except Exception:
        raise exceptions.ConfigError(
            'Config file (%s) is not valid yaml' % config_path)

    config = data.get('common', {})
    flavor = os.environ.get('SETTINGS_FLAVOR', 'dev')
    config.update(data.get(flavor, {}))
    config['flavor'] = flavor
    config = convert_env_vars(config)
    if 'privileged_key' in config:
        try:
            f = open(config['privileged_key'])
        except Exception:
            raise exceptions.FileNotFoundError(
                'Heads-up! File is missing: %s' % config['privileged_key'])

        try:
            config['privileged_key'] = rsa.PublicKey.load_pkcs1(f.read())
        except Exception:
            raise exceptions.ConfigError(
                'Key at %s is not a valid RSA key' % config['privileged_key'])

    _config = Config(config)
    return _config

########NEW FILE########
__FILENAME__ = db
# -*- coding: utf-8 -*-

"""An SQLAlchemy backend for the search endpoint
"""

import sqlalchemy
import sqlalchemy.exc
import sqlalchemy.ext.declarative
import sqlalchemy.orm
import sqlalchemy.sql.functions

from ... import storage
from .. import config
from . import Index


Base = sqlalchemy.ext.declarative.declarative_base()


class Version (Base):
    "Schema version for the search-index database"
    __tablename__ = 'version'

    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)

    def __repr__(self):
        return '<{0}(id={1})>'.format(type(self).__name__, self.id)


class Repository (Base):
    "Repository description"
    __tablename__ = 'repository'

    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)
    name = sqlalchemy.Column(
        sqlalchemy.String, nullable=False, unique=True)
    description = sqlalchemy.Column(sqlalchemy.String)

    def __repr__(self):
        return "<{0}(name='{1}', description='{2}')>".format(
            type(self).__name__, self.name, self.description)


class SQLAlchemyIndex (Index):
    """Maintain an index of repository data

    The index is a dictionary.  The keys are
    '{namespace}/{repository}' strings, and the values are description
    strings.  For example:

      index['library/ubuntu'] = 'An ubuntu image...'
    """
    def __init__(self, database=None):
        if database is None:
            cfg = config.load()
            database = cfg.sqlalchemy_index_database
        self._engine = sqlalchemy.create_engine(database)
        self._session = sqlalchemy.orm.sessionmaker(bind=self._engine)
        self.version = 1
        self._setup_database()
        super(SQLAlchemyIndex, self).__init__()

    def _setup_database(self):
        session = self._session()
        try:
            version = session.query(
                sqlalchemy.sql.functions.max(Version.id)).first()[0]
        except sqlalchemy.exc.OperationalError:
            version = None
        if version:
            if version != self.version:
                raise NotImplementedError(
                    'unrecognized search index version {0}'.format(version))
        else:
            self._generate_index(session=session)
        session.close()

    def _generate_index(self, session):
        store = storage.load()
        Base.metadata.create_all(self._engine)
        session.add(Version(id=self.version))
        for repository in self._walk_storage(store=store):
            session.add(Repository(**repository))
        session.commit()

    def _handle_repository_created(
            self, sender, namespace, repository, value):
        name = '{0}/{1}'.format(namespace, repository)
        description = ''  # TODO(wking): store descriptions
        session = self._session()
        session.add(Repository(name=name, description=description))
        session.commit()
        session.close()

    def _handle_repository_updated(
            self, sender, namespace, repository, value):
        name = '{0}/{1}'.format(namespace, repository)
        description = ''  # TODO(wking): store descriptions
        session = self._session()
        session.query(Repository).filter(
            Repository.name == name
        ).update(
            values={'description': description},
            synchronize_session=False
        )
        session.commit()
        session.close()

    def _handle_repository_deleted(self, sender, namespace, repository):
        name = '{0}/{1}'.format(namespace, repository)
        session = self._session()
        session.query(Repository).filter(Repository.name == name).delete()
        session.commit()
        session.close()

    def results(self, search_term):
        session = self._session()
        like_term = '%%%s%%' % search_term
        repositories = session.query(Repository).filter(
            sqlalchemy.sql.or_(
                Repository.name.like(like_term),
                Repository.description.like(like_term)))
        return [
            {
                'name': repo.name,
                'description': repo.description,
            }
            for repo in repositories]

########NEW FILE########
__FILENAME__ = layers
# -*- coding: utf-8 -*-

import tarfile
import tempfile

import backports.lzma as lzma
from docker_registry.core import compat
json = compat.json

from .. import storage
from . import cache
from . import rqueue

store = storage.load()

FILE_TYPES = {
    tarfile.REGTYPE: 'f',
    tarfile.AREGTYPE: 'f',
    tarfile.LNKTYPE: 'l',
    tarfile.SYMTYPE: 's',
    tarfile.CHRTYPE: 'c',
    tarfile.BLKTYPE: 'b',
    tarfile.DIRTYPE: 'd',
    tarfile.FIFOTYPE: 'i',
    tarfile.CONTTYPE: 't',
    tarfile.GNUTYPE_LONGNAME: 'L',
    tarfile.GNUTYPE_LONGLINK: 'K',
    tarfile.GNUTYPE_SPARSE: 'S',
}

# queue for requesting diff calculations from workers
diff_queue = rqueue.CappedCollection(cache.redis_conn, "diff-worker", 1024)


def generate_ancestry(image_id, parent_id=None):
    if not parent_id:
        store.put_content(store.image_ancestry_path(image_id),
                          json.dumps([image_id]))
        return
    # Note(dmp): unicode patch
    data = store.get_json(store.image_ancestry_path(parent_id))
    data.insert(0, image_id)
    # Note(dmp): unicode patch
    store.put_json(store.image_ancestry_path(image_id), data)


class Archive(lzma.LZMAFile):
    """file-object wrapper for decompressing xz compressed tar archives
    This class wraps a file-object that contains tar archive data. The data
    will be optionally decompressed with lzma/xz if found to be a compressed
    archive.
    The file-object itself must be seekable.
    """

    def __init__(self, *args, **kwargs):
        super(Archive, self).__init__(*args, **kwargs)
        self.compressed = True

    def _proxy(self, method, *args, **kwargs):
        if not self.compressed:
            return getattr(self._fp, method)(*args, **kwargs)
        if self.compressed:
            previous = self._fp.tell()
            try:
                return getattr(super(Archive, self), method)(*args, **kwargs)
            except lzma._lzma.LZMAError:
                self._fp.seek(previous)
                self.compressed = False
                return getattr(self._fp, method)(*args, **kwargs)

    def tell(self):
        return self._proxy('tell')

    def close(self):
        return self._proxy('close')

    def seek(self, offset, whence=0):
        return self._proxy('seek', offset, whence)

    def read(self, size=-1):
        return self._proxy('read', size)

    def _check_can_seek(self):
        return True

    def seekable(self):
        return True

    def readable(self):
        return True


class TarFilesInfo(object):

    def __init__(self):
        self.infos = []

    def append(self, member):
        info = serialize_tar_info(member)
        if info is not None:
            self.infos.append(info)

    def json(self):
        return json.dumps(self.infos)


def serialize_tar_info(tar_info):
    '''serialize a tarfile.TarInfo instance
    Take a single tarfile.TarInfo instance and serialize it to a
    tuple. Consider union whiteouts by filename and mark them as
    deleted in the third element. Don't include union metadata
    files.
    '''
    is_deleted = False
    filename = tar_info.name

    # notice and strip whiteouts
    if filename == ".":
        filename = '/'

    if filename.startswith("./"):
        filename = "/" + filename[2:]

    if filename.startswith("/.wh."):
        filename = "/" + filename[5:]
        is_deleted = True

    if filename.startswith("/.wh."):
        return None

    return (
        filename,
        FILE_TYPES.get(tar_info.type, 'u'),
        is_deleted,
        tar_info.size,
        tar_info.mtime,
        tar_info.mode,
        tar_info.uid,
        tar_info.gid,
    )


def read_tarfile(tar_fobj):
    # iterate over each file in the tar and then serialize it
    return [
        i for i in [serialize_tar_info(m) for m in tar_fobj.getmembers()]
        if i is not None
    ]


def get_image_files_cache(image_id):
    image_files_path = store.image_files_path(image_id)
    if store.exists(image_files_path):
        return store.get_content(image_files_path)


def set_image_files_cache(image_id, files_json):
    image_files_path = store.image_files_path(image_id)
    store.put_content(image_files_path, files_json)


def get_image_files_from_fobj(layer_file):
    '''get files from open file-object containing a layer

    Download the specified layer and determine the file contents.
    Alternatively, process a passed in file-object containing the
    layer data.

    '''
    layer_file.seek(0)
    archive_file = Archive(layer_file)
    tar_file = tarfile.open(fileobj=archive_file)
    files = read_tarfile(tar_file)
    return files


def get_image_files_json(image_id):
    '''return json file listing for given image id
    Download the specified layer and determine the file contents.
    Alternatively, process a passed in file-object containing the
    layer data.
    '''
    files_json = get_image_files_cache(image_id)
    if files_json:
        return files_json

    # download remote layer
    image_path = store.image_layer_path(image_id)
    with tempfile.TemporaryFile() as tmp_fobj:
        for buf in store.stream_read(image_path):
            tmp_fobj.write(buf)
        tmp_fobj.seek(0)
        # decompress and untar layer
        files_json = json.dumps(get_image_files_from_fobj(tmp_fobj))
    set_image_files_cache(image_id, files_json)
    return files_json


def get_file_info_map(file_infos):
    '''convert a list of file info tuples to dictionaries
    Convert a list of layer file info tuples to a dictionary using the
    first element (filename) as the key.
    '''
    return dict((file_info[0], file_info[1:]) for file_info in file_infos)


def get_image_diff_cache(image_id):
    image_diff_path = store.image_diff_path(image_id)
    if store.exists(image_diff_path):
        return store.get_content(image_diff_path)


def set_image_diff_cache(image_id, diff_json):
    image_diff_path = store.image_diff_path(image_id)
    store.put_content(image_diff_path, diff_json)


def get_image_diff_json(image_id):
    '''get json describing file differences in layer
    Calculate the diff information for the files contained within
    the layer. Return a dictionary of lists grouped by whether they
    were deleted, changed or created in this layer.

    To determine what happened to a file in a layer we walk backwards
    through the ancestry until we see the file in an older layer. Based
    on whether the file was previously deleted or not we know whether
    the file was created or modified. If we do not find the file in an
    ancestor we know the file was just created.

        - File marked as deleted by union fs tar: DELETED
        - Ancestor contains non-deleted file:     CHANGED
        - Ancestor contains deleted marked file:  CREATED
        - No ancestor contains file:              CREATED
    '''

    # check the cache first
    diff_json = get_image_diff_cache(image_id)
    if diff_json:
        return diff_json

    # we need all ancestral layers to calculate the diff
    ancestry_path = store.image_ancestry_path(image_id)
    # Note(dmp): unicode patch
    ancestry = store.get_json(ancestry_path)[1:]
    # grab the files from the layer
    # Note(dmp): unicode patch NOT applied - implications not clear
    files = json.loads(get_image_files_json(image_id))
    # convert to a dictionary by filename
    info_map = get_file_info_map(files)

    deleted = {}
    changed = {}
    created = {}

    # walk backwards in time by iterating the ancestry
    for id in ancestry:
        # get the files from the current ancestor
        # Note(dmp): unicode patch NOT applied - implications not clear
        ancestor_files = json.loads(get_image_files_json(id))
        # convert to a dictionary of the files mapped by filename
        ancestor_map = get_file_info_map(ancestor_files)
        # iterate over each of the top layer's files
        for filename, info in info_map.items():
            ancestor_info = ancestor_map.get(filename)
            # if the file in the top layer is already marked as deleted
            if info[1]:
                deleted[filename] = info
                del info_map[filename]
            # if the file exists in the current ancestor
            elif ancestor_info:
                # if the file was marked as deleted in the ancestor
                if ancestor_info[1]:
                    # is must have been just created in the top layer
                    created[filename] = info
                else:
                    # otherwise it must have simply changed in the top layer
                    changed[filename] = info
                del info_map[filename]
    created.update(info_map)

    # return dictionary of files grouped by file action
    diff_json = json.dumps({
        'deleted': deleted,
        'changed': changed,
        'created': created,
    })

    # store results in cache
    set_image_diff_cache(image_id, diff_json)

    return diff_json

########NEW FILE########
__FILENAME__ = mirroring
# -*- coding: utf-8 -*-

import flask
import functools
import logging
import requests

from .. import storage
from .. import toolkit
from . import cache
from . import config


DEFAULT_CACHE_TAGS_TTL = 48 * 3600
logger = logging.getLogger(__name__)


def is_mirror():
    cfg = config.load()
    return bool(cfg.get('mirroring', False))


def lookup_source(path, stream=False, source=None):
    if not source:
        cfg = config.load()
        mirroring_cfg = cfg.mirroring
        if not mirroring_cfg:
            return
        source = cfg.mirroring['source']
    source_url = '{0}{1}'.format(source, path)
    headers = {}
    for k, v in flask.request.headers.iteritems():
        if k.lower() != 'location' and k.lower() != 'host':
            headers[k] = v
    logger.debug('Request: GET {0}\nHeaders: {1}'.format(
        source_url, headers
    ))
    source_resp = requests.get(
        source_url,
        headers=headers,
        cookies=flask.request.cookies,
        stream=stream
    )
    if source_resp.status_code != 200:
        logger.debug('Source responded to request with non-200'
                     ' status')
        logger.debug('Response: {0}\n{1}\n'.format(
            source_resp.status_code, source_resp.text
        ))
        return None

    return source_resp


def source_lookup_tag(f):
    @functools.wraps(f)
    def wrapper(namespace, repository, *args, **kwargs):
        cfg = config.load()
        mirroring_cfg = cfg.mirroring
        resp = f(namespace, repository, *args, **kwargs)
        if not mirroring_cfg:
            return resp
        source = mirroring_cfg['source']
        tags_cache_ttl = mirroring_cfg.get('tags_cache_ttl',
                                           DEFAULT_CACHE_TAGS_TTL)

        if resp.status_code != 404:
            logger.debug('Status code is not 404, no source '
                         'lookup required')
            return resp

        if not cache.redis_conn:
            # No tags cache, just return
            logger.warning('mirroring: Tags cache is disabled, please set a '
                           'valid `cache\' directive in the config.')
            source_resp = lookup_source(
                flask.request.path, stream=False, source=source
            )
            if not source_resp:
                return resp

            headers = source_resp.headers
            if 'Content-Encoding' in headers:
                del headers['Content-Encoding']

            return toolkit.response(data=source_resp.content, headers=headers,
                                    raw=True)

        store = storage.load()
        request_path = flask.request.path

        if request_path.endswith('/tags'):
            # client GETs a list of tags
            tag_path = store.tag_path(namespace, repository)
        else:
            # client GETs a single tag
            tag_path = store.tag_path(namespace, repository, kwargs['tag'])

        data = cache.redis_conn.get('{0}:{1}'.format(
            cache.cache_prefix, tag_path
        ))
        if data is not None:
            return toolkit.response(data=data, raw=True)
        source_resp = lookup_source(
            flask.request.path, stream=False, source=source
        )
        if not source_resp:
            return resp
        data = source_resp.content
        headers = source_resp.headers
        if 'Content-Encoding' in headers:
                del headers['Content-Encoding']

        cache.redis_conn.setex('{0}:{1}'.format(
            cache.cache_prefix, tag_path
        ), tags_cache_ttl, data)
        return toolkit.response(data=data, headers=headers,
                                raw=True)
    return wrapper


def source_lookup(cache=False, stream=False, index_route=False):
    def decorator(f):
        @functools.wraps(f)
        def wrapper(*args, **kwargs):
            cfg = config.load()
            mirroring_cfg = cfg.mirroring
            resp = f(*args, **kwargs)
            if not mirroring_cfg:
                return resp
            source = mirroring_cfg['source']
            if index_route:
                source = mirroring_cfg.get('source_index', source)
            logger.debug('Source provided, registry acts as mirror')
            if resp.status_code != 404:
                logger.debug('Status code is not 404, no source '
                             'lookup required')
                return resp
            source_resp = lookup_source(
                flask.request.path, stream=stream, source=source
            )
            if not source_resp:
                return resp

            store = storage.load()

            headers = source_resp.headers
            if 'Content-Encoding' in headers:
                del headers['Content-Encoding']
            if index_route and 'X-Docker-Endpoints' in headers:
                headers['X-Docker-Endpoints'] = toolkit.get_endpoints()

            if not stream:
                logger.debug('JSON data found on source, writing response')
                resp_data = source_resp.content
                if cache:
                    store_mirrored_data(
                        resp_data, flask.request.url_rule.rule, kwargs,
                        store
                    )
                return toolkit.response(
                    data=resp_data,
                    headers=headers,
                    raw=True
                )
            logger.debug('Layer data found on source, preparing to '
                         'stream response...')
            layer_path = store.image_layer_path(kwargs['image_id'])
            return _handle_mirrored_layer(source_resp, layer_path, store,
                                          headers)

        return wrapper
    return decorator


def _handle_mirrored_layer(source_resp, layer_path, store, headers):
    sr = toolkit.SocketReader(source_resp)
    tmp, hndlr = storage.temp_store_handler()
    sr.add_handler(hndlr)

    def generate():
        for chunk in sr.iterate(store.buffer_size):
            yield chunk
        # FIXME: this could be done outside of the request context
        tmp.seek(0)
        store.stream_write(layer_path, tmp)
        tmp.close()
    return flask.Response(generate(), headers=headers)


def store_mirrored_data(data, endpoint, args, store):
    logger.debug('Endpoint: {0}'.format(endpoint))
    path_method, arglist = ({
        '/v1/images/<image_id>/json': ('image_json_path', ('image_id',)),
        '/v1/images/<image_id>/ancestry': (
            'image_ancestry_path', ('image_id',)
        ),
        '/v1/repositories/<path:repository>/json': (
            'registry_json_path', ('namespace', 'repository')
        ),
    }).get(endpoint, (None, None))
    if not path_method:
        return
    logger.debug('Path method: {0}'.format(path_method))
    pm_args = {}
    for arg in arglist:
        pm_args[arg] = args[arg]
    logger.debug('Path method args: {0}'.format(pm_args))
    storage_path = getattr(store, path_method)(**pm_args)
    logger.debug('Storage path: {0}'.format(storage_path))
    store.put_content(storage_path, data)

########NEW FILE########
__FILENAME__ = rlock
# -*- coding: utf-8 -*-

# https://gist.github.com/adewes/6103220

import redis
import time


class LockTimeout(BaseException):
    pass


class Lock(object):

    '''Implements a distributed lock using Redis.'''

    def __init__(self, redis, lock_type, key, expires=60):
        self.key = key
        self.lock_type = lock_type
        self.redis = redis
        self.expires = expires
        self.owns_lock = False

    def lock_key(self):
        return "%s:locks:%s" % (self.lock_type, self.key)

    def __enter__(self):
        expires = time.time() + self.expires + 1
        pipe = self.redis.pipeline()
        lock_key = self.lock_key()
        pipe.watch(lock_key)
        try:
            lock_value = float(self.redis.get(lock_key))
        except (ValueError, TypeError):
            lock_value = None
        if not lock_value or lock_value < time.time():
            try:
                pipe.multi()
                pipe.set(lock_key, expires)
                pipe.expire(lock_key, self.expires + 1)
                pipe.execute()
                self.owns_lock = True
                return expires
            except redis.WatchError:
                print("Someone tinkered with the lock!")
                pass

    def __exit__(self, exc_type, exc_value, traceback):
        if self.owns_lock:
            self.redis.delete(self.lock_key())

########NEW FILE########
__FILENAME__ = rqueue
# -*- coding: utf-8 -*-

# this module is a slight modification of Ted Nyman's QR
# https://raw.github.com/tnm/qr/master/qr.py

import logging

from docker_registry.core import compat
json = compat.json


class NullHandler(logging.Handler):
    """A logging handler that discards all logging records."""
    def emit(self, record):
        pass


# Clients can add handlers if they are interested.
log = logging.getLogger('qr')
log.addHandler(NullHandler())


class worker(object):
    def __init__(self, q, *args, **kwargs):
        self.q = q
        self.err = kwargs.get('err', None)
        self.args = args
        self.kwargs = kwargs

    def __call__(self, f):
        def wrapped():
            while True:
                # Blocking pop
                next = self.q.pop(block=True)
                if not next:
                    continue
                try:
                    # Try to execute the user's callback.
                    f(next, *self.args, **self.kwargs)
                except Exception as e:
                    try:
                        # Failing that, let's call the user's
                        # err-back, which we should keep from
                        # ever throwing an exception
                        self.err(e, *self.args, **self.kwargs)
                    except Exception:
                        pass
        return wrapped


class BaseQueue(object):
    """Base functionality common to queues."""
    def __init__(self, r_conn, key, **kwargs):
        self.serializer = json
        self.redis = r_conn
        self.key = key

    def __len__(self):
        """Return the length of the queue."""
        return self.redis.llen(self.key)

    def __getitem__(self, val):
        """Get a slice or a particular index."""
        try:
            slice = self.redis.lrange(self.key, val.start, val.stop - 1)
            return [self._unpack(i) for i in slice]
        except AttributeError:
            return self._unpack(self.redis.lindex(self.key, val))
        except Exception as e:
            log.error('Get item failed ** %s' % repr(e))
            return None

    def _pack(self, val):
        """Prepares a message to go into Redis."""
        return self.serializer.dumps(val, 1)

    def _unpack(self, val):
        """Unpacks a message stored in Redis."""
        try:
            return self.serializer.loads(val)
        except TypeError:
            return None

    def dump(self, fobj):
        """Destructively dump the contents of the queue into fp."""
        next = self.redis.rpop(self.key)
        while next:
            fobj.write(next)
            next = self.redis.rpop(self.key)

    def load(self, fobj):
        """Load the contents of the provided fobj into the queue."""
        try:
            while True:
                val = self._pack(self.serializer.load(fobj))
                self.redis.lpush(self.key, val)
        except Exception:
            return

    def dumpfname(self, fname, truncate=False):
        """Destructively dump the contents of the queue into fname."""
        if truncate:
            with file(fname, 'w+') as f:
                self.dump(f)
        else:
            with file(fname, 'a+') as f:
                self.dump(f)

    def loadfname(self, fname):
        """Load the contents of the contents of fname into the queue."""
        with file(fname) as f:
            self.load(f)

    def extend(self, vals):
        """Extends the elements in the queue."""
        with self.redis.pipeline(transaction=False) as pipe:
            for val in vals:
                pipe.lpush(self.key, self._pack(val))
            pipe.execute()

    def peek(self):
        """Look at the next item in the queue."""
        return self[-1]

    def elements(self):
        """Return all elements as a Python list."""
        return [self._unpack(o) for o in self.redis.lrange(self.key, 0, -1)]

    def elements_as_json(self):
        """Return all elements as JSON object."""
        return json.dumps(self.elements)

    def clear(self):
        """Removes all the elements in the queue."""
        self.redis.delete(self.key)


class CappedCollection(BaseQueue):
    """a bounded queue
    Implements a capped collection (the collection never
    gets larger than the specified size).
    """

    def __init__(self, r_conn, key, size, **kwargs):
        BaseQueue.__init__(self, r_conn, key, **kwargs)
        self.size = size

    def push(self, element):
        size = self.size
        with self.redis.pipeline() as pipe:
            # ltrim is zero-indexed
            val = self._pack(element)
            pipe = pipe.lpush(self.key, val).ltrim(self.key, 0, size - 1)
            pipe.execute()

    def extend(self, vals):
        """Extends the elements in the queue."""
        with self.redis.pipeline() as pipe:
            for val in vals:
                pipe.lpush(self.key, self._pack(val))
            pipe.ltrim(self.key, 0, self.size - 1)
            pipe.execute()

    def pop(self, block=False):
        if not block:
            popped = self.redis.rpop(self.key)
        else:
            queue, popped = self.redis.brpop(self.key)
        log.debug('Popped ** %s ** from key ** %s **' % (popped, self.key))
        return self._unpack(popped)

########NEW FILE########
__FILENAME__ = signals
# -*- coding: utf-8 -*-

import blinker


_signals = blinker.Namespace()

# Triggered when a repository is modified (registry/index.py)
repository_created = _signals.signal('repository-created')
repository_updated = _signals.signal('repository-updated')
repository_deleted = _signals.signal('repository-deleted')

# Triggered when a tag is modified (registry/tags.py)
tag_created = _signals.signal('tag-created')
tag_deleted = _signals.signal('tag-deleted')

########NEW FILE########
__FILENAME__ = run
# -*- coding: utf-8 -*-

from __future__ import print_function

# this must happen before anything else
import gevent.monkey
gevent.monkey.patch_all()

from argparse import ArgumentParser  # noqa
from argparse import RawTextHelpFormatter  # noqa
import distutils.spawn
import os
import sys

from .app import app  # noqa
from .tags import *  # noqa
from .images import *  # noqa
from .lib import config
from .status import *  # noqa
from .search import *  # noqa

cfg = config.load()
if cfg.standalone is not False:
    # If standalone mode is enabled (default), load the fake Index routes
    from .index import *  # noqa


DESCRIPTION = """run the docker-registry with gunicorn, honoring the following
environment variables:

GUNICORN_WORKERS: number of worker processes gunicorn should start
REGISTRY_PORT: TCP port to bind to on all ipv4 addresses; default is 5000
GUNICORN_GRACEFUL_TIMEOUT: timeout in seconds for graceful worker restart
GUNiCORN_SILENT_TIMEOUT: timeout in seconds for restarting silent workers
"""


def run_gunicorn():
    """Exec gunicorn with our wsgi app.

    Settings are taken from environment variables as listed in the help text.
    This is intended to be called as a console_script entry point.
    """

    # this only exists to provide help/usage text
    parser = ArgumentParser(description=DESCRIPTION,
                            formatter_class=RawTextHelpFormatter)
    parser.parse_args()

    workers = os.environ.get('GUNICORN_WORKERS', '4')
    port = os.environ.get('REGISTRY_PORT', '5000')
    graceful_timeout = os.environ.get('GUNICORN_GRACEFUL_TIMEOUT', '3600')
    silent_timeout = os.environ.get('GUNICORN_SILENT_TIMEOUT', '3600')

    address = '0.0.0.0:{0}'.format(port)

    gunicorn_path = distutils.spawn.find_executable('gunicorn')
    if gunicorn_path is None:
        print('error: gunicorn executable not found', file=sys.stderr)
        sys.exit(1)

    os.execl(gunicorn_path, 'gunicorn', '--access-logfile', '-', '--debug',
             '--max-requests', '100', '--graceful-timeout', graceful_timeout,
             '-t', silent_timeout, '-k', 'gevent', '-b', address,
             '-w', workers, 'docker_registry.wsgi:application')

########NEW FILE########
__FILENAME__ = search
# -*- coding: utf-8 -*-

import flask
import flask_cors

from .lib import config
from .lib import index

from . import toolkit
from .app import app


cfg = config.load()

# Enable the search index
if cfg.search_backend:
    INDEX = index.load(cfg.search_backend.lower())
else:
    INDEX = None


@app.route('/v1/search', methods=['GET'])
@flask_cors.cross_origin(methods=['GET'])  # allow all origins (*)
def get_search():
    search_term = flask.request.args.get('q', '')
    if INDEX is None:
        results = []
    else:
        results = INDEX.results(search_term=search_term)
    return toolkit.response({
        'query': search_term,
        'num_results': len(results),
        'results': results,
    })

########NEW FILE########
__FILENAME__ = status
# -*- coding: utf-8 -*-

__all__ = ['registry_status']

# http://blog.codepainters.com/2012/11/20/gevent-monkey-patching-versus-
# sniffer-nose/
# if 'threading' in sys.modules:
#     raise Exception('threading module loaded before patching!')
import gevent.monkey
gevent.monkey.patch_all()

import socket
import sys

from . import storage
from . import toolkit
from .app import app
from .lib import cache
from .lib import config

_config = config.load()


def redis_status():
    message = ''
    if not cache.redis_conn:
        cache.init()
    if not cache.redis_conn:
        return {'redis': 'unconfigured'}
    key = toolkit.gen_random_string()
    value = toolkit.gen_random_string()
    try:
        cache.redis_conn.setex(key, 5, value)
        if value != cache.redis_conn.get(key):
            message = 'Set value is different from what was received'
    except Exception:
        message = str(sys.exc_info()[1])
    return {'redis': message}


def storage_status():
    message = ''
    try:
        _storage = storage.load(_config.storage)
        key = toolkit.gen_random_string()
        value = toolkit.gen_random_string()
        _storage.put_content(key, value)
        stored_value = _storage.get_content(key)
        _storage.remove(key)
        if value != stored_value:
            message = 'Set value is different from what was received'
    except Exception as e:
        message = str(e)
    return {'storage': message}


@app.route('/_status')
@app.route('/v1/_status')
def registry_status():
    retval = {'services': ['redis', 'storage'], 'failures': {}}
    retval['host'] = socket.gethostname()
    code = 200
    jobs = [gevent.spawn(job) for job in [redis_status, storage_status]]
    gevent.joinall(jobs, timeout=10)
    for job, service in zip(jobs, retval['services']):
        try:
            value = job.get()
            if value[service] != '':
                retval['failures'].update({service: value[service]})
                code = 503
        except Exception as e:
            retval['failures'].update({service: str(e)})
            code = 503
    return toolkit.response(retval, code=code)

########NEW FILE########
__FILENAME__ = tags
# -*- coding: utf-8 -*-

import datetime
import logging
import re
import time

import flask

from docker_registry.core import compat
from docker_registry.core import exceptions
json = compat.json

from . import storage
from . import toolkit
from .app import app
from .lib import mirroring
from .lib import signals


store = storage.load()
logger = logging.getLogger(__name__)
RE_USER_AGENT = re.compile('([^\s/]+)/([^\s/]+)')


@app.route('/v1/repositories/<path:repository>/properties', methods=['PUT'])
@toolkit.parse_repository_name
@toolkit.requires_auth
def set_properties(namespace, repo):
    logger.debug("[set_access] namespace={0}; repository={1}".format(namespace,
                 repo))
    data = None
    try:
        # Note(dmp): unicode patch
        data = json.loads(flask.request.data.decode('utf8'))
    except ValueError:
        pass
    if not data or not isinstance(data, dict):
        return toolkit.api_error('Invalid data')
    private_flag_path = store.private_flag_path(namespace, repo)
    if data['access'] == 'private' and not store.is_private(namespace, repo):
        store.put_content(private_flag_path, '')
    elif data['access'] == 'public' and store.is_private(namespace, repo):
        # XXX is this necessary? Or do we know for sure the file exists?
        try:
            store.remove(private_flag_path)
        except Exception:
            pass
    return toolkit.response()


@app.route('/v1/repositories/<path:repository>/properties', methods=['GET'])
@toolkit.parse_repository_name
@toolkit.requires_auth
def get_properties(namespace, repo):
    logger.debug("[get_access] namespace={0}; repository={1}".format(namespace,
                 repo))
    is_private = store.is_private(namespace, repo)
    return toolkit.response({
        'access': 'private' if is_private else 'public'
    })


def get_tags(namespace, repository):
    tag_path = store.tag_path(namespace, repository)
    for fname in store.list_directory(tag_path):
        full_tag_name = fname.split('/').pop()
        if not full_tag_name.startswith('tag_'):
            continue
        tag_name = full_tag_name[4:]
        tag_content = store.get_content(fname)
        yield (tag_name, tag_content)


@app.route('/v1/repositories/<path:repository>/tags', methods=['GET'])
@toolkit.parse_repository_name
@toolkit.requires_auth
@mirroring.source_lookup_tag
def _get_tags(namespace, repository):
    logger.debug("[get_tags] namespace={0}; repository={1}".format(namespace,
                 repository))
    try:
        data = dict((tag_name, tag_content)
                    for tag_name, tag_content
                    in get_tags(namespace=namespace, repository=repository))
    except exceptions.FileNotFoundError:
        return toolkit.api_error('Repository not found', 404)
    return toolkit.response(data)


@app.route('/v1/repositories/<path:repository>/tags/<tag>', methods=['GET'])
@toolkit.parse_repository_name
@toolkit.requires_auth
@mirroring.source_lookup_tag
def get_tag(namespace, repository, tag):
    logger.debug("[get_tag] namespace={0}; repository={1}; tag={2}".format(
                 namespace, repository, tag))
    data = None
    tag_path = store.tag_path(namespace, repository, tag)
    try:
        data = store.get_content(tag_path)
    except exceptions.FileNotFoundError:
        return toolkit.api_error('Tag not found', 404)
    return toolkit.response(data)


# warning: this endpoint is deprecated in favor of tag-specific json
# implemented by get_repository_tag_json
@app.route('/v1/repositories/<path:repository>/json', methods=['GET'])
@toolkit.parse_repository_name
@toolkit.requires_auth
@mirroring.source_lookup(stream=False, cache=True)
def get_repository_json(namespace, repository):
    json_path = store.repository_json_path(namespace, repository)
    headers = {}
    data = {'last_update': None,
            'docker_version': None,
            'docker_go_version': None,
            'arch': 'amd64',
            'os': 'linux',
            'kernel': None}
    try:
        # Note(dmp): unicode patch
        data = store.get_json(json_path)
    except exceptions.FileNotFoundError:
        if mirroring.is_mirror():
            # use code 404 to trigger the source_lookup decorator.
            # TODO(joffrey): make sure this doesn't break anything or have the
            # decorator rewrite the status code before sending
            return toolkit.response(data, code=404, headers=headers)
        # else we ignore the error, we'll serve the default json declared above
    return toolkit.response(data, headers=headers)


@app.route(
    '/v1/repositories/<path:repository>/tags/<tag>/json',
    methods=['GET'])
@toolkit.parse_repository_name
@toolkit.requires_auth
def get_repository_tag_json(namespace, repository, tag):
    json_path = store.repository_tag_json_path(namespace, repository, tag)
    data = {'last_update': None,
            'docker_version': None,
            'docker_go_version': None,
            'arch': 'amd64',
            'os': 'linux',
            'kernel': None}
    try:
        # Note(dmp): unicode patch
        data = store.get_json(json_path)
    except exceptions.FileNotFoundError:
        # We ignore the error, we'll serve the default json declared above
        pass
    return toolkit.response(data)


def create_tag_json(user_agent):
    props = {
        'last_update': int(time.mktime(datetime.datetime.utcnow().timetuple()))
    }
    ua = dict(RE_USER_AGENT.findall(user_agent))
    if 'docker' in ua:
        props['docker_version'] = ua['docker']
    if 'go' in ua:
        props['docker_go_version'] = ua['go']
    for k in ['arch', 'kernel', 'os']:
        if k in ua:
            props[k] = ua[k].lower()
    return json.dumps(props)


@app.route('/v1/repositories/<path:repository>/tags/<tag>',
           methods=['PUT'])
@toolkit.parse_repository_name
@toolkit.requires_auth
def put_tag(namespace, repository, tag):
    logger.debug("[put_tag] namespace={0}; repository={1}; tag={2}".format(
                 namespace, repository, tag))
    data = None
    try:
        # Note(dmp): unicode patch
        data = json.loads(flask.request.data.decode('utf8'))
    except ValueError:
        pass
    if not data or not isinstance(data, basestring):
        return toolkit.api_error('Invalid data')
    if not store.exists(store.image_json_path(data)):
        return toolkit.api_error('Image not found', 404)
    store.put_content(store.tag_path(namespace, repository, tag), data)
    sender = flask.current_app._get_current_object()
    signals.tag_created.send(sender, namespace=namespace,
                             repository=repository, tag=tag, value=data)
    # Write some meta-data about the repos
    ua = flask.request.headers.get('user-agent', '')
    data = create_tag_json(user_agent=ua)
    json_path = store.repository_tag_json_path(namespace, repository, tag)
    store.put_content(json_path, data)
    if tag == "latest":  # TODO(dustinlacewell) : deprecate this for v2
        json_path = store.repository_json_path(namespace, repository)
        store.put_content(json_path, data)
    return toolkit.response()


def delete_tag(namespace, repository, tag):
    logger.debug("[delete_tag] namespace={0}; repository={1}; tag={2}".format(
                 namespace, repository, tag))
    store.remove(store.tag_path(namespace, repository, tag))
    store.remove(store.repository_tag_json_path(namespace, repository,
                                                tag))
    sender = flask.current_app._get_current_object()
    if tag == "latest":  # TODO(wking) : deprecate this for v2
        store.remove(store.repository_json_path(namespace, repository))
    signals.tag_deleted.send(
        sender, namespace=namespace, repository=repository, tag=tag)


@app.route('/v1/repositories/<path:repository>/tags/<tag>',
           methods=['DELETE'])
@toolkit.parse_repository_name
@toolkit.requires_auth
def _delete_tag(namespace, repository, tag):
    # XXX backends are inconsistent on this - some will throw, but not all
    try:
        delete_tag(namespace=namespace, repository=repository, tag=tag)
    except exceptions.FileNotFoundError:
        return toolkit.api_error('Tag not found', 404)
    return toolkit.response()


@app.route('/v1/repositories/<path:repository>/', methods=['DELETE'])
@app.route('/v1/repositories/<path:repository>/tags', methods=['DELETE'])
@toolkit.parse_repository_name
@toolkit.requires_auth
def delete_repository(namespace, repository):
    """Remove a repository from storage

    This endpoint exists in both the registry API [1] and the indexer
    API [2], but has the same semantics in each instance.  It's in the
    tags module (instead of the index module which handles most
    repository tasks) because it should be available regardless of
    whether the rest of the index-module endpoints are enabled via the
    'standalone' config setting.

    [1]: http://docs.docker.io/en/latest/reference/api/registry_api/#delete--v1-repositories-%28namespace%29-%28repository%29- # nopep8
    [2]: http://docs.docker.io/en/latest/reference/api/index_api/#delete--v1-repositories-%28namespace%29-%28repo_name%29- # nopep8
    """
    logger.debug("[delete_repository] namespace={0}; repository={1}".format(
                 namespace, repository))
    try:
        for tag_name, tag_content in get_tags(
                namespace=namespace, repository=repository):
            delete_tag(
                namespace=namespace, repository=repository, tag=tag_name)
        # TODO(wking): remove images, but may need refcounting
        store.remove(store.repository_path(
            namespace=namespace, repository=repository))
    except exceptions.FileNotFoundError:
        return toolkit.api_error('Repository not found', 404)
    else:
        sender = flask.current_app._get_current_object()
        signals.repository_deleted.send(
            sender, namespace=namespace, repository=repository)
    return toolkit.response()

########NEW FILE########
__FILENAME__ = toolkit
# -*- coding: utf-8 -*-

import base64
import distutils.version
import functools
import logging
import random
import re
import string
import urllib

import flask
import requests
import rsa

from docker_registry.core import compat
json = compat.json

from . import storage
from .lib import config


logger = logging.getLogger(__name__)
_re_docker_version = re.compile('docker/([^\s]+)')
_re_authorization = re.compile(r'(\w+)[:=][\s"]?([^",]+)"?')


class DockerVersion(distutils.version.StrictVersion):

    def __init__(self):
        ua = flask.request.headers.get('user-agent', '')
        m = _re_docker_version.search(ua)
        if not m:
            raise RuntimeError('toolkit.DockerVersion: cannot parse version')
        version = m.group(1)
        if '-' in version:
            version = version.split('-')[0]
        distutils.version.StrictVersion.__init__(self, version)


class SocketReader(object):

    def __init__(self, fp):
        self._fp = fp
        self.handlers = []

    def __iter__(self):
        return self.iterate()

    def iterate(self, chunk_size=-1):
        if isinstance(self._fp, requests.Response):
            if chunk_size == -1:
                chunk_size = 1024
            for chunk in self._fp.iter_content(chunk_size):
                logger.debug('Read %d bytes' % len(chunk))
                for handler in self.handlers:
                    handler(chunk)
                yield chunk
        else:
            chunk = self._fp.read(chunk_size)
            while chunk:
                logger.debug('Read %d bytes' % len(chunk))
                for handler in self.handlers:
                    handler(chunk)
                yield chunk
                chunk = self._fp.read(chunk_size)

    def add_handler(self, handler):
        self.handlers.append(handler)

    def read(self, n=-1):
        buf = self._fp.read(n)
        if not buf:
            return ''
        for handler in self.handlers:
            handler(buf)
        return buf


def response(data=None, code=200, headers=None, raw=False):
    if data is None:
        data = True
    h = {
        'Cache-Control': 'no-cache',
        'Expires': '-1',
        'Content-Type': 'application/json'
    }
    if headers:
        h.update(headers)

    if h['Cache-Control'] == 'no-cache':
        h['Pragma'] = 'no-cache'

    try:
        if raw is False:
            data = json.dumps(data, sort_keys=True, skipkeys=True)
    except TypeError:
        data = str(data)
    return flask.current_app.make_response((data, code, h))


def validate_parent_access(parent_id):
    cfg = config.load()
    if cfg.standalone is not False:
        return True
    auth = _parse_auth_header()
    if not auth:
        return False
    full_repos_name = auth.get('repository', '').split('/')
    if len(full_repos_name) != 2:
        logger.debug('validate_parent: Invalid repository field')
        return False
    index_endpoint = cfg.index_endpoint
    if index_endpoint is None:
        index_endpoint = 'https://index.docker.io'
    index_endpoint = index_endpoint.strip('/')
    url = '{0}/v1/repositories/{1}/{2}/layer/{3}/access'.format(
        index_endpoint, full_repos_name[0], full_repos_name[1], parent_id
    )
    headers = {'Authorization': flask.request.headers.get('authorization')}
    resp = requests.get(url, verify=True, headers=headers)
    if resp.status_code != 200:
        logger.debug('validate_parent: index returns status {0}'.format(
            resp.status_code
        ))
        return False
    try:
        # Note(dmp): unicode patch XXX not applied! Assuming requests does it
        logger.debug('validate_parent: Content: {0}'.format(resp.text))
        return json.loads(resp.text).get('access', False)
    except ValueError:
        logger.debug('validate_parent: Wrong response format')
        return False


def validate_token(auth):
    full_repos_name = auth.get('repository', '').split('/')
    if len(full_repos_name) != 2:
        logger.debug('validate_token: Invalid repository field')
        return False
    cfg = config.load()
    index_endpoint = cfg.index_endpoint
    if index_endpoint is None:
        index_endpoint = 'https://index.docker.io'
    index_endpoint = index_endpoint.strip('/')
    url = '{0}/v1/repositories/{1}/{2}/images'.format(index_endpoint,
                                                      full_repos_name[0],
                                                      full_repos_name[1])
    headers = {'Authorization': flask.request.headers.get('authorization')}
    resp = requests.get(url, verify=True, headers=headers)
    logger.debug('validate_token: Index returned {0}'.format(resp.status_code))
    if resp.status_code != 200:
        return False
    store = storage.load()
    try:
        # Note(dmp): unicode patch XXX not applied (requests)
        images_list = [i['id'] for i in json.loads(resp.text)]
        store.put_content(store.images_list_path(*full_repos_name),
                          json.dumps(images_list))
    except ValueError:
        logger.debug('validate_token: Wrong format for images_list')
        return False
    return True


def get_remote_ip():
    if 'X-Forwarded-For' in flask.request.headers:
        return flask.request.headers.getlist('X-Forwarded-For')[0]
    if 'X-Real-Ip' in flask.request.headers:
        return flask.request.headers.getlist('X-Real-Ip')[0]
    return flask.request.remote_addr


def is_ssl():
    for header in ('X-Forwarded-Proto', 'X-Forwarded-Protocol'):
        if header in flask.request.headers and \
                flask.request.headers[header].lower() in ('https', 'ssl'):
                    return True
    return False


def _parse_auth_header():
    auth = flask.request.headers.get('authorization', '')
    if auth.split(' ')[0].lower() != 'token':
        logger.debug('check_token: Invalid token format')
        return None
    logger.debug('Auth Token = {0}'.format(auth))
    auth = dict(_re_authorization.findall(auth))
    logger.debug('auth = {0}'.format(auth))
    return auth


def check_token(args):
    cfg = config.load()
    if cfg.disable_token_auth is True or cfg.standalone is not False:
        return True
    logger.debug('args = {0}'.format(args))
    auth = _parse_auth_header()
    if not auth:
        return False
    if 'namespace' in args and 'repository' in args:
        # We're authorizing an action on a repository,
        # let's check that it matches the repos name provided in the token
        full_repos_name = '{namespace}/{repository}'.format(**args)
        logger.debug('full_repos_name  = {0}'.format(full_repos_name))
        if full_repos_name != auth.get('repository'):
            logger.debug('check_token: Wrong repository name in the token:'
                         '{0} != {1}'.format(full_repos_name,
                                             auth.get('repository')))
            return False
    # Check that the token `access' variable is aligned with the HTTP method
    access = auth.get('access')
    if access == 'write' and flask.request.method not in ['POST', 'PUT']:
        logger.debug('check_token: Wrong access value in the token')
        return False
    if access == 'read' and flask.request.method != 'GET':
        logger.debug('check_token: Wrong access value in the token')
        return False
    if access == 'delete' and flask.request.method != 'DELETE':
        logger.debug('check_token: Wrong access value in the token')
        return False
    if validate_token(auth) is False:
        return False
    # Token is valid
    return True


def check_signature():
    cfg = config.load()
    if not cfg.get('privileged_key'):
        return False
    headers = flask.request.headers
    signature = headers.get('X-Signature')
    if not signature:
        logger.debug('No X-Signature header in request')
        return False
    sig = parse_content_signature(signature)
    logger.debug('Parsed signature: {}'.format(sig))
    sigdata = base64.b64decode(sig['data'])
    header_keys = sorted([
        x for x in headers.iterkeys() if x.startswith('X-Docker')
    ])
    message = ','.join([flask.request.method, flask.request.path] +
                       ['{}:{}'.format(k, headers[k]) for k in header_keys])
    logger.debug('Signed message: {}'.format(message))
    try:
        return rsa.verify(message, sigdata, cfg.get('privileged_key'))
    except rsa.VerificationError:
        return False


def parse_content_signature(s):
    lst = [x.strip().split('=', 1) for x in s.split(';')]
    ret = {}
    for k, v in lst:
        ret[k] = v
    return ret


def requires_auth(f):
    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        if check_signature() is True or check_token(kwargs) is True:
            return f(*args, **kwargs)
        headers = {'WWW-Authenticate': 'Token'}
        return api_error('Requires authorization', 401, headers)
    return wrapper


def api_error(message, code=400, headers=None):
    logger.debug('api_error: {0}'.format(message))
    return response({'error': message}, code, headers)


def gen_random_string(length=16):
    return ''.join([random.choice(string.ascii_uppercase + string.digits)
                    for x in range(length)])


def parse_repository_name(f):
    @functools.wraps(f)
    def wrapper(repository, *args, **kwargs):
        parts = repository.rstrip('/').split('/', 1)
        if len(parts) < 2:
            namespace = 'library'
            repository = parts[0]
        else:
            (namespace, repository) = parts
        repository = urllib.quote_plus(repository)
        return f(namespace, repository, *args, **kwargs)
    return wrapper


def get_repository():
    auth = flask.request.headers.get('authorization', '')
    if not auth:
        return
    auth = dict(_re_authorization.findall(auth))
    repository = auth.get('repository')
    if repository is None:
        return ('', '')
    parts = repository.rstrip('/').split('/', 1)
    if len(parts) < 2:
        return ('library', parts[0])
    return (parts[0], parts[1])


def get_endpoints(cfg=None):
    if not cfg:
        cfg = config.load()
    registry_endpoints = cfg.registry_endpoints
    if not registry_endpoints:
        #registry_endpoints = socket.gethostname()
        registry_endpoints = flask.request.environ['HTTP_HOST']
    return registry_endpoints

########NEW FILE########
__FILENAME__ = wsgi
#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import os

from .run import app


if __name__ == '__main__':
    # Bind to PORT if defined, otherwise default to 5000.
    port = int(os.environ.get('PORT_WWW', 5000))
    app.debug = True
    app.run(host='0.0.0.0', port=port)
    # Or you can run:
    # gunicorn --access-logfile - --log-level debug --debug -b 0.0.0.0:5000 \
    #  -w 1 wsgi:application
else:
    # For uwsgi
    app.logger.setLevel(logging.INFO)
    stderr_logger = logging.StreamHandler()
    stderr_logger.setLevel(logging.INFO)
    stderr_logger.setFormatter(
        logging.Formatter('%(asctime)s %(levelname)s: %(message)s'))
    app.logger.addHandler(stderr_logger)

    application = app

########NEW FILE########
__FILENAME__ = bandwidth_parser
#!/usr/bin/env python

import datetime
import json
import logging
import re
import redis
import sys

logging.basicConfig(format='%(asctime)s %(levelname)s: %(message)s',
                    level=logging.INFO)
logger = logging.getLogger('metrics')

redis_opts = {}
redis_conn = None
cache_prefix = 'bandwidth_log:'
control_cache_key = 'last_line_parsed'
logging_period = 60 * 24  # 24hs
logging_interval = 15  # 15 minutes
exp_time = 60 * 60 * 24  # Key expires in 24hs
try:
    with open('/home/dotcloud/environment.json') as f:
        env = json.load(f)
        # Prod
        redis_opts = {
            'host': env['DOTCLOUD_REDIS_REDIS_HOST'],
            'port': int(env['DOTCLOUD_REDIS_REDIS_PORT']),
            'db': 1,
            'password': env['DOTCLOUD_REDIS_REDIS_PASSWORD'],
        }
except Exception:
    # Dev
    redis_opts = {
        'host': 'localhost',
        'port': 6380,
        'db': 0,
        'password': None,
    }


def convert_str_to_datetime(date_str):
    return datetime.datetime.strptime(date_str, '%d/%b/%Y:%H:%M:%S')


def raw_line_parser(str_line):
    pattern = ("(?P<ip>\d{1,3}.\d{1,3}.\d{1,3}.\d{1,3}) - - \["
               "(?P<date>\d{2}/\w+/\d{4}:\d{2}:\d{2}:\d{2})?\] \""
               "(?P<http_request>\w+)? /\w+/\w+/"
               "(?P<id>\w+)?/(?P<type>\w+)?")
    pattern_2 = ".*?(\d+)$"
    results = re.match(pattern, str_line)
    if results is None:
        return results
    results = re.match(pattern, str_line).groupdict()
    temp_results = re.match(pattern_2, str_line)
    if temp_results is None:
        results['size'] = None
        return results
    results['size'] = re.match(pattern_2, str_line).group(1)
    return results


def compute_bandwidth(str_end_time, str_start_time, str_layer_size):
    bandwidth = 0.0
    if str_start_time is None:
        return bandwidth
    if str_end_time is None:
        return bandwidth
    if str_layer_size is None:
        return bandwidth
    start_time = convert_str_to_datetime(str_start_time)
    end_time = convert_str_to_datetime(str_end_time)
    layer_size = long(str_layer_size)
    layer_size_kb = (layer_size * 8) / 1024  # Kilobits
    delta = end_time - start_time
    num_seconds = delta.total_seconds()
    bandwidth = 0.0
    if num_seconds and layer_size_kb > 100:
        bandwidth = layer_size_kb / num_seconds  # Kilobits-per-second (KB/s)
    return bandwidth


def cache_key(key):
    return cache_prefix + key


def set_cache(interval, bandwidth):
    global redis_conn, exp_period
    if redis_conn is None:
        logger.error('Failed to find a redis connection.')
        return
    key = cache_key('{0}'.format(interval))
    redis_conn.setex(key, exp_time, bandwidth)  # time in seconds
    logger.info('Saved in Redis: key: {0} bandwidth: {1}'.format(
        key, bandwidth))


def adjust_current_interval(current_interval, end_time, items):
    global logging_interval, logging_period
    total_items = logging_period / logging_interval
    logger.info('Skipping interval: {0}'.format(current_interval))
    for i in range(items, total_items):
        items = i + 1
        current_interval -= datetime.timedelta(minutes=logging_interval)
        if current_interval <= end_time:
            break
        logger.info('Skipping interval: {0}'.format(current_interval))
    return current_interval, items


def save_bandwidth(bandwidth, key, items):
    # Save the average bandwidth of the give items
    avg_bandwidth = round(bandwidth[key] / items[key], 2)
    logger.info('Saving in Redis...')
    set_cache(key, avg_bandwidth)


def save_last_line_parsed(time):
    global redis_conn, cache_prefix
    if redis_conn is None:
        logger.error('Failed to find a redis connection.')
        return
    key = cache_key(control_cache_key)
    redis_conn.set(key, time)
    logger.info('Last time saved: {0}'.format(time))


def get_last_line_parsed():
    global redis_conn, cache_prefix
    if redis_conn is None:
        logger.error('Failed to find a redis connection.')
        return
    key = cache_key(control_cache_key)
    return redis_conn.get(key)


def update_current_interval(items, logging_interval, start_time):
    items += 1
    interval = logging_interval * items
    current_interval = start_time - datetime.timedelta(minutes=interval)
    logger.info('Updating interval to: {0}'.format(current_interval))
    return current_interval, items


def parse_data(item):
    str_start_time = None
    str_end_time = None
    str_layer_size = None
    key = None
    if item['http_request'] is not None and item['type'] is not None:
        if 'GET' in item['http_request'] and 'layer' in item['type']:
            str_end_time = item['date']
        elif 'GET' in item['http_request'] and 'json' in item['type']:
            str_start_time = item['date']
            str_layer_size = item['size']
        key = item['id']
    return str_start_time, str_end_time, str_layer_size, key


def read_file(file_name):
    logger.info('Reading file...')
    parsed_data = []
    try:
        with open(file_name) as f:
            for line in reversed(f.readlines()):
                processed_line = raw_line_parser(line.rstrip())
                if processed_line is not None:
                    parsed_data.append(processed_line)
    except IOError as e:
        logger.error('Failed to read the file. {0}'.format(e))
        exit(1)
    return parsed_data


def generate_bandwidth_data(start_time, min_time, time_interval):
    global logging_interval, logging_period
    end_times = {}
    bandwidth_items = {}
    num_items = {}
    total_items = logging_period / logging_interval
    items = 1
    parsed_data = read_file(sys.argv[1])
    last_time_parsed = get_last_line_parsed()
    most_recent_parsing = None
    if last_time_parsed:
        last_time_parsed = convert_str_to_datetime(last_time_parsed)
        logger.info('Last time parsed: {0}'.format(last_time_parsed))
    for item in parsed_data:
        str_start_time, str_end_time, str_layer_size, key = parse_data(item)
        if str_end_time:
            end_times[key] = str_end_time
        else:
            str_end_time = end_times.get(key)
        bandwidth = compute_bandwidth(str_end_time,
                                      str_start_time,
                                      str_layer_size)
        if bandwidth:
            end_time = convert_str_to_datetime(str_end_time)
            if last_time_parsed:
                if last_time_parsed >= end_time:
                    logger.info('Remaining data parsed already. Stopping...')
                    break
            if end_time < min_time:
                logger.info('Minimum date reached. Stopping...')
                break
            if items >= total_items:
                logger.info('Maximum number of elements reached. Stopping...')
                break
            if time_interval > end_time:
                if bandwidth_items.get(time_interval, 0):
                    save_bandwidth(bandwidth_items,
                                   time_interval,
                                   num_items)
                    if not most_recent_parsing:
                        most_recent_parsing = str_end_time
                    time_interval, items = \
                        update_current_interval(items,
                                                logging_interval,
                                                start_time)
                else:
                    time_interval, items = \
                        adjust_current_interval(time_interval,
                                                end_time,
                                                items)
            bandwidth_items[time_interval] = \
                bandwidth_items.get(time_interval, 0.0) \
                + bandwidth
            num_items[time_interval] = \
                num_items.get(time_interval, 0.0) + 1
            end_times.pop(key, None)
    if most_recent_parsing:
        save_last_line_parsed(most_recent_parsing)


def run():
    global redis_conn, redis_opts
    redis_conn = redis.StrictRedis(host=redis_opts['host'],
                                   port=int(redis_opts['port']),
                                   db=int(redis_opts['db']),
                                   password=redis_opts['password'])
    logger.info('Redis config: {0}'.format(redis_opts))
    start_time = datetime.datetime.utcnow()
    min_time = start_time - datetime.timedelta(minutes=logging_period)
    time_interval = start_time - datetime.timedelta(minutes=logging_interval)
    logger.info('Starting...')
    generate_bandwidth_data(start_time, min_time, time_interval)


if __name__ == "__main__":
    if len(sys.argv) == 1:
        logger.error('Please specify the logfile path.')
        exit(1)
    run()

########NEW FILE########
__FILENAME__ = create_ancestry
#!/usr/bin/env python

from __future__ import print_function

import hashlib
import sys

import simplejson as json

from docker_registry.core import exceptions
import docker_registry.storage as storage


store = storage.load()
images_cache = {}
ancestry_cache = {}
dry_run = True


def warning(msg):
    print('# Warning: ' + msg, file=sys.stderr)


def get_image_parent(image_id):
    if image_id in images_cache:
        return images_cache[image_id]
    image_json = store.image_json_path(image_id)
    parent_id = None
    try:
        # Note(dmp): unicode patch
        info = store.get_json(image_json)
        if info['id'] != image_id:
            warning('image_id != json image_id for image_id: ' + image_id)
        parent_id = info.get('parent')
    except exceptions.FileNotFoundError:
        warning('graph is broken for image_id: {0}'.format(image_id))
    images_cache[image_id] = parent_id
    return parent_id


def create_image_ancestry(image_id):
    global ancestry_cache
    if image_id in ancestry_cache:
        # We already generated the ancestry for that one
        return
    ancestry = [image_id]
    parent_id = image_id
    while True:
        parent_id = get_image_parent(parent_id)
        if not parent_id:
            break
        ancestry.append(parent_id)
        create_image_ancestry(parent_id)
    ancestry_path = store.image_ancestry_path(image_id)
    if dry_run is False:
        if not store.exists(ancestry_path):
            store.put_content(ancestry_path, json.dumps(ancestry))
    ancestry_cache[image_id] = True
    print('Generated ancestry (size: {0}) '
          'for image_id: {1}'.format(len(ancestry), image_id))


def resolve_all_tags():
    for namespace in store.list_directory(store.repositories):
        for repos in store.list_directory(namespace):
            try:
                for tag in store.list_directory(repos):
                    fname = tag.split('/').pop()
                    if not fname.startswith('tag_'):
                        continue
                    yield store.get_content(tag)
            except exceptions.FileNotFoundError:
                pass


def compute_image_checksum(image_id, json_data):
    layer_path = store.image_layer_path(image_id)
    if not store.exists(layer_path):
        warning('{0} is broken (no layer)'.format(image_id))
        return
    print('Writing checksum for {0}'.format(image_id))
    if dry_run:
        return
    h = hashlib.sha256(json_data + '\n')
    for buf in store.stream_read(layer_path):
        h.update(buf)
    checksum = 'sha256:{0}'.format(h.hexdigest())
    checksum_path = store.image_checksum_path(image_id)
    store.put_content(checksum_path, checksum)


def load_image_json(image_id):
    try:
        json_path = store.image_json_path(image_id)
        json_data = store.get_content(json_path)
        # Note(dmp): unicode patch
        info = json.loads(json_data.decode('utf8'))
        if image_id != info['id']:
            warning('{0} is broken (json\'s id mismatch)'.format(image_id))
            return
        return json_data
    except (IOError, exceptions.FileNotFoundError, json.JSONDecodeError):
        warning('{0} is broken (invalid json)'.format(image_id))


def compute_missing_checksums():
    for image in store.list_directory(store.images):
        image_id = image.split('/').pop()
        if image_id not in ancestry_cache:
            warning('{0} is orphan'.format(image_id))
        json_data = load_image_json(image_id)
        if not json_data:
            continue
        checksum_path = store.image_checksum_path(image_id)
        if store.exists(checksum_path):
            # Checksum already there, skipping
            continue
        compute_image_checksum(image_id, json_data)


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == '--seriously':
        dry_run = False
    for image_id in resolve_all_tags():
        create_image_ancestry(image_id)
    compute_missing_checksums()
    if dry_run:
        print('-------')
        print('/!\ No modification has been made (dry-run)')
        print('/!\ In order to apply the changes, re-run with:')
        print('$ {0} --seriously'.format(sys.argv[0]))
    else:
        print('# Changes applied.')

########NEW FILE########
__FILENAME__ = diff-worker
#!/usr/bin/env python

import argparse
import logging
import os

import redis

from docker_registry.lib import layers
from docker_registry.lib import rlock
from docker_registry.lib import rqueue
import docker_registry.storage as storage

store = storage.load()

redis_default_host = os.environ.get(
    'DOCKER_REDIS_1_PORT_6379_TCP_ADDR',
    '0.0.0.0')
redis_default_port = int(os.environ.get(
    'DOCKER_REDIS_1_PORT_6379_TCP_PORT',
    '6379'))

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)


def get_parser():
    parser = argparse.ArgumentParser(
        description="Daemon for computing layer diffs"
    )
    parser.add_argument(
        "--rhost", default=redis_default_host, dest="redis_host",
        help="Host of redis instance to listen to",
    )
    parser.add_argument(
        "--rport", default=redis_default_port, dest="redis_port", type=int,
        help="Port of redis instance to listen to",
    )
    parser.add_argument(
        "-d", "--database", default=0, dest="redis_db",
        type=int, metavar="redis_db",
        help="Redis database to connect to",
    )
    parser.add_argument(
        "-p", "--password", default=None, metavar="redis_pw", dest="redis_pw",
        help="Redis database password",
    )
    return parser


def get_redis_connection(options):
    redis_conn = redis.StrictRedis(
        host=options.redis_host,
        port=options.redis_port,
        db=options.redis_db,
        password=options.redis_pw,
    )
    return redis_conn


def handle_request(layer_id, redis_conn):
    '''handler for any item pulled from worker job queue
    This handler is called every time the worker is able to pop a message
    from the job queue filled by the registry. The worker blocks until a
    message is available. This handler will then attempt to aquire a lock
    for the provided layer_id and if successful, process a diff for the
    layer.

    If the lock for this layer_id has already been aquired for this layer
    the worker will immediately timeout to block for another request.
    '''
    try:
        # this with-context will attempt to establish a 5 minute lock
        # on the key for this layer, immediately passing on LockTimeout
        # if one isn't availble
        with rlock.Lock(redis_conn,
                        "diff-worker-lock",
                        layer_id,
                        expires=60 * 5):
            # first check if a cached result is already available. The registry
            # already does this, but hey.
            diff_data = layers.get_image_diff_cache(layer_id)
            if not diff_data:
                log.info("Processing diff for %s" % layer_id)
                layers.get_image_diff_json(layer_id)
    except rlock.LockTimeout:
        log.info("Another worker is processing %s. Skipping." % layer_id)

if __name__ == '__main__':
    parser = get_parser()
    options = parser.parse_args()
    redis_conn = get_redis_connection(options)
    # create a bounded queue holding registry requests for diff calculations
    queue = rqueue.CappedCollection(redis_conn, "diff-worker", 1024)
    # initialize worker factory with the queue and redis connection
    worker_factory = rqueue.worker(queue, redis_conn)
    # create worker instance with our handler
    worker = worker_factory(handle_request)
    log.info("Starting worker...")
    worker()

########NEW FILE########
__FILENAME__ = dump_repos_data
#!/usr/bin/env python

import sys

import simplejson as json

from docker_registry.core import exceptions
import docker_registry.storage as storage

store = storage.load()


def walk_all_tags():
    for namespace_path in store.list_directory(store.repositories):
        for repos_path in store.list_directory(namespace_path):
            try:
                for tag in store.list_directory(repos_path):
                    fname = tag.split('/').pop()
                    if not fname.startswith('tag_'):
                        continue
                    (namespace, repos) = repos_path.split('/')[-2:]
                    yield (namespace, repos, store.get_content(tag))
            except OSError:
                pass


def walk_ancestry(image_id):
    try:
        # Note(dmp): unicode patch
        ancestry = store.get_json(store.image_ancestry_path(image_id))
        return iter(ancestry)
    except exceptions.FileNotFoundError:
        print('Ancestry file for {0} is missing'.format(image_id))
    return []


def get_image_checksum(image_id):
    checksum_path = store.image_checksum_path(image_id)
    if not store.exists(checksum_path):
        return
    checksum = store.get_content(checksum_path)
    return checksum.strip()


def dump_json(all_repos, all_checksums, filename):
    data = []
    for ((namespace, repos), images) in all_repos.iteritems():
        images_checksums = []
        for i in set(images):
            images_checksums.append({'id': i, 'checksum': all_checksums[i]})
        data.append({
            'namespace': namespace,
            'repository': repos,
            'images': images_checksums
        })
    with open(filename, 'w') as f:
        json.dump(data, f, indent=4)


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Usage: {0} <output_file>'.format(sys.argv[0]))
        sys.exit(1)
    all_repos = {}
    all_checksums = {}
    for (namespace, repos, image_id) in walk_all_tags():
        key = (namespace, repos)
        if key not in all_repos:
            all_repos[key] = []
        for i in walk_ancestry(image_id):
            all_repos[key].append(i)
            if i in all_checksums:
                continue
            all_checksums[i] = get_image_checksum(i)
    dump_json(all_repos, all_checksums, sys.argv[1])

########NEW FILE########
__FILENAME__ = import_old_tags
#!/usr/bin/env python

import sys

import docker_registry.storage as storage


# Copy/Pasted from old models

from sqlalchemy import create_engine, ForeignKey, UniqueConstraint
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Table, Column, Integer, String, DateTime, func


Base = declarative_base()


class User(Base):

    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    created_at = Column(DateTime, nullable=False, default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())
    username = Column(String(256), nullable=False, unique=True)
    email = Column(String(256), nullable=False, unique=True)
    password = Column(String(64), nullable=False)

    repositories = relationship(
        'Repository', order_by='Repository.name', backref='user'
    )


repositories_revisions = Table(
    'repositories_revisions',
    Base.metadata,
    Column('repository_id', Integer, ForeignKey('repositories.id')),
    Column('revision_id', String(64), ForeignKey('revisions.id'))
)


class Tag(Base):

    __tablename__ = 'tags'
    __table_args__ = (
        UniqueConstraint('name', 'repository_id'),
    )

    id = Column(Integer, primary_key=True)
    name = Column(String(256), nullable=False)
    revision_id = Column(String(64), ForeignKey('revisions.id'))
    repository_id = Column(Integer, ForeignKey('repositories.id'))
    revision = relationship('ImageRevision')


class ImageRevision(Base):

    __tablename__ = 'revisions'

    id = Column(String(64), primary_key=True, autoincrement=False, unique=True)
    parent_id = Column(String(64), index=True, nullable=True)
    layer_url = Column(String(256), index=False, nullable=True)
    created_at = Column(DateTime, nullable=False)


class Repository(Base):

    __tablename__ = 'repositories'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    name = Column(String(64), index=True, nullable=False)

    revisions = relationship(
        ImageRevision,
        secondary=repositories_revisions,
        order_by=ImageRevision.created_at.desc(),
        backref='repositories'
    )
    tags = relationship('Tag', order_by='Tag.name', backref='repository')


def import_tags(sess, store):
    for tag in sess.query(Tag).all():
        try:
            repos_name = tag.repository.name
            tag_name = tag.name
            repos_namespace = tag.repository.user.username
            image_id = tag.revision.id
            path = store.tag_path(repos_namespace, repos_name, tag_name)
            if store.exists(path):
                continue
            dest = store.put_content(path, image_id)
            print('{0} -> {1}'.format(dest, image_id))
        except AttributeError as e:
            print('# Warning: {0}'.format(e))


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Usage: {0} URL'.format(sys.argv[0]))
        sys.exit(0)
    url = sys.argv[1]
    Session = sessionmaker(bind=create_engine(url))
    store = storage.load()
    sess = Session()
    import_tags(sess, store)

########NEW FILE########
__FILENAME__ = base
# -*- coding: utf-8 -*-

import docker_registry.run as run

import hashlib
import random
import string
import unittest

from docker_registry.core import compat


class TestCase(unittest.TestCase):

    def __init__(self, *args, **kwargs):
        unittest.TestCase.__init__(self, *args, **kwargs)
        run.app.testing = True
        self.http_client = run.app.test_client()
        # Override the method so we can set headers for every single call
        orig_open = self.http_client.open

        def _open(*args, **kwargs):
            if 'headers' not in kwargs:
                kwargs['headers'] = {}
            if 'User-Agent' not in kwargs['headers']:
                ua = ('docker/0.10.1 go/go1.2.1 git-commit/3600720 '
                      'kernel/3.8.0-19-generic os/linux arch/amd64')
                kwargs['headers']['User-Agent'] = ua
            return orig_open(*args, **kwargs)
        self.http_client.open = _open

    def gen_random_string(self, length=16):
        return ''.join([random.choice(string.ascii_uppercase + string.digits)
                        for x in range(length)]).lower()

    def set_image_checksum(self, image_id, checksum):
        headers = {'X-Docker-Checksum-Payload': checksum}
        url = '/v1/images/{0}/checksum'.format(image_id)
        resp = self.http_client.put(url, headers=headers)
        self.assertEqual(resp.status_code, 200, resp.data)
        # Once the checksum test passed, the image is "locked"
        resp = self.http_client.put(url, headers=headers)
        self.assertEqual(resp.status_code, 409, resp.data)
        # Cannot set the checksum on an non-existing image
        url = '/v1/images/{0}/checksum'.format(self.gen_random_string())
        resp = self.http_client.put(url, headers=headers)
        self.assertEqual(resp.status_code, 404, resp.data)

    def upload_image(self, image_id, parent_id, layer):
        json_obj = {
            'id': image_id
        }
        if parent_id:
            json_obj['parent'] = parent_id
        json_data = compat.json.dumps(json_obj)
        h = hashlib.sha256(json_data + '\n')
        h.update(layer)
        layer_checksum = 'sha256:{0}'.format(h.hexdigest())
        headers = {'X-Docker-Payload-Checksum': layer_checksum}
        resp = self.http_client.put('/v1/images/{0}/json'.format(image_id),
                                    headers=headers,
                                    data=json_data)
        self.assertEqual(resp.status_code, 200, resp.data)
        # Make sure I cannot download the image before push is complete
        resp = self.http_client.get('/v1/images/{0}/json'.format(image_id))
        self.assertEqual(resp.status_code, 400, resp.data)
        layer_file = compat.StringIO(layer)
        resp = self.http_client.put('/v1/images/{0}/layer'.format(image_id),
                                    input_stream=layer_file)
        layer_file.close()
        self.assertEqual(resp.status_code, 200, resp.data)
        self.set_image_checksum(image_id, layer_checksum)
        # Push done, test reading the image
        resp = self.http_client.get('/v1/images/{0}/json'.format(image_id))
        self.assertEqual(resp.status_code, 200, resp.data)
        self.assertEqual(resp.headers.get('x-docker-size'), str(len(layer)))
        self.assertEqual(resp.headers['x-docker-payload-checksum'],
                         layer_checksum)

########NEW FILE########
__FILENAME__ = mock_s3
# -*- coding: utf-8 -*-

'''Monkeypatch s3 Storage preventing parallel key stream read in unittesting.
   It is called from lib/storage/s3'''

from docker_registry.core import exceptions
import docker_registry.drivers.s3 as s3
from docker_registry.testing import utils


class Storage(s3.Storage):
    __metaclass__ = utils.monkeypatch_class

    # def stream_read(self, path, bytes_range=None):
    #     path = self._init_path(path)
    #     headers = None
    #     if bytes_range:
    #         headers = {'Range': 'bytes={0}-{1}'.format(*bytes_range)}
    #     key = self._boto_bucket.lookup(path, headers=headers)
    #     if not key:
    #         raise exceptions.FileNotFoundError('%s is not there' % path)
    #     while True:
    #         buf = key.read(self.buffer_size)
    #         if not buf:
    #             break
    #         yield buf

    def stream_read(self, path, bytes_range=None):
        path = self._init_path(path)
        nb_bytes = 0
        total_size = 0
        key = self._boto_bucket.lookup(path)
        if not key:
            raise exceptions.FileNotFoundError('%s is not there' % path)
        if bytes_range:
            key._last_position = bytes_range[0]
            total_size = bytes_range[1] - bytes_range[0] + 1
        while True:
            if bytes_range:
                # Bytes Range is enabled
                buf_size = self.buffer_size
                if nb_bytes + buf_size > total_size:
                    # We make sure we don't read out of the range
                    buf_size = total_size - nb_bytes
                if buf_size > 0:
                    buf = key.read(buf_size)
                    nb_bytes += len(buf)
                else:
                    # We're at the end of the range
                    buf = ''
            else:
                buf = key.read(self.buffer_size)
            if not buf:
                break
            yield buf

########NEW FILE########
__FILENAME__ = sitecustomize
# -*- coding: utf-8 -*-

'''This is a dirty hack in order to have gevent monkeying kick in before
nose and avoid the dreaded key error'''

# Prevent gevent monkeypatching used on lib/storage/s3 to throw KeyError
# exception. Should be loaded as early as posible:
#   http://stackoverflow.com/questions/8774958
import gevent.monkey
gevent.monkey.patch_thread()

########NEW FILE########
__FILENAME__ = test_all_installed_drivers
# -*- coding: utf-8 -*-

from docker_registry.core import driver as driveengine

from docker_registry import testing
# Mock any boto
from docker_registry.testing import mock_boto  # noqa

# Mock our s3 - xxx this smells like byte-range support is questionnable...
from . import mock_s3   # noqa


def getinit(name):
    def init(self):
        self.scheme = name
        self.path = ''
        self.config = testing.Config({})
    return init

for name in driveengine.available():
    # The globals shenanigan is required so that the test tool find the tests
    # The dynamic type declaration is required because it is so
    globals()['TestQuery%s' % name] = type('TestQuery%s' % name,
                                           (testing.Query,),
                                           dict(__init__=getinit(name)))

    globals()['TestDriver%s' % name] = type('TestDriver%s' % name,
                                            (testing.Driver,),
                                            dict(__init__=getinit(name)))

########NEW FILE########
__FILENAME__ = test_images
# -*- coding: utf-8 -*-

import random

import base

from docker_registry.core import compat
json = compat.json


class TestImages(base.TestCase):

    def test_unset_nginx_accel_redirect_layer(self):
        image_id = self.gen_random_string()
        layer_data = self.gen_random_string(1024)
        self.upload_image(image_id, parent_id=None, layer=layer_data)
        resp = self.http_client.get('/v1/images/{0}/layer'.format(image_id))
        self.assertEqual(layer_data, resp.data)

    def test_nginx_accel_redirect_layer(self):
        image_id = self.gen_random_string()
        layer_data = self.gen_random_string(1024)
        self.upload_image(image_id, parent_id=None, layer=layer_data)

        import docker_registry.images as images

        # ensure the storage mechanism is LocalStorage or this test is bad
        self.assertTrue(images.store.scheme == 'file',
                        'Store must be LocalStorage')

        # set the nginx accel config
        accel_header = 'X-Accel-Redirect'
        accel_prefix = '/registry'
        images.cfg._config['nginx_x_accel_redirect'] \
            = accel_prefix

        layer_path = 'images/{0}/layer'.format(image_id)

        try:
            resp = self.http_client.get('/v1/%s' % layer_path)
            self.assertTrue(accel_header in resp.headers)

            expected = '%s/%s' % (accel_prefix, layer_path)
            self.assertEqual(expected, resp.headers[accel_header])

            self.assertEqual('', resp.data)
        finally:
            images.cfg._config.pop('nginx_x_accel_redirect')

    def test_simple(self):
        image_id = self.gen_random_string()
        parent_id = self.gen_random_string()
        layer_data = self.gen_random_string(1024)
        self.upload_image(parent_id, parent_id=None, layer=layer_data)
        self.upload_image(image_id, parent_id=parent_id, layer=layer_data)
        # test fetching the ancestry
        resp = self.http_client.get('/v1/images/{0}/ancestry'.format(image_id))
        # Note(dmp): unicode patch XXX not applied assume requests does the job
        ancestry = json.loads(resp.data)
        self.assertEqual(len(ancestry), 2)
        self.assertEqual(ancestry[0], image_id)
        self.assertEqual(ancestry[1], parent_id)

    def test_notfound(self):
        resp = self.http_client.get('/v1/images/{0}/json'.format(
            self.gen_random_string()))
        self.assertEqual(resp.status_code, 404, resp.data)

    def test_bytes_range(self):
        image_id = self.gen_random_string()
        layer_data = self.gen_random_string(1024)
        b = random.randint(0, len(layer_data) / 2)
        bytes_range = (b, random.randint(b + 1, len(layer_data) - 1))
        headers = {'Range': 'bytes={0}-{1}'.format(*bytes_range)}
        self.upload_image(image_id, parent_id=None, layer=layer_data)
        url = '/v1/images/{0}/layer'.format(image_id)
        resp = self.http_client.get(url, headers=headers)
        expected_data = layer_data[bytes_range[0]:bytes_range[1] + 1]
        received_data = resp.data
        msg = 'expected size: {0}; got: {1}'.format(len(expected_data),
                                                    len(received_data))
        self.assertEqual(expected_data, received_data, msg)

########NEW FILE########
__FILENAME__ = test_index
# -*- coding: utf-8 -*-

import base

from docker_registry.core import compat
json = compat.json


class TestIndex(base.TestCase):

    """The Index module is fake at the moment, hence the unit tests only
       test the return codes
    """

    def test_users(self):
        # GET
        resp = self.http_client.get('/v1/users/')
        self.assertEqual(resp.status_code, 200, resp.data)
        # POST
        resp = self.http_client.post('/v1/users/',
                                     data=json.dumps('JSON DATA PLACEHOLDER'))
        self.assertEqual(resp.status_code, 201, resp.data)
        # PUT
        resp = self.http_client.put('/v1/users/{0}/'.format(
                                    self.gen_random_string()))
        self.assertEqual(resp.status_code, 204, resp.data)

    def test_repository_images(self):
        repo = 'test/{0}'.format(self.gen_random_string())
        images = [{'id': self.gen_random_string()},
                  {'id': self.gen_random_string()}]
        # PUT
        resp = self.http_client.put('/v1/repositories/{0}/'.format(repo),
                                    data=json.dumps(images))
        self.assertEqual(resp.status_code, 200, resp.data)
        resp = self.http_client.put('/v1/repositories/{0}/images'.format(repo),
                                    data=json.dumps(images))
        self.assertEqual(resp.status_code, 204, resp.data)
        # GET
        resp = self.http_client.get('/v1/repositories/{0}/images'.format(repo))
        self.assertEqual(resp.status_code, 200, resp.data)
        # Note(dmp): unicode patch XXX not applied assume requests does the job
        data = json.loads(resp.data)
        self.assertEqual(len(data), 2)
        self.assertTrue('id' in data[0])
        # DELETE
        resp = self.http_client.delete('/v1/repositories/{0}/images'.format(
            repo))
        self.assertEqual(resp.status_code, 204, resp.data)

    def test_auth(self):
        repo = 'test/{0}'.format(self.gen_random_string())
        resp = self.http_client.put('/v1/repositories/{0}/auth'.format(repo))
        self.assertEqual(resp.status_code, 200, resp.data)

    def test_search(self):
        search_term = self.gen_random_string()
        resp = self.http_client.get('/v1/search?q={0}'.format(search_term))
        self.assertEqual(resp.status_code, 200, resp.data)

########NEW FILE########
__FILENAME__ = test_layers
# -*- coding: utf-8 -*-

import backports.lzma as lzma
import os
import random
import string
import tarfile

import base
from docker_registry.lib import layers
from docker_registry import storage

from docker_registry.core import compat
json = compat.json
StringIO = compat.StringIO


# from mock import patch
# from mockredis import mock_strict_redis_client


def comp(n, f, *args, **kwargs):
    return (f(*args, **kwargs) for i in xrange(n))


def rndstr(length=5):
    palette = string.ascii_uppercase + string.digits
    return ''.join(comp(length, random.choice, palette))


def _get_tarfile(filenames):
    tfobj = StringIO()
    tar = tarfile.TarFile(fileobj=tfobj, mode='w')
    data = rndstr(512)
    for filename in filenames:
        tarinfo = tarfile.TarInfo(filename)
        tarinfo.size = len(data)
        io = StringIO()
        io.write(data)
        io.seek(0)
        tar.addfile(tarinfo, io)
    tfobj.seek(0)
    return tfobj


def _get_xzfile(filenames):
    tar_data = _get_tarfile(filenames)
    lzma_fobj = StringIO()
    xz_file = lzma.open(lzma_fobj, 'w')
    xz_file.write(tar_data.read())
    xz_file.close()
    lzma_fobj.seek(0)
    return lzma_fobj


class TestLayers(base.TestCase):

    def setUp(self):
        self.store = storage.load(kind='file')
        self.filenames = list(comp(5, rndstr))

    def test_tar_archive(self):
        tfobj = _get_tarfile(self.filenames)

        archive = layers.Archive(tfobj)
        tar = tarfile.open(fileobj=archive)
        members = tar.getmembers()
        for tarinfo in members:
            assert tarinfo.name in self.filenames

    def test_xz_archive(self):
        tfobj = _get_xzfile(self.filenames)
        archive = layers.Archive(tfobj)
        tar = tarfile.open(fileobj=archive)
        members = tar.getmembers()
        for tarinfo in members:
            assert tarinfo.name in self.filenames

    def test_info_serialization(self):
        tfobj = _get_tarfile(self.filenames)
        archive = layers.Archive(tfobj)
        tar = tarfile.open(fileobj=archive)
        members = tar.getmembers()
        for tarinfo in members:
            sinfo = layers.serialize_tar_info(tarinfo)
            assert sinfo[0] in self.filenames
            assert sinfo[1:] == ('f', False, 512, 0, 420, 0, 0)

    def test_tar_serialization(self):
        tfobj = _get_tarfile(self.filenames)
        archive = layers.Archive(tfobj)
        tar = tarfile.open(fileobj=archive)
        infos = layers.read_tarfile(tar)
        for tarinfo in infos:
            assert tarinfo[0] in self.filenames
            assert tarinfo[1:] == ('f', False, 512, 0, 420, 0, 0)

    def test_layer_cache(self):
        layer_id = rndstr(16)
        layers.set_image_files_cache(layer_id, "{}")
        fetched_json = layers.get_image_files_cache(layer_id)
        assert fetched_json == "{}"

    def test_tar_from_fobj(self):
        tfobj = _get_tarfile(self.filenames)
        files = layers.get_image_files_from_fobj(tfobj)
        for file in files:
            assert file[0] in self.filenames
            assert file[1:] == ('f', False, 512, 0, 420, 0, 0)

    def test_get_image_files_json_cached(self):
        layer_id = rndstr(16)
        layers.set_image_files_cache(layer_id, "{}")
        files_json = layers.get_image_files_json(layer_id)
        assert files_json == "{}"

    def test_get_image_files_json(self):
        layer_id = rndstr(16)
        tfobj = _get_tarfile(self.filenames)

        layer_path = self.store.image_layer_path(layer_id)
        layer_path = os.path.join(self.store._root_path, layer_path)
        path_parts = layer_path.split(os.sep)
        layer_parent = os.path.join(*path_parts[:-1])
        os.makedirs(layer_parent)

        with open(layer_path, 'w') as fobj:
            fobj.write(tfobj.read())

        files_json = layers.get_image_files_json(layer_id)
        file_infos = json.loads(files_json)
        for info in file_infos:
            assert info[0] in self.filenames
            assert info[1:] == [u"f", False, 512, 0, 420, 0, 0]

    def test_get_file_info_map(self):
        files = (
            ("test", "f", False, 512, 0, 420, 0, 0),
        )
        map = layers.get_file_info_map(files)
        assert "test" in map
        assert map['test'] == ("f", False, 512, 0, 420, 0, 0)

    def test_image_diff_cache(self):
        layer_id = rndstr(16)
        layers.set_image_diff_cache(layer_id, layer_id)
        diff_json = layers.get_image_diff_cache(layer_id)
        assert layer_id == diff_json

    def test_image_diff_json(self):
        layer_1 = (
            ("deleted", "f", False, 512, 0, 420, 0, 0),
            ("changed", "f", False, 512, 0, 420, 0, 0),
        )

        layer_2 = (
            ("deleted", "f", True, 512, 0, 420, 0, 0),
            ("changed", "f", False, 512, 0, 420, 0, 0),
            ("created", "f", False, 512, 0, 420, 0, 0),
        )
        layer_1_id = rndstr(16)
        layer_2_id = rndstr(16)

        ancestry = json.dumps([layer_2_id, layer_1_id])
        ancestry_path = self.store.image_ancestry_path(layer_2_id)
        self.store.put_content(ancestry_path, ancestry)

        layer_1_files_path = self.store.image_files_path(layer_1_id)
        self.store.put_content(layer_1_files_path, json.dumps(layer_1))

        layer_2_files_path = self.store.image_files_path(layer_2_id)
        self.store.put_content(layer_2_files_path, json.dumps(layer_2))

        diff_json = layers.get_image_diff_json(layer_2_id)
        diff = json.loads(diff_json)

        for type in ("deleted", "changed", "created"):
            assert type in diff
            assert type in diff[type]

########NEW FILE########
__FILENAME__ = test_mirrors
# -*- coding: utf-8 -*-

import mock
import requests

from docker_registry.lib import config
from docker_registry.lib import mirroring

import base

from docker_registry.core import compat
json = compat.json


def mock_lookup_source(path, stream=False, source=None):
    resp = requests.Response()
    resp.status_code = 200
    resp._content_consumed = True
    # resp.headers['X-Fake-Source-Header'] = 'foobar'
    if path.endswith('0145/layer'):
        resp._content = "abcdef0123456789xxxxxx=-//"
    elif path.endswith('0145/json'):
        resp._content = ('{"id": "cafebabe0145","created":"2014-02-03T16:47:06'
                         '.615279788Z"}')
    elif path.endswith('0145/ancestry'):
        resp._content = '["cafebabe0145"]'
    elif path.endswith('test/tags'):
        resp._content = '{"latest": "cafebabe0145", "0.1.2": "cafebabe0145"}'
    else:
        resp.status_code = 404

    return resp


class TestMirrorDecorator(base.TestCase):
    def setUp(self):
        config.load()
        config._config._config['mirroring'] = {
            'source': 'https://registry.mock'
        }
        self.cfg = config.load()

    def tearDown(self):
        del config._config._config['mirroring']

    def test_config_tampering(self):
        self.assertEqual(self.cfg.get('mirroring')['source'],
                         'https://registry.mock')

    def test_is_mirror(self):
        self.assertEqual(mirroring.is_mirror(), True)

    @mock.patch('docker_registry.lib.mirroring.lookup_source',
                mock_lookup_source)
    def test_source_lookup(self):
        resp = self.http_client.get('/v1/images/cafebabe0145/layer')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data, "abcdef0123456789xxxxxx=-//")

        resp_2 = self.http_client.get('/v1/images/cafebabe0145/json')
        self.assertEqual(resp_2.status_code, 200)
        # Note(dmp): unicode patch XXX not applied assume requests does the job
        json_data = json.loads(resp_2.data)
        assert 'id' in json_data
        assert 'created' in json_data
        self.assertEqual(json_data['id'], 'cafebabe0145')

        resp_3 = self.http_client.get('/v1/images/cafebabe0145/ancestry')
        self.assertEqual(resp_3.status_code, 200)
        # Note(dmp): unicode patch XXX not applied assume requests does the job
        json_data_2 = json.loads(resp_3.data)
        self.assertEqual(len(json_data_2), 1)
        self.assertEqual(json_data_2[0], 'cafebabe0145')

        resp_4 = self.http_client.get('/v1/images/doe587e8157/json')
        self.assertEqual(resp_4.status_code, 404)

    @mock.patch('docker_registry.lib.mirroring.lookup_source',
                mock_lookup_source)
    def test_source_lookup_tag(self):
        resp = self.http_client.get('/v1/repositories/testing/test/tags')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(
            resp.data,
            '{"latest": "cafebabe0145", "0.1.2": "cafebabe0145"}'
        )

        resp_2 = self.http_client.get('/v1/repositories/testing/bogus/tags')
        self.assertEqual(resp_2.status_code, 404)

########NEW FILE########
__FILENAME__ = test_run_gunicorn
# -*- coding: utf-8 -*-

import unittest

import docker_registry.run as run

import mock


class TestRunGunicorn(unittest.TestCase):
    @mock.patch('argparse.ArgumentParser.parse_args')
    @mock.patch('os.execl')
    def test_exec_gunicorn(self, mock_execl, mock_parse_args):
        run.run_gunicorn()

        self.assertEqual(mock_execl.call_count, 1)
        # ensure that the executable's path ends with 'gunicorn', so we have
        # some confidence that it called the correct executable
        self.assertTrue(mock_execl.call_args[0][0].endswith('gunicorn'))

    @mock.patch('argparse.ArgumentParser.parse_args')
    @mock.patch('os.execl')
    def test_parses_args(self, mock_execl, mock_parse_args):
        run.run_gunicorn()

        # ensure that argument parsing is happening
        mock_parse_args.assert_called_once_with()

    @mock.patch('sys.exit')
    @mock.patch('distutils.spawn.find_executable', autospec=True)
    @mock.patch('argparse.ArgumentParser.parse_args')
    @mock.patch('os.execl')
    def test_gunicorn_not_found(self, mock_execl, mock_parse_args,
                                mock_find_exec, mock_exit):
        mock_find_exec.return_value = None

        run.run_gunicorn()

        # ensure that sys.exit was called
        mock_exit.assert_called_once_with(1)

########NEW FILE########
__FILENAME__ = test_s3
# -*- coding: utf-8 -*-

import sys

import StringIO

from nose import tools

from docker_registry.core import exceptions
import docker_registry.testing as testing

from docker_registry.testing import mock_boto  # noqa

from . import mock_s3   # noqa


class StringIOWithError(StringIO.StringIO):
    '''Throw IOError after reaching EOF.'''

    def read(self, size):
        if self.pos == self.len:
            raise IOError('Reading beyond EOF')
        return StringIO.StringIO.read(self, size)


class TestDriver(testing.Driver):
    '''Extra tests for coverage completion.'''
    def __init__(self):
        self.scheme = 's3'
        self.path = ''
        self.config = testing.Config({})

    def tearDown(self):
        self._storage._boto_bucket.delete()
        super(TestDriver, self).tearDown()

    @tools.raises(exceptions.FileNotFoundError)
    def test_list_bucket(self):
        # Add a couple of bucket keys
        filename1 = self.gen_random_string()
        filename2 = self.gen_random_string()
        content = self.gen_random_string()
        self._storage.put_content(filename1, content)
        # Check bucket key is stored in normalized form
        self._storage.put_content(filename2 + '/', content)
        # Check both keys are in the bucket
        assert sorted([filename1, filename2]) == sorted(
            list(self._storage.list_directory()))
        # Check listing bucket raises exception after removing keys
        self._storage.remove(filename1)
        self._storage.remove(filename2)
        s = self._storage.list_directory()
        s.next()

    def test_stream_write(self):
        # Check stream write with buffer bigger than default 5MB
        self._storage.buffer_size = 7 * 1024 * 1024
        filename = self.gen_random_string()
        # Test 8MB
        content = self.gen_random_string(8 * 1024 * 1024)
        io = StringIOWithError(content)
        assert not self._storage.exists(filename)
        try:
            self._storage.stream_write(filename, io)
        except IOError:
            pass
        assert self._storage.exists(filename)
        # Test that EOFed io string throws IOError on lib/storage/s3
        try:
            self._storage.stream_write(filename, io)
        except IOError:
            pass
        # Cleanup
        io.close()
        self._storage.remove(filename)
        self._storage.buffer_size = 5 * 1024 * 1024
        assert not self._storage.exists(filename)

    def test_init_path(self):
        # s3 storage _init_path result keys are relative (no / at start)
        root_path = self._storage._root_path
        if root_path.startswith('/'):
            self._storage._root_path = root_path[1:]
            assert not self._storage._init_path().startswith('/')
            self._storage._root_path = root_path

    def test_debug_key(self):
        # Create a valid s3 key object to debug
        filename = self.gen_random_string()
        content = self.gen_random_string()
        self._storage.put_content(filename, content)

        # Get filename key path as stored
        key_path = self._storage._init_path(filename)
        key = self._storage._boto_bucket.lookup(key_path)
        self._storage._debug_key(key)

        # Capture debugged output
        saved_stdout = sys.stdout
        output = StringIO.StringIO()
        sys.stdout = output

        # As key is mocked for unittest purposes, we call make_request directly
        dummy = "################\n('d', 1)\n{'v': 2}\n################\n"
        # '{}\n{}\n{}\n{}\n'.format(
        #     '#' * 16, ('d', 1), {'v': 2}, '#' * 16)
        result = self._storage._boto_bucket.connection.make_request(
            'd', 1, v=2)
        assert output.getvalue() == dummy
        assert result == 'request result'

        sys.stdout = saved_stdout

        # We don't call self._storage.remove(filename) here to ensure tearDown
        # cleanup properly and that other tests keep running as expected.

########NEW FILE########
__FILENAME__ = test_tags
# -*- coding: utf-8 -*-

import base

from docker_registry.core import compat
json = compat.json


class TestTags(base.TestCase):

    def test_simple(self, repos_name=None):
        if repos_name is None:
            repos_name = self.gen_random_string()
        image_id = self.gen_random_string()
        layer_data = self.gen_random_string(1024)
        self.upload_image(image_id, parent_id=None, layer=layer_data)

       # test tags create
        url = '/v1/repositories/foo/{0}/tags/latest'.format(repos_name)
        headers = {'User-Agent':
                   'docker/0.7.2-dev go/go1.2 os/ostest arch/archtest'}
        resp = self.http_client.put(url,
                                    headers=headers,
                                    data=json.dumps(image_id))
        self.assertEqual(resp.status_code, 200, resp.data)
        url = '/v1/repositories/foo/{0}/tags/test'.format(repos_name)
        resp = self.http_client.put(url,
                                    data=json.dumps(image_id))
        self.assertEqual(resp.status_code, 200, resp.data)

        # test tags read
        url = '/v1/repositories/foo/{0}/tags/latest'.format(repos_name)
        resp = self.http_client.get(url)
        self.assertEqual(resp.status_code, 200, resp.data)
        # Note(dmp): unicode patch XXX not applied assume requests does the job
        self.assertEqual(json.loads(resp.data), image_id, resp.data)

        # test repository json
        url = '/v1/repositories/foo/{0}/json'.format(repos_name)
        resp = self.http_client.get(url)
        self.assertEqual(resp.status_code, 200, resp.data)
        # Note(dmp): unicode patch XXX not applied assume requests does the job
        props = json.loads(resp.data)
        self.assertEqual(props['docker_version'], '0.7.2-dev')
        self.assertEqual(props['docker_go_version'], 'go1.2')
        self.assertEqual(props['os'], 'ostest')
        self.assertEqual(props['arch'], 'archtest')

        # test repository tags json
        url = '/v1/repositories/foo/{0}/tags/latest/json'.format(repos_name)
        resp = self.http_client.get(url)
        self.assertEqual(resp.status_code, 200, resp.data)
        # Note(dmp): unicode patch XXX not applied assume requests does the job
        props = json.loads(resp.data)
        self.assertEqual(props['docker_version'], '0.7.2-dev')
        self.assertEqual(props['docker_go_version'], 'go1.2')
        self.assertEqual(props['os'], 'ostest')
        self.assertEqual(props['arch'], 'archtest')

       # test tags update
        url = '/v1/repositories/foo/{0}/tags/latest'.format(repos_name)
        headers = {'User-Agent':
                   'docker/0.7.2-dev go/go1.2 os/ostest arch/changedarch'}
        resp = self.http_client.put(url,
                                    headers=headers,
                                    data=json.dumps(image_id))
        self.assertEqual(resp.status_code, 200, resp.data)
        url = '/v1/repositories/foo/{0}/tags/test'.format(repos_name)
        resp = self.http_client.put(url,
                                    headers=headers,
                                    data=json.dumps(image_id))
        self.assertEqual(resp.status_code, 200, resp.data)

        # test repository latest tag json update
        url = '/v1/repositories/foo/{0}/tags/latest/json'.format(repos_name)
        resp = self.http_client.get(url)
        self.assertEqual(resp.status_code, 200, resp.data)
        # Note(dmp): unicode patch XXX not applied assume requests does the job
        props = json.loads(resp.data)
        self.assertEqual(props['docker_version'], '0.7.2-dev')
        self.assertEqual(props['docker_go_version'], 'go1.2')
        self.assertEqual(props['os'], 'ostest')
        self.assertEqual(props['arch'], 'changedarch')

        # test repository test tag json update
        url = '/v1/repositories/foo/{0}/tags/test/json'.format(repos_name)
        resp = self.http_client.get(url)
        self.assertEqual(resp.status_code, 200, resp.data)
        # Note(dmp): unicode patch XXX not applied assume requests does the job
        props = json.loads(resp.data)
        self.assertEqual(props['docker_version'], '0.7.2-dev')
        self.assertEqual(props['docker_go_version'], 'go1.2')
        self.assertEqual(props['os'], 'ostest')
        self.assertEqual(props['arch'], 'changedarch')

        # test tags list
        url = '/v1/repositories/foo/{0}/tags'.format(repos_name)
        resp = self.http_client.get(url)
        self.assertEqual(resp.status_code, 200, resp.data)
        # Note(dmp): unicode patch XXX not applied assume requests does the job
        self.assertEqual(len(json.loads(resp.data)), 2, resp.data)

        # test tag delete
        url = '/v1/repositories/foo/{0}/tags/latest'.format(repos_name)
        resp = self.http_client.delete(url)
        self.assertEqual(resp.status_code, 200, resp.data)
        url = '/v1/repositories/foo/{0}/tags'.format(repos_name)
        resp = self.http_client.get(url)
        self.assertEqual(resp.status_code, 200, resp.data)
        url = '/v1/repositories/foo/{0}/tags/latest'.format(repos_name)
        resp = self.http_client.get(url)
        self.assertEqual(resp.status_code, 404, resp.data)

        # test whole delete
        url = '/v1/repositories/foo/{0}/'.format(repos_name)
        resp = self.http_client.delete(url)
        self.assertEqual(resp.status_code, 200, resp.data)
        url = '/v1/repositories/foo/{0}/tags'.format(repos_name)
        resp = self.http_client.get(url)
        self.assertEqual(resp.status_code, 404, resp.data)

    def test_notfound(self):
        notexist = self.gen_random_string()
        url = '/v1/repositories/{0}/bar/tags'.format(notexist)
        resp = self.http_client.get(url)
        self.assertEqual(resp.status_code, 404, resp.data)

    def test_special_chars(self):
        repos_name = '{0}%$_-test'.format(self.gen_random_string(5))
        self.test_simple(repos_name)

########NEW FILE########
__FILENAME__ = workflow
import hashlib
import os

import requests
sess = requests.Session()
adapter = requests.adapters.HTTPAdapter(pool_connections=100, pool_maxsize=100)
sess.mount('https://', adapter)
requests = sess

from docker_registry.lib import checksums
from docker_registry.lib import config
import docker_registry.storage as storage

import base

from docker_registry.core import compat
json = compat.json
StringIO = compat.StringIO

cfg = config.load()

ua = 'docker/1.0.0 registry test pretending to be docker'


class TestWorkflow(base.TestCase):

    # Dev server needs to run on port 5000 in order to run this test
    registry_endpoint = os.environ.get(
        'DOCKER_REGISTRY_ENDPOINT',
        'https://registrystaging-docker.dotcloud.com')
    #registry_endpoint = 'http://localhost:5000'
    index_endpoint = os.environ.get(
        'DOCKER_INDEX_ENDPOINT',
        'https://indexstaging-docker.dotcloud.com')
    # export DOCKER_CREDS="login:password"
    user_credentials = os.environ['DOCKER_CREDS'].split(':')
    cookies = None

    def generate_chunk(self, data):
        bufsize = 1024
        io = StringIO(data)
        while True:
            buf = io.read(bufsize)
            if not buf:
                return
            yield buf
        io.close()

    def update_cookies(self, response):
        cookies = response.cookies
        if cookies:
            self.cookies = cookies

    def upload_image(self, image_id, parent_id, token):
        layer = self.gen_random_string(7 * 1024 * 1024)
        json_obj = {
            'id': image_id
        }
        if parent_id:
            json_obj['parent'] = parent_id
        json_data = json.dumps(json_obj)
        h = hashlib.sha256(json_data + '\n')
        h.update(layer)
        layer_checksum = 'sha256:{0}'.format(h.hexdigest())
        resp = requests.put('{0}/v1/images/{1}/json'.format(
            self.registry_endpoint, image_id),
            data=json_data,
            headers={'Authorization': 'Token ' + token,
                     'User-Agent': ua,
                     'X-Docker-Checksum': layer_checksum},
            cookies=self.cookies)
        self.assertEqual(resp.status_code, 200, resp.text)
        self.update_cookies(resp)
        resp = requests.put('{0}/v1/images/{1}/layer'.format(
            self.registry_endpoint, image_id),
            data=self.generate_chunk(layer),
            headers={'Authorization': 'Token ' + token,
                     'User-Agent': ua},
            cookies=self.cookies)
        self.assertEqual(resp.status_code, 200, resp.text)
        self.update_cookies(resp)
        return {'id': image_id, 'checksum': layer_checksum}

    def update_tag(self, namespace, repos, image_id, tag_name):
        resp = requests.put('{0}/v1/repositories/{1}/{2}/tags/{3}'.format(
            self.registry_endpoint, namespace, repos, tag_name),
            data=json.dumps(image_id),
            cookies=self.cookies)
        self.assertEqual(resp.status_code, 200, resp.text)
        self.update_cookies(resp)

    def docker_push(self):
        # Test Push
        self.image_id = self.gen_random_string()
        self.parent_id = self.gen_random_string()
        image_id = self.image_id
        parent_id = self.parent_id
        namespace = self.user_credentials[0]
        repos = self.gen_random_string()
        # Docker -> Index
        images_json = json.dumps([{'id': image_id}, {'id': parent_id}])
        resp = requests.put('{0}/v1/repositories/{1}/{2}/'.format(
            self.index_endpoint, namespace, repos),
            auth=tuple(self.user_credentials),
            headers={'X-Docker-Token': 'true',
                     'User-Agent': ua},
            data=images_json)
        self.assertEqual(resp.status_code, 200, resp.text)
        token = resp.headers.get('x-docker-token')
        # Docker -> Registry
        images_json = []
        images_json.append(self.upload_image(parent_id, None, token))
        images_json.append(self.upload_image(image_id, parent_id, token))
        # Updating the tags does not need a token, it will use the Cookie
        self.update_tag(namespace, repos, image_id, 'latest')
        # Docker -> Index
        resp = requests.put('{0}/v1/repositories/{1}/{2}/images'.format(
            self.index_endpoint, namespace, repos),
            auth=tuple(self.user_credentials),
            headers={'X-Endpoints': self.registry_endpoint,
                     'User-Agent': ua},
            data=json.dumps(images_json))
        self.assertEqual(resp.status_code, 204)
        return (namespace, repos)

    def fetch_image(self, image_id):
        """Return image json metadata, checksum and its blob."""
        resp = requests.get('{0}/v1/images/{1}/json'.format(
            self.registry_endpoint, image_id),
            cookies=self.cookies)
        self.assertEqual(resp.status_code, 200, resp.text)
        self.update_cookies(resp)
        json_data = resp.text
        checksum = resp.headers['x-docker-checksum']
        resp = requests.get('{0}/v1/images/{1}/layer'.format(
            self.registry_endpoint, image_id),
            cookies=self.cookies)
        self.assertEqual(resp.status_code, 200, resp.text)
        self.update_cookies(resp)
        return (json_data, checksum, resp.text)

    def docker_pull(self, namespace, repos):
        # Test pull
        # Docker -> Index
        resp = requests.get('{0}/v1/repositories/{1}/{2}/images'.format(
            self.index_endpoint, namespace, repos),
            auth=tuple(self.user_credentials),
            headers={'X-Docker-Token': 'true'})
        self.assertEqual(resp.status_code, 200)
        token = resp.headers.get('x-docker-token')
        # Here we should use the 'X-Endpoints' returned in a real environment
        # Docker -> Registry
        resp = requests.get('{0}/v1/repositories/{1}/{2}/tags/latest'.format(
                            self.registry_endpoint, namespace, repos),
                            headers={'Authorization': 'Token ' + token})
        self.assertEqual(resp.status_code, 200, resp.text)
        self.cookies = resp.cookies
        # Docker -> Registry
        # Note(dmp): unicode patch XXX not applied assume requests does the job
        image_id = json.loads(resp.text)
        resp = requests.get('{0}/v1/images/{1}/ancestry'.format(
            self.registry_endpoint, image_id),
            cookies=self.cookies)
        self.update_cookies(resp)
        self.assertEqual(resp.status_code, 200, resp.text)
        # Note(dmp): unicode patch XXX not applied assume requests does the job
        ancestry = json.loads(resp.text)
        # We got the ancestry, let's fetch all the images there
        for image_id in ancestry:
            json_data, checksum, blob = self.fetch_image(image_id)
            # check queried checksum and local computed checksum from the image
            # are the same
            tmpfile = StringIO()
            tmpfile.write(blob)
            tmpfile.seek(0)
            computed_checksum = checksums.compute_simple(tmpfile, json_data)
            tmpfile.close()
            self.assertEqual(checksum, computed_checksum)
        # Remove the repository
        resp = requests.delete('{0}/v1/repositories/{1}/{2}/'.format(
            self.registry_endpoint, namespace, repos), cookies=self.cookies)
        self.assertEqual(resp.status_code, 200, resp.text)
        self.update_cookies(resp)
        # Remove image_id, then parent_id
        store = storage.load()
        store.remove(os.path.join(store.images, self.image_id))
        store.remove(os.path.join(store.images, self.parent_id))

    def test_workflow(self):
        (namespace, repos) = self.docker_push()
        self.docker_pull(namespace, repos)

########NEW FILE########
