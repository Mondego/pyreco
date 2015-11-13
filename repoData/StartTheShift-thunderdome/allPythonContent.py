__FILENAME__ = connection
# Copyright (c) 2012-2013 SHIFT.com
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of
# this software and associated documentation files (the "Software"), to deal in
# the Software without restriction, including without limitation the rights to
# use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of
# the Software, and to permit persons to whom the Software is furnished to do so,
# subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS
# FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
# COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER
# IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
# CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

from collections import namedtuple
import httplib
import json
import logging
import Queue
import random
import re
import socket
import textwrap

from thunderdome.exceptions import ThunderdomeException
from thunderdome.spec import Spec


logger = logging.getLogger(__name__)


class ThunderdomeConnectionError(ThunderdomeException):
    """
    Problem connecting to Rexster
    """


class ThunderdomeQueryError(ThunderdomeException):
    """
    Problem with a Gremlin query to Titan
    """

    def __init__(self, message, full_response={}):
        """
        Initialize the thunderdome query error message.

        :param message: The message text itself
        :type message: str
        :param full_response: The full query response
        :type full_response: dict
        
        """
        super(ThunderdomeQueryError, self).__init__(message)
        self._full_response = full_response

    @property
    def raw_response(self):
        """
        Return the raw query response.

        :rtype: dict
        
        """
        return self._full_response


class ThunderdomeGraphMissingError(ThunderdomeException):
    """
    Graph with specified name does not exist
    """


Host = namedtuple('Host', ['name', 'port'])
_hosts = []
_host_idx = 0
_graph_name = None
_username = None
_password = None
_index_all_fields = True
_existing_indices = None
_statsd = None


def create_key_index(name):
    """
    Creates a key index if it does not already exist
    """
    global _existing_indices
    _existing_indices = _existing_indices or execute_query('g.getIndexedKeys(Vertex.class)')
    if name not in _existing_indices:
        execute_query(
            "g.createKeyIndex(keyname, Vertex.class); g.stopTransaction(SUCCESS)",
            {'keyname':name}, transaction=False)
        _existing_indices = None

        
def create_unique_index(name, data_type):
    """
    Creates a key index if it does not already exist
    """
    global _existing_indices
    _existing_indices = _existing_indices or execute_query('g.getIndexedKeys(Vertex.class)')
    
    if name not in _existing_indices:
        execute_query(
            "g.makeType().name(name).dataType({}.class).functional().unique().indexed().makePropertyKey(); g.stopTransaction(SUCCESS)".format(data_type),
            {'name':name}, transaction=False)
        _existing_indices = None

        
def setup(hosts, graph_name, username=None, password=None, index_all_fields=False, statsd=None):
    """
    Records the hosts and connects to one of them.

    :param hosts: list of hosts, strings in the <hostname>:<port> or just <hostname> format
    :type hosts: list of str
    :param graph_name: The name of the graph as defined in the rexster.xml
    :type graph_name: str
    :param username: The username for the rexster server
    :type username: str
    :param password: The password for the rexster server
    :type password: str
    :param index_all_fields: Toggle automatic indexing of all vertex fields
    :type index_all_fields: boolean
    :param statsd: host:port or just host of statsd server to report metrics to
    :type statsd: str
    :rtype None
    """
    global _hosts
    global _graph_name
    global _username
    global _password
    global _index_all_fields
    global _statsd

    _graph_name = graph_name
    _username = username
    _password = password
    _index_all_fields = index_all_fields


    if statsd:
        try:
            sd = statsd
            import statsd
            tmp = sd.split(':')
            if len(tmp) == 1:
                tmp.append('8125')
            _statsd = statsd.StatsClient(tmp[0], int(tmp[1]), prefix='thunderdome')
        except ImportError:
            logging.warning("Statsd configured but not installed.  Please install the statsd package.")
        except:
            raise

    for host in hosts:
        host = host.strip()
        host = host.split(':')
        if len(host) == 1:
            _hosts.append(Host(host[0], 8182))
        elif len(host) == 2:
            _hosts.append(Host(*host))
        else:
            raise ThunderdomeConnectionError("Can't parse {}".format(''.join(host)))

    if not _hosts:
        raise ThunderdomeConnectionError("At least one host required")

    random.shuffle(_hosts)
    
    create_unique_index('vid', 'String')

    #index any models that have already been defined
    from thunderdome.models import vertex_types
    for klass in vertex_types.values():
        klass._create_indices()
    
    
def execute_query(query, params={}, transaction=True, context=""):
    """
    Execute a raw Gremlin query with the given parameters passed in.

    :param query: The Gremlin query to be executed
    :type query: str
    :param params: Parameters to the Gremlin query
    :type params: dict
    :param context: String context data to include with the query for stats logging
    :rtype: dict
    
    """
    if transaction:
        query = "g.stopTransaction(FAILURE)\n" + query

    # If we have no hosts available raise an exception
    if len(_hosts) <= 0:
        raise ThunderdomeConnectionError('Attempt to execute query before calling thunderdome.connection.setup')
    
    host = _hosts[0]
    #url = 'http://{}/graphs/{}/tp/gremlin'.format(host.name, _graph_name)
    data = json.dumps({'script':query, 'params': params})
    headers = {'Content-Type':'application/json', 'Accept':'application/json', 'Accept-Charset':'utf-8'}
    import time
    try:
        start_time = time.time()
        conn = httplib.HTTPConnection(host.name, host.port)
        conn.request("POST", '/graphs/{}/tp/gremlin'.format(_graph_name), data, headers)
        response = conn.getresponse()
        content = response.read()

        total_time = int((time.time() - start_time) * 1000)

        if context and _statsd:
            _statsd.timing("{}.timer".format(context), total_time)
            _statsd.incr("{}.counter".format(context))


    except socket.error as sock_err:
        if _statsd:
            total_time = int((time.time() - start_time) * 1000)
            _statsd.incr("thunderdome.socket_error".format(context), total_time)
        raise ThunderdomeQueryError('Socket error during query - {}'.format(sock_err))
    except:
        raise
    
    logger.info(json.dumps(data))
    logger.info(content)

    try:
        response_data = json.loads(content)
    except ValueError as ve:
        raise ThunderdomeQueryError('Loading Rexster results failed: "{}"'.format(ve))
    
    if response.status != 200:
        if 'message' in response_data and len(response_data['message']) > 0:
            graph_missing_re = r"Graph \[(.*)\] could not be found"
            if re.search(graph_missing_re, response_data['message']):
                raise ThunderdomeGraphMissingError(response_data['message'])
            else:
                raise ThunderdomeQueryError(
                    response_data['message'],
                    response_data
                )
        else:
            if _statsd:
                _statsd.incr("{}.error".format(context))
            raise ThunderdomeQueryError(
                response_data['error'],
                response_data
            )

    return response_data['results'] 


def sync_spec(filename, host, graph_name, dry_run=False):
    """
    Sync the given spec file to thunderdome.

    :param filename: The filename of the spec file
    :type filename: str
    :param host: The host the be synced
    :type host: str
    :param graph_name: The name of the graph to be synced
    :type graph_name: str
    :param dry_run: Only prints generated Gremlin if True
    :type dry_run: boolean
    
    """
    Spec(filename).sync(host, graph_name, dry_run=dry_run)

########NEW FILE########
__FILENAME__ = containers
# Copyright (c) 2012-2013 SHIFT.com
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of
# this software and associated documentation files (the "Software"), to deal in
# the Software without restriction, including without limitation the rights to
# use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of
# the Software, and to permit persons to whom the Software is furnished to do so,
# subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS
# FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
# COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER
# IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
# CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

class Row(object):
    def __init__(self, data):
        for k,v in data.iteritems():
            setattr(self, k, v)
    
class Table(object):
    """
    A table accepts the results of a GremlinMethod in it's
    constructor.  
    It can be iterated over like a normal list, but within the rows
    the dictionaries are accessible via .notation
    
    For example:
    
    # returns a table of people & my friend edge to them
    # the edge contains my nickname for that person
    friends = thunderdome.GremlinMethod()
    
    def get_friends_and_my_nickname(self):
        result = self.friends()
        result = Table(result)
        for i in result:
            print "{}:{}".format(i.friend_edge.nickname, i.person.name)
    """
    
    def __init__(self, gremlin_result):
        if gremlin_result == [[]]:
            gremlin_result = []

        self._gremlin_result = gremlin_result
        self._position = 0
        
    
    def __getitem__(self, key): 
        """
        returns an enhanced dictionary
        """
        if key >= len(self._gremlin_result):
            raise IndexError()

        return Row(self._gremlin_result[key])
        
    def __iter__(self):
        return self
    
    def next(self):
        if self._position == len(self._gremlin_result):
            self._position = 0
            raise StopIteration()
        tmp = self._gremlin_result[self._position]
        self._position += 1
        return Row(tmp)
    
    
    def __len__(self):
        return len(self._gremlin_result)

########NEW FILE########
__FILENAME__ = exceptions
# Copyright (c) 2012-2013 SHIFT.com
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of
# this software and associated documentation files (the "Software"), to deal in
# the Software without restriction, including without limitation the rights to
# use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of
# the Software, and to permit persons to whom the Software is furnished to do so,
# subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS
# FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
# COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER
# IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
# CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

class ThunderdomeException(Exception): pass
class ModelException(ThunderdomeException): pass
class ValidationError(ThunderdomeException): pass
class DoesNotExist(ThunderdomeException): pass
class MultipleObjectsReturned(ThunderdomeException): pass
class WrongElementType(ThunderdomeException): pass


########NEW FILE########
__FILENAME__ = gremlin
import inspect
import os.path
import time
import logging

from thunderdome.connection import execute_query, ThunderdomeQueryError
from thunderdome.exceptions import ThunderdomeException
from thunderdome.groovy import parse
from containers import Table


logger = logging.getLogger(__name__)


class ThunderdomeGremlinException(ThunderdomeException):
    """
    Exception thrown when a Gremlin error is encountered
    """


class BaseGremlinMethod(object):
    """ Maps a function in a groovy file to a method on a python class """

    def __init__(self,
                 path=None,
                 method_name=None,
                 classmethod=False,
                 property=False,
                 defaults={},
                 transaction=True):
        """
        Initialize the gremlin method and define how it is attached to class.

        :param path: Path to the gremlin source (relative to file class is
        defined in). Absolute paths work as well. Defaults to gremlin.groovy.
        :type path: str
        :param method_name: The name of the function definition in the groovy file
        :type method_name: str
        :param classmethod: Method should behave as a classmethod if True
        :type classmethod: boolean
        :param property: Method should behave as a property
        :type property: boolean
        :param defaults: The default parameters to the function
        :type defaults: dict
        :param transaction: Close previous transaction before executing (True
        by default)
        :type transaction: boolean

        """
        self.is_configured = False
        self.is_setup = False
        self.path = path
        self.method_name = method_name
        self.classmethod = classmethod
        self.property = property
        self.defaults =defaults
        self.transaction = transaction

        self.attr_name = None
        self.arg_list = []
        self.function_body = None
        self.function_def = None

        #configuring attributes
        self.parent_class = None


    def configure_method(self, klass, attr_name, gremlin_path):
        """
        sets up the methods internals

        :param klass: The class object this function is being added to
        :type klass: object
        :param attr_name: The attribute name this function will be added as
        :type attr_name: str
        :param gremlin_path: The path to the gremlin file containing method
        :type gremlin_path: str

        """
        if not self.is_configured:
            self.parent_class = klass
            self.attr_name = attr_name
            self.method_name = self.method_name or self.attr_name
            self.path = gremlin_path

            self.is_configured = True

    def _setup(self):
        """
        Does the actual method configuration, this is here because the
        method configuration must happen after the class is defined
        """
        if not self.is_setup:

            #construct the default name
            name_func = getattr(self.parent_class, 'get_element_type', None) or getattr(self.parent_class, 'get_label', None)
            default_path = (name_func() if name_func else 'gremlin') + '.groovy'

            self.path = self.path or default_path
            if self.path.startswith('/'):
                path = self.path
            else:
                path = inspect.getfile(self.parent_class)
                path = os.path.split(path)[0]
                path += '/' + self.path

            #TODO: make this less naive
            gremlin_obj = None
            for grem_obj in parse(path):
                if grem_obj.name == self.method_name:
                    gremlin_obj = grem_obj
                    break

            if gremlin_obj is None:
                raise ThunderdomeGremlinException("The method '{}' wasnt found in {}".format(self.method_name, path))

            for arg in gremlin_obj.args:
                if arg in self.arg_list:
                    raise ThunderdomeGremlinException("'{}' defined more than once in gremlin method arguments".format(arg))
                self.arg_list.append(arg)

            self.function_body = gremlin_obj.body
            self.function_def = gremlin_obj.defn
            self.is_setup = True

    def __call__(self, instance, *args, **kwargs):
        """
        Intercept attempts to call the GremlinMethod attribute and perform a
        gremlin query returning the results.

        :param instance: The class instance the method was called on
        :type instance: object

        """
        self._setup()

        args = list(args)
        if not self.classmethod:
            args = [instance.eid] + args

        params = self.defaults.copy()
        if len(args + kwargs.values()) > len(self.arg_list):
            raise TypeError('{}() takes {} args, {} given'.format(self.attr_name, len(self.arg_list), len(args)))

        #check for and calculate callable defaults
        for k,v in params.items():
            if callable(v):
                params[k] = v()

        arglist = self.arg_list[:]
        for arg in args:
            params[arglist.pop(0)] = arg

        for k,v in kwargs.items():
            if k not in arglist:
                an = self.attr_name
                if k in params:
                    raise TypeError(
                        "{}() got multiple values for keyword argument '{}'".format(an, k))
                else:
                    raise TypeError(
                        "{}() got an unexpected keyword argument '{}'".format(an, k))
            arglist.pop(arglist.index(k))
            params[k] = v

        params = self.transform_params_to_database(params)

        try:
            from thunderdome import Vertex
            from thunderdome import Edge
            
            if hasattr(instance, 'get_element_type'):
                context = "vertices.{}".format(instance.get_element_type())
            elif hasattr(instance, 'get_label'):
                context = "edges.{}".format(instance.get_label())
            else:
                context = "other"

            context = "{}.{}".format(context, self.method_name)

            tmp = execute_query(self.function_body, params, transaction=self.transaction, context=context)
        except ThunderdomeQueryError as tqe:
            import pprint
            msg  = "Error while executing Gremlin method\n\n"
            msg += "[Method]\n{}\n\n".format(self.method_name)
            msg += "[Params]\n{}\n\n".format(pprint.pformat(params))
            msg += "[Function Body]\n{}\n".format(self.function_body)
            msg += "\n[Error]\n{}\n".format(tqe)
            msg += "\n[Raw Response]\n{}\n".format(tqe.raw_response)
            raise ThunderdomeGremlinException(msg)
        return tmp

    def transform_params_to_database(self, params):
        """
        Takes a dictionary of parameters and recursively translates them into
        parameters appropriate for sending over Rexster.

        :param params: The parameters to be sent to the function
        :type params: dict

        """
        import inspect
        from datetime import datetime
        from decimal import Decimal as _Decimal
        from uuid import UUID as _UUID
        from thunderdome.models import BaseElement, Edge, Vertex
        from thunderdome.properties import DateTime, Decimal, UUID

        if isinstance(params, dict):
            return {k:self.transform_params_to_database(v) for k,v in params.iteritems()}
        if isinstance(params, list):
            return [self.transform_params_to_database(x) for x in params]
        if isinstance(params, BaseElement):
            return params.eid
        if inspect.isclass(params) and issubclass(params, Edge):
            return params.label
        if inspect.isclass(params) and issubclass(params, Vertex):
            return params.element_type
        if isinstance(params, datetime):
            return DateTime().to_database(params)
        if isinstance(params, _UUID):
            return UUID().to_database(params)
        if isinstance(params, _Decimal):
            return Decimal().to_database(params)
        return params


