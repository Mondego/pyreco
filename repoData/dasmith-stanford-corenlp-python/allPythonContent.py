__FILENAME__ = client
import json
from jsonrpc import ServerProxy, JsonRpc20, TransportTcpIp
from pprint import pprint

class StanfordNLP:
    def __init__(self):
        self.server = ServerProxy(JsonRpc20(),
                                  TransportTcpIp(addr=("127.0.0.1", 8080)))
    
    def parse(self, text):
        return json.loads(self.server.parse(text))

nlp = StanfordNLP()
result = nlp.parse("Hello world!  It is so beautiful.")
pprint(result)

from nltk.tree import Tree
tree = Tree.parse(result['sentences'][0]['parsetree'])
pprint(tree)

########NEW FILE########
__FILENAME__ = corenlp
#!/usr/bin/env python
#
# corenlp  - Python interface to Stanford Core NLP tools
# Copyright (c) 2012 Dustin Smith
#   https://github.com/dasmith/stanford-corenlp-python
# 
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.

import json, optparse, os, re, sys, time, traceback
import jsonrpc, pexpect
from progressbar import ProgressBar, Fraction
from unidecode import unidecode


VERBOSE = True
STATE_START, STATE_TEXT, STATE_WORDS, STATE_TREE, STATE_DEPENDENCY, STATE_COREFERENCE = 0, 1, 2, 3, 4, 5
WORD_PATTERN = re.compile('\[([^\]]+)\]')
CR_PATTERN = re.compile(r"\((\d*),(\d)*,\[(\d*),(\d*)\)\) -> \((\d*),(\d)*,\[(\d*),(\d*)\)\), that is: \"(.*)\" -> \"(.*)\"")


def remove_id(word):
    """Removes the numeric suffix from the parsed recognized words: e.g. 'word-2' > 'word' """
    return word.count("-") == 0 and word or word[0:word.rindex("-")]


def parse_bracketed(s):
    '''Parse word features [abc=... def = ...]
    Also manages to parse out features that have XML within them
    '''
    word = None
    attrs = {}
    temp = {}
    # Substitute XML tags, to replace them later
    for i, tag in enumerate(re.findall(r"(<[^<>]+>.*<\/[^<>]+>)", s)):
        temp["^^^%d^^^" % i] = tag
        s = s.replace(tag, "^^^%d^^^" % i)
    # Load key-value pairs, substituting as necessary
    for attr, val in re.findall(r"([^=\s]*)=([^=\s]*)", s):
        if val in temp:
            val = temp[val]
        if attr == 'Text':
            word = val
        else:
            attrs[attr] = val
    return (word, attrs)


def parse_parser_results(text):
    """ This is the nasty bit of code to interact with the command-line
    interface of the CoreNLP tools.  Takes a string of the parser results
    and then returns a Python list of dictionaries, one for each parsed
    sentence.
    """
    results = {"sentences": []}
    state = STATE_START
    for line in unidecode(text).split("\n"):
        line = line.strip()
        
        if line.startswith("Sentence #"):
            sentence = {'words':[], 'parsetree':[], 'dependencies':[]}
            results["sentences"].append(sentence)
            state = STATE_TEXT
        
        elif state == STATE_TEXT:
            sentence['text'] = line
            state = STATE_WORDS
        
        elif state == STATE_WORDS:
            if not line.startswith("[Text="):
                raise Exception('Parse error. Could not find "[Text=" in: %s' % line)
            for s in WORD_PATTERN.findall(line):
                sentence['words'].append(parse_bracketed(s))
            state = STATE_TREE
        
        elif state == STATE_TREE:
            if len(line) == 0:
                state = STATE_DEPENDENCY
                sentence['parsetree'] = " ".join(sentence['parsetree'])
            else:
                sentence['parsetree'].append(line)
        
        elif state == STATE_DEPENDENCY:
            if len(line) == 0:
                state = STATE_COREFERENCE
            else:
                split_entry = re.split("\(|, ", line[:-1])
                if len(split_entry) == 3:
                    rel, left, right = map(lambda x: remove_id(x), split_entry)
                    sentence['dependencies'].append(tuple([rel,left,right]))
        
        elif state == STATE_COREFERENCE:
            if "Coreference set" in line:
                if 'coref' not in results:
                    results['coref'] = []
                coref_set = []
                results['coref'].append(coref_set)
            else:
                for src_i, src_pos, src_l, src_r, sink_i, sink_pos, sink_l, sink_r, src_word, sink_word in CR_PATTERN.findall(line):
                    src_i, src_pos, src_l, src_r = int(src_i)-1, int(src_pos)-1, int(src_l)-1, int(src_r)-1
                    sink_i, sink_pos, sink_l, sink_r = int(sink_i)-1, int(sink_pos)-1, int(sink_l)-1, int(sink_r)-1
                    coref_set.append(((src_word, src_i, src_pos, src_l, src_r), (sink_word, sink_i, sink_pos, sink_l, sink_r)))
    
    return results


class StanfordCoreNLP(object):
    """
    Command-line interaction with Stanford's CoreNLP java utilities.
    Can be run as a JSON-RPC server or imported as a module.
    """
    def __init__(self):
        """
        Checks the location of the jar files.
        Spawns the server as a process.
        """
        jars = ["stanford-corenlp-2012-07-09.jar",
                "stanford-corenlp-2012-07-06-models.jar",
                "joda-time.jar",
                "xom.jar"]
       
        # if CoreNLP libraries are in a different directory,
        # change the corenlp_path variable to point to them
        corenlp_path = "stanford-corenlp-2012-07-09/"
        
        java_path = "java"
        classname = "edu.stanford.nlp.pipeline.StanfordCoreNLP"
        # include the properties file, so you can change defaults
        # but any changes in output format will break parse_parser_results()
        props = "-props default.properties" 
        
        # add and check classpaths
        jars = [corenlp_path + jar for jar in jars]
        for jar in jars:
            if not os.path.exists(jar):
                print "Error! Cannot locate %s" % jar
                sys.exit(1)
        
        # spawn the server
        start_corenlp = "%s -Xmx1800m -cp %s %s %s" % (java_path, ':'.join(jars), classname, props)
        if VERBOSE: print start_corenlp
        self.corenlp = pexpect.spawn(start_corenlp)
        
        # show progress bar while loading the models
        widgets = ['Loading Models: ', Fraction()]
        pbar = ProgressBar(widgets=widgets, maxval=5, force_update=True).start()
        self.corenlp.expect("done.", timeout=20) # Load pos tagger model (~5sec)
        pbar.update(1)
        self.corenlp.expect("done.", timeout=200) # Load NER-all classifier (~33sec)
        pbar.update(2)
        self.corenlp.expect("done.", timeout=600) # Load NER-muc classifier (~60sec)
        pbar.update(3)
        self.corenlp.expect("done.", timeout=600) # Load CoNLL classifier (~50sec)
        pbar.update(4)
        self.corenlp.expect("done.", timeout=200) # Loading PCFG (~3sec)
        pbar.update(5)
        self.corenlp.expect("Entering interactive shell.")
        pbar.finish()
    
    def _parse(self, text):
        """
        This is the core interaction with the parser.
        
        It returns a Python data-structure, while the parse()
        function returns a JSON object
        """
        # clean up anything leftover
        while True:
            try:
                self.corenlp.read_nonblocking (4000, 0.3)
            except pexpect.TIMEOUT:
                break
        
        self.corenlp.sendline(text)
        
        # How much time should we give the parser to parse it?
        # the idea here is that you increase the timeout as a 
        # function of the text's length.
        # anything longer than 5 seconds requires that you also
        # increase timeout=5 in jsonrpc.py
        max_expected_time = min(5, 3 + len(text) / 20.0)
        end_time = time.time() + max_expected_time
        
        incoming = ""
        while True:
            # Time left, read more data
            try:
                incoming += self.corenlp.read_nonblocking(2000, 1)
                if "\nNLP>" in incoming: break
                time.sleep(0.0001)
            except pexpect.TIMEOUT:
                if end_time - time.time() < 0:
                    print "[ERROR] Timeout"
                    return {'error': "timed out after %f seconds" % max_expected_time,
                            'input': text,
                            'output': incoming}
                else:
                    continue
            except pexpect.EOF:
                break
        
        if VERBOSE: print "%s\n%s" % ('='*40, incoming)
        try:
            results = parse_parser_results(incoming)
        except Exception, e:
            if VERBOSE: print traceback.format_exc()
            raise e
        
        return results
    
    def parse(self, text):
        """ 
        This function takes a text string, sends it to the Stanford parser,
        reads in the result, parses the results and returns a list
        with one dictionary entry for each parsed sentence, in JSON format.
        """
        return json.dumps(self._parse(text))


