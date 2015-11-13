__FILENAME__ = benchmark
from nydus.db import create_cluster
import time

partition_cluster = create_cluster({
    'engine': 'nydus.db.backends.redis.Redis',
    'router': 'nydus.db.routers.keyvalue.PartitionRouter',
    'hosts': {
        0: {'db': 0},
        1: {'db': 1},
        2: {'db': 2},
        3: {'db': 3},
    },
})

ketama_cluster = create_cluster({
    'engine': 'nydus.db.backends.redis.Redis',
    'router': 'nydus.db.routers.keyvalue.ConsistentHashingRouter',
    'hosts': {
        0: {'db': 0},
        1: {'db': 1},
        2: {'db': 2},
        3: {'db': 3},
    },
})

roundrobin_cluster = create_cluster({
    'engine': 'nydus.db.backends.redis.Redis',
    'router': 'nydus.db.routers.RoundRobinRouter',
    'hosts': {
        0: {'db': 0},
        1: {'db': 1},
        2: {'db': 2},
        3: {'db': 3},
    },
})


def test_redis_normal(cluster):
    cluster.set('foo', 'bar')
    cluster.get('foo')
    cluster.set('biz', 'bar')
    cluster.get('biz')
    cluster.get('bar')


def test_redis_map(cluster):
    with cluster.map() as conn:
        for n in xrange(5):
            conn.set('foo', 'bar')
            conn.get('foo')
            conn.set('biz', 'bar')
            conn.get('biz')
            conn.get('bar')


def main(iterations=1000):
    for cluster in ('partition_cluster', 'ketama_cluster', 'roundrobin_cluster'):
        for func in ('test_redis_normal', 'test_redis_map'):
            print "Running %r on %r" % (func, cluster)
            s = time.time()
            for x in xrange(iterations):
                globals()[func](globals()[cluster])
            t = (time.time() - s) * 1000
            print "  %.3fms per iteration" % (t / iterations,)


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = conf
"""
nydus.conf
~~~~~~~~~~

:copyright: (c) 2011-2012 DISQUS.
:license: Apache License 2.0, see LICENSE for more details.
"""

import warnings

CONNECTIONS = {}


def configure(kwargs):
    for k, v in kwargs.iteritems():
        if k.upper() != k:
            warnings.warn('Invalid setting, \'%s\' which is not defined by Nydus' % k)
        elif k not in globals():
            warnings.warn('Invalid setting, \'%s\' which is not defined by Nydus' % k)
        else:
            globals()[k] = v

########NEW FILE########
__FILENAME__ = ketama
"""
    Ketama consistent hash algorithm.

    Rewrited from the original source: http://www.audioscrobbler.net/development/ketama/

"""
__author__ = "Andrey Nikishaev"
__email__ = "creotiv@gmail.com"
__version__ = 0.1
__status__ = "productrion"

__all__ = ['Ketama']

import hashlib
import math
from bisect import bisect


class Ketama(object):

    def __init__(self, nodes=None, weights=None):
        """
            nodes   - List of nodes(strings)
            weights - Dictionary of node wheights where keys are nodes names.
                      if not set, all nodes will be equal.
        """
        self._hashring = dict()
        self._sorted_keys = []

        self._nodes = set(nodes or [])
        self._weights = weights if weights else {}

        self._build_circle()

    def _build_circle(self):
        """
            Creates hash ring.
        """
        total_weight = 0
        for node in self._nodes:
            total_weight += self._weights.get(node, 1)

        for node in self._nodes:
            weight = self._weights.get(node, 1)

            ks = math.floor((40 * len(self._nodes) * weight) / total_weight)

            for i in xrange(0, int(ks)):
                b_key = self._md5_digest('%s-%s-salt' % (node, i))

                for l in xrange(0, 4):
                    key = ((b_key[3 + l * 4] << 24)
                           | (b_key[2 + l * 4] << 16)
                           | (b_key[1 + l * 4] << 8)
                           | b_key[l * 4])

                    self._hashring[key] = node
                    self._sorted_keys.append(key)

        self._sorted_keys.sort()

    def _get_node_pos(self, key):
        """
            Return node position(integer) for a given key. Else return None
        """
        if not self._hashring:
            return None

        key = self._gen_key(key)

        nodes = self._sorted_keys
        pos = bisect(nodes, key)

        if pos == len(nodes):
            return 0
        return pos

    def _gen_key(self, key):
        """
            Return long integer for a given key, that represent it place on
            the hash ring.
        """
        b_key = self._md5_digest(key)
        return self._hashi(b_key, lambda x: x)

    def _hashi(self, b_key, fn):
        return ((b_key[fn(3)] << 24)
                | (b_key[fn(2)] << 16)
                | (b_key[fn(1)] << 8)
                | b_key[fn(0)])

    def _md5_digest(self, key):
        return map(ord, hashlib.md5(key).digest())

    def remove_node(self, node):
        """
            Removes node from circle and rebuild it.
        """
        try:
            self._nodes.remove(node)
            del self._weights[node]
        except (KeyError, ValueError):
            pass
        self._hashring = dict()
        self._sorted_keys = []

        self._build_circle()

    def add_node(self, node, weight=1):
        """
            Adds node to circle and rebuild it.
        """
        self._nodes.add(node)
        self._weights[node] = weight
        self._hashring = dict()
        self._sorted_keys = []

        self._build_circle()

    def get_node(self, key):
        """
            Return node for a given key. Else return None.
        """
        pos = self._get_node_pos(key)
        if pos is None:
            return None
        return self._hashring[self._sorted_keys[pos]]


if __name__ == '__main__':
    def test(k):
        data = {}
        for i in xrange(REQUESTS):
            tower = k.get_node('a' + str(i))
            data.setdefault(tower, 0)
            data[tower] += 1
        print 'Number of caches on each node: '
        print data
        print ''

        print k.get_node('Aplple')
        print k.get_node('Hello')
        print k.get_node('Data')
        print k.get_node('Computer')

    NODES = [
        '192.168.0.1:6000', '192.168.0.1:6001', '192.168.0.1:6002',
        '192.168.0.1:6003', '192.168.0.1:6004', '192.168.0.1:6005',
        '192.168.0.1:6006', '192.168.0.1:6008', '192.168.0.1:6007'
    ]
    REQUESTS = 1000

    k = Ketama(NODES)

    test(k)

    k.remove_node('192.168.0.1:6007')

    test(k)

    k.add_node('192.168.0.1:6007')

    test(k)

########NEW FILE########
__FILENAME__ = base
"""
nydus.db.backends.base
~~~~~~~~~~~~~~~~~~~~~~

:copyright: (c) 2011-2012 DISQUS.
:license: Apache License 2.0, see LICENSE for more details.
"""

__all__ = ('BaseConnection',)

from nydus.db.base import BaseCluster


class BasePipeline(object):
    """
    Base Pipeline class.

    This basically is absolutely useless, and just provides a sample
    API for dealing with pipelined commands.
    """
    def __init__(self, connection):
        self.connection = connection
        self.pending = []

    def add(self, command):
        """
        Add a command to the pending execution pipeline.
        """
        self.pending.append(command)

    def execute(self):
        """
        Execute all pending commands and return a list of the results
        ordered by call.
        """
        raise NotImplementedError


class BaseConnection(object):
    """
    Base connection class.

    Child classes should implement at least
    connect() and disconnect() methods.
    """

    retryable_exceptions = ()
    supports_pipelines = False

    def __init__(self, num, **options):
        self._connection = None
        self.num = num

    def __getattr__(self, name):
        return getattr(self.connection, name)

    @property
    def identifier(self):
        return repr(self)

    @property
    def connection(self):
        if self._connection is None:
            self._connection = self.connect()
        return self._connection

    def close(self):
        """
        Close the connection if it is open.
        """
        if self._connection:
            self.disconnect()
        self._connection = None

    def connect(self):
        """
        Connect.

        Must return a connection object.
        """
        raise NotImplementedError

    def disconnect(self):
        """
        Disconnect.
        """
        raise NotImplementedError

    def get_pipeline(self):
        """
        Return a new pipeline instance (bound to this connection).
        """
        raise NotImplementedError

    @classmethod
    def get_cluster(cls):
        """
        Return the default cluster type for this backend.
        """
        return BaseCluster

########NEW FILE########
__FILENAME__ = memcache
"""
nydus.db.backends.memcache
~~~~~~~~~~~~~~~~~~~~~~~~~~

:copyright: (c) 2012 DISQUS.
:license: Apache License 2.0, see LICENSE for more details.
"""

from __future__ import absolute_import

import pylibmc

from itertools import izip
from nydus.db.backends import BaseConnection, BasePipeline
from nydus.db.promise import EventualCommand
from nydus.utils import peek


class Memcache(BaseConnection):

    retryable_exceptions = frozenset([pylibmc.Error])
    supports_pipelines = True

    def __init__(self, num, host='localhost', port=11211, binary=True,
            behaviors=None, **options):
        self.host = host
        self.port = port
        self.binary = binary
        self.behaviors = behaviors
        super(Memcache, self).__init__(num)

    @property
    def identifier(self):
        mapping = vars(self)
        return "memcache://%(host)s:%(port)s/" % mapping

    def connect(self):
        host = "%s:%i" % (self.host, self.port)
        return pylibmc.Client([host], binary=self.binary, behaviors=self.behaviors)

    def disconnect(self):
        self.connection.disconnect_all()

    def get_pipeline(self, *args, **kwargs):
        return MemcachePipeline(self)


class MemcachePipeline(BasePipeline):
    def execute(self):
        grouped = regroup_commands(self.pending)
        results = resolve_grouped_commands(grouped, self.connection)
        return results


def grouped_args_for_command(command):
    """
    Returns a list of arguments that are shared for this command.

    When comparing similar commands, these arguments represent the
    groupable signature for said commands.
    """
    if command.get_name() == 'set':
        return command.get_args()[2:]
    return command.get_args()[1:]


def grouped_command(commands):
    """
    Given a list of commands (which are assumed groupable), return
    a new command which is a batch (multi) command.

    For ``set`` commands the outcome will be::

        set_multi({key: value}, **kwargs)

    For ``get`` and ``delete`` commands, the outcome will be::

        get_multi(list_of_keys, **kwargs)

    (Or respectively ``delete_multi``)
    """
    base = commands[0]
    name = base.get_name()
    multi_command = EventualCommand('%s_multi' % name)
    if name in ('get', 'delete'):
        args = [c.get_args()[0] for c in commands]
    elif base.get_name() == 'set':
        args = dict(c.get_args()[0:2] for c in commands)
    else:
        raise ValueError('Command not supported: %r' % (base.get_name(),))

    multi_command(args, *grouped_args_for_command(base), **base.get_kwargs())

    return multi_command


def can_group_commands(command, next_command):
    """
    Returns a boolean representing whether these commands can be
    grouped together or not.

    A few things are taken into account for this decision:

    For ``set`` commands:

    - Are all arguments other than the key/value the same?

    For ``delete`` and ``get`` commands:

    - Are all arguments other than the key the same?
    """
    multi_capable_commands = ('get', 'set', 'delete')

    if next_command is None:
        return False

    name = command.get_name()

    # TODO: support multi commands
    if name not in multi_capable_commands:
        return False

    if name != next_command.get_name():
        return False

    # if the shared args (key, or key/value) do not match, we cannot group
    if grouped_args_for_command(command) != grouped_args_for_command(next_command):
        return False

    # If the keyword arguments do not much (e.g. key_prefix, or timeout on set)
    # then we cannot group
    if command.get_kwargs() != next_command.get_kwargs():
        return False

    return True


