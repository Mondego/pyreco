__FILENAME__ = api
"""Core classes and exceptions for Simple-Salesforce"""

import requests
import json

try:
    from urlparse import urlparse
except ImportError:
    # Python 3+
    from urllib.parse import urlparse
from simple_salesforce.login import SalesforceLogin
from simple_salesforce.util import date_to_iso8601

try:
    from collections import OrderedDict
except ImportError:
    # Python < 2.7
    from ordereddict import OrderedDict


class Salesforce(object):
    """Salesforce Instance

    An instance of Salesforce is a handy way to wrap a Salesforce session
    for easy use of the Salesforce REST API.
    """
    def __init__(self, **kwargs):
        """Initialize the instance with the given parameters.

        Available kwargs

        Password Authentication:

        * username -- the Salesforce username to use for authentication
        * password -- the password for the username
        * security_token -- the security token for the username
        * sandbox -- True if you want to login to `test.salesforce.com`, False
                     if you want to login to `login.salesforce.com`.

        Direct Session and Instance Access:

        * session_id -- Access token for this session

        Then either
        * instance -- Domain of your Salesforce instance, i.e. `na1.salesforce.com`
        OR
        * instance_url -- Full URL of your instance i.e. `https://na1.salesforce.com


        Universal Kwargs:
        * version -- the version of the Salesforce API to use, for example `29.0`
        * proxies -- the optional map of scheme to proxy server
        """

        # Determine if the user passed in the optional version and/or sandbox kwargs
        self.sf_version = kwargs.get('version', '29.0')
        self.sandbox = kwargs.get('sandbox', False)
        self.proxies = kwargs.get('proxies')

        # Determine if the user wants to use our username/password auth or pass in their own information
        if 'username' in kwargs and 'password' in kwargs and 'security_token' in kwargs:
            self.auth_type = "password"
            username = kwargs['username']
            password = kwargs['password']
            security_token = kwargs['security_token']

            # Pass along the username/password to our login helper
            self.session_id, self.sf_instance = SalesforceLogin(
                username=username,
                password=password,
                security_token=security_token,
                sandbox=self.sandbox,
                sf_version=self.sf_version,
                proxies=self.proxies)

        elif 'session_id' in kwargs and ('instance' in kwargs or 'instance_url' in kwargs):
            self.auth_type = "direct"
            self.session_id = kwargs['session_id']

            # If the user provides the full url (as returned by the OAuth interface for
            # example) extract the hostname (which we rely on)
            if 'instance_url' in kwargs:
                self.sf_instance = urlparse(kwargs['instance_url']).hostname
            else:
                self.sf_instance = kwargs['instance']

        elif 'username' in kwargs and 'password' in kwargs and 'organizationId' in kwargs:
            self.auth_type = 'ipfilter'
            username = kwargs['username']
            password = kwargs['password']
            organizationId = kwargs['organizationId']

            # Pass along the username/password to our login helper
            self.session_id, self.sf_instance = SalesforceLogin(
                username=username,
                password=password,
                organizationId=organizationId,
                sandbox=self.sandbox,
                sf_version=self.sf_version,
                proxies=self.proxies)

        else:
            raise SalesforceGeneralError(
                'You must provide login information or an instance and token')

        if self.sandbox:
            self.auth_site = 'https://test.salesforce.com'
        else:
            self.auth_site = 'https://login.salesforce.com'

        self.request = requests.Session()
        self.request.proxies = self.proxies
        self.headers = {
            'Content-Type': 'application/json',
            'Authorization': 'Bearer ' + self.session_id,
            'X-PrettyPrint': '1'
        }

        self.base_url = ('https://{instance}/services/data/v{version}/'
                         .format(instance=self.sf_instance,
                                 version=self.sf_version))
        self.apex_url = ('https://{instance}/services/apexrest/'
                         .format(instance=self.sf_instance))

    def describe(self):
        url = self.base_url + "sobjects"
        result = self.request.get(url, headers=self.headers)
        if result.status_code != 200:
            raise SalesforceGeneralError(result.content)
        json_result = result.json(object_pairs_hook=OrderedDict)
        if len(json_result) == 0:
            return None
        else:
            return json_result

    # SObject Handler
    def __getattr__(self, name):
        """Returns an `SFType` instance for the given Salesforce object type
        (given in `name`).

        The magic part of the SalesforceAPI, this function translates
        calls such as `salesforce_api_instance.Lead.metadata()` into fully
        constituted `SFType` instances to make a nice Python API wrapper
        for the REST API.

        Arguments:

        * name -- the name of a Salesforce object type, e.g. Lead or Contact
        """
        return SFType(name, self.session_id, self.sf_instance, self.sf_version, self.proxies)

    # Search Functions
    def search(self, search):
        """Returns the result of a Salesforce search as a dict decoded from
        the Salesforce response JSON payload.

        Arguments:

        * search -- the fully formatted SOSL search string, e.g.
                    `FIND {Waldo}`
        """
        url = self.base_url + 'search/'

        # `requests` will correctly encode the query string passed as `params`
        params = {'q': search}
        result = self.request.get(url, headers=self.headers, params=params)
        if result.status_code != 200:
            raise SalesforceGeneralError(result.content)
        json_result = result.json(object_pairs_hook=OrderedDict)
        if len(json_result) == 0:
            return None
        else:
            return json_result

    def quick_search(self, search):
        """Returns the result of a Salesforce search as a dict decoded from
        the Salesforce response JSON payload.

        Arguments:

        * search -- the non-SOSL search string, e.g. `Waldo`. This search
                    string will be wrapped to read `FIND {Waldo}` before being
                    sent to Salesforce
        """
        search_string = 'FIND {{{search_string}}}'.format(search_string=search)
        return self.search(search_string)

    # Query Handler
    def query(self, query, **kwargs):
        """Return the result of a Salesforce SOQL query as a dict decoded from
        the Salesforce response JSON payload.

        Arguments:

        * query -- the SOQL query to send to Salesforce, e.g.
                   `SELECT Id FROM Lead WHERE Email = "waldo@somewhere.com"`
        """
        url = self.base_url + 'query/'
        params = {'q': query}
        # `requests` will correctly encode the query string passed as `params`
        result = self.request.get(url, headers=self.headers, params=params, **kwargs)

        if result.status_code != 200:
            _exception_handler(result)

        return result.json(object_pairs_hook=OrderedDict)

    def query_more(self, next_records_identifier, identifier_is_url=False, **kwargs):
        """Retrieves more results from a query that returned more results
        than the batch maximum. Returns a dict decoded from the Salesforce
        response JSON payload.

        Arguments:

        * next_records_identifier -- either the Id of the next Salesforce
                                     object in the result, or a URL to the
                                     next record in the result.
        * identifier_is_url -- True if `next_records_identifier` should be
                               treated as a URL, False if
                               `next_records_identifer` should be treated as
                               an Id.
        """
        if identifier_is_url:
            # Don't use `self.base_url` here because the full URI is provided
            url = ('https://{instance}{next_record_url}'
                   .format(instance=self.sf_instance,
                           next_record_url=next_records_identifier))
        else:
            url = self.base_url + 'query/{next_record_id}'
            url = url.format(next_record_id=next_records_identifier)
        result = self.request.get(url, headers=self.headers, **kwargs)

        if result.status_code != 200:
            _exception_handler(result)

        return result.json(object_pairs_hook=OrderedDict)

    def query_all(self, query, **kwargs):
        """Returns the full set of results for the `query`. This is a
        convenience wrapper around `query(...)` and `query_more(...)`.

        The returned dict is the decoded JSON payload from the final call to
        Salesforce, but with the `totalSize` field representing the full
        number of results retrieved and the `records` list representing the
        full list of records retrieved.

        Arguments

        * query -- the SOQL query to send to Salesforce, e.g.
                   `SELECT Id FROM Lead WHERE Email = "waldo@somewhere.com"`
        """
        def get_all_results(previous_result, **kwargs):
            """Inner function for recursing until there are no more results.

            Returns the full set of results that will be the return value for
            `query_all(...)`

            Arguments:

            * previous_result -- the modified result of previous calls to
                                 Salesforce for this query
            """
            if previous_result['done']:
                return previous_result
            else:
                result = self.query_more(previous_result['nextRecordsUrl'],
                                         identifier_is_url=True, **kwargs)
                result['totalSize'] += previous_result['totalSize']
                # Include the new list of records with the previous list
                previous_result['records'].extend(result['records'])
                result['records'] = previous_result['records']
                # Continue the recursion
                return get_all_results(result, **kwargs)

        # Make the initial query to Salesforce
        result = self.query(query, **kwargs)
        # The number of results might have exceeded the Salesforce batch limit
        # so check whether there are more results and retrieve them if so.
        return get_all_results(result, **kwargs)

    def apexecute(self, action, method='GET', data=None):
        result = self._call_salesforce(method, self.apex_url + action, data=json.dumps(data))

        if result.status_code == 200:
            try:
                response_content = result.json()
            except Exception:
                response_content = result.text
            return response_content

    def _call_salesforce(self, method, url, **kwargs):
        """Utility method for performing HTTP call to Salesforce.

        Returns a `requests.result` object.
        """
        headers = {
            'Content-Type': 'application/json',
            'Authorization': 'Bearer ' + self.session_id,
            'X-PrettyPrint': '1'
        }
        result = self.request.request(method, url, headers=headers, **kwargs)

        if result.status_code >= 300:
            _exception_handler(result)

        return result