if __name__ == '__main__':
    """
    The code below starts an JSONRPC server
    """
    parser = optparse.OptionParser(usage="%prog [OPTIONS]")
    parser.add_option('-p', '--port', default='8080',
                      help='Port to serve on (default 8080)')
    parser.add_option('-H', '--host', default='127.0.0.1',
                      help='Host to serve on (default localhost; 0.0.0.0 to make public)')
    options, args = parser.parse_args()
    server = jsonrpc.Server(jsonrpc.JsonRpc20(),
                            jsonrpc.TransportTcpIp(addr=(options.host, int(options.port))))
    
    nlp = StanfordCoreNLP()
    server.register_function(nlp.parse)
    
    print 'Serving on http://%s:%s' % (options.host, options.port)
    server.serve()

########NEW FILE########
__FILENAME__ = jsonrpc
#!/usr/bin/env python
# -*- coding: ascii -*-
"""
JSON-RPC (remote procedure call).

It consists of 3 (independent) parts:
    - proxy/dispatcher
    - data structure / serializer
    - transport

It's intended for JSON-RPC, but since the above 3 parts are independent,
it could be used for other RPCs as well.

Currently, JSON-RPC 2.0(pre) and JSON-RPC 1.0 are implemented

:Version:   2008-08-31-beta
:Status:    experimental

:Example:
    simple Client with JsonRPC2.0 and TCP/IP::

        >>> proxy = ServerProxy( JsonRpc20(), TransportTcpIp(addr=("127.0.0.1",31415)) )
        >>> proxy.echo( "hello world" )
        u'hello world'
        >>> proxy.echo( "bye." )
        u'bye.'

    simple Server with JsonRPC2.0 and TCP/IP with logging to STDOUT::

        >>> server = Server( JsonRpc20(), TransportTcpIp(addr=("127.0.0.1",31415), logfunc=log_stdout) )
        >>> def echo( s ):
        ...   return s
        >>> server.register_function( echo )
        >>> server.serve( 2 )   # serve 2 requests          # doctest: +ELLIPSIS
        listen ('127.0.0.1', 31415)
        ('127.0.0.1', ...) connected
        ('127.0.0.1', ...) <-- {"jsonrpc": "2.0", "method": "echo", "params": ["hello world"], "id": 0}
        ('127.0.0.1', ...) --> {"jsonrpc": "2.0", "result": "hello world", "id": 0}
        ('127.0.0.1', ...) close
        ('127.0.0.1', ...) connected
        ('127.0.0.1', ...) <-- {"jsonrpc": "2.0", "method": "echo", "params": ["bye."], "id": 0}
        ('127.0.0.1', ...) --> {"jsonrpc": "2.0", "result": "bye.", "id": 0}
        ('127.0.0.1', ...) close
        close ('127.0.0.1', 31415)

    Client with JsonRPC2.0 and an abstract Unix Domain Socket::
    
        >>> proxy = ServerProxy( JsonRpc20(), TransportUnixSocket(addr="\\x00.rpcsocket") )
        >>> proxy.hi( message="hello" )         #named parameters
        u'hi there'
        >>> proxy.test()                        #fault
        Traceback (most recent call last):
          ...
        jsonrpc.RPCMethodNotFound: <RPCFault -32601: u'Method not found.' (None)>
        >>> proxy.debug.echo( "hello world" )   #hierarchical procedures
        u'hello world'

    Server with JsonRPC2.0 and abstract Unix Domain Socket with a logfile::
        
        >>> server = Server( JsonRpc20(), TransportUnixSocket(addr="\\x00.rpcsocket", logfunc=log_file("mylog.txt")) )
        >>> def echo( s ):
        ...   return s
        >>> def hi( message ):
        ...   return "hi there"
        >>> server.register_function( hi )
        >>> server.register_function( echo, name="debug.echo" )
        >>> server.serve( 3 )   # serve 3 requests

        "mylog.txt" then contains:
        listen '\\x00.rpcsocket'
        '' connected
        '' --> '{"jsonrpc": "2.0", "method": "hi", "params": {"message": "hello"}, "id": 0}'
        '' <-- '{"jsonrpc": "2.0", "result": "hi there", "id": 0}'
        '' close
        '' connected
        '' --> '{"jsonrpc": "2.0", "method": "test", "id": 0}'
        '' <-- '{"jsonrpc": "2.0", "error": {"code":-32601, "message": "Method not found."}, "id": 0}'
        '' close
        '' connected
        '' --> '{"jsonrpc": "2.0", "method": "debug.echo", "params": ["hello world"], "id": 0}'
        '' <-- '{"jsonrpc": "2.0", "result": "hello world", "id": 0}'
        '' close
        close '\\x00.rpcsocket'

:Note:      all exceptions derived from RPCFault are propagated to the client.
            other exceptions are logged and result in a sent-back "empty" INTERNAL_ERROR.
:Uses:      simplejson, socket, sys,time,codecs
:SeeAlso:   JSON-RPC 2.0 proposal, 1.0 specification
:Warning:
    .. Warning::
        This is **experimental** code!
:Bug:

:Author:    Roland Koebler (rk(at)simple-is-better.org)
:Copyright: 2007-2008 by Roland Koebler (rk(at)simple-is-better.org)
:License:   see __license__
:Changelog:
        - 2008-08-31:     1st release

TODO:
        - server: multithreading rpc-server
        - client: multicall (send several requests)
        - transport: SSL sockets, maybe HTTP, HTTPS
        - types: support for date/time (ISO 8601)
        - errors: maybe customizable error-codes/exceptions
        - mixed 1.0/2.0 server ?
        - system description etc. ?
        - maybe test other json-serializers, like cjson?
"""

__version__ = "2008-08-31-beta"
__author__   = "Roland Koebler <rk(at)simple-is-better.org>"
__license__  = """Copyright (c) 2007-2008 by Roland Koebler (rk(at)simple-is-better.org)

Permission is hereby granted, free of charge, to any person obtaining
a copy of this software and associated documentation files (the
"Software"), to deal in the Software without restriction, including
without limitation the rights to use, copy, modify, merge, publish,
distribute, sublicense, and/or sell copies of the Software, and to
permit persons to whom the Software is furnished to do so, subject to
the following conditions:

The above copyright notice and this permission notice shall be included
in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE."""

#=========================================
#import

import sys

try:
    import json
except ImportError:
    import simplejson as json


#=========================================
# errors

#----------------------
# error-codes + exceptions

#JSON-RPC 2.0 error-codes
PARSE_ERROR           = -32700
INVALID_REQUEST       = -32600
METHOD_NOT_FOUND      = -32601
INVALID_METHOD_PARAMS = -32602  #invalid number/type of parameters
INTERNAL_ERROR        = -32603  #"all other errors"

