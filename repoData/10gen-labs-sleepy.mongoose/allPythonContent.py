__FILENAME__ = httpd
sleepymongoose/httpd.py
########NEW FILE########
__FILENAME__ = handlers
# Copyright 2009-2010 10gen, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from bson.son import SON
from pymongo import Connection, ASCENDING, DESCENDING
from pymongo.errors import ConnectionFailure, ConfigurationError, OperationFailure, AutoReconnect
from bson import json_util

import re
try:
    import json
except ImportError:
    import simplejson as json

class MongoHandler:
    mh = None

    _cursor_id = 0

    def __init__(self, mongos):
        self.connections = {}

        for host in mongos:
            args = MongoFakeFieldStorage({"server" : host})

            out = MongoFakeStream()
            if len(mongos) == 1:
                name = "default"
            else:
                name = host.replace(".", "") 
                name = name.replace(":", "")

            self._connect(args, out.ostream, name = name)
        
    def _get_connection(self, name = None, uri='mongodb://localhost:27017'):
        if name == None:
            name = "default"

        if name in self.connections:
            return self.connections[name]
        
        try:
            connection = Connection(uri, network_timeout = 2)
        except (ConnectionFailure, ConfigurationError):
            return None

        self.connections[name] = connection
        return connection

    def _get_host_and_port(self, server):
        host = "localhost"
        port = 27017

        if len(server) == 0:
            return (host, port)

        m = re.search('([^:]+):([0-9]+)?', server)
        if m == None:
            return (host, port)

        handp = m.groups()

        if len(handp) >= 1:
            host = handp[0]
        if len(handp) == 2 and handp[1] != None:
            port = int(handp[1])

        return (host, port)

    def sm_object_hook(obj):
        if "$pyhint" in obj:
            temp = SON()
            for pair in obj['$pyhint']:
                temp[pair['key']] = pair['value']
            return temp
        else:
            return json_util.object_hook(obj)


    def _get_son(self, str, out):
        try:
            obj = json.loads(str, object_hook=json_util.object_hook)
        except (ValueError, TypeError):
            out('{"ok" : 0, "errmsg" : "couldn\'t parse json: %s"}' % str)
            return None

        if getattr(obj, '__iter__', False) == False:
            out('{"ok" : 0, "errmsg" : "type is not iterable: %s"}' % str)
            return None
 
        return obj


    def _cmd(self, args, out, name = None, db = None, collection = None):
        if name == None:
            name = "default"

        conn = self._get_connection(name)
        if conn == None:
            out('{"ok" : 0, "errmsg" : "couldn\'t get connection to mongo"}')
            return

        cmd = self._get_son(args.getvalue('cmd'), out)
        if cmd == None:
            return

        try:
            result = conn[db].command(cmd, check=False)
        except AutoReconnect:
            out('{"ok" : 0, "errmsg" : "wasn\'t connected to the db and '+
                'couldn\'t reconnect", "name" : "%s"}' % name)
            return
        except (OperationFailure, error):
            out('{"ok" : 0, "errmsg" : "%s"}' % error)
            return

        # debugging
        if result['ok'] == 0:
            result['cmd'] = args.getvalue('cmd')

        out(json.dumps(result, default=json_util.default))
        
    def _hello(self, args, out, name = None, db = None, collection = None):
        out('{"ok" : 1, "msg" : "Uh, we had a slight weapons malfunction, but ' + 
            'uh... everything\'s perfectly all right now. We\'re fine. We\'re ' +
            'all fine here now, thank you. How are you?"}')
        return
        
    def _status(self, args, out, name = None, db = None, collection = None):
        result = {"ok" : 1, "connections" : {}}

        for name, conn in self.connections.iteritems():
            result['connections'][name] = "%s:%d" % (conn.host, conn.port)

        out(json.dumps(result))
    
    def _connect(self, args, out, name = None, db = None, collection = None):
        """
        connect to a mongod
        """

        if type(args).__name__ == 'dict':
            out('{"ok" : 0, "errmsg" : "_connect must be a POST request"}')
            return

        if "server" in args:
            try:
                uri = args.getvalue('server')
            except Exception, e:
                print uri
                print e
                out('{"ok" : 0, "errmsg" : "invalid server uri given", "server" : "%s"}' % uri)
                return
        else:
            uri = 'mongodb://localhost:27017'

        if name == None:
            name = "default"

        conn = self._get_connection(name, uri)
        if conn != None:
            out('{"ok" : 1, "server" : "%s", "name" : "%s"}' % (uri, name))
        else:
            out('{"ok" : 0, "errmsg" : "could not connect", "server" : "%s", "name" : "%s"}' % (uri, name))

    def _authenticate(self, args, out, name = None, db = None, collection = None):
        """
        authenticate to the database.
        """

        if type(args).__name__ == 'dict':
            out('{"ok" : 0, "errmsg" : "_find must be a POST request"}')
            return

        conn = self._get_connection(name)
        if conn == None:
            out('{"ok" : 0, "errmsg" : "couldn\'t get connection to mongo"}')
            return

        if db == None:
            out('{"ok" : 0, "errmsg" : "db must be defined"}')
            return

        if not 'username' in args:
            out('{"ok" : 0, "errmsg" : "username must be defined"}')

        if not 'password' in args:
            out('{"ok" : 0, "errmsg" : "password must be defined"}')
        
        if not conn[db].authenticate(args.getvalue('username'), args.getvalue('password')):
            out('{"ok" : 0, "errmsg" : "authentication failed"}')
        else:
            out('{"ok" : 1}')
        
    def _find(self, args, out, name = None, db = None, collection = None):
        """
        query the database.
        """

        if type(args).__name__ != 'dict':
            out('{"ok" : 0, "errmsg" : "_find must be a GET request"}')
            return

        conn = self._get_connection(name)
        if conn == None:
            out('{"ok" : 0, "errmsg" : "couldn\'t get connection to mongo"}')
            return

        if db == None or collection == None:
            out('{"ok" : 0, "errmsg" : "db and collection must be defined"}')
            return            

        criteria = {}
        if 'criteria' in args:
            criteria = self._get_son(args['criteria'][0], out)
            if criteria == None:
                return

        fields = None
        if 'fields' in args:
            fields = self._get_son(args['fields'][0], out)
            if fields == None:
                return

        limit = 0
        if 'limit' in args:
            limit = int(args['limit'][0])

        skip = 0
        if 'skip' in args:
            skip = int(args['skip'][0])

        cursor = conn[db][collection].find(spec=criteria, fields=fields, limit=limit, skip=skip)

        sort = None
        if 'sort' in args:
            sort = self._get_son(args['sort'][0], out)
            if sort == None:
                return

            stupid_sort = []

            for field in sort:
                if sort[field] == -1:
                    stupid_sort.append([field, DESCENDING])
                else:
                    stupid_sort.append([field, ASCENDING])

            cursor.sort(stupid_sort)

        if 'explain' in args and bool(args['explain'][0]):
            out(json.dumps({"results" : [cursor.explain()], "ok" : 1}, default=json_util.default))


        if not hasattr(self, "cursors"):
            setattr(self, "cursors", {})

        id = MongoHandler._cursor_id
        MongoHandler._cursor_id = MongoHandler._cursor_id + 1

        cursors = getattr(self, "cursors")
        cursors[id] = cursor
        setattr(cursor, "id", id)

        batch_size = 15
        if 'batch_size' in args:
            batch_size = int(args['batch_size'][0])
            
        self.__output_results(cursor, out, batch_size)


    def _more(self, args, out, name = None, db = None, collection = None):
        """
        Get more results from a cursor
        """

        if type(args).__name__ != 'dict':
            out('{"ok" : 0, "errmsg" : "_more must be a GET request"}')
            return

        if 'id' not in args:
            out('{"ok" : 0, "errmsg" : "no cursor id given"}')
            return


        id = int(args["id"][0])
        cursors = getattr(self, "cursors")

        if id not in cursors:
            out('{"ok" : 0, "errmsg" : "couldn\'t find the cursor with id %d"}' % id)
            return

        cursor = cursors[id]

        batch_size = 15
        if 'batch_size' in args:
            batch_size = int(args['batch_size'][0])

        self.__output_results(cursor, out, batch_size)


    def __output_results(self, cursor, out, batch_size=15):
        """
        Iterate through the next batch
        """
        batch = []

        try:
            while len(batch) < batch_size:
                batch.append(cursor.next())
        except AutoReconnect:
            out(json.dumps({"ok" : 0, "errmsg" : "auto reconnecting, please try again"}))
            return
        except OperationFailure, of:
            out(json.dumps({"ok" : 0, "errmsg" : "%s" % of}))
            return
        except StopIteration:
            # this is so stupid, there's no has_next?
            pass
        
        out(json.dumps({"results" : batch, "id" : cursor.id, "ok" : 1}, default=json_util.default))


    def _insert(self, args, out, name = None, db = None, collection = None):
        """
        insert a doc
        """

        if type(args).__name__ == 'dict':
            out('{"ok" : 0, "errmsg" : "_insert must be a POST request"}')
            return

        conn = self._get_connection(name)
        if conn == None:
            out('{"ok" : 0, "errmsg" : "couldn\'t get connection to mongo"}')
            return

        if db == None or collection == None:
            out('{"ok" : 0, "errmsg" : "db and collection must be defined"}')
            return

        if "docs" not in args: 
            out('{"ok" : 0, "errmsg" : "missing docs"}')
            return

        docs = self._get_son(args.getvalue('docs'), out)
        if docs == None:
            return

        safe = False
        if "safe" in args:
            safe = bool(args.getvalue("safe"))

        result = {}
        result['oids'] = conn[db][collection].insert(docs)
        if safe:
            result['status'] = conn[db].last_status()

        out(json.dumps(result, default=json_util.default))


    def __safety_check(self, args, out, db):
        safe = False
        if "safe" in args:
            safe = bool(args.getvalue("safe"))

        if safe:
            result = db.last_status()
            out(json.dumps(result, default=json_util.default))
        else:
            out('{"ok" : 1}')


    def _update(self, args, out, name = None, db = None, collection = None):
        """
        update a doc
        """

        if type(args).__name__ == 'dict':
            out('{"ok" : 0, "errmsg" : "_update must be a POST request"}')
            return

        conn = self._get_connection(name)
        if conn == None:
            out('{"ok" : 0, "errmsg" : "couldn\'t get connection to mongo"}')
            return

        if db == None or collection == None:
            out('{"ok" : 0, "errmsg" : "db and collection must be defined"}')
            return
        
        if "criteria" not in args: 
            out('{"ok" : 0, "errmsg" : "missing criteria"}')
            return
        criteria = self._get_son(args.getvalue('criteria'), out)
        if criteria == None:
            return

        if "newobj" not in args:
            out('{"ok" : 0, "errmsg" : "missing newobj"}')
            return
        newobj = self._get_son(args.getvalue('newobj'), out)
        if newobj == None:
            return
        
        upsert = False
        if "upsert" in args:
            upsert = bool(args.getvalue('upsert'))

        multi = False
        if "multi" in args:
            multi = bool(args.getvalue('multi'))

        conn[db][collection].update(criteria, newobj, upsert=upsert, multi=multi)

        self.__safety_check(args, out, conn[db])

    def _remove(self, args, out, name = None, db = None, collection = None):
        """
        remove docs
        """

        if type(args).__name__ == 'dict':
            out('{"ok" : 0, "errmsg" : "_remove must be a POST request"}')
            return

        conn = self._get_connection(name)
        if conn == None:
            out('{"ok" : 0, "errmsg" : "couldn\'t get connection to mongo"}')
            return

        if db == None or collection == None:
            out('{"ok" : 0, "errmsg" : "db and collection must be defined"}')
            return
        
        criteria = {}
        if "criteria" in args:
            criteria = self._get_son(args.getvalue('criteria'), out)
            if criteria == None:
                return
        
        result = conn[db][collection].remove(criteria)

        self.__safety_check(args, out, conn[db])

    def _batch(self, args, out, name = None, db = None, collection = None):
        """
        batch process commands
        """

        if type(args).__name__ == 'dict':
            out('{"ok" : 0, "errmsg" : "_batch must be a POST request"}')
            return

        requests = self._get_son(args.getvalue('requests'), out)
        if requests == None:
            return

        out("[")

        first = True
        for request in requests:
            if "cmd" not in request:
                continue

            cmd = request['cmd']
            method = "GET"
            if 'method' in request:
                method = request['method']
            
            db = None
            if 'db' in request:
                db = request['db']

            collection = None
            if 'collection' in request:
                collection = request['collection']

            args = {}
            name = None
            if 'args' in request:
                args = request['args']
                if 'name' in args:
                    name = args['name']

            if method == "POST":
                args = MongoFakeFieldStorage(args)

            func = getattr(MongoHandler.mh, cmd, None)
            if callable(func):
                output = MongoFakeStream()
                func(args, output.ostream, name = name, db = db, collection = collection)
                if not first:
                    out(",")
                first = False

                out(output.get_ostream())
            else:
                continue

        out("]")

        
