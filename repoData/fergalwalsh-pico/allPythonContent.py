__FILENAME__ = auth
import pico
from pico import PicoError


class NotAuthorizedError(PicoError):
    def __init__(self, message=''):
        PicoError.__init__(self, message)
        self.response.status = "401 Not Authorized"
        self.response.set_header("WWW-Authenticate",  "Basic")


class InvalidSessionError(PicoError):
    def __init__(self, message=''):
        PicoError.__init__(self, message)
        self.response.status = "440 Invalid Session"


class Bunch:
    def __init__(self, **kwds):
        self.__dict__.update(kwds)


class object(pico.object):
    account_manager = None
    __headers__ = {'X-SESSION-ID': ''}

    def __init__(self):
        super(object, self).__init__()
        self.username = None
        if type(self.account_manager) == dict:
            self.account_manager = Bunch(**self.account_manager)
        request = pico.get_request()
        if 'HTTP_AUTHORIZATION' in request:
            try:
                auth_header = request.get('HTTP_AUTHORIZATION')
                scheme, data = auth_header.split(None, 1)
                assert(scheme == 'Basic')
                username, password = data.decode('base64').split(':', 1)
                self.user = self._get_user(username, password)
            except Exception, e:
                raise NotAuthorizedError(str(e))
        elif 'HTTP_X_SESSION_ID' in request:
            session_id = request.get('HTTP_X_SESSION_ID')
            self.user = self._get_session(session_id)
        elif 'DUMMY_REQUEST' in request:
            pass
        else:
            raise NotAuthorizedError("No username or password supplied")

    def _get_user(self, username, password):
        if self.account_manager:
            return self.account_manager._get_user(username, password)

    def _get_session(self, session_id):
        if self.account_manager:
            return self.account_manager._get_session(session_id)

########NEW FILE########
__FILENAME__ = client
"""
Load and call functions from a remote pico module.

pico.client.url = "http://localhost:8800/pico/" # the url of the remote pico server
example = pico.client.load('example')
s = example.hello()
# s == "Hello World"

s = example.hello("Python")
# s == "Hello Python"

Use help(example.hello) or example.hello? as normal to check function parameters and docstrings.
"""

__author__ = 'Fergal Walsh'
__version__ = '1.2.0'

import urllib
import urllib2
import json
import imp
import time
import hashlib
import httplib
import pico

url = 'http://localhost:8800/pico/'
_username = None
_password = None
_td = 0

def get(url, args={}, stream=False):
    if _username:
        args['_username'] = _username
        args['_nonce'] = int(time.time()) + _td
        args['_key'] = _hash(_password + str(args['_nonce']))
    encoded_args = urllib.urlencode(args)
    if stream:
        return _stream(url, encoded_args)
    else:
        r =  urllib.urlopen(url, encoded_args).read()
        data = json.loads(r)
        if type(data) == dict and 'exception' in data:
            raise Exception(data['exception'])
        else:
            return data

def _stream(url, encoded_args=""):
    s = urllib2.urlparse.urlsplit(url)
    try:
        c = httplib.HTTPConnection(s.netloc)
        u = s.path + '?'
        if s.query: u += s.query + '&'
        u += encoded_args
        c.request("GET", u)
        r = c.getresponse()
        for l in r.fp:
            if 'data:' in l:
                yield json.loads(l[6:-1])
    finally:
        c.close()


def _call_function(module, function, args, stream=False): 
    for k in args:
        args[k] = pico.to_json(args[k])
    # args['_function'] = function
    # args['_module'] = module
    return get(url + '%s/%s/'%(module, function), args, stream)

def authenticate(username, password):
    """ 
    Authenticate with the pico server

    You must call this function before calling any protected functions.
    """
    global _username
    global _password
    _username = username
    _password = _hash(password)
    try:
        r = _call_function('pico', 'authenticate', locals())
        return True
    except Exception, e:
        r = str(e)
        if r.startswith('Bad nonce.'):
            global _td
            _td = int(r.split('Bad nonce. The time difference is:')[-1])
            print(r)
            authenticate(username, password)
        else:
            print(r)
    return False

