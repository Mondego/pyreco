__FILENAME__ = example
import os, random, logging
from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.ext import db
from google.appengine.ext.webapp import template
from google.appengine.api import urlfetch

class NotAComment(db.Model):
    timestamp = db.DateTimeProperty(auto_now=True)
    bool1 = db.BooleanProperty()
    bool2 = db.BooleanProperty()
    i1 = db.IntegerProperty()
    image1 = db.BlobProperty()


class Comment(db.Model):
    timestamp = db.DateTimeProperty(auto_now=True)
    content = db.StringProperty(multiline=True)
    list1 = db.StringListProperty()
    list2 = db.StringListProperty()
    yeah = db.ReferenceProperty(NotAComment)


class Comments(webapp.RequestHandler):
    def get(self):
        comments = Comment.all()
        path = os.path.join(os.path.dirname(__file__), 'index.html')
        self.response.out.write(template.render(path, {'comments': comments}))

    def post(self):
        yeah_key = "YEAH%d" % random.Random().randint(1,3)
        yeah = NotAComment.get_by_key_name(yeah_key)
        if not yeah:
            yeah = NotAComment(
                key_name=yeah_key, 
                bool1=False, 
                bool2=True, 
                i1=random.Random().randint(0,1234567),
                image1=urlfetch.fetch("http://groups.google.com/group/approcket/icon?v=1&hl=en").content,
            ).put()
            
        Comment(
            content=self.request.get('content'),
            list1=self.request.get_all('list1'),
            list2=self.request.get_all('list2'),
            yeah = yeah,
        ).put()
        
        return self.get()        
    
class Images(webapp.RequestHandler):
    def get(self):
        key_name = self.request.get('key_name')
        yeah = NotAComment.get_by_key_name(key_name)
        self.response.headers['Content-Type'] = 'image/gif'
        self.response.out.write(yeah.image1)
        
application = webapp.WSGIApplication([('/', Comments), ('/images', Images)], debug=True)

def main():
  run_wsgi_app(application)

if __name__ == "__main__":
  main()
########NEW FILE########
__FILENAME__ = common
# Copyright 2009 Kaspars Dancis, Kurt Daal
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


import sys
from datetime import datetime

TYPE_DATETIME = "datetime"
TYPE_TIMESTAMP = "timestamp"
TYPE_BOOL = "bool"
TYPE_LONG = "long"
TYPE_FLOAT = "float"
TYPE_INT = "int"
TYPE_TEXT = "text"
TYPE_KEY = "key"
TYPE_REFERENCE = "ref"
TYPE_STR = "str"
TYPE_EMB_LIST = "emb_list"
TYPE_BLOB = "blob"

DEFAULT_TIMESTAMP_FIELD = "timestamp"
DEFAULT_KEY_FIELD = "k"
DEFAULT_BATCH_SIZE = 100

TYPE = "TYPE"

REPLICATION_SERVICE = "rocket.station.ReplicationService"

KIND = "KIND"

TIMESTAMP_FIELD = "TMSF"
TABLE_NAME = "TBLN"
TABLE_KEY_FIELD = "TBLK"

MODE = "MODE"

SEND_RECEIVE = "SR"
RECEIVE_SEND = "RS"
SEND = "S"
RECEIVE = "R"

RECEIVE_FIELDS = "RF"
RECEIVE_FIELDS_EXCLUDE = "RFE"

SEND_FIELDS = "SF"
SEND_FIELDS_EXCLUDE = "SFE"

EMBEDDED_LIST_FIELDS = "ELF" 

AFTER_SEND = "AFTER_SEND"

IDLE_TIME = "IDLE"


def escape(text):
    
    return text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;').replace("'", '&#39;')



def from_iso(s):
    dt = datetime.strptime(s[:19], "%Y-%m-%dT%H:%M:%S")
    try: dt = dt.replace(microsecond = int(s[20:]))
    except: pass
    return dt

def to_iso(dt):
    return dt.isoformat()



class Log:
    def __init__(self, f):
        self.f = f
        
    def write(self, s):
        sys.stdout.write(s)
        self.f.write(s)        
        
    def flush(self):
        self.f.flush()
########NEW FILE########
__FILENAME__ = config
import sys, os

sys.path.insert(0, os.path.abspath(".."))

from common import *

# See http://code.google.com/p/approcket/wiki/ConfigurationReference for full list of supported options.

# Replication URL - change this to URL corresponding your application
ROCKET_URL = "http://localhost:8080/rocket"

SERVICES = {    
# Define replication services for entities that you want to be replicated here.

# Example:
    "ReplicateNotAComment": {TYPE: REPLICATION_SERVICE, KIND: "NotAComment",},
    "ReplicateComment": {TYPE: REPLICATION_SERVICE, KIND: "Comment", EMBEDDED_LIST_FIELDS: ["list2"]}, 
}

BATCH_SIZE = 150 # number of AppEngine entities to load in a single request, reduce this number if requests are using too much CPU cycles or are timing out

SEND_RETRY_COUNT = 3    # How many times AppRocket will retry sending an update to AppEngine in case of server error (such as AppEngine timeout).
                        # This setting does not impact consistency, since if all retries fail, AppRocket will exit current cycle, sleep for IDLE_TIME and try again infinitely.


# MYSQL DATABASE CONFIGURATION
DATABASE_HOST = "localhost"
DATABASE_NAME = "approcket"
DATABASE_USER = "approcket"
DATABASE_PASSWORD = "approcket"
DATABASE_PORT = 3306
DATABASE_ENGINE = "InnoDB"

#LOGGING CONFIGURATION
import logging
LOG_LEVEL = logging.INFO

# DAEMON CONFIGURATION 
# This provides configuration for running AppRocket replicator (station.py) in daemon mode 
# (using -d command-line switch).
LOGFILE = '/var/log/approcket.log'
PIDFILE = '/var/run/approcket.pid'
GID = 103
UID = 103

