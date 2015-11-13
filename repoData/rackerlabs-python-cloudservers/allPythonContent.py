__FILENAME__ = authentication
# Copyright (c) 2010, Rackspace.
# See COPYING for details.

"""
Authentication Classes

Authentication instances are used to interact with the remote authentication 
service, retreiving storage system routing information and session tokens.
"""

import urllib
from httplib import HTTPSConnection, HTTPConnection, HTTPException
from com.rackspace.cloud.servers.api.client.shared.utils import parse_url
import com.rackspace.cloud.servers.api.client.errors as ClientErrors
from com.rackspace.cloud.servers.api.client.consts import user_agent, default_authurl


class BaseAuthentication(object):
    """
    The base authentication class from which all others inherit.
    """
    def __init__(self, username, api_key, authurl=default_authurl):
        self.authurl = authurl
        self.headers = {
                'x-auth-user': username,
                'x-auth-key': api_key,
                'User-Agent': user_agent}
        self.host, self.port, self.uri, self.is_ssl = parse_url(self.authurl)
        self.conn_class = (self.is_ssl and HTTPSConnection) or HTTPConnection

    def authenticate(self):
        """
        Initiates authentication with the remote service and returns a
        two-tuple containing the storage system URL and session token.

        This is a dummy method from the base class. It must be overridden by
        sub-classes and will raise MustBeOverriddenByChildClass if called.
        """
        raise ClientErrors.MustBeOverriddenByChildClass

class Authentication(BaseAuthentication):
    """
    Authentication, routing, and session token management.
    """
    def authenticate(self):
        """
        Initiates authentication with the remote service and returns a
        two-tuple containing the storage system URL and session token.
        """
        def retry_request():
            '''Re-connect and re-try a failed request once'''
            self.http_connect()
            self.connection.request(method, path, data, headers)
            return self.connection.getresponse()

        try:
            conn = self.conn_class(self.host, self.port)
        except HTTPException:   # httplib threw this
            # Try again, throw one of our exceptions if we can't get it
            try:
                conn = self.conn_class(self.host, self.port)
            except HTTPException,e:
                raise ClientErrors.HTTPLibFault(e)

        conn.request('GET', self.authurl, '', self.headers)
        response = conn.getresponse()
        buff = response.read()

        # A status code of 401 indicates that the supplied credentials
        # were not accepted by the authentication service.
        if response.status == 401:
            raise ClientErrors.AuthenticationFailed()
        elif response.status != 204:
            raise ClientErrors.ResponseError(response.status, response.reason)

        # these must be provided or we have an error
        compute_url = auth_token = None

        hdrs = response.getheaders()

        for hdr in hdrs:
            hdr_key_lc = hdr[0].lower()
            hdr_value = hdr[1]
            if hdr_key_lc == "x-auth-token":
                auth_token = hdr_value
            elif hdr_key_lc == "x-server-management-url":
                compute_url = hdr_value

        conn.close()

        if not (auth_token and compute_url):
            raise ClientErrors.AuthenticationError("Invalid response from the authentication service.")

        return (compute_url, auth_token)

# vim:set ai ts=4 sw=4 tw=0 expandtab:

########NEW FILE########
__FILENAME__ = backupschedule
# Copyright (c) 2010, Rackspace.
# See COPYING for details.

"""
BackupSchedule object
"""
from com.rackspace.cloud.servers.api.client.jsonwrapper import json

"""
Weekly Backup Schedule / Daily Backup Schedule dictionaries.

These are just used to keep requests to set the schedule honest i.e. if the
key's not found in wbs/dbs, it's not a valid value and needs to raise an
exception rather than pass bad data to the server.
"""

# Weekly Backup Schedule.
wbs = {
        "DISABLED": "Weekly backup disabled",
        "SUNDAY": "Sunday",
        "MONDAY": "Monday",
        "TUESDAY": "Tuesday",
        "WEDNESDAY": "Wednesday",
        "THURSDAY": "Thursday",
        "FRIDAY": "Friday",
        "SATURDAY": "Saturday" }


# Daily Backup Schedule
dbs = {
        "DISABLED": "Daily backups disabled",
        "H_0000_0200": "0000-0200",
        "H_0200_0400": "0200-0400",
        "H_0400_0600": "0400-0600",
        "H_0600_0800": "0600-0800",
        "H_0800_1000": "0800-1000",
        "H_1000_1200": "1000-1200",
        "H_1200_1400": "1200-1400",
        "H_1400_1600": "1400-1600",
        "H_1600_1800": "1600-1800",
        "H_1800_2000": "1800-2000",
        "H_2000_2200": "2000-2200",
        "H_2200_0000": "2200-0000" }

class BackupSchedule(object):
    """
    Backup schedule objects.
    """
    def __init__(self, enabled=False, daily="", weekly=""):
        """
        Create new BackupSchedule instance with specified enabled, weekly,
        and daily settings.
        """
        self._enabled = enabled
        self._daily = daily
        self._weekly = weekly

    def __str__(self):
        return "Enabled = %s : Daily = %s : Weekly = %s" % (self._enabled,
                self._daily, self._weekly)

    def get_enabled(self):
        """Whether or not backups are enabled for this server."""
        return self._enabled

    def set_enabled(self, value):
        # TBD: is this supposed to follow weekly & daily != "DISABLED" ?
        self._enabled = value
    enabled = property(get_enabled, set_enabled)

    def get_weekly(self):
        return self._weekly

    def set_weekly(self, value):
        if value in wbs:
            self._weekly = value
        else:
            raise InvalidArgumentsFault("Bad value %s passed for weekly backup", value)
    weekly = property(get_weekly, set_weekly)

    def get_daily(self):
        return self._daily

    def set_daily(self, value):
        if value in dbs:
            self._daily = value
        else:
            raise InvalidArgumentsFault("Bad value %s passed for daily backup", value)
    daily = property(get_daily, set_daily)

    @property
    def asDict(self):
        """
        Return backup schedule object with attributes as a dictionary
        """
        bsAsDict = { "backupSchedule": {
                    "enabled"   : self._enabled,
                    "weekly"    : self.weekly,
                    "daily"     : self.daily }
                    }
        return bsAsDict

    @property
    def asJSON(self):
        """
        Return the backup schedule object converted to JSON
        """
        return json.dumps(self.asDict)

    def initFromResultDict(self, dic):
        """
        Fills up a BackupSchedule object from the dictionary returned from a
        get backup schedule query of the API
        """
        # dic will be None when e.g. a find() fails.
        if dic:
            self._daily = dic['daily']
            self._weekly = dic['weekly']
            self._enabled = dic['enabled']


########NEW FILE########
__FILENAME__ = cloudserversservice
# Copyright (c) 2010, Rackspace.
# See COPYING for details.

"""
Cloud Servers Service class.

Container for the various Entity Managers that manage Rackspace Cloud Servers
entities such as Servers, Images, Shared IP Groups, and Flavors.
"""

from com.rackspace.cloud.servers.api.client.errors import NotImplementedException
from com.rackspace.cloud.servers.api.client.authentication import Authentication
from com.rackspace.cloud.servers.api.client.connection import Connection

from com.rackspace.cloud.servers.api.client.flavormanager import FlavorManager
from com.rackspace.cloud.servers.api.client.servermanager import ServerManager
from com.rackspace.cloud.servers.api.client.imagemanager import ImageManager
from com.rackspace.cloud.servers.api.client.sharedipgroupmanager import SharedIpGroupManager

from com.rackspace.cloud.servers.api.client.consts import json_hdrs
from com.rackspace.cloud.servers.api.client.jsonwrapper import json


class Settings(dict):
    """
    A thin wrapper over dict to conform to Java convention ivar access method
    names.
    """
    def __init__(self):
        self.setSetting = self.__setitem__
        self.getSetting = self.__getitem__


class ServiceInfo(object):
    """
    Provides service information about a CloudServersService object.
    """
    def __init__(self, owner):
        """
        ServiceInfo is a volatile object that can return current values
        for various information about the CloudServersService
        """
        # we are tied to one CloudServersService
        self._owner = owner

        self._versionInfo = None        # From Cloud Servers API, cached
        self._limits = None             # TBD: From CS API, volatile
        self._settings = None           # TBD: From CS API, volatile

    @property
    def limits(self):
        return self._owner.serviceInfoLimits

    @property
    def versionInfo(self):
        return self._owner.serviceInfoVersionInfo

    @property
    def settings(self):
        return self._owner.serviceInfoSettings


class CloudServersService(object):
    """
    Provides the main interface to, and serves as a container for all of the
    separate Entity Managers required to interface with Cloud Servers.
    """

    def __init__(self, userName, apiKey):
        """
        __init__ just makes sure the class's serviceInfo is initialized, once.
        """
        self._serviceInfo = ServiceInfo(self)

        # Get the computeURL and authToken to use for subsequent queries
        auth = Authentication(userName, apiKey)
        computeURL, authToken = auth.authenticate()

        self._auth = auth
        self._computeURL = computeURL
        self._authToken = authToken

        # defer all of these to be created as needed.
        self._conn =  None
        self._serverManager = self._imageManager = None
        self._sharedIpGroupManager = self._flavorManager = None


    def info(self, includePrivate=False):
        """
        TBD: better description
        Return all of the status information for the cloud servers service
        """
        raise NotImplementedException

    def versionInfo(self):
        """
        TBD: better description
        Return the version information.
        """
        raise NotImplementedException

    def createServerManager(self):
        if not self._serverManager:
            self._serverManager = ServerManager(self)
        return self._serverManager

    def createImageManager(self):
        if not self._imageManager:
            self._imageManager = ImageManager(self)
        return self._imageManager

    def createSharedIpGroupManager(self):
        if not self._sharedIpGroupManager:
            self._sharedIpGroupManager = SharedIpGroupManager(self)
        return self._sharedIpGroupManager

    def createFlavorManager(self):
        if not self._flavorManager:
            self._flavorManager = FlavorManager(self)
        return self._flavorManager

    def make_request(self, method, url, data='', headers=None, params=None,
             retHeaders=None):
        print "service make_request: ", url
        print "service params: ", params
        conn = self.get_connection()
        return conn.make_request(method, (url,), data=data, hdrs=headers,
                 params=params, retHeaders=retHeaders)

    def get_connection(self):
        """
        Handles getting a connection, redoing authorization if it's
        expired
        """
        if not self._conn:
            self._conn = Connection(auth=self._auth)
        return self._conn


    def GET(self, url, params=None, headers=None, retHeaders=None):
        """
        Feed a GET request through to our connection
        """
        # NOTE: ret is NOT an http response object, it's a digested
        #       object from reading the response object
        #       see Connection for implementation
        print "service GET: ", url, params
        ret = self.make_request("GET", url, params=params, headers=headers,
                retHeaders=retHeaders)
        return ret


    def POST(self, url, data):
        """
        Feed a POST request through to our connection.
        """
        ret = self.make_request("POST", url, data=data)
        return ret


    def DELETE(self, url):
        """
        Feed a DELETE request through to our connection.
        """
        ret = self.make_request("DELETE", url)
        return ret


    def PUT(self, url):
        """
        Feed a PUT request through to our connection.
        """
        ret = self.make_request("PUT", url)
        return ret

    #
    # serviceInfo attribute and ServiceInfo class support
    #
    @property
    def serviceInfo(self):
        return self._serviceInfo

    @property
    def serviceInfoLimits(self):
        limits_dict = self.GET("limits")
        return limits_dict["limits"]

    @property
    def serviceInfoVersionInfo(self):
        raise NotImplementedException

    @property
    def serviceInfoSettings(self):
        raise NotImplementedException

########NEW FILE########
__FILENAME__ = connection
# Copyright (c) 2010, Rackspace.
# See COPYING for details.

"""
Connection class.
"""

import socket
from urllib import quote
from httplib import HTTPSConnection, HTTPConnection, HTTPException
from time import sleep
from datetime import datetime

from com.rackspace.cloud.servers.api.client.shared.utils import parse_url
from com.rackspace.cloud.servers.api.client.authentication import Authentication
from com.rackspace.cloud.servers.api.client.consts import default_authurl, user_agent, json_hdrs
from com.rackspace.cloud.servers.api.client.jsonwrapper import json

import com.rackspace.cloud.servers.api.client.errors as ClientErrors

class Connection(object):
    """
    Manages the connection to the cloud server system.  Support class, not
    to be used directly.

    @undocumented: http_connect
    @undocumented: make_request
    """
    def __init__(self, username=None, api_key=None, **kwargs):
        """
        Accepts keyword arguments for Rackspace  username and api key.
        Optionally, you can omit these keywords and supply an
        Authentication object using the auth keyword.
        """
        self.connection_args = None
        self.connection = None
        self.token = None

        # handle optional kwargs
        self.debuglevel = int(kwargs.get('debuglevel', 0))
        self.auth = kwargs.get('auth', None)
        socket.setdefaulttimeout = int(kwargs.get('timeout', 5))

        if not self.auth:
            # If we didn't get an auth object, do authentication
            authurl = kwargs.get('authurl', default_authurl)
            if username and api_key and authurl:
                self.auth = Authentication(username, api_key, authurl)
            else:
                # Raise an InvalidArgumentsFault
                err_msg = "Connection "
                if not username:
                    err_msg += "- missing username"
                if not api_key:
                    err_msg += "- missing api_key"
                if not authurl:
                    err_msg += "- missing authurl"
                raise ClientErrors.InvalidArgumentsFault(err_msg)
        self._authenticate()


    def _authenticate(self):
        """
        Authenticate and setup this instance with the values returned.
        """
        (self.url, self.token) = self.auth.authenticate()
        self.connection_args = parse_url(self.url)
        self.conn_class = (self.connection_args[3] and HTTPSConnection) or HTTPConnection
        self.http_connect()


    def http_connect(self):
        """
        Setup the http connection instance.
        """
        host, port, self.uri, is_ssl = self.connection_args
        self.connection = self.conn_class(host, port=port)
        self.connection.set_debuglevel(self.debuglevel)


    def make_request(self, method, path=[], data='', hdrs=None, params=None,
                     retHeaders=None):
        """
        Given a method (i.e. GET, PUT, POST, DELETE etc), a path, data, header
        and metadata dicts, and an optional dictionary of query parameters,
        performs an http request.
        """
        path = '/%s/%s' % (self.uri.rstrip('/'), '/'.join([quote(i) for i in path]))
        print "connection path: ", path

        if isinstance(params, dict) and params:
            query_args = ['%s=%s' \
                    % (quote(x),quote(str(y))) for (x,y) in params.items()]
            path = '%s?%s' % (path, '&'.join(query_args))

        headers = { 'User-Agent': user_agent,
                    'X-Auth-Token': self.token }
                  
        if data and (method in ('POST', 'PUT')):
            # content type is required for requests with a body
            headers.update(json_hdrs)
            
        if isinstance(hdrs, dict):
            headers.update(hdrs)

        dataLen = len(data)
        if dataLen:
            headers['Content-Length'] = dataLen

        def retry_request():
            """
            Re-connect and re-try a failed request once
            """
            self.http_connect()
            self.connection.request(method, path, data, headers)
            return self.connection.getresponse()

        try:
            self.connection.request(method, path, data, headers)
            response = self.connection.getresponse()
        except HTTPException:
            # A simple HTTP exception, just retry once
            response = retry_request()

        # If our caller needs the headers back, they'll have sent this in
        # and it must be a list()!
        if retHeaders:
            retHeaders.extend(response.getheaders())

        raw = response.read()

        # print "status: ", response.status
        # print "response: ", raw

        try:
            responseObj = json.loads(raw)
        except:
            responseObj = {"cloudServersFault": "No message, no response obj"}

        if response.status == 401:
            self._authenticate()
            response = retry_request()

        # if the response is bad, parse and raise the CloudServersFault
        if 400 <= response.status <= 599:
            key = responseObj.keys()[0]
            faultType = "%s%s%s" % (key[0].capitalize(), key[1:], 'Fault')
            fault = responseObj[key]
            faultClass = getattr(ClientErrors, faultType)
            if faultType == 'OverLimitFault':
                raise faultClass(fault['message'], '', fault['code'], fault['retryAfter'])
            else:
                raise faultClass(fault['message'], fault['details'], fault['code'])

        return responseObj