#additional error-codes
PROCEDURE_EXCEPTION    = -32000
AUTHENTIFICATION_ERROR = -32001
PERMISSION_DENIED      = -32002
INVALID_PARAM_VALUES   = -32003

#human-readable messages
ERROR_MESSAGE = {
    PARSE_ERROR           : "Parse error.",
    INVALID_REQUEST       : "Invalid Request.",
    METHOD_NOT_FOUND      : "Method not found.",
    INVALID_METHOD_PARAMS : "Invalid parameters.",
    INTERNAL_ERROR        : "Internal error.",

    PROCEDURE_EXCEPTION   : "Procedure exception.",
    AUTHENTIFICATION_ERROR : "Authentification error.",
    PERMISSION_DENIED   : "Permission denied.",
    INVALID_PARAM_VALUES: "Invalid parameter values."
    }
 
#----------------------
# exceptions

class RPCError(Exception):
    """Base class for rpc-errors."""


class RPCTransportError(RPCError):
    """Transport error."""
class RPCTimeoutError(RPCTransportError):
    """Transport/reply timeout."""

class RPCFault(RPCError):
    """RPC error/fault package received.
    
    This exception can also be used as a class, to generate a
    RPC-error/fault message.

    :Variables:
        - error_code:   the RPC error-code
        - error_string: description of the error
        - error_data:   optional additional information
                        (must be json-serializable)
    :TODO: improve __str__
    """
    def __init__(self, error_code, error_message, error_data=None):
        RPCError.__init__(self)
        self.error_code   = error_code
        self.error_message = error_message
        self.error_data   = error_data
    def __str__(self):
        return repr(self)
    def __repr__(self):
        return( "<RPCFault %s: %s (%s)>" % (self.error_code, repr(self.error_message), repr(self.error_data)) )

class RPCParseError(RPCFault):
    """Broken rpc-package. (PARSE_ERROR)"""
    def __init__(self, error_data=None):
        RPCFault.__init__(self, PARSE_ERROR, ERROR_MESSAGE[PARSE_ERROR], error_data)

class RPCInvalidRPC(RPCFault):
    """Invalid rpc-package. (INVALID_REQUEST)"""
    def __init__(self, error_data=None):
        RPCFault.__init__(self, INVALID_REQUEST, ERROR_MESSAGE[INVALID_REQUEST], error_data)

class RPCMethodNotFound(RPCFault):
    """Method not found. (METHOD_NOT_FOUND)"""
    def __init__(self, error_data=None):
        RPCFault.__init__(self, METHOD_NOT_FOUND, ERROR_MESSAGE[METHOD_NOT_FOUND], error_data)

class RPCInvalidMethodParams(RPCFault):
    """Invalid method-parameters. (INVALID_METHOD_PARAMS)"""
    def __init__(self, error_data=None):
        RPCFault.__init__(self, INVALID_METHOD_PARAMS, ERROR_MESSAGE[INVALID_METHOD_PARAMS], error_data)

class RPCInternalError(RPCFault):
    """Internal error. (INTERNAL_ERROR)"""
    def __init__(self, error_data=None):
        RPCFault.__init__(self, INTERNAL_ERROR, ERROR_MESSAGE[INTERNAL_ERROR], error_data)


class RPCProcedureException(RPCFault):
    """Procedure exception. (PROCEDURE_EXCEPTION)"""
    def __init__(self, error_data=None):
        RPCFault.__init__(self, PROCEDURE_EXCEPTION, ERROR_MESSAGE[PROCEDURE_EXCEPTION], error_data)
class RPCAuthentificationError(RPCFault):
    """AUTHENTIFICATION_ERROR"""
    def __init__(self, error_data=None):
        RPCFault.__init__(self, AUTHENTIFICATION_ERROR, ERROR_MESSAGE[AUTHENTIFICATION_ERROR], error_data)
class RPCPermissionDenied(RPCFault):
    """PERMISSION_DENIED"""
    def __init__(self, error_data=None):
        RPCFault.__init__(self, PERMISSION_DENIED, ERROR_MESSAGE[PERMISSION_DENIED], error_data)
class RPCInvalidParamValues(RPCFault):
    """INVALID_PARAM_VALUES"""
    def __init__(self, error_data=None):
        RPCFault.__init__(self, INVALID_PARAM_VALUES, ERROR_MESSAGE[INVALID_PARAM_VALUES], error_data)


#=========================================
# data structure / serializer

#----------------------
#
def dictkeyclean(d):
    """Convert all keys of the dict 'd' to (ascii-)strings.

    :Raises: UnicodeEncodeError
    """
    new_d = {}
    for (k, v) in d.iteritems():
        new_d[str(k)] = v
    return new_d

#----------------------
# JSON-RPC 1.0

