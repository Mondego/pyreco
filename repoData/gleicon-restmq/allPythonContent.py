__FILENAME__ = dispatcher
#!/usr/bin/python
# coding: utf-8
# author: Eduardo S. Scarpellini, <scarpellini@gmail.com>

import myconfig
import myloader


def exe(name, params):
	cfg = myconfig.read()
	cfgvalues = cfg.dispatcher()

	if cfgvalues.has_key(name):
		try:
			func = myloader.myimport(cfgvalues[name])
			func(params)
		except Exception, err:
			print "Error: %s" % err
	else:
		print "Error: No function for key \"%s\"" % name

########NEW FILE########
__FILENAME__ = dummyfuncs
#!/usr/bin/python
# coding: utf-8
# author: Eduardo S. Scarpellini, <scarpellini@gmail.com>

def generic(data):
	for key in data.keys():
		print " - [dummy] Value for key \"%s\": %s" % (key, data[key])

########NEW FILE########
__FILENAME__ = myconfig
#!/usr/bin/python
# coding: utf-8
# author: Eduardo S. Scarpellini, <scarpellini@gmail.com>

import os
import ConfigParser

class read():
	__cfgfile = "%s/config/main.cfg" % os.path.dirname(os.path.realpath("%s/.." % __file__))

	def __init__(self, cfgfile=__cfgfile):
		self.__config = ConfigParser.ConfigParser()
		self.__config.read(cfgfile)
		self.__cfgvalues = {}

	def restmq(self):
		try:
			self.__cfgvalues = {
				"host": self.__config.get("RESTMQ", "host"),
				"port": self.__config.get("RESTMQ", "port"),
				"queuename": self.__config.get("RESTMQ", "queuename"),
			}
		except ConfigParser.Error, err:
			print err

		return self.__cfgvalues

	def dispatcher(self):
		try:
			self.__cfgvalues = {
				"cpu": self.__config.get("DISPATCHER", "cpu"),
				"mem": self.__config.get("DISPATCHER", "mem"),
				"load": self.__config.get("DISPATCHER", "load"),
				"swap": self.__config.get("DISPATCHER", "swap"),
			}
		except ConfigParser.Error, err:
			print err

		return self.__cfgvalues

########NEW FILE########
__FILENAME__ = myloader
#!/usr/bin/python
# coding: utf-8
# author: Eduardo S. Scarpellini, <scarpellini@gmail.com>

def myimport(name):
	components = name.split(".")

	try:
		attrref = __import__(components[0])

		for component in components[1:]:
			attrref = getattr(attrref, component)
	except Exception, err:
		print "Error: %s" % err
	else:
		return attrref

########NEW FILE########
__FILENAME__ = simplemonitor
#!/usr/bin/python
# coding: utf-8
# author: Eduardo S. Scarpellini, <scarpellini@gmail.com>

import statgrab

def get_all_values():
	cpu  = statgrab.sg_get_cpu_percents()
	mem  = statgrab.sg_get_mem_stats()
	load = statgrab.sg_get_load_stats()
	swap = statgrab.sg_get_swap_stats()

	my_stats = {
		"cpu": {
			"kernel": cpu.kernel,
			"user": cpu.user,
			"iowait": cpu.iowait,
			"nice": cpu.nice,
			"swap": cpu.swap,
			"idle": cpu.idle,
		},
		"load": {
			"min1": load.min1,
			"min5": load.min5,
			"min15": load.min15,
		},
		"mem": {
			"used": mem.used,
			"cache": mem.cache,
			"free": mem.free,
			"total": mem.total,
		},
		"swap": {
			"used": swap.used,
			"free": swap.free,
			"total": swap.total,
		},
	}

	return my_stats

########NEW FILE########
__FILENAME__ = qconsumer
#!/usr/bin/python
# coding: utf-8
# author: Eduardo S. Scarpellini, <scarpellini@gmail.com>

# You can uncomment bellow lines if you dont want to set PYTHONPATH
import sys, os
scriptdir = os.path.dirname(os.path.realpath(__file__))
sys.path.append("%s/lib" % scriptdir)

import sys
import json
import myconfig
import dispatcher
from twisted.web import client
from twisted.python import log
from twisted.internet import reactor


class CometClient(object):
	def write(self, content):
		try:
			data = []
			content.rstrip()

			for line in content.split("\r\n"):
				if line:
					packet = json.loads(line)
					data.append( {"key": packet["key"], "value": json.loads(packet["value"])} )

		except Exception, err:
			log.err("Cannot decode JSON: %s" % str(err))
			log.err("MQ Return: %s" % content)
		else:
			for job in data:
				log.msg("*** Processing job \"%s\" ***" % job["key"])

				for task in job["value"].keys():
					log.msg("=> Dispatching task \"%s\"" % task)
					dispatcher.exe(task, job["value"][task])

	def close(self):
		pass


if __name__ == "__main__":
	cfg = myconfig.read()
	cfgvalues = cfg.restmq()

	log.startLogging(sys.stdout)

	client.downloadPage("http://%s:%s/c/%s" % (cfgvalues["host"], str(cfgvalues["port"]), cfgvalues["queuename"]), CometClient())
	reactor.run()

########NEW FILE########
__FILENAME__ = qfeeder
#!/usr/bin/python
# coding: utf-8
# author: Eduardo S. Scarpellini, <scarpellini@gmail.com>

# You can uncomment bellow lines if you dont want to set PYTHONPATH
import sys, os
scriptdir = os.path.dirname(os.path.realpath(__file__))
sys.path.append("%s/lib" % scriptdir)

import urllib, urllib2
import json
import myconfig
import simplemonitor


def post_data(host, port, queuename):
	try:
		params = urllib.urlencode({"queue":queuename, "value":json.dumps(simplemonitor.get_all_values())})

		request = urllib2.Request("http://%s:%s" % (host, str(port)), params)
		f = urllib2.urlopen(request)

		response = f.read()

		f.close()
	except urllib2.URLError, err:
		print err
	else:
		print "MQ Response: %s" % response


if __name__ == "__main__":
	cfg = myconfig.read()
	cfgvalues = cfg.restmq()

	post_data(cfgvalues["host"], cfgvalues["port"], cfgvalues["queuename"])

########NEW FILE########
__FILENAME__ = map
#!/user/bin/python
#
# map for restmq map/reduce example
# it counts a file's word and post to a queue called reducer
# output: {'filename':sys.argv[1], 'count': No of words}
#

import sys, json
import urllib, urllib2

QUEUENAME = 'reducer'

def wc(file):
    try:
        f = open(file, 'r')
        words = f.read()
        f.close()
    except Exception, e:
        print "Exception: %s" % e

    return len(words.split())

def enqueue(filename, count):
    try:
        msg={'filename': filename, 'count':count}
        data = urllib.urlencode({'queue':QUEUENAME, 'value':json.dumps(msg)})
        r = urllib2.Request('http://localhost:8888/', data)
        f = urllib2.urlopen(r)
        data = f.read()
        f.close()
    except urllib2.URLError, e:
        print e

    return "Sent: %s: %d" %(filename, count)

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print "Usage: map.py <file_to_count.txt>"
        sys.exit(-1)
    count = wc(sys.argv[1])
    print enqueue(sys.argv[1], count)

########NEW FILE########
__FILENAME__ = map_keyfreq
#!/user/bin/python
#
# map for restmq map/reduce example
# it counts a file's word and post to a queue called reducer
# output: {'filename':sys.argv[1], 'count': No of words}
#

import sys, json
import urllib, urllib2

QUEUENAME = 'reducer'

def wordfreq(file):
    try:
        f = open(file, 'r')
        words = f.read()
        f.close()
    except Exception, e:
        print "Exception: %s" % e
        return None
   
    wf={}
    wlist = words.split()
    for b in wlist:
        a=b.lower()
        if wf.has_key(a):
            wf[a]=wf[a]+1
        else:
           wf[a]=1
    return len(wf), wf

def enqueue(filename, count, wf):
    try:
        msg={"filename": filename, "count":count, "wordfreqlist":wf}
        data = urllib.urlencode({'queue':QUEUENAME, 'value':json.dumps(msg)})
        r = urllib2.Request('http://localhost:8888/', data)
        f = urllib2.urlopen(r)
        data = f.read()
        f.close()
    except urllib2.URLError, e:
        print e

    return "Sent: %s: %d" %(filename, count)

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print "Usage: map.py <file_to_count.txt>"
        sys.exit(-1)
    l, wfl = wordfreq(sys.argv[1])
    print enqueue(sys.argv[1], l, wfl)
    print "count: %d" % l     

########NEW FILE########
__FILENAME__ = reduce
#!/usr/bin/env python
# coding: utf-8

import sys
import json
from twisted.web import client
from twisted.python import log
from twisted.internet import reactor

QUEUENAME = 'reducer'


class CometClient(object):
    def __init__(self):
        self.count=0

    def write(self, content):
        try:
			content.rstrip('\n')
			c = content.split('\n')
			data=[]
			for line in c:
				if len(line) < 2: continue
				data.append(json.loads(line))
        except Exception, e:
            log.err("cannot decode json: %s" % str(e))
            log.err("json is: %s" % content)
        else:
            for v in data:
                    val=json.loads(v['value'])
                    log.msg("file: %s count: %s" % (val['filename'], val['count']))
                    self.count=self.count+val['count']
			
            log.msg("Total: %d" % self.count)

    def close(self):
        pass