def regroup_commands(commands):
    """
    Returns a list of tuples:

        [(command_to_run, [list, of, commands])]

    If the list of commands has a single item, the command was not grouped.
    """
    grouped = []
    pending = []

    def group_pending():
        if not pending:
            return

        new_command = grouped_command(pending)
        result = []
        while pending:
            result.append(pending.pop(0))
        grouped.append((new_command, result))

    for command, next_command in peek(commands):
        # if the previous command was a get, and this is a set we must execute
        # any pending commands
        # TODO: unless this command is a get_multi and it matches the same option
        # signature
        if can_group_commands(command, next_command):
            # if previous command does not match this command
            if pending and not can_group_commands(pending[0], command):
                group_pending()

            pending.append(command)
        else:
            # if pending exists for this command, group it
            if pending and can_group_commands(pending[0], command):
                pending.append(command)
            else:
                grouped.append((command.clone(), [command]))

            # We couldn't group with previous command, so ensure we bubble up
            group_pending()

    group_pending()

    return grouped


def resolve_grouped_commands(grouped, connection):
    results = {}

    for master_command, grouped_commands in grouped:
        result = master_command.resolve(connection)

        # this command was not grouped
        if len(grouped_commands) == 1:
            results[grouped_commands[0]] = result
        else:
            if isinstance(result, dict):
                # XXX: assume first arg is key
                for command in grouped_commands:
                    results[command] = result.get(command.get_args()[0])
            else:
                for command, value in izip(grouped_commands, result):
                    results[command] = value

    return results

########NEW FILE########
__FILENAME__ = pycassa
"""
nydus.db.backends.pycassa
~~~~~~~~~~~~~~~~~~~~~~~~~

:copyright: (c) 2011-2012 DISQUS.
:license: Apache License 2.0, see LICENSE for more details.
"""

from __future__ import absolute_import

import collections
from nydus.db.base import BaseCluster
from nydus.db.backends import BaseConnection
from pycassa import ConnectionPool


class Pycassa(BaseConnection):
    def __init__(self, num, keyspace, hosts=['localhost'], **options):
        self.keyspace = keyspace
        self.hosts = hosts
        self.options = options
        super(Pycassa, self).__init__(num)

    @property
    def identifier(self):
        return "pycassa://%(hosts)s/%(keyspace)s" % {
            'hosts': ','.join(self.hosts),
            'keyspace': self.keyspace,
        }

    def connect(self):
        return ConnectionPool(keyspace=self.keyspace, server_list=self.hosts, **self.options)

    def disconnect(self):
        self.connection.dispose()

    @classmethod
    def get_cluster(cls):
        return PycassaCluster


class PycassaCluster(BaseCluster):
    """
    A PycassaCluster has a single host as pycassa internally handles routing
    and communication within a set of nodes.
    """
    def __init__(self, hosts=None, keyspace=None, backend=Pycassa, **kwargs):
        assert isinstance(hosts, collections.Iterable), 'hosts must be an iterable'
        assert keyspace, 'keyspace must be set'

        return super(PycassaCluster, self).__init__(
            hosts={
                0: {
                    'hosts': hosts,
                    'keyspace': keyspace,
                },
            },
            backend=backend,
            **kwargs
        )

########NEW FILE########
__FILENAME__ = redis
"""
nydus.db.backends.redis
~~~~~~~~~~~~~~~~~~~~~~~

:copyright: (c) 2011-2012 DISQUS.
:license: Apache License 2.0, see LICENSE for more details.
"""

from __future__ import absolute_import

from itertools import izip
from redis import Redis as RedisClient
from redis import ConnectionError, InvalidResponse

from nydus.db.backends import BaseConnection, BasePipeline


class RedisPipeline(BasePipeline):
    def __init__(self, connection):
        self.pending = []
        self.connection = connection
        self.pipe = connection.pipeline()

    def add(self, command):
        name, args, kwargs = command.get_command()
        self.pending.append(command)
        # ensure the command is executed in the pipeline
        getattr(self.pipe, name)(*args, **kwargs)

    def execute(self):
        return dict(izip(self.pending, self.pipe.execute()))


class Redis(BaseConnection):
    # Exceptions that can be retried by this backend
    retryable_exceptions = frozenset([ConnectionError, InvalidResponse])
    supports_pipelines = True

    def __init__(self, num, host='localhost', port=6379, db=0, timeout=None,
                 password=None, unix_socket_path=None):
        self.host = host
        self.port = port
        self.db = db
        self.unix_socket_path = unix_socket_path
        self.timeout = timeout
        self.__password = password
        super(Redis, self).__init__(num)

    @property
    def identifier(self):
        mapping = vars(self)
        mapping['klass'] = self.__class__.__name__
        return "redis://%(host)s:%(port)s/%(db)s" % mapping

    def connect(self):
        return RedisClient(
            host=self.host, port=self.port, db=self.db,
            socket_timeout=self.timeout, password=self.__password,
            unix_socket_path=self.unix_socket_path)

    def disconnect(self):
        self.connection.disconnect()

    def get_pipeline(self, *args, **kwargs):
        return RedisPipeline(self)

########NEW FILE########
__FILENAME__ = riak
"""
nydus.db.backends.riak
~~~~~~~~~~~~~~~~~~~~~~

:copyright: (c) 2011-2012 DISQUS.
:license: Apache License 2.0, see LICENSE for more details.
"""

from __future__ import absolute_import

import socket
import httplib

from riak import RiakClient, RiakError

from nydus.db.backends import BaseConnection


class Riak(BaseConnection):
    # Exceptions that can be retried by this backend
    retryable_exceptions = frozenset([socket.error, httplib.HTTPException, RiakError])
    supports_pipelines = False

    def __init__(self, num, host='127.0.0.1', port=8098, prefix='riak', mapred_prefix='mapred', client_id=None,
        transport_class=None, solr_transport_class=None, transport_options=None, **options):

        self.host = host
        self.port = port
        self.prefix = prefix
        self.mapred_prefix = mapred_prefix
        self.client_id = client_id
        self.transport_class = transport_class
        self.solr_transport_class = solr_transport_class
        self.transport_options = transport_options or {}
        super(Riak, self).__init__(num)

    @property
    def identifier(self):
        mapping = vars(self)
        return "http://%(host)s:%(port)s/%(prefix)s" % mapping

    def connect(self):
        return RiakClient(
            host=self.host, port=self.port, prefix=self.prefix,
            mapred_prefix=self.mapred_prefix, client_id=self.client_id,
            transport_class=self.transport_class, solr_transport_class=self.solr_transport_class,
            transport_options=self.transport_options)

    def disconnect(self):
        pass

########NEW FILE########
__FILENAME__ = thoonk
"""
nydus.db.backends.thoonk
~~~~~~~~~~~~~~~~~~~~~~~~

:copyright: (c) 2011-2012 DISQUS.
:license: Apache License 2.0, see LICENSE for more details.
"""

from __future__ import absolute_import

from thoonk import Pubsub

from redis import RedisError

from nydus.db.backends import BaseConnection


class Thoonk(BaseConnection):
    # Exceptions that can be retried by this backend
    retryable_exceptions = frozenset([RedisError])
    supports_pipelines = False

    def __init__(self, num, host='localhost', port=6379, db=0, timeout=None, listen=False):
        self.host = host
        self.port = port
        self.db = db
        self.timeout = timeout
        self.pubsub = None
        self.listen = listen
        super(Thoonk, self).__init__(num)

    @property
    def identifier(self):
        mapping = vars(self)
        mapping['klass'] = self.__class__.__name__
        return "redis://%(host)s:%(port)s/%(db)s" % mapping

    def connect(self):
        return Pubsub(host=self.host, port=self.port, db=self.db, listen=self.listen)

    def disconnect(self):
        self.connection.close()

    def flushdb(self):
        """the tests assume this function exists for all redis-like backends"""
        self.connection.redis.flushdb()

########NEW FILE########
__FILENAME__ = base
"""
nydus.db.base
~~~~~~~~~~~~~

:copyright: (c) 2011-2012 DISQUS.
:license: Apache License 2.0, see LICENSE for more details.
"""

__all__ = ('LazyConnectionHandler', 'BaseCluster')

import collections
from nydus.db.map import DistributedContextManager
from nydus.db.routers import BaseRouter, routing_params
from nydus.utils import apply_defaults


def iter_hosts(hosts):
    # this can either be a dictionary (with the key acting as the numeric
    # index) or it can be a sorted list.
    if isinstance(hosts, collections.Mapping):
        return hosts.iteritems()
    return enumerate(hosts)


def create_connection(Connection, num, host_settings, defaults):
    # host_settings can be an iterable or a dictionary depending on the style
    # of connection (some connections share options and simply just need to
    # pass a single host, or a list of hosts)
    if isinstance(host_settings, collections.Mapping):
        return Connection(num, **apply_defaults(host_settings, defaults or {}))
    elif isinstance(host_settings, collections.Iterable):
        return Connection(num, *host_settings, **defaults or {})
    return Connection(num, host_settings, **defaults or {})


class BaseCluster(object):
    """
    Holds a cluster of connections.
    """
    class MaxRetriesExceededError(Exception):
        pass

    def __init__(self, hosts, backend, router=BaseRouter, max_connection_retries=20, defaults=None):
        self.hosts = dict(
            (conn_number, create_connection(backend, conn_number, host_settings, defaults))
            for conn_number, host_settings
            in iter_hosts(hosts)
        )
        self.max_connection_retries = max_connection_retries
        self.install_router(router)

    def __len__(self):
        return len(self.hosts)

    def __getitem__(self, name):
        return self.hosts[name]

    def __getattr__(self, name):
        return CallProxy(self, name)

    def __iter__(self):
        for name in self.hosts.iterkeys():
            yield name

    def install_router(self, router):
        self.router = router(self)

    def execute(self, path, args, kwargs):
        connections = self.__connections_for(path, args=args, kwargs=kwargs)

        results = []
        for conn in connections:
            for retry in xrange(self.max_connection_retries):
                func = conn
                for piece in path.split('.'):
                    func = getattr(func, piece)
                try:
                    results.append(func(*args, **kwargs))
                except tuple(conn.retryable_exceptions), e:
                    if not self.router.retryable:
                        raise e
                    elif retry == self.max_connection_retries - 1:
                        raise self.MaxRetriesExceededError(e)
                    else:
                        conn = self.__connections_for(path, retry_for=conn.num, args=args, kwargs=kwargs)[0]
                else:
                    break

        # If we only had one db to query, we simply return that res
        if len(results) == 1:
            return results[0]
        else:
            return results

    def disconnect(self):
        """Disconnects all connections in cluster"""
        for connection in self.hosts.itervalues():
            connection.disconnect()

    def get_conn(self, *args, **kwargs):
        """
        Returns a connection object from the router given ``args``.

        Useful in cases where a connection cannot be automatically determined
        during all steps of the process. An example of this would be
        Redis pipelines.
        """
        connections = self.__connections_for('get_conn', args=args, kwargs=kwargs)

        if len(connections) is 1:
            return connections[0]
        else:
            return connections

    def map(self, workers=None, **kwargs):
        return DistributedContextManager(self, workers, **kwargs)

    @routing_params
    def __connections_for(self, attr, args, kwargs, **fkwargs):
        return [self[n] for n in self.router.get_dbs(attr=attr, args=args, kwargs=kwargs, **fkwargs)]


