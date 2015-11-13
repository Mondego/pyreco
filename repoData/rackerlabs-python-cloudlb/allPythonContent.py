__FILENAME__ = accesslist
# -*- encoding: utf-8 -*-
__author__ = "Chmouel Boudjnah <chmouel@chmouel.com>"
from cloudlb.base import SubResource


class NetworkItem(SubResource):
    def __repr__(self):
        return "<NetworkItem: %s:%s>" % (self.address, self.type)

    def __init__(self, parent=None,
                 address=None,
                 type=None,
                 id=None):
        self.address = address
        self.type = type
        self.id = id
        self._parent = parent
        self._originalInfo = self.toDict(includeNone=True)

        if not all([self.address, self.type]):
            #TODO: Proper Exceptions
            raise Exception("You need to specify an" + \
                                " address and a type.")


class AccessList(object):
    def __init__(self, client, lbId=None):
        self.lbId = lbId
        if self.lbId:
            self.lbId = int(self.lbId)
            self.path = "/loadbalancers/%s/accesslist" % self.lbId

        self.client = client

    def get(self, id):
        objects = self.list()
        for obj in objects:
            if obj.id == id:
                return obj
        #TODO: Not found Exceptions or None ?

    def list(self):
        ret = self.client.get("%s.json" % self.path)
        return [NetworkItem(**x) for x in ret[1]['accessList']]

    def add(self, networkitems):
        dico = [x.toDict() for x in networkitems]
        self.client.post(self.path, body=dico)

    def delete(self, id=None):
        extrapath = ""
        if id:
            extrapath = "/%d" % (id)
        self.client.delete("%s%s" % (self.path, extrapath))

########NEW FILE########
__FILENAME__ = base
# -*- encoding: utf-8 -*-
""" Base object class, basically the same class taken
from jacobian python-cloudservers library"""
import datetime

from dateutil import parser


class Resource(object):
    """ A resource represents a particular instance of an object
    (loadbalancers, protocol, etc). This is pretty much just a bag for
    attributes.  """
    def __init__(self, manager, info):
        self.manager = manager
        self._info = info
        self._add_details(info)

    def _add_details(self, info):
        for (k, v) in info.iteritems():
            setattr(self, k, v)

    def __getattr__(self, k):
        self.get()
        if k not in self.__dict__:
            raise AttributeError("Object has no attribute '%s'" % k)
        else:
            return self.__dict__[k]

    def __repr__(self):
        reprkeys = sorted(k for k in self.__dict__.keys() \
                              if k[0] != '_' and k != 'manager')
        info = ", ".join("%s=%s" % (k, getattr(self, k)) for k in reprkeys)
        return "<%s %s>" % (self.__class__.__name__, info)

    def get(self):
        new = self.manager.get(self.id)
        self._add_details(new._info)

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return False
        if hasattr(self, 'id') and hasattr(other, 'id'):
            return self.id == other.id
        return self._info == other._info

    def __setitem__(self, key, value):
        setattr(self, key, value)


class Manager(object):
    """ Managers interact with a particular type of API (loadbalancer,
    protocol, etc.) and provide CRUD operations for them."""
    resource_class = None

    def __init__(self, api):
        self.api = api

    def _list(self, url, response_key):
        resp, body = self.api.client.get(url)
        return [self.resource_class(self, res) for res in body[response_key]]

    def _get(self, url, response_key):
        resp, body = self.api.client.get(url)
        return self.resource_class(self, body[response_key])

    def _create(self, url, body, response_key):
        resp, body = self.api.client.post(url, body=body)
        return self.resource_class(self, body[response_key])

    def _delete(self, url):
        resp, body = self.api.client.delete(url)

    def _update(self, url, body):
        resp, body = self.api.client.put(url, body=body)


class ManagerWithFind(Manager):
    """
    Like a `Manager`, but with additional `find()`/`findall()` methods.
    """
    def find(self, **kwargs):
        """
        Find a single item with attributes matching ``**kwargs``.

        This isn't very efficient: it loads the entire list then filters on
        the Python side.
        """
        rl = self.findall(**kwargs)
        try:
            return rl[0]
        except IndexError:
            #TODO:
            # NotFound(404, "No %s matching %s." %
            # (self.resource_class.__name__, kwargs))
            raise Exception()

    def findall(self, **kwargs):
        """
        Find all items with attributes matching ``**kwargs``.

        This isn't very efficient: it loads the entire list then filters on
        the Python side.
        """
        found = []
        searches = kwargs.items()

        for obj in self.list():
            try:
                if all(getattr(obj, attr) == value \
                           for (attr, value) in searches):
                    found.append(obj)
            except AttributeError:
                continue

        return found


class SubResourceManager(object):
    path = None
    type = None
    resource = None

    def __init__(self, client, lbId=None):
        self.lbId = lbId
        if self.lbId:
            self.lbId = int(self.lbId)
            self.path = "/loadbalancers/%s/%s" % (self.lbId, self.type.lower())

        self.client = client

    def get(self):
        ret = self.client.get("%s.json" % self.path)
        tt = ret[1][self.type]
        if tt:
            return self.resource(**(tt))

    def add(self, ssp):
        dico = ssp.toDict()
        ret = self.client.put(self.path, body={self.type: dico})
        return ret

    def delete(self):
        ret = self.client.delete(self.path)
        return ret


class SubResource(object):
    def toDict(self, includeNone=False):
        """
        Convert the local attributes to a dict
        """
        ret = {}
        for attr in self.__dict__:
            if self.__dict__[attr] is None and not includeNone:
                continue
            if not attr.startswith("_"):
                ret[attr] = self.__dict__[attr]
        return ret

    def __setitem__(self, key, value):
        setattr(self, key, value)


class SubResourceDict(object):
    def __init__(self, dico):
        self.dico = dico

    def __iter__(self):
        for d in self.dico:
            yield d

    def __getitem__(self, i):
        return self.dico[i]

    def __len__(self):
        return len(self.dico)

    #Trying hard to look like a dict.. Not sure if I should do that.
    def __repr__(self):
        ret = '['
        for d in self.dico:
            ret += str(d)
            ret += ", "
        ret = ret[0:-2] + "]"
        return ret


