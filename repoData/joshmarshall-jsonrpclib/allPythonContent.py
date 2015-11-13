__FILENAME__ = config
import sys

class LocalClasses(dict):
    def add(self, cls):
        self[cls.__name__] = cls

class Config(object):
    """
    This is pretty much used exclusively for the 'jsonclass' 
    functionality... set use_jsonclass to False to turn it off.
    You can change serialize_method and ignore_attribute, or use
    the local_classes.add(class) to include "local" classes.
    """
    use_jsonclass = True
    # Change to False to keep __jsonclass__ entries raw.
    serialize_method = '_serialize'
    # The serialize_method should be a string that references the
    # method on a custom class object which is responsible for 
    # returning a tuple of the constructor arguments and a dict of
    # attributes.
    ignore_attribute = '_ignore'
    # The ignore attribute should be a string that references the
    # attribute on a custom class object which holds strings and / or
    # references of the attributes the class translator should ignore.
    classes = LocalClasses()
    # The list of classes to use for jsonclass translation.
    version = 2.0
    # Version of the JSON-RPC spec to support
    user_agent = 'jsonrpclib/0.1 (Python %s)' % \
        '.'.join([str(ver) for ver in sys.version_info[0:3]])
    # User agent to use for calls.
    _instance = None
    
    @classmethod
    def instance(cls):
        if not cls._instance:
            cls._instance = cls()
        return cls._instance

########NEW FILE########
__FILENAME__ = history
class History(object):
    """
    This holds all the response and request objects for a
    session. A server using this should call "clear" after
    each request cycle in order to keep it from clogging 
    memory.
    """
    requests = []
    responses = []
    _instance = None
    
    @classmethod
    def instance(cls):
        if not cls._instance:
            cls._instance = cls()
        return cls._instance

    def add_response(self, response_obj):
        self.responses.append(response_obj)
    
    def add_request(self, request_obj):
        self.requests.append(request_obj)

    @property
    def request(self):
        if len(self.requests) == 0:
            return None
        else:
            return self.requests[-1]

    @property
    def response(self):
        if len(self.responses) == 0:
            return None
        else:
            return self.responses[-1]

    def clear(self):
        del self.requests[:]
        del self.responses[:]

########NEW FILE########
__FILENAME__ = jsonclass
import types
import inspect
import re
import traceback

from jsonrpclib import config

iter_types = [
    types.DictType,
    types.ListType,
    types.TupleType
]

string_types = [
    types.StringType,
    types.UnicodeType
]

numeric_types = [
    types.IntType,
    types.LongType,
    types.FloatType
]

value_types = [
    types.BooleanType,
    types.NoneType
]

supported_types = iter_types+string_types+numeric_types+value_types
invalid_module_chars = r'[^a-zA-Z0-9\_\.]'

class TranslationError(Exception):
    pass

def dump(obj, serialize_method=None, ignore_attribute=None, ignore=[]):
    if not serialize_method:
        serialize_method = config.serialize_method
    if not ignore_attribute:
        ignore_attribute = config.ignore_attribute
    obj_type = type(obj)
    # Parse / return default "types"...
    if obj_type in numeric_types+string_types+value_types:
        return obj
    if obj_type in iter_types:
        if obj_type in (types.ListType, types.TupleType):
            new_obj = []
            for item in obj:
                new_obj.append(dump(item, serialize_method,
                                     ignore_attribute, ignore))
            if obj_type is types.TupleType:
                new_obj = tuple(new_obj)
            return new_obj
        # It's a dict...
        else:
            new_obj = {}
            for key, value in obj.iteritems():
                new_obj[key] = dump(value, serialize_method,
                                     ignore_attribute, ignore)
            return new_obj
    # It's not a standard type, so it needs __jsonclass__
    module_name = inspect.getmodule(obj).__name__
    class_name = obj.__class__.__name__
    json_class = class_name
    if module_name not in ['', '__main__']:
        json_class = '%s.%s' % (module_name, json_class)
    return_obj = {"__jsonclass__":[json_class,]}
    # If a serialization method is defined..
    if serialize_method in dir(obj):
        # Params can be a dict (keyword) or list (positional)
        # Attrs MUST be a dict.
        serialize = getattr(obj, serialize_method)
        params, attrs = serialize()
        return_obj['__jsonclass__'].append(params)
        return_obj.update(attrs)
        return return_obj
    # Otherwise, try to figure it out
    # Obviously, we can't assume to know anything about the
    # parameters passed to __init__
    return_obj['__jsonclass__'].append([])
    attrs = {}
    ignore_list = getattr(obj, ignore_attribute, [])+ignore
    for attr_name, attr_value in obj.__dict__.iteritems():
        if type(attr_value) in supported_types and \
                attr_name not in ignore_list and \
                attr_value not in ignore_list:
            attrs[attr_name] = dump(attr_value, serialize_method,
                                     ignore_attribute, ignore)
    return_obj.update(attrs)
    return return_obj

