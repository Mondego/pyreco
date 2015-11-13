__FILENAME__ = handler
# Copyright (C) 2013 Google Inc.
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

"""Request Handler for /main endpoint."""

__author__ = 'alainv@google.com (Alain Vongsouvanh)'


import logging
import webapp2

from util import auth_required


class AttachmentProxyHandler(webapp2.RequestHandler):
  """Request Handler for the main endpoint."""

  @auth_required
  def get(self):
    """Return the attachment's content using the current user's credentials."""
    # self.mirror_service is initialized in util.auth_required.
    attachment_id = self.request.get('attachment')
    item_id = self.request.get('timelineItem')
    logging.info('Attachment ID: %s', attachment_id)
    if not attachment_id or not item_id:
      self.response.set_status(400)
      return
    else:
      # Retrieve the attachment's metadata.
      attachment_metadata = self.mirror_service.timeline().attachments().get(
          itemId=item_id, attachmentId=attachment_id).execute()
      content_type = str(attachment_metadata.get('contentType'))
      content_url = attachment_metadata.get('contentUrl')

      # Retrieve the attachment's content.
      resp, content = self.mirror_service._http.request(content_url)
      if resp.status == 200:
        self.response.headers.add_header('Content-type', content_type)
        self.response.out.write(content)
      else:
        logging.info('Unable to retrieve attachment: %s', resp.status)
        self.response.set_status(500)


ATTACHMENT_PROXY_ROUTES = [
    ('/attachmentproxy', AttachmentProxyHandler)
]

########NEW FILE########
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

"""Client for discovery based APIs.

A client library for Google's discovery based APIs.
"""

__author__ = 'jcgregorio@google.com (Joe Gregorio)'
__all__ = [
    'build',
    'build_from_document',
    'fix_method_name',
    'key2param',
    ]


# Standard library imports
import copy
from email.mime.multipart import MIMEMultipart
from email.mime.nonmultipart import MIMENonMultipart
import keyword
import logging
import mimetypes
import os
import re
import urllib
import urlparse

try:
  from urlparse import parse_qsl
except ImportError:
  from cgi import parse_qsl

# Third-party imports
import httplib2
import mimeparse
import uritemplate

# Local imports
from apiclient.errors import HttpError
from apiclient.errors import InvalidJsonError
from apiclient.errors import MediaUploadSizeError
from apiclient.errors import UnacceptableMimeTypeError
from apiclient.errors import UnknownApiNameOrVersion
from apiclient.errors import UnknownFileType
from apiclient.http import HttpRequest
from apiclient.http import MediaFileUpload
from apiclient.http import MediaUpload
from apiclient.model import JsonModel
from apiclient.model import MediaModel
from apiclient.model import RawModel
from apiclient.schema import Schemas
from oauth2client.anyjson import simplejson
from oauth2client.util import _add_query_parameter
from oauth2client.util import positional


# The client library requires a version of httplib2 that supports RETRIES.
httplib2.RETRIES = 1

logger = logging.getLogger(__name__)

URITEMPLATE = re.compile('{[^}]*}')
VARNAME = re.compile('[a-zA-Z0-9_-]+')
DISCOVERY_URI = ('https://www.googleapis.com/discovery/v1/apis/'
                 '{api}/{apiVersion}/rest')
DEFAULT_METHOD_DOC = 'A description of how to use this function'
HTTP_PAYLOAD_METHODS = frozenset(['PUT', 'POST', 'PATCH'])
_MEDIA_SIZE_BIT_SHIFTS = {'KB': 10, 'MB': 20, 'GB': 30, 'TB': 40}
BODY_PARAMETER_DEFAULT_VALUE = {
    'description': 'The request body.',
    'type': 'object',
    'required': True,
}
MEDIA_BODY_PARAMETER_DEFAULT_VALUE = {
    'description': ('The filename of the media request body, or an instance '
                    'of a MediaUpload object.'),
    'type': 'string',
    'required': False,
}

# Parameters accepted by the stack, but not visible via discovery.
# TODO(dhermes): Remove 'userip' in 'v2'.
STACK_QUERY_PARAMETERS = frozenset(['trace', 'pp', 'userip', 'strict'])
STACK_QUERY_PARAMETER_DEFAULT_VALUE = {'type': 'string', 'location': 'query'}

# Library-specific reserved words beyond Python keywords.
RESERVED_WORDS = frozenset(['body'])


def fix_method_name(name):
  """Fix method names to avoid reserved word conflicts.

  Args:
    name: string, method name.

  Returns:
    The name with a '_' prefixed if the name is a reserved word.
  """
  if keyword.iskeyword(name) or name in RESERVED_WORDS:
    return name + '_'
  else:
    return name


def key2param(key):
  """Converts key names into parameter names.

  For example, converting "max-results" -> "max_results"

  Args:
    key: string, the method key name.

  Returns:
    A safe method name based on the key name.
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


@positional(2)
def build(serviceName,
          version,
          http=None,
          discoveryServiceUrl=DISCOVERY_URI,
          developerKey=None,
          model=None,
          requestBuilder=HttpRequest):
  """Construct a Resource for interacting with an API.

  Construct a Resource object for interacting with an API. The serviceName and
  version are the names from the Discovery service.

  Args:
    serviceName: string, name of the service.
    version: string, the version of the service.
    http: httplib2.Http, An instance of httplib2.Http or something that acts
      like it that HTTP requests will be made through.
    discoveryServiceUrl: string, a URI Template that points to the location of
      the discovery service. It should have two parameters {api} and
      {apiVersion} that when filled in produce an absolute URI to the discovery
      document for that service.
    developerKey: string, key obtained from
      https://code.google.com/apis/console.
    model: apiclient.Model, converts to and from the wire format.
    requestBuilder: apiclient.http.HttpRequest, encapsulator for an HTTP
      request.

  Returns:
    A Resource object with methods for interacting with the service.
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
  logger.info('URL being requested: %s' % requested_url)

  resp, content = http.request(requested_url)

  if resp.status == 404:
    raise UnknownApiNameOrVersion("name: %s  version: %s" % (serviceName,
                                                            version))
  if resp.status >= 400:
    raise HttpError(resp, content, uri=requested_url)

  try:
    service = simplejson.loads(content)
  except ValueError, e:
    logger.error('Failed to parse as JSON: ' + content)
    raise InvalidJsonError()

  return build_from_document(content, base=discoveryServiceUrl, http=http,
      developerKey=developerKey, model=model, requestBuilder=requestBuilder)


@positional(1)
def build_from_document(
    service,
    base=None,
    future=None,
    http=None,
    developerKey=None,
    model=None,
    requestBuilder=HttpRequest):
  """Create a Resource for interacting with an API.

  Same as `build()`, but constructs the Resource object from a discovery
  document that is it given, as opposed to retrieving one over HTTP.

  Args:
    service: string or object, the JSON discovery document describing the API.
      The value passed in may either be the JSON string or the deserialized
      JSON.
    base: string, base URI for all HTTP requests, usually the discovery URI.
      This parameter is no longer used as rootUrl and servicePath are included
      within the discovery document. (deprecated)
    future: string, discovery document with future capabilities (deprecated).
    http: httplib2.Http, An instance of httplib2.Http or something that acts
      like it that HTTP requests will be made through.
    developerKey: string, Key for controlling API usage, generated
      from the API Console.
    model: Model class instance that serializes and de-serializes requests and
      responses.
    requestBuilder: Takes an http request and packages it up to be executed.

  Returns:
    A Resource object with methods for interacting with the service.
  """

  # future is no longer used.
  future = {}

  if isinstance(service, basestring):
    service = simplejson.loads(service)
  base = urlparse.urljoin(service['rootUrl'], service['servicePath'])
  schema = Schemas(service)

  if model is None:
    features = service.get('features', [])
    model = JsonModel('dataWrapper' in features)
  return Resource(http=http, baseUrl=base, model=model,
                  developerKey=developerKey, requestBuilder=requestBuilder,
                  resourceDesc=service, rootDesc=service, schema=schema)


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


def _media_size_to_long(maxSize):
  """Convert a string media size, such as 10GB or 3TB into an integer.

  Args:
    maxSize: string, size as a string, such as 2MB or 7GB.

  Returns:
    The size as an integer value.
  """
  if len(maxSize) < 2:
    return 0L
  units = maxSize[-2:].upper()
  bit_shift = _MEDIA_SIZE_BIT_SHIFTS.get(units)
  if bit_shift is not None:
    return long(maxSize[:-2]) << bit_shift
  else:
    return long(maxSize)


def _media_path_url_from_info(root_desc, path_url):
  """Creates an absolute media path URL.

  Constructed using the API root URI and service path from the discovery
  document and the relative path for the API method.

  Args:
    root_desc: Dictionary; the entire original deserialized discovery document.
    path_url: String; the relative URL for the API method. Relative to the API
        root, which is specified in the discovery document.

  Returns:
    String; the absolute URI for media upload for the API method.
  """
  return '%(root)supload/%(service_path)s%(path)s' % {
      'root': root_desc['rootUrl'],
      'service_path': root_desc['servicePath'],
      'path': path_url,
  }


def _fix_up_parameters(method_desc, root_desc, http_method):
  """Updates parameters of an API method with values specific to this library.

  Specifically, adds whatever global parameters are specified by the API to the
  parameters for the individual method. Also adds parameters which don't
  appear in the discovery document, but are available to all discovery based
  APIs (these are listed in STACK_QUERY_PARAMETERS).

  SIDE EFFECTS: This updates the parameters dictionary object in the method
  description.

  Args:
    method_desc: Dictionary with metadata describing an API method. Value comes
        from the dictionary of methods stored in the 'methods' key in the
        deserialized discovery document.
    root_desc: Dictionary; the entire original deserialized discovery document.
    http_method: String; the HTTP method used to call the API method described
        in method_desc.

  Returns:
    The updated Dictionary stored in the 'parameters' key of the method
        description dictionary.
  """
  parameters = method_desc.setdefault('parameters', {})

  # Add in the parameters common to all methods.
  for name, description in root_desc.get('parameters', {}).iteritems():
    parameters[name] = description

  # Add in undocumented query parameters.
  for name in STACK_QUERY_PARAMETERS:
    parameters[name] = STACK_QUERY_PARAMETER_DEFAULT_VALUE.copy()

  # Add 'body' (our own reserved word) to parameters if the method supports
  # a request payload.
  if http_method in HTTP_PAYLOAD_METHODS and 'request' in method_desc:
    body = BODY_PARAMETER_DEFAULT_VALUE.copy()
    body.update(method_desc['request'])
    parameters['body'] = body

  return parameters


def _fix_up_media_upload(method_desc, root_desc, path_url, parameters):
  """Updates parameters of API by adding 'media_body' if supported by method.

  SIDE EFFECTS: If the method supports media upload and has a required body,
  sets body to be optional (required=False) instead. Also, if there is a
  'mediaUpload' in the method description, adds 'media_upload' key to
  parameters.

  Args:
    method_desc: Dictionary with metadata describing an API method. Value comes
        from the dictionary of methods stored in the 'methods' key in the
        deserialized discovery document.
    root_desc: Dictionary; the entire original deserialized discovery document.
    path_url: String; the relative URL for the API method. Relative to the API
        root, which is specified in the discovery document.
    parameters: A dictionary describing method parameters for method described
        in method_desc.

  Returns:
    Triple (accept, max_size, media_path_url) where:
      - accept is a list of strings representing what content types are
        accepted for media upload. Defaults to empty list if not in the
        discovery document.
      - max_size is a long representing the max size in bytes allowed for a
        media upload. Defaults to 0L if not in the discovery document.
      - media_path_url is a String; the absolute URI for media upload for the
        API method. Constructed using the API root URI and service path from
        the discovery document and the relative path for the API method. If
        media upload is not supported, this is None.
  """
  media_upload = method_desc.get('mediaUpload', {})
  accept = media_upload.get('accept', [])
  max_size = _media_size_to_long(media_upload.get('maxSize', ''))
  media_path_url = None

  if media_upload:
    media_path_url = _media_path_url_from_info(root_desc, path_url)
    parameters['media_body'] = MEDIA_BODY_PARAMETER_DEFAULT_VALUE.copy()
    if 'body' in parameters:
      parameters['body']['required'] = False

  return accept, max_size, media_path_url


def _fix_up_method_description(method_desc, root_desc):
  """Updates a method description in a discovery document.

  SIDE EFFECTS: Changes the parameters dictionary in the method description with
  extra parameters which are used locally.

  Args:
    method_desc: Dictionary with metadata describing an API method. Value comes
        from the dictionary of methods stored in the 'methods' key in the
        deserialized discovery document.
    root_desc: Dictionary; the entire original deserialized discovery document.

  Returns:
    Tuple (path_url, http_method, method_id, accept, max_size, media_path_url)
    where:
      - path_url is a String; the relative URL for the API method. Relative to
        the API root, which is specified in the discovery document.
      - http_method is a String; the HTTP method used to call the API method
        described in the method description.
      - method_id is a String; the name of the RPC method associated with the
        API method, and is in the method description in the 'id' key.
      - accept is a list of strings representing what content types are
        accepted for media upload. Defaults to empty list if not in the
        discovery document.
      - max_size is a long representing the max size in bytes allowed for a
        media upload. Defaults to 0L if not in the discovery document.
      - media_path_url is a String; the absolute URI for media upload for the
        API method. Constructed using the API root URI and service path from
        the discovery document and the relative path for the API method. If
        media upload is not supported, this is None.
  """
  path_url = method_desc['path']
  http_method = method_desc['httpMethod']
  method_id = method_desc['id']

  parameters = _fix_up_parameters(method_desc, root_desc, http_method)
  # Order is important. `_fix_up_media_upload` needs `method_desc` to have a
  # 'parameters' key and needs to know if there is a 'body' parameter because it
  # also sets a 'media_body' parameter.
  accept, max_size, media_path_url = _fix_up_media_upload(
      method_desc, root_desc, path_url, parameters)

  return path_url, http_method, method_id, accept, max_size, media_path_url


# TODO(dhermes): Convert this class to ResourceMethod and make it callable
class ResourceMethodParameters(object):
  """Represents the parameters associated with a method.

  Attributes:
    argmap: Map from method parameter name (string) to query parameter name
        (string).
    required_params: List of required parameters (represented by parameter
        name as string).
    repeated_params: List of repeated parameters (represented by parameter
        name as string).
    pattern_params: Map from method parameter name (string) to regular
        expression (as a string). If the pattern is set for a parameter, the
        value for that parameter must match the regular expression.
    query_params: List of parameters (represented by parameter name as string)
        that will be used in the query string.
    path_params: Set of parameters (represented by parameter name as string)
        that will be used in the base URL path.
    param_types: Map from method parameter name (string) to parameter type. Type
        can be any valid JSON schema type; valid values are 'any', 'array',
        'boolean', 'integer', 'number', 'object', or 'string'. Reference:
        http://tools.ietf.org/html/draft-zyp-json-schema-03#section-5.1
    enum_params: Map from method parameter name (string) to list of strings,
       where each list of strings is the list of acceptable enum values.
  """

  def __init__(self, method_desc):
    """Constructor for ResourceMethodParameters.

    Sets default values and defers to set_parameters to populate.

    Args:
      method_desc: Dictionary with metadata describing an API method. Value
          comes from the dictionary of methods stored in the 'methods' key in
          the deserialized discovery document.
    """
    self.argmap = {}
    self.required_params = []
    self.repeated_params = []
    self.pattern_params = {}
    self.query_params = []
    # TODO(dhermes): Change path_params to a list if the extra URITEMPLATE
    #                parsing is gotten rid of.
    self.path_params = set()
    self.param_types = {}
    self.enum_params = {}

    self.set_parameters(method_desc)

  def set_parameters(self, method_desc):
    """Populates maps and lists based on method description.

    Iterates through each parameter for the method and parses the values from
    the parameter dictionary.

    Args:
      method_desc: Dictionary with metadata describing an API method. Value
          comes from the dictionary of methods stored in the 'methods' key in
          the deserialized discovery document.
    """
    for arg, desc in method_desc.get('parameters', {}).iteritems():
      param = key2param(arg)
      self.argmap[param] = arg

      if desc.get('pattern'):
        self.pattern_params[param] = desc['pattern']
      if desc.get('enum'):
        self.enum_params[param] = desc['enum']
      if desc.get('required'):
        self.required_params.append(param)
      if desc.get('repeated'):
        self.repeated_params.append(param)
      if desc.get('location') == 'query':
        self.query_params.append(param)
      if desc.get('location') == 'path':
        self.path_params.add(param)
      self.param_types[param] = desc.get('type', 'string')

    # TODO(dhermes): Determine if this is still necessary. Discovery based APIs
    #                should have all path parameters already marked with
    #                'location: path'.
    for match in URITEMPLATE.finditer(method_desc['path']):
      for namematch in VARNAME.finditer(match.group(0)):
        name = key2param(namematch.group(0))
        self.path_params.add(name)
        if name in self.query_params:
          self.query_params.remove(name)