########NEW FILE########
__FILENAME__ = consts
# Copyright (c) 2010, Rackspace.
# See COPYING for details.

"""
Constants used across entire Rackspace Cloud Servers Python API.
"""
import datetime
import com.rackspace.cloud.servers.api.client as ApiClient

__version__ = '0.9' #ApiClient.version.get_version()

user_agent = "python-cloudservers/%s" % __version__

default_authurl =  "https://auth.api.rackspacecloud.com/v1.0"

json_hdrs = {
   "Content-Type": "application/json",
}

xml_hdrs = {
    "Accept": "application/xml",
    "Content-Type": "application/xml",
}

DEFAULT_PAGE_SIZE = 1000
BEGINNING_OF_TIME = datetime.datetime(1969, 12, 31, 17, 0)
def get_version():
    return __version__





########NEW FILE########
__FILENAME__ = entity
# Copyright (c) 2010, Rackspace.
# See COPYING for details.


"""
Entity is the base class for all objects managed by EntityManagers.
"""

class Entity(object):
    """
    Entity object; base class of all Entities managed by EntityManagers.
    """
    def __init__(self, name=""):
        self._name = name
        self._id = None


    @property
    def id(self):
        """
        Get the Entity's id
        """
        return self._id


    @property
    def name(self):
        """
        Get the Entity's name
        """
        return self._name


    def __repr__(self):
        """
        Get the cononical representation of the object, in this case,
        all vars in the object in string form
        """
        return str(vars(self))


    def __eq__(self, other):
        """
        eq assumes that if all the values in the lhs are the same as
        all the equivalent values on the rhs, then they're the same.
        obviously, if there are more attrs on the lhs, they're ignored
        but this serves our purpose
        """
        try:
            has_diff = bool([v for v in vars(self)
                    if getattr(self, v) != getattr(other, v)])
        except AttributeError:
            has_diff = True
        return not has_diff


    def __ne__(self, other):
        return not self.__eq__(other)


    def _notifyIfChanged_(self, other):
        """
        notify change listeners if there are any and the entity has changed
        """
        if (self._manager is not None) and self._manager._changeListeners and (other != self):
            for changeListener in self._manager._changeListeners:
                changeListener(False, self)
        
########NEW FILE########
__FILENAME__ = entitylist
# Copyright (c) 2010, Rackspace.
# See COPYING for details.


"""
EntityList base class. Entity lists are created by an entity manager via the 
the createList and createDeltaList calls.
"""

from datetime import datetime
from com.rackspace.cloud.servers.api.client.errors import InvalidInitialization
from com.rackspace.cloud.servers.api.client.consts import DEFAULT_PAGE_SIZE

class EntityList(list):
    """
    EntityLists behave like regular Python iterables, sort of.

    Full lists automatically page through the collection of items, seeming
    to be a single continuous list.

    Lists created with specific offset and limit parameters do not page this
    way; they're limited to the records they started with.

    Please note that items are cached from the database so, if you iterate
    over the list, one of the things you iterate onto may no longer exist.

    For this reason, you must check that the item still exists before
    attempting to do anything with it and/or catch any exceptions that may be
    generted by accessing a non-existent object.
    """
    def __init__(self, data, detail, manager):
        """
        Create a new EntityList using the data, set to return detailed items
        if requested, and using manager to perform database operations for it.
         """
        if not isinstance(data, list):
            raise InvalidInitialization("Attempt to initialize EntityList with non-list 'data'", data)

        list.__init__(self)
        self.extend(data)
        self._lastModified = datetime.now()
        self._detail = detail
        self._manager = manager
        self._entityIndex = 0
        self._pageIndex = 0


    def setExtendedBehaviour(self, data):
        """
        Sets up internal variables so that future operations behave as
        expected.
        """
        pass


    @property
    def lastModified(self):
        return self._lastModified


    @property
    def detail(self):
        return self._detail


    @property
    def manager(self):
        """
        Get this list's EntityManager.
        """
        return self._manager


    def __iter__(self):
        """
        Iterate through the records by pulling them off the server a page
        at a time.

        Currently set to do DEFAULT_PAGE_SIZE records at a time as per spec.
        """
        x = 0
        while True:
            print "__iter__: ", self.detail, x, DEFAULT_PAGE_SIZE
            theList = self.manager.createListP(self.detail, x, DEFAULT_PAGE_SIZE)
            if theList:
                i = 0
                while True:
					try:
						yield theList[i]
						i += 1
					except IndexError:
						x += i
						break
            else:
                break
        raise StopIteration


    def isEmpty(self):
        return self is None or self == []


    def delta(self):
        return self.manager.createDeltaList(self.detail, self.lastModified)


	def _notAtEnd(self):
		return self._entityIndex < (len(self) + (self._pageIndex * DEFAULT_PAGE_SIZE))


    def hasNext(self):
        if self._notAtEnd():
            return True
        else:
            self = self.manager.createListP(self.detail, self._entityIndex, \
                                            DEFAULT_PAGE_SIZE)
            if len(self) > 0:
                self._pageIndex += 1
                return True
            else:
                return False
    
        
    def next(self):
        if self._notAtEnd():
            ret = self[self._entityIndex]
            self._entityIndex += 1
            return ret
        else:
            self = self.manager.createListP(self.detail, self._entityIndex, \
                    DEFAULT_PAGE_SIZE)
            if len(self) > 0:
                self._pageIndex += 1
                return self[self._entityIndex - 1]
            else:
                return False


    def reset(self):
        self = self.manager.createList(self.detail)
########NEW FILE########
__FILENAME__ = entitymanager
# Copyright (c) 2010, Rackspace.
# See COPYING for details.


"""
EntityManager base class.  EntityManagers belong to a CloudServersService 
object and one is provided for each type of managed Entity: Servers, Images, 
Flavors, and Shared IP Group.
"""
import sys
import threading
from datetime import datetime
from dateutil.parser import parse
from time import sleep
import time

from com.rackspace.cloud.servers.api.client.consts import DEFAULT_PAGE_SIZE, BEGINNING_OF_TIME
from com.rackspace.cloud.servers.api.client.entitylist import EntityList
from com.rackspace.cloud.servers.api.client.errors import BadMethodFault, CloudServersFault, OverLimitFault
from com.rackspace.cloud.servers.api.client.shared.utils import build_url, find_in_list
from com.rackspace.cloud.servers.api.client.shared.cslogging import cslogger


class EntityManager(object):
    """
    EntityManager defines the base functionality of an entity manager and
    provides a standardized way of encapsulating the HTTP operations.

    Note that not all calls may be supported by all entity managers (you are
    not allowed to delete a Flavor, for example) and that it is possible for
    entity managers to extend the base interface with additional calls.

    See the documentation for those managers for details.
    """
    def __init__(self, cloudServersService, requestPrefix, responseKey=None):
        """
        Create the Entity manager.

        Each entity manager has its own `_requestPrefix` used to build API
        calls.

        Since not every entity type uses the `_requestPrefix` to retrieve
        data from the API's response object, we can send in an optional
        responseKey.  If there's no responseKey, it defaults to the 
        requestPrefix.

        The responseKey is only necessary, so far, on Shared IP Groups.
        """
        self._cloudServersService = cloudServersService
        self._requestPrefix = requestPrefix
        self._changeListeners = {}
        self._entityCopies = {} # for wait() comparisons
        #
        ## responseKey is used to handle cases where the key into the returned
        ## response is not the same as the url component used to make
        ## requests
        #
        if responseKey:
            self._responseKey = responseKey
        else:
            self._responseKey = requestPrefix


    def _timeout(func, args=(), kwargs={}, timeout_duration=10, default=None):
        """
        This function will spawn a thread and run the given function
        using the args, kwargs and return the given default value if the
        timeout_duration is exceeded.
        """ 
        import threading
        class InterruptableThread(threading.Thread):
            def __init__(self):
                threading.Thread.__init__(self)
                self.result = default

            def run(self):
                self.result = func(*args, **kwargs)
                it = InterruptableThread()
                it.start()
                it.join(timeout_duration)
                return it.result

    #
    ## These methods hide that we're calling our _cloudServersService to do 
    ## everything
    #
    def _POST(self, data, *url_parts):
        """
        Put together a full POST request and send to our cloudServersService.
        """
        url = build_url(self._requestPrefix, *url_parts)
        retVal = self._cloudServersService.POST(url, data=data)
        return(retVal)


    def _DELETE(self, id, *url_parts):
        """
        Put together a full DELETE request and send it on via our 
        cloudServersService
        """
        url = build_url(self._requestPrefix, id, *url_parts)
        retVal = self._cloudServersService.DELETE(url)
        return retVal


    def _GET(self, url, params=None, headers=None, retHeaders=None):
        url = build_url(self._requestPrefix, url)
        retVal = self._cloudServersService.GET(url, params, headers=headers,
                retHeaders=retHeaders)
        return retVal


    def _PUT(self, *url_parts):
        url = build_url(self._requestPrefix, *url_parts)
        retVal = self._cloudServersService.PUT(url)
        return retVal

    #
    #  CRUD Operations
    #
    # The default implementation of the CRUD operations raises a
    # BadMethodFault exception.
    #
    # For those classes that shouldn't implement these methods, this is the
    # correct exception.
    #
    # For those methods inherited from EntityManager, if the child class does
    # not provide a method by design, it must explicitly raise BadMethodFault.

    def create(self, entity):
        "Create entity, implemented by child classes."
        raise BadMethodFault(self.__class__)

    def remove(self, entity):
        "Remove entity."
        self._DELETE(entity.id)

    def update(self, entity):
        "Update entity, implemented by child classes."
        raise BadMethodFault(self.__class__)

    def refresh(self, entity):
        "Refresh entity, implemented by child classes."
        raise BadMethodFault(self.__class__)

    def find(self, id):
        """
        Find entity by `id`.
        """
        raise BadMethodFault

    #
    # Polling Operations
    #
        
    def wait (self, entity, timeout=None):
        "wait, implemented by child classes."
        raise BadMethodFault

    class Notifier(threading.Thread):
        def __init__ (self, entityManager, entity, changeListener):
            self._entityManager = entityManager
            self._entity = entity
            self._changeListener = changeListener
            self._stopped = False
            threading.Thread.__init__(self)

        def run (self):
            # check the stopped flag at every step to ensure stopNotify
            # kills the thread
            try:
                while not self._stopped: # poll forever or until error
                    if not self._stopped:
                        self._entityManager.wait(self._entity)
                    if not self._stopped:
                        # double check in case wait uses statuses as end states
                        ec = self._entityManager._entityCopies[self._entity.id]                        
                        if self._entity != ec:
                            self._changeListener(False, self._entity)
            except CloudServersFault, fault:
                if not self._stopped:
                    self._changeListener(True, self._entity, fault)

        def stop (self):
            self._stopped = True


    def notify (self, entity, changeListener):
        print "notify"
        notifier = self.Notifier(self, entity, changeListener)
        self._changeListeners[changeListener] = notifier
        notifier.start()


    def stopNotify (self, entity, changeListener):
        print "stopNotify"
        
        self._changeListeners[changeListener].stop()
        del self._changeListeners[changeListener]


    def _sleepUntilRetryAfter_ (self, overLimitFault):
        print "_sleepUntilRetryAfter_"
        
        retryAfter = parse(overLimitFault.retryAfter)
        now = datetime.utcnow()
        retryAfter = retryAfter - retryAfter.tzinfo.utcoffset(retryAfter)
        retryAfter = retryAfter.replace(tzinfo=None)                    
        timedelta = retryAfter - now
        # print 'caught an overlimit fault.  sleeping for ', \
        #       (timedelta.days * 86400) + timedelta.seconds, ' seconds'
        # use absolute value in case retry after ends up accidentally giving 
        # us a date in the past
        sleep(abs((timedelta.days * 86400) + timedelta.seconds))


    #
    # Lists
    #
    def _createList(self, detail=False, offset=0, limit=DEFAULT_PAGE_SIZE,
            lastModified=BEGINNING_OF_TIME):
        """
        Master function that can perform all possible combinations.

        Called by publicly accessible methods to do the actual work.

        What this really has to do is set up a ValueListIterator which will
        then ask us back for the actual data when it's requested.

        http://www.informit.com/articles/article.aspx?p=26148&seqNum=4

        This will actually fetch one page of results so, for efficiency, the
        iterator will have to be clever enough not to re-fetch on the first
        access.
        """
        
        print "_createList: ", detail, offset, limit
        
        # Set flags for parameters we have to act on
        conditionalGet = (lastModified != BEGINNING_OF_TIME)
        pagedGet = (offset != 0 or limit != DEFAULT_PAGE_SIZE)

        uri = self._requestPrefix
        if detail:
            uri += "/detail"
        params = {"offset":offset, "limit":limit}
        
        if conditionalGet:
            params['changes-since'] = lastModified
        
        retHeaders = [] # we may need "last-modified"
        if conditionalGet:
            deltaReturned = False
            while not deltaReturned:
                try:
                    ret_obj = self._cloudServersService.GET(uri, params, retHeaders=retHeaders)
                    deltaReturned = 'cloudServersFault' in ret_obj
                except OverLimitFault as olf:
                    # sleep until retry_after to avoid more OverLimitFaults
                    self._sleepUntilRetryAfter_(olf)
        else:
            ret_obj = self._cloudServersService.GET(uri, params, retHeaders=retHeaders)
        
        # print "ret_obj: " + str(ret_obj)
        
        theList = ret_obj[self._responseKey]

        # Create the entity list
        entityList = self.createEntityListFromResponse(ret_obj, detail)

        cslogger.debug(ret_obj)
        cslogger.debug(retHeaders)

        lastModifiedAsString = None
        if not conditionalGet:
            # For a non-conditional get, we store the one from the
            # returned headers for subsequent conditional gets
            lastModifiedAsString = find_in_list(retHeaders, "last-modified")

        # Now, make the entity list aware of enough state information to
        # perform future operations properly
        data = {'conditionalGet': conditionalGet,
                'pagedGet': pagedGet,
                'lastModified': lastModified }

        if lastModifiedAsString is not None:
            data['lastModifiedAsString'] = lastModifiedAsString
        return entityList


    def createList(self, detail):
        """
        Create a list of all items, optionally with details.
        """
        return self._createList(detail)


    def createDeltaList(self, detail, changes_since):
        """
        Create a list of all items modified since a specific time.
        Do not return until something has changed.
        """
        return self._createList(detail, lastModified=changes_since)


    #
    # Lists, Paged
    #
    def createListP(self, detail, offset, limit):
        """
        Create a paged list.
        """
        return self._createList(detail, offset=offset, limit=limit)


    def createDeltaListP(self, detail, changes_since, offset, limit):
        """
        Create a paged list of items changed since a particular time
        """
        return self._createDeltaList(detail, changes_since=changes_since, 
                offset=offset, limit=limit)

