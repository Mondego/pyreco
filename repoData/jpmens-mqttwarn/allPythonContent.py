__FILENAME__ = zabbix_mqtt_agent
#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Example "agent" for Zabbix/mqttwarn which publishes two metrics
# every few seconds.

import paho.mqtt.client as paho   # pip install paho-mqtt
import ssl
import time
import sys
from random import randint

__author__    = 'Jan-Piet Mens <jpmens()gmail.com>'
__copyright__ = 'Copyright 2014 Jan-Piet Mens'
__license__   = """Eclipse Public License - v 1.0 (http://www.eclipse.org/legal/epl-v10.html)"""

CLIENT = 'jog09'
HOST_TOPIC = "zabbix/clients/%s" % CLIENT

mqttc = paho.Client(clean_session=True, userdata=None)

def metric(name, value):
    mqttc.publish("zabbix/item/%s/%s" % (CLIENT, name), value)
    mqttc.loop()

mqttc.tls_set('/Users/jpm/tmp/mqtt/root.ca',
    tls_version=ssl.PROTOCOL_TLSv1)

mqttc.tls_insecure_set(True)    # Ensure False in production

# If this client dies, ensure broker publishes our death on our behalf (LWT)
mqttc.will_set(HOST_TOPIC, payload="0", qos=0, retain=True)

# mqttc.username_pw_set('john', 'secret')
mqttc.connect("localhost", 8883, 60)

# Indicate host is up
mqttc.publish(HOST_TOPIC, "1")
rc = 0
while rc == 0:
    try:
        rc = mqttc.loop()

        metric('system.cpu.load', randint(2, 8))
        metric('time.stamp',  time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()))

        time.sleep(10)
    except KeyboardInterrupt:
        sys.exit(0)

########NEW FILE########
__FILENAME__ = mqttwarn
#!/usr/bin/env python
# -*- coding: utf-8 -*-

import paho.mqtt.client as paho   # pip install paho-mqtt
import logging
import signal
import sys
import time
from datetime import datetime
try:
    import json
except ImportError:
    import simplejson as json
import Queue
import threading
import imp
try:
    import hashlib
    md = hashlib.md5
except ImportError:
    import md5
    md = md5.new
import os
import socket
from ConfigParser import RawConfigParser, NoOptionError
import codecs
import ast
import re
HAVE_TLS = True
try:
    import ssl
except ImportError:
    HAVE_TLS = False
HAVE_JINJA = True
try:
    from jinja2 import Environment, FileSystemLoader
    jenv = Environment(
            loader = FileSystemLoader('templates/', encoding='utf-8'),
            trim_blocks = True)
    jenv.filters['jsonify'] = json.dumps
except ImportError:
    HAVE_JINJA = False

__author__    = 'Jan-Piet Mens <jpmens()gmail.com>, Ben Jones <ben.jones12()gmail.com>'
__copyright__ = 'Copyright 2014 Jan-Piet Mens'
__license__   = """Eclipse Public License - v 1.0 (http://www.eclipse.org/legal/epl-v10.html)"""

# script name (without extension) used for config/logfile names
SCRIPTNAME = os.path.splitext(os.path.basename(__file__))[0]

CONFIGFILE = os.getenv(SCRIPTNAME.upper() + 'INI', SCRIPTNAME + '.ini')
LOGFILE    = os.getenv(SCRIPTNAME.upper() + 'LOG', SCRIPTNAME + '.log')

# lwt values - may make these configurable later?
LWTALIVE   = "1"
LWTDEAD    = "0"

class Config(RawConfigParser):

    specials = {
            'TRUE'  : True,
            'FALSE' : False,
            'NONE'  : None,
        }

    def __init__(self, configuration_file):
        RawConfigParser.__init__(self)
        f = codecs.open(configuration_file, 'r', encoding='utf-8')
        self.readfp(f)
        f.close()

        ''' set defaults '''
        self.hostname     = 'localhost'
        self.port         = 1883
        self.username     = None
        self.password     = None
        self.clientid     = SCRIPTNAME
        self.lwt          = 'clients/%s' % SCRIPTNAME
        self.skipretained = False
        self.cleansession = False

        self.logformat    = '%(asctime)-15s %(levelname)-5s [%(module)s] %(message)s'
        self.logfile      = LOGFILE
        self.loglevel     = 'DEBUG'

        self.functions    = None
        self.directory    = '.'
        self.ca_certs     = None
        self.tls_version  = None
        self.certfile     = None
        self.keyfile      = None
        self.tls_insecure = False
        self.tls          = False

        self.__dict__.update(self.config('defaults'))

        if HAVE_TLS == False:
            logging.error("TLS parameters set but no TLS available (SSL)")
            sys.exit(2)

        if self.ca_certs is not None:
            self.tls = True

        if self.tls_version is not None:
            if self.tls_version == 'tlsv1':
                self.tls_version = ssl.PROTOCOL_TLSv1
            if self.tls_version == 'sslv3':
                self.tls_version = ssl.PROTOCOL_SSLv3

        self.loglevelnumber = self.level2number(self.loglevel)

    def level2number(self, level):

        levels = {
            'CRITICAL' : 50,
            'DEBUG' : 10,
            'ERROR' : 40,
            'FATAL' : 50,
            'INFO' : 20,
            'NOTSET' : 0,
            'WARN' : 30,
            'WARNING' : 30,
        }

        return levels.get(level.upper(), levels['DEBUG'])


    def g(self, section, key, default=None):
        try:
            val = self.get(section, key)
            if val.upper() in self.specials:
                return self.specials[val.upper()]
            return ast.literal_eval(val)
        except NoOptionError:
            return default
        except ValueError:   # e.g. %(xxx)s in string
            return val
        except:
            raise
            return val

    def getlist(self, section, key):
        ''' Return a list, fail if it isn't a list '''

        val = None
        try:
            val = self.get(section, key)
            val = [s.strip() for s in val.split(',')]
        except:
            logging.warn("Expecting a list in section `%s', key `%s'" % (section, key))

        return val

    def getdict(self, section, key):
        val = self.g(section, key)

        try:
            return dict(val)
        except:
            return None

    def config(self, section):
        ''' Convert a whole section's options (except the options specified
            explicitly below) into a dict, turning

                [config:mqtt]
                host = 'localhost'
                username = None
                list = [1, 'aaa', 'bbb', 4]

            into

                {u'username': None, u'host': 'localhost', u'list': [1, 'aaa', 'bbb', 4]}

            Cannot use config.items() because I want each value to be
            retrieved with g() as above '''

        d = None
        if self.has_section(section):
            d = dict((key, self.g(section, key))
                for (key) in self.options(section) if key not in ['targets'])
        return d

    def datamap(self, name, topic):
        ''' Attempt to invoke function `name' loaded from the
            `functions' Python package '''

        val = None

        try:
            func = getattr(__import__(cf.functions, fromlist=[name]), name)
            try:
                val = func(topic, srv)  # new version
            except TypeError:
                val = func(topic)       # legacy
        except:
            raise

        return val

    def alldata(self, name, topic, data):
        ''' Attempt to invoke function `name' loaded from the
            `functions' Python package '''

        val = None

        try:
            func = getattr(__import__(cf.functions, fromlist=[name]), name)
            val = func(topic, data, srv)
        except:
            raise

        return val

    def filter(self, name, topic, payload):
        ''' Attempt to invoke function `name' from the `functions'
            package. Return that function's True/False '''

        rc = False
        try:
            func = getattr(__import__(cf.functions, fromlist=[name]), name)
            rc = func(topic, payload)
        except:
            raise

        return rc

# This class, shamelessly stolen from https://gist.github.com/cypreess/5481681
# The `srv' bits are added for mqttwarn
class PeriodicThread(object):
    """
    Python periodic Thread using Timer with instant cancellation
    """

    def __init__(self, callback=None, period=1, name=None, srv=None, *args, **kwargs):
        self.name = name
        self.srv = srv
        self.args = args
        self.kwargs = kwargs
        self.callback = callback
        self.period = period
        self.stop = False
        self.current_timer = None
        self.schedule_lock = threading.Lock()

    def start(self):
        """
        Mimics Thread standard start method
        """
        self.schedule_timer()

    def run(self):
        """
        By default run callback. Override it if you want to use inheritance
        """
        if self.callback is not None:
            self.callback(srv)

    def _run(self):
        """
        Run desired callback and then reschedule Timer (if thread is not stopped)
        """
        try:
            self.run()
        except Exception, e:
            logging.exception("Exception in running periodic thread")
        finally:
            with self.schedule_lock:
                if not self.stop:
                    self.schedule_timer()

    def schedule_timer(self):
        """
        Schedules next Timer run
        """
        self.current_timer = threading.Timer(self.period, self._run, *self.args, **self.kwargs)
        if self.name:
            self.current_timer.name = self.name
        self.current_timer.start()

    def cancel(self):
        """
        Mimics Timer standard cancel method
        """
        with self.schedule_lock:
            self.stop = True
            if self.current_timer is not None:
                self.current_timer.cancel()

    def join(self):
        """
        Mimics Thread standard join method
        """
        self.current_timer.join()

try:
    cf = Config(CONFIGFILE)
except Exception, e:
    print "Cannot open configuration at %s: %s" % (CONFIGFILE, str(e))
    sys.exit(2)

LOGLEVEL  = cf.loglevelnumber
LOGFILE   = cf.logfile
LOGFORMAT = cf.logformat

# initialise logging
logging.basicConfig(filename=LOGFILE, level=LOGLEVEL, format=LOGFORMAT)
logging.info("Starting %s" % SCRIPTNAME)
logging.info("INFO MODE")
logging.debug("DEBUG MODE")

# initialise MQTT broker connection
mqttc = paho.Client(cf.clientid, clean_session=cf.cleansession)

# initialise processor queue
q_in = Queue.Queue(maxsize=0)
num_workers = 1
exit_flag = False

ptlist = {}         # List of PeriodicThread() objects