# REQUEST TIMEOUT
import socket
socket.setdefaulttimeout(30)

########NEW FILE########
__FILENAME__ = daemon
# Copyright 2009 Kaspars Dancis
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



import sys, os, logging, time
from sys import stdout
from threading import Thread

from common import *

if __name__ == "__main__":
    import_config = "from config import *"

    daemon = False
    in_loop = False
    profile = False
    
    for arg in sys.argv[1:]:
        if arg == "-b": 
            daemon = True         
        elif arg == "-l": 
            in_loop = True
        elif arg == "-p": 
            profile = True
        elif arg.startswith("-c="):
            if arg.endswith(".py"):
                config = arg[3:len(arg)-3]
            else:
                config = arg[3:]
                
            import_config = "from %s import *" % config
        else:
            print "Usage: daemon.py [-b|-l] [-c=config file]"
            print '-b: run in background loop mode (*nix platforms only)'
            print '-l: run in loop mode'
            print '-c: configuration file, by default "config"'
            sys.exit()            

    exec import_config

DEFAULT_IDLE_TIME = 60

class Service(Thread):
    def __init__ (self, name, config):
        Thread.__init__(self)
        self.name = name
        self.config = config
        
        if self.config.has_key(IDLE_TIME):
            self.idle_time = self.config[IDLE_TIME]
        else:
            self.idle_time =  DEFAULT_IDLE_TIME
            
        self.single_run = False
        
    def run(self):
        self.on_start()
        
        try:
            if self.single_run:
                try:
                    self.process()
                except:
                    logging.exception(self.name + " Error:")
            else:
                while True:
                    try:
                        while self.process():
                            pass
                    except:
                        logging.exception(self.name + " Error:")
                    
                    logging.info(self.name + ' Idling for %d seconds' % (self.idle_time))                    
                    time.sleep(self.idle_time)
        finally:
            self.on_stop()              
                
            
    def on_start(self):
        pass
    
    def on_stop(self):
        pass
    
    def process(self):
        logging.fatal(self.name + ' Process method is not implemented')
        return False    



services = []



def run_services(in_loop):
    for service_name in SERVICES.keys():
        config = SERVICES[service_name]
        type = config[TYPE] # TODO: add error handling here        
        i = type.rfind('.')
        service_package = type[:i]
        service_class = type[i+1:]
        exec "from %s import %s" % (service_package, service_class)
        exec "service = %s(service_name, SERVICES[service_name])" % service_class
        
        if not in_loop:
            service.single_run = True
            
        services.append(service)
        
        service.start()



def main():
    sys.stdout = sys.stderr = o = open(DAEMON_LOG, 'a+')
    logging.basicConfig(level=LOG_LEVEL, format='%(asctime)s %(levelname)s %(message)s', stream=o)
    
    os.setegid(GID)     
    os.seteuid(UID)
    
    run_services(True)
    


def start_profiling():
    import cherrypy 
    import dowser
    
    cherrypy.tree.mount(dowser.Root())
    
    cherrypy.config.update({
        'environment': 'embedded',
        'server.socket_host': '0.0.0.0',
        'server.socket_port': 8484,
    })
    
    cherrypy.engine.start()


if __name__ == "__main__":
    if daemon:
        try:
            pid = os.fork()
            if pid > 0:
                # exit first parent
                sys.exit(0)
        except OSError, e:
            logging.error("Daemon Error: Fork #1 failed: %d (%s)" % (e.errno, e.strerror))
            sys.exit(1)
    
        # decouple from parent environment
        os.chdir("/")   #don't prevent unmounting....
        os.setsid()
        os.umask(0)
    
        # do second fork
        try:
            pid = os.fork()
            if pid > 0:
                logging.info("Daemon PID %d" % pid)
                open(DAEMON_PID,'w').write("%d"%pid)
                sys.exit(0)
        except OSError, e:
            logging.error("Daemon Error: Fork #2 failed: %d (%s)" % (e.errno, e.strerror))
            sys.exit(1)
            
        if profile:
            start_profiling()
    
        # start the daemon main loop
        main()
    else:
        logging.basicConfig(level=LOG_LEVEL, format='%(asctime)s %(levelname)s %(message)s', stream=stdout)

        if profile:
            start_profiling()

        run_services(in_loop)

########NEW FILE########
__FILENAME__ = key
SECRET_KEY = "change_this"
########NEW FILE########
__FILENAME__ = rocket
# Copyright 2009 Kaspars Dancis, Kurt Daal
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



import logging, base64

from google.appengine.api import datastore, datastore_types, datastore_errors

from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app

from rocket.key import SECRET_KEY

from rocket.common import *

CHANGE_THIS = "change_this"