class CallProxy(object):
    """
    Handles routing function calls to the proper connection.
    """
    def __init__(self, cluster, path):
        self.__cluster = cluster
        self.__path = path

    def __call__(self, *args, **kwargs):
        return self.__cluster.execute(self.__path, args, kwargs)

    def __getattr__(self, name):
        return CallProxy(self.__cluster, self.__path + '.' + name)


class LazyConnectionHandler(dict):
    """
    Maps clusters of connections within a dictionary.
    """
    def __init__(self, conf_callback):
        self.conf_callback = conf_callback
        self.conf_settings = {}
        self.__is_ready = False

    def __getitem__(self, key):
        if not self.is_ready():
            self.reload()
        return super(LazyConnectionHandler, self).__getitem__(key)

    def is_ready(self):
        return self.__is_ready

    def reload(self):
        from nydus.db import create_cluster

        for conn_alias, conn_settings in self.conf_callback().iteritems():
            self[conn_alias] = create_cluster(conn_settings)
        self._is_ready = True

    def disconnect(self):
        """Disconnects all connections in cluster"""
        for connection in self.itervalues():
            connection.disconnect()

########NEW FILE########
__FILENAME__ = exceptions
"""
nydus.db.exceptions
~~~~~~~~~~~~~~~~~~~

:copyright: (c) 2011-2012 DISQUS.
:license: Apache License 2.0, see LICENSE for more details.
"""


class CommandError(Exception):
    def __init__(self, errors):
        self.errors = errors

    def __repr__(self):
        return '<%s (%d): %r>' % (type(self), len(self.errors), self.errors)

    def __str__(self):
        return '%d command(s) failed: %r' % (len(self.errors), self.errors)

########NEW FILE########
__FILENAME__ = map
"""
nydus.db.map
~~~~~~~~~~~~

:copyright: (c) 2011 DISQUS.
:license: Apache License 2.0, see LICENSE for more details.
"""

from collections import defaultdict
from nydus.utils import ThreadPool
from nydus.db.exceptions import CommandError
from nydus.db.promise import EventualCommand, change_resolution


class BaseDistributedConnection(object):
    def __init__(self, cluster, workers=None, fail_silently=False):
        self._commands = []
        self._complete = False
        self._errors = []
        self._resolved = False
        self._cluster = cluster
        self._fail_silently = fail_silently
        self._workers = min(workers or len(cluster), 16)

    def __getattr__(self, attr):
        command = EventualCommand(attr)
        self._commands.append(command)
        return command

    def _build_pending_commands(self):
        pending_commands = defaultdict(list)

        # build up a list of pending commands and their routing information
        for command in self._commands:
            if not command.was_called():
                continue

            if self._cluster.router:
                name, args, kwargs = command.get_command()
                db_nums = self._cluster.router.get_dbs(
                    cluster=self._cluster,
                    attr=name,
                    args=args,
                    kwargs=kwargs,
                )
            else:
                db_nums = self._cluster.keys()

            for db_num in db_nums:
                # add to pending commands
                pending_commands[db_num].append(command)

        return pending_commands

    def get_pool(self, commands):
        return ThreadPool(min(self._workers, len(commands)))

    def resolve(self):
        pending_commands = self._build_pending_commands()

        num_commands = sum(len(v) for v in pending_commands.itervalues())
        # Don't bother with the pooling if we only need to do one operation on a single machine
        if num_commands == 1:
            db_num, (command,) = pending_commands.items()[0]
            self._commands = [command.resolve(self._cluster[db_num])]

        elif num_commands > 1:
            results = self.execute(self._cluster, pending_commands)

            for command in self._commands:
                result = results.get(command)

                if result:
                    for value in result:
                        if isinstance(value, Exception):
                            self._errors.append((command.get_name(), value))

                    # XXX: single path routing (implicit) doesnt return a list
                    if len(result) == 1:
                        result = result[0]

                change_resolution(command, result)

        self._resolved = True

        if not self._fail_silently and self._errors:
            raise CommandError(self._errors)

    def execute(self, cluster, commands):
        """
        Execute the given commands on the cluster.

        The result should be a dictionary mapping the original command to the
        result value.
        """
        raise NotImplementedError

    def get_results(self):
        """
        Returns a list of results (once commands have been resolved).
        """
        assert self._resolved, 'you must execute the commands before fetching results'

        return self._commands

    def get_errors(self):
        """
        Returns a list of errors (once commands have been resolved).
        """
        assert self._resolved, 'you must execute the commands before fetching results'

        return self._errors


class DistributedConnection(BaseDistributedConnection):
    """
    Runs all commands using a simple thread pool, queueing up each command for each database
    it needs to run on.
    """
    def execute(self, cluster, commands):
        # Create the threadpool and pipe jobs into it
        pool = self.get_pool(commands)

        # execute our pending commands either in the pool, or using a pipeline
        for db_num, command_list in commands.iteritems():
            for command in command_list:
                # XXX: its important that we clone the command here so we dont override anything
                # in the EventualCommand proxy (it can only resolve once)
                pool.add(command, command.clone().resolve, [cluster[db_num]])

        return dict(pool.join())


class PipelinedDistributedConnection(BaseDistributedConnection):
    """
    Runs all commands using pipelines, which will execute a single pipe.execute() call
    within a thread pool.
    """
    def execute(self, cluster, commands):
        # db_num: pipeline object
        pipes = {}

        # Create the threadpool and pipe jobs into it
        pool = self.get_pool(commands)

        # execute our pending commands either in the pool, or using a pipeline
        for db_num, command_list in commands.iteritems():
            pipes[db_num] = cluster[db_num].get_pipeline()
            for command in command_list:
                # add to pipeline
                pipes[db_num].add(command.clone())

        # We need to finalize our commands with a single execute in pipelines
        for db_num, pipe in pipes.iteritems():
            pool.add(db_num, pipe.execute, (), {})

        # Consolidate commands with their appropriate results
        db_result_map = pool.join()

        # Results get grouped by their command signature, so we have to separate the logic
        results = defaultdict(list)

        for db_num, db_results in db_result_map.iteritems():
            # Pipelines always execute on a single database
            assert len(db_results) == 1
            db_results = db_results[0]

            # if pipe.execute (within nydus) fails, this will be an exception object
            if isinstance(db_results, Exception):
                for command in commands[db_num]:
                    results[command].append(db_results)
                continue

            for command, result in db_results.iteritems():
                results[command].append(result)

        return results


class DistributedContextManager(object):
    def __init__(self, cluster, workers=None, **kwargs):
        if self.can_pipeline(cluster):
            cls = PipelinedDistributedConnection
        else:
            cls = DistributedConnection
        self.connection = cls(cluster, workers, **kwargs)

    def __enter__(self):
        return self.connection

    def __exit__(self, exc_type, exc_value, tb):
        # we need to break up each command and route it
        self.connection.resolve()

    def can_pipeline(self, cluster):
        return all(cluster[n].supports_pipelines for n in cluster)

########NEW FILE########
__FILENAME__ = promise
"""
nydus.db.promise
~~~~~~~~~~~~~~~~

:copyright: (c) 2011 DISQUS.
:license: Apache License 2.0, see LICENSE for more details.
"""

from nydus.db.exceptions import CommandError
from functools import wraps


def promise_method(func):
    """
    A decorator which ensures that once a method has been marked as resolved
    (via Class.__resolved)) will then propagate the attribute (function) call
    upstream.
    """
    name = func.__name__

    @wraps(func)
    def wrapped(self, *args, **kwargs):
        cls_name = type(self).__name__
        if getattr(self, '_%s__resolved' % (cls_name,)):
            return getattr(getattr(self, '_%s__wrapped' % (cls_name,)), name)(*args, **kwargs)
        return func(self, *args, **kwargs)
    return wrapped


def change_resolution(command, value):
    """
    Public API to change the resolution of an already resolved EventualCommand result value.
    """
    command._EventualCommand__wrapped = value
    command._EventualCommand__resolved = True


class EventualCommand(object):
    # introspection support:
    __members__ = property(lambda self: self.__dir__())

    def __init__(self, attr, args=None, kwargs=None):
        self.__attr = attr
        self.__called = False
        self.__wrapped = None
        self.__resolved = False
        self.__args = args or []
        self.__kwargs = kwargs or {}
        self.__ident = ':'.join(map(lambda x: str(hash(str(x))), [self.__attr, self.__args, self.__kwargs]))

    def __call__(self, *args, **kwargs):
        self.__called = True
        self.__args = args
        self.__kwargs = kwargs
        self.__ident = ':'.join(map(lambda x: str(hash(str(x))), [self.__attr, self.__args, self.__kwargs]))
        return self

    def __hash__(self):
        # We return our ident
        return hash(self.__ident)

    def __repr__(self):
        if self.__resolved:
            return repr(self.__wrapped)
        return u'<EventualCommand: %s args=%s kwargs=%s>' % (self.__attr, self.__args, self.__kwargs)

    def __str__(self):
        if self.__resolved:
            return str(self.__wrapped)
        return repr(self)

    def __unicode__(self):
        if self.__resolved:
            return unicode(self.__wrapped)
        return unicode(repr(self))

    def __getattr__(self, name):
        return getattr(self.__wrapped, name)

    def __setattr__(self, name, value):
        if name.startswith('_%s' % (type(self).__name__,)):
            return object.__setattr__(self, name, value)
        return setattr(self.__wrapped, name, value)

    def __delattr__(self, name):
        if name.startswith('_%s' % (type(self).__name__,)):
            raise TypeError("can't delete %s." % name)
        delattr(self.__wrapped, name)

    def __deepcopy__(self, memo):
        from copy import deepcopy
        return deepcopy(self.__wrapped, memo)

    # Need to pretend to be the wrapped class, for the sake of objects that care
    # about this (especially in equality tests)
    def __get_class(self):
        return self.__wrapped.__class__
    __class__ = property(__get_class)

    def __dict__(self):
        try:
            return vars(self.__wrapped)
        except RuntimeError:
            return AttributeError('__dict__')
    __dict__ = property(__dict__)

    def __setitem__(self, key, value):
        self.__wrapped[key] = value

    def __delitem__(self, key):
        del self.__wrapped[key]

    def __setslice__(self, i, j, seq):
        self.__wrapped[i:j] = seq

    def __delslice__(self, i, j):
        del self.__wrapped[i:j]

    def __instancecheck__(self, cls):
        if self._wrapped is None:
            return False
        return isinstance(self._wrapped, cls)

    __lt__ = lambda x, o: x.__wrapped < o
    __le__ = lambda x, o: x.__wrapped <= o
    __eq__ = lambda x, o: x.__wrapped == o
    __ne__ = lambda x, o: x.__wrapped != o
    __gt__ = lambda x, o: x.__wrapped > o
    __ge__ = lambda x, o: x.__wrapped >= o
    __cmp__ = lambda x, o: cmp(x.__wrapped, o)
    # attributes are currently not callable
    # __call__ = lambda x, *a, **kw: x.__wrapped(*a, **kw)
    __nonzero__ = lambda x: bool(x.__wrapped)
    __len__ = lambda x: len(x.__wrapped)
    __getitem__ = lambda x, i: x.__wrapped[i]
    __iter__ = lambda x: iter(x.__wrapped)
    __contains__ = lambda x, i: i in x.__wrapped
    __getslice__ = lambda x, i, j: x.__wrapped[i:j]
    __add__ = lambda x, o: x.__wrapped + o
    __sub__ = lambda x, o: x.__wrapped - o
    __mul__ = lambda x, o: x.__wrapped * o
    __floordiv__ = lambda x, o: x.__wrapped // o
    __mod__ = lambda x, o: x.__wrapped % o
    __divmod__ = lambda x, o: x.__wrapped.__divmod__(o)
    __pow__ = lambda x, o: x.__wrapped ** o
    __lshift__ = lambda x, o: x.__wrapped << o
    __rshift__ = lambda x, o: x.__wrapped >> o
    __and__ = lambda x, o: x.__wrapped & o
    __xor__ = lambda x, o: x.__wrapped ^ o
    __or__ = lambda x, o: x.__wrapped | o
    __div__ = lambda x, o: x.__wrapped.__div__(o)
    __truediv__ = lambda x, o: x.__wrapped.__truediv__(o)
    __neg__ = lambda x: -(x.__wrapped)
    __pos__ = lambda x: +(x.__wrapped)
    __abs__ = lambda x: abs(x.__wrapped)
    __invert__ = lambda x: ~(x.__wrapped)
    __complex__ = lambda x: complex(x.__wrapped)
    __int__ = lambda x: int(x.__wrapped)
    __long__ = lambda x: long(x.__wrapped)
    __float__ = lambda x: float(x.__wrapped)
    __oct__ = lambda x: oct(x.__wrapped)
    __hex__ = lambda x: hex(x.__wrapped)
    __index__ = lambda x: x.__wrapped.__index__()
    __coerce__ = lambda x, o: x.__coerce__(x, o)
    __enter__ = lambda x: x.__enter__()
    __exit__ = lambda x, *a, **kw: x.__exit__(*a, **kw)

    @property
    def is_error(self):
        return isinstance(self.__wrapped, CommandError)

    @promise_method
    def was_called(self):
        return self.__called

    @promise_method
    def resolve(self, conn):
        value = getattr(conn, self.__attr)(*self.__args, **self.__kwargs)
        return self.resolve_as(value)

    @promise_method
    def resolve_as(self, value):
        self.__wrapped = value
        self.__resolved = True
        return value

    @promise_method
    def get_command(self):
        return (self.__attr, self.__args, self.__kwargs)

    @promise_method
    def get_name(self):
        return self.__attr

    @promise_method
    def get_args(self):
        return self.__args

    @promise_method
    def get_kwargs(self):
        return self.__kwargs

    @promise_method
    def set_args(self, args):
        self.__args = args

    @promise_method
    def set_kwargs(self, kwargs):
        self.__kwargs = kwargs

    @promise_method
    def clone(self):
        return EventualCommand(self.__attr, self.__args, self.__kwargs)