def unauthenticate():
    global _username
    global _password
    _username = None
    _password = None
    return True

def load(module_name):
    """ 
    Load a remote module 
    pico.client.url must be set to the appropriate pico url first.
    e.g. pico.client.url="http://localhost:8800/pico/"

    example = pico.client.load("example")
    """
    if module_name.startswith('http://'):
        pico_url, module_name = module_name.split('/pico/')
        global url
        url = pico_url + '/pico/'
    module_dict = get(url + module_name)
    module = imp.new_module(module_name)
    module.__doc__ = module_dict['__doc__']
    functions = module_dict['functions']
    for function_def in functions:
        name = function_def['name']
        args = function_def['args']
        args_string = ', '.join(["%s=%s"%(arg, json.dumps(default).replace("null", "None")) for arg, default in args if arg != None])
        stream = function_def['stream']
        docstring = function_def['doc']
        exec("""
def f(%s):
    \"\"\" %s \"\"\"
    return _call_function('%s', '%s', locals(), %s)
"""%(args_string, docstring, module_name, name, stream))
        setattr(module, name, f)
    return module

def _hash(s):
    m = hashlib.md5()
    m.update(s)
    return m.hexdigest()
    
########NEW FILE########
__FILENAME__ = modules
import inspect
import imp
import os
import sys
import types
import time
import importlib

import pico

_mtimes = {}


def module_dict(module):
    module_dict = {}
    pico_exports = getattr(module, 'pico_exports', None)
    members = inspect.getmembers(module)

    def function_filter(x):
        (name, f) = x
        return ((inspect.isfunction(f) or inspect.ismethod(f))
                and (pico_exports is None or name in pico_exports)
                and f.__module__ == module.__name__
                and not name.startswith('_')
                and not hasattr(f, 'private'))

    def class_filter(x):
        (name, c) = x
        return (inspect.isclass(c)
                and (issubclass(c, pico.Pico) or issubclass(c, pico.object))
                and (pico_exports is None or name in pico_exports)
                and c.__module__ == module.__name__)
    class_defs = map(class_dict, filter(class_filter, members))
    function_defs = map(func_dict, filter(function_filter, members))
    module_dict['classes'] = class_defs
    module_dict['functions'] = function_defs
    module_dict['__doc__'] = module.__doc__
    module_dict['__headers__'] = getattr(module, '__headers__', {})
    return module_dict


def class_dict(x):
    name, cls = x

    def method_filter(x):
        (name, f) = x
        return ((inspect.isfunction(f) or inspect.ismethod(f))
                and (not name.startswith('_') or name == '__init__')
                and not hasattr(f, 'private'))
    class_dict = {'__class__': cls.__name__}
    class_dict['name'] = name
    methods = filter(method_filter, inspect.getmembers(cls))
    class_dict['__init__'] = func_dict(methods.pop(0))
    class_dict['functions'] = map(func_dict, methods)
    class_dict['__doc__'] = cls.__doc__
    class_dict['__headers__'] = getattr(cls, '__headers__', {})
    return class_dict


def func_dict(x):
    name, f = x
    func_dict = {}
    func_dict['name'] = name
    func_dict['cache'] = ((hasattr(f, 'cacheable') and f.cacheable))
    func_dict['stream'] = ((hasattr(f, 'stream') and f.stream))
    a = inspect.getargspec(f)
    arg_list_r = reversed(a.args)
    defaults_list_r = reversed(a.defaults or [None])
    args = reversed(map(None, arg_list_r, defaults_list_r))
    args = filter(lambda x: x[0] and x[0] != 'self', args)
    func_dict['args'] = args
    func_dict['doc'] = f.__doc__
    return func_dict


