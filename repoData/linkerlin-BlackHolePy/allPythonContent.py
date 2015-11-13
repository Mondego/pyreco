__FILENAME__ = bg_worker
#! /usr/bin/python
# -*- coding: utf-8 -*-
# cody by linker.lin@me.com

__author__ = 'linkerlin'

import threading
import Queue
import time


class BGWorker(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        self.q = Queue.Queue()

    def post(self, job):
        self.q.put(job)

    def run(self):
        while 1:
            job = None
            try:
                job = self.q.get(block=True)
                if job:
                    job()
            except Exception as ex:
                print "Error,job exception:", ex.message, type(ex)
                time.sleep(0.005)
            else:
                #print "job: ", job, " done"
                print ".",
                pass
            finally:
                time.sleep(0.005)


bgworker = BGWorker()
bgworker.setDaemon(True)
bgworker.start()

########NEW FILE########
__FILENAME__ = caches
#! /usr/bin/python
# -*- coding: utf-8 -*-
__author__ = 'linkerlin'
import sys

reload(sys)
sys.setdefaultencoding("utf-8")
import collections
import functools
from itertools import ifilterfalse
from heapq import nsmallest
from operator import itemgetter
import threading
import cPickle as p
import datetime as dt
import base64
import random
import time
from hashlib import md5


class Counter(dict):
    'Mapping where default values are zero'

    def __missing__(self, key):
        return 0


def sqlite_cache(timeout_seconds=100, cache_none=True, ignore_args={}):
    import sqlite3

    def decorating_function(user_function,
                            len=len, iter=iter, tuple=tuple, sorted=sorted, KeyError=KeyError):
        with sqlite3.connect(u"cache.sqlite") as cache_db:
            cache_cursor = cache_db.cursor()
            cache_table = u"table_" + user_function.func_name
            #print cache_table
            cache_cursor.execute(
                u"CREATE TABLE IF NOT EXISTS " + cache_table
                + u" (key CHAR(36) PRIMARY KEY, value TEXT, update_time  timestamp);")
            cache_db.commit()
        kwd_mark = object()             # separate positional and keyword args
        lock = threading.Lock()

        @functools.wraps(user_function)
        def wrapper(*args, **kwds):
            result = None
            cache_db = None
            # cache key records both positional and keyword args
            key = args
            if kwds:
                real_kwds = []
                for k in kwds:
                    if k not in ignore_args:
                        real_kwds.append((k, kwds[k]))
                key += (kwd_mark,)
                if len(real_kwds) > 0:
                    key += tuple(sorted(real_kwds))
            while cache_db is None:
                try:
                    with lock:
                        cache_db = sqlite3.connect(u"cache.sqlite")
                except sqlite3.OperationalError as ex:
                    print ex
                    time.sleep(0.05)
                # get cache entry or compute if not found
            try:
                cache_cursor = cache_db.cursor()
                key_str = str(key) # 更加宽泛的Key，只检查引用的地址，而不管内容，“浅”检查,更好的配合方法，但是可能会出现过于宽泛的问题
                key_str = md5(key_str).hexdigest() # base64.b64encode(key_str)
                #print "key_str:", key_str[:60]
                with lock:
                    cache_cursor.execute(
                        u"select * from " + cache_table
                        + u" where key = ? order by update_time desc", (key_str,))
                for record in cache_cursor:
                    dump_data = base64.b64decode(record[1])
                    result = p.loads(dump_data)
                    #print "cached:", md5(result).hexdigest()
                    break
                if result is not None:
                    with lock:
                        wrapper.hits += 1
                    print "hits", wrapper.hits, "miss", wrapper.misses, wrapper
                else:
                    result = user_function(*args, **kwds)
                    if result is None and cache_none == False:
                        return
                    value = base64.b64encode(p.dumps(result, p.HIGHEST_PROTOCOL))
                    while 1:
                        try:
                            cache_cursor.execute(u"REPLACE INTO " + cache_table + u" VALUES(?,?,?)",
                                                 (key_str, value, dt.datetime.now()))
                        except sqlite3.OperationalError as ex:
                            print ex, "retry update db."
                        else:
                            cache_db.commit()
                            with lock:
                                wrapper.misses += 1
                            break
            finally:
                if random.random() > 0.999:
                    timeout = dt.datetime.now() - dt.timedelta(seconds=timeout_seconds)
                    with lock:
                        cache_cursor.execute(u"DELETE FROM " + cache_table + u" WHERE update_time < datetime(?)",
                                             (str(timeout),))
                with lock:
                    cache_db.commit()
                    cache_db.close()
            return result

        def clear():
            with lock:
                wrapper.hits = wrapper.misses = 0

        wrapper.hits = wrapper.misses = 0
        wrapper.clear = clear
        return wrapper

    return decorating_function


def lru_cache(maxsize=100, cache_none=True, ignore_args=[]):
    '''Least-recently-used cache decorator.

    Arguments to the cached function must be hashable.
    Cache performance statistics stored in f.hits and f.misses.
    Clear the cache with f.clear().
    http://en.wikipedia.org/wiki/Cache_algorithms#Least_Recently_Used

    '''
    maxqueue = maxsize * 10

    def decorating_function(user_function,
                            len=len, iter=iter, tuple=tuple, sorted=sorted, KeyError=KeyError):
        cache = {}                  # mapping of args to results
        queue = collections.deque() # order that keys have been used
        refcount = Counter()        # times each key is in the queue
        sentinel = object()         # marker for looping around the queue
        kwd_mark = object()         # separate positional and keyword args

        # lookup optimizations (ugly but fast)
        queue_append, queue_popleft = queue.append, queue.popleft
        queue_appendleft, queue_pop = queue.appendleft, queue.pop
        lock = threading.RLock()

        @functools.wraps(user_function)
        def wrapper(*args, **kwds):
            with lock:
                # cache key records both positional and keyword args
                key = args
                if kwds:
                    real_kwds = []
                    for k in kwds:
                        if k not in ignore_args:
                            real_kwds.append((k, kwds[k]))
                    key += (kwd_mark,)
                    if len(real_kwds) > 0:
                        key += tuple(sorted(real_kwds))
                        #print "key", key

                # record recent use of this key
                queue_append(key)
                refcount[key] += 1

                # get cache entry or compute if not found
                try:
                    result = cache[key]
                    wrapper.hits += 1
                    #print "hits", wrapper.hits, "miss", wrapper.misses, wrapper
                except KeyError:
                    result = user_function(*args, **kwds)
                    if result is None and cache_none == False:
                        return
                    cache[key] = result
                    wrapper.misses += 1

                    # purge least recently used cache entry
                    if len(cache) > maxsize:
                        key = queue_popleft()
                        refcount[key] -= 1
                        while refcount[key]:
                            key = queue_popleft()
                            refcount[key] -= 1
                        if key in cache:
                            del cache[key]
                        if key in refcount:
                            refcount[key]
                finally:
                    pass

                # periodically compact the queue by eliminating duplicate keys
                # while preserving order of most recent access
                if len(queue) > maxqueue:
                    refcount.clear()
                    queue_appendleft(sentinel)
                    for key in ifilterfalse(refcount.__contains__,
                                            iter(queue_pop, sentinel)):
                        queue_appendleft(key)
                        refcount[key] = 1

            return result

        def clear():
            cache.clear()
            queue.clear()
            refcount.clear()
            wrapper.hits = wrapper.misses = 0

        wrapper.hits = wrapper.misses = 0
        wrapper.clear = clear
        return wrapper

    return decorating_function


def lfu_cache(maxsize=100):
    '''Least-frequenty-used cache decorator.

    Arguments to the cached function must be hashable.
    Cache performance statistics stored in f.hits and f.misses.
    Clear the cache with f.clear().
    http://en.wikipedia.org/wiki/Least_Frequently_Used

    '''

    def decorating_function(user_function):
        cache = {}                      # mapping of args to results
        use_count = Counter()           # times each key has been accessed
        kwd_mark = object()             # separate positional and keyword args
        lock = threading.RLock()

        @functools.wraps(user_function)
        def wrapper(*args, **kwds):
            with lock:
                key = args
                if kwds:
                    key += (kwd_mark,) + tuple(sorted(kwds.items()))
                use_count[key] += 1

                # get cache entry or compute if not found
                try:
                    result = cache[key]
                    wrapper.hits += 1
                except KeyError:
                    result = user_function(*args, **kwds)
                    cache[key] = result
                    wrapper.misses += 1

                    # purge least frequently used cache entry
                    if len(cache) > maxsize:
                        for key, _ in nsmallest(maxsize // 10,
                                                use_count.iteritems(),
                                                key=itemgetter(1)):
                            del cache[key], use_count[key]

            return result

        def clear():
            cache.clear()
            use_count.clear()
            wrapper.hits = wrapper.misses = 0

        wrapper.hits = wrapper.misses = 0
        wrapper.clear = clear
        return wrapper

    return decorating_function


if __name__ == '__main__':

    @lru_cache(maxsize=20, ignore_args=["y"])
    def f(x, y):
        return 3 * x + y

    domain = range(5)
    from random import choice

    for i in range(1000):
        r = f(choice(domain), y=choice(domain))

    print(f.hits, f.misses)

    @lfu_cache(maxsize=20)
    def f(x, y):
        return 3 * x + y

    domain = range(5)
    from random import choice

    for i in range(1000):
        r = f(choice(domain), choice(domain))

    print(f.hits, f.misses)

    @sqlite_cache()
    def f2(x, y):
        return 3 * x + y

    domain = range(50)
    for i in range(1000):
        r = f2(choice(domain), y=choice(domain))
    print(f2.hits, f2.misses)
########NEW FILE########
__FILENAME__ = config
#! /usr/bin/python
# -*- coding: utf-8 -*-
__author__ = 'linkerlin'
import sys


reload(sys)
sys.setdefaultencoding("utf-8")

DNSS = [
        ('8.8.8.8', 53, {"tcp",}),
        ('8.8.4.4', 53, {"tcp",}),
        ('208.67.222.222', 53, {"tcp",}),
        ('208.67.220.220', 53, {"tcp",}),


]



# a white dns server will service white list domains
WHITE_DNSS = [
    ("61.152.248.83", 53, {"udp",}, ["baidu.com", "qq.com"]),
]




########NEW FILE########
__FILENAME__ = dnsproxy
#! /usr/bin/python
# -*- coding: utf-8 -*-
__author__ = 'linkerlin'
import sys
import struct
import threading
import SocketServer
import optparse
try:
    from dns import message as m
except ImportError as ex:
    print "cannot find dnspython"
try:
    from gevent import monkey
    monkey.patch_all()
except ImportError as ex:
    print "cannot find gevent"

import config
from dnsserver import DNSServer
from servers import Servers


reload(sys)
sys.setdefaultencoding("utf-8")

from dnsserver import bytetodomain


class DNSProxy(SocketServer.ThreadingMixIn, SocketServer.UDPServer):
    SocketServer.ThreadingMixIn.daemon_threads = True
    allow_reuse_address = True

    def __init__(self, address=("0.0.0.0", 53), VERBOSE=2):
        self.VERBOSE = VERBOSE
        print "listening at:", address
        SELF = self

        class ProxyHandle(SocketServer.BaseRequestHandler):
            # Ctrl-C will cleanly kill all spawned threads
            daemon_threads = True
            # much faster rebinding
            allow_reuse_address = True

            def handle(self):
                data = self.request[0]
                socket = self.request[1]
                addr = self.client_address
                DNSProxy.transfer(SELF, data, addr, socket)

        SocketServer.UDPServer.__init__(self, address, ProxyHandle)

    def loadConfig(self, config):
        self.DNSS = config.DNSS
        self.servers = Servers()
        for s in self.DNSS:
            assert len(s) == 3
            ip, port, type_of_server = s
            self.servers.addDNSServer(DNSServer(ip, port, type_of_server, self.VERBOSE))
        self.WHITE_DNSS = config.WHITE_DNSS
        for ws in self.WHITE_DNSS:
            assert len(ws) == 4
            ip, port, type_of_server, white_list = ws
            self.servers.addWhiteDNSServer(DNSServer(ip, port, type_of_server, self.VERBOSE, white_list))


    def transfer(self, query_data, addr, server):
        if not query_data: return
        domain = bytetodomain(query_data[12:-4])
        qtype = struct.unpack('!h', query_data[-4:-2])[0]
        #print 'domain:%s, qtype:%x, thread:%d' % (domain, qtype, threading.activeCount())
        sys.stdout.flush()
        response = None
        for i in range(9):
            response = self.servers.query(query_data)
            if response:
                # udp dns packet no length
                server.sendto(response[2:], addr)
                break
        if response is None:
            print "[ERROR] Tried 9 times and failed to resolve %s" % domain
        return



def run_server():
    print '>> Please wait program init....'
    print '>> Init finished!'
    print '>> Now you can set dns server to 127.0.0.1'

    parser = optparse.OptionParser()
    parser.add_option("-v", dest="verbose", default="0", help="Verbosity level, 0-2, default is 0")
    options, _ = parser.parse_args()

    proxy = DNSProxy(VERBOSE=options.verbose)
    proxy.loadConfig(config)

    proxy.serve_forever()
    proxy.shutdown()

if __name__ == '__main__':
    run_server()
########NEW FILE########
__FILENAME__ = dnsserver
#! /usr/bin/python
# -*- coding: utf-8 -*-
__author__ = 'linkerlin'
import sys
import struct
import socket
import traceback as tb
import re

reload(sys)
sys.setdefaultencoding("utf-8")

#---------------------------------------------------------------
# bytetodomain
# 03www06google02cn00 => www.google.cn
#--------------------------------------------------------------
def bytetodomain(s):
    domain = ''
    i = 0
    length = struct.unpack('!B', s[0:1])[0]

    while length != 0:
        i += 1
        domain += s[i:i + length]
        i += length
        length = struct.unpack('!B', s[i:i + 1])[0]
        if length != 0:
            domain += '.'

    return domain


class DNSServer(object):
    def __init__(self, ip, port=53, type_of_server=("tcp", "udp"), VERBOSE=0, white_list=None):
        if white_list is None: # ref: http://blog.amir.rachum.com/post/54770419679/python-common-newbie-mistakes-part-1
            white_list = [] # Default values for functions in Python are instantiated when the function is defined, not when it’s called.
        self.VERBOSE = VERBOSE
        self.white_list = white_list
        if len(self.white_list) > 0:
            self.initWhiteList()
        self.type_of_server = type_of_server
        self.ip = ip
        if type(port) == "str" or type(port) == "unicode":
            port = int(port)
        self.port = port
        self.TIMEOUT = 20
        self.ok = 0
        self.error = 0

    def initWhiteList(self):
        self.patterns = []
        for w in self.white_list:
            p = re.compile(w, re.IGNORECASE)
            self.patterns.append(p)

    def __str__(self):
        return "DNS Server @ %s:%d %s" % (self.ip, self.port, str(self.type_of_server))

    def isUDPServer(self):
        return "udp" in self.type_of_server

    def isTCPServer(self):
        return "tcp" in self.type_of_server

    def address(self):
        return (self.ip, int(self.port))

    def suppressed(self):
        self.error -= 1
        print self, "suppressed"
        return None

    def needToSuppress(self):
        return self.error > (self.ok * 10) and self.error > 10

    def checkQuery(self, query_data):
        m = None
        domain = bytetodomain(query_data[12:-4])
        for p in self.patterns:
            m = p.match(domain)
            if m: break
        if not m:
            return None
        print "white list match:", domain, self
        return self.query(query_data)


    def query(self, query_data):
        if self.needToSuppress():
            return self.suppressed()
        buffer_length = struct.pack('!h', len(query_data))
        data = None
        s = None
        try:
            if self.isTCPServer():
                #print "tcp",len(query_data)
                sendbuf = buffer_length + query_data
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(self.TIMEOUT) # set socket timeout
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                #print "connect to ", self.address()
                s.connect(self.address())
                #print "send", len(sendbuf)
                s.send(sendbuf)
                data = s.recv(2048)
                #print "data:", data
            elif self.isUDPServer():
                #print "udp"
                sendbuf = query_data
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                s.settimeout(self.TIMEOUT) # set socket timeout
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                #print type(querydata),(server, int(port))
                s.sendto(sendbuf, self.address())
                r, serv = s.recvfrom(1024)
                data = struct.pack('!h', len(r)) + r
        except Exception, e:
            self.error += 1
            print '[ERROR] QueryDNS: %s %s' % e.message, type(e)
            tb.print_stack()
        else:
            self.ok += 1
        finally:
            if s: s.close()
            if int(self.VERBOSE) > 0:
                try:
                    self.showInfo(query_data, 0)
                    self.showInfo(data[2:], 1)
                except TypeError as ex:
                    #print ex
                    pass
                finally:
                    pass
            return data

    #----------------------------------------------------
    # show dns packet information
    #----------------------------------------------------
    def showInfo(self, data, direction):
        try:
            from dns import message as m
        except ImportError:
            print "Install dnspython module will give you more response infomation."
        else:
            if direction == 0:
                print "query:\n\t", "\n\t".join(str(m.from_wire(data)).split("\n"))
                print "\n================"
            elif direction == 1:
                print "response:\n\t", "\n\t".join(str(m.from_wire(data)).split("\n"))
                print "\n================"


if __name__ == "__main__":
    s = DNSServer("8.8.8.8")
    print s
########NEW FILE########
__FILENAME__ = servers
#! /usr/bin/python
# -*- coding: utf-8 -*-
__author__ = 'linkerlin'
import sys
import struct
try:
    from dns import message as m
except ImportError as ex:
    print "cannot find dnspython"

from dnsserver import bytetodomain
from caches import *


reload(sys)
sys.setdefaultencoding("utf-8")

from dnsserver import DNSServer
from random import sample
import base64


class Servers(object):
    def __init__(self):
        self.dns_servers = {}
        self.white_servers = []

    def addDNSServer(self, dns_server):
        assert isinstance(dns_server, DNSServer)
        self.dns_servers[dns_server.address()] = dns_server

    def addWhiteDNSServer(self, dns_server):
        assert isinstance(dns_server, DNSServer)
        self.white_servers.append(dns_server)

    def whiteListFirst(self, query_data):
        if len(self.white_servers):
            for s in self.white_servers:
                ret = s.checkQuery(query_data)
                if ret:
                    return ret
        return None

    def query(self, query_data):
        domain = bytetodomain(query_data[12:-4])
        qtype = struct.unpack('!h', query_data[-4:-2])[0]
        id = struct.unpack('!h', query_data[0:2])[0]
        #print "id", id
        #msg = [line for line in str(m.from_wire(query_data)).split('\n') if line.find("id", 0, -1) < 0]
        msg = query_data[4:]
        responce = self._query(tuple(msg),
                               query_data=query_data) # query_data must be written as a named argument, because of cache's ignore_args
        if responce:
            return responce[0:2] + query_data[0:2] + responce[4:]
        else:
            return responce

    @sqlite_cache(timeout_seconds=800000, cache_none=False, ignore_args={"query_data"})
    def _query(self, msg, query_data):
        #print msg
        ret = self.whiteListFirst(query_data)
        if ret:
            return ret
            # random select a server
        key = sample(self.dns_servers, 1)[0]
        #print key
        server = self.dns_servers[key]
        return server.query(query_data)


if __name__ == "__main__":
    ss = Servers()
    s = DNSServer("8.8.8.8")
    ss.addDNSServer(s)

########NEW FILE########
__FILENAME__ = test
#! /usr/bin/python
# -*- coding: utf-8 -*-
__author__ = 'linkerlin'
import sys
import struct
try:
    from dns import message as m
except ImportError as ex:
    print "cannot find dnspython"

from dnsserver import bytetodomain
from caches import *
import collections
import functools
from itertools import ifilterfalse
from heapq import nsmallest
from operator import itemgetter
import threading
import cPickle as p
import datetime as dt
import base64
import random
from random import choice

def testSqliteCache():
    @sqlite_cache()
    def f2(x, y):
        return 3 * x + y

    domain = range(50)
    for i in range(1000):
        r = f2(choice(domain), y=choice(domain))
    print(f2.hits, f2.misses)
    assert f2.hits>0


class R(object):
    def __init__(self, name):
        if isinstance(name, str):
            self.name = unicode(name)
        else:
            self.name = name

    def __str__(self):
        return self.name.decode("utf-8")
    def __unicode__(self):
        return self.name

    def __enter__(self):
        print "enter:",self
    def __exit__(self, exc_type, exc_val, exc_tb):
        print "exit:",self

with R("A") as a, R("B") as b: # require A then require B
    print "..."
########NEW FILE########
