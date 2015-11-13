__FILENAME__ = body_btree

def get():
    return getServerStatus()["indexCounters"]["btree"]

def doData():
    for k,v in get().iteritems():
        print( str(k) + ".value " + str(int(v)) )

def doConfig():

    print "graph_title MongoDB btree stats"
    print "graph_args --base 1000 -l 0"
    print "graph_vlabel mb ${graph_period}"
    print "graph_category MongoDB"

    for k in get():
        print k + ".label " + k
        print k + ".min 0"
        print k + ".type COUNTER"
        print k + ".max 500000"
        print k + ".draw LINE1"






########NEW FILE########
__FILENAME__ = body_conn

name = "connections"


def doData():
    print name + ".value " + str( getServerStatus()["connections"]["current"] )

def doConfig():

    print "graph_title MongoDB current connections"
    print "graph_args --base 1000 -l 0"
    print "graph_vlabel connections"
    print "graph_category MongoDB"

    print name + ".label " + name






########NEW FILE########
__FILENAME__ = body_lock

name = "locked"

def doData():
    print name + ".value " + str( 100 * getServerStatus()["globalLock"]["ratio"] )

def doConfig():

    print "graph_title MongoDB write lock percentage"
    print "graph_args --base 1000 -l 0 "
    print "graph_vlabel percentage"
    print "graph_category MongoDB"

    print name + ".label " + name






########NEW FILE########
__FILENAME__ = body_mem

def ok(s):
    return s == "resident" or s == "virtual" or s == "mapped"

def doData():
    for k,v in getServerStatus()["mem"].iteritems():
        if ok(k):
            print( str(k) + ".value " + str(v * 1024 * 1024) )

def doConfig():

    print "graph_title MongoDB memory usage"
    print "graph_args --base 1024 -l 0 --vertical-label Bytes"
    print "graph_category MongoDB"

    for k in getServerStatus()["mem"]:
        if ok( k ):
            print k + ".label " + k
            print k + ".draw LINE1"







########NEW FILE########
__FILENAME__ = body_ops


def doData():
    ss = getServerStatus()
    for k,v in ss["opcounters"].iteritems():
        print( str(k) + ".value " + str(v) )

def doConfig():

    print "graph_title MongoDB ops"
    print "graph_args --base 1000 -l 0"
    print "graph_vlabel ops / ${graph_period}"
    print "graph_category MongoDB"
    print "graph_total total"

    for k in getServerStatus()["opcounters"]:
        print k + ".label " + k
        print k + ".min 0"
        print k + ".type COUNTER"
        print k + ".max 500000"
        print k + ".draw LINE1"

########NEW FILE########
__FILENAME__ = footer

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "config":
        doConfig()
    else:
        doData()



########NEW FILE########
__FILENAME__ = header

import urllib2
import sys
import os

try:
    import json
except ImportError:
    import simplejson as json


def getServerStatus():
    host = os.environ.get("host", "127.0.0.1")
    port = 28017
    url = "http://%s:%d/_status" % (host, port)
    req = urllib2.Request(url)
    user = os.environ.get("user")
    password = os.environ.get("password")
    if user and password:
        passwdmngr = urllib2.HTTPPasswordMgrWithDefaultRealm()
        passwdmngr.add_password(None, 'http://%s:%d' % (host, port), user, password)
        authhandler = urllib2.HTTPDigestAuthHandler(passwdmngr)
        opener = urllib2.build_opener(authhandler)
        urllib2.install_opener(opener)
    raw = urllib2.urlopen(req).read()
    return json.loads( raw )["serverStatus"]

########NEW FILE########