class GremlinMethod(BaseGremlinMethod):
    """Gremlin method that returns a graph element"""

    @staticmethod
    def _deserialize(obj):
        """
        Recursively deserializes elements returned from rexster

        :param obj: The raw result returned from rexster
        :type obj: object

        """
        from thunderdome.models import Element

        if isinstance(obj, dict) and '_id' in obj and '_type' in obj:
            return Element.deserialize(obj)
        elif isinstance(obj, dict):
            return {k:GremlinMethod._deserialize(v) for k,v in obj.items()}
        elif isinstance(obj, list):
            return [GremlinMethod._deserialize(v) for v in obj]
        else:
            return obj

    def __call__(self, instance, *args, **kwargs):
        results = super(GremlinMethod, self).__call__(instance, *args, **kwargs)
        return GremlinMethod._deserialize(results)


class GremlinValue(GremlinMethod):
    """Gremlin Method that returns one value"""

    def __call__(self, instance, *args, **kwargs):
        results = super(GremlinValue, self).__call__(instance, *args, **kwargs)

        if results is None:
            return
        if len(results) != 1:
            raise ThunderdomeGremlinException('GremlinValue requires a single value is returned ({} returned)'.format(len(results)))

        return results[0]


class GremlinTable(GremlinMethod):
    """Gremlin method that returns a table as its result"""

    def __call__(self, instance, *args, **kwargs):
        results = super(GremlinTable, self).__call__(instance, *args, **kwargs)
        if results is None:
            return
        return Table(results)

########NEW FILE########
__FILENAME__ = groovy
# Copyright (c) 2012-2013 SHIFT.com
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of
# this software and associated documentation files (the "Software"), to deal in
# the Software without restriction, including without limitation the rights to
# use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of
# the Software, and to permit persons to whom the Software is furnished to do so,
# subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS
# FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
# COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER
# IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
# CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

import collections
import pyparsing
import re


# Cache of parsed files
_parsed_file_cache = {}


class GroovyFunctionParser(object):
    """
    Given a string containing a single function definition this class will 
    parse the function definition and return information regarding it.
    """

    # Simple Groovy sub-grammar definitions
    KeywordDef  = pyparsing.Keyword('def')
    VarName     = pyparsing.Regex(r'[A-Za-z_]\w*')
    FuncName    = VarName
    FuncDefn    = KeywordDef + FuncName + "(" + pyparsing.delimitedList(VarName) + ")" + "{"
    
    # Result named tuple
    GroovyFunction = collections.namedtuple('GroovyFunction', ['name', 'args', 'body', 'defn'])
    
    @classmethod
    def parse(cls, data):
        """
        Parse the given function definition and return information regarding
        the contained definition.
        
        :param data: The function definition in a string
        :type data: str
        :rtype: dict
        
        """
        try:
            # Parse the function here
            result = cls.FuncDefn.parseString(data)
            result_list = result.asList()
            args = result_list[3:result_list.index(')')]
            # Return single line or multi-line function body
            fn_body = re.sub(r'[^\{]+\{', '', data, count=1)
            parts = fn_body.strip().split('\n')
            fn_body = '\n'.join(parts[0:-1])
            return cls.GroovyFunction(result[1], args, fn_body, data)
        except Exception, ex:
            return {}
        

def parse(file):
    """
    Parse Groovy code in the given file and return a list of information about
    each function necessary for usage in queries to database.
    
    :param file: The file containing groovy code.
    :type file: str
    :rtype: 
    
    """
    # Check cache before parsing file
    global _parsed_file_cache
    if file in _parsed_file_cache:
        return _parsed_file_cache[file]
    
    FuncDefnRegexp = r'^def.*\{'
    FuncEndRegexp = r'^\}.*$'
    with open(file, 'r') as f:
        data = f.read()
    file_lines = data.split("\n")
    all_fns = []
    fn_lines = ''
    for line in file_lines:
        if len(fn_lines) > 0:
            if re.match(FuncEndRegexp, line):
                fn_lines += line + "\n"
                all_fns.append(fn_lines)
                fn_lines = ''
            else:
                fn_lines += line + "\n"
        elif re.match(FuncDefnRegexp, line):
            fn_lines += line + "\n"
            
    func_results = []
    for fn in all_fns:
        func_results += [GroovyFunctionParser.parse(fn)]
        
    _parsed_file_cache[file] = func_results
    return func_results

########NEW FILE########
__FILENAME__ = models
# Copyright (c) 2012-2013 SHIFT.com
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of
# this software and associated documentation files (the "Software"), to deal in
# the Software without restriction, including without limitation the rights to
# use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of
# the Software, and to permit persons to whom the Software is furnished to do so,
# subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS
# FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
# COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER
# IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
# CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

from collections import OrderedDict
import inspect
import re
from uuid import UUID
import warnings

from thunderdome import properties
from thunderdome.connection import execute_query, create_key_index, ThunderdomeQueryError
from thunderdome.exceptions import ModelException, ValidationError, DoesNotExist, MultipleObjectsReturned, ThunderdomeException, WrongElementType
from thunderdome.gremlin import BaseGremlinMethod, GremlinMethod


#dict of node and edge types for rehydrating results
vertex_types = {}
edge_types = {}

# in blueprints this is part of the Query.compare
# see http://www.tinkerpop.com/docs/javadocs/blueprints/2.2.0/
EQUAL = "EQUAL"
GREATER_THAN = "GREATER_THAN"
GREATER_THAN_EQUAL = "GREATER_THAN_EQUAL"
LESS_THAN = "LESS_THAN"
LESS_THAN_EQUAL = "LESS_THAN_EQUAL"
NOT_EQUAL = "NOT_EQUAL"

# direction
OUT = "OUT"
IN = "IN"
BOTH = "BOTH"


class ElementDefinitionException(ModelException):
    """
    Error in element definition
    """

    
class SaveStrategyException(ModelException):
    """
    Violation of save strategy
    """


class BaseElement(object):
    """
    The base model class, don't inherit from this, inherit from Model, defined
    below
    """

    # When true this will prepend the module name to the type name of the class
    __use_module_name__ = False
    __default_save_strategy__ = properties.SAVE_ALWAYS
    
    class DoesNotExist(DoesNotExist):
        """
        Object not found in database
        """

    class MultipleObjectsReturned(MultipleObjectsReturned):
        """
        Multiple objects returned on unique key lookup
        """
        
    class WrongElementType(WrongElementType):
        """
        Unique lookup with key corresponding to vertex of different type
        """

    def __init__(self, **values):
        """
        Initialize the element with the given properties.

        :param values: The properties for this element
        :type values: dict
        
        """
        self.eid = values.get('_id')
        self._values = {}
        for name, column in self._columns.items():
            value = values.get(name, None)
            if value is not None:
                value = column.to_python(value)
            value_mngr = column.value_manager(self, column, value)
            self._values[name] = value_mngr

    def __eq__(self, other):
        """
        Check for equality between two elements.

        :param other: Element to be compared to
        :type other: BaseElement
        :rtype: boolean
        
        """
        if not isinstance(other, BaseElement): return False
        return self.as_dict() == other.as_dict() and self.eid == other.eid

    def __ne__(self, other):
        """
        Check for inequality between two elements.

        :param other: Element to be compared to
        :type other: BaseElement
        :rtype: boolean
        
        """
        return not self.__eq__(other)

    @classmethod
    def _type_name(cls, manual_name):
        """
        Returns the element name if it has been defined, otherwise it creates
        it from the module and class name.

        :param manual_name: Name to override the default type name
        :type manual_name: str
        :rtype: str
        
        """
        cf_name = ''
        if manual_name:
            cf_name = manual_name.lower()
        else:
            camelcase = re.compile(r'([a-z])([A-Z])')
            ccase = lambda s: camelcase.sub(lambda v: '{}_{}'.format(v.group(1), v.group(2).lower()), s)
    
            cf_name += ccase(cls.__name__)
            cf_name = cf_name.lower()
        if cls.__use_module_name__:
            cf_name = cls.__module__ + '_{}'.format(cf_name)
        return cf_name

    def validate_field(self, field_name, val):
        """
        Perform the validations associated with the field with the given name on
        the value passed.

        :param field_name: The name of column whose validations will be run
        :type field_name: str
        :param val: The value to be validated
        :type val: mixed
        
        """
        return self._columns[field_name].validate(val)

    def validate(self):
        """Cleans and validates the field values"""
        for name in self._columns.keys():
            func_name = 'validate_{}'.format(name)
            val = getattr(self, name)
            if hasattr(self, func_name):
                val = getattr(self, func_name)(val)
            else:
                val = self.validate_field(name, val)
            setattr(self, name, val)

    def as_dict(self):
        """
        Returns a map of column names to cleaned values

        :rtype: dict
        
        """
        values = {}
        for name, col in self._columns.items():
            values[name] = col.to_database(getattr(self, name, None))
        return values

    def as_save_params(self):
        """
        Returns a map of column names to cleaned values containing only the
        columns which should be persisted on save.

        :rtype: dict
        
        """
        values = {}
        was_saved = self.eid is not None
        for name, col in self._columns.items():
            # Determine the save strategy for this column
            should_save = True

            col_strategy = self.__default_save_strategy__
            if col.has_save_strategy:
                col_strategy = col.get_save_strategy()

            # Enforce the save strategy
            if col_strategy == properties.SAVE_ONCE:
                if was_saved:
                    if self._values[name].changed:
                        raise SaveStrategyException("Attempt to change column '{}' with save strategy SAVE_ONCE".format(name))
                    else:
                        should_save = False
            elif col_strategy == properties.SAVE_ONCHANGE:
                if was_saved and not self._values[name].changed:
                    should_save = False
            
            if should_save:
                values[col.db_field or name] = col.to_database(getattr(self, name, None))
                
        return values

    @classmethod
    def translate_db_fields(cls, data):
        """
        Translates field names from the database into field names used in our model

        this is for cases where we're saving a field under a different name than it's model property

        :param cls:
        :param data:
        :return:
        """
        dst_data = data.copy()
        for name, col in cls._columns.items():
            key = col.db_field or name
            if key in dst_data:
                dst_data[name] = dst_data.pop(key)

        return dst_data

    @classmethod
    def create(cls, *args, **kwargs):
        """Create a new element with the given information."""
        return cls(*args, **kwargs).save()
        
    def pre_save(self):
        """Pre-save hook which is run before saving an element"""
        self.validate()
        
    def save(self):
        """
        Base class save method. Performs basic validation and error handling.
        """
        if self.__abstract__:
            raise ThunderdomeException('cant save abstract elements')
        self.pre_save()
        return self

    def pre_update(self, **values):
        """ Override this to perform pre-update validation """
        pass

    def update(self, **values):
        """
        performs an update of this element with the given values and returns the
        saved object
        """
        if self.__abstract__:
            raise ThunderdomeException('cant update abstract elements')
        self.pre_update(**values)
        for key in values.keys():
            if key not in self._columns:
                raise TypeError("unrecognized attribute name: '{}'".format(key))

        for k,v in values.items():
            setattr(self, k, v)

        return self.save()

    def _reload_values(self):
        """
        Base method for reloading an element from the database.
        """
        raise NotImplementedError

    def reload(self):
        """
        Reload the given element from the database.
        """
        values = self._reload_values()
        for name, column in self._columns.items():
            value = values.get(column.db_field_name, None)
            if value is not None: value = column.to_python(value)
            setattr(self, name, value)
        return self

    
class ElementMetaClass(type):
    """Metaclass for all graph elements"""
    
    def __new__(cls, name, bases, attrs):
        """
        """
        #move column definitions into columns dict
        #and set default column names
        column_dict = OrderedDict()
        
        #get inherited properties
        for base in bases:
            for k,v in getattr(base, '_columns', {}).items():
                column_dict.setdefault(k,v)

        def _transform_column(col_name, col_obj):
            column_dict[col_name] = col_obj
            col_obj.set_column_name(col_name)
            #set properties
            _get = lambda self: self._values[col_name].getval()
            _set = lambda self, val: self._values[col_name].setval(val)
            _del = lambda self: self._values[col_name].delval()
            if col_obj.can_delete:
                attrs[col_name] = property(_get, _set, _del)
            else:
                attrs[col_name] = property(_get, _set)

        column_definitions = [(k,v) for k,v in attrs.items() if isinstance(v, properties.Column)]
        column_definitions = sorted(column_definitions, lambda x,y: cmp(x[1].position, y[1].position))
        
        #TODO: check that the defined columns don't conflict with any of the
        #Model API's existing attributes/methods transform column definitions
        for k,v in column_definitions:
            _transform_column(k,v)
            
        #check for duplicate column names
        col_names = set()
        for v in column_dict.values():
            if v.db_field_name in col_names:
                raise ModelException("{} defines the column {} more than once".format(name, v.db_field_name))
            col_names.add(v.db_field_name)

        #create db_name -> model name map for loading
        db_map = {}
        for field_name, col in column_dict.items():
            db_map[col.db_field_name] = field_name

        #add management members to the class
        attrs['_columns'] = column_dict
        attrs['_db_map'] = db_map
        
        #auto link gremlin methods
        gremlin_methods = {}
        
        #get inherited gremlin methods
        for base in bases:
            for k,v in getattr(base, '_gremlin_methods', {}).items():
                gremlin_methods.setdefault(k, v)

        #short circuit __abstract__ inheritance
        attrs['__abstract__'] = attrs.get('__abstract__', False)
                
        #short circuit path inheritance
        gremlin_path = attrs.get('gremlin_path')
        attrs['gremlin_path'] = gremlin_path

        def wrap_method(method):
            def method_wrapper(self, *args, **kwargs):
                return method(self, *args, **kwargs)
            return method_wrapper
        
        for k,v in attrs.items():
            if isinstance(v, BaseGremlinMethod):
                gremlin_methods[k] = v
                method = wrap_method(v)
                attrs[k] = method
                if v.classmethod: attrs[k] = classmethod(method)
                if v.property: attrs[k] = property(method)

        attrs['_gremlin_methods'] = gremlin_methods

        #create the class and add a QuerySet to it
        klass = super(ElementMetaClass, cls).__new__(cls, name, bases, attrs)
        
        #configure the gremlin methods
        for name, method in gremlin_methods.items():
            method.configure_method(klass, name, gremlin_path)
            
        return klass


class Element(BaseElement):
    __metaclass__ = ElementMetaClass
    
    @classmethod
    def deserialize(cls, data):
        """
        Deserializes rexster json into vertex or edge objects
        """
        dtype = data.get('_type')
        if dtype == 'vertex':
            vertex_type = data['element_type']
            if vertex_type not in vertex_types:
                raise ElementDefinitionException('Vertex "{}" not defined'.format(vertex_type))
            translated_data = vertex_types[vertex_type].translate_db_fields(data)
            return vertex_types[vertex_type](**translated_data)
        elif dtype == 'edge':
            edge_type = data['_label']
            if edge_type not in edge_types:
                raise ElementDefinitionException('Edge "{}" not defined'.format(edge_type))
            translated_data = edge_types[edge_type].translate_db_fields(data)
            return edge_types[edge_type](data['_outV'], data['_inV'], **translated_data)
        else:
            raise TypeError("Can't deserialize '{}'".format(dtype))
    
    
class VertexMetaClass(ElementMetaClass):
    """Metaclass for vertices."""
    
    def __new__(cls, name, bases, attrs):

        #short circuit element_type inheritance
        attrs['element_type'] = attrs.pop('element_type', None)

        klass = super(VertexMetaClass, cls).__new__(cls, name, bases, attrs)

        if not klass.__abstract__:
            element_type = klass.get_element_type()
            if element_type in vertex_types and str(vertex_types[element_type]) != str(klass):
                raise ElementDefinitionException('{} is already registered as a vertex'.format(element_type))
            vertex_types[element_type] = klass

            #index requested indexed columns
            klass._create_indices()

        return klass

    
