__FILENAME__ = discovery
# Copyright (C) 2010 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Client for discovery based APIs

A client library for Google's discovery based APIs.
"""

__author__ = 'jcgregorio@google.com (Joe Gregorio)'
__all__ = [
    'build', 'build_from_document'
    ]

import copy
import httplib2
import logging
import os
import random
import re
import uritemplate
import urllib
import urlparse
import mimeparse
import mimetypes

try:
    from urlparse import parse_qsl
except ImportError:
    from cgi import parse_qsl

from apiclient.errors import HttpError
from apiclient.errors import InvalidJsonError
from apiclient.errors import MediaUploadSizeError
from apiclient.errors import UnacceptableMimeTypeError
from apiclient.errors import UnknownApiNameOrVersion
from apiclient.errors import UnknownLinkType
from apiclient.http import HttpRequest
from apiclient.http import MediaFileUpload
from apiclient.http import MediaUpload
from apiclient.model import JsonModel
from apiclient.model import RawModel
from apiclient.schema import Schemas
from email.mime.multipart import MIMEMultipart
from email.mime.nonmultipart import MIMENonMultipart
from oauth2client.anyjson import simplejson


URITEMPLATE = re.compile('{[^}]*}')
VARNAME = re.compile('[a-zA-Z0-9_-]+')
DISCOVERY_URI = ('https://www.googleapis.com/discovery/v1/apis/'
  '{api}/{apiVersion}/rest')
DEFAULT_METHOD_DOC = 'A description of how to use this function'

# Query parameters that work, but don't appear in discovery
STACK_QUERY_PARAMETERS = ['trace', 'fields', 'pp', 'prettyPrint', 'userIp',
  'userip', 'strict']

RESERVED_WORDS = ['and', 'assert', 'break', 'class', 'continue', 'def', 'del',
                  'elif', 'else', 'except', 'exec', 'finally', 'for', 'from',
                  'global', 'if', 'import', 'in', 'is', 'lambda', 'not', 'or',
                  'pass', 'print', 'raise', 'return', 'try', 'while' ]


def _fix_method_name(name):
  if name in RESERVED_WORDS:
    return name + '_'
  else:
    return name


def _write_headers(self):
  # Utility no-op method for multipart media handling
  pass


def _add_query_parameter(url, name, value):
  """Adds a query parameter to a url.

  Replaces the current value if it already exists in the URL.

  Args:
    url: string, url to add the query parameter to.
    name: string, query parameter name.
    value: string, query parameter value.

  Returns:
    Updated query parameter. Does not update the url if value is None.
  """
  if value is None:
    return url
  else:
    parsed = list(urlparse.urlparse(url))
    q = dict(parse_qsl(parsed[4]))
    q[name] = value
    parsed[4] = urllib.urlencode(q)
    return urlparse.urlunparse(parsed)


def key2param(key):
  """Converts key names into parameter names.

  For example, converting "max-results" -> "max_results"
  """
  result = []
  key = list(key)
  if not key[0].isalpha():
    result.append('x')
  for c in key:
    if c.isalnum():
      result.append(c)
    else:
      result.append('_')

  return ''.join(result)


def build(serviceName,
          version,
          http=None,
          discoveryServiceUrl=DISCOVERY_URI,
          developerKey=None,
          model=None,
          requestBuilder=HttpRequest):
  """Construct a Resource for interacting with an API.

  Construct a Resource object for interacting with
  an API. The serviceName and version are the
  names from the Discovery service.

  Args:
    serviceName: string, name of the service
    version: string, the version of the service
    http: httplib2.Http, An instance of httplib2.Http or something that acts
      like it that HTTP requests will be made through.
    discoveryServiceUrl: string, a URI Template that points to
      the location of the discovery service. It should have two
      parameters {api} and {apiVersion} that when filled in
      produce an absolute URI to the discovery document for
      that service.
    developerKey: string, key obtained
      from https://code.google.com/apis/console
    model: apiclient.Model, converts to and from the wire format
    requestBuilder: apiclient.http.HttpRequest, encapsulator for
      an HTTP request

  Returns:
    A Resource object with methods for interacting with
    the service.
  """
  params = {
      'api': serviceName,
      'apiVersion': version
      }

  if http is None:
    http = httplib2.Http()

  requested_url = uritemplate.expand(discoveryServiceUrl, params)

  # REMOTE_ADDR is defined by the CGI spec [RFC3875] as the environment
  # variable that contains the network address of the client sending the
  # request. If it exists then add that to the request for the discovery
  # document to avoid exceeding the quota on discovery requests.
  if 'REMOTE_ADDR' in os.environ:
    requested_url = _add_query_parameter(requested_url, 'userIp',
                                         os.environ['REMOTE_ADDR'])
  logging.info('URL being requested: %s' % requested_url)

  resp, content = http.request(requested_url)

  if resp.status == 404:
    raise UnknownApiNameOrVersion("name: %s  version: %s" % (serviceName,
                                                            version))
  if resp.status >= 400:
    raise HttpError(resp, content, requested_url)

  try:
    service = simplejson.loads(content)
  except ValueError, e:
    logging.error('Failed to parse as JSON: ' + content)
    raise InvalidJsonError()

  filename = os.path.join(os.path.dirname(__file__), 'contrib',
      serviceName, 'future.json')
  try:
    f = file(filename, 'r')
    future = f.read()
    f.close()
  except IOError:
    future = None

  return build_from_document(content, discoveryServiceUrl, future,
      http, developerKey, model, requestBuilder)


def build_from_document(
    service,
    base,
    future=None,
    http=None,
    developerKey=None,
    model=None,
    requestBuilder=HttpRequest):
  """Create a Resource for interacting with an API.

  Same as `build()`, but constructs the Resource object
  from a discovery document that is it given, as opposed to
  retrieving one over HTTP.

  Args:
    service: string, discovery document
    base: string, base URI for all HTTP requests, usually the discovery URI
    future: string, discovery document with future capabilities
    auth_discovery: dict, information about the authentication the API supports
    http: httplib2.Http, An instance of httplib2.Http or something that acts
      like it that HTTP requests will be made through.
    developerKey: string, Key for controlling API usage, generated
      from the API Console.
    model: Model class instance that serializes and
      de-serializes requests and responses.
    requestBuilder: Takes an http request and packages it up to be executed.

  Returns:
    A Resource object with methods for interacting with
    the service.
  """

  service = simplejson.loads(service)
  base = urlparse.urljoin(base, service['basePath'])
  if future:
    future = simplejson.loads(future)
    auth_discovery = future.get('auth', {})
  else:
    future = {}
    auth_discovery = {}
  schema = Schemas(service)

  if model is None:
    features = service.get('features', [])
    model = JsonModel('dataWrapper' in features)
  resource = createResource(http, base, model, requestBuilder, developerKey,
                       service, future, schema)

  def auth_method():
    """Discovery information about the authentication the API uses."""
    return auth_discovery

  setattr(resource, 'auth_discovery', auth_method)

  return resource


def _cast(value, schema_type):
  """Convert value to a string based on JSON Schema type.

  See http://tools.ietf.org/html/draft-zyp-json-schema-03 for more details on
  JSON Schema.

  Args:
    value: any, the value to convert
    schema_type: string, the type that value should be interpreted as

  Returns:
    A string representation of 'value' based on the schema_type.
  """
  if schema_type == 'string':
    if type(value) == type('') or type(value) == type(u''):
      return value
    else:
      return str(value)
  elif schema_type == 'integer':
    return str(int(value))
  elif schema_type == 'number':
    return str(float(value))
  elif schema_type == 'boolean':
    return str(bool(value)).lower()
  else:
    if type(value) == type('') or type(value) == type(u''):
      return value
    else:
      return str(value)

MULTIPLIERS = {
    "KB": 2 ** 10,
    "MB": 2 ** 20,
    "GB": 2 ** 30,
    "TB": 2 ** 40,
    }


def _media_size_to_long(maxSize):
  """Convert a string media size, such as 10GB or 3TB into an integer."""
  if len(maxSize) < 2:
    return 0
  units = maxSize[-2:].upper()
  multiplier = MULTIPLIERS.get(units, 0)
  if multiplier:
    return int(maxSize[:-2]) * multiplier
  else:
    return int(maxSize)


def createResource(http, baseUrl, model, requestBuilder,
                   developerKey, resourceDesc, futureDesc, schema):

  class Resource(object):
    """A class for interacting with a resource."""

    def __init__(self):
      self._http = http
      self._baseUrl = baseUrl
      self._model = model
      self._developerKey = developerKey
      self._requestBuilder = requestBuilder

  def createMethod(theclass, methodName, methodDesc, futureDesc):
    methodName = _fix_method_name(methodName)
    pathUrl = methodDesc['path']
    httpMethod = methodDesc['httpMethod']
    methodId = methodDesc['id']

    mediaPathUrl = None
    accept = []
    maxSize = 0
    if 'mediaUpload' in methodDesc:
      mediaUpload = methodDesc['mediaUpload']
      # TODO(jcgregorio) Use URLs from discovery once it is updated.
      parsed = list(urlparse.urlparse(baseUrl))
      basePath = parsed[2]
      mediaPathUrl = '/upload' + basePath + pathUrl
      accept = mediaUpload['accept']
      maxSize = _media_size_to_long(mediaUpload.get('maxSize', ''))

    if 'parameters' not in methodDesc:
      methodDesc['parameters'] = {}
    for name in STACK_QUERY_PARAMETERS:
      methodDesc['parameters'][name] = {
          'type': 'string',
          'location': 'query'
          }

    if httpMethod in ['PUT', 'POST', 'PATCH'] and 'request' in methodDesc:
      methodDesc['parameters']['body'] = {
          'description': 'The request body.',
          'type': 'object',
          'required': True,
          }
      if 'request' in methodDesc:
        methodDesc['parameters']['body'].update(methodDesc['request'])
      else:
        methodDesc['parameters']['body']['type'] = 'object'
    if 'mediaUpload' in methodDesc:
      methodDesc['parameters']['media_body'] = {
          'description': 'The filename of the media request body.',
          'type': 'string',
          'required': False,
          }
      if 'body' in methodDesc['parameters']:
        methodDesc['parameters']['body']['required'] = False

    argmap = {} # Map from method parameter name to query parameter name
    required_params = [] # Required parameters
    repeated_params = [] # Repeated parameters
    pattern_params = {}  # Parameters that must match a regex
    query_params = [] # Parameters that will be used in the query string
    path_params = {} # Parameters that will be used in the base URL
    param_type = {} # The type of the parameter
    enum_params = {} # Allowable enumeration values for each parameter


    if 'parameters' in methodDesc:
      for arg, desc in methodDesc['parameters'].iteritems():
        param = key2param(arg)
        argmap[param] = arg

        if desc.get('pattern', ''):
          pattern_params[param] = desc['pattern']
        if desc.get('enum', ''):
          enum_params[param] = desc['enum']
        if desc.get('required', False):
          required_params.append(param)
        if desc.get('repeated', False):
          repeated_params.append(param)
        if desc.get('location') == 'query':
          query_params.append(param)
        if desc.get('location') == 'path':
          path_params[param] = param
        param_type[param] = desc.get('type', 'string')

    for match in URITEMPLATE.finditer(pathUrl):
      for namematch in VARNAME.finditer(match.group(0)):
        name = key2param(namematch.group(0))
        path_params[name] = name
        if name in query_params:
          query_params.remove(name)

    def method(self, **kwargs):
      for name in kwargs.iterkeys():
        if name not in argmap:
          raise TypeError('Got an unexpected keyword argument "%s"' % name)

      for name in required_params:
        if name not in kwargs:
          raise TypeError('Missing required parameter "%s"' % name)

      for name, regex in pattern_params.iteritems():
        if name in kwargs:
          if isinstance(kwargs[name], basestring):
            pvalues = [kwargs[name]]
          else:
            pvalues = kwargs[name]
          for pvalue in pvalues:
            if re.match(regex, pvalue) is None:
              raise TypeError(
                  'Parameter "%s" value "%s" does not match the pattern "%s"' %
                  (name, pvalue, regex))

      for name, enums in enum_params.iteritems():
        if name in kwargs:
          # We need to handle the case of a repeated enum
          # name differently, since we want to handle both
          # arg='value' and arg=['value1', 'value2']
          if (name in repeated_params and
              not isinstance(kwargs[name], basestring)):
            values = kwargs[name]
          else:
            values = [kwargs[name]]
          for value in values:
            if value not in enums:
              raise TypeError(
                  'Parameter "%s" value "%s" is not an allowed value in "%s"' %
                  (name, value, str(enums)))

      actual_query_params = {}
      actual_path_params = {}
      for key, value in kwargs.iteritems():
        to_type = param_type.get(key, 'string')
        # For repeated parameters we cast each member of the list.
        if key in repeated_params and type(value) == type([]):
          cast_value = [_cast(x, to_type) for x in value]
        else:
          cast_value = _cast(value, to_type)
        if key in query_params:
          actual_query_params[argmap[key]] = cast_value
        if key in path_params:
          actual_path_params[argmap[key]] = cast_value
      body_value = kwargs.get('body', None)
      media_filename = kwargs.get('media_body', None)

      if self._developerKey:
        actual_query_params['key'] = self._developerKey

      model = self._model
      # If there is no schema for the response then presume a binary blob.
      if 'response' not in methodDesc:
        model = RawModel()

      headers = {}
      headers, params, query, body = model.request(headers,
          actual_path_params, actual_query_params, body_value)

      expanded_url = uritemplate.expand(pathUrl, params)
      url = urlparse.urljoin(self._baseUrl, expanded_url + query)

      resumable = None
      multipart_boundary = ''

      if media_filename:
        # Ensure we end up with a valid MediaUpload object.
        if isinstance(media_filename, basestring):
          (media_mime_type, encoding) = mimetypes.guess_type(media_filename)
          if media_mime_type is None:
            raise UnknownFileType(media_filename)
          if not mimeparse.best_match([media_mime_type], ','.join(accept)):
            raise UnacceptableMimeTypeError(media_mime_type)
          media_upload = MediaFileUpload(media_filename, media_mime_type)
        elif isinstance(media_filename, MediaUpload):
          media_upload = media_filename
        else:
          raise TypeError('media_filename must be str or MediaUpload.')

        # Check the maxSize
        if maxSize > 0 and media_upload.size() > maxSize:
          raise MediaUploadSizeError("Media larger than: %s" % maxSize)

        # Use the media path uri for media uploads
        expanded_url = uritemplate.expand(mediaPathUrl, params)
        url = urlparse.urljoin(self._baseUrl, expanded_url + query)
        if media_upload.resumable():
          url = _add_query_parameter(url, 'uploadType', 'resumable')

        if media_upload.resumable():
          # This is all we need to do for resumable, if the body exists it gets
          # sent in the first request, otherwise an empty body is sent.
          resumable = media_upload
        else:
          # A non-resumable upload
          if body is None:
            # This is a simple media upload
            headers['content-type'] = media_upload.mimetype()
            body = media_upload.getbytes(0, media_upload.size())
            url = _add_query_parameter(url, 'uploadType', 'media')
          else:
            # This is a multipart/related upload.
            msgRoot = MIMEMultipart('related')
            # msgRoot should not write out it's own headers
            setattr(msgRoot, '_write_headers', lambda self: None)

            # attach the body as one part
            msg = MIMENonMultipart(*headers['content-type'].split('/'))
            msg.set_payload(body)
            msgRoot.attach(msg)

            # attach the media as the second part
            msg = MIMENonMultipart(*media_upload.mimetype().split('/'))
            msg['Content-Transfer-Encoding'] = 'binary'

            payload = media_upload.getbytes(0, media_upload.size())
            msg.set_payload(payload)
            msgRoot.attach(msg)
            body = msgRoot.as_string()

            multipart_boundary = msgRoot.get_boundary()
            headers['content-type'] = ('multipart/related; '
                                       'boundary="%s"') % multipart_boundary
            url = _add_query_parameter(url, 'uploadType', 'multipart')

      logging.info('URL being requested: %s' % url)
      return self._requestBuilder(self._http,
                                  model.response,
                                  url,
                                  method=httpMethod,
                                  body=body,
                                  headers=headers,
                                  methodId=methodId,
                                  resumable=resumable)

    docs = [methodDesc.get('description', DEFAULT_METHOD_DOC), '\n\n']
    if len(argmap) > 0:
      docs.append('Args:\n')
    for arg in argmap.iterkeys():
      if arg in STACK_QUERY_PARAMETERS:
        continue
      repeated = ''
      if arg in repeated_params:
        repeated = ' (repeated)'
      required = ''
      if arg in required_params:
        required = ' (required)'
      paramdesc = methodDesc['parameters'][argmap[arg]]
      paramdoc = paramdesc.get('description', 'A parameter')
      if '$ref' in paramdesc:
        docs.append(
            ('  %s: object, %s%s%s\n    The object takes the'
            ' form of:\n\n%s\n\n') % (arg, paramdoc, required, repeated,
              schema.prettyPrintByName(paramdesc['$ref'])))
      else:
        paramtype = paramdesc.get('type', 'string')
        docs.append('  %s: %s, %s%s%s\n' % (arg, paramtype, paramdoc, required,
                                            repeated))
      enum = paramdesc.get('enum', [])
      enumDesc = paramdesc.get('enumDescriptions', [])
      if enum and enumDesc:
        docs.append('    Allowed values\n')
        for (name, desc) in zip(enum, enumDesc):
          docs.append('      %s - %s\n' % (name, desc))
    if 'response' in methodDesc:
      docs.append('\nReturns:\n  An object of the form\n\n    ')
      docs.append(schema.prettyPrintSchema(methodDesc['response']))

    setattr(method, '__doc__', ''.join(docs))
    setattr(theclass, methodName, method)

  def createNextMethodFromFuture(theclass, methodName, methodDesc, futureDesc):
    """ This is a legacy method, as only Buzz and Moderator use the future.json
    functionality for generating _next methods. It will be kept around as long
    as those API versions are around, but no new APIs should depend upon it.
    """
    methodName = _fix_method_name(methodName)
    methodId = methodDesc['id'] + '.next'

    def methodNext(self, previous):
      """Retrieve the next page of results.

      Takes a single argument, 'body', which is the results
      from the last call, and returns the next set of items
      in the collection.

      Returns:
        None if there are no more items in the collection.
      """
      if futureDesc['type'] != 'uri':
        raise UnknownLinkType(futureDesc['type'])

      try:
        p = previous
        for key in futureDesc['location']:
          p = p[key]
        url = p
      except (KeyError, TypeError):
        return None

      url = _add_query_parameter(url, 'key', self._developerKey)

      headers = {}
      headers, params, query, body = self._model.request(headers, {}, {}, None)

      logging.info('URL being requested: %s' % url)
      resp, content = self._http.request(url, method='GET', headers=headers)

      return self._requestBuilder(self._http,
                                  self._model.response,
                                  url,
                                  method='GET',
                                  headers=headers,
                                  methodId=methodId)

    setattr(theclass, methodName, methodNext)

  def createNextMethod(theclass, methodName, methodDesc, futureDesc):
    methodName = _fix_method_name(methodName)
    methodId = methodDesc['id'] + '.next'

    def methodNext(self, previous_request, previous_response):
      """Retrieves the next page of results.

      Args:
        previous_request: The request for the previous page.
        previous_response: The response from the request for the previous page.

      Returns:
        A request object that you can call 'execute()' on to request the next
        page. Returns None if there are no more items in the collection.
      """
      # Retrieve nextPageToken from previous_response
      # Use as pageToken in previous_request to create new request.

      if 'nextPageToken' not in previous_response:
        return None

      request = copy.copy(previous_request)

      pageToken = previous_response['nextPageToken']
      parsed = list(urlparse.urlparse(request.uri))
      q = parse_qsl(parsed[4])

      # Find and remove old 'pageToken' value from URI
      newq = [(key, value) for (key, value) in q if key != 'pageToken']
      newq.append(('pageToken', pageToken))
      parsed[4] = urllib.urlencode(newq)
      uri = urlparse.urlunparse(parsed)

      request.uri = uri

      logging.info('URL being requested: %s' % uri)

      return request

    setattr(theclass, methodName, methodNext)

  # Add basic methods to Resource
  if 'methods' in resourceDesc:
    for methodName, methodDesc in resourceDesc['methods'].iteritems():
      if futureDesc:
        future = futureDesc['methods'].get(methodName, {})
      else:
        future = None
      createMethod(Resource, methodName, methodDesc, future)

  # Add in nested resources
  if 'resources' in resourceDesc:

    def createResourceMethod(theclass, methodName, methodDesc, futureDesc):
      methodName = _fix_method_name(methodName)

      def methodResource(self):
        return createResource(self._http, self._baseUrl, self._model,
                              self._requestBuilder, self._developerKey,
                              methodDesc, futureDesc, schema)

      setattr(methodResource, '__doc__', 'A collection resource.')
      setattr(methodResource, '__is_resource__', True)
      setattr(theclass, methodName, methodResource)

    for methodName, methodDesc in resourceDesc['resources'].iteritems():
      if futureDesc and 'resources' in futureDesc:
        future = futureDesc['resources'].get(methodName, {})
      else:
        future = {}
      createResourceMethod(Resource, methodName, methodDesc, future)

  # Add <m>_next() methods to Resource
  if futureDesc and 'methods' in futureDesc:
    for methodName, methodDesc in futureDesc['methods'].iteritems():
      if 'next' in methodDesc and methodName in resourceDesc['methods']:
        createNextMethodFromFuture(Resource, methodName + '_next',
                         resourceDesc['methods'][methodName],
                         methodDesc['next'])
  # Add _next() methods
  # Look for response bodies in schema that contain nextPageToken, and methods
  # that take a pageToken parameter.
  if 'methods' in resourceDesc:
    for methodName, methodDesc in resourceDesc['methods'].iteritems():
      if 'response' in methodDesc:
        responseSchema = methodDesc['response']
        if '$ref' in responseSchema:
          responseSchema = schema.get(responseSchema['$ref'])
        hasNextPageToken = 'nextPageToken' in responseSchema.get('properties',
                                                                 {})
        hasPageToken = 'pageToken' in methodDesc.get('parameters', {})
        if hasNextPageToken and hasPageToken:
          createNextMethod(Resource, methodName + '_next',
                           resourceDesc['methods'][methodName],
                           methodName)

  return Resource()

########NEW FILE########
__FILENAME__ = errors
#!/usr/bin/python2.4
#
# Copyright (C) 2010 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Errors for the library.

All exceptions defined by the library
should be defined in this file.
"""

