__FILENAME__ = httpclient
import time
import gevent.pool
from geventhttpclient import HTTPClient, URL
from geventhttpclient.header import Headers


if __name__ == "__main__":

    N = 1000
    C = 10

    url = URL('http://127.0.0.1/index.html')
    qs = url.request_uri

    def run(client):
        response = client.get(qs)
        response.read()
        assert response.status_code == 200

    # For better compatibility, especially with cookies, use headers_type=Headers
    # The difference is 2900 requests/s with dict vs 2450 with Headers on my machine
    # For maximum speed, set headers_type=dict
    # In that case, multiple header lines will be ignored, only the first is kept
    client = HTTPClient.from_url(url, concurrency=C, headers_type=dict)
    group = gevent.pool.Pool(size=C)

    for i in xrange(5):
        now = time.time()
        for _ in xrange(N):
            group.spawn(run, client)
        group.join()
    
        delta = time.time() - now
        req_per_sec = N / delta
    
        print "request count:%d, concurrenry:%d, %f req/s" % (
        N, C, req_per_sec)



########NEW FILE########
__FILENAME__ = httplib2_patched
if __name__ == "__main__":

    from geventhttpclient import httplib
    httplib.patch()

    import httplib2
    import time
    import gevent.queue
    import gevent.pool
    from contextlib import contextmanager

    class ConnectionPool(object):

        def __init__(self, factory, size=5):
            self.factory = factory
            self.queue = gevent.queue.Queue(size)
            for i in xrange(size):
                self.queue.put(factory())

        @contextmanager
        def use(self):
            el = self.queue.get()
            yield el
            self.queue.put(el)


    def httplib2_factory(*args, **kw):
        def factory():
            return httplib2.Http(*args, **kw)
        return factory


    N = 1000
    C = 10

    url = 'http://127.0.0.1/index.html'

    def run(pool):
        with pool.use() as http:
            http.request(url)


    http_pool = ConnectionPool(httplib2_factory(), size=C)
    group = gevent.pool.Pool(size=C)

    for i in xrange(5):
        now = time.time()
        for _ in xrange(N):
            group.spawn(run, http_pool)
        group.join()
    
        delta = time.time() - now
        req_per_sec = N / delta
    
        print "request count:%d, concurrenry:%d, %f req/s" % (
            N, C, req_per_sec)



########NEW FILE########
__FILENAME__ = httplib2_simple
if __name__ == "__main__":

    import httplib2
    import time
    import gevent.queue
    import gevent.pool
    from contextlib import contextmanager
    from gevent import monkey
    monkey.patch_all()

    class ConnectionPool(object):

        def __init__(self, factory, size=5):
            self.factory = factory
            self.queue = gevent.queue.Queue(size)
            for i in xrange(size):
                self.queue.put(factory())

        @contextmanager
        def use(self):
            el = self.queue.get()
            yield el
            self.queue.put(el)


    def httplib2_factory(*args, **kw):
        def factory():
            return httplib2.Http(*args, **kw)
        return factory


    N = 1000
    C = 10

    url = 'http://127.0.0.1/index.html'

    def run(pool):
        with pool.use() as http:
            http.request(url)


    http_pool = ConnectionPool(httplib2_factory(), size=C)
    group = gevent.pool.Pool(size=C)

    for i in xrange(5):
        now = time.time()
        for _ in xrange(N):
            group.spawn(run, http_pool)
        group.join()
    
        delta = time.time() - now
        req_per_sec = N / delta
    
        print "request count:%d, concurrenry:%d, %f req/s" % (
            N, C, req_per_sec)



########NEW FILE########
__FILENAME__ = restkit_bench
if __name__ == "__main__":

    from gevent import monkey
    monkey.patch_all()

    import gevent.pool
    import time

    from restkit import *
    from socketpool import ConnectionPool

    url = 'http://127.0.0.1/index.html'

    N = 1000
    C = 10

    Pool = ConnectionPool(factory=Connection,backend="gevent",max_size=C,timeout=300)


    def run():
        response = request(url,follow_redirect=True,pool=Pool)
        response.body_string()
        assert response.status_int == 200


    group = gevent.pool.Pool(size=C)

    for i in xrange(5):
        now = time.time()
        for _ in xrange(N):
            group.spawn(run)
        group.join()
    
        delta = time.time() - now
        req_per_sec = N / delta
    
        print "request count:%d, concurrenry:%d, %f req/s" % (
            N, C, req_per_sec)


########NEW FILE########
__FILENAME__ = download
#!/usr/bin/env python

from geventhttpclient import HTTPClient, URL

if __name__ == "__main__":

    url = URL('http://127.0.0.1:80/100.dat')
    http = HTTPClient.from_url(url)
    response = http.get(url.request_uri)
    assert response.status_code == 200

    CHUNK_SIZE = 1024 * 16 # 16KB
    with open('/tmp/100.dat', 'w') as f:
        data = response.read(CHUNK_SIZE)
        while data:
            f.write(data)
            data = response.read(CHUNK_SIZE)



########NEW FILE########
__FILENAME__ = facebook
#!/usr/bin/env python

import gevent.pool
import json

from geventhttpclient import HTTPClient
from geventhttpclient.url import URL


if __name__ == "__main__":

    # go to http://developers.facebook.com/tools/explorer and copy the access token
    TOKEN = '<go to http://developers.facebook.com/tools/explorer and copy the access token>'


    url = URL('https://graph.facebook.com/me/friends')
    url['access_token'] = TOKEN

    # setting the concurrency to 10 allow to create 10 connections and
    # reuse them.
    http = HTTPClient.from_url(url, concurrency=10)

    response = http.get(url.request_uri)
    assert response.status_code == 200

    # response comply to the read protocol. It passes the stream to
    # the json parser as it's being read.
    data = json.load(response)['data']

    def print_friend_username(http, friend_id):
        friend_url = URL('/' + str(friend_id))
        friend_url['access_token'] = TOKEN
        # the greenlet will block until a connection is available
        response = http.get(friend_url.request_uri)
        assert response.status_code == 200
        friend = json.load(response)
        if friend.has_key('username'):
            print '%s: %s' % (friend['username'], friend['name'])
        else:
            print '%s has no username.' % friend['name']

    # allow to run 20 greenlet at a time, this is more than concurrency
    # of the http client but isn't a problem since the client has its own
    # connection pool.
    pool = gevent.pool.Pool(20)
    for item in data:
        friend_id = item['id']
        pool.spawn(print_friend_username, http, friend_id)

    pool.join()
    http.close()



########NEW FILE########
__FILENAME__ = httplib2_patched
from geventhttpclient import httplib
httplib.patch()

from httplib2 import Http

if __name__ == "__main__":
    http = Http()
    response, content = http.request('http://google.fr/')
    assert response.status == 200
    assert content
    print response
    print content

    response, content = http.request('http://google.fr/', method='HEAD')
    assert response.status == 200
    assert content == ''
    print response

    response, content = http.request('https://www.google.com/', method='HEAD')
    assert response.status == 200
    assert content == ''
    print response



########NEW FILE########
__FILENAME__ = twitter_streaming
import time
import json
from pprint import pprint as pp
from geventhttpclient.url import URL
from geventhttpclient import HTTPClient
import oauth2 as oauthlib

if __name__ == "__main__":

    APP_ID = '<your app id>'
    APP_SECRET = '<your app id>'

    # see https://github.com/simplegeo/python-oauth2
    # "Twitter Three-legged OAuth Example"
    token_info = {
        "oauth_token_secret" : "...",
        "user_id" : "...",
        "oauth_token" : "...",
        "screen_name" : "..."
    }

    oauthlib_consumer = oauthlib.Consumer(APP_ID, APP_SECRET)
    token = oauthlib.Token(token_info['oauth_token'],
                           token_info['oauth_token_secret'])

    params = {
        'oauth_version': "1.0",
        'oauth_nonce': oauthlib.generate_nonce(),
        'oauth_timestamp': int(time.time()),
        'oauth_token': token.key,
        'oauth_consumer_key': oauthlib_consumer.key,
        'locations': '-122.75,36.8,-121.75,37.8' # San Francisco
    }

    url = URL('https://stream.twitter.com/1/statuses/filter.json')
    req = oauthlib.Request.from_consumer_and_token(
            oauthlib_consumer,
            token=token,
            http_url=str(url),
            http_method='POST')

    signature_method = oauthlib.SignatureMethod_HMAC_SHA1()
    req = oauthlib.Request(method="POST", url=str(url), parameters=params)
    req.sign_request(signature_method, oauthlib_consumer, token)

    http = HTTPClient.from_url(url)
    response = http.request('POST', url.request_uri,
        body=req.to_postdata(),
        headers={'Content-Type': 'application/x-www-form-urlencoded',
                 'Accept': '*/*'})

    data = json.loads(response.readline())
    while data:
        pp(data)
        data = json.loads(response.readline())


########NEW FILE########
__FILENAME__ = urllib_patched
from geventhttpclient import httplib
httplib.patch()

from urllib2 import urlopen


print urlopen('https://www.google.fr/').read()



########NEW FILE########
__FILENAME__ = client
import errno
from geventhttpclient.connectionpool import ConnectionPool, SSLConnectionPool
from geventhttpclient.response import HTTPSocketPoolResponse
from geventhttpclient.response import HTTPConnectionClosed
from geventhttpclient.url import URL
from geventhttpclient.header import Headers
from geventhttpclient import __version__
import gevent.socket

CRLF = "\r\n"
WHITESPACE = " "
FIELD_VALUE_SEP = ": "
HOST_PORT_SEP = ":"
SLASH = "/"
PROTO_HTTP = "http"
PROTO_HTTPS = "https"
HEADER_HOST = "Host"
HEADER_CONTENT_LENGTH = "Content-Length"

METHOD_GET      = "GET"
METHOD_HEAD     = "HEAD"
METHOD_POST     = "POST"
METHOD_PUT      = "PUT"
METHOD_DELETE   = "DELETE"