def load(obj):
    if type(obj) in string_types+numeric_types+value_types:
        return obj
    if type(obj) is types.ListType:
        return_list = []
        for entry in obj:
            return_list.append(load(entry))
        return return_list
    # Othewise, it's a dict type
    if '__jsonclass__' not in obj.keys():
        return_dict = {}
        for key, value in obj.iteritems():
            new_value = load(value)
            return_dict[key] = new_value
        return return_dict
    # It's a dict, and it's a __jsonclass__
    orig_module_name = obj['__jsonclass__'][0]
    params = obj['__jsonclass__'][1]
    if orig_module_name == '':
        raise TranslationError('Module name empty.')
    json_module_clean = re.sub(invalid_module_chars, '', orig_module_name)
    if json_module_clean != orig_module_name:
        raise TranslationError('Module name %s has invalid characters.' %
                               orig_module_name)
    json_module_parts = json_module_clean.split('.')
    json_class = None
    if len(json_module_parts) == 1:
        # Local class name -- probably means it won't work
        if json_module_parts[0] not in config.classes.keys():
            raise TranslationError('Unknown class or module %s.' %
                                   json_module_parts[0])
        json_class = config.classes[json_module_parts[0]]
    else:
        json_class_name = json_module_parts.pop()
        json_module_tree = '.'.join(json_module_parts)
        try:
            temp_module = __import__(json_module_tree)
        except ImportError:
            raise TranslationError('Could not import %s from module %s.' %
                                   (json_class_name, json_module_tree))

        # The returned class is the top-level module, not the one we really
        # want.  (E.g., if we import a.b.c, we now have a.)  Walk through other
        # path components to get to b and c.
        for i in json_module_parts[1:]:
            temp_module = getattr(temp_module, i)

        json_class = getattr(temp_module, json_class_name)
    # Creating the object...
    new_obj = None
    if type(params) is types.ListType:
        new_obj = json_class(*params)
    elif type(params) is types.DictType:
        new_obj = json_class(**params)
    else:
        raise TranslationError('Constructor args must be a dict or list.')
    for key, value in obj.iteritems():
        if key == '__jsonclass__':
            continue
        setattr(new_obj, key, value)
    return new_obj

########NEW FILE########
__FILENAME__ = jsonrpc
"""
Licensed under the Apache License, Version 2.0 (the "License"); 
you may not use this file except in compliance with the License. 
You may obtain a copy of the License at 

   http://www.apache.org/licenses/LICENSE-2.0 

Unless required by applicable law or agreed to in writing, software 
distributed under the License is distributed on an "AS IS" BASIS, 
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. 
See the License for the specific language governing permissions and 
limitations under the License. 

============================
JSONRPC Library (jsonrpclib)
============================

This library is a JSON-RPC v.2 (proposed) implementation which
follows the xmlrpclib API for portability between clients. It
uses the same Server / ServerProxy, loads, dumps, etc. syntax,
while providing features not present in XML-RPC like:

* Keyword arguments
* Notifications
* Versioning
* Batches and batch notifications

Eventually, I'll add a SimpleXMLRPCServer compatible library,
and other things to tie the thing off nicely. :)

For a quick-start, just open a console and type the following,
replacing the server address, method, and parameters 
appropriately.
>>> import jsonrpclib
>>> server = jsonrpclib.Server('http://localhost:8181')
>>> server.add(5, 6)
11
>>> server._notify.add(5, 6)
>>> batch = jsonrpclib.MultiCall(server)
>>> batch.add(3, 50)
>>> batch.add(2, 3)
>>> batch._notify.add(3, 5)
>>> batch()
[53, 5]

See http://code.google.com/p/jsonrpclib/ for more info.
"""

import types
import sys
from xmlrpclib import Transport as XMLTransport
from xmlrpclib import SafeTransport as XMLSafeTransport
from xmlrpclib import ServerProxy as XMLServerProxy
from xmlrpclib import _Method as XML_Method
import time
import string
import random

# Library includes
import jsonrpclib
from jsonrpclib import config
from jsonrpclib import history

# JSON library importing
cjson = None
json = None
try:
    import cjson
except ImportError:
    try:
        import json
    except ImportError:
        try:
            import simplejson as json
        except ImportError:
            raise ImportError(
                'You must have the cjson, json, or simplejson ' +
                'module(s) available.'
            )

IDCHARS = string.ascii_lowercase+string.digits

class UnixSocketMissing(Exception):
    """ 
    Just a properly named Exception if Unix Sockets usage is 
    attempted on a platform that doesn't support them (Windows)
    """
    pass

#JSON Abstractions

def jdumps(obj, encoding='utf-8'):
    # Do 'serialize' test at some point for other classes
    global cjson
    if cjson:
        return cjson.encode(obj)
    else:
        return json.dumps(obj, encoding=encoding)

def jloads(json_string):
    global cjson
    if cjson:
        return cjson.decode(json_string)
    else:
        return json.loads(json_string)


# XMLRPClib re-implementations

class ProtocolError(Exception):
    pass

class TransportMixIn(object):
    """ Just extends the XMLRPC transport where necessary. """
    user_agent = config.user_agent
    # for Python 2.7 support
    _connection = None

    def send_content(self, connection, request_body):
        connection.putheader("Content-Type", "application/json-rpc")
        connection.putheader("Content-Length", str(len(request_body)))
        connection.endheaders()
        if request_body:
            connection.send(request_body)

    def getparser(self):
        target = JSONTarget()
        return JSONParser(target), target

class JSONParser(object):
    def __init__(self, target):
        self.target = target

    def feed(self, data):
        self.target.feed(data)

    def close(self):
        pass

class JSONTarget(object):
    def __init__(self):
        self.data = []

    def feed(self, data):
        self.data.append(data)

    def close(self):
        return ''.join(self.data)

class Transport(TransportMixIn, XMLTransport):
    pass

class SafeTransport(TransportMixIn, XMLSafeTransport):
    pass
from httplib import HTTP, HTTPConnection
from socket import socket

USE_UNIX_SOCKETS = False

try: 
    from socket import AF_UNIX, SOCK_STREAM
    USE_UNIX_SOCKETS = True
except ImportError:
    pass
    