########NEW FILE########
__FILENAME__ = errors
# Copyright (c) 2010, Rackspace.
# See COPYING for details.

"""
Exception (fault) classes.
"""

# Error codes
class ErrorCodes(object):
    """
    Error code manifest constants
    """
    E_UNKNOWN = -1

    # Calls to unimplemented or illegal methods (e.g. delete on Flavors)
    E_NOT_IMPLEMENTED = 1
    E_BAD_METHOD_FAULT = 2

    # Bad use of API due to bad parameters
    E_BAD_PARAMETERS_FAULT = 10

    # Specifically a badly formed server name
    E_INVALID_SERVER_NAME = 30

    # A low-level exception, wrapped in one of our exceptions
    E_HTTPLIB_EXCEPTION = 40


class CloudServersAPIFault(Exception):
    """Interface definition for CloudServersFault"""
    def __init__(self, message, details, code):
        self._message = message
        self._details = details
        self._code = code


    def __repr__(self):
        """
        return error as formatted string
        """
        return "%s:%s : %s" % (self._code, self._message, self._details)


    def __str__(self):
        return "Code   : %s Message: %s Details: %s" % (self.code, self._message, self._details)


    @property
    def message(self):
        return self._message

    @property
    def details(self):
        return self._details

    @property
    def code(self):
        return self._code


NotImplementedException = CloudServersAPIFault("Required Method not Implemented", 
        "", ErrorCodes.E_NOT_IMPLEMENTED)


class OverLimitAPIFault(CloudServersAPIFault):
    """
    Interface definition for an over-limit exception
    """
    def __init__(self, message, details, code, retryAfter):
        super(OverLimitAPIFault, self).__init__(message, details, code)
        self._retryAfter = retryAfter

    @property
    def retryAfter(self):
        return self._retryAfter


class CloudServersFault(CloudServersAPIFault):
    """
    Implementaiton of Cloud Servers Fault
    """
    pass


class OverLimitFault(OverLimitAPIFault):
    """
    Implementation of over-limit exception
    """
    pass


class BadMethodFault(CloudServersAPIFault):
    """
    BadMethodFault, raised when child class is not allowed to implement called
    method i.e. create(), remove() and update() for immutable children of
    EntityManager

    @param className: the name of the class on which the method was called
    """
    def __init__(self, className):
        super(BadMethodFault, self).__init__("Bad Method Fault",
                "Method not allowd on %s class" % (className,),
                ErrorCodes.E_BAD_METHOD_FAULT)


class InvalidArgumentsFault(CloudServersAPIFault):
    """
    Invalid arguments passed to API call.  Use `message` to tell the user
    which call/parameter was involved.
    """
    def __init__(self, message):
        super(InvalidArgumentsFault,self).__init__(message,
                "Bad or missing arguments passed to API call",
                ErrorCodes.E_BAD_PARAMETERS_FAULT)


class HTTPLibFault(CloudServersAPIFault):
    """
    Wraps HTTPExceptions into our exceptions as per spec
    """
    def __init__(self, message):
        super(HTTPLibFault,self).__init__(message, "Low Level HTTPLib Exception",
                ErrorCodes.E_HTTPLIB_EXCEPTION)


class ServerNameIsImmutable(CloudServersAPIFault):
    def __init(self, message):
        super(ServerNameIsImmutable, self).__init__(message,
                "Server can't be renamed when managed by ServerManager")


#-----------------------------------------------------------------------------
# Faults from the Cloud Servers Developer Guide
#-----------------------------------------------------------------------------

class ServiceUnavailableFault(CloudServersAPIFault):
    def __init(self, message):
        super(ServiceUnavailableFault, self).__init__(message, "", ErrorCodes.E_UNKNOWN)


class UnauthorizedFault(CloudServersAPIFault):
    def __init(self, message):
        super(UnauthorizedFault, self).__init__(message, "", ErrorCodes.E_UNKNOWN)


class BadRequestFault(CloudServersAPIFault):
    def __init(self, message):
        super(BadRequestFault, self).__init__(message, "", ErrorCodes.E_UNKNOWN)


class BadMediaTypeFault(CloudServersAPIFault):
    def __init(self, message):
        super(BadMediaTypeFault, self).__init__(message, "", ErrorCodes.E_UNKNOWN)


class ItemNotFoundFault(CloudServersAPIFault):
    def __init(self, message):
        super(ItemNotFoundFault, self).__init__(message, "", ErrorCodes.E_UNKNOWN)


class BuildInProgressFault(CloudServersAPIFault):
    def __init(self, message):
        super(BuildInProgressFault, self).__init__(message, "", ErrorCodes.E_UNKNOWN)


class ServerCapacityUnavailableFault(CloudServersAPIFault):
    def __init(self, message):
        super(ServerCapacityUnavailableFault, self).__init__(message, "", ErrorCodes.E_UNKNOWN)


class BackupOrResizeInProgressFault(CloudServersAPIFault):
    def __init(self, message):
        super(BackupOrResizeInProgressFault, self).__init__(message, "", ErrorCodes.E_UNKNOWN)


class ResizeNotAllowedFault(CloudServersAPIFault):
    def __init(self, message):
        super(ResizeNotAllowedFault, self).__init__(message, "", ErrorCodes.E_UNKNOWN)


#-----------------------------------------------------------------------------
# Extra exceptions, not in formal spec
#-----------------------------------------------------------------------------

class NeedsTestError(Exception):
    pass


class InvalidServerNameFault(CloudServersAPIFault):
    """
    Thrown when an invalid server name is specified.
    """
    def __init__(self, serverName):
        super(InvalidServerName, self).__init__("Invalid Server Name",
                serverName, ErrorCodes.E_INVALID_SERVER_NAME)


class ResponseError(Exception):
    """
    Raised when the remote service returns an error.
    """
    def __init__(self, status, reason):
        self.status = status
        self.reason = reason
        Exception.__init__(self)

    def __repr__(self):
        return '%d: %s' % (self.status, self.reason)


class InvalidUrl(Exception):
    """
    Not a valid url for use with this software.
    """
    pass


class IncompleteSend(Exception):
    """
    Raised when there is a insufficient amount of data to send.
    """
    pass


class AuthenticationFailed(Exception):
    """
    Raised on a failure to authenticate.
    """
    pass


class AuthenticationError(Exception):
    """
    Raised when an unspecified authentication error has occurred.
    """
    pass


class MustBeOverriddenByChildClass(Exception):
    """
    Raised when child class does not override required method defined in
    base class.
    """
    pass


class InvalidInitialization(Exception):
    """
    Raised when a class initializer is passed invalid data.
    """
    pass

########NEW FILE########
__FILENAME__ = file
# Copyright (c) 2010, Rackspace.
# See COPYING for details.

import base64
from com.rackspace.cloud.servers.api.client.jsonwrapper import json

class File(object):
    def __init__(self, path=None, contents=None):
        self._path = path
        self._contents = base64.b64encode(contents)
        
    def get_path(self):
        return self._path

    def set_path(self, value):
        self._path = value
    path = property(get_path, set_path)

    def get_contents(self):
        return self._contents
        
    def set_contents(self, value):
        self._contents = base64.b64encode(value)
    contents = property(get_contents, set_contents)
    
    @property
    def asDict(self):
        """
        Return file object with attributes as a dictionary suitable for use
        in creating a server json object.
        """
        return { "file": { "path": self.path, "contents": self.contents } }

    @property
    def asJSON(self):
        """
        Return the file object converted to JSON suitable for creating a
        server.
        """
        return json.dumps(self.asDict)
    
########NEW FILE########
__FILENAME__ = flavor
# Copyright (c) 2010, Rackspace.
# See COPYING for details.


"""
Flavor Entity.

A flavor is an available hardware configuration for a server. Each flavor has a
unique combination of disk space and memory capacity.
"""

import copy
from com.rackspace.cloud.servers.api.client.entity import Entity


class Flavor(Entity):
    """
    Flavor

    A flavor is an available hardware configuration for a server. Each flavor
    has a unique combination of disk space and memory capacity.

    """
    def __init__(self, name=None):
        super(Flavor, self).__init__(name)
        self._id = self._ram = self._disk = None
        self._manager = None

    def __eq__(self, other):
        return (self._id, self._name, self._ram, self._disk) == (other._id, other._name, other._ram, other._disk)


    def __ne__(self, other):
        return (self._id, self._name, self._ram, self._disk) != (other._id, other._name, other._ram, other._disk)


    def initFromResultDict(self, dic):
        """
        Fills up a Flavor object dict which is a result of a
        query (detailed or not) from the API
        """
        # This will happen when e.g. a find() fails.
        if dic is None:
            return

        # make a copy so we can decide if we should notify later
        flavorCopy = copy.copy(self)

        #
        ## All status queries return at least this
        #
        self._id = dic.get("id")
        self._name = dic.get("name")
        self._ram = dic.get("ram")
        self._disk = dic.get("disk")

        # notify change listeners if there are any and the server has changed
        self._notifyIfChanged_(flavorCopy)

    @property
    def ram(self):
        return self._ram

    @property
    def disk(self):
        return self._disk

########NEW FILE########
__FILENAME__ = flavormanager
# Copyright (c) 2010, Rackspace.
# See COPYING for details.

"""
Flavor Manager - entity manager for Cloud Servers flavors.
"""

import copy
from datetime import datetime

from com.rackspace.cloud.servers.api.client.entitymanager import EntityManager
from com.rackspace.cloud.servers.api.client.entitylist import EntityList
import com.rackspace.cloud.servers.api.client.errors as ClientErrors
from com.rackspace.cloud.servers.api.client.flavor import Flavor

"""
BadMethodFault is raised whenever a method is called that is not allowed.

Because flavors are immutable (provided by the API) and can not be changed
through the API.
"""
_bmf = ClientErrors.BadMethodFault("FlavorManager")


class FlavorManager(EntityManager):
    """
    Manages the list of server Flavors
    """
    def __init__(self, cloudServersService):
        super(FlavorManager, self).__init__(cloudServersService, "flavors")

    def create(self, entity):
        raise _bmf

    def refresh(self, entity):
        entity.initFromResultDict(self.flavorDetails(entity.id))
        entity._manager = self

    def remove(self, entity):
        raise _bmf

    def find(self, id):
        """
        Find the flavor given by `id` and returns a Flavor object filled with
        data from the API or None if the `id` can't be found.
        """
        try:
            detailsDict = self.flavorDetails(id)
        except ClientErrors.CloudServersAPIFault, e:
            if e.code == 404:   # not found
                return None     # just return None
            else:               # some other exception, just re-raise
                raise
        retFlavor = Flavor("")
        retFlavor.initFromResultDict(detailsDict)
        retFlavor._manager = self
        return retFlavor


    def flavorDetails(self, id):
        """
        Gets details dictionary for flavor with `id`.  If the flavor can't
        be found, returns None
        """
        retDict = None
        ret = self._GET(id, { "now": str(datetime.now()) })
        return ret.get("flavor")

    #
    # Polling Operations
    #    
    def _wait(self, flavor):
        """
        Wait implementation
        """
        thisFlavor = self._entityCopies[flavor.id]
        while flavor == thisFlavor:
            try:
                self.refresh(flavor)
            except ClientErrors.OverLimitFault as olf:
                # sleep until retry_after to avoid more OverLimitFaults
                self._sleepUntilRetryAfter_(olf)
            except ClientErrors.CloudServersFault:
                pass


    def wait (self, flavor, timeout=None):
        """
      	timeout is in milliseconds
        """
        self._entityCopies[flavor.id] = copy.copy(flavor)
        if timeout is None:
            self._wait(flavor)
        else:
            result = self._timeout(self._wait, (flavor,), timeout_duration=timeout/1000.0)


    def createEntityListFromResponse(self, response, detail):
        """
        Creates list of Flavor objects from response to list command sent
        to API
        """
        theList = []
        data = response["flavors"]
        for jsonObj in data:
            flavor = Flavor("")
            flavor.initFromResultDict(jsonObj)
            theList.append(flavor)
        return EntityList(theList, detail, self)

########NEW FILE########
__FILENAME__ = image
# Copyright (c) 2010, Rackspace.
# See COPYING for details.


"""
Image Entity.

An image is a collection of files you use to create or rebuild a server.
Rackspace provides pre-built OS images by default.
"""

import copy
from com.rackspace.cloud.servers.api.client.entity import Entity


class Image(Entity):
    """
    Image

    An image is a collection of files you use to create or rebuild a server.
    Rackspace provides pre-built OS images by default. You may also create 
    custom images.
    """
    def __init__(self, name=None):
        super(Image, self).__init__(name)
        self._id = self._updated = self._created = None
        self._status = self._progress = None
        self._manager = None


    def initFromResultDict(self, dic):
        """
        Fills up a Image object dict which is a result of a
        query (detailed or not) from the API
        """

        # This will happen when e.g. a find() fails.
        if dic is None:
            return

        # make a copy so we can decide if we should notify later
        imageCopy = copy.copy(self)

        #
        ## All status queries return at least this
        #
        self._id = dic.get("id")
        self._name = dic.get("name")
        # Detailed queries have 'updated'
        self._updated = dic.get("updated")
        self._created = dic.get("created")
        self._status = dic.get("status")
        # User created images have this...
        self._progress = dic.get("progress")

        # notify change listeners if there are any and the server has changed
        self._notifyIfChanged_(imageCopy)


    @property
    def updated(self):
        return self._updated

    @property
    def created(self):
        return self._created

    @property
    def status(self):
        return self._status

    @property
    def progress(self):
        return self._progress