class HTTPClient(object):

    HTTP_11 = 'HTTP/1.1'
    HTTP_10 = 'HTTP/1.0'

    BLOCK_SIZE = 1024 * 4 # 4KB

    DEFAULT_HEADERS = Headers({
        'User-Agent': 'python/gevent-http-client-' + __version__
    })

    @classmethod
    def from_url(cls, url, **kw):
        if not isinstance(url, URL):
            url = URL(url)
        enable_ssl = url.scheme == PROTO_HTTPS
        if not enable_ssl:
            kw.pop('ssl_options', None)
        return cls(url.host, port=url.port, ssl=enable_ssl, **kw)

    def __init__(self, host, port=None, headers={},
            block_size=BLOCK_SIZE,
            connection_timeout=ConnectionPool.DEFAULT_CONNECTION_TIMEOUT,
            network_timeout=ConnectionPool.DEFAULT_NETWORK_TIMEOUT,
            disable_ipv6=False,
            concurrency=1, ssl_options=None, ssl=False, insecure=False,
            proxy_host=None, proxy_port=None, version=HTTP_11,
            headers_type=Headers):
        self.host = host
        self.port = port
        connection_host = self.host
        connection_port = self.port
        if proxy_host is not None:
            assert proxy_port is not None, \
                'you have to provide proxy_port if you set proxy_host'
            self.use_proxy = True
            connection_host = proxy_host
            connection_port = proxy_port
        else:
            self.use_proxy = False
        if ssl and ssl_options is None:
            ssl_options = {}
        if ssl_options is not None:
            self.ssl = True
            if not self.port:
                self.port = 443
            if not connection_port:
                connection_port = self.port
            self._connection_pool = SSLConnectionPool(
                connection_host, connection_port, size=concurrency,
                ssl_options=ssl_options,
                insecure=insecure,
                network_timeout=network_timeout,
                connection_timeout=connection_timeout,
                disable_ipv6=disable_ipv6)
        else:
            self.ssl = False
            if not self.port:
                self.port = 80
            if not connection_port:
                connection_port = self.port
            self._connection_pool = ConnectionPool(
                connection_host, connection_port,
                size=concurrency,
                network_timeout=network_timeout,
                connection_timeout=connection_timeout,
                disable_ipv6=disable_ipv6)
        self.version = version
        self.headers_type = headers_type
        self.default_headers = headers_type()
        self.default_headers.update(self.DEFAULT_HEADERS)
        self.default_headers.update(headers)
        self.block_size = block_size
        self._base_url_string = str(self.get_base_url())

    def get_base_url(self):
        url = URL()
        url.host = self.host
        url.port = self.port
        url.scheme = self.ssl and PROTO_HTTPS or PROTO_HTTP
        return url

    def close(self):
        self._connection_pool.close()

    def _build_request(self, method, request_uri, body="", headers={}):
        header_fields = self.headers_type()
        header_fields.update(self.default_headers)
        header_fields.update(headers)
        if self.version == self.HTTP_11 and HEADER_HOST not in header_fields:
            host_port = self.host
            if self.port not in (80, 443):
                host_port += HOST_PORT_SEP + str(self.port)
            header_fields[HEADER_HOST] = host_port
        if body and HEADER_CONTENT_LENGTH not in header_fields:
            header_fields[HEADER_CONTENT_LENGTH] = len(body)

        request_url = request_uri
        if self.use_proxy:
            base_url = self._base_url_string
            if request_uri.startswith(SLASH):
                base_url = base_url[:-1]
            request_url = base_url + request_url
        elif not request_url.startswith((SLASH, PROTO_HTTP)):
            request_url = SLASH + request_url
        elif request_url.startswith(PROTO_HTTP):
            if request_url.startswith(self._base_url_string):
                request_url = request_url[len(self._base_url_string)-1:]
            else:
                raise ValueError("Invalid host in URL")

        request = method + WHITESPACE + request_url + WHITESPACE + self.version + CRLF

        for field, value in header_fields.iteritems():
            request += field + FIELD_VALUE_SEP + str(value) + CRLF
        request += CRLF
        return request

    def request(self, method, request_uri, body=b"", headers={}):
        request = self._build_request(
            method.upper(), request_uri, body=body, headers=headers)

        attempts_left = self._connection_pool.size + 1

        while 1:
            sock = self._connection_pool.get_socket()
            try:
                sock.sendall(request)
            except gevent.socket.error as e:
                self._connection_pool.release_socket(sock)
                if e.errno == errno.ECONNRESET and attempts_left > 0:
                    attempts_left -= 1
                    continue
                raise e

            if body:
                sock.sendall(body)

            try:
                response = HTTPSocketPoolResponse(sock, self._connection_pool,
                    block_size=self.block_size, method=method.upper(), headers_type=self.headers_type)
            except HTTPConnectionClosed as e:
                # connection is released by the response itself
                if attempts_left > 0:
                    attempts_left -= 1
                    continue
                raise e
            else:
                response._sent_request = request
                return response

    def get(self, request_uri, headers={}):
        return self.request(METHOD_GET, request_uri, headers=headers)

    def head(self, request_uri, headers={}):
        return self.request(METHOD_HEAD, request_uri, headers=headers)

    def post(self, request_uri, body=u'', headers={}):
        return self.request(METHOD_POST, request_uri, body=body, headers=headers)

    def put(self, request_uri, body=u'', headers={}):
        return self.request(METHOD_PUT, request_uri, body=body, headers=headers)

    def delete(self, request_uri, body=u'', headers={}):
        return self.request(METHOD_DELETE, request_uri, body=body, headers=headers)


class HTTPClientPool(object):
    """ Factory for maintaining a bunch of clients, one per host:port """
    # TODO: Add some housekeeping and cleanup logic

    def __init__(self, **kwargs):
        self.clients = dict()
        self.client_args = kwargs

    def get_client(self, url):
        if not isinstance(url, URL):
            url = URL(url)
        client_key = url.host, url.port
        try:
            return self.clients[client_key]
        except KeyError:
            client = HTTPClient.from_url(url, **self.client_args)
            self.clients[client_key] = client
            return client

    def close(self):
        for client in self.clients.values():
            client.close()

########NEW FILE########
__FILENAME__ = connectionpool
import os
import gevent.queue
import gevent.ssl
import gevent.socket
import certifi
from backports.ssl_match_hostname import match_hostname

try:
    from gevent import lock
except ImportError:
    # gevent < 1.0b2
    from gevent import coros as lock


CA_CERTS = certifi.where()


DEFAULT_CONNECTION_TIMEOUT = 5.0
DEFAULT_NETWORK_TIMEOUT = 5.0


IGNORED = object()


class ConnectionPool(object):

    DEFAULT_CONNECTION_TIMEOUT = 5.0
    DEFAULT_NETWORK_TIMEOUT = 5.0

    def __init__(self, host, port,
            size=5, disable_ipv6=False,
            connection_timeout=DEFAULT_CONNECTION_TIMEOUT,
            network_timeout=DEFAULT_NETWORK_TIMEOUT):
        self._closed = False
        self._host = host
        self._port = port
        self._semaphore = lock.BoundedSemaphore(size)
        self._socket_queue = gevent.queue.LifoQueue(size)

        self.connection_timeout = connection_timeout
        self.network_timeout = network_timeout
        self.size = size
        self.disable_ipv6 = disable_ipv6

    def _resolve(self):
        """ resolve (dns) socket informations needed to connect it.
        """
        family = 0
        if self.disable_ipv6:
            family = gevent.socket.AF_INET
        info = gevent.socket.getaddrinfo(self._host, self._port,
                family, 0, gevent.socket.SOL_TCP)
        # family, socktype, proto, canonname, sockaddr = info[0]
        return info

    def close(self):
        self._closed = True
        while not self._socket_queue.empty():
            try:
                sock = self._socket_queue.get(block=False)
                try:
                    sock.close()
                except:
                    pass
            except gevent.queue.Empty:
                pass

    def _create_tcp_socket(self, family, socktype, protocol):
        """ tcp socket factory.
        """
        sock = gevent.socket.socket(family, socktype, protocol)
        return sock

    def _create_socket(self):
        """ might be overriden and super for wrapping into a ssl socket
            or set tcp/socket options
        """
        sock_infos = self._resolve()
        first_error = None
        for sock_info in sock_infos:
            try:
                sock = self._create_tcp_socket(*sock_info[:3])
            except Exception as e:
                if not first_error:
                    first_error = e
                continue

            try:
                sock.settimeout(self.connection_timeout)
                sock.connect(sock_info[-1])
                self.after_connect(sock)
                sock.settimeout(self.network_timeout)
                return sock
            except IOError as e:
                sock.close()
                if not first_error:
                    first_error = e
            except:
                sock.close()
                raise

        if first_error:
            raise first_error
        else:
            raise RuntimeError("Cannot resolve %s:%s" % (self._host, self._port))


    def after_connect(self, sock):
        pass

    def get_socket(self):
        """ get a socket from the pool. This blocks until one is available.
        """
        self._semaphore.acquire()
        if self._closed:
            raise RuntimeError('connection pool closed')
        try:
            return self._socket_queue.get(block=False)
        except gevent.queue.Empty:
            try:
                return self._create_socket()
            except:
                self._semaphore.release()
                raise

    def return_socket(self, sock):
        """ return a socket to the pool.
        """
        if self._closed:
            try:
                sock.close()
            except:
                pass
            return
        self._socket_queue.put(sock)
        self._semaphore.release()

    def release_socket(self, sock):
        """ call when the socket is no more usable.
        """
        try:
            sock.close()
        except:
            pass
        if not self._closed:
            self._semaphore.release()


class SSLConnectionPool(ConnectionPool):

    default_options = {
        'ssl_version': gevent.ssl.PROTOCOL_SSLv3,
        'ca_certs': CA_CERTS,
        'cert_reqs': gevent.ssl.CERT_REQUIRED
    }

    def __init__(self, host, port, **kw):
        self.ssl_options = self.default_options.copy()
        self.insecure = kw.pop('insecure', False)
        self.ssl_options.update(kw.pop('ssl_options', dict()))
        super(SSLConnectionPool, self).__init__(host, port, **kw)

    def after_connect(self, sock):
        super(SSLConnectionPool, self).after_connect(sock)
        if not self.insecure:
            match_hostname(sock.getpeercert(), self._host)

    def _create_tcp_socket(self, family, socktype, protocol):
        sock = super(SSLConnectionPool, self)._create_tcp_socket(
            family, socktype, protocol)

        return gevent.ssl.wrap_socket(sock, **self.ssl_options)

########NEW FILE########
__FILENAME__ = header
import copy
import pprint
from collections import Mapping

_dict_setitem = dict.__setitem__
_dict_getitem = dict.__getitem__
_dict_delitem = dict.__delitem__
_dict_contains = dict.__contains__

MULTIPLE_HEADERS_ALLOWED = set(['cookie', 'set-cookie', 'set-cookie2'])

def lower(txt):
    try:
        return txt.lower()
    except AttributeError:
        raise TypeError("Header names must be of type basestring, not %s" % type(txt).__name__)