# Class with helper functions which is passed to each plugin
# and its global instantiation
class Service(object):
    def __init__(self, mqttc, logging):
        self.mqttc    = mqttc
        self.logging  = logging
        self.SCRIPTNAME = SCRIPTNAME
srv = Service(None, None)

service_plugins = {}

# http://stackoverflow.com/questions/1305532/
class Struct:
    def __init__(self, **entries):
        self.__dict__.update(entries)
    def __repr__(self):
        return '<%s>' % str("\n ".join("%s: %s" % (k, repr(v)) for (k, v) in self.__dict__.iteritems()))
    def get(self, key, default=None):
        if key in self.__dict__ and self.__dict__[key] is not None:
            return self.__dict__[key]
        else:
            return default

    def enum(self):
        item = {}
        for (k, v) in self.__dict__.iteritems():
            item[k] = v
        return item

def render_template(filename, data):
    text = None
    if HAVE_JINJA is True:
        template = jenv.get_template(filename)
        text = template.render(data)

    return text

def get_sections():
    sections = []
    for section in cf.sections():
        if section != 'defaults' and section != 'cron' and not section.startswith('config:'):
            if cf.has_option(section, 'targets'):
                sections.append(section)
            else:
                logging.warn("Section `%s' has no targets defined" % section)
    return sections

def get_topic(section):
    if cf.has_option(section, 'topic'):
        return cf.get(section, 'topic')
    return section

def get_qos(section):
    qos = 0
    if cf.has_option(section, 'qos'):
        qos = int(cf.get(section, 'qos'))
    return qos

def get_config(section, name):
    value = None
    if cf.has_option(section, name):
        value = cf.get(section, name)
    return value

def is_filtered(section, topic, payload):
    if cf.has_option(section, 'filter'):
        filterfunc = get_function_name( cf.get(section, 'filter') )
        try:
            return cf.filter(filterfunc, topic, payload)
        except Exception, e:
            logging.warn("Cannot invoke filter function %s defined in %s: %s" % (filterfunc, section, str(e)))
    return False

def get_function_name(s):
    func = None

    if s is not None:
        try:
            valid = re.match('^[\w]+\(\)', s)
            if valid is not None:
                func = re.sub('[()]', '', s)
        except:
            pass
    return func

def get_topic_data(section, topic):
    if cf.has_option(section, 'datamap'):
        name = get_function_name(cf.get(section, 'datamap'))
        try:
            return cf.datamap(name, topic)
        except Exception, e:
            logging.warn("Cannot invoke datamap function %s defined in %s: %s" % (name, section, str(e)))
    return None

def get_all_data(section, topic, data):
    if cf.has_option(section, 'alldata'):
        name = get_function_name(cf.get(section, 'alldata'))
        try:
            return cf.alldata(name, topic, data)
        except Exception, e:
            logging.warn("Cannot invoke alldata function %s defined in %s: %s" % (name, section, str(e)))
    return None

class Job(object):
    def __init__(self, prio, service, section, topic, payload, target):
        self.prio       = prio
        self.service    = service
        self.section    = section
        self.topic      = topic
        self.payload    = payload
        self.target     = target

        logging.debug("New `%s:%s' job: %s" % (service, target, topic))
        return
    def __cmp__(self, other):
        return cmp(self.prio, other.prio)

# MQTT broker callbacks
def on_connect(mosq, userdata, result_code):
    """
    Handle connections (or failures) to the broker.
    This is called after the client has received a CONNACK message
    from the broker in response to calling connect().

    The result_code is one of;
    0: Success
    1: Refused - unacceptable protocol version
    2: Refused - identifier rejected
    3: Refused - server unavailable
    4: Refused - bad user name or password (MQTT v3.1 broker only)
    5: Refused - not authorised (MQTT v3.1 broker only)
    """
    if result_code == 0:
        logging.debug("Connected to MQTT broker, subscribing to topics...")

        subscribed = []
        for section in get_sections():
            topic = get_topic(section)
            qos = get_qos(section)

            if topic in subscribed:
                continue

            logging.debug("Subscribing to %s (qos=%d)" % (topic, qos))
            mqttc.subscribe(str(topic), qos)
            subscribed.append(topic)

        mqttc.publish(cf.lwt, LWTALIVE, qos=0, retain=True)

    elif result_code == 1:
        logging.info("Connection refused - unacceptable protocol version")
    elif result_code == 2:
        logging.info("Connection refused - identifier rejected")
    elif result_code == 3:
        logging.info("Connection refused - server unavailable")
    elif result_code == 4:
        logging.info("Connection refused - bad user name or password")
    elif result_code == 5:
        logging.info("Connection refused - not authorised")
    else:
        logging.warning("Connection failed - result code %d" % (result_code))

def on_disconnect(mosq, userdata, result_code):
    """
    Handle disconnections from the broker
    """
    if result_code == 0:
        logging.info("Clean disconnection from broker")
    else:
        logging.info("Broker connection lost. Will attempt to reconnect in 5s...")
        time.sleep(5)

def on_message(mosq, userdata, msg):
    """
    Message received from the broker
    """
    topic = msg.topic
    payload = str(msg.payload)
    logging.debug("Message received on %s: %s" % (topic, payload))

    if msg.retain == 1:
        if cf.skipretained:
            logging.debug("Skipping retained message on %s" % topic)
            return

    # Try to find matching settings for this topic
    for section in get_sections():
        # Get the topic for this section (usually the section name but optionally overridden)
        match_topic = get_topic(section)
        if paho.topic_matches_sub(match_topic, topic):
            logging.debug("Section [%s] matches message on %s. Processing..." % (section, topic))
            # Check for any message filters
            if is_filtered(section, topic, payload):
                logging.debug("Filter in section [%s] has skipped message on %s" % (section, topic))
                continue

            targetlist = cf.getlist(section, 'targets')
            if type(targetlist) != list:
                logging.error("Target definition in section [%s] is incorrect" % section)
                cleanup(0)
                return

            for t in targetlist:
                logging.debug("Message on %s going to %s" % (topic, t))
                # Each target is either "service" or "service:target"
                # If no target specified then notify ALL targets
                service = t
                target = None

                # Check if this is for a specific target
                if t.find(':') != -1:
                    try:
                        service, target = t.split(':', 2)
                    except:
                        logging.warn("Invalid target %s - should be 'service:target'" % (t))
                        continue

                if not service in service_plugins:
                    logging.error("Invalid configuration: topic %s points to non-existing service %s" % (topic, service))
                    return

                sendtos = None
                if target is None:
                    sendtos = get_service_targets(service)
                else:
                    sendtos = [target]

                for sendto in sendtos:
                    job = Job(1, service, section, topic, payload, sendto)
                    q_in.put(job)
# End of MQTT broker callbacks

def builtin_transform_data(topic, payload):
    ''' Return a dict with initial transformation data which is made
        available to all plugins '''

    tdata = {}
    dt = datetime.now()

    tdata['topic']      = topic
    tdata['payload']    = payload
    tdata['_dtepoch']   = int(time.time())          # 1392628581
    tdata['_dtiso']     = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.%fZ") # 2014-02-17T10:38:43.910691Z
    tdata['_dthhmm']    = dt.strftime('%H:%M')      # 10:16
    tdata['_dthhmmss']  = dt.strftime('%H:%M:%S')   # hhmmss=10:16:21

    return tdata

def get_service_config(service):
    config = cf.config('config:' + service)
    if config is None:
        return {}
    return dict(config)

def get_service_targets(service):
    try:
        targets = cf.getdict('config:' + service, 'targets')
        if type(targets) != dict:
            logging.error("No targets for service `%s'" % service)
            cleanup(0)
    except:
        logging.error("No targets for service `%s'" % service)
        cleanup(0)

    if targets is None:
        return {}
    return dict(targets)

def xform(function, orig_value, transform_data):
    ''' Attempt transformation on orig_value.
        1st. function()
        2nd. inline {xxxx}
        '''

    if orig_value is None:
        return None

    res = orig_value

    if function is not None:
        function_name = get_function_name(function)
        if function_name is not None:
            try:
                res = cf.datamap(function_name, transform_data)
                return res
            except Exception, e:
                logging.warn("Cannot invoke %s(): %s" % (function_name, str(e)))

        try:
            res = function.format(**transform_data).encode('utf-8')
        except Exception, e:
            pass

    if type(res) == str:
        res = res.replace("\\n", "\n")
    return res

def processor():
    """
    Queue runner. Pull a job from the queue, find the module in charge
    of handling the service, and invoke the module's plugin to do so.
    """

    while not exit_flag:
        job = q_in.get(15)

        service = job.service
        section = job.section
        target  = job.target

        logging.debug("Processor is handling: `%s' for %s" % (service, target))

        item = {
            'service'       : service,
            'section'       : section,
            'target'        : target,
            'config'        : get_service_config(service),
            'addrs'         : get_service_targets(service)[target],
            'topic'         : job.topic,
            'payload'       : job.payload,
            'data'          : None,
            'title'         : None,
            'image'         : None,
            'message'       : None,
            'priority'      : None
        }

        transform_data = builtin_transform_data(job.topic, job.payload)

        topic_data = get_topic_data(job.section, job.topic)
        if topic_data is not None and type(topic_data) == dict:
            transform_data = dict(transform_data.items() + topic_data.items())

        # The dict returned is completely merged into transformation data
        # The difference bewteen this and `get_topic_data()' is that this
        # function obtains the topic string as well as the payload and any
        # existing transformation data, and it can do 'things' with all.
        # This is the way it should originally have been, but I can no
        # longer fix the original ... (legacy)

        all_data = get_all_data(job.section, job.topic, transform_data)
        if all_data is not None and type(all_data) == dict:
            transform_data = dict(transform_data.items() + all_data.items())

        # Attempt to decode the payload from JSON. If it's possible, add
        # the JSON keys into item to pass to the plugin, and create the
        # outgoing (i.e. transformed) message.
        try:
            payload_data = json.loads(job.payload)
            transform_data = dict(transform_data.items() + payload_data.items())
        except:
            pass

        item['data'] = dict(transform_data.items())

        item['title'] = xform(get_config(section, 'title'), SCRIPTNAME, transform_data)
        item['image'] = xform(get_config(section, 'image'), '', transform_data)
        item['message'] = xform(get_config(section, 'format'), job.payload, transform_data)
        item['priority'] = int(xform(get_config(section, 'priority'), 0, transform_data))
        item['callback'] = xform(get_config(section, 'callback'), SCRIPTNAME, transform_data)

        if HAVE_JINJA is True:
            template = get_config(section, 'template')
            if template is not None:
                try:
                    text = render_template(template, transform_data)
                    if text is not None:
                        item['message'] = text
                except Exception, e:
                    logging.warn("Cannot render `%s' template: %s" % (template, str(e)))

        if item.get('message') is not None and len(item.get('message')) > 0:
            st = Struct(**item)
            notified = False
            try:
                module = service_plugins[service]['module']
                notified = module.plugin(srv, st)
            except Exception, e:
                logging.error("Cannot invoke service for `%s': %s" % (service, str(e)))

            if not notified:
                logging.warn("Notification of %s for `%s' FAILED" % (service, item.get('topic')))
        else:
            logging.warn("Notification of %s for `%s' suppressed: text is empty" % (service, item.get('topic')))

        q_in.task_done()

    logging.debug("Thread exiting...")

