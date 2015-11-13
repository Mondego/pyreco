__FILENAME__ = whirlwind-admin
#!/usr/bin/env python

import whirlwind
import os
import logging
import optparse
from distutils import dir_util

'''
whirlwind-admin.py --version

whirlwind-admin.py --create-application app_name

whirlwind-admin.py --generate-cookie-secret

whirlwind-admin.py --generate-model-indexes
'''

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s %(levelname)s %(message)s')


def main():

    usage = "usage: %prog [options [args]]"
    parser = optparse.OptionParser(usage)

    parser.add_option("--ca", "--create-application",
                    dest="create_app",
                    metavar="FILE",
                    action="store_true",
                    default=False,
                    help="Creates an application structure")

    parser.add_option("--v", "--version", dest="version",
                    action="store_true",
                    default=False,
                    help="Print the version info for this release of WhirlWind")

    parser.add_option("--gcs", "--generate-cookie-secret", dest="generate_cookie_secret",
                    action="store_true",
                    default=False,
                    help="Generate a cookie secret hash")

    parser.add_option("--gmi", "--generate-model-indexes", dest="generate_model_indexes",
                action="store_true",
                default=False,
                help="Generate mongo indexes for your models")

    options, args = parser.parse_args()

    if not options.create_app and not options.version and not options.generate_cookie_secret and not options.generate_model_indexes:
        parser.error('Must choose one -- try --ca or --v or --gcs or --gmi')

    if options.create_app:

        if len(args) != 1:
            logging.error("Error no app name given")
            return

        #generate the template dir path
        template_dir = os.path.join(whirlwind.__path__[0], 'conf', 'app_template')

        #copy the template files
        copied_files = dir_util.copy_tree(template_dir, args[0])

        #check that we copied files
        if len(copied_files) > 0:
            logging.info('Created %s' % options.create_app)
        else:
            logging.info('Error copying app template')

    if options.version:
        logging.info(whirlwind.get_version())

    if options.generate_cookie_secret:
        import base64
        import uuid
        print(base64.b64encode(uuid.uuid4().bytes + uuid.uuid4().bytes))

    if options.generate_model_indexes:

        import sys
        import pkgutil
        from whirlwind.db.mongo import Mongo

        #insert the current dir into the path
        sys.path.insert(0, os.getcwd())

        #grab a settings path from our args if exists or assume relative default
        settings_module = args[0] if len(args) == 1 else 'config.settings'

        conf = __import__(settings_module)

        #connect to our db using our options set in settings.py
        Mongo.create(host=conf.settings.db_host, port=conf.settings.db_port)

        #import our default models package
        __import__('application.models')

        pkg_mods = sys.modules['application.models']

        #setup a prefix string
        prefix = pkg_mods.__name__ + "."

        #import all the modules in the models dir so the registration decorators fire
        for importer, modname, ispkg in pkgutil.iter_modules(pkg_mods.__path__, prefix):
            __import__(modname)

        #loop over the registered documents
        for doc, obj in Mongo.db.connection._registered_documents.iteritems():
            try:

                print 'Attempting to create index for ', doc
                #generate the index for this doc on the collection
                obj.generate_index(Mongo.db.connection[conf.settings.db_name][obj._obj_class.__collection__])
            except Exception, e:
                #barf up an error on fail
                print 'Could not create index for %s - exception: %s' % (doc, e.message)


if __name__ == "__main__":
    main()

########NEW FILE########
__FILENAME__ = chat
'''
Created on Sep 21, 2012

@author: matt

Here is an example of a chat websocket connection 
'''

#from whirlwind.contrib.sockjs.router_connection import connection
#from sockjs.tornado import SockJSConnection

#
#@connection('chat')
#class ChatConnection(SockJSConnection):
#    # Class level variable
#    participants = set()
#
#    def on_open(self, info):
#        self.send("Welcome from the server.")
#        self.participants.add(self)
#
#    def on_message(self, message):
#        # Pong message back
#        for p in self.participants:
#            p.send(message)
#
#    def on_close(self):
#        self.participants.remove(self)
########NEW FILE########
__FILENAME__ = account_controller
from whirlwind.core.request import BaseRequest
from whirlwind.db.mongo import Mongo
from application.models.user import User
import datetime, hashlib
from tornado.web import authenticated
from whirlwind.view.decorators import route

@route('/logout')
class LogoutHandler(BaseRequest):
    def get(self):
        self.session['username'] = None
        self.session.destroy()
        #kill the session.
        self.redirect("/")

@route('/login')
class LoginHandler(BaseRequest):
    def get(self):
        template_values = {}
        template_values['next'] = self.get_argument('next','/')
        
        self.render_template('/account/login.html',**template_values)

    def post(self):
        username = self.get_argument("username",None)
        password = self.get_argument("password",None)
        
        if not username or not password:
            # do something
            self.flash.error = "You must enter a username and password to proceed. Please try again."
            self.redirect("/login")
            return
        
        pw = hashlib.sha1(password).hexdigest()
        username = User.normalize(username)
        user = User.lookup(username)
        
        #check the password.
        if not user or user['password'] != pw:
            # do something
            self.flash.error = "Login not valid"
            self.redirect("/login")
            return
        
        # check if user is suspended.
        if user.is_suspended() :
            self.flash.error = "Sorry the account you specified has been suspended."
            self.redirect("/")
            return
          

        user.history.last_login = datetime.datetime.utcnow()
        Mongo.db.ui.users.update({'_id': username}, {
                                                    '$set' : {'history.last_login': user.history.last_login},
                                                    '$inc' : {'history.num_logins' : 1}
                                                    })        
        #add to the session.
        self.session['username'] = user._id
        #check keep_logged_in
        if self.get_argument("keep_logged_in", False) == "on" :
            self.session['keep_logged_in'] = True
        
        self.set_current_user(user)
        self.flash.notice = "Welcome, %s" % user._id
        forwardUrl = self.get_argument('next','/')
        self.redirect(forwardUrl)

@route('/signup')
class SignupHandler(BaseRequest):
    def get(self):
        template_values = {}
        template_values['next'] = self.get_argument('next','/')
        
        self.render_template('/account/signup.html',**template_values)
    
    def post(self):
        username = self.get_argument("username",None)
        password = self.get_argument("password",None)
        
        if not username or not password:
            # do something
            self.flash.error = "You must enter a username and password to proceed. Please try again."
            self.redirect("/signup")
            return
        
        if password != self.get_argument("password2", None) :
            self.flash.error = "Passwords do not match. Please try again."
            self.redirect("/signup")
            return
        
        user = User.instance(username, password)
        Mongo.db.ui.users.insert(user)
        self.flash.info = "Successfully created your account, please log in."
        self.redirect("/login")
        
