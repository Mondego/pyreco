__FILENAME__ = authentication
"""
authentication operations

Authentication instances are used to interact with the remote
authentication service, retreiving storage system routing information
and session tokens.

See COPYING for license information.
"""

from httplib  import HTTPSConnection, HTTPConnection
from utils    import parse_url, THTTPConnection, THTTPSConnection
from errors   import ResponseError, AuthenticationError, AuthenticationFailed
from consts   import user_agent, us_authurl, uk_authurl
from sys      import version_info


class BaseAuthentication(object):
    """
    The base authentication class from which all others inherit.
    """
    def __init__(self, username, api_key, authurl=us_authurl, timeout=15,
                 useragent=user_agent):
        self.authurl = authurl
        self.headers = dict()
        self.headers['x-auth-user'] = username
        self.headers['x-auth-key'] = api_key
        self.headers['User-Agent'] = useragent
        self.timeout = timeout
        (self.host, self.port, self.uri, self.is_ssl) = parse_url(self.authurl)
        if version_info[0] <= 2 and version_info[1] < 6:
            self.conn_class = self.is_ssl and THTTPSConnection or \
                THTTPConnection
        else:
            self.conn_class = self.is_ssl and HTTPSConnection or HTTPConnection

    def authenticate(self):
        """
        Initiates authentication with the remote service and returns a
        two-tuple containing the storage system URL and session token.

        Note: This is a dummy method from the base class. It must be
        overridden by sub-classes.
        """
        return (None, None, None)


class MockAuthentication(BaseAuthentication):
    """
    Mock authentication class for testing
    """
    def authenticate(self):
        return ('http://localhost/v1/account', None, 'xxxxxxxxx')


class Authentication(BaseAuthentication):
    """
    Authentication, routing, and session token management.
    """
    def authenticate(self):
        """
        Initiates authentication with the remote service and returns a
        two-tuple containing the storage system URL and session token.
        """
        conn = self.conn_class(self.host, self.port, timeout=self.timeout)
        #conn = self.conn_class(self.host, self.port)
        conn.request('GET', '/' + self.uri, headers=self.headers)
        response = conn.getresponse()
        response.read()

        # A status code of 401 indicates that the supplied credentials
        # were not accepted by the authentication service.
        if response.status == 401:
            raise AuthenticationFailed()

        # Raise an error for any response that is not 2XX
        if response.status // 100 != 2:
            raise ResponseError(response.status, response.reason)

        storage_url = cdn_url = auth_token = None

        for hdr in response.getheaders():
            if hdr[0].lower() == "x-storage-url":
                storage_url = hdr[1]
            if hdr[0].lower() == "x-cdn-management-url":
                cdn_url = hdr[1]
            if hdr[0].lower() == "x-storage-token":
                auth_token = hdr[1]
            if hdr[0].lower() == "x-auth-token":
                auth_token = hdr[1]

        conn.close()

        if not (auth_token and storage_url):
            raise AuthenticationError("Invalid response from the " \
                    "authentication service.")

        return (storage_url, cdn_url, auth_token)

# vim:set ai ts=4 sw=4 tw=0 expandtab:

########NEW FILE########
__FILENAME__ = connection
"""
connection operations

Connection instances are used to communicate with the remote service at
the account level creating, listing and deleting Containers, and returning
Container instances.

See COPYING for license information.
"""

import  socket
import  os
from    urllib    import urlencode
from    httplib   import HTTPSConnection, HTTPConnection, HTTPException
from    container import Container, ContainerResults
from    utils     import unicode_quote, parse_url, THTTPConnection, THTTPSConnection
from    errors    import ResponseError, NoSuchContainer, ContainerNotEmpty, \
                         InvalidContainerName, CDNNotEnabled, ContainerExists
from    Queue     import Queue, Empty, Full
from    time      import time
import  consts
from    authentication import Authentication
from    fjson     import json_loads
from    sys       import version_info
# Because HTTPResponse objects *have* to have read() called on them
# before they can be used again ...
# pylint: disable-msg=W0612


class Connection(object):
    """
    Manages the connection to the storage system and serves as a factory
    for Container instances.

    @undocumented: cdn_connect
    @undocumented: http_connect
    @undocumented: cdn_request
    @undocumented: make_request
    @undocumented: _check_container_name
    """

    def __init__(self, username=None, api_key=None, timeout=15, **kwargs):
        """
        Accepts keyword arguments for Mosso username and api key.
        Optionally, you can omit these keywords and supply an
        Authentication object using the auth keyword. Setting the argument
        servicenet to True will make use of Rackspace servicenet network.

        @type username: str
        @param username: a Mosso username
        @type api_key: str
        @param api_key: a Mosso API key
        @type servicenet: bool
        @param servicenet: Use Rackspace servicenet to access Cloud Files.
        @type cdn_log_retention: bool
        @param cdn_log_retention: set logs retention for this cdn enabled
        container.
        """
        self.cdn_enabled = False
        self.cdn_args = None
        self.connection_args = None
        self.cdn_connection = None
        self.connection = None
        self.token = None
        self.debuglevel = int(kwargs.get('debuglevel', 0))
        self.servicenet = kwargs.get('servicenet', False)
        self.user_agent = kwargs.get('useragent', consts.user_agent)
        self.timeout = timeout

        # if the environement variable RACKSPACE_SERVICENET is set (to
        # anything) it will automatically set servicenet=True
        if not 'servicenet' in kwargs \
                and 'RACKSPACE_SERVICENET' in os.environ:
            self.servicenet = True

        self.auth = 'auth' in kwargs and kwargs['auth'] or None

        if not self.auth:
            authurl = kwargs.get('authurl', consts.us_authurl)
            if username and api_key and authurl:
                self.auth = Authentication(username, api_key, authurl=authurl,
                            useragent=self.user_agent, timeout=self.timeout)
            else:
                raise TypeError("Incorrect or invalid arguments supplied")
        self._authenticate()
    def _authenticate(self):
        """
        Authenticate and setup this instance with the values returned.
        """
        (url, self.cdn_url, self.token) = self.auth.authenticate()
        url = self._set_storage_url(url)
        self.connection_args = parse_url(url)

        if version_info[0] <= 2 and version_info[1] < 6:
            self.conn_class = self.connection_args[3] and THTTPSConnection or \
                                                              THTTPConnection
        else:
            self.conn_class = self.connection_args[3] and HTTPSConnection or \
                                                              HTTPConnection
        self.http_connect()
        if self.cdn_url:
            self.cdn_connect()

    def _set_storage_url(self, url):
        if self.servicenet:
            return "https://snet-%s" % url.replace("https://", "")
        return url

    def cdn_connect(self):
        """
        Setup the http connection instance for the CDN service.
        """
        (host, port, cdn_uri, is_ssl) = parse_url(self.cdn_url)
        self.cdn_connection = self.conn_class(host, port, timeout=self.timeout)
        self.cdn_enabled = True

    def http_connect(self):
        """
        Setup the http connection instance.
        """
        (host, port, self.uri, is_ssl) = self.connection_args
        self.connection = self.conn_class(host, port=port, \
                                              timeout=self.timeout)
        self.connection.set_debuglevel(self.debuglevel)

    def cdn_request(self, method, path=[], data='', hdrs=None):
        """
        Given a method (i.e. GET, PUT, POST, etc), a path, data, header and
        metadata dicts, performs an http request against the CDN service.
        """
        if not self.cdn_enabled:
            raise CDNNotEnabled()

        path = '/%s/%s' % \
                 (self.uri.rstrip('/'), '/'.join([unicode_quote(i) for i in path]))
        headers = {'Content-Length': str(len(data)),
                   'User-Agent': self.user_agent,
                   'X-Auth-Token': self.token}
        if isinstance(hdrs, dict):
            headers.update(hdrs)

        def retry_request():
            '''Re-connect and re-try a failed request once'''
            self.cdn_connect()
            self.cdn_connection.request(method, path, data, headers)
            return self.cdn_connection.getresponse()

        try:
            self.cdn_connection.request(method, path, data, headers)
            response = self.cdn_connection.getresponse()
        except (socket.error, IOError, HTTPException):
            response = retry_request()
        if response.status == 401:
            self._authenticate()
            headers['X-Auth-Token'] = self.token
            response = retry_request()

        return response

    def make_request(self, method, path=[], data='', hdrs=None, parms=None):
        """
        Given a method (i.e. GET, PUT, POST, etc), a path, data, header and
        metadata dicts, and an optional dictionary of query parameters,
        performs an http request.
        """
        path = '/%s/%s' % \
                 (self.uri.rstrip('/'), '/'.join([unicode_quote(i) for i in path]))

        if isinstance(parms, dict) and parms:
            path = '%s?%s' % (path, urlencode(parms))

        headers = {'Content-Length': str(len(data)),
                   'User-Agent': self.user_agent,
                   'X-Auth-Token': self.token}
        isinstance(hdrs, dict) and headers.update(hdrs)

        def retry_request():
            '''Re-connect and re-try a failed request once'''
            self.http_connect()
            self.connection.request(method, path, data, headers)
            return self.connection.getresponse()

        try:
            self.connection.request(method, path, data, headers)
            response = self.connection.getresponse()
        except (socket.error, IOError, HTTPException):
            response = retry_request()
        if response.status == 401:
            self._authenticate()
            headers['X-Auth-Token'] = self.token
            response = retry_request()

        return response

    def get_info(self):
        """
        Return tuple for number of containers, total bytes in the account and account metadata

        >>> connection.get_info()
        (5, 2309749)

        @rtype: tuple
        @return: a tuple containing the number of containers, total bytes
                 used by the account and a dictionary containing account metadata
        """
        response = self.make_request('HEAD')
        count = size = None
        metadata = {}
        for hdr in response.getheaders():
            if hdr[0].lower() == 'x-account-container-count':
                try:
                    count = int(hdr[1])
                except ValueError:
                    count = 0
            if hdr[0].lower() == 'x-account-bytes-used':
                try:
                    size = int(hdr[1])
                except ValueError:
                    size = 0
            if hdr[0].lower().startswith('x-account-meta-'):
                metadata[hdr[0].lower()[15:]] = hdr[1]
        buff = response.read()
        if (response.status < 200) or (response.status > 299):
            raise ResponseError(response.status, response.reason)
        return (count, size, metadata)

    def update_account_metadata(self, metadata):
        """
        Update account metadata
        >>> metadata = {'x-account-meta-foo' : 'bar'}
        >>> connection.update_account_metadata(metadata)

        @param metadata: Dictionary of metadata
        @type metdada: dict
        """
        response = self.make_request('POST', hdrs=metadata)
        response.read()
        if (response.status < 200) or (response.status > 299):
           raise ResponseError(response.status, response.reason)

    def _check_container_name(self, container_name):
        if not container_name or \
                '/' in container_name or \
                len(container_name) > consts.container_name_limit:
            raise InvalidContainerName(container_name)

    def create_container(self, container_name, error_on_existing=False):
        """
        Given a container name, returns a L{Container} item, creating a new
        Container if one does not already exist.

        >>> connection.create_container('new_container')
        <cloudfiles.container.Container object at 0xb77d628c>

        @param container_name: name of the container to create
        @type container_name: str
        @param error_on_existing: raise ContainerExists if container already
        exists
        @type error_on_existing: bool
        @rtype: L{Container}
        @return: an object representing the newly created container
        """
        self._check_container_name(container_name)

        response = self.make_request('PUT', [container_name])
        buff = response.read()
        if (response.status < 200) or (response.status > 299):
            raise ResponseError(response.status, response.reason)
        if error_on_existing and (response.status == 202):
            raise ContainerExists(container_name)
        return Container(self, container_name)

    def delete_container(self, container_name):
        """
        Given a container name, delete it.

        >>> connection.delete_container('old_container')

        @param container_name: name of the container to delete
        @type container_name: str
        """
        if isinstance(container_name, Container):
            container_name = container_name.name
        self._check_container_name(container_name)

        response = self.make_request('DELETE', [container_name])
        response.read()

        if (response.status == 409):
            raise ContainerNotEmpty(container_name)
        elif (response.status == 404):
            raise NoSuchContainer
        elif (response.status < 200) or (response.status > 299):
            raise ResponseError(response.status, response.reason)

        if self.cdn_enabled:
            response = self.cdn_request('POST', [container_name],
                                hdrs={'X-CDN-Enabled': 'False'})

    def get_all_containers(self, limit=None, marker=None, **parms):
        """
        Returns a Container item result set.

        >>> connection.get_all_containers()
        ContainerResults: 4 containers
        >>> print ', '.join([container.name for container in
                             connection.get_all_containers()])
        new_container, old_container, pictures, music

        @rtype: L{ContainerResults}
        @return: an iterable set of objects representing all containers on the
                 account
        @param limit: number of results to return, up to 10,000
        @type limit: int
        @param marker: return only results whose name is greater than "marker"
        @type marker: str
        """
        if limit:
            parms['limit'] = limit
        if marker:
            parms['marker'] = marker
        return ContainerResults(self, self.list_containers_info(**parms))

    def get_container(self, container_name):
        """
        Return a single Container item for the given Container.

        >>> connection.get_container('old_container')
        <cloudfiles.container.Container object at 0xb77d628c>
        >>> container = connection.get_container('old_container')
        >>> container.size_used
        23074

        @param container_name: name of the container to create
        @type container_name: str
        @rtype: L{Container}
        @return: an object representing the container
        """
        self._check_container_name(container_name)

        response = self.make_request('HEAD', [container_name])
        count = size = None
        metadata = {}
        for hdr in response.getheaders():
            if hdr[0].lower() == 'x-container-object-count':
                try:
                    count = int(hdr[1])
                except ValueError:
                    count = 0
            if hdr[0].lower() == 'x-container-bytes-used':
                try:
                    size = int(hdr[1])
                except ValueError:
                    size = 0
            if hdr[0].lower().startswith('x-container-meta-'):
                metadata[hdr[0].lower()[17:]] = hdr[1]
        buff = response.read()
        if response.status == 404:
            raise NoSuchContainer(container_name)
        if (response.status < 200) or (response.status > 299):
            raise ResponseError(response.status, response.reason)
        return Container(self, container_name, count, size, metadata)

    def list_public_containers(self):
        """
        Returns a list of containers that have been published to the CDN.

        >>> connection.list_public_containers()
        ['container1', 'container2', 'container3']

        @rtype: list(str)
        @return: a list of all CDN-enabled container names as strings
        """
        response = self.cdn_request('GET', [''])
        if (response.status < 200) or (response.status > 299):
            buff = response.read()
            raise ResponseError(response.status, response.reason)
        return response.read().splitlines()

    def list_containers_info(self, limit=None, marker=None, **parms):
        """
        Returns a list of Containers, including object count and size.

        >>> connection.list_containers_info()
        [{u'count': 510, u'bytes': 2081717, u'name': u'new_container'},
         {u'count': 12, u'bytes': 23074, u'name': u'old_container'},
         {u'count': 0, u'bytes': 0, u'name': u'container1'},
         {u'count': 0, u'bytes': 0, u'name': u'container2'},
         {u'count': 0, u'bytes': 0, u'name': u'container3'},
         {u'count': 3, u'bytes': 2306, u'name': u'test'}]

        @rtype: list({"name":"...", "count":..., "bytes":...})
        @return: a list of all container info as dictionaries with the
                 keys "name", "count", and "bytes"
        @param limit: number of results to return, up to 10,000
        @type limit: int
        @param marker: return only results whose name is greater than "marker"
        @type marker: str
        """
        if limit:
            parms['limit'] = limit
        if marker:
            parms['marker'] = marker
        parms['format'] = 'json'
        response = self.make_request('GET', [''], parms=parms)
        if (response.status < 200) or (response.status > 299):
            buff = response.read()
            raise ResponseError(response.status, response.reason)
        return json_loads(response.read())

    def list_containers(self, limit=None, marker=None, **parms):
        """
        Returns a list of Containers.

        >>> connection.list_containers()
        ['new_container',
         'old_container',
         'container1',
         'container2',
         'container3',
         'test']

        @rtype: list(str)
        @return: a list of all containers names as strings
        @param limit: number of results to return, up to 10,000
        @type limit: int
        @param marker: return only results whose name is greater than "marker"
        @type marker: str
        """
        if limit:
            parms['limit'] = limit
        if marker:
            parms['marker'] = marker
        response = self.make_request('GET', [''], parms=parms)
        if (response.status < 200) or (response.status > 299):
            buff = response.read()
            raise ResponseError(response.status, response.reason)
        return response.read().splitlines()

    def __getitem__(self, key):
        """
        Container objects can be grabbed from a connection using index
        syntax.

        >>> container = conn['old_container']
        >>> container.size_used
        23074

        @rtype: L{Container}
        @return: an object representing the container
        """
        return self.get_container(key)