# http://code.davidjanes.com/blog/2008/11/27/how-to-dynamically-load-python-code/
def load_module(path):
    try:
        fp = open(path, 'rb')
        return imp.load_source(md(path).hexdigest(), path, fp)
    finally:
        try:
            fp.close()
        except:
            pass

def load_services(services):
    for service in services:
        modulefile = 'services/%s.py' % service

        service_plugins[service] = {}

        try:
            service_plugins[service]['module'] = load_module(modulefile)
            logging.debug("Service %s loaded" % (service))
        except Exception, e:
            logging.error("Can't load %s service (%s): %s" % (service, modulefile, str(e)))
            sys.exit(1)

        try:
            service_config = cf.config('config:' + service)
        except Exception, e:
            logging.error("Service `%s' has no config section: %s" % (service, str(e)))
            sys.exit(1)

        service_plugins[service]['config'] = service_config

def connect():
    """
    Load service plugins, connect to the broker, launch daemon threads and listen forever
    """

    try:
        services = cf.getlist('defaults', 'launch')
    except:
        logging.error("No services configured. Aborting")
        sys.exit(2)

    try:
        os.chdir(cf.directory)
    except Exception, e:
        logging.error("Cannot chdir to %s: %s" % (cf.directory, str(e)))
        sys.exit(2)

    load_services(services)

    srv.mqttc = mqttc
    srv.logging = logging

    logging.debug("Attempting connection to MQTT broker %s:%d..." % (cf.hostname, int(cf.port)))
    mqttc.on_connect = on_connect
    mqttc.on_message = on_message
    mqttc.on_disconnect = on_disconnect

    # check for authentication
    if cf.username:
        mqttc.username_pw_set(cf.username, cf.password)

    # set the lwt before connecting
    logging.debug("Setting LWT to %s..." % (cf.lwt))
    mqttc.will_set(cf.lwt, payload=LWTDEAD, qos=0, retain=True)

    # Delays will be: 3, 6, 12, 24, 30, 30, ...
    # mqttc.reconnect_delay_set(delay=3, delay_max=30, exponential_backoff=True)

    if cf.tls == True:
        mqttc.tls_set(cf.ca_certs, cf.certfile, cf.keyfile, tls_version=cf.tls_version, ciphers=None)

    if cf.tls_insecure:
        mqttc.tls_insecure_set(True)

    try:
        mqttc.connect(cf.hostname, int(cf.port), 60)
    except Exception, e:
        logging.error("Cannot connect to MQTT broker at %s:%d: %s" % (cf.hostname, int(cf.port), str(e)))
        sys.exit(2)

    # Launch worker threads to operate on queue
    for i in range(num_workers):
        t = threading.Thread(target=processor)
        t.daemon = True
        t.start()

    # If the config file has a [cron] section, the key names therein are
    # functions from 'myfuncs.py' which should be invoked periodically.
    # The key's value (must be numeric!) is the period in seconds.

    if cf.has_section('cron'):
        for name, val in cf.items('cron'):
            try:
                func = getattr(__import__(cf.functions, fromlist=[name]), name)
                interval = float(val)
                ptlist[name] = PeriodicThread(func, interval, srv=srv)
                ptlist[name].start()
            except AttributeError:
                logging.error("[cron] section has function [%s] specified, but that's not defined" % name)
                continue



    while True:
        try:
            mqttc.loop_forever()
        except socket.error:
            logging.info("MQTT server disconnected; sleeping")
            time.sleep(5)
        except:
            # FIXME: add logging with trace
            raise

def cleanup(signum=None, frame=None):
    """
    Signal handler to ensure we disconnect cleanly
    in the event of a SIGTERM or SIGINT.
    """

    global exit_flag

    exit_flag = True

    for ptname in ptlist:
        logging.debug("Cancel %s timer" % ptname)
        ptlist[ptname].cancel()

    logging.debug("Disconnecting from MQTT broker...")
    mqttc.publish(cf.lwt, LWTDEAD, qos=0, retain=True)
    mqttc.loop_stop()
    mqttc.disconnect()

    logging.info("Waiting for queue to drain")
    q_in.join()

    logging.debug("Exiting on signal %d", signum)
    sys.exit(signum)

if __name__ == '__main__':

    # use the signal module to handle signals
    signal.signal(signal.SIGTERM, cleanup)
    signal.signal(signal.SIGINT, cleanup)

    # connect to broker and start listening
    connect()

########NEW FILE########
__FILENAME__ = samplefuncs
import time

try:
    import json
except ImportError:
    import simplejson as json

def OwnTracksTopic2Data(topic):
    if type(topic) == str:
        try:
            # owntracks/username/device
            parts = topic.split('/')
            username = parts[1]
            deviceid = parts[2]
        except:
            deviceid = 'unknown'
            username = 'unknown'
        return dict(username=username, device=deviceid)
    return None

def OwnTracksConvert(data):
    if type(data) == dict:
        tst = data.get('tst', int(time.time()))
        data['tst'] = time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(int(tst)))
        # Remove these elements to eliminate warnings
        for k in ['_type', 'desc']:
            data.pop(k, None)

        return "{username} {device} {tst} at location {lat},{lon}".format(**data)

# custom function to filter out any OwnTracks notifications which do
# not contain the 'batt' parameter
def OwnTracksBattFilter(topic, message):
    data = dict(json.loads(message).items())
    if data['batt'] is not None:
        return int(data['batt']) > 20
    return True

########NEW FILE########
__FILENAME__ = dbus
#!/usr/bin/env python
# -*- coding: utf-8 -*-

__author__    = 'Fabian Affolter <fabian()affolter-engineering.ch>'
__copyright__ = 'Copyright 2014 Fabian Affolter'
__license__   = """Eclipse Public License - v 1.0 (http://www.eclipse.org/legal/epl-v10.html)"""

HAVE_DBUS=True
try:
    import dbus
except ImportError:
    HAVE_DBUS=False

def plugin(srv, item):
    """Send a message through dbus to the user's desktop."""

    srv.logging.debug("*** MODULE=%s: service=%s, target=%s", __file__, item.service, item.target)

    if not HAVE_DBUS:
        srv.logging.error("Cannot send DBUS message; `dbus' module not installed")
        return False

    text = item.message
    summary = item.addrs[0]
    app_name = item.get('title', srv.SCRIPTNAME)
    replaces_id = 0
    service = 'org.freedesktop.Notifications'
    path = '/' + service.replace('.', '/')
    interface = service
    app_icon = '/usr/share/icons/gnome/32x32/places/network-server.png'
    expire_timeout = 1000
    actions = []
    hints = []

    try:
        srv.logging.debug("Sending message to %s..." % (item.target))
        session_bus = dbus.SessionBus()
        obj = session_bus.get_object(service, path)
        interface = dbus.Interface(obj, interface)
        interface.Notify(app_name, replaces_id, app_icon, summary, text,
                    actions, hints, expire_timeout)
        srv.logging.debug("Successfully sent message")
    except Exception, e:
        srv.logging.error("Error sending message to %s: %s" % (item.target, str(e)))
        return False

    return True

########NEW FILE########
__FILENAME__ = file
#!/usr/bin/env python
# -*- coding: utf-8 -*-

__author__    = 'Jan-Piet Mens <jpmens()gmail.com>'
__copyright__ = 'Copyright 2014 Jan-Piet Mens'
__license__   = """Eclipse Public License - v 1.0 (http://www.eclipse.org/legal/epl-v10.html)"""

def plugin(srv, item):

    srv.logging.debug("*** MODULE=%s: service=%s, target=%s", __file__, item.service, item.target)

    # item.config is brought in from the configuration file
    config   = item.config

    # addrs is a list[] associated with a particular target.
    # While it may contain more than one item (e.g. pushover)
    # the `file' service carries one only, i.e. a path name
    filename = item.addrs[0]

    # If the incoming payload has been transformed, use that,
    # else the original payload
    text = item.message

    if type(config) == dict and 'append_newline' in config and config['append_newline']:
        text = text + "\n"

    try:
        f = open(filename, "a")
        f.write(text)
        f.close()
    except Exception, e:
        srv.logging.warning("Cannot write to file `%s': %s" % (filename, str(e)))
        return False

    return True

########NEW FILE########
__FILENAME__ = freeswitch
#!/usr/bin/env python
# -*- coding: utf-8 -*-

__author__    = 'Ben Jones <ben.jones12()gmail.com>'
__copyright__ = 'Copyright 2014 Ben Jones'
__license__   = """Eclipse Public License - v 1.0 (http://www.eclipse.org/legal/epl-v10.html)"""

from xmlrpclib import ServerProxy
import urllib