def getid(obj):
    """
    Abstracts the common pattern of allowing both an object or an object's ID
    (integer) as a parameter when dealing with relationships.
    """
    try:
        return obj.id
    except AttributeError:
        return int(obj)


def convert_iso_datetime(dt):
    """
    Convert iso8601 to datetime
    """
    return parser.parse(dt)

########NEW FILE########
__FILENAME__ = client
# -*- encoding: utf-8 -*-
__author__ = "Chmouel Boudjnah <chmouel@chmouel.com>"
import httplib2
import os
import sys
import json
import pprint
import time
import datetime

import cloudlb.base
import cloudlb.consts
import cloudlb.errors

class CLBClient(httplib2.Http):
    """
    Client class for accessing the CLB API.
    """

    def __init__(self,
                 username,
                 api_key,
                 region,
                 auth_url=None):
        super(CLBClient, self).__init__()
        self.username = username
        self.api_key = api_key

        if not auth_url and region == 'lon':
            auth_url = cloudlb.consts.UK_AUTH_SERVER
        else:
            auth_url = cloudlb.consts.DEFAULT_AUTH_SERVER
        self._auth_url = auth_url

        if region.lower() in cloudlb.consts.REGION.values():
            self.region = region
        elif region.lower() in cloudlb.consts.REGION.keys():
            self.region = cloudlb.consts.REGION[region]
        else:
            raise cloudlb.errors.InvalidRegion(region)

        self.auth_token = None
        self.account_number = None
        self.region_account_url = None

    def authenticate(self):
        headers = {'Content-Type': 'application/json'}
        body = '{"credentials": {"username": "%s", "key": "%s"}}' \
               % (self.username, self.api_key)

        #DEBUGGING:
        if 'PYTHON_CLOUDLB_DEBUG' in os.environ:
            pp = pprint.PrettyPrinter(stream=sys.stderr, indent=2)
            sys.stderr.write("URL: %s\n" % (self._auth_url))

        response, body = self.request(self._auth_url, 'POST',
                                      body=body, headers=headers)

        if 'PYTHON_CLOUDLB_DEBUG' in os.environ:
            sys.stderr.write("RETURNED HEADERS: %s\n" % (str(response)))
            sys.stderr.write("BODY:")
            pp.pprint(body)

        data = json.loads(body)

        # A status code of 401 indicates that the supplied credentials
        # were not accepted by the authentication service.
        if response.status == 401:
            reason = data['unauthorized']['message']
            raise cloudlb.errors.AuthenticationFailed(response.status, reason)

        if response.status != 200:
            raise cloudlb.errors.ResponseError(response.status,
                                               response.reason)

        auth_data = data['auth']

        self.account_number = int(
            auth_data['serviceCatalog']['cloudServersOpenStack'][0]['publicURL'].rsplit('/', 1)[-1])
        self.auth_token = auth_data['token']['id']
        self.region_account_url = "%s/%s" % (
            cloudlb.consts.REGION_URL % (self.region),
            self.account_number)

    def _cloudlb_request(self, url, method, **kwargs):
        if not self.region_account_url:
            self.authenticate()

        #TODO: Look over
        # Perform the request once. If we get a 401 back then it
        # might be because the auth token expired, so try to
        # re-authenticate and try again. If it still fails, bail.
        kwargs.setdefault('headers', {})['X-Auth-Token'] = self.auth_token
        kwargs['headers']['User-Agent'] = cloudlb.consts.USER_AGENT
        if 'body' in kwargs:
            kwargs['headers']['Content-Type'] = 'application/json'
            kwargs['body'] = json.dumps(kwargs['body'])

        ext = ""
        fullurl = "%s%s%s" % (self.region_account_url, url, ext)

        #DEBUGGING:
        if 'PYTHON_CLOUDLB_DEBUG' in os.environ:
            pp = pprint.PrettyPrinter(stream=sys.stderr, indent=2)
            sys.stderr.write("URL: %s\n" % (fullurl))
            sys.stderr.write("ARGS: %s\n" % (str(kwargs)))
            sys.stderr.write("METHOD: %s\n" % (str(method)))
            if 'body' in kwargs:
                pp.pprint(json.loads(kwargs['body']))
        response, body = self.request(fullurl, method, **kwargs)

        if 'PYTHON_CLOUDLB_DEBUG' in os.environ:
            sys.stderr.write("RETURNED HEADERS: %s\n" % (str(response)))
        # If we hit a 413 (Request Limit) response code,
        # check to see how long we have to wait.
        # If you have to wait more then 10 seconds,
        # raise ResponseError with a more sane message then CLB provides
        if response.status == 413:
            if 'PYTHON_CLOUDLB_DEBUG' in os.environ:
                sys.stderr.write("(413) BODY:")
                pp.pprint(body)
            now = datetime.datetime.strptime(response['date'],
                    '%a, %d %b %Y %H:%M:%S %Z')

            # Absolute limits are not resolved by waiting
            if not 'retry-after' in response:
                data = json.loads(body)
                raise cloudlb.errors.AbsoluteLimit(data['message'])

            # Retry-After header now doesn't always return a timestamp, 
            # try parsing the timestamp, if that fails wait 5 seconds 
            # and try again.  If it succeeds figure out how long to wait
            try:
                retry = datetime.datetime.strptime(response['retry-after'],
                        '%a, %d %b %Y %H:%M:%S %Z')
            except ValueError:
                if response['retry-after'] > '30':
                    raise cloudlb.errors.RateLimit(response['retry-after'])
                else:
                    time.sleep(5)
                    response, body = self.request(fullurl, method, **kwargs)
            except:
                raise
            else:
                if (retry - now) > datetime.timedelta(seconds=10):
                    raise cloudlb.errors.RateLimit((retry - now))
                else:
                    time.sleep((retry - now).seconds)
                    response, body = self.request(fullurl, method, **kwargs)

        if body:
            try:
                body = json.loads(body, object_hook=lambda obj: dict((k.encode('ascii'), v) for k, v in obj.items()))
            except(ValueError):
                pass

            if 'PYTHON_CLOUDLB_DEBUG' in os.environ:
                sys.stderr.write("BODY:")
                pp.pprint(body)

        if (response.status >= 200) and (response.status < 300):
            return response, body

        if response.status == 404:
            raise cloudlb.errors.NotFound(response.status, '%s not found' % url)
        elif response.status == 413:
            raise cloudlb.errors.RateLimit(retry)

        try:
            message = ', '.join(body['messages'])
        except KeyError:
            message = body['message']

        if response.status == 400:
            raise cloudlb.errors.BadRequest(response.status, message)
        elif response.status == 422:
            if 'unprocessable' in message:
                raise cloudlb.errors.UnprocessableEntity(response.status, 
                        message)
            else:
                raise cloudlb.errors.ImmutableEntity(response.status,
                        message)
        else:
            raise cloudlb.errors.ResponseError(response.status,
                    message)

    def put(self, url, **kwargs):
        return self._cloudlb_request(url, 'PUT', **kwargs)

    def get(self, url, **kwargs):
        return self._cloudlb_request(url, 'GET', **kwargs)

    def post(self, url, **kwargs):
        return self._cloudlb_request(url, 'POST', **kwargs)

    def delete(self, url, **kwargs):
        return self._cloudlb_request(url, 'DELETE', **kwargs)

