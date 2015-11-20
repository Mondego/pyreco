__FILENAME__ = megaphone
#!/usr/bin/env python
import json
import sys
import os
from bottle import Bottle
import time
import urllib2
import shutil
import socket
import bottle
from ConfigParser import SafeConfigParser
import logging
logging.basicConfig()

app = Bottle()

_basedir = os.path.abspath(os.path.dirname(__file__))
config = SafeConfigParser()
config.read('%s/megaphone.conf' % _basedir)

DEBUG = config.getboolean('settings', 'DEBUG')
RELOADER = config.getboolean('settings', 'RELOADER')
CACHEDIR = config.get('settings', 'CACHEDIR')
CACHEFILE = config.get('settings', 'CACHEFILE')
CACHE = "%s/%s" % (CACHEDIR, CACHEFILE)
LISTEN = config.get('settings', 'LISTEN')
PORT = config.get('settings', 'PORT')
TIMEOUT = float(config.get('settings', 'TIMEOUT'))

def bug(msg):
    if DEBUG:
        print "DEBUG: %s" % msg

class MyException(Exception):
    pass

# zookeeper reporting
# if we find ./zk.conf or /etc/zktools/zk.conf, we should try to report to
# zookeeper
enablezk = "false"
if os.path.exists('./zk.conf'):
    enablezk = "true"
    bug("using config ./zk.conf")
    parser = SafeConfigParser()
    parser.read('./zk.conf')
elif os.path.exists('/etc/zktools/zk.conf'):
    enablezk = "true"
    bug("Using config /etc/zktools/zk.conf")
    parser = SafeConfigParser()
    parser.read('/etc/zktools/zk.conf')

if enablezk == "true":
    from kazoo.client import KazooClient
    from kazoo.retry import KazooRetry
    from kazoo.exceptions import KazooException
    env = parser.get('default', 'env').strip()
    use_exhibitor = parser.getboolean(env, 'use_exhibitor')
    zkservers = parser.get(env, 'servers').strip()
    if use_exhibitor:
    	exhibitor = "http://%s/exhibitor/v1/cluster/list/" % (zkservers)
	try:
		if DEBUG:
			print "Connecting to: %s" % exhibitor
		servers = ""
    		zkdata = json.load(urllib2.urlopen(exhibitor, timeout = TIMEOUT))
		for z in zkdata['servers']:
			servers += "%s:%s," % (z, zkdata['port'])
		servers = servers[:-1]
		if DEBUG:
			print servers
	except:
		print "ERROR: unable to get server list from exhibitor! Aborting!"
		sys.exit(1)
    else:
    	servers = "%s" % (zkservers)
    zkroot = parser.get(env, 'root').strip()
    host = socket.getfqdn()
    kr = KazooRetry(max_tries=3)
    zk = KazooClient(hosts=servers)

    def storecache(path,data):
	try:
		if kr(zk.exists, path) == None:
			kr(zk.create, path, value=data, makepath=True)
		else:
			kr(zk.set_data, path, value=data)
	except KazooException:
		cancelled = False
		raise

    def addzk(path):
	if kr(zk.exists, path) == None:
		try:
			kr(zk.create, path, ephemeral=True, makepath=True)
		except KazooException:
			cancelled = False
			raise

    def rmzk(path):
	if kr(zk.exists, path) != None:
		try:
			kr(zk.delete, path)
		except KazooException:
			cancelled = False
			raise

    def loadzk(data):
        if DEBUG:
            print data
        zk.start()
        for i in data.keys():
            if DEBUG:
                print data[i]
            path = '%s/envs/%s/applications/%s/servers/%s' % (zkroot, env, i, host)
	    addzk(path)	
else:
    # if zookeeper is disabled, just output if DEBUG is set to True
    def nozk(data):
	bug("zookeeper support not enabled, not submitting zNode data for record:")
	if DEBUG:
		print data
    def addzk(path):
	nozk(path)
    def rmzk(path):
	nozk(path)
    def loadzk(data):
	nozk(data)

# end zookeeper reporting

t = time.localtime()
ts = time.strftime('%Y-%m-%dT%H:%M:%S%Z', t)