class ConnectionPool(Queue):
    """
    A thread-safe connection pool object.

    This component isn't required when using the cloudfiles library, but it may
    be useful when building threaded applications.
    """

    def __init__(self, username=None, api_key=None, **kwargs):
        poolsize = kwargs.pop('poolsize', 10)
        self.connargs = {'username': username, 'api_key': api_key}
        self.connargs.update(kwargs)
        Queue.__init__(self, poolsize)

    def get(self):
        """
        Return a cloudfiles connection object.

        @rtype: L{Connection}
        @return: a cloudfiles connection object
        """
        try:
            (create, connobj) = Queue.get(self, block=0)
        except Empty:
            connobj = Connection(**self.connargs)
        return connobj

    def put(self, connobj):
        """
        Place a cloudfiles connection object back into the pool.

        @param connobj: a cloudfiles connection object
        @type connobj: L{Connection}
        """
        try:
            Queue.put(self, (time(), connobj), block=0)
        except Full:
            del connobj
# vim:set ai sw=4 ts=4 tw=0 expandtab:

########NEW FILE########
__FILENAME__ = consts
""" See COPYING for license information. """

__version__ = "1.7.11"
user_agent = "python-cloudfiles/%s" % __version__
us_authurl = 'https://auth.api.rackspacecloud.com/v1.0'
uk_authurl = 'https://lon.auth.api.rackspacecloud.com/v1.0'
default_authurl = us_authurl
default_cdn_ttl = 86400
cdn_log_retention = False

meta_name_limit = 128
meta_value_limit = 256
object_name_limit = 1024
container_name_limit = 256

########NEW FILE########
__FILENAME__ = container
"""
container operations

Containers are storage compartments where you put your data (objects).
A container is similar to a directory or folder on a conventional filesystem
with the exception that they exist in a flat namespace, you can not create
containers inside of containers.

See COPYING for license information.
"""

from storage_object import Object, ObjectResults
from errors import ResponseError, InvalidContainerName, InvalidObjectName, \
                   ContainerNotPublic, CDNNotEnabled
from utils  import requires_name
import consts
from fjson  import json_loads

# Because HTTPResponse objects *have* to have read() called on them
# before they can be used again ...
# pylint: disable-msg=W0612