class SFType(object):
    """An interface to a specific type of SObject"""

    def __init__(self, object_name, session_id, sf_instance, sf_version='27.0', proxies=None):
        """Initialize the instance with the given parameters.

        Arguments:

        * object_name -- the name of the type of SObject this represents,
                         e.g. `Lead` or `Contact`
        * session_id -- the session ID for authenticating to Salesforce
        * sf_instance -- the domain of the instance of Salesforce to use
        * sf_version -- the version of the Salesforce API to use
        * proxies -- the optional map of scheme to proxy server
        """
        self.session_id = session_id
        self.name = object_name
        self.request = requests.Session()
        self.request.proxies = proxies

        self.base_url = ('https://{instance}/services/data/v{sf_version}/sobjects/{object_name}/'
                         .format(instance=sf_instance,
                                 object_name=object_name,
                                 sf_version=sf_version))

    def metadata(self):
        """Returns the result of a GET to `.../{object_name}/` as a dict
        decoded from the JSON payload returned by Salesforce.
        """
        result = self._call_salesforce('GET', self.base_url)
        return result.json(object_pairs_hook=OrderedDict)

    def describe(self):
        """Returns the result of a GET to `.../{object_name}/describe` as a
        dict decoded from the JSON payload returned by Salesforce.
        """
        result = self._call_salesforce('GET', self.base_url + 'describe')
        return result.json(object_pairs_hook=OrderedDict)

    def describe_layout(self, record_id):
        """Returns the result of a GET to `.../{object_name}/describe/layouts/<recordid>` as a
        dict decoded from the JSON payload returned by Salesforce.
        """
        result = self._call_salesforce('GET', self.base_url + 'describe/layouts/' + record_id)
        return result.json(object_pairs_hook=OrderedDict)

    def get(self, record_id):
        """Returns the result of a GET to `.../{object_name}/{record_id}` as a
        dict decoded from the JSON payload returned by Salesforce.

        Arguments:

        * record_id -- the Id of the SObject to get
        """
        result = self._call_salesforce('GET', self.base_url + record_id)
        return result.json(object_pairs_hook=OrderedDict)

    def create(self, data):
        """Creates a new SObject using a POST to `.../{object_name}/`.

        Returns a dict decoded from the JSON payload returned by Salesforce.

        Arguments:

        * data -- a dict of the data to create the SObject from. It will be
                  JSON-encoded before being transmitted.
        """
        result = self._call_salesforce('POST', self.base_url,
                                       data=json.dumps(data))
        return result.json(object_pairs_hook=OrderedDict)

    def upsert(self, record_id, data):
        """Creates or updates an SObject using a PATCH to
        `.../{object_name}/{record_id}`.

        Returns a dict decoded from the JSON payload returned by Salesforce.

        Arguments:

        * record_id -- an identifier for the SObject as described in the
                       Salesforce documentation
        * data -- a dict of the data to create or update the SObject from. It
                  will be JSON-encoded before being transmitted.
        """
        result = self._call_salesforce('PATCH', self.base_url + record_id,
                                       data=json.dumps(data))
        return result.status_code

    def update(self, record_id, data):
        """Updates an SObject using a PATCH to
        `.../{object_name}/{record_id}`.

        Returns a dict decoded from the JSON payload returned by Salesforce.

        Arguments:

        * record_id -- the Id of the SObject to update
        * data -- a dict of the data to update the SObject from. It will be
                  JSON-encoded before being transmitted.
        """
        result = self._call_salesforce('PATCH', self.base_url + record_id,
                                       data=json.dumps(data))
        return result.status_code

    def delete(self, record_id):
        """Deletes an SObject using a DELETE to
        `.../{object_name}/{record_id}`.

        Returns a dict decoded from the JSON payload returned by Salesforce.

        Arguments:

        * record_id -- the Id of the SObject to delete
        """
        result = self._call_salesforce('DELETE', self.base_url + record_id)
        return result.status_code

    def deleted(self, start, end):
        """Use the SObject Get Deleted resource to get a list of deleted records for the specified object.
         .../deleted/?start=2013-05-05T00:00:00+00:00&end=2013-05-10T00:00:00+00:00

        * start -- start datetime object
        * end -- end datetime object
        """
        url = self.base_url + 'deleted/?start={start}&end={end}'.format(
            start=date_to_iso8601(start), end=date_to_iso8601(end))
        result = self._call_salesforce('GET', url)
        return result.json(object_pairs_hook=OrderedDict)

    def updated(self, start, end):
        """Use the SObject Get Updated resource to get a list of updated (modified or added)
        records for the specified object.

         .../updated/?start=2014-03-20T00:00:00+00:00&end=2014-03-22T00:00:00+00:00

        * start -- start datetime object
        * end -- end datetime object
        """
        url = self.base_url + 'updated/?start={start}&end={end}'.format(
            start=date_to_iso8601(start), end=date_to_iso8601(end))
        result = self._call_salesforce('GET', url)
        return result.json(object_pairs_hook=OrderedDict)

    def _call_salesforce(self, method, url, **kwargs):
        """Utility method for performing HTTP call to Salesforce.

        Returns a `requests.result` object.
        """
        headers = {
            'Content-Type': 'application/json',
            'Authorization': 'Bearer ' + self.session_id,
            'X-PrettyPrint': '1'
        }
        result = self.request.request(method, url, headers=headers, **kwargs)

        if result.status_code >= 300:
            _exception_handler(result, self.name)

        return result


