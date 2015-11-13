__FILENAME__ = helpers
import threading
import time
from tornadorpc import start_server, private, async
from tornado.httpclient import AsyncHTTPClient


class Tree(object):

    def power(self, base, power, modulo=None):
        result = pow(base, power, modulo)
        return result

    def _private(self):
        # Should not be callable
        return False


class TestHandler(object):

    tree = Tree()

    def add(self, x, y):
        return x+y

    @private
    def private(self):
        # Should not be callable
        return False

    def _private(self):
        # Should not be callable
        return False

    def internal_error(self):
        raise Exception("Yar matey!")

    @async
    def async(self, url):
        async_client = AsyncHTTPClient()
        async_client.fetch(url, self._handle_response)

    def _handle_response(self, response):
        self.result(response.code)


class TestServer(object):

    threads = {}

    @classmethod
    def start(cls, handler, port):
        # threading, while functional for testing the built-in python
        # clients, is an overly complicated solution for IOLoop based
        # servers. After implementing a tornado-based JSON-RPC client
        # and XML-RPC client, move this to an IOLoop based test case.
        if not cls.threads.get(port):
            cls.threads[port] = threading.Thread(
                target=start_server,
                args=[handler],
                kwargs={'port': port}
            )
            cls.threads[port].daemon = True
            cls.threads[port].start()
            # Giving it time to start up
            time.sleep(1)


class RPCTests(object):

    server = None
    handler = None
    io_loop = None
    port = 8002

    def setUp(self):
        super(RPCTests, self).setUp()
        self.server = TestServer.start(self.handler, self.port)

    def get_url(self):
        return 'http://localhost:%d' % self.port

    def get_client(self):
        raise NotImplementedError("Must return an XML / JSON RPC client.")

    def test_tree(self):
        client = self.get_client()
        result = client.tree.power(2, 6)
        self.assertEqual(result, 64)

    def test_add(self):
        client = self.get_client()
        result = client.add(5, 6)
        self.assertEqual(result, 11)

    def test_async(self):
        # this should be refactored to use Async RPC clients...
        url = 'http://www.google.com'
        client = self.get_client()
        result = client.async(url)
        self.assertEqual(result, 200)

########NEW FILE########
__FILENAME__ = test_async
import json
from tests.helpers import TestHandler
from tornado.httpclient import AsyncHTTPClient
from tornado.testing import AsyncHTTPTestCase
import tornado.web
from tornadorpc import async
from tornadorpc.xml import XMLRPCHandler
import xmlrpclib


class AsyncHandler(XMLRPCHandler, TestHandler):

    @async
    def async_method(self, url):
        async_client = AsyncHTTPClient()
        async_client.fetch(url, self._handle_response)

    @async
    def bad_async_method(self, url):
        async_client = AsyncHTTPClient()
        async_client.fetch(url, self._handle_response)
        return 5

    def _handle_response(self, response):
        self.result(json.loads(response.body))


class AsyncXMLRPCClient(object):

    def __init__(self, url, ioloop, fetcher):
        self._url = url
        self._ioloop = ioloop
        self._fetcher = fetcher

    def __getattr__(self, attribute):
        return Caller(attribute, self)

    def execute(self, method, params, keyword_params):
        if params and keyword_params:
            raise Exception(
                "Can't have both keyword and positional arguments.")
        arguments = params or keyword_params
        body = xmlrpclib.dumps(arguments, methodname=method)
        response = self._fetcher(self._url, method="POST", body=body)
        result, _ = xmlrpclib.loads(response.body)
        return result[0]


class Caller(object):

    def __init__(self, namespace, client):
        self._namespace = namespace
        self._client = client

    def __getattr__(self, namespace):
        self._namespace += "." + namespace
        return self

    def __call__(self, *args, **kwargs):
        return self._client.execute(self._namespace, args, kwargs)