def load(module_name, RELOAD=False):
    if module_name == 'pico':
        return sys.modules['pico']
    if module_name == 'pico.modules':
        if module_name in sys.modules:
            return sys.modules[module_name]
        else:
            return sys.modules[__name__]
    modules_path = './'
    if not sys.path.__contains__(modules_path):
        sys.path.insert(0, modules_path)
    m = importlib.import_module(module_name)
    if RELOAD:
        mtime = os.stat(m.__file__.replace('.pyc', '.py')).st_mtime
        if _mtimes.get(module_name, mtime) < mtime:
            if module_name in sys.modules:
                del sys.modules[module_name]
            m = importlib.import_module(module_name)
            m = reload(m)
            print("Reloaded module %s, changed at %s" % (module_name,
                                                         time.ctime(mtime)))
        _mtimes[module_name] = mtime
    if not (hasattr(m, 'pico') and m.pico == pico):
        raise ImportError('This module has not imported pico!')
    return m


def module_proxy(cls):
    module_name = cls.__module__
    module = imp.new_module(module_name)
    module.pico = pico

    def method_filter(x):
        (name, f) = x
        return ((inspect.isfunction(f) or inspect.ismethod(f))
                and (not name.startswith('_') or name == '__init__')
                and not hasattr(f, 'private'))
    methods = filter(method_filter, inspect.getmembers(cls))
    for (name, f) in methods:
        setattr(module, name, f)
    return module

json_dumpers = {
    types.ModuleType:  module_dict
}

########NEW FILE########
__FILENAME__ = server
import sys
import cgi
import json
import os
import mimetypes
import hashlib
import traceback
import getopt
import re
import SocketServer
import threading
from wsgiref.simple_server import WSGIRequestHandler, WSGIServer, make_server

try:
    import gevent
    import gevent.pywsgi
    use_gevent = True
except ImportError:
    use_gevent = False

import pico
import pico.modules

from pico import PicoError, Response

pico_path = (os.path.dirname(__file__) or '.') + '/'
_server_process = None
pico_exports = []


class APIError(Exception):
    pass


def main():
    opts_args = getopt.getopt(sys.argv[1:], "hp:dm", ["help",
                                                      "port=",
                                                      "no-reload"])
    args = dict(opts_args[0])
    port = int(args.get('--port', args.get('-p', 8800)))
    multithreaded = '-m' in args
    global RELOAD
    RELOAD = RELOAD and ('--no-reload' not in args)
    host = '0.0.0.0'  # 'localhost'
    server = _make_server(host, port, multithreaded)
    print("Serving on http://%s:%s/" % (host, port))
    if multithreaded:
        print("Using multiple threads.")
    print("URL map: ")
    print('\t' + '\n\t'.join(["%s : %s " % x for x in STATIC_URL_MAP]))
    print("Hit CTRL-C to end")
    server.serve_forever()


def _make_server(host='0.0.0.0', port=8800, multithreaded=False):
    if use_gevent:
        server = gevent.pywsgi.WSGIServer((host, port), wsgi_dev_app)
        global STREAMING
        STREAMING = True
    elif multithreaded:
        class ThreadedTCPServer(SocketServer.ForkingMixIn,
                                WSGIServer):
            pass
        server = ThreadedTCPServer((host, port), WSGIRequestHandler)
        server.set_app(wsgi_dev_app)
    else:
        server = make_server(host, port, wsgi_dev_app)

        def log_message(self, format, *args):
            if not SILENT:
                print(format % (args))
        server.RequestHandlerClass.log_message = log_message
    return server


def start_thread(host='127.0.0.1', port=8800, silent=True):
    global RELOAD, SILENT, _server_process
    RELOAD = False
    SILENT = silent

    class Server(threading.Thread):
        def __init__(self):
            super(Server, self).__init__()
            self._server = _make_server(host, port)

        def run(self):
            self._server.serve_forever()

        def stop(self):
            self._server.shutdown()
            self._server.socket.close()
            print("Pico server has stopped")

    _server_process = Server()
    _server_process.start()
    print("Serving on http://%s:%s/" % (host, port))
    return _server_process


def stop_thread():
    _server_process.stop()
    _server_process.join(1)


def call_function(module, function_name, parameters):
    try:
        f = getattr(module, function_name)
    except AttributeError:
        raise Exception("No matching function availble. "
                        "You asked for %s with these parameters %s!" % (
                            function_name, parameters))
    results = f(**parameters)
    response = Response(content=results)
    if hasattr(f, 'cacheable') and f.cacheable:
        response.cacheable = True
    if hasattr(f, 'stream') and f.stream and STREAMING:
        response.type = "stream"
    elif response.content.__class__.__name__ == 'generator':
        response.type = "chunks"
    return response