########NEW FILE########
__FILENAME__ = imagemanager
# Copyright (c) 2010, Rackspace.
# See COPYING for details.


"""
ImageManager - EntityManager for managing image entities.
"""

from datetime import datetime
import time
import copy

from com.rackspace.cloud.servers.api.client.entitymanager import EntityManager
from com.rackspace.cloud.servers.api.client.entitylist import EntityList
from com.rackspace.cloud.servers.api.client.errors import BadMethodFault, \
        NotImplementedException, CloudServersAPIFault
from com.rackspace.cloud.servers.api.client.image import Image

"""
BadMethodFault is raised whenever a method is called that is not allowed
for flavors. Images are (currently) immutable (provided by the API) and can
not be changed through the API.
"""
_bmf = BadMethodFault("ImageManager")


class ImageManager(EntityManager):
    """
    Manages the list of server Images.
    """
    def __init__(self, cloudServersService):
        super(ImageManager, self).__init__(cloudServersService, "images")

    def create(self, entity):
        "Not implemented by this class, by design."
        raise _bmf

    def remove(self, entity):
        "Not implemented by this class, by design."
        raise _bmf

    def update(self, entity):
        "Not implemented by this class, by design."
        raise _bmf

    def refresh(self, entity):
        entity.initFromResultDict(self.imageDetails(entity.id))
        entity._manager = self

    def find(self, id):
        """
        Find the image given by `id` and returns an Image object filled with
        data from the API or None if the `id` can't be found.
        """
        try:
            detailsDict = self.imageDetails(id)
        except CloudServersAPIFault, e:
            if e.code == 404:   # not found
                return None     # just return None
            else:               # some other exception, just re-raise
                raise
        retImage = Image("")
        retImage.initFromResultDict(detailsDict)
        retImage._manager = self
        return retImage

    def imageDetails(self, id):
        """
        Gets details dictionary for image with `id`.  If the image can't
        be found, returns None
        """
        retDict = None
        ret = self._GET(id, { "now": str(datetime.now()) })
        return ret.get("image")


    #
    # Polling Operations
    #
    def _wait(self, image):
        """
        Wait implementation
        """
        while image.status in ('ACTIVE', 'FAILED', 'UNKNOWN'):
            try:
                self.refresh(image)
            except OverLimitFault, e:
                # sleep until retry_after to avoid more OverLimitFaults
                self._sleepUntilRetryAfter_(e)
            except CloudServersFault:
                pass


    def wait (self, image, timeout=None):
        """
      	timeout is in milliseconds
        """
        self._entityCopies[image.id] = copy.copy(image)
        if timeout is None:
            self._wait(image)
        else:
            result = self._timeout(self._wait, (image, ), timeout_duration=timeout/1000.0)


    def createEntityListFromResponse(self, response, detail):
        """
        Creates list of image objects from response to list command sent
        to API
        """
        theList = []
        data = response["images"]
        for jsonObj in data:
            img = Image("")
            img.initFromResultDict(jsonObj)
            theList.append(img)
        return EntityList(theList, detail, self)

########NEW FILE########
__FILENAME__ = jsonwrapper
# Copyright (c) 2010, Rackspace.
# See COPYING for details.


"""
Wrapper around JSON libraries.  We start trying the JSON library built into
Python 2.6, and fall back to using simplejson otherwise.

NOTE: simplejson is installed if we're not on 2.6+ by our setup.py
"""

try:
    # 2.6 will have a json module in the stdlib
    import json
except ImportError:
    try:
        # simplejson is the thing from which json was derived anyway...
        import simplejson as json
    except ImportError:
        print "No suitable json library found, see INSTALL.txt"
        raise

########NEW FILE########
__FILENAME__ = personality
# Copyright (c) 2010, Rackspace.
# See COPYING for details.

from com.rackspace.cloud.servers.api.client.jsonwrapper import json

class Personality:
    def __init__(self):
        self._files = None
        
    def get_files(self):
        return self._files

    def set_files(self, value):
        self._files = value
    files = property(get_files, set_files)

    @property
    def asDict(self):
        """
        Return personality object with attributes as a dictionary suitable for 
        use in creating a server json object.
        """
        personalityAsDict = { "personality": [] }
        
        for file in self.files:
            personalityAsDict['personality'].append(file.asDict)        
        return personalityAsDict

    @property
    def asJSON(self):
        """
        Return the personality object converted to JSON suitable for creating a
        server.
        """
        return json.dumps(self.asDict)

########NEW FILE########
__FILENAME__ = server
# Copyright (c) 2010, Rackspace.
# See COPYING for details.

"""
Server Entity
"""

import copy

from com.rackspace.cloud.servers.api.client.jsonwrapper import json
from com.rackspace.cloud.servers.api.client.entity import Entity

#
## This is what is specified in the docs, not sure what we'll use it for but
## wanted to have this around for reference
#
serverStatus = ("ACTIVE", "BUILD", "REBUILD", "SUSPENDED", "QUEUE_RESIZE",
        "PREP_RESIZE", "VERIFY_RESIZE", "PASSWORD", "RESCUE", "UNKNOWN")


class Server(Entity):
    def __init__(self, name, imageId=None, flavorId=None, metadata=None, personality=None):
        """
        Create new Server instance with specified name, imageId, flavorId and
        optional metadata.

        NOTE: This creates the data about the server, to actually create
        an actual "Server", you must ask a ServerManager.
        """
        super(Server, self).__init__(name)

        self._imageId = imageId
        self._flavorId = flavorId
        self._metadata = metadata
        # Set when a ServerManager creates a server
        self._manager = None
        # this server's ID
        self._id = None
        self._hostId = None
        self._progress = None
        self._addresses = None
        self._personality = None
        self._lastModified = None


    def __str__(self):
        return self.asJSON


    def initFromResultDict(self, dic, headers=None):
        """
        Fills up a server object from the dict which is a result of a query
        (detailed or not) from the API
        """
        # This will happen when e.g. a find() fails.
        if dic is None:
            return
        
        # make a copy so we can decide if we should notify later
        serverCopy = copy.copy(self)

        if headers:
            try:
                self._lastModified = [hd[1] for hd in headers
                        if hd[0] == "date"][0]
            except IndexError:
                # No date header
                self._lastModified = None

        #
        ## All status queries return at least this
        #
        self._id = dic.get("id")
        self._name = dic.get("name")
        self._status = dic.get("status")
        self._hostId = dic.get("hostId")
        self._metadata = dic.get("metadata")
        self._imageId = dic.get("imageId")
        self._flavorId = dic.get("flavorId")
        self._addresses = dic.get("addresses")
        # progress isn't necessarily always available
        self._progress = dic.get("progress")
        # We only get this on creation
        self._adminPass = dic.get("adminPass")

        # notify change listeners if there are any and the server has changed
        self._notifyIfChanged_(serverCopy)
        
    def _get_name(self):
        """Server's name (immutable once created @ Rackspace)."""
        return self._name

    def _set_name(self, value):
        """
        Rename a server.
        NOTE: This routine will throw a ServerNameIsImmutable fault if you try
        to rename a server attached to a ServerManager since that would
        put the name in the object and the name stored on the server
        out of sync.

        TBD:  there is an API call to change the server name and adminPass but
        it doesn't seem to allow for just changing the name.
        We could get around this by retrieving the password, then setting
        both in one shot, except you can't retrieve the password...

        TBD: Capture this comment/plan for next version.
        """
        if self._manager is None:   # if we're not owned by anyone
            self._name = value
        else:
            raise ServerNameIsImmutable("Can't rename server")
    name = property(_get_name, _set_name)


    def _get_personality(self):
        """Server's personality."""
        if self._personality:
            return self._personality
        else:
            return None

    def _set_personality(self, value):
        """Server's personality."""
        self._personality = value
    personality = property(_get_personality, _set_personality)


    @property
    def imageId(self):
        """
        Get the server's current imageId.
        """
        return self._imageId


    @property
    def flavorId(self):
        """
        Get server's current flavorId
        """
        return self._flavorId


    @property
    def metadata(self):
        """
        Return server's current metadata
        """
        return self._metadata


    @property
    def id(self):
        """
        Get the server's id
        """
        return self._id


    @property
    def hostId(self):
        """
        Get the server's hostId
        """
        return self._hostId


    @property
    def progress(self):
        """
        Server's progress as of the most recent status or 
        serverManager.ssupdate()
        """
        return self._progress


    @property
    def lastModified(self):
        """
        Server's last modified date as returned in Date header.  
        May not be the actual last modified date
        """
        return self._lastModified


    @property
    def addresses(self):
        """
        IP addresses associated with this server.
        """
        return self._addresses


    @property
    def adminPass(self):
        """
        Get admin password (only available if created within current session).
        """
        return self._adminPass


    @property
    def asDict(self):
        """
        Return server object with attributes as a dictionary suitable for use
        in creating a server json object.
        """
        serverAsDict = { "server": { "name": self.name,
                "imageId": self.imageId,
                "flavorId": self.flavorId,
                "metadata": self.metadata } }
        if self.personality:
            serverAsDict["server"]["personality"] = self.personality.asDict
        return serverAsDict


    @property
    def asJSON(self):
        """
        Return the server object converted to JSON suitable for creating a
        server.
        """
        return json.dumps(self.asDict)


    @property
    def status(self):
        """
        Get status of server, such as ACTIVE, BUILD, etc
        """
        return self._status

########NEW FILE########
__FILENAME__ = servermanager
# Copyright (c) 2010, Rackspace.
# See COPYING for details.

"""
ServerManager class.  Cloud Servers Entity Manager for Servers.

Provides interface for all Server operations as a component part of 
a Cloud Servers Service object.
"""

from datetime import datetime
import time
import copy

from com.rackspace.cloud.servers.api.client.entitymanager import EntityManager
from com.rackspace.cloud.servers.api.client.entitylist import EntityList

import com.rackspace.cloud.servers.api.client.errors as ClientErrors
from com.rackspace.cloud.servers.api.client.server import Server
from com.rackspace.cloud.servers.api.client.jsonwrapper import json
from com.rackspace.cloud.servers.api.client.backupschedule import BackupSchedule


class RebootType(object):
    """
    Just encloses hard/soft reboots so they can be referenced as
    rebootType.hard and rebootType.soft
    """
    hard = "HARD"
    soft = "SOFT"

"""
rebootType is just an instance of RebootType() for referring to hard/soft
reboots
"""
rebootType = RebootType()


class ServerManager(EntityManager):
    """
    Entity manager for servers.
    """
    def __init__(self, parent):
        super(ServerManager, self).__init__(parent, "servers")
        self._resizedServerIds = []

    #
    # Inherited
    #
    def create(self, server):
        """
        Create an actual server from the passed Server object
        """
        ret = self._POST(server.asJSON)
        # We update the object so it knows we're its manager
        # the manager property is ReadOnly so we're using an
        # internal variable here.  We're its manager, that's OK.
        server._manager = self
        server.initFromResultDict(ret["server"])

    # implemented in EntityManager
    #remove(self, server):
    #    self._DELETE(server.id)
    #    self.update(server) # get up-to-date status

    def update(self, server):
        server.initFromResultDict(self.serverDetails(server.id))
        server._manager = self

    def refresh(self, server):
        if server.lastModified == None:
            retHeaders = [(None, None)]
            serverDict = self.serverDetails(server.id, retHeaders=retHeaders)            
            server.initFromResultDict(serverDict, retHeaders)
            server._manager = self
        else:
            serverDict = self.serverDetails(server.id, \
                                        ifModifiedSince=server.lastModified)
            if serverDict:
                server.initFromResultDict(serverDict)

    def find(self, id):
        """
        Find the server given by `id` and returns a Server object filled with
        data from the API or None if the `id` can't be found.
        """
        try:
            retHeaders = [(None, None)]
            detailsDict = self.serverDetails(id, retHeaders=retHeaders)
        except ClientErrors.CloudServersAPIFault, e:
            if e.code == 404:   # not found
                return None     # just return None
            else:               # some other exception, just re-raise
                raise

        retServer = Server("")
        retServer.initFromResultDict(detailsDict, retHeaders)
        retServer._manager = self
        return retServer

    def status(self, id):
        """
        Get current status of server with `id`, returns statusDict so that
        server can update itself.
        """
        statusDict = self.serverDetails(id)
        return(statusDict["status"])

    def serverDetails(self, id, ifModifiedSince=None, retHeaders=None):
        """
        Gets details dictionary for server with `id`.  If the server can't
        be found, returns None
        """
        retDict = None
        headers = None
        if ifModifiedSince != None:
            headers = { 'If-Modified-Since': ifModifiedSince }
        
        ret = self._GET(id, { "now": str(datetime.now()) }, headers=headers, \
                        retHeaders=retHeaders)
        try:
            retDict = ret["server"]
        except KeyError, e:
            retDict = None

        return retDict

    #
    # ServerManager specificCloudServersAPIFault
    #

    def _post_action(self, id, data):
        url_parts = (id, "action")
        self._POST(data, url_parts)

    def _put_action(self, id, action):
        url_parts = (id, "action", action)
        self._PUT(id, url_parts)

    def _delete_action(self, id, action):
        self._DELETE(id, "action", action)

    def reboot(self, server, rebootType):
        """
        Reboot a server either "HARD", "SOFT".

        "SOFT" signals reboot with notification i.e. 'graceful'
        "HARD" forces reboot with no notification i.e. power cycle the server.
        """
        if rebootType in ("HARD", "SOFT"):
            id = server.id
            data = json.dumps({"reboot": {"type": rebootType}})
            self._post_action(id, data)
            self.refresh(server)    # get updated status
        else:
            raise ClientErrors.InvalidArgumentsFault("Bad value %s passed for reboot type,\
                                        must be 'HARD' or 'SOFT'", rebootType)

    def rebuild(self, server, imageId=None):
        """
        Rebuild a server, optionally specifying a different image.  If no new
        image is supplied, the original is used.
        """
        if not imageId:
            imageId = server.imageId
        data = json.dumps({"rebuild": {"imageId":imageId}})
        id = server.id
        self._post_action(id, data)

    def _resizeNotifyCallback(isError, server, fault):
        if isError == False and server.status == 'VERIFY_RESIZE':
            self._resizedServerIds.append(server)

    def resize(self, server, flavorId):
        """
        Change a server to a different size/flavor.  A backup is kept of the
        original until you confirmResize or it recycles automatically (after
        24 hours).
        """
        if not flavorId:
            flavorId = server.flavorId
        data = json.dumps({"resize": {"flavorId":flavorId}})
        id = server.id
        self._post_action(id, data)
        self.notify(server, _resizeNotifyCallback)

    def _confirmResizeNotifyCallback(isError, server, fault):
        if isError == False and server.status != 'VERIFY_RESIZE':
            self._resizedServerIds.remove(server)

    def confirmResize(self, server):
        """
        Confirm resized server, i.e. confirm that resize worked and it's OK to
        delete all backups made when resize was performed.
        """
        data = json.dumps({"confirmResize": None})
        id = server.id
        self._post_action(id, data)
        self.notify(server, _confirmResizeNotifyCallback)

    def revertResize(self, server):
        """
        Revert a resize operation, restoring the server from the backup made
        when the resize was performed.
        """
        data = json.dumps({"revertResize": None})
        id = server.id
        self._post_action(id, data)

    def shareIp (self, server, ipAddr, sharedIpGroupId, configureServer):
        url_parts = (server.id, "ips", "public", ipAddr)
        data = json.dumps({"shareIp": {"sharedIpGroupId": sharedIpGroupId, \
                            "configureServer": configureServer}})
        self._PUT(data, url_parts)

    def unshareIp (self, server, ipAddr):
        self._DELETE(server.id, "ips", "public", ipAddr)

    def setSchedule(self, server, backupSchedule):
        url_parts = (server.id, "backup_schedule")
        self._POST(backupSchedule.asJSON, url_parts)

    def getSchedule(self, server):
        backupDict = self._GET(server.id, "backup_schedule")
        backupSchedule = BackupSchedule()
        print "backupDict: ", backupDict
        try:
            backupSchedule.initFromResultDict(backupDict["backupSchedule"])
        except:
            pass # return an empty backup schedule
        return backupSchedule

    #
    ## Polling operations
    #
    def _serverInWaitState(self, server):
        if server in self._resizedServerIds:
	        end_states = ('ACTIVE', 'SUSPENDED', 'DELETED', 'ERROR', 'UNKNOWN')
    	else:
    		end_states = ('ACTIVE', 'SUSPENDED', 'VERIFY_RESIZE', 'DELETED', 'ERROR', 'UNKNOWN')
        return server.status in end_states
    
    
    def _wait(self, server):
        while self._serverInWaitState(server):
            try:
                self.refresh(server)
            except ClientErrors.OverLimitFault, e:
                # sleep until retry_after to avoid more OverLimitFaults
                self._sleepUntilRetryAfter_(e)
            except ClientErrors.CloudServersFault:
                pass


    def wait (self, server, timeout=None):
        """
      	timeout is in milliseconds
        """
        self._entityCopies[server.id] = copy.copy(server)
        if timeout is None:
            self._wait(server)
        else:
            result = self._timeout(self._wait, (server,), timeout_duration=timeout/1000.0)

    #
    ## Support methods
    #
    def createEntityListFromResponse(self, response, detail=False):
        """
        Creates list of server objects from response to list command sent
        to API
        """
        theList = []
        data = response["servers"]
        for jsonObj in data:
            srv = Server("")
            srv.initFromResultDict(jsonObj)
            theList.append(srv)
        return EntityList(theList, detail, self)