class AsyncTests(AsyncHTTPTestCase):

    def get_app(self):

        class IndexHandler(tornado.web.RequestHandler):

            def get(self):
                self.finish({"foo": "bar"})

        return tornado.web.Application([
            ("/", IndexHandler),
            ("/RPC2", AsyncHandler)
        ])

    def get_client(self):
        return AsyncXMLRPCClient(
            url="/RPC2", ioloop=self.io_loop, fetcher=self.fetch)

    def test_async_method(self):
        client = self.get_client()
        result = client.async_method(
            "http://localhost:%d/" % (self.get_http_port()))
        self.assertEqual({"foo": "bar"}, result)

    def test_async_returns_non_none_raises_internal_error(self):
        client = self.get_client()
        try:
            client.bad_async_method(
                "http://localhost:%d/" % (self.get_http_port()))
            self.fail("xmlrpclib.Fault should have been raised.")
        except xmlrpclib.Fault, fault:
            self.assertEqual(-32603, fault.faultCode)

########NEW FILE########
__FILENAME__ = test_json
from tests.helpers import TestHandler, RPCTests
from tornadorpc.json import JSONRPCHandler
import jsonrpclib
import unittest


class JSONTestHandler(TestHandler, JSONRPCHandler):

    def order(self, a=1, b=2, c=3):
        return {'a': a, 'b': b, 'c': c}


class JSONRPCTests(RPCTests, unittest.TestCase):

    port = 8003
    handler = JSONTestHandler

    def get_client(self):
        client = jsonrpclib.Server('http://localhost:%d' % self.port)
        return client

    def test_private(self):
        client = self.get_client()
        self.assertRaises(jsonrpclib.ProtocolError, client.private)

    def test_order(self):
        client = self.get_client()
        self.assertEqual(
            client.order(), {'a': 1, 'b': 2, 'c': 3})
        self.assertEqual(
            client.order(a=10), {'a': 10, 'b': 2, 'c': 3})
        self.assertEqual(
            client.order(c=10), {'a': 1, 'b': 2, 'c': 10})
        self.assertEqual(
            client.order(a=10, b=11, c=12), {'a': 10, 'b': 11, 'c': 12})

########NEW FILE########
__FILENAME__ = test_utils
import unittest
from tornadorpc.utils import getcallargs


class TestCallArgs(unittest.TestCase):
    """ Tries various argument settings """

    def test_no_args(self):
        def test():
            pass
        kwargs, xtra = getcallargs(test)
        self.assertEqual(kwargs, {})
        self.assertEqual(xtra, [])

    def test_bad_no_args(self):
        def test():
            pass
        self.assertRaises(TypeError, getcallargs, test, 5)

    def test_positional_args(self):
        def test(a, b):
            pass
        kwargs, xtra = getcallargs(test, 5, 6)
        self.assertEqual(kwargs, {'a': 5, 'b': 6})
        self.assertEqual(xtra, [])

    def test_extra_positional_args(self):
        def test(a, b, *args):
            pass
        kwargs, xtra = getcallargs(test, 5, 6, 7, 8)
        self.assertEqual(kwargs, {'a': 5, 'b': 6})
        self.assertEqual(xtra, [7, 8])

    def test_bad_positional_args(self):
        def test(a, b):
            pass
        self.assertRaises(TypeError, getcallargs, test, 5)

    def test_keyword_args(self):
        def test(a, b):
            pass
        kwargs, xtra = getcallargs(test, a=5, b=6)
        self.assertEqual(kwargs, {'a': 5, 'b': 6})
        self.assertEqual(xtra, [])

    def test_extra_keyword_args(self):
        def test(a, b, **kwargs):
            pass
        kwargs, xtra = getcallargs(test, a=5, b=6, c=7, d=8)
        self.assertEqual(kwargs, {'a': 5, 'b': 6, 'c': 7, 'd': 8})
        self.assertEqual(xtra, [])

    def test_bad_keyword_args(self):
        def test(a, b):
            pass
        self.assertRaises(TypeError, getcallargs, test, a=1, b=2, c=5)

    def test_method(self):
        class Foo(object):
            def test(myself, a, b):
                pass
        foo = Foo()
        kwargs, xtra = getcallargs(foo.test, 5, 6)
        self.assertEqual(kwargs, {'a': 5, 'b': 6})
        self.assertEqual(xtra, [])

    def test_default(self):
        def test(a, b, default=None):
            pass
        kwargs, xtra = getcallargs(test, a=5, b=6)
        self.assertEqual(kwargs, {'a': 5, 'b': 6, 'default': None})
        self.assertEqual(xtra, [])