class PasswordChanger(BaseRequest):
    @authenticated
    def post(self):
        pw = hashlib.sha1(self.get_argument("password")).hexdigest()
        
        if self.get_current_user()['password'] != pw:
            # do something
            self.flash.error = "Password not valid, please try again"
            self.redirect("/settings")
            return
        
        newPw = self.get_argument('new_pw')
        newPw2 = self.get_argument('new_pw_again')
        if newPw != newPw2 :
            self.flash.error = "Passwords do not match, please try again"
            self.redirect("/settings")
            return
        
        password = hashlib.sha1(newPw).hexdigest()
        Mongo.db.ui.users.update({'_id': self.get_username()}, {
                                                    '$set' : {'password': password}
                                                    })       
        self.flash.success = "Successfully updated password"
        self.redirect('/settings')

########NEW FILE########
__FILENAME__ = site_controller
from whirlwind.core.request import BaseRequest
from whirlwind.db.mongo import Mongo
from tornado.web import authenticated
from whirlwind.view.decorators import route

@route('/')
class IndexHandler(BaseRequest):
    def get(self):
        #template context variables go in here
        template_values = {}
        
        self.render_template('/site/index.html',**template_values)
########NEW FILE########
__FILENAME__ = user
from mongokit import *
import datetime
import hashlib, hmac, base64, re
from whirlwind.db.mongo import Mongo
from tornado import options

'''
normalizes a username or email address
'''
def normalize(username):
    if not username :
        return None
    #allow legal email address
    name = username.strip().lower()
    name = re.sub(r'[^a-z0-9\\.\\@_\\-~#]+', '', name)
    name = re.sub('\\s+', '_',name)
    
    #don't allow $ and . because they screw up the db.
    name = name.replace(".", "")
    name = name.replace("$", "")
    return name;

@Mongo.db.connection.register
class User(Document):
    structure = {
                 '_id':unicode,
                 'email':unicode,
                 'roles':list,
                 'password':unicode,
                 'created_at':datetime.datetime,
                 'history' : {
                              'last_login' : datetime.datetime,
                              'num_logins' : long
                              },
                 'timezone':unicode,
                 'suspended_at':datetime.datetime,
                 }
    use_dot_notation=True
    
    @staticmethod
    def normalize(username):
        return normalize(username)
        
    
    @staticmethod
    def lookup(username):
        return Mongo.db.ui.users.User.find_one({'_id' : normalize(username)})
        
        
    '''
    creates a new user instance. unsaved
    '''
    @staticmethod
    def instance(username, password):
        
        username = normalize(username)
        user = User()
        user.roles = [username]
        user['_id'] = username
        user.password = hashlib.sha1(password).hexdigest()
        user.created_at = datetime.datetime.utcnow()
        user.history = {
                        'num_logins' : 0
                        }
        return user
    
    
    def add_role(self, role):
        if not self.get('roles', False):
            self['roles'] = []
        
        if role in self['roles'] :
            return
        self['roles'].append(role)
        
    def remove_role(self, role):
        if not self.get('roles', False):
            self['roles'] = []
        try :
            while True:
                self['roles'].remove(role)
        except :
            pass
        
    def has_role(self, role):
        if not self.get('roles', False):
            self['roles'] = []
        if isinstance(role, basestring):
            return role in self['roles']
        else:
            for r in role:
                if r in self['roles']:
                    return True
    
    def name(self):
        return self._id
    
    def get_timezone(self):
        tz = self.get('timezone', None)
        if tz :
            return tz
        return 'America/New_York'
                
    def is_suspended(self):
        if self.get('suspended_at', None) == None :
            return False
        return self.suspended_at < datetime.datetime.utcnow()
     

########NEW FILE########
__FILENAME__ = example.settings
#run mode
mode = "development"

#define a port for testing
port = 8888

#set static resources path
static_path = '/path/to/your/python/apps/whirlwind/static'

#define a dir for mako to look for templates - relative to the app directory
template_dir = '/path/to/your/python/apps/whirlwind/templates'

#define a dir for mako to cache compiled templates
mako_modules_dir = '/path/to/your/python/apps/whirlwind/templates/mako_modules'

#define a database host
db_host = 'localhost'

#define the database port
db_port = 27017

cookie_secret = "fillmein"

#should we enable sessions
enable_sessions = True
########NEW FILE########
__FILENAME__ = routes
#import our controller handler classes

#  will choose the FIRST match it comes too
route_list = [
    #(r"/", my_controller.MyHandler ),
]
########NEW FILE########
__FILENAME__ = settings
#grab the current path so we can set some thing automatically
import sys
app_path = sys.path[1]

#the app version. you can use in templates via the Filters.version() helper. 
#good for browser cache busting on js & css 
version = '0.1'

#run mode
mode = "development"

#define a port for testing
port = 8000

#set static resources path
static_path = "%s/static" % app_path

#define a dir for mako to look for templates - relative to the app directory
template_dir = "%s/application/views" % app_path

#define a dir for mako to cache compiled templates
mako_modules_dir = "%s/tmp/mako_modules" % app_path

#define a log file... optionally just use the string 'db' to log it to mongo
log = "%s/tmp/log/application.log" % app_path

#define a database host
db_host = 'localhost'

#define the database port
db_port = 27017

#define the database name
db_name = 'whirlwind'

#uncomment the following if when using redis session middleware

#redis host
#redis_host = 'localhost:11211'

#redis port
#redis_port = 6379

#redis db name
#redis_db = 'whirlwind'

#uncomment the following when using memcache session middleware

#memcache host
#memcache_host = 'localhost'

#you must define a cookie secret. you can use the following to generate one:  whirlwind-admin.py --generate-cookie-secret
cookie_secret = "setthistoyourowncookiesecret"

#cookie domain (set this in case you need to share cookies cross subdomain)
#cookie_domain = '.yourdomain.com'

middleware_classes = [
    "whirlwind.middleware.flash.middleware.FlashMiddleware",
    "whirlwind.middleware.session.middleware.SessionMiddleware",
    #"whirlwind.middleware.session.redis.middleware.SessionMiddleware"
    #"whirlwind.middleware.session.memcache.middleware.SessionMiddleware"
]

########NEW FILE########
__FILENAME__ = main
#!/usr/bin/env python

from whirlwind.core.bootstrap import Bootstrap    
import os

#main app entry point
if __name__ == "__main__":
    Bootstrap.run(os.path.dirname(__file__))
########NEW FILE########
__FILENAME__ = version
#set this to bump the version number output by the version template filter
version = 0

########NEW FILE########
__FILENAME__ = bootstrap
'''
Created on Aug 16, 2012

@author: matt
'''
from whirlwind.core.bootstrap import Bootstrap as WhirlwindBootstrap
import os, logging
# from os import path as op
import tornado.web, tornado.options
from tornado.options import options
from config import options_setup
from whirlwind.db.mongo import Mongo
from whirlwind.contrib.sockjs.router_connection import ConnectionLoader,RouterConnection
from whirlwind.contrib.sockjs.multiplex import MultiplexConnection
from sockjs.tornado import SockJSRouter