class JsonRpc10:
    """JSON-RPC V1.0 data-structure / serializer

    This implementation is quite liberal in what it accepts: It treats
    missing "params" and "id" in Requests and missing "result"/"error" in
    Responses as empty/null.

    :SeeAlso:   JSON-RPC 1.0 specification
    :TODO:      catch simplejson.dumps not-serializable-exceptions
    """
    def __init__(self, dumps=json.dumps, loads=json.loads):
        """init: set serializer to use

        :Parameters:
            - dumps: json-encoder-function
            - loads: json-decoder-function
        :Note: The dumps_* functions of this class already directly create
               the invariant parts of the resulting json-object themselves,
               without using the given json-encoder-function.
        """
        self.dumps = dumps
        self.loads = loads

    def dumps_request( self, method, params=(), id=0 ):
        """serialize JSON-RPC-Request

        :Parameters:
            - method: the method-name (str/unicode)
            - params: the parameters (list/tuple)
            - id:     if id=None, this results in a Notification
        :Returns:   | {"method": "...", "params": ..., "id": ...}
                    | "method", "params" and "id" are always in this order.
        :Raises:    TypeError if method/params is of wrong type or 
                    not JSON-serializable
        """
        if not isinstance(method, (str, unicode)):
            raise TypeError('"method" must be a string (or unicode string).')
        if not isinstance(params, (tuple, list)):
            raise TypeError("params must be a tuple/list.")

        return '{"method": %s, "params": %s, "id": %s}' % \
                (self.dumps(method), self.dumps(params), self.dumps(id))

    def dumps_notification( self, method, params=() ):
        """serialize a JSON-RPC-Notification

        :Parameters: see dumps_request
        :Returns:   | {"method": "...", "params": ..., "id": null}
                    | "method", "params" and "id" are always in this order.
        :Raises:    see dumps_request
        """
        if not isinstance(method, (str, unicode)):
            raise TypeError('"method" must be a string (or unicode string).')
        if not isinstance(params, (tuple, list)):
            raise TypeError("params must be a tuple/list.")

        return '{"method": %s, "params": %s, "id": null}' % \
                (self.dumps(method), self.dumps(params))

    def dumps_response( self, result, id=None ):
        """serialize a JSON-RPC-Response (without error)

        :Returns:   | {"result": ..., "error": null, "id": ...}
                    | "result", "error" and "id" are always in this order.
        :Raises:    TypeError if not JSON-serializable
        """
        return '{"result": %s, "error": null, "id": %s}' % \
                (self.dumps(result), self.dumps(id))

    def dumps_error( self, error, id=None ):
        """serialize a JSON-RPC-Response-error

        Since JSON-RPC 1.0 does not define an error-object, this uses the
        JSON-RPC 2.0 error-object.
      
        :Parameters:
            - error: a RPCFault instance
        :Returns:   | {"result": null, "error": {"code": error_code, "message": error_message, "data": error_data}, "id": ...}
                    | "result", "error" and "id" are always in this order, data is omitted if None.
        :Raises:    ValueError if error is not a RPCFault instance,
                    TypeError if not JSON-serializable
        """
        if not isinstance(error, RPCFault):
            raise ValueError("""error must be a RPCFault-instance.""")
        if error.error_data is None:
            return '{"result": null, "error": {"code":%s, "message": %s}, "id": %s}' % \
                    (self.dumps(error.error_code), self.dumps(error.error_message), self.dumps(id))
        else:
            return '{"result": null, "error": {"code":%s, "message": %s, "data": %s}, "id": %s}' % \
                    (self.dumps(error.error_code), self.dumps(error.error_message), self.dumps(error.error_data), self.dumps(id))

    def loads_request( self, string ):
        """de-serialize a JSON-RPC Request/Notification

        :Returns:   | [method_name, params, id] or [method_name, params]
                    | params is a tuple/list
                    | if id is missing, this is a Notification
        :Raises:    RPCParseError, RPCInvalidRPC, RPCInvalidMethodParams
        """
        try:
            data = self.loads(string)
        except ValueError, err:
            raise RPCParseError("No valid JSON. (%s)" % str(err))
        if not isinstance(data, dict):  raise RPCInvalidRPC("No valid RPC-package.")
        if "method" not in data:        raise RPCInvalidRPC("""Invalid Request, "method" is missing.""")
        if not isinstance(data["method"], (str, unicode)):
            raise RPCInvalidRPC("""Invalid Request, "method" must be a string.""")
        if "id"     not in data:        data["id"]     = None   #be liberal
        if "params" not in data:        data["params"] = ()     #be liberal
        if not isinstance(data["params"], (list, tuple)):
            raise RPCInvalidRPC("""Invalid Request, "params" must be an array.""")
        if len(data) != 3:          raise RPCInvalidRPC("""Invalid Request, additional fields found.""")
        # notification / request
        if data["id"] is None:
            return data["method"], data["params"]               #notification
        else:
            return data["method"], data["params"], data["id"]   #request

    def loads_response( self, string ):
        """de-serialize a JSON-RPC Response/error

        :Returns: | [result, id] for Responses
        :Raises:  | RPCFault+derivates for error-packages/faults, RPCParseError, RPCInvalidRPC
                  | Note that for error-packages which do not match the
                    V2.0-definition, RPCFault(-1, "Error", RECEIVED_ERROR_OBJ)
                    is raised.
        """
        try:
            data = self.loads(string)
        except ValueError, err:
            raise RPCParseError("No valid JSON. (%s)" % str(err))
        if not isinstance(data, dict):  raise RPCInvalidRPC("No valid RPC-package.")
        if "id" not in data:            raise RPCInvalidRPC("""Invalid Response, "id" missing.""")
        if "result" not in data:        data["result"] = None    #be liberal
        if "error"  not in data:        data["error"]  = None    #be liberal
        if len(data) != 3:              raise RPCInvalidRPC("""Invalid Response, additional or missing fields.""")

        #error
        if data["error"] is not None:
            if data["result"] is not None:
                raise RPCInvalidRPC("""Invalid Response, one of "result" or "error" must be null.""")
            #v2.0 error-format
            if( isinstance(data["error"], dict)  and  "code" in data["error"]  and  "message" in data["error"]  and
                (len(data["error"])==2 or ("data" in data["error"] and len(data["error"])==3)) ):
                if "data" not in data["error"]:
                    error_data = None
                else:
                    error_data = data["error"]["data"]

                if   data["error"]["code"] == PARSE_ERROR:
                    raise RPCParseError(error_data)
                elif data["error"]["code"] == INVALID_REQUEST:
                    raise RPCInvalidRPC(error_data)
                elif data["error"]["code"] == METHOD_NOT_FOUND:
                    raise RPCMethodNotFound(error_data)
                elif data["error"]["code"] == INVALID_METHOD_PARAMS:
                    raise RPCInvalidMethodParams(error_data)
                elif data["error"]["code"] == INTERNAL_ERROR:
                    raise RPCInternalError(error_data)
                elif data["error"]["code"] == PROCEDURE_EXCEPTION:
                    raise RPCProcedureException(error_data)
                elif data["error"]["code"] == AUTHENTIFICATION_ERROR:
                    raise RPCAuthentificationError(error_data)
                elif data["error"]["code"] == PERMISSION_DENIED:
                    raise RPCPermissionDenied(error_data)
                elif data["error"]["code"] == INVALID_PARAM_VALUES:
                    raise RPCInvalidParamValues(error_data)
                else:
                    raise RPCFault(data["error"]["code"], data["error"]["message"], error_data)
            #other error-format
            else:
                raise RPCFault(-1, "Error", data["error"])
        #result
        else:
            return data["result"], data["id"]

#----------------------
# JSON-RPC 2.0