########NEW FILE########
__FILENAME__ = test_xml
import unittest
import xmlrpclib
import urllib2
from tornadorpc.xml import XMLRPCHandler

from tests.helpers import TestHandler, RPCTests


class XMLTestHandler(XMLRPCHandler, TestHandler):

    def return_fault(self, code, msg):
        return xmlrpclib.Fault(code, msg)


class XMLRPCTests(RPCTests, unittest.TestCase):

    handler = XMLTestHandler

    def get_client(self):
        client = xmlrpclib.ServerProxy(self.get_url())
        return client

    def test_private(self):
        client = self.get_client()
        try:
            client.private()
            self.fail('xmlrpclib.Fault should have been raised')
        except xmlrpclib.Fault, f:
            self.assertEqual(-32601, f.faultCode)

    def test_private_by_underscore(self):
        client = self.get_client()
        try:
            client._private()
            self.fail('xmlrpclib.Fault should have been raised')
        except xmlrpclib.Fault, f:
            self.assertEqual(-32601, f.faultCode)

    def test_invalid_params(self):
        client = self.get_client()
        try:
            client.return_fault('a', 'b', 'c')
            self.fail('xmlrpclib.Fault should have been raised')
        except xmlrpclib.Fault, f:
            self.assertEqual(-32602, f.faultCode)

    def test_internal_error(self):
        client = self.get_client()
        try:
            client.internal_error()
            self.fail('xmlrpclib.Fault should have been raised')
        except xmlrpclib.Fault, f:
            self.assertEqual(-32603, f.faultCode)

    def test_parse_error(self):
        try:
            urllib2.urlopen(self.get_url(), '<garbage/>')
        except xmlrpclib.Fault, f:
            self.assertEqual(-32700, f.faultCode)

    def test_handler_return_fault(self):
        client = self.get_client()
        fault_code = 100
        fault_string = 'Yar matey!'
        try:
            client.return_fault(fault_code, fault_string)
            self.fail('xmlrpclib.Fault should have been raised')
        except xmlrpclib.Fault, f:
            self.assertEqual(fault_code, f.faultCode)
            self.assertEqual(fault_string, f.faultString)

########NEW FILE########
__FILENAME__ = base
"""
============================
Base RPC Handler for Tornado
============================
This is a basic server implementation, designed for use within the
Tornado framework. The classes in this library should not be used
directly, but rather though the XML or JSON RPC implementations.
You can use the utility functions like 'private' and 'start_server'.
"""

from tornado.web import RequestHandler
import tornado.web
import tornado.ioloop
import tornado.httpserver
import types
import traceback
from tornadorpc.utils import getcallargs


# Configuration element
class Config(object):
    verbose = True
    short_errors = True

config = Config()