class Bootstrap(WhirlwindBootstrap):
	def __init__(self):
		WhirlwindBootstrap.__init__(self)
		self.connection_router = None

	def init_mongo(self):
		#connect to mongo
		Mongo.create(
			host=options.db_host, 
			port=options.db_port
		)
	
	def init_connection_router(self):
		#init our url routes
		connections = ConnectionLoader.load('application.connections')
		
		#setup our multiplexed router connection 
		for conn in connections:
			RouterConnection.__endpoints__[conn[0]] = conn[1]

		# Create multiplexer
		router = MultiplexConnection.get(**RouterConnection.__endpoints__)

		# Register multiplexer
		self.connection_router = SockJSRouter(router, '/echo')


	def main(self,path):
		
		#parse the app config
		tornado.options.parse_config_file(os.path.join(path,'config/settings.py'))
		
		#parse the command line args
		tornado.options.parse_command_line()
		
		#init mongo singleton interface
		self.init_mongo()
		
		#init our standard tornado routes
		url_routes = self.init_routes()
		
		#init our sockjs connection router
		self.init_connection_router()
		
		#add in any app settings 
		app_settings = {
			"static_path": options.static_path,
			"cookie_secret": options.cookie_secret,
			"login_url": options.login_url
		}
		
		# Create application
		self.application = tornado.web.Application(
			self.connection_router.urls + url_routes,
			**app_settings
		)
		
		#set a logger level
		logging.getLogger().setLevel(logging.DEBUG)
		
		#log our start message
		logging.info("Ready and listening")

		#listen on our desired port
		self.application.listen(options.port)

		#start the tornado IO loop
		tornado.ioloop.IOLoop.instance().start()
	
	@staticmethod
	def run(path):
		bootstrap = Bootstrap()
		bootstrap.main(path)

########NEW FILE########
__FILENAME__ = multiplex
from sockjs.tornado import conn, session
from sockjs.tornado.transports import base


class ChannelSession(session.BaseSession):
	def __init__(self, conn, server, base, name):
		super(ChannelSession, self).__init__(conn, server)

		self.base = base
		self.name = name

	def send_message(self, msg, stats=True, binary=False):
		self.base.send('msg,' + self.name + ',' + msg)

	def on_message(self, msg):
		self.conn.on_message(msg)

	def close(self, code=3000, message='Go away!'):
		self.base.send('uns,' + self.name)
		self._close(code, message)

	# Non-API version of the close, without sending the close message
	def _close(self, code=3000, message='Go away!'):
		super(ChannelSession, self).close(code, message)


class DummyHandler(base.BaseTransportMixin):
	name = 'multiplex'

	def __init__(self, conn_info):
		self.conn_info = conn_info

	def get_conn_info(self):
		return self.conn_info


class MultiplexConnection(conn.SockJSConnection):
	channels = dict()

	def on_open(self, info):
		self.endpoints = dict()
		self.handler = DummyHandler(self.session.conn_info)

	def on_message(self, msg):
		parts = msg.split(',', 2)
		op, chan = parts[0], parts[1]

		if chan not in self.channels:
			return

		if chan in self.endpoints:
			session = self.endpoints[chan]

			if op == 'uns':
				del self.endpoints[chan]
				session._close()
			elif op == 'msg':
				session.on_message(parts[2])
		else:
			if op == 'sub':
				session = ChannelSession(self.channels[chan],
										 self.session.server,
										 self,
										 chan)
				session.set_handler(self.handler)
				session.verify_state()

				self.endpoints[chan] = session

	def on_close(self):
		for chan in self.endpoints:
			self.endpoints[chan]._close()

	@classmethod
	def get(cls, **kwargs):
		return type('MultiplexRouter', (MultiplexConnection,), dict(channels=kwargs))

########NEW FILE########
__FILENAME__ = router_connection
'''
Created on Aug 17, 2012
@author: matt
'''
from sockjs.tornado import SockJSRouter, SockJSConnection

class RouterConnection(SockJSConnection):
	__endpoints__ = {}

	def on_open(self, info):
		print 'Router', repr(info)

class ConnectionLoader(object):
	
	@staticmethod
	def load(package_name):
		loader = ConnectionLoader()
		return loader.init_connections(package_name)
		
	def init_connections(self,package_name):
		import pkgutil,sys
		
		package = __import__(package_name)
		controllers_module = sys.modules[package_name]
		
		prefix = controllers_module.__name__ + "."
		
		for importer, modname, ispkg in pkgutil.iter_modules(controllers_module.__path__, prefix):
			module = __import__(modname)
		
		#grab the routes defined via the route decorator
		connections = connection.get_connections()

		return connections

class connection(object):
	_connections = []

	def __init__(self, uri):
		self._uri = uri

	def __call__(self, _connection):
		"""gets called when we class decorate"""
		self._connections.append((self._uri, _connection))
		return _connection

	@classmethod
	def get_connections(self):
		return self._connections
########NEW FILE########
__FILENAME__ = sockjs_base_request
from sockjs.tornado import SockJSConnection
from whirlwind.db.mongo import Mongo
import json


class SockjsBaseRequest(SockJSConnection):

	def __init__(self, session):
		SockJSConnection.__init__(self, session)
		self.db = Mongo.db.ui

	def send_message(self,message):
		if isinstance(message, basestring):
			self.send(message)
		else:
			self.send(json.dumps(message))

########NEW FILE########
__FILENAME__ = bootstrap
import sys,os
from whirlwind.core.log import Log

class Bootstrap():
    def __init__(self):
        self.application = None
        self.init_path()
    
    '''
    make sure the python path is set for this app
    '''
    def init_path(self):
        
        #split the current directory from the parent dirictory path
        parent_dir, dir = os.path.split(sys.path[0])
        
        #insert the parent directory into the front of the pythonpath list
        sys.path.insert(0,parent_dir)
    
    def init_logging(self,log):
        if log == 'db':
            Log.create()
        else:
            Log.create('FILE',log)
    
    def main(self,path):
        #import tornado stuff
        import tornado.web, tornado.httpserver, tornado.ioloop, tornado.options
        from tornado.options import options
        from config import options_setup
        from whirlwind.db.mongo import Mongo
        
        #parse the app config
        tornado.options.parse_config_file(os.path.join(path,'config/settings.py'))
        #parse the command line args
        tornado.options.parse_command_line()
        
        #connect to our db using our options set in settings.py
        Mongo.create(host=options.db_host, port=options.db_port)
        
        #init our url routes
        url_routes = self.init_routes()
        
        #init a logger
        self.init_logging(options.log)
        
        #add in any app settings 
        settings = {
            "static_path": options.static_path,
            "cookie_secret": options.cookie_secret,
            "login_url": options.login_url,
        }
        
        #setup the controller action routes
        self.application = tornado.web.Application(url_routes,**settings)
        
        #instantiate a server instance
        http_server = tornado.httpserver.HTTPServer(self.application)
        
        #bind server to port
        http_server.listen(options.port)
        
        #log our start message
        Log.info("Ready and listening")
        
        #start the server
        tornado.ioloop.IOLoop.instance().start()
    
    def init_routes(self):
        from whirlwind.core.routes import RouteLoader
        return RouteLoader.load('application.controllers')
    
    @staticmethod
    def run(path):
       (Bootstrap()).main(path)