class MongoFakeStream:
    def __init__(self):
        self.str = ""

    def ostream(self, content):
        self.str = self.str + content

    def get_ostream(self):
        return self.str

class MongoFakeFieldStorage:
    def __init__(self, args):
        self.args = args

    def getvalue(self, key):
        return self.args[key]

    def __contains__(self, key):
        return key in self.args

########NEW FILE########
__FILENAME__ = httpd
# Copyright 2009-2010 10gen, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from SocketServer import BaseServer
from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
from handlers import MongoHandler

try:
    from OpenSSL import SSL
except ImportError:
    pass

import os.path, socket
import urlparse
import cgi
import getopt
import sys

try:
    import json
except ImportError:
    import simplejson as json

# support python 2.5 (parse_qs was moved from cgi to urlparse in python 2.6)
try:
    urlparse.parse_qs
except AttributeError:
    urlparse.parse_qs = cgi.parse_qs



class MongoServer(HTTPServer):

    pem = None

    def __init__(self, server_address, HandlerClass):
        BaseServer.__init__(self, server_address, HandlerClass)
        ctx = SSL.Context(SSL.SSLv23_METHOD)

        fpem = MongoServer.pem
        ctx.use_privatekey_file(fpem)
        ctx.use_certificate_file(fpem)
        
        self.socket = SSL.Connection(ctx, socket.socket(self.address_family,
                                                        self.socket_type))
        self.server_bind()
        self.server_activate()