########NEW FILE########
__FILENAME__ = cli_help
# -*- encoding: utf-8 -*-
__author__ = "Chmouel Boudjnah <chmouel@chmouel.com>"

USAGE = """usage: cloudlb [-u USERNAME] [-k API_KEY]
               [-l DATACENTER_LOCATION] COMMAND ARGS

cloudlb is a tool allowing to interface to Rackspace Cloud
Load-Balancer service.

COMMANDS:

  add
  create
  delete
  list
  set
  show

Add help to command like :

   cloudlb add help

to display help for the add command."""

HELP_SET = """usage: set [connection_logging|session_persistence|healthmonitor|loadbalancer|node]

- Set load balancer attributes :
Usage:
 cloudlb set loadbalancer LOADBALANCER_ID name=NEWNAME port=PORT
         protocol=(HTTP|FTP|HTTPS|POP.....)
         algorithm=(LEAST_CONNECTIONS|RANDOM|ROUND_ROBIN|
                    WEIGHTED_LEAST_CONNECTIONS|WEIGHTED_ROUND_ROBIN)
Example:
 cloudlb set loadbalancer LOADBALANCER_ID name=MyNewName1
         port=2021 protocol=FTP algorithm=ROUND_ROBIN
 cloudlb set loadbalancer LOADBALANCER_ID name=MyNewName1
         port=8043 protocol=HTTPS algorithm=RANDOM

- Set node attribute :
Usage:
 set node LOADBALANCER_ID NODE_ID condition=(ENABLED|DISABLED|DRAINING)
Example:
 cloudlb set node LOADBALANCER_ID NODE_ID condition=ENABLED

- Enable or Disable connection_logging :
Usage:
 set connection_logging LOADBALANCER_ID (ENABLE|DISABLE)
Example:
 cloudlb set connection_logging LOADBALANCER_ID enable

- Set session persistence on load balancer:
Usage:
  set session_persistence LOADBALANCER_ID HTTP_COOKIE
Example:
  cloudlb set session_persistence LOADBALANCER_ID HTTP_COOKIE

- Set health monitoring on load balancer :
Usage:
  set healthmonitor LOADBALANCER_ID type=(CONNECT|HTTP|HTTPS)
                       delay=SECONDS timeout=SECONDS
                       attemptsBeforeDeactivation=NUMBER
                       [ path=HTTP_PATH statusRegex=REGEXP
                         bodyRegex=REGEXP ]
Examples:
  cloudlb set healthmonitor LOADBALANCER_ID type="CONNECT"
          delay="10" timeout="10" attemptsBeforeDeactivation=4

  cloudlb set healthmonitor LOADBALANCER_ID type="HTTP" delay="5" timeout="2"
          attemptsBeforeDeactivation=3 path=/
          statusRegex="^[234][0-9][0-9]$" bodyRegex=testing
"""

HELP_ADD = """usage: add [access_list|node]

- Add network access list :
Usage:
  add access_list (ALLOW|DENY):NETWORK
Example:
  cloudlb add access_list LOADBALANCER_ID ALLOW:127.0.0.1/24

- Add node to a load balancer :
Usage:
 add node LOADBALANCER_ID condition="ENABLED|DISABLED|DRAINING"
          port=PORT address=IPV4_ADDRESS
Example:
  cloudlb add node LOADBALANCER_ID
          condition=ENABLED port=80 address=98.129.220.40
"""

HELP_SHOW = """
usage: show [usage|algorithms|protocols|healthmonitor|
             session_persistence|connection_logging|loadbalancer|
             access_list|node|nodes]

- Show all (or specific) load balancer usage :
Usage:
  show usage [LOADBALANCER_ID]
Example:
  cloudlb show usage

- Show algorithms available :
Usage:
  show algorithms
Example:
  cloudlb show algorithms

- Show protocols available :
Usage:
  show protocols
Example:
  cloudlb show protocols

- Show Health Monitor type on LoadBalancer
Usage:
  show healthmonitor LOADBALANCER_ID
Example:
  cloudlb show healthmonitor LOADBALANCER_ID

- Show Session persistence type on LoadBalancer
Usage:
  show session_persistence LOADBALANCER_ID
Example:
  cloudlb show session_persistence LOADBALANCER_ID

- Show Connection type on LoadBalancer
Usage:
  show connection_logging LOADBALANCER_ID
Example:
  cloudlb show connection_logging LOADBALANCER_ID

- Show details about LoadBalancer
Usage:
  show loadbalancer LOADBALANCER_ID
Example:
  cloudlb show loadbalancer LOADBALANCER_ID

- Show access lists of LoadBalancer
Usage:
  show access_lists LOADBALANCER_ID
Example:
  cloudlb show access_lists LOADBALANCER_ID

- Show details about node.
Usage:
  show node LOADBALANCER_ID NODE_ID
Example:
  cloudlb show node LOADBALANCER_ID NODE_ID

"""