class Container(object):
    """
    Container object and Object instance factory.

    If your account has the feature enabled, containers can be publically
    shared over a global content delivery network.

    @ivar name: the container's name (generally treated as read-only)
    @type name: str
    @ivar object_count: the number of objects in this container (cached)
    @type object_count: number
    @ivar size_used: the sum of the sizes of all objects in this container
            (cached)
    @type size_used: number
    @ivar cdn_ttl: the time-to-live of the CDN's public cache of this container
            (cached, use make_public to alter)
    @type cdn_ttl: number
    @ivar cdn_log_retention: retention of the logs in the container.
    @type cdn_log_retention: bool

    @undocumented: _fetch_cdn_data
    @undocumented: _list_objects_raw
    """
    def __set_name(self, name):
        # slashes make for invalid names
        if isinstance(name, (str, unicode)) and \
                ('/' in name or len(name) > consts.container_name_limit):
            raise InvalidContainerName(name)
        self._name = name

    name = property(fget=lambda self: self._name, fset=__set_name,
        doc="the name of the container (read-only)")

    def __init__(self, connection=None, name=None, count=None, size=None, metadata=None):
        """
        Containers will rarely if ever need to be instantiated directly by the
        user.

        Instead, use the L{create_container<Connection.create_container>},
        L{get_container<Connection.get_container>},
        L{list_containers<Connection.list_containers>} and
        other methods on a valid Connection object.
        """
        self._name = None
        self.name = name
        self.conn = connection
        self.object_count = count
        self.size_used = size
        self.metadata = metadata
        self.cdn_uri = None
        self.cdn_ssl_uri = None
        self.cdn_streaming_uri = None
        self.cdn_ttl = None
        self.cdn_log_retention = None
        if self.metadata == None:
            self.metadata = {}
        if connection.cdn_enabled:
            self._fetch_cdn_data()

    @requires_name(InvalidContainerName)
    def update_metadata(self, metadata):
        """
        Update Container Metadata
        
        >>> metadata = {'x-container-meta-foo' : 'bar'}
        >>> container.update_metadata(metadata)
        
        @param metadata: A dictionary containing metadata.
        @type metadata: dict
        """
        response = self.conn.make_request('POST', [self.name], hdrs=metadata)
        response.read()
        if (response.status < 200) or (response.status > 299):
            raise ResponseError(response.status, response.reason)
    
    def enable_static_web(self, index=None, listings=None, error=None, listings_css=None):
        """
        Enable static web for this Container

        >>> container.enable_static_web('index.html', 'error.html', True, 'style.css')

        @param index: The name of the index landing page
        @type index : str
        @param listings: A boolean value to enable listing.
        @type error: bool
        @param listings_css: The file to be used when applying CSS to the listing.
        @type listings_css: str
        @param error: The suffix to be used for 404 and 401 error pages.
        @type error: str

        """
        metadata = {'X-Container-Meta-Web-Index' : '',
                    'X-Container-Meta-Web-Listings' : '',
                    'X-Container-Meta-Web-Error' : '',
                    'X-Container-Meta-Web-Listings-CSS' : ''}
        if index is not None:
            metadata['X-Container-Meta-Web-Index'] = index
        if listings is not None:
            metadata['X-Container-Meta-Web-Listings'] = str(listings)
        if error is not None:
            metadata['X-Container-Meta-Web-Error'] = error
        if listings_css is not None:
            metadata['X-Container-Meta-Web-Listings-CSS'] = listings_css
        self.update_metadata(metadata)

    def disable_static_web(self):
        """
        Disable static web for this Container

        >>> container.disable_static_web()
        """
        self.enable_static_web()

    def enable_object_versioning(self, container_name):
        """
        Enable object versioning on this container
        
        >>> container.enable_object_versioning('container_i_want_versions_to_go_to')
        
        @param container_url: The container where versions will be stored
        @type container_name: str
        """
        self.update_metadata({'X-Versions-Location' : container_name})

    def disable_object_versioning(self):
        """
        Disable object versioning on this container

        >>> container.disable_object_versioning()
        """
        self.update_metadata({'X-Versions-Location' : ''})

    @requires_name(InvalidContainerName)
    def _fetch_cdn_data(self):
        """
        Fetch the object's CDN data from the CDN service
        """
        response = self.conn.cdn_request('HEAD', [self.name])
        if response.status >= 200 and response.status < 300:
            for hdr in response.getheaders():
                if hdr[0].lower() == 'x-cdn-uri':
                    self.cdn_uri = hdr[1]
                if hdr[0].lower() == 'x-ttl':
                    self.cdn_ttl = int(hdr[1])
                if hdr[0].lower() == 'x-cdn-ssl-uri':
                    self.cdn_ssl_uri = hdr[1]
                if hdr[0].lower() == 'x-cdn-streaming-uri':
                    self.cdn_streaming_uri = hdr[1]
                if hdr[0].lower() == 'x-log-retention':
                    self.cdn_log_retention = hdr[1] == "True" and True or False

    @requires_name(InvalidContainerName)
    def make_public(self, ttl=consts.default_cdn_ttl):
        """
        Either publishes the current container to the CDN or updates its
        CDN attributes.  Requires CDN be enabled on the account.

        >>> container.make_public(ttl=604800) # expire in 1 week

        @param ttl: cache duration in seconds of the CDN server
        @type ttl: number
        """
        if not self.conn.cdn_enabled:
            raise CDNNotEnabled()
        if self.cdn_uri:
            request_method = 'POST'
        else:
            request_method = 'PUT'
        hdrs = {'X-TTL': str(ttl), 'X-CDN-Enabled': 'True'}
        response = self.conn.cdn_request(request_method, \
                                             [self.name], hdrs=hdrs)
        if (response.status < 200) or (response.status >= 300):
            raise ResponseError(response.status, response.reason)
        self.cdn_ttl = ttl
        for hdr in response.getheaders():
            if hdr[0].lower() == 'x-cdn-uri':
                self.cdn_uri = hdr[1]
            if hdr[0].lower() == 'x-cdn-ssl-uri':
                self.cdn_ssl_uri = hdr[1]

    @requires_name(InvalidContainerName)
    def make_private(self):
        """
        Disables CDN access to this container.
        It may continue to be available until its TTL expires.

        >>> container.make_private()
        """
        if not self.conn.cdn_enabled:
            raise CDNNotEnabled()
        hdrs = {'X-CDN-Enabled': 'False'}
        self.cdn_uri = None
        response = self.conn.cdn_request('POST', [self.name], hdrs=hdrs)
        if (response.status < 200) or (response.status >= 300):
            raise ResponseError(response.status, response.reason)

    @requires_name(InvalidContainerName)
    def purge_from_cdn(self, email=None):
        """
        Purge Edge cache for all object inside of this container.
        You will be notified by email if one is provided when the
        job completes.

        >>> container.purge_from_cdn("user@dmain.com")
        
        or

        >>> container.purge_from_cdn("user@domain.com,user2@domain.com")
        
        or
        
        >>> container.purge_from_cdn()
        
        @param email: A Valid email address
        @type email: str
        """
        if not self.conn.cdn_enabled:
            raise CDNNotEnabled()

        if email:
            hdrs = {"X-Purge-Email": email}
            response = self.conn.cdn_request('DELETE', [self.name], hdrs=hdrs)
        else:
            response = self.conn.cdn_request('DELETE', [self.name])

        if (response.status < 200) or (response.status >= 300):
            raise ResponseError(response.status, response.reason)

    @requires_name(InvalidContainerName)
    def log_retention(self, log_retention=consts.cdn_log_retention):
        """
        Enable CDN log retention on the container. If enabled logs will be
        periodically (at unpredictable intervals) compressed and uploaded to
        a ".CDN_ACCESS_LOGS" container in the form of
        "container_name/YYYY/MM/DD/HH/XXXX.gz". Requires CDN be enabled on the
        account.

        >>> container.log_retention(True)

        @param log_retention: Enable or disable logs retention.
        @type log_retention: bool
        """
        if not self.conn.cdn_enabled:
            raise CDNNotEnabled()

        hdrs = {'X-Log-Retention': log_retention}
        response = self.conn.cdn_request('POST', [self.name], hdrs=hdrs)
        if (response.status < 200) or (response.status >= 300):
            raise ResponseError(response.status, response.reason)

        self.cdn_log_retention = log_retention

    def is_public(self):
        """
        Returns a boolean indicating whether or not this container is
        publically accessible via the CDN.

        >>> container.is_public()
        False
        >>> container.make_public()
        >>> container.is_public()
        True

        @rtype: bool
        @return: whether or not this container is published to the CDN
        """
        if not self.conn.cdn_enabled:
            raise CDNNotEnabled()
        return self.cdn_uri is not None

    @requires_name(InvalidContainerName)
    def public_uri(self):
        """
        Return the URI for this container, if it is publically
        accessible via the CDN.

        >>> connection['container1'].public_uri()
        'http://c00061.cdn.cloudfiles.rackspacecloud.com'

        @rtype: str
        @return: the public URI for this container
        """
        if not self.is_public():
            raise ContainerNotPublic()
        return self.cdn_uri

    @requires_name(InvalidContainerName)
    def public_ssl_uri(self):
        """
        Return the SSL URI for this container, if it is publically
        accessible via the CDN.

        >>> connection['container1'].public_ssl_uri()
        'https://c61.ssl.cf0.rackcdn.com'

        @rtype: str
        @return: the public SSL URI for this container
        """
        if not self.is_public():
            raise ContainerNotPublic()
        return self.cdn_ssl_uri

    @requires_name(InvalidContainerName)
    def public_streaming_uri(self):
        """
        Return the Streaming URI for this container, if it is publically
        accessible via the CDN.

        >>> connection['container1'].public_ssl_uri()
        'https://c61.stream.rackcdn.com'

        @rtype: str
        @return: the public Streaming URI for this container
        """
        if not self.is_public():
            raise ContainerNotPublic()
        return self.cdn_streaming_uri

    @requires_name(InvalidContainerName)
    def create_object(self, object_name):
        """
        Return an L{Object} instance, creating it if necessary.

        When passed the name of an existing object, this method will
        return an instance of that object, otherwise it will create a
        new one.

        >>> container.create_object('new_object')
        <cloudfiles.storage_object.Object object at 0xb778366c>
        >>> obj = container.create_object('new_object')
        >>> obj.name
        'new_object'

        @type object_name: str
        @param object_name: the name of the object to create
        @rtype: L{Object}
        @return: an object representing the newly created storage object
        """
        return Object(self, object_name)

    @requires_name(InvalidContainerName)
    def get_objects(self, prefix=None, limit=None, marker=None,
                    path=None, delimiter=None, **parms):
        """
        Return a result set of all Objects in the Container.

        Keyword arguments are treated as HTTP query parameters and can
        be used to limit the result set (see the API documentation).

        >>> container.get_objects(limit=2)
        ObjectResults: 2 objects
        >>> for obj in container.get_objects():
        ...     print obj.name
        new_object
        old_object

        @param prefix: filter the results using this prefix
        @type prefix: str
        @param limit: return the first "limit" objects found
        @type limit: int
        @param marker: return objects whose names are greater than "marker"
        @type marker: str
        @param path: return all objects in "path"
        @type path: str
        @param delimiter: use this character as a delimiter for subdirectories
        @type delimiter: char

        @rtype: L{ObjectResults}
        @return: an iterable collection of all storage objects in the container
        """
        return ObjectResults(self, self.list_objects_info(
                prefix, limit, marker, path, delimiter, **parms))

    @requires_name(InvalidContainerName)
    def get_object(self, object_name):
        """
        Return an L{Object} instance for an existing storage object.

        If an object with a name matching object_name does not exist
        then a L{NoSuchObject} exception is raised.

        >>> obj = container.get_object('old_object')
        >>> obj.name
        'old_object'

        @param object_name: the name of the object to retrieve
        @type object_name: str
        @rtype: L{Object}
        @return: an Object representing the storage object requested
        """
        return Object(self, object_name, force_exists=True)

    @requires_name(InvalidContainerName)
    def list_objects_info(self, prefix=None, limit=None, marker=None,
                          path=None, delimiter=None, **parms):
        """
        Return information about all objects in the Container.

        Keyword arguments are treated as HTTP query parameters and can
        be used limit the result set (see the API documentation).

        >>> conn['container1'].list_objects_info(limit=2)
        [{u'bytes': 4820,
          u'content_type': u'application/octet-stream',
          u'hash': u'db8b55400b91ce34d800e126e37886f8',
          u'last_modified': u'2008-11-05T00:56:00.406565',
          u'name': u'new_object'},
         {u'bytes': 1896,
          u'content_type': u'application/octet-stream',
          u'hash': u'1b49df63db7bc97cd2a10e391e102d4b',
          u'last_modified': u'2008-11-05T00:56:27.508729',
          u'name': u'old_object'}]

        @param prefix: filter the results using this prefix
        @type prefix: str
        @param limit: return the first "limit" objects found
        @type limit: int
        @param marker: return objects with names greater than "marker"
        @type marker: str
        @param path: return all objects in "path"
        @type path: str
        @param delimiter: use this character as a delimiter for subdirectories
        @type delimiter: char

        @rtype: list({"name":"...", "hash":..., "size":..., "type":...})
        @return: a list of all container info as dictionaries with the
                 keys "name", "hash", "size", and "type"
        """
        parms['format'] = 'json'
        resp = self._list_objects_raw(
            prefix, limit, marker, path, delimiter, **parms)
        return json_loads(resp)

    @requires_name(InvalidContainerName)
    def list_objects(self, prefix=None, limit=None, marker=None,
                     path=None, delimiter=None, **parms):
        """
        Return names of all L{Object}s in the L{Container}.

        Keyword arguments are treated as HTTP query parameters and can
        be used to limit the result set (see the API documentation).

        >>> container.list_objects()
        ['new_object', 'old_object']

        @param prefix: filter the results using this prefix
        @type prefix: str
        @param limit: return the first "limit" objects found
        @type limit: int
        @param marker: return objects with names greater than "marker"
        @type marker: str
        @param path: return all objects in "path"
        @type path: str
        @param delimiter: use this character as a delimiter for subdirectories
        @type delimiter: char

        @rtype: list(str)
        @return: a list of all container names
        """
        resp = self._list_objects_raw(prefix=prefix, limit=limit,
                                      marker=marker, path=path,
                                      delimiter=delimiter, **parms)
        return resp.splitlines()

    @requires_name(InvalidContainerName)
    def _list_objects_raw(self, prefix=None, limit=None, marker=None,
                          path=None, delimiter=None, **parms):
        """
        Returns a chunk list of storage object info.
        """
        if prefix:
            parms['prefix'] = prefix
        if limit:
            parms['limit'] = limit
        if marker:
            parms['marker'] = marker
        if delimiter:
            parms['delimiter'] = delimiter
        if not path is None:
            parms['path'] = path  # empty strings are valid
        response = self.conn.make_request('GET', [self.name], parms=parms)
        if (response.status < 200) or (response.status > 299):
            response.read()
            raise ResponseError(response.status, response.reason)
        return response.read()

    def __getitem__(self, key):
        return self.get_object(key)

    def __str__(self):
        return self.name

    @requires_name(InvalidContainerName)
    def delete_object(self, object_name):
        """
        Permanently remove a storage object.

        >>> container.list_objects()
        ['new_object', 'old_object']
        >>> container.delete_object('old_object')
        >>> container.list_objects()
        ['new_object']

        @param object_name: the name of the object to retrieve
        @type object_name: str
        """
        if isinstance(object_name, Object):
            object_name = object_name.name
        if not object_name:
            raise InvalidObjectName(object_name)
        response = self.conn.make_request('DELETE', [self.name, object_name])
        if (response.status < 200) or (response.status > 299):
            response.read()
            raise ResponseError(response.status, response.reason)
        response.read()