def plugin(srv, item):

    srv.logging.debug("*** MODULE=%s: service=%s, target=%s", __file__, item.service, item.target)

    host     = item.config['host']
    port     = item.config['port']
    username = item.config['username']
    password = item.config['password']
 
    gateway  = item.addrs[0]
    number   = item.addrs[1]    
    title    = item.title
    message  = item.message

    if len(message) > 100:
        srv.logging.debug("Message is too long (%d chars) for Google Translate API (max 100 chars allowed), truncating message before processing" % (len(message)))
        message = message[:100]

    try:
        # Google Translate API
        params = urllib.urlencode({ 'tl' : 'en', 'q' : message })
        shout_url = "shout://translate.google.com/translate_tts?" + params
        # Freeswitch API
        server = ServerProxy("http://%s:%s@%s:%d" % (username, password, host, port))
        # channel variables we need to setup the call
        channel_vars = "{ignore_early_media=true,originate_timeout=60,origination_caller_id_name='" + title + "'}"
        # originate the call
        server.freeswitch.api("originate", channel_vars + gateway + number + " &playback(" + shout_url + ")")
    except Exception, e:
        srv.logging.error("Error originating Freeswitch VOIP call to %s via %s%s: %s" % (item.target, gateway, number, str(e)))
        return False

    return True

########NEW FILE########
__FILENAME__ = gss
#!/usr/bin/env python
# -*- coding: utf-8 -*-

__author__    = 'Jan Badenhorst <janhendrik.badenhorst()gmail.com>'
__copyright__ = 'Copyright 2014 Jan Badenhorst'
__license__   = """Eclipse Public License - v 1.0 (http://www.eclipse.org/legal/epl-v10.html)"""

try:
    import json
except ImportError:
    import simplejson as json

HAVE_GSS = True
try:
    import gdata.spreadsheet.service
except ImportError:
    HAVE_GSS = False


def plugin(srv, item):

    srv.logging.debug("*** MODULE=%s: service=%s, target=%s", __file__, item.service, item.target)
    if not HAVE_GSS:
        srv.logging.warn("Google Spreadsheet is not installed")
        return False

    spreadsheet_key = item.addrs[0]
    worksheet_id = item.addrs[1]
    username = item.config['username']
    password = item.config['password']

    try:
        srv.logging.debug("Adding row to spreadsheet %s [%s]..." % (spreadsheet_key, worksheet_id))

        client = gdata.spreadsheet.service.SpreadsheetsService()
        client.debug = True
        client.email = username
        client.password = password
        client.source = 'mqttwarn'
        client.ProgrammaticLogin()

        # The API Does not like raw numbers as values.
        row = {}
        for k, v in item.data.iteritems():
            row[k] = str(v)

        client.InsertRow(row, spreadsheet_key, worksheet_id)
        srv.logging.debug("Successfully added row to spreadsheet")

    except Exception as e:
        srv.logging.warn("Error adding row to spreadsheet %s [%s]: %s" % (spreadsheet_key, worksheet_id, str(e)))
        return False

    return True
########NEW FILE########
__FILENAME__ = http
#!/usr/bin/env python
# -*- coding: utf-8 -*-

__author__    = 'Jan-Piet Mens <jpmens()gmail.com>'
__copyright__ = 'Copyright 2014 Ben Jones'
__license__   = """Eclipse Public License - v 1.0 (http://www.eclipse.org/legal/epl-v10.html)"""

import urllib
import urllib2
import base64
try:
    import json
except ImportError:
    import simplejson as json

def plugin(srv, item):
    ''' addrs: (method, url dict(params), list(username, password)) '''

    srv.logging.debug("*** MODULE=%s: service=%s, target=%s", __file__, item.service, item.target)

    method = item.addrs[0]
    url    = item.addrs[1]
    params = item.addrs[2]
    timeout = item.config.get('timeout', 60)

    auth = None
    try:
        username, password = item.addrs[3]
        auth = base64.encodestring('%s:%s' % (username, password)).replace('\n', '')
    except:
        pass

    # Try and transform the URL. Use original URL if it's not possible
    try:
        url = url.format(**item.data)
    except:
        pass

    if params is not None:
        for key in params.keys():

            # { 'q' : '@message' }
            # Quoted field, starts with '@'. Do not use .format, instead grab
            # the item's [message] and inject as parameter value.
            if params[key].startswith('@'):         # "@message"
                params[key] = item.get(params[key][1:], "NOP")

            else:
                try:
                    params[key] = params[key].format(**item.data).encode('utf-8')
                except Exception, e:
                    srv.logging.debug("Parameter %s cannot be formatted: %s" % (key, str(e)))
                    return False

    message  = item.message

    if method.upper() == 'GET':
        try:
            if params is not None:
                resource = url
                if not resource.endswith('?'):
                    resource = resource + '?'
                resource = resource + urllib.urlencode(params)
            else:
                resource = url

            request = urllib2.Request(resource)
            request.add_header('User-agent', srv.SCRIPTNAME)

            if auth is not None:
                request.add_header("Authorization", "Basic %s" % auth)

            resp = urllib2.urlopen(request, timeout=timeout)
            data = resp.read()
        except Exception, e:
            srv.logging.warn("Cannot GET %s: %s" % (resource, str(e)))
            return False

        return True

    if method.upper() == 'POST':
        try:
            request = urllib2.Request(url)
            if params is not None:
                encoded_params = urllib.urlencode(params)
            else:
                encoded_params = message

            request.add_data(encoded_params)
            request.add_header('User-agent', srv.SCRIPTNAME)
            if auth is not None:
                request.add_header("Authorization", "Basic %s" % auth)
            resp = urllib2.urlopen(request, timeout=timeout)
            data = resp.read()
            # print "POST returns ", data
        except Exception, e:
            srv.logging.warn("Cannot POST %s: %s" % (url, str(e)))
            return False

        return True

    srv.logging.warn("Unsupported HTTP method: %s" % (method))
    return False

########NEW FILE########
__FILENAME__ = irccat
#!/usr/bin/env python
# -*- coding: utf-8 -*-

__author__    = 'Jan-Piet Mens <jpmens()gmail.com>'
__copyright__ = 'Copyright 2014 Jan-Piet Mens'
__license__   = """Eclipse Public License - v 1.0 (http://www.eclipse.org/legal/epl-v10.html)"""

import socket

def plugin(srv, item):

    srv.logging.debug("*** MODULE=%s: service=%s, target=%s", __file__, item.service, item.target)

    try:
        addr, port, channel = item.addrs
    except:
        srv.logging.warn("Incorrect target configuration")
        return False

    message  = item.message

    color = None
    priority =  item.priority
    if priority == 1:
        color = '%GREEN'
    if priority == 2:
        color = '%RED'

    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((addr, port))
        if color is not None:
            sock.send(color)
        sock.send(message)
        sock.close()

    except Exception, e:
        srv.logging.error("Error sending IRCCAT notification to %s:%s [%s]: %s" % (item.target, addr, port, str(e)))
        return False

    return True

########NEW FILE########
__FILENAME__ = linuxnotify
#!/usr/bin/env python
# -*- coding: utf-8 -*-

__author__    = 'Fabian Affolter <fabian()affolter-engineering.ch>'
__copyright__ = 'Copyright 2014 Fabian Affolter'
__license__   = """Eclipse Public License - v 1.0 (http://www.eclipse.org/legal/epl-v10.html)"""

from gi.repository import Notify

def plugin(srv, item):
    """Send a message to the user's desktop notification system."""

    srv.logging.debug("*** MODULE=%s: service=%s, target=%s", __file__,
            item.service, item.target)

    title = item.addrs[0]
    text = item.message

    try:
        srv.logging.debug("Sending notification to the user's desktop")
        Notify.init('mqttwarn')
        n = Notify.Notification.new(
            title,
            text,
            '/usr/share/icons/gnome/32x32/places/network-server.png')
        n.show()
        srv.logging.debug("Successfully sent notification")
    except Exception, e:
        srv.logging.warning("Cannot invoke notification to linux: %s" % (str(e)))
        return False

    return True

########NEW FILE########
__FILENAME__ = log
#!/usr/bin/env python
# -*- coding: utf-8 -*-

__author__    = 'Jan-Piet Mens <jpmens()gmail.com>'
__copyright__ = 'Copyright 2014 Jan-Piet Mens'
__license__   = """Eclipse Public License - v 1.0 (http://www.eclipse.org/legal/epl-v10.html)"""

def plugin(srv, item):

    srv.logging.debug("*** MODULE=%s: service=%s, target=%s", __file__, item.service, item.target)

    level = item.addrs[0]

    text = item.message

    levels = {
        'debug' : srv.logging.debug,
        'info'  : srv.logging.info,
        'warn'  : srv.logging.warning,
        'crit'  : srv.logging.critical,
        'error'  : srv.logging.error,
    }

    try:
        levels[level]("%s", text)
    except Exception, e:
        srv.logging.warn("Cannot invoke service log with level `%s': %s" % (level, str(e)))
        return False

    return True

########NEW FILE########
__FILENAME__ = mqtt
#!/usr/bin/env python
# -*- coding: utf-8 -*-

__author__    = 'Jan-Piet Mens <jpmens()gmail.com>'
__copyright__ = 'Copyright 2014 Jan-Piet Mens'
__license__   = """Eclipse Public License - v 1.0 (http://www.eclipse.org/legal/epl-v10.html)"""

import paho.mqtt.publish as mqtt  # pip install --upgrade paho-mqtt
import ConfigParser
import codecs

