__FILENAME__ = config
#!/usr/bin/env python

import copy
import logging

import yaml

log = logging.getLogger(__name__)


class Config(dict):
    """ Configuration dictionary """

    def __init__(self, *args, **kwargs):
        dict.__init__(self, *args, **kwargs)

    def load_file(self, file_name):
        data = yaml.load(open(file_name, 'r'))

        if not isinstance(data, dict):
            raise Exception("config file not parsed correctly")

        deep_merge(self, data)


def deep_merge(orig, other):
    """ Modify orig, overlaying information from other """

    for key, value in other.items():
        if key in orig and isinstance(orig[key], dict) and isinstance(value, dict):
            deep_merge(orig[key], value)
        else:
            orig[key] = value

#
# Singleton Instance
#

config = Config()

########NEW FILE########
__FILENAME__ = handlers
#!/usr/bin/env python

import logging
import httplib
import json
import crypt
import base64
import difflib

from passlib.apache import HtpasswdFile
from tornado import gen
from tornado.web import RequestHandler, HTTPError, asynchronous

from pyjojo.config import config
from pyjojo.scripts import create_collection
from pyjojo.util import route

log = logging.getLogger(__name__)


class BaseHandler(RequestHandler):
    """ Contains helper methods for all request handlers """    

    def prepare(self):
        self.handle_params()
        self.handle_auth()

    def handle_params(self):
        """ automatically parse the json body of the request """
        
        self.params = {}
        content_type = self.request.headers.get("Content-Type", 'application/json')
            
        if (content_type.startswith("application/json")) or (config['force_json']):
            if self.request.body in [None, ""]:
                return

            self.params = json.loads(self.request.body)
        else:
            # we only handle json, and say so
            raise HTTPError(400, "This application only support json, please set the http header Content-Type to application/json")

    def handle_auth(self):
        """ authenticate the user """
        
        # no passwords set, so they're good to go
        if config['passfile'] == None:
            return
        
        # grab the auth header, returning a demand for the auth if needed
        auth_header = self.request.headers.get('Authorization')
        if (auth_header is None) or (not auth_header.startswith('Basic ')):
            self.auth_challenge()
            return
        
        # decode the username and password
        auth_decoded = base64.decodestring(auth_header[6:])
        username, password = auth_decoded.split(':', 2)
                
        if not self.is_user_authenticated(username, password):
            self.auth_challenge()
            return
    
    def is_user_authenticated(self, username, password):
        passfile = HtpasswdFile(config['passfile'])
        
        # is the user in the password file?
        if not username in passfile.users():
            return False
        
        return passfile.check_password(username, password)
    
    def auth_challenge(self):
        """ return the standard basic auth challenge """
        
        self.set_header("WWW-Authenticate", "Basic realm=pyjojo")
        self.set_status(401)
        self.finish()
            
    def write(self, chunk):
        """ if we get a dict, automatically change it to json and set the content-type """

        if isinstance(chunk, dict):
            chunk = json.dumps(chunk)
            self.set_header("Content-Type", "application/json; charset=UTF-8")
        
        super(BaseHandler, self).write(chunk)

    def write_error(self, status_code, **kwargs):
        """ return an exception as an error json dict """

        if kwargs['exc_info'] and hasattr(kwargs['exc_info'][1], 'log_message'):
            message = kwargs['exc_info'][1].log_message
        else:
            # TODO: What should go here?
            message = ''

        self.write({
            'error': {
                'code': status_code,
                'type': httplib.responses[status_code],
                'message': message
            }
        })


@route(r"/script_names/?")
class ScriptNamesCollectionHandler(BaseHandler):
    
    def get(self):
        """ get the requirements for all of the scripts """

        tags = {'tags': [], 'not_tags': [], 'any_tags': []}

        for tag_arg in ['tags', 'not_tags', 'any_tags']:
            try:
                tags[tag_arg] = self.get_arguments(tag_arg)[0].split(',')
                break
            except IndexError:
                continue
       
        self.finish({'script_names': self.settings['scripts'].name(tags)})


@route(r"/scripts/?")
class ScriptCollectionHandler(BaseHandler):
    
    def get(self):
        """ get the requirements for all of the scripts """
       
        tags = {'tags': [], 'not_tags': [], 'any_tags': []}

        for tag_arg in ['tags', 'not_tags', 'any_tags']:
            try:
                tags[tag_arg] = self.get_arguments(tag_arg)[0].split(',')
                break
            except IndexError:
                continue

        self.finish({'scripts': self.settings['scripts'].metadata(tags)})


