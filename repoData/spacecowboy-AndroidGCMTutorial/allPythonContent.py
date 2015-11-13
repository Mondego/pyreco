__FILENAME__ = app
import os, binascii
from datetime import datetime

import endpoints
#from google.appengine.ext import endpoints
from google.appengine.ext import ndb
from protorpc import messages
from protorpc import message_types
from protorpc import remote

from app_gcm import send_link, GCMRegIdModel


def datetime_to_string(datetime_object):
    '''Converts a datetime object to a
    timestamp string in the format:

    2013-09-23 23:23:12.123456'''
    return datetime_object.isoformat(sep=' ')

def parse_timestamp(timestamp):
    '''Parses a timestamp string.
    Supports two formats, examples:

    In second precision
    >>> parse_timestamp("2013-09-29 13:21:42")
    datetime object

    Or in fractional second precision (shown in microseconds)
    >>> parse_timestamp("2013-09-29 13:21:42.123456")
    datetime object

    Returns None on failure to parse
    >>> parse_timestamp("2013-09-22")
    None
    '''
    result = None
    try:
        # Microseconds
        result = datetime.strptime(timestamp, '%Y-%m-%d %H:%M:%S.%f')
    except ValueError:
        pass

    try:
        # Seconds
        result = datetime.strptime(timestamp, '%Y-%m-%d %H:%M:%S')
    except ValueError:
        pass

    return result

class Link(messages.Message):
    url = messages.StringField(1, required=True)
    sha = messages.StringField(2)
    deleted = messages.BooleanField(3, default=False)
    timestamp = messages.StringField(4)

POST_REQUEST = endpoints.ResourceContainer(
    Link,
    regid=messages.StringField(2))


class LinkModel(ndb.Model):
    sha = ndb.StringProperty(required=True)
    url = ndb.StringProperty(required=True)
    deleted =  ndb.BooleanProperty(required=True, default=False)
    userid = ndb.UserProperty(required=True)
    timestamp = ndb.DateTimeProperty(required=True, auto_now=True)

# Used to request a link to be deleted.
# Has no body, only URL parameter
DELETE_REQUEST = endpoints.ResourceContainer(
    message_types.VoidMessage,
    sha=messages.StringField(2, required=True),
    regid=messages.StringField(3))

class LinkList(messages.Message):
    latestTimestamp = messages.StringField(2)
    links = messages.MessageField(Link, 1, repeated=True)

# Used to request the list with query parameters
LIST_REQUEST = endpoints.ResourceContainer(
    message_types.VoidMessage,
    showDeleted=messages.BooleanField(2, default=False),
    timestampMin=messages.StringField(3))

# Add a device id to the user, database model in app_gcm.py
class GCMRegId(messages.Message):
    regid = messages.StringField(1, required=True)


# Client id for webapps
CLIENT_ID = '86425096293.apps.googleusercontent.com'
# Client id for devices (android apps)
CLIENT_ID_ANDROID = '86425096293-v1er84h8bmp6c3pcsmdkgupr716u7jha.apps.googleusercontent.com'

@endpoints.api(name='links', version='v1',
               description='API for Link Management',
               allowed_client_ids=[CLIENT_ID,CLIENT_ID_ANDROID,
                                   endpoints.API_EXPLORER_CLIENT_ID]
               )
class LinkApi(remote.Service):
    '''This is the REST API. Annotations
    specify address, HTTP method and expected
    messages.'''

    @endpoints.method(POST_REQUEST, Link,
                      name = 'link.insert',
                      path = 'links',
                      http_method = 'POST')
    def add_link(self, request):
        current_user = endpoints.get_current_user()
        if current_user is None:
            raise endpoints.UnauthorizedException('Invalid token.')

        # Generate an ID if one wasn't included
        sha = request.sha
        if sha is None:
            sha = binascii.b2a_hex(os.urandom(15))
        # Construct object to save
        link = LinkModel(key=ndb.Key(LinkModel, sha),
                         sha=sha,
                         url=request.url,
                         deleted=request.deleted,
                         userid=current_user)
        # And save it
        link.put()

        # Notify through GCM
        send_link(link, request.regid)

        # Return a complete link
        return Link(url = link.url,
                    sha = link.sha,
                    timestamp = datetime_to_string(link.timestamp))

    @endpoints.method(DELETE_REQUEST, message_types.VoidMessage,
                      name = 'link.delete',
                      path = 'links/{sha}',
                      http_method = 'DELETE')
    def delete_link(self, request):
        current_user = endpoints.get_current_user()
        if current_user is None:
            raise endpoints.UnauthorizedException('Invalid token.')

        link_key = ndb.Key(LinkModel, request.sha)
        link = link_key.get()
        if link is not None:
            link.deleted = True
            link.put()
        else:
            raise endpoints.NotFoundException('No such item')

        # Notify through GCM
        send_link(link, request.regid)

        return message_types.VoidMessage()

    @endpoints.method(LIST_REQUEST, LinkList,
                      name = 'link.list',
                      path = 'links',
                      http_method = 'GET')
    def list_links(self, request):
        current_user = endpoints.get_current_user()
        if current_user is None:
            raise endpoints.UnauthorizedException('Invalid token.')

        # Build the query
        q = LinkModel.query(LinkModel.userid == current_user)
        q = q.order(LinkModel.timestamp)

        # Filter on delete
        if not request.showDeleted:
            q = q.filter(LinkModel.deleted == False)

        # Filter on timestamp
        if (request.timestampMin is not None and
            parse_timestamp(request.timestampMin) is not None):
            q = q.filter(LinkModel.timestamp >\
                         parse_timestamp(request.timestampMin))

        # Get the links
        links = []
        latest_time = None
        for link in q:
            ts = link.timestamp
            # Find the latest time
            if latest_time is None:
                latest_time = ts
            else:
                delta = ts - latest_time
                if delta.total_seconds() > 0:
                    latest_time = ts

            # Append to results
            links.append(Link(url=link.url, sha=link.sha,
                              deleted=link.deleted,
                              timestamp=datetime_to_string(ts)))

        if latest_time is None:
            latest_time = datetime(1970, 1, 1, 0, 0)

        return LinkList(links=links,
                        latestTimestamp=datetime_to_string(latest_time))

    @endpoints.method(GCMRegId, message_types.VoidMessage,
                      name = 'gcm.register',
                      path = 'registergcm',
                      http_method = 'POST')
    def register_gcm(self, request):
        current_user = endpoints.get_current_user()
        if current_user is None:
            raise endpoints.UnauthorizedException('Invalid token.')

        device = GCMRegIdModel(key=ndb.Key(GCMRegIdModel, request.regid),
                               regid=request.regid,
                               userid=current_user)
        # And save it
        device.put()

        # Return nothing
        return message_types.VoidMessage()


if __name__ != "__main__":
    # Set the application for GAE
    application = endpoints.api_server([LinkApi],
                                       restricted=False)

########NEW FILE########
__FILENAME__ = app_gcm
from __future__ import print_function, division
from threading import Thread
from functools import wraps
from gcm import GCM

from google.appengine.ext import ndb

gcm = GCM('Your API key here')

class GCMRegIdModel(ndb.Model):
    regid = ndb.StringProperty(required=True)
    userid = ndb.UserProperty(required=True)

def to_dict(link):
    return dict(sha=link.sha,
                url=link.url,
                timestamp=link.timestamp.isoformat(sep=" "),
                deleted=link.deleted)


def send_link(link, excludeid=None):
    '''Transmits the link specified by the sha to the users devices.

    Does not run in a separate thread because App-Engine did not
    seem to support that.
    '''
    # Get devices
    reg_ids = []
    query = GCMRegIdModel.query(GCMRegIdModel.userid == link.userid)

    for reg_model in query:
        reg_ids.append(reg_model.regid)

    # Dont send to origin device, if specified
    try:
        reg_ids.remove(excludeid)
    except ValueError:
        pass # not in list, or None

    if len(reg_ids) < 1:
        return

    _send(link.userid, reg_ids, to_dict(link))


def _remove_regid(regid):
    ndb.Key(GCMRegIdModel, regid).delete()


def _replace_regid(userid, oldid, newid):
    _remove_regid(oldid)
    device = GCMRegIdModel(key=ndb.Key(GCMRegIdModel, newid),
                           regid=newid,
                           userid=userid)
    device.put()


def _send(userid, rids, data):
    '''Send the data using GCM'''
    response = gcm.json_request(registration_ids=rids,
                                data=data,
                                delay_while_idle=True)

    # A device has switched registration id
    if 'canonical' in response:
        for reg_id, canonical_id in response['canonical'].items():
            # Repace reg_id with canonical_id in your database
            _replace_regid(userid, reg_id, canonical_id)

    # Handling errors
    if 'errors' in response:
        for error, reg_ids in response['errors'].items():
            # Check for errors and act accordingly
            if (error == 'NotRegistered' or
                error == 'InvalidRegistration'):
                # Remove reg_ids from database
                for regid in reg_ids:
                    _remove_regid(regid)

########NEW FILE########
__FILENAME__ = apiserving
#!/usr/bin/env python
#
# Copyright 2007 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#


"""A library supporting use of the Google API Server.

This library helps you configure a set of ProtoRPC services to act as
Endpoints backends.  In addition to translating ProtoRPC to Endpoints
compatible errors, it exposes a helper service that describes your services.

  Usage:
  1) Create an endpoints.api_server instead of a webapp.WSGIApplication.
  2) Annotate your ProtoRPC Service class with @endpoints.api to give your
     API a name, version, and short description
  3) To return an error from Google API Server raise an endpoints.*Exception
     The ServiceException classes specify the http status code returned.

     For example:
     raise endpoints.UnauthorizedException("Please log in as an admin user")


  Sample usage:
  - - - - app.yaml - - - -

  handlers:
  # Path to your API backend.
  - url: /_ah/spi/.*
    # For the legacy python runtime this would be "script: services.py"
    script: services.app

  - - - - services.py - - - -

  import endpoints
  import postservice

  app = endpoints.api_server([postservice.PostService], debug=True)

  - - - - postservice.py - - - -

  @endpoints.api(name='guestbook', version='v0.2', description='Guestbook API')
  class PostService(remote.Service):
    ...
    @endpoints.method(GetNotesRequest, Notes, name='notes.list', path='notes',
                       http_method='GET')
    def list(self, request):
      raise endpoints.UnauthorizedException("Please log in as an admin user")
"""


import cgi
import cStringIO
import httplib
import os

from endpoints import api_backend_service
from endpoints import api_config
from endpoints import api_exceptions
from endpoints import protojson
from protorpc import messages
from protorpc import remote
from protorpc.wsgi import service as wsgi_service

package = 'google.appengine.endpoints'


__all__ = [
    'api_server',
    'EndpointsErrorMessage',
    'package',
]


_ERROR_NAME_MAP = dict((httplib.responses[c.http_status], c) for c in [
    api_exceptions.BadRequestException,
    api_exceptions.ForbiddenException,
    api_exceptions.InternalServerErrorException,
    api_exceptions.NotFoundException,
    api_exceptions.UnauthorizedException,
    ])

_ALL_JSON_CONTENT_TYPES = frozenset(
    [protojson.EndpointsProtoJson.CONTENT_TYPE] +
    protojson.EndpointsProtoJson.ALTERNATIVE_CONTENT_TYPES)





class EndpointsErrorMessage(messages.Message):
  """Message for returning error back to Google Endpoints frontend.

  Fields:
    state: State of RPC, should be 'APPLICATION_ERROR'.
    error_message: Error message associated with status.
  """

  class State(messages.Enum):
    """Enumeration of possible RPC states.

    Values:
      OK: Completed successfully.
      RUNNING: Still running, not complete.
      REQUEST_ERROR: Request was malformed or incomplete.
      SERVER_ERROR: Server experienced an unexpected error.
      NETWORK_ERROR: An error occured on the network.
      APPLICATION_ERROR: The application is indicating an error.
        When in this state, RPC should also set application_error.
    """
    OK = 0
    RUNNING = 1

    REQUEST_ERROR = 2
    SERVER_ERROR = 3
    NETWORK_ERROR = 4
    APPLICATION_ERROR = 5
    METHOD_NOT_FOUND_ERROR = 6

  state = messages.EnumField(State, 1, required=True)
  error_message = messages.StringField(2)



def _get_app_revision(environ=None):
  """Gets the app revision (minor app version) of the current app.

  Args:
    environ: A dictionary with a key CURRENT_VERSION_ID that maps to a version
      string of the format <major>.<minor>.

  Returns:
    The app revision (minor version) of the current app, or None if one couldn't
    be found.
  """
  if environ is None:
    environ = os.environ
  if 'CURRENT_VERSION_ID' in environ:
    return environ['CURRENT_VERSION_ID'].split('.')[1]


class _ApiServer(object):
  """ProtoRPC wrapper, registers APIs and formats errors for Google API Server.

  - - - - ProtoRPC error format - - - -
  HTTP/1.0 400 Please log in as an admin user.
  content-type: application/json

  {
    "state": "APPLICATION_ERROR",
    "error_message": "Please log in as an admin user",
    "error_name": "unauthorized",
  }

  - - - - Reformatted error format - - - -
  HTTP/1.0 401 UNAUTHORIZED
  content-type: application/json

  {
    "state": "APPLICATION_ERROR",
    "error_message": "Please log in as an admin user"
  }
  """


  __SPI_PREFIX = '/_ah/spi/'
  __BACKEND_SERVICE_ROOT = '%sBackendService' % __SPI_PREFIX
  __SERVER_SOFTWARE = 'SERVER_SOFTWARE'




  __IGNORE_RESTRICTION_PREFIXES = ('Development/', 'WSGIServer/', 'testutil/')
  __HEADER_NAME_PEER = 'HTTP_X_APPENGINE_PEER'
  __GOOGLE_PEER = 'apiserving'


  __PROTOJSON = protojson.EndpointsProtoJson()

  def __init__(self, api_services, **kwargs):
    """Initialize an _ApiServer instance.

    The primary function of this method is to set up the WSGIApplication
    instance for the service handlers described by the services passed in.
    Additionally, it registers each API in ApiConfigRegistry for later use
    in the BackendService.getApiConfigs() (API config enumeration service).

    Args:
      api_services: List of protorpc.remote.Service classes implementing the API
        or a list of _ApiDecorator instances that decorate the service classes
        for an API.
      **kwargs: Passed through to protorpc.wsgi.service.service_handlers except:
        protocols - ProtoRPC protocols are not supported, and are disallowed.
        restricted - If True or unset, the API will only be allowed to serve to
          Google's API serving infrastructure once deployed.  Set to False to
          allow other clients.  Under dev_appserver, all clients are accepted.
          NOTE! Under experimental launch, this is not a secure restriction and
          other authentication mechanisms *must* be used to control access to
          the API.  The restriction is only intended to notify developers of
          a possible upcoming feature to securely restrict access to the API.

    Raises:
      TypeError: if protocols are configured (this feature is not supported).
      ApiConfigurationError: if there's a problem with the API config.
    """
    for entry in api_services[:]:

      if isinstance(entry, api_config._ApiDecorator):
        api_services.remove(entry)
        api_services.extend(entry.get_api_classes())

    self.api_config_registry = api_backend_service.ApiConfigRegistry()
    api_name_version_map = self.__create_name_version_map(api_services)
    protorpc_services = self.__register_services(api_name_version_map,
                                                 self.api_config_registry)


    backend_service = api_backend_service.BackendServiceImpl.new_factory(
        self.api_config_registry, _get_app_revision())
    protorpc_services.insert(0, (self.__BACKEND_SERVICE_ROOT, backend_service))


    if 'protocols' in kwargs:
      raise TypeError('__init__() got an unexpected keyword argument '
                      "'protocols'")
    protocols = remote.Protocols()
    protocols.add_protocol(self.__PROTOJSON, 'protojson')
    remote.Protocols.set_default(protocols)

    self.restricted = kwargs.pop('restricted', True)
    self.service_app = wsgi_service.service_mappings(protorpc_services,
                                                     **kwargs)

  @staticmethod
  def __create_name_version_map(api_services):
    """Create a map from API name/version to Service class/factory.

    This creates a map from an API name and version to a list of remote.Service
    factories that implement that API.

    Args:
      api_services: A list of remote.Service-derived classes or factories
        created with remote.Service.new_factory.

    Returns:
      A mapping from (api name, api version) to a list of service factories,
      for service classes that implement that API.

    Raises:
      ApiConfigurationError: If a Service class appears more than once
        in api_services.
    """
    api_name_version_map = {}
    for service_factory in api_services:
      try:
        service_class = service_factory.service_class
      except AttributeError:
        service_class = service_factory
        service_factory = service_class.new_factory()

      key = service_class.api_info.name, service_class.api_info.version
      service_factories = api_name_version_map.setdefault(key, [])
      if service_factory in service_factories:
        raise api_config.ApiConfigurationError(
            'Can\'t add the same class to an API twice: %s' %
            service_factory.service_class.__name__)

      service_factories.append(service_factory)
    return api_name_version_map

  @staticmethod
  def __register_services(api_name_version_map, api_config_registry):
    """Register & return a list of each SPI URL and class that handles that URL.

    This finds every service class in api_name_version_map, registers it with
    the given ApiConfigRegistry, builds the SPI url for that class, and adds
    the URL and its factory to a list that's returned.

    Args:
      api_name_version_map: A mapping from (api name, api version) to a list of
        service factories, as returned by __create_name_version_map.
      api_config_registry: The ApiConfigRegistry where service classes will
        be registered.

    Returns:
      A list of (SPI URL, service_factory) for each service class in
      api_name_version_map.

    Raises:
      ApiConfigurationError: If a Service class appears more than once
        in api_name_version_map.  This could happen if one class is used to
        implement multiple APIs.
    """
    generator = api_config.ApiConfigGenerator()
    protorpc_services = []
    for service_factories in api_name_version_map.itervalues():
      service_classes = [service_factory.service_class
                         for service_factory in service_factories]
      config_file = generator.pretty_print_config_to_json(service_classes)
      api_config_registry.register_spi(config_file)

      for service_factory in service_factories:
        protorpc_class_name = service_factory.service_class.__name__
        root = _ApiServer.__SPI_PREFIX + protorpc_class_name
        if any(service_map[0] == root or service_map[1] == service_factory
               for service_map in protorpc_services):
          raise api_config.ApiConfigurationError(
              'Can\'t reuse the same class in multiple APIs: %s' %
              protorpc_class_name)
        protorpc_services.append((root, service_factory))
    return protorpc_services

  def __is_request_restricted(self, environ):
    """Determine if access to SPI should be denied.

    Access will always be allowed in dev_appserver and under unit tests, but
    will only be allowed in production if the HTTP header HTTP_X_APPENGINE_PEER
    is set to 'apiserving'.  Google's Endpoints server sets this header by
    default and App Engine may securely prevent outside callers from setting it
    in the future to allow better protection of the API backend.

    Args:
      environ: WSGI environment dictionary.

    Returns:
      True if access should be denied, else False.
    """
    if not self.restricted:
      return False
    server = environ.get(self.__SERVER_SOFTWARE, '')
    for prefix in self.__IGNORE_RESTRICTION_PREFIXES:
      if server.startswith(prefix):
        return False
    peer_name = environ.get(self.__HEADER_NAME_PEER, '')
    return peer_name.lower() != self.__GOOGLE_PEER

  def __is_json_error(self, status, headers):
    """Determine if response is an error.

    Args:
      status: HTTP status code.
      headers: Dictionary of (lowercase) header name to value.

    Returns:
      True if the response was an error, else False.
    """
    content_header = headers.get('content-type', '')
    content_type, unused_params = cgi.parse_header(content_header)
    return (status.startswith('400') and
            content_type.lower() in _ALL_JSON_CONTENT_TYPES)

  def __write_error(self, status_code, error_message=None):
    """Return the HTTP status line and body for a given error code and message.

    Args:
      status_code: HTTP status code to be returned.
      error_message: Error message to be returned.

    Returns:
      Tuple (http_status, body):
        http_status: HTTP status line, e.g. 200 OK.
        body: Body of the HTTP request.
    """
    if error_message is None:
      error_message = httplib.responses[status_code]
    status = '%d %s' % (status_code, httplib.responses[status_code])
    message = EndpointsErrorMessage(
        state=EndpointsErrorMessage.State.APPLICATION_ERROR,
        error_message=error_message)
    return status, self.__PROTOJSON.encode_message(message)

  def protorpc_to_endpoints_error(self, status, body):
    """Convert a ProtoRPC error to the format expected by Google Endpoints.

    If the body does not contain an ProtoRPC message in state APPLICATION_ERROR
    the status and body will be returned unchanged.

    Args:
      status: HTTP status of the response from the backend
      body: JSON-encoded error in format expected by Endpoints frontend.

    Returns:
      Tuple of (http status, body)
    """
    try:
      rpc_error = self.__PROTOJSON.decode_message(remote.RpcStatus, body)
    except (ValueError, messages.ValidationError):
      rpc_error = remote.RpcStatus()

    if rpc_error.state == remote.RpcStatus.State.APPLICATION_ERROR:


      error_class = _ERROR_NAME_MAP.get(rpc_error.error_name)
      if error_class:
        status, body = self.__write_error(error_class.http_status,
                                          rpc_error.error_message)
    return status, body

  def __call__(self, environ, start_response):
    """Wrapper for Swarm server app.

    Args:
      environ: WSGI request environment.
      start_response: WSGI start response function.

    Returns:
      Response from service_app or appropriately transformed error response.
    """

    def StartResponse(status, headers, exc_info=None):
      """Save args, defer start_response until response body is parsed.

      Create output buffer for body to be written into.
      Note: this is not quite WSGI compliant: The body should come back as an
        iterator returned from calling service_app() but instead, StartResponse
        returns a writer that will be later called to output the body.
      See google/appengine/ext/webapp/__init__.py::Response.wsgi_write()
          write = start_response('%d %s' % self.__status, self.__wsgi_headers)
          write(body)

      Args:
        status: Http status to be sent with this response
        headers: Http headers to be sent with this response
        exc_info: Exception info to be displayed for this response
      Returns:
        callable that takes as an argument the body content
      """
      call_context['status'] = status
      call_context['headers'] = headers
      call_context['exc_info'] = exc_info

      return body_buffer.write

    if self.__is_request_restricted(environ):
      status, body = self.__write_error(httplib.NOT_FOUND)
      headers = [('Content-Type', 'text/plain')]
      exception = None

    else:

      call_context = {}
      body_buffer = cStringIO.StringIO()
      body_iter = self.service_app(environ, StartResponse)
      status = call_context['status']
      headers = call_context['headers']
      exception = call_context['exc_info']


      body = body_buffer.getvalue()

      if not body:
        body = ''.join(body_iter)


      headers_dict = dict([(k.lower(), v) for k, v in headers])
      if self.__is_json_error(status, headers_dict):
        status, body = self.protorpc_to_endpoints_error(status, body)

    start_response(status, headers, exception)
    return [body]




def api_server(api_services, **kwargs):
  """Create an api_server.

  The primary function of this method is to set up the WSGIApplication
  instance for the service handlers described by the services passed in.
  Additionally, it registers each API in ApiConfigRegistry for later use
  in the BackendService.getApiConfigs() (API config enumeration service).

  Args:
    api_services: List of protorpc.remote.Service classes implementing the API
      or a list of _ApiDecorator instances that decorate the service classes
      for an API.
    **kwargs: Passed through to protorpc.wsgi.service.service_handlers except:
      protocols - ProtoRPC protocols are not supported, and are disallowed.
      restricted - If True or unset, the API will only be allowed to serve to
        Google's API serving infrastructure once deployed.  Set to False to
        allow other clients.  Under dev_appserver, all clients are accepted.
        NOTE! Under experimental launch, this is not a secure restriction and
        other authentication mechanisms *must* be used to control access to
        the API.  The restriction is only intended to notify developers of
        a possible upcoming feature to securely restrict access to the API.

  Returns:
    A new WSGIApplication that serves the API backend and config registry.

  Raises:
    TypeError: if protocols are configured (this feature is not supported).
  """

  if 'protocols' in kwargs:
    raise TypeError("__init__() got an unexpected keyword argument 'protocols'")
  return _ApiServer(api_services, **kwargs)

########NEW FILE########
__FILENAME__ = api_backend
#!/usr/bin/env python
#
# Copyright 2007 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#


"""Interface to the BackendService that serves API configurations."""


import logging

from protorpc import message_types
from protorpc import messages
from protorpc import remote

package = 'google.appengine.endpoints'


__all__ = [
    'GetApiConfigsRequest',
    'LogMessagesRequest',
    'ApiConfigList',
    'BackendService',
    'package',
]


class GetApiConfigsRequest(messages.Message):
  """Request body for fetching API configs."""
  appRevision = messages.StringField(1)


class ApiConfigList(messages.Message):
  """List of API configuration file contents."""
  items = messages.StringField(1, repeated=True)


class LogMessagesRequest(messages.Message):
  """Request body for log messages sent by Swarm FE."""

  class LogMessage(messages.Message):
    """A single log message within a LogMessagesRequest."""

    class Level(messages.Enum):
      """Levels that can be specified for a log message."""
      debug = logging.DEBUG
      info = logging.INFO
      warning = logging.WARNING
      error = logging.ERROR
      critical = logging.CRITICAL

    level = messages.EnumField(Level, 1)
    message = messages.StringField(2, required=True)

  messages = messages.MessageField(LogMessage, 1, repeated=True)


class BackendService(remote.Service):
  """API config enumeration service used by Google API Server.

  This is a simple API providing a list of APIs served by this App Engine
  instance.  It is called by the Google API Server during app deployment
  to get an updated interface for each of the supported APIs.
  """



  @remote.method(GetApiConfigsRequest, ApiConfigList)
  def getApiConfigs(self, request):
    """Return a list of active APIs and their configuration files.

    Args:
      request: A request which may contain an app revision

    Returns:
      List of ApiConfigMessages
    """
    raise NotImplementedError()

  @remote.method(LogMessagesRequest, message_types.VoidMessage)
  def logMessages(self, request):
    """Write a log message from the Swarm FE to the log.

    Args:
      request: A log message request.

    Returns:
      Void message.
    """
    raise NotImplementedError()

########NEW FILE########
__FILENAME__ = api_backend_service
#!/usr/bin/env python
#
# Copyright 2007 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#


"""Api serving config collection service implementation.

Contains the implementation for BackendService as defined in api_backend.py.
"""



try:
  import json
except ImportError:
  import simplejson as json
import logging

from endpoints import api_backend
from endpoints import api_config
from endpoints import api_exceptions
from protorpc import message_types


__all__ = [
    'ApiConfigRegistry',
    'BackendServiceImpl',
]


class ApiConfigRegistry(object):
  """Registry of active APIs to be registered with Google API Server."""

  def __init__(self):

    self.__registered_classes = set()

    self.__api_configs = set()

    self.__api_methods = {}


  def register_spi(self, config_contents):
    """Register a single SPI and its config contents.

    Args:
      config_contents: String containing API configuration.
    """
    if config_contents is None:
      return
    parsed_config = json.loads(config_contents)
    self.__register_class(parsed_config)
    self.__api_configs.add(config_contents)
    self.__register_methods(parsed_config)

  def __register_class(self, parsed_config):
    """Register the class implementing this config, so we only add it once.

    Args:
      parsed_config: The JSON object with the API configuration being added.

    Raises:
      ApiConfigurationError: If the class has already been registered.
    """
    methods = parsed_config.get('methods')
    if not methods:
      return


    service_classes = set()
    for method in methods.itervalues():
      rosy_method = method.get('rosyMethod')
      if rosy_method and '.' in rosy_method:
        method_class = rosy_method.split('.', 1)[0]
        service_classes.add(method_class)

    for service_class in service_classes:
      if service_class in self.__registered_classes:
        raise api_config.ApiConfigurationError(
            'SPI class %s has already been registered.' % service_class)
      self.__registered_classes.add(service_class)

  def __register_methods(self, parsed_config):
    """Register all methods from the given api config file.

    Methods are stored in a map from method_name to rosyMethod,
    the name of the ProtoRPC method to be called on the backend.
    If no rosyMethod was specified the value will be None.

    Args:
      parsed_config: The JSON object with the API configuration being added.
    """
    methods = parsed_config.get('methods')
    if not methods:
      return

    for method_name, method in methods.iteritems():
      self.__api_methods[method_name] = method.get('rosyMethod')

  def lookup_api_method(self, api_method_name):
    """Looks an API method up by name to find the backend method to call.

    Args:
      api_method_name: Name of the method in the API that was called.

    Returns:
      Name of the ProtoRPC method called on the backend, or None if not found.
    """
    return self.__api_methods.get(api_method_name)

  def all_api_configs(self):
    """Return a list of all API configration specs as registered above."""
    return list(self.__api_configs)


class BackendServiceImpl(api_backend.BackendService):
  """Implementation of BackendService."""

  def __init__(self, api_config_registry, app_revision):
    """Create a new BackendService implementation.

    Args:
      api_config_registry: ApiConfigRegistry to register and look up configs.
      app_revision: string containing the current app revision.
    """
    self.__api_config_registry = api_config_registry
    self.__app_revision = app_revision




  @staticmethod
  def definition_name():
    """Override definition_name so that it is not BackendServiceImpl."""
    return api_backend.BackendService.definition_name()

  def getApiConfigs(self, request):
    """Return a list of active APIs and their configuration files.

    Args:
      request: A request which may contain an app revision

    Returns:
      ApiConfigList: A list of API config strings
    """
    if request.appRevision and request.appRevision != self.__app_revision:
      raise api_exceptions.BadRequestException(
          message='API backend app revision %s not the same as expected %s' % (
              self.__app_revision, request.appRevision))

    configs = self.__api_config_registry.all_api_configs()
    return api_backend.ApiConfigList(items=configs)

  def logMessages(self, request):
    """Write a log message from the Swarm FE to the log.

    Args:
      request: A log message request.

    Returns:
      Void message.
    """
    Level = api_backend.LogMessagesRequest.LogMessage.Level
    log = logging.getLogger(__name__)
    for message in request.messages:
      level = message.level if message.level is not None else Level.info



      record = logging.LogRecord(name=__name__, level=level.number, pathname='',
                                 lineno='', msg=message.message, args=None,
                                 exc_info=None)
      log.handle(record)

    return message_types.VoidMessage()

########NEW FILE########
__FILENAME__ = api_config
#!/usr/bin/env python
#
# Copyright 2007 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#


"""Library for generating an API configuration document for a ProtoRPC backend.

The protorpc.remote.Service is inspected and a JSON document describing
the API is returned.

    class MyResponse(messages.Message):
      bool_value = messages.BooleanField(1)
      int32_value = messages.IntegerField(2)

    class MyService(remote.Service):

      @remote.method(message_types.VoidMessage, MyResponse)
      def entries_get(self, request):
        pass

    api = ApiConfigGenerator().pretty_print_config_to_json(MyService)
"""



try:
  import json
except ImportError:
  import simplejson as json
import logging
import re

from endpoints import message_parser
from endpoints import users_id_token
from protorpc import message_types
from protorpc import messages
from protorpc import remote
from protorpc import util

try:

  from google.appengine.api import app_identity
except ImportError:

  from google.appengine.api import app_identity


__all__ = [
    'API_EXPLORER_CLIENT_ID',
    'ApiAuth',
    'ApiConfigGenerator',
    'ApiConfigurationError',
    'ApiFrontEndLimitRule',
    'ApiFrontEndLimits',
    'CacheControl',
    'ResourceContainer',
    'EMAIL_SCOPE',
    'api',
    'method',
    'AUTH_LEVEL'
]


API_EXPLORER_CLIENT_ID = '292824132082.apps.googleusercontent.com'
EMAIL_SCOPE = 'https://www.googleapis.com/auth/userinfo.email'
_PATH_VARIABLE_PATTERN = r'{([a-zA-Z_][a-zA-Z_.\d]*)}'

_MULTICLASS_MISMATCH_ERROR_TEMPLATE = (
    'Attempting to implement service %s, version %s, with multiple '
    'classes that aren\'t compatible. See docstring for api() for '
    'examples how to implement a multi-class API.')


def _Enum(docstring, *names):
  """Utility to generate enum classes used by annotations.

  Args:
    docstring: Docstring for the generated enum class.
    *names: Enum names.

  Returns:
    A class that contains enum names as attributes.
  """
  enums = dict(zip(names, range(len(names))))
  reverse = dict((value, key) for key, value in enums.iteritems())
  enums['reverse_mapping'] = reverse
  enums['__doc__'] = docstring
  return type('Enum', (object,), enums)