########NEW FILE########
__FILENAME__ = log
import pymongo, datetime, logging, os
from whirlwind.db.mongo import Mongo

'''
Database logger
'''
class Log():
    instance = None
    
    def __init__(self,type='',log_file=''):
        if type == 'FILE' and log_file != '':
            #make sure we have a log directory
            dirname, filename = os.path.split(log_file)
            if not os.path.exists(dirname):
                os.makedirs(dirname)
            
            self.destination = 'FILE'
            self.file_logger = logging.getLogger('whirlwind')
            hdlr = logging.FileHandler(log_file)
            hdlr.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(user)s %(message)s %(extended_info)s'))
            self.file_logger.addHandler(hdlr)
            self.file_logger.setLevel(logging.DEBUG)
        else:
            assert Mongo.db != None, "Logger Exception - you must initialize Mongo first to use DB logging"
            self.destination = 'DB'

    def message(self, type, message, user='', extended_info=''):
        if self.destination == 'DB':    
            log_data = {
                'created':datetime.datetime.utcnow(),
                'message':message,
                'type':type,
                'user':user,
                'extended_info':extended_info
            }
            Mongo.db.ui.log.insert(log_data)
        else:
            if type == 'access':
                type = 'info'
            
            getattr(self.file_logger, type)(message,extra={'user':user,'extended_info':extended_info})
    
    @staticmethod
    def create(type='FILE',log_file=''):
        Log.instance = Log(type,log_file)
        
    @staticmethod
    def access(message, user, extended_info):
        Log.instance.message('access', message, user, extended_info)
        
    @staticmethod
    def info(message, user=''):
        Log.instance.message('info', message, user)
    
    @staticmethod
    def debug(message, user=''):
        Log.instance.message('debug', message, user)
    
    @staticmethod
    def error(message, user=''):
        Log.instance.message('error', message, user)
    
    @staticmethod
    def warning(message, user=''):
        Log.instance.message('warning', message, user)

    @staticmethod
    def critical(message, user=''):
        Log.instance.message('critical', message, user)
########NEW FILE########
__FILENAME__ = multithreading
#from tornado import web
import hashlib
import os, StringIO, pycurl
from tornado.web import *


import sys
import threading
import time
import weakref
from Queue import Queue


from tornado import ioloop
from tornado import stack_context

def threaded(method):
    '''
        Makes a regular controller action threaded.
    '''
    @asynchronous
    def wrapper(self, *args, **kwargs):
        self._is_threaded = True        
        self._auto_finish = False
        action = ThreadedAction(method, self, *args, **kwargs)
        ThreadPool.instance().add_task(action.do_work)
    return wrapper


class ThreadedAction():
    
    def __init__(self, method, controller, *args, **kwargs):
        self._method = method
        self._controller = controller
        self._args = args
        self._kwargs = kwargs
        
    
    def do_work(self):
        try :
            # TODO: handle controllers that return a value. 
            # (think tornado considers that a json response)
            self._method(self._controller, *self._args, **self._kwargs)
            if not self._controller._is_whirlwind_finished :
                self._controller.finish()
        except Exception,e :
            self._controller._handle_request_exception(e)
        
        

'''
    Simple Threadpool implementation.  
    
    
'''
class ThreadPool():
    
    '''
        Pool of threads consuming tasks from a queue
        
        Note: I'm not crazy about the fixed threadpool implementation. 
        TODO: should have a max_threads argument, then we can build up to that as needed and 
        reap unused threads. 
        -dustin
    '''
    def __init__(self, num_threads=10):
        self.tasks = Queue(num_threads)
        for _ in range(num_threads): ThreadPoolWorker(self.tasks)

    '''
        Submits a task to the threadpool
        callback will be called once the task completes.
    '''
    def add_task(self, func, callback=None):
        """Add a task to the queue"""
        self.tasks.put((func, callback))

    def wait_completion(self):
        """Wait for completion of all the tasks in the queue"""
        self.tasks.join()    
    
    '''
        Returns the global threadpool.  Use this in almost all cases.
    '''
    @classmethod
    def instance(cls):
        if not hasattr(cls, "_instance"):
            cls._instance = cls()
        return cls._instance


class ThreadPoolWorker(threading.Thread):
    """Thread executing tasks from a given tasks queue"""
    def __init__(self, tasks):
        threading.Thread.__init__(self)
        self.tasks = tasks
        self.daemon = True
        self.start()
    
    def run(self):
        while True:
            func, callback = self.tasks.get()
            try: func()
            except Exception, e: print e
            if callback :
                callback()
            self.tasks.task_done()        
########NEW FILE########
__FILENAME__ = request
from tornado.web import _unicode
from tornado.web import RequestHandler, HTTPError
from mako.template import Template
from mako.lookup import TemplateLookup
from tornado.options import options
from tornado import escape
import datetime
import re, sys, threading, os, httplib, tornado.web
from urllib import unquote
from whirlwind.middleware import MiddlewareManager
from whirlwind.core.log import Log
from tornado.web import ErrorHandler
from tornado import ioloop
from pymongo import *
from whirlwind.view.filters import Filters
from whirlwind.view.paginator import Paginator
from whirlwind.core import dotdict
from whirlwind.db.mongo import Mongo
import pymongo
from tornado.websocket import WebSocketHandler

class WebSocketBaseRequest(WebSocketHandler):
	
	def __init__(self, application, request):
		WebSocketHandler.__init__(self, application, request)
		self._current_user = None
		self.middleware_manager = MiddlewareManager(self)
		self.db = Mongo.db.ui #@UndefinedVariable
		#run all middleware request hooks
		self.middleware_manager.run_request_hooks()
			
	def get_current_user(self):
		return self._current_user
		
	def set_current_user(self, user):
		self._current_user = user
	
	def is_logged_in(self):
		return self.get_current_user() != None