__author__ = 'jcgregorio@google.com (Joe Gregorio)'


from oauth2client.anyjson import simplejson


class Error(Exception):
  """Base error for this module."""
  pass


class HttpError(Error):
  """HTTP data was invalid or unexpected."""

  def __init__(self, resp, content, uri=None):
    self.resp = resp
    self.content = content
    self.uri = uri

  def _get_reason(self):
    """Calculate the reason for the error from the response content."""
    if self.resp.get('content-type', '').startswith('application/json'):
      try:
        data = simplejson.loads(self.content)
        reason = data['error']['message']
      except (ValueError, KeyError):
        reason = self.content
    else:
      reason = self.resp.reason
    return reason

  def __repr__(self):
    if self.uri:
      return '<HttpError %s when requesting %s returned "%s">' % (
          self.resp.status, self.uri, self._get_reason())
    else:
      return '<HttpError %s "%s">' % (self.resp.status, self._get_reason())

  __str__ = __repr__


class InvalidJsonError(Error):
  """The JSON returned could not be parsed."""
  pass


class UnknownLinkType(Error):
  """Link type unknown or unexpected."""
  pass


class UnknownApiNameOrVersion(Error):
  """No API with that name and version exists."""
  pass


class UnacceptableMimeTypeError(Error):
  """That is an unacceptable mimetype for this operation."""
  pass


class MediaUploadSizeError(Error):
  """Media is larger than the method can accept."""
  pass


class ResumableUploadError(Error):
  """Error occured during resumable upload."""
  pass


class BatchError(HttpError):
  """Error occured during batch operations."""

  def __init__(self, reason, resp=None, content=None):
    self.resp = resp
    self.content = content
    self.reason = reason

  def __repr__(self):
      return '<BatchError %s "%s">' % (self.resp.status, self.reason)

  __str__ = __repr__


class UnexpectedMethodError(Error):
  """Exception raised by RequestMockBuilder on unexpected calls."""

  def __init__(self, methodId=None):
    """Constructor for an UnexpectedMethodError."""
    super(UnexpectedMethodError, self).__init__(
        'Received unexpected call %s' % methodId)


class UnexpectedBodyError(Error):
  """Exception raised by RequestMockBuilder on unexpected bodies."""

  def __init__(self, expected, provided):
    """Constructor for an UnexpectedMethodError."""
    super(UnexpectedBodyError, self).__init__(
        'Expected: [%s] - Provided: [%s]' % (expected, provided))

########NEW FILE########
__FILENAME__ = appengine
# Copyright (C) 2010 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Utilities for Google App Engine

Utilities for making it easier to use the
Google API Client for Python on Google App Engine.
"""

__author__ = 'jcgregorio@google.com (Joe Gregorio)'

import pickle

from google.appengine.ext import db
from apiclient.oauth import OAuthCredentials
from apiclient.oauth import FlowThreeLegged


class FlowThreeLeggedProperty(db.Property):
  """Utility property that allows easy
  storage and retreival of an
  apiclient.oauth.FlowThreeLegged"""

  # Tell what the user type is.
  data_type = FlowThreeLegged

  # For writing to datastore.
  def get_value_for_datastore(self, model_instance):
    flow = super(FlowThreeLeggedProperty,
                 self).get_value_for_datastore(model_instance)
    return db.Blob(pickle.dumps(flow))

  # For reading from datastore.
  def make_value_from_datastore(self, value):
    if value is None:
      return None
    return pickle.loads(value)

  def validate(self, value):
    if value is not None and not isinstance(value, FlowThreeLegged):
      raise BadValueError('Property %s must be convertible '
                          'to a FlowThreeLegged instance (%s)' %
                          (self.name, value))
    return super(FlowThreeLeggedProperty, self).validate(value)

  def empty(self, value):
    return not value


class OAuthCredentialsProperty(db.Property):
  """Utility property that allows easy
  storage and retrieval of
  apiclient.oath.OAuthCredentials
  """

  # Tell what the user type is.
  data_type = OAuthCredentials

  # For writing to datastore.
  def get_value_for_datastore(self, model_instance):
    cred = super(OAuthCredentialsProperty,
                 self).get_value_for_datastore(model_instance)
    return db.Blob(pickle.dumps(cred))

  # For reading from datastore.
  def make_value_from_datastore(self, value):
    if value is None:
      return None
    return pickle.loads(value)

  def validate(self, value):
    if value is not None and not isinstance(value, OAuthCredentials):
      raise BadValueError('Property %s must be convertible '
                          'to an OAuthCredentials instance (%s)' %
                          (self.name, value))
    return super(OAuthCredentialsProperty, self).validate(value)

  def empty(self, value):
    return not value


class StorageByKeyName(object):
  """Store and retrieve a single credential to and from
  the App Engine datastore.

  This Storage helper presumes the Credentials
  have been stored as a CredenialsProperty
  on a datastore model class, and that entities
  are stored by key_name.
  """

  def __init__(self, model, key_name, property_name):
    """Constructor for Storage.

    Args:
      model: db.Model, model class
      key_name: string, key name for the entity that has the credentials
      property_name: string, name of the property that is a CredentialsProperty
    """
    self.model = model
    self.key_name = key_name
    self.property_name = property_name

  def get(self):
    """Retrieve Credential from datastore.

    Returns:
      Credentials
    """
    entity = self.model.get_or_insert(self.key_name)
    credential = getattr(entity, self.property_name)
    if credential and hasattr(credential, 'set_store'):
      credential.set_store(self.put)
    return credential

  def put(self, credentials):
    """Write a Credentials to the datastore.

    Args:
      credentials: Credentials, the credentials to store.
    """
    entity = self.model.get_or_insert(self.key_name)
    setattr(entity, self.property_name, credentials)
    entity.put()

########NEW FILE########
__FILENAME__ = authtools
# Copyright (C) 2010 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Command-line tools for authenticating via OAuth 1.0

Do the OAuth 1.0 Three Legged Dance for
a command line application. Stores the generated
credentials in a common file that is used by
other example apps in the same directory.
"""

__author__ = 'jcgregorio@google.com (Joe Gregorio)'
__all__ = ["run"]

import BaseHTTPServer
import gflags
import logging
import socket
import sys

from optparse import OptionParser
from apiclient.oauth import RequestError

try:
    from urlparse import parse_qsl
except ImportError:
    from cgi import parse_qsl


FLAGS = gflags.FLAGS

gflags.DEFINE_boolean('auth_local_webserver', True,
                     ('Run a local web server to handle redirects during '
                       'OAuth authorization.'))

gflags.DEFINE_string('auth_host_name', 'localhost',
                     ('Host name to use when running a local web server to '
                       'handle redirects during OAuth authorization.'))

gflags.DEFINE_multi_int('auth_host_port', [8080, 8090],
                     ('Port to use when running a local web server to '
                       'handle redirects during OAuth authorization.'))


class ClientRedirectServer(BaseHTTPServer.HTTPServer):
  """A server to handle OAuth 1.0 redirects back to localhost.

  Waits for a single request and parses the query parameters
  into query_params and then stops serving.
  """
  query_params = {}


class ClientRedirectHandler(BaseHTTPServer.BaseHTTPRequestHandler):
  """A handler for OAuth 1.0 redirects back to localhost.

  Waits for a single request and parses the query parameters
  into the servers query_params and then stops serving.
  """

  def do_GET(s):
    """Handle a GET request

    Parses the query parameters and prints a message
    if the flow has completed. Note that we can't detect
    if an error occurred.
    """
    s.send_response(200)
    s.send_header("Content-type", "text/html")
    s.end_headers()
    query = s.path.split('?', 1)[-1]
    query = dict(parse_qsl(query))
    s.server.query_params = query
    s.wfile.write("<html><head><title>Authentication Status</title></head>")
    s.wfile.write("<body><p>The authentication flow has completed.</p>")
    s.wfile.write("</body></html>")

  def log_message(self, format, *args):
    """Do not log messages to stdout while running as command line program."""
    pass


def run(flow, storage):
  """Core code for a command-line application.

  Args:
    flow: Flow, an OAuth 1.0 Flow to step through.
    storage: Storage, a Storage to store the credential in.

  Returns:
    Credentials, the obtained credential.

  Exceptions:
    RequestError: if step2 of the flow fails.
  Args:
  """

  if FLAGS.auth_local_webserver:
    success = False
    port_number = 0
    for port in FLAGS.auth_host_port:
      port_number = port
      try:
        httpd = BaseHTTPServer.HTTPServer((FLAGS.auth_host_name, port),
            ClientRedirectHandler)
      except socket.error, e:
        pass
      else:
        success = True
        break
    FLAGS.auth_local_webserver = success

  if FLAGS.auth_local_webserver:
    oauth_callback = 'http://%s:%s/' % (FLAGS.auth_host_name, port_number)
  else:
    oauth_callback = 'oob'
  authorize_url = flow.step1_get_authorize_url(oauth_callback)

  print 'Go to the following link in your browser:'
  print authorize_url
  print
  if FLAGS.auth_local_webserver:
    print 'If your browser is on a different machine then exit and re-run this'
    print 'application with the command-line parameter --noauth_local_webserver.'
    print

  if FLAGS.auth_local_webserver:
    httpd.handle_request()
    if 'error' in httpd.query_params:
      sys.exit('Authentication request was rejected.')
    if 'oauth_verifier' in httpd.query_params:
      code = httpd.query_params['oauth_verifier']
  else:
    accepted = 'n'
    while accepted.lower() == 'n':
      accepted = raw_input('Have you authorized me? (y/n) ')
    code = raw_input('What is the verification code? ').strip()

  try:
    credentials = flow.step2_exchange(code)
  except RequestError:
    sys.exit('The authentication has failed.')

  storage.put(credentials)
  credentials.set_store(storage.put)
  print "You have successfully authenticated."

  return credentials

########NEW FILE########
__FILENAME__ = django_orm
# Copyright (C) 2010 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import apiclient
import base64
import pickle

from django.db import models


class OAuthCredentialsField(models.Field):

  __metaclass__ = models.SubfieldBase

  def db_type(self):
    return 'VARCHAR'

  def to_python(self, value):
    if value is None:
      return None
    if isinstance(value, apiclient.oauth.Credentials):
      return value
    return pickle.loads(base64.b64decode(value))

  def get_db_prep_value(self, value):
    return base64.b64encode(pickle.dumps(value))


class FlowThreeLeggedField(models.Field):

  __metaclass__ = models.SubfieldBase

  def db_type(self):
    return 'VARCHAR'

  def to_python(self, value):
    print "In to_python", value
    if value is None:
      return None
    if isinstance(value, apiclient.oauth.FlowThreeLegged):
      return value
    return pickle.loads(base64.b64decode(value))

  def get_db_prep_value(self, value):
    return base64.b64encode(pickle.dumps(value))

########NEW FILE########
__FILENAME__ = file
# Copyright (C) 2010 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Utilities for OAuth.

Utilities for making it easier to work with OAuth 1.0 credentials.
"""

__author__ = 'jcgregorio@google.com (Joe Gregorio)'

import pickle
import threading

from apiclient.oauth import Storage as BaseStorage


class Storage(BaseStorage):
  """Store and retrieve a single credential to and from a file."""

  def __init__(self, filename):
    self._filename = filename
    self._lock = threading.Lock()

  def get(self):
    """Retrieve Credential from file.

    Returns:
      apiclient.oauth.Credentials
    """
    self._lock.acquire()
    try:
      f = open(self._filename, 'r')
      credentials = pickle.loads(f.read())
      f.close()
      credentials.set_store(self.put)
    except:
      credentials = None
    self._lock.release()

    return credentials

  def put(self, credentials):
    """Write a pickled Credentials to file.

    Args:
      credentials: Credentials, the credentials to store.
    """
    self._lock.acquire()
    f = open(self._filename, 'w')
    f.write(pickle.dumps(credentials))
    f.close()
    self._lock.release()

########NEW FILE########
__FILENAME__ = http
# Copyright (C) 2010 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Classes to encapsulate a single HTTP request.

The classes implement a command pattern, with every
object supporting an execute() method that does the
actuall HTTP request.
"""

__author__ = 'jcgregorio@google.com (Joe Gregorio)'
__all__ = [
    'HttpRequest', 'RequestMockBuilder', 'HttpMock'
    'set_user_agent', 'tunnel_patch'
    ]

import StringIO
import base64
import copy
import gzip
import httplib2
import mimeparse
import mimetypes
import os
import urllib
import urlparse
import uuid

from email.generator import Generator
from email.mime.multipart import MIMEMultipart
from email.mime.nonmultipart import MIMENonMultipart
from email.parser import FeedParser
from errors import BatchError
from errors import HttpError
from errors import ResumableUploadError
from errors import UnexpectedBodyError
from errors import UnexpectedMethodError
from model import JsonModel
from oauth2client.anyjson import simplejson


class MediaUploadProgress(object):
  """Status of a resumable upload."""

  def __init__(self, resumable_progress, total_size):
    """Constructor.

    Args:
      resumable_progress: int, bytes sent so far.
      total_size: int, total bytes in complete upload.
    """
    self.resumable_progress = resumable_progress
    self.total_size = total_size

  def progress(self):
    """Percent of upload completed, as a float."""
    return float(self.resumable_progress) / float(self.total_size)


class MediaUpload(object):
  """Describes a media object to upload.

  Base class that defines the interface of MediaUpload subclasses.
  """

  def getbytes(self, begin, end):
    raise NotImplementedError()

  def size(self):
    raise NotImplementedError()

  def chunksize(self):
    raise NotImplementedError()

  def mimetype(self):
    return 'application/octet-stream'

  def resumable(self):
    return False

  def _to_json(self, strip=None):
    """Utility function for creating a JSON representation of a MediaUpload.

    Args:
      strip: array, An array of names of members to not include in the JSON.

    Returns:
       string, a JSON representation of this instance, suitable to pass to
       from_json().
    """
    t = type(self)
    d = copy.copy(self.__dict__)
    if strip is not None:
      for member in strip:
        del d[member]
    d['_class'] = t.__name__
    d['_module'] = t.__module__
    return simplejson.dumps(d)

  def to_json(self):
    """Create a JSON representation of an instance of MediaUpload.

    Returns:
       string, a JSON representation of this instance, suitable to pass to
       from_json().
    """
    return self._to_json()

  @classmethod
  def new_from_json(cls, s):
    """Utility class method to instantiate a MediaUpload subclass from a JSON
    representation produced by to_json().

    Args:
      s: string, JSON from to_json().

    Returns:
      An instance of the subclass of MediaUpload that was serialized with
      to_json().
    """
    data = simplejson.loads(s)
    # Find and call the right classmethod from_json() to restore the object.
    module = data['_module']
    m = __import__(module, fromlist=module.split('.')[:-1])
    kls = getattr(m, data['_class'])
    from_json = getattr(kls, 'from_json')
    return from_json(s)


class MediaFileUpload(MediaUpload):
  """A MediaUpload for a file.

  Construct a MediaFileUpload and pass as the media_body parameter of the
  method. For example, if we had a service that allowed uploading images:


    media = MediaFileUpload('smiley.png', mimetype='image/png', chunksize=1000,
                    resumable=True)
    service.objects().insert(
        bucket=buckets['items'][0]['id'],
        name='smiley.png',
        media_body=media).execute()
  """

  def __init__(self, filename, mimetype=None, chunksize=256*1024, resumable=False):
    """Constructor.

    Args:
      filename: string, Name of the file.
      mimetype: string, Mime-type of the file. If None then a mime-type will be
        guessed from the file extension.
      chunksize: int, File will be uploaded in chunks of this many bytes. Only
        used if resumable=True.
      resumable: bool, True if this is a resumable upload. False means upload
        in a single request.
    """
    self._filename = filename
    self._size = os.path.getsize(filename)
    self._fd = None
    if mimetype is None:
      (mimetype, encoding) = mimetypes.guess_type(filename)
    self._mimetype = mimetype
    self._chunksize = chunksize
    self._resumable = resumable

  def mimetype(self):
    return self._mimetype

  def size(self):
    return self._size

  def chunksize(self):
    return self._chunksize

  def resumable(self):
    return self._resumable

  def getbytes(self, begin, length):
    """Get bytes from the media.

    Args:
      begin: int, offset from beginning of file.
      length: int, number of bytes to read, starting at begin.

    Returns:
      A string of bytes read. May be shorted than length if EOF was reached
      first.
    """
    if self._fd is None:
      self._fd = open(self._filename, 'rb')
    self._fd.seek(begin)
    return self._fd.read(length)

  def to_json(self):
    """Creating a JSON representation of an instance of Credentials.

    Returns:
       string, a JSON representation of this instance, suitable to pass to
       from_json().
    """
    return self._to_json(['_fd'])

  @staticmethod
  def from_json(s):
    d = simplejson.loads(s)
    return MediaFileUpload(
        d['_filename'], d['_mimetype'], d['_chunksize'], d['_resumable'])


class MediaInMemoryUpload(MediaUpload):
  """MediaUpload for a chunk of bytes.

  Construct a MediaFileUpload and pass as the media_body parameter of the
  method. For example, if we had a service that allowed plain text:
  """

  def __init__(self, body, mimetype='application/octet-stream',
               chunksize=256*1024, resumable=False):
    """Create a new MediaBytesUpload.

    Args:
      body: string, Bytes of body content.
      mimetype: string, Mime-type of the file or default of
        'application/octet-stream'.
      chunksize: int, File will be uploaded in chunks of this many bytes. Only
        used if resumable=True.
      resumable: bool, True if this is a resumable upload. False means upload
        in a single request.
    """
    self._body = body
    self._mimetype = mimetype
    self._resumable = resumable
    self._chunksize = chunksize

  def chunksize(self):
    """Chunk size for resumable uploads.

    Returns:
      Chunk size in bytes.
    """
    return self._chunksize

  def mimetype(self):
    """Mime type of the body.

    Returns:
      Mime type.
    """
    return self._mimetype

  def size(self):
    """Size of upload.

    Returns:
      Size of the body.
    """
    return len(self.body)

  def resumable(self):
    """Whether this upload is resumable.

    Returns:
      True if resumable upload or False.
    """
    return self._resumable

  def getbytes(self, begin, length):
    """Get bytes from the media.

    Args:
      begin: int, offset from beginning of file.
      length: int, number of bytes to read, starting at begin.

    Returns:
      A string of bytes read. May be shorter than length if EOF was reached
      first.
    """
    return self._body[begin:begin + length]

  def to_json(self):
    """Create a JSON representation of a MediaInMemoryUpload.

    Returns:
       string, a JSON representation of this instance, suitable to pass to
       from_json().
    """
    t = type(self)
    d = copy.copy(self.__dict__)
    del d['_body']
    d['_class'] = t.__name__
    d['_module'] = t.__module__
    d['_b64body'] = base64.b64encode(self._body)
    return simplejson.dumps(d)

  @staticmethod
  def from_json(s):
    d = simplejson.loads(s)
    return MediaInMemoryUpload(base64.b64decode(d['_b64body']),
                               d['_mimetype'], d['_chunksize'],
                               d['_resumable'])