def conf(ini_file, params):
    try:
        c = ConfigParser.ConfigParser()
        # f = codecs.open(ini_file, 'r', encoding='utf-8')
        f = open(ini_file, 'r')
        c.readfp(f)
        f.close()
    except Exception, e:
        raise

    if c.has_section('defaults'):
        # differentiate bool, int, str
        if c.has_option('defaults', 'hostname'):
            params['hostname']      = c.get('defaults', 'hostname')
        if c.has_option('defaults', 'client_id'):
            params['client_id']     = c.get('defaults', 'client_id')
        if c.has_option('defaults', 'port'):
            params['port']          = c.getint('defaults', 'port')
        if c.has_option('defaults', 'qos'):
            params['qos']           = c.getint('defaults', 'qos')
        if c.has_option('defaults', 'retain'):
            params['retain']        = c.getboolean('defaults', 'retain')

    auth = None
    if c.has_section('auth'):
        auth = dict(c.items('auth'))

    tls = None
    if c.has_section('tls'):
        tls = dict(c.items('tls'))

    return dict(connparams=params, auth=auth, tls=tls)

def plugin(srv, item):

    srv.logging.debug("*** MODULE=%s: service=%s, target=%s", __file__, item.service, item.target)

    config   = item.config

    hostname    = config.get('hostname', 'localhost')
    port        = int(config.get('port', '1883'))
    qos         = int(config.get('qos', 0))
    retain      = int(config.get('retain', 0))
    username    = config.get('username', None)
    password    = config.get('password', None)

    params = {
        'hostname'  : hostname,
        'port'      : port,
        'qos'       : qos,
        'retain'    : retain,
        'client_id' : None,
    }

    auth = None
    tls = None

    if username is not None:
        auth = {
            'username' : username,
            'password' : password
        }

    ini_file = None
    try:
        outgoing_topic, ini_file = item.addrs
    except:
        outgoing_topic =  item.addrs[0]

    if ini_file is not None:
        try:
            data = conf(ini_file, params)
        except Exception, e:
                srv.logging.error("Target mqtt cannot load/parse INI file `%s': %s", ini_file, str(e))
                return False

        if 'connparams' in data and data['connparams'] is not None:
            params = dict(params.items() + data['connparams'].items())

    # Attempt to interpolate data into topic name. If it isn't possible
    # ignore, and return without publish

    if item.data is not None:
        try:
            outgoing_topic =  item.addrs[0].format(**item.data).encode('utf-8')
        except:
            srv.logging.debug("Outgoing topic cannot be formatted; not published")
            return False

    outgoing_payload = item.message
    if type(outgoing_payload) == unicode:
        outgoing_payload = bytearray(outgoing_payload, encoding='utf-8')

    try:
        mqtt.single(outgoing_topic, outgoing_payload,
            auth=auth,
            tls=tls,
            **params)
    except Exception, e:
        srv.logging.warning("Cannot PUBlish via `mqtt:%s': %s" % (item.target, str(e)))
        return False

    return True

########NEW FILE########
__FILENAME__ = mqttpub
#!/usr/bin/env python
# -*- coding: utf-8 -*-

__author__    = 'Jan-Piet Mens <jpmens()gmail.com>'
__copyright__ = 'Copyright 2014 Jan-Piet Mens'
__license__   = """Eclipse Public License - v 1.0 (http://www.eclipse.org/legal/epl-v10.html)"""

def plugin(srv, item):
    ''' Publish via MQTT to the same broker connection.
        Requires topic, qos and retain flag '''

    srv.logging.debug("*** MODULE=%s: service=%s, target=%s", __file__, item.service, item.target)

    outgoing_topic =  item.addrs[0]
    qos  =  item.addrs[1]
    retain = item.addrs[2]

    # Attempt to interpolate data into topic name. If it isn't possible
    # ignore, and return without publish

    if item.data is not None:
        try:
            outgoing_topic =  item.addrs[0].format(**item.data).encode('utf-8')
        except:
            srv.logging.debug("Outgoing topic cannot be formatted; not published")
            return False

    outgoing_payload = item.message
    if type(outgoing_payload) == unicode:
        outgoing_payload = bytearray(outgoing_payload, encoding='utf-8')

    try:
        srv.mqttc.publish(outgoing_topic, outgoing_payload, qos=qos, retain=retain)
    except Exception, e:
        srv.logging.warning("Cannot PUBlish via `mqttpub:%s': %s" % (item.target, str(e)))
        return False

    return True

########NEW FILE########
__FILENAME__ = mysql
#!/usr/bin/env python
# -*- coding: utf-8 -*-

__author__    = 'Jan-Piet Mens <jpmens()gmail.com>'
__copyright__ = 'Copyright 2014 Jan-Piet Mens'
__license__   = """Eclipse Public License - v 1.0 (http://www.eclipse.org/legal/epl-v10.html)"""

import MySQLdb
import sys

# https://mail.python.org/pipermail/tutor/2010-December/080701.html
def add_row(cursor, tablename, rowdict):
    # XXX tablename not sanitized
    # XXX test for allowed keys is case-sensitive

    unknown_keys = None

    # filter out keys that are not column names
    cursor.execute("describe %s" % tablename)
    allowed_keys = set(row[0] for row in cursor.fetchall())
    keys = allowed_keys.intersection(rowdict)

    if len(rowdict) > len(keys):
        unknown_keys = set(rowdict) - allowed_keys

    columns = ", ".join(keys)
    values_template = ", ".join(["%s"] * len(keys))

    sql = "insert into %s (%s) values (%s)" % (
        tablename, columns, values_template)
    values = tuple(rowdict[key] for key in keys)
    cursor.execute(sql, values)

    return unknown_keys

def plugin(srv, item):

    srv.logging.debug("*** MODULE=%s: service=%s, target=%s", __file__, item.service, item.target)

    host    = item.config.get('host', 'localhost')
    port    = item.config.get('port', 3306)
    user    = item.config.get('user')
    passwd  = item.config.get('pass')
    dbname  = item.config.get('dbname')

    try:
        table_name, fallback_col = item.addrs
    except:
        srv.logging.warn("mysql target incorrectly configured")
        return False

    try:
        conn = MySQLdb.connect(host=host,
                    user=user,
                    passwd=passwd,
                    db=dbname)
        cursor = conn.cursor()
    except Exception, e:
        srv.logging.warn("Cannot connect to mysql: %s" % (str(e)))
        return False

    text = item.message

    # Create new dict for column data. First add fallback column
    # with full payload. Then attempt to use formatted JSON values
    col_data = {
        fallback_col : text
       }

    if item.data is not None:
        for key in item.data.keys():
            try:
                col_data[key] = item.data[key].format(**item.data).encode('utf-8')
            except Exception, e:
                col_data[key] = item.data[key]

    try:
        unknown_keys = add_row(cursor, table_name, col_data)
        if unknown_keys is not None:
            srv.logging.debug("Skipping unused keys %s" % ",".join(unknown_keys))
        conn.commit()
    except Exception, e:
        srv.logging.warn("Cannot add mysql row: %s" % (str(e)))
        cursor.close()
        conn.close()
        return False

    cursor.close()
    conn.close()

    return True

########NEW FILE########
__FILENAME__ = nma
#!/usr/bin/env python
# -*- coding: utf-8 -*-

__author__    = 'Jan-Piet Mens <jpmens()gmail.com>'
__copyright__ = 'Copyright 2014 Jan-Piet Mens'
__license__   = """Eclipse Public License - v 1.0 (http://www.eclipse.org/legal/epl-v10.html)"""

HAVE_NMA=True
try:
    from pynma import PyNMA
except ImportError:
    HAVE_NMA=False


def plugin(srv, item):
    ''' expects (apikey, appname, eventname) in addrs'''

    srv.logging.debug("*** MODULE=%s: service=%s, target=%s", __file__, item.service, item.target)
    if not HAVE_NMA:
        srv.logging.warn("PyNMA is not installed")
        return False

    try:
        apikey, appname, event = item.addrs
    except:
        srv.logging.warn("NMA incorrect # of target params passed")
        return False

    text = item.message
    priority = item.get('priority', 0)

    try:
        p = PyNMA()
        p.addkey(apikey)

        res = p.push(application=appname,
            event=event,
            description=text,
            url="",
            contenttype=None,
            priority=priority,
            batch_mode=False)

        srv.logging.debug("NMA returns %s" % (res))
        # {'xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx': {'message': '', u'code': u'200', 'type': u'success', u'remaining': u'798', u'resettimer': u'46'}}

        # FIXME: test for code 200
    except Exception, e:
        srv.logging.warn("NMA failed: %s" % (str(e)))
        return False

    return True

########NEW FILE########
__FILENAME__ = nntp
#!/usr/bin/env python
# -*- coding: utf-8 -*-

__author__    = 'Jan-Piet Mens <jpmens()gmail.com>'
__copyright__ = 'Copyright 2014 Jan-Piet Mens'
__license__   = """Eclipse Public License - v 1.0 (http://www.eclipse.org/legal/epl-v10.html)"""

import sys
import nntplib
import StringIO
from email.mime.text import MIMEText
from email.Utils import formatdate

def plugin(srv, item):

    srv.logging.debug("*** MODULE=%s: service=%s, target=%s", __file__, item.service, item.target)

    host      = item.config.get('server', 'localhost')
    port      = item.config.get('port', 119)
    username  = item.config.get('username')
    password  = item.config.get('password')

    try:
        from_hdr = item.addrs[0]
        newsgroup = item.addrs[1]
    except Exception:
        srv.logging.error("Incorrect target configuration for %s" % item.target)
        return False

    try:

        text  = item.message
        title    = item.title

        msg = MIMEText(text)

        msg['From']         = from_hdr
        msg['Subject']      = item.title
        msg['Newsgroups']   = newsgroup
        msg['Date']         = formatdate()
        msg['User-Agent']   = srv.SCRIPTNAME
        # msg['Message-ID'] = '<jp001@tiggr>'

        msg_file = StringIO.StringIO(msg.as_string())
        nntp = nntplib.NNTP(host, port, user=username, password=password)

        srv.logging.debug(nntp.getwelcome())
        nntp.set_debuglevel(0)

        nntp.post(msg_file)
        nntp.quit()
    except Exception, e:
        srv.logging.warn("Cannot post to %s newsgroup: %s" % (newsgroup, str(e)))
        return False

    return True

########NEW FILE########
__FILENAME__ = nsca
#!/usr/bin/env python
# -*- coding: utf-8 -*-