if (USE_UNIX_SOCKETS):
    
    class UnixHTTPConnection(HTTPConnection):
        def connect(self):
            self.sock = socket(AF_UNIX, SOCK_STREAM)
            self.sock.connect(self.host)

    class UnixHTTP(HTTP):
        _connection_class = UnixHTTPConnection

    class UnixTransport(TransportMixIn, XMLTransport):
        def make_connection(self, host):
            import httplib
            host, extra_headers, x509 = self.get_host_info(host)
            return UnixHTTP(host)

    
class ServerProxy(XMLServerProxy):
    """
    Unfortunately, much more of this class has to be copied since
    so much of it does the serialization.
    """

    def __init__(self, uri, transport=None, encoding=None, 
                 verbose=0, version=None):
        import urllib
        if not version:
            version = config.version
        self.__version = version
        schema, uri = urllib.splittype(uri)
        if schema not in ('http', 'https', 'unix'):
            raise IOError('Unsupported JSON-RPC protocol.')
        if schema == 'unix':
            if not USE_UNIX_SOCKETS:
                # Don't like the "generic" Exception...
                raise UnixSocketMissing("Unix sockets not available.")
            self.__host = uri
            self.__handler = '/'
        else:
            self.__host, self.__handler = urllib.splithost(uri)
            if not self.__handler:
                # Not sure if this is in the JSON spec?
                #self.__handler = '/'
                self.__handler == '/'
        if transport is None:
            if schema == 'unix':
                transport = UnixTransport()
            elif schema == 'https':
                transport = SafeTransport()
            else:
                transport = Transport()
        self.__transport = transport
        self.__encoding = encoding
        self.__verbose = verbose

    def _request(self, methodname, params, rpcid=None):
        request = dumps(params, methodname, encoding=self.__encoding,
                        rpcid=rpcid, version=self.__version)
        response = self._run_request(request)
        check_for_errors(response)
        return response['result']

    def _request_notify(self, methodname, params, rpcid=None):
        request = dumps(params, methodname, encoding=self.__encoding,
                        rpcid=rpcid, version=self.__version, notify=True)
        response = self._run_request(request, notify=True)
        check_for_errors(response)
        return

    def _run_request(self, request, notify=None):
        history.add_request(request)

        response = self.__transport.request(
            self.__host,
            self.__handler,
            request,
            verbose=self.__verbose
        )
        
        # Here, the XMLRPC library translates a single list
        # response to the single value -- should we do the
        # same, and require a tuple / list to be passed to
        # the response object, or expect the Server to be 
        # outputting the response appropriately?
        
        history.add_response(response)
        if not response:
            return None
        return_obj = loads(response)
        return return_obj

    def __getattr__(self, name):
        # Same as original, just with new _Method reference
        return _Method(self._request, name)

    @property
    def _notify(self):
        # Just like __getattr__, but with notify namespace.
        return _Notify(self._request_notify)


class _Method(XML_Method):
    
    def __call__(self, *args, **kwargs):
        if len(args) > 0 and len(kwargs) > 0:
            raise ProtocolError('Cannot use both positional ' +
                'and keyword arguments (according to JSON-RPC spec.)')
        if len(args) > 0:
            return self.__send(self.__name, args)
        else:
            return self.__send(self.__name, kwargs)

    def __getattr__(self, name):
        self.__name = '%s.%s' % (self.__name, name)
        return self
        # The old method returned a new instance, but this seemed wasteful.
        # The only thing that changes is the name.
        #return _Method(self.__send, "%s.%s" % (self.__name, name))

class _Notify(object):
    def __init__(self, request):
        self._request = request

    def __getattr__(self, name):
        return _Method(self._request, name)
        
# Batch implementation

class MultiCallMethod(object):
    
    def __init__(self, method, notify=False):
        self.method = method
        self.params = []
        self.notify = notify

    def __call__(self, *args, **kwargs):
        if len(kwargs) > 0 and len(args) > 0:
            raise ProtocolError('JSON-RPC does not support both ' +
                                'positional and keyword arguments.')
        if len(kwargs) > 0:
            self.params = kwargs
        else:
            self.params = args

    def request(self, encoding=None, rpcid=None):
        return dumps(self.params, self.method, version=2.0,
                     encoding=encoding, rpcid=rpcid, notify=self.notify)

    def __repr__(self):
        return '%s' % self.request()
        
    def __getattr__(self, method):
        new_method = '%s.%s' % (self.method, method)
        self.method = new_method
        return self

class MultiCallNotify(object):
    
    def __init__(self, multicall):
        self.multicall = multicall

    def __getattr__(self, name):
        new_job = MultiCallMethod(name, notify=True)
        self.multicall._job_list.append(new_job)
        return new_job

class MultiCallIterator(object):
    
    def __init__(self, results):
        self.results = results

    def __iter__(self):
        for i in range(0, len(self.results)):
            yield self[i]
        raise StopIteration

    def __getitem__(self, i):
        item = self.results[i]
        check_for_errors(item)
        return item['result']

    def __len__(self):
        return len(self.results)

class MultiCall(object):
    
    def __init__(self, server):
        self._server = server
        self._job_list = []

    def _request(self):
        if len(self._job_list) < 1:
            # Should we alert? This /is/ pretty obvious.
            return
        request_body = '[ %s ]' % ','.join([job.request() for
                                          job in self._job_list])
        responses = self._server._run_request(request_body)
        del self._job_list[:]
        if not responses:
            responses = []
        return MultiCallIterator(responses)

    @property
    def _notify(self):
        return MultiCallNotify(self)

    def __getattr__(self, name):
        new_job = MultiCallMethod(name)
        self._job_list.append(new_job)
        return new_job

    __call__ = _request