class JsonRpc20:
    """JSON-RPC V2.0 data-structure / serializer

    :SeeAlso:   JSON-RPC 2.0 specification
    :TODO:      catch simplejson.dumps not-serializable-exceptions
    """
    def __init__(self, dumps=json.dumps, loads=json.loads):
        """init: set serializer to use

        :Parameters:
            - dumps: json-encoder-function
            - loads: json-decoder-function
        :Note: The dumps_* functions of this class already directly create
               the invariant parts of the resulting json-object themselves,
               without using the given json-encoder-function.
        """
        self.dumps = dumps
        self.loads = loads

    def dumps_request( self, method, params=(), id=0 ):
        """serialize JSON-RPC-Request

        :Parameters:
            - method: the method-name (str/unicode)
            - params: the parameters (list/tuple/dict)
            - id:     the id (should not be None)
        :Returns:   | {"jsonrpc": "2.0", "method": "...", "params": ..., "id": ...}
                    | "jsonrpc", "method", "params" and "id" are always in this order.
                    | "params" is omitted if empty
        :Raises:    TypeError if method/params is of wrong type or 
                    not JSON-serializable
        """
        if not isinstance(method, (str, unicode)):
            raise TypeError('"method" must be a string (or unicode string).')
        if not isinstance(params, (tuple, list, dict)):
            raise TypeError("params must be a tuple/list/dict or None.")

        if params:
            return '{"jsonrpc": "2.0", "method": %s, "params": %s, "id": %s}' % \
                    (self.dumps(method), self.dumps(params), self.dumps(id))
        else:
            return '{"jsonrpc": "2.0", "method": %s, "id": %s}' % \
                    (self.dumps(method), self.dumps(id))

    def dumps_notification( self, method, params=() ):
        """serialize a JSON-RPC-Notification

        :Parameters: see dumps_request
        :Returns:   | {"jsonrpc": "2.0", "method": "...", "params": ...}
                    | "jsonrpc", "method" and "params" are always in this order.
        :Raises:    see dumps_request
        """
        if not isinstance(method, (str, unicode)):
            raise TypeError('"method" must be a string (or unicode string).')
        if not isinstance(params, (tuple, list, dict)):
            raise TypeError("params must be a tuple/list/dict or None.")

        if params:
            return '{"jsonrpc": "2.0", "method": %s, "params": %s}' % \
                    (self.dumps(method), self.dumps(params))
        else:
            return '{"jsonrpc": "2.0", "method": %s}' % \
                    (self.dumps(method))

    def dumps_response( self, result, id=None ):
        """serialize a JSON-RPC-Response (without error)

        :Returns:   | {"jsonrpc": "2.0", "result": ..., "id": ...}
                    | "jsonrpc", "result", and "id" are always in this order.
        :Raises:    TypeError if not JSON-serializable
        """
        return '{"jsonrpc": "2.0", "result": %s, "id": %s}' % \
                (self.dumps(result), self.dumps(id))

    def dumps_error( self, error, id=None ):
        """serialize a JSON-RPC-Response-error
      
        :Parameters:
            - error: a RPCFault instance
        :Returns:   | {"jsonrpc": "2.0", "error": {"code": error_code, "message": error_message, "data": error_data}, "id": ...}
                    | "jsonrpc", "result", "error" and "id" are always in this order, data is omitted if None.
        :Raises:    ValueError if error is not a RPCFault instance,
                    TypeError if not JSON-serializable
        """
        if not isinstance(error, RPCFault):
            raise ValueError("""error must be a RPCFault-instance.""")
        if error.error_data is None:
            return '{"jsonrpc": "2.0", "error": {"code":%s, "message": %s}, "id": %s}' % \
                    (self.dumps(error.error_code), self.dumps(error.error_message), self.dumps(id))
        else:
            return '{"jsonrpc": "2.0", "error": {"code":%s, "message": %s, "data": %s}, "id": %s}' % \
                    (self.dumps(error.error_code), self.dumps(error.error_message), self.dumps(error.error_data), self.dumps(id))

    def loads_request( self, string ):
        """de-serialize a JSON-RPC Request/Notification

        :Returns:   | [method_name, params, id] or [method_name, params]
                    | params is a tuple/list or dict (with only str-keys)
                    | if id is missing, this is a Notification
        :Raises:    RPCParseError, RPCInvalidRPC, RPCInvalidMethodParams
        """
        try:
            data = self.loads(string)
        except ValueError, err:
            raise RPCParseError("No valid JSON. (%s)" % str(err))
        if not isinstance(data, dict):  raise RPCInvalidRPC("No valid RPC-package.")
        if "jsonrpc" not in data:       raise RPCInvalidRPC("""Invalid Response, "jsonrpc" missing.""")
        if not isinstance(data["jsonrpc"], (str, unicode)):
            raise RPCInvalidRPC("""Invalid Response, "jsonrpc" must be a string.""")
        if data["jsonrpc"] != "2.0":    raise RPCInvalidRPC("""Invalid jsonrpc version.""")
        if "method" not in data:        raise RPCInvalidRPC("""Invalid Request, "method" is missing.""")
        if not isinstance(data["method"], (str, unicode)):
            raise RPCInvalidRPC("""Invalid Request, "method" must be a string.""")
        if "params" not in data:        data["params"] = ()
        #convert params-keys from unicode to str
        elif isinstance(data["params"], dict):
            try:
                data["params"] = dictkeyclean(data["params"])
            except UnicodeEncodeError:
                raise RPCInvalidMethodParams("Parameter-names must be in ascii.")
        elif not isinstance(data["params"], (list, tuple)):
            raise RPCInvalidRPC("""Invalid Request, "params" must be an array or object.""")
        if not( len(data)==3 or ("id" in data and len(data)==4) ):
            raise RPCInvalidRPC("""Invalid Request, additional fields found.""")

        # notification / request
        if "id" not in data:
            return data["method"], data["params"]               #notification
        else:
            return data["method"], data["params"], data["id"]   #request

    def loads_response( self, string ):
        """de-serialize a JSON-RPC Response/error

        :Returns: | [result, id] for Responses
        :Raises:  | RPCFault+derivates for error-packages/faults, RPCParseError, RPCInvalidRPC
        """
        try:
            data = self.loads(string)
        except ValueError, err:
            raise RPCParseError("No valid JSON. (%s)" % str(err))
        if not isinstance(data, dict):  raise RPCInvalidRPC("No valid RPC-package.")
        if "jsonrpc" not in data:       raise RPCInvalidRPC("""Invalid Response, "jsonrpc" missing.""")
        if not isinstance(data["jsonrpc"], (str, unicode)):
            raise RPCInvalidRPC("""Invalid Response, "jsonrpc" must be a string.""")
        if data["jsonrpc"] != "2.0":    raise RPCInvalidRPC("""Invalid jsonrpc version.""")
        if "id" not in data:            raise RPCInvalidRPC("""Invalid Response, "id" missing.""")
        if "result" not in data:        data["result"] = None
        if "error"  not in data:        data["error"]  = None
        if len(data) != 4:              raise RPCInvalidRPC("""Invalid Response, additional or missing fields.""")

        #error
        if data["error"] is not None:
            if data["result"] is not None:
                raise RPCInvalidRPC("""Invalid Response, only "result" OR "error" allowed.""")
            if not isinstance(data["error"], dict): raise RPCInvalidRPC("Invalid Response, invalid error-object.")
            if "code" not in data["error"]  or  "message" not in data["error"]:
                raise RPCInvalidRPC("Invalid Response, invalid error-object.")
            if "data" not in data["error"]:  data["error"]["data"] = None
            if len(data["error"]) != 3:
                raise RPCInvalidRPC("Invalid Response, invalid error-object.")

            error_data = data["error"]["data"]
            if   data["error"]["code"] == PARSE_ERROR:
                raise RPCParseError(error_data)
            elif data["error"]["code"] == INVALID_REQUEST:
                raise RPCInvalidRPC(error_data)
            elif data["error"]["code"] == METHOD_NOT_FOUND:
                raise RPCMethodNotFound(error_data)
            elif data["error"]["code"] == INVALID_METHOD_PARAMS:
                raise RPCInvalidMethodParams(error_data)
            elif data["error"]["code"] == INTERNAL_ERROR:
                raise RPCInternalError(error_data)
            elif data["error"]["code"] == PROCEDURE_EXCEPTION:
                raise RPCProcedureException(error_data)
            elif data["error"]["code"] == AUTHENTIFICATION_ERROR:
                raise RPCAuthentificationError(error_data)
            elif data["error"]["code"] == PERMISSION_DENIED:
                raise RPCPermissionDenied(error_data)
            elif data["error"]["code"] == INVALID_PARAM_VALUES:
                raise RPCInvalidParamValues(error_data)
            else:
                raise RPCFault(data["error"]["code"], data["error"]["message"], error_data)
        #result
        else:
            return data["result"], data["id"]


#=========================================
# transports

#----------------------
# transport-logging

import codecs
import time

def log_dummy( message ):
    """dummy-logger: do nothing"""
    pass
def log_stdout( message ):
    """print message to STDOUT"""
    print message

def log_file( filename ):
    """return a logfunc which logs to a file (in utf-8)"""
    def logfile( message ):
        f = codecs.open( filename, 'a', encoding='utf-8' )
        f.write( message+"\n" )
        f.close()
    return logfile

def log_filedate( filename ):
    """return a logfunc which logs date+message to a file (in utf-8)"""
    def logfile( message ):
        f = codecs.open( filename, 'a', encoding='utf-8' )
        f.write( time.strftime("%Y-%m-%d %H:%M:%S ")+message+"\n" )
        f.close()
    return logfile

#----------------------

class Transport:
    """generic Transport-interface.
    
    This class, and especially its methods and docstrings,
    define the Transport-Interface.
    """
    def __init__(self):
        pass

    def send( self, data ):
        """send all data. must be implemented by derived classes."""
        raise NotImplementedError
    def recv( self ):
        """receive data. must be implemented by derived classes."""
        raise NotImplementedError

    def sendrecv( self, string ):
        """send + receive data"""
        self.send( string )
        return self.recv()
    def serve( self, handler, n=None ):
        """serve (forever or for n communicaions).
        
        - receive data
        - call result = handler(data)
        - send back result if not None

        The serving can be stopped by SIGINT.

        :TODO:
            - how to stop?
              maybe use a .run-file, and stop server if file removed?
            - maybe make n_current accessible? (e.g. for logging)
        """
        n_current = 0
        while 1:
            if n is not None  and  n_current >= n:
                break
            data = self.recv()
            result = handler(data)
            if result is not None:
                self.send( result )
            n_current += 1