HELP_LIST = """usage: list [loadbalancers|nodes|access_lists]

- List loadbalancers
Usage:
  list loadbalancers [FILTER]
Filters:
  address
  id
  name
  port
  protocol
  status
Example:
  cloudlb list loadbalancers protocol=HTTP status=ENABLED

- List nodes of load balancers
Usage:
  list nodes LOADBALANCER_ID [FILTER]
Filters:
  address
  id
  port
  condition
  status
Example:
  cloudlb list nodes LOADBALANCER_ID port=80

- List access lists of load balancers
Usage:
  list access_lists LOADBALANCER_ID
Example:
  cloudlb list access_lists LOADBALANCER_ID
"""

HELP_DELETE = """usage: delete [loadbalancer|node|access_list|session_persistence|healthmonitor]

- Delete LoadBalancer :
Usage:
  delete loadbalancer LOADBALANCER_ID
Example:
  cloudlb delete loadbalancer LOADBALANCER_ID

- Delete node of LoadBalancer :
Usage:
  delete node LOADBALANCER_ID NODE_ID
Example:
  cloudlb delete node LOADBALANCER_ID NODE_ID

- Delete access_list of loadbalancer
Usage:
  delete access_list LOADBALANCER_ID (ACCESS_LIST_ID|all)
Example:
  cloudlb delete access_list all

- Delete session_persistence of loadbalancer
Usage:
  delete session_persistence LOADBALANCER_ID
Example:
  cloudlb delete session_persistence LOADBALANCER_ID

- Delete healthmonitor of loadbalancer
Usage:
  delete healthmonitor LOADBALANCER_ID
Example:
  cloudlb delete healthmonitor LOADBALANCER_ID


"""

HELP_CREATE = """
- Create LoadBalancer
Usage:
  create loadbalancer protocol=PROTOCOL name=NAME PORT=PORT \
         NODE1::address=IP_ADDRESS,port=PORT,condition=CONDITION \
         NODE2::address=IP_ADDRESS,port=PORT,condition=CONDITION \
         virtualIp1::type=PUBLIC

  Multiple nodes can be specified

Example:
create loadbalancer \
    protocol="HTTP" name=A_NAME port=80 \
    node1::address="100.1.0.1",port=80,condition=ENABLED \
    node2::address="100.1.0.2",port=80,condition=ENABLED \
    virtualIp1::type=PUBLIC

"""

EPILOG = ""

########NEW FILE########
__FILENAME__ = connectionlogging
# -*- encoding: utf-8 -*-
__author__ = "Chmouel Boudjnah <chmouel@chmouel.com>"


class ConnectionLogging(object):
    type = "connectionLogging"
    path = None

    def __init__(self, client, lbId=None):
        self.lbId = lbId
        if self.lbId:
            self.lbId = int(self.lbId)
            self.path = "/loadbalancers/%s/%s" % (self.lbId, self.type.lower())

        self.client = client

    def enable(self):
        dico = {'enabled': True}
        ret = self.client.put(self.path, body={self.type: dico})
        return ret

    def disable(self):
        dico = {'enabled': False}
        ret = self.client.put(self.path, body={self.type: dico})
        return ret

    def get(self):
        ret = self.client.get("%s.json" % self.path)
        return ret[1][self.type]['enabled']

########NEW FILE########
__FILENAME__ = connectionthrottle
# -*- encoding: utf-8 -*-
__author__ = "Chmouel Boudjnah <chmouel@chmouel.com>"
from cloudlb.base import SubResource, SubResourceManager


class ConnectionThrottle(SubResource):
    def __repr__(self):
        return "<ConnectionThrottle>" % (self.type)

    def __init__(self,
                 minConnections=None,
                 maxConnections=None,
                 rateInterval=None,
                 maxConnectionRate=None,
                 ):
        self.minConnections = minConnections
        self.maxConnections = maxConnections
        self.rateInterval = rateInterval
        self.maxConnectionsRate = maxConnectionRate

        if not all([minConnections, maxConnections,
                    rateInterval, maxConnectionRate]):
            #TODO:
            raise Exception("missing some parameters")


class ConnectionThrottleManager(SubResourceManager):
    type = "connectionThrottle"
    resource = ConnectionThrottle

########NEW FILE########
__FILENAME__ = consts
# -*- encoding: utf-8 -*-
__author__ = "Chmouel Boudjnah <chmouel@chmouel.com>"
VERSION = "0.6.0dev"
USER_AGENT = 'python-cloudlb/%s' % VERSION

# Default AUTH SERVER
DEFAULT_AUTH_SERVER = "https://auth.api.rackspacecloud.com/v1.1/auth"

# UK AUTH SERVER
UK_AUTH_SERVER = "https://lon.auth.api.rackspacecloud.com/v1.1/auth"

# Default URL for Regions
REGION_URL = "https://%s.loadbalancers.api.rackspacecloud.com/v1.0"

# Different available Regions
REGION = {
    "chicago": "ord",
    "dallas": "dfw",
    "london": "lon",
    "sydney": "syd",
    "ashburn": "iad",
    "staging": "staging",
}

# Allowed Protocol
LB_PROTOCOLS = ["FTP", "HTTP", "IMAPv4", "POP3", "LDAP",
                "LDAPS", "HTTPS", "IMAPS",
                "POP3S", "SMTP", "TCP"]

# Attributed allowed to be modified on loadbalancers
LB_ATTRIBUTES_MODIFIABLE = ["name", "algorithm", "protocol", 
                            "port", "timeout", "httpsRedirect",
                            "halfClosed"]