_AUTH_LEVEL_DOCSTRING = """
  Define the enums used by the auth_level annotation to specify frontend
  authentication requirement.

  Frontend authentication is handled by a Google API server prior to the
  request reaching backends. An early return before hitting the backend can
  happen if the request does not fulfil the requirement specified by the
  auth_level.

  Valid values of auth_level and their meanings are:

  AUTH_LEVEL.REQUIRED: Valid authentication credentials are required. Backend
    will be called only if authentication credentials are present and valid.

  AUTH_LEVEL.OPTIONAL: Authentication is optional. If authentication credentials
    are supplied they must be valid. Backend will be called if the request
    contains valid authentication credentials or no authentication credentials.

  AUTH_LEVEL.OPTIONAL_CONTINUE: Authentication is optional and will be attempted
    if authentication credentials are supplied. Invalid authentication
    credentials will be removed but the request can always reach backend.

  AUTH_LEVEL.NONE: Frontend authentication will be skipped. If authentication is
   desired, it will need to be performed by the backend.
  """

AUTH_LEVEL = _Enum(_AUTH_LEVEL_DOCSTRING, 'REQUIRED', 'OPTIONAL',
                   'OPTIONAL_CONTINUE', 'NONE')


class ApiConfigurationError(Exception):
  """Exception thrown if there's an error in the configuration/annotations."""


def _GetFieldAttributes(field):
  """Decomposes field into the needed arguments to pass to the constructor.

  This can be used to create copies of the field or to compare if two fields
  are "equal" (since __eq__ is not implemented on messages.Field).

  Args:
    field: A ProtoRPC message field (potentially to be copied).

  Raises:
    TypeError: If the field is not an instance of messages.Field.

  Returns:
    A pair of relevant arguments to be passed to the constructor for the field
      type. The first element is a list of positional arguments for the
      constructor and the second is a dictionary of keyword arguments.
  """
  if not isinstance(field, messages.Field):
    raise TypeError('Field %r to be copied not a ProtoRPC field.' % (field,))

  positional_args = []
  kwargs = {
      'required': field.required,
      'repeated': field.repeated,
      'variant': field.variant,
      'default': field._Field__default,
  }

  if isinstance(field, messages.MessageField):

    kwargs.pop('default')
    if not isinstance(field, message_types.DateTimeField):
      positional_args.insert(0, field.message_type)
  elif isinstance(field, messages.EnumField):
    positional_args.insert(0, field.type)

  return positional_args, kwargs


def _CopyField(field, number=None):
  """Copies a (potentially) owned ProtoRPC field instance into a new copy.

  Args:
    field: A ProtoRPC message field to be copied.
    number: An integer for the field to override the number of the field.
        Defaults to None.

  Raises:
    TypeError: If the field is not an instance of messages.Field.

  Returns:
    A copy of the ProtoRPC message field.
  """
  positional_args, kwargs = _GetFieldAttributes(field)
  number = number or field.number
  positional_args.append(number)
  return field.__class__(*positional_args, **kwargs)


def _CompareFields(field, other_field):
  """Checks if two ProtoRPC fields are "equal".

  Compares the arguments, rather than the id of the elements (which is
  the default __eq__ behavior) as well as the class of the fields.

  Args:
    field: A ProtoRPC message field to be compared.
    other_field: A ProtoRPC message field to be compared.

  Returns:
    Boolean indicating whether the fields are equal.
  """
  field_attrs = _GetFieldAttributes(field)
  other_field_attrs = _GetFieldAttributes(other_field)
  if field_attrs != other_field_attrs:
    return False
  return field.__class__ == other_field.__class__


class ResourceContainer(object):
  """Container for a request body resource combined with parameters.

  Used for API methods which may also have path or query parameters in addition
  to a request body.

  Attributes:
    body_message_class: A message class to represent a request body.
    parameters_message_class: A placeholder message class for request
        parameters.
  """

  __remote_info_cache = {}

  __combined_message_class = None

  def __init__(self, _body_message_class=message_types.VoidMessage, **kwargs):
    """Constructor for ResourceContainer.

    Stores a request body message class and attempts to create one from the
    keyword arguments passed in.

    Args:
      _body_message_class: A keyword argument to be treated like a positional
          argument. This will not conflict with the potential names of fields
          since they can't begin with underscore. We make this a keyword
          argument since the default VoidMessage is a very common choice given
          the prevalence of GET methods.
      **kwargs: Keyword arguments specifying field names (the named arguments)
          and instances of ProtoRPC fields as the values.
    """
    self.body_message_class = _body_message_class
    self.parameters_message_class = type('ParameterContainer',
                                         (messages.Message,), kwargs)

  @property
  def combined_message_class(self):
    """A ProtoRPC message class with both request and parameters fields.

    Caches the result in a local private variable. Uses _CopyField to create
    copies of the fields from the existing request and parameters classes since
    those fields are "owned" by the message classes.

    Raises:
      TypeError: If a field name is used in both the request message and the
        parameters but the two fields do not represent the same type.

    Returns:
      Value of combined message class for this property.
    """
    if self.__combined_message_class is not None:
      return self.__combined_message_class

    fields = {}







    field_number = 1
    for field in self.body_message_class.all_fields():
      fields[field.name] = _CopyField(field, number=field_number)
      field_number += 1
    for field in self.parameters_message_class.all_fields():
      if field.name in fields:
        if not _CompareFields(field, fields[field.name]):
          raise TypeError('Field %r contained in both parameters and request '
                          'body, but the fields differ.' % (field.name,))
        else:

          continue
      fields[field.name] = _CopyField(field, number=field_number)
      field_number += 1

    self.__combined_message_class = type('CombinedContainer',
                                         (messages.Message,), fields)
    return self.__combined_message_class

  @classmethod
  def add_to_cache(cls, remote_info, container):
    """Adds a ResourceContainer to a cache tying it to a protorpc method.

    Args:
      remote_info: Instance of protorpc.remote._RemoteMethodInfo corresponding
          to a method.
      container: An instance of ResourceContainer.

    Raises:
      TypeError: if the container is not an instance of cls.
      KeyError: if the remote method has been reference by a container before.
          This created remote method should never occur because a remote method
          is created once.
    """
    if not isinstance(container, cls):
      raise TypeError('%r not an instance of %r, could not be added to cache.' %
                      (container, cls))
    if remote_info in cls.__remote_info_cache:
      raise KeyError('Cache has collision but should not.')
    cls.__remote_info_cache[remote_info] = container

  @classmethod
  def get_request_message(cls, remote_info):
    """Gets request message or container from remote info.

    Args:
      remote_info: Instance of protorpc.remote._RemoteMethodInfo corresponding
          to a method.

    Returns:
      Either an instance of the request type from the remote or the
          ResourceContainer that was cached with the remote method.
    """
    if remote_info in cls.__remote_info_cache:
      return cls.__remote_info_cache[remote_info]
    else:
      return remote_info.request_type()


def _CheckListType(settings, allowed_type, name, allow_none=True):
  """Verify that settings in list are of the allowed type or raise TypeError.

  Args:
    settings: The list of settings to check.
    allowed_type: The allowed type of items in 'settings'.
    name: Name of the setting, added to the exception.
    allow_none: If set, None is also allowed.

  Raises:
    TypeError: if setting is not of the allowed type.

  Returns:
    The list of settings, for convenient use in assignment.
  """
  if settings is None:
    if not allow_none:
      raise TypeError('%s is None, which is not allowed.' % name)
    return settings
  if not isinstance(settings, (tuple, list)):
    raise TypeError('%s is not a list.' % name)
  if not all(isinstance(i, allowed_type) for i in settings):
    type_list = list(set(type(setting) for setting in settings))
    raise TypeError('%s contains types that don\'t match %s: %s' %
                    (name, allowed_type.__name__, type_list))
  return settings


def _CheckType(value, check_type, name, allow_none=True):
  """Check that the type of an object is acceptable.

  Args:
    value: The object whose type is to be checked.
    check_type: The type that the object must be an instance of.
    name: Name of the object, to be placed in any error messages.
    allow_none: True if value can be None, false if not.

  Raises:
    TypeError: If value is not an acceptable type.
  """
  if value is None and allow_none:
    return
  if not isinstance(value, check_type):
    raise TypeError('%s type doesn\'t match %s.' % (name, check_type))


def _CheckEnum(value, check_type, name):
  if value is None:
    return
  if value not in check_type.reverse_mapping:
    raise TypeError('%s is not a valid value for %s' % (value, name))



class _ApiInfo(object):
  """Configurable attributes of an API.

  A structured data object used to store API information associated with each
  remote.Service-derived class that implements an API.  This stores properties
  that could be different for each class (such as the path or
  collection/resource name), as well as properties common to all classes in
  the API (such as API name and version).
  """

  @util.positional(2)
  def __init__(self, common_info, resource_name=None, path=None, audiences=None,
               scopes=None, allowed_client_ids=None, auth_level=None):
    """Constructor for _ApiInfo.

    Args:
      common_info: _ApiDecorator.__ApiCommonInfo, Information that's common for
        all classes that implement an API.
      resource_name: string, The collection that the annotated class will
        implement in the API. (Default: None)
      path: string, Base request path for all methods in this API.
        (Default: None)
      audiences: list of strings, Acceptable audiences for authentication.
        (Default: None)
      scopes: list of strings, Acceptable scopes for authentication.
        (Default: None)
      allowed_client_ids: list of strings, Acceptable client IDs for auth.
        (Default: None)
      auth_level: enum from AUTH_LEVEL, Frontend authentication level.
        (Default: None)
    """
    _CheckType(resource_name, basestring, 'resource_name')
    _CheckType(path, basestring, 'path')
    _CheckListType(audiences, basestring, 'audiences')
    _CheckListType(scopes, basestring, 'scopes')
    _CheckListType(allowed_client_ids, basestring, 'allowed_client_ids')
    _CheckEnum(auth_level, AUTH_LEVEL, 'auth_level')

    self.__common_info = common_info
    self.__resource_name = resource_name
    self.__path = path
    self.__audiences = audiences
    self.__scopes = scopes
    self.__allowed_client_ids = allowed_client_ids
    self.__auth_level = auth_level

  def is_same_api(self, other):
    """Check if this implements the same API as another _ApiInfo instance."""
    if not isinstance(other, _ApiInfo):
      return False

    return self.__common_info is other.__common_info

  @property
  def name(self):
    """Name of the API."""
    return self.__common_info.name

  @property
  def version(self):
    """Version of the API."""
    return self.__common_info.version

  @property
  def description(self):
    """Description of the API."""
    return self.__common_info.description

  @property
  def hostname(self):
    """Hostname for the API."""
    return self.__common_info.hostname

  @property
  def audiences(self):
    """List of audiences accepted for the API, overriding the defaults."""
    if self.__audiences is not None:
      return self.__audiences
    return self.__common_info.audiences

  @property
  def scopes(self):
    """List of scopes accepted for the API, overriding the defaults."""
    if self.__scopes is not None:
      return self.__scopes
    return self.__common_info.scopes

  @property
  def allowed_client_ids(self):
    """List of client IDs accepted for the API, overriding the defaults."""
    if self.__allowed_client_ids is not None:
      return self.__allowed_client_ids
    return self.__common_info.allowed_client_ids

  @property
  def auth_level(self):
    """Enum from AUTH_LEVEL specifying the frontend authentication level."""
    if self.__auth_level is not None:
      return self.__auth_level
    return self.__common_info.auth_level

  @property
  def canonical_name(self):
    """Canonical name for the API."""
    return self.__common_info.canonical_name

  @property
  def auth(self):
    """Authentication configuration information for this API."""
    return self.__common_info.auth

  @property
  def owner_domain(self):
    """Domain of the owner of this API."""
    return self.__common_info.owner_domain

  @property
  def owner_name(self):
    """Name of the owner of this API."""
    return self.__common_info.owner_name

  @property
  def package_path(self):
    """Package this API belongs to, '/' delimited.  Used by client libs."""
    return self.__common_info.package_path

  @property
  def frontend_limits(self):
    """Optional query limits for unregistered developers."""
    return self.__common_info.frontend_limits

  @property
  def title(self):
    """Human readable name of this API."""
    return self.__common_info.title

  @property
  def documentation(self):
    """Link to the documentation for this version of the API."""
    return self.__common_info.documentation

  @property
  def resource_name(self):
    """Resource name for the class this decorates."""
    return self.__resource_name

  @property
  def path(self):
    """Base path prepended to any method paths in the class this decorates."""
    return self.__path


class _ApiDecorator(object):
  """Decorator for single- or multi-class APIs.

  An instance of this class can be used directly as a decorator for a
  single-class API.  Or call the api_class() method to decorate a multi-class
  API.
  """

  @util.positional(3)
  def __init__(self, name, version, description=None, hostname=None,
               audiences=None, scopes=None, allowed_client_ids=None,
               canonical_name=None, auth=None, owner_domain=None,
               owner_name=None, package_path=None, frontend_limits=None,
               title=None, documentation=None, auth_level=None):
    """Constructor for _ApiDecorator.

    Args:
      name: string, Name of the API.
      version: string, Version of the API.
      description: string, Short description of the API (Default: None)
      hostname: string, Hostname of the API (Default: app engine default host)
      audiences: list of strings, Acceptable audiences for authentication.
      scopes: list of strings, Acceptable scopes for authentication.
      allowed_client_ids: list of strings, Acceptable client IDs for auth.
      canonical_name: string, the canonical name for the API, a more human
        readable version of the name.
      auth: ApiAuth instance, the authentication configuration information
        for this API.
      owner_domain: string, the domain of the person or company that owns
        this API.  Along with owner_name, this provides hints to properly
        name client libraries for this API.
      owner_name: string, the name of the owner of this API.  Along with
        owner_domain, this provides hints to properly name client libraries
        for this API.
      package_path: string, the "package" this API belongs to.  This '/'
        delimited value specifies logical groupings of APIs.  This is used by
        client libraries of this API.
      frontend_limits: ApiFrontEndLimits, optional query limits for unregistered
        developers.
      title: string, the human readable title of your API. It is exposed in the
        discovery service.
      documentation: string, a URL where users can find documentation about this
        version of the API. This will be surfaced in the API Explorer and GPE
        plugin to allow users to learn about your service.
      auth_level: enum from AUTH_LEVEL, Frontend authentication level.
    """
    self.__common_info = self.__ApiCommonInfo(
        name, version, description=description, hostname=hostname,
        audiences=audiences, scopes=scopes,
        allowed_client_ids=allowed_client_ids,
        canonical_name=canonical_name, auth=auth, owner_domain=owner_domain,
        owner_name=owner_name, package_path=package_path,
        frontend_limits=frontend_limits, title=title,
        documentation=documentation, auth_level=auth_level)
    self.__classes = []

  class __ApiCommonInfo(object):
    """API information that's common among all classes that implement an API.

    When a remote.Service-derived class implements part of an API, there is
    some common information that remains constant across all such classes
    that implement the same API.  This includes things like name, version,
    hostname, and so on.  __ApiComminInfo stores that common information, and
    a single __ApiCommonInfo instance is shared among all classes that
    implement the same API, guaranteeing that they share the same common
    information.

    Some of these values can be overridden (such as audiences and scopes),
    while some can't and remain the same for all classes that implement
    the API (such as name and version).
    """

    @util.positional(3)
    def __init__(self, name, version, description=None, hostname=None,
                 audiences=None, scopes=None, allowed_client_ids=None,
                 canonical_name=None, auth=None, owner_domain=None,
                 owner_name=None, package_path=None, frontend_limits=None,
                 title=None, documentation=None, auth_level=None):
      """Constructor for _ApiCommonInfo.

      Args:
        name: string, Name of the API.
        version: string, Version of the API.
        description: string, Short description of the API (Default: None)
        hostname: string, Hostname of the API (Default: app engine default host)
        audiences: list of strings, Acceptable audiences for authentication.
        scopes: list of strings, Acceptable scopes for authentication.
        allowed_client_ids: list of strings, Acceptable client IDs for auth.
        canonical_name: string, the canonical name for the API, a more human
          readable version of the name.
        auth: ApiAuth instance, the authentication configuration information
          for this API.
        owner_domain: string, the domain of the person or company that owns
          this API.  Along with owner_name, this provides hints to properly
          name client libraries for this API.
        owner_name: string, the name of the owner of this API.  Along with
          owner_domain, this provides hints to properly name client libraries
          for this API.
        package_path: string, the "package" this API belongs to.  This '/'
          delimited value specifies logical groupings of APIs.  This is used by
          client libraries of this API.
        frontend_limits: ApiFrontEndLimits, optional query limits for
          unregistered developers.
        title: string, the human readable title of your API. It is exposed in
          the discovery service.
        documentation: string, a URL where users can find documentation about
          this version of the API. This will be surfaced in the API Explorer and
          GPE plugin to allow users to learn about your service.
        auth_level: enum from AUTH_LEVEL, Frontend authentication level.
      """
      _CheckType(name, basestring, 'name', allow_none=False)
      _CheckType(version, basestring, 'version', allow_none=False)
      _CheckType(description, basestring, 'description')
      _CheckType(hostname, basestring, 'hostname')
      _CheckListType(audiences, basestring, 'audiences')
      _CheckListType(scopes, basestring, 'scopes')
      _CheckListType(allowed_client_ids, basestring, 'allowed_client_ids')
      _CheckType(canonical_name, basestring, 'canonical_name')
      _CheckType(auth, ApiAuth, 'auth')
      _CheckType(owner_domain, basestring, 'owner_domain')
      _CheckType(owner_name, basestring, 'owner_name')
      _CheckType(package_path, basestring, 'package_path')
      _CheckType(frontend_limits, ApiFrontEndLimits, 'frontend_limits')
      _CheckType(title, basestring, 'title')
      _CheckType(documentation, basestring, 'documentation')
      _CheckEnum(auth_level, AUTH_LEVEL, 'auth_level')

      if hostname is None:
        hostname = app_identity.get_default_version_hostname()
      if audiences is None:
        audiences = []
      if scopes is None:
        scopes = [EMAIL_SCOPE]
      if allowed_client_ids is None:
        allowed_client_ids = [API_EXPLORER_CLIENT_ID]
      if auth_level is None:
        auth_level = AUTH_LEVEL.NONE

      self.__name = name
      self.__version = version
      self.__description = description
      self.__hostname = hostname
      self.__audiences = audiences
      self.__scopes = scopes
      self.__allowed_client_ids = allowed_client_ids
      self.__canonical_name = canonical_name
      self.__auth = auth
      self.__owner_domain = owner_domain
      self.__owner_name = owner_name
      self.__package_path = package_path
      self.__frontend_limits = frontend_limits
      self.__title = title
      self.__documentation = documentation
      self.__auth_level = auth_level

    @property
    def name(self):
      """Name of the API."""
      return self.__name

    @property
    def version(self):
      """Version of the API."""
      return self.__version

    @property
    def description(self):
      """Description of the API."""
      return self.__description

    @property
    def hostname(self):
      """Hostname for the API."""
      return self.__hostname

    @property
    def audiences(self):
      """List of audiences accepted by default for the API."""
      return self.__audiences

    @property
    def scopes(self):
      """List of scopes accepted by default for the API."""
      return self.__scopes

    @property
    def allowed_client_ids(self):
      """List of client IDs accepted by default for the API."""
      return self.__allowed_client_ids

    @property
    def auth_level(self):
      """Enum from AUTH_LEVEL specifying default frontend auth level."""
      return self.__auth_level

    @property
    def canonical_name(self):
      """Canonical name for the API."""
      return self.__canonical_name

    @property
    def auth(self):
      """Authentication configuration for this API."""
      return self.__auth

    @property
    def owner_domain(self):
      """Domain of the owner of this API."""
      return self.__owner_domain

    @property
    def owner_name(self):
      """Name of the owner of this API."""
      return self.__owner_name

    @property
    def package_path(self):
      """Package this API belongs to, '/' delimited.  Used by client libs."""
      return self.__package_path

    @property
    def frontend_limits(self):
      """Optional query limits for unregistered developers."""
      return self.__frontend_limits

    @property
    def title(self):
      """Human readable name of this API."""
      return self.__title

    @property
    def documentation(self):
      """Link to the documentation for this version of the API."""
      return self.__documentation

  def __call__(self, service_class):
    """Decorator for ProtoRPC class that configures Google's API server.

    Args:
      service_class: remote.Service class, ProtoRPC service class being wrapped.

    Returns:
      Same class with API attributes assigned in api_info.
    """
    return self.api_class()(service_class)

  def api_class(self, resource_name=None, path=None, audiences=None,
                scopes=None, allowed_client_ids=None, auth_level=None):
    """Get a decorator for a class that implements an API.

    This can be used for single-class or multi-class implementations.  It's
    used implicitly in simple single-class APIs that only use @api directly.

    Args:
      resource_name: string, Resource name for the class this decorates.
        (Default: None)
      path: string, Base path prepended to any method paths in the class this
        decorates. (Default: None)
      audiences: list of strings, Acceptable audiences for authentication.
        (Default: None)
      scopes: list of strings, Acceptable scopes for authentication.
        (Default: None)
      allowed_client_ids: list of strings, Acceptable client IDs for auth.
        (Default: None)
      auth_level: enum from AUTH_LEVEL, Frontend authentication level.
        (Default: None)

    Returns:
      A decorator function to decorate a class that implements an API.
    """

    def apiserving_api_decorator(api_class):
      """Decorator for ProtoRPC class that configures Google's API server.

      Args:
        api_class: remote.Service class, ProtoRPC service class being wrapped.

      Returns:
        Same class with API attributes assigned in api_info.
      """
      self.__classes.append(api_class)
      api_class.api_info = _ApiInfo(
          self.__common_info, resource_name=resource_name,
          path=path, audiences=audiences, scopes=scopes,
          allowed_client_ids=allowed_client_ids, auth_level=auth_level)
      return api_class

    return apiserving_api_decorator

  def get_api_classes(self):
    """Get the list of remote.Service classes that implement this API."""
    return self.__classes


class ApiAuth(object):
  """Optional authorization configuration information for an API."""

  def __init__(self, allow_cookie_auth=None, blocked_regions=None):
    """Constructor for ApiAuth, authentication information for an API.

    Args:
      allow_cookie_auth: boolean, whether cooking auth is allowed. By
        default, API methods do not allow cookie authentication, and
        require the use of OAuth2 or ID tokens. Setting this field to
        True will allow cookies to be used to access the API, with
        potentially dangerous results. Please be very cautious in enabling
        this setting, and make sure to require appropriate XSRF tokens to
        protect your API.
      blocked_regions: list of Strings, a list of 2-letter ISO region codes
        to block.
    """
    _CheckType(allow_cookie_auth, bool, 'allow_cookie_auth')
    _CheckListType(blocked_regions, basestring, 'blocked_regions')

    self.__allow_cookie_auth = allow_cookie_auth
    self.__blocked_regions = blocked_regions

  @property
  def allow_cookie_auth(self):
    """Whether cookie authentication is allowed for this API."""
    return self.__allow_cookie_auth

  @property
  def blocked_regions(self):
    """List of 2-letter ISO region codes to block."""
    return self.__blocked_regions


class ApiFrontEndLimitRule(object):
  """Custom rule to limit unregistered traffic."""

  def __init__(self, match=None, qps=None, user_qps=None, daily=None,
               analytics_id=None):
    """Constructor for ApiFrontEndLimitRule.

    Args:
      match: string, the matching rule that defines this traffic segment.
      qps: int, the aggregate QPS for this segment.
      user_qps: int, the per-end-user QPS for this segment.
      daily: int, the aggregate daily maximum for this segment.
      analytics_id: string, the project ID under which traffic for this segment
        will be logged.
    """
    _CheckType(match, basestring, 'match')
    _CheckType(qps, int, 'qps')
    _CheckType(user_qps, int, 'user_qps')
    _CheckType(daily, int, 'daily')
    _CheckType(analytics_id, basestring, 'analytics_id')

    self.__match = match
    self.__qps = qps
    self.__user_qps = user_qps
    self.__daily = daily
    self.__analytics_id = analytics_id

  @property
  def match(self):
    """The matching rule that defines this traffic segment."""
    return self.__match

  @property
  def qps(self):
    """The aggregate QPS for this segment."""
    return self.__qps

  @property
  def user_qps(self):
    """The per-end-user QPS for this segment."""
    return self.__user_qps

  @property
  def daily(self):
    """The aggregate daily maximum for this segment."""
    return self.__daily

  @property
  def analytics_id(self):
    """Project ID under which traffic for this segment will be logged."""
    return self.__analytics_id


class ApiFrontEndLimits(object):
  """Optional front end limit information for an API."""

  def __init__(self, unregistered_user_qps=None, unregistered_qps=None,
               unregistered_daily=None, rules=None):
    """Constructor for ApiFrontEndLimits, front end limit info for an API.

    Args:
      unregistered_user_qps: int, the per-end-user QPS.  Users are identified
        by their IP address. A value of 0 will block unregistered requests.
      unregistered_qps: int, an aggregate QPS upper-bound for all unregistered
        traffic. A value of 0 currently means unlimited, though it might change
        in the future. To block unregistered requests, use unregistered_user_qps
        or unregistered_daily instead.
      unregistered_daily: int, an aggregate daily upper-bound for all
        unregistered traffic. A value of 0 will block unregistered requests.
      rules: A list or tuple of ApiFrontEndLimitRule instances: custom rules
        used to apply limits to unregistered traffic.
    """
    _CheckType(unregistered_user_qps, int, 'unregistered_user_qps')
    _CheckType(unregistered_qps, int, 'unregistered_qps')
    _CheckType(unregistered_daily, int, 'unregistered_daily')
    _CheckListType(rules, ApiFrontEndLimitRule, 'rules')

    self.__unregistered_user_qps = unregistered_user_qps
    self.__unregistered_qps = unregistered_qps
    self.__unregistered_daily = unregistered_daily
    self.__rules = rules

  @property
  def unregistered_user_qps(self):
    """Per-end-user QPS limit."""
    return self.__unregistered_user_qps

  @property
  def unregistered_qps(self):
    """Aggregate QPS upper-bound for all unregistered traffic."""
    return self.__unregistered_qps

  @property
  def unregistered_daily(self):
    """Aggregate daily upper-bound for all unregistered traffic."""
    return self.__unregistered_daily

  @property
  def rules(self):
    """Custom rules used to apply limits to unregistered traffic."""
    return self.__rules


@util.positional(2)
def api(name, version, description=None, hostname=None, audiences=None,
        scopes=None, allowed_client_ids=None, canonical_name=None,
        auth=None, owner_domain=None, owner_name=None, package_path=None,
        frontend_limits=None, title=None, documentation=None, auth_level=None):
  """Decorate a ProtoRPC Service class for use by the framework above.

  This decorator can be used to specify an API name, version, description, and
  hostname for your API.

  Sample usage (python 2.7):
    @endpoints.api(name='guestbook', version='v0.2',
                   description='Guestbook API')
    class PostService(remote.Service):
      ...

  Sample usage (python 2.5):
    class PostService(remote.Service):
      ...
    endpoints.api(name='guestbook', version='v0.2',
                  description='Guestbook API')(PostService)

  Sample usage if multiple classes implement one API:
    api_root = endpoints.api(name='library', version='v1.0')

    @api_root.api_class(resource_name='shelves')
    class Shelves(remote.Service):
      ...

    @api_root.api_class(resource_name='books', path='books')
    class Books(remote.Service):
      ...

  Args:
    name: string, Name of the API.
    version: string, Version of the API.
    description: string, Short description of the API (Default: None)
    hostname: string, Hostname of the API (Default: app engine default host)
    audiences: list of strings, Acceptable audiences for authentication.
    scopes: list of strings, Acceptable scopes for authentication.
    allowed_client_ids: list of strings, Acceptable client IDs for auth.
    canonical_name: string, the canonical name for the API, a more human
      readable version of the name.
    auth: ApiAuth instance, the authentication configuration information
      for this API.
    owner_domain: string, the domain of the person or company that owns
      this API.  Along with owner_name, this provides hints to properly
      name client libraries for this API.
    owner_name: string, the name of the owner of this API.  Along with
      owner_domain, this provides hints to properly name client libraries
      for this API.
    package_path: string, the "package" this API belongs to.  This '/'
      delimited value specifies logical groupings of APIs.  This is used by
      client libraries of this API.
    frontend_limits: ApiFrontEndLimits, optional query limits for unregistered
      developers.
    title: string, the human readable title of your API. It is exposed in the
      discovery service.
    documentation: string, a URL where users can find documentation about this
      version of the API. This will be surfaced in the API Explorer and GPE
      plugin to allow users to learn about your service.
    auth_level: enum from AUTH_LEVEL, frontend authentication level.

  Returns:
    Class decorated with api_info attribute, an instance of ApiInfo.
  """

  return _ApiDecorator(name, version, description=description,
                       hostname=hostname, audiences=audiences, scopes=scopes,
                       allowed_client_ids=allowed_client_ids,
                       canonical_name=canonical_name, auth=auth,
                       owner_domain=owner_domain, owner_name=owner_name,
                       package_path=package_path,
                       frontend_limits=frontend_limits, title=title,
                       documentation=documentation, auth_level=auth_level)


class CacheControl(object):
  """Cache control settings for an API method.

  Setting is composed of a directive and maximum cache age.
  Available types:
    PUBLIC - Allows clients and proxies to cache responses.
    PRIVATE - Allows only clients to cache responses.
    NO_CACHE - Allows none to cache responses.
  """
  PUBLIC = 'public'
  PRIVATE = 'private'
  NO_CACHE = 'no-cache'
  VALID_VALUES = (PUBLIC, PRIVATE, NO_CACHE)

  def __init__(self, directive=NO_CACHE, max_age_seconds=0):
    """Constructor.

    Args:
      directive: string, Cache control directive, as above. (Default: NO_CACHE)
      max_age_seconds: int, Maximum age of cache responses. (Default: 0)
    """
    if directive not in self.VALID_VALUES:
      directive = self.NO_CACHE
    self.__directive = directive
    self.__max_age_seconds = max_age_seconds

  @property
  def directive(self):
    """The cache setting for this method, PUBLIC, PRIVATE, or NO_CACHE."""
    return self.__directive

  @property
  def max_age_seconds(self):
    """The maximum age of cache responses for this method, in seconds."""
    return self.__max_age_seconds


class _MethodInfo(object):
  """Configurable attributes of an API method.

  Consolidates settings from @method decorator and/or any settings that were
  calculating from the ProtoRPC method name, so they only need to be calculated
  once.
  """

  @util.positional(1)
  def __init__(self, name=None, path=None, http_method=None,
               cache_control=None, scopes=None, audiences=None,
               allowed_client_ids=None, auth_level=None):
    """Constructor.

    Args:
      name: string, Name of the method, prepended with <apiname>. to make it
        unique.
      path: string, Path portion of the URL to the method, for RESTful methods.
      http_method: string, HTTP method supported by the method.
      cache_control: CacheControl, Cache settings for the API method.
      scopes: list of string, OAuth2 token must contain one of these scopes.
      audiences: list of string, IdToken must contain one of these audiences.
      allowed_client_ids: list of string, Client IDs allowed to call the method.
      auth_level: enum from AUTH_LEVEL, Frontend auth level for the method.
    """
    self.__name = name
    self.__path = path
    self.__http_method = http_method
    self.__cache_control = cache_control
    self.__scopes = scopes
    self.__audiences = audiences
    self.__allowed_client_ids = allowed_client_ids
    self.__auth_level = auth_level

  def __safe_name(self, method_name):
    """Restrict method name to a-zA-Z0-9, first char lowercase."""


    safe_name = re.sub('[^\.a-zA-Z0-9]', '', method_name)

    return safe_name[0:1].lower() + safe_name[1:]

  @property
  def name(self):
    """Method name as specified in decorator or derived."""
    return self.__name

  def get_path(self, api_info):
    """Get the path portion of the URL to the method (for RESTful methods).

    Request path can be specified in the method, and it could have a base
    path prepended to it.

    Args:
      api_info: API information for this API, possibly including a base path.
        This is the api_info property on the class that's been annotated for
        this API.

    Returns:
      This method's request path (not including the http://.../_ah/api/ prefix).

    Raises:
      ApiConfigurationError: If the path isn't properly formatted.
    """
    path = self.__path or ''
    if path and path[0] == '/':

      path = path[1:]
    else:

      if api_info.path:
        path = '%s%s%s' % (api_info.path, '/' if path else '', path)


    for part in path.split('/'):
      if part and '{' in part and '}' in part:
        if re.match('^{[^{}]+}$', part) is None:
          raise ApiConfigurationError('Invalid path segment: %s (part of %s)' %
                                      (part, path))
    return path

  @property
  def http_method(self):
    """HTTP method supported by the method (e.g. GET, POST)."""
    return self.__http_method

  @property
  def cache_control(self):
    """Cache control setting for the API method."""
    return self.__cache_control

  @property
  def scopes(self):
    """List of scopes for the API method."""
    return self.__scopes

  @property
  def audiences(self):
    """List of audiences for the API method."""
    return self.__audiences

  @property
  def allowed_client_ids(self):
    """List of allowed client IDs for the API method."""
    return self.__allowed_client_ids

  @property
  def auth_level(self):
    """Enum from AUTH_LEVEL specifying default frontend auth level."""
    return self.__auth_level

  def method_id(self, api_info):
    """Computed method name."""



    if api_info.resource_name:
      resource_part = '.%s' % self.__safe_name(api_info.resource_name)
    else:
      resource_part = ''
    return '%s%s.%s' % (self.__safe_name(api_info.name), resource_part,
                        self.__safe_name(self.name))