class MongoHTTPRequest(BaseHTTPRequestHandler):

    mimetypes = { "html" : "text/html",
                  "htm" : "text/html",
                  "gif" : "image/gif",
                  "jpg" : "image/jpeg",
                  "png" : "image/png",
                  "json" : "application/json",
                  "css" : "text/css",
                  "js" : "text/javascript",
                  "ico" : "image/vnd.microsoft.icon" }

    docroot = "."
    mongos = []
    response_headers = []
    jsonp_callback = None;

    def _parse_call(self, uri):
        """ 
        this turns a uri like: /foo/bar/_query into properties: using the db 
        foo, the collection bar, executing a query.

        returns the database, collection, and action
        """
        parts = uri.split('/')

        # operations always start with _
        if parts[-1][0] != '_':
            return (None, None, None)

        if len(parts) == 1:
            return ("admin", None, parts[0])
        elif len(parts) == 2:
            return (parts[0], None, parts[1])
        else:
            return (parts[0], ".".join(parts[1:-1]), parts[-1])


    def call_handler(self, uri, args):
        """ execute something """

        (db, collection, func_name) = self._parse_call(uri)
        if db == None or func_name == None:
            self.send_error(404, 'Script Not Found: '+uri)
            return

        name = None
        if "name" in args:
            if type(args).__name__ == "dict":
                name = args["name"][0]
            else:
                name = args.getvalue("name")

        self.jsonp_callback = None
        if "callback" in args:
            if type(args).__name__ == "dict":
                self.jsonp_callback = args["callback"][0]
            else:
                self.jsonp_callback = args.getvalue("callback")
                
        func = getattr(MongoHandler.mh, func_name, None)
        if callable(func):
            self.send_response(200, 'OK')
            self.send_header('Content-type', MongoHTTPRequest.mimetypes['json'])
            for header in self.response_headers:
                self.send_header(header[0], header[1])
            self.end_headers()

            if self.jsonp_callback:
                func(args, self.prependJSONPCallback, name = name, db = db, collection = collection)
            else:
                func(args, self.wfile.write, name = name, db = db, collection = collection)

            return
        else:
            self.send_error(404, 'Script Not Found: '+uri)
            return            
        
    def prependJSONPCallback(self, str):
        jsonp_output = '%s(' % self.jsonp_callback + str + ')'
        self.wfile.write( jsonp_output )
        
    # TODO: check for ..s
    def process_uri(self, method):
        if method == "GET":
            (uri, q, args) = self.path.partition('?')
        else:
            uri = self.path
            if 'Content-Type' in self.headers:
                args = cgi.FieldStorage(fp=self.rfile, headers=self.headers,
                                        environ={'REQUEST_METHOD':'POST',
                                                 'CONTENT_TYPE':self.headers['Content-Type']})
            else:
                self.send_response(100, "Continue")
                self.send_header('Content-type', MongoHTTPRequest.mimetypes['json'])
                for header in self.response_headers:
                    self.send_header(header[0], header[1])
                self.end_headers()
                self.wfile.write('{"ok" : 0, "errmsg" : "100-continue msgs not handled yet"}')

                return (None, None, None)


        uri = uri.strip('/')

        # default "/" to "/index.html"
        if len(uri) == 0:
            uri = "index.html"

        (temp, dot, type) = uri.rpartition('.')
        # if we have a collection name with a dot, don't use that dot for type
        if len(dot) == 0 or uri.find('/') != -1:
            type = ""

        return (uri, args, type)


    def do_GET(self):        
        (uri, args, type) = self.process_uri("GET")

 
        # serve up a plain file
        if len(type) != 0:
            if type in MongoHTTPRequest.mimetypes and os.path.exists(MongoHTTPRequest.docroot+uri):

                fh = open(MongoHTTPRequest.docroot+uri, 'r')

                self.send_response(200, 'OK')
                self.send_header('Content-type', MongoHTTPRequest.mimetypes[type])
                for header in self.response_headers:
                    self.send_header(header[0], header[1])
                self.end_headers()
                self.wfile.write(fh.read())

                fh.close()

                return

            else:
                self.send_error(404, 'File Not Found: '+uri)

                return

        # make sure args is an array of tuples
        if len(args) != 0:
            args = urlparse.parse_qs(args)
        else:
            args = {}

        self.call_handler(uri, args)
        #self.wfile.write( self.path )

    def do_POST(self):
        (uri, args, type) = self.process_uri("POST")
        if uri == None:
            return
        self.call_handler(uri, args)

    @staticmethod
    def serve_forever(port):
        print "\n================================="
        print "|      MongoDB REST Server      |"
        print "=================================\n"

        if MongoServer.pem == None:
            try:
                server = HTTPServer(('', port), MongoHTTPRequest)
            except socket.error, (value, message):
                if value == 98:
                    print "could not bind to localhost:%d... is sleepy.mongoose already running?\n" % port
                else:
                    print message
                return
        else:
            print "--------Secure Connection--------\n"
            server = MongoServer(('', port), MongoHTTPSRequest)

        MongoHandler.mh = MongoHandler(MongoHTTPRequest.mongos)
        
        print "listening for connections on http://localhost:27080\n"
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            print "\nShutting down the server..."
            server.socket.close()
            print "\nGood bye!\n"


