__FILENAME__ = connection_pool
import time
import random
import logging

try:
    from Queue import PriorityQueue, Empty
except ImportError:
    from queue import PriorityQueue, Empty

logger = logging.getLogger('elasticsearch')


class ConnectionSelector(object):
    """
    Simple class used to select a connection from a list of currently live
    connection instances. In init time it is passed a dictionary containing all
    the connections' options which it can then use during the selection
    process. When the `select` method is called it is given a list of
    *currently* live connections to choose from.

    The options dictionary is the one that has been passed to
    :class:`~elasticsearch.Transport` as `hosts` param and the same that is
    used to construct the Connection object itself. When the Connection was
    created from information retrieved from the cluster via the sniffing
    process it will be the dictionary returned by the `host_info_callback`.

    Example of where this would be useful is a zone-aware selector that would
    only select connections from it's own zones and only fall back to other
    connections where there would be none in it's zones.
    """
    def __init__(self, opts):
        """
        :arg opts: dictionary of connection instances and their options
        """
        self.connection_opts = opts

    def select(self, connections):
        """
        Select a connection from the given list.

        :arg connections: list of live connections to choose from
        """
        pass


class RandomSelector(ConnectionSelector):
    """
    Select a connection at random
    """
    def select(self, connections):
        return random.choice(connections)


class RoundRobinSelector(ConnectionSelector):
    """
    Selector using round-robin.
    """
    def __init__(self, opts):
        super(RoundRobinSelector, self).__init__(opts)
        self.rr = -1

    def select(self, connections):
        self.rr += 1
        self.rr %= len(connections)
        return connections[self.rr]


class ConnectionPool(object):
    """
    Container holding the :class:`~elasticsearch.Connection` instances,
    managing the selection process (via a
    :class:`~elasticsearch.ConnectionSelector`) and dead connections.

    It's only interactions are with the :class:`~elasticsearch.Transport` class
    that drives all the actions within `ConnectionPool`.

    Initially connections are stored on the class as a list and, along with the
    connection options, get passed to the `ConnectionSelector` instance for
    future reference.

    Upon each request the `Transport` will ask for a `Connection` via the
    `get_connection` method. If the connection fails (it's `perform_request`
    raises a `ConnectionError`) it will be marked as dead (via `mark_dead`) and
    put on a timeout (if it fails N times in a row the timeout is exponentially
    longer - the formula is `default_timeout * 2 ** (fail_count - 1)`). When
    the timeout is over the connection will be resurrected and returned to the
    live pool. A connection that has been peviously marked as dead and
    succeedes will be marked as live (it's fail count will be deleted).
    """
    def __init__(self, connections, dead_timeout=60, timeout_cutoff=5,
        selector_class=RoundRobinSelector, randomize_hosts=True, **kwargs):
        """
        :arg connections: list of tuples containing the
            :class:`~elasticsearch.Connection` instance and it's options
        :arg dead_timeout: number of seconds a connection should be retired for
            after a failure, increases on consecutive failures
        :arg timeout_cutoff: number of consecutive failures after which the
            timeout doesn't increase
        :arg selector_class: :class:`~elasticsearch.ConnectionSelector`
            subclass to use
        :arg randomize_hosts: shuffle the list of connections upon arrival to
            avoid dog piling effect across processes
        """
        self.connection_opts = connections
        self.connections = [c for (c, opts) in connections]
        # PriorityQueue for thread safety and ease of timeout management
        self.dead = PriorityQueue(len(self.connections))
        self.dead_count = {}

        if randomize_hosts:
            # randomize the connection list to avoid all clients hitting same
            # node after startup/restart
            random.shuffle(self.connections)

        # default timeout after which to try resurrecting a connection
        self.dead_timeout = dead_timeout
        self.timeout_cutoff = timeout_cutoff

        self.selector = selector_class(dict(connections))

    def mark_dead(self, connection, now=None):
        """
        Mark the connection as dead (failed). Remove it from the live pool and
        put it on a timeout.

        :arg connection: the failed instance
        """
        # allow inject for testing purposes
        now = now if now else time.time()
        try:
            self.connections.remove(connection)
        except ValueError:
            # connection not alive or another thread marked it already, ignore
            return
        else:
            dead_count = self.dead_count.get(connection, 0) + 1
            self.dead_count[connection] = dead_count
            timeout = self.dead_timeout * 2 ** min(dead_count - 1,
                                                   self.timeout_cutoff)
            self.dead.put((now + timeout, connection))
            logger.warning(
                'Connection %r has failed for %i times in a row,'
                ' putting on %i second timeout.',
                connection, dead_count, timeout
            )

    def mark_live(self, connection):
        """
        Mark connection as healthy after a resurrection. Resets the fail
        counter for the connection.

        :arg connection: the connection to redeem
        """
        try:
            del self.dead_count[connection]
        except KeyError:
            # race condition, safe to ignore
            pass

    def resurrect(self, force=False):
        """
        Attempt to resurrect a connection from the dead pool. It will try to
        locate one (not all) eligible (it's timeout is over) connection to
        return to th live pool.

        :arg force: resurrect a connection even if there is none eligible (used
            when we have no live connections)

        """
        # no dead connections
        if self.dead.empty():
            return

        try:
            # retrieve a connection to check
            timeout, connection = self.dead.get(block=False)
        except Empty:
            # other thread has been faster and the queue is now empty
            return

        if not force and timeout > time.time():
            # return it back if not eligible and not forced
            self.dead.put((timeout, connection))
            return

        # either we were forced or the connection is elligible to be retried
        self.connections.append(connection)
        logger.info('Resurrecting connection %r (force=%s).', connection, force)

    def get_connection(self):
        """
        Return a connection from the pool using the `ConnectionSelector`
        instance.

        It tries to resurrect eligible connections, forces a resurrection when
        no connections are availible and passes the list of live connections to
        the selector instance to choose from.

        Returns a connection instance and it's current fail count.
        """
        self.resurrect()

        # no live nodes, resurrect one by force
        if not self.connections:
            self.resurrect(True)
        connection = self.selector.select(self.connections)

        return connection

########NEW FILE########
__FILENAME__ = elastic
#
#   Copyright 2012 The HumanGeo Group, LLC
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
#

import sys

from .connection_pool import ConnectionPool
from .encoders import encode_date_optional_time
from .http_connection import HttpConnection
from .utils import isstr
try:
    import simplejson as json
except ImportError:
    import json  # noqa

if sys.version_info[0] > 2:
    import urllib.parse as urlparse
else:
    import urlparse