class ContainerResults(object):
    """
    An iterable results set object for Containers.

    This class implements dictionary- and list-like interfaces.
    """
    def __init__(self, conn, containers=list()):
        self._containers = containers
        self._names = [k['name'] for k in containers]
        self.conn = conn

    def __getitem__(self, key):
        return Container(self.conn,
                         self._containers[key]['name'],
                         self._containers[key]['count'],
                         self._containers[key]['bytes'])

    def __getslice__(self, i, j):
        return [Container(self.conn, k['name'], k['count'], \
                              k['size']) for k in self._containers[i:j]]

    def __contains__(self, item):
        return item in self._names

    def __repr__(self):
        return 'ContainerResults: %s containers' % len(self._containers)
    __str__ = __repr__

    def __len__(self):
        return len(self._containers)

    def index(self, value, *args):
        """
        returns an integer for the first index of value
        """
        return self._names.index(value, *args)

    def count(self, value):
        """
        returns the number of occurrences of value
        """
        return self._names.count(value)

# vim:set ai sw=4 ts=4 tw=0 expandtab:

########NEW FILE########
__FILENAME__ = errors
"""
exception classes

See COPYING for license information.
"""

class Error(StandardError):
    """
    Base class for all errors and exceptions
    """
    pass


class ResponseError(Error):
    """
    Raised when the remote service returns an error.
    """
    def __init__(self, status, reason):
        self.status = status
        self.reason = reason
        Error.__init__(self)

    def __str__(self):
        return '%d: %s' % (self.status, self.reason)

    def __repr__(self):
        return '%d: %s' % (self.status, self.reason)


class NoSuchContainer(Error):
    """
    Raised on a non-existent Container.
    """
    pass


class NoSuchObject(Error):
    """
    Raised on a non-existent Object.
    """
    pass


class ContainerNotEmpty(Error):
    """
    Raised when attempting to delete a Container that still contains Objects.
    """
    def __init__(self, container_name):
        self.container_name = container_name
        Error.__init__(self)

    def __str__(self):
        return "Cannot delete non-empty Container %s" % self.container_name

    def __repr__(self):
        return "%s(%s)" % (self.__class__.__name__, self.container_name)


class ContainerExists(Error):
    """
    Raised when attempting to create a Container when the container already
    exists.
    """
    pass


class InvalidContainerName(Error):
    """
    Raised for invalid storage container names.
    """
    pass


class InvalidObjectName(Error):
    """
    Raised for invalid storage object names.
    """
    pass


class InvalidMetaName(Error):
    """
    Raised for invalid metadata names.
    """
    pass


class InvalidMetaValue(Error):
    """
    Raised for invalid metadata value.
    """
    pass


class InvalidUrl(Error):
    """
    Not a valid url for use with this software.
    """
    pass


class InvalidObjectSize(Error):
    """
    Not a valid storage_object size attribute.
    """
    pass


class IncompleteSend(Error):
    """
    Raised when there is a insufficient amount of data to send.
    """
    pass


class ContainerNotPublic(Error):
    """
    Raised when public features of a non-public container are accessed.
    """
    pass


class CDNNotEnabled(Error):
    """
    CDN is not enabled for this account.
    """
    pass


class AuthenticationFailed(Error):
    """
    Raised on a failure to authenticate.
    """
    pass


class AuthenticationError(Error):
    """
    Raised when an unspecified authentication error has occurred.
    """
    pass

########NEW FILE########
__FILENAME__ = fjson
from tokenize  import  generate_tokens, STRING, NAME, OP
from cStringIO import  StringIO
from re        import  compile, DOTALL

comments = compile(r'/\*.*\*/|//[^\r\n]*', DOTALL)


def _loads(string):
    '''
    Fairly competent json parser exploiting the python tokenizer and eval()

    _loads(serialized_json) -> object
    '''
    try:
        res = []
        consts = {'true': True, 'false': False, 'null': None}
        string = '(' + comments.sub('', string) + ')'
        for type, val, _, _, _ in generate_tokens(StringIO(string).readline):
            if (type == OP and val not in '[]{}:,()-') or \
               (type == NAME and val not in consts):
                raise AttributeError()
            elif type == STRING:
                res.append('u')
                res.append(val.replace('\\/', '/'))
            else:
                res.append(val)
        return eval(''.join(res), {}, consts)
    except:
        raise AttributeError()


# look for a real json parser first
try:
    # 2.6 will have a json module in the stdlib
    from json import loads as json_loads
except ImportError:
    try:
        # simplejson is popular and pretty good
        from simplejson import loads as json_loads
    # fall back on local parser otherwise
    except ImportError:
        json_loads = _loads

__all__ = ['json_loads']

########NEW FILE########
__FILENAME__ = storage_object
"""
Object operations

An Object is analogous to a file on a conventional filesystem. You can
read data from, or write data to your Objects. You can also associate
arbitrary metadata with them.

See COPYING for license information.
"""

try:
    from hashlib import md5
except ImportError:
    from md5 import md5
import StringIO
import mimetypes
import os

from errors  import ResponseError, NoSuchObject, \
                    InvalidObjectName, IncompleteSend, \
                    InvalidMetaName, InvalidMetaValue

from socket  import timeout
import consts
from utils   import unicode_quote, requires_name

# Because HTTPResponse objects *have* to have read() called on them
# before they can be used again ...
# pylint: disable-msg=W0612