class MongoHTTPSRequest(MongoHTTPRequest):
    def setup(self):
        self.connection = self.request
        self.rfile = socket._fileobject(self.request, "rb", self.rbufsize)
        self.wfile = socket._fileobject(self.request, "wb", self.wbufsize)


def usage():
    print "python httpd.py [-x] [-d docroot/dir] [-s certificate.pem] [-m list,of,mongods]"
    print "\t-x|--xorigin\tAllow cross-origin http requests"
    print "\t-d|--docroot\tlocation from which to load files"
    print "\t-s|--secure\tlocation of .pem file if ssl is desired"
    print "\t-m|--mongos\tcomma-separated list of mongo servers to connect to"


def main():
    try:
        opts, args = getopt.getopt(sys.argv[1:], "xd:s:m:", ["xorigin", "docroot=",
            "secure=", "mongos="])

        for o, a in opts:
            if o == "-d" or o == "--docroot":
                if not a.endswith('/'):
                    a = a+'/'
                MongoHTTPRequest.docroot = a
            if o == "-s" or o == "--secure":
                MongoServer.pem = a
            if o == "-m" or o == "--mongos":
                MongoHTTPRequest.mongos = a.split(',')
            if o == "-x" or o == "--xorigin":
                MongoHTTPRequest.response_headers.append(("Access-Control-Allow-Origin","*"))

    except getopt.GetoptError:
        print "error parsing cmd line args."
        usage()
        sys.exit(2)

    MongoHTTPRequest.serve_forever(27080)