class Elastic(object):
    """Connect to an elasticsearch instance"""

    def __init__(self, url='localhost:9200', path='', timeout=30,
                 json_encoder=encode_date_optional_time,
                 connection_pool=None,
                 connection_pool_kwargs={},
                 **kwargs):
        """Constructs an :class:`Elastic <Elastic>`, client object.
        Returns :class:`Elastic <Elastic>` object.

        :param url: (optional) URL for the host the client will conenct to.
            A list of URL's can be provided if you want to use a connection
            pool for your requests. Each new call will use a different host
            from the conenction pool. If you don't provide any arguments to
            this constructor then the default url will be used.
        :param path: (optional) elasticserach api path you want to make the
            call to.
        :param timeout: (optional) an integer specifying the number of seconds
            to wait before timing out a call
        :param json_encoder: (optional) customize the way you encode data sent
            over to elasticsearch
        :param connection_pool: (optional) if you have a connection pool object
            that you want to reuse you can pass it in here; in this case, the
            url value will be ignored
        :param connection_pool_kwargs: (optional) a dictionary of arguments to
            be passed to the connection pool in order to expose its options
            directly to the rawes constructor
        """

        super(Elastic, self).__init__()

        if not isinstance(url, list) and not isstr(url):
            raise ValueError('Url provided is not of right type')

        # Clean up url of any path items
        if isstr(url):
            decoded_url = self._decode_url(url, '')
            path = self._build_path(decoded_url.path, path)
            url = decoded_url.netloc
            if decoded_url.scheme:
                url = '{0}://{1}'.format(decoded_url.scheme, url)

        if connection_pool is None:
            urls = [url] if isstr(url) else url
            # Validate all urls are of correct format host:port
            for host_url in urls:
                if '//' not in host_url:
                    host_url = '//' + host_url
                if urlparse.urlsplit(host_url).path not in ['', '/']:
                    raise ValueError('Url paths not allowed in hosts list')
            connections = [(self._get_connection_from_url(host_url, timeout,
                        **kwargs), {}) for host_url in urls]
            connection_pool = ConnectionPool(connections,
                            **connection_pool_kwargs)

        self.path = path
        self.timeout = timeout  # seconds
        self.json_encoder = json_encoder
        self.connection_pool = connection_pool

    def put(self, path='', **kwargs):
        return self.request('put', path, **kwargs)

    def get(self, path='', **kwargs):
        return self.request('get', path, **kwargs)

    def post(self, path='', **kwargs):
        return self.request('post', path, **kwargs)

    def delete(self, path='', **kwargs):
        return self.request('delete', path, **kwargs)

    def head(self, path='', **kwargs):
        return self.request('head', path, **kwargs)

    def request(self, method, path, **kwargs):
        new_path = self._build_path(self.path, path)

        # Look for a custom json encoder
        if 'json_encoder' in kwargs:
            json_encoder = kwargs['json_encoder']
            del kwargs['json_encoder']
        else:
            json_encoder = self.json_encoder

        # Encode data dict to json if necessary
        if 'data' in kwargs and type(kwargs['data']) == dict:
            kwargs['data'] = json.dumps(kwargs['data'], default=json_encoder)

        # Always select a connection from the pool for each new request
        return self.connection_pool.get_connection().request(
                                                    method, new_path, **kwargs)

    def __getattr__(self, path_item):
        return self.__getitem__(path_item)

    def __getitem__(self, path_item):
        new_path = self._build_path(self.path, path_item)
        return Elastic(
            timeout=self.timeout,
            path=new_path,
            connection_pool=self.connection_pool
        )

    def _build_path(self, base_path, path_item):
        new_path = '/'.join((str(base_path), str(path_item))) if base_path != '' else str(path_item)
        # Clean up path of any extraneous forward slashes
        return new_path.strip("/")

    def _decode_url(self, url, path):
        # Make sure urlsplit() doesn't choke on scheme-less URLs, like 'localhost:9200'
        if '//' not in url:
            url = '//' + url

        url = urlparse.urlsplit(url)
        if not url.netloc:
            raise ValueError('Could not parse the given URL.')

        # If the scheme isn't explicitly provided by now, try to deduce it
        # from the port number
        scheme = url.scheme
        if not scheme:
            if 9500 <= url.port <= 9600:
                scheme = 'thrift'
            else:
                scheme = 'http'

        # Use path if provided
        if not path:
            path = url.path

        # Set default ports
        netloc = url.netloc
        if not url.port:
            if url.scheme == 'http':
                netloc = "{0}:{1}".format(netloc, 9200)
            elif url.scheme == 'https':
                netloc = "{0}:{1}".format(netloc, 443)
            elif url.scheme == 'thrift':
                netloc = "{0}:{1}".format(netloc, 9500)

        # Return new url.
        return urlparse.SplitResult(scheme=scheme, netloc=netloc, path=path,
                                    query='', fragment='')

    def _get_connection_from_url(self, url, timeout, **kwargs):
        """Returns a connection object given a string url"""

        url = self._decode_url(url, "")

        if url.scheme == 'http' or url.scheme == 'https':
            return HttpConnection(url.geturl(), timeout=timeout, **kwargs)
        else:
            if sys.version_info[0] > 2:
                raise ValueError("Thrift transport is not available "
                                 "for Python 3")

            try:
                from thrift_connection import ThriftConnection
            except ImportError:
                raise ImportError("The 'thrift' python package "
                                    "does not seem to be installed.")
            return ThriftConnection(url.hostname, url.port,
                                    timeout=timeout, **kwargs)


########NEW FILE########
__FILENAME__ = elastic_exception
#
#   Copyright 2012 The HumanGeo Group, LLC
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
#

class ElasticException(Exception):
    def __init__(self, message, result, status_code):
        super(ElasticException, self).__init__(self, message)
        self.result = result
        self.status_code = status_code

########NEW FILE########
__FILENAME__ = encoders
#
#   Copyright 2012 The HumanGeo Group, LLC
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
#

import datetime
from pytz import timezone

def encode_date_optional_time(obj):
    """
    ISO encode timezone-aware datetimes
    """
    if isinstance(obj, datetime.datetime):
        return timezone("UTC").normalize(obj.astimezone(timezone("UTC"))).strftime('%Y-%m-%dT%H:%M:%SZ')
    raise TypeError("{0} is not JSON serializable".format(repr(obj)))

########NEW FILE########
__FILENAME__ = http_connection
#
#   Copyright 2012 The HumanGeo Group, LLC
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
#

try:
    import simplejson as json
except ImportError:
    import json  # noqa

import requests
from .elastic_exception import ElasticException


class HttpConnection(object):
    """Connects to elasticsearch over HTTP"""
    def __init__(self, url, timeout=None, **kwargs):
        super(HttpConnection, self).__init__()
        self.protocol = 'http'
        self.url = url
        self.timeout = timeout
        self.kwargs = kwargs
        self.session = requests.session()

    def request(self, method, path, **kwargs):
        args = self.kwargs.copy()
        args.update(kwargs)

        if "json_decoder" in args:
            json_decoder = args["json_decoder"]
            del args["json_decoder"]
        else:
            json_decoder = json.loads

        if 'timeout' not in args:
            args['timeout'] = self.timeout
        response = self.session.request(method,
                                        "/".join((self.url, path)), **args)
        return self._decode(response, json_decoder)

    def _decode(self, response, json_decoder):
        if not response.text:
            decoded = response.status_code < 300
        else:
            try:
                decoded = json_decoder(response.text)
            except ValueError:
                decoded = False

        if response.status_code >= 400:
            raise ElasticException(
                    message="ElasticSearch Error: {0}".format(response.text),
                    result=decoded, status_code=response.status_code)
        return decoded

########NEW FILE########
__FILENAME__ = thrift_connection
#
#   Copyright 2012 The HumanGeo Group, LLC
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
#

try:
    import simplejson as json
except ImportError:
    import json  # noqa

from thrift.transport import TSocket
from thrift.transport import TTransport
from thrift.protocol import TBinaryProtocol

from rawes.thrift_elasticsearch import Rest
from rawes.thrift_elasticsearch.ttypes import Method, RestRequest

from elastic_exception import ElasticException