class HttpRequest(object):
  """Encapsulates a single HTTP request."""

  def __init__(self, http, postproc, uri,
               method='GET',
               body=None,
               headers=None,
               methodId=None,
               resumable=None):
    """Constructor for an HttpRequest.

    Args:
      http: httplib2.Http, the transport object to use to make a request
      postproc: callable, called on the HTTP response and content to transform
                it into a data object before returning, or raising an exception
                on an error.
      uri: string, the absolute URI to send the request to
      method: string, the HTTP method to use
      body: string, the request body of the HTTP request,
      headers: dict, the HTTP request headers
      methodId: string, a unique identifier for the API method being called.
      resumable: MediaUpload, None if this is not a resumbale request.
    """
    self.uri = uri
    self.method = method
    self.body = body
    self.headers = headers or {}
    self.methodId = methodId
    self.http = http
    self.postproc = postproc
    self.resumable = resumable

    # Pull the multipart boundary out of the content-type header.
    major, minor, params = mimeparse.parse_mime_type(
        headers.get('content-type', 'application/json'))

    # The size of the non-media part of the request.
    self.body_size = len(self.body or '')

    # The resumable URI to send chunks to.
    self.resumable_uri = None

    # The bytes that have been uploaded.
    self.resumable_progress = 0

  def execute(self, http=None):
    """Execute the request.

    Args:
      http: httplib2.Http, an http object to be used in place of the
            one the HttpRequest request object was constructed with.

    Returns:
      A deserialized object model of the response body as determined
      by the postproc.

    Raises:
      apiclient.errors.HttpError if the response was not a 2xx.
      httplib2.Error if a transport error has occured.
    """
    if http is None:
      http = self.http
    if self.resumable:
      body = None
      while body is None:
        _, body = self.next_chunk(http)
      return body
    else:
      if 'content-length' not in self.headers:
        self.headers['content-length'] = str(self.body_size)
      resp, content = http.request(self.uri, self.method,
                                   body=self.body,
                                   headers=self.headers)

      if resp.status >= 300:
        raise HttpError(resp, content, self.uri)
    return self.postproc(resp, content)

  def next_chunk(self, http=None):
    """Execute the next step of a resumable upload.

    Can only be used if the method being executed supports media uploads and
    the MediaUpload object passed in was flagged as using resumable upload.

    Example:

      media = MediaFileUpload('smiley.png', mimetype='image/png',
                              chunksize=1000, resumable=True)
      request = service.objects().insert(
          bucket=buckets['items'][0]['id'],
          name='smiley.png',
          media_body=media)

      response = None
      while response is None:
        status, response = request.next_chunk()
        if status:
          print "Upload %d%% complete." % int(status.progress() * 100)


    Returns:
      (status, body): (ResumableMediaStatus, object)
         The body will be None until the resumable media is fully uploaded.
    """
    if http is None:
      http = self.http

    if self.resumable_uri is None:
      start_headers = copy.copy(self.headers)
      start_headers['X-Upload-Content-Type'] = self.resumable.mimetype()
      start_headers['X-Upload-Content-Length'] = str(self.resumable.size())
      start_headers['content-length'] = str(self.body_size)

      resp, content = http.request(self.uri, self.method,
                                   body=self.body,
                                   headers=start_headers)
      if resp.status == 200 and 'location' in resp:
        self.resumable_uri = resp['location']
      else:
        raise ResumableUploadError("Failed to retrieve starting URI.")

    data = self.resumable.getbytes(self.resumable_progress,
                                   self.resumable.chunksize())

    headers = {
        'Content-Range': 'bytes %d-%d/%d' % (
            self.resumable_progress, self.resumable_progress + len(data) - 1,
            self.resumable.size()),
        }
    resp, content = http.request(self.resumable_uri, 'PUT',
                                 body=data,
                                 headers=headers)
    if resp.status in [200, 201]:
      return None, self.postproc(resp, content)
    elif resp.status == 308:
      # A "308 Resume Incomplete" indicates we are not done.
      self.resumable_progress = int(resp['range'].split('-')[1]) + 1
      if 'location' in resp:
        self.resumable_uri = resp['location']
    else:
      raise HttpError(resp, content, self.uri)

    return (MediaUploadProgress(self.resumable_progress, self.resumable.size()),
            None)

  def to_json(self):
    """Returns a JSON representation of the HttpRequest."""
    d = copy.copy(self.__dict__)
    if d['resumable'] is not None:
      d['resumable'] = self.resumable.to_json()
    del d['http']
    del d['postproc']
    return simplejson.dumps(d)

  @staticmethod
  def from_json(s, http, postproc):
    """Returns an HttpRequest populated with info from a JSON object."""
    d = simplejson.loads(s)
    if d['resumable'] is not None:
      d['resumable'] = MediaUpload.new_from_json(d['resumable'])
    return HttpRequest(
        http,
        postproc,
        uri=d['uri'],
        method=d['method'],
        body=d['body'],
        headers=d['headers'],
        methodId=d['methodId'],
        resumable=d['resumable'])


class BatchHttpRequest(object):
  """Batches multiple HttpRequest objects into a single HTTP request."""

  def __init__(self, callback=None, batch_uri=None):
    """Constructor for a BatchHttpRequest.

    Args:
      callback: callable, A callback to be called for each response, of the
        form callback(id, response). The first parameter is the request id, and
        the second is the deserialized response object.
      batch_uri: string, URI to send batch requests to.
    """
    if batch_uri is None:
      batch_uri = 'https://www.googleapis.com/batch'
    self._batch_uri = batch_uri

    # Global callback to be called for each individual response in the batch.
    self._callback = callback

    # A map from id to request.
    self._requests = {}

    # A map from id to callback.
    self._callbacks = {}

    # List of request ids, in the order in which they were added.
    self._order = []

    # The last auto generated id.
    self._last_auto_id = 0

    # Unique ID on which to base the Content-ID headers.
    self._base_id = None

    # A map from request id to (headers, content) response pairs
    self._responses = {}

    # A map of id(Credentials) that have been refreshed.
    self._refreshed_credentials = {}

  def _refresh_and_apply_credentials(self, request, http):
    """Refresh the credentials and apply to the request.

    Args:
      request: HttpRequest, the request.
      http: httplib2.Http, the global http object for the batch.
    """
    # For the credentials to refresh, but only once per refresh_token
    # If there is no http per the request then refresh the http passed in
    # via execute()
    creds = None
    if request.http is not None and hasattr(request.http.request,
        'credentials'):
      creds = request.http.request.credentials
    elif http is not None and hasattr(http.request, 'credentials'):
      creds = http.request.credentials
    if creds is not None:
      if id(creds) not in self._refreshed_credentials:
        creds.refresh(http)
        self._refreshed_credentials[id(creds)] = 1

    # Only apply the credentials if we are using the http object passed in,
    # otherwise apply() will get called during _serialize_request().
    if request.http is None or not hasattr(request.http.request,
        'credentials'):
      creds.apply(request.headers)

  def _id_to_header(self, id_):
    """Convert an id to a Content-ID header value.

    Args:
      id_: string, identifier of individual request.

    Returns:
      A Content-ID header with the id_ encoded into it. A UUID is prepended to
      the value because Content-ID headers are supposed to be universally
      unique.
    """
    if self._base_id is None:
      self._base_id = uuid.uuid4()

    return '<%s+%s>' % (self._base_id, urllib.quote(id_))

  def _header_to_id(self, header):
    """Convert a Content-ID header value to an id.

    Presumes the Content-ID header conforms to the format that _id_to_header()
    returns.

    Args:
      header: string, Content-ID header value.

    Returns:
      The extracted id value.

    Raises:
      BatchError if the header is not in the expected format.
    """
    if header[0] != '<' or header[-1] != '>':
      raise BatchError("Invalid value for Content-ID: %s" % header)
    if '+' not in header:
      raise BatchError("Invalid value for Content-ID: %s" % header)
    base, id_ = header[1:-1].rsplit('+', 1)

    return urllib.unquote(id_)

  def _serialize_request(self, request):
    """Convert an HttpRequest object into a string.

    Args:
      request: HttpRequest, the request to serialize.

    Returns:
      The request as a string in application/http format.
    """
    # Construct status line
    parsed = urlparse.urlparse(request.uri)
    request_line = urlparse.urlunparse(
        (None, None, parsed.path, parsed.params, parsed.query, None)
        )
    status_line = request.method + ' ' + request_line + ' HTTP/1.1\n'
    major, minor = request.headers.get('content-type', 'application/json').split('/')
    msg = MIMENonMultipart(major, minor)
    headers = request.headers.copy()

    if request.http is not None and hasattr(request.http.request,
        'credentials'):
      request.http.request.credentials.apply(headers)

    # MIMENonMultipart adds its own Content-Type header.
    if 'content-type' in headers:
      del headers['content-type']

    for key, value in headers.iteritems():
      msg[key] = value
    msg['Host'] = parsed.netloc
    msg.set_unixfrom(None)

    if request.body is not None:
      msg.set_payload(request.body)
      msg['content-length'] = str(len(request.body))

    # Serialize the mime message.
    fp = StringIO.StringIO()
    # maxheaderlen=0 means don't line wrap headers.
    g = Generator(fp, maxheaderlen=0)
    g.flatten(msg, unixfrom=False)
    body = fp.getvalue()

    # Strip off the \n\n that the MIME lib tacks onto the end of the payload.
    if request.body is None:
      body = body[:-2]

    return status_line.encode('utf-8') + body

  def _deserialize_response(self, payload):
    """Convert string into httplib2 response and content.

    Args:
      payload: string, headers and body as a string.

    Returns:
      A pair (resp, content) like would be returned from httplib2.request.
    """
    # Strip off the status line
    status_line, payload = payload.split('\n', 1)
    protocol, status, reason = status_line.split(' ', 2)

    # Parse the rest of the response
    parser = FeedParser()
    parser.feed(payload)
    msg = parser.close()
    msg['status'] = status

    # Create httplib2.Response from the parsed headers.
    resp = httplib2.Response(msg)
    resp.reason = reason
    resp.version = int(protocol.split('/', 1)[1].replace('.', ''))

    content = payload.split('\r\n\r\n', 1)[1]

    return resp, content

  def _new_id(self):
    """Create a new id.

    Auto incrementing number that avoids conflicts with ids already used.

    Returns:
       string, a new unique id.
    """
    self._last_auto_id += 1
    while str(self._last_auto_id) in self._requests:
      self._last_auto_id += 1
    return str(self._last_auto_id)

  def add(self, request, callback=None, request_id=None):
    """Add a new request.

    Every callback added will be paired with a unique id, the request_id. That
    unique id will be passed back to the callback when the response comes back
    from the server. The default behavior is to have the library generate it's
    own unique id. If the caller passes in a request_id then they must ensure
    uniqueness for each request_id, and if they are not an exception is
    raised. Callers should either supply all request_ids or nevery supply a
    request id, to avoid such an error.

    Args:
      request: HttpRequest, Request to add to the batch.
      callback: callable, A callback to be called for this response, of the
        form callback(id, response). The first parameter is the request id, and
        the second is the deserialized response object.
      request_id: string, A unique id for the request. The id will be passed to
        the callback with the response.

    Returns:
      None

    Raises:
      BatchError if a resumable request is added to a batch.
      KeyError is the request_id is not unique.
    """
    if request_id is None:
      request_id = self._new_id()
    if request.resumable is not None:
      raise BatchError("Resumable requests cannot be used in a batch request.")
    if request_id in self._requests:
      raise KeyError("A request with this ID already exists: %s" % request_id)
    self._requests[request_id] = request
    self._callbacks[request_id] = callback
    self._order.append(request_id)

  def _execute(self, http, order, requests):
    """Serialize batch request, send to server, process response.

    Args:
      http: httplib2.Http, an http object to be used to make the request with.
      order: list, list of request ids in the order they were added to the
        batch.
      request: list, list of request objects to send.

    Raises:
      httplib2.Error if a transport error has occured.
      apiclient.errors.BatchError if the response is the wrong format.
    """
    message = MIMEMultipart('mixed')
    # Message should not write out it's own headers.
    setattr(message, '_write_headers', lambda self: None)

    # Add all the individual requests.
    for request_id in order:
      request = requests[request_id]

      msg = MIMENonMultipart('application', 'http')
      msg['Content-Transfer-Encoding'] = 'binary'
      msg['Content-ID'] = self._id_to_header(request_id)

      body = self._serialize_request(request)
      msg.set_payload(body)
      message.attach(msg)

    body = message.as_string()

    headers = {}
    headers['content-type'] = ('multipart/mixed; '
                               'boundary="%s"') % message.get_boundary()

    resp, content = http.request(self._batch_uri, 'POST', body=body,
                                 headers=headers)

    if resp.status >= 300:
      raise HttpError(resp, content, self._batch_uri)

    # Now break out the individual responses and store each one.
    boundary, _ = content.split(None, 1)

    # Prepend with a content-type header so FeedParser can handle it.
    header = 'content-type: %s\r\n\r\n' % resp['content-type']
    for_parser = header + content

    parser = FeedParser()
    parser.feed(for_parser)
    mime_response = parser.close()

    if not mime_response.is_multipart():
      raise BatchError("Response not in multipart/mixed format.", resp,
          content)

    for part in mime_response.get_payload():
      request_id = self._header_to_id(part['Content-ID'])
      headers, content = self._deserialize_response(part.get_payload())
      self._responses[request_id] = (headers, content)

  def execute(self, http=None):
    """Execute all the requests as a single batched HTTP request.

    Args:
      http: httplib2.Http, an http object to be used in place of the one the
        HttpRequest request object was constructed with.  If one isn't supplied
        then use a http object from the requests in this batch.

    Returns:
      None

    Raises:
      httplib2.Error if a transport error has occured.
      apiclient.errors.BatchError if the response is the wrong format.
    """

    # If http is not supplied use the first valid one given in the requests.
    if http is None:
      for request_id in self._order:
        request = self._requests[request_id]
        if request is not None:
          http = request.http
          break

    if http is None:
      raise ValueError("Missing a valid http object.")

    self._execute(http, self._order, self._requests)

    # Loop over all the requests and check for 401s. For each 401 request the
    # credentials should be refreshed and then sent again in a separate batch.
    redo_requests = {}
    redo_order = []

    for request_id in self._order:
      headers, content = self._responses[request_id]
      if headers['status'] == '401':
        redo_order.append(request_id)
        request = self._requests[request_id]
        self._refresh_and_apply_credentials(request, http)
        redo_requests[request_id] = request

    if redo_requests:
      self._execute(http, redo_order, redo_requests)

    # Now process all callbacks that are erroring, and raise an exception for
    # ones that return a non-2xx response? Or add extra parameter to callback
    # that contains an HttpError?

    for request_id in self._order:
      headers, content = self._responses[request_id]

      request = self._requests[request_id]
      callback = self._callbacks[request_id]

      response = None
      exception = None
      try:
        r = httplib2.Response(headers)
        response = request.postproc(r, content)
      except HttpError, e:
        exception = e

      if callback is not None:
        callback(request_id, response, exception)
      if self._callback is not None:
        self._callback(request_id, response, exception)


class HttpRequestMock(object):
  """Mock of HttpRequest.

  Do not construct directly, instead use RequestMockBuilder.
  """

  def __init__(self, resp, content, postproc):
    """Constructor for HttpRequestMock

    Args:
      resp: httplib2.Response, the response to emulate coming from the request
      content: string, the response body
      postproc: callable, the post processing function usually supplied by
                the model class. See model.JsonModel.response() as an example.
    """
    self.resp = resp
    self.content = content
    self.postproc = postproc
    if resp is None:
      self.resp = httplib2.Response({'status': 200, 'reason': 'OK'})
    if 'reason' in self.resp:
      self.resp.reason = self.resp['reason']

  def execute(self, http=None):
    """Execute the request.

    Same behavior as HttpRequest.execute(), but the response is
    mocked and not really from an HTTP request/response.
    """
    return self.postproc(self.resp, self.content)


class RequestMockBuilder(object):
  """A simple mock of HttpRequest

    Pass in a dictionary to the constructor that maps request methodIds to
    tuples of (httplib2.Response, content, opt_expected_body) that should be
    returned when that method is called. None may also be passed in for the
    httplib2.Response, in which case a 200 OK response will be generated.
    If an opt_expected_body (str or dict) is provided, it will be compared to
    the body and UnexpectedBodyError will be raised on inequality.

    Example:
      response = '{"data": {"id": "tag:google.c...'
      requestBuilder = RequestMockBuilder(
        {
          'plus.activities.get': (None, response),
        }
      )
      apiclient.discovery.build("plus", "v1", requestBuilder=requestBuilder)

    Methods that you do not supply a response for will return a
    200 OK with an empty string as the response content or raise an excpetion
    if check_unexpected is set to True. The methodId is taken from the rpcName
    in the discovery document.

    For more details see the project wiki.
  """

  def __init__(self, responses, check_unexpected=False):
    """Constructor for RequestMockBuilder

    The constructed object should be a callable object
    that can replace the class HttpResponse.

    responses - A dictionary that maps methodIds into tuples
                of (httplib2.Response, content). The methodId
                comes from the 'rpcName' field in the discovery
                document.
    check_unexpected - A boolean setting whether or not UnexpectedMethodError
                       should be raised on unsupplied method.
    """
    self.responses = responses
    self.check_unexpected = check_unexpected

  def __call__(self, http, postproc, uri, method='GET', body=None,
               headers=None, methodId=None, resumable=None):
    """Implements the callable interface that discovery.build() expects
    of requestBuilder, which is to build an object compatible with
    HttpRequest.execute(). See that method for the description of the
    parameters and the expected response.
    """
    if methodId in self.responses:
      response = self.responses[methodId]
      resp, content = response[:2]
      if len(response) > 2:
        # Test the body against the supplied expected_body.
        expected_body = response[2]
        if bool(expected_body) != bool(body):
          # Not expecting a body and provided one
          # or expecting a body and not provided one.
          raise UnexpectedBodyError(expected_body, body)
        if isinstance(expected_body, str):
          expected_body = simplejson.loads(expected_body)
        body = simplejson.loads(body)
        if body != expected_body:
          raise UnexpectedBodyError(expected_body, body)
      return HttpRequestMock(resp, content, postproc)
    elif self.check_unexpected:
      raise UnexpectedMethodError(methodId)
    else:
      model = JsonModel(False)
      return HttpRequestMock(None, '{}', model.response)


class HttpMock(object):
  """Mock of httplib2.Http"""

  def __init__(self, filename, headers=None):
    """
    Args:
      filename: string, absolute filename to read response from
      headers: dict, header to return with response
    """
    if headers is None:
      headers = {'status': '200 OK'}
    f = file(filename, 'r')
    self.data = f.read()
    f.close()
    self.headers = headers

  def request(self, uri,
              method='GET',
              body=None,
              headers=None,
              redirections=1,
              connection_type=None):
    return httplib2.Response(self.headers), self.data


class HttpMockSequence(object):
  """Mock of httplib2.Http

  Mocks a sequence of calls to request returning different responses for each
  call. Create an instance initialized with the desired response headers
  and content and then use as if an httplib2.Http instance.

    http = HttpMockSequence([
      ({'status': '401'}, ''),
      ({'status': '200'}, '{"access_token":"1/3w","expires_in":3600}'),
      ({'status': '200'}, 'echo_request_headers'),
      ])
    resp, content = http.request("http://examples.com")

  There are special values you can pass in for content to trigger
  behavours that are helpful in testing.

  'echo_request_headers' means return the request headers in the response body
  'echo_request_headers_as_json' means return the request headers in
     the response body
  'echo_request_body' means return the request body in the response body
  'echo_request_uri' means return the request uri in the response body
  """

  def __init__(self, iterable):
    """
    Args:
      iterable: iterable, a sequence of pairs of (headers, body)
    """
    self._iterable = iterable

  def request(self, uri,
              method='GET',
              body=None,
              headers=None,
              redirections=1,
              connection_type=None):
    resp, content = self._iterable.pop(0)
    if content == 'echo_request_headers':
      content = headers
    elif content == 'echo_request_headers_as_json':
      content = simplejson.dumps(headers)
    elif content == 'echo_request_body':
      content = body
    elif content == 'echo_request_uri':
      content = uri
    return httplib2.Response(resp), content


def set_user_agent(http, user_agent):
  """Set the user-agent on every request.

  Args:
     http - An instance of httplib2.Http
         or something that acts like it.
     user_agent: string, the value for the user-agent header.

  Returns:
     A modified instance of http that was passed in.

  Example:

    h = httplib2.Http()
    h = set_user_agent(h, "my-app-name/6.0")

  Most of the time the user-agent will be set doing auth, this is for the rare
  cases where you are accessing an unauthenticated endpoint.
  """
  request_orig = http.request

  # The closure that will replace 'httplib2.Http.request'.
  def new_request(uri, method='GET', body=None, headers=None,
                  redirections=httplib2.DEFAULT_MAX_REDIRECTS,
                  connection_type=None):
    """Modify the request headers to add the user-agent."""
    if headers is None:
      headers = {}
    if 'user-agent' in headers:
      headers['user-agent'] = user_agent + ' ' + headers['user-agent']
    else:
      headers['user-agent'] = user_agent
    resp, content = request_orig(uri, method, body, headers,
                        redirections, connection_type)
    return resp, content

  http.request = new_request
  return http


def tunnel_patch(http):
  """Tunnel PATCH requests over POST.
  Args:
     http - An instance of httplib2.Http
         or something that acts like it.

  Returns:
     A modified instance of http that was passed in.

  Example:

    h = httplib2.Http()
    h = tunnel_patch(h, "my-app-name/6.0")

  Useful if you are running on a platform that doesn't support PATCH.
  Apply this last if you are using OAuth 1.0, as changing the method
  will result in a different signature.
  """
  request_orig = http.request

  # The closure that will replace 'httplib2.Http.request'.
  def new_request(uri, method='GET', body=None, headers=None,
                  redirections=httplib2.DEFAULT_MAX_REDIRECTS,
                  connection_type=None):
    """Modify the request headers to add the user-agent."""
    if headers is None:
      headers = {}
    if method == 'PATCH':
      if 'oauth_token' in headers.get('authorization', ''):
        logging.warning(
            'OAuth 1.0 request made with Credentials after tunnel_patch.')
      headers['x-http-method-override'] = "PATCH"
      method = 'POST'
    resp, content = request_orig(uri, method, body, headers,
                        redirections, connection_type)
    return resp, content

  http.request = new_request
  return http

########NEW FILE########
__FILENAME__ = mimeparse
# Copyright (C) 2007 Joe Gregorio
#
# Licensed under the MIT License