class Object(object):
    """
    Storage data representing an object, (metadata and data).

    @undocumented: _make_headers
    @undocumented: _name_check
    @undocumented: _initialize
    @undocumented: compute_md5sum
    @undocumented: __get_conn_for_write
    @ivar name: the object's name (generally treat as read-only)
    @type name: str
    @ivar content_type: the object's content-type (set or read)
    @type content_type: str
    @ivar metadata: metadata associated with the object (set or read)
    @type metadata: dict
    @ivar size: the object's size (cached)
    @type size: number
    @ivar last_modified: date and time of last file modification (cached)
    @type last_modified: str
    @ivar container: the object's container (generally treat as read-only)
    @type container: L{Container}
    """
    # R/O support of the legacy objsum attr.
    objsum = property(lambda self: self._etag)

    def __set_etag(self, value):
        self._etag = value
        self._etag_override = True

    etag = property(lambda self: self._etag, __set_etag)

    def __init__(self, container, name=None,
                 force_exists=False, object_record=None):
        """
        Storage objects rarely if ever need to be instantiated directly by the
        user.

        Instead, use the L{create_object<Container.create_object>},
        L{get_object<Container.get_object>},
        L{list_objects<Container.list_objects>} and other
        methods on its parent L{Container} object.
        """
        self.container = container
        self.last_modified = None
        self.metadata = {}
        self.headers = {}
        self.manifest = None
        if object_record:
            self.name = object_record['name']
            self.content_type = object_record['content_type']
            self.size = object_record['bytes']
            self.last_modified = object_record['last_modified']
            self._etag = object_record['hash']
            self._etag_override = False
        else:
            self.name = name
            self.content_type = None
            self.size = None
            self._etag = None
            self._etag_override = False
            if not self._initialize() and force_exists:
                raise NoSuchObject(self.name)

    @requires_name(InvalidObjectName)
    def read(self, size=-1, offset=0, hdrs=None, buffer=None, callback=None):
        """
        Read the content from the remote storage object.

        By default this method will buffer the response in memory and
        return it as a string. However, if a file-like object is passed
        in using the buffer keyword, the response will be written to it
        instead.

        A callback can be passed in for reporting on the progress of
        the download. The callback should accept two integers, the first
        will be for the amount of data written so far, the second for
        the total size of the transfer. Note: This option is only
        applicable when used in conjunction with the buffer option.

        >>> test_object.write('hello')
        >>> test_object.read()
        'hello'

        @param size: combined with offset, defines the length of data to be
                     read
        @type size: number
        @param offset: combined with size, defines the start location to be
                       read
        @type offset: number
        @param hdrs: an optional dict of headers to send with the request
        @type hdrs: dictionary
        @param buffer: an optional file-like object to write the content to
        @type buffer: file-like object
        @param callback: function to be used as a progress callback
        @type callback: callable(transferred, size)
        @rtype: str or None
        @return: a string of all data in the object, or None if a buffer is
                 used
        """
        self._name_check()
        if size > 0:
            range = 'bytes=%d-%d' % (offset, (offset + size) - 1)
            if hdrs:
                hdrs['Range'] = range
            else:
                hdrs = {'Range': range}
        response = self.container.conn.make_request('GET',
                path=[self.container.name, self.name], hdrs=hdrs)
        if (response.status < 200) or (response.status > 299):
            response.read()
            raise ResponseError(response.status, response.reason)

        if hasattr(buffer, 'write'):
            scratch = response.read(8192)
            transferred = 0

            while len(scratch) > 0:
                buffer.write(scratch)
                transferred += len(scratch)
                if callable(callback):
                    callback(transferred, self.size)
                scratch = response.read(8192)
            return None
        else:
            return response.read()

    def save_to_filename(self, filename, callback=None):
        """
        Save the contents of the object to filename.

        >>> container = connection['container1']
        >>> obj = container.get_object('backup_file')
        >>> obj.save_to_filename('./backup_file')

        @param filename: name of the file
        @type filename: str
        @param callback: function to be used as a progress callback
        @type callback: callable(transferred, size)
        """
        fobj = open(filename, 'wb')
        try:
            self.read(buffer=fobj, callback=callback)
        finally:
            fobj.close()

    @requires_name(InvalidObjectName)
    def stream(self, chunksize=8192, hdrs=None):
        """
        Return a generator of the remote storage object's data.

        Warning: The HTTP response is only complete after this generator
        has raised a StopIteration. No other methods can be called until
        this has occurred.

        >>> test_object.write('hello')
        >>> test_object.stream()
        <generator object at 0xb77939cc>
        >>> '-'.join(test_object.stream(chunksize=1))
        'h-e-l-l-o'

        @param chunksize: size in bytes yielded by the generator
        @type chunksize: number
        @param hdrs: an optional dict of headers to send in the request
        @type hdrs: dict
        @rtype: str generator
        @return: a generator which yields strings as the object is downloaded
        """
        self._name_check()
        response = self.container.conn.make_request('GET',
                path=[self.container.name, self.name], hdrs=hdrs)
        if response.status < 200 or response.status > 299:
            buff = response.read()
            raise ResponseError(response.status, response.reason)
        buff = response.read(chunksize)
        while len(buff) > 0:
            yield buff
            buff = response.read(chunksize)
        # I hate you httplib
        buff = response.read()

    @requires_name(InvalidObjectName)
    def sync_metadata(self):
        """
        Commits the metadata and custom headers to the remote storage system.

        >>> test_object = container['paradise_lost.pdf']
        >>> test_object.metadata = {'author': 'John Milton'}
        >>> test_object.headers = {'content-disposition': 'foo'}
        >>> test_objectt.sync_metadata()

        Object metadata can be set and retrieved through the object's
        .metadata attribute.
        """
        self._name_check()
        if self.metadata or self.headers:
            headers = self._make_headers()
            headers['Content-Length'] = "0"
            response = self.container.conn.make_request(
                'POST', [self.container.name, self.name], hdrs=headers,
                data='')
            response.read()
            if response.status != 202:
                raise ResponseError(response.status, response.reason)

    @requires_name(InvalidObjectName)
    def sync_manifest(self):
        """
        Commits the manifest to the remote storage system.

        >>> test_object = container['paradise_lost.pdf']
        >>> test_object.manifest = 'container/prefix'
        >>> test_object.sync_manifest()

        Object manifests can be set and retrieved through the object's
        .manifest attribute.
        """
        self._name_check()
        if self.manifest:
            headers = self._make_headers()
            headers['Content-Length'] = "0"
            response = self.container.conn.make_request(
                'PUT', [self.container.name, self.name], hdrs=headers,
                data='')
            response.read()
            if response.status < 200 or response.status > 299:
                raise ResponseError(response.status, response.reason)

    def __get_conn_for_write(self):
        headers = self._make_headers()

        headers['X-Auth-Token'] = self.container.conn.token

        path = "/%s/%s/%s" % (self.container.conn.uri.rstrip('/'), \
                unicode_quote(self.container.name), unicode_quote(self.name))

        # Requests are handled a little differently for writes ...
        http = self.container.conn.connection

        # TODO: more/better exception handling please
        http.putrequest('PUT', path)
        for hdr in headers:
            http.putheader(hdr, headers[hdr])
        http.putheader('User-Agent', self.container.conn.user_agent)
        http.endheaders()
        return http

    # pylint: disable-msg=W0622
    @requires_name(InvalidObjectName)
    def write(self, data='', verify=True, callback=None):
        """
        Write data to the remote storage system.

        By default, server-side verification is enabled, (verify=True), and
        end-to-end verification is performed using an md5 checksum. When
        verification is disabled, (verify=False), the etag attribute will
        be set to the value returned by the server, not one calculated
        locally. When disabling verification, there is no guarantee that
        what you think was uploaded matches what was actually stored. Use
        this optional carefully. You have been warned.

        A callback can be passed in for reporting on the progress of
        the upload. The callback should accept two integers, the first
        will be for the amount of data written so far, the second for
        the total size of the transfer.

        >>> test_object = container.create_object('file.txt')
        >>> test_object.content_type = 'text/plain'
        >>> fp = open('./file.txt')
        >>> test_object.write(fp)

        @param data: the data to be written
        @type data: str or file
        @param verify: enable/disable server-side checksum verification
        @type verify: boolean
        @param callback: function to be used as a progress callback
        @type callback: callable(transferred, size)
        """
        self._name_check()
        if isinstance(data, file):
            # pylint: disable-msg=E1101
            try:
                data.flush()
            except IOError:
                pass  # If the file descriptor is read-only this will fail
            self.size = int(os.fstat(data.fileno())[6])
        elif isinstance(data, basestring):
            data = StringIO.StringIO(data)
            self.size = data.len
        elif isinstance(data, StringIO.StringIO):
            self.size = data.len
        else:
            self.size = len(data)

        # If override is set (and _etag is not None), then the etag has
        # been manually assigned and we will not calculate our own.

        if not self._etag_override:
            self._etag = None

        if not self.content_type:
            # pylint: disable-msg=E1101
            type = None
            if hasattr(data, 'name'):
                type = mimetypes.guess_type(data.name)[0]
            self.content_type = type and type or 'application/octet-stream'

        http = self.__get_conn_for_write()

        response = None
        transfered = 0
        running_checksum = md5()

        buff = data.read(4096)
        try:
            while len(buff) > 0:
                http.send(buff)
                if verify and not self._etag_override:
                    running_checksum.update(buff)
                buff = data.read(4096)
                transfered += len(buff)
                if callable(callback):
                    callback(transfered, self.size)
            response = http.getresponse()
            buff = response.read()
        except timeout, err:
            if response:
                # pylint: disable-msg=E1101
                buff = response.read()
            raise err
        else:
            if verify and not self._etag_override:
                self._etag = running_checksum.hexdigest()

        # ----------------------------------------------------------------

        if (response.status < 200) or (response.status > 299):
            raise ResponseError(response.status, response.reason)

        # If verification has been disabled for this write, then set the
        # instances etag attribute to what the server returns to us.
        if not verify:
            for hdr in response.getheaders():
                if hdr[0].lower() == 'etag':
                    self._etag = hdr[1]

    @requires_name(InvalidObjectName)
    def copy_to(self, container_name, name):
        """
        Copy an object's contents to another location.
        """

        self._name_check()
        self._name_check(name)

        # This method implicitly disables verification.
        if not self._etag_override:
            self._etag = None

        headers = self._make_headers()
        headers['Destination'] = unicode_quote("%s/%s" % (container_name, name))
        headers['Content-Length'] = 0
        response = self.container.conn.make_request(
                   'COPY', [self.container.name, self.name], hdrs=headers, data='')
        buff = response.read()

        if response.status < 200 or response.status > 299:
            raise ResponseError(response.status, response.reason)

        # Reset the etag to what the server returns.
        for hdr in response.getheaders():
            if hdr[0].lower() == 'etag':
                self._etag = hdr[1]

    @requires_name(InvalidObjectName)
    def copy_from(self, container_name, name):
        """
        Copy another object's contents to this object.
        """

        self._name_check()
        self._name_check(name)

        # This method implicitly disables verification.
        if not self._etag_override:
            self._etag = None

        headers = self._make_headers()
        headers['X-Copy-From'] = unicode_quote("%s/%s" % (container_name, name))
        headers['Content-Length'] = 0
        response = self.container.conn.make_request(
                   'PUT', [self.container.name, self.name], hdrs=headers, data='')
        buff = response.read()

        if response.status < 200 or response.status > 299:
            raise ResponseError(response.status, response.reason)

        # Reset the etag to what the server returns.
        for hdr in response.getheaders():
            if hdr[0].lower() == 'etag':
                self._etag = hdr[1]

    @requires_name(InvalidObjectName)
    def send(self, iterable):
        """
        Write potentially transient data to the remote storage system using a
        generator or stream.

        If the object's size is not set, chunked transfer encoding will be
        used to upload the file.

        If the object's size attribute is set, it will be used as the
        Content-Length.  If the generator raises StopIteration prior to
        yielding the right number of bytes, an IncompleteSend exception is
        raised.

        If the content_type attribute is not set then a value of
        application/octet-stream will be used.

        Server-side verification will be performed if an md5 checksum is
        assigned to the etag property before calling this method,
        otherwise no verification will be performed, (verification
        can be performed afterward though by using the etag attribute
        which is set to the value returned by the server).

        >>> test_object = container.create_object('backup.tar.gz')
        >>> pfd = os.popen('tar -czvf - ./data/', 'r')
        >>> test_object.send(pfd)

        @param iterable: stream or generator which yields the content to upload
        @type iterable: generator or stream
        """
        self._name_check()

        if isinstance(iterable, basestring):
            # use write to buffer the string and avoid sending it 1 byte at a time
            self.write(iterable)

        if hasattr(iterable, 'read'):

            def file_iterator(file):
                chunk = file.read(4095)
                while chunk:
                    yield chunk
                    chunk = file.read(4095)
                raise StopIteration()
            iterable = file_iterator(iterable)

        # This method implicitly disables verification.
        if not self._etag_override:
            self._etag = None

        if not self.content_type:
            self.content_type = 'application/octet-stream'

        path = "/%s/%s/%s" % (self.container.conn.uri.rstrip('/'), \
                unicode_quote(self.container.name), unicode_quote(self.name))
        headers = self._make_headers()
        if self.size is None:
            del headers['Content-Length']
            headers['Transfer-Encoding'] = 'chunked'
        headers['X-Auth-Token'] = self.container.conn.token
        headers['User-Agent'] = self.container.conn.user_agent
        http = self.container.conn.connection
        http.putrequest('PUT', path)
        for key, value in headers.iteritems():
            http.putheader(key, value)
        http.endheaders()

        response = None
        transferred = 0
        try:
            for chunk in iterable:
                if self.size is None:
                    http.send("%X\r\n" % len(chunk))
                    http.send(chunk)
                    http.send("\r\n")
                else:
                    http.send(chunk)
                transferred += len(chunk)
            if self.size is None:
                http.send("0\r\n\r\n")
            # If the generator didn't yield enough data, stop, drop, and roll.
            elif transferred < self.size:
                raise IncompleteSend()
            response = http.getresponse()
            buff = response.read()
        except timeout, err:
            if response:
                # pylint: disable-msg=E1101
                response.read()
            raise err

        if (response.status < 200) or (response.status > 299):
            raise ResponseError(response.status, response.reason)

        for hdr in response.getheaders():
            if hdr[0].lower() == 'etag':
                self._etag = hdr[1]

    def load_from_filename(self, filename, verify=True, callback=None):
        """
        Put the contents of the named file into remote storage.

        >>> test_object = container.create_object('file.txt')
        >>> test_object.content_type = 'text/plain'
        >>> test_object.load_from_filename('./my_file.txt')

        @param filename: path to the file
        @type filename: str
        @param verify: enable/disable server-side checksum verification
        @type verify: boolean
        @param callback: function to be used as a progress callback
        @type callback: callable(transferred, size)
        """
        fobj = open(filename, 'rb')
        self.write(fobj, verify=verify, callback=callback)
        fobj.close()

    def _initialize(self):
        """
        Initialize the Object with values from the remote service (if any).
        """
        if not self.name:
            return False

        response = self.container.conn.make_request(
                'HEAD', [self.container.name, self.name])
        response.read()
        if response.status == 404:
            return False
        if (response.status < 200) or (response.status > 299):
            raise ResponseError(response.status, response.reason)
        for hdr in response.getheaders():
            if hdr[0].lower() == 'x-object-manifest':
                self.manifest = hdr[1]
            if hdr[0].lower() == 'content-type':
                self.content_type = hdr[1]
            if hdr[0].lower().startswith('x-object-meta-'):
                self.metadata[hdr[0][14:]] = hdr[1]
            if hdr[0].lower() == 'etag':
                self._etag = hdr[1]
                self._etag_override = False
            if hdr[0].lower() == 'content-length':
                self.size = int(hdr[1])
            if hdr[0].lower() == 'last-modified':
                self.last_modified = hdr[1]
        return True

    def __str__(self):
        return self.name

    def _name_check(self, name=None):
        if name is None:
            name = self.name
        if len(name) > consts.object_name_limit:
            raise InvalidObjectName(name)

    def _make_headers(self):
        """
        Returns a dictionary representing http headers based on the
        respective instance attributes.
        """
        headers = {}
        headers['Content-Length'] = (str(self.size) \
                                          and str(self.size) != "0") \
                                          and str(self.size) or "0"
        if self.manifest:
            headers['X-Object-Manifest'] = self.manifest
        if self._etag:
            headers['ETag'] = self._etag

        if self.content_type:
            headers['Content-Type'] = self.content_type
        else:
            headers['Content-Type'] = 'application/octet-stream'
        for key in self.metadata:
            if len(key) > consts.meta_name_limit:
                raise(InvalidMetaName(key))
            if len(self.metadata[key]) > consts.meta_value_limit:
                raise(InvalidMetaValue(self.metadata[key]))
            headers['X-Object-Meta-' + key] = self.metadata[key]
        headers.update(self.headers)
        return headers

    @classmethod
    def compute_md5sum(cls, fobj):
        """
        Given an open file object, returns the md5 hexdigest of the data.
        """
        checksum = md5()
        buff = fobj.read(4096)
        while buff:
            checksum.update(buff)
            buff = fobj.read(4096)
        fobj.seek(0)
        return checksum.hexdigest()
    
    def public_uri(self):
        """
        Retrieve the URI for this object, if its container is public.

        >>> container1 = connection['container1']
        >>> container1.make_public()
        >>> container1.create_object('file.txt').write('testing')
        >>> container1['file.txt'].public_uri()
        'http://c00061.cdn.cloudfiles.rackspacecloud.com/file.txt'

        @return: the public URI for this object
        @rtype: str
        """
        return "%s/%s" % (self.container.public_uri().rstrip('/'),
            unicode_quote(self.name))

    def public_ssl_uri(self):
        """
        Retrieve the SSL URI for this object, if its container is public.

        >>> container1 = connection['container1']
        >>> container1.make_public()
        >>> container1.create_object('file.txt').write('testing')
        >>> container1['file.txt'].public_ssl_uri()
        'https://c61.ssl.cf0.rackcdn.com/file.txt'

        @return: the public SSL URI for this object
        @rtype: str
        """
        return "%s/%s" % (self.container.public_ssl_uri().rstrip('/'),
                unicode_quote(self.name))

    def public_streaming_uri(self):
        """
        Retrieve the streaming URI for this object, if its container is public.

        >>> container1 = connection['container1']
        >>> container1.make_public()
        >>> container1.create_object('file.txt').write('testing')
        >>> container1['file.txt'].public_streaming_uri()
        'https://c61.stream.rackcdn.com/file.txt'

        @return: the public Streaming URI for this object
        @rtype: str
        """
        return "%s/%s" % (self.container.public_streaming_uri().rstrip('/'),
                unicode_quote(self.name))

    def purge_from_cdn(self, email=None):
        """
        Purge Edge cache for this object.
        You will be notified by email if one is provided when the
        job completes.

        >>> obj.purge_from_cdn("user@dmain.com")

        or

        >>> obj.purge_from_cdn("user@domain.com,user2@domain.com")

        or

        >>> obj.purge_from_cdn()

        @param email: A Valid email address
        @type email: str
        """
        if not self.container.conn.cdn_enabled:
            raise CDNNotEnabled()

        if email:
            hdrs = {"X-Purge-Email": email}
            response = self.container.conn.cdn_request('DELETE',
                       [self.container.name, self.name], hdrs=hdrs)
        else:
            response = self.container.conn.cdn_request('DELETE',
                       [self.container.name, self.name])

        if (response.status < 200) or (response.status >= 299):
            raise ResponseError(response.status, response.reason)