if __name__ == "__main__":
    log.startLogging(sys.stdout)
    client.downloadPage("http://localhost:8888/c/%s" % QUEUENAME, CometClient())
    reactor.run()

########NEW FILE########
__FILENAME__ = reduce_keyfreq
#!/usr/bin/env python
# coding: utf-8

import sys
import json
from twisted.web import client
from twisted.python import log
from twisted.internet import reactor

QUEUENAME = 'reducer'


class CometClient(object):
    def __init__(self):
        self.count=0
        self.wordfreq={}

    def write(self, content):
        try:
			content.rstrip('\n')
			c = content.split('\n')
			data=[]
			for line in c:
				if len(line) < 2: continue
				data.append(json.loads(line))
        except Exception, e:
            log.err("cannot decode json: %s" % str(e))
            log.err("json is: %s" % content)
        else:
            jobs=[]
            for v in data:
                    val=json.loads(v['value'])
                    jobs.append(v['key'])
                    log.msg("file: %s count: %s" % (val['filename'], val['count']))
                    self.count=self.count+val['count']
                    twf = val['wordfreqlist']
                    for a in twf.keys():
                        b=a.lower()
                        if self.wordfreq.has_key(b):
                            self.wordfreq[b]=self.wordfreq[b]+twf[b]
                        else:
                            self.wordfreq[b]=twf[b]
						 						
            log.msg("Total: %d" % self.count)
            log.msg("Word Frequence: ", str(self.wordfreq))
            print "---------------- Job %s -----------------" % jobs
    def close(self):
        pass

if __name__ == "__main__":
    log.startLogging(sys.stdout)
    client.downloadPage("http://localhost:8888/c/%s" % QUEUENAME, CometClient())
    reactor.run()

########NEW FILE########
__FILENAME__ = test_collectd
#!/usr/bin/env python
# coding: utf-8

import sys
import json
from twisted.web import client
from twisted.python import log
from twisted.internet import reactor

class CometClient(object):
    def write(self, content):
        for json in content.splitlines():
            try:
                    data = json.loads(json)
                    data = data.get('value')
            except Exception, e:
                log.err("cannot decode json: %s" % str(e))
                log.err("json is: %s" % content)
            else:
                log.msg("got data ok: %s" % repr(data))

    def close(self):
        pass

if __name__ == "__main__":
    log.startLogging(sys.stdout)
    client.downloadPage("http://localhost:8888/c/collectd_data", CometClient())
    client.downloadPage("http://localhost:8888/c/collectd_event", CometClient())
    reactor.run()

########NEW FILE########
__FILENAME__ = test_comet
#!/usr/bin/env python
# coding: utf-8

import sys
import json
from twisted.web import client
from twisted.python import log
from twisted.internet import reactor

class CometClient(object):
    def write(self, content):
        try:
            data = json.loads(content)
        except Exception, e:
            log.err("cannot decode json: %s" % str(e))
            log.err("json is: %s" % content)
        else:
            log.msg("got data: %s" % repr(data))

    def close(self):
        pass

if __name__ == "__main__":
    log.startLogging(sys.stdout)
    client.downloadPage("http://localhost:8888/c/test", CometClient())
    reactor.run()

########NEW FILE########
__FILENAME__ = test_comet_curl
#! /usr/bin/env python
# -*- coding: utf-8 -*-

#
# Usage: python test-comet-curl.py <url> [No of simultaneous connections]
# Example: python test-comet-curl.py http://localhost:8888/c/test 100
# Adapted from retrieve-multi.py from PyCurl library
#
 
import sys
import pycurl

def pretty_printer(who):#, buf):
#    print "%s: %s" %(who)#, buf)
    print "-> %s" %(who)

try:
    import signal
    from signal import SIGPIPE, SIG_IGN
    signal.signal(signal.SIGPIPE, signal.SIG_IGN)
except ImportError:
    pass


# Get args
num_conn = 10

try:
    if len(sys.argv) < 2:
        print "Needs a URL"
        sys.exit(-1)
    url = sys.argv[1]
    print url
    if len(sys.argv) >= 3:
        num_conn = int(sys.argv[2])
except Exception, e:
    print e
    print "Usage: %s <url> [No of simultaneous connections]" % sys.argv[0]
    raise SystemExit



assert 1 <= num_conn <= 10000, "invalid number of concurrent connections"
print "PycURL %s (compiled against 0x%x)" % (pycurl.version, pycurl.COMPILE_LIBCURL_VERSION_NUM)
print "----- Getting", url, "URLs using", num_conn, "connections -----"


# Pre-allocate a list of curl objects
m = pycurl.CurlMulti()
m.handles = []
for i in range(num_conn):
    c = pycurl.Curl()
    c.fp = None
    c.setopt(pycurl.FOLLOWLOCATION, 1)
    c.setopt(pycurl.MAXREDIRS, 5)
    c.setopt(pycurl.CONNECTTIMEOUT, 30)
    c.setopt(pycurl.TIMEOUT, 300)
    c.setopt(pycurl.NOSIGNAL, 1)
    m.handles.append(c)


# Main loop
freelist = m.handles[:]
num_processed = 0
while num_processed < num_conn:
    while freelist:
        c = freelist.pop()
        c.setopt(pycurl.URL, url)
#        c.setopt(pycurl.WRITEFUNCTION, pretty_printer)
        m.add_handle(c)

    while 1:
        ret, num_handles = m.perform()
        if ret != pycurl.E_CALL_MULTI_PERFORM:
            break

    while 1:
        num_q, ok_list, err_list = m.info_read()
        for c in ok_list:
            c.fp.close()
            c.fp = None
            m.remove_handle(c)
            print "Success:", c.filename, c.url, c.getinfo(pycurl.EFFECTIVE_URL)
            freelist.append(c)
        for c, errno, errmsg in err_list:
            c.fp.close()
            c.fp = None
            m.remove_handle(c)
            print "Failed: ", c.filename, c.url, errno, errmsg
            freelist.append(c)
        num_processed = num_processed + len(ok_list) + len(err_list)
        if num_q == 0:
            break
    m.select(1.0)


# Cleanup
for c in m.handles:
    if c.fp is not None:
        c.fp.close()
        c.fp = None
    c.close()
m.close()


########NEW FILE########
__FILENAME__ = test_request
import requests

payload = {'value': 'el requesto',}
r = requests.post("http://localhost:8888/q/test", data=payload)
print r.text

########NEW FILE########
__FILENAME__ = twitter_trends
# simple twitter producer for restmq. point your browser to http://localhost:8888/c/twitter and 
# execute it with python twitter_trends.py 

import json
import pickle, re, os, urllib, urllib2


def get_url(url):
    try:
        f = urllib2.urlopen(url)
        data = f.read()
        f.close()
    except urllib2.URLError, e:
        print e.code
        print e.read()
    return data

def post_in_queue(subject, author, text):
    try:
        msg={'subject': subject, 'author':author, 'text':text}
        data = urllib.urlencode({'queue':'twitter', 'value':json.dumps(msg)})
        r = urllib2.Request('http://localhost:8888/', data)
        f = urllib2.urlopen(r)
        data = f.read()
        f.close()
    except urllib2.URLError, e:
        print e.code
        print e.read()
    print data

filename = "last_topic_ids.db"

if os.path.exists(filename):  
    last_topic_ids = pickle.load(file(filename, 'r+b'))  
else:  
    last_topic_ids = {}



trends_current = json.loads(get_url("http://search.twitter.com/trends/current.json"))
c = trends_current["trends"]

for a in c[c.keys()[0]]:
    if a['query'] not in last_topic_ids.keys():
        url = "http://search.twitter.com/search.json?q=%s" % (urllib.quote_plus(a['query']))
    else:
        url = "http://search.twitter.com/search.json?q=%s&since_id=%s" % (urllib.quote_plus(a['query']), last_topic_ids[a['query']])
    print "--------------------------------------"
    print "%s: %s" % (a['name'], url)
    statuses = json.loads(get_url(url))
    for s in statuses['results']:
        print repr(s)
        print "%s: %s" %(s['from_user'], s['text'])
        post_in_queue(a, s['from_user'], s['text'])    
    last_topic_ids[a['query']] = statuses['max_id']
    print "--------------------------------------"

print "Last topic and posts ids: %s" % last_topic_ids
pickle.dump(last_topic_ids, file(filename, 'w+b')) 


########NEW FILE########
__FILENAME__ = collectd
# coding: utf-8

import os.path
import cyclone.web
import cyclone.redis

import pkg_resources as pkg

from twisted.python import log
from twisted.internet import defer

from restmq import core

import json
import web