class SalesforceAPI(Salesforce):
    """Depreciated SalesforceAPI Instance

    This class implements the Username/Password Authentication Mechanism using Arguments
    It has since been surpassed by the 'Salesforce' class, which relies on kwargs

    """
    def __init__(self, username, password, security_token, sandbox=False,
                 sf_version='27.0'):
        """Initialize the instance with the given parameters.

        Arguments:

        * username -- the Salesforce username to use for authentication
        * password -- the password for the username
        * security_token -- the security token for the username
        * sandbox -- True if you want to login to `test.salesforce.com`, False
                     if you want to login to `login.salesforce.com`.
        * sf_version -- the version of the Salesforce API to use, for example
                        "27.0"
        """
        import warnings
        warnings.warn(
            "Use of login arguments has been depreciated. Please use kwargs", DeprecationWarning)

        super(
            SalesforceAPI, self).__init__(username=username, password=password,
                                          security_token=security_token, sandbox=sandbox, version=sf_version)


def _exception_handler(result, name=""):
    """Exception router. Determines which error to raise for bad results"""
    url = result.url
    try:
        response_content = result.json()
    except Exception:
        response_content = result.text

    if result.status_code == 300:
        message = "More than one record for {url}. Response content: {content}"
        message = message.format(url=url, content=response_content)
        raise SalesforceMoreThanOneRecord(message)
    elif result.status_code == 400:
        message = "Malformed request {url}. Response content: {content}"
        message = message.format(url=url, content=response_content)
        raise SalesforceMalformedRequest(message)
    elif result.status_code == 401:
        message = "Expired session for {url}. Response content: {content}"
        message = message.format(url=url, content=response_content)
        raise SalesforceExpiredSession(message)
    elif result.status_code == 403:
        message = "Request refused for {url}. Response content: {content}"
        message = message.format(url=url, content=response_content)
        raise SalesforceRefusedRequest(message)
    elif result.status_code == 404:
        message = 'Resource {name} Not Found. Response content: {content}'
        message = message.format(name=name, content=response_content)
        raise SalesforceResourceNotFound(message)
    else:
        message = 'Error Code {status}. Response content: {content}'
        message = message.format(status=result.status_code, content=response_content)
        raise SalesforceGeneralError(message)