# These lines conform to xmlrpclib's "compatibility" line. 
# Not really sure if we should include these, but oh well.
Server = ServerProxy

class Fault(object):
    # JSON-RPC error class
    def __init__(self, code=-32000, message='Server error', rpcid=None):
        self.faultCode = code
        self.faultString = message
        self.rpcid = rpcid

    def error(self):
        return {'code':self.faultCode, 'message':self.faultString}

    def response(self, rpcid=None, version=None):
        if not version:
            version = config.version
        if rpcid:
            self.rpcid = rpcid
        return dumps(
            self, methodresponse=True, rpcid=self.rpcid, version=version
        )

    def __repr__(self):
        return '<Fault %s: %s>' % (self.faultCode, self.faultString)

def random_id(length=8):
    return_id = ''
    for i in range(length):
        return_id += random.choice(IDCHARS)
    return return_id

class Payload(dict):
    def __init__(self, rpcid=None, version=None):
        if not version:
            version = config.version
        self.id = rpcid
        self.version = float(version)
    
    def request(self, method, params=[]):
        if type(method) not in types.StringTypes:
            raise ValueError('Method name must be a string.')
        if not self.id:
            self.id = random_id()
        request = { 'id':self.id, 'method':method }
        if params:
            request['params'] = params
        if self.version >= 2:
            request['jsonrpc'] = str(self.version)
        return request

    def notify(self, method, params=[]):
        request = self.request(method, params)
        if self.version >= 2:
            del request['id']
        else:
            request['id'] = None
        return request

    def response(self, result=None):
        response = {'result':result, 'id':self.id}
        if self.version >= 2:
            response['jsonrpc'] = str(self.version)
        else:
            response['error'] = None
        return response

    def error(self, code=-32000, message='Server error.'):
        error = self.response()
        if self.version >= 2:
            del error['result']
        else:
            error['result'] = None
        error['error'] = {'code':code, 'message':message}
        return error

def dumps(params=[], methodname=None, methodresponse=None, 
        encoding=None, rpcid=None, version=None, notify=None):
    """
    This differs from the Python implementation in that it implements 
    the rpcid argument since the 2.0 spec requires it for responses.
    """
    if not version:
        version = config.version
    valid_params = (types.TupleType, types.ListType, types.DictType)
    if methodname in types.StringTypes and \
            type(params) not in valid_params and \
            not isinstance(params, Fault):
        """ 
        If a method, and params are not in a listish or a Fault,
        error out.
        """
        raise TypeError('Params must be a dict, list, tuple or Fault ' +
                        'instance.')
    # Begin parsing object
    payload = Payload(rpcid=rpcid, version=version)
    if not encoding:
        encoding = 'utf-8'
    if type(params) is Fault:
        response = payload.error(params.faultCode, params.faultString)
        return jdumps(response, encoding=encoding)
    if type(methodname) not in types.StringTypes and methodresponse != True:
        raise ValueError('Method name must be a string, or methodresponse '+
                         'must be set to True.')
    if config.use_jsonclass == True:
        from jsonrpclib import jsonclass
        params = jsonclass.dump(params)
    if methodresponse is True:
        if rpcid is None:
            raise ValueError('A method response must have an rpcid.')
        response = payload.response(params)
        return jdumps(response, encoding=encoding)
    request = None
    if notify == True:
        request = payload.notify(methodname, params)
    else:
        request = payload.request(methodname, params)
    return jdumps(request, encoding=encoding)

def loads(data):
    """
    This differs from the Python implementation, in that it returns
    the request structure in Dict format instead of the method, params.
    It will return a list in the case of a batch request / response.
    """
    if data == '':
        # notification
        return None
    result = jloads(data)
    # if the above raises an error, the implementing server code 
    # should return something like the following:
    # { 'jsonrpc':'2.0', 'error': fault.error(), id: None }
    if config.use_jsonclass == True:
        from jsonrpclib import jsonclass
        result = jsonclass.load(result)
    return result

def check_for_errors(result):
    if not result:
        # Notification
        return result
    if type(result) is not types.DictType:
        raise TypeError('Response is not a dict.')
    if 'jsonrpc' in result.keys() and float(result['jsonrpc']) > 2.0:
        raise NotImplementedError('JSON-RPC version not yet supported.')
    if 'result' not in result.keys() and 'error' not in result.keys():
        raise ValueError('Response does not have a result or error key.')
    if 'error' in result.keys() and result['error'] != None:
        code = result['error']['code']
        message = result['error']['message']
        raise ProtocolError((code, message))
    return result

def isbatch(result):
    if type(result) not in (types.ListType, types.TupleType):
        return False
    if len(result) < 1:
        return False
    if type(result[0]) is not types.DictType:
        return False
    if 'jsonrpc' not in result[0].keys():
        return False
    try:
        version = float(result[0]['jsonrpc'])
    except ValueError:
        raise ProtocolError('"jsonrpc" key must be a float(able) value.')
    if version < 2:
        return False
    return True

def isnotification(request):
    if 'id' not in request.keys():
        # 2.0 notification
        return True
    if request['id'] == None:
        # 1.0 notification
        return True
    return False

########NEW FILE########
__FILENAME__ = SimpleJSONRPCServer
import jsonrpclib
from jsonrpclib import Fault
from jsonrpclib.jsonrpc import USE_UNIX_SOCKETS
import SimpleXMLRPCServer
import SocketServer
import socket
import logging
import os
import types
import traceback
import sys
try:
    import fcntl
except ImportError:
    # For Windows
    fcntl = None

