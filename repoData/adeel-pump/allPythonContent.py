__FILENAME__ = adapters
# Functions for serving a Pump app.

from pump.util import wsgi

default_options = {
  "host": "127.0.0.1",
  "port": 8000,
  "server_name": "Pump"}

# Serve a Pump app with Paste's WSGI server.
def serve_with_paste(app, options={}):
  wsgi_app = wsgi.build_wsgi_app(app)
  options = dict(default_options, **options)

  from paste.httpserver import serve
  return serve(wsgi_app, **_get_paste_config(options))

def _get_paste_config(options):
  options["server_version"] = options.get("server_name")
  del options["server_name"]
  return options
########NEW FILE########
__FILENAME__ = content_type
# A middleware that adds a content_type key to the response.

import mimetypes
from pump.util import response

def wrap_content_type(app, options={}):
  def wrapped_app(req):
    resp = app(req)
    if not resp or resp.get("headers", {}).get("content_type"):
      return resp
    mime_type, _ = mimetypes.guess_type(req["uri"])
    return response.with_content_type(resp,
      mime_type or "application/octet-stream")

  return wrapped_app
########NEW FILE########
__FILENAME__ = cookies
# A middleware that adds cookie support.

from Cookie import SimpleCookie as Cookie
from pump.util import codec

# Adds a "cookies" key to the request, which contains a dictionary containing
# any cookies sent by the client.  If any new values are found in the
# dictionary after your app is called, the new cookies are sent to the client.
# The values in the dict will be converted to strings, unless they are
# themselves dicts.  In that case, the "value" key will be used as the cookie
# value and the other keys will be interpreted as cookie attributes.
# 
#     request["cookies"] = {"a": {"value": "b", "path": "/"}}
# 
# Note: if a cookie is set and is later deleted from request["cookies"], the
# corresponding cookie will not automatically be deleted.  You need to set the
# "expires" attribute of the cookie to a time in the past.
def wrap_cookies(app):
  def wrapped_app(request):
    # Get any cookies from the request.
    req_cookies = request.get("cookies")
    if not req_cookies:
      req_cookies = _parse_cookies(request)
    request["cookies"] = req_cookies

    response = app(request)

    # If the app modified request["cookies"], set the new cookies.
    updated_cookies = request.get("cookies", {}).copy()
    cookie_header = []
    for k, v in updated_cookies.iteritems():
      try:
        value = v.get("value")
      except AttributeError:
        value = str(v)
      if k not in req_cookies or req_cookies[k] != value:
        cookie_header.append(_format_cookie(k, v))

    response.setdefault("headers", {})["set_cookie"] = cookie_header
    return response
  return wrapped_app

# Parse the cookies from a request into a dictionary.
def _parse_cookies(request):
  cookie = Cookie(request["headers"].get("cookie"))
  parsed = {}
  for k, v in cookie.iteritems():
    parsed[k] = v.value
  return parsed

# Formats the dict of cookies for the set_cookie header.  If a value is a dict,
# its "value" key will be used as the value and the other keys will be
# interpreted as cookie attributes.
def _format_cookie(key, val):
  if not isinstance(val, dict):
    val = {"value": val}

  cookie = Cookie()
  cookie[key] = val["value"]
  del val["value"]

  morsel = cookie[key]
  for k, v in val.iteritems():
    morsel[k] = v
  return morsel.OutputString()

########NEW FILE########
__FILENAME__ = file
# A middleware for serving files.

import os
from pump.util import codec
from pump.util import response

# Wrap the app so that instead of handling requests normally, it first looks
# for a file in the root_path directory that corresponds to the request URL.
# If the file is not found, the request is handled normally.
def wrap_file(app, root_path, options={}):
  if not os.path.isdir(root_path):
    raise Exception("Directory does not exist: %s" % root_path)

  options = dict(options, **{"root": root_path, "index_files": True})

  def wrapped_app(req):
    if req["method"] != "get":
      return app(req)

    path = codec.url_decode(req["uri"])[1:]
    return response.file_response(path, options) or app(req)

  return wrapped_app