class BaseRPCParser(object):
    """
    This class is responsible for managing the request, dispatch,
    and response formatting of the system. It is tied into the
    _RPC_ attribute of the BaseRPCHandler (or subclasses) and
    populated as necessary throughout the request. Use the
    .faults attribute to take advantage of the built-in error
    codes.
    """
    content_type = 'text/plain'

    def __init__(self, library, encode=None, decode=None):
        # Attaches the RPC library and encode / decode functions.
        self.library = library
        if not encode:
            encode = getattr(library, 'dumps')
        if not decode:
            decode = getattr(library, 'loads')
        self.encode = encode
        self.decode = decode
        self.requests_in_progress = 0
        self.responses = []

    @property
    def faults(self):
        # Grabs the fault tree on request
        return Faults(self)

    def run(self, handler, request_body):
        """
        This is the main loop -- it passes the request body to
        the parse_request method, and then takes the resulting
        method(s) and parameters and passes them to the appropriate
        method on the parent Handler class, then parses the response
        into text and returns it to the parent Handler to send back
        to the client.
        """
        self.handler = handler
        try:
            requests = self.parse_request(request_body)
        except:
            self.traceback()
            return self.handler.result(self.faults.parse_error())
        if not isinstance(requests, types.TupleType):
            # SHOULD be the result of a fault call,
            # according tothe parse_request spec below.
            if isinstance(requests, basestring):
                # Should be the response text of a fault
                # This will break in Python 3.x
                return requests
            elif hasattr(requests, 'response'):
                # Fault types should have a 'response' method
                return requests.response()
            elif hasattr(requests, 'faultCode'):
                # XML-RPC fault types need to be properly dispatched. This
                # should only happen if there was an error parsing the
                # request above.
                return self.handler.result(requests)
            else:
                # No idea, hopefully the handler knows what it
                # is doing.
                return requests
        self.handler._requests = len(requests)
        for request in requests:
            self.dispatch(request[0], request[1])

    def dispatch(self, method_name, params):
        """
        This method walks the attribute tree in the method
        and passes the parameters, either in positional or
        keyword form, into the appropriate method on the
        Handler class. Currently supports only positional
        or keyword arguments, not mixed.
        """
        if hasattr(RequestHandler, method_name):
            # Pre-existing, not an implemented attribute
            return self.handler.result(self.faults.method_not_found())
        method = self.handler
        method_list = dir(method)
        method_list.sort()
        attr_tree = method_name.split('.')
        try:
            for attr_name in attr_tree:
                method = self.check_method(attr_name, method)
        except AttributeError:
            return self.handler.result(self.faults.method_not_found())
        if not callable(method):
            # Not callable, so not a method
            return self.handler.result(self.faults.method_not_found())
        if method_name.startswith('_') or \
                getattr(method, 'private', False) is True:
            # No, no. That's private.
            return self.handler.result(self.faults.method_not_found())
        args = []
        kwargs = {}
        if isinstance(params, dict):
            # The parameters are keyword-based
            kwargs = params
        elif type(params) in (list, tuple):
            # The parameters are positional
            args = params
        else:
            # Bad argument formatting?
            return self.handler.result(self.faults.invalid_params())
        # Validating call arguments
        try:
            final_kwargs, extra_args = getcallargs(method, *args, **kwargs)
        except TypeError:
            return self.handler.result(self.faults.invalid_params())
        try:
            response = method(*extra_args, **final_kwargs)
        except Exception:
            self.traceback(method_name, params)
            return self.handler.result(self.faults.internal_error())

        if getattr(method, 'async', False):
            # Asynchronous response -- the method should have called
            # self.result(RESULT_VALUE)
            if response is not None:
                # This should be deprecated to use self.result
                return self.handler.result(self.faults.internal_error())
        else:
            # Synchronous result -- we call result manually.
            return self.handler.result(response)

    def response(self, handler):
        """
        This is the callback for a single finished dispatch.
        Once all the dispatches have been run, it calls the
        parser library to parse responses and then calls the
        handler's async method.
        """
        handler._requests -= 1
        if handler._requests > 0:
            return
        # We are finished with requests, send response
        if handler._RPC_finished:
            # We've already sent the response
            raise Exception("Error trying to send response twice.")
        handler._RPC_finished = True
        responses = tuple(handler._results)
        response_text = self.parse_responses(responses)
        if type(response_text) not in types.StringTypes:
            # Likely a fault, or something messed up
            response_text = self.encode(response_text)
        # Calling the async callback
        handler.on_result(response_text)

    def traceback(self, method_name='REQUEST', params=[]):
        err_lines = traceback.format_exc().splitlines()
        err_title = "ERROR IN %s" % method_name
        if len(params) > 0:
            err_title = '%s - (PARAMS: %s)' % (err_title, repr(params))
        err_sep = ('-'*len(err_title))[:79]
        err_lines = [err_sep, err_title, err_sep]+err_lines
        if config.verbose:
            if len(err_lines) >= 7 and config.short_errors:
                # Minimum number of lines to see what happened
                # Plus title and separators
                print '\n'.join(err_lines[0:4]+err_lines[-3:])
            else:
                print '\n'.join(err_lines)
        # Log here
        return

    def parse_request(self, request_body):
        """
        Extend this on the implementing protocol. If it
        should error out, return the output of the
        'self.faults.fault_name' response. Otherwise,
        it MUST return a TUPLE of TUPLE. Each entry
        tuple must have the following structure:
        ('method_name', params)
        ...where params is a list or dictionary of
        arguments (positional or keyword, respectively.)
        So, the result should look something like
        the following:
        ( ('add', [5,4]), ('add', {'x':5, 'y':4}) )
        """
        return ([], [])

    def parse_responses(self, responses):
        """
        Extend this on the implementing protocol. It must
        return a response that can be returned as output to
        the client.
        """
        return self.encode(responses, methodresponse=True)

    def check_method(self, attr_name, obj):
        """
        Just checks to see whether an attribute is private
        (by the decorator or by a leading underscore) and
        returns boolean result.
        """
        if attr_name.startswith('_'):
            raise AttributeError('Private object or method.')
        attr = getattr(obj, attr_name)

        if getattr(attr, 'private', False):
            raise AttributeError('Private object or method.')
        return attr