def get_version(request):
    # must be a dict
    if 'jsonrpc' in request.keys():
        return 2.0
    if 'id' in request.keys():
        return 1.0
    return None
    
def validate_request(request):
    if type(request) is not types.DictType:
        fault = Fault(
            -32600, 'Request must be {}, not %s.' % type(request)
        )
        return fault
    rpcid = request.get('id', None)
    version = get_version(request)
    if not version:
        fault = Fault(-32600, 'Request %s invalid.' % request, rpcid=rpcid)
        return fault        
    request.setdefault('params', [])
    method = request.get('method', None)
    params = request.get('params')
    param_types = (types.ListType, types.DictType, types.TupleType)
    if not method or type(method) not in types.StringTypes or \
        type(params) not in param_types:
        fault = Fault(
            -32600, 'Invalid request parameters or method.', rpcid=rpcid
        )
        return fault
    return True

class SimpleJSONRPCDispatcher(SimpleXMLRPCServer.SimpleXMLRPCDispatcher):

    def __init__(self, encoding=None):
        SimpleXMLRPCServer.SimpleXMLRPCDispatcher.__init__(self,
                                        allow_none=True,
                                        encoding=encoding)

    def _marshaled_dispatch(self, data, dispatch_method = None):
        response = None
        try:
            request = jsonrpclib.loads(data)
        except Exception, e:
            fault = Fault(-32700, 'Request %s invalid. (%s)' % (data, e))
            response = fault.response()
            return response
        if not request:
            fault = Fault(-32600, 'Request invalid -- no request data.')
            return fault.response()
        if type(request) is types.ListType:
            # This SHOULD be a batch, by spec
            responses = []
            for req_entry in request:
                result = validate_request(req_entry)
                if type(result) is Fault:
                    responses.append(result.response())
                    continue
                resp_entry = self._marshaled_single_dispatch(req_entry)
                if resp_entry is not None:
                    responses.append(resp_entry)
            if len(responses) > 0:
                response = '[%s]' % ','.join(responses)
            else:
                response = ''
        else:    
            result = validate_request(request)
            if type(result) is Fault:
                return result.response()
            response = self._marshaled_single_dispatch(request)
        return response

    def _marshaled_single_dispatch(self, request):
        # TODO - Use the multiprocessing and skip the response if
        # it is a notification
        # Put in support for custom dispatcher here
        # (See SimpleXMLRPCServer._marshaled_dispatch)
        method = request.get('method')
        params = request.get('params')
        try:
            response = self._dispatch(method, params)
        except:
            exc_type, exc_value, exc_tb = sys.exc_info()
            fault = Fault(-32603, '%s:%s' % (exc_type, exc_value))
            return fault.response()
        if 'id' not in request.keys() or request['id'] == None:
            # It's a notification
            return None
        try:
            response = jsonrpclib.dumps(response,
                                        methodresponse=True,
                                        rpcid=request['id']
                                        )
            return response
        except:
            exc_type, exc_value, exc_tb = sys.exc_info()
            fault = Fault(-32603, '%s:%s' % (exc_type, exc_value))
            return fault.response()

    def _dispatch(self, method, params):
        func = None
        try:
            func = self.funcs[method]
        except KeyError:
            if self.instance is not None:
                if hasattr(self.instance, '_dispatch'):
                    return self.instance._dispatch(method, params)
                else:
                    try:
                        func = SimpleXMLRPCServer.resolve_dotted_attribute(
                            self.instance,
                            method,
                            True
                            )
                    except AttributeError:
                        pass
        if func is not None:
            try:
                if type(params) is types.ListType:
                    response = func(*params)
                else:
                    response = func(**params)
                return response
            except TypeError:
                return Fault(-32602, 'Invalid parameters.')
            except:
                err_lines = traceback.format_exc().splitlines()
                trace_string = '%s | %s' % (err_lines[-3], err_lines[-1])
                fault = jsonrpclib.Fault(-32603, 'Server error: %s' % 
                                         trace_string)
                return fault
        else:
            return Fault(-32601, 'Method %s not supported.' % method)

class SimpleJSONRPCRequestHandler(
        SimpleXMLRPCServer.SimpleXMLRPCRequestHandler):
    
    def do_POST(self):
        if not self.is_rpc_path_valid():
            self.report_404()
            return
        try:
            max_chunk_size = 10*1024*1024
            size_remaining = int(self.headers["content-length"])
            L = []
            while size_remaining:
                chunk_size = min(size_remaining, max_chunk_size)
                L.append(self.rfile.read(chunk_size))
                size_remaining -= len(L[-1])
            data = ''.join(L)
            response = self.server._marshaled_dispatch(data)
            self.send_response(200)
        except Exception, e:
            self.send_response(500)
            err_lines = traceback.format_exc().splitlines()
            trace_string = '%s | %s' % (err_lines[-3], err_lines[-1])
            fault = jsonrpclib.Fault(-32603, 'Server error: %s' % trace_string)
            response = fault.response()
        if response == None:
            response = ''
        self.send_header("Content-type", "application/json-rpc")
        self.send_header("Content-length", str(len(response)))
        self.end_headers()
        self.wfile.write(response)
        self.wfile.flush()
        self.connection.shutdown(1)