def createMethod(methodName, methodDesc, rootDesc, schema):
  """Creates a method for attaching to a Resource.

  Args:
    methodName: string, name of the method to use.
    methodDesc: object, fragment of deserialized discovery document that
      describes the method.
    rootDesc: object, the entire deserialized discovery document.
    schema: object, mapping of schema names to schema descriptions.
  """
  methodName = fix_method_name(methodName)
  (pathUrl, httpMethod, methodId, accept,
   maxSize, mediaPathUrl) = _fix_up_method_description(methodDesc, rootDesc)

  parameters = ResourceMethodParameters(methodDesc)

  def method(self, **kwargs):
    # Don't bother with doc string, it will be over-written by createMethod.

    for name in kwargs.iterkeys():
      if name not in parameters.argmap:
        raise TypeError('Got an unexpected keyword argument "%s"' % name)

    # Remove args that have a value of None.
    keys = kwargs.keys()
    for name in keys:
      if kwargs[name] is None:
        del kwargs[name]

    for name in parameters.required_params:
      if name not in kwargs:
        raise TypeError('Missing required parameter "%s"' % name)

    for name, regex in parameters.pattern_params.iteritems():
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

    for name, enums in parameters.enum_params.iteritems():
      if name in kwargs:
        # We need to handle the case of a repeated enum
        # name differently, since we want to handle both
        # arg='value' and arg=['value1', 'value2']
        if (name in parameters.repeated_params and
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
      to_type = parameters.param_types.get(key, 'string')
      # For repeated parameters we cast each member of the list.
      if key in parameters.repeated_params and type(value) == type([]):
        cast_value = [_cast(x, to_type) for x in value]
      else:
        cast_value = _cast(value, to_type)
      if key in parameters.query_params:
        actual_query_params[parameters.argmap[key]] = cast_value
      if key in parameters.path_params:
        actual_path_params[parameters.argmap[key]] = cast_value
    body_value = kwargs.get('body', None)
    media_filename = kwargs.get('media_body', None)

    if self._developerKey:
      actual_query_params['key'] = self._developerKey

    model = self._model
    if methodName.endswith('_media'):
      model = MediaModel()
    elif 'response' not in methodDesc:
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
        media_upload = MediaFileUpload(media_filename,
                                       mimetype=media_mime_type)
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

    logger.info('URL being requested: %s' % url)
    return self._requestBuilder(self._http,
                                model.response,
                                url,
                                method=httpMethod,
                                body=body,
                                headers=headers,
                                methodId=methodId,
                                resumable=resumable)

  docs = [methodDesc.get('description', DEFAULT_METHOD_DOC), '\n\n']
  if len(parameters.argmap) > 0:
    docs.append('Args:\n')

  # Skip undocumented params and params common to all methods.
  skip_parameters = rootDesc.get('parameters', {}).keys()
  skip_parameters.extend(STACK_QUERY_PARAMETERS)

  all_args = parameters.argmap.keys()
  args_ordered = [key2param(s) for s in methodDesc.get('parameterOrder', [])]

  # Move body to the front of the line.
  if 'body' in all_args:
    args_ordered.append('body')

  for name in all_args:
    if name not in args_ordered:
      args_ordered.append(name)

  for arg in args_ordered:
    if arg in skip_parameters:
      continue

    repeated = ''
    if arg in parameters.repeated_params:
      repeated = ' (repeated)'
    required = ''
    if arg in parameters.required_params:
      required = ' (required)'
    paramdesc = methodDesc['parameters'][parameters.argmap[arg]]
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
    if methodName.endswith('_media'):
      docs.append('\nReturns:\n  The media object as a string.\n\n    ')
    else:
      docs.append('\nReturns:\n  An object of the form:\n\n    ')
      docs.append(schema.prettyPrintSchema(methodDesc['response']))

  setattr(method, '__doc__', ''.join(docs))
  return (methodName, method)


def createNextMethod(methodName):
  """Creates any _next methods for attaching to a Resource.

  The _next methods allow for easy iteration through list() responses.

  Args:
    methodName: string, name of the method to use.
  """
  methodName = fix_method_name(methodName)

  def methodNext(self, previous_request, previous_response):
    """Retrieves the next page of results.

Args:
  previous_request: The request for the previous page. (required)
  previous_response: The response from the request for the previous page. (required)

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

    logger.info('URL being requested: %s' % uri)

    return request

  return (methodName, methodNext)


class Resource(object):
  """A class for interacting with a resource."""

  def __init__(self, http, baseUrl, model, requestBuilder, developerKey,
               resourceDesc, rootDesc, schema):
    """Build a Resource from the API description.

    Args:
      http: httplib2.Http, Object to make http requests with.
      baseUrl: string, base URL for the API. All requests are relative to this
          URI.
      model: apiclient.Model, converts to and from the wire format.
      requestBuilder: class or callable that instantiates an
          apiclient.HttpRequest object.
      developerKey: string, key obtained from
          https://code.google.com/apis/console
      resourceDesc: object, section of deserialized discovery document that
          describes a resource. Note that the top level discovery document
          is considered a resource.
      rootDesc: object, the entire deserialized discovery document.
      schema: object, mapping of schema names to schema descriptions.
    """
    self._dynamic_attrs = []

    self._http = http
    self._baseUrl = baseUrl
    self._model = model
    self._developerKey = developerKey
    self._requestBuilder = requestBuilder
    self._resourceDesc = resourceDesc
    self._rootDesc = rootDesc
    self._schema = schema

    self._set_service_methods()

  def _set_dynamic_attr(self, attr_name, value):
    """Sets an instance attribute and tracks it in a list of dynamic attributes.

    Args:
      attr_name: string; The name of the attribute to be set
      value: The value being set on the object and tracked in the dynamic cache.
    """
    self._dynamic_attrs.append(attr_name)
    self.__dict__[attr_name] = value

  def __getstate__(self):
    """Trim the state down to something that can be pickled.

    Uses the fact that the instance variable _dynamic_attrs holds attrs that
    will be wiped and restored on pickle serialization.
    """
    state_dict = copy.copy(self.__dict__)
    for dynamic_attr in self._dynamic_attrs:
      del state_dict[dynamic_attr]
    del state_dict['_dynamic_attrs']
    return state_dict

  def __setstate__(self, state):
    """Reconstitute the state of the object from being pickled.

    Uses the fact that the instance variable _dynamic_attrs holds attrs that
    will be wiped and restored on pickle serialization.
    """
    self.__dict__.update(state)
    self._dynamic_attrs = []
    self._set_service_methods()

  def _set_service_methods(self):
    self._add_basic_methods(self._resourceDesc, self._rootDesc, self._schema)
    self._add_nested_resources(self._resourceDesc, self._rootDesc, self._schema)
    self._add_next_methods(self._resourceDesc, self._schema)

  def _add_basic_methods(self, resourceDesc, rootDesc, schema):
    # Add basic methods to Resource
    if 'methods' in resourceDesc:
      for methodName, methodDesc in resourceDesc['methods'].iteritems():
        fixedMethodName, method = createMethod(
            methodName, methodDesc, rootDesc, schema)
        self._set_dynamic_attr(fixedMethodName,
                               method.__get__(self, self.__class__))
        # Add in _media methods. The functionality of the attached method will
        # change when it sees that the method name ends in _media.
        if methodDesc.get('supportsMediaDownload', False):
          fixedMethodName, method = createMethod(
              methodName + '_media', methodDesc, rootDesc, schema)
          self._set_dynamic_attr(fixedMethodName,
                                 method.__get__(self, self.__class__))

  def _add_nested_resources(self, resourceDesc, rootDesc, schema):
    # Add in nested resources
    if 'resources' in resourceDesc:

      def createResourceMethod(methodName, methodDesc):
        """Create a method on the Resource to access a nested Resource.

        Args:
          methodName: string, name of the method to use.
          methodDesc: object, fragment of deserialized discovery document that
            describes the method.
        """
        methodName = fix_method_name(methodName)

        def methodResource(self):
          return Resource(http=self._http, baseUrl=self._baseUrl,
                          model=self._model, developerKey=self._developerKey,
                          requestBuilder=self._requestBuilder,
                          resourceDesc=methodDesc, rootDesc=rootDesc,
                          schema=schema)

        setattr(methodResource, '__doc__', 'A collection resource.')
        setattr(methodResource, '__is_resource__', True)

        return (methodName, methodResource)

      for methodName, methodDesc in resourceDesc['resources'].iteritems():
        fixedMethodName, method = createResourceMethod(methodName, methodDesc)
        self._set_dynamic_attr(fixedMethodName,
                               method.__get__(self, self.__class__))

  def _add_next_methods(self, resourceDesc, schema):
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
            fixedMethodName, method = createNextMethod(methodName + '_next')
            self._set_dynamic_attr(fixedMethodName,
                                   method.__get__(self, self.__class__))

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


from oauth2client import util
from oauth2client.anyjson import simplejson


class Error(Exception):
  """Base error for this module."""
  pass


class HttpError(Error):
  """HTTP data was invalid or unexpected."""

  @util.positional(3)
  def __init__(self, resp, content, uri=None):
    self.resp = resp
    self.content = content
    self.uri = uri

  def _get_reason(self):
    """Calculate the reason for the error from the response content."""
    reason = self.resp.reason
    try:
      data = simplejson.loads(self.content)
      reason = data['error']['message']
    except (ValueError, KeyError):
      pass
    if reason is None:
      reason = ''
    return reason

  def __repr__(self):
    if self.uri:
      return '<HttpError %s when requesting %s returned "%s">' % (
          self.resp.status, self.uri, self._get_reason().strip())
    else:
      return '<HttpError %s "%s">' % (self.resp.status, self._get_reason())

  __str__ = __repr__


class InvalidJsonError(Error):
  """The JSON returned could not be parsed."""
  pass


class UnknownFileType(Error):
  """File type unknown or unexpected."""
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


class ResumableUploadError(HttpError):
  """Error occured during resumable upload."""
  pass


class InvalidChunkSizeError(Error):
  """The given chunksize is not valid."""
  pass


class BatchError(HttpError):
  """Error occured during batch operations."""

  @util.positional(2)
  def __init__(self, reason, resp=None, content=None):
    self.resp = resp
    self.content = content
    self.reason = reason

  def __repr__(self):
      return '<BatchError %s "%s">' % (self.resp.status, self.reason)

  __str__ = __repr__


class UnexpectedMethodError(Error):
  """Exception raised by RequestMockBuilder on unexpected calls."""

  @util.positional(1)
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
__FILENAME__ = http
# Copyright (C) 2012 Google Inc.
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

import StringIO
import base64
import copy
import gzip
import httplib2
import mimeparse
import mimetypes
import os
import sys
import urllib
import urlparse
import uuid

from email.generator import Generator
from email.mime.multipart import MIMEMultipart
from email.mime.nonmultipart import MIMENonMultipart
from email.parser import FeedParser
from errors import BatchError
from errors import HttpError
from errors import InvalidChunkSizeError
from errors import ResumableUploadError
from errors import UnexpectedBodyError
from errors import UnexpectedMethodError
from model import JsonModel
from oauth2client import util
from oauth2client.anyjson import simplejson


DEFAULT_CHUNK_SIZE = 512*1024

MAX_URI_LENGTH = 2048


class MediaUploadProgress(object):
  """Status of a resumable upload."""

  def __init__(self, resumable_progress, total_size):
    """Constructor.

    Args:
      resumable_progress: int, bytes sent so far.
      total_size: int, total bytes in complete upload, or None if the total
        upload size isn't known ahead of time.
    """
    self.resumable_progress = resumable_progress
    self.total_size = total_size

  def progress(self):
    """Percent of upload completed, as a float.

    Returns:
      the percentage complete as a float, returning 0.0 if the total size of
      the upload is unknown.
    """
    if self.total_size is not None:
      return float(self.resumable_progress) / float(self.total_size)
    else:
      return 0.0


class MediaDownloadProgress(object):
  """Status of a resumable download."""

  def __init__(self, resumable_progress, total_size):
    """Constructor.

    Args:
      resumable_progress: int, bytes received so far.
      total_size: int, total bytes in complete download.
    """
    self.resumable_progress = resumable_progress
    self.total_size = total_size

  def progress(self):
    """Percent of download completed, as a float.

    Returns:
      the percentage complete as a float, returning 0.0 if the total size of
      the download is unknown.
    """
    if self.total_size is not None:
      return float(self.resumable_progress) / float(self.total_size)
    else:
      return 0.0


class MediaUpload(object):
  """Describes a media object to upload.

  Base class that defines the interface of MediaUpload subclasses.

  Note that subclasses of MediaUpload may allow you to control the chunksize
  when uploading a media object. It is important to keep the size of the chunk
  as large as possible to keep the upload efficient. Other factors may influence
  the size of the chunk you use, particularly if you are working in an
  environment where individual HTTP requests may have a hardcoded time limit,
  such as under certain classes of requests under Google App Engine.

  Streams are io.Base compatible objects that support seek(). Some MediaUpload
  subclasses support using streams directly to upload data. Support for
  streaming may be indicated by a MediaUpload sub-class and if appropriate for a
  platform that stream will be used for uploading the media object. The support
  for streaming is indicated by has_stream() returning True. The stream() method
  should return an io.Base object that supports seek(). On platforms where the
  underlying httplib module supports streaming, for example Python 2.6 and
  later, the stream will be passed into the http library which will result in
  less memory being used and possibly faster uploads.

  If you need to upload media that can't be uploaded using any of the existing
  MediaUpload sub-class then you can sub-class MediaUpload for your particular
  needs.
  """

  def chunksize(self):
    """Chunk size for resumable uploads.

    Returns:
      Chunk size in bytes.
    """
    raise NotImplementedError()

  def mimetype(self):
    """Mime type of the body.

    Returns:
      Mime type.
    """
    return 'application/octet-stream'

  def size(self):
    """Size of upload.

    Returns:
      Size of the body, or None of the size is unknown.
    """
    return None

  def resumable(self):
    """Whether this upload is resumable.

    Returns:
      True if resumable upload or False.
    """
    return False

  def getbytes(self, begin, end):
    """Get bytes from the media.

    Args:
      begin: int, offset from beginning of file.
      length: int, number of bytes to read, starting at begin.

    Returns:
      A string of bytes read. May be shorter than length if EOF was reached
      first.
    """
    raise NotImplementedError()

  def has_stream(self):
    """Does the underlying upload support a streaming interface.

    Streaming means it is an io.IOBase subclass that supports seek, i.e.
    seekable() returns True.

    Returns:
      True if the call to stream() will return an instance of a seekable io.Base
      subclass.
    """
    return False

  def stream(self):
    """A stream interface to the data being uploaded.

    Returns:
      The returned value is an io.IOBase subclass that supports seek, i.e.
      seekable() returns True.
    """
    raise NotImplementedError()

  @util.positional(1)
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


class MediaIoBaseUpload(MediaUpload):
  """A MediaUpload for a io.Base objects.

  Note that the Python file object is compatible with io.Base and can be used
  with this class also.

    fh = io.BytesIO('...Some data to upload...')
    media = MediaIoBaseUpload(fh, mimetype='image/png',
      chunksize=1024*1024, resumable=True)
    farm.animals().insert(
        id='cow',
        name='cow.png',
        media_body=media).execute()

  Depending on the platform you are working on, you may pass -1 as the
  chunksize, which indicates that the entire file should be uploaded in a single
  request. If the underlying platform supports streams, such as Python 2.6 or
  later, then this can be very efficient as it avoids multiple connections, and
  also avoids loading the entire file into memory before sending it. Note that
  Google App Engine has a 5MB limit on request size, so you should never set
  your chunksize larger than 5MB, or to -1.
  """

  @util.positional(3)
  def __init__(self, fd, mimetype, chunksize=DEFAULT_CHUNK_SIZE,
      resumable=False):
    """Constructor.

    Args:
      fd: io.Base or file object, The source of the bytes to upload. MUST be
        opened in blocking mode, do not use streams opened in non-blocking mode.
        The given stream must be seekable, that is, it must be able to call
        seek() on fd.
      mimetype: string, Mime-type of the file.
      chunksize: int, File will be uploaded in chunks of this many bytes. Only
        used if resumable=True. Pass in a value of -1 if the file is to be
        uploaded as a single chunk. Note that Google App Engine has a 5MB limit
        on request size, so you should never set your chunksize larger than 5MB,
        or to -1.
      resumable: bool, True if this is a resumable upload. False means upload
        in a single request.
    """
    super(MediaIoBaseUpload, self).__init__()
    self._fd = fd
    self._mimetype = mimetype
    if not (chunksize == -1 or chunksize > 0):
      raise InvalidChunkSizeError()
    self._chunksize = chunksize
    self._resumable = resumable

    self._fd.seek(0, os.SEEK_END)
    self._size = self._fd.tell()

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
      Size of the body, or None of the size is unknown.
    """
    return self._size

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
      A string of bytes read. May be shorted than length if EOF was reached
      first.
    """
    self._fd.seek(begin)
    return self._fd.read(length)

  def has_stream(self):
    """Does the underlying upload support a streaming interface.

    Streaming means it is an io.IOBase subclass that supports seek, i.e.
    seekable() returns True.

    Returns:
      True if the call to stream() will return an instance of a seekable io.Base
      subclass.
    """
    return True

  def stream(self):
    """A stream interface to the data being uploaded.

    Returns:
      The returned value is an io.IOBase subclass that supports seek, i.e.
      seekable() returns True.
    """
    return self._fd

  def to_json(self):
    """This upload type is not serializable."""
    raise NotImplementedError('MediaIoBaseUpload is not serializable.')


class MediaFileUpload(MediaIoBaseUpload):
  """A MediaUpload for a file.

  Construct a MediaFileUpload and pass as the media_body parameter of the
  method. For example, if we had a service that allowed uploading images:


    media = MediaFileUpload('cow.png', mimetype='image/png',
      chunksize=1024*1024, resumable=True)
    farm.animals().insert(
        id='cow',
        name='cow.png',
        media_body=media).execute()

  Depending on the platform you are working on, you may pass -1 as the
  chunksize, which indicates that the entire file should be uploaded in a single
  request. If the underlying platform supports streams, such as Python 2.6 or
  later, then this can be very efficient as it avoids multiple connections, and
  also avoids loading the entire file into memory before sending it. Note that
  Google App Engine has a 5MB limit on request size, so you should never set
  your chunksize larger than 5MB, or to -1.
  """

  @util.positional(2)
  def __init__(self, filename, mimetype=None, chunksize=DEFAULT_CHUNK_SIZE,
               resumable=False):
    """Constructor.

    Args:
      filename: string, Name of the file.
      mimetype: string, Mime-type of the file. If None then a mime-type will be
        guessed from the file extension.
      chunksize: int, File will be uploaded in chunks of this many bytes. Only
        used if resumable=True. Pass in a value of -1 if the file is to be
        uploaded in a single chunk. Note that Google App Engine has a 5MB limit
        on request size, so you should never set your chunksize larger than 5MB,
        or to -1.
      resumable: bool, True if this is a resumable upload. False means upload
        in a single request.
    """
    self._filename = filename
    fd = open(self._filename, 'rb')
    if mimetype is None:
      (mimetype, encoding) = mimetypes.guess_type(filename)
    super(MediaFileUpload, self).__init__(fd, mimetype, chunksize=chunksize,
                                          resumable=resumable)

  def to_json(self):
    """Creating a JSON representation of an instance of MediaFileUpload.

    Returns:
       string, a JSON representation of this instance, suitable to pass to
       from_json().
    """
    return self._to_json(strip=['_fd'])

  @staticmethod
  def from_json(s):
    d = simplejson.loads(s)
    return MediaFileUpload(d['_filename'], mimetype=d['_mimetype'],
                           chunksize=d['_chunksize'], resumable=d['_resumable'])


class MediaInMemoryUpload(MediaIoBaseUpload):
  """MediaUpload for a chunk of bytes.

  DEPRECATED: Use MediaIoBaseUpload with either io.TextIOBase or StringIO for
  the stream.
  """

  @util.positional(2)
  def __init__(self, body, mimetype='application/octet-stream',
               chunksize=DEFAULT_CHUNK_SIZE, resumable=False):
    """Create a new MediaInMemoryUpload.

  DEPRECATED: Use MediaIoBaseUpload with either io.TextIOBase or StringIO for
  the stream.

  Args:
    body: string, Bytes of body content.
    mimetype: string, Mime-type of the file or default of
      'application/octet-stream'.
    chunksize: int, File will be uploaded in chunks of this many bytes. Only
      used if resumable=True.
    resumable: bool, True if this is a resumable upload. False means upload
      in a single request.
    """
    fd = StringIO.StringIO(body)
    super(MediaInMemoryUpload, self).__init__(fd, mimetype, chunksize=chunksize,
                                              resumable=resumable)


class MediaIoBaseDownload(object):
  """"Download media resources.

  Note that the Python file object is compatible with io.Base and can be used
  with this class also.


  Example:
    request = farms.animals().get_media(id='cow')
    fh = io.FileIO('cow.png', mode='wb')
    downloader = MediaIoBaseDownload(fh, request, chunksize=1024*1024)

    done = False
    while done is False:
      status, done = downloader.next_chunk()
      if status:
        print "Download %d%%." % int(status.progress() * 100)
    print "Download Complete!"
  """

  @util.positional(3)
  def __init__(self, fd, request, chunksize=DEFAULT_CHUNK_SIZE):
    """Constructor.

    Args:
      fd: io.Base or file object, The stream in which to write the downloaded
        bytes.
      request: apiclient.http.HttpRequest, the media request to perform in
        chunks.
      chunksize: int, File will be downloaded in chunks of this many bytes.
    """
    self._fd = fd
    self._request = request
    self._uri = request.uri
    self._chunksize = chunksize
    self._progress = 0
    self._total_size = None
    self._done = False

  def next_chunk(self):
    """Get the next chunk of the download.

    Returns:
      (status, done): (MediaDownloadStatus, boolean)
         The value of 'done' will be True when the media has been fully
         downloaded.

    Raises:
      apiclient.errors.HttpError if the response was not a 2xx.
      httplib2.HttpLib2Error if a transport error has occured.
    """
    headers = {
        'range': 'bytes=%d-%d' % (
            self._progress, self._progress + self._chunksize)
        }
    http = self._request.http
    http.follow_redirects = False

    resp, content = http.request(self._uri, headers=headers)
    if resp.status in [301, 302, 303, 307, 308] and 'location' in resp:
        self._uri = resp['location']
        resp, content = http.request(self._uri, headers=headers)
    if resp.status in [200, 206]:
      self._progress += len(content)
      self._fd.write(content)

      if 'content-range' in resp:
        content_range = resp['content-range']
        length = content_range.rsplit('/', 1)[1]
        self._total_size = int(length)

      if self._progress == self._total_size:
        self._done = True
      return MediaDownloadProgress(self._progress, self._total_size), self._done
    else:
      raise HttpError(resp, content, uri=self._uri)


class _StreamSlice(object):
  """Truncated stream.

  Takes a stream and presents a stream that is a slice of the original stream.
  This is used when uploading media in chunks. In later versions of Python a
  stream can be passed to httplib in place of the string of data to send. The
  problem is that httplib just blindly reads to the end of the stream. This
  wrapper presents a virtual stream that only reads to the end of the chunk.
  """

  def __init__(self, stream, begin, chunksize):
    """Constructor.

    Args:
      stream: (io.Base, file object), the stream to wrap.
      begin: int, the seek position the chunk begins at.
      chunksize: int, the size of the chunk.
    """
    self._stream = stream
    self._begin = begin
    self._chunksize = chunksize
    self._stream.seek(begin)

  def read(self, n=-1):
    """Read n bytes.

    Args:
      n, int, the number of bytes to read.

    Returns:
      A string of length 'n', or less if EOF is reached.
    """
    # The data left available to read sits in [cur, end)
    cur = self._stream.tell()
    end = self._begin + self._chunksize
    if n == -1 or cur + n > end:
      n = end - cur
    return self._stream.read(n)


class HttpRequest(object):
  """Encapsulates a single HTTP request."""

  @util.positional(4)
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
    self.response_callbacks = []
    self._in_error_state = False

    # Pull the multipart boundary out of the content-type header.
    major, minor, params = mimeparse.parse_mime_type(
        headers.get('content-type', 'application/json'))

    # The size of the non-media part of the request.
    self.body_size = len(self.body or '')

    # The resumable URI to send chunks to.
    self.resumable_uri = None

    # The bytes that have been uploaded.
    self.resumable_progress = 0

  @util.positional(1)
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
      httplib2.HttpLib2Error if a transport error has occured.
    """
    if http is None:
      http = self.http
    if self.resumable:
      body = None
      while body is None:
        _, body = self.next_chunk(http=http)
      return body
    else:
      if 'content-length' not in self.headers:
        self.headers['content-length'] = str(self.body_size)
      # If the request URI is too long then turn it into a POST request.
      if len(self.uri) > MAX_URI_LENGTH and self.method == 'GET':
        self.method = 'POST'
        self.headers['x-http-method-override'] = 'GET'
        self.headers['content-type'] = 'application/x-www-form-urlencoded'
        parsed = urlparse.urlparse(self.uri)
        self.uri = urlparse.urlunparse(
            (parsed.scheme, parsed.netloc, parsed.path, parsed.params, None,
             None)
            )
        self.body = parsed.query
        self.headers['content-length'] = str(len(self.body))

      resp, content = http.request(str(self.uri), method=str(self.method),
                                   body=self.body, headers=self.headers)
      for callback in self.response_callbacks:
        callback(resp)
      if resp.status >= 300:
        raise HttpError(resp, content, uri=self.uri)
    return self.postproc(resp, content)

  @util.positional(2)
  def add_response_callback(self, cb):
    """add_response_headers_callback

    Args:
      cb: Callback to be called on receiving the response headers, of signature:

      def cb(resp):
        # Where resp is an instance of httplib2.Response
    """
    self.response_callbacks.append(cb)

  @util.positional(1)
  def next_chunk(self, http=None):
    """Execute the next step of a resumable upload.

    Can only be used if the method being executed supports media uploads and
    the MediaUpload object passed in was flagged as using resumable upload.

    Example:

      media = MediaFileUpload('cow.png', mimetype='image/png',
                              chunksize=1000, resumable=True)
      request = farm.animals().insert(
          id='cow',
          name='cow.png',
          media_body=media)

      response = None
      while response is None:
        status, response = request.next_chunk()
        if status:
          print "Upload %d%% complete." % int(status.progress() * 100)


    Returns:
      (status, body): (ResumableMediaStatus, object)
         The body will be None until the resumable media is fully uploaded.

    Raises:
      apiclient.errors.HttpError if the response was not a 2xx.
      httplib2.HttpLib2Error if a transport error has occured.
    """
    if http is None:
      http = self.http

    if self.resumable.size() is None:
      size = '*'
    else:
      size = str(self.resumable.size())

    if self.resumable_uri is None:
      start_headers = copy.copy(self.headers)
      start_headers['X-Upload-Content-Type'] = self.resumable.mimetype()
      if size != '*':
        start_headers['X-Upload-Content-Length'] = size
      start_headers['content-length'] = str(self.body_size)

      resp, content = http.request(self.uri, self.method,
                                   body=self.body,
                                   headers=start_headers)
      if resp.status == 200 and 'location' in resp:
        self.resumable_uri = resp['location']
      else:
        raise ResumableUploadError(resp, content)
    elif self._in_error_state:
      # If we are in an error state then query the server for current state of
      # the upload by sending an empty PUT and reading the 'range' header in
      # the response.
      headers = {
          'Content-Range': 'bytes */%s' % size,
          'content-length': '0'
          }
      resp, content = http.request(self.resumable_uri, 'PUT',
                                   headers=headers)
      status, body = self._process_response(resp, content)
      if body:
        # The upload was complete.
        return (status, body)

    # The httplib.request method can take streams for the body parameter, but
    # only in Python 2.6 or later. If a stream is available under those
    # conditions then use it as the body argument.
    if self.resumable.has_stream() and sys.version_info[1] >= 6:
      data = self.resumable.stream()
      if self.resumable.chunksize() == -1:
        data.seek(self.resumable_progress)
        chunk_end = self.resumable.size() - self.resumable_progress - 1
      else:
        # Doing chunking with a stream, so wrap a slice of the stream.
        data = _StreamSlice(data, self.resumable_progress,
                            self.resumable.chunksize())
        chunk_end = min(
            self.resumable_progress + self.resumable.chunksize() - 1,
            self.resumable.size() - 1)
    else:
      data = self.resumable.getbytes(
          self.resumable_progress, self.resumable.chunksize())

      # A short read implies that we are at EOF, so finish the upload.
      if len(data) < self.resumable.chunksize():
        size = str(self.resumable_progress + len(data))

      chunk_end = self.resumable_progress + len(data) - 1

    headers = {
        'Content-Range': 'bytes %d-%d/%s' % (
            self.resumable_progress, chunk_end, size),
        # Must set the content-length header here because httplib can't
        # calculate the size when working with _StreamSlice.
        'Content-Length': str(chunk_end - self.resumable_progress + 1)
        }
    try:
      resp, content = http.request(self.resumable_uri, 'PUT',
                                   body=data,
                                   headers=headers)
    except:
      self._in_error_state = True
      raise

    return self._process_response(resp, content)

  def _process_response(self, resp, content):
    """Process the response from a single chunk upload.

    Args:
      resp: httplib2.Response, the response object.
      content: string, the content of the response.

    Returns:
      (status, body): (ResumableMediaStatus, object)
         The body will be None until the resumable media is fully uploaded.

    Raises:
      apiclient.errors.HttpError if the response was not a 2xx or a 308.
    """
    if resp.status in [200, 201]:
      self._in_error_state = False
      return None, self.postproc(resp, content)
    elif resp.status == 308:
      self._in_error_state = False
      # A "308 Resume Incomplete" indicates we are not done.
      self.resumable_progress = int(resp['range'].split('-')[1]) + 1
      if 'location' in resp:
        self.resumable_uri = resp['location']
    else:
      self._in_error_state = True
      raise HttpError(resp, content, uri=self.uri)

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
  """Batches multiple HttpRequest objects into a single HTTP request.

  Example:
    from apiclient.http import BatchHttpRequest

    def list_animals(request_id, response, exception):
      \"\"\"Do something with the animals list response.\"\"\"
      if exception is not None:
        # Do something with the exception.
        pass
      else:
        # Do something with the response.
        pass

    def list_farmers(request_id, response, exception):
      \"\"\"Do something with the farmers list response.\"\"\"
      if exception is not None:
        # Do something with the exception.
        pass
      else:
        # Do something with the response.
        pass

    service = build('farm', 'v2')

    batch = BatchHttpRequest()

    batch.add(service.animals().list(), list_animals)
    batch.add(service.farmers().list(), list_farmers)
    batch.execute(http=http)
  """

  @util.positional(1)
  def __init__(self, callback=None, batch_uri=None):
    """Constructor for a BatchHttpRequest.

    Args:
      callback: callable, A callback to be called for each response, of the
        form callback(id, response, exception). The first parameter is the
        request id, and the second is the deserialized response object. The
        third is an apiclient.errors.HttpError exception object if an HTTP error
        occurred while processing the request, or None if no error occurred.
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

    # A map from request id to (httplib2.Response, content) response pairs
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
      A pair (resp, content), such as would be returned from httplib2.request.
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

  @util.positional(2)
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
        form callback(id, response, exception). The first parameter is the
        request id, and the second is the deserialized response object. The
        third is an apiclient.errors.HttpError exception object if an HTTP error
        occurred while processing the request, or None if no errors occurred.
      request_id: string, A unique id for the request. The id will be passed to
        the callback with the response.

    Returns:
      None

    Raises:
      BatchError if a media request is added to a batch.
      KeyError is the request_id is not unique.
    """
    if request_id is None:
      request_id = self._new_id()
    if request.resumable is not None:
      raise BatchError("Media requests cannot be used in a batch request.")
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
      httplib2.HttpLib2Error if a transport error has occured.
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
      raise HttpError(resp, content, uri=self._batch_uri)

    # Now break out the individual responses and store each one.
    boundary, _ = content.split(None, 1)

    # Prepend with a content-type header so FeedParser can handle it.
    header = 'content-type: %s\r\n\r\n' % resp['content-type']
    for_parser = header + content

    parser = FeedParser()
    parser.feed(for_parser)
    mime_response = parser.close()

    if not mime_response.is_multipart():
      raise BatchError("Response not in multipart/mixed format.", resp=resp,
                       content=content)

    for part in mime_response.get_payload():
      request_id = self._header_to_id(part['Content-ID'])
      response, content = self._deserialize_response(part.get_payload())
      self._responses[request_id] = (response, content)

  @util.positional(1)
  def execute(self, http=None):
    """Execute all the requests as a single batched HTTP request.

    Args:
      http: httplib2.Http, an http object to be used in place of the one the
        HttpRequest request object was constructed with. If one isn't supplied
        then use a http object from the requests in this batch.

    Returns:
      None

    Raises:
      httplib2.HttpLib2Error if a transport error has occured.
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
      resp, content = self._responses[request_id]
      if resp['status'] == '401':
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
      resp, content = self._responses[request_id]

      request = self._requests[request_id]
      callback = self._callbacks[request_id]

      response = None
      exception = None
      try:
        if resp.status >= 300:
          raise HttpError(resp, content, uri=request.uri)
        response = request.postproc(resp, content)
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
      raise UnexpectedMethodError(methodId=methodId)
    else:
      model = JsonModel(False)
      return HttpRequestMock(None, '{}', model.response)


class HttpMock(object):
  """Mock of httplib2.Http"""

  def __init__(self, filename=None, headers=None):
    """
    Args:
      filename: string, absolute filename to read response from
      headers: dict, header to return with response
    """
    if headers is None:
      headers = {'status': '200 OK'}
    if filename:
      f = file(filename, 'r')
      self.data = f.read()
      f.close()
    else:
      self.data = None
    self.response_headers = headers
    self.headers = None
    self.uri = None
    self.method = None
    self.body = None
    self.headers = None


  def request(self, uri,
              method='GET',
              body=None,
              headers=None,
              redirections=1,
              connection_type=None):
    self.uri = uri
    self.method = method
    self.body = body
    self.headers = headers
    return httplib2.Response(self.response_headers), self.data


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
    self.follow_redirects = True

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
      if hasattr(body, 'read'):
        content = body.read()
      else:
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

import gflags
import logging
import urllib

from errors import HttpError
from oauth2client.anyjson import simplejson

FLAGS = gflags.FLAGS

gflags.DEFINE_boolean('dump_request_response', False,
                      'Dump all http server requests and responses. '
                     )


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
    if FLAGS.dump_request_response:
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
    if FLAGS.dump_request_response:
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
    if self._data_wrapper and isinstance(body, dict) and 'data' in body:
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


class MediaModel(JsonModel):
  """Model class for requests that return Media.

  Serializes and de-serializes between JSON and the Python
  object representation of HTTP request, and returns the raw bytes
  of the response body.
  """
  accept = '*/*'
  content_type = 'application/json'
  alt_param = 'media'

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
__FILENAME__ = push
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

"""Push notifications support.

This code is based on experimental APIs and is subject to change.
"""

__author__ = 'afshar@google.com (Ali Afshar)'

import binascii
import collections
import os
import urllib

SUBSCRIBE = 'X-GOOG-SUBSCRIBE'
SUBSCRIPTION_ID = 'X-GOOG-SUBSCRIPTION-ID'
TOPIC_ID = 'X-GOOG-TOPIC-ID'
TOPIC_URI = 'X-GOOG-TOPIC-URI'
CLIENT_TOKEN = 'X-GOOG-CLIENT-TOKEN'
EVENT_TYPE = 'X-GOOG-EVENT-TYPE'
UNSUBSCRIBE = 'X-GOOG-UNSUBSCRIBE'


class InvalidSubscriptionRequestError(ValueError):
  """The request cannot be subscribed."""


def new_token():
  """Gets a random token for use as a client_token in push notifications.

  Returns:
    str, a new random token.
  """
  return binascii.hexlify(os.urandom(32))


class Channel(object):
  """Base class for channel types."""

  def __init__(self, channel_type, channel_args):
    """Create a new Channel.

    You probably won't need to create this channel manually, since there are
    subclassed Channel for each specific type with a more customized set of
    arguments to pass. However, you may wish to just create it manually here.

    Args:
      channel_type: str, the type of channel.
      channel_args: dict, arguments to pass to the channel.
    """
    self.channel_type = channel_type
    self.channel_args = channel_args

  def as_header_value(self):
    """Create the appropriate header for this channel.

    Returns:
      str encoded channel description suitable for use as a header.
    """
    return '%s?%s' % (self.channel_type, urllib.urlencode(self.channel_args))

  def write_header(self, headers):
    """Write the appropriate subscribe header to a headers dict.

    Args:
      headers: dict, headers to add subscribe header to.
    """
    headers[SUBSCRIBE] = self.as_header_value()


class WebhookChannel(Channel):
  """Channel for registering web hook notifications."""

  def __init__(self, url, app_engine=False):
    """Create a new WebhookChannel

    Args:
      url: str, URL to post notifications to.
      app_engine: bool, default=False, whether the destination for the
      notifications is an App Engine application.
    """
    super(WebhookChannel, self).__init__(
        channel_type='web_hook',
        channel_args={
            'url': url,
            'app_engine': app_engine and 'true' or 'false',
        }
    )


class Headers(collections.defaultdict):
  """Headers for managing subscriptions."""


  ALL_HEADERS = set([SUBSCRIBE, SUBSCRIPTION_ID, TOPIC_ID, TOPIC_URI,
                     CLIENT_TOKEN, EVENT_TYPE, UNSUBSCRIBE])

  def __init__(self):
    """Create a new subscription configuration instance."""
    collections.defaultdict.__init__(self, str)

  def __setitem__(self, key, value):
    """Set a header value, ensuring the key is an allowed value.

    Args:
      key: str, the header key.
      value: str, the header value.
    Raises:
      ValueError if key is not one of the accepted headers.
    """
    normal_key = self._normalize_key(key)
    if normal_key not in self.ALL_HEADERS:
      raise ValueError('Header name must be one of %s.' % self.ALL_HEADERS)
    else:
      return collections.defaultdict.__setitem__(self, normal_key, value)

  def __getitem__(self, key):
    """Get a header value, normalizing the key case.

    Args:
      key: str, the header key.
    Returns:
      String header value.
    Raises:
      KeyError if the key is not one of the accepted headers.
    """
    normal_key = self._normalize_key(key)
    if normal_key not in self.ALL_HEADERS:
      raise ValueError('Header name must be one of %s.' % self.ALL_HEADERS)
    else:
      return collections.defaultdict.__getitem__(self, normal_key)

  def _normalize_key(self, key):
    """Normalize a header name for use as a key."""
    return key.upper()

  def items(self):
    """Generator for each header."""
    for header in self.ALL_HEADERS:
      value = self[header]
      if value:
        yield header, value

  def write(self, headers):
    """Applies the subscription headers.

    Args:
      headers: dict of headers to insert values into.
    """
    for header, value in self.items():
      headers[header.lower()] = value

  def read(self, headers):
    """Read from headers.

    Args:
      headers: dict of headers to read from.
    """
    for header in self.ALL_HEADERS:
      if header.lower() in headers:
        self[header] = headers[header.lower()]


class Subscription(object):
  """Information about a subscription."""

  def __init__(self):
    """Create a new Subscription."""
    self.headers = Headers()

  @classmethod
  def for_request(cls, request, channel, client_token=None):
    """Creates a subscription and attaches it to a request.

    Args:
      request: An http.HttpRequest to modify for making a subscription.
      channel: A apiclient.push.Channel describing the subscription to
               create.
      client_token: (optional) client token to verify the notification.

    Returns:
      New subscription object.
    """
    subscription = cls.for_channel(channel=channel, client_token=client_token)
    subscription.headers.write(request.headers)
    if request.method != 'GET':
      raise InvalidSubscriptionRequestError(
          'Can only subscribe to requests which are GET.')
    request.method = 'POST'

    def _on_response(response, subscription=subscription):
      """Called with the response headers. Reads the subscription headers."""
      subscription.headers.read(response)

    request.add_response_callback(_on_response)
    return subscription

  @classmethod
  def for_channel(cls, channel, client_token=None):
    """Alternate constructor to create a subscription from a channel.

    Args:
      channel: A apiclient.push.Channel describing the subscription to
               create.
      client_token: (optional) client token to verify the notification.

    Returns:
      New subscription object.
    """
    subscription = cls()
    channel.write_header(subscription.headers)
    if client_token is None:
      client_token = new_token()
    subscription.headers[SUBSCRIPTION_ID] = new_token()
    subscription.headers[CLIENT_TOKEN] = client_token
    return subscription

  def verify(self, headers):
    """Verifies that a webhook notification has the correct client_token.

    Args:
      headers: dict of request headers for a push notification.

    Returns:
      Boolean value indicating whether the notification is verified.
    """
    new_subscription = Subscription()
    new_subscription.headers.read(headers)
    return new_subscription.client_token == self.client_token

  @property
  def subscribe(self):
    """Subscribe header value."""
    return self.headers[SUBSCRIBE]

  @property
  def subscription_id(self):
    """Subscription ID header value."""
    return self.headers[SUBSCRIPTION_ID]

  @property
  def topic_id(self):
    """Topic ID header value."""
    return self.headers[TOPIC_ID]

  @property
  def topic_uri(self):
    """Topic URI header value."""
    return self.headers[TOPIC_URI]

  @property
  def client_token(self):
    """Client Token header value."""
    return self.headers[CLIENT_TOKEN]

  @property
  def event_type(self):
    """Event Type header value."""
    return self.headers[EVENT_TYPE]

  @property
  def unsubscribe(self):
    """Unsuscribe header value."""
    return self.headers[UNSUBSCRIBE]

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

from oauth2client import util
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

  @util.positional(2)
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
          seen, dent=dent).to_str(self._prettyPrintByName)

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

  @util.positional(2)
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

    return _SchemaToStruct(schema, seen, dent=dent).to_str(self._prettyPrintByName)

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

  @util.positional(3)
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
      if 'properties' in schema:
        for pname, pschema in schema.get('properties', {}).iteritems():
          self.emitBegin('"%s": ' % pname)
          self._to_str_impl(pschema)
      elif 'additionalProperties' in schema:
        self.emitBegin('"a_key": ')
        self._to_str_impl(schema['additionalProperties'])
      self.undent()
      self.emit('},')
    elif '$ref' in schema:
      schemaName = schema['$ref']
      description = schema.get('description', '')
      s = self.from_cache(schemaName, seen=self.seen)
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
__FILENAME__ = gflags
#!/usr/bin/env python
#
# Copyright (c) 2002, Google Inc.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are
# met:
#
#     * Redistributions of source code must retain the above copyright
# notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above
# copyright notice, this list of conditions and the following disclaimer
# in the documentation and/or other materials provided with the
# distribution.
#     * Neither the name of Google Inc. nor the names of its
# contributors may be used to endorse or promote products derived from
# this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#
# ---
# Author: Chad Lester
# Design and style contributions by:
#   Amit Patel, Bogdan Cocosel, Daniel Dulitz, Eric Tiedemann,
#   Eric Veach, Laurence Gonsalves, Matthew Springer
# Code reorganized a bit by Craig Silverstein

"""This module is used to define and parse command line flags.

This module defines a *distributed* flag-definition policy: rather than
an application having to define all flags in or near main(), each python
module defines flags that are useful to it.  When one python module
imports another, it gains access to the other's flags.  (This is
implemented by having all modules share a common, global registry object
containing all the flag information.)

Flags are defined through the use of one of the DEFINE_xxx functions.
The specific function used determines how the flag is parsed, checked,
and optionally type-converted, when it's seen on the command line.


IMPLEMENTATION: DEFINE_* creates a 'Flag' object and registers it with a
'FlagValues' object (typically the global FlagValues FLAGS, defined
here).  The 'FlagValues' object can scan the command line arguments and
pass flag arguments to the corresponding 'Flag' objects for
value-checking and type conversion.  The converted flag values are
available as attributes of the 'FlagValues' object.

Code can access the flag through a FlagValues object, for instance
gflags.FLAGS.myflag.  Typically, the __main__ module passes the command
line arguments to gflags.FLAGS for parsing.

At bottom, this module calls getopt(), so getopt functionality is
supported, including short- and long-style flags, and the use of -- to
terminate flags.

Methods defined by the flag module will throw 'FlagsError' exceptions.
The exception argument will be a human-readable string.


FLAG TYPES: This is a list of the DEFINE_*'s that you can do.  All flags
take a name, default value, help-string, and optional 'short' name
(one-letter name).  Some flags have other arguments, which are described
with the flag.

DEFINE_string: takes any input, and interprets it as a string.

DEFINE_bool or
DEFINE_boolean: typically does not take an argument: say --myflag to
                set FLAGS.myflag to true, or --nomyflag to set
                FLAGS.myflag to false.  Alternately, you can say
                   --myflag=true  or --myflag=t or --myflag=1  or
                   --myflag=false or --myflag=f or --myflag=0

DEFINE_float: takes an input and interprets it as a floating point
              number.  Takes optional args lower_bound and upper_bound;
              if the number specified on the command line is out of
              range, it will raise a FlagError.

DEFINE_integer: takes an input and interprets it as an integer.  Takes
                optional args lower_bound and upper_bound as for floats.

DEFINE_enum: takes a list of strings which represents legal values.  If
             the command-line value is not in this list, raise a flag
             error.  Otherwise, assign to FLAGS.flag as a string.

DEFINE_list: Takes a comma-separated list of strings on the commandline.
             Stores them in a python list object.

DEFINE_spaceseplist: Takes a space-separated list of strings on the
                     commandline.  Stores them in a python list object.
                     Example: --myspacesepflag "foo bar baz"

DEFINE_multistring: The same as DEFINE_string, except the flag can be
                    specified more than once on the commandline.  The
                    result is a python list object (list of strings),
                    even if the flag is only on the command line once.

DEFINE_multi_int: The same as DEFINE_integer, except the flag can be
                  specified more than once on the commandline.  The
                  result is a python list object (list of ints), even if
                  the flag is only on the command line once.


SPECIAL FLAGS: There are a few flags that have special meaning:
   --help          prints a list of all the flags in a human-readable fashion
   --helpshort     prints a list of all key flags (see below).
   --helpxml       prints a list of all flags, in XML format.  DO NOT parse
                   the output of --help and --helpshort.  Instead, parse
                   the output of --helpxml.  For more info, see
                   "OUTPUT FOR --helpxml" below.
   --flagfile=foo  read flags from file foo.
   --undefok=f1,f2 ignore unrecognized option errors for f1,f2.
                   For boolean flags, you should use --undefok=boolflag, and
                   --boolflag and --noboolflag will be accepted.  Do not use
                   --undefok=noboolflag.
   --              as in getopt(), terminates flag-processing


FLAGS VALIDATORS: If your program:
  - requires flag X to be specified
  - needs flag Y to match a regular expression
  - or requires any more general constraint to be satisfied
then validators are for you!

Each validator represents a constraint over one flag, which is enforced
starting from the initial parsing of the flags and until the program
terminates.

Also, lower_bound and upper_bound for numerical flags are enforced using flag
validators.

Howto:
If you want to enforce a constraint over one flag, use

gflags.RegisterValidator(flag_name,
                        checker,
                        message='Flag validation failed',
                        flag_values=FLAGS)

After flag values are initially parsed, and after any change to the specified
flag, method checker(flag_value) will be executed. If constraint is not
satisfied, an IllegalFlagValue exception will be raised. See
RegisterValidator's docstring for a detailed explanation on how to construct
your own checker.


EXAMPLE USAGE:

FLAGS = gflags.FLAGS

gflags.DEFINE_integer('my_version', 0, 'Version number.')
gflags.DEFINE_string('filename', None, 'Input file name', short_name='f')

gflags.RegisterValidator('my_version',
                        lambda value: value % 2 == 0,
                        message='--my_version must be divisible by 2')
gflags.MarkFlagAsRequired('filename')


NOTE ON --flagfile:

Flags may be loaded from text files in addition to being specified on
the commandline.

Any flags you don't feel like typing, throw them in a file, one flag per
line, for instance:
   --myflag=myvalue
   --nomyboolean_flag
You then specify your file with the special flag '--flagfile=somefile'.
You CAN recursively nest flagfile= tokens OR use multiple files on the
command line.  Lines beginning with a single hash '#' or a double slash
'//' are comments in your flagfile.

Any flagfile=<file> will be interpreted as having a relative path from
the current working directory rather than from the place the file was
included from:
   myPythonScript.py --flagfile=config/somefile.cfg

If somefile.cfg includes further --flagfile= directives, these will be
referenced relative to the original CWD, not from the directory the
including flagfile was found in!

The caveat applies to people who are including a series of nested files
in a different dir than they are executing out of.  Relative path names
are always from CWD, not from the directory of the parent include
flagfile. We do now support '~' expanded directory names.

Absolute path names ALWAYS work!


EXAMPLE USAGE:


  FLAGS = gflags.FLAGS

  # Flag names are globally defined!  So in general, we need to be
  # careful to pick names that are unlikely to be used by other libraries.
  # If there is a conflict, we'll get an error at import time.
  gflags.DEFINE_string('name', 'Mr. President', 'your name')
  gflags.DEFINE_integer('age', None, 'your age in years', lower_bound=0)
  gflags.DEFINE_boolean('debug', False, 'produces debugging output')
  gflags.DEFINE_enum('gender', 'male', ['male', 'female'], 'your gender')

  def main(argv):
    try:
      argv = FLAGS(argv)  # parse flags
    except gflags.FlagsError, e:
      print '%s\\nUsage: %s ARGS\\n%s' % (e, sys.argv[0], FLAGS)
      sys.exit(1)
    if FLAGS.debug: print 'non-flag arguments:', argv
    print 'Happy Birthday', FLAGS.name
    if FLAGS.age is not None:
      print 'You are a %d year old %s' % (FLAGS.age, FLAGS.gender)

  if __name__ == '__main__':
    main(sys.argv)


KEY FLAGS:

As we already explained, each module gains access to all flags defined
by all the other modules it transitively imports.  In the case of
non-trivial scripts, this means a lot of flags ...  For documentation
purposes, it is good to identify the flags that are key (i.e., really
important) to a module.  Clearly, the concept of "key flag" is a
subjective one.  When trying to determine whether a flag is key to a
module or not, assume that you are trying to explain your module to a
potential user: which flags would you really like to mention first?

We'll describe shortly how to declare which flags are key to a module.
For the moment, assume we know the set of key flags for each module.
Then, if you use the app.py module, you can use the --helpshort flag to
print only the help for the flags that are key to the main module, in a
human-readable format.

NOTE: If you need to parse the flag help, do NOT use the output of
--help / --helpshort.  That output is meant for human consumption, and
may be changed in the future.  Instead, use --helpxml; flags that are
key for the main module are marked there with a <key>yes</key> element.

The set of key flags for a module M is composed of:

1. Flags defined by module M by calling a DEFINE_* function.

2. Flags that module M explictly declares as key by using the function

     DECLARE_key_flag(<flag_name>)

3. Key flags of other modules that M specifies by using the function

     ADOPT_module_key_flags(<other_module>)

   This is a "bulk" declaration of key flags: each flag that is key for
   <other_module> becomes key for the current module too.

Notice that if you do not use the functions described at points 2 and 3
above, then --helpshort prints information only about the flags defined
by the main module of our script.  In many cases, this behavior is good
enough.  But if you move part of the main module code (together with the
related flags) into a different module, then it is nice to use
DECLARE_key_flag / ADOPT_module_key_flags and make sure --helpshort
lists all relevant flags (otherwise, your code refactoring may confuse
your users).

Note: each of DECLARE_key_flag / ADOPT_module_key_flags has its own
pluses and minuses: DECLARE_key_flag is more targeted and may lead a
more focused --helpshort documentation.  ADOPT_module_key_flags is good
for cases when an entire module is considered key to the current script.
Also, it does not require updates to client scripts when a new flag is
added to the module.


EXAMPLE USAGE 2 (WITH KEY FLAGS):

Consider an application that contains the following three files (two
auxiliary modules and a main module)

File libfoo.py:

  import gflags

  gflags.DEFINE_integer('num_replicas', 3, 'Number of replicas to start')
  gflags.DEFINE_boolean('rpc2', True, 'Turn on the usage of RPC2.')

  ... some code ...

File libbar.py:

  import gflags

  gflags.DEFINE_string('bar_gfs_path', '/gfs/path',
                      'Path to the GFS files for libbar.')
  gflags.DEFINE_string('email_for_bar_errors', 'bar-team@google.com',
                      'Email address for bug reports about module libbar.')
  gflags.DEFINE_boolean('bar_risky_hack', False,
                       'Turn on an experimental and buggy optimization.')

  ... some code ...

File myscript.py:

  import gflags
  import libfoo
  import libbar

  gflags.DEFINE_integer('num_iterations', 0, 'Number of iterations.')

  # Declare that all flags that are key for libfoo are
  # key for this module too.
  gflags.ADOPT_module_key_flags(libfoo)

  # Declare that the flag --bar_gfs_path (defined in libbar) is key
  # for this module.
  gflags.DECLARE_key_flag('bar_gfs_path')

  ... some code ...

When myscript is invoked with the flag --helpshort, the resulted help
message lists information about all the key flags for myscript:
--num_iterations, --num_replicas, --rpc2, and --bar_gfs_path.

Of course, myscript uses all the flags declared by it (in this case,
just --num_replicas) or by any of the modules it transitively imports
(e.g., the modules libfoo, libbar).  E.g., it can access the value of
FLAGS.bar_risky_hack, even if --bar_risky_hack is not declared as a key
flag for myscript.


OUTPUT FOR --helpxml:

The --helpxml flag generates output with the following structure:

<?xml version="1.0"?>
<AllFlags>
  <program>PROGRAM_BASENAME</program>
  <usage>MAIN_MODULE_DOCSTRING</usage>
  (<flag>
    [<key>yes</key>]
    <file>DECLARING_MODULE</file>
    <name>FLAG_NAME</name>
    <meaning>FLAG_HELP_MESSAGE</meaning>
    <default>DEFAULT_FLAG_VALUE</default>
    <current>CURRENT_FLAG_VALUE</current>
    <type>FLAG_TYPE</type>
    [OPTIONAL_ELEMENTS]
  </flag>)*
</AllFlags>

Notes:

1. The output is intentionally similar to the output generated by the
C++ command-line flag library.  The few differences are due to the
Python flags that do not have a C++ equivalent (at least not yet),
e.g., DEFINE_list.

2. New XML elements may be added in the future.

3. DEFAULT_FLAG_VALUE is in serialized form, i.e., the string you can
pass for this flag on the command-line.  E.g., for a flag defined
using DEFINE_list, this field may be foo,bar, not ['foo', 'bar'].

4. CURRENT_FLAG_VALUE is produced using str().  This means that the
string 'false' will be represented in the same way as the boolean
False.  Using repr() would have removed this ambiguity and simplified
parsing, but would have broken the compatibility with the C++
command-line flags.