class BaseRPCHandler(RequestHandler):
    """
    This is the base handler to be subclassed by the actual
    implementations and by the end user.
    """
    _RPC_ = None
    _results = None
    _requests = 0
    _RPC_finished = False

    @tornado.web.asynchronous
    def post(self):
        # Very simple -- dispatches request body to the parser
        # and returns the output
        self._results = []
        request_body = self.request.body
        self._RPC_.run(self, request_body)

    def result(self, result, *results):
        """ Use this to return a result. """
        if results:
            results = [result] + results
        else:
            results = result
        self._results.append(results)
        self._RPC_.response(self)

    def on_result(self, response_text):
        """ Asynchronous callback. """
        self.set_header('Content-Type', self._RPC_.content_type)
        self.finish(response_text)


class FaultMethod(object):
    """
    This is the 'dynamic' fault method so that the message can
    be changed on request from the parser.faults call.
    """
    def __init__(self, fault, code, message):
        self.fault = fault
        self.code = code
        self.message = message

    def __call__(self, message=None):
        if message:
            self.message = message
        return self.fault(self.code, self.message)


class Faults(object):
    """
    This holds the codes and messages for the RPC implementation.
    It is attached (dynamically) to the Parser when called via the
    parser.faults query, and returns a FaultMethod to be called so
    that the message can be changed. If the 'dynamic' attribute is
    not a key in the codes list, then it will error.

    USAGE:
        parser.fault.parse_error('Error parsing content.')

    If no message is passed in, it will check the messages dictionary
    for the same key as the codes dict. Otherwise, it just prettifies
    the code 'key' from the codes dict.

    """
    codes = {
        'parse_error': -32700,
        'method_not_found': -32601,
        'invalid_request': -32600,
        'invalid_params': -32602,
        'internal_error': -32603
    }

    messages = {}

    def __init__(self, parser, fault=None):
        self.library = parser.library
        self.fault = fault
        if not self.fault:
            self.fault = getattr(self.library, 'Fault')

    def __getattr__(self, attr):
        message = 'Error'
        if attr in self.messages.keys():
            message = self.messages[attr]
        else:
            message = ' '.join(map(str.capitalize, attr.split('_')))
        fault = FaultMethod(self.fault, self.codes[attr], message)
        return fault


"""
Utility Functions
"""


def private(func):
    """
    Use this to make a method private.
    It is intended to be used as a decorator.
    If you wish to make a method tree private, just
    create and set the 'private' variable to True
    on the tree object itself.
    """
    func.private = True
    return func


def async(func):
    """
    Use this to make a method asynchronous
    It is intended to be used as a decorator.
    Make sure you call "self.result" on any
    async method. Also, trees do not currently
    support async methods.
    """
    func.async = True
    return func


def start_server(handlers, route=r'/', port=8080):
    """
    This is just a friendly wrapper around the default
    Tornado instantiation calls. It simplifies the imports
    and setup calls you'd make otherwise.
    USAGE:
        start_server(handler_class, route=r'/', port=8181)
    """
    if type(handlers) not in (types.ListType, types.TupleType):
        handler = handlers
        handlers = [(route, handler)]
        if route != '/RPC2':
            # friendly addition for /RPC2 if it's the only one
            handlers.append(('/RPC2', handler))
    application = tornado.web.Application(handlers)
    http_server = tornado.httpserver.HTTPServer(application)
    http_server.listen(port)
    loop_instance = tornado.ioloop.IOLoop.instance()
    """ Setting the '_server' attribute if not set """
    for (route, handler) in handlers:
        try:
            setattr(handler, '_server', loop_instance)
        except AttributeError:
            handler._server = loop_instance
    loop_instance.start()
    return loop_instance