@route(r"/scripts/([\w\-]+)/?")
class ScriptDetailsHandler(BaseHandler):
    
    def options(self, script_name):
        """ get the requirements for this script """
        
        script = self.get_script(script_name, 'options')
        self.finish({'script': script.metadata()})
    
    @asynchronous
    @gen.engine
    def get(self, script_name):
        """ run the script """
        
        if config['force_json']:
            self.set_header("Content-Type", "application/json; charset=UTF-8")

        script = self.get_script(script_name, 'get')

        if script.output == 'combined':
            retcode, stdout = yield gen.Task(script.execute, self.params)
            self.finish({
                "stdout": stdout,
                "return_values": self.find_return_values(stdout),
                "retcode": retcode
            })
        else:
            retcode, stdout, stderr = yield gen.Task(script.execute, self.params)
            self.finish({
                "stdout": stdout,
                "stderr": stderr,
                "return_values": self.find_return_values(stdout),
                "retcode": retcode
            })
        
    @asynchronous
    @gen.engine
    def delete(self, script_name):
        """ run the script """
                
        if config['force_json']:
            self.set_header("Content-Type", "application/json; charset=UTF-8")

        script = self.get_script(script_name, 'delete')

        if script.output == 'combined':
            retcode, stdout = yield gen.Task(script.execute, self.params)
            self.finish({
                "stdout": stdout,
                "return_values": self.find_return_values(stdout),
                "retcode": retcode
            })
        else:
            retcode, stdout, stderr = yield gen.Task(script.execute, self.params)
            self.finish({
                "stdout": stdout,
                "stderr": stderr,
                "return_values": self.find_return_values(stdout),
                "retcode": retcode
            })
        
    @asynchronous
    @gen.engine
    def put(self, script_name):
        """ run the script """
                
        if config['force_json']:
            self.set_header("Content-Type", "application/json; charset=UTF-8")

        script = self.get_script(script_name, 'put')

        if script.output == 'combined':
            retcode, stdout = yield gen.Task(script.execute, self.params)
            self.finish({
                "stdout": stdout,
                "return_values": self.find_return_values(stdout),
                "retcode": retcode,
            })
        else:
            retcode, stdout, stderr = yield gen.Task(script.execute, self.params)
            self.finish({
                "stdout": stdout,
                "stderr": stderr,
                "return_values": self.find_return_values(stdout),
                "retcode": retcode
            })
        
    @asynchronous
    @gen.engine
    def post(self, script_name):
        """ run the script """
                
        if config['force_json']:
            self.set_header("Content-Type", "application/json; charset=UTF-8")

        script = self.get_script(script_name, 'post')

        if script.output == 'combined':
            retcode, stdout = yield gen.Task(script.execute, self.params)
            self.finish({
                "stdout": stdout,
                "return_values": self.find_return_values(stdout),
                "retcode": retcode
            })
        else:
            retcode, stdout, stderr = yield gen.Task(script.execute, self.params)
            self.finish({
                "stdout": stdout,
                "stderr": stderr,
                "return_values": self.find_return_values(stdout),
                "retcode": retcode
            })
        
    def get_script(self, script_name, http_method):
        script = self.settings['scripts'].get(script_name, None)
        
        if script is None:
            raise HTTPError(404, "Script with name '{0}' not found".format(script_name))

        if http_method == 'options':
            return script

        if script.http_method != http_method:
            raise HTTPError(405, "Wrong HTTP method for script '{0}'. Use '{1}'".format(script_name, script.http_method.upper()))

        return script

    def find_return_values(self, output):
        """ parse output array for return values """

        return_values = {}
        for line in output:
            if line.startswith('jojo_return_value'):
                temp = line.replace("jojo_return_value","").strip()
                key, value = [item.strip() for item in temp.split('=')]
                return_values[key] = value

        return return_values


@route(r"/reload/?")
class ReloadHandler(BaseHandler):
    
    def post(self):
        """ reload the scripts from the script directory """
        self.settings['scripts'] = create_collection(config['directory'])
        self.finish({"status": "ok"})

########NEW FILE########
__FILENAME__ = options
#!/usr/bin/env python

from optparse import OptionParser, IndentedHelpFormatter

from pyjojo.config import config