########NEW FILE########
__FILENAME__ = nested_params
# A middleware for parsing nested params, like
#     {"a[b]": 'c'}  =>  {'a': {'b': 'c'}}.

import re
from itertools import chain

def wrap_nested_params(app, options={}):
  def wrapped_app(req):
    # You can specify a custom key parsing function with the key_parser option.
    key_parser = options.get('key_parser', parse_nested_keys)
    req["params"] = nest_params(req["params"], key_parser)
    return app(req)
  return wrapped_app

# Takes a flat string of parameters and turns it into a nested dict of
# parameters, using the function key_parser to split the parameter names
# into keys.
def nest_params(params, key_parser):
  return reduce(lambda d, kv: set_nested_value(d, key_parser(kv[0]), kv[1]),
    param_pairs(params), {})

def param_pairs(params):
  return sum(
    [[(key, v) for v in val] if isinstance(val, list) else [(key, val)]
      for (key, val) in params.items()], [])

# Set a new value, v, in the dict d, at the key given by keys.  For example,
# 
#     set_nested_value({"a": {"b": {"c": "val"}}}, ["a", "b", "c"], "newval")
#       # => {"a": {"b": {"c": "newval"}}}
# 
#     set_nested_value({"a": {"b": {"c": "val"}}}, ["a", "x", "y"], "newval")
#       # => {"a": {"b": {"c": "val"}}, {"x": {"y": "newval"}}}
# 
# Treats values of blank keys as elements in a list.
def set_nested_value(d, keys, v):
  k, ks = None, None
  if keys:
    k = keys[0]
    if len(keys) > 1:
      ks = keys[1:]

  updates = {}
  if k:
    if ks:
      j, js = ks[0], ks[1:]
      if j == "":
        updates = {k: set_nested_value(d.get(k, []), js, v)}
      else:
        updates = {k: set_nested_value(d.get(k, {}), ks, v)}
    else:
      updates = {k: v}
  else:
    updates = v

  if isinstance(d, list):
    return d + [updates]
  return dict(d, **updates)

#    "a[b][c]"  =>  ["a", "b", "c"]
def parse_nested_keys(string):
  k, ks = re.compile(r"^(.*?)((?:\[.*?\])*)$").match(string).groups()
  if not ks:
    return [k]
  keys = re.compile('\[(.*?)\]').findall(ks)
  return [k] + keys
########NEW FILE########
__FILENAME__ = params
# A middleware for parsing GET and POST params.

import re
from pump.util import codec

# Middleware to parse GET and POST params.  Adds the following keys to the
# request:
# 
#   - get_params
#   - post_params
#   - params
# 
# You can specify an encoding to decode the URL-encoded params with.  If not
# specified, uses the character encoding specified in the request, or UTF-8 by
# default.
def wrap_params(app, options={}):
  def wrapped_app(request):
    encoding = (options.get('encoding') or
                request.get('character_encoding') or
                "utf8")
    if not request.get('get_params'):
      request = parse_get_params(request, encoding)
    if not request.get('post_params'):
      request = parse_post_params(request, encoding)
    return app(request)

  return wrapped_app

# Parse params from the query string.
def parse_get_params(request, encoding):
  if request.get("query_string"):
    params = parse_params(request["query_string"], encoding)
  else:
    params = {}

  return _recursive_merge(request, {'get_params': params, 'params': params})

# Parse params from the request body.
def parse_post_params(request, encoding):
  if _does_have_urlencoded_form(request) and request.get("body"):
    params = parse_params(request["body"].read(), encoding)
  else:
    params = {}

  return _recursive_merge(request, {'post_params': params, 'params': params})

# Parse params from a string (e.g. "a=b&c=d") into a dict.
def parse_params(params_string, encoding):
  def _parse(params_dict, encoded_param):
    match = re.compile(r'([^=]+)=(.*)').match(encoded_param)
    if not match:
      return params_dict
    key, val = match.groups()
    return set_param(params_dict,
      codec.url_decode(key, encoding), codec.url_decode(val or '', encoding))

  return reduce(_parse, params_string.split('&'), {})