if __name__ == "__main__":
    main()


########NEW FILE########
__FILENAME__ = get
from restclient import GET, POST

import json
import unittest

class TestGET(unittest.TestCase):

    def setUp(self):
        POST("http://localhost:27080/_connect", 
            params = {'server' : 'localhost:27017'})
        self._drop_collection()

    def _drop_collection(self):
        str = POST("http://localhost:27080/test/_cmd",
                   params = {'cmd' : '{"drop" : "mongoose"}'})

    def test_hello(self):
        str = GET("http://localhost:27080/_hello")

        self.assertEquals(type(str).__name__, "str")

        obj = json.loads(str)

        self.assertEquals(obj['ok'], 1)
        self.assertEquals(obj['msg'], "Uh, we had a slight weapons "+
                          "malfunction, but uh... everything's perfectly "+
                          "all right now. We're fine. We're all fine here "+
                          "now, thank you. How are you?")

    def test_find(self):
        POST("http://localhost:27080/test/mongoose/_insert",
             params={'docs' : '[{"x" : 1},{"x" : 2},{"x" : 3}]'},
             async = False)

        str = GET("http://localhost:27080/test/mongoose/_find")

        self.assertEquals(type(str).__name__, "str")

        obj = json.loads(str)

        self.assertEquals(obj['ok'], 1, str)
        self.assertEquals(type(obj['id']).__name__, "int", str)
        self.assertEquals(len(obj['results']), 3, str)


    def test_find_sort(self):
        POST("http://localhost:27080/test/mongoose/_insert",
             params={'docs' : '[{"x" : 1},{"x" : 2},{"x" : 3}]'},
             async = False)
        
        str = GET("http://localhost:27080/test/mongoose/_find",
                  {"sort" : '{"x" : -1}'})

        self.assertEquals(type(str).__name__, "str")

        obj = json.loads(str)

        self.assertEquals(obj['results'][0]['x'], 3, str)
        self.assertEquals(obj['results'][1]['x'], 2, str)
        self.assertEquals(obj['results'][2]['x'], 1, str)