class Headers(dict):
    """ Storing headers in an easily accessible way and providing cookielib compatibility

        RFC 2616/4.2: Multiple message-header fields with the same field-name MAY be present
        in a message if and only if the entire field-value for that header field is defined
        as a comma-separated list.
    """
    def __init__(self, *args, **kwargs):
        dict.__init__(self)
        self.update(*args, **kwargs)

    def __setitem__(self, key, val):
        """ Ensures only lowercase header names
        """
        return _dict_setitem(self, lower(key), val)

    def __getitem__(self, key):
        return _dict_getitem(self, lower(key))

    def __delitem__(self, key):
        return _dict_delitem(self, lower(key))

    def __contains__(self, key):
        return _dict_contains(self, lower(key))

    def iteritems(self):
        """ Iterates all headers also extracting multiple entries
        """
        for key, vals in dict.iteritems(self):
            if not isinstance(vals, list):
                yield key, vals
            else:
                for val in vals:
                    yield key, val

    def items(self):
        return list(self.iteritems())

    def __len__(self):
        return sum(len(vals) if isinstance(vals, list) else 1 for vals in self.itervalues())

    def get(self, key, default=None):
        """ Overwrite of inbuilt get, to use case-insensitive __getitem__
        """
        try:
            return self[key]
        except KeyError:
            return default

    def add(self, key, val):
        """ Insert new header lines to the container. This method creates lists only for multiple,
            not for single lines. This minimizes the overhead for the common case and optimizes the
            total parsing speed of the headers.
        """
        key = lower(key)
        # Use lower only once and then stick with inbuilt functions for speed
        if not _dict_contains(self, key):
            _dict_setitem(self, key, val)
        else:
            item = _dict_getitem(self, key)
            if isinstance(item, list):
                item.append(val)
            else:
                if key in MULTIPLE_HEADERS_ALLOWED:
                    # Only create duplicate headers for meaningful field names,
                    # else overwrite the field
                    _dict_setitem(self, key, [item, val])
                else:
                    _dict_setitem(self, key, val)

    # Keep some dict-compatible syntax for the Response object
    setdefault = add

    def update(self, *args, **kwds):
        """ Adapted from MutableMapping to use self.add instead of self.__setitem__
        """
        if len(args) > 1:
            raise TypeError("update() takes at most one positional "
                            "arguments ({} given)".format(len(args)))
        try:
            other = args[0]
        except IndexError:
            pass
        else:
            if isinstance(other, Mapping):
                for key in other:
                    self.add(key, other[key])
            elif hasattr(other, "keys"):
                for key in other.keys():
                    self.add(key, other[key])
            else:
                for key, value in other:
                    self.add(key, value)

        for key, value in kwds.items():
            self.add(key, value)

    def getheaders(self, name):
        """ Compatibility with urllib/cookielib: Always return lists
        """
        try:
            ret = self[name]
        except KeyError:
            return []
        else:
            if isinstance(ret, list):
                return ret
            else:
                return [ret]

    getallmatchingheaders = getheaders
    iget = getheaders

    def discard(self, key):
        try:
            self.__delitem__(key)
        except KeyError:
            pass

    @staticmethod
    def _format_field(field):
        return '-'.join(field_pt.capitalize() for field_pt in field.split('-'))

    def pretty_items(self):
        for key, vals in dict.iteritems(self):
            key = self._format_field(key)
            if not isinstance(vals, list):
                yield key, vals
            else:
                for val in vals:
                    yield key, val

    def __str__(self):
        return pprint.pformat(sorted(self.pretty_items()))

    def copy(self):
        """ Overwrite inbuilt copy method, as inbuilt does not preserve type
        """
        return copy.copy(self)

    def compatible_dict(self):
        """ If the client performing the request is not adjusted for this class, this function
            can create a backwards and standards compatible version containing comma joined
            strings instead of lists for multiple headers.
        """
        ret = dict()
        for key in self:
            val = self[key]
            key = self._format_field(key)
            if len(val) == 1:
                val = val[0]
            else:
                # TODO: Add escaping of quotes in vals and quoting
                val = ', '.join(val)
            ret[key] = val
        return ret


########NEW FILE########
__FILENAME__ = httplib
httplib = __import__('httplib')
from geventhttpclient import response
import gevent.socket
import gevent.ssl


class HTTPResponse(response.HTTPSocketResponse):

    def __init__(self, sock, method='GET', strict=0, debuglevel=0,
            buffering=False, **kw):
        if method is None:
            method = 'GET'
        else:
            method = method.upper()
        super(HTTPResponse, self).__init__(sock, method=method, **kw)

    @property
    def version(self):
        v = self.get_http_version()
        if v == 'HTTP/1.1':
            return 11
        return 10

    @property
    def status(self):
        return self.status_code

    @property
    def reason(self):
        return self.msg

    @property
    def msg(self):
        return httplib.responses[self.status_code]

    def _read_status(self):
        return (self.version, self.status_code, self.msg)

    def begin(self):
        pass

    def close(self):
        self.release()

    def isclosed(self):
        return self._sock is None

    def read(self, amt=None):
        return super(HTTPResponse, self).read(amt)

    def getheader(self, name, default=None):
        return self.get(name.lower(), default)

    def getheaders(self):
        return self._headers_index.items()

    @property
    def will_close(self):
        return self.message_complete and not self.should_keep_alive()

    def _check_close(self):
        return not self.should_keep_alive()


HTTPLibConnection = httplib.HTTPConnection

class HTTPConnection(httplib.HTTPConnection):

    response_class = HTTPResponse

    def __init__(self, *args, **kw):
        HTTPLibConnection.__init__(self, *args, **kw)
        # python 2.6 compat
        if not hasattr(self, "source_address"):
            self.source_address = None

    def connect(self):
        self.sock = gevent.socket.create_connection(
            (self.host,self.port),
            self.timeout, self.source_address)

        if self._tunnel_host:
            self._tunnel()


class HTTPSConnection(HTTPConnection):

    default_port = 443

    def __init__(self, host, port=None, key_file=None, cert_file=None, **kw):
        HTTPConnection.__init__(self, host, port, **kw)
        self.key_file = key_file
        self.cert_file = cert_file

    def connect(self):
        "Connect to a host on a given (SSL) port."

        sock = gevent.socket.create_connection((self.host, self.port),
                                        self.timeout, self.source_address)
        if self._tunnel_host:
            self.sock = sock
            self._tunnel()
        self.sock = gevent.ssl.wrap_socket(
            sock, self.key_file, self.cert_file)


def patch():
    httplib.HTTPConnection = HTTPConnection
    httplib.HTTPSConnection = HTTPSConnection
    httplib.HTTPResponse = HTTPResponse



########NEW FILE########
__FILENAME__ = response
import errno
from geventhttpclient._parser import HTTPResponseParser, HTTPParseError #@UnresolvedImport
from geventhttpclient.header import Headers
import gevent.socket


HEADER_STATE_INIT = 0
HEADER_STATE_FIELD = 1
HEADER_STATE_VALUE = 2
HEADER_STATE_DONE = 3


class HTTPConnectionClosed(HTTPParseError):
    pass


class HTTPProtocolViolationError(HTTPParseError):
    pass


class HTTPResponse(HTTPResponseParser):

    def __init__(self, method='GET', headers_type=Headers):
        super(HTTPResponse, self).__init__()
        self.method = method.upper()
        self.headers_complete = False
        self.message_begun = False
        self.message_complete = False
        self._headers_index = headers_type()
        self._header_state = HEADER_STATE_INIT
        self._current_header_field = None
        self._current_header_value = None
        self._header_position = 1
        self._body_buffer = bytearray()

    def __getitem__(self, key):
        return self._headers_index[key]

    def get(self, key, default=None):
        return self._headers_index.get(key, default)

    def iteritems(self):
        return self._headers_index.iteritems()

    def items(self):
        return self._headers_index.items()
    
    def info(self):
        """ Basic cookielib compatibility """
        return self._headers_index

    def should_keep_alive(self):
        """ return if the headers instruct to keep the connection
        alive.
        """
        return bool(super(HTTPResponse, self).should_keep_alive())

    def should_close(self):
        """ return if we should close the connection.

        It is not the opposite of should_keep_alive method. It also checks
        that the body as been consumed completely.
        """
        return not self.message_complete or \
               self.parser_failed() or \
               not super(HTTPResponse, self).should_keep_alive()

    headers = property(items)

    def __contains__(self, key):
        return key in self._headers_index

    @property
    def status_code(self):
        return self.get_code()

    @property
    def content_length(self):
        length = self.get('content-length', None)
        if length is not None:
            return long(length)

    @property
    def version(self):
        return self.get_http_version()

    def _on_message_begin(self):
        if self.message_begun:
            raise HTTPProtocolViolationError("A new response began before end of %r." % self)
        self.message_begun = True

    def _on_message_complete(self):
        self.message_complete = True

    def _on_headers_complete(self):
        self._flush_header()
        self._header_state = HEADER_STATE_DONE
        self.headers_complete = True

        if self.method == 'HEAD':
            return True # SKIP BODY
        return False

    def _on_header_field(self, string):
        if self._header_state == HEADER_STATE_FIELD:
            self._current_header_field += string
        else:
            if self._header_state == HEADER_STATE_VALUE:
                self._flush_header()
            self._current_header_field = string

        self._header_state = HEADER_STATE_FIELD

    def _on_header_value(self, string):
        if self._header_state == HEADER_STATE_VALUE:
            self._current_header_value += string
        else:
            self._current_header_value = string

        self._header_state = HEADER_STATE_VALUE

    def _flush_header(self):
        if self._current_header_field is not None:
            self._headers_index.setdefault(self._current_header_field, 
                                           self._current_header_value)
            self._header_position += 1
            self._current_header_field = None
            self._current_header_value = None

    def _on_body(self, buf):
        self._body_buffer += buf

    def __repr__(self):
        return "<{klass} status={status} headers={headers}>".format(
            klass=self.__class__.__name__,
            status=self.status_code,
            headers=dict(self.headers))


class HTTPSocketResponse(HTTPResponse):

    DEFAULT_BLOCK_SIZE = 1024 * 4 # 4KB

    def __init__(self, sock, block_size=DEFAULT_BLOCK_SIZE,
            method='GET', **kw):
        super(HTTPSocketResponse, self).__init__(method=method, **kw)
        self._sock = sock
        self.block_size = block_size
        self._read_headers()

    def release(self):
        try:
            if self._sock is not None and self.should_close():
                try:
                    self._sock.close()
                except:
                    pass
        finally:
            self._sock = None

    def __del__(self):
        self.release()

    def _read_headers(self):
        try:
            start = True
            while not self.headers_complete:
                try:
                    data = self._sock.recv(self.block_size)
                    self.feed(data)
                    # depending on gevent version we get a conn reset or no data
                    if not len(data) and not self.headers_complete:
                        if start:
                            raise HTTPConnectionClosed(
                                'connection closed.')
                        raise HTTPParseError('connection closed before'
                                            ' end of the headers')
                    start = False
                except gevent.socket.error as e:
                    if e.errno == errno.ECONNRESET:
                        if start:
                            raise HTTPConnectionClosed(
                                'connection closed.')
                    raise

            if self.message_complete:
                self.release()
        except BaseException:
            self.release()
            raise

    def readline(self, sep="\r\n"):
        cursor = 0
        multibyte = len(sep) > 1
        while True:
            cursor = self._body_buffer.find(sep[0], cursor)
            if cursor >= 0:
                found = True
                if multibyte:
                    pos = cursor
                    cursor = self._body_buffer.find(sep, cursor)
                    if cursor < 0:
                        cursor = pos
                        found = False
                if found:
                    length = cursor + len(sep)
                    line = str(self._body_buffer[:length])
                    del self._body_buffer[:length]
                    cursor = 0
                    return line
            else:
                cursor = 0
            if self.message_complete:
                return ''
            try:
                data = self._sock.recv(self.block_size)
                self.feed(data)
            except BaseException:
                self.release()
                raise

    def read(self, length=None):
        # get the existing body that may have already been parsed
        # during headers parsing
        if length is not None and len(self._body_buffer) >= length:
            read = self._body_buffer[0:length]
            del self._body_buffer[0:length]
            return str(read)

        if self._sock is None:
            read = str(self._body_buffer)
            del self._body_buffer[:]
            return read

        try:
            while not(self.message_complete) and (
                    length is None or len(self._body_buffer) < length):
                data = self._sock.recv(length or self.block_size)
                self.feed(data)
        except:
            self.release()
            raise

        if length is not None:
            read = str(self._body_buffer[0:length])
            del self._body_buffer[0:length]
            return read

        read = str(self._body_buffer)
        del self._body_buffer[:]
        return read

    def __iter__(self):
        return self

    def next(self):
        bytes = self.read(self.block_size)
        if not len(bytes):
            raise StopIteration()
        return bytes

    def _on_message_complete(self):
        super(HTTPSocketResponse, self)._on_message_complete()
        self.release()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.release()