class SimpleJSONRPCServer(SocketServer.TCPServer, SimpleJSONRPCDispatcher):

    allow_reuse_address = True

    def __init__(self, addr, requestHandler=SimpleJSONRPCRequestHandler,
                 logRequests=True, encoding=None, bind_and_activate=True,
                 address_family=socket.AF_INET):
        self.logRequests = logRequests
        SimpleJSONRPCDispatcher.__init__(self, encoding)
        # TCPServer.__init__ has an extra parameter on 2.6+, so
        # check Python version and decide on how to call it
        vi = sys.version_info
        self.address_family = address_family
        if USE_UNIX_SOCKETS and address_family == socket.AF_UNIX:
            # Unix sockets can't be bound if they already exist in the
            # filesystem. The convention of e.g. X11 is to unlink
            # before binding again.
            if os.path.exists(addr): 
                try:
                    os.unlink(addr)
                except OSError:
                    logging.warning("Could not unlink socket %s", addr)
        # if python 2.5 and lower
        if vi[0] < 3 and vi[1] < 6:
            SocketServer.TCPServer.__init__(self, addr, requestHandler)
        else:
            SocketServer.TCPServer.__init__(self, addr, requestHandler,
                bind_and_activate)
        if fcntl is not None and hasattr(fcntl, 'FD_CLOEXEC'):
            flags = fcntl.fcntl(self.fileno(), fcntl.F_GETFD)
            flags |= fcntl.FD_CLOEXEC
            fcntl.fcntl(self.fileno(), fcntl.F_SETFD, flags)

class CGIJSONRPCRequestHandler(SimpleJSONRPCDispatcher):

    def __init__(self, encoding=None):
        SimpleJSONRPCDispatcher.__init__(self, encoding)

    def handle_jsonrpc(self, request_text):
        response = self._marshaled_dispatch(request_text)
        print 'Content-Type: application/json-rpc'
        print 'Content-Length: %d' % len(response)
        print
        sys.stdout.write(response)

    handle_xmlrpc = handle_jsonrpc

########NEW FILE########
__FILENAME__ = tests
"""
The tests in this file compare the request and response objects
to the JSON-RPC 2.0 specification document, as well as testing
several internal components of the jsonrpclib library. Run this 
module without any parameters to run the tests.

Currently, this is not easily tested with a framework like 
nosetests because we spin up a daemon thread running the
the Server, and nosetests (at least in my tests) does not
ever "kill" the thread.

If you are testing jsonrpclib and the module doesn't return to
the command prompt after running the tests, you can hit 
"Ctrl-C" (or "Ctrl-Break" on Windows) and that should kill it.

TODO:
* Finish implementing JSON-RPC 2.0 Spec tests
* Implement JSON-RPC 1.0 tests
* Implement JSONClass, History, Config tests
"""

from jsonrpclib import Server, MultiCall, history, config, ProtocolError
from jsonrpclib import jsonrpc
from jsonrpclib.SimpleJSONRPCServer import SimpleJSONRPCServer
from jsonrpclib.SimpleJSONRPCServer import SimpleJSONRPCRequestHandler
import socket
import tempfile
import unittest
import os
import time
try:
    import json
except ImportError:
    import simplejson as json
from threading import Thread

PORTS = range(8000, 8999)