def call_method(module, class_name, method_name, parameters, init_args):
    try:
        cls = getattr(module, class_name)
        obj = cls(*init_args)
    except KeyError:
        raise Exception("No matching class availble."
                        "You asked for %s!" % (class_name))
    r = call_function(obj, method_name, parameters)
    del obj
    return r


def cache_key(params):
    params = dict(params)
    if '_callback' in params:
        del params['_callback']
    hashstring = hashlib.md5(str(params)).hexdigest()
    cache_key = "__".join([params.get('_module', ''),
                           params.get('_class', ''),
                           params.get('_function', ''),
                           hashstring])
    return cache_key.replace('.', '_')


def call(params, request):
    func = params.get('_function', '')
    module_name = params.get('_module', '')
    args = {}
    for k in params.keys():
        if not (k.startswith('_') or k.startswith('pico_')):
            try:
                args[k] = json.loads(params[k])
            except Exception:
                try:
                    args[k] = json.loads(params[k].replace("'", '"'))
                except Exception:
                    args[k] = params[k]
    callback = params.get('_callback', None)
    init_args = json.loads(params.get('_init', '[]'))
    class_name = params.get('_class', None)
    usecache = json.loads(params.get('_usecache', 'true'))
    x_session_id = params.get('_x_session_id', None)
    if x_session_id:
        request['X-SESSION-ID'] = x_session_id
    response = Response()
    if usecache and os.path.exists(CACHE_PATH):
        try:
            response = serve_file(CACHE_PATH + cache_key(params))
            log("Serving from cache")
        except OSError:
            pass
    if not response.content:
        module = pico.modules.load(module_name, RELOAD)
        json_loaders = getattr(module, "json_loaders", [])
        from_json = lambda s: pico.from_json(s, json_loaders)
        for k in args:
            args[k] = from_json(args[k])
        if class_name:
            init_args = map(from_json, init_args)
            response = call_method(module, class_name, func, args, init_args)
        else:
            response = call_function(module, func, args)
        response.json_dumpers = getattr(module, "json_dumpers", {})
        log(usecache, response.cacheable)
        if usecache and response.cacheable:
            log("Saving to cache")
            try:
                os.stat(CACHE_PATH)
            except Exception:
                os.mkdir(CACHE_PATH)
            f = open(CACHE_PATH + cache_key(params) + '.json', 'w')
            out = response.output
            if hasattr(out, 'read'):
                out = out.read()
                response.output.seek(0)
            else:
                out = out[0]
            f.write(out)
            f.close()
    response.callback = callback
    return response


def _load(module_name, params, environ):
    params['_module'] = 'pico.modules'
    params['_function'] = 'load'
    params['module_name'] = '"%s"' % module_name
    return call(params, environ)


def serve_file(file_path):
    response = Response()
    size = os.path.getsize(file_path)
    mimetype = mimetypes.guess_type(file_path)
    response.set_header("Content-type", mimetype[0] or 'text/plain')
    response.set_header("Content-length", str(size))
    response.set_header("Cache-Control", 'public, max-age=22222222')
    response.content = open(file_path, 'rb')
    response.type = "file"
    return response


def static_file_handler(path):
    file_path = ''
    for (url, directory) in STATIC_URL_MAP:
        m = re.match(url, path)
        if m:
            file_path = directory + ''.join(m.groups())

    # if the path does not point to a valid file, try default file
    file_exists = os.path.isfile(file_path)
    if not file_exists:
        file_path = os.path.join(file_path, DEFAULT)
    return serve_file(file_path)


def log(*args):
    if not SILENT:
        print(args[0] if len(args) == 1 else args)