class CollectdRestQueueHandler(web.RestQueueHandler):

    @web.authorize("rest_producer")
    @defer.inlineCallbacks
    def post(self, queue):
        value = self.request.body
        if value is None:
            raise cyclone.web.HTTPError(400)
        if queue == 'data':
            content_type = self.request.headers.get('Content-Type')
            queue = 'collectd_data'
            if content_type == 'text/plain':
                try:
                    value = value.splitlines()
                    value = self.collectd_plaintext_parser(value)
                    value = json.dumps(value)
                except Exception, e:
                    log.msg("ERROR: %s" % e)
                    raise cyclone.web.HTTPError(503)
            elif content_type == 'application/json':
                pass
            else:
                log.msg("ERROR: Content-Type not expected %s" % content_type)
                raise cyclone.web.HTTPError(503)
        elif queue == 'event':
            queue = 'collectd_event'
            try:
                value = value.splitlines()
                event = value.pop()
                value = value[:-1]
                value = self.collectd_plaintext_parser(value)
                value.append({'event_text': event})
                value = json.dumps(value)
            except Exception, e:
                log.msg("ERROR: %s" % e)
                raise cyclone.web.HTTPError(503)
        else:
            raise cyclone.web.HTTPError(400)
        callback = self.get_argument("callback", None)

        try:
            result = yield self.settings.oper.queue_add(queue, value)
        except Exception, e:
            log.msg("ERROR: oper.queue_add('%s', '%s') failed: %s" % (queue, value, e))
            raise cyclone.web.HTTPError(503)

        if result:
            self.settings.comet.queue.put(queue)
            web.CustomHandler(self, callback).finish(result)
        else:
            raise cyclone.web.HTTPError(400)

    def collectd_plaintext_parser(self,lines):
        event_protocol = {'Severity': None,
                'Time': None,
                'Host': None,
                'Plugin': None,
                'Type': None,
                'TypeInstance': None,
                'DataSource': None,
                'CurrentValue': None,
                'WarningMin': None,
                'WarningMax': None,
                'FailureMin': None,
                'FailureMax': None,}
        collectd_data = []
        for line in lines:
            line = line.split(' ')
            if line[0] == 'PUTVAL':
                (host,plugin_instance,type_instance) = line[1].split('/')
                interval = line[2].split('=')[1]
                value = line[3]
                collectd_data.append({'host':host,
                   'plugin_instance':plugin_instance,
                   'type_instance':type_instance,
                   'interval':interval,'value':value})
            elif line[0].rstrip(':') in event_protocol:
                key = line[0].rstrip(':').lower()
                value = line[1]
                collectd_data.append({key: value})
        return collectd_data

class Collectd(web.Application):

    def __init__(self, acl_file, redis_host, redis_port, redis_pool, redis_db):
        handlers = [
            (r"/",       web.IndexHandler),
            (r"/q/(.*)", web.RestQueueHandler),
            (r"/c/(.*)", web.CometQueueHandler),
            (r"/p/(.*)", web.PolicyQueueHandler),
            (r"/j/(.*)", web.JobQueueInfoHandler),
            (r"/stats/(.*)",  web.StatusHandler),
            (r"/queue",  web.QueueHandler),
            (r"/control/(.*)",  web.QueueControlHandler),
            (r"/ws/(.*)",  web.WebSocketQueueHandler),
        ]

        handlers.append((r"/collectd/(.*)", CollectdRestQueueHandler))

        try:
            acl = web.ACL(acl_file)
        except Exception, e:
            log.msg("ERROR: Cannot load ACL file: %s" % e)
            raise RuntimeError("Cannot load ACL file: %s" % e)

        db = cyclone.redis.lazyConnectionPool(
            redis_host, redis_port,
            poolsize=redis_pool, dbid=redis_db)

        oper = core.RedisOperations(db)
        
        settings = {
            "db": db,
            "acl": acl,
            "oper": oper,
            "comet": web.CometDispatcher(oper),
            "static_path": pkg.resource_filename('restmq', 'static'),
            "template_path": pkg.resource_filename('restmq', 'templates'),
        }

        cyclone.web.Application.__init__(self, handlers, **settings)

########NEW FILE########
__FILENAME__ = core
# coding: utf-8

import types
import cyclone.escape
from twisted.internet import defer
import itertools

POLICY_BROADCAST = 1
POLICY_ROUNDROBIN = 2
QUEUE_STATUS = 'queuestat:'
QUEUE_POLICY = "%s:queuepolicy"
QUEUE_NAME = '%s:queue' 