class BaseRequest(RequestHandler):
	
	__template_exists_cache = {}
	
	def __init__(self, application, request):
		RequestHandler.__init__(self, application, request)
		self._current_user = None
		self.middleware_manager = MiddlewareManager(self)
		self._is_threaded = False
		self._is_whirlwind_finished = False
		self.view = dotdict()
		self.db = Mongo.db.ui #@UndefinedVariable
	
	def template_exists(self, template_name):
		tmp = self.__template_exists_cache.get(template_name, None)
		if tmp != None:
			print "found in cache: " + template_name
			return tmp
		
		lookup = self._get_template_lookup()
		try:
			new_template = lookup.get_template(template_name)
			if new_template :
				self.__template_exists_cache[template_name] = True
				return True
		except Exception as detail:
			print 'run-time error in BaseRequest::template_exists - ', detail
		self.__template_exists_cache[template_name] = False   
		return False
		
		
	def _get_template_lookup(self,extra_imports=None) :
		from whirlwind.view.filters import Cycler
		Cycler.cycle_registry = {}
		
		filter_imports=[
			'from whirlwind.view.filters import Filters, Cycler',
		]
		
		if extra_imports:
			filter_imports.extend(extra_imports)
		
		
		if isinstance(options.template_dir,(list,tuple)):
			directory_paths = options.template_dir
		else:
			directory_paths = [options.template_dir]
			
		return TemplateLookup(
			directories=directory_paths, 
			module_directory=options.mako_modules_dir, 
			output_encoding='utf-8', 
			encoding_errors='replace',
			imports=filter_imports
		)
	
	
	#to support backwards compat
	def render_to_string(self,template_name,**kwargs):
		self.render_to_string(template_name,**kwargs)
	
	#returns the rendered output of a template populated with kwargs
	def render_string(self,template_name,**kwargs):
		lookup = self._get_template_lookup()
		new_template = lookup.get_template(template_name)
		kwargs = self.add_context_vars(**kwargs)
		return new_template.render(**kwargs)
	
	def add_context_vars(self,**kwargs):
		tornado_args = {
			"_": self.locale.translate,
			"current_user": self.get_current_user(),
			"datetime": datetime,
			"escape": escape.xhtml_escape,
			"handler": self,
			"json_encode": escape.json_encode,
			"linkify": escape.linkify,
			"locale": self.locale,
			"request": self.request,
			"reverse_url": self.application.reverse_url,
			"squeeze": escape.squeeze,
			"static_url": self.static_url,
			"url_escape": escape.url_escape,
			"xhtml_escape": escape.xhtml_escape,
			"xsrf_form_html": self.xsrf_form_html
		}
		tornado_args.update(self.ui)

		whirlwind_args = {
			"is_logged_in": self.get_current_user() != None,
			"render_as": self.get_argument("render_as", "html"),
			"dict_get" : Filters.dict_get
		}

		kwargs.update(whirlwind_args)
		kwargs.update(tornado_args)
		kwargs.update(self.view)
		
		return kwargs
	
	def render_template(self,template_name, **kwargs):
		lookup = self._get_template_lookup()
		new_template = lookup.get_template(template_name)

		kwargs = self.add_context_vars(**kwargs)
		
		self.middleware_manager.run_view_hooks(view=kwargs)
		
		self.finish(new_template.render(**kwargs))
	
	def get_nested_argument(self,prefix):
		'''
		get nested form input params as an object: project[name]
		'''
		
		params = self.get_arguments_as_dict()
		param_obj = {}
		
		for key in params.keys():
			if key.startswith(prefix):
				if '[' in key and ']' in key:
					param_obj[key[key.find("[")+1:key.find("]")]] = params[key]
				
		return param_obj
		
	'''
	hook into the end of the request
	'''
	def finish(self, chunk=None):	  
		self._is_whirlwind_finished = True
		#run all middleware response hooks
		self.middleware_manager.run_response_hooks()
		if self._is_threaded :
			
			print "Thread finished.  setting ioloop callback..", str(threading.currentThread())
			self._chunk = chunk
			ioloop.IOLoop.instance().add_callback(self.threaded_finish_callback)
			return
			
		super(BaseRequest, self).finish(chunk)
		
	
	'''
	 this is called by the ioloop when the thread finally returns.
	'''
	def threaded_finish_callback(self):
		print "In the finish callback thread is ", str(threading.currentThread()) 
		super(BaseRequest, self).finish(self._chunk)
		self._chunk = None;
		
	
	
	'''
	hook into the begining of the request here
	'''
	def prepare(self):
		#run all middleware request hooks
		self.middleware_manager.run_request_hooks()
			
	def get_current_user(self):
		return self._current_user
		
	def set_current_user(self, user):
		self._current_user = user		
	
	def is_logged_in(self):
		return self.get_current_user() != None
	
	'''
	gets all the request params as a map. cleans them all up ala get_argument(s)
	'''
	def get_arguments_as_dict(self):
		params = {}
		for key in self.request.arguments:
			values = self.get_arguments(key)
			k = unquote(key)
			if len(values) == 1 :
				params[k] = values[0]
			else :
				params[k] = values
			
		return params
	
	'''
	Same as get_argument but will return a list 
	if no arguments are supplied then a dict of all
	the arguments is returned.
	'''
	def get_arguments(self, name=None,  default=None, strip=True):
		if name is None :
			return self.get_arguments_as_dict()
		
		values = self.request.arguments.get(name, None)
		if values is None:
			return default
		
		retVals = []
		for val in values :
			value = self._cleanup_param(val, strip)
			retVals.append(value)
		return retVals
	
	def get_argument(self, name, default=RequestHandler._ARG_DEFAULT, strip=True):
		value = super(BaseRequest, self).get_argument(name, default, strip)
		if value == default :
			return value
		return unquote(value)
	
	'''
		cleans up any argument
		removes control chars, unescapes, ect
	'''
	def _cleanup_param(self, val, strip=True):
		# Get rid of any weird control chars
		value = re.sub(r"[\x00-\x08\x0e-\x1f]", " ", val)
		value = _unicode(value)
		if strip: value = value.strip()
		return unquote(value)   
	
	def get_username(self):
		if self.get_current_user() :
			return self.get_current_user()['_id']
		return None
		
	
	def write(self,chunk,status=None):
		if status:
			self.set_status(status)
		
		RequestHandler.write(self, chunk)
	
	def get_error_html(self, status_code, **kwargs):
		error_handler = WhirlwindErrorHandler(self.application, self.request, status_code=status_code)
		return error_handler.get_error_html(status_code, **kwargs) 

class WhirlwindErrorHandler(ErrorHandler):
	def get_error_html(self, status_code, **kwargs):
		self.require_setting("static_path")
		if status_code in [404, 500, 503, 403]:
			filename = os.path.join(self.settings['static_path'], 'errors/%d.html' % status_code)
			if os.path.exists(filename):
				f = open(filename, 'r')
				data = f.read()
				f.close()
				return data
		return "<html><title>%(code)d: %(message)s</title>" \
				"<body class='bodyErrorPage'>%(code)d: %(message)s</body></html>" % {
			"code": status_code,
			"message": httplib.responses[status_code],
		}