class HTTPSocketPoolResponse(HTTPSocketResponse):

    def __init__(self, sock, pool, **kw):
        self._pool = pool
        super(HTTPSocketPoolResponse, self).__init__(sock, **kw)

    def release(self):
        try:
            if self._sock is not None:
                if self.should_close():
                    self._pool.release_socket(self._sock)
                else:
                    self._pool.return_socket(self._sock)
        finally:
            self._sock = None
            self._pool = None

    def __del__(self):
        if self._sock is not None:
            self._pool.release_socket(self._sock)


########NEW FILE########
__FILENAME__ = test_client
import os
import pytest
import json
from contextlib import contextmanager
from geventhttpclient import HTTPClient
from gevent.ssl import SSLError #@UnresolvedImport
import gevent.pool

import gevent.server


listener = ('127.0.0.1', 54323)

@contextmanager
def server(handler):
    server = gevent.server.StreamServer(
        listener,
        handle=handler)
    server.start()
    try:
        yield
    finally:
        server.stop()


def test_client_simple():
    client = HTTPClient('www.google.fr')
    assert client.port == 80
    response = client.get('/')
    assert response.status_code == 200
    body = response.read()
    assert len(body)

def test_client_without_leading_slash():
    client = HTTPClient('www.google.fr')
    with client.get("") as response:
        assert response.status_code == 200
    with client.get("maps") as response:
        assert(response.status_code in (200, 301, 302))

test_headers = {'User-Agent': 'Mozilla/5.0 (X11; U; Linux i686; de; rv:1.9.2.17) Gecko/20110422 Ubuntu/10.04 (lucid) Firefox/3.6.17'}
def test_client_with_default_headers():
    client = HTTPClient.from_url('www.google.fr/', headers=test_headers)

def test_request_with_headers():
    client = HTTPClient('www.google.fr')
    response = client.get('/', headers=test_headers)
    assert response.status_code == 200

client = HTTPClient('www.heise.de')
raw_req_cmp = client._build_request('GET', '/tp/')

def test_build_request_relative_uri():
    raw_req = client._build_request('GET', 'tp/')
    assert raw_req == raw_req_cmp

def test_build_request_absolute_uri():
    raw_req = client._build_request('GET', '/tp/')
    assert raw_req == raw_req_cmp

def test_build_request_full_url():
    raw_req = client._build_request('GET', 'http://www.heise.de/tp/')
    assert raw_req == raw_req_cmp

def test_build_request_invalid_host():
    with pytest.raises(ValueError):
        client._build_request('GET', 'http://www.spiegel.de/')

def test_response_context_manager():
    client = HTTPClient.from_url('http://www.google.fr/')
    r = None
    with client.get('/') as response:
        assert response.status_code == 200
        r = response
    assert r._sock is None # released

def test_client_ssl():
    client = HTTPClient('www.google.fr', ssl=True)
    assert client.port == 443
    response = client.get('/')
    assert response.status_code == 200
    body = response.read()
    assert len(body)

def test_ssl_fail_invalid_certificate():
    certs = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "onecert.pem")
    client = HTTPClient('www.google.fr', ssl_options={'ca_certs': certs})
    assert client.port == 443
    with pytest.raises(SSLError):
        client.get('/')

def test_multi_queries_greenlet_safe():
    client = HTTPClient('www.google.fr', concurrency=3)
    group = gevent.pool.Group()
    event = gevent.event.Event()

    def run(i):
        event.wait()
        response = client.get('/')
        return response, response.read()

    count = 0

    gevent.spawn_later(0.2, event.set)
    for response, content in group.imap_unordered(run, xrange(5)):
        assert response.status_code == 200
        assert len(content)
        count += 1
    assert count == 5


class StreamTestIterator(object):

    def __init__(self, sep, count):
        lines = [json.dumps({
                 'index': i,
                 'title': 'this is line %d' % i})
                 for i in xrange(0, count)]
        self.buf = sep.join(lines) + sep
        self.cursor = 0

    def __len__(self):
        return len(self.buf)

    def __iter__(self):
        return self

    def next(self):
        if self.cursor >= len(self.buf):
            raise StopIteration()

        gevent.sleep(0)
        pos = self.cursor + 10
        data = self.buf[self.cursor:pos]
        self.cursor = pos

        return data


def readline_iter(sock, addr):
    sock.recv(1024)
    iterator = StreamTestIterator("\n", 100)
    sock.sendall("HTTP/1.1 200 Ok\r\nConnection: close\r\n\r\n")
    for block in iterator:
        sock.sendall(block)

def test_readline():
    with server(readline_iter):
        client = HTTPClient(*listener, block_size=1)
        response = client.get('/')
        lines = []
        while True:
            line = response.readline("\n")
            if not line:
                break
            data = json.loads(line[:-1])
            lines.append(data)
        assert len(lines) == 100
        assert map(lambda x: x['index'], lines) == range(0, 100)

def readline_multibyte_sep(sock, addr):
    sock.recv(1024)
    iterator = StreamTestIterator("\r\n", 100)
    sock.sendall("HTTP/1.1 200 Ok\r\nConnection: close\r\n\r\n")
    for block in iterator:
        sock.sendall(block)

def test_readline_multibyte_sep():
    with server(readline_multibyte_sep):
        client = HTTPClient(*listener, block_size=1)
        response = client.get('/')
        lines = []
        while True:
            line = response.readline("\r\n")
            if not line:
                break
            data = json.loads(line[:-1])
            lines.append(data)
        assert len(lines) == 100
        assert map(lambda x: x['index'], lines) == range(0, 100)

def readline_multibyte_splitsep(sock, addr):
    sock.recv(1024)
    sock.sendall("HTTP/1.1 200 Ok\r\nConnection: close\r\n\r\n")
    sock.sendall('{"a": 1}\r')
    gevent.sleep(0)
    sock.sendall('\n{"a": 2}\r\n{"a": 3}\r\n')

def test_readline_multibyte_splitsep():
    with server(readline_multibyte_splitsep):
        client = HTTPClient(*listener, block_size=1)
        response = client.get('/')
        lines = []
        last_index = 0
        while True:
            line = response.readline("\r\n")
            if not line:
                break
            data = json.loads(line[:-2])
            assert data['a'] == last_index + 1
            last_index = data['a']
        len(lines) == 3

def internal_server_error(sock, addr):
    sock.recv(1024)
    head = 'HTTP/1.1 500 Internal Server Error\r\n' \
           'Connection: close\r\n' \
           'Content-Type: text/html\r\n' \
           'Content-Length: 135\r\n\r\n'

    body = '<html>\n  <head>\n    <title>Internal Server Error</title>\n  ' \
           '</head>\n  <body>\n    <h1>Internal Server Error</h1>\n    \n  ' \
           '</body>\n</html>\n\n'

    sock.sendall(head + body)
    sock.close()

def test_internal_server_error():
    with server(internal_server_error):
        client = HTTPClient(*listener)
        response = client.get('/')
        assert not response.should_keep_alive()
        assert response.should_close()
        body = response.read()
        assert len(body) == response.content_length



########NEW FILE########
__FILENAME__ = test_headers
import gevent
import gevent.monkey
gevent.monkey.patch_all()

import pytest

from cookielib import CookieJar
from urllib2 import Request
import string
import random
import time

from geventhttpclient.response import HTTPResponse
from geventhttpclient.header import Headers

MULTI_COOKIE_RESPONSE = """
HTTP/1.1 200 OK
Server: nginx
Date: Fri, 21 Sep 2012 18:49:35 GMT
Content-Type: text/html; charset=windows-1251
Connection: keep-alive
X-Powered-By: PHP/5.2.17
Set-Cookie: bb_lastvisit=1348253375; expires=Sat, 21-Sep-2013 18:49:35 GMT; path=/
Set-Cookie: bb_lastactivity=0; expires=Sat, 21-Sep-2013 18:49:35 GMT; path=/
Cache-Control: private
Pragma: private
Set-Cookie: bb_sessionhash=deleted; expires=Thu, 22-Sep-2011 18:49:34 GMT; path=/
Set-Cookie: bb_referrerid=deleted; expires=Thu, 22-Sep-2011 18:49:34 GMT; path=/
Set-Cookie: bb_userid=deleted; expires=Thu, 22-Sep-2011 18:49:34 GMT; path=/
Set-Cookie: bb_password=deleted; expires=Thu, 22-Sep-2011 18:49:34 GMT; path=/
Set-Cookie: bb_lastvisit=deleted; expires=Thu, 22-Sep-2011 18:49:34 GMT; path=/
Set-Cookie: bb_lastactivity=deleted; expires=Thu, 22-Sep-2011 18:49:34 GMT; path=/
Set-Cookie: bb_threadedmode=deleted; expires=Thu, 22-Sep-2011 18:49:34 GMT; path=/
Set-Cookie: bb_userstyleid=deleted; expires=Thu, 22-Sep-2011 18:49:34 GMT; path=/
Set-Cookie: bb_languageid=deleted; expires=Thu, 22-Sep-2011 18:49:34 GMT; path=/
Set-Cookie: bb_fbaccesstoken=deleted; expires=Thu, 22-Sep-2011 18:49:34 GMT; path=/
Set-Cookie: bb_fbprofilepicurl=deleted; expires=Thu, 22-Sep-2011 18:49:34 GMT; path=/
Set-Cookie: bb_sessionhash=abcabcabcabcabcabcabcabcabcabcab; path=/; HttpOnly
Set-Cookie: tapatalk_redirect3=deleted; expires=Thu, 22-Sep-2011 18:49:34 GMT; path=1; domain=forum.somewhere.com
Set-Cookie: bb_sessionhash=deleted; expires=Thu, 22-Sep-2011 18:49:34 GMT; path=1; domain=forum.somewhere.com
Set-Cookie: __utma=deleted; expires=Thu, 22-Sep-2011 18:49:34 GMT; path=1; domain=forum.somewhere.com
Set-Cookie: __utmb=deleted; expires=Thu, 22-Sep-2011 18:49:34 GMT; path=1; domain=forum.somewhere.com
Set-Cookie: __utmc=deleted; expires=Thu, 22-Sep-2011 18:49:34 GMT; path=1; domain=forum.somewhere.com
Set-Cookie: __utmz=deleted; expires=Thu, 22-Sep-2011 18:49:34 GMT; path=1; domain=forum.somewhere.com
Set-Cookie: vbulletin_collapse=deleted; expires=Thu, 22-Sep-2011 18:49:34 GMT; path=1; domain=forum.somewhere.com
Set-Cookie: bb_referrerid=deleted; expires=Thu, 22-Sep-2011 18:49:34 GMT; path=1; domain=forum.somewhere.com
Set-Cookie: bb_userid=deleted; expires=Thu, 22-Sep-2011 18:49:34 GMT; path=1; domain=forum.somewhere.com
Set-Cookie: bb_password=deleted; expires=Thu, 22-Sep-2011 18:49:34 GMT; path=1; domain=forum.somewhere.com
Set-Cookie: bb_lastvisit=deleted; expires=Thu, 22-Sep-2011 18:49:34 GMT; path=1; domain=forum.somewhere.com
Set-Cookie: bb_lastactivity=deleted; expires=Thu, 22-Sep-2011 18:49:34 GMT; path=1; domain=forum.somewhere.com
Set-Cookie: bb_threadedmode=deleted; expires=Thu, 22-Sep-2011 18:49:34 GMT; path=1; domain=forum.somewhere.com
Set-Cookie: bb_userstyleid=deleted; expires=Thu, 22-Sep-2011 18:49:34 GMT; path=1; domain=forum.somewhere.com
Set-Cookie: bb_languageid=deleted; expires=Thu, 22-Sep-2011 18:49:34 GMT; path=1; domain=forum.somewhere.com
Set-Cookie: bb_fbaccesstoken=deleted; expires=Thu, 22-Sep-2011 18:49:34 GMT; path=1; domain=forum.somewhere.com
Set-Cookie: bb_fbprofilepicurl=deleted; expires=Thu, 22-Sep-2011 18:49:34 GMT; path=1; domain=forum.somewhere.com
Content-Encoding: gzip
Content-Length: 26186

""".lstrip().replace('\n', '\r\n')
# Do not remove the final empty line!