class Rocket(webapp.RequestHandler):
    
    def unauthorized(self, error = None):
        self.error(403)
        if error:
            logging.error(u"Unauthorized: %s" % error)
            self.response.out.write(u'<error>Unauthorized: %s</error>\n' % error)
        else:
            logging.error(u"Unauthorized")
    
    
    
    def bad_request(self, error):    
        self.error(400)
        logging.error(u"Bad Request: %s" % error)
        self.response.out.write(u'<error>%s</error>\n' % error)



    def not_found(self, error):    
        self.error(404)
        logging.error(u"Not Found: %s" % error)
        self.response.out.write(u'<error>%s</error>\n' % error)
        
        
        
    def server_error(self, error, exception=None):
        self.error(500)
        
        if exception != None:            
            logging.exception(u"Server Error: %s" % error)            
            self.response.out.write(u'<error>Server Error: %s\n%s</error>\n' % (error, exception))
        else:
            logging.error(u"Server Error: %s" % error)
            self.response.out.write(u'<error>Server Error: %s</error>\n' % error)            
        
        
        
    def get(self):    
        path = self.request.path.split("/")
                
        self.response.headers['Content-Type'] = 'text/xml'

        if SECRET_KEY == CHANGE_THIS:
            return self.unauthorized("Please change the default secret key in key.py")
        
        if self.request.get("secret_key") !=  SECRET_KEY:
            return self.unauthorized() 
            
        if len(path) < 3 or path[2] == '': 
            return self.bad_request("Please specify an entity kind")
        
        kind = path[2]
    
        self.response.out.write(u'<?xml version="1.0" encoding="UTF-8"?>\n')    
        self.response.out.write(u'<updates>\n')
        
        query = datastore.Query(kind)
        
        timestamp_field = self.request.get("timestamp")
        if not timestamp_field:
            timestamp_field = DEFAULT_TIMESTAMP_FIELD        
       
        batch_size = self.request.get("count")
        if not batch_size:
            batch_size = DEFAULT_BATCH_SIZE
        else:
            batch_size = int(batch_size)
            
        f = self.request.get("from") 
        if f: 
            query['%s >' % timestamp_field] = from_iso(f)
    
        query.Order(timestamp_field)
            
        entities = query.Get(batch_size, 0)
        
        for entity in entities:
            self.response.out.write(u'    <%s key="%s">\n' % (kind, ae_to_rocket(TYPE_KEY, entity.key())))
            
            for field, value in entity.items():
                if isinstance(value, list):
                    if len(value) > 0 and value[0] != None:
                        field_type = get_type(value[0])
                        self.response.out.write(u'        <%s type="%s" list="true">\n' % (field, field_type))
                        for item in value:
                            self.response.out.write(u"            <item>%s</item>\n" % ae_to_rocket(field_type, item))                    
                        self.response.out.write(u'</%s>\n' % field)
                else:
                    if value != None:  
                        if field == timestamp_field:
                            field_type = TYPE_TIMESTAMP
                        else:
                            field_type = get_type(value)
                        
                        self.response.out.write(u'        <%s type="%s">%s</%s>\n' % (field, field_type, ae_to_rocket(field_type, value), field))                
    
            self.response.out.write(u'    </%s>\n' % kind)
                
        self.response.out.write(u'</updates>')
        
        
    def post(self):
        path = self.request.path.split("/")
        
        self.response.headers['Content-Type'] = 'text/plain'

        if SECRET_KEY == CHANGE_THIS:
            return self.unauthorized("Please change the default secret key in key.py")        
        
        if self.request.get("secret_key") !=  SECRET_KEY:
            return self.unauthorized()
        
        if len(path) < 3 or path[2] == '': 
            return self.bad_request(u'Please specify an entity kind\n')
        
        kind = path[2]
        
        entity = None
        clear_cache = False
        
        key_name_or_id = self.request.get(TYPE_KEY)
        if key_name_or_id:
            if key_name_or_id[0] in "0123456789":
                key = datastore.Key.from_path(kind, int(key_name_or_id)) # KEY ID
            else:
                key = datastore.Key.from_path(kind, key_name_or_id) # KEY NAME
                
            try: entity = datastore.Get(key)
            except datastore_errors.EntityNotFoundError: pass
            
        if not entity:
            if key_name_or_id:
                
                if key_name_or_id[0] in "0123456789":
                    return self.not_found(u'Entity with AppEngine ID=%s is not found.\n' % key_name_or_id)
                    
                entity = datastore.Entity(kind=kind,name=key_name_or_id)
            else:
                entity = datastore.Entity(kind=kind)
        else:
            clear_cache = True
                
        args = self.request.arguments()
        for arg in args:
            if arg != TYPE_KEY:                
                bar = arg.find('|')
                if bar > 0:
                    field_type = arg[:bar]
                    field_name = arg[bar + 1:]
                    value = self.request.get(arg)                    
                    if field_type.startswith("*"):
                        field_type = field_type[1:]
                        if len(value) == 0:
                            if entity.has_key(field_name):
                                del entity[field_name]
                        else:
                            entity[field_name] = map(lambda v: rocket_to_ae(field_type, v), value.split('|'))
                    else:
                        entity[field_name] = rocket_to_ae(field_type, value)
                            
        datastore.Put(entity)
        
        after_send = self.request.get("after_send")
        if after_send:
            try:
                i = after_send.rfind('.')
                if i <= 0:
                    raise Exception("No module specified")                                
                p = after_send[:i]
                m = after_send[i+1:]
                exec "from %s import %s as after_send_method" % (p, m) in locals()
                exec "after_send_method(entity)" in locals()
            except Exception, e:                
                return self.server_error("Error invoking AFTER_SEND event handler (%s)" % after_send,e)
        
        self.response.out.write(u'<ok/>')




def get_type(value):
    if isinstance(value, datetime):
        return TYPE_DATETIME
    elif isinstance(value, bool):
        return TYPE_BOOL
    elif isinstance(value, long):
        return TYPE_LONG
    elif isinstance(value, float):
        return TYPE_FLOAT
    elif isinstance(value, int):
        return TYPE_INT
    elif isinstance(value, datastore_types.Text):
        return TYPE_TEXT
    elif isinstance(value, datastore_types.Key):
        return TYPE_REFERENCE
    elif isinstance(value, datastore_types.Blob):
        return TYPE_BLOB
    else:
        return TYPE_STR
                
    return None