class RedisOperations:
    """
    add element to the queue:
        - increments a UUID record 
        - store the object using a key as <queuename>:uuid
        - push this key into a list named <queuename>:queue
        - push this list name into the general QUEUESET
    get element from queue:
        - pop a key from the list
        - get and return, along with its key

    del element from the queue:
        - tricky part. there must be a queue_get() before. The object is out of the queue already. delete it.
        
    - TODO: the object may have an expiration instead of straight deletion
    - TODO: RPOPLPUSH can be used to put it in another queue as a backlog
    - TODO: persistence management (on/off/status)
    """

    def __init__(self, redis):
        self.STOPQUEUE = 0
        self.STARTQUEUE = 1 
        self.redis = redis
        self.policies = {
            "broadcast": POLICY_BROADCAST,
            "roundrobin": POLICY_ROUNDROBIN,
        }
        self.inverted_policies = dict([[v, k] for k, v in self.policies.items()])
        self.QUEUESET = 'QUEUESET' # the set which holds all queues
        self.PUBSUB_SUFIX = 'PUBSUB'

    def normalize(self, item):
        if isinstance(item, types.StringType):
            return item
        elif isinstance(item, types.UnicodeType):
            try:
                return item.encode("utf-8")
            except:
                raise ValueError("strings must be utf-8")
        else:
            raise ValueError("data must be utf-8")

    @defer.inlineCallbacks
    def authorize(self, queue, authkey):
        """ Authorize an operation for a given queue using an authentication key
            The basic mechanism is a check against Redis to see if key named AUTHKEY:<authkey value> exists
            If it exists, check against its content to see wheter the queue is authorized. 
            Authorization is either read/write a queue and create new queues
            queues and priv are lists in the authorization record
            returns boolean 
        """
        queue, authkey = self.normalize(queue), self.normalize(authkey)
        # get key and analyze {'queues': ['q1','q2','q3'], 'privs': ['create']}
        avkey = "AUTHKEY:%s" % authkey
        authval = yield self.redis.get(avkey.encode('utf-8'))
        if authval == None:
            defer.returnValue(False)
        try:
            adata = cyclone.escape.json_decode(authval)
        except Exception, e:
            defer.returnValue(None)
        if queue in adata['queues']:
            defer.returnValue(True)
        elif 'create' in adata['privs']:
            defer.returnValue(True)

        defer.returnValue(False)

    @defer.inlineCallbacks
    def _create_auth_record(self, authkey, queues=[], privs=[]):
        """ create a authorization record. queues and privs are lists """
        authkey = self.normalize(authkey)
        avkey = "AUTHKEY:%s" % authkey
        avkey = self.normalize(avkey)
        authrecord = {'queues': queues, 'privs':privs}

        res = yield self.redis.set(avkey, cyclone.escape.json_encode(authrecord))
        defer.returnValue(res)

    @defer.inlineCallbacks
    def queue_add(self, queue, value, ttl=None):
        queue, value = self.normalize(queue), self.normalize(value)

        uuid = yield self.redis.incr("%s:UUID" % queue)
        key = '%s:%d' % (queue, uuid)
        res = yield self.redis.set(key, value)
        if ttl is not None:
            res = yield self.redis.expire(key, ttl)
        internal_queue_name = QUEUE_NAME % self.normalize(queue)
        if uuid == 1: # TODO: use ismember()
            # either by checking uuid or by ismember, this is where you must know if the queue is a new one.
            # add to queues set
            res = yield self.redis.sadd(self.QUEUESET, queue)

            ckey = '%s:%s' % (QUEUE_STATUS, queue)
            res = yield self.redis.set(ckey, self.STARTQUEUE)

        res = yield self.redis.lpush(internal_queue_name, key)
        defer.returnValue(key)

    @defer.inlineCallbacks
    def queue_get(self, queue, softget=False): 
        """
            GET can be either soft or hard. 
            SOFTGET means that the object is not POP'ed from its queue list. It only gets a refcounter which is incremente for each GET
            HARDGET is the default behaviour. It POPs the key from its queue list.
            NoSQL dbs as mongodb would have other ways to deal with it. May be an interesting port.
            The reasoning behing refcounters is that they are important in some job scheduler patterns.
            To really cleanup the queue, one would have to issue a DEL after a hard GET.
        """
        policy = None
        queue = self.normalize(queue)
        lkey = QUEUE_NAME % self.normalize(queue)
        if softget == False:
            okey = yield self.redis.rpop(lkey)
        else:
            okey = yield self.redis.lindex(lkey, "-1")

        if okey == None:
            defer.returnValue((None, None))

        qpkey = QUEUE_POLICY % queue
        (policy, val) = yield self.redis.mget([qpkey, okey.encode('utf-8')])
        c=0
        if softget == True:
            c = yield self.redis.incr('%s:refcount' % okey.encode('utf-8'))

        defer.returnValue((policy or POLICY_BROADCAST, {'key':okey, 'value':val, 'count':c}))
    
    @defer.inlineCallbacks
    def queue_del(self, queue, okey):
        """
            DELetes an element from redis (not from the queue).
            Its important to make sure a GET was issued before a DEL. Its a kinda hard to guess the direct object key w/o a GET tho.
            the return value contains the key and value, which is a del return code from Redis. > 1 success and N keys where deleted, 0 == failure
        """
        queue, okey = self.normalize(queue), self.normalize(okey)
        val = yield self.redis.delete(okey)
        defer.returnValue({'key':okey, 'value':val})

    @defer.inlineCallbacks
    def queue_len(self, queue):
        lkey = QUEUE_NAME % self.normalize(queue)
        ll = yield self.redis.llen(lkey)
        defer.returnValue(ll)

    @defer.inlineCallbacks
    def queue_all(self):
        sm = yield self.redis.smembers(self.QUEUESET)
        defer.returnValue({'queues': sm})

    @defer.inlineCallbacks
    def queue_getdel(self, queue):
        policy = None
        queue = self.normalize(queue)
        lkey = QUEUE_NAME % self.normalize(queue)

        okey = yield self.redis.rpop(lkey) # take from queue's list
        if okey == None:
            defer.returnValue((None, False))

        okey = self.normalize(okey)
        nkey = '%s:lock' % okey
        ren = yield self.redis.rename(okey, nkey) # rename key

        if ren == None:
            defer.returnValue((None,None))

        qpkey = QUEUE_POLICY % queue
        (policy, val) = yield self.redis.mget(qpkey, nkey)
        delk = yield self.redis.delete(nkey)
        if delk == 0:
            defer.returnValue((None, None))
        else:
            defer.returnValue((policy, {'key':okey, 'value':val}))

    @defer.inlineCallbacks
    def queue_policy_set(self, queue, policy):
        queue, policy = self.normalize(queue), self.normalize(policy)
        if policy in ("broadcast", "roundrobin"):
            policy_id = self.policies[policy]
            qpkey = QUEUE_POLICY % queue
            res = yield self.redis.set(qpkey, policy_id)
            defer.returnValue(res)
            defer.returnValue({'queue': queue, 'response': res})
        else:
            defer.returnValue(None)

    @defer.inlineCallbacks
    def queue_policy_get(self, queue):
        queue = self.normalize(queue)
        qpkey = QUEUE_POLICY % queue
        val = yield self.redis.get(qpkey)
        name = self.inverted_policies.get(val, "unknown")
        defer.returnValue([val, name])

    @defer.inlineCallbacks
    def queue_tail(self, queue, keyno=10, delete_obj=False): 
        """
            TAIL follows on GET, but returns keyno keys instead of only one key.
            keyno could be a LLEN function over the queue list, but it lends almost the same effect.
            LRANGE could too fetch the latest keys, even if there was less than keyno keys. MGET could be used too.
            TODO: does DELete belongs here ?
            returns a tuple (policy, returnvalues[])
        """
        policy = None
        queue = self.normalize(queue)
        lkey = QUEUE_NAME % self.normalize(queue)
        multivalue = []
        for a in range(keyno):
            nk = yield self.redis.rpop(lkey)
            if nk != None:
                t = nk.encode('utf-8')
            else:
                continue

            if delete_obj == True:
                okey = self.normalize(t)
                t = '%s:lock' % okey
                ren = yield self.redis.rename(okey, t)
                if ren == None: continue

                v = yield self.redis.get(t)
                delk = yield self.redis.delete(t)
                if delk == 0: continue
            else:
                v = yield self.redis.get(t)

            multivalue.append({'key': okey, 'value':v.encode('utf-8')})

        qpkey = QUEUE_POLICY % queue
        policy = yield self.redis.get(qpkey)
        defer.returnValue((policy or POLICY_BROADCAST, multivalue))

    @defer.inlineCallbacks
    def queue_count_elements(self, queue):
        # this is necessary to evaluate how many objects still undeleted on redis.
        # seems like it triggers a condition which the client disconnects from redis
        try:
            lkey = '%s*' % self.normalize(queue)
            ll = yield self.redis.keys(lkey)
            defer.returnValue({"objects":len(ll)})
        except Exception, e:
            defer.returnValue({"error":str(e)})

    @defer.inlineCallbacks
    def queue_last_items(self, queue, count=10):
        """
            returns a list with the last count items in the queue
        """
        queue = self.normalize(queue)
        lkey = QUEUE_NAME % self.normalize(queue)
        multivalue = yield self.redis.lrange(lkey, 0, count-1)

        defer.returnValue( multivalue)

    @defer.inlineCallbacks
    def queue_changestatus(self, queue, status):
        """Statuses: core.STOPQUEUE/core.STARTQUEUE"""
        if status != self.STOPQUEUE and status != self.STARTQUEUE:
            defer.returnValue(None)

        key = '%s:%s' % (QUEUE_STATUS, queue)
        res = yield self.redis.set(key, status)
        defer.returnValue({'queue':queue, 'status':status})

    @defer.inlineCallbacks
    def queue_status(self, queue):
        key = '%s:%s' % (QUEUE_STATUS, queue)
        res = yield self.redis.get(key)
        defer.returnValue({'queue':queue, 'status':res})

    @defer.inlineCallbacks
    def queue_purge(self, queue):
        #TODO Must del all keys (or set expire)
        #it could rename the queue list, add to a deletion SET and use a task to clean it

        lkey = QUEUE_NAME % self.normalize(queue)
        res = yield self.redis.delete(lkey)
        defer.returnValue({'queue':queue, 'status':res})

    @defer.inlineCallbacks
    def pubsub(self, queue_name, content):
        key = "%s:%s" % (queue_name, self.PUBSUB_SUFIX)
        r = yield self.redis.publish(key, content)



    @defer.inlineCallbacks
    def queue_block_multi_get(self, queue_list): 
        """
            waits on a list of queues, get back with the first queue that
            received data.
            this makes the redis locallity very important as if there are other
            instances doing the same the policy wont be respected. OTOH it makes
            it fast by not polling lists and waiting x seconds
        """
        ql = [QUEUE_NAME % self.normalize(queue) for queue in queue_list]
        res = yield self.redis.brpop(ql) 
        if res is not None:
            q = self.normalize(res[1])                                            
            qpkey = QUEUE_POLICY % q
            (p, v) = yield self.redis.mget([qpkey, q])
            defer.returnValue((q, p, {'key':q, 'value':v}))
        else:
            defer.returnValue(None)
    
    @defer.inlineCallbacks
    def multi_queue_by_status(self, queue_list, filter_by=None):
        if filter_by is None: filter_by = self.STARTQUEUE
        ql = ["%s:%s" % (QUEUE_STATUS, self.normalize(queue)) for queue in queue_list]
        res = yield self.redis.mget(ql)
        qs = [True if r != filter_by else False for r in res]
        r = itertools.compress(ql, qs)
        defer.returnValue(list(r))

########NEW FILE########
__FILENAME__ = dispatch
# coding: utf-8

from twisted.internet import defer

class CommandDispatch:
    def __init__(self, ro):
        self.ro = ro

    @defer.inlineCallbacks
    def _add(self, jsonbody):
        """
            add an object to the queue
        """ 
        r={}
        try:
            e = yield self.ro.queue_add(jsonbody['queue'].encode("utf-8"), jsonbody['value'].encode("utf-8"))
            r['queue'] = jsonbody['queue']
            r['value'] = jsonbody['value']
            r['key'] = str(e)
            defer.returnValue(r)
        except Exception, e:
            defer.returnValue({"error":str(e)})
    
    @defer.inlineCallbacks
    def _get(self, jsonbody):
        """
            get an object from the queue. get is not destructive (wont pop the object out of the queue).
            check the 'count' attribute to see how many times a give object was requested
        """
        r={}
        try:
            p, e = yield self.ro.queue_get(jsonbody['queue'].encode("utf-8"), softget=True)
            if e is None:
                defer.returnValue({'error': 'empty queue'})
            else:
                r['queue'] = jsonbody['queue']
                r['value'] = e['value']
                r['key'] = e['key']
                r['count'] = e['count'] 
                defer.returnValue(r)
        except Exception, e:
            defer.returnValue({"error":str(e)})


    @defer.inlineCallbacks
    def _take(self, jsonbody):
        """
            get and delete an object from the queue. it is not really necessary as GET takes it out of the queue list, 
            so it will be basically hanging around redis with no reference. For now its a two pass operation, with no 
            guarantees and the same semantics as del
        """
        r={}
        try:
            p, e = yield self.ro.queue_getdel(jsonbody['queue'].encode("utf-8"))
            if e == False:
                defer.returnValue({"error":"empty queue"})
          
            if e == None:
                defer.returnValue({"error":"getdel error"})
            r['queue'] = jsonbody['queue']
            r['value'] = e['value']
            r['key'] = e['key']

            defer.returnValue(r)
        except Exception, e:
            defer.returnValue({"error":str(e)})

    @defer.inlineCallbacks
    def _del(self, jsonbody):
        """
            delete an object from the storage. returns key and a deleted attribute, false if the key doesn't exists'
        """
        r={}
        try:
            e = yield self.ro.queue_del(jsonbody['queue'].encode("utf-8"), jsonbody['key'])
            r['queue'] = jsonbody['queue']
            r['deleted'] = True if e['value'] > 0 else False
            r['key'] = e['key']
            defer.returnValue(r)
        except Exception, e:
            defer.returnValue({"error":str(e)})

        
    def execute(self, command, jsonbody):
        c = "_"+command
        if hasattr(self, c):
            m=getattr(self, c)
            return m(jsonbody)
        else:
            return None

########NEW FILE########
__FILENAME__ = syslogd
#!/usr/bin/python
# -*- coding: utf-8 -*-

# launchctl unload /System/Library/LaunchDaemons/com.apple.syslogd.plist
# launchctl load /System/Library/LaunchDaemons/com.apple.syslogd.plist

from twisted.internet import reactor, defer
from twisted.internet.protocol import Protocol, ServerFactory
from twisted.protocols.basic import LineReceiver
import time, re, math, json, os
from restmq import core
import cyclone.redis