########NEW FILE########
__FILENAME__ = base
"""
nydus.db.base
~~~~~~~~~~~~~

:copyright: (c) 2011-2012 DISQUS.
:license: Apache License 2.0, see LICENSE for more details.
"""

__all__ = ('BaseRouter', 'RoundRobinRouter', 'routing_params')

import time

from functools import wraps
from itertools import cycle


def routing_params(func):
    @wraps(func)
    def wrapped(*args, **kwargs):
        if kwargs.get('kwargs') is None:
            kwargs['kwargs'] = {}

        if kwargs.get('args') is None:
            kwargs['args'] = ()

        return func(*args, **kwargs)
    wrapped.__wraps__ = getattr(func, '__wraps__', func)
    return wrapped


class BaseRouter(object):
    """
    Handles routing requests to a specific connection in a single cluster.

    For the most part, all public functions will receive arguments as ``key=value``
    pairs and should expect as much. Functions which receive ``args`` and ``kwargs``
    from the calling function will receive default values for those, and need not
    worry about handling missing arguments.
    """
    retryable = False

    class UnableToSetupRouter(Exception):
        pass

    def __init__(self, cluster=None, *args, **kwargs):
        self._ready = False
        self.cluster = cluster

    @routing_params
    def get_dbs(self, attr, args, kwargs, **fkwargs):
        """
        Returns a list of db keys to route the given call to.

        :param attr: Name of attribute being called on the connection.
        :param args: List of arguments being passed to ``attr``.
        :param kwargs: Dictionary of keyword arguments being passed to ``attr``.

        >>> redis = Cluster(router=BaseRouter)
        >>> router = redis.router
        >>> router.get_dbs('incr', args=('key name', 1))
        [0,1,2]

        """
        if not self._ready:
            if not self.setup_router(args=args, kwargs=kwargs, **fkwargs):
                raise self.UnableToSetupRouter()

        retval = self._pre_routing(attr=attr, args=args, kwargs=kwargs, **fkwargs)
        if retval is not None:
            args, kwargs = retval

        if not (args or kwargs):
            return self.cluster.hosts.keys()

        try:
            db_nums = self._route(attr=attr, args=args, kwargs=kwargs, **fkwargs)
        except Exception as e:
            self._handle_exception(e)
            db_nums = []

        return self._post_routing(attr=attr, db_nums=db_nums, args=args, kwargs=kwargs, **fkwargs)

    # Backwards compatibilty
    get_db = get_dbs

    @routing_params
    def setup_router(self, args, kwargs, **fkwargs):
        """
        Call method to perform any setup
        """
        self._ready = self._setup_router(args=args, kwargs=kwargs, **fkwargs)

        return self._ready

    @routing_params
    def _setup_router(self, args, kwargs, **fkwargs):
        """
        Perform any initialization for the router
        Returns False if setup could not be completed
        """
        return True

    @routing_params
    def _pre_routing(self, attr, args, kwargs, **fkwargs):
        """
        Perform any prerouting with this method and return the key
        """
        return args, kwargs

    @routing_params
    def _route(self, attr, args, kwargs, **fkwargs):
        """
        Perform routing and return db_nums
        """
        return self.cluster.hosts.keys()

    @routing_params
    def _post_routing(self, attr, db_nums, args, kwargs, **fkwargs):
        """
        Perform any postrouting actions and return db_nums
        """
        return db_nums

    def _handle_exception(self, e):
        """
        Handle/transform exceptions and return it
        """
        raise e


class RoundRobinRouter(BaseRouter):
    """
    Basic retry router that performs round robin
    """

    # Raised if all hosts in the hash have been marked as down
    class HostListExhausted(Exception):
        pass

    class InvalidDBNum(Exception):
        pass

    # If this router can be retried on if a particular db index it gave out did
    # not work
    retryable = True

    # How many requests to serve in a situation when a host is down before
    # the down hosts are assesed for readmittance back into the pool of serving
    # requests.
    #
    # If the attempt_reconnect_threshold is hit, it does not guarantee that the
    # down hosts will be put back - only that the router will CHECK to see if
    # the hosts CAN be put back.  The elegibility of a host being put back is
    # handlede in the check_down_connections method, which by default will
    # readmit a host if it was marked down more than retry_timeout seconds ago.
    attempt_reconnect_threshold = 100000

    # Number of seconds a host must be marked down before it is elligable to be
    # put back in the pool and retried.
    retry_timeout = 30

    def __init__(self, *args, **kwargs):
        self._get_db_attempts = 0
        self._down_connections = {}

        super(RoundRobinRouter, self).__init__(*args, **kwargs)

    @classmethod
    def ensure_db_num(cls, db_num):
        try:
            return int(db_num)
        except ValueError:
            raise cls.InvalidDBNum()

    def check_down_connections(self):
        """
        Iterates through all connections which were previously listed as unavailable
        and marks any that have expired their retry_timeout as being up.
        """
        now = time.time()

        for db_num, marked_down_at in self._down_connections.items():
            if marked_down_at + self.retry_timeout <= now:
                self.mark_connection_up(db_num)

    def flush_down_connections(self):
        """
        Marks all connections which were previously listed as unavailable as being up.
        """
        self._get_db_attempts = 0
        for db_num in self._down_connections.keys():
            self.mark_connection_up(db_num)

    def mark_connection_down(self, db_num):
        db_num = self.ensure_db_num(db_num)
        self._down_connections[db_num] = time.time()

    def mark_connection_up(self, db_num):
        db_num = self.ensure_db_num(db_num)
        self._down_connections.pop(db_num, None)

    @routing_params
    def _setup_router(self, args, kwargs, **fkwargs):
        self._hosts_cycler = cycle(self.cluster.hosts.keys())

        return True

    @routing_params
    def _pre_routing(self, attr, args, kwargs, retry_for=None, **fkwargs):
        self._get_db_attempts += 1

        if self._get_db_attempts > self.attempt_reconnect_threshold:
            self.check_down_connections()

        if retry_for is not None:
            self.mark_connection_down(retry_for)

        return args, kwargs

    @routing_params
    def _route(self, attr, args, kwargs, **fkwargs):
        now = time.time()

        for i in xrange(len(self.cluster)):
            db_num = self._hosts_cycler.next()

            marked_down_at = self._down_connections.get(db_num, False)

            if not marked_down_at or (marked_down_at + self.retry_timeout <= now):
                return [db_num]
        else:
            raise self.HostListExhausted()

    @routing_params
    def _post_routing(self, attr, db_nums, args, kwargs, **fkwargs):
        if db_nums and db_nums[0] in self._down_connections:
            self.mark_connection_up(db_nums[0])

        return db_nums

########NEW FILE########
__FILENAME__ = keyvalue
"""
nydus.db.routers.keyvalue
~~~~~~~~~~~~~~~~~~~~~~~~~

:copyright: (c) 2011-2012 DISQUS.
:license: Apache License 2.0, see LICENSE for more details.
"""

from binascii import crc32

from nydus.contrib.ketama import Ketama
from nydus.db.routers import BaseRouter, RoundRobinRouter, routing_params

__all__ = ('ConsistentHashingRouter', 'PartitionRouter')


def get_key(args, kwargs):
    if 'key' in kwargs:
        return kwargs['key']
    elif args:
        return args[0]
    return None


class ConsistentHashingRouter(RoundRobinRouter):
    """
    Router that returns host number based on a consistent hashing algorithm.
    The consistent hashing algorithm only works if a key argument is provided.

    If a key is not provided, then all hosts are returned.

    The first argument is assumed to be the ``key`` for routing. Keyword arguments
    are not supported.
    """

    def __init__(self, *args, **kwargs):
        self._db_num_id_map = {}
        super(ConsistentHashingRouter, self).__init__(*args, **kwargs)

    def mark_connection_down(self, db_num):
        db_num = self.ensure_db_num(db_num)
        self._hash.remove_node(self._db_num_id_map[db_num])

        super(ConsistentHashingRouter, self).mark_connection_down(db_num)

    def mark_connection_up(self, db_num):
        db_num = self.ensure_db_num(db_num)
        self._hash.add_node(self._db_num_id_map[db_num])

        super(ConsistentHashingRouter, self).mark_connection_up(db_num)

    @routing_params
    def _setup_router(self, args, kwargs, **fkwargs):
        self._db_num_id_map = dict([(db_num, host.identifier) for db_num, host in self.cluster.hosts.iteritems()])
        self._hash = Ketama(self._db_num_id_map.values())

        return True

    @routing_params
    def _pre_routing(self, *args, **kwargs):
        self.check_down_connections()

        return super(ConsistentHashingRouter, self)._pre_routing(*args, **kwargs)

    @routing_params
    def _route(self, attr, args, kwargs, **fkwargs):
        """
        The first argument is assumed to be the ``key`` for routing.
        """

        key = get_key(args, kwargs)

        found = self._hash.get_node(key)

        if not found and len(self._down_connections) > 0:
            raise self.HostListExhausted()

        return [i for i, h in self.cluster.hosts.iteritems()
                if h.identifier == found]