"""
The following is a test implementation which should work
for both the XMLRPC and the JSONRPC clients.
"""


class TestMethodTree(object):
    def power(self, x, y=2):
        return pow(x, y)

    @private
    def private(self):
        # Shouldn't be called
        return False


class TestRPCHandler(BaseRPCHandler):

    _RPC_ = None

    def add(self, x, y):
        return x+y

    def ping(self, x):
        return x

    def noargs(self):
        return 'Works!'

    tree = TestMethodTree()

    def _private(self):
        # Shouldn't be called
        return False

    @private
    def private(self):
        # Also shouldn't be called
        return False

########NEW FILE########
__FILENAME__ = json
"""
============================
JSON-RPC Handler for Tornado
============================
This is a JSON-RPC server implementation, designed for use within the
Tornado framework. Usage is pretty simple:

>>> from tornadorpc.json import JSONRPCHandler
>>> from tornadorpc import start_server
>>>
>>> class handler(JSONRPCHandler):
>>> ... def add(self, x, y):
>>> ....... return x+y
>>>
>>> start_server(handler, port=8484)

It requires the jsonrpclib, which you can get from:

    http://github.com/joshmarshall/jsonrpclib

Also, you will need one of the following JSON modules:
* cjson
* simplejson

From Python 2.6 on, simplejson is included in the standard
distribution as the "json" module.
"""

from tornadorpc.base import BaseRPCParser, BaseRPCHandler
import jsonrpclib
from jsonrpclib.jsonrpc import isbatch, isnotification, Fault
from jsonrpclib.jsonrpc import dumps, loads


class JSONRPCParser(BaseRPCParser):

    content_type = 'application/json-rpc'

    def parse_request(self, request_body):
        try:
            request = loads(request_body)
        except:
            # Bad request formatting
            self.traceback()
            return self.faults.parse_error()
        self._requests = request
        self._batch = False
        request_list = []
        if isbatch(request):
            self._batch = True
            for req in request:
                req_tuple = (req['method'], req.get('params', []))
                request_list.append(req_tuple)
        else:
            self._requests = [request]
            request_list.append(
                (request['method'], request.get('params', []))
            )
        return tuple(request_list)

    def parse_responses(self, responses):
        if isinstance(responses, Fault):
            return dumps(responses)
        if len(responses) != len(self._requests):
            return dumps(self.faults.internal_error())
        response_list = []
        for i in range(0, len(responses)):
            request = self._requests[i]
            response = responses[i]
            if isnotification(request):
                # Even in batches, notifications have no
                # response entry
                continue
            rpcid = request['id']
            version = jsonrpclib.config.version
            if 'jsonrpc' not in request.keys():
                version = 1.0
            try:
                response_json = dumps(
                    response, version=version,
                    rpcid=rpcid, methodresponse=True
                )
            except TypeError:
                return dumps(
                    self.faults.server_error(),
                    rpcid=rpcid, version=version
                )
            response_list.append(response_json)
        if not self._batch:
            # Ensure it wasn't a batch to begin with, then
            # return 1 or 0 responses depending on if it was
            # a notification.
            if len(response_list) < 1:
                return ''
            return response_list[0]
        # Batch, return list
        return '[ %s ]' % ', '.join(response_list)


class JSONRPCLibraryWrapper(object):

    dumps = dumps
    loads = loads
    Fault = Fault


class JSONRPCHandler(BaseRPCHandler):
    """
    Subclass this to add methods -- you can treat them
    just like normal methods, this handles the JSON formatting.
    """
    _RPC_ = JSONRPCParser(JSONRPCLibraryWrapper)


if __name__ == '__main__':
    # Example Implementation
    import sys
    from tornadorpc.base import start_server
    from tornadorpc.base import TestRPCHandler

    class TestJSONRPC(TestRPCHandler):
        _RPC_ = JSONRPCParser(JSONRPCLibraryWrapper)

    port = 8181
    if len(sys.argv) > 1:
        port = int(sys.argv[1])

    print 'Starting server on port %s' % port
    start_server(TestJSONRPC, port=port)