# Change working directory so relative paths (and template lookup) work again
root = os.path.join(os.path.dirname(__file__))
sys.path.insert(0, root)

if not os.path.isdir(CACHEDIR):
    CACHE = "/tmp/megaphone.json"

if os.path.isfile(CACHE) == True:
    bug("CACHE: %s" % CACHE)
    with open(CACHE) as data_file:
        checks = json.load(data_file)
        loadzk(checks)
else:
    checks = {}

# we shouldn't write to tmp by default because our megaphone.json could get
# deleted by tmpwatch, etc.
if CACHE == "/tmp/megaphone.json":
    # i was originally going to use the --global override to inject a message, but decided against it
    # checks['--global'] = "ERROR: cache set to %s, will likely get clobbered by tmpwatch!" % CACHE
    print "WARNING: cache set to %s, could get clobbered by tmpwatch!" % CACHE


def writecache(data):
    try:
        if os.path.isfile(CACHE) == True:
            backup = "%s.backup" % CACHE
            shutil.copyfile(CACHE, backup)
        with open(CACHE, 'w') as outfile:
            json.dump(data, outfile)
            loadzk(data)
	    #path = '%s/machines/%s/content/megaphone' % (zkroot, host)
	    #storecache(path, data)
    except:
        # it's bad news if we can't create a cache file to reload on restart,
        # throw an error in megaphone!
        print "ERROR: cache creation failed!"
        checks['--global'] = "ERROR: cache creation failed!"
        writecache(checks)

# generate nested python dictionaries, copied from here:
# http://stackoverflow.com/questions/635483/what-is-the-best-way-to-implement-nested-dictionaries-in-python


class AutoVivification(dict):

    """Implementation of perl's autovivification feature."""

    def __getitem__(self, item):
        try:
            return dict.__getitem__(self, item)
        except KeyError:
            value = self[item] = type(self)()
            return value
# read a file


def readfile(fname):
    try:
        f = open(fname, 'r')
        o = f.read()
        return re.sub(r'\0', ' ', o)
        f.close()
    except:
        msg = "Critical: reading %s failed!" % fname
        return msg

# read a megaphone compatible status url and return the object
def readstatus(url):
    validstatus = ["OK", "Unknown", "Warning", "Critical"]
    try:
        # this is to support status somewhere other than 'status' under the root of a service
        # {"id": "ok2_status", "url": {"addr": "http://localhost:18999/status", "jsonpath": "megaphone/status"}}
        if isinstance(url, dict):
                data = AutoVivification()
                if 'addr' not in url:
			data['status'] = "Critical"
                        data['message'] = "ERROR: couldn't find addr in url, nothing to check"
		else:
                  	if 'jsonpath' in url:
                        	tdata = json.load(urllib2.urlopen(url['addr'], timeout = TIMEOUT))
                        	q = "tdata"
                        	for i in url['jsonpath'].split("/"):
                                	if i:  
                                        	q += "['%s']" % i
                        	data['status'] = eval(q)
                        	data['date'] = ts
                        	msg = "Status from path %s: %s" % (url['jsonpath'], eval(q))
                        	data['message'] = msg
                  	else:  
                        	data = json.load(urllib2.urlopen(url['addr'], timeout = TIMEOUT))
		  	if 'statusoverride' in url:
				if url['statusoverride'] not in validstatus:
					data['status'] = "Critical"
					data['message'] = "ERROR: invalid status '%s' written to statusoverride!" % url['statusoverride']
				else:
					data['status'] = url['statusoverride']
					data['message'] = "NOTICE: statusoverride used!"
        else:  
                data = json.load(urllib2.urlopen(url, timeout = TIMEOUT))
	if data["status"] not in validstatus:
		data['status'] = "Critical"
		data['message'] = "ERROR: status value '%s' not valid!" % data["status"]
        return data
    except:
        data = AutoVivification()
        data['status'] = "Critical"
        data['date'] = ts
        msg = "unable to connect to: %s" % url
        data['message'] = msg
        return data

# list all megaphone checks

@app.get('/checks')
def list():
    data = AutoVivification()
    return checks