5. OPTIONAL_ELEMENTS describe elements relevant for certain kinds of
flags: lower_bound, upper_bound (for flags that specify bounds),
enum_value (for enum flags), list_separator (for flags that consist of
a list of values, separated by a special token).

6. We do not provide any example here: please use --helpxml instead.

This module requires at least python 2.2.1 to run.
"""

import cgi
import getopt
import os
import re
import string
import struct
import sys
# pylint: disable-msg=C6204
try:
  import fcntl
except ImportError:
  fcntl = None
try:
  # Importing termios will fail on non-unix platforms.
  import termios
except ImportError:
  termios = None

import gflags_validators
# pylint: enable-msg=C6204


# Are we running under pychecker?
_RUNNING_PYCHECKER = 'pychecker.python' in sys.modules


def _GetCallingModuleObjectAndName():
  """Returns the module that's calling into this module.

  We generally use this function to get the name of the module calling a
  DEFINE_foo... function.
  """
  # Walk down the stack to find the first globals dict that's not ours.
  for depth in range(1, sys.getrecursionlimit()):
    if not sys._getframe(depth).f_globals is globals():
      globals_for_frame = sys._getframe(depth).f_globals
      module, module_name = _GetModuleObjectAndName(globals_for_frame)
      if module_name is not None:
        return module, module_name
  raise AssertionError("No module was found")


def _GetCallingModule():
  """Returns the name of the module that's calling into this module."""
  return _GetCallingModuleObjectAndName()[1]


def _GetThisModuleObjectAndName():
  """Returns: (module object, module name) for this module."""
  return _GetModuleObjectAndName(globals())


# module exceptions:
class FlagsError(Exception):
  """The base class for all flags errors."""
  pass


class DuplicateFlag(FlagsError):
  """Raised if there is a flag naming conflict."""
  pass

class CantOpenFlagFileError(FlagsError):
  """Raised if flagfile fails to open: doesn't exist, wrong permissions, etc."""
  pass


class DuplicateFlagCannotPropagateNoneToSwig(DuplicateFlag):
  """Special case of DuplicateFlag -- SWIG flag value can't be set to None.

  This can be raised when a duplicate flag is created. Even if allow_override is
  True, we still abort if the new value is None, because it's currently
  impossible to pass None default value back to SWIG. See FlagValues.SetDefault
  for details.
  """
  pass


class DuplicateFlagError(DuplicateFlag):
  """A DuplicateFlag whose message cites the conflicting definitions.

  A DuplicateFlagError conveys more information than a DuplicateFlag,
  namely the modules where the conflicting definitions occur. This
  class was created to avoid breaking external modules which depend on
  the existing DuplicateFlags interface.
  """

  def __init__(self, flagname, flag_values, other_flag_values=None):
    """Create a DuplicateFlagError.

    Args:
      flagname: Name of the flag being redefined.
      flag_values: FlagValues object containing the first definition of
          flagname.
      other_flag_values: If this argument is not None, it should be the
          FlagValues object where the second definition of flagname occurs.
          If it is None, we assume that we're being called when attempting
          to create the flag a second time, and we use the module calling
          this one as the source of the second definition.
    """
    self.flagname = flagname
    first_module = flag_values.FindModuleDefiningFlag(
        flagname, default='<unknown>')
    if other_flag_values is None:
      second_module = _GetCallingModule()
    else:
      second_module = other_flag_values.FindModuleDefiningFlag(
          flagname, default='<unknown>')
    msg = "The flag '%s' is defined twice. First from %s, Second from %s" % (
        self.flagname, first_module, second_module)
    DuplicateFlag.__init__(self, msg)


class IllegalFlagValue(FlagsError):
  """The flag command line argument is illegal."""
  pass


class UnrecognizedFlag(FlagsError):
  """Raised if a flag is unrecognized."""
  pass


# An UnrecognizedFlagError conveys more information than an UnrecognizedFlag.
# Since there are external modules that create DuplicateFlags, the interface to
# DuplicateFlag shouldn't change.  The flagvalue will be assigned the full value
# of the flag and its argument, if any, allowing handling of unrecognized flags
# in an exception handler.
# If flagvalue is the empty string, then this exception is an due to a
# reference to a flag that was not already defined.
class UnrecognizedFlagError(UnrecognizedFlag):
  def __init__(self, flagname, flagvalue=''):
    self.flagname = flagname
    self.flagvalue = flagvalue
    UnrecognizedFlag.__init__(
        self, "Unknown command line flag '%s'" % flagname)

# Global variable used by expvar
_exported_flags = {}
_help_width = 80  # width of help output


def GetHelpWidth():
  """Returns: an integer, the width of help lines that is used in TextWrap."""
  if (not sys.stdout.isatty()) or (termios is None) or (fcntl is None):
    return _help_width
  try:
    data = fcntl.ioctl(sys.stdout, termios.TIOCGWINSZ, '1234')
    columns = struct.unpack('hh', data)[1]
    # Emacs mode returns 0.
    # Here we assume that any value below 40 is unreasonable
    if columns >= 40:
      return columns
    # Returning an int as default is fine, int(int) just return the int.
    return int(os.getenv('COLUMNS', _help_width))

  except (TypeError, IOError, struct.error):
    return _help_width


def CutCommonSpacePrefix(text):
  """Removes a common space prefix from the lines of a multiline text.

  If the first line does not start with a space, it is left as it is and
  only in the remaining lines a common space prefix is being searched
  for. That means the first line will stay untouched. This is especially
  useful to turn doc strings into help texts. This is because some
  people prefer to have the doc comment start already after the
  apostrophe and then align the following lines while others have the
  apostrophes on a separate line.

  The function also drops trailing empty lines and ignores empty lines
  following the initial content line while calculating the initial
  common whitespace.

  Args:
    text: text to work on

  Returns:
    the resulting text
  """
  text_lines = text.splitlines()
  # Drop trailing empty lines
  while text_lines and not text_lines[-1]:
    text_lines = text_lines[:-1]
  if text_lines:
    # We got some content, is the first line starting with a space?
    if text_lines[0] and text_lines[0][0].isspace():
      text_first_line = []
    else:
      text_first_line = [text_lines.pop(0)]
    # Calculate length of common leading whitespace (only over content lines)
    common_prefix = os.path.commonprefix([line for line in text_lines if line])
    space_prefix_len = len(common_prefix) - len(common_prefix.lstrip())
    # If we have a common space prefix, drop it from all lines
    if space_prefix_len:
      for index in xrange(len(text_lines)):
        if text_lines[index]:
          text_lines[index] = text_lines[index][space_prefix_len:]
    return '\n'.join(text_first_line + text_lines)
  return ''


def TextWrap(text, length=None, indent='', firstline_indent=None, tabs='    '):
  """Wraps a given text to a maximum line length and returns it.

  We turn lines that only contain whitespace into empty lines.  We keep
  new lines and tabs (e.g., we do not treat tabs as spaces).

  Args:
    text:             text to wrap
    length:           maximum length of a line, includes indentation
                      if this is None then use GetHelpWidth()
    indent:           indent for all but first line
    firstline_indent: indent for first line; if None, fall back to indent
    tabs:             replacement for tabs

  Returns:
    wrapped text

  Raises:
    FlagsError: if indent not shorter than length
    FlagsError: if firstline_indent not shorter than length
  """
  # Get defaults where callee used None
  if length is None:
    length = GetHelpWidth()
  if indent is None:
    indent = ''
  if len(indent) >= length:
    raise FlagsError('Indent must be shorter than length')
  # In line we will be holding the current line which is to be started
  # with indent (or firstline_indent if available) and then appended
  # with words.
  if firstline_indent is None:
    firstline_indent = ''
    line = indent
  else:
    line = firstline_indent
    if len(firstline_indent) >= length:
      raise FlagsError('First line indent must be shorter than length')

  # If the callee does not care about tabs we simply convert them to
  # spaces If callee wanted tabs to be single space then we do that
  # already here.
  if not tabs or tabs == ' ':
    text = text.replace('\t', ' ')
  else:
    tabs_are_whitespace = not tabs.strip()

  line_regex = re.compile('([ ]*)(\t*)([^ \t]+)', re.MULTILINE)

  # Split the text into lines and the lines with the regex above. The
  # resulting lines are collected in result[]. For each split we get the
  # spaces, the tabs and the next non white space (e.g. next word).
  result = []
  for text_line in text.splitlines():
    # Store result length so we can find out whether processing the next
    # line gave any new content
    old_result_len = len(result)
    # Process next line with line_regex. For optimization we do an rstrip().
    # - process tabs (changes either line or word, see below)
    # - process word (first try to squeeze on line, then wrap or force wrap)
    # Spaces found on the line are ignored, they get added while wrapping as
    # needed.
    for spaces, current_tabs, word in line_regex.findall(text_line.rstrip()):
      # If tabs weren't converted to spaces, handle them now
      if current_tabs:
        # If the last thing we added was a space anyway then drop
        # it. But let's not get rid of the indentation.
        if (((result and line != indent) or
             (not result and line != firstline_indent)) and line[-1] == ' '):
          line = line[:-1]
        # Add the tabs, if that means adding whitespace, just add it at
        # the line, the rstrip() code while shorten the line down if
        # necessary
        if tabs_are_whitespace:
          line += tabs * len(current_tabs)
        else:
          # if not all tab replacement is whitespace we prepend it to the word
          word = tabs * len(current_tabs) + word
      # Handle the case where word cannot be squeezed onto current last line
      if len(line) + len(word) > length and len(indent) + len(word) <= length:
        result.append(line.rstrip())
        line = indent + word
        word = ''
        # No space left on line or can we append a space?
        if len(line) + 1 >= length:
          result.append(line.rstrip())
          line = indent
        else:
          line += ' '
      # Add word and shorten it up to allowed line length. Restart next
      # line with indent and repeat, or add a space if we're done (word
      # finished) This deals with words that cannot fit on one line
      # (e.g. indent + word longer than allowed line length).
      while len(line) + len(word) >= length:
        line += word
        result.append(line[:length])
        word = line[length:]
        line = indent
      # Default case, simply append the word and a space
      if word:
        line += word + ' '
    # End of input line. If we have content we finish the line. If the
    # current line is just the indent but we had content in during this
    # original line then we need to add an empty line.
    if (result and line != indent) or (not result and line != firstline_indent):
      result.append(line.rstrip())
    elif len(result) == old_result_len:
      result.append('')
    line = indent

  return '\n'.join(result)


def DocToHelp(doc):
  """Takes a __doc__ string and reformats it as help."""

  # Get rid of starting and ending white space. Using lstrip() or even
  # strip() could drop more than maximum of first line and right space
  # of last line.
  doc = doc.strip()

  # Get rid of all empty lines
  whitespace_only_line = re.compile('^[ \t]+$', re.M)
  doc = whitespace_only_line.sub('', doc)

  # Cut out common space at line beginnings
  doc = CutCommonSpacePrefix(doc)

  # Just like this module's comment, comments tend to be aligned somehow.
  # In other words they all start with the same amount of white space
  # 1) keep double new lines
  # 2) keep ws after new lines if not empty line
  # 3) all other new lines shall be changed to a space
  # Solution: Match new lines between non white space and replace with space.
  doc = re.sub('(?<=\S)\n(?=\S)', ' ', doc, re.M)

  return doc


def _GetModuleObjectAndName(globals_dict):
  """Returns the module that defines a global environment, and its name.

  Args:
    globals_dict: A dictionary that should correspond to an environment
      providing the values of the globals.

  Returns:
    A pair consisting of (1) module object and (2) module name (a
    string).  Returns (None, None) if the module could not be
    identified.
  """
  # The use of .items() (instead of .iteritems()) is NOT a mistake: if
  # a parallel thread imports a module while we iterate over
  # .iteritems() (not nice, but possible), we get a RuntimeError ...
  # Hence, we use the slightly slower but safer .items().
  for name, module in sys.modules.items():
    if getattr(module, '__dict__', None) is globals_dict:
      if name == '__main__':
        # Pick a more informative name for the main module.
        name = sys.argv[0]
      return (module, name)
  return (None, None)


def _GetMainModule():
  """Returns: string, name of the module from which execution started."""
  # First, try to use the same logic used by _GetCallingModuleObjectAndName(),
  # i.e., call _GetModuleObjectAndName().  For that we first need to
  # find the dictionary that the main module uses to store the
  # globals.
  #
  # That's (normally) the same dictionary object that the deepest
  # (oldest) stack frame is using for globals.
  deepest_frame = sys._getframe(0)
  while deepest_frame.f_back is not None:
    deepest_frame = deepest_frame.f_back
  globals_for_main_module = deepest_frame.f_globals
  main_module_name = _GetModuleObjectAndName(globals_for_main_module)[1]
  # The above strategy fails in some cases (e.g., tools that compute
  # code coverage by redefining, among other things, the main module).
  # If so, just use sys.argv[0].  We can probably always do this, but
  # it's safest to try to use the same logic as _GetCallingModuleObjectAndName()
  if main_module_name is None:
    main_module_name = sys.argv[0]
  return main_module_name


class FlagValues:
  """Registry of 'Flag' objects.

  A 'FlagValues' can then scan command line arguments, passing flag
  arguments through to the 'Flag' objects that it owns.  It also
  provides easy access to the flag values.  Typically only one
  'FlagValues' object is needed by an application: gflags.FLAGS

  This class is heavily overloaded:

  'Flag' objects are registered via __setitem__:
       FLAGS['longname'] = x   # register a new flag

  The .value attribute of the registered 'Flag' objects can be accessed
  as attributes of this 'FlagValues' object, through __getattr__.  Both
  the long and short name of the original 'Flag' objects can be used to
  access its value:
       FLAGS.longname          # parsed flag value
       FLAGS.x                 # parsed flag value (short name)

  Command line arguments are scanned and passed to the registered 'Flag'
  objects through the __call__ method.  Unparsed arguments, including
  argv[0] (e.g. the program name) are returned.
       argv = FLAGS(sys.argv)  # scan command line arguments

  The original registered Flag objects can be retrieved through the use
  of the dictionary-like operator, __getitem__:
       x = FLAGS['longname']   # access the registered Flag object

  The str() operator of a 'FlagValues' object provides help for all of
  the registered 'Flag' objects.
  """

  def __init__(self):
    # Since everything in this class is so heavily overloaded, the only
    # way of defining and using fields is to access __dict__ directly.

    # Dictionary: flag name (string) -> Flag object.
    self.__dict__['__flags'] = {}
    # Dictionary: module name (string) -> list of Flag objects that are defined
    # by that module.
    self.__dict__['__flags_by_module'] = {}
    # Dictionary: module id (int) -> list of Flag objects that are defined by
    # that module.
    self.__dict__['__flags_by_module_id'] = {}
    # Dictionary: module name (string) -> list of Flag objects that are
    # key for that module.
    self.__dict__['__key_flags_by_module'] = {}

    # Set if we should use new style gnu_getopt rather than getopt when parsing
    # the args.  Only possible with Python 2.3+
    self.UseGnuGetOpt(False)

  def UseGnuGetOpt(self, use_gnu_getopt=True):
    """Use GNU-style scanning. Allows mixing of flag and non-flag arguments.

    See http://docs.python.org/library/getopt.html#getopt.gnu_getopt

    Args:
      use_gnu_getopt: wether or not to use GNU style scanning.
    """
    self.__dict__['__use_gnu_getopt'] = use_gnu_getopt

  def IsGnuGetOpt(self):
    return self.__dict__['__use_gnu_getopt']

  def FlagDict(self):
    return self.__dict__['__flags']

  def FlagsByModuleDict(self):
    """Returns the dictionary of module_name -> list of defined flags.

    Returns:
      A dictionary.  Its keys are module names (strings).  Its values
      are lists of Flag objects.
    """
    return self.__dict__['__flags_by_module']

  def FlagsByModuleIdDict(self):
    """Returns the dictionary of module_id -> list of defined flags.

    Returns:
      A dictionary.  Its keys are module IDs (ints).  Its values
      are lists of Flag objects.
    """
    return self.__dict__['__flags_by_module_id']

  def KeyFlagsByModuleDict(self):
    """Returns the dictionary of module_name -> list of key flags.

    Returns:
      A dictionary.  Its keys are module names (strings).  Its values
      are lists of Flag objects.
    """
    return self.__dict__['__key_flags_by_module']

  def _RegisterFlagByModule(self, module_name, flag):
    """Records the module that defines a specific flag.

    We keep track of which flag is defined by which module so that we
    can later sort the flags by module.

    Args:
      module_name: A string, the name of a Python module.
      flag: A Flag object, a flag that is key to the module.
    """
    flags_by_module = self.FlagsByModuleDict()
    flags_by_module.setdefault(module_name, []).append(flag)

  def _RegisterFlagByModuleId(self, module_id, flag):
    """Records the module that defines a specific flag.

    Args:
      module_id: An int, the ID of the Python module.
      flag: A Flag object, a flag that is key to the module.
    """
    flags_by_module_id = self.FlagsByModuleIdDict()
    flags_by_module_id.setdefault(module_id, []).append(flag)

  def _RegisterKeyFlagForModule(self, module_name, flag):
    """Specifies that a flag is a key flag for a module.

    Args:
      module_name: A string, the name of a Python module.
      flag: A Flag object, a flag that is key to the module.
    """
    key_flags_by_module = self.KeyFlagsByModuleDict()
    # The list of key flags for the module named module_name.
    key_flags = key_flags_by_module.setdefault(module_name, [])
    # Add flag, but avoid duplicates.
    if flag not in key_flags:
      key_flags.append(flag)

  def _GetFlagsDefinedByModule(self, module):
    """Returns the list of flags defined by a module.

    Args:
      module: A module object or a module name (a string).

    Returns:
      A new list of Flag objects.  Caller may update this list as he
      wishes: none of those changes will affect the internals of this
      FlagValue object.
    """
    if not isinstance(module, str):
      module = module.__name__

    return list(self.FlagsByModuleDict().get(module, []))

  def _GetKeyFlagsForModule(self, module):
    """Returns the list of key flags for a module.

    Args:
      module: A module object or a module name (a string)

    Returns:
      A new list of Flag objects.  Caller may update this list as he
      wishes: none of those changes will affect the internals of this
      FlagValue object.
    """
    if not isinstance(module, str):
      module = module.__name__

    # Any flag is a key flag for the module that defined it.  NOTE:
    # key_flags is a fresh list: we can update it without affecting the
    # internals of this FlagValues object.
    key_flags = self._GetFlagsDefinedByModule(module)

    # Take into account flags explicitly declared as key for a module.
    for flag in self.KeyFlagsByModuleDict().get(module, []):
      if flag not in key_flags:
        key_flags.append(flag)
    return key_flags

  def FindModuleDefiningFlag(self, flagname, default=None):
    """Return the name of the module defining this flag, or default.

    Args:
      flagname: Name of the flag to lookup.
      default: Value to return if flagname is not defined. Defaults
          to None.

    Returns:
      The name of the module which registered the flag with this name.
      If no such module exists (i.e. no flag with this name exists),
      we return default.
    """
    for module, flags in self.FlagsByModuleDict().iteritems():
      for flag in flags:
        if flag.name == flagname or flag.short_name == flagname:
          return module
    return default

  def FindModuleIdDefiningFlag(self, flagname, default=None):
    """Return the ID of the module defining this flag, or default.

    Args:
      flagname: Name of the flag to lookup.
      default: Value to return if flagname is not defined. Defaults
          to None.

    Returns:
      The ID of the module which registered the flag with this name.
      If no such module exists (i.e. no flag with this name exists),
      we return default.
    """
    for module_id, flags in self.FlagsByModuleIdDict().iteritems():
      for flag in flags:
        if flag.name == flagname or flag.short_name == flagname:
          return module_id
    return default

  def AppendFlagValues(self, flag_values):
    """Appends flags registered in another FlagValues instance.

    Args:
      flag_values: registry to copy from
    """
    for flag_name, flag in flag_values.FlagDict().iteritems():
      # Each flags with shortname appears here twice (once under its
      # normal name, and again with its short name).  To prevent
      # problems (DuplicateFlagError) with double flag registration, we
      # perform a check to make sure that the entry we're looking at is
      # for its normal name.
      if flag_name == flag.name:
        try:
          self[flag_name] = flag
        except DuplicateFlagError:
          raise DuplicateFlagError(flag_name, self,
                                   other_flag_values=flag_values)

  def RemoveFlagValues(self, flag_values):
    """Remove flags that were previously appended from another FlagValues.

    Args:
      flag_values: registry containing flags to remove.
    """
    for flag_name in flag_values.FlagDict():
      self.__delattr__(flag_name)

  def __setitem__(self, name, flag):
    """Registers a new flag variable."""
    fl = self.FlagDict()
    if not isinstance(flag, Flag):
      raise IllegalFlagValue(flag)
    if not isinstance(name, type("")):
      raise FlagsError("Flag name must be a string")
    if len(name) == 0:
      raise FlagsError("Flag name cannot be empty")
    # If running under pychecker, duplicate keys are likely to be
    # defined.  Disable check for duplicate keys when pycheck'ing.
    if (name in fl and not flag.allow_override and
        not fl[name].allow_override and not _RUNNING_PYCHECKER):
      module, module_name = _GetCallingModuleObjectAndName()
      if (self.FindModuleDefiningFlag(name) == module_name and
          id(module) != self.FindModuleIdDefiningFlag(name)):
        # If the flag has already been defined by a module with the same name,
        # but a different ID, we can stop here because it indicates that the
        # module is simply being imported a subsequent time.
        return
      raise DuplicateFlagError(name, self)
    short_name = flag.short_name
    if short_name is not None:
      if (short_name in fl and not flag.allow_override and
          not fl[short_name].allow_override and not _RUNNING_PYCHECKER):
        raise DuplicateFlagError(short_name, self)
      fl[short_name] = flag
    fl[name] = flag
    global _exported_flags
    _exported_flags[name] = flag

  def __getitem__(self, name):
    """Retrieves the Flag object for the flag --name."""
    return self.FlagDict()[name]

  def __getattr__(self, name):
    """Retrieves the 'value' attribute of the flag --name."""
    fl = self.FlagDict()
    if name not in fl:
      raise AttributeError(name)
    return fl[name].value

  def __setattr__(self, name, value):
    """Sets the 'value' attribute of the flag --name."""
    fl = self.FlagDict()
    fl[name].value = value
    self._AssertValidators(fl[name].validators)
    return value

  def _AssertAllValidators(self):
    all_validators = set()
    for flag in self.FlagDict().itervalues():
      for validator in flag.validators:
        all_validators.add(validator)
    self._AssertValidators(all_validators)

  def _AssertValidators(self, validators):
    """Assert if all validators in the list are satisfied.

    Asserts validators in the order they were created.
    Args:
      validators: Iterable(gflags_validators.Validator), validators to be
        verified
    Raises:
      AttributeError: if validators work with a non-existing flag.
      IllegalFlagValue: if validation fails for at least one validator
    """
    for validator in sorted(
        validators, key=lambda validator: validator.insertion_index):
      try:
        validator.Verify(self)
      except gflags_validators.Error, e:
        message = validator.PrintFlagsWithValues(self)
        raise IllegalFlagValue('%s: %s' % (message, str(e)))

  def _FlagIsRegistered(self, flag_obj):
    """Checks whether a Flag object is registered under some name.

    Note: this is non trivial: in addition to its normal name, a flag
    may have a short name too.  In self.FlagDict(), both the normal and
    the short name are mapped to the same flag object.  E.g., calling
    only "del FLAGS.short_name" is not unregistering the corresponding
    Flag object (it is still registered under the longer name).

    Args:
      flag_obj: A Flag object.

    Returns:
      A boolean: True iff flag_obj is registered under some name.
    """
    flag_dict = self.FlagDict()
    # Check whether flag_obj is registered under its long name.
    name = flag_obj.name
    if flag_dict.get(name, None) == flag_obj:
      return True
    # Check whether flag_obj is registered under its short name.
    short_name = flag_obj.short_name
    if (short_name is not None and
        flag_dict.get(short_name, None) == flag_obj):
      return True
    # The flag cannot be registered under any other name, so we do not
    # need to do a full search through the values of self.FlagDict().
    return False

  def __delattr__(self, flag_name):
    """Deletes a previously-defined flag from a flag object.

    This method makes sure we can delete a flag by using

      del flag_values_object.<flag_name>

    E.g.,

      gflags.DEFINE_integer('foo', 1, 'Integer flag.')
      del gflags.FLAGS.foo

    Args:
      flag_name: A string, the name of the flag to be deleted.

    Raises:
      AttributeError: When there is no registered flag named flag_name.
    """
    fl = self.FlagDict()
    if flag_name not in fl:
      raise AttributeError(flag_name)

    flag_obj = fl[flag_name]
    del fl[flag_name]

    if not self._FlagIsRegistered(flag_obj):
      # If the Flag object indicated by flag_name is no longer
      # registered (please see the docstring of _FlagIsRegistered), then
      # we delete the occurrences of the flag object in all our internal
      # dictionaries.
      self.__RemoveFlagFromDictByModule(self.FlagsByModuleDict(), flag_obj)
      self.__RemoveFlagFromDictByModule(self.FlagsByModuleIdDict(), flag_obj)
      self.__RemoveFlagFromDictByModule(self.KeyFlagsByModuleDict(), flag_obj)

  def __RemoveFlagFromDictByModule(self, flags_by_module_dict, flag_obj):
    """Removes a flag object from a module -> list of flags dictionary.

    Args:
      flags_by_module_dict: A dictionary that maps module names to lists of
        flags.
      flag_obj: A flag object.
    """
    for unused_module, flags_in_module in flags_by_module_dict.iteritems():
      # while (as opposed to if) takes care of multiple occurrences of a
      # flag in the list for the same module.
      while flag_obj in flags_in_module:
        flags_in_module.remove(flag_obj)

  def SetDefault(self, name, value):
    """Changes the default value of the named flag object."""
    fl = self.FlagDict()
    if name not in fl:
      raise AttributeError(name)
    fl[name].SetDefault(value)
    self._AssertValidators(fl[name].validators)

  def __contains__(self, name):
    """Returns True if name is a value (flag) in the dict."""
    return name in self.FlagDict()

  has_key = __contains__  # a synonym for __contains__()

  def __iter__(self):
    return iter(self.FlagDict())

  def __call__(self, argv):
    """Parses flags from argv; stores parsed flags into this FlagValues object.

    All unparsed arguments are returned.  Flags are parsed using the GNU
    Program Argument Syntax Conventions, using getopt:

    http://www.gnu.org/software/libc/manual/html_mono/libc.html#Getopt

    Args:
       argv: argument list. Can be of any type that may be converted to a list.

    Returns:
       The list of arguments not parsed as options, including argv[0]

    Raises:
       FlagsError: on any parsing error
    """
    # Support any sequence type that can be converted to a list
    argv = list(argv)

    shortopts = ""
    longopts = []

    fl = self.FlagDict()

    # This pre parses the argv list for --flagfile=<> options.
    argv = argv[:1] + self.ReadFlagsFromFiles(argv[1:], force_gnu=False)

    # Correct the argv to support the google style of passing boolean
    # parameters.  Boolean parameters may be passed by using --mybool,
    # --nomybool, --mybool=(true|false|1|0).  getopt does not support
    # having options that may or may not have a parameter.  We replace
    # instances of the short form --mybool and --nomybool with their
    # full forms: --mybool=(true|false).
    original_argv = list(argv)  # list() makes a copy
    shortest_matches = None
    for name, flag in fl.items():
      if not flag.boolean:
        continue
      if shortest_matches is None:
        # Determine the smallest allowable prefix for all flag names
        shortest_matches = self.ShortestUniquePrefixes(fl)
      no_name = 'no' + name
      prefix = shortest_matches[name]
      no_prefix = shortest_matches[no_name]

      # Replace all occurrences of this boolean with extended forms
      for arg_idx in range(1, len(argv)):
        arg = argv[arg_idx]
        if arg.find('=') >= 0: continue
        if arg.startswith('--'+prefix) and ('--'+name).startswith(arg):
          argv[arg_idx] = ('--%s=true' % name)
        elif arg.startswith('--'+no_prefix) and ('--'+no_name).startswith(arg):
          argv[arg_idx] = ('--%s=false' % name)

    # Loop over all of the flags, building up the lists of short options
    # and long options that will be passed to getopt.  Short options are
    # specified as a string of letters, each letter followed by a colon
    # if it takes an argument.  Long options are stored in an array of
    # strings.  Each string ends with an '=' if it takes an argument.
    for name, flag in fl.items():
      longopts.append(name + "=")
      if len(name) == 1:  # one-letter option: allow short flag type also
        shortopts += name
        if not flag.boolean:
          shortopts += ":"

    longopts.append('undefok=')
    undefok_flags = []

    # In case --undefok is specified, loop to pick up unrecognized
    # options one by one.
    unrecognized_opts = []
    args = argv[1:]
    while True:
      try:
        if self.__dict__['__use_gnu_getopt']:
          optlist, unparsed_args = getopt.gnu_getopt(args, shortopts, longopts)
        else:
          optlist, unparsed_args = getopt.getopt(args, shortopts, longopts)
        break
      except getopt.GetoptError, e:
        if not e.opt or e.opt in fl:
          # Not an unrecognized option, re-raise the exception as a FlagsError
          raise FlagsError(e)
        # Remove offender from args and try again
        for arg_index in range(len(args)):
          if ((args[arg_index] == '--' + e.opt) or
              (args[arg_index] == '-' + e.opt) or
              (args[arg_index].startswith('--' + e.opt + '='))):
            unrecognized_opts.append((e.opt, args[arg_index]))
            args = args[0:arg_index] + args[arg_index+1:]
            break
        else:
          # We should have found the option, so we don't expect to get
          # here.  We could assert, but raising the original exception
          # might work better.
          raise FlagsError(e)

    for name, arg in optlist:
      if name == '--undefok':
        flag_names = arg.split(',')
        undefok_flags.extend(flag_names)
        # For boolean flags, if --undefok=boolflag is specified, then we should
        # also accept --noboolflag, in addition to --boolflag.
        # Since we don't know the type of the undefok'd flag, this will affect
        # non-boolean flags as well.
        # NOTE: You shouldn't use --undefok=noboolflag, because then we will
        # accept --nonoboolflag here.  We are choosing not to do the conversion
        # from noboolflag -> boolflag because of the ambiguity that flag names
        # can start with 'no'.
        undefok_flags.extend('no' + name for name in flag_names)
        continue
      if name.startswith('--'):
        # long option
        name = name[2:]
        short_option = 0
      else:
        # short option
        name = name[1:]
        short_option = 1
      if name in fl:
        flag = fl[name]
        if flag.boolean and short_option: arg = 1
        flag.Parse(arg)

    # If there were unrecognized options, raise an exception unless
    # the options were named via --undefok.
    for opt, value in unrecognized_opts:
      if opt not in undefok_flags:
        raise UnrecognizedFlagError(opt, value)

    if unparsed_args:
      if self.__dict__['__use_gnu_getopt']:
        # if using gnu_getopt just return the program name + remainder of argv.
        ret_val = argv[:1] + unparsed_args
      else:
        # unparsed_args becomes the first non-flag detected by getopt to
        # the end of argv.  Because argv may have been modified above,
        # return original_argv for this region.
        ret_val = argv[:1] + original_argv[-len(unparsed_args):]
    else:
      ret_val = argv[:1]

    self._AssertAllValidators()
    return ret_val

  def Reset(self):
    """Resets the values to the point before FLAGS(argv) was called."""
    for f in self.FlagDict().values():
      f.Unparse()

  def RegisteredFlags(self):
    """Returns: a list of the names and short names of all registered flags."""
    return list(self.FlagDict())

  def FlagValuesDict(self):
    """Returns: a dictionary that maps flag names to flag values."""
    flag_values = {}

    for flag_name in self.RegisteredFlags():
      flag = self.FlagDict()[flag_name]
      flag_values[flag_name] = flag.value

    return flag_values

  def __str__(self):
    """Generates a help string for all known flags."""
    return self.GetHelp()

  def GetHelp(self, prefix=''):
    """Generates a help string for all known flags."""
    helplist = []

    flags_by_module = self.FlagsByModuleDict()
    if flags_by_module:

      modules = sorted(flags_by_module)

      # Print the help for the main module first, if possible.
      main_module = _GetMainModule()
      if main_module in modules:
        modules.remove(main_module)
        modules = [main_module] + modules

      for module in modules:
        self.__RenderOurModuleFlags(module, helplist)

      self.__RenderModuleFlags('gflags',
                               _SPECIAL_FLAGS.FlagDict().values(),
                               helplist)

    else:
      # Just print one long list of flags.
      self.__RenderFlagList(
          self.FlagDict().values() + _SPECIAL_FLAGS.FlagDict().values(),
          helplist, prefix)

    return '\n'.join(helplist)

  def __RenderModuleFlags(self, module, flags, output_lines, prefix=""):
    """Generates a help string for a given module."""
    if not isinstance(module, str):
      module = module.__name__
    output_lines.append('\n%s%s:' % (prefix, module))
    self.__RenderFlagList(flags, output_lines, prefix + "  ")

  def __RenderOurModuleFlags(self, module, output_lines, prefix=""):
    """Generates a help string for a given module."""
    flags = self._GetFlagsDefinedByModule(module)
    if flags:
      self.__RenderModuleFlags(module, flags, output_lines, prefix)

  def __RenderOurModuleKeyFlags(self, module, output_lines, prefix=""):
    """Generates a help string for the key flags of a given module.

    Args:
      module: A module object or a module name (a string).
      output_lines: A list of strings.  The generated help message
        lines will be appended to this list.
      prefix: A string that is prepended to each generated help line.
    """
    key_flags = self._GetKeyFlagsForModule(module)
    if key_flags:
      self.__RenderModuleFlags(module, key_flags, output_lines, prefix)

  def ModuleHelp(self, module):
    """Describe the key flags of a module.

    Args:
      module: A module object or a module name (a string).

    Returns:
      string describing the key flags of a module.
    """
    helplist = []
    self.__RenderOurModuleKeyFlags(module, helplist)
    return '\n'.join(helplist)

  def MainModuleHelp(self):
    """Describe the key flags of the main module.

    Returns:
      string describing the key flags of a module.
    """
    return self.ModuleHelp(_GetMainModule())

  def __RenderFlagList(self, flaglist, output_lines, prefix="  "):
    fl = self.FlagDict()
    special_fl = _SPECIAL_FLAGS.FlagDict()
    flaglist = [(flag.name, flag) for flag in flaglist]
    flaglist.sort()
    flagset = {}
    for (name, flag) in flaglist:
      # It's possible this flag got deleted or overridden since being
      # registered in the per-module flaglist.  Check now against the
      # canonical source of current flag information, the FlagDict.
      if fl.get(name, None) != flag and special_fl.get(name, None) != flag:
        # a different flag is using this name now
        continue
      # only print help once
      if flag in flagset: continue
      flagset[flag] = 1
      flaghelp = ""
      if flag.short_name: flaghelp += "-%s," % flag.short_name
      if flag.boolean:
        flaghelp += "--[no]%s" % flag.name + ":"
      else:
        flaghelp += "--%s" % flag.name + ":"
      flaghelp += "  "
      if flag.help:
        flaghelp += flag.help
      flaghelp = TextWrap(flaghelp, indent=prefix+"  ",
                          firstline_indent=prefix)
      if flag.default_as_str:
        flaghelp += "\n"
        flaghelp += TextWrap("(default: %s)" % flag.default_as_str,
                             indent=prefix+"  ")
      if flag.parser.syntactic_help:
        flaghelp += "\n"
        flaghelp += TextWrap("(%s)" % flag.parser.syntactic_help,
                             indent=prefix+"  ")
      output_lines.append(flaghelp)

  def get(self, name, default):
    """Returns the value of a flag (if not None) or a default value.

    Args:
      name: A string, the name of a flag.
      default: Default value to use if the flag value is None.
    """

    value = self.__getattr__(name)
    if value is not None:  # Can't do if not value, b/c value might be '0' or ""
      return value
    else:
      return default

  def ShortestUniquePrefixes(self, fl):
    """Returns: dictionary; maps flag names to their shortest unique prefix."""
    # Sort the list of flag names
    sorted_flags = []
    for name, flag in fl.items():
      sorted_flags.append(name)
      if flag.boolean:
        sorted_flags.append('no%s' % name)
    sorted_flags.sort()

    # For each name in the sorted list, determine the shortest unique
    # prefix by comparing itself to the next name and to the previous
    # name (the latter check uses cached info from the previous loop).
    shortest_matches = {}
    prev_idx = 0
    for flag_idx in range(len(sorted_flags)):
      curr = sorted_flags[flag_idx]
      if flag_idx == (len(sorted_flags) - 1):
        next = None
      else:
        next = sorted_flags[flag_idx+1]
        next_len = len(next)
      for curr_idx in range(len(curr)):
        if (next is None
            or curr_idx >= next_len
            or curr[curr_idx] != next[curr_idx]):
          # curr longer than next or no more chars in common
          shortest_matches[curr] = curr[:max(prev_idx, curr_idx) + 1]
          prev_idx = curr_idx
          break
      else:
        # curr shorter than (or equal to) next
        shortest_matches[curr] = curr
        prev_idx = curr_idx + 1  # next will need at least one more char
    return shortest_matches

  def __IsFlagFileDirective(self, flag_string):
    """Checks whether flag_string contain a --flagfile=<foo> directive."""
    if isinstance(flag_string, type("")):
      if flag_string.startswith('--flagfile='):
        return 1
      elif flag_string == '--flagfile':
        return 1
      elif flag_string.startswith('-flagfile='):
        return 1
      elif flag_string == '-flagfile':
        return 1
      else:
        return 0
    return 0

  def ExtractFilename(self, flagfile_str):
    """Returns filename from a flagfile_str of form -[-]flagfile=filename.

    The cases of --flagfile foo and -flagfile foo shouldn't be hitting
    this function, as they are dealt with in the level above this
    function.
    """
    if flagfile_str.startswith('--flagfile='):
      return os.path.expanduser((flagfile_str[(len('--flagfile=')):]).strip())
    elif flagfile_str.startswith('-flagfile='):
      return os.path.expanduser((flagfile_str[(len('-flagfile=')):]).strip())
    else:
      raise FlagsError('Hit illegal --flagfile type: %s' % flagfile_str)

  def __GetFlagFileLines(self, filename, parsed_file_list):
    """Returns the useful (!=comments, etc) lines from a file with flags.

    Args:
      filename: A string, the name of the flag file.
      parsed_file_list: A list of the names of the files we have
        already read.  MUTATED BY THIS FUNCTION.

    Returns:
      List of strings. See the note below.

    NOTE(springer): This function checks for a nested --flagfile=<foo>
    tag and handles the lower file recursively. It returns a list of
    all the lines that _could_ contain command flags. This is
    EVERYTHING except whitespace lines and comments (lines starting
    with '#' or '//').
    """
    line_list = []  # All line from flagfile.
    flag_line_list = []  # Subset of lines w/o comments, blanks, flagfile= tags.
    try:
      file_obj = open(filename, 'r')
    except IOError, e_msg:
      raise CantOpenFlagFileError('ERROR:: Unable to open flagfile: %s' % e_msg)

    line_list = file_obj.readlines()
    file_obj.close()
    parsed_file_list.append(filename)

    # This is where we check each line in the file we just read.
    for line in line_list:
      if line.isspace():
        pass
      # Checks for comment (a line that starts with '#').
      elif line.startswith('#') or line.startswith('//'):
        pass
      # Checks for a nested "--flagfile=<bar>" flag in the current file.
      # If we find one, recursively parse down into that file.
      elif self.__IsFlagFileDirective(line):
        sub_filename = self.ExtractFilename(line)
        # We do a little safety check for reparsing a file we've already done.
        if not sub_filename in parsed_file_list:
          included_flags = self.__GetFlagFileLines(sub_filename,
                                                   parsed_file_list)
          flag_line_list.extend(included_flags)
        else:  # Case of hitting a circularly included file.
          sys.stderr.write('Warning: Hit circular flagfile dependency: %s\n' %
                           (sub_filename,))
      else:
        # Any line that's not a comment or a nested flagfile should get
        # copied into 2nd position.  This leaves earlier arguments
        # further back in the list, thus giving them higher priority.
        flag_line_list.append(line.strip())
    return flag_line_list

  def ReadFlagsFromFiles(self, argv, force_gnu=True):
    """Processes command line args, but also allow args to be read from file.

    Args:
      argv: A list of strings, usually sys.argv[1:], which may contain one or
        more flagfile directives of the form --flagfile="./filename".
        Note that the name of the program (sys.argv[0]) should be omitted.
      force_gnu: If False, --flagfile parsing obeys normal flag semantics.
        If True, --flagfile parsing instead follows gnu_getopt semantics.
        *** WARNING *** force_gnu=False may become the future default!

    Returns:

      A new list which has the original list combined with what we read
      from any flagfile(s).

    References: Global gflags.FLAG class instance.

    This function should be called before the normal FLAGS(argv) call.
    This function scans the input list for a flag that looks like:
    --flagfile=<somefile>. Then it opens <somefile>, reads all valid key
    and value pairs and inserts them into the input list between the
    first item of the list and any subsequent items in the list.

    Note that your application's flags are still defined the usual way
    using gflags DEFINE_flag() type functions.

    Notes (assuming we're getting a commandline of some sort as our input):
    --> Flags from the command line argv _should_ always take precedence!
    --> A further "--flagfile=<otherfile.cfg>" CAN be nested in a flagfile.
        It will be processed after the parent flag file is done.
    --> For duplicate flags, first one we hit should "win".
    --> In a flagfile, a line beginning with # or // is a comment.
    --> Entirely blank lines _should_ be ignored.
    """
    parsed_file_list = []
    rest_of_args = argv
    new_argv = []
    while rest_of_args:
      current_arg = rest_of_args[0]
      rest_of_args = rest_of_args[1:]
      if self.__IsFlagFileDirective(current_arg):
        # This handles the case of -(-)flagfile foo.  In this case the
        # next arg really is part of this one.
        if current_arg == '--flagfile' or current_arg == '-flagfile':
          if not rest_of_args:
            raise IllegalFlagValue('--flagfile with no argument')
          flag_filename = os.path.expanduser(rest_of_args[0])
          rest_of_args = rest_of_args[1:]
        else:
          # This handles the case of (-)-flagfile=foo.
          flag_filename = self.ExtractFilename(current_arg)
        new_argv.extend(
            self.__GetFlagFileLines(flag_filename, parsed_file_list))
      else:
        new_argv.append(current_arg)
        # Stop parsing after '--', like getopt and gnu_getopt.
        if current_arg == '--':
          break
        # Stop parsing after a non-flag, like getopt.
        if not current_arg.startswith('-'):
          if not force_gnu and not self.__dict__['__use_gnu_getopt']:
            break

    if rest_of_args:
      new_argv.extend(rest_of_args)

    return new_argv

  def FlagsIntoString(self):
    """Returns a string with the flags assignments from this FlagValues object.

    This function ignores flags whose value is None.  Each flag
    assignment is separated by a newline.

    NOTE: MUST mirror the behavior of the C++ CommandlineFlagsIntoString
    from http://code.google.com/p/google-gflags
    """
    s = ''
    for flag in self.FlagDict().values():
      if flag.value is not None:
        s += flag.Serialize() + '\n'
    return s

  def AppendFlagsIntoFile(self, filename):
    """Appends all flags assignments from this FlagInfo object to a file.

    Output will be in the format of a flagfile.

    NOTE: MUST mirror the behavior of the C++ AppendFlagsIntoFile
    from http://code.google.com/p/google-gflags
    """
    out_file = open(filename, 'a')
    out_file.write(self.FlagsIntoString())
    out_file.close()

  def WriteHelpInXMLFormat(self, outfile=None):
    """Outputs flag documentation in XML format.

    NOTE: We use element names that are consistent with those used by
    the C++ command-line flag library, from
    http://code.google.com/p/google-gflags
    We also use a few new elements (e.g., <key>), but we do not
    interfere / overlap with existing XML elements used by the C++
    library.  Please maintain this consistency.

    Args:
      outfile: File object we write to.  Default None means sys.stdout.
    """
    outfile = outfile or sys.stdout

    outfile.write('<?xml version=\"1.0\"?>\n')
    outfile.write('<AllFlags>\n')
    indent = '  '
    _WriteSimpleXMLElement(outfile, 'program', os.path.basename(sys.argv[0]),
                           indent)

    usage_doc = sys.modules['__main__'].__doc__
    if not usage_doc:
      usage_doc = '\nUSAGE: %s [flags]\n' % sys.argv[0]
    else:
      usage_doc = usage_doc.replace('%s', sys.argv[0])
    _WriteSimpleXMLElement(outfile, 'usage', usage_doc, indent)

    # Get list of key flags for the main module.
    key_flags = self._GetKeyFlagsForModule(_GetMainModule())

    # Sort flags by declaring module name and next by flag name.
    flags_by_module = self.FlagsByModuleDict()
    all_module_names = list(flags_by_module.keys())
    all_module_names.sort()
    for module_name in all_module_names:
      flag_list = [(f.name, f) for f in flags_by_module[module_name]]
      flag_list.sort()
      for unused_flag_name, flag in flag_list:
        is_key = flag in key_flags
        flag.WriteInfoInXMLFormat(outfile, module_name,
                                  is_key=is_key, indent=indent)

    outfile.write('</AllFlags>\n')
    outfile.flush()

  def AddValidator(self, validator):
    """Register new flags validator to be checked.

    Args:
      validator: gflags_validators.Validator
    Raises:
      AttributeError: if validators work with a non-existing flag.
    """
    for flag_name in validator.GetFlagsNames():
      flag = self.FlagDict()[flag_name]
      flag.validators.append(validator)