class PartitionRouter(BaseRouter):
    @routing_params
    def _route(self, attr, args, kwargs, **fkwargs):
        """
        The first argument is assumed to be the ``key`` for routing.
        """
        key = get_key(args, kwargs)

        return [crc32(str(key)) % len(self.cluster)]

########NEW FILE########
__FILENAME__ = redis
"""
nydus.db.routers.redis
~~~~~~~~~~~~~~~~~~~~~~

:copyright: (c) 2011-2012 DISQUS.
:license: Apache License 2.0, see LICENSE for more details.
"""

from nydus.db.routers import RoundRobinRouter
from nydus.db.routers.keyvalue import ConsistentHashingRouter, PartitionRouter

__all__ = ('ConsistentHashingRouter', 'PartitionRouter', 'RoundRobinRouter')

########NEW FILE########
__FILENAME__ = testutils
import unittest2

NOTSET = object()


class BaseTest(unittest2.TestCase):
    def setUp(self):
        pass


class fixture(object):
    """
    >>> class Foo(object):
    >>>     @fixture
    >>>     def foo(self):
    >>>         # calculate something important here
    >>>         return 42
    """
    def __init__(self, func):
        self.__name__ = func.__name__
        self.__module__ = func.__module__
        self.__doc__ = func.__doc__
        self.func = func

    def __get__(self, obj, type=None):
        if obj is None:
            return self
        value = obj.__dict__.get(self.__name__, NOTSET)
        if value is NOTSET:
            value = self.func(obj)
            obj.__dict__[self.__name__] = value
        return value

########NEW FILE########
__FILENAME__ = utils
from collections import defaultdict
from Queue import Queue, Empty
from threading import Thread


# import_string comes form Werkzeug
# http://werkzeug.pocoo.org
def import_string(import_name, silent=False):
    """Imports an object based on a string. If *silent* is True the return
    value will be None if the import fails.

    Simplified version of the function with same name from `Werkzeug`_.

    :param import_name:
        The dotted name for the object to import.
    :param silent:
        If True, import errors are ignored and None is returned instead.
    :returns:
        The imported object.
    """
    import_name = str(import_name)
    try:
        if '.' in import_name:
            module, obj = import_name.rsplit('.', 1)
            return getattr(__import__(module, None, None, [obj]), obj)
        else:
            return __import__(import_name)
    except (ImportError, AttributeError):
        if not silent:
            raise


def apply_defaults(host, defaults):
    for key, value in defaults.iteritems():
        if key not in host:
            host[key] = value
    return host


def peek(value):
    generator = iter(value)
    prev = generator.next()
    for item in generator:
        yield prev, item
        prev = item
    yield prev, None


class Worker(Thread):
    def __init__(self, queue):
        Thread.__init__(self)
        self.queue = queue
        self.results = defaultdict(list)

    def run(self):
        while True:
            try:
                ident, func, args, kwargs = self.queue.get_nowait()
            except Empty:
                break

            try:
                result = func(*args, **kwargs)
                self.results[ident].append(result)
            except Exception as e:
                self.results[ident].append(e)
            finally:
                self.queue.task_done()

        return self.results


class ThreadPool(object):
    def __init__(self, workers=10):
        self.queue = Queue()
        self.workers = []
        self.tasks = []
        for worker in xrange(workers):
            self.workers.append(Worker(self.queue))

    def add(self, ident, func, args=None, kwargs=None):
        if args is None:
            args = ()
        if kwargs is None:
            kwargs = {}
        task = (ident, func, args, kwargs)
        self.tasks.append(ident)
        self.queue.put_nowait(task)

    def join(self):
        for worker in self.workers:
            worker.start()

        results = defaultdict(list)
        for worker in self.workers:
            worker.join()
            for k, v in worker.results.iteritems():
                results[k].extend(v)
        return results

########NEW FILE########
__FILENAME__ = tests
from __future__ import absolute_import

from nydus.db import create_cluster
from nydus.db.base import BaseCluster
from nydus.db.backends.memcache import Memcache, regroup_commands, grouped_args_for_command, \
  can_group_commands
from nydus.db.promise import EventualCommand
from nydus.testutils import BaseTest, fixture

import mock
import pylibmc


class CanGroupCommandsTest(BaseTest):
    def test_groupable_set_commands(self):
        command = EventualCommand('set', ['foo', 1])
        other = EventualCommand('set', ['bar', 2])
        self.assertEquals(can_group_commands(command, other), True)

    def test_ungroupable_set_commands(self):
        command = EventualCommand('set', ['foo', 1], {'timeout': 1})
        other = EventualCommand('set', ['bar', 2], {'timeout': 2})
        self.assertEquals(can_group_commands(command, other), False)

    def test_groupable_get_commands(self):
        command = EventualCommand('get', ['foo'])
        other = EventualCommand('get', ['bar'])
        self.assertEquals(can_group_commands(command, other), True)

    def test_ungroupable_get_commands(self):
        command = EventualCommand('get', ['foo'], {'timeout': 1})
        other = EventualCommand('get', ['bar'], {'timeout': 2})
        self.assertEquals(can_group_commands(command, other), False)

    def test_groupable_delete_commands(self):
        command = EventualCommand('delete', ['foo'])
        other = EventualCommand('delete', ['bar'])
        self.assertEquals(can_group_commands(command, other), True)

    def test_ungroupable_delete_commands(self):
        command = EventualCommand('delete', ['foo'], {'timeout': 1})
        other = EventualCommand('delete', ['bar'], {'timeout': 2})
        self.assertEquals(can_group_commands(command, other), False)


class GroupedArgsForCommandTest(BaseTest):
    def test_set_excludes_first_two_args(self):
        command = EventualCommand('set', ['foo', 1, 'biz'])
        result = grouped_args_for_command(command)
        self.assertEquals(result, ['biz'])

    def test_get_excludes_first_arg(self):
        command = EventualCommand('get', ['foo', 1])
        result = grouped_args_for_command(command)
        self.assertEquals(result, [1])

    def test_delete_excludes_first_arg(self):
        command = EventualCommand('delete', ['foo', 1])
        result = grouped_args_for_command(command)
        self.assertEquals(result, [1])


class RegroupCommandsTest(BaseTest):
    def get_grouped_results(self, commands, num_expected):
        grouped = regroup_commands(commands)
        self.assertEquals(len(grouped), num_expected, grouped)
        return grouped

    def test_set_basic(self):
        commands = [
            EventualCommand('set', ['foo', 1], {'timeout': 1}),
            EventualCommand('set', ['bar', 2], {'timeout': 1}),
            EventualCommand('set', ['baz', 3], {'timeout': 2}),
        ]

        items = self.get_grouped_results(commands, 2)

        new_command, grouped_commands = items[0]
        self.assertEquals(len(grouped_commands), 2)
        self.assertEquals(grouped_commands, commands[0:2])
        self.assertEquals(new_command.get_name(), 'set_multi')
        self.assertEquals(new_command.get_args(), ({
            'foo': 1,
            'bar': 2,
        },))
        self.assertEquals(new_command.get_kwargs(), {
            'timeout': 1,
        })

        new_command, grouped_commands = items[1]
        self.assertEquals(len(grouped_commands), 1)
        self.assertEquals(grouped_commands, commands[2:3])
        self.assertEquals(new_command.get_name(), 'set')
        self.assertEquals(new_command.get_args(), ['baz', 3])
        self.assertEquals(new_command.get_kwargs(), {
            'timeout': 2,
        })

    def test_get_basic(self):
        commands = [
            EventualCommand('get', ['foo'], {'key_prefix': 1}),
            EventualCommand('get', ['bar'], {'key_prefix': 1}),
            EventualCommand('get', ['baz'], {'key_prefix': 2}),
        ]
        items = self.get_grouped_results(commands, 2)

        new_command, grouped_commands = items[0]
        self.assertEquals(len(grouped_commands), 2)
        self.assertEquals(grouped_commands, commands[0:2])
        self.assertEquals(new_command.get_name(), 'get_multi')
        self.assertEquals(new_command.get_args(), (['foo', 'bar'],))
        self.assertEquals(new_command.get_kwargs(), {
            'key_prefix': 1,
        })

        new_command, grouped_commands = items[1]
        self.assertEquals(len(grouped_commands), 1)
        self.assertEquals(grouped_commands, commands[2:3])
        self.assertEquals(new_command.get_name(), 'get')
        self.assertEquals(new_command.get_args(), ['baz'])
        self.assertEquals(new_command.get_kwargs(), {
            'key_prefix': 2,
        })

    def test_delete_basic(self):
        commands = [
            EventualCommand('delete', ['foo'], {'key_prefix': 1}),
            EventualCommand('delete', ['bar'], {'key_prefix': 1}),
            EventualCommand('delete', ['baz'], {'key_prefix': 2}),
        ]
        items = self.get_grouped_results(commands, 2)

        new_command, grouped_commands = items[0]
        self.assertEquals(len(grouped_commands), 2)
        self.assertEquals(grouped_commands, commands[0:2])
        self.assertEquals(new_command.get_name(), 'delete_multi')
        self.assertEquals(new_command.get_args(), (['foo', 'bar'],))
        self.assertEquals(new_command.get_kwargs(), {
            'key_prefix': 1,
        })

        new_command, grouped_commands = items[1]
        self.assertEquals(len(grouped_commands), 1)
        self.assertEquals(grouped_commands, commands[2:3])
        self.assertEquals(new_command.get_name(), 'delete')
        self.assertEquals(new_command.get_args(), ['baz'])
        self.assertEquals(new_command.get_kwargs(), {
            'key_prefix': 2,
        })

    def test_mixed_commands(self):
        commands = [
            EventualCommand('get', ['foo']),
            EventualCommand('set', ['bar', 1], {'timeout': 1}),
            EventualCommand('set', ['baz', 2], {'timeout': 1}),
            EventualCommand('get', ['bar']),
        ]

        items = self.get_grouped_results(commands, 3)

        new_command, grouped_commands = items[0]
        self.assertEquals(len(grouped_commands), 1)
        self.assertEquals(grouped_commands, commands[2:3])
        self.assertEquals(new_command.get_name(), 'get')
        self.assertEquals(new_command.get_args(), ['foo'])
        self.assertEquals(new_command.get_kwargs(), {})

        new_command, grouped_commands = items[1]
        self.assertEquals(len(grouped_commands), 2)
        self.assertEquals(grouped_commands, commands[0:2])
        self.assertEquals(new_command.get_name(), 'set_multi')
        self.assertEquals(new_command.get_args(), ({
            'bar': 1,
            'baz': 2,
        },))
        self.assertEquals(new_command.get_kwargs(), {
            'timeout': 1,
        })

        new_command, grouped_commands = items[2]
        self.assertEquals(len(grouped_commands), 1)
        self.assertEquals(grouped_commands, commands[2:3])
        self.assertEquals(new_command.get_name(), 'get')
        self.assertEquals(new_command.get_args(), ['bar'])
        self.assertEquals(new_command.get_kwargs(), {})


