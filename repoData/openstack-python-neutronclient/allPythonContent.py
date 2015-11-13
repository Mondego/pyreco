__FILENAME__ = conf
# -*- coding: utf-8 -*-
#

project = 'python-neutronclient'

# -- General configuration ---------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = ['sphinx.ext.autodoc', 'sphinx.ext.intersphinx']

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The master toctree document.
master_doc = 'index'

# General information about the project.
copyright = u'OpenStack Foundation'

# If true, '()' will be appended to :func: etc. cross-reference text.
add_function_parentheses = True

# If true, the current module name will be prepended to all description
# unit titles (such as .. function::).
add_module_names = True

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = 'sphinx'

# -- Options for HTML output ---------------------------------------------

# The theme to use for HTML and HTML Help pages.  Major themes that come with
# Sphinx are currently 'default' and 'sphinxdoc'.
html_theme = 'nature'

# Output file base name for HTML help builder.
htmlhelp_basename = '%sdoc' % project


# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author,
#  documentclass [howto/manual]).
latex_documents = [
  ('index',
    '%s.tex' % project,
    u'%s Documentation' % project,
    u'OpenStack Foundation', 'manual'),
]

# Example configuration for intersphinx: refer to the Python standard library.
intersphinx_mapping = {'http://docs.python.org/': None}

########NEW FILE########
__FILENAME__ = client
# Copyright 2012 OpenStack Foundation.
# All Rights Reserved
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.
#

try:
    import json
except ImportError:
    import simplejson as json
import logging
import os

import requests

from neutronclient.common import exceptions
from neutronclient.common import utils
from neutronclient.openstack.common.gettextutils import _

_logger = logging.getLogger(__name__)

if os.environ.get('NEUTRONCLIENT_DEBUG'):
    ch = logging.StreamHandler()
    _logger.setLevel(logging.DEBUG)
    _logger.addHandler(ch)
    _requests_log_level = logging.DEBUG
else:
    _requests_log_level = logging.WARNING

logging.getLogger("requests").setLevel(_requests_log_level)


class ServiceCatalog(object):
    """Helper methods for dealing with a Keystone Service Catalog."""

    def __init__(self, resource_dict):
        self.catalog = resource_dict

    def get_token(self):
        """Fetch token details from service catalog."""
        token = {'id': self.catalog['access']['token']['id'],
                 'expires': self.catalog['access']['token']['expires'], }
        try:
            token['user_id'] = self.catalog['access']['user']['id']
            token['tenant_id'] = (
                self.catalog['access']['token']['tenant']['id'])
        except Exception:
            # just leave the tenant and user out if it doesn't exist
            pass
        return token

    def url_for(self, attr=None, filter_value=None,
                service_type='network', endpoint_type='publicURL'):
        """Fetch the URL from the Neutron service for
        a particular endpoint type. If none given, return
        publicURL.
        """

        catalog = self.catalog['access'].get('serviceCatalog', [])
        matching_endpoints = []
        for service in catalog:
            if service['type'] != service_type:
                continue

            endpoints = service['endpoints']
            for endpoint in endpoints:
                if not filter_value or endpoint.get(attr) == filter_value:
                    matching_endpoints.append(endpoint)

        if not matching_endpoints:
            raise exceptions.EndpointNotFound()
        elif len(matching_endpoints) > 1:
            raise exceptions.AmbiguousEndpoints(
                matching_endpoints=matching_endpoints)
        else:
            if endpoint_type not in matching_endpoints[0]:
                raise exceptions.EndpointTypeNotFound(type_=endpoint_type)

            return matching_endpoints[0][endpoint_type]


class HTTPClient(object):
    """Handles the REST calls and responses, include authn."""

    USER_AGENT = 'python-neutronclient'

    def __init__(self, username=None, user_id=None,
                 tenant_name=None, tenant_id=None,
                 password=None, auth_url=None,
                 token=None, region_name=None, timeout=None,
                 endpoint_url=None, insecure=False,
                 endpoint_type='publicURL',
                 auth_strategy='keystone', ca_cert=None, log_credentials=False,
                 service_type='network',
                 **kwargs):

        self.username = username
        self.user_id = user_id
        self.tenant_name = tenant_name
        self.tenant_id = tenant_id
        self.password = password
        self.auth_url = auth_url.rstrip('/') if auth_url else None
        self.service_type = service_type
        self.endpoint_type = endpoint_type
        self.region_name = region_name
        self.timeout = timeout
        self.auth_token = token
        self.auth_tenant_id = None
        self.auth_user_id = None
        self.content_type = 'application/json'
        self.endpoint_url = endpoint_url
        self.auth_strategy = auth_strategy
        self.log_credentials = log_credentials
        if insecure:
            self.verify_cert = False
        else:
            self.verify_cert = ca_cert if ca_cert else True

    def _cs_request(self, *args, **kwargs):
        kargs = {}
        kargs.setdefault('headers', kwargs.get('headers', {}))
        kargs['headers']['User-Agent'] = self.USER_AGENT

        if 'content_type' in kwargs:
            kargs['headers']['Content-Type'] = kwargs['content_type']
            kargs['headers']['Accept'] = kwargs['content_type']
        else:
            kargs['headers']['Content-Type'] = self.content_type
            kargs['headers']['Accept'] = self.content_type

        if 'body' in kwargs:
            kargs['body'] = kwargs['body']
        args = utils.safe_encode_list(args)
        kargs = utils.safe_encode_dict(kargs)

        if self.log_credentials:
            log_kargs = kargs
        else:
            log_kargs = self._strip_credentials(kargs)

        utils.http_log_req(_logger, args, log_kargs)
        try:
            resp, body = self.request(*args, **kargs)
        except requests.exceptions.SSLError as e:
            raise exceptions.SslCertificateValidationError(reason=e)
        except Exception as e:
            # Wrap the low-level connection error (socket timeout, redirect
            # limit, decompression error, etc) into our custom high-level
            # connection exception (it is excepted in the upper layers of code)
            _logger.debug("throwing ConnectionFailed : %s", e)
            raise exceptions.ConnectionFailed(reason=e)
        utils.http_log_resp(_logger, resp, body)
        status_code = self.get_status_code(resp)
        if status_code == 401:
            raise exceptions.Unauthorized(message=body)
        return resp, body

    def _strip_credentials(self, kwargs):
        if kwargs.get('body') and self.password:
            log_kwargs = kwargs.copy()
            log_kwargs['body'] = kwargs['body'].replace(self.password,
                                                        'REDACTED')
            return log_kwargs
        else:
            return kwargs

    def authenticate_and_fetch_endpoint_url(self):
        if not self.auth_token:
            self.authenticate()
        elif not self.endpoint_url:
            self.endpoint_url = self._get_endpoint_url()

    def request(self, url, method, **kwargs):
        kwargs.setdefault('headers', kwargs.get('headers', {}))
        kwargs['headers']['User-Agent'] = self.USER_AGENT
        kwargs['headers']['Accept'] = 'application/json'
        if 'body' in kwargs:
            kwargs['headers']['Content-Type'] = 'application/json'
            kwargs['data'] = kwargs['body']
            del kwargs['body']
        resp = requests.request(
            method,
            url,
            verify=self.verify_cert,
            **kwargs)

        return resp, resp.text

    def do_request(self, url, method, **kwargs):
        self.authenticate_and_fetch_endpoint_url()
        # Perform the request once. If we get a 401 back then it
        # might be because the auth token expired, so try to
        # re-authenticate and try again. If it still fails, bail.
        try:
            kwargs.setdefault('headers', {})
            if self.auth_token is None:
                self.auth_token = ""
            kwargs['headers']['X-Auth-Token'] = self.auth_token
            resp, body = self._cs_request(self.endpoint_url + url, method,
                                          **kwargs)
            return resp, body
        except exceptions.Unauthorized:
            self.authenticate()
            kwargs.setdefault('headers', {})
            kwargs['headers']['X-Auth-Token'] = self.auth_token
            resp, body = self._cs_request(
                self.endpoint_url + url, method, **kwargs)
            return resp, body

    def _extract_service_catalog(self, body):
        """Set the client's service catalog from the response data."""
        self.service_catalog = ServiceCatalog(body)
        try:
            sc = self.service_catalog.get_token()
            self.auth_token = sc['id']
            self.auth_tenant_id = sc.get('tenant_id')
            self.auth_user_id = sc.get('user_id')
        except KeyError:
            raise exceptions.Unauthorized()
        if not self.endpoint_url:
            self.endpoint_url = self.service_catalog.url_for(
                attr='region', filter_value=self.region_name,
                service_type=self.service_type,
                endpoint_type=self.endpoint_type)

    def _authenticate_keystone(self):
        if self.user_id:
            creds = {'userId': self.user_id,
                     'password': self.password}
        else:
            creds = {'username': self.username,
                     'password': self.password}

        if self.tenant_id:
            body = {'auth': {'passwordCredentials': creds,
                             'tenantId': self.tenant_id, }, }
        else:
            body = {'auth': {'passwordCredentials': creds,
                             'tenantName': self.tenant_name, }, }

        if self.auth_url is None:
            raise exceptions.NoAuthURLProvided()

        token_url = self.auth_url + "/tokens"
        resp, resp_body = self._cs_request(token_url, "POST",
                                           body=json.dumps(body),
                                           content_type="application/json",
                                           allow_redirects=True)
        status_code = self.get_status_code(resp)
        if status_code != 200:
            raise exceptions.Unauthorized(message=resp_body)
        if resp_body:
            try:
                resp_body = json.loads(resp_body)
            except ValueError:
                pass
        else:
            resp_body = None
        self._extract_service_catalog(resp_body)

    def _authenticate_noauth(self):
        if not self.endpoint_url:
            message = _('For "noauth" authentication strategy, the endpoint '
                        'must be specified either in the constructor or '
                        'using --os-url')
            raise exceptions.Unauthorized(message=message)

    def authenticate(self):
        if self.auth_strategy == 'keystone':
            self._authenticate_keystone()
        elif self.auth_strategy == 'noauth':
            self._authenticate_noauth()
        else:
            err_msg = _('Unknown auth strategy: %s') % self.auth_strategy
            raise exceptions.Unauthorized(message=err_msg)

    def _get_endpoint_url(self):
        if self.auth_url is None:
            raise exceptions.NoAuthURLProvided()

        url = self.auth_url + '/tokens/%s/endpoints' % self.auth_token
        try:
            resp, body = self._cs_request(url, "GET")
        except exceptions.Unauthorized:
            # rollback to authenticate() to handle case when neutron client
            # is initialized just before the token is expired
            self.authenticate()
            return self.endpoint_url

        body = json.loads(body)
        for endpoint in body.get('endpoints', []):
            if (endpoint['type'] == 'network' and
                endpoint.get('region') == self.region_name):
                if self.endpoint_type not in endpoint:
                    raise exceptions.EndpointTypeNotFound(
                        type_=self.endpoint_type)
                return endpoint[self.endpoint_type]

        raise exceptions.EndpointNotFound()

    def get_auth_info(self):
        return {'auth_token': self.auth_token,
                'auth_tenant_id': self.auth_tenant_id,
                'auth_user_id': self.auth_user_id,
                'endpoint_url': self.endpoint_url}

    def get_status_code(self, response):
        """Returns the integer status code from the response.

        Either a Webob.Response (used in testing) or requests.Response
        is returned.
        """
        if hasattr(response, 'status_int'):
            return response.status_int
        else:
            return response.status_code

########NEW FILE########
__FILENAME__ = clientmanager
# Copyright 2012 OpenStack Foundation.
# All Rights Reserved
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.
#

"""Manage access to the clients, including authenticating when needed.
"""

import logging

from neutronclient import client
from neutronclient.neutron import client as neutron_client


LOG = logging.getLogger(__name__)


class ClientCache(object):
    """Descriptor class for caching created client handles.
    """

    def __init__(self, factory):
        self.factory = factory
        self._handle = None

    def __get__(self, instance, owner):
        # Tell the ClientManager to login to keystone
        if self._handle is None:
            self._handle = self.factory(instance)
        return self._handle


class ClientManager(object):
    """Manages access to API clients, including authentication.
    """
    neutron = ClientCache(neutron_client.make_client)
    # Provide support for old quantum commands (for example
    # in stable versions)
    quantum = neutron

    def __init__(self, token=None, url=None,
                 auth_url=None,
                 endpoint_type=None,
                 tenant_name=None,
                 tenant_id=None,
                 username=None,
                 user_id=None,
                 password=None,
                 region_name=None,
                 api_version=None,
                 auth_strategy=None,
                 insecure=False,
                 ca_cert=None,
                 log_credentials=False,
                 service_type=None,
                 ):
        self._token = token
        self._url = url
        self._auth_url = auth_url
        self._service_type = service_type
        self._endpoint_type = endpoint_type
        self._tenant_name = tenant_name
        self._tenant_id = tenant_id
        self._username = username
        self._user_id = user_id
        self._password = password
        self._region_name = region_name
        self._api_version = api_version
        self._service_catalog = None
        self._auth_strategy = auth_strategy
        self._insecure = insecure
        self._ca_cert = ca_cert
        self._log_credentials = log_credentials
        return

    def initialize(self):
        if not self._url:
            httpclient = client.HTTPClient(
                username=self._username,
                user_id=self._user_id,
                tenant_name=self._tenant_name,
                tenant_id=self._tenant_id,
                password=self._password,
                region_name=self._region_name,
                auth_url=self._auth_url,
                service_type=self._service_type,
                endpoint_type=self._endpoint_type,
                insecure=self._insecure,
                ca_cert=self._ca_cert,
                log_credentials=self._log_credentials)
            httpclient.authenticate()
            # Populate other password flow attributes
            self._token = httpclient.auth_token
            self._url = httpclient.endpoint_url

########NEW FILE########
__FILENAME__ = command
# Copyright 2012 OpenStack Foundation.
# All Rights Reserved
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.
#

"""
OpenStack base command
"""

from cliff import command


class OpenStackCommand(command.Command):
    """Base class for OpenStack commands
    """

    api = None

    def run(self, parsed_args):
        if not self.api:
            return
        else:
            return super(OpenStackCommand, self).run(parsed_args)

    def get_data(self, parsed_args):
        pass

    def take_action(self, parsed_args):
        return self.get_data(parsed_args)

########NEW FILE########
__FILENAME__ = constants
# Copyright (c) 2012 OpenStack Foundation.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.


EXT_NS = '_extension_ns'
XML_NS_V20 = 'http://openstack.org/quantum/api/v2.0'
XSI_NAMESPACE = "http://www.w3.org/2001/XMLSchema-instance"
XSI_ATTR = "xsi:nil"
XSI_NIL_ATTR = "xmlns:xsi"
TYPE_XMLNS = "xmlns:quantum"
TYPE_ATTR = "quantum:type"
VIRTUAL_ROOT_KEY = "_v_root"
ATOM_NAMESPACE = "http://www.w3.org/2005/Atom"
ATOM_XMLNS = "xmlns:atom"
ATOM_LINK_NOTATION = "{%s}link" % ATOM_NAMESPACE

TYPE_BOOL = "bool"
TYPE_INT = "int"
TYPE_LONG = "long"
TYPE_FLOAT = "float"
TYPE_LIST = "list"
TYPE_DICT = "dict"

PLURALS = {'networks': 'network',
           'ports': 'port',
           'subnets': 'subnet',
           'dns_nameservers': 'dns_nameserver',
           'host_routes': 'host_route',
           'allocation_pools': 'allocation_pool',
           'fixed_ips': 'fixed_ip',
           'extensions': 'extension'}

########NEW FILE########
__FILENAME__ = exceptions
# Copyright 2011 VMware, Inc
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

from neutronclient.common import _

"""
Neutron base exception handling.

Exceptions are classified into three categories:
* Exceptions corresponding to exceptions from neutron server:
  This type of exceptions should inherit one of exceptions
  in HTTP_EXCEPTION_MAP.
* Exceptions from client library:
  This type of exceptions should inherit NeutronClientException.
* Exceptions from CLI code:
  This type of exceptions should inherit NeutronCLIError.
"""


class NeutronException(Exception):
    """Base Neutron Exception

    To correctly use this class, inherit from it and define
    a 'message' property. That message will get printf'd
    with the keyword arguments provided to the constructor.

    """
    message = _("An unknown exception occurred.")

    def __init__(self, message=None, **kwargs):
        if message:
            self.message = message
        try:
            self._error_string = self.message % kwargs
        except Exception:
            # at least get the core message out if something happened
            self._error_string = self.message

    def __str__(self):
        return self._error_string


class NeutronClientException(NeutronException):
    """Base exception which exceptions from Neutron are mapped into.

    NOTE: on the client side, we use different exception types in order
    to allow client library users to handle server exceptions in try...except
    blocks. The actual error message is the one generated on the server side.
    """

    def __init__(self, message=None, **kwargs):
        if 'status_code' in kwargs:
            self.status_code = kwargs['status_code']
        super(NeutronClientException, self).__init__(message, **kwargs)


# Base exceptions from Neutron

class BadRequest(NeutronClientException):
    status_code = 400


class Unauthorized(NeutronClientException):
    status_code = 401
    message = _("Unauthorized: bad credentials.")


class Forbidden(NeutronClientException):
    status_code = 403
    message = _("Forbidden: your credentials don't give you access to this "
                "resource.")


class NotFound(NeutronClientException):
    status_code = 404


class Conflict(NeutronClientException):
    status_code = 409


class InternalServerError(NeutronClientException):
    status_code = 500


class ServiceUnavailable(NeutronClientException):
    status_code = 503


HTTP_EXCEPTION_MAP = {
    400: BadRequest,
    401: Unauthorized,
    403: Forbidden,
    404: NotFound,
    409: Conflict,
    500: InternalServerError,
    503: ServiceUnavailable,
}


# Exceptions mapped to Neutron server exceptions
# These are defined if a user of client library needs specific exception.
# Exception name should be <Neutron Exception Name> + 'Client'
# e.g., NetworkNotFound -> NetworkNotFoundClient

class NetworkNotFoundClient(NotFound):
    pass


class PortNotFoundClient(NotFound):
    pass


class StateInvalidClient(BadRequest):
    pass


class NetworkInUseClient(Conflict):
    pass


class PortInUseClient(Conflict):
    pass


class IpAddressInUseClient(Conflict):
    pass


# TODO(amotoki): It is unused in Neutron, but it is referred to
# in Horizon code. After Horizon code is updated, remove it.
class AlreadyAttachedClient(Conflict):
    pass


class IpAddressGenerationFailureClient(Conflict):
    pass


class ExternalIpAddressExhaustedClient(BadRequest):
    pass


# Exceptions from client library

class NoAuthURLProvided(Unauthorized):
    message = _("auth_url was not provided to the Neutron client")


class EndpointNotFound(NeutronClientException):
    message = _("Could not find Service or Region in Service Catalog.")


class EndpointTypeNotFound(NeutronClientException):
    message = _("Could not find endpoint type %(type_)s in Service Catalog.")


class AmbiguousEndpoints(NeutronClientException):
    message = _("Found more than one matching endpoint in Service Catalog: "
                "%(matching_endpoints)")


class RequestURITooLong(NeutronClientException):
    """Raised when a request fails with HTTP error 414."""

    def __init__(self, **kwargs):
        self.excess = kwargs.get('excess', 0)
        super(RequestURITooLong, self).__init__(**kwargs)


class ConnectionFailed(NeutronClientException):
    message = _("Connection to neutron failed: %(reason)s")


class SslCertificateValidationError(NeutronClientException):
    message = _("SSL certificate validation has failed: %(reason)s")


class MalformedResponseBody(NeutronClientException):
    message = _("Malformed response body: %(reason)s")


class InvalidContentType(NeutronClientException):
    message = _("Invalid content type %(content_type)s.")


# Command line exceptions

class NeutronCLIError(NeutronException):
    """Exception raised when command line parsing fails."""
    pass


class CommandError(NeutronCLIError):
    pass


class UnsupportedVersion(NeutronCLIError):
    """Indicates that the user is trying to use an unsupported
       version of the API
    """
    pass


class NeutronClientNoUniqueMatch(NeutronCLIError):
    message = _("Multiple %(resource)s matches found for name '%(name)s',"
                " use an ID to be more specific.")

########NEW FILE########
__FILENAME__ = serializer
# Copyright 2013 OpenStack Foundation.
# All Rights Reserved
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.
#
###
### Codes from neutron wsgi
###

import logging

from xml.etree import ElementTree as etree
from xml.parsers import expat

from neutronclient.common import constants
from neutronclient.common import exceptions as exception
from neutronclient.openstack.common.gettextutils import _
from neutronclient.openstack.common import jsonutils

LOG = logging.getLogger(__name__)


class ActionDispatcher(object):
    """Maps method name to local methods through action name."""

    def dispatch(self, *args, **kwargs):
        """Find and call local method."""
        action = kwargs.pop('action', 'default')
        action_method = getattr(self, str(action), self.default)
        return action_method(*args, **kwargs)

    def default(self, data):
        raise NotImplementedError()


class DictSerializer(ActionDispatcher):
    """Default request body serialization."""

    def serialize(self, data, action='default'):
        return self.dispatch(data, action=action)

    def default(self, data):
        return ""


class JSONDictSerializer(DictSerializer):
    """Default JSON request body serialization."""

    def default(self, data):
        def sanitizer(obj):
            return unicode(obj)
        return jsonutils.dumps(data, default=sanitizer)


class XMLDictSerializer(DictSerializer):

    def __init__(self, metadata=None, xmlns=None):
        """XMLDictSerializer constructor.

        :param metadata: information needed to deserialize xml into
                         a dictionary.
        :param xmlns: XML namespace to include with serialized xml
        """
        super(XMLDictSerializer, self).__init__()
        self.metadata = metadata or {}
        if not xmlns:
            xmlns = self.metadata.get('xmlns')
        if not xmlns:
            xmlns = constants.XML_NS_V20
        self.xmlns = xmlns

    def default(self, data):
        """Default serializer of XMLDictSerializer.

        :param data: expect data to contain a single key as XML root, or
                     contain another '*_links' key as atom links. Other
                     case will use 'VIRTUAL_ROOT_KEY' as XML root.
        """
        try:
            links = None
            has_atom = False
            if data is None:
                root_key = constants.VIRTUAL_ROOT_KEY
                root_value = None
            else:
                link_keys = [k for k in data.iterkeys() or []
                             if k.endswith('_links')]
                if link_keys:
                    links = data.pop(link_keys[0], None)
                    has_atom = True
                root_key = (len(data) == 1 and
                            data.keys()[0] or constants.VIRTUAL_ROOT_KEY)
                root_value = data.get(root_key, data)
            doc = etree.Element("_temp_root")
            used_prefixes = []
            self._to_xml_node(doc, self.metadata, root_key,
                              root_value, used_prefixes)
            if links:
                self._create_link_nodes(list(doc)[0], links)
            return self.to_xml_string(list(doc)[0], used_prefixes, has_atom)
        except AttributeError as e:
            LOG.exception(str(e))
            return ''

    def __call__(self, data):
        # Provides a migration path to a cleaner WSGI layer, this
        # "default" stuff and extreme extensibility isn't being used
        # like originally intended
        return self.default(data)

    def to_xml_string(self, node, used_prefixes, has_atom=False):
        self._add_xmlns(node, used_prefixes, has_atom)
        return etree.tostring(node, encoding='UTF-8')

    #NOTE (ameade): the has_atom should be removed after all of the
    # xml serializers and view builders have been updated to the current
    # spec that required all responses include the xmlns:atom, the has_atom
    # flag is to prevent current tests from breaking
    def _add_xmlns(self, node, used_prefixes, has_atom=False):
        node.set('xmlns', self.xmlns)
        node.set(constants.TYPE_XMLNS, self.xmlns)
        if has_atom:
            node.set(constants.ATOM_XMLNS, constants.ATOM_NAMESPACE)
        node.set(constants.XSI_NIL_ATTR, constants.XSI_NAMESPACE)
        ext_ns = self.metadata.get(constants.EXT_NS, {})
        for prefix in used_prefixes:
            if prefix in ext_ns:
                node.set('xmlns:' + prefix, ext_ns[prefix])

    def _to_xml_node(self, parent, metadata, nodename, data, used_prefixes):
        """Recursive method to convert data members to XML nodes."""
        result = etree.SubElement(parent, nodename)
        if ":" in nodename:
            used_prefixes.append(nodename.split(":", 1)[0])
        #TODO(bcwaldon): accomplish this without a type-check
        if isinstance(data, list):
            if not data:
                result.set(
                    constants.TYPE_ATTR,
                    constants.TYPE_LIST)
                return result
            singular = metadata.get('plurals', {}).get(nodename, None)
            if singular is None:
                if nodename.endswith('s'):
                    singular = nodename[:-1]
                else:
                    singular = 'item'
            for item in data:
                self._to_xml_node(result, metadata, singular, item,
                                  used_prefixes)
        #TODO(bcwaldon): accomplish this without a type-check
        elif isinstance(data, dict):
            if not data:
                result.set(
                    constants.TYPE_ATTR,
                    constants.TYPE_DICT)
                return result
            attrs = metadata.get('attributes', {}).get(nodename, {})
            for k, v in sorted(data.items()):
                if k in attrs:
                    result.set(k, str(v))
                else:
                    self._to_xml_node(result, metadata, k, v,
                                      used_prefixes)
        elif data is None:
            result.set(constants.XSI_ATTR, 'true')
        else:
            if isinstance(data, bool):
                result.set(
                    constants.TYPE_ATTR,
                    constants.TYPE_BOOL)
            elif isinstance(data, int):
                result.set(
                    constants.TYPE_ATTR,
                    constants.TYPE_INT)
            elif isinstance(data, long):
                result.set(
                    constants.TYPE_ATTR,
                    constants.TYPE_LONG)
            elif isinstance(data, float):
                result.set(
                    constants.TYPE_ATTR,
                    constants.TYPE_FLOAT)
            LOG.debug(_("Data %(data)s type is %(type)s"),
                      {'data': data,
                       'type': type(data)})
            if isinstance(data, str):
                result.text = unicode(data, 'utf-8')
            else:
                result.text = unicode(data)
        return result

    def _create_link_nodes(self, xml_doc, links):
        for link in links:
            link_node = etree.SubElement(xml_doc, 'atom:link')
            link_node.set('rel', link['rel'])
            link_node.set('href', link['href'])


class TextDeserializer(ActionDispatcher):
    """Default request body deserialization."""

    def deserialize(self, datastring, action='default'):
        return self.dispatch(datastring, action=action)

    def default(self, datastring):
        return {}


class JSONDeserializer(TextDeserializer):

    def _from_json(self, datastring):
        try:
            return jsonutils.loads(datastring)
        except ValueError:
            msg = _("Cannot understand JSON")
            raise exception.MalformedResponseBody(reason=msg)

    def default(self, datastring):
        return {'body': self._from_json(datastring)}


class XMLDeserializer(TextDeserializer):

    def __init__(self, metadata=None):
        """XMLDeserializer constructor.

        :param metadata: information needed to deserialize xml into
                         a dictionary.
        """
        super(XMLDeserializer, self).__init__()
        self.metadata = metadata or {}
        xmlns = self.metadata.get('xmlns')
        if not xmlns:
            xmlns = constants.XML_NS_V20
        self.xmlns = xmlns

    def _get_key(self, tag):
        tags = tag.split("}", 1)
        if len(tags) == 2:
            ns = tags[0][1:]
            bare_tag = tags[1]
            ext_ns = self.metadata.get(constants.EXT_NS, {})
            if ns == self.xmlns:
                return bare_tag
            for prefix, _ns in ext_ns.items():
                if ns == _ns:
                    return prefix + ":" + bare_tag
        else:
            return tag

    def _get_links(self, root_tag, node):
        link_nodes = node.findall(constants.ATOM_LINK_NOTATION)
        root_tag = self._get_key(node.tag)
        link_key = "%s_links" % root_tag
        link_list = []
        for link in link_nodes:
            link_list.append({'rel': link.get('rel'),
                              'href': link.get('href')})
            # Remove link node in order to avoid link node being
            # processed as an item in _from_xml_node
            node.remove(link)
        return link_list and {link_key: link_list} or {}

    def _from_xml(self, datastring):
        if datastring is None:
            return None
        plurals = set(self.metadata.get('plurals', {}))
        try:
            node = etree.fromstring(datastring)
            root_tag = self._get_key(node.tag)
            links = self._get_links(root_tag, node)
            result = self._from_xml_node(node, plurals)
            # There is no case where root_tag = constants.VIRTUAL_ROOT_KEY
            # and links is not None because of the way data are serialized
            if root_tag == constants.VIRTUAL_ROOT_KEY:
                return result
            return dict({root_tag: result}, **links)
        except Exception as e:
            parseError = False
            # Python2.7
            if (hasattr(etree, 'ParseError') and
                isinstance(e, getattr(etree, 'ParseError'))):
                parseError = True
            # Python2.6
            elif isinstance(e, expat.ExpatError):
                parseError = True
            if parseError:
                msg = _("Cannot understand XML")
                raise exception.MalformedResponseBody(reason=msg)
            else:
                raise

    def _from_xml_node(self, node, listnames):
        """Convert a minidom node to a simple Python type.

        :param node: minidom node name
        :param listnames: list of XML node names whose subnodes should
                          be considered list items.

        """
        attrNil = node.get(str(etree.QName(constants.XSI_NAMESPACE, "nil")))
        attrType = node.get(str(etree.QName(
            self.metadata.get('xmlns'), "type")))
        if (attrNil and attrNil.lower() == 'true'):
            return None
        elif not len(node) and not node.text:
            if (attrType and attrType == constants.TYPE_DICT):
                return {}
            elif (attrType and attrType == constants.TYPE_LIST):
                return []
            else:
                return ''
        elif (len(node) == 0 and node.text):
            converters = {constants.TYPE_BOOL:
                          lambda x: x.lower() == 'true',
                          constants.TYPE_INT:
                          lambda x: int(x),
                          constants.TYPE_LONG:
                          lambda x: long(x),
                          constants.TYPE_FLOAT:
                          lambda x: float(x)}
            if attrType and attrType in converters:
                return converters[attrType](node.text)
            else:
                return node.text
        elif self._get_key(node.tag) in listnames:
            return [self._from_xml_node(n, listnames) for n in node]
        else:
            result = dict()
            for attr in node.keys():
                if (attr == 'xmlns' or
                    attr.startswith('xmlns:') or
                    attr == constants.XSI_ATTR or
                    attr == constants.TYPE_ATTR):
                    continue
                result[self._get_key(attr)] = node.get(attr)
            children = list(node)
            for child in children:
                result[self._get_key(child.tag)] = self._from_xml_node(
                    child, listnames)
            return result

    def default(self, datastring):
        return {'body': self._from_xml(datastring)}

    def __call__(self, datastring):
        # Adding a migration path to allow us to remove unncessary classes
        return self.default(datastring)


# NOTE(maru): this class is duplicated from neutron.wsgi
class Serializer(object):
    """Serializes and deserializes dictionaries to certain MIME types."""

    def __init__(self, metadata=None, default_xmlns=None):
        """Create a serializer based on the given WSGI environment.

        'metadata' is an optional dict mapping MIME types to information
        needed to serialize a dictionary to that type.

        """
        self.metadata = metadata or {}
        self.default_xmlns = default_xmlns

    def _get_serialize_handler(self, content_type):
        handlers = {
            'application/json': JSONDictSerializer(),
            'application/xml': XMLDictSerializer(self.metadata),
        }

        try:
            return handlers[content_type]
        except Exception:
            raise exception.InvalidContentType(content_type=content_type)

    def serialize(self, data, content_type):
        """Serialize a dictionary into the specified content type."""
        return self._get_serialize_handler(content_type).serialize(data)

    def deserialize(self, datastring, content_type):
        """Deserialize a string to a dictionary.

        The string must be in the format of a supported MIME type.

        """
        return self.get_deserialize_handler(content_type).deserialize(
            datastring)

    def get_deserialize_handler(self, content_type):
        handlers = {
            'application/json': JSONDeserializer(),
            'application/xml': XMLDeserializer(self.metadata),
        }

        try:
            return handlers[content_type]
        except Exception:
            raise exception.InvalidContentType(content_type=content_type)

########NEW FILE########
__FILENAME__ = utils
# Copyright 2011, VMware, Inc.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.
#
# Borrowed from nova code base, more utilities will be added/borrowed as and
# when needed.

"""Utilities and helper functions."""

import datetime
import json
import logging
import os
import sys

from neutronclient.common import _
from neutronclient.common import exceptions
from neutronclient.openstack.common import strutils


def env(*vars, **kwargs):
    """Returns the first environment variable set.

    if none are non-empty, defaults to '' or keyword arg default.
    """
    for v in vars:
        value = os.environ.get(v)
        if value:
            return value
    return kwargs.get('default', '')


def to_primitive(value):
    if isinstance(value, list) or isinstance(value, tuple):
        o = []
        for v in value:
            o.append(to_primitive(v))
        return o
    elif isinstance(value, dict):
        o = {}
        for k, v in value.iteritems():
            o[k] = to_primitive(v)
        return o
    elif isinstance(value, datetime.datetime):
        return str(value)
    elif hasattr(value, 'iteritems'):
        return to_primitive(dict(value.iteritems()))
    elif hasattr(value, '__iter__'):
        return to_primitive(list(value))
    else:
        return value


def dumps(value, indent=None):
    try:
        return json.dumps(value, indent=indent)
    except TypeError:
        pass
    return json.dumps(to_primitive(value))


def loads(s):
    return json.loads(s)


def import_class(import_str):
    """Returns a class from a string including module and class.

    :param import_str: a string representation of the class name
    :rtype: the requested class
    """
    mod_str, _sep, class_str = import_str.rpartition('.')
    __import__(mod_str)
    return getattr(sys.modules[mod_str], class_str)


def get_client_class(api_name, version, version_map):
    """Returns the client class for the requested API version

    :param api_name: the name of the API, e.g. 'compute', 'image', etc
    :param version: the requested API version
    :param version_map: a dict of client classes keyed by version
    :rtype: a client class for the requested API version
    """
    try:
        client_path = version_map[str(version)]
    except (KeyError, ValueError):
        msg = _("Invalid %(api_name)s client version '%(version)s'. must be "
                "one of: %(map_keys)s")
        msg = msg % {'api_name': api_name, 'version': version,
                     'map_keys': ', '.join(version_map.keys())}
        raise exceptions.UnsupportedVersion(msg)

    return import_class(client_path)


def get_item_properties(item, fields, mixed_case_fields=[], formatters={}):
    """Return a tuple containing the item properties.

    :param item: a single item resource (e.g. Server, Tenant, etc)
    :param fields: tuple of strings with the desired field names
    :param mixed_case_fields: tuple of field names to preserve case
    :param formatters: dictionary mapping field names to callables
       to format the values
    """
    row = []

    for field in fields:
        if field in formatters:
            row.append(formatters[field](item))
        else:
            if field in mixed_case_fields:
                field_name = field.replace(' ', '_')
            else:
                field_name = field.lower().replace(' ', '_')
            if not hasattr(item, field_name) and isinstance(item, dict):
                data = item[field_name]
            else:
                data = getattr(item, field_name, '')
            if data is None:
                data = ''
            row.append(data)
    return tuple(row)


def str2bool(strbool):
    if strbool is None:
        return None
    else:
        return strbool.lower() == 'true'


def str2dict(strdict):
        '''Convert key1=value1,key2=value2,... string into dictionary.

        :param strdict: key1=value1,key2=value2
        '''
        _info = {}
        if not strdict:
            return _info
        for kv_str in strdict.split(","):
            k, v = kv_str.split("=", 1)
            _info.update({k: v})
        return _info


def http_log_req(_logger, args, kwargs):
    if not _logger.isEnabledFor(logging.DEBUG):
        return

    string_parts = ['curl -i']
    for element in args:
        if element in ('GET', 'POST', 'DELETE', 'PUT'):
            string_parts.append(' -X %s' % element)
        else:
            string_parts.append(' %s' % element)

    for element in kwargs['headers']:
        header = ' -H "%s: %s"' % (element, kwargs['headers'][element])
        string_parts.append(header)

    if 'body' in kwargs and kwargs['body']:
        string_parts.append(" -d '%s'" % (kwargs['body']))
    string_parts = safe_encode_list(string_parts)
    _logger.debug(_("\nREQ: %s\n"), "".join(string_parts))


def http_log_resp(_logger, resp, body):
    if not _logger.isEnabledFor(logging.DEBUG):
        return
    _logger.debug(_("RESP:%(code)s %(headers)s %(body)s\n"),
                  {'code': resp.status_code,
                   'headers': resp.headers,
                   'body': body})


def _safe_encode_without_obj(data):
    if isinstance(data, basestring):
        return strutils.safe_encode(data)
    return data


def safe_encode_list(data):
    return map(_safe_encode_without_obj, data)


def safe_encode_dict(data):
    def _encode_item((k, v)):
        if isinstance(v, list):
            return (k, safe_encode_list(v))
        elif isinstance(v, dict):
            return (k, safe_encode_dict(v))
        return (k, _safe_encode_without_obj(v))

    return dict(map(_encode_item, data.items()))

########NEW FILE########
__FILENAME__ = validators
# Copyright 2014 NEC Corporation
# All Rights Reserved
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import netaddr

from neutronclient.common import exceptions
from neutronclient.openstack.common.gettextutils import _


def validate_int_range(parsed_args, attr_name, min_value=None, max_value=None):
    val = getattr(parsed_args, attr_name, None)
    if val is None:
        return
    try:
        if not isinstance(val, int):
            int_val = int(val, 0)
        else:
            int_val = val
        if ((min_value is None or min_value <= int_val) and
            (max_value is None or int_val <= max_value)):
            return
    except (ValueError, TypeError):
        pass

    if min_value is not None and max_value is not None:
        msg = (_('%(attr_name)s "%(val)s" should be an integer '
                 '[%(min)i:%(max)i].') %
               {'attr_name': attr_name.replace('_', '-'),
                'val': val, 'min': min_value, 'max': max_value})
    elif min_value is not None:
        msg = (_('%(attr_name)s "%(val)s" should be an integer '
                 'greater than or equal to %(min)i.') %
               {'attr_name': attr_name.replace('_', '-'),
                'val': val, 'min': min_value})
    elif max_value is not None:
        msg = (_('%(attr_name)s "%(val)s" should be an integer '
                 'smaller than or equal to %(max)i.') %
               {'attr_name': attr_name.replace('_', '-'),
                'val': val, 'max': max_value})
    else:
        msg = (_('%(attr_name)s "%(val)s" should be an integer.') %
               {'attr_name': attr_name.replace('_', '-'),
                'val': val})

    raise exceptions.CommandError(msg)


def validate_ip_subnet(parsed_args, attr_name):
    val = getattr(parsed_args, attr_name)
    if not val:
        return
    try:
        netaddr.IPNetwork(val)
    except (netaddr.AddrFormatError, ValueError):
        raise exceptions.CommandError(
            (_('%(attr_name)s "%(val)s" is not a valid CIDR.') %
             {'attr_name': attr_name.replace('_', '-'), 'val': val}))

########NEW FILE########
__FILENAME__ = client
# Copyright 2012 OpenStack Foundation.
# All Rights Reserved
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.
#

from neutronclient.common import exceptions
from neutronclient.common import utils
from neutronclient.openstack.common.gettextutils import _


API_NAME = 'network'
API_VERSIONS = {
    '2.0': 'neutronclient.v2_0.client.Client',
}


def make_client(instance):
    """Returns an neutron client.
    """
    neutron_client = utils.get_client_class(
        API_NAME,
        instance._api_version[API_NAME],
        API_VERSIONS,
    )
    instance.initialize()
    url = instance._url
    url = url.rstrip("/")
    if '2.0' == instance._api_version[API_NAME]:
        client = neutron_client(username=instance._username,
                                tenant_name=instance._tenant_name,
                                password=instance._password,
                                region_name=instance._region_name,
                                auth_url=instance._auth_url,
                                endpoint_url=url,
                                token=instance._token,
                                auth_strategy=instance._auth_strategy,
                                insecure=instance._insecure,
                                ca_cert=instance._ca_cert)
        return client
    else:
        raise exceptions.UnsupportedVersion(_("API version %s is not "
                                              "supported") %
                                            instance._api_version[API_NAME])


def Client(api_version, *args, **kwargs):
    """Return an neutron client.
    @param api_version: only 2.0 is supported now
    """
    neutron_client = utils.get_client_class(
        API_NAME,
        api_version,
        API_VERSIONS,
    )
    return neutron_client(*args, **kwargs)

########NEW FILE########
__FILENAME__ = agent
# Copyright 2013 OpenStack Foundation.
# All Rights Reserved
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.
#

import logging

from neutronclient.neutron import v2_0 as neutronV20


def _format_timestamp(component):
    try:
        return component['heartbeat_timestamp'].split(".", 2)[0]
    except Exception:
        return ''


class ListAgent(neutronV20.ListCommand):
    """List agents."""

    resource = 'agent'
    log = logging.getLogger(__name__ + '.ListAgent')
    list_columns = ['id', 'agent_type', 'host', 'alive', 'admin_state_up']
    _formatters = {'heartbeat_timestamp': _format_timestamp}
    sorting_support = True

    def extend_list(self, data, parsed_args):
        for agent in data:
            if 'alive' in agent:
                agent['alive'] = ":-)" if agent['alive'] else 'xxx'


class ShowAgent(neutronV20.ShowCommand):
    """Show information of a given agent."""

    resource = 'agent'
    log = logging.getLogger(__name__ + '.ShowAgent')
    allow_names = False
    json_indent = 5


class DeleteAgent(neutronV20.DeleteCommand):
    """Delete a given agent."""

    log = logging.getLogger(__name__ + '.DeleteAgent')
    resource = 'agent'
    allow_names = False


class UpdateAgent(neutronV20.UpdateCommand):
    """Update a given agent."""

    log = logging.getLogger(__name__ + '.UpdateAgent')
    resource = 'agent'
    allow_names = False

########NEW FILE########
__FILENAME__ = agentscheduler
# Copyright 2013 OpenStack Foundation.
# All Rights Reserved
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.
#

from __future__ import print_function

import logging

from neutronclient.neutron import v2_0 as neutronV20
from neutronclient.neutron.v2_0 import network
from neutronclient.neutron.v2_0 import router
from neutronclient.openstack.common.gettextutils import _


PERFECT_TIME_FORMAT = "%Y-%m-%dT%H:%M:%S.%f"


class AddNetworkToDhcpAgent(neutronV20.NeutronCommand):
    """Add a network to a DHCP agent."""

    log = logging.getLogger(__name__ + '.AddNetworkToDhcpAgent')

    def get_parser(self, prog_name):
        parser = super(AddNetworkToDhcpAgent, self).get_parser(prog_name)
        parser.add_argument(
            'dhcp_agent',
            help=_('ID of the DHCP agent'))
        parser.add_argument(
            'network',
            help=_('Network to add'))
        return parser

    def run(self, parsed_args):
        self.log.debug('run(%s)' % parsed_args)
        neutron_client = self.get_client()
        neutron_client.format = parsed_args.request_format
        _net_id = neutronV20.find_resourceid_by_name_or_id(
            neutron_client, 'network', parsed_args.network)
        neutron_client.add_network_to_dhcp_agent(parsed_args.dhcp_agent,
                                                 {'network_id': _net_id})
        print(_('Added network %s to DHCP agent') % parsed_args.network,
              file=self.app.stdout)


class RemoveNetworkFromDhcpAgent(neutronV20.NeutronCommand):
    """Remove a network from a DHCP agent."""
    log = logging.getLogger(__name__ + '.RemoveNetworkFromDhcpAgent')

    def get_parser(self, prog_name):
        parser = super(RemoveNetworkFromDhcpAgent, self).get_parser(prog_name)
        parser.add_argument(
            'dhcp_agent',
            help=_('ID of the DHCP agent'))
        parser.add_argument(
            'network',
            help=_('Network to remove'))
        return parser

    def run(self, parsed_args):
        self.log.debug('run(%s)' % parsed_args)
        neutron_client = self.get_client()
        neutron_client.format = parsed_args.request_format
        _net_id = neutronV20.find_resourceid_by_name_or_id(
            neutron_client, 'network', parsed_args.network)
        neutron_client.remove_network_from_dhcp_agent(
            parsed_args.dhcp_agent, _net_id)
        print(_('Removed network %s to DHCP agent') % parsed_args.network,
              file=self.app.stdout)


class ListNetworksOnDhcpAgent(network.ListNetwork):
    """List the networks on a DHCP agent."""

    log = logging.getLogger(__name__ + '.ListNetworksOnDhcpAgent')
    unknown_parts_flag = False

    def get_parser(self, prog_name):
        parser = super(ListNetworksOnDhcpAgent,
                       self).get_parser(prog_name)
        parser.add_argument(
            'dhcp_agent',
            help=_('ID of the DHCP agent'))
        return parser

    def call_server(self, neutron_client, search_opts, parsed_args):
        data = neutron_client.list_networks_on_dhcp_agent(
            parsed_args.dhcp_agent, **search_opts)
        return data


class ListDhcpAgentsHostingNetwork(neutronV20.ListCommand):
    """List DHCP agents hosting a network."""

    resource = 'agent'
    _formatters = {}
    log = logging.getLogger(__name__ + '.ListDhcpAgentsHostingNetwork')
    list_columns = ['id', 'host', 'admin_state_up', 'alive']
    unknown_parts_flag = False

    def get_parser(self, prog_name):
        parser = super(ListDhcpAgentsHostingNetwork,
                       self).get_parser(prog_name)
        parser.add_argument(
            'network',
            help=_('Network to query'))
        return parser

    def extend_list(self, data, parsed_args):
        for agent in data:
            agent['alive'] = ":-)" if agent['alive'] else 'xxx'

    def call_server(self, neutron_client, search_opts, parsed_args):
        _id = neutronV20.find_resourceid_by_name_or_id(neutron_client,
                                                       'network',
                                                       parsed_args.network)
        search_opts['network'] = _id
        data = neutron_client.list_dhcp_agent_hosting_networks(**search_opts)
        return data


class AddRouterToL3Agent(neutronV20.NeutronCommand):
    """Add a router to a L3 agent."""

    log = logging.getLogger(__name__ + '.AddRouterToL3Agent')

    def get_parser(self, prog_name):
        parser = super(AddRouterToL3Agent, self).get_parser(prog_name)
        parser.add_argument(
            'l3_agent',
            help=_('ID of the L3 agent'))
        parser.add_argument(
            'router',
            help=_('Router to add'))
        return parser

    def run(self, parsed_args):
        self.log.debug('run(%s)' % parsed_args)
        neutron_client = self.get_client()
        neutron_client.format = parsed_args.request_format
        _id = neutronV20.find_resourceid_by_name_or_id(
            neutron_client, 'router', parsed_args.router)
        neutron_client.add_router_to_l3_agent(parsed_args.l3_agent,
                                              {'router_id': _id})
        print(_('Added router %s to L3 agent') % parsed_args.router,
              file=self.app.stdout)


class RemoveRouterFromL3Agent(neutronV20.NeutronCommand):
    """Remove a router from a L3 agent."""

    log = logging.getLogger(__name__ + '.RemoveRouterFromL3Agent')

    def get_parser(self, prog_name):
        parser = super(RemoveRouterFromL3Agent, self).get_parser(prog_name)
        parser.add_argument(
            'l3_agent',
            help=_('ID of the L3 agent'))
        parser.add_argument(
            'router',
            help=_('Router to remove'))
        return parser

    def run(self, parsed_args):
        self.log.debug('run(%s)' % parsed_args)
        neutron_client = self.get_client()
        neutron_client.format = parsed_args.request_format
        _id = neutronV20.find_resourceid_by_name_or_id(
            neutron_client, 'router', parsed_args.router)
        neutron_client.remove_router_from_l3_agent(
            parsed_args.l3_agent, _id)
        print(_('Removed Router %s to L3 agent') % parsed_args.router,
              file=self.app.stdout)


class ListRoutersOnL3Agent(neutronV20.ListCommand):
    """List the routers on a L3 agent."""

    log = logging.getLogger(__name__ + '.ListRoutersOnL3Agent')
    _formatters = {'external_gateway_info':
                   router._format_external_gateway_info}
    list_columns = ['id', 'name', 'external_gateway_info']
    resource = 'router'
    unknown_parts_flag = False

    def get_parser(self, prog_name):
        parser = super(ListRoutersOnL3Agent,
                       self).get_parser(prog_name)
        parser.add_argument(
            'l3_agent',
            help=_('ID of the L3 agent to query'))
        return parser

    def call_server(self, neutron_client, search_opts, parsed_args):
        data = neutron_client.list_routers_on_l3_agent(
            parsed_args.l3_agent, **search_opts)
        return data


class ListL3AgentsHostingRouter(neutronV20.ListCommand):
    """List L3 agents hosting a router."""

    resource = 'agent'
    _formatters = {}
    log = logging.getLogger(__name__ + '.ListL3AgentsHostingRouter')
    list_columns = ['id', 'host', 'admin_state_up', 'alive']
    unknown_parts_flag = False

    def get_parser(self, prog_name):
        parser = super(ListL3AgentsHostingRouter,
                       self).get_parser(prog_name)
        parser.add_argument('router',
                            help=_('Router to query'))
        return parser

    def extend_list(self, data, parsed_args):
        for agent in data:
            agent['alive'] = ":-)" if agent['alive'] else 'xxx'

    def call_server(self, neutron_client, search_opts, parsed_args):
        _id = neutronV20.find_resourceid_by_name_or_id(neutron_client,
                                                       'router',
                                                       parsed_args.router)
        search_opts['router'] = _id
        data = neutron_client.list_l3_agent_hosting_routers(**search_opts)
        return data


class ListPoolsOnLbaasAgent(neutronV20.ListCommand):
    """List the pools on a loadbalancer agent."""

    log = logging.getLogger(__name__ + '.ListPoolsOnLbaasAgent')
    list_columns = ['id', 'name', 'lb_method', 'protocol',
                    'admin_state_up', 'status']
    resource = 'pool'
    unknown_parts_flag = False

    def get_parser(self, prog_name):
        parser = super(ListPoolsOnLbaasAgent, self).get_parser(prog_name)
        parser.add_argument(
            'lbaas_agent',
            help=_('ID of the loadbalancer agent to query'))
        return parser

    def call_server(self, neutron_client, search_opts, parsed_args):
        data = neutron_client.list_pools_on_lbaas_agent(
            parsed_args.lbaas_agent, **search_opts)
        return data


class GetLbaasAgentHostingPool(neutronV20.ListCommand):
    """Get loadbalancer agent hosting a pool.

    Deriving from ListCommand though server will return only one agent
    to keep common output format for all agent schedulers
    """

    resource = 'agent'
    log = logging.getLogger(__name__ + '.GetLbaasAgentHostingPool')
    list_columns = ['id', 'host', 'admin_state_up', 'alive']
    unknown_parts_flag = False

    def get_parser(self, prog_name):
        parser = super(GetLbaasAgentHostingPool,
                       self).get_parser(prog_name)
        parser.add_argument('pool',
                            help=_('Pool to query'))
        return parser

    def extend_list(self, data, parsed_args):
        for agent in data:
            agent['alive'] = ":-)" if agent['alive'] else 'xxx'

    def call_server(self, neutron_client, search_opts, parsed_args):
        _id = neutronV20.find_resourceid_by_name_or_id(neutron_client,
                                                       'pool',
                                                       parsed_args.pool)
        search_opts['pool'] = _id
        agent = neutron_client.get_lbaas_agent_hosting_pool(**search_opts)
        data = {'agents': [agent['agent']]}
        return data

########NEW FILE########
__FILENAME__ = credential
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.
#

import logging

from neutronclient.neutron import v2_0 as neutronV20
from neutronclient.openstack.common.gettextutils import _


class ListCredential(neutronV20.ListCommand):
    """List credentials that belong to a given tenant."""

    resource = 'credential'
    log = logging.getLogger(__name__ + '.ListCredential')
    _formatters = {}
    list_columns = ['credential_id', 'credential_name', 'user_name',
                    'password', 'type']


class ShowCredential(neutronV20.ShowCommand):
    """Show information of a given credential."""

    resource = 'credential'
    log = logging.getLogger(__name__ + '.ShowCredential')
    allow_names = False


class CreateCredential(neutronV20.CreateCommand):
    """Creates a credential."""

    resource = 'credential'
    log = logging.getLogger(__name__ + '.CreateCredential')

    def add_known_arguments(self, parser):
        parser.add_argument(
            'credential_name',
            help=_('Name/Ip address for Credential'))
        parser.add_argument(
            'credential_type',
            help=_('Type of the Credential'))
        parser.add_argument(
            '--username',
            help=_('Username for the credential'))
        parser.add_argument(
            '--password',
            help=_('Password for the credential'))

    def args2body(self, parsed_args):
        body = {'credential': {
            'credential_name': parsed_args.credential_name}}

        if parsed_args.credential_type:
            body['credential'].update({'type':
                                      parsed_args.credential_type})
        if parsed_args.username:
            body['credential'].update({'user_name':
                                      parsed_args.username})
        if parsed_args.password:
            body['credential'].update({'password':
                                      parsed_args.password})
        return body


class DeleteCredential(neutronV20.DeleteCommand):
    """Delete a  given credential."""

    log = logging.getLogger(__name__ + '.DeleteCredential')
    resource = 'credential'
    allow_names = False

########NEW FILE########
__FILENAME__ = extension
# Copyright 2012 OpenStack Foundation.
# All Rights Reserved
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.
#

import logging

from neutronclient.neutron import v2_0 as cmd_base
from neutronclient.openstack.common.gettextutils import _


class ListExt(cmd_base.ListCommand):
    """List all extensions."""

    resource = 'extension'
    log = logging.getLogger(__name__ + '.ListExt')
    list_columns = ['alias', 'name']


class ShowExt(cmd_base.ShowCommand):
    """Show information of a given resource."""

    resource = "extension"
    log = logging.getLogger(__name__ + '.ShowExt')
    allow_names = False

    def get_parser(self, prog_name):
        parser = super(cmd_base.ShowCommand, self).get_parser(prog_name)
        cmd_base.add_show_list_common_argument(parser)
        parser.add_argument(
            'id', metavar='EXT-ALIAS',
            help=_('The extension alias'))
        return parser

########NEW FILE########
__FILENAME__ = floatingip
# Copyright 2012 OpenStack Foundation.
# All Rights Reserved
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.
#

from __future__ import print_function

import argparse
import logging

from neutronclient.neutron import v2_0 as neutronV20
from neutronclient.openstack.common.gettextutils import _


class ListFloatingIP(neutronV20.ListCommand):
    """List floating ips that belong to a given tenant."""

    resource = 'floatingip'
    log = logging.getLogger(__name__ + '.ListFloatingIP')
    list_columns = ['id', 'fixed_ip_address', 'floating_ip_address',
                    'port_id']
    pagination_support = True
    sorting_support = True


class ShowFloatingIP(neutronV20.ShowCommand):
    """Show information of a given floating ip."""

    resource = 'floatingip'
    log = logging.getLogger(__name__ + '.ShowFloatingIP')
    allow_names = False


class CreateFloatingIP(neutronV20.CreateCommand):
    """Create a floating ip for a given tenant."""

    resource = 'floatingip'
    log = logging.getLogger(__name__ + '.CreateFloatingIP')

    def add_known_arguments(self, parser):
        parser.add_argument(
            'floating_network_id', metavar='FLOATING_NETWORK',
            help=_('Network name or id to allocate floating IP from'))
        parser.add_argument(
            '--port-id',
            help=_('ID of the port to be associated with the floatingip'))
        parser.add_argument(
            '--port_id',
            help=argparse.SUPPRESS)
        parser.add_argument(
            '--fixed-ip-address',
            help=_('IP address on the port (only required if port has multiple'
                   'IPs)'))
        parser.add_argument(
            '--fixed_ip_address',
            help=argparse.SUPPRESS)

    def args2body(self, parsed_args):
        _network_id = neutronV20.find_resourceid_by_name_or_id(
            self.get_client(), 'network', parsed_args.floating_network_id)
        body = {self.resource: {'floating_network_id': _network_id}}
        if parsed_args.port_id:
            body[self.resource].update({'port_id': parsed_args.port_id})
        if parsed_args.tenant_id:
            body[self.resource].update({'tenant_id': parsed_args.tenant_id})
        if parsed_args.fixed_ip_address:
            body[self.resource].update({'fixed_ip_address':
                                        parsed_args.fixed_ip_address})
        return body


class DeleteFloatingIP(neutronV20.DeleteCommand):
    """Delete a given floating ip."""

    log = logging.getLogger(__name__ + '.DeleteFloatingIP')
    resource = 'floatingip'
    allow_names = False


class AssociateFloatingIP(neutronV20.NeutronCommand):
    """Create a mapping between a floating ip and a fixed ip."""

    api = 'network'
    log = logging.getLogger(__name__ + '.AssociateFloatingIP')
    resource = 'floatingip'

    def get_parser(self, prog_name):
        parser = super(AssociateFloatingIP, self).get_parser(prog_name)
        parser.add_argument(
            'floatingip_id', metavar='FLOATINGIP_ID',
            help=_('ID of the floating IP to associate'))
        parser.add_argument(
            'port_id', metavar='PORT',
            help=_('ID or name of the port to be associated with the '
                   'floatingip'))
        parser.add_argument(
            '--fixed-ip-address',
            help=_('IP address on the port (only required if port has multiple'
                   'IPs)'))
        parser.add_argument(
            '--fixed_ip_address',
            help=argparse.SUPPRESS)
        return parser

    def run(self, parsed_args):
        self.log.debug('run(%s)' % parsed_args)
        neutron_client = self.get_client()
        neutron_client.format = parsed_args.request_format
        update_dict = {}
        if parsed_args.port_id:
            update_dict['port_id'] = parsed_args.port_id
        if parsed_args.fixed_ip_address:
            update_dict['fixed_ip_address'] = parsed_args.fixed_ip_address
        neutron_client.update_floatingip(parsed_args.floatingip_id,
                                         {'floatingip': update_dict})
        print(_('Associated floatingip %s') % parsed_args.floatingip_id,
              file=self.app.stdout)


class DisassociateFloatingIP(neutronV20.NeutronCommand):
    """Remove a mapping from a floating ip to a fixed ip.
    """

    api = 'network'
    log = logging.getLogger(__name__ + '.DisassociateFloatingIP')
    resource = 'floatingip'

    def get_parser(self, prog_name):
        parser = super(DisassociateFloatingIP, self).get_parser(prog_name)
        parser.add_argument(
            'floatingip_id', metavar='FLOATINGIP_ID',
            help=_('ID of the floating IP to associate'))
        return parser

    def run(self, parsed_args):
        self.log.debug('run(%s)' % parsed_args)
        neutron_client = self.get_client()
        neutron_client.format = parsed_args.request_format
        neutron_client.update_floatingip(parsed_args.floatingip_id,
                                         {'floatingip': {'port_id': None}})
        print(_('Disassociated floatingip %s') % parsed_args.floatingip_id,
              file=self.app.stdout)

########NEW FILE########
__FILENAME__ = firewall
# Copyright 2013 Big Switch Networks
# All Rights Reserved
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.
#
# @author: KC Wang, Big Switch Networks
#

import argparse
import logging

from neutronclient.neutron import v2_0 as neutronv20
from neutronclient.openstack.common.gettextutils import _


class ListFirewall(neutronv20.ListCommand):
    """List firewalls that belong to a given tenant."""

    resource = 'firewall'
    log = logging.getLogger(__name__ + '.ListFirewall')
    list_columns = ['id', 'name', 'firewall_policy_id']
    _formatters = {}
    pagination_support = True
    sorting_support = True


class ShowFirewall(neutronv20.ShowCommand):
    """Show information of a given firewall."""

    resource = 'firewall'
    log = logging.getLogger(__name__ + '.ShowFirewall')


class CreateFirewall(neutronv20.CreateCommand):
    """Create a firewall."""

    resource = 'firewall'
    log = logging.getLogger(__name__ + '.CreateFirewall')

    def add_known_arguments(self, parser):
        parser.add_argument(
            'firewall_policy_id', metavar='POLICY',
            help=_('Firewall policy id'))
        parser.add_argument(
            '--name',
            help=_('Name for the firewall'))
        parser.add_argument(
            '--description',
            help=_('Description for the firewall rule'))
        parser.add_argument(
            '--shared',
            action='store_true',
            help=_('Set shared to True (default False)'),
            default=argparse.SUPPRESS)
        parser.add_argument(
            '--admin-state-down',
            dest='admin_state',
            action='store_false',
            help=_('Set admin state up to false'))

    def args2body(self, parsed_args):
        _policy_id = neutronv20.find_resourceid_by_name_or_id(
            self.get_client(), 'firewall_policy',
            parsed_args.firewall_policy_id)
        body = {
            self.resource: {
                'firewall_policy_id': _policy_id,
                'admin_state_up': parsed_args.admin_state, }, }
        neutronv20.update_dict(parsed_args, body[self.resource],
                               ['name', 'description', 'shared',
                                'tenant_id'])
        return body


class UpdateFirewall(neutronv20.UpdateCommand):
    """Update a given firewall."""

    resource = 'firewall'
    log = logging.getLogger(__name__ + '.UpdateFirewall')


class DeleteFirewall(neutronv20.DeleteCommand):
    """Delete a given firewall."""

    resource = 'firewall'
    log = logging.getLogger(__name__ + '.DeleteFirewall')

########NEW FILE########
__FILENAME__ = firewallpolicy
# Copyright 2013 Big Switch Networks
# All Rights Reserved
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.
#
# @author: KC Wang, Big Switch Networks
#

from __future__ import print_function

import argparse
import logging
import string

from neutronclient.neutron import v2_0 as neutronv20
from neutronclient.openstack.common.gettextutils import _


def _format_firewall_rules(firewall_policy):
    try:
        output = '[' + ',\n '.join([rule for rule in
                                    firewall_policy['firewall_rules']]) + ']'
        return output
    except Exception:
        return ''


class ListFirewallPolicy(neutronv20.ListCommand):
    """List firewall policies that belong to a given tenant."""

    resource = 'firewall_policy'
    log = logging.getLogger(__name__ + '.ListFirewallPolicy')
    list_columns = ['id', 'name', 'firewall_rules']
    _formatters = {'firewall_rules': _format_firewall_rules,
                   }
    pagination_support = True
    sorting_support = True


class ShowFirewallPolicy(neutronv20.ShowCommand):
    """Show information of a given firewall policy."""

    resource = 'firewall_policy'
    log = logging.getLogger(__name__ + '.ShowFirewallPolicy')


class CreateFirewallPolicy(neutronv20.CreateCommand):
    """Create a firewall policy."""

    resource = 'firewall_policy'
    log = logging.getLogger(__name__ + '.CreateFirewallPolicy')

    def add_known_arguments(self, parser):
        parser.add_argument(
            'name',
            metavar='NAME',
            help=_('Name for the firewall policy'))
        parser.add_argument(
            '--description',
            help=_('Description for the firewall policy'))
        parser.add_argument(
            '--shared',
            dest='shared',
            action='store_true',
            help=_('To create a shared policy'),
            default=argparse.SUPPRESS)
        parser.add_argument(
            '--firewall-rules', type=string.split,
            help=_('Ordered list of whitespace-delimited firewall rule '
            'names or IDs; e.g., --firewall-rules \"rule1 rule2\"'))
        parser.add_argument(
            '--audited',
            action='store_true',
            help=_('To set audited to True'),
            default=argparse.SUPPRESS)

    def args2body(self, parsed_args):
        if parsed_args.firewall_rules:
            _firewall_rules = []
            for f in parsed_args.firewall_rules:
                _firewall_rules.append(
                    neutronv20.find_resourceid_by_name_or_id(
                        self.get_client(), 'firewall_rule', f))
                body = {self.resource: {
                        'firewall_rules': _firewall_rules,
                        },
                        }
        else:
            body = {self.resource: {}}
        neutronv20.update_dict(parsed_args, body[self.resource],
                               ['name', 'description', 'shared',
                                'audited', 'tenant_id'])
        return body


class UpdateFirewallPolicy(neutronv20.UpdateCommand):
    """Update a given firewall policy."""

    resource = 'firewall_policy'
    log = logging.getLogger(__name__ + '.UpdateFirewallPolicy')


class DeleteFirewallPolicy(neutronv20.DeleteCommand):
    """Delete a given firewall policy."""

    resource = 'firewall_policy'
    log = logging.getLogger(__name__ + '.DeleteFirewallPolicy')


class FirewallPolicyInsertRule(neutronv20.UpdateCommand):
    """Insert a rule into a given firewall policy."""

    resource = 'firewall_policy'
    log = logging.getLogger(__name__ + '.FirewallPolicyInsertRule')

    def call_api(self, neutron_client, firewall_policy_id, body):
        return neutron_client.firewall_policy_insert_rule(firewall_policy_id,
                                                          body)

    def args2body(self, parsed_args):
        _rule = ''
        if parsed_args.firewall_rule_id:
            _rule = neutronv20.find_resourceid_by_name_or_id(
                self.get_client(), 'firewall_rule',
                parsed_args.firewall_rule_id)
        _insert_before = ''
        if 'insert_before' in parsed_args:
            if parsed_args.insert_before:
                _insert_before = neutronv20.find_resourceid_by_name_or_id(
                    self.get_client(), 'firewall_rule',
                    parsed_args.insert_before)
        _insert_after = ''
        if 'insert_after' in parsed_args:
            if parsed_args.insert_after:
                _insert_after = neutronv20.find_resourceid_by_name_or_id(
                    self.get_client(), 'firewall_rule',
                    parsed_args.insert_after)
        body = {'firewall_rule_id': _rule,
                'insert_before': _insert_before,
                'insert_after': _insert_after}
        neutronv20.update_dict(parsed_args, body, [])
        return body

    def get_parser(self, prog_name):
        parser = super(FirewallPolicyInsertRule, self).get_parser(prog_name)
        parser.add_argument(
            '--insert-before',
            metavar='FIREWALL_RULE',
            help=_('Insert before this rule'))
        parser.add_argument(
            '--insert-after',
            metavar='FIREWALL_RULE',
            help=_('Insert after this rule'))
        parser.add_argument(
            'firewall_rule_id',
            metavar='FIREWALL_RULE',
            help=_('New rule to insert'))
        self.add_known_arguments(parser)
        return parser

    def run(self, parsed_args):
        neutron_client = self.get_client()
        neutron_client.format = parsed_args.request_format
        body = self.args2body(parsed_args)
        _id = neutronv20.find_resourceid_by_name_or_id(neutron_client,
                                                       self.resource,
                                                       parsed_args.id)
        self.call_api(neutron_client, _id, body)
        print((_('Inserted firewall rule in firewall policy %(id)s') %
               {'id': parsed_args.id}), file=self.app.stdout)


class FirewallPolicyRemoveRule(neutronv20.UpdateCommand):
    """Remove a rule from a given firewall policy."""

    resource = 'firewall_policy'
    log = logging.getLogger(__name__ + '.FirewallPolicyRemoveRule')

    def call_api(self, neutron_client, firewall_policy_id, body):
        return neutron_client.firewall_policy_remove_rule(firewall_policy_id,
                                                          body)

    def args2body(self, parsed_args):
        _rule = ''
        if parsed_args.firewall_rule_id:
            _rule = neutronv20.find_resourceid_by_name_or_id(
                self.get_client(), 'firewall_rule',
                parsed_args.firewall_rule_id)
        body = {'firewall_rule_id': _rule}
        neutronv20.update_dict(parsed_args, body, [])
        return body

    def get_parser(self, prog_name):
        parser = super(FirewallPolicyRemoveRule, self).get_parser(prog_name)
        parser.add_argument(
            'firewall_rule_id',
            metavar='FIREWALL_RULE',
            help=_('Firewall rule to remove from policy'))
        self.add_known_arguments(parser)
        return parser

    def run(self, parsed_args):
        neutron_client = self.get_client()
        neutron_client.format = parsed_args.request_format
        body = self.args2body(parsed_args)
        _id = neutronv20.find_resourceid_by_name_or_id(neutron_client,
                                                       self.resource,
                                                       parsed_args.id)
        self.call_api(neutron_client, _id, body)
        print((_('Removed firewall rule from firewall policy %(id)s') %
               {'id': parsed_args.id}), file=self.app.stdout)

########NEW FILE########
__FILENAME__ = firewallrule
# Copyright 2013 Big Switch Networks
# All Rights Reserved
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.
#
# @author: KC Wang, Big Switch Networks
#

import argparse
import logging

from neutronclient.neutron import v2_0 as neutronv20
from neutronclient.openstack.common.gettextutils import _


class ListFirewallRule(neutronv20.ListCommand):
    """List firewall rules that belong to a given tenant."""

    resource = 'firewall_rule'
    log = logging.getLogger(__name__ + '.ListFirewallRule')
    list_columns = ['id', 'name', 'firewall_policy_id', 'summary', 'enabled']
    pagination_support = True
    sorting_support = True

    def extend_list(self, data, parsed_args):
        for d in data:
            val = []
            if d.get('protocol'):
                protocol = d['protocol'].upper()
            else:
                protocol = 'no-protocol'
            val.append(protocol)
            if 'source_ip_address' in d and 'source_port' in d:
                src = 'source: ' + str(d['source_ip_address']).lower()
                src = src + '(' + str(d['source_port']).lower() + ')'
            else:
                src = 'source: none specified'
            val.append(src)
            if 'destination_ip_address' in d and 'destination_port' in d:
                dst = 'dest: ' + str(d['destination_ip_address']).lower()
                dst = dst + '(' + str(d['destination_port']).lower() + ')'
            else:
                dst = 'dest: none specified'
            val.append(dst)
            if 'action' in d:
                action = d['action']
            else:
                action = 'no-action'
            val.append(action)
            d['summary'] = ',\n '.join(val)


class ShowFirewallRule(neutronv20.ShowCommand):
    """Show information of a given firewall rule."""

    resource = 'firewall_rule'
    log = logging.getLogger(__name__ + '.ShowFirewallRule')


class CreateFirewallRule(neutronv20.CreateCommand):
    """Create a firewall rule."""

    resource = 'firewall_rule'
    log = logging.getLogger(__name__ + '.CreateFirewallRule')

    def add_known_arguments(self, parser):
        parser.add_argument(
            '--name',
            help=_('Name for the firewall rule'))
        parser.add_argument(
            '--description',
            help=_('Description for the firewall rule'))
        parser.add_argument(
            '--shared',
            dest='shared',
            action='store_true',
            help=_('Set shared to True (default False)'),
            default=argparse.SUPPRESS)
        parser.add_argument(
            '--source-ip-address',
            help=_('Source ip address or subnet'))
        parser.add_argument(
            '--destination-ip-address',
            help=_('Destination ip address or subnet'))
        parser.add_argument(
            '--source-port',
            help=_('Source port (integer in [1, 65535] or range in a:b)'))
        parser.add_argument(
            '--destination-port',
            help=_('Destination port (integer in [1, 65535] or range in a:b)'))
        parser.add_argument(
            '--disabled',
            dest='enabled',
            action='store_false',
            help=_('To disable this rule'),
            default=argparse.SUPPRESS)
        parser.add_argument(
            '--protocol', choices=['tcp', 'udp', 'icmp', 'any'],
            required=True,
            help=_('Protocol for the firewall rule'))
        parser.add_argument(
            '--action',
            required=True,
            choices=['allow', 'deny'],
            help=_('Action for the firewall rule'))

    def args2body(self, parsed_args):
        body = {
            self.resource: {},
        }
        neutronv20.update_dict(parsed_args, body[self.resource],
                               ['name', 'description', 'shared', 'protocol',
                                'source_ip_address', 'destination_ip_address',
                                'source_port', 'destination_port',
                                'action', 'enabled', 'tenant_id'])
        protocol = parsed_args.protocol
        if protocol == 'any':
            protocol = None
        body[self.resource]['protocol'] = protocol
        return body


class UpdateFirewallRule(neutronv20.UpdateCommand):
    """Update a given firewall rule."""

    resource = 'firewall_rule'
    log = logging.getLogger(__name__ + '.UpdateFirewallRule')

    def add_known_arguments(self, parser):
        parser.add_argument(
            '--protocol', choices=['tcp', 'udp', 'icmp', 'any'],
            required=False,
            help=_('Protocol for the firewall rule'))

    def args2body(self, parsed_args):
        body = {
            self.resource: {},
        }
        protocol = parsed_args.protocol
        if protocol:
            if protocol == 'any':
                protocol = None
            body[self.resource]['protocol'] = protocol
        return body


class DeleteFirewallRule(neutronv20.DeleteCommand):
    """Delete a given firewall rule."""

    resource = 'firewall_rule'
    log = logging.getLogger(__name__ + '.DeleteFirewallRule')

########NEW FILE########
__FILENAME__ = healthmonitor
# Copyright 2013 Mirantis Inc.
# All Rights Reserved
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.
#
# @author: Ilya Shakhat, Mirantis Inc.
#

from __future__ import print_function

import logging

from neutronclient.neutron import v2_0 as neutronV20
from neutronclient.openstack.common.gettextutils import _


class ListHealthMonitor(neutronV20.ListCommand):
    """List healthmonitors that belong to a given tenant."""

    resource = 'health_monitor'
    log = logging.getLogger(__name__ + '.ListHealthMonitor')
    list_columns = ['id', 'type', 'admin_state_up']
    pagination_support = True
    sorting_support = True


class ShowHealthMonitor(neutronV20.ShowCommand):
    """Show information of a given healthmonitor."""

    resource = 'health_monitor'
    log = logging.getLogger(__name__ + '.ShowHealthMonitor')


class CreateHealthMonitor(neutronV20.CreateCommand):
    """Create a healthmonitor."""

    resource = 'health_monitor'
    log = logging.getLogger(__name__ + '.CreateHealthMonitor')

    def add_known_arguments(self, parser):
        parser.add_argument(
            '--admin-state-down',
            dest='admin_state', action='store_false',
            help=_('Set admin state up to false'))
        parser.add_argument(
            '--expected-codes',
            help=_('The list of HTTP status codes expected in '
                   'response from the member to declare it healthy. This '
                   'attribute can contain one value, '
                   'or a list of values separated by comma, '
                   'or a range of values (e.g. "200-299"). If this attribute '
                   'is not specified, it defaults to "200". '))
        parser.add_argument(
            '--http-method',
            help=_('The HTTP method used for requests by the monitor of type '
                   'HTTP.'))
        parser.add_argument(
            '--url-path',
            help=_('The HTTP path used in the HTTP request used by the monitor'
                   ' to test a member health. This must be a string '
                   'beginning with a / (forward slash)'))
        parser.add_argument(
            '--delay',
            required=True,
            help=_('The time in seconds between sending probes to members.'))
        parser.add_argument(
            '--max-retries',
            required=True,
            help=_('Number of permissible connection failures before changing '
                   'the member status to INACTIVE. [1..10]'))
        parser.add_argument(
            '--timeout',
            required=True,
            help=_('Maximum number of seconds for a monitor to wait for a '
                   'connection to be established before it times out. The '
                   'value must be less than the delay value.'))
        parser.add_argument(
            '--type',
            required=True, choices=['PING', 'TCP', 'HTTP', 'HTTPS'],
            help=_('One of predefined health monitor types'))

    def args2body(self, parsed_args):
        body = {
            self.resource: {
                'admin_state_up': parsed_args.admin_state,
                'delay': parsed_args.delay,
                'max_retries': parsed_args.max_retries,
                'timeout': parsed_args.timeout,
                'type': parsed_args.type,
            },
        }
        neutronV20.update_dict(parsed_args, body[self.resource],
                               ['expected_codes', 'http_method', 'url_path',
                                'tenant_id'])
        return body


class UpdateHealthMonitor(neutronV20.UpdateCommand):
    """Update a given healthmonitor."""

    resource = 'health_monitor'
    log = logging.getLogger(__name__ + '.UpdateHealthMonitor')
    allow_names = False


class DeleteHealthMonitor(neutronV20.DeleteCommand):
    """Delete a given healthmonitor."""

    resource = 'health_monitor'
    log = logging.getLogger(__name__ + '.DeleteHealthMonitor')


class AssociateHealthMonitor(neutronV20.NeutronCommand):
    """Create a mapping between a health monitor and a pool."""

    log = logging.getLogger(__name__ + '.AssociateHealthMonitor')
    resource = 'health_monitor'

    def get_parser(self, prog_name):
        parser = super(AssociateHealthMonitor, self).get_parser(prog_name)
        parser.add_argument(
            'health_monitor_id', metavar='HEALTH_MONITOR_ID',
            help=_('Health monitor to associate'))
        parser.add_argument(
            'pool_id', metavar='POOL',
            help=_('ID of the pool to be associated with the health monitor'))
        return parser

    def run(self, parsed_args):
        neutron_client = self.get_client()
        neutron_client.format = parsed_args.request_format
        body = {'health_monitor': {'id': parsed_args.health_monitor_id}}
        pool_id = neutronV20.find_resourceid_by_name_or_id(
            neutron_client, 'pool', parsed_args.pool_id)
        neutron_client.associate_health_monitor(pool_id, body)
        print((_('Associated health monitor '
                 '%s') % parsed_args.health_monitor_id),
              file=self.app.stdout)


class DisassociateHealthMonitor(neutronV20.NeutronCommand):
    """Remove a mapping from a health monitor to a pool."""

    log = logging.getLogger(__name__ + '.DisassociateHealthMonitor')
    resource = 'health_monitor'

    def get_parser(self, prog_name):
        parser = super(DisassociateHealthMonitor, self).get_parser(prog_name)
        parser.add_argument(
            'health_monitor_id', metavar='HEALTH_MONITOR_ID',
            help=_('Health monitor to associate'))
        parser.add_argument(
            'pool_id', metavar='POOL',
            help=_('ID of the pool to be associated with the health monitor'))
        return parser

    def run(self, parsed_args):
        neutron_client = self.get_client()
        neutron_client.format = parsed_args.request_format
        pool_id = neutronV20.find_resourceid_by_name_or_id(
            neutron_client, 'pool', parsed_args.pool_id)
        neutron_client.disassociate_health_monitor(pool_id,
                                                   parsed_args
                                                   .health_monitor_id)
        print((_('Disassociated health monitor '
                 '%s') % parsed_args.health_monitor_id),
              file=self.app.stdout)

########NEW FILE########
__FILENAME__ = member
# Copyright 2013 Mirantis Inc.
# All Rights Reserved
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.
#
# @author: Ilya Shakhat, Mirantis Inc.
#

import logging

from neutronclient.neutron import v2_0 as neutronV20
from neutronclient.openstack.common.gettextutils import _


class ListMember(neutronV20.ListCommand):
    """List members that belong to a given tenant."""

    resource = 'member'
    log = logging.getLogger(__name__ + '.ListMember')
    list_columns = [
        'id', 'address', 'protocol_port', 'weight', 'admin_state_up', 'status'
    ]
    pagination_support = True
    sorting_support = True


class ShowMember(neutronV20.ShowCommand):
    """Show information of a given member."""

    resource = 'member'
    log = logging.getLogger(__name__ + '.ShowMember')


class CreateMember(neutronV20.CreateCommand):
    """Create a member."""

    resource = 'member'
    log = logging.getLogger(__name__ + '.CreateMember')

    def add_known_arguments(self, parser):
        parser.add_argument(
            'pool_id', metavar='POOL',
            help=_('Pool id or name this vip belongs to'))
        parser.add_argument(
            '--admin-state-down',
            dest='admin_state', action='store_false',
            help=_('Set admin state up to false'))
        parser.add_argument(
            '--weight',
            help=_('Weight of pool member in the pool (default:1, [0..256])'))
        parser.add_argument(
            '--address',
            required=True,
            help=_('IP address of the pool member on the pool network. '))
        parser.add_argument(
            '--protocol-port',
            required=True,
            help=_('Port on which the pool member listens for requests or '
                   'connections. '))

    def args2body(self, parsed_args):
        _pool_id = neutronV20.find_resourceid_by_name_or_id(
            self.get_client(), 'pool', parsed_args.pool_id)
        body = {
            self.resource: {
                'pool_id': _pool_id,
                'admin_state_up': parsed_args.admin_state,
            },
        }
        neutronV20.update_dict(
            parsed_args,
            body[self.resource],
            ['address', 'protocol_port', 'weight', 'tenant_id']
        )
        return body


class UpdateMember(neutronV20.UpdateCommand):
    """Update a given member."""

    resource = 'member'
    log = logging.getLogger(__name__ + '.UpdateMember')


class DeleteMember(neutronV20.DeleteCommand):
    """Delete a given member."""

    resource = 'member'
    log = logging.getLogger(__name__ + '.DeleteMember')

########NEW FILE########
__FILENAME__ = pool
# Copyright 2013 Mirantis Inc.
# All Rights Reserved
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.
#
# @author: Ilya Shakhat, Mirantis Inc.
#

import logging

from neutronclient.neutron import v2_0 as neutronV20
from neutronclient.openstack.common.gettextutils import _


def _format_provider(pool):
    return pool.get('provider') or 'N/A'


class ListPool(neutronV20.ListCommand):
    """List pools that belong to a given tenant."""

    resource = 'pool'
    log = logging.getLogger(__name__ + '.ListPool')
    list_columns = ['id', 'name', 'provider', 'lb_method', 'protocol',
                    'admin_state_up', 'status']
    _formatters = {'provider': _format_provider}
    pagination_support = True
    sorting_support = True


class ShowPool(neutronV20.ShowCommand):
    """Show information of a given pool."""

    resource = 'pool'
    log = logging.getLogger(__name__ + '.ShowPool')


class CreatePool(neutronV20.CreateCommand):
    """Create a pool."""

    resource = 'pool'
    log = logging.getLogger(__name__ + '.CreatePool')

    def add_known_arguments(self, parser):
        parser.add_argument(
            '--admin-state-down',
            dest='admin_state', action='store_false',
            help=_('Set admin state up to false'))
        parser.add_argument(
            '--description',
            help=_('Description of the pool'))
        parser.add_argument(
            '--lb-method',
            required=True,
            choices=['ROUND_ROBIN', 'LEAST_CONNECTIONS', 'SOURCE_IP'],
            help=_('The algorithm used to distribute load between the members '
                   'of the pool'))
        parser.add_argument(
            '--name',
            required=True,
            help=_('The name of the pool'))
        parser.add_argument(
            '--protocol',
            required=True,
            choices=['HTTP', 'HTTPS', 'TCP'],
            help=_('Protocol for balancing'))
        parser.add_argument(
            '--subnet-id', metavar='SUBNET',
            required=True,
            help=_('The subnet on which the members of the pool will be '
                   'located'))
        parser.add_argument(
            '--provider',
            help=_('Provider name of loadbalancer service'))

    def args2body(self, parsed_args):
        _subnet_id = neutronV20.find_resourceid_by_name_or_id(
            self.get_client(), 'subnet', parsed_args.subnet_id)
        body = {
            self.resource: {
                'admin_state_up': parsed_args.admin_state,
                'subnet_id': _subnet_id,
            },
        }
        neutronV20.update_dict(parsed_args, body[self.resource],
                               ['description', 'lb_method', 'name',
                                'protocol', 'tenant_id', 'provider'])
        return body


class UpdatePool(neutronV20.UpdateCommand):
    """Update a given pool."""

    resource = 'pool'
    log = logging.getLogger(__name__ + '.UpdatePool')


class DeletePool(neutronV20.DeleteCommand):
    """Delete a given pool."""

    resource = 'pool'
    log = logging.getLogger(__name__ + '.DeletePool')


class RetrievePoolStats(neutronV20.ShowCommand):
    """Retrieve stats for a given pool."""

    resource = 'pool'
    log = logging.getLogger(__name__ + '.RetrievePoolStats')

    def get_data(self, parsed_args):
        self.log.debug('run(%s)' % parsed_args)
        neutron_client = self.get_client()
        neutron_client.format = parsed_args.request_format
        pool_id = neutronV20.find_resourceid_by_name_or_id(
            self.get_client(), 'pool', parsed_args.id)
        params = {}
        if parsed_args.fields:
            params = {'fields': parsed_args.fields}

        data = neutron_client.retrieve_pool_stats(pool_id, **params)
        self.format_output_data(data)
        stats = data['stats']
        if 'stats' in data:
            return zip(*sorted(stats.iteritems()))
        else:
            return None

########NEW FILE########
__FILENAME__ = vip
# Copyright 2013 Mirantis Inc.
# All Rights Reserved
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.
#
# @author: Ilya Shakhat, Mirantis Inc.
#

import logging

from neutronclient.neutron import v2_0 as neutronV20
from neutronclient.openstack.common.gettextutils import _


class ListVip(neutronV20.ListCommand):
    """List vips that belong to a given tenant."""

    resource = 'vip'
    log = logging.getLogger(__name__ + '.ListVip')
    list_columns = ['id', 'name', 'algorithm', 'address', 'protocol',
                    'admin_state_up', 'status']
    pagination_support = True
    sorting_support = True


class ShowVip(neutronV20.ShowCommand):
    """Show information of a given vip."""

    resource = 'vip'
    log = logging.getLogger(__name__ + '.ShowVip')


class CreateVip(neutronV20.CreateCommand):
    """Create a vip."""

    resource = 'vip'
    log = logging.getLogger(__name__ + '.CreateVip')

    def add_known_arguments(self, parser):
        parser.add_argument(
            'pool_id', metavar='POOL',
            help=_('Pool id or name this vip belongs to'))
        parser.add_argument(
            '--address',
            help=_('IP address of the vip'))
        parser.add_argument(
            '--admin-state-down',
            dest='admin_state', action='store_false',
            help=_('Set admin state up to false'))
        parser.add_argument(
            '--connection-limit',
            help=_('The maximum number of connections per second allowed for '
                   'the vip. Positive integer or -1 for unlimited (default)'))
        parser.add_argument(
            '--description',
            help=_('Description of the vip'))
        parser.add_argument(
            '--name',
            required=True,
            help=_('Name of the vip'))
        parser.add_argument(
            '--protocol-port',
            required=True,
            help=_('TCP port on which to listen for client traffic that is '
                   'associated with the vip address'))
        parser.add_argument(
            '--protocol',
            required=True, choices=['TCP', 'HTTP', 'HTTPS'],
            help=_('Protocol for balancing'))
        parser.add_argument(
            '--subnet-id', metavar='SUBNET',
            required=True,
            help=_('The subnet on which to allocate the vip address'))

    def args2body(self, parsed_args):
        _pool_id = neutronV20.find_resourceid_by_name_or_id(
            self.get_client(), 'pool', parsed_args.pool_id)
        _subnet_id = neutronV20.find_resourceid_by_name_or_id(
            self.get_client(), 'subnet', parsed_args.subnet_id)

        body = {
            self.resource: {
                'pool_id': _pool_id,
                'admin_state_up': parsed_args.admin_state,
                'subnet_id': _subnet_id,
            },
        }
        neutronV20.update_dict(parsed_args, body[self.resource],
                               ['address', 'connection_limit', 'description',
                                'name', 'protocol_port', 'protocol',
                                'tenant_id'])
        return body


class UpdateVip(neutronV20.UpdateCommand):
    """Update a given vip."""

    resource = 'vip'
    log = logging.getLogger(__name__ + '.UpdateVip')


class DeleteVip(neutronV20.DeleteCommand):
    """Delete a given vip."""

    resource = 'vip'
    log = logging.getLogger(__name__ + '.DeleteVip')

########NEW FILE########
__FILENAME__ = metering
# Copyright (C) 2013 eNovance SAS <licensing@enovance.com>
#
# Author: Sylvain Afchain <sylvain.afchain@enovance.com>
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import logging

from neutronclient.neutron import v2_0 as neutronv20
from neutronclient.openstack.common.gettextutils import _


class ListMeteringLabel(neutronv20.ListCommand):
    """List metering labels that belong to a given tenant."""

    resource = 'metering_label'
    log = logging.getLogger(__name__ + '.ListMeteringLabel')
    list_columns = ['id', 'name', 'description', 'shared']
    pagination_support = True
    sorting_support = True


class ShowMeteringLabel(neutronv20.ShowCommand):
    """Show information of a given metering label."""

    resource = 'metering_label'
    log = logging.getLogger(__name__ + '.ShowMeteringLabel')
    allow_names = True


class CreateMeteringLabel(neutronv20.CreateCommand):
    """Create a metering label for a given tenant."""

    resource = 'metering_label'
    log = logging.getLogger(__name__ + '.CreateMeteringLabel')

    def add_known_arguments(self, parser):
        parser.add_argument(
            'name', metavar='NAME',
            help=_('Name of metering label to create'))
        parser.add_argument(
            '--description',
            help=_('Description of metering label to create'))
        parser.add_argument(
            '--shared',
            action='store_true',
            help=_('Set the label as shared'))

    def args2body(self, parsed_args):
        body = {'metering_label': {
            'name': parsed_args.name}, }

        if parsed_args.tenant_id:
            body['metering_label'].update({'tenant_id': parsed_args.tenant_id})
        if parsed_args.description:
            body['metering_label'].update(
                {'description': parsed_args.description})
        if parsed_args.shared:
            body['metering_label'].update(
                {'shared': True})
        return body


class DeleteMeteringLabel(neutronv20.DeleteCommand):
    """Delete a given metering label."""

    log = logging.getLogger(__name__ + '.DeleteMeteringLabel')
    resource = 'metering_label'
    allow_names = True


class ListMeteringLabelRule(neutronv20.ListCommand):
    """List metering labels that belong to a given label."""

    resource = 'metering_label_rule'
    log = logging.getLogger(__name__ + '.ListMeteringLabelRule')
    list_columns = ['id', 'excluded', 'direction', 'remote_ip_prefix']
    pagination_support = True
    sorting_support = True


class ShowMeteringLabelRule(neutronv20.ShowCommand):
    """Show information of a given metering label rule."""

    resource = 'metering_label_rule'
    log = logging.getLogger(__name__ + '.ShowMeteringLabelRule')


class CreateMeteringLabelRule(neutronv20.CreateCommand):
    """Create a metering label rule for a given label."""

    resource = 'metering_label_rule'
    log = logging.getLogger(__name__ + '.CreateMeteringLabelRule')

    def add_known_arguments(self, parser):
        parser.add_argument(
            'label_id', metavar='LABEL',
            help=_('Id or Name of the label'))
        parser.add_argument(
            'remote_ip_prefix', metavar='REMOTE_IP_PREFIX',
            help=_('CIDR to match on'))
        parser.add_argument(
            '--direction',
            default='ingress', choices=['ingress', 'egress'],
            help=_('Direction of traffic, default:ingress'))
        parser.add_argument(
            '--excluded',
            action='store_true',
            help=_('Exclude this cidr from the label, default:not excluded'))

    def args2body(self, parsed_args):
        neutron_client = self.get_client()
        neutron_client.format = parsed_args.request_format
        label_id = neutronv20.find_resourceid_by_name_or_id(
            neutron_client, 'metering_label', parsed_args.label_id)

        body = {'metering_label_rule': {
            'metering_label_id': label_id,
            'remote_ip_prefix': parsed_args.remote_ip_prefix
        }}

        if parsed_args.direction:
            body['metering_label_rule'].update(
                {'direction': parsed_args.direction})
        if parsed_args.excluded:
            body['metering_label_rule'].update(
                {'excluded': True})
        return body


class DeleteMeteringLabelRule(neutronv20.DeleteCommand):
    """Delete a given metering label."""

    log = logging.getLogger(__name__ + '.DeleteMeteringLabelRule')
    resource = 'metering_label_rule'

########NEW FILE########
__FILENAME__ = packetfilter
# Copyright 2014 NEC Corporation
# All Rights Reserved
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import logging

from neutronclient.common import exceptions
from neutronclient.common import validators
from neutronclient.neutron import v2_0 as neutronV20
from neutronclient.openstack.common.gettextutils import _


class ListPacketFilter(neutronV20.ListCommand):
    """List packet filters that belong to a given tenant."""

    resource = 'packet_filter'
    log = logging.getLogger(__name__ + '.ListPacketFilter')
    list_columns = ['id', 'name', 'action', 'priority', 'summary']
    pagination_support = True
    sorting_support = True

    def extend_list(self, data, parsed_args):
        for d in data:
            val = []
            proto_eth_type = []
            if d.get('protocol'):
                proto_eth_type.append('protocol: %s' % d['protocol'].upper())
            if d.get('eth_type'):
                proto_eth_type.append('eth_type: %s' % d['eth_type'])
            if proto_eth_type:
                val.append(', '.join(proto_eth_type))
            val.append('network: ' + d['network_id'])
            if d.get('in_port'):
                val.append('in_port: ' + d['in_port'])
            source = [str(d.get(field)) for field
                      in ['src_mac', 'src_cidr', 'src_port'] if d.get(field)]
            if source:
                val.append('source: ' + ' '.join(source))
            dest = [str(d.get(field)) for field
                    in ['dst_mac', 'dst_cidr', 'dst_port'] if d.get(field)]
            if dest:
                val.append('destination: ' + ' '.join(dest))
            d['summary'] = '\n'.join(val)


class ShowPacketFilter(neutronV20.ShowCommand):
    """Show information of a given packet filter."""

    resource = 'packet_filter'
    log = logging.getLogger(__name__ + '.ShowPacketFilter')


class PacketFilterOptionMixin(object):
    def add_known_arguments(self, parser):
        mode = self._get_mode()
        if not mode:
            return
        mode_create = mode == 'create'

        if mode_create:
            parser.add_argument(
                '--admin-state-down',
                dest='admin_state', action='store_false',
                help=_('Set Admin State Up to false'))
        else:
            parser.add_argument(
                '--admin-state', choices=['True', 'False'],
                help=_('Set a value of Admin State Up'))

        parser.add_argument(
            '--name',
            help=_('Name of this packet filter'))

        if mode_create:
            parser.add_argument(
                '--in-port', metavar='PORT',
                help=_('Name or ID of the input port'))

        parser.add_argument(
            '--src-mac',
            help=_('Source MAC address'))
        parser.add_argument(
            '--dst-mac',
            help=_('Destination MAC address'))
        parser.add_argument(
            '--eth-type',
            help=_('Ether Type. Integer [0:65535] (hex or decimal).'
                   ' E.g., 0x0800 (IPv4), 0x0806 (ARP), 0x86DD (IPv6)'))
        parser.add_argument(
            '--protocol',
            help=_('IP Protocol.'
                   ' Protocol name or integer.'
                   ' Recognized names are icmp, tcp, udp, arp'
                   ' (case insensitive).'
                   ' Integer should be [0:255] (decimal or hex).'))
        parser.add_argument(
            '--src-cidr',
            help=_('Source IP address CIDR'))
        parser.add_argument(
            '--dst-cidr',
            help=_('Destination IP address CIDR'))
        parser.add_argument(
            '--src-port',
            help=_('Source port address'))
        parser.add_argument(
            '--dst-port',
            help=_('Destination port address'))

        default_priority = '30000' if mode_create else None
        parser.add_argument(
            '--priority', metavar='PRIORITY',
            default=default_priority,
            help=(_('Priority of the filter. Integer of [0:65535].%s')
                  % (' Default: 30000.' if mode_create else '')))

        default_action = 'allow' if mode_create else None
        parser.add_argument(
            '--action',
            choices=['allow', 'drop'],
            default=default_action,
            help=(_('Action of the filter.%s')
                  % (' Default: allow' if mode_create else '')))

        if mode_create:
            parser.add_argument(
                'network', metavar='NETWORK',
                help=_('network to which this packet filter is applied'))

    def _get_mode(self):
        klass = self.__class__.__name__.lower()
        if klass.startswith('create'):
            mode = 'create'
        elif klass.startswith('update'):
            mode = 'update'
        else:
            mode = None
        return mode

    def validate_fields(self, parsed_args):
        self._validate_protocol(parsed_args.protocol)
        validators.validate_int_range(parsed_args, 'priority', 0, 0xffff)
        validators.validate_int_range(parsed_args, 'src_port', 0, 0xffff)
        validators.validate_int_range(parsed_args, 'dst_port', 0, 0xffff)
        validators.validate_ip_subnet(parsed_args, 'src_cidr')
        validators.validate_ip_subnet(parsed_args, 'dst_cidr')

    def _validate_protocol(self, protocol):
        if not protocol or protocol == 'action=clear':
            return
        try:
            protocol = int(protocol, 0)
            if 0 <= protocol <= 255:
                return
        except ValueError:
            # Use string as a protocol name
            # Exact check will be done in the server side.
            return
        msg = (_('protocol %s should be either of name '
                 '(tcp, udp, icmp, arp; '
                 'case insensitive) or integer [0:255] (decimal or hex).') %
               protocol)
        raise exceptions.CommandError(msg)


class CreatePacketFilter(PacketFilterOptionMixin,
                         neutronV20.CreateCommand):
    """Create a packet filter for a given tenant."""

    resource = 'packet_filter'
    log = logging.getLogger(__name__ + '.CreatePacketFilter')

    def args2body(self, parsed_args):
        self.validate_fields(parsed_args)

        _network_id = neutronV20.find_resourceid_by_name_or_id(
            self.get_client(), 'network', parsed_args.network)
        body = {'network_id': _network_id,
                'admin_state_up': parsed_args.admin_state}
        if parsed_args.in_port:
            _port_id = neutronV20.find_resourceid_by_name_or_id(
                self.get_client(), 'port', parsed_args.in_port)
            body['in_port'] = _port_id

        neutronV20.update_dict(
            parsed_args, body,
            ['action', 'priority', 'name',
             'eth_type', 'protocol', 'src_mac', 'dst_mac',
             'src_cidr', 'dst_cidr', 'src_port', 'dst_port'])

        return {self.resource: body}


class UpdatePacketFilter(PacketFilterOptionMixin,
                         neutronV20.UpdateCommand):
    """Update packet filter's information."""

    resource = 'packet_filter'
    log = logging.getLogger(__name__ + '.UpdatePacketFilter')

    def args2body(self, parsed_args):
        self.validate_fields(parsed_args)

        body = {}
        if parsed_args.admin_state:
            body['admin_state_up'] = (parsed_args.admin_state == 'True')

        # fields which allows None
        for attr in ['eth_type', 'protocol', 'src_mac', 'dst_mac',
                     'src_cidr', 'dst_cidr', 'src_port', 'dst_port']:
            if not hasattr(parsed_args, attr):
                continue
            val = getattr(parsed_args, attr)
            if val is None:
                continue
            if val == '' or val == 'action=clear':
                body[attr] = None
            else:
                body[attr] = val

        for attr in ['action', 'priority', 'name']:
            if (hasattr(parsed_args, attr) and
                getattr(parsed_args, attr) is not None):
                body[attr] = getattr(parsed_args, attr)

        return {self.resource: body}


class DeletePacketFilter(neutronV20.DeleteCommand):
    """Delete a given packet filter."""

    resource = 'packet_filter'
    log = logging.getLogger(__name__ + '.DeletePacketFilter')

########NEW FILE########
__FILENAME__ = netpartition
# Copyright 2014 Alcatel-Lucent USA Inc.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.
#
# @author: Ronak Shah, Nuage Networks, Alcatel-Lucent USA Inc.

import logging

from neutronclient.neutron.v2_0 import CreateCommand
from neutronclient.neutron.v2_0 import DeleteCommand
from neutronclient.neutron.v2_0 import ListCommand
from neutronclient.neutron.v2_0 import ShowCommand


class ListNetPartition(ListCommand):
    """List netpartitions that belong to a given tenant."""
    resource = 'net_partition'
    log = logging.getLogger(__name__ + '.ListNetPartition')
    list_columns = ['id', 'name']


class ShowNetPartition(ShowCommand):
    """Show information of a given netpartition."""

    resource = 'net_partition'
    log = logging.getLogger(__name__ + '.ShowNetPartition')


class CreateNetPartition(CreateCommand):
    """Create a netpartition for a given tenant."""

    resource = 'net_partition'
    log = logging.getLogger(__name__ + '.CreateNetPartition')

    def add_known_arguments(self, parser):
        parser.add_argument(
            'name', metavar='name',
            help='Name of NetPartition to create')

    def args2body(self, parsed_args):
        body = {'net_partition': {'name': parsed_args.name}, }
        return body


class DeleteNetPartition(DeleteCommand):
    """Delete a given netpartition."""

    resource = 'net_partition'
    log = logging.getLogger(__name__ + '.DeleteNetPartition')

########NEW FILE########
__FILENAME__ = network
# Copyright 2012 OpenStack Foundation.
# All Rights Reserved
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.
#

import argparse
import logging

from neutronclient.common import exceptions
from neutronclient.neutron import v2_0 as neutronV20
from neutronclient.openstack.common.gettextutils import _


def _format_subnets(network):
    try:
        return '\n'.join([' '.join([s['id'], s.get('cidr', '')])
                          for s in network['subnets']])
    except Exception:
        return ''


class ListNetwork(neutronV20.ListCommand):
    """List networks that belong to a given tenant."""

    # Length of a query filter on subnet id
    # id=<uuid>& (with len(uuid)=36)
    subnet_id_filter_len = 40
    resource = 'network'
    log = logging.getLogger(__name__ + '.ListNetwork')
    _formatters = {'subnets': _format_subnets, }
    list_columns = ['id', 'name', 'subnets']
    pagination_support = True
    sorting_support = True

    def extend_list(self, data, parsed_args):
        """Add subnet information to a network list."""
        neutron_client = self.get_client()
        search_opts = {'fields': ['id', 'cidr']}
        if self.pagination_support:
            page_size = parsed_args.page_size
            if page_size:
                search_opts.update({'limit': page_size})
        subnet_ids = []
        for n in data:
            if 'subnets' in n:
                subnet_ids.extend(n['subnets'])

        def _get_subnet_list(sub_ids):
            search_opts['id'] = sub_ids
            return neutron_client.list_subnets(
                **search_opts).get('subnets', [])

        try:
            subnets = _get_subnet_list(subnet_ids)
        except exceptions.RequestURITooLong as uri_len_exc:
            # The URI is too long because of too many subnet_id filters
            # Use the excess attribute of the exception to know how many
            # subnet_id filters can be inserted into a single request
            subnet_count = len(subnet_ids)
            max_size = ((self.subnet_id_filter_len * subnet_count) -
                        uri_len_exc.excess)
            chunk_size = max_size / self.subnet_id_filter_len
            subnets = []
            for i in range(0, subnet_count, chunk_size):
                subnets.extend(
                    _get_subnet_list(subnet_ids[i: i + chunk_size]))

        subnet_dict = dict([(s['id'], s) for s in subnets])
        for n in data:
            if 'subnets' in n:
                n['subnets'] = [(subnet_dict.get(s) or {"id": s})
                                for s in n['subnets']]


class ListExternalNetwork(ListNetwork):
    """List external networks that belong to a given tenant."""

    log = logging.getLogger(__name__ + '.ListExternalNetwork')
    pagination_support = True
    sorting_support = True

    def retrieve_list(self, parsed_args):
        external = '--router:external=True'
        if external not in self.values_specs:
            self.values_specs.append('--router:external=True')
        return super(ListExternalNetwork, self).retrieve_list(parsed_args)


class ShowNetwork(neutronV20.ShowCommand):
    """Show information of a given network."""

    resource = 'network'
    log = logging.getLogger(__name__ + '.ShowNetwork')


class CreateNetwork(neutronV20.CreateCommand):
    """Create a network for a given tenant."""

    resource = 'network'
    log = logging.getLogger(__name__ + '.CreateNetwork')

    def add_known_arguments(self, parser):
        parser.add_argument(
            '--admin-state-down',
            dest='admin_state', action='store_false',
            help=_('Set Admin State Up to false'))
        parser.add_argument(
            '--admin_state_down',
            dest='admin_state', action='store_false',
            help=argparse.SUPPRESS)
        parser.add_argument(
            '--shared',
            action='store_true',
            help=_('Set the network as shared'),
            default=argparse.SUPPRESS)
        parser.add_argument(
            'name', metavar='NAME',
            help=_('Name of network to create'))

    def args2body(self, parsed_args):
        body = {'network': {
            'name': parsed_args.name,
            'admin_state_up': parsed_args.admin_state}, }
        neutronV20.update_dict(parsed_args, body['network'],
                               ['shared', 'tenant_id'])
        return body


class DeleteNetwork(neutronV20.DeleteCommand):
    """Delete a given network."""

    log = logging.getLogger(__name__ + '.DeleteNetwork')
    resource = 'network'


class UpdateNetwork(neutronV20.UpdateCommand):
    """Update network's information."""

    log = logging.getLogger(__name__ + '.UpdateNetwork')
    resource = 'network'

########NEW FILE########
__FILENAME__ = networkprofile
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.
#
#@author Abhishek Raut, Cisco Systems
#@author Sergey Sudakovich, Cisco Systems
#@author Rudrajit Tapadar, Cisco Systems

from __future__ import print_function

import logging

from neutronclient.neutron import v2_0 as neutronV20
from neutronclient.neutron.v2_0 import parse_args_to_dict
from neutronclient.openstack.common.gettextutils import _

RESOURCE = 'network_profile'
SEGMENT_TYPE_CHOICES = ['vlan', 'overlay', 'multi-segment', 'trunk']


class ListNetworkProfile(neutronV20.ListCommand):
    """List network profiles that belong to a given tenant."""

    resource = RESOURCE
    log = logging.getLogger(__name__ + '.ListNetworkProfile')
    _formatters = {}
    list_columns = ['id', 'name', 'segment_type', 'sub_type', 'segment_range',
                    'physical_network', 'multicast_ip_index',
                    'multicast_ip_range']


class ShowNetworkProfile(neutronV20.ShowCommand):
    """Show information of a given network profile."""

    resource = RESOURCE
    log = logging.getLogger(__name__ + '.ShowNetworkProfile')
    allow_names = True


class CreateNetworkProfile(neutronV20.CreateCommand):
    """Creates a network profile."""

    resource = RESOURCE
    log = logging.getLogger(__name__ + '.CreateNetworkProfile')

    def add_known_arguments(self, parser):
        parser.add_argument('name',
                            help=_('Name for Network Profile'))
        parser.add_argument('segment_type',
                            choices=SEGMENT_TYPE_CHOICES,
                            help='Segment type')
        # TODO(Abhishek): Check on sub-type choices depending on segment_type
        parser.add_argument('--sub_type',
                            help=_('Sub-type for the segment. Available sub-'
                            'types for overlay segments: native, enhanced; '
                            'For trunk segments: vlan, overlay.'))
        parser.add_argument('--segment_range',
                            help=_('Range for the Segment'))
        parser.add_argument('--physical_network',
                            help=_('Name for the Physical Network'))
        parser.add_argument('--multicast_ip_range',
                            help=_('Multicast IPv4 Range'))
        parser.add_argument("--add-tenant",
                            help=_("Add tenant to the network profile"))

    def args2body(self, parsed_args):
        body = {'network_profile': {'name': parsed_args.name}}
        if parsed_args.segment_type:
            body['network_profile'].update({'segment_type':
                                           parsed_args.segment_type})
        if parsed_args.sub_type:
            body['network_profile'].update({'sub_type':
                                           parsed_args.sub_type})
        if parsed_args.segment_range:
            body['network_profile'].update({'segment_range':
                                           parsed_args.segment_range})
        if parsed_args.physical_network:
            body['network_profile'].update({'physical_network':
                                           parsed_args.physical_network})
        if parsed_args.multicast_ip_range:
            body['network_profile'].update({'multicast_ip_range':
                                           parsed_args.multicast_ip_range})
        if parsed_args.add_tenant:
            body['network_profile'].update({'add_tenant':
                                           parsed_args.add_tenant})
        return body


class DeleteNetworkProfile(neutronV20.DeleteCommand):
    """Delete a given network profile."""

    log = logging.getLogger(__name__ + '.DeleteNetworkProfile')
    resource = RESOURCE
    allow_names = True


class UpdateNetworkProfile(neutronV20.UpdateCommand):
    """Update network profile's information."""

    resource = RESOURCE
    log = logging.getLogger(__name__ + '.UpdateNetworkProfile')


class UpdateNetworkProfileV2(neutronV20.NeutronCommand):

    api = 'network'
    log = logging.getLogger(__name__ + '.UpdateNetworkProfileV2')
    resource = RESOURCE

    def get_parser(self, prog_name):
        parser = super(UpdateNetworkProfileV2, self).get_parser(prog_name)
        parser.add_argument("--remove-tenant",
                            help="Remove tenant from the network profile")
        return parser

    def run(self, parsed_args):
        self.log.debug('run(%s)' % parsed_args)
        neutron_client = self.get_client()
        neutron_client.format = parsed_args.request_format
        data = {self.resource: parse_args_to_dict(parsed_args)}
        if parsed_args.remove_tenant:
            data[self.resource]['remove_tenant'] = parsed_args.remove_tenant
        neutron_client.update_network_profile(parsed_args.id,
                                              {self.resource: data})
        print((_('Updated %(resource)s: %(id)s') %
               {'id': parsed_args.id, 'resource': self.resource}),
              file=self.app.stdout)
        return

########NEW FILE########
__FILENAME__ = networkgateway
# Copyright 2013 OpenStack Foundation.
# All Rights Reserved
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.
#

from __future__ import print_function

import logging

from neutronclient.common import utils
from neutronclient.neutron import v2_0 as neutronV20
from neutronclient.openstack.common.gettextutils import _

GW_RESOURCE = 'network_gateway'
DEV_RESOURCE = 'gateway_device'
CONNECTOR_TYPE_HELP = _("Type of the transport zone connector to use for this "
                        "device. Valid values are gre, stt, ipsecgre, "
                        "ipsecstt, and bridge. Defaults to stt")
CONNECTOR_IP_HELP = _("IP address for this device's transport connector. "
                      "It must correspond to the IP address of the interface "
                      "used for tenant traffic on the NSX gateway node")
CLIENT_CERT_HELP = _("PEM certificate used by the NSX gateway transport node "
                     "to authenticate with the NSX controller")
CLIENT_CERT_FILE_HELP = _("File containing the PEM certificate used by the "
                          "NSX gateway transport node to authenticate with "
                          "the NSX controller")


class ListGatewayDevice(neutronV20.ListCommand):
    """List network gateway devices for a given tenant."""

    resource = DEV_RESOURCE
    log = logging.getLogger(__name__ + '.ListGatewayDevice')
    list_columns = ['id', 'name']


class ShowGatewayDevice(neutronV20.ShowCommand):
    """Show information for a given network gateway device."""

    resource = DEV_RESOURCE
    log = logging.getLogger(__name__ + '.ShowGatewayDevice')


def read_cert_file(cert_file):
    return open(cert_file, 'rb').read()


def gateway_device_args2body(parsed_args):
    body = {}
    if parsed_args.name:
        body['name'] = parsed_args.name
    if parsed_args.connector_type:
        body['connector_type'] = parsed_args.connector_type
    if parsed_args.connector_ip:
        body['connector_ip'] = parsed_args.connector_ip
    cert_data = None
    if parsed_args.cert_file:
        cert_data = read_cert_file(parsed_args.cert_file)
    elif parsed_args.cert_data:
        cert_data = parsed_args.cert_data
    if cert_data:
        body['client_certificate'] = cert_data
    if getattr(parsed_args, 'tenant_id', None):
        body['tenant_id'] = parsed_args.tenant_id
    return {DEV_RESOURCE: body}


class CreateGatewayDevice(neutronV20.CreateCommand):
    """Create a network gateway device."""

    resource = DEV_RESOURCE
    log = logging.getLogger(__name__ + '.CreateGatewayDevice')

    def add_known_arguments(self, parser):
        parser.add_argument(
            'name', metavar='NAME',
            help='Name of network gateway device to create')
        parser.add_argument(
            '--connector-type',
            default='stt',
            choices=['stt', 'gre', 'ipsecgre', 'ipsecstt', 'bridge'],
            help=CONNECTOR_TYPE_HELP)
        parser.add_argument(
            '--connector-ip',
            required=True,
            help=CONNECTOR_IP_HELP)
        client_cert_group = parser.add_mutually_exclusive_group(
            required=True)
        client_cert_group.add_argument(
            '--client-certificate',
            dest='cert_data',
            help=CLIENT_CERT_HELP)
        client_cert_group.add_argument(
            '--client-certificate-file',
            dest='cert_file',
            help=CLIENT_CERT_FILE_HELP)

    def args2body(self, parsed_args):
        return gateway_device_args2body(parsed_args)


class UpdateGatewayDevice(neutronV20.UpdateCommand):
    """Update a network gateway device."""

    resource = DEV_RESOURCE
    log = logging.getLogger(__name__ + '.UpdateGatewayDevice')

    def add_known_arguments(self, parser):
        parser.add_argument(
            '--name', metavar='NAME',
            help='New name for network gateway device')
        parser.add_argument(
            '--connector-type',
            required=False,
            choices=['stt', 'gre', 'ipsecgre', 'ipsecstt', 'bridge'],
            help=CONNECTOR_TYPE_HELP)
        parser.add_argument(
            '--connector-ip',
            required=False,
            help=CONNECTOR_IP_HELP)
        client_cert_group = parser.add_mutually_exclusive_group()
        client_cert_group.add_argument(
            '--client-certificate',
            dest='cert_data',
            help=CLIENT_CERT_HELP)
        client_cert_group.add_argument(
            '--client-certificate-file',
            dest='cert_file',
            help=CLIENT_CERT_FILE_HELP)

    def args2body(self, parsed_args):
        return gateway_device_args2body(parsed_args)


class DeleteGatewayDevice(neutronV20.DeleteCommand):
    """Delete a given network gateway device."""

    resource = DEV_RESOURCE
    log = logging.getLogger(__name__ + '.DeleteGatewayDevice')


class ListNetworkGateway(neutronV20.ListCommand):
    """List network gateways for a given tenant."""

    resource = GW_RESOURCE
    log = logging.getLogger(__name__ + '.ListNetworkGateway')
    list_columns = ['id', 'name']


class ShowNetworkGateway(neutronV20.ShowCommand):
    """Show information of a given network gateway."""

    resource = GW_RESOURCE
    log = logging.getLogger(__name__ + '.ShowNetworkGateway')


class CreateNetworkGateway(neutronV20.CreateCommand):
    """Create a network gateway."""

    resource = GW_RESOURCE
    log = logging.getLogger(__name__ + '.CreateNetworkGateway')

    def add_known_arguments(self, parser):
        parser.add_argument(
            'name', metavar='NAME',
            help=_('Name of network gateway to create'))
        parser.add_argument(
            '--device', metavar='id=ID,interface_name=NAME_OR_ID',
            action='append',
            help=_('Device info for this gateway, '
            'can be repeated for multiple devices for HA gateways'))

    def args2body(self, parsed_args):
        body = {self.resource: {
            'name': parsed_args.name}}
        devices = []
        if parsed_args.device:
            for device in parsed_args.device:
                devices.append(utils.str2dict(device))
        if devices:
            body[self.resource].update({'devices': devices})
        if parsed_args.tenant_id:
            body[self.resource].update({'tenant_id': parsed_args.tenant_id})
        return body


class DeleteNetworkGateway(neutronV20.DeleteCommand):
    """Delete a given network gateway."""

    resource = GW_RESOURCE
    log = logging.getLogger(__name__ + '.DeleteNetworkGateway')


class UpdateNetworkGateway(neutronV20.UpdateCommand):
    """Update the name for a network gateway."""

    resource = GW_RESOURCE
    log = logging.getLogger(__name__ + '.UpdateNetworkGateway')


class NetworkGatewayInterfaceCommand(neutronV20.NeutronCommand):
    """Base class for connecting/disconnecting networks to/from a gateway."""

    resource = GW_RESOURCE

    def get_parser(self, prog_name):
        parser = super(NetworkGatewayInterfaceCommand,
                       self).get_parser(prog_name)
        parser.add_argument(
            'net_gateway_id', metavar='NET-GATEWAY-ID',
            help=_('ID of the network gateway'))
        parser.add_argument(
            'network_id', metavar='NETWORK-ID',
            help=_('ID of the internal network to connect on the gateway'))
        parser.add_argument(
            '--segmentation-type',
            help=_('L2 segmentation strategy on the external side of '
                   'the gateway (e.g.: VLAN, FLAT)'))
        parser.add_argument(
            '--segmentation-id',
            help=_('Identifier for the L2 segment on the external side '
                   'of the gateway'))
        return parser

    def retrieve_ids(self, client, args):
        gateway_id = neutronV20.find_resourceid_by_name_or_id(
            client, self.resource, args.net_gateway_id)
        network_id = neutronV20.find_resourceid_by_name_or_id(
            client, 'network', args.network_id)
        return (gateway_id, network_id)


class ConnectNetworkGateway(NetworkGatewayInterfaceCommand):
    """Add an internal network interface to a router."""

    log = logging.getLogger(__name__ + '.ConnectNetworkGateway')

    def run(self, parsed_args):
        self.log.debug('run(%s)' % parsed_args)
        neutron_client = self.get_client()
        neutron_client.format = parsed_args.request_format
        (gateway_id, network_id) = self.retrieve_ids(neutron_client,
                                                     parsed_args)
        neutron_client.connect_network_gateway(
            gateway_id, {'network_id': network_id,
                         'segmentation_type': parsed_args.segmentation_type,
                         'segmentation_id': parsed_args.segmentation_id})
        # TODO(Salvatore-Orlando): Do output formatting as
        # any other command
        print(_('Connected network to gateway %s') % gateway_id,
              file=self.app.stdout)


class DisconnectNetworkGateway(NetworkGatewayInterfaceCommand):
    """Remove a network from a network gateway."""

    log = logging.getLogger(__name__ + '.DisconnectNetworkGateway')

    def run(self, parsed_args):
        self.log.debug('run(%s)' % parsed_args)
        neutron_client = self.get_client()
        neutron_client.format = parsed_args.request_format
        (gateway_id, network_id) = self.retrieve_ids(neutron_client,
                                                     parsed_args)
        neutron_client.disconnect_network_gateway(
            gateway_id, {'network_id': network_id,
                         'segmentation_type': parsed_args.segmentation_type,
                         'segmentation_id': parsed_args.segmentation_id})
        # TODO(Salvatore-Orlando): Do output formatting as
        # any other command
        print(_('Disconnected network from gateway %s') % gateway_id,
              file=self.app.stdout)

########NEW FILE########
__FILENAME__ = qos_queue
# Copyright 2013 VMware Inc.
# All Rights Reserved
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import logging

from neutronclient.neutron import v2_0 as neutronV20
from neutronclient.openstack.common.gettextutils import _


class ListQoSQueue(neutronV20.ListCommand):
    """List queues that belong to a given tenant."""

    resource = 'qos_queue'
    log = logging.getLogger(__name__ + '.ListQoSQueue')
    list_columns = ['id', 'name', 'min', 'max',
                    'qos_marking', 'dscp', 'default']


class ShowQoSQueue(neutronV20.ShowCommand):
    """Show information of a given queue."""

    resource = 'qos_queue'
    log = logging.getLogger(__name__ + '.ShowQoSQueue')
    allow_names = True


class CreateQoSQueue(neutronV20.CreateCommand):
    """Create a queue."""

    resource = 'qos_queue'
    log = logging.getLogger(__name__ + '.CreateQoSQueue')

    def add_known_arguments(self, parser):
        parser.add_argument(
            'name', metavar='NAME',
            help=_('Name of queue'))
        parser.add_argument(
            '--min',
            help=_('min-rate')),
        parser.add_argument(
            '--max',
            help=_('max-rate')),
        parser.add_argument(
            '--qos-marking',
            help=_('QOS marking untrusted/trusted')),
        parser.add_argument(
            '--default',
            default=False,
            help=_('If true all ports created with be the size of this queue'
                   ' if queue is not specified')),
        parser.add_argument(
            '--dscp',
            help=_('Differentiated Services Code Point')),

    def args2body(self, parsed_args):
        params = {'name': parsed_args.name,
                  'default': parsed_args.default}
        if parsed_args.min:
            params['min'] = parsed_args.min
        if parsed_args.max:
            params['max'] = parsed_args.max
        if parsed_args.qos_marking:
            params['qos_marking'] = parsed_args.qos_marking
        if parsed_args.dscp:
            params['dscp'] = parsed_args.dscp
        if parsed_args.tenant_id:
            params['tenant_id'] = parsed_args.tenant_id
        return {'qos_queue': params}


class DeleteQoSQueue(neutronV20.DeleteCommand):
    """Delete a given queue."""

    log = logging.getLogger(__name__ + '.DeleteQoSQueue')
    resource = 'qos_queue'
    allow_names = True

########NEW FILE########
__FILENAME__ = policyprofile
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.
#
#@author Abhishek Raut, Cisco Systems
#@author Sergey Sudakovich, Cisco Systems

from __future__ import print_function

import logging

from neutronclient.neutron import v2_0 as neutronV20
from neutronclient.neutron.v2_0 import parse_args_to_dict
from neutronclient.openstack.common.gettextutils import _

RESOURCE = 'policy_profile'


class ListPolicyProfile(neutronV20.ListCommand):
    """List policy profiles that belong to a given tenant."""

    resource = RESOURCE
    log = logging.getLogger(__name__ + '.ListProfile')
    _formatters = {}
    list_columns = ['id', 'name']


class ShowPolicyProfile(neutronV20.ShowCommand):
    """Show information of a given policy profile."""

    resource = RESOURCE
    log = logging.getLogger(__name__ + '.ShowProfile')
    allow_names = True


class UpdatePolicyProfile(neutronV20.UpdateCommand):
    """Update policy profile's information."""

    resource = RESOURCE
    log = logging.getLogger(__name__ + '.UpdatePolicyProfile')


class UpdatePolicyProfileV2(neutronV20.UpdateCommand):
    """Update policy profile's information."""

    api = 'network'
    log = logging.getLogger(__name__ + '.UpdatePolicyProfileV2')
    resource = RESOURCE

    def get_parser(self, prog_name):
        parser = super(UpdatePolicyProfileV2, self).get_parser(prog_name)
        parser.add_argument("--add-tenant",
                            help=_("Add tenant to the policy profile"))
        parser.add_argument("--remove-tenant",
                            help=_("Remove tenant from the policy profile"))
        return parser

    def run(self, parsed_args):
        self.log.debug('run(%s)' % parsed_args)
        neutron_client = self.get_client()
        neutron_client.format = parsed_args.request_format
        data = {self.resource: parse_args_to_dict(parsed_args)}
        if parsed_args.add_tenant:
            data[self.resource]['add_tenant'] = parsed_args.add_tenant
        if parsed_args.remove_tenant:
            data[self.resource]['remove_tenant'] = parsed_args.remove_tenant
        neutron_client.update_policy_profile(parsed_args.id,
                                             {self.resource: data})
        print((_('Updated %(resource)s: %(id)s') %
               {'id': parsed_args.id, 'resource': self.resource}),
              file=self.app.stdout)
        return

########NEW FILE########
__FILENAME__ = port
# Copyright 2012 OpenStack Foundation.
# All Rights Reserved
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.
#

import argparse
import logging

from neutronclient.common import exceptions
from neutronclient.common import utils
from neutronclient.neutron import v2_0 as neutronV20
from neutronclient.openstack.common.gettextutils import _


def _format_fixed_ips(port):
    try:
        return '\n'.join([utils.dumps(ip) for ip in port['fixed_ips']])
    except Exception:
        return ''


class ListPort(neutronV20.ListCommand):
    """List ports that belong to a given tenant."""

    resource = 'port'
    log = logging.getLogger(__name__ + '.ListPort')
    _formatters = {'fixed_ips': _format_fixed_ips, }
    list_columns = ['id', 'name', 'mac_address', 'fixed_ips']
    pagination_support = True
    sorting_support = True


class ListRouterPort(neutronV20.ListCommand):
    """List ports that belong to a given tenant, with specified router."""

    resource = 'port'
    log = logging.getLogger(__name__ + '.ListRouterPort')
    _formatters = {'fixed_ips': _format_fixed_ips, }
    list_columns = ['id', 'name', 'mac_address', 'fixed_ips']
    pagination_support = True
    sorting_support = True

    def get_parser(self, prog_name):
        parser = super(ListRouterPort, self).get_parser(prog_name)
        parser.add_argument(
            'id', metavar='router',
            help=_('ID or name of router to look up'))
        return parser

    def get_data(self, parsed_args):
        neutron_client = self.get_client()
        neutron_client.format = parsed_args.request_format
        _id = neutronV20.find_resourceid_by_name_or_id(
            neutron_client, 'router', parsed_args.id)
        self.values_specs.append('--device_id=%s' % _id)
        return super(ListRouterPort, self).get_data(parsed_args)


class ShowPort(neutronV20.ShowCommand):
    """Show information of a given port."""

    resource = 'port'
    log = logging.getLogger(__name__ + '.ShowPort')


class UpdatePortSecGroupMixin(object):
    def add_arguments_secgroup(self, parser):
        group_sg = parser.add_mutually_exclusive_group()
        group_sg.add_argument(
            '--security-group', metavar='SECURITY_GROUP',
            default=[], action='append', dest='security_groups',
            help=_('Security group associated with the port '
            '(This option can be repeated)'))
        group_sg.add_argument(
            '--no-security-groups',
            action='store_true',
            help=_('Associate no security groups with the port'))

    def _resolv_sgid(self, secgroup):
        return neutronV20.find_resourceid_by_name_or_id(
            self.get_client(), 'security_group', secgroup)

    def args2body_secgroup(self, parsed_args, port):
        if parsed_args.security_groups:
            port['security_groups'] = [self._resolv_sgid(sg) for sg
                                       in parsed_args.security_groups]
        elif parsed_args.no_security_groups:
            port['security_groups'] = []


class UpdateExtraDhcpOptMixin(object):
    def add_arguments_extradhcpopt(self, parser):
        group_sg = parser.add_mutually_exclusive_group()
        group_sg.add_argument(
            '--extra-dhcp-opt',
            default=[],
            action='append',
            dest='extra_dhcp_opts',
            help=_('Extra dhcp options to be assigned to this port: '
                   'opt_name=<dhcp_option_name>,opt_value=<value>, '
                   '(This option can be repeated.)'))

    def args2body_extradhcpopt(self, parsed_args, port):
        ops = []
        if parsed_args.extra_dhcp_opts:
            # the extra_dhcp_opt params (opt_name & opt_value)
            # must come in pairs, if there is a parm error
            # both must be thrown out.
            opt_ele = {}
            edo_err_msg = _("Invalid --extra-dhcp-opt option, can only be: "
                            "opt_name=<dhcp_option_name>,opt_value=<value>, "
                            "(This option can be repeated.")
            for opt in parsed_args.extra_dhcp_opts:
                if opt.split('=')[0] in ['opt_value', 'opt_name']:
                    opt_ele.update(utils.str2dict(opt))
                    if (('opt_name' in opt_ele) and
                        ('opt_value' in opt_ele)):
                        if opt_ele['opt_value'] == 'null':
                            opt_ele['opt_value'] = None
                        ops.append(opt_ele)
                        opt_ele = {}
                    else:
                        raise exceptions.CommandError(edo_err_msg)
                else:
                    raise exceptions.CommandError(edo_err_msg)

        if ops:
            port.update({'extra_dhcp_opts': ops})


class CreatePort(neutronV20.CreateCommand, UpdatePortSecGroupMixin,
                 UpdateExtraDhcpOptMixin):
    """Create a port for a given tenant."""

    resource = 'port'
    log = logging.getLogger(__name__ + '.CreatePort')

    def add_known_arguments(self, parser):
        parser.add_argument(
            '--name',
            help=_('Name of this port'))
        parser.add_argument(
            '--admin-state-down',
            dest='admin_state', action='store_false',
            help=_('Set admin state up to false'))
        parser.add_argument(
            '--admin_state_down',
            dest='admin_state', action='store_false',
            help=argparse.SUPPRESS)
        parser.add_argument(
            '--mac-address',
            help=_('MAC address of this port'))
        parser.add_argument(
            '--mac_address',
            help=argparse.SUPPRESS)
        parser.add_argument(
            '--device-id',
            help=_('Device id of this port'))
        parser.add_argument(
            '--device_id',
            help=argparse.SUPPRESS)
        parser.add_argument(
            '--fixed-ip', metavar='subnet_id=SUBNET,ip_address=IP_ADDR',
            action='append',
            help=_('Desired IP and/or subnet for this port: '
                   'subnet_id=<name_or_id>,ip_address=<ip>, '
                   '(This option can be repeated.)'))
        parser.add_argument(
            '--fixed_ip',
            action='append',
            help=argparse.SUPPRESS)

        self.add_arguments_secgroup(parser)
        self.add_arguments_extradhcpopt(parser)

        parser.add_argument(
            'network_id', metavar='NETWORK',
            help=_('Network id or name this port belongs to'))

    def args2body(self, parsed_args):
        _network_id = neutronV20.find_resourceid_by_name_or_id(
            self.get_client(), 'network', parsed_args.network_id)
        body = {'port': {'admin_state_up': parsed_args.admin_state,
                         'network_id': _network_id, }, }
        if parsed_args.mac_address:
            body['port'].update({'mac_address': parsed_args.mac_address})
        if parsed_args.device_id:
            body['port'].update({'device_id': parsed_args.device_id})
        if parsed_args.tenant_id:
            body['port'].update({'tenant_id': parsed_args.tenant_id})
        if parsed_args.name:
            body['port'].update({'name': parsed_args.name})
        ips = []
        if parsed_args.fixed_ip:
            for ip_spec in parsed_args.fixed_ip:
                ip_dict = utils.str2dict(ip_spec)
                if 'subnet_id' in ip_dict:
                    subnet_name_id = ip_dict['subnet_id']
                    _subnet_id = neutronV20.find_resourceid_by_name_or_id(
                        self.get_client(), 'subnet', subnet_name_id)
                    ip_dict['subnet_id'] = _subnet_id
                ips.append(ip_dict)
        if ips:
            body['port'].update({'fixed_ips': ips})

        self.args2body_secgroup(parsed_args, body['port'])
        self.args2body_extradhcpopt(parsed_args, body['port'])

        return body


class DeletePort(neutronV20.DeleteCommand):
    """Delete a given port."""

    resource = 'port'
    log = logging.getLogger(__name__ + '.DeletePort')


class UpdatePort(neutronV20.UpdateCommand, UpdatePortSecGroupMixin,
                 UpdateExtraDhcpOptMixin):
    """Update port's information."""

    resource = 'port'
    log = logging.getLogger(__name__ + '.UpdatePort')

    def add_known_arguments(self, parser):
        self.add_arguments_secgroup(parser)
        self.add_arguments_extradhcpopt(parser)

    def args2body(self, parsed_args):
        body = {'port': {}}
        self.args2body_secgroup(parsed_args, body['port'])
        self.args2body_extradhcpopt(parsed_args, body['port'])
        return body

########NEW FILE########
__FILENAME__ = quota
# Copyright 2012 OpenStack Foundation.
# All Rights Reserved
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.
#

from __future__ import print_function

import argparse
import logging

from cliff import lister
from cliff import show

from neutronclient.common import exceptions
from neutronclient.common import utils
from neutronclient.neutron import v2_0 as neutronV20
from neutronclient.openstack.common.gettextutils import _


def get_tenant_id(tenant_id, client):
    return (tenant_id if tenant_id else
            client.get_quotas_tenant()['tenant']['tenant_id'])


class DeleteQuota(neutronV20.NeutronCommand):
    """Delete defined quotas of a given tenant."""

    api = 'network'
    resource = 'quota'
    log = logging.getLogger(__name__ + '.DeleteQuota')

    def get_parser(self, prog_name):
        parser = super(DeleteQuota, self).get_parser(prog_name)
        parser.add_argument(
            '--tenant-id', metavar='tenant-id',
            help=_('The owner tenant ID'))
        parser.add_argument(
            '--tenant_id',
            help=argparse.SUPPRESS)
        return parser

    def run(self, parsed_args):
        self.log.debug('run(%s)' % parsed_args)
        neutron_client = self.get_client()
        neutron_client.format = parsed_args.request_format
        tenant_id = get_tenant_id(parsed_args.tenant_id,
                                  neutron_client)
        obj_deleter = getattr(neutron_client,
                              "delete_%s" % self.resource)
        obj_deleter(tenant_id)
        print((_('Deleted %(resource)s: %(tenant_id)s')
               % {'tenant_id': tenant_id,
                  'resource': self.resource}),
              file=self.app.stdout)
        return


class ListQuota(neutronV20.NeutronCommand, lister.Lister):
    """List quotas of all tenants who have non-default quota values."""

    api = 'network'
    resource = 'quota'
    log = logging.getLogger(__name__ + '.ListQuota')

    def get_parser(self, prog_name):
        parser = super(ListQuota, self).get_parser(prog_name)
        return parser

    def get_data(self, parsed_args):
        self.log.debug('get_data(%s)', parsed_args)
        neutron_client = self.get_client()
        search_opts = {}
        self.log.debug('search options: %s', search_opts)
        neutron_client.format = parsed_args.request_format
        obj_lister = getattr(neutron_client,
                             "list_%ss" % self.resource)
        data = obj_lister(**search_opts)
        info = []
        collection = self.resource + "s"
        if collection in data:
            info = data[collection]
        _columns = len(info) > 0 and sorted(info[0].keys()) or []
        return (_columns, (utils.get_item_properties(s, _columns)
                for s in info))


class ShowQuota(neutronV20.NeutronCommand, show.ShowOne):
    """Show quotas of a given tenant

    """
    api = 'network'
    resource = "quota"
    log = logging.getLogger(__name__ + '.ShowQuota')

    def get_parser(self, prog_name):
        parser = super(ShowQuota, self).get_parser(prog_name)
        parser.add_argument(
            '--tenant-id', metavar='tenant-id',
            help=_('The owner tenant ID'))
        parser.add_argument(
            '--tenant_id',
            help=argparse.SUPPRESS)
        return parser

    def get_data(self, parsed_args):
        self.log.debug('get_data(%s)', parsed_args)
        neutron_client = self.get_client()
        neutron_client.format = parsed_args.request_format
        tenant_id = get_tenant_id(parsed_args.tenant_id,
                                  neutron_client)
        params = {}
        obj_shower = getattr(neutron_client,
                             "show_%s" % self.resource)
        data = obj_shower(tenant_id, **params)
        if self.resource in data:
            for k, v in data[self.resource].iteritems():
                if isinstance(v, list):
                    value = ""
                    for _item in v:
                        if value:
                            value += "\n"
                        if isinstance(_item, dict):
                            value += utils.dumps(_item)
                        else:
                            value += str(_item)
                    data[self.resource][k] = value
                elif v is None:
                    data[self.resource][k] = ''
            return zip(*sorted(data[self.resource].iteritems()))
        else:
            return None


class UpdateQuota(neutronV20.NeutronCommand, show.ShowOne):
    """Define tenant's quotas not to use defaults."""

    resource = 'quota'
    log = logging.getLogger(__name__ + '.UpdateQuota')

    def get_parser(self, prog_name):
        parser = super(UpdateQuota, self).get_parser(prog_name)
        parser.add_argument(
            '--tenant-id', metavar='tenant-id',
            help=_('The owner tenant ID'))
        parser.add_argument(
            '--tenant_id',
            help=argparse.SUPPRESS)
        parser.add_argument(
            '--network', metavar='networks',
            help=_('The limit of networks'))
        parser.add_argument(
            '--subnet', metavar='subnets',
            help=_('The limit of subnets'))
        parser.add_argument(
            '--port', metavar='ports',
            help=_('The limit of ports'))
        parser.add_argument(
            '--router', metavar='routers',
            help=_('The limit of routers'))
        parser.add_argument(
            '--floatingip', metavar='floatingips',
            help=_('The limit of floating IPs'))
        parser.add_argument(
            '--security-group', metavar='security_groups',
            help=_('The limit of security groups'))
        parser.add_argument(
            '--security-group-rule', metavar='security_group_rules',
            help=_('The limit of security groups rules'))
        parser.add_argument(
            '--vip', metavar='vips',
            help=_('the limit of vips'))
        parser.add_argument(
            '--pool', metavar='pools',
            help=_('the limit of pools'))
        parser.add_argument(
            '--member', metavar='members',
            help=_('the limit of pool members'))
        parser.add_argument(
            '--health-monitor', metavar='health_monitors',
            help=_('the limit of health monitors'))

        return parser

    def _validate_int(self, name, value):
        try:
            return_value = int(value)
        except Exception:
            message = (_('Quota limit for %(name)s must be an integer') %
                       {'name': name})
            raise exceptions.NeutronClientException(message=message)
        return return_value

    def args2body(self, parsed_args):
        quota = {}
        for resource in ('network', 'subnet', 'port', 'router', 'floatingip',
                         'security_group', 'security_group_rule',
                         'vip', 'pool', 'member', 'health_monitor'):
            if getattr(parsed_args, resource):
                quota[resource] = self._validate_int(
                    resource,
                    getattr(parsed_args, resource))
        return {self.resource: quota}

    def get_data(self, parsed_args):
        self.log.debug('run(%s)', parsed_args)
        neutron_client = self.get_client()
        neutron_client.format = parsed_args.request_format
        _extra_values = neutronV20.parse_args_to_dict(self.values_specs)
        neutronV20._merge_args(self, parsed_args, _extra_values,
                               self.values_specs)
        body = self.args2body(parsed_args)
        if self.resource in body:
            body[self.resource].update(_extra_values)
        else:
            body[self.resource] = _extra_values
        obj_updator = getattr(neutron_client,
                              "update_%s" % self.resource)
        tenant_id = get_tenant_id(parsed_args.tenant_id,
                                  neutron_client)
        data = obj_updator(tenant_id, body)
        if self.resource in data:
            for k, v in data[self.resource].iteritems():
                if isinstance(v, list):
                    value = ""
                    for _item in v:
                        if value:
                            value += "\n"
                        if isinstance(_item, dict):
                            value += utils.dumps(_item)
                        else:
                            value += str(_item)
                    data[self.resource][k] = value
                elif v is None:
                    data[self.resource][k] = ''
            return zip(*sorted(data[self.resource].iteritems()))
        else:
            return None

########NEW FILE########
__FILENAME__ = router
# Copyright 2012 OpenStack Foundation.
# All Rights Reserved
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.
#

from __future__ import print_function

import argparse
import logging

from neutronclient.common import exceptions
from neutronclient.common import utils
from neutronclient.neutron import v2_0 as neutronV20
from neutronclient.openstack.common.gettextutils import _


def _format_external_gateway_info(router):
    try:
        return utils.dumps(router['external_gateway_info'])
    except Exception:
        return ''


class ListRouter(neutronV20.ListCommand):
    """List routers that belong to a given tenant."""

    resource = 'router'
    log = logging.getLogger(__name__ + '.ListRouter')
    _formatters = {'external_gateway_info': _format_external_gateway_info, }
    list_columns = ['id', 'name', 'external_gateway_info']
    pagination_support = True
    sorting_support = True


class ShowRouter(neutronV20.ShowCommand):
    """Show information of a given router."""

    resource = 'router'
    log = logging.getLogger(__name__ + '.ShowRouter')


class CreateRouter(neutronV20.CreateCommand):
    """Create a router for a given tenant."""

    resource = 'router'
    log = logging.getLogger(__name__ + '.CreateRouter')
    _formatters = {'external_gateway_info': _format_external_gateway_info, }

    def add_known_arguments(self, parser):
        parser.add_argument(
            '--admin-state-down',
            dest='admin_state', action='store_false',
            help=_('Set Admin State Up to false'))
        parser.add_argument(
            '--admin_state_down',
            dest='admin_state', action='store_false',
            help=argparse.SUPPRESS)
        parser.add_argument(
            'name', metavar='NAME',
            help=_('Name of router to create'))
        parser.add_argument(
            'distributed', action='store_true',
            help=_('Create a distributed router (VMware NSX plugin only)'))

    def args2body(self, parsed_args):
        body = {'router': {
            'name': parsed_args.name,
            'admin_state_up': parsed_args.admin_state, }, }
        if parsed_args.tenant_id:
            body['router'].update({'tenant_id': parsed_args.tenant_id})
        return body


class DeleteRouter(neutronV20.DeleteCommand):
    """Delete a given router."""

    log = logging.getLogger(__name__ + '.DeleteRouter')
    resource = 'router'


class UpdateRouter(neutronV20.UpdateCommand):
    """Update router's information."""

    log = logging.getLogger(__name__ + '.UpdateRouter')
    resource = 'router'


class RouterInterfaceCommand(neutronV20.NeutronCommand):
    """Based class to Add/Remove router interface."""

    api = 'network'
    resource = 'router'

    def call_api(self, neutron_client, router_id, body):
        raise NotImplementedError()

    def success_message(self, router_id, portinfo):
        raise NotImplementedError()

    def get_parser(self, prog_name):
        parser = super(RouterInterfaceCommand, self).get_parser(prog_name)
        parser.add_argument(
            'router_id', metavar='router-id',
            help=_('ID of the router'))
        parser.add_argument(
            'interface', metavar='INTERFACE',
            help=_('The format is "SUBNET|subnet=SUBNET|port=PORT". '
            'Either a subnet or port must be specified. '
            'Both ID and name are accepted as SUBNET or PORT. '
            'Note that "subnet=" can be omitted when specifying subnet.'))
        return parser

    def run(self, parsed_args):
        self.log.debug('run(%s)' % parsed_args)
        neutron_client = self.get_client()
        neutron_client.format = parsed_args.request_format

        if '=' in parsed_args.interface:
            resource, value = parsed_args.interface.split('=', 1)
            if resource not in ['subnet', 'port']:
                exceptions.CommandError(_('You must specify either subnet or '
                                        'port for INTERFACE parameter.'))
        else:
            resource = 'subnet'
            value = parsed_args.interface

        _router_id = neutronV20.find_resourceid_by_name_or_id(
            neutron_client, self.resource, parsed_args.router_id)

        _interface_id = neutronV20.find_resourceid_by_name_or_id(
            neutron_client, resource, value)
        body = {'%s_id' % resource: _interface_id}

        portinfo = self.call_api(neutron_client, _router_id, body)
        print(self.success_message(parsed_args.router_id, portinfo),
              file=self.app.stdout)


class AddInterfaceRouter(RouterInterfaceCommand):
    """Add an internal network interface to a router."""

    log = logging.getLogger(__name__ + '.AddInterfaceRouter')

    def call_api(self, neutron_client, router_id, body):
        return neutron_client.add_interface_router(router_id, body)

    def success_message(self, router_id, portinfo):
        return (_('Added interface %(port)s to router %(router)s.') %
                {'router': router_id, 'port': portinfo['port_id']})


class RemoveInterfaceRouter(RouterInterfaceCommand):
    """Remove an internal network interface from a router."""

    log = logging.getLogger(__name__ + '.RemoveInterfaceRouter')

    def call_api(self, neutron_client, router_id, body):
        return neutron_client.remove_interface_router(router_id, body)

    def success_message(self, router_id, portinfo):
        # portinfo is not used since it is None for router-interface-delete.
        return _('Removed interface from router %s.') % router_id


class SetGatewayRouter(neutronV20.NeutronCommand):
    """Set the external network gateway for a router."""

    log = logging.getLogger(__name__ + '.SetGatewayRouter')
    api = 'network'
    resource = 'router'

    def get_parser(self, prog_name):
        parser = super(SetGatewayRouter, self).get_parser(prog_name)
        parser.add_argument(
            'router_id', metavar='router-id',
            help=_('ID of the router'))
        parser.add_argument(
            'external_network_id', metavar='external-network-id',
            help=_('ID of the external network for the gateway'))
        parser.add_argument(
            '--disable-snat', action='store_true',
            help=_('Disable Source NAT on the router gateway'))
        return parser

    def run(self, parsed_args):
        self.log.debug('run(%s)' % parsed_args)
        neutron_client = self.get_client()
        neutron_client.format = parsed_args.request_format
        _router_id = neutronV20.find_resourceid_by_name_or_id(
            neutron_client, self.resource, parsed_args.router_id)
        _ext_net_id = neutronV20.find_resourceid_by_name_or_id(
            neutron_client, 'network', parsed_args.external_network_id)
        router_dict = {'network_id': _ext_net_id}
        if parsed_args.disable_snat:
            router_dict['enable_snat'] = False
        neutron_client.add_gateway_router(_router_id, router_dict)
        print(_('Set gateway for router %s') % parsed_args.router_id,
              file=self.app.stdout)


class RemoveGatewayRouter(neutronV20.NeutronCommand):
    """Remove an external network gateway from a router."""

    log = logging.getLogger(__name__ + '.RemoveGatewayRouter')
    api = 'network'
    resource = 'router'

    def get_parser(self, prog_name):
        parser = super(RemoveGatewayRouter, self).get_parser(prog_name)
        parser.add_argument(
            'router_id', metavar='router-id',
            help=_('ID of the router'))
        return parser

    def run(self, parsed_args):
        self.log.debug('run(%s)' % parsed_args)
        neutron_client = self.get_client()
        neutron_client.format = parsed_args.request_format
        _router_id = neutronV20.find_resourceid_by_name_or_id(
            neutron_client, self.resource, parsed_args.router_id)
        neutron_client.remove_gateway_router(_router_id)
        print(_('Removed gateway from router %s') % parsed_args.router_id,
              file=self.app.stdout)

########NEW FILE########
__FILENAME__ = securitygroup
# Copyright 2012 OpenStack Foundation.
# All Rights Reserved
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.
#

import argparse
import logging

from neutronclient.neutron import v2_0 as neutronV20
from neutronclient.openstack.common.gettextutils import _


class ListSecurityGroup(neutronV20.ListCommand):
    """List security groups that belong to a given tenant."""

    resource = 'security_group'
    log = logging.getLogger(__name__ + '.ListSecurityGroup')
    list_columns = ['id', 'name', 'description']
    pagination_support = True
    sorting_support = True


class ShowSecurityGroup(neutronV20.ShowCommand):
    """Show information of a given security group."""

    resource = 'security_group'
    log = logging.getLogger(__name__ + '.ShowSecurityGroup')
    allow_names = True


class CreateSecurityGroup(neutronV20.CreateCommand):
    """Create a security group."""

    resource = 'security_group'
    log = logging.getLogger(__name__ + '.CreateSecurityGroup')

    def add_known_arguments(self, parser):
        parser.add_argument(
            'name', metavar='NAME',
            help=_('Name of security group'))
        parser.add_argument(
            '--description',
            help=_('Description of security group'))

    def args2body(self, parsed_args):
        body = {'security_group': {
            'name': parsed_args.name}}
        if parsed_args.description:
            body['security_group'].update(
                {'description': parsed_args.description})
        if parsed_args.tenant_id:
            body['security_group'].update({'tenant_id': parsed_args.tenant_id})
        return body


class DeleteSecurityGroup(neutronV20.DeleteCommand):
    """Delete a given security group."""

    log = logging.getLogger(__name__ + '.DeleteSecurityGroup')
    resource = 'security_group'
    allow_names = True


class UpdateSecurityGroup(neutronV20.UpdateCommand):
    """Update a given security group."""

    log = logging.getLogger(__name__ + '.UpdateSecurityGroup')
    resource = 'security_group'

    def add_known_arguments(self, parser):
        parser.add_argument(
            '--name',
            help=_('Name of security group'))
        parser.add_argument(
            '--description',
            help=_('Description of security group'))

    def args2body(self, parsed_args):
        body = {'security_group': {}}
        if parsed_args.name:
            body['security_group'].update(
                {'name': parsed_args.name})
        if parsed_args.description:
            body['security_group'].update(
                {'description': parsed_args.description})
        return body


class ListSecurityGroupRule(neutronV20.ListCommand):
    """List security group rules that belong to a given tenant."""

    resource = 'security_group_rule'
    log = logging.getLogger(__name__ + '.ListSecurityGroupRule')
    list_columns = ['id', 'security_group_id', 'direction', 'protocol',
                    'remote_ip_prefix', 'remote_group_id']
    replace_rules = {'security_group_id': 'security_group',
                     'remote_group_id': 'remote_group'}
    pagination_support = True
    sorting_support = True

    def get_parser(self, prog_name):
        parser = super(ListSecurityGroupRule, self).get_parser(prog_name)
        parser.add_argument(
            '--no-nameconv', action='store_true',
            help=_('Do not convert security group ID to its name'))
        return parser

    @staticmethod
    def replace_columns(cols, rules, reverse=False):
        if reverse:
            rules = dict((rules[k], k) for k in rules.keys())
        return [rules.get(col, col) for col in cols]

    def retrieve_list(self, parsed_args):
        parsed_args.fields = self.replace_columns(parsed_args.fields,
                                                  self.replace_rules,
                                                  reverse=True)
        return super(ListSecurityGroupRule, self).retrieve_list(parsed_args)

    def extend_list(self, data, parsed_args):
        if parsed_args.no_nameconv:
            return
        neutron_client = self.get_client()
        search_opts = {'fields': ['id', 'name']}
        if self.pagination_support:
            page_size = parsed_args.page_size
            if page_size:
                search_opts.update({'limit': page_size})
        sec_group_ids = set()
        for rule in data:
            for key in self.replace_rules:
                sec_group_ids.add(rule[key])
        search_opts.update({"id": sec_group_ids})
        secgroups = neutron_client.list_security_groups(**search_opts)
        secgroups = secgroups.get('security_groups', [])
        sg_dict = dict([(sg['id'], sg['name'])
                        for sg in secgroups if sg['name']])
        for rule in data:
            for key in self.replace_rules:
                rule[key] = sg_dict.get(rule[key], rule[key])

    def setup_columns(self, info, parsed_args):
        parsed_args.columns = self.replace_columns(parsed_args.columns,
                                                   self.replace_rules,
                                                   reverse=True)
        # NOTE(amotoki): 2nd element of the tuple returned by setup_columns()
        # is a generator, so if you need to create a look using the generator
        # object, you need to recreate a generator to show a list expectedly.
        info = super(ListSecurityGroupRule, self).setup_columns(info,
                                                                parsed_args)
        cols = info[0]
        if not parsed_args.no_nameconv:
            cols = self.replace_columns(info[0], self.replace_rules)
            parsed_args.columns = cols
        return (cols, info[1])


class ShowSecurityGroupRule(neutronV20.ShowCommand):
    """Show information of a given security group rule."""

    resource = 'security_group_rule'
    log = logging.getLogger(__name__ + '.ShowSecurityGroupRule')
    allow_names = False


class CreateSecurityGroupRule(neutronV20.CreateCommand):
    """Create a security group rule."""

    resource = 'security_group_rule'
    log = logging.getLogger(__name__ + '.CreateSecurityGroupRule')

    def add_known_arguments(self, parser):
        parser.add_argument(
            'security_group_id', metavar='SECURITY_GROUP',
            help=_('Security group name or id to add rule.'))
        parser.add_argument(
            '--direction',
            default='ingress', choices=['ingress', 'egress'],
            help=_('Direction of traffic: ingress/egress'))
        parser.add_argument(
            '--ethertype',
            default='IPv4',
            help=_('IPv4/IPv6'))
        parser.add_argument(
            '--protocol',
            help=_('Protocol of packet'))
        parser.add_argument(
            '--port-range-min',
            help=_('Starting port range'))
        parser.add_argument(
            '--port_range_min',
            help=argparse.SUPPRESS)
        parser.add_argument(
            '--port-range-max',
            help=_('Ending port range'))
        parser.add_argument(
            '--port_range_max',
            help=argparse.SUPPRESS)
        parser.add_argument(
            '--remote-ip-prefix',
            help=_('CIDR to match on'))
        parser.add_argument(
            '--remote_ip_prefix',
            help=argparse.SUPPRESS)
        parser.add_argument(
            '--remote-group-id', metavar='REMOTE_GROUP',
            help=_('Remote security group name or id to apply rule'))
        parser.add_argument(
            '--remote_group_id',
            help=argparse.SUPPRESS)

    def args2body(self, parsed_args):
        _security_group_id = neutronV20.find_resourceid_by_name_or_id(
            self.get_client(), 'security_group', parsed_args.security_group_id)
        body = {'security_group_rule': {
            'security_group_id': _security_group_id,
            'direction': parsed_args.direction,
            'ethertype': parsed_args.ethertype}}
        if parsed_args.protocol:
            body['security_group_rule'].update(
                {'protocol': parsed_args.protocol})
        if parsed_args.port_range_min:
            body['security_group_rule'].update(
                {'port_range_min': parsed_args.port_range_min})
        if parsed_args.port_range_max:
            body['security_group_rule'].update(
                {'port_range_max': parsed_args.port_range_max})
        if parsed_args.remote_ip_prefix:
            body['security_group_rule'].update(
                {'remote_ip_prefix': parsed_args.remote_ip_prefix})
        if parsed_args.remote_group_id:
            _remote_group_id = neutronV20.find_resourceid_by_name_or_id(
                self.get_client(), 'security_group',
                parsed_args.remote_group_id)
            body['security_group_rule'].update(
                {'remote_group_id': _remote_group_id})
        if parsed_args.tenant_id:
            body['security_group_rule'].update(
                {'tenant_id': parsed_args.tenant_id})
        return body


class DeleteSecurityGroupRule(neutronV20.DeleteCommand):
    """Delete a given security group rule."""

    log = logging.getLogger(__name__ + '.DeleteSecurityGroupRule')
    resource = 'security_group_rule'
    allow_names = False

########NEW FILE########
__FILENAME__ = servicetype
# Copyright 2013 OpenStack Foundation.
# All Rights Reserved
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.
#

import logging

from neutronclient.neutron import v2_0 as neutronV20


class ListServiceProvider(neutronV20.ListCommand):
    """List service providers."""

    resource = 'service_provider'
    log = logging.getLogger(__name__ + '.ListServiceProviders')
    list_columns = ['service_type', 'name', 'default']
    _formatters = {}
    pagination_support = True
    sorting_support = True

########NEW FILE########
__FILENAME__ = subnet
# Copyright 2012 OpenStack Foundation.
# All Rights Reserved
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.
#

import argparse
import logging

from neutronclient.common import exceptions
from neutronclient.common import utils
from neutronclient.neutron import v2_0 as neutronV20
from neutronclient.openstack.common.gettextutils import _


def _format_allocation_pools(subnet):
    try:
        return '\n'.join([utils.dumps(pool) for pool in
                          subnet['allocation_pools']])
    except Exception:
        return ''


def _format_dns_nameservers(subnet):
    try:
        return '\n'.join([utils.dumps(server) for server in
                          subnet['dns_nameservers']])
    except Exception:
        return ''


def _format_host_routes(subnet):
    try:
        return '\n'.join([utils.dumps(route) for route in
                          subnet['host_routes']])
    except Exception:
        return ''


class ListSubnet(neutronV20.ListCommand):
    """List subnets that belong to a given tenant."""

    resource = 'subnet'
    log = logging.getLogger(__name__ + '.ListSubnet')
    _formatters = {'allocation_pools': _format_allocation_pools,
                   'dns_nameservers': _format_dns_nameservers,
                   'host_routes': _format_host_routes, }
    list_columns = ['id', 'name', 'cidr', 'allocation_pools']
    pagination_support = True
    sorting_support = True


class ShowSubnet(neutronV20.ShowCommand):
    """Show information of a given subnet."""

    resource = 'subnet'
    log = logging.getLogger(__name__ + '.ShowSubnet')


class CreateSubnet(neutronV20.CreateCommand):
    """Create a subnet for a given tenant."""

    resource = 'subnet'
    log = logging.getLogger(__name__ + '.CreateSubnet')

    def add_known_arguments(self, parser):
        parser.add_argument(
            '--name',
            help=_('Name of this subnet'))
        parser.add_argument(
            '--ip-version',
            type=int,
            default=4, choices=[4, 6],
            help=_('IP version with default 4'))
        parser.add_argument(
            '--ip_version',
            type=int,
            choices=[4, 6],
            help=argparse.SUPPRESS)
        parser.add_argument(
            '--gateway', metavar='GATEWAY_IP',
            help=_('Gateway ip of this subnet'))
        parser.add_argument(
            '--no-gateway',
            action='store_true',
            help=_('No distribution of gateway'))
        parser.add_argument(
            '--allocation-pool', metavar='start=IP_ADDR,end=IP_ADDR',
            action='append', dest='allocation_pools', type=utils.str2dict,
            help=_('Allocation pool IP addresses for this subnet '
            '(This option can be repeated)'))
        parser.add_argument(
            '--allocation_pool',
            action='append', dest='allocation_pools', type=utils.str2dict,
            help=argparse.SUPPRESS)
        parser.add_argument(
            '--host-route', metavar='destination=CIDR,nexthop=IP_ADDR',
            action='append', dest='host_routes', type=utils.str2dict,
            help=_('Additional route (This option can be repeated)'))
        parser.add_argument(
            '--dns-nameserver', metavar='DNS_NAMESERVER',
            action='append', dest='dns_nameservers',
            help=_('DNS name server for this subnet '
            '(This option can be repeated)'))
        parser.add_argument(
            '--disable-dhcp',
            action='store_true',
            help=_('Disable DHCP for this subnet'))
        parser.add_argument(
            'network_id', metavar='NETWORK',
            help=_('Network id or name this subnet belongs to'))
        parser.add_argument(
            'cidr', metavar='CIDR',
            help=_('CIDR of subnet to create'))

    def args2body(self, parsed_args):
        _network_id = neutronV20.find_resourceid_by_name_or_id(
            self.get_client(), 'network', parsed_args.network_id)
        body = {'subnet': {'cidr': parsed_args.cidr,
                           'network_id': _network_id,
                           'ip_version': parsed_args.ip_version, }, }

        if parsed_args.gateway and parsed_args.no_gateway:
            raise exceptions.CommandError(_("--gateway option and "
                                          "--no-gateway option can "
                                          "not be used same time"))
        if parsed_args.no_gateway:
            body['subnet'].update({'gateway_ip': None})
        if parsed_args.gateway:
            body['subnet'].update({'gateway_ip': parsed_args.gateway})
        if parsed_args.tenant_id:
            body['subnet'].update({'tenant_id': parsed_args.tenant_id})
        if parsed_args.name:
            body['subnet'].update({'name': parsed_args.name})
        if parsed_args.disable_dhcp:
            body['subnet'].update({'enable_dhcp': False})
        if parsed_args.allocation_pools:
            body['subnet']['allocation_pools'] = parsed_args.allocation_pools
        if parsed_args.host_routes:
            body['subnet']['host_routes'] = parsed_args.host_routes
        if parsed_args.dns_nameservers:
            body['subnet']['dns_nameservers'] = parsed_args.dns_nameservers

        return body


class DeleteSubnet(neutronV20.DeleteCommand):
    """Delete a given subnet."""

    resource = 'subnet'
    log = logging.getLogger(__name__ + '.DeleteSubnet')


class UpdateSubnet(neutronV20.UpdateCommand):
    """Update subnet's information."""

    resource = 'subnet'
    log = logging.getLogger(__name__ + '.UpdateSubnet')

########NEW FILE########
__FILENAME__ = ikepolicy
#    (c) Copyright 2013 Hewlett-Packard Development Company, L.P.
#    All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.
#
# @author: Swaminathan Vasudevan, Hewlett-Packard.
#

import logging

from neutronclient.common import utils
from neutronclient.neutron import v2_0 as neutronv20
from neutronclient.neutron.v2_0.vpn import utils as vpn_utils
from neutronclient.openstack.common.gettextutils import _


class ListIKEPolicy(neutronv20.ListCommand):
    """List IKEPolicies that belong to a tenant."""

    resource = 'ikepolicy'
    log = logging.getLogger(__name__ + '.ListIKEPolicy')
    list_columns = ['id', 'name', 'auth_algorithm',
                    'encryption_algorithm', 'ike_version', 'pfs']
    _formatters = {}
    pagination_support = True
    sorting_support = True


class ShowIKEPolicy(neutronv20.ShowCommand):
    """Show information of a given IKEPolicy."""

    resource = 'ikepolicy'
    log = logging.getLogger(__name__ + '.ShowIKEPolicy')


class CreateIKEPolicy(neutronv20.CreateCommand):
    """Create an IKEPolicy."""

    resource = 'ikepolicy'
    log = logging.getLogger(__name__ + '.CreateIKEPolicy')

    def add_known_arguments(self, parser):
        parser.add_argument(
            '--description',
            help=_('Description of the IKE policy'))
        parser.add_argument(
            '--auth-algorithm',
            default='sha1', choices=['sha1'],
            help=_('Authentication algorithm in lowercase. '
                   'default:sha1'))
        parser.add_argument(
            '--encryption-algorithm',
            default='aes-128', choices=['3des',
                                        'aes-128',
                                        'aes-192',
                                        'aes-256'],
            help=_('Encryption Algorithm in lowercase, default:aes-128'))
        parser.add_argument(
            '--phase1-negotiation-mode',
            default='main', choices=['main'],
            help=_('IKE Phase1 negotiation mode in lowercase, default:main'))
        parser.add_argument(
            '--ike-version',
            default='v1', choices=['v1', 'v2'],
            help=_('IKE version in lowercase, default:v1'))
        parser.add_argument(
            '--pfs',
            default='group5', choices=['group2', 'group5', 'group14'],
            help=_('Perfect Forward Secrecy in lowercase, default:group5'))
        parser.add_argument(
            '--lifetime',
            metavar="units=UNITS,value=VALUE",
            type=utils.str2dict,
            help=vpn_utils.lifetime_help("IKE"))
        parser.add_argument(
            'name', metavar='NAME',
            help=_('Name of the IKE Policy'))

    def args2body(self, parsed_args):

        body = {'ikepolicy': {
            'auth_algorithm': parsed_args.auth_algorithm,
            'encryption_algorithm': parsed_args.encryption_algorithm,
            'phase1_negotiation_mode': parsed_args.phase1_negotiation_mode,
            'ike_version': parsed_args.ike_version,
            'pfs': parsed_args.pfs,
        }, }
        if parsed_args.name:
            body['ikepolicy'].update({'name': parsed_args.name})
        if parsed_args.description:
            body['ikepolicy'].update({'description': parsed_args.description})
        if parsed_args.tenant_id:
            body['ikepolicy'].update({'tenant_id': parsed_args.tenant_id})
        if parsed_args.lifetime:
            vpn_utils.validate_lifetime_dict(parsed_args.lifetime)
            body['ikepolicy'].update({'lifetime': parsed_args.lifetime})
        return body


class UpdateIKEPolicy(neutronv20.UpdateCommand):
    """Update a given IKE Policy."""

    resource = 'ikepolicy'
    log = logging.getLogger(__name__ + '.UpdateIKEPolicy')

    def add_known_arguments(self, parser):
        parser.add_argument(
            '--lifetime',
            metavar="units=UNITS,value=VALUE",
            type=utils.str2dict,
            help=vpn_utils.lifetime_help("IKE"))

    def args2body(self, parsed_args):

        body = {'ikepolicy': {
        }, }
        if parsed_args.lifetime:
            vpn_utils.validate_lifetime_dict(parsed_args.lifetime)
            body['ikepolicy'].update({'lifetime': parsed_args.lifetime})
        return body


class DeleteIKEPolicy(neutronv20.DeleteCommand):
    """Delete a given IKE Policy."""

    resource = 'ikepolicy'
    log = logging.getLogger(__name__ + '.DeleteIKEPolicy')

########NEW FILE########
__FILENAME__ = ipsecpolicy
#    (c) Copyright 2013 Hewlett-Packard Development Company, L.P.
#    All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.
#
# @author: Swaminathan Vasudevan, Hewlett-Packard.

import logging

from neutronclient.common import utils
from neutronclient.neutron import v2_0 as neutronv20
from neutronclient.neutron.v2_0.vpn import utils as vpn_utils
from neutronclient.openstack.common.gettextutils import _


class ListIPsecPolicy(neutronv20.ListCommand):
    """List ipsecpolicies that belongs to a given tenant connection."""

    resource = 'ipsecpolicy'
    log = logging.getLogger(__name__ + '.ListIPsecPolicy')
    list_columns = ['id', 'name', 'auth_algorithm',
                    'encryption_algorithm', 'pfs']
    _formatters = {}
    pagination_support = True
    sorting_support = True


class ShowIPsecPolicy(neutronv20.ShowCommand):
    """Show information of a given ipsecpolicy."""

    resource = 'ipsecpolicy'
    log = logging.getLogger(__name__ + '.ShowIPsecPolicy')


class CreateIPsecPolicy(neutronv20.CreateCommand):
    """Create an ipsecpolicy."""

    resource = 'ipsecpolicy'
    log = logging.getLogger(__name__ + '.CreateIPsecPolicy')

    def add_known_arguments(self, parser):
        parser.add_argument(
            '--description',
            help=_('Description of the IPsecPolicy'))
        parser.add_argument(
            '--transform-protocol',
            default='esp', choices=['esp', 'ah', 'ah-esp'],
            help=_('Transform Protocol in lowercase, default:esp'))
        parser.add_argument(
            '--auth-algorithm',
            default='sha1', choices=['sha1'],
            help=_('Authentication algorithm in lowercase, default:sha1'))
        parser.add_argument(
            '--encryption-algorithm',
            default='aes-128', choices=['3des',
                                        'aes-128',
                                        'aes-192',
                                        'aes-256'],
            help=_('Encryption Algorithm in lowercase, default:aes-128'))
        parser.add_argument(
            '--encapsulation-mode',
            default='tunnel', choices=['tunnel', 'transport'],
            help=_('Encapsulation Mode in lowercase, default:tunnel'))
        parser.add_argument(
            '--pfs',
            default='group5', choices=['group2', 'group5', 'group14'],
            help=_('Perfect Forward Secrecy in lowercase, default:group5'))
        parser.add_argument(
            '--lifetime',
            metavar="units=UNITS,value=VALUE",
            type=utils.str2dict,
            help=vpn_utils.lifetime_help("IPsec"))
        parser.add_argument(
            'name', metavar='NAME',
            help=_('Name of the IPsecPolicy'))

    def args2body(self, parsed_args):

        body = {'ipsecpolicy': {
            'auth_algorithm': parsed_args.auth_algorithm,
            'encryption_algorithm': parsed_args.encryption_algorithm,
            'encapsulation_mode': parsed_args.encapsulation_mode,
            'transform_protocol': parsed_args.transform_protocol,
            'pfs': parsed_args.pfs,
        }, }
        if parsed_args.name:
            body['ipsecpolicy'].update({'name': parsed_args.name})
        if parsed_args.description:
            body['ipsecpolicy'].update(
                {'description': parsed_args.description}
            )
        if parsed_args.tenant_id:
            body['ipsecpolicy'].update({'tenant_id': parsed_args.tenant_id})
        if parsed_args.lifetime:
            vpn_utils.validate_lifetime_dict(parsed_args.lifetime)
            body['ipsecpolicy'].update({'lifetime': parsed_args.lifetime})
        return body


class UpdateIPsecPolicy(neutronv20.UpdateCommand):
    """Update a given ipsec policy."""

    resource = 'ipsecpolicy'
    log = logging.getLogger(__name__ + '.UpdateIPsecPolicy')

    def add_known_arguments(self, parser):
        parser.add_argument(
            '--lifetime',
            metavar="units=UNITS,value=VALUE",
            type=utils.str2dict,
            help=vpn_utils.lifetime_help("IPsec"))

    def args2body(self, parsed_args):

        body = {'ipsecpolicy': {
        }, }
        if parsed_args.lifetime:
            vpn_utils.validate_lifetime_dict(parsed_args.lifetime)
            body['ipsecpolicy'].update({'lifetime': parsed_args.lifetime})
        return body


class DeleteIPsecPolicy(neutronv20.DeleteCommand):
    """Delete a given ipsecpolicy."""

    resource = 'ipsecpolicy'
    log = logging.getLogger(__name__ + '.DeleteIPsecPolicy')

########NEW FILE########
__FILENAME__ = ipsec_site_connection
#    (c) Copyright 2013 Hewlett-Packard Development Company, L.P.
#    All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.
#
# @author: Swaminathan Vasudevan, Hewlett-Packard.
#

import logging

from neutronclient.common import exceptions
from neutronclient.common import utils
from neutronclient.neutron import v2_0 as neutronv20
from neutronclient.neutron.v2_0.vpn import utils as vpn_utils
from neutronclient.openstack.common.gettextutils import _


def _format_peer_cidrs(ipsec_site_connection):
    try:
        return '\n'.join([utils.dumps(cidrs) for cidrs in
                          ipsec_site_connection['peer_cidrs']])
    except Exception:
        return ''


class ListIPsecSiteConnection(neutronv20.ListCommand):
    """List IPsecSiteConnections that belong to a given tenant."""

    resource = 'ipsec_site_connection'
    log = logging.getLogger(__name__ + '.ListIPsecSiteConnection')
    _formatters = {'peer_cidrs': _format_peer_cidrs}
    list_columns = [
        'id', 'name', 'peer_address', 'peer_cidrs', 'route_mode',
        'auth_mode', 'status']
    pagination_support = True
    sorting_support = True


class ShowIPsecSiteConnection(neutronv20.ShowCommand):
    """Show information of a given IPsecSiteConnection."""

    resource = 'ipsec_site_connection'
    log = logging.getLogger(__name__ + '.ShowIPsecSiteConnection')


class CreateIPsecSiteConnection(neutronv20.CreateCommand):
    """Create an IPsecSiteConnection."""
    resource = 'ipsec_site_connection'
    log = logging.getLogger(__name__ + '.CreateIPsecSiteConnection')

    def add_known_arguments(self, parser):
        parser.add_argument(
            '--admin-state-down',
            default=True, action='store_false',
            help=_('Set admin state up to false'))
        parser.add_argument(
            '--name',
            help=_('Set friendly name for the connection'))
        parser.add_argument(
            '--description',
            help=_('Set a description for the connection'))
        parser.add_argument(
            '--mtu',
            default='1500',
            help=_('MTU size for the connection, default:1500'))
        parser.add_argument(
            '--initiator',
            default='bi-directional', choices=['bi-directional',
                                               'response-only'],
            help=_('Initiator state in lowercase, default:bi-directional'))
        parser.add_argument(
            '--dpd',
            metavar="action=ACTION,interval=INTERVAL,timeout=TIMEOUT",
            type=utils.str2dict,
            help=vpn_utils.dpd_help("IPsec Connection"))
        parser.add_argument(
            '--vpnservice-id', metavar='VPNSERVICE',
            required=True,
            help=_('VPNService instance id associated with this connection'))
        parser.add_argument(
            '--ikepolicy-id', metavar='IKEPOLICY',
            required=True,
            help=_('IKEPolicy id associated with this connection'))
        parser.add_argument(
            '--ipsecpolicy-id', metavar='IPSECPOLICY',
            required=True,
            help=_('IPsecPolicy id associated with this connection'))
        parser.add_argument(
            '--peer-address',
            required=True,
            help=_('Peer gateway public IPv4/IPv6 address or FQDN.'))
        parser.add_argument(
            '--peer-id',
            required=True,
            help=_('Peer router identity for authentication. Can be '
                   'IPv4/IPv6 address, e-mail address, key id, or FQDN.'))
        parser.add_argument(
            '--peer-cidr',
            action='append', dest='peer_cidrs',
            required=True,
            help=_('Remote subnet(s) in CIDR format'))
        parser.add_argument(
            '--psk',
            required=True,
            help=_('Pre-Shared Key string'))

    def args2body(self, parsed_args):
        _vpnservice_id = neutronv20.find_resourceid_by_name_or_id(
            self.get_client(), 'vpnservice',
            parsed_args.vpnservice_id)
        _ikepolicy_id = neutronv20.find_resourceid_by_name_or_id(
            self.get_client(), 'ikepolicy',
            parsed_args.ikepolicy_id)
        _ipsecpolicy_id = neutronv20.find_resourceid_by_name_or_id(
            self.get_client(), 'ipsecpolicy',
            parsed_args.ipsecpolicy_id)
        if int(parsed_args.mtu) < 68:
            message = _("Invalid MTU value: MTU must be "
                        "greater than or equal to 68")
            raise exceptions.CommandError(message)
        body = {'ipsec_site_connection': {
            'vpnservice_id': _vpnservice_id,
            'ikepolicy_id': _ikepolicy_id,
            'ipsecpolicy_id': _ipsecpolicy_id,
            'peer_address': parsed_args.peer_address,
            'peer_id': parsed_args.peer_id,
            'mtu': parsed_args.mtu,
            'initiator': parsed_args.initiator,
            'psk': parsed_args.psk,
            'admin_state_up': parsed_args.admin_state_down,
        }, }
        if parsed_args.name:
            body['ipsec_site_connection'].update(
                {'name': parsed_args.name}
            )
        if parsed_args.description:
            body['ipsec_site_connection'].update(
                {'description': parsed_args.description}
            )
        if parsed_args.tenant_id:
            body['ipsec_site_connection'].update(
                {'tenant_id': parsed_args.tenant_id}
            )
        if parsed_args.dpd:
            vpn_utils.validate_dpd_dict(parsed_args.dpd)
            body['ipsec_site_connection'].update({'dpd': parsed_args.dpd})
        if parsed_args.peer_cidrs:
            body['ipsec_site_connection'][
                'peer_cidrs'] = parsed_args.peer_cidrs

        return body


class UpdateIPsecSiteConnection(neutronv20.UpdateCommand):
    """Update a given IPsecSiteConnection."""

    resource = 'ipsec_site_connection'
    log = logging.getLogger(__name__ + '.UpdateIPsecSiteConnection')

    def add_known_arguments(self, parser):

        parser.add_argument(
            '--dpd',
            metavar="action=ACTION,interval=INTERVAL,timeout=TIMEOUT",
            type=utils.str2dict,
            help=vpn_utils.dpd_help("IPsec Connection"))

    def args2body(self, parsed_args):
        body = {'ipsec_site_connection': {
        }, }

        if parsed_args.dpd:
            vpn_utils.validate_dpd_dict(parsed_args.dpd)
            body['ipsec_site_connection'].update({'dpd': parsed_args.dpd})
        return body


class DeleteIPsecSiteConnection(neutronv20.DeleteCommand):
    """Delete a given IPsecSiteConnection."""

    resource = 'ipsec_site_connection'
    log = logging.getLogger(__name__ + '.DeleteIPsecSiteConnection')

########NEW FILE########
__FILENAME__ = utils
#    (c) Copyright 2013 Hewlett-Packard Development Company, L.P.
#    All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.
#
# @author: Swaminathan Vasudevan, Hewlett-Packard.
#


"""VPN Utilities and helper functions."""


from neutronclient.common import exceptions
from neutronclient.openstack.common.gettextutils import _

dpd_supported_actions = ['hold', 'clear', 'restart',
                         'restart-by-peer', 'disabled']
dpd_supported_keys = ['action', 'interval', 'timeout']

lifetime_keys = ['units', 'value']
lifetime_units = ['seconds']


def validate_dpd_dict(dpd_dict):
    for key, value in dpd_dict.items():
        if key not in dpd_supported_keys:
            message = _(
                "DPD Dictionary KeyError: "
                "Reason-Invalid DPD key : "
                "'%(key)s' not in %(supported_key)s ") % {
                    'key': key, 'supported_key': dpd_supported_keys}
            raise exceptions.CommandError(message)
        if key == 'action' and value not in dpd_supported_actions:
            message = _(
                "DPD Dictionary ValueError: "
                "Reason-Invalid DPD action : "
                "'%(key_value)s' not in %(supported_action)s ") % {
                    'key_value': value,
                    'supported_action': dpd_supported_actions}
            raise exceptions.CommandError(message)
        if key in ('interval', 'timeout'):
            try:
                if int(value) <= 0:
                    raise ValueError()
            except ValueError:
                message = _(
                    "DPD Dictionary ValueError: "
                    "Reason-Invalid positive integer value: "
                    "'%(key)s' = %(value)s ") % {
                        'key': key, 'value': value}
                raise exceptions.CommandError(message)
            else:
                dpd_dict[key] = int(value)
    return


def validate_lifetime_dict(lifetime_dict):

    for key, value in lifetime_dict.items():
        if key not in lifetime_keys:
            message = _(
                "Lifetime Dictionary KeyError: "
                "Reason-Invalid unit key : "
                "'%(key)s' not in %(supported_key)s ") % {
                    'key': key, 'supported_key': lifetime_keys}
            raise exceptions.CommandError(message)
        if key == 'units' and value not in lifetime_units:
            message = _(
                "Lifetime Dictionary ValueError: "
                "Reason-Invalid units : "
                "'%(key_value)s' not in %(supported_units)s ") % {
                    'key_value': key, 'supported_units': lifetime_units}
            raise exceptions.CommandError(message)
        if key == 'value':
            try:
                if int(value) < 60:
                    raise ValueError()
            except ValueError:
                message = _(
                    "Lifetime Dictionary ValueError: "
                    "Reason-Invalid value should be at least 60:"
                    "'%(key_value)s' = %(value)s ") % {
                        'key_value': key, 'value': value}
                raise exceptions.CommandError(message)
            else:
                lifetime_dict['value'] = int(value)
    return


def lifetime_help(policy):
    lifetime = _("%s Lifetime Attributes."
                 "'units'-seconds,default:seconds. "
                 "'value'-non negative integer, default:3600.") % policy
    return lifetime


def dpd_help(policy):
    dpd = _(" %s Dead Peer Detection Attributes. "
            " 'action'-hold,clear,disabled,restart,restart-by-peer."
            " 'interval' and 'timeout' are non negative integers. "
            " 'interval' should be less than 'timeout' value. "
            " 'action', default:hold 'interval', default:30, "
            " 'timeout', default:120.") % policy.capitalize()
    return dpd

########NEW FILE########
__FILENAME__ = vpnservice
#    (c) Copyright 2013 Hewlett-Packard Development Company, L.P.
#    All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.
#
# @author: Swaminathan Vasudevan, Hewlett-Packard.
#

import logging

from neutronclient.neutron import v2_0 as neutronv20
from neutronclient.openstack.common.gettextutils import _


class ListVPNService(neutronv20.ListCommand):
    """List VPNService configurations that belong to a given tenant."""

    resource = 'vpnservice'
    log = logging.getLogger(__name__ + '.ListVPNService')
    list_columns = [
        'id', 'name', 'router_id', 'status'
    ]
    _formatters = {}
    pagination_support = True
    sorting_support = True


class ShowVPNService(neutronv20.ShowCommand):
    """Show information of a given VPNService."""

    resource = 'vpnservice'
    log = logging.getLogger(__name__ + '.ShowVPNService')


class CreateVPNService(neutronv20.CreateCommand):
    """Create a VPNService."""
    resource = 'vpnservice'
    log = logging.getLogger(__name__ + '.CreateVPNService')

    def add_known_arguments(self, parser):
        parser.add_argument(
            '--admin-state-down',
            dest='admin_state', action='store_false',
            help=_('Set admin state up to false'))
        parser.add_argument(
            '--name',
            help=_('Set a name for the vpnservice'))
        parser.add_argument(
            '--description',
            help=_('Set a description for the vpnservice'))
        parser.add_argument(
            'router', metavar='ROUTER',
            help=_('Router unique identifier for the vpnservice'))
        parser.add_argument(
            'subnet', metavar='SUBNET',
            help=_('Subnet unique identifier for the vpnservice deployment'))

    def args2body(self, parsed_args):
        _subnet_id = neutronv20.find_resourceid_by_name_or_id(
            self.get_client(), 'subnet',
            parsed_args.subnet)
        _router_id = neutronv20.find_resourceid_by_name_or_id(
            self.get_client(), 'router',
            parsed_args.router)

        body = {self.resource: {'subnet_id': _subnet_id,
                                'router_id': _router_id,
                                'admin_state_up': parsed_args.admin_state}, }
        neutronv20.update_dict(parsed_args, body[self.resource],
                               ['name', 'description',
                                'tenant_id'])

        return body


class UpdateVPNService(neutronv20.UpdateCommand):
    """Update a given VPNService."""

    resource = 'vpnservice'
    log = logging.getLogger(__name__ + '.UpdateVPNService')


class DeleteVPNService(neutronv20.DeleteCommand):
    """Delete a given VPNService."""

    resource = 'vpnservice'
    log = logging.getLogger(__name__ + '.DeleteVPNService')

########NEW FILE########
__FILENAME__ = gettextutils
# Copyright 2012 Red Hat, Inc.
# Copyright 2013 IBM Corp.
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

"""
gettext for openstack-common modules.

Usual usage in an openstack.common module:

    from neutronclient.openstack.common.gettextutils import _
"""

import copy
import gettext
import logging
import os
import re
import UserString

from babel import localedata
import six

_localedir = os.environ.get('neutronclient'.upper() + '_LOCALEDIR')
_t = gettext.translation('neutronclient', localedir=_localedir, fallback=True)

_AVAILABLE_LANGUAGES = {}
USE_LAZY = False


def enable_lazy():
    """Convenience function for configuring _() to use lazy gettext

    Call this at the start of execution to enable the gettextutils._
    function to use lazy gettext functionality. This is useful if
    your project is importing _ directly instead of using the
    gettextutils.install() way of importing the _ function.
    """
    global USE_LAZY
    USE_LAZY = True


def _(msg):
    if USE_LAZY:
        return Message(msg, 'neutronclient')
    else:
        return _t.ugettext(msg)


def install(domain, lazy=False):
    """Install a _() function using the given translation domain.

    Given a translation domain, install a _() function using gettext's
    install() function.

    The main difference from gettext.install() is that we allow
    overriding the default localedir (e.g. /usr/share/locale) using
    a translation-domain-specific environment variable (e.g.
    NOVA_LOCALEDIR).

    :param domain: the translation domain
    :param lazy: indicates whether or not to install the lazy _() function.
                 The lazy _() introduces a way to do deferred translation
                 of messages by installing a _ that builds Message objects,
                 instead of strings, which can then be lazily translated into
                 any available locale.
    """
    if lazy:
        # NOTE(mrodden): Lazy gettext functionality.
        #
        # The following introduces a deferred way to do translations on
        # messages in OpenStack. We override the standard _() function
        # and % (format string) operation to build Message objects that can
        # later be translated when we have more information.
        #
        # Also included below is an example LocaleHandler that translates
        # Messages to an associated locale, effectively allowing many logs,
        # each with their own locale.

        def _lazy_gettext(msg):
            """Create and return a Message object.

            Lazy gettext function for a given domain, it is a factory method
            for a project/module to get a lazy gettext function for its own
            translation domain (i.e. nova, glance, cinder, etc.)

            Message encapsulates a string so that we can translate
            it later when needed.
            """
            return Message(msg, domain)

        import __builtin__
        __builtin__.__dict__['_'] = _lazy_gettext
    else:
        localedir = '%s_LOCALEDIR' % domain.upper()
        gettext.install(domain,
                        localedir=os.environ.get(localedir),
                        unicode=True)


class Message(UserString.UserString, object):
    """Class used to encapsulate translatable messages."""
    def __init__(self, msg, domain):
        # _msg is the gettext msgid and should never change
        self._msg = msg
        self._left_extra_msg = ''
        self._right_extra_msg = ''
        self.params = None
        self.locale = None
        self.domain = domain

    @property
    def data(self):
        # NOTE(mrodden): this should always resolve to a unicode string
        # that best represents the state of the message currently

        localedir = os.environ.get(self.domain.upper() + '_LOCALEDIR')
        if self.locale:
            lang = gettext.translation(self.domain,
                                       localedir=localedir,
                                       languages=[self.locale],
                                       fallback=True)
        else:
            # use system locale for translations
            lang = gettext.translation(self.domain,
                                       localedir=localedir,
                                       fallback=True)

        full_msg = (self._left_extra_msg +
                    lang.ugettext(self._msg) +
                    self._right_extra_msg)

        if self.params is not None:
            full_msg = full_msg % self.params

        return six.text_type(full_msg)

    def _save_dictionary_parameter(self, dict_param):
        full_msg = self.data
        # look for %(blah) fields in string;
        # ignore %% and deal with the
        # case where % is first character on the line
        keys = re.findall('(?:[^%]|^)?%\((\w*)\)[a-z]', full_msg)

        # if we don't find any %(blah) blocks but have a %s
        if not keys and re.findall('(?:[^%]|^)%[a-z]', full_msg):
            # apparently the full dictionary is the parameter
            params = copy.deepcopy(dict_param)
        else:
            params = {}
            for key in keys:
                try:
                    params[key] = copy.deepcopy(dict_param[key])
                except TypeError:
                    # cast uncopyable thing to unicode string
                    params[key] = unicode(dict_param[key])

        return params

    def _save_parameters(self, other):
        # we check for None later to see if
        # we actually have parameters to inject,
        # so encapsulate if our parameter is actually None
        if other is None:
            self.params = (other, )
        elif isinstance(other, dict):
            self.params = self._save_dictionary_parameter(other)
        else:
            # fallback to casting to unicode,
            # this will handle the problematic python code-like
            # objects that cannot be deep-copied
            try:
                self.params = copy.deepcopy(other)
            except TypeError:
                self.params = unicode(other)

        return self

    # overrides to be more string-like
    def __unicode__(self):
        return self.data

    def __str__(self):
        return self.data.encode('utf-8')

    def __getstate__(self):
        to_copy = ['_msg', '_right_extra_msg', '_left_extra_msg',
                   'domain', 'params', 'locale']
        new_dict = self.__dict__.fromkeys(to_copy)
        for attr in to_copy:
            new_dict[attr] = copy.deepcopy(self.__dict__[attr])

        return new_dict

    def __setstate__(self, state):
        for (k, v) in state.items():
            setattr(self, k, v)

    # operator overloads
    def __add__(self, other):
        copied = copy.deepcopy(self)
        copied._right_extra_msg += other.__str__()
        return copied

    def __radd__(self, other):
        copied = copy.deepcopy(self)
        copied._left_extra_msg += other.__str__()
        return copied

    def __mod__(self, other):
        # do a format string to catch and raise
        # any possible KeyErrors from missing parameters
        self.data % other
        copied = copy.deepcopy(self)
        return copied._save_parameters(other)

    def __mul__(self, other):
        return self.data * other

    def __rmul__(self, other):
        return other * self.data

    def __getitem__(self, key):
        return self.data[key]

    def __getslice__(self, start, end):
        return self.data.__getslice__(start, end)

    def __getattribute__(self, name):
        # NOTE(mrodden): handle lossy operations that we can't deal with yet
        # These override the UserString implementation, since UserString
        # uses our __class__ attribute to try and build a new message
        # after running the inner data string through the operation.
        # At that point, we have lost the gettext message id and can just
        # safely resolve to a string instead.
        ops = ['capitalize', 'center', 'decode', 'encode',
               'expandtabs', 'ljust', 'lstrip', 'replace', 'rjust', 'rstrip',
               'strip', 'swapcase', 'title', 'translate', 'upper', 'zfill']
        if name in ops:
            return getattr(self.data, name)
        else:
            return UserString.UserString.__getattribute__(self, name)


def get_available_languages(domain):
    """Lists the available languages for the given translation domain.

    :param domain: the domain to get languages for
    """
    if domain in _AVAILABLE_LANGUAGES:
        return copy.copy(_AVAILABLE_LANGUAGES[domain])

    localedir = '%s_LOCALEDIR' % domain.upper()
    find = lambda x: gettext.find(domain,
                                  localedir=os.environ.get(localedir),
                                  languages=[x])

    # NOTE(mrodden): en_US should always be available (and first in case
    # order matters) since our in-line message strings are en_US
    language_list = ['en_US']
    # NOTE(luisg): Babel <1.0 used a function called list(), which was
    # renamed to locale_identifiers() in >=1.0, the requirements master list
    # requires >=0.9.6, uncapped, so defensively work with both. We can remove
    # this check when the master list updates to >=1.0, and all projects udpate
    list_identifiers = (getattr(localedata, 'list', None) or
                        getattr(localedata, 'locale_identifiers'))
    locale_identifiers = list_identifiers()
    for i in locale_identifiers:
        if find(i) is not None:
            language_list.append(i)
    _AVAILABLE_LANGUAGES[domain] = language_list
    return copy.copy(language_list)


def get_localized_message(message, user_locale):
    """Gets a localized version of the given message in the given locale."""
    if isinstance(message, Message):
        if user_locale:
            message.locale = user_locale
        return unicode(message)
    else:
        return message


class LocaleHandler(logging.Handler):
    """Handler that can have a locale associated to translate Messages.

    A quick example of how to utilize the Message class above.
    LocaleHandler takes a locale and a target logging.Handler object
    to forward LogRecord objects to after translating the internal Message.
    """

    def __init__(self, locale, target):
        """Initialize a LocaleHandler

        :param locale: locale to use for translating messages
        :param target: logging.Handler object to forward
                       LogRecord objects to after translation
        """
        logging.Handler.__init__(self)
        self.locale = locale
        self.target = target

    def emit(self, record):
        if isinstance(record.msg, Message):
            # set the locale and resolve to a string
            record.msg.locale = self.locale

        self.target.emit(record)

########NEW FILE########
__FILENAME__ = importutils
# Copyright 2011 OpenStack Foundation.
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

"""
Import related utilities and helper functions.
"""

import sys
import traceback
from neutronclient.openstack.common.gettextutils import _


def import_class(import_str):
    """Returns a class from a string including module and class."""
    mod_str, _sep, class_str = import_str.rpartition('.')
    try:
        __import__(mod_str)
        return getattr(sys.modules[mod_str], class_str)
    except (ValueError, AttributeError):
        raise ImportError(_('Class %s cannot be found (%s)') %
                          (class_str,
                           traceback.format_exception(*sys.exc_info())))


def import_object(import_str, *args, **kwargs):
    """Import a class and return an instance of it."""
    return import_class(import_str)(*args, **kwargs)


def import_object_ns(name_space, import_str, *args, **kwargs):
    """Tries to import object from default namespace.

    Imports a class and return an instance of it, first by trying
    to find the class in a default namespace, then failing back to
    a full path if not found in the default namespace.
    """
    import_value = "%s.%s" % (name_space, import_str)
    try:
        return import_class(import_value)(*args, **kwargs)
    except ImportError:
        return import_class(import_str)(*args, **kwargs)


def import_module(import_str):
    """Import a module."""
    __import__(import_str)
    return sys.modules[import_str]


def try_import(import_str, default=None):
    """Try to import a module and if it fails return default."""
    try:
        return import_module(import_str)
    except ImportError:
        return default

########NEW FILE########
__FILENAME__ = jsonutils
# Copyright 2010 United States Government as represented by the
# Administrator of the National Aeronautics and Space Administration.
# Copyright 2011 Justin Santa Barbara
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

'''
JSON related utilities.

This module provides a few things:

    1) A handy function for getting an object down to something that can be
    JSON serialized.  See to_primitive().

    2) Wrappers around loads() and dumps().  The dumps() wrapper will
    automatically use to_primitive() for you if needed.

    3) This sets up anyjson to use the loads() and dumps() wrappers if anyjson
    is available.
'''


import datetime
import functools
import inspect
import itertools
import json
import types
import xmlrpclib

import six

from neutronclient.openstack.common import importutils
from neutronclient.openstack.common import timeutils

netaddr = importutils.try_import("netaddr")

_nasty_type_tests = [inspect.ismodule, inspect.isclass, inspect.ismethod,
                     inspect.isfunction, inspect.isgeneratorfunction,
                     inspect.isgenerator, inspect.istraceback, inspect.isframe,
                     inspect.iscode, inspect.isbuiltin, inspect.isroutine,
                     inspect.isabstract]

_simple_types = (types.NoneType, int, basestring, bool, float, long)


def to_primitive(value, convert_instances=False, convert_datetime=True,
                 level=0, max_depth=3):
    """Convert a complex object into primitives.

    Handy for JSON serialization. We can optionally handle instances,
    but since this is a recursive function, we could have cyclical
    data structures.

    To handle cyclical data structures we could track the actual objects
    visited in a set, but not all objects are hashable. Instead we just
    track the depth of the object inspections and don't go too deep.

    Therefore, convert_instances=True is lossy ... be aware.

    """
    # handle obvious types first - order of basic types determined by running
    # full tests on nova project, resulting in the following counts:
    # 572754 <type 'NoneType'>
    # 460353 <type 'int'>
    # 379632 <type 'unicode'>
    # 274610 <type 'str'>
    # 199918 <type 'dict'>
    # 114200 <type 'datetime.datetime'>
    #  51817 <type 'bool'>
    #  26164 <type 'list'>
    #   6491 <type 'float'>
    #    283 <type 'tuple'>
    #     19 <type 'long'>
    if isinstance(value, _simple_types):
        return value

    if isinstance(value, datetime.datetime):
        if convert_datetime:
            return timeutils.strtime(value)
        else:
            return value

    # value of itertools.count doesn't get caught by nasty_type_tests
    # and results in infinite loop when list(value) is called.
    if type(value) == itertools.count:
        return six.text_type(value)

    # FIXME(vish): Workaround for LP bug 852095. Without this workaround,
    #              tests that raise an exception in a mocked method that
    #              has a @wrap_exception with a notifier will fail. If
    #              we up the dependency to 0.5.4 (when it is released) we
    #              can remove this workaround.
    if getattr(value, '__module__', None) == 'mox':
        return 'mock'

    if level > max_depth:
        return '?'

    # The try block may not be necessary after the class check above,
    # but just in case ...
    try:
        recursive = functools.partial(to_primitive,
                                      convert_instances=convert_instances,
                                      convert_datetime=convert_datetime,
                                      level=level,
                                      max_depth=max_depth)
        if isinstance(value, dict):
            return dict((k, recursive(v)) for k, v in value.iteritems())
        elif isinstance(value, (list, tuple)):
            return [recursive(lv) for lv in value]

        # It's not clear why xmlrpclib created their own DateTime type, but
        # for our purposes, make it a datetime type which is explicitly
        # handled
        if isinstance(value, xmlrpclib.DateTime):
            value = datetime.datetime(*tuple(value.timetuple())[:6])

        if convert_datetime and isinstance(value, datetime.datetime):
            return timeutils.strtime(value)
        elif hasattr(value, 'iteritems'):
            return recursive(dict(value.iteritems()), level=level + 1)
        elif hasattr(value, '__iter__'):
            return recursive(list(value))
        elif convert_instances and hasattr(value, '__dict__'):
            # Likely an instance of something. Watch for cycles.
            # Ignore class member vars.
            return recursive(value.__dict__, level=level + 1)
        elif netaddr and isinstance(value, netaddr.IPAddress):
            return six.text_type(value)
        else:
            if any(test(value) for test in _nasty_type_tests):
                return six.text_type(value)
            return value
    except TypeError:
        # Class objects are tricky since they may define something like
        # __iter__ defined but it isn't callable as list().
        return six.text_type(value)


def dumps(value, default=to_primitive, **kwargs):
    return json.dumps(value, default=default, **kwargs)


def loads(s):
    return json.loads(s)


def load(s):
    return json.load(s)


try:
    import anyjson
except ImportError:
    pass
else:
    anyjson._modules.append((__name__, 'dumps', TypeError,
                                       'loads', ValueError, 'load'))
    anyjson.force_implementation(__name__)

########NEW FILE########
__FILENAME__ = strutils
# Copyright 2011 OpenStack Foundation.
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

"""
System-level utilities and helper functions.
"""

import re
import sys
import unicodedata

import six

from neutronclient.openstack.common.gettextutils import _  # noqa


# Used for looking up extensions of text
# to their 'multiplied' byte amount
BYTE_MULTIPLIERS = {
    '': 1,
    't': 1024 ** 4,
    'g': 1024 ** 3,
    'm': 1024 ** 2,
    'k': 1024,
}
BYTE_REGEX = re.compile(r'(^-?\d+)(\D*)')

TRUE_STRINGS = ('1', 't', 'true', 'on', 'y', 'yes')
FALSE_STRINGS = ('0', 'f', 'false', 'off', 'n', 'no')

SLUGIFY_STRIP_RE = re.compile(r"[^\w\s-]")
SLUGIFY_HYPHENATE_RE = re.compile(r"[-\s]+")


def int_from_bool_as_string(subject):
    """Interpret a string as a boolean and return either 1 or 0.

    Any string value in:

        ('True', 'true', 'On', 'on', '1')

    is interpreted as a boolean True.

    Useful for JSON-decoded stuff and config file parsing
    """
    return bool_from_string(subject) and 1 or 0


def bool_from_string(subject, strict=False):
    """Interpret a string as a boolean.

    A case-insensitive match is performed such that strings matching 't',
    'true', 'on', 'y', 'yes', or '1' are considered True and, when
    `strict=False`, anything else is considered False.

    Useful for JSON-decoded stuff and config file parsing.

    If `strict=True`, unrecognized values, including None, will raise a
    ValueError which is useful when parsing values passed in from an API call.
    Strings yielding False are 'f', 'false', 'off', 'n', 'no', or '0'.
    """
    if not isinstance(subject, six.string_types):
        subject = str(subject)

    lowered = subject.strip().lower()

    if lowered in TRUE_STRINGS:
        return True
    elif lowered in FALSE_STRINGS:
        return False
    elif strict:
        acceptable = ', '.join(
            "'%s'" % s for s in sorted(TRUE_STRINGS + FALSE_STRINGS))
        msg = _("Unrecognized value '%(val)s', acceptable values are:"
                " %(acceptable)s") % {'val': subject,
                                      'acceptable': acceptable}
        raise ValueError(msg)
    else:
        return False


def safe_decode(text, incoming=None, errors='strict'):
    """Decodes incoming str using `incoming` if they're not already unicode.

    :param incoming: Text's current encoding
    :param errors: Errors handling policy. See here for valid
        values http://docs.python.org/2/library/codecs.html
    :returns: text or a unicode `incoming` encoded
                representation of it.
    :raises TypeError: If text is not an isntance of str
    """
    if not isinstance(text, six.string_types):
        raise TypeError("%s can't be decoded" % type(text))

    if isinstance(text, six.text_type):
        return text

    if not incoming:
        incoming = (sys.stdin.encoding or
                    sys.getdefaultencoding())

    try:
        return text.decode(incoming, errors)
    except UnicodeDecodeError:
        # Note(flaper87) If we get here, it means that
        # sys.stdin.encoding / sys.getdefaultencoding
        # didn't return a suitable encoding to decode
        # text. This happens mostly when global LANG
        # var is not set correctly and there's no
        # default encoding. In this case, most likely
        # python will use ASCII or ANSI encoders as
        # default encodings but they won't be capable
        # of decoding non-ASCII characters.
        #
        # Also, UTF-8 is being used since it's an ASCII
        # extension.
        return text.decode('utf-8', errors)


def safe_encode(text, incoming=None,
                encoding='utf-8', errors='strict'):
    """Encodes incoming str/unicode using `encoding`.

    If incoming is not specified, text is expected to be encoded with
    current python's default encoding. (`sys.getdefaultencoding`)

    :param incoming: Text's current encoding
    :param encoding: Expected encoding for text (Default UTF-8)
    :param errors: Errors handling policy. See here for valid
        values http://docs.python.org/2/library/codecs.html
    :returns: text or a bytestring `encoding` encoded
                representation of it.
    :raises TypeError: If text is not an isntance of str
    """
    if not isinstance(text, six.string_types):
        raise TypeError(_("%s can't be encoded") % type(text).capitalize())

    if not incoming:
        incoming = (sys.stdin.encoding or
                    sys.getdefaultencoding())

    if isinstance(text, six.text_type):
        return text.encode(encoding, errors)
    elif text and encoding != incoming:
        # Decode text before encoding it with `encoding`
        text = safe_decode(text, incoming, errors)
        return text.encode(encoding, errors)

    return text


def to_bytes(text, default=0):
    """Converts a string into an integer of bytes.

    Looks at the last characters of the text to determine
    what conversion is needed to turn the input text into a byte number.
    Supports "B, K(B), M(B), G(B), and T(B)". (case insensitive)

    :param text: String input for bytes size conversion.
    :param default: Default return value when text is blank.

    """
    match = BYTE_REGEX.search(text)
    if match:
        magnitude = int(match.group(1))
        mult_key_org = match.group(2)
        if not mult_key_org:
            return magnitude
    elif text:
        msg = _('Invalid string format: %s') % text
        raise TypeError(msg)
    else:
        return default
    mult_key = mult_key_org.lower().replace('b', '', 1)
    multiplier = BYTE_MULTIPLIERS.get(mult_key)
    if multiplier is None:
        msg = _('Unknown byte multiplier: %s') % mult_key_org
        raise TypeError(msg)
    return magnitude * multiplier


def to_slug(value, incoming=None, errors="strict"):
    """Normalize string.

    Convert to lowercase, remove non-word characters, and convert spaces
    to hyphens.

    Inspired by Django's `slugify` filter.

    :param value: Text to slugify
    :param incoming: Text's current encoding
    :param errors: Errors handling policy. See here for valid
        values http://docs.python.org/2/library/codecs.html
    :returns: slugified unicode representation of `value`
    :raises TypeError: If text is not an instance of str
    """
    value = safe_decode(value, incoming, errors)
    # NOTE(aababilov): no need to use safe_(encode|decode) here:
    # encodings are always "ascii", error handling is always "ignore"
    # and types are always known (first: unicode; second: str)
    value = unicodedata.normalize("NFKD", value).encode(
        "ascii", "ignore").decode("ascii")
    value = SLUGIFY_STRIP_RE.sub("", value).strip().lower()
    return SLUGIFY_HYPHENATE_RE.sub("-", value)

########NEW FILE########
__FILENAME__ = timeutils
# Copyright 2011 OpenStack Foundation.
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

"""
Time related utilities and helper functions.
"""

import calendar
import datetime

import iso8601
import six


# ISO 8601 extended time format with microseconds
_ISO8601_TIME_FORMAT_SUBSECOND = '%Y-%m-%dT%H:%M:%S.%f'
_ISO8601_TIME_FORMAT = '%Y-%m-%dT%H:%M:%S'
PERFECT_TIME_FORMAT = _ISO8601_TIME_FORMAT_SUBSECOND


def isotime(at=None, subsecond=False):
    """Stringify time in ISO 8601 format."""
    if not at:
        at = utcnow()
    st = at.strftime(_ISO8601_TIME_FORMAT
                     if not subsecond
                     else _ISO8601_TIME_FORMAT_SUBSECOND)
    tz = at.tzinfo.tzname(None) if at.tzinfo else 'UTC'
    st += ('Z' if tz == 'UTC' else tz)
    return st


def parse_isotime(timestr):
    """Parse time from ISO 8601 format."""
    try:
        return iso8601.parse_date(timestr)
    except iso8601.ParseError as e:
        raise ValueError(unicode(e))
    except TypeError as e:
        raise ValueError(unicode(e))


def strtime(at=None, fmt=PERFECT_TIME_FORMAT):
    """Returns formatted utcnow."""
    if not at:
        at = utcnow()
    return at.strftime(fmt)


def parse_strtime(timestr, fmt=PERFECT_TIME_FORMAT):
    """Turn a formatted time back into a datetime."""
    return datetime.datetime.strptime(timestr, fmt)


def normalize_time(timestamp):
    """Normalize time in arbitrary timezone to UTC naive object."""
    offset = timestamp.utcoffset()
    if offset is None:
        return timestamp
    return timestamp.replace(tzinfo=None) - offset


def is_older_than(before, seconds):
    """Return True if before is older than seconds."""
    if isinstance(before, six.string_types):
        before = parse_strtime(before).replace(tzinfo=None)
    return utcnow() - before > datetime.timedelta(seconds=seconds)


def is_newer_than(after, seconds):
    """Return True if after is newer than seconds."""
    if isinstance(after, six.string_types):
        after = parse_strtime(after).replace(tzinfo=None)
    return after - utcnow() > datetime.timedelta(seconds=seconds)


def utcnow_ts():
    """Timestamp version of our utcnow function."""
    return calendar.timegm(utcnow().timetuple())


def utcnow():
    """Overridable version of utils.utcnow."""
    if utcnow.override_time:
        try:
            return utcnow.override_time.pop(0)
        except AttributeError:
            return utcnow.override_time
    return datetime.datetime.utcnow()


def iso8601_from_timestamp(timestamp):
    """Returns a iso8601 formated date from timestamp."""
    return isotime(datetime.datetime.utcfromtimestamp(timestamp))


utcnow.override_time = None


def set_time_override(override_time=datetime.datetime.utcnow()):
    """Overrides utils.utcnow.

    Make it return a constant time or a list thereof, one at a time.
    """
    utcnow.override_time = override_time


def advance_time_delta(timedelta):
    """Advance overridden time using a datetime.timedelta."""
    assert(not utcnow.override_time is None)
    try:
        for dt in utcnow.override_time:
            dt += timedelta
    except TypeError:
        utcnow.override_time += timedelta


def advance_time_seconds(seconds):
    """Advance overridden time by seconds."""
    advance_time_delta(datetime.timedelta(0, seconds))


def clear_time_override():
    """Remove the overridden time."""
    utcnow.override_time = None


def marshall_now(now=None):
    """Make an rpc-safe datetime with microseconds.

    Note: tzinfo is stripped, but not required for relative times.
    """
    if not now:
        now = utcnow()
    return dict(day=now.day, month=now.month, year=now.year, hour=now.hour,
                minute=now.minute, second=now.second,
                microsecond=now.microsecond)


def unmarshall_time(tyme):
    """Unmarshall a datetime dict."""
    return datetime.datetime(day=tyme['day'],
                             month=tyme['month'],
                             year=tyme['year'],
                             hour=tyme['hour'],
                             minute=tyme['minute'],
                             second=tyme['second'],
                             microsecond=tyme['microsecond'])


def delta_seconds(before, after):
    """Return the difference between two timing objects.

    Compute the difference in seconds between two date, time, or
    datetime objects (as a float, to microsecond resolution).
    """
    delta = after - before
    try:
        return delta.total_seconds()
    except AttributeError:
        return ((delta.days * 24 * 3600) + delta.seconds +
                float(delta.microseconds) / (10 ** 6))


def is_soon(dt, window):
    """Determines if time is going to happen in the next window seconds.

    :params dt: the time
    :params window: minimum seconds to remain to consider the time not soon

    :return: True if expiration is within the given duration
    """
    soon = (utcnow() + datetime.timedelta(seconds=window))
    return normalize_time(dt) <= soon

########NEW FILE########
__FILENAME__ = shell
# Copyright 2012 OpenStack Foundation.
# All Rights Reserved
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.
#

"""
Command-line interface to the Neutron APIs
"""

from __future__ import print_function

import argparse
import logging
import os
import sys

from cliff import app
from cliff import commandmanager

from neutronclient.common import clientmanager
from neutronclient.common import exceptions as exc
from neutronclient.common import utils
from neutronclient.neutron.v2_0 import agent
from neutronclient.neutron.v2_0 import agentscheduler
from neutronclient.neutron.v2_0 import credential
from neutronclient.neutron.v2_0 import extension
from neutronclient.neutron.v2_0 import floatingip
from neutronclient.neutron.v2_0.fw import firewall
from neutronclient.neutron.v2_0.fw import firewallpolicy
from neutronclient.neutron.v2_0.fw import firewallrule
from neutronclient.neutron.v2_0.lb import healthmonitor as lb_healthmonitor
from neutronclient.neutron.v2_0.lb import member as lb_member
from neutronclient.neutron.v2_0.lb import pool as lb_pool
from neutronclient.neutron.v2_0.lb import vip as lb_vip
from neutronclient.neutron.v2_0 import metering
from neutronclient.neutron.v2_0.nec import packetfilter
from neutronclient.neutron.v2_0 import netpartition
from neutronclient.neutron.v2_0 import network
from neutronclient.neutron.v2_0 import networkprofile
from neutronclient.neutron.v2_0.nsx import networkgateway
from neutronclient.neutron.v2_0.nsx import qos_queue
from neutronclient.neutron.v2_0 import policyprofile
from neutronclient.neutron.v2_0 import port
from neutronclient.neutron.v2_0 import quota
from neutronclient.neutron.v2_0 import router
from neutronclient.neutron.v2_0 import securitygroup
from neutronclient.neutron.v2_0 import servicetype
from neutronclient.neutron.v2_0 import subnet
from neutronclient.neutron.v2_0.vpn import ikepolicy
from neutronclient.neutron.v2_0.vpn import ipsec_site_connection
from neutronclient.neutron.v2_0.vpn import ipsecpolicy
from neutronclient.neutron.v2_0.vpn import vpnservice
from neutronclient.openstack.common.gettextutils import _
from neutronclient.openstack.common import strutils
from neutronclient.version import __version__


VERSION = '2.0'
NEUTRON_API_VERSION = '2.0'


def run_command(cmd, cmd_parser, sub_argv):
    _argv = sub_argv
    index = -1
    values_specs = []
    if '--' in sub_argv:
        index = sub_argv.index('--')
        _argv = sub_argv[:index]
        values_specs = sub_argv[index:]
    known_args, _values_specs = cmd_parser.parse_known_args(_argv)
    cmd.values_specs = (index == -1 and _values_specs or values_specs)
    return cmd.run(known_args)


def env(*_vars, **kwargs):
    """Search for the first defined of possibly many env vars.

    Returns the first environment variable defined in vars, or
    returns the default defined in kwargs.

    """
    for v in _vars:
        value = os.environ.get(v, None)
        if value:
            return value
    return kwargs.get('default', '')


COMMAND_V2 = {
    'net-list': network.ListNetwork,
    'net-external-list': network.ListExternalNetwork,
    'net-show': network.ShowNetwork,
    'net-create': network.CreateNetwork,
    'net-delete': network.DeleteNetwork,
    'net-update': network.UpdateNetwork,
    'subnet-list': subnet.ListSubnet,
    'subnet-show': subnet.ShowSubnet,
    'subnet-create': subnet.CreateSubnet,
    'subnet-delete': subnet.DeleteSubnet,
    'subnet-update': subnet.UpdateSubnet,
    'port-list': port.ListPort,
    'port-show': port.ShowPort,
    'port-create': port.CreatePort,
    'port-delete': port.DeletePort,
    'port-update': port.UpdatePort,
    'quota-list': quota.ListQuota,
    'quota-show': quota.ShowQuota,
    'quota-delete': quota.DeleteQuota,
    'quota-update': quota.UpdateQuota,
    'ext-list': extension.ListExt,
    'ext-show': extension.ShowExt,
    'router-list': router.ListRouter,
    'router-port-list': port.ListRouterPort,
    'router-show': router.ShowRouter,
    'router-create': router.CreateRouter,
    'router-delete': router.DeleteRouter,
    'router-update': router.UpdateRouter,
    'router-interface-add': router.AddInterfaceRouter,
    'router-interface-delete': router.RemoveInterfaceRouter,
    'router-gateway-set': router.SetGatewayRouter,
    'router-gateway-clear': router.RemoveGatewayRouter,
    'floatingip-list': floatingip.ListFloatingIP,
    'floatingip-show': floatingip.ShowFloatingIP,
    'floatingip-create': floatingip.CreateFloatingIP,
    'floatingip-delete': floatingip.DeleteFloatingIP,
    'floatingip-associate': floatingip.AssociateFloatingIP,
    'floatingip-disassociate': floatingip.DisassociateFloatingIP,
    'security-group-list': securitygroup.ListSecurityGroup,
    'security-group-show': securitygroup.ShowSecurityGroup,
    'security-group-create': securitygroup.CreateSecurityGroup,
    'security-group-delete': securitygroup.DeleteSecurityGroup,
    'security-group-update': securitygroup.UpdateSecurityGroup,
    'security-group-rule-list': securitygroup.ListSecurityGroupRule,
    'security-group-rule-show': securitygroup.ShowSecurityGroupRule,
    'security-group-rule-create': securitygroup.CreateSecurityGroupRule,
    'security-group-rule-delete': securitygroup.DeleteSecurityGroupRule,
    'lb-vip-list': lb_vip.ListVip,
    'lb-vip-show': lb_vip.ShowVip,
    'lb-vip-create': lb_vip.CreateVip,
    'lb-vip-update': lb_vip.UpdateVip,
    'lb-vip-delete': lb_vip.DeleteVip,
    'lb-pool-list': lb_pool.ListPool,
    'lb-pool-show': lb_pool.ShowPool,
    'lb-pool-create': lb_pool.CreatePool,
    'lb-pool-update': lb_pool.UpdatePool,
    'lb-pool-delete': lb_pool.DeletePool,
    'lb-pool-stats': lb_pool.RetrievePoolStats,
    'lb-member-list': lb_member.ListMember,
    'lb-member-show': lb_member.ShowMember,
    'lb-member-create': lb_member.CreateMember,
    'lb-member-update': lb_member.UpdateMember,
    'lb-member-delete': lb_member.DeleteMember,
    'lb-healthmonitor-list': lb_healthmonitor.ListHealthMonitor,
    'lb-healthmonitor-show': lb_healthmonitor.ShowHealthMonitor,
    'lb-healthmonitor-create': lb_healthmonitor.CreateHealthMonitor,
    'lb-healthmonitor-update': lb_healthmonitor.UpdateHealthMonitor,
    'lb-healthmonitor-delete': lb_healthmonitor.DeleteHealthMonitor,
    'lb-healthmonitor-associate': lb_healthmonitor.AssociateHealthMonitor,
    'lb-healthmonitor-disassociate': (
        lb_healthmonitor.DisassociateHealthMonitor
    ),
    'queue-create': qos_queue.CreateQoSQueue,
    'queue-delete': qos_queue.DeleteQoSQueue,
    'queue-show': qos_queue.ShowQoSQueue,
    'queue-list': qos_queue.ListQoSQueue,
    'agent-list': agent.ListAgent,
    'agent-show': agent.ShowAgent,
    'agent-delete': agent.DeleteAgent,
    'agent-update': agent.UpdateAgent,
    'net-gateway-create': networkgateway.CreateNetworkGateway,
    'net-gateway-update': networkgateway.UpdateNetworkGateway,
    'net-gateway-delete': networkgateway.DeleteNetworkGateway,
    'net-gateway-show': networkgateway.ShowNetworkGateway,
    'net-gateway-list': networkgateway.ListNetworkGateway,
    'net-gateway-connect': networkgateway.ConnectNetworkGateway,
    'net-gateway-disconnect': networkgateway.DisconnectNetworkGateway,
    'gateway-device-create': networkgateway.CreateGatewayDevice,
    'gateway-device-update': networkgateway.UpdateGatewayDevice,
    'gateway-device-delete': networkgateway.DeleteGatewayDevice,
    'gateway-device-show': networkgateway.ShowGatewayDevice,
    'gateway-device-list': networkgateway.ListGatewayDevice,
    'dhcp-agent-network-add': agentscheduler.AddNetworkToDhcpAgent,
    'dhcp-agent-network-remove': agentscheduler.RemoveNetworkFromDhcpAgent,
    'net-list-on-dhcp-agent': agentscheduler.ListNetworksOnDhcpAgent,
    'dhcp-agent-list-hosting-net': agentscheduler.ListDhcpAgentsHostingNetwork,
    'l3-agent-router-add': agentscheduler.AddRouterToL3Agent,
    'l3-agent-router-remove': agentscheduler.RemoveRouterFromL3Agent,
    'router-list-on-l3-agent': agentscheduler.ListRoutersOnL3Agent,
    'l3-agent-list-hosting-router': agentscheduler.ListL3AgentsHostingRouter,
    'lb-pool-list-on-agent': agentscheduler.ListPoolsOnLbaasAgent,
    'lb-agent-hosting-pool': agentscheduler.GetLbaasAgentHostingPool,
    'service-provider-list': servicetype.ListServiceProvider,
    'firewall-rule-list': firewallrule.ListFirewallRule,
    'firewall-rule-show': firewallrule.ShowFirewallRule,
    'firewall-rule-create': firewallrule.CreateFirewallRule,
    'firewall-rule-update': firewallrule.UpdateFirewallRule,
    'firewall-rule-delete': firewallrule.DeleteFirewallRule,
    'firewall-policy-list': firewallpolicy.ListFirewallPolicy,
    'firewall-policy-show': firewallpolicy.ShowFirewallPolicy,
    'firewall-policy-create': firewallpolicy.CreateFirewallPolicy,
    'firewall-policy-update': firewallpolicy.UpdateFirewallPolicy,
    'firewall-policy-delete': firewallpolicy.DeleteFirewallPolicy,
    'firewall-policy-insert-rule': firewallpolicy.FirewallPolicyInsertRule,
    'firewall-policy-remove-rule': firewallpolicy.FirewallPolicyRemoveRule,
    'firewall-list': firewall.ListFirewall,
    'firewall-show': firewall.ShowFirewall,
    'firewall-create': firewall.CreateFirewall,
    'firewall-update': firewall.UpdateFirewall,
    'firewall-delete': firewall.DeleteFirewall,
    'cisco-credential-list': credential.ListCredential,
    'cisco-credential-show': credential.ShowCredential,
    'cisco-credential-create': credential.CreateCredential,
    'cisco-credential-delete': credential.DeleteCredential,
    'cisco-network-profile-list': networkprofile.ListNetworkProfile,
    'cisco-network-profile-show': networkprofile.ShowNetworkProfile,
    'cisco-network-profile-create': networkprofile.CreateNetworkProfile,
    'cisco-network-profile-delete': networkprofile.DeleteNetworkProfile,
    'cisco-network-profile-update': networkprofile.UpdateNetworkProfile,
    'cisco-policy-profile-list': policyprofile.ListPolicyProfile,
    'cisco-policy-profile-show': policyprofile.ShowPolicyProfile,
    'cisco-policy-profile-update': policyprofile.UpdatePolicyProfile,
    'ipsec-site-connection-list': (
        ipsec_site_connection.ListIPsecSiteConnection
    ),
    'ipsec-site-connection-show': (
        ipsec_site_connection.ShowIPsecSiteConnection
    ),
    'ipsec-site-connection-create': (
        ipsec_site_connection.CreateIPsecSiteConnection
    ),
    'ipsec-site-connection-update': (
        ipsec_site_connection.UpdateIPsecSiteConnection
    ),
    'ipsec-site-connection-delete': (
        ipsec_site_connection.DeleteIPsecSiteConnection
    ),
    'vpn-service-list': vpnservice.ListVPNService,
    'vpn-service-show': vpnservice.ShowVPNService,
    'vpn-service-create': vpnservice.CreateVPNService,
    'vpn-service-update': vpnservice.UpdateVPNService,
    'vpn-service-delete': vpnservice.DeleteVPNService,
    'vpn-ipsecpolicy-list': ipsecpolicy.ListIPsecPolicy,
    'vpn-ipsecpolicy-show': ipsecpolicy.ShowIPsecPolicy,
    'vpn-ipsecpolicy-create': ipsecpolicy.CreateIPsecPolicy,
    'vpn-ipsecpolicy-update': ipsecpolicy.UpdateIPsecPolicy,
    'vpn-ipsecpolicy-delete': ipsecpolicy.DeleteIPsecPolicy,
    'vpn-ikepolicy-list': ikepolicy.ListIKEPolicy,
    'vpn-ikepolicy-show': ikepolicy.ShowIKEPolicy,
    'vpn-ikepolicy-create': ikepolicy.CreateIKEPolicy,
    'vpn-ikepolicy-update': ikepolicy.UpdateIKEPolicy,
    'vpn-ikepolicy-delete': ikepolicy.DeleteIKEPolicy,
    'meter-label-create': metering.CreateMeteringLabel,
    'meter-label-list': metering.ListMeteringLabel,
    'meter-label-show': metering.ShowMeteringLabel,
    'meter-label-delete': metering.DeleteMeteringLabel,
    'meter-label-rule-create': metering.CreateMeteringLabelRule,
    'meter-label-rule-list': metering.ListMeteringLabelRule,
    'meter-label-rule-show': metering.ShowMeteringLabelRule,
    'meter-label-rule-delete': metering.DeleteMeteringLabelRule,
    'nuage-netpartition-list': netpartition.ListNetPartition,
    'nuage-netpartition-show': netpartition.ShowNetPartition,
    'nuage-netpartition-create': netpartition.CreateNetPartition,
    'nuage-netpartition-delete': netpartition.DeleteNetPartition,
    'nec-packet-filter-list': packetfilter.ListPacketFilter,
    'nec-packet-filter-show': packetfilter.ShowPacketFilter,
    'nec-packet-filter-create': packetfilter.CreatePacketFilter,
    'nec-packet-filter-update': packetfilter.UpdatePacketFilter,
    'nec-packet-filter-delete': packetfilter.DeletePacketFilter,
}

COMMANDS = {'2.0': COMMAND_V2}


class HelpAction(argparse.Action):
    """Provide a custom action so the -h and --help options
    to the main app will print a list of the commands.

    The commands are determined by checking the CommandManager
    instance, passed in as the "default" value for the action.
    """
    def __call__(self, parser, namespace, values, option_string=None):
        outputs = []
        max_len = 0
        app = self.default
        parser.print_help(app.stdout)
        app.stdout.write(_('\nCommands for API v%s:\n') % app.api_version)
        command_manager = app.command_manager
        for name, ep in sorted(command_manager):
            factory = ep.load()
            cmd = factory(self, None)
            one_liner = cmd.get_description().split('\n')[0]
            outputs.append((name, one_liner))
            max_len = max(len(name), max_len)
        for (name, one_liner) in outputs:
            app.stdout.write('  %s  %s\n' % (name.ljust(max_len), one_liner))
        sys.exit(0)


class NeutronShell(app.App):

    # verbose logging levels
    WARNING_LEVEL = 0
    INFO_LEVEL = 1
    DEBUG_LEVEL = 2
    CONSOLE_MESSAGE_FORMAT = '%(message)s'
    DEBUG_MESSAGE_FORMAT = '%(levelname)s: %(name)s %(message)s'
    log = logging.getLogger(__name__)

    def __init__(self, apiversion):
        super(NeutronShell, self).__init__(
            description=__doc__.strip(),
            version=VERSION,
            command_manager=commandmanager.CommandManager('neutron.cli'), )
        self.commands = COMMANDS
        for k, v in self.commands[apiversion].items():
            self.command_manager.add_command(k, v)

        # This is instantiated in initialize_app() only when using
        # password flow auth
        self.auth_client = None
        self.api_version = apiversion

    def build_option_parser(self, description, version):
        """Return an argparse option parser for this application.

        Subclasses may override this method to extend
        the parser with more global options.

        :param description: full description of the application
        :paramtype description: str
        :param version: version number for the application
        :paramtype version: str
        """
        parser = argparse.ArgumentParser(
            description=description,
            add_help=False, )
        parser.add_argument(
            '--version',
            action='version',
            version=__version__, )
        parser.add_argument(
            '-v', '--verbose', '--debug',
            action='count',
            dest='verbose_level',
            default=self.DEFAULT_VERBOSE_LEVEL,
            help=_('Increase verbosity of output and show tracebacks on'
                   ' errors. Can be repeated.'))
        parser.add_argument(
            '-q', '--quiet',
            action='store_const',
            dest='verbose_level',
            const=0,
            help=_('Suppress output except warnings and errors'))
        parser.add_argument(
            '-h', '--help',
            action=HelpAction,
            nargs=0,
            default=self,  # tricky
            help=_("Show this help message and exit"))
        # Global arguments
        parser.add_argument(
            '--os-auth-strategy', metavar='<auth-strategy>',
            default=env('OS_AUTH_STRATEGY', default='keystone'),
            help=_('Authentication strategy (Env: OS_AUTH_STRATEGY'
            ', default keystone). For now, any other value will'
            ' disable the authentication'))
        parser.add_argument(
            '--os_auth_strategy',
            help=argparse.SUPPRESS)

        parser.add_argument(
            '--os-auth-url', metavar='<auth-url>',
            default=env('OS_AUTH_URL'),
            help=_('Authentication URL (Env: OS_AUTH_URL)'))
        parser.add_argument(
            '--os_auth_url',
            help=argparse.SUPPRESS)

        parser.add_argument(
            '--os-tenant-name', metavar='<auth-tenant-name>',
            default=env('OS_TENANT_NAME'),
            help=_('Authentication tenant name (Env: OS_TENANT_NAME)'))
        parser.add_argument(
            '--os_tenant_name',
            help=argparse.SUPPRESS)

        parser.add_argument(
            '--os-tenant-id', metavar='<auth-tenant-id>',
            default=env('OS_TENANT_ID'),
            help=_('Authentication tenant ID (Env: OS_TENANT_ID)'))

        parser.add_argument(
            '--os-username', metavar='<auth-username>',
            default=utils.env('OS_USERNAME'),
            help=_('Authentication username (Env: OS_USERNAME)'))
        parser.add_argument(
            '--os_username',
            help=argparse.SUPPRESS)

        parser.add_argument(
            '--os-user-id', metavar='<auth-user-id>',
            default=env('OS_USER_ID'),
            help=_('Authentication user ID (Env: OS_USER_ID)'))

        parser.add_argument(
            '--os-password', metavar='<auth-password>',
            default=utils.env('OS_PASSWORD'),
            help=_('Authentication password (Env: OS_PASSWORD)'))
        parser.add_argument(
            '--os_password',
            help=argparse.SUPPRESS)

        parser.add_argument(
            '--os-region-name', metavar='<auth-region-name>',
            default=env('OS_REGION_NAME'),
            help=_('Authentication region name (Env: OS_REGION_NAME)'))
        parser.add_argument(
            '--os_region_name',
            help=argparse.SUPPRESS)

        parser.add_argument(
            '--os-token', metavar='<token>',
            default=env('OS_TOKEN'),
            help=_('Defaults to env[OS_TOKEN]'))
        parser.add_argument(
            '--os_token',
            help=argparse.SUPPRESS)

        parser.add_argument(
            '--service-type', metavar='<service-type>',
            default=env('OS_NETWORK_SERVICE_TYPE', default='network'),
            help=_('Defaults to env[OS_NETWORK_SERVICE_TYPE] or network.'))

        parser.add_argument(
            '--endpoint-type', metavar='<endpoint-type>',
            default=env('OS_ENDPOINT_TYPE', default='publicURL'),
            help=_('Defaults to env[OS_ENDPOINT_TYPE] or publicURL.'))

        parser.add_argument(
            '--os-url', metavar='<url>',
            default=env('OS_URL'),
            help=_('Defaults to env[OS_URL]'))
        parser.add_argument(
            '--os_url',
            help=argparse.SUPPRESS)

        parser.add_argument(
            '--os-cacert',
            metavar='<ca-certificate>',
            default=env('OS_CACERT', default=None),
            help=_("Specify a CA bundle file to use in "
                   "verifying a TLS (https) server certificate. "
                   "Defaults to env[OS_CACERT]"))

        parser.add_argument(
            '--insecure',
            action='store_true',
            default=env('NEUTRONCLIENT_INSECURE', default=False),
            help=_("Explicitly allow neutronclient to perform \"insecure\" "
                   "SSL (https) requests. The server's certificate will "
                   "not be verified against any certificate authorities. "
                   "This option should be used with caution."))

        return parser

    def _bash_completion(self):
        """Prints all of the commands and options for bash-completion."""
        commands = set()
        options = set()
        for option, _action in self.parser._option_string_actions.items():
            options.add(option)
        for command_name, command in self.command_manager:
            commands.add(command_name)
            cmd_factory = command.load()
            cmd = cmd_factory(self, None)
            cmd_parser = cmd.get_parser('')
            for option, _action in cmd_parser._option_string_actions.items():
                options.add(option)
        print(' '.join(commands | options))

    def run(self, argv):
        """Equivalent to the main program for the application.

        :param argv: input arguments and options
        :paramtype argv: list of str
        """
        try:
            index = 0
            command_pos = -1
            help_pos = -1
            help_command_pos = -1
            for arg in argv:
                if arg == 'bash-completion':
                    self._bash_completion()
                    return 0
                if arg in self.commands[self.api_version]:
                    if command_pos == -1:
                        command_pos = index
                elif arg in ('-h', '--help'):
                    if help_pos == -1:
                        help_pos = index
                elif arg == 'help':
                    if help_command_pos == -1:
                        help_command_pos = index
                index = index + 1
            if command_pos > -1 and help_pos > command_pos:
                argv = ['help', argv[command_pos]]
            if help_command_pos > -1 and command_pos == -1:
                argv[help_command_pos] = '--help'
            self.options, remainder = self.parser.parse_known_args(argv)
            self.configure_logging()
            self.interactive_mode = not remainder
            self.initialize_app(remainder)
        except Exception as err:
            if self.options.verbose_level == self.DEBUG_LEVEL:
                self.log.exception(unicode(err))
                raise
            else:
                self.log.error(unicode(err))
            return 1
        result = 1
        if self.interactive_mode:
            _argv = [sys.argv[0]]
            sys.argv = _argv
            result = self.interact()
        else:
            result = self.run_subcommand(remainder)
        return result

    def run_subcommand(self, argv):
        subcommand = self.command_manager.find_command(argv)
        cmd_factory, cmd_name, sub_argv = subcommand
        cmd = cmd_factory(self, self.options)
        err = None
        result = 1
        try:
            self.prepare_to_run_command(cmd)
            full_name = (cmd_name
                         if self.interactive_mode
                         else ' '.join([self.NAME, cmd_name])
                         )
            cmd_parser = cmd.get_parser(full_name)
            return run_command(cmd, cmd_parser, sub_argv)
        except Exception as err:
            if self.options.verbose_level == self.DEBUG_LEVEL:
                self.log.exception(unicode(err))
            else:
                self.log.error(unicode(err))
            try:
                self.clean_up(cmd, result, err)
            except Exception as err2:
                if self.options.verbose_level == self.DEBUG_LEVEL:
                    self.log.exception(unicode(err2))
                else:
                    self.log.error(_('Could not clean up: %s'), unicode(err2))
            if self.options.verbose_level == self.DEBUG_LEVEL:
                raise
        else:
            try:
                self.clean_up(cmd, result, None)
            except Exception as err3:
                if self.options.verbose_level == self.DEBUG_LEVEL:
                    self.log.exception(unicode(err3))
                else:
                    self.log.error(_('Could not clean up: %s'), unicode(err3))
        return result

    def authenticate_user(self):
        """Make sure the user has provided all of the authentication
        info we need.
        """
        if self.options.os_auth_strategy == 'keystone':
            if self.options.os_token or self.options.os_url:
                # Token flow auth takes priority
                if not self.options.os_token:
                    raise exc.CommandError(
                        _("You must provide a token via"
                          " either --os-token or env[OS_TOKEN]"))

                if not self.options.os_url:
                    raise exc.CommandError(
                        _("You must provide a service URL via"
                          " either --os-url or env[OS_URL]"))

            else:
                # Validate password flow auth
                if (not self.options.os_username
                    and not self.options.os_user_id):
                    raise exc.CommandError(
                        _("You must provide a username or user ID via"
                          "  --os-username, env[OS_USERNAME] or"
                          "  --os-user_id, env[OS_USER_ID]"))

                if not self.options.os_password:
                    raise exc.CommandError(
                        _("You must provide a password via"
                          " either --os-password or env[OS_PASSWORD]"))

                if (not self.options.os_tenant_name
                    and not self.options.os_tenant_id):
                    raise exc.CommandError(
                        _("You must provide a tenant_name or tenant_id via"
                          "  --os-tenant-name, env[OS_TENANT_NAME]"
                          "  --os-tenant-id, or via env[OS_TENANT_ID]"))

                if not self.options.os_auth_url:
                    raise exc.CommandError(
                        _("You must provide an auth url via"
                          " either --os-auth-url or via env[OS_AUTH_URL]"))
        else:   # not keystone
            if not self.options.os_url:
                raise exc.CommandError(
                    _("You must provide a service URL via"
                      " either --os-url or env[OS_URL]"))

        self.client_manager = clientmanager.ClientManager(
            token=self.options.os_token,
            url=self.options.os_url,
            auth_url=self.options.os_auth_url,
            tenant_name=self.options.os_tenant_name,
            tenant_id=self.options.os_tenant_id,
            username=self.options.os_username,
            user_id=self.options.os_user_id,
            password=self.options.os_password,
            region_name=self.options.os_region_name,
            api_version=self.api_version,
            auth_strategy=self.options.os_auth_strategy,
            service_type=self.options.service_type,
            endpoint_type=self.options.endpoint_type,
            insecure=self.options.insecure,
            ca_cert=self.options.os_cacert,
            log_credentials=True)
        return

    def initialize_app(self, argv):
        """Global app init bits:

        * set up API versions
        * validate authentication info
        """

        super(NeutronShell, self).initialize_app(argv)

        self.api_version = {'network': self.api_version}

        # If the user is not asking for help, make sure they
        # have given us auth.
        cmd_name = None
        if argv:
            cmd_info = self.command_manager.find_command(argv)
            cmd_factory, cmd_name, sub_argv = cmd_info
        if self.interactive_mode or cmd_name != 'help':
            self.authenticate_user()

    def clean_up(self, cmd, result, err):
        self.log.debug('clean_up %s', cmd.__class__.__name__)
        if err:
            self.log.debug(_('Got an error: %s'), unicode(err))

    def configure_logging(self):
        """Create logging handlers for any log output."""
        root_logger = logging.getLogger('')

        # Set up logging to a file
        root_logger.setLevel(logging.DEBUG)

        # Send higher-level messages to the console via stderr
        console = logging.StreamHandler(self.stderr)
        console_level = {self.WARNING_LEVEL: logging.WARNING,
                         self.INFO_LEVEL: logging.INFO,
                         self.DEBUG_LEVEL: logging.DEBUG,
                         }.get(self.options.verbose_level, logging.DEBUG)
        console.setLevel(console_level)
        if logging.DEBUG == console_level:
            formatter = logging.Formatter(self.DEBUG_MESSAGE_FORMAT)
        else:
            formatter = logging.Formatter(self.CONSOLE_MESSAGE_FORMAT)
        console.setFormatter(formatter)
        root_logger.addHandler(console)
        return


def main(argv=sys.argv[1:]):
    try:
        return NeutronShell(NEUTRON_API_VERSION).run(map(strutils.safe_decode,
                                                         argv))
    except exc.NeutronClientException:
        return 1
    except Exception as e:
        print(unicode(e))
        return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

########NEW FILE########
__FILENAME__ = test_cli20_firewall
# Copyright 2013 Big Switch Networks Inc.
# All Rights Reserved
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.
#
# @author: KC Wang, Big Switch Networks Inc.
#

import sys

from neutronclient.neutron.v2_0.fw import firewall
from neutronclient.tests.unit import test_cli20


class CLITestV20FirewallJSON(test_cli20.CLITestV20Base):

    def test_create_firewall_with_mandatory_params(self):
        """firewall-create with mandatory (none) params."""
        resource = 'firewall'
        cmd = firewall.CreateFirewall(test_cli20.MyApp(sys.stdout), None)
        name = ''
        tenant_id = 'my-tenant'
        my_id = 'my-id'
        policy_id = 'my-policy-id'
        args = ['--tenant-id', tenant_id, policy_id, ]
        position_names = ['firewall_policy_id', ]
        position_values = [policy_id, ]
        self._test_create_resource(resource, cmd, name, my_id, args,
                                   position_names, position_values,
                                   admin_state_up=True, tenant_id=tenant_id)

    def test_create_firewall_with_all_params(self):
        """firewall-create with all params set."""
        resource = 'firewall'
        cmd = firewall.CreateFirewall(test_cli20.MyApp(sys.stdout), None)
        name = 'my-name'
        description = 'my-desc'
        policy_id = 'my-policy-id'
        tenant_id = 'my-tenant'
        my_id = 'my-id'
        args = ['--description', description,
                '--shared',
                '--admin-state-down',
                '--tenant-id', tenant_id,
                policy_id]
        position_names = ['firewall_policy_id', ]
        position_values = [policy_id, ]
        self._test_create_resource(resource, cmd, name, my_id, args,
                                   position_names, position_values,
                                   description=description,
                                   shared=True, admin_state_up=False,
                                   tenant_id=tenant_id)

    def test_list_firewalls(self):
        """firewall-list."""
        resources = "firewalls"
        cmd = firewall.ListFirewall(test_cli20.MyApp(sys.stdout), None)
        self._test_list_resources(resources, cmd, True)

    def test_list_firewalls_pagination(self):
        """firewall-list with pagination."""
        resources = "firewalls"
        cmd = firewall.ListFirewall(test_cli20.MyApp(sys.stdout), None)
        self._test_list_resources_with_pagination(resources, cmd)

    def test_list_firewalls_sort(self):
        """sorted list: firewall-list --sort-key name --sort-key id
        --sort-key asc --sort-key desc
        """
        resources = "firewalls"
        cmd = firewall.ListFirewall(test_cli20.MyApp(sys.stdout), None)
        self._test_list_resources(resources, cmd,
                                  sort_key=["name", "id"],
                                  sort_dir=["asc", "desc"])

    def test_list_firewalls_limit(self):
        """size (1000) limited list: firewall-list -P."""
        resources = "firewalls"
        cmd = firewall.ListFirewall(test_cli20.MyApp(sys.stdout), None)
        self._test_list_resources(resources, cmd, page_size=1000)

    def test_show_firewall_id(self):
        """firewall-show test_id."""
        resource = 'firewall'
        cmd = firewall.ShowFirewall(test_cli20.MyApp(sys.stdout), None)
        args = ['--fields', 'id', self.test_id]
        self._test_show_resource(resource, cmd, self.test_id, args, ['id'])

    def test_show_firewall_id_name(self):
        """firewall-show."""
        resource = 'firewall'
        cmd = firewall.ShowFirewall(test_cli20.MyApp(sys.stdout), None)
        args = ['--fields', 'id', '--fields', 'name', self.test_id]
        self._test_show_resource(resource, cmd, self.test_id,
                                 args, ['id', 'name'])

    def test_update_firewall(self):
        """firewall-update myid --name newname --tags a b."""
        resource = 'firewall'
        cmd = firewall.UpdateFirewall(test_cli20.MyApp(sys.stdout), None)
        self._test_update_resource(resource, cmd, 'myid',
                                   ['myid', '--name', 'newname'],
                                   {'name': 'newname', })

    def test_delete_firewall(self):
        """firewall-delete my-id."""
        resource = 'firewall'
        cmd = firewall.DeleteFirewall(test_cli20.MyApp(sys.stdout), None)
        my_id = 'my-id'
        args = [my_id]
        self._test_delete_resource(resource, cmd, my_id, args)


class CLITestV20FirewallXML(CLITestV20FirewallJSON):
    format = 'xml'

########NEW FILE########
__FILENAME__ = test_cli20_firewallpolicy
# Copyright 2013 Big Switch Networks Inc.
# All Rights Reserved
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.
#
# @author: KC Wang, Big Switch Networks Inc.
#

import sys

import mox

from neutronclient.neutron.v2_0.fw import firewallpolicy
from neutronclient import shell
from neutronclient.tests.unit import test_cli20


class CLITestV20FirewallPolicyJSON(test_cli20.CLITestV20Base):
    def setUp(self):
        super(CLITestV20FirewallPolicyJSON, self).setUp()

    def test_create_firewall_policy_with_mandatory_params(self):
        """firewall-policy-create with mandatory (none) params only."""
        resource = 'firewall_policy'
        cmd = firewallpolicy.CreateFirewallPolicy(test_cli20.MyApp(sys.stdout),
                                                  None)
        tenant_id = 'my-tenant'
        name = 'my-name'
        my_id = 'myid'
        args = ['--tenant-id', tenant_id,
                '--admin-state_up',
                name, ]
        position_names = ['name', ]
        position_values = [name, ]
        self._test_create_resource(resource, cmd, name, my_id, args,
                                   position_names, position_values,
                                   admin_state_up=True, tenant_id=tenant_id)

    def test_create_firewall_policy_with_all_params(self):
        """firewall-policy-create with all params set."""
        resource = 'firewall_policy'
        cmd = firewallpolicy.CreateFirewallPolicy(test_cli20.MyApp(sys.stdout),
                                                  None)
        name = 'my-name'
        description = 'my-desc'
        firewall_rules_arg = 'rule_id1 rule_id2'
        firewall_rules_res = ['rule_id1', 'rule_id2']
        tenant_id = 'my-tenant'
        my_id = 'myid'
        args = ['--description', description,
                '--shared',
                '--firewall-rules', firewall_rules_arg,
                '--audited',
                '--tenant-id', tenant_id,
                '--admin-state_up',
                name]
        position_names = ['name', ]
        position_values = [name, ]
        self._test_create_resource(resource, cmd, name, my_id, args,
                                   position_names, position_values,
                                   description=description, shared=True,
                                   firewall_rules=firewall_rules_res,
                                   audited=True, admin_state_up=True,
                                   tenant_id=tenant_id)

    def test_list_firewall_policies(self):
        """firewall-policy-list."""
        resources = "firewall_policies"
        cmd = firewallpolicy.ListFirewallPolicy(test_cli20.MyApp(sys.stdout),
                                                None)
        self._test_list_resources(resources, cmd, True)

    def test_list_firewall_policies_pagination(self):
        """firewall-policy-list."""
        resources = "firewall_policies"
        cmd = firewallpolicy.ListFirewallPolicy(test_cli20.MyApp(sys.stdout),
                                                None)
        self._test_list_resources_with_pagination(resources, cmd)

    def test_list_firewall_policies_sort(self):
        """sorted list: firewall-policy-list --sort-key name --sort-key id
        --sort-key asc --sort-key desc
        """
        resources = "firewall_policies"
        cmd = firewallpolicy.ListFirewallPolicy(test_cli20.MyApp(sys.stdout),
                                                None)
        self._test_list_resources(resources, cmd,
                                  sort_key=["name", "id"],
                                  sort_dir=["asc", "desc"])

    def test_list_firewall_policies_limit(self):
        """size (1000) limited list: firewall-policy-list -P."""
        resources = "firewall_policies"
        cmd = firewallpolicy.ListFirewallPolicy(test_cli20.MyApp(sys.stdout),
                                                None)
        self._test_list_resources(resources, cmd, page_size=1000)

    def test_show_firewall_policy_id(self):
        """firewall-policy-show test_id."""
        resource = 'firewall_policy'
        cmd = firewallpolicy.ShowFirewallPolicy(test_cli20.MyApp(sys.stdout),
                                                None)
        args = ['--fields', 'id', self.test_id]
        self._test_show_resource(resource, cmd, self.test_id, args, ['id'])

    def test_show_firewall_policy_id_name(self):
        """firewall-policy-show."""
        resource = 'firewall_policy'
        cmd = firewallpolicy.ShowFirewallPolicy(test_cli20.MyApp(sys.stdout),
                                                None)
        args = ['--fields', 'id', '--fields', 'name', self.test_id]
        self._test_show_resource(resource, cmd, self.test_id,
                                 args, ['id', 'name'])

    def test_update_firewall_policy(self):
        """firewall-policy-update myid --name newname."""
        resource = 'firewall_policy'
        cmd = firewallpolicy.UpdateFirewallPolicy(test_cli20.MyApp(sys.stdout),
                                                  None)
        self._test_update_resource(resource, cmd, 'myid',
                                   ['myid', '--name', 'newname'],
                                   {'name': 'newname', })

    def test_delete_firewall_policy(self):
        """firewall-policy-delete my-id."""
        resource = 'firewall_policy'
        cmd = firewallpolicy.DeleteFirewallPolicy(test_cli20.MyApp(sys.stdout),
                                                  None)
        my_id = 'myid1'
        args = [my_id]
        self._test_delete_resource(resource, cmd, my_id, args)

    def test_insert_firewall_rule(self):
        """firewall-policy-insert-rule myid newruleid
        --insert-before ruleAid
        --insert-after ruleBid
        """
        resource = 'firewall_policy'
        cmd = firewallpolicy.FirewallPolicyInsertRule(
            test_cli20.MyApp(sys.stdout),
            None)
        myid = 'myid'
        args = ['myid', 'newrule',
                '--insert-before', 'rule2',
                '--insert-after', 'rule1']
        extrafields = {'firewall_rule_id': 'newrule',
                       'insert_before': 'rule2',
                       'insert_after': 'rule1'}

        self.mox.StubOutWithMock(cmd, "get_client")
        self.mox.StubOutWithMock(self.client.httpclient, "request")
        cmd.get_client().MultipleTimes().AndReturn(self.client)
        body = extrafields
        path = getattr(self.client, resource + "_insert_path")
        self.client.httpclient.request(
            test_cli20.MyUrlComparator(
                test_cli20.end_url(path % myid, format=self.format),
                self.client),
            'PUT', body=test_cli20.MyComparator(body, self.client),
            headers=mox.ContainsKeyValue(
                'X-Auth-Token',
                test_cli20.TOKEN)).AndReturn((test_cli20.MyResp(204), None))
        args.extend(['--request-format', self.format])
        self.mox.ReplayAll()
        cmd_parser = cmd.get_parser(resource + "_insert_rule")
        shell.run_command(cmd, cmd_parser, args)
        self.mox.VerifyAll()
        self.mox.UnsetStubs()

    def test_remove_firewall_rule(self):
        """firewall-policy-remove-rule myid ruleid
        """
        resource = 'firewall_policy'
        cmd = firewallpolicy.FirewallPolicyRemoveRule(
            test_cli20.MyApp(sys.stdout),
            None)
        myid = 'myid'
        args = ['myid', 'removerule']
        extrafields = {'firewall_rule_id': 'removerule', }

        self.mox.StubOutWithMock(cmd, "get_client")
        self.mox.StubOutWithMock(self.client.httpclient, "request")
        cmd.get_client().MultipleTimes().AndReturn(self.client)
        body = extrafields
        path = getattr(self.client, resource + "_remove_path")
        self.client.httpclient.request(
            test_cli20.MyUrlComparator(
                test_cli20.end_url(path % myid, format=self.format),
                self.client),
            'PUT', body=test_cli20.MyComparator(body, self.client),
            headers=mox.ContainsKeyValue(
                'X-Auth-Token',
                test_cli20.TOKEN)).AndReturn((test_cli20.MyResp(204), None))
        args.extend(['--request-format', self.format])
        self.mox.ReplayAll()
        cmd_parser = cmd.get_parser(resource + "_remove_rule")
        shell.run_command(cmd, cmd_parser, args)
        self.mox.VerifyAll()
        self.mox.UnsetStubs()


class CLITestV20FirewallPolicyXML(CLITestV20FirewallPolicyJSON):
    format = 'xml'

########NEW FILE########
__FILENAME__ = test_cli20_firewallrule
# Copyright 2013 Big Switch Networks Inc.
# All Rights Reserved
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.
#
# @author: KC Wang, Big Switch Networks Inc.
#

import sys

from neutronclient.neutron.v2_0.fw import firewallrule
from neutronclient.tests.unit import test_cli20


class CLITestV20FirewallRuleJSON(test_cli20.CLITestV20Base):

    def _test_create_firewall_rule_with_mandatory_params(self, enabled):
        """firewall-rule-create with mandatory (none) params only."""
        resource = 'firewall_rule'
        cmd = firewallrule.CreateFirewallRule(test_cli20.MyApp(sys.stdout),
                                              None)
        tenant_id = 'my-tenant'
        name = ''
        my_id = 'myid'
        protocol = 'tcp'
        action = 'allow'
        enabled_flag = '--enabled' if enabled else '--disabled'
        args = ['--tenant-id', tenant_id,
                '--admin-state-up',
                '--protocol', protocol,
                '--action', action,
                enabled_flag]
        position_names = []
        position_values = []
        self._test_create_resource(resource, cmd, name, my_id, args,
                                   position_names, position_values,
                                   protocol=protocol, action=action,
                                   enabled=enabled, tenant_id=tenant_id)

    def test_create_enabled_firewall_rule_with_mandatory_params(self):
        self._test_create_firewall_rule_with_mandatory_params(enabled=True)

    def test_create_disabled_firewall_rule_with_mandatory_params(self):
        self._test_create_firewall_rule_with_mandatory_params(enabled=False)

    def _setup_create_firewall_rule_with_all_params(self, protocol='tcp'):
        """firewall-rule-create with all params set."""
        resource = 'firewall_rule'
        cmd = firewallrule.CreateFirewallRule(test_cli20.MyApp(sys.stdout),
                                              None)
        name = 'my-name'
        description = 'my-desc'
        source_ip = '192.168.1.0/24'
        destination_ip = '192.168.2.0/24'
        source_port = '0:65535'
        destination_port = '0:65535'
        action = 'allow'
        tenant_id = 'my-tenant'
        my_id = 'myid'
        args = ['--description', description,
                '--shared',
                '--protocol', protocol,
                '--source-ip-address', source_ip,
                '--destination-ip-address', destination_ip,
                '--source-port', source_port,
                '--destination-port', destination_port,
                '--action', action,
                '--enabled',
                '--admin-state-up',
                '--tenant-id', tenant_id]
        position_names = []
        position_values = []
        if protocol == 'any':
            protocol = None
        self._test_create_resource(resource, cmd, name, my_id, args,
                                   position_names, position_values,
                                   description=description, shared=True,
                                   protocol=protocol,
                                   source_ip_address=source_ip,
                                   destination_ip_address=destination_ip,
                                   source_port=source_port,
                                   destination_port=destination_port,
                                   action=action, enabled=True,
                                   tenant_id=tenant_id)

    def test_create_firewall_rule_with_all_params(self):
        self._setup_create_firewall_rule_with_all_params()

    def test_create_firewall_rule_with_proto_any(self):
        self._setup_create_firewall_rule_with_all_params(protocol='any')

    def test_list_firewall_rules(self):
        """firewall-rule-list."""
        resources = "firewall_rules"
        cmd = firewallrule.ListFirewallRule(test_cli20.MyApp(sys.stdout),
                                            None)
        self._test_list_resources(resources, cmd, True)

    def test_list_firewall_rules_pagination(self):
        """firewall-rule-list."""
        resources = "firewall_rules"
        cmd = firewallrule.ListFirewallRule(test_cli20.MyApp(sys.stdout),
                                            None)
        self._test_list_resources_with_pagination(resources, cmd)

    def test_list_firewall_rules_sort(self):
        """firewall-rule-list --sort-key name --sort-key id --sort-key asc
        --sort-key desc
        """
        resources = "firewall_rules"
        cmd = firewallrule.ListFirewallRule(test_cli20.MyApp(sys.stdout),
                                            None)
        self._test_list_resources(resources, cmd,
                                  sort_key=["name", "id"],
                                  sort_dir=["asc", "desc"])

    def test_list_firewall_rules_limit(self):
        """firewall-rule-list -P."""
        resources = "firewall_rules"
        cmd = firewallrule.ListFirewallRule(test_cli20.MyApp(sys.stdout),
                                            None)
        self._test_list_resources(resources, cmd, page_size=1000)

    def test_show_firewall_rule_id(self):
        """firewall-rule-show test_id."""
        resource = 'firewall_rule'
        cmd = firewallrule.ShowFirewallRule(test_cli20.MyApp(sys.stdout),
                                            None)
        args = ['--fields', 'id', self.test_id]
        self._test_show_resource(resource, cmd, self.test_id, args, ['id'])

    def test_show_firewall_rule_id_name(self):
        """firewall-rule-show."""
        resource = 'firewall_rule'
        cmd = firewallrule.ShowFirewallRule(test_cli20.MyApp(sys.stdout),
                                            None)
        args = ['--fields', 'id', '--fields', 'name', self.test_id]
        self._test_show_resource(resource, cmd, self.test_id,
                                 args, ['id', 'name'])

    def test_update_firewall_rule(self):
        """firewall-rule-update myid --name newname."""
        resource = 'firewall_rule'
        cmd = firewallrule.UpdateFirewallRule(test_cli20.MyApp(sys.stdout),
                                              None)
        self._test_update_resource(resource, cmd, 'myid',
                                   ['myid', '--name', 'newname'],
                                   {'name': 'newname', })

    def test_update_firewall_rule_protocol(self):
        """firewall-rule-update myid --protocol any."""
        resource = 'firewall_rule'
        cmd = firewallrule.UpdateFirewallRule(test_cli20.MyApp(sys.stdout),
                                              None)
        self._test_update_resource(resource, cmd, 'myid',
                                   ['myid', '--protocol', 'any'],
                                   {'protocol': None, })

    def test_delete_firewall_rule(self):
        """firewall-rule-delete my-id."""
        resource = 'firewall_rule'
        cmd = firewallrule.DeleteFirewallRule(test_cli20.MyApp(sys.stdout),
                                              None)
        my_id = 'myid1'
        args = [my_id]
        self._test_delete_resource(resource, cmd, my_id, args)


class CLITestV20FirewallRuleXML(CLITestV20FirewallRuleJSON):
    format = 'xml'

########NEW FILE########
__FILENAME__ = test_cli20_healthmonitor
# Copyright 2013 Mirantis Inc.
# All Rights Reserved
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.
#
# @author: Ilya Shakhat, Mirantis Inc.
#

import sys

import mox

from neutronclient.neutron.v2_0.lb import healthmonitor
from neutronclient.tests.unit import test_cli20


class CLITestV20LbHealthmonitorJSON(test_cli20.CLITestV20Base):
    def test_create_healthmonitor_with_mandatory_params(self):
        """lb-healthmonitor-create with mandatory params only."""
        resource = 'health_monitor'
        cmd = healthmonitor.CreateHealthMonitor(test_cli20.MyApp(sys.stdout),
                                                None)
        admin_state_up = False
        delay = '60'
        max_retries = '2'
        timeout = '10'
        type = 'TCP'
        tenant_id = 'my-tenant'
        my_id = 'my-id'
        args = ['--admin-state-down',
                '--delay', delay,
                '--max-retries', max_retries,
                '--timeout', timeout,
                '--type', type,
                '--tenant-id', tenant_id]
        position_names = ['admin_state_up', 'delay', 'max_retries', 'timeout',
                          'type', 'tenant_id']
        position_values = [admin_state_up, delay, max_retries, timeout, type,
                           tenant_id]
        self._test_create_resource(resource, cmd, '', my_id, args,
                                   position_names, position_values)

    def test_create_healthmonitor_with_all_params(self):
        """lb-healthmonitor-create with all params set."""
        resource = 'health_monitor'
        cmd = healthmonitor.CreateHealthMonitor(test_cli20.MyApp(sys.stdout),
                                                None)
        admin_state_up = False
        delay = '60'
        expected_codes = '200-202,204'
        http_method = 'HEAD'
        max_retries = '2'
        timeout = '10'
        type = 'TCP'
        tenant_id = 'my-tenant'
        url_path = '/health'
        my_id = 'my-id'
        args = ['--admin-state-down',
                '--delay', delay,
                '--expected-codes', expected_codes,
                '--http-method', http_method,
                '--max-retries', max_retries,
                '--timeout', timeout,
                '--type', type,
                '--tenant-id', tenant_id,
                '--url-path', url_path]
        position_names = ['admin_state_up', 'delay',
                          'expected_codes', 'http_method',
                          'max_retries', 'timeout',
                          'type', 'tenant_id', 'url_path']
        position_values = [admin_state_up, delay,
                           expected_codes, http_method,
                           max_retries, timeout,
                           type, tenant_id, url_path]
        self._test_create_resource(resource, cmd, '', my_id, args,
                                   position_names, position_values)

    def test_list_healthmonitors(self):
        """lb-healthmonitor-list."""
        resources = "health_monitors"
        cmd = healthmonitor.ListHealthMonitor(test_cli20.MyApp(sys.stdout),
                                              None)
        self._test_list_resources(resources, cmd, True)

    def test_list_healthmonitors_pagination(self):
        """lb-healthmonitor-list."""
        resources = "health_monitors"
        cmd = healthmonitor.ListHealthMonitor(test_cli20.MyApp(sys.stdout),
                                              None)
        self._test_list_resources_with_pagination(resources, cmd)

    def test_list_healthmonitors_sort(self):
        """lb-healthmonitor-list --sort-key name --sort-key id --sort-key asc
        --sort-key desc
        """
        resources = "health_monitors"
        cmd = healthmonitor.ListHealthMonitor(test_cli20.MyApp(sys.stdout),
                                              None)
        self._test_list_resources(resources, cmd,
                                  sort_key=["name", "id"],
                                  sort_dir=["asc", "desc"])

    def test_list_healthmonitors_limit(self):
        """lb-healthmonitor-list -P."""
        resources = "health_monitors"
        cmd = healthmonitor.ListHealthMonitor(test_cli20.MyApp(sys.stdout),
                                              None)
        self._test_list_resources(resources, cmd, page_size=1000)

    def test_show_healthmonitor_id(self):
        """lb-healthmonitor-show test_id."""
        resource = 'health_monitor'
        cmd = healthmonitor.ShowHealthMonitor(test_cli20.MyApp(sys.stdout),
                                              None)
        args = ['--fields', 'id', self.test_id]
        self._test_show_resource(resource, cmd, self.test_id, args, ['id'])

    def test_show_healthmonitor_id_name(self):
        """lb-healthmonitor-show."""
        resource = 'health_monitor'
        cmd = healthmonitor.ShowHealthMonitor(test_cli20.MyApp(sys.stdout),
                                              None)
        args = ['--fields', 'id', '--fields', 'name', self.test_id]
        self._test_show_resource(resource, cmd, self.test_id,
                                 args, ['id', 'name'])

    def test_update_health_monitor(self):
        """lb-healthmonitor-update  myid --name myname --tags a b."""
        resource = 'health_monitor'
        cmd = healthmonitor.UpdateHealthMonitor(test_cli20.MyApp(sys.stdout),
                                                None)
        self._test_update_resource(resource, cmd, 'myid',
                                   ['myid', '--timeout', '5'],
                                   {'timeout': '5', })

    def test_delete_healthmonitor(self):
        """lb-healthmonitor-delete my-id."""
        resource = 'health_monitor'
        cmd = healthmonitor.DeleteHealthMonitor(test_cli20.MyApp(sys.stdout),
                                                None)
        my_id = 'my-id'
        args = [my_id]
        self._test_delete_resource(resource, cmd, my_id, args)

    def test_associate_healthmonitor(self):
        cmd = healthmonitor.AssociateHealthMonitor(
            test_cli20.MyApp(sys.stdout),
            None)
        resource = 'health_monitor'
        health_monitor_id = 'hm-id'
        pool_id = 'p_id'
        args = [health_monitor_id, pool_id]

        self.mox.StubOutWithMock(cmd, "get_client")
        self.mox.StubOutWithMock(self.client.httpclient, "request")
        cmd.get_client().MultipleTimes().AndReturn(self.client)

        body = {resource: {'id': health_monitor_id}}
        result = {resource: {'id': health_monitor_id}, }
        result_str = self.client.serialize(result)

        path = getattr(self.client,
                       "associate_pool_health_monitors_path") % pool_id
        return_tup = (test_cli20.MyResp(200), result_str)
        self.client.httpclient.request(
            test_cli20.end_url(path), 'POST',
            body=test_cli20.MyComparator(body, self.client),
            headers=mox.ContainsKeyValue(
                'X-Auth-Token', test_cli20.TOKEN)).AndReturn(return_tup)
        self.mox.ReplayAll()
        cmd_parser = cmd.get_parser('test_' + resource)
        parsed_args = cmd_parser.parse_args(args)
        cmd.run(parsed_args)
        self.mox.VerifyAll()
        self.mox.UnsetStubs()

    def test_disassociate_healthmonitor(self):
        cmd = healthmonitor.DisassociateHealthMonitor(
            test_cli20.MyApp(sys.stdout),
            None)
        resource = 'health_monitor'
        health_monitor_id = 'hm-id'
        pool_id = 'p_id'
        args = [health_monitor_id, pool_id]

        self.mox.StubOutWithMock(cmd, "get_client")
        self.mox.StubOutWithMock(self.client.httpclient, "request")
        cmd.get_client().MultipleTimes().AndReturn(self.client)

        path = (getattr(self.client,
                        "disassociate_pool_health_monitors_path") %
                {'pool': pool_id, 'health_monitor': health_monitor_id})
        return_tup = (test_cli20.MyResp(204), None)
        self.client.httpclient.request(
            test_cli20.end_url(path), 'DELETE',
            body=None,
            headers=mox.ContainsKeyValue(
                'X-Auth-Token', test_cli20.TOKEN)).AndReturn(return_tup)
        self.mox.ReplayAll()
        cmd_parser = cmd.get_parser('test_' + resource)
        parsed_args = cmd_parser.parse_args(args)
        cmd.run(parsed_args)
        self.mox.VerifyAll()
        self.mox.UnsetStubs()


class CLITestV20LbHealthmonitorXML(CLITestV20LbHealthmonitorJSON):
    format = 'xml'

########NEW FILE########
__FILENAME__ = test_cli20_member
# Copyright 2013 Mirantis Inc.
# All Rights Reserved
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.
#
# @author: Ilya Shakhat, Mirantis Inc.
#

import sys

from neutronclient.neutron.v2_0.lb import member
from neutronclient.tests.unit import test_cli20


class CLITestV20LbMemberJSON(test_cli20.CLITestV20Base):
    def setUp(self):
        super(CLITestV20LbMemberJSON, self).setUp(plurals={'tags': 'tag'})

    def test_create_member(self):
        """lb-member-create with mandatory params only."""
        resource = 'member'
        cmd = member.CreateMember(test_cli20.MyApp(sys.stdout), None)
        address = '10.0.0.1'
        port = '8080'
        tenant_id = 'my-tenant'
        my_id = 'my-id'
        pool_id = 'pool-id'
        args = ['--address', address, '--protocol-port', port,
                '--tenant-id', tenant_id, pool_id]
        position_names = ['address', 'protocol_port', 'tenant_id', 'pool_id',
                          'admin_state_up']
        position_values = [address, port, tenant_id, pool_id, True]
        self._test_create_resource(resource, cmd, None, my_id, args,
                                   position_names, position_values,
                                   admin_state_up=None)

    def test_create_member_all_params(self):
        """lb-member-create with all available params."""
        resource = 'member'
        cmd = member.CreateMember(test_cli20.MyApp(sys.stdout), None)
        address = '10.0.0.1'
        admin_state_up = False
        port = '8080'
        weight = '1'
        tenant_id = 'my-tenant'
        my_id = 'my-id'
        pool_id = 'pool-id'
        args = ['--address', address, '--admin-state-down',
                '--protocol-port', port, '--weight', weight,
                '--tenant-id', tenant_id, pool_id]
        position_names = [
            'address', 'admin_state_up', 'protocol_port', 'weight',
            'tenant_id', 'pool_id'
        ]
        position_values = [address, admin_state_up, port, weight,
                           tenant_id, pool_id]
        self._test_create_resource(resource, cmd, None, my_id, args,
                                   position_names, position_values,
                                   admin_state_up=None)

    def test_list_members(self):
        """lb-member-list."""
        resources = "members"
        cmd = member.ListMember(test_cli20.MyApp(sys.stdout), None)
        self._test_list_resources(resources, cmd, True)

    def test_list_members_pagination(self):
        """lb-member-list."""
        resources = "members"
        cmd = member.ListMember(test_cli20.MyApp(sys.stdout), None)
        self._test_list_resources_with_pagination(resources, cmd)

    def test_list_members_sort(self):
        """lb-member-list --sort-key name --sort-key id --sort-key asc
        --sort-key desc
        """
        resources = "members"
        cmd = member.ListMember(test_cli20.MyApp(sys.stdout), None)
        self._test_list_resources(resources, cmd,
                                  sort_key=["name", "id"],
                                  sort_dir=["asc", "desc"])

    def test_list_members_limit(self):
        """lb-member-list -P."""
        resources = "members"
        cmd = member.ListMember(test_cli20.MyApp(sys.stdout), None)
        self._test_list_resources(resources, cmd, page_size=1000)

    def test_show_member_id(self):
        """lb-member-show test_id."""
        resource = 'member'
        cmd = member.ShowMember(test_cli20.MyApp(sys.stdout), None)
        args = ['--fields', 'id', self.test_id]
        self._test_show_resource(resource, cmd, self.test_id, args, ['id'])

    def test_show_member_id_name(self):
        """lb-member-show."""
        resource = 'member'
        cmd = member.ShowMember(test_cli20.MyApp(sys.stdout), None)
        args = ['--fields', 'id', '--fields', 'name', self.test_id]
        self._test_show_resource(resource, cmd, self.test_id,
                                 args, ['id', 'name'])

    def test_update_member(self):
        """lb-member-update  myid --name myname --tags a b."""
        resource = 'member'
        cmd = member.UpdateMember(test_cli20.MyApp(sys.stdout), None)
        self._test_update_resource(resource, cmd, 'myid',
                                   ['myid', '--name', 'myname',
                                    '--tags', 'a', 'b'],
                                   {'name': 'myname', 'tags': ['a', 'b'], })

    def test_delete_member(self):
        """lb-member-delete my-id."""
        resource = 'member'
        cmd = member.DeleteMember(test_cli20.MyApp(sys.stdout), None)
        my_id = 'my-id'
        args = [my_id]
        self._test_delete_resource(resource, cmd, my_id, args)


class CLITestV20LbMemberXML(CLITestV20LbMemberJSON):
    format = 'xml'

########NEW FILE########
__FILENAME__ = test_cli20_pool
# Copyright 2013 Mirantis Inc.
# All Rights Reserved
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.
#
# @author: Ilya Shakhat, Mirantis Inc.
#

import sys

import mox

from neutronclient.neutron.v2_0.lb import pool
from neutronclient.tests.unit import test_cli20


class CLITestV20LbPoolJSON(test_cli20.CLITestV20Base):

    def test_create_pool_with_mandatory_params(self):
        """lb-pool-create with mandatory params only."""
        resource = 'pool'
        cmd = pool.CreatePool(test_cli20.MyApp(sys.stdout), None)
        name = 'my-name'
        lb_method = 'ROUND_ROBIN'
        protocol = 'HTTP'
        subnet_id = 'subnet-id'
        tenant_id = 'my-tenant'
        my_id = 'my-id'
        args = ['--lb-method', lb_method,
                '--name', name,
                '--protocol', protocol,
                '--subnet-id', subnet_id,
                '--tenant-id', tenant_id]
        position_names = ['admin_state_up', 'lb_method', 'name',
                          'protocol', 'subnet_id', 'tenant_id']
        position_values = [True, lb_method, name,
                           protocol, subnet_id, tenant_id]
        self._test_create_resource(resource, cmd, name, my_id, args,
                                   position_names, position_values)

    def test_create_pool_with_all_params(self):
        """lb-pool-create with all params set."""
        resource = 'pool'
        cmd = pool.CreatePool(test_cli20.MyApp(sys.stdout), None)
        name = 'my-name'
        description = 'my-desc'
        lb_method = 'ROUND_ROBIN'
        protocol = 'HTTP'
        subnet_id = 'subnet-id'
        tenant_id = 'my-tenant'
        my_id = 'my-id'
        provider = 'lbaas'
        args = ['--admin-state-down',
                '--description', description,
                '--lb-method', lb_method,
                '--name', name,
                '--protocol', protocol,
                '--subnet-id', subnet_id,
                '--tenant-id', tenant_id,
                '--provider', provider]
        position_names = ['admin_state_up', 'description', 'lb_method', 'name',
                          'protocol', 'subnet_id', 'tenant_id', 'provider']
        position_values = [False, description, lb_method, name,
                           protocol, subnet_id, tenant_id, provider]
        self._test_create_resource(resource, cmd, name, my_id, args,
                                   position_names, position_values)

    def test_list_pools(self):
        """lb-pool-list."""
        resources = "pools"
        cmd = pool.ListPool(test_cli20.MyApp(sys.stdout), None)
        self._test_list_resources(resources, cmd, True)

    def test_list_pools_pagination(self):
        """lb-pool-list."""
        resources = "pools"
        cmd = pool.ListPool(test_cli20.MyApp(sys.stdout), None)
        self._test_list_resources_with_pagination(resources, cmd)

    def test_list_pools_sort(self):
        """lb-pool-list --sort-key name --sort-key id --sort-key asc
        --sort-key desc
        """
        resources = "pools"
        cmd = pool.ListPool(test_cli20.MyApp(sys.stdout), None)
        self._test_list_resources(resources, cmd,
                                  sort_key=["name", "id"],
                                  sort_dir=["asc", "desc"])

    def test_list_pools_limit(self):
        """lb-pool-list -P."""
        resources = "pools"
        cmd = pool.ListPool(test_cli20.MyApp(sys.stdout), None)
        self._test_list_resources(resources, cmd, page_size=1000)

    def test_show_pool_id(self):
        """lb-pool-show test_id."""
        resource = 'pool'
        cmd = pool.ShowPool(test_cli20.MyApp(sys.stdout), None)
        args = ['--fields', 'id', self.test_id]
        self._test_show_resource(resource, cmd, self.test_id, args, ['id'])

    def test_show_pool_id_name(self):
        """lb-pool-show."""
        resource = 'pool'
        cmd = pool.ShowPool(test_cli20.MyApp(sys.stdout), None)
        args = ['--fields', 'id', '--fields', 'name', self.test_id]
        self._test_show_resource(resource, cmd, self.test_id,
                                 args, ['id', 'name'])

    def test_update_pool(self):
        """lb-pool-update myid --name newname --tags a b."""
        resource = 'pool'
        cmd = pool.UpdatePool(test_cli20.MyApp(sys.stdout), None)
        self._test_update_resource(resource, cmd, 'myid',
                                   ['myid', '--name', 'newname'],
                                   {'name': 'newname', })

    def test_delete_pool(self):
        """lb-pool-delete my-id."""
        resource = 'pool'
        cmd = pool.DeletePool(test_cli20.MyApp(sys.stdout), None)
        my_id = 'my-id'
        args = [my_id]
        self._test_delete_resource(resource, cmd, my_id, args)

    def test_retrieve_pool_stats(self):
        """lb-pool-stats test_id."""
        resource = 'pool'
        cmd = pool.RetrievePoolStats(test_cli20.MyApp(sys.stdout), None)
        my_id = self.test_id
        fields = ['bytes_in', 'bytes_out']
        args = ['--fields', 'bytes_in', '--fields', 'bytes_out', my_id]

        self.mox.StubOutWithMock(cmd, "get_client")
        self.mox.StubOutWithMock(self.client.httpclient, "request")
        cmd.get_client().MultipleTimes().AndReturn(self.client)
        query = "&".join(["fields=%s" % field for field in fields])
        expected_res = {'stats': {'bytes_in': '1234', 'bytes_out': '4321'}}
        resstr = self.client.serialize(expected_res)
        path = getattr(self.client, "pool_path_stats")
        return_tup = (test_cli20.MyResp(200), resstr)
        self.client.httpclient.request(
            test_cli20.end_url(path % my_id, query), 'GET',
            body=None,
            headers=mox.ContainsKeyValue(
                'X-Auth-Token', test_cli20.TOKEN)).AndReturn(return_tup)
        self.mox.ReplayAll()

        cmd_parser = cmd.get_parser("test_" + resource)
        parsed_args = cmd_parser.parse_args(args)
        cmd.run(parsed_args)

        self.mox.VerifyAll()
        self.mox.UnsetStubs()
        _str = self.fake_stdout.make_string()
        self.assertIn('bytes_in', _str)
        self.assertIn('bytes_out', _str)


class CLITestV20LbPoolXML(CLITestV20LbPoolJSON):
    format = 'xml'

########NEW FILE########
__FILENAME__ = test_cli20_vip
# Copyright 2013 Mirantis Inc.
# All Rights Reserved
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.
#
# @author: Ilya Shakhat, Mirantis Inc.
#

import sys

from neutronclient.neutron.v2_0.lb import vip
from neutronclient.tests.unit import test_cli20


class CLITestV20LbVipJSON(test_cli20.CLITestV20Base):
    def setUp(self):
        super(CLITestV20LbVipJSON, self).setUp(plurals={'tags': 'tag'})

    def test_create_vip_with_mandatory_params(self):
        """lb-vip-create with all mandatory params."""
        resource = 'vip'
        cmd = vip.CreateVip(test_cli20.MyApp(sys.stdout), None)
        pool_id = 'my-pool-id'
        name = 'my-name'
        subnet_id = 'subnet-id'
        protocol_port = '1000'
        protocol = 'TCP'
        tenant_id = 'my-tenant'
        my_id = 'my-id'
        args = ['--name', name,
                '--protocol-port', protocol_port,
                '--protocol', protocol,
                '--subnet-id', subnet_id,
                '--tenant-id', tenant_id,
                pool_id]
        position_names = ['pool_id', 'name', 'protocol_port', 'protocol',
                          'subnet_id', 'tenant_id']
        position_values = [pool_id, name, protocol_port, protocol,
                           subnet_id, tenant_id]
        self._test_create_resource(resource, cmd, name, my_id, args,
                                   position_names, position_values,
                                   admin_state_up=True)

    def test_create_vip_with_all_params(self):
        """lb-vip-create with all params."""
        resource = 'vip'
        cmd = vip.CreateVip(test_cli20.MyApp(sys.stdout), None)
        pool_id = 'my-pool-id'
        name = 'my-name'
        description = 'my-desc'
        address = '10.0.0.2'
        admin_state = False
        connection_limit = '1000'
        subnet_id = 'subnet-id'
        protocol_port = '80'
        protocol = 'TCP'
        tenant_id = 'my-tenant'
        my_id = 'my-id'
        args = ['--name', name,
                '--description', description,
                '--address', address,
                '--admin-state-down',
                '--connection-limit', connection_limit,
                '--protocol-port', protocol_port,
                '--protocol', protocol,
                '--subnet-id', subnet_id,
                '--tenant-id', tenant_id,
                pool_id]
        position_names = ['pool_id', 'name', 'description', 'address',
                          'admin_state_up', 'connection_limit',
                          'protocol_port', 'protocol', 'subnet_id',
                          'tenant_id']
        position_values = [pool_id, name, description, address,
                           admin_state, connection_limit, protocol_port,
                           protocol, subnet_id,
                           tenant_id]
        self._test_create_resource(resource, cmd, name, my_id, args,
                                   position_names, position_values)

    def test_create_vip_with_session_persistence_params(self):
        """lb-vip-create with mandatory and session-persistence params."""
        resource = 'vip'
        cmd = vip.CreateVip(test_cli20.MyApp(sys.stdout), None)
        pool_id = 'my-pool-id'
        name = 'my-name'
        subnet_id = 'subnet-id'
        protocol_port = '1000'
        protocol = 'TCP'
        tenant_id = 'my-tenant'
        my_id = 'my-id'
        args = ['--name', name,
                '--protocol-port', protocol_port,
                '--protocol', protocol,
                '--subnet-id', subnet_id,
                '--tenant-id', tenant_id,
                pool_id,
                '--session-persistence', 'type=dict',
                'type=cookie,cookie_name=pie',
                '--optional-param', 'any']
        position_names = ['pool_id', 'name', 'protocol_port', 'protocol',
                          'subnet_id', 'tenant_id', 'optional_param']
        position_values = [pool_id, name, protocol_port, protocol,
                           subnet_id, tenant_id, 'any']
        extra_body = {
            'session_persistence': {
                'type': 'cookie',
                'cookie_name': 'pie',
            },
        }
        self._test_create_resource(resource, cmd, name, my_id, args,
                                   position_names, position_values,
                                   admin_state_up=True, extra_body=extra_body)

    def test_list_vips(self):
        """lb-vip-list."""
        resources = "vips"
        cmd = vip.ListVip(test_cli20.MyApp(sys.stdout), None)
        self._test_list_resources(resources, cmd, True)

    def test_list_vips_pagination(self):
        """lb-vip-list."""
        resources = "vips"
        cmd = vip.ListVip(test_cli20.MyApp(sys.stdout), None)
        self._test_list_resources_with_pagination(resources, cmd)

    def test_list_vips_sort(self):
        """lb-vip-list --sort-key name --sort-key id --sort-key asc
        --sort-key desc
        """
        resources = "vips"
        cmd = vip.ListVip(test_cli20.MyApp(sys.stdout), None)
        self._test_list_resources(resources, cmd,
                                  sort_key=["name", "id"],
                                  sort_dir=["asc", "desc"])

    def test_list_vips_limit(self):
        """lb-vip-list -P."""
        resources = "vips"
        cmd = vip.ListVip(test_cli20.MyApp(sys.stdout), None)
        self._test_list_resources(resources, cmd, page_size=1000)

    def test_show_vip_id(self):
        """lb-vip-show test_id."""
        resource = 'vip'
        cmd = vip.ShowVip(test_cli20.MyApp(sys.stdout), None)
        args = ['--fields', 'id', self.test_id]
        self._test_show_resource(resource, cmd, self.test_id, args, ['id'])

    def test_show_vip_id_name(self):
        """lb-vip-show."""
        resource = 'vip'
        cmd = vip.ShowVip(test_cli20.MyApp(sys.stdout), None)
        args = ['--fields', 'id', '--fields', 'name', self.test_id]
        self._test_show_resource(resource, cmd, self.test_id,
                                 args, ['id', 'name'])

    def test_update_vip(self):
        """lb-vip-update  myid --name myname --tags a b."""
        resource = 'vip'
        cmd = vip.UpdateVip(test_cli20.MyApp(sys.stdout), None)
        self._test_update_resource(resource, cmd, 'myid',
                                   ['myid', '--name', 'myname',
                                    '--tags', 'a', 'b'],
                                   {'name': 'myname', 'tags': ['a', 'b'], })

    def test_update_vip_with_session_persistence(self):
        resource = 'vip'
        cmd = vip.UpdateVip(test_cli20.MyApp(sys.stdout), None)
        body = {
            'session_persistence': {
                'type': 'source',
            },
        }
        args = ['myid', '--session-persistence', 'type=dict',
                'type=source']
        self._test_update_resource(resource, cmd, 'myid', args, body)

    def test_update_vip_with_session_persistence_and_name(self):
        resource = 'vip'
        cmd = vip.UpdateVip(test_cli20.MyApp(sys.stdout), None)
        body = {
            'name': 'newname',
            'session_persistence': {
                'type': 'cookie',
                'cookie_name': 'pie',
            },
        }
        args = ['myid', '--name', 'newname',
                '--session-persistence', 'type=dict',
                'type=cookie,cookie_name=pie']
        self._test_update_resource(resource, cmd, 'myid', args, body)

    def test_delete_vip(self):
        """lb-vip-delete my-id."""
        resource = 'vip'
        cmd = vip.DeleteVip(test_cli20.MyApp(sys.stdout), None)
        my_id = 'my-id'
        args = [my_id]
        self._test_delete_resource(resource, cmd, my_id, args)


class CLITestV20LbVipXML(CLITestV20LbVipJSON):
    format = 'xml'

########NEW FILE########
__FILENAME__ = test_auth
# Copyright 2012 NEC Corporation
# All Rights Reserved
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.
#

import copy
import json
import uuid

import mox
import requests
import testtools

from neutronclient import client
from neutronclient.common import exceptions
from neutronclient.common import utils


USERNAME = 'testuser'
USER_ID = 'testuser_id'
TENANT_NAME = 'testtenant'
TENANT_ID = 'testtenant_id'
PASSWORD = 'password'
AUTH_URL = 'authurl'
ENDPOINT_URL = 'localurl'
ENDPOINT_OVERRIDE = 'otherurl'
TOKEN = 'tokentoken'
REGION = 'RegionTest'
NOAUTH = 'noauth'

KS_TOKEN_RESULT = {
    'access': {
        'token': {'id': TOKEN,
                  'expires': '2012-08-11T07:49:01Z',
                  'tenant': {'id': str(uuid.uuid1())}},
        'user': {'id': str(uuid.uuid1())},
        'serviceCatalog': [
            {'endpoints_links': [],
             'endpoints': [{'adminURL': ENDPOINT_URL,
                            'internalURL': ENDPOINT_URL,
                            'publicURL': ENDPOINT_URL,
                            'region': REGION}],
             'type': 'network',
             'name': 'Neutron Service'}
        ]
    }
}

ENDPOINTS_RESULT = {
    'endpoints': [{
        'type': 'network',
        'name': 'Neutron Service',
        'region': REGION,
        'adminURL': ENDPOINT_URL,
        'internalURL': ENDPOINT_URL,
        'publicURL': ENDPOINT_URL
    }]
}


def get_response(status_code, headers=None):
    response = mox.Mox().CreateMock(requests.Response)
    response.headers = headers or {}
    response.status_code = status_code
    return response


class CLITestAuthNoAuth(testtools.TestCase):

    def setUp(self):
        """Prepare the test environment."""
        super(CLITestAuthNoAuth, self).setUp()
        self.mox = mox.Mox()
        self.client = client.HTTPClient(username=USERNAME,
                                        tenant_name=TENANT_NAME,
                                        password=PASSWORD,
                                        endpoint_url=ENDPOINT_URL,
                                        auth_strategy=NOAUTH,
                                        region_name=REGION)
        self.addCleanup(self.mox.VerifyAll)
        self.addCleanup(self.mox.UnsetStubs)

    def test_get_noauth(self):
        self.mox.StubOutWithMock(self.client, "request")

        res200 = get_response(200)

        self.client.request(
            mox.StrContains(ENDPOINT_URL + '/resource'), 'GET',
            headers=mox.IsA(dict),
        ).AndReturn((res200, ''))
        self.mox.ReplayAll()

        self.client.do_request('/resource', 'GET')
        self.assertEqual(self.client.endpoint_url, ENDPOINT_URL)


class CLITestAuthKeystone(testtools.TestCase):

    # Auth Body expected
    auth_body = ('{"auth": {"tenantName": "testtenant", '
                 '"passwordCredentials": '
                 '{"username": "testuser", "password": "password"}}}')

    def setUp(self):
        """Prepare the test environment."""
        super(CLITestAuthKeystone, self).setUp()
        self.mox = mox.Mox()
        self.client = client.HTTPClient(username=USERNAME,
                                        tenant_name=TENANT_NAME,
                                        password=PASSWORD,
                                        auth_url=AUTH_URL,
                                        region_name=REGION)
        self.addCleanup(self.mox.VerifyAll)
        self.addCleanup(self.mox.UnsetStubs)

    def test_reused_token_get_auth_info(self):
        """Test that Client.get_auth_info() works even if client was
           instantiated with predefined token.
        """
        client_ = client.HTTPClient(username=USERNAME,
                                    tenant_name=TENANT_NAME,
                                    token=TOKEN,
                                    password=PASSWORD,
                                    auth_url=AUTH_URL,
                                    region_name=REGION)
        expected = {'auth_token': TOKEN,
                    'auth_tenant_id': None,
                    'auth_user_id': None,
                    'endpoint_url': self.client.endpoint_url}
        self.assertEqual(client_.get_auth_info(), expected)

    def test_get_token(self):
        self.mox.StubOutWithMock(self.client, "request")

        res200 = get_response(200)

        self.client.request(
            AUTH_URL + '/tokens', 'POST',
            body=self.auth_body, headers=mox.IsA(dict)
        ).AndReturn((res200, json.dumps(KS_TOKEN_RESULT)))
        self.client.request(
            mox.StrContains(ENDPOINT_URL + '/resource'), 'GET',
            headers=mox.ContainsKeyValue('X-Auth-Token', TOKEN)
        ).AndReturn((res200, ''))
        self.mox.ReplayAll()

        self.client.do_request('/resource', 'GET')
        self.assertEqual(self.client.endpoint_url, ENDPOINT_URL)
        self.assertEqual(self.client.auth_token, TOKEN)

    def test_refresh_token(self):
        self.mox.StubOutWithMock(self.client, "request")

        self.client.auth_token = TOKEN
        self.client.endpoint_url = ENDPOINT_URL

        res200 = get_response(200)
        res401 = get_response(401)

        # If a token is expired, neutron server retruns 401
        self.client.request(
            mox.StrContains(ENDPOINT_URL + '/resource'), 'GET',
            headers=mox.ContainsKeyValue('X-Auth-Token', TOKEN)
        ).AndReturn((res401, ''))
        self.client.request(
            AUTH_URL + '/tokens', 'POST',
            body=mox.IsA(str), headers=mox.IsA(dict)
        ).AndReturn((res200, json.dumps(KS_TOKEN_RESULT)))
        self.client.request(
            mox.StrContains(ENDPOINT_URL + '/resource'), 'GET',
            headers=mox.ContainsKeyValue('X-Auth-Token', TOKEN)
        ).AndReturn((res200, ''))
        self.mox.ReplayAll()
        self.client.do_request('/resource', 'GET')

    def test_refresh_token_no_auth_url(self):
        self.mox.StubOutWithMock(self.client, "request")
        self.client.auth_url = None

        self.client.auth_token = TOKEN
        self.client.endpoint_url = ENDPOINT_URL

        res401 = get_response(401)

        # If a token is expired, neutron server returns 401
        self.client.request(
            mox.StrContains(ENDPOINT_URL + '/resource'), 'GET',
            headers=mox.ContainsKeyValue('X-Auth-Token', TOKEN)
        ).AndReturn((res401, ''))
        self.mox.ReplayAll()
        self.assertRaises(exceptions.NoAuthURLProvided,
                          self.client.do_request,
                          '/resource',
                          'GET')

    def test_get_endpoint_url_with_invalid_auth_url(self):
        # Handle the case when auth_url is not provided
        self.client.auth_url = None
        self.assertRaises(exceptions.NoAuthURLProvided,
                          self.client._get_endpoint_url)

    def test_get_endpoint_url(self):
        self.mox.StubOutWithMock(self.client, "request")

        self.client.auth_token = TOKEN

        res200 = get_response(200)

        self.client.request(
            mox.StrContains(AUTH_URL + '/tokens/%s/endpoints' % TOKEN), 'GET',
            headers=mox.IsA(dict)
        ).AndReturn((res200, json.dumps(ENDPOINTS_RESULT)))
        self.client.request(
            mox.StrContains(ENDPOINT_URL + '/resource'), 'GET',
            headers=mox.ContainsKeyValue('X-Auth-Token', TOKEN)
        ).AndReturn((res200, ''))
        self.mox.ReplayAll()
        self.client.do_request('/resource', 'GET')

    def test_use_given_endpoint_url(self):
        self.client = client.HTTPClient(
            username=USERNAME, tenant_name=TENANT_NAME, password=PASSWORD,
            auth_url=AUTH_URL, region_name=REGION,
            endpoint_url=ENDPOINT_OVERRIDE)
        self.assertEqual(self.client.endpoint_url, ENDPOINT_OVERRIDE)

        self.mox.StubOutWithMock(self.client, "request")

        self.client.auth_token = TOKEN
        res200 = get_response(200)

        self.client.request(
            mox.StrContains(ENDPOINT_OVERRIDE + '/resource'), 'GET',
            headers=mox.ContainsKeyValue('X-Auth-Token', TOKEN)
        ).AndReturn((res200, ''))
        self.mox.ReplayAll()
        self.client.do_request('/resource', 'GET')
        self.assertEqual(self.client.endpoint_url, ENDPOINT_OVERRIDE)

    def test_get_endpoint_url_other(self):
        self.client = client.HTTPClient(
            username=USERNAME, tenant_name=TENANT_NAME, password=PASSWORD,
            auth_url=AUTH_URL, region_name=REGION, endpoint_type='otherURL')
        self.mox.StubOutWithMock(self.client, "request")

        self.client.auth_token = TOKEN
        res200 = get_response(200)

        self.client.request(
            mox.StrContains(AUTH_URL + '/tokens/%s/endpoints' % TOKEN), 'GET',
            headers=mox.IsA(dict)
        ).AndReturn((res200, json.dumps(ENDPOINTS_RESULT)))
        self.mox.ReplayAll()
        self.assertRaises(exceptions.EndpointTypeNotFound,
                          self.client.do_request,
                          '/resource',
                          'GET')

    def test_get_endpoint_url_failed(self):
        self.mox.StubOutWithMock(self.client, "request")

        self.client.auth_token = TOKEN

        res200 = get_response(200)
        res401 = get_response(401)

        self.client.request(
            mox.StrContains(AUTH_URL + '/tokens/%s/endpoints' % TOKEN), 'GET',
            headers=mox.IsA(dict)
        ).AndReturn((res401, ''))
        self.client.request(
            AUTH_URL + '/tokens', 'POST',
            body=mox.IsA(str), headers=mox.IsA(dict)
        ).AndReturn((res200, json.dumps(KS_TOKEN_RESULT)))
        self.client.request(
            mox.StrContains(ENDPOINT_URL + '/resource'), 'GET',
            headers=mox.ContainsKeyValue('X-Auth-Token', TOKEN)
        ).AndReturn((res200, ''))
        self.mox.ReplayAll()
        self.client.do_request('/resource', 'GET')

    def test_url_for(self):
        resources = copy.deepcopy(KS_TOKEN_RESULT)

        endpoints = resources['access']['serviceCatalog'][0]['endpoints'][0]
        endpoints['publicURL'] = 'public'
        endpoints['internalURL'] = 'internal'
        endpoints['adminURL'] = 'admin'
        catalog = client.ServiceCatalog(resources)

        # endpoint_type not specified
        url = catalog.url_for(attr='region',
                              filter_value=REGION)
        self.assertEqual('public', url)

        # endpoint type specified (3 cases)
        url = catalog.url_for(attr='region',
                              filter_value=REGION,
                              endpoint_type='adminURL')
        self.assertEqual('admin', url)

        url = catalog.url_for(attr='region',
                              filter_value=REGION,
                              endpoint_type='publicURL')
        self.assertEqual('public', url)

        url = catalog.url_for(attr='region',
                              filter_value=REGION,
                              endpoint_type='internalURL')
        self.assertEqual('internal', url)

        # endpoint_type requested does not exist.
        self.assertRaises(exceptions.EndpointTypeNotFound,
                          catalog.url_for,
                          attr='region',
                          filter_value=REGION,
                          endpoint_type='privateURL')

    # Test scenario with url_for when the service catalog only has publicURL.
    def test_url_for_only_public_url(self):
        resources = copy.deepcopy(KS_TOKEN_RESULT)
        catalog = client.ServiceCatalog(resources)

        # Remove endpoints from the catalog.
        endpoints = resources['access']['serviceCatalog'][0]['endpoints'][0]
        del endpoints['internalURL']
        del endpoints['adminURL']
        endpoints['publicURL'] = 'public'

        # Use publicURL when specified explicitly.
        url = catalog.url_for(attr='region',
                              filter_value=REGION,
                              endpoint_type='publicURL')
        self.assertEqual('public', url)

        # Use publicURL when specified explicitly.
        url = catalog.url_for(attr='region',
                              filter_value=REGION)
        self.assertEqual('public', url)

    # Test scenario with url_for when the service catalog only has adminURL.
    def test_url_for_only_admin_url(self):
        resources = copy.deepcopy(KS_TOKEN_RESULT)
        catalog = client.ServiceCatalog(resources)
        endpoints = resources['access']['serviceCatalog'][0]['endpoints'][0]
        del endpoints['internalURL']
        del endpoints['publicURL']
        endpoints['adminURL'] = 'admin'

        # Use publicURL when specified explicitly.
        url = catalog.url_for(attr='region',
                              filter_value=REGION,
                              endpoint_type='adminURL')
        self.assertEqual('admin', url)

        # But not when nothing is specified.
        self.assertRaises(exceptions.EndpointTypeNotFound,
                          catalog.url_for,
                          attr='region',
                          filter_value=REGION)

    def test_endpoint_type(self):
        resources = copy.deepcopy(KS_TOKEN_RESULT)
        endpoints = resources['access']['serviceCatalog'][0]['endpoints'][0]
        endpoints['internalURL'] = 'internal'
        endpoints['adminURL'] = 'admin'
        endpoints['publicURL'] = 'public'

        # Test default behavior is to choose public.
        self.client = client.HTTPClient(
            username=USERNAME, tenant_name=TENANT_NAME, password=PASSWORD,
            auth_url=AUTH_URL, region_name=REGION)

        self.client._extract_service_catalog(resources)
        self.assertEqual(self.client.endpoint_url, 'public')

        # Test admin url
        self.client = client.HTTPClient(
            username=USERNAME, tenant_name=TENANT_NAME, password=PASSWORD,
            auth_url=AUTH_URL, region_name=REGION, endpoint_type='adminURL')

        self.client._extract_service_catalog(resources)
        self.assertEqual(self.client.endpoint_url, 'admin')

        # Test public url
        self.client = client.HTTPClient(
            username=USERNAME, tenant_name=TENANT_NAME, password=PASSWORD,
            auth_url=AUTH_URL, region_name=REGION, endpoint_type='publicURL')

        self.client._extract_service_catalog(resources)
        self.assertEqual(self.client.endpoint_url, 'public')

        # Test internal url
        self.client = client.HTTPClient(
            username=USERNAME, tenant_name=TENANT_NAME, password=PASSWORD,
            auth_url=AUTH_URL, region_name=REGION, endpoint_type='internalURL')

        self.client._extract_service_catalog(resources)
        self.assertEqual(self.client.endpoint_url, 'internal')

        # Test url that isn't found in the service catalog
        self.client = client.HTTPClient(
            username=USERNAME, tenant_name=TENANT_NAME, password=PASSWORD,
            auth_url=AUTH_URL, region_name=REGION, endpoint_type='privateURL')

        self.assertRaises(exceptions.EndpointTypeNotFound,
                          self.client._extract_service_catalog,
                          resources)

    def test_strip_credentials_from_log(self):
        def verify_no_credentials(kwargs):
            return ('REDACTED' in kwargs['body']) and (
                self.client.password not in kwargs['body'])

        def verify_credentials(body):
            return 'REDACTED' not in body and self.client.password in body

        self.mox.StubOutWithMock(self.client, "request")
        self.mox.StubOutWithMock(utils, "http_log_req")

        res200 = get_response(200)

        utils.http_log_req(mox.IgnoreArg(), mox.IgnoreArg(), mox.Func(
            verify_no_credentials))
        self.client.request(
            mox.IsA(str), mox.IsA(str), body=mox.Func(verify_credentials),
            headers=mox.IgnoreArg()
        ).AndReturn((res200, json.dumps(KS_TOKEN_RESULT)))
        utils.http_log_req(mox.IgnoreArg(), mox.IgnoreArg(), mox.IgnoreArg())
        self.client.request(
            mox.IsA(str), mox.IsA(str), headers=mox.IsA(dict)
        ).AndReturn((res200, ''))
        self.mox.ReplayAll()

        self.client.do_request('/resource', 'GET')


class CLITestAuthKeystoneWithId(CLITestAuthKeystone):

    # Auth Body expected
    auth_body = ('{"auth": {"passwordCredentials": '
                 '{"password": "password", "userId": "testuser_id"}, '
                 '"tenantId": "testtenant_id"}}')

    def setUp(self):
        """Prepare the test environment."""
        super(CLITestAuthKeystoneWithId, self).setUp()
        self.client = client.HTTPClient(user_id=USER_ID,
                                        tenant_id=TENANT_ID,
                                        password=PASSWORD,
                                        auth_url=AUTH_URL,
                                        region_name=REGION)


class CLITestAuthKeystoneWithIdandName(CLITestAuthKeystone):

    # Auth Body expected
    auth_body = ('{"auth": {"passwordCredentials": '
                 '{"password": "password", "userId": "testuser_id"}, '
                 '"tenantId": "testtenant_id"}}')

    def setUp(self):
        """Prepare the test environment."""
        super(CLITestAuthKeystoneWithIdandName, self).setUp()
        self.client = client.HTTPClient(username=USERNAME,
                                        user_id=USER_ID,
                                        tenant_id=TENANT_ID,
                                        tenant_name=TENANT_NAME,
                                        password=PASSWORD,
                                        auth_url=AUTH_URL,
                                        region_name=REGION)

########NEW FILE########
__FILENAME__ = test_casual_args
# Copyright 2012 OpenStack Foundation.
# All Rights Reserved
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.
#

import testtools

from neutronclient.common import exceptions
from neutronclient.neutron import v2_0 as neutronV20


class CLITestArgs(testtools.TestCase):

    def test_empty(self):
        _mydict = neutronV20.parse_args_to_dict([])
        self.assertEqual({}, _mydict)

    def test_default_bool(self):
        _specs = ['--my_bool', '--arg1', 'value1']
        _mydict = neutronV20.parse_args_to_dict(_specs)
        self.assertTrue(_mydict['my_bool'])

    def test_bool_true(self):
        _specs = ['--my-bool', 'type=bool', 'true', '--arg1', 'value1']
        _mydict = neutronV20.parse_args_to_dict(_specs)
        self.assertTrue(_mydict['my_bool'])

    def test_bool_false(self):
        _specs = ['--my_bool', 'type=bool', 'false', '--arg1', 'value1']
        _mydict = neutronV20.parse_args_to_dict(_specs)
        self.assertFalse(_mydict['my_bool'])

    def test_nargs(self):
        _specs = ['--tag', 'x', 'y', '--arg1', 'value1']
        _mydict = neutronV20.parse_args_to_dict(_specs)
        self.assertIn('x', _mydict['tag'])
        self.assertIn('y', _mydict['tag'])

    def test_badarg(self):
        _specs = ['--tag=t', 'x', 'y', '--arg1', 'value1']
        self.assertRaises(exceptions.CommandError,
                          neutronV20.parse_args_to_dict, _specs)

    def test_badarg_with_minus(self):
        _specs = ['--arg1', 'value1', '-D']
        self.assertRaises(exceptions.CommandError,
                          neutronV20.parse_args_to_dict, _specs)

    def test_goodarg_with_minus_number(self):
        _specs = ['--arg1', 'value1', '-1', '-1.0']
        _mydict = neutronV20.parse_args_to_dict(_specs)
        self.assertEqual(['value1', '-1', '-1.0'],
                         _mydict['arg1'])

    def test_badarg_duplicate(self):
        _specs = ['--tag=t', '--arg1', 'value1', '--arg1', 'value1']
        self.assertRaises(exceptions.CommandError,
                          neutronV20.parse_args_to_dict, _specs)

    def test_badarg_early_type_specification(self):
        _specs = ['type=dict', 'key=value']
        self.assertRaises(exceptions.CommandError,
                          neutronV20.parse_args_to_dict, _specs)

    def test_arg(self):
        _specs = ['--tag=t', '--arg1', 'value1']
        self.assertEqual('value1',
                         neutronV20.parse_args_to_dict(_specs)['arg1'])

    def test_dict_arg(self):
        _specs = ['--tag=t', '--arg1', 'type=dict', 'key1=value1,key2=value2']
        arg1 = neutronV20.parse_args_to_dict(_specs)['arg1']
        self.assertEqual('value1', arg1['key1'])
        self.assertEqual('value2', arg1['key2'])

    def test_dict_arg_with_attribute_named_type(self):
        _specs = ['--tag=t', '--arg1', 'type=dict', 'type=value1,key2=value2']
        arg1 = neutronV20.parse_args_to_dict(_specs)['arg1']
        self.assertEqual('value1', arg1['type'])
        self.assertEqual('value2', arg1['key2'])

    def test_list_of_dict_arg(self):
        _specs = ['--tag=t', '--arg1', 'type=dict',
                  'list=true', 'key1=value1,key2=value2']
        arg1 = neutronV20.parse_args_to_dict(_specs)['arg1']
        self.assertEqual('value1', arg1[0]['key1'])
        self.assertEqual('value2', arg1[0]['key2'])

    def test_clear_action(self):
        _specs = ['--anyarg', 'action=clear']
        args = neutronV20.parse_args_to_dict(_specs)
        self.assertIsNone(args['anyarg'])

    def test_bad_values_str(self):
        _specs = ['--strarg', 'type=str']
        self.assertRaises(exceptions.CommandError,
                          neutronV20.parse_args_to_dict, _specs)

    def test_bad_values_list(self):
        _specs = ['--listarg', 'list=true', 'type=str']
        self.assertRaises(exceptions.CommandError,
                          neutronV20.parse_args_to_dict, _specs)
        _specs = ['--listarg', 'type=list']
        self.assertRaises(exceptions.CommandError,
                          neutronV20.parse_args_to_dict, _specs)
        _specs = ['--listarg', 'type=list', 'action=clear']
        self.assertRaises(exceptions.CommandError,
                          neutronV20.parse_args_to_dict, _specs)

########NEW FILE########
__FILENAME__ = test_cli20
# Copyright 2012 OpenStack Foundation.
# All Rights Reserved
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.
#

import urllib

import contextlib
import cStringIO
import fixtures
import mox
import sys
import testtools

from neutronclient.common import constants
from neutronclient.common import exceptions
from neutronclient.neutron import v2_0 as neutronV2_0
from neutronclient import shell
from neutronclient.v2_0 import client

API_VERSION = "2.0"
FORMAT = 'json'
TOKEN = 'testtoken'
ENDURL = 'localurl'


@contextlib.contextmanager
def capture_std_streams():
    fake_stdout, fake_stderr = cStringIO.StringIO(), cStringIO.StringIO()
    stdout, stderr = sys.stdout, sys.stderr
    try:
        sys.stdout, sys.stderr = fake_stdout, fake_stderr
        yield fake_stdout, fake_stderr
    finally:
        sys.stdout, sys.stderr = stdout, stderr


class FakeStdout:

    def __init__(self):
        self.content = []

    def write(self, text):
        self.content.append(text)

    def make_string(self):
        result = ''
        for line in self.content:
            result = result + line
        return result


class MyResp(object):
    def __init__(self, status_code, headers=None, reason=None):
        self.status_code = status_code
        self.headers = headers or {}
        self.reason = reason


class MyApp(object):
    def __init__(self, _stdout):
        self.stdout = _stdout


def end_url(path, query=None, format=FORMAT):
    _url_str = ENDURL + "/v" + API_VERSION + path + "." + format
    return query and _url_str + "?" + query or _url_str


class MyUrlComparator(mox.Comparator):
    def __init__(self, lhs, client):
        self.lhs = lhs
        self.client = client

    def equals(self, rhs):
        return str(self) == rhs

    def __str__(self):
        if self.client and self.client.format != FORMAT:
            lhs_parts = self.lhs.split("?", 1)
            if len(lhs_parts) == 2:
                lhs = ("%s.%s?%s" % (lhs_parts[0][:-4],
                                     self.client.format,
                                     lhs_parts[1]))
            else:
                lhs = ("%s.%s" % (lhs_parts[0][:-4],
                                  self.client.format))
            return lhs
        return self.lhs

    def __repr__(self):
        return str(self)


class MyComparator(mox.Comparator):
    def __init__(self, lhs, client):
        self.lhs = lhs
        self.client = client

    def _com_dict(self, lhs, rhs):
        if len(lhs) != len(rhs):
            return False
        for key, value in lhs.iteritems():
            if key not in rhs:
                return False
            rhs_value = rhs[key]
            if not self._com(value, rhs_value):
                return False
        return True

    def _com_list(self, lhs, rhs):
        if len(lhs) != len(rhs):
            return False
        for lhs_value in lhs:
            if lhs_value not in rhs:
                return False
        return True

    def _com(self, lhs, rhs):
        if lhs is None:
            return rhs is None
        if isinstance(lhs, dict):
            if not isinstance(rhs, dict):
                return False
            return self._com_dict(lhs, rhs)
        if isinstance(lhs, list):
            if not isinstance(rhs, list):
                return False
            return self._com_list(lhs, rhs)
        if isinstance(lhs, tuple):
            if not isinstance(rhs, tuple):
                return False
            return self._com_list(lhs, rhs)
        return lhs == rhs

    def equals(self, rhs):
        if self.client:
            rhs = self.client.deserialize(rhs, 200)
        return self._com(self.lhs, rhs)

    def __repr__(self):
        if self.client:
            return self.client.serialize(self.lhs)
        return str(self.lhs)


class CLITestV20Base(testtools.TestCase):

    format = 'json'
    test_id = 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa'
    id_field = 'id'

    def _find_resourceid(self, client, resource, name_or_id):
        return name_or_id

    def _get_attr_metadata(self):
        return self.metadata
        client.Client.EXTED_PLURALS.update(constants.PLURALS)
        client.Client.EXTED_PLURALS.update({'tags': 'tag'})
        return {'plurals': client.Client.EXTED_PLURALS,
                'xmlns': constants.XML_NS_V20,
                constants.EXT_NS: {'prefix': 'http://xxxx.yy.com'}}

    def setUp(self, plurals={}):
        """Prepare the test environment."""
        super(CLITestV20Base, self).setUp()
        client.Client.EXTED_PLURALS.update(constants.PLURALS)
        client.Client.EXTED_PLURALS.update(plurals)
        self.metadata = {'plurals': client.Client.EXTED_PLURALS,
                         'xmlns': constants.XML_NS_V20,
                         constants.EXT_NS: {'prefix':
                                            'http://xxxx.yy.com'}}
        self.mox = mox.Mox()
        self.endurl = ENDURL
        self.fake_stdout = FakeStdout()
        self.useFixture(fixtures.MonkeyPatch('sys.stdout', self.fake_stdout))
        self.useFixture(fixtures.MonkeyPatch(
            'neutronclient.neutron.v2_0.find_resourceid_by_name_or_id',
            self._find_resourceid))
        self.useFixture(fixtures.MonkeyPatch(
            'neutronclient.neutron.v2_0.find_resourceid_by_id',
            self._find_resourceid))
        self.useFixture(fixtures.MonkeyPatch(
            'neutronclient.v2_0.client.Client.get_attr_metadata',
            self._get_attr_metadata))
        self.client = client.Client(token=TOKEN, endpoint_url=self.endurl)

    def _test_create_resource(self, resource, cmd,
                              name, myid, args,
                              position_names, position_values, tenant_id=None,
                              tags=None, admin_state_up=True, extra_body=None,
                              **kwargs):
        self.mox.StubOutWithMock(cmd, "get_client")
        self.mox.StubOutWithMock(self.client.httpclient, "request")
        cmd.get_client().MultipleTimes().AndReturn(self.client)
        non_admin_status_resources = ['subnet', 'floatingip', 'security_group',
                                      'security_group_rule', 'qos_queue',
                                      'network_gateway', 'gateway_device',
                                      'credential', 'network_profile',
                                      'policy_profile', 'ikepolicy',
                                      'ipsecpolicy', 'metering_label',
                                      'metering_label_rule', 'net_partition']
        if (resource in non_admin_status_resources):
            body = {resource: {}, }
        else:
            body = {resource: {'admin_state_up': admin_state_up, }, }
        if tenant_id:
            body[resource].update({'tenant_id': tenant_id})
        if tags:
            body[resource].update({'tags': tags})
        if extra_body:
            body[resource].update(extra_body)
        body[resource].update(kwargs)

        for i in range(len(position_names)):
            body[resource].update({position_names[i]: position_values[i]})
        ress = {resource:
                {self.id_field: myid}, }
        if name:
            ress[resource].update({'name': name})
        self.client.format = self.format
        resstr = self.client.serialize(ress)
        # url method body
        resource_plural = neutronV2_0._get_resource_plural(resource,
                                                           self.client)
        path = getattr(self.client, resource_plural + "_path")
        # Work around for LP #1217791. XML deserializer called from
        # MyComparator does not decodes XML string correctly.
        if self.format == 'json':
            mox_body = MyComparator(body, self.client)
        else:
            mox_body = self.client.serialize(body)
        self.client.httpclient.request(
            end_url(path, format=self.format), 'POST',
            body=mox_body,
            headers=mox.ContainsKeyValue(
                'X-Auth-Token', TOKEN)).AndReturn((MyResp(200), resstr))
        args.extend(['--request-format', self.format])
        self.mox.ReplayAll()
        cmd_parser = cmd.get_parser('create_' + resource)
        shell.run_command(cmd, cmd_parser, args)
        self.mox.VerifyAll()
        self.mox.UnsetStubs()
        _str = self.fake_stdout.make_string()
        self.assertIn(myid, _str)
        if name:
            self.assertIn(name, _str)

    def _test_list_columns(self, cmd, resources_collection,
                           resources_out, args=['-f', 'json']):
        self.mox.StubOutWithMock(cmd, "get_client")
        self.mox.StubOutWithMock(self.client.httpclient, "request")
        cmd.get_client().MultipleTimes().AndReturn(self.client)
        self.client.format = self.format
        resstr = self.client.serialize(resources_out)

        path = getattr(self.client, resources_collection + "_path")
        self.client.httpclient.request(
            end_url(path, format=self.format), 'GET',
            body=None,
            headers=mox.ContainsKeyValue(
                'X-Auth-Token', TOKEN)).AndReturn((MyResp(200), resstr))
        args.extend(['--request-format', self.format])
        self.mox.ReplayAll()
        cmd_parser = cmd.get_parser("list_" + resources_collection)
        shell.run_command(cmd, cmd_parser, args)
        self.mox.VerifyAll()
        self.mox.UnsetStubs()

    def _test_list_resources(self, resources, cmd, detail=False, tags=[],
                             fields_1=[], fields_2=[], page_size=None,
                             sort_key=[], sort_dir=[], response_contents=None,
                             base_args=None, path=None):
        self.mox.StubOutWithMock(cmd, "get_client")
        self.mox.StubOutWithMock(self.client.httpclient, "request")
        cmd.get_client().MultipleTimes().AndReturn(self.client)
        if response_contents is None:
            contents = [{self.id_field: 'myid1', },
                        {self.id_field: 'myid2', }, ]
        else:
            contents = response_contents
        reses = {resources: contents}
        self.client.format = self.format
        resstr = self.client.serialize(reses)
        # url method body
        query = ""
        args = base_args if base_args is not None else []
        if detail:
            args.append('-D')
        args.extend(['--request-format', self.format])
        if fields_1:
            for field in fields_1:
                args.append('--fields')
                args.append(field)

        if tags:
            args.append('--')
            args.append("--tag")
        for tag in tags:
            args.append(tag)
            if isinstance(tag, unicode):
                tag = urllib.quote(tag.encode('utf-8'))
            if query:
                query += "&tag=" + tag
            else:
                query = "tag=" + tag
        if (not tags) and fields_2:
            args.append('--')
        if fields_2:
            args.append("--fields")
            for field in fields_2:
                args.append(field)
        if detail:
            query = query and query + '&verbose=True' or 'verbose=True'
        fields_1.extend(fields_2)
        for field in fields_1:
            if query:
                query += "&fields=" + field
            else:
                query = "fields=" + field
        if page_size:
            args.append("--page-size")
            args.append(str(page_size))
            if query:
                query += "&limit=%s" % page_size
            else:
                query = "limit=%s" % page_size
        if sort_key:
            for key in sort_key:
                args.append('--sort-key')
                args.append(key)
                if query:
                    query += '&'
                query += 'sort_key=%s' % key
        if sort_dir:
            len_diff = len(sort_key) - len(sort_dir)
            if len_diff > 0:
                sort_dir += ['asc'] * len_diff
            elif len_diff < 0:
                sort_dir = sort_dir[:len(sort_key)]
            for dir in sort_dir:
                args.append('--sort-dir')
                args.append(dir)
                if query:
                    query += '&'
                query += 'sort_dir=%s' % dir
        if path is None:
            path = getattr(self.client, resources + "_path")
        self.client.httpclient.request(
            MyUrlComparator(end_url(path, query, format=self.format),
                            self.client),
            'GET',
            body=None,
            headers=mox.ContainsKeyValue(
                'X-Auth-Token', TOKEN)).AndReturn((MyResp(200), resstr))
        self.mox.ReplayAll()
        cmd_parser = cmd.get_parser("list_" + resources)
        shell.run_command(cmd, cmd_parser, args)
        self.mox.VerifyAll()
        self.mox.UnsetStubs()
        _str = self.fake_stdout.make_string()
        if response_contents is None:
            self.assertIn('myid1', _str)
        return _str

    def _test_list_resources_with_pagination(self, resources, cmd):
        self.mox.StubOutWithMock(cmd, "get_client")
        self.mox.StubOutWithMock(self.client.httpclient, "request")
        cmd.get_client().MultipleTimes().AndReturn(self.client)
        path = getattr(self.client, resources + "_path")
        fake_query = "marker=myid2&limit=2"
        reses1 = {resources: [{'id': 'myid1', },
                              {'id': 'myid2', }],
                  '%s_links' % resources: [{'href': end_url(path, fake_query),
                                            'rel': 'next'}]}
        reses2 = {resources: [{'id': 'myid3', },
                              {'id': 'myid4', }]}
        self.client.format = self.format
        resstr1 = self.client.serialize(reses1)
        resstr2 = self.client.serialize(reses2)
        self.client.httpclient.request(
            end_url(path, "", format=self.format), 'GET',
            body=None,
            headers=mox.ContainsKeyValue(
                'X-Auth-Token', TOKEN)).AndReturn((MyResp(200), resstr1))
        self.client.httpclient.request(
            end_url(path, fake_query, format=self.format), 'GET',
            body=None,
            headers=mox.ContainsKeyValue(
                'X-Auth-Token', TOKEN)).AndReturn((MyResp(200), resstr2))
        self.mox.ReplayAll()
        cmd_parser = cmd.get_parser("list_" + resources)
        args = ['--request-format', self.format]
        shell.run_command(cmd, cmd_parser, args)
        self.mox.VerifyAll()
        self.mox.UnsetStubs()

    def _test_update_resource(self, resource, cmd, myid, args, extrafields):
        self.mox.StubOutWithMock(cmd, "get_client")
        self.mox.StubOutWithMock(self.client.httpclient, "request")
        cmd.get_client().MultipleTimes().AndReturn(self.client)
        body = {resource: extrafields}
        path = getattr(self.client, resource + "_path")
        self.client.format = self.format
        # Work around for LP #1217791. XML deserializer called from
        # MyComparator does not decodes XML string correctly.
        if self.format == 'json':
            mox_body = MyComparator(body, self.client)
        else:
            mox_body = self.client.serialize(body)
        self.client.httpclient.request(
            MyUrlComparator(end_url(path % myid, format=self.format),
                            self.client),
            'PUT',
            body=mox_body,
            headers=mox.ContainsKeyValue(
                'X-Auth-Token', TOKEN)).AndReturn((MyResp(204), None))
        args.extend(['--request-format', self.format])
        self.mox.ReplayAll()
        cmd_parser = cmd.get_parser("update_" + resource)
        shell.run_command(cmd, cmd_parser, args)
        self.mox.VerifyAll()
        self.mox.UnsetStubs()
        _str = self.fake_stdout.make_string()
        self.assertIn(myid, _str)

    def _test_show_resource(self, resource, cmd, myid, args, fields=[]):
        self.mox.StubOutWithMock(cmd, "get_client")
        self.mox.StubOutWithMock(self.client.httpclient, "request")
        cmd.get_client().MultipleTimes().AndReturn(self.client)
        query = "&".join(["fields=%s" % field for field in fields])
        expected_res = {resource:
                        {self.id_field: myid,
                         'name': 'myname', }, }
        self.client.format = self.format
        resstr = self.client.serialize(expected_res)
        path = getattr(self.client, resource + "_path")
        self.client.httpclient.request(
            end_url(path % myid, query, format=self.format), 'GET',
            body=None,
            headers=mox.ContainsKeyValue(
                'X-Auth-Token', TOKEN)).AndReturn((MyResp(200), resstr))
        args.extend(['--request-format', self.format])
        self.mox.ReplayAll()
        cmd_parser = cmd.get_parser("show_" + resource)
        shell.run_command(cmd, cmd_parser, args)
        self.mox.VerifyAll()
        self.mox.UnsetStubs()
        _str = self.fake_stdout.make_string()
        self.assertIn(myid, _str)
        self.assertIn('myname', _str)

    def _test_delete_resource(self, resource, cmd, myid, args):
        self.mox.StubOutWithMock(cmd, "get_client")
        self.mox.StubOutWithMock(self.client.httpclient, "request")
        cmd.get_client().MultipleTimes().AndReturn(self.client)
        path = getattr(self.client, resource + "_path")
        self.client.httpclient.request(
            end_url(path % myid, format=self.format), 'DELETE',
            body=None,
            headers=mox.ContainsKeyValue(
                'X-Auth-Token', TOKEN)).AndReturn((MyResp(204), None))
        args.extend(['--request-format', self.format])
        self.mox.ReplayAll()
        cmd_parser = cmd.get_parser("delete_" + resource)
        shell.run_command(cmd, cmd_parser, args)
        self.mox.VerifyAll()
        self.mox.UnsetStubs()
        _str = self.fake_stdout.make_string()
        self.assertIn(myid, _str)

    def _test_update_resource_action(self, resource, cmd, myid, action, args,
                                     body, retval=None):
        self.mox.StubOutWithMock(cmd, "get_client")
        self.mox.StubOutWithMock(self.client.httpclient, "request")
        cmd.get_client().MultipleTimes().AndReturn(self.client)
        path = getattr(self.client, resource + "_path")
        path_action = '%s/%s' % (myid, action)
        self.client.httpclient.request(
            end_url(path % path_action, format=self.format), 'PUT',
            body=MyComparator(body, self.client),
            headers=mox.ContainsKeyValue(
                'X-Auth-Token', TOKEN)).AndReturn((MyResp(204), retval))
        args.extend(['--request-format', self.format])
        self.mox.ReplayAll()
        cmd_parser = cmd.get_parser("delete_" + resource)
        shell.run_command(cmd, cmd_parser, args)
        self.mox.VerifyAll()
        self.mox.UnsetStubs()
        _str = self.fake_stdout.make_string()
        self.assertIn(myid, _str)


class ClientV2TestJson(CLITestV20Base):
    def test_do_request_unicode(self):
        self.client.format = self.format
        self.mox.StubOutWithMock(self.client.httpclient, "request")
        unicode_text = u'\u7f51\u7edc'
        # url with unicode
        action = u'/test'
        expected_action = action.encode('utf-8')
        # query string with unicode
        params = {'test': unicode_text}
        expect_query = urllib.urlencode({'test':
                                         unicode_text.encode('utf-8')})
        # request body with unicode
        body = params
        expect_body = self.client.serialize(body)
        # headers with unicode
        self.client.httpclient.auth_token = unicode_text
        expected_auth_token = unicode_text.encode('utf-8')

        self.client.httpclient.request(
            end_url(expected_action, query=expect_query, format=self.format),
            'PUT', body=expect_body,
            headers=mox.ContainsKeyValue(
                'X-Auth-Token',
                expected_auth_token)).AndReturn((MyResp(200), expect_body))

        self.mox.ReplayAll()
        res_body = self.client.do_request('PUT', action, body=body,
                                          params=params)
        self.mox.VerifyAll()
        self.mox.UnsetStubs()

        # test response with unicode
        self.assertEqual(res_body, body)

    def test_do_request_error_without_response_body(self):
        self.client.format = self.format
        self.mox.StubOutWithMock(self.client.httpclient, "request")
        params = {'test': 'value'}
        expect_query = urllib.urlencode(params)
        self.client.httpclient.auth_token = 'token'

        self.client.httpclient.request(
            end_url('/test', query=expect_query, format=self.format),
            'PUT', body='',
            headers=mox.ContainsKeyValue('X-Auth-Token', 'token')
        ).AndReturn((MyResp(400, reason='An error'), ''))

        self.mox.ReplayAll()
        error = self.assertRaises(exceptions.NeutronClientException,
                                  self.client.do_request, 'PUT', '/test',
                                  body='', params=params)
        self.assertEqual("An error", str(error))
        self.mox.VerifyAll()
        self.mox.UnsetStubs()


class ClientV2UnicodeTestXML(ClientV2TestJson):
    format = 'xml'


class CLITestV20ExceptionHandler(CLITestV20Base):

    def _test_exception_handler_v20(
        self, expected_exception, status_code, expected_msg,
        error_type=None, error_msg=None, error_detail=None,
        error_content=None):
        if error_content is None:
            error_content = {'NeutronError': {'type': error_type,
                                              'message': error_msg,
                                              'detail': error_detail}}

        e = self.assertRaises(expected_exception,
                              client.exception_handler_v20,
                              status_code, error_content)
        self.assertEqual(status_code, e.status_code)

        if expected_msg is None:
            if error_detail:
                expected_msg = '\n'.join([error_msg, error_detail])
            else:
                expected_msg = error_msg
        self.assertEqual(expected_msg, e.message)

    def test_exception_handler_v20_ip_address_in_use(self):
        err_msg = ('Unable to complete operation for network '
                   'fake-network-uuid. The IP address fake-ip is in use.')
        self._test_exception_handler_v20(
            exceptions.IpAddressInUseClient, 409, err_msg,
            'IpAddressInUse', err_msg, '')

    def test_exception_handler_v20_neutron_known_error(self):
        known_error_map = [
            ('NetworkNotFound', exceptions.NetworkNotFoundClient, 404),
            ('PortNotFound', exceptions.PortNotFoundClient, 404),
            ('NetworkInUse', exceptions.NetworkInUseClient, 409),
            ('PortInUse', exceptions.PortInUseClient, 409),
            ('StateInvalid', exceptions.StateInvalidClient, 400),
            ('IpAddressInUse', exceptions.IpAddressInUseClient, 409),
            ('IpAddressGenerationFailure',
             exceptions.IpAddressGenerationFailureClient, 409),
            ('ExternalIpAddressExhausted',
             exceptions.ExternalIpAddressExhaustedClient, 400),
        ]

        error_msg = 'dummy exception message'
        error_detail = 'sample detail'
        for server_exc, client_exc, status_code in known_error_map:
            self._test_exception_handler_v20(
                client_exc, status_code,
                error_msg + '\n' + error_detail,
                server_exc, error_msg, error_detail)

    def test_exception_handler_v20_neutron_known_error_without_detail(self):
        error_msg = 'Network not found'
        error_detail = ''
        self._test_exception_handler_v20(
            exceptions.NetworkNotFoundClient, 404,
            error_msg,
            'NetworkNotFound', error_msg, error_detail)

    def test_exception_handler_v20_unknown_error_to_per_code_exception(self):
        for status_code, client_exc in exceptions.HTTP_EXCEPTION_MAP.items():
            error_msg = 'Unknown error'
            error_detail = 'This is detail'
            self._test_exception_handler_v20(
                client_exc, status_code,
                error_msg + '\n' + error_detail,
                'UnknownError', error_msg, error_detail)

    def test_exception_handler_v20_neutron_unknown_status_code(self):
        error_msg = 'Unknown error'
        error_detail = 'This is detail'
        self._test_exception_handler_v20(
            exceptions.NeutronClientException, 501,
            error_msg + '\n' + error_detail,
            'UnknownError', error_msg, error_detail)

    def test_exception_handler_v20_bad_neutron_error(self):
        error_content = {'NeutronError': {'unknown_key': 'UNKNOWN'}}
        self._test_exception_handler_v20(
            exceptions.NeutronClientException, 500,
            expected_msg={'unknown_key': 'UNKNOWN'},
            error_content=error_content)

    def test_exception_handler_v20_error_dict_contains_message(self):
        error_content = {'message': 'This is an error message'}
        self._test_exception_handler_v20(
            exceptions.NeutronClientException, 500,
            expected_msg='This is an error message',
            error_content=error_content)

    def test_exception_handler_v20_error_dict_not_contain_message(self):
        error_content = {'error': 'This is an error message'}
        expected_msg = '%s-%s' % (500, error_content)
        self._test_exception_handler_v20(
            exceptions.NeutronClientException, 500,
            expected_msg=expected_msg,
            error_content=error_content)

    def test_exception_handler_v20_default_fallback(self):
        error_content = 'This is an error message'
        expected_msg = '%s-%s' % (500, error_content)
        self._test_exception_handler_v20(
            exceptions.NeutronClientException, 500,
            expected_msg=expected_msg,
            error_content=error_content)

########NEW FILE########
__FILENAME__ = test_cli20_agenschedulers
# Copyright 2013 Mirantis Inc.
# All Rights Reserved
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.
#
# @author: Oleg Bondarev, Mirantis Inc.
#

import sys

from neutronclient.neutron.v2_0 import agentscheduler
from neutronclient.tests.unit import test_cli20


class CLITestV20LBaaSAgentScheduler(test_cli20.CLITestV20Base):

    def test_list_pools_on_agent(self):
        resources = 'pools'
        cmd = agentscheduler.ListPoolsOnLbaasAgent(
            test_cli20.MyApp(sys.stdout), None)
        agent_id = 'agent_id1'
        path = ((self.client.agent_path + self.client.LOADBALANCER_POOLS) %
                agent_id)
        self._test_list_resources(resources, cmd, base_args=[agent_id],
                                  path=path)

    def test_get_lbaas_agent_hosting_pool(self):
        resources = 'agent'
        cmd = agentscheduler.GetLbaasAgentHostingPool(
            test_cli20.MyApp(sys.stdout), None)
        pool_id = 'pool_id1'
        path = ((self.client.pool_path + self.client.LOADBALANCER_AGENT) %
                pool_id)
        contents = {self.id_field: 'myid1', 'alive': True}
        self._test_list_resources(resources, cmd, base_args=[pool_id],
                                  path=path, response_contents=contents)


class CLITestV20LBaaSAgentSchedulerXML(CLITestV20LBaaSAgentScheduler):
    format = 'xml'

########NEW FILE########
__FILENAME__ = test_cli20_agents
# All Rights Reserved
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.
#
# vim: tabstop=4 shiftwidth=4 softtabstop=4

import sys

from neutronclient.common import utils
from neutronclient.neutron.v2_0 import agent
from neutronclient.tests.unit import test_cli20


class CLITestV20Agent(test_cli20.CLITestV20Base):
    def test_list_agents(self):
        contents = {'agents': [{'id': 'myname', 'agent_type': 'mytype',
                                'alive': True}]}
        args = ['-f', 'json']
        resources = "agents"

        cmd = agent.ListAgent(test_cli20.MyApp(sys.stdout), None)
        self._test_list_columns(cmd, resources, contents, args)
        _str = self.fake_stdout.make_string()

        returned_agents = utils.loads(_str)
        self.assertEqual(1, len(returned_agents))
        ag = returned_agents[0]
        self.assertEqual(3, len(ag))
        self.assertEqual("alive", ag.keys()[2])

    def test_list_agents_field(self):
        contents = {'agents': [{'alive': True}]}
        args = ['-f', 'json']
        resources = "agents"
        smile = ':-)'

        cmd = agent.ListAgent(test_cli20.MyApp(sys.stdout), None)
        self._test_list_columns(cmd, resources, contents, args)
        _str = self.fake_stdout.make_string()

        returned_agents = utils.loads(_str)
        self.assertEqual(1, len(returned_agents))
        ag = returned_agents[0]
        self.assertEqual(1, len(ag))
        self.assertEqual("alive", ag.keys()[0])
        self.assertEqual(smile, ag.values()[0])

########NEW FILE########
__FILENAME__ = test_cli20_credential
# Copyright 2013 Cisco Systems Inc.
# All Rights Reserved
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.
#
# @author: Kyle Mestery, Cisco Systems, Inc.
#

import sys

from neutronclient.neutron.v2_0 import credential
from neutronclient.tests.unit import test_cli20


class CLITestV20Credential(test_cli20.CLITestV20Base):

    def test_create_credential(self):
        """Create credential: myid."""
        resource = 'credential'
        cmd = credential.CreateCredential(test_cli20.MyApp(sys.stdout), None)
        name = 'myname'
        myid = 'myid'
        type = 'mytype'
        args = [name, type]
        position_names = ['credential_name', 'type']
        position_values = [name, type]
        self._test_create_resource(resource, cmd, name, myid, args,
                                   position_names, position_values)

    def test_list_credentials_detail(self):
        """List credentials: -D."""
        resources = 'credentials'
        cmd = credential.ListCredential(test_cli20.MyApp(sys.stdout), None)
        contents = [{'credential_name': 'myname', 'type': 'mytype'}]
        self._test_list_resources(resources, cmd, True,
                                  response_contents=contents)

    def test_list_credential_known_option_after_unknown(self):
        """List credential: -- --tags a b --request-format xml."""
        resources = 'credentials'
        cmd = credential.ListCredential(test_cli20.MyApp(sys.stdout), None)
        contents = [{'credential_name': 'myname', 'type': 'mytype'}]
        self._test_list_resources(resources, cmd, tags=['a', 'b'],
                                  response_contents=contents)

    def test_list_credential_fields(self):
        """List credential: --fields a --fields b -- --fields c d."""
        resources = 'credentials'
        cmd = credential.ListCredential(test_cli20.MyApp(sys.stdout), None)
        contents = [{'credential_name': 'myname', 'type': 'mytype'}]
        self._test_list_resources(resources, cmd,
                                  fields_1=['a', 'b'], fields_2=['c', 'd'],
                                  response_contents=contents)

    def test_show_credential(self):
        """Show credential: --fields id --fields name myid."""
        resource = 'credential'
        cmd = credential.ShowCredential(test_cli20.MyApp(sys.stdout), None)
        args = ['--fields', 'id', '--fields', 'name', self.test_id]
        self._test_show_resource(resource, cmd, self.test_id, args,
                                 ['id', 'name'])

    def test_delete_credential(self):
        """Delete credential: myid."""
        resource = 'credential'
        cmd = credential.DeleteCredential(test_cli20.MyApp(sys.stdout), None)
        myid = 'myid'
        args = [myid]
        self._test_delete_resource(resource, cmd, myid, args)

########NEW FILE########
__FILENAME__ = test_cli20_extensions
# Copyright 2013 NEC Corporation
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import sys

from neutronclient.neutron.v2_0.extension import ListExt
from neutronclient.neutron.v2_0.extension import ShowExt
from neutronclient.tests.unit.test_cli20 import CLITestV20Base
from neutronclient.tests.unit.test_cli20 import MyApp


class CLITestV20Extension(CLITestV20Base):
    id_field = 'alias'

    def test_list_extensions(self):
        resources = 'extensions'
        cmd = ListExt(MyApp(sys.stdout), None)
        contents = [{'alias': 'ext1', 'name': 'name1', 'other': 'other1'},
                    {'alias': 'ext2', 'name': 'name2', 'other': 'other2'}]
        ret = self._test_list_resources(resources, cmd,
                                        response_contents=contents)
        ret_words = set(ret.split())
        # Check only the default columns are shown.
        self.assertIn('name', ret_words)
        self.assertIn('alias', ret_words)
        self.assertNotIn('other', ret_words)

    def test_show_extension(self):
        # -F option does not work for ext-show at the moment, so -F option
        # is not passed in the commandline args as other tests do.
        resource = 'extension'
        cmd = ShowExt(MyApp(sys.stdout), None)
        args = [self.test_id]
        ext_alias = self.test_id
        self._test_show_resource(resource, cmd, ext_alias, args, fields=[])

########NEW FILE########
__FILENAME__ = test_cli20_floatingips
#!/usr/bin/env python
# Copyright 2012 Red Hat
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import sys

from neutronclient.neutron.v2_0 import floatingip as fip
from neutronclient.tests.unit import test_cli20


class CLITestV20FloatingIpsJSON(test_cli20.CLITestV20Base):
    def test_create_floatingip(self):
        """Create floatingip: fip1."""
        resource = 'floatingip'
        cmd = fip.CreateFloatingIP(test_cli20.MyApp(sys.stdout), None)
        name = 'fip1'
        myid = 'myid'
        args = [name]
        position_names = ['floating_network_id']
        position_values = [name]
        self._test_create_resource(resource, cmd, name, myid, args,
                                   position_names, position_values)

    def test_create_floatingip_and_port(self):
        """Create floatingip: fip1."""
        resource = 'floatingip'
        cmd = fip.CreateFloatingIP(test_cli20.MyApp(sys.stdout), None)
        name = 'fip1'
        myid = 'myid'
        pid = 'mypid'
        args = [name, '--port_id', pid]
        position_names = ['floating_network_id', 'port_id']
        position_values = [name, pid]
        self._test_create_resource(resource, cmd, name, myid, args,
                                   position_names, position_values)

        # Test dashed options
        args = [name, '--port-id', pid]
        position_names = ['floating_network_id', 'port_id']
        self._test_create_resource(resource, cmd, name, myid, args,
                                   position_names, position_values)

    def test_create_floatingip_and_port_and_address(self):
        """Create floatingip: fip1 with a given port and address."""
        resource = 'floatingip'
        cmd = fip.CreateFloatingIP(test_cli20.MyApp(sys.stdout), None)
        name = 'fip1'
        myid = 'myid'
        pid = 'mypid'
        addr = '10.0.0.99'
        args = [name, '--port_id', pid, '--fixed_ip_address', addr]
        position_names = ['floating_network_id', 'port_id', 'fixed_ip_address']
        position_values = [name, pid, addr]
        self._test_create_resource(resource, cmd, name, myid, args,
                                   position_names, position_values)
        # Test dashed options
        args = [name, '--port-id', pid, '--fixed-ip-address', addr]
        position_names = ['floating_network_id', 'port_id', 'fixed_ip_address']
        self._test_create_resource(resource, cmd, name, myid, args,
                                   position_names, position_values)

    def test_list_floatingips(self):
        """list floatingips: -D."""
        resources = 'floatingips'
        cmd = fip.ListFloatingIP(test_cli20.MyApp(sys.stdout), None)
        self._test_list_resources(resources, cmd, True)

    def test_list_floatingips_pagination(self):
        resources = 'floatingips'
        cmd = fip.ListFloatingIP(test_cli20.MyApp(sys.stdout), None)
        self._test_list_resources_with_pagination(resources, cmd)

    def test_list_floatingips_sort(self):
        """list floatingips: --sort-key name --sort-key id --sort-key asc
        --sort-key desc
        """
        resources = 'floatingips'
        cmd = fip.ListFloatingIP(test_cli20.MyApp(sys.stdout), None)
        self._test_list_resources(resources, cmd,
                                  sort_key=["name", "id"],
                                  sort_dir=["asc", "desc"])

    def test_list_floatingips_limit(self):
        """list floatingips: -P."""
        resources = 'floatingips'
        cmd = fip.ListFloatingIP(test_cli20.MyApp(sys.stdout), None)
        self._test_list_resources(resources, cmd, page_size=1000)

    def test_delete_floatingip(self):
        """Delete floatingip: fip1."""
        resource = 'floatingip'
        cmd = fip.DeleteFloatingIP(test_cli20.MyApp(sys.stdout), None)
        myid = 'myid'
        args = [myid]
        self._test_delete_resource(resource, cmd, myid, args)

    def test_show_floatingip(self):
        """Show floatingip: --fields id."""
        resource = 'floatingip'
        cmd = fip.ShowFloatingIP(test_cli20.MyApp(sys.stdout), None)
        args = ['--fields', 'id', self.test_id]
        self._test_show_resource(resource, cmd, self.test_id,
                                 args, ['id'])

    def test_disassociate_ip(self):
        """Disassociate floating IP: myid."""
        resource = 'floatingip'
        cmd = fip.DisassociateFloatingIP(test_cli20.MyApp(sys.stdout), None)
        args = ['myid']
        self._test_update_resource(resource, cmd, 'myid',
                                   args, {"port_id": None}
                                   )

    def test_associate_ip(self):
        """Associate floating IP: myid portid."""
        resource = 'floatingip'
        cmd = fip.AssociateFloatingIP(test_cli20.MyApp(sys.stdout), None)
        args = ['myid', 'portid']
        self._test_update_resource(resource, cmd, 'myid',
                                   args, {"port_id": "portid"}
                                   )


class CLITestV20FloatingIpsXML(CLITestV20FloatingIpsJSON):
    format = 'xml'

########NEW FILE########
__FILENAME__ = test_cli20_metering
# Copyright (C) 2013 eNovance SAS <licensing@enovance.com>
#
# Author: Sylvain Afchain <sylvain.afchain@enovance.com>
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import sys

from neutronclient.neutron.v2_0 import metering
from neutronclient.tests.unit import test_cli20


class CLITestV20MeteringJSON(test_cli20.CLITestV20Base):
    def test_create_metering_label(self):
        """Create a metering label."""
        resource = 'metering_label'
        cmd = metering.CreateMeteringLabel(
            test_cli20.MyApp(sys.stdout), None)
        name = 'my label'
        myid = 'myid'
        description = 'my description'
        args = [name, '--description', description, '--shared']
        position_names = ['name', 'description', 'shared']
        position_values = [name, description, True]
        self._test_create_resource(resource, cmd, name, myid, args,
                                   position_names, position_values)

    def test_list_metering_labels(self):
        resources = "metering_labels"
        cmd = metering.ListMeteringLabel(
            test_cli20.MyApp(sys.stdout), None)
        self._test_list_resources(resources, cmd)

    def test_delete_metering_label(self):
        """Delete a metering label."""
        resource = 'metering_label'
        cmd = metering.DeleteMeteringLabel(
            test_cli20.MyApp(sys.stdout), None)
        myid = 'myid'
        args = [myid]
        self._test_delete_resource(resource, cmd, myid, args)

    def test_show_metering_label(self):
        resource = 'metering_label'
        cmd = metering.ShowMeteringLabel(
            test_cli20.MyApp(sys.stdout), None)
        args = ['--fields', 'id', self.test_id]
        self._test_show_resource(resource, cmd, self.test_id,
                                 args, ['id'])

    def test_create_metering_label_rule(self):
        resource = 'metering_label_rule'
        cmd = metering.CreateMeteringLabelRule(
            test_cli20.MyApp(sys.stdout), None)
        myid = 'myid'
        metering_label_id = 'aaa'
        remote_ip_prefix = '10.0.0.0/24'
        direction = 'ingress'
        args = [metering_label_id, remote_ip_prefix, '--direction', direction,
                '--excluded']
        position_names = ['metering_label_id', 'remote_ip_prefix', 'direction',
                          'excluded']
        position_values = [metering_label_id, remote_ip_prefix,
                           direction, True]
        self._test_create_resource(resource, cmd, metering_label_id,
                                   myid, args, position_names, position_values)

    def test_list_metering_label_rules(self):
        resources = "metering_label_rules"
        cmd = metering.ListMeteringLabelRule(
            test_cli20.MyApp(sys.stdout), None)
        self._test_list_resources(resources, cmd)

    def test_delete_metering_label_rule(self):
        resource = 'metering_label_rule'
        cmd = metering.DeleteMeteringLabelRule(
            test_cli20.MyApp(sys.stdout), None)
        myid = 'myid'
        args = [myid]
        self._test_delete_resource(resource, cmd, myid, args)

    def test_show_metering_label_rule(self):
        resource = 'metering_label_rule'
        cmd = metering.ShowMeteringLabelRule(
            test_cli20.MyApp(sys.stdout), None)
        args = ['--fields', 'id', self.test_id]
        self._test_show_resource(resource, cmd, self.test_id,
                                 args, ['id'])


class CLITestV20MeteringXML(CLITestV20MeteringJSON):
    format = 'xml'

########NEW FILE########
__FILENAME__ = test_cli20_network
# All Rights Reserved
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.
#

import sys

import mox

from neutronclient.common import exceptions
from neutronclient.common import utils
from neutronclient.neutron.v2_0 import network
from neutronclient import shell
from neutronclient.tests.unit import test_cli20


class CLITestV20NetworkJSON(test_cli20.CLITestV20Base):
    def setUp(self):
        super(CLITestV20NetworkJSON, self).setUp(plurals={'tags': 'tag'})

    def test_create_network(self):
        """Create net: myname."""
        resource = 'network'
        cmd = network.CreateNetwork(test_cli20.MyApp(sys.stdout), None)
        name = 'myname'
        myid = 'myid'
        args = [name, ]
        position_names = ['name', ]
        position_values = [name, ]
        self._test_create_resource(resource, cmd, name, myid, args,
                                   position_names, position_values)

    def test_create_network_with_unicode(self):
        """Create net: u'\u7f51\u7edc'."""
        resource = 'network'
        cmd = network.CreateNetwork(test_cli20.MyApp(sys.stdout), None)
        name = u'\u7f51\u7edc'
        myid = 'myid'
        args = [name, ]
        position_names = ['name', ]
        position_values = [name, ]
        self._test_create_resource(resource, cmd, name, myid, args,
                                   position_names, position_values)

    def test_create_network_tenant(self):
        """Create net: --tenant_id tenantid myname."""
        resource = 'network'
        cmd = network.CreateNetwork(test_cli20.MyApp(sys.stdout), None)
        name = 'myname'
        myid = 'myid'
        args = ['--tenant_id', 'tenantid', name]
        position_names = ['name', ]
        position_values = [name, ]
        self._test_create_resource(resource, cmd, name, myid, args,
                                   position_names, position_values,
                                   tenant_id='tenantid')

        # Test dashed options
        args = ['--tenant-id', 'tenantid', name]
        self._test_create_resource(resource, cmd, name, myid, args,
                                   position_names, position_values,
                                   tenant_id='tenantid')

    def test_create_network_tags(self):
        """Create net: myname --tags a b."""
        resource = 'network'
        cmd = network.CreateNetwork(test_cli20.MyApp(sys.stdout), None)
        name = 'myname'
        myid = 'myid'
        args = [name, '--tags', 'a', 'b']
        position_names = ['name', ]
        position_values = [name, ]
        self._test_create_resource(resource, cmd, name, myid, args,
                                   position_names, position_values,
                                   tags=['a', 'b'])

    def test_create_network_state(self):
        """Create net: --admin_state_down myname."""
        resource = 'network'
        cmd = network.CreateNetwork(test_cli20.MyApp(sys.stdout), None)
        name = 'myname'
        myid = 'myid'
        args = ['--admin_state_down', name, ]
        position_names = ['name', ]
        position_values = [name, ]
        self._test_create_resource(resource, cmd, name, myid, args,
                                   position_names, position_values,
                                   admin_state_up=False)

        # Test dashed options
        args = ['--admin-state-down', name, ]
        self._test_create_resource(resource, cmd, name, myid, args,
                                   position_names, position_values,
                                   admin_state_up=False)

    def test_list_nets_empty_with_column(self):
        resources = "networks"
        cmd = network.ListNetwork(test_cli20.MyApp(sys.stdout), None)
        self.mox.StubOutWithMock(cmd, "get_client")
        self.mox.StubOutWithMock(self.client.httpclient, "request")
        self.mox.StubOutWithMock(network.ListNetwork, "extend_list")
        network.ListNetwork.extend_list(mox.IsA(list), mox.IgnoreArg())
        cmd.get_client().MultipleTimes().AndReturn(self.client)
        reses = {resources: []}
        resstr = self.client.serialize(reses)
        # url method body
        query = "id=myfakeid"
        args = ['-c', 'id', '--', '--id', 'myfakeid']
        path = getattr(self.client, resources + "_path")
        self.client.httpclient.request(
            test_cli20.end_url(path, query), 'GET',
            body=None,
            headers=mox.ContainsKeyValue(
                'X-Auth-Token',
                test_cli20.TOKEN)).AndReturn(
                    (test_cli20.MyResp(200), resstr))
        self.mox.ReplayAll()
        cmd_parser = cmd.get_parser("list_" + resources)
        shell.run_command(cmd, cmd_parser, args)
        self.mox.VerifyAll()
        self.mox.UnsetStubs()
        _str = self.fake_stdout.make_string()
        self.assertEqual('\n', _str)

    def _test_list_networks(self, cmd, detail=False, tags=[],
                            fields_1=[], fields_2=[], page_size=None,
                            sort_key=[], sort_dir=[]):
        resources = "networks"
        self.mox.StubOutWithMock(network.ListNetwork, "extend_list")
        network.ListNetwork.extend_list(mox.IsA(list), mox.IgnoreArg())
        self._test_list_resources(resources, cmd, detail, tags,
                                  fields_1, fields_2, page_size=page_size,
                                  sort_key=sort_key, sort_dir=sort_dir)

    def test_list_nets_pagination(self):
        cmd = network.ListNetwork(test_cli20.MyApp(sys.stdout), None)
        self.mox.StubOutWithMock(network.ListNetwork, "extend_list")
        network.ListNetwork.extend_list(mox.IsA(list), mox.IgnoreArg())
        self._test_list_resources_with_pagination("networks", cmd)

    def test_list_nets_sort(self):
        """list nets: --sort-key name --sort-key id --sort-dir asc
        --sort-dir desc
        """
        cmd = network.ListNetwork(test_cli20.MyApp(sys.stdout), None)
        self._test_list_networks(cmd, sort_key=['name', 'id'],
                                 sort_dir=['asc', 'desc'])

    def test_list_nets_sort_with_keys_more_than_dirs(self):
        """list nets: --sort-key name --sort-key id --sort-dir desc
        """
        cmd = network.ListNetwork(test_cli20.MyApp(sys.stdout), None)
        self._test_list_networks(cmd, sort_key=['name', 'id'],
                                 sort_dir=['desc'])

    def test_list_nets_sort_with_dirs_more_than_keys(self):
        """list nets: --sort-key name --sort-dir desc --sort-dir asc
        """
        cmd = network.ListNetwork(test_cli20.MyApp(sys.stdout), None)
        self._test_list_networks(cmd, sort_key=['name'],
                                 sort_dir=['desc', 'asc'])

    def test_list_nets_limit(self):
        """list nets: -P."""
        cmd = network.ListNetwork(test_cli20.MyApp(sys.stdout), None)
        self._test_list_networks(cmd, page_size=1000)

    def test_list_nets_detail(self):
        """list nets: -D."""
        cmd = network.ListNetwork(test_cli20.MyApp(sys.stdout), None)
        self._test_list_networks(cmd, True)

    def test_list_nets_tags(self):
        """List nets: -- --tags a b."""
        cmd = network.ListNetwork(test_cli20.MyApp(sys.stdout), None)
        self._test_list_networks(cmd, tags=['a', 'b'])

    def test_list_nets_tags_with_unicode(self):
        """List nets: -- --tags u'\u7f51\u7edc'."""
        cmd = network.ListNetwork(test_cli20.MyApp(sys.stdout), None)
        self._test_list_networks(cmd, tags=[u'\u7f51\u7edc'])

    def test_list_nets_detail_tags(self):
        """List nets: -D -- --tags a b."""
        cmd = network.ListNetwork(test_cli20.MyApp(sys.stdout), None)
        self._test_list_networks(cmd, detail=True, tags=['a', 'b'])

    def _test_list_nets_extend_subnets(self, data, expected):
        def setup_list_stub(resources, data, query):
            reses = {resources: data}
            resstr = self.client.serialize(reses)
            resp = (test_cli20.MyResp(200), resstr)
            path = getattr(self.client, resources + '_path')
            self.client.httpclient.request(
                test_cli20.end_url(path, query), 'GET',
                body=None,
                headers=mox.ContainsKeyValue(
                    'X-Auth-Token', test_cli20.TOKEN)).AndReturn(resp)

        cmd = network.ListNetwork(test_cli20.MyApp(sys.stdout), None)
        self.mox.StubOutWithMock(cmd, 'get_client')
        self.mox.StubOutWithMock(self.client.httpclient, 'request')
        cmd.get_client().AndReturn(self.client)
        setup_list_stub('networks', data, '')
        cmd.get_client().AndReturn(self.client)
        filters = ''
        for n in data:
            for s in n['subnets']:
                filters = filters + "&id=%s" % s
        setup_list_stub('subnets',
                        [{'id': 'mysubid1', 'cidr': '192.168.1.0/24'},
                         {'id': 'mysubid2', 'cidr': '172.16.0.0/24'},
                         {'id': 'mysubid3', 'cidr': '10.1.1.0/24'}],
                        query='fields=id&fields=cidr' + filters)
        self.mox.ReplayAll()

        args = []
        cmd_parser = cmd.get_parser('list_networks')
        parsed_args = cmd_parser.parse_args(args)
        result = cmd.get_data(parsed_args)
        self.mox.VerifyAll()
        self.mox.UnsetStubs()
        _result = [x for x in result[1]]
        self.assertEqual(len(_result), len(expected))
        for res, exp in zip(_result, expected):
            self.assertEqual(len(res), len(exp))
            for a, b in zip(res, exp):
                self.assertEqual(a, b)

    def test_list_nets_extend_subnets(self):
        data = [{'id': 'netid1', 'name': 'net1', 'subnets': ['mysubid1']},
                {'id': 'netid2', 'name': 'net2', 'subnets': ['mysubid2',
                                                             'mysubid3']}]
        #             id,   name,   subnets
        expected = [('netid1', 'net1', 'mysubid1 192.168.1.0/24'),
                    ('netid2', 'net2',
                     'mysubid2 172.16.0.0/24\nmysubid3 10.1.1.0/24')]
        self._test_list_nets_extend_subnets(data, expected)

    def test_list_nets_extend_subnets_no_subnet(self):
        data = [{'id': 'netid1', 'name': 'net1', 'subnets': ['mysubid1']},
                {'id': 'netid2', 'name': 'net2', 'subnets': ['mysubid4']}]
        #             id,   name,   subnets
        expected = [('netid1', 'net1', 'mysubid1 192.168.1.0/24'),
                    ('netid2', 'net2', 'mysubid4 ')]
        self._test_list_nets_extend_subnets(data, expected)

    def test_list_nets_fields(self):
        """List nets: --fields a --fields b -- --fields c d."""
        cmd = network.ListNetwork(test_cli20.MyApp(sys.stdout), None)
        self._test_list_networks(cmd,
                                 fields_1=['a', 'b'], fields_2=['c', 'd'])

    def _test_list_nets_columns(self, cmd, returned_body,
                                args=['-f', 'json']):
        resources = 'networks'
        self.mox.StubOutWithMock(network.ListNetwork, "extend_list")
        network.ListNetwork.extend_list(mox.IsA(list), mox.IgnoreArg())
        self._test_list_columns(cmd, resources, returned_body, args=args)

    def test_list_nets_defined_column(self):
        cmd = network.ListNetwork(test_cli20.MyApp(sys.stdout), None)
        returned_body = {"networks": [{"name": "buildname3",
                                       "id": "id3",
                                       "tenant_id": "tenant_3",
                                       "subnets": []}]}
        self._test_list_nets_columns(cmd, returned_body,
                                     args=['-f', 'json', '-c', 'id'])
        _str = self.fake_stdout.make_string()
        returned_networks = utils.loads(_str)
        self.assertEqual(1, len(returned_networks))
        net = returned_networks[0]
        self.assertEqual(1, len(net))
        self.assertEqual("id", net.keys()[0])

    def test_list_nets_with_default_column(self):
        cmd = network.ListNetwork(test_cli20.MyApp(sys.stdout), None)
        returned_body = {"networks": [{"name": "buildname3",
                                       "id": "id3",
                                       "tenant_id": "tenant_3",
                                       "subnets": []}]}
        self._test_list_nets_columns(cmd, returned_body)
        _str = self.fake_stdout.make_string()
        returned_networks = utils.loads(_str)
        self.assertEqual(1, len(returned_networks))
        net = returned_networks[0]
        self.assertEqual(3, len(net))
        self.assertEqual(0, len(set(net) ^ set(cmd.list_columns)))

    def test_list_external_nets_empty_with_column(self):
        resources = "networks"
        cmd = network.ListExternalNetwork(test_cli20.MyApp(sys.stdout), None)
        self.mox.StubOutWithMock(cmd, "get_client")
        self.mox.StubOutWithMock(self.client.httpclient, "request")
        self.mox.StubOutWithMock(network.ListNetwork, "extend_list")
        network.ListNetwork.extend_list(mox.IsA(list), mox.IgnoreArg())
        cmd.get_client().MultipleTimes().AndReturn(self.client)
        reses = {resources: []}
        resstr = self.client.serialize(reses)
        # url method body
        query = "router%3Aexternal=True&id=myfakeid"
        args = ['-c', 'id', '--', '--id', 'myfakeid']
        path = getattr(self.client, resources + "_path")
        self.client.httpclient.request(
            test_cli20.end_url(path, query), 'GET',
            body=None,
            headers=mox.ContainsKeyValue(
                'X-Auth-Token',
                test_cli20.TOKEN)).AndReturn(
                    (test_cli20.MyResp(200), resstr))
        self.mox.ReplayAll()
        cmd_parser = cmd.get_parser("list_" + resources)
        shell.run_command(cmd, cmd_parser, args)
        self.mox.VerifyAll()
        self.mox.UnsetStubs()
        _str = self.fake_stdout.make_string()
        self.assertEqual('\n', _str)

    def _test_list_external_nets(self, resources, cmd,
                                 detail=False, tags=[],
                                 fields_1=[], fields_2=[]):
        self.mox.StubOutWithMock(cmd, "get_client")
        self.mox.StubOutWithMock(self.client.httpclient, "request")
        self.mox.StubOutWithMock(network.ListNetwork, "extend_list")
        network.ListNetwork.extend_list(mox.IsA(list), mox.IgnoreArg())
        cmd.get_client().MultipleTimes().AndReturn(self.client)
        reses = {resources: [{'id': 'myid1', },
                             {'id': 'myid2', }, ], }

        resstr = self.client.serialize(reses)

        # url method body
        query = ""
        args = detail and ['-D', ] or []
        if fields_1:
            for field in fields_1:
                args.append('--fields')
                args.append(field)
        if tags:
            args.append('--')
            args.append("--tag")
        for tag in tags:
            args.append(tag)
        if (not tags) and fields_2:
            args.append('--')
        if fields_2:
            args.append("--fields")
            for field in fields_2:
                args.append(field)
        fields_1.extend(fields_2)
        for field in fields_1:
            if query:
                query += "&fields=" + field
            else:
                query = "fields=" + field
        if query:
            query += '&router%3Aexternal=True'
        else:
            query += 'router%3Aexternal=True'
        for tag in tags:
            if query:
                query += "&tag=" + tag
            else:
                query = "tag=" + tag
        if detail:
            query = query and query + '&verbose=True' or 'verbose=True'
        path = getattr(self.client, resources + "_path")

        self.client.httpclient.request(
            test_cli20.end_url(path, query), 'GET',
            body=None,
            headers=mox.ContainsKeyValue('X-Auth-Token', test_cli20.TOKEN)
        ).AndReturn((test_cli20.MyResp(200), resstr))
        self.mox.ReplayAll()
        cmd_parser = cmd.get_parser("list_" + resources)
        shell.run_command(cmd, cmd_parser, args)
        self.mox.VerifyAll()
        self.mox.UnsetStubs()
        _str = self.fake_stdout.make_string()

        self.assertIn('myid1', _str)

    def test_list_external_nets_detail(self):
        """list external nets: -D."""
        resources = "networks"
        cmd = network.ListExternalNetwork(test_cli20.MyApp(sys.stdout), None)
        self._test_list_external_nets(resources, cmd, True)

    def test_list_external_nets_tags(self):
        """List external nets: -- --tags a b."""
        resources = "networks"
        cmd = network.ListExternalNetwork(test_cli20.MyApp(sys.stdout), None)
        self._test_list_external_nets(resources,
                                      cmd, tags=['a', 'b'])

    def test_list_external_nets_detail_tags(self):
        """List external nets: -D -- --tags a b."""
        resources = "networks"
        cmd = network.ListExternalNetwork(test_cli20.MyApp(sys.stdout), None)
        self._test_list_external_nets(resources, cmd,
                                      detail=True, tags=['a', 'b'])

    def test_list_externel_nets_fields(self):
        """List external nets: --fields a --fields b -- --fields c d."""
        resources = "networks"
        cmd = network.ListExternalNetwork(test_cli20.MyApp(sys.stdout), None)
        self._test_list_external_nets(resources, cmd,
                                      fields_1=['a', 'b'],
                                      fields_2=['c', 'd'])

    def test_update_network_exception(self):
        """Update net: myid."""
        resource = 'network'
        cmd = network.UpdateNetwork(test_cli20.MyApp(sys.stdout), None)
        self.assertRaises(exceptions.CommandError, self._test_update_resource,
                          resource, cmd, 'myid', ['myid'], {})

    def test_update_network(self):
        """Update net: myid --name myname --tags a b."""
        resource = 'network'
        cmd = network.UpdateNetwork(test_cli20.MyApp(sys.stdout), None)
        self._test_update_resource(resource, cmd, 'myid',
                                   ['myid', '--name', 'myname',
                                    '--tags', 'a', 'b'],
                                   {'name': 'myname', 'tags': ['a', 'b'], }
                                   )

    def test_update_network_with_unicode(self):
        """Update net: myid --name u'\u7f51\u7edc' --tags a b."""
        resource = 'network'
        cmd = network.UpdateNetwork(test_cli20.MyApp(sys.stdout), None)
        self._test_update_resource(resource, cmd, 'myid',
                                   ['myid', '--name', u'\u7f51\u7edc',
                                    '--tags', 'a', 'b'],
                                   {'name': u'\u7f51\u7edc',
                                    'tags': ['a', 'b'], }
                                   )

    def test_show_network(self):
        """Show net: --fields id --fields name myid."""
        resource = 'network'
        cmd = network.ShowNetwork(test_cli20.MyApp(sys.stdout), None)
        args = ['--fields', 'id', '--fields', 'name', self.test_id]
        self._test_show_resource(resource, cmd, self.test_id, args,
                                 ['id', 'name'])

    def test_delete_network(self):
        """Delete net: myid."""
        resource = 'network'
        cmd = network.DeleteNetwork(test_cli20.MyApp(sys.stdout), None)
        myid = 'myid'
        args = [myid]
        self._test_delete_resource(resource, cmd, myid, args)

    def _test_extend_list(self, mox_calls):
        data = [{'id': 'netid%d' % i, 'name': 'net%d' % i,
                 'subnets': ['mysubid%d' % i]}
                for i in range(10)]
        self.mox.StubOutWithMock(self.client.httpclient, "request")
        path = getattr(self.client, 'subnets_path')
        cmd = network.ListNetwork(test_cli20.MyApp(sys.stdout), None)
        self.mox.StubOutWithMock(cmd, "get_client")
        cmd.get_client().MultipleTimes().AndReturn(self.client)
        mox_calls(path, data)
        self.mox.ReplayAll()
        known_args, _vs = cmd.get_parser('create_subnets').parse_known_args()
        cmd.extend_list(data, known_args)
        self.mox.VerifyAll()

    def _build_test_data(self, data):
        subnet_ids = []
        response = []
        filters = ""
        for n in data:
            if 'subnets' in n:
                subnet_ids.extend(n['subnets'])
                for subnet_id in n['subnets']:
                    filters = "%s&id=%s" % (filters, subnet_id)
                    response.append({'id': subnet_id,
                                     'cidr': '192.168.0.0/16'})
        resp_str = self.client.serialize({'subnets': response})
        resp = (test_cli20.MyResp(200), resp_str)
        return filters, resp

    def test_extend_list(self):
        def mox_calls(path, data):
            filters, response = self._build_test_data(data)
            self.client.httpclient.request(
                test_cli20.end_url(path, 'fields=id&fields=cidr' + filters),
                'GET',
                body=None,
                headers=mox.ContainsKeyValue(
                    'X-Auth-Token', test_cli20.TOKEN)).AndReturn(response)

        self._test_extend_list(mox_calls)

    def test_extend_list_exceed_max_uri_len(self):
        def mox_calls(path, data):
            sub_data_lists = [data[:len(data) - 1], data[len(data) - 1:]]
            filters, response = self._build_test_data(data)

            # 1 char of extra URI len will cause a split in 2 requests
            self.mox.StubOutWithMock(self.client, "_check_uri_length")
            self.client._check_uri_length(mox.IgnoreArg()).AndRaise(
                exceptions.RequestURITooLong(excess=1))

            for data in sub_data_lists:
                filters, response = self._build_test_data(data)
                self.client._check_uri_length(mox.IgnoreArg()).AndReturn(None)
                self.client.httpclient.request(
                    test_cli20.end_url(path,
                                       'fields=id&fields=cidr%s' % filters),
                    'GET',
                    body=None,
                    headers=mox.ContainsKeyValue(
                        'X-Auth-Token', test_cli20.TOKEN)).AndReturn(response)

        self._test_extend_list(mox_calls)


class CLITestV20NetworkXML(CLITestV20NetworkJSON):
    format = 'xml'

########NEW FILE########
__FILENAME__ = test_cli20_networkprofile
# Copyright 2013 Cisco Systems Inc.
# All Rights Reserved
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.
#
# @author: Kyle Mestery, Cisco Systems, Inc.
#

import sys

from neutronclient.neutron.v2_0 import networkprofile
from neutronclient.tests.unit import test_cli20


class CLITestV20NetworkProfile(test_cli20.CLITestV20Base):

    def test_create_networkprofile(self):
        """Create networkprofile: myid."""
        resource = 'network_profile'
        cmd = networkprofile.CreateNetworkProfile(test_cli20.
                                                  MyApp(sys.stdout), None)
        name = 'myname'
        myid = 'myid'
        segment_type = 'vlan'
        args = [name, segment_type]
        position_names = ['name', 'segment_type']
        position_values = [name, segment_type]
        self._test_create_resource(resource, cmd, name, myid, args,
                                   position_names, position_values)

    def test_list_networkprofile_detail(self):
        """List networkprofile: -D."""
        resources = 'network_profiles'
        cmd = networkprofile.ListNetworkProfile(test_cli20.MyApp(sys.stdout),
                                                None)
        contents = [{'name': 'myname', 'segment_type': 'vlan'}]
        self._test_list_resources(resources, cmd, True,
                                  response_contents=contents)

    def test_list_networkprofile_known_option_after_unknown(self):
        """List networkprofile: -- --tags a b --request-format xml."""
        resources = 'network_profiles'
        cmd = networkprofile.ListNetworkProfile(test_cli20.MyApp(sys.stdout),
                                                None)
        contents = [{'name': 'myname', 'segment_type': 'vlan'}]
        self._test_list_resources(resources, cmd, tags=['a', 'b'],
                                  response_contents=contents)

    def test_list_networkprofile_fields(self):
        """List networkprofile: --fields a --fields b -- --fields c d."""
        resources = 'network_profiles'
        cmd = networkprofile.ListNetworkProfile(test_cli20.MyApp(sys.stdout),
                                                None)
        contents = [{'name': 'myname', 'segment_type': 'vlan'}]
        self._test_list_resources(resources, cmd,
                                  fields_1=['a', 'b'], fields_2=['c', 'd'],
                                  response_contents=contents)

    def test_show_networkprofile(self):
        """Show networkprofile: --fields id --fields name myid."""
        resource = 'network_profile'
        cmd = networkprofile.ShowNetworkProfile(test_cli20.MyApp(sys.stdout),
                                                None)
        args = ['--fields', 'id', '--fields', 'name', self.test_id]
        self._test_show_resource(resource, cmd, self.test_id, args,
                                 ['id', 'name'])

    def test_delete_networkprofile(self):
        """Delete networkprofile: myid."""
        resource = 'network_profile'
        cmd = networkprofile.DeleteNetworkProfile(test_cli20.
                                                  MyApp(sys.stdout), None)
        myid = 'myid'
        args = [myid]
        self._test_delete_resource(resource, cmd, myid, args)

    def test_create_networkprofile_trunk(self):
        """Create networkprofile: myid."""
        resource = 'network_profile'
        cmd = networkprofile.CreateNetworkProfile(test_cli20.
                                                  MyApp(sys.stdout), None)
        name = 'myname'
        myid = 'myid'
        segment_type = 'trunk'
        args = [name, segment_type, '--sub_type', 'vlan']
        position_names = ['name', 'segment_type', ]
        position_values = [name, segment_type, ]
        self._test_create_resource(resource, cmd, name, myid, args,
                                   position_names, position_values,
                                   sub_type='vlan')

    def test_list_networkprofile_trunk_detail(self):
        """List networkprofile: -D."""
        resources = 'network_profiles'
        cmd = networkprofile.ListNetworkProfile(test_cli20.MyApp(sys.stdout),
                                                None)
        contents = [{'name': 'myname', 'segment_type': 'trunk',
                    '--sub_type': 'vlan'}]
        self._test_list_resources(resources, cmd, True,
                                  response_contents=contents)

########NEW FILE########
__FILENAME__ = test_cli20_nsx_networkgateway
# Copyright 2012 VMware, Inc
# All Rights Reserved
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.
#

import sys

import mox

from neutronclient.neutron.v2_0.nsx import networkgateway as nwgw
from neutronclient.tests.unit import test_cli20


class CLITestV20NetworkGatewayJSON(test_cli20.CLITestV20Base):

    gw_resource = "network_gateway"
    dev_resource = "gateway_device"

    def setUp(self):
        super(CLITestV20NetworkGatewayJSON, self).setUp(
            plurals={'devices': 'device',
                     'network_gateways': 'network_gateway'})

    def test_create_gateway(self):
        cmd = nwgw.CreateNetworkGateway(test_cli20.MyApp(sys.stdout), None)
        name = 'gw-test'
        myid = 'myid'
        args = [name, ]
        position_names = ['name', ]
        position_values = [name, ]
        self._test_create_resource(self.gw_resource, cmd, name, myid, args,
                                   position_names, position_values)

    def test_create_gateway_with_tenant(self):
        cmd = nwgw.CreateNetworkGateway(test_cli20.MyApp(sys.stdout), None)
        name = 'gw-test'
        myid = 'myid'
        args = ['--tenant_id', 'tenantid', name]
        position_names = ['name', ]
        position_values = [name, ]
        self._test_create_resource(self.gw_resource, cmd, name, myid, args,
                                   position_names, position_values,
                                   tenant_id='tenantid')

    def test_create_gateway_with_device(self):
        cmd = nwgw.CreateNetworkGateway(test_cli20.MyApp(sys.stdout), None)
        name = 'gw-test'
        myid = 'myid'
        args = ['--device', 'device_id=test', name, ]
        position_names = ['name', ]
        position_values = [name, ]
        self._test_create_resource(self.gw_resource, cmd, name, myid, args,
                                   position_names, position_values,
                                   devices=[{'device_id': 'test'}])

    def test_list_gateways(self):
        resources = '%ss' % self.gw_resource
        cmd = nwgw.ListNetworkGateway(test_cli20.MyApp(sys.stdout), None)
        self._test_list_resources(resources, cmd, True)

    def test_update_gateway(self):
        cmd = nwgw.UpdateNetworkGateway(test_cli20.MyApp(sys.stdout), None)
        self._test_update_resource(self.gw_resource, cmd, 'myid',
                                   ['myid', '--name', 'higuain'],
                                   {'name': 'higuain'})

    def test_delete_gateway(self):
        cmd = nwgw.DeleteNetworkGateway(test_cli20.MyApp(sys.stdout), None)
        myid = 'myid'
        args = [myid]
        self._test_delete_resource(self.gw_resource, cmd, myid, args)

    def test_show_gateway(self):
        cmd = nwgw.ShowNetworkGateway(test_cli20.MyApp(sys.stdout), None)
        args = ['--fields', 'id', '--fields', 'name', self.test_id]
        self._test_show_resource(self.gw_resource, cmd, self.test_id, args,
                                 ['id', 'name'])

    def test_connect_network_to_gateway(self):
        cmd = nwgw.ConnectNetworkGateway(test_cli20.MyApp(sys.stdout), None)
        args = ['gw_id', 'net_id',
                '--segmentation-type', 'edi',
                '--segmentation-id', '7']
        self._test_update_resource_action(self.gw_resource, cmd, 'gw_id',
                                          'connect_network',
                                          args,
                                          {'network_id': 'net_id',
                                           'segmentation_type': 'edi',
                                           'segmentation_id': '7'})

    def test_disconnect_network_from_gateway(self):
        cmd = nwgw.DisconnectNetworkGateway(test_cli20.MyApp(sys.stdout), None)
        args = ['gw_id', 'net_id',
                '--segmentation-type', 'edi',
                '--segmentation-id', '7']
        self._test_update_resource_action(self.gw_resource, cmd, 'gw_id',
                                          'disconnect_network',
                                          args,
                                          {'network_id': 'net_id',
                                           'segmentation_type': 'edi',
                                           'segmentation_id': '7'})

    def _test_create_gateway_device(self,
                                    name,
                                    connector_type,
                                    connector_ip,
                                    client_certificate=None,
                                    client_certificate_file=None,
                                    must_raise=False):
        cmd = nwgw.CreateGatewayDevice(test_cli20.MyApp(sys.stdout), None)
        myid = 'myid'
        extra_body = {'connector_type': connector_type,
                      'connector_ip': connector_ip,
                      'client_certificate': client_certificate}
        self.mox.StubOutWithMock(nwgw, 'read_cert_file')
        if client_certificate_file:
            nwgw.read_cert_file(mox.IgnoreArg()).AndReturn('xyz')
            extra_body['client_certificate'] = 'xyz'
        self.mox.ReplayAll()
        position_names = ['name', ]
        position_values = [name, ]
        args = []
        for (k, v) in extra_body.iteritems():
            if (k == 'client_certificate' and client_certificate_file):
                v = client_certificate_file
                k = 'client_certificate_file'
            # Append argument only if value for it was specified
            if v:
                args.extend(['--%s' % k.replace('_', '-'), v])
        # The following is just for verifying the call fails as expected when
        # both certificate and certificate file are specified. The extra
        # argument added is client-certificate since the loop above added
        # client-certificate-file
        if client_certificate_file and client_certificate:
            args.extend(['--client-certificate', client_certificate_file])
        args.append(name)
        if must_raise:
            with test_cli20.capture_std_streams():
                self.assertRaises(
                    SystemExit, self._test_create_resource,
                    self.dev_resource, cmd, name, myid, args,
                    position_names, position_values, extra_body=extra_body)
        else:
            self._test_create_resource(
                self.dev_resource, cmd, name, myid, args,
                position_names, position_values, extra_body=extra_body)
        self.mox.UnsetStubs()

    def test_create_gateway_device(self):
        self._test_create_gateway_device('dev_test', 'stt', '1.1.1.1', 'xyz')

    def test_create_gateway_device_with_certfile(self):
        self._test_create_gateway_device('dev_test', 'stt', '1.1.1.1',
                                         client_certificate_file='some_file')

    def test_create_gateway_device_invalid_connector_type_fails(self):
        self._test_create_gateway_device('dev_test', 'ciccio',
                                         '1.1.1.1', client_certificate='xyz',
                                         must_raise=True)

    def test_create_gateway_device_missing_connector_ip_fails(self):
        self._test_create_gateway_device('dev_test', 'stt',
                                         None, client_certificate='xyz',
                                         must_raise=True)

    def test_create_gateway_device_missing_certificates_fails(self):
        self._test_create_gateway_device('dev_test', 'stt', '1.1.1.1',
                                         must_raise=True)

    def test_create_gateway_device_with_cert_and_cert_file_fails(self):
        self._test_create_gateway_device('dev_test', 'stt', '1.1.1.1',
                                         client_certificate='xyz',
                                         client_certificate_file='some_file',
                                         must_raise=True)

    def _test_update_gateway_device(self,
                                    name=None,
                                    connector_type=None,
                                    connector_ip=None,
                                    client_certificate=None,
                                    client_certificate_file=None,
                                    must_raise=False):
        cmd = nwgw.UpdateGatewayDevice(test_cli20.MyApp(sys.stdout), None)
        myid = 'myid'
        extra_body = {}
        self.mox.StubOutWithMock(nwgw, 'read_cert_file')
        if client_certificate_file:
            nwgw.read_cert_file(mox.IgnoreArg()).AndReturn('xyz')
        self.mox.ReplayAll()
        args = [myid]

        def process_arg(argname, arg):
            if arg:
                extra_body[argname] = arg
                args.extend(['--%s' % argname.replace('_', '-'), arg])

        process_arg('name', name)
        process_arg('connector_type', connector_type)
        process_arg('connector_ip', connector_ip)
        process_arg('client_certificate', client_certificate)
        if client_certificate_file:
            extra_body['client_certificate'] = 'xyz'
            args.extend(['--client-certificate-file',
                         client_certificate_file])
        if must_raise:
            with test_cli20.capture_std_streams():
                self.assertRaises(
                    SystemExit, self._test_update_resource,
                    self.dev_resource, cmd, myid, args,
                    extrafields=extra_body)
        else:
            self._test_update_resource(
                self.dev_resource, cmd, myid, args,
                extrafields=extra_body)
        self.mox.UnsetStubs()

    def test_update_gateway_device(self):
        self._test_update_gateway_device('dev_test', 'stt', '1.1.1.1', 'xyz')

    def test_update_gateway_device_partial_body(self):
        self._test_update_gateway_device(name='dev_test',
                                         connector_type='stt')

    def test_update_gateway_device_with_certfile(self):
        self._test_update_gateway_device('dev_test', 'stt', '1.1.1.1',
                                         client_certificate_file='some_file')

    def test_update_gateway_device_invalid_connector_type_fails(self):
        self._test_update_gateway_device('dev_test', 'ciccio',
                                         '1.1.1.1', client_certificate='xyz',
                                         must_raise=True)

    def test_update_gateway_device_with_cert_and_cert_file_fails(self):
        self._test_update_gateway_device('dev_test', 'stt', '1.1.1.1',
                                         client_certificate='xyz',
                                         client_certificate_file='some_file',
                                         must_raise=True)

    def test_delete_gateway_device(self):
        cmd = nwgw.DeleteGatewayDevice(test_cli20.MyApp(sys.stdout), None)
        myid = 'myid'
        args = [myid]
        self._test_delete_resource(self.dev_resource, cmd, myid, args)

    def test_show_gateway_device(self):
        cmd = nwgw.ShowGatewayDevice(test_cli20.MyApp(sys.stdout), None)
        args = ['--fields', 'id', '--fields', 'name', self.test_id]
        self._test_show_resource(self.dev_resource, cmd, self.test_id, args,
                                 ['id', 'name'])


class CLITestV20NetworkGatewayXML(CLITestV20NetworkGatewayJSON):
    format = 'xml'

########NEW FILE########
__FILENAME__ = test_cli20_nsx_queue
#!/usr/bin/env python
# Copyright 2013 VMware Inc.
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import sys

from neutronclient.neutron.v2_0.nsx import qos_queue as qos
from neutronclient.tests.unit import test_cli20


class CLITestV20QosQueueJSON(test_cli20.CLITestV20Base):
    def setUp(self):
        super(CLITestV20QosQueueJSON, self).setUp(
            plurals={'qos_queues': 'qos_queue'})

    def test_create_qos_queue(self):
        """Create a qos queue."""
        resource = 'qos_queue'
        cmd = qos.CreateQoSQueue(
            test_cli20.MyApp(sys.stdout), None)
        myid = 'myid'
        name = 'my_queue'
        default = False
        args = ['--default', default, name]
        position_names = ['name', 'default']
        position_values = [name, default]
        self._test_create_resource(resource, cmd, name, myid, args,
                                   position_names, position_values)

    def test_create_qos_queue_all_values(self):
        """Create a qos queue."""
        resource = 'qos_queue'
        cmd = qos.CreateQoSQueue(
            test_cli20.MyApp(sys.stdout), None)
        myid = 'myid'
        name = 'my_queue'
        default = False
        min = '10'
        max = '40'
        qos_marking = 'untrusted'
        dscp = '0'
        args = ['--default', default, '--min', min, '--max', max,
                '--qos-marking', qos_marking, '--dscp', dscp, name]
        position_names = ['name', 'default', 'min', 'max', 'qos_marking',
                          'dscp']
        position_values = [name, default, min, max, qos_marking, dscp]
        self._test_create_resource(resource, cmd, name, myid, args,
                                   position_names, position_values)

    def test_list_qos_queue(self):
        resources = "qos_queues"
        cmd = qos.ListQoSQueue(
            test_cli20.MyApp(sys.stdout), None)
        self._test_list_resources(resources, cmd, True)

    def test_show_qos_queue_id(self):
        resource = 'qos_queue'
        cmd = qos.ShowQoSQueue(
            test_cli20.MyApp(sys.stdout), None)
        args = ['--fields', 'id', self.test_id]
        self._test_show_resource(resource, cmd, self.test_id,
                                 args, ['id'])

    def test_delete_qos_queue(self):
        resource = 'qos_queue'
        cmd = qos.DeleteQoSQueue(
            test_cli20.MyApp(sys.stdout), None)
        myid = 'myid'
        args = [myid]
        self._test_delete_resource(resource, cmd, myid, args)


class CLITestV20QosQueueXML(CLITestV20QosQueueJSON):
    format = 'xml'

########NEW FILE########
__FILENAME__ = test_cli20_nuage_netpartition
# Copyright 2014 Alcatel-Lucent USA Inc.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.
#
# @author: Ronak Shah, Nuage Networks, Alcatel-Lucent USA Inc.

import sys

from neutronclient.neutron.v2_0 import netpartition
from neutronclient.tests.unit import test_cli20


class CLITestV20NetPartitionJSON(test_cli20.CLITestV20Base):
    resource = 'net_partition'

    def test_create_netpartition(self):
        cmd = netpartition.CreateNetPartition(test_cli20.MyApp(sys.stdout),
                                              None)
        name = 'myname'
        myid = 'myid'
        args = [name, ]
        position_names = ['name', ]
        position_values = [name, ]
        self._test_create_resource(self.resource, cmd, name, myid, args,
                                   position_names, position_values)

    def test_list_netpartitions(self):
        resources = '%ss' % self.resource
        cmd = netpartition.ListNetPartition(test_cli20.MyApp(sys.stdout),
                                            None)
        self._test_list_resources(resources, cmd, True)

    def test_show_netpartition(self):
        cmd = netpartition.ShowNetPartition(test_cli20.MyApp(sys.stdout),
                                            None)
        args = ['--fields', 'id', '--fields', 'name', self.test_id]
        self._test_show_resource(self.resource, cmd, self.test_id, args,
                                 ['id', 'name'])

    def test_delete_netpartition(self):
        cmd = netpartition.DeleteNetPartition(test_cli20.MyApp(sys.stdout),
                                              None)
        myid = 'myid'
        args = [myid]
        self._test_delete_resource(self.resource, cmd, myid, args)


class CLITestV20NetPartitionXML(CLITestV20NetPartitionJSON):
    format = 'xml'

########NEW FILE########
__FILENAME__ = test_cli20_packetfilter
# Copyright 2014 NEC Corporation.
# All Rights Reserved
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import sys

import mox

from neutronclient.common import exceptions
from neutronclient.neutron.v2_0.nec import packetfilter as pf
from neutronclient import shell
from neutronclient.tests.unit import test_cli20


class CLITestV20PacketFilterJSON(test_cli20.CLITestV20Base):
    def test_create_packetfilter_with_mandatory_params(self):
        """Create packetfilter: packetfilter1."""
        resource = 'packet_filter'
        cmd = pf.CreatePacketFilter(test_cli20.MyApp(sys.stdout), None)
        name = 'packetfilter1'
        myid = 'myid'
        args = ['--priority', '30000', '--action', 'allow', 'net1']
        position_names = ['network_id', 'action', 'priority']
        position_values = ['net1', 'allow', '30000']
        self._test_create_resource(resource, cmd, name, myid, args,
                                   position_names, position_values)

    def test_create_packetfilter_with_all_params(self):
        """Create packetfilter: packetfilter1."""
        resource = 'packet_filter'
        cmd = pf.CreatePacketFilter(test_cli20.MyApp(sys.stdout), None)
        name = 'packetfilter1'
        myid = 'myid'
        args = ['--name', name,
                '--admin-state-down',
                '--in-port', 'port1',
                '--src-mac', '00:11:22:33:44:55',
                '--dst-mac', 'aa:bb:cc:dd:ee:ff',
                '--eth-type', '0x0800',
                '--protocol', 'tcp',
                '--src-cidr', '10.1.1.0/24',
                '--dst-cidr', '10.2.2.0/24',
                '--src-port', '40001',
                '--dst-port', '4000',
                '--priority', '30000',
                '--action', 'drop', 'net1']
        params = {'network_id': 'net1',
                  'action': 'drop',
                  'priority': '30000',
                  'name': name,
                  'admin_state_up': False,
                  'in_port': 'port1',
                  'src_mac': '00:11:22:33:44:55',
                  'dst_mac': 'aa:bb:cc:dd:ee:ff',
                  'eth_type': '0x0800',
                  'protocol': 'tcp',
                  'src_cidr': '10.1.1.0/24',
                  'dst_cidr': '10.2.2.0/24',
                  'src_port': '40001',
                  'dst_port': '4000',
                  }
        position_names = sorted(params)
        position_values = [params[k] for k in sorted(params)]
        self._test_create_resource(resource, cmd, name, myid, args,
                                   position_names, position_values)

    def test_list_packetfilters_detail(self):
        """list packetfilters: -D."""
        resources = "packet_filters"
        cmd = pf.ListPacketFilter(test_cli20.MyApp(sys.stdout), None)
        response_contents = [{'id': 'myid1', 'network_id': 'net1'},
                             {'id': 'myid2', 'network_id': 'net2'}]
        self._test_list_resources(resources, cmd, True,
                                  response_contents=response_contents)

    def _stubout_extend_list(self):
        self.mox.StubOutWithMock(pf.ListPacketFilter, "extend_list")
        pf.ListPacketFilter.extend_list(mox.IsA(list), mox.IgnoreArg())

    def test_list_packetfilters_pagination(self):
        resources = "packet_filters"
        cmd = pf.ListPacketFilter(test_cli20.MyApp(sys.stdout), None)
        self._stubout_extend_list()
        self._test_list_resources_with_pagination(resources, cmd)

    def test_list_packetfilters_sort(self):
        """list packetfilters: --sort-key name --sort-key id --sort-key asc
        --sort-key desc
        """
        resources = "packet_filters"
        cmd = pf.ListPacketFilter(test_cli20.MyApp(sys.stdout), None)
        self._stubout_extend_list()
        self._test_list_resources(resources, cmd,
                                  sort_key=["name", "id"],
                                  sort_dir=["asc", "desc"])

    def test_list_packetfilters_limit(self):
        """list packetfilters: -P."""
        resources = "packet_filters"
        cmd = pf.ListPacketFilter(test_cli20.MyApp(sys.stdout), None)
        self._stubout_extend_list()
        self._test_list_resources(resources, cmd, page_size=1000)

    def test_update_packetfilter(self):
        """Update packetfilter: myid --name myname --tags a b."""
        resource = 'packet_filter'
        cmd = pf.UpdatePacketFilter(test_cli20.MyApp(sys.stdout), None)
        self._test_update_resource(resource, cmd, 'myid',
                                   ['myid', '--name', 'myname'],
                                   {'name': 'myname'}
                                   )

    def test_update_packetfilter_with_all_params(self):
        resource = 'packet_filter'
        cmd = pf.UpdatePacketFilter(test_cli20.MyApp(sys.stdout), None)
        name = 'packetfilter1'
        args = ['--name', name,
                '--admin-state', 'True',
                '--src-mac', '00:11:22:33:44:55',
                '--dst-mac', 'aa:bb:cc:dd:ee:ff',
                '--eth-type', '0x0800',
                '--protocol', 'tcp',
                '--src-cidr', '10.1.1.0/24',
                '--dst-cidr', '10.2.2.0/24',
                '--src-port', '40001',
                '--dst-port', '4000',
                '--priority', '30000',
                '--action', 'drop',
                'myid'
                ]
        params = {'action': 'drop',
                  'priority': '30000',
                  'name': name,
                  'admin_state_up': True,
                  'src_mac': '00:11:22:33:44:55',
                  'dst_mac': 'aa:bb:cc:dd:ee:ff',
                  'eth_type': '0x0800',
                  'protocol': 'tcp',
                  'src_cidr': '10.1.1.0/24',
                  'dst_cidr': '10.2.2.0/24',
                  'src_port': '40001',
                  'dst_port': '4000',
                  }
        # position_names = sorted(params)
        # position_values = [params[k] for k in sorted(params)]
        self._test_update_resource(resource, cmd, 'myid',
                                   args, params)

    def test_update_packetfilter_admin_state_false(self):
        resource = 'packet_filter'
        cmd = pf.UpdatePacketFilter(test_cli20.MyApp(sys.stdout), None)
        args = ['--admin-state', 'False', 'myid']
        params = {'admin_state_up': False}
        self._test_update_resource(resource, cmd, 'myid',
                                   args, params)

    def test_update_packetfilter_exception(self):
        """Update packetfilter: myid."""
        resource = 'packet_filter'
        cmd = pf.UpdatePacketFilter(test_cli20.MyApp(sys.stdout), None)
        exc = self.assertRaises(exceptions.CommandError,
                                self._test_update_resource,
                                resource, cmd, 'myid', ['myid'], {})
        self.assertEqual('Must specify new values to update packet_filter',
                         unicode(exc))

    def test_delete_packetfilter(self):
        """Delete packetfilter: myid."""
        resource = 'packet_filter'
        cmd = pf.DeletePacketFilter(test_cli20.MyApp(sys.stdout), None)
        myid = 'myid'
        args = [myid]
        self._test_delete_resource(resource, cmd, myid, args)

    def test_show_packetfilter(self):
        """Show packetfilter: myid."""
        resource = 'packet_filter'
        cmd = pf.ShowPacketFilter(test_cli20.MyApp(sys.stdout), None)
        args = ['--fields', 'id', '--fields', 'name', self.test_id]
        self._test_show_resource(resource, cmd, self.test_id, args,
                                 ['id', 'name'])


class CLITestV20PacketFilterXML(CLITestV20PacketFilterJSON):
    format = 'xml'


class CLITestV20PacketFilterValidateParam(test_cli20.CLITestV20Base):
    def _test_create_packetfilter_pass_validation(self, cmdline=None,
                                                  params=None, base_args=None):
        resource = 'packet_filter'
        cmd = pf.CreatePacketFilter(test_cli20.MyApp(sys.stdout), None)
        name = 'packetfilter1'
        myid = 'myid'
        if base_args is None:
            args = '--priority 30000 --action allow net1'.split()
        else:
            args = base_args.split()
        if cmdline:
            args += cmdline.split()
        _params = {'network_id': 'net1',
                   'action': 'allow',
                   'priority': '30000'}
        if params:
            _params.update(params)
        position_names = sorted(_params)
        position_values = [_params[k] for k in sorted(_params)]
        self._test_create_resource(resource, cmd, name, myid, args,
                                   position_names, position_values)

    def _test_create_packetfilter_negative_validation(self, cmdline):
        resource = 'packet_filter'
        cmd = pf.CreatePacketFilter(test_cli20.MyApp(sys.stdout), None)
        self.mox.StubOutWithMock(cmd, "get_client")
        self.mox.StubOutWithMock(self.client.httpclient, "request")
        cmd.get_client().MultipleTimes().AndReturn(self.client)
        cmd_parser = cmd.get_parser('create_' + resource)
        args = cmdline.split()
        self.assertRaises(exceptions.CommandError,
                          shell.run_command,
                          cmd, cmd_parser, args)

    def test_create_pf_hex_priority(self):
        self._test_create_packetfilter_pass_validation(
            base_args='--priority 0xffff --action allow net1',
            params={'priority': '0xffff'})

    def test_create_pf_hex_src_port(self):
        self._test_create_packetfilter_pass_validation(
            cmdline='--src-port 0xffff', params={'src_port': '0xffff'})

    def test_create_pf_hex_dst_port(self):
        self._test_create_packetfilter_pass_validation(
            cmdline='--dst-port 0xffff', params={'dst_port': '0xffff'})

    def test_create_pf_ip_proto_zero(self):
        self._test_create_packetfilter_pass_validation(
            cmdline='--protocol 0', params={'protocol': '0'})

    def test_create_pf_ip_proto_max_hex(self):
        self._test_create_packetfilter_pass_validation(
            cmdline='--protocol 0xff', params={'protocol': '0xff'})

    def test_create_pf_ip_proto_with_names(self):
        for proto in ['tcp', 'xxxx']:
            self._test_create_packetfilter_pass_validation(
                cmdline='--protocol ' + proto, params={'protocol': proto})

    def test_create_pf_negative_priority(self):
        self._test_create_packetfilter_negative_validation(
            '--priority -1 --action allow net1')

    def test_create_pf_too_big_priority(self):
        self._test_create_packetfilter_negative_validation(
            '--priority 65536 --action allow net1')

    def test_create_pf_negative_src_port(self):
        self._test_create_packetfilter_negative_validation(
            '--src-port -1 --priority 20000 --action allow net1')

    def test_create_pf_too_big_src_port(self):
        self._test_create_packetfilter_negative_validation(
            '--src-port 65536 --priority 20000 --action allow net1')

    def test_create_pf_negative_dst_port(self):
        self._test_create_packetfilter_negative_validation(
            '--dst-port -1 --priority 20000 --action allow net1')

    def test_create_pf_too_big_dst_port(self):
        self._test_create_packetfilter_negative_validation(
            '--dst-port 65536 --priority 20000 --action allow net1')

    def test_create_pf_negative_protocol(self):
        self._test_create_packetfilter_negative_validation(
            '--protocol -1 --priority 20000 --action allow net1')

    def test_create_pf_too_big_hex_protocol(self):
        self._test_create_packetfilter_negative_validation(
            '--protocol 0x100 --priority 20000 --action allow net1')

    def test_create_pf_invalid_src_cidr(self):
        self._test_create_packetfilter_negative_validation(
            '--src-cidr invalid --priority 20000 --action allow net1')

    def test_create_pf_invalid_dst_cidr(self):
        self._test_create_packetfilter_negative_validation(
            '--dst-cidr invalid --priority 20000 --action allow net1')

########NEW FILE########
__FILENAME__ = test_cli20_policyprofile
# Copyright 2013 Cisco Systems Inc.
# All Rights Reserved
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.
#
# @author: Kyle Mestery, Cisco Systems, Inc.
#

import sys

from neutronclient.neutron.v2_0 import policyprofile
from neutronclient.tests.unit import test_cli20


class CLITestV20PolicyProfile(test_cli20.CLITestV20Base):

    def test_list_policyprofile_detail(self):
        """List policyprofile: -D."""
        resources = 'policy_profiles'
        cmd = policyprofile.ListPolicyProfile(test_cli20.MyApp(sys.stdout),
                                              None)
        contents = [{'name': 'myname', 'segment_type': 'vlan'}]
        self._test_list_resources(resources, cmd, True,
                                  response_contents=contents)

    def test_list_policyprofile_known_option_after_unknown(self):
        """List policyprofile: -- --tags a b --request-format xml."""
        resources = 'policy_profiles'
        cmd = policyprofile.ListPolicyProfile(test_cli20.MyApp(sys.stdout),
                                              None)
        contents = [{'name': 'myname', 'segment_type': 'vlan'}]
        self._test_list_resources(resources, cmd, tags=['a', 'b'],
                                  response_contents=contents)

    def test_list_policyprofile_fields(self):
        """List policyprofile: --fields a --fields b -- --fields c d."""
        resources = 'policy_profiles'
        cmd = policyprofile.ListPolicyProfile(test_cli20.MyApp(sys.stdout),
                                              None)
        contents = [{'name': 'myname', 'segment_type': 'vlan'}]
        self._test_list_resources(resources, cmd,
                                  fields_1=['a', 'b'], fields_2=['c', 'd'],
                                  response_contents=contents)

    def test_show_policyprofile(self):
        """Show policyprofile: --fields id --fields name myid."""
        resource = 'policy_profile'
        cmd = policyprofile.ShowPolicyProfile(test_cli20.MyApp(sys.stdout),
                                              None)
        args = ['--fields', 'id', '--fields', 'name', self.test_id]
        self._test_show_resource(resource, cmd, self.test_id, args,
                                 ['id', 'name'])

    def test_update_policyprofile(self):
        """Update policyprofile: myid --name myname --tags a b."""
        resource = 'policy_profile'
        cmd = policyprofile.UpdatePolicyProfile(test_cli20.MyApp(sys.stdout),
                                                None)
        self._test_update_resource(resource, cmd, 'myid',
                                   ['myid', '--name', 'myname',
                                    '--tags', 'a', 'b'],
                                   {'name': 'myname', 'tags': ['a', 'b'], }
                                   )

########NEW FILE########
__FILENAME__ = test_cli20_port
# Copyright 2012 OpenStack Foundation.
# All Rights Reserved
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.
#

import sys

import mox

from neutronclient.neutron.v2_0 import port
from neutronclient import shell
from neutronclient.tests.unit import test_cli20


class CLITestV20PortJSON(test_cli20.CLITestV20Base):
    def setUp(self):
        super(CLITestV20PortJSON, self).setUp(plurals={'tags': 'tag'})

    def test_create_port(self):
        """Create port: netid."""
        resource = 'port'
        cmd = port.CreatePort(test_cli20.MyApp(sys.stdout), None)
        name = 'myname'
        myid = 'myid'
        netid = 'netid'
        args = [netid]
        position_names = ['network_id']
        position_values = []
        position_values.extend([netid])
        self._test_create_resource(resource, cmd, name, myid, args,
                                   position_names, position_values)

    def test_create_port_extra_dhcp_opts_args(self):
        """Create port: netid --extra_dhcp_opt."""
        resource = 'port'
        cmd = port.CreatePort(test_cli20.MyApp(sys.stdout), None)
        name = 'myname'
        myid = 'myid'
        netid = 'netid'
        extra_dhcp_opts = [{'opt_name': 'bootfile-name',
                            'opt_value': 'pxelinux.0'},
                           {'opt_name': 'tftp-server',
                            'opt_value': '123.123.123.123'},
                           {'opt_name': 'server-ip-address',
                            'opt_value': '123.123.123.45'}]
        args = [netid]
        for dhcp_opt in extra_dhcp_opts:
            args += ['--extra-dhcp-opt',
                     ('opt_name=%(opt_name)s,opt_value=%(opt_value)s' %
                      dhcp_opt)]
        position_names = ['network_id', 'extra_dhcp_opts']
        position_values = [netid, extra_dhcp_opts]
        position_values.extend([netid])
        self._test_create_resource(resource, cmd, name, myid, args,
                                   position_names, position_values)

    def test_create_port_full(self):
        """Create port: --mac_address mac --device_id deviceid netid."""
        resource = 'port'
        cmd = port.CreatePort(test_cli20.MyApp(sys.stdout), None)
        name = 'myname'
        myid = 'myid'
        netid = 'netid'
        args = ['--mac_address', 'mac', '--device_id', 'deviceid', netid]
        position_names = ['network_id', 'mac_address', 'device_id']
        position_values = [netid, 'mac', 'deviceid']
        self._test_create_resource(resource, cmd, name, myid, args,
                                   position_names, position_values)

        # Test dashed options
        args = ['--mac-address', 'mac', '--device-id', 'deviceid', netid]
        position_names = ['network_id', 'mac_address', 'device_id']
        self._test_create_resource(resource, cmd, name, myid, args,
                                   position_names, position_values)

    def test_create_port_tenant(self):
        """Create port: --tenant_id tenantid netid."""
        resource = 'port'
        cmd = port.CreatePort(test_cli20.MyApp(sys.stdout), None)
        name = 'myname'
        myid = 'myid'
        netid = 'netid'
        args = ['--tenant_id', 'tenantid', netid, ]
        position_names = ['network_id']
        position_values = []
        position_values.extend([netid])
        self._test_create_resource(resource, cmd, name, myid, args,
                                   position_names, position_values,
                                   tenant_id='tenantid')

        # Test dashed options
        args = ['--tenant-id', 'tenantid', netid, ]
        self._test_create_resource(resource, cmd, name, myid, args,
                                   position_names, position_values,
                                   tenant_id='tenantid')

    def test_create_port_tags(self):
        """Create port: netid mac_address device_id --tags a b."""
        resource = 'port'
        cmd = port.CreatePort(test_cli20.MyApp(sys.stdout), None)
        name = 'myname'
        myid = 'myid'
        netid = 'netid'
        args = [netid, '--tags', 'a', 'b']
        position_names = ['network_id']
        position_values = []
        position_values.extend([netid])
        self._test_create_resource(resource, cmd, name, myid, args,
                                   position_names, position_values,
                                   tags=['a', 'b'])

    def test_create_port_secgroup(self):
        """Create port: --security-group sg1_id netid."""
        resource = 'port'
        cmd = port.CreatePort(test_cli20.MyApp(sys.stdout), None)
        name = 'myname'
        myid = 'myid'
        netid = 'netid'
        args = ['--security-group', 'sg1_id', netid]
        position_names = ['network_id', 'security_groups']
        position_values = [netid, ['sg1_id']]
        self._test_create_resource(resource, cmd, name, myid, args,
                                   position_names, position_values)

    def test_create_port_secgroups(self):
        """Create port: <security_groups> netid

        The <security_groups> are
        --security-group sg1_id --security-group sg2_id
        """
        resource = 'port'
        cmd = port.CreatePort(test_cli20.MyApp(sys.stdout), None)
        name = 'myname'
        myid = 'myid'
        netid = 'netid'
        args = ['--security-group', 'sg1_id',
                '--security-group', 'sg2_id',
                netid]
        position_names = ['network_id', 'security_groups']
        position_values = [netid, ['sg1_id', 'sg2_id']]
        self._test_create_resource(resource, cmd, name, myid, args,
                                   position_names, position_values)

    def test_create_port_secgroup_off(self):
        resource = 'port'
        cmd = port.CreatePort(test_cli20.MyApp(sys.stdout), None)
        name = 'myname'
        myid = 'myid'
        netid = 'netid'
        args = ['--no-security-group', netid]
        position_names = ['network_id', 'security_groups']
        position_values = [netid, []]
        self._test_create_resource(resource, cmd, name, myid, args,
                                   position_names, position_values)

    def test_create_port_secgroups_list(self):
        """Create port: netid <security_groups>
        The <security_groups> are
        --security-groups list=true sg_id1 sg_id2
        """
        resource = 'port'
        cmd = port.CreatePort(test_cli20.MyApp(sys.stdout), None)
        name = 'myname'
        myid = 'myid'
        netid = 'netid'
        args = [netid, '--security-groups', 'list=true', 'sg_id1', 'sg_id2']
        position_names = ['network_id', 'security_groups']
        position_values = [netid, ['sg_id1', 'sg_id2']]
        self._test_create_resource(resource, cmd, name, myid, args,
                                   position_names, position_values)

    def test_list_ports(self):
        """List ports: -D."""
        resources = "ports"
        cmd = port.ListPort(test_cli20.MyApp(sys.stdout), None)
        self._test_list_resources(resources, cmd, True)

    def test_list_ports_pagination(self):
        resources = "ports"
        cmd = port.ListPort(test_cli20.MyApp(sys.stdout), None)
        self._test_list_resources_with_pagination(resources, cmd)

    def test_list_ports_sort(self):
        """list ports: --sort-key name --sort-key id --sort-key asc
        --sort-key desc
        """
        resources = "ports"
        cmd = port.ListPort(test_cli20.MyApp(sys.stdout), None)
        self._test_list_resources(resources, cmd,
                                  sort_key=["name", "id"],
                                  sort_dir=["asc", "desc"])

    def test_list_ports_limit(self):
        """list ports: -P."""
        resources = "ports"
        cmd = port.ListPort(test_cli20.MyApp(sys.stdout), None)
        self._test_list_resources(resources, cmd, page_size=1000)

    def test_list_ports_tags(self):
        """List ports: -- --tags a b."""
        resources = "ports"
        cmd = port.ListPort(test_cli20.MyApp(sys.stdout), None)
        self._test_list_resources(resources, cmd, tags=['a', 'b'])

    def test_list_ports_detail_tags(self):
        """List ports: -D -- --tags a b."""
        resources = "ports"
        cmd = port.ListPort(test_cli20.MyApp(sys.stdout), None)
        self._test_list_resources(resources, cmd, detail=True, tags=['a', 'b'])

    def test_list_ports_fields(self):
        """List ports: --fields a --fields b -- --fields c d."""
        resources = "ports"
        cmd = port.ListPort(test_cli20.MyApp(sys.stdout), None)
        self._test_list_resources(resources, cmd,
                                  fields_1=['a', 'b'], fields_2=['c', 'd'])

    def _test_list_router_port(self, resources, cmd,
                               myid, detail=False, tags=[],
                               fields_1=[], fields_2=[]):
        self.mox.StubOutWithMock(cmd, "get_client")
        self.mox.StubOutWithMock(self.client.httpclient, "request")
        cmd.get_client().MultipleTimes().AndReturn(self.client)
        reses = {resources: [{'id': 'myid1', },
                             {'id': 'myid2', }, ], }

        resstr = self.client.serialize(reses)

        # url method body
        query = ""
        args = detail and ['-D', ] or []

        if fields_1:
            for field in fields_1:
                args.append('--fields')
                args.append(field)
        args.append(myid)
        if tags:
            args.append('--')
            args.append("--tag")
        for tag in tags:
            args.append(tag)
        if (not tags) and fields_2:
            args.append('--')
        if fields_2:
            args.append("--fields")
            for field in fields_2:
                args.append(field)
        fields_1.extend(fields_2)
        for field in fields_1:
            if query:
                query += "&fields=" + field
            else:
                query = "fields=" + field

        for tag in tags:
            if query:
                query += "&tag=" + tag
            else:
                query = "tag=" + tag
        if detail:
            query = query and query + '&verbose=True' or 'verbose=True'
        query = query and query + '&device_id=%s' or 'device_id=%s'
        path = getattr(self.client, resources + "_path")
        self.client.httpclient.request(
            test_cli20.end_url(path, query % myid), 'GET',
            body=None,
            headers=mox.ContainsKeyValue('X-Auth-Token', test_cli20.TOKEN)
        ).AndReturn((test_cli20.MyResp(200), resstr))
        self.mox.ReplayAll()
        cmd_parser = cmd.get_parser("list_" + resources)
        shell.run_command(cmd, cmd_parser, args)
        self.mox.VerifyAll()
        self.mox.UnsetStubs()
        _str = self.fake_stdout.make_string()

        self.assertIn('myid1', _str)

    def test_list_router_ports(self):
        """List router ports: -D."""
        resources = "ports"
        cmd = port.ListRouterPort(test_cli20.MyApp(sys.stdout), None)
        self._test_list_router_port(resources, cmd,
                                    self.test_id, True)

    def test_list_router_ports_tags(self):
        """List router ports: -- --tags a b."""
        resources = "ports"
        cmd = port.ListRouterPort(test_cli20.MyApp(sys.stdout), None)
        self._test_list_router_port(resources, cmd,
                                    self.test_id, tags=['a', 'b'])

    def test_list_router_ports_detail_tags(self):
        """List router ports: -D -- --tags a b."""
        resources = "ports"
        cmd = port.ListRouterPort(test_cli20.MyApp(sys.stdout), None)
        self._test_list_router_port(resources, cmd, self.test_id,
                                    detail=True, tags=['a', 'b'])

    def test_list_router_ports_fields(self):
        """List ports: --fields a --fields b -- --fields c d."""
        resources = "ports"
        cmd = port.ListRouterPort(test_cli20.MyApp(sys.stdout), None)
        self._test_list_router_port(resources, cmd, self.test_id,
                                    fields_1=['a', 'b'],
                                    fields_2=['c', 'd'])

    def test_update_port(self):
        """Update port: myid --name myname --tags a b."""
        resource = 'port'
        cmd = port.UpdatePort(test_cli20.MyApp(sys.stdout), None)
        self._test_update_resource(resource, cmd, 'myid',
                                   ['myid', '--name', 'myname',
                                    '--tags', 'a', 'b'],
                                   {'name': 'myname', 'tags': ['a', 'b'], }
                                   )

    def test_update_port_secgroup(self):
        resource = 'port'
        cmd = port.UpdatePort(test_cli20.MyApp(sys.stdout), None)
        myid = 'myid'
        args = ['--security-group', 'sg1_id', myid]
        updatefields = {'security_groups': ['sg1_id']}
        self._test_update_resource(resource, cmd, myid, args, updatefields)

    def test_update_port_secgroups(self):
        resource = 'port'
        cmd = port.UpdatePort(test_cli20.MyApp(sys.stdout), None)
        myid = 'myid'
        args = ['--security-group', 'sg1_id',
                '--security-group', 'sg2_id',
                myid]
        updatefields = {'security_groups': ['sg1_id', 'sg2_id']}
        self._test_update_resource(resource, cmd, myid, args, updatefields)

    def test_update_port_extra_dhcp_opts(self):
        """Update port: myid --extra_dhcp_opt."""
        resource = 'port'
        myid = 'myid'
        args = [myid,
                '--extra-dhcp-opt',
                "opt_name=bootfile-name,opt_value=pxelinux.0",
                '--extra-dhcp-opt',
                "opt_name=tftp-server,opt_value=123.123.123.123",
                '--extra-dhcp-opt',
                "opt_name=server-ip-address,opt_value=123.123.123.45"
                ]
        updatedfields = {'extra_dhcp_opts': [{'opt_name': 'bootfile-name',
                                              'opt_value': 'pxelinux.0'},
                                             {'opt_name': 'tftp-server',
                                              'opt_value': '123.123.123.123'},
                                             {'opt_name': 'server-ip-address',
                                              'opt_value': '123.123.123.45'}]}
        cmd = port.UpdatePort(test_cli20.MyApp(sys.stdout), None)
        self._test_update_resource(resource, cmd, myid, args, updatedfields)

    def test_delete_extra_dhcp_opts_from_port(self):
        resource = 'port'
        myid = 'myid'
        args = [myid,
                '--extra-dhcp-opt',
                "opt_name=bootfile-name,opt_value=null",
                '--extra-dhcp-opt',
                "opt_name=tftp-server,opt_value=123.123.123.123",
                '--extra-dhcp-opt',
                "opt_name=server-ip-address,opt_value=123.123.123.45"
                ]
        # the client code will change the null to None and send to server,
        # where its interpreted as delete the DHCP option on the port.
        updatedfields = {'extra_dhcp_opts': [{'opt_name': 'bootfile-name',
                                             'opt_value': None},
                                             {'opt_name': 'tftp-server',
                                              'opt_value': '123.123.123.123'},
                                             {'opt_name': 'server-ip-address',
                                              'opt_value': '123.123.123.45'}]}
        cmd = port.UpdatePort(test_cli20.MyApp(sys.stdout), None)
        self._test_update_resource(resource, cmd, myid, args, updatedfields)

    def test_update_port_security_group_off(self):
        """Update port: --no-security-groups myid."""
        resource = 'port'
        cmd = port.UpdatePort(test_cli20.MyApp(sys.stdout), None)
        self._test_update_resource(resource, cmd, 'myid',
                                   ['--no-security-groups', 'myid'],
                                   {'security_groups': []})

    def test_show_port(self):
        """Show port: --fields id --fields name myid."""
        resource = 'port'
        cmd = port.ShowPort(test_cli20.MyApp(sys.stdout), None)
        args = ['--fields', 'id', '--fields', 'name', self.test_id]
        self._test_show_resource(resource, cmd, self.test_id,
                                 args, ['id', 'name'])

    def test_delete_port(self):
        """Delete port: myid."""
        resource = 'port'
        cmd = port.DeletePort(test_cli20.MyApp(sys.stdout), None)
        myid = 'myid'
        args = [myid]
        self._test_delete_resource(resource, cmd, myid, args)


class CLITestV20PortXML(CLITestV20PortJSON):
    format = 'xml'

########NEW FILE########
__FILENAME__ = test_cli20_router
# Copyright 2012 VMware, Inc
# All Rights Reserved
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.
#

import sys

from neutronclient.common import exceptions
from neutronclient.neutron.v2_0 import router
from neutronclient.tests.unit import test_cli20


class CLITestV20RouterJSON(test_cli20.CLITestV20Base):
    def test_create_router(self):
        """Create router: router1."""
        resource = 'router'
        cmd = router.CreateRouter(test_cli20.MyApp(sys.stdout), None)
        name = 'router1'
        myid = 'myid'
        args = [name, ]
        position_names = ['name', ]
        position_values = [name, ]
        self._test_create_resource(resource, cmd, name, myid, args,
                                   position_names, position_values)

    def test_create_router_tenant(self):
        """Create router: --tenant_id tenantid myname."""
        resource = 'router'
        cmd = router.CreateRouter(test_cli20.MyApp(sys.stdout), None)
        name = 'myname'
        myid = 'myid'
        args = ['--tenant_id', 'tenantid', name]
        position_names = ['name', ]
        position_values = [name, ]
        self._test_create_resource(resource, cmd, name, myid, args,
                                   position_names, position_values,
                                   tenant_id='tenantid')

    def test_create_router_admin_state(self):
        """Create router: --admin_state_down myname."""
        resource = 'router'
        cmd = router.CreateRouter(test_cli20.MyApp(sys.stdout), None)
        name = 'myname'
        myid = 'myid'
        args = ['--admin_state_down', name, ]
        position_names = ['name', ]
        position_values = [name, ]
        self._test_create_resource(resource, cmd, name, myid, args,
                                   position_names, position_values,
                                   admin_state_up=False)

    def test_create_router_distributed(self):
        """Create router: --distributed myname."""
        resource = 'router'
        cmd = router.CreateRouter(test_cli20.MyApp(sys.stdout), None)
        name = 'myname'
        myid = 'myid'
        args = ['--distributed', name, ]
        position_names = ['name', ]
        position_values = [name, ]
        self._test_create_resource(resource, cmd, name, myid, args,
                                   position_names, position_values,
                                   distributed=True)

    def test_list_routers_detail(self):
        """list routers: -D."""
        resources = "routers"
        cmd = router.ListRouter(test_cli20.MyApp(sys.stdout), None)
        self._test_list_resources(resources, cmd, True)

    def test_list_routers_pagination(self):
        resources = "routers"
        cmd = router.ListRouter(test_cli20.MyApp(sys.stdout), None)
        self._test_list_resources_with_pagination(resources, cmd)

    def test_list_routers_sort(self):
        """list routers: --sort-key name --sort-key id --sort-key asc
        --sort-key desc
        """
        resources = "routers"
        cmd = router.ListRouter(test_cli20.MyApp(sys.stdout), None)
        self._test_list_resources(resources, cmd,
                                  sort_key=["name", "id"],
                                  sort_dir=["asc", "desc"])

    def test_list_routers_limit(self):
        """list routers: -P."""
        resources = "routers"
        cmd = router.ListRouter(test_cli20.MyApp(sys.stdout), None)
        self._test_list_resources(resources, cmd, page_size=1000)

    def test_update_router_exception(self):
        """Update router: myid."""
        resource = 'router'
        cmd = router.UpdateRouter(test_cli20.MyApp(sys.stdout), None)
        self.assertRaises(exceptions.CommandError, self._test_update_resource,
                          resource, cmd, 'myid', ['myid'], {})

    def test_update_router(self):
        """Update router: myid --name myname --tags a b."""
        resource = 'router'
        cmd = router.UpdateRouter(test_cli20.MyApp(sys.stdout), None)
        self._test_update_resource(resource, cmd, 'myid',
                                   ['myid', '--name', 'myname'],
                                   {'name': 'myname'}
                                   )

    def test_delete_router(self):
        """Delete router: myid."""
        resource = 'router'
        cmd = router.DeleteRouter(test_cli20.MyApp(sys.stdout), None)
        myid = 'myid'
        args = [myid]
        self._test_delete_resource(resource, cmd, myid, args)

    def test_show_router(self):
        """Show router: myid."""
        resource = 'router'
        cmd = router.ShowRouter(test_cli20.MyApp(sys.stdout), None)
        args = ['--fields', 'id', '--fields', 'name', self.test_id]
        self._test_show_resource(resource, cmd, self.test_id, args,
                                 ['id', 'name'])

    def _test_add_remove_interface(self, action, mode, cmd, args):
        resource = 'router'
        subcmd = '%s_router_interface' % action
        if mode == 'port':
            body = {'port_id': 'portid'}
        else:
            body = {'subnet_id': 'subnetid'}
        if action == 'add':
            retval = {'subnet_id': 'subnetid', 'port_id': 'portid'}
        else:
            retval = None
        self._test_update_resource_action(resource, cmd, 'myid',
                                          subcmd, args,
                                          body, retval)

    def test_add_interface_compat(self):
        """Add interface to router: myid subnetid."""
        cmd = router.AddInterfaceRouter(test_cli20.MyApp(sys.stdout), None)
        args = ['myid', 'subnetid']
        self._test_add_remove_interface('add', 'subnet', cmd, args)

    def test_add_interface_by_subnet(self):
        """Add interface to router: myid subnet=subnetid."""
        cmd = router.AddInterfaceRouter(test_cli20.MyApp(sys.stdout), None)
        args = ['myid', 'subnet=subnetid']
        self._test_add_remove_interface('add', 'subnet', cmd, args)

    def test_add_interface_by_port(self):
        """Add interface to router: myid port=portid."""
        cmd = router.AddInterfaceRouter(test_cli20.MyApp(sys.stdout), None)
        args = ['myid', 'port=portid']
        self._test_add_remove_interface('add', 'port', cmd, args)

    def test_del_interface_compat(self):
        """Delete interface from router: myid subnetid."""
        cmd = router.RemoveInterfaceRouter(test_cli20.MyApp(sys.stdout), None)
        args = ['myid', 'subnetid']
        self._test_add_remove_interface('remove', 'subnet', cmd, args)

    def test_del_interface_by_subnet(self):
        """Delete interface from router: myid subnet=subnetid."""
        cmd = router.RemoveInterfaceRouter(test_cli20.MyApp(sys.stdout), None)
        args = ['myid', 'subnet=subnetid']
        self._test_add_remove_interface('remove', 'subnet', cmd, args)

    def test_del_interface_by_port(self):
        """Delete interface from router: myid port=portid."""
        cmd = router.RemoveInterfaceRouter(test_cli20.MyApp(sys.stdout), None)
        args = ['myid', 'port=portid']
        self._test_add_remove_interface('remove', 'port', cmd, args)

    def test_set_gateway(self):
        """Set external gateway for router: myid externalid."""
        resource = 'router'
        cmd = router.SetGatewayRouter(test_cli20.MyApp(sys.stdout), None)
        args = ['myid', 'externalid']
        self._test_update_resource(resource, cmd, 'myid',
                                   args,
                                   {"external_gateway_info":
                                    {"network_id": "externalid"}}
                                   )

    def test_set_gateway_disable_snat(self):
        """set external gateway for router: myid externalid."""
        resource = 'router'
        cmd = router.SetGatewayRouter(test_cli20.MyApp(sys.stdout), None)
        args = ['myid', 'externalid', '--disable-snat']
        self._test_update_resource(resource, cmd, 'myid',
                                   args,
                                   {"external_gateway_info":
                                    {"network_id": "externalid",
                                     "enable_snat": False}}
                                   )

    def test_remove_gateway(self):
        """Remove external gateway from router: externalid."""
        resource = 'router'
        cmd = router.RemoveGatewayRouter(test_cli20.MyApp(sys.stdout), None)
        args = ['externalid']
        self._test_update_resource(resource, cmd, 'externalid',
                                   args, {"external_gateway_info": {}}
                                   )


class CLITestV20RouterXML(CLITestV20RouterJSON):
    format = 'xml'

########NEW FILE########
__FILENAME__ = test_cli20_securitygroup
#!/usr/bin/env python
# Copyright 2012 Red Hat
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import sys

import mox

from neutronclient.neutron.v2_0 import securitygroup
from neutronclient.tests.unit import test_cli20


class CLITestV20SecurityGroupsJSON(test_cli20.CLITestV20Base):
    def test_create_security_group(self):
        """Create security group: webservers."""
        resource = 'security_group'
        cmd = securitygroup.CreateSecurityGroup(
            test_cli20.MyApp(sys.stdout), None)
        name = 'webservers'
        myid = 'myid'
        args = [name, ]
        position_names = ['name']
        position_values = [name]
        self._test_create_resource(resource, cmd, name, myid, args,
                                   position_names, position_values)

    def test_create_security_group_tenant(self):
        """Create security group: webservers."""
        resource = 'security_group'
        cmd = securitygroup.CreateSecurityGroup(
            test_cli20.MyApp(sys.stdout), None)
        name = 'webservers'
        description = 'my webservers'
        myid = 'myid'
        args = ['--tenant_id', 'tenant_id', '--description', description, name]
        position_names = ['name', 'description']
        position_values = [name, description]
        self._test_create_resource(resource, cmd, name, myid, args,
                                   position_names, position_values,
                                   tenant_id='tenant_id')

    def test_create_security_group_with_description(self):
        """Create security group: webservers."""
        resource = 'security_group'
        cmd = securitygroup.CreateSecurityGroup(
            test_cli20.MyApp(sys.stdout), None)
        name = 'webservers'
        description = 'my webservers'
        myid = 'myid'
        args = [name, '--description', description]
        position_names = ['name', 'description']
        position_values = [name, description]
        self._test_create_resource(resource, cmd, name, myid, args,
                                   position_names, position_values)

    def test_list_security_groups(self):
        resources = "security_groups"
        cmd = securitygroup.ListSecurityGroup(
            test_cli20.MyApp(sys.stdout), None)
        self._test_list_resources(resources, cmd, True)

    def test_list_security_groups_pagination(self):
        resources = "security_groups"
        cmd = securitygroup.ListSecurityGroup(
            test_cli20.MyApp(sys.stdout), None)
        self._test_list_resources_with_pagination(resources, cmd)

    def test_list_security_groups_sort(self):
        resources = "security_groups"
        cmd = securitygroup.ListSecurityGroup(
            test_cli20.MyApp(sys.stdout), None)
        self._test_list_resources(resources, cmd,
                                  sort_key=["name", "id"],
                                  sort_dir=["asc", "desc"])

    def test_list_security_groups_limit(self):
        resources = "security_groups"
        cmd = securitygroup.ListSecurityGroup(
            test_cli20.MyApp(sys.stdout), None)
        self._test_list_resources(resources, cmd, page_size=1000)

    def test_show_security_group_id(self):
        resource = 'security_group'
        cmd = securitygroup.ShowSecurityGroup(
            test_cli20.MyApp(sys.stdout), None)
        args = ['--fields', 'id', self.test_id]
        self._test_show_resource(resource, cmd, self.test_id,
                                 args, ['id'])

    def test_show_security_group_id_name(self):
        resource = 'security_group'
        cmd = securitygroup.ShowSecurityGroup(
            test_cli20.MyApp(sys.stdout), None)
        args = ['--fields', 'id', '--fields', 'name', self.test_id]
        self._test_show_resource(resource, cmd, self.test_id,
                                 args, ['id', 'name'])

    def test_delete_security_group(self):
        """Delete security group: myid."""
        resource = 'security_group'
        cmd = securitygroup.DeleteSecurityGroup(
            test_cli20.MyApp(sys.stdout), None)
        myid = 'myid'
        args = [myid]
        self._test_delete_resource(resource, cmd, myid, args)

    def test_update_security_group(self):
        """Update security group: myid --name myname --description desc."""
        resource = 'security_group'
        cmd = securitygroup.UpdateSecurityGroup(
            test_cli20.MyApp(sys.stdout), None)
        self._test_update_resource(resource, cmd, 'myid',
                                   ['myid', '--name', 'myname',
                                    '--description', 'mydescription'],
                                   {'name': 'myname',
                                    'description': 'mydescription'}
                                   )

    def test_update_security_group_with_unicode(self):
        resource = 'security_group'
        cmd = securitygroup.UpdateSecurityGroup(
            test_cli20.MyApp(sys.stdout), None)
        self._test_update_resource(resource, cmd, 'myid',
                                   ['myid', '--name', u'\u7f51\u7edc',
                                    '--description', u'\u7f51\u7edc'],
                                   {'name': u'\u7f51\u7edc',
                                    'description': u'\u7f51\u7edc'}
                                   )

    def test_create_security_group_rule_full(self):
        """Create security group rule."""
        resource = 'security_group_rule'
        cmd = securitygroup.CreateSecurityGroupRule(
            test_cli20.MyApp(sys.stdout), None)
        myid = 'myid'
        direction = 'ingress'
        ethertype = 'IPv4'
        protocol = 'tcp'
        port_range_min = '22'
        port_range_max = '22'
        remote_ip_prefix = '10.0.0.0/24'
        security_group_id = '1'
        remote_group_id = '1'
        args = ['--remote_ip_prefix', remote_ip_prefix, '--direction',
                direction, '--ethertype', ethertype, '--protocol', protocol,
                '--port_range_min', port_range_min, '--port_range_max',
                port_range_max, '--remote_group_id', remote_group_id,
                security_group_id]
        position_names = ['remote_ip_prefix', 'direction', 'ethertype',
                          'protocol', 'port_range_min', 'port_range_max',
                          'remote_group_id', 'security_group_id']
        position_values = [remote_ip_prefix, direction, ethertype, protocol,
                           port_range_min, port_range_max, remote_group_id,
                           security_group_id]
        self._test_create_resource(resource, cmd, None, myid, args,
                                   position_names, position_values)

    def test_delete_security_group_rule(self):
        """Delete security group rule: myid."""
        resource = 'security_group_rule'
        cmd = securitygroup.DeleteSecurityGroupRule(
            test_cli20.MyApp(sys.stdout), None)
        myid = 'myid'
        args = [myid]
        self._test_delete_resource(resource, cmd, myid, args)

    def test_list_security_group_rules(self):
        resources = "security_group_rules"
        cmd = securitygroup.ListSecurityGroupRule(
            test_cli20.MyApp(sys.stdout), None)
        self.mox.StubOutWithMock(securitygroup.ListSecurityGroupRule,
                                 "extend_list")
        securitygroup.ListSecurityGroupRule.extend_list(mox.IsA(list),
                                                        mox.IgnoreArg())
        self._test_list_resources(resources, cmd, True)

    def test_list_security_group_rules_pagination(self):
        resources = "security_group_rules"
        cmd = securitygroup.ListSecurityGroupRule(
            test_cli20.MyApp(sys.stdout), None)
        self.mox.StubOutWithMock(securitygroup.ListSecurityGroupRule,
                                 "extend_list")
        securitygroup.ListSecurityGroupRule.extend_list(mox.IsA(list),
                                                        mox.IgnoreArg())
        self._test_list_resources_with_pagination(resources, cmd)

    def test_list_security_group_rules_sort(self):
        resources = "security_group_rules"
        cmd = securitygroup.ListSecurityGroupRule(
            test_cli20.MyApp(sys.stdout), None)
        self.mox.StubOutWithMock(securitygroup.ListSecurityGroupRule,
                                 "extend_list")
        securitygroup.ListSecurityGroupRule.extend_list(mox.IsA(list),
                                                        mox.IgnoreArg())
        self._test_list_resources(resources, cmd,
                                  sort_key=["name", "id"],
                                  sort_dir=["asc", "desc"])

    def test_list_security_group_rules_limit(self):
        resources = "security_group_rules"
        cmd = securitygroup.ListSecurityGroupRule(
            test_cli20.MyApp(sys.stdout), None)
        self.mox.StubOutWithMock(securitygroup.ListSecurityGroupRule,
                                 "extend_list")
        securitygroup.ListSecurityGroupRule.extend_list(mox.IsA(list),
                                                        mox.IgnoreArg())
        self._test_list_resources(resources, cmd, page_size=1000)

    def test_show_security_group_rule(self):
        resource = 'security_group_rule'
        cmd = securitygroup.ShowSecurityGroupRule(
            test_cli20.MyApp(sys.stdout), None)
        args = ['--fields', 'id', self.test_id]
        self._test_show_resource(resource, cmd, self.test_id,
                                 args, ['id'])

    def _test_list_security_group_rules_extend(self, data=None, expected=None,
                                               args=[], conv=True,
                                               query_field=False):
        def setup_list_stub(resources, data, query):
            reses = {resources: data}
            resstr = self.client.serialize(reses)
            resp = (test_cli20.MyResp(200), resstr)
            path = getattr(self.client, resources + '_path')
            self.client.httpclient.request(
                test_cli20.end_url(path, query), 'GET',
                body=None,
                headers=mox.ContainsKeyValue(
                    'X-Auth-Token', test_cli20.TOKEN)).AndReturn(resp)

        # Setup the default data
        _data = {'cols': ['id', 'security_group_id', 'remote_group_id'],
                 'data': [('ruleid1', 'myid1', 'myid1'),
                          ('ruleid2', 'myid2', 'myid3'),
                          ('ruleid3', 'myid2', 'myid2')]}
        _expected = {'cols': ['id', 'security_group', 'remote_group'],
                     'data': [('ruleid1', 'group1', 'group1'),
                              ('ruleid2', 'group2', 'group3'),
                              ('ruleid3', 'group2', 'group2')]}
        if data is None:
            data = _data
        list_data = [dict(zip(data['cols'], d)) for d in data['data']]
        if expected is None:
            expected = {}
        expected['cols'] = expected.get('cols', _expected['cols'])
        expected['data'] = expected.get('data', _expected['data'])

        cmd = securitygroup.ListSecurityGroupRule(
            test_cli20.MyApp(sys.stdout), None)
        self.mox.StubOutWithMock(cmd, 'get_client')
        self.mox.StubOutWithMock(self.client.httpclient, 'request')
        cmd.get_client().AndReturn(self.client)
        query = ''
        if query_field:
            query = '&'.join(['fields=' + f for f in data['cols']])
        setup_list_stub('security_group_rules', list_data, query)
        if conv:
            cmd.get_client().AndReturn(self.client)
            sec_ids = set()
            for n in data['data']:
                sec_ids.add(n[1])
                sec_ids.add(n[2])
            filters = ''
            for id in sec_ids:
                filters = filters + "&id=%s" % id
            setup_list_stub('security_groups',
                            [{'id': 'myid1', 'name': 'group1'},
                             {'id': 'myid2', 'name': 'group2'},
                             {'id': 'myid3', 'name': 'group3'}],
                            query='fields=id&fields=name' + filters)
        self.mox.ReplayAll()

        cmd_parser = cmd.get_parser('list_security_group_rules')
        parsed_args = cmd_parser.parse_args(args)
        result = cmd.get_data(parsed_args)
        self.mox.VerifyAll()
        self.mox.UnsetStubs()
        # Check columns
        self.assertEqual(result[0], expected['cols'])
        # Check data
        _result = [x for x in result[1]]
        self.assertEqual(len(_result), len(expected['data']))
        for res, exp in zip(_result, expected['data']):
            self.assertEqual(len(res), len(exp))
            self.assertEqual(res, exp)

    def test_list_security_group_rules_extend_source_id(self):
        self._test_list_security_group_rules_extend()

    def test_list_security_group_rules_extend_no_nameconv(self):
        expected = {'cols': ['id', 'security_group_id', 'remote_group_id'],
                    'data': [('ruleid1', 'myid1', 'myid1'),
                             ('ruleid2', 'myid2', 'myid3'),
                             ('ruleid3', 'myid2', 'myid2')]}
        args = ['--no-nameconv']
        self._test_list_security_group_rules_extend(expected=expected,
                                                    args=args, conv=False)

    def test_list_security_group_rules_extend_with_columns(self):
        args = '-c id -c security_group_id -c remote_group_id'.split()
        self._test_list_security_group_rules_extend(args=args)

    def test_list_security_group_rules_extend_with_columns_no_id(self):
        args = '-c id -c security_group -c remote_group'.split()
        self._test_list_security_group_rules_extend(args=args)

    def test_list_security_group_rules_extend_with_fields(self):
        args = '-F id -F security_group_id -F remote_group_id'.split()
        self._test_list_security_group_rules_extend(args=args,
                                                    query_field=True)

    def test_list_security_group_rules_extend_with_fields_no_id(self):
        args = '-F id -F security_group -F remote_group'.split()
        self._test_list_security_group_rules_extend(args=args,
                                                    query_field=True)


class CLITestV20SecurityGroupsXML(CLITestV20SecurityGroupsJSON):
    format = 'xml'

########NEW FILE########
__FILENAME__ = test_cli20_servicetype
# Copyright 2013 Mirantis Inc.
# All Rights Reserved
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.
#
# @author: Eugene Nikanorov, Mirantis Inc.
#

import sys

from neutronclient.neutron.v2_0 import servicetype
from neutronclient.tests.unit import test_cli20


class CLITestV20ServiceProvidersJSON(test_cli20.CLITestV20Base):
    id_field = "name"

    def setUp(self):
        super(CLITestV20ServiceProvidersJSON, self).setUp(
            plurals={'tags': 'tag'}
        )

    def test_list_service_providers(self):
        resources = "service_providers"
        cmd = servicetype.ListServiceProvider(test_cli20.MyApp(sys.stdout),
                                              None)
        self._test_list_resources(resources, cmd, True)

    def test_list_service_providers_pagination(self):
        resources = "service_providers"
        cmd = servicetype.ListServiceProvider(test_cli20.MyApp(sys.stdout),
                                              None)
        self._test_list_resources_with_pagination(resources, cmd)

    def test_list_service_providers_sort(self):
        resources = "service_providers"
        cmd = servicetype.ListServiceProvider(test_cli20.MyApp(sys.stdout),
                                              None)
        self._test_list_resources(resources, cmd,
                                  sort_key=["name"],
                                  sort_dir=["asc", "desc"])

    def test_list_service_providers_limit(self):
        resources = "service_providers"
        cmd = servicetype.ListServiceProvider(test_cli20.MyApp(sys.stdout),
                                              None)
        self._test_list_resources(resources, cmd, page_size=1000)


class CLITestV20ServiceProvidersXML(CLITestV20ServiceProvidersJSON):
    format = 'xml'

########NEW FILE########
__FILENAME__ = test_cli20_subnet
# Copyright 2012 OpenStack Foundation.
# All Rights Reserved
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.
#

import sys

from neutronclient.neutron.v2_0 import subnet
from neutronclient.tests.unit import test_cli20


class CLITestV20SubnetJSON(test_cli20.CLITestV20Base):
    def setUp(self):
        super(CLITestV20SubnetJSON, self).setUp(plurals={'tags': 'tag'})

    def test_create_subnet(self):
        """Create subnet: --gateway gateway netid cidr."""
        resource = 'subnet'
        cmd = subnet.CreateSubnet(test_cli20.MyApp(sys.stdout), None)
        name = 'myname'
        myid = 'myid'
        netid = 'netid'
        cidr = 'cidrvalue'
        gateway = 'gatewayvalue'
        args = ['--gateway', gateway, netid, cidr]
        position_names = ['ip_version', 'network_id', 'cidr', 'gateway_ip']
        position_values = [4, netid, cidr, gateway]
        self._test_create_resource(resource, cmd, name, myid, args,
                                   position_names, position_values)

    def test_create_subnet_with_no_gateway(self):
        """Create subnet: --no-gateway netid cidr."""
        resource = 'subnet'
        cmd = subnet.CreateSubnet(test_cli20.MyApp(sys.stdout), None)
        name = 'myname'
        myid = 'myid'
        netid = 'netid'
        cidr = 'cidrvalue'
        args = ['--no-gateway', netid, cidr]
        position_names = ['ip_version', 'network_id', 'cidr', 'gateway_ip']
        position_values = [4, netid, cidr, None]
        self._test_create_resource(resource, cmd, name, myid, args,
                                   position_names, position_values)

    def test_create_subnet_with_bad_gateway_option(self):
        """Create sbunet: --no-gateway netid cidr."""
        resource = 'subnet'
        cmd = subnet.CreateSubnet(test_cli20.MyApp(sys.stdout), None)
        name = 'myname'
        myid = 'myid'
        netid = 'netid'
        cidr = 'cidrvalue'
        gateway = 'gatewayvalue'
        args = ['--gateway', gateway, '--no-gateway', netid, cidr]
        position_names = ['ip_version', 'network_id', 'cidr', 'gateway_ip']
        position_values = [4, netid, cidr, None]
        try:
            self._test_create_resource(resource, cmd, name, myid, args,
                                       position_names, position_values)
        except Exception:
            return
        self.fail('No exception for bad gateway option')

    def test_create_subnet_tenant(self):
        """Create subnet: --tenant_id tenantid netid cidr."""
        resource = 'subnet'
        cmd = subnet.CreateSubnet(test_cli20.MyApp(sys.stdout), None)
        name = 'myname'
        myid = 'myid'
        netid = 'netid'
        cidr = 'prefixvalue'
        args = ['--tenant_id', 'tenantid', netid, cidr]
        position_names = ['ip_version', 'network_id', 'cidr']
        position_values = [4, netid, cidr]
        self._test_create_resource(resource, cmd, name, myid, args,
                                   position_names, position_values,
                                   tenant_id='tenantid')

    def test_create_subnet_tags(self):
        """Create subnet: netid cidr --tags a b."""
        resource = 'subnet'
        cmd = subnet.CreateSubnet(test_cli20.MyApp(sys.stdout), None)
        name = 'myname'
        myid = 'myid'
        netid = 'netid'
        cidr = 'prefixvalue'
        args = [netid, cidr, '--tags', 'a', 'b']
        position_names = ['ip_version', 'network_id', 'cidr']
        position_values = [4, netid, cidr]
        self._test_create_resource(resource, cmd, name, myid, args,
                                   position_names, position_values,
                                   tags=['a', 'b'])

    def test_create_subnet_allocation_pool(self):
        """Create subnet: --tenant_id tenantid <allocation_pool> netid cidr.
        The <allocation_pool> is --allocation_pool start=1.1.1.10,end=1.1.1.20
        """
        resource = 'subnet'
        cmd = subnet.CreateSubnet(test_cli20.MyApp(sys.stdout), None)
        name = 'myname'
        myid = 'myid'
        netid = 'netid'
        cidr = 'prefixvalue'
        args = ['--tenant_id', 'tenantid',
                '--allocation_pool', 'start=1.1.1.10,end=1.1.1.20',
                netid, cidr]
        position_names = ['ip_version', 'allocation_pools', 'network_id',
                          'cidr']
        pool = [{'start': '1.1.1.10', 'end': '1.1.1.20'}]
        position_values = [4, pool, netid, cidr]
        self._test_create_resource(resource, cmd, name, myid, args,
                                   position_names, position_values,
                                   tenant_id='tenantid')

    def test_create_subnet_allocation_pools(self):
        """Create subnet: --tenant-id tenantid <pools> netid cidr.
        The <pools> are --allocation_pool start=1.1.1.10,end=1.1.1.20 and
        --allocation_pool start=1.1.1.30,end=1.1.1.40
        """
        resource = 'subnet'
        cmd = subnet.CreateSubnet(test_cli20.MyApp(sys.stdout), None)
        name = 'myname'
        myid = 'myid'
        netid = 'netid'
        cidr = 'prefixvalue'
        args = ['--tenant_id', 'tenantid',
                '--allocation_pool', 'start=1.1.1.10,end=1.1.1.20',
                '--allocation_pool', 'start=1.1.1.30,end=1.1.1.40',
                netid, cidr]
        position_names = ['ip_version', 'allocation_pools', 'network_id',
                          'cidr']
        pools = [{'start': '1.1.1.10', 'end': '1.1.1.20'},
                 {'start': '1.1.1.30', 'end': '1.1.1.40'}]
        position_values = [4, pools, netid, cidr]
        self._test_create_resource(resource, cmd, name, myid, args,
                                   position_names, position_values,
                                   tenant_id='tenantid')

    def test_create_subnet_host_route(self):
        """Create subnet: --tenant_id tenantid <host_route> netid cidr.
        The <host_route> is
        --host-route destination=172.16.1.0/24,nexthop=1.1.1.20
        """
        resource = 'subnet'
        cmd = subnet.CreateSubnet(test_cli20.MyApp(sys.stdout), None)
        name = 'myname'
        myid = 'myid'
        netid = 'netid'
        cidr = 'prefixvalue'
        args = ['--tenant_id', 'tenantid',
                '--host-route', 'destination=172.16.1.0/24,nexthop=1.1.1.20',
                netid, cidr]
        position_names = ['ip_version', 'host_routes', 'network_id',
                          'cidr']
        route = [{'destination': '172.16.1.0/24', 'nexthop': '1.1.1.20'}]
        position_values = [4, route, netid, cidr]
        self._test_create_resource(resource, cmd, name, myid, args,
                                   position_names, position_values,
                                   tenant_id='tenantid')

    def test_create_subnet_host_routes(self):
        """Create subnet: --tenant-id tenantid <host_routes> netid cidr.
        The <host_routes> are
        --host-route destination=172.16.1.0/24,nexthop=1.1.1.20 and
        --host-route destination=172.17.7.0/24,nexthop=1.1.1.40
        """
        resource = 'subnet'
        cmd = subnet.CreateSubnet(test_cli20.MyApp(sys.stdout), None)
        name = 'myname'
        myid = 'myid'
        netid = 'netid'
        cidr = 'prefixvalue'
        args = ['--tenant_id', 'tenantid',
                '--host-route', 'destination=172.16.1.0/24,nexthop=1.1.1.20',
                '--host-route', 'destination=172.17.7.0/24,nexthop=1.1.1.40',
                netid, cidr]
        position_names = ['ip_version', 'host_routes', 'network_id',
                          'cidr']
        routes = [{'destination': '172.16.1.0/24', 'nexthop': '1.1.1.20'},
                  {'destination': '172.17.7.0/24', 'nexthop': '1.1.1.40'}]
        position_values = [4, routes, netid, cidr]
        self._test_create_resource(resource, cmd, name, myid, args,
                                   position_names, position_values,
                                   tenant_id='tenantid')

    def test_create_subnet_dns_nameservers(self):
        """Create subnet: --tenant-id tenantid <dns-nameservers> netid cidr.
        The <dns-nameservers> are
        --dns-nameserver 1.1.1.20 and --dns-nameserver 1.1.1.40
        """
        resource = 'subnet'
        cmd = subnet.CreateSubnet(test_cli20.MyApp(sys.stdout), None)
        name = 'myname'
        myid = 'myid'
        netid = 'netid'
        cidr = 'prefixvalue'
        args = ['--tenant_id', 'tenantid',
                '--dns-nameserver', '1.1.1.20',
                '--dns-nameserver', '1.1.1.40',
                netid, cidr]
        position_names = ['ip_version', 'dns_nameservers', 'network_id',
                          'cidr']
        nameservers = ['1.1.1.20', '1.1.1.40']
        position_values = [4, nameservers, netid, cidr]
        self._test_create_resource(resource, cmd, name, myid, args,
                                   position_names, position_values,
                                   tenant_id='tenantid')

    def test_create_subnet_with_disable_dhcp(self):
        """Create subnet: --tenant-id tenantid --disable-dhcp netid cidr."""
        resource = 'subnet'
        cmd = subnet.CreateSubnet(test_cli20.MyApp(sys.stdout), None)
        name = 'myname'
        myid = 'myid'
        netid = 'netid'
        cidr = 'prefixvalue'
        args = ['--tenant_id', 'tenantid',
                '--disable-dhcp',
                netid, cidr]
        position_names = ['ip_version', 'enable_dhcp', 'network_id',
                          'cidr']
        position_values = [4, False, netid, cidr]
        self._test_create_resource(resource, cmd, name, myid, args,
                                   position_names, position_values,
                                   tenant_id='tenantid')

    def test_create_subnet_merge_single_plurar(self):
        resource = 'subnet'
        cmd = subnet.CreateSubnet(test_cli20.MyApp(sys.stdout), None)
        name = 'myname'
        myid = 'myid'
        netid = 'netid'
        cidr = 'prefixvalue'
        args = ['--tenant_id', 'tenantid',
                '--allocation-pool', 'start=1.1.1.10,end=1.1.1.20',
                netid, cidr,
                '--allocation-pools', 'list=true', 'type=dict',
                'start=1.1.1.30,end=1.1.1.40']
        position_names = ['ip_version', 'allocation_pools', 'network_id',
                          'cidr']
        pools = [{'start': '1.1.1.10', 'end': '1.1.1.20'},
                 {'start': '1.1.1.30', 'end': '1.1.1.40'}]
        position_values = [4, pools, netid, cidr]
        self._test_create_resource(resource, cmd, name, myid, args,
                                   position_names, position_values,
                                   tenant_id='tenantid')

    def test_create_subnet_merge_plurar(self):
        resource = 'subnet'
        cmd = subnet.CreateSubnet(test_cli20.MyApp(sys.stdout), None)
        name = 'myname'
        myid = 'myid'
        netid = 'netid'
        cidr = 'prefixvalue'
        args = ['--tenant_id', 'tenantid',
                netid, cidr,
                '--allocation-pools', 'list=true', 'type=dict',
                'start=1.1.1.30,end=1.1.1.40']
        position_names = ['ip_version', 'allocation_pools', 'network_id',
                          'cidr']
        pools = [{'start': '1.1.1.30', 'end': '1.1.1.40'}]
        position_values = [4, pools, netid, cidr]
        self._test_create_resource(resource, cmd, name, myid, args,
                                   position_names, position_values,
                                   tenant_id='tenantid')

    def test_create_subnet_merge_single_single(self):
        resource = 'subnet'
        cmd = subnet.CreateSubnet(test_cli20.MyApp(sys.stdout), None)
        name = 'myname'
        myid = 'myid'
        netid = 'netid'
        cidr = 'prefixvalue'
        args = ['--tenant_id', 'tenantid',
                '--allocation-pool', 'start=1.1.1.10,end=1.1.1.20',
                netid, cidr,
                '--allocation-pool',
                'start=1.1.1.30,end=1.1.1.40']
        position_names = ['ip_version', 'allocation_pools', 'network_id',
                          'cidr']
        pools = [{'start': '1.1.1.10', 'end': '1.1.1.20'},
                 {'start': '1.1.1.30', 'end': '1.1.1.40'}]
        position_values = [4, pools, netid, cidr]
        self._test_create_resource(resource, cmd, name, myid, args,
                                   position_names, position_values,
                                   tenant_id='tenantid')

    def test_list_subnets_detail(self):
        """List subnets: -D."""
        resources = "subnets"
        cmd = subnet.ListSubnet(test_cli20.MyApp(sys.stdout), None)
        self._test_list_resources(resources, cmd, True)

    def test_list_subnets_tags(self):
        """List subnets: -- --tags a b."""
        resources = "subnets"
        cmd = subnet.ListSubnet(test_cli20.MyApp(sys.stdout), None)
        self._test_list_resources(resources, cmd, tags=['a', 'b'])

    def test_list_subnets_known_option_after_unknown(self):
        """List subnets: -- --tags a b --request-format xml."""
        resources = "subnets"
        cmd = subnet.ListSubnet(test_cli20.MyApp(sys.stdout), None)
        self._test_list_resources(resources, cmd, tags=['a', 'b'])

    def test_list_subnets_detail_tags(self):
        """List subnets: -D -- --tags a b."""
        resources = "subnets"
        cmd = subnet.ListSubnet(test_cli20.MyApp(sys.stdout), None)
        self._test_list_resources(resources, cmd, detail=True, tags=['a', 'b'])

    def test_list_subnets_fields(self):
        """List subnets: --fields a --fields b -- --fields c d."""
        resources = "subnets"
        cmd = subnet.ListSubnet(test_cli20.MyApp(sys.stdout), None)
        self._test_list_resources(resources, cmd,
                                  fields_1=['a', 'b'], fields_2=['c', 'd'])

    def test_list_subnets_pagination(self):
        resources = "subnets"
        cmd = subnet.ListSubnet(test_cli20.MyApp(sys.stdout), None)
        self._test_list_resources_with_pagination(resources, cmd)

    def test_list_subnets_sort(self):
        """List subnets: --sort-key name --sort-key id --sort-key asc
        --sort-key desc
        """
        resources = "subnets"
        cmd = subnet.ListSubnet(test_cli20.MyApp(sys.stdout), None)
        self._test_list_resources(resources, cmd,
                                  sort_key=["name", "id"],
                                  sort_dir=["asc", "desc"])

    def test_list_subnets_limit(self):
        """List subnets: -P."""
        resources = "subnets"
        cmd = subnet.ListSubnet(test_cli20.MyApp(sys.stdout), None)
        self._test_list_resources(resources, cmd, page_size=1000)

    def test_update_subnet(self):
        """Update subnet: myid --name myname --tags a b."""
        resource = 'subnet'
        cmd = subnet.UpdateSubnet(test_cli20.MyApp(sys.stdout), None)
        self._test_update_resource(resource, cmd, 'myid',
                                   ['myid', '--name', 'myname',
                                    '--tags', 'a', 'b'],
                                   {'name': 'myname', 'tags': ['a', 'b'], }
                                   )

    def test_update_subnet_known_option_before_id(self):
        """Update subnet: --request-format json myid --name myname."""
        # --request-format xml is known option
        resource = 'subnet'
        cmd = subnet.UpdateSubnet(test_cli20.MyApp(sys.stdout), None)
        self._test_update_resource(resource, cmd, 'myid',
                                   ['--request-format', 'json',
                                    'myid', '--name', 'myname'],
                                   {'name': 'myname', }
                                   )

    def test_update_subnet_known_option_after_id(self):
        """Update subnet: myid --name myname --request-format json."""
        # --request-format xml is known option
        resource = 'subnet'
        cmd = subnet.UpdateSubnet(test_cli20.MyApp(sys.stdout), None)
        self._test_update_resource(resource, cmd, 'myid',
                                   ['myid', '--name', 'myname',
                                    '--request-format', 'json'],
                                   {'name': 'myname', }
                                   )

    def test_show_subnet(self):
        """Show subnet: --fields id --fields name myid."""
        resource = 'subnet'
        cmd = subnet.ShowSubnet(test_cli20.MyApp(sys.stdout), None)
        args = ['--fields', 'id', '--fields', 'name', self.test_id]
        self._test_show_resource(resource, cmd, self.test_id,
                                 args, ['id', 'name'])

    def test_delete_subnet(self):
        """Delete subnet: subnetid."""
        resource = 'subnet'
        cmd = subnet.DeleteSubnet(test_cli20.MyApp(sys.stdout), None)
        myid = 'myid'
        args = [myid]
        self._test_delete_resource(resource, cmd, myid, args)


class CLITestV20SubnetXML(CLITestV20SubnetJSON):
    format = 'xml'

########NEW FILE########
__FILENAME__ = test_http
# Copyright (C) 2013 OpenStack Foundation.
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import mox
import testtools

from neutronclient.client import HTTPClient
from neutronclient.common import exceptions
from neutronclient.tests.unit.test_cli20 import MyResp


AUTH_TOKEN = 'test_token'
END_URL = 'test_url'
METHOD = 'GET'
URL = 'http://test.test:1234/v2.0/test'


class TestHTTPClient(testtools.TestCase):
    def setUp(self):
        super(TestHTTPClient, self).setUp()

        self.mox = mox.Mox()
        self.mox.StubOutWithMock(HTTPClient, 'request')
        self.addCleanup(self.mox.UnsetStubs)

        self.http = HTTPClient(token=AUTH_TOKEN, endpoint_url=END_URL)

    def test_request_error(self):
        HTTPClient.request(
            URL, METHOD, headers=mox.IgnoreArg()
        ).AndRaise(Exception('error msg'))
        self.mox.ReplayAll()

        self.assertRaises(
            exceptions.ConnectionFailed,
            self.http._cs_request,
            URL, METHOD
        )
        self.mox.VerifyAll()

    def test_request_success(self):
        rv_should_be = MyResp(200), 'test content'

        HTTPClient.request(
            URL, METHOD, headers=mox.IgnoreArg()
        ).AndReturn(rv_should_be)
        self.mox.ReplayAll()

        self.assertEqual(rv_should_be, self.http._cs_request(URL, METHOD))
        self.mox.VerifyAll()

    def test_request_unauthorized(self):
        rv_should_be = MyResp(401), 'unauthorized message'
        HTTPClient.request(
            URL, METHOD, headers=mox.IgnoreArg()
        ).AndReturn(rv_should_be)
        self.mox.ReplayAll()

        e = self.assertRaises(exceptions.Unauthorized,
                              self.http._cs_request, URL, METHOD)
        self.assertEqual('unauthorized message', e.message)
        self.mox.VerifyAll()

    def test_request_forbidden_is_returned_to_caller(self):
        rv_should_be = MyResp(403), 'forbidden message'
        HTTPClient.request(
            URL, METHOD, headers=mox.IgnoreArg()
        ).AndReturn(rv_should_be)
        self.mox.ReplayAll()

        self.assertEqual(rv_should_be, self.http._cs_request(URL, METHOD))
        self.mox.VerifyAll()

########NEW FILE########
__FILENAME__ = test_name_or_id
# Copyright 2012 OpenStack Foundation.
# All Rights Reserved
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.
#

import uuid

import mox
import testtools

from neutronclient.common import exceptions
from neutronclient.neutron import v2_0 as neutronV20
from neutronclient.tests.unit import test_cli20
from neutronclient.v2_0 import client


class CLITestNameorID(testtools.TestCase):

    def setUp(self):
        """Prepare the test environment."""
        super(CLITestNameorID, self).setUp()
        self.mox = mox.Mox()
        self.endurl = test_cli20.ENDURL
        self.client = client.Client(token=test_cli20.TOKEN,
                                    endpoint_url=self.endurl)
        self.addCleanup(self.mox.VerifyAll)
        self.addCleanup(self.mox.UnsetStubs)

    def test_get_id_from_id(self):
        _id = str(uuid.uuid4())
        reses = {'networks': [{'id': _id, }, ], }
        resstr = self.client.serialize(reses)
        self.mox.StubOutWithMock(self.client.httpclient, "request")
        path = getattr(self.client, "networks_path")
        self.client.httpclient.request(
            test_cli20.end_url(path, "fields=id&id=" + _id), 'GET',
            body=None,
            headers=mox.ContainsKeyValue('X-Auth-Token', test_cli20.TOKEN)
        ).AndReturn((test_cli20.MyResp(200), resstr))
        self.mox.ReplayAll()
        returned_id = neutronV20.find_resourceid_by_name_or_id(
            self.client, 'network', _id)
        self.assertEqual(_id, returned_id)

    def test_get_id_from_id_then_name_empty(self):
        _id = str(uuid.uuid4())
        reses = {'networks': [{'id': _id, }, ], }
        resstr = self.client.serialize(reses)
        resstr1 = self.client.serialize({'networks': []})
        self.mox.StubOutWithMock(self.client.httpclient, "request")
        path = getattr(self.client, "networks_path")
        self.client.httpclient.request(
            test_cli20.end_url(path, "fields=id&id=" + _id), 'GET',
            body=None,
            headers=mox.ContainsKeyValue('X-Auth-Token', test_cli20.TOKEN)
        ).AndReturn((test_cli20.MyResp(200), resstr1))
        self.client.httpclient.request(
            test_cli20.end_url(path, "fields=id&name=" + _id), 'GET',
            body=None,
            headers=mox.ContainsKeyValue('X-Auth-Token', test_cli20.TOKEN)
        ).AndReturn((test_cli20.MyResp(200), resstr))
        self.mox.ReplayAll()
        returned_id = neutronV20.find_resourceid_by_name_or_id(
            self.client, 'network', _id)
        self.assertEqual(_id, returned_id)

    def test_get_id_from_name(self):
        name = 'myname'
        _id = str(uuid.uuid4())
        reses = {'networks': [{'id': _id, }, ], }
        resstr = self.client.serialize(reses)
        self.mox.StubOutWithMock(self.client.httpclient, "request")
        path = getattr(self.client, "networks_path")
        self.client.httpclient.request(
            test_cli20.end_url(path, "fields=id&name=" + name), 'GET',
            body=None,
            headers=mox.ContainsKeyValue('X-Auth-Token', test_cli20.TOKEN)
        ).AndReturn((test_cli20.MyResp(200), resstr))
        self.mox.ReplayAll()
        returned_id = neutronV20.find_resourceid_by_name_or_id(
            self.client, 'network', name)
        self.assertEqual(_id, returned_id)

    def test_get_id_from_name_multiple(self):
        name = 'myname'
        reses = {'networks': [{'id': str(uuid.uuid4())},
                              {'id': str(uuid.uuid4())}]}
        resstr = self.client.serialize(reses)
        self.mox.StubOutWithMock(self.client.httpclient, "request")
        path = getattr(self.client, "networks_path")
        self.client.httpclient.request(
            test_cli20.end_url(path, "fields=id&name=" + name), 'GET',
            body=None,
            headers=mox.ContainsKeyValue('X-Auth-Token', test_cli20.TOKEN)
        ).AndReturn((test_cli20.MyResp(200), resstr))
        self.mox.ReplayAll()
        try:
            neutronV20.find_resourceid_by_name_or_id(
                self.client, 'network', name)
        except exceptions.NeutronClientNoUniqueMatch as ex:
            self.assertIn('Multiple', ex.message)

    def test_get_id_from_name_notfound(self):
        name = 'myname'
        reses = {'networks': []}
        resstr = self.client.serialize(reses)
        self.mox.StubOutWithMock(self.client.httpclient, "request")
        path = getattr(self.client, "networks_path")
        self.client.httpclient.request(
            test_cli20.end_url(path, "fields=id&name=" + name), 'GET',
            body=None,
            headers=mox.ContainsKeyValue('X-Auth-Token', test_cli20.TOKEN)
        ).AndReturn((test_cli20.MyResp(200), resstr))
        self.mox.ReplayAll()
        try:
            neutronV20.find_resourceid_by_name_or_id(
                self.client, 'network', name)
        except exceptions.NeutronClientException as ex:
            self.assertIn('Unable to find', ex.message)
            self.assertEqual(404, ex.status_code)

########NEW FILE########
__FILENAME__ = test_quota
#!/usr/bin/env python
# Copyright (C) 2013 Yahoo! Inc.
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import sys

from neutronclient.common import exceptions
from neutronclient.neutron.v2_0 import quota as test_quota
from neutronclient.tests.unit import test_cli20


class CLITestV20Quota(test_cli20.CLITestV20Base):
    def test_show_quota(self):
        resource = 'quota'
        cmd = test_quota.ShowQuota(
            test_cli20.MyApp(sys.stdout), None)
        args = ['--tenant-id', self.test_id]
        self._test_show_resource(resource, cmd, self.test_id, args)

    def test_update_quota(self):
        resource = 'quota'
        cmd = test_quota.UpdateQuota(
            test_cli20.MyApp(sys.stdout), None)
        args = ['--tenant-id', self.test_id, '--network', 'test']
        self.assertRaises(
            exceptions.NeutronClientException, self._test_update_resource,
            resource, cmd, self.test_id, args=args,
            extrafields={'network': 'new'})

    def test_delete_quota_get_parser(self):
        cmd = test_cli20.MyApp(sys.stdout)
        test_quota.DeleteQuota(cmd, None).get_parser(cmd)

########NEW FILE########
__FILENAME__ = test_shell
# Copyright (C) 2013 Yahoo! Inc.
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import argparse
import cStringIO
import logging
import os
import re
import sys

import fixtures
import mox
import testtools
from testtools import matchers

from neutronclient.common import clientmanager
from neutronclient import shell as openstack_shell


DEFAULT_USERNAME = 'username'
DEFAULT_PASSWORD = 'password'
DEFAULT_TENANT_ID = 'tenant_id'
DEFAULT_TENANT_NAME = 'tenant_name'
DEFAULT_AUTH_URL = 'http://127.0.0.1:5000/v2.0/'
DEFAULT_TOKEN = '3bcc3d3a03f44e3d8377f9247b0ad155'
DEFAULT_URL = 'http://quantum.example.org:9696/'


class ShellTest(testtools.TestCase):

    FAKE_ENV = {
        'OS_USERNAME': DEFAULT_USERNAME,
        'OS_PASSWORD': DEFAULT_PASSWORD,
        'OS_TENANT_ID': DEFAULT_TENANT_ID,
        'OS_TENANT_NAME': DEFAULT_TENANT_NAME,
        'OS_AUTH_URL': DEFAULT_AUTH_URL}

    # Patch os.environ to avoid required auth info.
    def setUp(self):
        super(ShellTest, self).setUp()
        self.mox = mox.Mox()
        for var in self.FAKE_ENV:
            self.useFixture(
                fixtures.EnvironmentVariable(
                    var, self.FAKE_ENV[var]))

    def shell(self, argstr, check=False):
        orig = (sys.stdout, sys.stderr)
        clean_env = {}
        _old_env, os.environ = os.environ, clean_env.copy()
        try:
            sys.stdout = cStringIO.StringIO()
            sys.stderr = cStringIO.StringIO()
            _shell = openstack_shell.NeutronShell('2.0')
            _shell.run(argstr.split())
        except SystemExit:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            self.assertEqual(exc_value.code, 0)
        finally:
            stdout = sys.stdout.getvalue()
            stderr = sys.stderr.getvalue()
            sys.stdout.close()
            sys.stderr.close()
            sys.stdout, sys.stderr = orig
            os.environ = _old_env
        return stdout, stderr

    def test_run_unknown_command(self):
        self.useFixture(fixtures.FakeLogger(level=logging.DEBUG))
        stdout, stderr = self.shell('fake', check=True)
        self.assertFalse(stdout)
        self.assertEqual("Unknown command ['fake']", stderr.strip())

    def test_help(self):
        required = 'usage:'
        help_text, stderr = self.shell('help')
        self.assertThat(
            help_text,
            matchers.MatchesRegex(required))
        self.assertFalse(stderr)

    def test_help_on_subcommand(self):
        required = [
            '.*?^usage: .* quota-list']
        stdout, stderr = self.shell('help quota-list')
        for r in required:
            self.assertThat(
                stdout,
                matchers.MatchesRegex(r, re.DOTALL | re.MULTILINE))
        self.assertFalse(stderr)

    def test_help_command(self):
        required = 'usage:'
        help_text, stderr = self.shell('help network-create')
        self.assertThat(
            help_text,
            matchers.MatchesRegex(required))
        self.assertFalse(stderr)

    def test_unknown_auth_strategy(self):
        self.useFixture(fixtures.FakeLogger(level=logging.DEBUG))
        stdout, stderr = self.shell('--os-auth-strategy fake quota-list')
        self.assertFalse(stdout)
        self.assertEqual('You must provide a service URL via '
                         'either --os-url or env[OS_URL]', stderr.strip())

    def test_auth(self):
        #import pdb; pdb.set_trace()
        neutron_shell = openstack_shell.NeutronShell('2.0')
        self.addCleanup(self.mox.UnsetStubs)
        self.mox.StubOutWithMock(clientmanager.ClientManager, '__init__')
        self.mox.StubOutWithMock(neutron_shell, 'run_subcommand')
        clientmanager.ClientManager.__init__(
            token='', url='', auth_url='http://127.0.0.1:5000/',
            tenant_name='test', tenant_id='tenant_id',
            username='test', user_id='',
            password='test', region_name='', api_version={'network': '2.0'},
            auth_strategy='keystone', service_type='network',
            endpoint_type='publicURL', insecure=False, ca_cert=None,
            log_credentials=True)
        neutron_shell.run_subcommand(['quota-list'])
        self.mox.ReplayAll()
        cmdline = ('--os-username test '
                   '--os-password test '
                   '--os-tenant-name test '
                   '--os-auth-url http://127.0.0.1:5000/ '
                   '--os-auth-strategy keystone quota-list')
        neutron_shell.run(cmdline.split())
        self.mox.VerifyAll()

    def test_build_option_parser(self):
        neutron_shell = openstack_shell.NeutronShell('2.0')
        result = neutron_shell.build_option_parser('descr', '2.0')
        self.assertEqual(True, isinstance(result, argparse.ArgumentParser))

    def test_main_with_unicode(self):
        self.mox.StubOutClassWithMocks(openstack_shell, 'NeutronShell')
        qshell_mock = openstack_shell.NeutronShell('2.0')
        unicode_text = u'\u7f51\u7edc'
        argv = ['net-list', unicode_text, unicode_text.encode('utf-8')]
        qshell_mock.run([u'net-list', unicode_text,
                         unicode_text]).AndReturn(0)
        self.mox.ReplayAll()
        ret = openstack_shell.main(argv=argv)
        self.mox.VerifyAll()
        self.mox.UnsetStubs()
        self.assertEqual(ret, 0)

    def test_endpoint_option(self):
        shell = openstack_shell.NeutronShell('2.0')
        parser = shell.build_option_parser('descr', '2.0')

        # Neither $OS_ENDPOINT_TYPE nor --endpoint-type
        namespace = parser.parse_args([])
        self.assertEqual('publicURL', namespace.endpoint_type)

        # --endpoint-type but not $OS_ENDPOINT_TYPE
        namespace = parser.parse_args(['--endpoint-type=admin'])
        self.assertEqual('admin', namespace.endpoint_type)

    def test_endpoint_environment_variable(self):
        fixture = fixtures.EnvironmentVariable("OS_ENDPOINT_TYPE",
                                               "public")
        self.useFixture(fixture)

        shell = openstack_shell.NeutronShell('2.0')
        parser = shell.build_option_parser('descr', '2.0')

        # $OS_ENDPOINT_TYPE but not --endpoint-type
        namespace = parser.parse_args([])
        self.assertEqual("public", namespace.endpoint_type)

        # --endpoint-type and $OS_ENDPOINT_TYPE
        namespace = parser.parse_args(['--endpoint-type=admin'])
        self.assertEqual('admin', namespace.endpoint_type)

########NEW FILE########
__FILENAME__ = test_ssl
# Copyright (C) 2013 OpenStack Foundation.
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import fixtures
import mox
import requests
import testtools

from neutronclient.client import HTTPClient
from neutronclient.common.clientmanager import ClientManager
from neutronclient.common import exceptions
from neutronclient import shell as openstack_shell


AUTH_TOKEN = 'test_token'
END_URL = 'test_url'
METHOD = 'GET'
URL = 'http://test.test:1234/v2.0/'
CA_CERT = '/tmp/test/path'


class TestSSL(testtools.TestCase):
    def setUp(self):
        super(TestSSL, self).setUp()

        self.useFixture(fixtures.EnvironmentVariable('OS_TOKEN', AUTH_TOKEN))
        self.useFixture(fixtures.EnvironmentVariable('OS_URL', END_URL))

        self.mox = mox.Mox()
        self.addCleanup(self.mox.UnsetStubs)

    def test_ca_cert_passed(self):
        self.mox.StubOutWithMock(ClientManager, '__init__')
        self.mox.StubOutWithMock(openstack_shell.NeutronShell, 'interact')

        ClientManager.__init__(
            ca_cert=CA_CERT,
            # we are not really interested in other args
            api_version=mox.IgnoreArg(),
            auth_strategy=mox.IgnoreArg(),
            auth_url=mox.IgnoreArg(),
            service_type=mox.IgnoreArg(),
            endpoint_type=mox.IgnoreArg(),
            insecure=mox.IgnoreArg(),
            password=mox.IgnoreArg(),
            region_name=mox.IgnoreArg(),
            tenant_id=mox.IgnoreArg(),
            tenant_name=mox.IgnoreArg(),
            token=mox.IgnoreArg(),
            url=mox.IgnoreArg(),
            username=mox.IgnoreArg(),
            user_id=mox.IgnoreArg(),
            log_credentials=mox.IgnoreArg(),
        )
        openstack_shell.NeutronShell.interact().AndReturn(0)
        self.mox.ReplayAll()

        openstack_shell.NeutronShell('2.0').run(['--os-cacert', CA_CERT])
        self.mox.VerifyAll()

    def test_ca_cert_passed_as_env_var(self):
        self.useFixture(fixtures.EnvironmentVariable('OS_CACERT', CA_CERT))

        self.mox.StubOutWithMock(ClientManager, '__init__')
        self.mox.StubOutWithMock(openstack_shell.NeutronShell, 'interact')

        ClientManager.__init__(
            ca_cert=CA_CERT,
            # we are not really interested in other args
            api_version=mox.IgnoreArg(),
            auth_strategy=mox.IgnoreArg(),
            auth_url=mox.IgnoreArg(),
            service_type=mox.IgnoreArg(),
            endpoint_type=mox.IgnoreArg(),
            insecure=mox.IgnoreArg(),
            password=mox.IgnoreArg(),
            region_name=mox.IgnoreArg(),
            tenant_id=mox.IgnoreArg(),
            tenant_name=mox.IgnoreArg(),
            token=mox.IgnoreArg(),
            url=mox.IgnoreArg(),
            username=mox.IgnoreArg(),
            user_id=mox.IgnoreArg(),
            log_credentials=mox.IgnoreArg(),
        )
        openstack_shell.NeutronShell.interact().AndReturn(0)
        self.mox.ReplayAll()

        openstack_shell.NeutronShell('2.0').run([])
        self.mox.VerifyAll()

    def test_client_manager_properly_creates_httpclient_instance(self):
        self.mox.StubOutWithMock(HTTPClient, '__init__')
        HTTPClient.__init__(
            ca_cert=CA_CERT,
            # we are not really interested in other args
            auth_strategy=mox.IgnoreArg(),
            auth_url=mox.IgnoreArg(),
            endpoint_url=mox.IgnoreArg(),
            insecure=mox.IgnoreArg(),
            password=mox.IgnoreArg(),
            region_name=mox.IgnoreArg(),
            tenant_name=mox.IgnoreArg(),
            token=mox.IgnoreArg(),
            username=mox.IgnoreArg(),
        )
        self.mox.ReplayAll()

        version = {'network': '2.0'}
        ClientManager(ca_cert=CA_CERT,
                      api_version=version,
                      url=END_URL,
                      token=AUTH_TOKEN).neutron
        self.mox.VerifyAll()

    def test_proper_exception_is_raised_when_cert_validation_fails(self):
        http = HTTPClient(token=AUTH_TOKEN, endpoint_url=END_URL)

        self.mox.StubOutWithMock(HTTPClient, 'request')
        HTTPClient.request(
            URL, METHOD, headers=mox.IgnoreArg()
        ).AndRaise(requests.exceptions.SSLError)
        self.mox.ReplayAll()

        self.assertRaises(
            exceptions.SslCertificateValidationError,
            http._cs_request,
            URL, METHOD
        )
        self.mox.VerifyAll()

########NEW FILE########
__FILENAME__ = test_utils
# Copyright (C) 2013 Yahoo! Inc.
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import datetime
import sys

import testtools

from neutronclient.common import exceptions
from neutronclient.common import utils


class TestUtils(testtools.TestCase):
    def test_string_to_bool_true(self):
        self.assertTrue(utils.str2bool('true'))

    def test_string_to_bool_false(self):
        self.assertFalse(utils.str2bool('false'))

    def test_string_to_bool_None(self):
        self.assertIsNone(utils.str2bool(None))

    def test_string_to_dictionary(self):
        input_str = 'key1=value1,key2=value2'
        expected = {'key1': 'value1', 'key2': 'value2'}
        self.assertEqual(expected, utils.str2dict(input_str))

    def test_none_string_to_dictionary(self):
        input_str = ''
        expected = {}
        self.assertEqual(expected, utils.str2dict(input_str))
        input_str = None
        expected = {}
        self.assertEqual(expected, utils.str2dict(input_str))

    def test_get_dict_item_properties(self):
        item = {'name': 'test_name', 'id': 'test_id'}
        fields = ('name', 'id')
        actual = utils.get_item_properties(item=item, fields=fields)
        self.assertEqual(('test_name', 'test_id'), actual)

    def test_get_object_item_properties_mixed_case_fields(self):
        class Fake(object):
            def __init__(self):
                self.id = 'test_id'
                self.name = 'test_name'
                self.test_user = 'test'

        fields = ('name', 'id', 'test user')
        mixed_fields = ('test user', 'ID')
        item = Fake()
        actual = utils.get_item_properties(item, fields, mixed_fields)
        self.assertEqual(('test_name', 'test_id', 'test'), actual)

    def test_get_object_item_desired_fields_differ_from_item(self):
        class Fake(object):
            def __init__(self):
                self.id = 'test_id_1'
                self.name = 'test_name'
                self.test_user = 'test'

        fields = ('name', 'id', 'test user')
        item = Fake()
        actual = utils.get_item_properties(item, fields)
        self.assertNotEqual(('test_name', 'test_id', 'test'), actual)

    def test_get_object_item_desired_fields_is_empty(self):
        class Fake(object):
            def __init__(self):
                self.id = 'test_id_1'
                self.name = 'test_name'
                self.test_user = 'test'

        fields = []
        item = Fake()
        actual = utils.get_item_properties(item, fields)
        self.assertEqual((), actual)

    def test_get_object_item_with_formatters(self):
        class Fake(object):
            def __init__(self):
                self.id = 'test_id'
                self.name = 'test_name'
                self.test_user = 'test'

        class FakeCallable(object):
            def __call__(self, *args, **kwargs):
                return 'pass'

        fields = ('name', 'id', 'test user', 'is_public')
        formatters = {'is_public': FakeCallable()}
        item = Fake()
        act = utils.get_item_properties(item, fields, formatters=formatters)
        self.assertEqual(('test_name', 'test_id', 'test', 'pass'), act)


class JSONUtilsTestCase(testtools.TestCase):
    def test_dumps(self):
        self.assertEqual(utils.dumps({'a': 'b'}), '{"a": "b"}')

    def test_dumps_dict_with_date_value(self):
        x = datetime.datetime(1920, 2, 3, 4, 5, 6, 7)
        res = utils.dumps({1: 'a', 2: x})
        expected = '{"1": "a", "2": "1920-02-03 04:05:06.000007"}'
        self.assertEqual(expected, res)

    def test_dumps_dict_with_spaces(self):
        x = datetime.datetime(1920, 2, 3, 4, 5, 6, 7)
        res = utils.dumps({1: 'a ', 2: x})
        expected = '{"1": "a ", "2": "1920-02-03 04:05:06.000007"}'
        self.assertEqual(expected, res)

    def test_loads(self):
        self.assertEqual(utils.loads('{"a": "b"}'), {'a': 'b'})


class ToPrimitiveTestCase(testtools.TestCase):
    def test_list(self):
        self.assertEqual(utils.to_primitive([1, 2, 3]), [1, 2, 3])

    def test_empty_list(self):
        self.assertEqual(utils.to_primitive([]), [])

    def test_tuple(self):
        self.assertEqual(utils.to_primitive((1, 2, 3)), [1, 2, 3])

    def test_empty_tuple(self):
        self.assertEqual(utils.to_primitive(()), [])

    def test_dict(self):
        self.assertEqual(
            utils.to_primitive(dict(a=1, b=2, c=3)),
            dict(a=1, b=2, c=3))

    def test_empty_dict(self):
        self.assertEqual(utils.to_primitive({}), {})

    def test_datetime(self):
        x = datetime.datetime(1920, 2, 3, 4, 5, 6, 7)
        self.assertEqual(
            utils.to_primitive(x),
            '1920-02-03 04:05:06.000007')

    def test_iter(self):
        x = range(1, 6)
        self.assertEqual(utils.to_primitive(x), [1, 2, 3, 4, 5])

    def test_iteritems(self):
        d = {'a': 1, 'b': 2, 'c': 3}

        class IterItemsClass(object):
            def iteritems(self):
                return d.iteritems()

        x = IterItemsClass()
        p = utils.to_primitive(x)
        self.assertEqual(p, {'a': 1, 'b': 2, 'c': 3})

    def test_nasties(self):
        def foo():
            pass
        x = [datetime, foo, dir]
        ret = utils.to_primitive(x)
        self.assertEqual(len(ret), 3)

    def test_to_primitive_dict_with_date_value(self):
        x = datetime.datetime(1920, 2, 3, 4, 5, 6, 7)
        res = utils.to_primitive({'a': x})
        self.assertEqual({'a': '1920-02-03 04:05:06.000007'}, res)


class ImportClassTestCase(testtools.TestCase):
    def test_import_class(self):
        dt = utils.import_class('datetime.datetime')
        self.assertTrue(sys.modules['datetime'].datetime is dt)

    def test_import_bad_class(self):
        self.assertRaises(
            ImportError, utils.import_class,
            'lol.u_mad.brah')

    def test_get_client_class_invalid_version(self):
        self.assertRaises(
            exceptions.UnsupportedVersion,
            utils.get_client_class, 'image', '2', {'image': '2'})

########NEW FILE########
__FILENAME__ = test_validators
# Copyright 2014 NEC Corporation
# All Rights Reserved
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import testtools

from neutronclient.common import exceptions
from neutronclient.common import validators


class FakeParsedArgs():
    pass


class ValidatorTest(testtools.TestCase):

    def _test_validate_int(self, attr_val, attr_name='attr1',
                           min_value=1, max_value=10):
        obj = FakeParsedArgs()
        setattr(obj, attr_name, attr_val)
        ret = validators.validate_int_range(obj, attr_name,
                                            min_value, max_value)
        # Come here only if there is no exception.
        self.assertIsNone(ret)

    def _test_validate_int_error(self, attr_val, expected_msg,
                                 attr_name='attr1', expected_exc=None,
                                 min_value=1, max_value=10):
        if expected_exc is None:
            expected_exc = exceptions.CommandError
        e = self.assertRaises(expected_exc,
                              self._test_validate_int,
                              attr_val, attr_name, min_value, max_value)
        self.assertEqual(expected_msg, str(e))

    def test_validate_int_min_max(self):
        self._test_validate_int(1)
        self._test_validate_int(10)
        self._test_validate_int('1')
        self._test_validate_int('10')
        self._test_validate_int('0x0a')

        self._test_validate_int_error(
            0, 'attr1 "0" should be an integer [1:10].')
        self._test_validate_int_error(
            11, 'attr1 "11" should be an integer [1:10].')
        self._test_validate_int_error(
            '0x10', 'attr1 "0x10" should be an integer [1:10].')

    def test_validate_int_min_only(self):
        self._test_validate_int(1, max_value=None)
        self._test_validate_int(10, max_value=None)
        self._test_validate_int(11, max_value=None)
        self._test_validate_int_error(
            0, 'attr1 "0" should be an integer greater than or equal to 1.',
            max_value=None)

    def test_validate_int_max_only(self):
        self._test_validate_int(0, min_value=None)
        self._test_validate_int(1, min_value=None)
        self._test_validate_int(10, min_value=None)
        self._test_validate_int_error(
            11, 'attr1 "11" should be an integer smaller than or equal to 10.',
            min_value=None)

    def test_validate_int_no_limit(self):
        self._test_validate_int(0, min_value=None, max_value=None)
        self._test_validate_int(1, min_value=None, max_value=None)
        self._test_validate_int(10, min_value=None, max_value=None)
        self._test_validate_int(11, min_value=None, max_value=None)
        self._test_validate_int_error(
            'abc', 'attr1 "abc" should be an integer.',
            min_value=None, max_value=None)

    def _test_validate_subnet(self, attr_val, attr_name='attr1'):
        obj = FakeParsedArgs()
        setattr(obj, attr_name, attr_val)
        ret = validators.validate_ip_subnet(obj, attr_name)
        # Come here only if there is no exception.
        self.assertIsNone(ret)

    def test_validate_ip_subnet(self):
        self._test_validate_subnet('192.168.2.0/24')
        self._test_validate_subnet('192.168.2.3/20')
        self._test_validate_subnet('192.168.2.1')

        e = self.assertRaises(exceptions.CommandError,
                              self._test_validate_subnet,
                              '192.168.2.256')
        self.assertEqual('attr1 "192.168.2.256" is not a valid CIDR.', str(e))

########NEW FILE########
__FILENAME__ = test_cli20_ikepolicy
#    (c) Copyright 2013 Hewlett-Packard Development Company, L.P.
#    All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.
#
# @author: Swaminathan Vasudevan, Hewlett Packard.

import sys

from neutronclient.neutron.v2_0.vpn import ikepolicy
from neutronclient.tests.unit import test_cli20


class CLITestV20VpnIkePolicyJSON(test_cli20.CLITestV20Base):

    def test_create_ikepolicy_all_params(self):
        """vpn-ikepolicy-create all params."""
        resource = 'ikepolicy'
        cmd = ikepolicy.CreateIKEPolicy(test_cli20.MyApp(sys.stdout), None)
        name = 'ikepolicy1'
        description = 'my-ike-policy'
        auth_algorithm = 'sha1'
        encryption_algorithm = 'aes-256'
        ike_version = 'v1'
        phase1_negotiation_mode = 'main'
        pfs = 'group5'
        tenant_id = 'my-tenant'
        my_id = 'my-id'
        lifetime = 'units=seconds,value=20000'

        args = [name,
                '--description', description,
                '--tenant-id', tenant_id,
                '--auth-algorithm', auth_algorithm,
                '--encryption-algorithm', encryption_algorithm,
                '--ike-version', ike_version,
                '--phase1-negotiation-mode', phase1_negotiation_mode,
                '--lifetime', lifetime,
                '--pfs', pfs]

        position_names = ['name', 'description',
                          'auth_algorithm', 'encryption_algorithm',
                          'phase1_negotiation_mode',
                          'ike_version', 'pfs',
                          'tenant_id']

        position_values = [name, description,
                           auth_algorithm, encryption_algorithm,
                           phase1_negotiation_mode, ike_version, pfs,
                           tenant_id]
        extra_body = {
            'lifetime': {
                'units': 'seconds',
                'value': 20000,
            },
        }

        self._test_create_resource(resource, cmd, name, my_id, args,
                                   position_names, position_values,
                                   extra_body=extra_body)

    def test_create_ikepolicy_with_limited_params(self):
        """vpn-ikepolicy-create with limited params."""
        resource = 'ikepolicy'
        cmd = ikepolicy.CreateIKEPolicy(test_cli20.MyApp(sys.stdout), None)
        name = 'ikepolicy1'
        auth_algorithm = 'sha1'
        encryption_algorithm = 'aes-128'
        ike_version = 'v1'
        phase1_negotiation_mode = 'main'
        pfs = 'group5'
        tenant_id = 'my-tenant'
        my_id = 'my-id'

        args = [name,
                '--tenant-id', tenant_id]

        position_names = ['name',
                          'auth_algorithm', 'encryption_algorithm',
                          'phase1_negotiation_mode',
                          'ike_version', 'pfs',
                          'tenant_id']

        position_values = [name,
                           auth_algorithm, encryption_algorithm,
                           phase1_negotiation_mode,
                           ike_version, pfs,
                           tenant_id]

        self._test_create_resource(resource, cmd, name, my_id, args,
                                   position_names, position_values)

    def _test_lifetime_values(self, lifetime):
        resource = 'ikepolicy'
        cmd = ikepolicy.CreateIKEPolicy(test_cli20.MyApp(sys.stdout), None)
        name = 'ikepolicy1'
        description = 'my-ike-policy'
        auth_algorithm = 'sha1'
        encryption_algorithm = 'aes-256'
        ike_version = 'v1'
        phase1_negotiation_mode = 'main'
        pfs = 'group5'
        tenant_id = 'my-tenant'
        my_id = 'my-id'

        args = [name,
                '--description', description,
                '--tenant-id', tenant_id,
                '--auth-algorithm', auth_algorithm,
                '--encryption-algorithm', encryption_algorithm,
                '--ike-version', ike_version,
                '--phase1-negotiation-mode', phase1_negotiation_mode,
                '--lifetime', lifetime,
                '--pfs', pfs]

        position_names = ['name', 'description',
                          'auth_algorithm', 'encryption_algorithm',
                          'phase1_negotiation_mode',
                          'ike_version', 'pfs',
                          'tenant_id']

        position_values = [name, description,
                           auth_algorithm, encryption_algorithm,
                           phase1_negotiation_mode, ike_version, pfs,
                           tenant_id]
        try:
            self._test_create_resource(resource, cmd, name, my_id, args,
                                       position_names, position_values)
        except Exception:
            return
        self.fail("IKEPolicy Lifetime Error")

    def test_create_ikepolicy_with_invalid_lifetime_keys(self):
        lifetime = 'uts=seconds,val=20000'
        self._test_lifetime_values(lifetime)

    def test_create_ikepolicy_with_invalid_lifetime_value(self):
        lifetime = 'units=seconds,value=-1'
        self._test_lifetime_values(lifetime)

    def test_list_ikepolicy(self):
        """vpn-ikepolicy-list."""
        resources = "ikepolicies"
        cmd = ikepolicy.ListIKEPolicy(test_cli20.MyApp(sys.stdout), None)
        self._test_list_resources(resources, cmd, True)

    def test_list_ikepolicy_pagination(self):
        """vpn-ikepolicy-list."""
        resources = "ikepolicies"
        cmd = ikepolicy.ListIKEPolicy(test_cli20.MyApp(sys.stdout), None)
        self._test_list_resources_with_pagination(resources, cmd)

    def test_list_ikepolicy_sort(self):
        """vpn-ikepolicy-list --sort-key name --sort-key id --sort-key asc
        --sort-key desc
        """
        resources = "ikepolicies"
        cmd = ikepolicy.ListIKEPolicy(test_cli20.MyApp(sys.stdout), None)
        self._test_list_resources(resources, cmd,
                                  sort_key=["name", "id"],
                                  sort_dir=["asc", "desc"])

    def test_list_ikepolicy_limit(self):
        """vpn-ikepolicy-list -P."""
        resources = "ikepolicies"
        cmd = ikepolicy.ListIKEPolicy(test_cli20.MyApp(sys.stdout), None)
        self._test_list_resources(resources, cmd, page_size=1000)

    def test_show_ikepolicy_id(self):
        """vpn-ikepolicy-show ikepolicy_id."""
        resource = 'ikepolicy'
        cmd = ikepolicy.ShowIKEPolicy(test_cli20.MyApp(sys.stdout), None)
        args = ['--fields', 'id', self.test_id]
        self._test_show_resource(resource, cmd, self.test_id, args, ['id'])

    def test_show_ikepolicy_id_name(self):
        """vpn-ikepolicy-show."""
        resource = 'ikepolicy'
        cmd = ikepolicy.ShowIKEPolicy(test_cli20.MyApp(sys.stdout), None)
        args = ['--fields', 'id', '--fields', 'name', self.test_id]
        self._test_show_resource(resource, cmd, self.test_id,
                                 args, ['id', 'name'])

    def test_update_ikepolicy(self):
        """vpn-ikepolicy-update myid --name newname --tags a b."""
        resource = 'ikepolicy'
        cmd = ikepolicy.UpdateIKEPolicy(test_cli20.MyApp(sys.stdout), None)
        self._test_update_resource(resource, cmd, 'myid',
                                   ['myid', '--name', 'newname'],
                                   {'name': 'newname', })

    def test_delete_ikepolicy(self):
        """vpn-ikepolicy-delete my-id."""
        resource = 'ikepolicy'
        cmd = ikepolicy.DeleteIKEPolicy(test_cli20.MyApp(sys.stdout), None)
        my_id = 'my-id'
        args = [my_id]
        self._test_delete_resource(resource, cmd, my_id, args)


class CLITestV20VpnIkePolicyXML(CLITestV20VpnIkePolicyJSON):
    format = 'xml'

########NEW FILE########
__FILENAME__ = test_cli20_ipsecpolicy
#    (c) Copyright 2013 Hewlett-Packard Development Company, L.P.
#    All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.
#
# @author: Swaminathan Vasudevan, Hewlett Packard.

import sys

from neutronclient.neutron.v2_0.vpn import ipsecpolicy
from neutronclient.tests.unit import test_cli20


class CLITestV20VpnIpsecPolicyJSON(test_cli20.CLITestV20Base):

    def test_create_ipsecpolicy_all_params(self):
        """vpn-ipsecpolicy-create all params with dashes."""
        resource = 'ipsecpolicy'
        cmd = ipsecpolicy.CreateIPsecPolicy(test_cli20.MyApp(sys.stdout), None)
        name = 'ipsecpolicy1'
        description = 'first-ipsecpolicy1'
        auth_algorithm = 'sha1'
        encryption_algorithm = 'aes-256'
        encapsulation_mode = 'tunnel'
        pfs = 'group5'
        transform_protocol = 'ah'
        tenant_id = 'my-tenant'
        my_id = 'my-id'
        lifetime = 'units=seconds,value=20000'

        args = [name,
                '--description', description,
                '--tenant-id', tenant_id,
                '--auth-algorithm', auth_algorithm,
                '--encryption-algorithm', encryption_algorithm,
                '--transform-protocol', transform_protocol,
                '--encapsulation-mode', encapsulation_mode,
                '--lifetime', lifetime,
                '--pfs', pfs]

        position_names = ['name', 'auth_algorithm', 'encryption_algorithm',
                          'encapsulation_mode', 'description',
                          'transform_protocol', 'pfs',
                          'tenant_id']

        position_values = [name, auth_algorithm, encryption_algorithm,
                           encapsulation_mode, description,
                           transform_protocol, pfs,
                           tenant_id]
        extra_body = {
            'lifetime': {
                'units': 'seconds',
                'value': 20000,
            },
        }

        self._test_create_resource(resource, cmd, name, my_id, args,
                                   position_names, position_values,
                                   extra_body=extra_body)

    def test_create_ipsecpolicy_with_limited_params(self):
        """vpn-ipsecpolicy-create with limited params."""
        resource = 'ipsecpolicy'
        cmd = ipsecpolicy.CreateIPsecPolicy(test_cli20.MyApp(sys.stdout), None)
        name = 'ipsecpolicy1'
        auth_algorithm = 'sha1'
        encryption_algorithm = 'aes-128'
        encapsulation_mode = 'tunnel'
        pfs = 'group5'
        transform_protocol = 'esp'
        tenant_id = 'my-tenant'
        my_id = 'my-id'

        args = [name,
                '--tenant-id', tenant_id]

        position_names = ['name', 'auth_algorithm', 'encryption_algorithm',
                          'encapsulation_mode',
                          'transform_protocol', 'pfs',
                          'tenant_id']

        position_values = [name, auth_algorithm, encryption_algorithm,
                           encapsulation_mode,
                           transform_protocol, pfs,
                           tenant_id]

        self._test_create_resource(resource, cmd, name, my_id, args,
                                   position_names, position_values)

    def _test_lifetime_values(self, lifetime):
        resource = 'ipsecpolicy'
        cmd = ipsecpolicy.CreateIPsecPolicy(test_cli20.MyApp(sys.stdout), None)
        name = 'ipsecpolicy1'
        description = 'my-ipsec-policy'
        auth_algorithm = 'sha1'
        encryption_algorithm = 'aes-256'
        ike_version = 'v1'
        phase1_negotiation_mode = 'main'
        pfs = 'group5'
        tenant_id = 'my-tenant'
        my_id = 'my-id'

        args = [name,
                '--description', description,
                '--tenant-id', tenant_id,
                '--auth-algorithm', auth_algorithm,
                '--encryption-algorithm', encryption_algorithm,
                '--ike-version', ike_version,
                '--phase1-negotiation-mode', phase1_negotiation_mode,
                '--lifetime', lifetime,
                '--pfs', pfs]

        position_names = ['name', 'description',
                          'auth_algorithm', 'encryption_algorithm',
                          'phase1_negotiation_mode',
                          'ike_version', 'pfs',
                          'tenant_id']

        position_values = [name, description,
                           auth_algorithm, encryption_algorithm,
                           phase1_negotiation_mode, ike_version, pfs,
                           tenant_id]
        try:
            self._test_create_resource(resource, cmd, name, my_id, args,
                                       position_names, position_values)
        except Exception:
            return
        self.fail("IPsecPolicy Lifetime Error")

    def test_create_ipsecpolicy_with_invalid_lifetime_keys(self):
        lifetime = 'uts=seconds,val=20000'
        self._test_lifetime_values(lifetime)

    def test_create_ipsecpolicy_with_invalide_lifetime_values(self):
        lifetime = 'units=minutes,value=0'
        self._test_lifetime_values(lifetime)

    def test_list_ipsecpolicy(self):
        """vpn-ipsecpolicy-list."""
        resources = "ipsecpolicies"
        cmd = ipsecpolicy.ListIPsecPolicy(test_cli20.MyApp(sys.stdout), None)
        self._test_list_resources(resources, cmd, True)

    def test_list_ipsecpolicy_pagination(self):
        """vpn-ipsecpolicy-list."""
        resources = "ipsecpolicies"
        cmd = ipsecpolicy.ListIPsecPolicy(test_cli20.MyApp(sys.stdout), None)
        self._test_list_resources_with_pagination(resources, cmd)

    def test_list_ipsecpolicy_sort(self):
        """vpn-ipsecpolicy-list --sort-key name --sort-key id --sort-key asc
        --sort-key desc
        """
        resources = "ipsecpolicies"
        cmd = ipsecpolicy.ListIPsecPolicy(test_cli20.MyApp(sys.stdout), None)
        self._test_list_resources(resources, cmd,
                                  sort_key=["name", "id"],
                                  sort_dir=["asc", "desc"])

    def test_list_ipsecpolicy_limit(self):
        """vpn-ipsecpolicy-list -P."""
        resources = "ipsecpolicies"
        cmd = ipsecpolicy.ListIPsecPolicy(test_cli20.MyApp(sys.stdout), None)
        self._test_list_resources(resources, cmd, page_size=1000)

    def test_show_ipsecpolicy_id(self):
        """vpn-ipsecpolicy-show ipsecpolicy_id."""
        resource = 'ipsecpolicy'
        cmd = ipsecpolicy.ShowIPsecPolicy(test_cli20.MyApp(sys.stdout), None)
        args = ['--fields', 'id', self.test_id]
        self._test_show_resource(resource, cmd, self.test_id, args, ['id'])

    def test_show_ipsecpolicy_id_name(self):
        """vpn-ipsecpolicy-show."""
        resource = 'ipsecpolicy'
        cmd = ipsecpolicy.ShowIPsecPolicy(test_cli20.MyApp(sys.stdout), None)
        args = ['--fields', 'id', '--fields', 'name', self.test_id]
        self._test_show_resource(resource, cmd, self.test_id,
                                 args, ['id', 'name'])

    def test_update_ipsecpolicy(self):
        """vpn-ipsecpolicy-update myid --name newname --tags a b."""
        resource = 'ipsecpolicy'
        cmd = ipsecpolicy.UpdateIPsecPolicy(test_cli20.MyApp(sys.stdout), None)
        self._test_update_resource(resource, cmd, 'myid',
                                   ['myid', '--name', 'newname'],
                                   {'name': 'newname', })

    def test_delete_ipsecpolicy(self):
        """vpn-ipsecpolicy-delete my-id."""
        resource = 'ipsecpolicy'
        cmd = ipsecpolicy.DeleteIPsecPolicy(test_cli20.MyApp(sys.stdout), None)
        my_id = 'my-id'
        args = [my_id]
        self._test_delete_resource(resource, cmd, my_id, args)


class CLITestV20VpnIpsecPolicyXML(CLITestV20VpnIpsecPolicyJSON):
    format = 'xml'

########NEW FILE########
__FILENAME__ = test_cli20_ipsec_site_connection
#    (c) Copyright 2013 Hewlett-Packard Development Company, L.P.
#    All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.
#
# @author: Swaminathan Vasudevan, Hewlett Packard.

import sys

from neutronclient.common import exceptions
from neutronclient.neutron.v2_0.vpn import ipsec_site_connection
from neutronclient.tests.unit import test_cli20


class CLITestV20IPsecSiteConnectionJSON(test_cli20.CLITestV20Base):

    def test_create_ipsec_site_connection_all_params(self):
        """ipsecsite-connection-create all params."""
        resource = 'ipsec_site_connection'
        cmd = ipsec_site_connection.CreateIPsecSiteConnection(
            test_cli20.MyApp(sys.stdout), None
        )
        tenant_id = 'mytenant_id'
        name = 'connection1'
        my_id = 'my_id'
        peer_address = '192.168.2.10'
        peer_id = '192.168.2.10'
        psk = 'abcd'
        mtu = '1500'
        initiator = 'bi-directional'
        vpnservice_id = 'vpnservice_id'
        ikepolicy_id = 'ikepolicy_id'
        ipsecpolicy_id = 'ipsecpolicy_id'
        peer_cidrs = ['192.168.3.0/24', '192.168.2.0/24']
        admin_state = True
        description = 'my-vpn-connection'
        dpd = 'action=restart,interval=30,timeout=120'

        args = ['--tenant-id', tenant_id,
                '--peer-address', peer_address, '--peer-id', peer_id,
                '--psk', psk, '--initiator', initiator,
                '--vpnservice-id', vpnservice_id,
                '--ikepolicy-id', ikepolicy_id, '--name', name,
                '--ipsecpolicy-id', ipsecpolicy_id, '--mtu', mtu,
                '--description', description,
                '--peer-cidr', '192.168.3.0/24',
                '--peer-cidr', '192.168.2.0/24',
                '--dpd', dpd]

        position_names = ['name', 'tenant_id', 'admin_state_up',
                          'peer_address', 'peer_id', 'peer_cidrs',
                          'psk', 'mtu', 'initiator', 'description',
                          'vpnservice_id', 'ikepolicy_id',
                          'ipsecpolicy_id']

        position_values = [name, tenant_id, admin_state, peer_address,
                           peer_id, peer_cidrs, psk, mtu,
                           initiator, description,
                           vpnservice_id, ikepolicy_id, ipsecpolicy_id]
        extra_body = {
            'dpd': {
                'action': 'restart',
                'interval': 30,
                'timeout': 120,
            },
        }

        self._test_create_resource(resource, cmd, name, my_id, args,
                                   position_names, position_values,
                                   extra_body=extra_body)

    def test_create_ipsec_site_connection_with_limited_params(self):
        """ipsecsite-connection-create with limited params."""
        resource = 'ipsec_site_connection'
        cmd = ipsec_site_connection.CreateIPsecSiteConnection(
            test_cli20.MyApp(sys.stdout), None
        )
        tenant_id = 'mytenant_id'
        my_id = 'my_id'
        peer_address = '192.168.2.10'
        peer_id = '192.168.2.10'
        psk = 'abcd'
        mtu = '1500'
        initiator = 'bi-directional'
        vpnservice_id = 'vpnservice_id'
        ikepolicy_id = 'ikepolicy_id'
        ipsecpolicy_id = 'ipsecpolicy_id'
        peer_cidrs = ['192.168.3.0/24', '192.168.2.0/24']
        admin_state = True

        args = ['--tenant-id', tenant_id,
                '--peer-address', peer_address,
                '--peer-id', peer_id,
                '--psk', psk,
                '--vpnservice-id', vpnservice_id,
                '--ikepolicy-id', ikepolicy_id,
                '--ipsecpolicy-id', ipsecpolicy_id,
                '--peer-cidr', '192.168.3.0/24',
                '--peer-cidr', '192.168.2.0/24']

        position_names = ['tenant_id', 'admin_state_up',
                          'peer_address', 'peer_id', 'peer_cidrs',
                          'psk', 'mtu', 'initiator',
                          'vpnservice_id', 'ikepolicy_id',
                          'ipsecpolicy_id']

        position_values = [tenant_id, admin_state, peer_address,
                           peer_id, peer_cidrs, psk, mtu,
                           initiator,
                           vpnservice_id, ikepolicy_id, ipsecpolicy_id]

        self._test_create_resource(resource, cmd, None, my_id, args,
                                   position_names, position_values)

    def _test_dpd_values(self, dpd):
        """ipsecsite-connection-create with invalid dpd values."""
        resource = 'ipsec_site_connection'
        cmd = ipsec_site_connection.CreateIPsecSiteConnection(
            test_cli20.MyApp(sys.stdout), None
        )
        tenant_id = 'mytenant_id'
        name = 'connection1'
        my_id = 'my_id'
        peer_address = '192.168.2.10'
        peer_id = '192.168.2.10'
        psk = 'abcd'
        mtu = '1500'
        initiator = 'bi-directional'
        vpnservice_id = 'vpnservice_id'
        ikepolicy_id = 'ikepolicy_id'
        ipsecpolicy_id = 'ipsecpolicy_id'
        peer_cidrs = ['192.168.3.0/24', '192.168.2.0/24']
        admin_state = True
        description = 'my-vpn-connection'

        args = ['--tenant-id', tenant_id,
                '--peer-address', peer_address, '--peer-id', peer_id,
                '--psk', psk, '--initiator', initiator,
                '--vpnservice-id', vpnservice_id,
                '--ikepolicy-id', ikepolicy_id, '--name', name,
                '--ipsecpolicy-id', ipsecpolicy_id, '--mtu', mtu,
                '--description', description,
                '--peer-cidr', '192.168.3.0/24',
                '--peer-cidr', '192.168.2.0/24',
                '--dpd', dpd]

        position_names = ['name', 'tenant_id', 'admin_state_up',
                          'peer_address', 'peer_id', 'peer_cidrs',
                          'psk', 'mtu', 'initiator', 'description',
                          'vpnservice_id', 'ikepolicy_id',
                          'ipsecpolicy_id']

        position_values = [name, tenant_id, admin_state, peer_address,
                           peer_id, peer_cidrs, psk, mtu,
                           initiator, description,
                           vpnservice_id, ikepolicy_id, ipsecpolicy_id]
        self.assertRaises(
            exceptions.CommandError,
            self._test_create_resource,
            resource, cmd, name, my_id, args,
            position_names, position_values)

    def test_invalid_mtu(self):
        """ipsecsite-connection-create with invalid dpd values."""
        resource = 'ipsec_site_connection'
        cmd = ipsec_site_connection.CreateIPsecSiteConnection(
            test_cli20.MyApp(sys.stdout), None
        )
        tenant_id = 'mytenant_id'
        name = 'connection1'
        my_id = 'my_id'
        peer_address = '192.168.2.10'
        peer_id = '192.168.2.10'
        psk = 'abcd'
        mtu = '67'
        initiator = 'bi-directional'
        vpnservice_id = 'vpnservice_id'
        ikepolicy_id = 'ikepolicy_id'
        ipsecpolicy_id = 'ipsecpolicy_id'
        peer_cidrs = ['192.168.3.0/24', '192.168.2.0/24']
        admin_state = True
        description = 'my-vpn-connection'

        args = ['--tenant-id', tenant_id,
                '--peer-address', peer_address, '--peer-id', peer_id,
                '--psk', psk, '--initiator', initiator,
                '--vpnservice-id', vpnservice_id,
                '--ikepolicy-id', ikepolicy_id, '--name', name,
                '--ipsecpolicy-id', ipsecpolicy_id, '--mtu', mtu,
                '--description', description,
                '--peer-cidr', '192.168.3.0/24',
                '--peer-cidr', '192.168.2.0/24']

        position_names = ['name', 'tenant_id', 'admin_state_up',
                          'peer_address', 'peer_id', 'peer_cidrs',
                          'psk', 'mtu', 'initiator', 'description',
                          'vpnservice_id', 'ikepolicy_id',
                          'ipsecpolicy_id']

        position_values = [name, tenant_id, admin_state, peer_address,
                           peer_id, peer_cidrs, psk, mtu,
                           initiator, description,
                           vpnservice_id, ikepolicy_id, ipsecpolicy_id]
        self.assertRaises(
            exceptions.CommandError,
            self._test_create_resource,
            resource, cmd, name, my_id, args,
            position_names, position_values)

    def test_create_ipsec_site_connection_with_invalid_dpd_keys(self):
        dpd = 'act=restart,interval=30,time=120'
        self._test_dpd_values(dpd)

    def test_create_ipsec_site_connection_with_invalid_dpd_values(self):
        dpd = 'action=hold,interval=30,timeout=-1'
        self._test_dpd_values(dpd)

    def test_list_ipsec_site_connection(self):
        """ipsecsite-connection-list."""
        resources = "ipsec_site_connections"
        cmd = ipsec_site_connection.ListIPsecSiteConnection(
            test_cli20.MyApp(sys.stdout), None
        )
        self._test_list_resources(resources, cmd, True)

    def test_list_ipsec_site_connection_pagination(self):
        """ipsecsite-connection-list."""
        resources = "ipsec_site_connections"
        cmd = ipsec_site_connection.ListIPsecSiteConnection(
            test_cli20.MyApp(sys.stdout), None
        )
        self._test_list_resources_with_pagination(resources, cmd)

    def test_list_ipsec_site_connection_sort(self):
        """ipsecsite-connection-list.
        --sort-key name --sort-key id --sort-key asc --sort-key desc
        """
        resources = "ipsec_site_connections"
        cmd = ipsec_site_connection.ListIPsecSiteConnection(
            test_cli20.MyApp(sys.stdout), None
        )
        self._test_list_resources(resources, cmd,
                                  sort_key=["name", "id"],
                                  sort_dir=["asc", "desc"])

    def test_list_ipsec_site_connection_limit(self):
        """ipsecsite-connection-list -P."""
        resources = "ipsec_site_connections"
        cmd = ipsec_site_connection.ListIPsecSiteConnection(
            test_cli20.MyApp(sys.stdout), None
        )
        self._test_list_resources(resources, cmd, page_size=1000)

    def test_delete_ipsec_site_connection(self):
        """ipsecsite-connection-delete my-id."""
        resource = 'ipsec_site_connection'
        cmd = ipsec_site_connection.DeleteIPsecSiteConnection(
            test_cli20.MyApp(sys.stdout), None
        )
        my_id = 'my-id'
        args = [my_id]
        self._test_delete_resource(resource, cmd, my_id, args)

    def test_update_ipsec_site_connection(self):
        """ipsecsite-connection-update  myid --name myname --tags a b."""
        resource = 'ipsec_site_connection'
        cmd = ipsec_site_connection.UpdateIPsecSiteConnection(
            test_cli20.MyApp(sys.stdout), None
        )
        self._test_update_resource(resource, cmd, 'myid',
                                   ['myid', '--name', 'Branch-new',
                                    '--tags', 'a', 'b'],
                                   {'name': 'Branch-new',
                                    'tags': ['a', 'b'], })

    def test_show_ipsec_site_connection_id(self):
        """ipsecsite-connection-show test_id."""
        resource = 'ipsec_site_connection'
        cmd = ipsec_site_connection.ShowIPsecSiteConnection(
            test_cli20.MyApp(sys.stdout), None
        )
        args = ['--fields', 'id', self.test_id]
        self._test_show_resource(resource, cmd, self.test_id, args, ['id'])

    def test_show_ipsec_site_connection_id_name(self):
        """ipsecsite-connection-show."""
        resource = 'ipsec_site_connection'
        cmd = ipsec_site_connection.ShowIPsecSiteConnection(
            test_cli20.MyApp(sys.stdout), None
        )
        args = ['--fields', 'id', '--fields', 'name', self.test_id]
        self._test_show_resource(resource, cmd, self.test_id,
                                 args, ['id', 'name'])


class CLITestV20IPsecSiteConnectionXML(CLITestV20IPsecSiteConnectionJSON):
    format = 'xml'

########NEW FILE########
__FILENAME__ = test_cli20_vpnservice
#    (c) Copyright 2013 Hewlett-Packard Development Company, L.P.
#    All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.
#
# @author: Swaminathan Vasudevan, Hewlett Packard.

import sys

from neutronclient.neutron.v2_0.vpn import vpnservice
from neutronclient.tests.unit import test_cli20


class CLITestV20VpnServiceJSON(test_cli20.CLITestV20Base):

    def test_create_vpnservice_all_params(self):
        """vpn-service-create all params."""
        resource = 'vpnservice'
        cmd = vpnservice.CreateVPNService(test_cli20.MyApp(sys.stdout), None)
        subnet = 'mysubnet-id'
        router = 'myrouter-id'
        tenant_id = 'mytenant-id'
        my_id = 'my-id'
        name = 'myvpnservice'
        description = 'my-vpn-service'
        admin_state = True

        args = ['--name', name,
                '--description', description,
                router,
                subnet,
                '--tenant-id', tenant_id]

        position_names = ['admin_state_up', 'name', 'description',
                          'subnet_id', 'router_id',
                          'tenant_id']

        position_values = [admin_state, name, description,
                           subnet, router, tenant_id]

        self._test_create_resource(resource, cmd, name, my_id, args,
                                   position_names, position_values)

    def test_create_vpnservice_with_limited_params(self):
        """vpn-service-create with limited params."""
        resource = 'vpnservice'
        cmd = vpnservice.CreateVPNService(test_cli20.MyApp(sys.stdout), None)
        subnet = 'mysubnet-id'
        router = 'myrouter-id'
        tenant_id = 'mytenant-id'
        my_id = 'my-id'
        admin_state = True

        args = [router,
                subnet,
                '--tenant-id', tenant_id]

        position_names = ['admin_state_up',
                          'subnet_id', 'router_id',
                          'tenant_id']

        position_values = [admin_state, subnet, router, tenant_id]

        self._test_create_resource(resource, cmd, None, my_id, args,
                                   position_names, position_values)

    def test_list_vpnservice(self):
        """vpn-service-list."""
        resources = "vpnservices"
        cmd = vpnservice.ListVPNService(test_cli20.MyApp(sys.stdout), None)
        self._test_list_resources(resources, cmd, True)

    def test_list_vpnservice_pagination(self):
        """vpn-service-list."""
        resources = "vpnservices"
        cmd = vpnservice.ListVPNService(test_cli20.MyApp(sys.stdout), None)
        self._test_list_resources_with_pagination(resources, cmd)

    def test_list_vpnservice_sort(self):
        """vpn-service-list --sort-key name --sort-key id --sort-key asc
        --sort-key desc
        """
        resources = "vpnservices"
        cmd = vpnservice.ListVPNService(test_cli20.MyApp(sys.stdout), None)
        self._test_list_resources(resources, cmd,
                                  sort_key=["name", "id"],
                                  sort_dir=["asc", "desc"])

    def test_list_vpnservice_limit(self):
        """vpn-service-list -P."""
        resources = "vpnservices"
        cmd = vpnservice.ListVPNService(test_cli20.MyApp(sys.stdout), None)
        self._test_list_resources(resources, cmd, page_size=1000)

    def test_show_vpnservice_id(self):
        """vpn-service-show test_id."""
        resource = 'vpnservice'
        cmd = vpnservice.ShowVPNService(test_cli20.MyApp(sys.stdout), None)
        args = ['--fields', 'id', self.test_id]
        self._test_show_resource(resource, cmd, self.test_id, args, ['id'])

    def test_show_vpnservice_id_name(self):
        """vpn-service-show."""
        resource = 'vpnservice'
        cmd = vpnservice.ShowVPNService(test_cli20.MyApp(sys.stdout), None)
        args = ['--fields', 'id', '--fields', 'name', self.test_id]
        self._test_show_resource(resource, cmd, self.test_id,
                                 args, ['id', 'name'])

    def test_update_vpnservice(self):
        """vpn-service-update myid --name newname --tags a b."""
        resource = 'vpnservice'
        cmd = vpnservice.UpdateVPNService(test_cli20.MyApp(sys.stdout), None)
        self._test_update_resource(resource, cmd, 'myid',
                                   ['myid', '--name', 'newname'],
                                   {'name': 'newname', })

    def test_delete_vpnservice(self):
        """vpn-service-delete my-id."""
        resource = 'vpnservice'
        cmd = vpnservice.DeleteVPNService(test_cli20.MyApp(sys.stdout), None)
        my_id = 'my-id'
        args = [my_id]
        self._test_delete_resource(resource, cmd, my_id, args)


class CLITestV20VpnServiceXML(CLITestV20VpnServiceJSON):
    format = 'xml'

########NEW FILE########
__FILENAME__ = test_utils
#    (c) Copyright 2013 Hewlett-Packard Development Company, L.P.
#    All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.
#
# @author: Swaminathan Vasudevan, Hewlett Packard.

import testtools

from neutronclient.common import exceptions
from neutronclient.common import utils
from neutronclient.neutron.v2_0.vpn import utils as vpn_utils


class TestVPNUtils(testtools.TestCase):

    def test_validate_lifetime_dictionary_seconds(self):
        input_str = utils.str2dict("units=seconds,value=3600")
        self.assertIsNone(vpn_utils.validate_lifetime_dict(input_str))

    def test_validate_dpd_dictionary_action_hold(self):
        input_str = utils.str2dict("action=hold,interval=30,timeout=120")
        self.assertIsNone(vpn_utils.validate_dpd_dict(input_str))

    def test_validate_dpd_dictionary_action_restart(self):
        input_str = utils.str2dict("action=restart,interval=30,timeout=120")
        self.assertIsNone(vpn_utils.validate_dpd_dict(input_str))

    def test_validate_dpd_dictionary_action_restart_by_peer(self):
        input_str = utils.str2dict(
            "action=restart-by-peer,interval=30,timeout=120"
        )
        self.assertIsNone(vpn_utils.validate_dpd_dict(input_str))

    def test_validate_dpd_dictionary_action_clear(self):
        input_str = utils.str2dict('action=clear,interval=30,timeout=120')
        self.assertIsNone(vpn_utils.validate_dpd_dict(input_str))

    def test_validate_dpd_dictionary_action_disabled(self):
        input_str = utils.str2dict('action=disabled,interval=30,timeout=120')
        self.assertIsNone(vpn_utils.validate_dpd_dict(input_str))

    def test_validate_lifetime_dictionary_invalid_unit_key(self):
        input_str = utils.str2dict('ut=seconds,value=3600')
        self._test_validate_lifetime_negative_test_case(input_str)

    def test_validate_lifetime_dictionary_invalid_unit_key_value(self):
        input_str = utils.str2dict('units=seconds,val=3600')
        self._test_validate_lifetime_negative_test_case(input_str)

    def test_validate_lifetime_dictionary_unsupported_units(self):
        input_str = utils.str2dict('units=minutes,value=3600')
        self._test_validate_lifetime_negative_test_case(input_str)

    def test_validate_lifetime_dictionary_invalid_empty_unit(self):
        input_str = utils.str2dict('units=,value=3600')
        self._test_validate_lifetime_negative_test_case(input_str)

    def test_validate_lifetime_dictionary_under_minimum_integer_value(self):
        input_str = utils.str2dict('units=seconds,value=59')
        self._test_validate_lifetime_negative_test_case(input_str)

    def test_validate_lifetime_dictionary_negative_integer_value(self):
        input_str = utils.str2dict('units=seconds,value=-1')
        self._test_validate_lifetime_negative_test_case(input_str)

    def test_validate_lifetime_dictionary_empty_value(self):
        input_str = utils.str2dict('units=seconds,value=')
        self._test_validate_lifetime_negative_test_case(input_str)

    def test_validate_dpd_dictionary_invalid_key_action(self):
        input_str = utils.str2dict('act=hold,interval=30,timeout=120')
        self._test_validate_dpd_negative_test_case(input_str)

    def test_validate_dpd_dictionary_invalid_key_interval(self):
        input_str = utils.str2dict('action=hold,int=30,timeout=120')
        self._test_validate_dpd_negative_test_case(input_str)

    def test_validate_dpd_dictionary_invalid_key_timeout(self):
        input_str = utils.str2dict('action=hold,interval=30,tiut=120')
        self._test_validate_dpd_negative_test_case(input_str)

    def test_validate_dpd_dictionary_unsupported_action(self):
        input_str = utils.str2dict('action=bye-bye,interval=30,timeout=120')
        self._test_validate_dpd_negative_test_case(input_str)

    def test_validate_dpd_dictionary_empty_action(self):
        input_str = utils.str2dict('action=,interval=30,timeout=120')
        self._test_validate_dpd_negative_test_case(input_str)

    def test_validate_dpd_dictionary_empty_interval(self):
        input_str = utils.str2dict('action=hold,interval=,timeout=120')
        self._test_validate_dpd_negative_test_case(input_str)

    def test_validate_dpd_dictionary_negative_interval_value(self):
        input_str = utils.str2dict('action=hold,interval=-1,timeout=120')
        self._test_validate_lifetime_negative_test_case(input_str)

    def test_validate_dpd_dictionary_zero_timeout(self):
        input_str = utils.str2dict('action=hold,interval=30,timeout=0')
        self._test_validate_dpd_negative_test_case(input_str)

    def test_validate_dpd_dictionary_empty_timeout(self):
        input_str = utils.str2dict('action=hold,interval=30,timeout=')
        self._test_validate_dpd_negative_test_case(input_str)

    def test_validate_dpd_dictionary_negative_timeout_value(self):
        input_str = utils.str2dict('action=hold,interval=30,timeout=-1')
        self._test_validate_lifetime_negative_test_case(input_str)

    def _test_validate_lifetime_negative_test_case(self, input_str):
        """Generic handler for negative lifetime tests."""
        self.assertRaises(exceptions.CommandError,
                          vpn_utils.validate_lifetime_dict,
                          (input_str))

    def _test_validate_dpd_negative_test_case(self, input_str):
        """Generic handler for negative lifetime tests."""
        self.assertRaises(exceptions.CommandError,
                          vpn_utils.validate_lifetime_dict,
                          (input_str))

########NEW FILE########
__FILENAME__ = client
# Copyright 2012 OpenStack Foundation.
# All Rights Reserved
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.
#

import logging
import time
import urllib

import requests
import six.moves.urllib.parse as urlparse

from neutronclient import client
from neutronclient.common import _
from neutronclient.common import constants
from neutronclient.common import exceptions
from neutronclient.common import serializer
from neutronclient.common import utils


_logger = logging.getLogger(__name__)


def exception_handler_v20(status_code, error_content):
    """Exception handler for API v2.0 client

        This routine generates the appropriate
        Neutron exception according to the contents of the
        response body

        :param status_code: HTTP error status code
        :param error_content: deserialized body of error response
    """
    error_dict = None
    if isinstance(error_content, dict):
        error_dict = error_content.get('NeutronError')
    # Find real error type
    bad_neutron_error_flag = False
    if error_dict:
        # If Neutron key is found, it will definitely contain
        # a 'message' and 'type' keys?
        try:
            error_type = error_dict['type']
            error_message = error_dict['message']
            if error_dict['detail']:
                error_message += "\n" + error_dict['detail']
        except Exception:
            bad_neutron_error_flag = True
        if not bad_neutron_error_flag:
            # If corresponding exception is defined, use it.
            client_exc = getattr(exceptions, '%sClient' % error_type, None)
            # Otherwise look up per status-code client exception
            if not client_exc:
                client_exc = exceptions.HTTP_EXCEPTION_MAP.get(status_code)
            if client_exc:
                raise client_exc(message=error_message,
                                 status_code=status_code)
            else:
                raise exceptions.NeutronClientException(
                    status_code=status_code, message=error_message)
        else:
            raise exceptions.NeutronClientException(status_code=status_code,
                                                    message=error_dict)
    else:
        message = None
        if isinstance(error_content, dict):
            message = error_content.get('message')
        if message:
            raise exceptions.NeutronClientException(status_code=status_code,
                                                    message=message)

    # If we end up here the exception was not a neutron error
    msg = "%s-%s" % (status_code, error_content)
    raise exceptions.NeutronClientException(status_code=status_code,
                                            message=msg)


class APIParamsCall(object):
    """A Decorator to add support for format and tenant overriding
       and filters
    """
    def __init__(self, function):
        self.function = function

    def __get__(self, instance, owner):
        def with_params(*args, **kwargs):
            _format = instance.format
            if 'format' in kwargs:
                instance.format = kwargs['format']
            ret = self.function(instance, *args, **kwargs)
            instance.format = _format
            return ret
        return with_params


class Client(object):
    """Client for the OpenStack Neutron v2.0 API.

    :param string username: Username for authentication. (optional)
    :param string user_id: User ID for authentication. (optional)
    :param string password: Password for authentication. (optional)
    :param string token: Token for authentication. (optional)
    :param string tenant_name: Tenant name. (optional)
    :param string tenant_id: Tenant id. (optional)
    :param string auth_url: Keystone service endpoint for authorization.
    :param string service_type: Network service type to pull from the
                                keystone catalog (e.g. 'network') (optional)
    :param string endpoint_type: Network service endpoint type to pull from the
                                 keystone catalog (e.g. 'publicURL',
                                 'internalURL', or 'adminURL') (optional)
    :param string region_name: Name of a region to select when choosing an
                               endpoint from the service catalog.
    :param string endpoint_url: A user-supplied endpoint URL for the neutron
                            service.  Lazy-authentication is possible for API
                            service calls if endpoint is set at
                            instantiation.(optional)
    :param integer timeout: Allows customization of the timeout for client
                            http requests. (optional)
    :param bool insecure: SSL certificate validation. (optional)
    :param string ca_cert: SSL CA bundle file to use. (optional)

    Example::

        from neutronclient.v2_0 import client
        neutron = client.Client(username=USER,
                                password=PASS,
                                tenant_name=TENANT_NAME,
                                auth_url=KEYSTONE_URL)

        nets = neutron.list_networks()
        ...

    """

    networks_path = "/networks"
    network_path = "/networks/%s"
    ports_path = "/ports"
    port_path = "/ports/%s"
    subnets_path = "/subnets"
    subnet_path = "/subnets/%s"
    quotas_path = "/quotas"
    quota_path = "/quotas/%s"
    extensions_path = "/extensions"
    extension_path = "/extensions/%s"
    routers_path = "/routers"
    router_path = "/routers/%s"
    floatingips_path = "/floatingips"
    floatingip_path = "/floatingips/%s"
    security_groups_path = "/security-groups"
    security_group_path = "/security-groups/%s"
    security_group_rules_path = "/security-group-rules"
    security_group_rule_path = "/security-group-rules/%s"
    vpnservices_path = "/vpn/vpnservices"
    vpnservice_path = "/vpn/vpnservices/%s"
    ipsecpolicies_path = "/vpn/ipsecpolicies"
    ipsecpolicy_path = "/vpn/ipsecpolicies/%s"
    ikepolicies_path = "/vpn/ikepolicies"
    ikepolicy_path = "/vpn/ikepolicies/%s"
    ipsec_site_connections_path = "/vpn/ipsec-site-connections"
    ipsec_site_connection_path = "/vpn/ipsec-site-connections/%s"
    vips_path = "/lb/vips"
    vip_path = "/lb/vips/%s"
    pools_path = "/lb/pools"
    pool_path = "/lb/pools/%s"
    pool_path_stats = "/lb/pools/%s/stats"
    members_path = "/lb/members"
    member_path = "/lb/members/%s"
    health_monitors_path = "/lb/health_monitors"
    health_monitor_path = "/lb/health_monitors/%s"
    associate_pool_health_monitors_path = "/lb/pools/%s/health_monitors"
    disassociate_pool_health_monitors_path = (
        "/lb/pools/%(pool)s/health_monitors/%(health_monitor)s")
    qos_queues_path = "/qos-queues"
    qos_queue_path = "/qos-queues/%s"
    agents_path = "/agents"
    agent_path = "/agents/%s"
    network_gateways_path = "/network-gateways"
    network_gateway_path = "/network-gateways/%s"
    gateway_devices_path = "/gateway-devices"
    gateway_device_path = "/gateway-devices/%s"
    service_providers_path = "/service-providers"
    credentials_path = "/credentials"
    credential_path = "/credentials/%s"
    network_profiles_path = "/network_profiles"
    network_profile_path = "/network_profiles/%s"
    network_profile_bindings_path = "/network_profile_bindings"
    policy_profiles_path = "/policy_profiles"
    policy_profile_path = "/policy_profiles/%s"
    policy_profile_bindings_path = "/policy_profile_bindings"
    metering_labels_path = "/metering/metering-labels"
    metering_label_path = "/metering/metering-labels/%s"
    metering_label_rules_path = "/metering/metering-label-rules"
    metering_label_rule_path = "/metering/metering-label-rules/%s"
    packet_filters_path = "/packet_filters"
    packet_filter_path = "/packet_filters/%s"

    DHCP_NETS = '/dhcp-networks'
    DHCP_AGENTS = '/dhcp-agents'
    L3_ROUTERS = '/l3-routers'
    L3_AGENTS = '/l3-agents'
    LOADBALANCER_POOLS = '/loadbalancer-pools'
    LOADBALANCER_AGENT = '/loadbalancer-agent'
    firewall_rules_path = "/fw/firewall_rules"
    firewall_rule_path = "/fw/firewall_rules/%s"
    firewall_policies_path = "/fw/firewall_policies"
    firewall_policy_path = "/fw/firewall_policies/%s"
    firewall_policy_insert_path = "/fw/firewall_policies/%s/insert_rule"
    firewall_policy_remove_path = "/fw/firewall_policies/%s/remove_rule"
    firewalls_path = "/fw/firewalls"
    firewall_path = "/fw/firewalls/%s"
    net_partitions_path = "/net-partitions"
    net_partition_path = "/net-partitions/%s"

    # API has no way to report plurals, so we have to hard code them
    EXTED_PLURALS = {'routers': 'router',
                     'floatingips': 'floatingip',
                     'service_types': 'service_type',
                     'service_definitions': 'service_definition',
                     'security_groups': 'security_group',
                     'security_group_rules': 'security_group_rule',
                     'ipsecpolicies': 'ipsecpolicy',
                     'ikepolicies': 'ikepolicy',
                     'ipsec_site_connections': 'ipsec_site_connection',
                     'vpnservices': 'vpnservice',
                     'vips': 'vip',
                     'pools': 'pool',
                     'members': 'member',
                     'health_monitors': 'health_monitor',
                     'quotas': 'quota',
                     'service_providers': 'service_provider',
                     'firewall_rules': 'firewall_rule',
                     'firewall_policies': 'firewall_policy',
                     'firewalls': 'firewall',
                     'metering_labels': 'metering_label',
                     'metering_label_rules': 'metering_label_rule',
                     'net_partitions': 'net_partition',
                     'packet_filters': 'packet_filter',
                     }
    # 8192 Is the default max URI len for eventlet.wsgi.server
    MAX_URI_LEN = 8192

    def get_attr_metadata(self):
        if self.format == 'json':
            return {}
        old_request_format = self.format
        self.format = 'json'
        exts = self.list_extensions()['extensions']
        self.format = old_request_format
        ns = dict([(ext['alias'], ext['namespace']) for ext in exts])
        self.EXTED_PLURALS.update(constants.PLURALS)
        return {'plurals': self.EXTED_PLURALS,
                'xmlns': constants.XML_NS_V20,
                constants.EXT_NS: ns}

    @APIParamsCall
    def get_quotas_tenant(self, **_params):
        """Fetch tenant info in server's context for
        following quota operation.
        """
        return self.get(self.quota_path % 'tenant', params=_params)

    @APIParamsCall
    def list_quotas(self, **_params):
        """Fetch all tenants' quotas."""
        return self.get(self.quotas_path, params=_params)

    @APIParamsCall
    def show_quota(self, tenant_id, **_params):
        """Fetch information of a certain tenant's quotas."""
        return self.get(self.quota_path % (tenant_id), params=_params)

    @APIParamsCall
    def update_quota(self, tenant_id, body=None):
        """Update a tenant's quotas."""
        return self.put(self.quota_path % (tenant_id), body=body)

    @APIParamsCall
    def delete_quota(self, tenant_id):
        """Delete the specified tenant's quota values."""
        return self.delete(self.quota_path % (tenant_id))

    @APIParamsCall
    def list_extensions(self, **_params):
        """Fetch a list of all exts on server side."""
        return self.get(self.extensions_path, params=_params)

    @APIParamsCall
    def show_extension(self, ext_alias, **_params):
        """Fetch a list of all exts on server side."""
        return self.get(self.extension_path % ext_alias, params=_params)

    @APIParamsCall
    def list_ports(self, retrieve_all=True, **_params):
        """Fetches a list of all networks for a tenant."""
        # Pass filters in "params" argument to do_request
        return self.list('ports', self.ports_path, retrieve_all,
                         **_params)

    @APIParamsCall
    def show_port(self, port, **_params):
        """Fetches information of a certain network."""
        return self.get(self.port_path % (port), params=_params)

    @APIParamsCall
    def create_port(self, body=None):
        """Creates a new port."""
        return self.post(self.ports_path, body=body)

    @APIParamsCall
    def update_port(self, port, body=None):
        """Updates a port."""
        return self.put(self.port_path % (port), body=body)

    @APIParamsCall
    def delete_port(self, port):
        """Deletes the specified port."""
        return self.delete(self.port_path % (port))

    @APIParamsCall
    def list_networks(self, retrieve_all=True, **_params):
        """Fetches a list of all networks for a tenant."""
        # Pass filters in "params" argument to do_request
        return self.list('networks', self.networks_path, retrieve_all,
                         **_params)

    @APIParamsCall
    def show_network(self, network, **_params):
        """Fetches information of a certain network."""
        return self.get(self.network_path % (network), params=_params)

    @APIParamsCall
    def create_network(self, body=None):
        """Creates a new network."""
        return self.post(self.networks_path, body=body)

    @APIParamsCall
    def update_network(self, network, body=None):
        """Updates a network."""
        return self.put(self.network_path % (network), body=body)

    @APIParamsCall
    def delete_network(self, network):
        """Deletes the specified network."""
        return self.delete(self.network_path % (network))

    @APIParamsCall
    def list_subnets(self, retrieve_all=True, **_params):
        """Fetches a list of all networks for a tenant."""
        return self.list('subnets', self.subnets_path, retrieve_all,
                         **_params)

    @APIParamsCall
    def show_subnet(self, subnet, **_params):
        """Fetches information of a certain subnet."""
        return self.get(self.subnet_path % (subnet), params=_params)

    @APIParamsCall
    def create_subnet(self, body=None):
        """Creates a new subnet."""
        return self.post(self.subnets_path, body=body)

    @APIParamsCall
    def update_subnet(self, subnet, body=None):
        """Updates a subnet."""
        return self.put(self.subnet_path % (subnet), body=body)

    @APIParamsCall
    def delete_subnet(self, subnet):
        """Deletes the specified subnet."""
        return self.delete(self.subnet_path % (subnet))

    @APIParamsCall
    def list_routers(self, retrieve_all=True, **_params):
        """Fetches a list of all routers for a tenant."""
        # Pass filters in "params" argument to do_request
        return self.list('routers', self.routers_path, retrieve_all,
                         **_params)

    @APIParamsCall
    def show_router(self, router, **_params):
        """Fetches information of a certain router."""
        return self.get(self.router_path % (router), params=_params)

    @APIParamsCall
    def create_router(self, body=None):
        """Creates a new router."""
        return self.post(self.routers_path, body=body)

    @APIParamsCall
    def update_router(self, router, body=None):
        """Updates a router."""
        return self.put(self.router_path % (router), body=body)

    @APIParamsCall
    def delete_router(self, router):
        """Deletes the specified router."""
        return self.delete(self.router_path % (router))

    @APIParamsCall
    def add_interface_router(self, router, body=None):
        """Adds an internal network interface to the specified router."""
        return self.put((self.router_path % router) + "/add_router_interface",
                        body=body)

    @APIParamsCall
    def remove_interface_router(self, router, body=None):
        """Removes an internal network interface from the specified router."""
        return self.put((self.router_path % router) +
                        "/remove_router_interface", body=body)

    @APIParamsCall
    def add_gateway_router(self, router, body=None):
        """Adds an external network gateway to the specified router."""
        return self.put((self.router_path % router),
                        body={'router': {'external_gateway_info': body}})

    @APIParamsCall
    def remove_gateway_router(self, router):
        """Removes an external network gateway from the specified router."""
        return self.put((self.router_path % router),
                        body={'router': {'external_gateway_info': {}}})

    @APIParamsCall
    def list_floatingips(self, retrieve_all=True, **_params):
        """Fetches a list of all floatingips for a tenant."""
        # Pass filters in "params" argument to do_request
        return self.list('floatingips', self.floatingips_path, retrieve_all,
                         **_params)

    @APIParamsCall
    def show_floatingip(self, floatingip, **_params):
        """Fetches information of a certain floatingip."""
        return self.get(self.floatingip_path % (floatingip), params=_params)

    @APIParamsCall
    def create_floatingip(self, body=None):
        """Creates a new floatingip."""
        return self.post(self.floatingips_path, body=body)

    @APIParamsCall
    def update_floatingip(self, floatingip, body=None):
        """Updates a floatingip."""
        return self.put(self.floatingip_path % (floatingip), body=body)

    @APIParamsCall
    def delete_floatingip(self, floatingip):
        """Deletes the specified floatingip."""
        return self.delete(self.floatingip_path % (floatingip))

    @APIParamsCall
    def create_security_group(self, body=None):
        """Creates a new security group."""
        return self.post(self.security_groups_path, body=body)

    @APIParamsCall
    def update_security_group(self, security_group, body=None):
        """Updates a security group."""
        return self.put(self.security_group_path %
                        security_group, body=body)

    @APIParamsCall
    def list_security_groups(self, retrieve_all=True, **_params):
        """Fetches a list of all security groups for a tenant."""
        return self.list('security_groups', self.security_groups_path,
                         retrieve_all, **_params)

    @APIParamsCall
    def show_security_group(self, security_group, **_params):
        """Fetches information of a certain security group."""
        return self.get(self.security_group_path % (security_group),
                        params=_params)

    @APIParamsCall
    def delete_security_group(self, security_group):
        """Deletes the specified security group."""
        return self.delete(self.security_group_path % (security_group))

    @APIParamsCall
    def create_security_group_rule(self, body=None):
        """Creates a new security group rule."""
        return self.post(self.security_group_rules_path, body=body)

    @APIParamsCall
    def delete_security_group_rule(self, security_group_rule):
        """Deletes the specified security group rule."""
        return self.delete(self.security_group_rule_path %
                           (security_group_rule))

    @APIParamsCall
    def list_security_group_rules(self, retrieve_all=True, **_params):
        """Fetches a list of all security group rules for a tenant."""
        return self.list('security_group_rules',
                         self.security_group_rules_path,
                         retrieve_all, **_params)

    @APIParamsCall
    def show_security_group_rule(self, security_group_rule, **_params):
        """Fetches information of a certain security group rule."""
        return self.get(self.security_group_rule_path % (security_group_rule),
                        params=_params)

    @APIParamsCall
    def list_vpnservices(self, retrieve_all=True, **_params):
        """Fetches a list of all configured VPNServices for a tenant."""
        return self.list('vpnservices', self.vpnservices_path, retrieve_all,
                         **_params)

    @APIParamsCall
    def show_vpnservice(self, vpnservice, **_params):
        """Fetches information of a specific VPNService."""
        return self.get(self.vpnservice_path % (vpnservice), params=_params)

    @APIParamsCall
    def create_vpnservice(self, body=None):
        """Creates a new VPNService."""
        return self.post(self.vpnservices_path, body=body)

    @APIParamsCall
    def update_vpnservice(self, vpnservice, body=None):
        """Updates a VPNService."""
        return self.put(self.vpnservice_path % (vpnservice), body=body)

    @APIParamsCall
    def delete_vpnservice(self, vpnservice):
        """Deletes the specified VPNService."""
        return self.delete(self.vpnservice_path % (vpnservice))

    @APIParamsCall
    def list_ipsec_site_connections(self, retrieve_all=True, **_params):
        """Fetches all configured IPsecSiteConnections for a tenant."""
        return self.list('ipsec_site_connections',
                         self.ipsec_site_connections_path,
                         retrieve_all,
                         **_params)

    @APIParamsCall
    def show_ipsec_site_connection(self, ipsecsite_conn, **_params):
        """Fetches information of a specific IPsecSiteConnection."""
        return self.get(
            self.ipsec_site_connection_path % (ipsecsite_conn), params=_params
        )

    @APIParamsCall
    def create_ipsec_site_connection(self, body=None):
        """Creates a new IPsecSiteConnection."""
        return self.post(self.ipsec_site_connections_path, body=body)

    @APIParamsCall
    def update_ipsec_site_connection(self, ipsecsite_conn, body=None):
        """Updates an IPsecSiteConnection."""
        return self.put(
            self.ipsec_site_connection_path % (ipsecsite_conn), body=body
        )

    @APIParamsCall
    def delete_ipsec_site_connection(self, ipsecsite_conn):
        """Deletes the specified IPsecSiteConnection."""
        return self.delete(self.ipsec_site_connection_path % (ipsecsite_conn))

    @APIParamsCall
    def list_ikepolicies(self, retrieve_all=True, **_params):
        """Fetches a list of all configured IKEPolicies for a tenant."""
        return self.list('ikepolicies', self.ikepolicies_path, retrieve_all,
                         **_params)

    @APIParamsCall
    def show_ikepolicy(self, ikepolicy, **_params):
        """Fetches information of a specific IKEPolicy."""
        return self.get(self.ikepolicy_path % (ikepolicy), params=_params)

    @APIParamsCall
    def create_ikepolicy(self, body=None):
        """Creates a new IKEPolicy."""
        return self.post(self.ikepolicies_path, body=body)

    @APIParamsCall
    def update_ikepolicy(self, ikepolicy, body=None):
        """Updates an IKEPolicy."""
        return self.put(self.ikepolicy_path % (ikepolicy), body=body)

    @APIParamsCall
    def delete_ikepolicy(self, ikepolicy):
        """Deletes the specified IKEPolicy."""
        return self.delete(self.ikepolicy_path % (ikepolicy))

    @APIParamsCall
    def list_ipsecpolicies(self, retrieve_all=True, **_params):
        """Fetches a list of all configured IPsecPolicies for a tenant."""
        return self.list('ipsecpolicies',
                         self.ipsecpolicies_path,
                         retrieve_all,
                         **_params)

    @APIParamsCall
    def show_ipsecpolicy(self, ipsecpolicy, **_params):
        """Fetches information of a specific IPsecPolicy."""
        return self.get(self.ipsecpolicy_path % (ipsecpolicy), params=_params)

    @APIParamsCall
    def create_ipsecpolicy(self, body=None):
        """Creates a new IPsecPolicy."""
        return self.post(self.ipsecpolicies_path, body=body)

    @APIParamsCall
    def update_ipsecpolicy(self, ipsecpolicy, body=None):
        """Updates an IPsecPolicy."""
        return self.put(self.ipsecpolicy_path % (ipsecpolicy), body=body)

    @APIParamsCall
    def delete_ipsecpolicy(self, ipsecpolicy):
        """Deletes the specified IPsecPolicy."""
        return self.delete(self.ipsecpolicy_path % (ipsecpolicy))

    @APIParamsCall
    def list_vips(self, retrieve_all=True, **_params):
        """Fetches a list of all load balancer vips for a tenant."""
        # Pass filters in "params" argument to do_request
        return self.list('vips', self.vips_path, retrieve_all,
                         **_params)

    @APIParamsCall
    def show_vip(self, vip, **_params):
        """Fetches information of a certain load balancer vip."""
        return self.get(self.vip_path % (vip), params=_params)

    @APIParamsCall
    def create_vip(self, body=None):
        """Creates a new load balancer vip."""
        return self.post(self.vips_path, body=body)

    @APIParamsCall
    def update_vip(self, vip, body=None):
        """Updates a load balancer vip."""
        return self.put(self.vip_path % (vip), body=body)

    @APIParamsCall
    def delete_vip(self, vip):
        """Deletes the specified load balancer vip."""
        return self.delete(self.vip_path % (vip))

    @APIParamsCall
    def list_pools(self, retrieve_all=True, **_params):
        """Fetches a list of all load balancer pools for a tenant."""
        # Pass filters in "params" argument to do_request
        return self.list('pools', self.pools_path, retrieve_all,
                         **_params)

    @APIParamsCall
    def show_pool(self, pool, **_params):
        """Fetches information of a certain load balancer pool."""
        return self.get(self.pool_path % (pool), params=_params)

    @APIParamsCall
    def create_pool(self, body=None):
        """Creates a new load balancer pool."""
        return self.post(self.pools_path, body=body)

    @APIParamsCall
    def update_pool(self, pool, body=None):
        """Updates a load balancer pool."""
        return self.put(self.pool_path % (pool), body=body)

    @APIParamsCall
    def delete_pool(self, pool):
        """Deletes the specified load balancer pool."""
        return self.delete(self.pool_path % (pool))

    @APIParamsCall
    def retrieve_pool_stats(self, pool, **_params):
        """Retrieves stats for a certain load balancer pool."""
        return self.get(self.pool_path_stats % (pool), params=_params)

    @APIParamsCall
    def list_members(self, retrieve_all=True, **_params):
        """Fetches a list of all load balancer members for a tenant."""
        # Pass filters in "params" argument to do_request
        return self.list('members', self.members_path, retrieve_all,
                         **_params)

    @APIParamsCall
    def show_member(self, member, **_params):
        """Fetches information of a certain load balancer member."""
        return self.get(self.member_path % (member), params=_params)

    @APIParamsCall
    def create_member(self, body=None):
        """Creates a new load balancer member."""
        return self.post(self.members_path, body=body)

    @APIParamsCall
    def update_member(self, member, body=None):
        """Updates a load balancer member."""
        return self.put(self.member_path % (member), body=body)

    @APIParamsCall
    def delete_member(self, member):
        """Deletes the specified load balancer member."""
        return self.delete(self.member_path % (member))

    @APIParamsCall
    def list_health_monitors(self, retrieve_all=True, **_params):
        """Fetches a list of all load balancer health monitors for a tenant."""
        # Pass filters in "params" argument to do_request
        return self.list('health_monitors', self.health_monitors_path,
                         retrieve_all, **_params)

    @APIParamsCall
    def show_health_monitor(self, health_monitor, **_params):
        """Fetches information of a certain load balancer health monitor."""
        return self.get(self.health_monitor_path % (health_monitor),
                        params=_params)

    @APIParamsCall
    def create_health_monitor(self, body=None):
        """Creates a new load balancer health monitor."""
        return self.post(self.health_monitors_path, body=body)

    @APIParamsCall
    def update_health_monitor(self, health_monitor, body=None):
        """Updates a load balancer health monitor."""
        return self.put(self.health_monitor_path % (health_monitor), body=body)

    @APIParamsCall
    def delete_health_monitor(self, health_monitor):
        """Deletes the specified load balancer health monitor."""
        return self.delete(self.health_monitor_path % (health_monitor))

    @APIParamsCall
    def associate_health_monitor(self, pool, body):
        """Associate  specified load balancer health monitor and pool."""
        return self.post(self.associate_pool_health_monitors_path % (pool),
                         body=body)

    @APIParamsCall
    def disassociate_health_monitor(self, pool, health_monitor):
        """Disassociate specified load balancer health monitor and pool."""
        path = (self.disassociate_pool_health_monitors_path %
                {'pool': pool, 'health_monitor': health_monitor})
        return self.delete(path)

    @APIParamsCall
    def create_qos_queue(self, body=None):
        """Creates a new queue."""
        return self.post(self.qos_queues_path, body=body)

    @APIParamsCall
    def list_qos_queues(self, **_params):
        """Fetches a list of all queues for a tenant."""
        return self.get(self.qos_queues_path, params=_params)

    @APIParamsCall
    def show_qos_queue(self, queue, **_params):
        """Fetches information of a certain queue."""
        return self.get(self.qos_queue_path % (queue),
                        params=_params)

    @APIParamsCall
    def delete_qos_queue(self, queue):
        """Deletes the specified queue."""
        return self.delete(self.qos_queue_path % (queue))

    @APIParamsCall
    def list_agents(self, **_params):
        """Fetches agents."""
        # Pass filters in "params" argument to do_request
        return self.get(self.agents_path, params=_params)

    @APIParamsCall
    def show_agent(self, agent, **_params):
        """Fetches information of a certain agent."""
        return self.get(self.agent_path % (agent), params=_params)

    @APIParamsCall
    def update_agent(self, agent, body=None):
        """Updates an agent."""
        return self.put(self.agent_path % (agent), body=body)

    @APIParamsCall
    def delete_agent(self, agent):
        """Deletes the specified agent."""
        return self.delete(self.agent_path % (agent))

    @APIParamsCall
    def list_network_gateways(self, **_params):
        """Retrieve network gateways."""
        return self.get(self.network_gateways_path, params=_params)

    @APIParamsCall
    def show_network_gateway(self, gateway_id, **_params):
        """Fetch a network gateway."""
        return self.get(self.network_gateway_path % gateway_id, params=_params)

    @APIParamsCall
    def create_network_gateway(self, body=None):
        """Create a new network gateway."""
        return self.post(self.network_gateways_path, body=body)

    @APIParamsCall
    def update_network_gateway(self, gateway_id, body=None):
        """Update a network gateway."""
        return self.put(self.network_gateway_path % gateway_id, body=body)

    @APIParamsCall
    def delete_network_gateway(self, gateway_id):
        """Delete the specified network gateway."""
        return self.delete(self.network_gateway_path % gateway_id)

    @APIParamsCall
    def connect_network_gateway(self, gateway_id, body=None):
        """Connect a network gateway to the specified network."""
        base_uri = self.network_gateway_path % gateway_id
        return self.put("%s/connect_network" % base_uri, body=body)

    @APIParamsCall
    def disconnect_network_gateway(self, gateway_id, body=None):
        """Disconnect a network from the specified gateway."""
        base_uri = self.network_gateway_path % gateway_id
        return self.put("%s/disconnect_network" % base_uri, body=body)

    @APIParamsCall
    def list_gateway_devices(self, **_params):
        """Retrieve gateway devices."""
        return self.get(self.gateway_devices_path, params=_params)

    @APIParamsCall
    def show_gateway_device(self, gateway_device_id, **_params):
        """Fetch a gateway device."""
        return self.get(self.gateway_device_path % gateway_device_id,
                        params=_params)

    @APIParamsCall
    def create_gateway_device(self, body=None):
        """Create a new gateway device."""
        return self.post(self.gateway_devices_path, body=body)

    @APIParamsCall
    def update_gateway_device(self, gateway_device_id, body=None):
        """Updates a new gateway device."""
        return self.put(self.gateway_device_path % gateway_device_id,
                        body=body)

    @APIParamsCall
    def delete_gateway_device(self, gateway_device_id):
        """Delete the specified gateway device."""
        return self.delete(self.gateway_device_path % gateway_device_id)

    @APIParamsCall
    def list_dhcp_agent_hosting_networks(self, network, **_params):
        """Fetches a list of dhcp agents hosting a network."""
        return self.get((self.network_path + self.DHCP_AGENTS) % network,
                        params=_params)

    @APIParamsCall
    def list_networks_on_dhcp_agent(self, dhcp_agent, **_params):
        """Fetches a list of dhcp agents hosting a network."""
        return self.get((self.agent_path + self.DHCP_NETS) % dhcp_agent,
                        params=_params)

    @APIParamsCall
    def add_network_to_dhcp_agent(self, dhcp_agent, body=None):
        """Adds a network to dhcp agent."""
        return self.post((self.agent_path + self.DHCP_NETS) % dhcp_agent,
                         body=body)

    @APIParamsCall
    def remove_network_from_dhcp_agent(self, dhcp_agent, network_id):
        """Remove a network from dhcp agent."""
        return self.delete((self.agent_path + self.DHCP_NETS + "/%s") % (
            dhcp_agent, network_id))

    @APIParamsCall
    def list_l3_agent_hosting_routers(self, router, **_params):
        """Fetches a list of L3 agents hosting a router."""
        return self.get((self.router_path + self.L3_AGENTS) % router,
                        params=_params)

    @APIParamsCall
    def list_routers_on_l3_agent(self, l3_agent, **_params):
        """Fetches a list of L3 agents hosting a router."""
        return self.get((self.agent_path + self.L3_ROUTERS) % l3_agent,
                        params=_params)

    @APIParamsCall
    def add_router_to_l3_agent(self, l3_agent, body):
        """Adds a router to L3 agent."""
        return self.post((self.agent_path + self.L3_ROUTERS) % l3_agent,
                         body=body)

    @APIParamsCall
    def list_firewall_rules(self, retrieve_all=True, **_params):
        """Fetches a list of all firewall rules for a tenant."""
        # Pass filters in "params" argument to do_request

        return self.list('firewall_rules', self.firewall_rules_path,
                         retrieve_all, **_params)

    @APIParamsCall
    def show_firewall_rule(self, firewall_rule, **_params):
        """Fetches information of a certain firewall rule."""
        return self.get(self.firewall_rule_path % (firewall_rule),
                        params=_params)

    @APIParamsCall
    def create_firewall_rule(self, body=None):
        """Creates a new firewall rule."""
        return self.post(self.firewall_rules_path, body=body)

    @APIParamsCall
    def update_firewall_rule(self, firewall_rule, body=None):
        """Updates a firewall rule."""
        return self.put(self.firewall_rule_path % (firewall_rule), body=body)

    @APIParamsCall
    def delete_firewall_rule(self, firewall_rule):
        """Deletes the specified firewall rule."""
        return self.delete(self.firewall_rule_path % (firewall_rule))

    @APIParamsCall
    def list_firewall_policies(self, retrieve_all=True, **_params):
        """Fetches a list of all firewall policies for a tenant."""
        # Pass filters in "params" argument to do_request

        return self.list('firewall_policies', self.firewall_policies_path,
                         retrieve_all, **_params)

    @APIParamsCall
    def show_firewall_policy(self, firewall_policy, **_params):
        """Fetches information of a certain firewall policy."""
        return self.get(self.firewall_policy_path % (firewall_policy),
                        params=_params)

    @APIParamsCall
    def create_firewall_policy(self, body=None):
        """Creates a new firewall policy."""
        return self.post(self.firewall_policies_path, body=body)

    @APIParamsCall
    def update_firewall_policy(self, firewall_policy, body=None):
        """Updates a firewall policy."""
        return self.put(self.firewall_policy_path % (firewall_policy),
                        body=body)

    @APIParamsCall
    def delete_firewall_policy(self, firewall_policy):
        """Deletes the specified firewall policy."""
        return self.delete(self.firewall_policy_path % (firewall_policy))

    @APIParamsCall
    def firewall_policy_insert_rule(self, firewall_policy, body=None):
        """Inserts specified rule into firewall policy."""
        return self.put(self.firewall_policy_insert_path % (firewall_policy),
                        body=body)

    @APIParamsCall
    def firewall_policy_remove_rule(self, firewall_policy, body=None):
        """Removes specified rule from firewall policy."""
        return self.put(self.firewall_policy_remove_path % (firewall_policy),
                        body=body)

    @APIParamsCall
    def list_firewalls(self, retrieve_all=True, **_params):
        """Fetches a list of all firewals for a tenant."""
        # Pass filters in "params" argument to do_request

        return self.list('firewalls', self.firewalls_path, retrieve_all,
                         **_params)

    @APIParamsCall
    def show_firewall(self, firewall, **_params):
        """Fetches information of a certain firewall."""
        return self.get(self.firewall_path % (firewall), params=_params)

    @APIParamsCall
    def create_firewall(self, body=None):
        """Creates a new firewall."""
        return self.post(self.firewalls_path, body=body)

    @APIParamsCall
    def update_firewall(self, firewall, body=None):
        """Updates a firewall."""
        return self.put(self.firewall_path % (firewall), body=body)

    @APIParamsCall
    def delete_firewall(self, firewall):
        """Deletes the specified firewall."""
        return self.delete(self.firewall_path % (firewall))

    @APIParamsCall
    def remove_router_from_l3_agent(self, l3_agent, router_id):
        """Remove a router from l3 agent."""
        return self.delete((self.agent_path + self.L3_ROUTERS + "/%s") % (
            l3_agent, router_id))

    @APIParamsCall
    def get_lbaas_agent_hosting_pool(self, pool, **_params):
        """Fetches a loadbalancer agent hosting a pool."""
        return self.get((self.pool_path + self.LOADBALANCER_AGENT) % pool,
                        params=_params)

    @APIParamsCall
    def list_pools_on_lbaas_agent(self, lbaas_agent, **_params):
        """Fetches a list of pools hosted by the loadbalancer agent."""
        return self.get((self.agent_path + self.LOADBALANCER_POOLS) %
                        lbaas_agent, params=_params)

    @APIParamsCall
    def list_service_providers(self, retrieve_all=True, **_params):
        """Fetches service providers."""
        # Pass filters in "params" argument to do_request
        return self.list('service_providers', self.service_providers_path,
                         retrieve_all, **_params)

    def list_credentials(self, **_params):
        """Fetch a list of all credentials for a tenant."""
        return self.get(self.credentials_path, params=_params)

    @APIParamsCall
    def show_credential(self, credential, **_params):
        """Fetch a credential."""
        return self.get(self.credential_path % (credential), params=_params)

    @APIParamsCall
    def create_credential(self, body=None):
        """Create a new credential."""
        return self.post(self.credentials_path, body=body)

    @APIParamsCall
    def update_credential(self, credential, body=None):
        """Update a credential."""
        return self.put(self.credential_path % (credential), body=body)

    @APIParamsCall
    def delete_credential(self, credential):
        """Delete the specified credential."""
        return self.delete(self.credential_path % (credential))

    def list_network_profile_bindings(self, **params):
        """Fetch a list of all tenants associated for a network profile."""
        return self.get(self.network_profile_bindings_path, params=params)

    @APIParamsCall
    def list_network_profiles(self, **params):
        """Fetch a list of all network profiles for a tenant."""
        return self.get(self.network_profiles_path, params=params)

    @APIParamsCall
    def show_network_profile(self, profile, **params):
        """Fetch a network profile."""
        return self.get(self.network_profile_path % (profile), params=params)

    @APIParamsCall
    def create_network_profile(self, body=None):
        """Create a network profile."""
        return self.post(self.network_profiles_path, body=body)

    @APIParamsCall
    def update_network_profile(self, profile, body=None):
        """Update a network profile."""
        return self.put(self.network_profile_path % (profile), body=body)

    @APIParamsCall
    def delete_network_profile(self, profile):
        """Delete the network profile."""
        return self.delete(self.network_profile_path % profile)

    @APIParamsCall
    def list_policy_profile_bindings(self, **params):
        """Fetch a list of all tenants associated for a policy profile."""
        return self.get(self.policy_profile_bindings_path, params=params)

    @APIParamsCall
    def list_policy_profiles(self, **params):
        """Fetch a list of all network profiles for a tenant."""
        return self.get(self.policy_profiles_path, params=params)

    @APIParamsCall
    def show_policy_profile(self, profile, **params):
        """Fetch a network profile."""
        return self.get(self.policy_profile_path % (profile), params=params)

    @APIParamsCall
    def update_policy_profile(self, profile, body=None):
        """Update a policy profile."""
        return self.put(self.policy_profile_path % (profile), body=body)

    @APIParamsCall
    def create_metering_label(self, body=None):
        """Creates a metering label."""
        return self.post(self.metering_labels_path, body=body)

    @APIParamsCall
    def delete_metering_label(self, label):
        """Deletes the specified metering label."""
        return self.delete(self.metering_label_path % (label))

    @APIParamsCall
    def list_metering_labels(self, retrieve_all=True, **_params):
        """Fetches a list of all metering labels for a tenant."""
        return self.list('metering_labels', self.metering_labels_path,
                         retrieve_all, **_params)

    @APIParamsCall
    def show_metering_label(self, metering_label, **_params):
        """Fetches information of a certain metering label."""
        return self.get(self.metering_label_path %
                        (metering_label), params=_params)

    @APIParamsCall
    def create_metering_label_rule(self, body=None):
        """Creates a metering label rule."""
        return self.post(self.metering_label_rules_path, body=body)

    @APIParamsCall
    def delete_metering_label_rule(self, rule):
        """Deletes the specified metering label rule."""
        return self.delete(self.metering_label_rule_path % (rule))

    @APIParamsCall
    def list_metering_label_rules(self, retrieve_all=True, **_params):
        """Fetches a list of all metering label rules for a label."""
        return self.list('metering_label_rules',
                         self.metering_label_rules_path, retrieve_all,
                         **_params)

    @APIParamsCall
    def show_metering_label_rule(self, metering_label_rule, **_params):
        """Fetches information of a certain metering label rule."""
        return self.get(self.metering_label_rule_path %
                        (metering_label_rule), params=_params)

    @APIParamsCall
    def list_net_partitions(self, **params):
        """Fetch a list of all network partitions for a tenant."""
        return self.get(self.net_partitions_path, params=params)

    @APIParamsCall
    def show_net_partition(self, netpartition, **params):
        """Fetch a network partition."""
        return self.get(self.net_partition_path % (netpartition),
                        params=params)

    @APIParamsCall
    def create_net_partition(self, body=None):
        """Create a network partition."""
        return self.post(self.net_partitions_path, body=body)

    @APIParamsCall
    def delete_net_partition(self, netpartition):
        """Delete the network partition."""
        return self.delete(self.net_partition_path % netpartition)

    @APIParamsCall
    def create_packet_filter(self, body=None):
        """Create a new packet filter."""
        return self.post(self.packet_filters_path, body=body)

    @APIParamsCall
    def update_packet_filter(self, packet_filter_id, body=None):
        """Update a packet filter."""
        return self.put(self.packet_filter_path % packet_filter_id, body=body)

    @APIParamsCall
    def list_packet_filters(self, retrieve_all=True, **_params):
        """Fetch a list of all packet filters for a tenant."""
        return self.list('packet_filters', self.packet_filters_path,
                         retrieve_all, **_params)

    @APIParamsCall
    def show_packet_filter(self, packet_filter_id, **_params):
        """Fetch information of a certain packet filter."""
        return self.get(self.packet_filter_path % packet_filter_id,
                        params=_params)

    @APIParamsCall
    def delete_packet_filter(self, packet_filter_id):
        """Delete the specified packet filter."""
        return self.delete(self.packet_filter_path % packet_filter_id)

    def __init__(self, **kwargs):
        """Initialize a new client for the Neutron v2.0 API."""
        super(Client, self).__init__()
        self.httpclient = client.HTTPClient(**kwargs)
        self.version = '2.0'
        self.format = 'json'
        self.action_prefix = "/v%s" % (self.version)
        self.retries = 0
        self.retry_interval = 1

    def _handle_fault_response(self, status_code, response_body):
        # Create exception with HTTP status code and message
        _logger.debug(_("Error message: %s"), response_body)
        # Add deserialized error message to exception arguments
        try:
            des_error_body = self.deserialize(response_body, status_code)
        except Exception:
            # If unable to deserialized body it is probably not a
            # Neutron error
            des_error_body = {'message': response_body}
        # Raise the appropriate exception
        exception_handler_v20(status_code, des_error_body)

    def _check_uri_length(self, action):
        uri_len = len(self.httpclient.endpoint_url) + len(action)
        if uri_len > self.MAX_URI_LEN:
            raise exceptions.RequestURITooLong(
                excess=uri_len - self.MAX_URI_LEN)

    def do_request(self, method, action, body=None, headers=None, params=None):
        # Add format and tenant_id
        action += ".%s" % self.format
        action = self.action_prefix + action
        if type(params) is dict and params:
            params = utils.safe_encode_dict(params)
            action += '?' + urllib.urlencode(params, doseq=1)
        # Ensure client always has correct uri - do not guesstimate anything
        self.httpclient.authenticate_and_fetch_endpoint_url()
        self._check_uri_length(action)

        if body:
            body = self.serialize(body)
        self.httpclient.content_type = self.content_type()
        resp, replybody = self.httpclient.do_request(action, method, body=body)
        status_code = self.get_status_code(resp)
        if status_code in (requests.codes.ok,
                           requests.codes.created,
                           requests.codes.accepted,
                           requests.codes.no_content):
            return self.deserialize(replybody, status_code)
        else:
            if not replybody:
                replybody = resp.reason
            self._handle_fault_response(status_code, replybody)

    def get_auth_info(self):
        return self.httpclient.get_auth_info()

    def get_status_code(self, response):
        """Returns the integer status code from the response.

        Either a Webob.Response (used in testing) or requests.Response
        is returned.
        """
        if hasattr(response, 'status_int'):
            return response.status_int
        else:
            return response.status_code

    def serialize(self, data):
        """Serializes a dictionary into either xml or json.

        A dictionary with a single key can be passed and
        it can contain any structure.
        """
        if data is None:
            return None
        elif type(data) is dict:
            return serializer.Serializer(
                self.get_attr_metadata()).serialize(data, self.content_type())
        else:
            raise Exception(_("Unable to serialize object of type = '%s'") %
                            type(data))

    def deserialize(self, data, status_code):
        """Deserializes an xml or json string into a dictionary."""
        if status_code == 204:
            return data
        return serializer.Serializer(self.get_attr_metadata()).deserialize(
            data, self.content_type())['body']

    def content_type(self, _format=None):
        """Returns the mime-type for either 'xml' or 'json'.

        Defaults to the currently set format.
        """
        _format = _format or self.format
        return "application/%s" % (_format)

    def retry_request(self, method, action, body=None,
                      headers=None, params=None):
        """Call do_request with the default retry configuration.

        Only idempotent requests should retry failed connection attempts.
        :raises: ConnectionFailed if the maximum # of retries is exceeded
        """
        max_attempts = self.retries + 1
        for i in range(max_attempts):
            try:
                return self.do_request(method, action, body=body,
                                       headers=headers, params=params)
            except exceptions.ConnectionFailed:
                # Exception has already been logged by do_request()
                if i < self.retries:
                    _logger.debug(_('Retrying connection to Neutron service'))
                    time.sleep(self.retry_interval)

        raise exceptions.ConnectionFailed(reason=_("Maximum attempts reached"))

    def delete(self, action, body=None, headers=None, params=None):
        return self.retry_request("DELETE", action, body=body,
                                  headers=headers, params=params)

    def get(self, action, body=None, headers=None, params=None):
        return self.retry_request("GET", action, body=body,
                                  headers=headers, params=params)

    def post(self, action, body=None, headers=None, params=None):
        # Do not retry POST requests to avoid the orphan objects problem.
        return self.do_request("POST", action, body=body,
                               headers=headers, params=params)

    def put(self, action, body=None, headers=None, params=None):
        return self.retry_request("PUT", action, body=body,
                                  headers=headers, params=params)

    def list(self, collection, path, retrieve_all=True, **params):
        if retrieve_all:
            res = []
            for r in self._pagination(collection, path, **params):
                res.extend(r[collection])
            return {collection: res}
        else:
            return self._pagination(collection, path, **params)

    def _pagination(self, collection, path, **params):
        if params.get('page_reverse', False):
            linkrel = 'previous'
        else:
            linkrel = 'next'
        next = True
        while next:
            res = self.get(path, params=params)
            yield res
            next = False
            try:
                for link in res['%s_links' % collection]:
                    if link['rel'] == linkrel:
                        query_str = urlparse.urlparse(link['href']).query
                        params = urlparse.parse_qs(query_str)
                        next = True
                        break
            except KeyError:
                break

########NEW FILE########
__FILENAME__ = version
# Copyright (c) 2013 Hewlett-Packard Development Company, L.P.
# All Rights Reserved
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.
#
# vim: tabstop=4 shiftwidth=4 softtabstop=4
# @author: Carl Baldwin, Hewlett-Packard

import pbr.version


__version__ = pbr.version.VersionInfo('python-neutronclient').version_string()

########NEW FILE########