class Vertex(Element):
    """
    The Vertex model base class. All vertexes have a vid defined on them, the
    element type is autogenerated from the subclass name, but can optionally be
    set manually
    """
    __metaclass__ = VertexMetaClass
    __abstract__ = True

    gremlin_path = 'vertex.groovy'

    _save_vertex = GremlinMethod()
    _traversal = GremlinMethod()
    _delete_related = GremlinMethod()

    #vertex id
    vid = properties.UUID(save_strategy=properties.SAVE_ONCE)
    
    element_type = None

    @classmethod
    def _create_indices(cls):
        """
        Creates this model's indices. This will be skipped if connection.setup
        hasn't been called, but connection.setup calls this method on existing
        vertices
        """
        from thunderdome.connection import _hosts, _index_all_fields, create_key_index
        
        if not _hosts: return
        for column in cls._columns.values():
            if column.index or _index_all_fields:
                create_key_index(column.db_field_name)
    
    @classmethod
    def get_element_type(cls):
        """
        Returns the element type for this vertex.

        :rtype: str
        
        """
        return cls._type_name(cls.element_type)
    
    @classmethod
    def all(cls, vids, as_dict=False):
        """
        Load all vertices with the given vids from the graph. By default this
        will return a list of vertices but if as_dict is True then it will
        return a dictionary containing vids as keys and vertices found as
        values.

        :param vids: A list of thunderdome UUIDS (vids)
        :type vids: list
        :param as_dict: Toggle whether to return a dictionary or list
        :type as_dict: boolean
        :rtype: dict or list
        
        """
        if not isinstance(vids, (list, tuple)):
            raise ThunderdomeQueryError("vids must be of type list or tuple")
        
        strvids = [str(v) for v in vids]
        qs = ['vids.collect{g.V("vid", it).toList()[0]}']
        
        results = execute_query('\n'.join(qs), {'vids':strvids})
        results = filter(None, results)
        
        if len(results) != len(vids):
            raise ThunderdomeQueryError("the number of results don't match the number of vids requested")
        
        objects = []
        for r in results:
            try:
                objects += [Element.deserialize(r)]
            except KeyError:
                raise ThunderdomeQueryError('Vertex type "{}" is unknown'.format(
                    r.get('element_type', '')
                ))
            
        if as_dict:
            return {v.vid:v for v in objects}
        
        return objects

    def _reload_values(self):
        """
        Method for reloading the current vertex by reading its current values
        from the database.
        """
        results = execute_query('g.v(eid)', {'eid':self.eid})[0]
        del results['_id']
        del results['_type']
        return results

    @classmethod
    def get(cls, vid):
        """
        Look up vertex by thunderdome assigned UUID. Raises a DoesNotExist
        exception if a vertex with the given vid was not found. Raises a
        MultipleObjectsReturned exception if the vid corresponds to more than
        one vertex in the graph.

        :param vid: The thunderdome assigned UUID
        :type vid: str
        :rtype: thunderdome.models.Vertex
        
        """
        try:
            results = cls.all([vid])
            if len(results) >1:
                raise cls.MultipleObjectsReturned

            result = results[0]
            if not isinstance(result, cls):
                raise WrongElementType(
                    '{} is not an instance or subclass of {}'.format(result.__class__.__name__, cls.__name__)
                )
            return result
        except ThunderdomeQueryError:
            raise cls.DoesNotExist
    
    @classmethod
    def get_by_eid(cls, eid):
        """
        Look update a vertex by its Titan-specific id (eid). Raises a
        DoesNotExist exception if a vertex with the given eid was not found.

        :param eid: The numeric Titan-specific id
        :type eid: int
        :rtype: thunderdome.models.Vertex
        
        """
        results = execute_query('g.v(eid)', {'eid':eid})
        if not results:
            raise cls.DoesNotExist
        return Element.deserialize(results[0])
    
    def save(self, *args, **kwargs):
        """
        Save the current vertex using the configured save strategy, the default
        save strategy is to re-save all fields every time the object is saved.
        """
        super(Vertex, self).save(*args, **kwargs)
        params = self.as_save_params()
        params['element_type'] = self.get_element_type()
        result = self._save_vertex(params)[0]
        self.eid = result.eid
        for k,v in self._values.items():
            v.previous_value = result._values[k].previous_value
        return result
    
    def delete(self):
        """
        Delete the current vertex from the graph.
        """
        if self.__abstract__:
            raise ThunderdomeException('cant delete abstract elements')
        if self.eid is None:
            return self
        query = """
        g.removeVertex(g.v(eid))
        g.stopTransaction(SUCCESS)
        """
        results = execute_query(query, {'eid': self.eid})
        
    def _simple_traversal(self,
                          operation,
                          labels,
                          limit=None,
                          offset=None,
                          types=None):
        """
        Perform simple graph database traversals with ubiquitous pagination.

        :param operation: The operation to be performed
        :type operation: str
        :param labels: The edge labels to be used
        :type labels: list of Edges or strings
        :param start: The starting offset
        :type start: int
        :param max_results: The maximum number of results to return
        :type max_results: int
        :param types: The list of allowed result elements
        :type types: list
        
        """
        label_strings = []
        for label in labels:
            if inspect.isclass(label) and issubclass(label, Edge):
                label_string = label.get_label()
            elif isinstance(label, Edge):
                label_string = label.get_label()
            elif isinstance(label, basestring):
                label_string = label
            else:
                raise ThunderdomeException('traversal labels must be edge classes, instances, or strings')
            label_strings.append(label_string)

        allowed_elts = None
        if types is not None:
            allowed_elts = []
            for e in types:
                if issubclass(e, Vertex):
                    allowed_elts += [e.get_element_type()]
                elif issubclass(e, Edge):
                    allowed_elts += [e.get_label()]

        if limit is not None and offset is not None:
            start = offset
            end = offset + limit
        else:
            start = end = None
        
        return self._traversal(operation,
                               label_strings,
                               start,
                               end,
                               allowed_elts)

    def _simple_deletion(self, operation, labels):
        """
        Perform simple bulk graph deletion operation.

        :param operation: The operation to be performed
        :type operation: str
        :param label: The edge label to be used
        :type label: str or Edge
        
        """
        label_strings = []
        for label in labels:
            if inspect.isclass(label) and issubclass(label, Edge):
                label_string = label.get_label()
            elif isinstance(label, Edge):
                label_string = label.get_label()
            label_strings.append(label_string)

        return self._delete_related(operation, label_strings)

    def outV(self, *labels, **kwargs):
        """
        Return a list of vertices reached by traversing the outgoing edge with
        the given label.
        
        :param labels: pass in the labels to follow in as positional arguments
        :type labels: str or BaseEdge
        :param limit: The number of the page to start returning results at
        :type limit: int or None
        :param offset: The maximum number of results to return
        :type offset: int or None
        :param types: A list of allowed element types
        :type types: list
        
        """
        return self._simple_traversal('outV', labels, **kwargs)

    def inV(self, *labels, **kwargs):
        """
        Return a list of vertices reached by traversing the incoming edge with
        the given label.
        
        :param label: The edge label to be traversed
        :type label: str or BaseEdge
        :param limit: The number of the page to start returning results at
        :type limit: int or None
        :param offset: The maximum number of results to return
        :type offset: int or None
        :param types: A list of allowed element types
        :type types: list

        """
        return self._simple_traversal('inV', labels, **kwargs)

    def outE(self, *labels, **kwargs):
        """
        Return a list of edges with the given label going out of this vertex.
        
        :param label: The edge label to be traversed
        :type label: str or BaseEdge
        :param limit: The number of the page to start returning results at
        :type limit: int or None
        :param offset: The maximum number of results to return
        :type offset: int or None
        :param types: A list of allowed element types
        :type types: list
        
        """
        return self._simple_traversal('outE', labels, **kwargs)

    def inE(self, *labels, **kwargs):
        """
        Return a list of edges with the given label coming into this vertex.
        
        :param label: The edge label to be traversed
        :type label: str or BaseEdge
        :param limit: The number of the page to start returning results at
        :type limit: int or None
        :param offset: The maximum number of results to return
        :type offset: int or None
        :param types: A list of allowed element types
        :type types: list
        
        """
        return self._simple_traversal('inE', labels, **kwargs)

    def bothE(self, *labels, **kwargs):
        """
        Return a list of edges both incoming and outgoing from this vertex.

        :param label: The edge label to be traversed (optional)
        :type label: str or BaseEdge or None
        :param limit: The number of the page to start returning results at
        :type limit: int or None
        :param offset: The maximum number of results to return
        :type offset: int or None
        :param types: A list of allowed element types
        :type types: list
        
        """
        return self._simple_traversal('bothE', labels, **kwargs)

    def bothV(self, *labels, **kwargs):
        """
        Return a list of vertices both incoming and outgoing from this vertex.

        :param label: The edge label to be traversed (optional)
        :type label: str or BaseEdge or None
        :param limit: The number of the page to start returning results at
        :type limit: int or None
        :param offset: The maximum number of results to return
        :type offset: int or None
        :param types: A list of allowed element types
        :type types: list
        
        """
        return self._simple_traversal('bothV', labels, **kwargs)


    def delete_outE(self, *labels):
        """Delete all outgoing edges with the given label."""
        self._simple_deletion('outE', labels)

    def delete_inE(self, *labels):
        """Delete all incoming edges with the given label."""
        self._simple_deletion('inE', labels)

    def delete_outV(self, *labels):
        """Delete all outgoing vertices connected with edges with the given label."""
        self._simple_deletion('outV', labels)

    def delete_inV(self, *labels):
        """Delete all incoming vertices connected with edges with the given label."""
        self._simple_deletion('inV', labels)

    def query(self):
        return Query(self)

        
        
def to_offset(page_num, per_page):
    """
    Convert a page_num and per_page to offset.

    :param page_num: The current page number
    :type page_num: int
    :param per_page: The maximum number of results per page
    :type per_page: int
    :rtype: int
    
    """
    if page_num and per_page:
        return (page_num-1) * per_page
    else:
        return None
    
    
class PaginatedVertex(Vertex):
    """
    Convenience class to easily handle pagination for traversals
    """

    @staticmethod
    def _transform_kwargs(kwargs):
        """
        Transforms paginated kwargs into limit/offset kwargs
        :param kwargs:
        :return:
        """
        values = kwargs.copy()
        return {
            'limit': kwargs.get('per_page'),
            'offset': to_offset(kwargs.get('page_num'), kwargs.get('per_page')),
            'types': kwargs.get('types'),
        }

    __abstract__ = True
    def outV(self, *labels, **kwargs):
        """
        :param labels: pass in the labels to follow in as positional arguments
        :param page_num: the page number to return
        :param per_page: the number of objects to return per page
        :param types: the element types this method is allowed to return
        :return:
        """
        return super(PaginatedVertex, self).outV(*labels, **self._transform_kwargs(kwargs))
    
    def outE(self, *labels, **kwargs):
        """
        :param labels: pass in the labels to follow in as positional arguments
        :param page_num: the page number to return
        :param per_page: the number of objects to return per page
        :param types: the element types this method is allowed to return
        :return:
        """
        return super(PaginatedVertex, self).outE(*labels, **self._transform_kwargs(kwargs))
            
    def inV(self, *labels, **kwargs):
        """
        :param labels: pass in the labels to follow in as positional arguments
        :param page_num: the page number to return
        :param per_page: the number of objects to return per page
        :param types: the element types this method is allowed to return
        :return:
        """
        return super(PaginatedVertex, self).inV(*labels, **self._transform_kwargs(kwargs))
    
    def inE(self, *labels, **kwargs):
        """
        :param labels: pass in the labels to follow in as positional arguments
        :param page_num: the page number to return
        :param per_page: the number of objects to return per page
        :param types: the element types this method is allowed to return
        :return:
        """
        return super(PaginatedVertex, self).inE(*labels, **self._transform_kwargs(kwargs))
    
    def bothV(self, *labels, **kwargs):
        """
        :param labels: pass in the labels to follow in as positional arguments
        :param page_num: the page number to return
        :param per_page: the number of objects to return per page
        :param types: the element types this method is allowed to return
        :return:
        """
        return super(PaginatedVertex, self).bothV(*labels, **self._transform_kwargs(kwargs))
    
    def bothE(self, *labels, **kwargs):
        """
        :param labels: pass in the labels to follow in as positional arguments
        :param page_num: the page number to return
        :param per_page: the number of objects to return per page
        :param types: the element types this method is allowed to return
        :return:
        """
        return super(PaginatedVertex, self).bothE(*labels, **self._transform_kwargs(kwargs))
    
    
class EdgeMetaClass(ElementMetaClass):
    """Metaclass for edges."""
    
    def __new__(cls, name, bases, attrs):
        #short circuit element_type inheritance
        attrs['label'] = attrs.pop('label', None)

        klass = super(EdgeMetaClass, cls).__new__(cls, name, bases, attrs)

        if not klass.__abstract__:
            label = klass.get_label()
            if label in edge_types and str(edge_types[label]) != str(klass):
                raise ElementDefinitionException('{} is already registered as an edge'.format(label))
            edge_types[klass.get_label()] = klass
        return klass

    
class Edge(Element):
    """Base class for all edges."""
    
    __metaclass__ = EdgeMetaClass
    __abstract__ = True

    # if set to True, no more than one edge will
    # be created between two vertices
    __exclusive__ = False
    
    label = None
    
    gremlin_path = 'edge.groovy'
    
    _save_edge = GremlinMethod()
    _get_edges_between = GremlinMethod(classmethod=True)
    
    def __init__(self, outV, inV, **values):
        """
        Initialize this edge with the outgoing and incoming vertices as well as
        edge properties.

        :param outV: The vertex this edge is coming out of
        :type outV: Vertex
        :param inV: The vertex this edge is going into
        :type inV: Vertex
        :param values: The properties for this edge
        :type values: dict
        
        """
        self._outV = outV
        self._inV = inV
        super(Edge, self).__init__(**values)
        
    @classmethod
    def get_label(cls):
        """
        Returns the label for this edge.

        :rtype: str
        
        """
        return cls._type_name(cls.label)
    
    @classmethod
    def get_between(cls, outV, inV, page_num=None, per_page=None):
        """
        Return all the edges with a given label between two vertices.
        
        :param outV: The vertex the edge comes out of.
        :type outV: Vertex
        :param inV: The vertex the edge goes into.
        :type inV: Vertex
        :param page_num: The page number of the results
        :type page_num: int
        :param per_page: The number of results per page
        :type per_page : int
        :rtype: list
        
        """
        return cls._get_edges_between(out_v=outV,
                                      in_v=inV,
                                      label=cls.get_label(),
                                      page_num=page_num,
                                      per_page=per_page)
    
    def validate(self):
        """
        Perform validation of this edge raising a ValidationError if any
        problems are encountered.
        """
        if self.eid is None:
            if self._inV is None:
                raise ValidationError('in vertex must be set before saving new edges')
            if self._outV is None:
                raise ValidationError('out vertex must be set before saving new edges')
        super(Edge, self).validate()
        
    def save(self, *args, **kwargs):
        """
        Save this edge to the graph database.
        """
        super(Edge, self).save(*args, **kwargs)
        return self._save_edge(self._outV,
                               self._inV,
                               self.get_label(),
                               self.as_save_params(),
                               exclusive=self.__exclusive__)[0]

    def _reload_values(self):
        """
        Re-read the values for this edge from the graph database.
        """
        results = execute_query('g.e(eid)', {'eid':self.eid})[0]
        del results['_id']
        del results['_type']
        return results

    @classmethod
    def get_by_eid(cls, eid):
        """
        Return the edge with the given Titan-specific eid. Raises a
        DoesNotExist exception if no edge is found.

        :param eid: The Titan-specific edge id (eid)
        :type eid: int
        
        """
        results = execute_query('g.e(eid)', {'eid':eid})
        if not results:
            raise cls.DoesNotExist
        return Element.deserialize(results[0])

    @classmethod
    def create(cls, outV, inV, *args, **kwargs):
        """
        Create a new edge of the current type coming out of vertex outV and
        going into vertex inV with the given properties.

        :param outV: The vertex the edge is coming out of
        :type outV: Vertex
        :param inV: The vertex the edge is going into
        :type inV: Vertex
        
        """
        return super(Edge, cls).create(outV, inV, *args, **kwargs)
    
    def delete(self):
        """
        Delete the current edge from the graph.
        """
        if self.__abstract__:
            raise ThunderdomeException('cant delete abstract elements')
        if self.eid is None:
            return self
        query = """
        e = g.e(eid)
        if (e != null) {
          g.removeEdge(e)
          g.stopTransaction(SUCCESS)
        }
        """        
        results = execute_query(query, {'eid':self.eid})

    def _simple_traversal(self, operation):
        """
        Perform a simple traversal starting from the current edge returning a
        list of results.

        :param operation: The operation to be performed
        :type operation: str
        :rtype: list
        
        """
        results = execute_query('g.e(eid).%s()'%operation, {'eid':self.eid})
        return [Element.deserialize(r) for r in results]
        
    def inV(self):
        """
        Return the vertex that this edge goes into.

        :rtype: Vertex
        
        """
        if self._inV is None:
            self._inV = self._simple_traversal('inV')
        elif isinstance(self._inV, (int, long)):
            self._inV = Vertex.get_by_eid(self._inV)
        return self._inV
    
    def outV(self):
        """
        Return the vertex that this edge is coming out of.

        :rtype: Vertex
        
        """
        if self._outV is None:
            self._outV = self._simple_traversal('outV')
        elif isinstance(self._outV, (int, long)):
            self._outV = Vertex.get_by_eid(self._outV)
        return self._outV