"""MIME-Type Parser

This module provides basic functions for handling mime-types. It can handle
matching mime-types against a list of media-ranges. See section 14.1 of the
HTTP specification [RFC 2616] for a complete explanation.

   http://www.w3.org/Protocols/rfc2616/rfc2616-sec14.html#sec14.1

Contents:
 - parse_mime_type():   Parses a mime-type into its component parts.
 - parse_media_range(): Media-ranges are mime-types with wild-cards and a 'q'
                          quality parameter.
 - quality():           Determines the quality ('q') of a mime-type when
                          compared against a list of media-ranges.
 - quality_parsed():    Just like quality() except the second parameter must be
                          pre-parsed.
 - best_match():        Choose the mime-type with the highest quality ('q')
                          from a list of candidates.
"""

__version__ = '0.1.3'
__author__ = 'Joe Gregorio'
__email__ = 'joe@bitworking.org'
__license__ = 'MIT License'
__credits__ = ''


def parse_mime_type(mime_type):
    """Parses a mime-type into its component parts.

    Carves up a mime-type and returns a tuple of the (type, subtype, params)
    where 'params' is a dictionary of all the parameters for the media range.
    For example, the media range 'application/xhtml;q=0.5' would get parsed
    into:

       ('application', 'xhtml', {'q', '0.5'})
       """
    parts = mime_type.split(';')
    params = dict([tuple([s.strip() for s in param.split('=', 1)])\
            for param in parts[1:]
                  ])
    full_type = parts[0].strip()
    # Java URLConnection class sends an Accept header that includes a
    # single '*'. Turn it into a legal wildcard.
    if full_type == '*':
        full_type = '*/*'
    (type, subtype) = full_type.split('/')

    return (type.strip(), subtype.strip(), params)


def parse_media_range(range):
    """Parse a media-range into its component parts.

    Carves up a media range and returns a tuple of the (type, subtype,
    params) where 'params' is a dictionary of all the parameters for the media
    range.  For example, the media range 'application/*;q=0.5' would get parsed
    into:

       ('application', '*', {'q', '0.5'})

    In addition this function also guarantees that there is a value for 'q'
    in the params dictionary, filling it in with a proper default if
    necessary.
    """
    (type, subtype, params) = parse_mime_type(range)
    if not params.has_key('q') or not params['q'] or \
            not float(params['q']) or float(params['q']) > 1\
            or float(params['q']) < 0:
        params['q'] = '1'

    return (type, subtype, params)


def fitness_and_quality_parsed(mime_type, parsed_ranges):
    """Find the best match for a mime-type amongst parsed media-ranges.

    Find the best match for a given mime-type against a list of media_ranges
    that have already been parsed by parse_media_range(). Returns a tuple of
    the fitness value and the value of the 'q' quality parameter of the best
    match, or (-1, 0) if no match was found. Just as for quality_parsed(),
    'parsed_ranges' must be a list of parsed media ranges.
    """
    best_fitness = -1
    best_fit_q = 0
    (target_type, target_subtype, target_params) =\
            parse_media_range(mime_type)
    for (type, subtype, params) in parsed_ranges:
        type_match = (type == target_type or\
                      type == '*' or\
                      target_type == '*')
        subtype_match = (subtype == target_subtype or\
                         subtype == '*' or\
                         target_subtype == '*')
        if type_match and subtype_match:
            param_matches = reduce(lambda x, y: x + y, [1 for (key, value) in \
                    target_params.iteritems() if key != 'q' and \
                    params.has_key(key) and value == params[key]], 0)
            fitness = (type == target_type) and 100 or 0
            fitness += (subtype == target_subtype) and 10 or 0
            fitness += param_matches
            if fitness > best_fitness:
                best_fitness = fitness
                best_fit_q = params['q']

    return best_fitness, float(best_fit_q)


def quality_parsed(mime_type, parsed_ranges):
    """Find the best match for a mime-type amongst parsed media-ranges.

    Find the best match for a given mime-type against a list of media_ranges
    that have already been parsed by parse_media_range(). Returns the 'q'
    quality parameter of the best match, 0 if no match was found. This function
    bahaves the same as quality() except that 'parsed_ranges' must be a list of
    parsed media ranges.
    """

    return fitness_and_quality_parsed(mime_type, parsed_ranges)[1]


def quality(mime_type, ranges):
    """Return the quality ('q') of a mime-type against a list of media-ranges.

    Returns the quality 'q' of a mime-type when compared against the
    media-ranges in ranges. For example:

    >>> quality('text/html','text/*;q=0.3, text/html;q=0.7,
                  text/html;level=1, text/html;level=2;q=0.4, */*;q=0.5')
    0.7

    """
    parsed_ranges = [parse_media_range(r) for r in ranges.split(',')]

    return quality_parsed(mime_type, parsed_ranges)


def best_match(supported, header):
    """Return mime-type with the highest quality ('q') from list of candidates.

    Takes a list of supported mime-types and finds the best match for all the
    media-ranges listed in header. The value of header must be a string that
    conforms to the format of the HTTP Accept: header. The value of 'supported'
    is a list of mime-types. The list of supported mime-types should be sorted
    in order of increasing desirability, in case of a situation where there is
    a tie.

    >>> best_match(['application/xbel+xml', 'text/xml'],
                   'text/*;q=0.5,*/*; q=0.1')
    'text/xml'
    """
    split_header = _filter_blank(header.split(','))
    parsed_header = [parse_media_range(r) for r in split_header]
    weighted_matches = []
    pos = 0
    for mime_type in supported:
        weighted_matches.append((fitness_and_quality_parsed(mime_type,
                                 parsed_header), pos, mime_type))
        pos += 1
    weighted_matches.sort()

    return weighted_matches[-1][0][1] and weighted_matches[-1][2] or ''


def _filter_blank(i):
    for s in i:
        if s.strip():
            yield s

########NEW FILE########
__FILENAME__ = model
#!/usr/bin/python2.4
#
# Copyright (C) 2010 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Model objects for requests and responses.

Each API may support one or more serializations, such
as JSON, Atom, etc. The model classes are responsible
for converting between the wire format and the Python
object representation.
"""

__author__ = 'jcgregorio@google.com (Joe Gregorio)'

# import gflags
import logging
import urllib

from errors import HttpError
from oauth2client.anyjson import simplejson

# FLAGS = gflags.FLAGS

# gflags.DEFINE_boolean('dump_request_response', False,
                      # 'Dump all http server requests and responses. '
                     # )


def _abstract():
  raise NotImplementedError('You need to override this function')


class Model(object):
  """Model base class.

  All Model classes should implement this interface.
  The Model serializes and de-serializes between a wire
  format such as JSON and a Python object representation.
  """

  def request(self, headers, path_params, query_params, body_value):
    """Updates outgoing requests with a serialized body.

    Args:
      headers: dict, request headers
      path_params: dict, parameters that appear in the request path
      query_params: dict, parameters that appear in the query
      body_value: object, the request body as a Python object, which must be
                  serializable.
    Returns:
      A tuple of (headers, path_params, query, body)

      headers: dict, request headers
      path_params: dict, parameters that appear in the request path
      query: string, query part of the request URI
      body: string, the body serialized in the desired wire format.
    """
    _abstract()

  def response(self, resp, content):
    """Convert the response wire format into a Python object.

    Args:
      resp: httplib2.Response, the HTTP response headers and status
      content: string, the body of the HTTP response

    Returns:
      The body de-serialized as a Python object.

    Raises:
      apiclient.errors.HttpError if a non 2xx response is received.
    """
    _abstract()


class BaseModel(Model):
  """Base model class.

  Subclasses should provide implementations for the "serialize" and
  "deserialize" methods, as well as values for the following class attributes.

  Attributes:
    accept: The value to use for the HTTP Accept header.
    content_type: The value to use for the HTTP Content-type header.
    no_content_response: The value to return when deserializing a 204 "No
        Content" response.
    alt_param: The value to supply as the "alt" query parameter for requests.
  """

  accept = None
  content_type = None
  no_content_response = None
  alt_param = None

  def _log_request(self, headers, path_params, query, body):
    """Logs debugging information about the request if requested."""
    # if FLAGS.dump_request_response:
    logging.info('--request-start--')
    logging.info('-headers-start-')
    for h, v in headers.iteritems():
      logging.info('%s: %s', h, v)
    logging.info('-headers-end-')
    logging.info('-path-parameters-start-')
    for h, v in path_params.iteritems():
      logging.info('%s: %s', h, v)
    logging.info('-path-parameters-end-')
    logging.info('body: %s', body)
    logging.info('query: %s', query)
    logging.info('--request-end--')

  def request(self, headers, path_params, query_params, body_value):
    """Updates outgoing requests with a serialized body.

    Args:
      headers: dict, request headers
      path_params: dict, parameters that appear in the request path
      query_params: dict, parameters that appear in the query
      body_value: object, the request body as a Python object, which must be
                  serializable by simplejson.
    Returns:
      A tuple of (headers, path_params, query, body)

      headers: dict, request headers
      path_params: dict, parameters that appear in the request path
      query: string, query part of the request URI
      body: string, the body serialized as JSON
    """
    query = self._build_query(query_params)
    headers['accept'] = self.accept
    headers['accept-encoding'] = 'gzip, deflate'
    if 'user-agent' in headers:
      headers['user-agent'] += ' '
    else:
      headers['user-agent'] = ''
    headers['user-agent'] += 'google-api-python-client/1.0'

    if body_value is not None:
      headers['content-type'] = self.content_type
      body_value = self.serialize(body_value)
    self._log_request(headers, path_params, query, body_value)
    return (headers, path_params, query, body_value)

  def _build_query(self, params):
    """Builds a query string.

    Args:
      params: dict, the query parameters

    Returns:
      The query parameters properly encoded into an HTTP URI query string.
    """
    if self.alt_param is not None:
      params.update({'alt': self.alt_param})
    astuples = []
    for key, value in params.iteritems():
      if type(value) == type([]):
        for x in value:
          x = x.encode('utf-8')
          astuples.append((key, x))
      else:
        if getattr(value, 'encode', False) and callable(value.encode):
          value = value.encode('utf-8')
        astuples.append((key, value))
    return '?' + urllib.urlencode(astuples)

  def _log_response(self, resp, content):
    """Logs debugging information about the response if requested."""
    # if FLAGS.dump_request_response:
    logging.info('--response-start--')
    for h, v in resp.iteritems():
      logging.info('%s: %s', h, v)
    if content:
      logging.info(content)
    logging.info('--response-end--')

  def response(self, resp, content):
    """Convert the response wire format into a Python object.

    Args:
      resp: httplib2.Response, the HTTP response headers and status
      content: string, the body of the HTTP response

    Returns:
      The body de-serialized as a Python object.

    Raises:
      apiclient.errors.HttpError if a non 2xx response is received.
    """
    self._log_response(resp, content)
    # Error handling is TBD, for example, do we retry
    # for some operation/error combinations?
    if resp.status < 300:
      if resp.status == 204:
        # A 204: No Content response should be treated differently
        # to all the other success states
        return self.no_content_response
      return self.deserialize(content)
    else:
      logging.debug('Content from bad request was: %s' % content)
      raise HttpError(resp, content)

  def serialize(self, body_value):
    """Perform the actual Python object serialization.

    Args:
      body_value: object, the request body as a Python object.

    Returns:
      string, the body in serialized form.
    """
    _abstract()

  def deserialize(self, content):
    """Perform the actual deserialization from response string to Python
    object.

    Args:
      content: string, the body of the HTTP response

    Returns:
      The body de-serialized as a Python object.
    """
    _abstract()


class JsonModel(BaseModel):
  """Model class for JSON.

  Serializes and de-serializes between JSON and the Python
  object representation of HTTP request and response bodies.
  """
  accept = 'application/json'
  content_type = 'application/json'
  alt_param = 'json'

  def __init__(self, data_wrapper=False):
    """Construct a JsonModel.

    Args:
      data_wrapper: boolean, wrap requests and responses in a data wrapper
    """
    self._data_wrapper = data_wrapper

  def serialize(self, body_value):
    if (isinstance(body_value, dict) and 'data' not in body_value and
        self._data_wrapper):
      body_value = {'data': body_value}
    return simplejson.dumps(body_value)

  def deserialize(self, content):
    body = simplejson.loads(content)
    if isinstance(body, dict) and 'data' in body:
      body = body['data']
    return body

  @property
  def no_content_response(self):
    return {}


class RawModel(JsonModel):
  """Model class for requests that don't return JSON.

  Serializes and de-serializes between JSON and the Python
  object representation of HTTP request, and returns the raw bytes
  of the response body.
  """
  accept = '*/*'
  content_type = 'application/json'
  alt_param = None

  def deserialize(self, content):
    return content

  @property
  def no_content_response(self):
    return ''


class ProtocolBufferModel(BaseModel):
  """Model class for protocol buffers.

  Serializes and de-serializes the binary protocol buffer sent in the HTTP
  request and response bodies.
  """
  accept = 'application/x-protobuf'
  content_type = 'application/x-protobuf'
  alt_param = 'proto'

  def __init__(self, protocol_buffer):
    """Constructs a ProtocolBufferModel.

    The serialzed protocol buffer returned in an HTTP response will be
    de-serialized using the given protocol buffer class.

    Args:
      protocol_buffer: The protocol buffer class used to de-serialize a
      response from the API.
    """
    self._protocol_buffer = protocol_buffer

  def serialize(self, body_value):
    return body_value.SerializeToString()

  def deserialize(self, content):
    return self._protocol_buffer.FromString(content)

  @property
  def no_content_response(self):
    return self._protocol_buffer()


def makepatch(original, modified):
  """Create a patch object.

  Some methods support PATCH, an efficient way to send updates to a resource.
  This method allows the easy construction of patch bodies by looking at the
  differences between a resource before and after it was modified.

  Args:
    original: object, the original deserialized resource
    modified: object, the modified deserialized resource
  Returns:
    An object that contains only the changes from original to modified, in a
    form suitable to pass to a PATCH method.

  Example usage:
    item = service.activities().get(postid=postid, userid=userid).execute()
    original = copy.deepcopy(item)
    item['object']['content'] = 'This is updated.'
    service.activities.patch(postid=postid, userid=userid,
      body=makepatch(original, item)).execute()
  """
  patch = {}
  for key, original_value in original.iteritems():
    modified_value = modified.get(key, None)
    if modified_value is None:
      # Use None to signal that the element is deleted
      patch[key] = None
    elif original_value != modified_value:
      if type(original_value) == type({}):
        # Recursively descend objects
        patch[key] = makepatch(original_value, modified_value)
      else:
        # In the case of simple types or arrays we just replace
        patch[key] = modified_value
    else:
      # Don't add anything to patch if there's no change
      pass
  for key in modified:
    if key not in original:
      patch[key] = modified[key]

  return patch

########NEW FILE########
__FILENAME__ = oauth
# Copyright (C) 2010 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Utilities for OAuth.

Utilities for making it easier to work with OAuth.
"""

__author__ = 'jcgregorio@google.com (Joe Gregorio)'


import copy
import httplib2
import logging
import oauth2 as oauth
import urllib
import urlparse

from oauth2client.anyjson import simplejson
from oauth2client.client import Credentials
from oauth2client.client import Flow
from oauth2client.client import Storage

try:
  from urlparse import parse_qsl
except ImportError:
  from cgi import parse_qsl


class Error(Exception):
  """Base error for this module."""
  pass


class RequestError(Error):
  """Error occurred during request."""
  pass


class MissingParameter(Error):
  pass


class CredentialsInvalidError(Error):
  pass


def _abstract():
  raise NotImplementedError('You need to override this function')


def _oauth_uri(name, discovery, params):
  """Look up the OAuth URI from the discovery
  document and add query parameters based on
  params.

  name      - The name of the OAuth URI to lookup, one
              of 'request', 'access', or 'authorize'.
  discovery - Portion of discovery document the describes
              the OAuth endpoints.
  params    - Dictionary that is used to form the query parameters
              for the specified URI.
  """
  if name not in ['request', 'access', 'authorize']:
    raise KeyError(name)
  keys = discovery[name]['parameters'].keys()
  query = {}
  for key in keys:
    if key in params:
      query[key] = params[key]
  return discovery[name]['url'] + '?' + urllib.urlencode(query)



class OAuthCredentials(Credentials):
  """Credentials object for OAuth 1.0a
  """

  def __init__(self, consumer, token, user_agent):
    """
    consumer   - An instance of oauth.Consumer.
    token      - An instance of oauth.Token constructed with
                 the access token and secret.
    user_agent - The HTTP User-Agent to provide for this application.
    """
    self.consumer = consumer
    self.token = token
    self.user_agent = user_agent
    self.store = None

    # True if the credentials have been revoked
    self._invalid = False

  @property
  def invalid(self):
    """True if the credentials are invalid, such as being revoked."""
    return getattr(self, "_invalid", False)

  def set_store(self, store):
    """Set the storage for the credential.

    Args:
      store: callable, a callable that when passed a Credential
        will store the credential back to where it came from.
        This is needed to store the latest access_token if it
        has been revoked.
    """
    self.store = store

  def __getstate__(self):
    """Trim the state down to something that can be pickled."""
    d = copy.copy(self.__dict__)
    del d['store']
    return d

  def __setstate__(self, state):
    """Reconstitute the state of the object from being pickled."""
    self.__dict__.update(state)
    self.store = None

  def authorize(self, http):
    """Authorize an httplib2.Http instance with these Credentials

    Args:
       http - An instance of httplib2.Http
           or something that acts like it.

    Returns:
       A modified instance of http that was passed in.

    Example:

      h = httplib2.Http()
      h = credentials.authorize(h)

    You can't create a new OAuth
    subclass of httplib2.Authenication because
    it never gets passed the absolute URI, which is
    needed for signing. So instead we have to overload
    'request' with a closure that adds in the
    Authorization header and then calls the original version
    of 'request()'.
    """
    request_orig = http.request
    signer = oauth.SignatureMethod_HMAC_SHA1()

    # The closure that will replace 'httplib2.Http.request'.
    def new_request(uri, method='GET', body=None, headers=None,
                    redirections=httplib2.DEFAULT_MAX_REDIRECTS,
                    connection_type=None):
      """Modify the request headers to add the appropriate
      Authorization header."""
      response_code = 302
      http.follow_redirects = False
      while response_code in [301, 302]:
        req = oauth.Request.from_consumer_and_token(
            self.consumer, self.token, http_method=method, http_url=uri)
        req.sign_request(signer, self.consumer, self.token)
        if headers is None:
          headers = {}
        headers.update(req.to_header())
        if 'user-agent' in headers:
          headers['user-agent'] = self.user_agent + ' ' + headers['user-agent']
        else:
          headers['user-agent'] = self.user_agent

        resp, content = request_orig(uri, method, body, headers,
                            redirections, connection_type)
        response_code = resp.status
        if response_code in [301, 302]:
          uri = resp['location']

      # Update the stored credential if it becomes invalid.
      if response_code == 401:
        logging.info('Access token no longer valid: %s' % content)
        self._invalid = True
        if self.store is not None:
          self.store(self)
        raise CredentialsInvalidError("Credentials are no longer valid.")

      return resp, content

    http.request = new_request
    return http


class TwoLeggedOAuthCredentials(Credentials):
  """Two Legged Credentials object for OAuth 1.0a.

  The Two Legged object is created directly, not from a flow.  Once you
  authorize and httplib2.Http instance you can change the requestor and that
  change will propogate to the authorized httplib2.Http instance. For example:

    http = httplib2.Http()
    http = credentials.authorize(http)

    credentials.requestor = 'foo@example.info'
    http.request(...)
    credentials.requestor = 'bar@example.info'
    http.request(...)
  """

  def __init__(self, consumer_key, consumer_secret, user_agent):
    """
    Args:
      consumer_key: string, An OAuth 1.0 consumer key
      consumer_secret: string, An OAuth 1.0 consumer secret
      user_agent: string, The HTTP User-Agent to provide for this application.
    """
    self.consumer = oauth.Consumer(consumer_key, consumer_secret)
    self.user_agent = user_agent
    self.store = None

    # email address of the user to act on the behalf of.
    self._requestor = None

  @property
  def invalid(self):
    """True if the credentials are invalid, such as being revoked.

    Always returns False for Two Legged Credentials.
    """
    return False

  def getrequestor(self):
    return self._requestor

  def setrequestor(self, email):
    self._requestor = email

  requestor = property(getrequestor, setrequestor, None,
      'The email address of the user to act on behalf of')

  def set_store(self, store):
    """Set the storage for the credential.

    Args:
      store: callable, a callable that when passed a Credential
        will store the credential back to where it came from.
        This is needed to store the latest access_token if it
        has been revoked.
    """
    self.store = store

  def __getstate__(self):
    """Trim the state down to something that can be pickled."""
    d = copy.copy(self.__dict__)
    del d['store']
    return d

  def __setstate__(self, state):
    """Reconstitute the state of the object from being pickled."""
    self.__dict__.update(state)
    self.store = None

  def authorize(self, http):
    """Authorize an httplib2.Http instance with these Credentials

    Args:
       http - An instance of httplib2.Http
           or something that acts like it.

    Returns:
       A modified instance of http that was passed in.

    Example:

      h = httplib2.Http()
      h = credentials.authorize(h)

    You can't create a new OAuth
    subclass of httplib2.Authenication because
    it never gets passed the absolute URI, which is
    needed for signing. So instead we have to overload
    'request' with a closure that adds in the
    Authorization header and then calls the original version
    of 'request()'.
    """
    request_orig = http.request
    signer = oauth.SignatureMethod_HMAC_SHA1()

    # The closure that will replace 'httplib2.Http.request'.
    def new_request(uri, method='GET', body=None, headers=None,
                    redirections=httplib2.DEFAULT_MAX_REDIRECTS,
                    connection_type=None):
      """Modify the request headers to add the appropriate
      Authorization header."""
      response_code = 302
      http.follow_redirects = False
      while response_code in [301, 302]:
        # add in xoauth_requestor_id=self._requestor to the uri
        if self._requestor is None:
          raise MissingParameter(
              'Requestor must be set before using TwoLeggedOAuthCredentials')
        parsed = list(urlparse.urlparse(uri))
        q = parse_qsl(parsed[4])
        q.append(('xoauth_requestor_id', self._requestor))
        parsed[4] = urllib.urlencode(q)
        uri = urlparse.urlunparse(parsed)

        req = oauth.Request.from_consumer_and_token(
            self.consumer, None, http_method=method, http_url=uri)
        req.sign_request(signer, self.consumer, None)
        if headers is None:
          headers = {}
        headers.update(req.to_header())
        if 'user-agent' in headers:
          headers['user-agent'] = self.user_agent + ' ' + headers['user-agent']
        else:
          headers['user-agent'] = self.user_agent
        resp, content = request_orig(uri, method, body, headers,
                            redirections, connection_type)
        response_code = resp.status
        if response_code in [301, 302]:
          uri = resp['location']

      if response_code == 401:
        logging.info('Access token no longer valid: %s' % content)
        # Do not store the invalid state of the Credentials because
        # being 2LO they could be reinstated in the future.
        raise CredentialsInvalidError("Credentials are invalid.")

      return resp, content

    http.request = new_request
    return http