def test_create_from_kwargs():
    h = Headers(ab=1, cd=2, ef=3, gh=4)
    assert len(h) == 4
    assert 'ab' in h

def test_create_from_iterator():
    h = Headers((x, x*5) for x in string.ascii_lowercase)
    assert len(h) == len(string.ascii_lowercase)
    
def test_create_from_dict():
    h = Headers(dict(ab=1, cd=2, ef=3, gh=4))
    assert len(h) == 4
    assert 'ab' in h

def test_create_from_list():
    h = Headers([('ab', 'A'), ('cd', 'B'), ('cookie', 'C'), ('cookie', 'D'), ('cookie', 'E')])
    assert len(h) == 5
    assert 'ab' in h
    assert len(h['cookie']) == 3
    assert h['cookie'][0] == 'C'
    assert h['cookie'][-1] == 'E'

def test_case_insensitivity():
    h = Headers({'Content-Type': 'text/plain'})
    h.add('Content-Encoding', 'utf8')
    for val in ('content-type', 'content-encoding'):
        assert val.upper() in h
        assert val.lower() in h
        assert val.capitalize() in h
        assert h.get(val.lower()) == h.get(val.upper()) == h.get(val.capitalize())
        del h[val.upper()]
        assert val.lower() not in h

def test_read_multiple_header():
    parser = HTTPResponse()
    parser.feed(MULTI_COOKIE_RESPONSE)
    headers = parser._headers_index
    assert len(headers['set-cookie']) == MULTI_COOKIE_RESPONSE.count('Set-Cookie')
    assert headers['set-cookie'][0].startswith('bb_lastvisit')
    assert headers['set-cookie'][-1].startswith('bb_fbprofilepicurl')

def test_cookielib_compatibility():
    cj = CookieJar()
    # Set time in order to be still valid in some years, when cookie strings expire
    cj._now = cj._policy._now = time.mktime((2012, 1, 1, 0, 0, 0, 0, 0, 0))

    request = Request('')
    parser = HTTPResponse()
    parser.feed(MULTI_COOKIE_RESPONSE)
    cookies = cj.make_cookies(parser, request)
    # Don't use extract_cookies directly, as time can not be set there manually for testing
    for cookie in cookies:
        if cj._policy.set_ok(cookie, request):
            cj.set_cookie(cookie)
    # Three valid, not expired cookies placed
    assert len(list(cj)) == 3

def test_compatibility_with_previous_API_read():
    parser = HTTPResponse()
    parser.feed(MULTI_COOKIE_RESPONSE)
    for single_item in ('content-encoding', 'content-type', 'content-length', 'cache-control', 'connection'):
        assert isinstance(parser[single_item], basestring)
        assert isinstance(parser.get(single_item), basestring)

def test_compatibility_with_previous_API_write():
    h = Headers()
    h['asdf'] = 'jklm'
    h['asdf'] = 'dfdf'
    # Lists only if necessary
    assert h['asdf'] == 'dfdf'
    
def test_copy():
    rnd_txt = lambda length: ''.join(random.choice(string.ascii_letters) for _ in xrange(length))
    h = Headers((rnd_txt(10), rnd_txt(50)) for _ in xrange(100))
    c = h.copy()
    assert h is not c
    assert len(h) == len(c)
    assert set(h.keys()) == set(c.keys())
    assert h == c
    assert type(h) is type(c)
    for _ in xrange(100):
        rnd_key = rnd_txt(9)
        c[rnd_key] = rnd_txt(10)
        assert rnd_key in c
        assert rnd_key not in h
    
def test_fieldname_string_enforcement():
    with pytest.raises(TypeError):
        Headers({3: 3})
    h = Headers()
    with pytest.raises(TypeError):
        h[3] = 5
    with pytest.raises(TypeError):
        h.add(3, 4)
    with pytest.raises(TypeError):
        del h[3]
        

if __name__ == '__main__':
    test_copy()
    test_cookielib_compatibility()

def test_header_replace():
    d = {}
    d['Content-Type'] = "text/plain"
    d['content-type'] = "text/html"
    assert d['content-type'] == "text/html"

########NEW FILE########
__FILENAME__ = test_httplib
import pytest
from httplib import HTTPException
from geventhttpclient.httplib import HTTPConnection
import gevent.server
from contextlib import contextmanager

listener = ('127.0.0.1', 54322)

@contextmanager
def server(handler):
    server = gevent.server.StreamServer(
        listener,
        handle=handler)
    server.start()
    try:
        yield
    finally:
        server.stop()

def wrong_response_status_line(sock, addr):
    sock.recv(4096)
    sock.sendall('HTTP/1.1 apfais df0 asdf\r\n\r\n')

def test_httplib_exception():
    with server(wrong_response_status_line):
        connection = HTTPConnection(*listener)
        connection.request("GET", '/')
        with pytest.raises(HTTPException):
            connection.getresponse()

def success_response(sock, addr):
    sock.recv(4096)
    sock.sendall("HTTP/1.1 200 Ok\r\n"
               "Content-Type: text/plain\r\n"
               "Content-Length: 12\r\n\r\n"
               "Hello World!")

def test_success_response():
    with server(success_response):
        connection = HTTPConnection(*listener)
        connection.request("GET", "/")
        response = connection.getresponse()
        assert response.should_keep_alive()
        assert response.message_complete
        assert not response.should_close()
        assert response.read() == 'Hello World!'
        assert response.content_length == 12


########NEW FILE########
__FILENAME__ = test_keep_alive
from geventhttpclient.response import HTTPResponse
from geventhttpclient._parser import HTTPParseError
import pytest


def test_simple():
    response = HTTPResponse()
    response.feed("""HTTP/1.1 200 Ok\r\nContent-Length: 0\r\n\r\n""")
    assert response.headers_complete
    assert response.message_complete
    assert response.should_keep_alive()
    assert not response.should_close()
    assert response.status_code == 200

def test_keep_alive_http_10():
    response = HTTPResponse()
    response.feed("""HTTP/1.0 200 Ok\r\n\r\n""")
    response.feed("")
    assert response.headers_complete
    assert response.message_complete
    assert not response.should_keep_alive()
    assert response.should_close()
    assert response.status_code == 200

def test_keep_alive_bodyless_response_with_body():
    response = HTTPResponse(method='HEAD')
    response.feed("HTTP/1.1 200 Ok\r\n\r\n")
    assert response.message_complete
    assert response.should_keep_alive()

    response = HTTPResponse(method='HEAD')
    with pytest.raises(HTTPParseError):
        response.feed(
            """HTTP/1.1 200 Ok\r\nContent-Length: 10\r\n\r\n0123456789""")
    assert not response.should_keep_alive()
    assert response.should_close()

def test_keep_alive_bodyless_10x_request_with_body():
    response = HTTPResponse()
    response.feed("""HTTP/1.1 100 Continue\r\n\r\n""")
    assert response.should_keep_alive()

    response = HTTPResponse()
    response.feed("""HTTP/1.1 100 Continue\r\nTransfer-Encoding: chunked\r\n\r\n""")
    assert response.should_keep_alive()
    assert response.should_close()

def test_close_connection_and_no_content_length():
    response = HTTPResponse()
    response.feed("HTTP/1.1 200 Ok\r\n"
                "Connection: close\r\n\r\n"
                "Hello World!")
    assert response._body_buffer == bytearray("Hello World!")
    assert not response.should_keep_alive()
    assert response.should_close()


########NEW FILE########
__FILENAME__ = test_network_failures
import pytest
from httplib import HTTPException #@UnresolvedImport
from geventhttpclient import HTTPClient
import gevent.server
import gevent.socket
from contextlib import contextmanager

CRLF = "\r\n"

listener = ('127.0.0.1', 54323)

@contextmanager
def server(handler):
    server = gevent.server.StreamServer(
        listener,
        handle=handler)
    server.start()
    try:
        yield
    finally:
        server.stop()

def wrong_response_status_line(sock, addr):
    sock.recv(4096)
    sock.sendall('HTTP/1.1 apfais df0 asdf\r\n\r\n')

def test_exception():
    with server(wrong_response_status_line):
        connection = HTTPClient(*listener)
        with pytest.raises(HTTPException):
            connection.get('/')

def close(sock, addr):
    sock.close()

def test_close():
    with server(close):
        client = HTTPClient(*listener)
        with pytest.raises(HTTPException):
            client.get('/')

def close_after_recv(sock, addr):
    sock.recv(4096)
    sock.close()

def test_close_after_recv():
    with server(close_after_recv):
        client = HTTPClient(*listener)
        with pytest.raises(HTTPException):
            client.get('/')

def timeout_recv(sock, addr):
    sock.recv(4096)
    gevent.sleep(1)

def test_timeout_recv():
    with server(timeout_recv):
        connection = HTTPClient(*listener, network_timeout=0.1)
        with pytest.raises(gevent.socket.timeout):
            connection.request("GET", '/')

def timeout_send(sock, addr):
    gevent.sleep(1)

def test_timeout_send():
    with server(timeout_send):
        connection = HTTPClient(*listener, network_timeout=0.1)
        with pytest.raises(gevent.socket.timeout):
            connection.request("GET", '/')

def close_during_content(sock, addr):
    sock.recv(4096)
    sock.sendall("""HTTP/1.1 200 Ok\r\nContent-Length: 100\r\n\r\n""")
    sock.close()

def test_close_during_content():
    with server(close_during_content):
        client = HTTPClient(*listener, block_size=1)
        response = client.get('/')
        with pytest.raises(HTTPException):
            response.read()

def content_too_small(sock, addr):
    sock.recv(4096)
    sock.sendall("""HTTP/1.1 200 Ok\r\nContent-Length: 100\r\n\r\ncontent""")
    gevent.sleep(10)

def test_content_too_small():
    with server(content_too_small):
        client = HTTPClient(*listener, network_timeout=0.2)
        with pytest.raises(gevent.socket.timeout):
            response = client.get('/')
            response.read()

