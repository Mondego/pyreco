__FILENAME__ = base
# Copyright 2013-2014 DataStax, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from cProfile import Profile
import logging
import os.path
import sys
from threading import Thread
import time
from optparse import OptionParser

from greplin import scales

dirname = os.path.dirname(os.path.abspath(__file__))
sys.path.append(dirname)
sys.path.append(os.path.join(dirname, '..'))

from cassandra.cluster import Cluster
from cassandra.io.asyncorereactor import AsyncoreConnection
from cassandra.policies import HostDistance

log = logging.getLogger()
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s"))
log.addHandler(handler)

have_libev = False
supported_reactors = [AsyncoreConnection]
try:
    from cassandra.io.libevreactor import LibevConnection
    have_libev = True
    supported_reactors.append(LibevConnection)
except ImportError as exc:
    pass

KEYSPACE = "testkeyspace"
TABLE = "testtable"


def setup(hosts):

    cluster = Cluster(hosts)
    cluster.set_core_connections_per_host(HostDistance.LOCAL, 1)
    session = cluster.connect()

    rows = session.execute("SELECT keyspace_name FROM system.schema_keyspaces")
    if KEYSPACE in [row[0] for row in rows]:
        log.debug("dropping existing keyspace...")
        session.execute("DROP KEYSPACE " + KEYSPACE)

    log.debug("Creating keyspace...")
    session.execute("""
        CREATE KEYSPACE %s
        WITH replication = { 'class': 'SimpleStrategy', 'replication_factor': '2' }
        """ % KEYSPACE)

    log.debug("Setting keyspace...")
    session.set_keyspace(KEYSPACE)

    log.debug("Creating table...")
    session.execute("""
        CREATE TABLE %s (
            thekey text,
            col1 text,
            col2 text,
            PRIMARY KEY (thekey, col1)
        )
        """ % TABLE)


def teardown(hosts):
    cluster = Cluster(hosts)
    cluster.set_core_connections_per_host(HostDistance.LOCAL, 1)
    session = cluster.connect()
    session.execute("DROP KEYSPACE " + KEYSPACE)


def benchmark(thread_class):
    options, args = parse_options()
    for conn_class in options.supported_reactors:
        setup(options.hosts)
        log.info("==== %s ====" % (conn_class.__name__,))

        cluster = Cluster(options.hosts, metrics_enabled=options.enable_metrics)
        cluster.connection_class = conn_class
        session = cluster.connect(KEYSPACE)

        log.debug("Sleeping for two seconds...")
        time.sleep(2.0)

        query = session.prepare("""
            INSERT INTO {table} (thekey, col1, col2) VALUES (?, ?, ?)
            """.format(table=TABLE))
        values = ('key', 'a', 'b')

        per_thread = options.num_ops // options.threads
        threads = []

        log.debug("Beginning inserts...")
        start = time.time()
        try:
            for i in range(options.threads):
                thread = thread_class(i, session, query, values, per_thread, options.profile)
                thread.daemon = True
                threads.append(thread)

            for thread in threads:
                thread.start()

            for thread in threads:
                while thread.is_alive():
                    thread.join(timeout=0.5)

            end = time.time()
        finally:
            teardown(options.hosts)

        total = end - start
        log.info("Total time: %0.2fs" % total)
        log.info("Average throughput: %0.2f/sec" % (options.num_ops / total))
        if options.enable_metrics:
            stats = scales.getStats()['cassandra']
            log.info("Connection errors: %d", stats['connection_errors'])
            log.info("Write timeouts: %d", stats['write_timeouts'])
            log.info("Read timeouts: %d", stats['read_timeouts'])
            log.info("Unavailables: %d", stats['unavailables'])
            log.info("Other errors: %d", stats['other_errors'])
            log.info("Retries: %d", stats['retries'])

            request_timer = stats['request_timer']
            log.info("Request latencies:")
            log.info("  min: %0.4fs", request_timer['min'])
            log.info("  max: %0.4fs", request_timer['max'])
            log.info("  mean: %0.4fs", request_timer['mean'])
            log.info("  stddev: %0.4fs", request_timer['stddev'])
            log.info("  median: %0.4fs", request_timer['median'])
            log.info("  75th: %0.4fs", request_timer['75percentile'])
            log.info("  95th: %0.4fs", request_timer['95percentile'])
            log.info("  98th: %0.4fs", request_timer['98percentile'])
            log.info("  99th: %0.4fs", request_timer['99percentile'])
            log.info("  99.9th: %0.4fs", request_timer['999percentile'])


def parse_options():
    parser = OptionParser()
    parser.add_option('-H', '--hosts', default='127.0.0.1',
                      help='cassandra hosts to connect to (comma-separated list) [default: %default]')
    parser.add_option('-t', '--threads', type='int', default=1,
                      help='number of threads [default: %default]')
    parser.add_option('-n', '--num-ops', type='int', default=10000,
                      help='number of operations [default: %default]')
    parser.add_option('--asyncore-only', action='store_true', dest='asyncore_only',
                      help='only benchmark with asyncore connections')
    parser.add_option('--libev-only', action='store_true', dest='libev_only',
                      help='only benchmark with libev connections')
    parser.add_option('-m', '--metrics', action='store_true', dest='enable_metrics',
                      help='enable and print metrics for operations')
    parser.add_option('-l', '--log-level', default='info',
                      help='logging level: debug, info, warning, or error')
    parser.add_option('-p', '--profile', action='store_true', dest='profile',
                      help='Profile the run')

    options, args = parser.parse_args()

    options.hosts = options.hosts.split(',')

    log.setLevel(options.log_level.upper())

    if options.asyncore_only:
        options.supported_reactors = [AsyncoreConnection]
    elif options.libev_only:
        if not have_libev:
            log.error("libev is not available")
            sys.exit(1)
        options.supported_reactors = [LibevConnection]
    else:
        options.supported_reactors = supported_reactors
        if not have_libev:
            log.warning("Not benchmarking libev reactor because libev is not available")

    return options, args


class BenchmarkThread(Thread):

    def __init__(self, thread_num, session, query, values, num_queries, profile):
        Thread.__init__(self)
        self.thread_num = thread_num
        self.session = session
        self.query = query
        self.values = values
        self.num_queries = num_queries
        self.profiler = Profile() if profile else None

    def start_profile(self):
        if self.profiler:
            self.profiler.enable()

    def finish_profile(self):
        if self.profiler:
            self.profiler.disable()
            self.profiler.dump_stats('profile-%d' % self.thread_num)

########NEW FILE########
__FILENAME__ = callback_full_pipeline
# Copyright 2013-2014 DataStax, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import logging

from itertools import count
from threading import Event

from base import benchmark, BenchmarkThread
from six.moves import range

log = logging.getLogger(__name__)


sentinel = object()


class Runner(BenchmarkThread):

    def __init__(self, *args, **kwargs):
        BenchmarkThread.__init__(self, *args, **kwargs)
        self.num_started = count()
        self.num_finished = count()
        self.event = Event()

    def insert_next(self, previous_result=sentinel):
        if previous_result is not sentinel:
            if isinstance(previous_result, BaseException):
                log.error("Error on insert: %r", previous_result)
            if next(self.num_finished) >= self.num_queries:
                self.event.set()

        if next(self.num_started) <= self.num_queries:
            future = self.session.execute_async(self.query, self.values)
            future.add_callbacks(self.insert_next, self.insert_next)

    def run(self):
        self.start_profile()

        for _ in range(min(120, self.num_queries)):
            self.insert_next()

        self.event.wait()

        self.finish_profile()


if __name__ == "__main__":
    benchmark(Runner)

########NEW FILE########
__FILENAME__ = future_batches
# Copyright 2013-2014 DataStax, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import logging
from base import benchmark, BenchmarkThread
from six.moves import queue

log = logging.getLogger(__name__)


class Runner(BenchmarkThread):

    def run(self):
        futures = queue.Queue(maxsize=121)

        self.start_profile()

        for i in range(self.num_queries):
            if i > 0 and i % 120 == 0:
                # clear the existing queue
                while True:
                    try:
                        futures.get_nowait().result()
                    except queue.Empty:
                        break

            future = self.session.execute_async(self.query, self.values)
            futures.put_nowait(future)

        while True:
            try:
                futures.get_nowait().result()
            except queue.Empty:
                break

        self.finish_profile()


if __name__ == "__main__":
    benchmark(Runner)

########NEW FILE########
__FILENAME__ = future_full_pipeline
# Copyright 2013-2014 DataStax, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import logging
from base import benchmark, BenchmarkThread
from six.moves import queue

log = logging.getLogger(__name__)


class Runner(BenchmarkThread):

    def run(self):
        futures = queue.Queue(maxsize=121)

        self.start_profile()

        for i in range(self.num_queries):
            if i >= 120:
                old_future = futures.get_nowait()
                old_future.result()

            future = self.session.execute_async(self.query, self.values)
            futures.put_nowait(future)

        while True:
            try:
                futures.get_nowait().result()
            except queue.Empty:
                break

        self.finish_profile


if __name__ == "__main__":
    benchmark(Runner)

########NEW FILE########
__FILENAME__ = future_full_throttle
# Copyright 2013-2014 DataStax, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import logging

from base import benchmark, BenchmarkThread

log = logging.getLogger(__name__)

class Runner(BenchmarkThread):

    def run(self):
        futures = []

        self.start_profile()

        for _ in range(self.num_queries):
            future = self.session.execute_async(self.query, self.values)
            futures.append(future)

        for future in futures:
            future.result()

        self.finish_profile()


if __name__ == "__main__":
    benchmark(Runner)

########NEW FILE########
__FILENAME__ = sync
# Copyright 2013-2014 DataStax, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from base import benchmark, BenchmarkThread
from six.moves import range


class Runner(BenchmarkThread):

    def run(self):
        self.start_profile()

        for _ in range(self.num_queries):
            self.session.execute(self.query, self.values)

        self.finish_profile()


if __name__ == "__main__":
    benchmark(Runner)

########NEW FILE########
__FILENAME__ = auth
# Copyright 2013-2014 DataStax, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and


class AuthProvider(object):
    """
    An abstract class that defines the interface that will be used for
    creating :class:`~.Authenticator` instances when opening new
    connections to Cassandra.

    .. versionadded:: 2.0.0
    """

    def new_authenticator(self, host):
        """
        Implementations of this class should return a new instance
        of :class:`~.Authenticator` or one of its subclasses.
        """
        raise NotImplementedError()


class Authenticator(object):
    """
    An abstract class that handles SASL authentication with Cassandra servers.

    Each time a new connection is created and the server requires authentication,
    a new instance of this class will be created by the corresponding
    :class:`~.AuthProvider` to handler that authentication. The lifecycle of the
    new :class:`~.Authenticator` will the be:

    1) The :meth:`~.initial_response()` method will be called. The return
    value will be sent to the server to initiate the handshake.

    2) The server will respond to each client response by either issuing a
    challenge or indicating that the authentication is complete (successful or not).
    If a new challenge is issued, :meth:`~.evaluate_challenge()`
    will be called to produce a response that will be sent to the
    server. This challenge/response negotiation will continue until the server
    responds that authentication is successful (or an :exc:`~.AuthenticationFailed`
    is raised).

    3) When the server indicates that authentication is successful,
    :meth:`~.on_authentication_success` will be called a token string that
    that the server may optionally have sent.

    The exact nature of the negotiation between the client and server is specific
    to the authentication mechanism configured server-side.

    .. versionadded:: 2.0.0
    """

    def initial_response(self):
        """
        Returns an message to send to the server to initiate the SASL handshake.
        :const:`None` may be returned to send an empty message.
        """
        return None

    def evaluate_challenge(self, challenge):
        """
        Called when the server sends a challenge message.  Generally, this method
        should return :const:`None` when authentication is complete from a
        client perspective.  Otherwise, a string should be returned.
        """
        raise NotImplementedError()

    def on_authentication_success(self, token):
        """
        Called when the server indicates that authentication was successful.
        Depending on the authentication mechanism, `token` may be :const:`None`
        or a string.
        """
        pass


class PlainTextAuthProvider(AuthProvider):
    """
    An :class:`~.AuthProvider` that works with Cassandra's PasswordAuthenticator.

    Example usage::

        from cassandra.cluster import Cluster
        from cassandra.auth import PlainTextAuthProvider

        auth_provider = PlainTextAuthProvider(
                username='cassandra', password='cassandra')
        cluster = Cluster(auth_provider=auth_provider)

    .. versionadded:: 2.0.0
    """

    def __init__(self, username, password):
        self.username = username
        self.password = password

    def new_authenticator(self, host):
        return PlainTextAuthenticator(self.username, self.password)


class PlainTextAuthenticator(Authenticator):
    """
    An :class:`~.Authenticator` that works with Cassandra's PasswordAuthenticator.

    .. versionadded:: 2.0.0
    """

    def __init__(self, username, password):
        self.username = username
        self.password = password

    def initial_response(self):
        return "\x00%s\x00%s" % (self.username, self.password)

    def evaluate_challenge(self, challenge):
        return None

########NEW FILE########
__FILENAME__ = cluster
# Copyright 2013-2014 DataStax, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
This module houses the main classes you will interact with,
:class:`.Cluster` and :class:`.Session`.
"""
from __future__ import absolute_import

import atexit
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
import logging
import socket
import sys
import time
from threading import Lock, RLock, Thread, Event

import six
from six.moves import range
from six.moves import queue as Queue

import weakref
from weakref import WeakValueDictionary
try:
    from weakref import WeakSet
except ImportError:
    from cassandra.util import WeakSet  # NOQA

from functools import partial, wraps
from itertools import groupby

from cassandra import (ConsistencyLevel, AuthenticationFailed,
                       OperationTimedOut, UnsupportedOperation)
from cassandra.connection import ConnectionException, ConnectionShutdown
from cassandra.protocol import (QueryMessage, ResultMessage,
                                ErrorMessage, ReadTimeoutErrorMessage,
                                WriteTimeoutErrorMessage,
                                UnavailableErrorMessage,
                                OverloadedErrorMessage,
                                PrepareMessage, ExecuteMessage,
                                PreparedQueryNotFound,
                                IsBootstrappingErrorMessage,
                                BatchMessage, RESULT_KIND_PREPARED,
                                RESULT_KIND_SET_KEYSPACE, RESULT_KIND_ROWS,
                                RESULT_KIND_SCHEMA_CHANGE)
from cassandra.metadata import Metadata, protect_name
from cassandra.policies import (RoundRobinPolicy, SimpleConvictionPolicy,
                                ExponentialReconnectionPolicy, HostDistance,
                                RetryPolicy)
from cassandra.pool import (_ReconnectionHandler, _HostReconnectionHandler,
                            HostConnectionPool, NoConnectionsAvailable)
from cassandra.query import (SimpleStatement, PreparedStatement, BoundStatement,
                             BatchStatement, bind_params, QueryTrace, Statement,
                             named_tuple_factory, dict_factory)

# default to gevent when we are monkey patched, otherwise if libev is available, use that as the
# default because it's faster than asyncore
if 'gevent.monkey' in sys.modules:
    from cassandra.io.geventreactor import GeventConnection as DefaultConnection
else:
    try:
        from cassandra.io.libevreactor import LibevConnection as DefaultConnection  # NOQA
    except ImportError:
        from cassandra.io.asyncorereactor import AsyncoreConnection as DefaultConnection  # NOQA

# Forces load of utf8 encoding module to avoid deadlock that occurs
# if code that is being imported tries to import the module in a seperate
# thread.
# See http://bugs.python.org/issue10923
"".encode('utf8')

log = logging.getLogger(__name__)


DEFAULT_MIN_REQUESTS = 5
DEFAULT_MAX_REQUESTS = 100

DEFAULT_MIN_CONNECTIONS_PER_LOCAL_HOST = 2
DEFAULT_MAX_CONNECTIONS_PER_LOCAL_HOST = 8

DEFAULT_MIN_CONNECTIONS_PER_REMOTE_HOST = 1
DEFAULT_MAX_CONNECTIONS_PER_REMOTE_HOST = 2


_NOT_SET = object()


class NoHostAvailable(Exception):
    """
    Raised when an operation is attempted but all connections are
    busy, defunct, closed, or resulted in errors when used.
    """

    errors = None
    """
    A map of the form ``{ip: exception}`` which details the particular
    Exception that was caught for each host the operation was attempted
    against.
    """

    def __init__(self, message, errors):
        Exception.__init__(self, message, errors)
        self.errors = errors


def _future_completed(future):
    """ Helper for run_in_executor() """
    exc = future.exception()
    if exc:
        log.debug("Failed to run task on executor", exc_info=exc)


def run_in_executor(f):
    """
    A decorator to run the given method in the ThreadPoolExecutor.
    """

    @wraps(f)
    def new_f(self, *args, **kwargs):

        if self.is_shutdown:
            return
        try:
            future = self.executor.submit(f, self, *args, **kwargs)
            future.add_done_callback(_future_completed)
        except Exception:
            log.exception("Failed to submit task to executor")

    return new_f


def _shutdown_cluster(cluster):
    if cluster and not cluster.is_shutdown:
        cluster.shutdown()


class Cluster(object):
    """
    The main class to use when interacting with a Cassandra cluster.
    Typically, one instance of this class will be created for each
    separate Cassandra cluster that your application interacts with.

    Example usage::

        >>> from cassandra.cluster import Cluster
        >>> cluster = Cluster(['192.168.1.1', '192.168.1.2'])
        >>> session = cluster.connect()
        >>> session.execute("CREATE KEYSPACE ...")
        >>> ...
        >>> cluster.shutdown()

    """

    port = 9042
    """
    The server-side port to open connections to. Defaults to 9042.
    """

    cql_version = None
    """
    If a specific version of CQL should be used, this may be set to that
    string version.  Otherwise, the highest CQL version supported by the
    server will be automatically used.
    """

    protocol_version = 2
    """
    The version of the native protocol to use.  The protocol version 2
    add support for lightweight transactions, batch operations, and
    automatic query paging, but is only supported by Cassandra 2.0+.  When
    working with Cassandra 1.2, this must be set to 1.  You can also set
    this to 1 when working with Cassandra 2.0+, but features that require
    the version 2 protocol will not be enabled.
    """

    compression = True
    """
    Controls compression for communications between the driver and Cassandra.
    If left as the default of :const:`True`, either lz4 or snappy compression
    may be used, depending on what is supported by both the driver
    and Cassandra.  If both are fully supported, lz4 will be preferred.

    You may also set this to 'snappy' or 'lz4' to request that specific
    compression type.

    Setting this to :const:`False` disables compression.
    """

    _auth_provider = None
    _auth_provider_callable = None

    @property
    def auth_provider(self):
        """
        When :attr:`~.Cluster.protocol_version` is 2 or higher, this should
        be an instance of a subclass of :class:`~cassandra.auth.AuthProvider`,
        such as :class:`~.PlainTextAuthProvider`.

        When :attr:`~.Cluster.protocol_version` is 1, this should be
        a function that accepts one argument, the IP address of a node,
        and returns a dict of credentials for that node.

        When not using authentication, this should be left as :const:`None`.
        """
        return self._auth_provider

    @auth_provider.setter  # noqa
    def auth_provider(self, value):
        if not value:
            self._auth_provider = value
            return

        try:
            self._auth_provider_callable = value.new_authenticator
        except AttributeError:
            if self.protocol_version > 1:
                raise TypeError("auth_provider must implement the cassandra.auth.AuthProvider "
                                "interface when protocol_version >= 2")
            elif not callable(value):
                raise TypeError("auth_provider must be callable when protocol_version == 1")
            self._auth_provider_callable = value

        self._auth_provider = value

    load_balancing_policy = None
    """
    An instance of :class:`.policies.LoadBalancingPolicy` or
    one of its subclasses.  Defaults to :class:`~.RoundRobinPolicy`.
    """

    reconnection_policy = ExponentialReconnectionPolicy(1.0, 600.0)
    """
    An instance of :class:`.policies.ReconnectionPolicy`. Defaults to an instance
    of :class:`.ExponentialReconnectionPolicy` with a base delay of one second and
    a max delay of ten minutes.
    """

    default_retry_policy = RetryPolicy()
    """
    A default :class:`.policies.RetryPolicy` instance to use for all
    :class:`.Statement` objects which do not have a :attr:`~.Statement.retry_policy`
    explicitly set.
    """

    conviction_policy_factory = SimpleConvictionPolicy
    """
    A factory function which creates instances of
    :class:`.policies.ConvictionPolicy`.  Defaults to
    :class:`.policies.SimpleConvictionPolicy`.
    """

    metrics_enabled = False
    """
    Whether or not metric collection is enabled.  If enabled, :attr:`.metrics`
    will be an instance of :class:`~cassandra.metrics.Metrics`.
    """

    metrics = None
    """
    An instance of :class:`cassandra.metrics.Metrics` if :attr:`.metrics_enabled` is
    :const:`True`, else :const:`None`.
    """

    ssl_options = None
    """
    A optional dict which will be used as kwargs for ``ssl.wrap_socket()``
    when new sockets are created.  This should be used when client encryption
    is enabled in Cassandra.

    By default, a ``ca_certs`` value should be supplied (the value should be
    a string pointing to the location of the CA certs file), and you probably
    want to specify ``ssl_version`` as ``ssl.PROTOCOL_TLSv1`` to match
    Cassandra's default protocol.
    """

    sockopts = None
    """
    An optional list of tuples which will be used as arguments to
    ``socket.setsockopt()`` for all created sockets.
    """

    max_schema_agreement_wait = 10
    """
    The maximum duration (in seconds) that the driver will wait for schema
    agreement across the cluster. Defaults to ten seconds.
    """

    metadata = None
    """
    An instance of :class:`cassandra.metadata.Metadata`.
    """

    connection_class = DefaultConnection
    """
    This determines what event loop system will be used for managing
    I/O with Cassandra.  These are the current options:

    * :class:`cassandra.io.asyncorereactor.AsyncoreConnection`
    * :class:`cassandra.io.libevreactor.LibevConnection`

    By default, ``AsyncoreConnection`` will be used, which uses
    the ``asyncore`` module in the Python standard library.  The
    performance is slightly worse than with ``libev``, but it is
    supported on a wider range of systems.

    If ``libev`` is installed, ``LibevConnection`` will be used instead.
    """

    control_connection_timeout = 2.0
    """
    A timeout, in seconds, for queries made by the control connection, such
    as querying the current schema and information about nodes in the cluster.
    If set to :const:`None`, there will be no timeout for these queries.
    """

    sessions = None
    control_connection = None
    scheduler = None
    executor = None
    is_shutdown = False
    _is_setup = False
    _prepared_statements = None
    _prepared_statement_lock = Lock()

    _listeners = None
    _listener_lock = None

    def __init__(self,
                 contact_points=("127.0.0.1",),
                 port=9042,
                 compression=True,
                 auth_provider=None,
                 load_balancing_policy=None,
                 reconnection_policy=None,
                 default_retry_policy=None,
                 conviction_policy_factory=None,
                 metrics_enabled=False,
                 connection_class=None,
                 ssl_options=None,
                 sockopts=None,
                 cql_version=None,
                 protocol_version=2,
                 executor_threads=2,
                 max_schema_agreement_wait=10,
                 control_connection_timeout=2.0):
        """
        Any of the mutable Cluster attributes may be set as keyword arguments
        to the constructor.
        """
        self.contact_points = contact_points
        self.port = port
        self.compression = compression
        self.protocol_version = protocol_version
        self.auth_provider = auth_provider

        if load_balancing_policy is not None:
            if isinstance(load_balancing_policy, type):
                raise TypeError("load_balancing_policy should not be a class, it should be an instance of that class")

            self.load_balancing_policy = load_balancing_policy
        else:
            self.load_balancing_policy = RoundRobinPolicy()

        if reconnection_policy is not None:
            if isinstance(reconnection_policy, type):
                raise TypeError("reconnection_policy should not be a class, it should be an instance of that class")

            self.reconnection_policy = reconnection_policy

        if default_retry_policy is not None:
            if isinstance(default_retry_policy, type):
                raise TypeError("default_retry_policy should not be a class, it should be an instance of that class")

            self.default_retry_policy = default_retry_policy

        if conviction_policy_factory is not None:
            if not callable(conviction_policy_factory):
                raise ValueError("conviction_policy_factory must be callable")
            self.conviction_policy_factory = conviction_policy_factory

        if connection_class is not None:
            self.connection_class = connection_class

        self.metrics_enabled = metrics_enabled
        self.ssl_options = ssl_options
        self.sockopts = sockopts
        self.cql_version = cql_version
        self.max_schema_agreement_wait = max_schema_agreement_wait
        self.control_connection_timeout = control_connection_timeout

        self._listeners = set()
        self._listener_lock = Lock()

        # let Session objects be GC'ed (and shutdown) when the user no longer
        # holds a reference. Normally the cycle detector would handle this,
        # but implementing __del__ prevents that.
        self.sessions = WeakSet()
        self.metadata = Metadata(self)
        self.control_connection = None
        self._prepared_statements = WeakValueDictionary()

        self._min_requests_per_connection = {
            HostDistance.LOCAL: DEFAULT_MIN_REQUESTS,
            HostDistance.REMOTE: DEFAULT_MIN_REQUESTS
        }

        self._max_requests_per_connection = {
            HostDistance.LOCAL: DEFAULT_MAX_REQUESTS,
            HostDistance.REMOTE: DEFAULT_MAX_REQUESTS
        }

        self._core_connections_per_host = {
            HostDistance.LOCAL: DEFAULT_MIN_CONNECTIONS_PER_LOCAL_HOST,
            HostDistance.REMOTE: DEFAULT_MIN_CONNECTIONS_PER_REMOTE_HOST
        }

        self._max_connections_per_host = {
            HostDistance.LOCAL: DEFAULT_MAX_CONNECTIONS_PER_LOCAL_HOST,
            HostDistance.REMOTE: DEFAULT_MAX_CONNECTIONS_PER_REMOTE_HOST
        }

        self.executor = ThreadPoolExecutor(max_workers=executor_threads)
        self.scheduler = _Scheduler(self.executor)

        self._lock = RLock()

        if self.metrics_enabled:
            from cassandra.metrics import Metrics
            self.metrics = Metrics(weakref.proxy(self))

        self.control_connection = ControlConnection(
            self, self.control_connection_timeout)

    def get_min_requests_per_connection(self, host_distance):
        return self._min_requests_per_connection[host_distance]

    def set_min_requests_per_connection(self, host_distance, min_requests):
        self._min_requests_per_connection[host_distance] = min_requests

    def get_max_requests_per_connection(self, host_distance):
        return self._max_requests_per_connection[host_distance]

    def set_max_requests_per_connection(self, host_distance, max_requests):
        self._max_requests_per_connection[host_distance] = max_requests

    def get_core_connections_per_host(self, host_distance):
        """
        Gets the minimum number of connections per Session that will be opened
        for each host with :class:`~.HostDistance` equal to `host_distance`.
        The default is 2 for :attr:`~HostDistance.LOCAL` and 1 for
        :attr:`~HostDistance.REMOTE`.
        """
        return self._core_connections_per_host[host_distance]

    def set_core_connections_per_host(self, host_distance, core_connections):
        """
        Sets the minimum number of connections per Session that will be opened
        for each host with :class:`~.HostDistance` equal to `host_distance`.
        The default is 2 for :attr:`~HostDistance.LOCAL` and 1 for
        :attr:`~HostDistance.REMOTE`.
        """
        old = self._core_connections_per_host[host_distance]
        self._core_connections_per_host[host_distance] = core_connections
        if old < core_connections:
            self._ensure_core_connections()

    def get_max_connections_per_host(self, host_distance):
        """
        Gets the maximum number of connections per Session that will be opened
        for each host with :class:`~.HostDistance` equal to `host_distance`.
        The default is 8 for :attr:`~HostDistance.LOCAL` and 2 for
        :attr:`~HostDistance.REMOTE`.
        """
        return self._max_connections_per_host[host_distance]

    def set_max_connections_per_host(self, host_distance, max_connections):
        """
        Gets the maximum number of connections per Session that will be opened
        for each host with :class:`~.HostDistance` equal to `host_distance`.
        The default is 2 for :attr:`~HostDistance.LOCAL` and 1 for
        :attr:`~HostDistance.REMOTE`.
        """
        self._max_connections_per_host[host_distance] = max_connections

    def connection_factory(self, address, *args, **kwargs):
        """
        Called to create a new connection with proper configuration.
        Intended for internal use only.
        """
        kwargs = self._make_connection_kwargs(address, kwargs)
        return self.connection_class.factory(address, *args, **kwargs)

    def _make_connection_factory(self, host, *args, **kwargs):
        kwargs = self._make_connection_kwargs(host.address, kwargs)
        return partial(self.connection_class.factory, host.address, *args, **kwargs)

    def _make_connection_kwargs(self, address, kwargs_dict):
        if self._auth_provider_callable:
            kwargs_dict['authenticator'] = self._auth_provider_callable(address)

        kwargs_dict['port'] = self.port
        kwargs_dict['compression'] = self.compression
        kwargs_dict['sockopts'] = self.sockopts
        kwargs_dict['ssl_options'] = self.ssl_options
        kwargs_dict['cql_version'] = self.cql_version
        kwargs_dict['protocol_version'] = self.protocol_version

        return kwargs_dict

    def connect(self, keyspace=None):
        """
        Creates and returns a new :class:`~.Session` object.  If `keyspace`
        is specified, that keyspace will be the default keyspace for
        operations on the ``Session``.
        """
        with self._lock:
            if self.is_shutdown:
                raise Exception("Cluster is already shut down")

            if not self._is_setup:
                atexit.register(partial(_shutdown_cluster, self))
                for address in self.contact_points:
                    host = self.add_host(address, signal=False)
                    if host:
                        host.set_up()
                        for listener in self.listeners:
                            listener.on_add(host)

                self.load_balancing_policy.populate(
                    weakref.proxy(self), self.metadata.all_hosts())

                if self.control_connection:
                    try:
                        self.control_connection.connect()
                        log.debug("Control connection created")
                    except Exception:
                        log.exception("Control connection failed to connect, "
                                      "shutting down Cluster:")
                        self.shutdown()
                        raise

                self.load_balancing_policy.check_supported()

                self._is_setup = True

        session = self._new_session()
        if keyspace:
            session.set_keyspace(keyspace)
        return session

    def shutdown(self):
        """
        Closes all sessions and connection associated with this Cluster.
        To ensure all connections are properly closed, **you should always
        call shutdown() on a Cluster instance when you are done with it**.

        Once shutdown, a Cluster should not be used for any purpose.
        """
        with self._lock:
            if self.is_shutdown:
                return
            else:
                self.is_shutdown = True

        if self.scheduler:
            self.scheduler.shutdown()

        if self.control_connection:
            self.control_connection.shutdown()

        if self.sessions:
            for session in self.sessions:
                session.shutdown()

        if self.executor:
            self.executor.shutdown()

    def _new_session(self):
        session = Session(self, self.metadata.all_hosts())
        self.sessions.add(session)
        return session

    def _cleanup_failed_on_up_handling(self, host):
        self.load_balancing_policy.on_down(host)
        self.control_connection.on_down(host)
        for session in self.sessions:
            session.remove_pool(host)

        self._start_reconnector(host, is_host_addition=False)

    def _on_up_future_completed(self, host, futures, results, lock, finished_future):
        with lock:
            futures.discard(finished_future)

            try:
                results.append(finished_future.result())
            except Exception as exc:
                results.append(exc)

            if futures:
                return

        try:
            # all futures have completed at this point
            for exc in [f for f in results if isinstance(f, Exception)]:
                log.error("Unexpected failure while marking node %s up:", host, exc_info=exc)
                self._cleanup_failed_on_up_handling(host)
                return

            if not all(results):
                log.debug("Connection pool could not be created, not marking node %s up", host)
                self._cleanup_failed_on_up_handling(host)
                return

            # mark the host as up and notify all listeners
            host.set_up()
            for listener in self.listeners:
                listener.on_up(host)
        finally:
            with host.lock:
                host._currently_handling_node_up = False

        # see if there are any pools to add or remove now that the host is marked up
        for session in self.sessions:
            session.update_created_pools()

    def on_up(self, host):
        """
        Intended for internal use only.
        """
        if self.is_shutdown:
            return

        log.debug("Waiting to acquire lock for handling up status of node %s", host)
        with host.lock:
            if host._currently_handling_node_up:
                log.debug("Another thread is already handling up status of node %s", host)
                return

            if host.is_up:
                log.debug("Host %s was already marked up", host)
                return

            host._currently_handling_node_up = True
        log.debug("Starting to handle up status of node %s", host)

        have_future = False
        futures = set()
        try:
            log.info("Host %s may be up; will prepare queries and open connection pool", host)

            reconnector = host.get_and_set_reconnection_handler(None)
            if reconnector:
                log.debug("Now that host %s is up, cancelling the reconnection handler", host)
                reconnector.cancel()

            self._prepare_all_queries(host)
            log.debug("Done preparing all queries for host %s, ", host)

            for session in self.sessions:
                session.remove_pool(host)

            log.debug("Signalling to load balancing policy that host %s is up", host)
            self.load_balancing_policy.on_up(host)

            log.debug("Signalling to control connection that host %s is up", host)
            self.control_connection.on_up(host)

            log.debug("Attempting to open new connection pools for host %s", host)
            futures_lock = Lock()
            futures_results = []
            callback = partial(self._on_up_future_completed, host, futures, futures_results, futures_lock)
            for session in self.sessions:
                future = session.add_or_renew_pool(host, is_host_addition=False)
                if future is not None:
                    have_future = True
                    future.add_done_callback(callback)
                    futures.add(future)
        except Exception:
            log.exception("Unexpected failure handling node %s being marked up:", host)
            for future in futures:
                future.cancel()

            self._cleanup_failed_on_up_handling(host)

            with host.lock:
                host._currently_handling_node_up = False
            raise
        else:
            if not have_future:
                with host.lock:
                    host._currently_handling_node_up = False

        # for testing purposes
        return futures

    def _start_reconnector(self, host, is_host_addition):
        schedule = self.reconnection_policy.new_schedule()

        # in order to not hold references to this Cluster open and prevent
        # proper shutdown when the program ends, we'll just make a closure
        # of the current Cluster attributes to create new Connections with
        conn_factory = self._make_connection_factory(host)

        reconnector = _HostReconnectionHandler(
            host, conn_factory, is_host_addition, self.on_add, self.on_up,
            self.scheduler, schedule, host.get_and_set_reconnection_handler,
            new_handler=None)

        old_reconnector = host.get_and_set_reconnection_handler(reconnector)
        if old_reconnector:
            log.debug("Old host reconnector found for %s, cancelling", host)
            old_reconnector.cancel()

        log.debug("Starting reconnector for host %s", host)
        reconnector.start()

    @run_in_executor
    def on_down(self, host, is_host_addition, expect_host_to_be_down=False):
        """
        Intended for internal use only.
        """
        if self.is_shutdown:
            return

        with host.lock:
            if (not host.is_up and not expect_host_to_be_down) or host.is_currently_reconnecting():
                return

            host.set_down()

        log.warning("Host %s has been marked down", host)

        self.load_balancing_policy.on_down(host)
        self.control_connection.on_down(host)
        for session in self.sessions:
            session.on_down(host)

        for listener in self.listeners:
            listener.on_down(host)

        self._start_reconnector(host, is_host_addition)

    def on_add(self, host):
        if self.is_shutdown:
            return

        log.debug("Handling new host %r and notifying listeners", host)

        distance = self.load_balancing_policy.distance(host)
        if distance != HostDistance.IGNORED:
            self._prepare_all_queries(host)
            log.debug("Done preparing queries for new host %r", host)

        self.load_balancing_policy.on_add(host)
        self.control_connection.on_add(host)

        if distance == HostDistance.IGNORED:
            log.debug("Not adding connection pool for new host %r because the "
                      "load balancing policy has marked it as IGNORED", host)
            self._finalize_add(host)
            return

        futures_lock = Lock()
        futures_results = []
        futures = set()

        def future_completed(future):
            with futures_lock:
                futures.discard(future)

                try:
                    futures_results.append(future.result())
                except Exception as exc:
                    futures_results.append(exc)

                if futures:
                    return

            log.debug('All futures have completed for added host %s', host)

            for exc in [f for f in futures_results if isinstance(f, Exception)]:
                log.error("Unexpected failure while adding node %s, will not mark up:", host, exc_info=exc)
                return

            if not all(futures_results):
                log.warning("Connection pool could not be created, not marking node %s up", host)
                return

            self._finalize_add(host)

        have_future = False
        for session in self.sessions:
            future = session.add_or_renew_pool(host, is_host_addition=True)
            if future is not None:
                have_future = True
                futures.add(future)
                future.add_done_callback(future_completed)

        if not have_future:
            self._finalize_add(host)

    def _finalize_add(self, host):
        # mark the host as up and notify all listeners
        host.set_up()
        for listener in self.listeners:
            listener.on_add(host)

        # see if there are any pools to add or remove now that the host is marked up
        for session in self.sessions:
            session.update_created_pools()

    def on_remove(self, host):
        if self.is_shutdown:
            return

        log.debug("Removing host %s", host)
        host.set_down()
        self.load_balancing_policy.on_remove(host)
        for session in self.sessions:
            session.on_remove(host)
        for listener in self.listeners:
            listener.on_remove(host)
        self.control_connection.on_remove(host)

    def signal_connection_failure(self, host, connection_exc, is_host_addition, expect_host_to_be_down=False):
        is_down = host.signal_connection_failure(connection_exc)
        if is_down:
            self.on_down(host, is_host_addition, expect_host_to_be_down)
        return is_down

    def add_host(self, address, datacenter=None, rack=None, signal=True):
        """
        Called when adding initial contact points and when the control
        connection subsequently discovers a new node.  Intended for internal
        use only.
        """
        new_host = self.metadata.add_host(address, datacenter, rack)
        if new_host and signal:
            log.info("New Cassandra host %r discovered", new_host)
            self.on_add(new_host)

        return new_host

    def remove_host(self, host):
        """
        Called when the control connection observes that a node has left the
        ring.  Intended for internal use only.
        """
        if host and self.metadata.remove_host(host):
            log.info("Cassandra host %s removed", host)
            self.on_remove(host)

    def register_listener(self, listener):
        """
        Adds a :class:`cassandra.policies.HostStateListener` subclass instance to
        the list of listeners to be notified when a host is added, removed,
        marked up, or marked down.
        """
        with self._listener_lock:
            self._listeners.add(listener)

    def unregister_listener(self, listener):
        """ Removes a registered listener. """
        with self._listener_lock:
            self._listeners.remove(listener)

    @property
    def listeners(self):
        with self._listener_lock:
            return self._listeners.copy()

    def _ensure_core_connections(self):
        """
        If any host has fewer than the configured number of core connections
        open, attempt to open connections until that number is met.
        """
        for session in self.sessions:
            for pool in session._pools.values():
                pool.ensure_core_connections()

    def submit_schema_refresh(self, keyspace=None, table=None):
        """
        Schedule a refresh of the internal representation of the current
        schema for this cluster.  If `keyspace` is specified, only that
        keyspace will be refreshed, and likewise for `table`.
        """
        return self.executor.submit(
            self.control_connection.refresh_schema, keyspace, table)

    def _prepare_all_queries(self, host):
        if not self._prepared_statements:
            return

        log.debug("Preparing all known prepared statements against host %s", host)
        connection = None
        try:
            connection = self.connection_factory(host.address)
            try:
                self.control_connection.wait_for_schema_agreement(connection)
            except Exception:
                log.debug("Error waiting for schema agreement before preparing statements against host %s", host, exc_info=True)

            statements = self._prepared_statements.values()
            for keyspace, ks_statements in groupby(statements, lambda s: s.keyspace):
                if keyspace is not None:
                    connection.set_keyspace_blocking(keyspace)

                # prepare 10 statements at a time
                ks_statements = list(ks_statements)
                chunks = []
                for i in range(0, len(ks_statements), 10):
                    chunks.append(ks_statements[i:i + 10])

                for ks_chunk in chunks:
                    messages = [PrepareMessage(query=s.query_string) for s in ks_chunk]
                    # TODO: make this timeout configurable somehow?
                    responses = connection.wait_for_responses(*messages, timeout=5.0)
                    for response in responses:
                        if (not isinstance(response, ResultMessage) or
                                response.kind != RESULT_KIND_PREPARED):
                            log.debug("Got unexpected response when preparing "
                                      "statement on host %s: %r", host, response)

            log.debug("Done preparing all known prepared statements against host %s", host)
        except OperationTimedOut as timeout:
            log.warning("Timed out trying to prepare all statements on host %s: %s", host, timeout)
        except (ConnectionException, socket.error) as exc:
            log.warning("Error trying to prepare all statements on host %s: %r", host, exc)
        except Exception:
            log.exception("Error trying to prepare all statements on host %s", host)
        finally:
            if connection:
                connection.close()

    def prepare_on_all_sessions(self, query_id, prepared_statement, excluded_host):
        with self._prepared_statement_lock:
            self._prepared_statements[query_id] = prepared_statement
        for session in self.sessions:
            session.prepare_on_all_hosts(prepared_statement.query_string, excluded_host)


class Session(object):
    """
    A collection of connection pools for each host in the cluster.
    Instances of this class should not be created directly, only
    using :meth:`.Cluster.connect()`.

    Queries and statements can be executed through ``Session`` instances
    using the :meth:`~.Session.execute()` and :meth:`~.Session.execute_async()`
    methods.

    Example usage::

        >>> session = cluster.connect()
        >>> session.set_keyspace("mykeyspace")
        >>> session.execute("SELECT * FROM mycf")

    """

    cluster = None
    hosts = None
    keyspace = None
    is_shutdown = False

    row_factory = staticmethod(named_tuple_factory)
    """
    The format to return row results in.  By default, each
    returned row will be a named tuple.  You can alternatively
    use any of the following:

      - :func:`cassandra.query.tuple_factory` - return a result row as a tuple
      - :func:`cassandra.query.named_tuple_factory` - return a result row as a named tuple
      - :func:`cassandra.query.dict_factory` - return a result row as a dict
      - :func:`cassandra.query.ordered_dict_factory` - return a result row as an OrderedDict

    """

    default_timeout = 10.0
    """
    A default timeout, measured in seconds, for queries executed through
    :meth:`.execute()` or :meth:`.execute_async()`.  This default may be
    overridden with the `timeout` parameter for either of those methods
    or the `timeout` parameter for :meth:`.ResponseFuture.result()`.

    Setting this to :const:`None` will cause no timeouts to be set by default.

    **Important**: This timeout currently has no effect on callbacks registered
    on a :class:`~.ResponseFuture` through :meth:`.ResponseFuture.add_callback` or
    :meth:`.ResponseFuture.add_errback`; even if a query exceeds this default
    timeout, neither the registered callback or errback will be called.

    .. versionadded:: 2.0.0
    """

    default_consistency_level = ConsistencyLevel.ONE
    """
    The default :class:`~ConsistencyLevel` for operations executed through
    this session.  This default may be overridden by setting the
    :attr:`~.Statement.consistency_level` on individual statements.

    .. versionadded:: 1.2.0
    """

    max_trace_wait = 2.0
    """
    The maximum amount of time (in seconds) the driver will wait for trace
    details to be populated server-side for a query before giving up.
    If the `trace` parameter for :meth:`~.execute()` or :meth:`~.execute_async()`
    is :const:`True`, the driver will repeatedly attempt to fetch trace
    details for the query (using exponential backoff) until this limit is
    hit.  If the limit is passed, an error will be logged and the
    :attr:`.Statement.trace` will be left as :const:`None`. """

    default_fetch_size = 5000
    """
    By default, this many rows will be fetched at a time.  This can be
    specified per-query through :attr:`.Statement.fetch_size`.

    This only takes effect when protocol version 2 or higher is used.
    See :attr:`.Cluster.protocol_version` for details.

    .. versionadded:: 2.0.0
    """

    _lock = None
    _pools = None
    _load_balancer = None
    _metrics = None
    _protocol_version = None

    def __init__(self, cluster, hosts):
        self.cluster = cluster
        self.hosts = hosts

        self._lock = RLock()
        self._pools = {}
        self._load_balancer = cluster.load_balancing_policy
        self._metrics = cluster.metrics
        self._protocol_version = self.cluster.protocol_version

        # create connection pools in parallel
        futures = []
        for host in hosts:
            future = self.add_or_renew_pool(host, is_host_addition=False)
            if future is not None:
                futures.append(future)

        for future in futures:
            future.result()

    def execute(self, query, parameters=None, timeout=_NOT_SET, trace=False):
        """
        Execute the given query and synchronously wait for the response.

        If an error is encountered while executing the query, an Exception
        will be raised.

        `query` may be a query string or an instance of :class:`cassandra.query.Statement`.

        `parameters` may be a sequence or dict of parameters to bind.  If a
        sequence is used, ``%s`` should be used the placeholder for each
        argument.  If a dict is used, ``%(name)s`` style placeholders must
        be used.

        `timeout` should specify a floating-point timeout (in seconds) after
        which an :exc:`.OperationTimedOut` exception will be raised if the query
        has not completed.  If not set, the timeout defaults to
        :attr:`~.Session.default_timeout`.  If set to :const:`None`, there is
        no timeout.

        If `trace` is set to :const:`True`, an attempt will be made to
        fetch the trace details and attach them to the `query`'s
        :attr:`~.Statement.trace` attribute in the form of a :class:`.QueryTrace`
        instance.  This requires that `query` be a :class:`.Statement` subclass
        instance and not just a string.  If there is an error fetching the
        trace details, the :attr:`~.Statement.trace` attribute will be left as
        :const:`None`.
        """
        if timeout is _NOT_SET:
            timeout = self.default_timeout

        if trace and not isinstance(query, Statement):
            raise TypeError(
                "The query argument must be an instance of a subclass of "
                "cassandra.query.Statement when trace=True")

        future = self.execute_async(query, parameters, trace)
        try:
            result = future.result(timeout)
        finally:
            if trace:
                try:
                    query.trace = future.get_query_trace(self.max_trace_wait)
                except Exception:
                    log.exception("Unable to fetch query trace:")

        return result

    def execute_async(self, query, parameters=None, trace=False):
        """
        Execute the given query and return a :class:`~.ResponseFuture` object
        which callbacks may be attached to for asynchronous response
        delivery.  You may also call :meth:`~.ResponseFuture.result()`
        on the :class:`.ResponseFuture` to syncronously block for results at
        any time.

        If `trace` is set to :const:`True`, you may call
        :meth:`.ResponseFuture.get_query_trace()` after the request
        completes to retrieve a :class:`.QueryTrace` instance.

        Example usage::

            >>> session = cluster.connect()
            >>> future = session.execute_async("SELECT * FROM mycf")

            >>> def log_results(results):
            ...     for row in results:
            ...         log.info("Results: %s", row)

            >>> def log_error(exc):
            >>>     log.error("Operation failed: %s", exc)

            >>> future.add_callbacks(log_results, log_error)

        Async execution with blocking wait for results::

            >>> future = session.execute_async("SELECT * FROM mycf")
            >>> # do other stuff...

            >>> try:
            ...     results = future.result()
            ... except Exception:
            ...     log.exception("Operation failed:")

        """
        future = self._create_response_future(query, parameters, trace)
        future.send_request()
        return future

    def _create_response_future(self, query, parameters, trace):
        """ Returns the ResponseFuture before calling send_request() on it """

        prepared_statement = None

        if isinstance(query, six.string_types):
            query = SimpleStatement(query)
        elif isinstance(query, PreparedStatement):
            query = query.bind(parameters)

        cl = query.consistency_level if query.consistency_level is not None else self.default_consistency_level
        fetch_size = query.fetch_size
        if not fetch_size and self._protocol_version >= 2:
            fetch_size = self.default_fetch_size

        if isinstance(query, SimpleStatement):
            query_string = query.query_string
            if parameters:
                query_string = bind_params(query.query_string, parameters)
            message = QueryMessage(
                query_string, cl, query.serial_consistency_level,
                fetch_size=fetch_size)
        elif isinstance(query, BoundStatement):
            message = ExecuteMessage(
                query.prepared_statement.query_id, query.values, cl,
                query.serial_consistency_level, fetch_size=fetch_size)
            prepared_statement = query.prepared_statement
        elif isinstance(query, BatchStatement):
            if self._protocol_version < 2:
                raise UnsupportedOperation(
                    "BatchStatement execution is only supported with protocol version "
                    "2 or higher (supported in Cassandra 2.0 and higher).  Consider "
                    "setting Cluster.protocol_version to 2 to support this operation.")
            message = BatchMessage(
                query.batch_type, query._statements_and_parameters, cl)

        if trace:
            message.tracing = True

        return ResponseFuture(
            self, message, query, self.default_timeout, metrics=self._metrics,
            prepared_statement=prepared_statement)

    def prepare(self, query):
        """
        Prepares a query string, returing a :class:`~cassandra.query.PreparedStatement`
        instance which can be used as follows::

            >>> session = cluster.connect("mykeyspace")
            >>> query = "INSERT INTO users (id, name, age) VALUES (?, ?, ?)"
            >>> prepared = session.prepare(query)
            >>> session.execute(prepared, (user.id, user.name, user.age))

        Or you may bind values to the prepared statement ahead of time::

            >>> prepared = session.prepare(query)
            >>> bound_stmt = prepared.bind((user.id, user.name, user.age))
            >>> session.execute(bound_stmt)

        Of course, prepared statements may (and should) be reused::

            >>> prepared = session.prepare(query)
            >>> for user in users:
            ...     bound = prepared.bind((user.id, user.name, user.age))
            ...     session.execute(bound)

        **Important**: PreparedStatements should be prepared only once.
        Preparing the same query more than once will likely affect performance.
        """
        message = PrepareMessage(query=query)
        future = ResponseFuture(self, message, query=None)
        try:
            future.send_request()
            query_id, column_metadata = future.result()
        except Exception:
            log.exception("Error preparing query:")
            raise

        prepared_statement = PreparedStatement.from_message(
            query_id, column_metadata, self.cluster.metadata, query, self.keyspace)

        host = future._current_host
        try:
            self.cluster.prepare_on_all_sessions(query_id, prepared_statement, host)
        except Exception:
            log.exception("Error preparing query on all hosts:")

        return prepared_statement

    def prepare_on_all_hosts(self, query, excluded_host):
        """
        Prepare the given query on all hosts, excluding ``excluded_host``.
        Intended for internal use only.
        """
        futures = []
        for host in self._pools.keys():
            if host != excluded_host and host.is_up:
                future = ResponseFuture(self, PrepareMessage(query=query), None)

                # we don't care about errors preparing against specific hosts,
                # since we can always prepare them as needed when the prepared
                # statement is used.  Just log errors and continue on.
                try:
                    request_id = future._query(host)
                except Exception:
                    log.exception("Error preparing query for host %s:", host)
                    continue

                if request_id is None:
                    # the error has already been logged by ResponsFuture
                    log.debug("Failed to prepare query for host %s: %r",
                              host, future._errors.get(host))
                    continue

                futures.append((host, future))

        for host, future in futures:
            try:
                future.result()
            except Exception:
                log.exception("Error preparing query for host %s:", host)

    def shutdown(self):
        """
        Close all connections.  ``Session`` instances should not be used
        for any purpose after being shutdown.
        """
        with self._lock:
            if self.is_shutdown:
                return
            else:
                self.is_shutdown = True

        for pool in self._pools.values():
            pool.shutdown()

    def add_or_renew_pool(self, host, is_host_addition):
        """
        For internal use only.
        """
        distance = self._load_balancer.distance(host)
        if distance == HostDistance.IGNORED:
            return None

        def run_add_or_renew_pool():
            try:
                new_pool = HostConnectionPool(host, distance, self)
            except AuthenticationFailed as auth_exc:
                conn_exc = ConnectionException(str(auth_exc), host=host)
                self.cluster.signal_connection_failure(host, conn_exc, is_host_addition)
                return False
            except Exception as conn_exc:
                log.warning("Failed to create connection pool for new host %s: %s",
                            host, conn_exc)
                # the host itself will still be marked down, so we need to pass
                # a special flag to make sure the reconnector is created
                self.cluster.signal_connection_failure(
                        host, conn_exc, is_host_addition, expect_host_to_be_down=True)
                return False

            previous = self._pools.get(host)
            self._pools[host] = new_pool
            log.debug("Added pool for host %s to session", host)
            if previous:
                previous.shutdown()

            return True

        return self.submit(run_add_or_renew_pool)

    def remove_pool(self, host):
        pool = self._pools.pop(host, None)
        if pool:
            log.debug("Removed connection pool for %r", host)
            return self.submit(pool.shutdown)
        else:
            return None

    def update_created_pools(self):
        """
        When the set of live nodes change, the loadbalancer will change its
        mind on host distances. It might change it on the node that came/left
        but also on other nodes (for instance, if a node dies, another
        previously ignored node may be now considered).

        This method ensures that all hosts for which a pool should exist
        have one, and hosts that shouldn't don't.

        For internal use only.
        """
        for host in self.cluster.metadata.all_hosts():
            distance = self._load_balancer.distance(host)
            pool = self._pools.get(host)

            if not pool or pool.is_shutdown:
                if distance != HostDistance.IGNORED and host.is_up:
                    self.add_or_renew_pool(host, False)
            elif distance != pool.host_distance:
                # the distance has changed
                if distance == HostDistance.IGNORED:
                    self.remove_pool(host)
                else:
                    pool.host_distance = distance

    def on_down(self, host):
        """
        Called by the parent Cluster instance when a node is marked down.
        Only intended for internal use.
        """
        future = self.remove_pool(host)
        if future:
            future.add_done_callback(lambda f: self.update_created_pools())

    def on_remove(self, host):
        """ Internal """
        self.on_down(host)

    def set_keyspace(self, keyspace):
        """
        Set the default keyspace for all queries made through this Session.
        This operation blocks until complete.
        """
        self.execute('USE %s' % (protect_name(keyspace),))

    def _set_keyspace_for_all_pools(self, keyspace, callback):
        """
        Asynchronously sets the keyspace on all pools.  When all
        pools have set all of their connections, `callback` will be
        called with a dictionary of all errors that occurred, keyed
        by the `Host` that they occurred against.
        """
        self.keyspace = keyspace

        remaining_callbacks = set(self._pools.values())
        errors = {}

        if not remaining_callbacks:
            callback(errors)
            return

        def pool_finished_setting_keyspace(pool, host_errors):
            remaining_callbacks.remove(pool)
            if host_errors:
                errors[pool.host] = host_errors

            if not remaining_callbacks:
                callback(host_errors)

        for pool in self._pools.values():
            pool._set_keyspace_for_all_conns(keyspace, pool_finished_setting_keyspace)

    def submit(self, fn, *args, **kwargs):
        """ Internal """
        if not self.is_shutdown:
            return self.cluster.executor.submit(fn, *args, **kwargs)

    def get_pool_state(self):
        return dict((host, pool.get_state()) for host, pool in self._pools.items())


class _ControlReconnectionHandler(_ReconnectionHandler):
    """
    Internal
    """

    def __init__(self, control_connection, *args, **kwargs):
        _ReconnectionHandler.__init__(self, *args, **kwargs)
        self.control_connection = weakref.proxy(control_connection)

    def try_reconnect(self):
        # we'll either get back a new Connection or a NoHostAvailable
        return self.control_connection._reconnect_internal()

    def on_reconnection(self, connection):
        self.control_connection._set_new_connection(connection)

    def on_exception(self, exc, next_delay):
        # TODO only overridden to add logging, so add logging
        if isinstance(exc, AuthenticationFailed):
            return False
        else:
            log.debug("Error trying to reconnect control connection: %r", exc)
            return True


def _watch_callback(obj_weakref, method_name, *args, **kwargs):
    """
    A callback handler for the ControlConnection that tolerates
    weak references.
    """
    obj = obj_weakref()
    if obj is None:
        return
    getattr(obj, method_name)(*args, **kwargs)


def _clear_watcher(conn, expiring_weakref):
    """
    Called when the ControlConnection object is about to be finalized.
    This clears watchers on the underlying Connection object.
    """
    try:
        conn.control_conn_disposed()
    except ReferenceError:
        pass


class ControlConnection(object):
    """
    Internal
    """

    _SELECT_KEYSPACES = "SELECT * FROM system.schema_keyspaces"
    _SELECT_COLUMN_FAMILIES = "SELECT * FROM system.schema_columnfamilies"
    _SELECT_COLUMNS = "SELECT * FROM system.schema_columns"

    _SELECT_PEERS = "SELECT peer, data_center, rack, tokens, rpc_address, schema_version FROM system.peers"
    _SELECT_LOCAL = "SELECT cluster_name, data_center, rack, tokens, partitioner, schema_version FROM system.local WHERE key='local'"

    _SELECT_SCHEMA_PEERS = "SELECT rpc_address, schema_version FROM system.peers"
    _SELECT_SCHEMA_LOCAL = "SELECT schema_version FROM system.local WHERE key='local'"

    _is_shutdown = False
    _timeout = None

    # for testing purposes
    _time = time

    def __init__(self, cluster, timeout):
        # use a weak reference to allow the Cluster instance to be GC'ed (and
        # shutdown) since implementing __del__ disables the cycle detector
        self._cluster = weakref.proxy(cluster)
        self._connection = None
        self._timeout = timeout

        self._lock = RLock()
        self._schema_agreement_lock = Lock()

        self._reconnection_handler = None
        self._reconnection_lock = RLock()

    def connect(self):
        if self._is_shutdown:
            return

        self._set_new_connection(self._reconnect_internal())

    def _set_new_connection(self, conn):
        """
        Replace existing connection (if there is one) and close it.
        """
        with self._lock:
            old = self._connection
            self._connection = conn

        if old:
            log.debug("[control connection] Closing old connection %r, replacing with %r", old, conn)
            old.close()

    def _reconnect_internal(self):
        """
        Tries to connect to each host in the query plan until one succeeds
        or every attempt fails. If successful, a new Connection will be
        returned.  Otherwise, :exc:`NoHostAvailable` will be raised
        with an "errors" arg that is a dict mapping host addresses
        to the exception that was raised when an attempt was made to open
        a connection to that host.
        """
        errors = {}
        for host in self._cluster.load_balancing_policy.make_query_plan():
            try:
                return self._try_connect(host)
            except ConnectionException as exc:
                errors[host.address] = exc
                log.warning("[control connection] Error connecting to %s:", host, exc_info=True)
                self._cluster.signal_connection_failure(host, exc, is_host_addition=False)
            except Exception as exc:
                errors[host.address] = exc
                log.warning("[control connection] Error connecting to %s:", host, exc_info=True)

        raise NoHostAvailable("Unable to connect to any servers", errors)

    def _try_connect(self, host):
        """
        Creates a new Connection, registers for pushed events, and refreshes
        node/token and schema metadata.
        """
        log.debug("[control connection] Opening new connection to %s", host)
        connection = self._cluster.connection_factory(host.address, is_control_connection=True)

        log.debug("[control connection] Established new connection %r, "
                  "registering watchers and refreshing schema and topology",
                  connection)

        # use weak references in both directions
        # _clear_watcher will be called when this ControlConnection is about to be finalized
        # _watch_callback will get the actual callback from the Connection and relay it to
        # this object (after a dereferencing a weakref)
        self_weakref = weakref.ref(self, callback=partial(_clear_watcher, weakref.proxy(connection)))
        try:
            connection.register_watchers({
                "TOPOLOGY_CHANGE": partial(_watch_callback, self_weakref, '_handle_topology_change'),
                "STATUS_CHANGE": partial(_watch_callback, self_weakref, '_handle_status_change'),
                "SCHEMA_CHANGE": partial(_watch_callback, self_weakref, '_handle_schema_change')
            }, register_timeout=self._timeout)

            peers_query = QueryMessage(query=self._SELECT_PEERS, consistency_level=ConsistencyLevel.ONE)
            local_query = QueryMessage(query=self._SELECT_LOCAL, consistency_level=ConsistencyLevel.ONE)
            shared_results = connection.wait_for_responses(
                peers_query, local_query, timeout=self._timeout)

            self._refresh_node_list_and_token_map(connection, preloaded_results=shared_results)
            self._refresh_schema(connection, preloaded_results=shared_results)
        except Exception:
            connection.close()
            raise

        return connection

    def reconnect(self):
        if self._is_shutdown:
            return

        self._submit(self._reconnect)

    def _reconnect(self):
        log.debug("[control connection] Attempting to reconnect")
        try:
            self._set_new_connection(self._reconnect_internal())
        except NoHostAvailable:
            # make a retry schedule (which includes backoff)
            schedule = self.cluster.reconnection_policy.new_schedule()

            with self._reconnection_lock:

                # cancel existing reconnection attempts
                if self._reconnection_handler:
                    self._reconnection_handler.cancel()

                # when a connection is successfully made, _set_new_connection
                # will be called with the new connection and then our
                # _reconnection_handler will be cleared out
                self._reconnection_handler = _ControlReconnectionHandler(
                    self, self._cluster.scheduler, schedule,
                    self._get_and_set_reconnection_handler,
                    new_handler=None)
                self._reconnection_handler.start()
        except Exception:
            log.debug("[control connection] error reconnecting", exc_info=True)
            raise

    def _get_and_set_reconnection_handler(self, new_handler):
        """
        Called by the _ControlReconnectionHandler when a new connection
        is successfully created.  Clears out the _reconnection_handler on
        this ControlConnection.
        """
        with self._reconnection_lock:
            old = self._reconnection_handler
            self._reconnection_handler = new_handler
            return old

    def _submit(self, *args, **kwargs):
        try:
            if not self._cluster.is_shutdown:
                return self._cluster.executor.submit(*args, **kwargs)
        except ReferenceError:
            pass
        return None

    def shutdown(self):
        with self._lock:
            if self._is_shutdown:
                return
            else:
                self._is_shutdown = True

        log.debug("Shutting down control connection")
        # stop trying to reconnect (if we are)
        if self._reconnection_handler:
            self._reconnection_handler.cancel()

        if self._connection:
            self._connection.close()
            del self._connection

    def refresh_schema(self, keyspace=None, table=None):
        try:
            if self._connection:
                self._refresh_schema(self._connection, keyspace, table)
        except ReferenceError:
            pass  # our weak reference to the Cluster is no good
        except Exception:
            log.debug("[control connection] Error refreshing schema", exc_info=True)
            self._signal_error()

    def _refresh_schema(self, connection, keyspace=None, table=None, preloaded_results=None):
        if self._cluster.is_shutdown:
            return

        agreed = self.wait_for_schema_agreement(connection, preloaded_results=preloaded_results)
        if not agreed:
            log.debug("Skipping schema refresh due to lack of schema agreement")
            return

        where_clause = ""
        if keyspace:
            where_clause = " WHERE keyspace_name = '%s'" % (keyspace,)
            if table:
                where_clause += " AND columnfamily_name = '%s'" % (table,)

        cl = ConsistencyLevel.ONE
        if table:
            ks_query = None
        else:
            ks_query = QueryMessage(query=self._SELECT_KEYSPACES + where_clause, consistency_level=cl)
        cf_query = QueryMessage(query=self._SELECT_COLUMN_FAMILIES + where_clause, consistency_level=cl)
        col_query = QueryMessage(query=self._SELECT_COLUMNS + where_clause, consistency_level=cl)

        if ks_query:
            ks_result, cf_result, col_result = connection.wait_for_responses(
                ks_query, cf_query, col_query, timeout=self._timeout)
            ks_result = dict_factory(*ks_result.results)
            cf_result = dict_factory(*cf_result.results)
            col_result = dict_factory(*col_result.results)
        else:
            ks_result = None
            cf_result, col_result = connection.wait_for_responses(
                cf_query, col_query, timeout=self._timeout)
            cf_result = dict_factory(*cf_result.results)
            col_result = dict_factory(*col_result.results)

        log.debug("[control connection] Fetched schema, rebuilding metadata")
        if table:
            self._cluster.metadata.table_changed(keyspace, table, cf_result, col_result)
        elif keyspace:
            self._cluster.metadata.keyspace_changed(keyspace, ks_result, cf_result, col_result)
        else:
            self._cluster.metadata.rebuild_schema(ks_result, cf_result, col_result)

    def refresh_node_list_and_token_map(self):
        try:
            if self._connection:
                self._refresh_node_list_and_token_map(self._connection)
        except ReferenceError:
            pass  # our weak reference to the Cluster is no good
        except Exception:
            log.debug("[control connection] Error refreshing node list and token map", exc_info=True)
            self._signal_error()

    def _refresh_node_list_and_token_map(self, connection, preloaded_results=None):
        if preloaded_results:
            log.debug("[control connection] Refreshing node list and token map using preloaded results")
            peers_result = preloaded_results[0]
            local_result = preloaded_results[1]
        else:
            log.debug("[control connection] Refreshing node list and token map")
            cl = ConsistencyLevel.ONE
            peers_query = QueryMessage(query=self._SELECT_PEERS, consistency_level=cl)
            local_query = QueryMessage(query=self._SELECT_LOCAL, consistency_level=cl)
            peers_result, local_result = connection.wait_for_responses(
                peers_query, local_query, timeout=self._timeout)

        peers_result = dict_factory(*peers_result.results)

        partitioner = None
        token_map = {}

        if local_result.results:
            local_rows = dict_factory(*(local_result.results))
            local_row = local_rows[0]
            cluster_name = local_row["cluster_name"]
            self._cluster.metadata.cluster_name = cluster_name

            host = self._cluster.metadata.get_host(connection.host)
            if host:
                datacenter = local_row.get("data_center")
                rack = local_row.get("rack")
                self._update_location_info(host, datacenter, rack)

            partitioner = local_row.get("partitioner")
            tokens = local_row.get("tokens")
            if partitioner and tokens:
                token_map[host] = tokens

        should_rebuild_token_map = False
        found_hosts = set()
        for row in peers_result:
            addr = row.get("rpc_address")

            # TODO handle ipv6 equivalent
            if not addr or addr == "0.0.0.0":
                addr = row.get("peer")

            found_hosts.add(addr)

            host = self._cluster.metadata.get_host(addr)
            datacenter = row.get("data_center")
            rack = row.get("rack")
            if host is None:
                log.debug("[control connection] Found new host to connect to: %s", addr)
                host = self._cluster.add_host(addr, datacenter, rack, signal=True)
                should_rebuild_token_map = True
            else:
                should_rebuild_token_map |= self._update_location_info(host, datacenter, rack)

            tokens = row.get("tokens")
            if partitioner and tokens:
                token_map[host] = tokens

        for old_host in self._cluster.metadata.all_hosts():
            if old_host.address != connection.host and \
                    old_host.address not in found_hosts and \
                    old_host.address not in self._cluster.contact_points:
                log.debug("[control connection] Found host that has been removed: %r", old_host)
                should_rebuild_token_map = True
                self._cluster.remove_host(old_host)

        log.debug("[control connection] Finished fetching ring info")
        if partitioner and should_rebuild_token_map:
            log.debug("[control connection] Rebuilding token map due to topology changes")
            self._cluster.metadata.rebuild_token_map(partitioner, token_map)

    def _update_location_info(self, host, datacenter, rack):
        if host.datacenter == datacenter and host.rack == rack:
            return False

        # If the dc/rack information changes, we need to update the load balancing policy.
        # For that, we remove and re-add the node against the policy. Not the most elegant, and assumes
        # that the policy will update correctly, but in practice this should work.
        self._cluster.load_balancing_policy.on_down(host)
        host.set_location_info(datacenter, rack)
        self._cluster.load_balancing_policy.on_up(host)
        return True

    def _handle_topology_change(self, event):
        change_type = event["change_type"]
        addr, port = event["address"]
        if change_type == "NEW_NODE":
            self._cluster.scheduler.schedule(10, self.refresh_node_list_and_token_map)
        elif change_type == "REMOVED_NODE":
            host = self._cluster.metadata.get_host(addr)
            self._cluster.scheduler.schedule(0, self._cluster.remove_host, host)
        elif change_type == "MOVED_NODE":
            self._cluster.scheduler.schedule(1, self.refresh_node_list_and_token_map)

    def _handle_status_change(self, event):
        change_type = event["change_type"]
        addr, port = event["address"]
        host = self._cluster.metadata.get_host(addr)
        if change_type == "UP":
            if host is None:
                # this is the first time we've seen the node
                self._cluster.scheduler.schedule(2, self.refresh_node_list_and_token_map)
            else:
                # this will be run by the scheduler
                self._cluster.scheduler.schedule(2, self._cluster.on_up, host)
        elif change_type == "DOWN":
            # Note that there is a slight risk we can receive the event late and thus
            # mark the host down even though we already had reconnected successfully.
            # But it is unlikely, and don't have too much consequence since we'll try reconnecting
            # right away, so we favor the detection to make the Host.is_up more accurate.
            if host is not None:
                # this will be run by the scheduler
                self._cluster.on_down(host, is_host_addition=False)

    def _handle_schema_change(self, event):
        keyspace = event['keyspace'] or None
        table = event['table'] or None
        if event['change_type'] in ("CREATED", "DROPPED"):
            keyspace = keyspace if table else None
            self._submit(self.refresh_schema, keyspace)
        elif event['change_type'] == "UPDATED":
            self._submit(self.refresh_schema, keyspace, table)

    def wait_for_schema_agreement(self, connection=None, preloaded_results=None):
        # Each schema change typically generates two schema refreshes, one
        # from the response type and one from the pushed notification. Holding
        # a lock is just a simple way to cut down on the number of schema queries
        # we'll make.
        with self._schema_agreement_lock:
            if self._is_shutdown:
                return

            if not connection:
                connection = self._connection

            if preloaded_results:
                log.debug("[control connection] Attempting to use preloaded results for schema agreement")

                peers_result = preloaded_results[0]
                local_result = preloaded_results[1]
                schema_mismatches = self._get_schema_mismatches(peers_result, local_result, connection.host)
                if schema_mismatches is None:
                    return True

            log.debug("[control connection] Waiting for schema agreement")
            start = self._time.time()
            elapsed = 0
            cl = ConsistencyLevel.ONE
            total_timeout = self._cluster.max_schema_agreement_wait
            schema_mismatches = None
            while elapsed < total_timeout:
                peers_query = QueryMessage(query=self._SELECT_SCHEMA_PEERS, consistency_level=cl)
                local_query = QueryMessage(query=self._SELECT_SCHEMA_LOCAL, consistency_level=cl)
                try:
                    timeout = min(2.0, total_timeout - elapsed)
                    peers_result, local_result = connection.wait_for_responses(
                        peers_query, local_query, timeout=timeout)
                except OperationTimedOut as timeout:
                    log.debug("[control connection] Timed out waiting for " \
                              "response during schema agreement check: %s", timeout)
                    elapsed = self._time.time() - start
                    continue
                except ConnectionShutdown:
                    if self._is_shutdown:
                        log.debug("[control connection] Aborting wait for schema match due to shutdown")
                        return None
                    else:
                        raise

                schema_mismatches = self._get_schema_mismatches(peers_result, local_result, connection.host)
                if schema_mismatches is None:
                    return True

                log.debug("[control connection] Schemas mismatched, trying again")
                self._time.sleep(0.2)
                elapsed = self._time.time() - start

            log.warn("Node %s is reporting a schema disagreement: %s",
                     connection.host, schema_mismatches)
            return False

    def _get_schema_mismatches(self, peers_result, local_result, local_address):
        peers_result = dict_factory(*peers_result.results)

        versions = defaultdict(set)
        if local_result.results:
            local_row = dict_factory(*local_result.results)[0]
            if local_row.get("schema_version"):
                versions[local_row.get("schema_version")].add(local_address)

        for row in peers_result:
            if not row.get("rpc_address") or not row.get("schema_version"):
                continue

            rpc = row.get("rpc_address")
            if rpc == "0.0.0.0":  # TODO ipv6 check
                rpc = row.get("peer")

            peer = self._cluster.metadata.get_host(rpc)
            if peer and peer.is_up:
                versions[row.get("schema_version")].add(rpc)

        if len(versions) == 1:
            log.debug("[control connection] Schemas match")
            return None

        return dict((version, list(nodes)) for version, nodes in six.iteritems(versions))

    def _signal_error(self):
        # try just signaling the cluster, as this will trigger a reconnect
        # as part of marking the host down
        if self._connection and self._connection.is_defunct:
            host = self._cluster.metadata.get_host(self._connection.host)
            # host may be None if it's already been removed, but that indicates
            # that errors have already been reported, so we're fine
            if host:
                self._cluster.signal_connection_failure(
                    host, self._connection.last_error, is_host_addition=False)
                return

        # if the connection is not defunct or the host already left, reconnect
        # manually
        self.reconnect()

    @property
    def is_open(self):
        conn = self._connection
        return bool(conn and conn.is_open)

    def on_up(self, host):
        pass

    def on_down(self, host):

        conn = self._connection
        if conn and conn.host == host.address and \
                self._reconnection_handler is None:
            log.debug("[control connection] Control connection host (%s) is "
                      "considered down, starting reconnection", host)
            # this will result in a task being submitted to the executor to reconnect
            self.reconnect()

    def on_add(self, host):
        self.refresh_node_list_and_token_map()

    def on_remove(self, host):
        self.refresh_node_list_and_token_map()


def _stop_scheduler(scheduler, thread):
    try:
        if not scheduler.is_shutdown:
            scheduler.shutdown()
    except ReferenceError:
        pass

    thread.join()


class _Scheduler(object):

    _scheduled = None
    _executor = None
    is_shutdown = False

    def __init__(self, executor):
        self._scheduled = Queue.PriorityQueue()
        self._executor = executor

        t = Thread(target=self.run, name="Task Scheduler")
        t.daemon = True
        t.start()

        # although this runs on a daemonized thread, we prefer to stop
        # it gracefully to avoid random errors during interpreter shutdown
        atexit.register(partial(_stop_scheduler, weakref.proxy(self), t))

    def shutdown(self):
        try:
            log.debug("Shutting down Cluster Scheduler")
        except AttributeError:
            # this can happen on interpreter shutdown
            pass
        self.is_shutdown = True
        self._scheduled.put_nowait((0, None))

    def schedule(self, delay, fn, *args, **kwargs):
        if not self.is_shutdown:
            run_at = time.time() + delay
            self._scheduled.put_nowait((run_at, (fn, args, kwargs)))
        else:
            log.debug("Ignoring scheduled function after shutdown: %r", fn)

    def run(self):
        while True:
            if self.is_shutdown:
                return

            try:
                while True:
                    run_at, task = self._scheduled.get(block=True, timeout=None)
                    if self.is_shutdown:
                        log.debug("Not executing scheduled task due to Scheduler shutdown")
                        return
                    if run_at <= time.time():
                        fn, args, kwargs = task
                        future = self._executor.submit(fn, *args, **kwargs)
                        future.add_done_callback(self._log_if_failed)
                    else:
                        self._scheduled.put_nowait((run_at, task))
                        break
            except Queue.Empty:
                pass

            time.sleep(0.1)

    def _log_if_failed(self, future):
        exc = future.exception()
        if exc:
            log.warning(
                "An internally scheduled tasked failed with an unhandled exception:",
                exc_info=exc)


def refresh_schema_and_set_result(keyspace, table, control_conn, response_future):
    try:
        control_conn._refresh_schema(response_future._connection, keyspace, table)
    except Exception:
        log.exception("Exception refreshing schema in response to schema change:")
        response_future.session.submit(control_conn.refresh_schema, keyspace, table)
    finally:
        response_future._set_final_result(None)


class ResponseFuture(object):
    """
    An asynchronous response delivery mechanism that is returned from calls
    to :meth:`.Session.execute_async()`.

    There are two ways for results to be delivered:
     - Synchronously, by calling :meth:`.result()`
     - Asynchronously, by attaching callback and errback functions via
       :meth:`.add_callback()`, :meth:`.add_errback()`, and
       :meth:`.add_callbacks()`.
    """

    query = None
    """
    The :class:`~.Statement` instance that is being executed through this
    :class:`.ResponseFuture`.
    """

    session = None
    row_factory = None
    message = None
    default_timeout = None

    _req_id = None
    _final_result = _NOT_SET
    _final_exception = None
    _query_trace = None
    _callback = None
    _errback = None
    _current_host = None
    _current_pool = None
    _connection = None
    _query_retries = 0
    _start_time = None
    _metrics = None
    _paging_state = None

    def __init__(self, session, message, query, default_timeout=None, metrics=None, prepared_statement=None):
        self.session = session
        self.row_factory = session.row_factory
        self.message = message
        self.query = query
        self.default_timeout = default_timeout
        self._metrics = metrics
        self.prepared_statement = prepared_statement
        self._callback_lock = Lock()
        if metrics is not None:
            self._start_time = time.time()
        self._make_query_plan()
        self._event = Event()
        self._errors = {}

    def _make_query_plan(self):
        # convert the list/generator/etc to an iterator so that subsequent
        # calls to send_request (which retries may do) will resume where
        # they last left off
        self.query_plan = iter(self.session._load_balancer.make_query_plan(
            self.session.keyspace, self.query))

    def send_request(self):
        """ Internal """
        # query_plan is an iterator, so this will resume where we last left
        # off if send_request() is called multiple times
        for host in self.query_plan:
            req_id = self._query(host)
            if req_id is not None:
                self._req_id = req_id
                return

        self._set_final_exception(NoHostAvailable(
            "Unable to complete the operation against any hosts", self._errors))

    def _query(self, host, message=None, cb=None):
        if message is None:
            message = self.message

        if cb is None:
            cb = self._set_result

        pool = self.session._pools.get(host)
        if not pool:
            self._errors[host] = ConnectionException("Host has been marked down or removed")
            return None
        elif pool.is_shutdown:
            self._errors[host] = ConnectionException("Pool is shutdown")
            return None

        connection = None
        try:
            # TODO get connectTimeout from cluster settings
            connection = pool.borrow_connection(timeout=2.0)
            request_id = connection.send_msg(message, cb=cb)
        except NoConnectionsAvailable as exc:
            log.debug("All connections for host %s are at capacity, moving to the next host", host)
            self._errors[host] = exc
            return None
        except Exception as exc:
            log.debug("Error querying host %s", host, exc_info=True)
            self._errors[host] = exc
            if self._metrics is not None:
                self._metrics.on_connection_error()
            if connection:
                pool.return_connection(connection)
            return None

        self._current_host = host
        self._current_pool = pool
        self._connection = connection
        return request_id

    @property
    def has_more_pages(self):
        """
        Returns :const:`True` if there are more pages left in the
        query results, :const:`False` otherwise.  This should only
        be checked after the first page has been returned.

        .. versionadded:: 2.0.0
        """
        return self._paging_state is not None

    def start_fetching_next_page(self):
        """
        If there are more pages left in the query result, this asynchronously
        starts fetching the next page.  If there are no pages left, :exc:`.QueryExhausted`
        is raised.  Also see :attr:`.has_more_pages`.

        This should only be called after the first page has been returned.

        .. versionadded:: 2.0.0
        """
        if not self._paging_state:
            raise QueryExhausted()

        self._make_query_plan()
        self.message.paging_state = self._paging_state
        self._event.clear()
        self._final_result = _NOT_SET
        self._final_exception = None
        self.send_request()

    def _reprepare(self, prepare_message):
        cb = partial(self.session.submit, self._execute_after_prepare)
        request_id = self._query(self._current_host, prepare_message, cb=cb)
        if request_id is None:
            # try to submit the original prepared statement on some other host
            self.send_request()

    def _set_result(self, response):
        try:
            if self._current_pool and self._connection:
                self._current_pool.return_connection(self._connection)

            trace_id = getattr(response, 'trace_id', None)
            if trace_id:
                self._query_trace = QueryTrace(trace_id, self.session)

            if isinstance(response, ResultMessage):
                if response.kind == RESULT_KIND_SET_KEYSPACE:
                    session = getattr(self, 'session', None)
                    # since we're running on the event loop thread, we need to
                    # use a non-blocking method for setting the keyspace on
                    # all connections in this session, otherwise the event
                    # loop thread will deadlock waiting for keyspaces to be
                    # set.  This uses a callback chain which ends with
                    # self._set_keyspace_completed() being called in the
                    # event loop thread.
                    if session:
                        session._set_keyspace_for_all_pools(
                            response.results, self._set_keyspace_completed)
                elif response.kind == RESULT_KIND_SCHEMA_CHANGE:
                    # refresh the schema before responding, but do it in another
                    # thread instead of the event loop thread
                    self.session.submit(
                        refresh_schema_and_set_result,
                        response.results['keyspace'],
                        response.results['table'],
                        self.session.cluster.control_connection,
                        self)
                else:
                    results = getattr(response, 'results', None)
                    if results is not None and response.kind == RESULT_KIND_ROWS:
                        self._paging_state = response.paging_state
                        results = self.row_factory(*results)
                    self._set_final_result(results)
            elif isinstance(response, ErrorMessage):
                retry_policy = None
                if self.query:
                    retry_policy = self.query.retry_policy
                if not retry_policy:
                    retry_policy = self.session.cluster.default_retry_policy

                if isinstance(response, ReadTimeoutErrorMessage):
                    if self._metrics is not None:
                        self._metrics.on_read_timeout()
                    retry = retry_policy.on_read_timeout(
                        self.query, retry_num=self._query_retries, **response.info)
                elif isinstance(response, WriteTimeoutErrorMessage):
                    if self._metrics is not None:
                        self._metrics.on_write_timeout()
                    retry = retry_policy.on_write_timeout(
                        self.query, retry_num=self._query_retries, **response.info)
                elif isinstance(response, UnavailableErrorMessage):
                    if self._metrics is not None:
                        self._metrics.on_unavailable()
                    retry = retry_policy.on_unavailable(
                        self.query, retry_num=self._query_retries, **response.info)
                elif isinstance(response, OverloadedErrorMessage):
                    if self._metrics is not None:
                        self._metrics.on_other_error()
                    # need to retry against a different host here
                    log.warning("Host %s is overloaded, retrying against a different "
                                "host", self._current_host)
                    self._retry(reuse_connection=False, consistency_level=None)
                    return
                elif isinstance(response, IsBootstrappingErrorMessage):
                    if self._metrics is not None:
                        self._metrics.on_other_error()
                    # need to retry against a different host here
                    self._retry(reuse_connection=False, consistency_level=None)
                    return
                elif isinstance(response, PreparedQueryNotFound):
                    if self.prepared_statement:
                        query_id = self.prepared_statement.query_id
                        assert query_id == response.info, \
                            "Got different query ID in server response (%s) than we " \
                            "had before (%s)" % (response.info, query_id)
                    else:
                        query_id = response.info

                    try:
                        prepared_statement = self.session.cluster._prepared_statements[query_id]
                    except KeyError:
                        if not self.prepared_statement:
                            log.error("Tried to execute unknown prepared statement: id=%s",
                                      query_id.encode('hex'))
                            self._set_final_exception(response)
                            return
                        else:
                            prepared_statement = self.prepared_statement
                            self.session.cluster._prepared_statements[query_id] = prepared_statement

                    current_keyspace = self._connection.keyspace
                    prepared_keyspace = prepared_statement.keyspace
                    if current_keyspace != prepared_keyspace:
                        self._set_final_exception(
                            ValueError("The Session's current keyspace (%s) does "
                                       "not match the keyspace the statement was "
                                       "prepared with (%s)" %
                                       (current_keyspace, prepared_keyspace)))
                        return

                    log.debug("Re-preparing unrecognized prepared statement against host %s: %s",
                              self._current_host, prepared_statement.query_string)
                    prepare_message = PrepareMessage(query=prepared_statement.query_string)
                    # since this might block, run on the executor to avoid hanging
                    # the event loop thread
                    self.session.submit(self._reprepare, prepare_message)
                    return
                else:
                    if hasattr(response, 'to_exception'):
                        self._set_final_exception(response.to_exception())
                    else:
                        self._set_final_exception(response)
                    return

                retry_type, consistency = retry
                if retry_type is RetryPolicy.RETRY:
                    self._query_retries += 1
                    self._retry(reuse_connection=True, consistency_level=consistency)
                elif retry_type is RetryPolicy.RETHROW:
                    self._set_final_exception(response.to_exception())
                else:  # IGNORE
                    if self._metrics is not None:
                        self._metrics.on_ignore()
                    self._set_final_result(None)
            elif isinstance(response, ConnectionException):
                if self._metrics is not None:
                    self._metrics.on_connection_error()
                if not isinstance(response, ConnectionShutdown):
                    self._connection.defunct(response)
                self._retry(reuse_connection=False, consistency_level=None)
            elif isinstance(response, Exception):
                if hasattr(response, 'to_exception'):
                    self._set_final_exception(response.to_exception())
                else:
                    self._set_final_exception(response)
            else:
                # we got some other kind of response message
                msg = "Got unexpected message: %r" % (response,)
                exc = ConnectionException(msg, self._current_host)
                self._connection.defunct(exc)
                self._set_final_exception(exc)
        except Exception as exc:
            # almost certainly caused by a bug, but we need to set something here
            log.exception("Unexpected exception while handling result in ResponseFuture:")
            self._set_final_exception(exc)

    def _set_keyspace_completed(self, errors):
        if not errors:
            self._set_final_result(None)
        else:
            self._set_final_exception(ConnectionException(
                "Failed to set keyspace on all hosts: %s" % (errors,)))

    def _execute_after_prepare(self, response):
        """
        Handle the response to our attempt to prepare a statement.
        If it succeeded, run the original query again against the same host.
        """
        if self._current_pool and self._connection:
            self._current_pool.return_connection(self._connection)

        if self._final_exception:
            return

        if isinstance(response, ResultMessage):
            if response.kind == RESULT_KIND_PREPARED:
                # use self._query to re-use the same host and
                # at the same time properly borrow the connection
                request_id = self._query(self._current_host)
                if request_id is None:
                    # this host errored out, move on to the next
                    self.send_request()
            else:
                self._set_final_exception(ConnectionException(
                    "Got unexpected response when preparing statement "
                    "on host %s: %s" % (self._current_host, response)))
        elif isinstance(response, ErrorMessage):
            self._set_final_exception(response)
        elif isinstance(response, ConnectionException):
            log.debug("Connection error when preparing statement on host %s: %s",
                      self._current_host, response)
            # try again on a different host, preparing again if necessary
            self._errors[self._current_host] = response
            self.send_request()
        else:
            self._set_final_exception(ConnectionException(
                "Got unexpected response type when preparing "
                "statement on host %s: %s" % (self._current_host, response)))

    def _set_final_result(self, response):
        if self._metrics is not None:
            self._metrics.request_timer.addValue(time.time() - self._start_time)

        with self._callback_lock:
            self._final_result = response

        self._event.set()
        if self._callback:
            fn, args, kwargs = self._callback
            fn(response, *args, **kwargs)

    def _set_final_exception(self, response):
        if self._metrics is not None:
            self._metrics.request_timer.addValue(time.time() - self._start_time)

        with self._callback_lock:
            self._final_exception = response
        self._event.set()
        if self._errback:
            fn, args, kwargs = self._errback
            fn(response, *args, **kwargs)

    def _retry(self, reuse_connection, consistency_level):
        if self._final_exception:
            # the connection probably broke while we were waiting
            # to retry the operation
            return

        if self._metrics is not None:
            self._metrics.on_retry()
        if consistency_level is not None:
            self.message.consistency_level = consistency_level

        # don't retry on the event loop thread
        self.session.submit(self._retry_task, reuse_connection)

    def _retry_task(self, reuse_connection):
        if self._final_exception:
            # the connection probably broke while we were waiting
            # to retry the operation
            return

        if reuse_connection and self._query(self._current_host):
            return

        # otherwise, move onto another host
        self.send_request()

    def result(self, timeout=_NOT_SET):
        """
        Return the final result or raise an Exception if errors were
        encountered.  If the final result or error has not been set
        yet, this method will block until that time.

        You may set a timeout (in seconds) with the `timeout` parameter.
        By default, the :attr:`~.default_timeout` for the :class:`.Session`
        this was created through will be used for the timeout on this
        operation.  If the timeout is exceeded, an
        :exc:`cassandra.OperationTimedOut` will be raised.

        Example usage::

            >>> future = session.execute_async("SELECT * FROM mycf")
            >>> # do other stuff...

            >>> try:
            ...     rows = future.result()
            ...     for row in rows:
            ...         ... # process results
            ... except Exception:
            ...     log.exception("Operation failed:")

        """
        if timeout is _NOT_SET:
            timeout = self.default_timeout

        if self._final_result is not _NOT_SET:
            if self._paging_state is None:
                return self._final_result
            else:
                return PagedResult(self, self._final_result)
        elif self._final_exception:
            raise self._final_exception
        else:
            self._event.wait(timeout=timeout)
            if self._final_result is not _NOT_SET:
                if self._paging_state is None:
                    return self._final_result
                else:
                    return PagedResult(self, self._final_result)
            elif self._final_exception:
                raise self._final_exception
            else:
                raise OperationTimedOut(errors=self._errors, last_host=self._current_host)

    def get_query_trace(self, max_wait=None):
        """
        Returns the :class:`~.query.QueryTrace` instance representing a trace
        of the last attempt for this operation, or :const:`None` if tracing was
        not enabled for this query.  Note that this may raise an exception if
        there are problems retrieving the trace details from Cassandra. If the
        trace is not available after `max_wait` seconds,
        :exc:`cassandra.query.TraceUnavailable` will be raised.
        """
        if not self._query_trace:
            return None

        self._query_trace.populate(max_wait)
        return self._query_trace

    def add_callback(self, fn, *args, **kwargs):
        """
        Attaches a callback function to be called when the final results arrive.

        By default, `fn` will be called with the results as the first and only
        argument.  If `*args` or `**kwargs` are supplied, they will be passed
        through as additional positional or keyword arguments to `fn`.

        If an error is hit while executing the operation, a callback attached
        here will not be called.  Use :meth:`.add_errback()` or :meth:`add_callbacks()`
        if you wish to handle that case.

        If the final result has already been seen when this method is called,
        the callback will be called immediately (before this method returns).

        **Important**: if the callback you attach results in an exception being
        raised, **the exception will be ignored**, so please ensure your
        callback handles all error cases that you care about.

        Usage example::

            >>> session = cluster.connect("mykeyspace")

            >>> def handle_results(rows, start_time, should_log=False):
            ...     if should_log:
            ...         log.info("Total time: %f", time.time() - start_time)
            ...     ...

            >>> future = session.execute_async("SELECT * FROM users")
            >>> future.add_callback(handle_results, time.time(), should_log=True)

        """
        run_now = False
        with self._callback_lock:
            if self._final_result is not _NOT_SET:
                run_now = True
            else:
                self._callback = (fn, args, kwargs)
        if run_now:
            fn(self._final_result, *args, **kwargs)
        return self

    def add_errback(self, fn, *args, **kwargs):
        """
        Like :meth:`.add_callback()`, but handles error cases.
        An Exception instance will be passed as the first positional argument
        to `fn`.
        """
        run_now = False
        with self._callback_lock:
            if self._final_exception:
                run_now = True
            else:
                self._errback = (fn, args, kwargs)
        if run_now:
            fn(self._final_exception, *args, **kwargs)
        return self

    def add_callbacks(self, callback, errback,
                      callback_args=(), callback_kwargs=None,
                      errback_args=(), errback_kwargs=None):
        """
        A convenient combination of :meth:`.add_callback()` and
        :meth:`.add_errback()`.

        Example usage::

            >>> session = cluster.connect()
            >>> query = "SELECT * FROM mycf"
            >>> future = session.execute_async(query)

            >>> def log_results(results, level='debug'):
            ...     for row in results:
            ...         log.log(level, "Result: %s", row)

            >>> def log_error(exc, query):
            ...     log.error("Query '%s' failed: %s", query, exc)

            >>> future.add_callbacks(
            ...     callback=log_results, callback_kwargs={'level': 'info'},
            ...     errback=log_error, errback_args=(query,))

        """
        self.add_callback(callback, *callback_args, **(callback_kwargs or {}))
        self.add_errback(errback, *errback_args, **(errback_kwargs or {}))

    def __str__(self):
        result = "(no result yet)" if self._final_result is _NOT_SET else self._final_result
        return "<ResponseFuture: query='%s' request_id=%s result=%s exception=%s host=%s>" \
               % (self.query, self._req_id, result, self._final_exception, self._current_host)
    __repr__ = __str__


class QueryExhausted(Exception):
    """
    Raised when :meth:`.ResponseFuture.start_fetching_next_page()` is called and
    there are no more pages.  You can check :attr:`.ResponseFuture.has_more_pages`
    before calling to avoid this.

    .. versionadded:: 2.0.0
    """
    pass


class PagedResult(object):
    """
    An iterator over the rows from a paged query result.  Whenever the number
    of result rows for a query exceed the :attr:`~.query.Statement.fetch_size`
    (or :attr:`~.Session.default_fetch_size`, if not set) an instance of this
    class will be returned.

    You can treat this as a normal iterator over rows::

        >>> from cassandra.query import SimpleStatement
        >>> statement = SimpleStatement("SELECT * FROM users", fetch_size=10)
        >>> for user_row in session.execute(statement):
        ...     process_user(user_row)

    Whenever there are no more rows in the current page, the next page will
    be fetched transparently.  However, note that it *is* possible for
    an :class:`Exception` to be raised while fetching the next page, just
    like you might see on a normal call to ``session.execute()``.

    .. versionadded: 2.0.0
    """

    def __init__(self, response_future, initial_response):
        self.response_future = response_future
        self.current_response = iter(initial_response)

    def __iter__(self):
        return self

    def next(self):
        try:
            return next(self.current_response)
        except StopIteration:
            if self.response_future._paging_state is None:
                raise

        self.response_future.start_fetching_next_page()
        result = self.response_future.result()
        if self.response_future.has_more_pages:
            self.current_response = result.current_response
        else:
            self.current_response = iter(result)

        return next(self.current_response)

    __next__ = next

########NEW FILE########
__FILENAME__ = concurrent
# Copyright 2013-2014 DataStax, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import six
import sys

from itertools import count, cycle
from six.moves import xrange
from threading import Event


def execute_concurrent(session, statements_and_parameters, concurrency=100, raise_on_first_error=True):
    """
    Executes a sequence of (statement, parameters) tuples concurrently.  Each
    ``parameters`` item must be a sequence or :const:`None`.

    A sequence of ``(success, result_or_exc)`` tuples is returned in the same
    order that the statements were passed in.  If ``success`` if :const:`False`,
    there was an error executing the statement, and ``result_or_exc`` will be
    an :class:`Exception`.  If ``success`` is :const:`True`, ``result_or_exc``
    will be the query result.

    If `raise_on_first_error` is left as :const:`True`, execution will stop
    after the first failed statement and the corresponding exception will be
    raised.

    The `concurrency` parameter controls how many statements will be executed
    concurrently.  It is recommended that this be kept below the number of
    core connections per host times the number of connected hosts (see
    :meth:`.Cluster.set_core_connections_per_host`).  If that amount is exceeded,
    the event loop thread may attempt to block on new connection creation,
    substantially impacting throughput.

    Example usage::

        select_statement = session.prepare("SELECT * FROM users WHERE id=?")

        statements_and_params = []
        for user_id in user_ids:
            params = (user_id, )
            statatements_and_params.append((select_statement, params))

        results = execute_concurrent(
            session, statements_and_params, raise_on_first_error=False)

        for (success, result) in results:
            if not success:
                handle_error(result)  # result will be an Exception
            else:
                process_user(result[0])  # result will be a list of rows

    """
    if concurrency <= 0:
        raise ValueError("concurrency must be greater than 0")

    if not statements_and_parameters:
        return []

    # TODO handle iterators and generators naturally without converting the
    # whole thing to a list.  This would requires not building a result
    # list of Nones up front (we don't know how many results there will be),
    # so a dict keyed by index should be used instead.  The tricky part is
    # knowing when you're the final statement to finish.
    statements_and_parameters = list(statements_and_parameters)

    event = Event()
    first_error = [] if raise_on_first_error else None
    to_execute = len(statements_and_parameters)
    results = [None] * to_execute
    num_finished = count(start=1)
    statements = enumerate(iter(statements_and_parameters))
    for i in xrange(min(concurrency, len(statements_and_parameters))):
        _execute_next(_sentinel, i, event, session, statements, results, num_finished, to_execute, first_error)

    event.wait()
    if first_error:
        exc = first_error[0]
        if six.PY2 and isinstance(exc, tuple):
            (exc_type, value, traceback) = exc
            six.reraise(exc_type, value, traceback)
        else:
            raise exc
    else:
        return results


def execute_concurrent_with_args(session, statement, parameters, *args, **kwargs):
    """
    Like :meth:`~cassandra.concurrent.execute_concurrent()`, but takes a single
    statement and a sequence of parameters.  Each item in ``parameters``
    should be a sequence or :const:`None`.

    Example usage::

        statement = session.prepare("INSERT INTO mytable (a, b) VALUES (1, ?)")
        parameters = [(x,) for x in range(1000)]
        execute_concurrent_with_args(session, statement, parameters)
    """
    return execute_concurrent(session, list(zip(cycle((statement,)), parameters)), *args, **kwargs)


_sentinel = object()


def _handle_error(error, result_index, event, session, statements, results, num_finished, to_execute, first_error):
    if first_error is not None:
        first_error.append(error)
        event.set()
        return
    else:
        results[result_index] = (False, error)
        if next(num_finished) >= to_execute:
            event.set()
            return

    try:
        (next_index, (statement, params)) = next(statements)
    except StopIteration:
        return

    args = (next_index, event, session, statements, results, num_finished, to_execute, first_error)
    try:
        session.execute_async(statement, params).add_callbacks(
            callback=_execute_next, callback_args=args,
            errback=_handle_error, errback_args=args)
    except Exception as exc:
        if first_error is not None:
            if six.PY2:
                first_error.append(sys.exc_info())
            else:
                first_error.append(exc)
            event.set()
            return
        else:
            results[next_index] = (False, exc)
            if next(num_finished) >= to_execute:
                event.set()
                return


def _execute_next(result, result_index, event, session, statements, results, num_finished, to_execute, first_error):
    if result is not _sentinel:
        results[result_index] = (True, result)
        finished = next(num_finished)
        if finished >= to_execute:
            event.set()
            return

    try:
        (next_index, (statement, params)) = next(statements)
    except StopIteration:
        return

    args = (next_index, event, session, statements, results, num_finished, to_execute, first_error)
    try:
        session.execute_async(statement, params).add_callbacks(
            callback=_execute_next, callback_args=args,
            errback=_handle_error, errback_args=args)
    except Exception as exc:
        if first_error is not None:
            if six.PY2:
                first_error.append(sys.exc_info())
            else:
                first_error.append(exc)
            event.set()
            return
        else:
            results[next_index] = (False, exc)
            if next(num_finished) >= to_execute:
                event.set()
                return

########NEW FILE########
__FILENAME__ = connection
# Copyright 2013-2014 DataStax, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from collections import defaultdict
import errno
from functools import wraps, partial
import logging
import sys
from threading import Event, RLock
import time

if 'gevent.monkey' in sys.modules:
    from gevent.queue import Queue, Empty
else:
    from six.moves.queue import Queue, Empty  # noqa

import six
from six.moves import range

from cassandra import ConsistencyLevel, AuthenticationFailed, OperationTimedOut
from cassandra.marshal import int32_pack, header_unpack
from cassandra.protocol import (ReadyMessage, AuthenticateMessage, OptionsMessage,
                                StartupMessage, ErrorMessage, CredentialsMessage,
                                QueryMessage, ResultMessage, decode_response,
                                InvalidRequestException, SupportedMessage,
                                AuthResponseMessage, AuthChallengeMessage,
                                AuthSuccessMessage)
from cassandra.util import OrderedDict


log = logging.getLogger(__name__)

# We use an ordered dictionary and specifically add lz4 before
# snappy so that lz4 will be preferred. Changing the order of this
# will change the compression preferences for the driver.
locally_supported_compressions = OrderedDict()

try:
    import lz4
except ImportError:
    pass
else:

    # Cassandra writes the uncompressed message length in big endian order,
    # but the lz4 lib requires little endian order, so we wrap these
    # functions to handle that

    def lz4_compress(byts):
        # write length in big-endian instead of little-endian
        return int32_pack(len(byts)) + lz4.compress(byts)[4:]

    def lz4_decompress(byts):
        # flip from big-endian to little-endian
        return lz4.decompress(byts[3::-1] + byts[4:])

    locally_supported_compressions['lz4'] = (lz4_compress, lz4_decompress)

try:
    import snappy
except ImportError:
    pass
else:
    # work around apparently buggy snappy decompress
    def decompress(byts):
        if byts == '\x00':
            return ''
        return snappy.decompress(byts)
    locally_supported_compressions['snappy'] = (snappy.compress, decompress)


MAX_STREAM_PER_CONNECTION = 127

PROTOCOL_VERSION_MASK = 0x7f

HEADER_DIRECTION_FROM_CLIENT = 0x00
HEADER_DIRECTION_TO_CLIENT = 0x80
HEADER_DIRECTION_MASK = 0x80

NONBLOCKING = (errno.EAGAIN, errno.EWOULDBLOCK)


class ConnectionException(Exception):
    """
    An unrecoverable error was hit when attempting to use a connection,
    or the connection was already closed or defunct.
    """

    def __init__(self, message, host=None):
        Exception.__init__(self, message)
        self.host = host


class ConnectionShutdown(ConnectionException):
    """
    Raised when a connection has been marked as defunct or has been closed.
    """
    pass


class ConnectionBusy(Exception):
    """
    An attempt was made to send a message through a :class:`.Connection` that
    was already at the max number of in-flight operations.
    """
    pass


class ProtocolError(Exception):
    """
    Communication did not match the protocol that this driver expects.
    """
    pass


def defunct_on_error(f):

    @wraps(f)
    def wrapper(self, *args, **kwargs):
        try:
            return f(self, *args, **kwargs)
        except Exception as exc:
            self.defunct(exc)
    return wrapper


DEFAULT_CQL_VERSION = '3.0.0'


class Connection(object):

    in_buffer_size = 4096
    out_buffer_size = 4096

    cql_version = None
    protocol_version = 2

    keyspace = None
    compression = True
    compressor = None
    decompressor = None

    ssl_options = None
    last_error = None
    in_flight = 0
    is_defunct = False
    is_closed = False
    lock = None

    is_control_connection = False

    def __init__(self, host='127.0.0.1', port=9042, authenticator=None,
                 ssl_options=None, sockopts=None, compression=True,
                 cql_version=None, protocol_version=2, is_control_connection=False):
        self.host = host
        self.port = port
        self.authenticator = authenticator
        self.ssl_options = ssl_options
        self.sockopts = sockopts
        self.compression = compression
        self.cql_version = cql_version
        self.protocol_version = protocol_version
        self.is_control_connection = is_control_connection
        self._push_watchers = defaultdict(set)

        self._id_queue = Queue(MAX_STREAM_PER_CONNECTION)
        for i in range(MAX_STREAM_PER_CONNECTION):
            self._id_queue.put_nowait(i)

        self.lock = RLock()

    def close(self):
        raise NotImplementedError()

    def defunct(self, exc):
        with self.lock:
            if self.is_defunct or self.is_closed:
                return
            self.is_defunct = True

        log.debug("Defuncting connection (%s) to %s:",
                  id(self), self.host, exc_info=exc)

        self.last_error = exc
        self.close()
        self.error_all_callbacks(exc)
        self.connected_event.set()
        return exc

    def error_all_callbacks(self, exc):
        with self.lock:
            callbacks = self._callbacks
            self._callbacks = {}
        new_exc = ConnectionShutdown(str(exc))
        for cb in callbacks.values():
            try:
                cb(new_exc)
            except Exception:
                log.warning("Ignoring unhandled exception while erroring callbacks for a "
                            "failed connection (%s) to host %s:",
                            id(self), self.host, exc_info=True)

    def handle_pushed(self, response):
        log.debug("Message pushed from server: %r", response)
        for cb in self._push_watchers.get(response.event_type, []):
            try:
                cb(response.event_args)
            except Exception:
                log.exception("Pushed event handler errored, ignoring:")

    def send_msg(self, msg, cb, wait_for_id=False):
        if self.is_defunct:
            raise ConnectionShutdown("Connection to %s is defunct" % self.host)
        elif self.is_closed:
            raise ConnectionShutdown("Connection to %s is closed" % self.host)

        if not wait_for_id:
            try:
                request_id = self._id_queue.get_nowait()
            except Empty:
                raise ConnectionBusy(
                    "Connection to %s is at the max number of requests" % self.host)
        else:
            request_id = self._id_queue.get()

        self._callbacks[request_id] = cb
        self.push(msg.to_binary(request_id, self.protocol_version, compression=self.compressor))
        return request_id

    def wait_for_response(self, msg, timeout=None):
        return self.wait_for_responses(msg, timeout=timeout)[0]

    def wait_for_responses(self, *msgs, **kwargs):
        if self.is_closed or self.is_defunct:
            raise ConnectionShutdown("Connection %s is already closed" % (self, ))
        timeout = kwargs.get('timeout')
        waiter = ResponseWaiter(self, len(msgs))

        # busy wait for sufficient space on the connection
        messages_sent = 0
        while True:
            needed = len(msgs) - messages_sent
            with self.lock:
                available = min(needed, MAX_STREAM_PER_CONNECTION - self.in_flight)
                self.in_flight += available

            for i in range(messages_sent, messages_sent + available):
                self.send_msg(msgs[i], partial(waiter.got_response, index=i), wait_for_id=True)
            messages_sent += available

            if messages_sent == len(msgs):
                break
            else:
                if timeout is not None:
                    timeout -= 0.01
                    if timeout <= 0.0:
                        raise OperationTimedOut()
                time.sleep(0.01)

        try:
            return waiter.deliver(timeout)
        except OperationTimedOut:
            raise
        except Exception as exc:
            self.defunct(exc)
            raise

    def register_watcher(self, event_type, callback):
        raise NotImplementedError()

    def register_watchers(self, type_callback_dict):
        raise NotImplementedError()

    def control_conn_disposed(self):
        self.is_control_connection = False
        self._push_watchers = {}

    @defunct_on_error
    def process_msg(self, msg, body_len):
        version, flags, stream_id, opcode = header_unpack(msg[:4])
        if stream_id < 0:
            callback = None
        else:
            callback = self._callbacks.pop(stream_id, None)
            self._id_queue.put_nowait(stream_id)

        body = None
        try:
            # check that the protocol version is supported
            given_version = version & PROTOCOL_VERSION_MASK
            if given_version != self.protocol_version:
                msg = "Server protocol version (%d) does not match the specified driver protocol version (%d). " +\
                      "Consider setting Cluster.protocol_version to %d."
                raise ProtocolError(msg % (given_version, self.protocol_version, given_version))

            # check that the header direction is correct
            if version & HEADER_DIRECTION_MASK != HEADER_DIRECTION_TO_CLIENT:
                raise ProtocolError(
                    "Header direction in response is incorrect; opcode %04x, stream id %r"
                    % (opcode, stream_id))

            if body_len > 0:
                body = msg[8:]
            elif body_len == 0:
                body = six.binary_type()
            else:
                raise ProtocolError("Got negative body length: %r" % body_len)

            response = decode_response(stream_id, flags, opcode, body, self.decompressor)
        except Exception as exc:
            log.exception("Error decoding response from Cassandra. "
                          "opcode: %04x; message contents: %r", opcode, msg)
            if callback is not None:
                callback(exc)
            self.defunct(exc)
            return

        try:
            if stream_id < 0:
                self.handle_pushed(response)
            elif callback is not None:
                callback(response)
        except Exception:
            log.exception("Callback handler errored, ignoring:")

    @defunct_on_error
    def _send_options_message(self):
        if self.cql_version is None and (not self.compression or not locally_supported_compressions):
            log.debug("Not sending options message for new connection(%s) to %s "
                      "because compression is disabled and a cql version was not "
                      "specified", id(self), self.host)
            self._compressor = None
            self.cql_version = DEFAULT_CQL_VERSION
            self._send_startup_message()
        else:
            log.debug("Sending initial options message for new connection (%s) to %s", id(self), self.host)
            self.send_msg(OptionsMessage(), self._handle_options_response)

    @defunct_on_error
    def _handle_options_response(self, options_response):
        if self.is_defunct:
            return

        if not isinstance(options_response, SupportedMessage):
            if isinstance(options_response, ConnectionException):
                raise options_response
            else:
                log.error("Did not get expected SupportedMessage response; " \
                          "instead, got: %s", options_response)
                raise ConnectionException("Did not get expected SupportedMessage " \
                                          "response; instead, got: %s" \
                                          % (options_response,))

        log.debug("Received options response on new connection (%s) from %s",
                  id(self), self.host)
        supported_cql_versions = options_response.cql_versions
        remote_supported_compressions = options_response.options['COMPRESSION']

        if self.cql_version:
            if self.cql_version not in supported_cql_versions:
                raise ProtocolError(
                    "cql_version %r is not supported by remote (w/ native "
                    "protocol). Supported versions: %r"
                    % (self.cql_version, supported_cql_versions))
        else:
            self.cql_version = supported_cql_versions[0]

        self._compressor = None
        compression_type = None
        if self.compression:
            overlap = (set(locally_supported_compressions.keys()) &
                       set(remote_supported_compressions))
            if len(overlap) == 0:
                log.debug("No available compression types supported on both ends."
                          " locally supported: %r. remotely supported: %r",
                          locally_supported_compressions.keys(),
                          remote_supported_compressions)
            else:
                compression_type = None
                if isinstance(self.compression, six.string_types):
                    # the user picked a specific compression type ('snappy' or 'lz4')
                    if self.compression not in remote_supported_compressions:
                        raise ProtocolError(
                            "The requested compression type (%s) is not supported by the Cassandra server at %s"
                            % (self.compression, self.host))
                    compression_type = self.compression
                else:
                    # our locally supported compressions are ordered to prefer
                    # lz4, if available
                    for k in locally_supported_compressions.keys():
                        if k in overlap:
                            compression_type = k
                            break

                # set the decompressor here, but set the compressor only after
                # a successful Ready message
                self._compressor, self.decompressor = \
                    locally_supported_compressions[compression_type]

        self._send_startup_message(compression_type)

    @defunct_on_error
    def _send_startup_message(self, compression=None):
        opts = {}
        if compression:
            opts['COMPRESSION'] = compression
        sm = StartupMessage(cqlversion=self.cql_version, options=opts)
        self.send_msg(sm, cb=self._handle_startup_response)

    @defunct_on_error
    def _handle_startup_response(self, startup_response, did_authenticate=False):
        if self.is_defunct:
            return
        if isinstance(startup_response, ReadyMessage):
            log.debug("Got ReadyMessage on new connection (%s) from %s", id(self), self.host)
            if self._compressor:
                self.compressor = self._compressor
            self.connected_event.set()
        elif isinstance(startup_response, AuthenticateMessage):
            log.debug("Got AuthenticateMessage on new connection (%s) from %s: %s",
                      id(self), self.host, startup_response.authenticator)

            if self.authenticator is None:
                raise AuthenticationFailed('Remote end requires authentication.')

            self.authenticator_class = startup_response.authenticator

            if isinstance(self.authenticator, dict):
                log.debug("Sending credentials-based auth response on %s", self)
                cm = CredentialsMessage(creds=self.authenticator)
                callback = partial(self._handle_startup_response, did_authenticate=True)
                self.send_msg(cm, cb=callback)
            else:
                log.debug("Sending SASL-based auth response on %s", self)
                initial_response = self.authenticator.initial_response()
                initial_response = "" if initial_response is None else initial_response.encode('utf-8')
                self.send_msg(AuthResponseMessage(initial_response), self._handle_auth_response)
        elif isinstance(startup_response, ErrorMessage):
            log.debug("Received ErrorMessage on new connection (%s) from %s: %s",
                      id(self), self.host, startup_response.summary_msg())
            if did_authenticate:
                raise AuthenticationFailed(
                    "Failed to authenticate to %s: %s" %
                    (self.host, startup_response.summary_msg()))
            else:
                raise ConnectionException(
                    "Failed to initialize new connection to %s: %s"
                    % (self.host, startup_response.summary_msg()))
        elif isinstance(startup_response, ConnectionShutdown):
            log.debug("Connection to %s was closed during the startup handshake", (self.host))
            raise startup_response
        else:
            msg = "Unexpected response during Connection setup: %r"
            log.error(msg, startup_response)
            raise ProtocolError(msg % (startup_response,))

    @defunct_on_error
    def _handle_auth_response(self, auth_response):
        if self.is_defunct:
            return

        if isinstance(auth_response, AuthSuccessMessage):
            log.debug("Connection %s successfully authenticated", self)
            self.authenticator.on_authentication_success(auth_response.token)
            if self._compressor:
                self.compressor = self._compressor
            self.connected_event.set()
        elif isinstance(auth_response, AuthChallengeMessage):
            response = self.authenticator.evaluate_challenge(auth_response.challenge)
            msg = AuthResponseMessage("" if response is None else response)
            log.debug("Responding to auth challenge on %s", self)
            self.send_msg(msg, self._handle_auth_response)
        elif isinstance(auth_response, ErrorMessage):
            log.debug("Received ErrorMessage on new connection (%s) from %s: %s",
                      id(self), self.host, auth_response.summary_msg())
            raise AuthenticationFailed(
                "Failed to authenticate to %s: %s" %
                (self.host, auth_response.summary_msg()))
        elif isinstance(auth_response, ConnectionShutdown):
            log.debug("Connection to %s was closed during the authentication process", self.host)
            raise auth_response
        else:
            msg = "Unexpected response during Connection authentication to %s: %r"
            log.error(msg, self.host, auth_response)
            raise ProtocolError(msg % (self.host, auth_response))

    def set_keyspace_blocking(self, keyspace):
        if not keyspace or keyspace == self.keyspace:
            return

        query = QueryMessage(query='USE "%s"' % (keyspace,),
                             consistency_level=ConsistencyLevel.ONE)
        try:
            result = self.wait_for_response(query)
        except InvalidRequestException as ire:
            # the keyspace probably doesn't exist
            raise ire.to_exception()
        except Exception as exc:
            conn_exc = ConnectionException(
                "Problem while setting keyspace: %r" % (exc,), self.host)
            self.defunct(conn_exc)
            raise conn_exc

        if isinstance(result, ResultMessage):
            self.keyspace = keyspace
        else:
            conn_exc = ConnectionException(
                "Problem while setting keyspace: %r" % (result,), self.host)
            self.defunct(conn_exc)
            raise conn_exc

    def set_keyspace_async(self, keyspace, callback):
        """
        Use this in order to avoid deadlocking the event loop thread.
        When the operation completes, `callback` will be called with
        two arguments: this connection and an Exception if an error
        occurred, otherwise :const:`None`.
        """
        if not keyspace or keyspace == self.keyspace:
            callback(self, None)
            return

        query = QueryMessage(query='USE "%s"' % (keyspace,),
                             consistency_level=ConsistencyLevel.ONE)

        def process_result(result):
            if isinstance(result, ResultMessage):
                self.keyspace = keyspace
                callback(self, None)
            elif isinstance(result, InvalidRequestException):
                callback(self, result.to_exception())
            else:
                callback(self, self.defunct(ConnectionException(
                    "Problem while setting keyspace: %r" % (result,), self.host)))

        self.send_msg(query, process_result, wait_for_id=True)

    def __str__(self):
        status = ""
        if self.is_defunct:
            status = " (defunct)"
        elif self.is_closed:
            status = " (closed)"

        return "<%s(%r) %s:%d%s>" % (self.__class__.__name__, id(self), self.host, self.port, status)
    __repr__ = __str__


class ResponseWaiter(object):

    def __init__(self, connection, num_responses):
        self.connection = connection
        self.pending = num_responses
        self.error = None
        self.responses = [None] * num_responses
        self.event = Event()

    def got_response(self, response, index):
        with self.connection.lock:
            self.connection.in_flight -= 1
        if isinstance(response, Exception):
            self.error = response
            self.event.set()
        else:
            self.responses[index] = response
            self.pending -= 1
            if not self.pending:
                self.event.set()

    def deliver(self, timeout=None):
        self.event.wait(timeout)
        if self.error:
            raise self.error
        elif not self.event.is_set():
            raise OperationTimedOut()
        else:
            return self.responses

########NEW FILE########
__FILENAME__ = cqltypes
# Copyright 2013-2014 DataStax, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Representation of Cassandra data types. These classes should make it simple for
the library (and caller software) to deal with Cassandra-style Java class type
names and CQL type specifiers, and convert between them cleanly. Parameterized
types are fully supported in both flavors. Once you have the right Type object
for the type you want, you can use it to serialize, deserialize, or retrieve
the corresponding CQL or Cassandra type strings.
"""

# NOTE:
# If/when the need arises for interpret types from CQL string literals in
# different ways (for https://issues.apache.org/jira/browse/CASSANDRA-3799,
# for example), these classes would be a good place to tack on
# .from_cql_literal() and .as_cql_literal() classmethods (or whatever).

import calendar
from decimal import Decimal
import re
import socket
import time
from datetime import datetime
from uuid import UUID
import warnings

import six
from six.moves import range

from cassandra.marshal import (int8_pack, int8_unpack, uint16_pack, uint16_unpack,
                               int32_pack, int32_unpack, int64_pack, int64_unpack,
                               float_pack, float_unpack, double_pack, double_unpack,
                               varint_pack, varint_unpack)
from cassandra.util import OrderedDict

apache_cassandra_type_prefix = 'org.apache.cassandra.db.marshal.'

if six.PY3:
    _number_types = frozenset((int, float))
    long = int
else:
    _number_types = frozenset((int, long, float))

try:
    from blist import sortedset
except ImportError:
    warnings.warn(
        "The blist library is not available, so a normal set will "
        "be used in place of blist.sortedset for set collection values. "
        "You can find the blist library here: https://pypi.python.org/pypi/blist/")

    sortedset = set


def trim_if_startswith(s, prefix):
    if s.startswith(prefix):
        return s[len(prefix):]
    return s


def unix_time_from_uuid1(u):
    return (u.time - 0x01B21DD213814000) / 10000000.0

_casstypes = {}


class CassandraTypeType(type):
    """
    The CassandraType objects in this module will normally be used directly,
    rather than through instances of those types. They can be instantiated,
    of course, but the type information is what this driver mainly needs.

    This metaclass registers CassandraType classes in the global
    by-cassandra-typename and by-cql-typename registries, unless their class
    name starts with an underscore.
    """

    def __new__(metacls, name, bases, dct):
        dct.setdefault('cassname', name)
        cls = type.__new__(metacls, name, bases, dct)
        if not name.startswith('_'):
            _casstypes[name] = cls
        return cls


casstype_scanner = re.Scanner((
    (r'[()]', lambda s, t: t),
    (r'[a-zA-Z0-9_.:=>]+', lambda s, t: t),
    (r'[\s,]', None),
))


def lookup_casstype_simple(casstype):
    """
    Given a Cassandra type name (either fully distinguished or not), hand
    back the CassandraType class responsible for it. If a name is not
    recognized, a custom _UnrecognizedType subclass will be created for it.

    This function does not handle complex types (so no type parameters--
    nothing with parentheses). Use lookup_casstype() instead if you might need
    that.
    """
    shortname = trim_if_startswith(casstype, apache_cassandra_type_prefix)
    try:
        typeclass = _casstypes[shortname]
    except KeyError:
        typeclass = mkUnrecognizedType(casstype)
    return typeclass


def parse_casstype_args(typestring):
    tokens, remainder = casstype_scanner.scan(typestring)
    if remainder:
        raise ValueError("weird characters %r at end" % remainder)

    # use a stack of (types, names) lists
    args = [([], [])]
    for tok in tokens:
        if tok == '(':
            args.append(([], []))
        elif tok == ')':
            types, names = args.pop()
            prev_types, prev_names = args[-1]
            prev_types[-1] = prev_types[-1].apply_parameters(types, names)
        else:
            types, names = args[-1]
            if ':' in tok:
                name, tok = tok.rsplit(':', 1)
                names.append(name)
            else:
                names.append(None)

            ctype = lookup_casstype_simple(tok)
            types.append(ctype)

    # return the first (outer) type, which will have all parameters applied
    return args[0][0][0]


def lookup_casstype(casstype):
    """
    Given a Cassandra type as a string (possibly including parameters), hand
    back the CassandraType class responsible for it. If a name is not
    recognized, a custom _UnrecognizedType subclass will be created for it.

    Example:

        >>> lookup_casstype('org.apache.cassandra.db.marshal.MapType(org.apache.cassandra.db.marshal.UTF8Type,org.apache.cassandra.db.marshal.Int32Type)')
        <class 'cassandra.types.MapType(UTF8Type, Int32Type)'>

    """
    if isinstance(casstype, (CassandraType, CassandraTypeType)):
        return casstype
    try:
        return parse_casstype_args(casstype)
    except (ValueError, AssertionError, IndexError) as e:
        raise ValueError("Don't know how to parse type string %r: %s" % (casstype, e))


class EmptyValue(object):
    """ See _CassandraType.support_empty_values """

    def __str__(self):
        return "EMPTY"
    __repr__ = __str__

EMPTY = EmptyValue()


@six.add_metaclass(CassandraTypeType)
class _CassandraType(object):
    subtypes = ()
    num_subtypes = 0
    empty_binary_ok = False

    support_empty_values = False
    """
    Back in the Thrift days, empty strings were used for "null" values of
    all types, including non-string types.  For most users, an empty
    string value in an int column is the same as being null/not present,
    so the driver normally returns None in this case.  (For string-like
    types, it *will* return an empty string by default instead of None.)

    To avoid this behavior, set this to :const:`True`. Instead of returning
    None for empty string values, the EMPTY singleton (an instance
    of EmptyValue) will be returned.
    """

    def __init__(self, val):
        self.val = self.validate(val)

    def __repr__(self):
        return '<%s( %r )>' % (self.cql_parameterized_type(), self.val)

    @staticmethod
    def validate(val):
        """
        Called to transform an input value into one of a suitable type
        for this class. As an example, the BooleanType class uses this
        to convert an incoming value to True or False.
        """
        return val

    @classmethod
    def from_binary(cls, byts):
        """
        Deserialize a bytestring into a value. See the deserialize() method
        for more information. This method differs in that if None or the empty
        string is passed in, None may be returned.
        """
        if byts is None:
            return None
        elif len(byts) == 0 and not cls.empty_binary_ok:
            return EMPTY if cls.support_empty_values else None
        return cls.deserialize(byts)

    @classmethod
    def to_binary(cls, val):
        """
        Serialize a value into a bytestring. See the serialize() method for
        more information. This method differs in that if None is passed in,
        the result is the empty string.
        """
        return b'' if val is None else cls.serialize(val)

    @staticmethod
    def deserialize(byts):
        """
        Given a bytestring, deserialize into a value according to the protocol
        for this type. Note that this does not create a new instance of this
        class; it merely gives back a value that would be appropriate to go
        inside an instance of this class.
        """
        return byts

    @staticmethod
    def serialize(val):
        """
        Given a value appropriate for this class, serialize it according to the
        protocol for this type and return the corresponding bytestring.
        """
        return val

    @classmethod
    def cass_parameterized_type_with(cls, subtypes, full=False):
        """
        Return the name of this type as it would be expressed by Cassandra,
        optionally fully qualified. If subtypes is not None, it is expected
        to be a list of other CassandraType subclasses, and the output
        string includes the Cassandra names for those subclasses as well,
        as parameters to this one.

        Example:

            >>> LongType.cass_parameterized_type_with(())
            'LongType'
            >>> LongType.cass_parameterized_type_with((), full=True)
            'org.apache.cassandra.db.marshal.LongType'
            >>> SetType.cass_parameterized_type_with([DecimalType], full=True)
            'org.apache.cassandra.db.marshal.SetType(org.apache.cassandra.db.marshal.DecimalType)'
        """
        cname = cls.cassname
        if full and '.' not in cname:
            cname = apache_cassandra_type_prefix + cname
        if not subtypes:
            return cname
        sublist = ', '.join(styp.cass_parameterized_type(full=full) for styp in subtypes)
        return '%s(%s)' % (cname, sublist)

    @classmethod
    def apply_parameters(cls, subtypes, names=None):
        """
        Given a set of other CassandraTypes, create a new subtype of this type
        using them as parameters. This is how composite types are constructed.

            >>> MapType.apply_parameters(DateType, BooleanType)
            <class 'cassandra.types.MapType(DateType, BooleanType)'>

        `subtypes` will be a sequence of CassandraTypes.  If provided, `names`
        will be an equally long sequence of column names or Nones.
        """
        if cls.num_subtypes != 'UNKNOWN' and len(subtypes) != cls.num_subtypes:
            raise ValueError("%s types require %d subtypes (%d given)"
                             % (cls.typename, cls.num_subtypes, len(subtypes)))
        # newname = cls.cass_parameterized_type_with(subtypes).encode('utf8')
        newname = cls.cass_parameterized_type_with(subtypes)
        return type(newname, (cls,), {'subtypes': subtypes, 'cassname': cls.cassname})

    @classmethod
    def cql_parameterized_type(cls):
        """
        Return a CQL type specifier for this type. If this type has parameters,
        they are included in standard CQL <> notation.
        """
        if not cls.subtypes:
            return cls.typename
        return '%s<%s>' % (cls.typename, ', '.join(styp.cql_parameterized_type() for styp in cls.subtypes))

    @classmethod
    def cass_parameterized_type(cls, full=False):
        """
        Return a Cassandra type specifier for this type. If this type has
        parameters, they are included in the standard () notation.
        """
        return cls.cass_parameterized_type_with(cls.subtypes, full=full)


# it's initially named with a _ to avoid registering it as a real type, but
# client programs may want to use the name still for isinstance(), etc
CassandraType = _CassandraType


class _UnrecognizedType(_CassandraType):
    num_subtypes = 'UNKNOWN'


if six.PY3:
    def mkUnrecognizedType(casstypename):
        return CassandraTypeType(casstypename,
                                 (_UnrecognizedType,),
                                 {'typename': "'%s'" % casstypename})
else:
    def mkUnrecognizedType(casstypename):  # noqa
        return CassandraTypeType(casstypename.encode('utf8'),
                                 (_UnrecognizedType,),
                                 {'typename': "'%s'" % casstypename})


class BytesType(_CassandraType):
    typename = 'blob'
    empty_binary_ok = True

    @staticmethod
    def validate(val):
        return bytearray(val)

    @staticmethod
    def serialize(val):
        return six.binary_type(val)


class DecimalType(_CassandraType):
    typename = 'decimal'

    @staticmethod
    def validate(val):
        return Decimal(val)

    @staticmethod
    def deserialize(byts):
        scale = int32_unpack(byts[:4])
        unscaled = varint_unpack(byts[4:])
        return Decimal('%de%d' % (unscaled, -scale))

    @staticmethod
    def serialize(dec):
        try:
            sign, digits, exponent = dec.as_tuple()
        except AttributeError:
            raise TypeError("Non-Decimal type received for Decimal value")
        unscaled = int(''.join([str(digit) for digit in digits]))
        if sign:
            unscaled *= -1
        scale = int32_pack(-exponent)
        unscaled = varint_pack(unscaled)
        return scale + unscaled


class UUIDType(_CassandraType):
    typename = 'uuid'

    @staticmethod
    def deserialize(byts):
        return UUID(bytes=byts)

    @staticmethod
    def serialize(uuid):
        try:
            return uuid.bytes
        except AttributeError:
            raise TypeError("Got a non-UUID object for a UUID value")


class BooleanType(_CassandraType):
    typename = 'boolean'

    @staticmethod
    def validate(val):
        return bool(val)

    @staticmethod
    def deserialize(byts):
        return bool(int8_unpack(byts))

    @staticmethod
    def serialize(truth):
        return int8_pack(truth)


if six.PY2:
    class AsciiType(_CassandraType):
        typename = 'ascii'
        empty_binary_ok = True
else:
    class AsciiType(_CassandraType):
        typename = 'ascii'
        empty_binary_ok = True

        @staticmethod
        def deserialize(byts):
            return byts.decode('ascii')

        @staticmethod
        def serialize(var):
            try:
                return var.encode('ascii')
            except UnicodeDecodeError:
                return var


class FloatType(_CassandraType):
    typename = 'float'

    deserialize = staticmethod(float_unpack)
    serialize = staticmethod(float_pack)


class DoubleType(_CassandraType):
    typename = 'double'

    deserialize = staticmethod(double_unpack)
    serialize = staticmethod(double_pack)


class LongType(_CassandraType):
    typename = 'bigint'

    deserialize = staticmethod(int64_unpack)
    serialize = staticmethod(int64_pack)


class Int32Type(_CassandraType):
    typename = 'int'

    deserialize = staticmethod(int32_unpack)
    serialize = staticmethod(int32_pack)


class IntegerType(_CassandraType):
    typename = 'varint'

    deserialize = staticmethod(varint_unpack)
    serialize = staticmethod(varint_pack)


have_ipv6_packing = hasattr(socket, 'inet_ntop')


class InetAddressType(_CassandraType):
    typename = 'inet'

    # TODO: implement basic ipv6 support for Windows?
    # inet_ntop and inet_pton aren't available on Windows

    @staticmethod
    def deserialize(byts):
        if len(byts) == 16:
            if not have_ipv6_packing:
                raise Exception(
                    "IPv6 addresses cannot currently be handled on Windows")
            return socket.inet_ntop(socket.AF_INET6, byts)
        else:
            return socket.inet_ntoa(byts)

    @staticmethod
    def serialize(addr):
        if ':' in addr:
            fam = socket.AF_INET6
            if not have_ipv6_packing:
                raise Exception(
                    "IPv6 addresses cannot currently be handled on Windows")
            return socket.inet_pton(fam, addr)
        else:
            fam = socket.AF_INET
            return socket.inet_aton(addr)


class CounterColumnType(_CassandraType):
    typename = 'counter'

    deserialize = staticmethod(int64_unpack)
    serialize = staticmethod(int64_pack)


cql_time_formats = (
    '%Y-%m-%d %H:%M',
    '%Y-%m-%d %H:%M:%S',
    '%Y-%m-%dT%H:%M',
    '%Y-%m-%dT%H:%M:%S',
    '%Y-%m-%d'
)

_have_warned_about_timestamps = False


class DateType(_CassandraType):
    typename = 'timestamp'

    @classmethod
    def validate(cls, date):
        if isinstance(date, six.string_types):
            date = cls.interpret_datestring(date)
        return date

    @staticmethod
    def interpret_datestring(date):
        if date[-5] in ('+', '-'):
            offset = (int(date[-4:-2]) * 3600 + int(date[-2:]) * 60) * int(date[-5] + '1')
            date = date[:-5]
        else:
            offset = -time.timezone
        for tformat in cql_time_formats:
            try:
                tval = time.strptime(date, tformat)
            except ValueError:
                continue
            return calendar.timegm(tval) + offset
        else:
            raise ValueError("can't interpret %r as a date" % (date,))

    def my_timestamp(self):
        return self.val

    @staticmethod
    def deserialize(byts):
        return datetime.utcfromtimestamp(int64_unpack(byts) / 1000.0)

    @staticmethod
    def serialize(v):
        global _have_warned_about_timestamps
        try:
            converted = calendar.timegm(v.utctimetuple())
            converted = converted * 1e3 + getattr(v, 'microsecond', 0) / 1e3
        except AttributeError:
            # Ints and floats are valid timestamps too
            if type(v) not in _number_types:
                raise TypeError('DateType arguments must be a datetime or timestamp')

            if not _have_warned_about_timestamps:
                _have_warned_about_timestamps = True
                warnings.warn("timestamp columns in Cassandra hold a number of "
                    "milliseconds since the unix epoch.  Currently, when executing "
                    "prepared statements, this driver multiplies timestamp "
                    "values by 1000 so that the result of time.time() "
                    "can be used directly.  However, the driver cannot "
                    "match this behavior for non-prepared statements, "
                    "so the 2.0 version of the driver will no longer multiply "
                    "timestamps by 1000.  It is suggested that you simply use "
                    "datetime.datetime objects for 'timestamp' values to avoid "
                    "any ambiguity and to guarantee a smooth upgrade of the "
                    "driver.")
            converted = v * 1e3

        return int64_pack(long(converted))


class TimestampType(DateType):
    pass


class TimeUUIDType(DateType):
    typename = 'timeuuid'

    def my_timestamp(self):
        return unix_time_from_uuid1(self.val)

    @staticmethod
    def deserialize(byts):
        return UUID(bytes=byts)

    @staticmethod
    def serialize(timeuuid):
        try:
            return timeuuid.bytes
        except AttributeError:
            raise TypeError("Got a non-UUID object for a UUID value")


class UTF8Type(_CassandraType):
    typename = 'text'
    empty_binary_ok = True

    @staticmethod
    def deserialize(byts):
        return byts.decode('utf8')

    @staticmethod
    def serialize(ustr):
        try:
            return ustr.encode('utf-8')
        except UnicodeDecodeError:
            # already utf-8
            return ustr


class VarcharType(UTF8Type):
    typename = 'varchar'


class _ParameterizedType(_CassandraType):
    def __init__(self, val):
        if not self.subtypes:
            raise ValueError("%s type with no parameters can't be instantiated" % (self.typename,))
        _CassandraType.__init__(self, val)

    @classmethod
    def deserialize(cls, byts):
        if not cls.subtypes:
            raise NotImplementedError("can't deserialize unparameterized %s"
                                      % cls.typename)
        return cls.deserialize_safe(byts)

    @classmethod
    def serialize(cls, val):
        if not cls.subtypes:
            raise NotImplementedError("can't serialize unparameterized %s"
                                      % cls.typename)
        return cls.serialize_safe(val)


class _SimpleParameterizedType(_ParameterizedType):
    @classmethod
    def validate(cls, val):
        subtype, = cls.subtypes
        return cls.adapter([subtype.validate(subval) for subval in val])

    @classmethod
    def deserialize_safe(cls, byts):
        subtype, = cls.subtypes
        numelements = uint16_unpack(byts[:2])
        p = 2
        result = []
        for _ in range(numelements):
            itemlen = uint16_unpack(byts[p:p + 2])
            p += 2
            item = byts[p:p + itemlen]
            p += itemlen
            result.append(subtype.from_binary(item))
        return cls.adapter(result)

    @classmethod
    def serialize_safe(cls, items):
        if isinstance(items, six.string_types):
            raise TypeError("Received a string for a type that expects a sequence")

        subtype, = cls.subtypes
        buf = six.BytesIO()
        buf.write(uint16_pack(len(items)))
        for item in items:
            itembytes = subtype.to_binary(item)
            buf.write(uint16_pack(len(itembytes)))
            buf.write(itembytes)
        return buf.getvalue()


class ListType(_SimpleParameterizedType):
    typename = 'list'
    num_subtypes = 1
    adapter = tuple


class SetType(_SimpleParameterizedType):
    typename = 'set'
    num_subtypes = 1
    adapter = sortedset


class MapType(_ParameterizedType):
    typename = 'map'
    num_subtypes = 2

    @classmethod
    def validate(cls, val):
        subkeytype, subvaltype = cls.subtypes
        return dict((subkeytype.validate(k), subvaltype.validate(v)) for (k, v) in six.iteritems(val))

    @classmethod
    def deserialize_safe(cls, byts):
        subkeytype, subvaltype = cls.subtypes
        numelements = uint16_unpack(byts[:2])
        p = 2
        themap = OrderedDict()
        for _ in range(numelements):
            key_len = uint16_unpack(byts[p:p + 2])
            p += 2
            keybytes = byts[p:p + key_len]
            p += key_len
            val_len = uint16_unpack(byts[p:p + 2])
            p += 2
            valbytes = byts[p:p + val_len]
            p += val_len
            key = subkeytype.from_binary(keybytes)
            val = subvaltype.from_binary(valbytes)
            themap[key] = val
        return themap

    @classmethod
    def serialize_safe(cls, themap):
        subkeytype, subvaltype = cls.subtypes
        buf = six.BytesIO()
        buf.write(uint16_pack(len(themap)))
        try:
            items = six.iteritems(themap)
        except AttributeError:
            raise TypeError("Got a non-map object for a map value")
        for key, val in items:
            keybytes = subkeytype.to_binary(key)
            valbytes = subvaltype.to_binary(val)
            buf.write(uint16_pack(len(keybytes)))
            buf.write(keybytes)
            buf.write(uint16_pack(len(valbytes)))
            buf.write(valbytes)
        return buf.getvalue()


class CompositeType(_ParameterizedType):
    typename = "'org.apache.cassandra.db.marshal.CompositeType'"
    num_subtypes = 'UNKNOWN'


class DynamicCompositeType(_ParameterizedType):
    typename = "'org.apache.cassandra.db.marshal.DynamicCompositeType'"
    num_subtypes = 'UNKNOWN'


class ColumnToCollectionType(_ParameterizedType):
    """
    This class only really exists so that we can cleanly evaluate types when
    Cassandra includes this. We don't actually need or want the extra
    information.
    """
    typename = "'org.apache.cassandra.db.marshal.ColumnToCollectionType'"
    num_subtypes = 'UNKNOWN'


class ReversedType(_ParameterizedType):
    typename = "'org.apache.cassandra.db.marshal.ReversedType'"
    num_subtypes = 1

    @classmethod
    def deserialize_safe(cls, byts):
        subtype, = cls.subtypes
        return subtype.from_binary(byts)

    @classmethod
    def serialize_safe(cls, val):
        subtype, = cls.subtypes
        return subtype.to_binary(val)


def is_counter_type(t):
    if isinstance(t, six.string_types):
        t = lookup_casstype(t)
    return issubclass(t, CounterColumnType)


def cql_typename(casstypename):
    """
    Translate a Cassandra-style type specifier (optionally-fully-distinguished
    Java class names for data types, along with optional parameters) into a
    CQL-style type specifier.

        >>> cql_typename('DateType')
        'timestamp'
        >>> cql_typename('org.apache.cassandra.db.marshal.ListType(IntegerType)')
        'list<varint>'
    """
    return lookup_casstype(casstypename).cql_parameterized_type()

########NEW FILE########
__FILENAME__ = decoder
# Copyright 2013-2014 DataStax, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from functools import wraps
import warnings

import cassandra.query

import logging
log = logging.getLogger(__name__)

_have_warned = False


def warn_once(f):

    @wraps(f)
    def new_f(*args, **kwargs):
        global _have_warned
        if not _have_warned:
            msg = "cassandra.decoder.%s has moved to cassandra.query.%s" % (f.__name__, f.__name__)
            warnings.warn(msg, DeprecationWarning)
            log.warning(msg)
            _have_warned = True
        return f(*args, **kwargs)

    return new_f

tuple_factory = warn_once(cassandra.query.tuple_factory)
"""
Deprecated: use :meth:`cassandra.query.tuple_factory()`
"""

named_tuple_factory = warn_once(cassandra.query.named_tuple_factory)
"""
Deprecated: use :meth:`cassandra.query.named_tuple_factory()`
"""

dict_factory = warn_once(cassandra.query.dict_factory)
"""
Deprecated: use :meth:`cassandra.query.dict_factory()`
"""

ordered_dict_factory = warn_once(cassandra.query.ordered_dict_factory)
"""
Deprecated: use :meth:`cassandra.query.ordered_dict_factory()`
"""

########NEW FILE########
__FILENAME__ = encoder
# Copyright 2013-2014 DataStax, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import logging
log = logging.getLogger(__name__)

from binascii import hexlify
import calendar
import datetime
import sys
import types
from uuid import UUID
import six

from cassandra.util import OrderedDict

if six.PY3:
    long = int


def cql_quote(term):
    # The ordering of this method is important for the result of this method to
    # be a native str type (for both Python 2 and 3)

    # Handle quoting of native str and bool types
    if isinstance(term, (str, bool)):
        return "'%s'" % str(term).replace("'", "''")
    # This branch of the if statement will only be used by Python 2 to catch
    # unicode strings, text_type is used to prevent type errors with Python 3.
    elif isinstance(term, six.text_type):
        return "'%s'" % term.encode('utf8').replace("'", "''")
    else:
        return str(term)


def cql_encode_none(val):
    return 'NULL'


def cql_encode_unicode(val):
    return cql_quote(val.encode('utf-8'))


def cql_encode_str(val):
    return cql_quote(val)


if six.PY3:
    def cql_encode_bytes(val):
        return (b'0x' + hexlify(val)).decode('utf-8')
elif sys.version_info >= (2, 7):
    def cql_encode_bytes(val):  # noqa
        return b'0x' + hexlify(val)
else:
    # python 2.6 requires string or read-only buffer for hexlify
    def cql_encode_bytes(val):  # noqa
        return b'0x' + hexlify(buffer(val))


def cql_encode_object(val):
    return str(val)


def cql_encode_datetime(val):
    timestamp = calendar.timegm(val.utctimetuple())
    return str(long(timestamp * 1e3 + getattr(val, 'microsecond', 0) / 1e3))


def cql_encode_date(val):
    return "'%s'" % val.strftime('%Y-%m-%d-0000')


def cql_encode_sequence(val):
    return '( %s )' % ' , '.join(cql_encoders.get(type(v), cql_encode_object)(v)
                                 for v in val)


def cql_encode_map_collection(val):
    return '{ %s }' % ' , '.join('%s : %s' % (
        cql_encode_all_types(k),
        cql_encode_all_types(v)
    ) for k, v in six.iteritems(val))


def cql_encode_list_collection(val):
    return '[ %s ]' % ' , '.join(map(cql_encode_all_types, val))


def cql_encode_set_collection(val):
    return '{ %s }' % ' , '.join(map(cql_encode_all_types, val))


def cql_encode_all_types(val):
    return cql_encoders.get(type(val), cql_encode_object)(val)


cql_encoders = {
    float: cql_encode_object,
    bytearray: cql_encode_bytes,
    str: cql_encode_str,
    int: cql_encode_object,
    UUID: cql_encode_object,
    datetime.datetime: cql_encode_datetime,
    datetime.date: cql_encode_date,
    dict: cql_encode_map_collection,
    OrderedDict: cql_encode_map_collection,
    list: cql_encode_list_collection,
    tuple: cql_encode_list_collection,
    set: cql_encode_set_collection,
    frozenset: cql_encode_set_collection,
    types.GeneratorType: cql_encode_list_collection
}

if six.PY2:
    cql_encoders.update({
        unicode: cql_encode_unicode,
        buffer: cql_encode_bytes,
        long: cql_encode_object,
        types.NoneType: cql_encode_none,
    })
else:
    cql_encoders.update({
        memoryview: cql_encode_bytes,
        bytes: cql_encode_bytes,
        type(None): cql_encode_none,
    })

# sortedset is optional
try:
    from blist import sortedset
    cql_encoders.update({
        sortedset: cql_encode_set_collection
    })
except ImportError:
    pass

########NEW FILE########
__FILENAME__ = asyncorereactor
# Copyright 2013-2014 DataStax, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import atexit
from collections import deque
from functools import partial
import logging
import os
import socket
import sys
from threading import Event, Lock, Thread

from six import BytesIO
from six.moves import range

from errno import EALREADY, EINPROGRESS, EWOULDBLOCK, EINVAL, EISCONN, errorcode
try:
    from weakref import WeakSet
except ImportError:
    from cassandra.util import WeakSet  # noqa

import asyncore

try:
    import ssl
except ImportError:
    ssl = None  # NOQA

from cassandra import OperationTimedOut
from cassandra.connection import (Connection, ConnectionShutdown,
                                  ConnectionException, NONBLOCKING)
from cassandra.protocol import RegisterMessage
from cassandra.marshal import int32_unpack

log = logging.getLogger(__name__)


class AsyncoreLoop(object):

    def __init__(self):
        self._loop_lock = Lock()
        self._started = False
        self._shutdown = False

        self._conns_lock = Lock()
        self._conns = WeakSet()

    def maybe_start(self):
        should_start = False
        did_acquire = False
        try:
            did_acquire = self._loop_lock.acquire(False)
            if did_acquire and not self._started:
                self._started = True
                should_start = True
        finally:
            if did_acquire:
                self._loop_lock.release()

        if should_start:
            thread = Thread(target=self._run_loop, name="cassandra_driver_event_loop")
            thread.daemon = True
            thread.start()
            atexit.register(partial(self._cleanup, thread))

    def _run_loop(self):
        log.debug("Starting asyncore event loop")
        with self._loop_lock:
            while True:
                try:
                    asyncore.loop(timeout=0.001, use_poll=True, count=1000)
                except Exception:
                    log.debug("Asyncore event loop stopped unexepectedly", exc_info=True)
                    break

                if self._shutdown:
                    break

                with self._conns_lock:
                    if len(self._conns) == 0:
                        break

            self._started = False

        log.debug("Asyncore event loop ended")

    def _cleanup(self, thread):
        self._shutdown = True
        log.debug("Waiting for event loop thread to join...")
        thread.join(timeout=1.0)
        if thread.is_alive():
            log.warning(
                "Event loop thread could not be joined, so shutdown may not be clean. "
                "Please call Cluster.shutdown() to avoid this.")

        log.debug("Event loop thread was joined")

    def connection_created(self, connection):
        with self._conns_lock:
            self._conns.add(connection)

    def connection_destroyed(self, connection):
        with self._conns_lock:
            self._conns.discard(connection)


class AsyncoreConnection(Connection, asyncore.dispatcher):
    """
    An implementation of :class:`.Connection` that uses the ``asyncore``
    module in the Python standard library for its event loop.
    """

    _loop = AsyncoreLoop()

    _total_reqd_bytes = 0
    _writable = False
    _readable = False

    @classmethod
    def factory(cls, *args, **kwargs):
        timeout = kwargs.pop('timeout', 5.0)
        conn = cls(*args, **kwargs)
        conn.connected_event.wait(timeout)
        if conn.last_error:
            raise conn.last_error
        elif not conn.connected_event.is_set():
            conn.close()
            raise OperationTimedOut("Timed out creating connection")
        else:
            return conn

    def __init__(self, *args, **kwargs):
        Connection.__init__(self, *args, **kwargs)
        asyncore.dispatcher.__init__(self)

        self.connected_event = Event()
        self._iobuf = BytesIO()

        self._callbacks = {}
        self.deque = deque()
        self.deque_lock = Lock()

        self._loop.connection_created(self)

        self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
        self.connect((self.host, self.port))
        self.add_channel()

        if self.sockopts:
            for args in self.sockopts:
                self.socket.setsockopt(*args)

        self._writable = True
        self._readable = True

        # start the event loop if needed
        self._loop.maybe_start()

    def set_socket(self, sock):
        # Overrides the same method in asyncore. We deliberately
        # do not call add_channel() in this method so that we can call
        # it later, after connect() has completed.
        self.socket = sock
        self._fileno = sock.fileno()

    def create_socket(self, family, type):
        # copied from asyncore, but with the line to set the socket in
        # non-blocking mode removed (we will do that after connecting)
        self.family_and_type = family, type
        sock = socket.socket(family, type)
        if self.ssl_options:
            if not ssl:
                raise Exception("This version of Python was not compiled with SSL support")
            sock = ssl.wrap_socket(sock, **self.ssl_options)
        self.set_socket(sock)

    def connect(self, address):
        # this is copied directly from asyncore.py, except that
        # a timeout is set before connecting
        self.connected = False
        self.connecting = True
        self.socket.settimeout(1.0)
        err = self.socket.connect_ex(address)
        if err in (EINPROGRESS, EALREADY, EWOULDBLOCK) \
        or err == EINVAL and os.name in ('nt', 'ce'):
            raise ConnectionException("Timed out connecting to %s" % (address[0]))
        if err in (0, EISCONN):
            self.addr = address
            self.socket.setblocking(0)
            self.handle_connect_event()
        else:
            raise socket.error(err, errorcode[err])

    def close(self):
        with self.lock:
            if self.is_closed:
                return
            self.is_closed = True

        log.debug("Closing connection (%s) to %s", id(self), self.host)
        self._writable = False
        self._readable = False
        asyncore.dispatcher.close(self)
        log.debug("Closed socket to %s", self.host)

        self._loop.connection_destroyed(self)

        if not self.is_defunct:
            self.error_all_callbacks(
                ConnectionShutdown("Connection to %s was closed" % self.host))
            # don't leave in-progress operations hanging
            self.connected_event.set()

    def handle_connect(self):
        self._send_options_message()

    def handle_error(self):
        self.defunct(sys.exc_info()[1])

    def handle_close(self):
        log.debug("connection (%s) to %s closed by server", id(self), self.host)
        self.close()

    def handle_write(self):
        while True:
            try:
                with self.deque_lock:
                    next_msg = self.deque.popleft()
            except IndexError:
                self._writable = False
                return

            try:
                sent = self.send(next_msg)
                self._readable = True
            except socket.error as err:
                if (err.args[0] in NONBLOCKING):
                    with self.deque_lock:
                        self.deque.appendleft(next_msg)
                else:
                    self.defunct(err)
                return
            else:
                if sent < len(next_msg):
                    with self.deque_lock:
                        self.deque.appendleft(next_msg[sent:])
                    if sent == 0:
                        return

    def handle_read(self):
        try:
            while True:
                buf = self.recv(self.in_buffer_size)
                self._iobuf.write(buf)
                if len(buf) < self.in_buffer_size:
                    break
        except socket.error as err:
            if ssl and isinstance(err, ssl.SSLError):
                if err.args[0] not in (ssl.SSL_ERROR_WANT_READ, ssl.SSL_ERROR_WANT_WRITE):
                    self.defunct(err)
                    return
            elif err.args[0] not in NONBLOCKING:
                self.defunct(err)
                return

        if self._iobuf.tell():
            while True:
                pos = self._iobuf.tell()
                if pos < 8 or (self._total_reqd_bytes > 0 and pos < self._total_reqd_bytes):
                    # we don't have a complete header yet or we
                    # already saw a header, but we don't have a
                    # complete message yet
                    break
                else:
                    # have enough for header, read body len from header
                    self._iobuf.seek(4)
                    body_len = int32_unpack(self._iobuf.read(4))

                    # seek to end to get length of current buffer
                    self._iobuf.seek(0, os.SEEK_END)
                    pos = self._iobuf.tell()

                    if pos >= body_len + 8:
                        # read message header and body
                        self._iobuf.seek(0)
                        msg = self._iobuf.read(8 + body_len)

                        # leave leftover in current buffer
                        leftover = self._iobuf.read()
                        self._iobuf = BytesIO()
                        self._iobuf.write(leftover)

                        self._total_reqd_bytes = 0
                        self.process_msg(msg, body_len)
                    else:
                        self._total_reqd_bytes = body_len + 8
                        break

            if not self._callbacks and not self.is_control_connection:
                self._readable = False

    def push(self, data):
        sabs = self.out_buffer_size
        if len(data) > sabs:
            chunks = []
            for i in range(0, len(data), sabs):
                chunks.append(data[i:i + sabs])
        else:
            chunks = [data]

        with self.deque_lock:
            self.deque.extend(chunks)

        self._writable = True

    def writable(self):
        return self._writable

    def readable(self):
        return self._readable or (self.is_control_connection and not (self.is_defunct or self.is_closed))

    def register_watcher(self, event_type, callback, register_timeout=None):
        self._push_watchers[event_type].add(callback)
        self.wait_for_response(
            RegisterMessage(event_list=[event_type]), timeout=register_timeout)

    def register_watchers(self, type_callback_dict, register_timeout=None):
        for event_type, callback in type_callback_dict.items():
            self._push_watchers[event_type].add(callback)
        self.wait_for_response(
            RegisterMessage(event_list=type_callback_dict.keys()), timeout=register_timeout)

########NEW FILE########
__FILENAME__ = geventreactor
# Copyright 2013-2014 DataStax, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import gevent
from gevent import select, socket
from gevent.event import Event
from gevent.queue import Queue

from collections import defaultdict
from functools import partial
import logging
import os

try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO  # ignore flake8 warning: # NOQA

from errno import EALREADY, EINPROGRESS, EWOULDBLOCK, EINVAL

from cassandra import OperationTimedOut
from cassandra.connection import Connection, ConnectionShutdown
from cassandra.protocol import RegisterMessage
from cassandra.marshal import int32_unpack


log = logging.getLogger(__name__)


def is_timeout(err):
    return (
        err in (EINPROGRESS, EALREADY, EWOULDBLOCK) or
        (err == EINVAL and os.name in ('nt', 'ce'))
    )


class GeventConnection(Connection):
    """
    An implementation of :class:`.Connection` that utilizes ``gevent``.
    """

    _total_reqd_bytes = 0
    _read_watcher = None
    _write_watcher = None
    _socket = None

    @classmethod
    def factory(cls, *args, **kwargs):
        timeout = kwargs.pop('timeout', 5.0)
        conn = cls(*args, **kwargs)
        conn.connected_event.wait(timeout)
        if conn.last_error:
            raise conn.last_error
        elif not conn.connected_event.is_set():
            conn.close()
            raise OperationTimedOut("Timed out creating connection")
        else:
            return conn

    def __init__(self, *args, **kwargs):
        Connection.__init__(self, *args, **kwargs)

        self.connected_event = Event()
        self._iobuf = StringIO()
        self._write_queue = Queue()

        self._callbacks = {}
        self._push_watchers = defaultdict(set)

        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._socket.settimeout(1.0)
        self._socket.connect((self.host, self.port))

        if self.sockopts:
            for args in self.sockopts:
                self._socket.setsockopt(*args)

        self._read_watcher = gevent.spawn(lambda: self.handle_read())
        self._write_watcher = gevent.spawn(lambda: self.handle_write())
        self._send_options_message()

    def close(self):
        with self.lock:
            if self.is_closed:
                return
            self.is_closed = True

        log.debug("Closing connection (%s) to %s" % (id(self), self.host))
        if self._read_watcher:
            self._read_watcher.kill(block=False)
        if self._write_watcher:
            self._write_watcher.kill(block=False)
        if self._socket:
            self._socket.close()
        log.debug("Closed socket to %s" % (self.host,))

        if not self.is_defunct:
            self.error_all_callbacks(
                ConnectionShutdown("Connection to %s was closed" % self.host))
            # don't leave in-progress operations hanging
            self.connected_event.set()

    def handle_close(self):
        log.debug("connection closed by server")
        self.close()

    def handle_write(self):
        run_select = partial(select.select, (), (self._socket,), ())
        while True:
            try:
                next_msg = self._write_queue.get()
                run_select()
            except Exception as exc:
                if not self.is_closed:
                    log.debug("Exception during write select() for %s: %s", self, exc)
                    self.defunct(exc)
                return

            try:
                self._socket.sendall(next_msg)
            except socket.error as err:
                log.debug("Exception during socket sendall for %s: %s", self, err)
                self.defunct(err)
                return  # Leave the write loop

    def handle_read(self):
        run_select = partial(select.select, (self._socket,), (), ())
        while True:
            try:
                run_select()
            except Exception as exc:
                if not self.is_closed:
                    log.debug("Exception during read select() for %s: %s", self, exc)
                    self.defunct(exc)
                return

            try:
                buf = self._socket.recv(self.in_buffer_size)
                self._iobuf.write(buf)
            except socket.error as err:
                if not is_timeout(err):
                    log.debug("Exception during socket recv for %s: %s", self, err)
                    self.defunct(err)
                    return  # leave the read loop

            if self._iobuf.tell():
                while True:
                    pos = self._iobuf.tell()
                    if pos < 8 or (self._total_reqd_bytes > 0 and pos < self._total_reqd_bytes):
                        # we don't have a complete header yet or we
                        # already saw a header, but we don't have a
                        # complete message yet
                        break
                    else:
                        # have enough for header, read body len from header
                        self._iobuf.seek(4)
                        body_len = int32_unpack(self._iobuf.read(4))

                        # seek to end to get length of current buffer
                        self._iobuf.seek(0, os.SEEK_END)
                        pos = self._iobuf.tell()

                        if pos >= body_len + 8:
                            # read message header and body
                            self._iobuf.seek(0)
                            msg = self._iobuf.read(8 + body_len)

                            # leave leftover in current buffer
                            leftover = self._iobuf.read()
                            self._iobuf = StringIO()
                            self._iobuf.write(leftover)

                            self._total_reqd_bytes = 0
                            self.process_msg(msg, body_len)
                        else:
                            self._total_reqd_bytes = body_len + 8
                            break
            else:
                log.debug("connection closed by server")
                self.close()
                return

    def push(self, data):
        chunk_size = self.out_buffer_size
        for i in xrange(0, len(data), chunk_size):
            self._write_queue.put(data[i:i + chunk_size])

    def register_watcher(self, event_type, callback, register_timeout=None):
        self._push_watchers[event_type].add(callback)
        self.wait_for_response(
            RegisterMessage(event_list=[event_type]),
            timeout=register_timeout)

    def register_watchers(self, type_callback_dict, register_timeout=None):
        for event_type, callback in type_callback_dict.items():
            self._push_watchers[event_type].add(callback)
        self.wait_for_response(
            RegisterMessage(event_list=type_callback_dict.keys()),
            timeout=register_timeout)

########NEW FILE########
__FILENAME__ = libevreactor
# Copyright 2013-2014 DataStax, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import atexit
from collections import deque
from functools import partial
import logging
import os
import socket
from threading import Event, Lock, Thread

from six import BytesIO

from cassandra import OperationTimedOut
from cassandra.connection import Connection, ConnectionShutdown, NONBLOCKING
from cassandra.protocol import RegisterMessage
from cassandra.marshal import int32_unpack
try:
    import cassandra.io.libevwrapper as libev
except ImportError:
    raise ImportError(
        "The C extension needed to use libev was not found.  This "
        "probably means that you didn't have the required build dependencies "
        "when installing the driver.  See "
        "http://datastax.github.io/python-driver/installation.html#c-extensions "
        "for instructions on installing build dependencies and building "
        "the C extension.")


try:
    import ssl
except ImportError:
    ssl = None # NOQA

log = logging.getLogger(__name__)


class LibevConnection(Connection):
    """
    An implementation of :class:`.Connection` that uses libev for its event loop.
    """
    _loop = libev.Loop()
    _loop_notifier = libev.Async(_loop)
    _loop_notifier.start()

    # prevent _loop_notifier from keeping the loop from returning
    _loop.unref()

    _loop_started = None
    _loop_lock = Lock()
    _loop_shutdown = False

    @classmethod
    def _run_loop(cls):
        while True:
            end_condition = cls._loop.start()
            # there are still active watchers, no deadlock
            with cls._loop_lock:
                if not cls._loop_shutdown and (end_condition or cls._live_conns):
                    log.debug("Restarting event loop")
                    continue
                else:
                    # all Connections have been closed, no active watchers
                    log.debug("All Connections currently closed, event loop ended")
                    cls._loop_started = False
                    break

    @classmethod
    def _maybe_start_loop(cls):
        should_start = False
        with cls._loop_lock:
            if not cls._loop_started:
                log.debug("Starting libev event loop")
                cls._loop_started = True
                should_start = True

        if should_start:
            t = Thread(target=cls._run_loop, name="event_loop")
            t.daemon = True
            t.start()
            atexit.register(partial(cls._cleanup, t))

        return should_start

    @classmethod
    def _cleanup(cls, thread):
        cls._loop_shutdown = True
        log.debug("Waiting for event loop thread to join...")
        thread.join(timeout=1.0)
        if thread.is_alive():
            log.warning(
                "Event loop thread could not be joined, so shutdown may not be clean. "
                "Please call Cluster.shutdown() to avoid this.")

        log.debug("Event loop thread was joined")

    # class-level set of all connections; only replaced with a new copy
    # while holding _conn_set_lock, never modified in place
    _live_conns = set()
    # newly created connections that need their write/read watcher started
    _new_conns = set()
    # recently closed connections that need their write/read watcher stopped
    _closed_conns = set()
    _conn_set_lock = Lock()

    _write_watcher_is_active = False

    _total_reqd_bytes = 0
    _read_watcher = None
    _write_watcher = None
    _socket = None

    @classmethod
    def factory(cls, *args, **kwargs):
        timeout = kwargs.pop('timeout', 5.0)
        conn = cls(*args, **kwargs)
        conn.connected_event.wait(timeout)
        if conn.last_error:
            raise conn.last_error
        elif not conn.connected_event.is_set():
            conn.close()
            raise OperationTimedOut("Timed out creating new connection")
        else:
            return conn

    @classmethod
    def _connection_created(cls, conn):
        with cls._conn_set_lock:
            new_live_conns = cls._live_conns.copy()
            new_live_conns.add(conn)
            cls._live_conns = new_live_conns

            new_new_conns = cls._new_conns.copy()
            new_new_conns.add(conn)
            cls._new_conns = new_new_conns

    @classmethod
    def _connection_destroyed(cls, conn):
        with cls._conn_set_lock:
            new_live_conns = cls._live_conns.copy()
            new_live_conns.discard(conn)
            cls._live_conns = new_live_conns

            new_closed_conns = cls._closed_conns.copy()
            new_closed_conns.add(conn)
            cls._closed_conns = new_closed_conns

    @classmethod
    def loop_will_run(cls, prepare):
        changed = False
        for conn in cls._live_conns:
            if not conn.deque and conn._write_watcher_is_active:
                if conn._write_watcher:
                    conn._write_watcher.stop()
                conn._write_watcher_is_active = False
                changed = True
            elif conn.deque and not conn._write_watcher_is_active:
                conn._write_watcher.start()
                conn._write_watcher_is_active = True
                changed = True

        if cls._new_conns:
            with cls._conn_set_lock:
                to_start = cls._new_conns
                cls._new_conns = set()

            for conn in to_start:
                conn._read_watcher.start()

            changed = True

        if cls._closed_conns:
            with cls._conn_set_lock:
                to_stop = cls._closed_conns
                cls._closed_conns = set()

            for conn in to_stop:
                if conn._write_watcher:
                    conn._write_watcher.stop()
                if conn._read_watcher:
                    conn._read_watcher.stop()

            changed = True

        if changed:
            cls._loop_notifier.send()

    def __init__(self, *args, **kwargs):
        Connection.__init__(self, *args, **kwargs)

        self.connected_event = Event()
        self._iobuf = BytesIO()

        self._callbacks = {}
        self.deque = deque()
        self._deque_lock = Lock()

        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        if self.ssl_options:
            if not ssl:
                raise Exception("This version of Python was not compiled with SSL support")
            self._socket = ssl.wrap_socket(self._socket, **self.ssl_options)
        self._socket.settimeout(1.0)  # TODO potentially make this value configurable
        self._socket.connect((self.host, self.port))
        self._socket.setblocking(0)

        if self.sockopts:
            for args in self.sockopts:
                self._socket.setsockopt(*args)

        with self._loop_lock:
            self._read_watcher = libev.IO(self._socket.fileno(), libev.EV_READ, self._loop, self.handle_read)
            self._write_watcher = libev.IO(self._socket.fileno(), libev.EV_WRITE, self._loop, self.handle_write)

        self._send_options_message()

        self.__class__._connection_created(self)

        # start the global event loop if needed
        self._maybe_start_loop()
        self._loop_notifier.send()

    def close(self):
        with self.lock:
            if self.is_closed:
                return
            self.is_closed = True

        log.debug("Closing connection (%s) to %s", id(self), self.host)
        self.__class__._connection_destroyed(self)
        self._loop_notifier.send()
        self._socket.close()

        # don't leave in-progress operations hanging
        if not self.is_defunct:
            self.error_all_callbacks(
                ConnectionShutdown("Connection to %s was closed" % self.host))

    def handle_write(self, watcher, revents, errno=None):
        if revents & libev.EV_ERROR:
            if errno:
                exc = IOError(errno, os.strerror(errno))
            else:
                exc = Exception("libev reported an error")

            self.defunct(exc)
            return

        while True:
            try:
                with self._deque_lock:
                    next_msg = self.deque.popleft()
            except IndexError:
                return

            try:
                sent = self._socket.send(next_msg)
            except socket.error as err:
                if (err.args[0] in NONBLOCKING):
                    with self._deque_lock:
                        self.deque.appendleft(next_msg)
                else:
                    self.defunct(err)
                return
            else:
                if sent < len(next_msg):
                    with self._deque_lock:
                        self.deque.appendleft(next_msg[sent:])

    def handle_read(self, watcher, revents, errno=None):
        if revents & libev.EV_ERROR:
            if errno:
                exc = IOError(errno, os.strerror(errno))
            else:
                exc = Exception("libev reported an error")

            self.defunct(exc)
            return
        try:
            while True:
                buf = self._socket.recv(self.in_buffer_size)
                self._iobuf.write(buf)
                if len(buf) < self.in_buffer_size:
                    break
        except socket.error as err:
            if ssl and isinstance(err, ssl.SSLError):
                if err.args[0] not in (ssl.SSL_ERROR_WANT_READ, ssl.SSL_ERROR_WANT_WRITE):
                    self.defunct(err)
                    return
            elif err.args[0] not in NONBLOCKING:
                self.defunct(err)
                return

        if self._iobuf.tell():
            while True:
                pos = self._iobuf.tell()
                if pos < 8 or (self._total_reqd_bytes > 0 and pos < self._total_reqd_bytes):
                    # we don't have a complete header yet or we
                    # already saw a header, but we don't have a
                    # complete message yet
                    break
                else:
                    # have enough for header, read body len from header
                    self._iobuf.seek(4)
                    body_len = int32_unpack(self._iobuf.read(4))

                    # seek to end to get length of current buffer
                    self._iobuf.seek(0, os.SEEK_END)
                    pos = self._iobuf.tell()

                    if pos >= body_len + 8:
                        # read message header and body
                        self._iobuf.seek(0)
                        msg = self._iobuf.read(8 + body_len)

                        # leave leftover in current buffer
                        leftover = self._iobuf.read()
                        self._iobuf = BytesIO()
                        self._iobuf.write(leftover)

                        self._total_reqd_bytes = 0
                        self.process_msg(msg, body_len)
                    else:
                        self._total_reqd_bytes = body_len + 8
                        break
        else:
            log.debug("Connection %s closed by server", self)
            self.close()

    def push(self, data):
        sabs = self.out_buffer_size
        if len(data) > sabs:
            chunks = []
            for i in xrange(0, len(data), sabs):
                chunks.append(data[i:i + sabs])
        else:
            chunks = [data]

        with self._deque_lock:
            self.deque.extend(chunks)
            self._loop_notifier.send()

    def register_watcher(self, event_type, callback, register_timeout=None):
        self._push_watchers[event_type].add(callback)
        self.wait_for_response(
            RegisterMessage(event_list=[event_type]), timeout=register_timeout)

    def register_watchers(self, type_callback_dict, register_timeout=None):
        for event_type, callback in type_callback_dict.items():
            self._push_watchers[event_type].add(callback)
        self.wait_for_response(
            RegisterMessage(event_list=type_callback_dict.keys()), timeout=register_timeout)


_preparer = libev.Prepare(LibevConnection._loop, LibevConnection.loop_will_run)
# prevent _preparer from keeping the loop from returning
LibevConnection._loop.unref()
_preparer.start()

########NEW FILE########
__FILENAME__ = marshal
# Copyright 2013-2014 DataStax, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import six
import struct


def _make_packer(format_string):
    try:
        packer = struct.Struct(format_string)  # new in Python 2.5
    except AttributeError:
        pack = lambda x: struct.pack(format_string, x)
        unpack = lambda s: struct.unpack(format_string, s)
    else:
        pack = packer.pack
        unpack = lambda s: packer.unpack(s)[0]
    return pack, unpack

int64_pack, int64_unpack = _make_packer('>q')
int32_pack, int32_unpack = _make_packer('>i')
int16_pack, int16_unpack = _make_packer('>h')
int8_pack, int8_unpack = _make_packer('>b')
uint64_pack, uint64_unpack = _make_packer('>Q')
uint32_pack, uint32_unpack = _make_packer('>I')
uint16_pack, uint16_unpack = _make_packer('>H')
uint8_pack, uint8_unpack = _make_packer('>B')
float_pack, float_unpack = _make_packer('>f')
double_pack, double_unpack = _make_packer('>d')

# Special case for cassandra header
header_struct = struct.Struct('>BBbB')
header_pack = header_struct.pack
header_unpack = header_struct.unpack


if six.PY3:
    def varint_unpack(term):
        val = int(''.join("%02x" % i for i in term), 16)
        if (term[0] & 128) != 0:
            val -= 1 << (len(term) * 8)
        return val
else:
    def varint_unpack(term):  # noqa
        val = int(term.encode('hex'), 16)
        if (ord(term[0]) & 128) != 0:
            val = val - (1 << (len(term) * 8))
        return val


def bitlength(n):
    bitlen = 0
    while n > 0:
        n >>= 1
        bitlen += 1
    return bitlen


def varint_pack(big):
    pos = True
    if big == 0:
        return b'\x00'
    if big < 0:
        bytelength = bitlength(abs(big) - 1) // 8 + 1
        big = (1 << bytelength * 8) + big
        pos = False
    revbytes = bytearray()
    while big > 0:
        revbytes.append(big & 0xff)
        big >>= 8
    if pos and revbytes[-1] & 0x80:
        revbytes.append(0)
    revbytes.reverse()
    return six.binary_type(revbytes)

########NEW FILE########
__FILENAME__ = metadata
# Copyright 2013-2014 DataStax, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from bisect import bisect_right
from collections import defaultdict
from hashlib import md5
from itertools import islice, cycle
import json
import logging
import re
from threading import RLock
import weakref
import six

murmur3 = None
try:
    from cassandra.murmur3 import murmur3
except ImportError as e:
    pass

import cassandra.cqltypes as types
from cassandra.marshal import varint_unpack
from cassandra.pool import Host
from cassandra.util import OrderedDict

log = logging.getLogger(__name__)

_keywords = set((
    'select', 'from', 'where', 'and', 'key', 'insert', 'update', 'with',
    'limit', 'using', 'use', 'count', 'set',
    'begin', 'apply', 'batch', 'truncate', 'delete', 'in', 'create',
    'keyspace', 'schema', 'columnfamily', 'table', 'index', 'on', 'drop',
    'primary', 'into', 'values', 'timestamp', 'ttl', 'alter', 'add', 'type',
    'compact', 'storage', 'order', 'by', 'asc', 'desc', 'clustering',
    'token', 'writetime', 'map', 'list', 'to'
))

_unreserved_keywords = set((
    'key', 'clustering', 'ttl', 'compact', 'storage', 'type', 'values'
))


class Metadata(object):
    """
    Holds a representation of the cluster schema and topology.
    """

    cluster_name = None
    """ The string name of the cluster. """

    keyspaces = None
    """
    A map from keyspace names to matching :class:`~.KeyspaceMetadata` instances.
    """

    partitioner = None
    """
    The string name of the partitioner for the cluster.
    """

    token_map = None
    """ A :class:`~.TokenMap` instance describing the ring topology. """

    def __init__(self, cluster):
        # use a weak reference so that the Cluster object can be GC'ed.
        # Normally the cycle detector would handle this, but implementing
        # __del__ disables that.
        self.cluster_ref = weakref.ref(cluster)
        self.keyspaces = {}
        self._hosts = {}
        self._hosts_lock = RLock()

    def export_schema_as_string(self):
        """
        Returns a string that can be executed as a query in order to recreate
        the entire schema.  The string is formatted to be human readable.
        """
        return "\n".join(ks.export_as_string() for ks in self.keyspaces.values())

    def rebuild_schema(self, ks_results, cf_results, col_results):
        """
        Rebuild the view of the current schema from a fresh set of rows from
        the system schema tables.

        For internal use only.
        """
        cf_def_rows = defaultdict(list)
        col_def_rows = defaultdict(lambda: defaultdict(list))

        for row in cf_results:
            cf_def_rows[row["keyspace_name"]].append(row)

        for row in col_results:
            ksname = row["keyspace_name"]
            cfname = row["columnfamily_name"]
            col_def_rows[ksname][cfname].append(row)

        current_keyspaces = set()
        for row in ks_results:
            keyspace_meta = self._build_keyspace_metadata(row)
            for table_row in cf_def_rows.get(keyspace_meta.name, []):
                table_meta = self._build_table_metadata(
                    keyspace_meta, table_row, col_def_rows[keyspace_meta.name])
                keyspace_meta.tables[table_meta.name] = table_meta

            current_keyspaces.add(keyspace_meta.name)
            old_keyspace_meta = self.keyspaces.get(keyspace_meta.name, None)
            self.keyspaces[keyspace_meta.name] = keyspace_meta
            if old_keyspace_meta:
                self._keyspace_updated(keyspace_meta.name)
            else:
                self._keyspace_added(keyspace_meta.name)

        # remove not-just-added keyspaces
        removed_keyspaces = [ksname for ksname in self.keyspaces.keys()
                             if ksname not in current_keyspaces]
        self.keyspaces = dict((name, meta) for name, meta in self.keyspaces.items()
                              if name in current_keyspaces)
        for ksname in removed_keyspaces:
            self._keyspace_removed(ksname)

    def keyspace_changed(self, keyspace, ks_results, cf_results, col_results):
        if not ks_results:
            if keyspace in self.keyspaces:
                del self.keyspaces[keyspace]
                self._keyspace_removed(keyspace)
            return

        col_def_rows = defaultdict(list)
        for row in col_results:
            cfname = row["columnfamily_name"]
            col_def_rows[cfname].append(row)

        keyspace_meta = self._build_keyspace_metadata(ks_results[0])
        old_keyspace_meta = self.keyspaces.get(keyspace, None)

        new_table_metas = {}
        for table_row in cf_results:
            table_meta = self._build_table_metadata(
                keyspace_meta, table_row, col_def_rows)
            new_table_metas[table_meta.name] = table_meta

        keyspace_meta.tables = new_table_metas

        self.keyspaces[keyspace] = keyspace_meta
        if old_keyspace_meta:
            if (keyspace_meta.replication_strategy != old_keyspace_meta.replication_strategy):
                self._keyspace_updated(keyspace)
        else:
            self._keyspace_added(keyspace)

    def table_changed(self, keyspace, table, cf_results, col_results):
        try:
            keyspace_meta = self.keyspaces[keyspace]
        except KeyError:
            # we're trying to update a table in a keyspace we don't know about
            log.error("Tried to update schema for table '%s' in unknown keyspace '%s'",
                      table, keyspace)
            return

        if not cf_results:
            # the table was removed
            keyspace_meta.tables.pop(table, None)
        else:
            assert len(cf_results) == 1
            keyspace_meta.tables[table] = self._build_table_metadata(
                    keyspace_meta, cf_results[0], {table: col_results})

    def _keyspace_added(self, ksname):
        if self.token_map:
            self.token_map.rebuild_keyspace(ksname, build_if_absent=False)

    def _keyspace_updated(self, ksname):
        if self.token_map:
            self.token_map.rebuild_keyspace(ksname, build_if_absent=False)

    def _keyspace_removed(self, ksname):
        if self.token_map:
            self.token_map.remove_keyspace(ksname)

    def _build_keyspace_metadata(self, row):
        name = row["keyspace_name"]
        durable_writes = row["durable_writes"]
        strategy_class = row["strategy_class"]
        strategy_options = json.loads(row["strategy_options"])
        return KeyspaceMetadata(name, durable_writes, strategy_class, strategy_options)

    def _build_table_metadata(self, keyspace_metadata, row, col_rows):
        cfname = row["columnfamily_name"]

        comparator = types.lookup_casstype(row["comparator"])
        if issubclass(comparator, types.CompositeType):
            column_name_types = comparator.subtypes
            is_composite = True
        else:
            column_name_types = (comparator,)
            is_composite = False

        num_column_name_components = len(column_name_types)
        last_col = column_name_types[-1]

        column_aliases = json.loads(row["column_aliases"])
        if is_composite:
            if issubclass(last_col, types.ColumnToCollectionType):
                # collections
                is_compact = False
                has_value = False
                clustering_size = num_column_name_components - 2
            elif (len(column_aliases) == num_column_name_components - 1
                    and issubclass(last_col, types.UTF8Type)):
                # aliases?
                is_compact = False
                has_value = False
                clustering_size = num_column_name_components - 1
            else:
                # compact table
                is_compact = True
                has_value = True
                clustering_size = num_column_name_components
        else:
            is_compact = True
            if column_aliases or not col_rows.get(cfname):
                has_value = True
                clustering_size = num_column_name_components
            else:
                has_value = False
                clustering_size = 0

        table_meta = TableMetadata(keyspace_metadata, cfname)
        table_meta.comparator = comparator

        # partition key
        key_aliases = row.get("key_aliases")
        key_aliases = json.loads(key_aliases) if key_aliases else []

        key_type = types.lookup_casstype(row["key_validator"])
        key_types = key_type.subtypes if issubclass(key_type, types.CompositeType) else [key_type]
        for i, col_type in enumerate(key_types):
            if len(key_aliases) > i:
                column_name = key_aliases[i]
            elif i == 0:
                column_name = "key"
            else:
                column_name = "key%d" % i

            col = ColumnMetadata(table_meta, column_name, col_type)
            table_meta.columns[column_name] = col
            table_meta.partition_key.append(col)

        # clustering key
        for i in range(clustering_size):
            if len(column_aliases) > i:
                column_name = column_aliases[i]
            else:
                column_name = "column%d" % i

            col = ColumnMetadata(table_meta, column_name, column_name_types[i])
            table_meta.columns[column_name] = col
            table_meta.clustering_key.append(col)

        # value alias (if present)
        if has_value:
            validator = types.lookup_casstype(row["default_validator"])
            if not key_aliases:  # TODO are we checking the right thing here?
                value_alias = "value"
            else:
                value_alias = row["value_alias"]

            col = ColumnMetadata(table_meta, value_alias, validator)
            table_meta.columns[value_alias] = col

        # other normal columns
        if col_rows:
            for col_row in col_rows[cfname]:
                column_meta = self._build_column_metadata(table_meta, col_row)
                table_meta.columns[column_meta.name] = column_meta

        table_meta.options = self._build_table_options(row)
        table_meta.is_compact_storage = is_compact
        return table_meta

    def _build_table_options(self, row):
        """ Setup the mostly-non-schema table options, like caching settings """
        options = dict((o, row.get(o)) for o in TableMetadata.recognized_options if o in row)
        return options

    def _build_column_metadata(self, table_metadata, row):
        name = row["column_name"]
        data_type = types.lookup_casstype(row["validator"])
        is_static = row.get("type", None) == "static"
        column_meta = ColumnMetadata(table_metadata, name, data_type, is_static=is_static)
        index_meta = self._build_index_metadata(column_meta, row)
        column_meta.index = index_meta
        return column_meta

    def _build_index_metadata(self, column_metadata, row):
        index_name = row.get("index_name")
        index_type = row.get("index_type")
        if index_name or index_type:
            return IndexMetadata(column_metadata, index_name, index_type)
        else:
            return None

    def rebuild_token_map(self, partitioner, token_map):
        """
        Rebuild our view of the topology from fresh rows from the
        system topology tables.
        For internal use only.
        """
        self.partitioner = partitioner
        if partitioner.endswith('RandomPartitioner'):
            token_class = MD5Token
        elif partitioner.endswith('Murmur3Partitioner'):
            token_class = Murmur3Token
        elif partitioner.endswith('ByteOrderedPartitioner'):
            token_class = BytesToken
        else:
            self.token_map = None
            return

        token_to_host_owner = {}
        ring = []
        for host, token_strings in six.iteritems(token_map):
            for token_string in token_strings:
                token = token_class(token_string)
                ring.append(token)
                token_to_host_owner[token] = host

        all_tokens = sorted(ring)
        self.token_map = TokenMap(
                token_class, token_to_host_owner, all_tokens, self)

    def get_replicas(self, keyspace, key):
        """
        Returns a list of :class:`.Host` instances that are replicas for a given
        partition key.
        """
        t = self.token_map
        if not t:
            return []
        try:
            return t.get_replicas(keyspace, t.token_class.from_key(key))
        except NoMurmur3:
            return []

    def can_support_partitioner(self):
        if self.partitioner.endswith('Murmur3Partitioner') and murmur3 is None:
            return False
        else:
            return True

    def add_host(self, address, datacenter, rack):
        cluster = self.cluster_ref()
        with self._hosts_lock:
            if address not in self._hosts:
                new_host = Host(
                    address, cluster.conviction_policy_factory, datacenter, rack)
                self._hosts[address] = new_host
            else:
                return None

        return new_host

    def remove_host(self, host):
        with self._hosts_lock:
            return bool(self._hosts.pop(host.address, False))

    def get_host(self, address):
        return self._hosts.get(address)

    def all_hosts(self):
        """
        Returns a list of all known :class:`.Host` instances in the cluster.
        """
        with self._hosts_lock:
            return self._hosts.values()


class ReplicationStrategy(object):

    @classmethod
    def create(cls, strategy_class, options_map):
        if not strategy_class:
            return None

        if strategy_class.endswith("OldNetworkTopologyStrategy"):
            return None
        elif strategy_class.endswith("NetworkTopologyStrategy"):
            return NetworkTopologyStrategy(options_map)
        elif strategy_class.endswith("SimpleStrategy"):
            repl_factor = options_map.get('replication_factor', None)
            if not repl_factor:
                return None
            return SimpleStrategy(repl_factor)
        elif strategy_class.endswith("LocalStrategy"):
            return LocalStrategy()

    def make_token_replica_map(self, token_to_host_owner, ring):
        raise NotImplementedError()

    def export_for_schema(self):
        raise NotImplementedError()


class SimpleStrategy(ReplicationStrategy):

    name = "SimpleStrategy"

    replication_factor = None
    """
    The replication factor for this keyspace.
    """

    def __init__(self, replication_factor):
        self.replication_factor = int(replication_factor)

    def make_token_replica_map(self, token_to_host_owner, ring):
        replica_map = {}
        for i in range(len(ring)):
            j, hosts = 0, list()
            while len(hosts) < self.replication_factor and j < len(ring):
                token = ring[(i + j) % len(ring)]
                host = token_to_host_owner[token]
                if not host in hosts:
                    hosts.append(host)
                j += 1

            replica_map[ring[i]] = hosts
        return replica_map

    def export_for_schema(self):
        return "{'class': 'SimpleStrategy', 'replication_factor': '%d'}" \
               % (self.replication_factor,)

    def __eq__(self, other):
        if not isinstance(other, SimpleStrategy):
            return False

        return self.replication_factor == other.replication_factor


class NetworkTopologyStrategy(ReplicationStrategy):

    name = "NetworkTopologyStrategy"

    dc_replication_factors = None
    """
    A map of datacenter names to the replication factor for that DC.
    """

    def __init__(self, dc_replication_factors):
        self.dc_replication_factors = dict(
                (str(k), int(v)) for k, v in dc_replication_factors.items())

    def make_token_replica_map(self, token_to_host_owner, ring):
        # note: this does not account for hosts having different racks
        replica_map = defaultdict(list)
        ring_len = len(ring)
        ring_len_range = range(ring_len)
        dc_rf_map = dict((dc, int(rf))
                         for dc, rf in self.dc_replication_factors.items() if rf > 0)
        dcs = dict((h, h.datacenter) for h in set(token_to_host_owner.values()))

        # build a map of DCs to lists of indexes into `ring` for tokens that
        # belong to that DC
        dc_to_token_offset = defaultdict(list)
        for i, token in enumerate(ring):
            host = token_to_host_owner[token]
            dc_to_token_offset[dcs[host]].append(i)

        # A map of DCs to an index into the dc_to_token_offset value for that dc.
        # This is how we keep track of advancing around the ring for each DC.
        dc_to_current_index = defaultdict(int)

        for i in ring_len_range:
            remaining = dc_rf_map.copy()
            replicas = replica_map[ring[i]]

            # go through each DC and find the replicas in that DC
            for dc in dc_to_token_offset.keys():
                if dc not in remaining:
                    continue

                # advance our per-DC index until we're up to at least the
                # current token in the ring
                token_offsets = dc_to_token_offset[dc]
                index = dc_to_current_index[dc]
                num_tokens = len(token_offsets)
                while index < num_tokens and token_offsets[index] < i:
                    index += 1
                dc_to_current_index[dc] = index

                # now add the next RF distinct token owners to the set of
                # replicas for this DC
                for token_offset in islice(cycle(token_offsets), index, index + num_tokens):
                    host = token_to_host_owner[ring[token_offset]]
                    if host in replicas:
                        continue

                    replicas.append(host)
                    dc_remaining = remaining[dc] - 1
                    if dc_remaining == 0:
                        del remaining[dc]
                        break
                    else:
                        remaining[dc] = dc_remaining

        return replica_map

    def export_for_schema(self):
        ret = "{'class': 'NetworkTopologyStrategy'"
        for dc, repl_factor in self.dc_replication_factors:
            ret += ", '%s': '%d'" % (dc, repl_factor)
        return ret + "}"

    def __eq__(self, other):
        if not isinstance(other, NetworkTopologyStrategy):
            return False

        return self.dc_replication_factors == other.dc_replication_factors


class LocalStrategy(ReplicationStrategy):

    name = "LocalStrategy"

    def make_token_replica_map(self, token_to_host_owner, ring):
        return {}

    def export_for_schema(self):
        return "{'class': 'LocalStrategy'}"

    def __eq__(self, other):
        return isinstance(other, LocalStrategy)


class KeyspaceMetadata(object):
    """
    A representation of the schema for a single keyspace.
    """

    name = None
    """ The string name of the keyspace. """

    durable_writes = True
    """
    A boolean indicating whether durable writes are enabled for this keyspace
    or not.
    """

    replication_strategy = None
    """
    A :class:`.ReplicationStrategy` subclass object.
    """

    tables = None
    """
    A map from table names to instances of :class:`~.TableMetadata`.
    """

    def __init__(self, name, durable_writes, strategy_class, strategy_options):
        self.name = name
        self.durable_writes = durable_writes
        self.replication_strategy = ReplicationStrategy.create(strategy_class, strategy_options)
        self.tables = {}

    def export_as_string(self):
        return "\n".join([self.as_cql_query()] + [t.export_as_string() for t in self.tables.values()])

    def as_cql_query(self):
        ret = "CREATE KEYSPACE %s WITH replication = %s " % (
            protect_name(self.name),
            self.replication_strategy.export_for_schema())
        return ret + (' AND durable_writes = %s;' % ("true" if self.durable_writes else "false"))


class TableMetadata(object):
    """
    A representation of the schema for a single table.
    """

    keyspace = None
    """ An instance of :class:`~.KeyspaceMetadata`. """

    name = None
    """ The string name of the table. """

    partition_key = None
    """
    A list of :class:`.ColumnMetadata` instances representing the columns in
    the partition key for this table.  This will always hold at least one
    column.
    """

    clustering_key = None
    """
    A list of :class:`.ColumnMetadata` instances representing the columns
    in the clustering key for this table.  These are all of the
    :attr:`.primary_key` columns that are not in the :attr:`.partition_key`.

    Note that a table may have no clustering keys, in which case this will
    be an empty list.
    """

    @property
    def primary_key(self):
        """
        A list of :class:`.ColumnMetadata` representing the components of
        the primary key for this table.
        """
        return self.partition_key + self.clustering_key

    columns = None
    """
    A dict mapping column names to :class:`.ColumnMetadata` instances.
    """

    is_compact_storage = False

    options = None
    """
    A dict mapping table option names to their specific settings for this
    table.
    """

    recognized_options = (
        "comment",
        "read_repair_chance",
        "dclocal_read_repair_chance",
        "replicate_on_write",
        "gc_grace_seconds",
        "bloom_filter_fp_chance",
        "caching",
        "compaction_strategy_class",
        "compaction_strategy_options",
        "min_compaction_threshold",
        "max_compaction_threshold",
        "compression_parameters",
        "min_index_interval",
        "max_index_interval",
        "index_interval",
        "speculative_retry",
        "rows_per_partition_to_cache",
        "memtable_flush_period_in_ms",
        "populate_io_cache_on_flush",
        "compaction",
        "compression",
        "default_time_to_live")

    compaction_options = {
        "min_compaction_threshold": "min_threshold",
        "max_compaction_threshold": "max_threshold",
        "compaction_strategy_class": "class"}

    def __init__(self, keyspace_metadata, name, partition_key=None, clustering_key=None, columns=None, options=None):
        self.keyspace = keyspace_metadata
        self.name = name
        self.partition_key = [] if partition_key is None else partition_key
        self.clustering_key = [] if clustering_key is None else clustering_key
        self.columns = OrderedDict() if columns is None else columns
        self.options = options
        self.comparator = None

    def export_as_string(self):
        """
        Returns a string of CQL queries that can be used to recreate this table
        along with all indexes on it.  The returned string is formatted to
        be human readable.
        """
        ret = self.as_cql_query(formatted=True)
        ret += ";"

        for col_meta in self.columns.values():
            if col_meta.index:
                ret += "\n%s;" % (col_meta.index.as_cql_query(),)

        return ret

    def as_cql_query(self, formatted=False):
        """
        Returns a CQL query that can be used to recreate this table (index
        creations are not included).  If `formatted` is set to :const:`True`,
        extra whitespace will be added to make the query human readable.
        """
        ret = "CREATE TABLE %s.%s (%s" % (
            protect_name(self.keyspace.name),
            protect_name(self.name),
            "\n" if formatted else "")

        if formatted:
            column_join = ",\n"
            padding = "    "
        else:
            column_join = ", "
            padding = ""

        columns = []
        for col in self.columns.values():
            columns.append("%s %s%s" % (protect_name(col.name), col.typestring, ' static' if col.is_static else ''))

        if len(self.partition_key) == 1 and not self.clustering_key:
            columns[0] += " PRIMARY KEY"

        ret += column_join.join("%s%s" % (padding, col) for col in columns)

        # primary key
        if len(self.partition_key) > 1 or self.clustering_key:
            ret += "%s%sPRIMARY KEY (" % (column_join, padding)

            if len(self.partition_key) > 1:
                ret += "(%s)" % ", ".join(protect_name(col.name) for col in self.partition_key)
            else:
                ret += self.partition_key[0].name

            if self.clustering_key:
                ret += ", %s" % ", ".join(protect_name(col.name) for col in self.clustering_key)

            ret += ")"

        # options
        ret += "%s) WITH " % ("\n" if formatted else "")

        option_strings = []
        if self.is_compact_storage:
            option_strings.append("COMPACT STORAGE")

        if self.clustering_key:
            cluster_str = "CLUSTERING ORDER BY "

            clustering_names = protect_names([c.name for c in self.clustering_key])

            if self.is_compact_storage and \
                    not issubclass(self.comparator, types.CompositeType):
                subtypes = [self.comparator]
            else:
                subtypes = self.comparator.subtypes

            inner = []
            for colname, coltype in zip(clustering_names, subtypes):
                ordering = "DESC" if issubclass(coltype, types.ReversedType) else "ASC"
                inner.append("%s %s" % (colname, ordering))

            cluster_str += "(%s)" % ", ".join(inner)
            option_strings.append(cluster_str)

        option_strings.extend(self._make_option_strings())

        join_str = "\n    AND " if formatted else " AND "
        ret += join_str.join(option_strings)

        return ret

    def _make_option_strings(self):
        ret = []
        options_copy = dict(self.options.items())
        if not options_copy.get('compaction'):
            options_copy.pop('compaction', None)

            actual_options = json.loads(options_copy.pop('compaction_strategy_options', '{}'))
            for system_table_name, compact_option_name in self.compaction_options.items():
                value = options_copy.pop(system_table_name, None)
                if value:
                    actual_options.setdefault(compact_option_name, value)

            compaction_option_strings = ["'%s': '%s'" % (k, v) for k, v in actual_options.items()]
            ret.append('compaction = {%s}' % ', '.join(compaction_option_strings))

        for system_table_name in self.compaction_options.keys():
            options_copy.pop(system_table_name, None)  # delete if present
        options_copy.pop('compaction_strategy_option', None)

        if not options_copy.get('compression'):
            params = json.loads(options_copy.pop('compression_parameters', '{}'))
            if params:
                param_strings = ["'%s': '%s'" % (k, v) for k, v in params.items()]
                ret.append('compression = {%s}' % ', '.join(param_strings))

        for name, value in options_copy.items():
            if value is not None:
                if name == "comment":
                    value = value or ""
                ret.append("%s = %s" % (name, protect_value(value)))

        return list(sorted(ret))


if six.PY3:
    def protect_name(name):
        return maybe_escape_name(name)
else:
    def protect_name(name):  # NOQA
        if isinstance(name, six.text_type):
            name = name.encode('utf8')
        return maybe_escape_name(name)


def protect_names(names):
    return [protect_name(n) for n in names]


def protect_value(value):
    if value is None:
        return 'NULL'
    if isinstance(value, (int, float, bool)):
        return str(value).lower()
    return "'%s'" % value.replace("'", "''")


valid_cql3_word_re = re.compile(r'^[a-z][0-9a-z_]*$')


def is_valid_name(name):
    if name is None:
        return False
    if name.lower() in _keywords - _unreserved_keywords:
        return False
    return valid_cql3_word_re.match(name) is not None


def maybe_escape_name(name):
    if is_valid_name(name):
        return name
    return escape_name(name)


def escape_name(name):
    return '"%s"' % (name.replace('"', '""'),)


class ColumnMetadata(object):
    """
    A representation of a single column in a table.
    """

    table = None
    """ The :class:`.TableMetadata` this column belongs to. """

    name = None
    """ The string name of this column. """

    data_type = None

    index = None
    """
    If an index exists on this column, this is an instance of
    :class:`.IndexMetadata`, otherwise :const:`None`.
    """

    is_static = False
    """
    If this column is static (available in Cassandra 2.1+), this will
    be :const:`True`, otherwise :const:`False`.
    """

    def __init__(self, table_metadata, column_name, data_type, index_metadata=None, is_static=False):
        self.table = table_metadata
        self.name = column_name
        self.data_type = data_type
        self.index = index_metadata
        self.is_static = is_static

    @property
    def typestring(self):
        """
        A string representation of the type for this column, such as "varchar"
        or "map<string, int>".
        """
        if issubclass(self.data_type, types.ReversedType):
            return self.data_type.subtypes[0].cql_parameterized_type()
        else:
            return self.data_type.cql_parameterized_type()

    def __str__(self):
        return "%s %s" % (self.name, self.data_type)


class IndexMetadata(object):
    """
    A representation of a secondary index on a column.
    """

    column = None
    """
    The column (:class:`.ColumnMetadata`) this index is on.
    """

    name = None
    """ A string name for the index. """

    index_type = None
    """ A string representing the type of index. """

    def __init__(self, column_metadata, index_name=None, index_type=None):
        self.column = column_metadata
        self.name = index_name
        self.index_type = index_type

    def as_cql_query(self):
        """
        Returns a CQL query that can be used to recreate this index.
        """
        table = self.column.table
        return "CREATE INDEX %s ON %s.%s (%s)" % (
            self.name,  # Cassandra doesn't like quoted index names for some reason
            protect_name(table.keyspace.name),
            protect_name(table.name),
            protect_name(self.column.name))


class TokenMap(object):
    """
    Information about the layout of the ring.
    """

    token_class = None
    """
    A subclass of :class:`.Token`, depending on what partitioner the cluster uses.
    """

    token_to_host_owner = None
    """
    A map of :class:`.Token` objects to the :class:`.Host` that owns that token.
    """

    tokens_to_hosts_by_ks = None
    """
    A map of keyspace names to a nested map of :class:`.Token` objects to
    sets of :class:`.Host` objects.
    """

    ring = None
    """
    An ordered list of :class:`.Token` instances in the ring.
    """

    _metadata = None

    def __init__(self, token_class, token_to_host_owner, all_tokens, metadata):
        self.token_class = token_class
        self.ring = all_tokens
        self.token_to_host_owner = token_to_host_owner

        self.tokens_to_hosts_by_ks = {}
        self._metadata = metadata
        self._rebuild_lock = RLock()

    def rebuild_keyspace(self, keyspace, build_if_absent=False):
        with self._rebuild_lock:
            current = self.tokens_to_hosts_by_ks.get(keyspace, None)
            if (build_if_absent and current is None) or (not build_if_absent and current is not None):
                replica_map = self.replica_map_for_keyspace(self._metadata.keyspaces[keyspace])
                self.tokens_to_hosts_by_ks[keyspace] = replica_map

    def replica_map_for_keyspace(self, ks_metadata):
        strategy = ks_metadata.replication_strategy
        if strategy:
            return strategy.make_token_replica_map(self.token_to_host_owner, self.ring)
        else:
            return None

    def remove_keyspace(self, keyspace):
        del self.tokens_to_hosts_by_ks[keyspace]

    def get_replicas(self, keyspace, token):
        """
        Get  a set of :class:`.Host` instances representing all of the
        replica nodes for a given :class:`.Token`.
        """
        tokens_to_hosts = self.tokens_to_hosts_by_ks.get(keyspace, None)
        if tokens_to_hosts is None:
            self.rebuild_keyspace(keyspace, build_if_absent=True)
            tokens_to_hosts = self.tokens_to_hosts_by_ks.get(keyspace, None)
            if tokens_to_hosts is None:
                return []

        # token range ownership is exclusive on the LHS (the start token), so
        # we use bisect_right, which, in the case of a tie/exact match,
        # picks an insertion point to the right of the existing match
        point = bisect_right(self.ring, token)
        if point == len(self.ring):
            return tokens_to_hosts[self.ring[0]]
        else:
            return tokens_to_hosts[self.ring[point]]


class Token(object):
    """
    Abstract class representing a token.
    """

    @classmethod
    def hash_fn(cls, key):
        return key

    @classmethod
    def from_key(cls, key):
        return cls(cls.hash_fn(key))

    def __cmp__(self, other):
        if self.value < other.value:
            return -1
        elif self.value == other.value:
            return 0
        else:
            return 1

    def __eq__(self, other):
        return self.value == other.value

    def __lt__(self, other):
        return self.value < other.value

    def __hash__(self):
        return hash(self.value)

    def __repr__(self):
        return "<%s: %s>" % (self.__class__.__name__, self.value)
    __str__ = __repr__

MIN_LONG = -(2 ** 63)
MAX_LONG = (2 ** 63) - 1


class NoMurmur3(Exception):
    pass


class Murmur3Token(Token):
    """
    A token for ``Murmur3Partitioner``.
    """

    @classmethod
    def hash_fn(cls, key):
        if murmur3 is not None:
            h = int(murmur3(key))
            return h if h != MIN_LONG else MAX_LONG
        else:
            raise NoMurmur3()

    def __init__(self, token):
        """ `token` should be an int or string representing the token. """
        self.value = int(token)


class MD5Token(Token):
    """
    A token for ``RandomPartitioner``.
    """

    @classmethod
    def hash_fn(cls, key):
        if isinstance(key, six.text_type):
            key = key.encode('UTF-8')
        return abs(varint_unpack(md5(key).digest()))

    def __init__(self, token):
        """ `token` should be an int or string representing the token. """
        self.value = int(token)


class BytesToken(Token):
    """
    A token for ``ByteOrderedPartitioner``.
    """

    def __init__(self, token_string):
        """ `token_string` should be string representing the token. """
        if not isinstance(token_string, six.string_types):
            raise TypeError(
                "Tokens for ByteOrderedPartitioner should be strings (got %s)"
                % (type(token_string),))
        self.value = token_string

########NEW FILE########
__FILENAME__ = metrics
# Copyright 2013-2014 DataStax, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from itertools import chain
import logging

try:
    from greplin import scales
except ImportError:
    raise ImportError(
        "The scales library is required for metrics support: "
        "https://pypi.python.org/pypi/scales")

log = logging.getLogger(__name__)


class Metrics(object):
    """
    A collection of timers and counters for various performance metrics.
    """

    request_timer = None
    """
    A :class:`greplin.scales.PmfStat` timer for requests. This is a dict-like
    object with the following keys:

      * count - number of requests that have been timed
      * min - min latency
      * max - max latency
      * mean - mean latency
      * stdev - standard deviation for latencies
      * median - median latency
      * 75percentile - 75th percentile latencies
      * 97percentile - 97th percentile latencies
      * 98percentile - 98th percentile latencies
      * 99percentile - 99th percentile latencies
      * 999percentile - 99.9th percentile latencies
    """

    connection_errors = None
    """
    A :class:`greplin.scales.IntStat` count of the number of times that a
    request to a Cassandra node has failed due to a connection problem.
    """

    write_timeouts = None
    """
    A :class:`greplin.scales.IntStat` count of write requests that resulted
    in a timeout.
    """

    read_timeouts = None
    """
    A :class:`greplin.scales.IntStat` count of read requests that resulted
    in a timeout.
    """

    unavailables = None
    """
    A :class:`greplin.scales.IntStat` count of write or read requests that
    failed due to an insufficient number of replicas being alive to meet
    the requested :class:`.ConsistencyLevel`.
    """

    other_errors = None
    """
    A :class:`greplin.scales.IntStat` count of all other request failures,
    including failures caused by invalid requests, bootstrapping nodes,
    overloaded nodes, etc.
    """

    retries = None
    """
    A :class:`greplin.scales.IntStat` count of the number of times a
    request was retried based on the :class:`.RetryPolicy` decision.
    """

    ignores = None
    """
    A :class:`greplin.scales.IntStat` count of the number of times a
    failed request was ignored based on the :class:`.RetryPolicy` decision.
    """

    known_hosts = None
    """
    A :class:`greplin.scales.IntStat` count of the number of nodes in
    the cluster that the driver is aware of, regardless of whether any
    connections are opened to those nodes.
    """

    connected_to = None
    """
    A :class:`greplin.scales.IntStat` count of the number of nodes that
    the driver currently has at least one connection open to.
    """

    open_connections = None
    """
    A :class:`greplin.scales.IntStat` count of the number connections
    the driver currently has open.
    """

    def __init__(self, cluster_proxy):
        log.debug("Starting metric capture")

        self.stats = scales.collection('/cassandra',
            scales.PmfStat('request_timer'),
            scales.IntStat('connection_errors'),
            scales.IntStat('write_timeouts'),
            scales.IntStat('read_timeouts'),
            scales.IntStat('unavailables'),
            scales.IntStat('other_errors'),
            scales.IntStat('retries'),
            scales.IntStat('ignores'),

            # gauges
            scales.Stat('known_hosts',
                lambda: len(cluster_proxy.metadata.all_hosts())),
            scales.Stat('connected_to',
                lambda: len(set(chain.from_iterable(s._pools.keys() for s in cluster_proxy.sessions)))),
            scales.Stat('open_connections',
                lambda: sum(sum(p.open_count for p in s._pools.values()) for s in cluster_proxy.sessions)))

        self.request_timer = self.stats.request_timer
        self.connection_errors = self.stats.connection_errors
        self.write_timeouts = self.stats.write_timeouts
        self.read_timeouts = self.stats.read_timeouts
        self.unavailables = self.stats.unavailables
        self.other_errors = self.stats.other_errors
        self.retries = self.stats.retries
        self.ignores = self.stats.ignores
        self.known_hosts = self.stats.known_hosts
        self.connected_to = self.stats.connected_to
        self.open_connections = self.stats.open_connections

    def on_connection_error(self):
        self.stats.connection_errors += 1

    def on_write_timeout(self):
        self.stats.write_timeouts += 1

    def on_read_timeout(self):
        self.stats.read_timeouts += 1

    def on_unavailable(self):
        self.stats.unavailables += 1

    def on_other_error(self):
        self.stats.other_errors += 1

    def on_ignore(self):
        self.stats.ignores += 1

    def on_retry(self):
        self.stats.retries += 1

########NEW FILE########
__FILENAME__ = policies
# Copyright 2013-2014 DataStax, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from itertools import islice, cycle, groupby, repeat
import logging
from random import randint
from threading import Lock
import six

from cassandra import ConsistencyLevel

from six.moves import range

log = logging.getLogger(__name__)


class HostDistance(object):
    """
    A measure of how "distant" a node is from the client, which
    may influence how the load balancer distributes requests
    and how many connections are opened to the node.
    """

    IGNORED = -1
    """
    A node with this distance should never be queried or have
    connections opened to it.
    """

    LOCAL = 0
    """
    Nodes with ``LOCAL`` distance will be preferred for operations
    under some load balancing policies (such as :class:`.DCAwareRoundRobinPolicy`)
    and will have a greater number of connections opened against
    them by default.

    This distance is typically used for nodes within the same
    datacenter as the client.
    """

    REMOTE = 1
    """
    Nodes with ``REMOTE`` distance will be treated as a last resort
    by some load balancing policies (such as :class:`.DCAwareRoundRobinPolicy`)
    and will have a smaller number of connections opened against
    them by default.

    This distance is typically used for nodes outside of the
    datacenter that the client is running in.
    """


class HostStateListener(object):

    def on_up(self, host):
        """ Called when a node is marked up. """
        raise NotImplementedError()

    def on_down(self, host):
        """ Called when a node is marked down. """
        raise NotImplementedError()

    def on_add(self, host):
        """
        Called when a node is added to the cluster.  The newly added node
        should be considered up.
        """
        raise NotImplementedError()

    def on_remove(self, host):
        """ Called when a node is removed from the cluster. """
        raise NotImplementedError()


class LoadBalancingPolicy(HostStateListener):
    """
    Load balancing policies are used to decide how to distribute
    requests among all possible coordinator nodes in the cluster.

    In particular, they may focus on querying "near" nodes (those
    in a local datacenter) or on querying nodes who happen to
    be replicas for the requested data.

    You may also use subclasses of :class:`.LoadBalancingPolicy` for
    custom behavior.
    """

    _hosts_lock = None

    def __init__(self):
        self._hosts_lock = Lock()

    def distance(self, host):
        """
        Returns a measure of how remote a :class:`~.pool.Host` is in
        terms of the :class:`.HostDistance` enums.
        """
        raise NotImplementedError()

    def populate(self, cluster, hosts):
        """
        This method is called to initialize the load balancing
        policy with a set of :class:`.Host` instances before its
        first use.  The `cluster` parameter is an instance of
        :class:`.Cluster`.
        """
        raise NotImplementedError()

    def make_query_plan(self, working_keyspace=None, query=None):
        """
        Given a :class:`~.query.Statement` instance, return a iterable
        of :class:`.Host` instances which should be queried in that
        order.  A generator may work well for custom implementations
        of this method.

        Note that the `query` argument may be :const:`None` when preparing
        statements.

        `working_keyspace` should be the string name of the current keyspace,
        as set through :meth:`.Session.set_keyspace()` or with a ``USE``
        statement.
        """
        raise NotImplementedError()

    def check_supported(self):
        """
        This will be called after the cluster Metadata has been initialized.
        If the load balancing policy implementation cannot be supported for
        some reason (such as a missing C extension), this is the point at
        which it should raise an exception.
        """
        pass


class RoundRobinPolicy(LoadBalancingPolicy):
    """
    A subclass of :class:`.LoadBalancingPolicy` which evenly
    distributes queries across all nodes in the cluster,
    regardless of what datacenter the nodes may be in.

    This load balancing policy is used by default.
    """
    _live_hosts = frozenset(())

    def populate(self, cluster, hosts):
        self._live_hosts = frozenset(hosts)
        if len(hosts) <= 1:
            self._position = 0
        else:
            self._position = randint(0, len(hosts) - 1)

    def distance(self, host):
        return HostDistance.LOCAL

    def make_query_plan(self, working_keyspace=None, query=None):
        # not thread-safe, but we don't care much about lost increments
        # for the purposes of load balancing
        pos = self._position
        self._position += 1

        hosts = self._live_hosts
        length = len(hosts)
        if length:
            pos %= length
            return list(islice(cycle(hosts), pos, pos + length))
        else:
            return []

    def on_up(self, host):
        with self._hosts_lock:
            self._live_hosts = self._live_hosts.union((host, ))

    def on_down(self, host):
        with self._hosts_lock:
            self._live_hosts = self._live_hosts.difference((host, ))

    def on_add(self, host):
        with self._hosts_lock:
            self._live_hosts = self._live_hosts.union((host, ))

    def on_remove(self, host):
        with self._hosts_lock:
            self._live_hosts = self._live_hosts.difference((host, ))


class DCAwareRoundRobinPolicy(LoadBalancingPolicy):
    """
    Similar to :class:`.RoundRobinPolicy`, but prefers hosts
    in the local datacenter and only uses nodes in remote
    datacenters as a last resort.
    """

    local_dc = None
    used_hosts_per_remote_dc = 0

    def __init__(self, local_dc, used_hosts_per_remote_dc=0):
        """
        The `local_dc` parameter should be the name of the datacenter
        (such as is reported by ``nodetool ring``) that should
        be considered local.

        `used_hosts_per_remote_dc` controls how many nodes in
        each remote datacenter will have connections opened
        against them. In other words, `used_hosts_per_remote_dc` hosts
        will be considered :attr:`~.HostDistance.REMOTE` and the
        rest will be considered :attr:`~.HostDistance.IGNORED`.
        By default, all remote hosts are ignored.
        """
        self.local_dc = local_dc
        self.used_hosts_per_remote_dc = used_hosts_per_remote_dc
        self._dc_live_hosts = {}
        LoadBalancingPolicy.__init__(self)

    def _dc(self, host):
        return host.datacenter or self.local_dc

    def populate(self, cluster, hosts):
        for dc, dc_hosts in groupby(hosts, lambda h: self._dc(h)):
            self._dc_live_hosts[dc] = tuple(set(dc_hosts))

        # position is currently only used for local hosts
        local_live = self._dc_live_hosts.get(self.local_dc)
        if not local_live:
            self._position = 0
        elif len(local_live) == 1:
            self._position = 0
        else:
            self._position = randint(0, len(local_live) - 1)

    def distance(self, host):
        dc = self._dc(host)
        if dc == self.local_dc:
            return HostDistance.LOCAL

        if not self.used_hosts_per_remote_dc:
            return HostDistance.IGNORED
        else:
            dc_hosts = self._dc_live_hosts.get(dc)
            if not dc_hosts:
                return HostDistance.IGNORED

            if host in list(dc_hosts)[:self.used_hosts_per_remote_dc]:
                return HostDistance.REMOTE
            else:
                return HostDistance.IGNORED

    def make_query_plan(self, working_keyspace=None, query=None):
        # not thread-safe, but we don't care much about lost increments
        # for the purposes of load balancing
        pos = self._position
        self._position += 1

        local_live = self._dc_live_hosts.get(self.local_dc, ())
        pos = (pos % len(local_live)) if local_live else 0
        for host in islice(cycle(local_live), pos, pos + len(local_live)):
            yield host

        for dc, current_dc_hosts in six.iteritems(self._dc_live_hosts):
            if dc == self.local_dc:
                continue

            for host in current_dc_hosts[:self.used_hosts_per_remote_dc]:
                yield host

    def on_up(self, host):
        dc = self._dc(host)
        with self._hosts_lock:
            current_hosts = self._dc_live_hosts.setdefault(dc, ())
            if host not in current_hosts:
                self._dc_live_hosts[dc] = current_hosts + (host, )

    def on_down(self, host):
        dc = self._dc(host)
        with self._hosts_lock:
            current_hosts = self._dc_live_hosts.setdefault(dc, ())
            if host in current_hosts:
                self._dc_live_hosts[dc] = tuple(h for h in current_hosts if h != host)

    def on_add(self, host):
        dc = self._dc(host)
        with self._hosts_lock:
            current_hosts = self._dc_live_hosts.setdefault(dc, ())
            if host not in current_hosts:
                self._dc_live_hosts[dc] = current_hosts + (host, )

    def on_remove(self, host):
        dc = self._dc(host)
        with self._hosts_lock:
            current_hosts = self._dc_live_hosts.setdefault(dc, ())
            if host in current_hosts:
                self._dc_live_hosts[dc] = tuple(h for h in current_hosts if h != host)


class TokenAwarePolicy(LoadBalancingPolicy):
    """
    A :class:`.LoadBalancingPolicy` wrapper that adds token awareness to
    a child policy.

    This alters the child policy's behavior so that it first attempts to
    send queries to :attr:`~.HostDistance.LOCAL` replicas (as determined
    by the child policy) based on the :class:`.Statement`'s
    :attr:`~.Statement.routing_key`.  Once those hosts are exhausted, the
    remaining hosts in the child policy's query plan will be used.

    If no :attr:`~.Statement.routing_key` is set on the query, the child
    policy's query plan will be used as is.
    """

    _child_policy = None
    _cluster_metadata = None

    def __init__(self, child_policy):
        self._child_policy = child_policy

    def populate(self, cluster, hosts):
        self._cluster_metadata = cluster.metadata
        self._child_policy.populate(cluster, hosts)

    def check_supported(self):
        if not self._cluster_metadata.can_support_partitioner():
            raise Exception(
                '%s cannot be used with the cluster partitioner (%s) because '
                'the relevant C extension for this driver was not compiled. '
                'See the installation instructions for details on building '
                'and installing the C extensions.' % (self.__class__.__name__,
                self._cluster_metadata.partitioner))

    def distance(self, *args, **kwargs):
        return self._child_policy.distance(*args, **kwargs)

    def make_query_plan(self, working_keyspace=None, query=None):
        if query and query.keyspace:
            keyspace = query.keyspace
        else:
            keyspace = working_keyspace

        child = self._child_policy
        if query is None:
            for host in child.make_query_plan(keyspace, query):
                yield host
        else:
            routing_key = query.routing_key
            if routing_key is None:
                for host in child.make_query_plan(keyspace, query):
                    yield host
            else:
                replicas = self._cluster_metadata.get_replicas(keyspace, routing_key)
                for replica in replicas:
                    if replica.is_up and \
                            child.distance(replica) == HostDistance.LOCAL:
                        yield replica

                for host in child.make_query_plan(keyspace, query):
                    # skip if we've already listed this host
                    if host not in replicas or \
                            child.distance(host) == HostDistance.REMOTE:
                        yield host

    def on_up(self, *args, **kwargs):
        return self._child_policy.on_up(*args, **kwargs)

    def on_down(self, *args, **kwargs):
        return self._child_policy.on_down(*args, **kwargs)

    def on_add(self, *args, **kwargs):
        return self._child_policy.on_add(*args, **kwargs)

    def on_remove(self, *args, **kwargs):
        return self._child_policy.on_remove(*args, **kwargs)


class WhiteListRoundRobinPolicy(RoundRobinPolicy):
    """
    A subclass of :class:`.RoundRobinPolicy` which evenly
    distributes queries across all nodes in the cluster,
    regardless of what datacenter the nodes may be in, but
    only if that node exists in the list of allowed nodes

    This policy is addresses the issue described in
    https://datastax-oss.atlassian.net/browse/JAVA-145
    Where connection errors occur when connection
    attempts are made to private IP addresses remotely
    """
    def __init__(self, hosts):
        """
        The `hosts` parameter should be a sequence of hosts to permit
        connections to.
        """
        self._allowed_hosts = hosts
        RoundRobinPolicy.__init__(self)

    def populate(self, cluster, hosts):
        self._live_hosts = frozenset(h for h in hosts if h.address in self._allowed_hosts)

        if len(hosts) <= 1:
            self._position = 0
        else:
            self._position = randint(0, len(hosts) - 1)

    def distance(self, host):
        if host.address in self._allowed_hosts:
            return HostDistance.LOCAL
        else:
            return HostDistance.IGNORED

    def on_up(self, host):
        if host.address in self._allowed_hosts:
            RoundRobinPolicy.on_up(self, host)

    def on_add(self, host):
        if host.address in self._allowed_hosts:
            RoundRobinPolicy.on_add(self, host)


class ConvictionPolicy(object):
    """
    A policy which decides when hosts should be considered down
    based on the types of failures and the number of failures.

    If custom behavior is needed, this class may be subclassed.
    """

    def __init__(self, host):
        """
        `host` is an instance of :class:`.Host`.
        """
        self.host = host

    def add_failure(self, connection_exc):
        """
        Implementations should return :const:`True` if the host should be
        convicted, :const:`False` otherwise.
        """
        raise NotImplementedError()

    def reset(self):
        """
        Implementations should clear out any convictions or state regarding
        the host.
        """
        raise NotImplementedError()


class SimpleConvictionPolicy(ConvictionPolicy):
    """
    The default implementation of :class:`ConvictionPolicy`,
    which simply marks a host as down after the first failure
    of any kind.
    """

    def add_failure(self, connection_exc):
        return True

    def reset(self):
        pass


class ReconnectionPolicy(object):
    """
    This class and its subclasses govern how frequently an attempt is made
    to reconnect to nodes that are marked as dead.

    If custom behavior is needed, this class may be subclassed.
    """

    def new_schedule(self):
        """
        This should return a finite or infinite iterable of delays (each as a
        floating point number of seconds) inbetween each failed reconnection
        attempt.  Note that if the iterable is finite, reconnection attempts
        will cease once the iterable is exhausted.
        """
        raise NotImplementedError()


class ConstantReconnectionPolicy(ReconnectionPolicy):
    """
    A :class:`.ReconnectionPolicy` subclass which sleeps for a fixed delay
    inbetween each reconnection attempt.
    """

    def __init__(self, delay, max_attempts=64):
        """
        `delay` should be a floating point number of seconds to wait inbetween
        each attempt.

        `max_attempts` should be a total number of attempts to be made before
        giving up, or :const:`None` to continue reconnection attempts forever.
        The default is 64.
        """
        if delay < 0:
            raise ValueError("delay must not be negative")
        if max_attempts < 0:
            raise ValueError("max_attempts must not be negative")

        self.delay = delay
        self.max_attempts = max_attempts

    def new_schedule(self):
        return repeat(self.delay, self.max_attempts)


class ExponentialReconnectionPolicy(ReconnectionPolicy):
    """
    A :class:`.ReconnectionPolicy` subclass which exponentially increases
    the length of the delay inbetween each reconnection attempt up to
    a set maximum delay.
    """

    def __init__(self, base_delay, max_delay):
        """
        `base_delay` and `max_delay` should be in floating point units of
        seconds.
        """
        if base_delay < 0 or max_delay < 0:
            raise ValueError("Delays may not be negative")

        if max_delay < base_delay:
            raise ValueError("Max delay must be greater than base delay")

        self.base_delay = base_delay
        self.max_delay = max_delay

    def new_schedule(self):
        return (min(self.base_delay * (2 ** i), self.max_delay) for i in range(64))


class WriteType(object):
    """
    For usage with :class:`.RetryPolicy`, this describe a type
    of write operation.
    """

    SIMPLE = 0
    """
    A write to a single partition key. Such writes are guaranteed to be atomic
    and isolated.
    """

    BATCH = 1
    """
    A write to multiple partition keys that used the distributed batch log to
    ensure atomicity.
    """

    UNLOGGED_BATCH = 2
    """
    A write to multiple partition keys that did not use the distributed batch
    log. Atomicity for such writes is not guaranteed.
    """

    COUNTER = 3
    """
    A counter write (for one or multiple partition keys). Such writes should
    not be replayed in order to avoid overcount.
    """

    BATCH_LOG = 4
    """
    The initial write to the distributed batch log that Cassandra performs
    internally before a BATCH write.
    """

WriteType.name_to_value = {
    'SIMPLE': WriteType.SIMPLE,
    'BATCH': WriteType.BATCH,
    'UNLOGGED_BATCH': WriteType.UNLOGGED_BATCH,
    'COUNTER': WriteType.COUNTER,
    'BATCH_LOG': WriteType.BATCH_LOG,
}


class RetryPolicy(object):
    """
    A policy that describes whether to retry, rethrow, or ignore timeout
    and unavailable failures.

    To specify a default retry policy, set the
    :attr:`.Cluster.default_retry_policy` attribute to an instance of this
    class or one of its subclasses.

    To specify a retry policy per query, set the :attr:`.Statement.retry_policy`
    attribute to an instance of this class or one of its subclasses.

    If custom behavior is needed for retrying certain operations,
    this class may be subclassed.
    """

    RETRY = 0
    """
    This should be returned from the below methods if the operation
    should be retried on the same connection.
    """

    RETHROW = 1
    """
    This should be returned from the below methods if the failure
    should be propagated and no more retries attempted.
    """

    IGNORE = 2
    """
    This should be returned from the below methods if the failure
    should be ignored but no more retries should be attempted.
    """

    def on_read_timeout(self, query, consistency, required_responses,
                        received_responses, data_retrieved, retry_num):
        """
        This is called when a read operation times out from the coordinator's
        perspective (i.e. a replica did not respond to the coordinator in time).
        It should return a tuple with two items: one of the class enums (such
        as :attr:`.RETRY`) and a :class:`.ConsistencyLevel` to retry the
        operation at or :const:`None` to keep the same consistency level.

        `query` is the :class:`.Statement` that timed out.

        `consistency` is the :class:`.ConsistencyLevel` that the operation was
        attempted at.

        The `required_responses` and `received_responses` parameters describe
        how many replicas needed to respond to meet the requested consistency
        level and how many actually did respond before the coordinator timed
        out the request. `data_retrieved` is a boolean indicating whether
        any of those responses contained data (as opposed to just a digest).

        `retry_num` counts how many times the operation has been retried, so
        the first time this method is called, `retry_num` will be 0.

        By default, operations will be retried at most once, and only if
        a sufficient number of replicas responded (with data digests).
        """
        if retry_num != 0:
            return (self.RETHROW, None)
        elif received_responses >= required_responses and not data_retrieved:
            return (self.RETRY, consistency)
        else:
            return (self.RETHROW, None)

    def on_write_timeout(self, query, consistency, write_type,
                         required_responses, received_responses, retry_num):
        """
        This is called when a write operation times out from the coordinator's
        perspective (i.e. a replica did not respond to the coordinator in time).

        `query` is the :class:`.Statement` that timed out.

        `consistency` is the :class:`.ConsistencyLevel` that the operation was
        attempted at.

        `write_type` is one of the :class:`.WriteType` enums describing the
        type of write operation.

        The `required_responses` and `received_responses` parameters describe
        how many replicas needed to acknowledge the write to meet the requested
        consistency level and how many replicas actually did acknowledge the
        write before the coordinator timed out the request.

        `retry_num` counts how many times the operation has been retried, so
        the first time this method is called, `retry_num` will be 0.

        By default, failed write operations will retried at most once, and
        they will only be retried if the `write_type` was
        :attr:`~.WriteType.BATCH_LOG`.
        """
        if retry_num != 0:
            return (self.RETHROW, None)
        elif write_type == WriteType.BATCH_LOG:
            return (self.RETRY, consistency)
        else:
            return (self.RETHROW, None)

    def on_unavailable(self, query, consistency, required_replicas, alive_replicas, retry_num):
        """
        This is called when the coordinator node determines that a read or
        write operation cannot be successful because the number of live
        replicas are too low to meet the requested :class:`.ConsistencyLevel`.
        This means that the read or write operation was never forwared to
        any replicas.

        `query` is the :class:`.Statement` that failed.

        `consistency` is the :class:`.ConsistencyLevel` that the operation was
        attempted at.

        `required_replicas` is the number of replicas that would have needed to
        acknowledge the operation to meet the requested consistency level.
        `alive_replicas` is the number of replicas that the coordinator
        considered alive at the time of the request.

        `retry_num` counts how many times the operation has been retried, so
        the first time this method is called, `retry_num` will be 0.

        By default, no retries will be attempted and the error will be re-raised.
        """
        return (self.RETHROW, None)


class FallthroughRetryPolicy(RetryPolicy):
    """
    A retry policy that never retries and always propagates failures to
    the application.
    """

    def on_read_timeout(self, *args, **kwargs):
        return (self.RETHROW, None)

    def on_write_timeout(self, *args, **kwargs):
        return (self.RETHROW, None)

    def on_unavailable(self, *args, **kwargs):
        return (self.RETHROW, None)


class DowngradingConsistencyRetryPolicy(RetryPolicy):
    """
    A retry policy that sometimes retries with a lower consistency level than
    the one initially requested.

    **BEWARE**: This policy may retry queries using a lower consistency
    level than the one initially requested. By doing so, it may break
    consistency guarantees. In other words, if you use this retry policy,
    there are cases (documented below) where a read at :attr:`~.QUORUM`
    *may not* see a preceding write at :attr:`~.QUORUM`. Do not use this
    policy unless you have understood the cases where this can happen and
    are ok with that. It is also recommended to subclass this class so
    that queries that required a consistency level downgrade can be
    recorded (so that repairs can be made later, etc).

    This policy implements the same retries as :class:`.RetryPolicy`,
    but on top of that, it also retries in the following cases:

    * On a read timeout: if the number of replicas that responded is
      greater than one but lower than is required by the requested
      consistency level, the operation is retried at a lower consistency
      level.
    * On a write timeout: if the operation is an :attr:`~.UNLOGGED_BATCH`
      and at least one replica acknowledged the write, the operation is
      retried at a lower consistency level.  Furthermore, for other
      write types, if at least one replica acknowledged the write, the
      timeout is ignored.
    * On an unavailable exception: if at least one replica is alive, the
      operation is retried at a lower consistency level.

    The reasoning behind this retry policy is as follows: if, based
    on the information the Cassandra coordinator node returns, retrying the
    operation with the initially requested consistency has a chance to
    succeed, do it. Otherwise, if based on that information we know the
    initially requested consistency level cannot be achieved currently, then:

    * For writes, ignore the exception (thus silently failing the
      consistency requirement) if we know the write has been persisted on at
      least one replica.
    * For reads, try reading at a lower consistency level (thus silently
      failing the consistency requirement).

    In other words, this policy implements the idea that if the requested
    consistency level cannot be achieved, the next best thing for writes is
    to make sure the data is persisted, and that reading something is better
    than reading nothing, even if there is a risk of reading stale data.
    """
    def _pick_consistency(self, num_responses):
        if num_responses >= 3:
            return (self.RETRY, ConsistencyLevel.THREE)
        elif num_responses >= 2:
            return (self.RETRY, ConsistencyLevel.TWO)
        elif num_responses >= 1:
            return (self.RETRY, ConsistencyLevel.ONE)
        else:
            return (self.RETHROW, None)

    def on_read_timeout(self, query, consistency, required_responses,
                        received_responses, data_retrieved, retry_num):
        if retry_num != 0:
            return (self.RETHROW, None)
        elif received_responses < required_responses:
            return self._pick_consistency(received_responses)
        elif not data_retrieved:
            return (self.RETRY, consistency)
        else:
            return (self.RETHROW, None)

    def on_write_timeout(self, query, consistency, write_type,
                         required_responses, received_responses, retry_num):
        if retry_num != 0:
            return (self.RETHROW, None)
        elif write_type in (WriteType.SIMPLE, WriteType.BATCH, WriteType.COUNTER):
            return (self.IGNORE, None)
        elif write_type == WriteType.UNLOGGED_BATCH:
            return self._pick_consistency(received_responses)
        elif write_type == WriteType.BATCH_LOG:
            return (self.RETRY, consistency)
        else:
            return (self.RETHROW, None)

    def on_unavailable(self, query, consistency, required_replicas, alive_replicas, retry_num):
        if retry_num != 0:
            return (self.RETHROW, None)
        else:
            return self._pick_consistency(alive_replicas)

########NEW FILE########
__FILENAME__ = pool
# Copyright 2013-2014 DataStax, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Connection pooling and host management.
"""

import logging
import re
import socket
import time
from threading import RLock, Condition
import weakref
try:
    from weakref import WeakSet
except ImportError:
    from cassandra.util import WeakSet  # NOQA

from cassandra import AuthenticationFailed
from cassandra.connection import MAX_STREAM_PER_CONNECTION, ConnectionException

log = logging.getLogger(__name__)


class NoConnectionsAvailable(Exception):
    """
    All existing connections to a given host are busy, or there are
    no open connections.
    """
    pass


# example matches:
# 1.0.0
# 1.0.0-beta1
# 2.0-SNAPSHOT
version_re = re.compile(r"(?P<major>\d+)\.(?P<minor>\d+)(?:\.(?P<patch>\d+))?(?:-(?P<label>\w+))?")


class Host(object):
    """
    Represents a single Cassandra node.
    """

    address = None
    """
    The IP address or hostname of the node.
    """

    conviction_policy = None
    """
    A :class:`~.ConvictionPolicy` instance for determining when this node should
    be marked up or down.
    """

    is_up = None
    """
    :const:`True` if the node is considered up, :const:`False` if it is
    considered down, and :const:`None` if it is not known if the node is
    up or down.
    """

    version = None
    """
    A tuple representing the Cassandra version for this host.  This will
    remain as :const:`None` if the version is unknown.
    """

    _datacenter = None
    _rack = None
    _reconnection_handler = None
    lock = None

    _currently_handling_node_up = False

    def __init__(self, inet_address, conviction_policy_factory, datacenter=None, rack=None):
        if inet_address is None:
            raise ValueError("inet_address may not be None")
        if conviction_policy_factory is None:
            raise ValueError("conviction_policy_factory may not be None")

        self.address = inet_address
        self.conviction_policy = conviction_policy_factory(self)
        self.set_location_info(datacenter, rack)
        self.lock = RLock()

    @property
    def datacenter(self):
        """ The datacenter the node is in.  """
        return self._datacenter

    @property
    def rack(self):
        """ The rack the node is in.  """
        return self._rack

    def set_location_info(self, datacenter, rack):
        """
        Sets the datacenter and rack for this node. Intended for internal
        use (by the control connection, which periodically checks the
        ring topology) only.
        """
        self._datacenter = datacenter
        self._rack = rack

    def set_version(self, version_string):
        match = version_re.match(version_string)
        if match is not None:
            version = [int(match.group('major')), int(match.group('minor')), int(match.group('patch') or 0)]
            if match.group('label'):
                version.append(match.group('label'))
            self.version = tuple(version)

    def set_up(self):
        if not self.is_up:
            log.debug("Host %s is now marked up", self.address)
        self.conviction_policy.reset()
        self.is_up = True

    def set_down(self):
        self.is_up = False

    def signal_connection_failure(self, connection_exc):
        return self.conviction_policy.add_failure(connection_exc)

    def is_currently_reconnecting(self):
        return self._reconnection_handler is not None

    def get_and_set_reconnection_handler(self, new_handler):
        """
        Atomically replaces the reconnection handler for this
        host.  Intended for internal use only.
        """
        with self.lock:
            old = self._reconnection_handler
            self._reconnection_handler = new_handler
            return old

    def __eq__(self, other):
        return self.address == other.address

    def __hash__(self):
        return hash(self.address)

    def __lt__(self, other):
        return self.address < other.address

    def __str__(self):
        return str(self.address)

    def __repr__(self):
        dc = (" %s" % (self._datacenter,)) if self._datacenter else ""
        return "<%s: %s%s>" % (self.__class__.__name__, self.address, dc)


class _ReconnectionHandler(object):
    """
    Abstract class for attempting reconnections with a given
    schedule and scheduler.
    """

    _cancelled = False

    def __init__(self, scheduler, schedule, callback, *callback_args, **callback_kwargs):
        self.scheduler = scheduler
        self.schedule = schedule
        self.callback = callback
        self.callback_args = callback_args
        self.callback_kwargs = callback_kwargs

    def start(self):
        if self._cancelled:
            log.debug("Reconnection handler was cancelled before starting")
            return

        first_delay = next(self.schedule)
        self.scheduler.schedule(first_delay, self.run)

    def run(self):
        if self._cancelled:
            return

        conn = None
        try:
            conn = self.try_reconnect()
        except Exception as exc:
            try:
                next_delay = next(self.schedule)
            except StopIteration:
                # the schedule has been exhausted
                next_delay = None

            # call on_exception for logging purposes even if next_delay is None
            if self.on_exception(exc, next_delay):
                if next_delay is None:
                    log.warn(
                        "Will not continue to retry reconnection attempts "
                        "due to an exhausted retry schedule")
                else:
                    self.scheduler.schedule(next_delay, self.run)
        else:
            if not self._cancelled:
                self.on_reconnection(conn)
                self.callback(*(self.callback_args), **(self.callback_kwargs))
        finally:
            if conn:
                conn.close()

    def cancel(self):
        self._cancelled = True

    def try_reconnect(self):
        """
        Subclasses must implement this method.  It should attempt to
        open a new Connection and return it; if a failure occurs, an
        Exception should be raised.
        """
        raise NotImplementedError()

    def on_reconnection(self, connection):
        """
        Called when a new Connection is successfully opened.  Nothing is
        done by default.
        """
        pass

    def on_exception(self, exc, next_delay):
        """
        Called when an Exception is raised when trying to connect.
        `exc` is the Exception that was raised and `next_delay` is the
        number of seconds (as a float) that the handler will wait before
        attempting to connect again.

        Subclasses should return :const:`False` if no more attempts to
        connection should be made, :const:`True` otherwise.  The default
        behavior is to always retry unless the error is an
        :exc:`.AuthenticationFailed` instance.
        """
        if isinstance(exc, AuthenticationFailed):
            return False
        else:
            return True


class _HostReconnectionHandler(_ReconnectionHandler):

    def __init__(self, host, connection_factory, is_host_addition, on_add, on_up, *args, **kwargs):
        _ReconnectionHandler.__init__(self, *args, **kwargs)
        self.is_host_addition = is_host_addition
        self.on_add = on_add
        self.on_up = on_up
        self.host = host
        self.connection_factory = connection_factory

    def try_reconnect(self):
        return self.connection_factory()

    def on_reconnection(self, connection):
        log.info("Successful reconnection to %s, marking node up if it isn't already", self.host)
        if self.is_host_addition:
            self.on_add(self.host)
        else:
            self.on_up(self.host)

    def on_exception(self, exc, next_delay):
        if isinstance(exc, AuthenticationFailed):
            return False
        else:
            log.warning("Error attempting to reconnect to %s, scheduling retry in %s seconds: %s",
                        self.host, next_delay, exc)
            log.debug("Reconnection error details", exc_info=True)
            return True


_MAX_SIMULTANEOUS_CREATION = 1
_MIN_TRASH_INTERVAL = 10


class HostConnectionPool(object):

    host = None
    host_distance = None

    is_shutdown = False
    open_count = 0
    _scheduled_for_creation = 0
    _next_trash_allowed_at = 0

    def __init__(self, host, host_distance, session):
        self.host = host
        self.host_distance = host_distance

        self._session = weakref.proxy(session)
        self._lock = RLock()
        self._conn_available_condition = Condition()

        log.debug("Initializing new connection pool for host %s", self.host)
        core_conns = session.cluster.get_core_connections_per_host(host_distance)
        self._connections = [session.cluster.connection_factory(host.address)
                             for i in range(core_conns)]

        if session.keyspace:
            for conn in self._connections:
                conn.set_keyspace_blocking(session.keyspace)

        self._trash = set()
        self._next_trash_allowed_at = time.time()
        self.open_count = core_conns
        log.debug("Finished initializing new connection pool for host %s", self.host)

    def borrow_connection(self, timeout):
        if self.is_shutdown:
            raise ConnectionException(
                "Pool for %s is shutdown" % (self.host,), self.host)

        conns = self._connections
        if not conns:
            # handled specially just for simpler code
            log.debug("Detected empty pool, opening core conns to %s", self.host)
            core_conns = self._session.cluster.get_core_connections_per_host(self.host_distance)
            with self._lock:
                # we check the length of self._connections again
                # along with self._scheduled_for_creation while holding the lock
                # in case multiple threads hit this condition at the same time
                to_create = core_conns - (len(self._connections) + self._scheduled_for_creation)
                for i in range(to_create):
                    self._scheduled_for_creation += 1
                    self._session.submit(self._create_new_connection)

            # in_flight is incremented by wait_for_conn
            conn = self._wait_for_conn(timeout)
            return conn
        else:
            # note: it would be nice to push changes to these config settings
            # to pools instead of doing a new lookup on every
            # borrow_connection() call
            max_reqs = self._session.cluster.get_max_requests_per_connection(self.host_distance)
            max_conns = self._session.cluster.get_max_connections_per_host(self.host_distance)

            least_busy = min(conns, key=lambda c: c.in_flight)
            # to avoid another thread closing this connection while
            # trashing it (through the return_connection process), hold
            # the connection lock from this point until we've incremented
            # its in_flight count
            need_to_wait = False
            with least_busy.lock:

                if least_busy.in_flight >= MAX_STREAM_PER_CONNECTION:
                    # once we release the lock, wait for another connection
                    need_to_wait = True
                else:
                    least_busy.in_flight += 1

            if need_to_wait:
                # wait_for_conn will increment in_flight on the conn
                least_busy = self._wait_for_conn(timeout)

            # if we have too many requests on this connection but we still
            # have space to open a new connection against this host, go ahead
            # and schedule the creation of a new connection
            if least_busy.in_flight >= max_reqs and len(self._connections) < max_conns:
                self._maybe_spawn_new_connection()

            return least_busy

    def _maybe_spawn_new_connection(self):
        with self._lock:
            if self._scheduled_for_creation >= _MAX_SIMULTANEOUS_CREATION:
                return
            if self.open_count >= self._session.cluster.get_max_connections_per_host(self.host_distance):
                return
            self._scheduled_for_creation += 1

        log.debug("Submitting task for creation of new Connection to %s", self.host)
        self._session.submit(self._create_new_connection)

    def _create_new_connection(self):
        try:
            self._add_conn_if_under_max()
        except (ConnectionException, socket.error) as exc:
            log.warning("Failed to create new connection to %s: %s", self.host, exc)
        except Exception:
            log.exception("Unexpectedly failed to create new connection")
        finally:
            with self._lock:
                self._scheduled_for_creation -= 1

    def _add_conn_if_under_max(self):
        max_conns = self._session.cluster.get_max_connections_per_host(self.host_distance)
        with self._lock:
            if self.is_shutdown:
                return False

            if self.open_count >= max_conns:
                return False

            self.open_count += 1

        log.debug("Going to open new connection to host %s", self.host)
        try:
            conn = self._session.cluster.connection_factory(self.host.address)
            if self._session.keyspace:
                conn.set_keyspace_blocking(self._session.keyspace)
            self._next_trash_allowed_at = time.time() + _MIN_TRASH_INTERVAL
            with self._lock:
                new_connections = self._connections[:] + [conn]
                self._connections = new_connections
            log.debug("Added new connection (%s) to pool for host %s, signaling availablility",
                      id(conn), self.host)
            self._signal_available_conn()
            return True
        except (ConnectionException, socket.error) as exc:
            log.warning("Failed to add new connection to pool for host %s: %s", self.host, exc)
            with self._lock:
                self.open_count -= 1
            if self._session.cluster.signal_connection_failure(self.host, exc, is_host_addition=False):
                self.shutdown()
            return False
        except AuthenticationFailed:
            with self._lock:
                self.open_count -= 1
            return False

    def _await_available_conn(self, timeout):
        with self._conn_available_condition:
            self._conn_available_condition.wait(timeout)

    def _signal_available_conn(self):
        with self._conn_available_condition:
            self._conn_available_condition.notify()

    def _signal_all_available_conn(self):
        with self._conn_available_condition:
            self._conn_available_condition.notify_all()

    def _wait_for_conn(self, timeout):
        start = time.time()
        remaining = timeout

        while remaining > 0:
            # wait on our condition for the possibility that a connection
            # is useable
            self._await_available_conn(remaining)

            # self.shutdown() may trigger the above Condition
            if self.is_shutdown:
                raise ConnectionException("Pool is shutdown")

            conns = self._connections
            if conns:
                least_busy = min(conns, key=lambda c: c.in_flight)
                with least_busy.lock:
                    if least_busy.in_flight < MAX_STREAM_PER_CONNECTION:
                        least_busy.in_flight += 1
                        return least_busy

            remaining = timeout - (time.time() - start)

        raise NoConnectionsAvailable()

    def return_connection(self, connection):
        with connection.lock:
            connection.in_flight -= 1
            in_flight = connection.in_flight

        if connection.is_defunct or connection.is_closed:
            log.debug("Defunct or closed connection (%s) returned to pool, potentially "
                      "marking host %s as down", id(connection), self.host)
            is_down = self._session.cluster.signal_connection_failure(
                    self.host, connection.last_error, is_host_addition=False)
            if is_down:
                self.shutdown()
            else:
                self._replace(connection)
        else:
            if connection in self._trash:
                with connection.lock:
                    if connection.in_flight == 0:
                        with self._lock:
                            if connection in self._trash:
                                self._trash.remove(connection)
                        log.debug("Closing trashed connection (%s) to %s", id(connection), self.host)
                        connection.close()
                return

            core_conns = self._session.cluster.get_core_connections_per_host(self.host_distance)
            min_reqs = self._session.cluster.get_min_requests_per_connection(self.host_distance)
            # we can use in_flight here without holding the connection lock
            # because the fact that in_flight dipped below the min at some
            # point is enough to start the trashing procedure
            if len(self._connections) > core_conns and in_flight <= min_reqs and \
                    time.time() >= self._next_trash_allowed_at:
                self._maybe_trash_connection(connection)
            else:
                self._signal_available_conn()

    def _maybe_trash_connection(self, connection):
        core_conns = self._session.cluster.get_core_connections_per_host(self.host_distance)
        did_trash = False
        with self._lock:
            if connection not in self._connections:
                return

            if self.open_count > core_conns:
                did_trash = True
                self.open_count -= 1
                new_connections = self._connections[:]
                new_connections.remove(connection)
                self._connections = new_connections

                with connection.lock:
                    if connection.in_flight == 0:
                        log.debug("Skipping trash and closing unused connection (%s) to %s", id(connection), self.host)
                        connection.close()

                        # skip adding it to the trash if we're already closing it
                        return

                self._trash.add(connection)

        if did_trash:
            self._next_trash_allowed_at = time.time() + _MIN_TRASH_INTERVAL
            log.debug("Trashed connection (%s) to %s", id(connection), self.host)

    def _replace(self, connection):
        should_replace = False
        with self._lock:
            if connection in self._connections:
                new_connections = self._connections[:]
                new_connections.remove(connection)
                self._connections = new_connections
                self.open_count -= 1
                should_replace = True

        if should_replace:
            log.debug("Replacing connection (%s) to %s", id(connection), self.host)

            def close_and_replace():
                connection.close()
                self._add_conn_if_under_max()

            self._session.submit(close_and_replace)
        else:
            # just close it
            log.debug("Closing connection (%s) to %s", id(connection), self.host)
            connection.close()

    def shutdown(self):
        with self._lock:
            if self.is_shutdown:
                return
            else:
                self.is_shutdown = True

        self._signal_all_available_conn()
        for conn in self._connections:
            conn.close()
            self.open_count -= 1

        for conn in self._trash:
            conn.close()

    def ensure_core_connections(self):
        if self.is_shutdown:
            return

        core_conns = self._session.cluster.get_core_connections_per_host(self.host_distance)
        with self._lock:
            to_create = core_conns - (len(self._connections) + self._scheduled_for_creation)
            for i in range(to_create):
                self._scheduled_for_creation += 1
                self._session.submit(self._create_new_connection)

    def _set_keyspace_for_all_conns(self, keyspace, callback):
        """
        Asynchronously sets the keyspace for all connections.  When all
        connections have been set, `callback` will be called with two
        arguments: this pool, and a list of any errors that occurred.
        """
        remaining_callbacks = set(self._connections)
        errors = []

        if not remaining_callbacks:
            callback(self, errors)
            return

        def connection_finished_setting_keyspace(conn, error):
            remaining_callbacks.remove(conn)
            if error:
                errors.append(error)

            if not remaining_callbacks:
                callback(self, errors)

        for conn in self._connections:
            conn.set_keyspace_async(keyspace, connection_finished_setting_keyspace)

    def get_state(self):
        in_flights = ", ".join([str(c.in_flight) for c in self._connections])
        return "shutdown: %s, open_count: %d, in_flights: %s" % (self.is_shutdown, self.open_count, in_flights)

########NEW FILE########
__FILENAME__ = protocol
# Copyright 2013-2014 DataStax, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import logging
import socket
from uuid import UUID

import six
from six.moves import range

from cassandra import (Unavailable, WriteTimeout, ReadTimeout,
                       AlreadyExists, InvalidRequest, Unauthorized,
                       UnsupportedOperation)
from cassandra.marshal import (int32_pack, int32_unpack, uint16_pack, uint16_unpack,
                               int8_pack, int8_unpack, header_pack)
from cassandra.cqltypes import (AsciiType, BytesType, BooleanType,
                                CounterColumnType, DateType, DecimalType,
                                DoubleType, FloatType, Int32Type,
                                InetAddressType, IntegerType, ListType,
                                LongType, MapType, SetType, TimeUUIDType,
                                UTF8Type, UUIDType, lookup_casstype)
from cassandra.policies import WriteType

log = logging.getLogger(__name__)


class NotSupportedError(Exception):
    pass


class InternalError(Exception):
    pass


HEADER_DIRECTION_FROM_CLIENT = 0x00
HEADER_DIRECTION_TO_CLIENT = 0x80
HEADER_DIRECTION_MASK = 0x80

COMPRESSED_FLAG = 0x01
TRACING_FLAG = 0x02

_message_types_by_name = {}
_message_types_by_opcode = {}


class _RegisterMessageType(type):
    def __init__(cls, name, bases, dct):
        if not name.startswith('_'):
            _message_types_by_name[cls.name] = cls
            _message_types_by_opcode[cls.opcode] = cls


@six.add_metaclass(_RegisterMessageType)
class _MessageType(object):

    tracing = False

    def to_binary(self, stream_id, protocol_version, compression=None):
        body = six.BytesIO()
        self.send_body(body, protocol_version)
        body = body.getvalue()

        flags = 0
        if compression and len(body) > 0:
            body = compression(body)
            flags |= COMPRESSED_FLAG
        if self.tracing:
            flags |= TRACING_FLAG

        msg = six.BytesIO()
        write_header(
            msg,
            protocol_version | HEADER_DIRECTION_FROM_CLIENT,
            flags, stream_id, self.opcode, len(body)
        )
        msg.write(body)

        return msg.getvalue()

    def __repr__(self):
        return '<%s(%s)>' % (self.__class__.__name__, ', '.join('%s=%r' % i for i in _get_params(self)))


def _get_params(message_obj):
    base_attrs = dir(_MessageType)
    return (
        (n, a) for n, a in message_obj.__dict__.items()
        if n not in base_attrs and not n.startswith('_') and not callable(a)
    )


def decode_response(stream_id, flags, opcode, body, decompressor=None):
    if flags & COMPRESSED_FLAG:
        if decompressor is None:
            raise Exception("No de-compressor available for compressed frame!")
        body = decompressor(body)
        flags ^= COMPRESSED_FLAG

    body = six.BytesIO(body)
    if flags & TRACING_FLAG:
        trace_id = UUID(bytes=body.read(16))
        flags ^= TRACING_FLAG
    else:
        trace_id = None

    if flags:
        log.warning("Unknown protocol flags set: %02x. May cause problems.", flags)

    msg_class = _message_types_by_opcode[opcode]
    msg = msg_class.recv_body(body)
    msg.stream_id = stream_id
    msg.trace_id = trace_id
    return msg


error_classes = {}


class ErrorMessage(_MessageType, Exception):
    opcode = 0x00
    name = 'ERROR'
    summary = 'Unknown'

    def __init__(self, code, message, info):
        self.code = code
        self.message = message
        self.info = info

    @classmethod
    def recv_body(cls, f):
        code = read_int(f)
        msg = read_string(f)
        subcls = error_classes.get(code, cls)
        extra_info = subcls.recv_error_info(f)
        return subcls(code=code, message=msg, info=extra_info)

    def summary_msg(self):
        msg = 'code=%04x [%s] message="%s"' \
              % (self.code, self.summary, self.message)
        if self.info is not None:
            msg += (' info=' + repr(self.info))
        return msg

    def __str__(self):
        return '<ErrorMessage %s>' % self.summary_msg()
    __repr__ = __str__

    @staticmethod
    def recv_error_info(f):
        pass

    def to_exception(self):
        return self


class ErrorMessageSubclass(_RegisterMessageType):
    def __init__(cls, name, bases, dct):
        if cls.error_code is not None:  # Server has an error code of 0.
            error_classes[cls.error_code] = cls


@six.add_metaclass(ErrorMessageSubclass)
class ErrorMessageSub(ErrorMessage):
    error_code = None


class RequestExecutionException(ErrorMessageSub):
    pass


class RequestValidationException(ErrorMessageSub):
    pass


class ServerError(ErrorMessageSub):
    summary = 'Server error'
    error_code = 0x0000


class ProtocolException(ErrorMessageSub):
    summary = 'Protocol error'
    error_code = 0x000A


class BadCredentials(ErrorMessageSub):
    summary = 'Bad credentials'
    error_code = 0x0100


class UnavailableErrorMessage(RequestExecutionException):
    summary = 'Unavailable exception'
    error_code = 0x1000

    @staticmethod
    def recv_error_info(f):
        return {
            'consistency': read_consistency_level(f),
            'required_replicas': read_int(f),
            'alive_replicas': read_int(f),
        }

    def to_exception(self):
        return Unavailable(self.summary_msg(), **self.info)


class OverloadedErrorMessage(RequestExecutionException):
    summary = 'Coordinator node overloaded'
    error_code = 0x1001


class IsBootstrappingErrorMessage(RequestExecutionException):
    summary = 'Coordinator node is bootstrapping'
    error_code = 0x1002


class TruncateError(RequestExecutionException):
    summary = 'Error during truncate'
    error_code = 0x1003


class WriteTimeoutErrorMessage(RequestExecutionException):
    summary = 'Timeout during write request'
    error_code = 0x1100

    @staticmethod
    def recv_error_info(f):
        return {
            'consistency': read_consistency_level(f),
            'received_responses': read_int(f),
            'required_responses': read_int(f),
            'write_type': WriteType.name_to_value[read_string(f)],
        }

    def to_exception(self):
        return WriteTimeout(self.summary_msg(), **self.info)


class ReadTimeoutErrorMessage(RequestExecutionException):
    summary = 'Timeout during read request'
    error_code = 0x1200

    @staticmethod
    def recv_error_info(f):
        return {
            'consistency': read_consistency_level(f),
            'received_responses': read_int(f),
            'required_responses': read_int(f),
            'data_retrieved': bool(read_byte(f)),
        }

    def to_exception(self):
        return ReadTimeout(self.summary_msg(), **self.info)


class SyntaxException(RequestValidationException):
    summary = 'Syntax error in CQL query'
    error_code = 0x2000


class UnauthorizedErrorMessage(RequestValidationException):
    summary = 'Unauthorized'
    error_code = 0x2100

    def to_exception(self):
        return Unauthorized(self.summary_msg())


class InvalidRequestException(RequestValidationException):
    summary = 'Invalid query'
    error_code = 0x2200

    def to_exception(self):
        return InvalidRequest(self.summary_msg())


class ConfigurationException(RequestValidationException):
    summary = 'Query invalid because of configuration issue'
    error_code = 0x2300


class PreparedQueryNotFound(RequestValidationException):
    summary = 'Matching prepared statement not found on this node'
    error_code = 0x2500

    @staticmethod
    def recv_error_info(f):
        # return the query ID
        return read_binary_string(f)


class AlreadyExistsException(ConfigurationException):
    summary = 'Item already exists'
    error_code = 0x2400

    @staticmethod
    def recv_error_info(f):
        return {
            'keyspace': read_string(f),
            'table': read_string(f),
        }

    def to_exception(self):
        return AlreadyExists(**self.info)


class StartupMessage(_MessageType):
    opcode = 0x01
    name = 'STARTUP'

    KNOWN_OPTION_KEYS = set((
        'CQL_VERSION',
        'COMPRESSION',
    ))

    def __init__(self, cqlversion, options):
        self.cqlversion = cqlversion
        self.options = options

    def send_body(self, f, protocol_version):
        optmap = self.options.copy()
        optmap['CQL_VERSION'] = self.cqlversion
        write_stringmap(f, optmap)


class ReadyMessage(_MessageType):
    opcode = 0x02
    name = 'READY'

    @classmethod
    def recv_body(cls, f):
        return cls()


class AuthenticateMessage(_MessageType):
    opcode = 0x03
    name = 'AUTHENTICATE'

    def __init__(self, authenticator):
        self.authenticator = authenticator

    @classmethod
    def recv_body(cls, f):
        authname = read_string(f)
        return cls(authenticator=authname)


class CredentialsMessage(_MessageType):
    opcode = 0x04
    name = 'CREDENTIALS'

    def __init__(self, creds):
        self.creds = creds

    def send_body(self, f, protocol_version):
        if protocol_version > 1:
            raise UnsupportedOperation(
                "Credentials-based authentication is not supported with "
                "protocol version 2 or higher.  Use the SASL authentication "
                "mechanism instead.")
        write_short(f, len(self.creds))
        for credkey, credval in self.creds.items():
            write_string(f, credkey)
            write_string(f, credval)


class AuthChallengeMessage(_MessageType):
    opcode = 0x0E
    name = 'AUTH_CHALLENGE'

    def __init__(self, challenge):
        self.challenge = challenge

    @classmethod
    def recv_body(cls, f):
        return cls(read_longstring(f))


class AuthResponseMessage(_MessageType):
    opcode = 0x0F
    name = 'AUTH_RESPONSE'

    def __init__(self, response):
        self.response = response

    def send_body(self, f, protocol_version):
        write_longstring(f, self.response)


class AuthSuccessMessage(_MessageType):
    opcode = 0x10
    name = 'AUTH_SUCCESS'

    def __init__(self, token):
        self.token = token

    @classmethod
    def recv_body(cls, f):
        return cls(read_longstring(f))


class OptionsMessage(_MessageType):
    opcode = 0x05
    name = 'OPTIONS'

    def send_body(self, f, protocol_version):
        pass


class SupportedMessage(_MessageType):
    opcode = 0x06
    name = 'SUPPORTED'

    def __init__(self, cql_versions, options):
        self.cql_versions = cql_versions
        self.options = options

    @classmethod
    def recv_body(cls, f):
        options = read_stringmultimap(f)
        cql_versions = options.pop('CQL_VERSION')
        return cls(cql_versions=cql_versions, options=options)


# used for QueryMessage and ExecuteMessage
_VALUES_FLAG = 0x01
_SKIP_METADATA_FLAG = 0x01
_PAGE_SIZE_FLAG = 0x04
_WITH_PAGING_STATE_FLAG = 0x08
_WITH_SERIAL_CONSISTENCY_FLAG = 0x10


class QueryMessage(_MessageType):
    opcode = 0x07
    name = 'QUERY'

    def __init__(self, query, consistency_level, serial_consistency_level=None,
                 fetch_size=None, paging_state=None):
        self.query = query
        self.consistency_level = consistency_level
        self.serial_consistency_level = serial_consistency_level
        self.fetch_size = fetch_size
        self.paging_state = paging_state

    def send_body(self, f, protocol_version):
        write_longstring(f, self.query)
        write_consistency_level(f, self.consistency_level)
        flags = 0x00
        if self.serial_consistency_level:
            if protocol_version >= 2:
                flags |= _WITH_SERIAL_CONSISTENCY_FLAG
            else:
                raise UnsupportedOperation(
                    "Serial consistency levels require the use of protocol version "
                    "2 or higher. Consider setting Cluster.protocol_version to 2 "
                    "to support serial consistency levels.")

        if self.fetch_size:
            if protocol_version >= 2:
                flags |= _PAGE_SIZE_FLAG
            else:
                raise UnsupportedOperation(
                    "Automatic query paging may only be used with protocol version "
                    "2 or higher. Consider setting Cluster.protocol_version to 2.")

        if self.paging_state:
            if protocol_version >= 2:
                flags |= _WITH_PAGING_STATE_FLAG
            else:
                raise UnsupportedOperation(
                    "Automatic query paging may only be used with protocol version "
                    "2 or higher. Consider setting Cluster.protocol_version to 2.")

        write_byte(f, flags)
        if self.fetch_size:
            write_int(f, self.fetch_size)
        if self.paging_state:
            write_longstring(f, self.paging_state)
        if self.serial_consistency_level:
            write_consistency_level(f, self.serial_consistency_level)

CUSTOM_TYPE = object()

RESULT_KIND_VOID = 0x0001
RESULT_KIND_ROWS = 0x0002
RESULT_KIND_SET_KEYSPACE = 0x0003
RESULT_KIND_PREPARED = 0x0004
RESULT_KIND_SCHEMA_CHANGE = 0x0005


class ResultMessage(_MessageType):
    opcode = 0x08
    name = 'RESULT'

    kind = None
    results = None
    paging_state = None

    _type_codes = {
        0x0000: CUSTOM_TYPE,
        0x0001: AsciiType,
        0x0002: LongType,
        0x0003: BytesType,
        0x0004: BooleanType,
        0x0005: CounterColumnType,
        0x0006: DecimalType,
        0x0007: DoubleType,
        0x0008: FloatType,
        0x0009: Int32Type,
        0x000A: UTF8Type,
        0x000B: DateType,
        0x000C: UUIDType,
        0x000D: UTF8Type,
        0x000E: IntegerType,
        0x000F: TimeUUIDType,
        0x0010: InetAddressType,
        0x0020: ListType,
        0x0021: MapType,
        0x0022: SetType,
    }

    _FLAGS_GLOBAL_TABLES_SPEC = 0x0001
    _HAS_MORE_PAGES_FLAG = 0x0002
    _NO_METADATA_FLAG = 0x0004

    def __init__(self, kind, results, paging_state=None):
        self.kind = kind
        self.results = results
        self.paging_state = paging_state

    @classmethod
    def recv_body(cls, f):
        kind = read_int(f)
        paging_state = None
        if kind == RESULT_KIND_VOID:
            results = None
        elif kind == RESULT_KIND_ROWS:
            paging_state, results = cls.recv_results_rows(f)
        elif kind == RESULT_KIND_SET_KEYSPACE:
            ksname = read_string(f)
            results = ksname
        elif kind == RESULT_KIND_PREPARED:
            results = cls.recv_results_prepared(f)
        elif kind == RESULT_KIND_SCHEMA_CHANGE:
            results = cls.recv_results_schema_change(f)
        return cls(kind, results, paging_state)

    @classmethod
    def recv_results_rows(cls, f):
        paging_state, column_metadata = cls.recv_results_metadata(f)
        rowcount = read_int(f)
        rows = [cls.recv_row(f, len(column_metadata)) for _ in range(rowcount)]
        colnames = [c[2] for c in column_metadata]
        coltypes = [c[3] for c in column_metadata]
        return (
            paging_state,
            (colnames, [tuple(ctype.from_binary(val) for ctype, val in zip(coltypes, row))
                        for row in rows]))

    @classmethod
    def recv_results_prepared(cls, f):
        query_id = read_binary_string(f)
        _, column_metadata = cls.recv_results_metadata(f)
        return (query_id, column_metadata)

    @classmethod
    def recv_results_metadata(cls, f):
        flags = read_int(f)
        glob_tblspec = bool(flags & cls._FLAGS_GLOBAL_TABLES_SPEC)
        colcount = read_int(f)
        if flags & cls._HAS_MORE_PAGES_FLAG:
            paging_state = read_binary_longstring(f)
        else:
            paging_state = None
        if glob_tblspec:
            ksname = read_string(f)
            cfname = read_string(f)
        column_metadata = []
        for _ in range(colcount):
            if glob_tblspec:
                colksname = ksname
                colcfname = cfname
            else:
                colksname = read_string(f)
                colcfname = read_string(f)
            colname = read_string(f)
            coltype = cls.read_type(f)
            column_metadata.append((colksname, colcfname, colname, coltype))
        return paging_state, column_metadata

    @classmethod
    def recv_results_schema_change(cls, f):
        change_type = read_string(f)
        keyspace = read_string(f)
        table = read_string(f)
        return dict(change_type=change_type, keyspace=keyspace, table=table)

    @classmethod
    def read_type(cls, f):
        optid = read_short(f)
        try:
            typeclass = cls._type_codes[optid]
        except KeyError:
            raise NotSupportedError("Unknown data type code 0x%04x. Have to skip"
                                    " entire result set." % (optid,))
        if typeclass in (ListType, SetType):
            subtype = cls.read_type(f)
            typeclass = typeclass.apply_parameters((subtype,))
        elif typeclass == MapType:
            keysubtype = cls.read_type(f)
            valsubtype = cls.read_type(f)
            typeclass = typeclass.apply_parameters((keysubtype, valsubtype))
        elif typeclass == CUSTOM_TYPE:
            classname = read_string(f)
            typeclass = lookup_casstype(classname)

        return typeclass

    @staticmethod
    def recv_row(f, colcount):
        return [read_value(f) for _ in range(colcount)]


class PrepareMessage(_MessageType):
    opcode = 0x09
    name = 'PREPARE'

    def __init__(self, query):
        self.query = query

    def send_body(self, f, protocol_version):
        write_longstring(f, self.query)


class ExecuteMessage(_MessageType):
    opcode = 0x0A
    name = 'EXECUTE'

    def __init__(self, query_id, query_params, consistency_level,
                 serial_consistency_level=None, fetch_size=None,
                 paging_state=None):
        self.query_id = query_id
        self.query_params = query_params
        self.consistency_level = consistency_level
        self.serial_consistency_level = serial_consistency_level
        self.fetch_size = fetch_size
        self.paging_state = paging_state

    def send_body(self, f, protocol_version):
        write_string(f, self.query_id)
        if protocol_version == 1:
            if self.serial_consistency_level:
                raise UnsupportedOperation(
                    "Serial consistency levels require the use of protocol version "
                    "2 or higher. Consider setting Cluster.protocol_version to 2 "
                    "to support serial consistency levels.")
            if self.fetch_size or self.paging_state:
                raise UnsupportedOperation(
                    "Automatic query paging may only be used with protocol version "
                    "2 or higher. Consider setting Cluster.protocol_version to 2.")
            write_short(f, len(self.query_params))
            for param in self.query_params:
                write_value(f, param)
            write_consistency_level(f, self.consistency_level)
        else:
            write_consistency_level(f, self.consistency_level)
            flags = _VALUES_FLAG
            if self.serial_consistency_level:
                flags |= _WITH_SERIAL_CONSISTENCY_FLAG
            if self.fetch_size:
                flags |= _PAGE_SIZE_FLAG
            if self.paging_state:
                flags |= _WITH_PAGING_STATE_FLAG
            write_byte(f, flags)
            write_short(f, len(self.query_params))
            for param in self.query_params:
                write_value(f, param)
            if self.fetch_size:
                write_int(f, self.fetch_size)
            if self.paging_state:
                write_longstring(f, self.paging_state)
            if self.serial_consistency_level:
                write_consistency_level(f, self.serial_consistency_level)


class BatchMessage(_MessageType):
    opcode = 0x0D
    name = 'BATCH'

    def __init__(self, batch_type, queries, consistency_level):
        self.batch_type = batch_type
        self.queries = queries
        self.consistency_level = consistency_level

    def send_body(self, f, protocol_version):
        write_byte(f, self.batch_type.value)
        write_short(f, len(self.queries))
        for prepared, string_or_query_id, params in self.queries:
            if not prepared:
                write_byte(f, 0)
                write_longstring(f, string_or_query_id)
            else:
                write_byte(f, 1)
                write_short(f, len(string_or_query_id))
                f.write(string_or_query_id)
            write_short(f, len(params))
            for param in params:
                write_value(f, param)

        write_consistency_level(f, self.consistency_level)


known_event_types = frozenset((
    'TOPOLOGY_CHANGE',
    'STATUS_CHANGE',
    'SCHEMA_CHANGE'
))


class RegisterMessage(_MessageType):
    opcode = 0x0B
    name = 'REGISTER'

    def __init__(self, event_list):
        self.event_list = event_list

    def send_body(self, f, protocol_version):
        write_stringlist(f, self.event_list)


class EventMessage(_MessageType):
    opcode = 0x0C
    name = 'EVENT'

    def __init__(self, event_type, event_args):
        self.event_type = event_type
        self.event_args = event_args

    @classmethod
    def recv_body(cls, f):
        event_type = read_string(f).upper()
        if event_type in known_event_types:
            read_method = getattr(cls, 'recv_' + event_type.lower())
            return cls(event_type=event_type, event_args=read_method(f))
        raise NotSupportedError('Unknown event type %r' % event_type)

    @classmethod
    def recv_topology_change(cls, f):
        # "NEW_NODE" or "REMOVED_NODE"
        change_type = read_string(f)
        address = read_inet(f)
        return dict(change_type=change_type, address=address)

    @classmethod
    def recv_status_change(cls, f):
        # "UP" or "DOWN"
        change_type = read_string(f)
        address = read_inet(f)
        return dict(change_type=change_type, address=address)

    @classmethod
    def recv_schema_change(cls, f):
        # "CREATED", "DROPPED", or "UPDATED"
        change_type = read_string(f)
        keyspace = read_string(f)
        table = read_string(f)
        return dict(change_type=change_type, keyspace=keyspace, table=table)


def write_header(f, version, flags, stream_id, opcode, length):
    """
    Write a CQL protocol frame header.
    """
    f.write(header_pack(version, flags, stream_id, opcode))
    write_int(f, length)


def read_byte(f):
    return int8_unpack(f.read(1))


def write_byte(f, b):
    f.write(int8_pack(b))


def read_int(f):
    return int32_unpack(f.read(4))


def write_int(f, i):
    f.write(int32_pack(i))


def read_short(f):
    return uint16_unpack(f.read(2))


def write_short(f, s):
    f.write(uint16_pack(s))


def read_consistency_level(f):
    return read_short(f)


def write_consistency_level(f, cl):
    write_short(f, cl)


def read_string(f):
    size = read_short(f)
    contents = f.read(size)
    return contents.decode('utf8')


def read_binary_string(f):
    size = read_short(f)
    contents = f.read(size)
    return contents


def write_string(f, s):
    if isinstance(s, six.text_type):
        s = s.encode('utf8')
    write_short(f, len(s))
    f.write(s)


def read_binary_longstring(f):
    size = read_int(f)
    contents = f.read(size)
    return contents


def read_longstring(f):
    return read_binary_longstring(f).decode('utf8')


def write_longstring(f, s):
    if isinstance(s, six.text_type):
        s = s.encode('utf8')
    write_int(f, len(s))
    f.write(s)


def read_stringlist(f):
    numstrs = read_short(f)
    return [read_string(f) for _ in range(numstrs)]


def write_stringlist(f, stringlist):
    write_short(f, len(stringlist))
    for s in stringlist:
        write_string(f, s)


def read_stringmap(f):
    numpairs = read_short(f)
    strmap = {}
    for _ in range(numpairs):
        k = read_string(f)
        strmap[k] = read_string(f)
    return strmap


def write_stringmap(f, strmap):
    write_short(f, len(strmap))
    for k, v in strmap.items():
        write_string(f, k)
        write_string(f, v)


def read_stringmultimap(f):
    numkeys = read_short(f)
    strmmap = {}
    for _ in range(numkeys):
        k = read_string(f)
        strmmap[k] = read_stringlist(f)
    return strmmap


def write_stringmultimap(f, strmmap):
    write_short(f, len(strmmap))
    for k, v in strmmap.items():
        write_string(f, k)
        write_stringlist(f, v)


def read_value(f):
    size = read_int(f)
    if size < 0:
        return None
    return f.read(size)


def write_value(f, v):
    if v is None:
        write_int(f, -1)
    else:
        write_int(f, len(v))
        f.write(v)


def read_inet(f):
    size = read_byte(f)
    addrbytes = f.read(size)
    port = read_int(f)
    if size == 4:
        addrfam = socket.AF_INET
    elif size == 16:
        addrfam = socket.AF_INET6
    else:
        raise InternalError("bad inet address: %r" % (addrbytes,))
    return (socket.inet_ntop(addrfam, addrbytes), port)


def write_inet(f, addrtuple):
    addr, port = addrtuple
    if ':' in addr:
        addrfam = socket.AF_INET6
    else:
        addrfam = socket.AF_INET
    addrbytes = socket.inet_pton(addrfam, addr)
    write_byte(f, len(addrbytes))
    f.write(addrbytes)
    write_int(f, port)

########NEW FILE########
__FILENAME__ = query
# Copyright 2013-2014 DataStax, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
This module holds classes for working with prepared statements and
specifying consistency levels and retry policies for individual
queries.
"""

from collections import namedtuple
from datetime import datetime, timedelta
import re
import struct
import time
import six

from cassandra import ConsistencyLevel, OperationTimedOut
from cassandra.cqltypes import unix_time_from_uuid1
from cassandra.encoder import (cql_encoders, cql_encode_object,
                               cql_encode_sequence)
from cassandra.util import OrderedDict

import logging
log = logging.getLogger(__name__)


NON_ALPHA_REGEX = re.compile('[^a-zA-Z0-9]')
START_BADCHAR_REGEX = re.compile('^[^a-zA-Z0-9]*')
END_BADCHAR_REGEX = re.compile('[^a-zA-Z0-9_]*$')

_clean_name_cache = {}


def _clean_column_name(name):
    try:
        return _clean_name_cache[name]
    except KeyError:
        clean = NON_ALPHA_REGEX.sub("_", START_BADCHAR_REGEX.sub("", END_BADCHAR_REGEX.sub("", name)))
        _clean_name_cache[name] = clean
        return clean


def tuple_factory(colnames, rows):
    """
    Returns each row as a tuple

    Example::

        >>> from cassandra.query import named_tuple_factory
        >>> session = cluster.connect('mykeyspace')
        >>> session.row_factory = tuple_factory
        >>> rows = session.execute("SELECT name, age FROM users LIMIT 1")
        >>> print rows[0]
        ('Bob', 42)

    .. versionchanged:: 2.0.0
        moved from ``cassandra.decoder`` to ``cassandra.query``
    """
    return rows


def named_tuple_factory(colnames, rows):
    """
    Returns each row as a `namedtuple <https://docs.python.org/2/library/collections.html#collections.namedtuple>`_.
    This is the default row factory.

    Example::

        >>> from cassandra.query import named_tuple_factory
        >>> session = cluster.connect('mykeyspace')
        >>> session.row_factory = named_tuple_factory
        >>> rows = session.execute("SELECT name, age FROM users LIMIT 1")
        >>> user = rows[0]

        >>> # you can access field by their name:
        >>> print "name: %s, age: %d" % (user.name, user.age)
        name: Bob, age: 42

        >>> # or you can access fields by their position (like a tuple)
        >>> name, age = user
        >>> print "name: %s, age: %d" % (name, age)
        name: Bob, age: 42
        >>> name = user[0]
        >>> age = user[1]
        >>> print "name: %s, age: %d" % (name, age)
        name: Bob, age: 42

    .. versionchanged:: 2.0.0
        moved from ``cassandra.decoder`` to ``cassandra.query``
    """
    Row = namedtuple('Row', map(_clean_column_name, colnames))
    return [Row(*row) for row in rows]


def dict_factory(colnames, rows):
    """
    Returns each row as a dict.

    Example::

        >>> from cassandra.query import named_tuple_factory
        >>> session = cluster.connect('mykeyspace')
        >>> session.row_factory = dict_factory
        >>> rows = session.execute("SELECT name, age FROM users LIMIT 1")
        >>> print rows[0]
        {'age': 42, 'name': 'Bob'}

    .. versionchanged:: 2.0.0
        moved from ``cassandra.decoder`` to ``cassandra.query``
    """
    return [dict(zip(colnames, row)) for row in rows]


def ordered_dict_factory(colnames, rows):
    """
    Like :meth:`~cassandra.query.dict_factory`, but returns each row as an OrderedDict,
    so the order of the columns is preserved.

    .. versionchanged:: 2.0.0
        moved from ``cassandra.decoder`` to ``cassandra.query``
    """
    return [OrderedDict(zip(colnames, row)) for row in rows]


class Statement(object):
    """
    An abstract class representing a single query. There are three subclasses:
    :class:`.SimpleStatement`, :class:`.BoundStatement`, and :class:`.BatchStatement`.
    These can be passed to :meth:`.Session.execute()`.
    """

    retry_policy = None
    """
    An instance of a :class:`cassandra.policies.RetryPolicy` or one of its
    subclasses.  This controls when a query will be retried and how it
    will be retried.
    """

    trace = None
    """
    If :meth:`.Session.execute()` is run with `trace` set to :const:`True`,
    this will be set to a :class:`.QueryTrace` instance.
    """

    consistency_level = None
    """
    The :class:`.ConsistencyLevel` to be used for this operation.  Defaults
    to :const:`None`, which means that the default consistency level for
    the Session this is executed in will be used.
    """

    fetch_size = None
    """
    How many rows will be fetched at a time.  This overrides the default
    of :attr:`.Session.default_fetch_size`

    This only takes effect when protocol version 2 or higher is used.
    See :attr:`.Cluster.protocol_version` for details.

    .. versionadded:: 2.0.0
    """

    _serial_consistency_level = None
    _routing_key = None

    def __init__(self, retry_policy=None, consistency_level=None, routing_key=None,
                 serial_consistency_level=None, fetch_size=None):
        self.retry_policy = retry_policy
        if consistency_level is not None:
            self.consistency_level = consistency_level
        if serial_consistency_level is not None:
            self.serial_consistency_level = serial_consistency_level
        if fetch_size is not None:
            self.fetch_size = None
        self._routing_key = routing_key

    def _get_routing_key(self):
        return self._routing_key

    def _set_routing_key(self, key):
        if isinstance(key, (list, tuple)):
            self._routing_key = b"".join(struct.pack("HsB", len(component), component, 0)
                                         for component in key)
        else:
            self._routing_key = key

    def _del_routing_key(self):
        self._routing_key = None

    routing_key = property(
        _get_routing_key,
        _set_routing_key,
        _del_routing_key,
        """
        The :attr:`~.TableMetadata.partition_key` portion of the primary key,
        which can be used to determine which nodes are replicas for the query.

        If the partition key is a composite, a list or tuple must be passed in.
        Each key component should be in its packed (binary) format, so all
        components should be strings.
        """)

    def _get_serial_consistency_level(self):
        return self._serial_consistency_level

    def _set_serial_consistency_level(self, serial_consistency_level):
        acceptable = (None, ConsistencyLevel.SERIAL, ConsistencyLevel.LOCAL_SERIAL)
        if serial_consistency_level not in acceptable:
            raise ValueError(
                "serial_consistency_level must be either ConsistencyLevel.SERIAL "
                "or ConsistencyLevel.LOCAL_SERIAL")

    def _del_serial_consistency_level(self):
        self._serial_consistency_level = None

    serial_consistency_level = property(
         _get_serial_consistency_level,
         _set_serial_consistency_level,
         _del_serial_consistency_level,
        """
        The serial consistency level is only used by conditional updates
        (``INSERT``, ``UPDATE`` and ``DELETE`` with an ``IF`` condition).  For
        those, the ``serial_consistency_level`` defines the consistency level of
        the serial phase (or "paxos" phase) while the normal
        :attr:`~.consistency_level` defines the consistency for the "learn" phase,
        i.e. what type of reads will be guaranteed to see the update right away.
        For example, if a conditional write has a :attr:`~.consistency_level` of
        :attr:`~.ConsistencyLevel.QUORUM` (and is successful), then a
        :attr:`~.ConsistencyLevel.QUORUM` read is guaranteed to see that write.
        But if the regular :attr:`~.consistency_level` of that write is
        :attr:`~.ConsistencyLevel.ANY`, then only a read with a
        :attr:`~.consistency_level` of :attr:`~.ConsistencyLevel.SERIAL` is
        guaranteed to see it (even a read with consistency
        :attr:`~.ConsistencyLevel.ALL` is not guaranteed to be enough).

        The serial consistency can only be one of :attr:`~.ConsistencyLevel.SERIAL`
        or :attr:`~.ConsistencyLevel.LOCAL_SERIAL`. While ``SERIAL`` guarantees full
        linearizability (with other ``SERIAL`` updates), ``LOCAL_SERIAL`` only
        guarantees it in the local data center.

        The serial consistency level is ignored for any query that is not a
        conditional update. Serial reads should use the regular
        :attr:`consistency_level`.

        Serial consistency levels may only be used against Cassandra 2.0+
        and the :attr:`~.Cluster.protocol_version` must be set to 2 or higher.

        .. versionadded:: 2.0.0
        """)

    @property
    def keyspace(self):
        """
        The string name of the keyspace this query acts on.
        """
        return None


class SimpleStatement(Statement):
    """
    A simple, un-prepared query.  All attributes of :class:`Statement` apply
    to this class as well.
    """

    def __init__(self, query_string, *args, **kwargs):
        """
        `query_string` should be a literal CQL statement with the exception
        of parameter placeholders that will be filled through the
        `parameters` argument of :meth:`.Session.execute()`.
        """
        Statement.__init__(self, *args, **kwargs)
        self._query_string = query_string

    @property
    def query_string(self):
        return self._query_string

    def __str__(self):
        consistency = ConsistencyLevel.value_to_name.get(self.consistency_level, 'Not Set')
        return (u'<SimpleStatement query="%s", consistency=%s>' %
                (self.query_string, consistency))
    __repr__ = __str__


class PreparedStatement(object):
    """
    A statement that has been prepared against at least one Cassandra node.
    Instances of this class should not be created directly, but through
    :meth:`.Session.prepare()`.

    A :class:`.PreparedStatement` should be prepared only once. Re-preparing a statement
    may affect performance (as the operation requires a network roundtrip).
    """

    column_metadata = None
    query_id = None
    query_string = None
    keyspace = None

    routing_key_indexes = None

    consistency_level = None
    serial_consistency_level = None

    def __init__(self, column_metadata, query_id, routing_key_indexes, query, keyspace,
                 consistency_level=None, serial_consistency_level=None, fetch_size=None):
        self.column_metadata = column_metadata
        self.query_id = query_id
        self.routing_key_indexes = routing_key_indexes
        self.query_string = query
        self.keyspace = keyspace
        self.consistency_level = consistency_level
        self.serial_consistency_level = serial_consistency_level
        self.fetch_size = fetch_size

    @classmethod
    def from_message(cls, query_id, column_metadata, cluster_metadata, query, keyspace):
        if not column_metadata:
            return PreparedStatement(column_metadata, query_id, None, query, keyspace)

        partition_key_columns = None
        routing_key_indexes = None

        ks_name, table_name, _, _ = column_metadata[0]
        ks_meta = cluster_metadata.keyspaces.get(ks_name)
        if ks_meta:
            table_meta = ks_meta.tables.get(table_name)
            if table_meta:
                partition_key_columns = table_meta.partition_key

                # make a map of {column_name: index} for each column in the statement
                statement_indexes = dict((c[2], i) for i, c in enumerate(column_metadata))

                # a list of which indexes in the statement correspond to partition key items
                try:
                    routing_key_indexes = [statement_indexes[c.name]
                                           for c in partition_key_columns]
                except KeyError:
                    pass  # we're missing a partition key component in the prepared
                          # statement; just leave routing_key_indexes as None

        return PreparedStatement(column_metadata, query_id, routing_key_indexes, query, keyspace)

    def bind(self, values):
        """
        Creates and returns a :class:`BoundStatement` instance using `values`.
        The `values` parameter **must** be a sequence, such as a tuple or list,
        even if there is only one value to bind.
        """
        return BoundStatement(self).bind(values)

    def __str__(self):
        consistency = ConsistencyLevel.value_to_name.get(self.consistency_level, 'Not Set')
        return (u'<PreparedStatement query="%s", consistency=%s>' %
                (self.query_string, consistency))
    __repr__ = __str__


class BoundStatement(Statement):
    """
    A prepared statement that has been bound to a particular set of values.
    These may be created directly or through :meth:`.PreparedStatement.bind()`.

    All attributes of :class:`Statement` apply to this class as well.
    """

    prepared_statement = None
    """
    The :class:`PreparedStatement` instance that this was created from.
    """

    values = None
    """
    The sequence of values that were bound to the prepared statement.
    """

    def __init__(self, prepared_statement, *args, **kwargs):
        """
        `prepared_statement` should be an instance of :class:`PreparedStatement`.
        All other ``*args`` and ``**kwargs`` will be passed to :class:`.Statement`.
        """
        self.consistency_level = prepared_statement.consistency_level
        self.serial_consistency_level = prepared_statement.serial_consistency_level
        self.prepared_statement = prepared_statement
        self.values = []

        Statement.__init__(self, *args, **kwargs)

    def bind(self, values):
        """
        Binds a sequence of values for the prepared statement parameters
        and returns this instance.  Note that `values` *must* be:
        * a sequence, even if you are only binding one value, or
        * a dict that relates 1-to-1 between dict keys and columns
        """
        if values is None:
            values = ()
        col_meta = self.prepared_statement.column_metadata

        # special case for binding dicts
        if isinstance(values, dict):
            dict_values = values
            values = []

            # sort values accordingly
            for col in col_meta:
                try:
                    values.append(dict_values[col[2]])
                except KeyError:
                    raise KeyError(
                        'Column name `%s` not found in bound dict.' %
                        (col[2]))

            # ensure a 1-to-1 dict keys to columns relationship
            if len(dict_values) != len(col_meta):
                # find expected columns
                columns = set()
                for col in col_meta:
                    columns.add(col[2])

                # generate error message
                if len(dict_values) > len(col_meta):
                    difference = set(dict_values.keys()).difference(columns)
                    msg = "Too many arguments provided to bind() (got %d, expected %d). " + \
                          "Unexpected keys %s."
                else:
                    difference = set(columns).difference(dict_values.keys())
                    msg = "Too few arguments provided to bind() (got %d, expected %d). " + \
                          "Expected keys %s."

                # exit with error message
                msg = msg % (len(values), len(col_meta), difference)
                raise ValueError(msg)

        if len(values) > len(col_meta):
            raise ValueError(
                "Too many arguments provided to bind() (got %d, expected %d)" %
                (len(values), len(col_meta)))

        self.raw_values = values
        self.values = []
        for value, col_spec in zip(values, col_meta):
            if value is None:
                self.values.append(None)
            else:
                col_type = col_spec[-1]

                try:
                    self.values.append(col_type.serialize(value))
                except (TypeError, struct.error):
                    col_name = col_spec[2]
                    expected_type = col_type
                    actual_type = type(value)

                    message = ('Received an argument of invalid type for column "%s". '
                               'Expected: %s, Got: %s' % (col_name, expected_type, actual_type))
                    raise TypeError(message)

        return self

    @property
    def routing_key(self):
        if not self.prepared_statement.routing_key_indexes:
            return None

        if self._routing_key is not None:
            return self._routing_key

        routing_indexes = self.prepared_statement.routing_key_indexes
        if len(routing_indexes) == 1:
            self._routing_key = self.values[routing_indexes[0]]
        else:
            components = []
            for statement_index in routing_indexes:
                val = self.values[statement_index]
                components.append(struct.pack("HsB", len(val), val, 0))

            self._routing_key = b"".join(components)

        return self._routing_key

    @property
    def keyspace(self):
        meta = self.prepared_statement.column_metadata
        if meta:
            return meta[0][0]
        else:
            return None

    def __str__(self):
        consistency = ConsistencyLevel.value_to_name.get(self.consistency_level, 'Not Set')
        return (u'<BoundStatement query="%s", values=%s, consistency=%s>' %
                (self.prepared_statement.query_string, self.raw_values, consistency))
    __repr__ = __str__


class BatchType(object):
    """
    A BatchType is used with :class:`.BatchStatement` instances to control
    the atomicity of the batch operation.

    .. versionadded:: 2.0.0
    """

    LOGGED = None
    """
    Atomic batch operation.
    """

    UNLOGGED = None
    """
    Non-atomic batch operation.
    """

    COUNTER = None
    """
    Batches of counter operations.
    """

    def __init__(self, name, value):
        self.name = name
        self.value = value

    def __str__(self):
        return self.name

    def __repr__(self):
        return "BatchType.%s" % (self.name, )


BatchType.LOGGED = BatchType("LOGGED", 0)
BatchType.UNLOGGED = BatchType("UNLOGGED", 1)
BatchType.COUNTER = BatchType("COUNTER", 2)


class BatchStatement(Statement):
    """
    A protocol-level batch of operations which are applied atomically
    by default.

    .. versionadded:: 2.0.0
    """

    batch_type = None
    """
    The :class:`.BatchType` for the batch operation.  Defaults to
    :attr:`.BatchType.LOGGED`.
    """

    _statements_and_parameters = None

    def __init__(self, batch_type=BatchType.LOGGED, retry_policy=None,
                 consistency_level=None):
        """
        `batch_type` specifies The :class:`.BatchType` for the batch operation.
        Defaults to :attr:`.BatchType.LOGGED`.

        `retry_policy` should be a :class:`~.RetryPolicy` instance for
        controlling retries on the operation.

        `consistency_level` should be a :class:`~.ConsistencyLevel` value
        to be used for all operations in the batch.

        Example usage:

        .. code-block:: python

            insert_user = session.prepare("INSERT INTO users (name, age) VALUES (?, ?)")
            batch = BatchStatement(consistency_level=ConsistencyLevel.QUORUM)

            for (name, age) in users_to_insert:
                batch.add(insert_user, (name, age))

            session.execute(batch)

        You can also mix different types of operations within a batch:

        .. code-block:: python

            batch = BatchStatement()
            batch.add(SimpleStatement("INSERT INTO users (name, age) VALUES (%s, %s)", (name, age))
            batch.add(SimpleStatement("DELETE FROM pending_users WHERE name=%s", (name,))
            session.execute(batch)

        .. versionadded:: 2.0.0
        """
        self.batch_type = batch_type
        self._statements_and_parameters = []
        Statement.__init__(self, retry_policy=retry_policy, consistency_level=consistency_level)

    def add(self, statement, parameters=None):
        """
        Adds a :class:`.Statement` and optional sequence of parameters
        to be used with the statement to the batch.

        Like with other statements, parameters must be a sequence, even
        if there is only one item.
        """
        if isinstance(statement, six.string_types):
            if parameters:
                statement = bind_params(statement, parameters)
            self._statements_and_parameters.append((False, statement, ()))
        elif isinstance(statement, PreparedStatement):
            query_id = statement.query_id
            bound_statement = statement.bind(() if parameters is None else parameters)
            self._statements_and_parameters.append(
                (True, query_id, bound_statement.values))
        elif isinstance(statement, BoundStatement):
            if parameters:
                raise ValueError(
                    "Parameters cannot be passed with a BoundStatement "
                    "to BatchStatement.add()")
            self._statements_and_parameters.append(
                (True, statement.prepared_statement.query_id, statement.values))
        else:
            # it must be a SimpleStatement
            query_string = statement.query_string
            if parameters:
                query_string = bind_params(query_string, parameters)
            self._statements_and_parameters.append((False, query_string, ()))
        return self

    def add_all(self, statements, parameters):
        """
        Adds a sequence of :class:`.Statement` objects and a matching sequence
        of parameters to the batch.  :const:`None` can be used in place of
        parameters when no parameters are needed.
        """
        for statement, value in zip(statements, parameters):
            self.add(statement, parameters)

    def __str__(self):
        consistency = ConsistencyLevel.value_to_name.get(self.consistency_level, 'Not Set')
        return (u'<BatchStatement type=%s, statements=%d, consistency=%s>' %
                (self.batch_type, len(self._statements_and_parameters), consistency))
    __repr__ = __str__


class ValueSequence(object):
    """
    A wrapper class that is used to specify that a sequence of values should
    be treated as a CQL list of values instead of a single column collection when used
    as part of the `parameters` argument for :meth:`.Session.execute()`.

    This is typically needed when supplying a list of keys to select.
    For example::

        >>> my_user_ids = ('alice', 'bob', 'charles')
        >>> query = "SELECT * FROM users WHERE user_id IN %s"
        >>> session.execute(query, parameters=[ValueSequence(my_user_ids)])

    """

    def __init__(self, sequence):
        self.sequence = sequence

    def __str__(self):
        return cql_encode_sequence(self.sequence)


def bind_params(query, params):
    if isinstance(params, dict):
        return query % dict((k, cql_encoders.get(type(v), cql_encode_object)(v)) for k, v in six.iteritems(params))
    else:
        return query % tuple(cql_encoders.get(type(v), cql_encode_object)(v) for v in params)


class TraceUnavailable(Exception):
    """
    Raised when complete trace details cannot be fetched from Cassandra.
    """
    pass


class QueryTrace(object):
    """
    A trace of the duration and events that occurred when executing
    an operation.
    """

    trace_id = None
    """
    :class:`uuid.UUID` unique identifier for this tracing session.  Matches
    the ``session_id`` column in ``system_traces.sessions`` and
    ``system_traces.events``.
    """

    request_type = None
    """
    A string that very generally describes the traced operation.
    """

    duration = None
    """
    A :class:`datetime.timedelta` measure of the duration of the query.
    """

    coordinator = None
    """
    The IP address of the host that acted as coordinator for this request.
    """

    parameters = None
    """
    A :class:`dict` of parameters for the traced operation, such as the
    specific query string.
    """

    started_at = None
    """
    A UTC :class:`datetime.datetime` object describing when the operation
    was started.
    """

    events = None
    """
    A chronologically sorted list of :class:`.TraceEvent` instances
    representing the steps the traced operation went through.  This
    corresponds to the rows in ``system_traces.events`` for this tracing
    session.
    """

    _session = None

    _SELECT_SESSIONS_FORMAT = "SELECT * FROM system_traces.sessions WHERE session_id = %s"
    _SELECT_EVENTS_FORMAT = "SELECT * FROM system_traces.events WHERE session_id = %s"
    _BASE_RETRY_SLEEP = 0.003

    def __init__(self, trace_id, session):
        self.trace_id = trace_id
        self._session = session

    def populate(self, max_wait=2.0):
        """
        Retrieves the actual tracing details from Cassandra and populates the
        attributes of this instance.  Because tracing details are stored
        asynchronously by Cassandra, this may need to retry the session
        detail fetch.  If the trace is still not available after `max_wait`
        seconds, :exc:`.TraceUnavailable` will be raised; if `max_wait` is
        :const:`None`, this will retry forever.
        """
        attempt = 0
        start = time.time()
        while True:
            time_spent = time.time() - start
            if max_wait is not None and time_spent >= max_wait:
                raise TraceUnavailable(
                    "Trace information was not available within %f seconds. Consider raising Session.max_trace_wait." % (max_wait,))

            log.debug("Attempting to fetch trace info for trace ID: %s", self.trace_id)
            session_results = self._execute(
                self._SELECT_SESSIONS_FORMAT, (self.trace_id,), time_spent, max_wait)

            if not session_results or session_results[0].duration is None:
                time.sleep(self._BASE_RETRY_SLEEP * (2 ** attempt))
                attempt += 1
                continue
            log.debug("Fetched trace info for trace ID: %s", self.trace_id)

            session_row = session_results[0]
            self.request_type = session_row.request
            self.duration = timedelta(microseconds=session_row.duration)
            self.started_at = session_row.started_at
            self.coordinator = session_row.coordinator
            self.parameters = session_row.parameters

            log.debug("Attempting to fetch trace events for trace ID: %s", self.trace_id)
            time_spent = time.time() - start
            event_results = self._execute(
                self._SELECT_EVENTS_FORMAT, (self.trace_id,), time_spent, max_wait)
            log.debug("Fetched trace events for trace ID: %s", self.trace_id)
            self.events = tuple(TraceEvent(r.activity, r.event_id, r.source, r.source_elapsed, r.thread)
                                for r in event_results)
            break

    def _execute(self, query, parameters, time_spent, max_wait):
        # in case the user switched the row factory, set it to namedtuple for this query
        future = self._session._create_response_future(query, parameters, trace=False)
        future.row_factory = named_tuple_factory
        future.send_request()

        timeout = (max_wait - time_spent) if max_wait is not None else None
        try:
            return future.result(timeout=timeout)
        except OperationTimedOut:
            raise TraceUnavailable("Trace information was not available within %f seconds" % (max_wait,))

    def __str__(self):
        return "%s [%s] coordinator: %s, started at: %s, duration: %s, parameters: %s" \
               % (self.request_type, self.trace_id, self.coordinator, self.started_at,
                  self.duration, self.parameters)


class TraceEvent(object):
    """
    Representation of a single event within a query trace.
    """

    description = None
    """
    A brief description of the event.
    """

    datetime = None
    """
    A UTC :class:`datetime.datetime` marking when the event occurred.
    """

    source = None
    """
    The IP address of the node this event occurred on.
    """

    source_elapsed = None
    """
    A :class:`datetime.timedelta` measuring the amount of time until
    this event occurred starting from when :attr:`.source` first
    received the query.
    """

    thread_name = None
    """
    The name of the thread that this event occurred on.
    """

    def __init__(self, description, timeuuid, source, source_elapsed, thread_name):
        self.description = description
        self.datetime = datetime.utcfromtimestamp(unix_time_from_uuid1(timeuuid))
        self.source = source
        if source_elapsed is not None:
            self.source_elapsed = timedelta(microseconds=source_elapsed)
        else:
            self.source_elapsed = None
        self.thread_name = thread_name

    def __str__(self):
        return "%s on %s[%s] at %s" % (self.description, self.source, self.thread_name, self.datetime)

########NEW FILE########
__FILENAME__ = util
from __future__ import with_statement

try:
    from collections import OrderedDict
except ImportError:
    # OrderedDict from Python 2.7+

    # Copyright (c) 2009 Raymond Hettinger
    #
    # Permission is hereby granted, free of charge, to any person
    # obtaining a copy of this software and associated documentation files
    # (the "Software"), to deal in the Software without restriction,
    # including without limitation the rights to use, copy, modify, merge,
    # publish, distribute, sublicense, and/or sell copies of the Software,
    # and to permit persons to whom the Software is furnished to do so,
    # subject to the following conditions:
    #
    #     The above copyright notice and this permission notice shall be
    #     included in all copies or substantial portions of the Software.
    #
    #     THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
    #     EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES
    #     OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
    #     NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
    #     HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
    #     WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
    #     FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
    #     OTHER DEALINGS IN THE SOFTWARE.
    from UserDict import DictMixin

    class OrderedDict(dict, DictMixin):  # noqa
        """ A dictionary which maintains the insertion order of keys. """

        def __init__(self, *args, **kwds):
            """ A dictionary which maintains the insertion order of keys. """

            if len(args) > 1:
                raise TypeError('expected at most 1 arguments, got %d' % len(args))
            try:
                self.__end
            except AttributeError:
                self.clear()
            self.update(*args, **kwds)

        def clear(self):
            self.__end = end = []
            end += [None, end, end]         # sentinel node for doubly linked list
            self.__map = {}                 # key --> [key, prev, next]
            dict.clear(self)

        def __setitem__(self, key, value):
            if key not in self:
                end = self.__end
                curr = end[1]
                curr[2] = end[1] = self.__map[key] = [key, curr, end]
            dict.__setitem__(self, key, value)

        def __delitem__(self, key):
            dict.__delitem__(self, key)
            key, prev, next = self.__map.pop(key)
            prev[2] = next
            next[1] = prev

        def __iter__(self):
            end = self.__end
            curr = end[2]
            while curr is not end:
                yield curr[0]
                curr = curr[2]

        def __reversed__(self):
            end = self.__end
            curr = end[1]
            while curr is not end:
                yield curr[0]
                curr = curr[1]

        def popitem(self, last=True):
            if not self:
                raise KeyError('dictionary is empty')
            if last:
                key = next(reversed(self))
            else:
                key = next(iter(self))
            value = self.pop(key)
            return key, value

        def __reduce__(self):
            items = [[k, self[k]] for k in self]
            tmp = self.__map, self.__end
            del self.__map, self.__end
            inst_dict = vars(self).copy()
            self.__map, self.__end = tmp
            if inst_dict:
                return (self.__class__, (items,), inst_dict)
            return self.__class__, (items,)

        def keys(self):
            return list(self)

        setdefault = DictMixin.setdefault
        update = DictMixin.update
        pop = DictMixin.pop
        values = DictMixin.values
        items = DictMixin.items
        iterkeys = DictMixin.iterkeys
        itervalues = DictMixin.itervalues
        iteritems = DictMixin.iteritems

        def __repr__(self):
            if not self:
                return '%s()' % (self.__class__.__name__,)
            return '%s(%r)' % (self.__class__.__name__, self.items())

        def copy(self):
            return self.__class__(self)

        @classmethod
        def fromkeys(cls, iterable, value=None):
            d = cls()
            for key in iterable:
                d[key] = value
            return d

        def __eq__(self, other):
            if isinstance(other, OrderedDict):
                if len(self) != len(other):
                    return False
                for p, q in  zip(self.items(), other.items()):
                    if p != q:
                        return False
                return True
            return dict.__eq__(self, other)

        def __ne__(self, other):
            return not self == other


# WeakSet from Python 2.7+ (https://code.google.com/p/weakrefset)

from _weakref import ref


class _IterationGuard(object):
    # This context manager registers itself in the current iterators of the
    # weak container, such as to delay all removals until the context manager
    # exits.
    # This technique should be relatively thread-safe (since sets are).

    def __init__(self, weakcontainer):
        # Don't create cycles
        self.weakcontainer = ref(weakcontainer)

    def __enter__(self):
        w = self.weakcontainer()
        if w is not None:
            w._iterating.add(self)
        return self

    def __exit__(self, e, t, b):
        w = self.weakcontainer()
        if w is not None:
            s = w._iterating
            s.remove(self)
            if not s:
                w._commit_removals()


class WeakSet(object):
    def __init__(self, data=None):
        self.data = set()

        def _remove(item, selfref=ref(self)):
            self = selfref()
            if self is not None:
                if self._iterating:
                    self._pending_removals.append(item)
                else:
                    self.data.discard(item)

        self._remove = _remove
        # A list of keys to be removed
        self._pending_removals = []
        self._iterating = set()
        if data is not None:
            self.update(data)

    def _commit_removals(self):
        l = self._pending_removals
        discard = self.data.discard
        while l:
            discard(l.pop())

    def __iter__(self):
        with _IterationGuard(self):
            for itemref in self.data:
                item = itemref()
                if item is not None:
                    yield item

    def __len__(self):
        return sum(x() is not None for x in self.data)

    def __contains__(self, item):
        return ref(item) in self.data

    def __reduce__(self):
        return (self.__class__, (list(self),),
                getattr(self, '__dict__', None))

    __hash__ = None

    def add(self, item):
        if self._pending_removals:
            self._commit_removals()
        self.data.add(ref(item, self._remove))

    def clear(self):
        if self._pending_removals:
            self._commit_removals()
        self.data.clear()

    def copy(self):
        return self.__class__(self)

    def pop(self):
        if self._pending_removals:
            self._commit_removals()
        while True:
            try:
                itemref = self.data.pop()
            except KeyError:
                raise KeyError('pop from empty WeakSet')
            item = itemref()
            if item is not None:
                return item

    def remove(self, item):
        if self._pending_removals:
            self._commit_removals()
        self.data.remove(ref(item))

    def discard(self, item):
        if self._pending_removals:
            self._commit_removals()
        self.data.discard(ref(item))

    def update(self, other):
        if self._pending_removals:
            self._commit_removals()
        if isinstance(other, self.__class__):
            self.data.update(other.data)
        else:
            for element in other:
                self.add(element)

    def __ior__(self, other):
        self.update(other)
        return self

    # Helper functions for simple delegating methods.
    def _apply(self, other, method):
        if not isinstance(other, self.__class__):
            other = self.__class__(other)
        newdata = method(other.data)
        newset = self.__class__()
        newset.data = newdata
        return newset

    def difference(self, other):
        return self._apply(other, self.data.difference)
    __sub__ = difference

    def difference_update(self, other):
        if self._pending_removals:
            self._commit_removals()
        if self is other:
            self.data.clear()
        else:
            self.data.difference_update(ref(item) for item in other)

    def __isub__(self, other):
        if self._pending_removals:
            self._commit_removals()
        if self is other:
            self.data.clear()
        else:
            self.data.difference_update(ref(item) for item in other)
        return self

    def intersection(self, other):
        return self._apply(other, self.data.intersection)
    __and__ = intersection

    def intersection_update(self, other):
        if self._pending_removals:
            self._commit_removals()
        self.data.intersection_update(ref(item) for item in other)

    def __iand__(self, other):
        if self._pending_removals:
            self._commit_removals()
        self.data.intersection_update(ref(item) for item in other)
        return self

    def issubset(self, other):
        return self.data.issubset(ref(item) for item in other)
    __lt__ = issubset

    def __le__(self, other):
        return self.data <= set(ref(item) for item in other)

    def issuperset(self, other):
        return self.data.issuperset(ref(item) for item in other)
    __gt__ = issuperset

    def __ge__(self, other):
        return self.data >= set(ref(item) for item in other)

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return NotImplemented
        return self.data == set(ref(item) for item in other)

    def symmetric_difference(self, other):
        return self._apply(other, self.data.symmetric_difference)
    __xor__ = symmetric_difference

    def symmetric_difference_update(self, other):
        if self._pending_removals:
            self._commit_removals()
        if self is other:
            self.data.clear()
        else:
            self.data.symmetric_difference_update(ref(item) for item in other)

    def __ixor__(self, other):
        if self._pending_removals:
            self._commit_removals()
        if self is other:
            self.data.clear()
        else:
            self.data.symmetric_difference_update(ref(item) for item in other)
        return self

    def union(self, other):
        return self._apply(other, self.data.union)
    __or__ = union

    def isdisjoint(self, other):
        return len(self.intersection(other)) == 0

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# Cassandra Driver documentation build configuration file, created by
# sphinx-quickstart on Mon Jul  1 11:40:09 2013.
#
# This file is execfile()d with the current directory set to its containing dir.
#
# Note that not all possible configuration values are present in this
# autogenerated file.
#
# All configuration values have a default; values that are commented out
# serve to show the default.

import os
import sys

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
sys.path.insert(0, os.path.abspath('..'))
import cassandra

# -- General configuration -----------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
#needs_sphinx = '1.0'

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = ['sphinx.ext.autodoc', 'sphinx.ext.viewcode']

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8-sig'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'Cassandra Driver'
copyright = u'2014, DataStax'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = cassandra.__version__
# The full version, including alpha/beta/rc tags.
release = cassandra.__version__

autodoc_member_order = 'bysource'
autoclass_content = 'both'

# The language for content autogenerated by Sphinx. Refer to documentation
# for a list of supported languages.
#language = None

# There are two options for replacing |today|: either, you set today to some
# non-false value, then it is used:
#today = ''
# Else, today_fmt is used as the format for a strftime call.
#today_fmt = '%B %d, %Y'

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
exclude_patterns = ['_build']

# The reST default role (used for this markup: `text`) to use for all documents.
#default_role = None

# If true, '()' will be appended to :func: etc. cross-reference text.
#add_function_parentheses = True

# If true, the current module name will be prepended to all description
# unit titles (such as .. function::).
#add_module_names = True

# If true, sectionauthor and moduleauthor directives will be shown in the
# output. They are ignored by default.
#show_authors = False

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = 'sphinx'

# A list of ignored prefixes for module index sorting.
#modindex_common_prefix = []


# -- Options for HTML output ---------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
html_theme = 'sphinxdoc'

# Theme options are theme-specific and customize the look and feel of a theme
# further.  For a list of options available for each theme, see the
# documentation.
#html_theme_options = {}

# Add any paths that contain custom themes here, relative to this directory.
#html_theme_path = []

# The name for this set of Sphinx documents.  If None, it defaults to
# "<project> v<release> documentation".
#html_title = None

# A shorter title for the navigation bar.  Default is the same as html_title.
#html_short_title = None

# The name of an image file (relative to this directory) to place at the top
# of the sidebar.
#html_logo = None

# The name of an image file (within the static path) to use as favicon of the
# docs.  This file should be a Windows icon file (.ico) being 16x16 or 32x32
# pixels large.
#html_favicon = None

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['_static']

# If not '', a 'Last updated on:' timestamp is inserted at every page bottom,
# using the given strftime format.
#html_last_updated_fmt = '%b %d, %Y'

# If true, SmartyPants will be used to convert quotes and dashes to
# typographically correct entities.
#html_use_smartypants = True

# Custom sidebar templates, maps document names to template names.
#html_sidebars = {}

# Additional templates that should be rendered to pages, maps page names to
# template names.
#html_additional_pages = {}

# If false, no module index is generated.
#html_domain_indices = True

# If false, no index is generated.
#html_use_index = True

# If true, the index is split into individual pages for each letter.
#html_split_index = False

# If true, links to the reST sources are added to the pages.
#html_show_sourcelink = True

# If true, "Created using Sphinx" is shown in the HTML footer. Default is True.
#html_show_sphinx = True

# If true, "(C) Copyright ..." is shown in the HTML footer. Default is True.
#html_show_copyright = True

# If true, an OpenSearch description file will be output, and all pages will
# contain a <link> tag referring to it.  The value of this option must be the
# base URL from which the finished HTML is served.
#html_use_opensearch = ''

# This is the file name suffix for HTML files (e.g. ".xhtml").
#html_file_suffix = None

# Output file base name for HTML help builder.
htmlhelp_basename = 'CassandraDriverdoc'


# -- Options for LaTeX output --------------------------------------------------

# The paper size ('letter' or 'a4').
#latex_paper_size = 'letter'

# The font size ('10pt', '11pt' or '12pt').
#latex_font_size = '10pt'

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, documentclass [howto/manual]).
latex_documents = [
    ('index', 'CassandraDriver.tex', u'Cassandra Driver Documentation',
     u'DataStax', 'manual'),
]

# The name of an image file (relative to this directory) to place at the top of
# the title page.
#latex_logo = None

# For "manual" documents, if this is true, then toplevel headings are parts,
# not chapters.
#latex_use_parts = False

# If true, show page references after internal links.
#latex_show_pagerefs = False

# If true, show URL addresses after external links.
#latex_show_urls = False

# Additional stuff for the LaTeX preamble.
#latex_preamble = ''

# Documents to append as an appendix to all manuals.
#latex_appendices = []

# If false, no module index is generated.
#latex_domain_indices = True


# -- Options for manual page output --------------------------------------------

# One entry per manual page. List of tuples
# (source start file, name, description, authors, manual section).
man_pages = [
    ('index', 'cassandradriver', u'Cassandra Driver Documentation',
     [u'Tyler Hobbs'], 1)
]

########NEW FILE########
__FILENAME__ = example
#!/usr/bin/env python

# Copyright 2013-2014 DataStax, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import logging

log = logging.getLogger()
log.setLevel('DEBUG')
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s"))
log.addHandler(handler)

from cassandra import ConsistencyLevel
from cassandra.cluster import Cluster
from cassandra.query import SimpleStatement

KEYSPACE = "testkeyspace"


def main():
    cluster = Cluster(['127.0.0.1'])
    session = cluster.connect()

    rows = session.execute("SELECT keyspace_name FROM system.schema_keyspaces")
    if KEYSPACE in [row[0] for row in rows]:
        log.info("dropping existing keyspace...")
        session.execute("DROP KEYSPACE " + KEYSPACE)

    log.info("creating keyspace...")
    session.execute("""
        CREATE KEYSPACE %s
        WITH replication = { 'class': 'SimpleStrategy', 'replication_factor': '2' }
        """ % KEYSPACE)

    log.info("setting keyspace...")
    session.set_keyspace(KEYSPACE)

    log.info("creating table...")
    session.execute("""
        CREATE TABLE mytable (
            thekey text,
            col1 text,
            col2 text,
            PRIMARY KEY (thekey, col1)
        )
        """)

    query = SimpleStatement("""
        INSERT INTO mytable (thekey, col1, col2)
        VALUES (%(key)s, %(a)s, %(b)s)
        """, consistency_level=ConsistencyLevel.ONE)

    prepared = session.prepare("""
        INSERT INTO mytable (thekey, col1, col2)
        VALUES (?, ?, ?)
        """)

    for i in range(10):
        log.info("inserting row %d" % i)
        session.execute(query, dict(key="key%d" % i, a='a', b='b'))
        session.execute(prepared, ("key%d" % i, 'b', 'b'))

    future = session.execute_async("SELECT * FROM mytable")
    log.info("key\tcol1\tcol2")
    log.info("---\t----\t----")

    try:
        rows = future.result()
    except Exception:
        log.exeception()

    for row in rows:
        log.info('\t'.join(row))

    session.execute("DROP KEYSPACE " + KEYSPACE)

if __name__ == "__main__":
    main()

########NEW FILE########
__FILENAME__ = test_consistency
# Copyright 2013-2014 DataStax, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import struct
import traceback

import cassandra
from cassandra import ConsistencyLevel
from cassandra.cluster import Cluster
from cassandra.policies import TokenAwarePolicy, RoundRobinPolicy, \
    DowngradingConsistencyRetryPolicy
from cassandra.query import SimpleStatement
from tests.integration import PROTOCOL_VERSION

from tests.integration.long.utils import force_stop, create_schema, \
    wait_for_down, wait_for_up, start, CoordinatorStats

try:
    import unittest2 as unittest
except ImportError:
    import unittest # noqa

ALL_CONSISTENCY_LEVELS = set([
    ConsistencyLevel.ANY, ConsistencyLevel.ONE, ConsistencyLevel.TWO,
    ConsistencyLevel.QUORUM, ConsistencyLevel.THREE,
    ConsistencyLevel.ALL, ConsistencyLevel.LOCAL_QUORUM,
    ConsistencyLevel.EACH_QUORUM])

MULTI_DC_CONSISTENCY_LEVELS = set([
    ConsistencyLevel.LOCAL_QUORUM, ConsistencyLevel.EACH_QUORUM])

SINGLE_DC_CONSISTENCY_LEVELS = ALL_CONSISTENCY_LEVELS - MULTI_DC_CONSISTENCY_LEVELS


class ConsistencyTests(unittest.TestCase):

    def setUp(self):
        self.coordinator_stats = CoordinatorStats()

    def _cl_failure(self, consistency_level, e):
        self.fail('Instead of success, saw %s for CL.%s:\n\n%s' % (
            e, ConsistencyLevel.value_to_name[consistency_level],
            traceback.format_exc()))

    def _cl_expected_failure(self, cl):
        self.fail('Test passed at ConsistencyLevel.%s:\n\n%s' % (
                  ConsistencyLevel.value_to_name[cl], traceback.format_exc()))

    def _insert(self, session, keyspace, count, consistency_level=ConsistencyLevel.ONE):
        session.execute('USE %s' % keyspace)
        for i in range(count):
            ss = SimpleStatement('INSERT INTO cf(k, i) VALUES (0, 0)',
                                 consistency_level=consistency_level)
            session.execute(ss)

    def _query(self, session, keyspace, count, consistency_level=ConsistencyLevel.ONE):
        routing_key = struct.pack('>i', 0)
        for i in range(count):
            ss = SimpleStatement('SELECT * FROM cf WHERE k = 0',
                                 consistency_level=consistency_level,
                                 routing_key=routing_key)
            self.coordinator_stats.add_coordinator(session.execute_async(ss))

    def _assert_writes_succeed(self, session, keyspace, consistency_levels):
        for cl in consistency_levels:
            self.coordinator_stats.reset_counts()
            try:
                self._insert(session, keyspace, 1, cl)
            except Exception as e:
                self._cl_failure(cl, e)

    def _assert_reads_succeed(self, session, keyspace, consistency_levels, expected_reader=3):
        for cl in consistency_levels:
            self.coordinator_stats.reset_counts()
            try:
                self._query(session, keyspace, 1, cl)
                for i in range(3):
                    if i == expected_reader:
                        self.coordinator_stats.assert_query_count_equals(self, i, 1)
                    else:
                        self.coordinator_stats.assert_query_count_equals(self, i, 0)
            except Exception as e:
                self._cl_failure(cl, e)

    def _assert_writes_fail(self, session, keyspace, consistency_levels):
        for cl in consistency_levels:
            self.coordinator_stats.reset_counts()
            try:
                self._insert(session, keyspace, 1, cl)
                self._cl_expected_failure(cl)
            except (cassandra.Unavailable, cassandra.WriteTimeout):
                pass

    def _assert_reads_fail(self, session, keyspace, consistency_levels):
        for cl in consistency_levels:
            self.coordinator_stats.reset_counts()
            try:
                self._query(session, keyspace, 1, cl)
                self._cl_expected_failure(cl)
            except (cassandra.Unavailable, cassandra.ReadTimeout):
                pass

    def _test_tokenaware_one_node_down(self, keyspace, rf, accepted):
        cluster = Cluster(
            load_balancing_policy=TokenAwarePolicy(RoundRobinPolicy()),
            protocol_version=PROTOCOL_VERSION)
        session = cluster.connect()
        wait_for_up(cluster, 1, wait=False)
        wait_for_up(cluster, 2)

        create_schema(session, keyspace, replication_factor=rf)
        self._insert(session, keyspace, count=1)
        self._query(session, keyspace, count=1)
        self.coordinator_stats.assert_query_count_equals(self, 1, 0)
        self.coordinator_stats.assert_query_count_equals(self, 2, 1)
        self.coordinator_stats.assert_query_count_equals(self, 3, 0)

        try:
            force_stop(2)
            wait_for_down(cluster, 2)

            self._assert_writes_succeed(session, keyspace, accepted)
            self._assert_reads_succeed(session, keyspace,
                    accepted - set([ConsistencyLevel.ANY]))
            self._assert_writes_fail(session, keyspace,
                    SINGLE_DC_CONSISTENCY_LEVELS - accepted)
            self._assert_reads_fail(session, keyspace,
                    SINGLE_DC_CONSISTENCY_LEVELS - accepted)
        finally:
            start(2)
            wait_for_up(cluster, 2)

    def test_rfone_tokenaware_one_node_down(self):
        self._test_tokenaware_one_node_down(
            keyspace='test_rfone_tokenaware',
            rf=1,
            accepted=set([ConsistencyLevel.ANY]))

    def test_rftwo_tokenaware_one_node_down(self):
        self._test_tokenaware_one_node_down(
            keyspace='test_rftwo_tokenaware',
            rf=2,
            accepted=set([ConsistencyLevel.ANY, ConsistencyLevel.ONE]))

    def test_rfthree_tokenaware_one_node_down(self):
        self._test_tokenaware_one_node_down(
            keyspace='test_rfthree_tokenaware',
            rf=3,
            accepted=set([ConsistencyLevel.ANY, ConsistencyLevel.ONE,
                          ConsistencyLevel.TWO, ConsistencyLevel.QUORUM]))

    def test_rfthree_tokenaware_none_down(self):
        keyspace = 'test_rfthree_tokenaware_none_down'
        cluster = Cluster(
            load_balancing_policy=TokenAwarePolicy(RoundRobinPolicy()),
            protocol_version=PROTOCOL_VERSION)
        session = cluster.connect()
        wait_for_up(cluster, 1, wait=False)
        wait_for_up(cluster, 2)

        create_schema(session, keyspace, replication_factor=3)
        self._insert(session, keyspace, count=1)
        self._query(session, keyspace, count=1)
        self.coordinator_stats.assert_query_count_equals(self, 1, 0)
        self.coordinator_stats.assert_query_count_equals(self, 2, 1)
        self.coordinator_stats.assert_query_count_equals(self, 3, 0)

        self.coordinator_stats.reset_counts()

        self._assert_writes_succeed(session, keyspace, SINGLE_DC_CONSISTENCY_LEVELS)
        self._assert_reads_succeed(session, keyspace,
                SINGLE_DC_CONSISTENCY_LEVELS - set([ConsistencyLevel.ANY]),
                expected_reader=2)

    def _test_downgrading_cl(self, keyspace, rf, accepted):
        cluster = Cluster(
            load_balancing_policy=TokenAwarePolicy(RoundRobinPolicy()),
            default_retry_policy=DowngradingConsistencyRetryPolicy(),
            protocol_version=PROTOCOL_VERSION)
        session = cluster.connect()

        create_schema(session, keyspace, replication_factor=rf)
        self._insert(session, keyspace, 1)
        self._query(session, keyspace, 1)
        self.coordinator_stats.assert_query_count_equals(self, 1, 0)
        self.coordinator_stats.assert_query_count_equals(self, 2, 1)
        self.coordinator_stats.assert_query_count_equals(self, 3, 0)

        try:
            force_stop(2)
            wait_for_down(cluster, 2)

            self._assert_writes_succeed(session, keyspace, accepted)
            self._assert_reads_succeed(session, keyspace,
                    accepted - set([ConsistencyLevel.ANY]))
            self._assert_writes_fail(session, keyspace,
                    SINGLE_DC_CONSISTENCY_LEVELS - accepted)
            self._assert_reads_fail(session, keyspace,
                    SINGLE_DC_CONSISTENCY_LEVELS - accepted)
        finally:
            start(2)
            wait_for_up(cluster, 2)

    def test_rfone_downgradingcl(self):
        self._test_downgrading_cl(
            keyspace='test_rfone_downgradingcl',
            rf=1,
            accepted=set([ConsistencyLevel.ANY]))

    def test_rftwo_downgradingcl(self):
        self._test_downgrading_cl(
            keyspace='test_rftwo_downgradingcl',
            rf=2,
            accepted=SINGLE_DC_CONSISTENCY_LEVELS)

    def test_rfthree_roundrobin_downgradingcl(self):
        keyspace = 'test_rfthree_roundrobin_downgradingcl'
        cluster = Cluster(
            load_balancing_policy=RoundRobinPolicy(),
            default_retry_policy=DowngradingConsistencyRetryPolicy(),
            protocol_version=PROTOCOL_VERSION)
        self.rfthree_downgradingcl(cluster, keyspace, True)

    def test_rfthree_tokenaware_downgradingcl(self):
        keyspace = 'test_rfthree_tokenaware_downgradingcl'
        cluster = Cluster(
            load_balancing_policy=TokenAwarePolicy(RoundRobinPolicy()),
            default_retry_policy=DowngradingConsistencyRetryPolicy(),
            protocol_version=PROTOCOL_VERSION)
        self.rfthree_downgradingcl(cluster, keyspace, False)

    def rfthree_downgradingcl(self, cluster, keyspace, roundrobin):
        session = cluster.connect()

        create_schema(session, keyspace, replication_factor=2)
        self._insert(session, keyspace, count=12)
        self._query(session, keyspace, count=12)

        if roundrobin:
            self.coordinator_stats.assert_query_count_equals(self, 1, 4)
            self.coordinator_stats.assert_query_count_equals(self, 2, 4)
            self.coordinator_stats.assert_query_count_equals(self, 3, 4)
        else:
            self.coordinator_stats.assert_query_count_equals(self, 1, 0)
            self.coordinator_stats.assert_query_count_equals(self, 2, 12)
            self.coordinator_stats.assert_query_count_equals(self, 3, 0)

        try:
            self.coordinator_stats.reset_counts()
            force_stop(2)
            wait_for_down(cluster, 2)

            self._assert_writes_succeed(session, keyspace, SINGLE_DC_CONSISTENCY_LEVELS)

            # Test reads that expected to complete successfully
            for cl in SINGLE_DC_CONSISTENCY_LEVELS - set([ConsistencyLevel.ANY]):
                self.coordinator_stats.reset_counts()
                self._query(session, keyspace, 12, consistency_level=cl)
                if roundrobin:
                    self.coordinator_stats.assert_query_count_equals(self, 1, 6)
                    self.coordinator_stats.assert_query_count_equals(self, 2, 0)
                    self.coordinator_stats.assert_query_count_equals(self, 3, 6)
                else:
                    self.coordinator_stats.assert_query_count_equals(self, 1, 0)
                    self.coordinator_stats.assert_query_count_equals(self, 2, 0)
                    self.coordinator_stats.assert_query_count_equals(self, 3, 12)
        finally:
            start(2)
            wait_for_up(cluster, 2)

    # TODO: can't be done in this class since we reuse the ccm cluster
    #       instead we should create these elsewhere
    # def test_rfthree_downgradingcl_twodcs(self):
    # def test_rfthree_downgradingcl_twodcs_dcaware(self):

########NEW FILE########
__FILENAME__ = test_large_data
# Copyright 2013-2014 DataStax, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

try:
    from Queue import Queue, Empty
except ImportError:
    from queue import Queue, Empty  # noqa

from struct import pack
import unittest

from cassandra import ConsistencyLevel
from cassandra.cluster import Cluster
from cassandra.query import dict_factory
from cassandra.query import SimpleStatement
from tests.integration import PROTOCOL_VERSION
from tests.integration.long.utils import create_schema


# Converts an integer to an string of letters
def create_column_name(i):
    letters = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j']

    column_name = ''
    while True:
        column_name += letters[i % 10]
        i = i // 10
        if not i:
            break

    if column_name == 'if':
        column_name = 'special_case'
    return column_name


class LargeDataTests(unittest.TestCase):

    def setUp(self):
        self.keyspace = 'large_data'

    def make_session_and_keyspace(self):
        cluster = Cluster(protocol_version=PROTOCOL_VERSION)
        session = cluster.connect()
        session.default_timeout = 20.0  # increase the default timeout
        session.row_factory = dict_factory

        create_schema(session, self.keyspace)
        return session

    def batch_futures(self, session, statement_generator):
        concurrency = 10
        futures = Queue(maxsize=concurrency)
        for i, statement in enumerate(statement_generator):
            if i > 0 and i % (concurrency - 1) == 0:
                # clear the existing queue
                while True:
                    try:
                        futures.get_nowait().result()
                    except Empty:
                        break

            future = session.execute_async(statement)
            futures.put_nowait(future)

        while True:
            try:
                futures.get_nowait().result()
            except Empty:
                break

    def test_wide_rows(self):
        table = 'wide_rows'
        session = self.make_session_and_keyspace()
        session.execute('CREATE TABLE %s (k INT, i INT, PRIMARY KEY(k, i))' % table)

        prepared = session.prepare('INSERT INTO %s (k, i) VALUES (0, ?)' % (table, ))

        # Write via async futures
        self.batch_futures(session, (prepared.bind((i, )) for i in range(100000)))

        # Read
        results = session.execute('SELECT i FROM %s WHERE k=0' % (table, ))

        # Verify
        for i, row in enumerate(results):
            self.assertEqual(row['i'], i)

    def test_wide_batch_rows(self):
        table = 'wide_batch_rows'
        session = self.make_session_and_keyspace()
        session.execute('CREATE TABLE %s (k INT, i INT, PRIMARY KEY(k, i))' % table)

        # Write
        statement = 'BEGIN BATCH '
        for i in range(2000):
            statement += 'INSERT INTO %s (k, i) VALUES (%s, %s) ' % (table, 0, i)
        statement += 'APPLY BATCH'
        statement = SimpleStatement(statement, consistency_level=ConsistencyLevel.QUORUM)
        session.execute(statement)

        # Read
        results = session.execute('SELECT i FROM %s WHERE k=%s' % (table, 0))

        # Verify
        for i, row in enumerate(results):
            self.assertEqual(row['i'], i)

    def test_wide_byte_rows(self):
        table = 'wide_byte_rows'
        session = self.make_session_and_keyspace()
        session.execute('CREATE TABLE %s (k INT, i INT, v BLOB, PRIMARY KEY(k, i))' % table)

        prepared = session.prepare('INSERT INTO %s (k, i, v) VALUES (0, ?, 0xCAFE)' % (table, ))

        # Write
        self.batch_futures(session, (prepared.bind((i, )) for i in range(100000)))

        # Read
        results = session.execute('SELECT i, v FROM %s WHERE k=0' % (table, ))

        # Verify
        bb = pack('>H', 0xCAFE)
        for row in results:
            self.assertEqual(row['v'], bb)

    def test_large_text(self):
        table = 'large_text'
        session = self.make_session_and_keyspace()
        session.execute('CREATE TABLE %s (k int PRIMARY KEY, txt text)' % table)

        # Create ultra-long text
        text = 'a' * 1000000

        # Write
        session.execute(SimpleStatement("INSERT INTO %s (k, txt) VALUES (%s, '%s')"
                                        % (table, 0, text),
                                        consistency_level=ConsistencyLevel.QUORUM))

        # Read
        result = session.execute('SELECT * FROM %s WHERE k=%s' % (table, 0))

        # Verify
        for row in result:
            self.assertEqual(row['txt'], text)

    def test_wide_table(self):
        table = 'wide_table'
        table_width = 330
        session = self.make_session_and_keyspace()
        table_declaration = 'CREATE TABLE %s (key INT PRIMARY KEY, '
        table_declaration += ' INT, '.join(create_column_name(i) for i in range(table_width))
        table_declaration += ' INT)'
        session.execute(table_declaration % table)

        # Write
        insert_statement = 'INSERT INTO %s (key, '
        insert_statement += ', '.join(create_column_name(i) for i in range(table_width))
        insert_statement += ') VALUES (%s, '
        insert_statement += ', '.join(str(i) for i in range(table_width))
        insert_statement += ')'
        insert_statement = insert_statement % (table, 0)

        session.execute(SimpleStatement(insert_statement, consistency_level=ConsistencyLevel.QUORUM))

        # Read
        result = session.execute('SELECT * FROM %s WHERE key=%s' % (table, 0))

        # Verify
        for row in result:
            for i in range(table_width):
                self.assertEqual(row[create_column_name(i)], i)

########NEW FILE########
__FILENAME__ = test_loadbalancingpolicies
# Copyright 2013-2014 DataStax, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import struct
from cassandra import ConsistencyLevel, Unavailable
from cassandra.cluster import Cluster, NoHostAvailable
from cassandra.concurrent import execute_concurrent_with_args
from cassandra.policies import (RoundRobinPolicy, DCAwareRoundRobinPolicy,
                                TokenAwarePolicy, WhiteListRoundRobinPolicy)
from cassandra.query import SimpleStatement

from tests.integration import use_multidc, use_singledc, PROTOCOL_VERSION
from tests.integration.long.utils import (wait_for_up, create_schema,
                                          CoordinatorStats, force_stop,
                                          wait_for_down, decommission, start,
                                          bootstrap, stop, IP_FORMAT)

try:
    import unittest2 as unittest
except ImportError:
    import unittest  # noqa


class LoadBalancingPolicyTests(unittest.TestCase):
    def setUp(self):
        self.coordinator_stats = CoordinatorStats()
        self.prepared = None

    @classmethod
    def tearDownClass(cls):
        use_singledc()

    def _insert(self, session, keyspace, count=12,
                consistency_level=ConsistencyLevel.ONE):
        session.execute('USE %s' % keyspace)
        ss = SimpleStatement('INSERT INTO cf(k, i) VALUES (0, 0)',
                             consistency_level=consistency_level)
        execute_concurrent_with_args(session, ss, [None] * count)

    def _query(self, session, keyspace, count=12,
               consistency_level=ConsistencyLevel.ONE, use_prepared=False):
        if use_prepared:
            query_string = 'SELECT * FROM %s.cf WHERE k = ?' % keyspace
            if not self.prepared or self.prepared.query_string != query_string:
                self.prepared = session.prepare(query_string)

            for i in range(count):
                self.coordinator_stats.add_coordinator(session.execute_async(self.prepared.bind((0,))))
        else:
            routing_key = struct.pack('>i', 0)
            for i in range(count):
                ss = SimpleStatement('SELECT * FROM %s.cf WHERE k = 0' % keyspace,
                                     consistency_level=consistency_level,
                                     routing_key=routing_key)
                self.coordinator_stats.add_coordinator(session.execute_async(ss))

    def test_roundrobin(self):
        use_singledc()
        keyspace = 'test_roundrobin'
        cluster = Cluster(
            load_balancing_policy=RoundRobinPolicy(),
            protocol_version=PROTOCOL_VERSION)
        session = cluster.connect()
        wait_for_up(cluster, 1, wait=False)
        wait_for_up(cluster, 2, wait=False)
        wait_for_up(cluster, 3)

        create_schema(session, keyspace, replication_factor=3)
        self._insert(session, keyspace)
        self._query(session, keyspace)

        self.coordinator_stats.assert_query_count_equals(self, 1, 4)
        self.coordinator_stats.assert_query_count_equals(self, 2, 4)
        self.coordinator_stats.assert_query_count_equals(self, 3, 4)

        force_stop(3)
        wait_for_down(cluster, 3)

        self.coordinator_stats.reset_counts()
        self._query(session, keyspace)

        self.coordinator_stats.assert_query_count_equals(self, 1, 6)
        self.coordinator_stats.assert_query_count_equals(self, 2, 6)
        self.coordinator_stats.assert_query_count_equals(self, 3, 0)

        decommission(1)
        start(3)
        wait_for_down(cluster, 1)
        wait_for_up(cluster, 3)

        self.coordinator_stats.reset_counts()
        self._query(session, keyspace)

        self.coordinator_stats.assert_query_count_equals(self, 1, 0)
        self.coordinator_stats.assert_query_count_equals(self, 2, 6)
        self.coordinator_stats.assert_query_count_equals(self, 3, 6)

    def test_roundrobin_two_dcs(self):
        use_multidc([2, 2])
        keyspace = 'test_roundrobin_two_dcs'
        cluster = Cluster(
            load_balancing_policy=RoundRobinPolicy(),
            protocol_version=PROTOCOL_VERSION)
        session = cluster.connect()
        wait_for_up(cluster, 1, wait=False)
        wait_for_up(cluster, 2, wait=False)
        wait_for_up(cluster, 3, wait=False)
        wait_for_up(cluster, 4)

        create_schema(session, keyspace, replication_strategy=[2, 2])
        self._insert(session, keyspace)
        self._query(session, keyspace)

        self.coordinator_stats.assert_query_count_equals(self, 1, 3)
        self.coordinator_stats.assert_query_count_equals(self, 2, 3)
        self.coordinator_stats.assert_query_count_equals(self, 3, 3)
        self.coordinator_stats.assert_query_count_equals(self, 4, 3)

        force_stop(1)
        bootstrap(5, 'dc3')

        # reset control connection
        self._insert(session, keyspace, count=1000)

        wait_for_up(cluster, 5)

        self.coordinator_stats.reset_counts()
        self._query(session, keyspace)

        self.coordinator_stats.assert_query_count_equals(self, 1, 0)
        self.coordinator_stats.assert_query_count_equals(self, 2, 3)
        self.coordinator_stats.assert_query_count_equals(self, 3, 3)
        self.coordinator_stats.assert_query_count_equals(self, 4, 3)
        self.coordinator_stats.assert_query_count_equals(self, 5, 3)

    def test_roundrobin_two_dcs_2(self):
        use_multidc([2, 2])
        keyspace = 'test_roundrobin_two_dcs_2'
        cluster = Cluster(
            load_balancing_policy=RoundRobinPolicy(),
            protocol_version=PROTOCOL_VERSION)
        session = cluster.connect()
        wait_for_up(cluster, 1, wait=False)
        wait_for_up(cluster, 2, wait=False)
        wait_for_up(cluster, 3, wait=False)
        wait_for_up(cluster, 4)

        create_schema(session, keyspace, replication_strategy=[2, 2])
        self._insert(session, keyspace)
        self._query(session, keyspace)

        self.coordinator_stats.assert_query_count_equals(self, 1, 3)
        self.coordinator_stats.assert_query_count_equals(self, 2, 3)
        self.coordinator_stats.assert_query_count_equals(self, 3, 3)
        self.coordinator_stats.assert_query_count_equals(self, 4, 3)

        force_stop(1)
        bootstrap(5, 'dc1')

        # reset control connection
        self._insert(session, keyspace, count=1000)

        wait_for_up(cluster, 5)

        self.coordinator_stats.reset_counts()
        self._query(session, keyspace)

        self.coordinator_stats.assert_query_count_equals(self, 1, 0)
        self.coordinator_stats.assert_query_count_equals(self, 2, 3)
        self.coordinator_stats.assert_query_count_equals(self, 3, 3)
        self.coordinator_stats.assert_query_count_equals(self, 4, 3)
        self.coordinator_stats.assert_query_count_equals(self, 5, 3)

    def test_dc_aware_roundrobin_two_dcs(self):
        use_multidc([3, 2])
        keyspace = 'test_dc_aware_roundrobin_two_dcs'
        cluster = Cluster(
            load_balancing_policy=DCAwareRoundRobinPolicy('dc1'),
            protocol_version=PROTOCOL_VERSION)
        session = cluster.connect()
        wait_for_up(cluster, 1, wait=False)
        wait_for_up(cluster, 2, wait=False)
        wait_for_up(cluster, 3, wait=False)
        wait_for_up(cluster, 4, wait=False)
        wait_for_up(cluster, 5)

        create_schema(session, keyspace, replication_strategy=[2, 2])
        self._insert(session, keyspace)
        self._query(session, keyspace)

        self.coordinator_stats.assert_query_count_equals(self, 1, 4)
        self.coordinator_stats.assert_query_count_equals(self, 2, 4)
        self.coordinator_stats.assert_query_count_equals(self, 3, 4)
        self.coordinator_stats.assert_query_count_equals(self, 4, 0)
        self.coordinator_stats.assert_query_count_equals(self, 5, 0)

    def test_dc_aware_roundrobin_two_dcs_2(self):
        use_multidc([3, 2])
        keyspace = 'test_dc_aware_roundrobin_two_dcs_2'
        cluster = Cluster(
            load_balancing_policy=DCAwareRoundRobinPolicy('dc2'),
            protocol_version=PROTOCOL_VERSION)
        session = cluster.connect()
        wait_for_up(cluster, 1, wait=False)
        wait_for_up(cluster, 2, wait=False)
        wait_for_up(cluster, 3, wait=False)
        wait_for_up(cluster, 4, wait=False)
        wait_for_up(cluster, 5)

        create_schema(session, keyspace, replication_strategy=[2, 2])
        self._insert(session, keyspace)
        self._query(session, keyspace)

        self.coordinator_stats.assert_query_count_equals(self, 1, 0)
        self.coordinator_stats.assert_query_count_equals(self, 2, 0)
        self.coordinator_stats.assert_query_count_equals(self, 3, 0)
        self.coordinator_stats.assert_query_count_equals(self, 4, 6)
        self.coordinator_stats.assert_query_count_equals(self, 5, 6)

    def test_dc_aware_roundrobin_one_remote_host(self):
        use_multidc([2, 2])
        keyspace = 'test_dc_aware_roundrobin_one_remote_host'
        cluster = Cluster(
            load_balancing_policy=DCAwareRoundRobinPolicy('dc2', used_hosts_per_remote_dc=1),
            protocol_version=PROTOCOL_VERSION)
        session = cluster.connect()
        wait_for_up(cluster, 1, wait=False)
        wait_for_up(cluster, 2, wait=False)
        wait_for_up(cluster, 3, wait=False)
        wait_for_up(cluster, 4)

        create_schema(session, keyspace, replication_strategy=[2, 2])
        self._insert(session, keyspace)
        self._query(session, keyspace)

        self.coordinator_stats.assert_query_count_equals(self, 1, 0)
        self.coordinator_stats.assert_query_count_equals(self, 2, 0)
        self.coordinator_stats.assert_query_count_equals(self, 3, 6)
        self.coordinator_stats.assert_query_count_equals(self, 4, 6)

        self.coordinator_stats.reset_counts()
        bootstrap(5, 'dc1')
        wait_for_up(cluster, 5)

        self._query(session, keyspace)

        self.coordinator_stats.assert_query_count_equals(self, 1, 0)
        self.coordinator_stats.assert_query_count_equals(self, 2, 0)
        self.coordinator_stats.assert_query_count_equals(self, 3, 6)
        self.coordinator_stats.assert_query_count_equals(self, 4, 6)
        self.coordinator_stats.assert_query_count_equals(self, 5, 0)

        self.coordinator_stats.reset_counts()
        decommission(3)
        decommission(4)
        wait_for_down(cluster, 3, wait=True)
        wait_for_down(cluster, 4, wait=True)

        self._query(session, keyspace)

        self.coordinator_stats.assert_query_count_equals(self, 3, 0)
        self.coordinator_stats.assert_query_count_equals(self, 4, 0)
        responses = set()
        for node in [1, 2, 5]:
            responses.add(self.coordinator_stats.get_query_count(node))
        self.assertEqual(set([0, 0, 12]), responses)

        self.coordinator_stats.reset_counts()
        decommission(5)
        wait_for_down(cluster, 5, wait=True)

        self._query(session, keyspace)

        self.coordinator_stats.assert_query_count_equals(self, 3, 0)
        self.coordinator_stats.assert_query_count_equals(self, 4, 0)
        self.coordinator_stats.assert_query_count_equals(self, 5, 0)
        responses = set()
        for node in [1, 2]:
            responses.add(self.coordinator_stats.get_query_count(node))
        self.assertEqual(set([0, 12]), responses)

        self.coordinator_stats.reset_counts()
        decommission(1)
        wait_for_down(cluster, 1, wait=True)

        self._query(session, keyspace)

        self.coordinator_stats.assert_query_count_equals(self, 1, 0)
        self.coordinator_stats.assert_query_count_equals(self, 2, 12)
        self.coordinator_stats.assert_query_count_equals(self, 3, 0)
        self.coordinator_stats.assert_query_count_equals(self, 4, 0)
        self.coordinator_stats.assert_query_count_equals(self, 5, 0)

        self.coordinator_stats.reset_counts()
        force_stop(2)

        try:
            self._query(session, keyspace)
            self.fail()
        except NoHostAvailable:
            pass

    def test_token_aware(self):
        keyspace = 'test_token_aware'
        self.token_aware(keyspace)

    def test_token_aware_prepared(self):
        keyspace = 'test_token_aware_prepared'
        self.token_aware(keyspace, True)

    def token_aware(self, keyspace, use_prepared=False):
        use_singledc()
        cluster = Cluster(
            load_balancing_policy=TokenAwarePolicy(RoundRobinPolicy()),
            protocol_version=PROTOCOL_VERSION)
        session = cluster.connect()
        wait_for_up(cluster, 1, wait=False)
        wait_for_up(cluster, 2, wait=False)
        wait_for_up(cluster, 3)

        create_schema(session, keyspace, replication_factor=1)
        self._insert(session, keyspace)
        self._query(session, keyspace, use_prepared=use_prepared)

        self.coordinator_stats.assert_query_count_equals(self, 1, 0)
        self.coordinator_stats.assert_query_count_equals(self, 2, 12)
        self.coordinator_stats.assert_query_count_equals(self, 3, 0)

        self.coordinator_stats.reset_counts()
        self._query(session, keyspace, use_prepared=use_prepared)

        self.coordinator_stats.assert_query_count_equals(self, 1, 0)
        self.coordinator_stats.assert_query_count_equals(self, 2, 12)
        self.coordinator_stats.assert_query_count_equals(self, 3, 0)

        self.coordinator_stats.reset_counts()
        force_stop(2)
        wait_for_down(cluster, 2, wait=True)

        try:
            self._query(session, keyspace, use_prepared=use_prepared)
            self.fail()
        except Unavailable as e:
            self.assertEqual(e.consistency, 1)
            self.assertEqual(e.required_replicas, 1)
            self.assertEqual(e.alive_replicas, 0)

        self.coordinator_stats.reset_counts()
        start(2)
        wait_for_up(cluster, 2, wait=True)

        self._query(session, keyspace, use_prepared=use_prepared)

        self.coordinator_stats.assert_query_count_equals(self, 1, 0)
        self.coordinator_stats.assert_query_count_equals(self, 2, 12)
        self.coordinator_stats.assert_query_count_equals(self, 3, 0)

        self.coordinator_stats.reset_counts()
        stop(2)
        wait_for_down(cluster, 2, wait=True)

        try:
            self._query(session, keyspace, use_prepared=use_prepared)
            self.fail()
        except Unavailable:
            pass

        self.coordinator_stats.reset_counts()
        start(2)
        wait_for_up(cluster, 2, wait=True)
        decommission(2)
        wait_for_down(cluster, 2, wait=True)

        self._query(session, keyspace, use_prepared=use_prepared)

        results = set([
            self.coordinator_stats.get_query_count(1),
            self.coordinator_stats.get_query_count(3)
        ])
        self.assertEqual(results, set([0, 12]))
        self.coordinator_stats.assert_query_count_equals(self, 2, 0)

    def test_token_aware_composite_key(self):
        use_singledc()
        keyspace = 'test_token_aware_composite_key'
        table = 'composite'
        cluster = Cluster(
            load_balancing_policy=TokenAwarePolicy(RoundRobinPolicy()),
            protocol_version=PROTOCOL_VERSION)
        session = cluster.connect()
        wait_for_up(cluster, 1, wait=False)
        wait_for_up(cluster, 2, wait=False)
        wait_for_up(cluster, 3)

        create_schema(session, keyspace, replication_factor=2)
        session.execute('CREATE TABLE %s ('
                        'k1 int, '
                        'k2 int, '
                        'i int, '
                        'PRIMARY KEY ((k1, k2)))' % table)

        prepared = session.prepare('INSERT INTO %s '
                                   '(k1, k2, i) '
                                   'VALUES '
                                   '(?, ?, ?)' % table)
        session.execute(prepared.bind((1, 2, 3)))

        results = session.execute('SELECT * FROM %s WHERE k1 = 1 AND k2 = 2' % table)
        self.assertTrue(len(results) == 1)
        self.assertTrue(results[0].i)

    def test_token_aware_with_rf_2(self, use_prepared=False):
        use_singledc()
        keyspace = 'test_token_aware_with_rf_2'
        cluster = Cluster(
            load_balancing_policy=TokenAwarePolicy(RoundRobinPolicy()),
            protocol_version=PROTOCOL_VERSION)
        session = cluster.connect()
        wait_for_up(cluster, 1, wait=False)
        wait_for_up(cluster, 2, wait=False)
        wait_for_up(cluster, 3)

        create_schema(session, keyspace, replication_factor=2)
        self._insert(session, keyspace)
        self._query(session, keyspace)

        self.coordinator_stats.assert_query_count_equals(self, 1, 0)
        self.coordinator_stats.assert_query_count_equals(self, 2, 12)
        self.coordinator_stats.assert_query_count_equals(self, 3, 0)

        self.coordinator_stats.reset_counts()
        stop(2)
        wait_for_down(cluster, 2, wait=True)

        self._query(session, keyspace)

        self.coordinator_stats.assert_query_count_equals(self, 1, 0)
        self.coordinator_stats.assert_query_count_equals(self, 2, 0)
        self.coordinator_stats.assert_query_count_equals(self, 3, 12)

    def test_white_list(self):
        use_singledc()
        keyspace = 'test_white_list'

        cluster = Cluster(('127.0.0.2',),
            load_balancing_policy=WhiteListRoundRobinPolicy((IP_FORMAT % 2,)),
            protocol_version=PROTOCOL_VERSION)
        session = cluster.connect()
        wait_for_up(cluster, 1, wait=False)
        wait_for_up(cluster, 2, wait=False)
        wait_for_up(cluster, 3)

        create_schema(session, keyspace)
        self._insert(session, keyspace)
        self._query(session, keyspace)

        self.coordinator_stats.assert_query_count_equals(self, 1, 0)
        self.coordinator_stats.assert_query_count_equals(self, 2, 12)
        self.coordinator_stats.assert_query_count_equals(self, 3, 0)

        self.coordinator_stats.reset_counts()
        decommission(2)
        wait_for_down(cluster, 2, wait=True)

        try:
            self._query(session, keyspace)
            self.fail()
        except NoHostAvailable:
            pass

########NEW FILE########
__FILENAME__ = test_schema
# Copyright 2013-2014 DataStax, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import logging

from cassandra import ConsistencyLevel, OperationTimedOut
from cassandra.cluster import Cluster
from cassandra.query import SimpleStatement
from tests.integration import PROTOCOL_VERSION

try:
    import unittest2 as unittest
except ImportError:
    import unittest # noqa

log = logging.getLogger(__name__)


class SchemaTests(unittest.TestCase):

    def test_recreates(self):
        cluster = Cluster(protocol_version=PROTOCOL_VERSION)
        session = cluster.connect()
        replication_factor = 3

        for i in range(2):
            for keyspace in range(5):
                keyspace = 'ks_%s' % keyspace
                results = session.execute('SELECT keyspace_name FROM system.schema_keyspaces')
                existing_keyspaces = [row[0] for row in results]
                if keyspace in existing_keyspaces:
                    ddl = 'DROP KEYSPACE %s' % keyspace
                    log.debug(ddl)
                    session.execute(ddl)

                ddl = """
                    CREATE KEYSPACE %s
                    WITH replication = {'class': 'SimpleStrategy', 'replication_factor': '%s'}
                    """ % (keyspace, str(replication_factor))
                log.debug(ddl)
                session.execute(ddl)

                ddl = 'CREATE TABLE %s.cf (k int PRIMARY KEY, i int)' % keyspace
                log.debug(ddl)
                session.execute(ddl)

                statement = 'USE %s' % keyspace
                log.debug(ddl)
                session.execute(statement)

                statement = 'INSERT INTO %s(k, i) VALUES (0, 0)' % 'cf'
                log.debug(statement)
                ss = SimpleStatement(statement,
                                     consistency_level=ConsistencyLevel.QUORUM)
                session.execute(ss)

    def test_for_schema_disagreements_different_keyspaces(self):
        cluster = Cluster(protocol_version=PROTOCOL_VERSION)
        session = cluster.connect()

        for i in xrange(30):
            try:
                session.execute('''
                    CREATE KEYSPACE test_%s
                    WITH replication = {'class': 'SimpleStrategy',
                                        'replication_factor': 1}
                ''' % i)

                session.execute('''
                    CREATE TABLE test_%s.cf (
                        key int,
                        value int,
                        PRIMARY KEY (key))
                ''' % i)

                for j in xrange(100):
                    session.execute('INSERT INTO test_%s.cf (key, value) VALUES (%s, %s)' % (i, j, j))

                session.execute('''
                    DROP KEYSPACE test_%s
                ''' % i)
            except OperationTimedOut: pass

    def test_for_schema_disagreements_same_keyspace(self):
        cluster = Cluster(protocol_version=PROTOCOL_VERSION)
        session = cluster.connect()

        for i in xrange(30):
            try:
                session.execute('''
                    CREATE KEYSPACE test
                    WITH replication = {'class': 'SimpleStrategy',
                                        'replication_factor': 1}
                ''')

                session.execute('''
                    CREATE TABLE test.cf (
                        key int,
                        value int,
                        PRIMARY KEY (key))
                ''')

                for j in xrange(100):
                    session.execute('INSERT INTO test.cf (key, value) VALUES (%s, %s)' % (j, j))

                session.execute('''
                    DROP KEYSPACE test
                ''')
            except OperationTimedOut: pass

########NEW FILE########
__FILENAME__ = utils
# Copyright 2013-2014 DataStax, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import print_function
import logging
import time

from collections import defaultdict
from ccmlib.node import Node

from cassandra.query import named_tuple_factory

from tests.integration import get_node, get_cluster

IP_FORMAT = '127.0.0.%s'

log = logging.getLogger(__name__)


class CoordinatorStats():

    def __init__(self):
        self.coordinator_counts = defaultdict(int)

    def add_coordinator(self, future):
        future.result()
        coordinator = future._current_host.address
        self.coordinator_counts[coordinator] += 1

        if future._errors:
            log.error('future._errors: %s', future._errors)

    def reset_counts(self):
        self.coordinator_counts = defaultdict(int)

    def get_query_count(self, node):
        ip = '127.0.0.%d' % node
        return self.coordinator_counts[ip]

    def assert_query_count_equals(self, testcase, node, expected):
        ip = '127.0.0.%d' % node
        if self.get_query_count(node) != expected:
            testcase.fail('Expected %d queries to %s, but got %d. Query counts: %s' % (
                expected, ip, self.coordinator_counts[ip], dict(self.coordinator_counts)))


def create_schema(session, keyspace, simple_strategy=True,
                  replication_factor=1, replication_strategy=None):
    row_factory = session.row_factory
    session.row_factory = named_tuple_factory

    results = session.execute(
        'SELECT keyspace_name FROM system.schema_keyspaces')
    existing_keyspaces = [row[0] for row in results]
    if keyspace in existing_keyspaces:
        session.execute('DROP KEYSPACE %s' % keyspace, timeout=20)

    if simple_strategy:
        ddl = "CREATE KEYSPACE %s WITH replication" \
              " = {'class': 'SimpleStrategy', 'replication_factor': '%s'}"
        session.execute(ddl % (keyspace, replication_factor), timeout=10)
    else:
        if not replication_strategy:
            raise Exception('replication_strategy is not set')

        ddl = "CREATE KEYSPACE %s" \
              " WITH replication = { 'class' : 'NetworkTopologyStrategy', %s }"
        session.execute(ddl % (keyspace, str(replication_strategy)[1:-1]), timeout=10)

    ddl = 'CREATE TABLE %s.cf (k int PRIMARY KEY, i int)'
    session.execute(ddl % keyspace, timeout=10)
    session.execute('USE %s' % keyspace)

    session.row_factory = row_factory


def start(node):
    get_node(node).start()


def stop(node):
    get_node(node).stop()


def force_stop(node):
    log.debug("Forcing stop of node %s", node)
    get_node(node).stop(wait=False, gently=False)
    log.debug("Node %s was stopped", node)


def decommission(node):
    get_node(node).decommission()
    get_node(node).stop()


def bootstrap(node, data_center=None, token=None):
    node_instance = Node('node%s' % node,
                         get_cluster(),
                         auto_bootstrap=False,
                         thrift_interface=(IP_FORMAT % node, 9160),
                         storage_interface=(IP_FORMAT % node, 7000),
                         jmx_port=str(7000 + 100 * node),
                         remote_debug_port=0,
                         initial_token=token if token else node * 10)
    get_cluster().add(node_instance, is_seed=False, data_center=data_center)

    try:
        start(node)
    except:
        # Try only twice
        try:
            start(node)
        except:
            log.error('Added node failed to start twice.')


def ring(node):
    print('From node%s:' % node)
    get_node(node).nodetool('ring')


def wait_for_up(cluster, node, wait=True):
    while True:
        host = cluster.metadata.get_host(IP_FORMAT % node)
        time.sleep(0.1)
        if host and host.is_up:
            # BUG: shouldn't have to, but we do
            if wait:
                log.debug("Sleeping 30s until host is up")
                time.sleep(30)
            log.debug("Done waiting for node %s to be up", node)
            return


def wait_for_down(cluster, node, wait=True):
    log.debug("Waiting for node %s to be down", node)
    while True:
        host = cluster.metadata.get_host(IP_FORMAT % node)
        time.sleep(0.1)
        if not host or not host.is_up:
            # BUG: shouldn't have to, but we do
            if wait:
                log.debug("Sleeping 10s until host is down")
                time.sleep(10)
            log.debug("Done waiting for node %s to be down", node)
            return
        else:
            log.debug("Host is still marked up, waiting")

########NEW FILE########
__FILENAME__ = test_cluster
# Copyright 2013-2014 DataStax, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from tests.integration import PROTOCOL_VERSION

try:
    import unittest2 as unittest
except ImportError:
    import unittest # noqa

import cassandra
from cassandra.query import SimpleStatement, TraceUnavailable
from cassandra.policies import RoundRobinPolicy, ExponentialReconnectionPolicy, RetryPolicy, SimpleConvictionPolicy, HostDistance

from cassandra.cluster import Cluster, NoHostAvailable


class ClusterTests(unittest.TestCase):

    def test_basic(self):
        """
        Test basic connection and usage
        """

        cluster = Cluster(protocol_version=PROTOCOL_VERSION)
        session = cluster.connect()
        result = session.execute(
            """
            CREATE KEYSPACE clustertests
            WITH replication = {'class': 'SimpleStrategy', 'replication_factor': '1'}
            """)
        self.assertEqual(None, result)

        result = session.execute(
            """
            CREATE TABLE clustertests.cf0 (
                a text,
                b text,
                c text,
                PRIMARY KEY (a, b)
            )
            """)
        self.assertEqual(None, result)

        result = session.execute(
            """
            INSERT INTO clustertests.cf0 (a, b, c) VALUES ('a', 'b', 'c')
            """)
        self.assertEqual(None, result)

        result = session.execute("SELECT * FROM clustertests.cf0")
        self.assertEqual([('a', 'b', 'c')], result)

        cluster.shutdown()

    def test_connect_on_keyspace(self):
        """
        Ensure clusters that connect on a keyspace, do
        """

        cluster = Cluster(protocol_version=PROTOCOL_VERSION)
        session = cluster.connect()
        result = session.execute(
            """
            INSERT INTO test3rf.test (k, v) VALUES (8889, 8889)
            """)
        self.assertEqual(None, result)

        result = session.execute("SELECT * FROM test3rf.test")
        self.assertEqual([(8889, 8889)], result)

        # test_connect_on_keyspace
        session2 = cluster.connect('test3rf')
        result2 = session2.execute("SELECT * FROM test")
        self.assertEqual(result, result2)

    def test_set_keyspace_twice(self):
        cluster = Cluster(protocol_version=PROTOCOL_VERSION)
        session = cluster.connect()
        session.execute("USE system")
        session.execute("USE system")

    def test_default_connections(self):
        """
        Ensure errors are not thrown when using non-default policies
        """

        Cluster(
            load_balancing_policy=RoundRobinPolicy(),
            reconnection_policy=ExponentialReconnectionPolicy(1.0, 600.0),
            default_retry_policy=RetryPolicy(),
            conviction_policy_factory=SimpleConvictionPolicy,
            protocol_version=PROTOCOL_VERSION
        )

    def test_connect_to_already_shutdown_cluster(self):
        """
        Ensure you cannot connect to a cluster that's been shutdown
        """

        cluster = Cluster(protocol_version=PROTOCOL_VERSION)
        cluster.shutdown()
        self.assertRaises(Exception, cluster.connect)

    def test_auth_provider_is_callable(self):
        """
        Ensure that auth_providers are always callable
        """
        self.assertRaises(TypeError, Cluster, auth_provider=1, protocol_version=1)
        c = Cluster(protocol_version=1)
        self.assertRaises(TypeError, setattr, c, 'auth_provider', 1)

    def test_v2_auth_provider(self):
        """
        Check for v2 auth_provider compliance
        """
        bad_auth_provider = lambda x: {'username': 'foo', 'password': 'bar'}
        self.assertRaises(TypeError, Cluster, auth_provider=bad_auth_provider, protocol_version=2)
        c = Cluster(protocol_version=2)
        self.assertRaises(TypeError, setattr, c, 'auth_provider', bad_auth_provider)

    def test_conviction_policy_factory_is_callable(self):
        """
        Ensure that conviction_policy_factory are always callable
        """

        self.assertRaises(ValueError, Cluster, conviction_policy_factory=1)

    def test_connect_to_bad_hosts(self):
        """
        Ensure that a NoHostAvailable Exception is thrown
        when a cluster cannot connect to given hosts
        """

        cluster = Cluster(['127.1.2.9', '127.1.2.10'],
                          protocol_version=PROTOCOL_VERSION)
        self.assertRaises(NoHostAvailable, cluster.connect)

    def test_cluster_settings(self):
        """
        Test connection setting getters and setters
        """

        cluster = Cluster(protocol_version=PROTOCOL_VERSION)

        min_requests_per_connection = cluster.get_min_requests_per_connection(HostDistance.LOCAL)
        self.assertEqual(cassandra.cluster.DEFAULT_MIN_REQUESTS, min_requests_per_connection)
        cluster.set_min_requests_per_connection(HostDistance.LOCAL, min_requests_per_connection + 1)
        self.assertEqual(cluster.get_min_requests_per_connection(HostDistance.LOCAL), min_requests_per_connection + 1)

        max_requests_per_connection = cluster.get_max_requests_per_connection(HostDistance.LOCAL)
        self.assertEqual(cassandra.cluster.DEFAULT_MAX_REQUESTS, max_requests_per_connection)
        cluster.set_max_requests_per_connection(HostDistance.LOCAL, max_requests_per_connection + 1)
        self.assertEqual(cluster.get_max_requests_per_connection(HostDistance.LOCAL), max_requests_per_connection + 1)

        core_connections_per_host = cluster.get_core_connections_per_host(HostDistance.LOCAL)
        self.assertEqual(cassandra.cluster.DEFAULT_MIN_CONNECTIONS_PER_LOCAL_HOST, core_connections_per_host)
        cluster.set_core_connections_per_host(HostDistance.LOCAL, core_connections_per_host + 1)
        self.assertEqual(cluster.get_core_connections_per_host(HostDistance.LOCAL), core_connections_per_host + 1)

        max_connections_per_host = cluster.get_max_connections_per_host(HostDistance.LOCAL)
        self.assertEqual(cassandra.cluster.DEFAULT_MAX_CONNECTIONS_PER_LOCAL_HOST, max_connections_per_host)
        cluster.set_max_connections_per_host(HostDistance.LOCAL, max_connections_per_host + 1)
        self.assertEqual(cluster.get_max_connections_per_host(HostDistance.LOCAL), max_connections_per_host + 1)

    def test_submit_schema_refresh(self):
        """
        Ensure new new schema is refreshed after submit_schema_refresh()
        """

        cluster = Cluster(protocol_version=PROTOCOL_VERSION)
        cluster.connect()
        self.assertNotIn("newkeyspace", cluster.metadata.keyspaces)

        other_cluster = Cluster(protocol_version=PROTOCOL_VERSION)
        session = other_cluster.connect()
        session.execute(
            """
            CREATE KEYSPACE newkeyspace
            WITH replication = {'class': 'SimpleStrategy', 'replication_factor': '1'}
            """)

        future = cluster.submit_schema_refresh()
        future.result()

        self.assertIn("newkeyspace", cluster.metadata.keyspaces)

    def test_trace(self):
        """
        Ensure trace can be requested for async and non-async queries
        """

        cluster = Cluster(protocol_version=PROTOCOL_VERSION)
        session = cluster.connect()

        self.assertRaises(TypeError, session.execute, "SELECT * FROM system.local", trace=True)

        def check_trace(trace):
            self.assertIsNot(None, trace.request_type)
            self.assertIsNot(None, trace.duration)
            self.assertIsNot(None, trace.started_at)
            self.assertIsNot(None, trace.coordinator)
            self.assertIsNot(None, trace.events)

        query = "SELECT * FROM system.local"
        statement = SimpleStatement(query)
        session.execute(statement, trace=True)
        check_trace(statement.trace)

        query = "SELECT * FROM system.local"
        statement = SimpleStatement(query)
        session.execute(statement)
        self.assertEqual(None, statement.trace)

        statement2 = SimpleStatement(query)
        future = session.execute_async(statement2, trace=True)
        future.result()
        check_trace(future.get_query_trace())

        statement2 = SimpleStatement(query)
        future = session.execute_async(statement2)
        future.result()
        self.assertEqual(None, future.get_query_trace())

        prepared = session.prepare("SELECT * FROM system.local")
        future = session.execute_async(prepared, parameters=(), trace=True)
        future.result()
        check_trace(future.get_query_trace())

    def test_trace_timeout(self):
        cluster = Cluster(protocol_version=PROTOCOL_VERSION)
        session = cluster.connect()

        query = "SELECT * FROM system.local"
        statement = SimpleStatement(query)
        future = session.execute_async(statement, trace=True)
        future.result()
        self.assertRaises(TraceUnavailable, future.get_query_trace, -1.0)

    def test_string_coverage(self):
        """
        Ensure str(future) returns without error
        """

        cluster = Cluster(protocol_version=PROTOCOL_VERSION)
        session = cluster.connect()

        query = "SELECT * FROM system.local"
        statement = SimpleStatement(query)
        future = session.execute_async(statement)

        self.assertIn(query, str(future))
        future.result()

        self.assertIn(query, str(future))
        self.assertIn('result', str(future))

########NEW FILE########
__FILENAME__ = test_concurrent
# Copyright 2013-2014 DataStax, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from tests.integration import PROTOCOL_VERSION

try:
    import unittest2 as unittest
except ImportError:
    import unittest # noqa

from itertools import cycle

from cassandra import InvalidRequest, ConsistencyLevel
from cassandra.cluster import Cluster
from cassandra.concurrent import (execute_concurrent,
                                  execute_concurrent_with_args)
from cassandra.policies import HostDistance
from cassandra.query import tuple_factory, SimpleStatement


class ClusterTests(unittest.TestCase):

    def setUp(self):
        self.cluster = Cluster(protocol_version=PROTOCOL_VERSION)
        self.cluster.set_core_connections_per_host(HostDistance.LOCAL, 1)
        self.session = self.cluster.connect()
        self.session.row_factory = tuple_factory

    def test_execute_concurrent(self):
        for num_statements in (0, 1, 2, 7, 10, 99, 100, 101, 199, 200, 201):
            # write
            statement = SimpleStatement(
                "INSERT INTO test3rf.test (k, v) VALUES (%s, %s)",
                consistency_level=ConsistencyLevel.QUORUM)
            statements = cycle((statement, ))
            parameters = [(i, i) for i in range(num_statements)]

            results = execute_concurrent(self.session, list(zip(statements, parameters)))
            self.assertEqual(num_statements, len(results))
            self.assertEqual([(True, None)] * num_statements, results)

            # read
            statement = SimpleStatement(
                "SELECT v FROM test3rf.test WHERE k=%s",
                consistency_level=ConsistencyLevel.QUORUM)
            statements = cycle((statement, ))
            parameters = [(i, ) for i in range(num_statements)]

            results = execute_concurrent(self.session, list(zip(statements, parameters)))
            self.assertEqual(num_statements, len(results))
            self.assertEqual([(True, [(i,)]) for i in range(num_statements)], results)

    def test_execute_concurrent_with_args(self):
        for num_statements in (0, 1, 2, 7, 10, 99, 100, 101, 199, 200, 201):
            statement = SimpleStatement(
                "INSERT INTO test3rf.test (k, v) VALUES (%s, %s)",
                consistency_level=ConsistencyLevel.QUORUM)
            parameters = [(i, i) for i in range(num_statements)]

            results = execute_concurrent_with_args(self.session, statement, parameters)
            self.assertEqual(num_statements, len(results))
            self.assertEqual([(True, None)] * num_statements, results)

            # read
            statement = SimpleStatement(
                "SELECT v FROM test3rf.test WHERE k=%s",
                consistency_level=ConsistencyLevel.QUORUM)
            parameters = [(i, ) for i in range(num_statements)]

            results = execute_concurrent_with_args(self.session, statement, parameters)
            self.assertEqual(num_statements, len(results))
            self.assertEqual([(True, [(i,)]) for i in range(num_statements)], results)

    def test_first_failure(self):
        statements = cycle(("INSERT INTO test3rf.test (k, v) VALUES (%s, %s)", ))
        parameters = [(i, i) for i in range(100)]

        # we'll get an error back from the server
        parameters[57] = ('efefef', 'awefawefawef')

        self.assertRaises(
            InvalidRequest,
            execute_concurrent, self.session, list(zip(statements, parameters)), raise_on_first_error=True)

    def test_first_failure_client_side(self):
        statement = SimpleStatement(
            "INSERT INTO test3rf.test (k, v) VALUES (%s, %s)",
            consistency_level=ConsistencyLevel.QUORUM)
        statements = cycle((statement, ))
        parameters = [(i, i) for i in range(100)]

        # the driver will raise an error when binding the params
        parameters[57] = 1

        self.assertRaises(
            TypeError,
            execute_concurrent, self.session, list(zip(statements, parameters)), raise_on_first_error=True)

    def test_no_raise_on_first_failure(self):
        statement = SimpleStatement(
            "INSERT INTO test3rf.test (k, v) VALUES (%s, %s)",
            consistency_level=ConsistencyLevel.QUORUM)
        statements = cycle((statement, ))
        parameters = [(i, i) for i in range(100)]

        # we'll get an error back from the server
        parameters[57] = ('efefef', 'awefawefawef')

        results = execute_concurrent(self.session, list(zip(statements, parameters)), raise_on_first_error=False)
        for i, (success, result) in enumerate(results):
            if i == 57:
                self.assertFalse(success)
                self.assertIsInstance(result, InvalidRequest)
            else:
                self.assertTrue(success)
                self.assertEqual(None, result)

    def test_no_raise_on_first_failure_client_side(self):
        statement = SimpleStatement(
            "INSERT INTO test3rf.test (k, v) VALUES (%s, %s)",
            consistency_level=ConsistencyLevel.QUORUM)
        statements = cycle((statement, ))
        parameters = [(i, i) for i in range(100)]

        # the driver will raise an error when binding the params
        parameters[57] = 1

        results = execute_concurrent(self.session, list(zip(statements, parameters)), raise_on_first_error=False)
        for i, (success, result) in enumerate(results):
            if i == 57:
                self.assertFalse(success)
                self.assertIsInstance(result, TypeError)
            else:
                self.assertTrue(success)
                self.assertEqual(None, result)

########NEW FILE########
__FILENAME__ = test_connection
# Copyright 2013-2014 DataStax, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from tests.integration import PROTOCOL_VERSION

try:
    import unittest2 as unittest
except ImportError:
    import unittest # noqa

from functools import partial
from six.moves import range
import sys
from threading import Thread, Event

from cassandra import ConsistencyLevel, OperationTimedOut
from cassandra.cluster import NoHostAvailable
from cassandra.protocol import QueryMessage
from cassandra.io.asyncorereactor import AsyncoreConnection

try:
    from cassandra.io.libevreactor import LibevConnection
except ImportError:
    LibevConnection = None


class ConnectionTest(object):

    klass = None

    def get_connection(self):
        """
        Helper method to solve automated testing issues within Jenkins.
        Officially patched under the 2.0 branch through
        17998ef72a2fe2e67d27dd602b6ced33a58ad8ef, but left as is for the
        1.0 branch due to possible regressions for fixing an
        automated testing edge-case.
        """
        conn = None
        e = None
        for i in range(5):
            try:
                conn = self.klass.factory(protocol_version=PROTOCOL_VERSION)
                break
            except (OperationTimedOut, NoHostAvailable) as e:
                continue

        if conn:
            return conn
        else:
            raise e

    def test_single_connection(self):
        """
        Test a single connection with sequential requests.
        """
        conn = self.get_connection()
        query = "SELECT keyspace_name FROM system.schema_keyspaces LIMIT 1"
        event = Event()

        def cb(count, *args, **kwargs):
            count += 1
            if count >= 10:
                conn.close()
                event.set()
            else:
                conn.send_msg(
                    QueryMessage(query=query, consistency_level=ConsistencyLevel.ONE),
                    cb=partial(cb, count))

        conn.send_msg(
            QueryMessage(query=query, consistency_level=ConsistencyLevel.ONE),
            cb=partial(cb, 0))
        event.wait()

    def test_single_connection_pipelined_requests(self):
        """
        Test a single connection with pipelined requests.
        """
        conn = self.get_connection()
        query = "SELECT keyspace_name FROM system.schema_keyspaces LIMIT 1"
        responses = [False] * 100
        event = Event()

        def cb(response_list, request_num, *args, **kwargs):
            response_list[request_num] = True
            if all(response_list):
                conn.close()
                event.set()

        for i in range(100):
            conn.send_msg(
                QueryMessage(query=query, consistency_level=ConsistencyLevel.ONE),
                cb=partial(cb, responses, i))

        event.wait()

    def test_multiple_connections(self):
        """
        Test multiple connections with pipelined requests.
        """
        conns = [self.get_connection() for i in range(5)]
        events = [Event() for i in range(5)]
        query = "SELECT keyspace_name FROM system.schema_keyspaces LIMIT 1"

        def cb(event, conn, count, *args, **kwargs):
            count += 1
            if count >= 10:
                conn.close()
                event.set()
            else:
                conn.send_msg(
                    QueryMessage(query=query, consistency_level=ConsistencyLevel.ONE),
                    cb=partial(cb, event, conn, count))

        for event, conn in zip(events, conns):
            conn.send_msg(
                QueryMessage(query=query, consistency_level=ConsistencyLevel.ONE),
                cb=partial(cb, event, conn, 0))

        for event in events:
            event.wait()

    def test_multiple_threads_shared_connection(self):
        """
        Test sharing a single connections across multiple threads,
        which will result in pipelined requests.
        """
        num_requests_per_conn = 25
        num_threads = 5
        event = Event()

        conn = self.get_connection()
        query = "SELECT keyspace_name FROM system.schema_keyspaces LIMIT 1"

        def cb(all_responses, thread_responses, request_num, *args, **kwargs):
            thread_responses[request_num] = True
            if all(map(all, all_responses)):
                conn.close()
                event.set()

        def send_msgs(all_responses, thread_responses):
            for i in range(num_requests_per_conn):
                qmsg = QueryMessage(query=query, consistency_level=ConsistencyLevel.ONE)
                conn.send_msg(qmsg, cb=partial(cb, all_responses, thread_responses, i))

        all_responses = []
        threads = []
        for i in range(num_threads):
            thread_responses = [False] * num_requests_per_conn
            all_responses.append(thread_responses)
            t = Thread(target=send_msgs, args=(all_responses, thread_responses))
            threads.append(t)

        for t in threads:
            t.start()

        for t in threads:
            t.join()

        event.wait()

    def test_multiple_threads_multiple_connections(self):
        """
        Test several threads, each with their own Connection and pipelined
        requests.
        """
        num_requests_per_conn = 25
        num_conns = 5
        events = [Event() for i in range(5)]

        query = "SELECT keyspace_name FROM system.schema_keyspaces LIMIT 1"

        def cb(conn, event, thread_responses, request_num, *args, **kwargs):
            thread_responses[request_num] = True
            if all(thread_responses):
                conn.close()
                event.set()

        def send_msgs(conn, event):
            thread_responses = [False] * num_requests_per_conn
            for i in range(num_requests_per_conn):
                qmsg = QueryMessage(query=query, consistency_level=ConsistencyLevel.ONE)
                conn.send_msg(qmsg, cb=partial(cb, conn, event, thread_responses, i))

            event.wait()

        threads = []
        for i in range(num_conns):
            conn = self.get_connection()
            t = Thread(target=send_msgs, args=(conn, events[i]))
            threads.append(t)

        for t in threads:
            t.start()

        for t in threads:
            t.join()


class AsyncoreConnectionTest(ConnectionTest, unittest.TestCase):

    klass = AsyncoreConnection

    def setUp(self):
        if 'gevent.monkey' in sys.modules:
            raise unittest.SkipTest("Can't test libev with gevent monkey patching")


class LibevConnectionTest(ConnectionTest, unittest.TestCase):

    klass = LibevConnection

    def setUp(self):
        if 'gevent.monkey' in sys.modules:
            raise unittest.SkipTest("Can't test libev with gevent monkey patching")
        if LibevConnection is None:
            raise unittest.SkipTest(
                'libev does not appear to be installed properly')

########NEW FILE########
__FILENAME__ = test_factories
# Copyright 2013-2014 DataStax, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from tests.integration import PROTOCOL_VERSION

try:
    import unittest2 as unittest
except ImportError:
    import unittest # noqa

from cassandra.cluster import Cluster
from cassandra.query import tuple_factory, named_tuple_factory, dict_factory, ordered_dict_factory
from cassandra.util import OrderedDict


class TestFactories(unittest.TestCase):
    """
    Test different row_factories and access code
    """

    truncate = '''
        TRUNCATE test3rf.test
    '''

    insert1 = '''
        INSERT INTO test3rf.test
            ( k , v )
        VALUES
            ( 1 , 1 )
    '''

    insert2 = '''
        INSERT INTO test3rf.test
            ( k , v )
        VALUES
            ( 2 , 2 )
    '''

    select = '''
        SELECT * FROM test3rf.test
    '''

    def test_tuple_factory(self):
        cluster = Cluster(protocol_version=PROTOCOL_VERSION)
        session = cluster.connect()
        session.row_factory = tuple_factory

        session.execute(self.truncate)
        session.execute(self.insert1)
        session.execute(self.insert2)

        result = session.execute(self.select)

        self.assertIsInstance(result, list)
        self.assertIsInstance(result[0], tuple)

        for row in result:
            self.assertEqual(row[0], row[1])

        self.assertEqual(result[0][0], result[0][1])
        self.assertEqual(result[0][0], 1)
        self.assertEqual(result[1][0], result[1][1])
        self.assertEqual(result[1][0], 2)

    def test_named_tuple_factoryy(self):
        cluster = Cluster(protocol_version=PROTOCOL_VERSION)
        session = cluster.connect()
        session.row_factory = named_tuple_factory

        session.execute(self.truncate)
        session.execute(self.insert1)
        session.execute(self.insert2)

        result = session.execute(self.select)

        self.assertIsInstance(result, list)

        for row in result:
            self.assertEqual(row.k, row.v)

        self.assertEqual(result[0].k, result[0].v)
        self.assertEqual(result[0].k, 1)
        self.assertEqual(result[1].k, result[1].v)
        self.assertEqual(result[1].k, 2)

    def test_dict_factory(self):
        cluster = Cluster(protocol_version=PROTOCOL_VERSION)
        session = cluster.connect()
        session.row_factory = dict_factory

        session.execute(self.truncate)
        session.execute(self.insert1)
        session.execute(self.insert2)

        result = session.execute(self.select)

        self.assertIsInstance(result, list)
        self.assertIsInstance(result[0], dict)

        for row in result:
            self.assertEqual(row['k'], row['v'])

        self.assertEqual(result[0]['k'], result[0]['v'])
        self.assertEqual(result[0]['k'], 1)
        self.assertEqual(result[1]['k'], result[1]['v'])
        self.assertEqual(result[1]['k'], 2)

    def test_ordered_dict_factory(self):
        cluster = Cluster(protocol_version=PROTOCOL_VERSION)
        session = cluster.connect()
        session.row_factory = ordered_dict_factory

        session.execute(self.truncate)
        session.execute(self.insert1)
        session.execute(self.insert2)

        result = session.execute(self.select)

        self.assertIsInstance(result, list)
        self.assertIsInstance(result[0], OrderedDict)

        for row in result:
            self.assertEqual(row['k'], row['v'])

        self.assertEqual(result[0]['k'], result[0]['v'])
        self.assertEqual(result[0]['k'], 1)
        self.assertEqual(result[1]['k'], result[1]['v'])
        self.assertEqual(result[1]['k'], 2)

########NEW FILE########
__FILENAME__ = test_metadata
# Copyright 2013-2014 DataStax, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import six

try:
    import unittest2 as unittest
except ImportError:
    import unittest # noqa

from mock import Mock

from cassandra import AlreadyExists

from cassandra.cluster import Cluster
from cassandra.metadata import (Metadata, KeyspaceMetadata, TableMetadata,
                                Token, MD5Token, TokenMap, murmur3)
from cassandra.policies import SimpleConvictionPolicy
from cassandra.pool import Host

from tests.integration import get_cluster, PROTOCOL_VERSION


class SchemaMetadataTest(unittest.TestCase):

    ksname = "schemametadatatest"

    @property
    def cfname(self):
        return self._testMethodName.lower()

    @classmethod
    def setup_class(cls):
        cluster = Cluster(protocol_version=PROTOCOL_VERSION)
        session = cluster.connect()
        try:
            results = session.execute("SELECT keyspace_name FROM system.schema_keyspaces")
            existing_keyspaces = [row[0] for row in results]
            if cls.ksname in existing_keyspaces:
                session.execute("DROP KEYSPACE %s" % cls.ksname)

            session.execute(
                """
                CREATE KEYSPACE %s
                WITH replication = {'class': 'SimpleStrategy', 'replication_factor': '1'};
                """ % cls.ksname)
        finally:
            cluster.shutdown()

    @classmethod
    def teardown_class(cls):
        cluster = Cluster(['127.0.0.1'],
                          protocol_version=PROTOCOL_VERSION)
        session = cluster.connect()
        try:
            session.execute("DROP KEYSPACE %s" % cls.ksname)
        finally:
            cluster.shutdown()

    def setUp(self):
        self.cluster = Cluster(['127.0.0.1'],
                               protocol_version=PROTOCOL_VERSION)
        self.session = self.cluster.connect()

    def tearDown(self):
        try:
            self.session.execute(
                """
                DROP TABLE {ksname}.{cfname}
                """.format(ksname=self.ksname, cfname=self.cfname))
        finally:
            self.cluster.shutdown()

    def make_create_statement(self, partition_cols, clustering_cols=None, other_cols=None, compact=False):
        clustering_cols = clustering_cols or []
        other_cols = other_cols or []

        statement = "CREATE TABLE %s.%s (" % (self.ksname, self.cfname)
        if len(partition_cols) == 1 and not clustering_cols:
            statement += "%s text PRIMARY KEY, " % partition_cols[0]
        else:
            statement += ", ".join("%s text" % col for col in partition_cols)
            statement += ", "

        statement += ", ".join("%s text" % col for col in clustering_cols + other_cols)

        if len(partition_cols) != 1 or clustering_cols:
            statement += ", PRIMARY KEY ("

            if len(partition_cols) > 1:
                statement += "(" + ", ".join(partition_cols) + ")"
            else:
                statement += partition_cols[0]

            if clustering_cols:
                statement += ", "
                statement += ", ".join(clustering_cols)

            statement += ")"

        statement += ")"
        if compact:
            statement += " WITH COMPACT STORAGE"

        return statement

    def check_create_statement(self, tablemeta, original):
        recreate = tablemeta.as_cql_query(formatted=False)
        self.assertEqual(original, recreate[:len(original)])
        self.session.execute("DROP TABLE %s.%s" % (self.ksname, self.cfname))
        self.session.execute(recreate)

        # create the table again, but with formatting enabled
        self.session.execute("DROP TABLE %s.%s" % (self.ksname, self.cfname))
        recreate = tablemeta.as_cql_query(formatted=True)
        self.session.execute(recreate)

    def get_table_metadata(self):
        self.cluster.control_connection.refresh_schema()
        return self.cluster.metadata.keyspaces[self.ksname].tables[self.cfname]

    def test_basic_table_meta_properties(self):
        create_statement = self.make_create_statement(["a"], [], ["b", "c"])
        self.session.execute(create_statement)

        self.cluster.control_connection.refresh_schema()

        meta = self.cluster.metadata
        self.assertNotEqual(meta.cluster_ref, None)
        self.assertNotEqual(meta.cluster_name, None)
        self.assertTrue(self.ksname in meta.keyspaces)
        ksmeta = meta.keyspaces[self.ksname]

        self.assertEqual(ksmeta.name, self.ksname)
        self.assertTrue(ksmeta.durable_writes)
        self.assertEqual(ksmeta.replication_strategy.name, 'SimpleStrategy')
        self.assertEqual(ksmeta.replication_strategy.replication_factor, 1)

        self.assertTrue(self.cfname in ksmeta.tables)
        tablemeta = ksmeta.tables[self.cfname]
        self.assertEqual(tablemeta.keyspace, ksmeta)
        self.assertEqual(tablemeta.name, self.cfname)

        self.assertEqual([u'a'], [c.name for c in tablemeta.partition_key])
        self.assertEqual([], tablemeta.clustering_key)
        self.assertEqual([u'a', u'b', u'c'], sorted(tablemeta.columns.keys()))

        for option in tablemeta.options:
            self.assertIn(option, TableMetadata.recognized_options)

        self.check_create_statement(tablemeta, create_statement)

    def test_compound_primary_keys(self):
        create_statement = self.make_create_statement(["a"], ["b"], ["c"])
        create_statement += " WITH CLUSTERING ORDER BY (b ASC)"
        self.session.execute(create_statement)
        tablemeta = self.get_table_metadata()

        self.assertEqual([u'a'], [c.name for c in tablemeta.partition_key])
        self.assertEqual([u'b'], [c.name for c in tablemeta.clustering_key])
        self.assertEqual([u'a', u'b', u'c'], sorted(tablemeta.columns.keys()))

        self.check_create_statement(tablemeta, create_statement)

    def test_compound_primary_keys_more_columns(self):
        create_statement = self.make_create_statement(["a"], ["b", "c"], ["d", "e", "f"])
        create_statement += " WITH CLUSTERING ORDER BY (b ASC, c ASC)"
        self.session.execute(create_statement)
        tablemeta = self.get_table_metadata()

        self.assertEqual([u'a'], [c.name for c in tablemeta.partition_key])
        self.assertEqual([u'b', u'c'], [c.name for c in tablemeta.clustering_key])
        self.assertEqual(
            [u'a', u'b', u'c', u'd', u'e', u'f'],
            sorted(tablemeta.columns.keys()))

        self.check_create_statement(tablemeta, create_statement)

    def test_composite_primary_key(self):
        create_statement = self.make_create_statement(["a", "b"], [], ["c"])
        self.session.execute(create_statement)
        tablemeta = self.get_table_metadata()

        self.assertEqual([u'a', u'b'], [c.name for c in tablemeta.partition_key])
        self.assertEqual([], tablemeta.clustering_key)
        self.assertEqual([u'a', u'b', u'c'], sorted(tablemeta.columns.keys()))

        self.check_create_statement(tablemeta, create_statement)

    def test_composite_in_compound_primary_key(self):
        create_statement = self.make_create_statement(["a", "b"], ["c"], ["d", "e"])
        create_statement += " WITH CLUSTERING ORDER BY (c ASC)"
        self.session.execute(create_statement)
        tablemeta = self.get_table_metadata()

        self.assertEqual([u'a', u'b'], [c.name for c in tablemeta.partition_key])
        self.assertEqual([u'c'], [c.name for c in tablemeta.clustering_key])
        self.assertEqual([u'a', u'b', u'c', u'd', u'e'], sorted(tablemeta.columns.keys()))

        self.check_create_statement(tablemeta, create_statement)

    def test_compound_primary_keys_compact(self):
        create_statement = self.make_create_statement(["a"], ["b"], ["c"], compact=True)
        create_statement += " AND CLUSTERING ORDER BY (b ASC)"
        self.session.execute(create_statement)
        tablemeta = self.get_table_metadata()

        self.assertEqual([u'a'], [c.name for c in tablemeta.partition_key])
        self.assertEqual([u'b'], [c.name for c in tablemeta.clustering_key])
        self.assertEqual([u'a', u'b', u'c'], sorted(tablemeta.columns.keys()))

        self.check_create_statement(tablemeta, create_statement)

    def test_compound_primary_keys_more_columns_compact(self):
        create_statement = self.make_create_statement(["a"], ["b", "c"], ["d"], compact=True)
        create_statement += " AND CLUSTERING ORDER BY (b ASC, c ASC)"
        self.session.execute(create_statement)
        tablemeta = self.get_table_metadata()

        self.assertEqual([u'a'], [c.name for c in tablemeta.partition_key])
        self.assertEqual([u'b', u'c'], [c.name for c in tablemeta.clustering_key])
        self.assertEqual([u'a', u'b', u'c', u'd'], sorted(tablemeta.columns.keys()))

        self.check_create_statement(tablemeta, create_statement)

    def test_composite_primary_key_compact(self):
        create_statement = self.make_create_statement(["a", "b"], [], ["c"], compact=True)
        self.session.execute(create_statement)
        tablemeta = self.get_table_metadata()

        self.assertEqual([u'a', u'b'], [c.name for c in tablemeta.partition_key])
        self.assertEqual([], tablemeta.clustering_key)
        self.assertEqual([u'a', u'b', u'c'], sorted(tablemeta.columns.keys()))

        self.check_create_statement(tablemeta, create_statement)

    def test_composite_in_compound_primary_key_compact(self):
        create_statement = self.make_create_statement(["a", "b"], ["c"], ["d"], compact=True)
        create_statement += " AND CLUSTERING ORDER BY (c ASC)"
        self.session.execute(create_statement)
        tablemeta = self.get_table_metadata()

        self.assertEqual([u'a', u'b'], [c.name for c in tablemeta.partition_key])
        self.assertEqual([u'c'], [c.name for c in tablemeta.clustering_key])
        self.assertEqual([u'a', u'b', u'c', u'd'], sorted(tablemeta.columns.keys()))

        self.check_create_statement(tablemeta, create_statement)

    def test_compound_primary_keys_ordering(self):
        create_statement = self.make_create_statement(["a"], ["b"], ["c"])
        create_statement += " WITH CLUSTERING ORDER BY (b DESC)"
        self.session.execute(create_statement)
        tablemeta = self.get_table_metadata()
        self.check_create_statement(tablemeta, create_statement)

    def test_compound_primary_keys_more_columns_ordering(self):
        create_statement = self.make_create_statement(["a"], ["b", "c"], ["d", "e", "f"])
        create_statement += " WITH CLUSTERING ORDER BY (b DESC, c ASC)"
        self.session.execute(create_statement)
        tablemeta = self.get_table_metadata()
        self.check_create_statement(tablemeta, create_statement)

    def test_composite_in_compound_primary_key_ordering(self):
        create_statement = self.make_create_statement(["a", "b"], ["c"], ["d", "e"])
        create_statement += " WITH CLUSTERING ORDER BY (c DESC)"
        self.session.execute(create_statement)
        tablemeta = self.get_table_metadata()
        self.check_create_statement(tablemeta, create_statement)

    def test_indexes(self):
        create_statement = self.make_create_statement(["a"], ["b", "c"], ["d", "e", "f"])
        create_statement += " WITH CLUSTERING ORDER BY (b ASC, c ASC)"
        self.session.execute(create_statement)

        d_index = "CREATE INDEX d_index ON %s.%s (d)" % (self.ksname, self.cfname)
        e_index = "CREATE INDEX e_index ON %s.%s (e)" % (self.ksname, self.cfname)
        self.session.execute(d_index)
        self.session.execute(e_index)

        tablemeta = self.get_table_metadata()
        statements = tablemeta.export_as_string().strip()
        statements = [s.strip() for s in statements.split(';')]
        statements = list(filter(bool, statements))
        self.assertEqual(3, len(statements))
        self.assertEqual(d_index, statements[1])
        self.assertEqual(e_index, statements[2])

        # make sure indexes are included in KeyspaceMetadata.export_as_string()
        ksmeta = self.cluster.metadata.keyspaces[self.ksname]
        statement = ksmeta.export_as_string()
        self.assertIn('CREATE INDEX d_index', statement)
        self.assertIn('CREATE INDEX e_index', statement)


class TestCodeCoverage(unittest.TestCase):

    def test_export_schema(self):
        """
        Test export schema functionality
        """

        cluster = Cluster(protocol_version=PROTOCOL_VERSION)
        cluster.connect()

        self.assertIsInstance(cluster.metadata.export_schema_as_string(), six.string_types)

    def test_export_keyspace_schema(self):
        """
        Test export keyspace schema functionality
        """

        cluster = Cluster(protocol_version=PROTOCOL_VERSION)
        cluster.connect()

        for keyspace in cluster.metadata.keyspaces:
            keyspace_metadata = cluster.metadata.keyspaces[keyspace]
            self.assertIsInstance(keyspace_metadata.export_as_string(), six.string_types)
            self.assertIsInstance(keyspace_metadata.as_cql_query(), six.string_types)

    def test_case_sensitivity(self):
        """
        Test that names that need to be escaped in CREATE statements are
        """

        cluster = Cluster(protocol_version=PROTOCOL_VERSION)
        session = cluster.connect()

        ksname = 'AnInterestingKeyspace'
        cfname = 'AnInterestingTable'

        session.execute("""
            CREATE KEYSPACE "%s"
            WITH replication = {'class': 'SimpleStrategy', 'replication_factor': '1'}
            """ % (ksname,))
        session.execute("""
            CREATE TABLE "%s"."%s" (
                k int,
                "A" int,
                "B" int,
                "MyColumn" int,
                PRIMARY KEY (k, "A"))
            WITH CLUSTERING ORDER BY ("A" DESC)
            """ % (ksname, cfname))
        session.execute("""
            CREATE INDEX myindex ON "%s"."%s" ("MyColumn")
            """ % (ksname, cfname))

        ksmeta = cluster.metadata.keyspaces[ksname]
        schema = ksmeta.export_as_string()
        self.assertIn('CREATE KEYSPACE "AnInterestingKeyspace"', schema)
        self.assertIn('CREATE TABLE "AnInterestingKeyspace"."AnInterestingTable"', schema)
        self.assertIn('"A" int', schema)
        self.assertIn('"B" int', schema)
        self.assertIn('"MyColumn" int', schema)
        self.assertIn('PRIMARY KEY (k, "A")', schema)
        self.assertIn('WITH CLUSTERING ORDER BY ("A" DESC)', schema)
        self.assertIn('CREATE INDEX myindex ON "AnInterestingKeyspace"."AnInterestingTable" ("MyColumn")', schema)

    def test_already_exists_exceptions(self):
        """
        Ensure AlreadyExists exception is thrown when hit
        """

        cluster = Cluster(protocol_version=PROTOCOL_VERSION)
        session = cluster.connect()

        ksname = 'test3rf'
        cfname = 'test'

        ddl = '''
            CREATE KEYSPACE %s
            WITH replication = {'class': 'SimpleStrategy', 'replication_factor': '3'}'''
        self.assertRaises(AlreadyExists, session.execute, ddl % ksname)

        ddl = '''
            CREATE TABLE %s.%s (
                k int PRIMARY KEY,
                v int )'''
        self.assertRaises(AlreadyExists, session.execute, ddl % (ksname, cfname))

    def test_replicas(self):
        """
        Ensure cluster.metadata.get_replicas return correctly when not attached to keyspace
        """
        if murmur3 is None:
            raise unittest.SkipTest('the murmur3 extension is not available')

        cluster = Cluster(protocol_version=PROTOCOL_VERSION)
        self.assertEqual(cluster.metadata.get_replicas('test3rf', 'key'), [])

        cluster.connect('test3rf')

        self.assertNotEqual(list(cluster.metadata.get_replicas('test3rf', 'key')), [])
        host = list(cluster.metadata.get_replicas('test3rf', 'key'))[0]
        self.assertEqual(host.datacenter, 'datacenter1')
        self.assertEqual(host.rack, 'rack1')

    def test_token_map(self):
        """
        Test token mappings
        """

        cluster = Cluster(protocol_version=PROTOCOL_VERSION)
        cluster.connect('test3rf')
        ring = cluster.metadata.token_map.ring
        owners = list(cluster.metadata.token_map.token_to_host_owner[token] for token in ring)
        get_replicas = cluster.metadata.token_map.get_replicas

        for ksname in ('test1rf', 'test2rf', 'test3rf'):
            self.assertNotEqual(list(get_replicas(ksname, ring[0])), [])

        for i, token in enumerate(ring):
            self.assertEqual(set(get_replicas('test3rf', token)), set(owners))
            self.assertEqual(set(get_replicas('test2rf', token)), set([owners[(i + 1) % 3], owners[(i + 2) % 3]]))
            self.assertEqual(set(get_replicas('test1rf', token)), set([owners[(i + 1) % 3]]))


class TokenMetadataTest(unittest.TestCase):
    """
    Test of TokenMap creation and other behavior.
    """

    def test_token(self):
        expected_node_count = len(get_cluster().nodes)

        cluster = Cluster(protocol_version=PROTOCOL_VERSION)
        cluster.connect()
        tmap = cluster.metadata.token_map
        self.assertTrue(issubclass(tmap.token_class, Token))
        self.assertEqual(expected_node_count, len(tmap.ring))
        cluster.shutdown()

    def test_getting_replicas(self):
        tokens = [MD5Token(str(i)) for i in range(0, (2 ** 127 - 1), 2 ** 125)]
        hosts = [Host("ip%d" % i, SimpleConvictionPolicy) for i in range(len(tokens))]
        token_to_primary_replica = dict(zip(tokens, hosts))
        keyspace = KeyspaceMetadata("ks", True, "SimpleStrategy", {"replication_factor": "1"})
        metadata = Mock(spec=Metadata, keyspaces={'ks': keyspace})
        token_map = TokenMap(MD5Token, token_to_primary_replica, tokens, metadata)

        # tokens match node tokens exactly
        for i, token in enumerate(tokens):
            expected_host = hosts[(i + 1) % len(hosts)]
            replicas = token_map.get_replicas("ks", token)
            self.assertEqual(set(replicas), set([expected_host]))

        # shift the tokens back by one
        for token, expected_host in zip(tokens, hosts):
            replicas = token_map.get_replicas("ks", MD5Token(str(token.value - 1)))
            self.assertEqual(set(replicas), set([expected_host]))

        # shift the tokens forward by one
        for i, token in enumerate(tokens):
            replicas = token_map.get_replicas("ks", MD5Token(str(token.value + 1)))
            expected_host = hosts[(i + 1) % len(hosts)]
            self.assertEqual(set(replicas), set([expected_host]))

########NEW FILE########
__FILENAME__ = test_metrics
# Copyright 2013-2014 DataStax, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import time

try:
    import unittest2 as unittest
except ImportError:
    import unittest # noqa

from cassandra.query import SimpleStatement
from cassandra import ConsistencyLevel, WriteTimeout, Unavailable, ReadTimeout

from cassandra.cluster import Cluster, NoHostAvailable
from tests.integration import get_node, get_cluster, PROTOCOL_VERSION


class MetricsTests(unittest.TestCase):

    def test_connection_error(self):
        """
        Trigger and ensure connection_errors are counted
        """

        cluster = Cluster(metrics_enabled=True,
                          protocol_version=PROTOCOL_VERSION)
        session = cluster.connect()
        session.execute("USE test3rf")

        # Test writes
        for i in range(0, 100):
            session.execute_async(
                """
                INSERT INTO test3rf.test (k, v) VALUES (%s, %s)
                """ % (i, i))

        # Force kill cluster
        get_cluster().stop(wait=True, gently=False)
        try:
            # Ensure the nodes are actually down
            self.assertRaises(NoHostAvailable, session.execute, "USE test3rf")
        finally:
            get_cluster().start(wait_for_binary_proto=True)

        self.assertGreater(cluster.metrics.stats.connection_errors, 0)

    def test_write_timeout(self):
        """
        Trigger and ensure write_timeouts are counted
        Write a key, value pair. Force kill a node without waiting for the cluster to register the death.
        Attempt a write at cl.ALL and receive a WriteTimeout.
        """

        cluster = Cluster(metrics_enabled=True,
                          protocol_version=PROTOCOL_VERSION)
        session = cluster.connect()

        # Test write
        session.execute("INSERT INTO test3rf.test (k, v) VALUES (1, 1)")

        # Assert read
        query = SimpleStatement("SELECT v FROM test3rf.test WHERE k=%(k)s", consistency_level=ConsistencyLevel.ALL)
        results = session.execute(query, {'k': 1})
        self.assertEqual(1, results[0].v)

        # Force kill ccm node
        get_node(1).stop(wait=False, gently=False)

        try:
            # Test write
            query = SimpleStatement("INSERT INTO test3rf.test (k, v) VALUES (2, 2)", consistency_level=ConsistencyLevel.ALL)
            self.assertRaises(WriteTimeout, session.execute, query, timeout=None)
            self.assertEqual(1, cluster.metrics.stats.write_timeouts)

        finally:
            get_node(1).start(wait_other_notice=True, wait_for_binary_proto=True)

    def test_read_timeout(self):
        """
        Trigger and ensure read_timeouts are counted
        Write a key, value pair. Force kill a node without waiting for the cluster to register the death.
        Attempt a read at cl.ALL and receive a ReadTimeout.
        """

        cluster = Cluster(metrics_enabled=True,
                          protocol_version=PROTOCOL_VERSION)
        session = cluster.connect()

        # Test write
        session.execute("INSERT INTO test3rf.test (k, v) VALUES (1, 1)")

        # Assert read
        query = SimpleStatement("SELECT v FROM test3rf.test WHERE k=%(k)s", consistency_level=ConsistencyLevel.ALL)
        results = session.execute(query, {'k': 1})
        self.assertEqual(1, results[0].v)

        # Force kill ccm node
        get_node(1).stop(wait=False, gently=False)

        try:
            # Test read
            query = SimpleStatement("SELECT v FROM test3rf.test WHERE k=%(k)s", consistency_level=ConsistencyLevel.ALL)
            self.assertRaises(ReadTimeout, session.execute, query, {'k': 1}, timeout=None)
            self.assertEqual(1, cluster.metrics.stats.read_timeouts)

        finally:
            get_node(1).start(wait_other_notice=True, wait_for_binary_proto=True)

    def test_unavailable(self):
        """
        Trigger and ensure unavailables are counted
        Write a key, value pair. Kill a node while waiting for the cluster to register the death.
        Attempt an insert/read at cl.ALL and receive a Unavailable Exception.
        """

        cluster = Cluster(metrics_enabled=True,
                          protocol_version=PROTOCOL_VERSION)
        session = cluster.connect()

        # Test write
        session.execute("INSERT INTO test3rf.test (k, v) VALUES (1, 1)")

        # Assert read
        query = SimpleStatement("SELECT v FROM test3rf.test WHERE k=%(k)s", consistency_level=ConsistencyLevel.ALL)
        results = session.execute(query, {'k': 1})
        self.assertEqual(1, results[0].v)

        # Force kill ccm node
        get_node(1).stop(wait=True, gently=True)
        time.sleep(5)

        try:
            # Test write
            query = SimpleStatement("INSERT INTO test3rf.test (k, v) VALUES (2, 2)", consistency_level=ConsistencyLevel.ALL)
            self.assertRaises(Unavailable, session.execute, query)
            self.assertEqual(1, cluster.metrics.stats.unavailables)

            # Test write
            query = SimpleStatement("SELECT v FROM test3rf.test WHERE k=%(k)s", consistency_level=ConsistencyLevel.ALL)
            self.assertRaises(Unavailable, session.execute, query, {'k': 1})
            self.assertEqual(2, cluster.metrics.stats.unavailables)
        finally:
            get_node(1).start(wait_other_notice=True, wait_for_binary_proto=True)

    def test_other_error(self):
        # TODO: Bootstrapping or Overloaded cases
        pass

    def test_ignore(self):
        # TODO: Look for ways to generate ignores
        pass

    def test_retry(self):
        # TODO: Look for ways to generate retries
        pass

########NEW FILE########
__FILENAME__ = test_prepared_statements
# Copyright 2013-2014 DataStax, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


from tests.integration import PROTOCOL_VERSION

try:
    import unittest2 as unittest
except ImportError:
    import unittest # noqa
from cassandra import InvalidRequest

from cassandra.cluster import Cluster
from cassandra.query import PreparedStatement


class PreparedStatementTests(unittest.TestCase):

    def test_basic(self):
        """
        Test basic PreparedStatement usage
        """

        cluster = Cluster(protocol_version=PROTOCOL_VERSION)
        session = cluster.connect()
        session.execute(
            """
            CREATE KEYSPACE preparedtests
            WITH replication = {'class': 'SimpleStrategy', 'replication_factor': '1'}
            """)

        session.set_keyspace("preparedtests")
        session.execute(
            """
            CREATE TABLE cf0 (
                a text,
                b text,
                c text,
                PRIMARY KEY (a, b)
            )
            """)

        prepared = session.prepare(
            """
            INSERT INTO cf0 (a, b, c) VALUES  (?, ?, ?)
            """)

        self.assertIsInstance(prepared, PreparedStatement)
        bound = prepared.bind(('a', 'b', 'c'))

        session.execute(bound)

        prepared = session.prepare(
           """
           SELECT * FROM cf0 WHERE a=?
           """)
        self.assertIsInstance(prepared, PreparedStatement)

        bound = prepared.bind(('a'))
        results = session.execute(bound)
        self.assertEqual(results, [('a', 'b', 'c')])

        # test with new dict binding
        prepared = session.prepare(
            """
            INSERT INTO cf0 (a, b, c) VALUES  (?, ?, ?)
            """)

        self.assertIsInstance(prepared, PreparedStatement)
        bound = prepared.bind({
            'a': 'x',
            'b': 'y',
            'c': 'z'
        })

        session.execute(bound)

        prepared = session.prepare(
           """
           SELECT * FROM cf0 WHERE a=?
           """)

        self.assertIsInstance(prepared, PreparedStatement)

        bound = prepared.bind({'a': 'x'})
        results = session.execute(bound)
        self.assertEqual(results, [('x', 'y', 'z')])

    def test_missing_primary_key(self):
        """
        Ensure an InvalidRequest is thrown
        when prepared statements are missing the primary key
        """

        cluster = Cluster(protocol_version=PROTOCOL_VERSION)
        session = cluster.connect()

        prepared = session.prepare(
            """
            INSERT INTO test3rf.test (v) VALUES  (?)
            """)

        self.assertIsInstance(prepared, PreparedStatement)
        bound = prepared.bind((1,))
        self.assertRaises(InvalidRequest, session.execute, bound)

    def test_missing_primary_key_dicts(self):
        """
        Ensure an InvalidRequest is thrown
        when prepared statements are missing the primary key
        with dict bindings
        """

        cluster = Cluster(protocol_version=PROTOCOL_VERSION)
        session = cluster.connect()

        prepared = session.prepare(
            """
            INSERT INTO test3rf.test (v) VALUES  (?)
            """)

        self.assertIsInstance(prepared, PreparedStatement)
        bound = prepared.bind({'v': 1})
        self.assertRaises(InvalidRequest, session.execute, bound)

    def test_too_many_bind_values(self):
        """
        Ensure a ValueError is thrown when attempting to bind too many variables
        """

        cluster = Cluster(protocol_version=PROTOCOL_VERSION)
        session = cluster.connect()

        prepared = session.prepare(
            """
            INSERT INTO test3rf.test (v) VALUES  (?)
            """)

        self.assertIsInstance(prepared, PreparedStatement)
        self.assertRaises(ValueError, prepared.bind, (1, 2))

    def test_too_many_bind_values_dicts(self):
        """
        Ensure a ValueError is thrown when attempting to bind too many variables
        with dict bindings
        """

        cluster = Cluster(protocol_version=PROTOCOL_VERSION)
        session = cluster.connect()

        prepared = session.prepare(
            """
            INSERT INTO test3rf.test (v) VALUES  (?)
            """)

        self.assertIsInstance(prepared, PreparedStatement)
        self.assertRaises(ValueError, prepared.bind, {'k': 1, 'v': 2})

        # also catch too few variables with dicts
        self.assertIsInstance(prepared, PreparedStatement)
        self.assertRaises(KeyError, prepared.bind, {})

    def test_none_values(self):
        """
        Ensure binding None is handled correctly
        """

        cluster = Cluster(protocol_version=PROTOCOL_VERSION)
        session = cluster.connect()

        prepared = session.prepare(
            """
            INSERT INTO test3rf.test (k, v) VALUES  (?, ?)
            """)

        self.assertIsInstance(prepared, PreparedStatement)
        bound = prepared.bind((1, None))
        session.execute(bound)

        prepared = session.prepare(
           """
           SELECT * FROM test3rf.test WHERE k=?
           """)
        self.assertIsInstance(prepared, PreparedStatement)

        bound = prepared.bind((1,))
        results = session.execute(bound)
        self.assertEqual(results[0].v, None)

    def test_none_values_dicts(self):
        """
        Ensure binding None is handled correctly with dict bindings
        """

        cluster = Cluster(protocol_version=PROTOCOL_VERSION)
        session = cluster.connect()

        # test with new dict binding
        prepared = session.prepare(
            """
            INSERT INTO test3rf.test (k, v) VALUES  (?, ?)
            """)

        self.assertIsInstance(prepared, PreparedStatement)
        bound = prepared.bind({'k': 1, 'v': None})
        session.execute(bound)

        prepared = session.prepare(
           """
           SELECT * FROM test3rf.test WHERE k=?
           """)
        self.assertIsInstance(prepared, PreparedStatement)

        bound = prepared.bind({'k': 1})
        results = session.execute(bound)
        self.assertEqual(results[0].v, None)

    def test_async_binding(self):
        """
        Ensure None binding over async queries
        """

        cluster = Cluster(protocol_version=PROTOCOL_VERSION)
        session = cluster.connect()

        prepared = session.prepare(
            """
            INSERT INTO test3rf.test (k, v) VALUES  (?, ?)
            """)

        self.assertIsInstance(prepared, PreparedStatement)
        future = session.execute_async(prepared, (873, None))
        future.result()

        prepared = session.prepare(
           """
           SELECT * FROM test3rf.test WHERE k=?
           """)
        self.assertIsInstance(prepared, PreparedStatement)

        future = session.execute_async(prepared, (873,))
        results = future.result()
        self.assertEqual(results[0].v, None)

    def test_async_binding_dicts(self):
        """
        Ensure None binding over async queries with dict bindings
        """

        cluster = Cluster(protocol_version=PROTOCOL_VERSION)
        session = cluster.connect()

        prepared = session.prepare(
            """
            INSERT INTO test3rf.test (k, v) VALUES  (?, ?)
            """)

        self.assertIsInstance(prepared, PreparedStatement)
        future = session.execute_async(prepared, {'k': 873, 'v': None})
        future.result()

        prepared = session.prepare(
           """
           SELECT * FROM test3rf.test WHERE k=?
           """)
        self.assertIsInstance(prepared, PreparedStatement)

        future = session.execute_async(prepared, {'k': 873})
        results = future.result()
        self.assertEqual(results[0].v, None)

########NEW FILE########
__FILENAME__ = test_query
# Copyright 2013-2014 DataStax, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

try:
    import unittest2 as unittest
except ImportError:
    import unittest # noqa

from cassandra import ConsistencyLevel
from cassandra.query import (PreparedStatement, BoundStatement, ValueSequence,
                             SimpleStatement, BatchStatement, BatchType,
                             dict_factory)
from cassandra.cluster import Cluster
from cassandra.policies import HostDistance

from tests.integration import PROTOCOL_VERSION


class QueryTest(unittest.TestCase):

    def test_query(self):
        cluster = Cluster(protocol_version=PROTOCOL_VERSION)
        session = cluster.connect()

        prepared = session.prepare(
            """
            INSERT INTO test3rf.test (k, v) VALUES  (?, ?)
            """)

        self.assertIsInstance(prepared, PreparedStatement)
        bound = prepared.bind((1, None))
        self.assertIsInstance(bound, BoundStatement)
        self.assertEqual(2, len(bound.values))
        session.execute(bound)
        self.assertEqual(bound.routing_key, b'\x00\x00\x00\x01')

    def test_value_sequence(self):
        """
        Test the output of ValueSequences()
        """

        my_user_ids = ('alice', 'bob', 'charles')
        self.assertEqual(str(ValueSequence(my_user_ids)), "( 'alice' , 'bob' , 'charles' )")

    def test_trace_prints_okay(self):
        """
        Code coverage to ensure trace prints to string without error
        """

        cluster = Cluster(protocol_version=PROTOCOL_VERSION)
        session = cluster.connect()

        query = "SELECT * FROM system.local"
        statement = SimpleStatement(query)
        session.execute(statement, trace=True)

        # Ensure this does not throw an exception
        str(statement.trace)
        for event in statement.trace.events:
            str(event)

    def test_trace_ignores_row_factory(self):
        cluster = Cluster(protocol_version=PROTOCOL_VERSION)
        session = cluster.connect()
        session.row_factory = dict_factory

        query = "SELECT * FROM system.local"
        statement = SimpleStatement(query)
        session.execute(statement, trace=True)

        # Ensure this does not throw an exception
        str(statement.trace)
        for event in statement.trace.events:
            str(event)


class PreparedStatementTests(unittest.TestCase):

    def test_routing_key(self):
        """
        Simple code coverage to ensure routing_keys can be accessed
        """

        cluster = Cluster(protocol_version=PROTOCOL_VERSION)
        session = cluster.connect()

        prepared = session.prepare(
            """
            INSERT INTO test3rf.test (k, v) VALUES  (?, ?)
            """)

        self.assertIsInstance(prepared, PreparedStatement)
        bound = prepared.bind((1, None))
        self.assertEqual(bound.routing_key, b'\x00\x00\x00\x01')

    def test_empty_routing_key_indexes(self):
        """
        Ensure when routing_key_indexes are blank,
        the routing key should be None
        """

        cluster = Cluster(protocol_version=PROTOCOL_VERSION)
        session = cluster.connect()

        prepared = session.prepare(
            """
            INSERT INTO test3rf.test (k, v) VALUES  (?, ?)
            """)
        prepared.routing_key_indexes = None

        self.assertIsInstance(prepared, PreparedStatement)
        bound = prepared.bind((1, None))
        self.assertEqual(bound.routing_key, None)

    def test_predefined_routing_key(self):
        """
        Basic test that ensures _set_routing_key()
        overrides the current routing key
        """

        cluster = Cluster(protocol_version=PROTOCOL_VERSION)
        session = cluster.connect()

        prepared = session.prepare(
            """
            INSERT INTO test3rf.test (k, v) VALUES  (?, ?)
            """)

        self.assertIsInstance(prepared, PreparedStatement)
        bound = prepared.bind((1, None))
        bound._set_routing_key('fake_key')
        self.assertEqual(bound.routing_key, 'fake_key')

    def test_multiple_routing_key_indexes(self):
        """
        Basic test that uses a fake routing_key_index
        """

        cluster = Cluster(protocol_version=PROTOCOL_VERSION)
        session = cluster.connect()

        prepared = session.prepare(
            """
            INSERT INTO test3rf.test (k, v) VALUES  (?, ?)
            """)
        prepared.routing_key_indexes = {0: {0: 0}, 1: {1: 1}}

        self.assertIsInstance(prepared, PreparedStatement)
        bound = prepared.bind((1, 2))
        self.assertEqual(bound.routing_key, b'\x04\x00\x00\x00\x04\x00\x00\x00')

    def test_bound_keyspace(self):
        """
        Ensure that bound.keyspace works as expected
        """

        cluster = Cluster(protocol_version=PROTOCOL_VERSION)
        session = cluster.connect()

        prepared = session.prepare(
            """
            INSERT INTO test3rf.test (k, v) VALUES  (?, ?)
            """)

        self.assertIsInstance(prepared, PreparedStatement)
        bound = prepared.bind((1, 2))
        self.assertEqual(bound.keyspace, 'test3rf')

        bound.prepared_statement.column_metadata = None
        self.assertEqual(bound.keyspace, None)


class PrintStatementTests(unittest.TestCase):
    """
    Test that shows the format used when printing Statements
    """

    def test_simple_statement(self):
        """
        Highlight the format of printing SimpleStatements
        """

        ss = SimpleStatement('SELECT * FROM test3rf.test', consistency_level=ConsistencyLevel.ONE)
        self.assertEqual(str(ss),
                         '<SimpleStatement query="SELECT * FROM test3rf.test", consistency=ONE>')

    def test_prepared_statement(self):
        """
        Highlight the difference between Prepared and Bound statements
        """

        cluster = Cluster(protocol_version=PROTOCOL_VERSION)
        session = cluster.connect()

        prepared = session.prepare('INSERT INTO test3rf.test (k, v) VALUES (?, ?)')
        prepared.consistency_level = ConsistencyLevel.ONE

        self.assertEqual(str(prepared),
                         '<PreparedStatement query="INSERT INTO test3rf.test (k, v) VALUES (?, ?)", consistency=ONE>')

        bound = prepared.bind((1, 2))
        self.assertEqual(str(bound),
                         '<BoundStatement query="INSERT INTO test3rf.test (k, v) VALUES (?, ?)", values=(1, 2), consistency=ONE>')


class BatchStatementTests(unittest.TestCase):

    def setUp(self):
        if PROTOCOL_VERSION < 2:
            raise unittest.SkipTest(
                "Protocol 2.0+ is required for BATCH operations, currently testing against %r"
                % (PROTOCOL_VERSION,))

        self.cluster = Cluster(protocol_version=PROTOCOL_VERSION)
        self.cluster.set_core_connections_per_host(HostDistance.LOCAL, 1)
        self.session = self.cluster.connect()

        self.session.execute("TRUNCATE test3rf.test")

    def tearDown(self):
        self.cluster.shutdown()

    def confirm_results(self):
        keys = set()
        values = set()
        results = self.session.execute("SELECT * FROM test3rf.test")
        for result in results:
            keys.add(result.k)
            values.add(result.v)

        self.assertEqual(set(range(10)), keys)
        self.assertEqual(set(range(10)), values)

    def test_string_statements(self):
        batch = BatchStatement(BatchType.LOGGED)
        for i in range(10):
            batch.add("INSERT INTO test3rf.test (k, v) VALUES (%s, %s)", (i, i))

        self.session.execute(batch)
        self.session.execute_async(batch).result()
        self.confirm_results()

    def test_simple_statements(self):
        batch = BatchStatement(BatchType.LOGGED)
        for i in range(10):
            batch.add(SimpleStatement("INSERT INTO test3rf.test (k, v) VALUES (%s, %s)"), (i, i))

        self.session.execute(batch)
        self.session.execute_async(batch).result()
        self.confirm_results()

    def test_prepared_statements(self):
        prepared = self.session.prepare("INSERT INTO test3rf.test (k, v) VALUES (?, ?)")

        batch = BatchStatement(BatchType.LOGGED)
        for i in range(10):
            batch.add(prepared, (i, i))

        self.session.execute(batch)
        self.session.execute_async(batch).result()
        self.confirm_results()

    def test_bound_statements(self):
        prepared = self.session.prepare("INSERT INTO test3rf.test (k, v) VALUES (?, ?)")

        batch = BatchStatement(BatchType.LOGGED)
        for i in range(10):
            batch.add(prepared.bind((i, i)))

        self.session.execute(batch)
        self.session.execute_async(batch).result()
        self.confirm_results()

    def test_no_parameters(self):
        batch = BatchStatement(BatchType.LOGGED)
        batch.add("INSERT INTO test3rf.test (k, v) VALUES (0, 0)")
        batch.add("INSERT INTO test3rf.test (k, v) VALUES (1, 1)", ())
        batch.add(SimpleStatement("INSERT INTO test3rf.test (k, v) VALUES (2, 2)"))
        batch.add(SimpleStatement("INSERT INTO test3rf.test (k, v) VALUES (3, 3)"), ())

        prepared = self.session.prepare("INSERT INTO test3rf.test (k, v) VALUES (4, 4)")
        batch.add(prepared)
        batch.add(prepared, ())
        batch.add(prepared.bind([]))
        batch.add(prepared.bind([]), ())

        batch.add("INSERT INTO test3rf.test (k, v) VALUES (5, 5)", ())
        batch.add("INSERT INTO test3rf.test (k, v) VALUES (6, 6)", ())
        batch.add("INSERT INTO test3rf.test (k, v) VALUES (7, 7)", ())
        batch.add("INSERT INTO test3rf.test (k, v) VALUES (8, 8)", ())
        batch.add("INSERT INTO test3rf.test (k, v) VALUES (9, 9)", ())

        self.assertRaises(ValueError, batch.add, prepared.bind([]), (1))
        self.assertRaises(ValueError, batch.add, prepared.bind([]), (1, 2))
        self.assertRaises(ValueError, batch.add, prepared.bind([]), (1, 2, 3))

        self.session.execute(batch)
        self.confirm_results()


class SerialConsistencyTests(unittest.TestCase):

    def setUp(self):
        if PROTOCOL_VERSION < 2:
            raise unittest.SkipTest(
                "Protocol 2.0+ is required for BATCH operations, currently testing against %r"
                % (PROTOCOL_VERSION,))

        self.cluster = Cluster(protocol_version=PROTOCOL_VERSION)
        self.cluster.set_core_connections_per_host(HostDistance.LOCAL, 1)
        self.session = self.cluster.connect()

    def test_conditional_update(self):
        self.session.execute("INSERT INTO test3rf.test (k, v) VALUES (0, 0)")
        statement = SimpleStatement(
            "UPDATE test3rf.test SET v=1 WHERE k=0 IF v=1",
            serial_consistency_level=ConsistencyLevel.SERIAL)
        result = self.session.execute(statement)
        self.assertEqual(1, len(result))
        self.assertFalse(result[0].applied)

        statement = SimpleStatement(
            "UPDATE test3rf.test SET v=1 WHERE k=0 IF v=0",
            serial_consistency_level=ConsistencyLevel.SERIAL)
        result = self.session.execute(statement)
        self.assertEqual(1, len(result))
        self.assertTrue(result[0].applied)

    def test_conditional_update_with_prepared_statements(self):
        self.session.execute("INSERT INTO test3rf.test (k, v) VALUES (0, 0)")
        statement = self.session.prepare(
            "UPDATE test3rf.test SET v=1 WHERE k=0 IF v=2")

        statement.serial_consistency_level = ConsistencyLevel.SERIAL
        result = self.session.execute(statement)
        self.assertEqual(1, len(result))
        self.assertFalse(result[0].applied)

        statement = self.session.prepare(
            "UPDATE test3rf.test SET v=1 WHERE k=0 IF v=0")
        bound = statement.bind(())
        bound.serial_consistency_level = ConsistencyLevel.SERIAL
        result = self.session.execute(statement)
        self.assertEqual(1, len(result))
        self.assertTrue(result[0].applied)

    def test_bad_consistency_level(self):
        statement = SimpleStatement("foo")
        self.assertRaises(ValueError, setattr, statement, 'serial_consistency_level', ConsistencyLevel.ONE)
        self.assertRaises(ValueError, SimpleStatement, 'foo', serial_consistency_level=ConsistencyLevel.ONE)

########NEW FILE########
__FILENAME__ = test_query_paging
# Copyright 2013-2014 DataStax, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from tests.integration import PROTOCOL_VERSION

import logging
log = logging.getLogger(__name__)

try:
    import unittest2 as unittest
except ImportError:
    import unittest # noqa

from itertools import cycle, count
from six.moves import range
from threading import Event

from cassandra.cluster import Cluster
from cassandra.concurrent import execute_concurrent
from cassandra.policies import HostDistance
from cassandra.query import SimpleStatement


class QueryPagingTests(unittest.TestCase):

    def setUp(self):
        if PROTOCOL_VERSION < 2:
            raise unittest.SkipTest(
                "Protocol 2.0+ is required for BATCH operations, currently testing against %r"
                % (PROTOCOL_VERSION,))

        self.cluster = Cluster(protocol_version=PROTOCOL_VERSION)
        self.cluster.set_core_connections_per_host(HostDistance.LOCAL, 1)
        self.session = self.cluster.connect()
        self.session.execute("TRUNCATE test3rf.test")

    def test_paging(self):
        statements_and_params = zip(cycle(["INSERT INTO test3rf.test (k, v) VALUES (%s, 0)"]),
                                    [(i, ) for i in range(100)])
        execute_concurrent(self.session, list(statements_and_params))

        prepared = self.session.prepare("SELECT * FROM test3rf.test")

        for fetch_size in (2, 3, 7, 10, 99, 100, 101, 10000):
            self.session.default_fetch_size = fetch_size
            self.assertEqual(100, len(list(self.session.execute("SELECT * FROM test3rf.test"))))

            statement = SimpleStatement("SELECT * FROM test3rf.test")
            self.assertEqual(100, len(list(self.session.execute(statement))))

            self.assertEqual(100, len(list(self.session.execute(prepared))))

    def test_paging_verify_writes(self):
        statements_and_params = zip(cycle(["INSERT INTO test3rf.test (k, v) VALUES (%s, 0)"]),
                                    [(i, ) for i in range(100)])
        execute_concurrent(self.session, statements_and_params)

        prepared = self.session.prepare("SELECT * FROM test3rf.test")

        for fetch_size in (2, 3, 7, 10, 99, 100, 101, 10000):
            self.session.default_fetch_size = fetch_size
            results = self.session.execute("SELECT * FROM test3rf.test")
            result_array = set()
            result_set = set()
            for result in results:
                result_array.add(result.k)
                result_set.add(result.v)

            self.assertEqual(set(range(100)), result_array)
            self.assertEqual(set([0]), result_set)

            statement = SimpleStatement("SELECT * FROM test3rf.test")
            results = self.session.execute(statement)
            result_array = set()
            result_set = set()
            for result in results:
                result_array.add(result.k)
                result_set.add(result.v)

            self.assertEqual(set(range(100)), result_array)
            self.assertEqual(set([0]), result_set)

            results = self.session.execute(prepared)
            result_array = set()
            result_set = set()
            for result in results:
                result_array.add(result.k)
                result_set.add(result.v)

            self.assertEqual(set(range(100)), result_array)
            self.assertEqual(set([0]), result_set)

    def test_paging_verify_with_composite_keys(self):
        ddl = '''
            CREATE TABLE test3rf.test_paging_verify_2 (
                k1 int,
                k2 int,
                v int,
                PRIMARY KEY(k1, k2)
            )'''
        self.session.execute(ddl)

        statements_and_params = zip(cycle(["INSERT INTO test3rf.test_paging_verify_2 "
                                           "(k1, k2, v) VALUES (0, %s, %s)"]),
                                    [(i, i + 1) for i in range(100)])
        execute_concurrent(self.session, statements_and_params)

        prepared = self.session.prepare("SELECT * FROM test3rf.test_paging_verify_2")

        for fetch_size in (2, 3, 7, 10, 99, 100, 101, 10000):
            self.session.default_fetch_size = fetch_size
            results = self.session.execute("SELECT * FROM test3rf.test_paging_verify_2")
            result_array = []
            value_array = []
            for result in results:
                result_array.append(result.k2)
                value_array.append(result.v)

            self.assertSequenceEqual(range(100), result_array)
            self.assertSequenceEqual(range(1, 101), value_array)

            statement = SimpleStatement("SELECT * FROM test3rf.test_paging_verify_2")
            results = self.session.execute(statement)
            result_array = []
            value_array = []
            for result in results:
                result_array.append(result.k2)
                value_array.append(result.v)

            self.assertSequenceEqual(range(100), result_array)
            self.assertSequenceEqual(range(1, 101), value_array)

            results = self.session.execute(prepared)
            result_array = []
            value_array = []
            for result in results:
                result_array.append(result.k2)
                value_array.append(result.v)

            self.assertSequenceEqual(range(100), result_array)
            self.assertSequenceEqual(range(1, 101), value_array)

    def test_async_paging(self):
        statements_and_params = zip(cycle(["INSERT INTO test3rf.test (k, v) VALUES (%s, 0)"]),
                                    [(i, ) for i in range(100)])
        execute_concurrent(self.session, list(statements_and_params))

        prepared = self.session.prepare("SELECT * FROM test3rf.test")

        for fetch_size in (2, 3, 7, 10, 99, 100, 101, 10000):
            self.session.default_fetch_size = fetch_size
            self.assertEqual(100, len(list(self.session.execute_async("SELECT * FROM test3rf.test").result())))

            statement = SimpleStatement("SELECT * FROM test3rf.test")
            self.assertEqual(100, len(list(self.session.execute_async(statement).result())))

            self.assertEqual(100, len(list(self.session.execute_async(prepared).result())))

    def test_async_paging_verify_writes(self):
        ddl = '''
            CREATE TABLE test3rf.test_async_paging_verify (
                k1 int,
                k2 int,
                v int,
                PRIMARY KEY(k1, k2)
            )'''
        self.session.execute(ddl)

        statements_and_params = zip(cycle(["INSERT INTO test3rf.test_async_paging_verify "
                                           "(k1, k2, v) VALUES (0, %s, %s)"]),
                                    [(i, i + 1) for i in range(100)])
        execute_concurrent(self.session, statements_and_params)

        prepared = self.session.prepare("SELECT * FROM test3rf.test_async_paging_verify")

        for fetch_size in (2, 3, 7, 10, 99, 100, 101, 10000):
            self.session.default_fetch_size = fetch_size
            results = self.session.execute_async("SELECT * FROM test3rf.test_async_paging_verify").result()
            result_array = []
            value_array = []
            for result in results:
                result_array.append(result.k2)
                value_array.append(result.v)

            self.assertSequenceEqual(range(100), result_array)
            self.assertSequenceEqual(range(1, 101), value_array)

            statement = SimpleStatement("SELECT * FROM test3rf.test_async_paging_verify")
            results = self.session.execute_async(statement).result()
            result_array = []
            value_array = []
            for result in results:
                result_array.append(result.k2)
                value_array.append(result.v)

            self.assertSequenceEqual(range(100), result_array)
            self.assertSequenceEqual(range(1, 101), value_array)

            results = self.session.execute_async(prepared).result()
            result_array = []
            value_array = []
            for result in results:
                result_array.append(result.k2)
                value_array.append(result.v)

            self.assertSequenceEqual(range(100), result_array)
            self.assertSequenceEqual(range(1, 101), value_array)

    def test_paging_callbacks(self):
        statements_and_params = zip(cycle(["INSERT INTO test3rf.test (k, v) VALUES (%s, 0)"]),
                                    [(i, ) for i in range(100)])
        execute_concurrent(self.session, list(statements_and_params))

        prepared = self.session.prepare("SELECT * FROM test3rf.test")

        for fetch_size in (2, 3, 7, 10, 99, 100, 101, 10000):
            self.session.default_fetch_size = fetch_size
            future = self.session.execute_async("SELECT * FROM test3rf.test")

            event = Event()
            counter = count()

            def handle_page(rows, future, counter):
                for row in rows:
                    next(counter)

                if future.has_more_pages:
                    future.start_fetching_next_page()
                else:
                    event.set()

            def handle_error(err):
                event.set()
                self.fail(err)

            future.add_callbacks(callback=handle_page, callback_args=(future, counter), errback=handle_error)
            event.wait()
            self.assertEquals(next(counter), 100)

            # simple statement
            future = self.session.execute_async(SimpleStatement("SELECT * FROM test3rf.test"))
            event.clear()
            counter = count()

            future.add_callbacks(callback=handle_page, callback_args=(future, counter), errback=handle_error)
            event.wait()
            self.assertEquals(next(counter), 100)

            # prepared statement
            future = self.session.execute_async(prepared)
            event.clear()
            counter = count()

            future.add_callbacks(callback=handle_page, callback_args=(future, counter), errback=handle_error)
            event.wait()
            self.assertEquals(next(counter), 100)

########NEW FILE########
__FILENAME__ = test_types
# Copyright 2013-2014 DataStax, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

try:
    import unittest2 as unittest
except ImportError:
    import unittest # noqa

import logging
log = logging.getLogger(__name__)

from decimal import Decimal
from datetime import datetime
import six
from uuid import uuid1, uuid4

try:
    from blist import sortedset
except ImportError:
    sortedset = set  # noqa

from cassandra import InvalidRequest
from cassandra.cluster import Cluster
from cassandra.cqltypes import Int32Type, EMPTY
from cassandra.query import dict_factory
from cassandra.util import OrderedDict

from tests.integration import get_server_versions, PROTOCOL_VERSION


class TypeTests(unittest.TestCase):

    def setUp(self):
        self._cass_version, self._cql_version = get_server_versions()

    def test_blob_type_as_string(self):
        c = Cluster(protocol_version=PROTOCOL_VERSION)
        s = c.connect()

        s.execute("""
            CREATE KEYSPACE typetests_blob1
            WITH replication = { 'class' : 'SimpleStrategy', 'replication_factor': '1'}
            """)
        s.set_keyspace("typetests_blob1")
        s.execute("""
            CREATE TABLE mytable (
                a ascii,
                b blob,
                PRIMARY KEY (a)
            )
        """)

        params = [
            'key1',
            b'blobyblob'
        ]

        query = 'INSERT INTO mytable (a, b) VALUES (%s, %s)'

        # In python 3, the 'bytes' type is treated as a blob, so we can
        # correctly encode it with hex notation.
        # In python2, we don't treat the 'str' type as a blob, so we'll encode it
        # as a string literal and have the following failure.
        if six.PY2 and self._cql_version >= (3, 1, 0):
            # Blob values can't be specified using string notation in CQL 3.1.0 and
            # above which is used by default in Cassandra 2.0.
            msg = r'.*Invalid STRING constant \(.*?\) for b of type blob.*'
            self.assertRaisesRegexp(InvalidRequest, msg, s.execute, query, params)
            return
        elif six.PY2:
            params[1] = params[1].encode('hex')

        s.execute(query, params)
        expected_vals = [
           'key1',
           bytearray(b'blobyblob')
        ]

        results = s.execute("SELECT * FROM mytable")

        for expected, actual in zip(expected_vals, results[0]):
            self.assertEqual(expected, actual)

    def test_blob_type_as_bytearray(self):
        c = Cluster(protocol_version=PROTOCOL_VERSION)
        s = c.connect()

        s.execute("""
            CREATE KEYSPACE typetests_blob2
            WITH replication = { 'class' : 'SimpleStrategy', 'replication_factor': '1'}
            """)
        s.set_keyspace("typetests_blob2")
        s.execute("""
            CREATE TABLE mytable (
                a ascii,
                b blob,
                PRIMARY KEY (a)
            )
        """)

        params = [
            'key1',
            bytearray(b'blob1')
        ]

        query = 'INSERT INTO mytable (a, b) VALUES (%s, %s);'
        s.execute(query, params)

        expected_vals = [
            'key1',
            bytearray(b'blob1')
        ]

        results = s.execute("SELECT * FROM mytable")

        for expected, actual in zip(expected_vals, results[0]):
            self.assertEqual(expected, actual)

    create_type_table = """
        CREATE TABLE mytable (
                a text,
                b text,
                c ascii,
                d bigint,
                f boolean,
                g decimal,
                h double,
                i float,
                j inet,
                k int,
                l list<text>,
                m set<int>,
                n map<text, int>,
                o text,
                p timestamp,
                q uuid,
                r timeuuid,
                s varchar,
                t varint,
                PRIMARY KEY (a, b)
            )
        """

    def test_basic_types(self):
        c = Cluster(protocol_version=PROTOCOL_VERSION)
        s = c.connect()
        s.execute("""
            CREATE KEYSPACE typetests
            WITH replication = { 'class' : 'SimpleStrategy', 'replication_factor': '1'}
            """)
        s.set_keyspace("typetests")
        s.execute(self.create_type_table)

        v1_uuid = uuid1()
        v4_uuid = uuid4()
        mydatetime = datetime(2013, 12, 31, 23, 59, 59, 999000)

        params = [
            "sometext",
            "sometext",
            "ascii",  # ascii
            12345678923456789,  # bigint
            True,  # boolean
            Decimal('1.234567890123456789'),  # decimal
            0.000244140625,  # double
            1.25,  # float
            "1.2.3.4",  # inet
            12345,  # int
            ['a', 'b', 'c'],  # list<text> collection
            set([1, 2, 3]),  # set<int> collection
            {'a': 1, 'b': 2},  # map<text, int> collection
            "text",  # text
            mydatetime,  # timestamp
            v4_uuid,  # uuid
            v1_uuid,  # timeuuid
            u"sometext\u1234",  # varchar
            123456789123456789123456789  # varint
        ]

        expected_vals = (
            "sometext",
            "sometext",
            "ascii",  # ascii
            12345678923456789,  # bigint
            True,  # boolean
            Decimal('1.234567890123456789'),  # decimal
            0.000244140625,  # double
            1.25,  # float
            "1.2.3.4",  # inet
            12345,  # int
            ('a', 'b', 'c'),  # list<text> collection
            sortedset((1, 2, 3)),  # set<int> collection
            {'a': 1, 'b': 2},  # map<text, int> collection
            "text",  # text
            mydatetime,  # timestamp
            v4_uuid,  # uuid
            v1_uuid,  # timeuuid
            u"sometext\u1234",  # varchar
            123456789123456789123456789  # varint
        )

        s.execute("""
            INSERT INTO mytable (a, b, c, d, f, g, h, i, j, k, l, m, n, o, p, q, r, s, t)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, params)

        results = s.execute("SELECT * FROM mytable")

        for expected, actual in zip(expected_vals, results[0]):
            self.assertEqual(expected, actual)

        # try the same thing with a prepared statement
        prepared = s.prepare("""
            INSERT INTO mytable (a, b, c, d, f, g, h, i, j, k, l, m, n, o, p, q, r, s, t)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """)

        s.execute(prepared.bind(params))

        results = s.execute("SELECT * FROM mytable")

        for expected, actual in zip(expected_vals, results[0]):
            self.assertEqual(expected, actual)

        # query with prepared statement
        prepared = s.prepare("""
            SELECT a, b, c, d, f, g, h, i, j, k, l, m, n, o, p, q, r, s, t FROM mytable
            """)
        results = s.execute(prepared.bind(()))

        for expected, actual in zip(expected_vals, results[0]):
            self.assertEqual(expected, actual)

        # query with prepared statement, no explicit columns
        prepared = s.prepare("""SELECT * FROM mytable""")
        results = s.execute(prepared.bind(()))

        for expected, actual in zip(expected_vals, results[0]):
            self.assertEqual(expected, actual)

    def test_empty_strings_and_nones(self):
        c = Cluster(protocol_version=PROTOCOL_VERSION)
        s = c.connect()
        s.execute("""
            CREATE KEYSPACE test_empty_strings_and_nones
            WITH replication = { 'class' : 'SimpleStrategy', 'replication_factor': '1'}
            """)
        s.set_keyspace("test_empty_strings_and_nones")
        s.execute(self.create_type_table)

        s.execute("INSERT INTO mytable (a, b) VALUES ('a', 'b')")
        s.row_factory = dict_factory
        results = s.execute("""
            SELECT c, d, f, g, h, i, j, k, l, m, n, o, p, q, r, s, t FROM mytable
            """)
        self.assertTrue(all(x is None for x in results[0].values()))

        prepared = s.prepare("""
            SELECT c, d, f, g, h, i, j, k, l, m, n, o, p, q, r, s, t FROM mytable
            """)
        results = s.execute(prepared.bind(()))
        self.assertTrue(all(x is None for x in results[0].values()))

        # insert empty strings for string-like fields and fetch them
        s.execute("INSERT INTO mytable (a, b, c, o, s, l, n) VALUES ('a', 'b', %s, %s, %s, %s, %s)",
                  ('', '', '', [''], {'': 3}))
        self.assertEqual(
            {'c': '', 'o': '', 's': '', 'l': ('', ), 'n': OrderedDict({'': 3})},
            s.execute("SELECT c, o, s, l, n FROM mytable WHERE a='a' AND b='b'")[0])

        self.assertEqual(
            {'c': '', 'o': '', 's': '', 'l': ('', ), 'n': OrderedDict({'': 3})},
            s.execute(s.prepare("SELECT c, o, s, l, n FROM mytable WHERE a='a' AND b='b'"), [])[0])

        # non-string types shouldn't accept empty strings
        for col in ('d', 'f', 'g', 'h', 'i', 'k', 'l', 'm', 'n', 'q', 'r', 't'):
            query = "INSERT INTO mytable (a, b, %s) VALUES ('a', 'b', %%s)" % (col, )
            try:
                s.execute(query, [''])
            except InvalidRequest:
                pass
            else:
                self.fail("Expected an InvalidRequest error when inserting an "
                          "emptry string for column %s" % (col, ))

            prepared = s.prepare("INSERT INTO mytable (a, b, %s) VALUES ('a', 'b', ?)" % (col, ))
            try:
                s.execute(prepared, [''])
            except TypeError:
                pass
            else:
                self.fail("Expected an InvalidRequest error when inserting an "
                          "emptry string for column %s with a prepared statement" % (col, ))

        # insert values for all columns
        values = ['a', 'b', 'a', 1, True, Decimal('1.0'), 0.1, 0.1,
                  "1.2.3.4", 1, ['a'], set([1]), {'a': 1}, 'a',
                  datetime.now(), uuid4(), uuid1(), 'a', 1]
        s.execute("""
            INSERT INTO mytable (a, b, c, d, f, g, h, i, j, k, l, m, n, o, p, q, r, s, t)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, values)

        # then insert None, which should null them out
        null_values = values[:2] + ([None] * (len(values) - 2))
        s.execute("""
            INSERT INTO mytable (a, b, c, d, f, g, h, i, j, k, l, m, n, o, p, q, r, s, t)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, null_values)

        results = s.execute("""
            SELECT c, d, f, g, h, i, j, k, l, m, n, o, p, q, r, s, t FROM mytable
            """)
        self.assertEqual([], [(name, val) for (name, val) in results[0].items() if val is not None])

        prepared = s.prepare("""
            SELECT c, d, f, g, h, i, j, k, l, m, n, o, p, q, r, s, t FROM mytable
            """)
        results = s.execute(prepared.bind(()))
        self.assertEqual([], [(name, val) for (name, val) in results[0].items() if val is not None])

        # do the same thing again, but use a prepared statement to insert the nulls
        s.execute("""
            INSERT INTO mytable (a, b, c, d, f, g, h, i, j, k, l, m, n, o, p, q, r, s, t)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, values)
        prepared = s.prepare("""
            INSERT INTO mytable (a, b, c, d, f, g, h, i, j, k, l, m, n, o, p, q, r, s, t)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """)
        s.execute(prepared, null_values)

        results = s.execute("""
            SELECT c, d, f, g, h, i, j, k, l, m, n, o, p, q, r, s, t FROM mytable
            """)
        self.assertEqual([], [(name, val) for (name, val) in results[0].items() if val is not None])

        prepared = s.prepare("""
            SELECT c, d, f, g, h, i, j, k, l, m, n, o, p, q, r, s, t FROM mytable
            """)
        results = s.execute(prepared.bind(()))
        self.assertEqual([], [(name, val) for (name, val) in results[0].items() if val is not None])

    def test_empty_values(self):
        c = Cluster(protocol_version=PROTOCOL_VERSION)
        s = c.connect()
        s.execute("""
            CREATE KEYSPACE test_empty_values
            WITH replication = { 'class' : 'SimpleStrategy', 'replication_factor': '1'}
            """)
        s.set_keyspace("test_empty_values")
        s.execute("CREATE TABLE mytable (a text PRIMARY KEY, b int)")
        s.execute("INSERT INTO mytable (a, b) VALUES ('a', blobAsInt(0x))")
        try:
            Int32Type.support_empty_values = True
            results = s.execute("SELECT b FROM mytable WHERE a='a'")[0]
            self.assertIs(EMPTY, results.b)
        finally:
            Int32Type.support_empty_values = False

    def test_timezone_aware_datetimes(self):
        """ Ensure timezone-aware datetimes are converted to timestamps correctly """
        try:
            import pytz
        except ImportError as exc:
            raise unittest.SkipTest('pytz is not available: %r' % (exc,))

        dt = datetime(1997, 8, 29, 11, 14)
        eastern_tz = pytz.timezone('US/Eastern')
        eastern_tz.localize(dt)

        c = Cluster(protocol_version=PROTOCOL_VERSION)
        s = c.connect()

        s.execute("""CREATE KEYSPACE tz_aware_test
            WITH replication = { 'class' : 'SimpleStrategy', 'replication_factor': '1'}""")
        s.set_keyspace("tz_aware_test")
        s.execute("CREATE TABLE mytable (a ascii PRIMARY KEY, b timestamp)")

        # test non-prepared statement
        s.execute("INSERT INTO mytable (a, b) VALUES ('key1', %s)", parameters=(dt,))
        result = s.execute("SELECT b FROM mytable WHERE a='key1'")[0].b
        self.assertEqual(dt.utctimetuple(), result.utctimetuple())

        # test prepared statement
        prepared = s.prepare("INSERT INTO mytable (a, b) VALUES ('key2', ?)")
        s.execute(prepared, parameters=(dt,))
        result = s.execute("SELECT b FROM mytable WHERE a='key2'")[0].b
        self.assertEqual(dt.utctimetuple(), result.utctimetuple())

########NEW FILE########
__FILENAME__ = test_asyncorereactor
# Copyright 2013-2014 DataStax, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import six

try:
    import unittest2 as unittest
except ImportError:
    import unittest # noqa

import errno
import os

from six import BytesIO

import socket
from socket import error as socket_error

from mock import patch, Mock

from cassandra.connection import (HEADER_DIRECTION_TO_CLIENT,
                                  ConnectionException)

from cassandra.protocol import (write_stringmultimap, write_int, write_string,
                                SupportedMessage, ReadyMessage, ServerError)
from cassandra.marshal import uint8_pack, uint32_pack, int32_pack

from cassandra.io.asyncorereactor import AsyncoreConnection


class AsyncoreConnectionTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.socket_patcher = patch('socket.socket', spec=socket.socket)
        cls.mock_socket = cls.socket_patcher.start()
        cls.mock_socket().connect_ex.return_value = 0
        cls.mock_socket().getsockopt.return_value = 0

    @classmethod
    def tearDownClass(cls):
        cls.socket_patcher.stop()

    def make_connection(self):
        c = AsyncoreConnection('1.2.3.4', cql_version='3.0.1')
        c.socket = Mock()
        c.socket.send.side_effect = lambda x: len(x)
        return c

    def make_header_prefix(self, message_class, version=2, stream_id=0):
        return six.binary_type().join(map(uint8_pack, [
            0xff & (HEADER_DIRECTION_TO_CLIENT | version),
            0,  # flags (compression)
            stream_id,
            message_class.opcode  # opcode
        ]))

    def make_options_body(self):
        options_buf = BytesIO()
        write_stringmultimap(options_buf, {
            'CQL_VERSION': ['3.0.1'],
            'COMPRESSION': []
        })
        return options_buf.getvalue()

    def make_error_body(self, code, msg):
        buf = BytesIO()
        write_int(buf, code)
        write_string(buf, msg)
        return buf.getvalue()

    def make_msg(self, header, body=six.binary_type()):
        return header + uint32_pack(len(body)) + body

    def test_successful_connection(self, *args):
        c = self.make_connection()

        # let it write the OptionsMessage
        c.handle_write()

        # read in a SupportedMessage response
        header = self.make_header_prefix(SupportedMessage)
        options = self.make_options_body()
        c.socket.recv.return_value = self.make_msg(header, options)
        c.handle_read()

        # let it write out a StartupMessage
        c.handle_write()

        header = self.make_header_prefix(ReadyMessage, stream_id=1)
        c.socket.recv.return_value = self.make_msg(header)
        c.handle_read()

        self.assertTrue(c.connected_event.is_set())
        return c

    def test_egain_on_buffer_size(self, *args):
        # get a connection that's already fully started
        c = self.test_successful_connection()

        header = six.b('\x00\x00\x00\x00') + int32_pack(20000)
        responses = [
            header + (six.b('a') * (4096 - len(header))),
            six.b('a') * 4096,
            socket_error(errno.EAGAIN),
            six.b('a') * 100,
            socket_error(errno.EAGAIN)]

        def side_effect(*args):
            response = responses.pop(0)
            if isinstance(response, socket_error):
                raise response
            else:
                return response

        c.socket.recv.side_effect = side_effect
        c.handle_read()
        self.assertEqual(c._total_reqd_bytes, 20000 + len(header))
        # the EAGAIN prevents it from reading the last 100 bytes
        c._iobuf.seek(0, os.SEEK_END)
        pos = c._iobuf.tell()
        self.assertEqual(pos, 4096 + 4096)

        # now tell it to read the last 100 bytes
        c.handle_read()
        c._iobuf.seek(0, os.SEEK_END)
        pos = c._iobuf.tell()
        self.assertEqual(pos, 4096 + 4096 + 100)

    def test_protocol_error(self, *args):
        c = self.make_connection()

        # let it write the OptionsMessage
        c.handle_write()

        # read in a SupportedMessage response
        header = self.make_header_prefix(SupportedMessage, version=0xa4)
        options = self.make_options_body()
        c.socket.recv.return_value = self.make_msg(header, options)
        c.handle_read()

        # make sure it errored correctly
        self.assertTrue(c.is_defunct)
        self.assertTrue(c.connected_event.is_set())
        self.assertIsInstance(c.last_error, ConnectionException)

    def test_error_message_on_startup(self, *args):
        c = self.make_connection()

        # let it write the OptionsMessage
        c.handle_write()

        # read in a SupportedMessage response
        header = self.make_header_prefix(SupportedMessage)
        options = self.make_options_body()
        c.socket.recv.return_value = self.make_msg(header, options)
        c.handle_read()

        # let it write out a StartupMessage
        c.handle_write()

        header = self.make_header_prefix(ServerError, stream_id=1)
        body = self.make_error_body(ServerError.error_code, ServerError.summary)
        c.socket.recv.return_value = self.make_msg(header, body)
        c.handle_read()

        # make sure it errored correctly
        self.assertTrue(c.is_defunct)
        self.assertIsInstance(c.last_error, ConnectionException)
        self.assertTrue(c.connected_event.is_set())

    def test_socket_error_on_write(self, *args):
        c = self.make_connection()

        # make the OptionsMessage write fail
        c.socket.send.side_effect = socket_error(errno.EIO, "bad stuff!")
        c.handle_write()

        # make sure it errored correctly
        self.assertTrue(c.is_defunct)
        self.assertIsInstance(c.last_error, socket_error)
        self.assertTrue(c.connected_event.is_set())

    def test_blocking_on_write(self, *args):
        c = self.make_connection()

        # make the OptionsMessage write block
        c.socket.send.side_effect = socket_error(errno.EAGAIN, "socket busy")
        c.handle_write()

        self.assertFalse(c.is_defunct)

        # try again with normal behavior
        c.socket.send.side_effect = lambda x: len(x)
        c.handle_write()
        self.assertFalse(c.is_defunct)
        self.assertTrue(c.socket.send.call_args is not None)

    def test_partial_send(self, *args):
        c = self.make_connection()

        # only write the first four bytes of the OptionsMessage
        c.socket.send.side_effect = None
        c.socket.send.return_value = 4
        c.handle_write()

        self.assertFalse(c.is_defunct)
        self.assertEqual(2, c.socket.send.call_count)
        self.assertEqual(4, len(c.socket.send.call_args[0][0]))

    def test_socket_error_on_read(self, *args):
        c = self.make_connection()

        # let it write the OptionsMessage
        c.handle_write()

        # read in a SupportedMessage response
        c.socket.recv.side_effect = socket_error(errno.EIO, "busy socket")
        c.handle_read()

        # make sure it errored correctly
        self.assertTrue(c.is_defunct)
        self.assertIsInstance(c.last_error, socket_error)
        self.assertTrue(c.connected_event.is_set())

    def test_partial_header_read(self, *args):
        c = self.make_connection()

        header = self.make_header_prefix(SupportedMessage)
        options = self.make_options_body()
        message = self.make_msg(header, options)

        c.socket.recv.return_value = message[0:1]
        c.handle_read()
        self.assertEqual(c._iobuf.getvalue(), message[0:1])

        c.socket.recv.return_value = message[1:]
        c.handle_read()
        self.assertEqual(six.binary_type(), c._iobuf.getvalue())

        # let it write out a StartupMessage
        c.handle_write()

        header = self.make_header_prefix(ReadyMessage, stream_id=1)
        c.socket.recv.return_value = self.make_msg(header)
        c.handle_read()

        self.assertTrue(c.connected_event.is_set())
        self.assertFalse(c.is_defunct)

    def test_partial_message_read(self, *args):
        c = self.make_connection()

        header = self.make_header_prefix(SupportedMessage)
        options = self.make_options_body()
        message = self.make_msg(header, options)

        # read in the first nine bytes
        c.socket.recv.return_value = message[:9]
        c.handle_read()
        self.assertEqual(c._iobuf.getvalue(), message[:9])

        # ... then read in the rest
        c.socket.recv.return_value = message[9:]
        c.handle_read()
        self.assertEqual(six.binary_type(), c._iobuf.getvalue())

        # let it write out a StartupMessage
        c.handle_write()

        header = self.make_header_prefix(ReadyMessage, stream_id=1)
        c.socket.recv.return_value = self.make_msg(header)
        c.handle_read()

        self.assertTrue(c.connected_event.is_set())
        self.assertFalse(c.is_defunct)

########NEW FILE########
__FILENAME__ = test_libevreactor
# Copyright 2013-2014 DataStax, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

try:
    import unittest2 as unittest
except ImportError:
    import unittest # noqa

import errno
import os

import six
from six import BytesIO

from socket import error as socket_error

from mock import patch, Mock

from cassandra.connection import (HEADER_DIRECTION_TO_CLIENT,
                                  ConnectionException)

from cassandra.protocol import (write_stringmultimap, write_int, write_string,
                                SupportedMessage, ReadyMessage, ServerError)
from cassandra.marshal import uint8_pack, uint32_pack, int32_pack

try:
    from cassandra.io.libevreactor import LibevConnection
except ImportError:
    LibevConnection = None  # noqa


@patch('socket.socket')
@patch('cassandra.io.libevwrapper.IO')
@patch('cassandra.io.libevwrapper.Prepare')
@patch('cassandra.io.libevwrapper.Async')
@patch('cassandra.io.libevreactor.LibevConnection._maybe_start_loop')
class LibevConnectionTest(unittest.TestCase):

    def setUp(self):
        if LibevConnection is None:
            raise unittest.SkipTest('libev does not appear to be installed correctly')

    def make_connection(self):
        c = LibevConnection('1.2.3.4', cql_version='3.0.1')
        c._socket = Mock()
        c._socket.send.side_effect = lambda x: len(x)
        return c

    def make_header_prefix(self, message_class, version=2, stream_id=0):
        return six.binary_type().join(map(uint8_pack, [
            0xff & (HEADER_DIRECTION_TO_CLIENT | version),
            0,  # flags (compression)
            stream_id,
            message_class.opcode  # opcode
        ]))

    def make_options_body(self):
        options_buf = BytesIO()
        write_stringmultimap(options_buf, {
            'CQL_VERSION': ['3.0.1'],
            'COMPRESSION': []
        })
        return options_buf.getvalue()

    def make_error_body(self, code, msg):
        buf = BytesIO()
        write_int(buf, code)
        write_string(buf, msg)
        return buf.getvalue()

    def make_msg(self, header, body=six.binary_type()):
        return header + uint32_pack(len(body)) + body

    def test_successful_connection(self, *args):
        c = self.make_connection()

        # let it write the OptionsMessage
        c.handle_write(None, 0)

        # read in a SupportedMessage response
        header = self.make_header_prefix(SupportedMessage)
        options = self.make_options_body()
        c._socket.recv.return_value = self.make_msg(header, options)
        c.handle_read(None, 0)

        # let it write out a StartupMessage
        c.handle_write(None, 0)

        header = self.make_header_prefix(ReadyMessage, stream_id=1)
        c._socket.recv.return_value = self.make_msg(header)
        c.handle_read(None, 0)

        self.assertTrue(c.connected_event.is_set())
        return c

    def test_egain_on_buffer_size(self, *args):
        # get a connection that's already fully started
        c = self.test_successful_connection()

        header = six.b('\x00\x00\x00\x00') + int32_pack(20000)
        responses = [
            header + (six.b('a') * (4096 - len(header))),
            six.b('a') * 4096,
            socket_error(errno.EAGAIN),
            six.b('a') * 100,
            socket_error(errno.EAGAIN)]

        def side_effect(*args):
            response = responses.pop(0)
            if isinstance(response, socket_error):
                raise response
            else:
                return response

        c._socket.recv.side_effect = side_effect
        c.handle_read(None, 0)
        self.assertEqual(c._total_reqd_bytes, 20000 + len(header))
        # the EAGAIN prevents it from reading the last 100 bytes
        c._iobuf.seek(0, os.SEEK_END)
        pos = c._iobuf.tell()
        self.assertEqual(pos, 4096 + 4096)

        # now tell it to read the last 100 bytes
        c.handle_read(None, 0)
        c._iobuf.seek(0, os.SEEK_END)
        pos = c._iobuf.tell()
        self.assertEqual(pos, 4096 + 4096 + 100)

    def test_protocol_error(self, *args):
        c = self.make_connection()

        # let it write the OptionsMessage
        c.handle_write(None, 0)

        # read in a SupportedMessage response
        header = self.make_header_prefix(SupportedMessage, version=0xa4)
        options = self.make_options_body()
        c._socket.recv.return_value = self.make_msg(header, options)
        c.handle_read(None, 0)

        # make sure it errored correctly
        self.assertTrue(c.is_defunct)
        self.assertTrue(c.connected_event.is_set())
        self.assertIsInstance(c.last_error, ConnectionException)

    def test_error_message_on_startup(self, *args):
        c = self.make_connection()

        # let it write the OptionsMessage
        c.handle_write(None, 0)

        # read in a SupportedMessage response
        header = self.make_header_prefix(SupportedMessage)
        options = self.make_options_body()
        c._socket.recv.return_value = self.make_msg(header, options)
        c.handle_read(None, 0)

        # let it write out a StartupMessage
        c.handle_write(None, 0)

        header = self.make_header_prefix(ServerError, stream_id=1)
        body = self.make_error_body(ServerError.error_code, ServerError.summary)
        c._socket.recv.return_value = self.make_msg(header, body)
        c.handle_read(None, 0)

        # make sure it errored correctly
        self.assertTrue(c.is_defunct)
        self.assertIsInstance(c.last_error, ConnectionException)
        self.assertTrue(c.connected_event.is_set())

    def test_socket_error_on_write(self, *args):
        c = self.make_connection()

        # make the OptionsMessage write fail
        c._socket.send.side_effect = socket_error(errno.EIO, "bad stuff!")
        c.handle_write(None, 0)

        # make sure it errored correctly
        self.assertTrue(c.is_defunct)
        self.assertIsInstance(c.last_error, socket_error)
        self.assertTrue(c.connected_event.is_set())

    def test_blocking_on_write(self, *args):
        c = self.make_connection()

        # make the OptionsMessage write block
        c._socket.send.side_effect = socket_error(errno.EAGAIN, "socket busy")
        c.handle_write(None, 0)

        self.assertFalse(c.is_defunct)

        # try again with normal behavior
        c._socket.send.side_effect = lambda x: len(x)
        c.handle_write(None, 0)
        self.assertFalse(c.is_defunct)
        self.assertTrue(c._socket.send.call_args is not None)

    def test_partial_send(self, *args):
        c = self.make_connection()

        # only write the first four bytes of the OptionsMessage
        c._socket.send.side_effect = None
        c._socket.send.return_value = 4
        c.handle_write(None, 0)

        self.assertFalse(c.is_defunct)
        self.assertEqual(2, c._socket.send.call_count)
        self.assertEqual(4, len(c._socket.send.call_args[0][0]))

    def test_socket_error_on_read(self, *args):
        c = self.make_connection()

        # let it write the OptionsMessage
        c.handle_write(None, 0)

        # read in a SupportedMessage response
        c._socket.recv.side_effect = socket_error(errno.EIO, "busy socket")
        c.handle_read(None, 0)

        # make sure it errored correctly
        self.assertTrue(c.is_defunct)
        self.assertIsInstance(c.last_error, socket_error)
        self.assertTrue(c.connected_event.is_set())

    def test_partial_header_read(self, *args):
        c = self.make_connection()

        header = self.make_header_prefix(SupportedMessage)
        options = self.make_options_body()
        message = self.make_msg(header, options)

        # read in the first byte
        c._socket.recv.return_value = message[0:1]
        c.handle_read(None, 0)
        self.assertEqual(c._iobuf.getvalue(), message[0:1])

        c._socket.recv.return_value = message[1:]
        c.handle_read(None, 0)
        self.assertEqual(six.binary_type(), c._iobuf.getvalue())

        # let it write out a StartupMessage
        c.handle_write(None, 0)

        header = self.make_header_prefix(ReadyMessage, stream_id=1)
        c._socket.recv.return_value = self.make_msg(header)
        c.handle_read(None, 0)

        self.assertTrue(c.connected_event.is_set())
        self.assertFalse(c.is_defunct)

    def test_partial_message_read(self, *args):
        c = self.make_connection()

        header = self.make_header_prefix(SupportedMessage)
        options = self.make_options_body()
        message = self.make_msg(header, options)

        # read in the first nine bytes
        c._socket.recv.return_value = message[:9]
        c.handle_read(None, 0)
        self.assertEqual(c._iobuf.getvalue(), message[:9])

        # ... then read in the rest
        c._socket.recv.return_value = message[9:]
        c.handle_read(None, 0)
        self.assertEqual(six.binary_type(), c._iobuf.getvalue())

        # let it write out a StartupMessage
        c.handle_write(None, 0)

        header = self.make_header_prefix(ReadyMessage, stream_id=1)
        c._socket.recv.return_value = self.make_msg(header)
        c.handle_read(None, 0)

        self.assertTrue(c.connected_event.is_set())
        self.assertFalse(c.is_defunct)

########NEW FILE########
__FILENAME__ = test_connection
# Copyright 2013-2014 DataStax, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import six

try:
    import unittest2 as unittest
except ImportError:
    import unittest # noqa

from six import BytesIO

from mock import Mock, ANY

from cassandra.cluster import Cluster
from cassandra.connection import (Connection, HEADER_DIRECTION_TO_CLIENT,
                                  HEADER_DIRECTION_FROM_CLIENT, ProtocolError,
                                  locally_supported_compressions)
from cassandra.marshal import uint8_pack, uint32_pack
from cassandra.protocol import (write_stringmultimap, write_int, write_string,
                                SupportedMessage)


class ConnectionTest(unittest.TestCase):

    protocol_version = 2

    def make_connection(self):
        c = Connection('1.2.3.4')
        c._socket = Mock()
        c._socket.send.side_effect = lambda x: len(x)
        return c

    def make_header_prefix(self, message_class, version=2, stream_id=0):
        return six.binary_type().join(map(uint8_pack, [
            0xff & (HEADER_DIRECTION_TO_CLIENT | version),
            0,  # flags (compression)
            stream_id,
            message_class.opcode  # opcode
        ]))

    def make_options_body(self):
        options_buf = BytesIO()
        write_stringmultimap(options_buf, {
            'CQL_VERSION': ['3.0.1'],
            'COMPRESSION': []
        })
        return options_buf.getvalue()

    def make_error_body(self, code, msg):
        buf = BytesIO()
        write_int(buf, code)
        write_string(buf, msg)
        return buf.getvalue()

    def make_msg(self, header, body=""):
        return header + uint32_pack(len(body)) + body

    def test_bad_protocol_version(self, *args):
        c = self.make_connection()
        c._id_queue.get_nowait()
        c._callbacks = Mock()
        c.defunct = Mock()

        # read in a SupportedMessage response
        header = self.make_header_prefix(SupportedMessage, version=0x04)
        options = self.make_options_body()
        message = self.make_msg(header, options)
        c.process_msg(message, len(message) - 8)

        # make sure it errored correctly
        c.defunct.assert_called_once_with(ANY)
        args, kwargs = c.defunct.call_args
        self.assertIsInstance(args[0], ProtocolError)

    def test_bad_header_direction(self, *args):
        c = self.make_connection()
        c._id_queue.get_nowait()
        c._callbacks = Mock()
        c.defunct = Mock()

        # read in a SupportedMessage response
        header = six.binary_type().join(uint8_pack(i) for i in (
            0xff & (HEADER_DIRECTION_FROM_CLIENT | self.protocol_version),
            0,  # flags (compression)
            0,
            SupportedMessage.opcode  # opcode
        ))
        options = self.make_options_body()
        message = self.make_msg(header, options)
        c.process_msg(message, len(message) - 8)

        # make sure it errored correctly
        c.defunct.assert_called_once_with(ANY)
        args, kwargs = c.defunct.call_args
        self.assertIsInstance(args[0], ProtocolError)

    def test_negative_body_length(self, *args):
        c = self.make_connection()
        c._id_queue.get_nowait()
        c._callbacks = Mock()
        c.defunct = Mock()

        # read in a SupportedMessage response
        header = self.make_header_prefix(SupportedMessage)
        options = self.make_options_body()
        message = self.make_msg(header, options)
        c.process_msg(message, -13)

        # make sure it errored correctly
        c.defunct.assert_called_once_with(ANY)
        args, kwargs = c.defunct.call_args
        self.assertIsInstance(args[0], ProtocolError)

    def test_unsupported_cql_version(self, *args):
        c = self.make_connection()
        c._id_queue.get_nowait()
        c._callbacks = {0: c._handle_options_response}
        c.defunct = Mock()
        c.cql_version = "3.0.3"

        # read in a SupportedMessage response
        header = self.make_header_prefix(SupportedMessage)

        options_buf = BytesIO()
        write_stringmultimap(options_buf, {
            'CQL_VERSION': ['7.8.9'],
            'COMPRESSION': []
        })
        options = options_buf.getvalue()

        message = self.make_msg(header, options)
        c.process_msg(message, len(message) - 8)

        # make sure it errored correctly
        c.defunct.assert_called_once_with(ANY)
        args, kwargs = c.defunct.call_args
        self.assertIsInstance(args[0], ProtocolError)

    def test_prefer_lz4_compression(self, *args):
        c = self.make_connection()
        c._id_queue.get_nowait()
        c._callbacks = {0: c._handle_options_response}
        c.defunct = Mock()
        c.cql_version = "3.0.3"

        locally_supported_compressions.pop('lz4', None)
        locally_supported_compressions.pop('snappy', None)
        locally_supported_compressions['lz4'] = ('lz4compress', 'lz4decompress')
        locally_supported_compressions['snappy'] = ('snappycompress', 'snappydecompress')

        # read in a SupportedMessage response
        header = self.make_header_prefix(SupportedMessage)

        options_buf = BytesIO()
        write_stringmultimap(options_buf, {
            'CQL_VERSION': ['3.0.3'],
            'COMPRESSION': ['snappy', 'lz4']
        })
        options = options_buf.getvalue()

        message = self.make_msg(header, options)
        c.process_msg(message, len(message) - 8)

        self.assertEqual(c.decompressor, locally_supported_compressions['lz4'][1])

    def test_requested_compression_not_available(self, *args):
        c = self.make_connection()
        c._id_queue.get_nowait()
        c._callbacks = {0: c._handle_options_response}
        c.defunct = Mock()
        # request lz4 compression
        c.compression = "lz4"

        locally_supported_compressions.pop('lz4', None)
        locally_supported_compressions.pop('snappy', None)
        locally_supported_compressions['lz4'] = ('lz4compress', 'lz4decompress')
        locally_supported_compressions['snappy'] = ('snappycompress', 'snappydecompress')

        # read in a SupportedMessage response
        header = self.make_header_prefix(SupportedMessage)

        # the server only supports snappy
        options_buf = BytesIO()
        write_stringmultimap(options_buf, {
            'CQL_VERSION': ['3.0.3'],
            'COMPRESSION': ['snappy']
        })
        options = options_buf.getvalue()

        message = self.make_msg(header, options)
        c.process_msg(message, len(message) - 8)

        # make sure it errored correctly
        c.defunct.assert_called_once_with(ANY)
        args, kwargs = c.defunct.call_args
        self.assertIsInstance(args[0], ProtocolError)

    def test_use_requested_compression(self, *args):
        c = self.make_connection()
        c._id_queue.get_nowait()
        c._callbacks = {0: c._handle_options_response}
        c.defunct = Mock()
        # request snappy compression
        c.compression = "snappy"

        locally_supported_compressions.pop('lz4', None)
        locally_supported_compressions.pop('snappy', None)
        locally_supported_compressions['lz4'] = ('lz4compress', 'lz4decompress')
        locally_supported_compressions['snappy'] = ('snappycompress', 'snappydecompress')

        # read in a SupportedMessage response
        header = self.make_header_prefix(SupportedMessage)

        # the server only supports snappy
        options_buf = BytesIO()
        write_stringmultimap(options_buf, {
            'CQL_VERSION': ['3.0.3'],
            'COMPRESSION': ['snappy', 'lz4']
        })
        options = options_buf.getvalue()

        message = self.make_msg(header, options)
        c.process_msg(message, len(message) - 8)

        self.assertEqual(c.decompressor, locally_supported_compressions['snappy'][1])

    def test_disable_compression(self, *args):
        c = self.make_connection()
        c._id_queue.get_nowait()
        c._callbacks = {0: c._handle_options_response}
        c.defunct = Mock()
        # disable compression
        c.compression = False

        locally_supported_compressions.pop('lz4', None)
        locally_supported_compressions.pop('snappy', None)
        locally_supported_compressions['lz4'] = ('lz4compress', 'lz4decompress')
        locally_supported_compressions['snappy'] = ('snappycompress', 'snappydecompress')

        # read in a SupportedMessage response
        header = self.make_header_prefix(SupportedMessage)

        # the server only supports snappy
        options_buf = BytesIO()
        write_stringmultimap(options_buf, {
            'CQL_VERSION': ['3.0.3'],
            'COMPRESSION': ['snappy', 'lz4']
        })
        options = options_buf.getvalue()

        message = self.make_msg(header, options)
        c.process_msg(message, len(message) - 8)

        self.assertEqual(c.decompressor, None)

    def test_not_implemented(self):
        """
        Ensure the following methods throw NIE's. If not, come back and test them.
        """
        c = self.make_connection()

        self.assertRaises(NotImplementedError, c.close)
        self.assertRaises(NotImplementedError, c.register_watcher, None, None)
        self.assertRaises(NotImplementedError, c.register_watchers, None)

    def test_set_keyspace_blocking(self):
        c = self.make_connection()

        self.assertEqual(c.keyspace, None)
        c.set_keyspace_blocking(None)
        self.assertEqual(c.keyspace, None)

        c.keyspace = 'ks'
        c.set_keyspace_blocking('ks')
        self.assertEqual(c.keyspace, 'ks')

    def test_set_connection_class(self):
        cluster = Cluster(connection_class='test')
        self.assertEqual('test', cluster.connection_class)

########NEW FILE########
__FILENAME__ = test_control_connection
# Copyright 2013-2014 DataStax, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

try:
    import unittest2 as unittest
except ImportError:
    import unittest # noqa

from mock import Mock, ANY

from concurrent.futures import ThreadPoolExecutor

from cassandra import OperationTimedOut
from cassandra.protocol import ResultMessage, RESULT_KIND_ROWS
from cassandra.cluster import ControlConnection, Cluster, _Scheduler
from cassandra.pool import Host
from cassandra.policies import (SimpleConvictionPolicy, RoundRobinPolicy,
                                ConstantReconnectionPolicy)

PEER_IP = "foobar"


class MockMetadata(object):

    def __init__(self):
        self.hosts = {
            "192.168.1.0": Host("192.168.1.0", SimpleConvictionPolicy),
            "192.168.1.1": Host("192.168.1.1", SimpleConvictionPolicy),
            "192.168.1.2": Host("192.168.1.2", SimpleConvictionPolicy)
        }
        for host in self.hosts.values():
            host.set_up()

        self.cluster_name = None
        self.partitioner = None
        self.token_map = {}

    def get_host(self, rpc_address):
        return self.hosts.get(rpc_address)

    def all_hosts(self):
        return self.hosts.values()

    def rebuild_token_map(self, partitioner, token_map):
        self.partitioner = partitioner
        self.token_map = token_map


class MockCluster(object):

    max_schema_agreement_wait = Cluster.max_schema_agreement_wait
    load_balancing_policy = RoundRobinPolicy()
    reconnection_policy = ConstantReconnectionPolicy(2)
    down_host = None
    contact_points = []
    is_shutdown = False

    def __init__(self):
        self.metadata = MockMetadata()
        self.added_hosts = []
        self.removed_hosts = []
        self.scheduler = Mock(spec=_Scheduler)
        self.executor = Mock(spec=ThreadPoolExecutor)

    def add_host(self, address, datacenter, rack, signal=False):
        host = Host(address, SimpleConvictionPolicy, datacenter, rack)
        self.added_hosts.append(host)
        return host

    def remove_host(self, host):
        self.removed_hosts.append(host)

    def on_up(self, host):
        pass

    def on_down(self, host, is_host_addition):
        self.down_host = host


class MockConnection(object):

    is_defunct = False

    def __init__(self):
        self.host = "192.168.1.0"
        self.local_results = [
            ["schema_version", "cluster_name", "data_center", "rack", "partitioner", "tokens"],
            [["a", "foocluster", "dc1", "rack1", "Murmur3Partitioner", ["0", "100", "200"]]]
        ]

        self.peer_results = [
            ["rpc_address", "peer", "schema_version", "data_center", "rack", "tokens"],
            [["192.168.1.1", "10.0.0.1", "a", "dc1", "rack1", ["1", "101", "201"]],
             ["192.168.1.2", "10.0.0.2", "a", "dc1", "rack1", ["2", "102", "202"]]]
        ]
        local_response = ResultMessage(
            kind=RESULT_KIND_ROWS, results=self.local_results)
        peer_response = ResultMessage(
            kind=RESULT_KIND_ROWS, results=self.peer_results)

        self.wait_for_responses = Mock(return_value=(peer_response, local_response))


class FakeTime(object):

    def __init__(self):
        self.clock = 0

    def time(self):
        return self.clock

    def sleep(self, amount):
        self.clock += amount


class ControlConnectionTest(unittest.TestCase):

    def setUp(self):
        self.cluster = MockCluster()
        self.connection = MockConnection()
        self.time = FakeTime()

        self.control_connection = ControlConnection(self.cluster, timeout=0.01)
        self.control_connection._connection = self.connection
        self.control_connection._time = self.time

    def _get_matching_schema_preloaded_results(self):
        local_results = [
            ["schema_version", "cluster_name", "data_center", "rack", "partitioner", "tokens"],
            [["a", "foocluster", "dc1", "rack1", "Murmur3Partitioner", ["0", "100", "200"]]]
        ]
        local_response = ResultMessage(kind=RESULT_KIND_ROWS, results=local_results)

        peer_results = [
            ["rpc_address", "peer", "schema_version", "data_center", "rack", "tokens"],
            [["192.168.1.1", "10.0.0.1", "a", "dc1", "rack1", ["1", "101", "201"]],
             ["192.168.1.2", "10.0.0.2", "a", "dc1", "rack1", ["2", "102", "202"]]]
        ]
        peer_response = ResultMessage(kind=RESULT_KIND_ROWS, results=peer_results)

        return (peer_response, local_response)

    def _get_nonmatching_schema_preloaded_results(self):
        local_results = [
            ["schema_version", "cluster_name", "data_center", "rack", "partitioner", "tokens"],
            [["a", "foocluster", "dc1", "rack1", "Murmur3Partitioner", ["0", "100", "200"]]]
        ]
        local_response = ResultMessage(kind=RESULT_KIND_ROWS, results=local_results)

        peer_results = [
            ["rpc_address", "peer", "schema_version", "data_center", "rack", "tokens"],
            [["192.168.1.1", "10.0.0.1", "a", "dc1", "rack1", ["1", "101", "201"]],
             ["192.168.1.2", "10.0.0.2", "b", "dc1", "rack1", ["2", "102", "202"]]]
        ]
        peer_response = ResultMessage(kind=RESULT_KIND_ROWS, results=peer_results)

        return (peer_response, local_response)

    def test_wait_for_schema_agreement(self):
        """
        Basic test with all schema versions agreeing
        """
        self.assertTrue(self.control_connection.wait_for_schema_agreement())
        # the control connection should not have slept at all
        self.assertEqual(self.time.clock, 0)

    def test_wait_for_schema_agreement_uses_preloaded_results_if_given(self):
        """
        wait_for_schema_agreement uses preloaded results if given for shared table queries
        """
        preloaded_results = self._get_matching_schema_preloaded_results()

        self.assertTrue(self.control_connection.wait_for_schema_agreement(preloaded_results=preloaded_results))
        # the control connection should not have slept at all
        self.assertEqual(self.time.clock, 0)
        # the connection should not have made any queries if given preloaded results
        self.assertEqual(self.connection.wait_for_responses.call_count, 0)

    def test_wait_for_schema_agreement_falls_back_to_querying_if_schemas_dont_match_preloaded_result(self):
        """
        wait_for_schema_agreement requery if schema does not match using preloaded results
        """
        preloaded_results = self._get_nonmatching_schema_preloaded_results()

        self.assertTrue(self.control_connection.wait_for_schema_agreement(preloaded_results=preloaded_results))
        # the control connection should not have slept at all
        self.assertEqual(self.time.clock, 0)
        self.assertEqual(self.connection.wait_for_responses.call_count, 1)

    def test_wait_for_schema_agreement_fails(self):
        """
        Make sure the control connection sleeps and retries
        """
        # change the schema version on one node
        self.connection.peer_results[1][1][2] = 'b'
        self.assertFalse(self.control_connection.wait_for_schema_agreement())
        # the control connection should have slept until it hit the limit
        self.assertGreaterEqual(self.time.clock, Cluster.max_schema_agreement_wait)

    def test_wait_for_schema_agreement_skipping(self):
        """
        If rpc_address or schema_version isn't set, the host should be skipped
        """
        # an entry with no schema_version
        self.connection.peer_results[1].append(
            ["192.168.1.3", "10.0.0.3", None, "dc1", "rack1", ["3", "103", "203"]]
        )
        # an entry with a different schema_version and no rpc_address
        self.connection.peer_results[1].append(
            [None, None, "b", "dc1", "rack1", ["4", "104", "204"]]
        )

        # change the schema version on one of the existing entries
        self.connection.peer_results[1][1][3] = 'c'
        self.cluster.metadata.get_host('192.168.1.1').is_up = False

        self.assertTrue(self.control_connection.wait_for_schema_agreement())
        self.assertEqual(self.time.clock, 0)

    def test_wait_for_schema_agreement_rpc_lookup(self):
        """
        If the rpc_address is 0.0.0.0, the "peer" column should be used instead.
        """
        self.connection.peer_results[1].append(
            ["0.0.0.0", PEER_IP, "b", "dc1", "rack1", ["3", "103", "203"]]
        )
        host = Host("0.0.0.0", SimpleConvictionPolicy)
        self.cluster.metadata.hosts[PEER_IP] = host
        host.is_up = False

        # even though the new host has a different schema version, it's
        # marked as down, so the control connection shouldn't care
        self.assertTrue(self.control_connection.wait_for_schema_agreement())
        self.assertEqual(self.time.clock, 0)

        # but once we mark it up, the control connection will care
        host.is_up = True
        self.assertFalse(self.control_connection.wait_for_schema_agreement())
        self.assertGreaterEqual(self.time.clock, Cluster.max_schema_agreement_wait)

    def test_refresh_nodes_and_tokens(self):
        self.control_connection.refresh_node_list_and_token_map()
        meta = self.cluster.metadata
        self.assertEqual(meta.partitioner, 'Murmur3Partitioner')
        self.assertEqual(meta.cluster_name, 'foocluster')

        # check token map
        self.assertEqual(sorted(meta.all_hosts()), sorted(meta.token_map.keys()))
        for token_list in meta.token_map.values():
            self.assertEqual(3, len(token_list))

        # check datacenter/rack
        for host in meta.all_hosts():
            self.assertEqual(host.datacenter, "dc1")
            self.assertEqual(host.rack, "rack1")

        self.assertEqual(self.connection.wait_for_responses.call_count, 1)

    def test_refresh_nodes_and_tokens_uses_preloaded_results_if_given(self):
        """
        refresh_nodes_and_tokens uses preloaded results if given for shared table queries
        """
        preloaded_results = self._get_matching_schema_preloaded_results()

        self.control_connection._refresh_node_list_and_token_map(self.connection, preloaded_results=preloaded_results)
        meta = self.cluster.metadata
        self.assertEqual(meta.partitioner, 'Murmur3Partitioner')
        self.assertEqual(meta.cluster_name, 'foocluster')

        # check token map
        self.assertEqual(sorted(meta.all_hosts()), sorted(meta.token_map.keys()))
        for token_list in meta.token_map.values():
            self.assertEqual(3, len(token_list))

        # check datacenter/rack
        for host in meta.all_hosts():
            self.assertEqual(host.datacenter, "dc1")
            self.assertEqual(host.rack, "rack1")

        # the connection should not have made any queries if given preloaded results
        self.assertEqual(self.connection.wait_for_responses.call_count, 0)

    def test_refresh_nodes_and_tokens_no_partitioner(self):
        """
        Test handling of an unknown partitioner.
        """
        # set the partitioner column to None
        self.connection.local_results[1][0][4] = None
        self.control_connection.refresh_node_list_and_token_map()
        meta = self.cluster.metadata
        self.assertEqual(meta.partitioner, None)
        self.assertEqual(meta.token_map, {})

    def test_refresh_nodes_and_tokens_add_host(self):
        self.connection.peer_results[1].append(
            ["192.168.1.3", "10.0.0.3", "a", "dc1", "rack1", ["3", "103", "203"]]
        )
        self.cluster.scheduler.schedule = lambda delay, f, *args, **kwargs: f(*args, **kwargs)
        self.control_connection.refresh_node_list_and_token_map()
        self.assertEqual(1, len(self.cluster.added_hosts))
        self.assertEqual(self.cluster.added_hosts[0].address, "192.168.1.3")
        self.assertEqual(self.cluster.added_hosts[0].datacenter, "dc1")
        self.assertEqual(self.cluster.added_hosts[0].rack, "rack1")

    def test_refresh_nodes_and_tokens_remove_host(self):
        del self.connection.peer_results[1][1]
        self.control_connection.refresh_node_list_and_token_map()
        self.assertEqual(1, len(self.cluster.removed_hosts))
        self.assertEqual(self.cluster.removed_hosts[0].address, "192.168.1.2")

    def test_refresh_nodes_and_tokens_timeout(self):

        def bad_wait_for_responses(*args, **kwargs):
            self.assertEqual(kwargs['timeout'], self.control_connection._timeout)
            raise OperationTimedOut()

        self.connection.wait_for_responses = bad_wait_for_responses
        self.control_connection.refresh_node_list_and_token_map()
        self.cluster.executor.submit.assert_called_with(self.control_connection._reconnect)

    def test_refresh_schema_timeout(self):

        def bad_wait_for_responses(*args, **kwargs):
            self.assertEqual(kwargs['timeout'], self.control_connection._timeout)
            raise OperationTimedOut()

        self.connection.wait_for_responses = bad_wait_for_responses
        self.control_connection.refresh_schema()
        self.cluster.executor.submit.assert_called_with(self.control_connection._reconnect)

    def test_handle_topology_change(self):
        event = {
            'change_type': 'NEW_NODE',
            'address': ('1.2.3.4', 9000)
        }
        self.control_connection._handle_topology_change(event)
        self.cluster.scheduler.schedule.assert_called_with(ANY, self.control_connection.refresh_node_list_and_token_map)

        event = {
            'change_type': 'REMOVED_NODE',
            'address': ('1.2.3.4', 9000)
        }
        self.control_connection._handle_topology_change(event)
        self.cluster.scheduler.schedule.assert_called_with(ANY, self.cluster.remove_host, None)

        event = {
            'change_type': 'MOVED_NODE',
            'address': ('1.2.3.4', 9000)
        }
        self.control_connection._handle_topology_change(event)
        self.cluster.scheduler.schedule.assert_called_with(ANY, self.control_connection.refresh_node_list_and_token_map)

    def test_handle_status_change(self):
        event = {
            'change_type': 'UP',
            'address': ('1.2.3.4', 9000)
        }
        self.control_connection._handle_status_change(event)
        self.cluster.scheduler.schedule.assert_called_with(ANY, self.control_connection.refresh_node_list_and_token_map)

        # do the same with a known Host
        event = {
            'change_type': 'UP',
            'address': ('192.168.1.0', 9000)
        }
        self.control_connection._handle_status_change(event)
        host = self.cluster.metadata.hosts['192.168.1.0']
        self.cluster.scheduler.schedule.assert_called_with(ANY, self.cluster.on_up, host)

        self.cluster.scheduler.schedule.reset_mock()
        event = {
            'change_type': 'DOWN',
            'address': ('1.2.3.4', 9000)
        }
        self.control_connection._handle_status_change(event)
        self.assertFalse(self.cluster.scheduler.schedule.called)

        # do the same with a known Host
        event = {
            'change_type': 'DOWN',
            'address': ('192.168.1.0', 9000)
        }
        self.control_connection._handle_status_change(event)
        host = self.cluster.metadata.hosts['192.168.1.0']
        self.assertIs(host, self.cluster.down_host)

    def test_handle_schema_change(self):

        for change_type in ('CREATED', 'DROPPED'):
            event = {
                'change_type': change_type,
                'keyspace': 'ks1',
                'table': 'table1'
            }
            self.control_connection._handle_schema_change(event)
            self.cluster.executor.submit.assert_called_with(self.control_connection.refresh_schema, 'ks1')

            event['table'] = None
            self.control_connection._handle_schema_change(event)
            self.cluster.executor.submit.assert_called_with(self.control_connection.refresh_schema, None)

        event = {
            'change_type': 'UPDATED',
            'keyspace': 'ks1',
            'table': 'table1'
        }
        self.control_connection._handle_schema_change(event)
        self.cluster.executor.submit.assert_called_with(self.control_connection.refresh_schema, 'ks1', 'table1')

        event['table'] = None
        self.control_connection._handle_schema_change(event)
        self.cluster.executor.submit.assert_called_with(self.control_connection.refresh_schema, 'ks1', None)

########NEW FILE########
__FILENAME__ = test_host_connection_pool
# Copyright 2013-2014 DataStax, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

try:
    import unittest2 as unittest
except ImportError:
    import unittest # noqa

from mock import Mock, NonCallableMagicMock
from threading import Thread, Event

from cassandra.cluster import Session
from cassandra.connection import Connection, MAX_STREAM_PER_CONNECTION
from cassandra.pool import Host, HostConnectionPool, NoConnectionsAvailable
from cassandra.policies import HostDistance, SimpleConvictionPolicy


class HostConnectionPoolTests(unittest.TestCase):

    def make_session(self):
        session = NonCallableMagicMock(spec=Session, keyspace='foobarkeyspace')
        session.cluster.get_core_connections_per_host.return_value = 1
        session.cluster.get_max_requests_per_connection.return_value = 1
        session.cluster.get_max_connections_per_host.return_value = 1
        return session

    def test_borrow_and_return(self):
        host = Mock(spec=Host, address='ip1')
        session = self.make_session()
        conn = NonCallableMagicMock(spec=Connection, in_flight=0, is_defunct=False, is_closed=False)
        session.cluster.connection_factory.return_value = conn

        pool = HostConnectionPool(host, HostDistance.LOCAL, session)
        session.cluster.connection_factory.assert_called_once_with(host.address)

        c = pool.borrow_connection(timeout=0.01)
        self.assertIs(c, conn)
        self.assertEqual(1, conn.in_flight)
        conn.set_keyspace_blocking.assert_called_once_with('foobarkeyspace')

        pool.return_connection(conn)
        self.assertEqual(0, conn.in_flight)
        self.assertNotIn(conn, pool._trash)

    def test_failed_wait_for_connection(self):
        host = Mock(spec=Host, address='ip1')
        session = self.make_session()
        conn = NonCallableMagicMock(spec=Connection, in_flight=0, is_defunct=False, is_closed=False)
        session.cluster.connection_factory.return_value = conn

        pool = HostConnectionPool(host, HostDistance.LOCAL, session)
        session.cluster.connection_factory.assert_called_once_with(host.address)

        pool.borrow_connection(timeout=0.01)
        self.assertEqual(1, conn.in_flight)

        conn.in_flight = MAX_STREAM_PER_CONNECTION

        # we're already at the max number of requests for this connection,
        # so we this should fail
        self.assertRaises(NoConnectionsAvailable, pool.borrow_connection, 0)

    def test_successful_wait_for_connection(self):
        host = Mock(spec=Host, address='ip1')
        session = self.make_session()
        conn = NonCallableMagicMock(spec=Connection, in_flight=0, is_defunct=False, is_closed=False)
        session.cluster.connection_factory.return_value = conn

        pool = HostConnectionPool(host, HostDistance.LOCAL, session)
        session.cluster.connection_factory.assert_called_once_with(host.address)

        pool.borrow_connection(timeout=0.01)
        self.assertEqual(1, conn.in_flight)

        def get_second_conn():
            c = pool.borrow_connection(1.0)
            self.assertIs(conn, c)
            pool.return_connection(c)

        t = Thread(target=get_second_conn)
        t.start()

        pool.return_connection(conn)
        t.join()
        self.assertEqual(0, conn.in_flight)

    def test_all_connections_trashed(self):
        host = Mock(spec=Host, address='ip1')
        session = self.make_session()
        conn = NonCallableMagicMock(spec=Connection, in_flight=0, is_defunct=False, is_closed=False)
        session.cluster.connection_factory.return_value = conn
        session.cluster.get_core_connections_per_host.return_value = 1

        # manipulate the core connection setting so that we can
        # trash the only connection
        pool = HostConnectionPool(host, HostDistance.LOCAL, session)
        session.cluster.get_core_connections_per_host.return_value = 0
        pool._maybe_trash_connection(conn)
        session.cluster.get_core_connections_per_host.return_value = 1

        submit_called = Event()

        def fire_event(*args, **kwargs):
            submit_called.set()

        session.submit.side_effect = fire_event

        def get_conn():
            conn.reset_mock()
            c = pool.borrow_connection(1.0)
            self.assertIs(conn, c)
            self.assertEqual(1, conn.in_flight)
            conn.set_keyspace_blocking.assert_called_once_with('foobarkeyspace')
            pool.return_connection(c)

        t = Thread(target=get_conn)
        t.start()

        submit_called.wait()
        self.assertEqual(1, pool._scheduled_for_creation)
        session.submit.assert_called_once_with(pool._create_new_connection)

        # now run the create_new_connection call
        pool._create_new_connection()

        t.join()
        self.assertEqual(0, conn.in_flight)

    def test_spawn_when_at_max(self):
        host = Mock(spec=Host, address='ip1')
        session = self.make_session()
        conn = NonCallableMagicMock(spec=Connection, in_flight=0, is_defunct=False, is_closed=False)
        session.cluster.connection_factory.return_value = conn

        # core conns = 1, max conns = 2
        session.cluster.get_max_connections_per_host.return_value = 2

        pool = HostConnectionPool(host, HostDistance.LOCAL, session)
        session.cluster.connection_factory.assert_called_once_with(host.address)

        pool.borrow_connection(timeout=0.01)
        self.assertEqual(1, conn.in_flight)

        # make this conn full
        conn.in_flight = MAX_STREAM_PER_CONNECTION

        # we don't care about making this borrow_connection call succeed for the
        # purposes of this test, as long as it results in a new connection
        # creation being scheduled
        self.assertRaises(NoConnectionsAvailable, pool.borrow_connection, 0)
        session.submit.assert_called_once_with(pool._create_new_connection)

    def test_return_defunct_connection(self):
        host = Mock(spec=Host, address='ip1')
        session = self.make_session()
        conn = NonCallableMagicMock(spec=Connection, in_flight=0, is_defunct=False, is_closed=False)
        session.cluster.connection_factory.return_value = conn

        pool = HostConnectionPool(host, HostDistance.LOCAL, session)
        session.cluster.connection_factory.assert_called_once_with(host.address)

        pool.borrow_connection(timeout=0.01)
        conn.is_defunct = True
        session.cluster.signal_connection_failure.return_value = False
        pool.return_connection(conn)

        # the connection should be closed a new creation scheduled
        conn.close.assert_called_once()
        session.submit.assert_called_once()
        self.assertFalse(pool.is_shutdown)

    def test_return_defunct_connection_on_down_host(self):
        host = Mock(spec=Host, address='ip1')
        session = self.make_session()
        conn = NonCallableMagicMock(spec=Connection, in_flight=0, is_defunct=False, is_closed=False)
        session.cluster.connection_factory.return_value = conn

        pool = HostConnectionPool(host, HostDistance.LOCAL, session)
        session.cluster.connection_factory.assert_called_once_with(host.address)

        pool.borrow_connection(timeout=0.01)
        conn.is_defunct = True
        session.cluster.signal_connection_failure.return_value = True
        pool.return_connection(conn)

        # the connection should be closed a new creation scheduled
        session.cluster.signal_connection_failure.assert_called_once()
        conn.close.assert_called_once()
        self.assertFalse(session.submit.called)
        self.assertTrue(pool.is_shutdown)

    def test_return_closed_connection(self):
        host = Mock(spec=Host, address='ip1')
        session = self.make_session()
        conn = NonCallableMagicMock(spec=Connection, in_flight=0, is_defunct=False, is_closed=True)
        session.cluster.connection_factory.return_value = conn

        pool = HostConnectionPool(host, HostDistance.LOCAL, session)
        session.cluster.connection_factory.assert_called_once_with(host.address)

        pool.borrow_connection(timeout=0.01)
        conn.is_closed = True
        session.cluster.signal_connection_failure.return_value = False
        pool.return_connection(conn)

        # a new creation should be scheduled
        session.submit.assert_called_once()
        self.assertFalse(pool.is_shutdown)

    def test_host_instantiations(self):
        """
        Ensure Host fails if not initialized properly
        """

        self.assertRaises(ValueError, Host, None, None)
        self.assertRaises(ValueError, Host, '127.0.0.1', None)
        self.assertRaises(ValueError, Host, None, SimpleConvictionPolicy)

    def test_host_equality(self):
        """
        Test host equality has correct logic
        """

        a = Host('127.0.0.1', SimpleConvictionPolicy)
        b = Host('127.0.0.1', SimpleConvictionPolicy)
        c = Host('127.0.0.2', SimpleConvictionPolicy)

        self.assertEqual(a, b, 'Two Host instances should be equal when sharing.')
        self.assertNotEqual(a, c, 'Two Host instances should NOT be equal when using two different addresses.')
        self.assertNotEqual(b, c, 'Two Host instances should NOT be equal when using two different addresses.')


class HostTests(unittest.TestCase):

    def test_version_parsing(self):
        host = Host('127.0.0.1', SimpleConvictionPolicy)

        host.set_version("1.0.0")
        self.assertEqual((1, 0, 0), host.version)

        host.set_version("1.0")
        self.assertEqual((1, 0, 0), host.version)

        host.set_version("1.0.0-beta1")
        self.assertEqual((1, 0, 0, 'beta1'), host.version)

        host.set_version("1.0-SNAPSHOT")
        self.assertEqual((1, 0, 0, 'SNAPSHOT'), host.version)

########NEW FILE########
__FILENAME__ = test_marshalling
# Copyright 2013-2014 DataStax, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
from cassandra.marshal import bitlength

try:
    import unittest2 as unittest
except ImportError:
    import unittest  # noqa

import platform
from datetime import datetime
from decimal import Decimal
from uuid import UUID

try:
    from blist import sortedset
except ImportError:
    sortedset = set

from cassandra.cqltypes import lookup_casstype
from cassandra.util import OrderedDict

marshalled_value_pairs = (
    # binary form, type, python native type
    (b'lorem ipsum dolor sit amet', 'AsciiType', 'lorem ipsum dolor sit amet'),
    (b'', 'AsciiType', ''),
    (b'\x01', 'BooleanType', True),
    (b'\x00', 'BooleanType', False),
    (b'', 'BooleanType', None),
    (b'\xff\xfe\xfd\xfc\xfb', 'BytesType', b'\xff\xfe\xfd\xfc\xfb'),
    (b'', 'BytesType', b''),
    (b'\x7f\xff\xff\xff\xff\xff\xff\xff', 'CounterColumnType', 9223372036854775807),
    (b'\x80\x00\x00\x00\x00\x00\x00\x00', 'CounterColumnType', -9223372036854775808),
    (b'', 'CounterColumnType', None),
    (b'\x00\x00\x013\x7fb\xeey', 'DateType', datetime(2011, 11, 7, 18, 55, 49, 881000)),
    (b'', 'DateType', None),
    (b'\x00\x00\x00\r\nJ\x04"^\x91\x04\x8a\xb1\x18\xfe', 'DecimalType', Decimal('1243878957943.1234124191998')),
    (b'\x00\x00\x00\x06\xe5\xde]\x98Y', 'DecimalType', Decimal('-112233.441191')),
    (b'\x00\x00\x00\x14\x00\xfa\xce', 'DecimalType', Decimal('0.00000000000000064206')),
    (b'\x00\x00\x00\x14\xff\x052', 'DecimalType', Decimal('-0.00000000000000064206')),
    (b'\xff\xff\xff\x9c\x00\xfa\xce', 'DecimalType', Decimal('64206e100')),
    (b'', 'DecimalType', None),
    (b'@\xd2\xfa\x08\x00\x00\x00\x00', 'DoubleType', 19432.125),
    (b'\xc0\xd2\xfa\x08\x00\x00\x00\x00', 'DoubleType', -19432.125),
    (b'\x7f\xef\x00\x00\x00\x00\x00\x00', 'DoubleType', 1.7415152243978685e+308),
    (b'', 'DoubleType', None),
    (b'F\x97\xd0@', 'FloatType', 19432.125),
    (b'\xc6\x97\xd0@', 'FloatType', -19432.125),
    (b'\xc6\x97\xd0@', 'FloatType', -19432.125),
    (b'\x7f\x7f\x00\x00', 'FloatType', 338953138925153547590470800371487866880.0),
    (b'', 'FloatType', None),
    (b'\x7f\x50\x00\x00', 'Int32Type', 2135949312),
    (b'\xff\xfd\xcb\x91', 'Int32Type', -144495),
    (b'', 'Int32Type', None),
    (b'f\x1e\xfd\xf2\xe3\xb1\x9f|\x04_\x15', 'IntegerType', 123456789123456789123456789),
    (b'', 'IntegerType', None),
    (b'\x7f\xff\xff\xff\xff\xff\xff\xff', 'LongType', 9223372036854775807),
    (b'\x80\x00\x00\x00\x00\x00\x00\x00', 'LongType', -9223372036854775808),
    (b'', 'LongType', None),
    (b'', 'InetAddressType', None),
    (b'A46\xa9', 'InetAddressType', '65.52.54.169'),
    (b'*\x00\x13(\xe1\x02\xcc\xc0\x00\x00\x00\x00\x00\x00\x01"', 'InetAddressType', '2a00:1328:e102:ccc0::122'),
    (b'\xe3\x81\xbe\xe3\x81\x97\xe3\x81\xa6', 'UTF8Type', u'\u307e\u3057\u3066'),
    (b'\xe3\x81\xbe\xe3\x81\x97\xe3\x81\xa6' * 1000, 'UTF8Type', u'\u307e\u3057\u3066' * 1000),
    (b'', 'UTF8Type', u''),
    (b'\xff' * 16, 'UUIDType', UUID('ffffffff-ffff-ffff-ffff-ffffffffffff')),
    (b'I\x15~\xfc\xef<\x9d\xe3\x16\x98\xaf\x80\x1f\xb4\x0b*', 'UUIDType', UUID('49157efc-ef3c-9de3-1698-af801fb40b2a')),
    (b'', 'UUIDType', None),
    (b'', 'MapType(AsciiType, BooleanType)', None),
    (b'', 'ListType(FloatType)', None),
    (b'', 'SetType(LongType)', None),
    (b'\x00\x00', 'MapType(DecimalType, BooleanType)', OrderedDict()),
    (b'\x00\x00', 'ListType(FloatType)', ()),
    (b'\x00\x00', 'SetType(IntegerType)', sortedset()),
    (b'\x00\x01\x00\x10\xafYC\xa3\xea<\x11\xe1\xabc\xc4,\x03"y\xf0', 'ListType(TimeUUIDType)', (UUID(bytes=b'\xafYC\xa3\xea<\x11\xe1\xabc\xc4,\x03"y\xf0'),)),
)

ordered_dict_value = OrderedDict()
ordered_dict_value[u'\u307fbob'] = 199
ordered_dict_value[u''] = -1
ordered_dict_value[u'\\'] = 0

# these following entries work for me right now, but they're dependent on
# vagaries of internal python ordering for unordered types
marshalled_value_pairs_unsafe = (
    (b'\x00\x03\x00\x06\xe3\x81\xbfbob\x00\x04\x00\x00\x00\xc7\x00\x00\x00\x04\xff\xff\xff\xff\x00\x01\\\x00\x04\x00\x00\x00\x00', 'MapType(UTF8Type, Int32Type)', ordered_dict_value),
    (b'\x00\x02\x00\x08@\x01\x99\x99\x99\x99\x99\x9a\x00\x08@\x14\x00\x00\x00\x00\x00\x00', 'SetType(DoubleType)', sortedset([2.2, 5.0])),
    (b'\x00', 'IntegerType', 0),
)

if platform.python_implementation() == 'CPython':
    # Only run tests for entries which depend on internal python ordering under
    # CPython
    marshalled_value_pairs += marshalled_value_pairs_unsafe


class TestUnmarshal(unittest.TestCase):
    def test_unmarshalling(self):
        for serializedval, valtype, nativeval in marshalled_value_pairs:
            unmarshaller = lookup_casstype(valtype)
            whatwegot = unmarshaller.from_binary(serializedval)
            self.assertEqual(whatwegot, nativeval,
                             msg='Unmarshaller for %s (%s) failed: unmarshal(%r) got %r instead of %r'
                                 % (valtype, unmarshaller, serializedval, whatwegot, nativeval))
            self.assertEqual(type(whatwegot), type(nativeval),
                             msg='Unmarshaller for %s (%s) gave wrong type (%s instead of %s)'
                                 % (valtype, unmarshaller, type(whatwegot), type(nativeval)))

    def test_marshalling(self):
        for serializedval, valtype, nativeval in marshalled_value_pairs:
            marshaller = lookup_casstype(valtype)
            whatwegot = marshaller.to_binary(nativeval)
            self.assertEqual(whatwegot, serializedval,
                             msg='Marshaller for %s (%s) failed: marshal(%r) got %r instead of %r'
                                 % (valtype, marshaller, nativeval, whatwegot, serializedval))
            self.assertEqual(type(whatwegot), type(serializedval),
                             msg='Marshaller for %s (%s) gave wrong type (%s instead of %s)'
                                 % (valtype, marshaller, type(whatwegot), type(serializedval)))

    def test_bitlength(self):
        self.assertEqual(bitlength(9), 4)
        self.assertEqual(bitlength(-10), 0)
        self.assertEqual(bitlength(0), 0)

########NEW FILE########
__FILENAME__ = test_metadata
# Copyright 2013-2014 DataStax, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

try:
    import unittest2 as unittest
except ImportError:
    import unittest # noqa

import cassandra
from cassandra.metadata import (Murmur3Token, MD5Token,
                                BytesToken, ReplicationStrategy,
                                NetworkTopologyStrategy, SimpleStrategy,
                                LocalStrategy, NoMurmur3, protect_name,
                                protect_names, protect_value, is_valid_name)
from cassandra.policies import SimpleConvictionPolicy
from cassandra.pool import Host


class TestStrategies(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        "Hook method for setting up class fixture before running tests in the class."
        if not hasattr(cls, 'assertItemsEqual'):
            cls.assertItemsEqual = cls.assertCountEqual

    def test_replication_strategy(self):
        """
        Basic code coverage testing that ensures different ReplicationStrategies
        can be initiated using parameters correctly.
        """

        rs = ReplicationStrategy()

        self.assertEqual(rs.create('OldNetworkTopologyStrategy', None), None)
        self.assertEqual(rs.create('xxxxxxOldNetworkTopologyStrategy', None), None)

        fake_options_map = {'dc1': '3'}
        self.assertIsInstance(rs.create('NetworkTopologyStrategy', fake_options_map), NetworkTopologyStrategy)
        self.assertEqual(rs.create('NetworkTopologyStrategy', fake_options_map).dc_replication_factors,
                         NetworkTopologyStrategy(fake_options_map).dc_replication_factors)

        self.assertIsInstance(rs.create('xxxxxxNetworkTopologyStrategy', fake_options_map), NetworkTopologyStrategy)
        self.assertEqual(rs.create('xxxxxxNetworkTopologyStrategy', fake_options_map).dc_replication_factors,
                         NetworkTopologyStrategy(fake_options_map).dc_replication_factors)

        fake_options_map = {'options': 'map'}
        self.assertEqual(rs.create('SimpleStrategy', fake_options_map), None)
        self.assertEqual(rs.create('xxxxxxSimpleStrategy', fake_options_map), None)

        fake_options_map = {'options': 'map'}
        self.assertIsInstance(rs.create('LocalStrategy', fake_options_map), LocalStrategy)
        self.assertIsInstance(rs.create('xxxxxxLocalStrategy', fake_options_map), LocalStrategy)

        fake_options_map = {'options': 'map', 'replication_factor': 3}
        self.assertIsInstance(rs.create('SimpleStrategy', fake_options_map), SimpleStrategy)
        self.assertEqual(rs.create('SimpleStrategy', fake_options_map).replication_factor,
                         SimpleStrategy(fake_options_map['replication_factor']).replication_factor)

        self.assertIsInstance(rs.create('xxxxxxSimpleStrategy', fake_options_map), SimpleStrategy)
        self.assertEqual(rs.create('xxxxxxSimpleStrategy', fake_options_map).replication_factor,
                         SimpleStrategy(fake_options_map['replication_factor']).replication_factor)

        self.assertEqual(rs.create('xxxxxxxx', fake_options_map), None)

        self.assertRaises(NotImplementedError, rs.make_token_replica_map, None, None)
        self.assertRaises(NotImplementedError, rs.export_for_schema)

    def test_nts_make_token_replica_map(self):
        token_to_host_owner = {}

        dc1_1 = Host('dc1.1', SimpleConvictionPolicy)
        dc1_2 = Host('dc1.2', SimpleConvictionPolicy)
        dc1_3 = Host('dc1.3', SimpleConvictionPolicy)
        for host in (dc1_1, dc1_2, dc1_3):
            host.set_location_info('dc1', 'rack1')
        token_to_host_owner[MD5Token(0)] = dc1_1
        token_to_host_owner[MD5Token(100)] = dc1_2
        token_to_host_owner[MD5Token(200)] = dc1_3

        dc2_1 = Host('dc2.1', SimpleConvictionPolicy)
        dc2_2 = Host('dc2.2', SimpleConvictionPolicy)
        dc2_1.set_location_info('dc2', 'rack1')
        dc2_2.set_location_info('dc2', 'rack1')
        token_to_host_owner[MD5Token(1)] = dc2_1
        token_to_host_owner[MD5Token(101)] = dc2_2

        dc3_1 = Host('dc3.1', SimpleConvictionPolicy)
        dc3_1.set_location_info('dc3', 'rack3')
        token_to_host_owner[MD5Token(2)] = dc3_1

        ring = [MD5Token(0),
                MD5Token(1),
                MD5Token(2),
                MD5Token(100),
                MD5Token(101),
                MD5Token(200)]

        nts = NetworkTopologyStrategy({'dc1': 2, 'dc2': 2, 'dc3': 1})
        replica_map = nts.make_token_replica_map(token_to_host_owner, ring)

        self.assertItemsEqual(replica_map[MD5Token(0)], (dc1_1, dc1_2, dc2_1, dc2_2, dc3_1))

    def test_nts_make_token_replica_map_empty_dc(self):
        host = Host('1', SimpleConvictionPolicy)
        host.set_location_info('dc1', 'rack1')
        token_to_host_owner = {MD5Token(0): host}
        ring = [MD5Token(0)]
        nts = NetworkTopologyStrategy({'dc1': 1, 'dc2': 0})

        replica_map = nts.make_token_replica_map(token_to_host_owner, ring)
        self.assertEqual(set(replica_map[MD5Token(0)]), set([host]))

    def test_nts_export_for_schema(self):
        # TODO: Cover NetworkTopologyStrategy.export_for_schema()
        pass

    def test_simple_strategy_make_token_replica_map(self):
        host1 = Host('1', SimpleConvictionPolicy)
        host2 = Host('2', SimpleConvictionPolicy)
        host3 = Host('3', SimpleConvictionPolicy)
        token_to_host_owner = {
            MD5Token(0): host1,
            MD5Token(100): host2,
            MD5Token(200): host3
        }
        ring = [MD5Token(0), MD5Token(100), MD5Token(200)]

        rf1_replicas = SimpleStrategy(1).make_token_replica_map(token_to_host_owner, ring)
        self.assertItemsEqual(rf1_replicas[MD5Token(0)], [host1])
        self.assertItemsEqual(rf1_replicas[MD5Token(100)], [host2])
        self.assertItemsEqual(rf1_replicas[MD5Token(200)], [host3])

        rf2_replicas = SimpleStrategy(2).make_token_replica_map(token_to_host_owner, ring)
        self.assertItemsEqual(rf2_replicas[MD5Token(0)], [host1, host2])
        self.assertItemsEqual(rf2_replicas[MD5Token(100)], [host2, host3])
        self.assertItemsEqual(rf2_replicas[MD5Token(200)], [host3, host1])

        rf3_replicas = SimpleStrategy(3).make_token_replica_map(token_to_host_owner, ring)
        self.assertItemsEqual(rf3_replicas[MD5Token(0)], [host1, host2, host3])
        self.assertItemsEqual(rf3_replicas[MD5Token(100)], [host2, host3, host1])
        self.assertItemsEqual(rf3_replicas[MD5Token(200)], [host3, host1, host2])

    def test_ss_equals(self):
        self.assertNotEqual(SimpleStrategy(1), NetworkTopologyStrategy({'dc1': 2}))


class TestNameEscaping(unittest.TestCase):

    def test_protect_name(self):
        """
        Test cassandra.metadata.protect_name output
        """
        self.assertEqual(protect_name('tests'), 'tests')
        self.assertEqual(protect_name('test\'s'), '"test\'s"')
        self.assertEqual(protect_name('test\'s'), "\"test's\"")
        self.assertEqual(protect_name('tests ?!@#$%^&*()'), '"tests ?!@#$%^&*()"')
        self.assertEqual(protect_name('1'), '"1"')
        self.assertEqual(protect_name('1test'), '"1test"')

    def test_protect_names(self):
        """
        Test cassandra.metadata.protect_names output
        """
        self.assertEqual(protect_names(['tests']), ['tests'])
        self.assertEqual(protect_names(
            [
                'tests',
                'test\'s',
                'tests ?!@#$%^&*()',
                '1'
            ]),
             [
                 'tests',
                 "\"test's\"",
                 '"tests ?!@#$%^&*()"',
                 '"1"'
             ])

    def test_protect_value(self):
        """
        Test cassandra.metadata.protect_value output
        """
        self.assertEqual(protect_value(True), "true")
        self.assertEqual(protect_value(False), "false")
        self.assertEqual(protect_value(3.14), '3.14')
        self.assertEqual(protect_value(3), '3')
        self.assertEqual(protect_value('test'), "'test'")
        self.assertEqual(protect_value('test\'s'), "'test''s'")
        self.assertEqual(protect_value(None), 'NULL')

    def test_is_valid_name(self):
        """
        Test cassandra.metadata.is_valid_name output
        """
        self.assertEqual(is_valid_name(None), False)
        self.assertEqual(is_valid_name('test'), True)
        self.assertEqual(is_valid_name('Test'), False)
        self.assertEqual(is_valid_name('t_____1'), True)
        self.assertEqual(is_valid_name('test1'), True)
        self.assertEqual(is_valid_name('1test1'), False)

        non_valid_keywords = cassandra.metadata._keywords - cassandra.metadata._unreserved_keywords
        for keyword in non_valid_keywords:
            self.assertEqual(is_valid_name(keyword), False)


class TestTokens(unittest.TestCase):

    def test_murmur3_tokens(self):
        try:
            murmur3_token = Murmur3Token(cassandra.metadata.MIN_LONG - 1)
            self.assertEqual(murmur3_token.hash_fn('123'), -7468325962851647638)
            self.assertEqual(murmur3_token.hash_fn(str(cassandra.metadata.MAX_LONG)), 7162290910810015547)
            self.assertEqual(str(murmur3_token), '<Murmur3Token: -9223372036854775809>')
        except NoMurmur3:
            raise unittest.SkipTest('The murmur3 extension is not available')

    def test_md5_tokens(self):
        md5_token = MD5Token(cassandra.metadata.MIN_LONG - 1)
        self.assertEqual(md5_token.hash_fn('123'), 42767516990368493138776584305024125808)
        self.assertEqual(md5_token.hash_fn(str(cassandra.metadata.MAX_LONG)), 28528976619278518853815276204542453639)
        self.assertEqual(str(md5_token), '<MD5Token: %s>' % -9223372036854775809)

    def test_bytes_tokens(self):
        bytes_token = BytesToken(str(cassandra.metadata.MIN_LONG - 1))
        self.assertEqual(bytes_token.hash_fn('123'), '123')
        self.assertEqual(bytes_token.hash_fn(123), 123)
        self.assertEqual(bytes_token.hash_fn(str(cassandra.metadata.MAX_LONG)), str(cassandra.metadata.MAX_LONG))
        self.assertEqual(str(bytes_token), "<BytesToken: -9223372036854775809>")

        try:
            bytes_token = BytesToken(cassandra.metadata.MIN_LONG - 1)
            self.fail('Tokens for ByteOrderedPartitioner should be only strings')
        except TypeError:
            pass

########NEW FILE########
__FILENAME__ = test_parameter_binding
# Copyright 2013-2014 DataStax, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

try:
    import unittest2 as unittest
except ImportError:
    import unittest # noqa

from cassandra.query import bind_params, ValueSequence
from cassandra.query import PreparedStatement, BoundStatement
from cassandra.cqltypes import Int32Type
from cassandra.util import OrderedDict

from six.moves import xrange


class ParamBindingTest(unittest.TestCase):

    def test_bind_sequence(self):
        result = bind_params("%s %s %s", (1, "a", 2.0))
        self.assertEqual(result, "1 'a' 2.0")

    def test_bind_map(self):
        result = bind_params("%(a)s %(b)s %(c)s", dict(a=1, b="a", c=2.0))
        self.assertEqual(result, "1 'a' 2.0")

    def test_sequence_param(self):
        result = bind_params("%s", (ValueSequence((1, "a", 2.0)),))
        self.assertEqual(result, "( 1 , 'a' , 2.0 )")

    def test_generator_param(self):
        result = bind_params("%s", ((i for i in xrange(3)),))
        self.assertEqual(result, "[ 0 , 1 , 2 ]")

    def test_none_param(self):
        result = bind_params("%s", (None,))
        self.assertEqual(result, "NULL")

    def test_list_collection(self):
        result = bind_params("%s", (['a', 'b', 'c'],))
        self.assertEqual(result, "[ 'a' , 'b' , 'c' ]")

    def test_set_collection(self):
        result = bind_params("%s", (set(['a', 'b']),))
        self.assertIn(result, ("{ 'a' , 'b' }", "{ 'b' , 'a' }"))

    def test_map_collection(self):
        vals = OrderedDict()
        vals['a'] = 'a'
        vals['b'] = 'b'
        vals['c'] = 'c'
        result = bind_params("%s", (vals,))
        self.assertEqual(result, "{ 'a' : 'a' , 'b' : 'b' , 'c' : 'c' }")

    def test_quote_escaping(self):
        result = bind_params("%s", ("""'ef''ef"ef""ef'""",))
        self.assertEqual(result, """'''ef''''ef"ef""ef'''""")


class BoundStatementTestCase(unittest.TestCase):

    def test_invalid_argument_type(self):
        keyspace = 'keyspace1'
        column_family = 'cf1'

        column_metadata = [
            (keyspace, column_family, 'foo1', Int32Type),
            (keyspace, column_family, 'foo2', Int32Type)
        ]

        prepared_statement = PreparedStatement(column_metadata=column_metadata,
                                               query_id=None,
                                               routing_key_indexes=[],
                                               query=None,
                                               keyspace=keyspace)
        bound_statement = BoundStatement(prepared_statement=prepared_statement)

        values = ['nonint', 1]

        try:
            bound_statement.bind(values)
        except TypeError as e:
            self.assertIn('foo1', str(e))
            self.assertIn('Int32Type', str(e))
            self.assertIn('str', str(e))
        else:
            self.fail('Passed invalid type but exception was not thrown')

        values = [1, ['1', '2']]

        try:
            bound_statement.bind(values)
        except TypeError as e:
            self.assertIn('foo2', str(e))
            self.assertIn('Int32Type', str(e))
            self.assertIn('list', str(e))
        else:
            self.fail('Passed invalid type but exception was not thrown')

########NEW FILE########
__FILENAME__ = test_policies
# Copyright 2013-2014 DataStax, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

try:
    import unittest2 as unittest
except ImportError:
    import unittest # noqa

from itertools import islice, cycle
from mock import Mock
from random import randint
import six
import sys
import struct
from threading import Thread

from cassandra import ConsistencyLevel
from cassandra.cluster import Cluster
from cassandra.metadata import Metadata
from cassandra.policies import (RoundRobinPolicy, DCAwareRoundRobinPolicy,
                                TokenAwarePolicy, SimpleConvictionPolicy,
                                HostDistance, ExponentialReconnectionPolicy,
                                RetryPolicy, WriteType,
                                DowngradingConsistencyRetryPolicy, ConstantReconnectionPolicy,
                                LoadBalancingPolicy, ConvictionPolicy, ReconnectionPolicy, FallthroughRetryPolicy)
from cassandra.pool import Host
from cassandra.query import Statement

from six.moves import xrange


class TestLoadBalancingPolicy(unittest.TestCase):
    def test_non_implemented(self):
        """
        Code coverage for interface-style base class
        """

        policy = LoadBalancingPolicy()
        host = Host("ip1", SimpleConvictionPolicy)
        host.set_location_info("dc1", "rack1")

        self.assertRaises(NotImplementedError, policy.distance, host)
        self.assertRaises(NotImplementedError, policy.populate, None, host)
        self.assertRaises(NotImplementedError, policy.make_query_plan)
        self.assertRaises(NotImplementedError, policy.on_up, host)
        self.assertRaises(NotImplementedError, policy.on_down, host)
        self.assertRaises(NotImplementedError, policy.on_add, host)
        self.assertRaises(NotImplementedError, policy.on_remove, host)

    def test_instance_check(self):
        self.assertRaises(TypeError, Cluster, load_balancing_policy=RoundRobinPolicy)


class TestRoundRobinPolicy(unittest.TestCase):

    def test_basic(self):
        hosts = [0, 1, 2, 3]
        policy = RoundRobinPolicy()
        policy.populate(None, hosts)
        qplan = list(policy.make_query_plan())
        self.assertEqual(sorted(qplan), hosts)

    def test_multiple_query_plans(self):
        hosts = [0, 1, 2, 3]
        policy = RoundRobinPolicy()
        policy.populate(None, hosts)
        for i in xrange(20):
            qplan = list(policy.make_query_plan())
            self.assertEqual(sorted(qplan), hosts)

    def test_single_host(self):
        policy = RoundRobinPolicy()
        policy.populate(None, [0])
        qplan = list(policy.make_query_plan())
        self.assertEqual(qplan, [0])

    def test_status_updates(self):
        hosts = [0, 1, 2, 3]
        policy = RoundRobinPolicy()
        policy.populate(None, hosts)
        policy.on_down(0)
        policy.on_remove(1)
        policy.on_up(4)
        policy.on_add(5)
        qplan = list(policy.make_query_plan())
        self.assertEqual(sorted(qplan), [2, 3, 4, 5])

    def test_thread_safety(self):
        hosts = range(100)
        policy = RoundRobinPolicy()
        policy.populate(None, hosts)

        def check_query_plan():
            for i in range(100):
                qplan = list(policy.make_query_plan())
                self.assertEqual(sorted(qplan), hosts)

        threads = [Thread(target=check_query_plan) for i in range(4)]
        map(lambda t: t.start(), threads)
        map(lambda t: t.join(), threads)

    def test_thread_safety_during_modification(self):
        hosts = range(100)
        policy = RoundRobinPolicy()
        policy.populate(None, hosts)

        errors = []

        def check_query_plan():
            try:
                for i in xrange(100):
                    list(policy.make_query_plan())
            except Exception as exc:
                errors.append(exc)

        def host_up():
            for i in xrange(1000):
                policy.on_up(randint(0, 99))

        def host_down():
            for i in xrange(1000):
                policy.on_down(randint(0, 99))

        threads = []
        for i in range(5):
            threads.append(Thread(target=check_query_plan))
            threads.append(Thread(target=host_up))
            threads.append(Thread(target=host_down))

        # make the GIL switch after every instruction, maximizing
        # the chace of race conditions
        if six.PY2:
            original_interval = sys.getcheckinterval()
        else:
            original_interval = sys.getswitchinterval()

        try:
            if six.PY2:
                sys.setcheckinterval(0)
            else:
                sys.setswitchinterval(0.0001)
            map(lambda t: t.start(), threads)
            map(lambda t: t.join(), threads)
        finally:
            if six.PY2:
                sys.setcheckinterval(original_interval)
            else:
                sys.setswitchinterval(original_interval)

        if errors:
            self.fail("Saw errors: %s" % (errors,))

    def test_no_live_nodes(self):
        """
        Ensure query plan for a downed cluster will execute without errors
        """
        hosts = [0, 1, 2, 3]
        policy = RoundRobinPolicy()
        policy.populate(None, hosts)

        for i in range(4):
            policy.on_down(i)

        qplan = list(policy.make_query_plan())
        self.assertEqual(qplan, [])


class DCAwareRoundRobinPolicyTest(unittest.TestCase):

    def test_no_remote(self):
        hosts = []
        for i in range(4):
            h = Host(i, SimpleConvictionPolicy)
            h.set_location_info("dc1", "rack1")
            hosts.append(h)

        policy = DCAwareRoundRobinPolicy("dc1")
        policy.populate(None, hosts)
        qplan = list(policy.make_query_plan())
        self.assertEqual(sorted(qplan), sorted(hosts))

    def test_with_remotes(self):
        hosts = [Host(i, SimpleConvictionPolicy) for i in range(4)]
        for h in hosts[:2]:
            h.set_location_info("dc1", "rack1")
        for h in hosts[2:]:
            h.set_location_info("dc2", "rack1")

        local_hosts = set(h for h in hosts if h.datacenter == "dc1")
        remote_hosts = set(h for h in hosts if h.datacenter != "dc1")

        # allow all of the remote hosts to be used
        policy = DCAwareRoundRobinPolicy("dc1", used_hosts_per_remote_dc=2)
        policy.populate(Mock(spec=Metadata), hosts)
        qplan = list(policy.make_query_plan())
        self.assertEqual(set(qplan[:2]), local_hosts)
        self.assertEqual(set(qplan[2:]), remote_hosts)

        # allow only one of the remote hosts to be used
        policy = DCAwareRoundRobinPolicy("dc1", used_hosts_per_remote_dc=1)
        policy.populate(Mock(spec=Metadata), hosts)
        qplan = list(policy.make_query_plan())
        self.assertEqual(set(qplan[:2]), local_hosts)

        used_remotes = set(qplan[2:])
        self.assertEqual(1, len(used_remotes))
        self.assertIn(qplan[2], remote_hosts)

        # allow no remote hosts to be used
        policy = DCAwareRoundRobinPolicy("dc1", used_hosts_per_remote_dc=0)
        policy.populate(Mock(spec=Metadata), hosts)
        qplan = list(policy.make_query_plan())
        self.assertEqual(2, len(qplan))
        self.assertEqual(local_hosts, set(qplan))

    def test_get_distance(self):
        policy = DCAwareRoundRobinPolicy("dc1", used_hosts_per_remote_dc=0)
        host = Host("ip1", SimpleConvictionPolicy)
        host.set_location_info("dc1", "rack1")
        policy.populate(Mock(spec=Metadata), [host])

        self.assertEqual(policy.distance(host), HostDistance.LOCAL)

        # used_hosts_per_remote_dc is set to 0, so ignore it
        remote_host = Host("ip2", SimpleConvictionPolicy)
        remote_host.set_location_info("dc2", "rack1")
        self.assertEqual(policy.distance(remote_host), HostDistance.IGNORED)

        # dc2 isn't registered in the policy's live_hosts dict
        policy.used_hosts_per_remote_dc = 1
        self.assertEqual(policy.distance(remote_host), HostDistance.IGNORED)

        # make sure the policy has both dcs registered
        policy.populate(Mock(spec=Metadata), [host, remote_host])
        self.assertEqual(policy.distance(remote_host), HostDistance.REMOTE)

        # since used_hosts_per_remote_dc is set to 1, only the first
        # remote host in dc2 will be REMOTE, the rest are IGNORED
        second_remote_host = Host("ip3", SimpleConvictionPolicy)
        second_remote_host.set_location_info("dc2", "rack1")
        policy.populate(Mock(spec=Metadata), [host, remote_host, second_remote_host])
        distances = set([policy.distance(remote_host), policy.distance(second_remote_host)])
        self.assertEqual(distances, set([HostDistance.REMOTE, HostDistance.IGNORED]))

    def test_status_updates(self):
        hosts = [Host(i, SimpleConvictionPolicy) for i in range(4)]
        for h in hosts[:2]:
            h.set_location_info("dc1", "rack1")
        for h in hosts[2:]:
            h.set_location_info("dc2", "rack1")

        policy = DCAwareRoundRobinPolicy("dc1", used_hosts_per_remote_dc=1)
        policy.populate(Mock(spec=Metadata), hosts)
        policy.on_down(hosts[0])
        policy.on_remove(hosts[2])

        new_local_host = Host(4, SimpleConvictionPolicy)
        new_local_host.set_location_info("dc1", "rack1")
        policy.on_up(new_local_host)

        new_remote_host = Host(5, SimpleConvictionPolicy)
        new_remote_host.set_location_info("dc9000", "rack1")
        policy.on_add(new_remote_host)

        # we now have two local hosts and two remote hosts in separate dcs
        qplan = list(policy.make_query_plan())
        self.assertEqual(set(qplan[:2]), set([hosts[1], new_local_host]))
        self.assertEqual(set(qplan[2:]), set([hosts[3], new_remote_host]))

        # since we have hosts in dc9000, the distance shouldn't be IGNORED
        self.assertEqual(policy.distance(new_remote_host), HostDistance.REMOTE)

        policy.on_down(new_local_host)
        policy.on_down(hosts[1])
        qplan = list(policy.make_query_plan())
        self.assertEqual(set(qplan), set([hosts[3], new_remote_host]))

        policy.on_down(new_remote_host)
        policy.on_down(hosts[3])
        qplan = list(policy.make_query_plan())
        self.assertEqual(qplan, [])

    def test_no_live_nodes(self):
        """
        Ensure query plan for a downed cluster will execute without errors
        """

        hosts = []
        for i in range(4):
            h = Host(i, SimpleConvictionPolicy)
            h.set_location_info("dc1", "rack1")
            hosts.append(h)

        policy = DCAwareRoundRobinPolicy("dc1", used_hosts_per_remote_dc=1)
        policy.populate(Mock(spec=Metadata), hosts)

        for host in hosts:
            policy.on_down(host)

        qplan = list(policy.make_query_plan())
        self.assertEqual(qplan, [])

    def test_no_nodes(self):
        """
        Ensure query plan for an empty cluster will execute without errors
        """

        policy = DCAwareRoundRobinPolicy("dc1", used_hosts_per_remote_dc=1)
        policy.populate(None, [])

        qplan = list(policy.make_query_plan())
        self.assertEqual(qplan, [])


class TokenAwarePolicyTest(unittest.TestCase):

    def test_wrap_round_robin(self):
        cluster = Mock(spec=Cluster)
        cluster.metadata = Mock(spec=Metadata)
        hosts = [Host(str(i), SimpleConvictionPolicy) for i in range(4)]
        for host in hosts:
            host.set_up()

        def get_replicas(keyspace, packed_key):
            index = struct.unpack('>i', packed_key)[0]
            return list(islice(cycle(hosts), index, index + 2))

        cluster.metadata.get_replicas.side_effect = get_replicas

        policy = TokenAwarePolicy(RoundRobinPolicy())
        policy.populate(cluster, hosts)

        for i in range(4):
            query = Statement(routing_key=struct.pack('>i', i))
            qplan = list(policy.make_query_plan(None, query))

            replicas = get_replicas(None, struct.pack('>i', i))
            other = set(h for h in hosts if h not in replicas)
            self.assertEqual(replicas, qplan[:2])
            self.assertEqual(other, set(qplan[2:]))

        # Should use the secondary policy
        for i in range(4):
            qplan = list(policy.make_query_plan())

            self.assertEqual(set(qplan), set(hosts))

    def test_wrap_dc_aware(self):
        cluster = Mock(spec=Cluster)
        cluster.metadata = Mock(spec=Metadata)
        hosts = [Host(str(i), SimpleConvictionPolicy) for i in range(4)]
        for host in hosts:
            host.set_up()
        for h in hosts[:2]:
            h.set_location_info("dc1", "rack1")
        for h in hosts[2:]:
            h.set_location_info("dc2", "rack1")

        def get_replicas(keyspace, packed_key):
            index = struct.unpack('>i', packed_key)[0]
            # return one node from each DC
            if index % 2 == 0:
                return [hosts[0], hosts[2]]
            else:
                return [hosts[1], hosts[3]]

        cluster.metadata.get_replicas.side_effect = get_replicas

        policy = TokenAwarePolicy(DCAwareRoundRobinPolicy("dc1", used_hosts_per_remote_dc=1))
        policy.populate(cluster, hosts)

        for i in range(4):
            query = Statement(routing_key=struct.pack('>i', i))
            qplan = list(policy.make_query_plan(None, query))
            replicas = get_replicas(None, struct.pack('>i', i))

            # first should be the only local replica
            self.assertIn(qplan[0], replicas)
            self.assertEqual(qplan[0].datacenter, "dc1")

            # then the local non-replica
            self.assertNotIn(qplan[1], replicas)
            self.assertEqual(qplan[1].datacenter, "dc1")

            # then one of the remotes (used_hosts_per_remote_dc is 1, so we
            # shouldn't see two remotes)
            self.assertEqual(qplan[2].datacenter, "dc2")
            self.assertEqual(3, len(qplan))

    class FakeCluster:
        def __init__(self):
            self.metadata = Mock(spec=Metadata)

    def test_get_distance(self):
        """
        Same test as DCAwareRoundRobinPolicyTest.test_get_distance()
        Except a FakeCluster is needed for the metadata variable and
        policy.child_policy is needed to change child policy settings
        """

        policy = TokenAwarePolicy(DCAwareRoundRobinPolicy("dc1", used_hosts_per_remote_dc=0))
        host = Host("ip1", SimpleConvictionPolicy)
        host.set_location_info("dc1", "rack1")

        policy.populate(self.FakeCluster(), [host])

        self.assertEqual(policy.distance(host), HostDistance.LOCAL)

        # used_hosts_per_remote_dc is set to 0, so ignore it
        remote_host = Host("ip2", SimpleConvictionPolicy)
        remote_host.set_location_info("dc2", "rack1")
        self.assertEqual(policy.distance(remote_host), HostDistance.IGNORED)

        # dc2 isn't registered in the policy's live_hosts dict
        policy._child_policy.used_hosts_per_remote_dc = 1
        self.assertEqual(policy.distance(remote_host), HostDistance.IGNORED)

        # make sure the policy has both dcs registered
        policy.populate(self.FakeCluster(), [host, remote_host])
        self.assertEqual(policy.distance(remote_host), HostDistance.REMOTE)

        # since used_hosts_per_remote_dc is set to 1, only the first
        # remote host in dc2 will be REMOTE, the rest are IGNORED
        second_remote_host = Host("ip3", SimpleConvictionPolicy)
        second_remote_host.set_location_info("dc2", "rack1")
        policy.populate(self.FakeCluster(), [host, remote_host, second_remote_host])
        distances = set([policy.distance(remote_host), policy.distance(second_remote_host)])
        self.assertEqual(distances, set([HostDistance.REMOTE, HostDistance.IGNORED]))

    def test_status_updates(self):
        """
        Same test as DCAwareRoundRobinPolicyTest.test_status_updates()
        """

        hosts = [Host(i, SimpleConvictionPolicy) for i in range(4)]
        for h in hosts[:2]:
            h.set_location_info("dc1", "rack1")
        for h in hosts[2:]:
            h.set_location_info("dc2", "rack1")

        policy = TokenAwarePolicy(DCAwareRoundRobinPolicy("dc1", used_hosts_per_remote_dc=1))
        policy.populate(self.FakeCluster(), hosts)
        policy.on_down(hosts[0])
        policy.on_remove(hosts[2])

        new_local_host = Host(4, SimpleConvictionPolicy)
        new_local_host.set_location_info("dc1", "rack1")
        policy.on_up(new_local_host)

        new_remote_host = Host(5, SimpleConvictionPolicy)
        new_remote_host.set_location_info("dc9000", "rack1")
        policy.on_add(new_remote_host)

        # we now have two local hosts and two remote hosts in separate dcs
        qplan = list(policy.make_query_plan())
        self.assertEqual(set(qplan[:2]), set([hosts[1], new_local_host]))
        self.assertEqual(set(qplan[2:]), set([hosts[3], new_remote_host]))

        # since we have hosts in dc9000, the distance shouldn't be IGNORED
        self.assertEqual(policy.distance(new_remote_host), HostDistance.REMOTE)

        policy.on_down(new_local_host)
        policy.on_down(hosts[1])
        qplan = list(policy.make_query_plan())
        self.assertEqual(set(qplan), set([hosts[3], new_remote_host]))

        policy.on_down(new_remote_host)
        policy.on_down(hosts[3])
        qplan = list(policy.make_query_plan())
        self.assertEqual(qplan, [])


class ConvictionPolicyTest(unittest.TestCase):
    def test_not_implemented(self):
        """
        Code coverage for interface-style base class
        """

        conviction_policy = ConvictionPolicy(1)
        self.assertRaises(NotImplementedError, conviction_policy.add_failure, 1)
        self.assertRaises(NotImplementedError, conviction_policy.reset)


class SimpleConvictionPolicyTest(unittest.TestCase):
    def test_basic_responses(self):
        """
        Code coverage for SimpleConvictionPolicy
        """

        conviction_policy = SimpleConvictionPolicy(1)
        self.assertEqual(conviction_policy.add_failure(1), True)
        self.assertEqual(conviction_policy.reset(), None)


class ReconnectionPolicyTest(unittest.TestCase):
    def test_basic_responses(self):
        """
        Code coverage for interface-style base class
        """

        policy = ReconnectionPolicy()
        self.assertRaises(NotImplementedError, policy.new_schedule)


class ConstantReconnectionPolicyTest(unittest.TestCase):

    def test_bad_vals(self):
        """
        Test initialization values
        """

        self.assertRaises(ValueError, ConstantReconnectionPolicy, -1, 0)

    def test_schedule(self):
        """
        Test ConstantReconnectionPolicy schedule
        """

        delay = 2
        max_attempts = 100
        policy = ConstantReconnectionPolicy(delay=delay, max_attempts=max_attempts)
        schedule = list(policy.new_schedule())
        self.assertEqual(len(schedule), max_attempts)
        for i, delay in enumerate(schedule):
            self.assertEqual(delay, delay)

    def test_schedule_negative_max_attempts(self):
        """
        Test how negative max_attempts are handled
        """

        delay = 2
        max_attempts = -100

        try:
            ConstantReconnectionPolicy(delay=delay, max_attempts=max_attempts)
            self.fail('max_attempts should throw ValueError when negative')
        except ValueError:
            pass


class ExponentialReconnectionPolicyTest(unittest.TestCase):

    def test_bad_vals(self):
        self.assertRaises(ValueError, ExponentialReconnectionPolicy, -1, 0)
        self.assertRaises(ValueError, ExponentialReconnectionPolicy, 0, -1)
        self.assertRaises(ValueError, ExponentialReconnectionPolicy, 9000, 1)

    def test_schedule(self):
        policy = ExponentialReconnectionPolicy(base_delay=2, max_delay=100)
        schedule = list(policy.new_schedule())
        self.assertEqual(len(schedule), 64)
        for i, delay in enumerate(schedule):
            if i == 0:
                self.assertEqual(delay, 2)
            elif i < 6:
                self.assertEqual(delay, schedule[i - 1] * 2)
            else:
                self.assertEqual(delay, 100)

ONE = ConsistencyLevel.ONE

class RetryPolicyTest(unittest.TestCase):

    def test_read_timeout(self):
        policy = RetryPolicy()

        # if this is the second or greater attempt, rethrow
        retry, consistency = policy.on_read_timeout(
            query=None, consistency=ONE, required_responses=1, received_responses=2,
            data_retrieved=True, retry_num=1)
        self.assertEqual(retry, RetryPolicy.RETHROW)
        self.assertEqual(consistency, None)

        # if we didn't get enough responses, rethrow
        retry, consistency = policy.on_read_timeout(
            query=None, consistency=ONE, required_responses=2, received_responses=1,
            data_retrieved=True, retry_num=0)
        self.assertEqual(retry, RetryPolicy.RETHROW)
        self.assertEqual(consistency, None)

        # if we got enough responses, but also got a data response, rethrow
        retry, consistency = policy.on_read_timeout(
            query=None, consistency=ONE, required_responses=2, received_responses=2,
            data_retrieved=True, retry_num=0)
        self.assertEqual(retry, RetryPolicy.RETHROW)
        self.assertEqual(consistency, None)

        # we got enough responses but no data response, so retry
        retry, consistency = policy.on_read_timeout(
            query=None, consistency=ONE, required_responses=2, received_responses=2,
            data_retrieved=False, retry_num=0)
        self.assertEqual(retry, RetryPolicy.RETRY)
        self.assertEqual(consistency, ONE)

    def test_write_timeout(self):
        policy = RetryPolicy()

        # if this is the second or greater attempt, rethrow
        retry, consistency = policy.on_write_timeout(
            query=None, consistency=ONE, write_type=WriteType.SIMPLE,
            required_responses=1, received_responses=2, retry_num=1)
        self.assertEqual(retry, RetryPolicy.RETHROW)
        self.assertEqual(consistency, None)

        # if it's not a BATCH_LOG write, don't retry it
        retry, consistency = policy.on_write_timeout(
            query=None, consistency=ONE, write_type=WriteType.SIMPLE,
            required_responses=1, received_responses=2, retry_num=0)
        self.assertEqual(retry, RetryPolicy.RETHROW)
        self.assertEqual(consistency, None)

        # retry BATCH_LOG writes regardless of received responses
        retry, consistency = policy.on_write_timeout(
            query=None, consistency=ONE, write_type=WriteType.BATCH_LOG,
            required_responses=10000, received_responses=1, retry_num=0)
        self.assertEqual(retry, RetryPolicy.RETRY)
        self.assertEqual(consistency, ONE)

    def test_unavailable(self):
        """
        Use the same tests for test_write_timeout, but ensure they only RETHROW
        """
        policy = RetryPolicy()

        retry, consistency = policy.on_unavailable(
            query=None, consistency=ONE,
            required_replicas=1, alive_replicas=2, retry_num=1)
        self.assertEqual(retry, RetryPolicy.RETHROW)
        self.assertEqual(consistency, None)

        retry, consistency = policy.on_unavailable(
            query=None, consistency=ONE,
            required_replicas=1, alive_replicas=2, retry_num=0)
        self.assertEqual(retry, RetryPolicy.RETHROW)
        self.assertEqual(consistency, None)

        retry, consistency = policy.on_unavailable(
            query=None, consistency=ONE,
            required_replicas=10000, alive_replicas=1, retry_num=0)
        self.assertEqual(retry, RetryPolicy.RETHROW)
        self.assertEqual(consistency, None)


class FallthroughRetryPolicyTest(unittest.TestCase):

    """
    Use the same tests for test_write_timeout, but ensure they only RETHROW
    """

    def test_read_timeout(self):
        policy = FallthroughRetryPolicy()

        retry, consistency = policy.on_read_timeout(
            query=None, consistency=ONE, required_responses=1, received_responses=2,
            data_retrieved=True, retry_num=1)
        self.assertEqual(retry, RetryPolicy.RETHROW)
        self.assertEqual(consistency, None)

        retry, consistency = policy.on_read_timeout(
            query=None, consistency=ONE, required_responses=2, received_responses=1,
            data_retrieved=True, retry_num=0)
        self.assertEqual(retry, RetryPolicy.RETHROW)
        self.assertEqual(consistency, None)

        retry, consistency = policy.on_read_timeout(
            query=None, consistency=ONE, required_responses=2, received_responses=2,
            data_retrieved=True, retry_num=0)
        self.assertEqual(retry, RetryPolicy.RETHROW)
        self.assertEqual(consistency, None)

        retry, consistency = policy.on_read_timeout(
            query=None, consistency=ONE, required_responses=2, received_responses=2,
            data_retrieved=False, retry_num=0)
        self.assertEqual(retry, RetryPolicy.RETHROW)
        self.assertEqual(consistency, None)

    def test_write_timeout(self):
        policy = FallthroughRetryPolicy()

        retry, consistency = policy.on_write_timeout(
            query=None, consistency=ONE, write_type=WriteType.SIMPLE,
            required_responses=1, received_responses=2, retry_num=1)
        self.assertEqual(retry, RetryPolicy.RETHROW)
        self.assertEqual(consistency, None)

        retry, consistency = policy.on_write_timeout(
            query=None, consistency=ONE, write_type=WriteType.SIMPLE,
            required_responses=1, received_responses=2, retry_num=0)
        self.assertEqual(retry, RetryPolicy.RETHROW)
        self.assertEqual(consistency, None)

        retry, consistency = policy.on_write_timeout(
            query=None, consistency=ONE, write_type=WriteType.BATCH_LOG,
            required_responses=10000, received_responses=1, retry_num=0)
        self.assertEqual(retry, RetryPolicy.RETHROW)
        self.assertEqual(consistency, None)

    def test_unavailable(self):
        policy = FallthroughRetryPolicy()

        retry, consistency = policy.on_unavailable(
            query=None, consistency=ONE,
            required_replicas=1, alive_replicas=2, retry_num=1)
        self.assertEqual(retry, RetryPolicy.RETHROW)
        self.assertEqual(consistency, None)

        retry, consistency = policy.on_unavailable(
            query=None, consistency=ONE,
            required_replicas=1, alive_replicas=2, retry_num=0)
        self.assertEqual(retry, RetryPolicy.RETHROW)
        self.assertEqual(consistency, None)

        retry, consistency = policy.on_unavailable(
            query=None, consistency=ONE,
            required_replicas=10000, alive_replicas=1, retry_num=0)
        self.assertEqual(retry, RetryPolicy.RETHROW)
        self.assertEqual(consistency, None)


class DowngradingConsistencyRetryPolicyTest(unittest.TestCase):

    def test_read_timeout(self):
        policy = DowngradingConsistencyRetryPolicy()

        # if this is the second or greater attempt, rethrow
        retry, consistency = policy.on_read_timeout(
            query=None, consistency=ONE, required_responses=1, received_responses=2,
            data_retrieved=True, retry_num=1)
        self.assertEqual(retry, RetryPolicy.RETHROW)
        self.assertEqual(consistency, None)

        # if we didn't get enough responses, retry at a lower consistency
        retry, consistency = policy.on_read_timeout(
            query=None, consistency=ONE, required_responses=4, received_responses=3,
            data_retrieved=True, retry_num=0)
        self.assertEqual(retry, RetryPolicy.RETRY)
        self.assertEqual(consistency, ConsistencyLevel.THREE)

        # if we didn't get enough responses, retry at a lower consistency
        retry, consistency = policy.on_read_timeout(
            query=None, consistency=ONE, required_responses=3, received_responses=2,
            data_retrieved=True, retry_num=0)
        self.assertEqual(retry, RetryPolicy.RETRY)
        self.assertEqual(consistency, ConsistencyLevel.TWO)

        # retry consistency level goes down based on the # of recv'd responses
        retry, consistency = policy.on_read_timeout(
            query=None, consistency=ONE, required_responses=3, received_responses=1,
            data_retrieved=True, retry_num=0)
        self.assertEqual(retry, RetryPolicy.RETRY)
        self.assertEqual(consistency, ConsistencyLevel.ONE)

        # if we got no responses, rethrow
        retry, consistency = policy.on_read_timeout(
            query=None, consistency=ONE, required_responses=3, received_responses=0,
            data_retrieved=True, retry_num=0)
        self.assertEqual(retry, RetryPolicy.RETHROW)
        self.assertEqual(consistency, None)

        # if we got enough response but no data, retry
        retry, consistency = policy.on_read_timeout(
            query=None, consistency=ONE, required_responses=3, received_responses=3,
            data_retrieved=False, retry_num=0)
        self.assertEqual(retry, RetryPolicy.RETRY)
        self.assertEqual(consistency, ONE)

        # if we got enough responses, but also got a data response, rethrow
        retry, consistency = policy.on_read_timeout(
            query=None, consistency=ONE, required_responses=2, received_responses=2,
            data_retrieved=True, retry_num=0)
        self.assertEqual(retry, RetryPolicy.RETHROW)
        self.assertEqual(consistency, None)

    def test_write_timeout(self):
        policy = DowngradingConsistencyRetryPolicy()

        # if this is the second or greater attempt, rethrow
        retry, consistency = policy.on_write_timeout(
            query=None, consistency=ONE, write_type=WriteType.SIMPLE,
            required_responses=1, received_responses=2, retry_num=1)
        self.assertEqual(retry, RetryPolicy.RETHROW)
        self.assertEqual(consistency, None)

        # ignore failures on these types of writes
        for write_type in (WriteType.SIMPLE, WriteType.BATCH, WriteType.COUNTER):
            retry, consistency = policy.on_write_timeout(
                query=None, consistency=ONE, write_type=write_type,
                required_responses=1, received_responses=2, retry_num=0)
            self.assertEqual(retry, RetryPolicy.IGNORE)

        # downgrade consistency level on unlogged batch writes
        retry, consistency = policy.on_write_timeout(
            query=None, consistency=ONE, write_type=WriteType.UNLOGGED_BATCH,
            required_responses=3, received_responses=1, retry_num=0)
        self.assertEqual(retry, RetryPolicy.RETRY)
        self.assertEqual(consistency, ConsistencyLevel.ONE)

        # retry batch log writes at the same consistency level
        retry, consistency = policy.on_write_timeout(
            query=None, consistency=ONE, write_type=WriteType.BATCH_LOG,
            required_responses=3, received_responses=1, retry_num=0)
        self.assertEqual(retry, RetryPolicy.RETRY)
        self.assertEqual(consistency, ONE)

        # timeout on an unknown write_type
        retry, consistency = policy.on_write_timeout(
            query=None, consistency=ONE, write_type=None,
            required_responses=1, received_responses=2, retry_num=0)
        self.assertEqual(retry, RetryPolicy.RETHROW)
        self.assertEqual(consistency, None)

    def test_unavailable(self):
        policy = DowngradingConsistencyRetryPolicy()

        # if this is the second or greater attempt, rethrow
        retry, consistency = policy.on_unavailable(
            query=None, consistency=ONE, required_replicas=3, alive_replicas=1, retry_num=1)
        self.assertEqual(retry, RetryPolicy.RETHROW)
        self.assertEqual(consistency, None)

        # downgrade consistency on unavailable exceptions
        retry, consistency = policy.on_unavailable(
            query=None, consistency=ONE, required_replicas=3, alive_replicas=1, retry_num=0)
        self.assertEqual(retry, RetryPolicy.RETRY)
        self.assertEqual(consistency, ConsistencyLevel.ONE)

########NEW FILE########
__FILENAME__ = test_response_future
# Copyright 2013-2014 DataStax, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

try:
    import unittest2 as unittest
except ImportError:
    import unittest # noqa

from mock import Mock, MagicMock, ANY

from cassandra import ConsistencyLevel
from cassandra.cluster import Session, ResponseFuture, NoHostAvailable
from cassandra.connection import ConnectionException
from cassandra.protocol import (ReadTimeoutErrorMessage, WriteTimeoutErrorMessage,
                                UnavailableErrorMessage, ResultMessage, QueryMessage,
                                OverloadedErrorMessage, IsBootstrappingErrorMessage,
                                PreparedQueryNotFound, PrepareMessage,
                                RESULT_KIND_ROWS, RESULT_KIND_SET_KEYSPACE,
                                RESULT_KIND_SCHEMA_CHANGE)
from cassandra.policies import RetryPolicy
from cassandra.pool import NoConnectionsAvailable
from cassandra.query import SimpleStatement


class ResponseFutureTests(unittest.TestCase):

    def make_basic_session(self):
        return Mock(spec=Session, row_factory=lambda *x: list(x))

    def make_session(self):
        session = self.make_basic_session()
        session._load_balancer.make_query_plan.return_value = ['ip1', 'ip2']
        session._pools.get.return_value.is_shutdown = False
        return session

    def make_response_future(self, session):
        query = SimpleStatement("SELECT * FROM foo")
        message = QueryMessage(query=query, consistency_level=ConsistencyLevel.ONE)
        return ResponseFuture(session, message, query)

    def make_mock_response(self, results):
        return Mock(spec=ResultMessage, kind=RESULT_KIND_ROWS, results=results, paging_state=None)

    def test_result_message(self):
        session = self.make_basic_session()
        session._load_balancer.make_query_plan.return_value = ['ip1', 'ip2']
        pool = session._pools.get.return_value
        pool.is_shutdown = False

        rf = self.make_response_future(session)
        rf.send_request()

        rf.session._pools.get.assert_called_once_with('ip1')
        pool.borrow_connection.assert_called_once_with(timeout=ANY)
        connection = pool.borrow_connection.return_value
        connection.send_msg.assert_called_once_with(rf.message, cb=ANY)

        rf._set_result(self.make_mock_response([{'col': 'val'}]))
        result = rf.result()
        self.assertEqual(result, [{'col': 'val'}])

    def test_unknown_result_class(self):
        session = self.make_session()
        rf = self.make_response_future(session)
        rf.send_request()
        rf._set_result(object())
        self.assertRaises(ConnectionException, rf.result)

    def test_set_keyspace_result(self):
        session = self.make_session()
        rf = self.make_response_future(session)
        rf.send_request()

        result = Mock(spec=ResultMessage,
                      kind=RESULT_KIND_SET_KEYSPACE,
                      results="keyspace1")
        rf._set_result(result)
        rf._set_keyspace_completed({})
        self.assertEqual(None, rf.result())

    def test_schema_change_result(self):
        session = self.make_session()
        rf = self.make_response_future(session)
        rf.send_request()

        result = Mock(spec=ResultMessage,
                      kind=RESULT_KIND_SCHEMA_CHANGE,
                      results={'keyspace': "keyspace1", "table": "table1"})
        rf._set_result(result)
        session.submit.assert_called_once_with(ANY, 'keyspace1', 'table1', ANY, rf)

    def test_other_result_message_kind(self):
        session = self.make_session()
        rf = self.make_response_future(session)
        rf.send_request()
        result = object()
        rf._set_result(Mock(spec=ResultMessage, kind=999, results=result))
        self.assertIs(result, rf.result())

    def test_read_timeout_error_message(self):
        session = self.make_session()
        query = SimpleStatement("SELECT * FROM foo")
        query.retry_policy = Mock()
        query.retry_policy.on_read_timeout.return_value = (RetryPolicy.RETHROW, None)
        message = QueryMessage(query=query, consistency_level=ConsistencyLevel.ONE)

        rf = ResponseFuture(session, message, query)
        rf.send_request()

        result = Mock(spec=ReadTimeoutErrorMessage, info={})
        rf._set_result(result)

        self.assertRaises(Exception, rf.result)

    def test_write_timeout_error_message(self):
        session = self.make_session()
        query = SimpleStatement("INSERT INFO foo (a, b) VALUES (1, 2)")
        query.retry_policy = Mock()
        query.retry_policy.on_write_timeout.return_value = (RetryPolicy.RETHROW, None)
        message = QueryMessage(query=query, consistency_level=ConsistencyLevel.ONE)

        rf = ResponseFuture(session, message, query)
        rf.send_request()

        result = Mock(spec=WriteTimeoutErrorMessage, info={})
        rf._set_result(result)
        self.assertRaises(Exception, rf.result)

    def test_unavailable_error_message(self):
        session = self.make_session()
        query = SimpleStatement("INSERT INFO foo (a, b) VALUES (1, 2)")
        query.retry_policy = Mock()
        query.retry_policy.on_unavailable.return_value = (RetryPolicy.RETHROW, None)
        message = QueryMessage(query=query, consistency_level=ConsistencyLevel.ONE)

        rf = ResponseFuture(session, message, query)
        rf.send_request()

        result = Mock(spec=UnavailableErrorMessage, info={})
        rf._set_result(result)
        self.assertRaises(Exception, rf.result)

    def test_retry_policy_says_ignore(self):
        session = self.make_session()
        query = SimpleStatement("INSERT INFO foo (a, b) VALUES (1, 2)")
        query.retry_policy = Mock()
        query.retry_policy.on_unavailable.return_value = (RetryPolicy.IGNORE, None)
        message = QueryMessage(query=query, consistency_level=ConsistencyLevel.ONE)

        rf = ResponseFuture(session, message, query)
        rf.send_request()

        result = Mock(spec=UnavailableErrorMessage, info={})
        rf._set_result(result)
        self.assertEqual(None, rf.result())

    def test_retry_policy_says_retry(self):
        session = self.make_session()
        pool = session._pools.get.return_value
        query = SimpleStatement("INSERT INFO foo (a, b) VALUES (1, 2)")
        query.retry_policy = Mock()
        query.retry_policy.on_unavailable.return_value = (RetryPolicy.RETRY, ConsistencyLevel.ONE)
        message = QueryMessage(query=query, consistency_level=ConsistencyLevel.QUORUM)

        rf = ResponseFuture(session, message, query)
        rf.send_request()

        rf.session._pools.get.assert_called_once_with('ip1')
        pool.borrow_connection.assert_called_once_with(timeout=ANY)
        connection = pool.borrow_connection.return_value
        connection.send_msg.assert_called_once_with(rf.message, cb=ANY)

        result = Mock(spec=UnavailableErrorMessage, info={})
        rf._set_result(result)

        session.submit.assert_called_once_with(rf._retry_task, True)
        self.assertEqual(1, rf._query_retries)

        # simulate the executor running this
        rf._retry_task(True)

        # it should try again with the same host since this was
        # an UnavailableException
        rf.session._pools.get.assert_called_with('ip1')
        pool.borrow_connection.assert_called_with(timeout=ANY)
        connection = pool.borrow_connection.return_value
        connection.send_msg.assert_called_with(rf.message, cb=ANY)

    def test_retry_with_different_host(self):
        session = self.make_session()
        pool = session._pools.get.return_value

        rf = self.make_response_future(session)
        rf.message.consistency_level = ConsistencyLevel.QUORUM
        rf.send_request()

        rf.session._pools.get.assert_called_once_with('ip1')
        pool.borrow_connection.assert_called_once_with(timeout=ANY)
        connection = pool.borrow_connection.return_value
        connection.send_msg.assert_called_once_with(rf.message, cb=ANY)
        self.assertEqual(ConsistencyLevel.QUORUM, rf.message.consistency_level)

        result = Mock(spec=OverloadedErrorMessage, info={})
        rf._set_result(result)

        session.submit.assert_called_once_with(rf._retry_task, False)
        # query_retries does not get incremented for Overloaded/Bootstrapping errors
        self.assertEqual(0, rf._query_retries)

        # simulate the executor running this
        rf._retry_task(False)

        # it should try with a different host
        rf.session._pools.get.assert_called_with('ip2')
        pool.borrow_connection.assert_called_with(timeout=ANY)
        connection = pool.borrow_connection.return_value
        connection.send_msg.assert_called_with(rf.message, cb=ANY)

        # the consistency level should be the same
        self.assertEqual(ConsistencyLevel.QUORUM, rf.message.consistency_level)

    def test_all_retries_fail(self):
        session = self.make_session()

        rf = self.make_response_future(session)
        rf.send_request()
        rf.session._pools.get.assert_called_once_with('ip1')

        result = Mock(spec=IsBootstrappingErrorMessage, info={})
        rf._set_result(result)

        # simulate the executor running this
        session.submit.assert_called_once_with(rf._retry_task, False)
        rf._retry_task(False)

        # it should try with a different host
        rf.session._pools.get.assert_called_with('ip2')

        result = Mock(spec=IsBootstrappingErrorMessage, info={})
        rf._set_result(result)

        # simulate the executor running this
        session.submit.assert_called_with(rf._retry_task, False)
        rf._retry_task(False)

        self.assertRaises(NoHostAvailable, rf.result)

    def test_all_pools_shutdown(self):
        session = self.make_basic_session()
        session._load_balancer.make_query_plan.return_value = ['ip1', 'ip2']
        session._pools.get.return_value.is_shutdown = True

        rf = ResponseFuture(session, Mock(), Mock())
        rf.send_request()
        self.assertRaises(NoHostAvailable, rf.result)

    def test_first_pool_shutdown(self):
        session = self.make_basic_session()
        session._load_balancer.make_query_plan.return_value = ['ip1', 'ip2']
        # first return a pool with is_shutdown=True, then is_shutdown=False
        session._pools.get.side_effect = [Mock(is_shutdown=True), Mock(is_shutdown=False)]

        rf = self.make_response_future(session)
        rf.send_request()

        rf._set_result(self.make_mock_response([{'col': 'val'}]))

        result = rf.result()
        self.assertEqual(result, [{'col': 'val'}])

    def test_timeout_getting_connection_from_pool(self):
        session = self.make_basic_session()
        session._load_balancer.make_query_plan.return_value = ['ip1', 'ip2']

        # the first pool will raise an exception on borrow_connection()
        exc = NoConnectionsAvailable()
        first_pool = Mock(is_shutdown=False)
        first_pool.borrow_connection.side_effect = exc
        second_pool = Mock(is_shutdown=False)

        session._pools.get.side_effect = [first_pool, second_pool]

        rf = self.make_response_future(session)
        rf.send_request()

        rf._set_result(self.make_mock_response([{'col': 'val'}]))
        self.assertEqual(rf.result(), [{'col': 'val'}])

        # make sure the exception is recorded correctly
        self.assertEqual(rf._errors, {'ip1': exc})

    def test_callback(self):
        session = self.make_session()
        rf = self.make_response_future(session)
        rf.send_request()

        rf.add_callback(self.assertEqual, [{'col': 'val'}])

        rf._set_result(self.make_mock_response([{'col': 'val'}]))

        result = rf.result()
        self.assertEqual(result, [{'col': 'val'}])

        # this should get called immediately now that the result is set
        rf.add_callback(self.assertEqual, [{'col': 'val'}])

    def test_errback(self):
        session = self.make_session()
        query = SimpleStatement("INSERT INFO foo (a, b) VALUES (1, 2)")
        query.retry_policy = Mock()
        query.retry_policy.on_unavailable.return_value = (RetryPolicy.RETHROW, None)
        message = QueryMessage(query=query, consistency_level=ConsistencyLevel.ONE)

        rf = ResponseFuture(session, message, query)
        rf.send_request()

        rf.add_errback(self.assertIsInstance, Exception)

        result = Mock(spec=UnavailableErrorMessage, info={})
        rf._set_result(result)
        self.assertRaises(Exception, rf.result)

        # this should get called immediately now that the error is set
        rf.add_errback(self.assertIsInstance, Exception)

    def test_add_callbacks(self):
        session = self.make_session()
        query = SimpleStatement("INSERT INFO foo (a, b) VALUES (1, 2)")
        query.retry_policy = Mock()
        query.retry_policy.on_unavailable.return_value = (RetryPolicy.RETHROW, None)
        message = QueryMessage(query=query, consistency_level=ConsistencyLevel.ONE)

        # test errback
        rf = ResponseFuture(session, message, query)
        rf.send_request()

        rf.add_callbacks(
            callback=self.assertEqual, callback_args=([{'col': 'val'}],),
            errback=self.assertIsInstance, errback_args=(Exception,))

        result = Mock(spec=UnavailableErrorMessage, info={})
        rf._set_result(result)
        self.assertRaises(Exception, rf.result)

        # test callback
        rf = ResponseFuture(session, message, query)
        rf.send_request()

        rf.add_callbacks(
            callback=self.assertEqual, callback_args=([{'col': 'val'}],),
            errback=self.assertIsInstance, errback_args=(Exception,))

        rf._set_result(self.make_mock_response([{'col': 'val'}]))
        self.assertEqual(rf.result(), [{'col': 'val'}])

    def test_prepared_query_not_found(self):
        session = self.make_session()
        rf = self.make_response_future(session)
        rf.send_request()

        session.cluster._prepared_statements = MagicMock(dict)
        prepared_statement = session.cluster._prepared_statements.__getitem__.return_value
        prepared_statement.query_string = "SELECT * FROM foobar"
        prepared_statement.keyspace = "FooKeyspace"
        rf._connection.keyspace = "FooKeyspace"

        result = Mock(spec=PreparedQueryNotFound, info='a' * 16)
        rf._set_result(result)

        session.submit.assert_called_once()
        args, kwargs = session.submit.call_args
        self.assertEqual(rf._reprepare, args[-2])
        self.assertIsInstance(args[-1], PrepareMessage)
        self.assertEqual(args[-1].query, "SELECT * FROM foobar")

    def test_prepared_query_not_found_bad_keyspace(self):
        session = self.make_session()
        rf = self.make_response_future(session)
        rf.send_request()

        session.cluster._prepared_statements = MagicMock(dict)
        prepared_statement = session.cluster._prepared_statements.__getitem__.return_value
        prepared_statement.query_string = "SELECT * FROM foobar"
        prepared_statement.keyspace = "FooKeyspace"
        rf._connection.keyspace = "BarKeyspace"

        result = Mock(spec=PreparedQueryNotFound, info='a' * 16)
        rf._set_result(result)
        self.assertRaises(ValueError, rf.result)

########NEW FILE########
__FILENAME__ = test_types
# Copyright 2013-2014 DataStax, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import tempfile

try:
    import unittest2 as unittest
except ImportError:
    import unittest  # noqa

from binascii import unhexlify
import datetime
import cassandra
from cassandra.cqltypes import (BooleanType, lookup_casstype_simple, lookup_casstype,
                                LongType, DecimalType, SetType, cql_typename,
                                CassandraType, UTF8Type, parse_casstype_args,
                                EmptyValue, _CassandraType, DateType)
from cassandra.query import named_tuple_factory
from cassandra.protocol import (write_string, read_longstring, write_stringmap,
                                read_stringmap, read_inet, write_inet,
                                read_string, write_longstring)
from cassandra.encoder import cql_quote


class TypeTests(unittest.TestCase):

    def test_lookup_casstype_simple(self):
        """
        Ensure lookup_casstype_simple returns the correct classes
        """

        self.assertEqual(lookup_casstype_simple('AsciiType'), cassandra.cqltypes.AsciiType)
        self.assertEqual(lookup_casstype_simple('LongType'), cassandra.cqltypes.LongType)
        self.assertEqual(lookup_casstype_simple('BytesType'), cassandra.cqltypes.BytesType)
        self.assertEqual(lookup_casstype_simple('BooleanType'), cassandra.cqltypes.BooleanType)
        self.assertEqual(lookup_casstype_simple('CounterColumnType'), cassandra.cqltypes.CounterColumnType)
        self.assertEqual(lookup_casstype_simple('DecimalType'), cassandra.cqltypes.DecimalType)
        self.assertEqual(lookup_casstype_simple('DoubleType'), cassandra.cqltypes.DoubleType)
        self.assertEqual(lookup_casstype_simple('FloatType'), cassandra.cqltypes.FloatType)
        self.assertEqual(lookup_casstype_simple('InetAddressType'), cassandra.cqltypes.InetAddressType)
        self.assertEqual(lookup_casstype_simple('Int32Type'), cassandra.cqltypes.Int32Type)
        self.assertEqual(lookup_casstype_simple('UTF8Type'), cassandra.cqltypes.UTF8Type)
        self.assertEqual(lookup_casstype_simple('DateType'), cassandra.cqltypes.DateType)
        self.assertEqual(lookup_casstype_simple('TimeUUIDType'), cassandra.cqltypes.TimeUUIDType)
        self.assertEqual(lookup_casstype_simple('UUIDType'), cassandra.cqltypes.UUIDType)
        self.assertEqual(lookup_casstype_simple('IntegerType'), cassandra.cqltypes.IntegerType)
        self.assertEqual(lookup_casstype_simple('MapType'), cassandra.cqltypes.MapType)
        self.assertEqual(lookup_casstype_simple('ListType'), cassandra.cqltypes.ListType)
        self.assertEqual(lookup_casstype_simple('SetType'), cassandra.cqltypes.SetType)
        self.assertEqual(lookup_casstype_simple('CompositeType'), cassandra.cqltypes.CompositeType)
        self.assertEqual(lookup_casstype_simple('ColumnToCollectionType'), cassandra.cqltypes.ColumnToCollectionType)
        self.assertEqual(lookup_casstype_simple('ReversedType'), cassandra.cqltypes.ReversedType)

        self.assertEqual(str(lookup_casstype_simple('unknown')), str(cassandra.cqltypes.mkUnrecognizedType('unknown')))

    def test_lookup_casstype(self):
        """
        Ensure lookup_casstype returns the correct classes
        """

        self.assertEqual(lookup_casstype('AsciiType'), cassandra.cqltypes.AsciiType)
        self.assertEqual(lookup_casstype('LongType'), cassandra.cqltypes.LongType)
        self.assertEqual(lookup_casstype('BytesType'), cassandra.cqltypes.BytesType)
        self.assertEqual(lookup_casstype('BooleanType'), cassandra.cqltypes.BooleanType)
        self.assertEqual(lookup_casstype('CounterColumnType'), cassandra.cqltypes.CounterColumnType)
        self.assertEqual(lookup_casstype('DecimalType'), cassandra.cqltypes.DecimalType)
        self.assertEqual(lookup_casstype('DoubleType'), cassandra.cqltypes.DoubleType)
        self.assertEqual(lookup_casstype('FloatType'), cassandra.cqltypes.FloatType)
        self.assertEqual(lookup_casstype('InetAddressType'), cassandra.cqltypes.InetAddressType)
        self.assertEqual(lookup_casstype('Int32Type'), cassandra.cqltypes.Int32Type)
        self.assertEqual(lookup_casstype('UTF8Type'), cassandra.cqltypes.UTF8Type)
        self.assertEqual(lookup_casstype('DateType'), cassandra.cqltypes.DateType)
        self.assertEqual(lookup_casstype('TimeUUIDType'), cassandra.cqltypes.TimeUUIDType)
        self.assertEqual(lookup_casstype('UUIDType'), cassandra.cqltypes.UUIDType)
        self.assertEqual(lookup_casstype('IntegerType'), cassandra.cqltypes.IntegerType)
        self.assertEqual(lookup_casstype('MapType'), cassandra.cqltypes.MapType)
        self.assertEqual(lookup_casstype('ListType'), cassandra.cqltypes.ListType)
        self.assertEqual(lookup_casstype('SetType'), cassandra.cqltypes.SetType)
        self.assertEqual(lookup_casstype('CompositeType'), cassandra.cqltypes.CompositeType)
        self.assertEqual(lookup_casstype('ColumnToCollectionType'), cassandra.cqltypes.ColumnToCollectionType)
        self.assertEqual(lookup_casstype('ReversedType'), cassandra.cqltypes.ReversedType)

        self.assertEqual(str(lookup_casstype('unknown')), str(cassandra.cqltypes.mkUnrecognizedType('unknown')))

        self.assertRaises(ValueError, lookup_casstype, 'AsciiType~')

        # TODO: Do a few more tests
        # "I would say some parameterized and nested types would be good to test,
        # like "MapType(AsciiType, IntegerType)" and "ReversedType(AsciiType)"
        self.assertEqual(str(lookup_casstype(BooleanType(True))), str(BooleanType(True)))

    def test_cassandratype(self):
        """
        Smoke test cass_parameterized_type_with
        """

        self.assertEqual(LongType.cass_parameterized_type_with(()), 'LongType')
        self.assertEqual(LongType.cass_parameterized_type_with((), full=True), 'org.apache.cassandra.db.marshal.LongType')
        self.assertEqual(SetType.cass_parameterized_type_with([DecimalType], full=True), 'org.apache.cassandra.db.marshal.SetType(org.apache.cassandra.db.marshal.DecimalType)')

        self.assertEqual(LongType.cql_parameterized_type(), 'bigint')

        subtypes = (cassandra.cqltypes.UTF8Type, cassandra.cqltypes.UTF8Type)
        self.assertEqual(
                'map<text, text>',
                cassandra.cqltypes.MapType.apply_parameters(subtypes).cql_parameterized_type())

    def test_datetype(self):
        """
        Test cassandra.cqltypes.DateType() construction
        """

        # Ensure all formats can be parsed, without exception
        for format in cassandra.cqltypes.cql_time_formats:
            date_string = str(datetime.datetime.now().strftime(format))
            cassandra.cqltypes.DateType(date_string)

    def test_cql_typename(self):
        """
        Smoke test cql_typename
        """

        self.assertEqual(cql_typename('DateType'), 'timestamp')
        self.assertEqual(cql_typename('org.apache.cassandra.db.marshal.ListType(IntegerType)'), 'list<varint>')

    def test_named_tuple_colname_substitution(self):
        colnames = ("func(abc)", "[applied]", "func(func(abc))", "foo_bar", "foo_bar_")
        rows = [(1, 2, 3, 4, 5)]
        result = named_tuple_factory(colnames, rows)[0]
        self.assertEqual(result[0], result.func_abc)
        self.assertEqual(result[1], result.applied)
        self.assertEqual(result[2], result.func_func_abc)
        self.assertEqual(result[3], result.foo_bar)
        self.assertEqual(result[4], result.foo_bar_)

    def test_parse_casstype_args(self):
        class FooType(CassandraType):
            typename = 'org.apache.cassandra.db.marshal.FooType'

            def __init__(self, subtypes, names):
                self.subtypes = subtypes
                self.names = names

            @classmethod
            def apply_parameters(cls, subtypes, names):
                return cls(subtypes, [unhexlify(name) if name is not None else name for name in names])

        class BarType(FooType):
            typename = 'org.apache.cassandra.db.marshal.BarType'

        ctype = parse_casstype_args(''.join((
            'org.apache.cassandra.db.marshal.FooType(',
                '63697479:org.apache.cassandra.db.marshal.UTF8Type,',
                'BarType(61646472657373:org.apache.cassandra.db.marshal.UTF8Type),',
                '7a6970:org.apache.cassandra.db.marshal.UTF8Type',
            ')')))

        self.assertEqual(FooType, ctype.__class__)

        self.assertEqual(UTF8Type, ctype.subtypes[0])

        # middle subtype should be a BarType instance with its own subtypes and names
        self.assertIsInstance(ctype.subtypes[1], BarType)
        self.assertEqual([UTF8Type], ctype.subtypes[1].subtypes)
        self.assertEqual([b"address"], ctype.subtypes[1].names)

        self.assertEqual(UTF8Type, ctype.subtypes[2])
        self.assertEqual([b'city', None, b'zip'], ctype.names)

    def test_empty_value(self):
        self.assertEqual(str(EmptyValue()), 'EMPTY')

    def test_CassandraType(self):
        cassandra_type = _CassandraType('randomvaluetocheck')
        self.assertEqual(cassandra_type.val, 'randomvaluetocheck')
        self.assertEqual(cassandra_type.validate('randomvaluetocheck2'), 'randomvaluetocheck2')
        self.assertEqual(cassandra_type.val, 'randomvaluetocheck')

    def test_DateType(self):
        now = datetime.datetime.now()
        date_type = DateType(now)
        self.assertEqual(date_type.my_timestamp(), now)
        self.assertRaises(ValueError, date_type.interpret_datestring, 'fakestring')

    def test_write_read_string(self):
        with tempfile.TemporaryFile() as f:
            value = u'test'
            write_string(f, value)
            f.seek(0)
            self.assertEqual(read_string(f), value)

    def test_write_read_longstring(self):
        with tempfile.TemporaryFile() as f:
            value = u'test'
            write_longstring(f, value)
            f.seek(0)
            self.assertEqual(read_longstring(f), value)

    def test_write_read_stringmap(self):
        with tempfile.TemporaryFile() as f:
            value = {'key': 'value'}
            write_stringmap(f, value)
            f.seek(0)
            self.assertEqual(read_stringmap(f), value)

    def test_write_read_inet(self):
        with tempfile.TemporaryFile() as f:
            value = ('192.168.1.1', 9042)
            write_inet(f, value)
            f.seek(0)
            self.assertEqual(read_inet(f), value)

        with tempfile.TemporaryFile() as f:
            value = ('2001:db8:0:f101::1', 9042)
            write_inet(f, value)
            f.seek(0)
            self.assertEqual(read_inet(f), value)

    def test_cql_quote(self):
        self.assertEqual(cql_quote(u'test'), "'test'")
        self.assertEqual(cql_quote('test'), "'test'")
        self.assertEqual(cql_quote(0), '0')

########NEW FILE########