class FlowThreeLegged(Flow):
  """Does the Three Legged Dance for OAuth 1.0a.
  """

  def __init__(self, discovery, consumer_key, consumer_secret, user_agent,
               **kwargs):
    """
    discovery       - Section of the API discovery document that describes
                      the OAuth endpoints.
    consumer_key    - OAuth consumer key
    consumer_secret - OAuth consumer secret
    user_agent      - The HTTP User-Agent that identifies the application.
    **kwargs        - The keyword arguments are all optional and required
                      parameters for the OAuth calls.
    """
    self.discovery = discovery
    self.consumer_key = consumer_key
    self.consumer_secret = consumer_secret
    self.user_agent = user_agent
    self.params = kwargs
    self.request_token = {}
    required = {}
    for uriinfo in discovery.itervalues():
      for name, value in uriinfo['parameters'].iteritems():
        if value['required'] and not name.startswith('oauth_'):
          required[name] = 1
    for key in required.iterkeys():
      if key not in self.params:
        raise MissingParameter('Required parameter %s not supplied' % key)

  def step1_get_authorize_url(self, oauth_callback='oob'):
    """Returns a URI to redirect to the provider.

    oauth_callback - Either the string 'oob' for a non-web-based application,
                     or a URI that handles the callback from the authorization
                     server.

    If oauth_callback is 'oob' then pass in the
    generated verification code to step2_exchange,
    otherwise pass in the query parameters received
    at the callback uri to step2_exchange.
    """
    consumer = oauth.Consumer(self.consumer_key, self.consumer_secret)
    client = oauth.Client(consumer)

    headers = {
        'user-agent': self.user_agent,
        'content-type': 'application/x-www-form-urlencoded'
    }
    body = urllib.urlencode({'oauth_callback': oauth_callback})
    uri = _oauth_uri('request', self.discovery, self.params)

    resp, content = client.request(uri, 'POST', headers=headers,
                                   body=body)
    if resp['status'] != '200':
      logging.error('Failed to retrieve temporary authorization: %s', content)
      raise RequestError('Invalid response %s.' % resp['status'])

    self.request_token = dict(parse_qsl(content))

    auth_params = copy.copy(self.params)
    auth_params['oauth_token'] = self.request_token['oauth_token']

    return _oauth_uri('authorize', self.discovery, auth_params)

  def step2_exchange(self, verifier):
    """Exhanges an authorized request token
    for OAuthCredentials.

    Args:
      verifier: string, dict - either the verifier token, or a dictionary
        of the query parameters to the callback, which contains
        the oauth_verifier.
    Returns:
       The Credentials object.
    """

    if not (isinstance(verifier, str) or isinstance(verifier, unicode)):
      verifier = verifier['oauth_verifier']

    token = oauth.Token(
        self.request_token['oauth_token'],
        self.request_token['oauth_token_secret'])
    token.set_verifier(verifier)
    consumer = oauth.Consumer(self.consumer_key, self.consumer_secret)
    client = oauth.Client(consumer, token)

    headers = {
        'user-agent': self.user_agent,
        'content-type': 'application/x-www-form-urlencoded'
    }

    uri = _oauth_uri('access', self.discovery, self.params)
    resp, content = client.request(uri, 'POST', headers=headers)
    if resp['status'] != '200':
      logging.error('Failed to retrieve access token: %s', content)
      raise RequestError('Invalid response %s.' % resp['status'])

    oauth_params = dict(parse_qsl(content))
    token = oauth.Token(
        oauth_params['oauth_token'],
        oauth_params['oauth_token_secret'])

    return OAuthCredentials(consumer, token, self.user_agent)

########NEW FILE########
__FILENAME__ = schema
# Copyright (C) 2010 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Schema processing for discovery based APIs

Schemas holds an APIs discovery schemas. It can return those schema as
deserialized JSON objects, or pretty print them as prototype objects that
conform to the schema.

For example, given the schema:

 schema = \"\"\"{
   "Foo": {
    "type": "object",
    "properties": {
     "etag": {
      "type": "string",
      "description": "ETag of the collection."
     },
     "kind": {
      "type": "string",
      "description": "Type of the collection ('calendar#acl').",
      "default": "calendar#acl"
     },
     "nextPageToken": {
      "type": "string",
      "description": "Token used to access the next
         page of this result. Omitted if no further results are available."
     }
    }
   }
 }\"\"\"

 s = Schemas(schema)
 print s.prettyPrintByName('Foo')

 Produces the following output:

  {
   "nextPageToken": "A String", # Token used to access the
       # next page of this result. Omitted if no further results are available.
   "kind": "A String", # Type of the collection ('calendar#acl').
   "etag": "A String", # ETag of the collection.
  },

The constructor takes a discovery document in which to look up named schema.
"""

# TODO(jcgregorio) support format, enum, minimum, maximum

__author__ = 'jcgregorio@google.com (Joe Gregorio)'

import copy
from oauth2client.anyjson import simplejson


class Schemas(object):
  """Schemas for an API."""

  def __init__(self, discovery):
    """Constructor.

    Args:
      discovery: object, Deserialized discovery document from which we pull
        out the named schema.
    """
    self.schemas = discovery.get('schemas', {})

    # Cache of pretty printed schemas.
    self.pretty = {}

  def _prettyPrintByName(self, name, seen=None, dent=0):
    """Get pretty printed object prototype from the schema name.

    Args:
      name: string, Name of schema in the discovery document.
      seen: list of string, Names of schema already seen. Used to handle
        recursive definitions.

    Returns:
      string, A string that contains a prototype object with
        comments that conforms to the given schema.
    """
    if seen is None:
      seen = []

    if name in seen:
      # Do not fall into an infinite loop over recursive definitions.
      return '# Object with schema name: %s' % name
    seen.append(name)

    if name not in self.pretty:
      self.pretty[name] = _SchemaToStruct(self.schemas[name],
          seen, dent).to_str(self._prettyPrintByName)

    seen.pop()

    return self.pretty[name]

  def prettyPrintByName(self, name):
    """Get pretty printed object prototype from the schema name.

    Args:
      name: string, Name of schema in the discovery document.

    Returns:
      string, A string that contains a prototype object with
        comments that conforms to the given schema.
    """
    # Return with trailing comma and newline removed.
    return self._prettyPrintByName(name, seen=[], dent=1)[:-2]

  def _prettyPrintSchema(self, schema, seen=None, dent=0):
    """Get pretty printed object prototype of schema.

    Args:
      schema: object, Parsed JSON schema.
      seen: list of string, Names of schema already seen. Used to handle
        recursive definitions.

    Returns:
      string, A string that contains a prototype object with
        comments that conforms to the given schema.
    """
    if seen is None:
      seen = []

    return _SchemaToStruct(schema, seen, dent).to_str(self._prettyPrintByName)

  def prettyPrintSchema(self, schema):
    """Get pretty printed object prototype of schema.

    Args:
      schema: object, Parsed JSON schema.

    Returns:
      string, A string that contains a prototype object with
        comments that conforms to the given schema.
    """
    # Return with trailing comma and newline removed.
    return self._prettyPrintSchema(schema, dent=1)[:-2]

  def get(self, name):
    """Get deserialized JSON schema from the schema name.

    Args:
      name: string, Schema name.
    """
    return self.schemas[name]


class _SchemaToStruct(object):
  """Convert schema to a prototype object."""

  def __init__(self, schema, seen, dent=0):
    """Constructor.

    Args:
      schema: object, Parsed JSON schema.
      seen: list, List of names of schema already seen while parsing. Used to
        handle recursive definitions.
      dent: int, Initial indentation depth.
    """
    # The result of this parsing kept as list of strings.
    self.value = []

    # The final value of the parsing.
    self.string = None

    # The parsed JSON schema.
    self.schema = schema

    # Indentation level.
    self.dent = dent

    # Method that when called returns a prototype object for the schema with
    # the given name.
    self.from_cache = None

    # List of names of schema already seen while parsing.
    self.seen = seen

  def emit(self, text):
    """Add text as a line to the output.

    Args:
      text: string, Text to output.
    """
    self.value.extend(["  " * self.dent, text, '\n'])

  def emitBegin(self, text):
    """Add text to the output, but with no line terminator.

    Args:
      text: string, Text to output.
      """
    self.value.extend(["  " * self.dent, text])

  def emitEnd(self, text, comment):
    """Add text and comment to the output with line terminator.

    Args:
      text: string, Text to output.
      comment: string, Python comment.
    """
    if comment:
      divider = '\n' + '  ' * (self.dent + 2) + '# '
      lines = comment.splitlines()
      lines = [x.rstrip() for x in lines]
      comment = divider.join(lines)
      self.value.extend([text, ' # ', comment, '\n'])
    else:
      self.value.extend([text, '\n'])

  def indent(self):
    """Increase indentation level."""
    self.dent += 1

  def undent(self):
    """Decrease indentation level."""
    self.dent -= 1

  def _to_str_impl(self, schema):
    """Prototype object based on the schema, in Python code with comments.

    Args:
      schema: object, Parsed JSON schema file.

    Returns:
      Prototype object based on the schema, in Python code with comments.
    """
    stype = schema.get('type')
    if stype == 'object':
      self.emitEnd('{', schema.get('description', ''))
      self.indent()
      for pname, pschema in schema.get('properties', {}).iteritems():
        self.emitBegin('"%s": ' % pname)
        self._to_str_impl(pschema)
      self.undent()
      self.emit('},')
    elif '$ref' in schema:
      schemaName = schema['$ref']
      description = schema.get('description', '')
      s = self.from_cache(schemaName, self.seen)
      parts = s.splitlines()
      self.emitEnd(parts[0], description)
      for line in parts[1:]:
        self.emit(line.rstrip())
    elif stype == 'boolean':
      value = schema.get('default', 'True or False')
      self.emitEnd('%s,' % str(value), schema.get('description', ''))
    elif stype == 'string':
      value = schema.get('default', 'A String')
      self.emitEnd('"%s",' % str(value), schema.get('description', ''))
    elif stype == 'integer':
      value = schema.get('default', '42')
      self.emitEnd('%s,' % str(value), schema.get('description', ''))
    elif stype == 'number':
      value = schema.get('default', '3.14')
      self.emitEnd('%s,' % str(value), schema.get('description', ''))
    elif stype == 'null':
      self.emitEnd('None,', schema.get('description', ''))
    elif stype == 'any':
      self.emitEnd('"",', schema.get('description', ''))
    elif stype == 'array':
      self.emitEnd('[', schema.get('description'))
      self.indent()
      self.emitBegin('')
      self._to_str_impl(schema['items'])
      self.undent()
      self.emit('],')
    else:
      self.emit('Unknown type! %s' % stype)
      self.emitEnd('', '')

    self.string = ''.join(self.value)
    return self.string

  def to_str(self, from_cache):
    """Prototype object based on the schema, in Python code with comments.

    Args:
      from_cache: callable(name, seen), Callable that retrieves an object
         prototype for a schema with the given name. Seen is a list of schema
         names already seen as we recursively descend the schema definition.

    Returns:
      Prototype object based on the schema, in Python code with comments.
      The lines of the code will all be properly indented.
    """
    self.from_cache = from_cache
    return self._to_str_impl(self.schema)

########NEW FILE########
__FILENAME__ = anyjson
# Copyright (C) 2010 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Utility module to import a JSON module

Hides all the messy details of exactly where
we get a simplejson module from.
"""

__author__ = 'jcgregorio@google.com (Joe Gregorio)'


try: # pragma: no cover
  # Should work for Python2.6 and higher.
  import json as simplejson
except ImportError: # pragma: no cover
  try:
    import simplejson
  except ImportError:
    # Try to import from django, should work on App Engine
    from django.utils import simplejson

########NEW FILE########
__FILENAME__ = appengine
# Copyright (C) 2010 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Utilities for Google App Engine

Utilities for making it easier to use OAuth 2.0 on Google App Engine.
"""

__author__ = 'jcgregorio@google.com (Joe Gregorio)'

import base64
import httplib2
import logging
import pickle
import time

import clientsecrets

from anyjson import simplejson
from client import AccessTokenRefreshError
from client import AssertionCredentials
from client import Credentials
from client import Flow
from client import OAuth2WebServerFlow
from client import Storage
from google.appengine.api import memcache
from google.appengine.api import users
from google.appengine.api import app_identity
from google.appengine.ext import db
from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import login_required
from google.appengine.ext.webapp.util import run_wsgi_app

OAUTH2CLIENT_NAMESPACE = 'oauth2client#ns'


class InvalidClientSecretsError(Exception):
  """The client_secrets.json file is malformed or missing required fields."""
  pass


class AppAssertionCredentials(AssertionCredentials):
  """Credentials object for App Engine Assertion Grants

  This object will allow an App Engine application to identify itself to Google
  and other OAuth 2.0 servers that can verify assertions. It can be used for
  the purpose of accessing data stored under an account assigned to the App
  Engine application itself.

  This credential does not require a flow to instantiate because it represents
  a two legged flow, and therefore has all of the required information to
  generate and refresh its own access tokens.
  """

  def __init__(self, scope, **kwargs):
    """Constructor for AppAssertionCredentials

    Args:
      scope: string or list of strings, scope(s) of the credentials being requested.
    """
    if type(scope) is list:
      scope = ' '.join(scope)
    self.scope = scope

    super(AppAssertionCredentials, self).__init__(
        None,
        None,
        None)

  @classmethod
  def from_json(cls, json):
    data = simplejson.loads(json)
    return AppAssertionCredentials(data['scope'])

  def _refresh(self, http_request):
    """Refreshes the access_token.

    Since the underlying App Engine app_identity implementation does its own
    caching we can skip all the storage hoops and just to a refresh using the
    API.

    Args:
      http_request: callable, a callable that matches the method signature of
        httplib2.Http.request, used to make the refresh request.

    Raises:
      AccessTokenRefreshError: When the refresh fails.
    """
    try:
      (token, _) = app_identity.get_access_token(self.scope)
    except app_identity.Error, e:
      raise AccessTokenRefreshError(str(e))
    self.access_token = token


class FlowProperty(db.Property):
  """App Engine datastore Property for Flow.

  Utility property that allows easy storage and retreival of an
  oauth2client.Flow"""

  # Tell what the user type is.
  data_type = Flow

  # For writing to datastore.
  def get_value_for_datastore(self, model_instance):
    flow = super(FlowProperty,
                 self).get_value_for_datastore(model_instance)
    return db.Blob(pickle.dumps(flow))

  # For reading from datastore.
  def make_value_from_datastore(self, value):
    if value is None:
      return None
    return pickle.loads(value)

  def validate(self, value):
    if value is not None and not isinstance(value, Flow):
      raise db.BadValueError('Property %s must be convertible '
                          'to a FlowThreeLegged instance (%s)' %
                          (self.name, value))
    return super(FlowProperty, self).validate(value)

  def empty(self, value):
    return not value


class CredentialsProperty(db.Property):
  """App Engine datastore Property for Credentials.

  Utility property that allows easy storage and retrieval of
  oath2client.Credentials
  """

  # Tell what the user type is.
  data_type = Credentials

  # For writing to datastore.
  def get_value_for_datastore(self, model_instance):
    logging.info("get: Got type " + str(type(model_instance)))
    cred = super(CredentialsProperty,
                 self).get_value_for_datastore(model_instance)
    if cred is None:
      cred = ''
    else:
      cred = cred.to_json()
    return db.Blob(cred)

  # For reading from datastore.
  def make_value_from_datastore(self, value):
    logging.info("make: Got type " + str(type(value)))
    if value is None:
      return None
    if len(value) == 0:
      return None
    try:
      credentials = Credentials.new_from_json(value)
    except ValueError:
      credentials = None
    return credentials

  def validate(self, value):
    value = super(CredentialsProperty, self).validate(value)
    logging.info("validate: Got type " + str(type(value)))
    if value is not None and not isinstance(value, Credentials):
      raise db.BadValueError('Property %s must be convertible '
                          'to a Credentials instance (%s)' %
                            (self.name, value))
    #if value is not None and not isinstance(value, Credentials):
    #  return None
    return value


class StorageByKeyName(Storage):
  """Store and retrieve a single credential to and from
  the App Engine datastore.

  This Storage helper presumes the Credentials
  have been stored as a CredenialsProperty
  on a datastore model class, and that entities
  are stored by key_name.
  """

  def __init__(self, model, key_name, property_name, cache=None):
    """Constructor for Storage.

    Args:
      model: db.Model, model class
      key_name: string, key name for the entity that has the credentials
      property_name: string, name of the property that is a CredentialsProperty
      cache: memcache, a write-through cache to put in front of the datastore
    """
    self._model = model
    self._key_name = key_name
    self._property_name = property_name
    self._cache = cache

  def locked_get(self):
    """Retrieve Credential from datastore.

    Returns:
      oauth2client.Credentials
    """
    if self._cache:
      json = self._cache.get(self._key_name)
      if json:
        return Credentials.new_from_json(json)

    credential = None
    entity = self._model.get_by_key_name(self._key_name)
    if entity is not None:
      credential = getattr(entity, self._property_name)
      if credential and hasattr(credential, 'set_store'):
        credential.set_store(self)
        if self._cache:
          self._cache.set(self._key_name, credentials.to_json())

    return credential

  def locked_put(self, credentials):
    """Write a Credentials to the datastore.

    Args:
      credentials: Credentials, the credentials to store.
    """
    entity = self._model.get_or_insert(self._key_name)
    setattr(entity, self._property_name, credentials)
    entity.put()
    if self._cache:
      self._cache.set(self._key_name, credentials.to_json())

  def locked_delete(self):
    """Delete Credential from datastore."""

    if self._cache:
      self._cache.delete(self._key_name)

    entity = self._model.get_by_key_name(self._key_name)
    if entity is not None:
      entity.delete()


class CredentialsModel(db.Model):
  """Storage for OAuth 2.0 Credentials

  Storage of the model is keyed by the user.user_id().
  """
  credentials = CredentialsProperty()


class OAuth2Decorator(object):
  """Utility for making OAuth 2.0 easier.

  Instantiate and then use with oauth_required or oauth_aware
  as decorators on webapp.RequestHandler methods.

  Example:

    decorator = OAuth2Decorator(
        client_id='837...ent.com',
        client_secret='Qh...wwI',
        scope='https://www.googleapis.com/auth/plus')


    class MainHandler(webapp.RequestHandler):

      @decorator.oauth_required
      def get(self):
        http = decorator.http()
        # http is authorized with the user's Credentials and can be used
        # in API calls

  """

  def __init__(self, client_id, client_secret, scope,
               auth_uri='https://accounts.google.com/o/oauth2/auth',
               token_uri='https://accounts.google.com/o/oauth2/token',
               user_agent=None,
               message=None, **kwargs):

    """Constructor for OAuth2Decorator

    Args:
      client_id: string, client identifier.
      client_secret: string client secret.
      scope: string or list of strings, scope(s) of the credentials being
        requested.
      auth_uri: string, URI for authorization endpoint. For convenience
        defaults to Google's endpoints but any OAuth 2.0 provider can be used.
      token_uri: string, URI for token endpoint. For convenience
        defaults to Google's endpoints but any OAuth 2.0 provider can be used.
      user_agent: string, User agent of your application, default to None.
      message: Message to display if there are problems with the OAuth 2.0
        configuration. The message may contain HTML and will be presented on the
        web interface for any method that uses the decorator.
      **kwargs: dict, Keyword arguments are be passed along as kwargs to the
        OAuth2WebServerFlow constructor.
    """
    self.flow = OAuth2WebServerFlow(client_id, client_secret, scope, user_agent,
        auth_uri, token_uri, **kwargs)
    self.credentials = None
    self._request_handler = None
    self._message = message
    self._in_error = False

  def _display_error_message(self, request_handler):
    request_handler.response.out.write('<html><body>')
    request_handler.response.out.write(self._message)
    request_handler.response.out.write('</body></html>')

  def oauth_required(self, method):
    """Decorator that starts the OAuth 2.0 dance.

    Starts the OAuth dance for the logged in user if they haven't already
    granted access for this application.

    Args:
      method: callable, to be decorated method of a webapp.RequestHandler
        instance.
    """

    def check_oauth(request_handler, *args, **kwargs):
      if self._in_error:
        self._display_error_message(request_handler)
        return

      user = users.get_current_user()
      # Don't use @login_decorator as this could be used in a POST request.
      if not user:
        request_handler.redirect(users.create_login_url(
            request_handler.request.uri))
        return
      # Store the request URI in 'state' so we can use it later
      self.flow.params['state'] = request_handler.request.url
      self._request_handler = request_handler
      self.credentials = StorageByKeyName(
          CredentialsModel, user.user_id(), 'credentials').get()

      if not self.has_credentials():
        return request_handler.redirect(self.authorize_url())
      try:
        method(request_handler, *args, **kwargs)
      except AccessTokenRefreshError:
        return request_handler.redirect(self.authorize_url())

    return check_oauth

  def oauth_aware(self, method):
    """Decorator that sets up for OAuth 2.0 dance, but doesn't do it.

    Does all the setup for the OAuth dance, but doesn't initiate it.
    This decorator is useful if you want to create a page that knows
    whether or not the user has granted access to this application.
    From within a method decorated with @oauth_aware the has_credentials()
    and authorize_url() methods can be called.

    Args:
      method: callable, to be decorated method of a webapp.RequestHandler
        instance.
    """

    def setup_oauth(request_handler, *args, **kwargs):
      if self._in_error:
        self._display_error_message(request_handler)
        return

      user = users.get_current_user()
      # Don't use @login_decorator as this could be used in a POST request.
      if not user:
        request_handler.redirect(users.create_login_url(
            request_handler.request.uri))
        return


      self.flow.params['state'] = request_handler.request.url
      self._request_handler = request_handler
      self.credentials = StorageByKeyName(
          CredentialsModel, user.user_id(), 'credentials').get()
      method(request_handler, *args, **kwargs)
    return setup_oauth

  def has_credentials(self):
    """True if for the logged in user there are valid access Credentials.

    Must only be called from with a webapp.RequestHandler subclassed method
    that had been decorated with either @oauth_required or @oauth_aware.
    """
    return self.credentials is not None and not self.credentials.invalid

  def authorize_url(self):
    """Returns the URL to start the OAuth dance.

    Must only be called from with a webapp.RequestHandler subclassed method
    that had been decorated with either @oauth_required or @oauth_aware.
    """
    callback = self._request_handler.request.relative_url('/oauth2callback')
    url = self.flow.step1_get_authorize_url(callback)
    user = users.get_current_user()
    memcache.set(user.user_id(), pickle.dumps(self.flow),
                 namespace=OAUTH2CLIENT_NAMESPACE)
    return str(url)

  def http(self):
    """Returns an authorized http instance.

    Must only be called from within an @oauth_required decorated method, or
    from within an @oauth_aware decorated method where has_credentials()
    returns True.
    """
    return self.credentials.authorize(httplib2.Http())


class OAuth2DecoratorFromClientSecrets(OAuth2Decorator):
  """An OAuth2Decorator that builds from a clientsecrets file.

  Uses a clientsecrets file as the source for all the information when
  constructing an OAuth2Decorator.

  Example:

    decorator = OAuth2DecoratorFromClientSecrets(
      os.path.join(os.path.dirname(__file__), 'client_secrets.json')
      scope='https://www.googleapis.com/auth/plus')


    class MainHandler(webapp.RequestHandler):

      @decorator.oauth_required
      def get(self):
        http = decorator.http()
        # http is authorized with the user's Credentials and can be used
        # in API calls
  """

  def __init__(self, filename, scope, message=None):
    """Constructor

    Args:
      filename: string, File name of client secrets.
      scope: string, Space separated list of scopes.
      message: string, A friendly string to display to the user if the
        clientsecrets file is missing or invalid. The message may contain HTML and
        will be presented on the web interface for any method that uses the
        decorator.
    """
    try:
      client_type, client_info = clientsecrets.loadfile(filename)
      if client_type not in [clientsecrets.TYPE_WEB, clientsecrets.TYPE_INSTALLED]:
        raise InvalidClientSecretsError('OAuth2Decorator doesn\'t support this OAuth 2.0 flow.')
      super(OAuth2DecoratorFromClientSecrets,
            self).__init__(
                client_info['client_id'],
                client_info['client_secret'],
                scope,
                client_info['auth_uri'],
                client_info['token_uri'],
                message)
    except clientsecrets.InvalidClientSecretsError:
      self._in_error = True
    if message is not None:
      self._message = message
    else:
      self._message = "Please configure your application for OAuth 2.0"


def oauth2decorator_from_clientsecrets(filename, scope, message=None):
  """Creates an OAuth2Decorator populated from a clientsecrets file.

  Args:
    filename: string, File name of client secrets.
    scope: string, Space separated list of scopes.
    message: string, A friendly string to display to the user if the
      clientsecrets file is missing or invalid. The message may contain HTML and
      will be presented on the web interface for any method that uses the
      decorator.

  Returns: An OAuth2Decorator

  """
  return OAuth2DecoratorFromClientSecrets(filename, scope, message)


class OAuth2Handler(webapp.RequestHandler):
  """Handler for the redirect_uri of the OAuth 2.0 dance."""

  @login_required
  def get(self):
    error = self.request.get('error')
    if error:
      errormsg = self.request.get('error_description', error)
      self.response.out.write(
          'The authorization request failed: %s' % errormsg)
    else:
      user = users.get_current_user()
      flow = pickle.loads(memcache.get(user.user_id(),
                                       namespace=OAUTH2CLIENT_NAMESPACE))
      # This code should be ammended with application specific error
      # handling. The following cases should be considered:
      # 1. What if the flow doesn't exist in memcache? Or is corrupt?
      # 2. What if the step2_exchange fails?
      if flow:
        credentials = flow.step2_exchange(self.request.params)
        StorageByKeyName(
            CredentialsModel, user.user_id(), 'credentials').put(credentials)
        self.redirect(str(self.request.get('state')))
      else:
        # TODO Add error handling here.
        pass


application = webapp.WSGIApplication([('/oauth2callback', OAuth2Handler)])


def main():
  run_wsgi_app(application)

########NEW FILE########
__FILENAME__ = client
# Copyright (C) 2010 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""An OAuth 2.0 client.

Tools for interacting with OAuth 2.0 protected resources.
"""