class SalesforceMoreThanOneRecord(Exception):
    """
    Error Code: 300
    The value returned when an external ID exists in more than one record. The
    response body contains the list of matching records.
    """
    pass


class SalesforceMalformedRequest(Exception):
    """
    Error Code: 400
    The request couldn't be understood, usually becaue the JSON or XML body contains an error.
    """
    pass


class SalesforceExpiredSession(Exception):
    """
    Error Code: 401
    The session ID or OAuth token used has expired or is invalid. The response
    body contains the message and errorCode.
    """
    pass


class SalesforceRefusedRequest(Exception):
    """
    Error Code: 403
    The request has been refused. Verify that the logged-in user has
    appropriate permissions.
    """
    pass


class SalesforceResourceNotFound(Exception):
    """
    Error Code: 404
    The requested resource couldn't be found. Check the URI for errors, and
    verify that there are no sharing issues.
    """
    pass


class SalesforceGeneralError(Exception):
    """
    A non-specific Salesforce error.
    """
    pass

########NEW FILE########
__FILENAME__ = login
"""Login classes and functions for Simple-Salesforce

Heavily Modified from RestForce 1.0.0
"""

from simple_salesforce.util import getUniqueElementValueFromXmlString
try:
    # Python 3+
    from html import escape
except ImportError:
    from cgi import escape