########NEW FILE########
__FILENAME__ = cslogging
#
## Copyright (c) 2010, Rackspace.
## See COPYING for details.
#

"""
Logging functions for unit tests.

Logs are kept in the .../cloudservers/tests/logs directory.

If the cloudservers package is installed into the system Python, you may or 
may not have permission to create files in that location. This is normal and, 
if you're going to be using the test suite, you would be better off installing 
using the:

    python setup.py develop

command.

This just points your Python's library path at the directory into which you've 
checked out or unzipped the Cloud Servers Service. That way, you can write 
your changes, the unit test log files, etc. back to someplace you know you 
have 'write' permission.

Default rotation is 5 i.e. 5 results kept before oldest is overwritten.

There is currently no way to change rotation schedule other than modifying 
this code. This may be addressed in a future version of this API if there's a 
good reason to do so.


"""

import os
import logging
import logging.handlers

#
## Get the full path of the current Python file (cslogging.py)
#
this_file_path = os.path.dirname(os.path.realpath(__file__))

#
## The log file path is one up (..) from this file, in a subdir called 'logs'
#
LOG_FILE_PATH = os.path.join(this_file_path, "..", "logs")

#
## If the log file path doesn't exist, attempt to create it.
## Any exception is an error and probably means we can't write to the
## installation directory.  That would be normal during an install into the 
## system Python is on, for example, OS X.
#

if not os.path.exists(LOG_FILE_PATH):
    os.makedirs(LOG_FILE_PATH)

#
## Set our testing logfile name and full path
##
## This localizes our logfile to the path from which we're testing so we
## have a separate log for each testing directory.  Very handy for figuring
## out why it works so well in some plaes, but not others.
#
LOG_FILE_NAME = "cloudfiles.test.log"
LOG_FILE = os.path.join(LOG_FILE_PATH, LOG_FILE_NAME)

#
## Create a logger
#
cslogger =  logging.getLogger("cs")

#
## Make sure it captures everything up to and including DEBUG output
#
cslogger.setLevel(logging.DEBUG)

#
## Keep history of last five runs, keep 125k of debug info
#
handler = logging.handlers.RotatingFileHandler(LOG_FILE, maxBytes=125*1024, backupCount=5)

#
## Set formatting to something we can read
#
formatter = logging.Formatter("%(levelname)s: %(message)s %(pathname)s:%(lineno)d")

#
## Make sure out logger writes to the log file
#
cslogger.addHandler(handler)
########NEW FILE########
__FILENAME__ = utils
# Copyright (c) 2010, Rackspace.
# See COPYING for details.

import re
import string
from urlparse  import urlparse
from com.rackspace.cloud.servers.api.client.errors import InvalidUrl

# initialize only once, when this is imported
stripchars = string.whitespace + '/'


def find_in_list(somelist, searchValue, keyIndex=0, valueIndex=0):
    """
    Finds an item in a list of sequences where the key is in
    list[item][keyIndex] and the value is in list[item][valueIndex]
    """
    for i in somelist:
        if searchValue == i[keyIndex].lower():
            return i[valueIndex]
    return None


def parse_url(url):
    """
    Given a URL, returns a 4-tuple containing the hostname, port,
    a path relative to root (if any), and a boolean representing
    whether the connection should use SSL or not.
    NOTE: this routine's error checking is very weak.  Bad ports like ABC are
    not detected, for example.
    """
    scheme, netloc, path, params, query, frag = urlparse(url)

    # We only support web services
    if not scheme in ('http', 'https'):
        raise InvalidUrl('Scheme must be one of http or https')

    is_ssl = (scheme == 'https')

    # Verify hostnames are valid and parse a port spec (if any)
    match = re.match('([a-zA-Z0-9\-\.]+):?([0-9]{2,5})?', netloc)
    if match:
        (host, port) = match.groups()
        if not port:
            port = {True: 443, False: 80}[is_ssl]
    else:
        raise InvalidUrl('Invalid host and/or port: %s' % netloc)

    return (host, int(port), path.strip('/'), is_ssl)


def build_url(*params):
    """
    Join two or more url components, inserting '/' as needed.

    Cleans up the params before joining them

        * Removes whitespace from both ends
        * Removes any leading and trailing slashes
        * Converts integers to strings (used for server id's a lot)

    Also, sequences in paramters are properly handled i.e.:

        build_url("this", ("that", "and", "the"), "other")

    will produce:

        "this/that/and/the/other"

    The nesting, padding, '/' chars etc. can be completely arbitrary and this
    routine will handle it.

    If you find a case where it can't, please send a bug report!
    """

    path = ""
    elems = []
    for p in params:
        # we handle skipping None so callers needn't worry
        if not p:
            continue

        # If it's an iterable (this test will skip strings)
        #   go add it recursively
        if hasattr(p , '__iter__'):
            # Expand the iterable and pass it on, assign return value
            # to path and continue
            elems.append(build_url(path, *p))
        else:
            if isinstance(p, int):    # see if it's the same type as an int
                p = str(p)

            # strip all leading and trailing whitespace and '/'
            elems.append(p.strip(stripchars))
    return "/".join(elems)


########NEW FILE########
__FILENAME__ = sharedipgroup
# Copyright (c) 2010, Rackspace.
# See COPYING for details.

"""
SharedIpGroup object
"""

import copy

from com.rackspace.cloud.servers.api.client.entity import Entity
from com.rackspace.cloud.servers.api.client.jsonwrapper import json

"""
SharedIpGroup objects provide a convenient encapsulation of information about
shared IP groups.

As with Server objects, these objects must be manipulated with a manager class,
in this case, the SharedIpGroupManager.
"""


class SharedIpGroup(Entity):
    """
    Shared IP group objects.
    """
    def __init__(self, name="", server=None):
        """
        Create new SharedIpGroup instance. `servers` is singular since you can
        only create a new IP group by adding a single server.

        Further queries regarding the SharedIpGroup may include multiple
        servers in a list, but that info will be filled in by the API, and can
        not be done on construction.
        """
        super(SharedIpGroup, self).__init__(name)

        self._servers   = server
        self._manager = None


    def __str__(self):
        return "Name = %s : servers = %s" % (self._name, self._servers)


    def __eq__(self, other):
        return (self._id, self._name, self._servers) == (other._id, other._name, other._servers)


    def __ne__(self, other):
        return (self._id, self._name, self._servers) != (other._id, other._name, other._servers)


    def _get_name(self):
        """Get name from shared ip group object."""
        return self._name

    def _set_name(self, value):
        """Set name for this IP Group"""
        self._name = value
    name = property(_get_name, _set_name)


    @property
    def servers(self):
        return self._servers

    @property
    def asDict(self):
        """
        Return IP group object with attributes as a dictionary
        """
        # The key changes depending on whether we're dealing with a request,
        # where we're only supposed to have one, or a response, where the
        # API returns the list of servers in the IP group
        if hasattr(self._servers , "__iter__"):
            serverKey = "servers"
        else:
            serverKey = "server"

        return { "sharedIpGroup": { "id": self._id, "name": self._name, serverKey: self._servers } }

    @property
    def asJSON(self):
        """
        Return the backup schedule object converted to JSON
        """
        return json.dumps(self.asDict)


    def initFromResultDict(self, dic):
        """
        Fills up a shared ip group object from the dict which is a result of a
        query (detailed or not) from the API
        """
        # This will happen when e.g. a find() fails.
        if dic is None:
            return

        # make a copy so we can decide if we should notify later
        sharedIpGroupCopy = copy.copy(self)

        #
        ## All status queries return at least this
        #
        self._id = dic.get("id")
        self._name = dic.get("name")
        # if it has servers, grab those too
        self._servers = dic.get("servers")

        # notify change listeners if there are any and the server has changed
        self._notifyIfChanged_(sharedIpGroupCopy)

########NEW FILE########
__FILENAME__ = sharedipgroupmanager
# -*- test-case-name: com.rackspace.cloud.servers.api.client.tests.test_sharedipgroupmanager -*-

# Copyright (c) 2010, Rackspace.
# See COPYING for details.

"""
SharedIpGroupManager class.  
Cloud Servers Entity Manager for Shared IP Groups.

Provides interface for all Shared IP Group operations as a component part of a
Cloud Servers Service object.
"""

import copy
from datetime import datetime

from com.rackspace.cloud.servers.api.client.entitymanager import EntityManager
from com.rackspace.cloud.servers.api.client.entitylist import EntityList
import com.rackspace.cloud.servers.api.client.errors as ClientErrors
from com.rackspace.cloud.servers.api.client.sharedipgroup import SharedIpGroup

# _bmf is shortcut for BadMethodFault with our classname
_bmf = ClientErrors.BadMethodFault("SharedIpGroupManager")
# _nie is shortcut for NotImplementedException
_nie = ClientErrors.NotImplementedException


class SharedIpGroupManager(EntityManager):
    """
    Manages the list of shared IP groups
    """
    def __init__(self, cloudServersService):
        super(SharedIpGroupManager, self).__init__(cloudServersService, "shared_ip_groups", "sharedIpGroups")


    def create(self, ipgroup):
        """
        Create an IP Group using the passed in ipgroup.  NOTE: it is an error
        to create an IP Group with the 'servers' ivar containing a list of
        more than one server.
        TBD: trap that and throw an exception here
        """
        ret = self._POST(ipgroup.asJSON)
        ipgroup._manager = self


    def update(self, ipgroup):
        raise _nie


    def refresh(self, entity):
        entity.initFromResultDict(self.sharedIpGroupDetails(entity.id))
        entity._manager = self


    def find(self, id):
        """
        Find the shared ip group given by `id` and return a SharedIpGroup
        object or None if the `id` can't be found.
        """
        try:
            detailsDict = self.sharedIpGroupDetails(id)
        except ClientErrors.CloudServersAPIFault, e:
            if e.code == 404:
                # not found; just return None
                return None
            else:
                # some other exception, just re-raise
                raise

        retSharedIpGroup = SharedIpGroup()  # shared ip group to populate
        retSharedIpGroup.initFromResultDict(detailsDict)
        retSharedIpGroup._manager = self
        return retSharedIpGroup


    def sharedIpGroupDetails(self, id):
        """
        Gets details dictionary for shared ip group with `id`.  Returns None
        if the sharedIpGroup can't be found.
        """
        retDict = None
        ret = self._GET(id, { "now": str(datetime.now()) })
        try:
            retDict = ret["sharedIpGroup"]
        except KeyError, e:
            retDict = None
        return retDict

    #
    # Polling Operations
    #
    def _wait(self, sharedIpGroup):
        """
        Wait implementation
        """
        thisGroup = self._entityCopies[sharedIpGroup.id]
        while sharedIpGroup == thisGroup:
            try:
                self.refresh(sharedIpGroup)
            except ClientErrors.OverLimitFault, e:
                # sleep until retry_after to avoid more OverLimitFaults
                self._sleepUntilRetryAfter_(e)
            except ClientErrors.CloudServersFault:
                pass


    def wait (self, sharedIpGroup, timeout=None):
        """
      	timeout is in milliseconds
        """
        self._entityCopies[sharedIpGroup.id] = copy.copy(sharedIpGroup)
        if timeout is None:
            self._wait(sharedIpGroup)
        else:
            result = self._timeout(self._wait, (sharedIpGroup,), timeout_duration=timeout/1000.0)


    def createEntityListFromResponse(self, response, detail):
        ip_groups = response["sharedIpGroups"]
        retList = []
        for g in ip_groups:
            shared = SharedIpGroup()
            shared.initFromResultDict(g)
            retList.append(shared)
        return EntityList(retList, detail, self)

########NEW FILE########
__FILENAME__ = account
RS_UN = "your user name"
RS_KEY = "your api key"