#<22>Nov  1 00:12:04 gleicon-vm1 postfix/smtpd[4880]: connect from localhost[127.0.0.1]
severity = ['emerg', 'alert', 'crit', 'err', 'warn', 'notice', 'info', 'debug', ]

facility = ['kern', 'user', 'mail', 'daemon', 'auth', 'syslog', 'lpr', 'news',
    'uucp', 'cron', 'authpriv', 'ftp', 'ntp', 'audit', 'alert', 'at', 'local0',
    'local1', 'local2', 'local3', 'local4', 'local5', 'local6', 'local7',]

fs_match = re.compile("<(.+)>(.*)", re.I)

class SyslogdProtocol(LineReceiver):
    delimiter = '\n'
    def connectionMade(self):
        print 'Connection from %r' % self.transport

    def lineReceived(self, line):
        host = self.transport.getHost().host
        queue_name = "syslogd:%s" % host
        k = {}
        k['line'] = line.strip()
        (fac, sev) = self._calc_lvl(k['line'])
        k['host'] = host
        k['tstamp'] = time.time()
        k['facility'] = fac
        k['severity'] = sev
        self.factory.oper.queue_add(queue_name, json.dumps(k))

    def _calc_lvl(self, line):
        lvl = fs_match.split(line)
        if lvl and len(lvl) > 1:
            i = int(lvl[1])
            fac = int(math.floor(i / 8))
            sev = i - (fac * 8)
            return (facility[fac], severity[sev])
        return (None, None)

class SyslogdFactory(ServerFactory):
    protocol = SyslogdProtocol

    def __init__ (self, redis_host, redis_port, redis_pool, redis_db ):

        db = cyclone.redis.lazyConnectionPool(
            redis_host, redis_port,
            poolsize=redis_pool, dbid=redis_db)

        self.oper = core.RedisOperations(db)


########NEW FILE########
__FILENAME__ = web
# coding: utf-8

from os.path import dirname, abspath, join
import types
import base64
import hashlib
import os.path
import functools
import cyclone.web
import cyclone.redis
import cyclone.escape
import cyclone.websocket

from collections import defaultdict
from ConfigParser import ConfigParser

from twisted.python import log
from twisted.internet import task, defer, reactor

import pkg_resources as pkg

from restmq import core
from restmq import dispatch

class InvalidAddress(Exception):
    pass

class InvalidPassword(Exception):
    pass

def authorize(category):
    def decorator(method):
        @functools.wraps(method)
        def wrapper(self, *args, **kwargs):
            try:
                self.settings.acl.apply(self, category)
            except InvalidAddress:
                raise cyclone.web.HTTPError(401)
            except InvalidPassword:
                raise cyclone.web.HTTPAuthenticationRequired("Basic", "RestMQ Restricted Access")
            else:
                return method(self, *args, **kwargs)
        return wrapper
    return decorator


class CustomHandler(object):
    def __init__(self, handler, json_callback=None):
        self.handler = handler
        self.json_callback = json_callback

    def write(self, text):
        if not isinstance(text, types.StringType):
            text = cyclone.escape.json_encode(text)

        if isinstance(self.handler, cyclone.websocket.WebSocketHandler):
            self.handler.sendMessage(text)
        else:
            if self.json_callback:
                self.handler.write("%s(%s);\r\n" % (self.json_callback, text))
            else:
                self.handler.write(text+"\r\n")

    def flush(self):
        self.handler.flush()

    def finish(self, text=None):
        if buffer:
            self.write(text)
        self.handler.finish()


class IndexHandler(cyclone.web.RequestHandler):
    @authorize("rest_consumer")
    @defer.inlineCallbacks
    def get(self):
        try:
            queue = self.get_argument("queue", None)
            callback = self.get_argument("callback", None)
            if queue is None:
                self.redirect("/static/index.html")
                defer.returnValue(None)
        except Exception, e:
            print e

        try:
            policy, value = yield self.settings.oper.queue_get(queue)
        except Exception, e:
            log.msg("ERROR: oper.queue_get('%s') failed: %s" % (queue, e))
            cyclone.web.HTTPError(503)

        if value:
            CustomHandler(self, callback).finish(value)
        else:
            raise cyclone.web.HTTPError(404)

    @authorize("rest_producer")
    @defer.inlineCallbacks
    def post(self):
        queue = self.get_argument("queue")
        msg = self.get_argument("msg", None)
        value = self.get_argument("value", None)
        ttl = self.get_argument("ttl", None)

        if msg is None and value is None:
            raise cyclone.web.HTTPError(400)
        callback = self.get_argument("callback", None)

        try:
            result = yield self.settings.oper.queue_add(queue, value, ttl=ttl)
        except Exception, e:
            log.msg("ERROR: oper.queue_add('%s', '%s') failed: %s" % (queue, value, e))
            raise cyclone.web.HTTPError(503)

        if result:
            self.settings.comet.queue.put(queue)
            CustomHandler(self, callback).finish(result)
        else:
            raise cyclone.web.HTTPError(400)


class RestQueueHandler(cyclone.web.RequestHandler):
    """
        RestQueueHandler applies HTTP Methods to a given queue.
        GET /q/queuename gets an object out of the queue.
        POST /q/queuename inserts an object in the queue (I know, it could be PUT). The payload comes in the parameter body
        DELETE method purge and delete the queue. It will close all comet connections.
    """
    @authorize("rest_consumer")
    @defer.inlineCallbacks
    def get(self, queue):
        callback = self.get_argument("callback", None)

        if queue:
            try:
                policy, value = yield self.settings.oper.queue_get(queue)
            except Exception, e:
                log.msg("ERROR: oper.queue_get('%s') failed: %s" % (queue, e))
                raise cyclone.web.HTTPError(503)

            if value is None: raise cyclone.web.HTTPError(204)
            CustomHandler(self, callback).finish(value)
        else:
            try:
                allqueues = yield self.settings.oper.queue_all()
            except Exception, e:
                log.msg("ERROR: oper.queue_all() failed: %s" % e)
                raise cyclone.web.HTTPError(503)

            self.render("list_queues.html", route="q", extended_route="REST", allqueues=allqueues["queues"])

    @authorize("rest_producer")
    @defer.inlineCallbacks
    def post(self, queue):
        msg = self.get_argument("msg", None)
        value = self.get_argument("value", None)
        ttl = self.get_argument("ttl", None)
        if msg is None and value is None:
            raise cyclone.web.HTTPError(400)
        callback = self.get_argument("callback", None)

        try:
            result = yield self.settings.oper.queue_add(queue, msg or value, ttl=ttl)
        except Exception, e:
            log.msg("ERROR: oper.queue_add('%s', '%s') failed: %s" % (queue, msg or value, e))
            raise cyclone.web.HTTPError(503)

        if result:
            self.settings.comet.queue.put(queue)
            CustomHandler(self, callback).finish(result)
        else:
            raise cyclone.web.HTTPError(400)

    @authorize("rest_producer")
    @defer.inlineCallbacks
    def delete(self, queue):
        callback = self.get_argument("callback", None)
        clients = self.settings.comet.presence.get(queue, [])

        for conn in clients:
            try:
                conn.finish()
            except Exception, e:
                log.msg("ERROR: cannot close client connection: %s = %s" % (conn, e))

        try:
            result = yield self.settings.oper.queue_purge(queue)
        except Exception, e:
            log.msg("ERROR: oper.queue_purge('%s') failed: %s" % (queue, e))
            raise cyclone.web.HTTPError(503)

        CustomHandler(self, callback).finish(result)


class QueueHandler(cyclone.web.RequestHandler):
    """ QueueHandler deals with the json protocol"""

    def get(self):
        self.redirect("/static/help.html")

    @authorize("rest_producer")
    @defer.inlineCallbacks
    def post(self):
        msg = self.get_argument("msg", None)
        body = self.get_argument("body", None)

        if msg is None and body is None:
            raise cyclone.web.HTTPError(400)

        try:
            jsonbody = cyclone.escape.json_decode(msg or body)
            cmd = jsonbody["cmd"]
            assert cmd
        except:
            raise cyclone.web.HTTPError(400, "Malformed JSON. Invalid format.")

        try:
            result = yield dispatch.CommandDispatch(self.settings.oper).execute(cmd, jsonbody)
        except Exception, e:
            log.msg("ERROR: CommandDispatch/oper.%s('%s') failed: %s" % (cmd, jsonbody, e))
            raise cyclone.web.HTTPError(503)

        if result:
            self.finish(result)
        else:
            self.finish(cyclone.escape.json_encode({"error":"null resultset"}))


class CometQueueHandler(cyclone.web.RequestHandler):
    """
        CometQueueHandler is a permanent consumer for objects in a queue.
        it must only feed new objects to a permanent http connection
        deletion is not handled here for now.
        As each queue object has its own key, it can be done thru /queue interface
    """
    def _on_disconnect(self, why, handler, queue_name):
        try:
            self.settings.comet.presence[queue_name].remove(handler)
            if not len(self.settings.comet.presence[queue_name]):
                self.settings.comet.presence.pop(queue_name)
        except:
            pass

    @authorize("comet_consumer")
    @cyclone.web.asynchronous
    def get(self, queue):
        """
            this method is meant to build light http consumers emulating a subscription
            simple test: point the browser to /c/test
            execute python engine.py -p, check the browser to see if the object appears,
            then execute engine.py -c again, to make another object appear in the browser.
            Not it deletes objects from redis. To change it, set getdel to False on CometDispatcher
        """

        self.set_header("Content-Type", "text/plain")
        callback = self.get_argument("callback", None)

        handler = CustomHandler(self, callback)

        try:
            queue_name = queue.encode("utf-8")
        except:
            raise cyclone.web.HTTPError(400, "Invalid Queue Name")

        self.settings.comet.presence[queue_name].append(handler)
        self.notifyFinish().addCallback(self._on_disconnect, handler, queue_name)