# Set a value for a key.  If it already has a value, make a list of values.
def set_param(params, key, val):
  cur = params.get(key)
  if cur:
    if isinstance(cur, list):
      params[key].append(val)
    else:
      params[key] = [cur, val]
  else:
    params[key] = val
  return params

# Check whether a urlencoded form was submitted.
def _does_have_urlencoded_form(request):
  return request.get('content_type', '').startswith(
    'application/x-www-form-urlencoded')

# Merge two dicts recursively.
def _recursive_merge(x, y):
  z = x.copy()
  for key, val in y.iteritems():
    if isinstance(val, dict):
      if not z.has_key(key):
        z[key] = {}
      z[key] = _recursive_merge(z[key], val)
    else:
      z[key] = val
  return z

########NEW FILE########
__FILENAME__ = session
# A middleware that implements cookie-based sessions using Beaker.

import beaker.middleware
from pump.util import wsgi

# Adds a "session" key to the request.  Takes the following options:
# 
#   - store:
#       One of "memory", "database", "file", "cookie", "dbm", "memcached",
#       or "google".  Defaults to "memory".
#   - lock_dir:
#       The path to the directory to be used as a lock file.  See
#       <http://beaker.groovie.org/glossary.html#term-dog-pile-effect>.
#   - data_dir:
#       The path to the directory where files are stored.  Used for file and
#       dbm stores.
#   - url:
#       Used for database and memcached stores.  In the former case, this
#       should be a SQLAlchemy database string <http://bit.ly/gvzIlw>, e.g.
#       "sqlite:///tmp/sessions.db".  In the latter case, it should be a
#       semicolon-separated list of memcached servers.
#   - auto:
#       If False, you will need to call request["session"].save() explicitly
#       after modifying request["session"].  Defaults to True.
#   - cookie:
#       A dictionary with the following keys:
# 
#       - key:
#           The name of the cookie.  Defaults to "pump-session".
#       - secret:
#           A long, randomly-generated string used to ensure session
#           integrity.
#
#           - domain:
#               The domain the cookie will be set on.  Defaults to the current
#               domain.
#           - expires:
#               The expiration date of the cookie.  If True, expires when the
#               browser closes.  If False, never expires.  If a datetime
#               instance, expires at that specific date and time.  If a
#               timedelta instance, expires after the given time interval.
#               Defaults to False.
#           - secure:
#               Whether the session cookie should be marked as secure (for
#               SSL).
#           - timeout:
#               Seconds after the session was last accessed until it is
#               invalidated.  Defaults to never expiring.
#
# This uses Beaker in the background, so you can read
# <http://beaker.groovie.org/configuration.html> for more details.

def wrap_session(app, options={}):
  # Guess which language doesn't support recursively merging dictionaries?
  options = dict(dict({
    "store": "memory",
    "auto": True}, **options), cookies=dict({
      "expires": False,
      "key": "pump-session",
      "secure": False}, **options.get("cookies", {})))

  for middleware in [wrap_unbeaker, wrap_beaker(options)]:
    app = middleware(app)
  return app

# A Pump middleware that wraps around Beaker's WSGI middleware.
def wrap_beaker(options):
  return wsgi.build_middleware(_beaker_wsgi_middleware, options)

# Renames the beaker.session key in the request to "session".
def wrap_unbeaker(app):
  def wrapped(req):
    req["session"] = req.get("beaker.session")
    if req.has_key("beaker.session"):
      del req["beaker.session"]
    return app(req)
  return wrapped

# The WSGI middleware provided by Beaker.
def _beaker_wsgi_middleware(app, options):
  return beaker.middleware.SessionMiddleware(app, _get_beaker_config(options))