__all__ =(RS_UN, RS_KEY)
########NEW FILE########
__FILENAME__ = cloud_servers_console
"""

 cloud_servers_console

 A very simple text menu based application for showing the status of
everything in your Cloud Servers account.

 I developed this to make it simple to test the functionality of the library
as I went along and found it to be so handy I just left it in.

 Also, it shows real-world examples of the API in actual use which is always
my favorite type of documentation.

 It is purposely written in the most simple, straight-forward way without the
 types of optimizations or error handling that could be done in a production
 app in order to clearly show the simplest use of the API calls.

 NOTE: In order to actually run the console, you must create the file
account.py, in the tests directory, with the settings for your Cloud Servers
account.

 NOTE: Any servers created by this program are actual, live, working, billable
servers in the RackSpace Cloud.

 Always make sure to clean up what you're not using. If it's running, you're
paying for it!
"""

from datetime import datetime

from sys import stdin, exit
from time import sleep
from functools import partial
from pprint import pprint

# NOTE: this file must be created, see testing README.txt for info
from account import RS_UN, RS_KEY

# The __init__ for com.rackspace.cloud.servers.api.client.tests creates a 
# CloudServersServices instance (named `css`) as well as one of each type of 
# manager.  A *lot* has to go right for this to get past this import at all.
from com.rackspace.cloud.servers.api.client.tests import css, serverManager, \
                            flavorManager, imageManager, sharedIpGroupManager

from com.rackspace.cloud.servers.api.client.sharedipgroup import SharedIpGroup
from com.rackspace.cloud.servers.api.client.servermanager import rebootType
from com.rackspace.cloud.servers.api.client.server import Server
from com.rackspace.cloud.servers.api.client.backupschedule \
    import BackupSchedule
from com.rackspace.cloud.servers.api.client.errors import CloudServersFault
from com.rackspace.cloud.servers.api.client.personality import Personality
from com.rackspace.cloud.servers.api.client.file import File

# All utility functions for getting input and such
from com.rackspace.cloud.servers.api.client.tests.console_util import *

#----------------------------------------
# Backup Schedule
#----------------------------------------
def showBackupSchedule():
    """
    Show server's backup schedule.
    """
    id = getServerId()

    # Find is guaranteed not to throw a not-found exception
    server = serverManager.find(id)

    if server:
        schedule = serverManager.getSchedule(server)
        print "Backup schedule of server: ", id
        print schedule
    else:
        print "Server not found"

def setBackupSchedule():
    """
    Set server's backup schedule
    """
    id = getServerId()

    # Find is guaranteed not to throw a not-found exception
    server = serverManager.find(id)

    if server:
        backupSchedule = serverManager.getSchedule(server)
        print "Backup schedule of server: ", id
        print backupSchedule
        newbs = BackupSchedule(True, daily="H_0000_0200", weekly="SUNDAY")
        serverManager.setSchedule(server, newbs)
        backupSchedule = serverManager.getSchedule(server)
        print "Backup schedule of server: ", id
        print backupSchedule
    else:
        print "Server not found"

#----------------------------------------
# Servers
#----------------------------------------
def showStatus():
    """
    Get user input of server ID just show raw status object for that id

    Shows:
        Using find() to check an ID since it will just return None and not
        raise an exception.
    """
    id = getServerId()

    # Find is guaranteed not to throw a not-found exception
    server = serverManager.find(id)

    if server:
        status = serverManager.status(id)
        print "Status of server: ", id
        pprint(status)
    else:
        print "Server not found"

def showDetails():
    """
    Get user input of server ID just show raw status object for that id

    Shows:
        Catching the 404 error by hand instead of using find()
    """
    id = getServerId()
    try:
        server = serverManager.find(id)
    except CloudServersFault, cf:
        if cf.code == 404:
            print "Server not found"
            return

    print "Server: ", server
    pprint(server)
    print "Last Modified: ", server.lastModified

    # test conditional GET
    #i = 0
    #while i < 100:
    #    serverManager.refresh(server)
    #    i += 1

def showImageDetails():
    """
    Get user input of image ID and show details
    """
    id = getImageId()
    try:
        image = imageManager.find(id)
    except CloudServersFault, cf:
        if cf.code == 404:
            print "Server not found"
            return
    print "Image: ", id
    pprint(image)
        

def deleteServer():
    """
    Get user input of server ID and delete it
    """
    id = getServerId()
    serverToDelete = serverManager.find(id)

    if not serverToDelete:  # find() returns None on failure to find server
        print "Server not found %s" % id
    else:
        pprint(serverToDelete)
        status = serverManager.remove(serverToDelete)
        pprint(status)

def rebootServer():
    """
    Reboot a server, prompting for `id`
    """
    id = getServerId()
    serverToReboot = serverManager.find(id)
    if not serverToReboot:  # find() returns None on failure to find server
        print "Server not found %s" % id
        return

    print "Hard or Soft (h/S): "
    hard_soft = stdin.readline().strip()
    if hard_soft in "Hh":
        rType  = rebootType.hard
    else:
        rType = rebootType.soft

    sleepTime = getSleepTime()  # Get sleep time to avoid overlimit fault
    serverManager.reboot(serverToReboot, rType)
    status = serverToReboot.status
    while status != u"ACTIVE":
        status = serverToReboot.status
        print "Status   : ", serverToReboot.status
        print "Progress : ", serverToReboot.progress
        print "Sleeping : ", sleepTime
        sleep(sleepTime)        # pacing to avoid overlimit fault

    print "Rebooted!"

def notifyCallback(isError, entity, fault=None):
    print "we have been notified!"
    print "isError: ", isError
    print "fault: ", fault
    print "entity: ", entity

def createServer():
    """
    Creates a server with entered name, then shows how to poll for it
    to be created.
    """
    print "Server Name to Create: "
    name = stdin.readline().strip()
    s = Server(name=name, imageId=3, flavorId=1)
    # Create doesn't return anything, but fills in the server with info
    # (including) admin p/w
    serverManager.create(s)
    serverManager.notify(s, notifyCallback)
    pprint(s)
    print "Server is now: ", s # show the server with all values filled in

    # sleepTime = getSleepTime()
    # status = s.status
    # while status == "BUILD":
    #     status = s.status
    #     # print "Status   : ", s.status
    #     print "Progress : ", s.progress
    #     # print "Sleeping : ", sleepTime
    #     # sleep(sleepTime)

    print "Built!"

def createServerAndWait():
    """
    Creates a server with entered name, then uses the wait() method to poll 
    for it to be created.
    """
    print "Server Name to Create: "
    name = stdin.readline().strip()
    s = Server(name=name, imageId=3, flavorId=1)
    # Create doesn't return anything, but fills in the server with info
    # (including) admin p/w
    serverManager.create(s)
    pprint(s)
    print "Server is now: ", s # show the server with all values filled in
    serverManager.wait(s)

    print "Built!"

def resizeServer():
    """
    Resizes a server and asks you to confirm the resize.
    """
    id = getServerId()

    # Find is guaranteed not to throw a not-found exception
    server = serverManager.find(id)
    if server:
        print "Server: ", server
    else:
        print "Server not found"
        
    flavorId = 2    
    if server.flavorId == 2:
        flavorId = 1
    
    print "Resizing to Flavor ID ", flavorId
    serverManager.resize(server, flavorId)
    serverManager.wait(server)
    
    print "Done!  Ready to confirm or revert?\
           Type confirm or revert or press enter to do nothing:"
    action = stdin.readline().strip()
    
    if action == 'confirm':
        serverManager.confirmResize(server)
        serverManager.wait(server)
    elif action == 'revert':
        serverManager.revertResize(server)
        serverManager.wait(server)
        
    print "Done!"
    print "Server: ", server

#----------------------------------------
# Shared IP Groups
#----------------------------------------
def createSharedIpGroup():
    """
    Creates a shared IP group with entered name and single server id.

    Shows:
        how to poll while waiting for a server to be created.
    """
    print "Shared IP Group Name to Create: "
    name = stdin.readline().strip()

    print "Id of first server in group: "
    server = None
    found = False
    id = 0
    while not found and id != -1:
        id = getServerId()
        server = serverManager.find(id)
        found = (server != None)

    if found:
        ipg = SharedIpGroup(name, server.id )
        # Create doesn't return anything, but fills in the ipgroup with info
        sharedIpGroupManager.create(ipg)
        print "IP group is now:"
        pprint(ipg)

def deleteSharedIpGroup():
    """
    Delete a shared ip group by id
    """
    print "Shared IP Group id to delete: "
    name = getSharedIpGroupId()
    ipg = sharedIpGroupManager.find(name)
    if not ipg:
        print "IP Group not found"
    else:
        sharedIpGroupManager.remove(ipg)

def addServerToIpGroup():
    """
    Add server to IP Group by id
    """
    serverId = getServerId()
    server = serverManager.find(serverId)
    print "server: ", server
    sharedIpGroupId = getSharedIpGroupId()
    sharedIpGroup = sharedIpGroupManager.find(sharedIpGroupId)
    print "shared ip group: ", sharedIpGroup
    ipAddress = getIpAddress()
    serverManager.shareIp(server, ipAddress, sharedIpGroupId, True)
    pass

def testEntityListIter():
    """
    Test EntityList iterator methods
    """
    serverList = serverManager.createList(detail=False)
    expected_length = len(serverList)

    # test python iterator
    actual_length = 0
    for server in serverList:
        actual_length += 1
    print "testing 'for server in serverList': ", \
            'PASS' if actual_length == expected_length else ''

    # test hasNext() and next()
    actual_length = 0
    serverList = serverManager.createList(detail=False)
    while serverList.hasNext():
        serverList.next()
        actual_length += 1
    print "testing hasNext() and next():       ", \
            'PASS' if actual_length == expected_length else 'FAIL'

    # test reset()
    actual_length = 0
    serverList.reset()
    for server in serverList:
        actual_length += 1
    print "testing reset():                    ", \
            'PASS' if actual_length == expected_length else 'FAIL'
    
def testServerDeltaList():
    datestr = datetime.now().strftime('%s')
    print "To see anything listed, change a server"
    deltaList = serverManager.createDeltaList(True, changes_since=datestr)
    print "deltaList since ", datestr, ": "
    for item in deltaList:
        print item.id, " - ", item.name

def testFaultGeneration():
    try:
        print "Expecting an ItemNotFoundFault..."
        serverManager._cloudServersService.GET('blah', {})
    except Exception as e:
        print "Exception type: ", e.__class__
        print "Exception content: ", e
    
def testPersonality():
    s = Server(name="test", imageId=3, flavorId=1)
    p = Personality()
    f1 = File('/usr/local/personality1', \
              'this is a test.  if it is legible, the test failed')
    f2 = File('/usr/local/personality2', \
              'this is another test.  if it is legible, the test failed')
    p.files = [f1, f2]
    s.personality = p
    print "personality: ", s.personality
    print "files:"
    for file in p.files:
        print file.path, ' ', file.contents
    print "personality in server object:"
    print s.asJSON
    print "no personality in server object:"
    s.personality = None
    print s.asJSON

def waitOnFlavor():
    flavorId = getFlavorId()
    flavor = flavorManager.find(flavorId)
    print "flavor: ", flavor
    flavorManager.wait(flavor)

def waitOnSharedIpGroup():
    sharedIpGroupId = getSharedIpGroupId()
    sharedIpGroup = sharedIpGroupManager.find(sharedIpGroupId)
    print "Shared IP Group: ", sharedIpGroup
    sharedIpGroupManager.wait(sharedIpGroup)

####
# Notify tests
####

def simpleNotify(isError, entity, fault=None):
    print "notified!"

def _testNotify(entityId, entityManager):
    
    # first, we get the entity to run the notify call on.  we need a real one 
    # because notify will actually refresh via the API as well
    entity = entityManager.find(entityId)
    entityManager.notify(entity, simpleNotify)

    # all entities have a name, so let's use that to trigger the notify event
    dic = { 'name': 'test1', 'id': entityId }
    if entity.name == dic['name']:
        dic['name'] = 'test2' # in case the entity happened to be named test1
    entity.initFromResultDict(dic)

    sleep(2) # sleeping to catch any extra notify events that shouldn't happen
    
    entityManager.stopNotify(entity, simpleNotify)

def testServerNotify():
    serverId = getServerId()
    _testNotify(serverId, serverManager)
    
def testImageNotify():
    # imageId = getImageId()
    imageId = 3
    _testNotify(imageId, imageManager)

def testFlavorNotify():
    # flavorId = getFlavorId()
    flavorId = 1
    _testNotify(flavorId, flavorManager)

def testSharedIpGroupNotify():
    sharedIpGroupId = getSharedIpGroupId()
    _testNotify(sharedIpGroupId, sharedIpGroupManager)

choices = dict()                    # just so it's there for beatIt decl

#
# Ok, I could probably reduce this further with generators, fibrilators, etc.
# but this'll do the job and is easy enough to understand.
#
ls   = partial(lister, manager=serverManager, tag="Server")
lf   = partial(lister, manager=flavorManager, tag="Flavor")
li   = partial(lister, manager=imageManager, tag="Image")

# TODO: lists in an infinite loop
lsip = partial(lister, manager=sharedIpGroupManager, tag="SharedIP")

# TBD:
# Store this as array, do lookup with dict

shortLineLen = 40
longLineLen = 60
sepLine = '-' * shortLineLen

def groupHeader(groupName):
    groupLen = len(groupName)
    numDashes = (longLineLen - groupLen)  / 2
    return '\n' + '-' * numDashes + ' ' + groupName + ' ' + '-' * numDashes