class ThriftConnection(object):
    """Connects to elasticsearch over thrift protocol"""
    def __init__(self, host, port, timeout=None, **kwargs):
        self.protocol = 'thrift'
        self.host = host
        self.port = port
        tsocket = TSocket.TSocket(self.host, self.port)
        if timeout is not None:
            tsocket.setTimeout(timeout * 1000)  # thrift expects ms
        transport = TTransport.TBufferedTransport(tsocket)
        protocol = TBinaryProtocol.TBinaryProtocol(transport)
        self.client = Rest.Client(protocol)
        transport.open()
        self.kwargs = kwargs

    method_mappings = {
        'get': Method.GET,
        'post': Method.POST,
        'put': Method.PUT,
        'delete': Method.DELETE,
        'head': Method.HEAD
    }

    def request(self, method, path, **kwargs):
        newkwargs = self.kwargs.copy()
        newkwargs.update(kwargs)
        thriftargs = {}

        if "json_decoder" in newkwargs:
            json_decoder = newkwargs["json_decoder"]
        else:
            json_decoder = json.loads

        if 'data' in newkwargs:
            thriftargs['body'] = newkwargs['data']

        if 'params' in newkwargs:
            thriftargs['parameters'] = self._dict_to_map_str_str(newkwargs['params'])

        if 'headers' in newkwargs:
            thriftargs['headers'] = self._dict_to_map_str_str(newkwargs['headers'])

        mapped_method = ThriftConnection.method_mappings[method]
        request = RestRequest(method=mapped_method, uri=path, **thriftargs)
        response = self.client.execute(request)

        return self._decode(response, json_decoder)

    def _decode(self, response, json_decoder):
        if not response.body:
            decoded = response.status < 300
        else:
            try:
                decoded = json_decoder(response.body)
            except ValueError:
                decoded = False

        if response.status >= 400:
            raise ElasticException(message="ElasticSearch Error: %r" % response.body,
                                   result=decoded, status_code=response.status)
        return decoded

    def _dict_to_map_str_str(self, d):
        """
        Thrift requires the params and headers dict values to only contain str values.
        """
        return dict(map(
            lambda (k, v): (k, str(v).lower() if isinstance(v, bool) else str(v)),
            d.iteritems()
        ))

########NEW FILE########
__FILENAME__ = constants
#
# Autogenerated by Thrift Compiler (0.8.0)
#
# DO NOT EDIT UNLESS YOU ARE SURE THAT YOU KNOW WHAT YOU ARE DOING
#
#  options string: py
#

from thrift.Thrift import TType, TMessageType, TException
from ttypes import *

########NEW FILE########
__FILENAME__ = Rest
#
# Autogenerated by Thrift Compiler (0.8.0)
#
# DO NOT EDIT UNLESS YOU ARE SURE THAT YOU KNOW WHAT YOU ARE DOING
#
#  options string: py
#

from thrift.Thrift import TType, TMessageType, TException, TApplicationException
from ttypes import *
from thrift.Thrift import TProcessor
from thrift.transport import TTransport
from thrift.protocol import TBinaryProtocol, TProtocol

try:
    from thrift.protocol import fastbinary
except:
    fastbinary = None


class Iface:

    def execute(self, request):
        """
        Parameters:
        - request
        """
        pass


class Client(Iface):

    def __init__(self, iprot, oprot=None):
        self._iprot = self._oprot = iprot
        if oprot is not None:
            self._oprot = oprot
        self._seqid = 0

    def execute(self, request):
        """
        Parameters:
        - request
        """
        self.send_execute(request)
        return self.recv_execute()

    def send_execute(self, request):
        self._oprot.writeMessageBegin('execute', TMessageType.CALL, self._seqid)
        args = execute_args()
        args.request = request
        args.write(self._oprot)
        self._oprot.writeMessageEnd()
        self._oprot.trans.flush()

    def recv_execute(self, ):
        (fname, mtype, rseqid) = self._iprot.readMessageBegin()
        if mtype == TMessageType.EXCEPTION:
            x = TApplicationException()
            x.read(self._iprot)
            self._iprot.readMessageEnd()
            raise x
        result = execute_result()
        result.read(self._iprot)
        self._iprot.readMessageEnd()
        if result.success is not None:
            return result.success
        raise TApplicationException(TApplicationException.MISSING_RESULT, "execute failed: unknown result")


class Processor(Iface, TProcessor):

    def __init__(self, handler):
        self._handler = handler
        self._processMap = {}
        self._processMap["execute"] = Processor.process_execute

    def process(self, iprot, oprot):
        (name, type, seqid) = iprot.readMessageBegin()
        if name not in self._processMap:
            iprot.skip(TType.STRUCT)
            iprot.readMessageEnd()
            x = TApplicationException(TApplicationException.UNKNOWN_METHOD, 'Unknown function %s' % (name))
            oprot.writeMessageBegin(name, TMessageType.EXCEPTION, seqid)
            x.write(oprot)
            oprot.writeMessageEnd()
            oprot.trans.flush()
            return
        else:
            self._processMap[name](self, seqid, iprot, oprot)
        return True

    def process_execute(self, seqid, iprot, oprot):
        args = execute_args()
        args.read(iprot)
        iprot.readMessageEnd()
        result = execute_result()
        result.success = self._handler.execute(args.request)
        oprot.writeMessageBegin("execute", TMessageType.REPLY, seqid)
        result.write(oprot)
        oprot.writeMessageEnd()
        oprot.trans.flush()

# HELPER FUNCTIONS AND STRUCTURES


class execute_args:
    """
    Attributes:
    - request
    """

    thrift_spec = (
        None,  # 0
        (1, TType.STRUCT, 'request', (RestRequest, RestRequest.thrift_spec), None, ),  # 1
    )

    def __init__(self, request=None):
        self.request = request

    def read(self, iprot):
        if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
            fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
            return
        iprot.readStructBegin()
        while True:
            (fname, ftype, fid) = iprot.readFieldBegin()
            if ftype == TType.STOP:
                break
            if fid == 1:
                if ftype == TType.STRUCT:
                    self.request = RestRequest()
                    self.request.read(iprot)
                else:
                    iprot.skip(ftype)
            else:
                iprot.skip(ftype)
            iprot.readFieldEnd()
        iprot.readStructEnd()

    def write(self, oprot):
        if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
            oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
            return
        oprot.writeStructBegin('execute_args')
        if self.request is not None:
            oprot.writeFieldBegin('request', TType.STRUCT, 1)
            self.request.write(oprot)
            oprot.writeFieldEnd()
        oprot.writeFieldStop()
        oprot.writeStructEnd()

    def validate(self):
        if self.request is None:
            raise TProtocol.TProtocolException(message='Required field request is unset!')
        return

    def __repr__(self):
        L = ['%s=%r' % (key, value)
             for key, value in self.__dict__.iteritems()]
        return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

    def __eq__(self, other):
        return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

    def __ne__(self, other):
        return not (self == other)


class execute_result:
    """
    Attributes:
    - success
    """

    thrift_spec = (
        (0, TType.STRUCT, 'success', (RestResponse, RestResponse.thrift_spec), None, ),  # 0
    )

    def __init__(self, success=None,):
        self.success = success

    def read(self, iprot):
        if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
            fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
            return
        iprot.readStructBegin()
        while True:
            (fname, ftype, fid) = iprot.readFieldBegin()
            if ftype == TType.STOP:
                break
            if fid == 0:
                if ftype == TType.STRUCT:
                    self.success = RestResponse()
                    self.success.read(iprot)
                else:
                    iprot.skip(ftype)
            else:
                iprot.skip(ftype)
            iprot.readFieldEnd()
        iprot.readStructEnd()

    def write(self, oprot):
        if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
            oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
            return
        oprot.writeStructBegin('execute_result')
        if self.success is not None:
            oprot.writeFieldBegin('success', TType.STRUCT, 0)
            self.success.write(oprot)
            oprot.writeFieldEnd()
        oprot.writeFieldStop()
        oprot.writeStructEnd()

    def validate(self):
        return

    def __repr__(self):
        L = ['%s=%r' % (key, value)
             for key, value in self.__dict__.iteritems()]
        return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

    def __eq__(self, other):
        return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

    def __ne__(self, other):
        return not (self == other)