class PolicyQueueHandler(cyclone.web.RequestHandler):
    @authorize("rest_consumer")
    @defer.inlineCallbacks
    def get(self, queue):
        callback = self.get_argument("callback", None)

        try:
            policy, policy_name = yield self.settings.oper.queue_policy_get(queue)
            r = {'queue':queue, 'value': policy_name}
            CustomHandler(self, callback).finish(r)
        except Exception, e:
            log.msg("ERROR: oper.queue_policy_get('%s') failed: %s" % (queue, e))
            raise cyclone.web.HTTPError(503)

    @authorize("rest_producer")
    @defer.inlineCallbacks
    def post(self, queue):
        policy = self.get_argument("policy")
        callback = self.get_argument("callback", None)

        try:
            result = yield self.settings.oper.queue_policy_set(queue, policy)
        except Exception, e:
            log.msg("ERROR: oper.queue_policy_set('%s', '%s') failed: %s" % (queue, policy, e))
            raise cyclone.web.HTTPError(503)

        CustomHandler(self, callback).finish(result)


class JobQueueInfoHandler(cyclone.web.RequestHandler):
    @defer.inlineCallbacks
    def get(self, queue):
        try:
            jobs = yield self.settings.oper.queue_last_items(queue)
            job_count = yield self.settings.oper.queue_len(queue)
            queue_obj_count = yield self.settings.oper.queue_count_elements(queue)
        except Exception, e:
            log.msg("ERROR: Cannot get JOB data: queue=%s, %s" % (queue, e))
            raise cyclone.web.HTTPError(503)

        self.render("jobs.html", queue=queue, jobs=jobs, job_count=job_count, queue_size=queue_obj_count)


class StatusHandler(cyclone.web.RequestHandler):
    @authorize("rest_consumer")
    @defer.inlineCallbacks
    def get(self, queue):
        self.set_header("Content-Type", "application/json")
        jsoncallback = self.get_argument("callback", None)
        res = {}

        if queue is None or len(queue) < 1:
            try:
                allqueues = yield self.settings.oper.queue_all()
            except Exception, e:
                log.msg("ERROR: oper.queue_all() failed: %s" % e)
                raise cyclone.web.HTTPError(503)
            ql = list(allqueues["queues"]) 
            res["queues"]={}
            for q in ql:
                qn = str(q)
                res["queues"][qn]={}
                res["queues"][qn]["name"]=qn
                res["queues"][qn]['len'] = yield self.settings.oper.queue_len(q)
                st = yield self.settings.oper.queue_status(q) 
                res["queues"][qn]['status'] = st["status"] if st['status'] else ""
                pl, pl_name = yield self.settings.oper.queue_policy_get(q)
                res["queues"][qn]['policy'] = pl if pl else ""

            res['redis'] = repr(self.settings.db)
            res['count'] = len(ql)
            if jsoncallback is not None: res = "%s(%s)" % (jsoncallback, res)
            self.finish(res)

        else:
            try:
                qlen = yield self.settings.oper.queue_len(queue)
            except Exception, e:
                log.msg("ERROR: oper.queue_len('%s') failed: %s" % (queue, e))
                raise cyclone.web.HTTPError(503)

            resp = "%s" % cyclone.escape.json_encode({
                "redis": repr(self.settings.db),
                "queue": queue, "len": qlen})
            
            if jsoncallback is not None: resp = "%s(%s)" % (jsoncallback, resp)
            self.finish(resp)


class CometDispatcher(object):
    def __init__(self, oper, del_obj=True):
        self.oper = oper
        self.queue = defer.DeferredQueue()
        self.presence = defaultdict(lambda: [])
        self.qcounter = defaultdict(lambda: 0)
        self.queue.get().addCallback(self._new_data)
        task.LoopingCall(self._auto_dispatch).start(1) # secs between checkings
        task.LoopingCall(self._counters_cleanup).start(30) # presence maintenance
        self.delete_objects = del_obj

    def _new_data(self, queue_name):
        self.dispatch(queue_name)
        self.queue.get().addCallback(self._new_data)

    def _auto_dispatch(self):
        for queue_name, handlers in self.presence.items():
            self.dispatch(queue_name, handlers)
    
    def _counters_cleanup(self):
        keys = self.qcounter.keys()
        for queue_name in keys:
            if not self.presence.has_key(queue_name):
                self.qcounter.pop(queue_name)

    @defer.inlineCallbacks
    def dispatch(self, queue_name, handlers=None):
        try:
            qstat = yield self.oper.queue_status(queue_name)
        except Exception, e:
            log.msg("ERROR: oper.queue_status('%s') failed: %s" % (queue_name, e))
            defer.returnValue(None)

        if qstat["status"] != self.oper.STARTQUEUE:
            defer.returnValue(None)

        handlers = handlers or self.presence.get(queue_name)
        if handlers:
            try:
                policy, contents = yield self.oper.queue_tail(queue_name, delete_obj = self.delete_objects)
                assert policy and contents and isinstance(contents, types.ListType)
            except:
                defer.returnValue(None)
             
            self._dump(handlers, contents, policy)

    def _dump(self, handlers, contents, policy = None):
        if policy is None:
            policy == core.POLICY_BROADCAST

        size = len(handlers)

        if policy == core.POLICY_BROADCAST:
            self._send(handlers, contents)

        elif policy == core.POLICY_ROUNDROBIN:
            idx = self.qcounter[queue_name] % size
            self._send((handlers[idx],), contents)
            self.qcounter[queue_name] += 1

    def _send(self, handlers, contents): 
        for handler in handlers:
            for content in contents:
                try:
                    handler.write(cyclone.escape.json_encode(content))
                    handler.flush()
                except Exception, e:
                    log.msg("ERROR: Cannot write to comet client: %s = %s" % (handler, e))


class QueueControlHandler(cyclone.web.RequestHandler):
    """ QueueControlHandler stops/starts a queue (pause consumers)"""

    @authorize("rest_consumer")
    @defer.inlineCallbacks
    def get(self, queue):
        self.set_header("Content-Type", "application/json")

        stats={}
        if queue:
            try:
                qstat = yield self.settings.oper.queue_status(queue)
            except Exception, e:
                log.msg("ERROR: oper.queue_status('%s') failed: %s" % (queue, e))
                raise cyclone.web.HTTPError(503)

            stats={"redis": repr(self.settings.db), "queue": queue, "status": qstat}

        else:
            try:
                allqueues = yield self.settings.oper.queue_all()
            except Exception, e:
                log.msg("ERROR: oper.queue_all() failed: %s" % e)
                raise cyclone.web.HTTPError(503)

            aq={}
            for q in allqueues:
                try:
                    aq[q] = yield self.settings.oper.queue_status(q)
                except Exception, e:
                    log.msg("ERROR: oper.queue_status('%s') failed: %s" % (q, e))
                    raise cyclone.web.HTTPError(503)

            stats={"redis": repr(self.settings.db), "queues": aq, "count": len(aq)}

        self.finish("%s\r\n" % cyclone.escape.json_encode(stats))

    @authorize("rest_producer")
    @defer.inlineCallbacks
    def post(self, queue):
        status = self.get_argument("status", None)
        jsoncallback = self.get_argument("callback", None)

        if status == "start":
            try:
                qstat = yield self.settings.oper.queue_changestatus(queue, self.settings.oper.STARTQUEUE)
            except Exception, e:
                log.msg("ERROR: oper.queue_changestatus('%s', STARTQUEUE) failed: %s" % (queue, e))
                raise cyclone.web.HTTPError(503)

        elif status == "stop":
            try:
                qstat = yield self.settings.oper.queue_changestatus(queue, self.settings.oper.STOPQUEUE)
            except Exception, e:
                log.msg("ERROR: oper.queue_changestatus('%s', STOPQUEUE) failed: %s" % (queue, e))
                raise cyclone.web.HTTPError(503)

        else:
            qstat = "invalid status: %s" % status

        resp = "%s" % cyclone.escape.json_encode({"stat": qstat })

        if jsoncallback is not None: resp = "%s(%s)" % (jsoncallback, resp)
        self.finish("%s\r\n" % resp)


class WebSocketQueueHandler(cyclone.websocket.WebSocketHandler):
    """
        Guess what, I had a fever, and the only prescription is websocket
    """
    def _disconnected(self, why, handler, queue_name):
        try:
            self.settings.comet.presence[queue_name].remove(handler)
            if not len(self.settings.comet.presence[queue_name]):
                self.settings.comet.presence.pop(queue_name)
        except:
            pass

    def headersReceived(self):
        # for authenticated websocket clientes, the browser must set a
        # cookie like this:
        #   document.cookie = "auth=user:password"
        #
        # see ACL.check_password for details
        try:
            self.settings.acl.apply(self, "websocket_consumer", websocket=True)
        except:
            raise cyclone.web.HTTPError(401)

    def connectionMade(self, queue):
        self.queue = queue
        handler = CustomHandler(self, None)

        try:
            queue_name = queue.encode("utf-8")
        except:
            raise cyclone.web.HTTPError(400, "Invalid Queue Name")

        self.settings.comet.presence[queue_name].append(handler)
        self.notifyFinish().addCallback(self._disconnected, handler, queue_name)

    def messageReceived(self, message):
        """
            same idea as COMET consumer, but using websockets. how cool is that ?
        """
        self.sendMessage(message)