import requests


def SalesforceLogin(**kwargs):
    """Return a tuple of `(session_id, sf_instance)` where `session_id` is the
    session ID to use for authentication to Salesforce and `sf_instance` is
    the domain of the instance of Salesforce to use for the session.

    Arguments:

    * username -- the Salesforce username to use for authentication
    * password -- the password for the username
    * security_token -- the security token for the username
    * organizationId -- the ID of your organization
            NOTE: security_token an organizationId are mutually exclusive
    * sandbox -- True if you want to login to `test.salesforce.com`, False if
                 you want to login to `login.salesforce.com`.
    * sf_version -- the version of the Salesforce API to use, for example
                    "27.0"
    * proxies -- the optional map of scheme to proxy server
    """

    sandbox = kwargs.get('sandbox', False)
    sf_version = kwargs.get('sf_version', '23.0')

    username = kwargs['username']
    password = kwargs['password']

    soap_url = 'https://{domain}.salesforce.com/services/Soap/u/{sf_version}'
    domain = 'test' if sandbox else 'login'

    soap_url = soap_url.format(domain=domain, sf_version=sf_version)

    username = escape(username)
    password = escape(password)

    # Check if token authentication is used
    if 'security_token' in kwargs:
        security_token = kwargs['security_token']

        # Security Token Soap request body
        login_soap_request_body = """<?xml version="1.0" encoding="utf-8" ?>
        <env:Envelope
                xmlns:xsd="http://www.w3.org/2001/XMLSchema"
                xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
                xmlns:env="http://schemas.xmlsoap.org/soap/envelope/">
            <env:Body>
                <n1:login xmlns:n1="urn:partner.soap.sforce.com">
                    <n1:username>{username}</n1:username>
                    <n1:password>{password}{token}</n1:password>
                </n1:login>
            </env:Body>
        </env:Envelope>""".format(username=username, password=password, token=security_token)

    # Check if IP Filtering is used in cojuction with organizationId
    elif 'organizationId' in kwargs:
        organizationId = kwargs['organizationId']

        # IP Filtering Login Soap request body
        login_soap_request_body = """<?xml version="1.0" encoding="utf-8" ?>
        <soapenv:Envelope
                xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/"
                xmlns:urn="urn:partner.soap.sforce.com">
            <soapenv:Header>
                <urn:CallOptions>
                    <urn:client>RestForce</urn:client>
                    <urn:defaultNamespace>sf</urn:defaultNamespace>
                </urn:CallOptions>
                <urn:LoginScopeHeader>
                    <urn:organizationId>{organizationId}</urn:organizationId>
                </urn:LoginScopeHeader>
            </soapenv:Header>
            <soapenv:Body>
                <urn:login>
                    <urn:username>{username}</urn:username>
                    <urn:password>{password}</urn:password>
                </urn:login>
            </soapenv:Body>
        </soapenv:Envelope>""".format(
            username=username, password=password, organizationId=organizationId)

    else:
        except_code = 'INVALID AUTH'
        except_msg = 'You must submit either a security token or organizationId for authentication'
        raise SalesforceAuthenticationFailed('{code}: {message}'.format(
            code=except_code, message=except_msg))

    login_soap_request_headers = {
        'content-type': 'text/xml',
        'charset': 'UTF-8',
        'SOAPAction': 'login'
    }
    response = requests.post(soap_url,
                             login_soap_request_body,
                             headers=login_soap_request_headers,
                             proxies=kwargs.get('proxies', None))

    if response.status_code != 200:
        except_code = getUniqueElementValueFromXmlString(
            response.content, 'sf:exceptionCode')
        except_msg = getUniqueElementValueFromXmlString(
            response.content, 'sf:exceptionMessage')
        raise SalesforceAuthenticationFailed('{code}: {message}'.format(
            code=except_code, message=except_msg))

    session_id = getUniqueElementValueFromXmlString(response.content, 'sessionId')
    server_url = getUniqueElementValueFromXmlString(response.content, 'serverUrl')

    sf_instance = (server_url
                   .replace('http://', '')
                   .replace('https://', '')
                   .split('/')[0]
                   .replace('-api', ''))

    return session_id, sf_instance