def command_line_options():
    """ command line configuration """
    
    parser = OptionParser(usage="usage: %prog [options] <htpasswd>")
    
    parser.formatter = PlainHelpFormatter()
    parser.description = """Expose a directory of bash scripts as an API.

Note: This application gives you plenty of bullets to shoot yourself in the 
foot!  Please use the SSL config options, give a password file, and either 
whitelist access to it via a firewall or keep it in a private network.

You can use the apache htpasswd utility to create your htpasswd files.  If
you do, I recommend passing the -d flag, forcing the encryption type pyjojo
recognises."""
    
    parser.add_option('-d', '--debug', action="store_true", dest="debug", default=False,
                      help="Start the application in debugging mode.")
    
    parser.add_option('--dir', action="store", dest="directory", default="/srv/pyjojo",
                      help="Base directory to parse the scripts out of")
    
    parser.add_option('--force-json', action="store_true", dest="force_json", default=False,
                      help="Force the application to treat all incoming requests as 'Content-Type: application/json'")
    
    parser.add_option('-p', '--port', action="store", dest="port", default=3000,
                      help="Set the port to listen to on startup.")
    
    parser.add_option('-a', '--address', action ="store", dest="address", default=None,
                      help="Set the address to listen to on startup. Can be a hostname or an IPv4/v6 address.")
    
    parser.add_option('-c', '--certfile', action="store", dest="certfile", default=None,
                      help="SSL Certificate File")
    
    parser.add_option('-k', '--keyfile', action="store", dest="keyfile", default=None,
                      help="SSL Private Key File")
    
    parser.add_option('-u', '--unix-socket', action="store", dest="unix_socket", default=None,
                      help="Bind pyjojo to a unix domain socket")

    options, args = parser.parse_args()

    # TODO: only do this if they specify the ssl certfile and keyfile
    if len(args) >= 1:
        config['passfile'] = args[0]
    else:
        config['passfile'] = None
        
    config['directory'] = options.directory
    config['force_json'] = options.force_json

    return options


class PlainHelpFormatter(IndentedHelpFormatter): 
    def format_description(self, description):
        if description:
            return description + "\n"
        else:
            return ""

########NEW FILE########
__FILENAME__ = scripts
#!/usr/bin/env python

import logging
import os
import os.path
import re
import subprocess

from tornado import gen
from tornado.process import Subprocess
from tornado.ioloop import IOLoop
import toro

log = logging.getLogger(__name__)


class ScriptCollection(dict):
    """ load the collection of scripts """

    def __init__(self, *args, **kwargs):
        dict.__init__(self, *args, **kwargs)
        
    def metadata(self, tags):
        """ return the metadata for all of the scripts, keyed by name """
        
        output = {}
        
        for key, value in self.items():

            if (tags['tags']) or (tags['not_tags']) or (tags['any_tags']):
                if (set(tags['tags']).issubset(value.tags)) and (tags['tags']):
                    output[key] = value.metadata()
                    continue
                if tags['not_tags']:
                    output[key] = value.metadata()
                    for tag in tags['not_tags']:
                        if (tag in value.tags):
                            output.pop(key,None)
                            break
                for tag in tags['any_tags']:
                    if tag in value.tags:
                        output[key] = value.metadata()
                        break
            else:
                output[key] = value.metadata()
        
        return output

    def name(self, tags):
        """ return a list of just the names of all scripts """

        output = []

        for key, value in self.items():
            if (tags['tags']) or (tags['not_tags']) or (tags['any_tags']):
                if (set(tags['tags']).issubset(value.tags)) and (tags['tags']):
                    output.append(value.name)
                    continue
                if tags['not_tags']:
                    output.append(value.name)
                    for tag in tags['not_tags']:
                        if (tag in value.tags):
                            output.remove(value.name)
                            break
                for tag in tags['any_tags']:
                    if tag in value.tags:
                        output.append(value.name)
                        break
            else:
                output.append(value.name)

        return output