# Reformat options dictionary to match Beaker's configuration settings.  See
# <http://beaker.groovie.org/configuration.html>.
def _get_beaker_config(options):
  return {
    "session.data_dir":       options.get("data_dir"),
    "session.lock_dir":       options.get("lock_dir"),
    "session.type":           _get_beaker_session_type(options.get("store")),
    "session.url":            options.get("url"),
    "session.auto":           options.get("auto"),
    "session.cookie_expires": options.get("cookies").get("expires"),
    "session.cookie_domain":  options.get("cookies").get("domain"),
    "session.key":            options.get("cookies").get("key"),
    "session.secret":         options.get("cookies").get("secret"),
    "session.secure":         options.get("cookies").get("secure"),
    "session.timeout":        options.get("cookies").get("timeout")}

def _get_beaker_session_type(store):
  return {
    "database":  "ext:database",
    "memcached": "ext:memcached",
    "google":    "ext:google"}.get(store, store)
########NEW FILE########
__FILENAME__ = static
# A middleware for serving static files that is more selective than
# pump.middleware.file.

from pump.middleware.file import *

# Wrap the app so that if the request URL falls under any of the URLs in
# static_urls (the URL must start with one of the static_urls), it looks in
# public_dir for a file corresponding to the request URL.  If no such file is
# not found, the request is handled normally.
# 
# Note that the paths in static_urls should include the leading '/'.
def wrap_static(app, public_dir, static_urls):
  app_with_file = wrap_file(app, public_dir)
  def wrapped_app(req):
    if any([req["uri"].startswith(s) for s in static_urls]):
      return app_with_file(req)
    else:
      return app(req)
  return wrapped_app
########NEW FILE########
__FILENAME__ = codec
import urllib

def url_decode(string, encoding='utf8'):
  return urllib.unquote_plus(string)

def url_encode(string, encoding='utf8'):
  return urllib.urlencode(string)

########NEW FILE########
__FILENAME__ = response
import os

# The minimal Pump response.
skeleton = {"status": 200, "headers": {}, "body": ""}

# Return a skeleton response with the given body.
def with_body(body):
  return dict(skeleton, body=body)

# Return a redirect response to the given URL.
def redirect(url):
  return {"status": 302, "headers": {"Location": url}, "body": ""}

# Return the given response updated with the given status.
def with_status(response, status):
  return dict(response, status=status)

# Return the given response updated with the given header.
def with_header(response, key, value):
  return dict(response,
    headers=dict(response.get("headers", {}), **{key: value}))

# Return the given response updated with the given content-type.
def with_content_type(response, content_type):
  return with_header(response, 'content_type', content_type)

# Returns a response containing the contents of the file at the given path.
# Options:
#
#   - root: the root path for the given file path
#   - index_files: whether to look for index.* files in directories (true by
#                  default)
def file_response(path, options={}):
  file = _get_file(path, options)
  if file:
    return with_body(open(file, 'r'))

def _get_file(path, options={}):
  root = options.get("root")
  if root:
    if _is_path_safe(root, path):
      file = os.path.join(root, path)
  else:
    file = path

  if os.path.isdir(file):
    if options.get("index_files", True):
      return _find_index(file)
  elif os.path.exists(file):
    return file

def _is_path_safe(root, path):
  return os.path.realpath(os.path.join(root, path)).startswith(
    os.path.realpath(root))

def _find_index(dir):
  indexes = [f for f in os.listdir(dir) if f.lower().startswith('index.')]
  if indexes:
    return indexes[0]

########NEW FILE########
__FILENAME__ = wsgi
# Methods for converting between Pump apps and WSGI apps.

import threading
from pump.util.response import skeleton

# Convert a WSGI app to a Pump app.
def build_app(wsgi_app):
  def app(request):
    # A thread-local storage is required here, because of the way WSGI is
    # implemented (start_response in particular).  As far as I can tell,
    # we have to give the WSGI app a custom start_response function that
    # just saves the status and headers to a thread-local variable.
    # Then we combine these with the body, returned by the WSGI app, to build
    # the Pump response.
    data = threading.local()
    def start_response(status, headers, _=None):
      data.status = status
      data.headers = headers

    body = wsgi_app(build_wsgi_request(request), start_response)
    return build_response((data.status, data.headers, body))
  return app