@util.positional(2)
def method(request_message=message_types.VoidMessage,
           response_message=message_types.VoidMessage,
           name=None,
           path=None,
           http_method='POST',
           cache_control=None,
           scopes=None,
           audiences=None,
           allowed_client_ids=None,
           auth_level=None):
  """Decorate a ProtoRPC Method for use by the framework above.

  This decorator can be used to specify a method name, path, http method,
  cache control, scopes, audiences, client ids and auth_level.

  Sample usage:
    @api_config.method(RequestMessage, ResponseMessage,
                       name='insert', http_method='PUT')
    def greeting_insert(request):
      ...
      return response

  Args:
    request_message: Message type of expected request.
    response_message: Message type of expected response.
    name: string, Name of the method, prepended with <apiname>. to make it
      unique. (Default: python method name)
    path: string, Path portion of the URL to the method, for RESTful methods.
    http_method: string, HTTP method supported by the method. (Default: POST)
    cache_control: CacheControl, Cache settings for the API method.
    scopes: list of string, OAuth2 token must contain one of these scopes.
    audiences: list of string, IdToken must contain one of these audiences.
    allowed_client_ids: list of string, Client IDs allowed to call the method.
      Currently limited to 5.  If None, no calls will be allowed.
    auth_level: enum from AUTH_LEVEL, Frontend auth level for the method.

  Returns:
    'apiserving_method_wrapper' function.

  Raises:
    ValueError: if more than 5 allowed_client_ids are specified.
    TypeError: if the request_type or response_type parameters are not
      proper subclasses of messages.Message.
  """


  DEFAULT_HTTP_METHOD = 'POST'

  def check_type(setting, allowed_type, name, allow_none=True):
    """Verify that the setting is of the allowed type or raise TypeError.

    Args:
      setting: The setting to check.
      allowed_type: The allowed type.
      name: Name of the setting, added to the exception.
      allow_none: If set, None is also allowed.

    Raises:
      TypeError: if setting is not of the allowed type.

    Returns:
      The setting, for convenient use in assignment.
    """
    if (setting is None and allow_none or
        isinstance(setting, allowed_type)):
      return setting
    raise TypeError('%s is not of type %s' % (name, allowed_type.__name__))

  def apiserving_method_decorator(api_method):
    """Decorator for ProtoRPC method that configures Google's API server.

    Args:
      api_method: Original method being wrapped.

    Returns:
      Function responsible for actual invocation.
      Assigns the following attributes to invocation function:
        remote: Instance of RemoteInfo, contains remote method information.
        remote.request_type: Expected request type for remote method.
        remote.response_type: Response type returned from remote method.
        method_info: Instance of _MethodInfo, api method configuration.
      It is also assigned attributes corresponding to the aforementioned kwargs.

    Raises:
      TypeError: if the request_type or response_type parameters are not
        proper subclasses of messages.Message.
      KeyError: if the request_message is a ResourceContainer and the newly
          created remote method has been reference by the container before. This
          should never occur because a remote method is created once.
    """
    if isinstance(request_message, ResourceContainer):
      remote_decorator = remote.method(request_message.combined_message_class,
                                       response_message)
    else:
      remote_decorator = remote.method(request_message, response_message)
    remote_method = remote_decorator(api_method)

    def invoke_remote(service_instance, request):


      users_id_token._maybe_set_current_user_vars(
          invoke_remote, api_info=getattr(service_instance, 'api_info', None),
          request=request)

      return remote_method(service_instance, request)

    invoke_remote.remote = remote_method.remote
    if isinstance(request_message, ResourceContainer):
      ResourceContainer.add_to_cache(invoke_remote.remote, request_message)

    invoke_remote.method_info = _MethodInfo(
        name=name or api_method.__name__, path=path or '',
        http_method=http_method or DEFAULT_HTTP_METHOD,
        cache_control=cache_control, scopes=scopes, audiences=audiences,
        allowed_client_ids=allowed_client_ids, auth_level=auth_level)
    invoke_remote.__name__ = invoke_remote.method_info.name
    return invoke_remote

  check_type(cache_control, CacheControl, 'cache_control')
  _CheckListType(scopes, basestring, 'scopes')
  _CheckListType(audiences, basestring, 'audiences')
  _CheckListType(allowed_client_ids, basestring, 'allowed_client_ids')
  _CheckEnum(auth_level, AUTH_LEVEL, 'auth_level')
  if allowed_client_ids is not None and len(allowed_client_ids) > 5:
    raise ValueError('allowed_client_ids must have 5 or fewer entries.')
  return apiserving_method_decorator


class ApiConfigGenerator(object):
  """Generates an API configuration from a ProtoRPC service.

  Example:

    class HelloRequest(messages.Message):
      my_name = messages.StringField(1, required=True)

    class HelloResponse(messages.Message):
      hello = messages.StringField(1, required=True)

    class HelloService(remote.Service):

      @remote.method(HelloRequest, HelloResponse)
      def hello(self, request):
        return HelloResponse(hello='Hello there, %s!' %
                             request.my_name)

    api_config = ApiConfigGenerator().pretty_print_config_to_json(HelloService)

  The resulting api_config will be a JSON document describing the API
  implemented by HelloService.
  """




  __NO_BODY = 1
  __HAS_BODY = 2

  def __init__(self):
    self.__parser = message_parser.MessageTypeToJsonSchema()


    self.__request_schema = {}


    self.__response_schema = {}


    self.__id_from_name = {}

  def __get_request_kind(self, method_info):
    """Categorize the type of the request.

    Args:
      method_info: _MethodInfo, method information.

    Returns:
      The kind of request.
    """
    if method_info.http_method in ('GET', 'DELETE'):
      return self.__NO_BODY
    else:
      return self.__HAS_BODY

  def __field_to_subfields(self, field):
    """Fully describes data represented by field, including the nested case.

    In the case that the field is not a message field, we have no fields nested
    within a message definition, so we can simply return that field. However, in
    the nested case, we can't simply describe the data with one field or even
    with one chain of fields.

    For example, if we have a message field

      m_field = messages.MessageField(RefClass, 1)

    which references a class with two fields:

      class RefClass(messages.Message):
        one = messages.StringField(1)
        two = messages.IntegerField(2)

    then we would need to include both one and two to represent all the
    data contained.

    Calling __field_to_subfields(m_field) would return:
    [
      [<MessageField "m_field">, <StringField "one">],
      [<MessageField "m_field">, <StringField "two">],
    ]

    If the second field was instead a message field

      class RefClass(messages.Message):
        one = messages.StringField(1)
        two = messages.MessageField(OtherRefClass, 2)

    referencing another class with two fields

      class OtherRefClass(messages.Message):
        three = messages.BooleanField(1)
        four = messages.FloatField(2)

    then we would need to recurse one level deeper for two.

    With this change, calling __field_to_subfields(m_field) would return:
    [
      [<MessageField "m_field">, <StringField "one">],
      [<MessageField "m_field">, <StringField "two">, <StringField "three">],
      [<MessageField "m_field">, <StringField "two">, <StringField "four">],
    ]

    Args:
      field: An instance of a subclass of messages.Field.

    Returns:
      A list of lists, where each sublist is a list of fields.
    """

    if not isinstance(field, messages.MessageField):
      return [[field]]

    result = []
    for subfield in sorted(field.message_type.all_fields(),
                           key=lambda f: f.number):
      subfield_results = self.__field_to_subfields(subfield)
      for subfields_list in subfield_results:
        subfields_list.insert(0, field)
        result.append(subfields_list)
    return result





  def __field_to_parameter_type(self, field):
    """Converts the field variant type into a string describing the parameter.

    Args:
      field: An instance of a subclass of messages.Field.

    Returns:
      A string corresponding to the variant enum of the field, with a few
        exceptions. In the case of signed ints, the 's' is dropped; for the BOOL
        variant, 'boolean' is used; and for the ENUM variant, 'string' is used.

    Raises:
      TypeError: if the field variant is a message variant.
    """






    variant = field.variant
    if variant == messages.Variant.MESSAGE:
      raise TypeError('A message variant can\'t be used in a parameter.')

    custom_variant_map = {
        messages.Variant.SINT32: 'int32',
        messages.Variant.SINT64: 'int64',
        messages.Variant.BOOL: 'boolean',
        messages.Variant.ENUM: 'string',
    }
    return custom_variant_map.get(variant) or variant.name.lower()

  def __get_path_parameters(self, path):
    """Parses path paremeters from a URI path and organizes them by parameter.

    Some of the parameters may correspond to message fields, and so will be
    represented as segments corresponding to each subfield; e.g. first.second if
    the field "second" in the message field "first" is pulled from the path.

    The resulting dictionary uses the first segments as keys and each key has as
    value the list of full parameter values with first segment equal to the key.

    If the match path parameter is null, that part of the path template is
    ignored; this occurs if '{}' is used in a template.

    Args:
      path: String; a URI path, potentially with some parameters.

    Returns:
      A dictionary with strings as keys and list of strings as values.
    """
    path_parameters_by_segment = {}
    for format_var_name in re.findall(_PATH_VARIABLE_PATTERN, path):
      first_segment = format_var_name.split('.', 1)[0]
      matches = path_parameters_by_segment.setdefault(first_segment, [])
      matches.append(format_var_name)

    return path_parameters_by_segment

  def __validate_simple_subfield(self, parameter, field, segment_list,
                                 _segment_index=0):
    """Verifies that a proposed subfield actually exists and is a simple field.

    Here, simple means it is not a MessageField (nested).

    Args:
      parameter: String; the '.' delimited name of the current field being
          considered. This is relative to some root.
      field: An instance of a subclass of messages.Field. Corresponds to the
          previous segment in the path (previous relative to _segment_index),
          since this field should be a message field with the current segment
          as a field in the message class.
      segment_list: The full list of segments from the '.' delimited subfield
          being validated.
      _segment_index: Integer; used to hold the position of current segment so
          that segment_list can be passed as a reference instead of having to
          copy using segment_list[1:] at each step.

    Raises:
      TypeError: If the final subfield (indicated by _segment_index relative
        to the length of segment_list) is a MessageField.
      TypeError: If at any stage the lookup at a segment fails, e.g if a.b
        exists but a.b.c does not exist. This can happen either if a.b is not
        a message field or if a.b.c is not a property on the message class from
        a.b.
    """
    if _segment_index >= len(segment_list):

      if isinstance(field, messages.MessageField):
        field_class = field.__class__.__name__
        raise TypeError('Can\'t use messages in path. Subfield %r was '
                        'included but is a %s.' % (parameter, field_class))
      return

    segment = segment_list[_segment_index]
    parameter += '.' + segment
    try:
      field = field.type.field_by_name(segment)
    except (AttributeError, KeyError):
      raise TypeError('Subfield %r from path does not exist.' % (parameter,))

    self.__validate_simple_subfield(parameter, field, segment_list,
                                    _segment_index=_segment_index + 1)

  def __validate_path_parameters(self, field, path_parameters):
    """Verifies that all path parameters correspond to an existing subfield.

    Args:
      field: An instance of a subclass of messages.Field. Should be the root
          level property name in each path parameter in path_parameters. For
          example, if the field is called 'foo', then each path parameter should
          begin with 'foo.'.
      path_parameters: A list of Strings representing URI parameter variables.

    Raises:
      TypeError: If one of the path parameters does not start with field.name.
    """
    for param in path_parameters:
      segment_list = param.split('.')
      if segment_list[0] != field.name:
        raise TypeError('Subfield %r can\'t come from field %r.'
                        % (param, field.name))
      self.__validate_simple_subfield(field.name, field, segment_list[1:])

  def __parameter_default(self, final_subfield):
    """Returns default value of final subfield if it has one.

    If this subfield comes from a field list returned from __field_to_subfields,
    none of the fields in the subfield list can have a default except the final
    one since they all must be message fields.

    Args:
      final_subfield: A simple field from the end of a subfield list.

    Returns:
      The default value of the subfield, if any exists, with the exception of an
          enum field, which will have its value cast to a string.
    """
    if final_subfield.default:
      if isinstance(final_subfield, messages.EnumField):
        return final_subfield.default.name
      else:
        return final_subfield.default

  def __parameter_enum(self, final_subfield):
    """Returns enum descriptor of final subfield if it is an enum.

    An enum descriptor is a dictionary with keys as the names from the enum and
    each value is a dictionary with a single key "backendValue" and value equal
    to the same enum name used to stored it in the descriptor.

    The key "description" can also be used next to "backendValue", but protorpc
    Enum classes have no way of supporting a description for each value.

    Args:
      final_subfield: A simple field from the end of a subfield list.

    Returns:
      The enum descriptor for the field, if it's an enum descriptor, else
          returns None.
    """
    if isinstance(final_subfield, messages.EnumField):
      enum_descriptor = {}
      for enum_value in final_subfield.type.to_dict().keys():
        enum_descriptor[enum_value] = {'backendValue': enum_value}
      return enum_descriptor

  def __parameter_descriptor(self, subfield_list):
    """Creates descriptor for a parameter using the subfields that define it.

    Each parameter is defined by a list of fields, with all but the last being
    a message field and the final being a simple (non-message) field.

    Many of the fields in the descriptor are determined solely by the simple
    field at the end, though some (such as repeated and required) take the whole
    chain of fields into consideration.

    Args:
      subfield_list: List of fields describing the parameter.

    Returns:
      Dictionary containing a descriptor for the parameter described by the list
          of fields.
    """
    descriptor = {}
    final_subfield = subfield_list[-1]


    if all(subfield.required for subfield in subfield_list):
      descriptor['required'] = True


    descriptor['type'] = self.__field_to_parameter_type(final_subfield)


    default = self.__parameter_default(final_subfield)
    if default is not None:
      descriptor['default'] = default


    if any(subfield.repeated for subfield in subfield_list):
      descriptor['repeated'] = True


    enum_descriptor = self.__parameter_enum(final_subfield)
    if enum_descriptor is not None:
      descriptor['enum'] = enum_descriptor

    return descriptor

  def __add_parameters_from_field(self, field, path_parameters,
                                  params, param_order):
    """Adds all parameters in a field to a method parameters descriptor.

    Simple fields will only have one parameter, but a message field 'x' that
    corresponds to a message class with fields 'y' and 'z' will result in
    parameters 'x.y' and 'x.z', for example. The mapping from field to
    parameters is mostly handled by __field_to_subfields.

    Args:
      field: Field from which parameters will be added to the method descriptor.
      path_parameters: A list of parameters matched from a path for this field.
         For example for the hypothetical 'x' from above if the path was
         '/a/{x.z}/b/{other}' then this list would contain only the element
         'x.z' since 'other' does not match to this field.
      params: Dictionary with parameter names as keys and parameter descriptors
          as values. This will be updated for each parameter in the field.
      param_order: List of required parameter names to give them an order in the
          descriptor. All required parameters in the field will be added to this
          list.
    """
    for subfield_list in self.__field_to_subfields(field):
      descriptor = self.__parameter_descriptor(subfield_list)

      qualified_name = '.'.join(subfield.name for subfield in subfield_list)
      in_path = qualified_name in path_parameters
      if descriptor.get('required', in_path):
        descriptor['required'] = True
        param_order.append(qualified_name)

      params[qualified_name] = descriptor

  def __params_descriptor_without_container(self, message_type,
                                            request_kind, path):
    """Describe parameters of a method which does not use a ResourceContainer.

    Makes sure that the path parameters are included in the message definition
    and adds any required fields and URL query parameters.

    This method is to preserve backwards compatibility and will be removed in
    a future release.

    Args:
      message_type: messages.Message class, Message with parameters to describe.
      request_kind: The type of request being made.
      path: string, HTTP path to method.

    Returns:
      A tuple (dict, list of string): Descriptor of the parameters, Order of the
        parameters.
    """
    params = {}
    param_order = []

    path_parameter_dict = self.__get_path_parameters(path)
    for field in sorted(message_type.all_fields(), key=lambda f: f.number):
      matched_path_parameters = path_parameter_dict.get(field.name, [])
      self.__validate_path_parameters(field, matched_path_parameters)
      if matched_path_parameters or request_kind == self.__NO_BODY:
        self.__add_parameters_from_field(field, matched_path_parameters,
                                         params, param_order)

    return params, param_order




  def __params_descriptor(self, message_type, request_kind, path):
    """Describe the parameters of a method.

    If the message_type is not a ResourceContainer, will fall back to
    __params_descriptor_without_container (which will eventually be deprecated).

    If the message type is a ResourceContainer, then all path/query parameters
    will come from the ResourceContainer. This method will also make sure all
    path parameters are covered by the message fields.

    Args:
      message_type: messages.Message or ResourceContainer class, Message with
        parameters to describe.
      request_kind: The type of request being made.
      path: string, HTTP path to method.

    Returns:
      A tuple (dict, list of string): Descriptor of the parameters, Order of the
        parameters.
    """
    path_parameter_dict = self.__get_path_parameters(path)

    if not isinstance(message_type, ResourceContainer):
      if path_parameter_dict:
        logging.warning('Method specifies path parameters but you are not '
                        'using a ResourceContainer. This will fail in future '
                        'releases; please switch to using ResourceContainer as '
                        'soon as possible.')
      return self.__params_descriptor_without_container(
          message_type, request_kind, path)


    message_type = message_type.parameters_message_class()

    params = {}
    param_order = []


    for field_name, matched_path_parameters in path_parameter_dict.iteritems():
      field = message_type.field_by_name(field_name)
      self.__validate_path_parameters(field, matched_path_parameters)


    for field in sorted(message_type.all_fields(), key=lambda f: f.number):
      matched_path_parameters = path_parameter_dict.get(field.name, [])
      self.__add_parameters_from_field(field, matched_path_parameters,
                                       params, param_order)

    return params, param_order

  def __request_message_descriptor(self, request_kind, message_type, method_id,
                                   path):
    """Describes the parameters and body of the request.

    Args:
      request_kind: The type of request being made.
      message_type: messages.Message or ResourceContainer class. The message to
          describe.
      method_id: string, Unique method identifier (e.g. 'myapi.items.method')
      path: string, HTTP path to method.

    Returns:
      Dictionary describing the request.

    Raises:
      ValueError: if the method path and request required fields do not match
    """
    descriptor = {}

    params, param_order = self.__params_descriptor(message_type,
                                                   request_kind, path)

    if isinstance(message_type, ResourceContainer):
      message_type = message_type.body_message_class()

    if (request_kind == self.__NO_BODY or
        message_type == message_types.VoidMessage()):
      descriptor['body'] = 'empty'
    else:
      descriptor['body'] = 'autoTemplate(backendRequest)'
      descriptor['bodyName'] = 'resource'
      self.__request_schema[method_id] = self.__parser.add_message(
          message_type.__class__)

    if params:
      descriptor['parameters'] = params

    if param_order:
      descriptor['parameterOrder'] = param_order

    return descriptor

  def __response_message_descriptor(self, message_type, method_id,
                                    cache_control):
    """Describes the response.

    Args:
      message_type: messages.Message class, The message to describe.
      method_id: string, Unique method identifier (e.g. 'myapi.items.method')
      cache_control: CacheControl, Cache settings for the API method.

    Returns:
      Dictionary describing the response.
    """
    descriptor = {}

    self.__parser.add_message(message_type.__class__)
    if message_type == message_types.VoidMessage():
      descriptor['body'] = 'empty'
    else:
      descriptor['body'] = 'autoTemplate(backendResponse)'
      descriptor['bodyName'] = 'resource'
      self.__response_schema[method_id] = self.__parser.ref_for_message_type(
          message_type.__class__)

    if cache_control is not None:
      descriptor['cacheControl'] = {
          'type': cache_control.directive,
          'maxAge': cache_control.max_age_seconds,
      }

    return descriptor

  def __method_descriptor(self, service, service_name, method_info,
                          protorpc_method_name, protorpc_method_info):
    """Describes a method.

    Args:
      service: endpoints.Service, Implementation of the API as a service.
      service_name: string, Name of the service.
      method_info: _MethodInfo, Configuration for the method.
      protorpc_method_name: string, Name of the method as given in the
        ProtoRPC implementation.
      protorpc_method_info: protorpc.remote._RemoteMethodInfo, ProtoRPC
        description of the method.

    Returns:
      Dictionary describing the method.
    """
    descriptor = {}

    request_message_type = ResourceContainer.get_request_message(
        protorpc_method_info.remote)
    request_kind = self.__get_request_kind(method_info)
    remote_method = protorpc_method_info.remote

    descriptor['path'] = method_info.get_path(service.api_info)
    descriptor['httpMethod'] = method_info.http_method
    descriptor['rosyMethod'] = '%s.%s' % (service_name, protorpc_method_name)
    descriptor['request'] = self.__request_message_descriptor(
        request_kind, request_message_type,
        method_info.method_id(service.api_info),
        descriptor['path'])
    descriptor['response'] = self.__response_message_descriptor(
        remote_method.response_type(), method_info.method_id(service.api_info),
        method_info.cache_control)




    scopes = (method_info.scopes
              if method_info.scopes is not None
              else service.api_info.scopes)
    if scopes:
      descriptor['scopes'] = scopes
    audiences = (method_info.audiences
                 if method_info.audiences is not None
                 else service.api_info.audiences)
    if audiences:
      descriptor['audiences'] = audiences
    allowed_client_ids = (method_info.allowed_client_ids
                          if method_info.allowed_client_ids is not None
                          else service.api_info.allowed_client_ids)
    if allowed_client_ids:
      descriptor['clientIds'] = allowed_client_ids

    if remote_method.method.__doc__:
      descriptor['description'] = remote_method.method.__doc__

    auth_level = (method_info.auth_level
                  if method_info.auth_level is not None
                  else service.api_info.auth_level)
    if auth_level:
      descriptor['authLevel'] = AUTH_LEVEL.reverse_mapping[auth_level]

    return descriptor

  def __schema_descriptor(self, services):
    """Descriptor for the all the JSON Schema used.

    Args:
      services: List of protorpc.remote.Service instances implementing an
        api/version.

    Returns:
      Dictionary containing all the JSON Schema used in the service.
    """
    methods_desc = {}

    for service in services:
      protorpc_methods = service.all_remote_methods()
      for protorpc_method_name in protorpc_methods.iterkeys():
        method_id = self.__id_from_name[protorpc_method_name]

        request_response = {}

        request_schema_id = self.__request_schema.get(method_id)
        if request_schema_id:
          request_response['request'] = {
              '$ref': request_schema_id
              }

        response_schema_id = self.__response_schema.get(method_id)
        if response_schema_id:
          request_response['response'] = {
              '$ref': response_schema_id
              }

        rosy_method = '%s.%s' % (service.__name__, protorpc_method_name)
        methods_desc[rosy_method] = request_response

    descriptor = {
        'methods': methods_desc,
        'schemas': self.__parser.schemas(),
        }

    return descriptor

  def __get_merged_api_info(self, services):
    """Builds a description of an API.

    Args:
      services: List of protorpc.remote.Service instances implementing an
        api/version.

    Returns:
      The _ApiInfo object to use for the API that the given services implement.

    Raises:
      ApiConfigurationError: If there's something wrong with the API
        configuration, such as a multiclass API decorated with different API
        descriptors (see the docstring for api()).
    """
    merged_api_info = services[0].api_info



    for service in services[1:]:
      if not merged_api_info.is_same_api(service.api_info):
        raise ApiConfigurationError(_MULTICLASS_MISMATCH_ERROR_TEMPLATE % (
            service.api_info.name, service.api_info.version))

    return merged_api_info

  def __auth_descriptor(self, api_info):
    if api_info.auth is None:
      return None

    auth_descriptor = {}
    if api_info.auth.allow_cookie_auth is not None:
      auth_descriptor['allowCookieAuth'] = api_info.auth.allow_cookie_auth
    if api_info.auth.blocked_regions:
      auth_descriptor['blockedRegions'] = api_info.auth.blocked_regions

    return auth_descriptor

  def __frontend_limit_descriptor(self, api_info):
    if api_info.frontend_limits is None:
      return None

    descriptor = {}
    for propname, descname in (('unregistered_user_qps', 'unregisteredUserQps'),
                               ('unregistered_qps', 'unregisteredQps'),
                               ('unregistered_daily', 'unregisteredDaily')):
      if getattr(api_info.frontend_limits, propname) is not None:
        descriptor[descname] = getattr(api_info.frontend_limits, propname)

    rules = self.__frontend_limit_rules_descriptor(api_info)
    if rules:
      descriptor['rules'] = rules

    return descriptor

  def __frontend_limit_rules_descriptor(self, api_info):
    if not api_info.frontend_limits.rules:
      return None

    rules = []
    for rule in api_info.frontend_limits.rules:
      descriptor = {}
      for propname, descname in (('match', 'match'),
                                 ('qps', 'qps'),
                                 ('user_qps', 'userQps'),
                                 ('daily', 'daily'),
                                 ('analytics_id', 'analyticsId')):
        if getattr(rule, propname) is not None:
          descriptor[descname] = getattr(rule, propname)
      if descriptor:
        rules.append(descriptor)

    return rules

  def __api_descriptor(self, services, hostname=None):
    """Builds a description of an API.

    Args:
      services: List of protorpc.remote.Service instances implementing an
        api/version.
      hostname: string, Hostname of the API, to override the value set on the
        current service. Defaults to None.

    Returns:
      A dictionary that can be deserialized into JSON and stored as an API
      description document.

    Raises:
      ApiConfigurationError: If there's something wrong with the API
        configuration, such as a multiclass API decorated with different API
        descriptors (see the docstring for api()), or a repeated method
        signature.
    """
    merged_api_info = self.__get_merged_api_info(services)
    descriptor = self.get_descriptor_defaults(merged_api_info,
                                              hostname=hostname)
    description = merged_api_info.description
    if not description and len(services) == 1:
      description = services[0].__doc__
    if description:
      descriptor['description'] = description

    auth_descriptor = self.__auth_descriptor(merged_api_info)
    if auth_descriptor:
      descriptor['auth'] = auth_descriptor

    frontend_limit_descriptor = self.__frontend_limit_descriptor(
        merged_api_info)
    if frontend_limit_descriptor:
      descriptor['frontendLimits'] = frontend_limit_descriptor

    method_map = {}
    method_collision_tracker = {}
    rest_collision_tracker = {}

    for service in services:
      remote_methods = service.all_remote_methods()
      for protorpc_meth_name, protorpc_meth_info in remote_methods.iteritems():
        method_info = getattr(protorpc_meth_info, 'method_info', None)

        if method_info is None:
          continue
        method_id = method_info.method_id(service.api_info)
        self.__id_from_name[protorpc_meth_name] = method_id
        method_map[method_id] = self.__method_descriptor(
            service, service.__name__, method_info,
            protorpc_meth_name, protorpc_meth_info)


        if method_id in method_collision_tracker:
          raise ApiConfigurationError(
              'Method %s used multiple times, in classes %s and %s' %
              (method_id, method_collision_tracker[method_id],
               service.__name__))
        else:
          method_collision_tracker[method_id] = service.__name__


        rest_identifier = (method_info.http_method,
                           method_info.get_path(service.api_info))
        if rest_identifier in rest_collision_tracker:
          raise ApiConfigurationError(
              '%s path "%s" used multiple times, in classes %s and %s' %
              (method_info.http_method, method_info.get_path(service.api_info),
               rest_collision_tracker[rest_identifier],
               service.__name__))
        else:
          rest_collision_tracker[rest_identifier] = service.__name__

    if method_map:
      descriptor['methods'] = method_map
      descriptor['descriptor'] = self.__schema_descriptor(services)

    return descriptor

  def get_descriptor_defaults(self, api_info, hostname=None):
    """Gets a default configuration for a service.

    Args:
      api_info: _ApiInfo object for this service.
      hostname: string, Hostname of the API, to override the value set on the
        current service. Defaults to None.

    Returns:
      A dictionary with the default configuration.
    """
    hostname = hostname or api_info.hostname
    defaults = {
        'extends': 'thirdParty.api',
        'root': 'https://%s/_ah/api' % hostname,
        'name': api_info.name,
        'version': api_info.version,
        'defaultVersion': True,
        'abstract': False,
        'adapter': {
            'bns': 'https://%s/_ah/spi' % hostname,
            'type': 'lily',
            'deadline': 10.0
        }
    }
    if api_info.canonical_name:
      defaults['canonicalName'] = api_info.canonical_name
    if api_info.owner_domain:
      defaults['ownerDomain'] = api_info.owner_domain
    if api_info.owner_name:
      defaults['ownerName'] = api_info.owner_name
    if api_info.package_path:
      defaults['packagePath'] = api_info.package_path
    if api_info.title:
      defaults['title'] = api_info.title
    if api_info.documentation:
      defaults['documentation'] = api_info.documentation
    return defaults

  def pretty_print_config_to_json(self, services, hostname=None):
    """Description of a protorpc.remote.Service in API format.

    Args:
      services: Either a single protorpc.remote.Service or a list of them
        that implements an api/version.
      hostname: string, Hostname of the API, to override the value set on the
        current service. Defaults to None.

    Returns:
      string, The API descriptor document as JSON.
    """
    if not isinstance(services, (tuple, list)):
      services = [services]



    _CheckListType(services, remote._ServiceClass, 'services', allow_none=False)

    descriptor = self.__api_descriptor(services, hostname=hostname)
    return json.dumps(descriptor, sort_keys=True, indent=2)

########NEW FILE########
__FILENAME__ = api_exceptions
#!/usr/bin/env python
#
# Copyright 2007 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
"""A library containing exception types used by Endpoints ProtoRPC services."""



import httplib

from protorpc import remote


class ServiceException(remote.ApplicationError):
  """Base class for request/service exceptions in Endpoints."""

  def __init__(self, message=None):
    super(ServiceException, self).__init__(message,
                                           httplib.responses[self.http_status])


class BadRequestException(ServiceException):
  """Bad request exception that is mapped to a 400 response."""
  http_status = httplib.BAD_REQUEST


class ForbiddenException(ServiceException):
  """Forbidden exception that is mapped to a 403 response."""
  http_status = httplib.FORBIDDEN


class InternalServerErrorException(ServiceException):
  """Internal server exception that is mapped to a 500 response."""
  http_status = httplib.INTERNAL_SERVER_ERROR


class NotFoundException(ServiceException):
  """Not found exception that is mapped to a 404 response."""
  http_status = httplib.NOT_FOUND


class UnauthorizedException(ServiceException):
  """Unauthorized exception that is mapped to a 401 response."""
  http_status = httplib.UNAUTHORIZED

########NEW FILE########
__FILENAME__ = message_parser
#!/usr/bin/env python
#
# Copyright 2007 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#


"""Describe ProtoRPC Messages in JSON Schema.

Add protorpc.message subclasses to MessageTypeToJsonSchema and get a JSON
Schema description of all the messages.
"""


import re

from protorpc import message_types
from protorpc import messages

__all__ = ['MessageTypeToJsonSchema']