choicesList = (
    (groupHeader("Servers"),),
    ("ls"       , ChoiceItem("List Servers",            lambda: ls(False))  ),
    ("lsd"      , ChoiceItem("List Servers Detail",     lambda: ls(True))   ),
    ("sdelta"   , ChoiceItem("Servers Delta List",      testServerDeltaList)),
    (sepLine,),
    ("ss"       , ChoiceItem("Show Server's Status by id", showStatus)),
    ("sd"       , ChoiceItem("Show Server's Details by id", showDetails)),
    (sepLine,),
    ("sc"       , ChoiceItem("Create Server",           createServer)),
    ("scw"      , ChoiceItem("Create Server and wait",  createServerAndWait)),
    ("sdel"     , ChoiceItem("Delete Server by id",     deleteServer)),
    ("sr"       , ChoiceItem("Reboot Server by id",     rebootServer)),
    ("sresize"  , ChoiceItem("Resize Server by id",     resizeServer)),
    (sepLine,),
    ("sbs"      , ChoiceItem("Show Server's Backup Schedule by id", \
                                                        showBackupSchedule)),
    ("sbsup"    , ChoiceItem("Update Server's Backup Schedule by id", \
                                                        setBackupSchedule)),

    (groupHeader("Flavors, Images"),),
    ("lf"       , ChoiceItem("List Flavors",            lambda: lf(False))  ),
    ("lfd"      , ChoiceItem("List Flavors (detail)",   lambda: lf(True))   ),
    (sepLine,),
    ("li"       , ChoiceItem("List Images",             lambda: li(False))  ),
    ("lid"      , ChoiceItem("List Images (detail)",    lambda: li(True))   ),
    ("lidid"    , ChoiceItem("List Image Details by id", showImageDetails)   ),
    ("fwait"    , ChoiceItem("Wait on a Flavor by id",   waitOnFlavor)       ),

    (groupHeader("Shared IP Groups"),),
    ("lip"      , ChoiceItem("List Shared IP Groups",   lambda: lsip(False))),
    ("lipd"     , ChoiceItem("List Shared IP Groups (detail)", \
                                                        lambda: lsip(True)) ),
    ("sipc"     , ChoiceItem("Create Shared IP Group",  createSharedIpGroup)),
    ("sipdel"   , ChoiceItem("Delete Shared IP Group",  deleteSharedIpGroup)),
    ("sipadd"   , ChoiceItem("Add Server to Shared IP Group by id", \
                                                        addServerToIpGroup) ),
    ("ipwait"   , ChoiceItem("Wait on a Shared IP Group by id", \
                                                        waitOnSharedIpGroup)),

    (groupHeader("Misc Account Functions"),),
    ("ll"       , ChoiceItem("List Account Limits",     showLimits)         ),

    (groupHeader("Misc Functions"),),
    ("iter"     , ChoiceItem("Test EntityList iterator", testEntityListIter)),
    ("pers"     , ChoiceItem("Server Personality get/set", testPersonality)),
    ("fault"    , ChoiceItem("Test Fault Parser",       testFaultGeneration)),

    (groupHeader("Notifiers"),),
    ("notifyserver", ChoiceItem("Test ServerManager.notify()", \
                                                            testServerNotify)),
    ("notifyimage",  ChoiceItem("Test ImageManager.notify()", \
                                                            testImageNotify)),
    ("notifyflavor", ChoiceItem("Test FlavorManager.notify()", \
                                                            testFlavorNotify)),
    ("notifysip",    ChoiceItem("Test SharedIpGroupManager.notify()", \
                                                    testSharedIpGroupNotify)),
    

    (groupHeader("Quit"),),
    ("q"        , ChoiceItem("quit",                    lambda: exit(0))    ),
    (sepLine,),
)

#
# Create dictionary for lookups
#
lookupDict = dict()
for choice in choicesList:
    if not '-' in choice[0]:        # skip our separators
        lookupDict[choice[0]] = choice[1]

#
# Get input from user, execute selected function
#   until interrupted by 'q' or Ctrl-C
#
slcu = "Servers Listing Console Utility"

choice = ""
while 1:
    if choice in lookupDict:
        lookupDict[choice].func()
    else:
        printChoices(choicesList)

    choice = raw_input("Command (enter to show menu...)")

    if choice == "q":
        print "Bye!"
        exit(0)

########NEW FILE########
__FILENAME__ = console_util
#----------------------------------------------------------------------------
# console_util.py
#
# A very simple set of utilities for creating text menu based applications for
# simple manual testing.
#
# Developed to assist with the *_console.py test programs that are in the
# test directory but not really part of the "Test Suite" per se.
#----------------------------------------------------------------------------

from sys import stdin, exit
from functools import partial

# The __init__ for com.rackspace.cloud.servers.api.client.tests creates a 
# CloudServersServices instance (named `css`) as well as one of each type of 
# manager.  A *lot* has to go right for this to get past this import at all.
from com.rackspace.cloud.servers.api.client.tests import css, serverManager, \
                            flavorManager, imageManager, sharedIpGroupManager

#
# Choices for our fancy menu system
#
class ChoiceItem(object):
    """
    A prompt and a function to call
    """
    def __init__(self, prompt, func):
        """
        Create a choiceItem
        """
        self.prompt = prompt
        self.func = func

def getId(idType, showId=True):
    if showId == True:
        print idType + " ID: "
    else:
        print idType + ": "
    id = stdin.readline().strip()
    if id == "":    # If they leave it blank, just bail returning -1
        return -1

    # don't mind if it's not numeric
    # try:
    #     id = int(id)
    # except ValueError, e:
    #     print "ValueError : ", e
    #     id = -1
    return id
    
def getServerId():
    return getId("Server")

def getImageId():
    return getId("Image")

def getFlavorId():
    return getId("Flavor")
    
def getSharedIpGroupId():
    return getId("Shared IP Group")

def getIpAddress():
    return getId("IP Address", showId=False)

def printChoices(choices):
    """
    Print all of the choices, one per line, nicely formatted
    """
    for c in choices:
        # Print the whole thing if it's not a separator, else print separator
        if not '-' in c[0]:
            print "%-8s - %s" % (c[0], c[1].prompt)
        else:
            print c[0]

def getSleepTime():
    """
    Computes sleep time for polling operations
    """

    # Now, get the limits for our account to pace our "busy waiting"
    limits = css.serviceInfoLimits
    print "Limits are: ", limits

    queriesRateRecord =  limits["rate"][1]        
    queriesPerMinute = queriesRateRecord["value"] 

    sleepTime = 60/queriesPerMinute

    return sleepTime

#
# Generic Lister
#
def lister(detail, manager, tag):
    """
    List using:
        `manager`   manager to use to create the list
        `tag`       string to show what's being listed
        `detail`    whether to show detail or not
    """
    theList = (manager).createList(detail)
    
    print "%s List of %ss" %(detail and "Detailed" or "Quick", tag)
    
    print "List length: ", len(theList)
    
    for item in theList:
        print "id=%s" % (item.id,)
        if detail:
            print repr(item)
        else:
            print str(item)

        print

def showLimits():
    """
    Just show account limits
    """
    limits = css.serviceInfo.limits
    print limits

def notimp():
    print "Not implemented, yet..."


########NEW FILE########
__FILENAME__ = printdoc
# Copyright (c) 2010, Rackspace.
# See COPYING for details.

"""
printdoc decorator, prints module's docstring (used for tests)
"""
from sys import stdout

def printdoc(f):
    """
    printdoc decorator, prints out func's docstring, returns unmodified func
    """
    if f.__doc__:
        stdout.write('\n')

        testname = "[ %s ]" % f.__name__
        testname = testname.center(74) + '\n'
        stdout.write(testname)

        stdout.write('  ' + (74 * "~") + '\n')

        words = list()
        for l in f.__doc__.splitlines(): words += l.split()

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
__FILENAME__ = test_authentication
import unittest

from nose import SkipTest
from nose.tools import assert_raises

from com.rackspace.cloud.servers.api.client.errors import AuthenticationFailed
from com.rackspace.cloud.servers.api.client.authentication \
    import Authentication

class TestBaseAuthentication(unittest.TestCase):
    # NOTE: This class is never instantiated, no tests necessary
    def test___init__(self):
        # base_authentication = BaseAuthentication(username, api_key, authurl)
        pass # Base class, not called

    def test_authenticate(self):
        # base_authentication = BaseAuthentication(username, api_key, authurl)
        # self.assertEqual(expected, base_authentication.authenticate())
        pass # Base class, not called

class TestAuthentication(unittest.TestCase):
    def test_authenticate(self):
        # authentication = Authentication()
        # self.assertEqual(expected, authentication.authenticate())
        # Get the computeURL and authToken to use for subsequent queries
        auth = Authentication("badname", "really bad key")
        assert_raises(AuthenticationFailed,auth.authenticate)

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_conditional_get
import unittest
from nose import SkipTest

# I'll give it a shot.
#
# Here's the test case:
#
#   Get a list of servers at time X.
#
#  An If-modified-Since X should return a 304, not modified response.
#
#  Create a new server.
#
#  Wait until it is built.
#
#  Mark time Y.
#
#  Build another server, wait until it is built.
#
#  Mark time Z.
#
# A conditional get on any value between X and Y should return both new 
# servers.
#
# A conditional get on Z or greater should just the one new server.
#
# A conditional get on any time after Y should return 304, not modified.
#
# Is there anything else that should be added to the test case?
#
# Thanks,
#
#
class TestConditionalGet(unittest.TestCase):
    pass

########NEW FILE########
__FILENAME__ = test_entitylist
import unittest
from nose import SkipTest
from nose.tools import assert_equal, assert_true, assert_false

from com.rackspace.cloud.servers.api.client.entitylist import EntityList
from com.rackspace.cloud.servers.api.client.errors import InvalidInitialization

def setupModule(module):
    pass

class TestEntityList(unittest.TestCase):

    def test___init__(self):
        self.assertRaises(InvalidInitialization, EntityList, None, True, None)
        self.assertRaises(InvalidInitialization, EntityList, "not a list", \
                          True, None)
        self.assertRaises(InvalidInitialization, EntityList, {"also":None, \
                          "not a list":None}, True, None)

    def test___iter__(self):
        # entity_list = EntityList(data)
        # self.assertEqual(expected, entity_list.__iter__())
        pass # TODO: implement your test here

    def test_delta(self):
        # entity_list = EntityList(data)
        # self.assertEqual(expected, entity_list.delta())
        pass # TODO: implement your test here

    def test_isEmpty(self):
        el1 = EntityList(["some", "data"],True,None)
        el2 = EntityList([],True,None)
        assert_false(el1.isEmpty())
        assert_true(el2.isEmpty())

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_entitymanager
import unittest
from nose import SkipTest
from com.rackspace.cloud.servers.api.client.errors \
    import MustBeOverriddenByChildClass
from com.rackspace.cloud.servers.api.client.entitymanager import EntityManager

class TestEntityManager(unittest.TestCase):
    def test___init__(self):
        # entity_manager = EntityManager(cloudServersService, requestPrefix, \
        #                                responseKey)
        pass # Not instantiated directly

    def test_create(self):
        #entity_manager = EntityManager(cloudServersService, requestPrefix, \
        #                               responseKey)
        ## self.assertEqual(expected, entity_manager.create(entity))
        #self.assertRaises( MustBeOverriddenByChildClass, enti )
        pass    # TBD: should check for MustBeOverriddenByChildClass as above

    def test_createDeltaList(self):
        # entity_manager = EntityManager(cloudServersService, requestPrefix, \
        #                                responseKey)
        # self.assertEqual(expected, entity_manager.createDeltaList(detail, \
        #                  changes_since))
        pass # Not called directly

    def test_createDeltaListP(self):
        # entity_manager = EntityManager(cloudServersService, requestPrefix, \
        #                                responseKey)
        # self.assertEqual(expected, entity_manager.createDeltaListP(detail, \
        #                  changes_since, offset, limit))
        pass # Not called directly

    def test_createList(self):
        # entity_manager = EntityManager(cloudServersService, requestPrefix, \
        #                                responseKey)
        # self.assertEqual(expected, entity_manager.createList(detail))
        pass # Not called directly

    def test_createListP(self):
        # entity_manager = EntityManager(cloudServersService, requestPrefix, \
        #                                responseKey)
        # self.assertEqual(expected, entity_manager.createListP(detail, \
        #                  offset, limit))
        pass # Not called directly

    def test_find(self):
        # entity_manager = EntityManager(cloudServersService, requestPrefix, \
        #                                responseKey)
        # self.assertEqual(expected, entity_manager.find(id))
        pass # Not called directly

    def test_notify(self):
        # entity_manager = EntityManager(cloudServersService, requestPrefix, \
        #                                responseKey)
        # self.assertEqual(expected, entity_manager.notify(entity, \
        #                  changeListener))
        pass # Not called directly

    def test_refresh(self):
        # entity_manager = EntityManager(cloudServersService, requestPrefix, \
        #                                responseKey)
        # self.assertEqual(expected, entity_manager.refresh(entity))
        pass # Not called directly

    def test_remove(self):
        # entity_manager = EntityManager(cloudServersService, requestPrefix, \
        #                                responseKey)
        # self.assertEqual(expected, entity_manager.remove(entity))
        pass # Not called directly

    def test_stopNotify(self):
        # entity_manager = EntityManager(cloudServersService, requestPrefix, \
        #                                responseKey)
        # self.assertEqual(expected, entity_manager.stopNotify(entity, \
        #                  changeListener))
        pass # Not called directly

    def test_update(self):
        # entity_manager = EntityManager(cloudServersService, requestPrefix, \
        #                                responseKey)
        # self.assertEqual(expected, entity_manager.update(entity))
        pass # Not called directly

    def test_wait(self):
        # entity_manager = EntityManager(cloudServersService, requestPrefix, \
        #                                responseKey)
        # self.assertEqual(expected, entity_manager.wait(entity))
        pass # Not called directly

    def test_waitT(self):
        # entity_manager = EntityManager(cloudServersService, requestPrefix, \
        #                                responseKey)
        # self.assertEqual(expected, entity_manager.waitT(entity, timeout))
        pass # Not called directly

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_flavor
import unittest
from nose import SkipTest

from com.rackspace.cloud.servers.api.client.flavor import Flavor
from com.rackspace.cloud.servers.api.client.errors import BadMethodFault

class TestFlavor(unittest.TestCase):
    def test___init__(self):
        # flavor = Flavor(name)
        f = Flavor("dog")
        self.assertEqual(f.name, "dog")
        f = Flavor(None)
        self.assertEqual(f.name, None)

    def test_initFromResultDict(self):
        # flavor = Flavor(name)
        # self.assertEqual(expected, flavor.initFromResultDict(dic))
        f = Flavor("fido")
        f.initFromResultDict({'disk': 10, 'id': 1, 'ram': 256, \
                              'name': u'256 server'})
        self.assertEqual(f.disk,10)
        self.assertEqual(f.id,1)
        self.assertEqual(f.ram,256)
        self.assertEqual(f.name, u'256 server')

    def test_initFromNoneDict(self):
        f = Flavor("Name")
        f2 = Flavor("Name")
        f.initFromResultDict(None)
        f2.initFromResultDict(None)

    def test_equality(self):
        f = Flavor("Name")
        self.assertEqual(f.name, "Name")
        self.assertEqual(f.disk,None)
        self.assertEqual(f.id,None)
        self.assertEqual(f.ram,None)

        f2 = Flavor("Name")
        self.assertEqual(f, f2)
        f2.initFromResultDict({'disk':10})
        self.assertNotEqual(f2, f)

    def test_repr(self):
        f = Flavor("Snoopy")
        f.initFromResultDict({'disk': 10, 'id': 1, 'ram': 256, \
                              'name': u'256 server'})
        rep = f.__repr__()        # Just to make it happen for coverage

    def test_extra_attr(self):
        f = Flavor("Name")
        self.assertEqual(f.name, "Name")
        f2 = Flavor("Name")
        self.assertEqual(f, f2)
        f.dog = "woof"
        self.assertNotEqual(f, f2)

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_flavormanager
import unittest
from nose import SkipTest