def close_during_chuncked_readline(sock, addr):
    sock.recv(4096)
    sock.sendall('HTTP/1.1 200 Ok\r\nTransfer-Encoding: chunked\r\n\r\n')

    chunks = ['This is the data in the first chunk\r\n',
        'and this is the second one\r\n',
        'con\r\n']

    for chunk in chunks:
        gevent.sleep(0.1)
        sock.sendall(hex(len(chunk))[2:] + CRLF + chunk + CRLF)
    sock.close()

def test_close_during_chuncked_readline():
    with server(close_during_chuncked_readline):
        client = HTTPClient(*listener)
        response = client.get('/')
        assert response['transfer-encoding'] == 'chunked'
        chunks = []
        with pytest.raises(HTTPException):
            data = 'enter_loop'
            while data:
                data = response.readline()
                chunks.append(data)
        assert len(chunks) == 3

def timeout_during_chuncked_readline(sock, addr):
    sock.recv(4096)
    sock.sendall('HTTP/1.1 200 Ok\r\nTransfer-Encoding: chunked\r\n\r\n')

    chunks = ['This is the data in the first chunk\r\n',
        'and this is the second one\r\n',
        'con\r\n']

    for chunk in chunks:
        sock.sendall(hex(len(chunk))[2:] + CRLF + chunk + CRLF)
    gevent.sleep(2)
    sock.close()

def test_timeout_during_chuncked_readline():
    with server(timeout_during_chuncked_readline):
        client = HTTPClient(*listener, network_timeout=0.1)
        response = client.get('/')
        assert response['transfer-encoding'] == 'chunked'
        chunks = []
        with pytest.raises(gevent.socket.timeout):
            data = 'enter_loop'
            while data:
                data = response.readline()
                chunks.append(data)
        assert len(chunks) == 3


########NEW FILE########
__FILENAME__ = test_parser
from geventhttpclient.response import HTTPResponse
from geventhttpclient._parser import HTTPParseError
from cStringIO import StringIO
import pytest

from functools import wraps
import sys

RESPONSE = 'HTTP/1.1 301 Moved Permanently\r\nLocation: http://www.google.fr/\r\nContent-Type: text/html; charset=UTF-8\r\nDate: Thu, 13 Oct 2011 15:03:12 GMT\r\nExpires: Sat, 12 Nov 2011 15:03:12 GMT\r\nCache-Control: public, max-age=2592000\r\nServer: gws\r\nContent-Length: 218\r\nX-XSS-Protection: 1; mode=block\r\n\r\n<HTML><HEAD><meta http-equiv="content-type" content="text/html;charset=utf-8">\n<TITLE>301 Moved</TITLE></HEAD><BODY>\n<H1>301 Moved</H1>\nThe document has moved\n<A HREF="http://www.google.fr/">here</A>.\r\n</BODY></HTML>\r\n'

# borrowed from gevent
# sys.gettotalrefcount is available only with python built with debug flag on
gettotalrefcount = getattr(sys, 'gettotalrefcount', None)


def wrap_refcount(method):
    if gettotalrefcount is None:
        return method
    @wraps(method)
    def wrapped(*args, **kwargs):
        import gc
        gc.disable()
        gc.collect()
        deltas = []
        d = None
        try:
            for _ in xrange(4):
                d = gettotalrefcount()
                method(*args, **kwargs)
                if 'urlparse' in sys.modules:
                    sys.modules['urlparse'].clear_cache()
                d = gettotalrefcount() - d
                deltas.append(d)
                if deltas[-1] == 0:
                    break
            else:
                raise AssertionError('refcount increased by %r' % (deltas, ))
        finally:
            gc.collect()
            gc.enable()
    return wrapped

@wrap_refcount
def test_parse():
    parser = HTTPResponse()
    assert parser.feed(RESPONSE), len(RESPONSE)
    assert parser.message_begun
    assert parser.headers_complete
    assert parser.message_complete

@wrap_refcount
def test_parse_small_blocks():
    parser = HTTPResponse()
    parser.feed(RESPONSE)
    response = StringIO(RESPONSE)
    while not parser.message_complete:
        data = response.read(10)
        parser.feed(data)

    assert parser.message_begun
    assert parser.headers_complete
    assert parser.message_complete
    assert parser.should_keep_alive()
    assert parser.status_code == 301
    assert sorted(parser.items()) == [
        ('cache-control', 'public, max-age=2592000'),
        ('content-length', '218'),
        ('content-type', 'text/html; charset=UTF-8'),
        ('date', 'Thu, 13 Oct 2011 15:03:12 GMT'),
        ('expires', 'Sat, 12 Nov 2011 15:03:12 GMT'),
        ('location', 'http://www.google.fr/'),
        ('server', 'gws'),
        ('x-xss-protection', '1; mode=block'),
    ]

@wrap_refcount
def test_parse_error():
    response =  HTTPResponse()
    try:
        response.feed("HTTP/1.1 asdf\r\n\r\n")
        response.feed("")
        assert response.status_code, 0
        assert response.message_begun
    except HTTPParseError as e:
        assert 'invalid HTTP status code' in str(e)
    else:
        assert False, "should have raised"

@wrap_refcount
def test_incomplete_response():
    response = HTTPResponse()
    response.feed("""HTTP/1.1 200 Ok\r\nContent-Length:10\r\n\r\n1""")
    with pytest.raises(HTTPParseError):
        response.feed("")
    assert response.should_keep_alive()
    assert response.should_close()

@wrap_refcount
def test_response_too_long():
    response = HTTPResponse()
    data = """HTTP/1.1 200 Ok\r\nContent-Length:1\r\n\r\ntoolong"""
    with pytest.raises(HTTPParseError):
        response.feed(data)

@wrap_refcount
def test_on_body_raises():
    response = HTTPResponse()

    def on_body(buf):
        raise RuntimeError('error')

    response._on_body = on_body
    with pytest.raises(RuntimeError):
        response.feed(RESPONSE)

@wrap_refcount
def test_on_message_begin():
    response = HTTPResponse()

    def on_message_begin():
        raise RuntimeError('error')

    response._on_message_begin = on_message_begin
    with pytest.raises(RuntimeError):
        response.feed(RESPONSE)



########NEW FILE########
__FILENAME__ = test_ssl
from contextlib import contextmanager
import pytest
import gevent.server
import gevent.socket
import gevent.ssl
import os.path
from geventhttpclient import HTTPClient
from backports.ssl_match_hostname import CertificateError

BASEDIR = os.path.dirname(__file__)
KEY = os.path.join(BASEDIR, 'server.key')
CERT = os.path.join(BASEDIR, 'server.crt')


listener = ('127.0.0.1', 54323)

@contextmanager
def server(handler, backlog=1):
    server = gevent.server.StreamServer(
        listener,
        backlog=backlog,
        handle=handler,
        keyfile=KEY,
        certfile=CERT)
    server.start()
    try:
        yield
    finally:
        server.stop()

@contextmanager
def timeout_connect_server():
    sock = gevent.socket.socket(gevent.socket.AF_INET,
        gevent.socket.SOCK_STREAM, 0)
    sock = gevent.ssl.wrap_socket(sock, keyfile=KEY, certfile=CERT)
    sock.setsockopt(gevent.socket.SOL_SOCKET, gevent.socket.SO_REUSEADDR, 1)
    sock.bind(listener)
    sock.listen(1)

    def run(sock):
        conns = []
        while True:
            conn, addr = sock.accept()
            conns.append(conns)
            conn.recv(1024)
            gevent.sleep(10)

    job = gevent.spawn(run, sock)
    try:
        yield
    finally:
        job.kill()

def simple_ssl_response(sock, addr):
    sock.recv(1024)
    sock.sendall('HTTP/1.1 200 Ok\r\nConnection: close\r\n\r\n')
    sock.close()

def test_simple_ssl():
    with server(simple_ssl_response):
        http = HTTPClient(*listener, insecure=True, ssl=True, ssl_options={'ca_certs': CERT})
        response = http.get('/')
        assert response.status_code == 200
        response.read()

def timeout_on_connect(sock, addr):
    sock.recv(1024)
    sock.sendall('HTTP/1.1 200 Ok\r\nContent-Length: 0\r\n\r\n')

def test_timeout_on_connect():
    with timeout_connect_server():
        http = HTTPClient(*listener,
            insecure=True, ssl=True, ssl_options={'ca_certs': CERT})

        def run(http, wait_time=100):
            response = http.get('/')
            gevent.sleep(wait_time)
            response.read()

        gevent.spawn(run, http)
        gevent.sleep(0)

        e = None
        try:
            http2 = HTTPClient(*listener,
                insecure=True,
                ssl=True,
                connection_timeout=0.1,
                ssl_options={'ca_certs': CERT})
            http2.get('/')
        except gevent.ssl.SSLError as error:
            e = error
        except gevent.socket.timeout as error:
            e = error
        except:
            raise

        assert e is not None, 'should have raised'
        if isinstance(e, gevent.ssl.SSLError):
            assert str(e).endswith("handshake operation timed out")

def network_timeout(sock, addr):
    sock.recv(1024)
    gevent.sleep(10)
    sock.sendall('HTTP/1.1 200 Ok\r\nContent-Length: 0\r\n\r\n')

def test_network_timeout():
    with server(network_timeout):
        http = HTTPClient(*listener, ssl=True, insecure=True,
            network_timeout=0.1, ssl_options={'ca_certs': CERT})
        with pytest.raises(gevent.ssl.SSLError):
            response = http.get('/')
            assert response.status_code == 0, 'should have timed out.'

def test_verify_hostname():
    with server(simple_ssl_response):
        http = HTTPClient(*listener, ssl=True, ssl_options={'ca_certs': CERT})
        with pytest.raises(CertificateError):
            http.get('/')

########NEW FILE########
__FILENAME__ = test_url
from geventhttpclient.url import URL

url_full = 'http://getgauss.com/subdir/file.py?param=value&other=true#frag'
url_path_only = '/path/to/something?param=value&other=true'

def test_simple_url():
    url = URL(url_full)
    assert url.path == '/subdir/file.py'
    assert url.host == 'getgauss.com'
    assert url.port == 80
    assert url['param'] == 'value'
    assert url['other'] == 'true'
    assert url.fragment == 'frag'

def test_path_only():
    url = URL(url_path_only)
    assert url.host == ''
    assert url.port == None
    assert url.path == '/path/to/something'
    assert url['param'] == 'value'
    assert url['other'] == 'true'
    
def test_empty():
    url = URL()
    assert url.host == ''
    assert url.port == 80
    assert url.query == {}
    assert url.fragment == ''
    assert url.netloc == ''
    assert str(url) == 'http:///'

def test_consistent_reparsing():
    for surl in (url_full, url_path_only):
        url = URL(surl)
        reparsed = URL(str(url))
        for attr in URL.__slots__:
            assert getattr(reparsed, attr) == getattr(url, attr)
            
def test_redirection_abs_path():
    url = URL(url_full)
    updated = url.redirect('/test.html')
    assert updated.host == url.host
    assert updated.port == url.port
    assert updated.path == '/test.html'
    assert updated.query == {}
    assert updated.fragment == ''
    
def test_redirection_rel_path():
    url = URL(url_full)
    for redir in ('test.html?key=val', 'folder/test.html?key=val'):
        updated = url.redirect(redir)
        assert updated.host == url.host
        assert updated.port == url.port
        assert updated.path.startswith('/subdir/')
        assert updated.path.endswith(redir.split('?', 1)[0])
        assert updated.query == {'key': 'val'}
        assert updated.fragment == ''
    