# end of FlagValues definition


# The global FlagValues instance
FLAGS = FlagValues()


def _StrOrUnicode(value):
  """Converts value to a python string or, if necessary, unicode-string."""
  try:
    return str(value)
  except UnicodeEncodeError:
    return unicode(value)


def _MakeXMLSafe(s):
  """Escapes <, >, and & from s, and removes XML 1.0-illegal chars."""
  s = cgi.escape(s)  # Escape <, >, and &
  # Remove characters that cannot appear in an XML 1.0 document
  # (http://www.w3.org/TR/REC-xml/#charsets).
  #
  # NOTE: if there are problems with current solution, one may move to
  # XML 1.1, which allows such chars, if they're entity-escaped (&#xHH;).
  s = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', s)
  # Convert non-ascii characters to entities.  Note: requires python >=2.3
  s = s.encode('ascii', 'xmlcharrefreplace')   # u'\xce\x88' -> 'u&#904;'
  return s


def _WriteSimpleXMLElement(outfile, name, value, indent):
  """Writes a simple XML element.

  Args:
    outfile: File object we write the XML element to.
    name: A string, the name of XML element.
    value: A Python object, whose string representation will be used
      as the value of the XML element.
    indent: A string, prepended to each line of generated output.
  """
  value_str = _StrOrUnicode(value)
  if isinstance(value, bool):
    # Display boolean values as the C++ flag library does: no caps.
    value_str = value_str.lower()
  safe_value_str = _MakeXMLSafe(value_str)
  outfile.write('%s<%s>%s</%s>\n' % (indent, name, safe_value_str, name))


class Flag:
  """Information about a command-line flag.

  'Flag' objects define the following fields:
    .name  - the name for this flag
    .default - the default value for this flag
    .default_as_str - default value as repr'd string, e.g., "'true'" (or None)
    .value  - the most recent parsed value of this flag; set by Parse()
    .help  - a help string or None if no help is available
    .short_name  - the single letter alias for this flag (or None)
    .boolean  - if 'true', this flag does not accept arguments
    .present  - true if this flag was parsed from command line flags.
    .parser  - an ArgumentParser object
    .serializer - an ArgumentSerializer object
    .allow_override - the flag may be redefined without raising an error

  The only public method of a 'Flag' object is Parse(), but it is
  typically only called by a 'FlagValues' object.  The Parse() method is
  a thin wrapper around the 'ArgumentParser' Parse() method.  The parsed
  value is saved in .value, and the .present attribute is updated.  If
  this flag was already present, a FlagsError is raised.

  Parse() is also called during __init__ to parse the default value and
  initialize the .value attribute.  This enables other python modules to
  safely use flags even if the __main__ module neglects to parse the
  command line arguments.  The .present attribute is cleared after
  __init__ parsing.  If the default value is set to None, then the
  __init__ parsing step is skipped and the .value attribute is
  initialized to None.

  Note: The default value is also presented to the user in the help
  string, so it is important that it be a legal value for this flag.
  """

  def __init__(self, parser, serializer, name, default, help_string,
               short_name=None, boolean=0, allow_override=0):
    self.name = name

    if not help_string:
      help_string = '(no help available)'

    self.help = help_string
    self.short_name = short_name
    self.boolean = boolean
    self.present = 0
    self.parser = parser
    self.serializer = serializer
    self.allow_override = allow_override
    self.value = None
    self.validators = []

    self.SetDefault(default)

  def __hash__(self):
    return hash(id(self))

  def __eq__(self, other):
    return self is other

  def __lt__(self, other):
    if isinstance(other, Flag):
      return id(self) < id(other)
    return NotImplemented

  def __GetParsedValueAsString(self, value):
    if value is None:
      return None
    if self.serializer:
      return repr(self.serializer.Serialize(value))
    if self.boolean:
      if value:
        return repr('true')
      else:
        return repr('false')
    return repr(_StrOrUnicode(value))

  def Parse(self, argument):
    try:
      self.value = self.parser.Parse(argument)
    except ValueError, e:  # recast ValueError as IllegalFlagValue
      raise IllegalFlagValue("flag --%s=%s: %s" % (self.name, argument, e))
    self.present += 1

  def Unparse(self):
    if self.default is None:
      self.value = None
    else:
      self.Parse(self.default)
    self.present = 0

  def Serialize(self):
    if self.value is None:
      return ''
    if self.boolean:
      if self.value:
        return "--%s" % self.name
      else:
        return "--no%s" % self.name
    else:
      if not self.serializer:
        raise FlagsError("Serializer not present for flag %s" % self.name)
      return "--%s=%s" % (self.name, self.serializer.Serialize(self.value))

  def SetDefault(self, value):
    """Changes the default value (and current value too) for this Flag."""
    # We can't allow a None override because it may end up not being
    # passed to C++ code when we're overriding C++ flags.  So we
    # cowardly bail out until someone fixes the semantics of trying to
    # pass None to a C++ flag.  See swig_flags.Init() for details on
    # this behavior.
    # TODO(olexiy): Users can directly call this method, bypassing all flags
    # validators (we don't have FlagValues here, so we can not check
    # validators).
    # The simplest solution I see is to make this method private.
    # Another approach would be to store reference to the corresponding
    # FlagValues with each flag, but this seems to be an overkill.
    if value is None and self.allow_override:
      raise DuplicateFlagCannotPropagateNoneToSwig(self.name)

    self.default = value
    self.Unparse()
    self.default_as_str = self.__GetParsedValueAsString(self.value)

  def Type(self):
    """Returns: a string that describes the type of this Flag."""
    # NOTE: we use strings, and not the types.*Type constants because
    # our flags can have more exotic types, e.g., 'comma separated list
    # of strings', 'whitespace separated list of strings', etc.
    return self.parser.Type()

  def WriteInfoInXMLFormat(self, outfile, module_name, is_key=False, indent=''):
    """Writes common info about this flag, in XML format.

    This is information that is relevant to all flags (e.g., name,
    meaning, etc.).  If you defined a flag that has some other pieces of
    info, then please override _WriteCustomInfoInXMLFormat.

    Please do NOT override this method.

    Args:
      outfile: File object we write to.
      module_name: A string, the name of the module that defines this flag.
      is_key: A boolean, True iff this flag is key for main module.
      indent: A string that is prepended to each generated line.
    """
    outfile.write(indent + '<flag>\n')
    inner_indent = indent + '  '
    if is_key:
      _WriteSimpleXMLElement(outfile, 'key', 'yes', inner_indent)
    _WriteSimpleXMLElement(outfile, 'file', module_name, inner_indent)
    # Print flag features that are relevant for all flags.
    _WriteSimpleXMLElement(outfile, 'name', self.name, inner_indent)
    if self.short_name:
      _WriteSimpleXMLElement(outfile, 'short_name', self.short_name,
                             inner_indent)
    if self.help:
      _WriteSimpleXMLElement(outfile, 'meaning', self.help, inner_indent)
    # The default flag value can either be represented as a string like on the
    # command line, or as a Python object.  We serialize this value in the
    # latter case in order to remain consistent.
    if self.serializer and not isinstance(self.default, str):
      default_serialized = self.serializer.Serialize(self.default)
    else:
      default_serialized = self.default
    _WriteSimpleXMLElement(outfile, 'default', default_serialized, inner_indent)
    _WriteSimpleXMLElement(outfile, 'current', self.value, inner_indent)
    _WriteSimpleXMLElement(outfile, 'type', self.Type(), inner_indent)
    # Print extra flag features this flag may have.
    self._WriteCustomInfoInXMLFormat(outfile, inner_indent)
    outfile.write(indent + '</flag>\n')

  def _WriteCustomInfoInXMLFormat(self, outfile, indent):
    """Writes extra info about this flag, in XML format.

    "Extra" means "not already printed by WriteInfoInXMLFormat above."

    Args:
      outfile: File object we write to.
      indent: A string that is prepended to each generated line.
    """
    # Usually, the parser knows the extra details about the flag, so
    # we just forward the call to it.
    self.parser.WriteCustomInfoInXMLFormat(outfile, indent)
# End of Flag definition


class _ArgumentParserCache(type):
  """Metaclass used to cache and share argument parsers among flags."""

  _instances = {}

  def __call__(mcs, *args, **kwargs):
    """Returns an instance of the argument parser cls.

    This method overrides behavior of the __new__ methods in
    all subclasses of ArgumentParser (inclusive). If an instance
    for mcs with the same set of arguments exists, this instance is
    returned, otherwise a new instance is created.

    If any keyword arguments are defined, or the values in args
    are not hashable, this method always returns a new instance of
    cls.

    Args:
      args: Positional initializer arguments.
      kwargs: Initializer keyword arguments.

    Returns:
      An instance of cls, shared or new.
    """
    if kwargs:
      return type.__call__(mcs, *args, **kwargs)
    else:
      instances = mcs._instances
      key = (mcs,) + tuple(args)
      try:
        return instances[key]
      except KeyError:
        # No cache entry for key exists, create a new one.
        return instances.setdefault(key, type.__call__(mcs, *args))
      except TypeError:
        # An object in args cannot be hashed, always return
        # a new instance.
        return type.__call__(mcs, *args)


class ArgumentParser(object):
  """Base class used to parse and convert arguments.

  The Parse() method checks to make sure that the string argument is a
  legal value and convert it to a native type.  If the value cannot be
  converted, it should throw a 'ValueError' exception with a human
  readable explanation of why the value is illegal.

  Subclasses should also define a syntactic_help string which may be
  presented to the user to describe the form of the legal values.

  Argument parser classes must be stateless, since instances are cached
  and shared between flags. Initializer arguments are allowed, but all
  member variables must be derived from initializer arguments only.
  """
  __metaclass__ = _ArgumentParserCache

  syntactic_help = ""

  def Parse(self, argument):
    """Default implementation: always returns its argument unmodified."""
    return argument

  def Type(self):
    return 'string'

  def WriteCustomInfoInXMLFormat(self, outfile, indent):
    pass


class ArgumentSerializer:
  """Base class for generating string representations of a flag value."""

  def Serialize(self, value):
    return _StrOrUnicode(value)


class ListSerializer(ArgumentSerializer):

  def __init__(self, list_sep):
    self.list_sep = list_sep

  def Serialize(self, value):
    return self.list_sep.join([_StrOrUnicode(x) for x in value])


# Flags validators


def RegisterValidator(flag_name,
                      checker,
                      message='Flag validation failed',
                      flag_values=FLAGS):
  """Adds a constraint, which will be enforced during program execution.

  The constraint is validated when flags are initially parsed, and after each
  change of the corresponding flag's value.
  Args:
    flag_name: string, name of the flag to be checked.
    checker: method to validate the flag.
      input  - value of the corresponding flag (string, boolean, etc.
        This value will be passed to checker by the library). See file's
        docstring for examples.
      output - Boolean.
        Must return True if validator constraint is satisfied.
        If constraint is not satisfied, it should either return False or
          raise gflags_validators.Error(desired_error_message).
    message: error text to be shown to the user if checker returns False.
      If checker raises gflags_validators.Error, message from the raised
        Error will be shown.
    flag_values: FlagValues
  Raises:
    AttributeError: if flag_name is not registered as a valid flag name.
  """
  flag_values.AddValidator(gflags_validators.SimpleValidator(flag_name,
                                                            checker,
                                                            message))


def MarkFlagAsRequired(flag_name, flag_values=FLAGS):
  """Ensure that flag is not None during program execution.

  Registers a flag validator, which will follow usual validator
  rules.
  Args:
    flag_name: string, name of the flag
    flag_values: FlagValues
  Raises:
    AttributeError: if flag_name is not registered as a valid flag name.
  """
  RegisterValidator(flag_name,
                    lambda value: value is not None,
                    message='Flag --%s must be specified.' % flag_name,
                    flag_values=flag_values)


def _RegisterBoundsValidatorIfNeeded(parser, name, flag_values):
  """Enforce lower and upper bounds for numeric flags.

  Args:
    parser: NumericParser (either FloatParser or IntegerParser). Provides lower
      and upper bounds, and help text to display.
    name: string, name of the flag
    flag_values: FlagValues
  """
  if parser.lower_bound is not None or parser.upper_bound is not None:

    def Checker(value):
      if value is not None and parser.IsOutsideBounds(value):
        message = '%s is not %s' % (value, parser.syntactic_help)
        raise gflags_validators.Error(message)
      return True

    RegisterValidator(name,
                      Checker,
                      flag_values=flag_values)


# The DEFINE functions are explained in mode details in the module doc string.


def DEFINE(parser, name, default, help, flag_values=FLAGS, serializer=None,
           **args):
  """Registers a generic Flag object.

  NOTE: in the docstrings of all DEFINE* functions, "registers" is short
  for "creates a new flag and registers it".

  Auxiliary function: clients should use the specialized DEFINE_<type>
  function instead.

  Args:
    parser: ArgumentParser that is used to parse the flag arguments.
    name: A string, the flag name.
    default: The default value of the flag.
    help: A help string.
    flag_values: FlagValues object the flag will be registered with.
    serializer: ArgumentSerializer that serializes the flag value.
    args: Dictionary with extra keyword args that are passes to the
      Flag __init__.
  """
  DEFINE_flag(Flag(parser, serializer, name, default, help, **args),
              flag_values)


def DEFINE_flag(flag, flag_values=FLAGS):
  """Registers a 'Flag' object with a 'FlagValues' object.

  By default, the global FLAGS 'FlagValue' object is used.

  Typical users will use one of the more specialized DEFINE_xxx
  functions, such as DEFINE_string or DEFINE_integer.  But developers
  who need to create Flag objects themselves should use this function
  to register their flags.
  """
  # copying the reference to flag_values prevents pychecker warnings
  fv = flag_values
  fv[flag.name] = flag
  # Tell flag_values who's defining the flag.
  if isinstance(flag_values, FlagValues):
    # Regarding the above isinstance test: some users pass funny
    # values of flag_values (e.g., {}) in order to avoid the flag
    # registration (in the past, there used to be a flag_values ==
    # FLAGS test here) and redefine flags with the same name (e.g.,
    # debug).  To avoid breaking their code, we perform the
    # registration only if flag_values is a real FlagValues object.
    module, module_name = _GetCallingModuleObjectAndName()
    flag_values._RegisterFlagByModule(module_name, flag)
    flag_values._RegisterFlagByModuleId(id(module), flag)


def _InternalDeclareKeyFlags(flag_names,
                             flag_values=FLAGS, key_flag_values=None):
  """Declares a flag as key for the calling module.

  Internal function.  User code should call DECLARE_key_flag or
  ADOPT_module_key_flags instead.

  Args:
    flag_names: A list of strings that are names of already-registered
      Flag objects.
    flag_values: A FlagValues object that the flags listed in
      flag_names have registered with (the value of the flag_values
      argument from the DEFINE_* calls that defined those flags).
      This should almost never need to be overridden.
    key_flag_values: A FlagValues object that (among possibly many
      other things) keeps track of the key flags for each module.
      Default None means "same as flag_values".  This should almost
      never need to be overridden.

  Raises:
    UnrecognizedFlagError: when we refer to a flag that was not
      defined yet.
  """
  key_flag_values = key_flag_values or flag_values

  module = _GetCallingModule()

  for flag_name in flag_names:
    if flag_name not in flag_values:
      raise UnrecognizedFlagError(flag_name)
    flag = flag_values.FlagDict()[flag_name]
    key_flag_values._RegisterKeyFlagForModule(module, flag)


def DECLARE_key_flag(flag_name, flag_values=FLAGS):
  """Declares one flag as key to the current module.

  Key flags are flags that are deemed really important for a module.
  They are important when listing help messages; e.g., if the
  --helpshort command-line flag is used, then only the key flags of the
  main module are listed (instead of all flags, as in the case of
  --help).

  Sample usage:

    gflags.DECLARED_key_flag('flag_1')

  Args:
    flag_name: A string, the name of an already declared flag.
      (Redeclaring flags as key, including flags implicitly key
      because they were declared in this module, is a no-op.)
    flag_values: A FlagValues object.  This should almost never
      need to be overridden.
  """
  if flag_name in _SPECIAL_FLAGS:
    # Take care of the special flags, e.g., --flagfile, --undefok.
    # These flags are defined in _SPECIAL_FLAGS, and are treated
    # specially during flag parsing, taking precedence over the
    # user-defined flags.
    _InternalDeclareKeyFlags([flag_name],
                             flag_values=_SPECIAL_FLAGS,
                             key_flag_values=flag_values)
    return
  _InternalDeclareKeyFlags([flag_name], flag_values=flag_values)


def ADOPT_module_key_flags(module, flag_values=FLAGS):
  """Declares that all flags key to a module are key to the current module.

  Args:
    module: A module object.
    flag_values: A FlagValues object.  This should almost never need
      to be overridden.

  Raises:
    FlagsError: When given an argument that is a module name (a
    string), instead of a module object.
  """
  # NOTE(salcianu): an even better test would be if not
  # isinstance(module, types.ModuleType) but I didn't want to import
  # types for such a tiny use.
  if isinstance(module, str):
    raise FlagsError('Received module name %s; expected a module object.'
                     % module)
  _InternalDeclareKeyFlags(
      [f.name for f in flag_values._GetKeyFlagsForModule(module.__name__)],
      flag_values=flag_values)
  # If module is this flag module, take _SPECIAL_FLAGS into account.
  if module == _GetThisModuleObjectAndName()[0]:
    _InternalDeclareKeyFlags(
        # As we associate flags with _GetCallingModuleObjectAndName(), the
        # special flags defined in this module are incorrectly registered with
        # a different module.  So, we can't use _GetKeyFlagsForModule.
        # Instead, we take all flags from _SPECIAL_FLAGS (a private
        # FlagValues, where no other module should register flags).
        [f.name for f in _SPECIAL_FLAGS.FlagDict().values()],
        flag_values=_SPECIAL_FLAGS,
        key_flag_values=flag_values)


#
# STRING FLAGS
#


def DEFINE_string(name, default, help, flag_values=FLAGS, **args):
  """Registers a flag whose value can be any string."""
  parser = ArgumentParser()
  serializer = ArgumentSerializer()
  DEFINE(parser, name, default, help, flag_values, serializer, **args)


#
# BOOLEAN FLAGS
#


class BooleanParser(ArgumentParser):
  """Parser of boolean values."""

  def Convert(self, argument):
    """Converts the argument to a boolean; raise ValueError on errors."""
    if type(argument) == str:
      if argument.lower() in ['true', 't', '1']:
        return True
      elif argument.lower() in ['false', 'f', '0']:
        return False

    bool_argument = bool(argument)
    if argument == bool_argument:
      # The argument is a valid boolean (True, False, 0, or 1), and not just
      # something that always converts to bool (list, string, int, etc.).
      return bool_argument

    raise ValueError('Non-boolean argument to boolean flag', argument)

  def Parse(self, argument):
    val = self.Convert(argument)
    return val

  def Type(self):
    return 'bool'


class BooleanFlag(Flag):
  """Basic boolean flag.

  Boolean flags do not take any arguments, and their value is either
  True (1) or False (0).  The false value is specified on the command
  line by prepending the word 'no' to either the long or the short flag
  name.

  For example, if a Boolean flag was created whose long name was
  'update' and whose short name was 'x', then this flag could be
  explicitly unset through either --noupdate or --nox.
  """

  def __init__(self, name, default, help, short_name=None, **args):
    p = BooleanParser()
    Flag.__init__(self, p, None, name, default, help, short_name, 1, **args)
    if not self.help: self.help = "a boolean value"


def DEFINE_boolean(name, default, help, flag_values=FLAGS, **args):
  """Registers a boolean flag.

  Such a boolean flag does not take an argument.  If a user wants to
  specify a false value explicitly, the long option beginning with 'no'
  must be used: i.e. --noflag

  This flag will have a value of None, True or False.  None is possible
  if default=None and the user does not specify the flag on the command
  line.
  """
  DEFINE_flag(BooleanFlag(name, default, help, **args), flag_values)


# Match C++ API to unconfuse C++ people.
DEFINE_bool = DEFINE_boolean


class HelpFlag(BooleanFlag):
  """
  HelpFlag is a special boolean flag that prints usage information and
  raises a SystemExit exception if it is ever found in the command
  line arguments.  Note this is called with allow_override=1, so other
  apps can define their own --help flag, replacing this one, if they want.
  """
  def __init__(self):
    BooleanFlag.__init__(self, "help", 0, "show this help",
                         short_name="?", allow_override=1)
  def Parse(self, arg):
    if arg:
      doc = sys.modules["__main__"].__doc__
      flags = str(FLAGS)
      print doc or ("\nUSAGE: %s [flags]\n" % sys.argv[0])
      if flags:
        print "flags:"
        print flags
      sys.exit(1)
class HelpXMLFlag(BooleanFlag):
  """Similar to HelpFlag, but generates output in XML format."""
  def __init__(self):
    BooleanFlag.__init__(self, 'helpxml', False,
                         'like --help, but generates XML output',
                         allow_override=1)
  def Parse(self, arg):
    if arg:
      FLAGS.WriteHelpInXMLFormat(sys.stdout)
      sys.exit(1)
class HelpshortFlag(BooleanFlag):
  """
  HelpshortFlag is a special boolean flag that prints usage
  information for the "main" module, and rasies a SystemExit exception
  if it is ever found in the command line arguments.  Note this is
  called with allow_override=1, so other apps can define their own
  --helpshort flag, replacing this one, if they want.
  """
  def __init__(self):
    BooleanFlag.__init__(self, "helpshort", 0,
                         "show usage only for this module", allow_override=1)
  def Parse(self, arg):
    if arg:
      doc = sys.modules["__main__"].__doc__
      flags = FLAGS.MainModuleHelp()
      print doc or ("\nUSAGE: %s [flags]\n" % sys.argv[0])
      if flags:
        print "flags:"
        print flags
      sys.exit(1)

#
# Numeric parser - base class for Integer and Float parsers
#


class NumericParser(ArgumentParser):
  """Parser of numeric values.

  Parsed value may be bounded to a given upper and lower bound.
  """

  def IsOutsideBounds(self, val):
    return ((self.lower_bound is not None and val < self.lower_bound) or
            (self.upper_bound is not None and val > self.upper_bound))

  def Parse(self, argument):
    val = self.Convert(argument)
    if self.IsOutsideBounds(val):
      raise ValueError("%s is not %s" % (val, self.syntactic_help))
    return val

  def WriteCustomInfoInXMLFormat(self, outfile, indent):
    if self.lower_bound is not None:
      _WriteSimpleXMLElement(outfile, 'lower_bound', self.lower_bound, indent)
    if self.upper_bound is not None:
      _WriteSimpleXMLElement(outfile, 'upper_bound', self.upper_bound, indent)

  def Convert(self, argument):
    """Default implementation: always returns its argument unmodified."""
    return argument

# End of Numeric Parser

#
# FLOAT FLAGS
#


class FloatParser(NumericParser):
  """Parser of floating point values.

  Parsed value may be bounded to a given upper and lower bound.
  """
  number_article = "a"
  number_name = "number"
  syntactic_help = " ".join((number_article, number_name))

  def __init__(self, lower_bound=None, upper_bound=None):
    super(FloatParser, self).__init__()
    self.lower_bound = lower_bound
    self.upper_bound = upper_bound
    sh = self.syntactic_help
    if lower_bound is not None and upper_bound is not None:
      sh = ("%s in the range [%s, %s]" % (sh, lower_bound, upper_bound))
    elif lower_bound == 0:
      sh = "a non-negative %s" % self.number_name
    elif upper_bound == 0:
      sh = "a non-positive %s" % self.number_name
    elif upper_bound is not None:
      sh = "%s <= %s" % (self.number_name, upper_bound)
    elif lower_bound is not None:
      sh = "%s >= %s" % (self.number_name, lower_bound)
    self.syntactic_help = sh

  def Convert(self, argument):
    """Converts argument to a float; raises ValueError on errors."""
    return float(argument)

  def Type(self):
    return 'float'
# End of FloatParser


def DEFINE_float(name, default, help, lower_bound=None, upper_bound=None,
                 flag_values=FLAGS, **args):
  """Registers a flag whose value must be a float.

  If lower_bound or upper_bound are set, then this flag must be
  within the given range.
  """
  parser = FloatParser(lower_bound, upper_bound)
  serializer = ArgumentSerializer()
  DEFINE(parser, name, default, help, flag_values, serializer, **args)
  _RegisterBoundsValidatorIfNeeded(parser, name, flag_values=flag_values)

#
# INTEGER FLAGS
#


class IntegerParser(NumericParser):
  """Parser of an integer value.

  Parsed value may be bounded to a given upper and lower bound.
  """
  number_article = "an"
  number_name = "integer"
  syntactic_help = " ".join((number_article, number_name))

  def __init__(self, lower_bound=None, upper_bound=None):
    super(IntegerParser, self).__init__()
    self.lower_bound = lower_bound
    self.upper_bound = upper_bound
    sh = self.syntactic_help
    if lower_bound is not None and upper_bound is not None:
      sh = ("%s in the range [%s, %s]" % (sh, lower_bound, upper_bound))
    elif lower_bound == 1:
      sh = "a positive %s" % self.number_name
    elif upper_bound == -1:
      sh = "a negative %s" % self.number_name
    elif lower_bound == 0:
      sh = "a non-negative %s" % self.number_name
    elif upper_bound == 0:
      sh = "a non-positive %s" % self.number_name
    elif upper_bound is not None:
      sh = "%s <= %s" % (self.number_name, upper_bound)
    elif lower_bound is not None:
      sh = "%s >= %s" % (self.number_name, lower_bound)
    self.syntactic_help = sh

  def Convert(self, argument):
    __pychecker__ = 'no-returnvalues'
    if type(argument) == str:
      base = 10
      if len(argument) > 2 and argument[0] == "0" and argument[1] == "x":
        base = 16
      return int(argument, base)
    else:
      return int(argument)

  def Type(self):
    return 'int'