class TestCompatibility(unittest.TestCase):
    
    client = None
    port = None
    server = None
    
    def setUp(self):
        self.port = PORTS.pop()
        self.server = server_set_up(addr=('', self.port))
        self.client = Server('http://localhost:%d' % self.port)
    
    # v1 tests forthcoming
    
    # Version 2.0 Tests
    def test_positional(self):
        """ Positional arguments in a single call """
        result = self.client.subtract(23, 42)
        self.assertTrue(result == -19)
        result = self.client.subtract(42, 23)
        self.assertTrue(result == 19)
        request = json.loads(history.request)
        response = json.loads(history.response)
        verify_request = {
            "jsonrpc": "2.0", "method": "subtract", 
            "params": [42, 23], "id": request['id']
        }
        verify_response = {
            "jsonrpc": "2.0", "result": 19, "id": request['id']
        }
        self.assertTrue(request == verify_request)
        self.assertTrue(response == verify_response)
        
    def test_named(self):
        """ Named arguments in a single call """
        result = self.client.subtract(subtrahend=23, minuend=42)
        self.assertTrue(result == 19)
        result = self.client.subtract(minuend=42, subtrahend=23)
        self.assertTrue(result == 19)
        request = json.loads(history.request)
        response = json.loads(history.response)
        verify_request = {
            "jsonrpc": "2.0", "method": "subtract", 
            "params": {"subtrahend": 23, "minuend": 42}, 
            "id": request['id']
        }
        verify_response = {
            "jsonrpc": "2.0", "result": 19, "id": request['id']
        }
        self.assertTrue(request == verify_request)
        self.assertTrue(response == verify_response)
        
    def test_notification(self):
        """ Testing a notification (response should be null) """
        result = self.client._notify.update(1, 2, 3, 4, 5)
        self.assertTrue(result == None)
        request = json.loads(history.request)
        response = history.response
        verify_request = {
            "jsonrpc": "2.0", "method": "update", "params": [1,2,3,4,5]
        }
        verify_response = ''
        self.assertTrue(request == verify_request)
        self.assertTrue(response == verify_response)
        
    def test_non_existent_method(self):
        self.assertRaises(ProtocolError, self.client.foobar)
        request = json.loads(history.request)
        response = json.loads(history.response)
        verify_request = {
            "jsonrpc": "2.0", "method": "foobar", "id": request['id']
        }
        verify_response = {
            "jsonrpc": "2.0", 
            "error": 
                {"code": -32601, "message": response['error']['message']}, 
            "id": request['id']
        }
        self.assertTrue(request == verify_request)
        self.assertTrue(response == verify_response)
        
    def test_invalid_json(self):
        invalid_json = '{"jsonrpc": "2.0", "method": "foobar, '+ \
            '"params": "bar", "baz]'
        response = self.client._run_request(invalid_json)
        response = json.loads(history.response)
        verify_response = json.loads(
            '{"jsonrpc": "2.0", "error": {"code": -32700,'+
            ' "message": "Parse error."}, "id": null}'
        )
        verify_response['error']['message'] = response['error']['message']
        self.assertTrue(response == verify_response)
        
    def test_invalid_request(self):
        invalid_request = '{"jsonrpc": "2.0", "method": 1, "params": "bar"}'
        response = self.client._run_request(invalid_request)
        response = json.loads(history.response)
        verify_response = json.loads(
            '{"jsonrpc": "2.0", "error": {"code": -32600, '+
            '"message": "Invalid Request."}, "id": null}'
        )
        verify_response['error']['message'] = response['error']['message']
        self.assertTrue(response == verify_response)
        
    def test_batch_invalid_json(self):
        invalid_request = '[ {"jsonrpc": "2.0", "method": "sum", '+ \
            '"params": [1,2,4], "id": "1"},{"jsonrpc": "2.0", "method" ]'
        response = self.client._run_request(invalid_request)
        response = json.loads(history.response)
        verify_response = json.loads(
            '{"jsonrpc": "2.0", "error": {"code": -32700,'+
            '"message": "Parse error."}, "id": null}'
        )
        verify_response['error']['message'] = response['error']['message']
        self.assertTrue(response == verify_response)
        
    def test_empty_array(self):
        invalid_request = '[]'
        response = self.client._run_request(invalid_request)
        response = json.loads(history.response)
        verify_response = json.loads(
            '{"jsonrpc": "2.0", "error": {"code": -32600, '+
            '"message": "Invalid Request."}, "id": null}'
        )
        verify_response['error']['message'] = response['error']['message']
        self.assertTrue(response == verify_response)
        
    def test_nonempty_array(self):
        invalid_request = '[1,2]'
        request_obj = json.loads(invalid_request)
        response = self.client._run_request(invalid_request)
        response = json.loads(history.response)
        self.assertTrue(len(response) == len(request_obj))
        for resp in response:
            verify_resp = json.loads(
                '{"jsonrpc": "2.0", "error": {"code": -32600, '+
                '"message": "Invalid Request."}, "id": null}'
            )
            verify_resp['error']['message'] = resp['error']['message']
            self.assertTrue(resp == verify_resp)
        
    def test_batch(self):
        multicall = MultiCall(self.client)
        multicall.sum(1,2,4)
        multicall._notify.notify_hello(7)
        multicall.subtract(42,23)
        multicall.foo.get(name='myself')
        multicall.get_data()
        job_requests = [j.request() for j in multicall._job_list]
        job_requests.insert(3, '{"foo": "boo"}')
        json_requests = '[%s]' % ','.join(job_requests)
        requests = json.loads(json_requests)
        responses = self.client._run_request(json_requests)
        
        verify_requests = json.loads("""[
            {"jsonrpc": "2.0", "method": "sum", "params": [1,2,4], "id": "1"},
            {"jsonrpc": "2.0", "method": "notify_hello", "params": [7]},
            {"jsonrpc": "2.0", "method": "subtract", "params": [42,23], "id": "2"},
            {"foo": "boo"},
            {"jsonrpc": "2.0", "method": "foo.get", "params": {"name": "myself"}, "id": "5"},
            {"jsonrpc": "2.0", "method": "get_data", "id": "9"} 
        ]""")
            
        # Thankfully, these are in order so testing is pretty simple.
        verify_responses = json.loads("""[
            {"jsonrpc": "2.0", "result": 7, "id": "1"},
            {"jsonrpc": "2.0", "result": 19, "id": "2"},
            {"jsonrpc": "2.0", "error": {"code": -32600, "message": "Invalid Request."}, "id": null},
            {"jsonrpc": "2.0", "error": {"code": -32601, "message": "Method not found."}, "id": "5"},
            {"jsonrpc": "2.0", "result": ["hello", 5], "id": "9"}
        ]""")
        
        self.assertTrue(len(requests) == len(verify_requests))
        self.assertTrue(len(responses) == len(verify_responses))
        
        responses_by_id = {}
        response_i = 0
        
        for i in range(len(requests)):
            verify_request = verify_requests[i]
            request = requests[i]
            response = None
            if request.get('method') != 'notify_hello':
                req_id = request.get('id')
                if verify_request.has_key('id'):
                    verify_request['id'] = req_id
                verify_response = verify_responses[response_i]
                verify_response['id'] = req_id
                responses_by_id[req_id] = verify_response
                response_i += 1
                response = verify_response
            self.assertTrue(request == verify_request)
            
        for response in responses:
            verify_response = responses_by_id.get(response.get('id'))
            if verify_response.has_key('error'):
                verify_response['error']['message'] = \
                    response['error']['message']
            self.assertTrue(response == verify_response)
        
    def test_batch_notifications(self):    
        multicall = MultiCall(self.client)
        multicall._notify.notify_sum(1, 2, 4)
        multicall._notify.notify_hello(7)
        result = multicall()
        self.assertTrue(len(result) == 0)
        valid_request = json.loads(
            '[{"jsonrpc": "2.0", "method": "notify_sum", '+
            '"params": [1,2,4]},{"jsonrpc": "2.0", '+
            '"method": "notify_hello", "params": [7]}]'
        )
        request = json.loads(history.request)
        self.assertTrue(len(request) == len(valid_request))
        for i in range(len(request)):
            req = request[i]
            valid_req = valid_request[i]
            self.assertTrue(req == valid_req)
        self.assertTrue(history.response == '')
        