def test_redirection_full_path():
    url_full2_plain = 'http://google.de/index'
    url = URL(url_full)
    updated = url.redirect(url_full2_plain)
    url_full2 = URL(url_full2_plain)
    for attr in URL.__slots__:
        assert getattr(updated, attr) == getattr(url_full2, attr)
    assert str(url_full2) == url_full2_plain
    
def test_set_safe_encoding():
    class SafeModURL(URL):
        quoting_safe = '*'
    surl = '/path/to/something?param=value&other=*'

    assert URL(surl).query_string == 'other=%2A&param=value'
    assert SafeModURL(surl).query_string == 'other=*&param=value'
    URL.quoting_safe = '*'
    assert URL(surl).query_string == 'other=*&param=value'
    URL.quoting_safe = ''

def test_equality():
    assert URL('https://example.com/') != URL('http://example.com/')
    assert URL('http://example.com/') == URL('http://example.com/')

if __name__ == '__main__':
    test_redirection_abs_path()
    test_redirection_rel_path()
    test_redirection_full_path()
    
########NEW FILE########
__FILENAME__ = test_useragent
'''
Created on 05.11.2012

@author: nimrod
'''
import gevent
import gevent.monkey
gevent.monkey.patch_all()

import pytest
import os
import sys
import filecmp

from geventhttpclient.useragent import UserAgent, RetriesExceeded, ConnectionError


USER_AGENT = 'Mozilla/5.0 (X11; U; Linux i686; de; rv:1.9.2.17) Gecko/20110422 Ubuntu/10.04 (lucid) Firefox/3.6.17'
DEFAULT_HEADERS = {
    'User-Agent': USER_AGENT,
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Encoding': 'gzip,deflate',
    'Connection': 'keep-alive'}


def test_open_multiple_domains():
    ua = UserAgent(max_retries=1)
    for domain in ('google.com', 'microsoft.com'):
        try:
            r = ua.urlopen('http://' + domain + '/')
        except RetriesExceeded:
            print "Redirect failed"
        else:
            print r.headers

def test_open_multiple_domains_parallel():
    ua = UserAgent(max_retries=1, headers=DEFAULT_HEADERS)
    domains = 'google.com', 'microsoft.com', 'debian.org', 'spiegel.de', 'heise.de'
    get_domain_headers = lambda d: (d, ua.urlopen('http://' + d).headers)
    gp = gevent.pool.Group()
    for domain, hdr in gp.imap_unordered(get_domain_headers, domains):
        print domain
        print hdr
        print

dl_url = 'http://de.archive.ubuntu.com/ubuntu/pool/universe/v/vlc/vlc_2.0.4-0ubuntu1_i386.deb'
def test_download():
    fpath = '/tmp/_test_download'
    if os.path.exists(fpath):
        os.remove(fpath)
    ua = UserAgent(max_retries=3)
    try:
        r = ua.download(dl_url, fpath)
    except RetriesExceeded:
        print "Redirect failed"
    except ConnectionError as e:
        print "Not found: %s %s" % (type(e).__name__, e)
    else:
        fl = os.path.getsize(fpath)
        cl = r.headers.get('Content-Length')
        cl = int(cl) if cl else None
        assert cl == fl
        len_str = 'OK' if cl == fl else 'CL: %s / FL: %s' % (cl, fl)
        print "Download finished:", len_str

def test_download_parts():
    fpath = '/tmp/_test_download'
    fpath_part = '/tmp/_test_download_part'
    part_size = 400000
    ua = UserAgent(max_retries=3)
    if not os.path.exists(fpath) or os.path.getsize(fpath) < part_size:
        ua.download(dl_url, fpath)
    assert os.path.getsize(fpath) > part_size
    with open(fpath_part, 'w') as chunk:
        chunk.write(open(fpath).read(part_size))
        chunk.flush()
    assert part_size == os.path.getsize(fpath_part)

    try:
        r = ua.download(dl_url, fpath_part, resume=True)
    except RetriesExceeded:
        print "Redirect failed"
    except ConnectionError as e:
        print "Not found: %s %s" % (type(e).__name__, e)
    else:
        assert len(r) + part_size == os.path.getsize(fpath)
        assert os.path.getsize(fpath) == os.path.getsize(fpath_part)
        assert filecmp.cmp(fpath, fpath_part)
        print "Resuming download finished successful"
    os.remove(fpath)
    os.remove(fpath_part)

def test_gzip():
    ua = UserAgent(max_retries=1, headers=DEFAULT_HEADERS)
    resp = ua.urlopen('https://google.com')
    assert resp.headers.get('content-encoding') == 'gzip'
    cl = int(resp.headers.get('content-length', 0))
    if cl:
        # Looks like google dropped content-length recently
        assert cl > 5000
        assert len(resp.content) > 2 * cl
    # Check, if unzip produced readable output
    for word in ('doctype', 'html', 'function', 'script', 'google'):
        assert word in resp.content

def test_error_handling():
    ua = UserAgent(max_retries=1)
    try:
        1 / 0
    except ZeroDivisionError as err:
        err.trace = sys.exc_info()[2]
    with pytest.raises(ZeroDivisionError) as cm:
        ua._handle_error(err)
    assert str(cm.traceback[-1]).strip().endswith('1 / 0')


if __name__ == '__main__':
#    test_open_multiple_domains_parallel()
#    test_gzip()
#    test_download()
#    test_download_parts()
    test_error_handling()

########NEW FILE########
__FILENAME__ = url
import urlparse
from urllib import quote_plus


class URL(object):
    """ A mutable URL class

    You build it from a url string.
    >>> url = URL('http://getgauss.com/urls?param=asdfa')
    >>> url
    URL(http://getgauss.com/urls?param=asdfa)

    You cast it to a tuple, it returns the same tuple as `urlparse.urlsplit`.
    >>> tuple(url)
    ('http', 'getgauss.com', '/urls', 'param=asdfa', '')

    You can cast it as a string.
    >>> str(url)
    'http://getgauss.com/urls?param=asdfa'

    You can manipulate query arguments.
    >>> url.query['auth_token'] = 'asdfaisdfuasdf'
    >>> url
    URL(http://getgauss.com/urls?auth_token=asdfaisdfuasdf&param=asdfa)

    You can change attributes.
    >>> url.host = 'infrae.com'
    >>> url
    URL(http://infrae.com/urls?auth_token=asdfaisdfuasdf&param=asdfa)
    """

    DEFAULT_PORTS = {
        'http': 80,
        'https': 443
    }

    __slots__ = ('scheme', 'host', 'port', 'path', 'query', 'fragment')
    quoting_safe = ''

    def __init__(self, url=None):
        if url is not None:
            self.scheme, netloc, self.path, \
                query, self.fragment = urlparse.urlsplit(url)
        else:
            self.scheme, netloc, self.path, query, self.fragment = \
                'http', '', '/', '', ''
        self.port = None
        self.host = None
        if netloc is not None:
            info = netloc.rsplit(':', 1)
            if len(info) == 2:
                self.host, port = info
                self.port = int(port)
            else:
                self.host = info[0]
                self.port = self.DEFAULT_PORTS.get(self.scheme)
            # for IPv6 hosts
            self.host = self.host.strip('[]')
        if not self.path:
            self.path = "/"
        self.query = {}
        for key, value in urlparse.parse_qs(query).iteritems():
            if len(value) > 1:
                self.query[key] = value
            else:
                self.query[key] = value[0]

    @property
    def netloc(self):
        buf = self.host
        if self.port is None:
            return buf
        elif self.DEFAULT_PORTS.get(self.scheme) == self.port:
            return buf
        buf += ":" + str(self.port)
        return buf

    def __copy__(self):
        return URL(str(self))

    def __repr__(self):
        return "URL(%s)" % str(self)

    def __iter__(self):
        return iter((self.scheme, self.netloc, self.path,
                self.query_string, self.fragment))

    def __str__(self):
        return urlparse.urlunsplit(tuple(self))

    def __eq__(self, other):
        return str(self) == str(other)

    @property
    def query_string(self):
        params = []
        for key, value in self.query.iteritems():
            if isinstance(value, list):
                for item in value:
                    params.append("%s=%s" % (
                        quote_plus(key), quote_plus(str(item), safe=self.quoting_safe)))
            else:
                params.append("%s=%s" % (
                    quote_plus(key), quote_plus(str(value), safe=self.quoting_safe)))
        if params:
            return "&".join(params)
        return ''

    @property
    def request_uri(self):
        query = self.query_string
        if not query:
            return self.path
        return self.path + '?' + query

    def __getitem__(self, key):
        return self.query[key]

    def get(self, key):
        return self.query.get(key)

    def __setitem__(self, key, value):
        self.query[key] = value
        return value

    def append_to_path(self, value):
        if value.startswith('/'):
            if self.path.endswith('/'):
                self.path += value[1:]
                return self.path
        elif not self.path.endswith("/"):
            self.path += "/" + value
            return self.path

        self.path += value
        return self.path

    def redirect(self, other):
        other = type(self)(other)
        if not other.host:
            other.scheme = self.scheme
            other.host = self.host
            other.port = self.port
        if not other.path.startswith('/'):
            if self.path.endswith('/'):
                other.path = self.path + other.path
            else:
                other.path = self.path.rsplit('/', 1)[0] + '/' + other.path
        return other

########NEW FILE########
__FILENAME__ = useragent
'''
Created on 04.11.2012

@author: nimrod
'''
import socket
import errno
import sys
import ssl
import zlib
import os
import cStringIO
from urllib import urlencode

import gevent
try:
    from gevent.dns import DNSError
except ImportError:
    class DNSError(StandardError): pass

from url import URL
from client import HTTPClient, HTTPClientPool


class ConnectionError(Exception):
    def __init__(self, url, *args, **kwargs):
        self.url = url
        self.__dict__.update(kwargs)
        if args and isinstance(args[0], basestring):
            try:
                self.text = args[0] % args[1:]
            except TypeError:
                self.text = args[0] + ': ' + str(args[1:]) if args else ''
        else:
            self.text = str(args[0]) if len(args) == 1 else ''
        if kwargs:
            self.text += ', ' if self.text else ''
            self.text += ', '.join("%s=%s" % (key, val) for key, val in kwargs.iteritems())
        else:
            self.text = ''

    def __str__(self):
        if self.text:
            return "URL %s: %s" % (self.url, self.text)
        else:
            return "URL %s" % self.url


class RetriesExceeded(ConnectionError):
    pass


class BadStatusCode(ConnectionError):
    pass


class EmptyResponse(ConnectionError):
    pass


class CompatRequest(object):
    """ urllib / cookielib compatible request class. 
        See also: http://docs.python.org/library/cookielib.html 
    """
    def __init__(self, url, method='GET', headers=None, payload=None):
        self.set_url(url)
        self.original_host = self.url_split.netloc
        self.method = method
        self.headers = headers
        self.payload = payload

    def set_url(self, url):
        if isinstance(url, URL):
            self.url = str(url)
            self.url_split = url
        else:
            self.url = url
            self.url_split = URL(self.url)

    def get_full_url(self):
        return self.url

    def get_host(self):
        self.url_split.netloc

    def get_type(self):
        self.url_split.scheme

    def get_origin_req_host(self):
        self.original_host

    def is_unverifiable(self):
        """ See http://tools.ietf.org/html/rfc2965.html. Not fully implemented! 
        """
        return False

    def get_header(self, header_name, default=None):
        return self.headers.get(header_name, default)

    def has_header(self, header_name):
        return header_name in self.headers

    def header_items(self):
        return self.headers.items()

    def add_unredirected_header(self, key, val):
        self.headers.add(key, val)