########NEW FILE########
__FILENAME__ = ttypes
#
# Autogenerated by Thrift Compiler (0.8.0)
#
# DO NOT EDIT UNLESS YOU ARE SURE THAT YOU KNOW WHAT YOU ARE DOING
#
#  options string: py
#

from thrift.Thrift import TType, TMessageType, TException
from thrift.transport import TTransport
from thrift.protocol import TBinaryProtocol, TProtocol

try:
    from thrift.protocol import fastbinary
except:
    fastbinary = None


class Method:
    GET = 0
    PUT = 1
    POST = 2
    DELETE = 3
    HEAD = 4
    OPTIONS = 5

    _VALUES_TO_NAMES = {
        0: "GET",
        1: "PUT",
        2: "POST",
        3: "DELETE",
        4: "HEAD",
        5: "OPTIONS",
    }

    _NAMES_TO_VALUES = {
        "GET": 0,
        "PUT": 1,
        "POST": 2,
        "DELETE": 3,
        "HEAD": 4,
        "OPTIONS": 5,
    }


class Status:
    CONT = 100
    SWITCHING_PROTOCOLS = 101
    OK = 200
    CREATED = 201
    ACCEPTED = 202
    NON_AUTHORITATIVE_INFORMATION = 203
    NO_CONTENT = 204
    RESET_CONTENT = 205
    PARTIAL_CONTENT = 206
    MULTI_STATUS = 207
    MULTIPLE_CHOICES = 300
    MOVED_PERMANENTLY = 301
    FOUND = 302
    SEE_OTHER = 303
    NOT_MODIFIED = 304
    USE_PROXY = 305
    TEMPORARY_REDIRECT = 307
    BAD_REQUEST = 400
    UNAUTHORIZED = 401
    PAYMENT_REQUIRED = 402
    FORBIDDEN = 403
    NOT_FOUND = 404
    METHOD_NOT_ALLOWED = 405
    NOT_ACCEPTABLE = 406
    PROXY_AUTHENTICATION = 407
    REQUEST_TIMEOUT = 408
    CONFLICT = 409
    GONE = 410
    LENGTH_REQUIRED = 411
    PRECONDITION_FAILED = 412
    REQUEST_ENTITY_TOO_LARGE = 413
    REQUEST_URI_TOO_LONG = 414
    UNSUPPORTED_MEDIA_TYPE = 415
    REQUESTED_RANGE_NOT_SATISFIED = 416
    EXPECTATION_FAILED = 417
    UNPROCESSABLE_ENTITY = 422
    LOCKED = 423
    FAILED_DEPENDENCY = 424
    INTERNAL_SERVER_ERROR = 500
    NOT_IMPLEMENTED = 501
    BAD_GATEWAY = 502
    SERVICE_UNAVAILABLE = 503
    GATEWAY_TIMEOUT = 504
    INSUFFICIENT_STORAGE = 506

    _VALUES_TO_NAMES = {
        100: "CONT",
        101: "SWITCHING_PROTOCOLS",
        200: "OK",
        201: "CREATED",
        202: "ACCEPTED",
        203: "NON_AUTHORITATIVE_INFORMATION",
        204: "NO_CONTENT",
        205: "RESET_CONTENT",
        206: "PARTIAL_CONTENT",
        207: "MULTI_STATUS",
        300: "MULTIPLE_CHOICES",
        301: "MOVED_PERMANENTLY",
        302: "FOUND",
        303: "SEE_OTHER",
        304: "NOT_MODIFIED",
        305: "USE_PROXY",
        307: "TEMPORARY_REDIRECT",
        400: "BAD_REQUEST",
        401: "UNAUTHORIZED",
        402: "PAYMENT_REQUIRED",
        403: "FORBIDDEN",
        404: "NOT_FOUND",
        405: "METHOD_NOT_ALLOWED",
        406: "NOT_ACCEPTABLE",
        407: "PROXY_AUTHENTICATION",
        408: "REQUEST_TIMEOUT",
        409: "CONFLICT",
        410: "GONE",
        411: "LENGTH_REQUIRED",
        412: "PRECONDITION_FAILED",
        413: "REQUEST_ENTITY_TOO_LARGE",
        414: "REQUEST_URI_TOO_LONG",
        415: "UNSUPPORTED_MEDIA_TYPE",
        416: "REQUESTED_RANGE_NOT_SATISFIED",
        417: "EXPECTATION_FAILED",
        422: "UNPROCESSABLE_ENTITY",
        423: "LOCKED",
        424: "FAILED_DEPENDENCY",
        500: "INTERNAL_SERVER_ERROR",
        501: "NOT_IMPLEMENTED",
        502: "BAD_GATEWAY",
        503: "SERVICE_UNAVAILABLE",
        504: "GATEWAY_TIMEOUT",
        506: "INSUFFICIENT_STORAGE",
    }

    _NAMES_TO_VALUES = {
        "CONT": 100,
        "SWITCHING_PROTOCOLS": 101,
        "OK": 200,
        "CREATED": 201,
        "ACCEPTED": 202,
        "NON_AUTHORITATIVE_INFORMATION": 203,
        "NO_CONTENT": 204,
        "RESET_CONTENT": 205,
        "PARTIAL_CONTENT": 206,
        "MULTI_STATUS": 207,
        "MULTIPLE_CHOICES": 300,
        "MOVED_PERMANENTLY": 301,
        "FOUND": 302,
        "SEE_OTHER": 303,
        "NOT_MODIFIED": 304,
        "USE_PROXY": 305,
        "TEMPORARY_REDIRECT": 307,
        "BAD_REQUEST": 400,
        "UNAUTHORIZED": 401,
        "PAYMENT_REQUIRED": 402,
        "FORBIDDEN": 403,
        "NOT_FOUND": 404,
        "METHOD_NOT_ALLOWED": 405,
        "NOT_ACCEPTABLE": 406,
        "PROXY_AUTHENTICATION": 407,
        "REQUEST_TIMEOUT": 408,
        "CONFLICT": 409,
        "GONE": 410,
        "LENGTH_REQUIRED": 411,
        "PRECONDITION_FAILED": 412,
        "REQUEST_ENTITY_TOO_LARGE": 413,
        "REQUEST_URI_TOO_LONG": 414,
        "UNSUPPORTED_MEDIA_TYPE": 415,
        "REQUESTED_RANGE_NOT_SATISFIED": 416,
        "EXPECTATION_FAILED": 417,
        "UNPROCESSABLE_ENTITY": 422,
        "LOCKED": 423,
        "FAILED_DEPENDENCY": 424,
        "INTERNAL_SERVER_ERROR": 500,
        "NOT_IMPLEMENTED": 501,
        "BAD_GATEWAY": 502,
        "SERVICE_UNAVAILABLE": 503,
        "GATEWAY_TIMEOUT": 504,
        "INSUFFICIENT_STORAGE": 506,
    }