class TransportSTDINOUT(Transport):
    """receive from STDIN, send to STDOUT.

    Useful e.g. for debugging.
    """
    def send(self, string):
        """write data to STDOUT with '***SEND:' prefix """
        print "***SEND:"
        print string
    def recv(self):
        """read data from STDIN"""
        print "***RECV (please enter, ^D ends.):"
        return sys.stdin.read()


import socket, select
class TransportSocket(Transport):
    """Transport via socket.
   
    :SeeAlso:   python-module socket
    :TODO:
        - documentation
        - improve this (e.g. make sure that connections are closed, socket-files are deleted etc.)
        - exception-handling? (socket.error)
    """
    def __init__( self, addr, limit=4096, sock_type=socket.AF_INET, sock_prot=socket.SOCK_STREAM, timeout=5.0, logfunc=log_dummy ):
        """
        :Parameters:
            - addr: socket-address
            - timeout: timeout in seconds
            - logfunc: function for logging, logfunc(message)
        :Raises: socket.timeout after timeout
        """
        self.limit  = limit
        self.addr   = addr
        self.s_type = sock_type
        self.s_prot = sock_prot
        self.s      = None
        self.timeout = timeout
        self.log    = logfunc
    def connect( self ):
        self.close()
        self.log( "connect to %s" % repr(self.addr) )
        self.s = socket.socket( self.s_type, self.s_prot )
        self.s.settimeout( self.timeout )
        self.s.connect( self.addr )
    def close( self ):
        if self.s is not None:
            self.log( "close %s" % repr(self.addr) )
            self.s.close()
            self.s = None
    def __repr__(self):
        return "<TransportSocket, %s>" % repr(self.addr)
    
    def send( self, string ):
        if self.s is None:
            self.connect()
        self.log( "--> "+repr(string) )
        self.s.sendall( string )
    def recv( self ):
        if self.s is None:
            self.connect()
        data = self.s.recv( self.limit )
        while( select.select((self.s,), (), (), 0.1)[0] ):  #TODO: this select is probably not necessary, because server closes this socket
            d = self.s.recv( self.limit )
            if len(d) == 0:
                break
            data += d
        self.log( "<-- "+repr(data) )
        return data

    def sendrecv( self, string ):
        """send data + receive data + close"""
        try:
            self.send( string )
            return self.recv()
        finally:
            self.close()
    def serve(self, handler, n=None):
        """open socket, wait for incoming connections and handle them.
        
        :Parameters:
            - n: serve n requests, None=forever
        """
        self.close()
        self.s = socket.socket( self.s_type, self.s_prot )
        try:
            self.log( "listen %s" % repr(self.addr) )
            self.s.bind( self.addr )
            self.s.listen(1)
            n_current = 0
            while 1:
                if n is not None  and  n_current >= n:
                    break
                conn, addr = self.s.accept()
                self.log( "%s connected" % repr(addr) )
                data = conn.recv(self.limit)
                self.log( "%s --> %s" % (repr(addr), repr(data)) )
                result = handler(data)
                if data is not None:
                    self.log( "%s <-- %s" % (repr(addr), repr(result)) )
                    conn.send( result )
                self.log( "%s close" % repr(addr) )
                conn.close()
                n_current += 1
        finally:
            self.close()


if hasattr(socket, 'AF_UNIX'):
    
    class TransportUnixSocket(TransportSocket):
        """Transport via Unix Domain Socket.
        """
        def __init__(self, addr=None, limit=4096, timeout=5.0, logfunc=log_dummy):
            """
            :Parameters:
                - addr: "socket_file"
            :Note: | The socket-file is not deleted.
                   | If the socket-file begins with \x00, abstract sockets are used,
                     and no socket-file is created.
            :SeeAlso:   TransportSocket
            """
            TransportSocket.__init__( self, addr, limit, socket.AF_UNIX, socket.SOCK_STREAM, timeout, logfunc )

class TransportTcpIp(TransportSocket):
    """Transport via TCP/IP.
    """
    def __init__(self, addr=None, limit=4096, timeout=5.0, logfunc=log_dummy):
        """
        :Parameters:
            - addr: ("host",port)
        :SeeAlso:   TransportSocket
        """
        TransportSocket.__init__( self, addr, limit, socket.AF_INET, socket.SOCK_STREAM, timeout, logfunc )


#=========================================
# client side: server proxy

class ServerProxy:
    """RPC-client: server proxy

    A logical connection to a RPC server.

    It works with different data/serializers and different transports.

    Notifications and id-handling/multicall are not yet implemented.

    :Example:
        see module-docstring

    :TODO: verbose/logging?
    """
    def __init__( self, data_serializer, transport ):
        """
        :Parameters:
            - data_serializer: a data_structure+serializer-instance
            - transport: a Transport instance
        """
        #TODO: check parameters
        self.__data_serializer = data_serializer
        if not isinstance(transport, Transport):
            raise ValueError('invalid "transport" (must be a Transport-instance)"')
        self.__transport = transport

    def __str__(self):
        return repr(self)
    def __repr__(self):
        return "<ServerProxy for %s, with serializer %s>" % (self.__transport, self.__data_serializer)

    def __req( self, methodname, args=None, kwargs=None, id=0 ):
        # JSON-RPC 1.0: only positional parameters
        if len(kwargs) > 0 and isinstance(self.data_serializer, JsonRpc10):
            raise ValueError("Only positional parameters allowed in JSON-RPC 1.0")
        # JSON-RPC 2.0: only args OR kwargs allowed!
        if len(args) > 0 and len(kwargs) > 0:
            raise ValueError("Only positional or named parameters are allowed!")
        if len(kwargs) == 0:
            req_str  = self.__data_serializer.dumps_request( methodname, args, id )
        else:
            req_str  = self.__data_serializer.dumps_request( methodname, kwargs, id )
        try:
            resp_str = self.__transport.sendrecv( req_str )
        except Exception,err:
            raise RPCTransportError(err)
        resp = self.__data_serializer.loads_response( resp_str )
        return resp[0]

    def __getattr__(self, name):
        # magic method dispatcher
        #  note: to call a remote object with an non-standard name, use
        #  result getattr(my_server_proxy, "strange-python-name")(args)
        return _method(self.__req, name)

# request dispatcher
class _method:
    """some "magic" to bind an RPC method to an RPC server.

    Supports "nested" methods (e.g. examples.getStateName).

    :Raises: AttributeError for method-names/attributes beginning with '_'.
    """
    def __init__(self, req, name):
        if name[0] == "_":  #prevent rpc-calls for proxy._*-functions
            raise AttributeError("invalid attribute '%s'" % name)
        self.__req  = req
        self.__name = name
    def __getattr__(self, name):
        if name[0] == "_":  #prevent rpc-calls for proxy._*-functions
            raise AttributeError("invalid attribute '%s'" % name)
        return _method(self.__req, "%s.%s" % (self.__name, name))
    def __call__(self, *args, **kwargs):
        return self.__req(self.__name, args, kwargs)

#=========================================
# server side: Server