def extract_params(environ):
    params = {}
    # if parameters are in the URL, we extract them first
    get_params = environ['QUERY_STRING']
    if get_params == '' and '/call/' in environ['PATH_INFO']:
        path = environ['PATH_INFO'].split('/')
        environ['PATH_INFO'] = '/'.join(path[:-1]) + '/'
        params.update(cgi.parse_qs(path[-1]))

    # now get GET and POST data
    fields = cgi.FieldStorage(fp=environ['wsgi.input'], environ=environ)
    for name in fields:
        if fields[name].filename:
            upload = fields[name]
            params[name] = upload.file
        elif type(fields[name]) == list and fields[name][0].file:
            params[name] = [v.file for v in fields[name]]
        else:
            params[name] = fields[name].value
    return params


def generate_exception_report(e, path, params):
    response = Response()
    full_tb = traceback.extract_tb(sys.exc_info()[2])
    tb_str = ''
    for tb in full_tb:
        tb_str += "File '%s', line %s, in %s; " % (tb[0], tb[1], tb[2])
    report = {}
    report['exception'] = str(e)
    report['traceback'] = tb_str
    report['url'] = path.replace('/pico/', '/')
    report['params'] = dict([(k, _value_summary(params[k])) for k in params])
    log(json.dumps(report, indent=1))
    response.content = report
    response.status = '500 ' + str(e)
    return response


def _value_summary(value):
    s = repr(value)
    if len(s) > 100:
        s = s[:100] + '...'
    return s


def handle_api_v1(path, params, environ):
    if '/module/' in path:
        module_name = path.split('/')[2]
        return _load(module_name, params, environ)
    elif '/call/' in path:
        return call(params, environ)
    raise APIError()


def handle_api_v2(path, params, environ):
    # nice urls:
    #   /module_name/
    #   /module_name/function_name/?foo=bar
    #   /module_name/function_name/foo=bar # not implemented!
    #   /module_name/class_name/function_name/
    parts = [p for p in path.split('/') if p]
    if len(parts) == 1:
        return _load(parts[0], params, environ)
    elif len(parts) == 2:
        params['_module'] = parts[0]
        params['_function'] = parts[1]
        return call(params, environ)
    elif len(parts) == 3:
        params['_module'] = parts[0]
        params['_class'] = parts[1]
        params['_function'] = parts[2]
        return call(params, environ)
    raise APIError(path)


def handle_pico_js(path, params):
    if path == '/pico.js' or path == '/client.js':
        return serve_file(pico_path + 'client.js')
    raise APIError()


def not_found_error(path):
    response = Response()
    response.status = '404 NOT FOUND'
    response.content = '404 File not found'
    response.type = 'plaintext'
    return response


def wsgi_app(environ, start_response, enable_static=False):
    if environ['REQUEST_METHOD'] == 'OPTIONS':
        # This is to hanle the preflight request for CORS.
        # See https://developer.mozilla.org/en/http_access_control
        response = Response()
        response.status = "200 OK"
    else:
        params = extract_params(environ)
        log('------')
        path = environ['PATH_INFO'].split(environ['HTTP_HOST'])[-1]
        if BASE_PATH:
            path = path.split(BASE_PATH)[1]
        log(path)
        try:
            if '/pico/' in path:
                path = path.replace('/pico/', '/')
                try:
                    response = handle_api_v1(path, params, environ)
                except APIError:
                    try:
                        response = handle_pico_js(path, params)
                    except APIError:
                        try:
                            response = handle_api_v2(path, params, environ)
                        except APIError:
                            response = not_found_error(path)
            elif enable_static:
                try:
                    response = static_file_handler(path)
                except OSError, e:
                    response = not_found_error(path)
            else:
                response = not_found_error(path)
        except PicoError, e:
            response = e.response
        except Exception, e:
            response = generate_exception_report(e, path, params)
    start_response(response.status, response.headers)
    return response.output


def wsgi_dev_app(environ, start_response):
    return wsgi_app(environ, start_response, enable_static=True)


CACHE_PATH = './cache/'
BASE_PATH = ''
STATIC_URL_MAP = [
    ('^/(.*)$', './'),
]
DEFAULT = 'index.html'
RELOAD = True
STREAMING = False
SILENT = False

if __name__ == '__main__':
    main()

########NEW FILE########