def ae_to_rocket(field_type, ae_value):
    if ae_value == None:
        rocket_value = ""
    elif field_type == TYPE_DATETIME or field_type == TYPE_TIMESTAMP:
        rocket_value = to_iso(ae_value)
    elif field_type == TYPE_REFERENCE:
        rocket_value = "%s/%s" % (ae_value.kind(), ae_to_rocket(TYPE_KEY, ae_value))
    elif field_type == TYPE_KEY:
        if ae_value.name():
            rocket_value = escape(ae_value.name())
        else:
            rocket_value = "%d" % ae_value.id()
    elif field_type == TYPE_BOOL:
        rocket_value = "%d" % ae_value
    elif field_type == TYPE_BLOB:
        rocket_value = base64.b64encode(ae_value)
    else:
        rocket_value = escape(u"%s" % ae_value)
        
    return rocket_value



def rocket_to_ae(field_type, rocket_value):
    if not rocket_value:
        ae_value = None
    elif field_type == TYPE_DATETIME or field_type == TYPE_TIMESTAMP:
        ae_value = from_iso(rocket_value)
    elif field_type == TYPE_BOOL:
        ae_value = bool(int(rocket_value))
    elif field_type == TYPE_LONG:
        ae_value = long(rocket_value)
    elif field_type == TYPE_FLOAT:
        ae_value = float(rocket_value)
    elif field_type == TYPE_INT:
        ae_value = int(rocket_value)
    elif field_type == TYPE_TEXT:
        ae_value = datastore_types.Text(rocket_value.replace('&#124;','|'))
    elif field_type == TYPE_REFERENCE:
        slash = rocket_value.find("/")
        if slash > 0:
            kind = rocket_value[:slash]
            key_name_or_id = rocket_value[slash + 1:]        
            if key_name_or_id[0] in "0123456789":
                key_name_or_id = int(key_name_or_id)
            ae_value = datastore.Key.from_path(kind, key_name_or_id)  
        else:
            logging.error("invalid reference value: %s" % rocket_value)
            ae_value = None
    elif field_type == TYPE_BLOB:
        ae_value = datastore_types.Blob(base64.b64decode(rocket_value))
    else: #str
        ae_value = (u"%s" % rocket_value).replace('&#124;','|')
    
    return ae_value
                                                                
             

application = webapp.WSGIApplication([('/rocket/.*', Rocket)], debug=True)

def main():
  run_wsgi_app(application)

if __name__ == "__main__":
  main()
########NEW FILE########
__FILENAME__ = station
# Copyright 2009 Kaspars Dancis, Kurt Daal
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



import urllib, logging,base64
from datetime import timedelta
from xml.etree import ElementTree
from xml.parsers.expat import ExpatError

import MySQLdb as db

from daemon import Service
from common import *
from key import SECRET_KEY


import_config = "from config import *"

for arg in sys.argv[1:]:
    if arg.startswith("-c="):
        if arg.endswith(".py"):
            config = arg[3:len(arg)-3]
        else:
            config = arg[3:]
            
        import_config = "from %s import *" % config

exec import_config



class Table:
    def __init__(self, name, timestamp_field, key_field):
        self.name = name
        self.timestamp_field = timestamp_field
        self.key_field = key_field        

        self.fields = {}
        self.fields[key_field] = TYPE_KEY
        self.fields[timestamp_field] = TYPE_TIMESTAMP
        
        self.list_fields = {}
        