class MessageTypeToJsonSchema(object):
  """Describe ProtoRPC messages in JSON Schema.

  Add protorpc.message subclasses to MessageTypeToJsonSchema and get a JSON
  Schema description of all the messages. MessageTypeToJsonSchema handles
  all the types of fields that can appear in a message.
  """







  __FIELD_TO_SCHEMA_TYPE_MAP = {
      messages.IntegerField: {messages.Variant.INT32: ('integer', 'int32'),
                              messages.Variant.INT64: ('string', 'int64'),
                              messages.Variant.UINT32: ('integer', 'uint32'),
                              messages.Variant.UINT64: ('string', 'uint64'),
                              messages.Variant.SINT32: ('integer', 'int32'),
                              messages.Variant.SINT64: ('string', 'int64'),
                              None: ('integer', 'int32')},
      messages.FloatField: {messages.Variant.FLOAT: ('number', 'float'),
                            messages.Variant.DOUBLE: ('number', 'double'),
                            None: ('number', 'float')},
      messages.BooleanField: ('boolean', None),
      messages.BytesField: ('string', 'byte'),
      message_types.DateTimeField: ('string', 'date-time'),
      messages.StringField: ('string', None),
      messages.MessageField: ('object', None),
      messages.EnumField: ('string', None),
  }

  __DEFAULT_SCHEMA_TYPE = ('string', None)

  def __init__(self):

    self.__schemas = {}


    self.__normalized_names = {}

  def add_message(self, message_type):
    """Add a new message.

    Args:
      message_type: protorpc.message.Message class to be parsed.

    Returns:
      string, The JSON Schema id.

    Raises:
      KeyError if the Schema id for this message_type would collide with the
      Schema id of a different message_type that was already added.
    """
    name = self.__normalized_name(message_type)
    if name not in self.__schemas:
      schema = self.__message_to_schema(message_type)
      self.__schemas[name] = schema
    return name

  def ref_for_message_type(self, message_type):
    """Returns the JSON Schema id for the given message.

    Args:
      message_type: protorpc.message.Message class to be parsed.

    Returns:
      string, The JSON Schema id.

    Raises:
      KeyError: if the message hasn't been parsed via add_message().
    """
    name = self.__normalized_name(message_type)
    if name not in self.__schemas:
      raise KeyError('Message has not been parsed: %s', name)
    return name

  def schemas(self):
    """Returns the JSON Schema of all the messages.

    Returns:
      object: JSON Schema description of all messages.
    """
    return self.__schemas.copy()

  def __normalized_name(self, message_type):
    """Normalized schema name.

    Generate a normalized schema name, taking the class name and stripping out
    everything but alphanumerics, and camel casing the remaining words.
    A normalized schema name is a name that matches [a-zA-Z][a-zA-Z0-9]*

    Args:
      message_type: protorpc.message.Message class being parsed.

    Returns:
      A string, the normalized schema name.

    Raises:
      KeyError if a collision is found between normalized names.
    """


    name = message_type.definition_name()

    split_name = re.split(r'[^0-9a-zA-Z]', name)
    normalized = ''.join(
        part[0].upper() + part[1:] for part in split_name if part)

    previous = self.__normalized_names.get(normalized)
    if previous:
      if previous != name:
        raise KeyError('Both %s and %s normalize to the same schema name: %s' %
                       (name, previous, normalized))
    else:
      self.__normalized_names[normalized] = name

    return normalized

  def __message_to_schema(self, message_type):
    """Parse a single message into JSON Schema.

    Will recursively descend the message structure
    and also parse other messages references via MessageFields.

    Args:
      message_type: protorpc.messages.Message class to parse.

    Returns:
      An object representation of the schema.
    """
    name = self.__normalized_name(message_type)
    schema = {
        'id': name,
        'type': 'object',
        }
    if message_type.__doc__:
      schema['description'] = message_type.__doc__
    properties = {}
    for field in message_type.all_fields():
      descriptor = {}



      type_info = {}

      if type(field) == messages.MessageField:
        field_type = field.type().__class__
        type_info['$ref'] = self.add_message(field_type)
        if field_type.__doc__:
          descriptor['description'] = field_type.__doc__
      else:
        schema_type = self.__FIELD_TO_SCHEMA_TYPE_MAP.get(
            type(field), self.__DEFAULT_SCHEMA_TYPE)


        if isinstance(schema_type, dict):
          variant_map = schema_type
          variant = getattr(field, 'variant', None)
          if variant in variant_map:
            schema_type = variant_map[variant]
          else:

            schema_type = variant_map[None]
        type_info['type'] = schema_type[0]
        if schema_type[1]:
          type_info['format'] = schema_type[1]

      if type(field) == messages.EnumField:
        sorted_enums = sorted([enum_info for enum_info in field.type],
                              key=lambda enum_info: enum_info.number)
        type_info['enum'] = [enum_info.name for enum_info in sorted_enums]

      if field.required:
        descriptor['required'] = True

      if field.default:
        if type(field) == messages.EnumField:
          descriptor['default'] = str(field.default)
        else:
          descriptor['default'] = field.default

      if field.repeated:
        descriptor['items'] = type_info
        descriptor['type'] = 'array'
      else:
        descriptor.update(type_info)

      properties[field.name] = descriptor

    schema['properties'] = properties

    return schema

########NEW FILE########
__FILENAME__ = protojson
#!/usr/bin/env python
#
# Copyright 2007 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#


"""Endpoints-specific implementation of ProtoRPC's ProtoJson class."""


import base64

from protorpc import messages
from protorpc import protojson



__all__ = ['EndpointsProtoJson']


class EndpointsProtoJson(protojson.ProtoJson):
  """Endpoints-specific implementation of ProtoRPC's ProtoJson class.

  We need to adjust the way some types of data are encoded to ensure they're
  consistent with the existing API pipeline.  This class adjusts the JSON
  encoding as needed.

  This may be used in a multithreaded environment, so take care to ensure
  that this class (and its parent, protojson.ProtoJson) remain thread-safe.
  """

  def encode_field(self, field, value):
    """Encode a python field value to a JSON value.

    Args:
      field: A ProtoRPC field instance.
      value: A python value supported by field.

    Returns:
      A JSON serializable value appropriate for field.
    """


    if (isinstance(field, messages.IntegerField) and
        field.variant in (messages.Variant.INT64,
                          messages.Variant.UINT64,
                          messages.Variant.SINT64)):
      if value not in (None, [], ()):

        if isinstance(value, list):
          value = [str(subvalue) for subvalue in value]
        else:
          value = str(value)
        return value

    return super(EndpointsProtoJson, self).encode_field(field, value)

  def decode_field(self, field, value):
    """Decode a JSON value to a python value.

    Args:
      field: A ProtoRPC field instance.
      value: A serialized JSON value.

    Returns:
      A Python value compatible with field.
    """



    if isinstance(field, messages.BytesField):
      try:


        return base64.urlsafe_b64decode(str(value))
      except (TypeError, UnicodeEncodeError), err:
        raise messages.DecodeError('Base64 decoding error: %s' % err)

    return super(EndpointsProtoJson, self).decode_field(field, value)

########NEW FILE########
__FILENAME__ = users_id_token
#!/usr/bin/env python
#
# Copyright 2007 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#


"""Utility library for reading user information from an id_token.

This is an experimental library that can temporarily be used to extract
a user from an id_token.  The functionality provided by this library
will be provided elsewhere in the future.
"""


import base64

try:
  import json
except ImportError:
  import simplejson as json
import logging
import os
import re
import time
import urllib

try:

  from google.appengine.api import memcache
  from google.appengine.api import oauth
  from google.appengine.api import urlfetch
  from google.appengine.api import users
except ImportError:

  from google.appengine.api import memcache
  from google.appengine.api import oauth
  from google.appengine.api import urlfetch
  from google.appengine.api import users

try:





  from Crypto.Hash import SHA256
  from Crypto.PublicKey import RSA

  _CRYPTO_LOADED = True
except ImportError:
  _CRYPTO_LOADED = False


__all__ = ['get_current_user',
           'InvalidGetUserCall',
           'SKIP_CLIENT_ID_CHECK']

SKIP_CLIENT_ID_CHECK = ['*']
_CLOCK_SKEW_SECS = 300
_MAX_TOKEN_LIFETIME_SECS = 86400
_DEFAULT_CERT_URI = ('https://www.googleapis.com/service_accounts/v1/metadata/'
                     'raw/federated-signon@system.gserviceaccount.com')
_ENV_USE_OAUTH_SCOPE = 'ENDPOINTS_USE_OAUTH_SCOPE'
_ENV_AUTH_EMAIL = 'ENDPOINTS_AUTH_EMAIL'
_ENV_AUTH_DOMAIN = 'ENDPOINTS_AUTH_DOMAIN'
_EMAIL_SCOPE = 'https://www.googleapis.com/auth/userinfo.email'
_TOKENINFO_URL = 'https://www.googleapis.com/oauth2/v1/tokeninfo'
_MAX_AGE_REGEX = re.compile(r'\s*max-age\s*=\s*(\d+)\s*')
_CERT_NAMESPACE = '__verify_jwt'


class _AppIdentityError(Exception):
  pass


class InvalidGetUserCall(Exception):
  """Called get_current_user when the environment was not set up for it."""



def get_current_user():
  """Get user information from the id_token or oauth token in the request.

  This should only be called from within an Endpoints request handler,
  decorated with an @endpoints.method decorator.  The decorator should include
  the https://www.googleapis.com/auth/userinfo.email scope.

  If the current request uses an id_token, this validates and parses the token
  against the info in the current request handler and returns the user.
  Or, for an Oauth token, this call validates the token against the tokeninfo
  endpoint and oauth.get_current_user with the scopes provided in the method's
  decorator.

  Returns:
    None if there is no token or it's invalid.  If the token was valid, this
      returns a User.  Only the user's email field is guaranteed to be set.
      Other fields may be empty.

  Raises:
    InvalidGetUserCall: if the environment variables necessary to determine the
      endpoints user are not set. These are typically set when processing a
      request using an Endpoints handler. If they are not set, it likely
      indicates that this function was called from outside an Endpoints request
      handler.
  """
  if not _is_auth_info_available():

    raise InvalidGetUserCall('No valid endpoints user in environment.')

  if _ENV_USE_OAUTH_SCOPE in os.environ:




    return oauth.get_current_user(os.environ[_ENV_USE_OAUTH_SCOPE])

  if (_ENV_AUTH_EMAIL in os.environ and
      _ENV_AUTH_DOMAIN in os.environ):
    if not os.environ[_ENV_AUTH_EMAIL]:


      return None


    return users.User(os.environ[_ENV_AUTH_EMAIL],
                      os.environ[_ENV_AUTH_DOMAIN] or None)



  return None



def _is_auth_info_available():
  """Check if user auth info has been set in environment variables."""
  return ((_ENV_AUTH_EMAIL in os.environ and
           _ENV_AUTH_DOMAIN in os.environ) or
          _ENV_USE_OAUTH_SCOPE in os.environ)


def _maybe_set_current_user_vars(method, api_info=None, request=None):
  """Get user information from the id_token or oauth token in the request.

  Used internally by Endpoints to set up environment variables for user
  authentication.

  Args:
    method: The class method that's handling this request.  This method
      should be annotated with @endpoints.method.
    api_info: An api_config._ApiInfo instance. Optional. If None, will attempt
      to parse api_info from the implicit instance of the method.
    request: The current request, or None.
  """
  if _is_auth_info_available():
    return


  os.environ[_ENV_AUTH_EMAIL] = ''
  os.environ[_ENV_AUTH_DOMAIN] = ''




  try:
    api_info = api_info or method.im_self.api_info
  except AttributeError:





    logging.warning('AttributeError when accessing %s.im_self.  An unbound '
                    'method was probably passed as an endpoints handler.',
                    method.__name__)
    scopes = method.method_info.scopes
    audiences = method.method_info.audiences
    allowed_client_ids = method.method_info.allowed_client_ids
  else:
    scopes = (method.method_info.scopes
              if method.method_info.scopes is not None
              else api_info.scopes)
    audiences = (method.method_info.audiences
                 if method.method_info.audiences is not None
                 else api_info.audiences)
    allowed_client_ids = (method.method_info.allowed_client_ids
                          if method.method_info.allowed_client_ids is not None
                          else api_info.allowed_client_ids)

  if not scopes and not audiences and not allowed_client_ids:



    return

  token = _get_token(request)
  if not token:

    return None





  if ((scopes == [_EMAIL_SCOPE] or scopes == (_EMAIL_SCOPE,)) and
      allowed_client_ids):

    logging.debug('Checking for id_token.')
    time_now = long(time.time())
    user = _get_id_token_user(token, audiences, allowed_client_ids, time_now,
                              memcache)

    if user:
      os.environ[_ENV_AUTH_EMAIL] = user.email()
      os.environ[_ENV_AUTH_DOMAIN] = user.auth_domain()

      return


  if scopes:
    logging.debug('Checking for oauth token.')
    if _is_local_dev():
      _set_bearer_user_vars_local(token, allowed_client_ids, scopes)
    else:
      _set_bearer_user_vars(allowed_client_ids, scopes)



def _get_token(request):
  """Get the auth token for this request.

  Auth token may be specified in either the Authorization header or
  as a query param (either access_token or bearer_token).  We'll check in
  this order:
    1. Authorization header.
    2. bearer_token query param.
    3. access_token query param.

  Args:
    request: The current request, or None.

  Returns:
    The token in the request or None.
  """

  auth_header = os.environ.get('HTTP_AUTHORIZATION')

  if auth_header:
    allowed_auth_schemes = ('OAuth', 'Bearer')
    for auth_scheme in allowed_auth_schemes:
      if auth_header.startswith(auth_scheme):

        return auth_header[len(auth_scheme) + 1:]


    return None


  if request:
    for key in ('bearer_token', 'access_token'):
      token, _ = request.get_unrecognized_field_info(key)
      if token:

        return token



def _get_id_token_user(token, audiences, allowed_client_ids, time_now, cache):
  """Get a User for the given id token, if the token is valid.

  Args:
    token: The id_token to check.
    audiences: List of audiences that are acceptable.
    allowed_client_ids: List of client IDs that are acceptable.
    time_now: The current time as a long (eg. long(time.time())).
    cache: Cache to use (eg. the memcache module).

  Returns:
    A User if the token is valid, None otherwise.
  """


  try:
    parsed_token = _verify_signed_jwt_with_certs(token, time_now, cache)
  except _AppIdentityError, e:
    logging.debug('id_token verification failed: %s', e)
    return None
  except:
    logging.debug('id_token verification failed.')
    return None

  if _verify_parsed_token(parsed_token, audiences, allowed_client_ids):
    email = parsed_token['email']






    return users.User(email)



def _set_oauth_user_vars(token_info, audiences, allowed_client_ids, scopes,
                         local_dev):
  logging.warning('_set_oauth_user_vars is deprecated and will be removed '
                  'soon.')
  return _set_bearer_user_vars(allowed_client_ids, scopes)



def _set_bearer_user_vars(allowed_client_ids, scopes):
  """Validate the oauth bearer token and set endpoints auth user variables.

  If the bearer token is valid, this sets ENDPOINTS_USE_OAUTH_SCOPE.  This
  provides enough information that our endpoints.get_current_user() function
  can get the user.

  Args:
    allowed_client_ids: List of client IDs that are acceptable.
    scopes: List of acceptable scopes.
  """
  for scope in scopes:
    try:
      client_id = oauth.get_client_id(scope)
    except oauth.Error:

      continue




    if (list(allowed_client_ids) != SKIP_CLIENT_ID_CHECK and
        client_id not in allowed_client_ids):
      logging.warning('Client ID is not allowed: %s', client_id)
      return

    os.environ[_ENV_USE_OAUTH_SCOPE] = scope
    logging.debug('Returning user from matched oauth_user.')
    return

  logging.debug('Oauth framework user didn\'t match oauth token user.')
  return None


def _set_bearer_user_vars_local(token, allowed_client_ids, scopes):
  """Validate the oauth bearer token on the dev server.

  Since the functions in the oauth module return only example results in local
  development, this hits the tokeninfo endpoint and attempts to validate the
  token.  If it's valid, we'll set _ENV_AUTH_EMAIL and _ENV_AUTH_DOMAIN so we
  can get the user from the token.

  Args:
    token: String with the oauth token to validate.
    allowed_client_ids: List of client IDs that are acceptable.
    scopes: List of acceptable scopes.
  """

  result = urlfetch.fetch(
      '%s?%s' % (_TOKENINFO_URL, urllib.urlencode({'access_token': token})))
  if result.status_code != 200:
    try:
      error_description = json.loads(result.content)['error_description']
    except (ValueError, KeyError):
      error_description = ''
    logging.error('Token info endpoint returned status %s: %s',
                  result.status_code, error_description)
    return
  token_info = json.loads(result.content)


  if 'email' not in token_info:
    logging.warning('Oauth token doesn\'t include an email address.')
    return
  if not token_info.get('verified_email'):
    logging.warning('Oauth token email isn\'t verified.')
    return


  client_id = token_info.get('issued_to')
  if (list(allowed_client_ids) != SKIP_CLIENT_ID_CHECK and
      client_id not in allowed_client_ids):
    logging.warning('Client ID is not allowed: %s', client_id)
    return


  token_scopes = token_info.get('scope', '').split(' ')
  if not any(scope in scopes for scope in token_scopes):
    logging.warning('Oauth token scopes don\'t match any acceptable scopes.')
    return

  os.environ[_ENV_AUTH_EMAIL] = token_info['email']
  os.environ[_ENV_AUTH_DOMAIN] = ''
  logging.debug('Local dev returning user from token.')
  return


def _is_local_dev():
  return os.environ.get('SERVER_SOFTWARE', '').startswith('Development')


def _verify_parsed_token(parsed_token, audiences, allowed_client_ids):

  if parsed_token.get('iss') != 'accounts.google.com':
    logging.warning('Issuer was not valid: %s', parsed_token.get('iss'))
    return False


  aud = parsed_token.get('aud')
  if not aud:
    logging.warning('No aud field in token')
    return False



  cid = parsed_token.get('azp')
  if aud != cid and aud not in audiences:
    logging.warning('Audience not allowed: %s', aud)
    return False


  if list(allowed_client_ids) == SKIP_CLIENT_ID_CHECK:
    logging.warning('Client ID check can\'t be skipped for ID tokens.  '
                    'Id_token cannot be verified.')
    return False
  elif not cid or cid not in allowed_client_ids:
    logging.warning('Client ID is not allowed: %s', cid)
    return False

  if 'email' not in parsed_token:
    return False

  return True


def _urlsafe_b64decode(b64string):

  b64string = b64string.encode('ascii')
  padded = b64string + '=' * ((4 - len(b64string)) % 4)
  return base64.urlsafe_b64decode(padded)


def _get_cert_expiration_time(headers):
  """Get the expiration time for a cert, given the response headers.

  Get expiration time from the headers in the result.  If we can't get
  a time from the headers, this returns 0, indicating that the cert
  shouldn't be cached.

  Args:
    headers: A dict containing the response headers from the request to get
      certs.

  Returns:
    An integer with the number of seconds the cert should be cached.  This
    value is guaranteed to be >= 0.
  """

  cache_control = headers.get('Cache-Control', '')



  for entry in cache_control.split(','):
    match = _MAX_AGE_REGEX.match(entry)
    if match:
      cache_time_seconds = int(match.group(1))
      break
  else:
    return 0


  age = headers.get('Age')
  if age is not None:
    try:
      age = int(age)
    except ValueError:
      age = 0
    cache_time_seconds -= age

  return max(0, cache_time_seconds)


def _get_cached_certs(cert_uri, cache):
  certs = cache.get(cert_uri, namespace=_CERT_NAMESPACE)
  if certs is None:
    logging.debug('Cert cache miss')
    try:
      result = urlfetch.fetch(cert_uri)
    except AssertionError:

      return None

    if result.status_code == 200:
      certs = json.loads(result.content)
      expiration_time_seconds = _get_cert_expiration_time(result.headers)
      if expiration_time_seconds:
        cache.set(cert_uri, certs, time=expiration_time_seconds,
                  namespace=_CERT_NAMESPACE)
    else:
      logging.error(
          'Certs not available, HTTP request returned %d', result.status_code)

  return certs


def _b64_to_long(b):
  b = b.encode('ascii')
  b += '=' * ((4 - len(b)) % 4)
  b = base64.b64decode(b)
  return long(b.encode('hex'), 16)


def _verify_signed_jwt_with_certs(
    jwt, time_now, cache,
    cert_uri=_DEFAULT_CERT_URI):
  """Verify a JWT against public certs.

  See http://self-issued.info/docs/draft-jones-json-web-token.html.

  The PyCrypto library included with Google App Engine is severely limited and
  so you have to use it very carefully to verify JWT signatures. The first
  issue is that the library can't read X.509 files, so we make a call to a
  special URI that has the public cert in modulus/exponent form in JSON.

  The second issue is that the RSA.verify method doesn't work, at least for
  how the JWT tokens are signed, so we have to manually verify the signature
  of the JWT, which means hashing the signed part of the JWT and comparing
  that to the signature that's been encrypted with the public key.

  Args:
    jwt: string, A JWT.
    time_now: The current time, as a long (eg. long(time.time())).
    cache: Cache to use (eg. the memcache module).
    cert_uri: string, URI to get cert modulus and exponent in JSON format.

  Returns:
    dict, The deserialized JSON payload in the JWT.

  Raises:
    _AppIdentityError: if any checks are failed.
  """

  segments = jwt.split('.')

  if len(segments) != 3:
    raise _AppIdentityError('Wrong number of segments in token: %s' % jwt)
  signed = '%s.%s' % (segments[0], segments[1])

  signature = _urlsafe_b64decode(segments[2])



  lsignature = long(signature.encode('hex'), 16)


  header_body = _urlsafe_b64decode(segments[0])
  try:
    header = json.loads(header_body)
  except:
    raise _AppIdentityError('Can\'t parse header: %s' % header_body)
  if header.get('alg') != 'RS256':
    raise _AppIdentityError('Unexpected encryption algorithm: %s' %
                            header.get('alg'))


  json_body = _urlsafe_b64decode(segments[1])
  try:
    parsed = json.loads(json_body)
  except:
    raise _AppIdentityError('Can\'t parse token: %s' % json_body)

  certs = _get_cached_certs(cert_uri, cache)
  if certs is None:
    raise _AppIdentityError(
        'Unable to retrieve certs needed to verify the signed JWT: %s' % jwt)



  if not _CRYPTO_LOADED:
    raise _AppIdentityError('Unable to load pycrypto library.  Can\'t verify '
                            'id_token signature.  See http://www.pycrypto.org '
                            'for more information on pycrypto.')



  local_hash = SHA256.new(signed).hexdigest()


  verified = False
  for keyvalue in certs['keyvalues']:
    modulus = _b64_to_long(keyvalue['modulus'])
    exponent = _b64_to_long(keyvalue['exponent'])
    key = RSA.construct((modulus, exponent))


    hexsig = '%064x' % key.encrypt(lsignature, '')[0]

    hexsig = hexsig[-64:]



    verified = (hexsig == local_hash)
    if verified:
      break
  if not verified:
    raise _AppIdentityError('Invalid token signature: %s' % jwt)


  iat = parsed.get('iat')
  if iat is None:
    raise _AppIdentityError('No iat field in token: %s' % json_body)
  earliest = iat - _CLOCK_SKEW_SECS


  exp = parsed.get('exp')
  if exp is None:
    raise _AppIdentityError('No exp field in token: %s' % json_body)
  if exp >= time_now + _MAX_TOKEN_LIFETIME_SECS:
    raise _AppIdentityError('exp field too far in future: %s' % json_body)
  latest = exp + _CLOCK_SKEW_SECS

  if time_now < earliest:
    raise _AppIdentityError('Token used too early, %d < %d: %s' %
                            (time_now, earliest, json_body))
  if time_now > latest:
    raise _AppIdentityError('Token used too late, %d > %d: %s' %
                            (time_now, latest, json_body))

  return parsed

########NEW FILE########
__FILENAME__ = gcm
import urllib
import urllib2
import json
from collections import defaultdict
import time
import random

GCM_URL = 'https://android.googleapis.com/gcm/send'


class GCMException(Exception): pass
class GCMMalformedJsonException(GCMException): pass
class GCMConnectionException(GCMException): pass
class GCMAuthenticationException(GCMException): pass
class GCMTooManyRegIdsException(GCMException): pass
class GCMNoCollapseKeyException(GCMException): pass
class GCMInvalidTtlException(GCMException): pass

# Exceptions from Google responses
class GCMMissingRegistrationException(GCMException): pass
class GCMMismatchSenderIdException(GCMException): pass
class GCMNotRegisteredException(GCMException): pass
class GCMMessageTooBigException(GCMException): pass
class GCMInvalidRegistrationException(GCMException): pass
class GCMUnavailableException(GCMException): pass


# TODO: Refactor this to be more human-readable
def group_response(response, registration_ids, key):
    # Pair up results and reg_ids
    mapping = zip(registration_ids, response['results'])
    # Filter by key
    filtered = filter(lambda x: key in x[1], mapping)
    # Only consider the value in the dict
    tupled = [(s[0], s[1][key]) for s in filtered]
    # Grouping of errors and mapping of ids
    if key is 'registration_id':
        grouping = {}
        for k, v in tupled:
            grouping[k] = v
    else:
        grouping = defaultdict(list)
        for k, v in tupled:
            grouping[v].append(k)

    if len(grouping) == 0:
        return
    return grouping


class GCM(object):

    # Timeunit is milliseconds.
    BACKOFF_INITIAL_DELAY = 1000;
    MAX_BACKOFF_DELAY = 1024000;

    def __init__(self, api_key, url=GCM_URL, proxy=None):
        """ api_key : google api key
            url: url of gcm service.
            proxy: can be string "http://host:port" or dict {'https':'host:port'}
        """
        self.api_key = api_key
        self.url = url
        if proxy:
            if isinstance(proxy,basestring):
                protocol = url.split(':')[0]
                proxy={protocol:proxy}

            auth = urllib2.HTTPBasicAuthHandler()
            opener = urllib2.build_opener(urllib2.ProxyHandler(proxy), auth, urllib2.HTTPHandler)
            urllib2.install_opener(opener)


    def construct_payload(self, registration_ids, data=None, collapse_key=None,
                            delay_while_idle=False, time_to_live=None, is_json=True):
        """
        Construct the dictionary mapping of parameters.
        Encodes the dictionary into JSON if for json requests.
        Helps appending 'data.' prefix to the plaintext data: 'hello' => 'data.hello'

        :return constructed dict or JSON payload
        :raises GCMInvalidTtlException: if time_to_live is invalid
        :raises GCMNoCollapseKeyException: if collapse_key is missing when time_to_live is used
        """

        if time_to_live:
            if time_to_live > 2419200 or time_to_live < 0:
                raise GCMInvalidTtlException("Invalid time to live value")

        if is_json:
            payload = {'registration_ids': registration_ids}
            if data:
                payload['data'] = data
        else:
            payload = {'registration_id': registration_ids}
            if data:
                plaintext_data = data.copy()
                for k in plaintext_data.keys():
                    plaintext_data['data.%s' % k] = plaintext_data.pop(k)
                payload.update(plaintext_data)

        if delay_while_idle:
            payload['delay_while_idle'] = delay_while_idle

        if time_to_live:
            payload['time_to_live'] = time_to_live
            if collapse_key is None:
                raise GCMNoCollapseKeyException("collapse_key is required when time_to_live is provided")

        if collapse_key:
            payload['collapse_key'] = collapse_key

        if is_json:
            payload = json.dumps(payload)

        return payload

    def make_request(self, data, is_json=True):
        """
        Makes a HTTP request to GCM servers with the constructed payload

        :param data: return value from construct_payload method
        :raises GCMMalformedJsonException: if malformed JSON request found
        :raises GCMAuthenticationException: if there was a problem with authentication, invalid api key
        :raises GCMConnectionException: if GCM is screwed
        """

        headers = {
            'Authorization': 'key=%s' % self.api_key,
        }
        # Default Content-Type is defaulted to application/x-www-form-urlencoded;charset=UTF-8
        if is_json:
            headers['Content-Type'] = 'application/json'

        if not is_json:
            data = urllib.urlencode(data)
        req = urllib2.Request(self.url, data, headers)

        try:
            response = urllib2.urlopen(req).read()
        except urllib2.HTTPError as e:
            if e.code == 400:
                raise GCMMalformedJsonException("The request could not be parsed as JSON")
            elif e.code == 401:
                raise GCMAuthenticationException("There was an error authenticating the sender account")
            elif e.code == 503:
                raise GCMUnavailableException("GCM service is unavailable")
            else:
                error = "GCM service error: %d" % e.code
                raise GCMUnavailableException(error)
        except urllib2.URLError as e:
            raise GCMConnectionException("There was an internal error in the GCM server while trying to process the request")

        if is_json:
            response = json.loads(response)
        return response

    def raise_error(self, error):
        if error == 'InvalidRegistration':
            raise GCMInvalidRegistrationException("Registration ID is invalid")
        elif error == 'Unavailable':
            # Plain-text requests will never return Unavailable as the error code.
            # http://developer.android.com/guide/google/gcm/gcm.html#error_codes
            raise GCMUnavailableException("Server unavailable. Resent the message")
        elif error == 'NotRegistered':
            raise GCMNotRegisteredException("Registration id is not valid anymore")
        elif error == 'MismatchSenderId':
            raise GCMMismatchSenderIdException("A Registration ID is tied to a certain group of senders")
        elif error == 'MessageTooBig':
            raise GCMMessageTooBigException("Message can't exceed 4096 bytes")

    def handle_plaintext_response(self, response):

        # Split response by line
        response_lines = response.strip().split('\n')
        # Split the first line by =
        key, value = response_lines[0].split('=')
        if key == 'Error':
            self.raise_error(value)
        else:
            if len(response_lines) == 2:
                return response_lines[1].split('=')[1]
            return

    def handle_json_response(self, response, registration_ids):
        errors = group_response(response, registration_ids, 'error')
        canonical = group_response(response, registration_ids, 'registration_id')

        info = {}
        if errors:
            info.update({'errors': errors})
        if canonical:
            info.update({'canonical': canonical})

        return info

    def extract_unsent_reg_ids(self, info):
        if 'errors' in info and 'Unavailable' in info['errors']:
            return info['errors']['Unavailable']
        return []

    def plaintext_request(self, registration_id, data=None, collapse_key=None,
                            delay_while_idle=False, time_to_live=None, retries=5):
        """
        Makes a plaintext request to GCM servers

        :param registration_id: string of the registration id
        :param data: dict mapping of key-value pairs of messages
        :return dict of response body from Google including multicast_id, success, failure, canonical_ids, etc
        :raises GCMMissingRegistrationException: if registration_id is not provided
        """

        if not registration_id:
            raise GCMMissingRegistrationException("Missing registration_id")

        payload = self.construct_payload(
            registration_id, data, collapse_key,
            delay_while_idle, time_to_live, False
        )

        attempt = 0
        backoff = self.BACKOFF_INITIAL_DELAY
        for attempt in range(retries):
            try:
                response = self.make_request(payload, is_json=False)
                return self.handle_plaintext_response(response)
            except GCMUnavailableException:
                sleep_time = backoff / 2 + random.randrange(backoff)
                time.sleep(float(sleep_time) / 1000)
                if 2 * backoff < self.MAX_BACKOFF_DELAY:
                    backoff *= 2

        raise IOError("Could not make request after %d attempts" % attempt)

    def json_request(self, registration_ids, data=None, collapse_key=None,
                        delay_while_idle=False, time_to_live=None, retries=5):
        """
        Makes a JSON request to GCM servers

        :param registration_ids: list of the registration ids
        :param data: dict mapping of key-value pairs of messages
        :return dict of response body from Google including multicast_id, success, failure, canonical_ids, etc
        :raises GCMMissingRegistrationException: if the list of registration_ids exceeds 1000 items
        """

        if not registration_ids:
            raise GCMMissingRegistrationException("Missing registration_ids")
        if len(registration_ids) > 1000:
            raise GCMTooManyRegIdsException("Exceded number of registration_ids")

        attempt = 0
        backoff = self.BACKOFF_INITIAL_DELAY
        for attempt in range(retries):
            payload = self.construct_payload(
                registration_ids, data, collapse_key,
                delay_while_idle, time_to_live
            )
            response = self.make_request(payload, is_json=True)
            info = self.handle_json_response(response, registration_ids)

            unsent_reg_ids = self.extract_unsent_reg_ids(info)
            if unsent_reg_ids:
                registration_ids = unsent_reg_ids
                sleep_time = backoff / 2 + random.randrange(backoff)
                time.sleep(float(sleep_time) / 1000)
                if 2 * backoff < self.MAX_BACKOFF_DELAY:
                    backoff *= 2
            else:
                break

        return info

########NEW FILE########
__FILENAME__ = test
import unittest
from gcm import *
import json
from mock import MagicMock
import time


# Helper method to return a different value for each call.
def create_side_effect(returns):
    def side_effect(*args, **kwargs):
        result = returns.pop(0)
        if isinstance(result, Exception):
            raise result
        return result
    return side_effect


