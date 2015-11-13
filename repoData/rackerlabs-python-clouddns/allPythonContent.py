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
from consts   import user_agent, us_authurl, dns_management_host
from sys      import version_info


class BaseAuthentication(object):
    """
    The base authentication class from which all others inherit.
    """
    def __init__(self, username, api_key, authurl=us_authurl,
                 dns_management_host=dns_management_host,
                 timeout=5,
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

        for hdr in response.getheaders():
            if hdr[0].lower() == "x-auth-token":
                auth_token = hdr[1]
            if hdr[0].lower() == "x-server-management-url":

                (pnetloc, pport,
                 puri, pis_ssl) = parse_url(hdr[1])
                puri = "/" + puri

                _dns_management_host = dns_management_host
                if 'lon.' in pnetloc:
                    _dns_management_host = 'lon.' + _dns_management_host

                dns_management_url = []
                if pis_ssl:
                    dns_management_url.append("https://")
                else:
                    dns_management_url.append("http://")

                for x in (_dns_management_host, puri):
                    dns_management_url.append(x)

        conn.close()

        if not (auth_token, dns_management_host):
            raise AuthenticationError("Invalid response from the " \
                    "authentication service.")

        return ("".join(dns_management_url), auth_token)

# vim:set ai ts=4 sw=4 tw=0 expandtab:

########NEW FILE########
__FILENAME__ = connection
__author__ = "Chmouel Boudjnah <chmouel@chmouel.com>"
"""
connection operations

Connection instances are used to communicate with the remote service.

See COPYING for license information.
"""

import os
import socket
import consts
import time
import datetime
import json

from Queue import Queue, Empty, Full
from errors import ResponseError, UnknownDomain, NotDomainOwner, DomainAlreadyExists
from httplib import HTTPSConnection, HTTPConnection, HTTPException
from math import ceil
from sys import version_info
from urllib import quote

from utils  import unicode_quote, parse_url, \
    THTTPConnection, THTTPSConnection
from domain import DomainResults, Domain
from authentication import Authentication

# Because HTTPResponse objects *have* to have read() called on them
# before they can be used again ...
# pylint: disable-msg=W0612


class Connection(object):
    """
    Manages the connection to the storage system and serves as a factory
    for Container instances.

    @undocumented: http_connect
    @undocumented: make_request
    @undocumented: _check_container_name
    """

    def __init__(self, username=None, api_key=None, timeout=10, **kwargs):
        """
        Accepts keyword arguments for Rackspace Cloud username and api key.
        Optionally, you can omit these keywords and supply an
        Authentication object using the auth keyword.

        @type username: str
        @param username: a Rackspace Cloud username
        @type api_key: str
        @param api_key: a Rackspace Cloud API key
        """
        self.connection_args = None
        self.connection = None
        self.token = None
        self.debuglevel = int(kwargs.get('debuglevel', 0))
        self.user_agent = kwargs.get('useragent', consts.user_agent)
        self.timeout = timeout
        self._total_domains = -1

        self.auth = 'auth' in kwargs and kwargs['auth'] or None

        if not self.auth:
            authurl = kwargs.get('authurl', consts.us_authurl)
            if username and api_key and authurl:
                self.auth = Authentication(username, api_key, authurl=authurl,
                            useragent=self.user_agent)
            else:
                raise TypeError("Incorrect or invalid arguments supplied")

        self._authenticate()

    @property
    def total_domains(self):
        if self._total_domains == -1:
            self.list_domains_info(offset=0, limit=1)
        return self._total_domains

    def _authenticate(self):
        """
        Authenticate and setup this instance with the values returned.
        """
        (url, self.token) = self.auth.authenticate()
        self.connection_args = parse_url(url)

        if version_info[0] <= 2 and version_info[1] < 6:
            self.conn_class = self.connection_args[3] and THTTPSConnection or \
                                                              THTTPConnection
        else:
            self.conn_class = self.connection_args[3] and HTTPSConnection or \
                                                              HTTPConnection
        self.http_connect()

    def convert_iso_datetime(self, dt):
        """
        Convert iso8601 to datetime
        """
        isoFormat = "%Y-%m-%dT%H:%M:%S.000+0000"
        if type(dt) is datetime.datetime:
            return dt
        if dt.endswith("Z"):
            dt = dt.split('Z')[0]
            isoFormat = "%Y-%m-%dT%H:%M:%S"
        return datetime.datetime.strptime(dt, isoFormat)

    def http_connect(self):
        """
        Setup the http connection instance.
        """
        (host, port, self.uri, is_ssl) = self.connection_args
        self.connection = self.conn_class(host, port=port, \
                                              timeout=self.timeout)
        self.connection.set_debuglevel(self.debuglevel)

    def make_request(self, method, path=[], data='', hdrs=None, parms=None):
        """
        Given a method (i.e. GET, PUT, POST, etc), a path, data, header and
        metadata dicts, and an optional dictionary of query parameters,
        performs an http request.
        """
        query_args = ""
        path = '/%s/%s' % \
                 (self.uri.rstrip('/'), '/'.join(
                   [unicode_quote(i) for i in path]))
        if isinstance(parms, dict) and parms:
            query_args = \
                ['%s=%s' % (quote(x),
                            quote(str(y))) for (x, y) in parms.items()]
        elif isinstance(parms, list) and parms:
            query_args = \
                ["%s" % x for x in parms]
        path = '%s?%s' % (path, '&'.join(query_args))

        headers = {'Content-Length': str(len(data)),
                   'User-Agent': self.user_agent,
                   'X-Auth-Token': self.token,
                   'Content-Type': 'application/xml'}
        isinstance(hdrs, dict) and headers.update(hdrs)

        def retry_request():
            '''Re-connect and re-try a failed request once'''
            self.http_connect()
            self.connection.request(method, path, data, headers)
            return self.connection.getresponse()

        try:
            if 'PYTHON_CLOUDDNS_DEBUG' in os.environ and \
                    os.environ['PYTHON_CLOUDDNS_DEBUG'].strip():
                import sys
                url = "https://%s%s\n" % \
                    (self.connection_args[0],
                     path)
                sys.stderr.write("METHOD: %s\n" % (str(method)))
                sys.stderr.write("URL: %s" % (url))
                sys.stderr.write("HEADERS: %s\n" % (str(headers)))
                sys.stderr.write("DATA: %s\n" % (str(data)))
                sys.stderr.write("curl -X '%s' -H 'X-Auth-Token: %s' %s %s" % \
                                     (method, self.token, url, str(data)))
            self.connection.request(method, path, data, headers)
            response = self.connection.getresponse()
        except (socket.error, IOError, HTTPException):
            response = retry_request()
        if response.status == 401:
            self._authenticate()
            headers['X-Auth-Token'] = self.token
            response = retry_request()
        return response

    def get_domains(self, name=None, offset=0, limit=None):
        return DomainResults(self, self.list_domains_info(name, 
                                                          offset, 
                                                          limit))

    def list_domains_info(self, name=None, offset=0, limit=None):
        if offset != 0:
            if limit is None:
                raise ValueError('limit must be specified when setting offset')
            elif offset % limit > 0:
                raise ValueError(
                        'offset (%d) must be a multiple of limit (%d)' % 
                        (offset, limit))
        if limit is None:
            limit = int(ceil(self.total_domains / 100.0) * 100)
        domains = []
        step = min(limit, 100) if limit > 0 else 1
        for _offset in xrange(offset, offset + limit, step):
            resp = self._list_domains_info_raw(name, _offset, step)
            domains_info = json.loads(resp)
            if 'totalEntries' in domains_info:
                self._total_domains = domains_info['totalEntries']
            domains.extend(domains_info['domains'])
        return domains[:limit]
    
    def _list_domains_info_raw(self, name, offset, limit):
        parms = {'offset': offset, 'limit': limit}
        if name is not None:
            parms.update({'name': name})
        response = self.make_request('GET', ['domains'], parms=parms)
        if (response.status < 200) or (response.status > 299):
            response.read()
            raise ResponseError(response.status, response.reason)
        return response.read()

    def get_domain(self, id=None, **dico):
        if id:
            dico['id'] = id
        if 'name' in dico:
            dico['name'] = dico['name'].lower()

        domains = self.list_domains_info(name=dico.get('name', None))
        for domain in domains:
            for k in dico:
                if k in domain and domain[k] == dico[k]:
                    return Domain(self, **domain)
        raise UnknownDomain("Not found")

    def get_domain_details(self, id=None):
        """Get details on a particular domain"""
        parms = { 'showRecords': 'false', 'showSubdomains': 'false' }
        response = self.make_request('GET', ['domains', str(id)], parms=parms)

        if (response.status < 200) or (response.status > 299):
            response.read()
            raise ResponseError(response.status, response.reason)
        read_output = response.read()
        domains = json.loads(read_output)

        return Domain(self, **domains)

    # Take a reponse parse it if there is asyncResponse and wait for
    # it (TODO: should offer to not)
    def wait_for_async_request(self, response):
        if (response.status < 200) or (response.status > 299):
            _output = response.read().strip()
            try:
                output = json.loads(_output)
            except ValueError:
                output = None
            api_reasons = ""
            if output and 'validationErrors' in output:
                for msg in output['validationErrors']['messages']:
                    api_reasons += " (%s)" % msg
            raise ResponseError(response.status, response.reason+api_reasons)
        output = json.loads(response.read())
        jobId = output['jobId']
        while True:
            response = self.make_request('GET', ['status', jobId],
                                         parms=['showDetails=True'])
            if (response.status < 200) or (response.status > 299):
                response.read()
                raise ResponseError(response.status, response.reason)
            _output = response.read().strip()
            output = json.loads(_output)
            if output['status'] == 'COMPLETED':
                try:
                    return output['response']
                except KeyError:
                    return output
            if output['status'] == 'ERROR':
                if (output['error']['code'] == 409 and
                    output['error']['details'] == 'Domain already exists'):
                    raise DomainAlreadyExists
                if (output['error']['code'] == 409 and
                    output['error']['details'].find('belongs to another owner')):
                    raise NotDomainOwner
                raise ResponseError(output['error']['code'],
                                    output['error']['details'])
            time.sleep(1)
            continue

    def _domain(self, name, ttl, emailAddress, comment=""):
        if not ttl >= 300:
            raise Exception("Ttl is a minimun of 300 seconds")
        s = '<domain name="%s" ttl="%s" emailAddress="%s" comment="%s"></domain>'
        return s % (name, ttl, emailAddress, comment)

    def create_domain(self, name, ttl, emailAddress, comment=""):
        domain = [name, ttl, emailAddress, comment]
        return self.create_domains([domain])[0]

    def create_domains(self, domains):
        xml = '<domains xmlns="http://docs.rackspacecloud.com/dns/api/v1.0">'
        ret = []
        for dom in domains:
            ret.append(self._domain(*dom))
        xml += "\n".join(ret)
        xml += "</domains>"
        response = self.make_request('POST', ['domains'], data=xml)
        output = self.wait_for_async_request(response)

        ret = []
        for domain in output['domains']:
            ret.append(Domain(connection=self, **domain))
        return ret

    def delete_domain(self, domain_id):
        return self.delete_domains([domain_id])

    def delete_domains(self, domains_id):
        ret = ["id=%s" % (i) for i in domains_id]
        response = self.make_request('DELETE',
                                     ['domains'],
                                     parms=ret,
                                      )
        return self.wait_for_async_request(response)

    def import_domain(self, bind_zone):
        """
        Allows for a bind zone file to be imported in one operation.  The
        bind_zone parameter can be a string or a file object.
        """

        if type(bind_zone) is file:
            bind_zone = bind_zone.read()

        xml = '<domains xmlns="http://docs.rackspacecloud.com/dns/api/v1.0">'
        xml += '<domain contentType="BIND_9">'
        xml += '<contents>%s</contents>' % bind_zone
        xml += '</domain></domains>'

        response = self.make_request('POST', ['domains', 'import'], data=xml)
        output = self.wait_for_async_request(response)

        ret = []
        for domain in output['domains']:
            ret.append(Domain(self, **domain))
        return ret


class ConnectionPool(Queue):
    """
    A thread-safe connection pool object.

    This component isn't required when using the clouddns library, but it may
    be useful when building threaded applications.
    """

    def __init__(self, username=None, api_key=None, **kwargs):
        auth = kwargs.get('auth', None)
        self.timeout = kwargs.get('timeout', 5)
        self.connargs = {'username': username,
                         'api_key': api_key,
                         'auth': auth}
        poolsize = kwargs.get('poolsize', 10)
        Queue.__init__(self, poolsize)

    def get(self):
        """
        Return a clouddns connection object.

        @rtype: L{Connection}
        @return: a clouddns connection object
        """
        try:
            (create, connobj) = Queue.get(self, block=0)
        except Empty:
            connobj = Connection(**self.connargs)
        return connobj

    def put(self, connobj):
        """
        Place a clouddns connection object back into the pool.

        @param connobj: a clouddns connection object
        @type connobj: L{Connection}
        """
        try:
            Queue.put(self, (time.time(), connobj), block=0)
        except Full:
            del connobj
# vim:set ai sw=4 ts=4 tw=0 expandtab:

########NEW FILE########
__FILENAME__ = consts
""" See COPYING for license information. """

__version__ = "0.1"
user_agent = "python-clouddns/%s" % __version__
us_authurl = 'https://auth.api.rackspacecloud.com/v1.0'
uk_authurl = 'https://lon.auth.api.rackspacecloud.com/v1.0'
dns_management_host = 'dns.api.rackspacecloud.com'
default_authurl = us_authurl
domain_name_limit = 253

########NEW FILE########
__FILENAME__ = domain
# -*- encoding: utf-8 -*-
__author__ = "Chmouel Boudjnah <chmouel@chmouel.com>"
import json

import consts
from errors import InvalidDomainName, ResponseError
from math import ceil
from record import RecordResults, Record


class Domain(object):
    def __set_name(self, name):
        # slashes make for invalid names
        if isinstance(name, (str, unicode)) and \
                ('/' in name or len(name) > consts.domain_name_limit):
            raise InvalidDomainName(name)
        self._name = name

    name = property(fget=lambda self: self._name, fset=__set_name,
        doc="the name of the domain (read-only)")

    def __init__(self, connection=None,
                 name=None,
                 id=None,
                 accountId=None,
                 ttl=None,
                 emailAddress=None,
                 comment=None,
                 updated=None,
                 created=None,
                 nameservers=[],
                 recordsList=[],
                 ):
        self.conn = connection
        self.name = name
        self.id = id
        self.accountId = accountId
        self.ttl = ttl
        self.emailAddress = emailAddress
        self.comment = comment
        self.updated = updated and \
            self.conn.convert_iso_datetime(updated) or \
            None
        self.created = created and \
            self.conn.convert_iso_datetime(created) or \
            None
        self.nameservers = nameservers
        self.records = recordsList
        self._total_records = -1
    
    @property
    def total_records(self):
        if self._total_records == -1:
            self.list_records_info(offset=0, limit=1)
        return self._total_records

    def get_record(self, id=None, **dico):
        if id:
            dico['id'] = id
        if 'name' in dico:
            dico['name'] = dico['name'].lower()
        records = self.list_records_info()
        for record in records:
            for k in dico:
                if k in record and record[k] == dico[k]:
                    return Record(self, **record)
        #TODO:
        raise Exception("Not found")

    def get_records(self, type=None, name=None, data=None, offset=0, limit=None):
        return RecordResults(self, self.list_records_info(type,
                                                          name,
                                                          data,
                                                          offset,
                                                          limit))

    def list_records_info(self, type=None, 
                                name=None, 
                                data=None, 
                                offset=0, 
                                limit=None):
        if offset != 0:
            if limit is None:
                raise ValueError('limit must be specified when setting offset')
            elif offset % limit > 0:
                raise ValueError(
                        'offset (%d) must be a multiple of limit (%d)' % 
                        (offset, limit))
        if limit is None:
            limit = int(ceil(self.total_records / 100.0) * 100)
        if (name is not None or data is not None) and type is None:
            raise ValueError('filtering by name or data requires type to be set')
        records = []
        step = min(limit, 100)
        for _offset in xrange(offset, offset + limit, step):
            resp = self._list_records_raw(type, name, data, _offset, step)
            records_info = json.loads(resp)
            if 'totalEntries' in records_info:
                self._total_records = records_info['totalEntries']
            records.extend(records_info['records'])
        return records[:limit]

    def _list_records_raw(self, type, name, data, offset, limit):
        """
        Returns a chunk list of records
        """
        parms = {'offset': offset, 'limit': limit, 'type': type, 
                 'name': name, 'data': data}
        parms = dict(filter(lambda x: x[1] is not None, parms.items()))
        response = self.conn.make_request('GET', ["domains", self.id,
                                                  "records"], parms=parms)
        if (response.status < 200) or (response.status > 299):
            response.read()
            raise ResponseError(response.status, response.reason)
        return response.read()

    def __getitem__(self, key):
        return self.get_record(key)

    def __str__(self):
        return self.name

    def update(self,
               ttl=None,
               emailAddress=None,
               comment=None):
        dom = {}
        if ttl:
            self.ttl = ttl
            dom['ttl'] = self.ttl
        if emailAddress:
            self.emailAddress = emailAddress
            dom['emailAddress'] = self.emailAddress
        if comment: 
            self.comment = comment
            dom['comment'] = self.comment
        js = json.dumps(dom)

        response = self.conn.make_request('PUT', ["domains", self.id],
                                          data=js, hdrs={'Content-Type': 'application/json'})
        output = self.conn.wait_for_async_request(response)
        return output

    def _record(self, name, data, type, ttl=None, priority=None, comment=""):
        rec = {'name': name,
               'data': data,
               'type': type,
               'comment': comment}
        if type.upper() in ('MX', 'SRV'):
            rec['priority'] = priority
        if ttl: rec['ttl'] = ttl
        return rec 

    def create_record(self, name, data, type, ttl=None, priority=None, comment=""):
        rec = [name, data, type, ttl, priority, comment]
        return self.create_records((rec,))[0]

    def create_records(self, records):
        ret = []
        for rec in records:
            ret.append(self._record(*rec))
        js = json.dumps({"records": ret})
        response = self.conn.make_request('POST',
                                          ['domains', self.id, 'records'],
                                          data=js,
                                          hdrs={'Content-Type': 'application/json'})
        output = self.conn.wait_for_async_request(response)

        ret = []
        for record in output['records']:
            ret.append(Record(domain=self, **record))
        return ret

    def delete_record(self, record_id):
        return self.delete_records([record_id])

    def delete_records(self, records_id):
        ret = ["id=%s" % (i) for i in records_id]
        response = self.conn.make_request('DELETE',
                                          ['domains',
                                           self.id,
                                           'records'],
                                          parms=ret,
                                           )
        return response


class DomainResults(object):
    """
    An iterable results set object for Domains.

    This class implements dictionary- and list-like interfaces.
    """
    def __init__(self, conn, domains=None):
        self._domains = domains if domains is not None else []
        self._names = [k['name'] for k in self._domains]
        self.conn = conn
    
    def __getitem__(self, key):
        kwargs = {}
        if 'comment' in self._domains[key]:
            kwargs['comment'] = self._domains[key]['comment']
        else:
            kwargs['comment'] = None
        
        return Domain(self.conn,
                      self._domains[key]['name'],
                      self._domains[key]['id'],
                      self._domains[key]['accountId'],
                      **kwargs)
                         

    def __getslice__(self, i, j):
        return [Domain(self.conn, k['name'], k['id'], \
                              k['accountId']) for k in self._domains[i:j]]

    def __contains__(self, item):
        return item in self._names

    def __repr__(self):
        return 'DomainResults: %s domains' % len(self)
    __str__ = __repr__

    def __len__(self):
        return len(self._domains)

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


class InvalidDomainName(Error):
    """
    Raised for invalid storage domain names.
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


class InvalidUrl(Error):
    """
    Not a valid url for use with this software.
    """
    pass

class UnknownDomain(Error):
    """
    Raised when a domain name does not belong to this account.
    """
    pass

class NotDomainOwner(Error):
    """
    Raised when a domain belongs to another account.
    """
    pass

class DomainAlreadyExists(Error):
    """
    Raised with a domain already exists.
    """
    pass

########NEW FILE########
__FILENAME__ = record
# -*- encoding: utf-8 -*-
__author__ = "Chmouel Boudjnah <chmouel@chmouel.com>"
import json

class Record(object):
    def __init__(self, domain,
                 data=None,
                 ttl=1800,
                 name=None,
                 type=None,
                 priority=None,
                 comment="",
                 updated=None,
                 created=None,
                 id=None):
        self.domain = domain
        self.data = data
        self.name = name
        self.id = id
        self.ttl = ttl
        self.type = type
        self.priority = priority
        self.comment = comment
        self.updated = updated and \
            self.domain.conn.convert_iso_datetime(updated) or \
            None
        self.created = created and \
            self.domain.conn.convert_iso_datetime(created) or \
            None

    def update(self, data=None,
               ttl=None,
               comment=None):
        rec = {'name': self.name}
        if data:
            self.data = data
            rec['data'] = self.data
        if ttl:
            self.ttl = ttl
            rec['ttl'] = self.ttl
        if comment:
            self.comment = comment
            rec['comment'] = self.comment
        js = json.dumps(rec)
        response = self.domain.conn.make_request('PUT',
                                                 ["domains",
                                                  self.domain.id,
                                                  "records", self.id, ""],
                                                 data=js,
                                                 hdrs={"Content-Type": "application/json"})
        output = self.domain.conn.wait_for_async_request(response)
        return output

    def __str__(self):
        return self.name


class RecordResults(object):
    """
    An iterable results set records for Record.

    This class implements dictionary- and list-like interfaces.
    """
    def __init__(self, domain, records=None):
        self._names = []
        self._records = records if records is not None else []
        self._names = [r['name'] for r in self._records]
        self.domain = domain

    def __getitem__(self, key):
        return Record(self.domain, **(self._records[key]))

    def __getslice__(self, i, j):
        return [Record(self.domain, **k) \
                    for k in self._records[i:j]]

    def __contains__(self, item):
        return item in self._names

    def __len__(self):
        return len(self._records)

    def __repr__(self):
        return 'RecordResults: %s records' % len(self)
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

########NEW FILE########
__FILENAME__ = utils
""" See COPYING for license information. """

import re
from urllib    import quote
from urlparse  import urlparse
from errors    import InvalidUrl
from httplib   import HTTPConnection, HTTPSConnection


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


def unicode_quote(s):
    """
    Utility function to address handling of unicode characters
    when using the quote method of the stdlib module
    urlparse. Converts unicode, if supplied, to utf-8 and returns
    quoted utf-8 string.

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


class THTTPSConnection(HTTPSConnection):
    def __init__(self, host, port, timeout):
        HTTPSConnection.__init__(self, host, port)
        self.timeout = timeout

    def connect(self):
        HTTPSConnection.connect(self)
        self.sock.settimeout(self.timeout)

########NEW FILE########
__FILENAME__ = authentication_test
import unittest
from clouddns.authentication import BaseAuthentication as Auth
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
__FILENAME__ = t
# -*- encoding: utf-8 -*-
__author__ = "Chmouel Boudjnah <chmouel@chmouel.com>"
import clouddns
import os
import sys

REGION = "UK"

US_RCLOUD_USER = os.environ.get("US_RCLOUD_USER")
US_RCLOUD_KEY = os.environ.get("US_RCLOUD_KEY")

UK_RCLOUD_USER = os.environ.get("UK_RCLOUD_USER")
UK_RCLOUD_KEY = os.environ.get("UK_RCLOUD_KEY")

CNX = None
DOMAIN = "chmoutesting-%s.com" % (REGION)
FORCE_DBG = True


def dbg(msg, force_dbg=FORCE_DBG):
    if ('PYTHON_CLOUDDNS_DEBUG' in os.environ and \
            os.environ['PYTHON_CLOUDDNS_DEBUG'].strip()) or \
            force_dbg:
        print "****** %s ******" % msg

if not US_RCLOUD_KEY or not US_RCLOUD_USER:
    print "API Keys env not defined"
    sys.exit(1)


def auth():
    global CNX
    if not CNX:
        if REGION == "US":
            dbg("Authing to US cloud")
            CNX = clouddns.connection.Connection(US_RCLOUD_USER, US_RCLOUD_KEY)
        elif REGION == "UK":
            dbg("DBG: Authing to UK cloud")
            CNX = clouddns.connection.Connection(
                UK_RCLOUD_USER,
                UK_RCLOUD_KEY,
                authurl=clouddns.consts.uk_authurl)
    return CNX


def test():
    cnx = auth()

    # Domain list
    all_domains = cnx.get_domains()
    if all_domains:
        # __getitem__
        domain = all_domains[0]

        # __getslice__
        domain = all_domains[0:1][0]
        # __contains__
        assert(str(domain) in all_domains)
        # __len__
        len(all_domains)

        for x in all_domains:
            if str(x).startswith("chmoutest"):
                dbg("Deleting domain: %s" % x.name)
                cnx.delete_domain(x.id)

    # Create Domain
    dbg("Creating domain: %s" % (DOMAIN))
    domain_created = cnx.create_domain(name=DOMAIN,
                                       ttl=300,
                                       emailAddress="foo@foo.com")

    # Get domain by id.
    dbg("GETting domain by ID: %s" % (domain_created.id))
    sDomain = cnx.get_domain(domain_created.id)
    assert(sDomain.id == domain_created.id)

    # Get domain by name.
    dbg("GETting domain by Name: %s" % (DOMAIN))
    sDomain = cnx.get_domain(name=DOMAIN)
    assert(sDomain.id == domain_created.id)

    domain = domain_created

    ttl = 500
    # Update Domain
    domain.update(ttl=ttl)

    record = "test1.%s" % (DOMAIN)
    # Create Record
    dbg("Creating Record: %s" % (record))
    newRecord = \
        domain.create_record(record, "127.0.0.1", "A")

    # Get Record by ID
    dbg("Get Record By ID: %s" % (newRecord.id))
    record = domain.get_record(newRecord.id)
    assert(record.id == newRecord.id)

    # Get Record by name
    dbg("Get Record By Name: %s" % (record))
    record = domain.get_record(name=record.name)
    assert(record.id == newRecord.id)

    # Modify Record data
    newRecord.update(data="127.0.0.2", ttl=1300)

    # Delete Record
    domain.delete_record(newRecord.id)

test()

########NEW FILE########