__author__ = 'jcgregorio@google.com (Joe Gregorio)'

import base64
import clientsecrets
import copy
import datetime
import httplib2
import logging
import os
import sys
import time
import urllib
import urlparse

from anyjson import simplejson

HAS_OPENSSL = False
from oauth2client.crypt import Signer
from oauth2client.crypt import make_signed_jwt
from oauth2client.crypt import verify_signed_jwt_with_certs
HAS_OPENSSL = True

try:
  from urlparse import parse_qsl
except ImportError:
  from cgi import parse_qsl

logger = logging.getLogger(__name__)

# Expiry is stored in RFC3339 UTC format
EXPIRY_FORMAT = '%Y-%m-%dT%H:%M:%SZ'

# Which certs to use to validate id_tokens received.
ID_TOKEN_VERIFICATON_CERTS = 'https://www.googleapis.com/oauth2/v1/certs'

# Constant to use for the out of band OAuth 2.0 flow.
OOB_CALLBACK_URN = 'urn:ietf:wg:oauth:2.0:oob'


class Error(Exception):
  """Base error for this module."""
  pass


class FlowExchangeError(Error):
  """Error trying to exchange an authorization grant for an access token."""
  pass


class AccessTokenRefreshError(Error):
  """Error trying to refresh an expired access token."""
  pass

class UnknownClientSecretsFlowError(Error):
  """The client secrets file called for an unknown type of OAuth 2.0 flow. """
  pass


class AccessTokenCredentialsError(Error):
  """Having only the access_token means no refresh is possible."""
  pass


class VerifyJwtTokenError(Error):
  """Could on retrieve certificates for validation."""
  pass


def _abstract():
  raise NotImplementedError('You need to override this function')


class MemoryCache(object):
  """httplib2 Cache implementation which only caches locally."""

  def __init__(self):
    self.cache = {}

  def get(self, key):
    return self.cache.get(key)

  def set(self, key, value):
    self.cache[key] = value

  def delete(self, key):
    self.cache.pop(key, None)


class Credentials(object):
  """Base class for all Credentials objects.

  Subclasses must define an authorize() method that applies the credentials to
  an HTTP transport.

  Subclasses must also specify a classmethod named 'from_json' that takes a JSON
  string as input and returns an instaniated Credentials object.
  """

  NON_SERIALIZED_MEMBERS = ['store']

  def authorize(self, http):
    """Take an httplib2.Http instance (or equivalent) and
    authorizes it for the set of credentials, usually by
    replacing http.request() with a method that adds in
    the appropriate headers and then delegates to the original
    Http.request() method.
    """
    _abstract()

  def refresh(self, http):
    """Forces a refresh of the access_token.

    Args:
      http: httplib2.Http, an http object to be used to make the refresh
        request.
    """
    _abstract()

  def apply(self, headers):
    """Add the authorization to the headers.

    Args:
      headers: dict, the headers to add the Authorization header to.
    """
    _abstract()

  def _to_json(self, strip):
    """Utility function for creating a JSON representation of an instance of Credentials.

    Args:
      strip: array, An array of names of members to not include in the JSON.

    Returns:
       string, a JSON representation of this instance, suitable to pass to
       from_json().
    """
    t = type(self)
    d = copy.copy(self.__dict__)
    for member in strip:
      del d[member]
    if 'token_expiry' in d and isinstance(d['token_expiry'], datetime.datetime):
      d['token_expiry'] = d['token_expiry'].strftime(EXPIRY_FORMAT)
    # Add in information we will need later to reconsistitue this instance.
    d['_class'] = t.__name__
    d['_module'] = t.__module__
    return simplejson.dumps(d)

  def to_json(self):
    """Creating a JSON representation of an instance of Credentials.

    Returns:
       string, a JSON representation of this instance, suitable to pass to
       from_json().
    """
    return self._to_json(Credentials.NON_SERIALIZED_MEMBERS)

  @classmethod
  def new_from_json(cls, s):
    """Utility class method to instantiate a Credentials subclass from a JSON
    representation produced by to_json().

    Args:
      s: string, JSON from to_json().

    Returns:
      An instance of the subclass of Credentials that was serialized with
      to_json().
    """
    data = simplejson.loads(s)
    # Find and call the right classmethod from_json() to restore the object.
    module = data['_module']
    try:
      m = __import__(module)
    except ImportError:
      # In case there's an object from the old package structure, update it
      module = module.replace('.apiclient', '')
      m = __import__(module)

    m = __import__(module, fromlist=module.split('.')[:-1])
    kls = getattr(m, data['_class'])
    from_json = getattr(kls, 'from_json')
    return from_json(s)


class Flow(object):
  """Base class for all Flow objects."""
  pass


class Storage(object):
  """Base class for all Storage objects.

  Store and retrieve a single credential.  This class supports locking
  such that multiple processes and threads can operate on a single
  store.
  """

  def acquire_lock(self):
    """Acquires any lock necessary to access this Storage.

    This lock is not reentrant."""
    pass

  def release_lock(self):
    """Release the Storage lock.

    Trying to release a lock that isn't held will result in a
    RuntimeError.
    """
    pass

  def locked_get(self):
    """Retrieve credential.

    The Storage lock must be held when this is called.

    Returns:
      oauth2client.client.Credentials
    """
    _abstract()

  def locked_put(self, credentials):
    """Write a credential.

    The Storage lock must be held when this is called.

    Args:
      credentials: Credentials, the credentials to store.
    """
    _abstract()

  def locked_delete(self):
    """Delete a credential.

    The Storage lock must be held when this is called.
    """
    _abstract()

  def get(self):
    """Retrieve credential.

    The Storage lock must *not* be held when this is called.

    Returns:
      oauth2client.client.Credentials
    """
    self.acquire_lock()
    try:
      return self.locked_get()
    finally:
      self.release_lock()

  def put(self, credentials):
    """Write a credential.

    The Storage lock must be held when this is called.

    Args:
      credentials: Credentials, the credentials to store.
    """
    self.acquire_lock()
    try:
      self.locked_put(credentials)
    finally:
      self.release_lock()

  def delete(self):
    """Delete credential.

    Frees any resources associated with storing the credential.
    The Storage lock must *not* be held when this is called.

    Returns:
      None
    """
    self.acquire_lock()
    try:
      return self.locked_delete()
    finally:
      self.release_lock()


class OAuth2Credentials(Credentials):
  """Credentials object for OAuth 2.0.

  Credentials can be applied to an httplib2.Http object using the authorize()
  method, which then adds the OAuth 2.0 access token to each request.

  OAuth2Credentials objects may be safely pickled and unpickled.
  """

  def __init__(self, access_token, client_id, client_secret, refresh_token,
               token_expiry, token_uri, user_agent, id_token=None):
    """Create an instance of OAuth2Credentials.

    This constructor is not usually called by the user, instead
    OAuth2Credentials objects are instantiated by the OAuth2WebServerFlow.

    Args:
      access_token: string, access token.
      client_id: string, client identifier.
      client_secret: string, client secret.
      refresh_token: string, refresh token.
      token_expiry: datetime, when the access_token expires.
      token_uri: string, URI of token endpoint.
      user_agent: string, The HTTP User-Agent to provide for this application.
      id_token: object, The identity of the resource owner.

    Notes:
      store: callable, A callable that when passed a Credential
        will store the credential back to where it came from.
        This is needed to store the latest access_token if it
        has expired and been refreshed.
    """
    self.access_token = access_token
    self.client_id = client_id
    self.client_secret = client_secret
    self.refresh_token = refresh_token
    self.store = None
    self.token_expiry = token_expiry
    self.token_uri = token_uri
    self.user_agent = user_agent
    self.id_token = id_token

    # True if the credentials have been revoked or expired and can't be
    # refreshed.
    self.invalid = False

  def authorize(self, http):
    """Authorize an httplib2.Http instance with these credentials.

    The modified http.request method will add authentication headers to each
    request and will refresh access_tokens when a 401 is received on a
    request. In addition the http.request method has a credentials property,
    http.request.credentials, which is the Credentials object that authorized
    it.

    Args:
       http: An instance of httplib2.Http
           or something that acts like it.

    Returns:
       A modified instance of http that was passed in.

    Example:

      h = httplib2.Http()
      h = credentials.authorize(h)

    You can't create a new OAuth subclass of httplib2.Authenication
    because it never gets passed the absolute URI, which is needed for
    signing. So instead we have to overload 'request' with a closure
    that adds in the Authorization header and then calls the original
    version of 'request()'.
    """
    request_orig = http.request

    # The closure that will replace 'httplib2.Http.request'.
    def new_request(uri, method='GET', body=None, headers=None,
                    redirections=httplib2.DEFAULT_MAX_REDIRECTS,
                    connection_type=None):
      if not self.access_token:
        logger.info('Attempting refresh to obtain initial access_token')
        self._refresh(request_orig)

      # Modify the request headers to add the appropriate
      # Authorization header.
      if headers is None:
        headers = {}
      self.apply(headers)

      if self.user_agent is not None:
        if 'user-agent' in headers:
          headers['user-agent'] = self.user_agent + ' ' + headers['user-agent']
        else:
          headers['user-agent'] = self.user_agent

      resp, content = request_orig(uri, method, body, headers,
                                   redirections, connection_type)

      if resp.status == 401:
        logger.info('Refreshing due to a 401')
        self._refresh(request_orig)
        self.apply(headers)
        return request_orig(uri, method, body, headers,
                            redirections, connection_type)
      else:
        return (resp, content)

    # Replace the request method with our own closure.
    http.request = new_request

    # Set credentials as a property of the request method.
    setattr(http.request, 'credentials', self)

    return http

  def refresh(self, http):
    """Forces a refresh of the access_token.

    Args:
      http: httplib2.Http, an http object to be used to make the refresh
        request.
    """
    self._refresh(http.request)

  def apply(self, headers):
    """Add the authorization to the headers.

    Args:
      headers: dict, the headers to add the Authorization header to.
    """
    headers['Authorization'] = 'Bearer ' + self.access_token

  def to_json(self):
    return self._to_json(Credentials.NON_SERIALIZED_MEMBERS)

  @classmethod
  def from_json(cls, s):
    """Instantiate a Credentials object from a JSON description of it. The JSON
    should have been produced by calling .to_json() on the object.

    Args:
      data: dict, A deserialized JSON object.

    Returns:
      An instance of a Credentials subclass.
    """
    data = simplejson.loads(s)
    if 'token_expiry' in data and not isinstance(data['token_expiry'],
        datetime.datetime):
      try:
        data['token_expiry'] = datetime.datetime.strptime(
            data['token_expiry'], EXPIRY_FORMAT)
      except:
        data['token_expiry'] = None
    retval = OAuth2Credentials(
        data['access_token'],
        data['client_id'],
        data['client_secret'],
        data['refresh_token'],
        data['token_expiry'],
        data['token_uri'],
        data['user_agent'],
        data.get('id_token', None))
    retval.invalid = data['invalid']
    return retval

  @property
  def access_token_expired(self):
    """True if the credential is expired or invalid.

    If the token_expiry isn't set, we assume the token doesn't expire.
    """
    if self.invalid:
      return True

    if not self.token_expiry:
      return False

    now = datetime.datetime.utcnow()
    if now >= self.token_expiry:
      logger.info('access_token is expired. Now: %s, token_expiry: %s',
                  now, self.token_expiry)
      return True
    return False

  def set_store(self, store):
    """Set the Storage for the credential.

    Args:
      store: Storage, an implementation of Stroage object.
        This is needed to store the latest access_token if it
        has expired and been refreshed.  This implementation uses
        locking to check for updates before updating the
        access_token.
    """
    self.store = store

  def _updateFromCredential(self, other):
    """Update this Credential from another instance."""
    self.__dict__.update(other.__getstate__())

  def __getstate__(self):
    """Trim the state down to something that can be pickled."""
    d = copy.copy(self.__dict__)
    del d['store']
    return d

  def __setstate__(self, state):
    """Reconstitute the state of the object from being pickled."""
    self.__dict__.update(state)
    self.store = None

  def _generate_refresh_request_body(self):
    """Generate the body that will be used in the refresh request."""
    body = urllib.urlencode({
        'grant_type': 'refresh_token',
        'client_id': self.client_id,
        'client_secret': self.client_secret,
        'refresh_token': self.refresh_token,
        })
    return body

  def _generate_refresh_request_headers(self):
    """Generate the headers that will be used in the refresh request."""
    headers = {
        'content-type': 'application/x-www-form-urlencoded',
    }

    if self.user_agent is not None:
      headers['user-agent'] = self.user_agent

    return headers

  def _refresh(self, http_request):
    """Refreshes the access_token.

    This method first checks by reading the Storage object if available.
    If a refresh is still needed, it holds the Storage lock until the
    refresh is completed.

    Args:
      http_request: callable, a callable that matches the method signature of
        httplib2.Http.request, used to make the refresh request.

    Raises:
      AccessTokenRefreshError: When the refresh fails.
    """
    if not self.store:
      self._do_refresh_request(http_request)
    else:
      self.store.acquire_lock()
      try:
        new_cred = self.store.locked_get()
        if (new_cred and not new_cred.invalid and
            new_cred.access_token != self.access_token):
          logger.info('Updated access_token read from Storage')
          self._updateFromCredential(new_cred)
        else:
          self._do_refresh_request(http_request)
      finally:
        self.store.release_lock()

  def _do_refresh_request(self, http_request):
    """Refresh the access_token using the refresh_token.

    Args:
      http_request: callable, a callable that matches the method signature of
        httplib2.Http.request, used to make the refresh request.

    Raises:
      AccessTokenRefreshError: When the refresh fails.
    """
    body = self._generate_refresh_request_body()
    headers = self._generate_refresh_request_headers()

    logger.info('Refresing access_token')
    resp, content = http_request(
        self.token_uri, method='POST', body=body, headers=headers)
    if resp.status == 200:
      # TODO(jcgregorio) Raise an error if loads fails?
      d = simplejson.loads(content)
      self.access_token = d['access_token']
      self.refresh_token = d.get('refresh_token', self.refresh_token)
      if 'expires_in' in d:
        self.token_expiry = datetime.timedelta(
            seconds=int(d['expires_in'])) + datetime.datetime.utcnow()
      else:
        self.token_expiry = None
      if self.store:
        self.store.locked_put(self)
    else:
      # An {'error':...} response body means the token is expired or revoked,
      # so we flag the credentials as such.
      logger.error('Failed to retrieve access token: %s' % content)
      error_msg = 'Invalid response %s.' % resp['status']
      try:
        d = simplejson.loads(content)
        if 'error' in d:
          error_msg = d['error']
          self.invalid = True
          if self.store:
            self.store.locked_put(self)
      except:
        pass
      raise AccessTokenRefreshError(error_msg)