class MemcacheTest(BaseTest):

    @fixture
    def memcache(self):
        return Memcache(num=0)

    def test_provides_retryable_exceptions(self):
        self.assertEquals(Memcache.retryable_exceptions, frozenset([pylibmc.Error]))

    def test_provides_identifier(self):
        self.assertEquals(self.memcache.identifier, str(self.memcache.identifier))

    @mock.patch('pylibmc.Client')
    def test_client_instantiates_with_kwargs(self, Client):
        client = Memcache(num=0)
        client.connect()

        self.assertEquals(Client.call_count, 1)
        Client.assert_any_call(['localhost:11211'], binary=True, behaviors=None)

    @mock.patch('pylibmc.Client.get')
    def test_with_cluster(self, get):
        p = BaseCluster(
            backend=Memcache,
            hosts={0: {}},
        )
        result = p.get('MemcacheTest_with_cluster')
        get.assert_called_once_with('MemcacheTest_with_cluster')
        self.assertEquals(result, get.return_value)

    @mock.patch('pylibmc.Client')
    def test_pipeline_behavior(self, Client):
        cluster = create_cluster({
            'engine': 'nydus.db.backends.memcache.Memcache',
            'hosts': {
                0: {'binary': True},
            }
        })

        with cluster.map() as conn:
            conn.set('a', 1)
            conn.set('b', 2)
            conn.set('c', 3)
            conn.get('a')
            conn.get('b')
            conn.get('c')

        Client.return_value.set_multi.assert_any_call({'a': 1, 'b': 2, 'c': 3})
        Client.return_value.get_multi.assert_any_call(['a', 'b', 'c'])

    def test_pipeline_integration(self):
        cluster = create_cluster({
            'engine': 'nydus.db.backends.memcache.Memcache',
            'hosts': {
                0: {'binary': True},
            }
        })

        with cluster.map() as conn:
            conn.set('a', 1)
            conn.set('b', 2)
            conn.set('c', 3)
            conn.get('a')
            conn.get('b')
            conn.get('c')

        results = conn.get_results()
        self.assertEquals(len(results), 6, results)
        self.assertEquals(results[0:3], [None, None, None])
        self.assertEquals(results[3:6], [1, 2, 3])

########NEW FILE########
__FILENAME__ = tests
from __future__ import absolute_import

from nydus.db import create_cluster
from nydus.db.backends.pycassa import Pycassa, PycassaCluster
from nydus.testutils import BaseTest, fixture
import mock


class PycassCreateClusterTest(BaseTest):
    @fixture
    def cluster(self):
        return create_cluster({
            'backend': 'nydus.db.backends.pycassa.Pycassa',
            'hosts': ['localhost'],
            'keyspace': 'test',
        })

    def test_is_pycassa_cluster(self):
        self.assertEquals(type(self.cluster), PycassaCluster)


class PycassClusterTest(BaseTest):
    @fixture
    def cluster(self):
        return PycassaCluster(
            hosts=['localhost'],
            keyspace='test',
        )

    def test_has_one_connection(self):
        self.assertEquals(len(self.cluster), 1)

    def test_backend_is_pycassa(self):
        self.assertEquals(type(self.cluster[0]), Pycassa)


class PycassaTest(BaseTest):
    @fixture
    def connection(self):
        return Pycassa(num=0, keyspace='test', hosts=['localhost'])

    @mock.patch('nydus.db.backends.pycassa.ConnectionPool')
    def test_client_instantiates_with_kwargs(self, ConnectionPool):
        client = Pycassa(
            keyspace='test', hosts=['localhost'], prefill=True,
            timeout=5, foo='bar', num=0,
        )
        client.connect()
        ConnectionPool.assert_called_once_with(
            keyspace='test', prefill=True, timeout=5,
            server_list=['localhost'], foo='bar'
        )

    @mock.patch('nydus.db.backends.pycassa.ConnectionPool')
    def test_disconnect_calls_dispose(self, ConnectionPool):
        self.connection.disconnect()
        ConnectionPool().dispose.assert_called_once_with()

########NEW FILE########
__FILENAME__ = tests
from __future__ import absolute_import

from nydus.db import create_cluster
from nydus.db.base import BaseCluster
from nydus.db.backends.redis import Redis
from nydus.db.promise import EventualCommand
from nydus.testutils import BaseTest, fixture
import mock
import redis as redis_


class RedisPipelineTest(BaseTest):
    @fixture
    def cluster(self):
        return create_cluster({
            'backend': 'nydus.db.backends.redis.Redis',
            'router': 'nydus.db.routers.keyvalue.PartitionRouter',
            'hosts': {
                0: {'db': 5},
                1: {'db': 6},
                2: {'db': 7},
                3: {'db': 8},
                4: {'db': 9},
            }
        })

    # XXX: technically we're testing the Nydus map code, and not ours
    def test_pipelined_map(self):
        chars = ('a', 'b', 'c', 'd', 'e', 'f')
        with self.cluster.map() as conn:
            [conn.set(c, i) for i, c in enumerate(chars)]
            res = [conn.get(c) for c in chars]
        self.assertEqual(range(len(chars)), [int(r) for r in res])

    def test_map_single_connection(self):
        with self.cluster.map() as conn:
            conn.set('a', '1')
        self.assertEquals(self.cluster.get('a'), '1')

    def test_no_proxy_without_call_on_map(self):
        with self.cluster.map() as conn:
            result = conn.incr

        assert type(result) is EventualCommand
        assert not result.was_called()


class RedisTest(BaseTest):

    def setUp(self):
        self.redis = Redis(num=0, db=1)
        self.redis.flushdb()

    def test_proxy(self):
        self.assertEquals(self.redis.incr('RedisTest_proxy'), 1)

    def test_with_cluster(self):
        p = BaseCluster(
            backend=Redis,
            hosts={0: {'db': 1}},
        )
        self.assertEquals(p.incr('RedisTest_with_cluster'), 1)

    def test_provides_retryable_exceptions(self):
        self.assertEquals(Redis.retryable_exceptions, frozenset([redis_.ConnectionError, redis_.InvalidResponse]))

    def test_provides_identifier(self):
        self.assertEquals(self.redis.identifier, str(self.redis.identifier))

    @mock.patch('nydus.db.backends.redis.RedisClient')
    def test_client_instantiates_with_kwargs(self, RedisClient):
        client = Redis(num=0)
        client.connect()

        self.assertEquals(RedisClient.call_count, 1)
        RedisClient.assert_any_call(host='localhost', port=6379, db=0, socket_timeout=None,
            password=None, unix_socket_path=None)

    @mock.patch('nydus.db.backends.redis.RedisClient')
    def test_map_does_pipeline(self, RedisClient):
        redis = create_cluster({
            'backend': 'nydus.db.backends.redis.Redis',
            'router': 'nydus.db.routers.keyvalue.PartitionRouter',
            'hosts': {
                0: {'db': 0},
                1: {'db': 1},
            }
        })

        with redis.map() as conn:
            conn.set('a', 0)
            conn.set('d', 1)

        # ensure this was actually called through the pipeline
        self.assertFalse(RedisClient().set.called)

        self.assertEquals(RedisClient().pipeline.call_count, 2)
        RedisClient().pipeline.assert_called_with()

        self.assertEquals(RedisClient().pipeline().set.call_count, 2)
        RedisClient().pipeline().set.assert_any_call('a', 0)
        RedisClient().pipeline().set.assert_any_call('d', 1)

        self.assertEquals(RedisClient().pipeline().execute.call_count, 2)
        RedisClient().pipeline().execute.assert_called_with()

    @mock.patch('nydus.db.backends.redis.RedisClient')
    def test_map_only_runs_on_required_nodes(self, RedisClient):
        redis = create_cluster({
            'engine': 'nydus.db.backends.redis.Redis',
            'router': 'nydus.db.routers.keyvalue.PartitionRouter',
            'hosts': {
                0: {'db': 0},
                1: {'db': 1},
            }
        })
        with redis.map() as conn:
            conn.set('a', 0)
            conn.set('b', 1)

        # ensure this was actually called through the pipeline
        self.assertFalse(RedisClient().set.called)

        self.assertEquals(RedisClient().pipeline.call_count, 1)
        RedisClient().pipeline.assert_called_with()

        self.assertEquals(RedisClient().pipeline().set.call_count, 2)
        RedisClient().pipeline().set.assert_any_call('a', 0)
        RedisClient().pipeline().set.assert_any_call('b', 1)

        self.assertEquals(RedisClient().pipeline().execute.call_count, 1)
        RedisClient().pipeline().execute.assert_called_with()

    def test_normal_exceptions_dont_break_the_cluster(self):
        redis = create_cluster({
            'engine': 'nydus.db.backends.redis.Redis',
            'router': 'nydus.db.routers.keyvalue.ConsistentHashingRouter',
            'hosts': {
                0: {'db': 0},
                1: {'db': 1},
            }
        })

        # Create a normal key
        redis.set('a', 0)

        with self.assertRaises(redis_.ResponseError):
            # We are going to preform an operation on a key that is not a set
            # This call *should* raise the actual Redis exception, and
            # not continue on to think the host is down.
            redis.scard('a')

        # This shouldn't raise a HostListExhausted exception
        redis.get('a')

########NEW FILE########
__FILENAME__ = tests
from __future__ import absolute_import

import mock
from httplib import HTTPException
from nydus.db.backends.riak import Riak
from nydus.testutils import BaseTest
from riak import RiakClient, RiakError
from socket import error as SocketError


class RiakTest(BaseTest):
    def setUp(self):
        self.expected_defaults = {
            'host': '127.0.0.1',
            'port': 8098,
            'prefix': 'riak',
            'mapred_prefix': 'mapred',
            'client_id': None,
        }

        self.modified_props = {
            'host': '127.0.0.254',
            'port': 8908,
            'prefix': 'kair',
            'mapred_prefix': 'derpam',
            'client_id': 'MjgxMDg2MzQx',
            'transport_options': {},
            'transport_class': mock.Mock,
            'solr_transport_class': mock.Mock,
        }

        self.conn = Riak(0)
        self.modified_conn = Riak(1, **self.modified_props)

    def test_init_defaults(self):
        self.assertDictContainsSubset(self.expected_defaults, self.conn.__dict__)

    def test_init_properties(self):
        self.assertDictContainsSubset(self.modified_props, self.modified_conn.__dict__)

    def test_identifier(self):
        expected_identifier = 'http://%(host)s:%(port)s/%(prefix)s' % self.conn.__dict__
        self.assertEquals(expected_identifier, self.conn.identifier)

    def test_identifier_properties(self):
        expected_identifier = 'http://%(host)s:%(port)s/%(prefix)s' % self.modified_props
        self.assertEquals(expected_identifier, self.modified_conn.identifier)

    @mock.patch('nydus.db.backends.riak.RiakClient')
    def test_connect_riakclient_options(self, _RiakClient):
        self.conn.connect()

        _RiakClient.assert_called_with(host=self.conn.host, port=self.conn.port, prefix=self.conn.prefix, \
                                        mapred_prefix=self.conn.mapred_prefix, client_id=self.conn.client_id, \
                                        transport_options=self.conn.transport_options, transport_class=self.conn.transport_class, \
                                        solr_transport_class=self.conn.solr_transport_class)

    @mock.patch('nydus.db.backends.riak.RiakClient')
    def test_connect_riakclient_modified_options(self, _RiakClient):
        self.modified_conn.connect()

        _RiakClient.assert_called_with(host=self.modified_conn.host, port=self.modified_conn.port, prefix=self.modified_conn.prefix, \
                                        mapred_prefix=self.modified_conn.mapred_prefix, client_id=self.modified_conn.client_id, \
                                        transport_options=self.modified_conn.transport_options, transport_class=self.modified_conn.transport_class, \
                                        solr_transport_class=self.modified_conn.solr_transport_class)

    def test_connect_returns_riakclient(self):
        client = self.conn.connect()

        self.assertIsInstance(client, RiakClient)

    def test_provides_retryable_exceptions(self):
        self.assertItemsEqual([RiakError, HTTPException, SocketError], self.conn.retryable_exceptions)

########NEW FILE########
__FILENAME__ = tests
from __future__ import absolute_import