class RestRequest:
    """
    Attributes:
    - method
    - uri
    - parameters
    - headers
    - body
    """

    thrift_spec = (
        None,  # 0
        (1, TType.I32, 'method', None, None, ),  # 1
        (2, TType.STRING, 'uri', None, None, ),  # 2
        (3, TType.MAP, 'parameters', (TType.STRING, None, TType.STRING, None), None, ),  # 3
        (4, TType.MAP, 'headers', (TType.STRING, None, TType.STRING, None), None, ),  # 4
        (5, TType.STRING, 'body', None, None, ),  # 5
    )

    def __init__(self, method=None, uri=None, parameters=None, headers=None, body=None,):
        self.method = method
        self.uri = uri
        self.parameters = parameters
        self.headers = headers
        self.body = body

    def read(self, iprot):
        if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
            fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
            return
        iprot.readStructBegin()
        while True:
            (fname, ftype, fid) = iprot.readFieldBegin()
            if ftype == TType.STOP:
                break
            if fid == 1:
                if ftype == TType.I32:
                    self.method = iprot.readI32()
                else:
                    iprot.skip(ftype)
            elif fid == 2:
                if ftype == TType.STRING:
                    self.uri = iprot.readString()
                else:
                    iprot.skip(ftype)
            elif fid == 3:
                if ftype == TType.MAP:
                    self.parameters = {}
                    (_ktype1, _vtype2, _size0) = iprot.readMapBegin()
                    for _i4 in xrange(_size0):
                        _key5 = iprot.readString()
                        _val6 = iprot.readString()
                        self.parameters[_key5] = _val6
                    iprot.readMapEnd()
                else:
                    iprot.skip(ftype)
            elif fid == 4:
                if ftype == TType.MAP:
                    self.headers = {}
                    (_ktype8, _vtype9, _size7) = iprot.readMapBegin()
                    for _i11 in xrange(_size7):
                        _key12 = iprot.readString()
                        _val13 = iprot.readString()
                        self.headers[_key12] = _val13
                    iprot.readMapEnd()
                else:
                    iprot.skip(ftype)
            elif fid == 5:
                if ftype == TType.STRING:
                    self.body = iprot.readString()
                else:
                    iprot.skip(ftype)
            else:
                iprot.skip(ftype)
            iprot.readFieldEnd()
        iprot.readStructEnd()

    def write(self, oprot):
        if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
            oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
            return
        oprot.writeStructBegin('RestRequest')
        if self.method is not None:
            oprot.writeFieldBegin('method', TType.I32, 1)
            oprot.writeI32(self.method)
            oprot.writeFieldEnd()
        if self.uri is not None:
            oprot.writeFieldBegin('uri', TType.STRING, 2)
            oprot.writeString(self.uri)
            oprot.writeFieldEnd()
        if self.parameters is not None:
            oprot.writeFieldBegin('parameters', TType.MAP, 3)
            oprot.writeMapBegin(TType.STRING, TType.STRING, len(self.parameters))
            for kiter14, viter15 in self.parameters.items():
                oprot.writeString(kiter14)
                oprot.writeString(viter15)
            oprot.writeMapEnd()
            oprot.writeFieldEnd()
        if self.headers is not None:
            oprot.writeFieldBegin('headers', TType.MAP, 4)
            oprot.writeMapBegin(TType.STRING, TType.STRING, len(self.headers))
            for kiter16, viter17 in self.headers.items():
                oprot.writeString(kiter16)
                oprot.writeString(viter17)
            oprot.writeMapEnd()
            oprot.writeFieldEnd()
        if self.body is not None:
            oprot.writeFieldBegin('body', TType.STRING, 5)
            oprot.writeString(self.body)
            oprot.writeFieldEnd()
        oprot.writeFieldStop()
        oprot.writeStructEnd()

    def validate(self):
        if self.method is None:
            raise TProtocol.TProtocolException(message='Required field method is unset!')
        if self.uri is None:
            raise TProtocol.TProtocolException(message='Required field uri is unset!')
        return

    def __repr__(self):
        L = ['%s=%r' % (key, value)
             for key, value in self.__dict__.iteritems()]
        return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

    def __eq__(self, other):
        return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

    def __ne__(self, other):
        return not (self == other)


class RestResponse:
    """
    Attributes:
    - status
    - headers
    - body
    """

    thrift_spec = (
        None,  # 0
        (1, TType.I32, 'status', None, None, ),  # 1
        (2, TType.MAP, 'headers', (TType.STRING, None, TType.STRING, None), None, ),  # 2
        (3, TType.STRING, 'body', None, None, ),  # 3
    )

    def __init__(self, status=None, headers=None, body=None,):
        self.status = status
        self.headers = headers
        self.body = body

    def read(self, iprot):
        if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
            fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
            return
        iprot.readStructBegin()
        while True:
            (fname, ftype, fid) = iprot.readFieldBegin()
            if ftype == TType.STOP:
                break
            if fid == 1:
                if ftype == TType.I32:
                    self.status = iprot.readI32()
                else:
                    iprot.skip(ftype)
            elif fid == 2:
                if ftype == TType.MAP:
                    self.headers = {}
                    (_ktype19, _vtype20, _size18) = iprot.readMapBegin()
                    for _i22 in xrange(_size18):
                        _key23 = iprot.readString()
                        _val24 = iprot.readString()
                        self.headers[_key23] = _val24
                    iprot.readMapEnd()
                else:
                    iprot.skip(ftype)
            elif fid == 3:
                if ftype == TType.STRING:
                    self.body = iprot.readString()
                else:
                    iprot.skip(ftype)
            else:
                iprot.skip(ftype)
            iprot.readFieldEnd()
        iprot.readStructEnd()

    def write(self, oprot):
        if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
            oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
            return
        oprot.writeStructBegin('RestResponse')
        if self.status is not None:
            oprot.writeFieldBegin('status', TType.I32, 1)
            oprot.writeI32(self.status)
            oprot.writeFieldEnd()
        if self.headers is not None:
            oprot.writeFieldBegin('headers', TType.MAP, 2)
            oprot.writeMapBegin(TType.STRING, TType.STRING, len(self.headers))
            for kiter25, viter26 in self.headers.items():
                oprot.writeString(kiter25)
                oprot.writeString(viter26)
            oprot.writeMapEnd()
            oprot.writeFieldEnd()
        if self.body is not None:
            oprot.writeFieldBegin('body', TType.STRING, 3)
            oprot.writeString(self.body)
            oprot.writeFieldEnd()
        oprot.writeFieldStop()
        oprot.writeStructEnd()

    def validate(self):
        if self.status is None:
            raise TProtocol.TProtocolException(message='Required field status is unset!')
        return

    def __repr__(self):
        L = ['%s=%r' % (key, value)
             for key, value in self.__dict__.iteritems()]
        return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

    def __eq__(self, other):
        return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

    def __ne__(self, other):
        return not (self == other)

########NEW FILE########
__FILENAME__ = utils
#
#   Copyright 2012 The HumanGeo Group, LLC
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
#

# python2.x and 3.x compatible way of checking if an object is a string
try:
    basestring  # attempt to evaluate basestring
    def isstr(s):
        return isinstance(s, basestring)
except NameError:
    def isstr(s):
        return isinstance(s, str)

########NEW FILE########
__FILENAME__ = config
#
#   Copyright 2012 The HumanGeo Group, LLC
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
#

ES_HOST = 'localhost'
ES_HTTP_PORT = 9200
ES_THRIFT_PORT = 9500
ES_INDEX = 'rawes_test'
ES_TYPE = 'rawes_test_type'
HTTP_ONLY=False
########NEW FILE########
__FILENAME__ = connection_pool_tests
import time

from rawes.connection_pool import ConnectionPool, RoundRobinSelector

from unittest import TestCase