# Types of VirtualIPS
VIRTUALIP_TYPES = ["PUBLIC", "SERVICENET"]

# HealthMonitors Types
HEALTH_MONITOR_TYPES = ['CONNECT', 'HTTP', 'HTTPS']

# SessionPersistence Types
SESSION_PERSISTENCE_TYPES = ['HTTP_COOKIE']

########NEW FILE########
__FILENAME__ = errorpage
# -*- encoding: utf-8 -*-
__author__ = "Chmouel Boudjnah <chmouel@chmouel.com>"

class ErrorPage(object):
    def __repr__(self):
        return "<ErrorPage>"

    def __init__(self, client, lbId=None):
        self.lbId = lbId
        if self.lbId:
            self.lbId = int(self.lbId)
            self.path = "/loadbalancers/%s/errorpage" % self.lbId

        self.client = client

    def get(self):
        ret = self.client.get("%s.json" % self.path)
        return ret[1]['errorpage']['content']

    def add(self, html):
        body = {'errorpage': {'content': html}}
        self.client.put(self.path, body=body)

    def delete(self):
        self.client.delete(self.path)

########NEW FILE########
__FILENAME__ = errors
# -*- encoding: utf-8 -*-
__author__ = "Chmouel Boudjnah <chmouel@chmouel.com>"

import cloudlb.consts

class CloudlbException(Exception): pass

class ResponseError(CloudlbException):
    """
    Raised when the remote service returns an error.
    """
    def __init__(self, status, reason):
        self.status = status
        self.reason = reason
        Exception.__init__(self)

    def __str__(self):
        return '%d: %s' % (self.status, self.reason)

    def __repr__(self):
        return '%d: %s' % (self.status, self.reason)

class RateLimit(ResponseError):
    """
    Raised when too many requests have been made 
    of the remote service in a given time period.
    """
    status = 413
    
    def __init__(self, wait):
        self.wait = wait
        self.reason = "Account is currently above limit, please wait %s seconds." % (wait)
        Exception.__init__(self)

class AbsoluteLimit(ResponseError):
    """
    Raised when an absolute limit is reached. Absolute limits include the
    number of load balancers in a region, the number of nodes behind a load
    balancer.
    """
    status = 413
    def __init__(self, reason):
        self.reason = reason
        Exception.__init__(self)

class BadRequest(ResponseError):
    """
    Raised when the request doesn't match what was anticipated.
    """
    pass

# Immutable and Unprocessable Entity are both 422 errors, but have slightly different meanings
class ImmutableEntity(ResponseError):
    pass

class UnprocessableEntity(ResponseError):
    pass

class InvalidRegion(CloudlbException):
    """
    Raised when the region specified is invalid
    """
    regions = cloudlb.consts.REGION.values() + cloudlb.consts.REGION.keys()
    def __init__(self, region):
        self.region = region
        Exception.__init__(self)

    def __str__(self):
        return 'Region %s not in active region list: %s' % (self.region, ', '.join(self.regions))

    def __repr__(self):
        return 'Region %s not in active region list: %s' % (self.region, ', '.join(self.regions))

class InvalidProtocol(CloudlbException):
    """
    Raised when the protocol specified is invalid
    """
    pass


class AuthenticationFailed(ResponseError):
    """
    Raised on a failure to authenticate.
    """
    pass


class NotFound(ResponseError):
    """
    Raised when there the object wasn't found.
    """
    pass

class InvalidLoadBalancerName(CloudlbException):
    def __init__(self, reason):
        self.reason = reason
        Exception.__init__(self)

    def __str__(self):
        return '%s' % (self.reason)

    def __repr__(self):
        return '%s' % (self.reason)

########NEW FILE########
__FILENAME__ = healthmonitor
# -*- encoding: utf-8 -*-
__author__ = "Chmouel Boudjnah <chmouel@chmouel.com>"
from cloudlb.base import SubResource, SubResourceManager
from cloudlb.consts import HEALTH_MONITOR_TYPES


class HealthMonitor(SubResource):
    def __repr__(self):
        return "<HealthMonitor: %s>" % (self.type)

    def __init__(self, type=None,
                 delay=None,
                 timeout=None,
                 attemptsBeforeDeactivation=None,
                 path=None,
                 statusRegex=None,
                 bodyRegex=None):

        self.type = type
        self.delay = delay
        self.timeout = timeout
        self.attemptsBeforeDeactivation = attemptsBeforeDeactivation

        if not all([self.type, self.delay,
                    self.timeout, self.attemptsBeforeDeactivation]):
            #TODO: Proper Exceptions
            raise Exception("You need to specify a timeout type" + \
                            " and an attemptsBeforeDeactivation.")

        if not self.type in HEALTH_MONITOR_TYPES:
            raise Exception("%s is an invalid healthmonitor type" % (
                    self.type))

        if self.type in ("HTTP", "HTTPS"):
            self.path = path
            self.statusRegex = statusRegex
            # We're only going to define self.bodyRegex is we've been passed a value for it. 
            if bodyRegex:
                self.bodyRegex = bodyRegex

            if not all([path, statusRegex]):
                raise Exception("You need to specify a path and statusRegex with HTTP(S) monitor")


class HealthMonitorManager(SubResourceManager):
    path = None
    type = "healthMonitor"
    resource = HealthMonitor

########NEW FILE########
__FILENAME__ = loadbalancers
# -*- encoding: utf-8 -*-
__author__ = "Chmouel Boudjnah <chmouel@chmouel.com>, Randall Burt <randall.burt@rackspace.com>"
from cloudlb import base
from cloudlb.consts import LB_PROTOCOLS, LB_ATTRIBUTES_MODIFIABLE
from cloudlb.errors import InvalidProtocol, InvalidLoadBalancerName
from cloudlb.node import Node, NodeDict
from cloudlb.virtualip import VirtualIP
from cloudlb.usage import get_usage
from cloudlb.stats import Stats
from cloudlb.accesslist import AccessList
from cloudlb.healthmonitor import HealthMonitorManager
from cloudlb.sessionpersistence import SessionPersistenceManager
from cloudlb.connectionlogging import ConnectionLogging
from cloudlb.connectionthrottle import ConnectionThrottleManager
from cloudlb.errorpage import ErrorPage
from cloudlb.ssltermination import SSLTermination