class ACL(object):
    def __init__(self, filename):
        self.md5 = None
        self.filename = filename

        self.rest_producer = {}
        self.rest_consumer = {}
        self.comet_consumer = {}
        self.websocket_consumer = {}

        self.parse(True)

    def parse(self, firstRun=False):
        try:
            if(self.filename.startswith('/') or os.path.exists(self.filename)):
                fp = open(self.filename)
            else:
                import pkg_resources as pkg
                fp = pkg.resource_stream('restmq.assets', self.filename)
            
            md5 = hashlib.md5(fp.read()).hexdigest()

            if self.md5 is None:
                self.md5 = md5
            else:
                if self.md5 == md5:
                    return fp.close()

            fp.seek(0)
            cfg = ConfigParser()
            cfg.readfp(fp)
            fp.close()

        except Exception, e:
            if firstRun:
                raise e
            else:
                log.msg("ERROR: Could not reload configuration: %s" % e)
                return
        else:
            if not firstRun:
                log.msg("Reloading ACL configuration")

        for section in ("rest:producer", "rest:consumer", "comet:consumer", "websocket:consumer"):
            d = getattr(self, section.replace(":", "_"))

            try:
                hosts_allow = cfg.get(section, "hosts_allow")
                d["hosts_allow"] = hosts_allow != "all" and hosts_allow.split() or None
            except:
                d["hosts_allow"] = None

            try:
                hosts_deny = cfg.get(section, "hosts_deny")
                d["hosts_deny"] = hosts_deny != "all" and hosts_deny.split() or None
            except:
                d["hosts_deny"] = None

            try:
                username = cfg.get(section, "username")
                d["username"] = username
            except:
                d["username"] = None

            try:
                password = cfg.get(section, "password")
                d["password"] = password
            except:
                d["password"] = None

        reactor.callLater(60, self.parse)

    def check_password(self, client, username, password, websocket):
        try:
            if websocket is True:
                rusername, rpassword = client.get_cookie("auth").split(":", 1)
                assert username == rusername and password == rpassword

            else:
                authtype, authdata = client.request.headers["Authorization"].split()
                assert authtype == "Basic"
                rusername, rpassword = base64.b64decode(authdata).split(":", 1)
                assert username == rusername and password == rpassword
        except:
            raise InvalidPassword

    def apply(self, client, category, websocket=False):
        acl = getattr(self, category)
        require_password = acl["username"] and acl["password"]

        if acl["hosts_allow"]:
            for ip in acl["hosts_allow"]:
                if client.request.remote_ip.startswith(ip):
                    if require_password:
                        self.check_password(client,
                            acl["username"], acl["password"], websocket)
                        return
                    else:
                        return

            if acl["hosts_deny"] is None:
                raise InvalidAddress("ip address %s not allowed" % client.request.remote_ip)

        if acl["hosts_deny"]:
            for ip in acl["hosts_deny"]:
                if client.request.remote_ip.startswith(ip):
                    raise InvalidAddress("ip address %s not allowed" % client.request.remote_ip)

        if require_password:
            self.check_password(client, acl["username"], acl["password"], websocket)


class Application(cyclone.web.Application):
    def __init__(self, acl_file, redis_host, redis_port, redis_pool, redis_db):
        handlers = [
            (r"/",       IndexHandler),
            (r"/q/(.*)", RestQueueHandler),
            (r"/c/(.*)", CometQueueHandler),
            (r"/p/(.*)", PolicyQueueHandler),
            (r"/j/(.*)", JobQueueInfoHandler),
            (r"/stats/(.*)",  StatusHandler),
            (r"/queue",  QueueHandler),
            (r"/control/(.*)",  QueueControlHandler),
            (r"/ws/(.*)",  WebSocketQueueHandler),
        ]

        try:
            acl = ACL(acl_file)
        except Exception, e:
            log.msg("ERROR: Cannot load ACL file: %s" % e)
            raise RuntimeError("Cannot load ACL file: %s" % e)

        db = cyclone.redis.lazyConnectionPool(
            redis_host, redis_port,
            poolsize=redis_pool, dbid=redis_db)

        oper = core.RedisOperations(db)

        settings = {
            "db": db,
            "acl": acl,
            "oper": oper,
            "comet": CometDispatcher(oper),
            "static_path": pkg.resource_filename('restmq', 'static'),
            "template_path": pkg.resource_filename('restmq', 'templates'),
        }

        cyclone.web.Application.__init__(self, handlers, **settings)


########NEW FILE########
__FILENAME__ = collectd_plugin
#!/usr/bin/env python
# coding: utf-8

from zope.interface import implements
from twisted.python import usage
from twisted.plugin import IPlugin
from twisted.application import service, internet

import restmq.collectd

class Options(usage.Options):
    optParameters = [
        ["acl", "", "acl.conf", "acl configuration file for endpoints"],
        ["redis-host", "", "127.0.0.1", "hostname or ip address of the redis server"],
        ["redis-port", "", 6379, "port number of the redis server", int],
        ["redis-pool", "", 10, "connection pool size", int],
        ["redis-db", "", 0, "redis database", int],
        ["port", "", 8888, "port number to listen on", int],
        ["listen", "", "127.0.0.1", "interface to listen on"],
    ]

class ServiceMaker(object):
    implements(service.IServiceMaker, IPlugin)
    tapname = "collectd"
    description = "Collectd RESTful Message Broker"
    options = Options

    def makeService(self, options):
        return internet.TCPServer(options["port"],
            restmq.collectd.Collectd(options["acl"],
                options["redis-host"], options["redis-port"],
                options["redis-pool"], options["redis-db"]),
            interface=options["listen"])

serviceMaker = ServiceMaker()

########NEW FILE########
__FILENAME__ = restmq_plugin
#!/usr/bin/env python
# coding: utf-8

from zope.interface import implements
from twisted.python import usage
from twisted.plugin import IPlugin
from twisted.application import service, internet

import restmq.web

class Options(usage.Options):
    optParameters = [
        ["acl", "", "acl.conf", "acl configuration file for endpoints"],
        ["redis-host", "", "127.0.0.1", "hostname or ip address of the redis server"],
        ["redis-port", "", 6379, "port number of the redis server", int],
        ["redis-pool", "", 10, "connection pool size", int],
        ["redis-db", "", 0, "redis database", int],
        ["port", "", 8888, "port number to listen on", int],
        ["listen", "", "127.0.0.1", "interface to listen on"],
    ]

class ServiceMaker(object):
    implements(service.IServiceMaker, IPlugin)
    tapname = "restmq"
    description = "A RESTful Message Broker"
    options = Options

    def makeService(self, options):
        return internet.TCPServer(options["port"],
            restmq.web.Application(options["acl"],
                options["redis-host"], options["redis-port"],
                options["redis-pool"], options["redis-db"]),
            interface=options["listen"])

serviceMaker = ServiceMaker()

########NEW FILE########
__FILENAME__ = syslogd_plugin
#!/usr/bin/env python
# coding: utf-8

from zope.interface import implements
from twisted.python import usage
from twisted.plugin import IPlugin
from twisted.application import service, internet

import restmq.syslogd

class Options(usage.Options):
    optParameters = [
        ["redis-host", "", "127.0.0.1", "hostname or ip address of the redis server"],
        ["redis-port", "", 6379, "port number of the redis server", int],
        ["redis-pool", "", 10, "connection pool size", int],
        ["redis-db", "", 0, "redis database", int],
        ["port", "", 25000, "port number to listen on", int],
        ["listen", "", "127.0.0.1", "interface to listen on"],
    ]

class ServiceMaker(object):
    implements(service.IServiceMaker, IPlugin)
    tapname = "syslogd"
    description = "Syslogd RESTful Message Broker"
    options = Options

    def makeService(self, options):
        return internet.TCPServer(options["port"],
            restmq.syslogd.SyslogdFactory(options["redis-host"], options["redis-port"],
                options["redis-pool"], options["redis-db"]),
            interface=options["listen"])

serviceMaker = ServiceMaker()

########NEW FILE########
__FILENAME__ = bigmessage
#!/user/bin/python
#
# functional test for medium/big messages
# queue, check size both on restmq and redis
# make sure the queue is empty

import sys, json
import urllib, urllib2
import difflib
import redis
import hashlib
import time

QUEUENAME = 'bigmessages_%s' % time.time()

def str_checksum(str_m):
    return hashlib.md5(str_m).hexdigest()

def read_msg(file):
    try:
        f = open(file, 'r')
        words = f.read()
        f.close()
    except Exception, e:
        print "Exception: %s" % e
    return words