__author__    = 'Jan-Piet Mens <jpmens()gmail.com>'
__copyright__ = 'Copyright 2014 Jan-Piet Mens'
__license__   = """Eclipse Public License - v 1.0 (http://www.eclipse.org/legal/epl-v10.html)"""

HAVE_NSCA = True
try:
    import pynsca                     # https://pypi.python.org/pypi/pynsca
    from pynsca import NSCANotifier
except ImportError:
    HAVE_NSCA = False

def plugin(srv, item):

    srv.logging.debug("*** MODULE=%s: service=%s, target=%s", __file__, item.service, item.target)

    if HAVE_NSCA == False:
        return False

    config   = item.config

    statii = [ pynsca.OK, pynsca.WARNING, pynsca.CRITICAL, pynsca.UNKNOWN ]
    status = pynsca.OK
    try:
        prio = item.priority
        status = statii[prio]
    except:
        pass

    nsca_host = config['nsca_host']

    host_name = item.addrs[0]
    service_description = item.addrs[1]

    # If the incoming payload has been transformed, use that,
    # else the original payload
    text = item.message

    try:
        notif = NSCANotifier(nsca_host)
        notif.svc_result(host_name, service_description, status, text)
    except Exception, e:
        srv.logging.warning("Cannot notify to NSCA host `%s': %s" % (nsca_host, str(e)))
        return False

    return True

########NEW FILE########
__FILENAME__ = osxnotify
#!/usr/bin/env python
# -*- coding: utf-8 -*-

__author__    = 'Jan-Piet Mens <jpmens()gmail.com>'
__copyright__ = 'Copyright 2014 Jan-Piet Mens'
__license__   = """Eclipse Public License - v 1.0 (http://www.eclipse.org/legal/epl-v10.html)"""

from pync import Notifier   # https://github.com/SeTem/pync
import os

def plugin(srv, item):

    srv.logging.debug("*** MODULE=%s: service=%s, target=%s", __file__, item.service, item.target)

    text = item.message
    application_name = item.get('title', item.topic)

    try:
        Notifier.notify(text,  title=application_name)
    except Exception, e:
        srv.logging.warning("Cannot invoke Notifier to osx: %s" % (str(e)))
        return False

    return True

########NEW FILE########
__FILENAME__ = osxsay
#!/usr/bin/env python
# -*- coding: utf-8 -*-

__author__    = 'Jan-Piet Mens <jpmens()gmail.com>'
__copyright__ = 'Copyright 2014 Jan-Piet Mens'
__license__   = """Eclipse Public License - v 1.0 (http://www.eclipse.org/legal/epl-v10.html)"""

import subprocess

def plugin(srv, item):

    srv.logging.debug("*** MODULE=%s: service=%s, target=%s", __file__, item.service, item.target)

    voice = item.addrs[0]
    text = item.message

    argv = [ "/usr/bin/say", "-f", "-", "--voice=%s" % voice ]

    try:
        proc = subprocess.Popen(argv,
            stdin=subprocess.PIPE, close_fds=True)
    except Exception, e:
        srv.logging.warn("Cannot create osxsay pipe: %s" % str(e))
        return False

    try:
        proc.stdin.write(text)
    except IOError as e:
        srv.logging.warn("Cannot write to osxsay pipe: errno %d" % (e.errno))
        return False
    except Exception, e:
        srv.logging.warn("Cannot write to osxsay pipe: %s" % (str(e)))
        return False

    proc.stdin.close()
    proc.wait()
    return True

########NEW FILE########
__FILENAME__ = pastebinpub
#!/usr/bin/env python
# -*- coding: utf-8 -*-

__author__    = 'Fabian Affolter <fabian()affolter-engineering.ch>'
__copyright__ = 'Copyright 2014 Fabian Affolter'
__license__   = """Eclipse Public License - v 1.0 (http://www.eclipse.org/legal/epl-v10.html)"""

HAVE_PASTEBIN=True
try:
    from pastebin import PastebinAPI
except:
    HAVE_PASTEBIN=False

def plugin(srv, item):
    """ Pushlish the message to pastebin.com """

    srv.logging.debug("*** MODULE=%s: service=%s, target=%s", __file__,
        item.service, item.target)

    if HAVE_PASTEBIN is False:
        srv.logging.warn("Pastebin module is not available.")
        return False

    pastebin_data = item.addrs

    pastebinapi = PastebinAPI()
    api_dev_key = pastebin_data[0]
    username = pastebin_data[1]
    password = pastebin_data[2]
    pastename = 'mqttwarn'
    pasteprivate = pastebin_data[3]
    expiredate = pastebin_data[4]

    text = item.message

    try:
        api_user_key = pastebinapi.generate_user_key(
            api_dev_key,
            username,
            password)
    except Exception, e:
        srv.logging.warn("Cannot retrieve session data from pastebin: %s" % (str(e)))
        return False

    try:
        srv.logging.debug("Adding entry to pastebin.com as user %s..." % (username))
        pastebinapi.paste(
            api_dev_key,
            text,
            api_user_key = api_user_key,
            paste_name = pastename,
            paste_format = None,
            paste_private = pasteprivate,
            paste_expire_date = expiredate
            )
        srv.logging.debug("Successfully added paste to pastebin")
    except Exception, e:
        srv.logging.warn("Cannot publish to pastebin: %s" % (str(e)))
        return False

    return True

########NEW FILE########
__FILENAME__ = pipe
#!/usr/bin/env python
# -*- coding: utf-8 -*-

__author__    = 'Jan-Piet Mens <jpmens()gmail.com>'
__copyright__ = 'Copyright 2014 Jan-Piet Mens'
__license__   = """Eclipse Public License - v 1.0 (http://www.eclipse.org/legal/epl-v10.html)"""

import subprocess
import errno

def plugin(srv, item):

    srv.logging.debug("*** MODULE=%s: service=%s, target=%s", __file__, item.service, item.target)

    # addrs is a list[] with process name and args
    argv = item.addrs

    text = item.message

    if not text.endswith("\n"):
        text = text + "\n"

    try:
        proc = subprocess.Popen(argv,
            stdin=subprocess.PIPE, close_fds=True)
    except Exception, e:
        srv.logging.warn("Cannot create pipe: %s" % str(e))
        return False

    try:
        proc.stdin.write(text)
    except IOError as e:
        srv.logging.warn("Cannot write to pipe: errno %d" % (e.errno))
        return False
    except Exception, e:
        srv.logging.warn("Cannot write to pipe: %s" % (str(e)))
        return False

    proc.stdin.close()
    proc.wait()
    return True

########NEW FILE########
__FILENAME__ = prowl
#!/usr/bin/env python
# -*- coding: utf-8 -*-

__author__    = 'Jan-Piet Mens <jpmens()gmail.com>'
__copyright__ = 'Copyright 2014 Jan-Piet Mens'
__license__   = """Eclipse Public License - v 1.0 (http://www.eclipse.org/legal/epl-v10.html)"""

import prowlpy # from https://github.com/jacobb/prowlpy

def plugin(srv, item):

    srv.logging.debug("*** MODULE=%s: service=%s, target=%s", __file__, item.service, item.target)

    apikey = item.addrs[0]
    application = item.addrs[1]

    title = item.get('title', srv.SCRIPTNAME)
    text = item.message
    priority = item.get('priority', 0)

    try:
        p = prowlpy.Prowl(apikey)
        p.post(application=title,
            event=application,
            description=text,
            priority=priority,
            providerkey=None,
            url=None)
    except Exception, e:
        srv.logging.warning("Cannot prowl: %s" % (str(e)))
        return False

    return True

########NEW FILE########
__FILENAME__ = pushbullet
#!/usr/bin/env python
# -*- coding: utf-8 -*-

__author__    = 'Jan-Piet Mens <jpmens()gmail.com>'
__copyright__ = 'Copyright 2014 Jan-Piet Mens'
__license__   = """Eclipse Public License - v 1.0 (http://www.eclipse.org/legal/epl-v10.html)"""

HAVE_PUSHBULLET=True
try:
    from pushbullet import PushBullet
except ImportError:
    HAVE_PUSHBULLET=False

def plugin(srv, item):
    ''' expects (apikey, device_id) in adddrs '''

    srv.logging.debug("*** MODULE=%s: service=%s, target=%s", __file__, item.service, item.target)
    if not HAVE_PUSHBULLET:
        srv.logging.warn("pushbullet is not installed")
        return False

    try:
        apikey, device_id = item.addrs
    except:
        srv.logging.warn("pushbullet target is incorrectly configured")
        return False

    text = item.message
    title = item.get('title', srv.SCRIPTNAME)

    try:
        srv.logging.debug("Sending pushbullet notification to %s..." % (item.target))
        pb = PushBullet(apikey)
        pb.pushNote(device_id, title, text)
        srv.logging.debug("Successfully sent pushbullet notification")
    except Exception, e:
        srv.logging.warning("Cannot notify pushbullet: %s" % (str(e)))
        return False

    return True

########NEW FILE########
__FILENAME__ = pushover
#!/usr/bin/env python
# -*- coding: utf-8 -*-

# The code for pushover() between cuts was written by Mike Matz and
# gracefully swiped from https://github.com/pix0r/pushover

import urllib
import urllib2
import urlparse
import json
import os

PUSHOVER_API = "https://api.pushover.net/1/"

class PushoverError(Exception): pass

def pushover(**kwargs):
    assert 'message' in kwargs

    if not 'token' in kwargs:
        kwargs['token'] = os.environ['PUSHOVER_TOKEN']
    if not 'user' in kwargs:
        kwargs['user'] = os.environ['PUSHOVER_USER']

    url = urlparse.urljoin(PUSHOVER_API, "messages.json")
    data = urllib.urlencode(kwargs)
    req = urllib2.Request(url, data)
    response = urllib2.urlopen(req)
    output = response.read()
    data = json.loads(output)

    if data['status'] != 1:
        raise PushoverError(output)