class GCMTest(unittest.TestCase):

    def setUp(self):
        self.gcm = GCM('123api')
        self.data = {
            'param1': '1',
            'param2': '2'
        }
        self.response = {
            'results': [
                {'error': 'InvalidRegistration'},
                {'error': 'NotRegistered'},
                {'message_id': '54749687859', 'registration_id': '6969'},
                {'message_id': '5456453453'},
                {'error': 'NotRegistered'},
                {'message_id': '123456778', 'registration_id': '07645'},
            ]
        }
        self.mock_response_1 = {
            'results': [
                {'error': 'Unavailable'},
                {'error': 'Unavailable'},
            ]
        }
        self.mock_response_2 = {
            'results': [
                {'error': 'Unavailable'},
                {'message_id': '1234'}
            ]
        }
        self.mock_response_3 = {
            'results': [
                {'message_id': '5678'},
                {'message_id': '1234'}
            ]
        }
        time.sleep = MagicMock()

    def test_construct_payload(self):
        res = self.gcm.construct_payload(
            registration_ids=['1', '2'], data=self.data, collapse_key='foo',
            delay_while_idle=True, time_to_live=3600, is_json=True
        )
        payload = json.loads(res)
        for arg in ['registration_ids', 'data', 'collapse_key', 'delay_while_idle', 'time_to_live']:
            self.assertIn(arg, payload)

    def test_require_collapse_key(self):
        with self.assertRaises(GCMNoCollapseKeyException):
            self.gcm.construct_payload(registration_ids='1234', data=self.data, time_to_live=3600)

    def test_json_payload(self):
        reg_ids = ['12', '145', '56']
        json_payload = self.gcm.construct_payload(registration_ids=reg_ids, data=self.data)
        payload = json.loads(json_payload)

        self.assertIn('registration_ids', payload)
        self.assertEqual(payload['data'], self.data)
        self.assertEqual(payload['registration_ids'], reg_ids)

    def test_plaintext_payload(self):
        result = self.gcm.construct_payload(registration_ids='1234', data=self.data, is_json=False)

        self.assertIn('registration_id', result)
        self.assertIn('data.param1', result)
        self.assertIn('data.param2', result)

    def test_limit_reg_ids(self):
        reg_ids = range(1003)
        self.assertTrue(len(reg_ids) > 1000)
        with self.assertRaises(GCMTooManyRegIdsException):
            self.gcm.json_request(registration_ids=reg_ids, data=self.data)

    def test_missing_reg_id(self):
        with self.assertRaises(GCMMissingRegistrationException):
            self.gcm.json_request(registration_ids=[], data=self.data)

        with self.assertRaises(GCMMissingRegistrationException):
            self.gcm.plaintext_request(registration_id=None, data=self.data)

    def test_invalid_ttl(self):
        with self.assertRaises(GCMInvalidTtlException):
            self.gcm.construct_payload(
                registration_ids='1234', data=self.data, is_json=False, time_to_live=5000000
            )

        with self.assertRaises(GCMInvalidTtlException):
            self.gcm.construct_payload(
                registration_ids='1234', data=self.data, is_json=False, time_to_live=-10
            )

    def test_group_response(self):
        ids = ['123', '345', '678', '999', '1919', '5443']
        error_group = group_response(self.response, ids, 'error')
        self.assertEqual(error_group['NotRegistered'], ['345', '1919'])
        self.assertEqual(error_group['InvalidRegistration'], ['123'])

        canonical_group = group_response(self.response, ids, 'registration_id')
        self.assertEqual(canonical_group['678'], '6969')
        self.assertEqual(canonical_group['5443'], '07645')

    def test_group_response_no_error(self):
        ids = ['123', '345', '678']
        response = {
            'results': [
                {'message_id': '346547676'},
                {'message_id': '54749687859'},
                {'message_id': '5456453453'},
            ]
        }
        error_group = group_response(response, ids, 'error')
        canonical_group = group_response(response, ids, 'registration_id')
        self.assertEqual(error_group, None)
        self.assertEqual(canonical_group, None)

    def test_handle_json_response(self):
        ids = ['123', '345', '678', '999', '1919', '5443']
        res = self.gcm.handle_json_response(self.response, ids)

        self.assertIn('errors', res)
        self.assertIn('NotRegistered', res['errors'])
        self.assertIn('canonical', res)
        self.assertIn('678', res['canonical'])

    def test_handle_json_response_no_error(self):
        ids = ['123', '345', '678']
        response = {
            'results': [
                {'message_id': '346547676'},
                {'message_id': '54749687859'},
                {'message_id': '5456453453'},
            ]
        }
        res = self.gcm.handle_json_response(response, ids)

        self.assertNotIn('errors', res)
        self.assertNotIn('canonical', res)

    def test_handle_plaintext_response(self):
        response = 'Error=NotRegistered'
        with self.assertRaises(GCMNotRegisteredException):
            self.gcm.handle_plaintext_response(response)

        response = 'id=23436576'
        res = self.gcm.handle_plaintext_response(response)
        self.assertIsNone(res)

        response = 'id=23436576\nregistration_id=3456'
        res = self.gcm.handle_plaintext_response(response)
        self.assertEqual(res, '3456')

    def test_retry_plaintext_request_ok(self):
        returns = [GCMUnavailableException(), GCMUnavailableException(), 'id=123456789']

        self.gcm.make_request = MagicMock(side_effect=create_side_effect(returns))
        res = self.gcm.plaintext_request(registration_id='1234', data=self.data)

        self.assertIsNone(res)
        self.assertEqual(self.gcm.make_request.call_count, 3)

    def test_retry_plaintext_request_fail(self):
        returns = [GCMUnavailableException(), GCMUnavailableException(), GCMUnavailableException()]

        self.gcm.make_request = MagicMock(side_effect=create_side_effect(returns))
        with self.assertRaises(IOError):
            self.gcm.plaintext_request(registration_id='1234', data=self.data, retries=2)

        self.assertEqual(self.gcm.make_request.call_count, 2)

    def test_retry_json_request_ok(self):
        returns = [self.mock_response_1, self.mock_response_2, self.mock_response_3]

        self.gcm.make_request = MagicMock(side_effect=create_side_effect(returns))
        res = self.gcm.json_request(registration_ids=['1', '2'], data=self.data)

        self.assertEqual(self.gcm.make_request.call_count, 3)
        self.assertNotIn('errors', res)

    def test_retry_json_request_fail(self):
        returns = [self.mock_response_1, self.mock_response_2, self.mock_response_3]

        self.gcm.make_request = MagicMock(side_effect=create_side_effect(returns))
        res = self.gcm.json_request(registration_ids=['1', '2'], data=self.data, retries=2)

        self.assertEqual(self.gcm.make_request.call_count, 2)
        self.assertIn('Unavailable', res['errors'])
        self.assertEqual(res['errors']['Unavailable'][0], '1')

    def test_retry_exponential_backoff(self):
        returns = [GCMUnavailableException(), GCMUnavailableException(), 'id=123456789']

        self.gcm.make_request = MagicMock(side_effect=create_side_effect(returns))
        self.gcm.plaintext_request(registration_id='1234', data=self.data)

        # time.sleep is actually mock object.
        self.assertEqual(time.sleep.call_count, 2)
        backoff = self.gcm.BACKOFF_INITIAL_DELAY
        for arg in time.sleep.call_args_list:
            sleep_time = int(arg[0][0] * 1000)
            self.assertTrue(backoff / 2 <= sleep_time <= backoff * 3 / 2)
            if 2 * backoff < self.gcm.MAX_BACKOFF_DELAY:
                backoff *= 2

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = linksdb
"""Generate a sample project"""

from AndroidCodeGenerator.generator import Generator
from AndroidCodeGenerator.db_table import (Table, Column, ForeignKey,
                                           Unique, Trigger)
from AndroidCodeGenerator.sql_validator import SQLTester

links = Table('Link').add_cols(Column('sha').text.not_null,
                               Column('url').text.not_null,
                               Column('timestamp').timestamp.not_null\
                               .default_current_timestamp,
                               Column('deleted').integer.not_null\
                               .default(0),
                               Column('synced').integer.not_null\
                               .default(0))

links.add_constraints(Unique('url').on_conflict_ignore,
                      Unique('sha').on_conflict_ignore)

'''
deltrigger = Trigger("tr_del_link").temp.if_not_exists
deltrigger.after.delete_on(links.name)
deltrigger.do_sql("INSERT INTO {table} (sha, url, timestamp, deleted) VALUES\
 (old.sha, old.url, old.timestamp, 1)".format(table=synclinks.name))


intrigger = Trigger("tr_ins_link").temp.if_not_exists
intrigger.after.insert_on(links.name)
intrigger.do_sql("INSERT INTO {table} (sha, url, timestamp) \
VALUES (new.sha, new.url, new.timestamp)"\
                 .format(table=synclinks.name))

#uptrigger = Trigger("tr_upd_link").temp.if_not_exists
#uptrigger.after.update_on(links.name)
#uptrigger.do_sql("INSERT INTO {table} (sha, url, timestamp) \
#VALUES (new.sha, new.url, new.timestamp)"\
#                 .format(table=synclinks.name))
'''

s = SQLTester()
s.add_tables(links)
#s.add_triggers(deltrigger, intrigger)
s.test_create()

g = Generator(path='android-client/src/com/nononsenseapps/linksgcm/database',
              pkg='com.nononsenseapps.linksgcm.database')

g.add_tables(links)
#g.add_triggers(deltrigger, intrigger)

g.write()

########NEW FILE########
__FILENAME__ = app
import os, binascii
from dateutil import parser as dateparser
from bottle import run, get, post, delete, install, HTTPError, request
from bottle_sqlite import SQLitePlugin
from dbsetup import init_db
from google_auth import gauth
from app_conf import DBNAME
from app_gcm import send_link

init_db(DBNAME)
install(SQLitePlugin(dbfile=DBNAME))

install(gauth)

def to_dict(row):
    return dict(sha=row['sha'],
                url=row['url'],
                timestamp=row['timestamp'],
                # Convert integer to boolean
                deleted=(1 == row['deleted']))


@get('/')
@get('/links')
def list_links(db, userid):
    '''Return a complete list of all links'''
    args = [userid]

    deleted_part = ' AND deleted IS 0'
    if ('showDeleted' in request.query and
        'true' == request.query['showDeleted']):
        deleted_part = ''

    timestamp_part = ''
    if 'timestampMin' in request.query:
        timestamp_part = ' AND timestamp > ?'
        args.append(request.query['timestampMin'])

    latest_time = None
    links = []
    stmt = 'SELECT * from links WHERE userid IS ?'
    stmt += deleted_part + timestamp_part
    for row in db.execute(stmt,
                          args):
        links.append(to_dict(row))
        # Keep track of the latest timestamp here
        if latest_time is None:
            latest_time = row['timestamp']
        else:
            delta = dateparser.parse(row['timestamp']) - dateparser.parse(latest_time)
            if delta.total_seconds() > 0:
                latest_time = row['timestamp']

    return dict(latestTimestamp=latest_time,
                links=links)

@get('/links/<sha>')
def get_link(db, sha, userid):
    '''Returns a specific link'''
    row = db.execute('SELECT * from links WHERE sha IS ? AND userid IS ?',
                     [sha, userid]).fetchone()
    if row:
        return to_dict(row)

    return HTTPError(404, "No such item")



@delete('/links/<sha>')
def delete_link(db, sha, userid):
    '''Deletes a specific link from the list.
    On success, returns an empty response'''
    db.execute('UPDATE links SET deleted = 1, timestamp = CURRENT_TIMESTAMP \
    WHERE sha IS ? AND userid is ?', [sha, userid])

    if db.total_changes > 0:
        # Regid is optional to provide from the client
        # If present, it will not receive a GCM msg
        regid = None
        if 'regid' in request.query:
            regid = request.query['regid']
        send_link(userid, sha, regid)

    return {}

@post('/links')
def add_link(db, userid):
    '''Adds a link to the list.
    On success, returns the entry created.'''
    if 'application/json' not in request.content_type:
        return HTTPError(415, "Only json is accepted")
    # Check required fields
    if ('url' not in request.json or request.json['url'] is None
        or len(request.json['url']) < 1):
        return HTTPError(400, "Must specify a url")

    # Sha is optional, generate if not present
    if 'sha' not in request.json:
        request.json['sha'] = binascii.b2a_hex(os.urandom(15))

    args = [userid,
            request.json['url'],
            request.json['sha']]
    stmt = 'INSERT INTO links (userid, url, sha) VALUES(?, ?, ?)'

    db.execute(stmt, args)

    if db.total_changes > 0:
        # Regid is optional to provide from the client
        # If present, it will not receive a GCM msg
        regid = None
        if 'regid' in request.query:
            regid = request.query['regid']
        send_link(userid, request.json['sha'], regid)

    return get_link(db, request.json['sha'], userid)


@post('/registergcm')
def register_gcm(db, userid):
    '''Adds a registration id for a user to the database.
    Returns nothing.'''
    if 'application/json' not in request.content_type:
        return HTTPError(415, "Only json is accepted")
    # Check required fields
    if ('regid' not in request.json or request.json['regid'] is None
        or len(request.json['regid']) < 1):
        return HTTPError(400, "Must specify a registration id")

    db.execute('INSERT INTO gcm (userid, regid) VALUES(?, ?)',
               [userid, request.json['regid']])

    if db.total_changes > 0:
        return {}
    else:
        return HTTPError(500, "Adding regid to DB failed")

if __name__ == '__main__':
    # Restart server automatically when this file changes
    run(host='0.0.0.0', port=5500, reloader=True, debug=True)

########NEW FILE########
__FILENAME__ = app_conf
'''Call from a file which requires the stuff as
from app_conf import GCM_API_KEY
from app_conf import DBNAME'''

DBNAME = 'test.db'
GCM_API_KEY = 'Your key here'

########NEW FILE########
__FILENAME__ = app_gcm
from __future__ import print_function, division
from threading import Thread
from functools import wraps
import sqlite3 as sql
from gcm import GCM
from app_conf import GCM_API_KEY, DBNAME
from dbsetup import init_db

init_db(DBNAME)

gcm = GCM(GCM_API_KEY)

def to_dict(row):
    return dict(sha=row['sha'],
                url=row['url'],
                timestamp=row['timestamp'],
                # Convert integer to boolean
                deleted=(1 == row['deleted']))


def async(func):
    """
    Runs the decorated function in a separate thread.
    Returns the thread.

    Example:
    @async
    def dowork():
        print('Hello from another thread')

    t = dowork()
    t.join()
    """
    @wraps(func)
    def async_func(*args, **kwargs):
        t = Thread(target = func, args = args, kwargs = kwargs)
        t.start()
        return t

    return async_func

@async
def send_link(userid, sha, excludeid=None):
    '''This method runs in a separate thread as to not block
    the main app with this networking IO.

    Transmits the link specified by the sha to the users devices.
    '''
    db = _get_db()
    with db:
        c = db.cursor()
        # Get link
        link = db.execute('SELECT * FROM links WHERE\
        userid IS ? AND sha IS ?', [userid, sha]).fetchone()

        if link is None:
            return

        data = to_dict(link)
        print("Sending data:", data)

        # Get devices
        regrows = db.execute('SELECT * FROM gcm WHERE userid IS ?', [userid])\
                 .fetchall()

        if len(regrows) < 1:
            return

        reg_ids = []
        for row in regrows:
            reg_ids.append(row['regid'])

        # Dont send to origin device, if specified
        try:
            reg_ids.remove(excludeid)
        except ValueError:
            pass # not in list, or None

    if len(reg_ids) < 1:
        return

    print("Sending to:", len(reg_ids))
    _send(userid, reg_ids, data)


def _get_db():
    db = sql.connect(DBNAME)
    db.row_factory = sql.Row
    return db


def _remove_regid(userid, regid):
    db = _get_db()
    with db:
        c = db.cursor()
        c.execute('DELETE FROM gcm WHERE userid IS ? AND regid IS ?',
                  [userid, regid])


def _replace_regid(userid, oldid, newid):
    db = _get_db()
    with db:
        c = db.cursor()
        c.execute('UPDATE gcm SET regid=? WHERE userid IS ? AND regid IS ?',
                  [newid, userid, oldid])


def _send(userid, rids, data):
    '''Send the data using GCM'''
    response = gcm.json_request(registration_ids=rids,
                                data=data,
                                delay_while_idle=True)
    # A device has switched registration id
    if 'canonical' in response:
        for reg_id, canonical_id in response['canonical'].items():
            # Repace reg_id with canonical_id in your database
            _replace_regid(userid, reg_id, canonical_id)

    # Handling errors
    if 'errors' in response:
        for error, reg_ids in response['errors'].items():
            # Check for errors and act accordingly
            if error is 'NotRegistered':
                # Remove reg_ids from database
                for regid in reg_ids:
                    _remove_regid(userid, regid)

########NEW FILE########
__FILENAME__ = bottle
#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Bottle is a fast and simple micro-framework for small web applications. It
offers request dispatching (Routes) with url parameter support, templates,
a built-in HTTP Server and adapters for many third party WSGI/HTTP-server and
template engines - all in a single file and with no dependencies other than the
Python Standard Library.

Homepage and documentation: http://bottlepy.org/