def DEFINE_integer(name, default, help, lower_bound=None, upper_bound=None,
                   flag_values=FLAGS, **args):
  """Registers a flag whose value must be an integer.

  If lower_bound, or upper_bound are set, then this flag must be
  within the given range.
  """
  parser = IntegerParser(lower_bound, upper_bound)
  serializer = ArgumentSerializer()
  DEFINE(parser, name, default, help, flag_values, serializer, **args)
  _RegisterBoundsValidatorIfNeeded(parser, name, flag_values=flag_values)


#
# ENUM FLAGS
#


class EnumParser(ArgumentParser):
  """Parser of a string enum value (a string value from a given set).

  If enum_values (see below) is not specified, any string is allowed.
  """

  def __init__(self, enum_values=None):
    super(EnumParser, self).__init__()
    self.enum_values = enum_values

  def Parse(self, argument):
    if self.enum_values and argument not in self.enum_values:
      raise ValueError("value should be one of <%s>" %
                       "|".join(self.enum_values))
    return argument

  def Type(self):
    return 'string enum'


class EnumFlag(Flag):
  """Basic enum flag; its value can be any string from list of enum_values."""

  def __init__(self, name, default, help, enum_values=None,
               short_name=None, **args):
    enum_values = enum_values or []
    p = EnumParser(enum_values)
    g = ArgumentSerializer()
    Flag.__init__(self, p, g, name, default, help, short_name, **args)
    if not self.help: self.help = "an enum string"
    self.help = "<%s>: %s" % ("|".join(enum_values), self.help)

  def _WriteCustomInfoInXMLFormat(self, outfile, indent):
    for enum_value in self.parser.enum_values:
      _WriteSimpleXMLElement(outfile, 'enum_value', enum_value, indent)


def DEFINE_enum(name, default, enum_values, help, flag_values=FLAGS,
                **args):
  """Registers a flag whose value can be any string from enum_values."""
  DEFINE_flag(EnumFlag(name, default, help, enum_values, ** args),
              flag_values)


#
# LIST FLAGS
#


class BaseListParser(ArgumentParser):
  """Base class for a parser of lists of strings.

  To extend, inherit from this class; from the subclass __init__, call

    BaseListParser.__init__(self, token, name)

  where token is a character used to tokenize, and name is a description
  of the separator.
  """

  def __init__(self, token=None, name=None):
    assert name
    super(BaseListParser, self).__init__()
    self._token = token
    self._name = name
    self.syntactic_help = "a %s separated list" % self._name

  def Parse(self, argument):
    if isinstance(argument, list):
      return argument
    elif argument == '':
      return []
    else:
      return [s.strip() for s in argument.split(self._token)]

  def Type(self):
    return '%s separated list of strings' % self._name


class ListParser(BaseListParser):
  """Parser for a comma-separated list of strings."""

  def __init__(self):
    BaseListParser.__init__(self, ',', 'comma')

  def WriteCustomInfoInXMLFormat(self, outfile, indent):
    BaseListParser.WriteCustomInfoInXMLFormat(self, outfile, indent)
    _WriteSimpleXMLElement(outfile, 'list_separator', repr(','), indent)


class WhitespaceSeparatedListParser(BaseListParser):
  """Parser for a whitespace-separated list of strings."""

  def __init__(self):
    BaseListParser.__init__(self, None, 'whitespace')

  def WriteCustomInfoInXMLFormat(self, outfile, indent):
    BaseListParser.WriteCustomInfoInXMLFormat(self, outfile, indent)
    separators = list(string.whitespace)
    separators.sort()
    for ws_char in string.whitespace:
      _WriteSimpleXMLElement(outfile, 'list_separator', repr(ws_char), indent)


def DEFINE_list(name, default, help, flag_values=FLAGS, **args):
  """Registers a flag whose value is a comma-separated list of strings."""
  parser = ListParser()
  serializer = ListSerializer(',')
  DEFINE(parser, name, default, help, flag_values, serializer, **args)


def DEFINE_spaceseplist(name, default, help, flag_values=FLAGS, **args):
  """Registers a flag whose value is a whitespace-separated list of strings.

  Any whitespace can be used as a separator.
  """
  parser = WhitespaceSeparatedListParser()
  serializer = ListSerializer(' ')
  DEFINE(parser, name, default, help, flag_values, serializer, **args)


#
# MULTI FLAGS
#


class MultiFlag(Flag):
  """A flag that can appear multiple time on the command-line.

  The value of such a flag is a list that contains the individual values
  from all the appearances of that flag on the command-line.

  See the __doc__ for Flag for most behavior of this class.  Only
  differences in behavior are described here:

    * The default value may be either a single value or a list of values.
      A single value is interpreted as the [value] singleton list.

    * The value of the flag is always a list, even if the option was
      only supplied once, and even if the default value is a single
      value
  """

  def __init__(self, *args, **kwargs):
    Flag.__init__(self, *args, **kwargs)
    self.help += ';\n    repeat this option to specify a list of values'

  def Parse(self, arguments):
    """Parses one or more arguments with the installed parser.

    Args:
      arguments: a single argument or a list of arguments (typically a
        list of default values); a single argument is converted
        internally into a list containing one item.
    """
    if not isinstance(arguments, list):
      # Default value may be a list of values.  Most other arguments
      # will not be, so convert them into a single-item list to make
      # processing simpler below.
      arguments = [arguments]

    if self.present:
      # keep a backup reference to list of previously supplied option values
      values = self.value
    else:
      # "erase" the defaults with an empty list
      values = []

    for item in arguments:
      # have Flag superclass parse argument, overwriting self.value reference
      Flag.Parse(self, item)  # also increments self.present
      values.append(self.value)

    # put list of option values back in the 'value' attribute
    self.value = values

  def Serialize(self):
    if not self.serializer:
      raise FlagsError("Serializer not present for flag %s" % self.name)
    if self.value is None:
      return ''

    s = ''

    multi_value = self.value

    for self.value in multi_value:
      if s: s += ' '
      s += Flag.Serialize(self)

    self.value = multi_value

    return s

  def Type(self):
    return 'multi ' + self.parser.Type()


def DEFINE_multi(parser, serializer, name, default, help, flag_values=FLAGS,
                 **args):
  """Registers a generic MultiFlag that parses its args with a given parser.

  Auxiliary function.  Normal users should NOT use it directly.

  Developers who need to create their own 'Parser' classes for options
  which can appear multiple times can call this module function to
  register their flags.
  """
  DEFINE_flag(MultiFlag(parser, serializer, name, default, help, **args),
              flag_values)


def DEFINE_multistring(name, default, help, flag_values=FLAGS, **args):
  """Registers a flag whose value can be a list of any strings.

  Use the flag on the command line multiple times to place multiple
  string values into the list.  The 'default' may be a single string
  (which will be converted into a single-element list) or a list of
  strings.
  """
  parser = ArgumentParser()
  serializer = ArgumentSerializer()
  DEFINE_multi(parser, serializer, name, default, help, flag_values, **args)


def DEFINE_multi_int(name, default, help, lower_bound=None, upper_bound=None,
                     flag_values=FLAGS, **args):
  """Registers a flag whose value can be a list of arbitrary integers.

  Use the flag on the command line multiple times to place multiple
  integer values into the list.  The 'default' may be a single integer
  (which will be converted into a single-element list) or a list of
  integers.
  """
  parser = IntegerParser(lower_bound, upper_bound)
  serializer = ArgumentSerializer()
  DEFINE_multi(parser, serializer, name, default, help, flag_values, **args)


def DEFINE_multi_float(name, default, help, lower_bound=None, upper_bound=None,
                       flag_values=FLAGS, **args):
  """Registers a flag whose value can be a list of arbitrary floats.

  Use the flag on the command line multiple times to place multiple
  float values into the list.  The 'default' may be a single float
  (which will be converted into a single-element list) or a list of
  floats.
  """
  parser = FloatParser(lower_bound, upper_bound)
  serializer = ArgumentSerializer()
  DEFINE_multi(parser, serializer, name, default, help, flag_values, **args)


# Now register the flags that we want to exist in all applications.
# These are all defined with allow_override=1, so user-apps can use
# these flagnames for their own purposes, if they want.
DEFINE_flag(HelpFlag())
DEFINE_flag(HelpshortFlag())
DEFINE_flag(HelpXMLFlag())

# Define special flags here so that help may be generated for them.
# NOTE: Please do NOT use _SPECIAL_FLAGS from outside this module.
_SPECIAL_FLAGS = FlagValues()


DEFINE_string(
    'flagfile', "",
    "Insert flag definitions from the given file into the command line.",
    _SPECIAL_FLAGS)

DEFINE_string(
    'undefok', "",
    "comma-separated list of flag names that it is okay to specify "
    "on the command line even if the program does not define a flag "
    "with that name.  IMPORTANT: flags in this list that have "
    "arguments MUST use the --flag=value format.", _SPECIAL_FLAGS)

########NEW FILE########
__FILENAME__ = gflags_validators
#!/usr/bin/env python

# Copyright (c) 2010, Google Inc.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are
# met:
#
#     * Redistributions of source code must retain the above copyright
# notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above
# copyright notice, this list of conditions and the following disclaimer
# in the documentation and/or other materials provided with the
# distribution.
#     * Neither the name of Google Inc. nor the names of its
# contributors may be used to endorse or promote products derived from
# this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

"""Module to enforce different constraints on flags.

A validator represents an invariant, enforced over a one or more flags.
See 'FLAGS VALIDATORS' in gflags.py's docstring for a usage manual.
"""

__author__ = 'olexiy@google.com (Olexiy Oryeshko)'


class Error(Exception):
  """Thrown If validator constraint is not satisfied."""


class Validator(object):
  """Base class for flags validators.

  Users should NOT overload these classes, and use gflags.Register...
  methods instead.
  """

  # Used to assign each validator an unique insertion_index
  validators_count = 0

  def __init__(self, checker, message):
    """Constructor to create all validators.

    Args:
      checker: function to verify the constraint.
        Input of this method varies, see SimpleValidator and
          DictionaryValidator for a detailed description.
      message: string, error message to be shown to the user
    """
    self.checker = checker
    self.message = message
    Validator.validators_count += 1
    # Used to assert validators in the order they were registered (CL/18694236)
    self.insertion_index = Validator.validators_count

  def Verify(self, flag_values):
    """Verify that constraint is satisfied.

    flags library calls this method to verify Validator's constraint.
    Args:
      flag_values: gflags.FlagValues, containing all flags
    Raises:
      Error: if constraint is not satisfied.
    """
    param = self._GetInputToCheckerFunction(flag_values)
    if not self.checker(param):
      raise Error(self.message)

  def GetFlagsNames(self):
    """Return the names of the flags checked by this validator.

    Returns:
      [string], names of the flags
    """
    raise NotImplementedError('This method should be overloaded')

  def PrintFlagsWithValues(self, flag_values):
    raise NotImplementedError('This method should be overloaded')

  def _GetInputToCheckerFunction(self, flag_values):
    """Given flag values, construct the input to be given to checker.

    Args:
      flag_values: gflags.FlagValues, containing all flags.
    Returns:
      Return type depends on the specific validator.
    """
    raise NotImplementedError('This method should be overloaded')


class SimpleValidator(Validator):
  """Validator behind RegisterValidator() method.

  Validates that a single flag passes its checker function. The checker function
  takes the flag value and returns True (if value looks fine) or, if flag value
  is not valid, either returns False or raises an Exception."""
  def __init__(self, flag_name, checker, message):
    """Constructor.

    Args:
      flag_name: string, name of the flag.
      checker: function to verify the validator.
        input  - value of the corresponding flag (string, boolean, etc).
        output - Boolean. Must return True if validator constraint is satisfied.
          If constraint is not satisfied, it should either return False or
          raise Error.
      message: string, error message to be shown to the user if validator's
        condition is not satisfied
    """
    super(SimpleValidator, self).__init__(checker, message)
    self.flag_name = flag_name

  def GetFlagsNames(self):
    return [self.flag_name]

  def PrintFlagsWithValues(self, flag_values):
    return 'flag --%s=%s' % (self.flag_name, flag_values[self.flag_name].value)

  def _GetInputToCheckerFunction(self, flag_values):
    """Given flag values, construct the input to be given to checker.

    Args:
      flag_values: gflags.FlagValues
    Returns:
      value of the corresponding flag.
    """
    return flag_values[self.flag_name].value


class DictionaryValidator(Validator):
  """Validator behind RegisterDictionaryValidator method.

  Validates that flag values pass their common checker function. The checker
  function takes flag values and returns True (if values look fine) or,
  if values are not valid, either returns False or raises an Exception.
  """
  def __init__(self, flag_names, checker, message):
    """Constructor.

    Args:
      flag_names: [string], containing names of the flags used by checker.
      checker: function to verify the validator.
        input  - dictionary, with keys() being flag_names, and value for each
          key being the value of the corresponding flag (string, boolean, etc).
        output - Boolean. Must return True if validator constraint is satisfied.
          If constraint is not satisfied, it should either return False or
          raise Error.
      message: string, error message to be shown to the user if validator's
        condition is not satisfied
    """
    super(DictionaryValidator, self).__init__(checker, message)
    self.flag_names = flag_names

  def _GetInputToCheckerFunction(self, flag_values):
    """Given flag values, construct the input to be given to checker.

    Args:
      flag_values: gflags.FlagValues
    Returns:
      dictionary, with keys() being self.lag_names, and value for each key
        being the value of the corresponding flag (string, boolean, etc).
    """
    return dict([key, flag_values[key].value] for key in self.flag_names)

  def PrintFlagsWithValues(self, flag_values):
    prefix = 'flags '
    flags_with_values = []
    for key in self.flag_names:
      flags_with_values.append('%s=%s' % (key, flag_values[key].value))
    return prefix + ', '.join(flags_with_values)

  def GetFlagsNames(self):
    return self.flag_names

########NEW FILE########
__FILENAME__ = iri2uri
"""
iri2uri

Converts an IRI to a URI.

"""
__author__ = "Joe Gregorio (joe@bitworking.org)"
__copyright__ = "Copyright 2006, Joe Gregorio"
__contributors__ = []
__version__ = "1.0.0"
__license__ = "MIT"
__history__ = """
"""

import urlparse


# Convert an IRI to a URI following the rules in RFC 3987
#
# The characters we need to enocde and escape are defined in the spec:
#
# iprivate =  %xE000-F8FF / %xF0000-FFFFD / %x100000-10FFFD
# ucschar = %xA0-D7FF / %xF900-FDCF / %xFDF0-FFEF
#         / %x10000-1FFFD / %x20000-2FFFD / %x30000-3FFFD
#         / %x40000-4FFFD / %x50000-5FFFD / %x60000-6FFFD
#         / %x70000-7FFFD / %x80000-8FFFD / %x90000-9FFFD
#         / %xA0000-AFFFD / %xB0000-BFFFD / %xC0000-CFFFD
#         / %xD0000-DFFFD / %xE1000-EFFFD

escape_range = [
    (0xA0, 0xD7FF),
    (0xE000, 0xF8FF),
    (0xF900, 0xFDCF),
    (0xFDF0, 0xFFEF),
    (0x10000, 0x1FFFD),
    (0x20000, 0x2FFFD),
    (0x30000, 0x3FFFD),
    (0x40000, 0x4FFFD),
    (0x50000, 0x5FFFD),
    (0x60000, 0x6FFFD),
    (0x70000, 0x7FFFD),
    (0x80000, 0x8FFFD),
    (0x90000, 0x9FFFD),
    (0xA0000, 0xAFFFD),
    (0xB0000, 0xBFFFD),
    (0xC0000, 0xCFFFD),
    (0xD0000, 0xDFFFD),
    (0xE1000, 0xEFFFD),
    (0xF0000, 0xFFFFD),
    (0x100000, 0x10FFFD),
]

def encode(c):
    retval = c
    i = ord(c)
    for low, high in escape_range:
        if i < low:
            break
        if i >= low and i <= high:
            retval = "".join(["%%%2X" % ord(o) for o in c.encode('utf-8')])
            break
    return retval


def iri2uri(uri):
    """Convert an IRI to a URI. Note that IRIs must be
    passed in a unicode strings. That is, do not utf-8 encode
    the IRI before passing it into the function."""
    if isinstance(uri ,unicode):
        (scheme, authority, path, query, fragment) = urlparse.urlsplit(uri)
        authority = authority.encode('idna')
        # For each character in 'ucschar' or 'iprivate'
        #  1. encode as utf-8
        #  2. then %-encode each octet of that utf-8
        uri = urlparse.urlunsplit((scheme, authority, path, query, fragment))
        uri = "".join([encode(c) for c in uri])
    return uri

if __name__ == "__main__":
    import unittest

    class Test(unittest.TestCase):

        def test_uris(self):
            """Test that URIs are invariant under the transformation."""
            invariant = [
                u"ftp://ftp.is.co.za/rfc/rfc1808.txt",
                u"http://www.ietf.org/rfc/rfc2396.txt",
                u"ldap://[2001:db8::7]/c=GB?objectClass?one",
                u"mailto:John.Doe@example.com",
                u"news:comp.infosystems.www.servers.unix",
                u"tel:+1-816-555-1212",
                u"telnet://192.0.2.16:80/",
                u"urn:oasis:names:specification:docbook:dtd:xml:4.1.2" ]
            for uri in invariant:
                self.assertEqual(uri, iri2uri(uri))

        def test_iri(self):
            """ Test that the right type of escaping is done for each part of the URI."""
            self.assertEqual("http://xn--o3h.com/%E2%98%84", iri2uri(u"http://\N{COMET}.com/\N{COMET}"))
            self.assertEqual("http://bitworking.org/?fred=%E2%98%84", iri2uri(u"http://bitworking.org/?fred=\N{COMET}"))
            self.assertEqual("http://bitworking.org/#%E2%98%84", iri2uri(u"http://bitworking.org/#\N{COMET}"))
            self.assertEqual("#%E2%98%84", iri2uri(u"#\N{COMET}"))
            self.assertEqual("/fred?bar=%E2%98%9A#%E2%98%84", iri2uri(u"/fred?bar=\N{BLACK LEFT POINTING INDEX}#\N{COMET}"))
            self.assertEqual("/fred?bar=%E2%98%9A#%E2%98%84", iri2uri(iri2uri(u"/fred?bar=\N{BLACK LEFT POINTING INDEX}#\N{COMET}")))
            self.assertNotEqual("/fred?bar=%E2%98%9A#%E2%98%84", iri2uri(u"/fred?bar=\N{BLACK LEFT POINTING INDEX}#\N{COMET}".encode('utf-8')))

    unittest.main()



########NEW FILE########
__FILENAME__ = socks
"""SocksiPy - Python SOCKS module.
Version 1.00

Copyright 2006 Dan-Haim. All rights reserved.

Redistribution and use in source and binary forms, with or without modification,
are permitted provided that the following conditions are met:
1. Redistributions of source code must retain the above copyright notice, this
   list of conditions and the following disclaimer.
2. Redistributions in binary form must reproduce the above copyright notice,
   this list of conditions and the following disclaimer in the documentation
   and/or other materials provided with the distribution.
3. Neither the name of Dan Haim nor the names of his contributors may be used
   to endorse or promote products derived from this software without specific
   prior written permission.

THIS SOFTWARE IS PROVIDED BY DAN HAIM "AS IS" AND ANY EXPRESS OR IMPLIED
WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF
MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO
EVENT SHALL DAN HAIM OR HIS CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA
OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF
LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT
OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMANGE.


This module provides a standard socket-like interface for Python
for tunneling connections through SOCKS proxies.

"""

"""

Minor modifications made by Christopher Gilbert (http://motomastyle.com/)
for use in PyLoris (http://pyloris.sourceforge.net/)

Minor modifications made by Mario Vilas (http://breakingcode.wordpress.com/)
mainly to merge bug fixes found in Sourceforge

"""

import base64
import socket
import struct
import sys

if getattr(socket, 'socket', None) is None:
    raise ImportError('socket.socket missing, proxy support unusable')

PROXY_TYPE_SOCKS4 = 1
PROXY_TYPE_SOCKS5 = 2
PROXY_TYPE_HTTP = 3
PROXY_TYPE_HTTP_NO_TUNNEL = 4

_defaultproxy = None
_orgsocket = socket.socket

class ProxyError(Exception): pass
class GeneralProxyError(ProxyError): pass
class Socks5AuthError(ProxyError): pass
class Socks5Error(ProxyError): pass
class Socks4Error(ProxyError): pass
class HTTPError(ProxyError): pass

_generalerrors = ("success",
    "invalid data",
    "not connected",
    "not available",
    "bad proxy type",
    "bad input")

_socks5errors = ("succeeded",
    "general SOCKS server failure",
    "connection not allowed by ruleset",
    "Network unreachable",
    "Host unreachable",
    "Connection refused",
    "TTL expired",
    "Command not supported",
    "Address type not supported",
    "Unknown error")

_socks5autherrors = ("succeeded",
    "authentication is required",
    "all offered authentication methods were rejected",
    "unknown username or invalid password",
    "unknown error")

_socks4errors = ("request granted",
    "request rejected or failed",
    "request rejected because SOCKS server cannot connect to identd on the client",
    "request rejected because the client program and identd report different user-ids",
    "unknown error")

def setdefaultproxy(proxytype=None, addr=None, port=None, rdns=True, username=None, password=None):
    """setdefaultproxy(proxytype, addr[, port[, rdns[, username[, password]]]])
    Sets a default proxy which all further socksocket objects will use,
    unless explicitly changed.
    """
    global _defaultproxy
    _defaultproxy = (proxytype, addr, port, rdns, username, password)

def wrapmodule(module):
    """wrapmodule(module)
    Attempts to replace a module's socket library with a SOCKS socket. Must set
    a default proxy using setdefaultproxy(...) first.
    This will only work on modules that import socket directly into the namespace;
    most of the Python Standard Library falls into this category.
    """
    if _defaultproxy != None:
        module.socket.socket = socksocket
    else:
        raise GeneralProxyError((4, "no proxy specified"))

class socksocket(socket.socket):
    """socksocket([family[, type[, proto]]]) -> socket object
    Open a SOCKS enabled socket. The parameters are the same as
    those of the standard socket init. In order for SOCKS to work,
    you must specify family=AF_INET, type=SOCK_STREAM and proto=0.
    """

    def __init__(self, family=socket.AF_INET, type=socket.SOCK_STREAM, proto=0, _sock=None):
        _orgsocket.__init__(self, family, type, proto, _sock)
        if _defaultproxy != None:
            self.__proxy = _defaultproxy
        else:
            self.__proxy = (None, None, None, None, None, None)
        self.__proxysockname = None
        self.__proxypeername = None
        self.__httptunnel = True

    def __recvall(self, count):
        """__recvall(count) -> data
        Receive EXACTLY the number of bytes requested from the socket.
        Blocks until the required number of bytes have been received.
        """
        data = self.recv(count)
        while len(data) < count:
            d = self.recv(count-len(data))
            if not d: raise GeneralProxyError((0, "connection closed unexpectedly"))
            data = data + d
        return data

    def sendall(self, content, *args):
        """ override socket.socket.sendall method to rewrite the header
        for non-tunneling proxies if needed
        """
        if not self.__httptunnel:
            content = self.__rewriteproxy(content)
        return super(socksocket, self).sendall(content, *args)

    def __rewriteproxy(self, header):
        """ rewrite HTTP request headers to support non-tunneling proxies
        (i.e. those which do not support the CONNECT method).
        This only works for HTTP (not HTTPS) since HTTPS requires tunneling.
        """
        host, endpt = None, None
        hdrs = header.split("\r\n")
        for hdr in hdrs:
            if hdr.lower().startswith("host:"):
                host = hdr
            elif hdr.lower().startswith("get") or hdr.lower().startswith("post"):
                endpt = hdr
        if host and endpt:
            hdrs.remove(host)
            hdrs.remove(endpt)
            host = host.split(" ")[1]
            endpt = endpt.split(" ")
            if (self.__proxy[4] != None and self.__proxy[5] != None):
                hdrs.insert(0, self.__getauthheader())
            hdrs.insert(0, "Host: %s" % host)
            hdrs.insert(0, "%s http://%s%s %s" % (endpt[0], host, endpt[1], endpt[2]))
        return "\r\n".join(hdrs)

    def __getauthheader(self):
        auth = self.__proxy[4] + ":" + self.__proxy[5]
        return "Proxy-Authorization: Basic " + base64.b64encode(auth)

    def setproxy(self, proxytype=None, addr=None, port=None, rdns=True, username=None, password=None):
        """setproxy(proxytype, addr[, port[, rdns[, username[, password]]]])
        Sets the proxy to be used.
        proxytype -    The type of the proxy to be used. Three types
                are supported: PROXY_TYPE_SOCKS4 (including socks4a),
                PROXY_TYPE_SOCKS5 and PROXY_TYPE_HTTP
        addr -        The address of the server (IP or DNS).
        port -        The port of the server. Defaults to 1080 for SOCKS
                servers and 8080 for HTTP proxy servers.
        rdns -        Should DNS queries be preformed on the remote side
                (rather than the local side). The default is True.
                Note: This has no effect with SOCKS4 servers.
        username -    Username to authenticate with to the server.
                The default is no authentication.
        password -    Password to authenticate with to the server.
                Only relevant when username is also provided.
        """
        self.__proxy = (proxytype, addr, port, rdns, username, password)

    def __negotiatesocks5(self, destaddr, destport):
        """__negotiatesocks5(self,destaddr,destport)
        Negotiates a connection through a SOCKS5 server.
        """
        # First we'll send the authentication packages we support.
        if (self.__proxy[4]!=None) and (self.__proxy[5]!=None):
            # The username/password details were supplied to the
            # setproxy method so we support the USERNAME/PASSWORD
            # authentication (in addition to the standard none).
            self.sendall(struct.pack('BBBB', 0x05, 0x02, 0x00, 0x02))
        else:
            # No username/password were entered, therefore we
            # only support connections with no authentication.
            self.sendall(struct.pack('BBB', 0x05, 0x01, 0x00))
        # We'll receive the server's response to determine which
        # method was selected
        chosenauth = self.__recvall(2)
        if chosenauth[0:1] != chr(0x05).encode():
            self.close()
            raise GeneralProxyError((1, _generalerrors[1]))
        # Check the chosen authentication method
        if chosenauth[1:2] == chr(0x00).encode():
            # No authentication is required
            pass
        elif chosenauth[1:2] == chr(0x02).encode():
            # Okay, we need to perform a basic username/password
            # authentication.
            self.sendall(chr(0x01).encode() + chr(len(self.__proxy[4])) + self.__proxy[4] + chr(len(self.__proxy[5])) + self.__proxy[5])
            authstat = self.__recvall(2)
            if authstat[0:1] != chr(0x01).encode():
                # Bad response
                self.close()
                raise GeneralProxyError((1, _generalerrors[1]))
            if authstat[1:2] != chr(0x00).encode():
                # Authentication failed
                self.close()
                raise Socks5AuthError((3, _socks5autherrors[3]))
            # Authentication succeeded
        else:
            # Reaching here is always bad
            self.close()
            if chosenauth[1] == chr(0xFF).encode():
                raise Socks5AuthError((2, _socks5autherrors[2]))
            else:
                raise GeneralProxyError((1, _generalerrors[1]))
        # Now we can request the actual connection
        req = struct.pack('BBB', 0x05, 0x01, 0x00)
        # If the given destination address is an IP address, we'll
        # use the IPv4 address request even if remote resolving was specified.
        try:
            ipaddr = socket.inet_aton(destaddr)
            req = req + chr(0x01).encode() + ipaddr
        except socket.error:
            # Well it's not an IP number,  so it's probably a DNS name.
            if self.__proxy[3]:
                # Resolve remotely
                ipaddr = None
                req = req + chr(0x03).encode() + chr(len(destaddr)).encode() + destaddr
            else:
                # Resolve locally
                ipaddr = socket.inet_aton(socket.gethostbyname(destaddr))
                req = req + chr(0x01).encode() + ipaddr
        req = req + struct.pack(">H", destport)
        self.sendall(req)
        # Get the response
        resp = self.__recvall(4)
        if resp[0:1] != chr(0x05).encode():
            self.close()
            raise GeneralProxyError((1, _generalerrors[1]))
        elif resp[1:2] != chr(0x00).encode():
            # Connection failed
            self.close()
            if ord(resp[1:2])<=8:
                raise Socks5Error((ord(resp[1:2]), _socks5errors[ord(resp[1:2])]))
            else:
                raise Socks5Error((9, _socks5errors[9]))
        # Get the bound address/port
        elif resp[3:4] == chr(0x01).encode():
            boundaddr = self.__recvall(4)
        elif resp[3:4] == chr(0x03).encode():
            resp = resp + self.recv(1)
            boundaddr = self.__recvall(ord(resp[4:5]))
        else:
            self.close()
            raise GeneralProxyError((1,_generalerrors[1]))
        boundport = struct.unpack(">H", self.__recvall(2))[0]
        self.__proxysockname = (boundaddr, boundport)
        if ipaddr != None:
            self.__proxypeername = (socket.inet_ntoa(ipaddr), destport)
        else:
            self.__proxypeername = (destaddr, destport)

    def getproxysockname(self):
        """getsockname() -> address info
        Returns the bound IP address and port number at the proxy.
        """
        return self.__proxysockname

    def getproxypeername(self):
        """getproxypeername() -> address info
        Returns the IP and port number of the proxy.
        """
        return _orgsocket.getpeername(self)

    def getpeername(self):
        """getpeername() -> address info
        Returns the IP address and port number of the destination
        machine (note: getproxypeername returns the proxy)
        """
        return self.__proxypeername

    def __negotiatesocks4(self,destaddr,destport):
        """__negotiatesocks4(self,destaddr,destport)
        Negotiates a connection through a SOCKS4 server.
        """
        # Check if the destination address provided is an IP address
        rmtrslv = False
        try:
            ipaddr = socket.inet_aton(destaddr)
        except socket.error:
            # It's a DNS name. Check where it should be resolved.
            if self.__proxy[3]:
                ipaddr = struct.pack("BBBB", 0x00, 0x00, 0x00, 0x01)
                rmtrslv = True
            else:
                ipaddr = socket.inet_aton(socket.gethostbyname(destaddr))
        # Construct the request packet
        req = struct.pack(">BBH", 0x04, 0x01, destport) + ipaddr
        # The username parameter is considered userid for SOCKS4
        if self.__proxy[4] != None:
            req = req + self.__proxy[4]
        req = req + chr(0x00).encode()
        # DNS name if remote resolving is required
        # NOTE: This is actually an extension to the SOCKS4 protocol
        # called SOCKS4A and may not be supported in all cases.
        if rmtrslv:
            req = req + destaddr + chr(0x00).encode()
        self.sendall(req)
        # Get the response from the server
        resp = self.__recvall(8)
        if resp[0:1] != chr(0x00).encode():
            # Bad data
            self.close()
            raise GeneralProxyError((1,_generalerrors[1]))
        if resp[1:2] != chr(0x5A).encode():
            # Server returned an error
            self.close()
            if ord(resp[1:2]) in (91, 92, 93):
                self.close()
                raise Socks4Error((ord(resp[1:2]), _socks4errors[ord(resp[1:2]) - 90]))
            else:
                raise Socks4Error((94, _socks4errors[4]))
        # Get the bound address/port
        self.__proxysockname = (socket.inet_ntoa(resp[4:]), struct.unpack(">H", resp[2:4])[0])
        if rmtrslv != None:
            self.__proxypeername = (socket.inet_ntoa(ipaddr), destport)
        else:
            self.__proxypeername = (destaddr, destport)

    def __negotiatehttp(self, destaddr, destport):
        """__negotiatehttp(self,destaddr,destport)
        Negotiates a connection through an HTTP server.
        """
        # If we need to resolve locally, we do this now
        if not self.__proxy[3]:
            addr = socket.gethostbyname(destaddr)
        else:
            addr = destaddr
        headers =  ["CONNECT ", addr, ":", str(destport), " HTTP/1.1\r\n"]
        headers += ["Host: ", destaddr, "\r\n"]
        if (self.__proxy[4] != None and self.__proxy[5] != None):
                headers += [self.__getauthheader(), "\r\n"]
        headers.append("\r\n")
        self.sendall("".join(headers).encode())
        # We read the response until we get the string "\r\n\r\n"
        resp = self.recv(1)
        while resp.find("\r\n\r\n".encode()) == -1:
            resp = resp + self.recv(1)
        # We just need the first line to check if the connection
        # was successful
        statusline = resp.splitlines()[0].split(" ".encode(), 2)
        if statusline[0] not in ("HTTP/1.0".encode(), "HTTP/1.1".encode()):
            self.close()
            raise GeneralProxyError((1, _generalerrors[1]))
        try:
            statuscode = int(statusline[1])
        except ValueError:
            self.close()
            raise GeneralProxyError((1, _generalerrors[1]))
        if statuscode != 200:
            self.close()
            raise HTTPError((statuscode, statusline[2]))
        self.__proxysockname = ("0.0.0.0", 0)
        self.__proxypeername = (addr, destport)

    def connect(self, destpair):
        """connect(self, despair)
        Connects to the specified destination through a proxy.
        destpar - A tuple of the IP/DNS address and the port number.
        (identical to socket's connect).
        To select the proxy server use setproxy().
        """
        # Do a minimal input check first
        if (not type(destpair) in (list,tuple)) or (len(destpair) < 2) or (not isinstance(destpair[0], basestring)) or (type(destpair[1]) != int):
            raise GeneralProxyError((5, _generalerrors[5]))
        if self.__proxy[0] == PROXY_TYPE_SOCKS5:
            if self.__proxy[2] != None:
                portnum = self.__proxy[2]
            else:
                portnum = 1080
            _orgsocket.connect(self, (self.__proxy[1], portnum))
            self.__negotiatesocks5(destpair[0], destpair[1])
        elif self.__proxy[0] == PROXY_TYPE_SOCKS4:
            if self.__proxy[2] != None:
                portnum = self.__proxy[2]
            else:
                portnum = 1080
            _orgsocket.connect(self,(self.__proxy[1], portnum))
            self.__negotiatesocks4(destpair[0], destpair[1])
        elif self.__proxy[0] == PROXY_TYPE_HTTP:
            if self.__proxy[2] != None:
                portnum = self.__proxy[2]
            else:
                portnum = 8080
            _orgsocket.connect(self,(self.__proxy[1], portnum))
            self.__negotiatehttp(destpair[0], destpair[1])
        elif self.__proxy[0] == PROXY_TYPE_HTTP_NO_TUNNEL:
            if self.__proxy[2] != None:
                portnum = self.__proxy[2]
            else:
                portnum = 8080
            _orgsocket.connect(self,(self.__proxy[1],portnum))
            if destpair[1] == 443:
                self.__negotiatehttp(destpair[0],destpair[1])
            else:
                self.__httptunnel = False
        elif self.__proxy[0] == None:
            _orgsocket.connect(self, (destpair[0], destpair[1]))
        else:
            raise GeneralProxyError((4, _generalerrors[4]))

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
import cgi
import httplib2
import logging
import os
import pickle
import time

from google.appengine.api import app_identity
from google.appengine.api import memcache
from google.appengine.api import users
from google.appengine.ext import db
from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import login_required
from google.appengine.ext.webapp.util import run_wsgi_app
from oauth2client import GOOGLE_AUTH_URI
from oauth2client import GOOGLE_REVOKE_URI
from oauth2client import GOOGLE_TOKEN_URI
from oauth2client import clientsecrets
from oauth2client import util
from oauth2client import xsrfutil
from oauth2client.anyjson import simplejson
from oauth2client.client import AccessTokenRefreshError
from oauth2client.client import AssertionCredentials
from oauth2client.client import Credentials
from oauth2client.client import Flow
from oauth2client.client import OAuth2WebServerFlow
from oauth2client.client import Storage

# TODO(dhermes): Resolve import issue.
# This is a temporary fix for a Google internal issue.
try:
  from google.appengine.ext import ndb
except ImportError:
  ndb = None


logger = logging.getLogger(__name__)

OAUTH2CLIENT_NAMESPACE = 'oauth2client#ns'

XSRF_MEMCACHE_ID = 'xsrf_secret_key'