__author__    = 'Jan-Piet Mens <jpmens()gmail.com>'
__copyright__ = 'Copyright 2014 Jan-Piet Mens'
__license__   = """Eclipse Public License - v 1.0 (http://www.eclipse.org/legal/epl-v10.html)"""

def plugin(srv, item):

    message  = item.message
    addrs    = item.addrs
    title    = item.title
    priority = item.priority
    callback = item.callback

    srv.logging.debug("*** MODULE=%s: service=%s, target=%s", __file__, item.service, item.target)

    # addrs is an array with two elements:
    # 0 is the user key
    # 1 is the app key

    try:
        userkey = addrs[0]
        appkey  = addrs[1]
    except:
        srv.logging.warn("No pushover userkey/appkey configured for target `%s'" % (item.target))
        return False

    params = {
            'retry' : 60,
            'expire' : 3600,
        }

    if title is not None:
        params['title'] = title

    if priority is not None:
        params['priority'] = priority

    if callback is not None:
        params['callback'] = callback

    try:
        srv.logging.debug("Sending pushover notification to %s [%s]..." % (item.target, params))
        pushover(message=message, user=userkey, token=appkey, **params)
        srv.logging.debug("Successfully sent pushover notification")
    except Exception, e:
        srv.logging.warn("Error sending pushover notification to %s [%s]: %s" % (item.target, params, str(e)))
        return False

    return True

########NEW FILE########
__FILENAME__ = redispub
#!/usr/bin/env python
# -*- coding: utf-8 -*-

__author__    = 'Jan-Piet Mens <jpmens()gmail.com>'
__copyright__ = 'Copyright 2014 Jan-Piet Mens'
__license__   = """Eclipse Public License - v 1.0 (http://www.eclipse.org/legal/epl-v10.html)"""

HAVE_REDIS=True
try:
    import redis
except:
    HAVE_REDIS=False

def plugin(srv, item):
    ''' redispub. Expects addrs to contain (channel) '''

    srv.logging.debug("*** MODULE=%s: service=%s, target=%s", __file__, item.service, item.target)

    if HAVE_REDIS is False:
        srv.logging.warn("Redis is not installed")
        return False

    host = item.config.get('host', 'localhost')
    port = int(item.config.get('port', 6379))

    try:
        rp = redis.Redis(host, port)
    except Exception, e:
        srv.logging.warn("Cannot connect to redis on %s:%s : %s" % (host, port, str(e)))
        return False

    channel = item.addrs[0]
    text = item.message

    try:
        rp.publish(channel, text)
    except Exception, e:
        srv.logging.warn("Cannot publish to redis on %s:%s : %s" % (host, port, str(e)))
        return False

    return True

########NEW FILE########
__FILENAME__ = smtp
#!/usr/bin/env python
# -*- coding: utf-8 -*-

__author__    = 'Jan-Piet Mens <jpmens()gmail.com>'
__copyright__ = 'Copyright 2014 Jan-Piet Mens'
__license__   = """Eclipse Public License - v 1.0 (http://www.eclipse.org/legal/epl-v10.html)"""

import smtplib
from email.mime.text import MIMEText

def plugin(srv, item):

    srv.logging.debug("*** MODULE=%s: service=%s, target=%s", __file__, item.service, item.target)

    smtp_addresses = item.addrs

    server      = item.config['server']
    sender      = item.config['sender']
    starttls    = item.config['starttls']
    username    = item.config['username']
    password    = item.config['password']

    msg = MIMEText(item.message)
    msg['Subject']      = item.get('title', "%s notification" % (srv.SCRIPTNAME))
    msg['To']           = ", ".join(smtp_addresses)
    msg['From']         = sender
    msg['X-Mailer']     = srv.SCRIPTNAME

    try:
        srv.logging.debug("Sending SMTP notification to %s [%s]..." % (item.target, smtp_addresses))
        server = smtplib.SMTP(server)
        server.set_debuglevel(0)
        server.ehlo()
        if starttls:
            server.starttls()
        if username:
            server.login(username, password)
        server.sendmail(sender, smtp_addresses, msg.as_string())
        server.quit()
        srv.logging.debug("Successfully sent SMTP notification")
    except Exception, e:
        srv.logging.warn("Error sending notification to SMTP recipient %s [%s]: %s" % (item.target, smtp_addresses, str(e)))
        return False

    return True

########NEW FILE########
__FILENAME__ = sqlite
#!/usr/bin/env python
# -*- coding: utf-8 -*-

__author__    = 'Jan-Piet Mens <jpmens()gmail.com>'
__copyright__ = 'Copyright 2014 Jan-Piet Mens'
__license__   = """Eclipse Public License - v 1.0 (http://www.eclipse.org/legal/epl-v10.html)"""

HAVE_SQLITE=True
try:
    import sqlite3
except:
    HAVE_SQLITE=False

def plugin(srv, item):
    ''' sqlite. Expects addrs to contain (path, tablename) '''

    srv.logging.debug("*** MODULE=%s: service=%s, target=%s", __file__, item.service, item.target)

    if HAVE_SQLITE is False:
        srv.logging.warn("Sqlite3 is not installed")
        return False

    path  = item.addrs[0]
    table = item.addrs[1]
    try:
        conn = sqlite3.connect(path)
    except Exception, e:
        srv.logging.warn("Cannot connect to sqlite at %s : %s" % (path, str(e)))
        return False

    c = conn.cursor()
    try:
        c.execute('CREATE TABLE IF NOT EXISTS %s (payload TEXT)' % table)
    except Exception, e:
        srv.logging.warn("Cannot create sqlite table in %s : %s" % (path, str(e)))
        return False

    text = item.message

    try:
        c.execute('INSERT INTO %s VALUES (?)' % table, (text, ))
        conn.commit()
        c.close()
    except Exception, e:
        srv.logging.warn("Cannot INSERT INTO sqlite:%s : %s" % (table, str(e)))

    return True

########NEW FILE########
__FILENAME__ = syslog
#!/usr/bin/env python
# -*- coding: utf-8 -*-

__author__    = 'Fabian Affolter <fabian()affolter-engineering.ch>'
__copyright__ = 'Copyright 2014 Fabian Affolter'
__license__   = """Eclipse Public License - v 1.0 (http://www.eclipse.org/legal/epl-v10.html)"""

import syslog

def plugin(srv, item):
    """Transfer a message to a syslog server."""

    srv.logging.debug("*** MODULE=%s: service=%s, target=%s",
                        __file__, item.service, item.target)

    facilities = {
            'kernel' : syslog.LOG_KERN,
            'user'   : syslog.LOG_USER,
            'mail'   : syslog.LOG_MAIL,
            'daemon' : syslog.LOG_DAEMON,
            'auth'   : syslog.LOG_KERN,
            'LPR'    : syslog.LOG_LPR,
            'news'   : syslog.LOG_NEWS,
            'uucp'   : syslog.LOG_UUCP,
            'cron'   : syslog.LOG_CRON,
            'syslog' : syslog.LOG_SYSLOG,
            'local0' : syslog.LOG_LOCAL0,
            'local1' : syslog.LOG_LOCAL1,
            'local2' : syslog.LOG_LOCAL2,
            'local3' : syslog.LOG_LOCAL3,
            'local4' : syslog.LOG_LOCAL4,
            'local5' : syslog.LOG_LOCAL5,
            'local6' : syslog.LOG_LOCAL6,
            'local7' : syslog.LOG_LOCAL7
        }

    priorities = {
        'emerg'  : syslog.LOG_EMERG,
        'alert'  : syslog.LOG_ALERT,
        'crit'   : syslog.LOG_CRIT,
        'error'  : syslog.LOG_ERR,
        'warn'   : syslog.LOG_WARNING,
        'notice' : syslog.LOG_NOTICE,
        'info'   : syslog.LOG_INFO,
        'debug'  : syslog.LOG_DEBUG
    }

    options = {
        'pid'    : syslog.LOG_PID,
        'cons'   : syslog.LOG_CONS,
        'ndelay' : syslog.LOG_NDELAY,
        'nowait' : syslog.LOG_NOWAIT,
        'perror' : syslog.LOG_PERROR
    }

    facility  = facilities[item.addrs[0]]
    priority = priorities[item.addrs[1]]
    option = options[item.addrs[2]]
    message = item.message
    title = item.get('title', srv.SCRIPTNAME)

    syslog.openlog(title, option, facility)

    try:
        srv.logging.debug("Message is going to syslog facility %s..." \
            % ((item.target).upper()))
        syslog.syslog(priority, message)
        srv.logging.debug("Successfully sent")
        syslog.closelog()
    except Exception, e:
        srv.logging.error("Error sending to syslog: %s" % (str(e)))
        syslog.closelog()
        return False

    return True

########NEW FILE########
__FILENAME__ = twilio
#!/usr/bin/env python
# -*- coding: utf-8 -*-

__author__    = 'Jan-Piet Mens <jpmens()gmail.com>'
__copyright__ = 'Copyright 2014 Jan-Piet Mens'
__license__   = """Eclipse Public License - v 1.0 (http://www.eclipse.org/legal/epl-v10.html)"""

HAVE_TWILIO=True
try:
    from twilio.rest import TwilioRestClient
except ImportError:
    HAVE_TWILIO=False


def plugin(srv, item):
    ''' expects (accountSID, authToken, from, to) in addrs'''

    srv.logging.debug("*** MODULE=%s: service=%s, target=%s", __file__, item.service, item.target)
    if not HAVE_TWILIO:
        srv.logging.warn("twilio-python is not installed")
        return False

    try:
        account_sid, auth_token, from_nr, to_nr = item.addrs
    except:
        srv.logging.warn("Twilio target is incorrectly configured")
        return False

    text = item.message

    try:
        client = TwilioRestClient(account_sid, auth_token)
        message = client.messages.create(
                    body=text,
                    to=to_nr,
                    from_=from_nr)
        srv.logging.debug("Twilio returns %s" % (message.sid))
    except Exception, e:
        srv.logging.warn("Twilio failed: %s" % (str(e)))
        return False

    return True