########NEW FILE########
__FILENAME__ = utils
"""
Various utilities for the TornadoRPC library.
"""

import inspect


def getcallargs(func, *positional, **named):
    """
    Simple implementation of inspect.getcallargs function in
    the Python 2.7 standard library.

    Takes a function and the position and keyword arguments and
    returns a dictionary with the appropriate named arguments.
    Raises an exception if invalid arguments are passed.
    """
    args, varargs, varkw, defaults = inspect.getargspec(func)

    final_kwargs = {}
    extra_args = []
    has_self = inspect.ismethod(func) and func.im_self is not None
    if has_self:
        args.pop(0)

    # (Since our RPC supports only positional OR named.)
    if named:
        for key, value in named.iteritems():
            arg_key = None
            try:
                arg_key = args[args.index(key)]
            except ValueError:
                if not varkw:
                    raise TypeError("Keyword argument '%s' not valid" % key)
            if key in final_kwargs.keys():
                message = "Keyword argument '%s' used more than once" % key
                raise TypeError(message)
            final_kwargs[key] = value
    else:
        for i in range(len(positional)):
            value = positional[i]
            arg_key = None
            try:
                arg_key = args[i]
            except IndexError:
                if not varargs:
                    raise TypeError("Too many positional arguments")
            if arg_key:
                final_kwargs[arg_key] = value
            else:
                extra_args.append(value)
    if defaults:
        for kwarg, default in zip(args[-len(defaults):], defaults):
            final_kwargs.setdefault(kwarg, default)
    for arg in args:
        if arg not in final_kwargs:
            raise TypeError("Not all arguments supplied. (%s)", arg)
    return final_kwargs, extra_args

########NEW FILE########
__FILENAME__ = xml
"""
===========================
XML-RPC Handler for Tornado
===========================
This is a XML-RPC server implementation, designed for use within the
Tornado framework. Usage is pretty simple:

>>> from tornadorpc.xml import XMLRPCHandler
>>> from tornadorpc import start_server
>>>
>>> class handler(XMLRPCHandler):
>>> ... def add(self, x, y):
>>> ....... return x+y
>>>
>>> start_server(handler, port=8484)

It requires the xmlrpclib, which is built-in to Python distributions
from version 2.3 on.

"""

from tornadorpc.base import BaseRPCParser, BaseRPCHandler
import xmlrpclib


class XMLRPCSystem(object):
    # Multicall functions and, eventually, introspection

    def __init__(self, handler):
        self._dispatch = handler._RPC_.dispatch

    def multicall(self, calls):
        for call in calls:
            method_name = call['methodName']
            params = call['params']
            self._dispatch(method_name, params)


class XMLRPCParser(BaseRPCParser):

    content_type = 'text/xml'

    def parse_request(self, request_body):
        try:
            params, method_name = xmlrpclib.loads(request_body)
        except:
            # Bad request formatting, bad.
            return self.faults.parse_error()
        return ((method_name, params),)

    def parse_responses(self, responses):
        try:
            if isinstance(responses[0], xmlrpclib.Fault):
                return xmlrpclib.dumps(responses[0])
        except IndexError:
            pass
        try:
            response_xml = xmlrpclib.dumps(responses, methodresponse=True)
        except TypeError:
            return self.faults.internal_error()
        return response_xml


class XMLRPCHandler(BaseRPCHandler):
    """
    Subclass this to add methods -- you can treat them
    just like normal methods, this handles the XML formatting.
    """
    _RPC_ = XMLRPCParser(xmlrpclib)

    @property
    def system(self):
        return XMLRPCSystem(self)


if __name__ == '__main__':
    # Test implementation
    from tornadorpc.base import TestRPCHandler, start_server
    import sys

    port = 8282
    if len(sys.argv) > 1:
        port = int(sys.argv[1])

    class TestXMLRPC(TestRPCHandler):
        _RPC_ = XMLRPCParser(xmlrpclib)

        @property
        def system(self):
            return XMLRPCSystem(self)

    print 'Starting server on port %s' % port
    start_server(TestXMLRPC, port=port)

########NEW FILE########