class CompatResponse(object):
    """ Adapter for urllib responses with some extensions 
    """
    __slots__ = 'headers', '_response', '_request', '_sent_request', '_cached_content'

    def __init__(self, ghc_response, request=None, sent_request=None):
        self._response = ghc_response
        self._request = request
        self._sent_request = sent_request
        self.headers = self._response._headers_index

    @property
    def status(self):
        """ The returned http status 
        """
        # TODO: Should be a readable string
        return str(self.status_code)

    @property
    def status_code(self):
        """ The http status code as plain integer 
        """
        return self._response.get_code()

    @property
    def stream(self):
        return self._response

    def read(self, n=None):
        """ Read n bytes from the response body 
        """
        return self._response.read(n)

    def readline(self):
        return self._response.readline()

    def release(self):
        return self._response.release()

    def unzipped(self, gzip=True):
        bodystr = self._response.read()
        if gzip:
            return zlib.decompress(bodystr, 16 + zlib.MAX_WBITS)
        else:
            # zlib only provides the zlib compress format, not the deflate format;
            # so on top of all there's this workaround:
            try:
                return zlib.decompress(bodystr, -zlib.MAX_WBITS)
            except zlib.error:
                return zlib.decompress(bodystr)

    @property
    def content(self):
        """ Unzips if necessary and buffers the received body. Careful with large files! 
        """
        try:
            return self._cached_content
        except AttributeError:
            self._cached_content = self._content()
            return self._cached_content

    def _content(self):
        try:
            content_type = self.headers.getheaders('content-encoding')[0].lower()
        except IndexError:
            # No content-encoding header set
            content_type = 'identity'

        if  content_type == 'gzip':
            ret = self.unzipped(gzip=True)
        elif content_type == 'deflate':
            ret = self.unzipped(gzip=False)
        elif content_type == 'identity':
            ret = self._response.read()
        elif content_type == 'compress':
            raise ValueError("Compression type not supported: %s" % content_type)
        else:
            raise ValueError("Unknown content encoding: %s" % content_type)

        self.release()
        return ret

    def __len__(self):
        """ The content lengths as should be returned from the headers 
        """
        try:
            return int(self.headers.getheaders('content-length')[0])
        except (IndexError, ValueError):
            return len(self.content)

    def __nonzero__(self):
        """ If we have an empty response body, we still don't want to evaluate as false 
        """
        return True

    def info(self):
        """ Adaption to cookielib: Alias for headers  
        """
        return self.headers

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.release()


class RestkitCompatResponse(CompatResponse):
    """ Some extra lines to also serve as a drop in replacement for restkit 
    """
    def body_string(self):
        return self.content

    def body_stream(self):
        return self._response

    @property
    def status_int(self):
        return self.status_code


class UserAgent(object):
    response_type = CompatResponse
    request_type = CompatRequest
    valid_response_codes = set([200, 206, 301, 302, 303, 307])

    def __init__(self, max_redirects=3, max_retries=3, retry_delay=0,
                 cookiejar=None, headers=None, **kwargs):
        self.max_redirects = int(max_redirects)
        self.max_retries = int(max_retries)
        self.retry_delay = retry_delay
        self.default_headers = HTTPClient.DEFAULT_HEADERS.copy()
        if headers:
            self.default_headers.update(headers)
        self.cookiejar = cookiejar
        self.clientpool = HTTPClientPool(**kwargs)

    def _make_request(self, url, method='GET', headers=None, payload=None):
        req_headers = self.default_headers.copy()
        if headers:
            req_headers.update(headers)
        if payload:
            # Adjust headers depending on payload content
            content_type = req_headers.get('content-type', None)
            if not content_type and isinstance(payload, dict):
                req_headers['content-type'] = "application/x-www-form-urlencoded; charset=utf-8"
                payload = urlencode(payload)
                req_headers['content-length'] = len(payload)
            elif not content_type:
                req_headers['content-type'] = 'application/octet-stream'
                payload = payload if isinstance(payload, basestring) else str(payload)
                req_headers['content-length'] = len(payload)
            elif content_type.startswith("multipart/form-data"):
                # See restkit for some example implementation
                # TODO: Implement it
                raise NotImplementedError
            else:
                payload = payload if isinstance(payload, basestring) else str(payload)
                req_headers['content-length'] = len(payload)
        return CompatRequest(url, method=method, headers=req_headers, payload=payload)

    def _urlopen(self, request):
        client = self.clientpool.get_client(request.url_split)
        resp = client.request(request.method, request.url_split.request_uri,
                              body=request.payload, headers=request.headers)
        return CompatResponse(resp, request=request, sent_request=resp._sent_request)

    def _verify_status(self, status_code, url=None):
        """ Hook for subclassing 
        """
        if status_code not in self.valid_response_codes:
            raise BadStatusCode(url, code=status_code)

    def _handle_error(self, e, url=None):
        """ Hook for subclassing. Raise the error to interrupt further retrying,
            return it to continue retries and save the error, when retries
            exceed the limit.
            Temporary errors should be swallowed here for automatic retries.
        """
        if isinstance(e, (socket.timeout, gevent.Timeout)):
            return e
        elif isinstance(e, (socket.error, DNSError)) and \
                e.errno in set([errno.ETIMEDOUT, errno.ENOLINK, errno.ENOENT, errno.EPIPE]):
            return e
        elif isinstance(e, ssl.SSLError) and 'read operation timed out' in str(e):
            return e
        elif isinstance(e, EmptyResponse):
            return e
        raise e, None, sys.exc_info()[2]

    def _handle_retries_exceeded(self, url, last_error=None):
        """ Hook for subclassing 
        """
        raise RetriesExceeded(url, self.max_retries, original=last_error)

    def urlopen(self, url, method='GET', response_codes=valid_response_codes,
                headers=None, payload=None, to_string=False, debug_stream=None, **kwargs):
        """ Open an URL, do retries and redirects and verify the status code 
        """
        # POST or GET parameters can be passed in **kwargs
        if kwargs:
            if not payload:
                payload = kwargs
            elif isinstance(payload, dict):
                payload.update(kwargs)

        req = self._make_request(url, method=method, headers=headers, payload=payload)
        for retry in xrange(self.max_retries):
            if retry > 0 and self.retry_delay:
                # Don't wait the first time and skip if no delay specified
                gevent.sleep(self.retry_delay)
            for _ in xrange(self.max_redirects):
                if self.cookiejar is not None:
                    # Check against None to avoid issues with empty cookiejars
                    self.cookiejar.add_cookie_header(req)

                try:
                    resp = self._urlopen(req)
                except gevent.GreenletExit:
                    raise
                except BaseException as e:
                    e.request = req
                    e = self._handle_error(e, url=req.url)
                    break # Continue with next retry

                # We received a response
                if debug_stream is not None:
                    debug_stream.write(self._conversation_str(url, resp) + '\n\n')

                try:
                    self._verify_status(resp.status_code, url=req.url)
                except Exception as e:
                    # Basic transmission successful, but not the wished result
                    # Let's collect some debug info
                    e.response = resp
                    e.request = req
                    e.http_log = self._conversation_str(url, resp)
                    resp.release()
                    e = self._handle_error(e, url=req.url)
                    break # Continue with next retry

                if self.cookiejar is not None:
                    # Check against None to avoid issues with empty cookiejars
                    self.cookiejar.extract_cookies(resp, req)

                redirection = resp.headers.get('location')
                if resp.status_code in set([301, 302, 303, 307]) and redirection:
                    resp.release()
                    req.set_url(req.url_split.redirect(redirection))
                    req.method = 'GET' if resp.status_code in set([302, 303]) else req.method
                    for item in ('content-length', 'content-type', 'content-encoding', 'cookie', 'cookie2'):
                        req.headers.discard(item)
                    req.payload = None
                    continue

                if not to_string:
                    return resp
                else:
                    # to_string added as parameter, to handle empty response
                    # bodies as error and continue retries automatically
                    try:
                        ret = resp.content
                    except Exception as e:
                        e = self._handle_error(e, url=url)
                        break
                    else:
                        if not ret:
                            e = EmptyResponse(url, "Empty response body received")
                            e = self._handle_error(e, url=url)
                            break
                        else:
                            return ret
            else:
                e = RetriesExceeded(url, "Redirection limit reached (%s)" % self.max_redirects)
                e = self._handle_error(e, url=url)
        else:
            return self._handle_retries_exceeded(url, last_error=e)

    @classmethod
    def _conversation_str(cls, url, resp):
        header_str = '\n'.join('%s: %s' % item for item in resp.headers.pretty_items())
        ret = 'REQUEST: ' + url + '\n' + resp._sent_request + '\n\n'
        ret += 'RESPONSE: ' + resp._response.version + ' ' + \
                           str(resp.status_code) + '\n' + \
                           header_str + '\n\n' + resp.content
        return ret

    def download(self, url, fpath, chunk_size=16 * 1024, resume=False, **kwargs):
        kwargs.pop('to_string', None)
        headers = kwargs.pop('headers', {})
        headers['Connection'] = 'Keep-Alive'
        if resume and os.path.isfile(fpath):
            offset = os.path.getsize(fpath)
        else:
            offset = 0

        for _ in xrange(self.max_retries):
            if offset:
                headers['Range'] = 'bytes=%d-' % offset
                resp = self.urlopen(url, headers=headers, **kwargs)
                cr = resp.headers.get('Content-Range')
                if resp.status_code != 206 or not cr or not cr.startswith('bytes') or \
                            not cr.split(None, 1)[1].startswith(str(offset)):
                    resp.release()
                    offset = 0
            if not offset:
                headers.pop('Range', None)
                resp = self.urlopen(url, headers=headers, **kwargs)

            with open(fpath, 'ab' if offset else 'wb') as f:
                if offset:
                    f.seek(offset, os.SEEK_SET)
                try:
                    data = resp.read(chunk_size)
                    with resp:
                        while data:
                            f.write(data)
                            data = resp.read(chunk_size)
                except BaseException as e:
                    self._handle_error(e, url=url)
                    if resp.headers.get('accept-ranges') == 'bytes':
                        # Only if this header is set, we can fall back to partial download
                        offset = f.tell()
                    continue
            # All done, break outer loop
            break
        else:
            self._handle_retries_exceeded(url, last_error=e)
        return resp

    def close(self):
        self.clientpool.close()


class RestkitCompatUserAgent(UserAgent):
    response_type = RestkitCompatResponse


class XmlrpcCompatUserAgent(UserAgent):
    def request(self, host, handler, request, verbose=False):
        debug_stream = None if not verbose else cStringIO.StringIO()
        ret = self.urlopen(host + handler, 'POST', payload=request, to_string=True, debug_stream=debug_stream)
        if debug_stream is not None:
            debug_stream.seek(0)
            print debug_stream.read()
        return ret

########NEW FILE########