tornado.web.ErrorHandler = WhirlwindErrorHandler


class RequestHelpers(object):
	'''
	helper function to get chunks of large collections
	
	more efficient approach when paging large collections as long as 
	your using the standard automaticly generated mongo document _id
	
	PLEASE NOTE 
		only supports sorting by _id column
		
	'''
	@staticmethod
	def ranged_list(handler, table_class,select={}):
		max_id = handler.get_argument('max_id',False)
		min_id = handler.get_argument('min_id',False)
		
		if not max_id and not min_id:
			return False
			
		count = handler.get_argument('count',10)
		count = count if count >= 1 else 10
		order_by = handler.get_argument('order_by',None)
		
		sort = None
		
		if order_by:
			order = handler.get_argument('order',None)
			order = pymongo.DESCENDING if order.lower() == 'desc' else pymongo.ASCENDING
			sort = {
				order:'_id'
			}
		
		original_select = select
		if max_id != False:
			select['_id'] = {'$gt' : max_id}
		elif handler.get_argument('min_id',False):
			select['_id'] = {'$lt' : min_id}

		if sort:
			results = table_class.find(select).limit(count).sort(sort)
		else:
			results = table_class.find(select).limit(count)
		
		total = table_class.find(original_select).count()

		return [results,total]

	'''
	helper function to page lists of objects
	
	not as effient as paging by ids but is fine as long as your not paging large collections
	you must use this method if your using non standard document _ids 
	'''
	@staticmethod
	def paged_list(handler,table_class,select=None):
	
		page = handler.get_argument('page',1)
		page = page if page >= 1 else 1
		
		count = handler.get_argument('count',10)
		count = count if count >= 1 else 10
		
		sort = None
		order_by = handler.get_argument('order_by',None)
		
		try:
			if order_by:
				order = handler.get_argument('order',None)
				order = pymongo.DESCENDING if order.lower() == 'desc' else pymongo.ASCENDING
				sort = {
					order:order_by
				}

			if select:
				if sort:
					results = table_class.find(select).skip((page-1)*count).limit(count).sort(sort)
				else:
					results = table_class.find(select).skip((page-1)*count).limit(count)
				
				total = table_class.find(select).count()
			else:
				if sort:
					results = table_class.find().skip((page-1)*count).limit(count).sort(sort)
				else:
					results = table_class.find().skip((page-1)*count).limit(count)
					
				total = table_class.find().count()
	
			return Paginator(results,page,count,total)
	
		except:	
			return Paginator([],page,count,0)
	
	#delete checked list items
	@staticmethod
	def delete_selected(handler,pymongo_collection,feild_name='ids',return_stats=False):
		ids = handler.get_argument(feild_name,[])
		
		if len(ids) == 0: return False
		
		if not return_stats:
			pymongo_collection.remove(
				{'_id':{'$in':ids}
			})
			return True
		else:
			stats = {
				'requested':len(ids),
				'success':0,
				'failed':0
			}
			
			for _id in ids:
				try:
					pymongo_collection.remove({'_id':_id},True)
					stats['success'] += 1
				except Exception, ex:
					stats['failed'] += 1
					Log.error(ex.message)
		
			return stats
########NEW FILE########
__FILENAME__ = routes
class RouteLoader(object):
    
    @staticmethod
    def load(package_name,include_routes_file=True):
        loader = RouteLoader()
        return loader.init_routes(package_name,include_routes_file)
        
    def init_routes(self,package_name,include_routes_file=True):
        import pkgutil,sys
        from whirlwind.view.decorators import route
        
        package = __import__(package_name)
        controllers_module = sys.modules[package_name]
        
        prefix = controllers_module.__name__ + "."
        
        for importer, modname, ispkg in pkgutil.iter_modules(controllers_module.__path__, prefix):
            module = __import__(modname)
        
        #grab the routes defined via the route decorator
        url_routes = route.get_routes()
        
        #add the routes from our route file
        if include_routes_file:
            from config.routes import route_list #@UnresolvedImport
            url_routes.extend(route_list)


        return url_routes
########NEW FILE########
__FILENAME__ = memcache_interface
import memcache
from whirlwind.util.singleton import Singleton

class Memcache(Singleton):
	db = None
	
	def __init__(self):
		self.pool = None
		
	@staticmethod
	def create(**kwargs):
		mc = memcache.Client(kwargs['host'].split(','), debug=0)
		if 'debug' in kwargs:
			print kwargs
			print mc
		
		Memcache.db = mc
		print Memcache.db
		
	@staticmethod
	def get(key):
		if Memcache.db == None:
			return None
		else:
			return Memcache.db.get(key)
		
	@staticmethod
	def set(key,val,timeout=None):
		if Memcache.db == None:
			return False
		else:
			if timeout:
				return Memcache.db.set(key,val,timeout)
			else:
				return Memcache.db.set(key,val)
########NEW FILE########
__FILENAME__ = mongo
from mongokit import Connection
from tornado.options import options
from whirlwind.util.singleton import Singleton

'''
    Singleton mongo connection
'''
class Mongo(Singleton):
    
    db = None
    
    def __init__(self):
        self.connection = None
    
    '''
        register a collection of mongokit model objects
    '''
    def register_models(self,models):
        self.connection.register(models)
    
    '''
        Accessor for ui specific database.
    '''   
    @property
    def ui(self):
        return self.connection[options.db_name]
    
    '''
        Useage:
        from whirlwind.db.mongo import Mongo
        Mongo.create(host='host.com', port='23423', username='mongouser', password='password')
    '''
    @staticmethod
    def create(**kwargs):
        db = Mongo()
        db.connection = Connection(kwargs['host'],kwargs['port'])
        Mongo.db = db
        if 'debug' in kwargs:
            print Mongo.db.connection
       
        
########NEW FILE########
__FILENAME__ = redis_interface
import redis
from whirlwind.util.singleton import Singleton

class Redis(Singleton):
	db = None
	
	def __init__(self):
		pass
	
	@staticmethod
	def create(**kwargs):
		if 'connection_pool' in kwargs and kwargs['connection_pool'] == True:
			r = redis.Redis(
				host=kwargs['host'],
				port=kwargs['port'],
				db=kwargs['db'],
				connection_pool=redis.ConnectionPool()
			)
		else:
			r = redis.Redis(
				host=kwargs['host'],
				port=kwargs['port'],
				db=kwargs['db']
			)
		
		if 'debug' in kwargs:
			print r
		
		Redis.db = r
########NEW FILE########
__FILENAME__ = middleware
from whirlwind.middleware.flash import Flash

class FlashMiddleware():
    def __init__(self,request):
        self.request = request
    
    def request_hook(self):