import copy

class Query(object):
    """
    All query operations return a new query object, which currently deviates from blueprints.
    The blueprints query object modifies and returns the same object
    This method seems more flexible, and consistent w/ the rest of Gremlin.
    """
    _limit = None

    def __init__(self, vertex):
        self._vertex = vertex
        self._has = []
        self._interval = []
        self._labels = []
        self._direction = []
        self._vars = {}

    def count(self):
        """
        :return: number of matching vertices
        :rtype int
        """
        return self._execute('count', deserialize=False)[0]

    def direction(self, direction):
        """
        :param direction:
        :rtype: Query
        """
        q = copy.copy(self)
        if self._direction:
            raise ThunderdomeQueryError("Direction already set")
        q._direction = direction
        return q

    def edges(self):
        """
        :return list of matching edges
        """
        return self._execute('edges')

    def has(self, key, value, compare=EQUAL):
        """
        :param key: str
        :param value: str, float, int
        :param compare:
        :rtype: Query
        """
        compare = "Query.Compare.{}".format(compare)

        q = copy.copy(self)
        q._has.append((key,value,compare))
        return q

    def interval(self, key, start, end):
        """
        :rtype : Query
        """
        if start > end:
            start, end = end, start

        q = copy.copy(self)
        q._interval.append((key, start, end))
        return q


    def labels(self, *args):
        """
        :param args: list of Edges
        :return: Query
        """
        tmp = []
        for x in args:
            try:
                tmp.append(x.get_label())
            except:
                tmp.append(x)

        q = copy.copy(self)
        q._labels = tmp
        return q

    def limit(self, limit):
        q = copy.copy(self)
        q._limit = limit
        return q

    def vertexIds(self):
        return self._execute('vertexIds', deserialize=False)

    def vertices(self):
        return self._execute('vertices')

    def _get_partial(self):
        limit = ".limit(limit)" if self._limit else ""
        dir = ".direction({})".format(self._direction) if self._direction else ""

        # do labels
        labels = ""
        if self._labels:
            labels = ["'{}'".format(x) for x in self._labels]
            labels = ", ".join(labels)
            labels = ".labels({})".format(labels)

        ### construct has clauses
        has = []

        for x in self._has:
            c = "v{}".format(len(self._vars))
            self._vars[c] = x[1]

            val = "{} as double".format(c) if isinstance(x[1], float) else c
            key = x[0]
            has.append("has('{}', {}, {})".format(key, val, x[2]))

        if has:
            tmp = ".".join(has)
            has = '.{}'.format(tmp)
        else:
            has = ""
        ### end construct has clauses

        intervals = []
        for x in self._interval:
            c = "v{}".format(len(self._vars))
            self._vars[c] = x[1]
            c2 = "v{}".format(len(self._vars))
            self._vars[c2] = x[2]


            val1 = "{} as double".format(c) if isinstance(x[1], float) else c
            val2 = "{} as double".format(c2) if isinstance(x[2], float) else c2

            tmp = "interval('{}', {}, {})".format(x[0], val1, val2)
            intervals.append(tmp)

        if intervals:
            intervals = ".{}".format(".".join(intervals))
        else:
            intervals = ""

        return "g.v(eid).query(){}{}{}{}{}".format(labels, limit, dir, has, intervals)

    def _execute(self, func, deserialize=True):
        tmp = "{}.{}()".format(self._get_partial(), func)
        self._vars.update({"eid":self._vertex.eid, "limit":self._limit})
        results = execute_query(tmp, self._vars)

        if deserialize:
            return  [Element.deserialize(r) for r in results]
        else:
            return results







########NEW FILE########
__FILENAME__ = properties
# Copyright (c) 2012-2013 SHIFT.com
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of
# this software and associated documentation files (the "Software"), to deal in
# the Software without restriction, including without limitation the rights to
# use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of
# the Software, and to permit persons to whom the Software is furnished to do so,
# subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS
# FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
# COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER
# IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
# CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

import copy
from datetime import datetime
from decimal import Decimal as D
import re
import time
import warnings
from uuid import uuid1, uuid4
from uuid import UUID as _UUID

from thunderdome.exceptions import ValidationError

# Saving strategies for thunderdome. These are used to indicate when a property
# should be saved after the initial vertex/edge creation.
#
# SAVE_ONCE     - Only save this value once. If it changes throw an exception.
# SAVE_ONCHANGE - Only save this value if it has changed.
# SAVE_ALWAYS   - Save this value every time the corresponding model is saved.

SAVE_ONCE = 1
SAVE_ONCHANGE = 2
SAVE_ALWAYS = 3


class BaseValueManager(object):
    """
    Value managers are used to manage values pulled from the database and
    track state changes.
    """

    def __init__(self, instance, column, value):
        """
        Initialize the value manager.

        :param instance: An object instance
        :type instance: mixed
        :param column: The column to manage
        :type column: thunder.columns.Column
        :param value: The initial value of the column
        :type value: mixed

        """
        self._create_private_fields()

        self.instance = instance
        self.column = column
        self.previous_value = value
        self.value = value

    def _create_private_fields(self):
        self._previous_value = None

    @property
    def previous_value(self):
        return self._previous_value

    @previous_value.setter
    def previous_value(self, val):
        self._previous_value = copy.copy(val)

    @property
    def deleted(self):
        """
        Indicates whether or not this value has been deleted.

        :rtype: boolean

        """
        return self.value is None and self.previous_value is not None

    @property
    def changed(self):
        """
        Indicates whether or not this value has changed.

        :rtype: boolean

        """
        return self.value != self.previous_value

    def getval(self):
        """Return the current value."""
        return self.value

    def setval(self, val):
        """
        Updates the current value.

        :param val: The new value
        :type val: mixed

        """
        self.value = val

    def delval(self):
        """Delete a given value"""
        self.value = None

    def get_property(self):
        """
        Returns a value-managed property attributes

        :rtype: property

        """
        _get = lambda slf: self.getval()
        _set = lambda slf, val: self.setval(val)
        _del = lambda slf: self.delval()

        if self.column.can_delete:
            return property(_get, _set, _del)
        else:
            return property(_get, _set)


class Column(object):
    """Base class for column types"""

    value_manager = BaseValueManager
    instance_counter = 0

    def __init__(self,
                 primary_key=False,
                 index=False,
                 db_field=None,
                 default=None,
                 required=False,
                 save_strategy=None):
        """
        Initialize this column with the given information.

        :param primary_key: Indicates whether or not this is primary key
        :type primary_key: boolean
        :param index: Indicates whether or not this field should be indexed
        :type index: boolean
        :param db_field: The fieldname this field will map to in the database
        :type db_field: str
        :param default: Value or callable with no args to set default value
        :type default: mixed or callable
        :param required: Whether or not this field is required
        :type required: boolean
        :param save_strategy: Strategy used when saving the value of the column
        :type save_strategy: int

        """
        self.primary_key = primary_key
        self.index = index
        self.db_field = db_field
        self.default = default
        self.required = required
        self.save_strategy = save_strategy

        #the column name in the model definition
        self.column_name = None

        self.value = None

        #keep track of instantiation order
        self.position = Column.instance_counter
        Column.instance_counter += 1

    def validate(self, value):
        """
        Returns a cleaned and validated value. Raises a ValidationError
        if there's a problem
        """
        if value is None:
            if self.has_default:
                return self.get_default()
            elif self.required:
                raise ValidationError('{} - None values are not allowed'.format(self.column_name or self.db_field))
        return value

    def to_python(self, value):
        """
        Converts data from the database into python values
        raises a ValidationError if the value can't be converted
        """
        return value

    def to_database(self, value):
        """
        Converts python value into database value
        """
        if value is None and self.has_default:
            return self.get_default()
        return value

    @property
    def has_default(self):
        """
        Indicates whether or not this column has a default value.

        :rtype: boolean

        """
        return self.default is not None

    @property
    def has_save_strategy(self):
        """
        Indicates whether or not this column has a save strategy.

        :rtype: boolean

        """
        return self.save_strategy is not None

    @property
    def can_delete(self):
        return not self.primary_key

    def get_save_strategy(self):
        """
        Returns the save strategy attached to this column.

        :rtype: int or None

        """
        return self.save_strategy

    def get_default(self):
        """
        Returns the default value for this column if one is available.

        :rtype: mixed or None

        """
        if self.has_default:
            if callable(self.default):
                return self.default()
            else:
                return self.default

    def set_column_name(self, name):
        """
        Sets the column name during document class construction This value will
        be ignored if db_field is set in __init__

        :param name: The name of this column
        :type name: str

        """
        self.column_name = name

    @property
    def db_field_name(self):
        """Returns the name of the thunderdome name of this column"""
        return self.db_field or self.column_name


class String(Column):

    def __init__(self, *args, **kwargs):
        required = kwargs.get('required', False)
        self.min_length = kwargs.pop('min_length', 1 if required else None)
        self.max_length = kwargs.pop('max_length', None)
        self.encoding = kwargs.pop('encoding', 'utf-8')
        if 'default' in kwargs and isinstance(kwargs['default'], basestring):
            kwargs['default'] = kwargs['default'].encode(self.encoding)
        super(Text, self).__init__(*args, **kwargs)

    def validate(self, value):
        # Make sure that shit gets encoded properly
        if isinstance(value, unicode):
            value = value.encode(self.encoding)

        value = super(Text, self).validate(value)

        if value is None:
            return None

        if not isinstance(value, basestring) and value is not None:
            raise ValidationError('{} is not a string'.format(type(value)))
        if self.max_length:
            if len(value) > self.max_length:
                raise ValidationError('{} is longer than {} characters'.format(self.column_name, self.max_length))
        if self.min_length:
            if len(value) < self.min_length:
                raise ValidationError('{} is shorter than {} characters'.format(self.column_name, self.min_length))
        return value

Text = String

class Integer(Column):

    def validate(self, value):
        val = super(Integer, self).validate(value)

        if val is None:
            return

        try:
            return long(val)
        except (TypeError, ValueError):
            raise ValidationError("{} can't be converted to integral value".format(value))

    def to_python(self, value):
        if value is not None:
            return long(value)

    def to_database(self, value):
        value = super(Integer, self).to_database(value)
        if value is not None:
            return long(value)


class DateTime(Column):

    def __init__(self, strict=True, **kwargs):
        """
        Initialize date-time column with the given settings.

        :param strict: Whether or not to attempt to automatically coerce types
        :type strict: boolean
        
        """
        self.strict = strict
        super(DateTime, self).__init__(**kwargs)

    def to_python(self, value):
        if isinstance(value, datetime):
            return value
        return datetime.fromtimestamp(float(value))

    def to_database(self, value):
        value = super(DateTime, self).to_database(value)
        if value is None:
            return
        if not isinstance(value, datetime):
            if not self.strict and isinstance(value, (basestring, int, float)):
                value = datetime.fromtimestamp(float(value))
            else:
                raise ValidationError("'{}' is not a datetime object".format(value))

        tmp = time.mktime(value.timetuple()) # gives us a float with .0
        # microtime is a 6 digit int, so we bring it down to .xxx and add it to the float TS
        tmp = tmp + float(value.microsecond) / 1000000
        return tmp


class UUID(Column):
    """Universally Unique Identifier (UUID) type - UUID4 by default"""
    
    re_uuid = re.compile(r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}')

    def __init__(self, default=lambda: str(uuid4()), **kwargs):
        super(UUID, self).__init__(default=default, **kwargs)

    def validate(self, value):
        val = super(UUID, self).validate(value)

        if val is None:
            return None  # if required = False and not given
        if not self.re_uuid.match(str(val)):
            raise ValidationError("{} is not a valid uuid".format(value))
        return val

    def to_python(self, value):
        val = super(UUID, self).to_python(value)
        return str(val)

    def to_database(self, value):
        val = super(UUID, self).to_database(value)
        if val is None:
            return
        return str(val)


class Boolean(Column):

    def to_python(self, value):
        return bool(value)

    def to_database(self, value):
        val = super(Boolean, self).to_database(value)
        return bool(val)


class Double(Column):

    def __init__(self, **kwargs):
        self.db_type = 'double'
        super(Double, self).__init__(**kwargs)

    def validate(self, value):
        val = super(Double, self).validate(value)
        if val is None:
            return None  # required = False
        try:
            return float(value)
        except (TypeError, ValueError):
            raise ValidationError("{} is not a valid double".format(value))

    def to_python(self, value):
        if value is not None:
            return float(value)

    def to_database(self, value):
        value = super(Double, self).to_database(value)
        if value is not None:
            return float(value)


class Float(Double):
    """Float class for backwards compatability / if you really want to"""
    
    def __init__(self, **kwargs):
        warnings.warn("Float type is deprecated. Please use Double.",
                      category=DeprecationWarning)
        super(Float, self).__init__(**kwargs)


class Decimal(Column):

    def to_python(self, value):
        val = super(Decimal, self).to_python(value)
        if val is not None:
            return D(val)

    def to_database(self, value):
        val = super(Decimal, self).to_database(value)
        if val is not None:
            return str(val)


class Dictionary(Column):

    def validate(self, value):
        val = super(Dictionary, self).validate(value)
        if val is None:
            return None  # required = False
        if not isinstance(val, dict):
            raise ValidationError('{} is not a valid dict'.format(val))
        return val


class List(Column):

    def validate(self, value):
        val = super(List, self).validate(value)
        if val is None:
            return None  # required = False
        if not isinstance(val, (list, tuple)):
            raise ValidationError('{} is not a valid list'.format(val))
        return val

########NEW FILE########
__FILENAME__ = spec
# Copyright (c) 2012-2013 SHIFT.com
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of
# this software and associated documentation files (the "Software"), to deal in
# the Software without restriction, including without limitation the rights to
# use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of
# the Software, and to permit persons to whom the Software is furnished to do so,
# subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS
# FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
# COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER
# IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
# CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

import json


class Property(object):
    """Abstracts a property parsed from a spec file."""

    def __init__(self, name, data_type, functional=False, locking=True, indexed=False, unique=False):
        """
        Defines a property parsed from a spec file.

        :param name: The name of the property
        :type name: str
        :param data_type: The Java data type to be used for this property
        :type data_type: str
        :param functional: Indicates whether or not this is a functional property
        :type functional: boolean
        :param locking: Indicates whether or not to make this a locking property
        :type locking: boolean
        :param index: Indicates whether or not this field should be indexed
        :type index: boolean

        """
        self.name = name
        self.data_type = data_type
        self.functional = functional
        self.locking = locking
        self.indexed = indexed
        self.unique = unique

    @property
    def gremlin(self):
        """
        Return the gremlin code for creating this property.

        :rtype: str

        """
        initial = '{} = g.makeType().name("{}").dataType({}.class).{}{}{}makePropertyKey()'
        func = ''
        idx = ''
        if self.functional:
            func = 'functional({}).'.format("true" if self.locking else "false")
        if self.indexed:
            idx = 'indexed().'

        unique = "unique()." if self.unique else ""

        return initial.format(self.name, self.name, self.data_type, func, idx, unique)