class TestConnectionPool(TestCase):
    def test_default_round_robin(self):
        pool = ConnectionPool([(x, {}) for x in range(100)])

        connections = set()
        for _ in range(100):
            connections.add(pool.get_connection())
        self.assertEquals(connections, set(range(100)))

    def test_disable_shuffling(self):
        pool = ConnectionPool([(x, {}) for x in range(100)],
                              randomize_hosts=False)

        connections = []
        for _ in range(100):
            connections.append(pool.get_connection())
        self.assertEquals(connections, list(range(100)))

    def test_selectors_have_access_to_connection_opts(self):
        class MySelector(RoundRobinSelector):
            def select(self, connections):
                return self.connection_opts[
                        super(MySelector, self).select(connections)]["actual"]
        pool = ConnectionPool([(x, {"actual": x * x}) for x in range(100)],
                               selector_class=MySelector, randomize_hosts=False)

        connections = []
        for _ in range(100):
            connections.append(pool.get_connection())
        self.assertEquals(connections, [x * x for x in range(100)])

    def test_dead_nodes_are_removed_from_active_connections(self):
        pool = ConnectionPool([(x, {}) for x in range(100)])

        now = time.time()
        pool.mark_dead(42, now=now)
        self.assertEquals(99, len(pool.connections))
        self.assertEquals(1, pool.dead.qsize())
        self.assertEquals((now + 60, 42), pool.dead.get())

    def test_connection_is_skipped_when_dead(self):
        pool = ConnectionPool([(x, {}) for x in range(2)])
        pool.mark_dead(0)

        self.assertEquals([1, 1, 1],
                          [pool.get_connection(),
                           pool.get_connection(),
                           pool.get_connection(), ])

    def test_connection_is_forcibly_resurrected_when_no_live_ones_are_availible(self):
        pool = ConnectionPool([(x, {}) for x in range(2)])
        pool.dead_count[0] = 1
        pool.mark_dead(0)  # failed twice, longer timeout
        pool.mark_dead(1)  # failed the first time, first to be resurrected

        self.assertEquals([], pool.connections)
        self.assertEquals(1, pool.get_connection())
        self.assertEquals([1, ], pool.connections)

    def test_connection_is_resurrected_after_its_timeout(self):
        pool = ConnectionPool([(x, {}) for x in range(100)])

        now = time.time()
        pool.mark_dead(42, now=now - 61)
        pool.get_connection()
        self.assertEquals(42, pool.connections[-1])
        self.assertEquals(100, len(pool.connections))

    def test_already_failed_connection_has_longer_timeout(self):
        pool = ConnectionPool([(x, {}) for x in range(100)])
        now = time.time()
        pool.dead_count[42] = 2
        pool.mark_dead(42, now=now)

        self.assertEquals(3, pool.dead_count[42])
        self.assertEquals((now + 4 * 60, 42), pool.dead.get())

    def test_timeout_for_failed_connections_is_limitted(self):
        pool = ConnectionPool([(x, {}) for x in range(100)])
        now = time.time()
        pool.dead_count[42] = 245
        pool.mark_dead(42, now=now)

        self.assertEquals(246, pool.dead_count[42])
        self.assertEquals((now + 32 * 60, 42), pool.dead.get())

    def test_dead_count_is_wiped_clean_for_connection_if_marked_live(self):
        pool = ConnectionPool([(x, {}) for x in range(100)])
        now = time.time()
        pool.dead_count[42] = 2
        pool.mark_dead(42, now=now)

        self.assertEquals(3, pool.dead_count[42])
        pool.mark_live(42)
        self.assertNotIn(42, pool.dead_count)

########NEW FILE########
__FILENAME__ = core_tests
#
#   Copyright 2012 The HumanGeo Group, LLC
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
#

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import mock
import rawes
from rawes.elastic_exception import ElasticException
from tests import test_encoder
import unittest
from tests import config
import json
from datetime import datetime
import pytz
from pytz import timezone
import time

import logging
log_level = logging.ERROR
log_format = '[%(levelname)s] [%(name)s] %(asctime)s - %(message)s'
logging.basicConfig(format=log_format, datefmt='%m/%d/%Y %I:%M:%S %p', level=log_level)
soh = logging.StreamHandler(sys.stdout)
soh.setLevel(log_level)
logger = logging.getLogger("rawes.tests")
logger.addHandler(soh)


