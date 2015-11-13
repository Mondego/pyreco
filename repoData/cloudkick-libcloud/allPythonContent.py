__FILENAME__ = ec2_demo
#!/usr/bin/env python
#
# Licensed to the Apache Software Foundation (ASF) under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

#
# This example provides both a running script (invoke from command line)
# and an importable module one can play with in Interactive Mode.
#
# See docstrings for usage examples.
#

try:
    import secrets
except:
    pass
import sys; sys.path.append('..')

from libcloud.compute.types import Provider
from libcloud.providers import get_driver

from pprint import pprint

def main(argv):
    """Main EC2 Demo

    When invoked from the command line, it will connect using secrets.py
    (see secrets.py.dist for setup instructions), and perform the following
    tasks:

    - List current nodes
    - List available images (up to 10)
    - List available sizes (up to 10)
    """
    # Load EC2 driver
    EC2Driver = get_driver(Provider.EC2_US_EAST)

    # Instantiate with Access ID and Secret Key
    # (see secrets.py.dist)
    try:
        ec2 = EC2Driver(secrets.EC2_ACCESS_ID, secrets.EC2_SECRET_KEY)
        print ">> Loading nodes..."
        nodes = ec2.list_nodes()
        pprint(nodes)
    except NameError, e:
        print ">> Fatal Error: %s" % e
        print "   (Hint: modify secrets.py.dist)"
        return 1
    except Exception, e:
        print ">> Fatal error: %s" % e
        return 1
    
    print ">> Loading images... (showing up to 10)"
    images = ec2.list_images()
    pprint(images[:10])

    print ">> Loading sizes... (showing up to 10)"
    sizes = ec2.list_sizes()
    pprint(sizes[:10])

    return 0

def get_ec2(**kwargs):
    """An easy way to play with the EC2 Driver in Interactive Mode

    # Load credentials from secrets.py
    >>> from ec2demo import get_ec2
    >>> ec2 = get_ec2()

    # Or, provide credentials
    >>> from ec2demo import get_ec2
    >>> ec2 = get_ec2(access_id='xxx', secret_key='yyy')

    # Do things
    >>> ec2.load_nodes()
    >>> images = ec2.load_images()
    >>> sizes = ec2.load_sizes()
    """
    access_id = kwargs.get('access_id', secrets.EC2_ACCESS_ID)
    secret_key = kwargs.get('secret_key', secrets.EC2_SECRET_KEY)
    
    EC2Driver = get_driver(Provider.EC2_US_EAST)
    return EC2Driver(access_id, secret_key)

def create_demo(ec2):
    """Create EC2 Node Demo

    >>> from ec2demo import get_ec2, create_demo
    >>> ec2 = get_ec2()
    >>> node = create_demo(ec2)
    >>> node
    <Node: uuid=9d1..., name=i-7b1fa910, state=3, public_ip=[''], ...>

    And to destroy the node:

    >>> node.destroy()

    If you've accidentally quit and need to destroy the node:

    >>> from ec2demo import get_ec2
    >>> nodes = ec2.list_nodes()
    >>> nodes[0].destroy() # assuming it's the first node
    """
    images = ec2.list_images()
    image = [image for image in images if 'ami' in image.id][0]
    sizes = ec2.list_sizes()
    size = sizes[0]

    # Note, name is ignored by EC2
    node = ec2.create_node(name='create_image_demo',
                           image=image,
                           size=size)
    return node

if __name__ == '__main__':
    sys.exit(main(sys.argv))

########NEW FILE########
__FILENAME__ = example_compute
# Licensed to the Apache Software Foundation (ASF) under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
from libcloud.compute.types import Provider
from libcloud.compute.providers import get_driver

EC2 = get_driver(Provider.EC2_US_EAST)
Slicehost = get_driver(Provider.SLICEHOST)
Rackspace = get_driver(Provider.RACKSPACE)

drivers = [ EC2('access key id', 'secret key'), 
            Slicehost('api key'), 
            Rackspace('username', 'api key') ]

nodes = [ driver.list_nodes() for driver in drivers ]

print nodes
# [ <Node: provider=Amazon, status=RUNNING, name=bob, ip=1.2.3.4.5>,
# <Node: provider=Slicehost, status=REBOOT, name=korine, ip=6.7.8.9.10>, ... ]

# grab the node named "test"
node = filter(lambda x: x.name == 'test', nodes)[0]

# reboot "test"
node.reboot()

########NEW FILE########
__FILENAME__ = example_storage
# Licensed to the Apache Software Foundation (ASF) under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from pprint import pprint

from libcloud.storage.types import Provider
from libcloud.storage.providers import get_driver

CloudFiles = get_driver(Provider.CloudFiles)

driver = CloudFiles('access key id', 'secret key')

containers = driver.list_containers()
container_objects = driver.list_container_objects(containers[0])

pprint(containers)
pprint(container_objects)

########NEW FILE########
__FILENAME__ = base
# Licensed to the Apache Software Foundation (ASF) under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from libcloud.common.base import RawResponse, Response, LoggingConnection
from libcloud.common.base import LoggingHTTPSConnection, LoggingHTTPConnection
from libcloud.common.base import ConnectionKey, ConnectionUserAndKey
from libcloud.compute.base import Node, NodeSize, NodeImage
from libcloud.compute.base import NodeLocation, NodeAuthSSHKey, NodeAuthPassword
from libcloud.compute.base import NodeDriver, is_private_subnet

from libcloud.utils import deprecated_warning

deprecated_warning(__name__)

########NEW FILE########
__FILENAME__ = base
# Licensed to the Apache Software Foundation (ASF) under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import httplib
import urllib
import time
import hashlib
import StringIO
import ssl
import os
import socket
import struct

from pipes import quote as pquote

import libcloud

from libcloud.httplib_ssl import LibcloudHTTPSConnection
from httplib import HTTPConnection as LibcloudHTTPConnection

class RawResponse(object):

    def __init__(self, response=None):
        self._status = None
        self._response = None
        self._headers = {}
        self._error = None
        self._reason = None

    @property
    def response(self):
        if not self._response:
            self._response = self.connection.connection.getresponse()
        return self._response

    @property
    def status(self):
        if not self._status:
            self._status = self.response.status
        return self._status

    @property
    def headers(self):
        if not self._headers:
            self._headers = dict(self.response.getheaders())
        return self._headers

    @property
    def reason(self):
        if not self._reason:
            self._reason = self.response.reason
        return self._reason

class Response(object):
    """
    A Base Response class to derive from.
    """
    NODE_STATE_MAP = {}

    object = None
    body = None
    status = httplib.OK
    headers = {}
    error = None
    connection = None

    def __init__(self, response):
        self.body = response.read()
        self.status = response.status
        self.headers = dict(response.getheaders())
        self.error = response.reason

        if not self.success():
            raise Exception(self.parse_error())

        self.object = self.parse_body()

    def parse_body(self):
        """
        Parse response body.

        Override in a provider's subclass.

        @return: Parsed body.
        """
        return self.body

    def parse_error(self):
        """
        Parse the error messages.

        Override in a provider's subclass.

        @return: Parsed error.
        """
        return self.body

    def success(self):
        """
        Determine if our request was successful.

        The meaning of this can be arbitrary; did we receive OK status? Did
        the node get created? Were we authenticated?

        @return: C{True} or C{False}
        """
        return self.status == httplib.OK or self.status == httplib.CREATED

#TODO: Move this to a better location/package
class LoggingConnection():
    """
    Debug class to log all HTTP(s) requests as they could be made
    with the C{curl} command.

    @cvar log: file-like object that logs entries are written to.
    """
    log = None

    def _log_response(self, r):
        rv = "# -------- begin %d:%d response ----------\n" % (id(self), id(r))
        ht = ""
        v = r.version
        if r.version == 10:
            v = "HTTP/1.0"
        if r.version == 11:
            v = "HTTP/1.1"
        ht += "%s %s %s\r\n" % (v, r.status, r.reason)
        body = r.read()
        for h in r.getheaders():
            ht += "%s: %s\r\n" % (h[0].title(), h[1])
        ht += "\r\n"
        # this is evil. laugh with me. ha arharhrhahahaha
        class fakesock:
            def __init__(self, s):
                self.s = s
            def makefile(self, mode, foo):
                return StringIO.StringIO(self.s)
        rr = r
        if r.chunked:
            ht += "%x\r\n" % (len(body))
            ht += body
            ht += "\r\n0\r\n"
        else:
            ht += body
        rr = httplib.HTTPResponse(fakesock(ht),
                                  method=r._method,
                                  debuglevel=r.debuglevel)
        rr.begin()
        rv += ht
        rv += ("\n# -------- end %d:%d response ----------\n"
               % (id(self), id(r)))
        return (rr, rv)

    def _log_curl(self, method, url, body, headers):
        cmd = ["curl", "-i"]

        cmd.extend(["-X", pquote(method)])

        for h in headers:
            cmd.extend(["-H", pquote("%s: %s" % (h, headers[h]))])

        # TODO: in python 2.6, body can be a file-like object.
        if body is not None and len(body) > 0:
            cmd.extend(["--data-binary", pquote(body)])

        cmd.extend([pquote("https://%s:%d%s" % (self.host, self.port, url))])
        return " ".join(cmd)

class LoggingHTTPSConnection(LoggingConnection, LibcloudHTTPSConnection):
    """
    Utility Class for logging HTTPS connections
    """

    def getresponse(self):
        r = LibcloudHTTPSConnection.getresponse(self)
        if self.log is not None:
            r, rv = self._log_response(r)
            self.log.write(rv + "\n")
            self.log.flush()
        return r

    def request(self, method, url, body=None, headers=None):
        headers.update({'X-LC-Request-ID': str(id(self))})
        if self.log is not None:
            pre = "# -------- begin %d request ----------\n"  % id(self)
            self.log.write(pre +
                           self._log_curl(method, url, body, headers) + "\n")
            self.log.flush()
        return LibcloudHTTPSConnection.request(self, method, url, body, headers)

class LoggingHTTPConnection(LoggingConnection, LibcloudHTTPConnection):
    """
    Utility Class for logging HTTP connections
    """

    def getresponse(self):
        r = LibcloudHTTPConnection.getresponse(self)
        if self.log is not None:
            r, rv = self._log_response(r)
            self.log.write(rv + "\n")
            self.log.flush()
        return r

    def request(self, method, url, body=None, headers=None):
        headers.update({'X-LC-Request-ID': str(id(self))})
        if self.log is not None:
            pre = "# -------- begin %d request ----------\n"  % id(self)
            self.log.write(pre +
                           self._log_curl(method, url, body, headers) + "\n")
            self.log.flush()
        return LibcloudHTTPConnection.request(self, method, url,
                                               body, headers)

class ConnectionKey(object):
    """
    A Base Connection class to derive from.
    """
    #conn_classes = (LoggingHTTPSConnection)
    conn_classes = (LibcloudHTTPConnection, LibcloudHTTPSConnection)

    responseCls = Response
    rawResponseCls = RawResponse
    connection = None
    host = '127.0.0.1'
    port = (80, 443)
    secure = 1
    driver = None
    action = None

    def __init__(self, key, secure=True, host=None, force_port=None):
        """
        Initialize `user_id` and `key`; set `secure` to an C{int} based on
        passed value.
        """
        self.key = key
        self.secure = secure and 1 or 0
        self.ua = []
        if host:
            self.host = host

        if force_port:
            self.port = (force_port, force_port)

    def connect(self, host=None, port=None):
        """
        Establish a connection with the API server.

        @type host: C{str}
        @param host: Optional host to override our default

        @type port: C{int}
        @param port: Optional port to override our default

        @returns: A connection
        """
        host = host or self.host
        port = port or self.port[self.secure]

        kwargs = {'host': host, 'port': port}

        connection = self.conn_classes[self.secure](**kwargs)
        # You can uncoment this line, if you setup a reverse proxy server
        # which proxies to your endpoint, and lets you easily capture
        # connections in cleartext when you setup the proxy to do SSL
        # for you
        #connection = self.conn_classes[False]("127.0.0.1", 8080)

        self.connection = connection

    def _user_agent(self):
        return 'libcloud/%s (%s)%s' % (
                  libcloud.__version__,
                  self.driver.name,
                  "".join([" (%s)" % x for x in self.ua]))

    def user_agent_append(self, token):
        """
        Append a token to a user agent string.

        Users of the library should call this to uniquely identify thier requests
        to a provider.

        @type token: C{str}
        @param token: Token to add to the user agent.
        """
        self.ua.append(token)

    def request(self,
                action,
                params=None,
                data='',
                headers=None,
                method='GET',
                raw=False):
        """
        Request a given `action`.

        Basically a wrapper around the connection
        object's `request` that does some helpful pre-processing.

        @type action: C{str}
        @param action: A path

        @type params: C{dict}
        @param params: Optional mapping of additional parameters to send. If
            None, leave as an empty C{dict}.

        @type data: C{unicode}
        @param data: A body of data to send with the request.

        @type headers: C{dict}
        @param headers: Extra headers to add to the request
            None, leave as an empty C{dict}.

        @type method: C{str}
        @param method: An HTTP method such as "GET" or "POST".

        @return: An instance of type I{responseCls}
        """
        if params is None:
            params = {}
        if headers is None:
            headers = {}

        self.action = action
        self.method = method
        # Extend default parameters
        params = self.add_default_params(params)
        # Extend default headers
        headers = self.add_default_headers(headers)
        # We always send a content length and user-agent header
        headers.update({'User-Agent': self._user_agent()})
        headers.update({'Host': self.host})
        # Encode data if necessary
        if data != '' and data != None:
            data = self.encode_data(data)

        if data is not None:
            headers.update({'Content-Length': str(len(data))})

        if params:
            url = '?'.join((action, urllib.urlencode(params)))
        else:
            url = action

        # Removed terrible hack...this a less-bad hack that doesn't execute a
        # request twice, but it's still a hack.
        self.connect()
        try:
            # @TODO: Should we just pass File object as body to request method
            # instead of dealing with splitting and sending the file ourselves?
            if raw:
                self.connection.putrequest(method, action)

                for key, value in headers.iteritems():
                    self.connection.putheader(key, value)

                self.connection.endheaders()
            else:
                self.connection.request(method=method, url=url, body=data,
                                        headers=headers)
        except ssl.SSLError, e:
            raise ssl.SSLError(str(e))

        if raw:
            response = self.rawResponseCls()
        else:
            response = self.responseCls(self.connection.getresponse())

        response.connection = self
        return response

    def add_default_params(self, params):
        """
        Adds default parameters (such as API key, version, etc.)
        to the passed `params`

        Should return a dictionary.
        """
        return params

    def add_default_headers(self, headers):
        """
        Adds default headers (such as Authorization, X-Foo-Bar)
        to the passed `headers`

        Should return a dictionary.
        """
        return headers

    def encode_data(self, data):
        """
        Encode body data.

        Override in a provider's subclass.
        """
        return data

class ConnectionUserAndKey(ConnectionKey):
    """
    Base connection which accepts a user_id and key
    """

    user_id = None

    def __init__(self, user_id, key, secure=True, host=None, port=None):
        super(ConnectionUserAndKey, self).__init__(key, secure, host, port)
        self.user_id = user_id

########NEW FILE########
__FILENAME__ = rackspace
# Licensed to the Apache Software Foundation (ASF) under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Common utilities for Rackspace Cloud Servers and Cloud Files
"""
import httplib
from urllib2 import urlparse
from libcloud.common.base import ConnectionUserAndKey
from libcloud.compute.types import InvalidCredsError

AUTH_HOST_US='auth.api.rackspacecloud.com'
AUTH_HOST_UK='lon.auth.api.rackspacecloud.com'
AUTH_API_VERSION = 'v1.0'

class RackspaceBaseConnection(ConnectionUserAndKey):
    def __init__(self, user_id, key, secure):
        self.cdn_management_url = None
        self.storage_url = None
        self.auth_token = None
        self.request_path = None
        self.__host = None
        super(RackspaceBaseConnection, self).__init__(user_id, key, secure=secure)

    def add_default_headers(self, headers):
        headers['X-Auth-Token'] = self.auth_token
        headers['Accept'] = self.accept_format
        return headers

    @property
    def host(self):
        """
        Rackspace uses a separate host for API calls which is only provided
        after an initial authentication request. If we haven't made that
        request yet, do it here. Otherwise, just return the management host.
        """
        if not self.__host:
            # Initial connection used for authentication
            conn = self.conn_classes[self.secure](self.auth_host, self.port[self.secure])
            conn.request(
                method='GET',
                url='/%s' % (AUTH_API_VERSION),
                headers={
                    'X-Auth-User': self.user_id,
                    'X-Auth-Key': self.key
                }
            )

            resp = conn.getresponse()

            if resp.status != httplib.NO_CONTENT:
                raise InvalidCredsError()

            headers = dict(resp.getheaders())

            try:
                self.server_url = headers['x-server-management-url']
                self.storage_url = headers['x-storage-url']
                self.cdn_management_url = headers['x-cdn-management-url']
                self.auth_token = headers['x-auth-token']
            except KeyError:
                raise InvalidCredsError()

            scheme, server, self.request_path, param, query, fragment = (
                urlparse.urlparse(getattr(self, self._url_key))
            )

            if scheme is "https" and self.secure is not True:
                raise InvalidCredsError()

            # Set host to where we want to make further requests to;
            self.__host = server
            conn.close()

        return self.__host

########NEW FILE########
__FILENAME__ = types
# Licensed to the Apache Software Foundation (ASF) under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

class LibcloudError(Exception):
    """The base class for other libcloud exceptions"""
    def __init__(self, value, driver=None):
        self.value = value
        self.driver = driver

    def __str__(self):
        return "<LibcloudError in "+ repr(self.driver) +" "+ repr(self.value) + ">"

class MalformedResponseError(LibcloudError):
    """Exception for the cases when a provider returns a malformed
    response, e.g. you request JSON and provider returns 
    '<h3>something</h3>' due to some error on their side."""
    def __init__(self, value, body=None, driver=None):
      self.value = value
      self.driver = driver
      self.body = body
    def __str__(self):
        return "<MalformedResponseException in "+ repr(self.driver) +" "+ repr(self.value) +">: "+ repr(self.body)

class InvalidCredsError(LibcloudError):
    """Exception used when invalid credentials are used on a provider."""
    def __init__(self, value='Invalid credentials with the provider', driver=None):
        self.value = value
        self.driver = driver
    def __str__(self):
        return repr(self.value)

"""Deprecated alias of L{InvalidCredsError}"""
InvalidCredsException = InvalidCredsError

########NEW FILE########
__FILENAME__ = base
# Licensed to the Apache Software Foundation (ASF) under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Provides base classes for working with drivers
"""
import httplib, urllib
import time
import hashlib
import StringIO
import ssl
import os
import socket
import struct

from libcloud.common.base import ConnectionKey, ConnectionUserAndKey
from libcloud.compute.types import NodeState, DeploymentError
from libcloud.compute.ssh import SSHClient
from libcloud.httplib_ssl import LibcloudHTTPSConnection
from httplib import HTTPConnection as LibcloudHTTPConnection

class Node(object):
    """
    Provide a common interface for handling nodes of all types.

    The Node object provides the interface in libcloud through which
    we can manipulate nodes in different cloud providers in the same
    way.  Node objects don't actually do much directly themselves,
    instead the node driver handles the connection to the node.

    You don't normally create a node object yourself; instead you use
    a driver and then have that create the node for you.

    >>> from libcloud.compute.drivers.dummy import DummyNodeDriver
    >>> driver = DummyNodeDriver(0)
    >>> node = driver.create_node()
    >>> node.public_ip[0]
    '127.0.0.3'
    >>> node.name
    'dummy-3'

    You can also get nodes from the driver's list_node function.

    >>> node = driver.list_nodes()[0]
    >>> node.name
    'dummy-1'

    the node keeps a reference to its own driver which means that we
    can work on nodes from different providers without having to know
    which is which.

    >>> driver = DummyNodeDriver(72)
    >>> node2 = driver.create_node()
    >>> node.driver.creds
    0
    >>> node2.driver.creds
    72

    Althrough Node objects can be subclassed, this isn't normally
    done.  Instead, any driver specific information is stored in the
    "extra" proproperty of the node.

    >>> node.extra
    {'foo': 'bar'}

    """

    def __init__(self, id, name, state, public_ip, private_ip,
                 driver, extra=None):
        self.id = str(id) if id else None
        self.name = name
        self.state = state
        self.public_ip = public_ip
        self.private_ip = private_ip
        self.driver = driver
        self.uuid = self.get_uuid()
        if not extra:
            self.extra = {}
        else:
            self.extra = extra

    def get_uuid(self):
        """Unique hash for this node

        @return: C{string}

        The hash is a function of an SHA1 hash of the node's ID and
        its driver which means that it should be unique between all
        nodes.  In some subclasses (e.g. GoGrid) there is no ID
        available so the public IP address is used.  This means that,
        unlike a properly done system UUID, the same UUID may mean a
        different system install at a different time

        >>> from libcloud.compute.drivers.dummy import DummyNodeDriver
        >>> driver = DummyNodeDriver(0)
        >>> node = driver.create_node()
        >>> node.get_uuid()
        'd3748461511d8b9b0e0bfa0d4d3383a619a2bb9f'

        Note, for example, that this example will always produce the
        same UUID!
        """
        return hashlib.sha1("%s:%d" % (self.id,self.driver.type)).hexdigest()

    def reboot(self):
        """Reboot this node

        @return: C{bool}

        This calls the node's driver and reboots the node

        >>> from libcloud.compute.drivers.dummy import DummyNodeDriver
        >>> driver = DummyNodeDriver(0)
        >>> node = driver.create_node()
        >>> from libcloud.compute.types import NodeState
        >>> node.state == NodeState.RUNNING
        True
        >>> node.state == NodeState.REBOOTING
        False
        >>> node.reboot()
        True
        >>> node.state == NodeState.REBOOTING
        True
        """
        return self.driver.reboot_node(self)

    def destroy(self):
        """Destroy this node

        @return: C{bool}

        This calls the node's driver and destroys the node

        >>> from libcloud.compute.drivers.dummy import DummyNodeDriver
        >>> driver = DummyNodeDriver(0)
        >>> from libcloud.compute.types import NodeState
        >>> node = driver.create_node()
        >>> node.state == NodeState.RUNNING
        True
        >>> node.destroy()
        True
        >>> node.state == NodeState.RUNNING
        False

        """
        return self.driver.destroy_node(self)

    def __repr__(self):
        return (('<Node: uuid=%s, name=%s, state=%s, public_ip=%s, '
                 'provider=%s ...>')
                % (self.uuid, self.name, self.state, self.public_ip,
                   self.driver.name))


class NodeSize(object):
    """
    A Base NodeSize class to derive from.

    NodeSizes are objects which are typically returned a driver's
    list_sizes function.  They contain a number of different
    parameters which define how big an image is.

    The exact parameters available depends on the provider.

    N.B. Where a parameter is "unlimited" (for example bandwidth in
    Amazon) this will be given as 0.

    >>> from libcloud.compute.drivers.dummy import DummyNodeDriver
    >>> driver = DummyNodeDriver(0)
    >>> size = driver.list_sizes()[0]
    >>> size.ram
    128
    >>> size.bandwidth
    500
    >>> size.price
    4
    """

    def __init__(self, id, name, ram, disk, bandwidth, price, driver):
        self.id = str(id)
        self.name = name
        self.ram = ram
        self.disk = disk
        self.bandwidth = bandwidth
        self.price = price
        self.driver = driver
    def __repr__(self):
        return (('<NodeSize: id=%s, name=%s, ram=%s disk=%s bandwidth=%s '
                 'price=%s driver=%s ...>')
                % (self.id, self.name, self.ram, self.disk, self.bandwidth,
                   self.price, self.driver.name))


class NodeImage(object):
    """
    An operating system image.

    NodeImage objects are typically returned by the driver for the
    cloud provider in response to the list_images function

    >>> from libcloud.compute.drivers.dummy import DummyNodeDriver
    >>> driver = DummyNodeDriver(0)
    >>> image = driver.list_images()[0]
    >>> image.name
    'Ubuntu 9.10'

    Apart from name and id, there is no further standard information;
    other parameters are stored in a driver specific "extra" variable

    When creating a node, a node image should be given as an argument
    to the create_node function to decide which OS image to use.

    >>> node = driver.create_node(image=image)

    """

    def __init__(self, id, name, driver, extra=None):
        self.id = str(id)
        self.name = name
        self.driver = driver
        if not extra:
            self.extra = {}
        else:
            self.extra = extra
    def __repr__(self):
        return (('<NodeImage: id=%s, name=%s, driver=%s  ...>')
                % (self.id, self.name, self.driver.name))

class NodeLocation(object):
    """
    A physical location where nodes can be.

    >>> from libcloud.compute.drivers.dummy import DummyNodeDriver
    >>> driver = DummyNodeDriver(0)
    >>> location = driver.list_locations()[0]
    >>> location.country
    'US'
    """

    def __init__(self, id, name, country, driver):
        self.id = str(id)
        self.name = name
        self.country = country
        self.driver = driver
    def __repr__(self):
        return (('<NodeLocation: id=%s, name=%s, country=%s, driver=%s>')
                % (self.id, self.name, self.country, self.driver.name))

class NodeAuthSSHKey(object):
    """
    An SSH key to be installed for authentication to a node.

    This is the actual contents of the users ssh public key which will
    normally be installed as root's public key on the node.

    >>> pubkey = '...' # read from file
    >>> from libcloud.compute.base import NodeAuthSSHKey
    >>> k = NodeAuthSSHKey(pubkey)
    >>> k
    <NodeAuthSSHKey>

    """
    def __init__(self, pubkey):
        self.pubkey = pubkey
    def __repr__(self):
        return '<NodeAuthSSHKey>'

class NodeAuthPassword(object):
    """
    A password to be used for authentication to a node.
    """
    def __init__(self, password):
        self.password = password
    def __repr__(self):
        return '<NodeAuthPassword>'

class NodeDriver(object):
    """
    A base NodeDriver class to derive from

    This class is always subclassed by a specific driver.  For
    examples of base behavior of most functions (except deploy node)
    see the dummy driver.

    """

    connectionCls = ConnectionKey
    name = None
    type = None
    port = None
    features = {"create_node": []}
    """
    List of available features for a driver.
        - L{create_node}
            - ssh_key: Supports L{NodeAuthSSHKey} as an authentication method
              for nodes.
            - password: Supports L{NodeAuthPassword} as an authentication
              method for nodes.
            - generates_password: Returns a password attribute on the Node
              object returned from creation.
    """

    NODE_STATE_MAP = {}

    def __init__(self, key, secret=None, secure=True, host=None, port=None):
        """
        @keyword    key:    API key or username to used
        @type       key:    str

        @keyword    secret: Secret password to be used
        @type       secret: str

        @keyword    secure: Weither to use HTTPS or HTTP. Note: Some providers
                            only support HTTPS, and it is on by default.
        @type       secure: bool

        @keyword    host: Override hostname used for connections.
        @type       host: str

        @keyword    port: Override port used for connections.
        @type       port: int
        """
        self.key = key
        self.secret = secret
        self.secure = secure
        args = [self.key]

        if self.secret != None:
            args.append(self.secret)

        args.append(secure)

        if host != None:
            args.append(host)

        if port != None:
            args.append(port)

        self.connection = self.connectionCls(*args)

        self.connection.driver = self
        self.connection.connect()

    def create_node(self, **kwargs):
        """Create a new node instance.

        @keyword    name:   String with a name for this new node (required)
        @type       name:   str

        @keyword    size:   The size of resources allocated to this node.
                            (required)
        @type       size:   L{NodeSize}

        @keyword    image:  OS Image to boot on node. (required)
        @type       image:  L{NodeImage}

        @keyword    location: Which data center to create a node in. If empty,
                              undefined behavoir will be selected. (optional)
        @type       location: L{NodeLocation}

        @keyword    auth:   Initial authentication information for the node
                            (optional)
        @type       auth:   L{NodeAuthSSHKey} or L{NodeAuthPassword}

        @return: The newly created L{Node}.
        """
        raise NotImplementedError, \
            'create_node not implemented for this driver'

    def destroy_node(self, node):
        """Destroy a node.

        Depending upon the provider, this may destroy all data associated with
        the node, including backups.

        @return: C{bool} True if the destroy was successful, otherwise False
        """
        raise NotImplementedError, \
            'destroy_node not implemented for this driver'

    def reboot_node(self, node):
        """
        Reboot a node.
        @return: C{bool} True if the reboot was successful, otherwise False
        """
        raise NotImplementedError, \
            'reboot_node not implemented for this driver'

    def list_nodes(self):
        """
        List all nodes
        @return: C{list} of L{Node} objects
        """
        raise NotImplementedError, \
            'list_nodes not implemented for this driver'

    def list_images(self, location=None):
        """
        List images on a provider
        @return: C{list} of L{NodeImage} objects
        """
        raise NotImplementedError, \
            'list_images not implemented for this driver'

    def list_sizes(self, location=None):
        """
        List sizes on a provider
        @return: C{list} of L{NodeSize} objects
        """
        raise NotImplementedError, \
            'list_sizes not implemented for this driver'

    def list_locations(self):
        """
        List data centers for a provider
        @return: C{list} of L{NodeLocation} objects
        """
        raise NotImplementedError, \
            'list_locations not implemented for this driver'

    def deploy_node(self, **kwargs):
        """
        Create a new node, and start deployment.

        Depends on a Provider Driver supporting either using a specific password
        or returning a generated password.

        This function may raise a L{DeploymentException}, if a create_node
        call was successful, but there is a later error (like SSH failing or
        timing out).  This exception includes a Node object which you may want
        to destroy if incomplete deployments are not desirable.

        @keyword    deploy: Deployment to run once machine is online and availble to SSH.
        @type       deploy: L{Deployment}

        @keyword    ssh_username: Optional name of the account which is used when connecting to
                                  SSH server (default is root)
        @type       ssh_username: C{str}

        @keyword    ssh_port: Optional SSH server port (default is 22)
        @type       ssh_port: C{int}

        See L{NodeDriver.create_node} for more keyword args.

        >>> from libcloud.compute.drivers.dummy import DummyNodeDriver
        >>> from libcloud.deployment import ScriptDeployment, MultiStepDeployment
        >>> from libcloud.compute.base import NodeAuthSSHKey
        >>> driver = DummyNodeDriver(0)
        >>> key = NodeAuthSSHKey('...') # read from file
        >>> script = ScriptDeployment("yum -y install emacs strace tcpdump")
        >>> msd = MultiStepDeployment([key, script])
        >>> def d():
        ...     try:
        ...         node = driver.deploy_node(deploy=msd)
        ...     except NotImplementedError:
        ...         print "not implemented for dummy driver"
        >>> d()
        not implemented for dummy driver

        Deploy node is typically not overridden in subclasses.  The
        existing implementation should be able to handle most such.
        """
        # TODO: support ssh keys
        WAIT_PERIOD=3
        password = None

        if 'generates_password' not in self.features["create_node"]:
            if 'password' not in self.features["create_node"]:
                raise NotImplementedError, \
                    'deploy_node not implemented for this driver'

            if not kwargs.has_key('auth'):
                kwargs['auth'] = NodeAuthPassword(os.urandom(16).encode('hex'))

            password = kwargs['auth'].password
        node = self.create_node(**kwargs)
        try:
          if 'generates_password' in self.features["create_node"]:
              password = node.extra.get('password')
          start = time.time()
          end = start + (60 * 15)
          while time.time() < end:
              # need to wait until we get a public IP address.
              # TODO: there must be a better way of doing this
              time.sleep(WAIT_PERIOD)
              nodes = self.list_nodes()
              nodes = filter(lambda n: n.uuid == node.uuid, nodes)
              if len(nodes) == 0:
                  raise DeploymentError(node, "Booted node[%s] is missing form list_nodes." % node)
              if len(nodes) > 1:
                  raise DeploymentError(node, "Booted single node[%s], but multiple nodes have same UUID"% node)

              node = nodes[0]

              if node.public_ip is not None and node.public_ip != "" and node.state == NodeState.RUNNING:
                  break

          ssh_username = kwargs.get('ssh_username', 'root')
          ssh_port = kwargs.get('ssh_port', 22)

          client = SSHClient(hostname=node.public_ip[0],
                             port=ssh_port, username=ssh_username,
                             password=password)
          laste = None
          while time.time() < end:
              laste = None
              try:
                  client.connect()
                  break
              except (IOError, socket.gaierror, socket.error), e:
                  laste = e
              time.sleep(WAIT_PERIOD)
          if laste is not None:
              raise e

          tries = 3
          while tries >= 0:
            try:
              n = kwargs["deploy"].run(node, client)
              client.close()
              break
            except Exception, e:
              tries -= 1
              if tries == 0:
                raise
              client.connect()

        except DeploymentError, e:
          raise
        except Exception, e:
          raise DeploymentError(node, e)
        return n

def is_private_subnet(ip):
    """
    Utility function to check if an IP address is inside a private subnet.

    @type ip: C{str}
    @keyword ip: IP address to check

    @return: C{bool} if the specified IP address is private.
    """
    priv_subnets = [ {'subnet': '10.0.0.0', 'mask': '255.0.0.0'},
                     {'subnet': '172.16.0.0', 'mask': '255.240.0.0'},
                     {'subnet': '192.168.0.0', 'mask': '255.255.0.0'} ]

    ip = struct.unpack('I',socket.inet_aton(ip))[0]

    for network in priv_subnets:
        subnet = struct.unpack('I',socket.inet_aton(network['subnet']))[0]
        mask = struct.unpack('I',socket.inet_aton(network['mask']))[0]

        if (ip & mask) == (subnet & mask):
            return True

    return False


if __name__ == "__main__":
    import doctest
    doctest.testmod()

########NEW FILE########
__FILENAME__ = deployment
# Licensed to the Apache Software Foundation (ASF) under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Provides generic deployment steps for machines post boot.
"""
import os

class Deployment(object):
    """
    Base class for deployment tasks.
    """

    def run(self, node, client):
        """
        Runs this deployment task on C{node} using the C{client} provided.

        @type node: L{Node}
        @keyword node: Node to operate one

        @type client: L{BaseSSHClient}
        @keyword client: Connected SSH client to use.

        @return: L{Node}
        """
        raise NotImplementedError, \
            'run not implemented for this deployment'


class SSHKeyDeployment(Deployment):
    """
    Installs a public SSH Key onto a host.
    """

    def __init__(self, key):
        """
        @type key: C{str}
        @keyword key: Contents of the public key write
        """
        self.key = key

    def run(self, node, client):
        """
        Installs SSH key into C{.ssh/authorized_keys}

        See also L{Deployment.run}
        """
        client.put(".ssh/authorized_keys", contents=self.key)
        return node

class ScriptDeployment(Deployment):
    """
    Runs an arbitrary Shell Script task.
    """

    def __init__(self, script, name=None, delete=False):
        """
        @type script: C{str}
        @keyword script: Contents of the script to run

        @type name: C{str}
        @keyword name: Name of the script to upload it as, if not specified, a random name will be choosen.

        @type delete: C{bool}
        @keyword delete: Whether to delete the script on completion.
        """
        self.script = script
        self.stdout = None
        self.stderr = None
        self.exit_status = None
        self.delete = delete
        self.name = name
        if self.name is None:
            self.name = "/root/deployment_%s.sh" % (os.urandom(4).encode('hex'))

    def run(self, node, client):
        """
        Uploads the shell script and then executes it.

        See also L{Deployment.run}
        """
        client.put(path=self.name, chmod=755, contents=self.script)
        self.stdout, self.stderr, self.exit_status = client.run(self.name)
        if self.delete:
            client.delete(self.name)
        return node

class MultiStepDeployment(Deployment):
    """
    Runs a chain of Deployment steps.
    """
    def __init__(self, add = None):
        """
        @type add: C{list}
        @keyword add: Deployment steps to add.
        """
        self.steps = []
        self.add(add)

    def add(self, add):
        """Add a deployment to this chain.

        @type add: Single L{Deployment} or a C{list} of L{Deployment}
        @keyword add: Adds this deployment to the others already in this object.
        """
        if add is not None:
            add = add if isinstance(add, (list, tuple)) else [add]
            self.steps.extend(add)

    def run(self, node, client):
        """
        Run each deployment that has been added.

        See also L{Deployment.run}
        """
        for s in self.steps:
            node = s.run(node, client)
        return node

########NEW FILE########
__FILENAME__ = brightbox
# Licensed to the Apache Software Foundation (ASF) under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""
Brightbox Driver
"""
import httplib
import base64

from libcloud.common.base import ConnectionUserAndKey, Response
from libcloud.compute.types import Provider, NodeState, InvalidCredsError
from libcloud.compute.base import NodeDriver
from libcloud.compute.base import Node, NodeImage, NodeSize, NodeLocation

try:
    import json
except ImportError:
    import simplejson as json

API_VERSION = '1.0'


class BrightboxResponse(Response):
    def success(self):
        return self.status >= 200 and self.status < 400

    def parse_body(self):
        if self.headers['content-type'].split('; ')[0] == 'application/json' and len(self.body) > 0:
            return json.loads(self.body)
        else:
            return self.body

    def parse_error(self):
        return json.loads(self.body)['error']


class BrightboxConnection(ConnectionUserAndKey):
    """
    Connection class for the Brightbox driver
    """

    host = 'api.gb1.brightbox.com'
    responseCls = BrightboxResponse

    def _fetch_oauth_token(self):
        body = json.dumps({'client_id': self.user_id, 'grant_type': 'none'})

        authorization = 'Basic ' + base64.encodestring('%s:%s' % (self.user_id, self.key)).rstrip()

        self.connect()

        response = self.connection.request(method='POST', url='/token', body=body, headers={
            'Host': self.host,
            'User-Agent': self._user_agent(),
            'Authorization': authorization,
            'Content-Type': 'application/json',
            'Content-Length': str(len(body))
        })

        response = self.connection.getresponse()

        if response.status == 200:
            return json.loads(response.read())['access_token']
        else:
            message = '%s (%s)' % (json.loads(response.read())['error'], response.status)

            raise InvalidCredsError, message

    def add_default_headers(self, headers):
        try:
            headers['Authorization'] = 'OAuth ' + self.token
        except AttributeError:
            self.token = self._fetch_oauth_token()

            headers['Authorization'] = 'OAuth ' + self.token

        return headers

    def encode_data(self, data):
        return json.dumps(data)


class BrightboxNodeDriver(NodeDriver):
    """
    Brightbox node driver
    """

    connectionCls = BrightboxConnection

    type = Provider.BRIGHTBOX
    name = 'Brightbox'

    NODE_STATE_MAP = { 'creating': NodeState.PENDING,
                       'active': NodeState.RUNNING,
                       'inactive': NodeState.UNKNOWN,
                       'deleting': NodeState.UNKNOWN,
                       'deleted': NodeState.TERMINATED,
                       'failed': NodeState.UNKNOWN }

    def _to_node(self, data):
        return Node(
            id = data['id'],
            name = data['name'],
            state = self.NODE_STATE_MAP[data['status']],
            public_ip = map(lambda cloud_ip: cloud_ip['public_ip'], data['cloud_ips']),
            private_ip = map(lambda interface: interface['ipv4_address'], data['interfaces']),
            driver = self.connection.driver,
            extra = {
                'status': data['status'],
                'interfaces': data['interfaces']
            }
        )

    def _to_image(self, data):
        return NodeImage(
            id = data['id'],
            name = data['name'],
            driver = self,
            extra = {
                'description': data['description'],
                'arch': data['arch']
            }
        )

    def _to_size(self, data):
        return NodeSize(
            id = data['id'],
            name = data['name'],
            ram = data['ram'],
            disk = data['disk_size'],
            bandwidth = 0,
            price = '',
            driver = self
        )

    def _to_location(self, data):
        return NodeLocation(
            id = data['id'],
            name = data['handle'],
            country = 'GB',
            driver = self
        )

    def _post(self, path, data={}):
        headers = {'Content-Type': 'application/json'}

        return self.connection.request(path, data=data, headers=headers, method='POST')

    def create_node(self, **kwargs):
        data = {
            'name': kwargs['name'],
            'server_type': kwargs['size'].id,
            'image': kwargs['image'].id,
            'user_data': ''
        }

        if kwargs.has_key('location'):
            data['zone'] = kwargs['location'].id
        else:
            data['zone'] = ''

        data = self._post('/%s/servers' % API_VERSION, data).object

        return self._to_node(data)

    def destroy_node(self, node):
        response = self.connection.request('/%s/servers/%s' % (API_VERSION, node.id), method='DELETE')

        return response.status == httplib.ACCEPTED

    def list_nodes(self):
        data = self.connection.request('/%s/servers' % API_VERSION).object

        return map(self._to_node, data)

    def list_images(self):
        data = self.connection.request('/%s/images' % API_VERSION).object

        return map(self._to_image, data)

    def list_sizes(self):
        data = self.connection.request('/%s/server_types' % API_VERSION).object

        return map(self._to_size, data)

    def list_locations(self):
        data = self.connection.request('/%s/zones' % API_VERSION).object

        return map(self._to_location, data)

    def ex_list_cloud_ips(self):
        return self.connection.request('/%s/cloud_ips' % API_VERSION).object

    def ex_create_cloud_ip(self):
        return self._post('/%s/cloud_ips' % API_VERSION).object

    def ex_map_cloud_ip(self, cloud_ip_id, interface_id):
        response = self._post('/%s/cloud_ips/%s/map' % (API_VERSION, cloud_ip_id), {'interface': interface_id})

        return response.status == httplib.ACCEPTED

    def ex_unmap_cloud_ip(self, cloud_ip_id):
        response = self._post('/%s/cloud_ips/%s/unmap' % (API_VERSION, cloud_ip_id))

        return response.status == httplib.ACCEPTED

    def ex_destroy_cloud_ip(self, cloud_ip_id):
        response = self.connection.request('/%s/cloud_ips/%s' % (API_VERSION, cloud_ip_id), method='DELETE')

        return response.status == httplib.OK

########NEW FILE########
__FILENAME__ = cloudsigma
# -*- coding: utf-8 -*-
# Licensed to the Apache Software Foundation (ASF) under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""
CloudSigma Driver
"""
import re
import time
import base64

from libcloud.common.base import ConnectionUserAndKey, Response
from libcloud.common.types import InvalidCredsError
from libcloud.compute.types import NodeState, Provider
from libcloud.compute.base import NodeDriver, NodeSize, Node
from libcloud.compute.base import NodeImage

# API end-points
API_ENDPOINTS = {
    'zrh': {
        'name': 'Zurich',
        'country': 'Switzerland',
        'host': 'api.cloudsigma.com'
    },
}

# Default API end-point for the base connection clase.
DEFAULT_ENDPOINT = 'zrh'

# CloudSigma doesn't specify special instance types.
# Basically for CPU any value between 0.5 GHz and 20.0 GHz should work, 500 MB to 32000 MB for ram
# and 1 GB to 1024 GB for hard drive size.
# Plans in this file are based on examples listed on http://www.cloudsigma.com/en/pricing/price-schedules
INSTANCE_TYPES = {
    'micro-regular': {
        'id': 'micro-regular',
        'name': 'Micro/Regular instance',
        'cpu': 1100,
        'memory': 640,
        'disk': 50,
        'price': '0.0548',
        'bandwidth': None,
    },
    'micro-high-cpu': {
        'id': 'micro-high-cpu',
        'name': 'Micro/High CPU instance',
        'cpu': 2200,
        'memory': 640,
        'disk': 80,
        'price': '.381',
        'bandwidth': None,
    },
    'standard-small': {
        'id': 'standard-small',
        'name': 'Standard/Small instance',
        'cpu': 1100,
        'memory': 1741,
        'disk': 50,
        'price': '0.0796',
        'bandwidth': None,
    },
    'standard-large': {
        'id': 'standard-large',
        'name': 'Standard/Large instance',
        'cpu': 4400,
        'memory': 7680,
        'disk': 250,
        'price': '0.381',
        'bandwidth': None,
    },
    'standard-extra-large': {
        'id': 'standard-extra-large',
        'name': 'Standard/Extra Large instance',
        'cpu': 8800,
        'memory': 15360,
        'disk': 500,
        'price': '0.762',
        'bandwidth': None,
    },
    'high-memory-extra-large': {
        'id': 'high-memory-extra-large',
        'name': 'High Memory/Extra Large instance',
        'cpu': 7150,
        'memory': 17510,
        'disk': 250,
        'price': '0.642',
        'bandwidth': None,
    },
    'high-memory-double-extra-large': {
        'id': 'high-memory-double-extra-large',
        'name': 'High Memory/Double Extra Large instance',
        'cpu': 14300,
        'memory': 32768,
        'disk': 500,
        'price': '1.383',
        'bandwidth': None,
    },
    'high-cpu-medium': {
        'id': 'high-cpu-medium',
        'name': 'High CPU/Medium instance',
        'cpu': 5500,
        'memory': 1741,
        'disk': 150,
        'price': '0.211',
        'bandwidth': None,
    },
    'high-cpu-extra-large': {
        'id': 'high-cpu-extra-large',
        'name': 'High CPU/Extra Large instance',
        'cpu': 20000,
        'memory': 7168,
        'disk': 500,
        'price': '0.780',
        'bandwidth': None,
    },
}

NODE_STATE_MAP = {
    'active': NodeState.RUNNING,
    'stopped': NodeState.TERMINATED,
    'dead': NodeState.TERMINATED,
    'dumped': NodeState.TERMINATED,
}

# Default timeout (in seconds) for the drive imaging process
IMAGING_TIMEOUT = 20 * 60

class CloudSigmaException(Exception):
    def __str__(self):
        return self.args[0]

    def __repr__(self):
        return "<CloudSigmaException '%s'>" % (self.args[0])

class CloudSigmaInsufficientFundsException(Exception):
    def __repr__(self):
        return "<CloudSigmaInsufficientFundsException '%s'>" % (self.args[0])

class CloudSigmaResponse(Response):
    def success(self):
        if self.status == 401:
            raise InvalidCredsError()

        return self.status >= 200 and self.status <= 299

    def parse_body(self):
        if not self.body:
            return self.body

        return str2dicts(self.body)

    def parse_error(self):
        return 'Error: %s' % (self.body.replace('errors:', '').strip())

class CloudSigmaNodeSize(NodeSize):
    def __init__(self, id, name, cpu, ram, disk, bandwidth, price, driver):
        self.id = id
        self.name = name
        self.cpu = cpu
        self.ram = ram
        self.disk = disk
        self.bandwidth = bandwidth
        self.price = price
        self.driver = driver

    def __repr__(self):
        return (('<NodeSize: id=%s, name=%s, cpu=%s, ram=%s disk=%s bandwidth=%s '
                 'price=%s driver=%s ...>')
                % (self.id, self.name, self.cpu, self.ram, self.disk, self.bandwidth,
                   self.price, self.driver.name))

class CloudSigmaBaseConnection(ConnectionUserAndKey):
    host = API_ENDPOINTS[DEFAULT_ENDPOINT]['host']
    responseCls = CloudSigmaResponse

    def add_default_headers(self, headers):
        headers['Accept'] = 'application/json'
        headers['Content-Type'] = 'application/json'

        headers['Authorization'] = 'Basic %s' % (base64.b64encode('%s:%s' % (self.user_id, self.key)))

        return headers

class CloudSigmaBaseNodeDriver(NodeDriver):
    type = Provider.CLOUDSIGMA
    name = 'CloudSigma'
    connectionCls = CloudSigmaBaseConnection

    def reboot_node(self, node):
        """
        Reboot a node.

        Because Cloudsigma API does not provide native reboot call, it's emulated using stop and start.
        """
        node = self._get_node(node.id)
        state = node.state

        if state == NodeState.RUNNING:
            stopped = self.ex_stop_node(node)
        else:
            stopped = True

        if not stopped:
            raise CloudSigmaException('Could not stop node with id %s' % (node.id))

        success = self.ex_start_node(node)

        return success

    def destroy_node(self, node):
        """
        Destroy a node (all the drives associated with it are NOT destroyed).

        If a node is still running, it's stopped before it's destroyed.
        """
        node = self._get_node(node.id)
        state = node.state

        # Node cannot be destroyed while running so it must be stopped first
        if state == NodeState.RUNNING:
            stopped = self.ex_stop_node(node)
        else:
            stopped = True

        if not stopped:
            raise CloudSigmaException('Could not stop node with id %s' % (node.id))

        response = self.connection.request(action = '/servers/%s/destroy' % (node.id),
                                           method = 'POST')
        return response.status == 204

    def list_images(self, location=None):
        """
        Return a list of available standard images (this call might take up to 15 seconds to return).
        """
        response = self.connection.request(action = '/drives/standard/info').object

        images = []
        for value in response:
            if value.get('type'):
                if value['type'] == 'disk':
                    image = NodeImage(id = value['drive'], name = value['name'], driver = self.connection.driver,
                                    extra = {'size': value['size']})
                    images.append(image)

        return images

    def list_sizes(self, location = None):
        """
        Return a list of available node sizes.
        """
        sizes = []
        for key, value in INSTANCE_TYPES.iteritems():
            size = CloudSigmaNodeSize(id = value['id'], name = value['name'], cpu = value['cpu'], ram = value['memory'],
                            disk = value['disk'], bandwidth = value['bandwidth'], price = value['price'],
                            driver = self.connection.driver)
            sizes.append(size)

        return sizes

    def list_nodes(self):
        """
        Return a list of nodes.
        """
        response = self.connection.request(action = '/servers/info').object

        nodes = []
        for data in response:
            node = self._to_node(data)
            if node:
                nodes.append(node)
        return nodes

    def create_node(self, **kwargs):
        """
        Creates a CloudSigma instance

        See L{NodeDriver.create_node} for more keyword args.

        @keyword    name: String with a name for this new node (required)
        @type       name: C{string}

        @keyword    smp: Number of virtual processors or None to calculate based on the cpu speed
        @type       smp: C{int}

        @keyword    nic_model: e1000, rtl8139 or virtio (is not specified, e1000 is used)
        @type       nic_model: C{string}

        @keyword    vnc_password: If not set, VNC access is disabled.
        @type       vnc_password: C{bool}
        """
        size = kwargs['size']
        image = kwargs['image']
        smp = kwargs.get('smp', 'auto')
        nic_model = kwargs.get('nic_model', 'e1000')
        vnc_password = kwargs.get('vnc_password', None)

        if nic_model not in ['e1000', 'rtl8139', 'virtio']:
            raise CloudSigmaException('Invalid NIC model specified')

        drive_data = {}
        drive_data.update({'name': kwargs['name'], 'size': '%sG' % (kwargs['size'].disk)})

        response = self.connection.request(action = '/drives/%s/clone' % image.id, data = dict2str(drive_data),
                                           method = 'POST').object

        if not response:
            raise CloudSigmaException('Drive creation failed')

        drive_uuid = response[0]['drive']

        response = self.connection.request(action = '/drives/%s/info' % (drive_uuid)).object
        imaging_start = time.time()
        while response[0].has_key('imaging'):
            response = self.connection.request(action = '/drives/%s/info' % (drive_uuid)).object
            elapsed_time = time.time() - imaging_start
            if response[0].has_key('imaging') and elapsed_time >= IMAGING_TIMEOUT:
                raise CloudSigmaException('Drive imaging timed out')
            time.sleep(1)

        node_data = {}
        node_data.update({'name': kwargs['name'], 'cpu': size.cpu, 'mem': size.ram, 'ide:0:0': drive_uuid,
                          'boot': 'ide:0:0', 'smp': smp})
        node_data.update({'nic:0:model': nic_model, 'nic:0:dhcp': 'auto'})

        if vnc_password:
            node_data.update({'vnc:ip': 'auto', 'vnc:password': vnc_password})

        response = self.connection.request(action = '/servers/create', data = dict2str(node_data),
                                           method = 'POST').object

        if not isinstance(response, list):
            response = [ response ]

        node = self._to_node(response[0])
        if node is None:
            # Insufficient funds, destroy created drive
            self.ex_drive_destroy(drive_uuid)
            raise CloudSigmaInsufficientFundsException('Insufficient funds, node creation failed')

        # Start the node after it has been created
        started = self.ex_start_node(node)

        if started:
            node.state = NodeState.RUNNING

        return node

    def ex_destroy_node_and_drives(self, node):
        """
        Destroy a node and all the drives associated with it.
        """
        node = self._get_node_info(node)

        drive_uuids = []
        for key, value in node.iteritems():
            if (key.startswith('ide:') or key.startswith('scsi') or key.startswith('block')) and \
               not (key.endswith(':bytes') or key.endswith(':requests') or key.endswith('media')):
                drive_uuids.append(value)

        node_destroyed = self.destroy_node(self._to_node(node))

        if not node_destroyed:
            return False

        for drive_uuid in drive_uuids:
            self.ex_drive_destroy(drive_uuid)

        return True

    def ex_static_ip_list(self):
        """
        Return a list of available static IP addresses.
        """
        response = self.connection.request(action = '/resources/ip/list', method = 'GET')

        if response.status != 200:
            raise CloudSigmaException('Could not retrieve IP list')

        ips = str2list(response.body)
        return ips

    def ex_drives_list(self):
        """
        Return a list of all the available drives.
        """
        response = self.connection.request(action = '/drives/info', method = 'GET')

        result = str2dicts(response.body)
        return result

    def ex_static_ip_create(self):
        """
        Create a new static IP address.
        """
        response = self.connection.request(action = '/resources/ip/create', method = 'GET')

        result = str2dicts(response.body)
        return result

    def ex_static_ip_destroy(self, ip_address):
        """
        Destroy a static IP address.
        """
        response = self.connection.request(action = '/resources/ip/%s/destroy' % (ip_address), method = 'GET')

        return response.status == 204

    def ex_drive_destroy(self, drive_uuid):
        """
        Destroy a drive with a specified uuid.
        If the drive is currently mounted an exception is thrown.
        """
        response = self.connection.request(action = '/drives/%s/destroy' % (drive_uuid), method = 'POST')

        return response.status == 204


    def ex_set_node_configuration(self, node, **kwargs):
        """
        Update a node configuration.
        Changing most of the parameters requires node to be stopped.
        """
        valid_keys = ('^name$', '^parent$', '^cpu$', '^smp$', '^mem$', '^boot$', '^nic:0:model$', '^nic:0:dhcp',
                      '^nic:1:model$', '^nic:1:vlan$', '^nic:1:mac$', '^vnc:ip$', '^vnc:password$', '^vnc:tls',
                      '^ide:[0-1]:[0-1](:media)?$', '^scsi:0:[0-7](:media)?$', '^block:[0-7](:media)?$')

        invalid_keys = []
        for key in kwargs.keys():
            matches = False
            for regex in valid_keys:
                if re.match(regex, key):
                    matches = True
                    break
            if not matches:
                invalid_keys.append(key)

        if invalid_keys:
            raise CloudSigmaException('Invalid configuration key specified: %s' % (',' .join(invalid_keys)))

        response = self.connection.request(action = '/servers/%s/set' % (node.id), data = dict2str(kwargs),
                                           method = 'POST')

        return (response.status == 200 and response.body != '')

    def ex_start_node(self, node):
        """
        Start a node.
        """
        response = self.connection.request(action = '/servers/%s/start' % (node.id),
                                           method = 'POST')

        return response.status == 200

    def ex_stop_node(self, node):
        """
        Stop (shutdown) a node.
        """
        response = self.connection.request(action = '/servers/%s/stop' % (node.id),
                                           method = 'POST')
        return response.status == 204

    def ex_shutdown_node(self, node):
        """
        Stop (shutdown) a node.
        """
        return self.ex_stop_node(node)

    def ex_destroy_drive(self, drive_uuid):
        """
        Destroy a drive.
        """
        response = self.connection.request(action = '/drives/%s/destroy' % (drive_uuid),
                                           method = 'POST')
        return response.status == 204

    def _to_node(self, data):
        if data:
            try:
                state = NODE_STATE_MAP[data['status']]
            except KeyError:
                state = NodeState.UNKNOWN

            if 'server' not in data:
                # Response does not contain server UUID if the server
                # creation failed because of insufficient funds.
                return None

            public_ip = []
            if data.has_key('nic:0:dhcp'):
                if isinstance(data['nic:0:dhcp'], list):
                    public_ip = data['nic:0:dhcp']
                else:
                    public_ip = [data['nic:0:dhcp']]

            extra = {}
            extra_keys = [ ('cpu', 'int'), ('smp', 'auto'), ('mem', 'int'), ('status', 'str') ]
            for key, value_type in extra_keys:
                if data.has_key(key):
                    value = data[key]

                    if value_type == 'int':
                        value = int(value)
                    elif value_type == 'auto':
                        try:
                            value = int(value)
                        except ValueError:
                            pass

                    extra.update({key: value})

            if data.has_key('vnc:ip') and data.has_key('vnc:password'):
                extra.update({'vnc_ip': data['vnc:ip'], 'vnc_password': data['vnc:password']})

            node = Node(id = data['server'], name = data['name'], state =  state,
                        public_ip = public_ip, private_ip = None, driver = self.connection.driver,
                        extra = extra)

            return node
        return None

    def _get_node(self, node_id):
        nodes = self.list_nodes()
        node = [node for node in nodes if node.id == node.id]

        if not node:
            raise CloudSigmaException('Node with id %s does not exist' % (node_id))

        return node[0]

    def _get_node_info(self, node):
        response = self.connection.request(action = '/servers/%s/info' % (node.id))

        result = str2dicts(response.body)
        return result[0]

class CloudSigmaZrhConnection(CloudSigmaBaseConnection):
    """
    Connection class for the CloudSigma driver for the Zurich end-point
    """
    host = API_ENDPOINTS[DEFAULT_ENDPOINT]['host']

class CloudSigmaZrhNodeDriver(CloudSigmaBaseNodeDriver):
    """
    CloudSigma node driver for the Zurich end-point
    """
    connectionCls = CloudSigmaZrhConnection

# Utility methods (should we place them in libcloud/utils.py ?)
def str2dicts(data):
    """
    Create a list of dictionaries from a whitespace and newline delimited text.

    For example, this:
    cpu 1100
    ram 640

    cpu 2200
    ram 1024

    becomes:
    [{'cpu': '1100', 'ram': '640'}, {'cpu': '2200', 'ram': '1024'}]
    """
    list_data = []
    list_data.append({})
    d = list_data[-1]

    lines = data.split('\n')
    for line in lines:
        line = line.strip()

        if not line:
            d = {}
            list_data.append(d)
            d = list_data[-1]
            continue

        whitespace = line.find(' ')

        if not whitespace:
            continue

        key = line[0:whitespace]
        value = line[whitespace + 1:]
        d.update({key: value})

    list_data = [value for value in list_data if value != {}]
    return list_data

def str2list(data):
    """
    Create a list of values from a whitespace and newline delimited text (keys are ignored).

    For example, this:
    ip 1.2.3.4
    ip 1.2.3.5
    ip 1.2.3.6

    becomes:
    ['1.2.3.4', '1.2.3.5', '1.2.3.6']
    """
    list_data = []

    for line in data.split('\n'):
        line = line.strip()

        if not line:
            continue

        try:
            splitted = line.split(' ')
            # key = splitted[0]
            value = splitted[1]
        except Exception:
            continue

        list_data.append(value)

    return list_data

def dict2str(data):
    """
    Create a string with a whitespace and newline delimited text from a dictionary.

    For example, this:
    {'cpu': '1100', 'ram': '640', 'smp': 'auto'}

    becomes:
    cpu 1100
    ram 640
    smp auto

    cpu 2200
    ram 1024
    """
    result = ''
    for k in data:
        if data[k] != None:
            result += '%s %s\n' % (str(k), str(data[k]))
        else:
            result += '%s\n' % str(k)

    return result

########NEW FILE########
__FILENAME__ = dreamhost
# Licensed to the Apache Software Foundation (ASF) under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""
DreamHost Driver
"""

try:
    import json
except:
    import simplejson as json

from libcloud.common.base import ConnectionKey, Response
from libcloud.common.types import InvalidCredsError
from libcloud.compute.base import Node, NodeDriver, NodeLocation, NodeSize
from libcloud.compute.base import NodeImage
from libcloud.compute.types import Provider, NodeState

"""
DreamHost Private Servers can be resized on the fly, but Libcloud doesn't
currently support extensions to its interface, so we'll put some basic sizes
in for node creation.
"""
DH_PS_SIZES = {
    'minimum': {
        'id' : 'minimum',
        'name' : 'Minimum DH PS size',
        'ram' : 300,
        'price' : 15,
        'disk' : None,
        'bandwidth' : None
    },
    'maximum': {
        'id' : 'maximum',
        'name' : 'Maximum DH PS size',
        'ram' : 4000,
        'price' : 200,
        'disk' : None,
        'bandwidth' : None
    },
    'default': {
        'id' : 'default',
        'name' : 'Default DH PS size',
        'ram' : 2300,
        'price' : 115,
        'disk' : None,
        'bandwidth' : None
    },
    'low': {
        'id' : 'low',
        'name' : 'DH PS with 1GB RAM',
        'ram' : 1000,
        'price' : 50,
        'disk' : None,
        'bandwidth' : None
    },
    'high': {
        'id' : 'high',
        'name' : 'DH PS with 3GB RAM',
        'ram' : 3000,
        'price' : 150,
        'disk' : None,
        'bandwidth' : None
    },
}


class DreamhostAPIException(Exception):

    def __str__(self):
        return self.args[0]

    def __repr__(self):
        return "<DreamhostException '%s'>" % (self.args[0])


class DreamhostResponse(Response):
    """
    Response class for DreamHost PS
    """

    def parse_body(self):
        resp = json.loads(self.body)
        if resp['result'] != 'success':
            raise Exception(self._api_parse_error(resp))
        return resp['data']

    def parse_error(self):
        raise Exception

    def _api_parse_error(self, response):
        if 'data' in response:
            if response['data'] == 'invalid_api_key':
                raise InvalidCredsError("Oops!  You've entered an invalid API key")
            else:
                raise DreamhostAPIException(response['data'])
        else:
            raise DreamhostAPIException("Unknown problem: %s" % (self.body))

class DreamhostConnection(ConnectionKey):
    """
    Connection class to connect to DreamHost's API servers
    """

    host = 'api.dreamhost.com'
    responseCls = DreamhostResponse
    format = 'json'

    def add_default_params(self, params):
        """
        Add key and format parameters to the request.  Eventually should add
        unique_id to prevent re-execution of a single request.
        """
        params['key'] = self.key
        params['format'] = self.format
        #params['unique_id'] = generate_unique_id()
        return params


class DreamhostNodeDriver(NodeDriver):
    """
    Node Driver for DreamHost PS
    """
    type = Provider.DREAMHOST
    name = "Dreamhost"
    connectionCls = DreamhostConnection
    _sizes = DH_PS_SIZES

    def create_node(self, **kwargs):
        """Create a new Dreamhost node

        See L{NodeDriver.create_node} for more keyword args.

        @keyword    ex_movedata: Copy all your existing users to this new PS
        @type       ex_movedata: C{str}
        """
        size = kwargs['size'].ram
        params = {
            'cmd' : 'dreamhost_ps-add_ps',
            'movedata' : kwargs.get('movedata', 'no'),
            'type' : kwargs['image'].name,
            'size' : size
        }
        data = self.connection.request('/', params).object
        return Node(
            id = data['added_web'],
            name = data['added_web'],
            state = NodeState.PENDING,
            public_ip = [],
            private_ip = [],
            driver = self.connection.driver,
            extra = {
                'type' : kwargs['image'].name
            }
        )

    def destroy_node(self, node):
        params = {
            'cmd' : 'dreamhost_ps-remove_ps',
            'ps' : node.id
        }
        try:
            return self.connection.request('/', params).success()
        except DreamhostAPIException:
            return False

    def reboot_node(self, node):
        params = {
            'cmd' : 'dreamhost_ps-reboot',
            'ps' : node.id
        }
        try:
            return self.connection.request('/', params).success()
        except DreamhostAPIException:
            return False

    def list_nodes(self, **kwargs):
        data = self.connection.request('/', {'cmd': 'dreamhost_ps-list_ps'}).object
        return [self._to_node(n) for n in data]

    def list_images(self, **kwargs):
        data = self.connection.request('/', {'cmd': 'dreamhost_ps-list_images'}).object
        images = []
        for img in data:
            images.append(NodeImage(
                id = img['image'],
                name = img['image'],
                driver = self.connection.driver
            ))
        return images

    def list_sizes(self, **kwargs):
        return [ NodeSize(driver=self.connection.driver, **i)
            for i in self._sizes.values() ]

    def list_locations(self, **kwargs):
        raise NotImplementedError('You cannot select a location for DreamHost Private Servers at this time.')

    ############################################
    # Private Methods (helpers and extensions) #
    ############################################
    def _resize_node(self, node, size):
        if (size < 300 or size > 4000):
            return False

        params = {
            'cmd' : 'dreamhost_ps-set_size',
            'ps' : node.id,
            'size' : size
        }
        try:
            return self.connection.request('/', params).success()
        except DreamhostAPIException:
            return False

    def _to_node(self, data):
        """
        Convert the data from a DreamhostResponse object into a Node
        """
        return Node(
            id = data['ps'],
            name = data['ps'],
            state = NodeState.UNKNOWN,
            public_ip = [data['ip']],
            private_ip = [],
            driver = self.connection.driver,
            extra = {
                'current_size' : data['memory_mb'],
                'account_id' : data['account_id'],
                'type' : data['type']
            }
        )

########NEW FILE########
__FILENAME__ = dummy
# Licensed to the Apache Software Foundation (ASF) under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""
Dummy Driver

@note: This driver is out of date
"""
import uuid
import socket
import struct

from libcloud.base import ConnectionKey, NodeDriver, NodeSize, NodeLocation
from libcloud.compute.base import NodeImage, Node
from libcloud.compute.types import Provider,NodeState

class DummyConnection(ConnectionKey):
    """
    Dummy connection class
    """

    def connect(self, host=None, port=None):
        pass

class DummyNodeDriver(NodeDriver):
    """
    Dummy node driver

    This is a fake driver which appears to always create or destroy
    nodes successfully.

    >>> from libcloud.compute.drivers.dummy import DummyNodeDriver
    >>> driver = DummyNodeDriver(0)
    >>> node=driver.create_node()
    >>> node.public_ip[0]
    '127.0.0.3'
    >>> node.name
    'dummy-3'

    If the credentials you give convert to an integer then the next
    node to be created will be one higher.

    Each time you create a node you will get a different IP address.

    >>> driver = DummyNodeDriver(22)
    >>> node=driver.create_node()
    >>> node.name
    'dummy-23'

    """

    name = "Dummy Node Provider"
    type = Provider.DUMMY

    def __init__(self, creds):
        self.creds = creds
        try:
          num = int(creds)
        except ValueError:
          num = None
        if num:
          self.nl = []
          startip = _ip_to_int('127.0.0.1')
          for i in xrange(num):
            ip = _int_to_ip(startip + i)
            self.nl.append(
              Node(id=i,
                   name='dummy-%d' % (i),
                   state=NodeState.RUNNING,
                   public_ip=[ip],
                   private_ip=[],
                   driver=self,
                   extra={'foo': 'bar'})
            )
        else:
          self.nl = [
              Node(id=1,
                   name='dummy-1',
                   state=NodeState.RUNNING,
                   public_ip=['127.0.0.1'],
                   private_ip=[],
                   driver=self,
                   extra={'foo': 'bar'}),
              Node(id=2,
                   name='dummy-2',
                   state=NodeState.RUNNING,
                   public_ip=['127.0.0.1'],
                   private_ip=[],
                   driver=self,
                   extra={'foo': 'bar'}),
          ]
        self.connection = DummyConnection(self.creds)

    def get_uuid(self, unique_field=None):
        return str(uuid.uuid4())

    def list_nodes(self):
        """
        List the nodes known to a particular driver;
        There are two default nodes created at the beginning

        >>> from libcloud.compute.drivers.dummy import DummyNodeDriver
        >>> driver = DummyNodeDriver(0)
        >>> node_list=driver.list_nodes()
        >>> sorted([node.name for node in node_list ])
        ['dummy-1', 'dummy-2']

        each item in the list returned is a node object from which you
        can carry out any node actions you wish

        >>> node_list[0].reboot()
        True

        As more nodes are added, list_nodes will return them

        >>> node=driver.create_node()
        >>> sorted([node.name for node in driver.list_nodes()])
        ['dummy-1', 'dummy-2', 'dummy-3']
        """
        return self.nl

    def reboot_node(self, node):
        """
        Sets the node state to rebooting; in this dummy driver always
        returns True as if the reboot had been successful.

        >>> from libcloud.compute.drivers.dummy import DummyNodeDriver
        >>> driver = DummyNodeDriver(0)
        >>> node=driver.create_node()
        >>> from libcloud.compute.types import NodeState
        >>> node.state == NodeState.RUNNING
        True
        >>> node.state == NodeState.REBOOTING
        False
        >>> driver.reboot_node(node)
        True
        >>> node.state == NodeState.REBOOTING
        True

        Please note, dummy nodes never recover from the reboot.
        """

        node.state = NodeState.REBOOTING
        return True

    def destroy_node(self, node):
        """
        Sets the node state to terminated and removes it from the node list

        >>> from libcloud.compute.drivers.dummy import DummyNodeDriver
        >>> driver = DummyNodeDriver(0)
        >>> from libcloud.compute.types import NodeState
        >>> node = [node for node in driver.list_nodes() if node.name == 'dummy-1'][0]
        >>> node.state == NodeState.RUNNING
        True
        >>> driver.destroy_node(node)
        True
        >>> node.state == NodeState.RUNNING
        False
        >>> [node for node in driver.list_nodes() if node.name == 'dummy-1']
        []
        """

        node.state = NodeState.TERMINATED
        self.nl.remove(node)
        return True

    def list_images(self, location=None):
        """
        Returns a list of images as a cloud provider might have

        >>> from libcloud.compute.drivers.dummy import DummyNodeDriver
        >>> driver = DummyNodeDriver(0)
        >>> sorted([image.name for image in driver.list_images()])
        ['Slackware 4', 'Ubuntu 9.04', 'Ubuntu 9.10']
        """
        return [
            NodeImage(id=1, name="Ubuntu 9.10", driver=self),
            NodeImage(id=2, name="Ubuntu 9.04", driver=self),
            NodeImage(id=3, name="Slackware 4", driver=self),
        ]

    def list_sizes(self, location=None):
        """
        Returns a list of node sizes as a cloud provider might have

        >>> from libcloud.compute.drivers.dummy import DummyNodeDriver
        >>> driver = DummyNodeDriver(0)
        >>> sorted([size.ram for size in driver.list_sizes()])
        [128, 512, 4096, 8192]
        """

        return [
            NodeSize(id=1,
                     name="Small",
                     ram=128,
                     disk=4,
                     bandwidth=500,
                     price=4,
                     driver=self),
            NodeSize(id=2,
                     name="Medium",
                     ram=512,
                     disk=16,
                     bandwidth=1500,
                     price=8,
                     driver=self),
            NodeSize(id=3,
                     name="Big",
                     ram=4096,
                     disk=32,
                     bandwidth=2500,
                     price=32,
                     driver=self),
            NodeSize(id=4,
                     name="XXL Big",
                     ram=4096*2,
                     disk=32*4,
                     bandwidth=2500*3,
                     price=32*2,
                     driver=self),
        ]

    def list_locations(self):
        """
        Returns a list of locations of nodes

        >>> from libcloud.compute.drivers.dummy import DummyNodeDriver
        >>> driver = DummyNodeDriver(0)
        >>> sorted([loc.name + " in " + loc.country for loc in driver.list_locations()])
        ['Island Datacenter in FJ', 'London Loft in GB', "Paul's Room in US"]
        """
        return [
            NodeLocation(id=1,
                         name="Paul's Room",
                         country='US',
                         driver=self),
            NodeLocation(id=2,
                         name="London Loft",
                         country='GB',
                         driver=self),
            NodeLocation(id=3,
                         name="Island Datacenter",
                         country='FJ',
                         driver=self),
        ]

    def create_node(self, **kwargs):
        """
        Creates a dummy node; the node id is equal to the number of
        nodes in the node list

        >>> from libcloud.compute.drivers.dummy import DummyNodeDriver
        >>> driver = DummyNodeDriver(0)
        >>> sorted([node.name for node in driver.list_nodes()])
        ['dummy-1', 'dummy-2']
        >>> nodeA = driver.create_node()
        >>> sorted([node.name for node in driver.list_nodes()])
        ['dummy-1', 'dummy-2', 'dummy-3']
        >>> driver.create_node().name
        'dummy-4'
        >>> driver.destroy_node(nodeA)
        True
        >>> sorted([node.name for node in driver.list_nodes()])
        ['dummy-1', 'dummy-2', 'dummy-4']
        """
        l = len(self.nl) + 1
        n = Node(id=l,
                 name='dummy-%d' % l,
                 state=NodeState.RUNNING,
                 public_ip=['127.0.0.%d' % l],
                 private_ip=[],
                 driver=self,
                 extra={'foo': 'bar'})
        self.nl.append(n)
        return n

def _ip_to_int(ip):
    return socket.htonl(struct.unpack('I', socket.inet_aton(ip))[0])

def _int_to_ip(ip):
    return socket.inet_ntoa(struct.pack('I', socket.ntohl(ip)))

if __name__ == "__main__":
    import doctest
    doctest.testmod()

########NEW FILE########
__FILENAME__ = ec2
# Licensed to the Apache Software Foundation (ASF) under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Amazon EC2 driver
"""
import base64
import hmac
import os
import time
import urllib

from hashlib import sha256
from xml.etree import ElementTree as ET

from libcloud.common.base import Response, ConnectionUserAndKey
from libcloud.common.types import InvalidCredsError, MalformedResponseError, LibcloudError
from libcloud.compute.providers import Provider
from libcloud.compute.types import NodeState
from libcloud.compute.base import Node, NodeDriver, NodeLocation, NodeSize
from libcloud.compute.base import NodeImage

EC2_US_EAST_HOST = 'ec2.us-east-1.amazonaws.com'
EC2_US_WEST_HOST = 'ec2.us-west-1.amazonaws.com'
EC2_EU_WEST_HOST = 'ec2.eu-west-1.amazonaws.com'
EC2_AP_SOUTHEAST_HOST = 'ec2.ap-southeast-1.amazonaws.com'
EC2_AP_NORTHEAST_HOST = 'ec2.ap-northeast-1.amazonaws.com'

API_VERSION = '2010-08-31'

NAMESPACE = "http://ec2.amazonaws.com/doc/%s/" % (API_VERSION)

"""
Sizes must be hardcoded, because Amazon doesn't provide an API to fetch them.
From http://aws.amazon.com/ec2/instance-types/
"""
EC2_INSTANCE_TYPES = {
    't1.micro': {
        'id': 't1.micro',
        'name': 'Micro Instance',
        'ram': 613,
        'disk': 15,
        'bandwidth': None
    },
    'm1.small': {
        'id': 'm1.small',
        'name': 'Small Instance',
        'ram': 1740,
        'disk': 160,
        'bandwidth': None
    },
    'm1.large': {
        'id': 'm1.large',
        'name': 'Large Instance',
        'ram': 7680,
        'disk': 850,
        'bandwidth': None
    },
    'm1.xlarge': {
        'id': 'm1.xlarge',
        'name': 'Extra Large Instance',
        'ram': 15360,
        'disk': 1690,
        'bandwidth': None
    },
    'c1.medium': {
        'id': 'c1.medium',
        'name': 'High-CPU Medium Instance',
        'ram': 1740,
        'disk': 350,
        'bandwidth': None
    },
    'c1.xlarge': {
        'id': 'c1.xlarge',
        'name': 'High-CPU Extra Large Instance',
        'ram': 7680,
        'disk': 1690,
        'bandwidth': None
    },
    'm2.xlarge': {
        'id': 'm2.xlarge',
        'name': 'High-Memory Extra Large Instance',
        'ram': 17510,
        'disk': 420,
        'bandwidth': None
    },
    'm2.2xlarge': {
        'id': 'm2.2xlarge',
        'name': 'High-Memory Double Extra Large Instance',
        'ram': 35021,
        'disk': 850,
        'bandwidth': None
    },
    'm2.4xlarge': {
        'id': 'm2.4xlarge',
        'name': 'High-Memory Quadruple Extra Large Instance',
        'ram': 70042,
        'disk': 1690,
        'bandwidth': None
    },
    'cg1.4xlarge': {
        'id': 'cg1.4xlarge',
        'name': 'Cluster GPU Quadruple Extra Large Instance',
        'ram': 22528,
        'disk': 1690,
        'bandwidth': None
    },
    'cc1.4xlarge': {
        'id': 'cc1.4xlarge',
        'name': 'Cluster Compute Quadruple Extra Large Instance',
        'ram': 23552,
        'disk': 1690,
        'bandwidth': None
    },
}

CLUSTER_INSTANCES_IDS = [ 'cg1.4xlarge', 'cc1.4xlarge' ]

EC2_US_EAST_INSTANCE_TYPES = dict(EC2_INSTANCE_TYPES)
EC2_US_WEST_INSTANCE_TYPES = dict(EC2_INSTANCE_TYPES)
EC2_EU_WEST_INSTANCE_TYPES = dict(EC2_INSTANCE_TYPES)
EC2_AP_SOUTHEAST_INSTANCE_TYPES = dict(EC2_INSTANCE_TYPES)
EC2_AP_NORTHEAST_INSTANCE_TYPES = dict(EC2_INSTANCE_TYPES)

#
# On demand prices must also be hardcoded, because Amazon doesn't provide an
# API to fetch them. From http://aws.amazon.com/ec2/pricing/
#
EC2_US_EAST_INSTANCE_TYPES['t1.micro']['price'] = '.02'
EC2_US_EAST_INSTANCE_TYPES['m1.small']['price'] = '.085'
EC2_US_EAST_INSTANCE_TYPES['m1.large']['price'] = '.34'
EC2_US_EAST_INSTANCE_TYPES['m1.xlarge']['price'] = '.68'
EC2_US_EAST_INSTANCE_TYPES['c1.medium']['price'] = '.17'
EC2_US_EAST_INSTANCE_TYPES['c1.xlarge']['price'] = '.68'
EC2_US_EAST_INSTANCE_TYPES['m2.xlarge']['price'] = '.50'
EC2_US_EAST_INSTANCE_TYPES['m2.2xlarge']['price'] = '1.0'
EC2_US_EAST_INSTANCE_TYPES['m2.4xlarge']['price'] = '2.0'
EC2_US_EAST_INSTANCE_TYPES['cg1.4xlarge']['price'] = '2.1'
EC2_US_EAST_INSTANCE_TYPES['cc1.4xlarge']['price'] = '1.6'

EC2_US_WEST_INSTANCE_TYPES['t1.micro']['price'] = '.025'
EC2_US_WEST_INSTANCE_TYPES['m1.small']['price'] = '.095'
EC2_US_WEST_INSTANCE_TYPES['m1.large']['price'] = '.38'
EC2_US_WEST_INSTANCE_TYPES['m1.xlarge']['price'] = '.76'
EC2_US_WEST_INSTANCE_TYPES['c1.medium']['price'] = '.19'
EC2_US_WEST_INSTANCE_TYPES['c1.xlarge']['price'] = '.76'
EC2_US_WEST_INSTANCE_TYPES['m2.xlarge']['price'] = '.57'
EC2_US_WEST_INSTANCE_TYPES['m2.2xlarge']['price'] = '1.14'
EC2_US_WEST_INSTANCE_TYPES['m2.4xlarge']['price'] = '2.28'

EC2_EU_WEST_INSTANCE_TYPES['t1.micro']['price'] = '.025'
EC2_EU_WEST_INSTANCE_TYPES['m1.small']['price'] = '.095'
EC2_EU_WEST_INSTANCE_TYPES['m1.large']['price'] = '.38'
EC2_EU_WEST_INSTANCE_TYPES['m1.xlarge']['price'] = '.76'
EC2_EU_WEST_INSTANCE_TYPES['c1.medium']['price'] = '.19'
EC2_EU_WEST_INSTANCE_TYPES['c1.xlarge']['price'] = '.76'
EC2_EU_WEST_INSTANCE_TYPES['m2.xlarge']['price'] = '.57'
EC2_EU_WEST_INSTANCE_TYPES['m2.2xlarge']['price'] = '1.14'
EC2_EU_WEST_INSTANCE_TYPES['m2.4xlarge']['price'] = '2.28'

# prices are the same
EC2_AP_SOUTHEAST_INSTANCE_TYPES = dict(EC2_EU_WEST_INSTANCE_TYPES)

EC2_AP_NORTHEAST_INSTANCE_TYPES['t1.micro']['price'] = '.027'
EC2_AP_NORTHEAST_INSTANCE_TYPES['m1.small']['price'] = '.10'
EC2_AP_NORTHEAST_INSTANCE_TYPES['m1.large']['price'] = '.40'
EC2_AP_NORTHEAST_INSTANCE_TYPES['m1.xlarge']['price'] = '.80'
EC2_AP_NORTHEAST_INSTANCE_TYPES['c1.medium']['price'] = '.20'
EC2_AP_NORTHEAST_INSTANCE_TYPES['c1.xlarge']['price'] = '.80'
EC2_AP_NORTHEAST_INSTANCE_TYPES['m2.xlarge']['price'] = '.60'
EC2_AP_NORTHEAST_INSTANCE_TYPES['m2.2xlarge']['price'] = '1.20'
EC2_AP_NORTHEAST_INSTANCE_TYPES['m2.4xlarge']['price'] = '2.39'

class EC2NodeLocation(NodeLocation):
    def __init__(self, id, name, country, driver, availability_zone):
        super(EC2NodeLocation, self).__init__(id, name, country, driver)
        self.availability_zone = availability_zone

    def __repr__(self):
        return (('<EC2NodeLocation: id=%s, name=%s, country=%s, '
                 'availability_zone=%s driver=%s>')
                % (self.id, self.name, self.country,
                   self.availability_zone.name, self.driver.name))

class EC2Response(Response):
    """
    EC2 specific response parsing and error handling.
    """
    def parse_body(self):
        if not self.body:
            return None
        try:
          body = ET.XML(self.body)
        except:
          raise MalformedResponseError("Failed to parse XML", body=self.body, driver=EC2NodeDriver)
        return body

    def parse_error(self):
        err_list = []
        # Okay, so for Eucalyptus, you can get a 403, with no body,
        # if you are using the wrong user/password.
        msg = "Failure: 403 Forbidden"
        if self.status == 403 and self.body[:len(msg)] == msg:
            raise InvalidCredsError(msg)

        try:
            body = ET.XML(self.body)
        except:
            raise MalformedResponseError("Failed to parse XML", body=self.body, driver=EC2NodeDriver)

        for err in body.findall('Errors/Error'):
            code, message = err.getchildren()
            err_list.append("%s: %s" % (code.text, message.text))
            if code.text == "InvalidClientTokenId":
                raise InvalidCredsError(err_list[-1])
            if code.text == "SignatureDoesNotMatch":
                raise InvalidCredsError(err_list[-1])
            if code.text == "AuthFailure":
                raise InvalidCredsError(err_list[-1])
            if code.text == "OptInRequired":
                raise InvalidCredsError(err_list[-1])
            if code.text == "IdempotentParameterMismatch":
                raise IdempotentParamError(err_list[-1])
        return "\n".join(err_list)

class EC2Connection(ConnectionUserAndKey):
    """
    Repersents a single connection to the EC2 Endpoint
    """

    host = EC2_US_EAST_HOST
    responseCls = EC2Response

    def add_default_params(self, params):
        params['SignatureVersion'] = '2'
        params['SignatureMethod'] = 'HmacSHA256'
        params['AWSAccessKeyId'] = self.user_id
        params['Version'] = API_VERSION
        params['Timestamp'] = time.strftime('%Y-%m-%dT%H:%M:%SZ',
                                            time.gmtime())
        params['Signature'] = self._get_aws_auth_param(params, self.key, self.action)
        return params

    def _get_aws_auth_param(self, params, secret_key, path='/'):
        """
        Creates the signature required for AWS, per
        http://bit.ly/aR7GaQ [docs.amazonwebservices.com]:

        StringToSign = HTTPVerb + "\n" +
                       ValueOfHostHeaderInLowercase + "\n" +
                       HTTPRequestURI + "\n" +
                       CanonicalizedQueryString <from the preceding step>
        """
        keys = params.keys()
        keys.sort()
        pairs = []
        for key in keys:
            pairs.append(urllib.quote(key, safe='') + '=' +
                         urllib.quote(params[key], safe='-_~'))

        qs = '&'.join(pairs)
        string_to_sign = '\n'.join(('GET', self.host, path, qs))

        b64_hmac = base64.b64encode(
            hmac.new(secret_key, string_to_sign, digestmod=sha256).digest()
        )
        return b64_hmac

class ExEC2AvailabilityZone(object):
    """
    Extension class which stores information about an EC2 availability zone.

    Note: This class is EC2 specific.
    """
    def __init__(self, name, zone_state, region_name):
        self.name = name
        self.zone_state = zone_state
        self.region_name = region_name

    def __repr__(self):
        return (('<ExEC2AvailabilityZone: name=%s, zone_state=%s, '
                 'region_name=%s>')
                % (self.name, self.zone_state, self.region_name))

class EC2NodeDriver(NodeDriver):
    """
    Amazon EC2 node driver
    """

    connectionCls = EC2Connection
    type = Provider.EC2
    name = 'Amazon EC2 (us-east-1)'
    friendly_name = 'Amazon US N. Virginia'
    country = 'US'
    region_name = 'us-east-1'
    path = '/'

    _instance_types = EC2_US_EAST_INSTANCE_TYPES

    NODE_STATE_MAP = {
        'pending': NodeState.PENDING,
        'running': NodeState.RUNNING,
        'shutting-down': NodeState.TERMINATED,
        'terminated': NodeState.TERMINATED
    }

    def _findtext(self, element, xpath):
        return element.findtext(self._fixxpath(xpath))

    def _fixxpath(self, xpath):
        # ElementTree wants namespaces in its xpaths, so here we add them.
        return "/".join(["{%s}%s" % (NAMESPACE, e) for e in xpath.split("/")])

    def _findattr(self, element, xpath):
        return element.findtext(self._fixxpath(xpath))

    def _findall(self, element, xpath):
        return element.findall(self._fixxpath(xpath))

    def _pathlist(self, key, arr):
        """
        Converts a key and an array of values into AWS query param format.
        """
        params = {}
        i = 0
        for value in arr:
            i += 1
            params["%s.%s" % (key, i)] = value
        return params

    def _get_boolean(self, element):
        tag = "{%s}%s" % (NAMESPACE, 'return')
        return element.findtext(tag) == 'true'

    def _get_terminate_boolean(self, element):
        status = element.findtext(".//{%s}%s" % (NAMESPACE, 'name'))
        return any([ term_status == status
                     for term_status
                     in ('shutting-down', 'terminated') ])

    def _to_nodes(self, object, xpath, groups=None):
        return [ self._to_node(el, groups=groups)
                 for el in object.findall(self._fixxpath(xpath)) ]

    def _to_node(self, element, groups=None):
        try:
            state = self.NODE_STATE_MAP[
                self._findattr(element, "instanceState/name")
            ]
        except KeyError:
            state = NodeState.UNKNOWN

        n = Node(
            id=self._findtext(element, 'instanceId'),
            name=self._findtext(element, 'instanceId'),
            state=state,
            public_ip=[self._findtext(element, 'ipAddress')],
            private_ip=[self._findtext(element, 'privateIpAddress')],
            driver=self.connection.driver,
            extra={
                'dns_name': self._findattr(element, "dnsName"),
                'instanceId': self._findattr(element, "instanceId"),
                'imageId': self._findattr(element, "imageId"),
                'private_dns': self._findattr(element, "privateDnsName"),
                'status': self._findattr(element, "instanceState/name"),
                'keyname': self._findattr(element, "keyName"),
                'launchindex': self._findattr(element, "amiLaunchIndex"),
                'productcode':
                    [p.text for p in self._findall(
                        element, "productCodesSet/item/productCode"
                     )],
                'instancetype': self._findattr(element, "instanceType"),
                'launchdatetime': self._findattr(element, "launchTime"),
                'availability': self._findattr(element,
                                               "placement/availabilityZone"),
                'kernelid': self._findattr(element, "kernelId"),
                'ramdiskid': self._findattr(element, "ramdiskId"),
                'clienttoken' : self._findattr(element, "clientToken"),
                'groups': groups
            }
        )
        return n

    def _to_images(self, object):
        return [ self._to_image(el)
                 for el in object.findall(
                    self._fixxpath('imagesSet/item')
                 ) ]

    def _to_image(self, element):
        n = NodeImage(id=self._findtext(element, 'imageId'),
                      name=self._findtext(element, 'imageLocation'),
                      driver=self.connection.driver)
        return n

    def list_nodes(self):
        params = {'Action': 'DescribeInstances' }
        elem=self.connection.request(self.path, params=params).object
        nodes=[]
        for rs in self._findall(elem, 'reservationSet/item'):
            groups=[g.findtext('')
                        for g in self._findall(rs, 'groupSet/item/groupId')]
            nodes += self._to_nodes(rs, 'instancesSet/item', groups)

        nodes_elastic_ips_mappings = self.ex_describe_addresses(nodes)
        for node in nodes:
            node.public_ip.extend(nodes_elastic_ips_mappings[node.id])
        return nodes

    def list_sizes(self, location=None):
        # Cluster instances are currently only available in the US - N. Virginia Region
        include_cluser_instances = self.region_name == 'us-east-1'
        sizes = self._get_sizes(include_cluser_instances =
                                include_cluser_instances)

        return sizes

    def _get_sizes(self, include_cluser_instances=False):
        sizes = [ NodeSize(driver=self.connection.driver, **i)
                         for i in self._instance_types.values() ]

        if not include_cluser_instances:
            sizes = [ size for size in sizes if \
                      size.id not in CLUSTER_INSTANCES_IDS]
        return sizes

    def list_images(self, location=None):
        params = {'Action': 'DescribeImages'}
        images = self._to_images(
            self.connection.request(self.path, params=params).object
        )
        return images

    def list_locations(self):
        locations = []
        for index, availability_zone in enumerate(self.ex_list_availability_zones()):
            locations.append(EC2NodeLocation(index,
                                             self.friendly_name,
                                             self.country,
                                             self,
                                             availability_zone))
        return locations

    def ex_create_keypair(self, name):
        """Creates a new keypair

        @note: This is a non-standard extension API, and
               only works for EC2.

        @type name: C{str}
        @param name: The name of the keypair to Create. This must be
                     unique, otherwise an InvalidKeyPair.Duplicate
                     exception is raised.
        """
        params = {
            'Action': 'CreateKeyPair',
            'KeyName': name,
        }
        response = self.connection.request(self.path, params=params).object
        key_material = self._findtext(response, 'keyMaterial')
        key_fingerprint = self._findtext(response, 'keyFingerprint')
        return {
            'keyMaterial': key_material,
            'keyFingerprint': key_fingerprint,
        }

    def ex_import_keypair(self, name, keyfile):
        """imports a new public key

        @note: This is a non-standard extension API, and only works for EC2.

        @type name: C{str}
        @param name: The name of the public key to import. This must be unique,
                     otherwise an InvalidKeyPair.Duplicate exception is raised.

        @type keyfile: C{str}
        @param keyfile: The filename with path of the public key to import.

        """

        base64key = base64.b64encode(open(os.path.expanduser(keyfile)).read())

        params = {'Action': 'ImportKeyPair',
                  'KeyName': name,
                  'PublicKeyMaterial': base64key
        }

        response = self.connection.request(self.path, params=params).object
        key_name = self._findtext(response, 'keyName')
        key_fingerprint = self._findtext(response, 'keyFingerprint')
        return {
                'keyName': key_name,
                'keyFingerprint': key_fingerprint,
        }

    def ex_describe_keypairs(self, name):
        """Describes a keypiar by name

        @note: This is a non-standard extension API, and only works for EC2.

        @type name: C{str}
        @param name: The name of the keypair to describe.

        """

        params = {'Action': 'DescribeKeyPairs',
                  'KeyName.1': name
        }

        response = self.connection.request(self.path, params=params).object
        key_name = self._findattr(response, 'keySet/item/keyName')
        return {
                'keyName': key_name
        }

    def ex_create_security_group(self, name, description):
        """Creates a new Security Group

        @note: This is a non-standard extension API, and only works for EC2.

        @type name: C{str}
        @param name: The name of the security group to Create. This must be unique.

        @type description: C{str}
        @param description: Human readable description of a Security Group.
        """
        params = {'Action': 'CreateSecurityGroup',
                  'GroupName': name,
                  'GroupDescription': description}
        return self.connection.request(self.path, params=params).object

    def ex_authorize_security_group_permissive(self, name):
        """Edit a Security Group to allow all traffic.

        @note: This is a non-standard extension API, and only works for EC2.

        @type name: C{str}
        @param name: The name of the security group to edit
        """

        results = []
        params = {'Action': 'AuthorizeSecurityGroupIngress',
                  'GroupName': name,
                  'IpProtocol': 'tcp',
                  'FromPort': '0',
                  'ToPort': '65535',
                  'CidrIp': '0.0.0.0/0'}
        try:
            results.append(
                self.connection.request(self.path, params=params.copy()).object
            )
        except Exception, e:
            if e.args[0].find("InvalidPermission.Duplicate") == -1:
                raise e
        params['IpProtocol'] = 'udp'

        try:
            results.append(
                self.connection.request(self.path, params=params.copy()).object
            )
        except Exception, e:
            if e.args[0].find("InvalidPermission.Duplicate") == -1:
                raise e

        params.update({'IpProtocol': 'icmp', 'FromPort': '-1', 'ToPort': '-1'})

        try:
            results.append(
                self.connection.request(self.path, params=params.copy()).object
            )
        except Exception, e:
            if e.args[0].find("InvalidPermission.Duplicate") == -1:
                raise e
        return results

    def ex_list_availability_zones(self, only_available=True):
        """
        Return a list of L{ExEC2AvailabilityZone} objects for the
        current region.

        Note: This is an extension method and is only available for EC2
        driver.

        @keyword  only_available: If true, return only availability zones
                                  with state 'available'
        @type     only_available: C{string}
        """
        params = {'Action': 'DescribeAvailabilityZones'}

        if only_available:
            params.update({'Filter.0.Name': 'state'})
            params.update({'Filter.0.Value.0': 'available'})

        params.update({'Filter.1.Name': 'region-name'})
        params.update({'Filter.1.Value.0': self.region_name})

        result = self.connection.request(self.path,
                                         params=params.copy()).object

        availability_zones = []
        for element in self._findall(result, 'availabilityZoneInfo/item'):
            name = self._findtext(element, 'zoneName')
            zone_state = self._findtext(element, 'zoneState')
            region_name = self._findtext(element, 'regionName')

            availability_zone = ExEC2AvailabilityZone(
                name=name,
                zone_state=zone_state,
                region_name=region_name
            )
            availability_zones.append(availability_zone)

        return availability_zones

    def ex_describe_tags(self, node):
        """
        Return a dictionary of tags for this instance.

        @type node: C{Node}
        @param node: Node instance

        @return dict Node tags
        """
        params = { 'Action': 'DescribeTags',
                   'Filter.0.Name': 'resource-id',
                   'Filter.0.Value.0': node.id,
                   'Filter.1.Name': 'resource-type',
                   'Filter.1.Value.0': 'instance',
                   }

        result = self.connection.request(self.path,
                                         params=params.copy()).object

        tags = {}
        for element in self._findall(result, 'tagSet/item'):
            key = self._findtext(element, 'key')
            value = self._findtext(element, 'value')

            tags[key] = value
        return tags

    def ex_create_tags(self, node, tags):
        """
        Create tags for an instance.

        @type node: C{Node}
        @param node: Node instance
        @param tags: A dictionary or other mapping of strings to strings,
                     associating tag names with tag values.
        """
        if not tags:
            return

        params = { 'Action': 'CreateTags',
                   'ResourceId.0': node.id }
        for i, key in enumerate(tags):
            params['Tag.%d.Key' % i] = key
            params['Tag.%d.Value' % i] = tags[key]

        self.connection.request(self.path,
                                params=params.copy()).object

    def ex_delete_tags(self, node, tags):
        """
        Delete tags from an instance.

        @type node: C{Node}
        @param node: Node instance
        @param tags: A dictionary or other mapping of strings to strings,
                     specifying the tag names and tag values to be deleted.
        """
        if not tags:
            return

        params = { 'Action': 'DeleteTags',
                   'ResourceId.0': node.id }
        for i, key in enumerate(tags):
            params['Tag.%d.Key' % i] = key
            params['Tag.%d.Value' % i] = tags[key]

        self.connection.request(self.path,
                                params=params.copy()).object

    def ex_describe_addresses(self, nodes):
        """
        Return Elastic IP addresses for all the nodes in the provided list.

        @type nodes: C{list}
        @param nodes: List of C{Node} instances

        @return dict Dictionary where a key is a node ID and the value is a
                     list with the Elastic IP addresses associated with this node.
        """
        if not nodes:
            return {}

        params = { 'Action': 'DescribeAddresses' }

        if len(nodes) == 1:
           params.update({
                  'Filter.0.Name': 'instance-id',
                  'Filter.0.Value.0': nodes[0].id
           })

        result = self.connection.request(self.path,
                                         params=params.copy()).object

        node_instance_ids = [ node.id for node in nodes ]
        nodes_elastic_ip_mappings = {}

        for node_id in node_instance_ids:
            nodes_elastic_ip_mappings.setdefault(node_id, [])
        for element in self._findall(result, 'addressesSet/item'):
            instance_id = self._findtext(element, 'instanceId')
            ip_address = self._findtext(element, 'publicIp')

            if instance_id not in node_instance_ids:
                continue

            nodes_elastic_ip_mappings[instance_id].append(ip_address)
        return nodes_elastic_ip_mappings

    def ex_describe_addresses_for_node(self, node):
        """
        Return a list of Elastic IP addresses associated with this node.

        @type node: C{Node}
        @param node: Node instance

        @return list Elastic IP addresses attached to this node.
        """
        node_elastic_ips = self.ex_describe_addresses([node])
        return node_elastic_ips[node.id]

    def create_node(self, **kwargs):
        """Create a new EC2 node

        See L{NodeDriver.create_node} for more keyword args.
        Reference: http://bit.ly/8ZyPSy [docs.amazonwebservices.com]

        @keyword    ex_mincount: Minimum number of instances to launch
        @type       ex_mincount: C{int}

        @keyword    ex_maxcount: Maximum number of instances to launch
        @type       ex_maxcount: C{int}

        @keyword    ex_securitygroup: Name of security group
        @type       ex_securitygroup: C{str}

        @keyword    ex_keyname: The name of the key pair
        @type       ex_keyname: C{str}

        @keyword    ex_userdata: User data
        @type       ex_userdata: C{str}

        @keyword    ex_clienttoken: Unique identifier to ensure idempotency
        @type       ex_clienttoken: C{str}
        """
        image = kwargs["image"]
        size = kwargs["size"]
        params = {
            'Action': 'RunInstances',
            'ImageId': image.id,
            'MinCount': kwargs.get('ex_mincount','1'),
            'MaxCount': kwargs.get('ex_maxcount','1'),
            'InstanceType': size.id
        }

        if 'ex_securitygroup' in kwargs:
            if not isinstance(kwargs['ex_securitygroup'], list):
                kwargs['ex_securitygroup'] = [kwargs['ex_securitygroup']]
            for sig in range(len(kwargs['ex_securitygroup'])):
                params['SecurityGroup.%d' % (sig+1,)]  = kwargs['ex_securitygroup'][sig]

        if 'location' in kwargs:
            availability_zone = getattr(kwargs['location'], 'availability_zone',
                                        None)
            if availability_zone:
                if availability_zone.region_name != self.region_name:
                    raise AttributeError('Invalid availability zone: %s'
                                         % (availability_zone.name))
                params['Placement.AvailabilityZone'] = availability_zone.name

        if 'ex_keyname' in kwargs:
            params['KeyName'] = kwargs['ex_keyname']

        if 'ex_userdata' in kwargs:
            params['UserData'] = base64.b64encode(kwargs['ex_userdata'])

        if 'ex_clienttoken' in kwargs:
            params['ClientToken'] = kwargs['ex_clienttoken']

        object = self.connection.request(self.path, params=params).object
        nodes = self._to_nodes(object, 'instancesSet/item')

        if len(nodes) == 1:
            return nodes[0]
        else:
            return nodes

    def reboot_node(self, node):
        """
        Reboot the node by passing in the node object
        """
        params = {'Action': 'RebootInstances'}
        params.update(self._pathlist('InstanceId', [node.id]))
        res = self.connection.request(self.path, params=params).object
        return self._get_boolean(res)

    def destroy_node(self, node):
        """
        Destroy node by passing in the node object
        """
        params = {'Action': 'TerminateInstances'}
        params.update(self._pathlist('InstanceId', [node.id]))
        res = self.connection.request(self.path, params=params).object
        return self._get_terminate_boolean(res)

class IdempotentParamError(LibcloudError):
    """
    Request used the same client token as a previous, but non-identical request.
    """
    def __str__(self):
        return repr(self.value)

class EC2EUConnection(EC2Connection):
    """
    Connection class for EC2 in the Western Europe Region
    """
    host = EC2_EU_WEST_HOST

class EC2EUNodeDriver(EC2NodeDriver):
    """
    Driver class for EC2 in the Western Europe Region
    """

    name = 'Amazon EC2 (eu-west-1)'
    friendly_name = 'Amazon Europe Ireland'
    country = 'IE'
    region_name = 'eu-west-1'
    connectionCls = EC2EUConnection
    _instance_types = EC2_EU_WEST_INSTANCE_TYPES

class EC2USWestConnection(EC2Connection):
    """
    Connection class for EC2 in the Western US Region
    """

    host = EC2_US_WEST_HOST

class EC2USWestNodeDriver(EC2NodeDriver):
    """
    Driver class for EC2 in the Western US Region
    """

    name = 'Amazon EC2 (us-west-1)'
    friendly_name = 'Amazon US N. California'
    country = 'US'
    region_name = 'us-west-1'
    connectionCls = EC2USWestConnection
    _instance_types = EC2_US_WEST_INSTANCE_TYPES

class EC2APSEConnection(EC2Connection):
    """
    Connection class for EC2 in the Southeast Asia Pacific Region
    """

    host = EC2_AP_SOUTHEAST_HOST

class EC2APNEConnection(EC2Connection):
    """
    Connection class for EC2 in the Northeast Asia Pacific Region
    """

    host = EC2_AP_NORTHEAST_HOST

class EC2APSENodeDriver(EC2NodeDriver):
    """
    Driver class for EC2 in the Southeast Asia Pacific Region
    """

    name = 'Amazon EC2 (ap-southeast-1)'
    friendly_name = 'Amazon Asia-Pacific Singapore'
    country = 'SG'
    region_name = 'ap-southeast-1'
    connectionCls = EC2APSEConnection
    _instance_types = EC2_AP_SOUTHEAST_INSTANCE_TYPES

class EC2APNENodeDriver(EC2NodeDriver):
    """
    Driver class for EC2 in the Northeast Asia Pacific Region
    """

    name = 'Amazon EC2 (ap-northeast-1)'
    friendly_name = 'Amazon Asia-Pacific Tokyo'
    country = 'JP'
    region_name = 'ap-northeast-1'
    connectionCls = EC2APNEConnection
    _instance_types = EC2_AP_NORTHEAST_INSTANCE_TYPES

class EucConnection(EC2Connection):
    """
    Connection class for Eucalyptus
    """

    host = None

class EucNodeDriver(EC2NodeDriver):
    """
    Driver class for Eucalyptus
    """

    name = 'Eucalyptus'
    connectionCls = EucConnection
    _instance_types = EC2_US_WEST_INSTANCE_TYPES

    def __init__(self, key, secret=None, secure=True, host=None, path=None, port=None):
        super(EucNodeDriver, self).__init__(key, secret, secure, host, port)
        if path is None:
            path = "/services/Eucalyptus"
        self.path = path

    def list_locations(self):
        raise NotImplementedError, \
            'list_locations not implemented for this driver'

########NEW FILE########
__FILENAME__ = ecp
# Licensed to the Apache Software Foundation (ASF) under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Enomaly ECP driver
"""
import time
import base64
import httplib
import socket
import os

# JSON is included in the standard library starting with Python 2.6.  For 2.5
# and 2.4, there's a simplejson egg at: http://pypi.python.org/pypi/simplejson
try:
    import json
except:
    import simplejson as json

from libcloud.common.base import Response, ConnectionUserAndKey
from libcloud.compute.base import NodeDriver, NodeSize, NodeLocation
from libcloud.compute.base import NodeImage, Node
from libcloud.compute.types import Provider, NodeState, InvalidCredsError
from libcloud.compute.base import is_private_subnet

#Defaults
API_HOST = ''
API_PORT = (80,443)

class ECPResponse(Response):

    def success(self):
        if self.status == httplib.OK or self.status == httplib.CREATED:
            try:
                j_body = json.loads(self.body)
            except ValueError:
                self.error = "JSON response cannot be decoded."
                return False
            if j_body['errno'] == 0:
                return True
            else:
                self.error = "ECP error: %s" % j_body['message']
                return False
        elif self.status == httplib.UNAUTHORIZED:
            raise InvalidCredsError()
        else:
            self.error = "HTTP Error Code: %s" % self.status
        return False

    def parse_error(self):
        return self.error

    #Interpret the json responses - no error checking required
    def parse_body(self):
        return json.loads(self.body)

    def getheaders(self):
        return self.headers

class ECPConnection(ConnectionUserAndKey):
    """
    Connection class for the Enomaly ECP driver
    """

    responseCls = ECPResponse
    host = API_HOST
    port = API_PORT

    def add_default_headers(self, headers):
        #Authentication
        username = self.user_id
        password = self.key
        base64string =  base64.encodestring(
                '%s:%s' % (username, password))[:-1]
        authheader =  "Basic %s" % base64string
        headers['Authorization']= authheader

        return headers

    def _encode_multipart_formdata(self, fields):
        """
        Based on Wade Leftwich's function:
        http://code.activestate.com/recipes/146306/
        """
        #use a random boundary that does not appear in the fields
        boundary = ''
        while boundary in ''.join(fields):
            boundary = os.urandom(16).encode('hex')
        L = []
        for i in fields:
            L.append('--' + boundary)
            L.append('Content-Disposition: form-data; name="%s"' % i)
            L.append('')
            L.append(fields[i])
        L.append('--' + boundary + '--')
        L.append('')
        body = '\r\n'.join(L)
        content_type = 'multipart/form-data; boundary=%s' % boundary
        header = {'Content-Type':content_type}
        return header, body


class ECPNodeDriver(NodeDriver):
    """
    Enomaly ECP node driver
    """

    name = "Enomaly Elastic Computing Platform"
    type = Provider.ECP
    connectionCls = ECPConnection

    def list_nodes(self):
        """
        Returns a list of all running Nodes
        """

        #Make the call
        res = self.connection.request('/rest/hosting/vm/list').parse_body()

        #Put together a list of node objects
        nodes=[]
        for vm in res['vms']:
            node = self._to_node(vm)
            if not node == None:
                nodes.append(node)

        #And return it
        return nodes


    def _to_node(self, vm):
        """
        Turns a (json) dictionary into a Node object.
        This returns only running VMs.
        """

        #Check state
        if not vm['state'] == "running":
            return None

        #IPs
        iplist = [interface['ip'] for interface in vm['interfaces']  if interface['ip'] != '127.0.0.1']

        public_ips = []
        private_ips = []
        for ip in iplist:
            try:
                socket.inet_aton(ip)
            except socket.error:
                # not a valid ip
                continue
            if is_private_subnet(ip):
                private_ips.append(ip)
            else:
                public_ips.append(ip)

        #Create the node object
        n = Node(
          id=vm['uuid'],
          name=vm['name'],
          state=NodeState.RUNNING,
          public_ip=public_ips,
          private_ip=private_ips,
          driver=self,
        )

        return n

    def reboot_node(self, node):
        """
        Shuts down a VM and then starts it again.
        """

        #Turn the VM off
        #Black magic to make the POST requests work
        d = self.connection._encode_multipart_formdata({'action':'stop'})
        self.connection.request(
                   '/rest/hosting/vm/%s' % node.id,
                   method='POST',
                   headers=d[0],
                   data=d[1]
        ).parse_body()

        node.state = NodeState.REBOOTING
        #Wait for it to turn off and then continue (to turn it on again)
        while node.state == NodeState.REBOOTING:
            #Check if it's off.
            response = self.connection.request(
                     '/rest/hosting/vm/%s' % node.id
                     ).parse_body()
            if response['vm']['state'] == 'off':
                node.state = NodeState.TERMINATED
            else:
                time.sleep(5)


        #Turn the VM back on.
        #Black magic to make the POST requests work
        d = self.connection._encode_multipart_formdata({'action':'start'})
        self.connection.request(
            '/rest/hosting/vm/%s' % node.id,
            method='POST',
            headers=d[0],
            data=d[1]
        ).parse_body()

        node.state = NodeState.RUNNING
        return True

    def destroy_node(self, node):
        """
        Shuts down and deletes a VM.
        """

        #Shut down first
        #Black magic to make the POST requests work
        d = self.connection._encode_multipart_formdata({'action':'stop'})
        self.connection.request(
            '/rest/hosting/vm/%s' % node.id,
            method = 'POST',
            headers=d[0],
            data=d[1]
        ).parse_body()

        #Ensure there was no applicationl level error
        node.state = NodeState.PENDING
        #Wait for the VM to turn off before continuing
        while node.state == NodeState.PENDING:
            #Check if it's off.
            response = self.connection.request(
                       '/rest/hosting/vm/%s' % node.id
                       ).parse_body()
            if response['vm']['state'] == 'off':
                node.state = NodeState.TERMINATED
            else:
                time.sleep(5)

        #Delete the VM
        #Black magic to make the POST requests work
        d = self.connection._encode_multipart_formdata({'action':'delete'})
        self.connection.request(
            '/rest/hosting/vm/%s' % (node.id),
            method='POST',
            headers=d[0],
            data=d[1]
        ).parse_body()

        return True

    def list_images(self, location=None):
        """
        Returns a list of all package templates aka appiances aka images
        """

        #Make the call
        response = self.connection.request(
            '/rest/hosting/ptemplate/list').parse_body()

        #Turn the response into an array of NodeImage objects
        images = []
        for ptemplate in response['packages']:
            images.append(NodeImage(
                id = ptemplate['uuid'],
                name= '%s: %s' % (ptemplate['name'], ptemplate['description']),
                driver = self,
                ))

        return images


    def list_sizes(self, location=None):
        """
        Returns a list of all hardware templates
        """

        #Make the call
        response = self.connection.request(
            '/rest/hosting/htemplate/list').parse_body()

        #Turn the response into an array of NodeSize objects
        sizes = []
        for htemplate in response['templates']:
            sizes.append(NodeSize(
                id = htemplate['uuid'],
                name = htemplate['name'],
                ram = htemplate['memory'],
                disk = 0, #Disk is independent of hardware template
                bandwidth = 0, #There is no way to keep track of bandwidth
                price = 0, #The billing system is external
                driver = self,
                ))

        return sizes

    def list_locations(self):
        """
        This feature does not exist in ECP. Returns hard coded dummy location.
        """
        return [
          NodeLocation(id=1,
                       name="Cloud",
                       country='',
                       driver=self),
        ]

    def create_node(self, **kwargs):
        """
        Creates a virtual machine.

        Parameters: name (string), image (NodeImage), size (NodeSize)
        """

        #Find out what network to put the VM on.
        res = self.connection.request('/rest/hosting/network/list').parse_body()

        #Use the first / default network because there is no way to specific
        #which one
        network = res['networks'][0]['uuid']

        #Prepare to make the VM
        data = {
            'name' : str(kwargs['name']),
            'package' : str(kwargs['image'].id),
            'hardware' : str(kwargs['size'].id),
            'network_uuid' : str(network),
            'disk' : ''
        }

        #Black magic to make the POST requests work
        d = self.connection._encode_multipart_formdata(data)
        response = self.connection.request(
            '/rest/hosting/vm/',
            method='PUT',
            headers = d[0],
            data=d[1]
        ).parse_body()

        #Create a node object and return it.
        n = Node(
            id=response['machine_id'],
            name=data['name'],
            state=NodeState.PENDING,
            public_ip=[],
            private_ip=[],
            driver=self,
        )

        return n

########NEW FILE########
__FILENAME__ = elastichosts
# Licensed to the Apache Software Foundation (ASF) under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""
ElasticHosts Driver
"""
import re
import time
import base64

try:
    import json
except:
    import simplejson as json

from libcloud.common.base import ConnectionUserAndKey, Response
from libcloud.common.types import InvalidCredsError, MalformedResponseError
from libcloud.compute.types import Provider, NodeState
from libcloud.compute.base import NodeDriver, NodeSize, Node
from libcloud.compute.base import NodeImage
from libcloud.compute.deployment import ScriptDeployment, SSHKeyDeployment, MultiStepDeployment

# API end-points
API_ENDPOINTS = {
    'uk-1': {
        'name': 'London Peer 1',
        'country': 'United Kingdom',
        'host': 'api.lon-p.elastichosts.com'
    },
     'uk-2': {
        'name': 'London BlueSquare',
        'country': 'United Kingdom',
        'host': 'api.lon-b.elastichosts.com'
    },
     'us-1': {
        'name': 'San Antonio Peer 1',
        'country': 'United States',
        'host': 'api.sat-p.elastichosts.com'
    },
}

# Default API end-point for the base connection clase.
DEFAULT_ENDPOINT = 'us-1'

# ElasticHosts doesn't specify special instance types, so I just specified
# some plans based on the pricing page
# (http://www.elastichosts.com/cloud-hosting/pricing)
# and other provides.
#
# Basically for CPU any value between 500Mhz and 20000Mhz should work,
# 256MB to 8192MB for ram and 1GB to 2TB for disk.
INSTANCE_TYPES = {
    'small': {
        'id': 'small',
        'name': 'Small instance',
        'cpu': 2000,
        'memory': 1700,
        'disk': 160,
        'bandwidth': None,
    },
    'large': {
        'id': 'large',
        'name': 'Large instance',
        'cpu': 4000,
        'memory': 7680,
        'disk': 850,
        'bandwidth': None,
    },
    'extra-large': {
        'id': 'extra-large',
        'name': 'Extra Large instance',
        'cpu': 8000,
        'memory': 8192,
        'disk': 1690,
        'bandwidth': None,
    },
    'high-cpu-medium': {
        'id': 'high-cpu-medium',
        'name': 'High-CPU Medium instance',
        'cpu': 5000,
        'memory': 1700,
        'disk': 350,
        'bandwidth': None,
    },
    'high-cpu-extra-large': {
        'id': 'high-cpu-extra-large',
        'name': 'High-CPU Extra Large instance',
        'cpu': 20000,
        'memory': 7168,
        'disk': 1690,
        'bandwidth': None,
    },
}

# Retrieved from http://www.elastichosts.com/cloud-hosting/api
STANDARD_DRIVES = {
    '38df0986-4d85-4b76-b502-3878ffc80161': {
        'uuid': '38df0986-4d85-4b76-b502-3878ffc80161',
        'description': 'CentOS Linux 5.5',
        'size_gunzipped': '3GB',
        'supports_deployment': True,
    },
    '980cf63c-f21e-4382-997b-6541d5809629': {
        'uuid': '980cf63c-f21e-4382-997b-6541d5809629',
        'description': 'Debian Linux 5.0',
        'size_gunzipped': '1GB',
        'supports_deployment': True,
    },
    'aee5589a-88c3-43ef-bb0a-9cab6e64192d': {
        'uuid': 'aee5589a-88c3-43ef-bb0a-9cab6e64192d',
        'description': 'Ubuntu Linux 10.04',
        'size_gunzipped': '1GB',
        'supports_deployment': True,
    },
    'b9d0eb72-d273-43f1-98e3-0d4b87d372c0': {
        'uuid': 'b9d0eb72-d273-43f1-98e3-0d4b87d372c0',
        'description': 'Windows Web Server 2008',
        'size_gunzipped': '13GB',
        'supports_deployment': False,
    },
    '30824e97-05a4-410c-946e-2ba5a92b07cb': {
        'uuid': '30824e97-05a4-410c-946e-2ba5a92b07cb',
        'description': 'Windows Web Server 2008 R2',
        'size_gunzipped': '13GB',
        'supports_deployment': False,
    },
    '9ecf810e-6ad1-40ef-b360-d606f0444671': {
        'uuid': '9ecf810e-6ad1-40ef-b360-d606f0444671',
        'description': 'Windows Web Server 2008 R2 + SQL Server',
        'size_gunzipped': '13GB',
        'supports_deployment': False,
    },
    '10a88d1c-6575-46e3-8d2c-7744065ea530': {
        'uuid': '10a88d1c-6575-46e3-8d2c-7744065ea530',
        'description': 'Windows Server 2008 Standard R2',
        'size_gunzipped': '13GB',
        'supports_deployment': False,
    },
    '2567f25c-8fb8-45c7-95fc-bfe3c3d84c47': {
        'uuid': '2567f25c-8fb8-45c7-95fc-bfe3c3d84c47',
        'description': 'Windows Server 2008 Standard R2 + SQL Server',
        'size_gunzipped': '13GB',
        'supports_deployment': False,
    },
}

NODE_STATE_MAP = {
    'active': NodeState.RUNNING,
    'dead': NodeState.TERMINATED,
    'dumped': NodeState.TERMINATED,
}

# Default timeout (in seconds) for the drive imaging process
IMAGING_TIMEOUT = 10 * 60

class ElasticHostsException(Exception):
    """
    Exception class for ElasticHosts driver
    """

    def __str__(self):
        return self.args[0]

    def __repr__(self):
        return "<ElasticHostsException '%s'>" % (self.args[0])

class ElasticHostsResponse(Response):
    def success(self):
        if self.status == 401:
            raise InvalidCredsError()

        return self.status >= 200 and self.status <= 299

    def parse_body(self):
        if not self.body:
            return self.body

        try:
            data = json.loads(self.body)
        except:
            raise MalformedResponseError("Failed to parse JSON",
                                         body=self.body,
                                         driver=ElasticHostsBaseNodeDriver)

        return data

    def parse_error(self):
        error_header = self.headers.get('x-elastic-error', '')
        return 'X-Elastic-Error: %s (%s)' % (error_header, self.body.strip())

class ElasticHostsNodeSize(NodeSize):
    def __init__(self, id, name, cpu, ram, disk, bandwidth, price, driver):
        self.id = id
        self.name = name
        self.cpu = cpu
        self.ram = ram
        self.disk = disk
        self.bandwidth = bandwidth
        self.price = price
        self.driver = driver

    def __repr__(self):
        return (('<NodeSize: id=%s, name=%s, cpu=%s, ram=%s '
                 'disk=%s bandwidth=%s price=%s driver=%s ...>')
                % (self.id, self.name, self.cpu, self.ram,
                   self.disk, self.bandwidth, self.price, self.driver.name))

class ElasticHostsBaseConnection(ConnectionUserAndKey):
    """
    Base connection class for the ElasticHosts driver
    """

    host = API_ENDPOINTS[DEFAULT_ENDPOINT]['host']
    responseCls = ElasticHostsResponse

    def add_default_headers(self, headers):
        headers['Accept'] = 'application/json'
        headers['Content-Type'] = 'application/json'
        headers['Authorization'] = ('Basic %s'
                                    % (base64.b64encode('%s:%s'
                                                        % (self.user_id,
                                                           self.key))))
        return headers

class ElasticHostsBaseNodeDriver(NodeDriver):
    """
    Base ElasticHosts node driver
    """

    type = Provider.ELASTICHOSTS
    name = 'ElasticHosts'
    connectionCls = ElasticHostsBaseConnection
    features = {"create_node": ["generates_password"]}

    def reboot_node(self, node):
        # Reboots the node
        response = self.connection.request(
            action='/servers/%s/reset' % (node.id),
            method='POST'
        )
        return response.status == 204

    def destroy_node(self, node):
        # Kills the server immediately
        response = self.connection.request(
            action='/servers/%s/destroy' % (node.id),
            method='POST'
        )
        return response.status == 204

    def list_images(self, location=None):
        # Returns a list of available pre-installed system drive images
        images = []
        for key, value in STANDARD_DRIVES.iteritems():
            image = NodeImage(
                id=value['uuid'],
                name=value['description'],
                driver=self.connection.driver,
                extra={
                    'size_gunzipped': value['size_gunzipped']
                }
            )
            images.append(image)

        return images

    def list_sizes(self, location=None):
        sizes = []
        for key, value in INSTANCE_TYPES.iteritems():
            size = ElasticHostsNodeSize(
                id=value['id'],
                name=value['name'], cpu=value['cpu'], ram=value['memory'],
                disk=value['disk'], bandwidth=value['bandwidth'], price='',
                driver=self.connection.driver
            )
            sizes.append(size)

        return sizes

    def list_nodes(self):
        # Returns a list of active (running) nodes
        response = self.connection.request(action='/servers/info').object

        nodes = []
        for data in response:
            node = self._to_node(data)
            nodes.append(node)

        return nodes

    def create_node(self, **kwargs):
        """Creates a ElasticHosts instance

        See L{NodeDriver.create_node} for more keyword args.

        @keyword    name: String with a name for this new node (required)
        @type       name: C{string}

        @keyword    smp: Number of virtual processors or None to calculate
                         based on the cpu speed
        @type       smp: C{int}

        @keyword    nic_model: e1000, rtl8139 or virtio
                               (if not specified, e1000 is used)
        @type       nic_model: C{string}

        @keyword    vnc_password: If set, the same password is also used for
                                  SSH access with user toor,
                                  otherwise VNC access is disabled and
                                  no SSH login is possible.
        @type       vnc_password: C{string}
        """
        size = kwargs['size']
        image = kwargs['image']
        smp = kwargs.get('smp', 'auto')
        nic_model = kwargs.get('nic_model', 'e1000')
        vnc_password = ssh_password = kwargs.get('vnc_password', None)

        if nic_model not in ('e1000', 'rtl8139', 'virtio'):
            raise ElasticHostsException('Invalid NIC model specified')

        # check that drive size is not smaller then pre installed image size

        # First we create a drive with the specified size
        drive_data = {}
        drive_data.update({'name': kwargs['name'],
                           'size': '%sG' % (kwargs['size'].disk)})

        response = self.connection.request(action='/drives/create',
                                           data=json.dumps(drive_data),
                                           method='POST').object

        if not response:
            raise ElasticHostsException('Drive creation failed')

        drive_uuid = response['drive']

        # Then we image the selected pre-installed system drive onto it
        response = self.connection.request(
            action='/drives/%s/image/%s/gunzip' % (drive_uuid, image.id),
            method='POST'
        )

        if response.status != 204:
            raise ElasticHostsException('Drive imaging failed')

        # We wait until the drive is imaged and then boot up the node
        # (in most cases, the imaging process shouldn't take longer
        # than a few minutes)
        response = self.connection.request(
            action='/drives/%s/info' % (drive_uuid)
        ).object
        imaging_start = time.time()
        while response.has_key('imaging'):
            response = self.connection.request(
                action='/drives/%s/info' % (drive_uuid)
            ).object
            elapsed_time = time.time() - imaging_start
            if (response.has_key('imaging')
                and elapsed_time >= IMAGING_TIMEOUT):
                raise ElasticHostsException('Drive imaging timed out')
            time.sleep(1)

        node_data = {}
        node_data.update({'name': kwargs['name'],
                          'cpu': size.cpu,
                          'mem': size.ram,
                          'ide:0:0': drive_uuid,
                          'boot': 'ide:0:0',
                          'smp': smp})
        node_data.update({'nic:0:model': nic_model, 'nic:0:dhcp': 'auto'})

        if vnc_password:
            node_data.update({'vnc:ip': 'auto', 'vnc:password': vnc_password})

        response = self.connection.request(
            action='/servers/create', data=json.dumps(node_data),
            method='POST'
        ).object

        if isinstance(response, list):
            nodes = [self._to_node(node, ssh_password) for node in response]
        else:
            nodes = self._to_node(response, ssh_password)

        return nodes

    # Extension methods
    def ex_set_node_configuration(self, node, **kwargs):
        # Changes the configuration of the running server
        valid_keys = ('^name$', '^parent$', '^cpu$', '^smp$', '^mem$',
                      '^boot$', '^nic:0:model$', '^nic:0:dhcp',
                      '^nic:1:model$', '^nic:1:vlan$', '^nic:1:mac$',
                      '^vnc:ip$', '^vnc:password$', '^vnc:tls',
                      '^ide:[0-1]:[0-1](:media)?$',
                      '^scsi:0:[0-7](:media)?$', '^block:[0-7](:media)?$')

        invalid_keys = []
        for key in kwargs.keys():
            matches = False
            for regex in valid_keys:
                if re.match(regex, key):
                    matches = True
                    break
            if not matches:
                invalid_keys.append(key)

        if invalid_keys:
            raise ElasticHostsException(
                'Invalid configuration key specified: %s'
                % (',' .join(invalid_keys))
            )

        response = self.connection.request(
            action='/servers/%s/set' % (node.id), data=json.dumps(kwargs),
            method='POST'
        )

        return (response.status == 200 and response.body != '')

    def deploy_node(self, **kwargs):
        """
        Create a new node, and start deployment.

        @keyword    enable_root: If true, root password will be set to
                                 vnc_password (this will enable SSH access)
                                 and default 'toor' account will be deleted.
        @type       enable_root: C{bool}

        For detailed description and keywords args, see
        L{NodeDriver.deploy_node}.
        """
        image = kwargs['image']
        vnc_password = kwargs.get('vnc_password', None)
        enable_root = kwargs.get('enable_root', False)

        if not vnc_password:
            raise ValueError('You need to provide vnc_password argument '
                             'if you want to use deployment')

        if (image in STANDARD_DRIVES
            and STANDARD_DRIVES[image]['supports_deployment']):
            raise ValueError('Image %s does not support deployment'
                             % (image.id))

        if enable_root:
            script = ("unset HISTFILE;"
                      "echo root:%s | chpasswd;"
                      "sed -i '/^toor.*$/d' /etc/passwd /etc/shadow;"
                      "history -c") % vnc_password
            root_enable_script = ScriptDeployment(script=script,
                                                  delete=True)
            deploy = kwargs.get('deploy', None)
            if deploy:
                if (isinstance(deploy, ScriptDeployment)
                    or isinstance(deploy, SSHKeyDeployment)):
                    deployment = MultiStepDeployment([deploy,
                                                      root_enable_script])
                elif isinstance(deploy, MultiStepDeployment):
                    deployment = deploy
                    deployment.add(root_enable_script)
            else:
                deployment = root_enable_script

            kwargs['deploy'] = deployment

        if not kwargs.get('ssh_username', None):
            kwargs['ssh_username'] = 'toor'

        return super(ElasticHostsBaseNodeDriver, self).deploy_node(**kwargs)

    def ex_shutdown_node(self, node):
        # Sends the ACPI power-down event
        response = self.connection.request(
            action='/servers/%s/shutdown' % (node.id),
            method='POST'
        )
        return response.status == 204

    def ex_destroy_drive(self, drive_uuid):
        # Deletes a drive
        response = self.connection.request(
            action='/drives/%s/destroy' % (drive_uuid),
            method='POST'
        )
        return response.status == 204

    # Helper methods
    def _to_node(self, data, ssh_password=None):
        try:
            state = NODE_STATE_MAP[data['status']]
        except KeyError:
            state = NodeState.UNKNOWN

        if isinstance(data['nic:0:dhcp'], list):
            public_ip = data['nic:0:dhcp']
        else:
            public_ip = [data['nic:0:dhcp']]

        extra = {'cpu': data['cpu'],
                 'smp': data['smp'],
                 'mem': data['mem'],
                 'started': data['started']}

        if data.has_key('vnc:ip') and data.has_key('vnc:password'):
            extra.update({'vnc_ip': data['vnc:ip'],
                          'vnc_password': data['vnc:password']})

        if ssh_password:
            extra.update({'password': ssh_password})

        node = Node(id=data['server'], name=data['name'], state=state,
                    public_ip=public_ip, private_ip=None,
                    driver=self.connection.driver,
                    extra=extra)

        return node

class ElasticHostsUK1Connection(ElasticHostsBaseConnection):
    """
    Connection class for the ElasticHosts driver for
    the London Peer 1 end-point
    """

    host = API_ENDPOINTS['uk-1']['host']

class ElasticHostsUK1NodeDriver(ElasticHostsBaseNodeDriver):
    """
    ElasticHosts node driver for the London Peer 1 end-point
    """
    connectionCls = ElasticHostsUK1Connection

class ElasticHostsUK2Connection(ElasticHostsBaseConnection):
    """
    Connection class for the ElasticHosts driver for
    the London Bluesquare end-point
    """
    host = API_ENDPOINTS['uk-2']['host']

class ElasticHostsUK2NodeDriver(ElasticHostsBaseNodeDriver):
    """
    ElasticHosts node driver for the London Bluesquare end-point
    """
    connectionCls = ElasticHostsUK2Connection

class ElasticHostsUS1Connection(ElasticHostsBaseConnection):
    """
    Connection class for the ElasticHosts driver for
    the San Antonio Peer 1 end-point
    """
    host = API_ENDPOINTS['us-1']['host']

class ElasticHostsUS1NodeDriver(ElasticHostsBaseNodeDriver):
    """
    ElasticHosts node driver for the San Antonio Peer 1 end-point
    """
    connectionCls = ElasticHostsUS1Connection

########NEW FILE########
__FILENAME__ = gogrid
# Licensed to the Apache Software Foundation (ASF) under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""
GoGrid driver
"""
import time
import hashlib

try:
    import json
except ImportError:
    import simplejson as json

from libcloud.common.base import ConnectionUserAndKey, Response
from libcloud.common.types import InvalidCredsError, LibcloudError
from libcloud.common.types import MalformedResponseError
from libcloud.compute.providers import Provider
from libcloud.compute.types import NodeState
from libcloud.compute.base import Node, NodeDriver
from libcloud.compute.base import NodeSize, NodeImage, NodeLocation

HOST = 'api.gogrid.com'
PORTS_BY_SECURITY = { True: 443, False: 80 }
API_VERSION = '1.7'

STATE = {
    "Starting": NodeState.PENDING,
    "On": NodeState.RUNNING,
    "Off": NodeState.PENDING,
    "Restarting": NodeState.REBOOTING,
    "Saving": NodeState.PENDING,
    "Restoring": NodeState.PENDING,
}

GOGRID_INSTANCE_TYPES = {'512MB': {'id': '512MB',
                       'name': '512MB',
                       'ram': 512,
                       'disk': 30,
                       'bandwidth': None,
                       'price':0.095},
        '1GB': {'id': '1GB',
                       'name': '1GB',
                       'ram': 1024,
                       'disk': 60,
                       'bandwidth': None,
                       'price':0.19},
        '2GB': {'id': '2GB',
                       'name': '2GB',
                       'ram': 2048,
                       'disk': 120,
                       'bandwidth': None,
                       'price':0.38},
        '4GB': {'id': '4GB',
                       'name': '4GB',
                       'ram': 4096,
                       'disk': 240,
                       'bandwidth': None,
                       'price':0.76},
        '8GB': {'id': '8GB',
                       'name': '8GB',
                       'ram': 8192,
                       'disk': 480,
                       'bandwidth': None,
                       'price':1.52}}


class GoGridResponse(Response):

    def success(self):
        if self.status == 403:
            raise InvalidCredsError('Invalid credentials', GoGridNodeDriver)
        if self.status == 401:
            raise InvalidCredsError('API Key has insufficient rights', GoGridNodeDriver)
        if not self.body:
            return None
        try:
            return json.loads(self.body)['status'] == 'success'
        except ValueError:
            raise MalformedResponseError('Malformed reply', body=self.body, driver=GoGridNodeDriver)

    def parse_body(self):
        if not self.body:
            return None
        return json.loads(self.body)

    def parse_error(self):
        try:
            return json.loads(self.body)["list"][0]['message']
        except ValueError:
            return None

class GoGridConnection(ConnectionUserAndKey):
    """
    Connection class for the GoGrid driver
    """

    host = HOST
    responseCls = GoGridResponse

    def add_default_params(self, params):
        params["api_key"] = self.user_id
        params["v"] = API_VERSION
        params["format"] = 'json'
        params["sig"] = self.get_signature(self.user_id, self.key)

        return params

    def get_signature(self, key, secret):
        """ create sig from md5 of key + secret + time """
        m = hashlib.md5(key+secret+str(int(time.time())))
        return m.hexdigest()

class GoGridIpAddress(object):
    """
    IP Address
    """

    def __init__(self, id, ip, public, state, subnet):
        self.id = id
        self.ip = ip
        self.public = public
        self.state = state
        self.subnet = subnet

class GoGridNode(Node):
    # Generating uuid based on public ip to get around missing id on
    # create_node in gogrid api
    #
    # Used public ip since it is not mutable and specified at create time,
    # so uuid of node should not change after add is completed
    def get_uuid(self):
        return hashlib.sha1(
            "%s:%d" % (self.public_ip,self.driver.type)
        ).hexdigest()

class GoGridNodeDriver(NodeDriver):
    """
    GoGrid node driver
    """

    connectionCls = GoGridConnection
    type = Provider.GOGRID
    name = 'GoGrid'
    features = {"create_node": ["generates_password"]}

    _instance_types = GOGRID_INSTANCE_TYPES

    def _get_state(self, element):
        try:
            return STATE[element['state']['name']]
        except:
            pass
        return NodeState.UNKNOWN

    def _get_ip(self, element):
        return element.get('ip').get('ip')

    def _get_id(self, element):
        return element.get('id')

    def _to_node(self, element, password=None):
        state = self._get_state(element)
        ip = self._get_ip(element)
        id = self._get_id(element)
        n = GoGridNode(id=id,
                 name=element['name'],
                 state=state,
                 public_ip=[ip],
                 private_ip=[],
                 extra={'ram': element.get('ram').get('name'),
                     'isSandbox': element['isSandbox'] == 'true'},
                 driver=self.connection.driver)
        if password:
            n.extra['password'] = password

        return n

    def _to_image(self, element):
        n = NodeImage(id=element['id'],
                      name=element['friendlyName'],
                      driver=self.connection.driver)
        return n

    def _to_images(self, object):
        return [ self._to_image(el)
                 for el in object['list'] ]

    def _to_location(self, element):
        location = NodeLocation(id=element['id'],
                name=element['name'],
                country="US",
                driver=self.connection.driver)
        return location

    def _to_ip(self, element):
        ip = GoGridIpAddress(id=element['id'],
                ip=element['ip'],
                public=element['public'],
                subnet=element['subnet'],
                state=element["state"]["name"])
        ip.location = self._to_location(element['datacenter'])
        return ip

    def _to_ips(self, object):
        return [ self._to_ip(el)
                for el in object['list'] ]

    def _to_locations(self, object):
        return [self._to_location(el)
                for el in object['list']]

    def list_images(self, location=None):
        params = {}
        if location is not None:
            params["datacenter"] = location.id
        images = self._to_images(
                self.connection.request('/api/grid/image/list', params).object)
        return images

    def list_nodes(self):
        passwords_map = {}

        res = self._server_list()
        try:
          for password in self._password_list()['list']:
              try:
                  passwords_map[password['server']['id']] = password['password']
              except KeyError:
                  pass
        except InvalidCredsError:
          # some gogrid API keys don't have permission to access the password list.
          pass

        return [ self._to_node(el, passwords_map.get(el.get('id')))
                 for el
                 in res['list'] ]

    def reboot_node(self, node):
        id = node.id
        power = 'restart'
        res = self._server_power(id, power)
        if not res.success():
            raise Exception(res.parse_error())
        return True

    def destroy_node(self, node):
        id = node.id
        res = self._server_delete(id)
        if not res.success():
            raise Exception(res.parse_error())
        return True

    def _server_list(self):
        return self.connection.request('/api/grid/server/list').object

    def _password_list(self):
        return self.connection.request('/api/support/password/list').object

    def _server_power(self, id, power):
        # power in ['start', 'stop', 'restart']
        params = {'id': id, 'power': power}
        return self.connection.request("/api/grid/server/power", params,
                                         method='POST')

    def _server_delete(self, id):
        params = {'id': id}
        return self.connection.request("/api/grid/server/delete", params,
                                        method='POST')

    def _get_first_ip(self, location=None):
        ips = self.ex_list_ips(public=True, assigned=False, location=location)
        try:
            return ips[0].ip 
        except IndexError:
            raise LibcloudError('No public unassigned IPs left',
                    GoGridNodeDriver)

    def list_sizes(self, location=None):
        return [ NodeSize(driver=self.connection.driver, **i)
                    for i in self._instance_types.values() ]

    def list_locations(self):
        locations = self._to_locations(
            self.connection.request('/api/common/lookup/list',
                params={'lookup': 'ip.datacenter'}).object)
        return locations

    def ex_create_node_nowait(self, **kwargs):
        """Don't block until GoGrid allocates id for a node
        but return right away with id == None.

        The existance of this method is explained by the fact
        that GoGrid assigns id to a node only few minutes after
        creation."""
        name = kwargs['name']
        image = kwargs['image']
        size = kwargs['size']
        try:
            ip = kwargs['ex_ip']
        except KeyError:
            ip = self._get_first_ip(kwargs.get('location'))

        params = {'name': name,
                  'image': image.id,
                  'description': kwargs.get('ex_description', ''),
                  'isSandbox': str(kwargs.get('ex_issandbox', False)).lower(),
                  'server.ram': size.id,
                  'ip': ip}

        object = self.connection.request('/api/grid/server/add',
                                         params=params, method='POST').object
        node = self._to_node(object['list'][0])

        return node

    def create_node(self, **kwargs):
        """Create a new GoGird node

        See L{NodeDriver.create_node} for more keyword args.

        @keyword    ex_description: Description of a Node
        @type       ex_description: C{string}
        @keyword    ex_issandbox: Should server be sendbox?
        @type       ex_issandbox: C{bool}
        @keyword    ex_ip: Public IP address to use for a Node. If not
                    specified, first available IP address will be picked
        @type       ex_ip: C{string}
        """
        node = self.ex_create_node_nowait(**kwargs)

        timeout = 60 * 20
        waittime = 0
        interval = 2 * 60

        while node.id is None and waittime < timeout:
            nodes = self.list_nodes()

            for i in nodes:
                if i.public_ip[0] == node.public_ip[0] and i.id is not None:
                    return i

            waittime += interval
            time.sleep(interval)

        if id is None:
            raise Exception("Wasn't able to wait for id allocation for the node %s" % str(node))

        return node

    def ex_save_image(self, node, name):
        """Create an image for node.

        Please refer to GoGrid documentation to get info
        how prepare a node for image creation:

        http://wiki.gogrid.com/wiki/index.php/MyGSI

        @keyword    node: node to use as a base for image
        @type       node: L{Node}
        @keyword    name: name for new image
        @type       name: C{string}
        """
        params = {'server': node.id,
                  'friendlyName': name}
        object = self.connection.request('/api/grid/image/save', params=params,
                                         method='POST').object

        return self._to_images(object)[0]

    def ex_edit_node(self, **kwargs):
        """Change attributes of a node.

        @keyword    node: node to be edited
        @type       node: L{Node}
        @keyword    size: new size of a node
        @type       size: L{NodeSize}
        @keyword    ex_description: new description of a node
        @type       ex_description: C{string}
        """
        node = kwargs['node']
        size = kwargs['size']

        params = {'id': node.id,
                'server.ram': size.id}

        if 'ex_description' in kwargs:
            params['description'] = kwargs['ex_description']

        object = self.connection.request('/api/grid/server/edit',
                params=params).object

        return self._to_node(object['list'][0])

    def ex_edit_image(self, **kwargs):
        """Edit metadata of a server image.

        @keyword    image: image to be edited
        @type       image: L{NodeImage}
        @keyword    public: should be the image public?
        @type       public: C{bool}
        @keyword    ex_description: description of the image (optional)
        @type       ex_description: C{string}
        @keyword    name: name of the image
        @type       name C{string}

        """

        image = kwargs['image']
        public = kwargs['public']

        params = {'id': image.id,
                'isPublic': str(public).lower()}

        if 'ex_description' in kwargs:
            params['description'] = kwargs['ex_description']

        if 'name' in kwargs:
            params['friendlyName'] = kwargs['name']

        object = self.connection.request('/api/grid/image/edit',
                params=params).object

        return self._to_image(object['list'][0])

    def ex_list_ips(self, **kwargs):
        """Return list of IP addresses assigned to
        the account.

        @keyword    public: set to True to list only
                    public IPs or False to list only
                    private IPs. Set to None or not specify
                    at all not to filter by type
        @type       public: C{bool}
        @keyword    assigned: set to True to list only addresses
                    assigned to servers, False to list unassigned
                    addresses and set to None or don't set at all
                    not no filter by state
        @type       assigned: C{bool}
        @keyword    location: filter IP addresses by location
        @type       location: L{NodeLocation}
        @return:    C{list} of L{GoGridIpAddress}es
        """

        params = {}

        if "public" in kwargs and kwargs["public"] is not None:
            params["ip.type"] = {True: "Public",
                    False: "Private"}[kwargs["public"]]
        if "assigned" in kwargs and kwargs["assigned"] is not None:
            params["ip.state"] = {True: "Assigned",
                    False: "Unassigned"}[kwargs["assigned"]]
        if "location" in kwargs and kwargs['location'] is not None:
            params['datacenter'] = kwargs['location'].id

        ips = self._to_ips(
                self.connection.request('/api/grid/ip/list',
                    params=params).object)
        return ips

########NEW FILE########
__FILENAME__ = ibm_sbc
# Licensed to the Apache Software Foundation (ASF) under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""
Driver for the IBM Developer Cloud.
"""
import base64, urllib

from libcloud.common.base import Response, ConnectionUserAndKey
from libcloud.common.types import InvalidCredsError
from libcloud.compute.types import NodeState, Provider
from libcloud.compute.base import NodeDriver, Node, NodeImage, NodeSize, NodeLocation, NodeAuthSSHKey

from xml.etree import ElementTree as ET

HOST = 'www-147.ibm.com'
REST_BASE = '/computecloud/enterprise/api/rest/20100331'

class IBMResponse(Response):
    def success(self):
        return int(self.status) == 200

    def parse_body(self):
        if not self.body:
            return None
        return ET.XML(self.body)

    def parse_error(self):
        if int(self.status) == 401:
            if not self.body:
                raise InvalidCredsError(str(self.status) + ': ' + self.error)
            else:
                raise InvalidCredsError(self.body)
        return self.body

class IBMConnection(ConnectionUserAndKey):
    """
    Connection class for the IBM Developer Cloud driver
    """

    host = HOST
    responseCls = IBMResponse

    def add_default_headers(self, headers):
        headers['Accept'] = 'text/xml'
        headers['Authorization'] = ('Basic %s' % (base64.b64encode('%s:%s' % (self.user_id, self.key))))
        if not 'Content-Type' in headers:
            headers['Content-Type'] = 'text/xml'
        return headers

    def encode_data(self, data):
        return urllib.urlencode(data)

class IBMNodeDriver(NodeDriver):
    """
    IBM Developer Cloud node driver.
    """
    connectionCls = IBMConnection
    type = Provider.IBM
    name = "IBM Developer Cloud"

    NODE_STATE_MAP = { 0: NodeState.PENDING,    # New
                       1: NodeState.PENDING,    # Provisioning
                       2: NodeState.TERMINATED, # Failed
                       3: NodeState.TERMINATED, # Removed
                       4: NodeState.TERMINATED, # Rejected
                       5: NodeState.RUNNING,    # Active
                       6: NodeState.UNKNOWN,    # Unknown
                       7: NodeState.PENDING,    # Deprovisioning
                       8: NodeState.REBOOTING,  # Restarting
                       9: NodeState.PENDING,    # Starting
                       10: NodeState.PENDING,   # Stopping
                       11: NodeState.TERMINATED,# Stopped
                       12: NodeState.PENDING,   # Deprovision Pending
                       13: NodeState.PENDING,   # Restart Pending
                       14: NodeState.PENDING,   # Attaching
                       15: NodeState.PENDING }  # Detaching

    def create_node(self, **kwargs):
        """
        Creates a node in the IBM Developer Cloud.

        See L{NodeDriver.create_node} for more keyword args.

        @keyword    ex_configurationData: Image-specific configuration parameters.
                                       Configuration parameters are defined in
                                       the parameters.xml file.  The URL to
                                       this file is defined in the NodeImage
                                       at extra[parametersURL].
        @type       ex_configurationData: C{dict}
        """

        # Compose headers for message body
        data = {}
        data.update({'name': kwargs['name']})
        data.update({'imageID': kwargs['image'].id})
        data.update({'instanceType': kwargs['size'].id})
        if 'location' in kwargs:
            data.update({'location': kwargs['location'].id})
        else:
            data.update({'location': '1'})
        if 'auth' in kwargs and isinstance(kwargs['auth'], NodeAuthSSHKey):
            data.update({'publicKey': kwargs['auth'].pubkey})
        if 'ex_configurationData' in kwargs:
            configurationData = kwargs['ex_configurationData']
            for key in configurationData.keys():
                data.update({key: configurationData.get(key)})

        # Send request!
        resp = self.connection.request(action = REST_BASE + '/instances',
                                       headers = {'Content-Type': 'application/x-www-form-urlencoded'},
                                       method = 'POST',
                                       data = data).object
        return self._to_nodes(resp)[0]

    def destroy_node(self, node):
        url = REST_BASE + '/instances/%s' % (node.id)
        status = int(self.connection.request(action = url, method='DELETE').status)
        return status == 200

    def reboot_node(self, node):
        url = REST_BASE + '/instances/%s' % (node.id)
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        data = {'state': 'restart'}

        resp = self.connection.request(action = url,
                                       method = 'PUT',
                                       headers = headers,
                                       data = data)
        return int(resp.status) == 200

    def list_nodes(self):
        return self._to_nodes(self.connection.request(REST_BASE + '/instances').object)

    def list_images(self, location = None):
        return self._to_images(self.connection.request(REST_BASE + '/offerings/image').object)

    def list_sizes(self, location = None):        
        return [ NodeSize('BRZ32.1/2048/60*175', 'Bronze 32 bit', None, None, None, None, self.connection.driver),
                 NodeSize('BRZ64.2/4096/60*500*350', 'Bronze 64 bit', None, None, None, None, self.connection.driver),
                 NodeSize('COP32.1/2048/60', 'Copper 32 bit', None, None, None, None, self.connection.driver),
                 NodeSize('COP64.2/4096/60', 'Copper 64 bit', None, None, None, None, self.connection.driver),
                 NodeSize('SLV32.2/4096/60*350', 'Silver 32 bit', None, None, None, None, self.connection.driver),
                 NodeSize('SLV64.4/8192/60*500*500', 'Silver 64 bit', None, None, None, None, self.connection.driver),
                 NodeSize('GLD32.4/4096/60*350', 'Gold 32 bit', None, None, None, None, self.connection.driver),
                 NodeSize('GLD64.8/16384/60*500*500', 'Gold 64 bit', None, None, None, None, self.connection.driver),
                 NodeSize('PLT64.16/16384/60*500*500*500*500', 'Platinum 64 bit', None, None, None, None, self.connection.driver) ]

    def list_locations(self):
        return self._to_locations(self.connection.request(REST_BASE + '/locations').object)

    def _to_nodes(self, object):
        return [ self._to_node(instance) for instance in object.findall('Instance') ]

    def _to_node(self, instance):
        return Node(id = instance.findtext('ID'),
                    name = instance.findtext('Name'),
                    state = self.NODE_STATE_MAP[int(instance.findtext('Status'))],
                    public_ip = instance.findtext('IP'),
                    private_ip = None,
                    driver = self.connection.driver)

    def _to_images(self, object):
        return [ self._to_image(image) for image in object.findall('Image') ]

    def _to_image(self, image):
        return NodeImage(id = image.findtext('ID'),
                         name = image.findtext('Name'),
                         driver = self.connection.driver,
                         extra = {'parametersURL': image.findtext('Manifest')})

    def _to_locations(self, object):
        return [ self._to_location(location) for location in object.findall('Location') ]

    def _to_location(self, location):
        # NOTE: country currently hardcoded
        return NodeLocation(id = location.findtext('ID'),
                            name = location.findtext('Name'),
                            country = 'US',
                            driver = self.connection.driver)

########NEW FILE########
__FILENAME__ = linode
# Licensed to the Apache Software Foundation (ASF) under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""libcloud driver for the Linode(R) API

This driver implements all libcloud functionality for the Linode API.  Since the
API is a bit more fine-grained, create_node abstracts a significant amount of
work (and may take a while to run).

Linode home page                    http://www.linode.com/
Linode API documentation            http://www.linode.com/api/
Alternate bindings for reference    http://github.com/tjfontaine/linode-python

Linode(R) is a registered trademark of Linode, LLC.

"""
import itertools
import os

from copy import copy

try:
    import json
except:
    import simplejson as json

from libcloud.common.base import ConnectionKey, Response
from libcloud.common.types import InvalidCredsError, MalformedResponseError
from libcloud.compute.types import Provider, NodeState
from libcloud.compute.base import NodeDriver, NodeSize, Node, NodeLocation
from libcloud.compute.base import NodeAuthPassword, NodeAuthSSHKey
from libcloud.compute.base import NodeImage

# Where requests go - in beta situations, this information may change.
LINODE_API = "api.linode.com"
LINODE_ROOT = "/"

# Map of TOTALRAM to PLANID, allows us to figure out what plan
# a particular node is on (updated with new plan sizes 6/28/10)
LINODE_PLAN_IDS = {512:'1',
                   768:'2',
                  1024:'3',
                  1536:'4',
                  2048:'5',
                  4096:'6',
                  8192:'7',
                 12288:'8',
                 16384:'9',
                 20480:'10'}


class LinodeException(Exception):
    """Error originating from the Linode API

    This class wraps a Linode API error, a list of which is available in the
    API documentation.  All Linode API errors are a numeric code and a
    human-readable description.
    """
    def __str__(self):
        return "(%u) %s" % (self.args[0], self.args[1])
    def __repr__(self):
        return "<LinodeException code %u '%s'>" % (self.args[0], self.args[1])


class LinodeResponse(Response):
    """Linode API response

    Wraps the HTTP response returned by the Linode API, which should be JSON in
    this structure:

       {
         "ERRORARRAY": [ ... ],
         "DATA": [ ... ],
         "ACTION": " ... "
       }

    libcloud does not take advantage of batching, so a response will always
    reflect the above format.  A few weird quirks are caught here as well."""
    def __init__(self, response):
        """Instantiate a LinodeResponse from the HTTP response

        @keyword response: The raw response returned by urllib
        @return: parsed L{LinodeResponse}"""
        self.body = response.read()
        self.status = response.status
        self.headers = dict(response.getheaders())
        self.error = response.reason
        self.invalid = LinodeException(0xFF,
                                       "Invalid JSON received from server")

        # Move parse_body() to here;  we can't be sure of failure until we've
        # parsed the body into JSON.
        self.objects, self.errors = self.parse_body()
        if not self.success():
            # Raise the first error, as there will usually only be one
            raise self.errors[0]

    def parse_body(self):
        """Parse the body of the response into JSON objects

        If the response chokes the parser, action and data will be returned as
        None and errorarray will indicate an invalid JSON exception.

        @return: C{list} of objects and C{list} of errors"""
        try:
            js = json.loads(self.body)
        except:
            raise MalformedResponseError("Failed to parse JSON", body=self.body,
                driver=LinodeNodeDriver)

        try:
            if isinstance(js, dict):
                # solitary response - promote to list
                js = [js]
            ret = []
            errs = []
            for obj in js:
                if ("DATA" not in obj or "ERRORARRAY" not in obj
                    or "ACTION" not in obj):
                    ret.append(None)
                    errs.append(self.invalid)
                    continue
                ret.append(obj["DATA"])
                errs.extend(self._make_excp(e) for e in obj["ERRORARRAY"])
            return (ret, errs)
        except:
            return (None, [self.invalid])

    def success(self):
        """Check the response for success

        The way we determine success is by the presence of an error in
        ERRORARRAY.  If one is there, we assume the whole request failed.

        @return: C{bool} indicating a successful request"""
        return len(self.errors) == 0

    def _make_excp(self, error):
        """Convert an API error to a LinodeException instance

        @keyword error: JSON object containing C{ERRORCODE} and C{ERRORMESSAGE}
        @type error: dict"""
        if "ERRORCODE" not in error or "ERRORMESSAGE" not in error:
            return None
        if error["ERRORCODE"] == 4:
            return InvalidCredsError(error["ERRORMESSAGE"])
        return LinodeException(error["ERRORCODE"], error["ERRORMESSAGE"])


class LinodeConnection(ConnectionKey):
    """A connection to the Linode API

    Wraps SSL connections to the Linode API, automagically injecting the
    parameters that the API needs for each request."""
    host = LINODE_API
    responseCls = LinodeResponse

    def add_default_params(self, params):
        """Add parameters that are necessary for every request

        This method adds C{api_key} and C{api_responseFormat} to the request."""
        params["api_key"] = self.key
        # Be explicit about this in case the default changes.
        params["api_responseFormat"] = "json"
        return params


class LinodeNodeDriver(NodeDriver):
    """libcloud driver for the Linode API

    Rough mapping of which is which:

        list_nodes              linode.list
        reboot_node             linode.reboot
        destroy_node            linode.delete
        create_node             linode.create, linode.update,
                                linode.disk.createfromdistribution,
                                linode.disk.create, linode.config.create,
                                linode.ip.addprivate, linode.boot
        list_sizes              avail.linodeplans
        list_images             avail.distributions
        list_locations          avail.datacenters

    For more information on the Linode API, be sure to read the reference:

        http://www.linode.com/api/
    """
    type = Provider.LINODE
    name = "Linode"
    connectionCls = LinodeConnection
    _linode_plan_ids = LINODE_PLAN_IDS

    def __init__(self, key):
        """Instantiate the driver with the given API key

        @keyword key: the API key to use
        @type key: C{str}"""
        self.datacenter = None
        NodeDriver.__init__(self, key)

    # Converts Linode's state from DB to a NodeState constant.
    LINODE_STATES = {
        -2: NodeState.UNKNOWN,              # Boot Failed
        -1: NodeState.PENDING,              # Being Created
         0: NodeState.PENDING,              # Brand New
         1: NodeState.RUNNING,              # Running
         2: NodeState.TERMINATED,           # Powered Off
         3: NodeState.REBOOTING,            # Shutting Down
         4: NodeState.UNKNOWN               # Reserved
    }

    def list_nodes(self):
        """List all Linodes that the API key can access

        This call will return all Linodes that the API key in use has access to.
        If a node is in this list, rebooting will work; however, creation and
        destruction are a separate grant.

        @return: C{list} of L{Node} objects that the API key can access"""
        params = { "api_action": "linode.list" }
        data = self.connection.request(LINODE_ROOT, params=params).objects[0]
        return self._to_nodes(data)

    def reboot_node(self, node):
        """Reboot the given Linode

        Will issue a shutdown job followed by a boot job, using the last booted
        configuration.  In most cases, this will be the only configuration.

        @keyword node: the Linode to reboot
        @type node: L{Node}"""
        params = { "api_action": "linode.reboot", "LinodeID": node.id }
        self.connection.request(LINODE_ROOT, params=params)
        return True

    def destroy_node(self, node):
        """Destroy the given Linode

        Will remove the Linode from the account and issue a prorated credit. A
        grant for removing Linodes from the account is required, otherwise this
        method will fail.

        In most cases, all disk images must be removed from a Linode before the
        Linode can be removed; however, this call explicitly skips those
        safeguards.  There is no going back from this method.

        @keyword node: the Linode to destroy
        @type node: L{Node}"""
        params = { "api_action": "linode.delete", "LinodeID": node.id,
            "skipChecks": True }
        self.connection.request(LINODE_ROOT, params=params)
        return True

    def create_node(self, **kwargs):
        """Create a new Linode, deploy a Linux distribution, and boot

        This call abstracts much of the functionality of provisioning a Linode
        and getting it booted.  A global grant to add Linodes to the account is
        required, as this call will result in a billing charge.

        Note that there is a safety valve of 5 Linodes per hour, in order to
        prevent a runaway script from ruining your day.

        @keyword name: the name to assign the Linode (mandatory)
        @type name: C{str}

        @keyword image: which distribution to deploy on the Linode (mandatory)
        @type image: L{NodeImage}

        @keyword size: the plan size to create (mandatory)
        @type size: L{NodeSize}

        @keyword auth: an SSH key or root password (mandatory)
        @type auth: L{NodeAuthSSHKey} or L{NodeAuthPassword}

        @keyword location: which datacenter to create the Linode in
        @type location: L{NodeLocation}

        @keyword ex_swap: size of the swap partition in MB (128)
        @type ex_swap: C{int}

        @keyword ex_rsize: size of the root partition in MB (plan size - swap).
        @type ex_rsize: C{int}

        @keyword ex_kernel: a kernel ID from avail.kernels (Latest 2.6 Stable).
        @type ex_kernel: C{str}

        @keyword ex_payment: one of 1, 12, or 24; subscription length (1)
        @type ex_payment: C{int}

        @keyword ex_comment: a small comment for the configuration (libcloud)
        @type ex_comment: C{str}

        @keyword ex_private: whether or not to request a private IP (False)
        @type ex_private: C{bool}

        @keyword lconfig: what to call the configuration (generated)
        @type lconfig: C{str}

        @keyword lroot: what to call the root image (generated)
        @type lroot: C{str}

        @keyword lswap: what to call the swap space (generated)
        @type lswap: C{str}

        @return: a L{Node} representing the newly-created Linode
        """
        name = kwargs["name"]
        image = kwargs["image"]
        size = kwargs["size"]
        auth = kwargs["auth"]

        # Pick a location (resolves LIBCLOUD-41 in JIRA)
        if "location" in kwargs:
            chosen = kwargs["location"].id
        elif self.datacenter:
            chosen = self.datacenter
        else:
            raise LinodeException(0xFB, "Need to select a datacenter first")

        # Step 0: Parameter validation before we purchase
        # We're especially careful here so we don't fail after purchase, rather
        # than getting halfway through the process and having the API fail.

        # Plan ID
        plans = self.list_sizes()
        if size.id not in [p.id for p in plans]:
            raise LinodeException(0xFB, "Invalid plan ID -- avail.plans")

        # Payment schedule
        payment = "1" if "ex_payment" not in kwargs else str(kwargs["ex_payment"])
        if payment not in ["1", "12", "24"]:
            raise LinodeException(0xFB, "Invalid subscription (1, 12, 24)")

        ssh = None
        root = None
        # SSH key and/or root password
        if isinstance(auth, NodeAuthSSHKey):
            ssh = auth.pubkey
        elif isinstance(auth, NodeAuthPassword):
            root = auth.password

        if not ssh and not root:
            raise LinodeException(0xFB, "Need SSH key or root password")
        if not root is None and len(root) < 6:
            raise LinodeException(0xFB, "Root password is too short")

        # Swap size
        try: swap = 128 if "ex_swap" not in kwargs else int(kwargs["ex_swap"])
        except: raise LinodeException(0xFB, "Need an integer swap size")

        # Root partition size
        imagesize = (size.disk - swap) if "ex_rsize" not in kwargs else \
            int(kwargs["ex_rsize"])
        if (imagesize + swap) > size.disk:
            raise LinodeException(0xFB, "Total disk images are too big")

        # Distribution ID
        distros = self.list_images()
        if image.id not in [d.id for d in distros]:
            raise LinodeException(0xFB,
                                  "Invalid distro -- avail.distributions")

        # Kernel
        if "ex_kernel" in kwargs:
            kernel = kwargs["ex_kernel"]
        else:
            if image.extra['64bit']:
                kernel = 111 if image.extra['pvops'] else 107
            else:
                kernel = 110 if image.extra['pvops'] else 60
        params = { "api_action": "avail.kernels" }
        kernels = self.connection.request(LINODE_ROOT, params=params).objects[0]
        if kernel not in [z["KERNELID"] for z in kernels]:
            raise LinodeException(0xFB, "Invalid kernel -- avail.kernels")

        # Comments
        comments = "Created by Apache libcloud <http://www.libcloud.org>" if \
            "ex_comment" not in kwargs else kwargs["ex_comment"]

        # Labels
        label = {
            "lconfig": "[%s] Configuration Profile" % name,
            "lroot": "[%s] %s Disk Image" % (name, image.name),
            "lswap": "[%s] Swap Space" % name
        }
        for what in ["lconfig", "lroot", "lswap"]:
            if what in kwargs:
                label[what] = kwargs[what]

        # Step 1: linode.create
        params = {
            "api_action":   "linode.create",
            "DatacenterID": chosen,
            "PlanID":       size.id,
            "PaymentTerm":  payment
        }
        data = self.connection.request(LINODE_ROOT, params=params).objects[0]
        linode = { "id": data["LinodeID"] }

        # Step 1b. linode.update to rename the Linode
        params = {
            "api_action": "linode.update",
            "LinodeID": linode["id"],
            "Label": name
        }
        self.connection.request(LINODE_ROOT, params=params)

        # Step 1c. linode.ip.addprivate if it was requested
        if "ex_private" in kwargs and kwargs["ex_private"]:
            params = {
                "api_action":   "linode.ip.addprivate",
                "LinodeID":     linode["id"]
            }
            self.connection.request(LINODE_ROOT, params=params)

        # Step 2: linode.disk.createfromdistribution
        if not root:
            root = os.urandom(8).encode('hex')
        params = {
            "api_action":       "linode.disk.createfromdistribution",
            "LinodeID":         linode["id"],
            "DistributionID":   image.id,
            "Label":            label["lroot"],
            "Size":             imagesize,
            "rootPass":         root,
        }
        if ssh: params["rootSSHKey"] = ssh
        data = self.connection.request(LINODE_ROOT, params=params).objects[0]
        linode["rootimage"] = data["DiskID"]

        # Step 3: linode.disk.create for swap
        params = {
            "api_action":       "linode.disk.create",
            "LinodeID":         linode["id"],
            "Label":            label["lswap"],
            "Type":             "swap",
            "Size":             swap
        }
        data = self.connection.request(LINODE_ROOT, params=params).objects[0]
        linode["swapimage"] = data["DiskID"]

        # Step 4: linode.config.create for main profile
        disks = "%s,%s,,,,,,," % (linode["rootimage"], linode["swapimage"])
        params = {
            "api_action":       "linode.config.create",
            "LinodeID":         linode["id"],
            "KernelID":         kernel,
            "Label":            label["lconfig"],
            "Comments":         comments,
            "DiskList":         disks
        }
        data = self.connection.request(LINODE_ROOT, params=params).objects[0]
        linode["config"] = data["ConfigID"]

        # Step 5: linode.boot
        params = {
            "api_action":       "linode.boot",
            "LinodeID":         linode["id"],
            "ConfigID":         linode["config"]
        }
        self.connection.request(LINODE_ROOT, params=params)

        # Make a node out of it and hand it back
        params = { "api_action": "linode.list", "LinodeID": linode["id"] }
        data = self.connection.request(LINODE_ROOT, params=params).objects[0]
        return self._to_nodes(data)

    def list_sizes(self, location=None):
        """List available Linode plans

        Gets the sizes that can be used for creating a Linode.  Since available
        Linode plans vary per-location, this method can also be passed a
        location to filter the availability.

        @keyword location: the facility to retrieve plans in
        @type location: NodeLocation

        @return: a C{list} of L{NodeSize}s"""
        params = { "api_action": "avail.linodeplans" }
        data = self.connection.request(LINODE_ROOT, params=params).objects[0]
        sizes = []
        for obj in data:
            n = NodeSize(id=obj["PLANID"], name=obj["LABEL"], ram=obj["RAM"],
                    disk=(obj["DISK"] * 1024), bandwidth=obj["XFER"],
                    price=obj["PRICE"], driver=self.connection.driver)
            sizes.append(n)
        return sizes

    def list_images(self):
        """List available Linux distributions

        Retrieve all Linux distributions that can be deployed to a Linode.

        @return: a C{list} of L{NodeImage}s"""
        params = { "api_action": "avail.distributions" }
        data = self.connection.request(LINODE_ROOT, params=params).objects[0]
        distros = []
        for obj in data:
            i = NodeImage(id=obj["DISTRIBUTIONID"],
                          name=obj["LABEL"],
                          driver=self.connection.driver,
                          extra={'pvops': obj['REQUIRESPVOPSKERNEL'],
                                 '64bit': obj['IS64BIT']})
            distros.append(i)
        return distros

    def list_locations(self):
        """List available facilities for deployment

        Retrieve all facilities that a Linode can be deployed in.

        @return: a C{list} of L{NodeLocation}s"""
        params = { "api_action": "avail.datacenters" }
        data = self.connection.request(LINODE_ROOT, params=params).objects[0]
        nl = []
        for dc in data:
            country = None
            if "USA" in dc["LOCATION"]: country = "US"
            elif "UK" in dc["LOCATION"]: country = "GB"
            else: country = "??"
            nl.append(NodeLocation(dc["DATACENTERID"],
                                   dc["LOCATION"],
                                   country,
                                   self))
        return nl

    def linode_set_datacenter(self, dc):
        """Set the default datacenter for Linode creation

        Since Linodes must be created in a facility, this function sets the
        default that L{create_node} will use.  If a C{location} keyword is not
        passed to L{create_node}, this method must have already been used.

        @keyword dc: the datacenter to create Linodes in unless specified
        @type dc: L{NodeLocation}"""
        did = dc.id
        params = { "api_action": "avail.datacenters" }
        data = self.connection.request(LINODE_ROOT, params=params).objects[0]
        for datacenter in data:
            if did == dc["DATACENTERID"]:
                self.datacenter = did
                return

        dcs = ", ".join([d["DATACENTERID"] for d in data])
        self.datacenter = None
        raise LinodeException(0xFD, "Invalid datacenter (use one of %s)" % dcs)

    def _to_nodes(self, objs):
        """Convert returned JSON Linodes into Node instances

        @keyword objs: C{list} of JSON dictionaries representing the Linodes
        @type objs: C{list}
        @return: C{list} of L{Node}s"""

        # Get the IP addresses for the Linodes
        nodes = {}
        batch = []
        for o in objs:
            lid = o["LINODEID"]
            nodes[lid] = n = Node(id=lid, name=o["LABEL"], public_ip=[],
                private_ip=[], state=self.LINODE_STATES[o["STATUS"]],
                driver=self.connection.driver)
            n.extra = copy(o)
            n.extra["PLANID"] = self._linode_plan_ids.get(o.get("TOTALRAM"))
            batch.append({"api_action": "linode.ip.list", "LinodeID": lid})

        # Avoid batch limitation
        ip_answers = []
        args = [iter(batch)] * 25
        izip_longest = getattr(itertools, 'izip_longest', _izip_longest)
        for twenty_five in izip_longest(*args):
            twenty_five = [q for q in twenty_five if q]
            params = { "api_action": "batch",
                "api_requestArray": json.dumps(twenty_five) }
            req = self.connection.request(LINODE_ROOT, params=params)
            if not req.success() or len(req.objects) == 0:
                return None
            ip_answers.extend(req.objects)

        # Add the returned IPs to the nodes and return them
        for ip_list in ip_answers:
            for ip in ip_list:
                lid = ip["LINODEID"]
                which = nodes[lid].public_ip if ip["ISPUBLIC"] == 1 else \
                    nodes[lid].private_ip
                which.append(ip["IPADDRESS"])
        return nodes.values()

    features = {"create_node": ["ssh_key", "password"]}

def _izip_longest(*args, **kwds):
    """Taken from Python docs

    http://docs.python.org/library/itertools.html#itertools.izip
    """
    fillvalue = kwds.get('fillvalue')
    def sentinel(counter = ([fillvalue]*(len(args)-1)).pop):
        yield counter() # yields the fillvalue, or raises IndexError
    fillers = itertools.repeat(fillvalue)
    iters = [itertools.chain(it, sentinel(), fillers) for it in args]
    try:
        for tup in itertools.izip(*iters):
            yield tup
    except IndexError:
        pass

########NEW FILE########
__FILENAME__ = opennebula
# Copyright 2002-2009, Distributed Systems Architecture Group, Universidad
# Complutense de Madrid (dsa-research.org)
#
# Licensed to the Apache Software Foundation (ASF) under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""
OpenNebula driver
"""

from base64 import b64encode
import hashlib
from xml.etree import ElementTree as ET

from libcloud.common.base import ConnectionUserAndKey, Response
from libcloud.common.types import InvalidCredsError
from libcloud.compute.providers import Provider
from libcloud.compute.types import NodeState
from libcloud.compute.base import NodeDriver, Node, NodeLocation
from libcloud.compute.base import NodeImage, NodeSize

API_HOST = ''
API_PORT = (4567, 443)
API_SECURE = True


class OpenNebulaResponse(Response):

    def success(self):
        i = int(self.status)
        return i >= 200 and i <= 299

    def parse_body(self):
        if not self.body:
            return None
        return ET.XML(self.body)

    def parse_error(self):
        if int(self.status) == 401:
            raise InvalidCredsError(self.body)
        return self.body


class OpenNebulaConnection(ConnectionUserAndKey):
    """
    Connection class for the OpenNebula driver
    """

    host = API_HOST
    port = API_PORT
    secure = API_SECURE
    responseCls = OpenNebulaResponse

    def add_default_headers(self, headers):
        pass_sha1 = hashlib.sha1(self.key).hexdigest()
        headers['Authorization'] = ("Basic %s" % b64encode("%s:%s" % (self.user_id, pass_sha1)))
        return headers


class OpenNebulaNodeDriver(NodeDriver):
    """
    OpenNebula node driver
    """

    connectionCls = OpenNebulaConnection
    type = Provider.OPENNEBULA
    name = 'OpenNebula'

    NODE_STATE_MAP = {
        'PENDING': NodeState.PENDING,
        'ACTIVE': NodeState.RUNNING,
        'DONE': NodeState.TERMINATED,
        'STOPPED': NodeState.TERMINATED
    }

    def list_sizes(self, location=None):
        return [
          NodeSize(id=1,
                   name="small",
                   ram=None,
                   disk=None,
                   bandwidth=None,
                   price=None,
                   driver=self),
          NodeSize(id=2,
                   name="medium",
                   ram=None,
                   disk=None,
                   bandwidth=None,
                   price=None,
                   driver=self),
          NodeSize(id=3,
                   name="large",
                   ram=None,
                   disk=None,
                   bandwidth=None,
                   price=None,
                   driver=self),
        ]

    def list_nodes(self):
        return self._to_nodes(self.connection.request('/compute').object)

    def list_images(self, location=None):
        return self._to_images(self.connection.request('/storage').object)

    def list_locations(self):
        return [NodeLocation(0,  'OpenNebula', 'ONE', self)]

    def reboot_node(self, node):
        compute_id = str(node.id)

        url = '/compute/%s' % compute_id
        resp1 = self.connection.request(url,method='PUT',data=self._xml_action(compute_id,'STOPPED'))

        if resp1.status == 400:
            return False

        resp2 = self.connection.request(url,method='PUT',data=self._xml_action(compute_id,'RESUME'))

        if resp2.status == 400:
            return False

        return True

    def destroy_node(self, node):
        url = '/compute/%s' % (str(node.id))
        resp = self.connection.request(url,method='DELETE')

        return resp.status == 204

    def create_node(self, **kwargs):
        """Create a new OpenNebula node

        See L{NodeDriver.create_node} for more keyword args.
        """
        compute = ET.Element('COMPUTE')

        name = ET.SubElement(compute, 'NAME')
        name.text = kwargs['name']

        # """
        # Other extractable (but unused) information
        # """
        # instance_type = ET.SubElement(compute, 'INSTANCE_TYPE')
        # instance_type.text = kwargs['size'].name
        #
        # storage = ET.SubElement(compute, 'STORAGE')
        # disk = ET.SubElement(storage, 'DISK', {'image': str(kwargs['image'].id),
        #                                        'dev': 'sda1'})

        xml = ET.tostring(compute)

        node = self.connection.request('/compute',method='POST',data=xml).object

        return self._to_node(node)

    def _to_images(self, object):
        images = []
        for element in object.findall("DISK"):
            image_id = element.attrib["href"].partition("/storage/")[2]
            image = self.connection.request(("/storage/%s" % (image_id))).object
            images.append(self._to_image(image))

        return images

    def _to_image(self, image):
        return NodeImage(id=image.findtext("ID"),
                         name=image.findtext("NAME"),
                         driver=self.connection.driver)

    def _to_nodes(self, object):
        computes = []
        for element in object.findall("COMPUTE"):
            compute_id = element.attrib["href"].partition("/compute/")[2]
            compute = self.connection.request(("/compute/%s" % (compute_id))).object
            computes.append(self._to_node(compute))

        return computes

    def _to_node(self, compute):
        try:
            state = self.NODE_STATE_MAP[compute.findtext("STATE")]
        except KeyError:
            state = NodeState.UNKNOWN

        networks = []
        for element in compute.findall("NIC"):
            networks.append(element.attrib["ip"])

        return Node(id=compute.findtext("ID"),
                    name=compute.findtext("NAME"),
                    state=state,
                    public_ip=networks,
                    private_ip=[],
                    driver=self.connection.driver)

    def _xml_action(self, compute_id, action):
        compute = ET.Element('COMPUTE')

        compute_id = ET.SubElement(compute, 'ID')
        compute_id.text = str(compute_id)

        state = ET.SubElement(compute, 'STATE')
        state.text = action

        xml = ET.tostring(compute)
        return xml

########NEW FILE########
__FILENAME__ = rackspace
# Licensed to the Apache Software Foundation (ASF) under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""
Rackspace driver
"""
import os

import base64
import urlparse

from xml.etree import ElementTree as ET
from xml.parsers.expat import ExpatError

from libcloud.common.base import Response
from libcloud.common.types import InvalidCredsError, MalformedResponseError
from libcloud.compute.types import NodeState, Provider
from libcloud.compute.base import NodeDriver, Node
from libcloud.compute.base import NodeSize, NodeImage, NodeLocation

from libcloud.common.rackspace import AUTH_HOST_US, AUTH_HOST_UK, RackspaceBaseConnection

NAMESPACE='http://docs.rackspacecloud.com/servers/api/v1.0'

#
# Prices need to be hardcoded as Rackspace doesn't expose them through
# the API. Prices are associated with flavors, of which there are 7.
# See - http://www.rackspacecloud.com/cloud_hosting_products/servers/pricing
#
RACKSPACE_PRICES = {
    '1':'.015',
    '2':'.030',
    '3':'.060',
    '4':'.120',
    '5':'.240',
    '6':'.480',
    '7':'.960',
}

class RackspaceResponse(Response):

    def success(self):
        i = int(self.status)
        return i >= 200 and i <= 299

    def parse_body(self):
        if not self.body:
            return None
        try:
            body = ET.XML(self.body)
        except:
            raise MalformedResponseError("Failed to parse XML", body=self.body, driver=RackspaceNodeDriver)
        return body
    def parse_error(self):
        # TODO: fixup, Rackspace only uses response codes really!
        try:
            body = ET.XML(self.body)
        except:
            raise MalformedResponseError("Failed to parse XML", body=self.body, driver=RackspaceNodeDriver)
        try:
            text = "; ".join([ err.text or ''
                               for err in
                               body.getiterator()
                               if err.text])
        except ExpatError:
            text = self.body
        return '%s %s %s' % (self.status, self.error, text)


class RackspaceConnection(RackspaceBaseConnection):
    """
    Connection class for the Rackspace driver
    """

    responseCls = RackspaceResponse
    auth_host = AUTH_HOST_US
    _url_key = "server_url"

    def __init__(self, user_id, key, secure=True):
        super(RackspaceConnection, self).__init__(user_id, key, secure)
        self.api_version = 'v1.0'
        self.accept_format = 'application/xml'

    def request(self, action, params=None, data='', headers=None, method='GET'):
        if not headers:
            headers = {}
        if not params:
            params = {}
        # Due to first-run authentication request, we may not have a path
        if self.server_url:
            action = self.server_url + action
        if method in ("POST", "PUT"):
            headers = {'Content-Type': 'application/xml; charset=UTF-8'}
        if method == "GET":
            params['cache-busting'] = os.urandom(8).encode('hex')
        return super(RackspaceConnection, self).request(
            action=action,
            params=params, data=data,
            method=method, headers=headers
        )


class RackspaceSharedIpGroup(object):
    """
    Shared IP group info.
    """

    def __init__(self, id, name, servers=None):
        self.id = str(id)
        self.name = name
        self.servers = servers


class RackspaceNodeIpAddresses(object):
    """
    List of public and private IP addresses of a Node.
    """

    def __init__(self, public_addresses, private_addresses):
        self.public_addresses = public_addresses
        self.private_addresses = private_addresses


class RackspaceNodeDriver(NodeDriver):
    """
    Rackspace node driver.

    Extra node attributes:
        - password: root password, available after create.
        - hostId: represents the host your cloud server runs on
        - imageId: id of image
        - flavorId: id of flavor
    """
    connectionCls = RackspaceConnection
    type = Provider.RACKSPACE
    name = 'Rackspace'

    _rackspace_prices = RACKSPACE_PRICES

    features = {"create_node": ["generates_password"]}

    NODE_STATE_MAP = { 'BUILD': NodeState.PENDING,
                       'REBUILD': NodeState.PENDING,
                       'ACTIVE': NodeState.RUNNING,
                       'SUSPENDED': NodeState.TERMINATED,
                       'QUEUE_RESIZE': NodeState.PENDING,
                       'PREP_RESIZE': NodeState.PENDING,
                       'VERIFY_RESIZE': NodeState.RUNNING,
                       'PASSWORD': NodeState.PENDING,
                       'RESCUE': NodeState.PENDING,
                       'REBUILD': NodeState.PENDING,
                       'REBOOT': NodeState.REBOOTING,
                       'HARD_REBOOT': NodeState.REBOOTING,
                       'SHARE_IP': NodeState.PENDING,
                       'SHARE_IP_NO_CONFIG': NodeState.PENDING,
                       'DELETE_IP': NodeState.PENDING,
                       'UNKNOWN': NodeState.UNKNOWN}

    def list_nodes(self):
        return self._to_nodes(self.connection.request('/servers/detail').object)

    def list_sizes(self, location=None):
        return self._to_sizes(self.connection.request('/flavors/detail').object)

    def list_images(self, location=None):
        return self._to_images(self.connection.request('/images/detail').object)

    def list_locations(self):
        """Lists available locations

        Locations cannot be set or retrieved via the API, but currently
        there are two locations, DFW and ORD.
        """
        return [NodeLocation(0, "Rackspace DFW1/ORD1", 'US', self)]

    def _change_password_or_name(self, node, name=None, password=None):
        uri = '/servers/%s' % (node.id)

        if not name:
            name = node.name

        body = { 'xmlns': NAMESPACE,
                 'name': name}

        if password != None:
            body['adminPass'] = password

        server_elm = ET.Element('server', body)

        resp = self.connection.request(uri, method='PUT', data=ET.tostring(server_elm))

        if resp.status == 204 and password != None:
            node.extra['password'] = password

        return resp.status == 204

    def ex_set_password(self, node, password):
        """
        Sets the Node's root password.

        This will reboot the instance to complete the operation.

        L{node.extra['password']} will be set to the new value if the
        operation was successful.
        """
        return self._change_password_or_name(node, password=password)

    def ex_set_server_name(self, node, name):
        """
        Sets the Node's name.

        This will reboot the instance to complete the operation.
        """
        return self._change_password_or_name(node, name=name)

    def create_node(self, **kwargs):
        """Create a new rackspace node

        See L{NodeDriver.create_node} for more keyword args.
        @keyword    ex_metadata: Key/Value metadata to associate with a node
        @type       ex_metadata: C{dict}

        @keyword    ex_files:   File Path => File contents to create on the node
        @type       ex_files:   C{dict}
        """
        name = kwargs['name']
        image = kwargs['image']
        size = kwargs['size']
        server_elm = ET.Element(
            'server',
            {'xmlns': NAMESPACE,
             'name': name,
             'imageId': str(image.id),
             'flavorId': str(size.id)}
        )

        metadata_elm = self._metadata_to_xml(kwargs.get("ex_metadata", {}))
        if metadata_elm:
            server_elm.append(metadata_elm)

        files_elm = self._files_to_xml(kwargs.get("ex_files", {}))
        if files_elm:
            server_elm.append(files_elm)

        shared_ip_elm = self._shared_ip_group_to_xml(kwargs.get("ex_shared_ip_group", None))
        if shared_ip_elm:
            server_elm.append(shared_ip_elm)

        resp = self.connection.request("/servers",
                                       method='POST',
                                       data=ET.tostring(server_elm))
        return self._to_node(resp.object)

    def ex_rebuild(self, node_id, image_id):
        elm = ET.Element(
            'rebuild',
            {'xmlns': NAMESPACE,
             'imageId': image_id,
            }
        )
        resp = self.connection.request("/servers/%s/action" % node_id,
                                       method='POST',
                                       data=ET.tostring(elm))
        return resp.status == 202

    def ex_create_ip_group(self, group_name, node_id=None):
        group_elm = ET.Element(
            'sharedIpGroup',
            {'xmlns': NAMESPACE,
             'name': group_name,
            }
        )
        if node_id:
            ET.SubElement(group_elm,
                'server',
                {'id': node_id}
            )

        resp = self.connection.request('/shared_ip_groups',
                                       method='POST',
                                       data=ET.tostring(group_elm))
        return self._to_shared_ip_group(resp.object)

    def ex_list_ip_groups(self, details=False):
        uri = '/shared_ip_groups/detail' if details else '/shared_ip_groups'
        resp = self.connection.request(uri,
                                       method='GET')
        groups = self._findall(resp.object, 'sharedIpGroup')
        return [self._to_shared_ip_group(el) for el in groups]

    def ex_delete_ip_group(self, group_id):
        uri = '/shared_ip_groups/%s' % group_id
        resp = self.connection.request(uri, method='DELETE')
        return resp.status == 204

    def ex_share_ip(self, group_id, node_id, ip, configure_node=True):
        if configure_node:
            str_configure = 'true'
        else:
            str_configure = 'false'

        elm = ET.Element(
            'shareIp',
            {'xmlns': NAMESPACE,
             'sharedIpGroupId' : group_id,
             'configureServer' : str_configure}
        )

        uri = '/servers/%s/ips/public/%s' % (node_id, ip)

        resp = self.connection.request(uri,
                                       method='PUT',
                                       data=ET.tostring(elm))
        return resp.status == 202

    def ex_unshare_ip(self, node_id, ip):
        uri = '/servers/%s/ips/public/%s' % (node_id, ip)

        resp = self.connection.request(uri,
                                       method='DELETE')
        return resp.status == 202

    def ex_list_ip_addresses(self, node_id):
        uri = '/servers/%s/ips' % node_id
        resp = self.connection.request(uri,
                                       method='GET')
        return self._to_ip_addresses(resp.object)

    def _metadata_to_xml(self, metadata):
        if len(metadata) == 0:
            return None

        metadata_elm = ET.Element('metadata')
        for k, v in metadata.items():
            meta_elm = ET.SubElement(metadata_elm, 'meta', {'key': str(k) })
            meta_elm.text = str(v)

        return metadata_elm

    def _files_to_xml(self, files):
        if len(files) == 0:
            return None

        personality_elm = ET.Element('personality')
        for k, v in files.items():
            file_elm = ET.SubElement(personality_elm,
                                     'file',
                                     {'path': str(k)})
            file_elm.text = base64.b64encode(v)

        return personality_elm

    def _reboot_node(self, node, reboot_type='SOFT'):
        resp = self._node_action(node, ['reboot', ('type', reboot_type)])
        return resp.status == 202

    def ex_soft_reboot_node(self, node):
        return self._reboot_node(node, reboot_type='SOFT')

    def ex_hard_reboot_node(self, node):
        return self._reboot_node(node, reboot_type='HARD')

    def reboot_node(self, node):
        return self._reboot_node(node, reboot_type='HARD')

    def destroy_node(self, node):
        uri = '/servers/%s' % (node.id)
        resp = self.connection.request(uri, method='DELETE')
        return resp.status == 202

    def ex_get_node_details(self, node_id):
        uri = '/servers/%s' % (node_id)
        resp = self.connection.request(uri, method='GET')
        if resp.status == 404:
            return None
        return self._to_node(resp.object)

    def _node_action(self, node, body):
        if isinstance(body, list):
            attr = ' '.join(['%s="%s"' % (item[0], item[1])
                             for item in body[1:]])
            body = '<%s xmlns="%s" %s/>' % (body[0], NAMESPACE, attr)
        uri = '/servers/%s/action' % (node.id)
        resp = self.connection.request(uri, method='POST', data=body)
        return resp

    def _to_nodes(self, object):
        node_elements = self._findall(object, 'server')
        return [ self._to_node(el) for el in node_elements ]

    def _fixxpath(self, xpath):
        # ElementTree wants namespaces in its xpaths, so here we add them.
        return "/".join(["{%s}%s" % (NAMESPACE, e) for e in xpath.split("/")])

    def _findall(self, element, xpath):
        return element.findall(self._fixxpath(xpath))

    def _to_node(self, el):
        def get_ips(el):
            return [ip.get('addr') for ip in el]

        def get_meta_dict(el):
            d = {}
            for meta in el:
                d[meta.get('key')] =  meta.text
            return d

        public_ip = get_ips(self._findall(el,
                                          'addresses/public/ip'))
        private_ip = get_ips(self._findall(el,
                                          'addresses/private/ip'))
        metadata = get_meta_dict(self._findall(el, 'metadata/meta'))

        n = Node(id=el.get('id'),
                 name=el.get('name'),
                 state=self.NODE_STATE_MAP.get(el.get('status'), NodeState.UNKNOWN),
                 public_ip=public_ip,
                 private_ip=private_ip,
                 driver=self.connection.driver,
                 extra={
                    'password': el.get('adminPass'),
                    'hostId': el.get('hostId'),
                    'imageId': el.get('imageId'),
                    'flavorId': el.get('flavorId'),
                    'uri': "https://%s%s/servers/%s" % (self.connection.host, self.connection.request_path, el.get('id')),
                    'metadata': metadata,
                 })
        return n

    def _to_sizes(self, object):
        elements = self._findall(object, 'flavor')
        return [ self._to_size(el) for el in elements ]

    def _to_size(self, el):
        s = NodeSize(id=el.get('id'),
                     name=el.get('name'),
                     ram=int(el.get('ram')),
                     disk=int(el.get('disk')),
                     bandwidth=None, # XXX: needs hardcode
                     price=self._rackspace_prices.get(el.get('id')), # Hardcoded,
                     driver=self.connection.driver)
        return s

    def _to_images(self, object):
        elements = self._findall(object, "image")
        return [ self._to_image(el)
                 for el in elements
                 if el.get('status') == 'ACTIVE' ]

    def _to_image(self, el):
        i = NodeImage(id=el.get('id'),
                     name=el.get('name'),
                     driver=self.connection.driver,
                     extra={'serverId': el.get('serverId')})
        return i

    def ex_limits(self):
        """
        Extra call to get account's limits, such as
        rates (for example amount of POST requests per day)
        and absolute limits like total amount of available
        RAM to be used by servers.
        
        @return: C{dict} with keys 'rate' and 'absolute'
        """

        def _to_rate(el):
            rate = {}
            for item in el.items():
                rate[item[0]] = item[1]

            return rate

        def _to_absolute(el):
            return {el.get('name'): el.get('value')}

        limits = self.connection.request("/limits").object
        rate = [ _to_rate(el) for el in self._findall(limits, 'rate/limit') ]
        absolute = {}
        for item in self._findall(limits, 'absolute/limit'):
            absolute.update(_to_absolute(item))

        return {"rate": rate, "absolute": absolute}

    def ex_save_image(self, node, name):
        """Create an image for node.

        @keyword    node: node to use as a base for image
        @param      node: L{Node}
        @keyword    name: name for new image
        @param      name: C{string}
        """

        image_elm = ET.Element(
                'image',
                {'xmlns': NAMESPACE,
                    'name': name,
                    'serverId': node.id}
        )

        return self._to_image(self.connection.request("/images",
                    method="POST",
                    data=ET.tostring(image_elm)).object)

    def _to_shared_ip_group(self, el):
        servers_el = self._findall(el, 'servers')
        if servers_el:
            servers = [s.get('id') for s in self._findall(servers_el[0], 'server')]
        else:
            servers = None
        return RackspaceSharedIpGroup(id=el.get('id'),
                                      name=el.get('name'),
                                      servers=servers)

    def _to_ip_addresses(self, el):
        return RackspaceNodeIpAddresses(
            [ip.get('addr') for ip in self._findall(self._findall(el, 'public')[0], 'ip')],
            [ip.get('addr') for ip in self._findall(self._findall(el, 'private')[0], 'ip')]
        )

    def _shared_ip_group_to_xml(self, shared_ip_group):
        if not shared_ip_group:
            return None

        return ET.Element('sharedIpGroupId', shared_ip_group)

class RackspaceUKConnection(RackspaceConnection):
    """
    Connection class for the Rackspace UK driver
    """
    auth_host = AUTH_HOST_UK

class RackspaceUKNodeDriver(RackspaceNodeDriver):
    """Driver for Rackspace in the UK (London)
    """

    name = 'Rackspace (UK)'
    connectionCls = RackspaceUKConnection

    def list_locations(self):
        return [NodeLocation(0, 'Rackspace UK London', 'UK', self)]

########NEW FILE########
__FILENAME__ = rimuhosting
# Licensed to the Apache Software Foundation (ASF) under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""
RimuHosting Driver
"""
try:
    import json
except:
    import simplejson as json

from libcloud.common.base import ConnectionKey, Response
from libcloud.common.types import InvalidCredsError
from libcloud.compute.types import Provider, NodeState
from libcloud.compute.base import NodeDriver, NodeSize, Node, NodeLocation
from libcloud.compute.base import NodeImage, NodeAuthPassword

API_CONTEXT = '/r'
API_HOST = 'rimuhosting.com'
API_PORT = (80,443)
API_SECURE = True

class RimuHostingException(Exception):
    """
    Exception class for RimuHosting driver
    """

    def __str__(self):
        return self.args[0]

    def __repr__(self):
        return "<RimuHostingException '%s'>" % (self.args[0])

class RimuHostingResponse(Response):
    def __init__(self, response):
        self.body = response.read()
        self.status = response.status
        self.headers = dict(response.getheaders())
        self.error = response.reason

        if self.success():
            self.object = self.parse_body()

    def success(self):
        if self.status == 403:
            raise InvalidCredsError()
        return True
    def parse_body(self):
        try:
            js = json.loads(self.body)
            if js[js.keys()[0]]['response_type'] == "ERROR":
                raise RimuHostingException(
                    js[js.keys()[0]]['human_readable_message']
                )
            return js[js.keys()[0]]
        except ValueError:
            raise RimuHostingException('Could not parse body: %s'
                                       % (self.body))
        except KeyError:
            raise RimuHostingException('Could not parse body: %s'
                                       % (self.body))

class RimuHostingConnection(ConnectionKey):
    """
    Connection class for the RimuHosting driver
    """

    api_context = API_CONTEXT
    host = API_HOST
    port = API_PORT
    responseCls = RimuHostingResponse

    def __init__(self, key, secure=True):
        # override __init__ so that we can set secure of False for testing
        ConnectionKey.__init__(self,key,secure)

    def add_default_headers(self, headers):
        # We want JSON back from the server. Could be application/xml
        # (but JSON is better).
        headers['Accept'] = 'application/json'
        # Must encode all data as json, or override this header.
        headers['Content-Type'] = 'application/json'

        headers['Authorization'] = 'rimuhosting apikey=%s' % (self.key)
        return headers;

    def request(self, action, params=None, data='', headers=None, method='GET'):
        if not headers:
            headers = {}
        if not params:
            params = {}
        # Override this method to prepend the api_context
        return ConnectionKey.request(self, self.api_context + action,
                                     params, data, headers, method)

class RimuHostingNodeDriver(NodeDriver):
    """
    RimuHosting node driver
    """

    type = Provider.RIMUHOSTING
    name = 'RimuHosting'
    connectionCls = RimuHostingConnection

    def __init__(self, key, host=API_HOST, port=API_PORT,
                 api_context=API_CONTEXT, secure=API_SECURE):
        # Pass in some extra vars so that
        self.key = key
        self.secure = secure
        self.connection = self.connectionCls(key ,secure)
        self.connection.host = host
        self.connection.api_context = api_context
        self.connection.port = port
        self.connection.driver = self
        self.connection.connect()

    def _order_uri(self, node,resource):
        # Returns the order uri with its resourse appended.
        return "/orders/%s/%s" % (node.id,resource)

    # TODO: Get the node state.
    def _to_node(self, order):
        n = Node(id=order['slug'],
                name=order['domain_name'],
                state=NodeState.RUNNING,
                public_ip=(
                    [order['allocated_ips']['primary_ip']]
                    + order['allocated_ips']['secondary_ips']
                ),
                private_ip=[],
                driver=self.connection.driver,
                extra={'order_oid': order['order_oid'],
                       'monthly_recurring_fee': order.get('billing_info').get('monthly_recurring_fee')})
        return n

    def _to_size(self,plan):
        return NodeSize(
            id=plan['pricing_plan_code'],
            name=plan['pricing_plan_description'],
            ram=plan['minimum_memory_mb'],
            disk=plan['minimum_disk_gb'],
            bandwidth=plan['minimum_data_transfer_allowance_gb'],
            price=plan['monthly_recurring_amt']['amt_usd'],
            driver=self.connection.driver
        )

    def _to_image(self,image):
        return NodeImage(id=image['distro_code'],
            name=image['distro_description'],
            driver=self.connection.driver)

    def list_sizes(self, location=None):
        # Returns a list of sizes (aka plans)
        # Get plans. Note this is really just for libcloud.
        # We are happy with any size.
        if location == None:
            location = '';
        else:
            location = ";dc_location=%s" % (location.id)

        res = self.connection.request('/pricing-plans;server-type=VPS%s' % (location)).object
        return map(lambda x : self._to_size(x), res['pricing_plan_infos'])

    def list_nodes(self):
        # Returns a list of Nodes
        # Will only include active ones.
        res = self.connection.request('/orders;include_inactive=N').object
        return map(lambda x : self._to_node(x), res['about_orders'])

    def list_images(self, location=None):
        # Get all base images.
        # TODO: add other image sources. (Such as a backup of a VPS)
        # All Images are available for use at all locations
        res = self.connection.request('/distributions').object
        return map(lambda x : self._to_image(x), res['distro_infos'])

    def reboot_node(self, node):
        # Reboot
        # PUT the state of RESTARTING to restart a VPS.
        # All data is encoded as JSON
        data = {'reboot_request':{'running_state':'RESTARTING'}}
        uri = self._order_uri(node,'vps/running-state')
        self.connection.request(uri,data=json.dumps(data),method='PUT')
        # XXX check that the response was actually successful
        return True

    def destroy_node(self, node):
        # Shutdown a VPS.
        uri = self._order_uri(node,'vps')
        self.connection.request(uri,method='DELETE')
        # XXX check that the response was actually successful
        return True

    def create_node(self, **kwargs):
        """Creates a RimuHosting instance

        See L{NodeDriver.create_node} for more keyword args.

        @keyword    name: Must be a FQDN. e.g example.com.
        @type       name: C{string}

        @keyword    ex_billing_oid: If not set, a billing method is automatically picked.
        @type       ex_billing_oid: C{string}

        @keyword    ex_host_server_oid: The host server to set the VPS up on.
        @type       ex_host_server_oid: C{string}

        @keyword    ex_vps_order_oid_to_clone: Clone another VPS to use as the image for the new VPS.
        @type       ex_vps_order_oid_to_clone: C{string}

        @keyword    ex_num_ips: Number of IPs to allocate. Defaults to 1.
        @type       ex_num_ips: C{int}

        @keyword    ex_extra_ip_reason: Reason for needing the extra IPs.
        @type       ex_extra_ip_reason: C{string}

        @keyword    ex_memory_mb: Memory to allocate to the VPS.
        @type       ex_memory_mb: C{int}

        @keyword    ex_disk_space_mb: Diskspace to allocate to the VPS. Defaults to 4096 (4GB).
        @type       ex_disk_space_mb: C{int}

        @keyword    ex_disk_space_2_mb: Secondary disk size allocation. Disabled by default.
        @type       ex_disk_space_2_mb: C{int}

        @keyword    ex_control_panel: Control panel to install on the VPS.
        @type       ex_control_panel: C{string}
        """
        # Note we don't do much error checking in this because we
        # expect the API to error out if there is a problem.
        name = kwargs['name']
        image = kwargs['image']
        size = kwargs['size']

        data = {
            'instantiation_options':{
                'domain_name': name, 'distro': image.id
            },
            'pricing_plan_code': size.id,
        }

        if kwargs.has_key('ex_control_panel'):
            data['instantiation_options']['control_panel'] = kwargs['ex_control_panel']

        if kwargs.has_key('auth'):
            auth = kwargs['auth']
            if not isinstance(auth, NodeAuthPassword):
                raise ValueError('auth must be of NodeAuthPassword type')
            data['instantiation_options']['password'] = auth.password

        if kwargs.has_key('ex_billing_oid'):
            #TODO check for valid oid.
            data['billing_oid'] = kwargs['ex_billing_oid']

        if kwargs.has_key('ex_host_server_oid'):
            data['host_server_oid'] = kwargs['ex_host_server_oid']

        if kwargs.has_key('ex_vps_order_oid_to_clone'):
            data['vps_order_oid_to_clone'] = kwargs['ex_vps_order_oid_to_clone']

        if kwargs.has_key('ex_num_ips') and int(kwargs['ex_num_ips']) > 1:
            if not kwargs.has_key('ex_extra_ip_reason'):
                raise RimuHostingException('Need an reason for having an extra IP')
            else:
                if not data.has_key('ip_request'):
                    data['ip_request'] = {}
                data['ip_request']['num_ips'] = int(kwargs['ex_num_ips'])
                data['ip_request']['extra_ip_reason'] = kwargs['ex_extra_ip_reason']

        if kwargs.has_key('ex_memory_mb'):
            if not data.has_key('vps_parameters'):
                data['vps_parameters'] = {}
            data['vps_parameters']['memory_mb'] = kwargs['ex_memory_mb']

        if kwargs.has_key('ex_disk_space_mb'):
            if not data.has_key('ex_vps_parameters'):
                data['vps_parameters'] = {}
            data['vps_parameters']['disk_space_mb'] = kwargs['ex_disk_space_mb']

        if kwargs.has_key('ex_disk_space_2_mb'):
            if not data.has_key('vps_parameters'):
                data['vps_parameters'] = {}
            data['vps_parameters']['disk_space_2_mb'] = kwargs['ex_disk_space_2_mb']

        res = self.connection.request(
            '/orders/new-vps',
            method='POST',
            data=json.dumps({"new-vps":data})
        ).object
        node = self._to_node(res['about_order'])
        node.extra['password'] = res['new_order_request']['instantiation_options']['password']
        return node

    def list_locations(self):
        return [
            NodeLocation('DCAUCKLAND', "RimuHosting Auckland", 'NZ', self),
            NodeLocation('DCDALLAS', "RimuHosting Dallas", 'US', self),
            NodeLocation('DCLONDON', "RimuHosting London", 'GB', self),
            NodeLocation('DCSYDNEY', "RimuHosting Sydney", 'AU', self),
        ]

    features = {"create_node": ["password"]}

########NEW FILE########
__FILENAME__ = slicehost
# Licensed to the Apache Software Foundation (ASF) under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""
Slicehost Driver
"""
import base64
import socket

from xml.etree import ElementTree as ET
from xml.parsers.expat import ExpatError

from libcloud.common.base import ConnectionUserAndKey, ConnectionKey, Response
from libcloud.compute.types import NodeState, Provider, InvalidCredsError, MalformedResponseError
from libcloud.compute.base import NodeSize, NodeDriver, NodeImage, NodeLocation
from libcloud.compute.base import Node, is_private_subnet

class SlicehostResponse(Response):

    def parse_body(self):
        # length of 1 can't be valid XML, but on destroy node, slicehost returns
        # a 1 byte response with a "Content-Type: application/xml" header. booya.
        if not self.body or len(self.body) <= 1:
            return None
        try:
            body = ET.XML(self.body)
        except:
            raise MalformedResponseError("Failed to parse XML", body=self.body, driver=SlicehostNodeDriver)
        return body

    def parse_error(self):
        if self.status == 401:
            raise InvalidCredsError(self.body)

        try:
            body = ET.XML(self.body)
        except:
            raise MalformedResponseError("Failed to parse XML", body=self.body, driver=SlicehostNodeDriver)
        try:
            return "; ".join([ err.text
                               for err in
                               body.findall('error') ])
        except ExpatError:
            return self.body


class SlicehostConnection(ConnectionKey):
    """
    Connection class for the Slicehost driver
    """

    host = 'api.slicehost.com'
    responseCls = SlicehostResponse

    def add_default_headers(self, headers):
        headers['Authorization'] = ('Basic %s'
                              % (base64.b64encode('%s:' % self.key)))
        return headers


class SlicehostNodeDriver(NodeDriver):
    """
    Slicehost node driver
    """

    connectionCls = SlicehostConnection

    type = Provider.SLICEHOST
    name = 'Slicehost'

    features = {"create_node": ["generates_password"]}

    NODE_STATE_MAP = { 'active': NodeState.RUNNING,
                       'build': NodeState.PENDING,
                       'reboot': NodeState.REBOOTING,
                       'hard_reboot': NodeState.REBOOTING,
                       'terminated': NodeState.TERMINATED }

    def list_nodes(self):
        return self._to_nodes(self.connection.request('/slices.xml').object)

    def list_sizes(self, location=None):
        return self._to_sizes(self.connection.request('/flavors.xml').object)

    def list_images(self, location=None):
        return self._to_images(self.connection.request('/images.xml').object)

    def list_locations(self):
        return [
            NodeLocation(0, 'Slicehost St. Louis (STL-A)', 'US', self),
            NodeLocation(0, 'Slicehost St. Louis (STL-B)', 'US', self),
            NodeLocation(0, 'Slicehost Dallas-Fort Worth (DFW-1)', 'US', self)
        ]

    def create_node(self, **kwargs):
        name = kwargs['name']
        image = kwargs['image']
        size = kwargs['size']
        uri = '/slices.xml'

        # create a slice obj
        root = ET.Element('slice')
        el_name = ET.SubElement(root, 'name')
        el_name.text = name
        flavor_id = ET.SubElement(root, 'flavor-id')
        flavor_id.text = str(size.id)
        image_id = ET.SubElement(root, 'image-id')
        image_id.text = str(image.id)
        xml = ET.tostring(root)

        node = self._to_nodes(
            self.connection.request(
                uri,
                method='POST',
                data=xml,
                headers={'Content-Type': 'application/xml'}
            ).object
        )[0]
        return node

    def reboot_node(self, node):
        """Reboot the node by passing in the node object"""

        # 'hard' could bubble up as kwarg depending on how reboot_node
        # turns out. Defaulting to soft reboot.
        #hard = False
        #reboot = self.api.hard_reboot if hard else self.api.reboot
        #expected_status = 'hard_reboot' if hard else 'reboot'

        uri = '/slices/%s/reboot.xml' % (node.id)
        node = self._to_nodes(
            self.connection.request(uri, method='PUT').object
        )[0]
        return node.state == NodeState.REBOOTING

    def destroy_node(self, node):
        """Destroys the node

        Requires 'Allow Slices to be deleted or rebuilt from the API' to be
        ticked at https://manage.slicehost.com/api, otherwise returns::
            <errors>
              <error>You must enable slice deletes in the SliceManager</error>
              <error>Permission denied</error>
            </errors>
        """
        uri = '/slices/%s/destroy.xml' % (node.id)
        self.connection.request(uri, method='PUT')
        return True

    def _to_nodes(self, object):
        if object.tag == 'slice':
            return [ self._to_node(object) ]
        node_elements = object.findall('slice')
        return [ self._to_node(el) for el in node_elements ]

    def _to_node(self, element):

        attrs = [ 'name', 'image-id', 'progress', 'id', 'bw-out', 'bw-in',
                  'flavor-id', 'status', 'ip-address', 'root-password' ]

        node_attrs = {}
        for attr in attrs:
            node_attrs[attr] = element.findtext(attr)

        # slicehost does not determine between public and private, so we
        # have to figure it out
        primary_ip = element.findtext('ip-address')
        public_ip = []
        private_ip = []
        for addr in element.findall('addresses/address'):
            ip = addr.text
            try:
                socket.inet_aton(ip)
            except socket.error:
                # not a valid ip
                continue
            if is_private_subnet(ip):
                private_ip.append(ip)
            else:
                public_ip.append(ip)

        public_ip.append(primary_ip)

        public_ip = list(set(public_ip))

        try:
            state = self.NODE_STATE_MAP[element.findtext('status')]
        except:
            state = NodeState.UNKNOWN

        # for consistency with other drivers, we put this in two places.
        node_attrs['password'] = node_attrs['root-password']
        extra = {}
        for k in node_attrs.keys():
            ek = k.replace("-", "_")
            extra[ek] = node_attrs[k]
        n = Node(id=element.findtext('id'),
                 name=element.findtext('name'),
                 state=state,
                 public_ip=public_ip,
                 private_ip=private_ip,
                 driver=self.connection.driver,
                 extra=extra)
        return n

    def _to_sizes(self, object):
        if object.tag == 'flavor':
            return [ self._to_size(object) ]
        elements = object.findall('flavor')
        return [ self._to_size(el) for el in elements ]

    def _to_size(self, element):
        s = NodeSize(id=int(element.findtext('id')),
                     name=str(element.findtext('name')),
                     ram=int(element.findtext('ram')),
                     disk=None, # XXX: needs hardcode
                     bandwidth=None, # XXX: needs hardcode
                     price=float(element.findtext('price'))/(100*24*30),
                     driver=self.connection.driver)
        return s

    def _to_images(self, object):
        if object.tag == 'image':
            return [ self._to_image(object) ]
        elements = object.findall('image')
        return [ self._to_image(el) for el in elements ]

    def _to_image(self, element):
        i = NodeImage(id=int(element.findtext('id')),
                     name=str(element.findtext('name')),
                     driver=self.connection.driver)
        return i

########NEW FILE########
__FILENAME__ = softlayer
# Licensed to the Apache Software Foundation (ASF) under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""
Softlayer driver
"""

import time
import xmlrpclib

import libcloud

from libcloud.common.types import InvalidCredsError, LibcloudError
from libcloud.compute.types import Provider, NodeState
from libcloud.compute.base import NodeDriver, Node, NodeLocation, NodeSize, NodeImage

DATACENTERS = {
    'sea01': {'country': 'US'},
    'wdc01': {'country': 'US'},
    'dal01': {'country': 'US'}
}

NODE_STATE_MAP = {
    'RUNNING': NodeState.RUNNING,
    'HALTED': NodeState.TERMINATED,
    'PAUSED': NodeState.TERMINATED,
}

DEFAULT_PACKAGE = 46

SL_IMAGES = [
    {'id': 1684, 'name': 'CentOS 5 - Minimal Install (32 bit)'},
    {'id': 1685, 'name': 'CentOS 5 - Minimal Install (64 bit)'},
    {'id': 1686, 'name': 'CentOS 5 - LAMP Install (32 bit)'},
    {'id': 1687, 'name': 'CentOS 5 - LAMP Install (64 bit)'},
    {'id': 1688, 'name': 'Red Hat Enterprise Linux 5 - Minimal Install (32 bit)'},
    {'id': 1689, 'name': 'Red Hat Enterprise Linux 5 - Minimal Install (64 bit)'},
    {'id': 1690, 'name': 'Red Hat Enterprise Linux 5 - LAMP Install (32 bit)'},
    {'id': 1691, 'name': 'Red Hat Enterprise Linux 5 - LAMP Install (64 bit)'},
    {'id': 1692, 'name': 'Ubuntu Linux 8 LTS Hardy Heron - Minimal Install (32 bit)'},
    {'id': 1693, 'name': 'Ubuntu Linux 8 LTS Hardy Heron - Minimal Install (64 bit)'},
    {'id': 1694, 'name': 'Ubuntu Linux 8 LTS Hardy Heron - LAMP Install (32 bit)'},
    {'id': 1695, 'name': 'Ubuntu Linux 8 LTS Hardy Heron - LAMP Install (64 bit)'},
    {'id': 1696, 'name': 'Debian GNU/Linux 5.0 Lenny/Stable - Minimal Install (32 bit)'},
    {'id': 1697, 'name': 'Debian GNU/Linux 5.0 Lenny/Stable - Minimal Install (64 bit)'},
    {'id': 1698, 'name': 'Debian GNU/Linux 5.0 Lenny/Stable - LAMP Install (32 bit)'},
    {'id': 1699, 'name': 'Debian GNU/Linux 5.0 Lenny/Stable - LAMP Install (64 bit)'},
    {'id': 1700, 'name': 'Windows Server 2003 Standard SP2 with R2 (32 bit)'},
    {'id': 1701, 'name': 'Windows Server 2003 Standard SP2 with R2 (64 bit)'},
    {'id': 1703, 'name': 'Windows Server 2003 Enterprise SP2 with R2 (64 bit)'},
    {'id': 1705, 'name': 'Windows Server 2008 Standard Edition (64bit)'},
    {'id': 1715, 'name': 'Windows Server 2003 Datacenter SP2 (64 bit)'},
    {'id': 1716, 'name': 'Windows Server 2003 Datacenter SP2 (32 bit)'},
    {'id': 1742, 'name': 'Windows Server 2008 Standard Edition SP2 (32bit)'},
    {'id': 1752, 'name': 'Windows Server 2008 Standard Edition SP2 (64bit)'},
    {'id': 1756, 'name': 'Windows Server 2008 Enterprise Edition SP2 (32bit)'},
    {'id': 1761, 'name': 'Windows Server 2008 Enterprise Edition SP2 (64bit)'},
    {'id': 1766, 'name': 'Windows Server 2008 Datacenter Edition SP2 (32bit)'},
    {'id': 1770, 'name': 'Windows Server 2008 Datacenter Edition SP2 (64bit)'},
    {'id': 1857, 'name': 'Windows Server 2008 R2 Standard Edition (64bit)'},
    {'id': 1860, 'name': 'Windows Server 2008 R2 Enterprise Edition (64bit)'},
    {'id': 1863, 'name': 'Windows Server 2008 R2 Datacenter Edition (64bit)'},
]

"""
The following code snippet will print out all available "prices"
    mask = { 'items': '' }
    res = self.connection.request(
        "SoftLayer_Product_Package",
        "getObject",
        res,
        id=46,
        object_mask=mask
    )

    from pprint import pprint; pprint(res)
"""
SL_TEMPLATES = {
    'sl1': {
        'imagedata': {
            'name': '2 x 2.0 GHz, 1GB ram, 100GB',
            'ram': 1024,
            'disk': 100,
            'bandwidth': None
        },
        'prices': [
            {'id': 1644}, # 1 GB
            {'id': 1639}, # 100 GB (SAN)
            {'id': 1963}, # Private 2 x 2.0 GHz Cores
            {'id': 21}, # 1 IP Address
            {'id': 55}, # Host Ping
            {'id': 58}, # Automated Notification
            {'id': 1800}, # 0 GB Bandwidth
            {'id': 57}, # Email and Ticket
            {'id': 274}, # 1000 Mbps Public & Private Networks
            {'id': 905}, # Reboot / Remote Console
            {'id': 418}, # Nessus Vulnerability Assessment & Reporting
            {'id': 420}, # Unlimited SSL VPN Users & 1 PPTP VPN User per account
        ],
    },
    'sl2': {
        'imagedata': {
            'name': '2 x 2.0 GHz, 4GB ram, 350GB',
            'ram': 4096,
            'disk': 350,
            'bandwidth': None
        },
        'prices': [
            {'id': 1646}, # 4 GB
            {'id': 1639}, # 100 GB (SAN) - This is the only available "First Disk"
            {'id': 1638}, # 250 GB (SAN)
            {'id': 1963}, # Private 2 x 2.0 GHz Cores
            {'id': 21}, # 1 IP Address
            {'id': 55}, # Host Ping
            {'id': 58}, # Automated Notification
            {'id': 1800}, # 0 GB Bandwidth
            {'id': 57}, # Email and Ticket
            {'id': 274}, # 1000 Mbps Public & Private Networks
            {'id': 905}, # Reboot / Remote Console
            {'id': 418}, # Nessus Vulnerability Assessment & Reporting
            {'id': 420}, # Unlimited SSL VPN Users & 1 PPTP VPN User per account
        ],
    }
}

class SoftLayerException(LibcloudError):
    """
    Exception class for SoftLayer driver
    """
    pass

class SoftLayerSafeTransport(xmlrpclib.SafeTransport):
    pass

class SoftLayerTransport(xmlrpclib.Transport):
    pass

class SoftLayerProxy(xmlrpclib.ServerProxy):
    transportCls = (SoftLayerTransport, SoftLayerSafeTransport)
    API_PREFIX = "http://api.service.softlayer.com/xmlrpc/v3"

    def __init__(self, service, user_agent, verbose=0):
        cls = self.transportCls[0]
        if SoftLayerProxy.API_PREFIX[:8] == "https://":
            cls = self.transportCls[1]
        t = cls(use_datetime=0)
        t.user_agent = user_agent
        xmlrpclib.ServerProxy.__init__(
            self,
            uri="%s/%s" % (SoftLayerProxy.API_PREFIX, service),
            transport=t,
            verbose=verbose
        )

class SoftLayerConnection(object):
    """
    Connection class for the SoftLayer driver
    """

    proxyCls = SoftLayerProxy
    driver = None

    def __init__(self, user, key):
        self.user = user
        self.key = key
        self.ua = []

    def request(self, service, method, *args, **kwargs):
        sl = self.proxyCls(service, self._user_agent())

        headers = {}
        headers.update(self._get_auth_headers())
        headers.update(self._get_init_params(service, kwargs.get('id')))
        headers.update(self._get_object_mask(service, kwargs.get('object_mask')))
        params = [{'headers': headers}] + list(args)

        try:
            return getattr(sl, method)(*params)
        except xmlrpclib.Fault, e:
            if e.faultCode == "SoftLayer_Account":
                raise InvalidCredsError(e.faultString)
            raise SoftLayerException(e)

    def _user_agent(self):
        return 'libcloud/%s (%s)%s' % (
                libcloud.__version__,
                self.driver.name,
                "".join([" (%s)" % x for x in self.ua]))

    def user_agent_append(self, s):
        self.ua.append(s)

    def _get_auth_headers(self):
        return {
            'authenticate': {
                'username': self.user,
                'apiKey': self.key
            }
        }

    def _get_init_params(self, service, id):
        if id is not None:
            return {
                '%sInitParameters' % service: {'id': id}
            }
        else:
            return {}

    def _get_object_mask(self, service, mask):
        if mask is not None:
            return {
                '%sObjectMask' % service: {'mask': mask}
            }
        else:
            return {}

class SoftLayerNodeDriver(NodeDriver):
    """
    SoftLayer node driver

    Extra node attributes:
        - password: root password
        - hourlyRecurringFee: hourly price (if applicable)
        - recurringFee      : flat rate    (if applicable)
        - recurringMonths   : The number of months in which the recurringFee will be incurred.
    """
    connectionCls = SoftLayerConnection
    name = 'SoftLayer'
    type = Provider.SOFTLAYER

    features = {"create_node": ["generates_password"]}

    def __init__(self, key, secret=None, secure=False):
        self.key = key
        self.secret = secret
        self.connection = self.connectionCls(key, secret)
        self.connection.driver = self

    def _to_node(self, host):
        try:
            password = host['softwareComponents'][0]['passwords'][0]['password']
        except (IndexError, KeyError):
            password = None

        hourlyRecurringFee = host.get('billingItem', {}).get('hourlyRecurringFee', 0)
        recurringFee       = host.get('billingItem', {}).get('recurringFee', 0)
        recurringMonths    = host.get('billingItem', {}).get('recurringMonths', 0)

        return Node(
            id=host['id'],
            name=host['hostname'],
            state=NODE_STATE_MAP.get(
                host['powerState']['keyName'],
                NodeState.UNKNOWN
            ),
            public_ip=[host['primaryIpAddress']],
            private_ip=[host['primaryBackendIpAddress']],
            driver=self,
            extra={
                'password': password,
                'hourlyRecurringFee': hourlyRecurringFee,
                'recurringFee': recurringFee,
                'recurringMonths': recurringMonths,
            }
        )

    def _to_nodes(self, hosts):
        return [self._to_node(h) for h in hosts]

    def destroy_node(self, node):
        billing_item = self.connection.request(
            "SoftLayer_Virtual_Guest",
            "getBillingItem",
            id=node.id
        )

        if billing_item:
            res = self.connection.request(
                "SoftLayer_Billing_Item",
                "cancelService",
                id=billing_item['id']
            )
            return res
        else:
            return False

    def _get_order_information(self, order_id, timeout=1200, check_interval=5):
        mask = {
            'orderTopLevelItems': {
                'billingItem':  {
                    'resource': {
                        'softwareComponents': {
                            'passwords': ''
                        },
                        'powerState': '',
                    }
                },
            }
         }

        for i in range(0, timeout, check_interval):
            try:
                res = self.connection.request(
                    "SoftLayer_Billing_Order",
                    "getObject",
                    id=order_id,
                    object_mask=mask
                )
                item = res['orderTopLevelItems'][0]['billingItem']['resource']
                if item['softwareComponents'][0]['passwords']:
                    return item

            except (KeyError, IndexError):
                pass

            time.sleep(check_interval)

        return None

    def create_node(self, **kwargs):
        """Create a new SoftLayer node

        See L{NodeDriver.create_node} for more keyword args.
        @keyword    ex_domain: e.g. libcloud.org
        @type       ex_domain: C{string}
        """
        name = kwargs['name']
        image = kwargs['image']
        size = kwargs['size']
        domain = kwargs.get('ex_domain')
        location = kwargs['location']
        if domain == None:
            if name.find(".") != -1:
                domain = name[name.find('.')+1:]

        if domain == None:
            # TODO: domain is a required argument for the Sofylayer API, but it
            # it shouldn't be.
            domain = "exmaple.com"

        res = {'prices': SL_TEMPLATES[size.id]['prices']}
        res['packageId'] = DEFAULT_PACKAGE
        res['prices'].append({'id': image.id})  # Add OS to order
        res['location'] = location.id
        res['complexType'] = 'SoftLayer_Container_Product_Order_Virtual_Guest'
        res['quantity'] = 1
        res['useHourlyPricing'] = True
        res['virtualGuests'] = [
            {
                'hostname': name,
                'domain': domain
            }
        ]

        res = self.connection.request(
            "SoftLayer_Product_Order",
            "placeOrder",
            res
        )

        order_id = res['orderId']
        raw_node = self._get_order_information(order_id)

        return self._to_node(raw_node)

    def _to_image(self, img):
        return NodeImage(
            id=img['id'],
            name=img['name'],
            driver=self.connection.driver
        )

    def list_images(self, location=None):
        return [self._to_image(i) for i in SL_IMAGES]

    def _to_size(self, id, size):
        return NodeSize(
            id=id,
            name=size['name'],
            ram=size['ram'],
            disk=size['disk'],
            bandwidth=size['bandwidth'],
            price=None,
            driver=self.connection.driver,
        )

    def list_sizes(self, location=None):
        return [self._to_size(id, s['imagedata']) for id, s in SL_TEMPLATES.iteritems()]

    def _to_loc(self, loc):
        return NodeLocation(
            id=loc['id'],
            name=loc['name'],
            country=DATACENTERS[loc['name']]['country'],
            driver=self
        )

    def list_locations(self):
        res = self.connection.request(
            "SoftLayer_Location_Datacenter",
            "getDatacenters"
        )

        # checking "in DATACENTERS", because some of the locations returned by getDatacenters are not useable.
        return [self._to_loc(l) for l in res if l['name'] in DATACENTERS]

    def list_nodes(self):
        mask = {
            'virtualGuests': {
                'powerState': '',
                'softwareComponents': {
                    'passwords': ''
                },
                'billingItem': '',
            },
        }
        res = self.connection.request(
            "SoftLayer_Account",
            "getVirtualGuests",
            object_mask=mask
        )
        nodes = self._to_nodes(res)
        return nodes

    def reboot_node(self, node):
        res = self.connection.request(
            "SoftLayer_Virtual_Guest",
            "rebootHard",
            id=node.id
        )
        return res

########NEW FILE########
__FILENAME__ = vcloud
# Licensed to the Apache Software Foundation (ASF) under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""
VMware vCloud driver.
"""
import base64
import httplib
import time

from urlparse import urlparse
from xml.etree import ElementTree as ET
from xml.parsers.expat import ExpatError

from libcloud.common.base import Response, ConnectionUserAndKey
from libcloud.common.types import InvalidCredsError
from libcloud.compute.providers import Provider
from libcloud.compute.types import NodeState
from libcloud.compute.base import Node, NodeDriver, NodeLocation
from libcloud.compute.base import NodeSize, NodeImage, NodeAuthPassword

"""
From vcloud api "The VirtualQuantity element defines the number of MB
of memory. This should be either 512 or a multiple of 1024 (1 GB)."
"""
VIRTUAL_MEMORY_VALS = [512] + [1024 * i for i in range(1,9)]

DEFAULT_TASK_COMPLETION_TIMEOUT = 600

def get_url_path(url):
    return urlparse(url.strip()).path

def fixxpath(root, xpath):
    """ElementTree wants namespaces in its xpaths, so here we add them."""
    namespace, root_tag = root.tag[1:].split("}", 1)
    fixed_xpath = "/".join(["{%s}%s" % (namespace, e)
                            for e in xpath.split("/")])
    return fixed_xpath

class InstantiateVAppXML(object):

    def __init__(self, name, template, net_href, cpus, memory,
                 password=None, row=None, group=None):
        self.name = name
        self.template = template
        self.net_href = net_href
        self.cpus = cpus
        self.memory = memory
        self.password = password
        self.row = row
        self.group = group

        self._build_xmltree()

    def tostring(self):
        return ET.tostring(self.root)

    def _build_xmltree(self):
        self.root = self._make_instantiation_root()

        self._add_vapp_template(self.root)
        instantionation_params = ET.SubElement(self.root,
                                               "InstantiationParams")

        # product and virtual hardware
        self._make_product_section(instantionation_params)
        self._make_virtual_hardware(instantionation_params)

        network_config_section = ET.SubElement(instantionation_params,
                                               "NetworkConfigSection")

        network_config = ET.SubElement(network_config_section,
                                       "NetworkConfig")
        self._add_network_association(network_config)

    def _make_instantiation_root(self):
        return ET.Element(
            "InstantiateVAppTemplateParams",
            {'name': self.name,
             'xml:lang': 'en',
             'xmlns': "http://www.vmware.com/vcloud/v0.8",
             'xmlns:xsi': "http://www.w3.org/2001/XMLSchema-instance"}
        )

    def _add_vapp_template(self, parent):
        return ET.SubElement(
            parent,
            "VAppTemplate",
            {'href': self.template}
        )

    def _make_product_section(self, parent):
        prod_section = ET.SubElement(
            parent,
            "ProductSection",
            {'xmlns:q1': "http://www.vmware.com/vcloud/v0.8",
             'xmlns:ovf': "http://schemas.dmtf.org/ovf/envelope/1"}
        )

        if self.password:
            self._add_property(prod_section, 'password', self.password)

        if self.row:
            self._add_property(prod_section, 'row', self.row)

        if self.group:
            self._add_property(prod_section, 'group', self.group)

        return prod_section

    def _add_property(self, parent, ovfkey, ovfvalue):
        return ET.SubElement(
            parent,
            "Property",
            {'xmlns': 'http://schemas.dmtf.org/ovf/envelope/1',
             'ovf:key': ovfkey,
             'ovf:value': ovfvalue}
        )

    def _make_virtual_hardware(self, parent):
        vh = ET.SubElement(
            parent,
            "VirtualHardwareSection",
            {'xmlns:q1': "http://www.vmware.com/vcloud/v0.8"}
        )

        self._add_cpu(vh)
        self._add_memory(vh)

        return vh

    def _add_cpu(self, parent):
        cpu_item = ET.SubElement(
            parent,
            "Item",
            {'xmlns': "http://schemas.dmtf.org/ovf/envelope/1"}
        )
        self._add_instance_id(cpu_item, '1')
        self._add_resource_type(cpu_item, '3')
        self._add_virtual_quantity(cpu_item, self.cpus)

        return cpu_item

    def _add_memory(self, parent):
        mem_item = ET.SubElement(
            parent,
            "Item",
            {'xmlns': "http://schemas.dmtf.org/ovf/envelope/1"}
        )
        self._add_instance_id(mem_item, '2')
        self._add_resource_type(mem_item, '4')
        self._add_virtual_quantity(mem_item, self.memory)

        return mem_item

    def _add_instance_id(self, parent, id):
        elm = ET.SubElement(
            parent,
            "InstanceID",
            {'xmlns': 'http://schemas.dmtf.org/wbem/wscim/1/cim-schema/2/CIM_ResourceAllocationSettingData'}
        )
        elm.text = id
        return elm

    def _add_resource_type(self, parent, type):
        elm = ET.SubElement(
            parent,
            "ResourceType",
            {'xmlns': 'http://schemas.dmtf.org/wbem/wscim/1/cim-schema/2/CIM_ResourceAllocationSettingData'}
        )
        elm.text = type
        return elm

    def _add_virtual_quantity(self, parent, amount):
        elm = ET.SubElement(
             parent,
             "VirtualQuantity",
             {'xmlns': 'http://schemas.dmtf.org/wbem/wscim/1/cim-schema/2/CIM_ResourceAllocationSettingData'}
         )
        elm.text = amount
        return elm

    def _add_network_association(self, parent):
        return ET.SubElement(
            parent,
            "NetworkAssociation",
            {'href': self.net_href}
        )

class VCloudResponse(Response):

    def parse_body(self):
        if not self.body:
            return None
        try:
            return ET.XML(self.body)
        except ExpatError, e:
            raise Exception("%s: %s" % (e, self.parse_error()))

    def parse_error(self):
        return self.error

    def success(self):
        return self.status in (httplib.OK, httplib.CREATED,
                               httplib.NO_CONTENT, httplib.ACCEPTED)

class VCloudConnection(ConnectionUserAndKey):
    """
    Connection class for the vCloud driver
    """

    responseCls = VCloudResponse
    token = None
    host = None

    def request(self, *args, **kwargs):
        self._get_auth_token()
        return super(VCloudConnection, self).request(*args, **kwargs)

    def check_org(self):
        # the only way to get our org is by logging in.
        self._get_auth_token()

    def _get_auth_headers(self):
        """Some providers need different headers than others"""
        return {
            'Authorization':
                "Basic %s"
                % base64.b64encode('%s:%s' % (self.user_id, self.key)),
            'Content-Length': 0
        }

    def _get_auth_token(self):
        if not self.token:
            conn = self.conn_classes[self.secure](self.host,
                                                  self.port[self.secure])
            conn.request(method='POST', url='/api/v0.8/login',
                         headers=self._get_auth_headers())

            resp = conn.getresponse()
            headers = dict(resp.getheaders())
            body = ET.XML(resp.read())

            try:
                self.token = headers['set-cookie']
            except KeyError:
                raise InvalidCredsError()

            self.driver.org = get_url_path(
                body.find(fixxpath(body, 'Org')).get('href')
            )

    def add_default_headers(self, headers):
        headers['Cookie'] = self.token
        return headers

class VCloudNodeDriver(NodeDriver):
    """
    vCloud node driver
    """

    type = Provider.VCLOUD
    name = "vCloud"
    connectionCls = VCloudConnection
    org = None
    _vdcs = None

    NODE_STATE_MAP = {'0': NodeState.PENDING,
                      '1': NodeState.PENDING,
                      '2': NodeState.PENDING,
                      '3': NodeState.PENDING,
                      '4': NodeState.RUNNING}

    @property
    def vdcs(self):
        if not self._vdcs:
            self.connection.check_org() # make sure the org is set.
            res = self.connection.request(self.org)
            self._vdcs = [
                get_url_path(i.get('href'))
                for i
                in res.object.findall(fixxpath(res.object, "Link"))
                if i.get('type') == 'application/vnd.vmware.vcloud.vdc+xml'
            ]

        return self._vdcs

    @property
    def networks(self):
        networks = []
        for vdc in self.vdcs:
            res = self.connection.request(vdc).object
            networks.extend(
                [network
                 for network in res.findall(
                     fixxpath(res, "AvailableNetworks/Network")
                 )]
            )

        return networks

    def _to_image(self, image):
        image = NodeImage(id=image.get('href'),
                          name=image.get('name'),
                          driver=self.connection.driver)
        return image

    def _to_node(self, name, elm):
        state = self.NODE_STATE_MAP[elm.get('status')]
        public_ips = []
        private_ips = []

        # Following code to find private IPs works for Terremark
        connections = elm.findall('{http://schemas.dmtf.org/ovf/envelope/1}NetworkConnectionSection/{http://www.vmware.com/vcloud/v0.8}NetworkConnection')
        for connection in connections:
            ips = [ip.text
                   for ip
                   in connection.findall(fixxpath(elm, "IpAddress"))]
            if connection.get('Network') == 'Internal':
                private_ips.extend(ips)
            else:
                public_ips.extend(ips)

        node = Node(id=elm.get('href'),
                    name=name,
                    state=state,
                    public_ip=public_ips,
                    private_ip=private_ips,
                    driver=self.connection.driver)

        return node

    def _get_catalog_hrefs(self):
        res = self.connection.request(self.org)
        catalogs = [
            get_url_path(i.get('href'))
            for i in res.object.findall(fixxpath(res.object, "Link"))
            if i.get('type') == 'application/vnd.vmware.vcloud.catalog+xml'
        ]

        return catalogs

    def _wait_for_task_completion(self, task_href,
                                  timeout=DEFAULT_TASK_COMPLETION_TIMEOUT):
        start_time = time.time()
        res = self.connection.request(task_href)
        status = res.object.get('status')
        while status != 'success':
            if status == 'error':
                raise Exception("Error status returned by task %s."
                                % task_href)
            if status == 'canceled':
                raise Exception("Canceled status returned by task %s."
                                % task_href)
            if (time.time() - start_time >= timeout):
                raise Exception("Timeout while waiting for task %s."
                                % task_href)
            time.sleep(5)
            res = self.connection.request(task_href)
            status = res.object.get('status')

    def destroy_node(self, node):
        node_path = get_url_path(node.id)
        # blindly poweroff node, it will throw an exception if already off
        try:
            res = self.connection.request('%s/power/action/poweroff'
                                          % node_path,
                                          method='POST')
            self._wait_for_task_completion(res.object.get('href'))
        except Exception:
            pass

        try:
            res = self.connection.request('%s/action/undeploy' % node_path,
                                          method='POST')
            self._wait_for_task_completion(res.object.get('href'))
        except ExpatError:
            # The undeploy response is malformed XML atm.
            # We can remove this whent he providers fix the problem.
            pass
        except Exception:
            # Some vendors don't implement undeploy at all yet,
            # so catch this and move on.
            pass

        res = self.connection.request(node_path, method='DELETE')
        return res.status == 202

    def reboot_node(self, node):
        res = self.connection.request('%s/power/action/reset'
                                      % get_url_path(node.id),
                                      method='POST')
        return res.status == 202 or res.status == 204

    def list_nodes(self):
        nodes = []
        for vdc in self.vdcs:
            res = self.connection.request(vdc)
            elms = res.object.findall(fixxpath(
                res.object, "ResourceEntities/ResourceEntity")
            )
            vapps = [
                (i.get('name'), get_url_path(i.get('href')))
                for i in elms
                if i.get('type')
                    == 'application/vnd.vmware.vcloud.vApp+xml'
                    and i.get('name')
            ]

            for vapp_name, vapp_href in vapps:
                res = self.connection.request(
                    vapp_href,
                    headers={
                        'Content-Type':
                            'application/vnd.vmware.vcloud.vApp+xml'
                    }
                )
                nodes.append(self._to_node(vapp_name, res.object))

        return nodes

    def _to_size(self, ram):
        ns = NodeSize(
            id=None,
            name="%s Ram" % ram,
            ram=ram,
            disk=None,
            bandwidth=None,
            price=None,
            driver=self.connection.driver
        )
        return ns

    def list_sizes(self, location=None):
        sizes = [self._to_size(i) for i in VIRTUAL_MEMORY_VALS]
        return sizes

    def _get_catalogitems_hrefs(self, catalog):
        """Given a catalog href returns contained catalog item hrefs"""
        res = self.connection.request(
            catalog,
            headers={
                'Content-Type':
                    'application/vnd.vmware.vcloud.catalog+xml'
            }
        ).object

        cat_items = res.findall(fixxpath(res, "CatalogItems/CatalogItem"))
        cat_item_hrefs = [i.get('href')
                          for i in cat_items
                          if i.get('type') ==
                              'application/vnd.vmware.vcloud.catalogItem+xml']

        return cat_item_hrefs

    def _get_catalogitem(self, catalog_item):
        """Given a catalog item href returns elementree"""
        res = self.connection.request(
            catalog_item,
            headers={
                'Content-Type':
                    'application/vnd.vmware.vcloud.catalogItem+xml'
            }
        ).object

        return res

    def list_images(self, location=None):
        images = []
        for vdc in self.vdcs:
            res = self.connection.request(vdc).object
            res_ents = res.findall(fixxpath(
                res, "ResourceEntities/ResourceEntity")
            )
            images += [
                self._to_image(i)
                for i in res_ents
                if i.get('type') ==
                    'application/vnd.vmware.vcloud.vAppTemplate+xml'
            ]

        for catalog in self._get_catalog_hrefs():
            for cat_item in self._get_catalogitems_hrefs(catalog):
                res = self._get_catalogitem(cat_item)
                res_ents = res.findall(fixxpath(res, 'Entity'))
                images += [
                    self._to_image(i)
                    for i in res_ents
                    if i.get('type') ==
                        'application/vnd.vmware.vcloud.vAppTemplate+xml'
                ]

        return images

    def create_node(self, **kwargs):
        """Creates and returns node.


        See L{NodeDriver.create_node} for more keyword args.

        Non-standard optional keyword arguments:
        @keyword    ex_network: link to a "Network" e.g., "https://services.vcloudexpress.terremark.com/api/v0.8/network/7"
        @type       ex_network: C{string}

        @keyword    ex_vdc: link to a "VDC" e.g., "https://services.vcloudexpress.terremark.com/api/v0.8/vdc/1"
        @type       ex_vdc: C{string}

        @keyword    ex_cpus: number of virtual cpus (limit depends on provider)
        @type       ex_cpus: C{int}

        @keyword    row: ????
        @type       row: C{????}

        @keyword    group: ????
        @type       group: C{????}
        """
        name = kwargs['name']
        image = kwargs['image']
        size = kwargs['size']

        # Some providers don't require a network link
        try:
            network = kwargs.get('ex_network', self.networks[0].get('href'))
        except IndexError:
            network = ''

        password = None
        if kwargs.has_key('auth'):
            auth = kwargs['auth']
            if isinstance(auth, NodeAuthPassword):
                password = auth.password
            else:
                raise ValueError('auth must be of NodeAuthPassword type')

        instantiate_xml = InstantiateVAppXML(
            name=name,
            template=image.id,
            net_href=network,
            cpus=str(kwargs.get('ex_cpus', 1)),
            memory=str(size.ram),
            password=password,
            row=kwargs.get('ex_row', None),
            group=kwargs.get('ex_group', None)
        )

        # Instantiate VM and get identifier.
        res = self.connection.request(
            '%s/action/instantiateVAppTemplate'
                % kwargs.get('vdc', self.vdcs[0]),
            data=instantiate_xml.tostring(),
            method='POST',
            headers={
                'Content-Type':
                    'application/vnd.vmware.vcloud.instantiateVAppTemplateParams+xml'
            }
        )
        vapp_name = res.object.get('name')
        vapp_href = get_url_path(res.object.get('href'))

        # Deploy the VM from the identifier.
        res = self.connection.request('%s/action/deploy' % vapp_href,
                                      method='POST')

        self._wait_for_task_completion(res.object.get('href'))

        # Power on the VM.
        res = self.connection.request('%s/power/action/powerOn' % vapp_href,
                                      method='POST')

        res = self.connection.request(vapp_href)
        node = self._to_node(vapp_name, res.object)

        return node

    features = {"create_node": ["password"]}

class HostingComConnection(VCloudConnection):
    """
    vCloud connection subclass for Hosting.com
    """

    host = "vcloud.safesecureweb.com"

    def _get_auth_headers(self):
        """hosting.com doesn't follow the standard vCloud authentication API"""
        return {
            'Authentication':
                base64.b64encode('%s:%s' % (self.user_id, self.key)),
            'Content-Length': 0
        }

class HostingComDriver(VCloudNodeDriver):
    """
    vCloud node driver for Hosting.com
    """
    connectionCls = HostingComConnection

class TerremarkConnection(VCloudConnection):
    """
    vCloud connection subclass for Terremark
    """

    host = "services.vcloudexpress.terremark.com"

class TerremarkDriver(VCloudNodeDriver):
    """
    vCloud node driver for Terremark
    """

    connectionCls = TerremarkConnection

    def list_locations(self):
        return [NodeLocation(0, "Terremark Texas", 'US', self)]

########NEW FILE########
__FILENAME__ = voxel
# Licensed to the Apache Software Foundation (ASF) under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Voxel VoxCloud driver
"""
import datetime
import hashlib

from xml.etree import ElementTree as ET

from libcloud.common.base import Response, ConnectionUserAndKey
from libcloud.common.types import InvalidCredsError
from libcloud.compute.providers import Provider
from libcloud.compute.types import NodeState
from libcloud.compute.base import Node, NodeDriver
from libcloud.compute.base import NodeSize, NodeImage, NodeLocation

VOXEL_API_HOST = "api.voxel.net"

class VoxelResponse(Response):

    def __init__(self, response):
        self.parsed = None
        super(VoxelResponse, self).__init__(response)

    def parse_body(self):
        if not self.body:
            return None
        if not self.parsed:
            self.parsed = ET.XML(self.body)
        return self.parsed

    def parse_error(self):
        err_list = []
        if not self.body:
            return None
        if not self.parsed:
            self.parsed = ET.XML(self.body)
        for err in self.parsed.findall('err'):
            code = err.get('code')
            err_list.append("(%s) %s" % (code, err.get('msg')))
            # From voxel docs:
            # 1: Invalid login or password
            # 9: Permission denied: user lacks access rights for this method
            if code == "1" or code == "9":
                # sucks, but only way to detect
                # bad authentication tokens so far
                raise InvalidCredsError(err_list[-1])
        return "\n".join(err_list)

    def success(self):
        if not self.parsed:
            self.parsed = ET.XML(self.body)
        stat = self.parsed.get('stat')
        if stat != "ok":
            return False
        return True

class VoxelConnection(ConnectionUserAndKey):
    """
    Connection class for the Voxel driver
    """

    host = VOXEL_API_HOST
    responseCls = VoxelResponse

    def add_default_params(self, params):
        params["key"] = self.user_id
        params["timestamp"] = datetime.datetime.utcnow().isoformat()+"+0000"

        for param in params.keys():
            if params[param] is None:
                del params[param]

        keys = params.keys()
        keys.sort()

        md5 = hashlib.md5()
        md5.update(self.key)
        for key in keys:
            if params[key]:
                if not params[key] is None:
                    md5.update("%s%s"% (key, params[key]))
                else:
                    md5.update(key)
        params['api_sig'] = md5.hexdigest()
        return params

VOXEL_INSTANCE_TYPES = {}
RAM_PER_CPU = 2048

NODE_STATE_MAP = {
    'IN_PROGRESS': NodeState.PENDING,
    'QUEUED': NodeState.PENDING,
    'SUCCEEDED': NodeState.RUNNING,
    'shutting-down': NodeState.TERMINATED,
    'terminated': NodeState.TERMINATED,
    'unknown': NodeState.UNKNOWN,
}

class VoxelNodeDriver(NodeDriver):
    """
    Voxel VoxCLOUD node driver
    """

    connectionCls = VoxelConnection
    type = Provider.VOXEL
    name = 'Voxel VoxCLOUD'

    def _initialize_instance_types():
        for cpus in range(1,14):
            if cpus == 1:
                name = "Single CPU"
            else:
                name = "%d CPUs" % cpus
            id = "%dcpu" % cpus
            ram = cpus * RAM_PER_CPU

            VOXEL_INSTANCE_TYPES[id]= {
                         'id': id,
                         'name': name,
                         'ram': ram,
                         'disk': None,
                         'bandwidth': None,
                         'price': None}

    features = {"create_node": [],
                "list_sizes":  ["variable_disk"]}

    _initialize_instance_types()

    def list_nodes(self):
        params = {"method": "voxel.devices.list"}
        result = self.connection.request('/', params=params).object
        return self._to_nodes(result)

    def list_sizes(self, location=None):
        return [ NodeSize(driver=self.connection.driver, **i)
                 for i in VOXEL_INSTANCE_TYPES.values() ]

    def list_images(self, location=None):
        params = {"method": "voxel.images.list"}
        result = self.connection.request('/', params=params).object
        return self._to_images(result)

    def create_node(self, **kwargs):
        """Create Voxel Node

        @keyword name: the name to assign the node (mandatory)
        @type    name: C{str}

        @keyword image: distribution to deploy
        @type    image: L{NodeImage}

        @keyword size: the plan size to create (mandatory)
                       Requires size.disk (GB) to be set manually
        @type    size: L{NodeSize}

        @keyword location: which datacenter to create the node in
        @type    location: L{NodeLocation}

        @keyword ex_privateip: Backend IP address to assign to node;
                               must be chosen from the customer's
                               private VLAN assignment.
        @type    ex_privateip: C{str}

        @keyword ex_publicip: Public-facing IP address to assign to node;
                              must be chosen from the customer's
                              public VLAN assignment.
        @type    ex_publicip: C{str}

        @keyword ex_rootpass: Password for root access; generated if unset.
        @type    ex_rootpass: C{str}

        @keyword ex_consolepass: Password for remote console;
                                 generated if unset.
        @type    ex_consolepass: C{str}

        @keyword ex_sshuser: Username for SSH access
        @type    ex_sshuser: C{str}

        @keyword ex_sshpass: Password for SSH access; generated if unset.
        @type    ex_sshpass: C{str}

        @keyword ex_voxel_access: Allow access Voxel administrative access.
                                  Defaults to False.
        @type    ex_voxel_access: C{bool}
        """

        # assert that disk > 0
        if not kwargs["size"].disk:
            raise ValueError("size.disk must be non-zero")

        # convert voxel_access to string boolean if needed
        voxel_access = kwargs.get("ex_voxel_access", None)
        if voxel_access is not None:
            voxel_access = "true" if voxel_access else "false"

        params = {
            'method':           'voxel.voxcloud.create',
            'hostname':         kwargs["name"],
            'disk_size':        int(kwargs["size"].disk),
            'facility':         kwargs["location"].id,
            'image_id':         kwargs["image"].id,
            'processing_cores': kwargs["size"].ram / RAM_PER_CPU,
            'backend_ip':       kwargs.get("ex_privateip", None),
            'frontend_ip':      kwargs.get("ex_publicip", None),
            'admin_password':   kwargs.get("ex_rootpass", None),
            'console_password': kwargs.get("ex_consolepass", None),
            'ssh_username':     kwargs.get("ex_sshuser", None),
            'ssh_password':     kwargs.get("ex_sshpass", None),
            'voxel_access':     voxel_access,
        }

        object = self.connection.request('/', params=params).object

        if self._getstatus(object):
            return Node(
                id = object.findtext("device/id"),
                name = kwargs["name"],
                state = NODE_STATE_MAP[object.findtext("device/status")],
                public_ip = kwargs.get("publicip", None),
                private_ip = kwargs.get("privateip", None),
                driver = self.connection.driver
            )
        else:
            return None

    def reboot_node(self, node):
        """
        Reboot the node by passing in the node object
        """
        params = {'method': 'voxel.devices.power',
                  'device_id': node.id,
                  'power_action': 'reboot'}
        return self._getstatus(self.connection.request('/', params=params).object)

    def destroy_node(self, node):
        """
        Destroy node by passing in the node object
        """
        params = {'method': 'voxel.voxcloud.delete',
                  'device_id': node.id}
        return self._getstatus(self.connection.request('/', params=params).object)

    def list_locations(self):
        params = {"method": "voxel.voxcloud.facilities.list"}
        result = self.connection.request('/', params=params).object
        nodes = self._to_locations(result)
        return nodes

    def _getstatus(self, element):
        status = element.attrib["stat"]
        return status == "ok"


    def _to_locations(self, object):
        return [NodeLocation(element.attrib["label"],
                             element.findtext("description"),
                             element.findtext("description"),
                             self)
                for element in object.findall('facilities/facility')]

    def _to_nodes(self, object):
        nodes = []
        for element in object.findall('devices/device'):
            if element.findtext("type") == "Virtual Server":
                try:
                    state = self.NODE_STATE_MAP[element.attrib['status']]
                except KeyError:
                    state = NodeState.UNKNOWN

                public_ip = private_ip = None
                ipassignments = element.findall("ipassignments/ipassignment")
                for ip in ipassignments:
                    if ip.attrib["type"] =="frontend":
                        public_ip = ip.text
                    elif ip.attrib["type"] == "backend":
                        private_ip = ip.text

                nodes.append(Node(id= element.attrib['id'],
                                 name=element.attrib['label'],
                                 state=state,
                                 public_ip= public_ip,
                                 private_ip= private_ip,
                                 driver=self.connection.driver))
        return nodes

    def _to_images(self, object):
        images = []
        for element in object.findall("images/image"):
            images.append(NodeImage(id = element.attrib["id"],
                                    name = element.attrib["summary"],
                                    driver = self.connection.driver))
        return images

########NEW FILE########
__FILENAME__ = vpsnet
# Licensed to the Apache Software Foundation (ASF) under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""
VPS.net driver
"""
import base64

try:
    import json
except:
    import simplejson as json

from libcloud.common.base import ConnectionUserAndKey, Response
from libcloud.common.types import InvalidCredsError
from libcloud.compute.providers import Provider
from libcloud.compute.types import NodeState
from libcloud.compute.base import Node, NodeDriver
from libcloud.compute.base import NodeSize, NodeImage, NodeLocation

API_HOST = 'api.vps.net'
API_VERSION = 'api10json'

RAM_PER_NODE = 256
DISK_PER_NODE = 10
BANDWIDTH_PER_NODE = 250
PRICE_PER_NODE = {1: 20,
                  2: 19,
                  3: 18,
                  4: 17,
                  5: 16,
                  6: 15,
                  7: 14,
                  15: 13,
                  30: 12,
                  60: 11,
                  100: 10}

class VPSNetResponse(Response):

    def parse_body(self):
        try:
            js = json.loads(self.body)
            return js
        except ValueError:
            return self.body

    def success(self):
        # vps.net wrongly uses 406 for invalid auth creds
        if self.status == 406 or self.status == 403:
            raise InvalidCredsError()
        return True

    def parse_error(self):
        try:
            errors = json.loads(self.body)['errors'][0]
        except ValueError:
            return self.body
        else:
            return "\n".join(errors)

class VPSNetConnection(ConnectionUserAndKey):
    """
    Connection class for the VPS.net driver
    """

    host = API_HOST
    responseCls = VPSNetResponse

    def add_default_headers(self, headers):
        user_b64 = base64.b64encode('%s:%s' % (self.user_id, self.key))
        headers['Authorization'] = 'Basic %s' % (user_b64)
        return headers

class VPSNetNodeDriver(NodeDriver):
    """
    VPS.net node driver
    """

    type = Provider.VPSNET
    name = "vps.net"
    connectionCls = VPSNetConnection

    def _to_node(self, vm):
        if vm['running']:
            state = NodeState.RUNNING
        else:
            state = NodeState.PENDING

        n = Node(id=vm['id'],
                 name=vm['label'],
                 state=state,
                 public_ip=[vm.get('primary_ip_address', None)],
                 private_ip=[],
                 extra={'slices_count':vm['slices_count']}, # Number of nodes consumed by VM
                 driver=self.connection.driver)
        return n

    def _to_image(self, image, cloud):
        image = NodeImage(id=image['id'],
                          name="%s: %s" % (cloud, image['label']),
                          driver=self.connection.driver)

        return image

    def _to_size(self, num):
        size = NodeSize(id=num,
                        name="%d Node" % (num,),
                        ram=RAM_PER_NODE * num,
                        disk=DISK_PER_NODE,
                        bandwidth=BANDWIDTH_PER_NODE * num,
                        price=self._get_price_per_node(num) * num,
                        driver=self.connection.driver)
        return size

    def _get_price_per_node(self, num):
        keys = sorted(PRICE_PER_NODE.keys())

        if num >= max(keys):
            return PRICE_PER_NODE[keys[-1]]

        for i in range(0,len(keys)):
            if keys[i] <= num < keys[i+1]:
                return PRICE_PER_NODE[keys[i]]

    def create_node(self, name, image, size, **kwargs):
        """Create a new VPS.net node

        See L{NodeDriver.create_node} for more keyword args.
        @keyword    ex_backups_enabled: Enable automatic backups
        @type       ex_backups_enabled: C{bool}

        @keyword    ex_fqdn:   Fully Qualified domain of the node
        @type       ex_fqdn:   C{string}
        """
        headers = {'Content-Type': 'application/json'}
        request = {'virtual_machine':
                        {'label': name,
                         'fqdn': kwargs.get('ex_fqdn', ''),
                         'system_template_id': image.id,
                         'backups_enabled': kwargs.get('ex_backups_enabled', 0),
                         'slices_required': size.id}}

        res = self.connection.request('/virtual_machines.%s' % (API_VERSION,),
                                    data=json.dumps(request),
                                    headers=headers,
                                    method='POST')
        node = self._to_node(res.object['virtual_machine'])
        return node

    def reboot_node(self, node):
        res = self.connection.request('/virtual_machines/%s/%s.%s' %
                                        (node.id, 'reboot', API_VERSION),
                                        method="POST")
        node = self._to_node(res.object['virtual_machine'])
        return True

    def list_sizes(self, location=None):
        res = self.connection.request('/nodes.%s' % (API_VERSION,))
        available_nodes = len([size for size in res.object
                            if size['slice']['virtual_machine_id']])
        sizes = [self._to_size(i) for i in range(1, available_nodes + 1)]
        return sizes

    def destroy_node(self, node):
        res = self.connection.request('/virtual_machines/%s.%s'
                                      % (node.id, API_VERSION),
                                      method='DELETE')
        return res.status == 200

    def list_nodes(self):
        res = self.connection.request('/virtual_machines.%s' % (API_VERSION,))
        return [self._to_node(i['virtual_machine']) for i in res.object]

    def list_images(self, location=None):
        res = self.connection.request('/available_clouds.%s' % (API_VERSION,))

        images = []
        for cloud in res.object:
            label = cloud['cloud']['label']
            templates = cloud['cloud']['system_templates']
            images.extend([self._to_image(image, label)
                           for image in templates])

        return images

    def list_locations(self):
        return [NodeLocation(0, "VPS.net Western US", 'US', self)]

########NEW FILE########
__FILENAME__ = providers
# Licensed to the Apache Software Foundation (ASF) under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""
Provider related utilities
"""

from libcloud.utils import get_driver as get_provider_driver
from libcloud.compute.types import Provider

DRIVERS = {
    Provider.DUMMY:
        ('libcloud.compute.drivers.dummy', 'DummyNodeDriver'),
    Provider.EC2_US_EAST:
        ('libcloud.compute.drivers.ec2', 'EC2NodeDriver'),
    Provider.EC2_EU_WEST:
        ('libcloud.compute.drivers.ec2', 'EC2EUNodeDriver'),
    Provider.EC2_US_WEST:
        ('libcloud.compute.drivers.ec2', 'EC2USWestNodeDriver'),
    Provider.EC2_AP_SOUTHEAST:
        ('libcloud.compute.drivers.ec2', 'EC2APSENodeDriver'),
    Provider.EC2_AP_NORTHEAST:
        ('libcloud.compute.drivers.ec2', 'EC2APNENodeDriver'),
    Provider.ECP:
        ('libcloud.compute.drivers.ecp', 'ECPNodeDriver'),
    Provider.ELASTICHOSTS_UK1:
        ('libcloud.compute.drivers.elastichosts', 'ElasticHostsUK1NodeDriver'),
    Provider.ELASTICHOSTS_UK2:
        ('libcloud.compute.drivers.elastichosts', 'ElasticHostsUK2NodeDriver'),
    Provider.ELASTICHOSTS_US1:
        ('libcloud.compute.drivers.elastichosts', 'ElasticHostsUS1NodeDriver'),
    Provider.CLOUDSIGMA:
        ('libcloud.compute.drivers.cloudsigma', 'CloudSigmaZrhNodeDriver'),
    Provider.GOGRID:
        ('libcloud.compute.drivers.gogrid', 'GoGridNodeDriver'),
    Provider.RACKSPACE:
        ('libcloud.compute.drivers.rackspace', 'RackspaceNodeDriver'),
    Provider.RACKSPACE_UK:
        ('libcloud.compute.drivers.rackspace', 'RackspaceUKNodeDriver'),
    Provider.SLICEHOST:
        ('libcloud.compute.drivers.slicehost', 'SlicehostNodeDriver'),
    Provider.VPSNET:
        ('libcloud.compute.drivers.vpsnet', 'VPSNetNodeDriver'),
    Provider.LINODE:
        ('libcloud.compute.drivers.linode', 'LinodeNodeDriver'),
    Provider.RIMUHOSTING:
        ('libcloud.compute.drivers.rimuhosting', 'RimuHostingNodeDriver'),
    Provider.VOXEL:
        ('libcloud.compute.drivers.voxel', 'VoxelNodeDriver'),
    Provider.SOFTLAYER:
        ('libcloud.compute.drivers.softlayer', 'SoftLayerNodeDriver'),
    Provider.EUCALYPTUS:
        ('libcloud.compute.drivers.ec2', 'EucNodeDriver'),
    Provider.IBM:
        ('libcloud.compute.drivers.ibm_sbc', 'IBMNodeDriver'),
    Provider.OPENNEBULA:
        ('libcloud.compute.drivers.opennebula', 'OpenNebulaNodeDriver'),
    Provider.DREAMHOST:
        ('libcloud.compute.drivers.dreamhost', 'DreamhostNodeDriver'),
    Provider.BRIGHTBOX:
        ('libcloud.compute.drivers.brightbox', 'BrightboxNodeDriver'),
}

def get_driver(provider):
    return get_provider_driver(DRIVERS, provider)

########NEW FILE########
__FILENAME__ = ssh
# Licensed to the Apache Software Foundation (ASF) under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Wraps multiple ways to communicate over SSH
"""
have_paramiko = False

try:
    import paramiko
    have_paramiko = True
except ImportError:
    pass

# Depending on your version of Paramiko, it may cause a deprecation
# warning on Python 2.6.
# Ref: https://bugs.launchpad.net/paramiko/+bug/392973

from os.path import split as psplit

class BaseSSHClient(object):
    """
    Base class representing a connection over SSH/SCP to a remote node.
    """

    def __init__(self, hostname, port=22, username='root', password=None, key=None):
        """
        @type hostname: C{str}
        @keyword hostname: Hostname or IP address to connect to.

        @type port: C{int}
        @keyword port: TCP port to communicate on, defaults to 22.

        @type username: C{str}
        @keyword username: Username to use, defaults to root.

        @type password: C{str}
        @keyword password: Password to authenticate with.

        @type key: C{list}
        @keyword key: Private SSH keys to authenticate with.
        """
        self.hostname = hostname
        self.port = port
        self.username = username
        self.password = password
        self.key = key

    def connect(self):
        """
        Connect to the remote node over SSH.

        @return: C{bool}
        """
        raise NotImplementedError, \
            'connect not implemented for this ssh client'

    def put(self, path, contents=None, chmod=None):
        """
        Upload a file to the remote node.

        @type path: C{str}
        @keyword path: File path on the remote node.

        @type contents: C{str}
        @keyword contents: File Contents.

        @type chmod: C{int}
        @keyword chmod: chmod file to this after creation.
        """
        raise NotImplementedError, \
            'put not implemented for this ssh client'

    def delete(self, path):
        """
        Delete/Unlink a file on the remote node.

        @type path: C{str}
        @keyword path: File path on the remote node.
        """
        raise NotImplementedError, \
            'delete not implemented for this ssh client'

    def run(self, cmd):
        """
        Run a command on a remote node.

        @type cmd: C{str}
        @keyword cmd: Command to run.
        
        @return C{list} of [stdout, stderr, exit_status]
        """
        raise NotImplementedError, \
            'run not implemented for this ssh client'

    def close(self):
        """
        Shutdown connection to the remote node.
        """
        raise NotImplementedError, \
            'close not implemented for this ssh client'

class ParamikoSSHClient(BaseSSHClient):
    """
    A SSH Client powered by Paramiko.
    """
    def __init__(self, hostname, port=22, username='root', password=None, key=None):
        super(ParamikoSSHClient, self).__init__(hostname, port, username, password, key)
        self.client = paramiko.SSHClient()
        self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    def connect(self):
        conninfo = {'hostname': self.hostname,
                    'port': self.port,
                    'username': self.username,
                    'password': self.password,
                    'allow_agent': False,
                    'look_for_keys': False}
        self.client.connect(**conninfo)
        return True

    def put(self, path, contents=None, chmod=None):
        sftp = self.client.open_sftp()
        # less than ideal, but we need to mkdir stuff otherwise file() fails
        head, tail = psplit(path)
        if path[0] == "/":
            sftp.chdir("/")
        for part in head.split("/"):
            if part != "":
                try:
                    sftp.mkdir(part)
                except IOError:
                    # so, there doesn't seem to be a way to
                    # catch EEXIST consistently *sigh*
                    pass
                sftp.chdir(part)
        ak = sftp.file(tail,  mode='w')
        ak.write(contents)
        if chmod is not None:
            ak.chmod(chmod)
        ak.close()
        sftp.close()

    def delete(self, path):
        sftp = self.client.open_sftp()
        sftp.unlink(path)
        sftp.close()

    def run(self, cmd):
        # based on exec_command()
        bufsize = -1
        t =  self.client.get_transport()
        chan = t.open_session()
        chan.exec_command(cmd)
        stdin = chan.makefile('wb', bufsize)
        stdout = chan.makefile('rb', bufsize)
        stderr = chan.makefile_stderr('rb', bufsize)
        #stdin, stdout, stderr = self.client.exec_command(cmd)
        stdin.close()
        status = chan.recv_exit_status()
        so = stdout.read()
        se = stderr.read()
        return [so, se, status]

    def close(self):
        self.client.close()

class ShellOutSSHClient(BaseSSHClient):
    # TODO: write this one
    pass

SSHClient = ParamikoSSHClient
if not have_paramiko:
    SSHClient = ShellOutSSHClient

########NEW FILE########
__FILENAME__ = types
# Licensed to the Apache Software Foundation (ASF) under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""
Base types used by other parts of libcloud
"""

from libcloud.common.types import LibcloudError, MalformedResponseError
from libcloud.common.types import InvalidCredsError, InvalidCredsException

class Provider(object):
    """
    Defines for each of the supported providers

    @cvar DUMMY: Example provider
    @cvar EC2_US_EAST: Amazon AWS US N. Virgina
    @cvar EC2_US_WEST: Amazon AWS US N. California
    @cvar EC2_EU_WEST: Amazon AWS EU Ireland
    @cvar RACKSPACE: Rackspace Cloud Servers
    @cvar RACKSPACE_UK: Rackspace UK Cloud Servers
    @cvar SLICEHOST: Slicehost.com
    @cvar GOGRID: GoGrid
    @cvar VPSNET: VPS.net
    @cvar LINODE: Linode.com
    @cvar VCLOUD: vmware vCloud
    @cvar RIMUHOSTING: RimuHosting.com
    @cvar ECP: Enomaly
    @cvar IBM: IBM Developer Cloud
    @cvar OPENNEBULA: OpenNebula.org
    @cvar DREAMHOST: DreamHost Private Server
    @cvar CLOUDSIGMA: CloudSigma
    """
    DUMMY = 0
    EC2 = 1  # deprecated name
    EC2_US_EAST = 1
    EC2_EU = 2 # deprecated name
    EC2_EU_WEST = 2
    RACKSPACE = 3
    SLICEHOST = 4
    GOGRID = 5
    VPSNET = 6
    LINODE = 7
    VCLOUD = 8
    RIMUHOSTING = 9
    EC2_US_WEST = 10
    VOXEL = 11
    SOFTLAYER = 12
    EUCALYPTUS = 13
    ECP = 14
    IBM = 15
    OPENNEBULA = 16
    DREAMHOST = 17
    ELASTICHOSTS = 18
    ELASTICHOSTS_UK1 = 19
    ELASTICHOSTS_UK2 = 20
    ELASTICHOSTS_US1 = 21
    EC2_AP_SOUTHEAST = 22
    RACKSPACE_UK = 23
    BRIGHTBOX = 24
    CLOUDSIGMA = 25
    EC2_AP_NORTHEAST = 26

class NodeState(object):
    """
    Standard states for a node

    @cvar RUNNING: Node is running
    @cvar REBOOTING: Node is rebooting
    @cvar TERMINATED: Node is terminated
    @cvar PENDING: Node is pending
    @cvar UNKNOWN: Node state is unknown
    """
    RUNNING = 0
    REBOOTING = 1
    TERMINATED = 2
    PENDING = 3
    UNKNOWN = 4

class DeploymentError(LibcloudError):
    """
    Exception used when a Deployment Task failed.

    @ivar node: L{Node} on which this exception happened, you might want to call L{Node.destroy}
    """
    def __init__(self, node, original_exception=None):
        self.node = node
        self.value = original_exception
    def __str__(self):
        return repr(self.value)

"""Deprecated alias of L{DeploymentException}"""
DeploymentException = DeploymentError

########NEW FILE########
__FILENAME__ = deployment
# Licensed to the Apache Software Foundation (ASF) under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from libcloud.utils import deprecated_warning
from libcloud.compute.deployment import *

deprecated_warning(__name__)

########NEW FILE########
__FILENAME__ = brightbox
# Licensed to the Apache Software Foundation (ASF) under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from libcloud.utils import deprecated_warning
from libcloud.compute.drivers.brightbox import *

deprecated_warning(__name__)

########NEW FILE########
__FILENAME__ = cloudsigma
# -*- coding: utf-8 -*-
# Licensed to the Apache Software Foundation (ASF) under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from libcloud.utils import deprecated_warning
from libcloud.compute.drivers.cloudsigma import *

deprecated_warning(__name__)

########NEW FILE########
__FILENAME__ = dreamhost
# Licensed to the Apache Software Foundation (ASF) under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from libcloud.utils import deprecated_warning
from libcloud.compute.drivers.dreamhost import *

deprecated_warning(__name__)

########NEW FILE########
__FILENAME__ = dummy
# Licensed to the Apache Software Foundation (ASF) under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from libcloud.utils import deprecated_warning
from libcloud.compute.drivers.dummy import *

deprecated_warning(__name__)

########NEW FILE########
__FILENAME__ = ec2
# Licensed to the Apache Software Foundation (ASF) under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from libcloud.utils import deprecated_warning
from libcloud.compute.drivers.ec2 import *

deprecated_warning(__name__)

########NEW FILE########
__FILENAME__ = ecp
# Licensed to the Apache Software Foundation (ASF) under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from libcloud.utils import deprecated_warning
from libcloud.compute.drivers.ecp import *

deprecated_warning(__name__)

########NEW FILE########
__FILENAME__ = elastichosts
# Licensed to the Apache Software Foundation (ASF) under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from libcloud.utils import deprecated_warning
from libcloud.compute.drivers.elastichosts import *

deprecated_warning(__name__)

########NEW FILE########
__FILENAME__ = gogrid
# Licensed to the Apache Software Foundation (ASF) under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from libcloud.utils import deprecated_warning
from libcloud.compute.drivers.gogrid import *

deprecated_warning(__name__)

########NEW FILE########
__FILENAME__ = ibm_sbc
# Licensed to the Apache Software Foundation (ASF) under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from libcloud.utils import deprecated_warning
from libcloud.compute.drivers.ibm_sbc import *

deprecated_warning(__name__)

########NEW FILE########
__FILENAME__ = linode
# Licensed to the Apache Software Foundation (ASF) under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from libcloud.utils import deprecated_warning
from libcloud.compute.drivers.linode import *

deprecated_warning(__name__)

########NEW FILE########
__FILENAME__ = opennebula
# Copyright 2002-2009, Distributed Systems Architecture Group, Universidad
# Complutense de Madrid (dsa-research.org)
#
# Licensed to the Apache Software Foundation (ASF) under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from libcloud.utils import deprecated_warning
from libcloud.compute.drivers.opennebula import *

deprecated_warning(__name__)

########NEW FILE########
__FILENAME__ = rackspace
# Licensed to the Apache Software Foundation (ASF) under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from libcloud.utils import deprecated_warning
from libcloud.compute.drivers.rackspace import *

deprecated_warning(__name__)

########NEW FILE########
__FILENAME__ = rimuhosting
# Licensed to the Apache Software Foundation (ASF) under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from libcloud.utils import deprecated_warning
from libcloud.compute.drivers.rimuhosting import *

deprecated_warning(__name__)

########NEW FILE########
__FILENAME__ = slicehost
# Licensed to the Apache Software Foundation (ASF) under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from libcloud.utils import deprecated_warning
from libcloud.compute.drivers.slicehost import *

deprecated_warning(__name__)

########NEW FILE########
__FILENAME__ = softlayer
# Licensed to the Apache Software Foundation (ASF) under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from libcloud.utils import deprecated_warning
from libcloud.compute.drivers.softlayer import *

deprecated_warning(__name__)

########NEW FILE########
__FILENAME__ = vcloud
# Licensed to the Apache Software Foundation (ASF) under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from libcloud.utils import deprecated_warning
from libcloud.compute.drivers.vcloud import *

deprecated_warning(__name__)

########NEW FILE########
__FILENAME__ = voxel
# Licensed to the Apache Software Foundation (ASF) under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from libcloud.utils import deprecated_warning
from libcloud.compute.drivers.voxel import *

deprecated_warning(__name__)

########NEW FILE########
__FILENAME__ = vpsnet
# Licensed to the Apache Software Foundation (ASF) under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from libcloud.utils import deprecated_warning
from libcloud.compute.drivers.vpsnet import *

deprecated_warning(__name__)

########NEW FILE########
__FILENAME__ = httplib_ssl
# Licensed to the Apache Software Foundation (ASF) under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""
Subclass for httplib.HTTPSConnection with optional certificate name
verification, depending on libcloud.security settings.
"""
import httplib
import os
import re
import socket
import ssl
import warnings

import libcloud.security

class LibcloudHTTPSConnection(httplib.HTTPSConnection):
    """LibcloudHTTPSConnection

    Subclass of HTTPSConnection which verifies certificate names
    if and only if CA certificates are available.
    """
    verify = False        # does not verify
    ca_cert = None        # no default CA Certificate

    def __init__(self, *args, **kwargs):
        """Constructor
        """
        self._setup_verify()
        httplib.HTTPSConnection.__init__(self, *args, **kwargs)

    def _setup_verify(self):
        """Setup Verify SSL or not

        Reads security module's VERIFY_SSL_CERT and toggles whether
        the class overrides the connect() class method or runs the
        inherited httplib.HTTPSConnection connect()
        """
        self.verify = libcloud.security.VERIFY_SSL_CERT

        if self.verify:
            self._setup_ca_cert()
        else:
            warnings.warn(libcloud.security.VERIFY_SSL_DISABLED_MSG)

    def _setup_ca_cert(self):
        """Setup CA Certs

        Search in CA_CERTS_PATH for valid candidates and
        return first match.  Otherwise, complain about certs
        not being available.
        """
        if not self.verify:
            return

        ca_certs_available = [cert
                              for cert in libcloud.security.CA_CERTS_PATH
                              if os.path.exists(cert)]
        if ca_certs_available:
            # use first available certificate
            self.ca_cert = ca_certs_available[0]
        else:
            # no certificates found; toggle verify to False
            warnings.warn(libcloud.security.CA_CERTS_UNAVAILABLE_MSG)
            self.ca_cert = None
            self.verify = False

    def connect(self):
        """Connect

        Checks if verification is toggled; if not, just call
        httplib.HTTPSConnection's connect
        """
        if not self.verify:
            return httplib.HTTPSConnection.connect(self)

        # otherwise, create a connection and verify the hostname
        # use socket.create_connection (in 2.6+) if possible
        if getattr(socket, 'create_connection', None):
            sock = socket.create_connection((self.host, self.port),
                                            self.timeout)
        else:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((self.host, self.port))
        self.sock = ssl.wrap_socket(sock,
                                    self.key_file,
                                    self.cert_file,
                                    cert_reqs=ssl.CERT_REQUIRED,
                                    ca_certs=self.ca_cert,
                                    ssl_version=ssl.PROTOCOL_TLSv1)
        cert = self.sock.getpeercert()
        if not self._verify_hostname(self.host, cert):
            raise ssl.SSLError('Failed to verify hostname')

    def _verify_hostname(self, hostname, cert):
        """Verify hostname against peer cert

        Check both commonName and entries in subjectAltName, using a
        rudimentary glob to dns regex check to find matches
        """
        common_name = self._get_common_name(cert)
        alt_names = self._get_subject_alt_names(cert)

        # replace * with alphanumeric and dash
        # replace . with literal .
        valid_patterns = [
            re.compile(
                pattern.replace(
                    r".", r"\."
                ).replace(
                    r"*", r"[0-9A-Za-z]+"
                )
            )
            for pattern
            in (set(common_name) | set(alt_names))
        ]

        return any(
            pattern.search(hostname)
            for pattern in valid_patterns
        )

    def _get_subject_alt_names(self, cert):
        """Get SubjectAltNames

        Retrieve 'subjectAltName' attributes from cert data structure
        """
        if 'subjectAltName' not in cert:
            values = []
        else:
            values = [value
                      for field, value in cert['subjectAltName']
                      if field == 'DNS']
        return values

    def _get_common_name(self, cert):
        """Get Common Name

        Retrieve 'commonName' attribute from cert data structure
        """
        if 'subject' not in cert:
            return None
        values = [value[0][1]
                  for value in cert['subject']
                  if value[0][0] == 'commonName']
        return values

########NEW FILE########
__FILENAME__ = providers
# Licensed to the Apache Software Foundation (ASF) under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from libcloud.utils import deprecated_warning
from libcloud.compute.providers import *

deprecated_warning(__name__)

########NEW FILE########
__FILENAME__ = security
# Licensed to the Apache Software Foundation (ASF) under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""
Security (SSL) Settings

Usage:
    import libcloud.security
    libcloud.security.VERIFY_SSL_CERT = True

    # optional
    libcloud.security.CA_CERTS_PATH.append("/path/to/cacert.txt")
"""
# For backward compatibility this option is disabled by default
VERIFY_SSL_CERT = False

# File containing one or more PEM-encoded CA certificates
# concatenated together
CA_CERTS_PATH = [
    # centos/fedora: openssl
    '/etc/pki/tls/certs/ca-bundle.crt',

    # debian/ubuntu/arch/gentoo: ca-certificates
    '/etc/ssl/certs/ca-certificates.crt',

    # freebsd: ca_root_nss
    '/usr/local/share/certs/ca-root-nss.crt',

    # macports: curl-ca-bundle
    '/opt/local/share/curl/curl-ca-bundle.crt',
]

CA_CERTS_UNAVAILABLE_MSG = (
   'Warning: No CA Certificates were found in CA_CERTS_PATH. '
   'Toggling VERIFY_SSL_CERT to False.'
)

VERIFY_SSL_DISABLED_MSG = (
    'SSL certificate verification is disabled, this can pose a '
    'security risk. For more information how to enable the SSL '
    'certificate verification, please visit the libcloud '
    'documentation.'
)

########NEW FILE########
__FILENAME__ = ssh
# Licensed to the Apache Software Foundation (ASF) under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from libcloud.utils import deprecated_warning
from libcloud.compute.ssh import *

deprecated_warning(__name__)

########NEW FILE########
__FILENAME__ = base
# Licensed to the Apache Software Foundation (ASF) under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# Backward compatibility for Python 2.5
from __future__ import with_statement

import os
import os.path
import hashlib
from os.path import join as pjoin

from libcloud import utils
from libcloud.common.types import LibcloudError
from libcloud.common.base import ConnectionKey

CHUNK_SIZE = 8096

class Object(object):
    """
    Represents an object (BLOB).
    """

    def __init__(self, name, size, hash, extra, meta_data, container,
                 driver):
        """
        @type name: C{str}
        @param name: Object name (must be unique per container).

        @type size: C{int}
        @param size: Object size in bytes.

        @type hash: C{string}
        @param hash Object hash.

        @type container: C{Container}
        @param container: Object container.

        @type extra: C{dict}
        @param extra: Extra attributes.

        @type meta_data: C{dict}
        @param meta_data: Optional object meta data.

        @type driver: C{StorageDriver}
        @param driver: StorageDriver instance.
        """

        self.name = name
        self.size = size
        self.hash = hash
        self.container = container
        self.extra = extra or {}
        self.meta_data = meta_data or {}
        self.driver = driver

    def download(self, destination_path, overwrite_existing=False,
                 delete_on_failure=True):
        return self.driver.download_object(self, destination_path,
                                           overwrite_existing,
                                           delete_on_failure)

    def as_stream(self, chunk_size=None):
        return self.driver.download_object_as_stream(self, chunk_size)

    def delete(self):
        return self.driver.delete_object(self)

    def __repr__(self):
        return '<Object: name=%s, size=%s, hash=%s, provider=%s ...>' % \
        (self.name, self.size, self.hash, self.driver.name)

class Container(object):
    """
    Represents a container (bucket) which can hold multiple objects.
    """

    def __init__(self, name, extra, driver):
        """
        @type name: C{str}
        @param name: Container name (must be unique).

        @type extra: C{dict}
        @param extra: Extra attributes.

        @type driver: C{StorageDriver}
        @param driver: StorageDriver instance.
        """

        self.name = name
        self.extra = extra or {}
        self.driver = driver

    def list_objects(self):
        return self.driver.list_container_objects(self)

    def get_object(self, object_name):
        return self.driver.get_object(container_name=self.name,
                                      object_name=object_name)

    def upload_object(self, file_path, object_name, extra=None, file_hash=None):
        return self.driver.upload_object(file_path, self, object_name, extra, file_hash)

    def upload_object_via_stream(self, iterator, object_name, extra=None):
        return self.driver.upload_object_via_stream(iterator, self, object_name, extra)

    def download_object(self, obj, destination_path, overwrite_existing=False,
                        delete_on_failure=True):
        return self.driver.download_object(obj, destination_path)

    def download_object_as_stream(self, obj, chunk_size=None):
        return self.driver.download_object_as_stream(obj, chunk_size)

    def delete_object(self, obj):
        return self.driver.delete_object(obj)

    def delete(self):
        return self.driver.delete_container(self)

    def __repr__(self):
        return '<Container: name=%s, provider=%s>' % (self.name, self.driver.name)

class StorageDriver(object):
    """
    A base StorageDriver to derive from.
    """

    connectionCls = ConnectionKey
    name = None
    hash_type = 'md5'

    def __init__(self, key, secret=None, secure=True, host=None, port=None):
        self.key = key
        self.secret = secret
        self.secure = secure
        args = [self.key]

        if self.secret != None:
            args.append(self.secret)

        args.append(secure)

        if host != None:
            args.append(host)

        if port != None:
            args.append(port)

        self.connection = self.connectionCls(*args)

        self.connection.driver = self
        self.connection.connect()

    def get_meta_data(self):
        """
        Return account meta data - total number of containers, objects and
        number of bytes currently used.

        @return A C{dict} with account meta data.
        """
        raise NotImplementedError, \
            'get_account_meta_data not implemented for this driver'

    def list_containters(self):
        raise NotImplementedError, \
            'list_containers not implemented for this driver'

    def list_container_objects(self, container):
        """
        Return a list of objects for the given container.

        @type container: C{Container}
        @param container: Container instance

        @return A list of Object instances.
        """
        raise NotImplementedError, \
            'list_objects not implemented for this driver'

    def get_container(self, container_name):
        """
        Return a container instance.

        @type container_name: C{str}
        @param container_name: Container name.

        @return: C{Container} instance.
        """
        raise NotImplementedError, \
            'get_object not implemented for this driver'

    def get_object(self, container_name, object_name):
        """
        Return an object instance.

        @type container_name: C{str}
        @param container_name: Container name.

        @type object_name: C{str}
        @param object_name: Object name.

        @return: C{Object} instance.
        """
        raise NotImplementedError, \
            'get_object not implemented for this driver'

    def download_object(self, obj, destination_path, delete_on_failure=True):
        """
        Download an object to the specified destination path.

        @type obj; C{Object}
        @param obj: Object instance.

        @type destination_path: C{str}
        @type destination_path: Full path to a file or a directory where the
                                incoming file will be saved.

        @type overwrite_existing: C{bool}
        @type overwrite_existing: True to overwrite an existing file.

        @type delete_on_failure: C{bool}
        @param delete_on_failure: True to delete a partially downloaded file if
        the download was not successful (hash mismatch / file size).

        @return C{bool} True if an object has been successfully downloaded, False
        otherwise.
        """
        raise NotImplementedError, \
            'download_object not implemented for this driver'

    def download_object_as_stream(self, obj, chunk_size=None):
        """
        Return a generator which yields object data.

        @type obj: C{Object}
        @param obj: Object instance

        @type chunk_size: C{int}
        @param chunk_size: Optional chunk size (in bytes).
        """
        raise NotImplementedError, \
            'download_object_as_stream not implemented for this driver'

    def upload_object(self, file_path, container, object_name, extra=None,
                      file_hash=None):
        """
        Upload an object.

        @type file_path: C{str}
        @param file_path: Path to the object on disk.

        @type container: C{Container}
        @param container: Destination container.

        @type object_name: C{str}
        @param object_name: Object name.

        @type extra: C{dict}
        @param extra: (optional) Extra attributes (driver specific).

        @type file_hash: C{str}
        @param file_hash: (optional) File hash. If provided object hash is
                          on upload and if it doesn't match the one provided an
                          exception is thrown.
        """
        raise NotImplementedError, \
            'upload_object not implemented for this driver'

    def upload_object_via_stream(self, iterator, container, object_name, extra=None):
        """
        @type iterator: C{object}
        @param iterator: An object which implements the iterator interface.

        @type container: C{Container}
        @param container: Destination container.

        @type object_name: C{str}
        @param object_name: Object name.

        @type extra: C{dict}
        @param extra: (optional) Extra attributes (driver specific).
        """
        raise NotImplementedError, \
            'upload_object_via_stream not implemented for this driver'

    def delete_object(self, obj):
        """
        Delete an object.

        @type obj: C{Object}
        @param obj: Object instance.

        @return: C{bool} True on success.
        """
        raise NotImplementedError, \
            'delete_object not implemented for this driver'

    def create_container(self, container_name):
        """
        Create a new container.

        @type container_name: C{str}
        @param container_name: Container name.

        @return C{Container} instance on success.
        """
        raise NotImplementedError, \
            'create_container not implemented for this driver'

    def delete_container(self, container):
        """
        Delete a container.

        @type container: C{Container}
        @param container: Container instance

        @return C{bool} True on success, False otherwise.
        """
        raise NotImplementedError, \
            'delete_container not implemented for this driver'

    def _save_object(self, response, obj, destination_path,
                     overwrite_existing=False, delete_on_failure=True,
                     chunk_size=None):
        """
        Save object to the provided path.

        @type response: C{RawResponse}
        @param response: RawResponse instance.

        @type obj: C{Object}
        @param obj: Object instance.

        @type destination_path: C{Str}
        @param destination_path: Destination directory.

        @type delete_on_failure: C{bool}
        @param delete_on_failure: True to delete partially downloaded object if
                                  the download fails.
        @type overwrite_existing: C{bool}
        @param overwrite_existing: True to overwrite a local path if it already
                                   exists.

        @type chunk_size: C{int}
        @param chunk_size: Optional chunk size (defaults to CHUNK_SIZE)

        @return C{bool} True on success, False otherwise.
        """

        chunk_size = chunk_size or CHUNK_SIZE

        base_name = os.path.basename(destination_path)

        if not base_name and not os.path.exists(destination_path):
            raise LibcloudError(value='Path %s does not exist' % (destination_path),
                                driver=self)

        if not base_name:
            file_path = pjoin(destination_path, obj.name)
        else:
            file_path = destination_path

        if os.path.exists(file_path) and not overwrite_existing:
            raise LibcloudError(value='File %s already exists, but ' % (file_path) +
                                'overwrite_existing=False',
                                driver=self)

        stream = utils.read_in_chunks(response, chunk_size)

        try:
            data_read = stream.next()
        except StopIteration:
            # Empty response?
            return False

        bytes_transferred = 0

        with open(file_path, 'wb') as file_handle:
            while len(data_read) > 0:
                file_handle.write(data_read)
                bytes_transferred += len(data_read)

                try:
                    data_read = stream.next()
                except StopIteration:
                    data_read = ''

        if obj.size != bytes_transferred:
            # Transfer failed, support retry?
            if delete_on_failure:
                try:
                    os.unlink(file_path)
                except Exception:
                    pass

            return False

        return True

    def _stream_data(self, response, iterator, chunked=False,
                     calculate_hash=True, chunk_size=None):
        """
        Stream a data over an http connection.

        @type response: C{RawResponse}
        @param response: RawResponse object.

        @type iterator: C{}
        @param response: An object which implements an iterator interface
                         or a File like object with read method.

        @type chunk_size: C{int}
        @param chunk_size: Optional chunk size (defaults to CHUNK_SIZE)

        @return C{tuple} First item is a boolean indicator of success, second
                         one is the uploaded data MD5 hash and the third one
                         is the number of transferred bytes.
        """

        chunk_size = chunk_size or CHUNK_SIZE

        data_hash = None
        if calculate_hash:
            data_hash = hashlib.md5()

        generator = utils.read_in_chunks(iterator, chunk_size)

        bytes_transferred = 0
        try:
            chunk = generator.next()
        except StopIteration:
            # No data?
            return False, None, None

        while len(chunk) > 0:
            try:
                if chunked:
                    response.connection.connection.send('%X\r\n' %
                                                       (len(chunk)))
                    response.connection.connection.send(chunk)
                    response.connection.connection.send('\r\n')
                else:
                    response.connection.connection.send(chunk)
            except Exception, e:
                # Timeout, etc.
                return False, None, bytes_transferred

            bytes_transferred += len(chunk)
            if calculate_hash:
                data_hash.update(chunk)

            try:
                chunk = generator.next()
            except StopIteration:
                chunk = ''

        if chunked:
            response.connection.connection.send('0\r\n\r\n')

        if calculate_hash:
            data_hash = data_hash.hexdigest()

        return True, data_hash, bytes_transferred

    def _upload_file(self, response, file_path, chunked=False,
                     calculate_hash=True):
        """
        Upload a file to the server.

        @type response: C{RawResponse}
        @param response: RawResponse object.

        @type file_path: C{str}
        @param file_path: Path to a local file.

        @type iterator: C{}
        @param response: An object which implements an iterator interface (File
                         object, etc.)

        @return C{tuple} First item is a boolean indicator of success, second
                         one is the uploaded data MD5 hash and the third one
                         is the number of transferred bytes.
        """
        with open (file_path, 'rb') as file_handle:
            success, data_hash, bytes_transferred = \
                     self._stream_data(response=response,
                                       iterator=iter(file_handle),
                                       chunked=chunked,
                                       calculate_hash=calculate_hash)

        return success, data_hash, bytes_transferred

########NEW FILE########
__FILENAME__ = cloudfiles
# Licensed to the Apache Software Foundation (ASF) under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import httplib
import urlparse
import os.path
import urllib

try:
    import json
except:
    import simplejson as json

from libcloud import utils
from libcloud.common.types import MalformedResponseError, LibcloudError
from libcloud.common.types import InvalidCredsError
from libcloud.common.base import ConnectionUserAndKey, Response

from libcloud.storage.providers import Provider
from libcloud.storage.base import Object, Container, StorageDriver
from libcloud.storage.types import ContainerAlreadyExistsError
from libcloud.storage.types import ContainerDoesNotExistError
from libcloud.storage.types import ContainerIsNotEmptyError
from libcloud.storage.types import ObjectDoesNotExistError
from libcloud.storage.types import ObjectHashMismatchError
from libcloud.storage.types import InvalidContainerNameError

from libcloud.common.rackspace import AUTH_HOST_US, AUTH_HOST_UK, RackspaceBaseConnection

API_VERSION = 'v1.0'

class CloudFilesResponse(Response):

    valid_response_codes = [ httplib.NOT_FOUND, httplib.CONFLICT ]

    def success(self):
        i = int(self.status)
        return i >= 200 and i <= 299 or i in self.valid_response_codes

    def parse_body(self):
        if not self.body:
            return None

        if 'content-type' in self.headers:
            key = 'content-type'
        elif 'Content-Type' in self.headers:
            key = 'Content-Type'
        else:
            raise LibcloudError('Missing content-type header')

        content_type = self.headers[key]
        if content_type.find(';') != -1:
            content_type = content_type.split(';')[0]

        if content_type == 'application/json':
            try:
                data = json.loads(self.body)
            except:
                raise MalformedResponseError('Failed to parse JSON',
                                             body=self.body,
                                             driver=CloudFilesStorageDriver)
        elif content_type == 'text/plain':
            data = self.body
        else:
            data = self.body

        return data


class CloudFilesConnection(RackspaceBaseConnection):
    """
    Base connection class for the Cloudfiles driver.
    """

    responseCls = CloudFilesResponse
    auth_host = None
    _url_key = "storage_url"

    def __init__(self, user_id, key, secure=True):
        super(CloudFilesConnection, self).__init__(user_id, key, secure=secure)
        self.api_version = API_VERSION
        self.accept_format = 'application/json'

    def request(self, action, params=None, data='', headers=None, method='GET',
                raw=False):
        if not headers:
            headers = {}
        if not params:
            params = {}
        # Due to first-run authentication request, we may not have a path
        if self.request_path:
            action = self.request_path + action
            params['format'] = 'json'
        if method in [ 'POST', 'PUT' ]:
            headers = {'Content-Type': 'application/json; charset=UTF-8'}

        return super(CloudFilesConnection, self).request(
            action=action,
            params=params, data=data,
            method=method, headers=headers,
            raw=raw
        )


class CloudFilesUSConnection(CloudFilesConnection):
    """
    Connection class for the Cloudfiles US endpoint.
    """

    auth_host = AUTH_HOST_US


class CloudFilesUKConnection(CloudFilesConnection):
    """
    Connection class for the Cloudfiles UK endpoint.
    """

    auth_host = AUTH_HOST_UK


class CloudFilesStorageDriver(StorageDriver):
    """
    Base CloudFiles driver.

    You should never create an instance of this class directly but use US/US
    class.
    """
    name = 'CloudFiles'
    connectionCls = CloudFilesConnection
    hash_type = 'md5'

    def get_meta_data(self):
        response = self.connection.request('', method='HEAD')

        if response.status == httplib.NO_CONTENT:
            container_count = response.headers.get('x-account-container-count', 'unknown')
            object_count = response.headers.get('x-account-object-count', 'unknown')
            bytes_used = response.headers.get('x-account-bytes-used', 'unknown')

            return { 'container_count': int(container_count),
                      'object_count': int(object_count),
                      'bytes_used': int(bytes_used) }

        raise LibcloudError('Unexpected status code: %s' % (response.status))

    def list_containers(self):
        response = self.connection.request('')

        if response.status == httplib.NO_CONTENT:
            return []
        elif response.status == httplib.OK:
            return self._to_container_list(json.loads(response.body))

        raise LibcloudError('Unexpected status code: %s' % (response.status))

    def list_container_objects(self, container):
        response = self.connection.request('/%s' % (container.name))

        if response.status == httplib.NO_CONTENT:
            # Empty or inexistent container
            return []
        elif response.status == httplib.OK:
            return self._to_object_list(json.loads(response.body), container)

        raise LibcloudError('Unexpected status code: %s' % (response.status))

    def get_container(self, container_name):
        response = self.connection.request('/%s' % (container_name),
                                                    method='HEAD')

        if response.status == httplib.NO_CONTENT:
            container = self._headers_to_container(container_name, response.headers)
            return container
        elif response.status == httplib.NOT_FOUND:
            raise ContainerDoesNotExistError(None, self, container_name)

        raise LibcloudError('Unexpected status code: %s' % (response.status))

    def get_object(self, container_name, object_name):
        container = self.get_container(container_name)
        response = self.connection.request('/%s/%s' % (container_name,
                                                       object_name),
                                                       method='HEAD')

        if response.status in [ httplib.OK, httplib.NO_CONTENT ]:
            obj = self._headers_to_object(object_name, container, response.headers)
            return obj
        elif response.status == httplib.NOT_FOUND:
            raise ObjectDoesNotExistError(None, self, object_name)

        raise LibcloudError('Unexpected status code: %s' % (response.status))

    def create_container(self, container_name):
        container_name = self._clean_container_name(container_name)
        response = self.connection.request('/%s' % (container_name), method='PUT')

        if response.status == httplib.CREATED:
            # Accepted mean that container is not yet created but it will be
            # eventually
            extra = { 'object_count': 0 }
            container = Container(name=container_name, extra=extra, driver=self)

            return container
        elif response.status == httplib.ACCEPTED:
            error = ContainerAlreadyExistsError(None, self, container_name)
            raise error

        raise LibcloudError('Unexpected status code: %s' % (response.status))

    def delete_container(self, container):
        name = self._clean_container_name(container.name)

        # Only empty container can be deleted
        response = self.connection.request('/%s' % (name), method='DELETE')

        if response.status == httplib.NO_CONTENT:
            return True
        elif response.status == httplib.NOT_FOUND:
            raise ContainerDoesNotExistError(value='',
                                             container_name=name, driver=self)
        elif response.status == httplib.CONFLICT:
            # @TODO: Add "delete_all_objects" parameter?
            raise ContainerIsNotEmptyError(value='',
                                           container_name=name, driver=self)

    def download_object(self, obj, destination_path, overwrite_existing=False,
                        delete_on_failure=True):
        return self._get_object(obj, self._save_object,
                                {'obj': obj,
                                 'destination_path': destination_path,
                                 'overwrite_existing': overwrite_existing,
                                 'delete_on_failure': delete_on_failure})

    def download_object_as_stream(self, obj, chunk_size=None):
        return self._get_object(obj, self._get_object_as_stream,
                                {'chunk_size': chunk_size})

    def upload_object(self, file_path, container, object_name, extra=None,
                      file_hash=None):
        """
        Upload an object.

        Note: This will override file with a same name if it already exists.
        """
        upload_func = self._upload_file
        upload_func_args = { 'file_path': file_path }

        return self._put_object(container=container, file_path=file_path,
                                object_name=object_name, extra=extra,
                                upload_func=upload_func,
                                upload_func_args=upload_func_args)

    def upload_object_via_stream(self, iterator, container, object_name, extra=None):
        if isinstance(iterator, file):
            iterator = iter(iterator)

        upload_func = self._stream_data
        upload_func_args = { 'iterator': iterator }

        return self._put_object(container=container, iterator=iterator,
                                object_name=object_name, extra=extra,
                                upload_func=upload_func,
                                upload_func_args=upload_func_args)

    def delete_object(self, obj):
        container_name = self._clean_container_name(obj.container.name)
        object_name = self._clean_object_name(obj.name)

        response = self.connection.request('/%s/%s' % (container_name,
                                                       object_name), method='DELETE')

        if response.status == httplib.NO_CONTENT:
            return True
        elif response.status == httplib.NOT_FOUND:
            raise ObjectDoesNotExistError(value='', object_name=object_name,
                                          driver=self)

        raise LibcloudError('Unexpected status code: %s' % (response.status))

    def _get_object(self, obj, callback, callback_args):
        container_name = obj.container.name
        object_name = obj.name

        response = self.connection.request('/%s/%s' % (container_name,
                                                       object_name),
                                           raw=True)

        callback_args['response'] = response.response

        if response.status == httplib.OK:
            return callback(**callback_args)
        elif response.status == httplib.NOT_FOUND:
            raise ObjectDoesNotExistError(name=object_name)

        raise LibcloudError('Unexpected status code: %s' % (response.status))

    def _put_object(self, upload_func, upload_func_args, container, object_name,
                    extra=None, file_path=None, iterator=None, file_hash=None):
        container_name_cleaned = self._clean_container_name(container.name)
        object_name_cleaned = self._clean_object_name(object_name)

        extra = extra or {}
        content_type = extra.get('content_type', None)
        meta_data = extra.get('meta_data', None)

        if not content_type:
            if file_path:
                name = file_path
            else:
                name = object_name
            content_type, _ = utils.guess_file_mime_type(name)

            if not content_type:
                raise AttributeError('File content-type could not be guessed and' +
                                     ' no content_type value provided')

        headers = {}
        if iterator:
            headers['Transfer-Encoding'] = 'chunked'
            upload_func_args['chunked'] = True
        else:
            file_size = os.path.getsize(file_path)
            headers['Content-Length'] = file_size
            upload_func_args['chunked'] = False

            if file_hash:
                headers['ETag'] = file_hash

        headers['Content-Type'] = content_type

        if meta_data:
            for key, value in meta_data.iteritems():
                key = 'X-Object-Meta-%s' % (key)
                headers[key] = value

        response = self.connection.request('/%s/%s' % (container_name_cleaned,
                                                       object_name_cleaned),
                                           method='PUT', data=None,
                                           headers=headers, raw=True)

        upload_func_args['response'] = response
        success, data_hash, bytes_transferred = upload_func(**upload_func_args)

        if not success:
            raise LibcloudError('Object upload failed, Perhaps a timeout?')

        response = response.response

        if response.status == httplib.EXPECTATION_FAILED:
            raise LibcloudError('Missing content-type header')
        elif response.status == httplib.UNPROCESSABLE_ENTITY:
            raise ObjectHashMismatchError(value='MD5 hash checksum does not match',
                                          object_name=object_name, driver=self)
        elif response.status == httplib.CREATED:
            obj = Object(name=object_name, size=bytes_transferred, hash=file_hash,
                         extra=None, meta_data=meta_data, container=container,
                         driver=self)

            return obj

    def _clean_container_name(self, name):
        """
        Clean container name.
        """
        if name.startswith('/'):
            name = name[1:]
        name = urllib.quote(name)

        if name.find('/') != -1:
            raise InvalidContainerNameError(value='Container name cannot'
                                                  ' contain slashes',
                                            container_name=name, driver=self)

        if len(name) > 256:
            raise InvalidContainerNameError(value='Container name cannot be'
                                                   ' longer than 256 bytes',
                                            container_name=name, driver=self)


        return name

    def _clean_object_name(self, name):
        name = urllib.quote(name)
        return name

    def _to_container_list(self, response):
        # @TODO: Handle more then 10k containers - use "lazy list"?
        containers = []

        for container in response:
            extra = { 'object_count': int(container['count']),
                      'size': int(container['bytes'])}
            containers.append(Container(name=container['name'], extra=extra,
                                        driver=self))

        return containers

    def _to_object_list(self, response, container):
        objects = []

        for obj in response:
            name = obj['name']
            size = int(obj['bytes'])
            hash = obj['hash']
            extra = { 'content_type': obj['content_type'],
                      'last_modified': obj['last_modified'] }
            objects.append(Object(name=name, size=size, hash=hash, extra=extra,
                                  meta_data=None, container=container, driver=self))

        return objects

    def _headers_to_container(self, name, headers):
        size = int(headers.get('x-container-bytes-used', 0))
        object_count = int(headers.get('x-container-object-count', 0))

        extra = { 'object_count': object_count,
                  'size': size }
        container = Container(name=name, extra=extra, driver=self)
        return container

    def _headers_to_object(self, name, container, headers):
        size = int(headers.pop('content-length', 0))
        last_modified = headers.pop('last-modified', None)
        etag = headers.pop('etag', None)
        content_type = headers.pop('content-type', None)

        meta_data = {}
        for key, value in headers.iteritems():
            if key.find('x-object-meta-') != -1:
                key = key.replace('x-object-meta-', '')
                meta_data[key] = value

        extra = { 'content_type': content_type, 'last_modified': last_modified,
                  'etag': etag }

        obj = Object(name=name, size=size, hash=None, extra=extra,
                     meta_data=meta_data, container=container, driver=self)
        return obj

class CloudFilesUSStorageDriver(CloudFilesStorageDriver):
    """
    Cloudfiles storage driver for the US endpoint.
    """

    type = Provider.CLOUDFILES_US
    name = 'CloudFiles (US)'
    connectionCls = CloudFilesUSConnection

class CloudFilesUKStorageDriver(CloudFilesStorageDriver):
    """
    Cloudfiles storage driver for the UK endpoint.
    """

    type = Provider.CLOUDFILES_UK
    name = 'CloudFiles (UK)'
    connectionCls = CloudFilesUKConnection

########NEW FILE########
__FILENAME__ = dummy
# Licensed to the Apache Software Foundation (ASF) under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os.path
import random

from libcloud.common.types import LibcloudError

from libcloud.storage.base import Object, Container, StorageDriver
from libcloud.storage.types import ContainerAlreadyExistsError
from libcloud.storage.types import ContainerDoesNotExistError
from libcloud.storage.types import ContainerIsNotEmptyError
from libcloud.storage.types import ObjectDoesNotExistError


class DummyFileObject(file):
    def __init__(self, yield_count=5, chunk_len=10):
        self._yield_count = yield_count
        self._chunk_len = chunk_len

    def read(self, size):
        i = 0

        while i < self._yield_count:
            yield self._get_chunk(self._chunk_len)
            i += 1

        raise StopIteration

    def _get_chunk(self, chunk_len):
        chunk = [str(x) for x in random.randint(97, 120)]
        return chunk

    def __len__(self):
        return self._yield_count * self._chunk_len

class DummyIterator(object):
  def __init__(self, data=None):
    self._data = data or []
    self._current_item = 0

  def next(self):
      if self._current_item == len(self._data):
          raise StopIteration

      value = self._data[self._current_item]
      self._current_item += 1
      return value

class DummyStorageDriver(StorageDriver):
    """
    Dummy Storage driver.

    >>> from libcloud.storage.drivers.dummy import DummyStorageDriver
    >>> driver = DummyStorageDriver('key', 'secret')
    >>> container = driver.create_container(container_name='test container')
    >>> container
    <Container: name=test container, provider=Dummy Storage Provider>
    >>> container.name
    'test container'
    >>> container.extra['object_count']
    0
    """

    name = 'Dummy Storage Provider'

    def __init__(self, api_key, api_secret):
        self._containers = {}

    def get_meta_data(self):
        """
        >>> driver = DummyStorageDriver('key', 'secret')
        >>> driver.get_meta_data()
        {'object_count': 0, 'container_count': 0, 'bytes_used': 0}
        >>> container = driver.create_container(container_name='test container 1')
        >>> container = driver.create_container(container_name='test container 2')
        >>> obj = container.upload_object_via_stream(object_name='test object', iterator=DummyFileObject(5, 10), extra={})
        >>> driver.get_meta_data()
        {'object_count': 1, 'container_count': 2, 'bytes_used': 50}
        """

        container_count = len(self._containers)
        object_count = sum([ len(self._containers[container]['objects']) for
                        container in self._containers ])

        bytes_used = 0
        for container in self._containers:
            objects = self._containers[container]['objects']
            for _, obj in objects.iteritems():
                bytes_used += obj.size

        return { 'container_count': int(container_count),
                  'object_count': int(object_count),
                  'bytes_used': int(bytes_used) }

    def list_containers(self):
        """
        >>> driver = DummyStorageDriver('key', 'secret')
        >>> driver.list_containers()
        []
        >>> container = driver.create_container(container_name='test container 1')
        >>> container
        <Container: name=test container 1, provider=Dummy Storage Provider>
        >>> container.name
        'test container 1'
        >>> container = driver.create_container(container_name='test container 2')
        >>> container
        <Container: name=test container 2, provider=Dummy Storage Provider>
        >>> container = driver.create_container(container_name='test container 2') #doctest: +IGNORE_EXCEPTION_DETAIL
        Traceback (most recent call last):
        ContainerAlreadyExistsError:
        >>> container_list=driver.list_containers()
        >>> sorted([container.name for container in container_list])
        ['test container 1', 'test container 2']
        """

        return [container['container'] for container in
                self._containers.values()]

    def list_container_objects(self, container):
        container = self.get_container(container.name)

        return container.objects

    def get_container(self, container_name):
        """
        >>> driver = DummyStorageDriver('key', 'secret')
        >>> driver.get_container('unknown') #doctest: +IGNORE_EXCEPTION_DETAIL
        Traceback (most recent call last):
        ContainerDoesNotExistError:
        >>> container = driver.create_container(container_name='test container 1')
        >>> container
        <Container: name=test container 1, provider=Dummy Storage Provider>
        >>> container.name
        'test container 1'
        >>> driver.get_container('test container 1')
        <Container: name=test container 1, provider=Dummy Storage Provider>
        """

        if container_name not in self._containers:
           raise ContainerDoesNotExistError(driver=self, value=None,
                                            container_name=container_name)

        return self._containers[container_name]['container']

    def get_object(self, container_name, object_name):
        """
        >>> driver = DummyStorageDriver('key', 'secret')
        >>> driver.get_object('unknown', 'unknown') #doctest: +IGNORE_EXCEPTION_DETAIL
        Traceback (most recent call last):
        ContainerDoesNotExistError:
        >>> container = driver.create_container(container_name='test container 1')
        >>> container
        <Container: name=test container 1, provider=Dummy Storage Provider>
        >>> driver.get_object('test container 1', 'unknown') #doctest: +IGNORE_EXCEPTION_DETAIL
        Traceback (most recent call last):
        ObjectDoesNotExistError:
        >>> obj = container.upload_object_via_stream(object_name='test object', iterator=DummyFileObject(5, 10), extra={})
        >>> obj
        <Object: name=test object, size=50, hash=None, provider=Dummy Storage Provider ...>
        """

        container = self.get_container(container_name)

        container_objects = self._containers[container_name]['objects']
        if object_name not in container_objects:
            raise ObjectDoesNotExistError(object_name=object_name, value=None,
                                          driver=self)

        return container_objects[object_name]

    def create_container(self, container_name):
        """
        >>> driver = DummyStorageDriver('key', 'secret')
        >>> container = driver.create_container(container_name='test container 1')
        >>> container
        <Container: name=test container 1, provider=Dummy Storage Provider>
        >>> container = driver.create_container(container_name='test container 1') #doctest: +IGNORE_EXCEPTION_DETAIL
        Traceback (most recent call last):
        ContainerAlreadyExistsError:
        """

        if container_name in self._containers:
            raise ContainerAlreadyExistsError(container_name=container_name,
                                              value=None, driver=self)

        extra = { 'object_count': 0 }
        container = Container(name=container_name, extra=extra, driver=self)

        self._containers[container_name] = { 'container': container,
                                             'objects': {}
                                           }
        return container

    def delete_container(self, container):
        """
        >>> driver = DummyStorageDriver('key', 'secret')
        >>> container = Container(name = 'test container', extra={'object_count': 0}, driver=driver)
        >>> driver.delete_container(container=container) #doctest: +IGNORE_EXCEPTION_DETAIL
        Traceback (most recent call last):
        ContainerDoesNotExistError:
        >>> container = driver.create_container(container_name='test container 1') #doctest: +IGNORE_EXCEPTION_DETAIL
        >>> len(driver._containers)
        1
        >>> driver.delete_container(container=container)
        True
        >>> len(driver._containers)
        0
        >>> container = driver.create_container(container_name='test container 1') #doctest: +IGNORE_EXCEPTION_DETAIL
        >>> obj = container.upload_object_via_stream(object_name='test object', iterator=DummyFileObject(5, 10), extra={})
        >>> driver.delete_container(container=container) #doctest: +IGNORE_EXCEPTION_DETAIL
        Traceback (most recent call last):
        ContainerIsNotEmptyError:
        """

        container_name = container.name
        if container_name not in self._containers:
           raise ContainerDoesNotExistError(container_name=container_name,
                                            value=None, driver=self)

        container = self._containers[container_name]
        if len(container['objects']) > 0:
           raise ContainerIsNotEmptyError(container_name=container_name,
                                          value=None, driver=self)

        del self._containers[container_name]
        return True

    def download_object(self, obj, destination_path, overwrite_existing=False,
                       delete_on_failure=True):
      kwargs_dict =  {'obj': obj,
                      'response': DummyFileObject(),
                      'destination_path': destination_path,
                      'overwrite_existing': overwrite_existing,
                      'delete_on_failure': delete_on_failure}

      return self._save_object(**kwargs_dict)

    def download_object_as_stream(self, obj, chunk_size=None):
        """
        >>> driver = DummyStorageDriver('key', 'secret')
        >>> container = driver.create_container(container_name='test container 1') #doctest: +IGNORE_EXCEPTION_DETAIL
        >>> obj = container.upload_object_via_stream(object_name='test object', iterator=DummyFileObject(5, 10), extra={})
        >>> stream = container.download_object_as_stream(obj)
        >>> stream #doctest: +ELLIPSIS
        <closed file '<uninitialized file>', mode '<uninitialized file>' at 0x...>
        """

        return DummyFileObject()

    def upload_object(self, file_path, container, object_name, extra=None,
                      file_hash=None):
        """
        >>> driver = DummyStorageDriver('key', 'secret')
        >>> container = driver.create_container(container_name='test container 1')
        >>> container.upload_object(file_path='/tmp/inexistent.file', object_name='test') #doctest: +IGNORE_EXCEPTION_DETAIL
        Traceback (most recent call last):
        LibcloudError:
        >>> file_path = path = os.path.abspath(__file__)
        >>> file_size = os.path.getsize(file_path)
        >>> obj = container.upload_object(file_path=file_path, object_name='test')
        >>> obj #doctest: +ELLIPSIS
        <Object: name=test, size=...>
        >>> obj.size == file_size
        True
        """

        if not os.path.exists(file_path):
            raise LibcloudError(value='File %s does not exist' % (file_path),
                                driver=self)

        size = os.path.getsize(file_path)
        return self._add_object(container=container, object_name=object_name,
                                size=size, extra=extra)

    def upload_object_via_stream(self, iterator, container, object_name, extra=None):
        """
        >>> driver = DummyStorageDriver('key', 'secret')
        >>> container = driver.create_container(container_name='test container 1') #doctest: +IGNORE_EXCEPTION_DETAIL
        >>> obj = container.upload_object_via_stream(object_name='test object', iterator=DummyFileObject(5, 10), extra={})
        >>> obj #doctest: +ELLIPSIS
        <Object: name=test object, size=50, ...>
        """

        size = len(iterator)
        return self._add_object(container=container, object_name=object_name,
                                size=size, extra=extra)

    def delete_object(self, obj):
        """
        >>> driver = DummyStorageDriver('key', 'secret')
        >>> container = driver.create_container(container_name='test container 1') #doctest: +IGNORE_EXCEPTION_DETAIL
        >>> obj = container.upload_object_via_stream(object_name='test object', iterator=DummyFileObject(5, 10), extra={})
        >>> obj #doctest: +ELLIPSIS
        <Object: name=test object, size=50, ...>
        >>> container.delete_object(obj=obj)
        True
        >>> obj = Object(name='test object 2', size=1000, hash=None, extra=None, meta_data=None, container=container,driver=None)
        >>> container.delete_object(obj=obj) #doctest: +IGNORE_EXCEPTION_DETAIL
        Traceback (most recent call last):
        ObjectDoesNotExistError:
        """

        container_name = obj.container.name
        object_name = obj.name
        obj = self.get_object(container_name=container_name,
                              object_name=object_name)

        del self._containers[container_name]['objects'][object_name]
        return True

    def _add_object(self, container, object_name, size, extra=None):
        container = self.get_container(container.name)

        extra = extra or {}
        meta_data = extra.get('meta_data', {})
        obj = Object(name=object_name, size=size, extra=extra, hash=None,
                     meta_data=meta_data, container=container, driver=self)

        self._containers[container.name]['objects'][object_name] = obj
        return obj

if __name__ == "__main__":
    import doctest
    doctest.testmod()

########NEW FILE########
__FILENAME__ = providers
# Licensed to the Apache Software Foundation (ASF) under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from libcloud.utils import get_driver as get_provider_driver
from libcloud.storage.types import Provider

DRIVERS = {
    Provider.DUMMY:
        ('libcloud.storage.drivers.dummy', 'DummyStorageDriver'),
    Provider.CLOUDFILES_US:
        ('libcloud.storage.drivers.cloudfiles', 'CloudFilesUSStorageDriver'),
    Provider.CLOUDFILES_UK:
        ('libcloud.storage.drivers.cloudfiles', 'CloudFilesUKStorageDriver'),
}

def get_driver(provider):
    return get_provider_driver(DRIVERS, provider)

########NEW FILE########
__FILENAME__ = types
# Licensed to the Apache Software Foundation (ASF) under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from libcloud.common.types import LibcloudError

class Provider(object):
    """
    Defines for each of the supported providers

    @cvar DUMMY: Example provider
    @cvar CLOUDFILES_US: CloudFiles US
    @cvar CLOUDFILES_UK: CloudFiles UK
    """
    DUMMY = 0
    CLOUDFILES_US = 1
    CLOUDFILES_UK = 2

class ContainerError(LibcloudError):
    error_type = 'ContainerError'

    def __init__(self, value, driver, container_name):
        self.container_name = container_name
        super(ContainerError, self).__init__(value=value, driver=driver)

    def __str__(self):
        return '<%s in %s, container = %s>' % (self.error_type, repr(self.driver),
                                          self.container_name)

class ObjectError(LibcloudError):
    error_type = 'ContainerError'

    def __init__(self, value, driver, object_name):
        self.object_name = object_name
        super(ObjectError, self).__init__(value=value, driver=driver)

    def __str__(self):
        return '<%s in %s, object = %s>' % (self.error_type, repr(self.driver),
                                            self.object_name)

class ContainerAlreadyExistsError(ContainerError):
    error_type = 'ContainerAlreadyExistsError'

class ContainerDoesNotExistError(ContainerError):
    error_type = 'ContainerDoesNotExistError'

class ContainerIsNotEmptyError(ContainerError):
    error_type = 'ContainerIsNotEmptyError'

class ObjectDoesNotExistError(ObjectError):
    error_type = 'ObjectDoesNotExistError'

class ObjectHashMismatchError(ObjectError):
    error_type = 'ObjectHashMismatchError'

class InvalidContainerNameError(ContainerError):
    error_type = 'InvalidContainerNameError'

########NEW FILE########
__FILENAME__ = types
# Licensed to the Apache Software Foundation (ASF) under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from libcloud.common.types import LibcloudError, MalformedResponseError
from libcloud.common.types import InvalidCredsError, InvalidCredsException
from libcloud.compute.types import Provider, NodeState, DeploymentError
from libcloud.compute.types import DeploymentException

from libcloud.utils import deprecated_warning

deprecated_warning(__name__)

########NEW FILE########
__FILENAME__ = utils
# Licensed to the Apache Software Foundation (ASF) under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
import mimetypes
import warnings
from httplib import HTTPResponse

SHOW_DEPRECATION_WARNING = True
OLD_API_REMOVE_VERSION = '0.6.0'

def read_in_chunks(iterator, chunk_size=None):
    """
    Return a generator which yields data in chunks.

    @type iterator: C{Iterator}
    @param response: An object which implements an iterator interface
                     or a File like object with read method.

    @type chunk_size: C{int}
    @param chunk_size: Optional chunk size (defaults to CHUNK_SIZE)
    """

    if isinstance(iterator, (file, HTTPResponse)):
        get_data = iterator.read
        args = (chunk_size, )
    else:
        get_data = iterator.next
        args = ()

    while True:
        chunk = str(get_data(*args))

        if len(chunk) == 0:
            raise StopIteration

        yield chunk

def guess_file_mime_type(file_path):
    filename = os.path.basename(file_path)
    (mimetype, encoding) = mimetypes.guess_type(filename)
    return mimetype, encoding

def deprecated_warning(module):
    if SHOW_DEPRECATION_WARNING:
        warnings.warn('This path has been deprecated and the module'
                       ' is now available at "libcloud.compute.%s".'
                       ' This path will be fully removed in libcloud %s.' % \
                       (module, OLD_API_REMOVE_VERSION),
                  category=DeprecationWarning)

def get_driver(drivers, provider):
    """
    Get a driver.

    @param drivers: Dictionary containing valid providers.
    @param provider: Id of provider to get driver
    @type provider: L{libcloud.types.Provider}
    """
    if provider in drivers:
        mod_name, driver_name = drivers[provider]
        _mod = __import__(mod_name, globals(), locals(), [driver_name])
        return getattr(_mod, driver_name)

    raise AttributeError('Provider %s does not exist' % (provider))

########NEW FILE########
__FILENAME__ = test_base
# Licensed to the Apache Software Foundation (ASF) under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import sys
import unittest

from libcloud.common.base import Response
from libcloud.common.base import ConnectionKey, ConnectionUserAndKey
from libcloud.compute.base import Node, NodeSize, NodeImage, NodeDriver

from test import MockResponse

class FakeDriver(object):
    type = 0

class BaseTests(unittest.TestCase):

    def test_base_node(self):
        node = Node(id=0, name=0, state=0, public_ip=0, private_ip=0,
            driver=FakeDriver())

    def test_base_node_size(self):
        node_size = NodeSize(id=0, name=0, ram=0, disk=0, bandwidth=0, price=0,
            driver=FakeDriver())

    def test_base_node_image(self):
        node_image = NodeImage(id=0, name=0, driver=FakeDriver())

    def test_base_response(self):
        resp = Response(MockResponse(status=200, body='foo'))

    def test_base_node_driver(self):
        node_driver = NodeDriver('foo')

    def test_base_connection_key(self):
        conn = ConnectionKey('foo')

    def test_base_connection_userkey(self):
        conn = ConnectionUserAndKey('foo', 'bar')

#    def test_drivers_interface(self):
#        failures = []
#        for driver in DRIVERS:
#            creds = ProviderCreds(driver, 'foo', 'bar')
#            try:
#                verifyObject(INodeDriver, get_driver(driver)(creds))
#            except BrokenImplementation:
#                failures.append(DRIVERS[driver][1])
#
#        if failures:
#            self.fail('the following drivers do not support the \
#                       INodeDriver interface: %s' % (', '.join(failures)))

#    def test_invalid_creds(self):
#        failures = []
#        for driver in DRIVERS:
#            if driver == Provider.DUMMY:
#                continue
#            conn = connect(driver, 'bad', 'keys')
#            try:
#                conn.list_nodes()
#            except InvalidCredsException:
#                pass
#            else:
#                failures.append(DRIVERS[driver][1])
#
#        if failures:
#            self.fail('the following drivers did not throw an \
#                       InvalidCredsException: %s' % (', '.join(failures)))

if __name__ == '__main__':
    sys.exit(unittest.main())

########NEW FILE########
__FILENAME__ = test_brightbox
# Licensed to the Apache Software Foundation (ASF) under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import sys
import unittest
import httplib

try:
    import json
except ImportError:
    import simplejson as json

from libcloud.common.types import InvalidCredsError
from libcloud.compute.drivers.brightbox import BrightboxNodeDriver
from libcloud.compute.types import NodeState

from test import MockHttp
from test.compute import TestCaseMixin
from test.file_fixtures import ComputeFileFixtures
from test.secrets import BRIGHTBOX_CLIENT_ID, BRIGHTBOX_CLIENT_SECRET


class BrightboxTest(unittest.TestCase, TestCaseMixin):
    def setUp(self):
        BrightboxNodeDriver.connectionCls.conn_classes = (None, BrightboxMockHttp)
        BrightboxMockHttp.type = None
        self.driver = BrightboxNodeDriver(BRIGHTBOX_CLIENT_ID, BRIGHTBOX_CLIENT_SECRET)

    def test_authentication(self):
        BrightboxMockHttp.type = 'INVALID_CLIENT'
        self.assertRaises(InvalidCredsError, self.driver.list_nodes)

        BrightboxMockHttp.type = 'UNAUTHORIZED_CLIENT'
        self.assertRaises(InvalidCredsError, self.driver.list_nodes)

    def test_list_nodes(self):
        nodes = self.driver.list_nodes()
        self.assertEqual(len(nodes), 1)
        self.assertTrue('109.107.42.129' in nodes[0].public_ip)
        self.assertTrue('10.110.24.54' in nodes[0].private_ip)
        self.assertEqual(nodes[0].state, NodeState.RUNNING)

    def test_list_sizes(self):
        sizes = self.driver.list_sizes()
        self.assertEqual(len(sizes), 1)
        self.assertEqual(sizes[0].id, 'typ-4nssg')
        self.assertEqual(sizes[0].name, 'Brightbox Nano Instance')
        self.assertEqual(sizes[0].ram, 512)

    def test_list_images(self):
        images = self.driver.list_images()
        self.assertEqual(len(images), 1)
        self.assertEqual(images[0].id, 'img-9vxqi')
        self.assertEqual(images[0].name, 'Brightbox Lucid 32')
        self.assertEqual(images[0].extra['arch'], '32-bit')

    def test_reboot_node_response(self):
        node = self.driver.list_nodes()[0]
        self.assertRaises(NotImplementedError, self.driver.reboot_node, [node])

    def test_destroy_node(self):
        node = self.driver.list_nodes()[0]
        self.assertTrue(self.driver.destroy_node(node))

    def test_create_node(self):
        size = self.driver.list_sizes()[0]
        image = self.driver.list_images()[0]
        node = self.driver.create_node(name='Test Node', image=image, size=size)
        self.assertEqual('srv-3a97e', node.id)
        self.assertEqual('Test Node', node.name)


class BrightboxMockHttp(MockHttp):
    fixtures = ComputeFileFixtures('brightbox')

    def _token(self, method, url, body, headers):
        if method == 'POST':
            return self.response(httplib.OK, self.fixtures.load('token.json'))

    def _token_INVALID_CLIENT(self, method, url, body, headers):
        if method == 'POST':
            return self.response(httplib.BAD_REQUEST, '{"error":"invalid_client"}')

    def _token_UNAUTHORIZED_CLIENT(self, method, url, body, headers):
        if method == 'POST':
            return self.response(httplib.UNAUTHORIZED, '{"error":"unauthorized_client"}')

    def _1_0_images(self, method, url, body, headers):
        if method == 'GET':
            return self.response(httplib.OK, self.fixtures.load('list_images.json'))

    def _1_0_servers(self, method, url, body, headers):
        if method == 'GET':
            return self.response(httplib.OK, self.fixtures.load('list_servers.json'))
        elif method == 'POST':
            body = json.loads(body)

            node = json.loads(self.fixtures.load('create_server.json'))

            node['name'] = body['name']

            return self.response(httplib.ACCEPTED, json.dumps(node))

    def _1_0_servers_srv_3a97e(self, method, url, body, headers):
        if method == 'DELETE':
            return self.response(httplib.ACCEPTED, '')

    def _1_0_server_types(self, method, url, body, headers):
        if method == 'GET':
            return self.response(httplib.OK, self.fixtures.load('list_server_types.json'))

    def _1_0_zones(self, method, url, body, headers):
        if method == 'GET':
            return self.response(httplib.OK, self.fixtures.load('list_zones.json'))

    def response(self, status, body):
        return (status, body, {'content-type': 'application/json'}, httplib.responses[status])


if __name__ == '__main__':
    sys.exit(unittest.main())

########NEW FILE########
__FILENAME__ = test_cloudsigma
# Licensed to the Apache Software Foundation (ASF) under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import sys
import unittest
import httplib

from libcloud.compute.base import Node
from libcloud.compute.drivers.cloudsigma import CloudSigmaBaseNodeDriver
from libcloud.compute.drivers.cloudsigma import str2dicts, str2list, dict2str

from test import MockHttp
from test.compute import TestCaseMixin
from test.file_fixtures import ComputeFileFixtures


class CloudSigmaTestCase(unittest.TestCase, TestCaseMixin):
    def setUp(self):
        CloudSigmaBaseNodeDriver.connectionCls.conn_classes = (None,
                                                               CloudSigmaHttp)
        self.driver = CloudSigmaBaseNodeDriver('foo', 'bar')

    def test_list_nodes(self):
        nodes = self.driver.list_nodes()
        self.assertTrue(isinstance(nodes, list))
        self.assertEqual(len(nodes), 1)

        node = nodes[0]
        self.assertEqual(node.public_ip[0], "1.2.3.4")
        self.assertEqual(node.extra['smp'], 1)
        self.assertEqual(node.extra['cpu'], 1100)
        self.assertEqual(node.extra['mem'], 640)

    def test_list_sizes(self):
        images = self.driver.list_sizes()
        self.assertEqual(len(images), 9)

    def test_list_images(self):
        sizes = self.driver.list_images()
        self.assertEqual(len(sizes), 10)

    def test_list_locations_response(self):
        pass

    def test_start_node(self):
        nodes = self.driver.list_nodes()
        node = nodes[0]
        self.assertTrue(self.driver.ex_start_node(node))

    def test_shutdown_node(self):
        nodes = self.driver.list_nodes()
        node = nodes[0]
        self.assertTrue(self.driver.ex_stop_node(node))
        self.assertTrue(self.driver.ex_shutdown_node(node))

    def test_reboot_node(self):
        node = self.driver.list_nodes()[0]
        self.assertTrue(self.driver.reboot_node(node))

    def test_destroy_node(self):
        node = self.driver.list_nodes()[0]
        self.assertTrue(self.driver.destroy_node(node))
        nodes = self.driver.list_nodes()

    def test_create_node(self):
        size = self.driver.list_sizes()[0]
        image = self.driver.list_images()[0]
        node = self.driver.create_node(name = "cloudsigma node", image = image, size = size)
        self.assertTrue(isinstance(node, Node))

    def test_ex_static_ip_list(self):
        ips = self.driver.ex_static_ip_list()
        self.assertEqual(len(ips), 3)

    def test_ex_static_ip_create(self):
        result = self.driver.ex_static_ip_create()
        self.assertEqual(len(result), 2)
        self.assertEqual(len(result[0].keys()), 6)
        self.assertEqual(len(result[1].keys()), 6)

    def test_ex_static_ip_destroy(self):
        result = self.driver.ex_static_ip_destroy('1.2.3.4')
        self.assertTrue(result)

    def test_ex_drives_list(self):
        result = self.driver.ex_drives_list()
        self.assertEqual(len(result), 2)

    def test_ex_drive_destroy(self):
        result = self.driver.ex_drive_destroy('d18119ce_7afa_474a_9242_e0384b160220')
        self.assertTrue(result)

    def test_ex_set_node_configuration(self):
        node = self.driver.list_nodes()[0]
        result = self.driver.ex_set_node_configuration(node, **{'smp': 2})
        self.assertTrue(result)

    def test_str2dicts(self):
        string = 'mem 1024\ncpu 2200\n\nmem2048\cpu 1100'
        result = str2dicts(string)
        self.assertEqual(len(result), 2)

    def test_str2list(self):
        string = 'ip 1.2.3.4\nip 1.2.3.5\nip 1.2.3.6'
        result = str2list(string)
        self.assertEqual(len(result), 3)
        self.assertEqual(result[0], '1.2.3.4')
        self.assertEqual(result[1], '1.2.3.5')
        self.assertEqual(result[2], '1.2.3.6')

    def test_dict2str(self):
        d = {'smp': 5, 'cpu': 2200, 'mem': 1024}
        result = dict2str(d)
        self.assertTrue(len(result) > 0)
        self.assertTrue(result.find('smp 5') >= 0)
        self.assertTrue(result.find('cpu 2200') >= 0)
        self.assertTrue(result.find('mem 1024') >= 0)

class CloudSigmaHttp(MockHttp):
    fixtures = ComputeFileFixtures('cloudsigma')

    def _drives_standard_info(self, method, url, body, headers):
        body = self.fixtures.load('drives_standard_info.txt')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _servers_62fe7cde_4fb9_4c63_bd8c_e757930066a0_start(self, method, url, body, headers):
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _servers_62fe7cde_4fb9_4c63_bd8c_e757930066a0_stop(self, method, url, body, headers):
        return (httplib.NO_CONTENT, body, {}, httplib.responses[httplib.OK])

    def _servers_62fe7cde_4fb9_4c63_bd8c_e757930066a0_destroy(self, method, url, body, headers):
         return (httplib.NO_CONTENT, body, {}, httplib.responses[httplib.NO_CONTENT])

    def _drives_d18119ce_7afa_474a_9242_e0384b160220_clone(self, method, url, body, headers):
        body = self.fixtures.load('drives_clone.txt')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _drives_a814def5_1789_49a0_bf88_7abe7bb1682a_info(self, method, url, body, headers):
        body = self.fixtures.load('drives_single_info.txt')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _drives_info(self, method, url, body, headers):
        body = self.fixtures.load('drives_info.txt')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _servers_create(self, method, url, body, headers):
        body = self.fixtures.load('servers_create.txt')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _servers_info(self, method, url, body, headers):
        body = self.fixtures.load('servers_info.txt')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _resources_ip_list(self, method, url, body, headers):
        body = self.fixtures.load('resources_ip_list.txt')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _resources_ip_create(self, method, url, body, headers):
        body = self.fixtures.load('resources_ip_create.txt')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _resources_ip_1_2_3_4_destroy(self, method, url, body, headers):
        return (httplib.NO_CONTENT, body, {}, httplib.responses[httplib.OK])

    def _drives_d18119ce_7afa_474a_9242_e0384b160220_destroy(self, method, url, body, headers):
        return (httplib.NO_CONTENT, body, {}, httplib.responses[httplib.OK])

    def _servers_62fe7cde_4fb9_4c63_bd8c_e757930066a0_set(self, method, url, body, headers):
        body = self.fixtures.load('servers_set.txt')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

if __name__ == '__main__':
    sys.exit(unittest.main())

########NEW FILE########
__FILENAME__ = test_dreamhost
# Licensed to the Apache Software Foundation (ASF) under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import sys
import unittest
import httplib

try:
  import json
except: 
  import simplejson as json

from libcloud.common.types import InvalidCredsError
from libcloud.compute.drivers.dreamhost import DreamhostNodeDriver
from libcloud.compute.types import NodeState

from test import MockHttp
from test.compute import TestCaseMixin
from test.secrets import DREAMHOST_KEY

class DreamhostTest(unittest.TestCase, TestCaseMixin):

    def setUp(self):
        DreamhostNodeDriver.connectionCls.conn_classes = (
            None,
            DreamhostMockHttp
        )
        DreamhostMockHttp.type = None
        DreamhostMockHttp.use_param = 'cmd'
        self.driver = DreamhostNodeDriver(DREAMHOST_KEY)

    def test_invalid_creds(self):
        """
        Tests the error-handling for passing a bad API Key to the DreamHost API
        """
        DreamhostMockHttp.type = 'BAD_AUTH'
        try:
            self.driver.list_nodes()
            self.assertTrue(False) # Above command should have thrown an InvalidCredsException
        except InvalidCredsError:
            self.assertTrue(True)


    def test_list_nodes(self):
        """
        Test list_nodes for DreamHost PS driver.  Should return a list of two nodes:
            -   account_id: 000000
                ip: 75.119.203.51
                memory_mb: 500
                ps: ps22174
                start_date: 2010-02-25
                type: web
            -   account_id: 000000
                ip: 75.119.203.52
                memory_mb: 1500
                ps: ps22175
                start_date: 2010-02-25
                type: mysql
        """

        nodes = self.driver.list_nodes()
        self.assertEqual(len(nodes), 2)
        web_node = nodes[0]
        mysql_node = nodes[1]

        # Web node tests
        self.assertEqual(web_node.id, 'ps22174')
        self.assertEqual(web_node.state, NodeState.UNKNOWN)
        self.assertTrue('75.119.203.51' in web_node.public_ip)
        self.assertTrue(
            web_node.extra.has_key('current_size') and
            web_node.extra['current_size'] == 500
        )
        self.assertTrue(
            web_node.extra.has_key('account_id') and
            web_node.extra['account_id'] == 000000
        )
        self.assertTrue(
            web_node.extra.has_key('type') and
            web_node.extra['type'] == 'web'
        )
        # MySql node tests
        self.assertEqual(mysql_node.id, 'ps22175')
        self.assertEqual(mysql_node.state, NodeState.UNKNOWN)
        self.assertTrue('75.119.203.52' in mysql_node.public_ip)
        self.assertTrue(
            mysql_node.extra.has_key('current_size') and
            mysql_node.extra['current_size'] == 1500
        )
        self.assertTrue(
            mysql_node.extra.has_key('account_id') and
            mysql_node.extra['account_id'] == 000000
        )
        self.assertTrue(
            mysql_node.extra.has_key('type') and
            mysql_node.extra['type'] == 'mysql'
        )

    def test_create_node(self):
        """
        Test create_node for DreamHost PS driver.
        This is not remarkably compatible with libcloud.  The DH API allows
        users to specify what image they want to create and whether to move
        all their data to the (web) PS. It does NOT accept a name, size, or
        location.  The only information it returns is the PS's context id
        Once the PS is ready it will appear in the list generated by list_ps.
        """
        new_node = self.driver.create_node(
            image = self.driver.list_images()[0],
            size = self.driver.list_sizes()[0],
            movedata = 'no',
        )
        self.assertEqual(new_node.id, 'ps12345')
        self.assertEqual(new_node.state, NodeState.PENDING)
        self.assertTrue(
            new_node.extra.has_key('type') and
            new_node.extra['type'] == 'web'
        )

    def test_destroy_node(self):
        """
        Test destroy_node for DreamHost PS driver
        """
        node = self.driver.list_nodes()[0]
        self.assertTrue(self.driver.destroy_node(node))

    def test_destroy_node_failure(self):
        """
        Test destroy_node failure for DreamHost PS driver
        """
        node = self.driver.list_nodes()[0]

        DreamhostMockHttp.type = 'API_FAILURE'
        self.assertFalse(self.driver.destroy_node(node))

    def test_reboot_node(self):
        """
        Test reboot_node for DreamHost PS driver.
        """
        node = self.driver.list_nodes()[0]
        self.assertTrue(self.driver.reboot_node(node))

    def test_reboot_node_failure(self):
        """
        Test reboot_node failure for DreamHost PS driver
        """
        node = self.driver.list_nodes()[0]

        DreamhostMockHttp.type = 'API_FAILURE'
        self.assertFalse(self.driver.reboot_node(node))

    def test_resize_node(self):
        """
        Test resize_node for DreamHost PS driver
        """
        node = self.driver.list_nodes()[0]
        self.assertTrue(self.driver._resize_node(node, 400))

    def test_resize_node_failure(self):
        """
        Test reboot_node faliure for DreamHost PS driver
        """
        node = self.driver.list_nodes()[0]

        DreamhostMockHttp.type = 'API_FAILURE'
        self.assertFalse(self.driver._resize_node(node, 400))

    def test_list_images(self):
        """
        Test list_images for DreamHost PS driver.
        """
        images = self.driver.list_images()
        self.assertEqual(len(images), 2)
        self.assertEqual(images[0].id, 'web')
        self.assertEqual(images[0].name, 'web')
        self.assertEqual(images[1].id, 'mysql')
        self.assertEqual(images[1].name, 'mysql')

    def test_list_sizes(self):
        sizes = self.driver.list_sizes()
        self.assertEqual(len(sizes), 5)

        self.assertEqual(sizes[0].id, 'default')
        self.assertEqual(sizes[0].bandwidth, None)
        self.assertEqual(sizes[0].disk, None)
        self.assertEqual(sizes[0].ram, 2300)
        self.assertEqual(sizes[0].price, 115)

    def test_list_locations(self):
        try:
            self.driver.list_locations()
        except NotImplementedError:
            pass

    def test_list_locations_response(self):
        self.assertRaises(NotImplementedError, self.driver.list_locations)

class DreamhostMockHttp(MockHttp):

    def _BAD_AUTH_dreamhost_ps_list_ps(self, method, url, body, headers):
        body = json.dumps({'data' : 'invalid_api_key', 'result' : 'error'})
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _dreamhost_ps_add_ps(self, method, url, body, headers):
        body = json.dumps({'data' : {'added_web' : 'ps12345'}, 'result' : 'success'})
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _dreamhost_ps_list_ps(self, method, url, body, headers):
        data = [{
            'account_id' : 000000,
            'ip': '75.119.203.51',
            'memory_mb' : 500,
            'ps' : 'ps22174',
            'start_date' : '2010-02-25',
            'type' : 'web'
        },
        {
            'account_id' : 000000,
            'ip' : '75.119.203.52',
            'memory_mb' : 1500,
            'ps' : 'ps22175',
            'start_date' : '2010-02-25',
            'type' : 'mysql'
        }]
        result = 'success'
        body = json.dumps({'data' : data, 'result' : result})
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _dreamhost_ps_list_images(self, method, url, body, headers):
        data = [{
            'description' : 'Private web server',
            'image' : 'web'
        },
        {
            'description' : 'Private MySQL server',
            'image' : 'mysql'
        }]
        result = 'success'
        body = json.dumps({'data' : data, 'result' : result})
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _dreamhost_ps_reboot(self, method, url, body, headers):
        body = json.dumps({'data' : 'reboot_scheduled', 'result' : 'success'})
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _API_FAILURE_dreamhost_ps_reboot(self, method, url, body, headers):
        body = json.dumps({'data' : 'no_such_ps', 'result' : 'error'})
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _dreamhost_ps_set_size(self, method, url, body, headers):
        body = json.dumps({'data' : {'memory-mb' : '500'}, 'result' : 'success'})
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _API_FAILURE_dreamhost_ps_set_size(self, method, url, body, headers):
        body = json.dumps({'data' : 'internal_error_setting_size', 'result' : 'error'})
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _dreamhost_ps_remove_ps(self, method, url, body, headers):
        body = json.dumps({'data' : 'removed_web', 'result' : 'success'})
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _API_FAILURE_dreamhost_ps_remove_ps(self, method, url, body, headers):
        body = json.dumps({'data' : 'no_such_ps', 'result' : 'error'})
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

if __name__ == '__main__':
    sys.exit(unittest.main())


########NEW FILE########
__FILENAME__ = test_ec2
# Licensed to the Apache Software Foundation (ASF) under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import sys
import unittest
import httplib

from libcloud.compute.drivers.ec2 import EC2NodeDriver, EC2APSENodeDriver
from libcloud.compute.drivers.ec2 import EC2APNENodeDriver, IdempotentParamError
from libcloud.compute.base import Node, NodeImage, NodeSize, NodeLocation

from test import MockHttp
from test.compute import TestCaseMixin
from test.file_fixtures import ComputeFileFixtures

from test.secrets import EC2_ACCESS_ID, EC2_SECRET

class EC2Tests(unittest.TestCase, TestCaseMixin):

    def setUp(self):
        EC2NodeDriver.connectionCls.conn_classes = (None, EC2MockHttp)
        EC2MockHttp.use_param = 'Action'
        EC2MockHttp.type = None
        self.driver = EC2NodeDriver(EC2_ACCESS_ID, EC2_SECRET)

    def test_create_node(self):
        image = NodeImage(id='ami-be3adfd7',
                          name='ec2-public-images/fedora-8-i386-base-v1.04.manifest.xml',
                          driver=self.driver)
        size = NodeSize('m1.small', 'Small Instance', None, None, None, None, driver=self.driver)
        node = self.driver.create_node(name='foo', image=image, size=size)
        self.assertEqual(node.id, 'i-2ba64342')

    def test_create_node_idempotent(self):
        EC2MockHttp.type = 'idempotent'
        image = NodeImage(id='ami-be3adfd7',
                          name='ec2-public-images/fedora-8-i386-base-v1.04.manifest.xml',
                          driver=self.driver)
        size = NodeSize('m1.small', 'Small Instance', None, None, None, None, driver=self.driver)
        token = 'testclienttoken'
        node = self.driver.create_node(name='foo', image=image, size=size,
                ex_clienttoken=token)
        self.assertEqual(node.id, 'i-2ba64342')
        self.assertEqual(node.extra['clienttoken'], token)

        # from: http://docs.amazonwebservices.com/AWSEC2/latest/DeveloperGuide/index.html?Run_Instance_Idempotency.html

        #    If you repeat the request with the same client token, but change
        #    another request parameter, Amazon EC2 returns an
        #    IdempotentParameterMismatch error.

        # In our case, changing the parameter doesn't actually matter since we
        # are forcing the error response fixture.
        EC2MockHttp.type = 'idempotent_mismatch'

        idem_error = None
        try:
            self.driver.create_node(name='foo', image=image, size=size,
                    ex_mincount='2', ex_maxcount='2', # different count
                    ex_clienttoken=token)
        except IdempotentParamError, e:
            idem_error = e
        self.assertTrue(idem_error is not None)

    def test_create_node_no_availability_zone(self):
        image = NodeImage(id='ami-be3adfd7',
                          name='ec2-public-images/fedora-8-i386-base-v1.04.manifest.xml',
                          driver=self.driver)
        size = NodeSize('m1.small', 'Small Instance', None, None, None, None,
                        driver=self.driver)
        node = self.driver.create_node(name='foo', image=image, size=size)
        location = NodeLocation(0, 'Amazon US N. Virginia', 'US', self.driver)
        self.assertEqual(node.id, 'i-2ba64342')
        node = self.driver.create_node(name='foo', image=image, size=size,
                                       location=location)
        self.assertEqual(node.id, 'i-2ba64342')

    def test_list_nodes(self):
        node = self.driver.list_nodes()[0]
        public_ips = sorted(node.public_ip)
        self.assertEqual(node.id, 'i-4382922a')
        self.assertEqual(len(node.public_ip), 2)

        self.assertEqual(public_ips[0], '1.2.3.4')
        self.assertEqual(public_ips[1], '1.2.3.5')

    def test_list_location(self):
        locations = self.driver.list_locations()
        self.assertTrue(len(locations) > 0)
        self.assertTrue(locations[0].availability_zone != None)

    def test_reboot_node(self):
        node = Node('i-4382922a', None, None, None, None, self.driver)
        ret = self.driver.reboot_node(node)
        self.assertTrue(ret)

    def test_destroy_node(self):
        node = Node('i-4382922a', None, None, None, None, self.driver)
        ret = self.driver.destroy_node(node)
        self.assertTrue(ret)

    def test_list_sizes(self):
        region_old = self.driver.region_name

        for region_name in [ 'us-east-1', 'us-west-1', 'eu-west-1',
                             'ap-southeast-1' ]:
            self.driver.region_name = region_name
            sizes = self.driver.list_sizes()

            ids = [s.id for s in sizes]
            self.assertTrue('t1.micro' in ids)
            self.assertTrue('m1.small' in ids)
            self.assertTrue('m1.large' in ids)
            self.assertTrue('m1.xlarge' in ids)
            self.assertTrue('c1.medium' in ids)
            self.assertTrue('c1.xlarge' in ids)
            self.assertTrue('m2.xlarge' in ids)
            self.assertTrue('m2.2xlarge' in ids)
            self.assertTrue('m2.4xlarge' in ids)

            if region_name == 'us-east-1':
                self.assertEqual(len(sizes), 11)
                self.assertTrue('cg1.4xlarge' in ids)
                self.assertTrue('cc1.4xlarge' in ids)
            else:
                self.assertEqual(len(sizes), 9)

        self.driver.region_name = region_old

    def test_list_images(self):
        images = self.driver.list_images()
        image = images[0]
        self.assertEqual(len(images), 1)
        self.assertEqual(image.name, 'ec2-public-images/fedora-8-i386-base-v1.04.manifest.xml')
        self.assertEqual(image.id, 'ami-be3adfd7')

    def test_ex_list_availability_zones(self):
        availability_zones = self.driver.ex_list_availability_zones()
        availability_zone = availability_zones[0]
        self.assertTrue(len(availability_zones) > 0)
        self.assertEqual(availability_zone.name, 'eu-west-1a')
        self.assertEqual(availability_zone.zone_state, 'available')
        self.assertEqual(availability_zone.region_name, 'eu-west-1')

    def test_ex_describe_tags(self):
        node = Node('i-4382922a', None, None, None, None, self.driver)
        tags = self.driver.ex_describe_tags(node)

        self.assertEqual(len(tags), 3)
        self.assertTrue('tag' in tags)
        self.assertTrue('owner' in tags)
        self.assertTrue('stack' in tags)

    def test_ex_create_tags(self):
        node = Node('i-4382922a', None, None, None, None, self.driver)
        self.driver.ex_create_tags(node, {'sample': 'tag'})

    def test_ex_delete_tags(self):
        node = Node('i-4382922a', None, None, None, None, self.driver)
        self.driver.ex_delete_tags(node, {'sample': 'tag'})

    def test_ex_describe_addresses_for_node(self):
        node1 = Node('i-4382922a', None, None, None, None, self.driver)
        ip_addresses1 = self.driver.ex_describe_addresses_for_node(node1)
        node2 = Node('i-4382922b', None, None, None, None, self.driver)
        ip_addresses2 = sorted(self.driver.ex_describe_addresses_for_node(node2))
        node3 = Node('i-4382922g', None, None, None, None, self.driver)
        ip_addresses3 = sorted(self.driver.ex_describe_addresses_for_node(node3))

        self.assertEqual(len(ip_addresses1), 1)
        self.assertEqual(ip_addresses1[0], '1.2.3.4')

        self.assertEqual(len(ip_addresses2), 2)
        self.assertEqual(ip_addresses2[0], '1.2.3.5')
        self.assertEqual(ip_addresses2[1], '1.2.3.6')

        self.assertEqual(len(ip_addresses3), 0)

    def test_ex_describe_addresses(self):
        node1 = Node('i-4382922a', None, None, None, None, self.driver)
        node2 = Node('i-4382922g', None, None, None, None, self.driver)
        nodes_elastic_ips1 = self.driver.ex_describe_addresses([node1])
        nodes_elastic_ips2 = self.driver.ex_describe_addresses([node2])

        self.assertEqual(len(nodes_elastic_ips1), 1)
        self.assertTrue(node1.id in nodes_elastic_ips1)
        self.assertEqual(nodes_elastic_ips1[node1.id], ['1.2.3.4'])

        self.assertEqual(len(nodes_elastic_ips2), 1)
        self.assertTrue(node2.id in nodes_elastic_ips2)
        self.assertEqual(nodes_elastic_ips2[node2.id], [])


class EC2MockHttp(MockHttp):

    fixtures = ComputeFileFixtures('ec2')

    def _DescribeInstances(self, method, url, body, headers):
        body = self.fixtures.load('describe_instances.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _DescribeAvailabilityZones(self, method, url, body, headers):
        body = self.fixtures.load('describe_availability_zones.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _RebootInstances(self, method, url, body, headers):
        body = self.fixtures.load('reboot_instances.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _DescribeImages(self, method, url, body, headers):
        body = self.fixtures.load('describe_images.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _RunInstances(self, method, url, body, headers):
        body = self.fixtures.load('run_instances.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _idempotent_RunInstances(self, method, url, body, headers):
        body = self.fixtures.load('run_instances_idem.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _idempotent_mismatch_RunInstances(self, method, url, body, headers):
        body = self.fixtures.load('run_instances_idem_mismatch.xml')
        return (httplib.BAD_REQUEST, body, {}, httplib.responses[httplib.BAD_REQUEST])

    def _TerminateInstances(self, method, url, body, headers):
        body = self.fixtures.load('terminate_instances.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _DescribeTags(self, method, url, body, headers):
        body = self.fixtures.load('describe_tags.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _CreateTags(self, method, url, body, headers):
        body = self.fixtures.load('create_tags.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _DeleteTags(self, method, url, body, headers):
        body = self.fixtures.load('delete_tags.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _DescribeAddresses(self, method, url, body, headers):
        body = self.fixtures.load('describe_addresses_multi.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])


class EC2APSETests(EC2Tests):
    def setUp(self):
        EC2APSENodeDriver.connectionCls.conn_classes = (None, EC2MockHttp)
        EC2MockHttp.use_param = 'Action'
        EC2MockHttp.type = None
        self.driver = EC2APSENodeDriver(EC2_ACCESS_ID, EC2_SECRET)

class EC2APNETests(EC2Tests):
    def setUp(self):
        EC2APNENodeDriver.connectionCls.conn_classes = (None, EC2MockHttp)
        EC2MockHttp.use_param = 'Action'
        EC2MockHttp.type = None
        self.driver = EC2APNENodeDriver(EC2_ACCESS_ID, EC2_SECRET)

if __name__ == '__main__':
    sys.exit(unittest.main())

########NEW FILE########
__FILENAME__ = test_ecp
# Licensed to the Apache Software Foundation (ASF) under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import sys
import unittest
import httplib

from libcloud.compute.drivers.ecp import ECPNodeDriver
from libcloud.compute.types import NodeState

from test import MockHttp
from test.compute import TestCaseMixin
from test.file_fixtures import ComputeFileFixtures

from test.secrets import ECP_USER_NAME, ECP_PASSWORD

class ECPTests(unittest.TestCase, TestCaseMixin):

    def setUp(self):
        ECPNodeDriver.connectionCls.conn_classes = (None,
                                                            ECPMockHttp)
        self.driver = ECPNodeDriver(ECP_USER_NAME, ECP_PASSWORD)


    def test_list_nodes(self):
        nodes = self.driver.list_nodes()
        self.assertEqual(len(nodes),2)
        node = nodes[0]
        self.assertEqual(node.id, '1')
        self.assertEqual(node.name, 'dummy-1')
        self.assertEqual(node.public_ip[0], "42.78.124.75")
        self.assertEqual(node.state, NodeState.RUNNING)


    def test_list_sizes(self):
        sizes = self.driver.list_sizes()
        self.assertEqual(len(sizes),3)
        size = sizes[0]
        self.assertEqual(size.id,'1')
        self.assertEqual(size.ram,512)
        self.assertEqual(size.disk,0)
        self.assertEqual(size.bandwidth,0)
        self.assertEqual(size.price,0)

    def test_list_images(self):
        images = self.driver.list_images()
        self.assertEqual(len(images),2)
        self.assertEqual(images[0].name,"centos54: AUTO import from /opt/enomalism2/repo/5d407a68-c76c-11de-86e5-000475cb7577.xvm2")
        self.assertEqual(images[0].id, "1")
        self.assertEqual(images[1].name,"centos54 two: AUTO import from /opt/enomalism2/repo/5d407a68-c76c-11de-86e5-000475cb7577.xvm2")
        self.assertEqual(images[1].id, "2")

    def test_reboot_node(self):
        # Raises exception on failure
        node = self.driver.list_nodes()[0]
        self.driver.reboot_node(node)

    def test_destroy_node(self):
        # Raises exception on failure
        node = self.driver.list_nodes()[0]
        self.driver.destroy_node(node)

    def test_create_node(self):
        # Raises exception on failure
        size = self.driver.list_sizes()[0]
        image = self.driver.list_images()[0]
        node = self.driver.create_node(name="api.ivan.net.nz", image=image, size=size)
        self.assertEqual(node.name, "api.ivan.net.nz")
        self.assertEqual(node.id, "1234")

class ECPMockHttp(MockHttp):

    fixtures = ComputeFileFixtures('ecp')

    def _modules_hosting(self, method, url, body, headers):
        headers = {}
        headers['set-cookie'] = 'vcloud-token=testtoken'
        body = 'Anything'
        return (httplib.OK, body, headers, httplib.responses[httplib.OK])

    def _rest_hosting_vm_1(self, method, url, body, headers):
        if method == 'GET':
            body = self.fixtures.load('vm_1_get.json')
        if method == 'POST':
            if body.find('delete',0):
                body = self.fixtures.load('vm_1_action_delete.json')
            if body.find('stop',0):
                body = self.fixtures.load('vm_1_action_stop.json')
            if body.find('start',0):
                body = self.fixtures.load('vm_1_action_start.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _rest_hosting_vm(self, method, url, body, headers):
        if method == 'PUT':
            body = self.fixtures.load('vm_put.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _rest_hosting_vm_list(self, method, url, body, headers):
        body = self.fixtures.load('vm_list.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _rest_hosting_htemplate_list(self, method, url, body, headers):
        body = self.fixtures.load('htemplate_list.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _rest_hosting_network_list(self, method, url, body, headers):
        body = self.fixtures.load('network_list.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _rest_hosting_ptemplate_list(self, method, url, body, headers):
        body = self.fixtures.load('ptemplate_list.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])



if __name__ == '__main__':
    sys.exit(unittest.main())

########NEW FILE########
__FILENAME__ = test_elastichosts
# Licensed to the Apache Software Foundation (ASF) under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# Copyright 2009 RedRata Ltd

import sys
import unittest
import httplib

from libcloud.compute.drivers.elastichosts import ElasticHostsBaseNodeDriver

from test import MockHttp
from test.compute import TestCaseMixin
from test.file_fixtures import ComputeFileFixtures

class ElasticHostsTestCase(unittest.TestCase, TestCaseMixin):
    def setUp(self):
        ElasticHostsBaseNodeDriver.connectionCls.conn_classes = (None,
                                                            ElasticHostsHttp)
        self.driver = ElasticHostsBaseNodeDriver('foo', 'bar')

    def test_list_nodes(self):
        nodes = self.driver.list_nodes()
        self.assertTrue(isinstance(nodes, list))
        self.assertEqual(len(nodes), 1)
        
        node = nodes[0]
        self.assertEqual(node.public_ip[0], "1.2.3.4")
        self.assertEqual(node.public_ip[1], "1.2.3.5")
        self.assertEqual(node.extra['smp'], 1)

    def test_list_sizes(self):
        images = self.driver.list_sizes()
        self.assertEqual(len(images), 5)
        image = images[0]
        self.assertEqual(image.id, 'small')
        self.assertEqual(image.name, 'Small instance')
        self.assertEqual(image.cpu, 2000)
        self.assertEqual(image.ram, 1700)
        self.assertEqual(image.disk, 160)

    def test_list_images(self):
        sizes = self.driver.list_images()
        self.assertEqual(len(sizes), 8)
        size = sizes[0]
        self.assertEqual(size.id, '38df0986-4d85-4b76-b502-3878ffc80161')
        self.assertEqual(size.name, 'CentOS Linux 5.5')
        
    def test_list_locations_response(self):
        pass

    def test_reboot_node(self):
        node = self.driver.list_nodes()[0]
        self.assertTrue(self.driver.reboot_node(node))

    def test_destroy_node(self):
        node = self.driver.list_nodes()[0]
        self.assertTrue(self.driver.destroy_node(node))

    def test_create_node(self):
        size = self.driver.list_sizes()[0]
        image = self.driver.list_images()[0]
        self.assertTrue(self.driver.create_node(name="api.ivan.net.nz", image=image, size=size))

class ElasticHostsHttp(MockHttp):

    fixtures = ComputeFileFixtures('elastichosts')
    
    def _servers_b605ca90_c3e6_4cee_85f8_a8ebdf8f9903_reset(self, method, url, body, headers):
         return (httplib.NO_CONTENT, body, {}, httplib.responses[httplib.NO_CONTENT])
    
    def _servers_b605ca90_c3e6_4cee_85f8_a8ebdf8f9903_destroy(self, method, url, body, headers):
         return (httplib.NO_CONTENT, body, {}, httplib.responses[httplib.NO_CONTENT])
    
    def _drives_create(self, method, url, body, headers):
        body = self.fixtures.load('drives_create.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])
    
    def _drives_0012e24a_6eae_4279_9912_3432f698cec8_image_38df0986_4d85_4b76_b502_3878ffc80161_gunzip(self, method, url, body, headers):
        return (httplib.NO_CONTENT, body, {}, httplib.responses[httplib.NO_CONTENT])

    def _drives_0012e24a_6eae_4279_9912_3432f698cec8_info(self, method, url, body, headers):
        body = self.fixtures.load('drives_info.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])
    
    def _servers_create(self, method, url, body, headers):
        body = self.fixtures.load('servers_create.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _servers_info(self, method, url, body, headers):
        body = self.fixtures.load('servers_info.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

if __name__ == '__main__':
    sys.exit(unittest.main())

########NEW FILE########
__FILENAME__ = test_gogrid
# Licensed to the Apache Software Foundation (ASF) under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import httplib
import sys
import unittest
import urlparse

try:
    import json
except ImportError:
    import simplejson as json

from libcloud.common.types import LibcloudError, InvalidCredsError
from libcloud.compute.drivers.gogrid import GoGridNodeDriver, GoGridIpAddress
from libcloud.compute.base import Node, NodeImage, NodeSize, NodeLocation

from test import MockHttp
from test.compute import TestCaseMixin
from test.file_fixtures import ComputeFileFixtures

class GoGridTests(unittest.TestCase, TestCaseMixin):

    def setUp(self):
        GoGridNodeDriver.connectionCls.conn_classes = (None, GoGridMockHttp)
        GoGridMockHttp.type = None
        self.driver = GoGridNodeDriver("foo", "bar")

    def test_create_node(self):
        image = NodeImage(1531, None, self.driver)
        size = NodeSize('512Mb', None, None, None, None, None, driver=self.driver)

        node = self.driver.create_node(name='test1', image=image, size=size)
        self.assertEqual(node.name, 'test1')
        self.assertTrue(node.id is not None)
        self.assertEqual(node.extra['password'], 'bebebe')

    def test_list_nodes(self):
        node = self.driver.list_nodes()[0]

        self.assertEqual(node.id, '90967')
        self.assertEqual(node.extra['password'], 'bebebe')
        self.assertEqual(node.extra['isSandbox'], False)

    def test_reboot_node(self):
        node = Node(90967, None, None, None, None, self.driver)
        ret = self.driver.reboot_node(node)
        self.assertTrue(ret)

    def test_destroy_node(self):
        node = Node(90967, None, None, None, None, self.driver)
        ret = self.driver.destroy_node(node)
        self.assertTrue(ret)

    def test_list_images(self):
        images = self.driver.list_images()
        image = images[0]
        self.assertEqual(len(images), 4)
        self.assertEqual(image.name, 'CentOS 5.3 (32-bit) w/ None')
        self.assertEqual(image.id, '1531')

    def test_malformed_reply(self):
        GoGridMockHttp.type = 'FAIL'
        try:
            images = self.driver.list_images()
        except LibcloudError, e:
            self.assertTrue(isinstance(e, LibcloudError))
        else:
            self.fail("test should have thrown")

    def test_invalid_creds(self):
        GoGridMockHttp.type = 'FAIL'
        try:
            nodes = self.driver.list_nodes()
        except InvalidCredsError, e:
            self.assertTrue(e.driver is not None)
            self.assertEqual(e.driver.name, self.driver.name)
        else:
            self.fail("test should have thrown")

    def test_node_creation_without_free_public_ips(self):
        GoGridMockHttp.type = 'NOPUBIPS'
        try:
            image = NodeImage(1531, None, self.driver)
            size = NodeSize('512Mb', None, None, None, None, None, driver=self.driver)

            node = self.driver.create_node(name='test1', image=image, size=size)
        except LibcloudError, e:
            self.assertTrue(isinstance(e, LibcloudError))
            self.assertTrue(e.driver is not None)
            self.assertEqual(e.driver.name, self.driver.name)
        else:
            self.fail("test should have thrown")

    def test_list_locations(self):
        locations = self.driver.list_locations()
        location_names = [location.name for location in locations]

        self.assertEqual(len(locations), 2)
        for i in 0, 1:
            self.assertTrue(isinstance(locations[i], NodeLocation))
        self.assertTrue("US-West-1" in location_names)
        self.assertTrue("US-East-1" in location_names)

    def test_ex_save_image(self):
        node = self.driver.list_nodes()[0]
        image = self.driver.ex_save_image(node, "testimage")
        self.assertEqual(image.name, "testimage")

    def test_ex_edit_image(self):
        image = self.driver.list_images()[0]
        ret = self.driver.ex_edit_image(image=image, public=False,
                ex_description="test", name="testname")

        self.assertTrue(isinstance(ret, NodeImage))

    def test_ex_edit_node(self):
        node = Node(90967, None, None, None, None, self.driver)
        size = NodeSize('512Mb', None, None, None, None, None, driver=self.driver)
        ret = self.driver.ex_edit_node(node=node, size=size)

        self.assertTrue(isinstance(ret, Node))

    def test_ex_list_ips(self):
        ips = self.driver.ex_list_ips()

        expected_ips = {"192.168.75.66": GoGridIpAddress(id="5348099",
            ip="192.168.75.66", public=True, state="Unassigned",
            subnet="192.168.75.64/255.255.255.240"),
            "192.168.75.67": GoGridIpAddress(id="5348100",
                ip="192.168.75.67", public=True, state="Assigned",
                subnet="192.168.75.64/255.255.255.240"),
            "192.168.75.68": GoGridIpAddress(id="5348101",
                ip="192.168.75.68", public=False, state="Unassigned",
                subnet="192.168.75.64/255.255.255.240")}

        self.assertEqual(len(expected_ips), 3)

        for ip in ips:
            self.assertTrue(ip.ip in expected_ips)
            self.assertEqual(ip.public, expected_ips[ip.ip].public)
            self.assertEqual(ip.state, expected_ips[ip.ip].state)
            self.assertEqual(ip.subnet, expected_ips[ip.ip].subnet)

            del expected_ips[ip.ip]

        self.assertEqual(len(expected_ips), 0)

class GoGridMockHttp(MockHttp):

    fixtures = ComputeFileFixtures('gogrid')

    def _api_grid_image_list(self, method, url, body, headers):
        body = self.fixtures.load('image_list.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _api_grid_image_list_FAIL(self, method, url, body, headers):
        body = "<h3>some non valid json here</h3>"
        return (httplib.SERVICE_UNAVAILABLE, body, {},
                httplib.responses[httplib.SERVICE_UNAVAILABLE])

    def _api_grid_server_list(self, method, url, body, headers):
        body = self.fixtures.load('server_list.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    _api_grid_server_list_NOPUBIPS = _api_grid_server_list

    def _api_grid_server_list_FAIL(self, method, url, body, headers):
        return (httplib.FORBIDDEN, "123", {}, httplib.responses[httplib.FORBIDDEN])

    def _api_grid_ip_list(self, method, url, body, headers):
        body = self.fixtures.load('ip_list.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _api_grid_ip_list_NOPUBIPS(self, method, url, body, headers):
        body = self.fixtures.load('ip_list_empty.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _api_grid_server_power(self, method, url, body, headers):
        body = self.fixtures.load('server_power.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _api_grid_server_add(self, method, url, body, headers):
        body = self.fixtures.load('server_add.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    _api_grid_server_add_NOPUBIPS = _api_grid_server_add

    def _api_grid_server_delete(self, method, url, body, headers):
        body = self.fixtures.load('server_delete.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _api_grid_server_edit(self, method, url, body, headers):
        body = self.fixtures.load('server_edit.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _api_support_password_list(self, method, url, body, headers):
        body = self.fixtures.load('password_list.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    _api_support_password_list_NOPUBIPS = _api_support_password_list

    def _api_grid_image_save(self, method, url, body, headers):
        body = self.fixtures.load('image_save.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _api_grid_image_edit(self, method, url, body, headers):
        # edit method is quite similar to save method from the response
        # perspective
        body = self.fixtures.load('image_save.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _api_common_lookup_list(self, method, url, body, headers):
        _valid_lookups = ("ip.datacenter",)

        try:
            from urlparse import parse_qs
        except ImportError:
            from cgi import parse_qs

        lookup = parse_qs(urlparse.urlparse(url).query)["lookup"][0]
        if lookup in _valid_lookups:
            fixture_path = "lookup_list_%s.json" % \
                    (lookup.replace(".", "_"))
        else:
            raise NotImplementedError
        body = self.fixtures.load(fixture_path)
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

if __name__ == '__main__':
    sys.exit(unittest.main())

########NEW FILE########
__FILENAME__ = test_ibm_sbc
# Licensed to the Apache Software Foundation (ASF) under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
import unittest
import httplib
import sys

from libcloud.compute.types import InvalidCredsError
from libcloud.compute.drivers.ibm_sbc import IBMNodeDriver as IBM
from libcloud.compute.base import Node, NodeImage, NodeSize, NodeLocation

from test import MockHttp
from test.compute import TestCaseMixin
from test.file_fixtures import ComputeFileFixtures
from test.secrets import IBM_USER, IBM_SECRET

class IBMTests(unittest.TestCase, TestCaseMixin):
    """
    Tests the IBM Developer Cloud driver.
    """

    def setUp(self):
        IBM.connectionCls.conn_classes = (None, IBMMockHttp)
        IBMMockHttp.type = None
        self.driver = IBM(IBM_USER, IBM_SECRET)

    def test_auth(self):
        IBMMockHttp.type = 'UNAUTHORIZED'

        try:
            self.driver.list_nodes()
        except InvalidCredsError, e:
            self.assertTrue(isinstance(e, InvalidCredsError))
            self.assertEquals(e.value, '401: Unauthorized')
        else:
            self.fail('test should have thrown')

    def test_list_nodes(self):
        ret = self.driver.list_nodes()
        self.assertEquals(len(ret), 3)
        self.assertEquals(ret[0].id, '26557')
        self.assertEquals(ret[0].name, 'Insight Instance')
        self.assertEquals(ret[0].public_ip, '129.33.196.128')
        self.assertEquals(ret[0].private_ip, None)  # Private IPs not supported
        self.assertEquals(ret[1].public_ip, None)   # Node is non-active (no IP)
        self.assertEquals(ret[1].private_ip, None)
        self.assertEquals(ret[1].id, '28193')

    def test_list_sizes(self):
        ret = self.driver.list_sizes()
        self.assertEquals(len(ret), 9) # 9 instance configurations supported
        self.assertEquals(ret[0].id, 'BRZ32.1/2048/60*175')
        self.assertEquals(ret[1].id, 'BRZ64.2/4096/60*500*350')
        self.assertEquals(ret[2].id, 'COP32.1/2048/60')
        self.assertEquals(ret[0].name, 'Bronze 32 bit')
        self.assertEquals(ret[0].disk, None)

    def test_list_images(self):
        ret = self.driver.list_images()
        self.assertEqual(len(ret), 21)
        self.assertEqual(ret[10].name, "Rational Asset Manager 7.2.0.1")
        self.assertEqual(ret[9].id, '10002573')

    def test_list_locations(self):
        ret = self.driver.list_locations()
        self.assertEquals(len(ret), 1)
        self.assertEquals(ret[0].id, '1')
        self.assertEquals(ret[0].name, 'US North East: Poughkeepsie, NY')
        self.assertEquals(ret[0].country, 'US')

    def test_create_node(self):
        # Test creation of node
        IBMMockHttp.type = 'CREATE'
        image = NodeImage(id=11, name='Rational Insight', driver=self.driver)
        size = NodeSize('LARGE', 'LARGE', None, None, None, None, self.driver)
        location = NodeLocation('1', 'POK', 'US', driver=self.driver)
        ret = self.driver.create_node(name='RationalInsight4',
                                      image=image,
                                      size=size,
                                      location=location,
                                      publicKey='MyPublicKey',
                                      configurationData = {
                                           'insight_admin_password': 'myPassword1',
                                           'db2_admin_password': 'myPassword2',
                                           'report_user_password': 'myPassword3'})
        self.assertTrue(isinstance(ret, Node))
        self.assertEquals(ret.name, 'RationalInsight4')

        # Test creation attempt with invalid location
        IBMMockHttp.type = 'CREATE_INVALID'
        location = NodeLocation('3', 'DOESNOTEXIST', 'US', driver=self.driver)
        try:
            ret = self.driver.create_node(name='RationalInsight5',
                                          image=image,
                                          size=size,
                                          location=location,
                                          publicKey='MyPublicKey',
                                          configurationData = {
                                               'insight_admin_password': 'myPassword1',
                                               'db2_admin_password': 'myPassword2',
                                               'report_user_password': 'myPassword3'})
        except Exception, e:
            self.assertEquals(e.args[0], 'Error 412: No DataCenter with id: 3')
        else:
            self.fail('test should have thrown')

    def test_destroy_node(self):
        # Delete existant node
        nodes = self.driver.list_nodes()            # retrieves 3 nodes
        self.assertEquals(len(nodes), 3)
        IBMMockHttp.type = 'DELETE'
        toDelete = nodes[1]
        ret = self.driver.destroy_node(toDelete)
        self.assertTrue(ret)

        # Delete non-existant node
        IBMMockHttp.type = 'DELETED'
        nodes = self.driver.list_nodes()            # retrieves 2 nodes
        self.assertEquals(len(nodes), 2)
        try:
            self.driver.destroy_node(toDelete)      # delete non-existent node
        except Exception, e:
            self.assertEquals(e.args[0], 'Error 404: Invalid Instance ID 28193')
        else:
            self.fail('test should have thrown')

    def test_reboot_node(self):
        nodes = self.driver.list_nodes()
        IBMMockHttp.type = 'REBOOT'

        # Reboot active node
        self.assertEquals(len(nodes), 3)
        ret = self.driver.reboot_node(nodes[0])
        self.assertTrue(ret)

        # Reboot inactive node
        try:
            ret = self.driver.reboot_node(nodes[1])
        except Exception, e:
            self.assertEquals(e.args[0], 'Error 412: Instance must be in the Active state')
        else:
            self.fail('test should have thrown')

class IBMMockHttp(MockHttp):
    fixtures = ComputeFileFixtures('ibm_sbc')

    def _computecloud_enterprise_api_rest_20100331_instances(self, method, url, body, headers):
        body = self.fixtures.load('instances.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _computecloud_enterprise_api_rest_20100331_instances_DELETED(self, method, url, body, headers):
        body = self.fixtures.load('instances_deleted.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _computecloud_enterprise_api_rest_20100331_instances_UNAUTHORIZED(self, method, url, body, headers):
        return (httplib.UNAUTHORIZED, body, {}, httplib.responses[httplib.UNAUTHORIZED])

    def _computecloud_enterprise_api_rest_20100331_offerings_image(self, method, url, body, headers):
        body = self.fixtures.load('images.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _computecloud_enterprise_api_rest_20100331_locations(self, method, url, body, headers):
        body = self.fixtures.load('locations.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _computecloud_enterprise_api_rest_20100331_instances_26557_REBOOT(self, method, url, body, headers):
        body = self.fixtures.load('reboot_active.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _computecloud_enterprise_api_rest_20100331_instances_28193_REBOOT(self, method, url, body, headers):
        return (412, 'Error 412: Instance must be in the Active state', {}, 'Precondition Failed')

    def _computecloud_enterprise_api_rest_20100331_instances_28193_DELETE(self, method, url, body, headers):
        body = self.fixtures.load('delete.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _computecloud_enterprise_api_rest_20100331_instances_28193_DELETED(self, method, url, body, headers):
        return (404, 'Error 404: Invalid Instance ID 28193', {}, 'Precondition Failed')

    def _computecloud_enterprise_api_rest_20100331_instances_CREATE(self, method, url, body, headers):
        body = self.fixtures.load('create.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _computecloud_enterprise_api_rest_20100331_instances_CREATE_INVALID(self, method, url, body, headers):
        return (412, 'Error 412: No DataCenter with id: 3', {}, 'Precondition Failed')

    # This is only to accomodate the response tests built into test\__init__.py
    def _computecloud_enterprise_api_rest_20100331_instances_26557(self, method, url, body, headers):
        if method == 'DELETE':
            body = self.fixtures.load('delete.xml')
        else:
            body = self.fixtures.load('reboot_active.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

if __name__ == '__main__':
    sys.exit(unittest.main())

########NEW FILE########
__FILENAME__ = test_linode
# Licensed to the Apache Software Foundation (ASF) under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# Maintainer: Jed Smith <jed@linode.com>
# Based upon code written by Alex Polvi <polvi@cloudkick.com>
#

import sys
import unittest
import httplib

from libcloud.compute.drivers.linode import LinodeNodeDriver
from libcloud.compute.base import Node, NodeAuthPassword

from test import MockHttp
from test.compute import TestCaseMixin

class LinodeTest(unittest.TestCase, TestCaseMixin):
    # The Linode test suite

    def setUp(self):
        LinodeNodeDriver.connectionCls.conn_classes = (None, LinodeMockHttp)
        LinodeMockHttp.use_param = 'api_action'
        self.driver = LinodeNodeDriver('foo')

    def test_list_nodes(self):
        nodes = self.driver.list_nodes()
        self.assertEqual(len(nodes), 1)
        node = nodes[0]
        self.assertEqual(node.id, "8098")
        self.assertEqual(node.name, 'api-node3')
        self.assertTrue('75.127.96.245' in node.public_ip)
        self.assertEqual(node.private_ip, [])

    def test_reboot_node(self):
        # An exception would indicate failure
        node = self.driver.list_nodes()[0]
        self.driver.reboot_node(node)

    def test_destroy_node(self):
        # An exception would indicate failure
        node = self.driver.list_nodes()[0]
        self.driver.destroy_node(node)

    def test_create_node(self):
        # Will exception on failure
        self.driver.create_node(name="Test",
                                location=self.driver.list_locations()[0],
                                size=self.driver.list_sizes()[0],
                                image=self.driver.list_images()[6],
                                auth=NodeAuthPassword("test123"))

    def test_list_sizes(self):
        sizes = self.driver.list_sizes()
        self.assertEqual(len(sizes), 10)
        for size in sizes:
            self.assertEqual(size.ram, int(size.name.split(" ")[1]))

    def test_list_images(self):
        images = self.driver.list_images()
        self.assertEqual(len(images), 22)

    def test_create_node_response(self):
        # should return a node object
        node = self.driver.create_node(name="node-name",
                         location=self.driver.list_locations()[0],
                         size=self.driver.list_sizes()[0],
                         image=self.driver.list_images()[0],
                         auth=NodeAuthPassword("foobar"))
        self.assertTrue(isinstance(node[0], Node))


class LinodeMockHttp(MockHttp):
    def _avail_datacenters(self, method, url, body, headers):
        body = '{"ERRORARRAY":[],"ACTION":"avail.datacenters","DATA":[{"DATACENTERID":2,"LOCATION":"Dallas, TX, USA"},{"DATACENTERID":3,"LOCATION":"Fremont, CA, USA"},{"DATACENTERID":4,"LOCATION":"Atlanta, GA, USA"},{"DATACENTERID":6,"LOCATION":"Newark, NJ, USA"}]}'
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _avail_linodeplans(self, method, url, body, headers):
        body = '{"ERRORARRAY":[],"ACTION":"avail.linodeplans","DATA":[{"AVAIL":{"2":27,"3":0,"4":0,"6":0},"DISK":16,"PRICE":19.95,"PLANID":1,"LABEL":"Linode 360","RAM":360,"XFER":200},{"AVAIL":{"2":0,"3":0,"4":0,"6":0},"DISK":24,"PRICE":29.95,"PLANID":2,"LABEL":"Linode 540","RAM":540,"XFER":300},{"AVAIL":{"2":0,"3":0,"4":0,"6":0},"DISK":32,"PRICE":39.95,"PLANID":3,"LABEL":"Linode 720","RAM":720,"XFER":400},{"AVAIL":{"2":0,"3":0,"4":0,"6":0},"DISK":48,"PRICE":59.95,"PLANID":4,"LABEL":"Linode 1080","RAM":1080,"XFER":600},{"AVAIL":{"2":0,"3":0,"4":0,"6":0},"DISK":64,"PRICE":79.95,"PLANID":5,"LABEL":"Linode 1440","RAM":1440,"XFER":800},{"AVAIL":{"2":0,"3":0,"4":0,"6":0},"DISK":128,"PRICE":159.95,"PLANID":6,"LABEL":"Linode 2880","RAM":2880,"XFER":1600},{"AVAIL":{"2":0,"3":0,"4":0,"6":0},"DISK":256,"PRICE":319.95,"PLANID":7,"LABEL":"Linode 5760","RAM":5760,"XFER":2000},{"AVAIL":{"2":0,"3":0,"4":0,"6":0},"DISK":384,"PRICE":479.95,"PLANID":8,"LABEL":"Linode 8640","RAM":8640,"XFER":2000},{"AVAIL":{"2":0,"3":0,"4":0,"6":0},"DISK":512,"PRICE":639.95,"PLANID":9,"LABEL":"Linode 11520","RAM":11520,"XFER":2000},{"AVAIL":{"2":0,"3":0,"4":0,"6":0},"DISK":640,"PRICE":799.95,"PLANID":10,"LABEL":"Linode 14400","RAM":14400,"XFER":2000}]}'
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _avail_distributions(self, method, url, body, headers):
        body = '{"ERRORARRAY":[],"ACTION":"avail.distributions","DATA":[{"REQUIRESPVOPSKERNEL":0,"IS64BIT":0,"LABEL":"Arch Linux 2007.08","MINIMAGESIZE":436,"DISTRIBUTIONID":38,"CREATE_DT":"2007-10-24 00:00:00.0"},{"REQUIRESPVOPSKERNEL":0,"IS64BIT":0,"LABEL":"Centos 5.0","MINIMAGESIZE":594,"DISTRIBUTIONID":32,"CREATE_DT":"2007-04-27 00:00:00.0"},{"REQUIRESPVOPSKERNEL":0,"IS64BIT":0,"LABEL":"Centos 5.2","MINIMAGESIZE":950,"DISTRIBUTIONID":46,"CREATE_DT":"2008-11-30 00:00:00.0"},{"REQUIRESPVOPSKERNEL":1,"IS64BIT":1,"LABEL":"Centos 5.2 64bit","MINIMAGESIZE":980,"DISTRIBUTIONID":47,"CREATE_DT":"2008-11-30 00:00:00.0"},{"REQUIRESPVOPSKERNEL":1,"IS64BIT":0,"LABEL":"Debian 4.0","MINIMAGESIZE":200,"DISTRIBUTIONID":28,"CREATE_DT":"2007-04-18 00:00:00.0"},{"REQUIRESPVOPSKERNEL":0,"IS64BIT":1,"LABEL":"Debian 4.0 64bit","MINIMAGESIZE":220,"DISTRIBUTIONID":48,"CREATE_DT":"2008-12-02 00:00:00.0"},{"REQUIRESPVOPSKERNEL":0,"IS64BIT":0,"LABEL":"Debian 5.0","MINIMAGESIZE":200,"DISTRIBUTIONID":50,"CREATE_DT":"2009-02-19 00:00:00.0"},{"REQUIRESPVOPSKERNEL":0,"IS64BIT":1,"LABEL":"Debian 5.0 64bit","MINIMAGESIZE":300,"DISTRIBUTIONID":51,"CREATE_DT":"2009-02-19 00:00:00.0"},{"REQUIRESPVOPSKERNEL":1,"IS64BIT":0,"LABEL":"Fedora 8","MINIMAGESIZE":740,"DISTRIBUTIONID":40,"CREATE_DT":"2007-11-09 00:00:00.0"},{"REQUIRESPVOPSKERNEL":0,"IS64BIT":0,"LABEL":"Fedora 9","MINIMAGESIZE":1175,"DISTRIBUTIONID":43,"CREATE_DT":"2008-06-09 15:15:21.0"},{"REQUIRESPVOPSKERNEL":1,"IS64BIT":0,"LABEL":"Gentoo 2007.0","MINIMAGESIZE":1800,"DISTRIBUTIONID":35,"CREATE_DT":"2007-08-29 00:00:00.0"},{"REQUIRESPVOPSKERNEL":0,"IS64BIT":0,"LABEL":"Gentoo 2008.0","MINIMAGESIZE":1500,"DISTRIBUTIONID":52,"CREATE_DT":"2009-03-20 00:00:00.0"},{"REQUIRESPVOPSKERNEL":1,"IS64BIT":1,"LABEL":"Gentoo 2008.0 64bit","MINIMAGESIZE":2500,"DISTRIBUTIONID":53,"CREATE_DT":"2009-04-04 00:00:00.0"},{"REQUIRESPVOPSKERNEL":0,"IS64BIT":0,"LABEL":"OpenSUSE 11.0","MINIMAGESIZE":850,"DISTRIBUTIONID":44,"CREATE_DT":"2008-08-21 08:32:16.0"},{"REQUIRESPVOPSKERNEL":0,"IS64BIT":0,"LABEL":"Slackware 12.0","MINIMAGESIZE":315,"DISTRIBUTIONID":34,"CREATE_DT":"2007-07-16 00:00:00.0"},{"REQUIRESPVOPSKERNEL":1,"IS64BIT":0,"LABEL":"Slackware 12.2","MINIMAGESIZE":500,"DISTRIBUTIONID":54,"CREATE_DT":"2009-04-04 00:00:00.0"},{"REQUIRESPVOPSKERNEL":0,"IS64BIT":0,"LABEL":"Ubuntu 8.04 LTS","MINIMAGESIZE":400,"DISTRIBUTIONID":41,"CREATE_DT":"2008-04-23 15:11:29.0"},{"REQUIRESPVOPSKERNEL":0,"IS64BIT":1,"LABEL":"Ubuntu 8.04 LTS 64bit","MINIMAGESIZE":350,"DISTRIBUTIONID":42,"CREATE_DT":"2008-06-03 12:51:11.0"},{"REQUIRESPVOPSKERNEL":0,"IS64BIT":0,"LABEL":"Ubuntu 8.10","MINIMAGESIZE":220,"DISTRIBUTIONID":45,"CREATE_DT":"2008-10-30 23:23:03.0"},{"REQUIRESPVOPSKERNEL":1,"IS64BIT":1,"LABEL":"Ubuntu 8.10 64bit","MINIMAGESIZE":230,"DISTRIBUTIONID":49,"CREATE_DT":"2008-12-02 00:00:00.0"},{"REQUIRESPVOPSKERNEL":0,"IS64BIT":0,"LABEL":"Ubuntu 9.04","MINIMAGESIZE":350,"DISTRIBUTIONID":55,"CREATE_DT":"2009-04-23 00:00:00.0"},{"REQUIRESPVOPSKERNEL":0,"IS64BIT":1,"LABEL":"Ubuntu 9.04 64bit","MINIMAGESIZE":350,"DISTRIBUTIONID":56,"CREATE_DT":"2009-04-23 00:00:00.0"}]}'
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _linode_create(self, method, url, body, headers):
        body = '{"ERRORARRAY":[],"ACTION":"linode.create","DATA":{"LinodeID":8098}}'
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _linode_disk_createfromdistribution(self, method, url, body, headers):
        body = '{"ERRORARRAY":[],"ACTION":"linode.disk.createFromDistribution","DATA":{"JobID":1298,"DiskID":55647}}'
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _linode_delete(self, method, url, body, headers):
        body = '{"ERRORARRAY":[],"ACTION":"linode.delete","DATA":{"LinodeID":8098}}'
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _linode_update(self, method, url, body, headers):
        body = '{"ERRORARRAY":[],"ACTION":"linode.update","DATA":{"LinodeID":8098}}'
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _linode_reboot(self, method, url, body, headers):
        body = '{"ERRORARRAY":[],"ACTION":"linode.reboot","DATA":{"JobID":1305}}'
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _avail_kernels(self, method, url, body, headers):
        body = '{"ERRORARRAY":[],"ACTION":"avail.kernels","DATA":[{"LABEL":"Latest 2.6 Stable (2.6.18.8-linode19)","ISXEN":1,"KERNELID":60},{"LABEL":"2.6.18.8-linode19","ISXEN":1,"KERNELID":103},{"LABEL":"2.6.30.5-linode20","ISXEN":1,"KERNELID":105},{"LABEL":"Latest 2.6 Stable (2.6.18.8-x86_64-linode7)","ISXEN":1,"KERNELID":107},{"LABEL":"2.6.18.8-x86_64-linode7","ISXEN":1,"KERNELID":104},{"LABEL":"2.6.30.5-x86_64-linode8","ISXEN":1,"KERNELID":106},{"LABEL":"pv-grub-x86_32","ISXEN":1,"KERNELID":92},{"LABEL":"pv-grub-x86_64","ISXEN":1,"KERNELID":95},{"LABEL":"Recovery - Finnix (kernel)","ISXEN":1,"KERNELID":61},{"LABEL":"2.6.18.8-domU-linode7","ISXEN":1,"KERNELID":81},{"LABEL":"2.6.18.8-linode10","ISXEN":1,"KERNELID":89},{"LABEL":"2.6.18.8-linode16","ISXEN":1,"KERNELID":98},{"LABEL":"2.6.24.4-linode8","ISXEN":1,"KERNELID":84},{"LABEL":"2.6.25-linode9","ISXEN":1,"KERNELID":88},{"LABEL":"2.6.25.10-linode12","ISXEN":1,"KERNELID":90},{"LABEL":"2.6.26-linode13","ISXEN":1,"KERNELID":91},{"LABEL":"2.6.27.4-linode14","ISXEN":1,"KERNELID":93},{"LABEL":"2.6.28-linode15","ISXEN":1,"KERNELID":96},{"LABEL":"2.6.28.3-linode17","ISXEN":1,"KERNELID":99},{"LABEL":"2.6.29-linode18","ISXEN":1,"KERNELID":101},{"LABEL":"2.6.16.38-x86_64-linode2","ISXEN":1,"KERNELID":85},{"LABEL":"2.6.18.8-x86_64-linode1","ISXEN":1,"KERNELID":86},{"LABEL":"2.6.27.4-x86_64-linode3","ISXEN":1,"KERNELID":94},{"LABEL":"2.6.28-x86_64-linode4","ISXEN":1,"KERNELID":97},{"LABEL":"2.6.28.3-x86_64-linode5","ISXEN":1,"KERNELID":100},{"LABEL":"2.6.29-x86_64-linode6","ISXEN":1,"KERNELID":102}]}'
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _linode_disk_create(self, method, url, body, headers):
        body = '{"ERRORARRAY":[],"ACTION":"linode.disk.create","DATA":{"JobID":1299,"DiskID":55648}}'
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _linode_boot(self, method, url, body, headers):
        body = '{"ERRORARRAY":[],"ACTION":"linode.boot","DATA":{"JobID":1300}}'
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _linode_config_create(self, method, url, body, headers):
        body = '{"ERRORARRAY":[],"ACTION":"linode.config.create","DATA":{"ConfigID":31239}}'
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _linode_list(self, method, url, body, headers):
        body = '{"ACTION": "linode.list", "DATA": [{"ALERT_DISKIO_ENABLED": 1, "BACKUPWEEKLYDAY": 0, "LABEL": "api-node3", "DATACENTERID": 5, "ALERT_BWOUT_ENABLED": 1, "ALERT_CPU_THRESHOLD": 10, "TOTALHD": 100, "ALERT_BWQUOTA_THRESHOLD": 81, "ALERT_BWQUOTA_ENABLED": 1, "TOTALXFER": 200, "STATUS": 2, "ALERT_BWIN_ENABLED": 1, "ALERT_BWIN_THRESHOLD": 5, "ALERT_DISKIO_THRESHOLD": 200, "WATCHDOG": 1, "LINODEID": 8098, "BACKUPWINDOW": 1, "TOTALRAM": 540, "LPM_DISPLAYGROUP": "", "ALERT_BWOUT_THRESHOLD": 5, "BACKUPSENABLED": 1, "ALERT_CPU_ENABLED": 1}], "ERRORARRAY": []}'
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _linode_ip_list(self, method, url, body, headers):
        body = '{"ACTION": "linode.ip.list", "DATA": [{"RDNS_NAME": "li22-54.members.linode.com", "ISPUBLIC": 1, "IPADDRESS": "75.127.96.54", "IPADDRESSID": 5384, "LINODEID": 8098}, {"RDNS_NAME": "li22-245.members.linode.com", "ISPUBLIC": 1, "IPADDRESS": "75.127.96.245", "IPADDRESSID": 5575, "LINODEID": 8098}], "ERRORARRAY": []}'
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _batch(self, method, url, body, headers):
        body = '[{"ACTION": "linode.ip.list", "DATA": [{"RDNS_NAME": "li22-54.members.linode.com", "ISPUBLIC": 1, "IPADDRESS": "75.127.96.54", "IPADDRESSID": 5384, "LINODEID": 8098}, {"RDNS_NAME": "li22-245.members.linode.com", "ISPUBLIC": 1, "IPADDRESS": "75.127.96.245", "IPADDRESSID": 5575, "LINODEID": 8098}], "ERRORARRAY": []}]'
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])


if __name__ == '__main__':
    sys.exit(unittest.main())

########NEW FILE########
__FILENAME__ = test_opennebula
# Copyright 2002-2009, Distributed Systems Architecture Group, Universidad
# Complutense de Madrid (dsa-research.org)
#
# Licensed to the Apache Software Foundation (ASF) under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import sys
import unittest
import httplib

from libcloud.compute.drivers.opennebula import OpenNebulaNodeDriver
from libcloud.compute.base import Node, NodeImage, NodeSize

from test import MockHttp
from test.compute import TestCaseMixin
from test.file_fixtures import ComputeFileFixtures

from test.secrets import OPENNEBULA_USER, OPENNEBULA_KEY

class OpenNebulaTests(unittest.TestCase, TestCaseMixin):

    def setUp(self):
        OpenNebulaNodeDriver.connectionCls.conn_classes = (None, OpenNebulaMockHttp)
        self.driver = OpenNebulaNodeDriver(OPENNEBULA_USER, OPENNEBULA_KEY)

    def test_create_node(self):
        image = NodeImage(id=1, name='UbuntuServer9.04-Contextualized', driver=self.driver)
        size = NodeSize(1, 'small', None, None, None, None, driver=self.driver)
        node = self.driver.create_node(name='MyCompute', image=image, size=size)
        self.assertEqual(node.id, '5')
        self.assertEqual(node.name, 'MyCompute')

    def test_list_nodes(self):
        nodes = self.driver.list_nodes()
        self.assertEqual(len(nodes), 2)
        node = nodes[0]
        self.assertEqual(node.id, '5')
        self.assertEqual(node.name, 'MyCompute')

    def test_reboot_node(self):
        node = Node(5, None, None, None, None, self.driver)
        ret = self.driver.reboot_node(node)
        self.assertTrue(ret)

    def test_destroy_node(self):
        node = Node(5, None, None, None, None, self.driver)
        ret = self.driver.destroy_node(node)
        self.assertTrue(ret)

    def test_list_sizes(self):
        sizes = self.driver.list_sizes()
        self.assertEqual(len(sizes), 3)
        self.assertTrue('small' in [ s.name for s in sizes])
        self.assertTrue('medium' in [ s.name for s in sizes])
        self.assertTrue('large' in [ s.name for s in sizes])

    def test_list_images(self):
        images = self.driver.list_images()
        self.assertEqual(len(images), 2)
        image = images[0]
        self.assertEqual(image.id, '1')
        self.assertEqual(image.name, 'UbuntuServer9.04-Contextualized')

class OpenNebulaMockHttp(MockHttp):

    fixtures = ComputeFileFixtures('opennebula')

    def _compute(self, method, url, body, headers):
        if method == 'GET':
            body = self.fixtures.load('computes.xml')
            return (httplib.OK, body, {}, httplib.responses[httplib.OK])

        if method == 'POST':
            body = self.fixtures.load('compute.xml')
            return (httplib.CREATED, body, {}, httplib.responses[httplib.CREATED])

    def _storage(self, method, url, body, headers):
        if method == 'GET':
            body = self.fixtures.load('storage.xml')
            return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _compute_5(self, method, url, body, headers):
        if method == 'GET':
            body = self.fixtures.load('compute.xml')
            return (httplib.OK, body, {}, httplib.responses[httplib.OK])

        if method == 'PUT':
            body = ""
            return (httplib.ACCEPTED, body, {}, httplib.responses[httplib.ACCEPTED])

        if method == 'DELETE':
            body = ""
            return (httplib.NO_CONTENT, body, {}, httplib.responses[httplib.NO_CONTENT])

    def _compute_15(self, method, url, body, headers):
        if method == 'GET':
            body = self.fixtures.load('compute.xml')
            return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _storage_1(self, method, url, body, headers):
        if method == 'GET':
            body = self.fixtures.load('disk.xml')
            return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _storage_8(self, method, url, body, headers):
        if method == 'GET':
            body = self.fixtures.load('disk.xml')
            return (httplib.OK, body, {}, httplib.responses[httplib.OK])

if __name__ == '__main__':
    sys.exit(unittest.main())

########NEW FILE########
__FILENAME__ = test_rackspace
# Licensed to the Apache Software Foundation (ASF) under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import sys
import unittest
import httplib

from libcloud.common.types import InvalidCredsError
from libcloud.compute.drivers.rackspace import RackspaceNodeDriver as Rackspace
from libcloud.compute.base import Node, NodeImage, NodeSize

from test import MockHttp
from test.compute import TestCaseMixin
from test.file_fixtures import ComputeFileFixtures

from test.secrets import RACKSPACE_USER, RACKSPACE_KEY

class RackspaceTests(unittest.TestCase, TestCaseMixin):

    def setUp(self):
        Rackspace.connectionCls.conn_classes = (None, RackspaceMockHttp)
        RackspaceMockHttp.type = None
        self.driver = Rackspace(RACKSPACE_USER, RACKSPACE_KEY)

    def test_auth(self):
        RackspaceMockHttp.type = 'UNAUTHORIZED'
        try:
            self.driver = Rackspace(RACKSPACE_USER, RACKSPACE_KEY)
        except InvalidCredsError, e:
            self.assertEqual(True, isinstance(e, InvalidCredsError))
        else:
            self.fail('test should have thrown')

    def test_list_nodes(self):
        RackspaceMockHttp.type = 'EMPTY'
        ret = self.driver.list_nodes()
        self.assertEqual(len(ret), 0)
        RackspaceMockHttp.type = None
        ret = self.driver.list_nodes()
        self.assertEqual(len(ret), 1)
        node = ret[0]
        self.assertEqual('67.23.21.33', node.public_ip[0])
        self.assertEqual('10.176.168.218', node.private_ip[0])
        self.assertEqual(node.extra.get('flavorId'), '1')
        self.assertEqual(node.extra.get('imageId'), '11')
        self.assertEqual(type(node.extra.get('metadata')), type(dict()))
        RackspaceMockHttp.type = 'METADATA'
        ret = self.driver.list_nodes()
        self.assertEqual(len(ret), 1)
        node = ret[0]
        self.assertEqual(type(node.extra.get('metadata')), type(dict()))
        self.assertEqual(node.extra.get('metadata').get('somekey'), 'somevalue')
        RackspaceMockHttp.type = None

    def test_list_sizes(self):
        ret = self.driver.list_sizes()
        self.assertEqual(len(ret), 7)
        size = ret[0]
        self.assertEqual(size.name, '256 slice')

    def test_list_images(self):
        ret = self.driver.list_images()
        self.assertEqual(ret[10].extra['serverId'], None)
        self.assertEqual(ret[11].extra['serverId'], '91221')

    def test_create_node(self):
        image = NodeImage(id=11, name='Ubuntu 8.10 (intrepid)', driver=self.driver)
        size = NodeSize(1, '256 slice', None, None, None, None, driver=self.driver)
        node = self.driver.create_node(name='racktest', image=image, size=size, shared_ip_group='group1')
        self.assertEqual(node.name, 'racktest')
        self.assertEqual(node.extra.get('password'), 'racktestvJq7d3')

    def test_create_node_with_metadata(self):
        RackspaceMockHttp.type = 'METADATA'
        image = NodeImage(id=11, name='Ubuntu 8.10 (intrepid)', driver=self.driver)
        size = NodeSize(1, '256 slice', None, None, None, None, driver=self.driver)
        metadata = { 'a': 'b', 'c': 'd' }
        files = { '/file1': 'content1', '/file2': 'content2' }
        node = self.driver.create_node(name='racktest', image=image, size=size, metadata=metadata, files=files)
        self.assertEqual(node.name, 'racktest')
        self.assertEqual(node.extra.get('password'), 'racktestvJq7d3')
        self.assertEqual(node.extra.get('metadata'), metadata)

    def test_reboot_node(self):
        node = Node(id=72258, name=None, state=None, public_ip=None, private_ip=None,
                    driver=self.driver)
        ret = node.reboot()
        self.assertTrue(ret is True)

    def test_destroy_node(self):
        node = Node(id=72258, name=None, state=None, public_ip=None, private_ip=None,
                    driver=self.driver)
        ret = node.destroy()
        self.assertTrue(ret is True)

    def test_ex_limits(self):
        limits = self.driver.ex_limits()
        self.assertTrue("rate" in limits)
        self.assertTrue("absolute" in limits)

    def test_ex_save_image(self):
        node = Node(id=444222, name=None, state=None, public_ip=None, private_ip=None,
                driver=self.driver)
        image = self.driver.ex_save_image(node, "imgtest")
        self.assertEqual(image.name, "imgtest")
        self.assertEqual(image.id, "12345")

    def test_ex_list_ip_addresses(self):
        ret = self.driver.ex_list_ip_addresses(node_id=72258)
        self.assertEquals(2, len(ret.public_addresses))
        self.assertTrue('67.23.10.131' in ret.public_addresses)
        self.assertTrue('67.23.10.132' in ret.public_addresses)
        self.assertEquals(1, len(ret.private_addresses))
        self.assertTrue('10.176.42.16' in ret.private_addresses)

    def test_ex_list_ip_groups(self):
        ret = self.driver.ex_list_ip_groups()
        self.assertEquals(2, len(ret))
        self.assertEquals('1234', ret[0].id)
        self.assertEquals('Shared IP Group 1', ret[0].name)
        self.assertEquals('5678', ret[1].id)
        self.assertEquals('Shared IP Group 2', ret[1].name)
        self.assertTrue(ret[0].servers is None)

    def test_ex_list_ip_groups_detail(self):
        ret = self.driver.ex_list_ip_groups(details=True)

        self.assertEquals(2, len(ret))

        self.assertEquals('1234', ret[0].id)
        self.assertEquals('Shared IP Group 1', ret[0].name)
        self.assertEquals(2, len(ret[0].servers))
        self.assertEquals('422', ret[0].servers[0])
        self.assertEquals('3445', ret[0].servers[1])

        self.assertEquals('5678', ret[1].id)
        self.assertEquals('Shared IP Group 2', ret[1].name)
        self.assertEquals(3, len(ret[1].servers))
        self.assertEquals('23203', ret[1].servers[0])
        self.assertEquals('2456', ret[1].servers[1])
        self.assertEquals('9891', ret[1].servers[2])

    def test_ex_create_ip_group(self):
        ret = self.driver.ex_create_ip_group('Shared IP Group 1', '5467')
        self.assertEquals('1234', ret.id)
        self.assertEquals('Shared IP Group 1', ret.name)
        self.assertEquals(1, len(ret.servers))
        self.assertEquals('422', ret.servers[0])

    def test_ex_delete_ip_group(self):
        ret = self.driver.ex_delete_ip_group('5467')
        self.assertEquals(True, ret)

    def test_ex_share_ip(self):
        ret = self.driver.ex_share_ip('1234', '3445', '67.23.21.133')
        self.assertEquals(True, ret)

    def test_ex_unshare_ip(self):
        ret = self.driver.ex_unshare_ip('3445', '67.23.21.133')
        self.assertEquals(True, ret)


class RackspaceMockHttp(MockHttp):

    fixtures = ComputeFileFixtures('rackspace')

    # fake auth token response
    def _v1_0(self, method, url, body, headers):
        headers = {'x-server-management-url': 'https://servers.api.rackspacecloud.com/v1.0/slug',
                   'x-auth-token': 'FE011C19-CF86-4F87-BE5D-9229145D7A06',
                   'x-cdn-management-url': 'https://cdn.clouddrive.com/v1/MossoCloudFS_FE011C19-CF86-4F87-BE5D-9229145D7A06',
                   'x-storage-token': 'FE011C19-CF86-4F87-BE5D-9229145D7A06',
                   'x-storage-url': 'https://storage4.clouddrive.com/v1/MossoCloudFS_FE011C19-CF86-4F87-BE5D-9229145D7A06'}
        return (httplib.NO_CONTENT, "", headers, httplib.responses[httplib.NO_CONTENT])

    def _v1_0_UNAUTHORIZED(self, method, url, body, headers):
        return  (httplib.UNAUTHORIZED, "", {}, httplib.responses[httplib.UNAUTHORIZED])

    def _v1_0_slug_servers_detail_EMPTY(self, method, url, body, headers):
        body = self.fixtures.load('v1_slug_servers_detail_empty.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _v1_0_slug_servers_detail(self, method, url, body, headers):
        body = self.fixtures.load('v1_slug_servers_detail.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _v1_0_slug_servers_detail_METADATA(self, method, url, body, headers):
        body = self.fixtures.load('v1_slug_servers_detail_metadata.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _v1_0_slug_flavors_detail(self, method, url, body, headers):
        body = self.fixtures.load('v1_slug_flavors_detail.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _v1_0_slug_images(self, method, url, body, headers):
        if method != "POST":
            raise NotImplemented
        # this is currently used for creation of new image with
        # POST request, don't handle GET to avoid possible confusion
        body = self.fixtures.load('v1_slug_images_post.xml')
        return (httplib.ACCEPTED, body, {}, httplib.responses[httplib.ACCEPTED])

    def _v1_0_slug_images_detail(self, method, url, body, headers):
        body = self.fixtures.load('v1_slug_images_detail.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _v1_0_slug_servers(self, method, url, body, headers):
        body = self.fixtures.load('v1_slug_servers.xml')
        return (httplib.ACCEPTED, body, {}, httplib.responses[httplib.ACCEPTED])

    def _v1_0_slug_servers_METADATA(self, method, url, body, headers):
        body = self.fixtures.load('v1_slug_servers_metadata.xml')
        return (httplib.ACCEPTED, body, {}, httplib.responses[httplib.ACCEPTED])

    def _v1_0_slug_servers_72258_action(self, method, url, body, headers):
        if method != "POST" or body[:8] != "<reboot ":
            raise NotImplemented
        # only used by reboot() right now, but we will need to parse body someday !!!!
        return (httplib.ACCEPTED, "", {}, httplib.responses[httplib.ACCEPTED])

    def _v1_0_slug_limits(self, method, url, body, headers):
        body = self.fixtures.load('v1_slug_limits.xml')
        return (httplib.ACCEPTED, body, {}, httplib.responses[httplib.ACCEPTED])

    def _v1_0_slug_servers_72258(self, method, url, body, headers):
        if method != "DELETE":
            raise NotImplemented
        # only used by destroy node()
        return (httplib.ACCEPTED, "", {}, httplib.responses[httplib.ACCEPTED])

    def _v1_0_slug_servers_72258_ips(self, method, url, body, headers):
        body = self.fixtures.load('v1_slug_servers_ips.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _v1_0_slug_shared_ip_groups_5467(self, method, url, body, headers):
        if method != 'DELETE':
            raise NotImplemented
        return (httplib.NO_CONTENT, "", {}, httplib.responses[httplib.NO_CONTENT])

    def _v1_0_slug_shared_ip_groups(self, method, url, body, headers):

        fixture = 'v1_slug_shared_ip_group.xml' if method == 'POST' else 'v1_slug_shared_ip_groups.xml'
        body = self.fixtures.load(fixture)
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _v1_0_slug_shared_ip_groups_detail(self, method, url, body, headers):
        body = self.fixtures.load('v1_slug_shared_ip_groups_detail.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _v1_0_slug_servers_3445_ips_public_67_23_21_133(self, method, url, body, headers):
        return (httplib.ACCEPTED, "", {}, httplib.responses[httplib.ACCEPTED])



if __name__ == '__main__':
    sys.exit(unittest.main())

########NEW FILE########
__FILENAME__ = test_rimuhosting
# Licensed to the Apache Software Foundation (ASF) under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# Copyright 2009 RedRata Ltd

import sys
import unittest
import httplib

from libcloud.compute.drivers.rimuhosting import RimuHostingNodeDriver

from test import MockHttp
from test.compute import TestCaseMixin
from test.file_fixtures import ComputeFileFixtures

class RimuHostingTest(unittest.TestCase, TestCaseMixin):
    def setUp(self):
        RimuHostingNodeDriver.connectionCls.conn_classes = (None,
                                                            RimuHostingMockHttp)
        self.driver = RimuHostingNodeDriver('foo')

    def test_list_nodes(self):
        nodes = self.driver.list_nodes()
        self.assertEqual(len(nodes),1)
        node = nodes[0]
        self.assertEqual(node.public_ip[0], "1.2.3.4")
        self.assertEqual(node.public_ip[1], "1.2.3.5")
        self.assertEqual(node.extra['order_oid'], 88833465)
        self.assertEqual(node.id, "order-88833465-api-ivan-net-nz")

    def test_list_sizes(self):
        sizes = self.driver.list_sizes()
        self.assertEqual(len(sizes),1)
        size = sizes[0]
        self.assertEqual(size.ram,950)
        self.assertEqual(size.disk,20)
        self.assertEqual(size.bandwidth,75)
        self.assertEqual(size.price,32.54)

    def test_list_images(self):
        images = self.driver.list_images()
        self.assertEqual(len(images),6)
        image = images[0]
        self.assertEqual(image.name,"Debian 5.0 (aka Lenny, RimuHosting"\
                         " recommended distro)")
        self.assertEqual(image.id, "lenny")

    def test_reboot_node(self):
        # Raises exception on failure
        node = self.driver.list_nodes()[0]
        self.driver.reboot_node(node)

    def test_destroy_node(self):
        # Raises exception on failure
        node = self.driver.list_nodes()[0]
        self.driver.destroy_node(node)

    def test_create_node(self):
        # Raises exception on failure
        size = self.driver.list_sizes()[0]
        image = self.driver.list_images()[0]
        self.driver.create_node(name="api.ivan.net.nz", image=image, size=size)

class RimuHostingMockHttp(MockHttp):

    fixtures = ComputeFileFixtures('rimuhosting')

    def _r_orders(self,method,url,body,headers):
        body = self.fixtures.load('r_orders.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _r_pricing_plans(self,method,url,body,headers):
        body = self.fixtures.load('r_pricing_plans.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _r_distributions(self, method, url, body, headers):
        body = self.fixtures.load('r_distributions.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _r_orders_new_vps(self, method, url, body, headers):
        body = self.fixtures.load('r_orders_new_vps.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _r_orders_order_88833465_api_ivan_net_nz_vps(self, method, url, body, headers):
        body = self.fixtures.load('r_orders_order_88833465_api_ivan_net_nz_vps.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _r_orders_order_88833465_api_ivan_net_nz_vps_running_state(self, method,
                                                                   url, body,
                                                                   headers):
        body = self.fixtures.load('r_orders_order_88833465_api_ivan_net_nz_vps_running_state.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])


if __name__ == '__main__':
    sys.exit(unittest.main())

########NEW FILE########
__FILENAME__ = test_slicehost
# Licensed to the Apache Software Foundation (ASF) under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import sys
import unittest
import httplib

from xml.etree import ElementTree as ET

from libcloud.compute.drivers.slicehost import SlicehostNodeDriver as Slicehost
from libcloud.compute.types import NodeState, InvalidCredsError
from libcloud.compute.base import Node, NodeImage, NodeSize

from test import MockHttp
from test.compute import TestCaseMixin
from test.file_fixtures import ComputeFileFixtures
from test.secrets import SLICEHOST_KEY

class SlicehostTest(unittest.TestCase, TestCaseMixin):

    def setUp(self):

        Slicehost.connectionCls.conn_classes = (None, SlicehostMockHttp)
        SlicehostMockHttp.type = None
        self.driver = Slicehost(SLICEHOST_KEY)

    def test_list_nodes(self):
        ret = self.driver.list_nodes()
        self.assertEqual(len(ret), 1)
        node = ret[0]
        self.assertTrue('174.143.212.229' in node.public_ip)
        self.assertTrue('10.176.164.199' in node.private_ip)
        self.assertEqual(node.state, NodeState.PENDING)

        SlicehostMockHttp.type = 'UNAUTHORIZED'
        try:
            ret = self.driver.list_nodes()
        except InvalidCredsError, e:
            self.assertEqual(e.value, 'HTTP Basic: Access denied.')
        else:
            self.fail('test should have thrown')

    def test_list_sizes(self):
        ret = self.driver.list_sizes()
        self.assertEqual(len(ret), 7)
        size = ret[0]
        self.assertEqual(size.name, '256 slice')

    def test_list_images(self):
        ret = self.driver.list_images()
        self.assertEqual(len(ret), 11)
        image = ret[0]
        self.assertEqual(image.name, 'CentOS 5.2')
        self.assertEqual(image.id, '2')

    def test_reboot_node(self):
        node = Node(id=1, name=None, state=None, public_ip=None, private_ip=None,
                    driver=self.driver)

        ret = node.reboot()
        self.assertTrue(ret is True)

        ret = self.driver.reboot_node(node)
        self.assertTrue(ret is True)

        SlicehostMockHttp.type = 'FORBIDDEN'
        try:
            ret = self.driver.reboot_node(node)
        except Exception, e:
            self.assertEqual(e.args[0], 'Permission denied')
        else:
            self.fail('test should have thrown')

    def test_destroy_node(self):
        node = Node(id=1, name=None, state=None, public_ip=None, private_ip=None,
                    driver=self.driver)

        ret = node.destroy()
        self.assertTrue(ret is True)

        ret = self.driver.destroy_node(node)
        self.assertTrue(ret is True)

    def test_create_node(self):
        image = NodeImage(id=11, name='ubuntu 8.10', driver=self.driver)
        size = NodeSize(1, '256 slice', None, None, None, None, driver=self.driver)
        node = self.driver.create_node(name='slicetest', image=image, size=size)
        self.assertEqual(node.name, 'slicetest')
        self.assertEqual(node.extra.get('password'), 'fooadfa1231')

class SlicehostMockHttp(MockHttp):

    fixtures = ComputeFileFixtures('slicehost')

    def _slices_xml(self, method, url, body, headers):
        if method == 'POST':
            tree = ET.XML(body)
            name = tree.findtext('name')
            image_id = int(tree.findtext('image-id'))
            flavor_id = int(tree.findtext('flavor-id'))

            # TODO: would be awesome to get the slicehost api developers to fill in the
            # the correct validation logic
            if not (name and image_id and flavor_id) \
                or tree.tag != 'slice' \
                or not headers.has_key('Content-Type')  \
                or headers['Content-Type'] != 'application/xml':

                err_body = self.fixtures.load('slices_error.xml')
                return (httplib.UNPROCESSABLE_ENTITY, err_body, {}, '')

            body = self.fixtures.load('slices_post.xml')
            return (httplib.CREATED, body, {}, '')
        else:
            body = self.fixtures.load('slices_get.xml')
            return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _slices_xml_UNAUTHORIZED(self, method, url, body, headers):
        err_body = 'HTTP Basic: Access denied.'
        return (httplib.UNAUTHORIZED, err_body, {},
                httplib.responses[httplib.UNAUTHORIZED])

    def _flavors_xml(self, method, url, body, headers):
        body = self.fixtures.load('flavors.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _images_xml(self, method, url, body, headers):
        body = self.fixtures.load('images.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _slices_1_reboot_xml(self, method, url, body, headers):
        body = self.fixtures.load('slices_1_reboot.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _slices_1_reboot_xml_FORBIDDEN(self, method, url, body, headers):
        body = self.fixtures.load('slices_1_reboot_forbidden.xml')
        return (httplib.FORBIDDEN, body, {}, httplib.responses[httplib.FORBIDDEN])

    def _slices_1_destroy_xml(self, method, url, body, headers):
        body = ''
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

if __name__ == '__main__':
    sys.exit(unittest.main())

########NEW FILE########
__FILENAME__ = test_softlayer
# Licensed to the Apache Software Foundation (ASF) under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import httplib
import unittest
import sys

from xml.etree import ElementTree as ET
import xmlrpclib

from libcloud.compute.drivers.softlayer import SoftLayerNodeDriver as SoftLayer
from libcloud.compute.types import NodeState

from test import MockHttp
from test.compute import TestCaseMixin
from test.file_fixtures import ComputeFileFixtures

from test.secrets import SOFTLAYER_USER, SOFTLAYER_APIKEY

class MockSoftLayerTransport(xmlrpclib.Transport):

    def request(self, host, handler, request_body, verbose=0):
        self.verbose = 0
        method = ET.XML(request_body).find('methodName').text
        mock = SoftLayerMockHttp(host, 80)
        mock.request('POST', "%s/%s" % (handler, method))
        resp = mock.getresponse()

        return self._parse_response(resp.body, None)

class SoftLayerTests(unittest.TestCase):

    def setUp(self):
        SoftLayer.connectionCls.proxyCls.transportCls = [MockSoftLayerTransport, MockSoftLayerTransport]
        self.driver = SoftLayer(SOFTLAYER_USER, SOFTLAYER_APIKEY)

    def test_list_nodes(self):
        node = self.driver.list_nodes()[0]
        self.assertEqual(node.name, 'test1')
        self.assertEqual(node.state, NodeState.RUNNING)
        self.assertEqual(node.extra['password'], 'TEST')

    def test_list_locations(self):
        locations = self.driver.list_locations()
        seattle = (l for l in locations if l.name == 'sea01').next()
        self.assertEqual(seattle.country, 'US')
        self.assertEqual(seattle.id, '18171')

    def test_list_images(self):
        images = self.driver.list_images()
        image = images[0]
        self.assertEqual(image.id, '1684')

    def test_list_sizes(self):
        sizes = self.driver.list_sizes()
        self.assertEqual(len(sizes), 2)
        self.assertEqual(sizes[0].id, 'sl1')

class SoftLayerMockHttp(MockHttp):
    fixtures = ComputeFileFixtures('softlayer')

    def _xmlrpc_v3_SoftLayer_Account_getVirtualGuests(self, method, url, body, headers):
        body = self.fixtures.load('v3_SoftLayer_Account_getVirtualGuests.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _xmlrpc_v3_SoftLayer_Location_Datacenter_getDatacenters(self, method, url, body, headers):
        body = self.fixtures.load('v3_SoftLayer_Location_Datacenter_getDatacenters.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

if __name__ == '__main__':
    sys.exit(unittest.main())

########NEW FILE########
__FILENAME__ = test_vcloud
# Licensed to the Apache Software Foundation (ASF) under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import sys
import unittest
import httplib

from libcloud.compute.drivers.vcloud import TerremarkDriver
from libcloud.compute.drivers.vcloud import VCloudNodeDriver
from libcloud.compute.base import Node
from libcloud.compute.types import NodeState

from test import MockHttp
from test.compute import TestCaseMixin
from test.file_fixtures import ComputeFileFixtures

from test.secrets import TERREMARK_USER, TERREMARK_SECRET

class TerremarkTests(unittest.TestCase, TestCaseMixin):

    def setUp(self):
        VCloudNodeDriver.connectionCls.host = "test"
        VCloudNodeDriver.connectionCls.conn_classes = (None, TerremarkMockHttp)
        TerremarkMockHttp.type = None
        self.driver = TerremarkDriver(TERREMARK_USER, TERREMARK_SECRET)

    def test_list_images(self):
        ret = self.driver.list_images()
        self.assertEqual(ret[0].id,'https://services.vcloudexpress.terremark.com/api/v0.8/vAppTemplate/5')

    def test_list_sizes(self):
        ret = self.driver.list_sizes()
        self.assertEqual(ret[0].ram, 512)

    def test_create_node(self):
        image = self.driver.list_images()[0]
        size = self.driver.list_sizes()[0]
        node = self.driver.create_node(
            name='testerpart2',
            image=image,
            size=size,
            vdc='https://services.vcloudexpress.terremark.com/api/v0.8/vdc/224',
            network='https://services.vcloudexpress.terremark.com/api/v0.8/network/725',
            cpus=2,
        )
        self.assertTrue(isinstance(node, Node))
        self.assertEqual(node.id, 'https://services.vcloudexpress.terremark.com/api/v0.8/vapp/14031')
        self.assertEqual(node.name, 'testerpart2')

    def test_list_nodes(self):
        ret = self.driver.list_nodes()
        node = ret[0]
        self.assertEqual(node.id, 'https://services.vcloudexpress.terremark.com/api/v0.8/vapp/14031')
        self.assertEqual(node.name, 'testerpart2')
        self.assertEqual(node.state, NodeState.RUNNING)
        self.assertEqual(node.public_ip, [])
        self.assertEqual(node.private_ip, ['10.112.78.69'])

    def test_reboot_node(self):
        node = self.driver.list_nodes()[0]
        ret = self.driver.reboot_node(node)
        self.assertTrue(ret)

    def test_destroy_node(self):
        node = self.driver.list_nodes()[0]
        ret = self.driver.destroy_node(node)
        self.assertTrue(ret)


class TerremarkMockHttp(MockHttp):

    fixtures = ComputeFileFixtures('terremark')

    def _api_v0_8_login(self, method, url, body, headers):
        headers['set-cookie'] = 'vcloud-token=testtoken'
        body = self.fixtures.load('api_v0_8_login.xml')
        return (httplib.OK, body, headers, httplib.responses[httplib.OK])

    def _api_v0_8_org_240(self, method, url, body, headers):
        body = self.fixtures.load('api_v0_8_org_240.xml')
        return (httplib.OK, body, headers, httplib.responses[httplib.OK])

    def _api_v0_8_vdc_224(self, method, url, body, headers):
        body = self.fixtures.load('api_v0_8_vdc_224.xml')
        return (httplib.OK, body, headers, httplib.responses[httplib.OK])

    def _api_v0_8_vdc_224_catalog(self, method, url, body, headers):
        body = self.fixtures.load('api_v0_8_vdc_224_catalog.xml')
        return (httplib.OK, body, headers, httplib.responses[httplib.OK])

    def _api_v0_8_catalogItem_5(self, method, url, body, headers):
        body = self.fixtures.load('api_v0_8_catalogItem_5.xml')
        return (httplib.OK, body, headers, httplib.responses[httplib.OK])

    def _api_v0_8_vdc_224_action_instantiateVAppTemplate(self, method, url, body, headers):
        body = self.fixtures.load('api_v0_8_vdc_224_action_instantiateVAppTemplate.xml')
        return (httplib.OK, body, headers, httplib.responses[httplib.OK])

    def _api_v0_8_vapp_14031_action_deploy(self, method, url, body, headers):
        body = self.fixtures.load('api_v0_8_vapp_14031_action_deploy.xml')
        return (httplib.ACCEPTED, body, headers, httplib.responses[httplib.ACCEPTED])

    def _api_v0_8_task_10496(self, method, url, body, headers):
        body = self.fixtures.load('api_v0_8_task_10496.xml')
        return (httplib.ACCEPTED, body, headers, httplib.responses[httplib.ACCEPTED])

    def _api_v0_8_vapp_14031_power_action_powerOn(self, method, url, body, headers):
        body = self.fixtures.load('api_v0_8_vapp_14031_power_action_powerOn.xml')
        return (httplib.ACCEPTED, body, headers, httplib.responses[httplib.ACCEPTED])

    def _api_v0_8_vapp_14031(self, method, url, body, headers):
        if method == 'GET':
            body = self.fixtures.load('api_v0_8_vapp_14031_get.xml')
        elif method == 'DELETE':
            body = ''
        return (httplib.ACCEPTED, body, headers, httplib.responses[httplib.ACCEPTED])

    def _api_v0_8_vapp_14031_power_action_reset(self, method, url, body, headers):
        body = self.fixtures.load('api_v0_8_vapp_14031_power_action_reset.xml')
        return (httplib.ACCEPTED, body, headers, httplib.responses[httplib.ACCEPTED])

    def _api_v0_8_vapp_14031_power_action_poweroff(self, method, url, body, headers):
        body = self.fixtures.load('api_v0_8_vapp_14031_power_action_poweroff.xml')
        return (httplib.ACCEPTED, body, headers, httplib.responses[httplib.ACCEPTED])

    def _api_v0_8_task_11001(self, method, url, body, headers):
        body = self.fixtures.load('api_v0_8_task_11001.xml')
        return (httplib.ACCEPTED, body, headers, httplib.responses[httplib.ACCEPTED])

if __name__ == '__main__':
    sys.exit(unittest.main())

########NEW FILE########
__FILENAME__ = test_voxel
# Licensed to the Apache Software Foundation (ASF) under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import sys
import unittest
import httplib

from libcloud.compute.drivers.voxel import VoxelNodeDriver as Voxel
from libcloud.compute.types import InvalidCredsError

from test import MockHttp
from test.file_fixtures import ComputeFileFixtures

from test.secrets import VOXEL_KEY, VOXEL_SECRET

class VoxelTest(unittest.TestCase):

    def setUp(self):

        Voxel.connectionCls.conn_classes = (None, VoxelMockHttp)
        VoxelMockHttp.type = None
        self.driver = Voxel(VOXEL_KEY, VOXEL_SECRET)

    def test_auth_failed(self):
        VoxelMockHttp.type = 'UNAUTHORIZED'
        try:
            self.driver.list_nodes()
        except Exception, e:
            self.assertTrue(isinstance(e, InvalidCredsError))
        else:
            self.fail('test should have thrown')

class VoxelMockHttp(MockHttp):

    fixtures = ComputeFileFixtures('voxel')

    def _UNAUTHORIZED(self, method, url, body, headers):
        body = self.fixtures.load('unauthorized.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

if __name__ == '__main__':
    sys.exit(unittest.main())

########NEW FILE########
__FILENAME__ = test_vpsnet
# Licensed to the Apache Software Foundation (ASF) under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import sys
import unittest
import exceptions
import httplib

from libcloud.compute.drivers.vpsnet import VPSNetNodeDriver
from libcloud.compute.base import Node
from libcloud.compute.types import NodeState

from test import MockHttp
from test.compute import TestCaseMixin

from test.secrets import VPSNET_USER, VPSNET_KEY

class VPSNetTests(unittest.TestCase, TestCaseMixin):

    def setUp(self):
        VPSNetNodeDriver.connectionCls.conn_classes = (None, VPSNetMockHttp)
        self.driver = VPSNetNodeDriver(VPSNET_USER, VPSNET_KEY)

    def test_create_node(self):
        VPSNetMockHttp.type = 'create'
        image = self.driver.list_images()[0]
        size = self.driver.list_sizes()[0]
        node = self.driver.create_node('foo', image, size)
        self.assertEqual(node.name, 'foo')

    def test_list_nodes(self):
        VPSNetMockHttp.type = 'virtual_machines'
        node = self.driver.list_nodes()[0]
        self.assertEqual(node.id, '1384')
        self.assertEqual(node.state, NodeState.RUNNING)

    def test_reboot_node(self):
        VPSNetMockHttp.type = 'virtual_machines'
        node = self.driver.list_nodes()[0]

        VPSNetMockHttp.type = 'reboot'
        ret = self.driver.reboot_node(node)
        self.assertEqual(ret, True)

    def test_destroy_node(self):
        VPSNetMockHttp.type = 'delete'
        node = Node('2222', None, None, None, None, self.driver)
        ret = self.driver.destroy_node(node)
        self.assertTrue(ret)
        VPSNetMockHttp.type = 'delete_fail'
        node = Node('2223', None, None, None, None, self.driver)
        self.assertRaises(exceptions.Exception, self.driver.destroy_node, node)

    def test_list_images(self):
        VPSNetMockHttp.type = 'templates'
        ret = self.driver.list_images()
        self.assertEqual(ret[0].id, '9')
        self.assertEqual(ret[-1].id, '160')

    def test_list_sizes(self):
        VPSNetMockHttp.type = 'sizes'
        ret = self.driver.list_sizes()
        self.assertEqual(len(ret), 1)
        self.assertEqual(ret[0].id, '1')
        self.assertEqual(ret[0].name, '1 Node')

    def test_destroy_node_response(self):
        # should return a node object
        node = Node('2222', None, None, None, None, self.driver)
        VPSNetMockHttp.type = 'delete'
        ret = self.driver.destroy_node(node)
        self.assertTrue(isinstance(ret, bool))

    def test_reboot_node_response(self):
        # should return a node object
        VPSNetMockHttp.type = 'virtual_machines'
        node = self.driver.list_nodes()[0]
        VPSNetMockHttp.type = 'reboot'
        ret = self.driver.reboot_node(node)
        self.assertTrue(isinstance(ret, bool))



class VPSNetMockHttp(MockHttp):


    def _nodes_api10json_sizes(self, method, url, body, headers):
        body = """[{"slice":{"virtual_machine_id":8592,"id":12256,"consumer_id":0}},
                   {"slice":{"virtual_machine_id":null,"id":12258,"consumer_id":0}},
                   {"slice":{"virtual_machine_id":null,"id":12434,"consumer_id":0}}]"""
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _nodes_api10json_create(self, method, url, body, headers):
        body = """[{"slice":{"virtual_machine_id":8592,"id":12256,"consumer_id":0}},
                   {"slice":{"virtual_machine_id":null,"id":12258,"consumer_id":0}},
                   {"slice":{"virtual_machine_id":null,"id":12434,"consumer_id":0}}]"""
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _virtual_machines_2222_api10json_delete_fail(self, method, url, body, headers):
        return (httplib.FORBIDDEN, '', {}, httplib.responses[httplib.FORBIDDEN])

    def _virtual_machines_2222_api10json_delete(self, method, url, body, headers):
        return (httplib.OK, '', {}, httplib.responses[httplib.OK])

    def _virtual_machines_1384_reboot_api10json_reboot(self, method, url, body, headers):
        body = """{
              "virtual_machine":
                {
                  "running": true,
                  "updated_at": "2009-05-15T06:55:02-04:00",
                  "power_action_pending": false,
                  "system_template_id": 41,
                  "id": 1384,
                  "cloud_id": 3,
                  "domain_name": "demodomain.com",
                  "hostname": "web01",
                  "consumer_id": 0,
                  "backups_enabled": false,
                  "password": "a8hjsjnbs91",
                  "label": "foo",
                  "slices_count": null,
                  "created_at": "2009-04-16T08:17:39-04:00"
                }
              }"""
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _virtual_machines_api10json_create(self, method, url, body, headers):
        body = """{
              "virtual_machine":
                {
                  "running": true,
                  "updated_at": "2009-05-15T06:55:02-04:00",
                  "power_action_pending": false,
                  "system_template_id": 41,
                  "id": 1384,
                  "cloud_id": 3,
                  "domain_name": "demodomain.com",
                  "hostname": "web01",
                  "consumer_id": 0,
                  "backups_enabled": false,
                  "password": "a8hjsjnbs91",
                  "label": "foo",
                  "slices_count": null,
                  "created_at": "2009-04-16T08:17:39-04:00"
                }
              }"""
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _virtual_machines_api10json_virtual_machines(self, method, url, body, headers):
        body = """     [{
              "virtual_machine":
                {
                  "running": true,
                  "updated_at": "2009-05-15T06:55:02-04:00",
                  "power_action_pending": false,
                  "system_template_id": 41,
                  "id": 1384,
                  "cloud_id": 3,
                  "domain_name": "demodomain.com",
                  "hostname": "web01",
                  "consumer_id": 0,
                  "backups_enabled": false,
                  "password": "a8hjsjnbs91",
                  "label": "Web Server 01",
                  "slices_count": null,
                  "created_at": "2009-04-16T08:17:39-04:00"
                }
              },
              {
                "virtual_machine":
                  {
                    "running": true,
                    "updated_at": "2009-05-15T06:55:02-04:00",
                    "power_action_pending": false,
                    "system_template_id": 41,
                    "id": 1385,
                    "cloud_id": 3,
                    "domain_name": "demodomain.com",
                    "hostname": "mysql01",
                    "consumer_id": 0,
                    "backups_enabled": false,
                    "password": "dsi8h38hd2s",
                    "label": "MySQL Server 01",
                    "slices_count": null,
                    "created_at": "2009-04-16T08:17:39-04:00"
                  }
                }]"""
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _available_clouds_api10json_templates(self, method, url, body, headers):
        body = """[{"cloud":{"system_templates":[{"id":9,"label":"Ubuntu 8.04 x64"},{"id":10,"label":"CentOS 5.2 x64"},{"id":11,"label":"Gentoo 2008.0 x64"},{"id":18,"label":"Ubuntu 8.04 x64 LAMP"},{"id":19,"label":"Ubuntu 8.04 x64 MySQL"},{"id":20,"label":"Ubuntu 8.04 x64 Postfix"},{"id":21,"label":"Ubuntu 8.04 x64 Apache"},{"id":22,"label":"CentOS 5.2 x64 MySQL"},{"id":23,"label":"CentOS 5.2 x64 LAMP"},{"id":24,"label":"CentOS 5.2 x64 HAProxy"},{"id":25,"label":"CentOS 5.2 x64 Postfix"},{"id":26,"label":"CentOS 5.2 x64 Varnish"},{"id":27,"label":"CentOS 5.2 x64 Shoutcast"},{"id":28,"label":"CentOS 5.2 x64 Apache"},{"id":40,"label":"cPanel"},{"id":42,"label":"Debian 5.0 (Lenny) x64"},{"id":58,"label":"Django on Ubuntu 8.04 (x86)"},{"id":59,"label":"Drupal 5 on Ubuntu 8.04 (x86)"},{"id":60,"label":"Drupal 6 on Ubuntu 8.04 (x86)"},{"id":61,"label":"Google App Engine on Ubuntu 8.04 (x86)"},{"id":62,"label":"LAMP on Ubuntu 8.04 (x86)"},{"id":63,"label":"LAPP on Ubuntu 8.04 (x86)"},{"id":64,"label":"MediaWiki on Ubuntu 8.04 (x86)"},{"id":65,"label":"MySQL on Ubuntu 8.04 (x86)"},{"id":66,"label":"phpBB on Ubuntu 8.04 (x86)"},{"id":67,"label":"PostgreSQL on Ubuntu 8.04 (x86)"},{"id":68,"label":"Rails on Ubuntu 8.04 (x86)"},{"id":69,"label":"Tomcat on Ubuntu 8.04 (x86)"},{"id":70,"label":"Wordpress on Ubuntu 8.04 (x86)"},{"id":71,"label":"Joomla on Ubuntu 8.04 (x86)"},{"id":72,"label":"Ubuntu 8.04 Default Install (turnkey)"},{"id":128,"label":"CentOS Optimised"},{"id":129,"label":"Optimised CentOS + Apache + MySQL + PHP"},{"id":130,"label":"Optimised CentOS + Apache + MySQL + Ruby"},{"id":131,"label":"Optimised CentOS + Apache + MySQL + Ruby + PHP"},{"id":132,"label":"Debian Optimised"},{"id":133,"label":"Optimised Debian + Apache + MySQL + PHP"},{"id":134,"label":"Optimised Debian + NGINX + MySQL + PHP"},{"id":135,"label":"Optimised Debian + Lighttpd + MySQL + PHP"},{"id":136,"label":"Optimised Debian + Apache + MySQL + Ruby + PHP"},{"id":137,"label":"Optimised Debian + Apache + MySQL + Ruby"},{"id":138,"label":"Optimised Debian + NGINX + MySQL + Ruby + PHP"},{"id":139,"label":"Optimised Debian + NGINX + MySQL + Ruby"},{"id":140,"label":"Optimised Debian + Apache + MySQL + PHP + Magento"},{"id":141,"label":"Optimised Debian + NGINX + MySQL + PHP + Magento"},{"id":142,"label":"Optimised Debian + Lighttpd + MySQL + PHP + Wordpress"}],"id":2,"label":"USA VPS Cloud"}},{"cloud":{"system_templates":[{"id":15,"label":"Ubuntu 8.04 x64"},{"id":16,"label":"CentOS 5.2 x64"},{"id":17,"label":"Gentoo 2008.0 x64"},{"id":29,"label":"Ubuntu 8.04 x64 LAMP"},{"id":30,"label":"Ubuntu 8.04 x64 MySQL"},{"id":31,"label":"Ubuntu 8.04 x64 Postfix"},{"id":32,"label":"Ubuntu 8.04 x64 Apache"},{"id":33,"label":"CentOS 5.2 x64 MySQL"},{"id":34,"label":"CentOS 5.2 x64 LAMP"},{"id":35,"label":"CentOS 5.2 x64 HAProxy"},{"id":36,"label":"CentOS 5.2 x64 Postfix"},{"id":37,"label":"CentOS 5.2 x64 Varnish"},{"id":38,"label":"CentOS 5.2 x64 Shoutcast"},{"id":39,"label":"CentOS 5.2 x64 Apache"},{"id":41,"label":"cPanel"},{"id":43,"label":"Debian 5.0 (Lenny) x64"},{"id":44,"label":"Django on Ubuntu 8.04 (x86)"},{"id":45,"label":"Drupal 5 on Ubuntu 8.04 (x86)"},{"id":46,"label":"Drupal 6 on Ubuntu 8.04 (x86)"},{"id":47,"label":"Google App Engine on Ubuntu 8.04 (x86)"},{"id":48,"label":"LAMP on Ubuntu 8.04 (x86)"},{"id":49,"label":"LAPP on Ubuntu 8.04 (x86)"},{"id":50,"label":"MediaWiki on Ubuntu 8.04 (x86)"},{"id":51,"label":"MySQL on Ubuntu 8.04 (x86)"},{"id":52,"label":"phpBB on Ubuntu 8.04 (x86)"},{"id":53,"label":"PostgreSQL on Ubuntu 8.04 (x86)"},{"id":54,"label":"Rails on Ubuntu 8.04 (x86)"},{"id":55,"label":"Tomcat on Ubuntu 8.04 (x86)"},{"id":56,"label":"Wordpress on Ubuntu 8.04 (x86)"},{"id":57,"label":"Joomla on Ubuntu 8.04 (x86)"},{"id":73,"label":"Ubuntu 8.04 Default Install (turnkey)"},{"id":148,"label":"CentOS Optimised"},{"id":149,"label":"Optimised CentOS + Apache + MySQL + PHP"},{"id":150,"label":"Optimised CentOS + Apache + MySQL + Ruby"},{"id":151,"label":"Optimised CentOS + Apache + MySQL + Ruby + PHP"},{"id":152,"label":"Debian Optimised"},{"id":153,"label":"Optimised Debian + Apache + MySQL + PHP"},{"id":154,"label":"Optimised Debian + NGINX + MySQL + PHP"},{"id":155,"label":"Optimised Debian + Lighttpd + MySQL + PHP"},{"id":156,"label":"Optimised Debian + Apache + MySQL + Ruby + PHP"},{"id":157,"label":"Optimised Debian + Apache + MySQL + Ruby"},{"id":158,"label":"Optimised Debian + NGINX + MySQL + Ruby + PHP"},{"id":159,"label":"Optimised Debian + NGINX + MySQL + Ruby"},{"id":160,"label":"Optimised Debian + Lighttpd + MySQL + PHP + Wordpress"}],"id":3,"label":"UK VPS Cloud"}}]"""
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])
    def _available_clouds_api10json_create(self, method, url, body, headers):
        body = """[{"cloud":{"system_templates":[{"id":9,"label":"Ubuntu 8.04 x64"}],"id":2,"label":"USA VPS Cloud"}}]"""
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

if __name__ == '__main__':
    sys.exit(unittest.main())

########NEW FILE########
__FILENAME__ = file_fixtures
# Licensed to the Apache Software Foundation (ASF) under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# Helper class for loading large fixture data

import os

FIXTURES_ROOT = {
    'compute': 'compute/fixtures',
    'storage': 'storage/fixtures'
}

class FileFixtures(object):
    def __init__(self, fixtures_type, sub_dir=''):
        script_dir = os.path.abspath(os.path.split(__file__)[0])
        self.root = os.path.join(script_dir, FIXTURES_ROOT[fixtures_type], 
                                 sub_dir)

    def load(self, file):
        path = os.path.join(self.root, file)
        if os.path.exists(path):
            return open(path, 'r').read()
        else:
            raise IOError

class ComputeFileFixtures(FileFixtures):
    def __init__(self, sub_dir=''):
        super(ComputeFileFixtures, self).__init__(fixtures_type='compute',
                                                  sub_dir=sub_dir)

class StorageFileFixtures(FileFixtures):
    def __init__(self, sub_dir=''):
        super(StorageFileFixtures, self).__init__(fixtures_type='storage',
                                                  sub_dir=sub_dir)

########NEW FILE########
__FILENAME__ = test_cloudfiles
# Licensed to the Apache Software Foundation (ASF) under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import os
import os.path
import random
import sys
import copy
import unittest
import httplib

import libcloud.utils

from libcloud.common.types import LibcloudError
from libcloud.storage.base import Container, Object
from libcloud.storage.types import ContainerAlreadyExistsError
from libcloud.storage.types import ContainerDoesNotExistError
from libcloud.storage.types import ContainerIsNotEmptyError
from libcloud.storage.types import ObjectDoesNotExistError
from libcloud.storage.types import ObjectHashMismatchError
from libcloud.storage.drivers.cloudfiles import CloudFilesStorageDriver
from libcloud.storage.drivers.dummy import DummyFileObject, DummyIterator

from test import MockHttp, MockRawResponse
from test.file_fixtures import StorageFileFixtures

class CloudFilesTests(unittest.TestCase):

    def setUp(self):
        CloudFilesStorageDriver.connectionCls.conn_classes = (None,
                                                              CloudFilesMockHttp)
        CloudFilesStorageDriver.connectionCls.rawResponseCls = CloudFilesMockRawResponse
        CloudFilesMockHttp.type = None
        CloudFilesMockRawResponse.type = None
        self.driver = CloudFilesStorageDriver('dummy', 'dummy')
        self._remove_test_file()

    def tearDown(self):
        self._remove_test_file()

    def test_get_meta_data(self):
        meta_data = self.driver.get_meta_data()

    def test_list_containers(self):
        CloudFilesMockHttp.type = 'EMPTY'
        containers = self.driver.list_containers()
        self.assertEqual(len(containers), 0)

        CloudFilesMockHttp.type = None
        containers = self.driver.list_containers()
        self.assertEqual(len(containers), 3)

        container = [c for c in containers if c.name == 'container2'][0]
        self.assertEqual(container.extra['object_count'], 120)
        self.assertEqual(container.extra['size'], 340084450)

    def test_list_container_objects(self):
        CloudFilesMockHttp.type = 'EMPTY'
        container = Container(name='test_container', extra={}, driver=self.driver)
        objects = self.driver.list_container_objects(container=container)
        self.assertEqual(len(objects), 0)

        CloudFilesMockHttp.type = None
        objects = self.driver.list_container_objects(container=container)
        self.assertEqual(len(objects), 4)

        obj = [o for o in objects if o.name == 'foo test 1'][0]
        self.assertEqual(obj.hash, '16265549b5bda64ecdaa5156de4c97cc')
        self.assertEqual(obj.size, 1160520)
        self.assertEqual(obj.container.name, 'test_container')

    def test_get_container(self):
        container = self.driver.get_container(container_name='test_container')
        self.assertEqual(container.name, 'test_container')
        self.assertEqual(container.extra['object_count'], 800)
        self.assertEqual(container.extra['size'], 1234568)

    def test_get_object(self):
        obj = self.driver.get_object(container_name='test_container',
                                     object_name='test_object')
        self.assertEqual(obj.container.name, 'test_container')
        self.assertEqual(obj.size, 555)
        self.assertEqual(obj.extra['content_type'], 'application/zip')
        self.assertEqual(obj.extra['etag'], '6b21c4a111ac178feacf9ec9d0c71f17')
        self.assertEqual(obj.extra['last_modified'], 'Tue, 25 Jan 2011 22:01:49 GMT')
        self.assertEqual(obj.meta_data['foo-bar'], 'test 1')
        self.assertEqual(obj.meta_data['bar-foo'], 'test 2')

    def test_create_container_success(self):
        container = self.driver.create_container(container_name='test_create_container')
        self.assertTrue(isinstance(container, Container))
        self.assertEqual(container.name, 'test_create_container')
        self.assertEqual(container.extra['object_count'], 0)

    def test_create_container_already_exists(self):
        CloudFilesMockHttp.type = 'ALREADY_EXISTS'

        try:
            container = self.driver.create_container(container_name='test_create_container')
        except ContainerAlreadyExistsError:
            pass
        else:
            self.fail('Container already exists but an exception was not thrown')

    def test_create_container_invalid_name(self):
        try:
            container = self.driver.create_container(container_name='invalid//name/')
        except:
            pass
        else:
            self.fail('Invalid name was provided (name contains slashes), but exception was not thrown')

    def test_create_container_invalid_name(self):
        name = ''.join([ 'x' for x in range(0, 257)])
        try:
            container = self.driver.create_container(container_name=name)
        except:
            pass
        else:
            self.fail('Invalid name was provided (name is too long), but exception was not thrown')

    def test_delete_container_success(self):
        container = Container(name='foo_bar_container', extra={}, driver=self)
        result = self.driver.delete_container(container=container)
        self.assertTrue(result)

    def test_delete_container_not_found(self):
        CloudFilesMockHttp.type = 'NOT_FOUND'
        container = Container(name='foo_bar_container', extra={}, driver=self)
        try:
            result = self.driver.delete_container(container=container)
        except ContainerDoesNotExistError:
            pass
        else:
            self.fail('Container does not exist but an exception was not thrown')

    def test_delete_container_not_empty(self):
        CloudFilesMockHttp.type = 'NOT_EMPTY'
        container = Container(name='foo_bar_container', extra={}, driver=self)
        try:
            result = self.driver.delete_container(container=container)
        except ContainerIsNotEmptyError:
            pass
        else:
            self.fail('Container is not empty but an exception was not thrown')

    def test_download_object_success(self):
        container = Container(name='foo_bar_container', extra={}, driver=self)
        obj = Object(name='foo_bar_object', size=1000, hash=None, extra={},
                     container=container, meta_data=None,
                     driver=CloudFilesStorageDriver)
        destination_path = os.path.abspath(__file__) + '.temp'
        result = self.driver.download_object(obj=obj,
                                             destination_path=destination_path,
                                             overwrite_existing=False,
                                             delete_on_failure=True)
        self.assertTrue(result)

    def test_download_object_invalid_file_size(self):
        CloudFilesMockRawResponse.type = 'INVALID_SIZE'
        container = Container(name='foo_bar_container', extra={}, driver=self)
        obj = Object(name='foo_bar_object', size=1000, hash=None, extra={},
                     container=container, meta_data=None,
                     driver=CloudFilesStorageDriver)
        destination_path = os.path.abspath(__file__) + '.temp'
        result = self.driver.download_object(obj=obj,
                                             destination_path=destination_path,
                                             overwrite_existing=False,
                                             delete_on_failure=True)
        self.assertFalse(result)

    def download_object_success_not_found(self):
        CloudFilesMockHttp.type = 'NOT_FOUND'
        obj = Object(name='foo_bar_object', size=1000, hash=None, extra={},
                     container=container, meta_data=None,
                     driver=CloudFilesStorageDriver)
        destination_path = os.path.abspath(__file__)
        try:
            result = self.driver.download_object(obj=obj,
                                                 destination_path=destination_path,
                                                 overwrite_existing=False,
                                                 delete_on_failure=True)
        except ObjectDoesNotExistError:
            pass
        else:
            self.fail('Object does not exist but an exception was not thrown')

    def object_as_stream(self):
        pass

    def test_upload_object_success(self):
        def upload_file(self, response, file_path, chunked=False,
                     calculate_hash=True):
            return True, 'hash343hhash89h932439jsaa89', 1000

        old_func = CloudFilesStorageDriver._upload_file
        CloudFilesStorageDriver._upload_file = upload_file
        file_path = os.path.abspath(__file__)
        container = Container(name='foo_bar_container', extra={}, driver=self)
        object_name = 'foo_test_upload'
        obj = self.driver.upload_object(file_path=file_path, container=container,
                                        object_name=object_name)
        self.assertEqual(obj.name, 'foo_test_upload')
        self.assertEqual(obj.size, 1000)
        CloudFilesStorageDriver._upload_file = old_func

    def test_upload_object_invalid_hash(self):
        def upload_file(self, response, file_path, chunked=False,
                     calculate_hash=True):
            return True, 'hash343hhash89h932439jsaa89', 1000

        CloudFilesMockRawResponse.type = 'INVALID_HASH'

        old_func = CloudFilesStorageDriver._upload_file
        CloudFilesStorageDriver._upload_file = upload_file
        file_path = os.path.abspath(__file__)
        container = Container(name='foo_bar_container', extra={}, driver=self)
        object_name = 'foo_test_upload'
        try:
            obj = self.driver.upload_object(file_path=file_path, container=container,
                                            object_name=object_name,
                                            file_hash='footest123')
        except ObjectHashMismatchError:
            pass
        else:
            self.fail('Invalid hash was returned but an exception was not thrown')
        finally:
            CloudFilesStorageDriver._upload_file = old_func

    def test_upload_object_no_content_type(self):
        def no_content_type(name):
            return None, None

        old_func = libcloud.utils.guess_file_mime_type
        libcloud.utils.guess_file_mime_type = no_content_type
        file_path = os.path.abspath(__file__)
        container = Container(name='foo_bar_container', extra={}, driver=self)
        object_name = 'foo_test_upload'
        try:
            obj = self.driver.upload_object(file_path=file_path, container=container,
                                            object_name=object_name)
        except AttributeError:
            pass
        else:
            self.fail('File content type not provided but an exception was not thrown')
        finally:
            libcloud.utils.guess_file_mime_type = old_func

    def test_upload_object_error(self):
        def dummy_content_type(name):
            return 'application/zip', None

        def send(instance):
            raise Exception('')

        old_func1 = libcloud.utils.guess_file_mime_type
        libcloud.utils.guess_file_mime_type = dummy_content_type
        old_func2 = CloudFilesMockHttp.send
        CloudFilesMockHttp.send = send

        file_path = os.path.abspath(__file__)
        container = Container(name='foo_bar_container', extra={}, driver=self)
        object_name = 'foo_test_upload'
        try:
            obj = self.driver.upload_object(file_path=file_path, container=container,
                                            object_name=object_name)
        except LibcloudError:
            pass
        else:
            self.fail('Timeout while uploading but an exception was not thrown')
        finally:
            libcloud.utils.guess_file_mime_type = old_func1
            CloudFilesMockHttp.send = old_func2

    def test_upload_object_inexistent_file(self):
        def dummy_content_type(name):
            return 'application/zip', None

        old_func = libcloud.utils.guess_file_mime_type
        libcloud.utils.guess_file_mime_type = dummy_content_type

        file_path = os.path.abspath(__file__ + '.inexistent')
        container = Container(name='foo_bar_container', extra={}, driver=self)
        object_name = 'foo_test_upload'
        try:
            obj = self.driver.upload_object(file_path=file_path, container=container,
                                            object_name=object_name)
        except OSError:
            pass
        else:
            self.fail('Inesitent but an exception was not thrown')
        finally:
            libcloud.utils.guess_file_mime_type = old_func

    def test_upload_object_via_stream(self):
        def dummy_content_type(name):
            return 'application/zip', None

        old_func = libcloud.utils.guess_file_mime_type
        libcloud.utils.guess_file_mime_type = dummy_content_type

        container = Container(name='foo_bar_container', extra={}, driver=self)
        object_name = 'foo_test_stream_data'
        iterator = DummyIterator(data=['2', '3', '5'])
        try:
            obj = self.driver.upload_object_via_stream(container=container,
                                                 object_name=object_name,
                                                 iterator=iterator)
        finally:
            libcloud.utils.guess_file_mime_type = old_func

    def test_delete_object_success(self):
        container = Container(name='foo_bar_container', extra={}, driver=self)
        obj = Object(name='foo_bar_object', size=1000, hash=None, extra={},
                     container=container, meta_data=None,
                     driver=CloudFilesStorageDriver)
        result = self.driver.delete_object(obj=obj)
        self.assertTrue(result)

    def test_delete_object_success(self):
        CloudFilesMockHttp.type = 'NOT_FOUND'
        container = Container(name='foo_bar_container', extra={}, driver=self)
        obj = Object(name='foo_bar_object', size=1000, hash=None, extra={},
                     container=container, meta_data=None,
                     driver=CloudFilesStorageDriver)
        try:
            result = self.driver.delete_object(obj=obj)
        except ObjectDoesNotExistError:
            pass
        else:
            self.fail('Object does not exist but an exception was not thrown')

    def _remove_test_file(self):
        file_path = os.path.abspath(__file__) + '.temp'

        try:
            os.unlink(file_path)
        except OSError:
            pass

class CloudFilesMockHttp(MockHttp):

    fixtures = StorageFileFixtures('cloudfiles')
    base_headers = { 'content-type': 'application/json; charset=UTF-8'}

    def putrequest(self, method, action):
        pass

    def putheader(self, key, value):
        pass

    def endheaders(self):
        pass

    def send(self, data):
      pass

    # fake auth token response
    def _v1_0(self, method, url, body, headers):
        headers = copy.deepcopy(self.base_headers)
        headers.update({ 'x-server-management-url': 'https://servers.api.rackspacecloud.com/v1.0/slug',
                         'x-auth-token': 'FE011C19',
                         'x-cdn-management-url': 'https://cdn.clouddrive.com/v1/MossoCloudFS',
                         'x-storage-token': 'FE011C19',
                         'x-storage-url': 'https://storage4.clouddrive.com/v1/MossoCloudFS'})
        return (httplib.NO_CONTENT, "", headers, httplib.responses[httplib.NO_CONTENT])

    def _v1_MossoCloudFS_EMPTY(self, method, url, body, headers):
        body = self.fixtures.load('list_containers_empty.json')
        return (httplib.OK, body, self.base_headers, httplib.responses[httplib.OK])

    def _v1_MossoCloudFS(self, method, url, body, headers):
        if method == 'GET':
            # list_containers
            body = self.fixtures.load('list_containers.json')
            status_code = httplib.OK
            headers = copy.deepcopy(self.base_headers)
        elif method == 'HEAD':
            # get_meta_data
            body = self.fixtures.load('meta_data.json')
            status_code = httplib.NO_CONTENT
            headers = copy.deepcopy(self.base_headers)
            headers.update({ 'x-account-container-count': 10,
                             'x-account-object-count': 400,
                             'x-account-bytes-used': 1234567
                           })
        return (status_code, body, headers, httplib.responses[httplib.OK])

    def _v1_MossoCloudFS_test_container_EMPTY(self, method, url, body, headers):
        body = self.fixtures.load('list_container_objects_empty.json')
        return (httplib.OK, body, self.base_headers, httplib.responses[httplib.OK])

    def _v1_MossoCloudFS_test_container(self, method, url, body, headers):
        if method == 'GET':
            # list_container_objects
            body = self.fixtures.load('list_container_objects.json')
            status_code = httplib.OK
            headers = copy.deepcopy(self.base_headers)
        elif method == 'HEAD':
            # get_container
            body = self.fixtures.load('list_container_objects_empty.json')
            status_code = httplib.NO_CONTENT
            headers = copy.deepcopy(self.base_headers)
            headers.update({ 'x-container-object-count': 800,
                             'x-container-bytes-used': 1234568
                           })
        return (status_code, body, headers, httplib.responses[httplib.OK])

    def _v1_MossoCloudFS_test_container_test_object(self, method, url, body,
                                                    headers):
        if method == 'HEAD':
            # get_object
            body = self.fixtures.load('list_container_objects_empty.json')
            status_code = httplib.NO_CONTENT
            headers = self.base_headers
            headers.update({ 'content-length': 555,
                             'last-modified': 'Tue, 25 Jan 2011 22:01:49 GMT',
                             'etag': '6b21c4a111ac178feacf9ec9d0c71f17',
                             'x-object-meta-foo-bar': 'test 1',
                             'x-object-meta-bar-foo': 'test 2',
                             'content-type': 'application/zip'})
        return (status_code, body, headers, httplib.responses[httplib.OK])

    def _v1_MossoCloudFS_test_create_container(self, method, url, body, headers):
        # test_create_container_success
        body = self.fixtures.load('list_container_objects_empty.json')
        headers = self.base_headers
        headers.update({ 'content-length': 18,
                         'date': 'Mon, 28 Feb 2011 07:52:57 GMT'
                       })
        status_code = httplib.CREATED
        return (status_code, body, headers, httplib.responses[httplib.OK])

    def _v1_MossoCloudFS_test_create_container_ALREADY_EXISTS(self, method, url, body, headers):
        # test_create_container_already_exists
        body = self.fixtures.load('list_container_objects_empty.json')
        headers = self.base_headers
        headers.update({ 'content-type': 'text/plain' })
        status_code = httplib.ACCEPTED
        return (status_code, body, headers, httplib.responses[httplib.OK])

    def _v1_MossoCloudFS_foo_bar_container(self, method, url, body, headers):
        if method == 'DELETE':
            # test_delete_container_success
            body = self.fixtures.load('list_container_objects_empty.json')
            headers = self.base_headers
            status_code = httplib.NO_CONTENT
        return (status_code, body, headers, httplib.responses[httplib.OK])

    def _v1_MossoCloudFS_foo_bar_container_NOT_FOUND(self, method, url, body, headers):
        if method == 'DELETE':
            # test_delete_container_not_found
            body = self.fixtures.load('list_container_objects_empty.json')
            headers = self.base_headers
            status_code = httplib.NOT_FOUND
        return (status_code, body, headers, httplib.responses[httplib.OK])

    def _v1_MossoCloudFS_foo_bar_container_NOT_EMPTY(self, method, url, body, headers):
        if method == 'DELETE':
            # test_delete_container_not_empty
            body = self.fixtures.load('list_container_objects_empty.json')
            headers = self.base_headers
            status_code = httplib.CONFLICT
        return (status_code, body, headers, httplib.responses[httplib.OK])

    def _v1_MossoCloudFS_foo_bar_container_foo_bar_object(self, method, url, body, headers):
        if method == 'DELETE':
            # test_delete_object_success
            body = self.fixtures.load('list_container_objects_empty.json')
            headers = self.base_headers
            status_code = httplib.NO_CONTENT
        return (status_code, body, headers, httplib.responses[httplib.OK])

    def _v1_MossoCloudFS_foo_bar_container_foo_bar_object_NOT_FOUND(self, method, url, body, headers):
        if method == 'DELETE':
            # test_delete_object_success
            body = self.fixtures.load('list_container_objects_empty.json')
            headers = self.base_headers
            status_code = httplib.NOT_FOUND
        return (status_code, body, headers, httplib.responses[httplib.OK])

class CloudFilesMockRawResponse(MockRawResponse):

    fixtures = StorageFileFixtures('cloudfiles')
    base_headers = { 'content-type': 'application/json; charset=UTF-8'}

    def __init__(self, *args, **kwargs):
      super(CloudFilesMockRawResponse, self).__init__(*args, **kwargs)
      self._data = []
      self._current_item = 0

    def next(self):
        if self._current_item == len(self._data):
          raise StopIteration

        value = self._data[self._current_item]
        self._current_item += 1
        return value

    def _generate_random_data(self, size):
      data = []
      current_size = 0
      while current_size < size:
        value = str(random.randint(0, 9))
        value_size = len(value)
        data.append(value)
        current_size += value_size

      return data

    def  _v1_MossoCloudFS_foo_bar_container_foo_test_upload(self, method, url, body, headers):
        # test_object_upload_success
        body = ''
        header = copy.deepcopy(self.base_headers)
        return (httplib.CREATED, body, headers, httplib.responses[httplib.OK])

    def  _v1_MossoCloudFS_foo_bar_container_foo_test_upload_INVALID_HASH(self, method, url, body, headers):
        # test_object_upload_invalid_hash
        body = ''
        headers = self.base_headers
        return (httplib.UNPROCESSABLE_ENTITY, body, headers,
                httplib.responses[httplib.OK])

    def _v1_MossoCloudFS_foo_bar_container_foo_bar_object(self, method, url, body, headers):
        # test_download_object_success
        body = 'test'
        self._data = self._generate_random_data(1000)
        return (httplib.OK, body, self.base_headers, httplib.responses[httplib.OK])

    def _v1_MossoCloudFS_foo_bar_container_foo_bar_object_INVALID_SIZE(self, method, url, body, headers):
        # test_download_object_invalid_file_size
        body = 'test'
        self._data = self._generate_random_data(100)
        return (httplib.OK, body, self.base_headers, httplib.responses[httplib.OK])

    def _v1_MossoCloudFS_foo_bar_container_foo_test_stream_data(self, method, url, body, headers):
        # test_upload_object_via_stream_success
        body = 'test'
        return (httplib.OK, body, self.base_headers, httplib.responses[httplib.OK])

if __name__ == '__main__':
    sys.exit(unittest.main())

########NEW FILE########
__FILENAME__ = test_file_fixtures
# Licensed to the Apache Software Foundation (ASF) under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import sys
import unittest

from test.file_fixtures import ComputeFileFixtures

class FileFixturesTests(unittest.TestCase):

    def test_success(self):
        f = ComputeFileFixtures('meta')
        self.assertEqual("Hello, World!", f.load('helloworld.txt'))

    def test_failure(self):
        f = ComputeFileFixtures('meta')
        self.assertRaises(IOError, f.load, 'nil')

if __name__ == '__main__':
    sys.exit(unittest.main())

########NEW FILE########