class Edge(object):
    """Abstracts an edge parsed from a spec file."""

    def __init__(self, label, primary_key=None, functional=False):
        """
        Defines an edge parsed from a spec file.

        :param label: The label for this edge
        :type label: str
        :param primary_key: The primary key for this edge
        :type primary_key: thunderdome.spec.Property or None

        """
        self.label = label
        self.primary_key = primary_key
        self.functional = functional

    @property
    def gremlin(self):
        """
        Return the gremlin code for creating this edge.

        :rtype: str

        """
        initial = '{} = g.makeType().name("{}").{}{}makeEdgeLabel()'
        primary_key = ''
        if self.primary_key:
            primary_key = "primaryKey({}).".format(self.primary_key)

        functional = "functional()." if self.functional else ""

        return initial.format(self.label, self.label, primary_key, functional)


class KeyIndex(object):
    """Abstracts key index parsed from spec file."""

    def __init__(self, name, data_type="Vertex"):
        """
        Defines a key index parsed from spec file.

        :param name: The name for this key index
        :type name: str
        :param data_type: The data type for this key index
        :type data_type: str
        
        """
        self.name = name
        self.data_type = data_type

    @property
    def gremlin(self):
        """
        Return the gremlin code for creating this key index.

        :rtype: str
        
        """
        initial = 'g.createKeyIndex("{}", {}.class)'
        return initial.format(self.name, self.data_type)


class Default(object):
    """Abstracts defaults parsed from the spec file."""

    def __init__(self, spec_type, values):
        """
        Defines defaults for the given type.

        :param spec_type: The spec type these defaults are for
        (eg. property, edge)
        :type spec_type: str
        :param values: The default values
        :type values: dict
        
        """
        self._values = values
        self._spec_type = spec_type

    def get_spec_type(self):
        """
        Return the spec type this default is for.

        :rtype: str
        
        """
        return self._spec_type

    def get_default(self, stmt, key):
        """
        Return the default value for the given key on the given statement.
        Basically this will see if the stmt defines a value for the given
        key and if not use a default if possible.

        :param stmt: Single spec file statement
        :type stmt: dict
        :param key: The key to be searched for
        :type key: str

        :rtype: mixed
        
        """
        default = None
        if key in self._values:
            default = self._values[key]
        return stmt.get(key, default)


class SpecParser(object):
    """
    Parser for a spec file describing properties and primary keys for edges.
    This file is used to ensure duplicate primary keys are not created.

    File format:

    [
        {
            "type":"defaults",
            "spec_type": "property",
            "functional": false,
            "indexed": false,
            "locking": false
        },
        {
            "type":"property",
            "name":"updated_at",
            "data_type":"Integer",
            "functional":true,
            "locking": true,
            "indexed": true
        },
        {
            "type":"edge",
            "label":"subscribed_to",
            "primary_key":"updated_at"
        },
        {
            "type": "key_index",
            "name": "email",
            "type": "Vertex"
        }
    ]

    """

    def __init__(self, filename=None):
        """
        Pass in the filename of the spec to be parsed

        :param filename: The path to the file to be parsed
        :type filename: str

        """
        self._specs = self._load_spec(filename)
        self._properties = {}
        self._names = []
        self._defaults = {}

    def _load_spec(self, filename=None):
        """
        Loads the spec with the given filename or returns an empty
        list.

        :param filename: The filename to be opened (optional)
        :type filename: str or None
        :rtype: list

        """
        specs = []
        if filename:
            with open(filename) as spec_file:
                specs = json.load(spec_file)
        return specs

    def parse(self):
        """
        Parse the internal spec and return a list of gremlin statements.

        :rtype: list

        """
        self._properties = {}
        self._names = []

        self._results = []
        for x in self._specs:
            result = self.parse_statement(x)
            if result:
                self._results.append(result)
        self.validate(self._results)
        return self._results

    def validate(self, results):
        """
        Validate the given set of results.

        :param results: List of parsed objects
        :type results: list

        """
        edges = [x for x in results if isinstance(x, Edge)]
        props = {x.name: x for x in results if isinstance(x, Property)}

        for e in edges:
            if e.primary_key and e.primary_key not in props:
                raise ValueError('Missing primary key {} for edge {}'.format(e.primary_key, e.label))

    def parse_property(self, stmt):
        """
        Build object for a new property type.

        :param stmt: The statement to be parsed
        :type stmt: str

        :rtype: thunderdome.spec.Property

        """
        if stmt['name'] in self._properties:
            raise ValueError('There is already a property called {}'.format(stmt['name']))
        if stmt['name'] in self._names:
            raise ValueError('There is already a value with name {}'.format(stmt['name']))
        # Right now only support defaults for properties
        if 'property' in self._defaults:
            defaults = self._defaults['property']
            stmt['functional'] = defaults.get_default(stmt, 'functional')
            stmt['locking'] = defaults.get_default(stmt, 'locking')
            stmt['indexed'] = defaults.get_default(stmt, 'indexed')
            stmt['unique'] = defaults.get_default(stmt, 'unique')

        prop = Property(name=stmt['name'],
                        data_type=stmt['data_type'],
                        functional=stmt.get('functional', False),
                        locking=stmt.get('locking', True),
                        indexed=stmt.get('indexed', False),
                        unique=stmt.get('unique', False))

        self._properties[prop.name] = prop
        self._names += [prop.name]
        return prop

    def parse_edge(self, stmt):
        """
        Build object for a new edge with a primary key.

        :param stmt: The statement to be parsed
        :type stmt: str

        :rtype: thunderdome.spec.Edge

        """
        if stmt['label'] in self._names:
            raise ValueError('There is already a value with name {}'.format(stmt['label']))
        edge = Edge(label=stmt['label'],
                    primary_key=stmt.get('primary_key', None),
                    functional=stmt.get('functional', False))
        self._names += [edge.label]
        return edge

    def parse_key_index(self, stmt):
        """
        Takes the given spec statement and converts it into an object.

        :param stmt: The statement
        :type stmt: dict

        :rtype: thunderdome.spec.KeyIndex
        
        """
        if stmt['name'] in self._names:
            raise ValueError('There is already a value with name {}'.format(stmt['name']))
        key_index = KeyIndex(name=stmt['name'],
                             data_type=stmt.get('data_type', 'Vertex'))
        return key_index

    def parse_defaults(self, stmt):
        """
        Parses out statement containing default

        :param stmt: The statement
        :type stmt: dict

        :rtype: None
        
        """
        spec_type = stmt['spec_type']
        if spec_type in self._defaults:
            raise ValueError('More than one default for {}'.format(stmt['spec_type']))
        self._defaults[spec_type] = Default(spec_type, stmt)
        return None

    def parse_statement(self, stmt):
        """
        Takes the given spec statement and converts it into an object.

        :param stmt: The statement
        :type stmt: dict

        :rtype: thunderdome.spec.Property, thunderdome.spec.Edge, thunderdome.spec.KeyIndex

        """
        if 'type' not in stmt:
            raise TypeError('Type field required')

        if stmt['type'] == 'property':
            return self.parse_property(stmt)
        elif stmt['type'] == 'edge':
            return self.parse_edge(stmt)
        elif stmt['type'] == 'key_index':
            return self.parse_key_index(stmt)
        elif stmt['type'] == 'defaults':
            return self.parse_defaults(stmt)
        else:
            raise ValueError('Invalid `type` value {}'.format(stmt['type']))     


class Spec(object):
    """Represents a generic type spec for thunderdome."""

    def __init__(self, filename):
        """
        Parse and attempt to initialize the spec with the contents of the given
        file.

        :param filename: The spec file to be parsed
        :type filename: str

        """
        self._results = SpecParser(filename).parse()

    def sync(self, host, graph_name, username=None, password=None, dry_run=False):
        """
        Sync the current internal spec using the given graph on the given host.

        :param host: The host in <hostname>:<port> or <hostname> format
        :type host: str
        :param graph_name: The name of the graph as defined in rexster.xml
        :type graph_name: str
        :param username: The username for the rexster server
        :type username: str
        :param password: The password for the rexster server
        :type password: str
        :param dry_run: If true then the generated Gremlin will just be printed
        :type dry_run: boolean

        """
        def _get_name(x):
            """
            Return the name for the given object.

            :param x: The object
            :type x: Property, Edge, KeyIndex
            :rtype: str
            
            """
            if isinstance(x, Property) or isinstance(x, KeyIndex):
                return x.name
            elif isinstance(x, Edge):
                return x.label
            raise RuntimeError("Invalid object type {}".format(type(x)))
        
        if not dry_run:
            from thunderdome.connection import setup, execute_query
            setup(hosts=[host],
                  graph_name=graph_name,
                  username=username,
                  password=password,
                  index_all_fields=False)
        
        q = "def t = null"
        for x in self._results:
            name = _get_name(x)
            q += "t = g.getType('{}')\n".format(name)
            q += "if (t == null) {\n"
            q += "  {}\n".format(x.gremlin)
            q += "} else {\n"
            q += "  {} = g.getType('{}')\n".format(name, name)
            q += "}\n"
        q += "null"

        print q
        
        from thunderdome.connection import execute_query
        if not dry_run:
            return execute_query(q)

########NEW FILE########
__FILENAME__ = base
# Copyright (c) 2012-2013 SHIFT.com
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of
# this software and associated documentation files (the "Software"), to deal in
# the Software without restriction, including without limitation the rights to
# use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of
# the Software, and to permit persons to whom the Software is furnished to do so,
# subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS
# FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
# COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER
# IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
# CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

from unittest import TestCase
from thunderdome import connection

    
class BaseThunderdomeTestCase(TestCase):

    @classmethod
    def setUpClass(cls):
        super(BaseThunderdomeTestCase, cls).setUpClass()
        if not connection._hosts:
            connection.setup(['localhost'], 'thunderdome')

    def assertHasAttr(self, obj, attr):
        self.assertTrue(hasattr(obj, attr), 
                "{} doesn't have attribute: {}".format(obj, attr))

    def assertNotHasAttr(self, obj, attr):
        self.assertFalse(hasattr(obj, attr), 
                "{} shouldn't have the attribute: {}".format(obj, attr))

########NEW FILE########
__FILENAME__ = test_tables
# Copyright (c) 2012-2013 SHIFT.com
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of
# this software and associated documentation files (the "Software"), to deal in
# the Software without restriction, including without limitation the rights to
# use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of
# the Software, and to permit persons to whom the Software is furnished to do so,
# subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS
# FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
# COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER
# IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
# CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

from thunderdome.containers import Table

from unittest import TestCase

class Person(object):
    def __init__(self, name):
        self.name = name

class SomeEdge(object):
    def __init__(self, nickname):
        self.nickname = nickname
    

class TableTest(TestCase):
    def setUp(self):
        self.data = [{'v':Person('jon'), 'e':SomeEdge('rustyrazorblade')},
                     {'v':Person('eric'), 'e':SomeEdge('enasty')},
                     {'v':Person('blake'), 'e':SomeEdge('bmoney')}]
        self.t = Table(self.data)
    
    def test_length(self):
        assert len(self.t) == 3
    
    def test_iteration(self):
        i = 0
        for r in self.t:
            i += 1
            assert r.v.name is not None
        assert i == 3
        
    def test_access_element(self):
        assert self.t[0].v.name == 'jon'
        assert self.t[0].e.nickname == 'rustyrazorblade'
        
        assert self.t[1].v.name == 'eric', self.t[1].v.name
        assert self.t[2].e.nickname == 'bmoney'


class EmptyTableTest(TestCase):
    def test_empty(self):
        t = Table([])
        with self.assertRaises(IndexError):
            t[0]

    def test_empty2(self):
        t = Table([[]])
        with self.assertRaises(IndexError):
            t[0]


########NEW FILE########
__FILENAME__ = test_defaults
# Copyright (c) 2012-2013 SHIFT.com
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of
# this software and associated documentation files (the "Software"), to deal in
# the Software without restriction, including without limitation the rights to
# use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of
# the Software, and to permit persons to whom the Software is furnished to do so,
# subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS
# FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
# COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER
# IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
# CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

from datetime import datetime
from decimal import Decimal as D
import uuid

from thunderdome.properties import *
from thunderdome.tests.base import BaseThunderdomeTestCase

class TestDefaultValue(BaseThunderdomeTestCase):
    """ Tests that setting default values works on all column types """

    def test_string_default(self):
        """ Tests string defaults work properly """
        default = 'BLAKE!'
        prop = String(default=default, required=True)
        self.assertEqual(prop.to_database(None), prop.to_database(default))

    def test_integer_default(self):
        """ Tests integer defaults work properly """
        default = 5
        prop = Integer(default=5, required=True)
        self.assertEqual(prop.to_database(None), prop.to_database(default))

    def test_datetime_default(self):
        """ Tests datetime defaults work properly """
        default = datetime.now()
        prop = DateTime(default=default, required=True)
        self.assertEqual(prop.to_database(None), prop.to_database(default))

    def test_uuid_default(self):
        """ Tests uuid defaults work properly """
        default = uuid.uuid4()
        prop = UUID(default=default, required=True)
        self.assertEqual(prop.to_database(None), prop.to_database(default))

    def test_boolean_default(self):
        """ Tests boolean defaults work properly """
        default = True
        prop = Boolean(default=default, required=True)
        self.assertEqual(prop.to_database(None), prop.to_database(default))

    def test_double_default(self):
        """ Tests double defaults work properly """
        default = 7.0
        prop = Double(default=default, required=True)
        self.assertEqual(prop.to_database(None), prop.to_database(default))

    def test_decimal_default(self):
        """ Tests decimal defaults work properly """
        default = D('2.00')
        prop = Decimal(default=default, required=True)
        self.assertEqual(prop.to_database(None), prop.to_database(default))

    def test_dictionary_default(self):
        """ Tests dictionary defaults work properly """
        default = {1:2}
        prop = Dictionary(default=default, required=True)
        self.assertEqual(prop.to_database(None), prop.to_database(default))

    def test_list_default(self):
        """ Tests list defaults work properly """
        default = [1,2]
        prop = String(default=default, required=True)
        self.assertEqual(prop.to_database(None), prop.to_database(default))

########NEW FILE########
__FILENAME__ = test_validation
# Copyright (c) 2012-2013 SHIFT.com
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of
# this software and associated documentation files (the "Software"), to deal in
# the Software without restriction, including without limitation the rights to
# use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of
# the Software, and to permit persons to whom the Software is furnished to do so,
# subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS
# FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
# COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER
# IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
# CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

from datetime import datetime
from decimal import Decimal as D

from thunderdome.tests.base import BaseThunderdomeTestCase

from thunderdome.properties import Column
from thunderdome.properties import Text
from thunderdome.properties import Integer
from thunderdome.properties import DateTime
from thunderdome.properties import Dictionary
from thunderdome.properties import UUID
from thunderdome.properties import Boolean
from thunderdome.properties import Float
from thunderdome.properties import List
from thunderdome.properties import Decimal

from thunderdome.models import Vertex

from thunderdome.exceptions import ValidationError

class DatetimeTest(Vertex):
    test_id = Integer(primary_key=True)
    created_at = DateTime(required=False)
    

class DatetimeCoercionTest(Vertex):
    test_id = Integer(primary_key=True)
    created_at = DateTime(required=False, strict=False)

    
class TestDatetime(BaseThunderdomeTestCase):

    def test_datetime_io(self):
        now = datetime.now()
        dt = DatetimeTest.create(test_id=0, created_at=now)
        dt2 = DatetimeTest.get(dt.vid)
        assert dt2.created_at.timetuple()[:6] == now.timetuple()[:6]

    def test_none_handling(self):
        """
        Tests the handling of NoneType
        :return:
        """
        dt = DatetimeTest.create(test_id=0, created_at=None)

    def test_coercion_of_floats(self):
        with self.assertRaises(ValidationError):
            dt = DatetimeTest.create(test_id=1)
            dt.created_at = 12309834.234
            dt.save()

        dt2 = DatetimeCoercionTest.create(test_id=2)
        dt2.created_at = 1362470400
        dt2.save()
        dt2.created_at = 1098234098.2098
        dt2.save()
        dt2.created_at = '120398231'
        dt2.save()
        dt2.created_at = '12039823.198'
        dt2.save()
        dt2.reload()
        assert isinstance(dt2.created_at, datetime)