class ObjectResults(object):
    """
    An iterable results set object for Objects.

    This class implements dictionary- and list-like interfaces.
    """
    def __init__(self, container, objects=None):
        if objects is None:
            objects = []
        self._names = []
        self._objects = []
        for obj in objects:
            try:
                self._names.append(obj['name'])
            except KeyError:
                # pseudo-objects from a delimiter query don't have names
                continue
            else:
                self._objects.append(obj)
        self.container = container

    def __getitem__(self, key):
        return Object(self.container, object_record=self._objects[key])

    def __getslice__(self, i, j):
        return [Object(self.container, object_record=k) \
                    for k in self._objects[i:j]]

    def __contains__(self, item):
        return item in self._objects

    def __len__(self):
        return len(self._objects)

    def __repr__(self):
        return 'ObjectResults: %s objects' % len(self._objects)
    __str__ = __repr__

    def index(self, value, *args):
        """
        returns an integer for the first index of value
        """
        return self._names.index(value, *args)

    def count(self, value):
        """
        returns the number of occurrences of value
        """
        return self._names.count(value)

# vim:set ai sw=4 ts=4 tw=0 expandtab:

########NEW FILE########
__FILENAME__ = utils
""" See COPYING for license information. """

import re
from urllib    import quote
from urlparse  import urlparse
from errors    import InvalidUrl
from httplib   import HTTPConnection, HTTPSConnection, HTTP


def parse_url(url):
    """
    Given a URL, returns a 4-tuple containing the hostname, port,
    a path relative to root (if any), and a boolean representing
    whether the connection should use SSL or not.
    """
    (scheme, netloc, path, params, query, frag) = urlparse(url)

    # We only support web services
    if not scheme in ('http', 'https'):
        raise InvalidUrl('Scheme must be one of http or https')

    is_ssl = scheme == 'https' and True or False

    # Verify hostnames are valid and parse a port spec (if any)
    match = re.match('([a-zA-Z0-9\-\.]+):?([0-9]{2,5})?', netloc)

    if match:
        (host, port) = match.groups()
        if not port:
            port = is_ssl and '443' or '80'
    else:
        raise InvalidUrl('Invalid host and/or port: %s' % netloc)

    return (host, int(port), path.strip('/'), is_ssl)


def requires_name(exc_class):
    """Decorator to guard against invalid or unset names."""
    def wrapper(f):
        def decorator(*args, **kwargs):
            if not hasattr(args[0], 'name'):
                raise exc_class('')
            if not args[0].name:
                raise exc_class(args[0].name)
            return f(*args, **kwargs)
        decorator.__name__ = f.__name__
        decorator.__doc__ = f.__doc__
        decorator.parent_func = f
        return decorator
    return wrapper


def unicode_quote(s):
    """
    Utility function to address handling of unicode characters when using the quote
    method of the stdlib module urlparse. Converts unicode, if supplied, to utf-8
    and returns quoted utf-8 string.

    For more info see http://bugs.python.org/issue1712522 or
    http://mail.python.org/pipermail/python-dev/2006-July/067248.html
    """
    if isinstance(s, unicode):
        return quote(s.encode("utf-8"))
    else:
        return quote(str(s))


class THTTPConnection(HTTPConnection):
    def __init__(self, host, port, timeout):
        HTTPConnection.__init__(self, host, port)
        self.timeout = timeout

    def connect(self):
        HTTPConnection.connect(self)
        self.sock.settimeout(self.timeout)


class THTTP(HTTP):
    _connection_class = THTTPConnection

    def set_timeout(self, timeout):
        self._conn.timeout = timeout


class THTTPSConnection(HTTPSConnection):
    def __init__(self, host, port, timeout):
        HTTPSConnection.__init__(self, host, port)
        self.timeout = timeout

    def connect(self):
        HTTPSConnection.connect(self)
        self.sock.settimeout(self.timeout)


class THTTPS(HTTP):
    _connection_class = THTTPSConnection

    def set_timeout(self, timeout):
        self._conn.timeout = timeout

########NEW FILE########
__FILENAME__ = authentication_test
import unittest
from cloudfiles.authentication import BaseAuthentication as Auth
from misc import printdoc


class AuthenticationTest(unittest.TestCase):
    """
    Freerange Authentication class tests.
    """

    def test_get_uri(self):
        """
        Validate authentication uri construction.
        """
        self.assert_(self.auth.uri == "v1.0", \
               "authentication URL was not properly constructed")

    @printdoc
    def test_authenticate(self):
        """
        Sanity check authentication method stub (lame).
        """
        self.assert_(self.auth.authenticate() == (None, None, None), \
               "authenticate() did not return a two-tuple")

    @printdoc
    def test_headers(self):
        """
        Ensure headers are being set.
        """
        self.assert_(self.auth.headers['x-auth-user'] == 'jsmith', \
               "storage user header not properly assigned")
        self.assert_(self.auth.headers['x-auth-key'] == 'xxxxxxxx', \
               "storage password header not properly assigned")

    def setUp(self):
        self.auth = Auth('jsmith', 'xxxxxxxx')

    def tearDown(self):
        del self.auth

# vim:set ai ts=4 tw=0 sw=4 expandtab:

########NEW FILE########
__FILENAME__ = connectionpool_test
import unittest
from misc       import printdoc
from cloudfiles import ConnectionPool, Connection
from cloudfiles.authentication import MockAuthentication as Auth

class ConnectionPoolTest(unittest.TestCase):
    """
    ConnectionPool class tests.
    """
    @printdoc
    def test_connection(self):
        """
        Verify that ConnectionPool returns a Connection
        """
        conn = self.connpool.get()
        self.assert_(isinstance(conn, Connection))
        self.connpool.put(conn)

    @printdoc
    def test_connection(self):
        """
        Verify that ConnectionPool passes arguments through to Connections
        """
        conn = self.connpool.get()
        self.assert_(self.connpool.maxsize == 22)
        self.assert_(conn.timeout == 33)
        self.connpool.put(conn)

    def setUp(self):
        self.auth = Auth('jsmith', 'qwerty')
        self.connpool = ConnectionPool(auth=self.auth,
                                  poolsize=22,
                                  timeout=33,
                                  )
    def tearDown(self):
        del self.connpool
        del self.auth


# vim:set ai sw=4 ts=4 tw=0 expandtab:

########NEW FILE########
__FILENAME__ = connection_test
import unittest
from misc       import printdoc
from fakehttp   import CustomHTTPConnection
from cloudfiles import Connection, Container
from cloudfiles.authentication import MockAuthentication as Auth
from cloudfiles.errors import InvalidContainerName
from cloudfiles.consts import container_name_limit
import socket
class ConnectionTest(unittest.TestCase):
    """
    Freerange Connection class tests.
    """
    @printdoc
    def test_create_container(self):
        """
        Verify that Connection.create_container() returns a Container instance.
        """
        container = self.conn.create_container('container1')
        self.assert_(isinstance(container, Container))

    @printdoc
    def test_delete_container(self):
        """
        Simple sanity check of Connection.delete_container()
        """
        self.conn.delete_container('container1')

    @printdoc
    def test_get_all_containers(self):
        """
        Iterate a ContainerResults and verify that it returns Container instances.
        Validate that the count() and index() methods work as expected.
        """
        containers = self.conn.get_all_containers()
        for instance in containers:
            self.assert_(isinstance(instance, Container))
        self.assert_(containers.count('container1') == 1)
        self.assert_(containers.index('container3') == 2)

    @printdoc
    def test_get_container(self):
        """
        Verify that Connection.get_container() returns a Container instance.
        """
        container = self.conn.get_container('container1')
        self.assert_(isinstance(container, Container))

    @printdoc
    def test_list_containers(self):
        """
        Verify that Connection.list_containers() returns a list object.
        """
        self.assert_(isinstance(self.conn.list_containers(), list))

    @printdoc
    def test_list_containers_info(self):
        """
        Verify that Connection.list_containers_info() returns a list object.
        """
        self.assert_(isinstance(self.conn.list_containers_info(), list))

    @printdoc
    def test_bad_names(self):
        """
        Verify that methods do not accept invalid container names.
        """
        exccls = InvalidContainerName
        for badname in ('', 'yougivelove/abadname', 
                        'a'*(container_name_limit+1)):
            self.assertRaises(exccls, self.conn.create_container, badname)
            self.assertRaises(exccls, self.conn.get_container, badname)
            self.assertRaises(exccls, self.conn.delete_container, badname)

    @printdoc
    def test_account_info(self):
        """
        Test to see if the account has only one container
        """
        self.assert_(self.conn.get_info()[0] == 3)
    
    @printdoc
    def test_servicenet_cnx(self):
        """
        Test connection to servicenet.
        """
        auth = Auth('jsmith', 'qwerty')
        conn = Connection(auth=auth, servicenet=True)
        self.assert_(conn.connection_args[0].startswith("snet-"))
    @printdoc
    def test_socket_timeout(self):
        socket.setdefaulttimeout(21)
        self.conn.list_containers()
        self.assert_(socket.getdefaulttimeout() == 21.0)

    def setUp(self):
        self.auth = Auth('jsmith', 'qwerty')
        self.conn = Connection(auth=self.auth)
        self.conn.conn_class = CustomHTTPConnection
        self.conn.http_connect()
    def tearDown(self):
        del self.conn
        del self.auth

# vim:set ai sw=4 ts=4 tw=0 expandtab:

########NEW FILE########
__FILENAME__ = container_test
import unittest
from cloudfiles  import Connection, Container, Object
from cloudfiles.authentication import MockAuthentication as Auth
from cloudfiles.errors import InvalidContainerName, InvalidObjectName
from cloudfiles.consts import container_name_limit
from fakehttp   import CustomHTTPConnection
from misc       import printdoc