if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = post
from restclient import GET, POST

import json
import unittest

class TestPOST(unittest.TestCase):

    def setUp(self):
        POST("http://localhost:27080/_connect")
        self._drop_collection()

    def _drop_collection(self):
        str = POST("http://localhost:27080/test/_cmd",
                   params = {'cmd' : '{"drop" : "mongoose"}'})

    def test_insert_err1(self):
        str = POST("http://localhost:27080/_insert",
                   params = {'docs' : '[{"foo" : "bar"}]'},
                   async = False )

        self.assertEquals(type(str).__name__, "str")

        obj = json.loads(str)

        self.assertEquals(obj['ok'], 0)
        self.assertEquals(obj['errmsg'], 'db and collection must be defined')

    def test_insert_err2(self):
        str = POST("http://localhost:27080/test/_insert",
                   params = {'docs' : '[{"foo" : "bar"}]'},
                   async = False )

        self.assertEquals(type(str).__name__, "str")

        obj = json.loads(str)

        self.assertEquals(obj['ok'], 0)
        self.assertEquals(obj['errmsg'], 'db and collection must be defined')

    def test_insert_err3(self):
        str = POST("http://localhost:27080/test/mongoose/_insert",
                   async = False )

        self.assertEquals(type(str).__name__, "str")

        obj = json.loads(str)

        self.assertEquals(obj['ok'], 0)
        self.assertEquals(obj['errmsg'], 'missing docs')

    def test_insert(self):
        str = POST("http://localhost:27080/test/mongoose/_insert",
                   params = {'docs' : '[{"foo" : "bar"}]'},
                   async = False )

        self.assertEquals(type(str).__name__, "str")

        obj = json.loads(str)

        self.assertEquals(type(obj['oids'][0]['$oid']).__name__, "unicode")

    def test_safe_insert(self):
        str = POST("http://localhost:27080/test/mongoose/_insert",
                   params = {'docs' : '[{"foo" : "bar"}]', 'safe' : 1},
                   async = False )

        self.assertEquals(type(str).__name__, "str")

        obj = json.loads(str)

        self.assertEquals(type(obj['oids'][0]['$oid']).__name__, "unicode")
        self.assertEquals(obj['status']['ok'], 1)
        self.assertEquals(obj['status']['err'], None)

    def test_safe_insert_err1(self):
        str = POST("http://localhost:27080/test/mongoose/_insert",
                   params = {'docs' : '[{"_id" : "bar"}, {"_id" : "bar"}]', 'safe' : 1},
                   async = False )

        self.assertEquals(type(str).__name__, "str")

        obj = json.loads(str)

        self.assertEquals(obj['status']['ok'], 1)
        self.assertEquals(obj['status']['code'], 11000)

    def test_update_err1(self):
        str = POST("http://localhost:27080/_update",
                   async = False )

        self.assertEquals(type(str).__name__, "str")

        obj = json.loads(str)

        self.assertEquals(obj['ok'], 0)
        self.assertEquals(obj['errmsg'], 'db and collection must be defined')

    def test_update_err2(self):
        str = POST("http://localhost:27080/test/_update",
                   async = False )

        self.assertEquals(type(str).__name__, "str")

        obj = json.loads(str)

        self.assertEquals(obj['ok'], 0)
        self.assertEquals(obj['errmsg'], 'db and collection must be defined')

    def test_update_err3(self):
        str = POST("http://localhost:27080/test/mongoose/_update",
                   async = False )

        self.assertEquals(type(str).__name__, "str")

        obj = json.loads(str)

        self.assertEquals(obj['ok'], 0)
        self.assertEquals(obj['errmsg'], 'missing criteria')

    def test_update_err4(self):
        str = POST("http://localhost:27080/test/mongoose/_update",
                   params = {"criteria" : "{}"},
                   async = False )

        self.assertEquals(type(str).__name__, "str")

        obj = json.loads(str)

        self.assertEquals(obj['ok'], 0)
        self.assertEquals(obj['errmsg'], 'missing newobj')

    def test_update(self):
        str = POST("http://localhost:27080/test/mongoose/_update",
                   params = {"criteria" : "{}", "newobj" : '{"$set" : {"x" : 1}}'},
                   async = False )

        self.assertEquals(type(str).__name__, "str")

        obj = json.loads(str)

        self.assertEquals(obj['ok'], 1, str)

    def test_safe(self):
        str = POST("http://localhost:27080/test/mongoose/_update",
                   params = {"criteria" : "{}", "newobj" : '{"$set" : {"x" : 1}}', "safe" : "1"},
                   async = False )

        self.assertEquals(type(str).__name__, "str")

        obj = json.loads(str)

        self.assertEquals(obj['ok'], 1)
        self.assertEquals(obj['n'], 0)
        self.assertEquals(obj['err'], None)

    def test_upsert(self):
        str = POST("http://localhost:27080/test/mongoose/_update",
                   params = {"criteria" : "{}", "newobj" : '{"$set" : {"x" : 1}}', "upsert" : "1", "safe" : "1"},
                   async = False )

        self.assertEquals(type(str).__name__, "str")

        obj = json.loads(str)

        self.assertEquals(obj['ok'], 1, str)
        self.assertEquals(obj['n'], 1, str)

        str = GET("http://localhost:27080/test/mongoose/_find")
        obj = json.loads(str)

        self.assertEquals(obj['ok'], 1, str)
        self.assertEquals(obj['results'][0]['x'], 1, str)

    def test_multi(self):
        POST("http://localhost:27080/test/mongoose/_insert",
             params = {"docs" : '[{"x" : 1},{"x" : 1},{"x" : 1},{"y" : 1}]'},
             async = False )

        str = POST("http://localhost:27080/test/mongoose/_update",
                   params = {"criteria" : '{"x" : 1}', "newobj" : '{"$set" : {"x" : 2}}', "multi" : "1", "safe" : "1"},
                   async = False )

        obj = json.loads(str)

        self.assertEquals(obj['ok'], 1, str)
        self.assertEquals(obj['n'], 3, str)

    def test_remove(self):
        POST("http://localhost:27080/test/mongoose/_insert",
             params = {"docs" : '[{"x" : 1},{"x" : 1},{"x" : 1},{"y" : 1}]'},
             async = False )

        str = POST("http://localhost:27080/test/mongoose/_remove",
                   async = False )

        obj = json.loads(str)

        self.assertEquals(obj['ok'], 1, str)


    def test_remove_safe(self):
        POST("http://localhost:27080/test/mongoose/_insert",
             params = {"docs" : '[{"x" : 1},{"x" : 1},{"x" : 1},{"y" : 1}]'},
             async = False )

        str = POST("http://localhost:27080/test/mongoose/_remove",
                   params = {"criteria" : '{"x" : 1}', "safe" : 1},
                   async = False )

        obj = json.loads(str)

        self.assertEquals(obj['ok'], 1, str)
        self.assertEquals(obj['n'], 3, str)

        str = POST("http://localhost:27080/test/mongoose/_remove",
                   params = {"safe" : "1"},
                   async = False )

        obj = json.loads(str)

        self.assertEquals(obj['ok'], 1, str)
        self.assertEquals(obj['n'], 1, str)


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