def enqueue(filename, content):
    try:
        msg={'filename': filename, 'len':len(content), 'content':content}
        data = urllib.urlencode({'queue':QUEUENAME, 'value':json.dumps(msg)})
        r = urllib2.Request('http://localhost:8888/', data)
        f = urllib2.urlopen(r)
        data = f.read()
        f.close()
    except urllib2.URLError, e:
        print e
    data = data.rstrip()
    ck_c = str_checksum(content)
    l_c = len(content)
    print '[Queued message] Key name: %s' % data
    print "[Queued message] checksum: %s size: %d bytes" % (ck_c, l_c)
    return (l_c, ck_c, data)

def dequeue():
    try:
        r = urllib2.Request('http://localhost:8888/q/%s' % QUEUENAME)
        f = urllib2.urlopen(r)
        data = f.read()
        f.close()
    except urllib2.URLError, e:
        print e
    data_dic = json.loads(data)
    dd2 = json.loads(data_dic['value'])
    content = dd2['content']
    ck_c = str_checksum(content)
    l_c = len(content)
    print "[Dequeued message] checksum: %s size: %d bytes" %(ck_c, l_c)
    return (l_c, ck_c, content)

def check_redis(redis_key):
    r = redis.Redis(host='localhost', port=6379, db=0)
    meh = r.get(redis_key)
    data_dic = json.loads(meh)
    content = data_dic['content']
    ck_c = str_checksum(content)
    l_c = len(content)
    print '[Redis] checksum: %s size for key %s: %d' % (ck_c, redis_key, l_c)
    return (l_c, ck_c)

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print "big message testing"
        print "Usage: bigmessage.py <file_to_count.txt>"
        sys.exit(-1)
    fname = sys.argv[1]
    content = read_msg(fname)
    (len_queued, ck_queued, redis_key) = enqueue(fname, content)
    (len_dequeued, ck_dequeued, ddq) = dequeue()
    (len_redis, ck_redis) = check_redis(redis_key)
    if (len_queued != len_dequeued): print 'Invalid dequeued message size'
    if (len_queued != len_redis): print 'Invalid redis message size'

#    d = difflib.Differ()
#    diff = d.compare(content.split(','), ddq.split(','))
#    print '\n'.join(list(diff))


########NEW FILE########
__FILENAME__ = restmq-test
# coding: utf-8
# author: Eduardo S. Scarpellini, <scarpellini@gmail.com>
from net.grinder.script.Grinder import grinder
from net.grinder.script import Test
from net.grinder.plugin.http import HTTPRequest, HTTPPluginControl
from HTTPClient import NVPair
from java.util import Random

# Import "random" module from the Jython lib path
import sys
#sys.path.append("/opt/jython2.5.1/Lib")
#import random
randomizer = Random()


# Parameters
RESTMQ_URL = "http://localhost:8888/"
QUEUENAME  = "PERFTEST"
VALUES     = [
	"fagtejmanP09as78d897891eidEnAidNa",
	"OdnutonbapHyGracasd8789asd0123Atvo",
	"igmesyaHenUrnoranGio",
	"lybDitdonCibW897989ewJedth",
	"CiUdlynJeHeySasd987asd8hkasd89ebjalky",
	"nafAtcepdetM_asdiu8aipgapGej",
	"itidpyctEijusas9d8821111hcoiWun",
	"yatnuWibAndOrHaubNqw0e897891ud",
	"CydIpavAycsEibsEiasd081xye",
	"dicedInBebEwatAigasd087Dab",
	1.1273,
	0.1771,
	9012830,
	1098,
	193,
	2.127398,
	67651,
	1218937829,
	981,
	8711
]

def rndIndex():
    return VALUES[randomizer.nextInt() % len(VALUES)]

# Logging
log = grinder.logger.output
out = grinder.logger.TERMINAL

test1 = Test(1, "enqueue")
test2 = Test(2, "dequeue")
request1 = test1.wrap(HTTPRequest())
request2 = test2.wrap(HTTPRequest())

# Test Interface
class TestRunner:
	def __call__(self):
                post_data={}
                for pt in ['1', '2', '3', '4', '5', 'X', 'K', 'Y', 'W', 'Z']:
                    post_data['FAKENAME'+pt]=rndIndex()

		log("Sending data (enqueuing): %s" % post_data )

		post_parameters = (
			NVPair("queue", QUEUENAME),
			NVPair("value", str(post_data)),
		)
		result1 = request1.POST(RESTMQ_URL, post_parameters)

		result2 = request2.GET("%s/q/%s" % (RESTMQ_URL.rstrip("/"), QUEUENAME))
		log("Getting data (dequeuing): %s" % result2.getText())

########NEW FILE########
__FILENAME__ = restmq_engine
#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import json
import cyclone.redis
from restmq import core
from optparse import OptionParser
from twisted.internet import defer, reactor
        
QUEUENAME = 'test'

@defer.inlineCallbacks
def test_operations(opt, args):
    """ 
        test and docs for a redis based queue engine in python
        based on tx-redis
    """
    try:
        rd = yield cyclone.redis.RedisConnectionPool()
    except Exception, e:
        print "Error creating redis pool %s" % e
        defer.returnValue(None)

    ro = core.RedisOperations(rd)

    if opt.producer == True:
        print "Running as producer"
        uuid = yield ro.queue_add(QUEUENAME, json.dumps({'value':'a value'}))
        print 'uuid: %s' % uuid

    if opt.consumer == True:
    	print "Running as consumer"
        (policy, ret) = yield ro.queue_get( QUEUENAME)
        if ret != None:
            print "value: %s" % ret['value'] #json.loads(ret['value'])
            print "policy: %s" % policy
        else:
            print 'empty queue'

    if opt.stats == True:
        ll = yield ro.queue_stats(QUEUENAME)
        print "list len: %s" % ll
  
        sm = yield ro.queue_all()
        print "all queues: %s" % sm

    if opt.non_consumer == True:
    	print "Running as consumer"
        (policy, ret) = yield ro.queue_get( QUEUENAME, softget=True)
        if ret != None:
            print "value: %s" % ret['value'] #json.loads(ret['value'])
            print "policy: %s" % policy
        else:
            print 'empty queue'

    if opt.get_policy == True:
    	print "GET queue policy"
        ret = yield ro.queue_policy_get(QUEUENAME)
        print repr(ret)

        if ret != None:
            print "value: %s" % ret['value'] #json.loads(ret['value'])
        else:
            print 'empty queue policy'

    if opt.set_policy == True:
    	print "SET queue policy"
        resp = yield ro.queue_policy_set(QUEUENAME, "roundrobin")
        print 'resp: %s' % resp

    if opt.get_del == True:
    	print "Running as getdel consumer"
        (policy, ret) = yield ro.queue_getdel(QUEUENAME)
        if ret != None and ret != False:
            print "value: %s" % ret['value'] #json.loads(ret['value'])
            print "policy: %s" % policy
        else:
            print 'empty queue'

    if opt.tail_mget == True:
    	print "Running as tail multiget"
        (policy, ret) = yield ro.queue_tail(QUEUENAME)
        if ret != None and ret != False:
            print "value: %s" % repr(ret) #json.loads(ret['value'])
            print "policy: %s" % policy
        else:
            print 'empty queue'

    if opt.count_objects == True:
    	print "Running as count object"
        ret = yield ro.queue_count_elements(QUEUENAME)
        if ret != None and ret != False:
            print "value: %s" % repr(ret) #json.loads(ret['value'])
        else:
            print 'empty queue'

    if opt.queue_last_items == True:
    	print "Running as count object"
        ret = yield ro.queue_last_items(QUEUENAME)
        if ret != None and ret != False:
            print "value: %s" % repr(ret) #json.loads(ret['value'])
        else:
            print 'empty queue'

    if opt.authorize == True:
    	print "Running authorization"
        ret = yield ro.authorize(QUEUENAME, 'aaa123')
        print ret
    
    if opt.create_auth == True:
    	print "Creating auth record"
        ret = yield ro._create_auth_record('aaa123', [QUEUENAME], ['create'])
        print ret


def main():
    p = OptionParser()
    p.add_option("-p", "--producer", action="store_true", dest="producer", help="Run as producer")
    p.add_option("-c", "--consumer", action="store_true", dest="consumer", help="Run as consumer")
    p.add_option("-g", "--non-consumer", action="store_true", dest="non_consumer", help="Run as a non destructive consumer")
    p.add_option("-s", "--stats", action="store_true", dest="stats", help="Stats")
    p.add_option("-q", "--get_policy", action="store_true", dest="get_policy", help="Get queue policy")
    p.add_option("-j", "--set_policy", action="store_true", dest="set_policy", help="Set queue policy")
    p.add_option("-k", "--get_delete", action="store_true", dest="get_del", help="Consumer get del")
    p.add_option("-t", "--tail_multiget", action="store_true", dest="tail_mget", help="Multi get 10 keys")
    p.add_option("-u", "--count_objects", action="store_true", dest="count_objects", help="Count objects of a given queue")
    p.add_option("-i", "--list_last_items", action="store_true", dest="queue_last_items", help="List the latest queue items")
    # authorization tests
    p.add_option("-a", "--authorize", action="store_true", dest="authorize", help="authorize a key for queues/privileges")
    p.add_option("-r", "--create_auth", action="store_true", dest="create_auth", help="Create an authorization record")


    (opt, args)=p.parse_args(sys.argv[1:])

    test_operations(opt, args).addCallback(lambda ign: reactor.stop())


if __name__ == "__main__":
	main()
	reactor.run()

########NEW FILE########