class AccessTokenCredentials(OAuth2Credentials):
  """Credentials object for OAuth 2.0.

  Credentials can be applied to an httplib2.Http object using the
  authorize() method, which then signs each request from that object
  with the OAuth 2.0 access token.  This set of credentials is for the
  use case where you have acquired an OAuth 2.0 access_token from
  another place such as a JavaScript client or another web
  application, and wish to use it from Python. Because only the
  access_token is present it can not be refreshed and will in time
  expire.

  AccessTokenCredentials objects may be safely pickled and unpickled.

  Usage:
    credentials = AccessTokenCredentials('<an access token>',
      'my-user-agent/1.0')
    http = httplib2.Http()
    http = credentials.authorize(http)

  Exceptions:
    AccessTokenCredentialsExpired: raised when the access_token expires or is
      revoked.
  """

  def __init__(self, access_token, user_agent):
    """Create an instance of OAuth2Credentials

    This is one of the few types if Credentials that you should contrust,
    Credentials objects are usually instantiated by a Flow.

    Args:
      access_token: string, access token.
      user_agent: string, The HTTP User-Agent to provide for this application.

    Notes:
      store: callable, a callable that when passed a Credential
        will store the credential back to where it came from.
    """
    super(AccessTokenCredentials, self).__init__(
        access_token,
        None,
        None,
        None,
        None,
        None,
        user_agent)


  @classmethod
  def from_json(cls, s):
    data = simplejson.loads(s)
    retval = AccessTokenCredentials(
        data['access_token'],
        data['user_agent'])
    return retval

  def _refresh(self, http_request):
    raise AccessTokenCredentialsError(
        "The access_token is expired or invalid and can't be refreshed.")


class AssertionCredentials(OAuth2Credentials):
  """Abstract Credentials object used for OAuth 2.0 assertion grants.

  This credential does not require a flow to instantiate because it
  represents a two legged flow, and therefore has all of the required
  information to generate and refresh its own access tokens.  It must
  be subclassed to generate the appropriate assertion string.

  AssertionCredentials objects may be safely pickled and unpickled.
  """

  def __init__(self, assertion_type, user_agent,
               token_uri='https://accounts.google.com/o/oauth2/token',
               **unused_kwargs):
    """Constructor for AssertionFlowCredentials.

    Args:
      assertion_type: string, assertion type that will be declared to the auth
          server
      user_agent: string, The HTTP User-Agent to provide for this application.
      token_uri: string, URI for token endpoint. For convenience
        defaults to Google's endpoints but any OAuth 2.0 provider can be used.
    """
    super(AssertionCredentials, self).__init__(
        None,
        None,
        None,
        None,
        None,
        token_uri,
        user_agent)
    self.assertion_type = assertion_type

  def _generate_refresh_request_body(self):
    assertion = self._generate_assertion()

    body = urllib.urlencode({
        'assertion_type': self.assertion_type,
        'assertion': assertion,
        'grant_type': 'assertion',
        })

    return body

  def _generate_assertion(self):
    """Generate the assertion string that will be used in the access token
    request.
    """
    _abstract()

if HAS_OPENSSL:
  # PyOpenSSL is not a prerequisite for oauth2client, so if it is missing then
  # don't create the SignedJwtAssertionCredentials or the verify_id_token()
  # method.

  class SignedJwtAssertionCredentials(AssertionCredentials):
    """Credentials object used for OAuth 2.0 Signed JWT assertion grants.

    This credential does not require a flow to instantiate because it
    represents a two legged flow, and therefore has all of the required
    information to generate and refresh its own access tokens.
    """

    MAX_TOKEN_LIFETIME_SECS = 3600 # 1 hour in seconds

    def __init__(self,
        service_account_name,
        private_key,
        scope,
        private_key_password='notasecret',
        user_agent=None,
        token_uri='https://accounts.google.com/o/oauth2/token',
        **kwargs):
      """Constructor for SignedJwtAssertionCredentials.

      Args:
        service_account_name: string, id for account, usually an email address.
        private_key: string, private key in P12 format.
        scope: string or list of strings, scope(s) of the credentials being
          requested.
        private_key_password: string, password for private_key.
        user_agent: string, HTTP User-Agent to provide for this application.
        token_uri: string, URI for token endpoint. For convenience
          defaults to Google's endpoints but any OAuth 2.0 provider can be used.
        kwargs: kwargs, Additional parameters to add to the JWT token, for
          example prn=joe@xample.org."""

      super(SignedJwtAssertionCredentials, self).__init__(
          'http://oauth.net/grant_type/jwt/1.0/bearer',
          user_agent,
          token_uri=token_uri,
          )

      if type(scope) is list:
        scope = ' '.join(scope)
      self.scope = scope

      self.private_key = private_key
      self.private_key_password = private_key_password
      self.service_account_name = service_account_name
      self.kwargs = kwargs

    @classmethod
    def from_json(cls, s):
      data = simplejson.loads(s)
      retval = SignedJwtAssertionCredentials(
          data['service_account_name'],
          data['private_key'],
          data['private_key_password'],
          data['scope'],
          data['user_agent'],
          data['token_uri'],
          data['kwargs']
          )
      retval.invalid = data['invalid']
      return retval

    def _generate_assertion(self):
      """Generate the assertion that will be used in the request."""
      now = long(time.time())
      payload = {
          'aud': self.token_uri,
          'scope': self.scope,
          'iat': now,
          'exp': now + SignedJwtAssertionCredentials.MAX_TOKEN_LIFETIME_SECS,
          'iss': self.service_account_name
      }
      payload.update(self.kwargs)
      logging.debug(str(payload))

      return make_signed_jwt(
          Signer.from_string(self.private_key, self.private_key_password),
          payload)

  # Only used in verify_id_token(), which is always calling to the same URI
  # for the certs.
  _cached_http = httplib2.Http(MemoryCache())

  def verify_id_token(id_token, audience, http=None,
      cert_uri=ID_TOKEN_VERIFICATON_CERTS):
    """Verifies a signed JWT id_token.

    Args:
      id_token: string, A Signed JWT.
      audience: string, The audience 'aud' that the token should be for.
      http: httplib2.Http, instance to use to make the HTTP request. Callers
        should supply an instance that has caching enabled.
      cert_uri: string, URI of the certificates in JSON format to
        verify the JWT against.

    Returns:
      The deserialized JSON in the JWT.

    Raises:
      oauth2client.crypt.AppIdentityError if the JWT fails to verify.
    """
    if http is None:
      http = _cached_http

    resp, content = http.request(cert_uri)

    if resp.status == 200:
      certs = simplejson.loads(content)
      return verify_signed_jwt_with_certs(id_token, certs, audience)
    else:
      raise VerifyJwtTokenError('Status code: %d' % resp.status)


def _urlsafe_b64decode(b64string):
  # Guard against unicode strings, which base64 can't handle.
  b64string = b64string.encode('ascii')
  padded = b64string + '=' * (4 - len(b64string) % 4)
  return base64.urlsafe_b64decode(padded)


def _extract_id_token(id_token):
  """Extract the JSON payload from a JWT.

  Does the extraction w/o checking the signature.

  Args:
    id_token: string, OAuth 2.0 id_token.

  Returns:
    object, The deserialized JSON payload.
  """
  segments = id_token.split('.')

  if (len(segments) != 3):
    raise VerifyJwtTokenError(
      'Wrong number of segments in token: %s' % id_token)

  return simplejson.loads(_urlsafe_b64decode(segments[1]))


class OAuth2WebServerFlow(Flow):
  """Does the Web Server Flow for OAuth 2.0.

  OAuth2Credentials objects may be safely pickled and unpickled.
  """

  def __init__(self, client_id, client_secret, scope, user_agent=None,
               auth_uri='https://accounts.google.com/o/oauth2/auth',
               token_uri='https://accounts.google.com/o/oauth2/token',
               **kwargs):
    """Constructor for OAuth2WebServerFlow.

    Args:
      client_id: string, client identifier.
      client_secret: string client secret.
      scope: string or list of strings, scope(s) of the credentials being
        requested.
      user_agent: string, HTTP User-Agent to provide for this application.
      auth_uri: string, URI for authorization endpoint. For convenience
        defaults to Google's endpoints but any OAuth 2.0 provider can be used.
      token_uri: string, URI for token endpoint. For convenience
        defaults to Google's endpoints but any OAuth 2.0 provider can be used.
      **kwargs: dict, The keyword arguments are all optional and required
                        parameters for the OAuth calls.
    """
    self.client_id = client_id
    self.client_secret = client_secret
    if type(scope) is list:
      scope = ' '.join(scope)
    self.scope = scope
    self.user_agent = user_agent
    self.auth_uri = auth_uri
    self.token_uri = token_uri
    self.params = {
        'access_type': 'offline',
        }
    self.params.update(kwargs)
    self.redirect_uri = None

  def step1_get_authorize_url(self, redirect_uri=OOB_CALLBACK_URN):
    """Returns a URI to redirect to the provider.

    Args:
      redirect_uri: string, Either the string 'urn:ietf:wg:oauth:2.0:oob' for
          a non-web-based application, or a URI that handles the callback from
          the authorization server.

    If redirect_uri is 'urn:ietf:wg:oauth:2.0:oob' then pass in the
    generated verification code to step2_exchange,
    otherwise pass in the query parameters received
    at the callback uri to step2_exchange.
    """

    self.redirect_uri = redirect_uri
    query = {
        'response_type': 'code',
        'client_id': self.client_id,
        'redirect_uri': redirect_uri,
        'scope': self.scope,
        }
    query.update(self.params)
    parts = list(urlparse.urlparse(self.auth_uri))
    query.update(dict(parse_qsl(parts[4]))) # 4 is the index of the query part
    parts[4] = urllib.urlencode(query)
    return urlparse.urlunparse(parts)

  def step2_exchange(self, code, http=None):
    """Exhanges a code for OAuth2Credentials.

    Args:
      code: string or dict, either the code as a string, or a dictionary
        of the query parameters to the redirect_uri, which contains
        the code.
      http: httplib2.Http, optional http instance to use to do the fetch
    """

    if not (isinstance(code, str) or isinstance(code, unicode)):
      code = code['code']

    body = urllib.urlencode({
        'grant_type': 'authorization_code',
        'client_id': self.client_id,
        'client_secret': self.client_secret,
        'code': code,
        'redirect_uri': self.redirect_uri,
        'scope': self.scope,
        })
    headers = {
        'content-type': 'application/x-www-form-urlencoded',
    }

    if self.user_agent is not None:
      headers['user-agent'] = self.user_agent

    if http is None:
      http = httplib2.Http()

    resp, content = http.request(self.token_uri, method='POST', body=body,
                                 headers=headers)
    if resp.status == 200:
      # TODO(jcgregorio) Raise an error if simplejson.loads fails?
      d = simplejson.loads(content)
      access_token = d['access_token']
      refresh_token = d.get('refresh_token', None)
      token_expiry = None
      if 'expires_in' in d:
        token_expiry = datetime.datetime.utcnow() + datetime.timedelta(
            seconds=int(d['expires_in']))

      if 'id_token' in d:
        d['id_token'] = _extract_id_token(d['id_token'])

      logger.info('Successfully retrieved access token: %s' % content)
      return OAuth2Credentials(access_token, self.client_id,
                               self.client_secret, refresh_token, token_expiry,
                               self.token_uri, self.user_agent,
                               id_token=d.get('id_token', None))
    else:
      logger.error('Failed to retrieve access token: %s' % content)
      error_msg = 'Invalid response %s.' % resp['status']
      try:
        d = simplejson.loads(content)
        if 'error' in d:
          error_msg = d['error']
      except:
        pass

      raise FlowExchangeError(error_msg)

def flow_from_clientsecrets(filename, scope, message=None):
  """Create a Flow from a clientsecrets file.

  Will create the right kind of Flow based on the contents of the clientsecrets
  file or will raise InvalidClientSecretsError for unknown types of Flows.

  Args:
    filename: string, File name of client secrets.
    scope: string or list of strings, scope(s) to request.
    message: string, A friendly string to display to the user if the
      clientsecrets file is missing or invalid. If message is provided then
      sys.exit will be called in the case of an error. If message in not
      provided then clientsecrets.InvalidClientSecretsError will be raised.

  Returns:
    A Flow object.

  Raises:
    UnknownClientSecretsFlowError if the file describes an unknown kind of Flow.
    clientsecrets.InvalidClientSecretsError if the clientsecrets file is
      invalid.
  """
  try:
    client_type, client_info = clientsecrets.loadfile(filename)
    if client_type in [clientsecrets.TYPE_WEB, clientsecrets.TYPE_INSTALLED]:
        return OAuth2WebServerFlow(
            client_info['client_id'],
            client_info['client_secret'],
            scope,
            None, # user_agent
            client_info['auth_uri'],
            client_info['token_uri'])
  except clientsecrets.InvalidClientSecretsError:
    if message:
      sys.exit(message)
    else:
      raise
  else:
    raise UnknownClientSecretsFlowError(
        'This OAuth 2.0 flow is unsupported: "%s"' * client_type)

########NEW FILE########
__FILENAME__ = clientsecrets
# Copyright (C) 2011 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Utilities for reading OAuth 2.0 client secret files.

A client_secrets.json file contains all the information needed to interact with
an OAuth 2.0 protected service.
"""

__author__ = 'jcgregorio@google.com (Joe Gregorio)'


from anyjson import simplejson

# Properties that make a client_secrets.json file valid.
TYPE_WEB = 'web'
TYPE_INSTALLED = 'installed'

VALID_CLIENT = {
    TYPE_WEB: {
        'required': [
            'client_id',
            'client_secret',
            'redirect_uris',
            'auth_uri',
            'token_uri'],
        'string': [
            'client_id',
            'client_secret'
            ]
        },
    TYPE_INSTALLED: {
        'required': [
            'client_id',
            'client_secret',
            'redirect_uris',
            'auth_uri',
            'token_uri'],
        'string': [
            'client_id',
            'client_secret'
            ]
      }
    }

class Error(Exception):
  """Base error for this module."""
  pass


class InvalidClientSecretsError(Error):
  """Format of ClientSecrets file is invalid."""
  pass


def _validate_clientsecrets(obj):
  if obj is None or len(obj) != 1:
    raise InvalidClientSecretsError('Invalid file format.')
  client_type = obj.keys()[0]
  if client_type not in VALID_CLIENT.keys():
    raise InvalidClientSecretsError('Unknown client type: %s.' % client_type)
  client_info = obj[client_type]
  for prop_name in VALID_CLIENT[client_type]['required']:
    if prop_name not in client_info:
      raise InvalidClientSecretsError(
        'Missing property "%s" in a client type of "%s".' % (prop_name,
                                                           client_type))
  for prop_name in VALID_CLIENT[client_type]['string']:
    if client_info[prop_name].startswith('[['):
      raise InvalidClientSecretsError(
        'Property "%s" is not configured.' % prop_name)
  return client_type, client_info


def load(fp):
  obj = simplejson.load(fp)
  return _validate_clientsecrets(obj)


def loads(s):
  obj = simplejson.loads(s)
  return _validate_clientsecrets(obj)


def loadfile(filename):
  try:
    fp = file(filename, 'r')
    try:
      obj = simplejson.load(fp)
    finally:
      fp.close()
  except IOError:
    raise InvalidClientSecretsError('File not found: "%s"' % filename)
  return _validate_clientsecrets(obj)

########NEW FILE########
__FILENAME__ = crypt
#!/usr/bin/python2.4
# -*- coding: utf-8 -*-
#
# Copyright (C) 2011 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import base64
import hashlib
import logging
import time

from OpenSSL import crypto
from anyjson import simplejson


CLOCK_SKEW_SECS = 300  # 5 minutes in seconds
AUTH_TOKEN_LIFETIME_SECS = 300  # 5 minutes in seconds
MAX_TOKEN_LIFETIME_SECS = 86400  # 1 day in seconds


class AppIdentityError(Exception):
  pass


class Verifier(object):
  """Verifies the signature on a message."""

  def __init__(self, pubkey):
    """Constructor.

    Args:
      pubkey, OpenSSL.crypto.PKey, The public key to verify with.
    """
    self._pubkey = pubkey

  def verify(self, message, signature):
    """Verifies a message against a signature.

    Args:
      message: string, The message to verify.
      signature: string, The signature on the message.

    Returns:
      True if message was singed by the private key associated with the public
      key that this object was constructed with.
    """
    try:
      crypto.verify(self._pubkey, signature, message, 'sha256')
      return True
    except:
      return False

  @staticmethod
  def from_string(key_pem, is_x509_cert):
    """Construct a Verified instance from a string.

    Args:
      key_pem: string, public key in PEM format.
      is_x509_cert: bool, True if key_pem is an X509 cert, otherwise it is
        expected to be an RSA key in PEM format.

    Returns:
      Verifier instance.

    Raises:
      OpenSSL.crypto.Error if the key_pem can't be parsed.
    """
    if is_x509_cert:
      pubkey = crypto.load_certificate(crypto.FILETYPE_PEM, key_pem)
    else:
      pubkey = crypto.load_privatekey(crypto.FILETYPE_PEM, key_pem)
    return Verifier(pubkey)


class Signer(object):
  """Signs messages with a private key."""

  def __init__(self, pkey):
    """Constructor.

    Args:
      pkey, OpenSSL.crypto.PKey, The private key to sign with.
    """
    self._key = pkey

  def sign(self, message):
    """Signs a message.

    Args:
      message: string, Message to be signed.

    Returns:
      string, The signature of the message for the given key.
    """
    return crypto.sign(self._key, message, 'sha256')

  @staticmethod
  def from_string(key, password='notasecret'):
    """Construct a Signer instance from a string.

    Args:
      key: string, private key in P12 format.
      password: string, password for the private key file.

    Returns:
      Signer instance.

    Raises:
      OpenSSL.crypto.Error if the key can't be parsed.
    """
    pkey = crypto.load_pkcs12(key, password).get_privatekey()
    return Signer(pkey)


def _urlsafe_b64encode(raw_bytes):
  return base64.urlsafe_b64encode(raw_bytes).rstrip('=')


def _urlsafe_b64decode(b64string):
  # Guard against unicode strings, which base64 can't handle.
  b64string = b64string.encode('ascii')
  padded = b64string + '=' * (4 - len(b64string) % 4)
  return base64.urlsafe_b64decode(padded)


def _json_encode(data):
  return simplejson.dumps(data, separators = (',', ':'))


def make_signed_jwt(signer, payload):
  """Make a signed JWT.

  See http://self-issued.info/docs/draft-jones-json-web-token.html.

  Args:
    signer: crypt.Signer, Cryptographic signer.
    payload: dict, Dictionary of data to convert to JSON and then sign.

  Returns:
    string, The JWT for the payload.
  """
  header = {'typ': 'JWT', 'alg': 'RS256'}

  segments = [
          _urlsafe_b64encode(_json_encode(header)),
          _urlsafe_b64encode(_json_encode(payload)),
  ]
  signing_input = '.'.join(segments)

  signature = signer.sign(signing_input)
  segments.append(_urlsafe_b64encode(signature))

  logging.debug(str(segments))

  return '.'.join(segments)


def verify_signed_jwt_with_certs(jwt, certs, audience):
  """Verify a JWT against public certs.

  See http://self-issued.info/docs/draft-jones-json-web-token.html.

  Args:
    jwt: string, A JWT.
    certs: dict, Dictionary where values of public keys in PEM format.
    audience: string, The audience, 'aud', that this JWT should contain. If
      None then the JWT's 'aud' parameter is not verified.

  Returns:
    dict, The deserialized JSON payload in the JWT.

  Raises:
    AppIdentityError if any checks are failed.
  """
  segments = jwt.split('.')

  if (len(segments) != 3):
    raise AppIdentityError(
      'Wrong number of segments in token: %s' % jwt)
  signed = '%s.%s' % (segments[0], segments[1])

  signature = _urlsafe_b64decode(segments[2])

  # Parse token.
  json_body = _urlsafe_b64decode(segments[1])
  try:
    parsed = simplejson.loads(json_body)
  except:
    raise AppIdentityError('Can\'t parse token: %s' % json_body)

  # Check signature.
  verified = False
  for (keyname, pem) in certs.items():
    verifier = Verifier.from_string(pem, True)
    if (verifier.verify(signed, signature)):
      verified = True
      break
  if not verified:
    raise AppIdentityError('Invalid token signature: %s' % jwt)

  # Check creation timestamp.
  iat = parsed.get('iat')
  if iat is None:
    raise AppIdentityError('No iat field in token: %s' % json_body)
  earliest = iat - CLOCK_SKEW_SECS

  # Check expiration timestamp.
  now = long(time.time())
  exp = parsed.get('exp')
  if exp is None:
    raise AppIdentityError('No exp field in token: %s' % json_body)
  if exp >= now + MAX_TOKEN_LIFETIME_SECS:
    raise AppIdentityError(
      'exp field too far in future: %s' % json_body)
  latest = exp + CLOCK_SKEW_SECS

  if now < earliest:
    raise AppIdentityError('Token used too early, %d < %d: %s' %
      (now, earliest, json_body))
  if now > latest:
    raise AppIdentityError('Token used too late, %d > %d: %s' %
      (now, latest, json_body))

  # Check audience.
  if audience is not None:
    aud = parsed.get('aud')
    if aud is None:
      raise AppIdentityError('No aud field in token: %s' % json_body)
    if aud != audience:
      raise AppIdentityError('Wrong recipient, %s != %s: %s' %
          (aud, audience, json_body))

  return parsed

########NEW FILE########
__FILENAME__ = django_orm
# Copyright (C) 2010 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""OAuth 2.0 utilities for Django.

Utilities for using OAuth 2.0 in conjunction with
the Django datastore.
"""