# add a check: {"id": "ok_status", "url": "http://localhost:18999/status"}

@app.post('/checks')
def add_submit():
    data = bottle.request.body.readline()
    if not data:
        app.abort(400, 'No data received')
    entity = json.loads(data)
    if 'id' not in entity:
        app.abort(400, 'No id specified')
    try:
        checks[entity["id"]] = entity["url"]
        writecache(checks)
    except:
        app.abort(400, "Error adding new check!")

# delete a check: {"id": "ok_status"}

@app.delete('/checks/:s')
def delcheck(s):
    try:
        del checks[s]
        writecache(checks)
	path = '%s/envs/%s/applications/%s/servers/%s' % (zkroot, env, s, host)
	rmzk(path)
    except:
        app.abort(400, "Error deleting check!")

# proxy the response of a status url megaphone is checking

@app.get('/checks/:s')
def checkshow(s):
    return readstatus(checks[s])

# generate the main status output

@app.get('/')
def status():
    data = AutoVivification()
    # setting a global override. If there is a check with the id '--global',
    # only respect that. Always return Critical with a message of whatever is
    # in the url object
    if "--global" in checks.keys():
        data['status'] = "Critical"
        data['message'] = checks['--global']
        data['date'] = ts
        return data
    # if there's no global override, parse the rest of the checks.
    else:
        # trying to conform to current monitoring status guidelines
        # http://nagiosplug.sourceforge.net/developer-guidelines.html#PLUGOUTPUT
        statusc = {
            "Warning":  0,
            "Critical":  0,
            "Unknown":  0,
        }
        E = 0
        msg = ""
        for i in checks.keys():
        # for all checks we're monitoring, capture the state and the message
        # figure out something to do with date testing
        # like throw an error if current date is > 5min from returned date
	    path = '%s/envs/%s/applications/%s/servers/%s' % (zkroot, env, i, host)
            x = readstatus(checks[i])
            if x['status'] == "Warning":
                if 'message' not in x.keys():
                    mymsg = 'Detected Warning state [no message specified]'
                else:
                    mymsg = x['message']
                statusc['Warning'] = statusc['Warning'] + 1
                msg += "%s:%s:%s|" % (i, x['status'], mymsg)
		rmzk(path)
            elif x['status'] == "Critical":
                if 'message' not in x.keys():
                    mymsg = 'Detected Critical state [no message specified]'
                else:
                    mymsg = x['message']
                statusc['Critical'] = statusc['Critical'] + 1
                msg += "%s:%s:%s|" % (i, x['status'], mymsg)
		rmzk(path)
            elif x['status'] == "OK":
                # Throw it away
                throwaway = "ok"
		addzk(path)
            else:
                if 'message' not in x.keys():
                    mymsg = 'Detected Unknown state [no message specified]'
                else:
                    mymsg = x['message']
                # things aren't Warning, Critical, or OK so something else is
                # going on
                statusc['Unknown'] = statusc['Unknown'] + 1
                msg += "%s:%s:%s|" % (i, x['status'], mymsg)
		rmzk(path)

        # set the status to the most critical value in the order: Unknown, Warning, Critical
        # i.e. if WARNING is the worst issue, i present that, but if ERROR and
        # WARNING are both present use ERROR
        if statusc['Unknown'] > 0:
            data['status'] = "Unknown"
            E = 1
        if statusc['Warning'] > 0:
            data['status'] = "Warning"
            E = 1
        if statusc['Critical'] > 0:
            data['status'] = "Critical"
            E = 1

        # trim the value of msg since we're appending and adding ';' at the end
        # for errors
        if E > 0:
            data['message'] = msg[:-1]
        else:
            if len(checks.keys()) > 0:
                # we didn't find any error states, so we're OK
                data['status'] = "OK"
                data['message'] = "Everything is OK!"
            else:
                data['status'] = "Unknown"
                data['message'] = "No checks are registered!"
        data['date'] = ts
        return data

if __name__ == '__main__':
    app.run(host=LISTEN, port=PORT, debug=DEBUG, reloader=RELOADER)

########NEW FILE########
__FILENAME__ = sample_service
#!/usr/bin/env python
import json
import sys
import os
from bottle import route, run, get
import time
import httplib