from com.rackspace.cloud.servers.api.client.flavormanager import FlavorManager
import com.rackspace.cloud.servers.api.client.tests as cst
from com.rackspace.cloud.servers.api.client.errors import BadMethodFault

class TestFlavorManager(unittest.TestCase):
    def test___init__(self):
        # flavor_manager = FlavorManager(cloudServersService)
        pass    # Will get tested by other tests

    def test_bad_methods(self):
        f = cst.flavorManager
        self.assertRaises(BadMethodFault, f.create, None  )
        self.assertRaises(BadMethodFault, f.remove, None )
        self.assertRaises(BadMethodFault, f.update, None )
        self.assertRaises(BadMethodFault, f.refresh, None )
        self.assertRaises(BadMethodFault, f.wait, None )
        self.assertRaises(BadMethodFault, f.waitT, None, None )
        self.assertRaises(BadMethodFault, f.notify, None, None )
        self.assertRaises(BadMethodFault, f.stopNotify, None, None )

    def test_createEntityListFromResponse(self):
        # flavor_manager = FlavorManager(cloudServersService)
        # self.assertEqual(expected, \
        #               flavor_manager.createEntityListFromResponse(response))
        pass # TODO: implement your test here

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_image
import unittest
from nose import SkipTest
from nose.tools import assert_equal
from com.rackspace.cloud.servers.api.client.image import Image

class TestImage(unittest.TestCase):
    def test___init__(self):
        # flavor = Image(name)
        f = Image("dog")
        self.assertEqual(f.name, "dog")
        f = Image(None)
        self.assertEqual(f.name, None)

    def test_initFromResultDict(self):
        # flavor = Image(name)
        # self.assertEqual(expected, flavor.initFromResultDict(dic))
        f = Image("fido")
        f.initFromResultDict({'updated': "whatever", 'id': 1, \
                              'created': "whenever", 'status': 'stateriffic', \
                              'progress':'progresseriffic'})
        self.assertEqual(f.updated,"whatever")
        self.assertEqual(f.id,1)
        self.assertEqual(f.created,"whenever")
        self.assertEqual(f.status, 'stateriffic')
        self.assertEqual(f.progress, 'progresseriffic')

    def test_initFromNoneDict(self):
        f = Image("Name")
        f.initFromResultDict(None)
        self.assertEqual(f.name, "Name")
        self.assertEqual(f.updated,None)
        self.assertEqual(f.id,None)
        self.assertEqual(f.created,None)
        self.assertEqual(f.status,None)
        self.assertEqual(f.progress,None)

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_imagemanager
import unittest
from nose import SkipTest
from nose.tools import assert_equal

import com.rackspace.cloud.servers.api.client.tests as cst
from com.rackspace.cloud.servers.api.client.errors import BadMethodFault

class TestImageManager(unittest.TestCase):
    def test___init__(self):
        # image_manager = ImageManager(cloudServersService)
        raise  SkipTest # TODO: implement your test here

    def test_bad_methods(self):
        f = cst.imageManager
        self.assertRaises(BadMethodFault, f.create, None  )
        self.assertRaises(BadMethodFault, f.remove, None )
        self.assertRaises(BadMethodFault, f.update, None )
        self.assertRaises(BadMethodFault, f.refresh, None )
        self.assertRaises(BadMethodFault, f.wait, None )
        self.assertRaises(BadMethodFault, f.waitT, None, None )
        self.assertRaises(BadMethodFault, f.notify, None, None )
        self.assertRaises(BadMethodFault, f.stopNotify, None, None )

    def test_createEntityListFromResponse(self):
        # image_manager = ImageManager(cloudServersService)
        # self.assertEqual(expected, \
        #               image_manager.createEntityListFromResponse(response))
        raise  SkipTest # TODO: implement your test here

    def test_find(self):
        # image_manager = ImageManager(cloudServersService)
        # self.assertEqual(expected, image_manager.find(id))
        raise  SkipTest # TODO: implement your test here

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_limits

import unittest
from nose import SkipTest

from com.rackspace.cloud.servers.api.client.tests import css, flavorManager, \
                                                         imageManager

fm = flavorManager
im = imageManager

from functools import partial
getFList = partial(fm.createListP, True)
getIList = partial(im.createListP, True)

class TestLimits(unittest.TestCase):
    """
    Test getting offset/limit sets by pulling out top and bottom pairs using
    the limit and offset parameters and comparing the results against slices
    out of the full list obtained without limit and offset pairs i.e. the
    whole list.
    """
    fullFList = None
    fullIList = None

    @classmethod
    def setUp(cls):
        """
        Get the full list of flavors against which to compare.
        """
        cls.fullFList = fm.createList(detail=True)
        cls.fullIList = im.createList(detail=True)

    def test_getBottomTwoFlavors(self):
        bottomTwo = getFList(0, 2)
        flBottomTwo = TestLimits.fullFList[:2]
        self.assertEqual(bottomTwo, flBottomTwo)

    def test_topTwoFlavors(self):
        top = len(TestLimits.fullFList) - 2  # get top 2
        topTwo = getFList(top, 2)
        fullListTopTwo = TestLimits.fullFList[-2:] # slice off top 2
        self.assertEqual(topTwo, fullListTopTwo)

    def test_getBottomTwoImages(self):
        bottomTwo = getIList(0, 2)
        ilBottomTwo = TestLimits.fullIList[:2]
        self.assertEqual(bottomTwo, ilBottomTwo)

    def test_topTwoImages(self):
        top = len(TestLimits.fullIList) - 2  # get top 2
        topTwo = getIList(top, 2)
        fullListTopTwo = TestLimits.fullIList[-2:] # slice off top 2
        self.assertEqual(topTwo, fullListTopTwo)

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_server_class
# Copyright (c) 2010, Rackspace.
# See COPYING for details.

"""
Test Server object.  These tests just test the internals of the class itself, 
not the use thereof.
"""

from com.rackspace.cloud.servers.api.client.server import Server
from com.rackspace.cloud.servers.api.client.jsonwrapper import json

from com.rackspace.cloud.servers.api.client.tests.unittest_wrapper \
    import unittest

from com.rackspace.cloud.servers.api.client.tests.shared.printdoc \
    import printdoc

from com.rackspace.cloud.servers.api.client.tests import css, sm, im, fm, sipgm

class ServerClassTestCase(unittest.TestCase):
    """
    Tests server object internals.
    """
    def setUp(self):
        """Create a couple of server objects to play with"""
        self.server0 = Server(name="TestServer0", imageId=1, flavorId=2, \
                    metadata={"meta1":"0meta1 value", "meta2":"0meta2 value"})
        self.server1 = Server(name="TestServer1", imageId=2, flavorId=3)

    def tearDown(self):
        del self.server0
        del self.server1

    @printdoc
    def test_server0(self):
        """Test values of self.server0"""
        s = self.server0    # typing shorthand
        assert s.name == "TestServer0"
        assert s.imageId == 1
        assert s.flavorId == 2
        assert s.metadata["meta1"] == "0meta1 value"
        assert s.metadata["meta2"] == "0meta2 value"

    @printdoc
    def test_readonly(self):
        """
        Verify that Server properties are readonly.
        NOTE: name is mutable unless the Server is attached
              to a ServerManager.
        """
        awbb = "Anything Would Be Bad"
        def _test_set_imageId(o):
            o.imageId = awbb

        def _test_set_flavorId(o):
            o.flavorId = awbb

        def _test_set_metadata(o):
            o.metadata = awbb

        x = AttributeError  # typing shorthand
        self.assertRaises(x, _test_set_flavorId, self.server0)
        self.assertRaises(x, _test_set_imageId,  self.server0)
        self.assertRaises(x, _test_set_metadata, self.server0)

    @printdoc
    def test_asJSON(self):
        """
        Test JSON conversion of servers with and without metadata.
        """
        srvr0Dict = {"server":
                        {
                            "name"      : "TestServer0",
                            "imageId"   : 1,
                            "flavorId"  : 2,
                            "metadata"  : {"meta1":"0meta1 value",
                                           "meta2":"0meta2 value"}
                        }
                    }
        srvr0Json = json.dumps(srvr0Dict)
        self.assertEqual(self.server0.asJSON, srvr0Json)

        srvr1Dict = {"server":
                        {
                            "name"      : "TestServer1",
                            "imageId"   : 2,
                            "flavorId"  : 3,
                            "metadata"  : None
                        }
                    }
        srvr1Json = json.dumps(srvr1Dict)
        self.assertEqual(self.server1.asJSON, srvr1Json)

if __name__ == "__main__":
    unittest.main()

########NEW FILE########
__FILENAME__ = test_util
# Copyright (c) 2010, Rackspace.
# See COPYING for details.


"""
Tests for utility functions
"""

import unittest

from com.rackspace.cloud.servers.api.client.shared.utils \
    import build_url, parse_url, find_in_list
from com.rackspace.cloud.servers.api.client.errors import InvalidUrl
from com.rackspace.cloud.servers.api.client.consts \
    import get_version, __version__
from com.rackspace.cloud.servers.api.client.version \
    import get_version as csv_get_version

class TestConsts(unittest.TestCase):
    """
    Test consts module
    """
    def testVersion(self):
        self.assertEqual(get_version(), __version__)
        self.assertEqual(get_version(), csv_get_version())

    def test_version_params(self):
        """
        Test permutations of parameters to get_version()
        """
        a = csv_get_version(True)
        b = csv_get_version(False)
        c = csv_get_version(True, False)
        d = csv_get_version(True, True)
        e = csv_get_version(False, False)
        f = csv_get_version(False, True)
        return

class TestUtilities(unittest.TestCase):
    """
    Test utility functions
    """
    def test_build_url(self):
        tiat = "this/is/a/test"
        urls =  [
                    # Simple list of params
                    (1,
                        (
                            "this", "is", "a", "test"
                        )
                    ),

                    # leading and trailing '/'
                    (2,
                        (
                        "////this///", "////is///",
                        "//////a/////", "///////test//////"
                        )
                    ),

                    # sequence + string
                    (3,
                        (
                            ("this", "is", "a"),
                            "test"
                        )
                    ),

                    # whitespace
                    (4,
                        (
                        "  this  ", "\r\nis  \r\n",
                        "\t\r\n a\r\n\t", "    test    "
                        )
                    ),
                ]

        for tn, param in urls:
            tr = build_url(param)
            self.assertEqual(tiat, tr)

            tr = build_url(*param)
            self.assertEqual(tiat, tr)

    def test_build_url_with_numbers(self):
        rslt = "123/456/abc/hithere"
        urls=[
                (1,
                    (
                    123, 456, "abc", "hithere"
                    )
                ),
                (2,
                    (
                    "123",456, "abc", "hithere"
                    )
                ),
                (3,
                    (
                    123,"456", "abc", "hithere"
                    )
                ),
                (4,
                    (
                    "123","456", "abc", "hithere"
                    )
                ),
            ]
        for tn, param in urls:
            tr = build_url(param)
            self.assertEqual(rslt, tr)

            tr = build_url(*param)
            self.assertEqual(rslt, tr)

    def test_parse_url(self):
        self.assertRaises(InvalidUrl, parse_url, \
                          "bad://doggie.not.valid.url.scheme")
        self.assertRaises(InvalidUrl, parse_url, "http://%%")

    def test_find_in_list(self):
        hl = [
                ('content-length', '18031'),
                ('accept-ranges', 'bytes'),
                ('server', 'Apache/2.2.9 (Debian) DAV/2 SVN/1.5.1 mod_ssl/2.2.9 OpenSSL/0.9.8g mod_wsgi/2.5 Python/2.5.2'),
                ('last-modified', 'Fri, 27 Nov 2009 22:03:14 GMT'),
                ('etag', '"105800d-466f-479617552ec80"'),
                ('date', 'Sat, 28 Nov 2009 02:03:43 GMT'),
                ('content-type', 'text/html'),
             ]
        last_modified = find_in_list(hl,"last-modified", 0, 1)
        self.assertEqual(last_modified, 'Fri, 27 Nov 2009 22:03:14 GMT')
        content_type = find_in_list(hl,"content-type", 0, 1)
        self.assertEqual(content_type, 'text/html')
        notThere = find_in_list(hl, "BADKEY", 0, 1)
        self.assertEqual(notThere, None)

if __name__ == "__main__":
    unittest.main()

########NEW FILE########
__FILENAME__ = unittest_wrapper
# Copyright (c) 2010, Rackspace.
# See COPYING for details.



"""
Just wraps import of unittest in case we want to use e.g. Twisted's, if it's
available, or regular unittest otherwise.
"""

__all__ = []

# Was using twisted, removed
#try:
#    from twisted.trial import unittest as ut
#    import unittest as regular_unittest
#    # workaround for twisted.trial's lack of main()
#    ut.main = regular_unittest.main 
#except ImportError:
#    import unittest as ut

import unittest

########NEW FILE########
__FILENAME__ = version
# -*- test-case-name: com.rackspace.cloud.servers.api.client.tests.test_version -*-

# Copyright (c) 2010, Rackspace.
# See COPYING for details.


"""
Current Cloud Servers version constant plus version pretty-print method.

This functionality is contained in its own module to prevent circular import
problems with ``__init__.py`` (which is loaded by setup.py during 
installation, which in turn needs access to this version information.)

This code was lifted from Fabric (http://fabfile.org) which borrowed it from
Django.
"""

VERSION = (0, 9, 0, 'alpha', 0)

def get_version(verbose=False, line_only=False):
    """
    Return a version string for this package, based on `VERSION`.

    When ``verbose`` is False (the default), `get_version` prints a
    tag-friendly version of the string, e.g. '0.9a2'.

    When ``verbose`` is True, a slightly more human-readable version is
    produced, e.g. '0.9 alpha 2'.

    When ``line_only`` is True, only the major and minor version numbers are
    returned, e.g. '0.9'.

    This code is based off of Django's similar version output algorithm.
    """
    # Major + minor only
    version = '%s.%s' % (VERSION[0], VERSION[1])
    # Break off now if we only want the line of development
    if line_only:
        return version
    # Append tertiary/patch if non-zero
    if VERSION[2]:
        version = '%s.%s' % (version, VERSION[2])
    # Append alpha/beta modifier if not a final release
    if VERSION[3] != 'final':
        # If non-verbose, just the first letter of the modifier, no spaces.
        if not verbose:
            version = '%s%s%s' % (version, VERSION[3][0], VERSION[4])
        # Otherwise, be more generous.
        else:
            version = '%s %s %s' % (version, VERSION[3], VERSION[4])
    # If it is final, and we're being verbose, also tack on the 'final'.
    elif verbose:
        version = '%s %s' % (version, VERSION[3])

    return version

__version__ = get_version()


########NEW FILE########