Copyright (c) 2012, Marcel Hellkamp.
License: MIT (see LICENSE for details)
"""

from __future__ import with_statement

__author__ = 'Marcel Hellkamp'
__version__ = '0.11.6'
__license__ = 'MIT'

# The gevent server adapter needs to patch some modules before they are imported
# This is why we parse the commandline parameters here but handle them later
if __name__ == '__main__':
    from optparse import OptionParser
    _cmd_parser = OptionParser(usage="usage: %prog [options] package.module:app")
    _opt = _cmd_parser.add_option
    _opt("--version", action="store_true", help="show version number.")
    _opt("-b", "--bind", metavar="ADDRESS", help="bind socket to ADDRESS.")
    _opt("-s", "--server", default='wsgiref', help="use SERVER as backend.")
    _opt("-p", "--plugin", action="append", help="install additional plugin/s.")
    _opt("--debug", action="store_true", help="start server in debug mode.")
    _opt("--reload", action="store_true", help="auto-reload on file changes.")
    _cmd_options, _cmd_args = _cmd_parser.parse_args()
    if _cmd_options.server and _cmd_options.server.startswith('gevent'):
        import gevent.monkey; gevent.monkey.patch_all()

import base64, cgi, email.utils, functools, hmac, imp, itertools, mimetypes,\
        os, re, subprocess, sys, tempfile, threading, time, urllib, warnings

from datetime import date as datedate, datetime, timedelta
from tempfile import TemporaryFile
from traceback import format_exc, print_exc

try: from json import dumps as json_dumps, loads as json_lds
except ImportError: # pragma: no cover
    try: from simplejson import dumps as json_dumps, loads as json_lds
    except ImportError:
        try: from django.utils.simplejson import dumps as json_dumps, loads as json_lds
        except ImportError:
            def json_dumps(data):
                raise ImportError("JSON support requires Python 2.6 or simplejson.")
            json_lds = json_dumps



# We now try to fix 2.5/2.6/3.1/3.2 incompatibilities.
# It ain't pretty but it works... Sorry for the mess.

py   = sys.version_info
py3k = py >= (3,0,0)
py25 = py <  (2,6,0)
py31 = (3,1,0) <= py < (3,2,0)

# Workaround for the missing "as" keyword in py3k.
def _e(): return sys.exc_info()[1]

# Workaround for the "print is a keyword/function" Python 2/3 dilemma
# and a fallback for mod_wsgi (resticts stdout/err attribute access)
try:
    _stdout, _stderr = sys.stdout.write, sys.stderr.write
except IOError:
    _stdout = lambda x: sys.stdout.write(x)
    _stderr = lambda x: sys.stderr.write(x)

# Lots of stdlib and builtin differences.
if py3k:
    import http.client as httplib
    import _thread as thread
    from urllib.parse import urljoin, SplitResult as UrlSplitResult
    from urllib.parse import urlencode, quote as urlquote, unquote as urlunquote
    urlunquote = functools.partial(urlunquote, encoding='latin1')
    from http.cookies import SimpleCookie
    from collections import MutableMapping as DictMixin
    import pickle
    from io import BytesIO
    basestring = str
    unicode = str
    json_loads = lambda s: json_lds(touni(s))
    callable = lambda x: hasattr(x, '__call__')
    imap = map
else: # 2.x
    import httplib
    import thread
    from urlparse import urljoin, SplitResult as UrlSplitResult
    from urllib import urlencode, quote as urlquote, unquote as urlunquote
    from Cookie import SimpleCookie
    from itertools import imap
    import cPickle as pickle
    from StringIO import StringIO as BytesIO
    if py25:
        msg = "Python 2.5 support may be dropped in future versions of Bottle."
        warnings.warn(msg, DeprecationWarning)
        from UserDict import DictMixin
        def next(it): return it.next()
        bytes = str
    else: # 2.6, 2.7
        from collections import MutableMapping as DictMixin
    json_loads = json_lds

# Some helpers for string/byte handling
def tob(s, enc='utf8'):
    return s.encode(enc) if isinstance(s, unicode) else bytes(s)
def touni(s, enc='utf8', err='strict'):
    return s.decode(enc, err) if isinstance(s, bytes) else unicode(s)
tonat = touni if py3k else tob

# 3.2 fixes cgi.FieldStorage to accept bytes (which makes a lot of sense).
# 3.1 needs a workaround.
if py31:
    from io import TextIOWrapper
    class NCTextIOWrapper(TextIOWrapper):
        def close(self): pass # Keep wrapped buffer open.

# File uploads (which are implemented as empty FiledStorage instances...)
# have a negative truth value. That makes no sense, here is a fix.
class FieldStorage(cgi.FieldStorage):
    def __nonzero__(self): return bool(self.list or self.file)
    if py3k: __bool__ = __nonzero__

# A bug in functools causes it to break if the wrapper is an instance method
def update_wrapper(wrapper, wrapped, *a, **ka):
    try: functools.update_wrapper(wrapper, wrapped, *a, **ka)
    except AttributeError: pass



# These helpers are used at module level and need to be defined first.
# And yes, I know PEP-8, but sometimes a lower-case classname makes more sense.

def depr(message):
    warnings.warn(message, DeprecationWarning, stacklevel=3)

def makelist(data): # This is just to handy
    if isinstance(data, (tuple, list, set, dict)): return list(data)
    elif data: return [data]
    else: return []


class DictProperty(object):
    ''' Property that maps to a key in a local dict-like attribute. '''
    def __init__(self, attr, key=None, read_only=False):
        self.attr, self.key, self.read_only = attr, key, read_only

    def __call__(self, func):
        functools.update_wrapper(self, func, updated=[])
        self.getter, self.key = func, self.key or func.__name__
        return self

    def __get__(self, obj, cls):
        if obj is None: return self
        key, storage = self.key, getattr(obj, self.attr)
        if key not in storage: storage[key] = self.getter(obj)
        return storage[key]

    def __set__(self, obj, value):
        if self.read_only: raise AttributeError("Read-Only property.")
        getattr(obj, self.attr)[self.key] = value

    def __delete__(self, obj):
        if self.read_only: raise AttributeError("Read-Only property.")
        del getattr(obj, self.attr)[self.key]


class cached_property(object):
    ''' A property that is only computed once per instance and then replaces
        itself with an ordinary attribute. Deleting the attribute resets the
        property. '''

    def __init__(self, func):
        self.func = func

    def __get__(self, obj, cls):
        if obj is None: return self
        value = obj.__dict__[self.func.__name__] = self.func(obj)
        return value


class lazy_attribute(object):
    ''' A property that caches itself to the class object. '''
    def __init__(self, func):
        functools.update_wrapper(self, func, updated=[])
        self.getter = func

    def __get__(self, obj, cls):
        value = self.getter(cls)
        setattr(cls, self.__name__, value)
        return value






###############################################################################
# Exceptions and Events ########################################################
###############################################################################


class BottleException(Exception):
    """ A base class for exceptions used by bottle. """
    pass






###############################################################################
# Routing ######################################################################
###############################################################################


class RouteError(BottleException):
    """ This is a base class for all routing related exceptions """


class RouteReset(BottleException):
    """ If raised by a plugin or request handler, the route is reset and all
        plugins are re-applied. """

class RouterUnknownModeError(RouteError): pass


class RouteSyntaxError(RouteError):
    """ The route parser found something not supported by this router """


class RouteBuildError(RouteError):
    """ The route could not been built """


class Router(object):
    ''' A Router is an ordered collection of route->target pairs. It is used to
        efficiently match WSGI requests against a number of routes and return
        the first target that satisfies the request. The target may be anything,
        usually a string, ID or callable object. A route consists of a path-rule
        and a HTTP method.

        The path-rule is either a static path (e.g. `/contact`) or a dynamic
        path that contains wildcards (e.g. `/wiki/<page>`). The wildcard syntax
        and details on the matching order are described in docs:`routing`.
    '''

    default_pattern = '[^/]+'
    default_filter   = 're'
    #: Sorry for the mess. It works. Trust me.
    rule_syntax = re.compile('(\\\\*)'\
        '(?:(?::([a-zA-Z_][a-zA-Z_0-9]*)?()(?:#(.*?)#)?)'\
          '|(?:<([a-zA-Z_][a-zA-Z_0-9]*)?(?::([a-zA-Z_]*)'\
            '(?::((?:\\\\.|[^\\\\>]+)+)?)?)?>))')

    def __init__(self, strict=False):
        self.rules    = {} # A {rule: Rule} mapping
        self.builder  = {} # A rule/name->build_info mapping
        self.static   = {} # Cache for static routes: {path: {method: target}}
        self.dynamic  = [] # Cache for dynamic routes. See _compile()
        #: If true, static routes are no longer checked first.
        self.strict_order = strict
        self.filters = {'re': self.re_filter, 'int': self.int_filter,
                        'float': self.float_filter, 'path': self.path_filter}

    def re_filter(self, conf):
        return conf or self.default_pattern, None, None

    def int_filter(self, conf):
        return r'-?\d+', int, lambda x: str(int(x))

    def float_filter(self, conf):
        return r'-?[\d.]+', float, lambda x: str(float(x))

    def path_filter(self, conf):
        return r'.+?', None, None

    def add_filter(self, name, func):
        ''' Add a filter. The provided function is called with the configuration
        string as parameter and must return a (regexp, to_python, to_url) tuple.
        The first element is a string, the last two are callables or None. '''
        self.filters[name] = func

    def parse_rule(self, rule):
        ''' Parses a rule into a (name, filter, conf) token stream. If mode is
            None, name contains a static rule part. '''
        offset, prefix = 0, ''
        for match in self.rule_syntax.finditer(rule):
            prefix += rule[offset:match.start()]
            g = match.groups()
            if len(g[0])%2: # Escaped wildcard
                prefix += match.group(0)[len(g[0]):]
                offset = match.end()
                continue
            if prefix: yield prefix, None, None
            name, filtr, conf = g[1:4] if not g[2] is None else g[4:7]
            if not filtr: filtr = self.default_filter
            yield name, filtr, conf or None
            offset, prefix = match.end(), ''
        if offset <= len(rule) or prefix:
            yield prefix+rule[offset:], None, None

    def add(self, rule, method, target, name=None):
        ''' Add a new route or replace the target for an existing route. '''
        if rule in self.rules:
            self.rules[rule][method] = target
            if name: self.builder[name] = self.builder[rule]
            return

        target = self.rules[rule] = {method: target}

        # Build pattern and other structures for dynamic routes
        anons = 0      # Number of anonymous wildcards
        pattern = ''   # Regular expression  pattern
        filters = []   # Lists of wildcard input filters
        builder = []   # Data structure for the URL builder
        is_static = True
        for key, mode, conf in self.parse_rule(rule):
            if mode:
                is_static = False
                mask, in_filter, out_filter = self.filters[mode](conf)
                if key:
                    pattern += '(?P<%s>%s)' % (key, mask)
                else:
                    pattern += '(?:%s)' % mask
                    key = 'anon%d' % anons; anons += 1
                if in_filter: filters.append((key, in_filter))
                builder.append((key, out_filter or str))
            elif key:
                pattern += re.escape(key)
                builder.append((None, key))
        self.builder[rule] = builder
        if name: self.builder[name] = builder

        if is_static and not self.strict_order:
            self.static[self.build(rule)] = target
            return

        def fpat_sub(m):
            return m.group(0) if len(m.group(1)) % 2 else m.group(1) + '(?:'
        flat_pattern = re.sub(r'(\\*)(\(\?P<[^>]*>|\((?!\?))', fpat_sub, pattern)

        try:
            re_match = re.compile('^(%s)$' % pattern).match
        except re.error:
            raise RouteSyntaxError("Could not add Route: %s (%s)" % (rule, _e()))

        def match(path):
            """ Return an url-argument dictionary. """
            url_args = re_match(path).groupdict()
            for name, wildcard_filter in filters:
                try:
                    url_args[name] = wildcard_filter(url_args[name])
                except ValueError:
                    raise HTTPError(400, 'Path has wrong format.')
            return url_args

        try:
            combined = '%s|(^%s$)' % (self.dynamic[-1][0].pattern, flat_pattern)
            self.dynamic[-1] = (re.compile(combined), self.dynamic[-1][1])
            self.dynamic[-1][1].append((match, target))
        except (AssertionError, IndexError): # AssertionError: Too many groups
            self.dynamic.append((re.compile('(^%s$)' % flat_pattern),
                                [(match, target)]))
        return match

    def build(self, _name, *anons, **query):
        ''' Build an URL by filling the wildcards in a rule. '''
        builder = self.builder.get(_name)
        if not builder: raise RouteBuildError("No route with that name.", _name)
        try:
            for i, value in enumerate(anons): query['anon%d'%i] = value
            url = ''.join([f(query.pop(n)) if n else f for (n,f) in builder])
            return url if not query else url+'?'+urlencode(query)
        except KeyError:
            raise RouteBuildError('Missing URL argument: %r' % _e().args[0])

    def match(self, environ):
        ''' Return a (target, url_agrs) tuple or raise HTTPError(400/404/405). '''
        path, targets, urlargs = environ['PATH_INFO'] or '/', None, {}
        if path in self.static:
            targets = self.static[path]
        else:
            for combined, rules in self.dynamic:
                match = combined.match(path)
                if not match: continue
                getargs, targets = rules[match.lastindex - 1]
                urlargs = getargs(path) if getargs else {}
                break

        if not targets:
            raise HTTPError(404, "Not found: " + repr(environ['PATH_INFO']))
        method = environ['REQUEST_METHOD'].upper()
        if method in targets:
            return targets[method], urlargs
        if method == 'HEAD' and 'GET' in targets:
            return targets['GET'], urlargs
        if 'ANY' in targets:
            return targets['ANY'], urlargs
        allowed = [verb for verb in targets if verb != 'ANY']
        if 'GET' in allowed and 'HEAD' not in allowed:
            allowed.append('HEAD')
        raise HTTPError(405, "Method not allowed.", Allow=",".join(allowed))


class Route(object):
    ''' This class wraps a route callback along with route specific metadata and
        configuration and applies Plugins on demand. It is also responsible for
        turing an URL path rule into a regular expression usable by the Router.
    '''

    def __init__(self, app, rule, method, callback, name=None,
                 plugins=None, skiplist=None, **config):
        #: The application this route is installed to.
        self.app = app
        #: The path-rule string (e.g. ``/wiki/:page``).
        self.rule = rule
        #: The HTTP method as a string (e.g. ``GET``).
        self.method = method
        #: The original callback with no plugins applied. Useful for introspection.
        self.callback = callback
        #: The name of the route (if specified) or ``None``.
        self.name = name or None
        #: A list of route-specific plugins (see :meth:`Bottle.route`).
        self.plugins = plugins or []
        #: A list of plugins to not apply to this route (see :meth:`Bottle.route`).
        self.skiplist = skiplist or []
        #: Additional keyword arguments passed to the :meth:`Bottle.route`
        #: decorator are stored in this dictionary. Used for route-specific
        #: plugin configuration and meta-data.
        self.config = ConfigDict(config)

    def __call__(self, *a, **ka):
        depr("Some APIs changed to return Route() instances instead of"\
             " callables. Make sure to use the Route.call method and not to"\
             " call Route instances directly.")
        return self.call(*a, **ka)

    @cached_property
    def call(self):
        ''' The route callback with all plugins applied. This property is
            created on demand and then cached to speed up subsequent requests.'''
        return self._make_callback()

    def reset(self):
        ''' Forget any cached values. The next time :attr:`call` is accessed,
            all plugins are re-applied. '''
        self.__dict__.pop('call', None)

    def prepare(self):
        ''' Do all on-demand work immediately (useful for debugging).'''
        self.call

    @property
    def _context(self):
        depr('Switch to Plugin API v2 and access the Route object directly.')
        return dict(rule=self.rule, method=self.method, callback=self.callback,
                    name=self.name, app=self.app, config=self.config,
                    apply=self.plugins, skip=self.skiplist)

    def all_plugins(self):
        ''' Yield all Plugins affecting this route. '''
        unique = set()
        for p in reversed(self.app.plugins + self.plugins):
            if True in self.skiplist: break
            name = getattr(p, 'name', False)
            if name and (name in self.skiplist or name in unique): continue
            if p in self.skiplist or type(p) in self.skiplist: continue
            if name: unique.add(name)
            yield p

    def _make_callback(self):
        callback = self.callback
        for plugin in self.all_plugins():
            try:
                if hasattr(plugin, 'apply'):
                    api = getattr(plugin, 'api', 1)
                    context = self if api > 1 else self._context
                    callback = plugin.apply(callback, context)
                else:
                    callback = plugin(callback)
            except RouteReset: # Try again with changed configuration.
                return self._make_callback()
            if not callback is self.callback:
                update_wrapper(callback, self.callback)
        return callback

    def __repr__(self):
        return '<%s %r %r>' % (self.method, self.rule, self.callback)






###############################################################################
# Application Object ###########################################################
###############################################################################


class Bottle(object):
    """ Each Bottle object represents a single, distinct web application and
        consists of routes, callbacks, plugins, resources and configuration.
        Instances are callable WSGI applications.

        :param catchall: If true (default), handle all exceptions. Turn off to
                         let debugging middleware handle exceptions.
    """

    def __init__(self, catchall=True, autojson=True):
        #: If true, most exceptions are caught and returned as :exc:`HTTPError`
        self.catchall = catchall

        #: A :class:`ResourceManager` for application files
        self.resources = ResourceManager()

        #: A :class:`ConfigDict` for app specific configuration.
        self.config = ConfigDict()
        self.config.autojson = autojson

        self.routes = [] # List of installed :class:`Route` instances.
        self.router = Router() # Maps requests to :class:`Route` instances.
        self.error_handler = {}

        # Core plugins
        self.plugins = [] # List of installed plugins.
        self.hooks = HooksPlugin()
        self.install(self.hooks)
        if self.config.autojson:
            self.install(JSONPlugin())
        self.install(TemplatePlugin())


    def mount(self, prefix, app, **options):
        ''' Mount an application (:class:`Bottle` or plain WSGI) to a specific
            URL prefix. Example::

                root_app.mount('/admin/', admin_app)

            :param prefix: path prefix or `mount-point`. If it ends in a slash,
                that slash is mandatory.
            :param app: an instance of :class:`Bottle` or a WSGI application.

            All other parameters are passed to the underlying :meth:`route` call.
        '''
        if isinstance(app, basestring):
            prefix, app = app, prefix
            depr('Parameter order of Bottle.mount() changed.') # 0.10

        segments = [p for p in prefix.split('/') if p]
        if not segments: raise ValueError('Empty path prefix.')
        path_depth = len(segments)

        def mountpoint_wrapper():
            try:
                request.path_shift(path_depth)
                rs = HTTPResponse([])
                def start_response(status, headerlist):
                    rs.status = status
                    for name, value in headerlist: rs.add_header(name, value)
                    return rs.body.append
                body = app(request.environ, start_response)
                if body and rs.body: body = itertools.chain(rs.body, body)
                rs.body = body or rs.body
                return rs
            finally:
                request.path_shift(-path_depth)

        options.setdefault('skip', True)
        options.setdefault('method', 'ANY')
        options.setdefault('mountpoint', {'prefix': prefix, 'target': app})
        options['callback'] = mountpoint_wrapper

        self.route('/%s/<:re:.*>' % '/'.join(segments), **options)
        if not prefix.endswith('/'):
            self.route('/' + '/'.join(segments), **options)

    def merge(self, routes):
        ''' Merge the routes of another :class:`Bottle` application or a list of
            :class:`Route` objects into this application. The routes keep their
            'owner', meaning that the :data:`Route.app` attribute is not
            changed. '''
        if isinstance(routes, Bottle):
            routes = routes.routes
        for route in routes:
            self.add_route(route)

    def install(self, plugin):
        ''' Add a plugin to the list of plugins and prepare it for being
            applied to all routes of this application. A plugin may be a simple
            decorator or an object that implements the :class:`Plugin` API.
        '''
        if hasattr(plugin, 'setup'): plugin.setup(self)
        if not callable(plugin) and not hasattr(plugin, 'apply'):
            raise TypeError("Plugins must be callable or implement .apply()")
        self.plugins.append(plugin)
        self.reset()
        return plugin

    def uninstall(self, plugin):
        ''' Uninstall plugins. Pass an instance to remove a specific plugin, a type
            object to remove all plugins that match that type, a string to remove
            all plugins with a matching ``name`` attribute or ``True`` to remove all
            plugins. Return the list of removed plugins. '''
        removed, remove = [], plugin
        for i, plugin in list(enumerate(self.plugins))[::-1]:
            if remove is True or remove is plugin or remove is type(plugin) \
            or getattr(plugin, 'name', True) == remove:
                removed.append(plugin)
                del self.plugins[i]
                if hasattr(plugin, 'close'): plugin.close()
        if removed: self.reset()
        return removed

    def run(self, **kwargs):
        ''' Calls :func:`run` with the same parameters. '''
        run(self, **kwargs)

    def reset(self, route=None):
        ''' Reset all routes (force plugins to be re-applied) and clear all
            caches. If an ID or route object is given, only that specific route
            is affected. '''
        if route is None: routes = self.routes
        elif isinstance(route, Route): routes = [route]
        else: routes = [self.routes[route]]
        for route in routes: route.reset()
        if DEBUG:
            for route in routes: route.prepare()
        self.hooks.trigger('app_reset')

    def close(self):
        ''' Close the application and all installed plugins. '''
        for plugin in self.plugins:
            if hasattr(plugin, 'close'): plugin.close()
        self.stopped = True

    def match(self, environ):
        """ Search for a matching route and return a (:class:`Route` , urlargs)
            tuple. The second value is a dictionary with parameters extracted
            from the URL. Raise :exc:`HTTPError` (404/405) on a non-match."""
        return self.router.match(environ)

    def get_url(self, routename, **kargs):
        """ Return a string that matches a named route """
        scriptname = request.environ.get('SCRIPT_NAME', '').strip('/') + '/'
        location = self.router.build(routename, **kargs).lstrip('/')
        return urljoin(urljoin('/', scriptname), location)

    def add_route(self, route):
        ''' Add a route object, but do not change the :data:`Route.app`
            attribute.'''
        self.routes.append(route)
        self.router.add(route.rule, route.method, route, name=route.name)
        if DEBUG: route.prepare()

    def route(self, path=None, method='GET', callback=None, name=None,
              apply=None, skip=None, **config):
        """ A decorator to bind a function to a request URL. Example::

                @app.route('/hello/:name')
                def hello(name):
                    return 'Hello %s' % name

            The ``:name`` part is a wildcard. See :class:`Router` for syntax
            details.

            :param path: Request path or a list of paths to listen to. If no
              path is specified, it is automatically generated from the
              signature of the function.
            :param method: HTTP method (`GET`, `POST`, `PUT`, ...) or a list of
              methods to listen to. (default: `GET`)
            :param callback: An optional shortcut to avoid the decorator
              syntax. ``route(..., callback=func)`` equals ``route(...)(func)``
            :param name: The name for this route. (default: None)
            :param apply: A decorator or plugin or a list of plugins. These are
              applied to the route callback in addition to installed plugins.
            :param skip: A list of plugins, plugin classes or names. Matching
              plugins are not installed to this route. ``True`` skips all.

            Any additional keyword arguments are stored as route-specific
            configuration and passed to plugins (see :meth:`Plugin.apply`).
        """
        if callable(path): path, callback = None, path
        plugins = makelist(apply)
        skiplist = makelist(skip)
        def decorator(callback):
            # TODO: Documentation and tests
            if isinstance(callback, basestring): callback = load(callback)
            for rule in makelist(path) or yieldroutes(callback):
                for verb in makelist(method):
                    verb = verb.upper()
                    route = Route(self, rule, verb, callback, name=name,
                                  plugins=plugins, skiplist=skiplist, **config)
                    self.add_route(route)
            return callback
        return decorator(callback) if callback else decorator

    def get(self, path=None, method='GET', **options):
        """ Equals :meth:`route`. """
        return self.route(path, method, **options)

    def post(self, path=None, method='POST', **options):
        """ Equals :meth:`route` with a ``POST`` method parameter. """
        return self.route(path, method, **options)

    def put(self, path=None, method='PUT', **options):
        """ Equals :meth:`route` with a ``PUT`` method parameter. """
        return self.route(path, method, **options)

    def delete(self, path=None, method='DELETE', **options):
        """ Equals :meth:`route` with a ``DELETE`` method parameter. """
        return self.route(path, method, **options)

    def error(self, code=500):
        """ Decorator: Register an output handler for a HTTP error code"""
        def wrapper(handler):
            self.error_handler[int(code)] = handler
            return handler
        return wrapper

    def hook(self, name):
        """ Return a decorator that attaches a callback to a hook. Three hooks
            are currently implemented:

            - before_request: Executed once before each request
            - after_request: Executed once after each request
            - app_reset: Called whenever :meth:`reset` is called.
        """
        def wrapper(func):
            self.hooks.add(name, func)
            return func
        return wrapper

    def handle(self, path, method='GET'):
        """ (deprecated) Execute the first matching route callback and return
            the result. :exc:`HTTPResponse` exceptions are caught and returned.
            If :attr:`Bottle.catchall` is true, other exceptions are caught as
            well and returned as :exc:`HTTPError` instances (500).
        """
        depr("This method will change semantics in 0.10. Try to avoid it.")
        if isinstance(path, dict):
            return self._handle(path)
        return self._handle({'PATH_INFO': path, 'REQUEST_METHOD': method.upper()})

    def default_error_handler(self, res):
        return tob(template(ERROR_PAGE_TEMPLATE, e=res))

    def _handle(self, environ):
        try:
            environ['bottle.app'] = self
            request.bind(environ)
            response.bind()
            route, args = self.router.match(environ)
            environ['route.handle'] = route
            environ['bottle.route'] = route
            environ['route.url_args'] = args
            return route.call(**args)
        except HTTPResponse:
            return _e()
        except RouteReset:
            route.reset()
            return self._handle(environ)
        except (KeyboardInterrupt, SystemExit, MemoryError):
            raise
        except Exception:
            if not self.catchall: raise
            stacktrace = format_exc()
            environ['wsgi.errors'].write(stacktrace)
            return HTTPError(500, "Internal Server Error", _e(), stacktrace)

    def _cast(self, out, peek=None):
        """ Try to convert the parameter into something WSGI compatible and set
        correct HTTP headers when possible.
        Support: False, str, unicode, dict, HTTPResponse, HTTPError, file-like,
        iterable of strings and iterable of unicodes
        """

        # Empty output is done here
        if not out:
            if 'Content-Length' not in response:
                response['Content-Length'] = 0
            return []
        # Join lists of byte or unicode strings. Mixed lists are NOT supported
        if isinstance(out, (tuple, list))\
        and isinstance(out[0], (bytes, unicode)):
            out = out[0][0:0].join(out) # b'abc'[0:0] -> b''
        # Encode unicode strings
        if isinstance(out, unicode):
            out = out.encode(response.charset)
        # Byte Strings are just returned
        if isinstance(out, bytes):
            if 'Content-Length' not in response:
                response['Content-Length'] = len(out)
            return [out]
        # HTTPError or HTTPException (recursive, because they may wrap anything)
        # TODO: Handle these explicitly in handle() or make them iterable.
        if isinstance(out, HTTPError):
            out.apply(response)
            out = self.error_handler.get(out.status_code, self.default_error_handler)(out)
            return self._cast(out)
        if isinstance(out, HTTPResponse):
            out.apply(response)
            return self._cast(out.body)

        # File-like objects.
        if hasattr(out, 'read'):
            if 'wsgi.file_wrapper' in request.environ:
                return request.environ['wsgi.file_wrapper'](out)
            elif hasattr(out, 'close') or not hasattr(out, '__iter__'):
                return WSGIFileWrapper(out)

        # Handle Iterables. We peek into them to detect their inner type.
        try:
            out = iter(out)
            first = next(out)
            while not first:
                first = next(out)
        except StopIteration:
            return self._cast('')
        except HTTPResponse:
            first = _e()
        except (KeyboardInterrupt, SystemExit, MemoryError):
            raise
        except Exception:
            if not self.catchall: raise
            first = HTTPError(500, 'Unhandled exception', _e(), format_exc())

        # These are the inner types allowed in iterator or generator objects.
        if isinstance(first, HTTPResponse):
            return self._cast(first)
        if isinstance(first, bytes):
            return itertools.chain([first], out)
        if isinstance(first, unicode):
            return imap(lambda x: x.encode(response.charset),
                                  itertools.chain([first], out))
        return self._cast(HTTPError(500, 'Unsupported response type: %s'\
                                         % type(first)))

    def wsgi(self, environ, start_response):
        """ The bottle WSGI-interface. """
        try:
            out = self._cast(self._handle(environ))
            # rfc2616 section 4.3
            if response._status_code in (100, 101, 204, 304)\
            or environ['REQUEST_METHOD'] == 'HEAD':
                if hasattr(out, 'close'): out.close()
                out = []
            start_response(response._status_line, response.headerlist)
            return out
        except (KeyboardInterrupt, SystemExit, MemoryError):
            raise
        except Exception:
            if not self.catchall: raise
            err = '<h1>Critical error while processing request: %s</h1>' \
                  % html_escape(environ.get('PATH_INFO', '/'))
            if DEBUG:
                err += '<h2>Error:</h2>\n<pre>\n%s\n</pre>\n' \
                       '<h2>Traceback:</h2>\n<pre>\n%s\n</pre>\n' \
                       % (html_escape(repr(_e())), html_escape(format_exc()))
            environ['wsgi.errors'].write(err)
            headers = [('Content-Type', 'text/html; charset=UTF-8')]
            start_response('500 INTERNAL SERVER ERROR', headers)
            return [tob(err)]

    def __call__(self, environ, start_response):
        ''' Each instance of :class:'Bottle' is a WSGI application. '''
        return self.wsgi(environ, start_response)






###############################################################################
# HTTP and WSGI Tools ##########################################################
###############################################################################


class BaseRequest(object):
    """ A wrapper for WSGI environment dictionaries that adds a lot of
        convenient access methods and properties. Most of them are read-only.

        Adding new attributes to a request actually adds them to the environ
        dictionary (as 'bottle.request.ext.<name>'). This is the recommended
        way to store and access request-specific data.
    """

    __slots__ = ('environ')

    #: Maximum size of memory buffer for :attr:`body` in bytes.
    MEMFILE_MAX = 102400
    #: Maximum number pr GET or POST parameters per request
    MAX_PARAMS  = 100

    def __init__(self, environ=None):
        """ Wrap a WSGI environ dictionary. """
        #: The wrapped WSGI environ dictionary. This is the only real attribute.
        #: All other attributes actually are read-only properties.
        self.environ = {} if environ is None else environ
        self.environ['bottle.request'] = self

    @DictProperty('environ', 'bottle.app', read_only=True)
    def app(self):
        ''' Bottle application handling this request. '''
        raise RuntimeError('This request is not connected to an application.')

    @property
    def path(self):
        ''' The value of ``PATH_INFO`` with exactly one prefixed slash (to fix
            broken clients and avoid the "empty path" edge case). '''
        return '/' + self.environ.get('PATH_INFO','').lstrip('/')

    @property
    def method(self):
        ''' The ``REQUEST_METHOD`` value as an uppercase string. '''
        return self.environ.get('REQUEST_METHOD', 'GET').upper()

    @DictProperty('environ', 'bottle.request.headers', read_only=True)
    def headers(self):
        ''' A :class:`WSGIHeaderDict` that provides case-insensitive access to
            HTTP request headers. '''
        return WSGIHeaderDict(self.environ)

    def get_header(self, name, default=None):
        ''' Return the value of a request header, or a given default value. '''
        return self.headers.get(name, default)

    @DictProperty('environ', 'bottle.request.cookies', read_only=True)
    def cookies(self):
        """ Cookies parsed into a :class:`FormsDict`. Signed cookies are NOT
            decoded. Use :meth:`get_cookie` if you expect signed cookies. """
        cookies = SimpleCookie(self.environ.get('HTTP_COOKIE',''))
        cookies = list(cookies.values())[:self.MAX_PARAMS]
        return FormsDict((c.key, c.value) for c in cookies)

    def get_cookie(self, key, default=None, secret=None):
        """ Return the content of a cookie. To read a `Signed Cookie`, the
            `secret` must match the one used to create the cookie (see
            :meth:`BaseResponse.set_cookie`). If anything goes wrong (missing
            cookie or wrong signature), return a default value. """
        value = self.cookies.get(key)
        if secret and value:
            dec = cookie_decode(value, secret) # (key, value) tuple or None
            return dec[1] if dec and dec[0] == key else default
        return value or default

    @DictProperty('environ', 'bottle.request.query', read_only=True)
    def query(self):
        ''' The :attr:`query_string` parsed into a :class:`FormsDict`. These
            values are sometimes called "URL arguments" or "GET parameters", but
            not to be confused with "URL wildcards" as they are provided by the
            :class:`Router`. '''
        get = self.environ['bottle.get'] = FormsDict()
        pairs = _parse_qsl(self.environ.get('QUERY_STRING', ''))
        for key, value in pairs[:self.MAX_PARAMS]:
            get[key] = value
        return get

    @DictProperty('environ', 'bottle.request.forms', read_only=True)
    def forms(self):
        """ Form values parsed from an `url-encoded` or `multipart/form-data`
            encoded POST or PUT request body. The result is retuned as a
            :class:`FormsDict`. All keys and values are strings. File uploads
            are stored separately in :attr:`files`. """
        forms = FormsDict()
        for name, item in self.POST.allitems():
            if not hasattr(item, 'filename'):
                forms[name] = item
        return forms

    @DictProperty('environ', 'bottle.request.params', read_only=True)
    def params(self):
        """ A :class:`FormsDict` with the combined values of :attr:`query` and
            :attr:`forms`. File uploads are stored in :attr:`files`. """
        params = FormsDict()
        for key, value in self.query.allitems():
            params[key] = value
        for key, value in self.forms.allitems():
            params[key] = value
        return params

    @DictProperty('environ', 'bottle.request.files', read_only=True)
    def files(self):
        """ File uploads parsed from an `url-encoded` or `multipart/form-data`
            encoded POST or PUT request body. The values are instances of
            :class:`cgi.FieldStorage`. The most important attributes are:

            filename
                The filename, if specified; otherwise None; this is the client
                side filename, *not* the file name on which it is stored (that's
                a temporary file you don't deal with)
            file
                The file(-like) object from which you can read the data.
            value
                The value as a *string*; for file uploads, this transparently
                reads the file every time you request the value. Do not do this
                on big files.
        """
        files = FormsDict()
        for name, item in self.POST.allitems():
            if hasattr(item, 'filename'):
                files[name] = item
        return files

    @DictProperty('environ', 'bottle.request.json', read_only=True)
    def json(self):
        ''' If the ``Content-Type`` header is ``application/json``, this
            property holds the parsed content of the request body. Only requests
            smaller than :attr:`MEMFILE_MAX` are processed to avoid memory
            exhaustion. '''
        if 'application/json' in self.environ.get('CONTENT_TYPE', '') \
        and 0 < self.content_length < self.MEMFILE_MAX:
            return json_loads(self.body.read(self.MEMFILE_MAX))
        return None

    @DictProperty('environ', 'bottle.request.body', read_only=True)
    def _body(self):
        maxread = max(0, self.content_length)
        stream = self.environ['wsgi.input']
        body = BytesIO() if maxread < self.MEMFILE_MAX else TemporaryFile(mode='w+b')
        while maxread > 0:
            part = stream.read(min(maxread, self.MEMFILE_MAX))
            if not part: break
            body.write(part)
            maxread -= len(part)
        self.environ['wsgi.input'] = body
        body.seek(0)
        return body

    @property
    def body(self):
        """ The HTTP request body as a seek-able file-like object. Depending on
            :attr:`MEMFILE_MAX`, this is either a temporary file or a
            :class:`io.BytesIO` instance. Accessing this property for the first
            time reads and replaces the ``wsgi.input`` environ variable.
            Subsequent accesses just do a `seek(0)` on the file object. """
        self._body.seek(0)
        return self._body

    #: An alias for :attr:`query`.
    GET = query

    @DictProperty('environ', 'bottle.request.post', read_only=True)
    def POST(self):
        """ The values of :attr:`forms` and :attr:`files` combined into a single
            :class:`FormsDict`. Values are either strings (form values) or
            instances of :class:`cgi.FieldStorage` (file uploads).
        """
        post = FormsDict()
        # We default to application/x-www-form-urlencoded for everything that
        # is not multipart and take the fast path (also: 3.1 workaround)
        if not self.content_type.startswith('multipart/'):
            maxlen = max(0, min(self.content_length, self.MEMFILE_MAX))
            pairs = _parse_qsl(tonat(self.body.read(maxlen), 'latin1'))
            for key, value in pairs[:self.MAX_PARAMS]:
                post[key] = value
            return post

        safe_env = {'QUERY_STRING':''} # Build a safe environment for cgi
        for key in ('REQUEST_METHOD', 'CONTENT_TYPE', 'CONTENT_LENGTH'):
            if key in self.environ: safe_env[key] = self.environ[key]
        args = dict(fp=self.body, environ=safe_env, keep_blank_values=True)
        if py31:
            args['fp'] = NCTextIOWrapper(args['fp'], encoding='ISO-8859-1',
                                         newline='\n')
        elif py3k:
            args['encoding'] = 'ISO-8859-1'
        data = FieldStorage(**args)
        for item in (data.list or [])[:self.MAX_PARAMS]:
            post[item.name] = item if item.filename else item.value
        return post

    @property
    def COOKIES(self):
        ''' Alias for :attr:`cookies` (deprecated). '''
        depr('BaseRequest.COOKIES was renamed to BaseRequest.cookies (lowercase).')
        return self.cookies

    @property
    def url(self):
        """ The full request URI including hostname and scheme. If your app
            lives behind a reverse proxy or load balancer and you get confusing
            results, make sure that the ``X-Forwarded-Host`` header is set
            correctly. """
        return self.urlparts.geturl()

    @DictProperty('environ', 'bottle.request.urlparts', read_only=True)
    def urlparts(self):
        ''' The :attr:`url` string as an :class:`urlparse.SplitResult` tuple.
            The tuple contains (scheme, host, path, query_string and fragment),
            but the fragment is always empty because it is not visible to the
            server. '''
        env = self.environ
        http = env.get('HTTP_X_FORWARDED_PROTO') or env.get('wsgi.url_scheme', 'http')
        host = env.get('HTTP_X_FORWARDED_HOST') or env.get('HTTP_HOST')
        if not host:
            # HTTP 1.1 requires a Host-header. This is for HTTP/1.0 clients.
            host = env.get('SERVER_NAME', '127.0.0.1')
            port = env.get('SERVER_PORT')
            if port and port != ('80' if http == 'http' else '443'):
                host += ':' + port
        path = urlquote(self.fullpath)
        return UrlSplitResult(http, host, path, env.get('QUERY_STRING'), '')

    @property
    def fullpath(self):
        """ Request path including :attr:`script_name` (if present). """
        return urljoin(self.script_name, self.path.lstrip('/'))

    @property
    def query_string(self):
        """ The raw :attr:`query` part of the URL (everything in between ``?``
            and ``#``) as a string. """
        return self.environ.get('QUERY_STRING', '')

    @property
    def script_name(self):
        ''' The initial portion of the URL's `path` that was removed by a higher
            level (server or routing middleware) before the application was
            called. This script path is returned with leading and tailing
            slashes. '''
        script_name = self.environ.get('SCRIPT_NAME', '').strip('/')
        return '/' + script_name + '/' if script_name else '/'

    def path_shift(self, shift=1):
        ''' Shift path segments from :attr:`path` to :attr:`script_name` and
            vice versa.

           :param shift: The number of path segments to shift. May be negative
                         to change the shift direction. (default: 1)
        '''
        script = self.environ.get('SCRIPT_NAME','/')
        self['SCRIPT_NAME'], self['PATH_INFO'] = path_shift(script, self.path, shift)

    @property
    def content_length(self):
        ''' The request body length as an integer. The client is responsible to
            set this header. Otherwise, the real length of the body is unknown
            and -1 is returned. In this case, :attr:`body` will be empty. '''
        return int(self.environ.get('CONTENT_LENGTH') or -1)

    @property
    def content_type(self):
        ''' The Content-Type header as a lowercase-string (default: empty). '''
        return self.environ.get('CONTENT_TYPE', '').lower()

    @property
    def is_xhr(self):
        ''' True if the request was triggered by a XMLHttpRequest. This only
            works with JavaScript libraries that support the `X-Requested-With`
            header (most of the popular libraries do). '''
        requested_with = self.environ.get('HTTP_X_REQUESTED_WITH','')
        return requested_with.lower() == 'xmlhttprequest'

    @property
    def is_ajax(self):
        ''' Alias for :attr:`is_xhr`. "Ajax" is not the right term. '''
        return self.is_xhr

    @property
    def auth(self):
        """ HTTP authentication data as a (user, password) tuple. This
            implementation currently supports basic (not digest) authentication
            only. If the authentication happened at a higher level (e.g. in the
            front web-server or a middleware), the password field is None, but
            the user field is looked up from the ``REMOTE_USER`` environ
            variable. On any errors, None is returned. """
        basic = parse_auth(self.environ.get('HTTP_AUTHORIZATION',''))
        if basic: return basic
        ruser = self.environ.get('REMOTE_USER')
        if ruser: return (ruser, None)
        return None

    @property
    def remote_route(self):
        """ A list of all IPs that were involved in this request, starting with
            the client IP and followed by zero or more proxies. This does only
            work if all proxies support the ```X-Forwarded-For`` header. Note
            that this information can be forged by malicious clients. """
        proxy = self.environ.get('HTTP_X_FORWARDED_FOR')
        if proxy: return [ip.strip() for ip in proxy.split(',')]
        remote = self.environ.get('REMOTE_ADDR')
        return [remote] if remote else []

    @property
    def remote_addr(self):
        """ The client IP as a string. Note that this information can be forged
            by malicious clients. """
        route = self.remote_route
        return route[0] if route else None

    def copy(self):
        """ Return a new :class:`Request` with a shallow :attr:`environ` copy. """
        return Request(self.environ.copy())

    def get(self, value, default=None): return self.environ.get(value, default)
    def __getitem__(self, key): return self.environ[key]
    def __delitem__(self, key): self[key] = ""; del(self.environ[key])
    def __iter__(self): return iter(self.environ)
    def __len__(self): return len(self.environ)
    def keys(self): return self.environ.keys()
    def __setitem__(self, key, value):
        """ Change an environ value and clear all caches that depend on it. """

        if self.environ.get('bottle.request.readonly'):
            raise KeyError('The environ dictionary is read-only.')

        self.environ[key] = value
        todelete = ()

        if key == 'wsgi.input':
            todelete = ('body', 'forms', 'files', 'params', 'post', 'json')
        elif key == 'QUERY_STRING':
            todelete = ('query', 'params')
        elif key.startswith('HTTP_'):
            todelete = ('headers', 'cookies')

        for key in todelete:
            self.environ.pop('bottle.request.'+key, None)

    def __repr__(self):
        return '<%s: %s %s>' % (self.__class__.__name__, self.method, self.url)

    def __getattr__(self, name):
        ''' Search in self.environ for additional user defined attributes. '''
        try:
            var = self.environ['bottle.request.ext.%s'%name]
            return var.__get__(self) if hasattr(var, '__get__') else var
        except KeyError:
            raise AttributeError('Attribute %r not defined.' % name)

    def __setattr__(self, name, value):
        if name == 'environ': return object.__setattr__(self, name, value)
        self.environ['bottle.request.ext.%s'%name] = value




def _hkey(s):
    return s.title().replace('_','-')


class HeaderProperty(object):
    def __init__(self, name, reader=None, writer=str, default=''):
        self.name, self.default = name, default
        self.reader, self.writer = reader, writer
        self.__doc__ = 'Current value of the %r header.' % name.title()

    def __get__(self, obj, cls):
        if obj is None: return self
        value = obj.headers.get(self.name, self.default)
        return self.reader(value) if self.reader else value

    def __set__(self, obj, value):
        obj.headers[self.name] = self.writer(value)

    def __delete__(self, obj):
        del obj.headers[self.name]


class BaseResponse(object):
    """ Storage class for a response body as well as headers and cookies.

        This class does support dict-like case-insensitive item-access to
        headers, but is NOT a dict. Most notably, iterating over a response
        yields parts of the body and not the headers.
    """

    default_status = 200
    default_content_type = 'text/html; charset=UTF-8'

    # Header blacklist for specific response codes
    # (rfc2616 section 10.2.3 and 10.3.5)
    bad_headers = {
        204: set(('Content-Type',)),
        304: set(('Allow', 'Content-Encoding', 'Content-Language',
                  'Content-Length', 'Content-Range', 'Content-Type',
                  'Content-Md5', 'Last-Modified'))}

    def __init__(self, body='', status=None, **headers):
        self._cookies = None
        self._headers = {}
        self.body = body
        self.status = status or self.default_status
        if headers:
            for name, value in headers.items():
                self[name] = value

    def copy(self):
        ''' Returns a copy of self. '''
        copy = Response()
        copy.status = self.status
        copy._headers = dict((k, v[:]) for (k, v) in self._headers.items())
        return copy

    def __iter__(self):
        return iter(self.body)

    def close(self):
        if hasattr(self.body, 'close'):
            self.body.close()

    @property
    def status_line(self):
        ''' The HTTP status line as a string (e.g. ``404 Not Found``).'''
        return self._status_line

    @property
    def status_code(self):
        ''' The HTTP status code as an integer (e.g. 404).'''
        return self._status_code

    def _set_status(self, status):
        if isinstance(status, int):
            code, status = status, _HTTP_STATUS_LINES.get(status)
        elif ' ' in status:
            status = status.strip()
            code   = int(status.split()[0])
        else:
            raise ValueError('String status line without a reason phrase.')
        if not 100 <= code <= 999: raise ValueError('Status code out of range.')
        self._status_code = code
        self._status_line = str(status or ('%d Unknown' % code))

    def _get_status(self):
        return self._status_line

    status = property(_get_status, _set_status, None,
        ''' A writeable property to change the HTTP response status. It accepts
            either a numeric code (100-999) or a string with a custom reason
            phrase (e.g. "404 Brain not found"). Both :data:`status_line` and
            :data:`status_code` are updated accordingly. The return value is
            always a status string. ''')
    del _get_status, _set_status

    @property
    def headers(self):
        ''' An instance of :class:`HeaderDict`, a case-insensitive dict-like
            view on the response headers. '''
        hdict = HeaderDict()
        hdict.dict = self._headers
        return hdict

    def __contains__(self, name): return _hkey(name) in self._headers
    def __delitem__(self, name):  del self._headers[_hkey(name)]
    def __getitem__(self, name):  return self._headers[_hkey(name)][-1]
    def __setitem__(self, name, value): self._headers[_hkey(name)] = [str(value)]

    def get_header(self, name, default=None):
        ''' Return the value of a previously defined header. If there is no
            header with that name, return a default value. '''
        return self._headers.get(_hkey(name), [default])[-1]

    def set_header(self, name, value):
        ''' Create a new response header, replacing any previously defined
            headers with the same name. '''
        self._headers[_hkey(name)] = [str(value)]

    def add_header(self, name, value):
        ''' Add an additional response header, not removing duplicates. '''
        self._headers.setdefault(_hkey(name), []).append(str(value))

    def iter_headers(self):
        ''' Yield (header, value) tuples, skipping headers that are not
            allowed with the current response status code. '''
        return self.headerlist

    def wsgiheader(self):
        depr('The wsgiheader method is deprecated. See headerlist.') #0.10
        return self.headerlist

    @property
    def headerlist(self):
        ''' WSGI conform list of (header, value) tuples. '''
        out = []
        headers = list(self._headers.items())
        if 'Content-Type' not in self._headers:
            headers.append(('Content-Type', [self.default_content_type]))
        if self._status_code in self.bad_headers:
            bad_headers = self.bad_headers[self._status_code]
            headers = [h for h in headers if h[0] not in bad_headers]
        out += [(name, val) for name, vals in headers for val in vals]
        if self._cookies:
            for c in self._cookies.values():
                out.append(('Set-Cookie', c.OutputString()))
        return out

    content_type = HeaderProperty('Content-Type')
    content_length = HeaderProperty('Content-Length', reader=int)

    @property
    def charset(self):
        """ Return the charset specified in the content-type header (default: utf8). """
        if 'charset=' in self.content_type:
            return self.content_type.split('charset=')[-1].split(';')[0].strip()
        return 'UTF-8'

    @property
    def COOKIES(self):
        """ A dict-like SimpleCookie instance. This should not be used directly.
            See :meth:`set_cookie`. """
        depr('The COOKIES dict is deprecated. Use `set_cookie()` instead.') # 0.10
        if not self._cookies:
            self._cookies = SimpleCookie()
        return self._cookies

    def set_cookie(self, name, value, secret=None, **options):
        ''' Create a new cookie or replace an old one. If the `secret` parameter is
            set, create a `Signed Cookie` (described below).

            :param name: the name of the cookie.
            :param value: the value of the cookie.
            :param secret: a signature key required for signed cookies.

            Additionally, this method accepts all RFC 2109 attributes that are
            supported by :class:`cookie.Morsel`, including:

            :param max_age: maximum age in seconds. (default: None)
            :param expires: a datetime object or UNIX timestamp. (default: None)
            :param domain: the domain that is allowed to read the cookie.
              (default: current domain)
            :param path: limits the cookie to a given path (default: current path)
            :param secure: limit the cookie to HTTPS connections (default: off).
            :param httponly: prevents client-side javascript to read this cookie
              (default: off, requires Python 2.6 or newer).

            If neither `expires` nor `max_age` is set (default), the cookie will
            expire at the end of the browser session (as soon as the browser
            window is closed).

            Signed cookies may store any pickle-able object and are
            cryptographically signed to prevent manipulation. Keep in mind that
            cookies are limited to 4kb in most browsers.

            Warning: Signed cookies are not encrypted (the client can still see
            the content) and not copy-protected (the client can restore an old
            cookie). The main intention is to make pickling and unpickling
            save, not to store secret information at client side.
        '''
        if not self._cookies:
            self._cookies = SimpleCookie()

        if secret:
            value = touni(cookie_encode((name, value), secret))
        elif not isinstance(value, basestring):
            raise TypeError('Secret key missing for non-string Cookie.')

        if len(value) > 4096: raise ValueError('Cookie value to long.')
        self._cookies[name] = value

        for key, value in options.items():
            if key == 'max_age':
                if isinstance(value, timedelta):
                    value = value.seconds + value.days * 24 * 3600
            if key == 'expires':
                if isinstance(value, (datedate, datetime)):
                    value = value.timetuple()
                elif isinstance(value, (int, float)):
                    value = time.gmtime(value)
                value = time.strftime("%a, %d %b %Y %H:%M:%S GMT", value)
            self._cookies[name][key.replace('_', '-')] = value

    def delete_cookie(self, key, **kwargs):
        ''' Delete a cookie. Be sure to use the same `domain` and `path`
            settings as used to create the cookie. '''
        kwargs['max_age'] = -1
        kwargs['expires'] = 0
        self.set_cookie(key, '', **kwargs)

    def __repr__(self):
        out = ''
        for name, value in self.headerlist:
            out += '%s: %s\n' % (name.title(), value.strip())
        return out

#: Thread-local storage for :class:`LocalRequest` and :class:`LocalResponse`
#: attributes.
_lctx = threading.local()

def local_property(name):
    def fget(self):
        try:
            return getattr(_lctx, name)
        except AttributeError:
            raise RuntimeError("Request context not initialized.")
    def fset(self, value): setattr(_lctx, name, value)
    def fdel(self): delattr(_lctx, name)
    return property(fget, fset, fdel,
        'Thread-local property stored in :data:`_lctx.%s`' % name)


class LocalRequest(BaseRequest):
    ''' A thread-local subclass of :class:`BaseRequest` with a different
        set of attribues for each thread. There is usually only one global
        instance of this class (:data:`request`). If accessed during a
        request/response cycle, this instance always refers to the *current*
        request (even on a multithreaded server). '''
    bind = BaseRequest.__init__
    environ = local_property('request_environ')


class LocalResponse(BaseResponse):
    ''' A thread-local subclass of :class:`BaseResponse` with a different
        set of attribues for each thread. There is usually only one global
        instance of this class (:data:`response`). Its attributes are used
        to build the HTTP response at the end of the request/response cycle.
    '''
    bind = BaseResponse.__init__
    _status_line = local_property('response_status_line')
    _status_code = local_property('response_status_code')
    _cookies     = local_property('response_cookies')
    _headers     = local_property('response_headers')
    body         = local_property('response_body')

Request = BaseRequest
Response = BaseResponse

class HTTPResponse(Response, BottleException):
    def __init__(self, body='', status=None, header=None, **headers):
        if header or 'output' in headers:
            depr('Call signature changed (for the better)')
            if header: headers.update(header)
            if 'output' in headers: body = headers.pop('output')
        super(HTTPResponse, self).__init__(body, status, **headers)

    def apply(self, response):
        response._status_code = self._status_code
        response._status_line = self._status_line
        response._headers = self._headers
        response._cookies = self._cookies
        response.body = self.body

    def _output(self, value=None):
        depr('Use HTTPResponse.body instead of HTTPResponse.output')
        if value is None: return self.body
        self.body = value

    output = property(_output, _output, doc='Alias for .body')

class HTTPError(HTTPResponse):
    default_status = 500
    def __init__(self, status=None, body=None, exception=None, traceback=None, header=None, **headers):
        self.exception = exception
        self.traceback = traceback
        super(HTTPError, self).__init__(body, status, header, **headers)





###############################################################################
# Plugins ######################################################################
###############################################################################

class PluginError(BottleException): pass

class JSONPlugin(object):
    name = 'json'
    api  = 2

    def __init__(self, json_dumps=json_dumps):
        self.json_dumps = json_dumps

    def apply(self, callback, route):
        dumps = self.json_dumps
        if not dumps: return callback
        def wrapper(*a, **ka):
            rv = callback(*a, **ka)
            if isinstance(rv, dict):
                #Attempt to serialize, raises exception on failure
                json_response = dumps(rv)
                #Set content type only if serialization succesful
                response.content_type = 'application/json'
                return json_response
            return rv
        return wrapper


class HooksPlugin(object):
    name = 'hooks'
    api  = 2

    _names = 'before_request', 'after_request', 'app_reset'

    def __init__(self):
        self.hooks = dict((name, []) for name in self._names)
        self.app = None

    def _empty(self):
        return not (self.hooks['before_request'] or self.hooks['after_request'])

    def setup(self, app):
        self.app = app

    def add(self, name, func):
        ''' Attach a callback to a hook. '''
        was_empty = self._empty()
        self.hooks.setdefault(name, []).append(func)
        if self.app and was_empty and not self._empty(): self.app.reset()

    def remove(self, name, func):
        ''' Remove a callback from a hook. '''
        was_empty = self._empty()
        if name in self.hooks and func in self.hooks[name]:
            self.hooks[name].remove(func)
        if self.app and not was_empty and self._empty(): self.app.reset()

    def trigger(self, name, *a, **ka):
        ''' Trigger a hook and return a list of results. '''
        hooks = self.hooks[name]
        if ka.pop('reversed', False): hooks = hooks[::-1]
        return [hook(*a, **ka) for hook in hooks]

    def apply(self, callback, route):
        if self._empty(): return callback
        def wrapper(*a, **ka):
            self.trigger('before_request')
            rv = callback(*a, **ka)
            self.trigger('after_request', reversed=True)
            return rv
        return wrapper


class TemplatePlugin(object):
    ''' This plugin applies the :func:`view` decorator to all routes with a
        `template` config parameter. If the parameter is a tuple, the second
        element must be a dict with additional options (e.g. `template_engine`)
        or default variables for the template. '''
    name = 'template'
    api  = 2

    def apply(self, callback, route):
        conf = route.config.get('template')
        if isinstance(conf, (tuple, list)) and len(conf) == 2:
            return view(conf[0], **conf[1])(callback)
        elif isinstance(conf, str) and 'template_opts' in route.config:
            depr('The `template_opts` parameter is deprecated.') #0.9
            return view(conf, **route.config['template_opts'])(callback)
        elif isinstance(conf, str):
            return view(conf)(callback)
        else:
            return callback


#: Not a plugin, but part of the plugin API. TODO: Find a better place.
class _ImportRedirect(object):
    def __init__(self, name, impmask):
        ''' Create a virtual package that redirects imports (see PEP 302). '''
        self.name = name
        self.impmask = impmask
        self.module = sys.modules.setdefault(name, imp.new_module(name))
        self.module.__dict__.update({'__file__': __file__, '__path__': [],
                                    '__all__': [], '__loader__': self})
        sys.meta_path.append(self)

    def find_module(self, fullname, path=None):
        if '.' not in fullname: return
        packname, modname = fullname.rsplit('.', 1)
        if packname != self.name: return
        return self

    def load_module(self, fullname):
        if fullname in sys.modules: return sys.modules[fullname]
        packname, modname = fullname.rsplit('.', 1)
        realname = self.impmask % modname
        __import__(realname)
        module = sys.modules[fullname] = sys.modules[realname]
        setattr(self.module, modname, module)
        module.__loader__ = self
        return module






###############################################################################
# Common Utilities #############################################################
###############################################################################


class MultiDict(DictMixin):
    """ This dict stores multiple values per key, but behaves exactly like a
        normal dict in that it returns only the newest value for any given key.
        There are special methods available to access the full list of values.
    """

    def __init__(self, *a, **k):
        self.dict = dict((k, [v]) for (k, v) in dict(*a, **k).items())

    def __len__(self): return len(self.dict)
    def __iter__(self): return iter(self.dict)
    def __contains__(self, key): return key in self.dict
    def __delitem__(self, key): del self.dict[key]
    def __getitem__(self, key): return self.dict[key][-1]
    def __setitem__(self, key, value): self.append(key, value)
    def keys(self): return self.dict.keys()

    if py3k:
        def values(self): return (v[-1] for v in self.dict.values())
        def items(self): return ((k, v[-1]) for k, v in self.dict.items())
        def allitems(self):
            return ((k, v) for k, vl in self.dict.items() for v in vl)
        iterkeys = keys
        itervalues = values
        iteritems = items
        iterallitems = allitems

    else:
        def values(self): return [v[-1] for v in self.dict.values()]
        def items(self): return [(k, v[-1]) for k, v in self.dict.items()]
        def iterkeys(self): return self.dict.iterkeys()
        def itervalues(self): return (v[-1] for v in self.dict.itervalues())
        def iteritems(self):
            return ((k, v[-1]) for k, v in self.dict.iteritems())
        def iterallitems(self):
            return ((k, v) for k, vl in self.dict.iteritems() for v in vl)
        def allitems(self):
            return [(k, v) for k, vl in self.dict.iteritems() for v in vl]

    def get(self, key, default=None, index=-1, type=None):
        ''' Return the most recent value for a key.

            :param default: The default value to be returned if the key is not
                   present or the type conversion fails.
            :param index: An index for the list of available values.
            :param type: If defined, this callable is used to cast the value
                    into a specific type. Exception are suppressed and result in
                    the default value to be returned.
        '''
        try:
            val = self.dict[key][index]
            return type(val) if type else val
        except Exception:
            pass
        return default

    def append(self, key, value):
        ''' Add a new value to the list of values for this key. '''
        self.dict.setdefault(key, []).append(value)

    def replace(self, key, value):
        ''' Replace the list of values with a single value. '''
        self.dict[key] = [value]

    def getall(self, key):
        ''' Return a (possibly empty) list of values for a key. '''
        return self.dict.get(key) or []

    #: Aliases for WTForms to mimic other multi-dict APIs (Django)
    getone = get
    getlist = getall



class FormsDict(MultiDict):
    ''' This :class:`MultiDict` subclass is used to store request form data.
        Additionally to the normal dict-like item access methods (which return
        unmodified data as native strings), this container also supports
        attribute-like access to its values. Attributes are automatically de-
        or recoded to match :attr:`input_encoding` (default: 'utf8'). Missing
        attributes default to an empty string. '''

    #: Encoding used for attribute values.
    input_encoding = 'utf8'
    #: If true (default), unicode strings are first encoded with `latin1`
    #: and then decoded to match :attr:`input_encoding`.
    recode_unicode = True

    def _fix(self, s, encoding=None):
        if isinstance(s, unicode) and self.recode_unicode: # Python 3 WSGI
            s = s.encode('latin1')
        if isinstance(s, bytes): # Python 2 WSGI
            return s.decode(encoding or self.input_encoding)
        return s

    def decode(self, encoding=None):
        ''' Returns a copy with all keys and values de- or recoded to match
            :attr:`input_encoding`. Some libraries (e.g. WTForms) want a
            unicode dictionary. '''
        copy = FormsDict()
        enc = copy.input_encoding = encoding or self.input_encoding
        copy.recode_unicode = False
        for key, value in self.allitems():
            copy.append(self._fix(key, enc), self._fix(value, enc))
        return copy

    def getunicode(self, name, default=None, encoding=None):
        try:
            return self._fix(self[name], encoding)
        except (UnicodeError, KeyError):
            return default

    def __getattr__(self, name, default=unicode()):
        # Without this guard, pickle generates a cryptic TypeError:
        if name.startswith('__') and name.endswith('__'):
            return super(FormsDict, self).__getattr__(name)
        return self.getunicode(name, default=default)


class HeaderDict(MultiDict):
    """ A case-insensitive version of :class:`MultiDict` that defaults to
        replace the old value instead of appending it. """

    def __init__(self, *a, **ka):
        self.dict = {}
        if a or ka: self.update(*a, **ka)

    def __contains__(self, key): return _hkey(key) in self.dict
    def __delitem__(self, key): del self.dict[_hkey(key)]
    def __getitem__(self, key): return self.dict[_hkey(key)][-1]
    def __setitem__(self, key, value): self.dict[_hkey(key)] = [str(value)]
    def append(self, key, value):
        self.dict.setdefault(_hkey(key), []).append(str(value))
    def replace(self, key, value): self.dict[_hkey(key)] = [str(value)]
    def getall(self, key): return self.dict.get(_hkey(key)) or []
    def get(self, key, default=None, index=-1):
        return MultiDict.get(self, _hkey(key), default, index)
    def filter(self, names):
        for name in [_hkey(n) for n in names]:
            if name in self.dict:
                del self.dict[name]


class WSGIHeaderDict(DictMixin):
    ''' This dict-like class wraps a WSGI environ dict and provides convenient
        access to HTTP_* fields. Keys and values are native strings
        (2.x bytes or 3.x unicode) and keys are case-insensitive. If the WSGI
        environment contains non-native string values, these are de- or encoded
        using a lossless 'latin1' character set.

        The API will remain stable even on changes to the relevant PEPs.
        Currently PEP 333, 444 and 3333 are supported. (PEP 444 is the only one
        that uses non-native strings.)
    '''
    #: List of keys that do not have a ``HTTP_`` prefix.
    cgikeys = ('CONTENT_TYPE', 'CONTENT_LENGTH')

    def __init__(self, environ):
        self.environ = environ

    def _ekey(self, key):
        ''' Translate header field name to CGI/WSGI environ key. '''
        key = key.replace('-','_').upper()
        if key in self.cgikeys:
            return key
        return 'HTTP_' + key

    def raw(self, key, default=None):
        ''' Return the header value as is (may be bytes or unicode). '''
        return self.environ.get(self._ekey(key), default)

    def __getitem__(self, key):
        return tonat(self.environ[self._ekey(key)], 'latin1')

    def __setitem__(self, key, value):
        raise TypeError("%s is read-only." % self.__class__)

    def __delitem__(self, key):
        raise TypeError("%s is read-only." % self.__class__)

    def __iter__(self):
        for key in self.environ:
            if key[:5] == 'HTTP_':
                yield key[5:].replace('_', '-').title()
            elif key in self.cgikeys:
                yield key.replace('_', '-').title()

    def keys(self): return [x for x in self]
    def __len__(self): return len(self.keys())
    def __contains__(self, key): return self._ekey(key) in self.environ


class ConfigDict(dict):
    ''' A dict-subclass with some extras: You can access keys like attributes.
        Uppercase attributes create new ConfigDicts and act as name-spaces.
        Other missing attributes return None. Calling a ConfigDict updates its
        values and returns itself.

        >>> cfg = ConfigDict()
        >>> cfg.Namespace.value = 5
        >>> cfg.OtherNamespace(a=1, b=2)
        >>> cfg
        {'Namespace': {'value': 5}, 'OtherNamespace': {'a': 1, 'b': 2}}
    '''

    def __getattr__(self, key):
        if key not in self and key[0].isupper():
            self[key] = ConfigDict()
        return self.get(key)

    def __setattr__(self, key, value):
        if hasattr(dict, key):
            raise AttributeError('Read-only attribute.')
        if key in self and self[key] and isinstance(self[key], ConfigDict):
            raise AttributeError('Non-empty namespace attribute.')
        self[key] = value

    def __delattr__(self, key):
        if key in self: del self[key]

    def __call__(self, *a, **ka):
        for key, value in dict(*a, **ka).items(): setattr(self, key, value)
        return self


class AppStack(list):
    """ A stack-like list. Calling it returns the head of the stack. """

    def __call__(self):
        """ Return the current default application. """
        return self[-1]

    def push(self, value=None):
        """ Add a new :class:`Bottle` instance to the stack """
        if not isinstance(value, Bottle):
            value = Bottle()
        self.append(value)
        return value


class WSGIFileWrapper(object):

    def __init__(self, fp, buffer_size=1024*64):
        self.fp, self.buffer_size = fp, buffer_size
        for attr in ('fileno', 'close', 'read', 'readlines', 'tell', 'seek'):
            if hasattr(fp, attr): setattr(self, attr, getattr(fp, attr))

    def __iter__(self):
        buff, read = self.buffer_size, self.read
        while True:
            part = read(buff)
            if not part: return
            yield part


class ResourceManager(object):
    ''' This class manages a list of search paths and helps to find and open
        application-bound resources (files).

        :param base: default value for :meth:`add_path` calls.
        :param opener: callable used to open resources.
        :param cachemode: controls which lookups are cached. One of 'all',
                         'found' or 'none'.
    '''

    def __init__(self, base='./', opener=open, cachemode='all'):
        self.opener = open
        self.base = base
        self.cachemode = cachemode

        #: A list of search paths. See :meth:`add_path` for details.
        self.path = []
        #: A cache for resolved paths. ``res.cache.clear()`` clears the cache.
        self.cache = {}

    def add_path(self, path, base=None, index=None, create=False):
        ''' Add a new path to the list of search paths. Return False if the
            path does not exist.

            :param path: The new search path. Relative paths are turned into
                an absolute and normalized form. If the path looks like a file
                (not ending in `/`), the filename is stripped off.
            :param base: Path used to absolutize relative search paths.
                Defaults to :attr:`base` which defaults to ``os.getcwd()``.
            :param index: Position within the list of search paths. Defaults
                to last index (appends to the list).

            The `base` parameter makes it easy to reference files installed
            along with a python module or package::

                res.add_path('./resources/', __file__)
        '''
        base = os.path.abspath(os.path.dirname(base or self.base))
        path = os.path.abspath(os.path.join(base, os.path.dirname(path)))
        path += os.sep
        if path in self.path:
            self.path.remove(path)
        if create and not os.path.isdir(path):
            os.makedirs(path)
        if index is None:
            self.path.append(path)
        else:
            self.path.insert(index, path)
        self.cache.clear()
        return os.path.exists(path)

    def __iter__(self):
        ''' Iterate over all existing files in all registered paths. '''
        search = self.path[:]
        while search:
            path = search.pop()
            if not os.path.isdir(path): continue
            for name in os.listdir(path):
                full = os.path.join(path, name)
                if os.path.isdir(full): search.append(full)
                else: yield full

    def lookup(self, name):
        ''' Search for a resource and return an absolute file path, or `None`.

            The :attr:`path` list is searched in order. The first match is
            returend. Symlinks are followed. The result is cached to speed up
            future lookups. '''
        if name not in self.cache or DEBUG:
            for path in self.path:
                fpath = os.path.join(path, name)
                if os.path.isfile(fpath):
                    if self.cachemode in ('all', 'found'):
                        self.cache[name] = fpath
                    return fpath
            if self.cachemode == 'all':
                self.cache[name] = None
        return self.cache[name]

    def open(self, name, mode='r', *args, **kwargs):
        ''' Find a resource and return a file object, or raise IOError. '''
        fname = self.lookup(name)
        if not fname: raise IOError("Resource %r not found." % name)
        return self.opener(name, mode=mode, *args, **kwargs)






###############################################################################
# Application Helper ###########################################################
###############################################################################


def abort(code=500, text='Unknown Error: Application stopped.'):
    """ Aborts execution and causes a HTTP error. """
    raise HTTPError(code, text)


def redirect(url, code=None):
    """ Aborts execution and causes a 303 or 302 redirect, depending on
        the HTTP protocol version. """
    if code is None:
        code = 303 if request.get('SERVER_PROTOCOL') == "HTTP/1.1" else 302
    location = urljoin(request.url, url)
    res = HTTPResponse("", status=code, Location=location)
    if response._cookies:
        res._cookies = response._cookies
    raise res


def _file_iter_range(fp, offset, bytes, maxread=1024*1024):
    ''' Yield chunks from a range in a file. No chunk is bigger than maxread.'''
    fp.seek(offset)
    while bytes > 0:
        part = fp.read(min(bytes, maxread))
        if not part: break
        bytes -= len(part)
        yield part


def static_file(filename, root, mimetype='auto', download=False):
    """ Open a file in a safe way and return :exc:`HTTPResponse` with status
        code 200, 305, 401 or 404. Set Content-Type, Content-Encoding,
        Content-Length and Last-Modified header. Obey If-Modified-Since header
        and HEAD requests.
    """
    root = os.path.abspath(root) + os.sep
    filename = os.path.abspath(os.path.join(root, filename.strip('/\\')))
    headers = dict()

    if not filename.startswith(root):
        return HTTPError(403, "Access denied.")
    if not os.path.exists(filename) or not os.path.isfile(filename):
        return HTTPError(404, "File does not exist.")
    if not os.access(filename, os.R_OK):
        return HTTPError(403, "You do not have permission to access this file.")

    if mimetype == 'auto':
        mimetype, encoding = mimetypes.guess_type(filename)
        if mimetype: headers['Content-Type'] = mimetype
        if encoding: headers['Content-Encoding'] = encoding
    elif mimetype:
        headers['Content-Type'] = mimetype

    if download:
        download = os.path.basename(filename if download == True else download)
        headers['Content-Disposition'] = 'attachment; filename="%s"' % download

    stats = os.stat(filename)
    headers['Content-Length'] = clen = stats.st_size
    lm = time.strftime("%a, %d %b %Y %H:%M:%S GMT", time.gmtime(stats.st_mtime))
    headers['Last-Modified'] = lm

    ims = request.environ.get('HTTP_IF_MODIFIED_SINCE')
    if ims:
        ims = parse_date(ims.split(";")[0].strip())
    if ims is not None and ims >= int(stats.st_mtime):
        headers['Date'] = time.strftime("%a, %d %b %Y %H:%M:%S GMT", time.gmtime())
        return HTTPResponse(status=304, **headers)

    body = '' if request.method == 'HEAD' else open(filename, 'rb')

    headers["Accept-Ranges"] = "bytes"
    ranges = request.environ.get('HTTP_RANGE')
    if 'HTTP_RANGE' in request.environ:
        ranges = list(parse_range_header(request.environ['HTTP_RANGE'], clen))
        if not ranges:
            return HTTPError(416, "Requested Range Not Satisfiable")
        offset, end = ranges[0]
        headers["Content-Range"] = "bytes %d-%d/%d" % (offset, end-1, clen)
        headers["Content-Length"] = str(end-offset)
        if body: body = _file_iter_range(body, offset, end-offset)
        return HTTPResponse(body, status=206, **headers)
    return HTTPResponse(body, **headers)






###############################################################################
# HTTP Utilities and MISC (TODO) ###############################################
###############################################################################


def debug(mode=True):
    """ Change the debug level.
    There is only one debug level supported at the moment."""
    global DEBUG
    DEBUG = bool(mode)


def parse_date(ims):
    """ Parse rfc1123, rfc850 and asctime timestamps and return UTC epoch. """
    try:
        ts = email.utils.parsedate_tz(ims)
        return time.mktime(ts[:8] + (0,)) - (ts[9] or 0) - time.timezone
    except (TypeError, ValueError, IndexError, OverflowError):
        return None


def parse_auth(header):
    """ Parse rfc2617 HTTP authentication header string (basic) and return (user,pass) tuple or None"""
    try:
        method, data = header.split(None, 1)
        if method.lower() == 'basic':
            user, pwd = touni(base64.b64decode(tob(data))).split(':',1)
            return user, pwd
    except (KeyError, ValueError):
        return None

def parse_range_header(header, maxlen=0):
    ''' Yield (start, end) ranges parsed from a HTTP Range header. Skip
        unsatisfiable ranges. The end index is non-inclusive.'''
    if not header or header[:6] != 'bytes=': return
    ranges = [r.split('-', 1) for r in header[6:].split(',') if '-' in r]
    for start, end in ranges:
        try:
            if not start:  # bytes=-100    -> last 100 bytes
                start, end = max(0, maxlen-int(end)), maxlen
            elif not end:  # bytes=100-    -> all but the first 99 bytes
                start, end = int(start), maxlen
            else:          # bytes=100-200 -> bytes 100-200 (inclusive)
                start, end = int(start), min(int(end)+1, maxlen)
            if 0 <= start < end <= maxlen:
                yield start, end
        except ValueError:
            pass

def _parse_qsl(qs):
    r = []
    for pair in qs.replace(';','&').split('&'):
        if not pair: continue
        nv = pair.split('=', 1)
        if len(nv) != 2: nv.append('')
        key = urlunquote(nv[0].replace('+', ' '))
        value = urlunquote(nv[1].replace('+', ' '))
        r.append((key, value))
    return r

def _lscmp(a, b):
    ''' Compares two strings in a cryptographically safe way:
        Runtime is not affected by length of common prefix. '''
    return not sum(0 if x==y else 1 for x, y in zip(a, b)) and len(a) == len(b)


def cookie_encode(data, key):
    ''' Encode and sign a pickle-able object. Return a (byte) string '''
    msg = base64.b64encode(pickle.dumps(data, -1))
    sig = base64.b64encode(hmac.new(tob(key), msg).digest())
    return tob('!') + sig + tob('?') + msg


def cookie_decode(data, key):
    ''' Verify and decode an encoded string. Return an object or None.'''
    data = tob(data)
    if cookie_is_encoded(data):
        sig, msg = data.split(tob('?'), 1)
        if _lscmp(sig[1:], base64.b64encode(hmac.new(tob(key), msg).digest())):
            return pickle.loads(base64.b64decode(msg))
    return None


def cookie_is_encoded(data):
    ''' Return True if the argument looks like a encoded cookie.'''
    return bool(data.startswith(tob('!')) and tob('?') in data)


def html_escape(string):
    ''' Escape HTML special characters ``&<>`` and quotes ``'"``. '''
    return string.replace('&','&amp;').replace('<','&lt;').replace('>','&gt;')\
                 .replace('"','&quot;').replace("'",'&#039;')


def html_quote(string):
    ''' Escape and quote a string to be used as an HTTP attribute.'''
    return '"%s"' % html_escape(string).replace('\n','%#10;')\
                    .replace('\r','&#13;').replace('\t','&#9;')


def yieldroutes(func):
    """ Return a generator for routes that match the signature (name, args)
    of the func parameter. This may yield more than one route if the function
    takes optional keyword arguments. The output is best described by example::

        a()         -> '/a'
        b(x, y)     -> '/b/:x/:y'
        c(x, y=5)   -> '/c/:x' and '/c/:x/:y'
        d(x=5, y=6) -> '/d' and '/d/:x' and '/d/:x/:y'
    """
    import inspect # Expensive module. Only import if necessary.
    path = '/' + func.__name__.replace('__','/').lstrip('/')
    spec = inspect.getargspec(func)
    argc = len(spec[0]) - len(spec[3] or [])
    path += ('/:%s' * argc) % tuple(spec[0][:argc])
    yield path
    for arg in spec[0][argc:]:
        path += '/:%s' % arg
        yield path


def path_shift(script_name, path_info, shift=1):
    ''' Shift path fragments from PATH_INFO to SCRIPT_NAME and vice versa.

        :return: The modified paths.
        :param script_name: The SCRIPT_NAME path.
        :param script_name: The PATH_INFO path.
        :param shift: The number of path fragments to shift. May be negative to
          change the shift direction. (default: 1)
    '''
    if shift == 0: return script_name, path_info
    pathlist = path_info.strip('/').split('/')
    scriptlist = script_name.strip('/').split('/')
    if pathlist and pathlist[0] == '': pathlist = []
    if scriptlist and scriptlist[0] == '': scriptlist = []
    if shift > 0 and shift <= len(pathlist):
        moved = pathlist[:shift]
        scriptlist = scriptlist + moved
        pathlist = pathlist[shift:]
    elif shift < 0 and shift >= -len(scriptlist):
        moved = scriptlist[shift:]
        pathlist = moved + pathlist
        scriptlist = scriptlist[:shift]
    else:
        empty = 'SCRIPT_NAME' if shift < 0 else 'PATH_INFO'
        raise AssertionError("Cannot shift. Nothing left from %s" % empty)
    new_script_name = '/' + '/'.join(scriptlist)
    new_path_info = '/' + '/'.join(pathlist)
    if path_info.endswith('/') and pathlist: new_path_info += '/'
    return new_script_name, new_path_info


def validate(**vkargs):
    """
    Validates and manipulates keyword arguments by user defined callables.
    Handles ValueError and missing arguments by raising HTTPError(403).
    """
    depr('Use route wildcard filters instead.')
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kargs):
            for key, value in vkargs.items():
                if key not in kargs:
                    abort(403, 'Missing parameter: %s' % key)
                try:
                    kargs[key] = value(kargs[key])
                except ValueError:
                    abort(403, 'Wrong parameter format for: %s' % key)
            return func(*args, **kargs)
        return wrapper
    return decorator


def auth_basic(check, realm="private", text="Access denied"):
    ''' Callback decorator to require HTTP auth (basic).
        TODO: Add route(check_auth=...) parameter. '''
    def decorator(func):
      def wrapper(*a, **ka):
        user, password = request.auth or (None, None)
        if user is None or not check(user, password):
          response.headers['WWW-Authenticate'] = 'Basic realm="%s"' % realm
          return HTTPError(401, text)
        return func(*a, **ka)
      return wrapper
    return decorator


# Shortcuts for common Bottle methods.
# They all refer to the current default application.

def make_default_app_wrapper(name):
    ''' Return a callable that relays calls to the current default app. '''
    @functools.wraps(getattr(Bottle, name))
    def wrapper(*a, **ka):
        return getattr(app(), name)(*a, **ka)
    return wrapper

route     = make_default_app_wrapper('route')
get       = make_default_app_wrapper('get')
post      = make_default_app_wrapper('post')
put       = make_default_app_wrapper('put')
delete    = make_default_app_wrapper('delete')
error     = make_default_app_wrapper('error')
mount     = make_default_app_wrapper('mount')
hook      = make_default_app_wrapper('hook')
install   = make_default_app_wrapper('install')
uninstall = make_default_app_wrapper('uninstall')
url       = make_default_app_wrapper('get_url')







###############################################################################
# Server Adapter ###############################################################
###############################################################################


class ServerAdapter(object):
    quiet = False
    def __init__(self, host='127.0.0.1', port=8080, **config):
        self.options = config
        self.host = host
        self.port = int(port)

    def run(self, handler): # pragma: no cover
        pass

    def __repr__(self):
        args = ', '.join(['%s=%s'%(k,repr(v)) for k, v in self.options.items()])
        return "%s(%s)" % (self.__class__.__name__, args)


class CGIServer(ServerAdapter):
    quiet = True
    def run(self, handler): # pragma: no cover
        from wsgiref.handlers import CGIHandler
        def fixed_environ(environ, start_response):
            environ.setdefault('PATH_INFO', '')
            return handler(environ, start_response)
        CGIHandler().run(fixed_environ)


class FlupFCGIServer(ServerAdapter):
    def run(self, handler): # pragma: no cover
        import flup.server.fcgi
        self.options.setdefault('bindAddress', (self.host, self.port))
        flup.server.fcgi.WSGIServer(handler, **self.options).run()


class WSGIRefServer(ServerAdapter):
    def run(self, handler): # pragma: no cover
        from wsgiref.simple_server import make_server, WSGIRequestHandler
        if self.quiet:
            class QuietHandler(WSGIRequestHandler):
                def log_request(*args, **kw): pass
            self.options['handler_class'] = QuietHandler
        srv = make_server(self.host, self.port, handler, **self.options)
        srv.serve_forever()


class CherryPyServer(ServerAdapter):
    def run(self, handler): # pragma: no cover
        from cherrypy import wsgiserver
        server = wsgiserver.CherryPyWSGIServer((self.host, self.port), handler)
        try:
            server.start()
        finally:
            server.stop()


class WaitressServer(ServerAdapter):
    def run(self, handler):
        from waitress import serve
        serve(handler, host=self.host, port=self.port)


class PasteServer(ServerAdapter):
    def run(self, handler): # pragma: no cover
        from paste import httpserver
        if not self.quiet:
            from paste.translogger import TransLogger
            handler = TransLogger(handler)
        httpserver.serve(handler, host=self.host, port=str(self.port),
                         **self.options)


class MeinheldServer(ServerAdapter):
    def run(self, handler):
        from meinheld import server
        server.listen((self.host, self.port))
        server.run(handler)


class FapwsServer(ServerAdapter):
    """ Extremely fast webserver using libev. See http://www.fapws.org/ """
    def run(self, handler): # pragma: no cover
        import fapws._evwsgi as evwsgi
        from fapws import base, config
        port = self.port
        if float(config.SERVER_IDENT[-2:]) > 0.4:
            # fapws3 silently changed its API in 0.5
            port = str(port)
        evwsgi.start(self.host, port)
        # fapws3 never releases the GIL. Complain upstream. I tried. No luck.
        if 'BOTTLE_CHILD' in os.environ and not self.quiet:
            _stderr("WARNING: Auto-reloading does not work with Fapws3.\n")
            _stderr("         (Fapws3 breaks python thread support)\n")
        evwsgi.set_base_module(base)
        def app(environ, start_response):
            environ['wsgi.multiprocess'] = False
            return handler(environ, start_response)
        evwsgi.wsgi_cb(('', app))
        evwsgi.run()


class TornadoServer(ServerAdapter):
    """ The super hyped asynchronous server by facebook. Untested. """
    def run(self, handler): # pragma: no cover
        import tornado.wsgi, tornado.httpserver, tornado.ioloop
        container = tornado.wsgi.WSGIContainer(handler)
        server = tornado.httpserver.HTTPServer(container)
        server.listen(port=self.port)
        tornado.ioloop.IOLoop.instance().start()


class AppEngineServer(ServerAdapter):
    """ Adapter for Google App Engine. """
    quiet = True
    def run(self, handler):
        from google.appengine.ext.webapp import util
        # A main() function in the handler script enables 'App Caching'.
        # Lets makes sure it is there. This _really_ improves performance.
        module = sys.modules.get('__main__')
        if module and not hasattr(module, 'main'):
            module.main = lambda: util.run_wsgi_app(handler)
        util.run_wsgi_app(handler)


class TwistedServer(ServerAdapter):
    """ Untested. """
    def run(self, handler):
        from twisted.web import server, wsgi
        from twisted.python.threadpool import ThreadPool
        from twisted.internet import reactor
        thread_pool = ThreadPool()
        thread_pool.start()
        reactor.addSystemEventTrigger('after', 'shutdown', thread_pool.stop)
        factory = server.Site(wsgi.WSGIResource(reactor, thread_pool, handler))
        reactor.listenTCP(self.port, factory, interface=self.host)
        reactor.run()


class DieselServer(ServerAdapter):
    """ Untested. """
    def run(self, handler):
        from diesel.protocols.wsgi import WSGIApplication
        app = WSGIApplication(handler, port=self.port)
        app.run()


class GeventServer(ServerAdapter):
    """ Untested. Options:

        * `fast` (default: False) uses libevent's http server, but has some
          issues: No streaming, no pipelining, no SSL.
    """
    def run(self, handler):
        from gevent import wsgi, pywsgi, local
        if not isinstance(_lctx, local.local):
            msg = "Bottle requires gevent.monkey.patch_all() (before import)"
            raise RuntimeError(msg)
        if not self.options.get('fast'): wsgi = pywsgi
        log = None if self.quiet else 'default'
        wsgi.WSGIServer((self.host, self.port), handler, log=log).serve_forever()


class GunicornServer(ServerAdapter):
    """ Untested. See http://gunicorn.org/configure.html for options. """
    def run(self, handler):
        from gunicorn.app.base import Application

        config = {'bind': "%s:%d" % (self.host, int(self.port))}
        config.update(self.options)

        class GunicornApplication(Application):
            def init(self, parser, opts, args):
                return config

            def load(self):
                return handler

        GunicornApplication().run()


class EventletServer(ServerAdapter):
    """ Untested """
    def run(self, handler):
        from eventlet import wsgi, listen
        try:
            wsgi.server(listen((self.host, self.port)), handler,
                        log_output=(not self.quiet))
        except TypeError:
            # Fallback, if we have old version of eventlet
            wsgi.server(listen((self.host, self.port)), handler)


class RocketServer(ServerAdapter):
    """ Untested. """
    def run(self, handler):
        from rocket import Rocket
        server = Rocket((self.host, self.port), 'wsgi', { 'wsgi_app' : handler })
        server.start()


class BjoernServer(ServerAdapter):
    """ Fast server written in C: https://github.com/jonashaag/bjoern """
    def run(self, handler):
        from bjoern import run
        run(handler, self.host, self.port)


class AutoServer(ServerAdapter):
    """ Untested. """
    adapters = [WaitressServer, PasteServer, TwistedServer, CherryPyServer, WSGIRefServer]
    def run(self, handler):
        for sa in self.adapters:
            try:
                return sa(self.host, self.port, **self.options).run(handler)
            except ImportError:
                pass

server_names = {
    'cgi': CGIServer,
    'flup': FlupFCGIServer,
    'wsgiref': WSGIRefServer,
    'waitress': WaitressServer,
    'cherrypy': CherryPyServer,
    'paste': PasteServer,
    'fapws3': FapwsServer,
    'tornado': TornadoServer,
    'gae': AppEngineServer,
    'twisted': TwistedServer,
    'diesel': DieselServer,
    'meinheld': MeinheldServer,
    'gunicorn': GunicornServer,
    'eventlet': EventletServer,
    'gevent': GeventServer,
    'rocket': RocketServer,
    'bjoern' : BjoernServer,
    'auto': AutoServer,
}






###############################################################################
# Application Control ##########################################################
###############################################################################


def load(target, **namespace):
    """ Import a module or fetch an object from a module.

        * ``package.module`` returns `module` as a module object.
        * ``pack.mod:name`` returns the module variable `name` from `pack.mod`.
        * ``pack.mod:func()`` calls `pack.mod.func()` and returns the result.

        The last form accepts not only function calls, but any type of
        expression. Keyword arguments passed to this function are available as
        local variables. Example: ``import_string('re:compile(x)', x='[a-z]')``
    """
    module, target = target.split(":", 1) if ':' in target else (target, None)
    if module not in sys.modules: __import__(module)
    if not target: return sys.modules[module]
    if target.isalnum(): return getattr(sys.modules[module], target)
    package_name = module.split('.')[0]
    namespace[package_name] = sys.modules[package_name]
    return eval('%s.%s' % (module, target), namespace)


def load_app(target):
    """ Load a bottle application from a module and make sure that the import
        does not affect the current default application, but returns a separate
        application object. See :func:`load` for the target parameter. """
    global NORUN; NORUN, nr_old = True, NORUN
    try:
        tmp = default_app.push() # Create a new "default application"
        rv = load(target) # Import the target module
        return rv if callable(rv) else tmp
    finally:
        default_app.remove(tmp) # Remove the temporary added default application
        NORUN = nr_old

_debug = debug
def run(app=None, server='wsgiref', host='127.0.0.1', port=8080,
        interval=1, reloader=False, quiet=False, plugins=None,
        debug=False, **kargs):
    """ Start a server instance. This method blocks until the server terminates.

        :param app: WSGI application or target string supported by
               :func:`load_app`. (default: :func:`default_app`)
        :param server: Server adapter to use. See :data:`server_names` keys
               for valid names or pass a :class:`ServerAdapter` subclass.
               (default: `wsgiref`)
        :param host: Server address to bind to. Pass ``0.0.0.0`` to listens on
               all interfaces including the external one. (default: 127.0.0.1)
        :param port: Server port to bind to. Values below 1024 require root
               privileges. (default: 8080)
        :param reloader: Start auto-reloading server? (default: False)
        :param interval: Auto-reloader interval in seconds (default: 1)
        :param quiet: Suppress output to stdout and stderr? (default: False)
        :param options: Options passed to the server adapter.
     """
    if NORUN: return
    if reloader and not os.environ.get('BOTTLE_CHILD'):
        try:
            lockfile = None
            fd, lockfile = tempfile.mkstemp(prefix='bottle.', suffix='.lock')
            os.close(fd) # We only need this file to exist. We never write to it
            while os.path.exists(lockfile):
                args = [sys.executable] + sys.argv
                environ = os.environ.copy()
                environ['BOTTLE_CHILD'] = 'true'
                environ['BOTTLE_LOCKFILE'] = lockfile
                p = subprocess.Popen(args, env=environ)
                while p.poll() is None: # Busy wait...
                    os.utime(lockfile, None) # I am alive!
                    time.sleep(interval)
                if p.poll() != 3:
                    if os.path.exists(lockfile): os.unlink(lockfile)
                    sys.exit(p.poll())
        except KeyboardInterrupt:
            pass
        finally:
            if os.path.exists(lockfile):
                os.unlink(lockfile)
        return

    try:
        _debug(debug)
        app = app or default_app()
        if isinstance(app, basestring):
            app = load_app(app)
        if not callable(app):
            raise ValueError("Application is not callable: %r" % app)

        for plugin in plugins or []:
            app.install(plugin)

        if server in server_names:
            server = server_names.get(server)
        if isinstance(server, basestring):
            server = load(server)
        if isinstance(server, type):
            server = server(host=host, port=port, **kargs)
        if not isinstance(server, ServerAdapter):
            raise ValueError("Unknown or unsupported server: %r" % server)

        server.quiet = server.quiet or quiet
        if not server.quiet:
            _stderr("Bottle v%s server starting up (using %s)...\n" % (__version__, repr(server)))
            _stderr("Listening on http://%s:%d/\n" % (server.host, server.port))
            _stderr("Hit Ctrl-C to quit.\n\n")

        if reloader:
            lockfile = os.environ.get('BOTTLE_LOCKFILE')
            bgcheck = FileCheckerThread(lockfile, interval)
            with bgcheck:
                server.run(app)
            if bgcheck.status == 'reload':
                sys.exit(3)
        else:
            server.run(app)
    except KeyboardInterrupt:
        pass
    except (SystemExit, MemoryError):
        raise
    except:
        if not reloader: raise
        if not getattr(server, 'quiet', quiet):
            print_exc()
        time.sleep(interval)
        sys.exit(3)



class FileCheckerThread(threading.Thread):
    ''' Interrupt main-thread as soon as a changed module file is detected,
        the lockfile gets deleted or gets to old. '''

    def __init__(self, lockfile, interval):
        threading.Thread.__init__(self)
        self.lockfile, self.interval = lockfile, interval
        #: Is one of 'reload', 'error' or 'exit'
        self.status = None

    def run(self):
        exists = os.path.exists
        mtime = lambda path: os.stat(path).st_mtime
        files = dict()

        for module in list(sys.modules.values()):
            path = getattr(module, '__file__', '')
            if path[-4:] in ('.pyo', '.pyc'): path = path[:-1]
            if path and exists(path): files[path] = mtime(path)

        while not self.status:
            if not exists(self.lockfile)\
            or mtime(self.lockfile) < time.time() - self.interval - 5:
                self.status = 'error'
                thread.interrupt_main()
            for path, lmtime in list(files.items()):
                if not exists(path) or mtime(path) > lmtime:
                    self.status = 'reload'
                    thread.interrupt_main()
                    break
            time.sleep(self.interval)

    def __enter__(self):
        self.start()

    def __exit__(self, exc_type, exc_val, exc_tb):
        if not self.status: self.status = 'exit' # silent exit
        self.join()
        return exc_type is not None and issubclass(exc_type, KeyboardInterrupt)





###############################################################################
# Template Adapters ############################################################
###############################################################################


class TemplateError(HTTPError):
    def __init__(self, message):
        HTTPError.__init__(self, 500, message)


class BaseTemplate(object):
    """ Base class and minimal API for template adapters """
    extensions = ['tpl','html','thtml','stpl']
    settings = {} #used in prepare()
    defaults = {} #used in render()

    def __init__(self, source=None, name=None, lookup=[], encoding='utf8', **settings):
        """ Create a new template.
        If the source parameter (str or buffer) is missing, the name argument
        is used to guess a template filename. Subclasses can assume that
        self.source and/or self.filename are set. Both are strings.
        The lookup, encoding and settings parameters are stored as instance
        variables.
        The lookup parameter stores a list containing directory paths.
        The encoding parameter should be used to decode byte strings or files.
        The settings parameter contains a dict for engine-specific settings.
        """
        self.name = name
        self.source = source.read() if hasattr(source, 'read') else source
        self.filename = source.filename if hasattr(source, 'filename') else None
        self.lookup = [os.path.abspath(x) for x in lookup]
        self.encoding = encoding
        self.settings = self.settings.copy() # Copy from class variable
        self.settings.update(settings) # Apply
        if not self.source and self.name:
            self.filename = self.search(self.name, self.lookup)
            if not self.filename:
                raise TemplateError('Template %s not found.' % repr(name))
        if not self.source and not self.filename:
            raise TemplateError('No template specified.')
        self.prepare(**self.settings)

    @classmethod
    def search(cls, name, lookup=[]):
        """ Search name in all directories specified in lookup.
        First without, then with common extensions. Return first hit. """
        if not lookup:
            depr('The template lookup path list should not be empty.')
            lookup = ['.']

        if os.path.isabs(name) and os.path.isfile(name):
            depr('Absolute template path names are deprecated.')
            return os.path.abspath(name)

        for spath in lookup:
            spath = os.path.abspath(spath) + os.sep
            fname = os.path.abspath(os.path.join(spath, name))
            if not fname.startswith(spath): continue
            if os.path.isfile(fname): return fname
            for ext in cls.extensions:
                if os.path.isfile('%s.%s' % (fname, ext)):
                    return '%s.%s' % (fname, ext)

    @classmethod
    def global_config(cls, key, *args):
        ''' This reads or sets the global settings stored in class.settings. '''
        if args:
            cls.settings = cls.settings.copy() # Make settings local to class
            cls.settings[key] = args[0]
        else:
            return cls.settings[key]

    def prepare(self, **options):
        """ Run preparations (parsing, caching, ...).
        It should be possible to call this again to refresh a template or to
        update settings.
        """
        raise NotImplementedError

    def render(self, *args, **kwargs):
        """ Render the template with the specified local variables and return
        a single byte or unicode string. If it is a byte string, the encoding
        must match self.encoding. This method must be thread-safe!
        Local variables may be provided in dictionaries (*args)
        or directly, as keywords (**kwargs).
        """
        raise NotImplementedError


class MakoTemplate(BaseTemplate):
    def prepare(self, **options):
        from mako.template import Template
        from mako.lookup import TemplateLookup
        options.update({'input_encoding':self.encoding})
        options.setdefault('format_exceptions', bool(DEBUG))
        lookup = TemplateLookup(directories=self.lookup, **options)
        if self.source:
            self.tpl = Template(self.source, lookup=lookup, **options)
        else:
            self.tpl = Template(uri=self.name, filename=self.filename, lookup=lookup, **options)

    def render(self, *args, **kwargs):
        for dictarg in args: kwargs.update(dictarg)
        _defaults = self.defaults.copy()
        _defaults.update(kwargs)
        return self.tpl.render(**_defaults)


class CheetahTemplate(BaseTemplate):
    def prepare(self, **options):
        from Cheetah.Template import Template
        self.context = threading.local()
        self.context.vars = {}
        options['searchList'] = [self.context.vars]
        if self.source:
            self.tpl = Template(source=self.source, **options)
        else:
            self.tpl = Template(file=self.filename, **options)

    def render(self, *args, **kwargs):
        for dictarg in args: kwargs.update(dictarg)
        self.context.vars.update(self.defaults)
        self.context.vars.update(kwargs)
        out = str(self.tpl)
        self.context.vars.clear()
        return out


class Jinja2Template(BaseTemplate):
    def prepare(self, filters=None, tests=None, **kwargs):
        from jinja2 import Environment, FunctionLoader
        if 'prefix' in kwargs: # TODO: to be removed after a while
            raise RuntimeError('The keyword argument `prefix` has been removed. '
                'Use the full jinja2 environment name line_statement_prefix instead.')
        self.env = Environment(loader=FunctionLoader(self.loader), **kwargs)
        if filters: self.env.filters.update(filters)
        if tests: self.env.tests.update(tests)
        if self.source:
            self.tpl = self.env.from_string(self.source)
        else:
            self.tpl = self.env.get_template(self.filename)

    def render(self, *args, **kwargs):
        for dictarg in args: kwargs.update(dictarg)
        _defaults = self.defaults.copy()
        _defaults.update(kwargs)
        return self.tpl.render(**_defaults)

    def loader(self, name):
        fname = self.search(name, self.lookup)
        if not fname: return
        with open(fname, "rb") as f:
            return f.read().decode(self.encoding)


class SimpleTALTemplate(BaseTemplate):
    ''' Deprecated, do not use. '''
    def prepare(self, **options):
        depr('The SimpleTAL template handler is deprecated'\
             ' and will be removed in 0.12')
        from simpletal import simpleTAL
        if self.source:
            self.tpl = simpleTAL.compileHTMLTemplate(self.source)
        else:
            with open(self.filename, 'rb') as fp:
                self.tpl = simpleTAL.compileHTMLTemplate(tonat(fp.read()))

    def render(self, *args, **kwargs):
        from simpletal import simpleTALES
        for dictarg in args: kwargs.update(dictarg)
        context = simpleTALES.Context()
        for k,v in self.defaults.items():
            context.addGlobal(k, v)
        for k,v in kwargs.items():
            context.addGlobal(k, v)
        output = StringIO()
        self.tpl.expand(context, output)
        return output.getvalue()


class SimpleTemplate(BaseTemplate):
    blocks = ('if', 'elif', 'else', 'try', 'except', 'finally', 'for', 'while',
              'with', 'def', 'class')
    dedent_blocks = ('elif', 'else', 'except', 'finally')

    @lazy_attribute
    def re_pytokens(cls):
        ''' This matches comments and all kinds of quoted strings but does
            NOT match comments (#...) within quoted strings. (trust me) '''
        return re.compile(r'''
            (''(?!')|""(?!")|'{6}|"{6}    # Empty strings (all 4 types)
             |'(?:[^\\']|\\.)+?'          # Single quotes (')
             |"(?:[^\\"]|\\.)+?"          # Double quotes (")
             |'{3}(?:[^\\]|\\.|\n)+?'{3}  # Triple-quoted strings (')
             |"{3}(?:[^\\]|\\.|\n)+?"{3}  # Triple-quoted strings (")
             |\#.*                        # Comments
            )''', re.VERBOSE)

    def prepare(self, escape_func=html_escape, noescape=False, **kwargs):
        self.cache = {}
        enc = self.encoding
        self._str = lambda x: touni(x, enc)
        self._escape = lambda x: escape_func(touni(x, enc))
        if noescape:
            self._str, self._escape = self._escape, self._str

    @classmethod
    def split_comment(cls, code):
        """ Removes comments (#...) from python code. """
        if '#' not in code: return code
        #: Remove comments only (leave quoted strings as they are)
        subf = lambda m: '' if m.group(0)[0]=='#' else m.group(0)
        return re.sub(cls.re_pytokens, subf, code)

    @cached_property
    def co(self):
        return compile(self.code, self.filename or '<string>', 'exec')

    @cached_property
    def code(self):
        stack = [] # Current Code indentation
        lineno = 0 # Current line of code
        ptrbuffer = [] # Buffer for printable strings and token tuple instances
        codebuffer = [] # Buffer for generated python code
        multiline = dedent = oneline = False
        template = self.source or open(self.filename, 'rb').read()

        def yield_tokens(line):
            for i, part in enumerate(re.split(r'\{\{(.*?)\}\}', line)):
                if i % 2:
                    if part.startswith('!'): yield 'RAW', part[1:]
                    else: yield 'CMD', part
                else: yield 'TXT', part

        def flush(): # Flush the ptrbuffer
            if not ptrbuffer: return
            cline = ''
            for line in ptrbuffer:
                for token, value in line:
                    if token == 'TXT': cline += repr(value)
                    elif token == 'RAW': cline += '_str(%s)' % value
                    elif token == 'CMD': cline += '_escape(%s)' % value
                    cline +=  ', '
                cline = cline[:-2] + '\\\n'
            cline = cline[:-2]
            if cline[:-1].endswith('\\\\\\\\\\n'):
                cline = cline[:-7] + cline[-1] # 'nobr\\\\\n' --> 'nobr'
            cline = '_printlist([' + cline + '])'
            del ptrbuffer[:] # Do this before calling code() again
            code(cline)

        def code(stmt):
            for line in stmt.splitlines():
                codebuffer.append('  ' * len(stack) + line.strip())

        for line in template.splitlines(True):
            lineno += 1
            line = touni(line, self.encoding)
            sline = line.lstrip()
            if lineno <= 2:
                m = re.match(r"%\s*#.*coding[:=]\s*([-\w.]+)", sline)
                if m: self.encoding = m.group(1)
                if m: line = line.replace('coding','coding (removed)')
            if sline and sline[0] == '%' and sline[:2] != '%%':
                line = line.split('%',1)[1].lstrip() # Full line following the %
                cline = self.split_comment(line).strip()
                cmd = re.split(r'[^a-zA-Z0-9_]', cline)[0]
                flush() # You are actually reading this? Good luck, it's a mess :)
                if cmd in self.blocks or multiline:
                    cmd = multiline or cmd
                    dedent = cmd in self.dedent_blocks # "else:"
                    if dedent and not oneline and not multiline:
                        cmd = stack.pop()
                    code(line)
                    oneline = not cline.endswith(':') # "if 1: pass"
                    multiline = cmd if cline.endswith('\\') else False
                    if not oneline and not multiline:
                        stack.append(cmd)
                elif cmd == 'end' and stack:
                    code('#end(%s) %s' % (stack.pop(), line.strip()[3:]))
                elif cmd == 'include':
                    p = cline.split(None, 2)[1:]
                    if len(p) == 2:
                        code("_=_include(%s, _stdout, %s)" % (repr(p[0]), p[1]))
                    elif p:
                        code("_=_include(%s, _stdout)" % repr(p[0]))
                    else: # Empty %include -> reverse of %rebase
                        code("_printlist(_base)")
                elif cmd == 'rebase':
                    p = cline.split(None, 2)[1:]
                    if len(p) == 2:
                        code("globals()['_rebase']=(%s, dict(%s))" % (repr(p[0]), p[1]))
                    elif p:
                        code("globals()['_rebase']=(%s, {})" % repr(p[0]))
                else:
                    code(line)
            else: # Line starting with text (not '%') or '%%' (escaped)
                if line.strip().startswith('%%'):
                    line = line.replace('%%', '%', 1)
                ptrbuffer.append(yield_tokens(line))
        flush()
        return '\n'.join(codebuffer) + '\n'

    def subtemplate(self, _name, _stdout, *args, **kwargs):
        for dictarg in args: kwargs.update(dictarg)
        if _name not in self.cache:
            self.cache[_name] = self.__class__(name=_name, lookup=self.lookup)
        return self.cache[_name].execute(_stdout, kwargs)

    def execute(self, _stdout, *args, **kwargs):
        for dictarg in args: kwargs.update(dictarg)
        env = self.defaults.copy()
        env.update({'_stdout': _stdout, '_printlist': _stdout.extend,
               '_include': self.subtemplate, '_str': self._str,
               '_escape': self._escape, 'get': env.get,
               'setdefault': env.setdefault, 'defined': env.__contains__})
        env.update(kwargs)
        eval(self.co, env)
        if '_rebase' in env:
            subtpl, rargs = env['_rebase']
            rargs['_base'] = _stdout[:] #copy stdout
            del _stdout[:] # clear stdout
            return self.subtemplate(subtpl,_stdout,rargs)
        return env

    def render(self, *args, **kwargs):
        """ Render the template using keyword arguments as local variables. """
        for dictarg in args: kwargs.update(dictarg)
        stdout = []
        self.execute(stdout, kwargs)
        return ''.join(stdout)


def template(*args, **kwargs):
    '''
    Get a rendered template as a string iterator.
    You can use a name, a filename or a template string as first parameter.
    Template rendering arguments can be passed as dictionaries
    or directly (as keyword arguments).
    '''
    tpl = args[0] if args else None
    adapter = kwargs.pop('template_adapter', SimpleTemplate)
    lookup = kwargs.pop('template_lookup', TEMPLATE_PATH)
    tplid = (id(lookup), tpl)
    if tplid not in TEMPLATES or DEBUG:
        settings = kwargs.pop('template_settings', {})
        if isinstance(tpl, adapter):
            TEMPLATES[tplid] = tpl
            if settings: TEMPLATES[tplid].prepare(**settings)
        elif "\n" in tpl or "{" in tpl or "%" in tpl or '$' in tpl:
            TEMPLATES[tplid] = adapter(source=tpl, lookup=lookup, **settings)
        else:
            TEMPLATES[tplid] = adapter(name=tpl, lookup=lookup, **settings)
    if not TEMPLATES[tplid]:
        abort(500, 'Template (%s) not found' % tpl)
    for dictarg in args[1:]: kwargs.update(dictarg)
    return TEMPLATES[tplid].render(kwargs)

mako_template = functools.partial(template, template_adapter=MakoTemplate)
cheetah_template = functools.partial(template, template_adapter=CheetahTemplate)
jinja2_template = functools.partial(template, template_adapter=Jinja2Template)
simpletal_template = functools.partial(template, template_adapter=SimpleTALTemplate)


def view(tpl_name, **defaults):
    ''' Decorator: renders a template for a handler.
        The handler can control its behavior like that:

          - return a dict of template vars to fill out the template
          - return something other than a dict and the view decorator will not
            process the template, but return the handler result as is.
            This includes returning a HTTPResponse(dict) to get,
            for instance, JSON with autojson or other castfilters.
    '''
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            result = func(*args, **kwargs)
            if isinstance(result, (dict, DictMixin)):
                tplvars = defaults.copy()
                tplvars.update(result)
                return template(tpl_name, **tplvars)
            return result
        return wrapper
    return decorator

mako_view = functools.partial(view, template_adapter=MakoTemplate)
cheetah_view = functools.partial(view, template_adapter=CheetahTemplate)
jinja2_view = functools.partial(view, template_adapter=Jinja2Template)
simpletal_view = functools.partial(view, template_adapter=SimpleTALTemplate)






###############################################################################
# Constants and Globals ########################################################
###############################################################################


TEMPLATE_PATH = ['./', './views/']
TEMPLATES = {}
DEBUG = False
NORUN = False # If set, run() does nothing. Used by load_app()

#: A dict to map HTTP status codes (e.g. 404) to phrases (e.g. 'Not Found')
HTTP_CODES = httplib.responses
HTTP_CODES[418] = "I'm a teapot" # RFC 2324
HTTP_CODES[428] = "Precondition Required"
HTTP_CODES[429] = "Too Many Requests"
HTTP_CODES[431] = "Request Header Fields Too Large"
HTTP_CODES[511] = "Network Authentication Required"
_HTTP_STATUS_LINES = dict((k, '%d %s'%(k,v)) for (k,v) in HTTP_CODES.items())

#: The default template used for error pages. Override with @error()
ERROR_PAGE_TEMPLATE = """
%%try:
    %%from %s import DEBUG, HTTP_CODES, request, touni
    <!DOCTYPE HTML PUBLIC "-//IETF//DTD HTML 2.0//EN">
    <html>
        <head>
            <title>Error: {{e.status}}</title>
            <style type="text/css">
              html {background-color: #eee; font-family: sans;}
              body {background-color: #fff; border: 1px solid #ddd;
                    padding: 15px; margin: 15px;}
              pre {background-color: #eee; border: 1px solid #ddd; padding: 5px;}
            </style>
        </head>
        <body>
            <h1>Error: {{e.status}}</h1>
            <p>Sorry, the requested URL <tt>{{repr(request.url)}}</tt>
               caused an error:</p>
            <pre>{{e.body}}</pre>
            %%if DEBUG and e.exception:
              <h2>Exception:</h2>
              <pre>{{repr(e.exception)}}</pre>
            %%end
            %%if DEBUG and e.traceback:
              <h2>Traceback:</h2>
              <pre>{{e.traceback}}</pre>
            %%end
        </body>
    </html>
%%except ImportError:
    <b>ImportError:</b> Could not generate the error page. Please add bottle to
    the import path.
%%end
""" % __name__

#: A thread-safe instance of :class:`LocalRequest`. If accessed from within a
#: request callback, this instance always refers to the *current* request
#: (even on a multithreaded server).
request = LocalRequest()

#: A thread-safe instance of :class:`LocalResponse`. It is used to change the
#: HTTP response for the *current* request.
response = LocalResponse()

#: A thread-safe namespace. Not used by Bottle.
local = threading.local()

# Initialize app stack (create first empty Bottle app)
# BC: 0.6.4 and needed for run()
app = default_app = AppStack()
app.push()

#: A virtual package that redirects import statements.
#: Example: ``import bottle.ext.sqlite`` actually imports `bottle_sqlite`.
ext = _ImportRedirect('bottle.ext' if __name__ == '__main__' else __name__+".ext", 'bottle_%s').module

if __name__ == '__main__':
    opt, args, parser = _cmd_options, _cmd_args, _cmd_parser
    if opt.version:
        _stdout('Bottle %s\n'%__version__)
        sys.exit(0)
    if not args:
        parser.print_help()
        _stderr('\nError: No application specified.\n')
        sys.exit(1)

    sys.path.insert(0, '.')
    sys.modules.setdefault('bottle', sys.modules['__main__'])

    host, port = (opt.bind or 'localhost'), 8080
    if ':' in host:
        host, port = host.rsplit(':', 1)

    run(args[0], host=host, port=port, server=opt.server,
        reloader=opt.reload, plugins=opt.plugin, debug=opt.debug)




# THE END

########NEW FILE########
__FILENAME__ = bottle_sqlite
'''
Bottle-sqlite is a plugin that integrates SQLite3 with your Bottle
application. It automatically connects to a database at the beginning of a
request, passes the database handle to the route callback and closes the
connection afterwards.

To automatically detect routes that need a database connection, the plugin
searches for route callbacks that require a `db` keyword argument
(configurable) and skips routes that do not. This removes any overhead for
routes that don't need a database connection.

Usage Example::

    import bottle
    from bottle.ext import sqlite

    app = bottle.Bottle()
    plugin = sqlite.Plugin(dbfile='/tmp/test.db')
    app.install(plugin)

    @app.route('/show/:item')
    def show(item, db):
        row = db.execute('SELECT * from items where name=?', item).fetchone()
        if row:
            return template('showitem', page=row)
        return HTTPError(404, "Page not found")
'''

__author__ = "Marcel Hellkamp"
__version__ = '0.1.2'
__license__ = 'MIT'

### CUT HERE (see setup.py)

import sqlite3
import inspect
from bottle import HTTPResponse, HTTPError


class SQLitePlugin(object):
    ''' This plugin passes an sqlite3 database handle to route callbacks
    that accept a `db` keyword argument. If a callback does not expect
    such a parameter, no connection is made. You can override the database
    settings on a per-route basis. '''

    name = 'sqlite'

    def __init__(self, dbfile=':memory:', autocommit=True, dictrows=True,
                 keyword='db'):
         self.dbfile = dbfile
         self.autocommit = autocommit
         self.dictrows = dictrows
         self.keyword = keyword

    def setup(self, app):
        ''' Make sure that other installed plugins don't affect the same
            keyword argument.'''
        for other in app.plugins:
            if not isinstance(other, SQLitePlugin): continue
            if other.keyword == self.keyword:
                raise PluginError("Found another sqlite plugin with "\
                "conflicting settings (non-unique keyword).")

    def apply(self, callback, context):
        # Override global configuration with route-specific values.
        conf = context['config'].get('sqlite') or {}
        dbfile = conf.get('dbfile', self.dbfile)
        autocommit = conf.get('autocommit', self.autocommit)
        dictrows = conf.get('dictrows', self.dictrows)
        keyword = conf.get('keyword', self.keyword)

        # Test if the original callback accepts a 'db' keyword.
        # Ignore it if it does not need a database handle.
        args = inspect.getargspec(context['callback'])[0]
        if keyword not in args:
            return callback

        def wrapper(*args, **kwargs):
            # Connect to the database
            db = sqlite3.connect(dbfile)
            # This enables column access by name: row['column_name']
            if dictrows: db.row_factory = sqlite3.Row
            # Add the connection handle as a keyword argument.
            kwargs[keyword] = db

            try:
                rv = callback(*args, **kwargs)
                if autocommit: db.commit()
            except sqlite3.IntegrityError, e:
                db.rollback()
                raise HTTPError(500, "Database Error", e)
            except HTTPError, e:
                raise
            except HTTPResponse, e:
                if autocommit: db.commit()
                raise
            finally:
                db.close()
            return rv

        # Replace the route callback with the wrapped one.
        return wrapper

Plugin = SQLitePlugin
########NEW FILE########
__FILENAME__ = google_auth
"""Handle validating that a client is verified"""
from __future__ import print_function
from bottle import request, HTTPError
from httplib2 import Http
import json


def validate_token(access_token):
    '''Verifies that an access-token is valid and
    meant for this app.

    Returns None on fail, and an e-mail on success'''
    h = Http()
    resp, cont = h.request("https://www.googleapis.com/oauth2/v2/userinfo",
                           headers={'Host':'www.googleapis.com',
                                    'Authorization':access_token})

    if not resp['status'] == '200':
        return None

    data = json.loads(cont)

    return data['email']

def gauth(fn):
    """Decorator that checks Bottle requests to
    contain an id-token in the request header.
    userid will be None if the
    authentication failed, and have an id otherwise.

    Use like so:
    bottle.install(guath)"""

    def _wrap(*args, **kwargs):
        if 'Authorization' not in request.headers:
            return HTTPError(401, 'Unauthorized')

        userid = validate_token(request.headers['Authorization'])
        if userid is None:
            return HTTPError(401, "Unauthorized")

        return fn(userid=userid, *args, **kwargs)
    return _wrap

########NEW FILE########