class ContainerTest(unittest.TestCase):
    """
    Freerange Container class tests.
    """

    @printdoc
    def test_create_object(self):
        """
        Verify that Container.create_object() returns an Object instance.
        """
        storage_object = self.container.create_object('object1')
        self.assert_(isinstance(storage_object, Object))

    @printdoc
    def test_delete_object(self):
        """
        Simple sanity check of Container.delete_object()
        """
        self.container.delete_object('object1')

    @printdoc
    def test_get_object(self):
        """
        Verify that Container.get_object() returns an Object instance.
        """
        storage_object = self.container.get_object('object1')
        self.assert_(isinstance(storage_object, Object))

    @printdoc
    def test_get_objects(self):
        """
        Iterate an ObjectResults and verify that it returns Object instances.
        Validate that the count() and index() methods work as expected.
        """
        objects = self.container.get_objects()
        for storage_object in objects:
            self.assert_(isinstance(storage_object, Object))
        self.assert_(objects.count('object1') == 1)
        self.assert_(objects.index('object3') == 2)

    @printdoc
    def test_get_objects_parametrized(self):
        """
        Iterate an ObjectResults and verify that it returns Object instances.
        Validate that the count() and index() methods work as expected.
        """
        objects = self.container.get_objects(prefix='object', limit=3,
                                             offset=3, path='/')
        for storage_object in objects:
            self.assert_(isinstance(storage_object, Object))
        self.assert_(objects.count('object4') == 1)
        self.assert_(objects.index('object6') == 2)

    @printdoc
    def test_list_objects_info(self):
        """
        Verify that Container.list_objects_info() returns a list object.
        """
        self.assert_(isinstance(self.container.list_objects(), list))

    @printdoc
    def test_list_objects(self):
        """
        Verify that Container.list_objects() returns a list object.
        """
        self.assert_(isinstance(self.container.list_objects(), list))

    @printdoc
    def test_list_objects_limited(self):
        """
        Verify that limit & order query parameters work.
        """
        self.assert_(len(self.container.list_objects(limit=3)) == 3)
        self.assert_(len(self.container.list_objects(limit=3, offset=3)) == 3)

    @printdoc
    def test_list_objects_prefixed(self):
        """
        Verify that the prefix query parameter works.
        """
        self.assert_(isinstance(
                self.container.list_objects(prefix='object'), list))

    @printdoc
    def test_list_objects_path(self):
        """
        Verify that the path query parameter works.
        """
        self.assert_(isinstance(
                self.container.list_objects(path='/'), list))

    @printdoc
    def test_list_objects_delimiter(self):
        """
        Verify that the delimiter query parameter works.
        """
        self.assert_(isinstance(
                self.container.list_objects(delimiter='/'), list))

    @printdoc
    def test_bad_name_assignment(self):
        """
        Ensure you can't assign an invalid name.
        """
        basket = Container(self.conn)
        try:
            basket.name = 'yougivelove/abadname'
            self.fail("InvalidContainerName exception not raised!")
        except InvalidContainerName:
            pass

        try:
            basket.name = 'a'*(container_name_limit+1)
            self.fail("InvalidContainerName exception not raised!")
        except InvalidContainerName:
            pass

    @printdoc
    def test_bad_object_name(self):
        """
        Verify that methods do not accept invalid container names.
        """
        self.assertRaises(InvalidObjectName, self.container.delete_object, '')

    def setUp(self):
        self.auth = Auth('jsmith', 'qwerty')
        self.conn = Connection(auth=self.auth)
        self.conn.conn_class = CustomHTTPConnection
        self.conn.http_connect()
        self.container = self.conn.get_container('container1')

    def tearDown(self):
        del self.container
        del self.conn
        del self.auth

# vim:set ai sw=4 ts=4 tw=0 expandtab:

########NEW FILE########
__FILENAME__ = fakehttp

"""
fakehttp/socket implementation

- TrackerSocket: an object which masquerades as a socket and responds to
  requests in a manner consistent with a *very* stupid CloudFS tracker. 
   
- CustomHTTPConnection: an object which subclasses httplib.HTTPConnection
  in order to replace it's socket with a TrackerSocket instance.

The unittests each have setup methods which create freerange connection 
instances that have had their HTTPConnection instances replaced by 
intances of CustomHTTPConnection.
"""

from sys import version_info
if version_info[0] <= 2 and version_info[1] < 6:
    from cloudfiles.utils import THTTPConnection as connbase
else:
    from httplib import HTTPConnection as connbase

import StringIO

class FakeSocket(object):
    def __init__(self):
        self._rbuffer = StringIO.StringIO()
        self._wbuffer = StringIO.StringIO()

    def close(self):
        pass

    def send(self, data, flags=0):
        self._rbuffer.write(data)
    sendall = send

    def recv(self, len=1024, flags=0):
        return self._wbuffer(len)

    def connect(self):
        pass

    def makefile(self, mode, flags):
        return self._wbuffer

class TrackerSocket(FakeSocket):
    def write(self, data):
        self._wbuffer.write(data)
    def read(self, length=-1):
        return self._rbuffer.read(length)

    def _create_GET_account_content(self, path, args):
        if args.has_key('format') and args['format'] == 'json':
            containers = []
            containers.append('[\n');
            containers.append('{"name":"container1","count":2,"bytes":78},\n')
            containers.append('{"name":"container2","count":1,"bytes":39},\n')
            containers.append('{"name":"container3","count":3,"bytes":117}\n')
            containers.append(']\n')
        elif args.has_key('format') and args['format'] == 'xml':
            containers = []
            containers.append('<?xml version="1.0" encoding="UTF-8"?>\n')
            containers.append('<account name="FakeAccount">\n')
            containers.append('<container><name>container1</name>'
                              '<count>2</count>'
                              '<bytes>78</bytes></container>\n')
            containers.append('<container><name>container2</name>'
                              '<count>1</count>'
                              '<bytes>39</bytes></container>\n')
            containers.append('<container><name>container3</name>'
                              '<count>3</count>'
                              '<bytes>117</bytes></container>\n')
            containers.append('</account>\n')
        else:
            containers = ['container%s\n' % i for i in range(1,4)]
        return ''.join(containers)

    def _create_GET_container_content(self, path, args):
        left = 0
        right = 9
        if args.has_key('offset'):
            left = int(args['offset'])
        if args.has_key('limit'):
            right = left + int(args['limit'])

        if args.has_key('format') and args['format'] == 'json':
            objects = []
            objects.append('{"name":"object1",'
                           '"hash":"4281c348eaf83e70ddce0e07221c3d28",'
                           '"bytes":14,'
                           '"content_type":"application\/octet-stream",'
                           '"last_modified":"2007-03-04 20:32:17"}')
            objects.append('{"name":"object2",'
                           '"hash":"b039efe731ad111bc1b0ef221c3849d0",'
                           '"bytes":64,'
                           '"content_type":"application\/octet-stream",'
                           '"last_modified":"2007-03-04 20:32:17"}')
            objects.append('{"name":"object3",'
                           '"hash":"4281c348eaf83e70ddce0e07221c3d28",'
                           '"bytes":14,'
                           '"content_type":"application\/octet-stream",'
                           '"last_modified":"2007-03-04 20:32:17"}')
            objects.append('{"name":"object4",'
                           '"hash":"b039efe731ad111bc1b0ef221c3849d0",'
                           '"bytes":64,'
                           '"content_type":"application\/octet-stream",'
                           '"last_modified":"2007-03-04 20:32:17"}')
            objects.append('{"name":"object5",'
                           '"hash":"4281c348eaf83e70ddce0e07221c3d28",'
                           '"bytes":14,'
                           '"content_type":"application\/octet-stream",'
                           '"last_modified":"2007-03-04 20:32:17"}')
            objects.append('{"name":"object6",'
                           '"hash":"b039efe731ad111bc1b0ef221c3849d0",'
                           '"bytes":64,'
                           '"content_type":"application\/octet-stream",'
                           '"last_modified":"2007-03-04 20:32:17"}')
            objects.append('{"name":"object7",'
                           '"hash":"4281c348eaf83e70ddce0e07221c3d28",'
                           '"bytes":14,'
                           '"content_type":"application\/octet-stream",'
                           '"last_modified":"2007-03-04 20:32:17"}')
            objects.append('{"name":"object8",'
                           '"hash":"b039efe731ad111bc1b0ef221c3849d0",'
                           '"bytes":64,'
                           '"content_type":"application\/octet-stream",'
                           '"last_modified":"2007-03-04 20:32:17"}')
            output = '[\n%s\n]\n' % (',\n'.join(objects[left:right]))
        elif args.has_key('format') and args['format'] == 'xml':
            objects = []
            objects.append('<object><name>object1</name>'
                           '<hash>4281c348eaf83e70ddce0e07221c3d28</hash>'
                           '<bytes>14</bytes>'
                           '<content_type>application/octet-stream</content_type>'
                           '<last_modified>2007-03-04 20:32:17</last_modified>'
                           '</object>\n')
            objects.append('<object><name>object2</name>'
                           '<hash>b039efe731ad111bc1b0ef221c3849d0</hash>'
                           '<bytes>64</bytes>'
                           '<content_type>application/octet-stream</content_type>'
                           '<last_modified>2007-03-04 20:32:17</last_modified>'
                           '</object>\n')
            objects.append('<object><name>object3</name>'
                           '<hash>4281c348eaf83e70ddce0e07221c3d28</hash>'
                           '<bytes>14</bytes>'
                           '<content_type>application/octet-stream</content_type>'
                           '<last_modified>2007-03-04 20:32:17</last_modified>'
                           '</object>\n')
            objects.append('<object><name>object4</name>'
                           '<hash>b039efe731ad111bc1b0ef221c3849d0</hash>'
                           '<bytes>64</bytes>'
                           '<content_type>application/octet-stream</content_type>'
                           '<last_modified>2007-03-04 20:32:17</last_modified>'
                           '</object>\n')
            objects.append('<object><name>object5</name>'
                           '<hash>4281c348eaf83e70ddce0e07221c3d28</hash>'
                           '<bytes>14</bytes>'
                           '<content_type>application/octet-stream</content_type>'
                           '<last_modified>2007-03-04 20:32:17</last_modified>'
                           '</object>\n')
            objects.append('<object><name>object6</name>'
                           '<hash>b039efe731ad111bc1b0ef221c3849d0</hash>'
                           '<bytes>64</bytes>'
                           '<content_type>application/octet-stream</content_type>'
                           '<last_modified>2007-03-04 20:32:17</last_modified>'
                           '</object>\n')
            objects.append('<object><name>object7</name>'
                           '<hash>4281c348eaf83e70ddce0e07221c3d28</hash>'
                           '<bytes>14</bytes>'
                           '<content_type>application/octet-stream</content_type>'
                           '<last_modified>2007-03-04 20:32:17</last_modified>'
                           '</object>\n')
            objects.append('<object><name>object8</name>'
                           '<hash>b039efe731ad111bc1b0ef221c3849d0</hash>'
                           '<bytes>64</bytes>'
                           '<content_type>application/octet-stream</content_type>'
                           '<last_modified>2007-03-04 20:32:17</last_modified>'
                           '</object>\n')
            objects = objects[left:right]
            objects.insert(0, '<?xml version="1.0" encoding="UTF-8"?>\n')
            objects.insert(1, '<container name="test_container_1"\n')
            objects.append('</container>\n')
            output = ''.join(objects)
        else:
            objects = ['object%s\n' % i for i in range(1,9)]
            objects = objects[left:right]
            output = ''.join(objects)

        # prefix/path don't make much sense given our test data
        if args.has_key('prefix') or args.has_key('path'):
            pass
        return output

    def render_GET(self, path, args):
        # Special path that returns 404 Not Found
        if (len(path) == 4) and (path[3] == 'bogus'):
            self.write('HTTP/1.1 404 Not Found\n')
            self.write('Content-Type: text/plain\n')
            self.write('Content-Length: 0\n')
            self.write('Connection: close\n\n')
            return

        self.write('HTTP/1.1 200 Ok\n')
        self.write('Content-Type: text/plain\n')
        if len(path) == 2:
            content = self._create_GET_account_content(path, args)
        elif len(path) == 3:
            content = self._create_GET_container_content(path, args)
        # Object
        elif len(path) == 4:
            content = 'I am a teapot, short and stout\n'
        self.write('Content-Length: %d\n' % len(content))
        self.write('Connection: close\n\n')
        self.write(content)

    def render_HEAD(self, path, args):
        # Account
        if len(path) == 2:
            self.write('HTTP/1.1 204 No Content\n')
            self.write('Content-Type: text/plain\n')
            self.write('Connection: close\n')
            self.write('X-Account-Container-Count: 3\n')
            self.write('X-Account-Bytes-Used: 234\n\n')
        else:
            self.write('HTTP/1.1 200 Ok\n')
            self.write('Content-Type: text/plain\n')
            self.write('ETag: d5c7f3babf6c602a8da902fb301a9f27\n')
            self.write('Content-Length: 21\n')
            self.write('Connection: close\n\n')

    def render_POST(self, path, args):
        self.write('HTTP/1.1 202 Ok\n')
        self.write('Connection: close\n\n')

    def render_PUT(self, path, args):
        self.write('HTTP/1.1 200 Ok\n')
        self.write('Content-Type: text/plain\n')
        self.write('Connection: close\n\n')
    render_DELETE = render_PUT

    def render(self, method, uri):
        if '?' in uri:
            parts = uri.split('?')
            query = parts[1].strip('&').split('&')
            args = dict([tuple(i.split('=', 1)) for i in query])
            path = parts[0].strip('/').split('/')
        else:
            args = {}
            path = uri.strip('/').split('/')

        if hasattr(self, 'render_%s' % method):
            getattr(self, 'render_%s' % method)(path, args)
        else:
            self.write('HTTP/1.1 406 Not Acceptable\n')
            self.write('Content-Type: text/plain\n')
            self.write('Connection: close\n')

    def makefile(self, mode, flags):
        self._rbuffer.seek(0)
        lines = self.read().splitlines()
        (method, uri, version) = lines[0].split()

        self.render(method, uri)

        self._wbuffer.seek(0)
        return self._wbuffer