class ReplicationService(Service):
    def on_start(self):
        self.can_process = False
        
        if self.config.has_key(KIND): self.kind = self.config[KIND]
        else:
            logging.error("Replication service is not configured properly - KIND parameter missing %s" % self.config)
            return            
         
        if self.config.has_key(TABLE_NAME): self.table_name = self.config[TABLE_NAME] 
        else: self.table_name = self.kind.lower()
    
        if self.config.has_key(TIMESTAMP_FIELD): self.timestamp_field = self.config[TIMESTAMP_FIELD] 
        else: self.timestamp_field = DEFAULT_TIMESTAMP_FIELD
    
        if self.config.has_key(TABLE_KEY_FIELD): self.table_key_field = self.config[TABLE_KEY_FIELD] 
        else: self.table_key_field = DEFAULT_KEY_FIELD
    
        if self.config.has_key(TABLE_KEY_FIELD): self.table_key_field = self.config[TABLE_KEY_FIELD] 
        else: self.table_key_field = DEFAULT_KEY_FIELD
    
        if self.config.has_key(SEND_FIELDS): self.send_fields = set(self.config[SEND_FIELDS])
        else: self.send_fields = None

        if self.config.has_key(SEND_FIELDS_EXCLUDE): self.send_fields_exclude = set(self.config[SEND_FIELDS_EXCLUDE])
        else: self.send_fields_exclude = set()
        
        if self.config.has_key(RECEIVE_FIELDS): self.receive_fields = set(self.config[RECEIVE_FIELDS])
        else: self.receive_fields = None

        if self.config.has_key(RECEIVE_FIELDS_EXCLUDE): self.receive_fields_exclude = set(self.config[RECEIVE_FIELDS_EXCLUDE])
        else: self.receive_fields_exclude = set()
    
        if self.config.has_key(EMBEDDED_LIST_FIELDS): self.embedded_list_fields = set(self.config[EMBEDDED_LIST_FIELDS])
        else: self.embedded_list_fields = []

        if self.config.has_key(AFTER_SEND): self.after_send = self.config[AFTER_SEND]
        else: self.after_send = None
    
        if self.config.has_key(MODE): self.mode = self.config[MODE] 
        else: self.mode = SEND_RECEIVE      
        
        kwargs = {
            'charset': 'utf8',
            'use_unicode': True,            
        }
        
        if DATABASE_USER:
            kwargs['user'] = DATABASE_USER
        if DATABASE_NAME:
            kwargs['db'] = DATABASE_NAME
        if DATABASE_PASSWORD:
            kwargs['passwd'] = DATABASE_PASSWORD
        if DATABASE_HOST.startswith('/'):
            kwargs['unix_socket'] = DATABASE_HOST
        elif DATABASE_HOST:
            kwargs['host'] = DATABASE_HOST
        if DATABASE_PORT:
            kwargs['port'] = int(DATABASE_PORT)
        
        self.con = db.connect(**kwargs)
                
        cur = self.con.cursor()
        
        try:            
            # retrieve table metadata if available
            
            cur.execute('SHOW tables LIKE "%s"' % self.table_name)
            if cur.fetchone():
                # table exist
                
                # start with empty definition
                self.table = Table(self.table_name, self.timestamp_field, self.table_key_field)
                
                # add table fields
                cur.execute('SHOW COLUMNS FROM %s' % self.table_name)
                for col in cur.fetchall():
                    field_name = col[0]
                    if field_name in self.embedded_list_fields:
                        self.table.fields[field_name] = TYPE_EMB_LIST
                    else:
                        field_type = self.normalize_type(field_name, col[1])
                        self.table.fields[field_name] = field_type
                    
                # add list fields stored in separate self.tables (TableName_ListField)
                cur.execute('SHOW tables LIKE "%s_%%"' % self.table_name)
                for row in cur.fetchall():
                    list_table_name = row[0]
                    list_field_name = list_table_name[len(self.table_name) + 1:]
                    cur.execute('SHOW COLUMNS FROM %s' % list_table_name)
                    for col in cur.fetchall():
                        field_name = col[0]
                        if field_name == list_field_name:
                            field_type = self.normalize_type(field_name, col[1])
                            self.table.list_fields[field_name] = field_type
                            break                
                
            else:
                # self.tables is missing
                cur.execute(
                    "CREATE TABLE %s (%s VARCHAR(255) NOT NULL, %s TIMESTAMP, PRIMARY KEY(%s), INDEX %s(%s)) ENGINE = %s CHARACTER SET utf8 COLLATE utf8_general_ci" % (
                        self.table_name, 
                        self.table_key_field, 
                        self.timestamp_field, 
                        self.table_key_field, 
                        self.timestamp_field, 
                        self.timestamp_field, 
                        DATABASE_ENGINE,
                    ))
                
                self.table = Table(self.table_name, self.timestamp_field, self.table_key_field)
                
            # reading existing replication state if available        

            cur.execute('show tables like "rocket_station"')
            
            self.send_state = None
            self.receive_state = None
            
            if cur.fetchone():
                cur.execute("select send_state, receive_state from rocket_station where kind = '%s'" % self.kind)
                row = cur.fetchone() 
                if row:
                    self.send_state = row[0]
                    self.receive_state = row[1]
            else:
                cur.execute("CREATE TABLE rocket_station (kind VARCHAR(255), send_state VARCHAR(500), receive_state VARCHAR(500), PRIMARY KEY (kind)) ENGINE = %s CHARACTER SET utf8 COLLATE utf8_general_ci" % DATABASE_ENGINE)                
            
            self.con.commit()
                        
        finally:        
            cur.close() 
                        
        self.can_process = True       
        
        
    def on_stop(self):
        self.con.close()  
        
        
    def process(self):
        if not self.can_process:
            return False
        
        updates = False
           
        if self.mode == SEND_RECEIVE or self.mode == SEND:     
            if self.send_updates(
                self.kind, 
                self.table_name, 
                self.timestamp_field, 
                self.table_key_field, 
                self.send_fields, 
                self.send_fields_exclude, 
                self.embedded_list_fields
                ):
                updates = True
            
        if self.mode == RECEIVE_SEND or self.mode == SEND_RECEIVE or self.mode == RECEIVE:     
            if self.receive_updates(
                self.kind, 
                self.table_name, 
                self.timestamp_field, 
                self.table_key_field, 
                self.receive_fields, 
                self.receive_fields_exclude, 
                self.embedded_list_fields
                ):
                updates = True
    
        if self.mode == RECEIVE_SEND:     
            if self.send_updates(
                self.kind, 
                self.table_name, 
                self.timestamp_field, 
                self.table_key_field, 
                self.send_fields, 
                self.send_fields_exclude, 
                self.embedded_list_fields
                ):
                updates = True
                        
        return updates
    
    
    
    def send_updates(self, kind, table_name, timestamp_field, table_key_field, send_fields, send_fields_exclude, embedded_list_fields):
        cur = self.con.cursor()
        
        table = self.get_table_metadata(cur, table_name, timestamp_field, table_key_field, embedded_list_fields)        
        
        if not table.fields.has_key(timestamp_field):
            logging.error(self.name + ' Error: table %s is missing timestamp field "%s"' % (table_name, timestamp_field))
            return
    
        if not table.fields.has_key(table_key_field):
            logging.error(self.name + ' Error: table %s is missing key field "%s"' % (table_name, table_key_field))
            return
        
        cur.execute("select current_timestamp")
        to_timestamp = cur.fetchone()[0] - timedelta(seconds=1) # -1 second to ensure there will be no more updates with that timestamp    
        params = [to_timestamp]
        
        sql = "select %s from %s where %s < " % (', '.join(["`" + k[0] + "`" for k in table.fields.items()]), table_name, timestamp_field) + """%s """
        
        if self.send_state:
            sql += "and " + timestamp_field + """ > %s """
            params.append(from_iso(self.send_state))
            logging.info(self.name + " Send %s: from %s" % (kind, self.send_state))
        else:
            logging.info(self.name + " Send %s: from beginning" % (kind))
                        
        sql += "order by %s " % timestamp_field                
        
        offset = 0
        count = BATCH_SIZE
        while count == BATCH_SIZE:
            count = 0
            batch_sql = sql + " limit %d, %d" % (offset, BATCH_SIZE)
            cur.execute(batch_sql, params)
            intermediate_timestamp = None
            for row in cur.fetchall():                
                count += 1
                
                key = None
                
                entity = {
                }
                
                i = 0
                for field_name, field_type in table.fields.items():
                    
                    field_value = row[i]
                    
                    if field_name == timestamp_field and field_value:
                        intermediate_timestamp = field_value - timedelta(seconds=1)
                        # do not send time stamp to avoid send/receive loop
                        # entity["%s|%s" % (field_type, field_name)] = self.mysql_to_rocket(field_type, field_value) # test
                        
                    elif field_name == table_key_field:
                        key = field_value
                        entity[TYPE_KEY] = self.mysql_to_rocket(TYPE_KEY, field_value)
                                              
                    elif field_type == TYPE_EMB_LIST:
                        field_type = TYPE_STR
                        if field_value:
                            if field_value.startswith("integer:"):
                                field_value = field_value[8:]
                                field_type = TYPE_INT
                            value = '|'.join(map(lambda v: self.mysql_to_rocket(TYPE_STR, v), field_value.split('|')))
                        else:
                            value = ''
                        entity["*%s|%s" % (field_type, field_name)] = value                        
                        
                    else:
                        if field_name.endswith("_ref"):
                            field_name = field_name[:len(field_name)-4]
                            
                        if (not send_fields or field_name in send_fields) and (not field_name in send_fields_exclude):
                            entity["%s|%s" % (field_type, field_name)] = self.mysql_to_rocket(field_type, field_value)
                        
                    i += 1
    
    
                if not key:
                    logging.error(self.name + ' Send %s: key field %s is empty' % (kind, table_key_field))
                    continue
                
                # retrieve lists
                for field_name, field_type in table.list_fields.items():
                    if (not send_fields or field_name in send_fields) and (not field_name in send_fields_exclude):
                        cur.execute('select %s from %s_%s where %s = ' % (field_name, table_name, field_name, table_key_field) + """%s""", (key))
                        
                        items = []
                        for item in cur.fetchall():
                            items.append(self.mysql_to_rocket(field_type, item[0]))
                        
                        entity["*%s|%s" % (field_type, field_name)] = '|'.join(items)
                        
                logging.debug(self.name + ' Send %s: key=%s' % (kind, key))
                            
                for attempt in range(SEND_RETRY_COUNT): 
                    if self.send_row(kind, key, entity, attempt + 1):
                        break
                else:
                    logging.error(" Send %s: all %d attempts failed, giving up until next cycle" % (kind, attempt + 1))
                    # if all retries failed - rollback and return
                    self.con.rollback()
                    return                                        
                
            logging.info(self.name + ' Send %s: batch end, count=%d, offset=%d' % (kind, count, offset))
            offset += count        
            
            if intermediate_timestamp:
                intermediate_timestamp = to_iso(intermediate_timestamp)
                self.write_send_state(cur, kind, intermediate_timestamp)            
                self.con.commit()            
                self.send_state = intermediate_timestamp 
    
        to_timestamp = to_iso(to_timestamp)
        self.write_send_state(cur, kind, to_timestamp)            
        self.con.commit()            
        self.send_state = to_timestamp
                            
        cur.close()    
        
        return count > 0 or offset > 0



    def send_row(self, kind, key, entity, attempt):
        #logging.error(entity)
        
        url = "%s/%s?secret_key=%s" % (ROCKET_URL, kind, SECRET_KEY)
        
        if self.after_send:
            url += "&after_send=%s" % self.after_send
            
        try:
            result = urllib.urlopen(url, urllib.urlencode(entity))
            response = ''.join(result).strip(" \r\n")
        except:
            logging.exception(self.name + ' Send %s: key=%s, attempt #%d failed' % (kind, key, attempt + 1))
            return False
        
        try:
            if result.code != 200:
                logging.error(self.name + " Send %s: key=%s, attempt #%d failed, code=%d, URL=%s, response=%s" % (kind, key, attempt, result.code, url, response))
                return False                    
        finally:
            result.close()
            
        return True
    
    

    def receive_updates(self, kind, table_name, timestamp_field, table_key_field, receive_fields, receive_fields_exclude, embedded_list_fields):
        updates = False
                    
        # receive updates
        count = BATCH_SIZE
        while count == BATCH_SIZE:
            count = 0
            
            url = "%s/%s?secret_key=%s&timestamp=%s&count=%d" % (ROCKET_URL, kind, SECRET_KEY, timestamp_field, BATCH_SIZE)
            if self.receive_state:
                url += "&from=%s" % self.receive_state        
                logging.info(self.name + " Receive %s: from %s" % (kind, self.receive_state))
            else:
                logging.info(self.name + " Receive %s: from beginning" % (kind))            
    
            try:
                result = urllib.urlopen(url)
                response = ''.join(result)            
            except:
                logging.exception(self.name + " Receive %s: error retrieving updates, URL=%s" % (kind, url))
                return False

            if result.code != 200:
                logging.error(self.name + " Receive %s: error retrieving updates, code=%d, URL=%s, response=%s" % (kind, result.code, url, response))
                return False            
                
            cur = self.con.cursor()
            
            try:
                
                xml = ElementTree.XML(response)
                for entity in xml:
                    self.receive_row(cur, kind, table_name, timestamp_field, table_key_field, receive_fields, receive_fields_exclude, embedded_list_fields, entity)
                    count += 1
                    last_timestamp = entity.findtext(timestamp_field)
                
                if count > 0:
                    updates = True
                    self.write_receive_state(cur, kind, last_timestamp)            
                    self.con.commit()            
                    self.receive_state = last_timestamp    
            
            except ExpatError, e:
                logging.exception(self.name + " Receive %s: error parsing response: %s, response:\n%s" % (kind, e, response))
                self.con.rollback()
                
            except:
                logging.exception(self.name + " Receive %s: error" % kind)
                self.con.rollback()
            
            cur.close()
                
            logging.info(self.name + " Receive %s: batch end, count=%d" % (kind, count))                
            
        return updates 



    def receive_row(self, cur, kind, table_name, timestamp_field, table_key_field, receive_fields, receive_fields_exclude, embedded_list_fields, entity):
        fields = []
        values = []
    
        table = self.get_table_metadata(cur, table_name, timestamp_field, table_key_field, embedded_list_fields)
    
        key = self.rocket_to_mysql(TYPE_KEY, entity.attrib[TYPE_KEY]) 
        
        logging.debug(self.name + " Receive %s: key=%s" % (kind, key))
        
        row = None
        
        for field in entity:
            field_name = field.tag 
            
            if (not receive_fields or field_name in receive_fields) and (not field_name in receive_fields_exclude):
                # only receive fields if no receive fields are specified (means ALL will be received
                # or the field is in receive fields list
                
                field_type = field.attrib["type"]
    
                if field_type == TYPE_REFERENCE:
                    field_name += "_ref"            
    
                is_list = field.attrib.has_key("list")
                is_embedded_list = field_name in embedded_list_fields
                self.synchronize_field(cur, table, field_name, field_type, is_list, is_embedded_list)
                
                if is_embedded_list:
                    list_values = []
                    for item in field:
                        list_values.append(item.text)
                    fields.append("`%s`" % field_name)
                    values.append('|'.join(list_values))
                elif is_list:
                    list_table_name = '%s_%s' % (table_name, field_name)
                    sql = 'DELETE FROM ' + list_table_name + ' WHERE ' +  table_key_field + """ = %s"""
                    cur.execute(sql, (key))
                    for item in field:
                        sql = 'INSERT INTO ' + list_table_name + ' (' + table_key_field + ',' + field_name + """) VALUES (%s, %s)"""
                        cur.execute(sql, (key, self.rocket_to_mysql(field_type, item.text))) 
                else:            
                    fields.append("`%s`" % field_name)
                    values.append(self.rocket_to_mysql(field_type, field.text))
                    
        cur.execute("SELECT * FROM " + table_name + " WHERE " + table_key_field + """ = %s""", (key))
        if cur.fetchone():
            # record already exist
            if len(fields) > 0:
                values.append(key)
                sql = 'UPDATE `%s` SET %s WHERE %s = ' % (table_name, ','.join(map(lambda f: f + """=%s""", fields)), table_key_field) + """%s"""
                cur.execute(sql, values)
            
        else:
            fields.append(table_key_field)
            values.append(key)
            sql = 'INSERT INTO `%s` (%s) VALUES (%s)' % (table_name, ','.join(fields), ','.join(map(lambda f: """%s""", fields)))
            cur.execute(sql, values)



    def get_table_metadata(self, cur, table_name, timestamp_field, table_key_field, embedded_list_fields):
        if not self.table:
            cur.execute('SHOW tables LIKE "%s"' % table_name)
            if cur.fetchone():
                # table exist
                
                # start with empty definition
                self.table = Table(table_name, timestamp_field, table_key_field)
                
                # add table fields
                cur.execute('SHOW COLUMNS FROM %s' % table_name)
                for col in cur.fetchall():
                    field_name = col[0]
                    if field_name in embedded_list_fields:
                        table.fields[field_name] = TYPE_EMB_LIST
                    else:
                        field_type = self.normalize_type(field_name, col[1])
                        table.fields[field_name] = field_type
                    
                # add list fields stored in separate self.tables (TableName_ListField)
                cur.execute('SHOW tables LIKE "%s_%%"' % table_name)
                for row in cur.fetchall():
                    list_table_name = row[0]
                    list_field_name = list_table_name[len(table_name) + 1:]
                    cur.execute('SHOW COLUMNS FROM %s' % list_table_name)
                    for col in cur.fetchall():
                        field_name = col[0]
                        if field_name == list_field_name:
                            field_type = self.normalize_type(field_name, col[1])
                            table.list_fields[field_name] = field_type
                            break
                
            else:
                # self.tables is missing
                cur.execute("CREATE TABLE %s (%s VARCHAR(255) NOT NULL, %s TIMESTAMP, PRIMARY KEY(%s), INDEX %s(%s)) ENGINE = %s CHARACTER SET utf8 COLLATE utf8_general_ci" % (table_name, table_key_field, timestamp_field, table_key_field, timestamp_field, timestamp_field, DATABASE_ENGINE))
                
                self.table = Table(table_name, timestamp_field, table_key_field)
                
        return self.table



    def normalize_type(self, field_name, field_type):
        if field_name.endswith("_ref"):
            return TYPE_REFERENCE
        elif field_type.startswith("tinyint(1)"):
            return TYPE_BOOL
        elif field_type.startswith("varchar"):
            return TYPE_STR
        elif field_type.startswith("int") or field_type.startswith("bigint"):
            return TYPE_INT 
        else:
            return field_type

                

    def synchronize_field(self, cur, table, field_name, field_type, is_list, is_embedded_list):
        if is_embedded_list:
            if not table.fields.has_key(field_name):        
                # table doesn't have this field yet - add it
                self.create_field(cur, table.name, table.key_field, field_name, TYPE_EMB_LIST, False)            
                table.fields[field_name] = TYPE_EMB_LIST
        elif is_list:
            if not table.list_fields.has_key(field_name):        
                # table doesn't have this field yet - add it
                self.create_field(cur, table.name, table.key_field, field_name, field_type, is_list)            
                table.list_fields[field_name] = field_type
        else:            
            if not table.fields.has_key(field_name):        
                # table doesn't have this field yet - add it
                self.create_field(cur, table.name, table.key_field, field_name, field_type, is_list)            
                table.fields[field_name] = field_type
    


    def create_field(self, cur, table_name, table_key_field, field_name, field_type, is_list):
        if is_list:
            # this is list field - create a separate table for it
            list_table_name = "%s_%s" % (table_name, field_name)
            cur.execute("CREATE TABLE %s (id BIGINT NOT NULL AUTO_INCREMENT, %s VARCHAR(255) NOT NULL, PRIMARY KEY(id), INDEX k(%s)) ENGINE = %s CHARACTER SET utf8 COLLATE utf8_general_ci" % (list_table_name, table_key_field, table_key_field, DATABASE_ENGINE))
            self.create_field(cur, list_table_name, table_key_field, field_name, field_type, False)        
        else:
            if field_type == TYPE_DATETIME:
                cur.execute("ALTER TABLE %s ADD COLUMN `%s` DATETIME" % (table_name, field_name))
            elif field_type == TYPE_TIMESTAMP:
                cur.execute("ALTER TABLE %s ADD COLUMN `%s` TIMESTAMP NOT NULL, ADD INDEX %s(%s)" % (table_name, field_name, field_name, field_name))
            elif field_type == TYPE_INT:
                cur.execute("ALTER TABLE %s ADD COLUMN `%s` BIGINT" % (table_name, field_name))
            elif field_type == TYPE_LONG:
                cur.execute("ALTER TABLE %s ADD COLUMN `%s` BIGINT" % (table_name, field_name))
            elif field_type == TYPE_FLOAT:
                cur.execute("ALTER TABLE %s ADD COLUMN `%s` FLOAT" % (table_name, field_name))
            elif field_type == TYPE_BOOL:
                cur.execute("ALTER TABLE %s ADD COLUMN `%s` BOOLEAN" % (table_name, field_name))
            elif field_type == TYPE_TEXT or field_type == TYPE_EMB_LIST:
                cur.execute("ALTER TABLE %s ADD COLUMN `%s` TEXT" % (table_name, field_name))
            elif field_type == TYPE_KEY or field_type == TYPE_REFERENCE:
                cur.execute("ALTER TABLE %s ADD COLUMN `%s` VARCHAR(500)" % (table_name, field_name))
            elif field_type == TYPE_BLOB:
                cur.execute("ALTER TABLE %s ADD COLUMN `%s` BLOB" % (table_name, field_name))
            else: # str
                cur.execute("ALTER TABLE %s ADD COLUMN `%s` VARCHAR(500)" % (table_name, field_name))
            


    def mysql_to_rocket(self, field_type, mysql_value):
        if mysql_value == None:
            rocket_value = ""
        elif (field_type == TYPE_DATETIME or field_type == TYPE_TIMESTAMP):
            rocket_value = to_iso(mysql_value)
        elif field_type == TYPE_KEY:
            rocket_value = self.mysql_to_rocket(TYPE_STR, mysql_value)
            if rocket_value[0] in '0123456789': 
                # MYSQL ID
                rocket_value = '_%s' % rocket_value
            elif mysql_value[0] == '_':
                # APPENGINE ID
                rocket_value = rocket_value[1:]
                
        elif field_type == TYPE_REFERENCE:
            slash = mysql_value.find("/")
            if slash > 0:
                kind = mysql_value[:slash]
                key_name_or_id = self.mysql_to_rocket(TYPE_KEY, mysql_value[slash + 1:])
                rocket_value = "%s/%s" % (kind, key_name_or_id)
            else:
                logging.error(self.name + " Error: Invalid reference value: %s" % mysql_value)
                rocket_value = ""           
        elif field_type == TYPE_BLOB:
            rocket_value = base64.b64encode(mysql_value)
        else:
            rocket_value = (u'%s' % mysql_value).replace('|', '&#124;').encode('utf-8')
        
        return rocket_value    
    

        
    def rocket_to_mysql(self, field_type, rocket_value):
        if not rocket_value:
            mysql_value = None
        elif field_type == TYPE_DATETIME or field_type == TYPE_TIMESTAMP:                
            mysql_value = from_iso(rocket_value)
        elif field_type == TYPE_BOOL:
            mysql_value = bool(int(rocket_value))
        elif field_type == TYPE_INT:
            mysql_value = int(rocket_value)
        elif field_type == TYPE_LONG:
            mysql_value = long(rocket_value)
        elif field_type == TYPE_FLOAT:
            mysql_value = float(rocket_value)
        elif field_type == TYPE_KEY:
            if rocket_value[0] in '0123456789':
                # APPENGINE ID 
                mysql_value = u'_%s' % rocket_value
            elif rocket_value[0] == '_':
                # MYSQL ID
                mysql_value = rocket_value[1:]
            else:
                mysql_value = rocket_value
                
        elif field_type == TYPE_REFERENCE:
            slash = rocket_value.find("/")
            if slash > 0:
                kind = rocket_value[:slash]
                key_name_or_id = self.rocket_to_mysql(TYPE_KEY, rocket_value[slash + 1:])
                mysql_value = "%s/%s" % (kind, key_name_or_id)
            else:
                logging.error(self.name + " Error: invalid reference value: %s" % rocket_value)
                mysql_value = None
        elif field_type == TYPE_BLOB:
            mysql_value = base64.b64decode(rocket_value)
        else:
            mysql_value = rocket_value
        
        return mysql_value


    def write_send_state(self, cur, kind, send_state):
        if self.send_state or self.receive_state:
            cur.execute("""UPDATE rocket_station SET send_state =  %s WHERE kind = %s""", (send_state, kind))
        else:
            cur.execute("""INSERT INTO rocket_station (kind, send_state) VALUES (%s, %s)""", (kind, send_state))

            
                        
    def write_receive_state(self, cur, kind, receive_state):
        if self.send_state or self.receive_state:
            cur.execute("""UPDATE rocket_station SET receive_state =  %s WHERE kind = %s""", (receive_state, kind))
        else:
            cur.execute("""INSERT INTO rocket_station (kind, receive_state) VALUES (%s, %s)""", (kind, receive_state))

########NEW FILE########