class DecimalTest(Vertex):
    test_id = Integer(primary_key=True)
    dec_val = Decimal()
    
class TestDecimal(BaseThunderdomeTestCase):

    def test_datetime_io(self):
        dt = DecimalTest.create(test_id=0, dec_val=D('0.00'))
        dt2 = DecimalTest.get(dt.vid)
        assert dt2.dec_val == dt.dec_val

        dt = DecimalTest.create(test_id=0, dec_val=5)
        dt2 = DecimalTest.get(dt.vid)
        assert dt2.dec_val == D('5')

class TestText(BaseThunderdomeTestCase):

    def test_max_length_validation(self):
        """
        Tests that the max_length kwarg works
        """

class TestInteger(BaseThunderdomeTestCase):

    def test_non_integral_validation(self):
        """
        Tests that attempting to save non integral values raises a ValidationError
        """

class TestFloat(BaseThunderdomeTestCase):

    def test_non_numberic_validation(self):
        """
        Tests that attempting to save a non numeric value raises a ValidationError
        """

class DictionaryTestVertex(Vertex):
    test_id = Integer(primary_key=True)
    map_val = Dictionary()

class TestDictionary(BaseThunderdomeTestCase):

    def test_dictionary_io(self):
        """ Tests that dictionary objects are saved and loaded successfully """
        dict_val = {'blake':31, 'something_else':'that'}
        v1 = DictionaryTestVertex.create(test_id=5, map_val=dict_val)
        v2 = DictionaryTestVertex.get(v1.vid)

        assert v2.map_val == dict_val

    def test_validation(self):
        """ Tests that the Dictionary column validates values properly """

        with self.assertRaises(ValidationError):
            Dictionary().validate([1,2,3])

        with self.assertRaises(ValidationError):
            Dictionary().validate('stringy')

        with self.assertRaises(ValidationError):
            Dictionary().validate(1)

class ListTestVertex(Vertex):
    test_id = Integer(primary_key=True)
    list_val = List()

class TestList(BaseThunderdomeTestCase):

    def test_dictionary_io(self):
        """ Tests that dictionary objects are saved and loaded successfully """
        list_val = ['blake', 31, 'something_else', 'that']
        v1 = ListTestVertex.create(test_id=5, list_val=list_val)
        v2 = ListTestVertex.get(v1.vid)

        assert v2.list_val == list_val

    def test_validation(self):
        """ Tests that the Dictionary column validates values properly """

        with self.assertRaises(ValidationError):
            List().validate({'blake':31, 'something_else':'that'})

        with self.assertRaises(ValidationError):
            List().validate('stringy')

        with self.assertRaises(ValidationError):
            List().validate(1)















########NEW FILE########
__FILENAME__ = test_value_manager
# Copyright (c) 2012-2013 SHIFT.com
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of
# this software and associated documentation files (the "Software"), to deal in
# the Software without restriction, including without limitation the rights to
# use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of
# the Software, and to permit persons to whom the Software is furnished to do so,
# subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS
# FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
# COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER
# IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
# CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

from datetime import datetime, timedelta

from thunderdome.properties import *
from thunderdome.tests.base import BaseThunderdomeTestCase


class TestChangedProperty(BaseThunderdomeTestCase):
    """
    Tests that the `changed` property works as intended
    """

    def test_string_update(self):
        """ Tests changes on string types """
        vm = String.value_manager(None, None, 'str')
        assert not vm.changed
        vm.value = 'unicode'
        assert vm.changed

    def test_string_inplace_update(self):
        """ Tests changes on string types """
        vm = String.value_manager(None, None, 'str')
        assert not vm.changed
        vm.value += 's'
        assert vm.changed

    def test_integer_update(self):
        """ Tests changes on string types """
        vm = Integer.value_manager(None, None, 5)
        assert not vm.changed
        vm.value = 4
        assert vm.changed

    def test_integer_inplace_update(self):
        """ Tests changes on string types """
        vm = Integer.value_manager(None, None, 5)
        assert not vm.changed
        vm.value += 1
        assert vm.changed

    def test_datetime_update(self):
        """ Tests changes on string types """
        now = datetime.now()
        vm = DateTime.value_manager(None, None, now)
        assert not vm.changed
        vm.value = now + timedelta(days=1)
        assert vm.changed

    def test_decimal_update(self):
        """ Tests changes on string types """
        vm = Decimal.value_manager(None, None, D('5.00'))
        assert not vm.changed
        vm.value = D('4.00')
        assert vm.changed

    def test_decimal_inplace_update(self):
        """ Tests changes on string types """
        vm = Decimal.value_manager(None, None, D('5.00'))
        assert not vm.changed
        vm.value += D('1.00')
        assert vm.changed

    def test_dictionary_update(self):
        """ Tests changes on string types """
        vm = Dictionary.value_manager(None, None, {1:2, 3:4})
        assert not vm.changed
        vm.value = {4:5}
        assert vm.changed

    def test_dictionary_inplace_update(self):
        """ Tests changes on string types """
        vm = Dictionary.value_manager(None, None, {1:2, 3:4})
        assert not vm.changed
        vm.value[4] = 5
        assert vm.changed

    def test_list_update(self):
        """ Tests changes on string types """
        vm = List.value_manager(None, None, [1,2,3])
        assert not vm.changed
        vm.value = [4,5,6]
        assert vm.changed

    def test_list_inplace_update(self):
        """ Tests changes on string types """
        vm = List.value_manager(None, None, [1,2,3])
        assert not vm.changed
        vm.value.append(4)
        assert vm.changed


########NEW FILE########
__FILENAME__ = test_method_loading
# Copyright (c) 2012-2013 SHIFT.com
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of
# this software and associated documentation files (the "Software"), to deal in
# the Software without restriction, including without limitation the rights to
# use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of
# the Software, and to permit persons to whom the Software is furnished to do so,
# subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS
# FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
# COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER
# IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
# CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

from datetime import datetime
from unittest import skip
from uuid import uuid4

from thunderdome.gremlin import ThunderdomeGremlinException
from thunderdome.tests.base import BaseThunderdomeTestCase

from thunderdome.models import Vertex
from thunderdome import properties
from thunderdome import gremlin

class GroovyTestModel(Vertex):
    text    = properties.Text()
    get_self = gremlin.GremlinMethod()
    cm_get_self = gremlin.GremlinMethod(method_name='get_self', classmethod=True)

    return_default = gremlin.GremlinValue(method_name='return_value', defaults={'val':lambda:5000})
    return_list = gremlin.GremlinValue(property=1)
    return_value = gremlin.GremlinValue()

    arg_test1 = gremlin.GremlinValue()
    arg_test2 = gremlin.GremlinValue()

class TestMethodLoading(BaseThunderdomeTestCase):
    
    def test_method_loads_and_works(self):
        v1 = GroovyTestModel.create(text='cross fingers')
        
        v2 = v1.get_self()
        assert v1.vid == v2[0].vid
        
        v3 = v1.cm_get_self(v1.eid)
        assert v1.vid == v3[0].vid
        

class TestMethodArgumentHandling(BaseThunderdomeTestCase):

    def test_callable_defaults(self):
        """
        Tests that callable default arguments are called
        """
        v1 = GroovyTestModel.create(text='cross fingers')
        assert v1.return_default() == 5000

    def test_gremlin_value_enforces_single_object_returned(self):
        """
        Tests that a GremlinValue instance raises an error if more than one object is returned
        """
        v1 = GroovyTestModel.create(text='cross fingers')
        with self.assertRaises(ThunderdomeGremlinException):
            v1.return_list

    def test_type_conversion(self):
        """ Tests that the gremlin method converts certain python objects to their gremlin equivalents """
        v1 = GroovyTestModel.create(text='cross fingers')

        now = datetime.now()
        assert v1.return_value(now) == properties.DateTime().to_database(now)

        uu = uuid4()
        assert v1.return_value(uu) == properties.UUID().to_database(uu)

    def test_initial_arg_name_isnt_set(self):
        """ Tests that the name of the first argument in a instance method """
        v = GroovyTestModel.create(text='cross fingers')

        assert v == v.arg_test1()
        assert v == v.arg_test2()

########NEW FILE########
__FILENAME__ = test_scanner
# Copyright (c) 2012-2013 SHIFT.com
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of
# this software and associated documentation files (the "Software"), to deal in
# the Software without restriction, including without limitation the rights to
# use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of
# the Software, and to permit persons to whom the Software is furnished to do so,
# subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS
# FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
# COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER
# IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
# CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

import os

from unittest import TestCase
from thunderdome.gremlin import parse

class GroovyScannerTest(TestCase):
    """
    Test Groovy language scanner
    """
    
    def test_parsing_complicated_function(self):
        groovy_file = os.path.join(os.path.dirname(__file__), 'groovy_test_model.groovy')
        result = parse(groovy_file)
        assert len(result[6].body.split('\n')) == 8

        result_map = {x.name: x for x in result}
        assert 'get_self' in result_map
        assert 'return_value' in result_map
        assert 'long_func' in result_map

########NEW FILE########
__FILENAME__ = mocks

########NEW FILE########
__FILENAME__ = test_class_construction
# Copyright (c) 2012-2013 SHIFT.com
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of
# this software and associated documentation files (the "Software"), to deal in
# the Software without restriction, including without limitation the rights to
# use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of
# the Software, and to permit persons to whom the Software is furnished to do so,
# subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS
# FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
# COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER
# IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
# CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

from thunderdome.tests.base import BaseThunderdomeTestCase

from thunderdome.exceptions import ModelException, ThunderdomeException
from thunderdome.models import Vertex, Edge
from thunderdome import properties, ValidationError
import thunderdome

from thunderdome.tests.models import TestModel

class WildDBNames(Vertex):
    content = properties.Text(db_field='words_and_whatnot')
    numbers = properties.Integer(db_field='integers_etc')
            
class Stuff(Vertex):
    num = properties.Integer()

class TestModelClassFunction(BaseThunderdomeTestCase):
    """
    Tests verifying the behavior of the Model metaclass
    """

    def test_column_attributes_handled_correctly(self):
        """
        Tests that column attributes are moved to a _columns dict
        and replaced with simple value attributes
        """

        #check class attibutes
        self.assertHasAttr(TestModel, '_columns')
        self.assertHasAttr(TestModel, 'vid')
        self.assertHasAttr(TestModel, 'text')

        #check instance attributes
        inst = TestModel()
        self.assertHasAttr(inst, 'vid')
        self.assertHasAttr(inst, 'text')
        self.assertIsNone(inst.vid)
        self.assertIsNone(inst.text)

    def test_db_map(self):
        """
        Tests that the db_map is properly defined
        -the db_map allows columns
        """


        db_map = WildDBNames._db_map
        self.assertEquals(db_map['words_and_whatnot'], 'content')
        self.assertEquals(db_map['integers_etc'], 'numbers')

    def test_attempting_to_make_duplicate_column_names_fails(self):
        """
        Tests that trying to create conflicting db column names will fail
        """

        with self.assertRaises(ModelException):
            class BadNames(Vertex):
                words = properties.Text()
                content = properties.Text(db_field='words')

    def test_value_managers_are_keeping_model_instances_isolated(self):
        """
        Tests that instance value managers are isolated from other instances
        """
        inst1 = TestModel(count=5)
        inst2 = TestModel(count=7)

        self.assertNotEquals(inst1.count, inst2.count)
        self.assertEquals(inst1.count, 5)
        self.assertEquals(inst2.count, 7)

class RenamedTest(thunderdome.Vertex):
    element_type = 'manual_name'
    
    vid = thunderdome.UUID(primary_key=True)
    data = thunderdome.Text()
        
class TestManualTableNaming(BaseThunderdomeTestCase):
    
    def test_proper_table_naming(self):
        assert RenamedTest.get_element_type() == 'manual_name'

class BaseAbstractVertex(thunderdome.Vertex):
    __abstract__ = True
    data = thunderdome.Text()

class DerivedAbstractVertex(BaseAbstractVertex): pass

class TestAbstractElementAttribute(BaseThunderdomeTestCase):

    def test_abstract_property_is_not_inherited(self):
        assert BaseAbstractVertex.__abstract__
        assert not DerivedAbstractVertex.__abstract__

    def test_abstract_element_persistence_methods_fail(self):
        bm = BaseAbstractVertex(data='something')

        with self.assertRaises(ThunderdomeException):
            bm.save()

        with self.assertRaises(ThunderdomeException):
            bm.delete()

        with self.assertRaises(ThunderdomeException):
            bm.update(data='something else')



class TestValidationVertex(Vertex):
    num     = thunderdome.Integer(required=True)
    num2    = thunderdome.Integer(required=True)

    def validate_num(self, value):
        val = self.validate_field('num', value)
        return 5

    def validate_num2(self, value):
        return 5

class TestValidation(BaseThunderdomeTestCase):

    def test_custom_validation_method(self):
        v = TestValidationVertex.create(num=6)
        assert v.num == 5
        assert v.num2 == 5

        with self.assertRaises(ValidationError):
            TestValidationVertex.create()











########NEW FILE########
__FILENAME__ = test_db_field
# -*- coding: utf-8 -*-
from unittest import skip
from thunderdome import connection
from thunderdome.tests.base import BaseThunderdomeTestCase

from thunderdome.tests.models import TestModel, TestEdge

from thunderdome import gremlin
from thunderdome import models
from thunderdome.models import Edge, Vertex
from thunderdome import properties

class DBFieldVertex(Vertex):
    text    = properties.Text(db_field='vertex_text')

class DBFieldEdge(Edge):
    text    = properties.Text(db_field='edge_text')

class TestDbField(BaseThunderdomeTestCase):

    def test_db_field_io(self):
        v1 = DBFieldVertex.create(text='vertex1')
        v2 = DBFieldVertex.create(text='vertex2')
        e1 = DBFieldEdge.create(v1, v2, text='edge1')

        v1_raw = connection.execute_query('g.v(eid)', params={'eid':v1.eid})
        assert v1.text == v1_raw[0]['vertex_text']

        v2_raw = connection.execute_query('g.v(eid)', params={'eid':v2.eid})
        assert v2.text == v2_raw[0]['vertex_text']

        e1_raw = connection.execute_query('g.e(eid)', params={'eid':e1.eid})
        assert e1.text == e1_raw[0]['edge_text']


########NEW FILE########
__FILENAME__ = test_edge_io
# Copyright (c) 2012-2013 SHIFT.com
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of
# this software and associated documentation files (the "Software"), to deal in
# the Software without restriction, including without limitation the rights to
# use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of
# the Software, and to permit persons to whom the Software is furnished to do so,
# subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS
# FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
# COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER
# IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
# CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

from unittest import skip

from thunderdome.tests.base import BaseThunderdomeTestCase
from thunderdome.tests.models import TestModel, TestEdge


class TestEdgeIO(BaseThunderdomeTestCase):

    def setUp(self):
        super(TestEdgeIO, self).setUp()
        self.v1 = TestModel.create(count=8, text='a')
        self.v2 = TestModel.create(count=7, text='b')
        
    def test_model_save_and_load(self):
        """
        Tests that models can be saved and retrieved
        """
        e1 = TestEdge.create(self.v1, self.v2, numbers=3)
        
        edges = self.v1.outE()
        assert len(edges) == 1
        assert edges[0].eid == e1.eid
        
    def test_model_updating_works_properly(self):
        """
        Tests that subsequent saves after initial model creation work
        """
        e1 = TestEdge.create(self.v1, self.v2, numbers=3)

        e1.numbers = 20
        e1.save()
        
        edges = self.v1.outE()
        assert len(edges) == 1
        assert edges[0].numbers == 20

    def test_model_deleting_works_properly(self):
        """q
        Tests that an instance's delete method deletes the instance
        """
        e1 = TestEdge.create(self.v1, self.v2, numbers=3)
        
        e1.delete()
        edges = self.v1.outE()
        assert len(edges) == 0

    def test_reload(self):
        """ Tests that the reload method performs an inplace update of an instance's values """
        e1 = TestEdge.create(self.v1, self.v2, numbers=3)
        e2 = TestEdge.get_by_eid(e1.eid)
        e2.numbers = 5
        e2.save()

        e1.reload()
        assert e1.numbers == 5