class Server:
    """RPC-server.

    It works with different data/serializers and 
    with different transports.

    :Example:
        see module-docstring

    :TODO:
        - mixed JSON-RPC 1.0/2.0 server?
        - logging/loglevels?
    """
    def __init__( self, data_serializer, transport, logfile=None ):
        """
        :Parameters:
            - data_serializer: a data_structure+serializer-instance
            - transport: a Transport instance
            - logfile: file to log ("unexpected") errors to
        """
        #TODO: check parameters
        self.__data_serializer = data_serializer
        if not isinstance(transport, Transport):
            raise ValueError('invalid "transport" (must be a Transport-instance)"')
        self.__transport = transport
        self.logfile = logfile
        if self.logfile is not None:    #create logfile (or raise exception)
            f = codecs.open( self.logfile, 'a', encoding='utf-8' )
            f.close()

        self.funcs = {}

    def __repr__(self):
        return "<Server for %s, with serializer %s>" % (self.__transport, self.__data_serializer)

    def log(self, message):
        """write a message to the logfile (in utf-8)"""
        if self.logfile is not None:
            f = codecs.open( self.logfile, 'a', encoding='utf-8' )
            f.write( time.strftime("%Y-%m-%d %H:%M:%S ")+message+"\n" )
            f.close()

    def register_instance(self, myinst, name=None):
        """Add all functions of a class-instance to the RPC-services.
        
        All entries of the instance which do not begin with '_' are added.

        :Parameters:
            - myinst: class-instance containing the functions
            - name:   | hierarchical prefix.
                      | If omitted, the functions are added directly.
                      | If given, the functions are added as "name.function".
        :TODO:
            - only add functions and omit attributes?
            - improve hierarchy?
        """
        for e in dir(myinst):
            if e[0][0] != "_":
                if name is None:
                    self.register_function( getattr(myinst, e) )
                else:
                    self.register_function( getattr(myinst, e), name="%s.%s" % (name, e) )
    def register_function(self, function, name=None):
        """Add a function to the RPC-services.
        
        :Parameters:
            - function: function to add
            - name:     RPC-name for the function. If omitted/None, the original
                        name of the function is used.
        """
        if name is None:
            self.funcs[function.__name__] = function
        else:
            self.funcs[name] = function
    
    def handle(self, rpcstr):
        """Handle a RPC-Request.

        :Parameters:
            - rpcstr: the received rpc-string
        :Returns: the data to send back or None if nothing should be sent back
        :Raises:  RPCFault (and maybe others)
        """
        #TODO: id
        notification = False
        try:
            req = self.__data_serializer.loads_request( rpcstr )
            if len(req) == 2:       #notification
                method, params = req
                notification = True
            else:                   #request
                method, params, id = req
        except RPCFault, err:
            return self.__data_serializer.dumps_error( err, id=None )
        except Exception, err:
            self.log( "%d (%s): %s" % (INTERNAL_ERROR, ERROR_MESSAGE[INTERNAL_ERROR], str(err)) )
            return self.__data_serializer.dumps_error( RPCFault(INTERNAL_ERROR, ERROR_MESSAGE[INTERNAL_ERROR]), id=None )

        if method not in self.funcs:
            if notification:
                return None
            return self.__data_serializer.dumps_error( RPCFault(METHOD_NOT_FOUND, ERROR_MESSAGE[METHOD_NOT_FOUND]), id )

        try:
            if isinstance(params, dict):
                result = self.funcs[method]( **params )
            else:
                result = self.funcs[method]( *params )
        except RPCFault, err:
            if notification:
                return None
            return self.__data_serializer.dumps_error( err, id=None )
        except Exception, err:
            if notification:
                return None
            self.log( "%d (%s): %s" % (INTERNAL_ERROR, ERROR_MESSAGE[INTERNAL_ERROR], str(err)) )
            return self.__data_serializer.dumps_error( RPCFault(INTERNAL_ERROR, ERROR_MESSAGE[INTERNAL_ERROR]), id )

        if notification:
            return None
        try:
            return self.__data_serializer.dumps_response( result, id )
        except Exception, err:
            self.log( "%d (%s): %s" % (INTERNAL_ERROR, ERROR_MESSAGE[INTERNAL_ERROR], str(err)) )
            return self.__data_serializer.dumps_error( RPCFault(INTERNAL_ERROR, ERROR_MESSAGE[INTERNAL_ERROR]), id )

    def serve(self, n=None):
        """serve (forever or for n communicaions).
        
        :See: Transport
        """
        self.__transport.serve( self.handle, n )

#=========================================


########NEW FILE########
__FILENAME__ = progressbar
#!/usr/bin/python
# -*- coding: iso-8859-1 -*-
#
# progressbar  - Text progressbar library for python.
# Copyright (c) 2005 Nilton Volpato
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA


"""Text progressbar library for python.

This library provides a text mode progressbar. This is typically used
to display the progress of a long running operation, providing a
visual clue that processing is underway.

The ProgressBar class manages the progress, and the format of the line
is given by a number of widgets. A widget is an object that may
display diferently depending on the state of the progress. There are
three types of widget:
- a string, which always shows itself;
- a ProgressBarWidget, which may return a diferent value every time
it's update method is called; and
- a ProgressBarWidgetHFill, which is like ProgressBarWidget, except it
expands to fill the remaining width of the line.

The progressbar module is very easy to use, yet very powerful. And
automatically supports features like auto-resizing when available.
"""

__author__ = "Nilton Volpato"
__author_email__ = "first-name dot last-name @ gmail.com"
__date__ = "2006-05-07"
__version__ = "2.2"

# Changelog
#
# 2006-05-07: v2.2 fixed bug in windows
# 2005-12-04: v2.1 autodetect terminal width, added start method
# 2005-12-04: v2.0 everything is now a widget (wow!)
# 2005-12-03: v1.0 rewrite using widgets
# 2005-06-02: v0.5 rewrite
# 2004-??-??: v0.1 first version

import sys
import time
from array import array
try:
    from fcntl import ioctl
    import termios
except ImportError:
    pass
import signal


class ProgressBarWidget(object):
    """This is an element of ProgressBar formatting.

    The ProgressBar object will call it's update value when an update
    is needed. It's size may change between call, but the results will
    not be good if the size changes drastically and repeatedly.
    """
    def update(self, pbar):
        """Returns the string representing the widget.

        The parameter pbar is a reference to the calling ProgressBar,
        where one can access attributes of the class for knowing how
        the update must be made.

        At least this function must be overriden."""
        pass


class ProgressBarWidgetHFill(object):
    """This is a variable width element of ProgressBar formatting.

    The ProgressBar object will call it's update value, informing the
    width this object must the made. This is like TeX \\hfill, it will
    expand to fill the line. You can use more than one in the same
    line, and they will all have the same width, and together will
    fill the line.
    """
    def update(self, pbar, width):
        """Returns the string representing the widget.

        The parameter pbar is a reference to the calling ProgressBar,
        where one can access attributes of the class for knowing how
        the update must be made. The parameter width is the total
        horizontal width the widget must have.

        At least this function must be overriden."""
        pass


class ETA(ProgressBarWidget):
    "Widget for the Estimated Time of Arrival"
    def format_time(self, seconds):
        return time.strftime('%H:%M:%S', time.gmtime(seconds))

    def update(self, pbar):
        if pbar.currval == 0:
            return 'ETA:  --:--:--'
        elif pbar.finished:
            return 'Time: %s' % self.format_time(pbar.seconds_elapsed)
        else:
            elapsed = pbar.seconds_elapsed
            eta = elapsed * pbar.maxval / pbar.currval - elapsed
            return 'ETA:  %s' % self.format_time(eta)


class FileTransferSpeed(ProgressBarWidget):
    "Widget for showing the transfer speed (useful for file transfers)."
    def __init__(self):
        self.fmt = '%6.2f %s'
        self.units = ['B', 'K', 'M', 'G', 'T', 'P']

    def update(self, pbar):
        if pbar.seconds_elapsed < 2e-6:  # == 0:
            bps = 0.0
        else:
            bps = float(pbar.currval) / pbar.seconds_elapsed
        spd = bps
        for u in self.units:
            if spd < 1000:
                break
            spd /= 1000
        return self.fmt % (spd, u + '/s')


class RotatingMarker(ProgressBarWidget):
    "A rotating marker for filling the bar of progress."
    def __init__(self, markers='|/-\\'):
        self.markers = markers
        self.curmark = -1

    def update(self, pbar):
        if pbar.finished:
            return self.markers[0]
        self.curmark = (self.curmark + 1) % len(self.markers)
        return self.markers[self.curmark]