class Script(object):
    """ a single script in the directory """
    
    def __init__(self, filename, name, description, params, filtered_params, tags, http_method, output, needs_lock):
        self.lock = toro.Lock()
        self.filename = filename
        self.name = name
        self.description = description
        self.params = params
        self.filtered_params = filtered_params
        self.tags = tags
        self.http_method = http_method
        self.needs_lock = needs_lock
        self.output = output

    def filter_params(self, params):
        filtered_params = dict(params)
        for k,v in filtered_params.items():
            if k in self.filtered_params:
                filtered_params[k] = 'FILTERED'
        return filtered_params

    @gen.engine
    def execute(self, params, callback):
        log.info("Executing script: {0} with params: {1}".format(self.filename, self.filter_params(params)))
        
        if self.needs_lock:
            with (yield gen.Task(self.lock.aquire)):
                response = yield gen.Task(self.do_execute, params)
        else:
            response = yield gen.Task(self.do_execute, params)

        callback(response)

    @gen.engine
    def do_execute(self, params, callback):
        env = self.create_env(params)
        
        if self.output == 'combined':
            child = Subprocess(
                    self.filename,
                    env=env,
                    stdout=Subprocess.STREAM,
                    stderr=subprocess.STDOUT,
                    io_loop=IOLoop.instance()
                )
        
            retcode, stdout = yield [
                gen.Task(child.set_exit_callback),
                gen.Task(child.stdout.read_until_close)
            ]
            
            callback((child.returncode, stdout.split()))
        else:
            child = Subprocess(
                    self.filename,
                    env=env,
                    stdout=Subprocess.STREAM,
                    stderr=Subprocess.STREAM,
                    io_loop=IOLoop.instance()
                )
        
            retcode, stdout, stderr = yield [
                gen.Task(child.set_exit_callback),
                gen.Task(child.stdout.read_until_close),
                gen.Task(child.stderr.read_until_close)
            ]
            
            callback((child.returncode, stdout.splitlines(), stderr.splitlines()))

    def create_env(self, input):
        output = {}
        
        # add all the parameters as env variables
        for param in self.params:
            name = param['name']
            output[name.upper()] = input.get(name, '')
        
        return output

    def metadata(self):
        return {
            "filename": self.filename,
            "http_method": self.http_method,
            "name": self.name,
            "description": self.description,
            "params": self.params,
            "filtered_params": self.filtered_params,
            "tags": self.tags,
            "output": self.output,
            "lock": self.needs_lock
        }

    def __repr__(self):
        return "<{0} {1}>".format(self.__class__.__name__, self.metadata())

def create_collection(directory):
    """ create the script collection for the directory """
    
    log.info("Getting scripts from directory {0}".format(directory))
    
    collection = ScriptCollection()
    
    for (dirpath, _, filenames) in os.walk(directory):                
        for filename in filenames:
            # grab the file's absolute path, and name
            path = os.path.join(dirpath, filename)
            full_path = os.path.abspath(path)

            # format the name for sanity
            name = path.replace(directory + os.sep, '')
            name = '.'.join(name.split(".")[:-1])
            name = re.sub(r'(\W)+', '_', name)
            
            log.info("Adding script with name: {0} and path: {1}".format(name, full_path))
            script = create_script(name, full_path)
            
            if script is not None:
                collection[name] = script

    return collection


def create_script(script_name, filename):
    """ parse a script, returning a Script object """
    
    # script defaults
    description = None
    params = []
    filtered_params = []
    tags = []
    http_method = 'post'
    output = 'split'
    lock = False
    
    # warn the user if we can't execute this file
    if not os.access(filename, os.X_OK):
        log.error("file with filename {0} is not executable, Ignoring.".format(filename))
        return None
    
    # grab file contents
    with open(filename) as f:
        contents = list(f)
    
    in_block = False
    
    # loop over the contents of the file
    for line in contents:        
        
        # all lines should be bash style comments
        if not line.startswith("#"):
            continue
                
        # we don't need the first comment, or extranious whitespace
        line = line.replace("#", "").strip()
        
        # start of the jojo block
        if not in_block and line.startswith("-- jojo --"):
            in_block = True
            continue
        
        # end of the jojo block, so we'll stop here
        if in_block and line.startswith("-- jojo --"):
            in_block = False
            break
        
        # make sure the line is good
        if not ':' in line:
            continue
        
        # prep work for later
        key, value = [item.strip() for item in line.split(':')]
        
        # description
        if in_block and key == "description":
            description = value
            continue
        
        # http_method
        if in_block and key == "http_method":
            if value.lower() in ['get','post','put','delete']:
                http_method = value.lower()
                continue
            else:
                log.warn("unrecognized http_method type in jojo block: {0}".format(value.lower()))
                continue
        
        # output
        if in_block and key == "output":
            if value.lower() in ['split','combined']:
                output = value.lower()
                continue
            else:
                log.warn("unrecognized output type in jojo block: {0}".format(value.lower()))
                continue
        
        # param
        if in_block and key == "param":
            # handle the optional description
            if "-" in value:
                name, desc = [item.strip() for item in value.split('-')]
                params.append({'name': name, 'description': desc})
                continue
            
            params.append({'name': value})
            continue

        # filtered_params
        if in_block and key == "filtered_params":
            filter_values = [filter_value.strip() for filter_value in value.split(',')]
            if len(filter_values) > 1:
                for filter_value in filter_values:
                    filtered_params.append(filter_value)
                continue

            filtered_params.append(value)
            continue

        # tags
        if in_block and key == "tags":
            tag_values = [tag_value.strip() for tag_value in value.split(',')]
            if len(tag_values) > 1:
                for tag_value in tag_values:
                    tags.append(tag_value)
                continue

            tags.append(value)
            continue
        
        # lock
        if in_block and key == "lock":
            lock = (value == "True")
            continue
        
        log.warn("unrecognized line in jojo block: {0}".format(line))
    
    # if in_bock is true, then we never got an end to the block, which is bad
    if in_block:
        log.error("file with filename {0} is missing an end block, Ignoring".format(filename))
        return None
    
    return Script(filename, script_name, description, params, filtered_params, tags, http_method, output, lock)