class LoadBalancer(base.Resource):
    accessList = None
    sessionPersistence = None
    healthMonitor = None

    def __repr__(self):
        return "<LoadBalancer: %s>" % self.name

    def delete(self):
        """
        Delete Load Balancer..
        """
        self.manager.delete(self)

    def _add_details(self, info):
        for (k, v) in info.iteritems():
            if k == "nodes":
                v = NodeDict([Node(parent=self, **x) for x in v])

            if k == "sessionPersistence":
                v = v['persistenceType']

            if k == "cluster":
                v = v['name']

            if k == "virtualIps":
                v = [VirtualIP(parent=self, **x) for x in v]

            if k in ('created', 'updated'):
                v = base.convert_iso_datetime(v['time'])

            setattr(self, k, v)

    def add_nodes(self, nodes):
        resp, body = self.manager.add_nodes(self.id, nodes)
        n = [Node(parent=self, **x) for x in body['nodes']]
        self.nodes.add(n)
        return n

    def update(self):
        self.manager.update(self, self._info, self.__dict__)

    def get_usage(self, startTime=None, endTime=None):
        startTime = startTime and startTime.isoformat()
        endTime = endTime and endTime.isoformat()
        ret = get_usage(self.manager.api.client, lbId=base.getid(self),
                        startTime=startTime, endTime=endTime)
        return ret

    def get_stats(self):
        stats = Stats(self.manager.api.client, base.getid(self))
        return stats.get() 

    def accesslist(self):
        accesslist = AccessList(self.manager.api.client, base.getid(self))
        return accesslist

    def healthmonitor(self):
        hm = HealthMonitorManager(self.manager.api.client, base.getid(self))
        return hm

    def session_persistence(self):
        sm = SessionPersistenceManager(
            self.manager.api.client, base.getid(self))
        return sm

    def errorpage(self):
        errorpage = ErrorPage(self.manager.api.client, base.getid(self))
        return errorpage

    def connection_logging(self):
        cm = ConnectionLogging(
            self.manager.api.client, base.getid(self))
        return cm

    #TODO: Not working!
    def connection_throttling(self):
        ctm = ConnectionThrottleManager(
            self.manager.api.client, base.getid(self),
        )
        return ctm

    def ssl_termination(self):
        sslt = SSLTermination(self.manager.api.client, base.getid(self))
        return sslt


class LoadBalancerManager(base.ManagerWithFind):
    resource_class = LoadBalancer

    def get(self, loadbalancerid):
        """
        Get a Load Balancer.

        :param loadbalancerid: ID of the :class:`LoadBalancer` to get.
        :rtype: :class:`LoadBalancer`
        """
        return self._get("/loadbalancers/%s.json" % \
                      base.getid(loadbalancerid), "loadBalancer")

    def list(self):
        """
        Get a list of loadbalancers.
        :rtype: list of :class:`LoadBalancer`

        Arguments:
        """
        return [x for x in \
                    self._list("/loadbalancers.json", "loadBalancers") \
                 if x._info['status'] != "DELETED"]

    def search(self, ip):
        """
        Get a list of loadbalancers who are balancing traffic to `ip`.
        The loadbalancer details are not as complete as the list() call,
        only name, status and id are returned.
        """
        return [x for x in \
                    self._list("/loadbalancers.json?nodeaddress=%s" % ip, 
                        "loadBalancers")]

    def create(self, name, port,
               protocol, nodes, virtualIps, algorithm='RANDOM', timeout=30, **kwargs):
        """
        Create a new loadbalancer.

        :param name: Name of the LB to create
        :param port: Port number for the service you are load balancing
        :param protocol: Protocol of the service which is being load balanced
        :param nodes: List of nodes to be added to the LB
        :param virtualIps: Type of vIP to add with creation of LB
        :param algorithm: Algorithm that defines how traffic should be directed
        :param timeout: Timeout (seconds) for unresponsive backend nodes
        :param kwargs: Name-based arguments for optional LB parameters (such as metadata)
        :rtype: :class:'LoadBalancer'
        """
        if not protocol in LB_PROTOCOLS:
            raise InvalidProtocol("''%s'' is not a valid protocol" % \
                                      (protocol))

        nodeDico = [x.toDict() for x in nodes]
        vipDico = [x.toDict() for x in virtualIps]

        if len(name) > 128:
            raise InvalidLoadBalancerName("LB name is too long.")
        body = {"loadBalancer": {
            "name": name,
            "port": base.getid(port),
            "protocol": protocol,
            "nodes": nodeDico,
            "virtualIps": vipDico,
            "algorithm": algorithm,
            "timeout": timeout
        }}

        if kwargs:
            for key in kwargs:
                body["loadBalancer"][key] = kwargs[key]

        return self._create("/loadbalancers", body, "loadBalancer")

    def delete(self, loadbalancerid):
        """
        Delete load balancer.

        :param loadbalancerid: ID of the :class:`LoadBalancer` to get.
        :rtype: :class:`LoadBalancer`
        """
        self._delete("/loadbalancers/%s" % base.getid(loadbalancerid))

    def add_nodes(self, loadBalancerId, nodes):
        nodeDico = [x.toDict() for x in nodes]
        resp, body = self.api.client.post('/loadbalancers/%d/nodes' % (
                            base.getid(loadBalancerId)
                            ), body={"nodes": nodeDico})
        return (resp, body)

    def delete_node(self, loadBalancerId, nodeId):
        self.api.client.delete('/loadbalancers/%d/nodes/%d' % (
                base.getid(loadBalancerId),
                base.getid(nodeId),
                ))

    def update_node(self, loadBalancerId, nodeId, dico):
        self.api.client.put('/loadbalancers/%d/nodes/%d' % (
                base.getid(loadBalancerId),
                base.getid(nodeId),
                ), body={"node": dico})

    def update(self, lb, originalInfo, info):
        ret = {}
        for k in LB_ATTRIBUTES_MODIFIABLE:
            if k in info and info[k] != originalInfo.get(k):
                ret[k] = info[k]

        if 'protocol' in ret.keys() and ret['protocol'] not in LB_PROTOCOLS:
            raise InvalidProtocol("''%s'' is not a valid protocol" % \
                                      (ret['protocol']))

        if not ret:
            #TODO: proper Exceptions:
            raise Exception("Nothing to update.")

        self.api.client.put('/loadbalancers/%s' % base.getid(lb), body=ret)

    def get_absolute_limits(self):
        _, body = self.api.client.get("/loadbalancers/absolutelimits")
        return {name: val for name, val in [(item.get('name'),
                                             item.get('value'))
                                            for item in
                                            body.get('absolute')]}