def _safe_html(s):
  """Escape text to make it safe to display.

  Args:
    s: string, The text to escape.

  Returns:
    The escaped text as a string.
  """
  return cgi.escape(s, quote=1).replace("'", '&#39;')


class InvalidClientSecretsError(Exception):
  """The client_secrets.json file is malformed or missing required fields."""


class InvalidXsrfTokenError(Exception):
  """The XSRF token is invalid or expired."""


class SiteXsrfSecretKey(db.Model):
  """Storage for the sites XSRF secret key.

  There will only be one instance stored of this model, the one used for the
  site.
  """
  secret = db.StringProperty()

if ndb is not None:
  class SiteXsrfSecretKeyNDB(ndb.Model):
    """NDB Model for storage for the sites XSRF secret key.

    Since this model uses the same kind as SiteXsrfSecretKey, it can be used
    interchangeably. This simply provides an NDB model for interacting with the
    same data the DB model interacts with.

    There should only be one instance stored of this model, the one used for the
    site.
    """
    secret = ndb.StringProperty()

    @classmethod
    def _get_kind(cls):
      """Return the kind name for this class."""
      return 'SiteXsrfSecretKey'


def _generate_new_xsrf_secret_key():
  """Returns a random XSRF secret key.
  """
  return os.urandom(16).encode("hex")


def xsrf_secret_key():
  """Return the secret key for use for XSRF protection.

  If the Site entity does not have a secret key, this method will also create
  one and persist it.

  Returns:
    The secret key.
  """
  secret = memcache.get(XSRF_MEMCACHE_ID, namespace=OAUTH2CLIENT_NAMESPACE)
  if not secret:
    # Load the one and only instance of SiteXsrfSecretKey.
    model = SiteXsrfSecretKey.get_or_insert(key_name='site')
    if not model.secret:
      model.secret = _generate_new_xsrf_secret_key()
      model.put()
    secret = model.secret
    memcache.add(XSRF_MEMCACHE_ID, secret, namespace=OAUTH2CLIENT_NAMESPACE)

  return str(secret)


class AppAssertionCredentials(AssertionCredentials):
  """Credentials object for App Engine Assertion Grants

  This object will allow an App Engine application to identify itself to Google
  and other OAuth 2.0 servers that can verify assertions. It can be used for the
  purpose of accessing data stored under an account assigned to the App Engine
  application itself.

  This credential does not require a flow to instantiate because it represents
  a two legged flow, and therefore has all of the required information to
  generate and refresh its own access tokens.
  """

  @util.positional(2)
  def __init__(self, scope, **kwargs):
    """Constructor for AppAssertionCredentials

    Args:
      scope: string or iterable of strings, scope(s) of the credentials being
        requested.
    """
    self.scope = util.scopes_to_string(scope)

    # Assertion type is no longer used, but still in the parent class signature.
    super(AppAssertionCredentials, self).__init__(None)

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
      scopes = self.scope.split()
      (token, _) = app_identity.get_access_token(scopes)
    except app_identity.Error, e:
      raise AccessTokenRefreshError(str(e))
    self.access_token = token


class FlowProperty(db.Property):
  """App Engine datastore Property for Flow.

  Utility property that allows easy storage and retrieval of an
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


if ndb is not None:
  class FlowNDBProperty(ndb.PickleProperty):
    """App Engine NDB datastore Property for Flow.

    Serves the same purpose as the DB FlowProperty, but for NDB models. Since
    PickleProperty inherits from BlobProperty, the underlying representation of
    the data in the datastore will be the same as in the DB case.

    Utility property that allows easy storage and retrieval of an
    oauth2client.Flow
    """

    def _validate(self, value):
      """Validates a value as a proper Flow object.

      Args:
        value: A value to be set on the property.

      Raises:
        TypeError if the value is not an instance of Flow.
      """
      logger.info('validate: Got type %s', type(value))
      if value is not None and not isinstance(value, Flow):
        raise TypeError('Property %s must be convertible to a flow '
                        'instance; received: %s.' % (self._name, value))


class CredentialsProperty(db.Property):
  """App Engine datastore Property for Credentials.

  Utility property that allows easy storage and retrieval of
  oath2client.Credentials
  """

  # Tell what the user type is.
  data_type = Credentials

  # For writing to datastore.
  def get_value_for_datastore(self, model_instance):
    logger.info("get: Got type " + str(type(model_instance)))
    cred = super(CredentialsProperty,
                 self).get_value_for_datastore(model_instance)
    if cred is None:
      cred = ''
    else:
      cred = cred.to_json()
    return db.Blob(cred)

  # For reading from datastore.
  def make_value_from_datastore(self, value):
    logger.info("make: Got type " + str(type(value)))
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
    logger.info("validate: Got type " + str(type(value)))
    if value is not None and not isinstance(value, Credentials):
      raise db.BadValueError('Property %s must be convertible '
                          'to a Credentials instance (%s)' %
                            (self.name, value))
    #if value is not None and not isinstance(value, Credentials):
    #  return None
    return value


if ndb is not None:
  # TODO(dhermes): Turn this into a JsonProperty and overhaul the Credentials
  #                and subclass mechanics to use new_from_dict, to_dict,
  #                from_dict, etc.
  class CredentialsNDBProperty(ndb.BlobProperty):
    """App Engine NDB datastore Property for Credentials.

    Serves the same purpose as the DB CredentialsProperty, but for NDB models.
    Since CredentialsProperty stores data as a blob and this inherits from
    BlobProperty, the data in the datastore will be the same as in the DB case.

    Utility property that allows easy storage and retrieval of Credentials and
    subclasses.
    """
    def _validate(self, value):
      """Validates a value as a proper credentials object.

      Args:
        value: A value to be set on the property.

      Raises:
        TypeError if the value is not an instance of Credentials.
      """
      logger.info('validate: Got type %s', type(value))
      if value is not None and not isinstance(value, Credentials):
        raise TypeError('Property %s must be convertible to a credentials '
                        'instance; received: %s.' % (self._name, value))

    def _to_base_type(self, value):
      """Converts our validated value to a JSON serialized string.

      Args:
        value: A value to be set in the datastore.

      Returns:
        A JSON serialized version of the credential, else '' if value is None.
      """
      if value is None:
        return ''
      else:
        return value.to_json()

    def _from_base_type(self, value):
      """Converts our stored JSON string back to the desired type.

      Args:
        value: A value from the datastore to be converted to the desired type.

      Returns:
        A deserialized Credentials (or subclass) object, else None if the
            value can't be parsed.
      """
      if not value:
        return None
      try:
        # Uses the from_json method of the implied class of value
        credentials = Credentials.new_from_json(value)
      except ValueError:
        credentials = None
      return credentials


class StorageByKeyName(Storage):
  """Store and retrieve a credential to and from the App Engine datastore.

  This Storage helper presumes the Credentials have been stored as a
  CredentialsProperty or CredentialsNDBProperty on a datastore model class, and
  that entities are stored by key_name.
  """

  @util.positional(4)
  def __init__(self, model, key_name, property_name, cache=None):
    """Constructor for Storage.

    Args:
      model: db.Model or ndb.Model, model class
      key_name: string, key name for the entity that has the credentials
      property_name: string, name of the property that is a CredentialsProperty
        or CredentialsNDBProperty.
      cache: memcache, a write-through cache to put in front of the datastore.
        If the model you are using is an NDB model, using a cache will be
        redundant since the model uses an instance cache and memcache for you.
    """
    self._model = model
    self._key_name = key_name
    self._property_name = property_name
    self._cache = cache

  def _is_ndb(self):
    """Determine whether the model of the instance is an NDB model.

    Returns:
      Boolean indicating whether or not the model is an NDB or DB model.
    """
    # issubclass will fail if one of the arguments is not a class, only need
    # worry about new-style classes since ndb and db models are new-style
    if isinstance(self._model, type):
      if ndb is not None and issubclass(self._model, ndb.Model):
        return True
      elif issubclass(self._model, db.Model):
        return False

    raise TypeError('Model class not an NDB or DB model: %s.' % (self._model,))

  def _get_entity(self):
    """Retrieve entity from datastore.

    Uses a different model method for db or ndb models.

    Returns:
      Instance of the model corresponding to the current storage object
          and stored using the key name of the storage object.
    """
    if self._is_ndb():
      return self._model.get_by_id(self._key_name)
    else:
      return self._model.get_by_key_name(self._key_name)

  def _delete_entity(self):
    """Delete entity from datastore.

    Attempts to delete using the key_name stored on the object, whether or not
    the given key is in the datastore.
    """
    if self._is_ndb():
      ndb.Key(self._model, self._key_name).delete()
    else:
      entity_key = db.Key.from_path(self._model.kind(), self._key_name)
      db.delete(entity_key)

  def locked_get(self):
    """Retrieve Credential from datastore.

    Returns:
      oauth2client.Credentials
    """
    if self._cache:
      json = self._cache.get(self._key_name)
      if json:
        return Credentials.new_from_json(json)

    credentials = None
    entity = self._get_entity()
    if entity is not None:
      credentials = getattr(entity, self._property_name)
      if credentials and hasattr(credentials, 'set_store'):
        credentials.set_store(self)
        if self._cache:
          self._cache.set(self._key_name, credentials.to_json())

    return credentials

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

    self._delete_entity()


class CredentialsModel(db.Model):
  """Storage for OAuth 2.0 Credentials

  Storage of the model is keyed by the user.user_id().
  """
  credentials = CredentialsProperty()


if ndb is not None:
  class CredentialsNDBModel(ndb.Model):
    """NDB Model for storage of OAuth 2.0 Credentials

    Since this model uses the same kind as CredentialsModel and has a property
    which can serialize and deserialize Credentials correctly, it can be used
    interchangeably with a CredentialsModel to access, insert and delete the
    same entities. This simply provides an NDB model for interacting with the
    same data the DB model interacts with.

    Storage of the model is keyed by the user.user_id().
    """
    credentials = CredentialsNDBProperty()

    @classmethod
    def _get_kind(cls):
      """Return the kind name for this class."""
      return 'CredentialsModel'


def _build_state_value(request_handler, user):
  """Composes the value for the 'state' parameter.

  Packs the current request URI and an XSRF token into an opaque string that
  can be passed to the authentication server via the 'state' parameter.

  Args:
    request_handler: webapp.RequestHandler, The request.
    user: google.appengine.api.users.User, The current user.

  Returns:
    The state value as a string.
  """
  uri = request_handler.request.url
  token = xsrfutil.generate_token(xsrf_secret_key(), user.user_id(),
                                  action_id=str(uri))
  return  uri + ':' + token


def _parse_state_value(state, user):
  """Parse the value of the 'state' parameter.

  Parses the value and validates the XSRF token in the state parameter.

  Args:
    state: string, The value of the state parameter.
    user: google.appengine.api.users.User, The current user.

  Raises:
    InvalidXsrfTokenError: if the XSRF token is invalid.

  Returns:
    The redirect URI.
  """
  uri, token = state.rsplit(':', 1)
  if not xsrfutil.validate_token(xsrf_secret_key(), token, user.user_id(),
                                 action_id=uri):
    raise InvalidXsrfTokenError()

  return uri


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

  @util.positional(4)
  def __init__(self, client_id, client_secret, scope,
               auth_uri=GOOGLE_AUTH_URI,
               token_uri=GOOGLE_TOKEN_URI,
               revoke_uri=GOOGLE_REVOKE_URI,
               user_agent=None,
               message=None,
               callback_path='/oauth2callback',
               token_response_param=None,
               **kwargs):

    """Constructor for OAuth2Decorator

    Args:
      client_id: string, client identifier.
      client_secret: string client secret.
      scope: string or iterable of strings, scope(s) of the credentials being
        requested.
      auth_uri: string, URI for authorization endpoint. For convenience
        defaults to Google's endpoints but any OAuth 2.0 provider can be used.
      token_uri: string, URI for token endpoint. For convenience
        defaults to Google's endpoints but any OAuth 2.0 provider can be used.
      revoke_uri: string, URI for revoke endpoint. For convenience
        defaults to Google's endpoints but any OAuth 2.0 provider can be used.
      user_agent: string, User agent of your application, default to None.
      message: Message to display if there are problems with the OAuth 2.0
        configuration. The message may contain HTML and will be presented on the
        web interface for any method that uses the decorator.
      callback_path: string, The absolute path to use as the callback URI. Note
        that this must match up with the URI given when registering the
        application in the APIs Console.
      token_response_param: string. If provided, the full JSON response
        to the access token request will be encoded and included in this query
        parameter in the callback URI. This is useful with providers (e.g.
        wordpress.com) that include extra fields that the client may want.
      **kwargs: dict, Keyword arguments are be passed along as kwargs to the
        OAuth2WebServerFlow constructor.
    """
    self.flow = None
    self.credentials = None
    self._client_id = client_id
    self._client_secret = client_secret
    self._scope = util.scopes_to_string(scope)
    self._auth_uri = auth_uri
    self._token_uri = token_uri
    self._revoke_uri = revoke_uri
    self._user_agent = user_agent
    self._kwargs = kwargs
    self._message = message
    self._in_error = False
    self._callback_path = callback_path
    self._token_response_param = token_response_param

  def _display_error_message(self, request_handler):
    request_handler.response.out.write('<html><body>')
    request_handler.response.out.write(_safe_html(self._message))
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

      self._create_flow(request_handler)

      # Store the request URI in 'state' so we can use it later
      self.flow.params['state'] = _build_state_value(request_handler, user)
      self.credentials = StorageByKeyName(
          CredentialsModel, user.user_id(), 'credentials').get()

      if not self.has_credentials():
        return request_handler.redirect(self.authorize_url())
      try:
        return method(request_handler, *args, **kwargs)
      except AccessTokenRefreshError:
        return request_handler.redirect(self.authorize_url())

    return check_oauth

  def _create_flow(self, request_handler):
    """Create the Flow object.

    The Flow is calculated lazily since we don't know where this app is
    running until it receives a request, at which point redirect_uri can be
    calculated and then the Flow object can be constructed.

    Args:
      request_handler: webapp.RequestHandler, the request handler.
    """
    if self.flow is None:
      redirect_uri = request_handler.request.relative_url(
          self._callback_path) # Usually /oauth2callback
      self.flow = OAuth2WebServerFlow(self._client_id, self._client_secret,
                                      self._scope, redirect_uri=redirect_uri,
                                      user_agent=self._user_agent,
                                      auth_uri=self._auth_uri,
                                      token_uri=self._token_uri,
                                      revoke_uri=self._revoke_uri,
                                      **self._kwargs)

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

      self._create_flow(request_handler)

      self.flow.params['state'] = _build_state_value(request_handler, user)
      self.credentials = StorageByKeyName(
          CredentialsModel, user.user_id(), 'credentials').get()
      return method(request_handler, *args, **kwargs)
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
    url = self.flow.step1_get_authorize_url()
    return str(url)

  def http(self):
    """Returns an authorized http instance.

    Must only be called from within an @oauth_required decorated method, or
    from within an @oauth_aware decorated method where has_credentials()
    returns True.
    """
    return self.credentials.authorize(httplib2.Http())

  @property
  def callback_path(self):
    """The absolute path where the callback will occur.

    Note this is the absolute path, not the absolute URI, that will be
    calculated by the decorator at runtime. See callback_handler() for how this
    should be used.

    Returns:
      The callback path as a string.
    """
    return self._callback_path


  def callback_handler(self):
    """RequestHandler for the OAuth 2.0 redirect callback.

    Usage:
       app = webapp.WSGIApplication([
         ('/index', MyIndexHandler),
         ...,
         (decorator.callback_path, decorator.callback_handler())
       ])

    Returns:
      A webapp.RequestHandler that handles the redirect back from the
      server during the OAuth 2.0 dance.
    """
    decorator = self

    class OAuth2Handler(webapp.RequestHandler):
      """Handler for the redirect_uri of the OAuth 2.0 dance."""

      @login_required
      def get(self):
        error = self.request.get('error')
        if error:
          errormsg = self.request.get('error_description', error)
          self.response.out.write(
              'The authorization request failed: %s' % _safe_html(errormsg))
        else:
          user = users.get_current_user()
          decorator._create_flow(self)
          credentials = decorator.flow.step2_exchange(self.request.params)
          StorageByKeyName(
              CredentialsModel, user.user_id(), 'credentials').put(credentials)
          redirect_uri = _parse_state_value(str(self.request.get('state')),
                                            user)

          if decorator._token_response_param and credentials.token_response:
            resp_json = simplejson.dumps(credentials.token_response)
            redirect_uri = util._add_query_parameter(
                redirect_uri, decorator._token_response_param, resp_json)

          self.redirect(redirect_uri)

    return OAuth2Handler

  def callback_application(self):
    """WSGI application for handling the OAuth 2.0 redirect callback.

    If you need finer grained control use `callback_handler` which returns just
    the webapp.RequestHandler.

    Returns:
      A webapp.WSGIApplication that handles the redirect back from the
      server during the OAuth 2.0 dance.
    """
    return webapp.WSGIApplication([
        (self.callback_path, self.callback_handler())
        ])


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

  @util.positional(3)
  def __init__(self, filename, scope, message=None, cache=None):
    """Constructor

    Args:
      filename: string, File name of client secrets.
      scope: string or iterable of strings, scope(s) of the credentials being
        requested.
      message: string, A friendly string to display to the user if the
        clientsecrets file is missing or invalid. The message may contain HTML
        and will be presented on the web interface for any method that uses the
        decorator.
      cache: An optional cache service client that implements get() and set()
        methods. See clientsecrets.loadfile() for details.
    """
    client_type, client_info = clientsecrets.loadfile(filename, cache=cache)
    if client_type not in [
        clientsecrets.TYPE_WEB, clientsecrets.TYPE_INSTALLED]:
      raise InvalidClientSecretsError(
          'OAuth2Decorator doesn\'t support this OAuth 2.0 flow.')
    constructor_kwargs = {
      'auth_uri': client_info['auth_uri'],
      'token_uri': client_info['token_uri'],
      'message': message,
    }
    revoke_uri = client_info.get('revoke_uri')
    if revoke_uri is not None:
      constructor_kwargs['revoke_uri'] = revoke_uri
    super(OAuth2DecoratorFromClientSecrets, self).__init__(
        client_info['client_id'], client_info['client_secret'],
        scope, **constructor_kwargs)
    if message is not None:
      self._message = message
    else:
      self._message = 'Please configure your application for OAuth 2.0.'


@util.positional(2)
def oauth2decorator_from_clientsecrets(filename, scope,
                                       message=None, cache=None):
  """Creates an OAuth2Decorator populated from a clientsecrets file.

  Args:
    filename: string, File name of client secrets.
    scope: string or list of strings, scope(s) of the credentials being
      requested.
    message: string, A friendly string to display to the user if the
      clientsecrets file is missing or invalid. The message may contain HTML and
      will be presented on the web interface for any method that uses the
      decorator.
    cache: An optional cache service client that implements get() and set()
      methods. See clientsecrets.loadfile() for details.

  Returns: An OAuth2Decorator

  """
  return OAuth2DecoratorFromClientSecrets(filename, scope,
                                          message=message, cache=cache)

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

from oauth2client import GOOGLE_AUTH_URI
from oauth2client import GOOGLE_REVOKE_URI
from oauth2client import GOOGLE_TOKEN_URI
from oauth2client import util
from oauth2client.anyjson import simplejson

HAS_OPENSSL = False
HAS_CRYPTO = False
try:
  from oauth2client import crypt
  HAS_CRYPTO = True
  if crypt.OpenSSLVerifier is not None:
    HAS_OPENSSL = True
except ImportError:
  pass

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

# Google Data client libraries may need to set this to [401, 403].
REFRESH_STATUS_CODES = [401]


class Error(Exception):
  """Base error for this module."""


class FlowExchangeError(Error):
  """Error trying to exchange an authorization grant for an access token."""


class AccessTokenRefreshError(Error):
  """Error trying to refresh an expired access token."""


class TokenRevokeError(Error):
  """Error trying to revoke a token."""


class UnknownClientSecretsFlowError(Error):
  """The client secrets file called for an unknown type of OAuth 2.0 flow. """


class AccessTokenCredentialsError(Error):
  """Having only the access_token means no refresh is possible."""


class VerifyJwtTokenError(Error):
  """Could on retrieve certificates for validation."""


class NonAsciiHeaderError(Error):
  """Header names and values must be ASCII strings."""


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
    """Take an httplib2.Http instance (or equivalent) and authorizes it.

    Authorizes it for the set of credentials, usually by replacing
    http.request() with a method that adds in the appropriate headers and then
    delegates to the original Http.request() method.

    Args:
      http: httplib2.Http, an http object to be used to make the refresh
        request.
    """
    _abstract()

  def refresh(self, http):
    """Forces a refresh of the access_token.

    Args:
      http: httplib2.Http, an http object to be used to make the refresh
        request.
    """
    _abstract()

  def revoke(self, http):
    """Revokes a refresh_token and makes the credentials void.

    Args:
      http: httplib2.Http, an http object to be used to make the revoke
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
    """Utility function that creates JSON repr. of a Credentials object.

    Args:
      strip: array, An array of names of members to not include in the JSON.

    Returns:
       string, a JSON representation of this instance, suitable to pass to
       from_json().
    """
    t = type(self)
    d = copy.copy(self.__dict__)
    for member in strip:
      if member in d:
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

  @classmethod
  def from_json(cls, s):
    """Instantiate a Credentials object from a JSON description of it.

    The JSON should have been produced by calling .to_json() on the object.

    Args:
      data: dict, A deserialized JSON object.

    Returns:
      An instance of a Credentials subclass.
    """
    return Credentials()


class Flow(object):
  """Base class for all Flow objects."""
  pass


class Storage(object):
  """Base class for all Storage objects.

  Store and retrieve a single credential. This class supports locking
  such that multiple processes and threads can operate on a single
  store.
  """

  def acquire_lock(self):
    """Acquires any lock necessary to access this Storage.

    This lock is not reentrant.
    """
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


def clean_headers(headers):
  """Forces header keys and values to be strings, i.e not unicode.

  The httplib module just concats the header keys and values in a way that may
  make the message header a unicode string, which, if it then tries to
  contatenate to a binary request body may result in a unicode decode error.

  Args:
    headers: dict, A dictionary of headers.

  Returns:
    The same dictionary but with all the keys converted to strings.
  """
  clean = {}
  try:
    for k, v in headers.iteritems():
      clean[str(k)] = str(v)
  except UnicodeEncodeError:
    raise NonAsciiHeaderError(k + ': ' + v)
  return clean


def _update_query_params(uri, params):
  """Updates a URI with new query parameters.

  Args:
    uri: string, A valid URI, with potential existing query parameters.
    params: dict, A dictionary of query parameters.

  Returns:
    The same URI but with the new query parameters added.
  """
  parts = list(urlparse.urlparse(uri))
  query_params = dict(parse_qsl(parts[4])) # 4 is the index of the query part
  query_params.update(params)
  parts[4] = urllib.urlencode(query_params)
  return urlparse.urlunparse(parts)


class OAuth2Credentials(Credentials):
  """Credentials object for OAuth 2.0.

  Credentials can be applied to an httplib2.Http object using the authorize()
  method, which then adds the OAuth 2.0 access token to each request.

  OAuth2Credentials objects may be safely pickled and unpickled.
  """

  @util.positional(8)
  def __init__(self, access_token, client_id, client_secret, refresh_token,
               token_expiry, token_uri, user_agent, revoke_uri=None,
               id_token=None, token_response=None):
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
      revoke_uri: string, URI for revoke endpoint. Defaults to None; a token
        can't be revoked if this is None.
      id_token: object, The identity of the resource owner.
      token_response: dict, the decoded response to the token request. None
        if a token hasn't been requested yet. Stored because some providers
        (e.g. wordpress.com) include extra fields that clients may want.

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
    self.revoke_uri = revoke_uri
    self.id_token = id_token
    self.token_response = token_response

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
    @util.positional(1)
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

      resp, content = request_orig(uri, method, body, clean_headers(headers),
                                   redirections, connection_type)

      if resp.status in REFRESH_STATUS_CODES:
        logger.info('Refreshing due to a %s' % str(resp.status))
        self._refresh(request_orig)
        self.apply(headers)
        return request_orig(uri, method, body, clean_headers(headers),
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

  def revoke(self, http):
    """Revokes a refresh_token and makes the credentials void.

    Args:
      http: httplib2.Http, an http object to be used to make the revoke
        request.
    """
    self._revoke(http.request)

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
    retval = cls(
        data['access_token'],
        data['client_id'],
        data['client_secret'],
        data['refresh_token'],
        data['token_expiry'],
        data['token_uri'],
        data['user_agent'],
        revoke_uri=data.get('revoke_uri', None),
        id_token=data.get('id_token', None),
        token_response=data.get('token_response', None))
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
        has expired and been refreshed. This implementation uses
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

    logger.info('Refreshing access_token')
    resp, content = http_request(
        self.token_uri, method='POST', body=body, headers=headers)
    if resp.status == 200:
      # TODO(jcgregorio) Raise an error if loads fails?
      d = simplejson.loads(content)
      self.token_response = d
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
      logger.info('Failed to retrieve access token: %s' % content)
      error_msg = 'Invalid response %s.' % resp['status']
      try:
        d = simplejson.loads(content)
        if 'error' in d:
          error_msg = d['error']
          self.invalid = True
          if self.store:
            self.store.locked_put(self)
      except StandardError:
        pass
      raise AccessTokenRefreshError(error_msg)

  def _revoke(self, http_request):
    """Revokes the refresh_token and deletes the store if available.

    Args:
      http_request: callable, a callable that matches the method signature of
        httplib2.Http.request, used to make the revoke request.
    """
    self._do_revoke(http_request, self.refresh_token)

  def _do_revoke(self, http_request, token):
    """Revokes the credentials and deletes the store if available.

    Args:
      http_request: callable, a callable that matches the method signature of
        httplib2.Http.request, used to make the refresh request.
      token: A string used as the token to be revoked. Can be either an
        access_token or refresh_token.

    Raises:
      TokenRevokeError: If the revoke request does not return with a 200 OK.
    """
    logger.info('Revoking token')
    query_params = {'token': token}
    token_revoke_uri = _update_query_params(self.revoke_uri, query_params)
    resp, content = http_request(token_revoke_uri)
    if resp.status == 200:
      self.invalid = True
    else:
      error_msg = 'Invalid response %s.' % resp.status
      try:
        d = simplejson.loads(content)
        if 'error' in d:
          error_msg = d['error']
      except StandardError:
        pass
      raise TokenRevokeError(error_msg)

    if self.store:
      self.store.delete()


class AccessTokenCredentials(OAuth2Credentials):
  """Credentials object for OAuth 2.0.

  Credentials can be applied to an httplib2.Http object using the
  authorize() method, which then signs each request from that object
  with the OAuth 2.0 access token. This set of credentials is for the
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

  def __init__(self, access_token, user_agent, revoke_uri=None):
    """Create an instance of OAuth2Credentials

    This is one of the few types if Credentials that you should contrust,
    Credentials objects are usually instantiated by a Flow.

    Args:
      access_token: string, access token.
      user_agent: string, The HTTP User-Agent to provide for this application.
      revoke_uri: string, URI for revoke endpoint. Defaults to None; a token
        can't be revoked if this is None.
    """
    super(AccessTokenCredentials, self).__init__(
        access_token,
        None,
        None,
        None,
        None,
        None,
        user_agent,
        revoke_uri=revoke_uri)


  @classmethod
  def from_json(cls, s):
    data = simplejson.loads(s)
    retval = AccessTokenCredentials(
        data['access_token'],
        data['user_agent'])
    return retval

  def _refresh(self, http_request):
    raise AccessTokenCredentialsError(
        'The access_token is expired or invalid and can\'t be refreshed.')

  def _revoke(self, http_request):
    """Revokes the access_token and deletes the store if available.

    Args:
      http_request: callable, a callable that matches the method signature of
        httplib2.Http.request, used to make the revoke request.
    """
    self._do_revoke(http_request, self.access_token)


class AssertionCredentials(OAuth2Credentials):
  """Abstract Credentials object used for OAuth 2.0 assertion grants.

  This credential does not require a flow to instantiate because it
  represents a two legged flow, and therefore has all of the required
  information to generate and refresh its own access tokens. It must
  be subclassed to generate the appropriate assertion string.

  AssertionCredentials objects may be safely pickled and unpickled.
  """

  @util.positional(2)
  def __init__(self, assertion_type, user_agent=None,
               token_uri=GOOGLE_TOKEN_URI,
               revoke_uri=GOOGLE_REVOKE_URI,
               **unused_kwargs):
    """Constructor for AssertionFlowCredentials.

    Args:
      assertion_type: string, assertion type that will be declared to the auth
        server
      user_agent: string, The HTTP User-Agent to provide for this application.
      token_uri: string, URI for token endpoint. For convenience
        defaults to Google's endpoints but any OAuth 2.0 provider can be used.
      revoke_uri: string, URI for revoke endpoint.
    """
    super(AssertionCredentials, self).__init__(
        None,
        None,
        None,
        None,
        None,
        token_uri,
        user_agent,
        revoke_uri=revoke_uri)
    self.assertion_type = assertion_type

  def _generate_refresh_request_body(self):
    assertion = self._generate_assertion()

    body = urllib.urlencode({
        'assertion': assertion,
        'grant_type': 'urn:ietf:params:oauth:grant-type:jwt-bearer',
        })

    return body

  def _generate_assertion(self):
    """Generate the assertion string that will be used in the access token
    request.
    """
    _abstract()

  def _revoke(self, http_request):
    """Revokes the access_token and deletes the store if available.

    Args:
      http_request: callable, a callable that matches the method signature of
        httplib2.Http.request, used to make the revoke request.
    """
    self._do_revoke(http_request, self.access_token)


if HAS_CRYPTO:
  # PyOpenSSL and PyCrypto are not prerequisites for oauth2client, so if it is
  # missing then don't create the SignedJwtAssertionCredentials or the
  # verify_id_token() method.

  class SignedJwtAssertionCredentials(AssertionCredentials):
    """Credentials object used for OAuth 2.0 Signed JWT assertion grants.

    This credential does not require a flow to instantiate because it represents
    a two legged flow, and therefore has all of the required information to
    generate and refresh its own access tokens.

    SignedJwtAssertionCredentials requires either PyOpenSSL, or PyCrypto 2.6 or
    later. For App Engine you may also consider using AppAssertionCredentials.
    """

    MAX_TOKEN_LIFETIME_SECS = 3600 # 1 hour in seconds

    @util.positional(4)
    def __init__(self,
        service_account_name,
        private_key,
        scope,
        private_key_password='notasecret',
        user_agent=None,
        token_uri=GOOGLE_TOKEN_URI,
        revoke_uri=GOOGLE_REVOKE_URI,
        **kwargs):
      """Constructor for SignedJwtAssertionCredentials.

      Args:
        service_account_name: string, id for account, usually an email address.
        private_key: string, private key in PKCS12 or PEM format.
        scope: string or iterable of strings, scope(s) of the credentials being
          requested.
        private_key_password: string, password for private_key, unused if
          private_key is in PEM format.
        user_agent: string, HTTP User-Agent to provide for this application.
        token_uri: string, URI for token endpoint. For convenience
          defaults to Google's endpoints but any OAuth 2.0 provider can be used.
        revoke_uri: string, URI for revoke endpoint.
        kwargs: kwargs, Additional parameters to add to the JWT token, for
          example prn=joe@xample.org."""

      super(SignedJwtAssertionCredentials, self).__init__(
          None,
          user_agent=user_agent,
          token_uri=token_uri,
          revoke_uri=revoke_uri,
          )

      self.scope = util.scopes_to_string(scope)

      # Keep base64 encoded so it can be stored in JSON.
      self.private_key = base64.b64encode(private_key)

      self.private_key_password = private_key_password
      self.service_account_name = service_account_name
      self.kwargs = kwargs

    @classmethod
    def from_json(cls, s):
      data = simplejson.loads(s)
      retval = SignedJwtAssertionCredentials(
          data['service_account_name'],
          base64.b64decode(data['private_key']),
          data['scope'],
          private_key_password=data['private_key_password'],
          user_agent=data['user_agent'],
          token_uri=data['token_uri'],
          **data['kwargs']
          )
      retval.invalid = data['invalid']
      retval.access_token = data['access_token']
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
      logger.debug(str(payload))

      private_key = base64.b64decode(self.private_key)
      return crypt.make_signed_jwt(crypt.Signer.from_string(
          private_key, self.private_key_password), payload)

  # Only used in verify_id_token(), which is always calling to the same URI
  # for the certs.
  _cached_http = httplib2.Http(MemoryCache())

  @util.positional(2)
  def verify_id_token(id_token, audience, http=None,
      cert_uri=ID_TOKEN_VERIFICATON_CERTS):
    """Verifies a signed JWT id_token.

    This function requires PyOpenSSL and because of that it does not work on
    App Engine.

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
      return crypt.verify_signed_jwt_with_certs(id_token, certs, audience)
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


def _parse_exchange_token_response(content):
  """Parses response of an exchange token request.

  Most providers return JSON but some (e.g. Facebook) return a
  url-encoded string.

  Args:
    content: The body of a response

  Returns:
    Content as a dictionary object. Note that the dict could be empty,
    i.e. {}. That basically indicates a failure.
  """
  resp = {}
  try:
    resp = simplejson.loads(content)
  except StandardError:
    # different JSON libs raise different exceptions,
    # so we just do a catch-all here
    resp = dict(parse_qsl(content))

  # some providers respond with 'expires', others with 'expires_in'
  if resp and 'expires' in resp:
    resp['expires_in'] = resp.pop('expires')

  return resp


@util.positional(4)
def credentials_from_code(client_id, client_secret, scope, code,
                          redirect_uri='postmessage', http=None,
                          user_agent=None, token_uri=GOOGLE_TOKEN_URI,
                          auth_uri=GOOGLE_AUTH_URI,
                          revoke_uri=GOOGLE_REVOKE_URI):
  """Exchanges an authorization code for an OAuth2Credentials object.

  Args:
    client_id: string, client identifier.
    client_secret: string, client secret.
    scope: string or iterable of strings, scope(s) to request.
    code: string, An authroization code, most likely passed down from
      the client
    redirect_uri: string, this is generally set to 'postmessage' to match the
      redirect_uri that the client specified
    http: httplib2.Http, optional http instance to use to do the fetch
    token_uri: string, URI for token endpoint. For convenience
      defaults to Google's endpoints but any OAuth 2.0 provider can be used.
    auth_uri: string, URI for authorization endpoint. For convenience
      defaults to Google's endpoints but any OAuth 2.0 provider can be used.
    revoke_uri: string, URI for revoke endpoint. For convenience
      defaults to Google's endpoints but any OAuth 2.0 provider can be used.

  Returns:
    An OAuth2Credentials object.

  Raises:
    FlowExchangeError if the authorization code cannot be exchanged for an
     access token
  """
  flow = OAuth2WebServerFlow(client_id, client_secret, scope,
                             redirect_uri=redirect_uri, user_agent=user_agent,
                             auth_uri=auth_uri, token_uri=token_uri,
                             revoke_uri=revoke_uri)

  credentials = flow.step2_exchange(code, http=http)
  return credentials


@util.positional(3)
def credentials_from_clientsecrets_and_code(filename, scope, code,
                                            message = None,
                                            redirect_uri='postmessage',
                                            http=None,
                                            cache=None):
  """Returns OAuth2Credentials from a clientsecrets file and an auth code.

  Will create the right kind of Flow based on the contents of the clientsecrets
  file or will raise InvalidClientSecretsError for unknown types of Flows.

  Args:
    filename: string, File name of clientsecrets.
    scope: string or iterable of strings, scope(s) to request.
    code: string, An authorization code, most likely passed down from
      the client
    message: string, A friendly string to display to the user if the
      clientsecrets file is missing or invalid. If message is provided then
      sys.exit will be called in the case of an error. If message in not
      provided then clientsecrets.InvalidClientSecretsError will be raised.
    redirect_uri: string, this is generally set to 'postmessage' to match the
      redirect_uri that the client specified
    http: httplib2.Http, optional http instance to use to do the fetch
    cache: An optional cache service client that implements get() and set()
      methods. See clientsecrets.loadfile() for details.

  Returns:
    An OAuth2Credentials object.

  Raises:
    FlowExchangeError if the authorization code cannot be exchanged for an
     access token
    UnknownClientSecretsFlowError if the file describes an unknown kind of Flow.
    clientsecrets.InvalidClientSecretsError if the clientsecrets file is
      invalid.
  """
  flow = flow_from_clientsecrets(filename, scope, message=message, cache=cache,
                                 redirect_uri=redirect_uri)
  credentials = flow.step2_exchange(code, http=http)
  return credentials


class OAuth2WebServerFlow(Flow):
  """Does the Web Server Flow for OAuth 2.0.

  OAuth2WebServerFlow objects may be safely pickled and unpickled.
  """

  @util.positional(4)
  def __init__(self, client_id, client_secret, scope,
               redirect_uri=None,
               user_agent=None,
               auth_uri=GOOGLE_AUTH_URI,
               token_uri=GOOGLE_TOKEN_URI,
               revoke_uri=GOOGLE_REVOKE_URI,
               **kwargs):
    """Constructor for OAuth2WebServerFlow.

    The kwargs argument is used to set extra query parameters on the
    auth_uri. For example, the access_type and approval_prompt
    query parameters can be set via kwargs.

    Args:
      client_id: string, client identifier.
      client_secret: string client secret.
      scope: string or iterable of strings, scope(s) of the credentials being
        requested.
      redirect_uri: string, Either the string 'urn:ietf:wg:oauth:2.0:oob' for
        a non-web-based application, or a URI that handles the callback from
        the authorization server.
      user_agent: string, HTTP User-Agent to provide for this application.
      auth_uri: string, URI for authorization endpoint. For convenience
        defaults to Google's endpoints but any OAuth 2.0 provider can be used.
      token_uri: string, URI for token endpoint. For convenience
        defaults to Google's endpoints but any OAuth 2.0 provider can be used.
      revoke_uri: string, URI for revoke endpoint. For convenience
        defaults to Google's endpoints but any OAuth 2.0 provider can be used.
      **kwargs: dict, The keyword arguments are all optional and required
                        parameters for the OAuth calls.
    """
    self.client_id = client_id
    self.client_secret = client_secret
    self.scope = util.scopes_to_string(scope)
    self.redirect_uri = redirect_uri
    self.user_agent = user_agent
    self.auth_uri = auth_uri
    self.token_uri = token_uri
    self.revoke_uri = revoke_uri
    self.params = {
        'access_type': 'offline',
        'response_type': 'code',
    }
    self.params.update(kwargs)

  @util.positional(1)
  def step1_get_authorize_url(self, redirect_uri=None):
    """Returns a URI to redirect to the provider.

    Args:
      redirect_uri: string, Either the string 'urn:ietf:wg:oauth:2.0:oob' for
        a non-web-based application, or a URI that handles the callback from
        the authorization server. This parameter is deprecated, please move to
        passing the redirect_uri in via the constructor.

    Returns:
      A URI as a string to redirect the user to begin the authorization flow.
    """
    if redirect_uri is not None:
      logger.warning(('The redirect_uri parameter for'
          'OAuth2WebServerFlow.step1_get_authorize_url is deprecated. Please'
          'move to passing the redirect_uri in via the constructor.'))
      self.redirect_uri = redirect_uri

    if self.redirect_uri is None:
      raise ValueError('The value of redirect_uri must not be None.')

    query_params = {
        'client_id': self.client_id,
        'redirect_uri': self.redirect_uri,
        'scope': self.scope,
    }
    query_params.update(self.params)
    return _update_query_params(self.auth_uri, query_params)

  @util.positional(2)
  def step2_exchange(self, code, http=None):
    """Exhanges a code for OAuth2Credentials.

    Args:
      code: string or dict, either the code as a string, or a dictionary
        of the query parameters to the redirect_uri, which contains
        the code.
      http: httplib2.Http, optional http instance to use to do the fetch

    Returns:
      An OAuth2Credentials object that can be used to authorize requests.

    Raises:
      FlowExchangeError if a problem occured exchanging the code for a
      refresh_token.
    """

    if not (isinstance(code, str) or isinstance(code, unicode)):
      if 'code' not in code:
        if 'error' in code:
          error_msg = code['error']
        else:
          error_msg = 'No code was supplied in the query parameters.'
        raise FlowExchangeError(error_msg)
      else:
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
    d = _parse_exchange_token_response(content)
    if resp.status == 200 and 'access_token' in d:
      access_token = d['access_token']
      refresh_token = d.get('refresh_token', None)
      token_expiry = None
      if 'expires_in' in d:
        token_expiry = datetime.datetime.utcnow() + datetime.timedelta(
            seconds=int(d['expires_in']))

      if 'id_token' in d:
        d['id_token'] = _extract_id_token(d['id_token'])

      logger.info('Successfully retrieved access token')
      return OAuth2Credentials(access_token, self.client_id,
                               self.client_secret, refresh_token, token_expiry,
                               self.token_uri, self.user_agent,
                               revoke_uri=self.revoke_uri,
                               id_token=d.get('id_token', None),
                               token_response=d)
    else:
      logger.info('Failed to retrieve access token: %s' % content)
      if 'error' in d:
        # you never know what those providers got to say
        error_msg = unicode(d['error'])
      else:
        error_msg = 'Invalid response: %s.' % str(resp.status)
      raise FlowExchangeError(error_msg)


@util.positional(2)
def flow_from_clientsecrets(filename, scope, redirect_uri=None,
                            message=None, cache=None):
  """Create a Flow from a clientsecrets file.

  Will create the right kind of Flow based on the contents of the clientsecrets
  file or will raise InvalidClientSecretsError for unknown types of Flows.

  Args:
    filename: string, File name of client secrets.
    scope: string or iterable of strings, scope(s) to request.
    redirect_uri: string, Either the string 'urn:ietf:wg:oauth:2.0:oob' for
      a non-web-based application, or a URI that handles the callback from
      the authorization server.
    message: string, A friendly string to display to the user if the
      clientsecrets file is missing or invalid. If message is provided then
      sys.exit will be called in the case of an error. If message in not
      provided then clientsecrets.InvalidClientSecretsError will be raised.
    cache: An optional cache service client that implements get() and set()
      methods. See clientsecrets.loadfile() for details.

  Returns:
    A Flow object.

  Raises:
    UnknownClientSecretsFlowError if the file describes an unknown kind of Flow.
    clientsecrets.InvalidClientSecretsError if the clientsecrets file is
      invalid.
  """
  try:
    client_type, client_info = clientsecrets.loadfile(filename, cache=cache)
    if client_type in (clientsecrets.TYPE_WEB, clientsecrets.TYPE_INSTALLED):
      constructor_kwargs = {
          'redirect_uri': redirect_uri,
          'auth_uri': client_info['auth_uri'],
          'token_uri': client_info['token_uri'],
      }
      revoke_uri = client_info.get('revoke_uri')
      if revoke_uri is not None:
        constructor_kwargs['revoke_uri'] = revoke_uri
      return OAuth2WebServerFlow(
          client_info['client_id'], client_info['client_secret'],
          scope, **constructor_kwargs)

  except clientsecrets.InvalidClientSecretsError:
    if message:
      sys.exit(message)
    else:
      raise
  else:
    raise UnknownClientSecretsFlowError(
        'This OAuth 2.0 flow is unsupported: %r' % client_type)

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
            'token_uri',
        ],
        'string': [
            'client_id',
            'client_secret',
        ],
    },
    TYPE_INSTALLED: {
        'required': [
            'client_id',
            'client_secret',
            'redirect_uris',
            'auth_uri',
            'token_uri',
        ],
        'string': [
            'client_id',
            'client_secret',
        ],
    },
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