__author__ = 'jcgregorio@google.com (Joe Gregorio)'

import oauth2client
import base64
import pickle

from django.db import models
from oauth2client.client import Storage as BaseStorage

class CredentialsField(models.Field):

  __metaclass__ = models.SubfieldBase

  def get_internal_type(self):
    return "TextField"

  def to_python(self, value):
    if not value:
      return None
    if isinstance(value, oauth2client.client.Credentials):
      return value
    return pickle.loads(base64.b64decode(value))

  def get_db_prep_value(self, value, connection, prepared=False):
    return base64.b64encode(pickle.dumps(value))


class FlowField(models.Field):

  __metaclass__ = models.SubfieldBase

  def get_internal_type(self):
    return "TextField"

  def to_python(self, value):
    if value is None:
      return None
    if isinstance(value, oauth2client.client.Flow):
      return value
    return pickle.loads(base64.b64decode(value))

  def get_db_prep_value(self, value, connection, prepared=False):
    return base64.b64encode(pickle.dumps(value))


class Storage(BaseStorage):
  """Store and retrieve a single credential to and from
  the datastore.

  This Storage helper presumes the Credentials
  have been stored as a CredenialsField
  on a db model class.
  """

  def __init__(self, model_class, key_name, key_value, property_name):
    """Constructor for Storage.

    Args:
      model: db.Model, model class
      key_name: string, key name for the entity that has the credentials
      key_value: string, key value for the entity that has the credentials
      property_name: string, name of the property that is an CredentialsProperty
    """
    self.model_class = model_class
    self.key_name = key_name
    self.key_value = key_value
    self.property_name = property_name

  def locked_get(self):
    """Retrieve Credential from datastore.

    Returns:
      oauth2client.Credentials
    """
    credential = None

    query = {self.key_name: self.key_value}
    entities = self.model_class.objects.filter(**query)
    if len(entities) > 0:
      credential = getattr(entities[0], self.property_name)
      if credential and hasattr(credential, 'set_store'):
        credential.set_store(self)
    return credential

  def locked_put(self, credentials):
    """Write a Credentials to the datastore.

    Args:
      credentials: Credentials, the credentials to store.
    """
    args = {self.key_name: self.key_value}
    entity = self.model_class(**args)
    setattr(entity, self.property_name, credentials)
    entity.save()

  def locked_delete(self):
    """Delete Credentials from the datastore."""

    query = {self.key_name: self.key_value}
    entities = self.model_class.objects.filter(**query).delete()

########NEW FILE########
__FILENAME__ = file
# Copyright (C) 2010 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Utilities for OAuth.

Utilities for making it easier to work with OAuth 2.0
credentials.
"""

__author__ = 'jcgregorio@google.com (Joe Gregorio)'

import os
import stat
import threading

from anyjson import simplejson
from client import Storage as BaseStorage
from client import Credentials


class Storage(BaseStorage):
  """Store and retrieve a single credential to and from a file."""

  def __init__(self, filename):
    self._filename = filename
    self._lock = threading.Lock()

  def acquire_lock(self):
    """Acquires any lock necessary to access this Storage.

    This lock is not reentrant."""
    self._lock.acquire()

  def release_lock(self):
    """Release the Storage lock.

    Trying to release a lock that isn't held will result in a
    RuntimeError.
    """
    self._lock.release()

  def locked_get(self):
    """Retrieve Credential from file.

    Returns:
      oauth2client.client.Credentials
    """
    credentials = None
    try:
      f = open(self._filename, 'rb')
      content = f.read()
      f.close()
    except IOError:
      return credentials

    try:
      credentials = Credentials.new_from_json(content)
      credentials.set_store(self)
    except ValueError:
      pass

    return credentials

  def _create_file_if_needed(self):
    """Create an empty file if necessary.

    This method will not initialize the file. Instead it implements a
    simple version of "touch" to ensure the file has been created.
    """
    if not os.path.exists(self._filename):
      old_umask = os.umask(0177)
      try:
        open(self._filename, 'a+b').close()
      finally:
        os.umask(old_umask)

  def locked_put(self, credentials):
    """Write Credentials to file.

    Args:
      credentials: Credentials, the credentials to store.
    """

    self._create_file_if_needed()
    f = open(self._filename, 'wb')
    f.write(credentials.to_json())
    f.close()

  def locked_delete(self):
    """Delete Credentials file.

    Args:
      credentials: Credentials, the credentials to store.
    """

    os.unlink(self._filename)

########NEW FILE########
__FILENAME__ = multistore_file
# Copyright 2011 Google Inc. All Rights Reserved.

"""Multi-credential file store with lock support.

This module implements a JSON credential store where multiple
credentials can be stored in one file.  That file supports locking
both in a single process and across processes.

The credential themselves are keyed off of:
* client_id
* user_agent
* scope

The format of the stored data is like so:
{
  'file_version': 1,
  'data': [
    {
      'key': {
        'clientId': '<client id>',
        'userAgent': '<user agent>',
        'scope': '<scope>'
      },
      'credential': {
        # JSON serialized Credentials.
      }
    }
  ]
}
"""

__author__ = 'jbeda@google.com (Joe Beda)'

import base64
import errno
import fcntl
import logging
import os
import threading

from anyjson import simplejson
from client import Storage as BaseStorage
from client import Credentials

logger = logging.getLogger(__name__)

# A dict from 'filename'->_MultiStore instances
_multistores = {}
_multistores_lock = threading.Lock()


class Error(Exception):
  """Base error for this module."""
  pass


class NewerCredentialStoreError(Error):
  """The credential store is a newer version that supported."""
  pass


def get_credential_storage(filename, client_id, user_agent, scope,
                           warn_on_readonly=True):
  """Get a Storage instance for a credential.

  Args:
    filename: The JSON file storing a set of credentials
    client_id: The client_id for the credential
    user_agent: The user agent for the credential
    scope: string or list of strings, Scope(s) being requested
    warn_on_readonly: if True, log a warning if the store is readonly

  Returns:
    An object derived from client.Storage for getting/setting the
    credential.
  """
  filename = os.path.realpath(os.path.expanduser(filename))
  _multistores_lock.acquire()
  try:
    multistore = _multistores.setdefault(
        filename, _MultiStore(filename, warn_on_readonly))
  finally:
    _multistores_lock.release()
  if type(scope) is list:
    scope = ' '.join(scope)
  return multistore._get_storage(client_id, user_agent, scope)


class _MultiStore(object):
  """A file backed store for multiple credentials."""

  def __init__(self, filename, warn_on_readonly=True):
    """Initialize the class.

    This will create the file if necessary.
    """
    self._filename = filename
    self._thread_lock = threading.Lock()
    self._file_handle = None
    self._read_only = False
    self._warn_on_readonly = warn_on_readonly

    self._create_file_if_needed()

    # Cache of deserialized store.  This is only valid after the
    # _MultiStore is locked or _refresh_data_cache is called.  This is
    # of the form of:
    #
    # (client_id, user_agent, scope) -> OAuth2Credential
    #
    # If this is None, then the store hasn't been read yet.
    self._data = None

  class _Storage(BaseStorage):
    """A Storage object that knows how to read/write a single credential."""

    def __init__(self, multistore, client_id, user_agent, scope):
      self._multistore = multistore
      self._client_id = client_id
      self._user_agent = user_agent
      self._scope = scope

    def acquire_lock(self):
      """Acquires any lock necessary to access this Storage.

      This lock is not reentrant.
      """
      self._multistore._lock()

    def release_lock(self):
      """Release the Storage lock.

      Trying to release a lock that isn't held will result in a
      RuntimeError.
      """
      self._multistore._unlock()

    def locked_get(self):
      """Retrieve credential.

      The Storage lock must be held when this is called.

      Returns:
        oauth2client.client.Credentials
      """
      credential = self._multistore._get_credential(
          self._client_id, self._user_agent, self._scope)
      if credential:
        credential.set_store(self)
      return credential

    def locked_put(self, credentials):
      """Write a credential.

      The Storage lock must be held when this is called.

      Args:
        credentials: Credentials, the credentials to store.
      """
      self._multistore._update_credential(credentials, self._scope)

    def locked_delete(self):
      """Delete a credential.

      The Storage lock must be held when this is called.

      Args:
        credentials: Credentials, the credentials to store.
      """
      self._multistore._delete_credential(self._client_id, self._user_agent,
          self._scope)

  def _create_file_if_needed(self):
    """Create an empty file if necessary.

    This method will not initialize the file. Instead it implements a
    simple version of "touch" to ensure the file has been created.
    """
    if not os.path.exists(self._filename):
      old_umask = os.umask(0177)
      try:
        open(self._filename, 'a+b').close()
      finally:
        os.umask(old_umask)

  def _lock(self):
    """Lock the entire multistore."""
    self._thread_lock.acquire()
    # Check to see if the file is writeable.
    try:
      self._file_handle = open(self._filename, 'r+b')
      fcntl.lockf(self._file_handle.fileno(), fcntl.LOCK_EX)
    except IOError, e:
      if e.errno != errno.EACCES:
        raise e
      self._file_handle = open(self._filename, 'rb')
      self._read_only = True
      if self._warn_on_readonly:
        logger.warn('The credentials file (%s) is not writable. Opening in '
                    'read-only mode. Any refreshed credentials will only be '
                    'valid for this run.' % self._filename)
    if os.path.getsize(self._filename) == 0:
      logger.debug('Initializing empty multistore file')
      # The multistore is empty so write out an empty file.
      self._data = {}
      self._write()
    elif not self._read_only or self._data is None:
      # Only refresh the data if we are read/write or we haven't
      # cached the data yet.  If we are readonly, we assume is isn't
      # changing out from under us and that we only have to read it
      # once.  This prevents us from whacking any new access keys that
      # we have cached in memory but were unable to write out.
      self._refresh_data_cache()

  def _unlock(self):
    """Release the lock on the multistore."""
    if not self._read_only:
      fcntl.lockf(self._file_handle.fileno(), fcntl.LOCK_UN)
    self._file_handle.close()
    self._thread_lock.release()

  def _locked_json_read(self):
    """Get the raw content of the multistore file.

    The multistore must be locked when this is called.

    Returns:
      The contents of the multistore decoded as JSON.
    """
    assert self._thread_lock.locked()
    self._file_handle.seek(0)
    return simplejson.load(self._file_handle)

  def _locked_json_write(self, data):
    """Write a JSON serializable data structure to the multistore.

    The multistore must be locked when this is called.

    Args:
      data: The data to be serialized and written.
    """
    assert self._thread_lock.locked()
    if self._read_only:
      return
    self._file_handle.seek(0)
    simplejson.dump(data, self._file_handle, sort_keys=True, indent=2)
    self._file_handle.truncate()

  def _refresh_data_cache(self):
    """Refresh the contents of the multistore.

    The multistore must be locked when this is called.

    Raises:
      NewerCredentialStoreError: Raised when a newer client has written the
        store.
    """
    self._data = {}
    try:
      raw_data = self._locked_json_read()
    except Exception:
      logger.warn('Credential data store could not be loaded. '
                  'Will ignore and overwrite.')
      return

    version = 0
    try:
      version = raw_data['file_version']
    except Exception:
      logger.warn('Missing version for credential data store. It may be '
                  'corrupt or an old version. Overwriting.')
    if version > 1:
      raise NewerCredentialStoreError(
          'Credential file has file_version of %d. '
          'Only file_version of 1 is supported.' % version)

    credentials = []
    try:
      credentials = raw_data['data']
    except (TypeError, KeyError):
      pass

    for cred_entry in credentials:
      try:
        (key, credential) = self._decode_credential_from_json(cred_entry)
        self._data[key] = credential
      except:
        # If something goes wrong loading a credential, just ignore it
        logger.info('Error decoding credential, skipping', exc_info=True)

  def _decode_credential_from_json(self, cred_entry):
    """Load a credential from our JSON serialization.

    Args:
      cred_entry: A dict entry from the data member of our format

    Returns:
      (key, cred) where the key is the key tuple and the cred is the
        OAuth2Credential object.
    """
    raw_key = cred_entry['key']
    client_id = raw_key['clientId']
    user_agent = raw_key['userAgent']
    scope = raw_key['scope']
    key = (client_id, user_agent, scope)
    credential = None
    credential = Credentials.new_from_json(simplejson.dumps(cred_entry['credential']))
    return (key, credential)

  def _write(self):
    """Write the cached data back out.

    The multistore must be locked.
    """
    raw_data = {'file_version': 1}
    raw_creds = []
    raw_data['data'] = raw_creds
    for (cred_key, cred) in self._data.items():
      raw_key = {
          'clientId': cred_key[0],
          'userAgent': cred_key[1],
          'scope': cred_key[2]
          }
      raw_cred = simplejson.loads(cred.to_json())
      raw_creds.append({'key': raw_key, 'credential': raw_cred})
    self._locked_json_write(raw_data)

  def _get_credential(self, client_id, user_agent, scope):
    """Get a credential from the multistore.

    The multistore must be locked.

    Args:
      client_id: The client_id for the credential
      user_agent: The user agent for the credential
      scope: A string for the scope(s) being requested

    Returns:
      The credential specified or None if not present
    """
    key = (client_id, user_agent, scope)

    return self._data.get(key, None)

  def _update_credential(self, cred, scope):
    """Update a credential and write the multistore.

    This must be called when the multistore is locked.

    Args:
      cred: The OAuth2Credential to update/set
      scope: The scope(s) that this credential covers
    """
    key = (cred.client_id, cred.user_agent, scope)
    self._data[key] = cred
    self._write()

  def _delete_credential(self, client_id, user_agent, scope):
    """Delete a credential and write the multistore.

    This must be called when the multistore is locked.

    Args:
      client_id: The client_id for the credential
      user_agent: The user agent for the credential
      scope: The scope(s) that this credential covers
    """
    key = (client_id, user_agent, scope)
    try:
      del self._data[key]
    except KeyError:
      pass
    self._write()

  def _get_storage(self, client_id, user_agent, scope):
    """Get a Storage object to get/set a credential.

    This Storage is a 'view' into the multistore.

    Args:
      client_id: The client_id for the credential
      user_agent: The user agent for the credential
      scope: A string for the scope(s) being requested

    Returns:
      A Storage object that can be used to get/set this cred
    """
    return self._Storage(self, client_id, user_agent, scope)

########NEW FILE########
__FILENAME__ = tools
# Copyright (C) 2010 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Command-line tools for authenticating via OAuth 2.0

Do the OAuth 2.0 Web Server dance for a command line application. Stores the
generated credentials in a common file that is used by other example apps in
the same directory.
"""

__author__ = 'jcgregorio@google.com (Joe Gregorio)'
__all__ = ['run']


import BaseHTTPServer
import gflags
import socket
import sys
import webbrowser

from client import FlowExchangeError
from client import OOB_CALLBACK_URN

try:
  from urlparse import parse_qsl
except ImportError:
  from cgi import parse_qsl


FLAGS = gflags.FLAGS

gflags.DEFINE_boolean('auth_local_webserver', True,
                      ('Run a local web server to handle redirects during '
                       'OAuth authorization.'))

gflags.DEFINE_string('auth_host_name', 'localhost',
                     ('Host name to use when running a local web server to '
                      'handle redirects during OAuth authorization.'))

gflags.DEFINE_multi_int('auth_host_port', [8080, 8090],
                        ('Port to use when running a local web server to '
                         'handle redirects during OAuth authorization.'))


class ClientRedirectServer(BaseHTTPServer.HTTPServer):
  """A server to handle OAuth 2.0 redirects back to localhost.

  Waits for a single request and parses the query parameters
  into query_params and then stops serving.
  """
  query_params = {}


class ClientRedirectHandler(BaseHTTPServer.BaseHTTPRequestHandler):
  """A handler for OAuth 2.0 redirects back to localhost.

  Waits for a single request and parses the query parameters
  into the servers query_params and then stops serving.
  """

  def do_GET(s):
    """Handle a GET request.

    Parses the query parameters and prints a message
    if the flow has completed. Note that we can't detect
    if an error occurred.
    """
    s.send_response(200)
    s.send_header("Content-type", "text/html")
    s.end_headers()
    query = s.path.split('?', 1)[-1]
    query = dict(parse_qsl(query))
    s.server.query_params = query
    s.wfile.write("<html><head><title>Authentication Status</title></head>")
    s.wfile.write("<body><p>The authentication flow has completed.</p>")
    s.wfile.write("</body></html>")

  def log_message(self, format, *args):
    """Do not log messages to stdout while running as command line program."""
    pass


def run(flow, storage, http=None):
  """Core code for a command-line application.

  Args:
    flow: Flow, an OAuth 2.0 Flow to step through.
    storage: Storage, a Storage to store the credential in.
    http: An instance of httplib2.Http.request
         or something that acts like it.

  Returns:
    Credentials, the obtained credential.
  """
  if FLAGS.auth_local_webserver:
    success = False
    port_number = 0
    for port in FLAGS.auth_host_port:
      port_number = port
      try:
        httpd = ClientRedirectServer((FLAGS.auth_host_name, port),
                                     ClientRedirectHandler)
      except socket.error, e:
        pass
      else:
        success = True
        break
    FLAGS.auth_local_webserver = success

  if FLAGS.auth_local_webserver:
    oauth_callback = 'http://%s:%s/' % (FLAGS.auth_host_name, port_number)
  else:
    oauth_callback = OOB_CALLBACK_URN
  authorize_url = flow.step1_get_authorize_url(oauth_callback)

  if FLAGS.auth_local_webserver:
    webbrowser.open(authorize_url, new=1, autoraise=True)
    print 'Your browser has been opened to visit:'
    print
    print '    ' + authorize_url
    print
    print 'If your browser is on a different machine then exit and re-run this'
    print 'application with the command-line parameter '
    print
    print '  --noauth_local_webserver'
    print
  else:
    print 'Go to the following link in your browser:'
    print
    print '    ' + authorize_url
    print

  code = None
  if FLAGS.auth_local_webserver:
    httpd.handle_request()
    if 'error' in httpd.query_params:
      sys.exit('Authentication request was rejected.')
    if 'code' in httpd.query_params:
      code = httpd.query_params['code']
    else:
      print 'Failed to find "code" in the query parameters of the redirect.'
      sys.exit('Try running with --noauth_local_webserver.')
  else:
    code = raw_input('Enter verification code: ').strip()

  try:
    credential = flow.step2_exchange(code, http)
  except FlowExchangeError, e:
    sys.exit('Authentication has failed: %s' % e)

  storage.put(credential)
  credential.set_store(storage)
  print 'Authentication successful.'

  return credential

########NEW FILE########
__FILENAME__ = scrape
import httplib2
import pprint
import sys
import urllib2
import simplejson
import MySQLdb
import dbauth
import random
import requests
from time import sleep
from bs4 import BeautifulSoup
from twitter_auth import token, token_secret, consumer, consumer_secret
from twitter import Twitter, OAuth
import subprocess
import json
import time
import dateutil.parser

def insult(name):
    person = '@' + name
    i = ['Watch your mouth, ' + person, 
        person + ', I love it when you talk dirty', 
        'Very disappointed with your language, ' + person, 
        'Yo,' + person + ', quit cursing in your code!',
        person + ', you should be ashamed for using this kind of language.',
        person + ', you kiss your mother with that mouth?',
        person.upper() + ' CURSES IN HIS !@*^ING CODE',
        person + ', act professional and quit using bad words. Fucker.',
        'Impressive vocabulary, ' + person,
        person + ', fucking cursing in your code and shit.',
        'Hope your manager doesn\'t see this, ' + person + '!'
        ]

    return random.choice(i)

def find_avatar(userurl):
    r = urllib2.urlopen(userurl)
    body = r.read()
    soup = BeautifulSoup(body)
    for img in soup.find_all("img"):
        print img
        try:
            if img.get('src').index('avatar') > 0:
                return img.get('src')
        except:
            continue


def process(output):
    for row in output:
        try:
            userurl = "https://" + row['userurl']
            avatar = find_avatar(userurl)
            created_at = dbauth.db.escape_string(dateutil.parser.parse(row['created_at']).strftime('%Y-%m-%d %H:%M:%S'))
            query = "INSERT INTO new_commits VALUES ('', \'%s\', \'%s\', \'%s\', \'%s\', \'%s\', \'%s\', '')" % (row['commiter'], dbauth.db.escape_string(row['message']), avatar, dbauth.db.escape_string(row['commiturl']), dbauth.db.escape_string(userurl), created_at)
            cursor.execute(query)
        except Exception as e:
            print e
            continue

while True:
    cursor = dbauth.db.cursor()
    t = Twitter(
        auth=OAuth(token, token_secret, consumer, consumer_secret))

    output = subprocess.Popen(["/home/abasababa/.rvm/rubies/ruby-2.1.1/bin/ruby", "/home/abasababa/webapps/commit/get_commits.rb"], stdout=subprocess.PIPE).communicate()[0]
    output = json.loads(output)

    process(output)

    time.sleep(3600)

########NEW FILE########