########NEW FILE########
__FILENAME__ = server
#!/usr/bin/env python

import logging

from tornado.ioloop import IOLoop

from pyjojo.options import command_line_options
from pyjojo.util import setup_logging, create_application
from pyjojo.servers import http_server, https_server, unix_socket_server

log = logging.getLogger(__name__)

def main():
    """ entry point for the application """

    # get the command line options
    options = command_line_options()
    setup_logging()

    # setup the application
    log.info("Setting up the application")
    application = create_application(options.debug)

    # warn about --force-json
    if options.force_json:
        log.warn("Application started with '--force-json' option.  All calls will be treated as if they passed the 'Content-Type: application/json' header.  This may cause unexpected behavior.")

    # server startup
    if options.unix_socket:
        unix_socket_server(application, options)
    elif options.certfile and options.keyfile:
        https_server(application, options)
    else:
        http_server(application, options)

    # start the ioloop
    log.info("Starting the IOLoop")
    IOLoop.instance().start()

########NEW FILE########
__FILENAME__ = servers
#!/usr/bin/env python

import logging
import sys

from tornado.httpserver import HTTPServer
from tornado.netutil import bind_unix_socket

log = logging.getLogger(__name__)

def https_server(application, options):
    """ https server """

    log.info("Binding application to unix socket {0}".format(options.unix_socket))
    if sys.version_info < (2,7,0):
        server = HTTPServer(application, ssl_options={
            "certfile": options.certfile,
            "keyfile": options.keyfile
        })
    else:
        server = HTTPServer(application, ssl_options={
            "certfile": options.certfile,
            "keyfile": options.keyfile,
            "ciphers": "HIGH,MEDIUM"
        })
    server.bind(options.port, options.address)
    server.start()

def http_server(application, options):
    """ http server """

    log.warn("Application is running in HTTP mode, this is insecure.  Pass in the --certfile and --keyfile to use SSL.")
    server = HTTPServer(application)
    server.bind(options.port, options.address)
    server.start()

def unix_socket_server(application, options):
    """ unix socket server """

    log.info("Binding application to unix socket {0}".format(options.unix_socket))
    server = HTTPServer(application)
    socket = bind_unix_socket(options.unix_socket)
    server.add_socket(socket)

########NEW FILE########
__FILENAME__ = util
#!/usr/bin/env python

import os
import pkgutil
import logging
import sys

import tornado.web

from pyjojo.config import config
from pyjojo.scripts import create_collection

log = logging.getLogger(__name__)


class route(object):
    """
    decorates RequestHandlers and builds up a list of routables handlers
    
    From: https://gist.github.com/616347
    """
    
    _routes = []

    def __init__(self, uri, name=None):
        self._uri = uri
        self.name = name

    def __call__(self, _handler):
        """gets called when we class decorate"""
        
        log.info("Binding {0} to route {1}".format(_handler.__name__, self._uri))        
        name = self.name and self.name or _handler.__name__
        self._routes.append(tornado.web.url(self._uri, _handler, name=name))
        return _handler

    @classmethod
    def get_routes(self):
        return self._routes


def setup_logging():
    """ setup the logging system """
    
    base_log = logging.getLogger()
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s [%(filename)s:%(lineno)d] %(message)s"))
    base_log.addHandler(handler)
    base_log.setLevel(logging.DEBUG)
    return handler

def create_application(debug):
    # import the handler file, this will fill out the route.get_routes() call.
    import pyjojo.handlers

    application = tornado.web.Application(
        route.get_routes(), 
        scripts=create_collection(config['directory']),
        debug=debug
    )
    
    return application

########NEW FILE########
__FILENAME__ = base
#!/usr/bin/env python

import logging

from tornado.httpclient import HTTPClient, AsyncHTTPClient
from tornado.ioloop import IOLoop
from tornado.testing import AsyncHTTPTestCase

from pyjojo.util import create_application
from pyjojo.config import config

log = logging.getLogger(__name__)


class BaseFunctionalTest(AsyncHTTPTestCase):
    """Base class for all functional tests"""

    def get_app(self):
        # create the application
        config['directory'] = 'test/fixtures'
        return create_application(False)
    
    def get_new_ioloop(self): 
        return IOLoop.instance()

########NEW FILE########