class Percentage(ProgressBarWidget):
    "Just the percentage done."
    def update(self, pbar):
        return '%3d%%' % pbar.percentage()


class Fraction(ProgressBarWidget):
    "Just the fraction done."
    def update(self, pbar):
        return "%d/%d" % (pbar.currval, pbar.maxval)


class Bar(ProgressBarWidgetHFill):
    "The bar of progress. It will strech to fill the line."
    def __init__(self, marker='#', left='|', right='|'):
        self.marker = marker
        self.left = left
        self.right = right

    def _format_marker(self, pbar):
        if isinstance(self.marker, (str, unicode)):
            return self.marker
        else:
            return self.marker.update(pbar)

    def update(self, pbar, width):
        percent = pbar.percentage()
        cwidth = width - len(self.left) - len(self.right)
        marked_width = int(percent * cwidth / 100)
        m = self._format_marker(pbar)
        bar = (self.left + (m * marked_width).ljust(cwidth) + self.right)
        return bar


class ReverseBar(Bar):
    "The reverse bar of progress, or bar of regress. :)"
    def update(self, pbar, width):
        percent = pbar.percentage()
        cwidth = width - len(self.left) - len(self.right)
        marked_width = int(percent * cwidth / 100)
        m = self._format_marker(pbar)
        bar = (self.left + (m * marked_width).rjust(cwidth) + self.right)
        return bar

default_widgets = [Percentage(), ' ', Bar()]


class ProgressBar(object):
    """This is the ProgressBar class, it updates and prints the bar.

    The term_width parameter may be an integer. Or None, in which case
    it will try to guess it, if it fails it will default to 80 columns.

    The simple use is like this:
    >>> pbar = ProgressBar().start()
    >>> for i in xrange(100):
    ...    # do something
    ...    pbar.update(i+1)
    ...
    >>> pbar.finish()

    But anything you want to do is possible (well, almost anything).
    You can supply different widgets of any type in any order. And you
    can even write your own widgets! There are many widgets already
    shipped and you should experiment with them.

    When implementing a widget update method you may access any
    attribute or function of the ProgressBar object calling the
    widget's update method. The most important attributes you would
    like to access are:
    - currval: current value of the progress, 0 <= currval <= maxval
    - maxval: maximum (and final) value of the progress
    - finished: True if the bar is have finished (reached 100%), False o/w
    - start_time: first time update() method of ProgressBar was called
    - seconds_elapsed: seconds elapsed since start_time
    - percentage(): percentage of the progress (this is a method)
    """
    def __init__(self, maxval=100, widgets=default_widgets, term_width=None,
                 fd=sys.stderr, force_update=False):
        assert maxval > 0
        self.maxval = maxval
        self.widgets = widgets
        self.fd = fd
        self.signal_set = False
        if term_width is None:
            try:
                self.handle_resize(None, None)
                signal.signal(signal.SIGWINCH, self.handle_resize)
                self.signal_set = True
            except:
                self.term_width = 79
        else:
            self.term_width = term_width

        self.currval = 0
        self.finished = False
        self.prev_percentage = -1
        self.start_time = None
        self.seconds_elapsed = 0
        self.force_update = force_update

    def handle_resize(self, signum, frame):
        h, w = array('h', ioctl(self.fd, termios.TIOCGWINSZ, '\0' * 8))[:2]
        self.term_width = w

    def percentage(self):
        "Returns the percentage of the progress."
        return self.currval * 100.0 / self.maxval

    def _format_widgets(self):
        r = []
        hfill_inds = []
        num_hfill = 0
        currwidth = 0
        for i, w in enumerate(self.widgets):
            if isinstance(w, ProgressBarWidgetHFill):
                r.append(w)
                hfill_inds.append(i)
                num_hfill += 1
            elif isinstance(w, (str, unicode)):
                r.append(w)
                currwidth += len(w)
            else:
                weval = w.update(self)
                currwidth += len(weval)
                r.append(weval)
        for iw in hfill_inds:
            r[iw] = r[iw].update(self,
                                 (self.term_width - currwidth) / num_hfill)
        return r

    def _format_line(self):
        return ''.join(self._format_widgets()).ljust(self.term_width)

    def _need_update(self):
        if self.force_update:
            return True
        return int(self.percentage()) != int(self.prev_percentage)

    def reset(self):
        if not self.finished and self.start_time:
            self.finish()
        self.finished = False
        self.currval = 0
        self.start_time = None
        self.seconds_elapsed = None
        self.prev_percentage = None
        return self

    def update(self, value):
        "Updates the progress bar to a new value."
        assert 0 <= value <= self.maxval
        self.currval = value
        if not self._need_update() or self.finished:
            return
        if not self.start_time:
            self.start_time = time.time()
        self.seconds_elapsed = time.time() - self.start_time
        self.prev_percentage = self.percentage()
        if value != self.maxval:
            self.fd.write(self._format_line() + '\r')
        else:
            self.finished = True
            self.fd.write(self._format_line() + '\n')

    def start(self):
        """Start measuring time, and prints the bar at 0%.

        It returns self so you can use it like this:
        >>> pbar = ProgressBar().start()
        >>> for i in xrange(100):
        ...    # do something
        ...    pbar.update(i+1)
        ...
        >>> pbar.finish()
        """
        self.update(0)
        return self

    def finish(self):
        """Used to tell the progress is finished."""
        self.update(self.maxval)
        if self.signal_set:
            signal.signal(signal.SIGWINCH, signal.SIG_DFL)


def example1():
    widgets = ['Test: ', Percentage(), ' ', Bar(marker=RotatingMarker()),
               ' ', ETA(), ' ', FileTransferSpeed()]
    pbar = ProgressBar(widgets=widgets, maxval=10000000).start()
    for i in range(1000000):
        # do something
        pbar.update(10 * i + 1)
    pbar.finish()
    return pbar


def example2():
    class CrazyFileTransferSpeed(FileTransferSpeed):
        "It's bigger between 45 and 80 percent"
        def update(self, pbar):
            if 45 < pbar.percentage() < 80:
                return 'Bigger Now ' + FileTransferSpeed.update(self, pbar)
            else:
                return FileTransferSpeed.update(self, pbar)

    widgets = [CrazyFileTransferSpeed(), ' <<<',
               Bar(), '>>> ', Percentage(), ' ', ETA()]
    pbar = ProgressBar(widgets=widgets, maxval=10000000)
    # maybe do something
    pbar.start()
    for i in range(2000000):
        # do something
        pbar.update(5 * i + 1)
    pbar.finish()
    return pbar


def example3():
    widgets = [Bar('>'), ' ', ETA(), ' ', ReverseBar('<')]
    pbar = ProgressBar(widgets=widgets, maxval=10000000).start()
    for i in range(1000000):
        # do something
        pbar.update(10 * i + 1)
    pbar.finish()
    return pbar


def example4():
    widgets = ['Test: ', Percentage(), ' ',
               Bar(marker='0', left='[', right=']'),
               ' ', ETA(), ' ', FileTransferSpeed()]
    pbar = ProgressBar(widgets=widgets, maxval=500)
    pbar.start()
    for i in range(100, 500 + 1, 50):
        time.sleep(0.2)
        pbar.update(i)
    pbar.finish()
    return pbar


def example5():
    widgets = ['Test: ', Fraction(), ' ', Bar(marker=RotatingMarker()),
               ' ', ETA(), ' ', FileTransferSpeed()]
    pbar = ProgressBar(widgets=widgets, maxval=10, force_update=True).start()
    for i in range(1, 11):
        # do something
        time.sleep(0.5)
        pbar.update(i)
    pbar.finish()
    return pbar


def main():
    example1()
    print
    example2()
    print
    example3()
    print
    example4()
    print
    example5()
    print

if __name__ == '__main__':
    main()

########NEW FILE########