class InternalTests(unittest.TestCase):
    """ 
    These tests verify that the client and server portions of 
    jsonrpclib talk to each other properly.
    """    
    client = None
    server = None
    port = None
    
    def setUp(self):
        self.port = PORTS.pop()
        self.server = server_set_up(addr=('', self.port))
    
    def get_client(self):
        return Server('http://localhost:%d' % self.port)
        
    def get_multicall_client(self):
        server = self.get_client()
        return MultiCall(server)

    def test_connect(self):
        client = self.get_client()
        result = client.ping()
        self.assertTrue(result)
        
    def test_single_args(self):
        client = self.get_client()
        result = client.add(5, 10)
        self.assertTrue(result == 15)
        
    def test_single_kwargs(self):
        client = self.get_client()
        result = client.add(x=5, y=10)
        self.assertTrue(result == 15)
        
    def test_single_kwargs_and_args(self):
        client = self.get_client()
        self.assertRaises(ProtocolError, client.add, (5,), {'y':10})
        
    def test_single_notify(self):
        client = self.get_client()
        result = client._notify.add(5, 10)
        self.assertTrue(result == None)
    
    def test_single_namespace(self):
        client = self.get_client()
        response = client.namespace.sum(1,2,4)
        request = json.loads(history.request)
        response = json.loads(history.response)
        verify_request = {
            "jsonrpc": "2.0", "params": [1, 2, 4], 
            "id": "5", "method": "namespace.sum"
        }
        verify_response = {
            "jsonrpc": "2.0", "result": 7, "id": "5"
        }
        verify_request['id'] = request['id']
        verify_response['id'] = request['id']
        self.assertTrue(verify_request == request)
        self.assertTrue(verify_response == response)
        
    def test_multicall_success(self):
        multicall = self.get_multicall_client()
        multicall.ping()
        multicall.add(5, 10)
        multicall.namespace.sum([5, 10, 15])
        correct = [True, 15, 30]
        i = 0
        for result in multicall():
            self.assertTrue(result == correct[i])
            i += 1
            
    def test_multicall_success(self):
        multicall = self.get_multicall_client()
        for i in range(3):
            multicall.add(5, i)
        result = multicall()
        self.assertTrue(result[2] == 7)
    
    def test_multicall_failure(self):
        multicall = self.get_multicall_client()
        multicall.ping()
        multicall.add(x=5, y=10, z=10)
        raises = [None, ProtocolError]
        result = multicall()
        for i in range(2):
            if not raises[i]:
                result[i]
            else:
                def func():
                    return result[i]
                self.assertRaises(raises[i], func)
        
        
if jsonrpc.USE_UNIX_SOCKETS:
    # We won't do these tests unless Unix Sockets are supported
    
    class UnixSocketInternalTests(InternalTests):
        """
        These tests run the same internal communication tests, 
        but over a Unix socket instead of a TCP socket.
        """
        def setUp(self):
            suffix = "%d.sock" % PORTS.pop()
            
            # Open to safer, alternative processes 
            # for getting a temp file name...
            temp = tempfile.NamedTemporaryFile(
                suffix=suffix
            )
            self.port = temp.name
            temp.close()
            
            self.server = server_set_up(
                addr=self.port, 
                address_family=socket.AF_UNIX
            )

        def get_client(self):
            return Server('unix:/%s' % self.port)
            
        def tearDown(self):
            """ Removes the tempory socket file """
            os.unlink(self.port)
            
class UnixSocketErrorTests(unittest.TestCase):
    """ 
    Simply tests that the proper exceptions fire if 
    Unix sockets are attempted to be used on a platform
    that doesn't support them.
    """
    
    def setUp(self):
        self.original_value = jsonrpc.USE_UNIX_SOCKETS
        if (jsonrpc.USE_UNIX_SOCKETS):
            jsonrpc.USE_UNIX_SOCKETS = False
        
    def test_client(self):
        address = "unix://shouldnt/work.sock"
        self.assertRaises(
            jsonrpc.UnixSocketMissing,
            Server,
            address
        )
        
    def tearDown(self):
        jsonrpc.USE_UNIX_SOCKETS = self.original_value
        

""" Test Methods """
def subtract(minuend, subtrahend):
    """ Using the keywords from the JSON-RPC v2 doc """
    return minuend-subtrahend
    
def add(x, y):
    return x + y
    
def update(*args):
    return args
    
def summation(*args):
    return sum(args)
    
def notify_hello(*args):
    return args
    
def get_data():
    return ['hello', 5]
        
def ping():
    return True
        
def server_set_up(addr, address_family=socket.AF_INET):
    # Not sure this is a good idea to spin up a new server thread
    # for each test... but it seems to work fine.
    def log_request(self, *args, **kwargs):
        """ Making the server output 'quiet' """
        pass
    SimpleJSONRPCRequestHandler.log_request = log_request
    server = SimpleJSONRPCServer(addr, address_family=address_family)
    server.register_function(summation, 'sum')
    server.register_function(summation, 'notify_sum')
    server.register_function(notify_hello)
    server.register_function(subtract)
    server.register_function(update)
    server.register_function(get_data)
    server.register_function(add)
    server.register_function(ping)
    server.register_function(summation, 'namespace.sum')
    server_proc = Thread(target=server.serve_forever)
    server_proc.daemon = True
    server_proc.start()
    return server_proc

if __name__ == '__main__':
    print "==============================================================="
    print "  NOTE: There may be threading exceptions after tests finish.  "
    print "==============================================================="
    time.sleep(2)
    unittest.main()

########NEW FILE########