#        assert hasattr(self.request, 'session'), "FlashMiddleware requires SessionMiddleware to be installed."
        
        #add a flash member to the request object
        self.request.flash = Flash()
    
    def response_hook(self):
        if len(self.request.flash) > 0:
            self.request.session['flash'] = self.request.flash
    
    def view_hook(self,view):
        #check if we have any flash messages set in the session
        if self.request.session.get('flash',False):     
            #add it to our template context args   
            view['flash'] = self.request.session['flash']
            
            #remove the flash from the session
            del self.request.session['flash']
        else:
            #required in case we add flash without redirecting
            if len(self.request.flash):
                view['flash'] = self.request.flash
                

########NEW FILE########
__FILENAME__ = middleware
from whirlwind.middleware.session.memcache import Session
from whirlwind.db.memcache_interface import Memcache
from tornado.options import options

class SessionMiddleware():
    def __init__(self,request):
        if options.memcache_host :
            Memcache.create(host=options.memcache_host)
        else:
            raise Exception('memcache.session.SessionMiddleware memcache settings not defined')
        
        self.request = request
    
    def request_hook(self):
        #add a session member to the request object
        self.request.session = Session(self.request)
    
    def response_hook(self):
        #save the session
        self.request.session.save()
        
        #delete the session from the session
        del self.request.session
    
    def view_hook(self,view):
        #add the session to the view so its accessable in our template
        view['session'] = self.request.session
########NEW FILE########
__FILENAME__ = middleware
from whirlwind.middleware.session import Session

class SessionMiddleware():
    def __init__(self,request):
        self.request = request
    
    def request_hook(self):
        #add a session member to the request object
        self.request.session = Session(self.request)
    
    def response_hook(self):
        #save the session
        self.request.session.save()
        
        #delete the session from the session
        del self.request.session
    
    def view_hook(self,view):
        #add the session to the view so its accessable in our template
        view['session'] = self.request.session
########NEW FILE########
__FILENAME__ = middleware
from whirlwind.middleware.session.redis import Session
from whirlwind.db.redis_interface import Redis
from tornado.options import options

class SessionMiddleware():
    def __init__(self,request):
        if options.redis_host :
            Redis.create(host=options.redis_host, port=options.redis_port, db=options.redis_db, connection_pool=True)
        else:
            raise Exception('redis_session.SessionMiddleware redis settings not defined')
        
        self.request = request
    
    def request_hook(self):
        #add a session member to the request object
        self.request.session = Session(self.request)
    
    def response_hook(self):
        #save the session
        self.request.session.save()
        
        #delete the session from the session
        del self.request.session
    
    def view_hook(self,view):
        #add the session to the view so its accessable in our template
        view['session'] = self.request.session
########NEW FILE########
__FILENAME__ = test
class TestMiddleware():

    def __init__(self, request):
        print "TestMiddleware loaded"

    def request_hook(self):
        print "TestMiddleware.request_hook called"

    def response_hook(self):
        print "TestMiddleware.response_hook called"

    def view_hook(self, view):
        print "TestMiddleware.view_hook called"

########NEW FILE########
__FILENAME__ = singleton
class Singleton(object):
    def __new__(type):
        if not '_the_instance' in type.__dict__:
            type._the_instance = object.__new__(type)
        return type._the_instance

########NEW FILE########
__FILENAME__ = decorators
import urllib
from tornado.web import HTTPError


def role_required(role):
    def wrap(view_func):
        def has_role(self, *args, **kwargs):
            if not self.current_user:
                if self.request.method == "GET":
                    url = self.get_login_url()
                    if "?" not in url:
                        url += "?" + urllib.urlencode(dict(next=self.request.uri))
                    self.redirect(url)
                    return
                raise HTTPError(403)
            else:
                if not self.current_user.has_role(role):
                    self.flash.error = "You do not have permissions to access the requested url"
                    self.redirect('/')
                    return

                return view_func(self, *args, **kwargs)

        return has_role
    return wrap


class route(object):
    """
    taken from http://gist.github.com/616347

    decorates RequestHandlers and builds up a list of routables handlers

    Tech Notes (or "What the *@# is really happening here?")
    --------------------------------------------------------

    Everytime @route('...') is called, we instantiate a new route object which
    saves off the passed in URI.  Then, since it's a decorator, the function is
    passed to the route.__call__ method as an argument.  We save a reference to
    that handler with our uri in our class level routes list then return that
    class to be instantiated as normal.

    Later, we can call the classmethod route.get_routes to return that list of
    tuples which can be handed directly to the tornado.web.Application
    instantiation.

    Example
    -------

    @route('/some/path')
    class SomeRequestHandler(RequestHandler):
        pass

    my_routes = route.get_routes()
    """
    _routes = []

    def __init__(self, uri):
        self._uri = uri

    def __call__(self, _handler):
        """gets called when we class decorate"""
        self._routes.append((self._uri, _handler))
        return _handler

    @classmethod
    def get_routes(self):
        return self._routes

########NEW FILE########
__FILENAME__ = filters
import re
import sys
import json
import locale
from tornado.options import options
from dateutil import tz