########NEW FILE########
__FILENAME__ = node
# -*- encoding: utf-8 -*-
__author__ = "Chmouel Boudjnah <chmouel@chmouel.com>"
from cloudlb.base import SubResource, SubResourceDict


class NodeDict(SubResourceDict):
    def get(self, nodeId):
        for d in self.dico:
            if d.id == nodeId:
                return d

    def filter(self,
               id=None,
               condition=None,
               address=None,
               port=None,
               status=None):
        ret = []
        for d in self.dico:
            if condition and d.condition.lower() == condition.lower():
                ret.append(d)
            if address and d.address.lower() == address.lower():
                ret.append(d)
            if id and int(id) == int(id):
                ret.append(d)
            if port and int(d.port) == int(port):
                ret.append(d)
            if status and d.status.lower() == status.lower():
                ret.append(d)
        return ret

    def add(self, nodes):
        """Add a list of Nodes to the NodeDict.
        
        This DOES NOT actually add nodes to the LB, 
        it should be called from the LB's add_nodes method"""
        for node in nodes:
            self.dico.append(node)

    def delete(self, nid):
        """Delete a Node from the NodeDict.
        
        This DOES NOT actually remove nodes from the LB, 
        it should be called from the node.delete() method"""
        for x in range(len(self.dico) - 1, -1, -1):
            if self.dico[x].id == nid:
                del self.dico[x]



class Node(SubResource):
    def __repr__(self):
        return "<Node: %s:%s:%s>" % (self.id, self.address, self.port)

    def __init__(self,
                 weight=None,
                 parent=None,
                 address=None,
                 port=None,
                 condition=None,
                 status=None,
                 id=None,
                 **kwargs):
        self.port = port
        self.weight = weight
        self.address = address
        self.condition = condition
        self.status = status
        self.id = id
        self._parent = parent
        self._originalInfo = self.toDict(includeNone=True)

        if not all([self.port, self.address, self.condition]):
            #TODO: Proper Exceptions
            raise Exception("You need to specify a" + \
                                " port address and a condition")

    def delete(self):
        self._parent.manager.delete_node(self._parent.id,
                                         self.id,
                                         )
        self._parent.nodes.delete(self.id)

    def update(self):
        ret = {}
        dico = self.toDict()
        #Not allowed to update.
        dico.pop('address')
        dico.pop('port')
        for k in dico.keys():
            if k in self._originalInfo and dico[k] != self._originalInfo[k]:
                ret[k] = dico[k]
        if not ret:
            #TODO: Proper exceptions
            raise Exception("Nothing to update nothing has changed.")

        self._parent.manager.update_node(self._parent.id,
                                         self.id, ret)

########NEW FILE########
__FILENAME__ = sessionpersistence
# -*- encoding: utf-8 -*-
__author__ = "Chmouel Boudjnah <chmouel@chmouel.com>"
from cloudlb.base import SubResource, SubResourceManager
from cloudlb.consts import SESSION_PERSISTENCE_TYPES


class SessionPersistence(SubResource):
    def __repr__(self):
        return "<SessionPersistence: %s>" % (self.persistenceType)

    def __init__(self, persistenceType=None):
        self.persistenceType = persistenceType

        if not self.persistenceType:
            raise Exception("You need to specify a persistenceType.")

        if not self.persistenceType in SESSION_PERSISTENCE_TYPES:
            raise Exception("%s is an invalid session persistence type" % (
                    self.type))


class SessionPersistenceManager(SubResourceManager):
    path = None
    type = "sessionPersistence"
    resource = SessionPersistence

########NEW FILE########
__FILENAME__ = ssltermination
# -*- encoding: utf-8 -*-
__author__ = "Jason Straw <jason.straw@rackspace.com>"

import cloudlb.errors

class SSLTermination(object):
    kwargs = {'port': 'securePort',
                   'enabled': 'enabled',
                   'secureonly': 'secureTrafficOnly',
                   'certificate': 'certificate',
                   'intermediate': 'intermediateCertificate',
                   'privatekey': 'privatekey'
                  }
        
    def __repr__(self):
        try:
            return "<SSLTermination: port %s>" % self.port
        except AttributeError:
            return "<SSLTermination: unconfigured>"

    def __init__(self, client, lbId=None):
        self.lbId = lbId
        if self.lbId:
            self.lbId = int(self.lbId)
            self.path = "/loadbalancers/%s/ssltermination" % self.lbId

        self.client = client
        self.get()

    def get(self):
        """Get dictionary of current LB settings.

    Returns None if SSL Termination is not configured.
    """
        try:
            ret = self.client.get("%s.json" % self.path)
        except cloudlb.errors.NotFound:
            return None
        sslt = ret[1]['sslTermination']
        for (skey, value) in sslt.iteritems():
            key = [k for (k, v) in self.kwargs.iteritems() if v == skey]
            try:
                setattr(self, key[0], value)
            except IndexError:
                print skey, repr(key)
                raise
        if 'intermediateCertificate' in sslt.keys():
            self.intermediate = sslt['intermediateCertificate']
        else:
            self.intermediate = None
        return self
        
    def update(self, **kwargs):
        """Update SSL Termination settings:
        
    Takes keyword args of items to update.  
    
    If you're updating the cert/key/intermediate certificate, 
    you must provide all 3 keywords.
    """
        body = {}
        for (key, value) in kwargs.iteritems():
            body[self.kwargs[key]] = value
            setattr(self, key, value)
        self._put(body)


    def add(self, port, privatekey, certificate, intermediate=None, enabled=True, secureonly=False):
        self.port = port
        self.enabled = enabled
        self.secureonly = secureonly
        self.privatekey = privatekey
        self.certificate = certificate
        self.intermediate = intermediate
        body = {'securePort': self.port, 'enabled': self.enabled, 'secureTrafficOnly': self.secureonly}
        body['privatekey'] = self.privatekey
        body['certificate'] = self.certificate
        if self.intermediate != None:
           body['intermediateCertificate'] = self.intermediate
        self._put(body)

    def _put(self, body):
        self.client.put(self.path, body=body)

    def delete(self):
        self.client.delete(self.path)