class CustomHTTPConnection(connbase):
    def connect(self):
        self.sock = TrackerSocket()

    def send(self, data):
        self._wbuffer = data
        connbase.send(self, data)

if __name__ == '__main__':
    conn = CustomHTTPConnection('localhost', 8000)
    conn.request('HEAD', '/v1/account/container/object')
    response = conn.getresponse()
    print "Status:", response.status, response.reason
    for (key, value) in response.getheaders():
        print "%s: %s" % (key, value)
    print response.read()


# vim:set ai sw=4 ts=4 tw=0 expandtab:

########NEW FILE########
__FILENAME__ = misc
from sys import stdout


def printdoc(f):
    if f.__doc__:
        stdout.write('\n')

        testname = "[ %s ]" % f.__name__
        testname = testname.center(74) + '\n'
        stdout.write(testname)

        stdout.write('  ' + (74 * "~") + '\n')

        words = list()
        for l in f.__doc__.splitlines():
            words += l.split()

        lines = list()
        buff = ' '

        for word in words:
            if (len(buff) + len(word)) >= 78:
                lines.append(buff)
                buff = ' '
            buff += ' %s' % word
        lines.append(buff)

        stdout.write('\n'.join(lines))
        stdout.write('\n')
        stdout.write('  ' + (74 * "~") + '\n')
    else:
        print "%s: No docstring found!" % f.__name__
    return f

# vim:set ai sw=4 ts=4 tw=0 expandtab:

########NEW FILE########
__FILENAME__ = object_test
import unittest
try:
    from hashlib import md5
except ImportError:
    from md5 import md5
from cloudfiles        import Object, Connection
from cloudfiles.errors import ResponseError, InvalidObjectName,\
                              InvalidMetaName, InvalidMetaValue
from cloudfiles.authentication import MockAuthentication as Auth
from cloudfiles.consts import meta_name_limit, meta_value_limit,\
                              object_name_limit
from fakehttp          import CustomHTTPConnection
from misc              import printdoc
from tempfile          import mktemp
import os
from StringIO import StringIO


class ObjectTest(unittest.TestCase):
    """
    Freerange Object class tests.
    """

    @printdoc
    def test_read(self):
        """
        Test an Object's ability to read.
        """
        self.assert_("teapot" in self.storage_object.read())

    @printdoc
    def test_read_pass_headers(self):
        """
        Test an Object's ability to read when it has
        extra headers passed in.
        """
        hdrs = {}
        hdrs['x-bogus-header-1'] = 'bogus value'
        hdrs['x-bogus-header-2'] = 'boguser value'
        self.assert_("teapot" in self.storage_object.read(hdrs=hdrs))

    @printdoc
    def test_response_error(self):
        """
        Verify that reading a non-existent Object raises a ResponseError
        exception.
        """
        storage_object = self.container.create_object('bogus')
        self.assertRaises(ResponseError, storage_object.read)

    @printdoc
    def test_write(self):
        """
        Simple sanity test of Object.write()
        """
        self.storage_object.write('the rain in spain ...')
        self.assertEqual('the rain in spain ...', self.conn.connection._wbuffer)

    @printdoc
    def test_write_with_stringio(self):
        """
        Ensure write() can deal with a StringIO instance
        """
        self.storage_object.write(StringIO('the rain in spain ...'))
        self.assertEqual('the rain in spain ...', self.conn.connection._wbuffer)

    @printdoc
    def test_write_with_file(self):
        """
        Ensure write() can deal with a file instance
        """
        tmpnam = mktemp()
        try:
            fp = open(tmpnam, 'w')
            fp.write('the rain in spain ...')
            fp.close()
            fp = open(tmpnam, 'r')
            self.storage_object.write(fp)
            fp.close()
            self.assertEqual('the rain in spain ...', self.conn.connection._wbuffer)
        finally:
            os.unlink(tmpnam)

    @printdoc
    def test_send(self):
        """Sanity test of Object.send()."""
        gener = (part for part in ('the ', 'rain ', 'in ', 'spain ...'))
        self.storage_object.size = 21
        self.storage_object.content_type = "text/plain"
        self.storage_object.send(gener)

    @printdoc
    def test_sync_metadata(self):
        """
        Sanity check of Object.sync_metadata()
        """
        self.storage_object.headers['content-encoding'] = 'gzip'
        self.storage_object.metadata['unit'] = 'test'
        self.storage_object.sync_metadata()

    @printdoc
    def test_load_from_file(self):
        """
        Simple sanity test of Object.load_from_file().
        """
        path = os.path.join(os.path.dirname(__file__), 'samplefile.txt')
        self.storage_object.load_from_filename(path)

    @printdoc
    def test_save_to_filename(self):
        """Sanity test of Object.save_to_filename()."""
        tmpnam = mktemp()
        self.storage_object.save_to_filename(tmpnam)
        rdr = open(tmpnam, 'r')
        try:
            self.assert_(rdr.read() == self.storage_object.read(),
                   "save_to_filename() stored invalid content!")
        finally:
            rdr.close()
            os.unlink(tmpnam)

    @printdoc
    def test_compute_md5sum(self):
        """
        Verify that the Object.compute_md5sum() class method returns an
        accurate md5 sum value.
        """
        f = open('/bin/ls', 'r')
        m = md5()
        m.update(f.read())
        sum1 = m.hexdigest()
        f.seek(0)
        try:
            sum2 = Object.compute_md5sum(f)
            self.assert_(sum1 == sum2, "%s != %s" % (sum1, sum2))
        finally:
            f.close()

    @printdoc
    def test_bad_name(self):
        """
        Ensure you can't assign an invalid object name.
        """
        obj = Object(self.container)    # name is None
        self.assertRaises(InvalidObjectName, obj.read)
        self.assertRaises(InvalidObjectName, obj.stream)
        self.assertRaises(InvalidObjectName, obj.sync_metadata)
        self.assertRaises(InvalidObjectName, obj.write, '')

        obj.name = ''    # name is zero-length string
        self.assertRaises(InvalidObjectName, obj.read)
        self.assertRaises(InvalidObjectName, obj.stream)
        self.assertRaises(InvalidObjectName, obj.sync_metadata)
        self.assertRaises(InvalidObjectName, obj.write, '')

        obj.name = 'a'*(object_name_limit+1) # too-long string
        self.assertRaises(InvalidObjectName, obj.read)
        self.assertRaises(InvalidObjectName, obj.stream().next)
        self.assertRaises(InvalidObjectName, obj.sync_metadata)
        self.assertRaises(InvalidObjectName, obj.write, '')

        obj.name = 'a'*(object_name_limit) # ok name
        obj.read()
        obj.stream()
        obj.sync_metadata()
        obj.write('')

    @printdoc
    def test_bad_meta_data(self):
        """
        Ensure you can't sync bad metadata.
        """
        # too-long name
        self.storage_object.metadata['a'*(meta_name_limit+1)] = 'test'
        self.assertRaises(InvalidMetaName,
                          self.storage_object.sync_metadata)
        del(self.storage_object.metadata['a'*(meta_name_limit+1)])

        # too-long value
        self.storage_object.metadata['a'*(meta_name_limit)] = \
                                     'a'*(meta_value_limit+1)
        self.assertRaises(InvalidMetaValue,
                          self.storage_object.sync_metadata)

    @printdoc
    def test_account_size(self):
        """
        Test to see that the total bytes on the account is size of
        the samplefile
        """
        self.assert_(self.conn.get_info()[1] == 234)

    def setUp(self):
        self.auth = Auth('jsmith', 'qwerty')
        self.conn = Connection(auth=self.auth)
        self.conn.conn_class = CustomHTTPConnection
        self.conn.http_connect()
        self.container = self.conn.get_container('container1')
        self.storage_object = self.container.get_object('object1')

    def tearDown(self):
        del self.storage_object
        del self.container
        del self.conn
        del self.auth


# vim:set ai sw=4 ts=4 tw=0 expandtab:

########NEW FILE########
__FILENAME__ = utils_test

import unittest
from misc             import printdoc
from cloudfiles.utils  import unicode_quote, parse_url

@printdoc
def test_parse_url():
    """
    Validate that the parse_url() function properly returns the hostname,
    port number, path (if any), and ssl boolean. Attempts several
    different URL permutations, (5 tests total).
    """
    urls = {
        'http_noport_nopath': {
            'url':   'http://bogus.not',
            'host':  'bogus.not',
            'port':  80,
            'path':  '',
            'ssl':   False,
        },
        'https_noport_nopath': {
            'url':   'https://bogus.not',
            'host':  'bogus.not',
            'port':  443,
            'path':  '',
            'ssl':   True,
        },
        'http_noport_withpath': {
            'url':   'http://bogus.not/v1/bar',
            'host':  'bogus.not',
            'port':  80,
            'path':  'v1/bar',
            'ssl':   False,
        },
        'http_withport_nopath': {
            'url':   'http://bogus.not:8000',
            'host':  'bogus.not',
            'port':  8000,
            'path':  '',
            'ssl':   False,
        },
        'https_withport_withpath': {
            'url':   'https://bogus.not:8443/v1/foo',
            'host':  'bogus.not',
            'port':  8443,
            'path':  'v1/foo',
            'ssl':   True,
        },
    }
    for url in urls:
        yield check_url, url, urls[url]

def check_url(test, urlspec):
    (host, port, path, ssl) = parse_url(urlspec['url'])
    assert host == urlspec['host'], "%s failed on host assertion" % test
    assert port == urlspec['port'], "%s failed on port assertion" % test
    assert path == urlspec['path'], "%s failed on path assertion" % test
    assert ssl == urlspec['ssl'], "%s failed on ssl assertion" % test

def test_unicode_quote():
    """
    Ensure that unicode strings are encoded as utf-8 properly for use with the
    quote method of the urlparse stdlib.
    """
    assert unicode_quote("non-unicode text") == "non-unicode%20text"
    assert unicode_quote(u'\xe1gua.txt') == "%C3%A1gua.txt"

# vim:set ai sw=4 ts=4 tw=0 expandtab:

########NEW FILE########