def _loadfile(filename):
  try:
    fp = file(filename, 'r')
    try:
      obj = simplejson.load(fp)
    finally:
      fp.close()
  except IOError:
    raise InvalidClientSecretsError('File not found: "%s"' % filename)
  return _validate_clientsecrets(obj)


def loadfile(filename, cache=None):
  """Loading of client_secrets JSON file, optionally backed by a cache.

  Typical cache storage would be App Engine memcache service,
  but you can pass in any other cache client that implements
  these methods:
    - get(key, namespace=ns)
    - set(key, value, namespace=ns)

  Usage:
    # without caching
    client_type, client_info = loadfile('secrets.json')
    # using App Engine memcache service
    from google.appengine.api import memcache
    client_type, client_info = loadfile('secrets.json', cache=memcache)

  Args:
    filename: string, Path to a client_secrets.json file on a filesystem.
    cache: An optional cache service client that implements get() and set()
      methods. If not specified, the file is always being loaded from
      a filesystem.

  Raises:
    InvalidClientSecretsError: In case of a validation error or some
      I/O failure. Can happen only on cache miss.

  Returns:
    (client_type, client_info) tuple, as _loadfile() normally would.
    JSON contents is validated only during first load. Cache hits are not
    validated.
  """
  _SECRET_NAMESPACE = 'oauth2client:secrets#ns'

  if not cache:
    return _loadfile(filename)

  obj = cache.get(filename, namespace=_SECRET_NAMESPACE)
  if obj is None:
    client_type, client_info = _loadfile(filename)
    obj = {client_type: client_info}
    cache.set(filename, obj, namespace=_SECRET_NAMESPACE)

  return obj.iteritems().next()

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

from anyjson import simplejson


CLOCK_SKEW_SECS = 300  # 5 minutes in seconds
AUTH_TOKEN_LIFETIME_SECS = 300  # 5 minutes in seconds
MAX_TOKEN_LIFETIME_SECS = 86400  # 1 day in seconds


logger = logging.getLogger(__name__)


class AppIdentityError(Exception):
  pass


try:
  from OpenSSL import crypto


  class OpenSSLVerifier(object):
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
        True if message was signed by the private key associated with the public
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
      return OpenSSLVerifier(pubkey)


  class OpenSSLSigner(object):
    """Signs messages with a private key."""

    def __init__(self, pkey):
      """Constructor.

      Args:
        pkey, OpenSSL.crypto.PKey (or equiv), The private key to sign with.
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
        key: string, private key in PKCS12 or PEM format.
        password: string, password for the private key file.

      Returns:
        Signer instance.

      Raises:
        OpenSSL.crypto.Error if the key can't be parsed.
      """
      if key.startswith('-----BEGIN '):
        pkey = crypto.load_privatekey(crypto.FILETYPE_PEM, key)
      else:
        pkey = crypto.load_pkcs12(key, password).get_privatekey()
      return OpenSSLSigner(pkey)

except ImportError:
  OpenSSLVerifier = None
  OpenSSLSigner = None


try:
  from Crypto.PublicKey import RSA
  from Crypto.Hash import SHA256
  from Crypto.Signature import PKCS1_v1_5


  class PyCryptoVerifier(object):
    """Verifies the signature on a message."""

    def __init__(self, pubkey):
      """Constructor.

      Args:
        pubkey, OpenSSL.crypto.PKey (or equiv), The public key to verify with.
      """
      self._pubkey = pubkey

    def verify(self, message, signature):
      """Verifies a message against a signature.

      Args:
        message: string, The message to verify.
        signature: string, The signature on the message.

      Returns:
        True if message was signed by the private key associated with the public
        key that this object was constructed with.
      """
      try:
        return PKCS1_v1_5.new(self._pubkey).verify(
            SHA256.new(message), signature)
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
        NotImplementedError if is_x509_cert is true.
      """
      if is_x509_cert:
        raise NotImplementedError(
            'X509 certs are not supported by the PyCrypto library. '
            'Try using PyOpenSSL if native code is an option.')
      else:
        pubkey = RSA.importKey(key_pem)
      return PyCryptoVerifier(pubkey)


  class PyCryptoSigner(object):
    """Signs messages with a private key."""

    def __init__(self, pkey):
      """Constructor.

      Args:
        pkey, OpenSSL.crypto.PKey (or equiv), The private key to sign with.
      """
      self._key = pkey

    def sign(self, message):
      """Signs a message.

      Args:
        message: string, Message to be signed.

      Returns:
        string, The signature of the message for the given key.
      """
      return PKCS1_v1_5.new(self._key).sign(SHA256.new(message))

    @staticmethod
    def from_string(key, password='notasecret'):
      """Construct a Signer instance from a string.

      Args:
        key: string, private key in PEM format.
        password: string, password for private key file. Unused for PEM files.

      Returns:
        Signer instance.

      Raises:
        NotImplementedError if they key isn't in PEM format.
      """
      if key.startswith('-----BEGIN '):
        pkey = RSA.importKey(key)
      else:
        raise NotImplementedError(
            'PKCS12 format is not supported by the PyCrpto library. '
            'Try converting to a "PEM" '
            '(openssl pkcs12 -in xxxxx.p12 -nodes -nocerts > privatekey.pem) '
            'or using PyOpenSSL if native code is an option.')
      return PyCryptoSigner(pkey)

except ImportError:
  PyCryptoVerifier = None
  PyCryptoSigner = None


if OpenSSLSigner:
  Signer = OpenSSLSigner
  Verifier = OpenSSLVerifier
elif PyCryptoSigner:
  Signer = PyCryptoSigner
  Verifier = PyCryptoVerifier
else:
  raise ImportError('No encryption library found. Please install either '
                    'PyOpenSSL, or PyCrypto 2.6 or later')


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

  logger.debug(str(segments))

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

  def __init__(self, *args, **kwargs):
    if 'null' not in kwargs:
      kwargs['null'] = True
    super(CredentialsField, self).__init__(*args, **kwargs)

  def get_internal_type(self):
    return "TextField"

  def to_python(self, value):
    if value is None:
      return None
    if isinstance(value, oauth2client.client.Credentials):
      return value
    return pickle.loads(base64.b64decode(value))

  def get_db_prep_value(self, value, connection, prepared=False):
    if value is None:
      return None
    return base64.b64encode(pickle.dumps(value))


class FlowField(models.Field):

  __metaclass__ = models.SubfieldBase

  def __init__(self, *args, **kwargs):
    if 'null' not in kwargs:
      kwargs['null'] = True
    super(FlowField, self).__init__(*args, **kwargs)

  def get_internal_type(self):
    return "TextField"

  def to_python(self, value):
    if value is None:
      return None
    if isinstance(value, oauth2client.client.Flow):
      return value
    return pickle.loads(base64.b64decode(value))

  def get_db_prep_value(self, value, connection, prepared=False):
    if value is None:
      return None
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


class CredentialsFileSymbolicLinkError(Exception):
  """Credentials files must not be symbolic links."""


class Storage(BaseStorage):
  """Store and retrieve a single credential to and from a file."""

  def __init__(self, filename):
    self._filename = filename
    self._lock = threading.Lock()

  def _validate_file(self):
    if os.path.islink(self._filename):
      raise CredentialsFileSymbolicLinkError(
          'File: %s is a symbolic link.' % self._filename)

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

    Raises:
      CredentialsFileSymbolicLinkError if the file is a symbolic link.
    """
    credentials = None
    self._validate_file()
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

    Raises:
      CredentialsFileSymbolicLinkError if the file is a symbolic link.
    """

    self._create_file_if_needed()
    self._validate_file()
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
__FILENAME__ = gce
# Copyright (C) 2012 Google Inc.
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

"""Utilities for Google Compute Engine

Utilities for making it easier to use OAuth 2.0 on Google Compute Engine.
"""

__author__ = 'jcgregorio@google.com (Joe Gregorio)'

import httplib2
import logging
import uritemplate

from oauth2client import util
from oauth2client.anyjson import simplejson
from oauth2client.client import AccessTokenRefreshError
from oauth2client.client import AssertionCredentials

logger = logging.getLogger(__name__)

# URI Template for the endpoint that returns access_tokens.
META = ('http://metadata.google.internal/0.1/meta-data/service-accounts/'
        'default/acquire{?scope}')


class AppAssertionCredentials(AssertionCredentials):
  """Credentials object for Compute Engine Assertion Grants

  This object will allow a Compute Engine instance to identify itself to
  Google and other OAuth 2.0 servers that can verify assertions. It can be used
  for the purpose of accessing data stored under an account assigned to the
  Compute Engine instance itself.

  This credential does not require a flow to instantiate because it represents
  a two legged flow, and therefore has all of the required information to
  generate and refresh its own access tokens.
  """

  @util.positional(2)
  def __init__(self, scope, **kwargs):
    """Constructor for AppAssertionCredentials

    Args:
      scope: string or iterable of strings, scope(s) of the credentials being
        requested.
    """
    self.scope = util.scopes_to_string(scope)

    # Assertion type is no longer used, but still in the parent class signature.
    super(AppAssertionCredentials, self).__init__(None)

  @classmethod
  def from_json(cls, json):
    data = simplejson.loads(json)
    return AppAssertionCredentials(data['scope'])

  def _refresh(self, http_request):
    """Refreshes the access_token.

    Skip all the storage hoops and just refresh using the API.

    Args:
      http_request: callable, a callable that matches the method signature of
        httplib2.Http.request, used to make the refresh request.

    Raises:
      AccessTokenRefreshError: When the refresh fails.
    """
    uri = uritemplate.expand(META, {'scope': self.scope})
    response, content = http_request(uri)
    if response.status == 200:
      try:
        d = simplejson.loads(content)
      except StandardError, e:
        raise AccessTokenRefreshError(str(e))
      self.access_token = d['accessToken']
    else:
      raise AccessTokenRefreshError(content)

########NEW FILE########
__FILENAME__ = keyring_storage
# Copyright (C) 2012 Google Inc.
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

"""A keyring based Storage.

A Storage for Credentials that uses the keyring module.
"""

__author__ = 'jcgregorio@google.com (Joe Gregorio)'

import keyring
import threading

from client import Storage as BaseStorage
from client import Credentials


class Storage(BaseStorage):
  """Store and retrieve a single credential to and from the keyring.

  To use this module you must have the keyring module installed. See
  <http://pypi.python.org/pypi/keyring/>. This is an optional module and is not
  installed with oauth2client by default because it does not work on all the
  platforms that oauth2client supports, such as Google App Engine.

  The keyring module <http://pypi.python.org/pypi/keyring/> is a cross-platform
  library for access the keyring capabilities of the local system. The user will
  be prompted for their keyring password when this module is used, and the
  manner in which the user is prompted will vary per platform.

  Usage:
    from oauth2client.keyring_storage import Storage

    s = Storage('name_of_application', 'user1')
    credentials = s.get()

  """

  def __init__(self, service_name, user_name):
    """Constructor.

    Args:
      service_name: string, The name of the service under which the credentials
        are stored.
      user_name: string, The name of the user to store credentials for.
    """
    self._service_name = service_name
    self._user_name = user_name
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
    content = keyring.get_password(self._service_name, self._user_name)

    if content is not None:
      try:
        credentials = Credentials.new_from_json(content)
        credentials.set_store(self)
      except ValueError:
        pass

    return credentials

  def locked_put(self, credentials):
    """Write Credentials to file.

    Args:
      credentials: Credentials, the credentials to store.
    """
    keyring.set_password(self._service_name, self._user_name,
                         credentials.to_json())

  def locked_delete(self):
    """Delete Credentials file.

    Args:
      credentials: Credentials, the credentials to store.
    """
    keyring.set_password(self._service_name, self._user_name, '')

########NEW FILE########
__FILENAME__ = locked_file
# Copyright 2011 Google Inc. All Rights Reserved.

"""Locked file interface that should work on Unix and Windows pythons.

This module first tries to use fcntl locking to ensure serialized access
to a file, then falls back on a lock file if that is unavialable.

Usage:
    f = LockedFile('filename', 'r+b', 'rb')
    f.open_and_lock()
    if f.is_locked():
      print 'Acquired filename with r+b mode'
      f.file_handle().write('locked data')
    else:
      print 'Aquired filename with rb mode'
    f.unlock_and_close()
"""

__author__ = 'cache@google.com (David T McWherter)'

import errno
import logging
import os
import time

from oauth2client import util

logger = logging.getLogger(__name__)


class CredentialsFileSymbolicLinkError(Exception):
  """Credentials files must not be symbolic links."""


class AlreadyLockedException(Exception):
  """Trying to lock a file that has already been locked by the LockedFile."""
  pass


def validate_file(filename):
  if os.path.islink(filename):
    raise CredentialsFileSymbolicLinkError(
        'File: %s is a symbolic link.' % filename)

class _Opener(object):
  """Base class for different locking primitives."""

  def __init__(self, filename, mode, fallback_mode):
    """Create an Opener.

    Args:
      filename: string, The pathname of the file.
      mode: string, The preferred mode to access the file with.
      fallback_mode: string, The mode to use if locking fails.
    """
    self._locked = False
    self._filename = filename
    self._mode = mode
    self._fallback_mode = fallback_mode
    self._fh = None

  def is_locked(self):
    """Was the file locked."""
    return self._locked

  def file_handle(self):
    """The file handle to the file. Valid only after opened."""
    return self._fh

  def filename(self):
    """The filename that is being locked."""
    return self._filename

  def open_and_lock(self, timeout, delay):
    """Open the file and lock it.

    Args:
      timeout: float, How long to try to lock for.
      delay: float, How long to wait between retries.
    """
    pass

  def unlock_and_close(self):
    """Unlock and close the file."""
    pass


class _PosixOpener(_Opener):
  """Lock files using Posix advisory lock files."""

  def open_and_lock(self, timeout, delay):
    """Open the file and lock it.

    Tries to create a .lock file next to the file we're trying to open.

    Args:
      timeout: float, How long to try to lock for.
      delay: float, How long to wait between retries.

    Raises:
      AlreadyLockedException: if the lock is already acquired.
      IOError: if the open fails.
      CredentialsFileSymbolicLinkError if the file is a symbolic link.
    """
    if self._locked:
      raise AlreadyLockedException('File %s is already locked' %
                                   self._filename)
    self._locked = False

    validate_file(self._filename)
    try:
      self._fh = open(self._filename, self._mode)
    except IOError, e:
      # If we can't access with _mode, try _fallback_mode and don't lock.
      if e.errno == errno.EACCES:
        self._fh = open(self._filename, self._fallback_mode)
        return

    lock_filename = self._posix_lockfile(self._filename)
    start_time = time.time()
    while True:
      try:
        self._lock_fd = os.open(lock_filename,
                                os.O_CREAT|os.O_EXCL|os.O_RDWR)
        self._locked = True
        break

      except OSError, e:
        if e.errno != errno.EEXIST:
          raise
        if (time.time() - start_time) >= timeout:
          logger.warn('Could not acquire lock %s in %s seconds' % (
              lock_filename, timeout))
          # Close the file and open in fallback_mode.
          if self._fh:
            self._fh.close()
          self._fh = open(self._filename, self._fallback_mode)
          return
        time.sleep(delay)

  def unlock_and_close(self):
    """Unlock a file by removing the .lock file, and close the handle."""
    if self._locked:
      lock_filename = self._posix_lockfile(self._filename)
      os.close(self._lock_fd)
      os.unlink(lock_filename)
      self._locked = False
      self._lock_fd = None
    if self._fh:
      self._fh.close()

  def _posix_lockfile(self, filename):
    """The name of the lock file to use for posix locking."""
    return '%s.lock' % filename


try:
  import fcntl

  class _FcntlOpener(_Opener):
    """Open, lock, and unlock a file using fcntl.lockf."""

    def open_and_lock(self, timeout, delay):
      """Open the file and lock it.

      Args:
        timeout: float, How long to try to lock for.
        delay: float, How long to wait between retries

      Raises:
        AlreadyLockedException: if the lock is already acquired.
        IOError: if the open fails.
        CredentialsFileSymbolicLinkError if the file is a symbolic link.
      """
      if self._locked:
        raise AlreadyLockedException('File %s is already locked' %
                                     self._filename)
      start_time = time.time()

      validate_file(self._filename)
      try:
        self._fh = open(self._filename, self._mode)
      except IOError, e:
        # If we can't access with _mode, try _fallback_mode and don't lock.
        if e.errno == errno.EACCES:
          self._fh = open(self._filename, self._fallback_mode)
          return

      # We opened in _mode, try to lock the file.
      while True:
        try:
          fcntl.lockf(self._fh.fileno(), fcntl.LOCK_EX)
          self._locked = True
          return
        except IOError, e:
          # If not retrying, then just pass on the error.
          if timeout == 0:
            raise e
          if e.errno != errno.EACCES:
            raise e
          # We could not acquire the lock. Try again.
          if (time.time() - start_time) >= timeout:
            logger.warn('Could not lock %s in %s seconds' % (
                self._filename, timeout))
            if self._fh:
              self._fh.close()
            self._fh = open(self._filename, self._fallback_mode)
            return
          time.sleep(delay)

    def unlock_and_close(self):
      """Close and unlock the file using the fcntl.lockf primitive."""
      if self._locked:
        fcntl.lockf(self._fh.fileno(), fcntl.LOCK_UN)
      self._locked = False
      if self._fh:
        self._fh.close()
except ImportError:
  _FcntlOpener = None


try:
  import pywintypes
  import win32con
  import win32file

  class _Win32Opener(_Opener):
    """Open, lock, and unlock a file using windows primitives."""

    # Error #33:
    #  'The process cannot access the file because another process'
    FILE_IN_USE_ERROR = 33

    # Error #158:
    #  'The segment is already unlocked.'
    FILE_ALREADY_UNLOCKED_ERROR = 158

    def open_and_lock(self, timeout, delay):
      """Open the file and lock it.

      Args:
        timeout: float, How long to try to lock for.
        delay: float, How long to wait between retries

      Raises:
        AlreadyLockedException: if the lock is already acquired.
        IOError: if the open fails.
        CredentialsFileSymbolicLinkError if the file is a symbolic link.
      """
      if self._locked:
        raise AlreadyLockedException('File %s is already locked' %
                                     self._filename)
      start_time = time.time()

      validate_file(self._filename)
      try:
        self._fh = open(self._filename, self._mode)
      except IOError, e:
        # If we can't access with _mode, try _fallback_mode and don't lock.
        if e.errno == errno.EACCES:
          self._fh = open(self._filename, self._fallback_mode)
          return

      # We opened in _mode, try to lock the file.
      while True:
        try:
          hfile = win32file._get_osfhandle(self._fh.fileno())
          win32file.LockFileEx(
              hfile,
              (win32con.LOCKFILE_FAIL_IMMEDIATELY|
               win32con.LOCKFILE_EXCLUSIVE_LOCK), 0, -0x10000,
              pywintypes.OVERLAPPED())
          self._locked = True
          return
        except pywintypes.error, e:
          if timeout == 0:
            raise e

          # If the error is not that the file is already in use, raise.
          if e[0] != _Win32Opener.FILE_IN_USE_ERROR:
            raise

          # We could not acquire the lock. Try again.
          if (time.time() - start_time) >= timeout:
            logger.warn('Could not lock %s in %s seconds' % (
                self._filename, timeout))
            if self._fh:
              self._fh.close()
            self._fh = open(self._filename, self._fallback_mode)
            return
          time.sleep(delay)

    def unlock_and_close(self):
      """Close and unlock the file using the win32 primitive."""
      if self._locked:
        try:
          hfile = win32file._get_osfhandle(self._fh.fileno())
          win32file.UnlockFileEx(hfile, 0, -0x10000, pywintypes.OVERLAPPED())
        except pywintypes.error, e:
          if e[0] != _Win32Opener.FILE_ALREADY_UNLOCKED_ERROR:
            raise
      self._locked = False
      if self._fh:
        self._fh.close()
except ImportError:
  _Win32Opener = None


class LockedFile(object):
  """Represent a file that has exclusive access."""

  @util.positional(4)
  def __init__(self, filename, mode, fallback_mode, use_native_locking=True):
    """Construct a LockedFile.

    Args:
      filename: string, The path of the file to open.
      mode: string, The mode to try to open the file with.
      fallback_mode: string, The mode to use if locking fails.
      use_native_locking: bool, Whether or not fcntl/win32 locking is used.
    """
    opener = None
    if not opener and use_native_locking:
      if _Win32Opener:
        opener = _Win32Opener(filename, mode, fallback_mode)
      if _FcntlOpener:
        opener = _FcntlOpener(filename, mode, fallback_mode)

    if not opener:
      opener = _PosixOpener(filename, mode, fallback_mode)

    self._opener = opener

  def filename(self):
    """Return the filename we were constructed with."""
    return self._opener._filename

  def file_handle(self):
    """Return the file_handle to the opened file."""
    return self._opener.file_handle()

  def is_locked(self):
    """Return whether we successfully locked the file."""
    return self._opener.is_locked()

  def open_and_lock(self, timeout=0, delay=0.05):
    """Open the file, trying to lock it.

    Args:
      timeout: float, The number of seconds to try to acquire the lock.
      delay: float, The number of seconds to wait between retry attempts.

    Raises:
      AlreadyLockedException: if the lock is already acquired.
      IOError: if the open fails.
    """
    self._opener.open_and_lock(timeout, delay)

  def unlock_and_close(self):
    """Unlock and close a file."""
    self._opener.unlock_and_close()

########NEW FILE########
__FILENAME__ = multistore_file
# Copyright 2011 Google Inc. All Rights Reserved.

"""Multi-credential file store with lock support.

This module implements a JSON credential store where multiple
credentials can be stored in one file. That file supports locking
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
import logging
import os
import threading

from anyjson import simplejson
from oauth2client.client import Storage as BaseStorage
from oauth2client.client import Credentials
from oauth2client import util
from locked_file import LockedFile

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


@util.positional(4)
def get_credential_storage(filename, client_id, user_agent, scope,
                           warn_on_readonly=True):
  """Get a Storage instance for a credential.

  Args:
    filename: The JSON file storing a set of credentials
    client_id: The client_id for the credential
    user_agent: The user agent for the credential
    scope: string or iterable of strings, Scope(s) being requested
    warn_on_readonly: if True, log a warning if the store is readonly

  Returns:
    An object derived from client.Storage for getting/setting the
    credential.
  """
  # Recreate the legacy key with these specific parameters
  key = {'clientId': client_id, 'userAgent': user_agent,
         'scope': util.scopes_to_string(scope)}
  return get_credential_storage_custom_key(
      filename, key, warn_on_readonly=warn_on_readonly)


@util.positional(2)
def get_credential_storage_custom_string_key(
    filename, key_string, warn_on_readonly=True):
  """Get a Storage instance for a credential using a single string as a key.

  Allows you to provide a string as a custom key that will be used for
  credential storage and retrieval.

  Args:
    filename: The JSON file storing a set of credentials
    key_string: A string to use as the key for storing this credential.
    warn_on_readonly: if True, log a warning if the store is readonly

  Returns:
    An object derived from client.Storage for getting/setting the
    credential.
  """
  # Create a key dictionary that can be used
  key_dict = {'key': key_string}
  return get_credential_storage_custom_key(
      filename, key_dict, warn_on_readonly=warn_on_readonly)


@util.positional(2)
def get_credential_storage_custom_key(
    filename, key_dict, warn_on_readonly=True):
  """Get a Storage instance for a credential using a dictionary as a key.

  Allows you to provide a dictionary as a custom key that will be used for
  credential storage and retrieval.

  Args:
    filename: The JSON file storing a set of credentials
    key_dict: A dictionary to use as the key for storing this credential. There
      is no ordering of the keys in the dictionary. Logically equivalent
      dictionaries will produce equivalent storage keys.
    warn_on_readonly: if True, log a warning if the store is readonly

  Returns:
    An object derived from client.Storage for getting/setting the
    credential.
  """
  filename = os.path.expanduser(filename)
  _multistores_lock.acquire()
  try:
    multistore = _multistores.setdefault(
        filename, _MultiStore(filename, warn_on_readonly=warn_on_readonly))
  finally:
    _multistores_lock.release()
  key = util.dict_to_tuple_key(key_dict)
  return multistore._get_storage(key)


class _MultiStore(object):
  """A file backed store for multiple credentials."""

  @util.positional(2)
  def __init__(self, filename, warn_on_readonly=True):
    """Initialize the class.

    This will create the file if necessary.
    """
    self._file = LockedFile(filename, 'r+b', 'rb')
    self._thread_lock = threading.Lock()
    self._read_only = False
    self._warn_on_readonly = warn_on_readonly

    self._create_file_if_needed()

    # Cache of deserialized store. This is only valid after the
    # _MultiStore is locked or _refresh_data_cache is called. This is
    # of the form of:
    #
    # ((key, value), (key, value)...) -> OAuth2Credential
    #
    # If this is None, then the store hasn't been read yet.
    self._data = None

  class _Storage(BaseStorage):
    """A Storage object that knows how to read/write a single credential."""

    def __init__(self, multistore, key):
      self._multistore = multistore
      self._key = key

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
      credential = self._multistore._get_credential(self._key)
      if credential:
        credential.set_store(self)
      return credential

    def locked_put(self, credentials):
      """Write a credential.

      The Storage lock must be held when this is called.

      Args:
        credentials: Credentials, the credentials to store.
      """
      self._multistore._update_credential(self._key, credentials)

    def locked_delete(self):
      """Delete a credential.

      The Storage lock must be held when this is called.

      Args:
        credentials: Credentials, the credentials to store.
      """
      self._multistore._delete_credential(self._key)

  def _create_file_if_needed(self):
    """Create an empty file if necessary.

    This method will not initialize the file. Instead it implements a
    simple version of "touch" to ensure the file has been created.
    """
    if not os.path.exists(self._file.filename()):
      old_umask = os.umask(0177)
      try:
        open(self._file.filename(), 'a+b').close()
      finally:
        os.umask(old_umask)

  def _lock(self):
    """Lock the entire multistore."""
    self._thread_lock.acquire()
    self._file.open_and_lock()
    if not self._file.is_locked():
      self._read_only = True
      if self._warn_on_readonly:
        logger.warn('The credentials file (%s) is not writable. Opening in '
                    'read-only mode. Any refreshed credentials will only be '
                    'valid for this run.' % self._file.filename())
    if os.path.getsize(self._file.filename()) == 0:
      logger.debug('Initializing empty multistore file')
      # The multistore is empty so write out an empty file.
      self._data = {}
      self._write()
    elif not self._read_only or self._data is None:
      # Only refresh the data if we are read/write or we haven't
      # cached the data yet. If we are readonly, we assume is isn't
      # changing out from under us and that we only have to read it
      # once. This prevents us from whacking any new access keys that
      # we have cached in memory but were unable to write out.
      self._refresh_data_cache()

  def _unlock(self):
    """Release the lock on the multistore."""
    self._file.unlock_and_close()
    self._thread_lock.release()

  def _locked_json_read(self):
    """Get the raw content of the multistore file.

    The multistore must be locked when this is called.

    Returns:
      The contents of the multistore decoded as JSON.
    """
    assert self._thread_lock.locked()
    self._file.file_handle().seek(0)
    return simplejson.load(self._file.file_handle())

  def _locked_json_write(self, data):
    """Write a JSON serializable data structure to the multistore.

    The multistore must be locked when this is called.

    Args:
      data: The data to be serialized and written.
    """
    assert self._thread_lock.locked()
    if self._read_only:
      return
    self._file.file_handle().seek(0)
    simplejson.dump(data, self._file.file_handle(), sort_keys=True, indent=2)
    self._file.file_handle().truncate()

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
    key = util.dict_to_tuple_key(raw_key)
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
      raw_key = dict(cred_key)
      raw_cred = simplejson.loads(cred.to_json())
      raw_creds.append({'key': raw_key, 'credential': raw_cred})
    self._locked_json_write(raw_data)

  def _get_credential(self, key):
    """Get a credential from the multistore.

    The multistore must be locked.

    Args:
      key: The key used to retrieve the credential

    Returns:
      The credential specified or None if not present
    """
    return self._data.get(key, None)

  def _update_credential(self, key, cred):
    """Update a credential and write the multistore.

    This must be called when the multistore is locked.

    Args:
      key: The key used to retrieve the credential
      cred: The OAuth2Credential to update/set
    """
    self._data[key] = cred
    self._write()

  def _delete_credential(self, key):
    """Delete a credential and write the multistore.

    This must be called when the multistore is locked.

    Args:
      key: The key used to retrieve the credential
    """
    try:
      del self._data[key]
    except KeyError:
      pass
    self._write()

  def _get_storage(self, key):
    """Get a Storage object to get/set a credential.

    This Storage is a 'view' into the multistore.

    Args:
      key: The key used to retrieve the credential

    Returns:
      A Storage object that can be used to get/set this cred
    """
    return self._Storage(self, key)

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