server = "127.0.0.1"
statport = "18081"
host = "%s:18001" % server
staturl = "http://%s:%s/status" % (server,statport)

blob = {"id": "bar", "url": staturl}
data = json.dumps(blob)
connection =  httplib.HTTPConnection(host)
connection.request('POST', '/checks', data)
result = connection.getresponse()
print "RESULT: %s - %s" % (result.status, result.reason)

def usage():
        print "%s [status: OK,Unknown,Warning,Critical]" % (sys.argv[0])

msgs = {
	"OK": "Everything is groovy!",
	"Unknown": "Unknown error!",
	"Warning": "Houston, I think we have a problem.",
	"Critical": "Danger Will Rogers! Danger!"
}

t = len(sys.argv)
if t < 2:
        usage()
        sys.exit(1)
else:  
        statusm = sys.argv[1]



t = time.localtime()
ts = time.strftime('%Y-%m-%dT%H:%M:%S%Z', t)
rootdir = "./"

# Change working directory so relative paths (and template lookup) work again
root = os.path.join(os.path.dirname(__file__))
sys.path.insert(0, root)

# generate nested python dictionaries, copied from here:
# http://stackoverflow.com/questions/635483/what-is-the-best-way-to-implement-nested-dictionaries-in-python
class AutoVivification(dict):
        """Implementation of perl's autovivification feature."""
        def __getitem__(self, item):
                try:
                        return dict.__getitem__(self, item)
                except KeyError:
                        value = self[item] = type(self)()
                        return value

@get('/status')
def status():
	data = AutoVivification()
	data['id'] = "bar"
	data['status'] = statusm
	data['date'] = ts
	data['message'] = msgs[statusm]
	data['version'] = "1.0.0"
	return data

run(host='localhost', port=statport, debug=True)

########NEW FILE########
__FILENAME__ = sample_service2
#!/usr/bin/env python
import json
import sys
import os
from bottle import route, run, get
import time
import httplib

server = "127.0.0.1"
statport = "18082"
host = "%s:18001" % server
staturl = "http://%s:%s/status" % (server,statport)

blob = {"id": "foo", "url": staturl}
data = json.dumps(blob)
connection =  httplib.HTTPConnection(host)
connection.request('POST', '/checks', data)
result = connection.getresponse()
print "RESULT: %s - %s" % (result.status, result.reason)

def usage():
        print "%s [status: OK,Unknown,Warning,Critical]" % (sys.argv[0])

msgs = {
	"OK": "Everything is groovy!",
	"Unknown": "Unknown error!",
        "Warning": "Houston, I think we have a problem.",
        "Critical": "Danger Will Rogers! Danger!"
}

t = len(sys.argv)
if t < 2:
        usage()
        sys.exit(1)
else:  
        statusm = sys.argv[1]



t = time.localtime()
ts = time.strftime('%Y-%m-%dT%H:%M:%S%Z', t)
rootdir = "./"

# Change working directory so relative paths (and template lookup) work again
root = os.path.join(os.path.dirname(__file__))
sys.path.insert(0, root)

# generate nested python dictionaries, copied from here:
# http://stackoverflow.com/questions/635483/what-is-the-best-way-to-implement-nested-dictionaries-in-python
class AutoVivification(dict):
        """Implementation of perl's autovivification feature."""
        def __getitem__(self, item):
                try:
                        return dict.__getitem__(self, item)
                except KeyError:
                        value = self[item] = type(self)()
                        return value

@get('/status')
def status():
	data = AutoVivification()
	data['id'] = "bar"
	data['status'] = statusm
	data['date'] = ts
	data['message'] = msgs[statusm]
	data['version'] = "1.0.0"
	return data

run(host='localhost', port=statport, debug=True)

########NEW FILE########
__FILENAME__ = test_funtional
from webtest import TestApp
from megaphone import megaphone

# see: http://webtest.pythonpaste.org/en/latest/index.html


def test_get_status():
    app = TestApp(megaphone.app)
    resp = app.get('/')

    assert resp.status_int == 200

########NEW FILE########