class TestElasticCore(unittest.TestCase):

    @classmethod
    def setUpClass(self):
        self.http_url = '%s:%s' % (config.ES_HOST, config.ES_HTTP_PORT)
        self.es_http = rawes.Elastic(url=self.http_url)
        self.custom_json_decoder = test_encoder.DateAwareJsonDecoder().decode
        if not config.HTTP_ONLY:
            self.thrift_url = '%s:%s' % (config.ES_HOST, config.ES_THRIFT_PORT)
            self.es_thrift = rawes.Elastic(url=self.thrift_url)

    def test_http(self):
        self._reset_indices(self.es_http)
        self._test_document_search(self.es_http)
        self._test_document_update(self.es_http)
        self._test_document_delete(self.es_http)
        self._test_bulk_load(self.es_http)
        self._test_datetime_encoder(self.es_http)
        self._test_no_handler_found_for_uri(self.es_http)

    def test_thrift(self):
        if config.HTTP_ONLY:
            return
        self._reset_indices(self.es_thrift)
        self._test_document_search(self.es_thrift)
        self._test_document_update(self.es_thrift)
        self._test_document_delete(self.es_thrift)
        self._test_bulk_load(self.es_thrift)
        self._test_datetime_encoder(self.es_thrift)
        self._test_no_handler_found_for_uri(self.es_thrift)

    def test_timeouts(self):
        es_http_short_timeout = rawes.Elastic(url=self.http_url, timeout=0.0001)
        self._test_timeout(es_short_timeout=es_http_short_timeout)

        if not config.HTTP_ONLY:
            es_thrift_short_timeout = rawes.Elastic(url=self.thrift_url, timeout=0.0001)
            self._test_timeout(es_short_timeout=es_thrift_short_timeout)

    def test_json_decoder_encoder(self):
        es_http_decoder = rawes.Elastic(url=self.http_url, json_decoder=self.custom_json_decoder)
        es_http_encoder = rawes.Elastic(url=self.http_url, json_encoder=test_encoder.encode_custom)
        self._test_custom_encoder(self.es_http, es_encoder=es_http_encoder)
        self._test_custom_decoder(self.es_http, es_decoder=es_http_decoder)
        if not config.HTTP_ONLY:
            self._reset_indices(self.es_thrift)
            self._wait_for_good_health(self.es_thrift)
            es_thrift_decoder = rawes.Elastic(url=self.thrift_url, json_decoder=self.custom_json_decoder)
            es_thrift_encoder = rawes.Elastic(url=self.thrift_url, json_encoder=test_encoder.encode_custom)
            self._test_custom_encoder(self.es_thrift, es_encoder=es_thrift_encoder)
            self._test_custom_decoder(self.es_thrift, es_decoder=es_thrift_decoder)

    def test_unicode_url(self):
        with mock.patch('rawes.http_connection.HttpConnection.__init__',
                mock.MagicMock(return_value=None)) as new_connection:
            rawes.Elastic(u'http://localhost:9200')
            new_connection.assert_called_with(u'http://localhost:9200',
                                              timeout=30)

    def test_empty_constructor(self):
        with mock.patch('rawes.http_connection.HttpConnection.__init__',
                mock.MagicMock(return_value=None)) as new_connection:
            rawes.Elastic()
            new_connection.assert_called_with('http://localhost:9200',
                                              timeout=30)

    def test_https(self):
        with mock.patch('rawes.http_connection.HttpConnection.__init__',
                mock.MagicMock(return_value=None)) as new_connection:
            rawes.Elastic("https://localhost")
            new_connection.assert_called_with('https://localhost:443',
                                              timeout=30)

    def _reset_indices(self, es):
        # If the index does not exist, test creating it and deleting it
        try:
            es.get('%s/_status' % config.ES_INDEX)
        except ElasticException:
            es.put(config.ES_INDEX)

        # Test deleting the index
        es.delete(config.ES_INDEX)
        try:
            es.get('%s/_status' % config.ES_INDEX)['status']
            self.assertTrue(False)
        except ElasticException as e:
            self.assertTrue(e.status_code == 404)

        # Now remake the index
        es.put(config.ES_INDEX)
        index_exists = es.get('%s/_status' % config.ES_INDEX)['ok'] == True
        self.assertTrue(index_exists)

    def _test_document_search(self, es):
        # Create some sample documents
        result1 = es.post('%s/tweet/' % config.ES_INDEX, data={
            'user': 'dwnoble',
            'post_date': '2012-8-27T08:00:30Z',
            'message': 'Tweeting about elasticsearch'
        }, params={
            'refresh': True
        })
        self.assertTrue(result1['ok'])
        result2 = es.put('%s/post/2' % config.ES_INDEX, data={
            'user': 'dan',
            'post_date': '2012-8-27T09:30:03Z',
            'title': 'Elasticsearch',
            'body': 'Blogging about elasticsearch'
        }, params={
            'refresh': 'true'
        })
        self.assertTrue(result2['ok'])

        # Search for documents of one type
        search_result = es.get('%s/tweet/_search' % config.ES_INDEX, data={
            'query': {
                'match_all': {}
            }
        }, params={
            'size': 2
        })
        self.assertTrue(search_result['hits']['total'] == 1)

        # Search for documents of both types
        search_result2 = es.get('%s/tweet,post/_search' % config.ES_INDEX,
                                data={
                                    'query': {
                                        'match_all': {}
                                    }},
                                params={
                                    'size': '2'
                                })
        self.assertTrue(search_result2['hits']['total'] == 2)

    def _test_document_update(self, es):
        # Ensure the document does not already exist (using alternate syntax)
        self._wait_for_good_health(es)
        try:
            es[config.ES_INDEX].sometype['123'].get()
            self.fail("Document should not exist")
        except ElasticException as e:
            self.assertEqual(e.status_code, 404)

        # Create a sample document (using alternate syntax)
        insert_result = es[config.ES_INDEX].sometype[123].put(data={
            'value': 100,
            'other': 'stuff'
        }, params={
            'refresh': 'true'
        })
        self.assertTrue(insert_result['ok'])

        # Perform a simple update (using alternate syntax)
        update_result = es[config.ES_INDEX].sometype['123']._update.post(data={
            'script': 'ctx._source.value += value',
            'params': {
                'value': 50
            }
        }, params={
            'refresh': 'true'
        })
        self.assertTrue(update_result['ok'])

        # Ensure the value was updated
        search_result2 = es[config.ES_INDEX].sometype['123'].get()
        self.assertTrue(search_result2['_source']['value'] == 150)

    def _test_document_delete(self, es):
        # Ensure the document does not already exist (using alternate syntax)
        try:
            es[config.ES_INDEX].persontype['555'].get()
            self.fail("Document should not exist")
        except ElasticException as e:
            self.assertEqual(e.status_code, 404)

        # Create a sample document (using alternate syntax)
        insert_result = es[config.ES_INDEX].persontype[555].put(data={
            'name': 'bob'
        }, params={
            'refresh': 'true'
        })
        self.assertTrue(insert_result['ok'])

        # Delete the document
        delete_result = es[config.ES_INDEX].delete('persontype/555')
        self.assertTrue(delete_result['ok'])

        # Verify the document was deleted
        try:
            es[config.ES_INDEX]['persontype']['555'].get()
            self.fail("Document should not exist")
        except ElasticException as e:
            self.assertEqual(e.status_code, 404)

    def _test_bulk_load(self, es):
        index_size = es[config.ES_INDEX][config.ES_TYPE].get('_search',
                                            params={'size': 0})['hits']['total']

        bulk_body = '''
        {"index" : {}}
        {"key":"value1"}
        {"index" : {}}
        {"key":"value2"}
        {"index" : {}}
        {"key":"value3"}
        '''

        es[config.ES_INDEX][config.ES_TYPE].post('_bulk', data=bulk_body, params={
            'refresh': 'true'
        })
        new_index_size = es[config.ES_INDEX][config.ES_TYPE].get('_search', params={'size': 0})['hits']['total']

        self.assertEqual(index_size + 3, new_index_size)

        bulk_list = [
            {"index": {}},
            {"key": "value4"},
            {"index": {}},
            {"key": "value5"},
            {"index": {}},
            {"key": "value6"}
        ]

        bulk_body_2 = '\n'.join(map(json.dumps, bulk_list)) + '\n'
        es[config.ES_INDEX][config.ES_TYPE].post('_bulk',
                                                 data=bulk_body_2,
                                                 params={
                                                    'refresh': 'true'
                                                })
        newer_index_size = es[config.ES_INDEX][config.ES_TYPE].get('_search',
                                            params={'size': 0})['hits']['total']

        self.assertEqual(index_size + 6, newer_index_size)

    def _test_datetime_encoder(self, es):
        # Ensure the document does not already exist
        test_type = 'datetimetesttype'
        test_id = 123

        try:
            es.get('%s/%s/%s' % (config.ES_INDEX, test_type, test_id))
            self.fail("Document should not exist")
        except ElasticException as e:
            self.assertEqual(e.status_code, 404)

        # Ensure no mapping exists for this type
        try:
            es.get('%s/%s/_mapping' % (config.ES_INDEX, test_type))
            self.fail("Document should not exist")
        except ElasticException as e:
            self.assertEqual(e.status_code, 404)

        # Create a sample document with a datetime
        eastern_timezone = timezone('US/Eastern')
        test_updated = datetime(2012, 11, 12, 9, 30, 3, tzinfo=eastern_timezone)
        insert_result = es.put('%s/%s/%s' % (config.ES_INDEX,
                                             test_type, test_id),
                                             data={
                                                'name': 'dateme',
                                                'updated': test_updated
                                            })
        self.assertTrue(insert_result['ok'])

        # Refresh the index after setting the mapping
        refresh_result = es.post('%s/_refresh' % config.ES_INDEX)
        self.assertTrue(refresh_result['ok'])

        # Verify the mapping was created properly
        time.sleep(0.5)  # Wait for the mapping to exist.  Probably a better way to do this
        mapping = es.get('%s/%s/_mapping' % (config.ES_INDEX, test_type))

        if test_type not in mapping:
            raise(Exception('type %s not in mapping: %r' % (test_type, mapping)))
        mapping_date_format = mapping[test_type]['properties']['updated']['format']
        self.assertEqual(mapping_date_format, 'dateOptionalTime')

        # Verify the document was created and has the proper date
        search_result = es.get('%s/%s/%s' % (config.ES_INDEX, test_type, test_id))
        self.assertTrue('exists' in search_result and search_result['exists'])
        self.assertEqual('2012-11-12T14:30:03Z', search_result['_source']['updated'])

    def _test_custom_encoder(self, es, es_encoder):
        # Ensure the document does not already exist
        test_type = 'customdatetimetesttype'
        test_id = 456
        try:
            es.get('%s/%s/%s' % (config.ES_INDEX, test_type, test_id))
            self.fail("Document should not exist")
        except ElasticException as e:
            self.assertTrue(e.status_code >= 404)

        # Ensure no mapping exists for this type
        try:
            es.get('%s/%s/_mapping' % (config.ES_INDEX, test_type))
            self.fail("Document should not exist")
        except ElasticException as e:
            self.assertEqual(e.status_code, 404)

        # Create a sample document with a datetime
        eastern_timezone = timezone('US/Eastern')
        test_updated = datetime(2012, 11, 12, 9, 30, 3, tzinfo=eastern_timezone)
        insert_result = es.put('%s/%s/%s' % (config.ES_INDEX, test_type, test_id), data={
            'name': 'dateme',
            'updated': test_updated
        }, params={
            'refresh': 'true'
        }, json_encoder=test_encoder.encode_custom)
        self.assertTrue(insert_result['ok'])

        # Flush the index after adding the new item to ensure the mapping is updated
        refresh_result = es.post('%s/_refresh' % config.ES_INDEX)
        self.assertTrue(refresh_result['ok'])

        # Verify the mapping was created properly
        mapping = es.get('%s/%s/_mapping' % (config.ES_INDEX, test_type))
        mapping_date_format = mapping[test_type]['properties']['updated']['format']
        self.assertEqual(mapping_date_format, 'dateOptionalTime')

        # Verify the document was created and has the proper date
        search_result = es.get('%s/%s/%s' % (config.ES_INDEX, test_type, test_id))
        self.assertTrue(search_result['exists'])
        self.assertEqual('2012-11-12', search_result['_source']['updated'])

        # Ensure that the class level encoder works
        # Encode a new doc w class encoder
        encoded_test_id = 12412545
        es_encoder.put('%s/%s/%s' % (config.ES_INDEX, test_type, encoded_test_id), data={
            'name': 'dateme',
            'updated' : test_updated
        }, params={
            'refresh': 'true'
        })
        encoded_search_result = es.get('%s/%s/%s' % (config.ES_INDEX, test_type, encoded_test_id))
        self.assertTrue(encoded_search_result['exists'])
        self.assertEqual('2012-11-12',encoded_search_result['_source']['updated'])

    def _test_custom_decoder(self,es, es_decoder):
        # Ensure the document does not already exist
        test_type = 'customdecodertype'
        test_id = 889988
        try:
            es.get('%s/%s/%s' % (config.ES_INDEX, test_type, test_id))
            self.fail("Document should not exist")
        except ElasticException as e:
            self.assertEqual(e.status_code,404)

        # Create a sample document with a value %Y-%m-%d
        insert_result = es.put('%s/%s/%s' % (config.ES_INDEX, test_type, test_id), data={
            'name': 'testdecode',
            'updated': "2013-07-04"
        }, params={
            'refresh': 'true'
        })
        self.assertTrue(insert_result['ok'])

        # Flush the index after adding the new item to ensure the mapping is updated
        refresh_result = es.post('%s/_refresh' % config.ES_INDEX)
        self.assertTrue(refresh_result['ok'])

        # Ensure the document was created
        search_result = es.get('%s/%s/%s' % (config.ES_INDEX, test_type, test_id))
        self.assertTrue(search_result['exists'])
        self.assertEqual('2013-07-04', search_result['_source']['updated'])

        # Ensure the class level json decoder works
        search_result_constructor_decoded = es_decoder.get('%s/%s/%s' % (config.ES_INDEX, test_type, test_id))
        self.assertTrue(search_result_constructor_decoded['exists'])
        self.assertEqual(type(search_result_constructor_decoded['_source']['updated']),datetime)
        self.assertEqual(search_result_constructor_decoded['_source']['updated'].year, 2013)
        self.assertEqual(search_result_constructor_decoded['_source']['updated'].month, 7)
        self.assertEqual(search_result_constructor_decoded['_source']['updated'].day, 4)
        self.assertEqual(search_result_constructor_decoded['_source']['updated'].tzinfo, pytz.utc)

        # Ensure the request level json decoder works
        search_result_decoded = es.get('%s/%s/%s' % (config.ES_INDEX, test_type, test_id),json_decoder=self.custom_json_decoder)
        self.assertTrue(search_result_decoded['exists'])
        self.assertEqual(type(search_result_decoded['_source']['updated']), datetime)
        self.assertEqual(search_result_decoded['_source']['updated'].year, 2013)
        self.assertEqual(search_result_decoded['_source']['updated'].month, 7)
        self.assertEqual(search_result_decoded['_source']['updated'].day, 4)
        self.assertEqual(search_result_decoded['_source']['updated'].tzinfo, pytz.utc)

    def _test_timeout(self, es_short_timeout):
        timed_out = False
        try:
            es_short_timeout.get("/_mapping")
        except Exception as e:
            timed_out = str("{0}".format(e)).find('timed out') > -1
        self.assertTrue(timed_out)

    def _test_no_handler_found_for_uri(self,es):
        try:
            es[config.ES_INDEX].nopedontexist.get()
            self.fail("Document should not exist")
        except ElasticException as e:
            self.assertEqual(e.status_code, 400)

    def _wait_for_good_health(self, es):
        # Give elasticsearch a few seconds to turn 'yellow' or 'green' after an operation
        # Try 6 times
        interval = 0.25
        good_health = False
        for _ in range(5):
            health = es.get("_cluster/health")
            if health["status"] == "green" or health["status"] == "yellow":
                good_health = True
                break
            time.sleep(interval)
        self.assertTrue(good_health)