from oauth2client.client import FlowExchangeError
from oauth2client.client import OOB_CALLBACK_URN
from oauth2client import util

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


@util.positional(2)
def run(flow, storage, http=None):
  """Core code for a command-line application.

  The run() function is called from your application and runs through all the
  steps to obtain credentials. It takes a Flow argument and attempts to open an
  authorization server page in the user's default web browser. The server asks
  the user to grant your application access to the user's data. If the user
  grants access, the run() function returns new credentials. The new credentials
  are also stored in the Storage argument, which updates the file associated
  with the Storage object.

  It presumes it is run from a command-line application and supports the
  following flags:

    --auth_host_name: Host name to use when running a local web server
      to handle redirects during OAuth authorization.
      (default: 'localhost')

    --auth_host_port: Port to use when running a local web server to handle
      redirects during OAuth authorization.;
      repeat this option to specify a list of values
      (default: '[8080, 8090]')
      (an integer)

    --[no]auth_local_webserver: Run a local web server to handle redirects
      during OAuth authorization.
      (default: 'true')

  Since it uses flags make sure to initialize the gflags module before calling
  run().

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
    if not success:
      print 'Failed to start a local webserver listening on either port 8080'
      print 'or port 9090. Please check your firewall settings and locally'
      print 'running programs that may be blocking or using those ports.'
      print
      print 'Falling back to --noauth_local_webserver and continuing with',
      print 'authorization.'
      print

  if FLAGS.auth_local_webserver:
    oauth_callback = 'http://%s:%s/' % (FLAGS.auth_host_name, port_number)
  else:
    oauth_callback = OOB_CALLBACK_URN
  flow.redirect_uri = oauth_callback
  authorize_url = flow.step1_get_authorize_url()

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
    credential = flow.step2_exchange(code, http=http)
  except FlowExchangeError, e:
    sys.exit('Authentication has failed: %s' % e)

  storage.put(credential)
  credential.set_store(storage)
  print 'Authentication successful.'

  return credential

########NEW FILE########
__FILENAME__ = util
#!/usr/bin/env python
#
# Copyright 2010 Google Inc.
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

"""Common utility library."""

__author__ = ['rafek@google.com (Rafe Kaplan)',
              'guido@google.com (Guido van Rossum)',
]
__all__ = [
  'positional',
]

import gflags
import inspect
import logging
import types
import urllib
import urlparse

try:
  from urlparse import parse_qsl
except ImportError:
  from cgi import parse_qsl

logger = logging.getLogger(__name__)

FLAGS = gflags.FLAGS

gflags.DEFINE_enum('positional_parameters_enforcement', 'WARNING',
    ['EXCEPTION', 'WARNING', 'IGNORE'],
    'The action when an oauth2client.util.positional declaration is violated.')


def positional(max_positional_args):
  """A decorator to declare that only the first N arguments my be positional.

  This decorator makes it easy to support Python 3 style key-word only
  parameters. For example, in Python 3 it is possible to write:

    def fn(pos1, *, kwonly1=None, kwonly1=None):
      ...

  All named parameters after * must be a keyword:

    fn(10, 'kw1', 'kw2')  # Raises exception.
    fn(10, kwonly1='kw1')  # Ok.

  Example:
    To define a function like above, do:

      @positional(1)
      def fn(pos1, kwonly1=None, kwonly2=None):
        ...

    If no default value is provided to a keyword argument, it becomes a required
    keyword argument:

      @positional(0)
      def fn(required_kw):
        ...

    This must be called with the keyword parameter:

      fn()  # Raises exception.
      fn(10)  # Raises exception.
      fn(required_kw=10)  # Ok.

    When defining instance or class methods always remember to account for
    'self' and 'cls':

      class MyClass(object):

        @positional(2)
        def my_method(self, pos1, kwonly1=None):
          ...

        @classmethod
        @positional(2)
        def my_method(cls, pos1, kwonly1=None):
          ...

  The positional decorator behavior is controlled by the
  --positional_parameters_enforcement flag. The flag may be set to 'EXCEPTION',
  'WARNING' or 'IGNORE' to raise an exception, log a warning, or do nothing,
  respectively, if a declaration is violated.

  Args:
    max_positional_arguments: Maximum number of positional arguments. All
      parameters after the this index must be keyword only.

  Returns:
    A decorator that prevents using arguments after max_positional_args from
    being used as positional parameters.

  Raises:
    TypeError if a key-word only argument is provided as a positional parameter,
    but only if the --positional_parameters_enforcement flag is set to
    'EXCEPTION'.
  """
  def positional_decorator(wrapped):
    def positional_wrapper(*args, **kwargs):
      if len(args) > max_positional_args:
        plural_s = ''
        if max_positional_args != 1:
          plural_s = 's'
        message = '%s() takes at most %d positional argument%s (%d given)' % (
            wrapped.__name__, max_positional_args, plural_s, len(args))
        if FLAGS.positional_parameters_enforcement == 'EXCEPTION':
          raise TypeError(message)
        elif FLAGS.positional_parameters_enforcement == 'WARNING':
          logger.warning(message)
        else: # IGNORE
          pass
      return wrapped(*args, **kwargs)
    return positional_wrapper

  if isinstance(max_positional_args, (int, long)):
    return positional_decorator
  else:
    args, _, _, defaults = inspect.getargspec(max_positional_args)
    return positional(len(args) - len(defaults))(max_positional_args)


def scopes_to_string(scopes):
  """Converts scope value to a string.

  If scopes is a string then it is simply passed through. If scopes is an
  iterable then a string is returned that is all the individual scopes
  concatenated with spaces.

  Args:
    scopes: string or iterable of strings, the scopes.

  Returns:
    The scopes formatted as a single string.
  """
  if isinstance(scopes, types.StringTypes):
    return scopes
  else:
    return ' '.join(scopes)


def dict_to_tuple_key(dictionary):
  """Converts a dictionary to a tuple that can be used as an immutable key.

  The resulting key is always sorted so that logically equivalent dictionaries
  always produce an identical tuple for a key.

  Args:
    dictionary: the dictionary to use as the key.

  Returns:
    A tuple representing the dictionary in it's naturally sorted ordering.
  """
  return tuple(sorted(dictionary.items()))


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

########NEW FILE########
__FILENAME__ = xsrfutil
#!/usr/bin/python2.5
#
# Copyright 2010 the Melange authors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Helper methods for creating & verifying XSRF tokens."""

__authors__ = [
  '"Doug Coker" <dcoker@google.com>',
  '"Joe Gregorio" <jcgregorio@google.com>',
]


import base64
import hmac
import os  # for urandom
import time

from oauth2client import util


# Delimiter character
DELIMITER = ':'

# 1 hour in seconds
DEFAULT_TIMEOUT_SECS = 1*60*60

@util.positional(2)
def generate_token(key, user_id, action_id="", when=None):
  """Generates a URL-safe token for the given user, action, time tuple.

  Args:
    key: secret key to use.
    user_id: the user ID of the authenticated user.
    action_id: a string identifier of the action they requested
      authorization for.
    when: the time in seconds since the epoch at which the user was
      authorized for this action. If not set the current time is used.

  Returns:
    A string XSRF protection token.
  """
  when = when or int(time.time())
  digester = hmac.new(key)
  digester.update(str(user_id))
  digester.update(DELIMITER)
  digester.update(action_id)
  digester.update(DELIMITER)
  digester.update(str(when))
  digest = digester.digest()

  token = base64.urlsafe_b64encode('%s%s%d' % (digest,
                                               DELIMITER,
                                               when))
  return token


@util.positional(3)
def validate_token(key, token, user_id, action_id="", current_time=None):
  """Validates that the given token authorizes the user for the action.

  Tokens are invalid if the time of issue is too old or if the token
  does not match what generateToken outputs (i.e. the token was forged).

  Args:
    key: secret key to use.
    token: a string of the token generated by generateToken.
    user_id: the user ID of the authenticated user.
    action_id: a string identifier of the action they requested
      authorization for.

  Returns:
    A boolean - True if the user is authorized for the action, False
    otherwise.
  """
  if not token:
    return False
  try:
    decoded = base64.urlsafe_b64decode(str(token))
    token_time = long(decoded.split(DELIMITER)[-1])
  except (TypeError, ValueError):
    return False
  if current_time is None:
    current_time = time.time()
  # If the token is too old it's not valid.
  if current_time - token_time > DEFAULT_TIMEOUT_SECS:
    return False

  # The given token should match the generated one with the same time.
  expected_token = generate_token(key, user_id, action_id=action_id,
                                  when=token_time)
  if len(token) != len(expected_token):
    return False

  # Perform constant time comparison to avoid timing attacks
  different = 0
  for x, y in zip(token, expected_token):
    different |= ord(x) ^ ord(y)
  if different:
    return False

  return True

########NEW FILE########
__FILENAME__ = sessions
import Cookie
import datetime
import time
import email.utils
import calendar
import base64
import hashlib
import hmac
import re
import logging

# Ripped from the Tornado Framework's web.py
# http://github.com/facebook/tornado/commit/39ac6d169a36a54bb1f6b9bf1fdebb5c9da96e09
#
# Tornado is licensed under the Apache Licence, Version 2.0
# (http://www.apache.org/licenses/LICENSE-2.0.html).
#
# Example:
# from vendor.prayls.lilcookies import LilCookies
# cookieutil = LilCookies(self, application_settings['cookie_secret'])
# cookieutil.set_secure_cookie(name = 'mykey', value = 'myvalue', expires_days= 365*100)
# cookieutil.get_secure_cookie(name = 'mykey')
class LilCookies:

  @staticmethod
  def _utf8(s):
    if isinstance(s, unicode):
      return s.encode("utf-8")
    assert isinstance(s, str)
    return s

  @staticmethod
  def _time_independent_equals(a, b):
    if len(a) != len(b):
      return False
    result = 0
    for x, y in zip(a, b):
      result |= ord(x) ^ ord(y)
    return result == 0

  @staticmethod
  def _signature_from_secret(cookie_secret, *parts):
    """ Takes a secret salt value to create a signature for values in the `parts` param."""
    hash = hmac.new(cookie_secret, digestmod=hashlib.sha1)
    for part in parts: hash.update(part)
    return hash.hexdigest()

  @staticmethod
  def _signed_cookie_value(cookie_secret, name, value):
    """ Returns a signed value for use in a cookie.

    This is helpful to have in its own method if you need to re-use this function for other needs. """
    timestamp = str(int(time.time()))
    value = base64.b64encode(value)
    signature = LilCookies._signature_from_secret(cookie_secret, name, value, timestamp)
    return "|".join([value, timestamp, signature])

  @staticmethod
  def _verified_cookie_value(cookie_secret, name, signed_value):
    """Returns the un-encrypted value given the signed value if it validates, or None."""
    value = signed_value
    if not value: return None
    parts = value.split("|")
    if len(parts) != 3: return None
    signature = LilCookies._signature_from_secret(cookie_secret, name, parts[0], parts[1])
    if not LilCookies._time_independent_equals(parts[2], signature):
      logging.warning("Invalid cookie signature %r", value)
      return None
    timestamp = int(parts[1])
    if timestamp < time.time() - 31 * 86400:
      logging.warning("Expired cookie %r", value)
      return None
    try:
      return base64.b64decode(parts[0])
    except:
      return None

  def __init__(self, handler, cookie_secret):
    """You must specify the cookie_secret to use any of the secure methods.
    It should be a long, random sequence of bytes to be used as the HMAC
    secret for the signature.
    """
    if len(cookie_secret) < 45:
      raise ValueError("LilCookies cookie_secret should at least be 45 characters long, but got `%s`" % cookie_secret)
    self.handler = handler
    self.request = handler.request
    self.response = handler.response
    self.cookie_secret = cookie_secret

  def cookies(self):
    """A dictionary of Cookie.Morsel objects."""
    if not hasattr(self, "_cookies"):
      self._cookies = Cookie.BaseCookie()
      if "Cookie" in self.request.headers:
        try:
          self._cookies.load(self.request.headers["Cookie"])
        except:
          self.clear_all_cookies()
    return self._cookies

  def get_cookie(self, name, default=None):
    """Gets the value of the cookie with the given name, else default."""
    if name in self.cookies():
      return self._cookies[name].value
    return default

  def set_cookie(self, name, value, domain=None, expires=None, path="/",
           expires_days=None, **kwargs):
    """Sets the given cookie name/value with the given options.

    Additional keyword arguments are set on the Cookie.Morsel
    directly.
    See http://docs.python.org/library/cookie.html#morsel-objects
    for available attributes.
    """
    name = LilCookies._utf8(name)
    value = LilCookies._utf8(value)
    if re.search(r"[\x00-\x20]", name + value):
      # Don't let us accidentally inject bad stuff
      raise ValueError("Invalid cookie %r: %r" % (name, value))
    if not hasattr(self, "_new_cookies"):
      self._new_cookies = []
    new_cookie = Cookie.BaseCookie()
    self._new_cookies.append(new_cookie)
    new_cookie[name] = value
    if domain:
      new_cookie[name]["domain"] = domain
    if expires_days is not None and not expires:
      expires = datetime.datetime.utcnow() + datetime.timedelta(days=expires_days)
    if expires:
      timestamp = calendar.timegm(expires.utctimetuple())
      new_cookie[name]["expires"] = email.utils.formatdate(
        timestamp, localtime=False, usegmt=True)
    if path:
      new_cookie[name]["path"] = path
    for k, v in kwargs.iteritems():
      new_cookie[name][k] = v

    # The 2 lines below were not in Tornado.  Instead, they output all their cookies to the headers at once before a response flush.
    for vals in new_cookie.values():
      self.response.headers.add('Set-Cookie', vals.OutputString(None))

  def clear_cookie(self, name, path="/", domain=None):
    """Deletes the cookie with the given name."""
    expires = datetime.datetime.utcnow() - datetime.timedelta(days=365)
    self.set_cookie(name, value="", path=path, expires=expires,
            domain=domain)

  def clear_all_cookies(self):
    """Deletes all the cookies the user sent with this request."""
    for name in self.cookies().iterkeys():
      self.clear_cookie(name)

  def set_secure_cookie(self, name, value, expires_days=30, **kwargs):
    """Signs and timestamps a cookie so it cannot be forged.

    To read a cookie set with this method, use get_secure_cookie().
    """
    value = LilCookies._signed_cookie_value(self.cookie_secret, name, value)
    self.set_cookie(name, value, expires_days=expires_days, **kwargs)

  def get_secure_cookie(self, name, value=None):
    """Returns the given signed cookie if it validates, or None."""
    if value is None: value = self.get_cookie(name)
    return LilCookies._verified_cookie_value(self.cookie_secret, name, value)

  def _cookie_signature(self, *parts):
    return LilCookies._signature_from_secret(self.cookie_secret)

########NEW FILE########
__FILENAME__ = main
# Copyright (C) 2013 Google Inc.
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

"""RequestHandlers for starter project."""

__author__ = 'alainv@google.com (Alain Vongsouvanh)'


# Add the library location to the path
import sys
sys.path.insert(0, 'lib')

import webapp2

from attachmentproxy.handler import ATTACHMENT_PROXY_ROUTES
from main_handler import MAIN_ROUTES
from notify.handler import NOTIFY_ROUTES
from oauth.handler import OAUTH_ROUTES
from signout.handler import SIGNOUT_ROUTES


ROUTES = (
    ATTACHMENT_PROXY_ROUTES + MAIN_ROUTES + NOTIFY_ROUTES + OAUTH_ROUTES +
    SIGNOUT_ROUTES)


app = webapp2.WSGIApplication(ROUTES)

########NEW FILE########
__FILENAME__ = main_handler
# Copyright (C) 2013 Google Inc.
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

"""Request Handler for /main endpoint."""

__author__ = 'alainv@google.com (Alain Vongsouvanh)'


import io
import jinja2
import logging
import os
import webapp2

from google.appengine.api import memcache
from google.appengine.api import urlfetch

import httplib2
from apiclient import errors
from apiclient.http import MediaIoBaseUpload
from apiclient.http import BatchHttpRequest
from oauth2client.appengine import StorageByKeyName

from model import Credentials
import util


jinja_environment = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.dirname(__file__)))


PAGINATED_HTML = """
<article class='auto-paginate'>
<h2 class='blue text-large'>Did you know...?</h2>
<p>Cats are <em class='yellow'>solar-powered.</em> The time they spend
napping in direct sunlight is necessary to regenerate their internal
batteries. Cats that do not receive sufficient charge may exhibit the
following symptoms: lethargy, irritability, and disdainful glares. Cats
will reactivate on their own automatically after a complete charge
cycle; it is recommended that they be left undisturbed during this
process to maximize your enjoyment of your cat.</p><br/><p>
For more cat maintenance tips, tap to view the website!</p>
</article>
"""


class _BatchCallback(object):
  """Class used to track batch request responses."""

  def __init__(self):
    """Initialize a new _BatchCallback object."""
    self.success = 0
    self.failure = 0

  def callback(self, request_id, response, exception):
    """Method called on each HTTP Response from a batch request.

    For more information, see
      https://developers.google.com/api-client-library/python/guide/batch
    """
    if exception is None:
      self.success += 1
    else:
      self.failure += 1
      logging.error(
          'Failed to insert item for user %s: %s', request_id, exception)


class MainHandler(webapp2.RequestHandler):
  """Request Handler for the main endpoint."""

  def _render_template(self, message=None):
    """Render the main page template."""
    template_values = {'userId': self.userid}
    if message:
      template_values['message'] = message
    # self.mirror_service is initialized in util.auth_required.
    try:
      template_values['contact'] = self.mirror_service.contacts().get(
        id='python-quick-start').execute()
    except errors.HttpError:
      logging.info('Unable to find Python Quick Start contact.')

    timeline_items = self.mirror_service.timeline().list(maxResults=3).execute()
    template_values['timelineItems'] = timeline_items.get('items', [])

    subscriptions = self.mirror_service.subscriptions().list().execute()
    for subscription in subscriptions.get('items', []):
      collection = subscription.get('collection')
      if collection == 'timeline':
        template_values['timelineSubscriptionExists'] = True
      elif collection == 'locations':
        template_values['locationSubscriptionExists'] = True

    template = jinja_environment.get_template('templates/index.html')
    self.response.out.write(template.render(template_values))

  @util.auth_required
  def get(self):
    """Render the main page."""
    # Get the flash message and delete it.
    message = memcache.get(key=self.userid)
    memcache.delete(key=self.userid)
    self._render_template(message)

  @util.auth_required
  def post(self):
    """Execute the request and render the template."""
    operation = self.request.get('operation')
    # Dict of operations to easily map keys to methods.
    operations = {
        'insertSubscription': self._insert_subscription,
        'deleteSubscription': self._delete_subscription,
        'insertItem': self._insert_item,
        'insertPaginatedItem': self._insert_paginated_item,
        'insertItemWithAction': self._insert_item_with_action,
        'insertItemAllUsers': self._insert_item_all_users,
        'insertContact': self._insert_contact,
        'deleteContact': self._delete_contact,
        'deleteTimelineItem': self._delete_timeline_item
    }
    if operation in operations:
      message = operations[operation]()
    else:
      message = "I don't know how to " + operation
    # Store the flash message for 5 seconds.
    memcache.set(key=self.userid, value=message, time=5)
    self.redirect('/')

  def _insert_subscription(self):
    """Subscribe the app."""
    # self.userid is initialized in util.auth_required.
    body = {
        'collection': self.request.get('collection', 'timeline'),
        'userToken': self.userid,
        'callbackUrl': util.get_full_url(self, '/notify')
    }
    # self.mirror_service is initialized in util.auth_required.
    self.mirror_service.subscriptions().insert(body=body).execute()
    return 'Application is now subscribed to updates.'

  def _delete_subscription(self):
    """Unsubscribe from notifications."""
    collection = self.request.get('subscriptionId')
    self.mirror_service.subscriptions().delete(id=collection).execute()
    return 'Application has been unsubscribed.'

  def _insert_item(self):
    """Insert a timeline item."""
    logging.info('Inserting timeline item')
    body = {
        'notification': {'level': 'DEFAULT'}
    }
    if self.request.get('html') == 'on':
      body['html'] = [self.request.get('message')]
    else:
      body['text'] = self.request.get('message')

    media_link = self.request.get('imageUrl')
    if media_link:
      if media_link.startswith('/'):
        media_link = util.get_full_url(self, media_link)
      resp = urlfetch.fetch(media_link, deadline=20)
      media = MediaIoBaseUpload(
          io.BytesIO(resp.content), mimetype='image/jpeg', resumable=True)
    else:
      media = None

    # self.mirror_service is initialized in util.auth_required.
    self.mirror_service.timeline().insert(body=body, media_body=media).execute()
    return  'A timeline item has been inserted.'

  def _insert_paginated_item(self):
    """Insert a paginated timeline item."""
    logging.info('Inserting paginated timeline item')
    body = {
        'html': PAGINATED_HTML,
        'notification': {'level': 'DEFAULT'},
        'menuItems': [{
            'action': 'OPEN_URI',
            'payload': 'https://www.google.com/search?q=cat+maintenance+tips'
        }]
    }
    # self.mirror_service is initialized in util.auth_required.
    self.mirror_service.timeline().insert(body=body).execute()
    return  'A timeline item has been inserted.'

  def _insert_item_with_action(self):
    """Insert a timeline item user can reply to."""
    logging.info('Inserting timeline item')
    body = {
        'creator': {
            'displayName': 'Python Starter Project',
            'id': 'PYTHON_STARTER_PROJECT'
        },
        'text': 'Tell me what you had for lunch :)',
        'notification': {'level': 'DEFAULT'},
        'menuItems': [{'action': 'REPLY'}]
    }
    # self.mirror_service is initialized in util.auth_required.
    self.mirror_service.timeline().insert(body=body).execute()
    return 'A timeline item with action has been inserted.'

  def _insert_item_all_users(self):
    """Insert a timeline item to all authorized users."""
    logging.info('Inserting timeline item to all users')
    users = Credentials.all()
    total_users = users.count()

    if total_users > 10:
      return 'Total user count is %d. Aborting broadcast to save your quota' % (
          total_users)
    body = {
        'text': 'Hello Everyone!',
        'notification': {'level': 'DEFAULT'}
    }

    batch_responses = _BatchCallback()
    batch = BatchHttpRequest(callback=batch_responses.callback)
    for user in users:
      creds = StorageByKeyName(
          Credentials, user.key().name(), 'credentials').get()
      mirror_service = util.create_service('mirror', 'v1', creds)
      batch.add(
          mirror_service.timeline().insert(body=body),
          request_id=user.key().name())

    batch.execute(httplib2.Http())
    return 'Successfully sent cards to %d users (%d failed).' % (
        batch_responses.success, batch_responses.failure)

  def _insert_contact(self):
    """Insert a new Contact."""
    logging.info('Inserting contact')
    id = self.request.get('id')
    name = self.request.get('name')
    image_url = self.request.get('imageUrl')
    if not name or not image_url:
      return 'Must specify imageUrl and name to insert contact'
    else:
      if image_url.startswith('/'):
        image_url = util.get_full_url(self, image_url)
      body = {
          'id': id,
          'displayName': name,
          'imageUrls': [image_url],
          'acceptCommands': [{ 'type': 'TAKE_A_NOTE' }]
      }
      # self.mirror_service is initialized in util.auth_required.
      self.mirror_service.contacts().insert(body=body).execute()
      return 'Inserted contact: ' + name

  def _delete_contact(self):
    """Delete a Contact."""
    # self.mirror_service is initialized in util.auth_required.
    self.mirror_service.contacts().delete(
        id=self.request.get('id')).execute()
    return 'Contact has been deleted.'

  def _delete_timeline_item(self):
    """Delete a Timeline Item."""
    logging.info('Deleting timeline item')
    # self.mirror_service is initialized in util.auth_required.
    self.mirror_service.timeline().delete(id=self.request.get('itemId')).execute()
    return 'A timeline item has been deleted.'
	


MAIN_ROUTES = [
    ('/', MainHandler)
]

########NEW FILE########
__FILENAME__ = model
# Copyright (C) 2013 Google Inc.
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

"""Datastore models for Starter Project"""

__author__ = 'alainv@google.com (Alain Vongsouvanh)'


from google.appengine.ext import db

from oauth2client.appengine import CredentialsProperty


class Credentials(db.Model):
  """Datastore entity for storing OAuth2.0 credentials.

  The CredentialsProperty is provided by the Google API Python Client, and is
  used by the Storage classes to store OAuth 2.0 credentials in the data store.
  """
  credentials = CredentialsProperty()

########NEW FILE########
__FILENAME__ = handler
# Copyright (C) 2013 Google Inc.
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

"""Request Handler for /notify endpoint."""

__author__ = 'alainv@google.com (Alain Vongsouvanh)'


import io
import json
import logging
import webapp2

from random import choice
from apiclient.http import MediaIoBaseUpload
from oauth2client.appengine import StorageByKeyName

from model import Credentials
import util


CAT_UTTERANCES = [
    "<em class='green'>Purr...</em>",
    "<em class='red'>Hisss... scratch...</em>",
    "<em class='yellow'>Meow...</em>"
]


class NotifyHandler(webapp2.RequestHandler):
  """Request Handler for notification pings."""

  def post(self):
    """Handles notification pings."""
    logging.info('Got a notification with payload %s', self.request.body)
    data = json.loads(self.request.body)
    userid = data['userToken']
    # TODO: Check that the userToken is a valid userToken.
    self.mirror_service = util.create_service(
        'mirror', 'v1',
        StorageByKeyName(Credentials, userid, 'credentials').get())
    if data.get('collection') == 'locations':
      self._handle_locations_notification(data)
    elif data.get('collection') == 'timeline':
      self._handle_timeline_notification(data)

  def _handle_locations_notification(self, data):
    """Handle locations notification."""
    location = self.mirror_service.locations().get(id=data['itemId']).execute()
    text = 'Python Quick Start says you are at %s by %s.' % \
        (location.get('latitude'), location.get('longitude'))
    body = {
        'text': text,
        'location': location,
        'menuItems': [{'action': 'NAVIGATE'}],
        'notification': {'level': 'DEFAULT'}
    }
    self.mirror_service.timeline().insert(body=body).execute()

  def _handle_timeline_notification(self, data):
    """Handle timeline notification."""
    for user_action in data.get('userActions', []):
      # Fetch the timeline item.
      item = self.mirror_service.timeline().get(id=data['itemId']).execute()

      if user_action.get('type') == 'SHARE':
        # Create a dictionary with just the attributes that we want to patch.
        body = {
            'text': 'Python Quick Start got your photo! %s' % item.get('text', '')
        }

        # Patch the item. Notice that since we retrieved the entire item above
        # in order to access the caption, we could have just changed the text
        # in place and used the update method, but we wanted to illustrate the
        # patch method here.
        self.mirror_service.timeline().patch(
            id=data['itemId'], body=body).execute()

        # Only handle the first successful action.
        break
      elif user_action.get('type') == 'LAUNCH':
        # Grab the spoken text from the timeline card and update the card with
        # an HTML response (deleting the text as well).
        note_text = item.get('text', '');
        utterance = choice(CAT_UTTERANCES)

        item['text'] = None
        item['html'] = ("<article class='auto-paginate'>" +
            "<p class='text-auto-size'>" +
            "Oh, did you say " + note_text + "? " + utterance + "</p>" +
            "<footer><p>Python Quick Start</p></footer></article>")
        item['menuItems'] = [{ 'action': 'DELETE' }];

        self.mirror_service.timeline().update(
            id=item['id'], body=item).execute()
      else:
        logging.info(
            "I don't know what to do with this notification: %s", user_action)


NOTIFY_ROUTES = [
    ('/notify', NotifyHandler)
]

########NEW FILE########
__FILENAME__ = handler
# Copyright (C) 2013 Google Inc.
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

"""OAuth 2.0 handlers."""

__author__ = 'alainv@google.com (Alain Vongsouvanh)'


import logging
import webapp2
from urlparse import urlparse

from oauth2client.appengine import StorageByKeyName
from oauth2client.client import flow_from_clientsecrets
from oauth2client.client import FlowExchangeError

from model import Credentials
import util


SCOPES = ('https://www.googleapis.com/auth/glass.timeline '
          'https://www.googleapis.com/auth/glass.location '
          'https://www.googleapis.com/auth/userinfo.profile')


class OAuthBaseRequestHandler(webapp2.RequestHandler):
  """Base request handler for OAuth 2.0 flow."""

  def create_oauth_flow(self):
    """Create OAuth2.0 flow controller."""
    flow = flow_from_clientsecrets('client_secrets.json', scope=SCOPES)
    # Dynamically set the redirect_uri based on the request URL. This is
    # extremely convenient for debugging to an alternative host without manually
    # setting the redirect URI.
    pr = urlparse(self.request.url)
    flow.redirect_uri = '%s://%s/oauth2callback' % (pr.scheme, pr.netloc)
    return flow


class OAuthCodeRequestHandler(OAuthBaseRequestHandler):
  """Request handler for OAuth 2.0 auth request."""

  def get(self):
    flow = self.create_oauth_flow()
    flow.params['approval_prompt'] = 'force'
    # Create the redirect URI by performing step 1 of the OAuth 2.0 web server
    # flow.
    uri = flow.step1_get_authorize_url()
    # Perform the redirect.
    self.redirect(str(uri))


class OAuthCodeExchangeHandler(OAuthBaseRequestHandler):
  """Request handler for OAuth 2.0 code exchange."""

  def get(self):
    """Handle code exchange."""
    code = self.request.get('code')
    if not code:
      # TODO: Display error.
      return None
    oauth_flow = self.create_oauth_flow()

    # Perform the exchange of the code. If there is a failure with exchanging
    # the code, return None.
    try:
      creds = oauth_flow.step2_exchange(code)
    except FlowExchangeError:
      # TODO: Display error.
      return None

    users_service = util.create_service('oauth2', 'v2', creds)
    # TODO: Check for errors.
    user = users_service.userinfo().get().execute()

    userid = user.get('id')

    # Store the credentials in the data store using the userid as the key.
    # TODO: Hash the userid the same way the userToken is.
    StorageByKeyName(Credentials, userid, 'credentials').put(creds)
    logging.info('Successfully stored credentials for user: %s', userid)
    util.store_userid(self, userid)

    self._perform_post_auth_tasks(userid, creds)
    self.redirect('/')

  def _perform_post_auth_tasks(self, userid, creds):
    """Perform commong post authorization tasks.

    Subscribes the service to notifications for the user and add one sharing
    contact.

    Args:
      userid: ID of the current user.
      creds: Credentials for the current user.
    """
    mirror_service = util.create_service('mirror', 'v1', creds)
    hostname = util.get_full_url(self, '')

    # Only do the post auth tasks when deployed.
    if hostname.startswith('https://'):
      # Insert a subscription.
      subscription_body = {
          'collection': 'timeline',
          # TODO: hash the userToken.
          'userToken': userid,
          'callbackUrl': util.get_full_url(self, '/notify')
      }
      mirror_service.subscriptions().insert(body=subscription_body).execute()

      # Insert a sharing contact.
      contact_body = {
          'id': 'python-quick-start',
          'displayName': 'Python Quick Start',
          'imageUrls': [util.get_full_url(self, '/static/images/python.png')],
          'acceptCommands': [{ 'type': 'TAKE_A_NOTE' }]
      }
      mirror_service.contacts().insert(body=contact_body).execute()
    else:
      logging.info('Post auth tasks are not supported on staging.')

    # Insert welcome message.
    timeline_item_body = {
        'text': 'Welcome to the Python Quick Start',
        'notification': {
            'level': 'DEFAULT'
        }
    }
    mirror_service.timeline().insert(body=timeline_item_body).execute()


OAUTH_ROUTES = [
    ('/auth', OAuthCodeRequestHandler),
    ('/oauth2callback', OAuthCodeExchangeHandler)
]

########NEW FILE########
__FILENAME__ = handler
# Copyright (C) 2013 Google Inc.
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

"""Request Handler for /signout endpoint."""

__author__ = 'alainv@google.com (Alain Vongsouvanh)'


import webapp2

from google.appengine.api import urlfetch

from model import Credentials
import util


OAUTH2_REVOKE_ENDPOINT = 'https://accounts.google.com/o/oauth2/revoke?token=%s'


class SignoutHandler(webapp2.RequestHandler):
  """Request Handler for the signout endpoint."""

  @util.auth_required
  def post(self):
    """Delete the user's credentials from the datastore."""
    urlfetch.fetch(OAUTH2_REVOKE_ENDPOINT % self.credentials.refresh_token)
    util.store_userid(self, '')
    credentials_entity = Credentials.get_by_key_name(self.userid)
    if credentials_entity:
      credentials_entity.delete()
    self.redirect('/')


SIGNOUT_ROUTES = [
    ('/signout', SignoutHandler)
]

########NEW FILE########
__FILENAME__ = util
# Copyright (C) 2013 Google Inc.
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

"""Utility functions for the Quickstart."""

__author__ = 'alainv@google.com (Alain Vongsouvanh)'


from urlparse import urlparse

import httplib2
from apiclient.discovery import build
from oauth2client.appengine import StorageByKeyName
from oauth2client.client import AccessTokenRefreshError
import sessions

from model import Credentials


# Load the secret that is used for client side sessions
# Create one of these for yourself with, for example:
# python -c "import os; print os.urandom(64)" > session.secret
SESSION_SECRET = open('session.secret').read()


def get_full_url(request_handler, path):
  """Return the full url from the provided request handler and path."""
  pr = urlparse(request_handler.request.url)
  return '%s://%s%s' % (pr.scheme, pr.netloc, path)


def load_session_credentials(request_handler):
  """Load credentials from the current session."""
  session = sessions.LilCookies(request_handler, SESSION_SECRET)
  userid = session.get_secure_cookie(name='userid')
  if userid:
    return userid, StorageByKeyName(Credentials, userid, 'credentials').get()
  else:
    return None, None


def store_userid(request_handler, userid):
  """Store current user's ID in session."""
  session = sessions.LilCookies(request_handler, SESSION_SECRET)
  session.set_secure_cookie(name='userid', value=userid)


def create_service(service, version, creds=None):
  """Create a Google API service.

  Load an API service from a discovery document and authorize it with the
  provided credentials.

  Args:
    service: Service name (e.g 'mirror', 'oauth2').
    version: Service version (e.g 'v1').
    creds: Credentials used to authorize service.
  Returns:
    Authorized Google API service.
  """
  # Instantiate an Http instance
  http = httplib2.Http()

  if creds:
    # Authorize the Http instance with the passed credentials
    creds.authorize(http)

  return build(service, version, http=http)


def auth_required(handler_method):
  """A decorator to require that the user has authorized the Glassware."""

  def check_auth(self, *args):
    self.userid, self.credentials = load_session_credentials(self)
    self.mirror_service = create_service('mirror', 'v1', self.credentials)
    # TODO: Also check that credentials are still valid.
    if self.credentials:
      try:
        self.credentials.refresh(httplib2.Http())
        return handler_method(self, *args)
      except AccessTokenRefreshError:
        # Access has been revoked.
        store_userid(self, '')
        credentials_entity = Credentials.get_by_key_name(self.userid)
        if credentials_entity:
          credentials_entity.delete()
    self.redirect('/auth')
  return check_auth

########NEW FILE########