# Convert a WSGI request (environ) to a Pump request.
def build_request(wsgi_req):
  return dict({
    'uri':     wsgi_req.get('RAW_URI') or wsgi_req.get('PATH_INFO'),
    'scheme':  wsgi_req.get('wsgi.url_scheme'),
    'method':  wsgi_req.get('REQUEST_METHOD', 'get').lower(),
    'headers': get_headers(wsgi_req),
    'body':    wsgi_req.get('wsgi.input')
  }, **dict([(k.lower(), v) for k, v in wsgi_req.iteritems()]))

# Convert a WSGI response to a Pump response.
def build_response(wsgi_response):
  status, headers, body = wsgi_response
  return {
    "status":  int(status[:3]),
    "headers": dict([(k.replace("-", "_").lower(), v) for k, v in headers]),
    "body":    body}

# Converts a WSGI middleware into Pump middleware.  You can pass additional
# arguments which will be passed to the middleware given.
def build_middleware(wsgi_middleware, *args):
  def middleware(app):
    return build_app(wsgi_middleware(build_wsgi_app(app), *args))
  return middleware

# Convert a Pump app to a WSGI app.
def build_wsgi_app(app):
  def wsgi_app(request, start_response, _=None):
    response = app(build_request(request)) or {}
    response_map = dict(skeleton, **response)
    return build_wsgi_response(response_map, start_response)
  return wsgi_app

# Convert a Pump request to a WSGI request.
def build_wsgi_request(request):
  wsgi_request = {
    "SERVER_PORT":     request.get("server_port"),
    "SERVER_NAME":     request.get("server_name"),
    "REMOTE_ADDR":     request.get("remote_addr"),
    "RAW_URI":         request.get("uri"),
    "PATH_INFO":       request.get("uri"),
    "QUERY_STRING":    request.get("query_string"),
    "wsgi.url_scheme": request.get("scheme"),
    "REQUEST_METHOD":  request.get("method", "GET").upper(),
    "CONTENT_TYPE":    request.get("content_type"),
    "CONTENT_LENGTH":  request.get("content_length"),
    "wsgi.input":      request.get("body")}
  for key, value in request.get("headers", {}).iteritems():
    wsgi_request["HTTP_%s" % key.upper()] = value

  for key, value in request.iteritems():
    if key.upper() not in wsgi_request:
      wsgi_request[key] = value

  return wsgi_request

# Convert a Pump response to a WSGI response.
def build_wsgi_response(response_map, start_response):
  response = {}
  response = set_status(response, response_map["status"])
  response = set_headers(response, response_map["headers"])
  response = set_body(response, response_map["body"])

  start_response(response["status"], response["headers"])
  return response["body"]

def get_headers(request):
  return dict([(k.replace('HTTP_', '').lower(), v) for k, v in request.items()
    if k.startswith('HTTP_')])

def set_status(response, status):
  status_map = {
    200: "200 OK",
    301: "301 Moved Permanently",
    302: "302 Found",
    303: "303 See Other",
    304: "304 Not Modified",
    307: "307 Temporary Redirect",
    400: "400 Bad Request",
    401: "401 Unauthorized",
    403: "403 Forbidden",
    404: "404 Not Found",
    405: "405 Method Not Allowed",
    418: "418 I'm a teapot",
    500: "500 Internal Server Error",
    502: "502 Bad Gateway",
    503: "503 Service Unavailable",
    504: "504 Gateway Timeout"}

  response["status"] = status_map.get(status, str(status))
  return response

def set_headers(response, headers):
  response["headers"] = []
  for key, val in headers.items():
    key = key.replace("_", "-").title()
    if isinstance(val, list):
      for v in val:
        response["headers"].append((key, v))
    else:
      response["headers"].append((key, val))
  return response

def set_body(response, body):
  if isinstance(body, str) or isinstance(body, unicode):
    response["body"] = body
  elif isinstance(body, list):
    response["body"] = ''.join(body)
  elif isinstance(body, file):
    response["body"] = body.read()
  elif not body:
    response["body"] = ""
  else:
    raise Exception("Unrecognized body: %s" % repr(body))

  return response
########NEW FILE########