class SalesforceAuthenticationFailed(Exception):
    """
    Thrown to indicate that authentication with Salesforce failed.
    """
    pass

########NEW FILE########
__FILENAME__ = test_api
"""Tests for api.py"""

try:
    # Python 2.6
    import unittest2 as unittest
except ImportError:
    import unittest

try:
    # Python 2.6/2.7
    from mock import Mock, patch
except ImportError:
    # Python 3
    from unittest.mock import Mock, patch

from simple_salesforce.api import (
    _exception_handler,
    SalesforceMoreThanOneRecord,
    SalesforceMalformedRequest,
    SalesforceExpiredSession,
    SalesforceRefusedRequest,
    SalesforceResourceNotFound,
    SalesforceGeneralError
)


class TestSalesforce(unittest.TestCase):
    """Tests for the Salesforce instance"""
    def setUp(self):
        """Setup the SalesforceLogin tests"""
        request_patcher = patch('simple_salesforce.api.requests')
        self.mockrequest = request_patcher.start()
        self.addCleanup(request_patcher.stop)


class TestExceptionHandler(unittest.TestCase):
    """Test the exception router"""
    def setUp(self):
        """Setup the exception router tests"""
        self.mockresult = Mock()
        self.mockresult.url = 'http://www.example.com/'
        self.mockresult.json.return_value = 'Example Content'

    def test_multiple_records_returned(self):
        """Test multiple records returned (a 300 code)"""
        self.mockresult.status_code = 300
        with self.assertRaises(SalesforceMoreThanOneRecord) as cm:
            _exception_handler(self.mockresult)

        self.assertEqual(str(cm.exception), (
            'More than one record for '
            'http://www.example.com/. Response content: Example Content'))

    def test_malformed_request(self):
        """Test a malformed request (400 code)"""
        self.mockresult.status_code = 400
        with self.assertRaises(SalesforceMalformedRequest) as cm:
            _exception_handler(self.mockresult)

        self.assertEqual(str(cm.exception), (
            'Malformed request '
            'http://www.example.com/. Response content: Example Content'))

    def test_expired_session(self):
        """Test an expired session (401 code)"""
        self.mockresult.status_code = 401
        with self.assertRaises(SalesforceExpiredSession) as cm:
            _exception_handler(self.mockresult)

        self.assertEqual(str(cm.exception), (
            'Expired session for '
            'http://www.example.com/. Response content: Example Content'))

    def test_request_refused(self):
        """Test a refused request (403 code)"""
        self.mockresult.status_code = 403
        with self.assertRaises(SalesforceRefusedRequest) as cm:
            _exception_handler(self.mockresult)

        self.assertEqual(str(cm.exception), (
            'Request refused for '
            'http://www.example.com/. Response content: Example Content'))

    def test_resource_not_found(self):
        """Test resource not found (404 code)"""
        self.mockresult.status_code = 404
        with self.assertRaises(SalesforceResourceNotFound) as cm:
            _exception_handler(self.mockresult, 'SpecialContacts')

        self.assertEqual(str(cm.exception), (
            'Resource SpecialContacts Not'
            ' Found. Response content: Example Content'))

    def test_generic_error_code(self):
        """Test an error code that is otherwise not caught"""
        self.mockresult.status_code = 500
        with self.assertRaises(SalesforceGeneralError) as cm:
            _exception_handler(self.mockresult)

        self.assertEqual(str(cm.exception), (
            'Error Code 500. Response content'
            ': Example Content'))

########NEW FILE########
__FILENAME__ = test_login
"""Tests for login.py"""

try:
    import unittest2 as unittest