class Filters():

    '''
        Checks whether the passed in value is considered useful otherwise will return None

        will return None on the following values:
            None
            ''
            'null'
            'undefined'
            {}
    '''
    @staticmethod
    def val(val):
        if val == None:
            return None
        if val == 'null':
            return None
        if val == 'undefined':
            return None
        if val == 0:
            return val
        if isinstance(val, basestring) and len(val) == 0:
            return None
        if isinstance(val, dict) and len(val) == 0:
            return None
        return val

    @staticmethod
    def version():
        try:
            return options.version
        except:
            return ''

    @staticmethod
    def str(val):
        if not val:
            return ''
        #TODO: sensibly handle:
        # dicts => json
        # dates => pretty
        # numbers => add commas
        return str(val)

    '''
        Checks for various styles of true.
        matches on True, 'true', 'on'
    '''
    @staticmethod
    def is_true(val):
        if not val:
            return False
        if isinstance(val, basestring):
            if val == 'True' or val == 'true' or val == 'on':
                return True
            return False
        if val == True:
            return True
        return False

    @staticmethod
    def strip_html(data):
        if not data:
            return
        p = re.compile(r'<[^<]*?/?>')
        return p.sub('', data)

    @staticmethod
    def long_timestamp(dt_str, tz="America/New_York"):
        utc_dt = Filters._convert_utc_to_local(dt_str, tz)
        if utc_dt:
            return utc_dt.strftime("%A, %d. %B %Y %I:% %p")
        else:
            return dt_str

    @staticmethod
    def short_timestamp(dt_str, tz="America/New_York"):
        tz_dt = Filters._convert_utc_to_local(dt_str, tz)
        return tz_dt.strftime("%m/%d/%Y %I:%M %p")

    @staticmethod
    def short_date(dt_str, tz="America/New_York"):
        tz_dt = Filters._convert_utc_to_local(dt_str, tz)
        return tz_dt.strftime("%m/%d/%Y")

    @staticmethod
    def ellipsis(data, limit, append='...'):
        return (data[:limit] + append) if len(data) > limit else data

    '''
     filter to translate a dict to json
    '''
    @staticmethod
    def to_json(dict):
        return json.dumps(dict, True)

    @staticmethod
    def idize(str):
        return (re.sub(r'[^0-9a-zA-Z]', '_', str)).lower()

    @staticmethod
    def _convert_utc_to_local(utc_dt, timezone):
        try:
            from_zone = tz.gettz('UTC')
            to_zone = tz.gettz(timezone)
            utc_dt = utc_dt.replace(tzinfo=from_zone)
            return utc_dt.astimezone(to_zone)
        except Exception:
            print sys.exc_info()
            return None

    @staticmethod
    def url_pretty(str):
        if not str:
            return

        url = re.sub(r'[^0-9a-zA-Z]', '_', Filters.str(str))
        url = re.sub('_+', '_', url)
        #max 32 chars.
        if len(url) > 32:
            url = url[0:32]
        return url

    @staticmethod
    def add_commas(val, as_data_type='int', the_locale=locale.LC_ALL):
        locale.setlocale(the_locale, "")
        if as_data_type == 'int':
            return locale.format('%d', int(val), True)
        elif as_data_type == 'float':
            return locale.format('%f', float(val), True)
        else:
            return val

    @staticmethod
    def get_time_string(str):
        if str == "N/A":
            return str

        parts = str.split("/")
        isPM = parts[0].find('am') == -1
        if not isPM:
            parts[0] = parts[0].replace("am", "")

        parts[1] = parts[1].replace("c", "")
        if(len(parts[0]) >= 3):
            if(len(parts[0]) == 4):
                parts[0] = parts[0][0:2] + ":" + parts[0][2:]
            else:
                parts[0] = parts[0][:1] + ":" + parts[0][1:]
        if(len(parts[1]) >= 3):
            if(len(parts[1]) == 4):
                parts[1] = parts[1][0:2] + ":" + parts[1][2:]
            else:
                parts[1] = parts[1][:1] + ":" + parts[1][1:]

        if isPM:
            time = parts[0] + "/" + parts[1] + "c"
        else:
            time = parts[0] + "am/" + parts[1] + "c"

        return time

    @staticmethod
    def pluralize(str):
        pl = Pluralizer()
        return pl.plural(str)

    '''
        Does a get on the dict.  will work with dot operator, and not throw an exception
        returns default if the key doesn't work

        will also work to reach into lists via integer keys.

        example:
        {
            'key1' : {
                'subkey' : [{'subsubkey1':9},{}]
            }
        }
        Filters.dict_get('key1.subkey.0.subsubkey1') => 9
    '''
    @staticmethod
    def dict_get(dict, key, default=None):
        #Surround this with try in case key is None or not a string or something
        try:
            keys = key.split(".")
        except:
            return default

        tmp = dict
        for k in keys:
            try:
                tmp = tmp[k]
            except TypeError:
                #Issue may be that we have something like '0'. Try converting to a number
                try:
                    tmp = tmp[int(k)]
                except:
                    #Either couldn't convert or went out of bounds on list
                    return default
            except:
                #Exception other than TypeError probably missing key, so default
                return default
        return tmp


class Pluralizer():
    #
    # (pattern, search, replace) regex english plural rules tuple
    #
    rule_tuple = (
                  ('[ml]ouse$', '([ml])ouse$', '\\1ice'),
                  ('child$', 'child$', 'children'),
                  ('booth$', 'booth$', 'booths'),
                  ('foot$', 'foot$', 'feet'),
                  ('ooth$', 'ooth$', 'eeth'),
                  ('l[eo]af$', 'l([eo])af$', 'l\\1aves'),
                  ('sis$', 'sis$', 'ses'),
                  ('man$', 'man$', 'men'),
                  ('ife$', 'ife$', 'ives'),
                  ('eau$', 'eau$', 'eaux'),
                  ('lf$', 'lf$', 'lves'),
                  ('[sxz]$', '$', 'es'),
                  ('[^aeioudgkprt]h$', '$', 'es'),
                  ('(qu|[^aeiou])y$', 'y$', 'ies'),
                  ('$', '$', 's')
                  )

    def regex_rules(self, rules=rule_tuple):
        for line in rules:
            pattern, search, replace = line
            yield lambda word: re.search(pattern, word) and re.sub(search, replace, word)

    def plural(self, noun):
        for rule in self.regex_rules():
            result = rule(noun)
            if result:
                return result


class Cycler():
    cycle_registry = {}

    @staticmethod
    def uuid():
        import uuid
        return uuid.uuid1()

    @staticmethod
    def cycle(values, name='default'):
        if name in Cycler.cycle_registry:
            try:
                return Cycler.cycle_registry[name].next()
            except StopIteration:
                Cycler.cycle_registry[name] = iter(values)
                return Cycler.cycle_registry[name].next()
        else:
            Cycler.cycle_registry[name] = iter(values)
            return Cycler.cycle_registry[name].next()

########NEW FILE########
__FILENAME__ = paginator
from whirlwind.core.log import Log
from math import ceil


class Paginator(object):

    def __init__(self, collection, page_number=1, limit=20, total=-1):
        self.collection = collection
        self.page_number = int(page_number)
        self.limit = int(limit)
        self.total = int(total)

    @property
    def page(self):
        start = (self.page_number - 1) * self.limit
        end = start + self.limit
        try:
            return self.collection[start:end]
        except Exception as detail:
            Log.warning(detail)
            return []

    @property
    def current_page(self):
        return self.page_number

    @property
    def page_count(self):
        if self.total != -1:
            pages = int(ceil((0.0 + self.total) / self.limit))
            return pages
        else:
            return None

    @property
    def has_previous(self):
        return True if (self.page_number > 1) else False

    @property
    def has_next(self):
        return True if (self.current_page < self.page_count) else False

    @property
    def previous_page(self):
        if self.has_previous:
            return self.page_number - 1

    @property
    def next_page(self):
        if self.has_next:
            return self.page_number + 1

    def previous_page_link(self, request):
        return self.__build_url(self.previous_page, request.full_url())

    def next_page_link(self, request):
        return self.__build_url(self.next_page, request.full_url())

    def __build_url(self, page_num, url):
        import re

        #check if there is a query string
        if url.find('?') != -1:
            if re.search(r'page=\d', url) != None:
                page_str = "page=%d" % page_num
                return re.sub(r'page=\d+', page_str, url)
            else:
                return "%s&page=%d" % (url, page_num)

        else:
            return "%s?page=%d" % (url, page_num)

########NEW FILE########