import unittest2
from nydus.db.backends.thoonk import Thoonk
from nydus.db import create_cluster


class ThoonkTest(unittest2.TestCase):
    def get_cluster(self, router):
        cluster = create_cluster({
            'backend': 'nydus.db.backends.thoonk.Thoonk',
            'router': router,
            'hosts': {
                0: {'db': 5},
                1: {'db': 6},
                2: {'db': 7},
                3: {'db': 8},
                4: {'db': 9},
            }
        })
        self.flush_custer(cluster)
        return cluster

    def flush_custer(self, cluster):
        for x in range(len(cluster)):
            c = cluster.get_conn()[x]
            c.redis.flushdb()

    def setUp(self):
        self.ps = Thoonk(0, db=1)
        self.redis = self.ps.redis
        self.redis.flushdb()

    def tearDown(self):
        pass

    def test_flush_db(self):
        pubsub = self.get_cluster('nydus.db.routers.keyvalue.ConsistentHashingRouter')
        pubsub.flushdb()

    def test_job_with_ConsistentHashingRouter(self):
        pubsub = self.get_cluster('nydus.db.routers.keyvalue.ConsistentHashingRouter')
        job = pubsub.job("test1")
        jid = job.put("10")

        jid_found = False

        for ps in pubsub.get_conn():
            jps = ps.job('test1')
            if jid in jps.get_ids():
                self.assertFalse(jid_found)
                jid_found = True

        self.assertTrue(jid_found)

    def test_job_with_RoundRobinRouter(self):
        pubsub = self.get_cluster('nydus.db.routers.RoundRobinRouter')

        jobs = {}
        size = 20

        # put jobs onto the queue
        for x in xrange(0, size):
            jps = pubsub.job('testjob')
            jid = jps.put(str(x))
            if id(jps) not in jobs:
                jobs[id(jps)] = []
            jobs[id(jps)].append(jid)

        # make sure that we are reusing the job items
        self.assertEqual(len(jobs), 5)
        for k, v in jobs.iteritems():
            self.assertEqual(len(v), size / 5)

        # make sure we fishi
        for x in xrange(0, size):
            jps = pubsub.job('testjob')
            jid, job, cancel_count = jps.get()
            jps.finish(jid)

        self.assertEqual(len(jobs), 5)

        for x in range(len(pubsub)):
            ps = pubsub.get_conn('testjob')
            jps = ps.job('testjob')
            self.assertEqual(jps.get_ids(), [])

########NEW FILE########
__FILENAME__ = tests
from __future__ import absolute_import

import mock

from nydus.db import create_cluster
from nydus.db.backends.base import BaseConnection
from nydus.db.base import BaseCluster, create_connection
from nydus.db.exceptions import CommandError
from nydus.db.routers.base import BaseRouter
from nydus.db.routers.keyvalue import get_key
from nydus.db.promise import EventualCommand
from nydus.testutils import BaseTest, fixture
from nydus.utils import apply_defaults


class DummyConnection(BaseConnection):
    def __init__(self, num, resp='foo', **kwargs):
        self.resp = resp
        super(DummyConnection, self).__init__(num, **kwargs)

    def foo(self, *args, **kwargs):
        return self.resp


class DummyErroringConnection(DummyConnection):
    def foo(self, *args, **kwargs):
        if self.resp == 'error':
            raise ValueError(self.resp)
        return self.resp


class DummyRouter(BaseRouter):
    def get_dbs(self, attr, args, kwargs, **fkwargs):
        key = get_key(args, kwargs)
        if key == 'foo':
            return [1]
        return [0]


class ConnectionTest(BaseTest):
    @fixture
    def connection(self):
        return BaseConnection(0)

    @mock.patch('nydus.db.backends.base.BaseConnection.disconnect')
    def test_close_calls_disconnect(self, disconnect):
        self.connection._connection = mock.Mock()
        self.connection.close()
        disconnect.assert_called_once_with()

    @mock.patch('nydus.db.backends.base.BaseConnection.disconnect', mock.Mock(return_value=None))
    def test_close_unsets_connection(self):
        self.connection.close()
        self.assertEquals(self.connection._connection, None)

    @mock.patch('nydus.db.backends.base.BaseConnection.disconnect')
    def test_close_propagates_noops_if_not_connected(self, disconnect):
        self.connection.close()
        self.assertFalse(disconnect.called)

    @mock.patch('nydus.db.backends.base.BaseConnection.connect')
    def test_connection_forces_connect(self, connect):
        self.connection.connection
        connect.assert_called_once_with()

    @mock.patch('nydus.db.backends.base.BaseConnection.connect')
    def test_connection_doesnt_reconnect_with_existing_connection(self, connect):
        self.connection._connection = mock.Mock()
        self.connection.connection
        self.assertFalse(connect.called)

    @mock.patch('nydus.db.backends.base.BaseConnection.connect')
    def test_connection_returns_result_of_connect(self, connect):
        val = self.connection.connection
        self.assertEquals(val, connect.return_value)

    def test_attrs_proxy(self):
        conn = mock.Mock()
        self.connection._connection = conn
        val = self.connection.foo(biz='baz')
        conn.foo.assert_called_once_with(biz='baz')
        self.assertEquals(val, conn.foo.return_value)


class CreateConnectionTest(BaseTest):
    def test_does_apply_defaults(self):
        conn = mock.Mock()
        create_connection(conn, 0, {'resp': 'bar'}, {'foo': 'baz'})
        conn.assert_called_once_with(0, foo='baz', resp='bar')

    def test_handles_arg_list_with_defaults(self):
        conn = mock.Mock()
        create_connection(conn, 0, ['localhost'], {'foo': 'baz'})
        conn.assert_called_once_with(0, 'localhost', foo='baz')


class CreateClusterTest(BaseTest):
    def test_creates_cluster(self):
        c = create_cluster({
            'backend': DummyConnection,
            'router': DummyRouter,
            'hosts': {
                0: {'resp': 'bar'},
            }
        })
        self.assertEquals(len(c), 1)

    @mock.patch('nydus.db.base.create_connection')
    def test_does_create_connection_with_defaults(self, create_connection):
        create_cluster({
            'backend': DummyConnection,
            'defaults': {'foo': 'baz'},
            'hosts': {
                0: {'resp': 'bar'},
            }
        })
        create_connection.assert_called_once_with(DummyConnection, 0, {'resp': 'bar'}, {'foo': 'baz'})


class ClusterTest(BaseTest):
    def test_len_returns_num_backends(self):
        p = BaseCluster(
            backend=BaseConnection,
            hosts={0: {}},
        )
        self.assertEquals(len(p), 1)

    def test_proxy(self):
        p = BaseCluster(
            backend=DummyConnection,
            hosts={0: {'resp': 'bar'}},
        )
        self.assertEquals(p.foo(), 'bar')

    def test_disconnect(self):
        c = mock.Mock()
        p = BaseCluster(
            backend=c,
            hosts={0: {'resp': 'bar'}},
        )
        p.disconnect()
        c.disconnect.assert_called_once()

    def test_with_split_router(self):
        p = BaseCluster(
            router=DummyRouter,
            backend=DummyConnection,
            hosts={
                0: {'resp': 'foo'},
                1: {'resp': 'bar'},
            },
        )
        self.assertEquals(p.foo(), 'foo')
        self.assertEquals(p.foo('foo'), 'bar')

    def test_default_routing_with_multiple_hosts(self):
        p = BaseCluster(
            backend=DummyConnection,
            hosts={
                0: {'resp': 'foo'},
                1: {'resp': 'bar'},
            },
        )
        self.assertEquals(p.foo(), ['foo', 'bar'])
        self.assertEquals(p.foo('foo'), ['foo', 'bar'])

    def test_get_conn_with_split_router(self):
        # test dummy router
        p = BaseCluster(
            backend=DummyConnection,
            hosts={
                0: {'resp': 'foo'},
                1: {'resp': 'bar'},
            },
            router=DummyRouter,
        )
        self.assertEquals(p.get_conn().num, 0)
        self.assertEquals(p.get_conn('foo').num, 1)

    def test_get_conn_default_routing_with_multiple_hosts(self):
        # test default routing behavior
        p = BaseCluster(
            backend=DummyConnection,
            hosts={
                0: {'resp': 'foo'},
                1: {'resp': 'bar'},
            },
        )
        self.assertEquals(map(lambda x: x.num, p.get_conn()), [0, 1])
        self.assertEquals(map(lambda x: x.num, p.get_conn('foo')), [0, 1])


class MapTest(BaseTest):
    @fixture
    def cluster(self):
        return BaseCluster(
            backend=DummyConnection,
            hosts={
                0: {'resp': 'foo'},
                1: {'resp': 'bar'},
            },
        )

    def test_handles_single_routing_results(self):
        self.cluster.install_router(DummyRouter)

        with self.cluster.map() as conn:
            foo = conn.foo()
            bar = conn.foo('foo')
            self.assertEquals(foo, None)
            self.assertEquals(bar, None)

        self.assertEquals(bar, 'bar')
        self.assertEquals(foo, 'foo')

    def test_handles_groups_of_results(self):
        with self.cluster.map() as conn:
            foo = conn.foo()
            bar = conn.foo('foo')
            self.assertEquals(foo, None)
            self.assertEquals(bar, None)

        self.assertEquals(foo, ['foo', 'bar'])
        self.assertEquals(bar, ['foo', 'bar'])


class MapWithFailuresTest(BaseTest):
    @fixture
    def cluster(self):
        return BaseCluster(
            backend=DummyErroringConnection,
            hosts={
                0: {'resp': 'foo'},
                1: {'resp': 'error'},
            },
            router=DummyRouter,
        )

    def test_propagates_errors(self):
        with self.assertRaises(CommandError):
            with self.cluster.map() as conn:
                foo = conn.foo()
                bar = conn.foo('foo')
                self.assertEquals(foo, None)
                self.assertEquals(bar, None)

    def test_fail_silenlty(self):
        with self.cluster.map(fail_silently=True) as conn:
            foo = conn.foo()
            bar = conn.foo('foo')
            self.assertEquals(foo, None)
            self.assertEquals(bar, None)

        self.assertEquals(len(conn.get_errors()), 1, conn.get_errors())
        self.assertEquals(type(conn.get_errors()[0][1]), ValueError)

        self.assertEquals(foo, 'foo')
        self.assertNotEquals(foo, 'bar')


class FlakeyConnection(DummyConnection):

    retryable_exceptions = [Exception]

    def foo(self, *args, **kwargs):
        if hasattr(self, 'already_failed'):
            super(FlakeyConnection, self).foo()
        else:
            self.already_failed = True
            raise Exception('boom!')


class RetryableRouter(DummyRouter):
    retryable = True

    def __init__(self, *args, **kwargs):
        self.kwargs_seen = []
        self.key_args_seen = []
        super(RetryableRouter, self).__init__(*args, **kwargs)

    def get_dbs(self, attr, args, kwargs, **fkwargs):
        key = get_key(args, kwargs)
        self.kwargs_seen.append(fkwargs)
        self.key_args_seen.append(key)
        return [0]


class ScumbagConnection(DummyConnection):

    retryable_exceptions = [Exception]

    def foo(self):
        raise Exception("Says it's a connection / Never actually connects.")