########NEW FILE########
__FILENAME__ = stats
# -*- encoding: utf-8 -*-
__author__ = "Chmouel Boudjnah <chmouel@chmouel.com>"

class Stats(object):
    def __init__(self, client, lbId=None):
        self.lbId = lbId
        if self.lbId:
            self.lbId = int(self.lbId)
            self.path = "/loadbalancers/%s/stats" % self.lbId

        self.client = client

    def get(self):
        ret = self.client.get("%s.json" % self.path)
        #return ret[1]['errorpage']['content']
        return ret[1]


########NEW FILE########
__FILENAME__ = usage
# -*- encoding: utf-8 -*-
__author__ = "Chmouel Boudjnah <chmouel@chmouel.com>"
import urllib
from cloudlb import base


def get_usage(client, lbId=None, startTime=None, endTime=None):
    dico = {}
    if startTime:
        dico['startTime'] = startTime.isoformat()
    if endTime:
        dico['endTime'] = endTime.isoformat()

    query_string = ""
    if dico:
        query_string = "?" + urllib.urlencode(dico)

    query_lb = ""
    if lbId:
        query_lb = "/%s" % (lbId)

    ret = client.get('/loadbalancers%s/usage%s' % \
                                         (query_lb, query_string))

    ret = ret[1]

    #TODO: Convert all startTime and endTime field to datetime
    if not lbId:
        return ret

    ret = ret['loadBalancerUsageRecords']
    alist = []
    for row in ret:
        row['startTime'] = base.convert_iso_datetime(row['startTime'])
        row['endTime'] = base.convert_iso_datetime(row['endTime'])
        alist.append(row)

    return alist

########NEW FILE########
__FILENAME__ = virtualip
# -*- encoding: utf-8 -*-
__author__ = "Chmouel Boudjnah <chmouel@chmouel.com>"
import cloudlb.base
from cloudlb.consts import VIRTUALIP_TYPES


class VirtualIP(cloudlb.base.SubResource):
    def __repr__(self):
        return "<VirtualIP: %s:%s>" % (self.address, self.type)

    def __init__(self, address=None,
                 ipVersion=None,
                 type=None,
                 id=None,
                 parent=None,
                 **kwargs):
        self.address = address
        self.ipVersion = ipVersion
        self.type = type
        self.id = id
        if self.id:
            self.id = int(id)
        self._parent = parent

        if self.type and not self.type in VIRTUALIP_TYPES:
            #TODO: Proper check on conditon as well
            raise Exception("You have specified a invalid type: %s" % \
                                (self.type))

        if not any([self.type, self.id]):
            #TODO: Proper check on conditon as well
            raise Exception("You need to specify a" + \
                                " type or an id (for shared ip)")

########NEW FILE########
__FILENAME__ = test_client
# -*- encoding: utf-8 -*-
__author__ = "Chmouel Boudjnah <chmouel@chmouel.com>"

import unittest
import os
import cloudlb.client
import cloudlb.errors


class TestClient(unittest.TestCase):
    def setUp(self):
        self.username = os.environ.get("RCLOUD_USER", None)
        self.api_key = os.environ.get("RCLOUD_KEY", None)
        self.region = "ord"

        if not all([self.username, self.api_key]):
            print """
You have not defined your environement variable properly for the unit tests.
Please adjust your RCLOUD_USER, RCLOUD_KEY variables to be able
to launch the tests.
"""
            self.assertTrue(False)

    def test_constructor(self):
        """
        Test passing argument to constructor.
        """

        region = "ord"
        client = cloudlb.client.CLBClient(self.username,
                                      self.api_key,
                                      region)
        self.assertTrue(client.region == "ord")

        region = "chicago"
        client = cloudlb.client.CLBClient(self.username,
                                      self.api_key,
                                      region)
        self.assertTrue(client.region == "ord")

        callit = lambda: cloudlb.client.CLBClient(self.username,
                                              self.api_key,
                                              "nowhere")
        self.assertRaises(cloudlb.errors.InvalidRegion,
                          callit)

    def test_auth(self):
        client = cloudlb.client.CLBClient(self.username,
                                      self.api_key,
                                      self.region)
        client.authenticate()
        self.assert_(client.auth_token)
        self.assert_(type(client.account_number) is int)

        client = cloudlb.client.CLBClient("memyself",
                                      "andI....",
                                      self.region)
        self.assertRaises(cloudlb.errors.AuthenticationFailed,
                          client.authenticate)

        client = cloudlb.client.CLBClient("memyself",
                                      "andI....",
                                      self.region,
                                      auth_url="http://www.google.com")
        self.assertRaises(cloudlb.errors.ResponseError,
                          client.authenticate)

    def test_get(self):
        client = cloudlb.client.CLBClient(self.username,
                                      self.api_key,
                                      self.region)
        r, b = client.get("/loadbalancers")
        self.assertEqual(r.status, 200)

        callme = lambda: client.get("/loadbalancersf")
        self.assertRaises(cloudlb.errors.NotFound, callme)

########NEW FILE########