except ImportError:
    import unittest

try:
    # Python 2.6/2.7
    from mock import Mock, patch
except ImportError:
    # Python 3
    from unittest.mock import Mock, patch

from simple_salesforce.login import (
    SalesforceLogin, SalesforceAuthenticationFailed
)


class TestSalesforceLogin(unittest.TestCase):
    """Tests for the SalesforceLogin function"""
    def setUp(self):
        """Setup the SalesforceLogin tests"""
        request_patcher = patch('simple_salesforce.login.requests')
        self.mockrequest = request_patcher.start()
        self.addCleanup(request_patcher.stop)

    def test_failure(self):
        """Test A Failed Login Response"""
        return_mock = Mock()
        return_mock.status_code = 500
        # pylint: disable=line-too-long
        return_mock.content = '<?xml version="1.0" encoding="UTF-8"?><soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:sf="urn:fault.partner.soap.sforce.com" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"><soapenv:Body><soapenv:Fault><faultcode>INVALID_LOGIN</faultcode><faultstring>INVALID_LOGIN: Invalid username, password, security token; or user locked out.</faultstring><detail><sf:LoginFault xsi:type="sf:LoginFault"><sf:exceptionCode>INVALID_LOGIN</sf:exceptionCode><sf:exceptionMessage>Invalid username, password, security token; or user locked out.</sf:exceptionMessage></sf:LoginFault></detail></soapenv:Fault></soapenv:Body></soapenv:Envelope>'
        self.mockrequest.post.return_value = return_mock

        with self.assertRaises(SalesforceAuthenticationFailed):
            session_id, instance = SalesforceLogin(
                username='myemail@example.com.sandbox',
                password='password',
                security_token='token',
                sandbox=True
            )
        self.assertTrue(self.mockrequest.post.called)

########NEW FILE########
__FILENAME__ = test_util
"""Tests for simple-salesforce utility functions"""
try:
    import unittest2 as unittest
except ImportError:
    import unittest

import datetime
import pytz
from simple_salesforce.util import getUniqueElementValueFromXmlString, date_to_iso8601


class TestXMLParser(unittest.TestCase):
    """Test the XML parser utility function"""
    def test_returns_valid_value(self):
        """Test that when given the correct XML a valid response is returned"""
        result = getUniqueElementValueFromXmlString(
            '<?xml version="1.0" encoding="UTF-8"?><foo>bar</foo>', 'foo')
        self.assertEqual(result, 'bar')

    def test_date_to_iso8601(self):
        date = datetime.datetime(2014, 3, 22, 00, 00, 00, 0, tzinfo=pytz.UTC)
        result = date_to_iso8601(date)
        expected = '2014-03-22T00%3A00%3A00%2B00%3A00'
        self.assertEquals(result, expected)

        date = datetime.datetime(2014, 3, 22, 00, 00, 00, 0, tzinfo=pytz.timezone('America/Chicago'))
        result = date_to_iso8601(date)
        expected = '2014-03-22T00%3A00%3A00-06%3A00'
        self.assertEquals(result, expected)

########NEW FILE########
__FILENAME__ = util
"""Utility functions for simple-salesforce"""

import xml.dom.minidom


def getUniqueElementValueFromXmlString(xmlString, elementName):
    """
    Extracts an element value from an XML string.

    For example, invoking
    getUniqueElementValueFromXmlString('<?xml version="1.0" encoding="UTF-8"?><foo>bar</foo>', 'foo')
    should return the value 'bar'.
    """
    xmlStringAsDom = xml.dom.minidom.parseString(xmlString)
    elementsByName = xmlStringAsDom.getElementsByTagName(elementName)
    elementValue = None
    if len(elementsByName) > 0:
        elementValue = elementsByName[0].toxml().replace('<' + elementName + '>', '').replace('</' + elementName + '>', '')
    return elementValue


def date_to_iso8601(date):
    """Returns an ISO8601 string from a date"""
    datetimestr = date.strftime('%Y-%m-%dT%H:%M:%S')
    timezone_sign = date.strftime('%z')[0:1]
    timezone_str = '%s:%s' % (
        date.strftime('%z')[1:3], date.strftime('%z')[3:5])
    return '{datetimestr}{tzsign}{timezone}'.format(
        datetimestr=datetimestr,
        tzsign=timezone_sign,
        timezone=timezone_str
        ).replace(':', '%3A').replace('+', '%2B')
########NEW FILE########