########NEW FILE########
__FILENAME__ = twitter
#!/usr/bin/env python
# -*- coding: utf-8 -*-

__author__    = 'Jan-Piet Mens <jpmens()gmail.com>'
__copyright__ = 'Copyright 2014 Jan-Piet Mens'
__license__   = """Eclipse Public License - v 1.0 (http://www.eclipse.org/legal/epl-v10.html)"""

import twitter                    # pip install python-twitter

def plugin(srv, item):

    srv.logging.debug("*** MODULE=%s: service=%s, target=%s", __file__, item.service, item.target)

    twitter_keys = item.addrs

    twapi = twitter.Api(
        consumer_key        = twitter_keys[0],
        consumer_secret     = twitter_keys[1],
        access_token_key    = twitter_keys[2],
        access_token_secret = twitter_keys[3]
    )

    text = item.message[0:138]
    try:
        srv.logging.debug("Sending tweet to %s..." % (item.target))
        res = twapi.PostUpdate(text, trim_user=False)
        srv.logging.debug("Successfully sent tweet")
    except twitter.TwitterError, e:
        srv.logging.error("TwitterError: %s" % (str(e)))
        return False
    except Exception, e:
        srv.logging.error("Error sending tweet to %s: %s" % (item.target, str(e)))
        return False

    return True

########NEW FILE########
__FILENAME__ = xbmc
#!/usr/bin/env python
# -*- coding: utf-8 -*-

__author__    = 'Ben Jones <ben.jones12()gmail.com>'
__copyright__ = 'Copyright 2014 Ben Jones'
__license__   = """Eclipse Public License - v 1.0 (http://www.eclipse.org/legal/epl-v10.html)"""

import urllib
import urllib2
import base64
try:
    import json
except ImportError:
    import simplejson as json

def plugin(srv, item):

    srv.logging.debug("*** MODULE=%s: service=%s, target=%s", __file__, item.service, item.target)

    xbmchost = item.addrs[0]
    xbmcusername = None
    xbmcpassword = None

    if len(item.addrs) == 3:
        xbmcusername = item.addrs[1]
        xbmcpassword = item.addrs[2]

    title    = item.title
    message  = item.message
    image    = item.image

    jsonparams = {
        "jsonrpc" : "2.0",
        "method"  : "GUI.ShowNotification",
        "id"      : 1,
        "params"  : {
            "title"   : title,
            "message" : message,
            "image"   : image
        }
    }
    jsoncommand = json.dumps(jsonparams)

    url = 'http://%s/jsonrpc' % (xbmchost)
    try:
        srv.logging.debug("Sending XBMC notification to %s [%s]..." % (item.target, xbmchost))
        req = urllib2.Request(url, jsoncommand)
        req.add_header("Content-type", "application/json")
        if xbmcpassword is not None:
            base64string = base64.encodestring ('%s:%s' % (xbmcusername, xbmcpassword))[:-1]
            authheader = "Basic %s" % base64string
            req.add_header("Authorization", authheader)
        response = urllib2.urlopen(req)
        srv.logging.debug("Successfully sent XBMC notification")
    except urllib2.URLError, e:
        srv.logging.error("URLError: %s" % (str(e)))
        return False
    except Exception, e:
        srv.logging.error("Error sending XBMC notification to %s [%s]: %s" % (item.target, xbmchost, str(e)))
        return False

    return True

########NEW FILE########
__FILENAME__ = xmpp
#!/usr/bin/env python
# -*- coding: utf-8 -*-

__author__    = 'Fabian Affolter <fabian()affolter-engineering.ch>'
__copyright__ = 'Copyright 2014 Fabian Affolter'
__license__   = """Eclipse Public License - v 1.0 (http://www.eclipse.org/legal/epl-v10.html)"""

import xmpp     # pip install xmpp

def plugin(srv, item):
    """Send a message to XMPP recipient(s)."""

    srv.logging.debug("*** MODULE=%s: service=%s, target=%s", __file__, item.service, item.target)

    xmpp_addresses = item.addrs
    sender = item.config['sender']
    password = item.config['password']
    text = item.message

    try:
        srv.logging.debug("Sending message to %s..." % (item.target))
        for target in xmpp_addresses:
            jid = xmpp.protocol.JID(sender)
            connection = xmpp.Client(jid.getDomain(),debug=[])
            connection.connect()
            connection.auth(jid.getNode(), password, resource=jid.getResource())
            connection.send(xmpp.protocol.Message(target, text))
        srv.logging.debug("Successfully sent message")
    except Exception, e:
        srv.logging.error("Error sending message to %s: %s" % (item.target, str(e)))
        return False

    return True

########NEW FILE########
__FILENAME__ = zabbix
#!/usr/bin/env python
# -*- coding: utf-8 -*-

__author__    = 'Jan-Piet Mens <jpmens()gmail.com>'
__copyright__ = 'Copyright 2014 Jan-Piet Mens'
__license__   = """Eclipse Public License - v 1.0 (http://www.eclipse.org/legal/epl-v10.html)"""

try:
    import json
except ImportError:
    import simplejson as json
from vendor import ZabbixSender
import time

def plugin(srv, item):

    srv.logging.debug("*** MODULE=%s: service=%s, target=%s", __file__, item.service, item.target)

    try:
        trapper, port = item.addrs
    except:
        srv.logging.error("Module target is incorrectly configured")
        return False

    client = item.data.get('client', None)
    if client is None:
        srv.logging.warn("No client in item; ignoring")
        return False

    # If status_key is in item (set by function ZabbixData()), then we have to
    # add a host to Zabbix LLD, and the value of the message is 0/1 to indicate
    # host down/up
    status_key = item.data.get('status_key', None)
    if status_key is not None:
        status = item.message

        clients = []
        clients.append( { '{#MQTTHOST}' : client } )

        # {"data": [{"{#MQTTHOST}": "jog02"}]}
        lld_payload = json.dumps(dict(data = clients))

        try:
            # Add LLD for the client host to Zabbix
            sender = ZabbixSender.ZabbixSender(trapper, server_port = int(port))
            sender.AddData(host='MQTT_BUS', key='mqtt.discovery', value=lld_payload)
            res = sender.Send()
            sender.ClearData()

            if res and 'info' in res:
                srv.logging.debug("Trapper for LLD responds with %s" % res['info'])

                # Add status to the "status key". This must not happen too early,
                # or Zabbix will fail this value if the LLD for the host hasn't
                # been recorded. Attempt a sleep. FIXME
                time.sleep(3)  # FIXME
                sender.AddData(host=client, key=status_key, value=status)
                res = sender.Send()
                sender.ClearData()
                if res and 'info' in res:
                    srv.logging.debug("Trapper for STATUS responds with %s" % res['info'])

                return True
        except Exception, e:
            srv.logging.warn("Trapper responded: %s" % (str(e)))
            return False

    # We are adding a normal item/value via the trapper
    key = item.data.get('key', None)
    if client is None or key is None:
        srv.logging.warn("Client or Key missing in item; ignoring")
        return False

    value = item.message

    try:
        # Send item/value for host to the trapper
        sender = ZabbixSender.ZabbixSender(trapper, server_port = int(port))
        sender.AddData(host=client, key=key, value=value)
        res = sender.Send()
        sender.ClearData()

        if res and 'info' in res:
            srv.logging.debug("Trapper for client=%s, item=%s, value=%s responds with %s" % (client, key, value, res['info']))

            return True
    except Exception, e:
        srv.logging.warn("Trapper responded: %s" % (str(e)))

    return False

########NEW FILE########
__FILENAME__ = ZabbixSender
#!/usr/bin/env python
# -*- coding: utf-8 -*-
import socket
import struct

# Single file, imported from https://github.com/BlueSkyDetector/code-snippet/tree/master/ZabbixSender
# Lincense: DO WHAT THE FUCK YOU WANT TO PUBLIC LICENSE
#                     Version 2, December 2004
# Copyright (C) 2010 Takanori Suzuki

# JPM: s/simplejson/json/g

try:
    import json
except ImportError:
    import simplejson as json

class ZabbixSender:
    
    zbx_header = 'ZBXD'
    zbx_version = 1
    zbx_sender_data = {u'request': u'sender data', u'data': []}
    send_data = ''
    
    def __init__(self, server_host, server_port = 10051):
        self.server_ip = socket.gethostbyname(server_host)
        self.server_port = server_port
    
    def AddData(self, host, key, value, clock = None):
        add_data = {u'host': host, u'key': key, u'value': value}
        if clock != None:
            add_data[u'clock'] = clock
        self.zbx_sender_data['data'].append(add_data)
        return self.zbx_sender_data
    
    def ClearData(self):
        self.zbx_sender_data['data'] = []
        return self.zbx_sender_data
    
    def __MakeSendData(self):
        zbx_sender_json = json.dumps(self.zbx_sender_data, separators=(',', ':'), ensure_ascii=False).encode('utf-8')
        json_byte = len(zbx_sender_json)
        self.send_data = struct.pack("<4sBq" + str(json_byte) + "s", self.zbx_header, self.zbx_version, json_byte, zbx_sender_json)
    
    def Send(self):
        self.__MakeSendData()
        so = socket.socket()
        so.connect((self.server_ip, self.server_port))
        wobj = so.makefile(u'wb')
        wobj.write(self.send_data)
        wobj.close()
        robj = so.makefile(u'rb')
        recv_data = robj.read()
        robj.close()
        so.close()
        tmp_data = struct.unpack("<4sBq" + str(len(recv_data) - struct.calcsize("<4sBq")) + "s", recv_data)
        recv_json = json.loads(tmp_data[3])
        #JPM return recv_data
        return recv_json

if __name__ == '__main__':
    sender = ZabbixSender(u'127.0.0.1')
    for num in range(0,2):
        sender.AddData(u'HostA', u'AppX_Logger', u'sent data 第' + str(num))
    res = sender.Send()
    print sender.send_data
    print res

########NEW FILE########