########NEW FILE########
__FILENAME__ = test_paginated_vertex
# Copyright (c) 2012-2013 SHIFT.com
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of
# this software and associated documentation files (the "Software"), to deal in
# the Software without restriction, including without limitation the rights to
# use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of
# the Software, and to permit persons to whom the Software is furnished to do so,
# subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS
# FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
# COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER
# IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
# CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

from unittest import skip
from thunderdome import connection 
from thunderdome.tests.base import BaseThunderdomeTestCase


from thunderdome import gremlin
from thunderdome import models
from thunderdome.models import Edge, PaginatedVertex
from thunderdome import properties
import unittest



class TestPModel(PaginatedVertex):
    count   = properties.Integer()
    text    = properties.Text(required=False)

    
class TestPEdge(Edge):
    numbers = properties.Integer()



class PaginatedVertexTest(unittest.TestCase):
    def test_traversal(self):
        t = TestPModel.create()
        t2 = TestPModel.create()
        
        edges = []
        for x in range(5):
            edges.append(TestPEdge.create(t, t2, numbers=x))
        
        tmp = t.outV(page_num=1, per_page=2)
        assert len(tmp) == 2, len(tmp)
        
        tmp = t.outE(page_num=2, per_page=2)
        
        assert len(tmp) == 2, len(tmp)
        assert tmp[0].numbers == 2
        
        tmp = t.outE(page_num=3, per_page=2)
        assert len(tmp) == 1, len(tmp)
        
        # just to be sure
        all_edges = t.outV()
        assert len(all_edges) == 5

########NEW FILE########
__FILENAME__ = test_save_strategies
# Copyright (c) 2012-2013 SHIFT.com
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of
# this software and associated documentation files (the "Software"), to deal in
# the Software without restriction, including without limitation the rights to
# use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of
# the Software, and to permit persons to whom the Software is furnished to do so,
# subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS
# FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
# COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER
# IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
# CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

import uuid
from thunderdome import connection 
from thunderdome.tests.base import BaseThunderdomeTestCase

from thunderdome.models import Edge, Vertex, SaveStrategyException
from thunderdome import properties


class OnceSaveStrategy(Vertex):
    """
    Should be enforced on vid
    """


class OnChangeSaveStrategy(Vertex):
    val = properties.Integer(save_strategy=properties.SAVE_ONCHANGE)


class AlwaysSaveStrategy(Vertex):
    val = properties.Integer(save_strategy=properties.SAVE_ALWAYS)


class ModelLevelSaveStrategy(Vertex):
    __default_save_strategy__ = properties.SAVE_ONCHANGE
    
    val = properties.Integer()


class DefaultModelLevelSaveStrategy(Vertex):
    val = properties.Integer()

    
class TestOnceSaveStrategy(BaseThunderdomeTestCase):

    def test_should_be_able_to_resave_with_once_strategy(self):
        """Once save strategy should allow saving so long as columns haven't changed'"""
        v = OnceSaveStrategy.create()
        assert 'vid' not in v.as_save_params()
        v.save()
        
    def test_should_enforce_once_save_strategy(self):
        """Should raise SaveStrategyException if once save strategy violated"""
        v = OnceSaveStrategy.create()
        v.vid = str(uuid.uuid4())

        with self.assertRaises(SaveStrategyException):
            v.save()

            
class TestOnChangeSaveStrategy(BaseThunderdomeTestCase):

    def test_should_be_able_to_save_columns_with_on_change(self):
        """Should be able to resave models with on change save policy"""
        v = OnChangeSaveStrategy.create(val=1)
        v.save()

    def test_should_persist_changes_with_on_change_strategy(self):
        """Should still persist changes with onchange save strategy"""
        v = OnChangeSaveStrategy.create(val=1)
        assert 'val' not in v.as_save_params()
        v.val = 2
        assert 'val' in v.as_save_params()
        v.save()

        v1 = OnChangeSaveStrategy.get(v.vid)
        assert v1.val == 2

        
class TestAlwaysSaveStrategy(BaseThunderdomeTestCase):

    def test_should_be_able_to_save_with_always(self):
        """Should be able to save with always save strategy"""
        v = AlwaysSaveStrategy.create(val=1)
        assert 'val' in v.as_save_params()
        v.val = 2
        assert 'val' in v.as_save_params()
        v.save()

        v1 = AlwaysSaveStrategy.get(v.vid)
        assert v1.val == 2


class TestModelLevelSaveStrategy(BaseThunderdomeTestCase):

    def test_default_save_strategy_should_be_always(self):
        """Default save strategy should be to always save"""
        v = DefaultModelLevelSaveStrategy.create(val=1)
        assert 'val' in v.as_save_params()
        v.val = 2
        assert 'val' in v.as_save_params()
        v.save()
        
    def test_should_use_default_model_save_strategy(self):
        """Should use model-level save strategy if none provided"""
        v = ModelLevelSaveStrategy.create(val=1)
        assert 'val' not in v.as_save_params()
        v.val = 2
        assert 'val' in v.as_save_params()
        v.save()

########NEW FILE########
__FILENAME__ = test_vertex_io
# -*- coding: utf-8 -*-
from unittest import skip
from thunderdome import connection
from thunderdome.exceptions import ThunderdomeException
from thunderdome.tests.base import BaseThunderdomeTestCase

from thunderdome.tests.models import TestModel, TestEdge

from thunderdome import gremlin
from thunderdome import models
from thunderdome.models import Edge, Vertex
from thunderdome import properties


class OtherTestModel(Vertex):
    count = properties.Integer()
    text  = properties.Text()

class AliasedTestModel(Vertex):
    count = properties.Integer(db_field='how_many')
    text  = properties.Text()

class OtherTestEdge(Edge):
    numbers = properties.Integer()

class YetAnotherTestEdge(Edge):
    numbers = properties.Integer()


class TestVertexIO(BaseThunderdomeTestCase):

    def test_unicode_io(self):
        """
        Tests that unicode is saved and retrieved properly
        """
        tm1 = TestModel.create(count=9, text=u'4567ë9989')
        tm2 = TestModel.get(tm1.vid)

    def test_model_save_and_load(self):
        """
        Tests that models can be saved and retrieved
        """
        tm0 = TestModel.create(count=8, text='123456789')
        tm1 = TestModel.create(count=9, text='456789')
        tms = TestModel.all([tm0.vid, tm1.vid])

        assert len(tms) == 2
       
        for cname in tm0._columns.keys():
            self.assertEquals(getattr(tm0, cname), getattr(tms[0], cname))
            
        tms = TestModel.all([tm1.vid, tm0.vid])
        assert tms[0].vid == tm1.vid 
        assert tms[1].vid == tm0.vid 
            
    def test_model_updating_works_properly(self):
        """
        Tests that subsequent saves after initial model creation work
        """
        tm = TestModel.create(count=8, text='123456789')

        tm.count = 100
        tm.save()

        tm.count = 80
        tm.save()

        tm.count = 60
        tm.save()

        tm.count = 40
        tm.save()

        tm.count = 20
        tm.save()

        tm2 = TestModel.get(tm.vid)
        self.assertEquals(tm.count, tm2.count)

    def test_model_deleting_works_properly(self):
        """
        Tests that an instance's delete method deletes the instance
        """
        tm = TestModel.create(count=8, text='123456789')
        vid = tm.vid
        tm.delete()
        with self.assertRaises(TestModel.DoesNotExist):
            tm2 = TestModel.get(vid)

    def test_reload(self):
        """ Tests that and instance's reload method does an inplace update of the instance """
        tm0 = TestModel.create(count=8, text='123456789')
        tm1 = TestModel.get(tm0.vid)
        tm1.count = 7
        tm1.save()

        tm0.reload()
        assert tm0.count == 7

    def test_reload_on_aliased_field(self):
        """ Tests that reload works with aliased fields """
        tm0 = AliasedTestModel.create(count=8, text='123456789')
        tm1 = AliasedTestModel.get(tm0.vid)
        tm1.count = 7
        tm1.save()

        tm0.reload()
        assert tm0.count == 7

class DeserializationTestModel(Vertex):
    count = properties.Integer()
    text  = properties.Text()

    gremlin_path = 'deserialize.groovy'

    get_map = gremlin.GremlinValue()
    get_list = gremlin.GremlinMethod()

class TestNestedDeserialization(BaseThunderdomeTestCase):
    """
    Tests that vertices are properly deserialized when nested in map and list data structures
    """

    def test_map_deserialization(self):
        """
        Tests that elements nested in maps are properly deserialized
        """
        
        original = DeserializationTestModel.create(count=5, text='happy')
        nested = original.get_map()

        assert isinstance(nested, dict)
        assert nested['vertex'] == original
        assert nested['number'] == 5

    def test_list_deserialization(self):
        """
        Tests that elements nested in lists are properly deserialized
        """
        
        original = DeserializationTestModel.create(count=5, text='happy')
        nested = original.get_list()

        assert isinstance(nested, list)
        assert nested[0] == None
        assert nested[1] == 0
        assert nested[2] == 1

        assert isinstance(nested[3], list)
        assert nested[3][0] == 2
        assert nested[3][1] == original
        assert nested[3][2] == 3

        assert nested[4] == 5

class TestUpdateMethod(BaseThunderdomeTestCase):
    def test_success_case(self):
        """ Tests that the update method works as expected """
        tm = TestModel.create(count=8, text='123456789')
        tm2 = tm.update(count=9)

        tm3 = TestModel.get(tm.vid)
        assert tm2.count == 9
        assert tm3.count == 9

    def test_unknown_names_raise_exception(self):
        """ Tests that passing in names for columns that don't exist raises an exception """
        tm = TestModel.create(count=8, text='123456789')
        with self.assertRaises(TypeError):
            tm.update(jon='beard')


class TestVertexTraversal(BaseThunderdomeTestCase):

    def setUp(self):
        super(TestVertexTraversal, self).setUp()
        self.v1 = TestModel.create(count=1, text='Test1')
        self.v2 = TestModel.create(count=2, text='Test2')
        self.v3 = OtherTestModel.create(count=3, text='Test3')
        self.v4 = OtherTestModel.create(count=3, text='Test3')

    def test_outgoing_vertex_traversal(self):
        """Test that outgoing vertex traversals work."""
        e1 = TestEdge.create(self.v1, self.v2, numbers=12)
        e2 = TestEdge.create(self.v1, self.v3, numbers=13)
        e3 = TestEdge.create(self.v2, self.v3, numbers=14)

        results = self.v1.outV(TestEdge)
        assert len(results) == 2
        assert self.v2 in results
        assert self.v3 in results

        results = self.v1.outV(TestEdge, types=[OtherTestModel])
        assert len(results) == 1
        assert self.v3 in results

    
    def test_incoming_vertex_traversal(self):
        """Test that incoming vertex traversals work."""
        e1 = TestEdge.create(self.v1, self.v2, numbers=12)
        e2 = TestEdge.create(self.v1, self.v3, numbers=13)
        e3 = TestEdge.create(self.v2, self.v3, numbers=14)

        results = self.v2.inV(TestEdge)
        assert len(results) == 1
        assert self.v1 in results

        results = self.v2.inV(TestEdge, types=[OtherTestModel])
        assert len(results) == 0

    def test_outgoing_edge_traversals(self):
        """Test that outgoing edge traversals work."""
        e1 = TestEdge.create(self.v1, self.v2, numbers=12)
        e2 = TestEdge.create(self.v1, self.v3, numbers=13)
        e3 = OtherTestEdge.create(self.v2, self.v3, numbers=14)

        results = self.v2.outE()
        assert len(results) == 1
        assert e3 in results

        results = self.v2.outE(types=[TestEdge])
        assert len(results) == 0

    def test_incoming_edge_traversals(self):
        """Test that incoming edge traversals work."""
        e1 = TestEdge.create(self.v1, self.v2, numbers=12)
        e2 = TestEdge.create(self.v1, self.v3, numbers=13)
        e3 = OtherTestEdge.create(self.v2, self.v3, numbers=14)

        results = self.v2.inE()
        assert len(results) == 1
        assert e1 in results

        results = self.v2.inE(types=[OtherTestEdge])
        assert len(results) == 0

    def test_multiple_label_traversals(self):
        """ Tests that using multiple edges for traversals works """
        TestEdge.create(self.v1, self.v2)
        OtherTestEdge.create(self.v1, self.v3)
        YetAnotherTestEdge.create(self.v1, self.v4)

        assert len(self.v1.outV()) == 3

        assert len(self.v1.outV(TestEdge)) == 1
        assert len(self.v1.outV(OtherTestEdge)) == 1
        assert len(self.v1.outV(YetAnotherTestEdge)) == 1

        out = self.v1.outV(TestEdge, OtherTestEdge)
        assert len(out) == 2
        assert self.v2.vid in [v.vid for v in out]
        assert self.v3.vid in [v.vid for v in out]

        out = self.v1.outV(OtherTestEdge, YetAnotherTestEdge)
        assert len(out) == 2
        assert self.v3.vid in [v.vid for v in out]
        assert self.v4.vid in [v.vid for v in out]

    def test_multiple_edge_traversal_with_type_filtering(self):
        """ Tests that using multiple edges for traversals works """
        v = TestModel.create(count=1, text='Test1')

        v1 = TestModel.create()
        TestEdge.create(v, v1)

        v2 = TestModel.create()
        OtherTestEdge.create(v, v2)

        v3 = TestModel.create()
        YetAnotherTestEdge.create(v, v3)

        v4 = OtherTestModel.create()
        TestEdge.create(v, v4)

        v5 = OtherTestModel.create()
        OtherTestEdge.create(v, v5)

        v6 = OtherTestModel.create()
        YetAnotherTestEdge.create(v, v6)

        assert len(v.outV()) == 6

        assert len(v.outV(TestEdge, OtherTestEdge)) == 4
        assert len(v.outV(TestEdge, OtherTestEdge, types=[TestModel])) == 2

    def test_edge_instance_traversal_types(self):
        """ Test traversals with edge instances work properly """
        te = TestEdge.create(self.v1, self.v2)
        ote = OtherTestEdge.create(self.v1, self.v3)
        yate = YetAnotherTestEdge.create(self.v1, self.v4)

        out = self.v1.outV(te, ote)
        assert len(out) == 2
        assert self.v2.vid in [v.vid for v in out]
        assert self.v3.vid in [v.vid for v in out]

        out = self.v1.outV(ote, yate)
        assert len(out) == 2
        assert self.v3.vid in [v.vid for v in out]
        assert self.v4.vid in [v.vid for v in out]

    def test_edge_label_string_traversal_types(self):
        """ Test traversals with edge instances work properly """
        TestEdge.create(self.v1, self.v2)
        OtherTestEdge.create(self.v1, self.v3)
        YetAnotherTestEdge.create(self.v1, self.v4)

        out = self.v1.outV(TestEdge.get_label(), OtherTestEdge.get_label())
        assert len(out) == 2
        assert self.v2.vid in [v.vid for v in out]
        assert self.v3.vid in [v.vid for v in out]

        out = self.v1.outV(OtherTestEdge.get_label(), YetAnotherTestEdge.get_label())
        assert len(out) == 2
        assert self.v3.vid in [v.vid for v in out]
        assert self.v4.vid in [v.vid for v in out]

    def test_unknown_edge_traversal_filter_type_fails(self):
        """
        Tests an exception is raised if a traversal filter is
        used that's not an edge class, instance or label string fails
        """
        TestEdge.create(self.v1, self.v2)
        OtherTestEdge.create(self.v1, self.v3)
        YetAnotherTestEdge.create(self.v1, self.v4)

        with self.assertRaises(ThunderdomeException):
            out = self.v1.outV(5)

        with self.assertRaises(ThunderdomeException):
            out = self.v1.outV(True)