class RetryClusterTest(BaseTest):

    def build_cluster(self, connection=FlakeyConnection, router=RetryableRouter):
        return create_cluster({
            'backend': connection,
            'router': router,
            'hosts': {
                0: {'resp': 'bar'},
            }
        })

    def test_returns_correctly(self):
        cluster = self.build_cluster(connection=DummyConnection)
        self.assertEquals(cluster.foo(), 'bar')

    def test_retry_router_when_receives_error(self):
        cluster = self.build_cluster()

        cluster.foo()
        self.assertEquals({'retry_for': 0}, cluster.router.kwargs_seen.pop())

    def test_protection_from_infinate_loops(self):
        cluster = self.build_cluster(connection=ScumbagConnection)
        with self.assertRaises(Exception):
            cluster.foo()


class EventualCommandTest(BaseTest):
    def test_unevaled_repr(self):
        ec = EventualCommand('foo')
        ec('bar', baz='foo')

        self.assertEquals(repr(ec), u"<EventualCommand: foo args=('bar',) kwargs={'baz': 'foo'}>")

    def test_evaled_repr(self):
        ec = EventualCommand('foo')
        ec('bar', baz='foo')
        ec.resolve_as('biz')

        self.assertEquals(repr(ec), u"'biz'")

    def test_coersion(self):
        ec = EventualCommand('foo')()
        ec.resolve_as('5')

        self.assertEquals(int(ec), 5)

    def test_nonzero(self):
        ec = EventualCommand('foo')()
        ec.resolve_as(None)

        self.assertEquals(int(ec or 0), 0)

    def test_evaled_unicode(self):
        ec = EventualCommand('foo')
        ec.resolve_as('biz')

        self.assertEquals(unicode(ec), u'biz')

    def test_command_error_returns_as_error(self):
        ec = EventualCommand('foo')
        ec.resolve_as(CommandError([ValueError('test')]))
        self.assertEquals(ec.is_error, True)

    def test_other_error_does_not_return_as_error(self):
        ec = EventualCommand('foo')
        ec.resolve_as(ValueError('test'))
        self.assertEquals(ec.is_error, False)

    def test_isinstance_check(self):
        ec = EventualCommand('foo')
        ec.resolve_as(['foo', 'bar'])

        self.assertEquals(isinstance(ec, list), True)


class ApplyDefaultsTest(BaseTest):
    def test_does_apply(self):
        host = {'port': 6379}
        defaults = {'host': 'localhost'}
        results = apply_defaults(host, defaults)
        self.assertEquals(results, {
            'port': 6379,
            'host': 'localhost',
        })

    def test_does_not_overwrite(self):
        host = {'port': 6379}
        defaults = {'port': 9000}
        results = apply_defaults(host, defaults)
        self.assertEquals(results, {
            'port': 6379,
        })

########NEW FILE########
__FILENAME__ = tests
from __future__ import absolute_import

import mock
import time

from collections import Iterable
from inspect import getargspec

from nydus.db.base import BaseCluster
from nydus.db.backends import BaseConnection
from nydus.db.routers import BaseRouter, RoundRobinRouter
from nydus.db.routers.keyvalue import ConsistentHashingRouter
from nydus.testutils import BaseTest


def _get_func(func):
    return getattr(func, '__wraps__', func)


class DummyConnection(BaseConnection):
    def __init__(self, i):
        self.host = 'dummyhost'
        self.i = i
        super(DummyConnection, self).__init__(i)

    @property
    def identifier(self):
        return "%s:%s" % (self.host, self.i)


class BaseRouterTest(BaseTest):
    Router = BaseRouter

    class TestException(Exception):
        pass

    def setUp(self):
        self.hosts = dict((i, {}) for i in xrange(5))
        self.cluster = BaseCluster(router=self.Router, hosts=self.hosts, backend=DummyConnection)
        self.router = self.cluster.router

    def get_dbs(self, *args, **kwargs):
        return self.router.get_dbs(*args, **kwargs)

    def test_not_ready(self):
        self.assertTrue(not self.router._ready)

    def test_get_dbs_iterable(self):
        db_nums = self.get_dbs(attr='test', args=('foo',))
        self.assertIsInstance(db_nums, Iterable)

    def test_get_dbs_unabletosetuproute(self):
        with mock.patch.object(self.router, '_setup_router', return_value=False):
            with self.assertRaises(BaseRouter.UnableToSetupRouter):
                self.get_dbs(attr='test', args=('foo',))

    def test_setup_router_returns_true(self):
        self.assertTrue(self.router.setup_router())

    def test_offers_router_interface(self):
        func = _get_func(self.router.get_dbs)
        self.assertTrue(callable(func))
        dbargs, _, _, dbdefaults = getargspec(func)
        self.assertTrue(set(dbargs) >= set(['self', 'attr', 'args', 'kwargs']))
        self.assertIsNone(dbdefaults)

        func = _get_func(self.router.setup_router)
        self.assertTrue(callable(func))
        setupargs, _, _, setupdefaults = getargspec(func)
        self.assertTrue(set(setupargs) >= set(['self', 'args', 'kwargs']))
        self.assertIsNone(setupdefaults)

    def test_returns_whole_cluster_without_key(self):
        self.assertEquals(self.hosts.keys(), self.get_dbs(attr='test'))

    def test_get_dbs_handles_exception(self):
        with mock.patch.object(self.router, '_route') as _route:
            with mock.patch.object(self.router, '_handle_exception') as _handle_exception:
                _route.side_effect = self.TestException()

                self.get_dbs(attr='test', args=('foo',))

                self.assertTrue(_handle_exception.called)


class BaseBaseRouterTest(BaseRouterTest):
    def test__setup_router_returns_true(self):
        self.assertTrue(self.router._setup_router())

    def test__pre_routing_returns_args_and_kwargs(self):
        self.assertEqual((('foo',), {}), self.router._pre_routing(attr='test', args=('foo',)))

    def test__route_returns_first_db_num(self):
        self.assertEqual(self.cluster.hosts.keys()[0], self.router._route(attr='test', args=('foo',))[0])

    def test__post_routing_returns_db_nums(self):
        db_nums = self.hosts.keys()

        self.assertEqual(db_nums, self.router._post_routing(attr='test', db_nums=db_nums, args=('foo',)))

    def test__handle_exception_raises_same_exception(self):
        e = self.TestException()

        with self.assertRaises(self.TestException):
            self.router._handle_exception(e)

    def test_returns_sequence_with_one_item_when_given_key(self):
        self.assertEqual(len(self.get_dbs(attr='test', args=('foo',))), len(self.hosts))


class BaseRoundRobinRouterTest(BaseRouterTest):
    Router = RoundRobinRouter

    def setUp(self):
        super(BaseRoundRobinRouterTest, self).setUp()
        assert self.router._setup_router()

    def test_ensure_db_num(self):
        db_num = 0
        s_db_num = str(db_num)

        self.assertEqual(self.router.ensure_db_num(db_num), db_num)
        self.assertEqual(self.router.ensure_db_num(s_db_num), db_num)

    def test_esnure_db_num_raises(self):
        with self.assertRaises(RoundRobinRouter.InvalidDBNum):
            self.router.ensure_db_num('a')

    def test_flush_down_connections(self):
        self.router._get_db_attempts = 9001
        self._down_connections = {0: time.time()}

        self.router.flush_down_connections()

        self.assertEqual(self.router._get_db_attempts, 0)
        self.assertEqual(self.router._down_connections, {})

    def test_mark_connection_down(self):
        db_num = 0

        self.router.mark_connection_down(db_num)

        self.assertAlmostEqual(self.router._down_connections[db_num], time.time(), delta=10)

    def test_mark_connection_up(self):
        db_num = 0

        self.router.mark_connection_down(db_num)

        self.assertIn(db_num, self.router._down_connections)

        self.router.mark_connection_up(db_num)

        self.assertNotIn(db_num, self.router._down_connections)

    def test__pre_routing_updates__get_db_attempts(self):
        self.router._pre_routing(attr='test', args=('foo',))

        self.assertEqual(self.router._get_db_attempts, 1)

    @mock.patch('nydus.db.routers.base.RoundRobinRouter.check_down_connections')
    def test__pre_routing_check_down_connections(self, _check_down_connections):
        self.router._get_db_attempts = RoundRobinRouter.attempt_reconnect_threshold + 1

        self.router._pre_routing(attr='test', args=('foo',))

        self.assertTrue(_check_down_connections.called)

    @mock.patch('nydus.db.routers.base.RoundRobinRouter.mark_connection_down')
    def test__pre_routing_retry_for(self, _mark_connection_down):
        db_num = 0

        self.router._pre_routing(attr='test', args=('foo',), retry_for=db_num)

        _mark_connection_down.assert_called_with(db_num)

    @mock.patch('nydus.db.routers.base.RoundRobinRouter.mark_connection_up')
    def test_online_connections_dont_get_marked_as_up(self, mark_connection_up):
        db_nums = [0]

        self.assertEqual(self.router._post_routing(attr='test', db_nums=db_nums, args=('foo',)), db_nums)
        self.assertFalse(mark_connection_up.called)

    @mock.patch('nydus.db.routers.base.RoundRobinRouter.mark_connection_up')
    def test_offline_connections_get_marked_as_up(self, mark_connection_up):
        self.router.mark_connection_down(0)
        db_nums = [0]

        self.assertEqual(self.router._post_routing(attr='test', db_nums=db_nums, args=('foo',)), db_nums)
        mark_connection_up.assert_called_with(db_nums[0])


class RoundRobinRouterTest(BaseRoundRobinRouterTest):
    def test__setup_router(self):
        self.assertTrue(self.router._setup_router())
        self.assertIsInstance(self.router._hosts_cycler, Iterable)

    def test__route_cycles_through_keys(self):
        db_nums = self.hosts.keys() * 2
        results = [self.router._route(attr='test', args=('foo',))[0] for _ in db_nums]

        self.assertEqual(results, db_nums)

    def test__route_retry(self):
        self.router.retry_timeout = 0

        db_num = 0

        self.router.mark_connection_down(db_num)

        db_nums = self.router._route(attr='test', args=('foo',))

        self.assertEqual(db_nums, [db_num])

    def test__route_skip_down(self):
        db_num = 0

        self.router.mark_connection_down(db_num)

        db_nums = self.router._route(attr='test', args=('foo',))

        self.assertNotEqual(db_nums, [db_num])
        self.assertEqual(db_nums, [db_num + 1])

    def test__route_hostlistexhausted(self):
        [self.router.mark_connection_down(db_num) for db_num in self.hosts.keys()]

        with self.assertRaises(RoundRobinRouter.HostListExhausted):
            self.router._route(attr='test', args=('foo',))


class ConsistentHashingRouterTest(BaseRoundRobinRouterTest):
    Router = ConsistentHashingRouter

    def get_dbs(self, *args, **kwargs):
        kwargs['attr'] = 'test'
        return super(ConsistentHashingRouterTest, self).get_dbs(*args, **kwargs)

    def test_retry_gives_next_host_if_primary_is_offline(self):
        self.assertEquals([2], self.get_dbs(args=('foo',)))
        self.assertEquals([4], self.get_dbs(args=('foo',), retry_for=2))

    def test_retry_host_change_is_sticky(self):
        self.assertEquals([2], self.get_dbs(args=('foo',)))
        self.assertEquals([4], self.get_dbs(args=('foo',), retry_for=2))

        self.assertEquals([4], self.get_dbs(args=('foo',)))

    def test_raises_host_list_exhaused_if_no_host_can_be_found(self):
        # Kill the first 4
        [self.get_dbs(retry_for=i) for i in range(4)]

        # And the 5th should raise an error
        self.assertRaises(
            ConsistentHashingRouter.HostListExhausted,
            self.get_dbs, **dict(args=('foo',), retry_for=4))

########NEW FILE########