########NEW FILE########
__FILENAME__ = connection_pool_integration_tests
import unittest

from mock import patch, MagicMock
from rawes.elastic import Elastic
from requests.models import Response
from rawes.http_connection import HttpConnection


class TestConnectionPooling(unittest.TestCase):
    """Connection pooling was added on top of Rawes, it wasn't designed from
    the beggingin. We need some tests to ensure our expectations of the
    connection pooling are met.
    """

    def testBasicRoundRobin(self):
        """ Set up a client with three different hosts to connect to, make
        multiple calls and check that each call goes on a different host in a
        Round Robin fashion
        """
        hosts = ['http://someserver1:9200', 'http://someserver2:9200',
                 'http://someserver3:9200']
        es = Elastic(hosts, connection_pool_kwargs={'dead_timeout': 10})
        with patch('rawes.http_connection.requests.Session.request',
                MagicMock(return_value=None)) as request:
            request.return_value = Response()
            called = []
            for _ in xrange(len(hosts)):
                es.get()
                # Save a list of called hosts (and remove trailing /)
                called.append(request.call_args[0][1][:-1])
            # Check against original hosts list
            self.assertSetEqual(set(hosts), set(called),
                            'All hosts in coonnection pool should be used')
            called_again = []
            for _ in xrange(len(hosts)):
                es.get()
                # Call the same hosts again (don't forget about the trailing /)
                called_again.append(request.call_args[0][1][:-1])
            # Check they were called in the same order as before
            self.assertListEqual(called, called_again,
                                    'Round robin order wasn\'t preserved')


########NEW FILE########
__FILENAME__ = py3k
#
#   Copyright 2012 The HumanGeo Group, LLC
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
#

from tests import config
config.HTTP_ONLY=True
from tests.core_tests import *

########NEW FILE########
__FILENAME__ = test_encoder
#
#   Copyright 2012 The HumanGeo Group, LLC
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
#

import datetime
import pytz
import json
from rawes.utils import isstr

def encode_custom(obj):
    """
    ISO encode datetimes with less precision
    """
    if isinstance(obj, datetime.datetime):
        return obj.astimezone(pytz.utc).strftime('%Y-%m-%d')
    raise TypeError(repr(obj) + " is not JSON serializable")

class DateAwareJsonDecoder(json.JSONDecoder):
    """
    Automatically decode Y-m-d strings to python datetime objects in UTC timezone
    """
    def __init__(self):
        json.JSONDecoder.__init__(self, object_hook=self.dict_to_object)
    
    def dict_to_object(self, d):
        for k,v in d.items():
            if isstr(v):
                try:
                    d[k] = pytz.utc.localize(datetime.datetime.strptime( v, "%Y-%m-%d"))
                except Exception as e:
                    pass
        return d

########NEW FILE########