class TestIndexCreation(BaseThunderdomeTestCase):
    """
    Tests that automatic index creation works as expected
    """
    def setUp(self):
        super(TestIndexCreation, self).setUp()
        self.old_create_index = connection.create_key_index
        self.index_calls = []
        def new_create_index(name):
            #fire blanks
            self.index_calls.append(name)
            #return self.old_create_index(name)
        connection.create_key_index = new_create_index

        self.old_vertex_types = models.vertex_types
        models.vertex_types = {}

        self.old_index_setting = connection._index_all_fields

    def tearDown(self):
        super(TestIndexCreation, self).tearDown()
        models.vertex_types = self.old_vertex_types
        connection._index_all_fields = self.old_index_setting
        connection.create_key_index = self.old_create_index 

    def test_create_index_is_called(self):
        """
        Tests that create_key_index is called when defining indexed columns
        """
        assert len(self.index_calls) == 0

        connection._index_all_fields = False
        
        class TestIndexCreationCallTestVertex(Vertex):
            col1 = properties.Text(index=True)
            col2 = properties.Text(index=True, db_field='____column')
            col3 = properties.Text(db_field='____column3')

        assert len(self.index_calls) == 2
        assert 'vid' not in self.index_calls
        assert 'col1' in self.index_calls
        assert '____column' in self.index_calls
        assert '____column3' not in self.index_calls

        connection._index_all_fields = True
        self.index_calls = []

        class TestIndexCreationCallTestVertex2(Vertex):
            col1 = properties.Text()
            col2 = properties.Text(db_field='____column')

        assert len(self.index_calls) == 3
        assert 'vid' in self.index_calls
        assert 'col1' in self.index_calls
        assert '____column' in self.index_calls

########NEW FILE########
__FILENAME__ = test_vertex_queries
from thunderdome.connection import ThunderdomeQueryError
from thunderdome.tests.base import BaseThunderdomeTestCase
from thunderdome.models import Query, IN, OUT, Edge, Vertex, GREATER_THAN
from thunderdome import Integer, Double


class MockVertex(object):
    eid = 1

class MockVertex2(Vertex):
    age = Integer()

class MockEdge(Edge):
    age = Integer()
    fierceness = Double()


class SimpleQueryTest(BaseThunderdomeTestCase):
    def setUp(self):
        self.q = Query(MockVertex())

    def test_limit(self):
        result = self.q.limit(10)._get_partial()
        assert result == "g.v(eid).query().limit(limit)"

    def test_direction_in(self):
        result = self.q.direction(IN)._get_partial()
        assert result == "g.v(eid).query().direction(IN)"

    def test_direction_out(self):
        result = self.q.direction(OUT)._get_partial()
        assert result == "g.v(eid).query().direction(OUT)"

    def test_labels(self):
        result = self.q.labels('test')._get_partial()
        assert result == "g.v(eid).query().labels('test')"
        # ensure the original wasn't modified
        assert self.q._labels == []

    def test_2labels(self):
        result = self.q.labels('test', 'test2')._get_partial()
        assert result == "g.v(eid).query().labels('test', 'test2')"

    def test_object_label(self):
        result = self.q.labels(MockEdge)._get_partial()
        assert result == "g.v(eid).query().labels('mock_edge')", result

    # def test_has(self):
    #     result = self.q.has(MockEdge.age, 10)._get_parial()
    #     assert result == "g.v(eid).has('prop','val')"
    #
    # def test_has_double_casting(self):
    #     result = self.q.has(MockEdge.fierceness, 3.3)._get_parial()
    #     assert result == "g.v(eid).has('fierceness',3.3 as double)"

    def test_direction_except(self):
        with self.assertRaises(ThunderdomeQueryError):
            self.q.direction(OUT).direction(OUT)

    def test_has_double_casting(self):
        result = self.q.has('fierceness', 3.3)._get_partial()
        assert result == "g.v(eid).query().has('fierceness', v0 as double, Query.Compare.EQUAL)", result

    def test_has_int(self):
        result = self.q.has('age', 21, GREATER_THAN)._get_partial()
        assert result == "g.v(eid).query().has('age', v0, Query.Compare.GREATER_THAN)", result

    def test_intervals(self):
        result = self.q.interval('age', 10, 20)._get_partial()
        assert result == "g.v(eid).query().interval('age', v0, v1)", result

    def test_double_interval(self):
        result = self.q.interval('fierceness', 2.5, 5.2)._get_partial()
        assert result == "g.v(eid).query().interval('fierceness', v0 as double, v1 as double)", result


########NEW FILE########
__FILENAME__ = test_vertex_traversals
# Copyright (c) 2012-2013 SHIFT.com
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of
# this software and associated documentation files (the "Software"), to deal in
# the Software without restriction, including without limitation the rights to
# use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of
# the Software, and to permit persons to whom the Software is furnished to do so,
# subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS
# FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
# COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER
# IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
# CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

from datetime import datetime

from thunderdome import connection 
from thunderdome.tests.base import BaseThunderdomeTestCase

from thunderdome.models import Vertex, Edge, IN, OUT, BOTH, GREATER_THAN, LESS_THAN
from thunderdome import properties


# Vertices
class Person(Vertex):
    name = properties.Text()
    age  = properties.Integer()


class Course(Vertex):
    name = properties.Text()
    credits = properties.Decimal()

# Edges
class EnrolledIn(Edge):
    date_enrolled = properties.DateTime()
    enthusiasm = properties.Integer(default=5) # medium, 1-10, 5 by default

class TaughtBy(Edge):
    overall_mood = properties.Text(default='Grumpy')

class BaseTraversalTestCase(BaseThunderdomeTestCase):

    @classmethod
    def setUpClass(cls):
        """
        person -enrolled_in-> course
        course -taught_by-> person

        :param cls:
        :return:
        """
        cls.jon = Person.create(name='Jon', age=143)
        cls.eric = Person.create(name='Eric', age=25)
        cls.blake = Person.create(name='Blake', age=14)

        cls.physics = Course.create(name='Physics 264', credits=1.0)
        cls.beekeeping = Course.create(name='Beekeeping', credits=15.0)
        cls.theoretics = Course.create(name='Theoretical Theoretics', credits=-3.5)

        cls.eric_in_physics = EnrolledIn.create(cls.eric, cls.physics, date_enrolled=datetime.now(),
                                                enthusiasm=10) # eric loves physics
        cls.jon_in_beekeeping = EnrolledIn.create(cls.jon, cls.beekeeping, date_enrolled=datetime.now(),
                                                  enthusiasm=1) # jon hates beekeeping

        cls.blake_in_theoretics = EnrolledIn.create(cls.blake, cls.theoretics, date_enrolled=datetime.now(),
                                                    enthusiasm=8)

        cls.blake_beekeeping = TaughtBy.create(cls.beekeeping, cls.blake, overall_mood='Pedantic')
        cls.jon_physics = TaughtBy.create(cls.physics, cls.jon, overall_mood='Creepy')
        cls.eric_theoretics = TaughtBy.create(cls.theoretics, cls.eric, overall_mood='Obtuse')

class TestVertexTraversals(BaseTraversalTestCase):

    def test_inV_works(self):
        """Test that inV traversals work as expected"""
        results = self.jon.inV()
        assert len(results) == 1
        assert self.physics in results

        results = self.physics.inV()
        assert len(results) == 1
        assert self.eric in results

        results = self.eric.inV()
        assert len(results) == 1
        assert self.theoretics in results

        results = self.theoretics.inV()
        assert len(results) == 1
        assert self.blake in results

        results = self.beekeeping.inV()
        assert len(results) == 1
        assert self.jon in results

        results = self.blake.inV()
        assert len(results) == 1
        assert self.beekeeping in results

    def test_inE_traversals(self):
        """Test that inE traversals work as expected"""
        results = self.jon.inE()
        assert len(results) == 1
        assert self.jon_physics in results

    def test_outV_traversals(self):
        """Test that outV traversals work as expected"""
        results = self.eric.outV()
        assert len(results) == 1
        assert self.physics in results

    def test_outE_traverals(self):
        """Test that outE traversals work as expected"""
        results = self.blake.outE()
        assert len(results) == 1
        assert self.blake_in_theoretics in results

    def test_bothE_traversals(self):
        """Test that bothE traversals works"""
        results = self.jon.bothE()
        assert len(results) == 2
        assert self.jon_physics in results
        assert self.jon_in_beekeeping in results

    def test_bothV_traversals(self):
        """Test that bothV traversals work"""
        results = self.blake.bothV()
        assert len(results) == 2
        assert self.beekeeping in results

class TestVertexCentricQueries(BaseTraversalTestCase):

    def test_query_vertices(self):
        classes = self.jon.query().labels(EnrolledIn).direction(OUT).vertices()

    def test_query_in(self):
        people = self.physics.query().labels(EnrolledIn).direction(IN).vertices()
        for x in people:
            assert isinstance(x, Person)

    def test_query_out_edges(self):
        classes = self.jon.query().labels(EnrolledIn).direction(OUT).edges()
        for x in classes:
            assert isinstance(x, EnrolledIn), type(x)

    def test_two_labels(self):
        edges = self.jon.query().labels(EnrolledIn, TaughtBy).direction(BOTH).edges()
        for e in edges:
            assert isinstance(e, (EnrolledIn, TaughtBy))

    def test_has(self):
        assert 0 == len(self.jon.query().labels(EnrolledIn).has('enthusiasm', 5, GREATER_THAN).vertices())
        num = self.jon.query().labels(EnrolledIn).has('enthusiasm', 5, GREATER_THAN).count()
        assert 0 == num, num

        assert 1 == len(self.jon.query().labels(EnrolledIn).has('enthusiasm', 5, LESS_THAN).vertices())
        num = self.jon.query().labels(EnrolledIn).has('enthusiasm', 5, LESS_THAN).count()
        assert 1 == num, num

    def test_interval(self):
        assert 1 == len(self.blake.query().labels(EnrolledIn).interval('enthusiasm', 2, 9).vertices())
        assert 1 == len(self.blake.query().labels(EnrolledIn).interval('enthusiasm', 9, 2).vertices())
        assert 0 == len(self.blake.query().labels(EnrolledIn).interval('enthusiasm', 2, 8).vertices())


########NEW FILE########
__FILENAME__ = models
# Copyright (c) 2012-2013 SHIFT.com
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of
# this software and associated documentation files (the "Software"), to deal in
# the Software without restriction, including without limitation the rights to
# use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of
# the Software, and to permit persons to whom the Software is furnished to do so,
# subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS
# FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
# COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER
# IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
# CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

from thunderdome.models import Vertex, Edge
from thunderdome import properties


class TestModel(Vertex):
    count   = properties.Integer()
    text    = properties.Text(required=False)

    
class TestEdge(Edge):
    numbers = properties.Integer()

########NEW FILE########
__FILENAME__ = test_spec
from thunderdome.tests.base import BaseThunderdomeTestCase
from thunderdome.spec import SpecParser, Property, Edge


class SpecParserTest(BaseThunderdomeTestCase):
    """Test spec parsing from dictionary objects"""

    def setUp(self):
        self.spec_parser = SpecParser()
        self.property_spec = {
            'type': 'property',
            'name': 'updated_at',
            'data_type': 'Integer',
            'functional': True,
            'locking': True
        }
        self.edge_spec = {
            'type': 'edge',
            'label': 'subscribed_to',
            'primary_key': 'updated_at'
        }
        self.key_index_spec = {
            'type': 'key_index',
            'name': 'email',
            'data_type': 'Vertex'
        }
        
    def test_should_return_error_if_stmt_contains_no_type(self):
        """Should raise error if statement contains no type"""
        with self.assertRaises(TypeError):
            self.spec_parser.parse_statement({'name': 'todd'})

    def test_should_raise_error_if_type_is_invalid(self):
        """Should raise error if type is invalid"""
        with self.assertRaises(ValueError):
            self.spec_parser.parse_statement({'type': 'sugar'})

    def test_should_raise_error_for_duplicate_names(self):
        """Should raise error if duplicate names given"""
        self.edge_spec['label'] = 'updated_at'
        with self.assertRaises(ValueError):
            self.spec_parser.parse_statement(self.property_spec)
            self.spec_parser.parse_statement(self.edge_spec)

    def test_should_return_correct_gremlin_for_property(self):
        """Should construct the correct Gremlin code for a property"""
        expected = 'updated_at = g.makeType().name("updated_at").dataType(Integer.class).functional(true).makePropertyKey()'
        prop = self.spec_parser.parse_property(self.property_spec)
        assert prop.gremlin == expected

        expected = 'updated_at = g.makeType().name("updated_at").dataType(Integer.class).functional(false).makePropertyKey()'
        self.property_spec['locking'] = False
        self.spec_parser._properties = {} # Reset saved properties
        self.spec_parser._names = []
        prop = self.spec_parser.parse_property(self.property_spec)
        assert prop.gremlin == expected

        expected = 'updated_at = g.makeType().name("updated_at").dataType(Integer.class).functional(false).indexed().makePropertyKey()'
        self.property_spec['locking'] = False
        self.property_spec['indexed'] = True
        self.spec_parser._properties = {} # Reset saved properties
        self.spec_parser._names = []
        prop = self.spec_parser.parse_property(self.property_spec)
        assert prop.gremlin == expected

        expected = 'updated_at = g.makeType().name("updated_at").dataType(Integer.class).makePropertyKey()'
        self.property_spec['functional'] = False
        self.property_spec['indexed'] = False
        self.spec_parser._properties = {} # Reset saved properties
        self.spec_parser._names = []
        prop = self.spec_parser.parse_property(self.property_spec)
        assert prop.gremlin == expected

        expected = 'updated_at = g.makeType().name("updated_at").dataType(Integer.class).unique().makePropertyKey()'
        self.property_spec['functional'] = False
        self.property_spec['indexed'] = False
        self.property_spec['unique'] = True
        self.spec_parser._properties = {} # Reset saved properties
        self.spec_parser._names = []
        prop = self.spec_parser.parse_property(self.property_spec)
        assert prop.gremlin == expected, prop.gremlin

    def test_should_return_correct_gremlin_for_edge(self):
        """Should return correct gremlin for an edge"""
        expected = 'subscribed_to = g.makeType().name("subscribed_to").primaryKey(updated_at).makeEdgeLabel()'
        edge = self.spec_parser.parse_edge(self.edge_spec)
        assert edge.gremlin == expected

        expected = 'subscribed_to = g.makeType().name("subscribed_to").makeEdgeLabel()'
        self.spec_parser._names = []
        del self.edge_spec['primary_key']
        edge = self.spec_parser.parse_edge(self.edge_spec)
        assert edge.gremlin == expected

    def test_functional_edge(self):
        expected = 'subscribed_to = g.makeType().name("subscribed_to").functional().makeEdgeLabel()'
        del self.edge_spec['primary_key']
        self.edge_spec['functional'] = True
        edge = self.spec_parser.parse_edge(self.edge_spec)
        assert edge.gremlin == expected

    def test_should_return_correct_gremlin_for_key_index_creation(self):
        """Should return correct gremlin for key index"""
        expected = 'g.createKeyIndex("email", Vertex.class)'
        key_index = self.spec_parser.parse_key_index(self.key_index_spec)
        assert key_index.gremlin == expected

    def test_should_return_appropriate_type(self):
        """Should return appropriate type when parsing a statement"""
        assert isinstance(self.spec_parser.parse_statement(self.edge_spec), Edge)
        assert isinstance(self.spec_parser.parse_statement(self.property_spec), Property)

    def test_should_raise_error_if_inconsistent_properties(self):
        """Should raise an error if a primary key is not defined"""
        edge_spec = {
            'type': 'edge',
            'label': 'subscribed_to',
            'primary_key': 'undefined'
        }

        results = [self.spec_parser.parse_statement(edge_spec)]
        results += [self.spec_parser.parse_statement(self.property_spec)]
        with self.assertRaises(ValueError):
            self.spec_parser.validate(results)

    def test_should_return_none_for_defaults(self):
        """Should return none for defaults"""
        default_spec = {
            'type': 'defaults',
            'spec_type': 'property',
            'functional': True
        }

        assert 'property' not in self.spec_parser._defaults
        assert self.spec_parser.parse_statement(default_spec) is None
        assert 'property' in self.spec_parser._defaults
        assert 'functional' in self.spec_parser._defaults['property']._values

########NEW FILE########
