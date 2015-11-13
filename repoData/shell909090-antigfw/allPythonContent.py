__FILENAME__ = dns2tcp
#!/usr/bin/python
# -*- coding: utf-8 -*-
'''
@date: 2012-09-28
@author: shell.xu
'''
import os, sys, struct, socket, logging

DNSSERVER = '8.8.8.8'

def initlog(lv, logfile=None):
    rootlog = logging.getLogger()
    if logfile: handler = logging.FileHandler(logfile)
    else: handler = logging.StreamHandler()
    handler.setFormatter(
        logging.Formatter(
            '%(asctime)s,%(msecs)03d %(name)s[%(levelname)s]: %(message)s',
            '%H:%M:%S'))
    rootlog.addHandler(handler)
    rootlog.setLevel(lv)

def on_datagram(data):
    sock = socket.socket()
    try:
        sock.connect((DNSSERVER, 53))
        stream = sock.makefile()

        s = struct.pack('!H', len(data))
        stream.write(s+data)
        stream.flush()

        s = stream.read(2)
        if len(s) == 0: raise EOFError()
        count = struct.unpack('!H', s)[0]
        reply = stream.read(count)
        if len(reply) == 0: raise EOFError()
    finally: sock.close()
    return reply

def server(port=53):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(('', port))
    logging.info('init DNS Server')

    while True:
        data, addr = sock.recvfrom(1024)
        logging.debug('data come in from %s' % str(addr))
        try:
            r = on_datagram(data)
            if r is None: continue
            sock.sendto(r, addr)
        except Exception, err: logging.exception(err)

def main():
    initlog(logging.DEBUG)
    server()

if __name__ == '__main__': main()

########NEW FILE########
__FILENAME__ = dnsproxy
#!/usr/bin/python
# -*- coding: utf-8 -*-
'''
@date: 2012-10-29
@author: shell.xu
'''
import os, sys, time, socket, select, logging

sys.path.append('uniproxy')
from mydns import *

inquery = {}
DNSSERVER = '8.8.8.8'
TIMEOUT = 60
fakeset = set([
        '8.7.198.45', '37.61.54.158',
        '46.82.174.68', '59.24.3.173',
        '78.16.49.15', '93.46.8.89',
        '159.106.121.75', '203.98.7.65',
        '243.185.187.39'])

def on_query():
    data, addr = sock.recvfrom(1024)
    q = Record.unpack(data)
    if q.id not in inquery:
        inquery[q.id] = (addr, time.time())
        client.sendto(data, (DNSSERVER, 53))
    else: logging.warn('dns id %d is conflict.' % q.id)

def on_answer():
    data, addr = client.recvfrom(1024)
    r = Record.unpack(data)
    if r.id in inquery:
        addr, ti = inquery[r.id]
        if not get_ipaddrs(r): return
        sock.sendto(data, addr)
        del inquery[r.id]
    else: logging.warn('dns server return a record id %d but no one care.' % r.id)

def get_ipaddrs(r):
    ipaddrs = [rdata for name, type, cls, ttl, rdata in r.ans if type == TYPE.A]
    if not ipaddrs:
        logging.info('drop an empty dns response.')
    elif fakeset & set(ipaddrs):
        logging.info('drop %s for fakeset.' % ipaddrs)
    else: return ipaddrs

def on_idle():
    t = time.time()
    rlist = [k for k, v in inquery.iteritems() if t - v[1] > TIMEOUT]
    for k in rlist: del inquery[k]

def main():
    global sock, client
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(('', 53))
    client = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    logging.info('init dns server')

    poll = select.poll()
    fdmap = {sock.fileno(): on_query, client.fileno(): on_answer}
    for fd in fdmap.keys(): poll.register(fd, select.POLLIN)
    while True:
        try:
            for fd, ev in poll.poll(60): fdmap[fd]()
            on_idle()
        except Exception, err: logging.exception('unknown')

if __name__ == '__main__': main()

########NEW FILE########
__FILENAME__ = gengae
#!/usr/bin/python
# -*- coding: utf-8 -*-
'''
@date: 2012-10-28
@author: shell.xu
'''
import re, os, sys, shutil
from os import path

def genapp(srcpath, dstpath):
    import sc
    d = os.getcwd()
    os.chdir(path.dirname(srcpath))
    with open(path.basename(srcpath)) as fi:
        data = ''.join(sc.server_compile(fi))
    os.chdir(d)
    with open(dstpath, 'w') as fo: fo.write(data)

re_tmpl = re.compile('<%(.*?)%>')
def template(s, d):
    return re_tmpl.sub(lambda m: str(eval(m.group(1), globals(), d)), s)

def gencfg(srcpath, dstpath):
    with open(srcpath) as fi: data = fi.read()
    data = template(data, {"youappid": raw_input("youappid: ")})
    with open(dstpath, 'w') as fo: fo.write(data)

def main():
    if path.exists(sys.argv[2]): shutil.rmtree(sys.argv[2])
    os.mkdir(sys.argv[2])
    genapp(path.join(sys.argv[1], 'wsgi.py'),
           path.join(sys.argv[2], 'wsgi.py'))
    shutil.copyfile(path.join(sys.argv[1], 'robots.txt'),
                    path.join(sys.argv[2], 'robots.txt'))
    gencfg(path.join(sys.argv[1], 'app.yaml'),
           path.join(sys.argv[2], 'app.yaml'))
    

if __name__ == '__main__': main()

########NEW FILE########
__FILENAME__ = sc
#!/usr/bin/python
# -*- coding: utf-8 -*-
'''
@date: 2012-10-16
@author: shell.xu
@remark: 用于将多个文件合并入一个脚本内，形成单一的上传文件
'''
import re, os, sys, getopt
from os import path

filepath = ['.',]

def findfile(filename):
    for p in filepath:
        f = path.join(p, filename)
        if path.exists(f): return f

include_re = re.compile('from (.*) import \*')
addpath_re = re.compile('sys\.path\.append\((.*)\)')
def server_compile(infile):
    for line in infile:
        mi = include_re.match(line)
        ma = addpath_re.match(line)
        if mi is not None:
            with open(findfile(mi.group(1) + '.py')) as fi:
                for line in server_compile(fi):
                    if line.startswith('#'): continue
                    yield line
            yield '\n'
        elif ma is not None:
            filepath.append(ma.group(1).strip('\''))
        else: yield line

def main():
    '''
    -h: help
    '''
    optlist, args = getopt.getopt(sys.argv[1:], 'h')
    optdict = dict(optlist)
    if '-h' in optdict:
        print '%s type output' % sys.argv[0]
        print main.__doc__
        return
    d = os.getcwd()
    if path.dirname(args[0]): os.chdir(path.dirname(args[0]))
    with open(path.basename(args[0])) as fi:
        data = ''.join(server_compile(fi))
    os.chdir(d)
    with open(args[1], 'w') as fo: fo.write(data)

if __name__ == '__main__': main()

########NEW FILE########
__FILENAME__ = config
config = {
    'fakeurl': '/fakeurl', 'geturl': '/geturl',
    'method': 'XOR', 'key': '1234567890'
    }

########NEW FILE########
__FILENAME__ = serve
#!/usr/bin/python
# -*- coding: utf-8 -*-
'''
@date: 2012-10-14
@author: shell.xu
'''
import sys
sys.path.append('../uniproxy/')
from config import *
from hoh import *
import copy, logging

from gevent.pywsgi import WSGIServer
from gevent import socket

def http_over_http(d):
    d = base64.b64decode(d.replace('&', '').replace('=', '') + '==', '_%')
    d = get_crypt(config['method'], config['key'])[1](d)
    req, options = loadmsg(zlib.decompress(d), HttpRequest)

    reqx = copy.copy(req)
    url = urlparse(req.uri)
    reqx.uri = url.path + ('?'+url.query if url.query else '')
    res = http_client(
        reqx,
        (url.netloc, url.port or (443 if url.scheme == 'https' else 80)),
        socket.socket)
    d = zlib.compress(dumpres(res), 9)
    return get_crypt(config['method'], config['key'])[0](d)

def redirget(uri):
    url = urlparse(uri)
    req = HttpRequest('GET', url.path + ('?'+url.query if url.query else ''),
                      'HTTP/1.1')
    req.set_header('Host', url.netloc)
    res = http_client(
        req, (url.netloc, url.port or (443 if url.scheme == 'https' else 80)),
        socket.socket)
    return res

def application(env, start_response):
    if env['PATH_INFO'] == config['fakeurl']:
        if env['REQUEST_METHOD'] == 'GET': d = env['QUERY_STRING']
        elif env['REQUEST_METHOD'] == 'POST': d = env['wsgi.input'].read()
        else:
            start_response('404 Not Found')
            return
        d = http_over_http(d)
        start_response('200 OK', [('Content-Type', 'application/mp4')])
        yield d
    elif env['PATH_INFO'] == config['geturl']:
        res = redirget(base64.b64decode(env['QUERY_STRING']))
        start_response('%s %s' % (res.code, res.phrase), res.headers)
        for d in res.read_chunk(res.stream): yield d

def initlog(lv, logfile=None):
    rootlog = logging.getLogger()
    if logfile: handler = logging.FileHandler(logfile)
    else: handler = logging.StreamHandler()
    handler.setFormatter(
        logging.Formatter(
            '%(asctime)s,%(msecs)03d %(name)s[%(levelname)s]: %(message)s',
            '%H:%M:%S'))
    rootlog.addHandler(handler)
    rootlog.setLevel(lv)

if __name__ == '__main__':
    initlog(logging.DEBUG)
    WSGIServer(('0.0.0.0', 8088), application).serve_forever()

########NEW FILE########
__FILENAME__ = wsgi
#!/usr/bin/python
# -*- coding: utf-8 -*-
'''
@date: 2012-10-17
@author: shell.xu
'''
import sys
sys.path.append('../uniproxy/')
from config import *
from hoh import *

from google.appengine.api import urlfetch

def dump_gaeres(res, **options):
    headers = map(lambda i: (headernum.get(i[0], i[0]), i[1]), res.headers)
    return packdata(('HTTP/1.1', res.status_code, DEFAULT_PAGES[res.status_code][0],
                     headers, options), res.content)

def http_over_http(d):
    d = base64.b64decode(d.replace('&', '').replace('=', '') + '==', '_%')
    d = get_crypt(config['method'], config['key'])[1](d)
    req, options = loadmsg(zlib.decompress(d), HttpRequest)

    res = urlfetch.fetch(req.uri, req.body, req.method, dict(req.headers), deadline=30)
    d = zlib.compress(dump_gaeres(res), 9)
    return get_crypt(config['method'], config['key'])[0](d)

def application(env, start_response):
    if env['PATH_INFO'] == config['fakeurl']:
        if env['REQUEST_METHOD'] == 'GET': d = env['QUERY_STRING']
        elif env['REQUEST_METHOD'] == 'POST':
            d = env['wsgi.input'].read(int(env['HTTP_CONTEXT_LENGTH']))
        else:
            start_response('404 Not Found', [])
            return
        d = http_over_http(d)
        start_response('200 OK', [('Content-Type', 'application/mp4')])
        yield d
    elif env['PATH_INFO'] == config['geturl']:
        res = urlfetch.fetch(base64.b64decode(env['QUERY_STRING']))
        start_response('%s %s' % (res.status_code, DEFAULT_PAGES[res.status_code][0]),
                       res.headers.items())
        yield res.content

########NEW FILE########
__FILENAME__ = lru
#!/usr/bin/python
# -*- coding: utf-8 -*-
'''
@date: 2012-10-18
@author: shell.xu
'''
import sys, unittest

sys.path.append("../uniproxy")
import dnsserver

class LRUTest(unittest.TestCase):
    def setUp(self):
        self.lru = dnsserver.ObjHeap(10)

    def test_lru(self):
        for i in xrange(10): self.lru[i] = i
        for i in xrange(5): self.lru[i]
        for i in xrange(20, 25): self.lru[i] = i
        self.assertTrue(any(map(self.lru.get, xrange(5))))
        self.assertTrue(len(self.lru) <= 10)

########NEW FILE########
__FILENAME__ = main
#!/usr/bin/python
# -*- coding: utf-8 -*-
'''
@date: 2012-10-18
@author: shell.xu
'''
import os, urllib2, unittest
from BeautifulSoup import BeautifulSoup

try: del os.environ['http_proxy']
except KeyError: pass
try: del os.environ['https_proxy']
except KeyError: pass

proxy_handler = urllib2.ProxyHandler({
        'http': 'http://localhost:8080/', 'https': 'http://localhost:8080/'})
# proxy_auth_handler = urllib2.ProxyBasicAuthHandler()
# proxy_auth_handler.add_password('realm', 'host', 'username', 'password')
proxy_opener = urllib2.build_opener(proxy_handler)

class ProxyTest(unittest.TestCase):
    def test_ingfw_http(self):
        proxy_opener.open('http://www.sina.com.cn/')
    def test_ingfw_https(self):
        proxy_opener.open('https://www.cmbchina.com/')
    def test_gfw_http(self):
        proxy_opener.open('http://www.cnn.com/')
    def test_gfw_https(self):
        proxy_opener.open('https://www.facebook.com')

class TypeTest(unittest.TestCase):
    def test_chunk(self):
        s = BeautifulSoup(proxy_opener.open('http://wordpress.org//').read())
        self.assertTrue(s.title.string.find(u'WordPress') != -1)
    def test_length(self):
        s = BeautifulSoup(proxy_opener.open('http://www.twitter.com/').read())
        self.assertTrue(s.title.string.find(u'Twitter') != -1)
    def test_hasbody(self):
        s = BeautifulSoup(proxy_opener.open('http://www.dangdang.com/').read())
        self.assertTrue(s.title.string.find(u'当当网') != -1)

def main():
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    suite.addTests(loader.loadTestsFromModule(__import__('main')))
    suite.addTests(loader.loadTestsFromModule(__import__('mgr')))
    suite.addTests(loader.loadTestsFromModule(__import__('lru')))
    unittest.TextTestRunner(verbosity = 2).run(suite)

if __name__ == '__main__': main()

########NEW FILE########
__FILENAME__ = mgr
#!/usr/bin/python
# -*- coding: utf-8 -*-
'''
@date: 2012-11-05
@author: shell.xu
'''
import urllib2, unittest

auth_handler = urllib2.HTTPBasicAuthHandler()
auth_handler.add_password(
    realm='managers', uri='http://127.0.0.1:8080/', user='admin', passwd='uniproxy')
auth_opener = urllib2.build_opener(auth_handler)

class ManagerAuth(unittest.TestCase):
    def test_noauth(self):
        with self.assertRaises(urllib2.HTTPError):
            urllib2.urlopen('http://127.0.0.1:8080/')
    def test_auth(self):
        auth_opener.open('http://127.0.0.1:8080/')

class ManagerTest(unittest.TestCase):
    def test_stat(self):
        auth_opener.open('http://127.0.0.1:8080/')
    def test_dnsfake(self):
        auth_opener.open('http://127.0.0.1:8080/dnsfake')
    def test_whitenets(self):
        auth_opener.open('http://127.0.0.1:8080/whitenets')
    def test_blacknets(self):
        auth_opener.open('http://127.0.0.1:8080/blacknets')

########NEW FILE########
__FILENAME__ = conn
#!/usr/bin/python
# -*- coding: utf-8 -*-
'''
@date: 2012-09-29
@author: shell.xu
'''
import logging
from contextlib import contextmanager
from gevent import ssl, dns, coros, socket, Timeout
from gevent import with_timeout as call_timeout
from http import *

logger = logging.getLogger('conn')

def ssl_socket(certfile=None):
    def reciver(func):
        def creator(family=socket.AF_INET, type=socket.SOCK_STREAM, proto=0):
            sock = func(family, type, proto)
            if not certfile: return ssl.wrap_socket(sock)
            else: return ssl.wrap_socket(sock, certfile=cretfile)
        return creator
    return reciver

class DirectManager(object):
    name = 'direct'

    def __init__(self, dns): self.count, self.dns = 0, dns

    def size(self): return 65536
    def stat(self): return '%d/unlimited' % self.count

    @contextmanager
    def socket(self):
        self.count += 1
        logger.debug('%s %s allocated' % (self.name, self.stat()))
        sock = socket.socket()
        connect = sock.connect
        def newconn(addr):
            # 没办法，gevent的dns这时如果碰到多ip返回值，会直接报错
            try: connect(addr)
            except dns.DNSError:
                address = self.dns.gethostbyname(addr[0])
                if address is None: raise Exception('DNS not found')
                sock.connect((address, addr[1]))
        sock.connect = newconn
        try: yield sock
        finally:
            sock.close()
            logger.debug('%s %s released' % (self.name, self.stat()))
            self.count -= 1

class Manager(object):
    def __init__(self, max_conn=10, name=None, **kargs):
        self.smph, self.max_conn = coros.BoundedSemaphore(max_conn), max_conn
        self.name, self.creator = name, socket.socket

    def size(self): return self.max_conn - self.smph.counter
    def stat(self): return '%d/%d' % (self.size(), self.max_conn)

    @contextmanager
    def socket(self):
        with self.smph:
            logger.debug('%s %s allocated' % (self.name, self.stat()))
            sock = self.creator()
            try: yield sock
            finally:
                sock.close()
                logger.debug('%s %s released' % (self.name, self.stat()))

def http_connect(sock, target, username=None, password=None):
    stream = sock.makefile()
    req = HttpRequest('CONNECT', '%s:%d' % target, 'HTTP/1.1')
    if username and password:
        req.add_header('Proxy-Authorization',
                       base64.b64encode('Basic %s:%s' % (username, password)))
    req.send_header(stream)
    res = recv_msg(stream, HttpResponse)
    if res.code != 200: raise Exception('http proxy connect failed')

def http_proxy(proxyaddr, username=None, password=None):
    def reciver(func):
        def creator(family=socket.AF_INET, type=socket.SOCK_STREAM, proto=0):
            sock = func(family, type, proto)
            sock.connect(proxyaddr)
            def newconn(addr): http_connect(sock, addr, username, password)
            sock.connect, sock.connect_ex = newconn, newconn
            return sock
        return creator
    return reciver

class HttpManager(Manager):
    def __init__(self, addr, port, username=None, password=None,
                 max_conn=10, name=None, ssl=False, **kargs):
        super(HttpManager, self).__init__(
            max_conn, name or '%s:%s:%s' % ('https' if ssl else 'http', addr, port))
        if ssl is True: self.creator = ssl_socket()(self.creator)
        elif ssl: self.creator = ssl_socket(ssl)(self.creator)
        self.creator = http_proxy((addr, port), username, password)(self.creator)

def ssl_socket(certfile=None):
    def reciver(func):
        def creator(family=socket.AF_INET, type=socket.SOCK_STREAM, proto=0):
            sock = func(family, type, proto)
            if not certfile: return ssl.wrap_socket(sock)
            else: return ssl.wrap_socket(sock, certfile=cretfile)
        return creator
    return reciver

def set_timeout(timeout=None):
    def reciver(func):
        if timeout is None: return func
        return lambda *p: call_timeout(timeout, func, *p)
    return reciver

########NEW FILE########
__FILENAME__ = dnsserver
#!/usr/bin/python
# -*- coding: utf-8 -*-
'''
@date: 2012-09-29
@author: shell.xu
'''
import sys, time, heapq, random, getopt, logging, cStringIO, gevent
from mydns import *
from contextlib import contextmanager
from gevent import socket, queue

logger = logging.getLogger('dnsserver')

class ObjHeap(object):
    ''' 使用lru算法的对象缓存容器，感谢Evan Prodromou <evan@bad.dynu.ca>。
    thx for Evan Prodromou <evan@bad.dynu.ca>. '''
    MAXSEQ = 0x100000000

    class __node(object):
        def __init__(self, k, v, f): self.k, self.v, self.f = k, v, f
        def __cmp__(self, o): return self.f > o.f

    def __init__(self, size):
        self.size = size
        self.clean()

    def clean(self):
        self.f, self.__dict, self.__heap = 0, {}, []

    def getseq(self):
        if self.f >= self.MAXSEQ:
            self.f = 1
            for n in self.__heap: n.f = 0
        else: self.f += 1
        return self.f

    def __len__(self): return len(self.__dict)
    def __contains__(self, k): return self.__dict.has_key(k)

    def __setitem__(self, k, v):
        if self.__dict.has_key(k):
            n = self.__dict[k]
            n.v, n.f = v, self.getseq()
        elif len(self.__heap) < self.size:
            n = self.__node(k, v, self.getseq())
            self.__heap.append(n)
            self.__dict[k] = n
        else:
            heapq.heapify(self.__heap)
            try:
                while len(self.__heap) > self.size:
                    del self.__dict[heapq.heappop(self.__heap).k]
                n = self.__node(k, v, self.getseq())
                del self.__dict[heapq.heappushpop(self.__heap, n).k]
                self.__dict[k] = n
            except KeyError: self.clean()

    def __getitem__(self, k):
        n = self.__dict[k]
        n.f = self.getseq()
        return n.v

    def get(self, k):
        n = self.__dict.get(k)
        if n is None: return None
        n.f = self.getseq()
        return n.v

    def __delitem__(self, k):
        n = self.__dict[k]
        self.__heap.remove(n)
        del self.__dict[k]
        return n.v

    def __iter__(self):
        c = self.__heap[:]
        while len(c): yield heapq.heappop(c).k

class DNSServer(object):
    DNSSERVER = '8.8.8.8'
    DNSPORT   = 53
    TIMEOUT   = 3600
    RETRY     = 3

    def __init__(self, dnsserver, cachesize=512, timeout=30):
        self.dnsserver = dnsserver or self.DNSSERVER
        self.cache, self.cachesize = ObjHeap(cachesize), cachesize
        self.timeout = timeout
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.fakeset = set()
        self.inquery = {}
        self.gr = gevent.spawn(self.receiver)
        self.srv = None

    def runserver(self, dnsport=None):
        self.srv = gevent.spawn(self.server, dnsport)

    def stop(self):
        if self.srv: self.srv.kill()
        self.gr.kill()

    def load(self, stream):
        for line in stream:
            if line.startswith('#'): continue
            self.fakeset.add(line.strip())

    def loadfile(self, filename):
        openfile = open
        if filename.endswith('.gz'):
            import gzip
            openfile = gzip.open
        try:
            with openfile(filename) as fi: self.load(fi)
        except (OSError, IOError): return False

    def loadlist(self, filelist):
        for f in filelist: self.loadfile(f)

    def save(self, stream):
        for i in list(self.fakeset): stream.write(i+'\n')

    def savefile(self, filepath):
        openfile = open
        if filepath.endswith('.gz'):
            import gzip
            openfile = gzip.open
        try:
            with openfile(filepath, 'w+') as fo: self.save(fo)
        except (OSError, IOError): return False

    def get_ipaddrs(self, r):
        ipaddrs = [rdata for name, type, cls, ttl, rdata in r.ans if type == TYPE.A]
        if not ipaddrs:
            logger.info('drop an empty dns response.')
            return
        if self.fakeset and self.fakeset & set(ipaddrs):
            logger.info('drop %s in fakeset.' % ipaddrs)
            return
        ttls = [ttl for name, type, cls, ttl, rdata in r.ans if type == TYPE.A]
        return ipaddrs, ttls[0] * 60 if ttls else self.TIMEOUT

    def gethostbyname(self, name):
        try:
            socket.inet_aton(name)
            return name
        except socket.error: pass

        if name in self.cache:
            if time.time() <= self.cache[name][0]:
                return random.choice(self.cache[name][1])
            else: del self.cache[name]

        self.query(name)
        r = self.cache.get(name)
        if r is None: return None
        else: return random.choice(r[1])

    @contextmanager
    def with_queue(self, id):
        qp = queue.Queue()
        logger.debug('add id %d' % id)
        self.inquery[id] = lambda r, d: qp.put(r)
        try: yield qp
        finally: del self.inquery[id]
        logger.debug('del id %d' % id)

    def query(self, name, type=TYPE.A):
        q = mkquery((name, type))
        while q.id in self.inquery: q = mkquery((name, type))
        logger.debug('request dns %s with id %d' % (name, q.id))
        with self.with_queue(q.id) as qp:
            self.sock.sendto(q.pack(), (self.dnsserver, self.DNSPORT))
            for i in xrange(self.RETRY):
                try:
                    r = qp.get(timeout=self.timeout)
                    logger.debug('get response with id: %d' % r.id)
                    ipaddrs, ttl = self.get_ipaddrs(r)
                    self.cache[name] = (time.time() + ttl, ipaddrs)
                    return
                except (EOFError, socket.error): continue
                except queue.Empty: return

    def receiver(self):
        while True:
            try:
                while True:
                    d = self.sock.recvfrom(2048)[0]
                    r = Record.unpack(d)
                    if not self.get_ipaddrs(r): continue
                    if r.id not in self.inquery:
                        logger.warn('got a record not in query\n')
                        for line in r.show(): logger.warn(line)
                    else: self.inquery[r.id](r, d)
            except Exception, err: logger.exception(err)

    def on_datagram(self, data, sock, addr):
        q = Record.unpack(data)
        if q.id in self.inquery:
            logger.warn('dns id %d conflict.' % q.id)
            return

        # TODO: timeout!
        def sendback(r, d):
            assert r.id==q.id
            sock.sendto(d, addr)
            del self.inquery[q.id]
        self.inquery[q.id] = sendback
        self.sock.sendto(data, (self.dnsserver, self.DNSPORT))

    def server(self, port=53):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind(('', port))
        logger.info('init DNS Server')

        while True:
            try:
                while True:
                    data, addr = sock.recvfrom(1024)
                    self.on_datagram(data, sock, addr)
            except Exception, err: logger.exception(err)

class TCPDNSServer(DNSServer):

    def __init__(self, dnsserver, cmanager=None, cachesize=512, timeout=30):
        self.dnsserver = dnsserver or self.DNSSERVER
        self.cache, self.cachesize = ObjHeap(cachesize), cachesize
        self.timeout = timeout
        self.fakeset = set()
        self.cmanager = cmanager
        if self.cmanager is None: self.cmanager = conn.DirectManager(self.dns)
    
    def query(self, name, type=TYPE.A):
        q = mkquery((name, type))
        while q.id in self.inquery: q = mkquery((name, type))
        logger.debug('request dns %s with id %d in tcp' % (name, q.id))

        with self.cmanager.socket() as sock:
            stream = sock.makefile()

            data = q.pack()
            stream.write(struct.pack('!H', len(data)) + data)
            stream.flush()
            s = stream.read(2)
            if len(s) == 0: raise EOFError()
            count = struct.unpack('!H', s)[0]
            reply = stream.read(count)
            if len(reply) == 0: raise EOFError()

            r = Record.unpack(reply)
            ips = self.get_ipaddrs(r)
            if ips is None: raise Exception('get fake ip in tcp mode?')
            ipaddrs, ttl = ips
            self.cache[name] = (time.time() + ttl, ipaddrs)

    def on_datagram(self, data, sock, addr):
        q = Record.unpack(data)

        with self.cmanager.socket() as sock:
            stream = sock.makefile()

            s = struct.pack('!H', len(data))
            stream.write(s+data)
            stream.flush()
            s = stream.read(2)
            if len(s) == 0: raise EOFError()
            count = struct.unpack('!H', s)[0]
            reply = stream.read(count)
            if len(reply) == 0: raise EOFError()

            sock.sendto(reply, d)

########NEW FILE########
__FILENAME__ = dofilter
#!/usr/bin/python
# -*- coding: utf-8 -*-
'''
@date: 2012-04-26
@author: shell.xu
'''
import sys, logging

__all__ = ['DomainFilter']
logger = logging.getLogger('dofilter')

class DomainFilter(object):

    def __init__(self): self.domains = {}
    def empty(self): self.domains = {}

    def add(self, domain):
        doptr, chunk, domain = self.domains, domain.split('.'), domain.lower()
        for c in reversed(chunk):
            if len(c.strip()) == 0: continue
            if c not in doptr or doptr[c] is None: doptr[c] = {}
            lastptr, doptr = doptr, doptr[c]
        if len(doptr) == 0: lastptr[c] = None

    def remove(self, domain):
        doptr, stack, chunk = self.domains, [], domain.split('.')
        for c in reversed(chunk):
            if len(c.strip()) == 0: raise LookupError()
            if doptr is None: return False
            stack.append(doptr)
            if c not in doptr: return False
            doptr = doptr[c]
        for doptr, c in zip(reversed(stack), chunk):
            if doptr[c] is None or len(doptr[c]) == 0: del doptr[c]
        return True

    def __getitem__(self, domain):
        doptr, chunk = self.domains, domain.split('.')
        for c in reversed(chunk):
            if len(c.strip()) == 0: continue
            if c not in doptr: return False
            doptr = doptr[c]
            if doptr is None: break
        return doptr
    def __contains__(self, domain): return self.__getitem__(domain) is None

    def getlist(self, d = None, s = ''):
        if d is None: d = self.domains
        for k, v in d.items():
            t = '%s.%s' %(k, s)
            if v is None: yield t.strip('.')
            else:
                for i in self.getlist(v, t): yield i

    def show(self, d = None, s = 0):
        if d is None: d = self.domains
        for k, v in d.items():
            yield '  '*s + k
            if v is not None:
                for i in self.show(v, s + 1): yield i

    def load(self, stream):
            for line in stream:
                if line.startswith('#'): continue
                self.add(line.strip().lower())

    def loadfile(self, filepath):
        openfile = open
        if filepath.endswith('.gz'):
            import gzip
            openfile = gzip.open
        try:
            with openfile(filepath, 'r') as fi: self.load(fi)
        except (OSError, IOError): return False

    def save(self, stream):
        for line in sorted(self.getlist()): stream.write(line+'\n')

    def savefile(self, filepath):
        openfile = open
        if filepath.endswith('.gz'):
            import gzip
            openfile = gzip.open
        try:
            with openfile(filepath, 'w+') as fo: self.save(fo)
        except (OSError, IOError): return False

def main():
    filter = DomainFilter()
    filter.loadfile(sys.argv[1])
    for i in sys.argv[2:]: print '%s: %s' % (i, i in filter)

if __name__ == '__main__': main()

########NEW FILE########
__FILENAME__ = hoh
#!/usr/bin/python
# -*- coding: utf-8 -*-
'''
@date: 2012-10-15
@author: shell.xu
'''
import json, zlib, base64, random, logging
from urlparse import urlparse
from http import *

headerlist = ['Accept', 'Accept-Charset', 'Accept-Encoding', 'Accept-Language', 'Accept-Ranges', 'Age', 'Allow', 'Authorization', 'Cache-Control', 'Connection', 'Content-Encoding', 'Content-Language', 'Content-Length', 'Content-Location', 'Content-Md5', 'Content-Range', 'Content-Type', 'Date', 'Etag', 'Expect', 'Expires', 'From', 'Host', 'If-Match', 'If-Modified-Since', 'If-None-Match', 'If-Range', 'If-Unmodified-Since', 'Last-Modified', 'Location', 'Max-Forwards', 'Pragma', 'Proxy-Authenticate', 'Proxy-Authorization', 'Range', 'Referer', 'Retry-After', 'Server', 'Te', 'Trailer', 'Transfer-Encodin', 'Upgrade', 'User-Agent', 'Vary', 'Via', 'Warning', 'Www-Authenticate', 'Cookie']
headernum = dict(zip(headerlist, xrange(len(headerlist))))
headername = dict(zip(xrange(len(headerlist)), headerlist))

def packdata(h, d):
    h = json.dumps(h)
    l = len(h)
    if l > 0xffff: raise Exception('header too long')
    return chr(l>>8)+chr(l&0xff) + h + d

def unpackdata(s):
    l = (ord(s[0])<<8) + ord(s[1])
    return json.loads(s[2:2+l]), s[2+l:]

def dumpreq(req, **options):
    headers = [(h, v) for h, v in req.headers if not h.startswith('Proxy')]
    headers = map(lambda i: (headernum.get(i[0], i[0]), i[1]), headers)
    return packdata((req.method, req.uri, req.version, headers, options), req.read_body())

def dumpres(res, **options):
    headers = map(lambda i: (headernum.get(i[0], i[0]), i[1]), res.headers)
    return packdata((res.version, res.code, res.phrase, headers, options), res.read_body())

def loadmsg(s, cls):
    r, d = unpackdata(s)
    req = cls(*r[:3])
    req.headers, req.body = map(lambda i: (headername.get(i[0], i[0]), i[1]), r[3]), d
    return req, r[4]

def get_crypt(algoname, key):
    algo = getattr(__import__('Crypto.Cipher', fromlist=[algoname,]), algoname)
    if algo is None: raise Exception('unknown cipher %s' % algoname)
    if algoname in ['AES', 'Blowfish', 'DES3']:
        def block_encrypt(s):
            from Crypto import Random
            iv = Random.new().read(algo.block_size)
            cipher = algo.new(key, algo.MODE_CFB, iv)
            return iv + cipher.encrypt(s)
        def block_decrypt(s):
            iv = s[:algo.block_size]
            cipher = algo.new(key, algo.MODE_CFB, iv)
            return cipher.decrypt(s[algo.block_size:])
        return block_encrypt, block_decrypt
    elif algoname in ['ARC4', 'XOR']:
        cipher = algo.new(key)
        return cipher.encrypt, cipher.decrypt
    else: raise Exception('unknown cipher %s' % name)

def fakedict(s):
    r = []
    while s:
        kl, vl = random.randint(5, 15), random.randint(50, 200)
        s, k, v = s[kl+vl:], s[:kl], s[kl:kl+vl]
        r.append((k, v))
    return '&'.join(['%s=%s' % i for i in r])

class HttpOverHttp(object):
    MAXGETSIZE = 512
    logger = logging.getLogger('hoh')
    name = 'hoh'

    def __init__(self, baseurl, algoname, key):
        from gevent import socket
        self.baseurl, self.url = baseurl, urlparse(baseurl)
        self.socket = socket.socket
        if self.url.scheme == 'https': self.socket = ssl_socket()(self.socket)
        port = self.url.port or (443 if self.url.scheme.lower() == 'https' else 80)
        self.addr, self.path = (self.url.hostname, port), self.url.path
        self.algoname, self.key = algoname, key

    def client(self, query):
        if len(query) >= self.MAXGETSIZE:
            logger.debug('query in post mode.')
            req = request_http(self.path, data=query)
            req.set_header('Context-Length', str(len(query)))
            req.set_header('Context-Type', 'multipart/form-data')
        else:
            logger.debug('query in get mode.')
            req = request_http(self.path + '?' + query)
        req.set_header('Host', self.url.hostname)
        req.debug()
        res = http_client(req, self.addr, self.socket)
        res.debug()
        if res.code != 200: return
        return res.read_body()

    def handler(self, req):
        if req.method.upper() == 'CONNECT': return None
        d = zlib.compress(dumpreq(req), 9)
        d = get_crypt(self.algoname, self.key)[0](d)
        d = base64.b64encode(d, '_%').strip('=')
        d = self.client(fakedict(d))
        # if d is None: return None
        d = get_crypt(self.algoname, self.key)[1](d)
        res, options = loadmsg(zlib.decompress(d), HttpResponse)
        return res

class GAE(HttpOverHttp):
    name = 'gae'
    ipaddr = '74.125.128.106'
    def __init__(self, gaeid, algoname, key, ssl=False):
        super(GAE, self).__init__('%s://%s.appspot.com/fakeurl' % (
                'https' if ssl else 'http', gaeid), algoname, key)
        self.addr = (self.ipaddr, self.addr[1])

########NEW FILE########
__FILENAME__ = http
#!/usr/bin/python
# -*- coding: utf-8 -*-
'''
@date: 2012-04-26
@author: shell.xu
'''
import logging

logger = logging.getLogger('http')

BUFSIZE = 8192
CODE_NOBODY = [100, 101, 204, 304]
DEFAULT_PAGES = {
    100:('Continue', 'Request received, please continue'),
    101:('Switching Protocols',
          'Switching to new protocol; obey Upgrade header'),

    200:('OK', ''),
    201:('Created', 'Document created, URL follows'),
    202:('Accepted', 'Request accepted, processing continues off-line'),
    203:('Non-Authoritative Information', 'Request fulfilled from cache'),
    204:('No Content', 'Request fulfilled, nothing follows'),
    205:('Reset Content', 'Clear input form for further input.'),
    206:('Partial Content', 'Partial content follows.'),

    300:('Multiple Choices', 'Object has several resources -- see URI list'),
    301:('Moved Permanently', 'Object moved permanently -- see URI list'),
    302:('Found', 'Object moved temporarily -- see URI list'),
    303:('See Other', 'Object moved -- see Method and URL list'),
    304:('Not Modified', 'Document has not changed since given time'),
    305:('Use Proxy',
          'You must use proxy specified in Location to access this resource.'),
    307:('Temporary Redirect', 'Object moved temporarily -- see URI list'),

    400:('Bad Request', 'Bad request syntax or unsupported method'),
    401:('Unauthorized', 'No permission -- see authorization schemes'),
    402:('Payment Required', 'No payment -- see charging schemes'),
    403:('Forbidden', 'Request forbidden -- authorization will not help'),
    404:('Not Found', 'Nothing matches the given URI'),
    405:('Method Not Allowed', 'Specified method is invalid for this server.'),
    406:('Not Acceptable', 'URI not available in preferred format.'),
    407:('Proxy Authentication Required',
          'You must authenticate with this proxy before proceeding.'),
    408:('Request Timeout', 'Request timed out; try again later.'),
    409:('Conflict', 'Request conflict.'),
    410:('Gone', 'URI no longer exists and has been permanently removed.'),
    411:('Length Required', 'Client must specify Content-Length.'),
    412:('Precondition Failed', 'Precondition in headers is false.'),
    413:('Request Entity Too Large', 'Entity is too large.'),
    414:('Request-URI Too Long', 'URI is too long.'),
    415:('Unsupported Media Type', 'Entity body in unsupported format.'),
    416:('Requested Range Not Satisfiable', 'Cannot satisfy request range.'),
    417:('Expectation Failed', 'Expect condition could not be satisfied.'),

    500:('Internal Server Error', 'Server got itself in trouble'),
    501:('Not Implemented', 'Server does not support this operation'),
    502:('Bad Gateway', 'Invalid responses from another server/proxy.'),
    503:('Service Unavailable',
          'The server cannot process the request due to a high load'),
    504:('Gateway Timeout',
          'The gateway server did not receive a timely response'),
    505:('HTTP Version Not Supported', 'Cannot fulfill request.'),
}

def dummy_write(d): return

def capitalize_httptitle(k):
    return '-'.join([t.capitalize() for t in k.split('-')])

class HttpMessage(object):
    def __init__(self): self.headers, self.body = [], None

    def add_header(self, k, v):
        self.headers.append([k, v])

    def set_header(self, k, v):
        for h in self.headers:
            if h[0] == k:
                h[1] = v
                return
        self.add_header(k, v)

    def get_header(self, k, v=None):
        for ks, vs in self.headers:
            if ks == k: return vs
        return v

    def get_headers(self, k):
        return [vs for ks, vs in self.headers if ks == k]

    def has_header(self, k): return self.get_header(k) is not None

    def send_header(self, stream):
        stream.write(self.get_startline() + '\r\n')
        for k, l in self.headers: stream.write("%s: %s\r\n" % (k, l))
        stream.write('\r\n')

    def recv_header(self, stream):
        while True:
            line = stream.readline()
            if not line: raise EOFError()
            line = line.strip()
            if not line: break
            if line[0] not in (' ', '\t'):
                h, v = line.split(':', 1)
                self.add_header(h.strip(), v.strip())
            else: self.add_header(h.strip(), line.strip())

    def read_chunk(self, stream, hasbody=False, raw=False):
        if self.get_header('Transfer-Encoding', 'identity') != 'identity':
            logger.debug('recv body on chunk mode')
            chunk_size = 1
            while chunk_size:
                line = stream.readline()
                chunk = line.split(';')
                chunk_size = int(chunk[0], 16)
                if raw: yield line + stream.read(chunk_size + 2)
                else: yield stream.read(chunk_size + 2)[:-2]
        elif self.has_header('Content-Length'):
            length = int(self.get_header('Content-Length'))
            logger.debug('recv body on length mode, size: %s' % length)
            for i in xrange(0, length, BUFSIZE):
                yield stream.read(min(length - i, BUFSIZE))
        elif hasbody:
            logger.debug('recv body on close mode')
            d = stream.read(BUFSIZE)
            while d:
                yield d
                d = stream.read(BUFSIZE)

    def read_body(self, hasbody=False, raw=False):
        return ''.join(self.read_chunk(self.stream, hasbody, raw))

    def read_form(self):
        return dict([i.split('=', 1) for i in self.read_body().split('&')])

    def sendto(self, stream, *p, **kw):
        self.send_header(stream)
        if self.body is None: return
        elif callable(self.body):
            for d in self.body(*p, **kw): stream.write(d)
        else: stream.write(self.body)

    def debug(self):
        logger.debug(self.d + self.get_startline())
        for k, v in self.headers: logger.debug('%s%s: %s' % (self.d, k, v))

class HttpRequest(HttpMessage):
    d = '> '

    def __init__(self, method, uri, version):
        HttpMessage.__init__(self)
        self.method, self.uri, self.version = method, uri, version

    def get_startline(self):
        return ' '.join((self.method, self.uri, self.version))

class HttpResponse(HttpMessage):
    d = '< '

    def __init__(self, version, code, phrase):
        HttpMessage.__init__(self)
        self.version, self.code, self.phrase = version, int(code), phrase
        self.connection, self.cache = False, 0

    def __nonzero__(self): return self.connection

    def get_startline(self):
        return ' '.join((self.version, str(self.code), self.phrase))

def recv_msg(stream, cls):
    line = stream.readline().strip()
    if len(line) == 0: raise EOFError()
    r = line.split(' ', 2)
    if len(r) < 2: raise Exception('unknown format')
    if len(r) < 3: r.append(DEFAULT_PAGES[int(r[1])][0])
    msg = cls(*r)
    msg.stream = stream
    msg.recv_header(stream)
    return msg

def request_http(uri, method=None, version=None, headers=None, data=None):
    if not method: method = 'GET' if data is None else 'POST'
    if not version: version = 'HTTP/1.1'
    if not headers: headers = []
    req = HttpRequest(method, uri, version)
    req.headers, req.body = headers, data
    if req.body and isinstance(req.body, basestring):
        req.set_header('Content-Length', str(len(req.body)))
    return req

def response_http(code, phrase=None, version=None, headers=None,
                  cache=0, body=None):
    if not phrase: phrase = DEFAULT_PAGES[code][0]
    if not version: version = 'HTTP/1.1'
    res = HttpResponse(version, code, phrase)
    if body and isinstance(body, basestring):
        res.set_header('Content-Length', str(len(body)))
    if headers:
        for k, v in headers: res.set_header(k, v)
    res.cache, res.body = cache, body
    return res

def http_client(req, addr, creator):
    sock = creator()
    sock.connect(addr)
    try:
        stream = sock.makefile()
        req.sendto(stream)
        stream.flush()
        return recv_msg(stream, HttpResponse)
    finally: sock.close()

########NEW FILE########
__FILENAME__ = main
#!/usr/bin/python
# -*- coding: utf-8 -*-
'''
@date: 2012-05-25
@author: shell.xu
'''
import sys, logging, gevent, serve, hoh, mgr
from os import path
from gevent import server

logger = logging.getLogger('main')

def initlog(lv, logfile=None):
    rootlog = logging.getLogger()
    if logfile: handler = logging.FileHandler(logfile)
    else: handler = logging.StreamHandler()
    handler.setFormatter(
        logging.Formatter(
            '%(asctime)s,%(msecs)03d (%(process)d)%(name)s[%(levelname)s]: %(message)s',
            '%H:%M:%S'))
    rootlog.addHandler(handler)
    rootlog.setLevel(lv)

def main(*cfgs):
    if not cfgs:
        print 'no configure'
        return
    ps = serve.ProxyServer(cfgs)
    initlog(getattr(logging, ps.config.get('loglevel', 'WARNING')))
    logger.info('ProxyServer inited')
    addr = (ps.config.get('localip', ''), ps.config.get('localport', 8118))
    try:
        try: server.StreamServer(addr, ps.http_handler).serve_forever()
        except KeyboardInterrupt: pass
    finally: ps.final()

if __name__ == '__main__': main(*sys.argv[1:])

########NEW FILE########
__FILENAME__ = mgr
#!/usr/bin/python
# -*- coding: utf-8 -*-
'''
@date: 2012-05-25
@author: shell.xu
'''
import base64, logging, cStringIO
import serve, template
from http import *

logger = logging.getLogger('manager')

def auth_manager(func):
    def realfunc(ps, req):
        managers = ps.config['managers']
        if not managers: return func(ps, req)
        auth = req.get_header('Authorization')
        if auth:
            username, password = base64.b64decode(auth[6:]).split(':')
            if managers.get(username, None) == password: return func(ps, req)
        logging.info('access to %s without auth' % req.uri.split('?', 1)[0])
        return response_http(401, headers=[('WWW-Authenticate', 'Basic realm="managers"')])
    return realfunc

socks_stat = template.Template(template='''
<html><body>
<table>
  <tr>
    <td><a href="/reload">reload</a></td><td><a href="/quit">quit</a></td>
    <td><a href="/dnsfake">dnsfake</a></td>
    {%if ps.whitenf:%}<td><a href="/whitenets">whitenets</a></td>{%end%}
    {%if ps.blacknf:%}<td><a href="/blacknets">blacknets</a></td>{%end%}
  </tr>
  <tr><td>dns cache</td></tr>
  <tr><td>{%=len(ps.dns.cache)%}/{%=ps.dns.cachesize%}</td></tr>
</table><p/>
<table>
  <tr><td>socks</td><td>stat</td></tr>
  <tr><td>{%=ps.direct.name%}</td><td>{%=ps.direct.stat()%}</td></tr>
  {%for i in ps.proxies:%}
    <tr><td>{%=i.name%}</td><td>{%=i.stat()%}</td></tr>
  {%end%}
</table><p/>
<table>
  {%import time%}
  {%ti = time.time()%}
  <tr>
    <td>time</td><td>type</td><td>source</td><td>method</td><td>url</td>
  </tr>
  {%for req, usesocks, addr, t, name in sorted(ps.worklist, key=lambda x: x[3]):%}
  <tr>
    <td>{%="%0.2f" % (ti-t)%}</td>
    <td>{%=name%}</td>
    <td>{%=addr[0]%}:{%=addr[1]%}</td>
    <td>{%=req.method%}</td>
    <td>{%=req.uri.split('?', 1)[0]%}</td>
  </tr>
  {%end%}
</table></body></html>
''')

@serve.ProxyServer.register('/')
@auth_manager
def mgr_socks_stat(ps, req):
    req.read_body()
    return response_http(200, body=socks_stat.render({'ps': ps}))

@serve.ProxyServer.register('/reload')
@auth_manager
def mgr_reload(ps, req):
    req.read_body()
    ps.loadconfig()
    return response_http(302, headers=[('Location', '/')])

@serve.ProxyServer.register('/quit')
@auth_manager
def mgr_quit(ps, req): sys.exit(-1)

filter_list = template.Template(template='''
<html><body>
{%import cStringIO%}
{%if filter is not None:%}
{%strs = cStringIO.StringIO()%}
{%filter.save(strs)%}
<pre>{%=strs.getvalue()%}</pre>
{%end%}
</body></html>
''')

@serve.ProxyServer.register('/dnsfake')
@auth_manager
def mgr_dnsfake_list(ps, req):
    req.read_body()
    return response_http(200, body=filter_list.render({'filter': ps.dns}))

@serve.ProxyServer.register('/whitenets')
@auth_manager
def mgr_netfilter_list(ps, req):
    req.read_body()
    return response_http(200, body=filter_list.render({'filter': ps.whitenf}))

@serve.ProxyServer.register('/blacknets')
@auth_manager
def mgr_netfilter_list(ps, req):
    req.read_body()
    return response_http(200, body=filter_list.render({'filter': ps.blacknf}))

########NEW FILE########
__FILENAME__ = mydns
#!/usr/bin/python
# -*- coding: utf-8 -*-
'''
@date: 2012-09-27
@author: shell.xu
'''
import sys, struct, random, logging, cStringIO
from gevent import socket

logger = logging.getLogger('dns')

class Meta(type):
    def __new__(cls, name, bases, attrs):
        r = dict([(v, n) for n, v in attrs.iteritems() if n.isupper()])
        attrs['__reversed__'] = r
        return type.__new__(cls, name, bases, attrs)

class DEFINE(object):
    __metaclass__ = Meta
    @classmethod
    def lookup(cls, id, default='NOT FOUND'):
        return cls.__reversed__.get(id, default)

class OPCODE(DEFINE):
    QUERY = 0
    IQUERY = 1
    STATUS = 2
    NOTIFY = 4
    UPDATE = 5

# with NULL, cython can't compile this file
class TYPE(DEFINE):
    A = 1           # a host address
    NS = 2          # an authoritative name server
    MD = 3          # a mail destination (Obsolete - use MX)
    MF = 4          # a mail forwarder (Obsolete - use MX)
    CNAME = 5       # the canonical name for an alias
    SOA = 6         # marks the start of a zone of authority
    MB = 7          # a mailbox domain name (EXPERIMENTAL)
    MG = 8          # a mail group member (EXPERIMENTAL)
    MR = 9          # a mail rename domain name (EXPERIMENTAL)
    # NULL = 10       # a null RR (EXPERIMENTAL)
    WKS = 11        # a well known service description
    PTR = 12        # a domain name pointer
    HINFO = 13      # host information
    MINFO = 14      # mailbox or mail list information
    MX = 15         # mail exchange
    TXT = 16        # text strings
    AAAA = 28       # IPv6 AAAA records (RFC 1886)
    SRV = 33        # DNS RR for specifying the location of services (RFC 2782)
    SPF = 99        # TXT RR for Sender Policy Framework
    UNAME = 110
    MP = 240

class QTYPE(DEFINE):
    AXFR = 252      # A request for a transfer of an entire zone
    MAILB = 253     # A request for mailbox-related records (MB, MG or MR)
    MAILA = 254     # A request for mail agent RRs (Obsolete - see MX)
    ANY = 255       # A request for all records

class CLASS(DEFINE):
    IN = 1          # the Internet
    CS = 2          # the CSNET class (Obsolete - used only for examples in
                    # some obsolete RFCs)
    CH = 3          # the CHAOS class. When someone shows me python running on
                    # a Symbolics Lisp machine, I'll look at implementing this.
    HS = 4          # Hesiod [Dyer 87]
    ANY = 255       # any class

def packbit(r, bit, dt): return r << bit | (dt & (2**bit - 1))
def unpack(r, bit): return r & (2**bit - 1), r >> bit

def packflag(qr, opcode, auth, truncated, rd, ra, rcode):
    r = packbit(packbit(0, 1, qr), 4, opcode)
    r = packbit(packbit(r, 1, auth), 1, truncated)
    r = packbit(packbit(r, 1, rd), 1, ra)
    r = packbit(packbit(r, 3, 0), 4, rcode)
    return r

def unpackflag(r):
    r, qr = unpack(r, 1)
    r, opcode = unpack(r, 4)
    r, auth = unpack(r, 1)
    r, truncated = unpack(r, 1)
    r, rd = unpack(r, 1)
    r, ra = unpack(r, 1)
    r, rv = unpack(r, 3)
    r, rcode = unpack(r, 4)
    assert rv == 0
    return qr, opcode, auth, truncated, rd, ra, rcode

class Record(object):
    
    def __init__(self, id, qr, opcode, auth, truncated, rd, ra, rcode):
        self.id, self.qr, self.opcode, self.authans = id, qr, opcode, auth
        self.truncated, self.rd, self.ra, self.rcode = truncated, rd, ra, rcode
        self.quiz, self.ans, self.auth, self.ex = [], [], [], []

    def show(self):
        yield 'quiz'
        for q in self.quiz: yield self.showquiz(q)
        yield 'answer'
        for r in self.ans: yield self.showRR(r)
        yield 'auth'
        for r in self.auth: yield self.showRR(r)
        yield 'ex'
        for r in self.ex: yield self.showRR(r)

    def filteredRR(self, RRs, types): return (i for i in RRs if i[0] in types)

    def packname(self, name):
        return ''.join([chr(len(i))+i for i in name.split('.')]) + '\x00'

    def unpackname(self, s):
        r = []
        c = ord(s.read(1))
        while c != 0:
            if c & 0xC0 == 0xC0:
                c = (c << 8) + ord(s.read(1)) & 0x3FFF
                r.append(self.unpackname(cStringIO.StringIO(self.buf[c:])))
                break
            else: r.append(s.read(c))
            c = ord(s.read(1))
        return '.'.join(r)

    def packquiz(self, name, qtype, cls):
        return self.packname(name) + struct.pack('>HH', qtype, cls)

    def unpackquiz(self, s):
        name, r = self.unpackname(s), struct.unpack('>HH', s.read(4))
        return name, r[0], r[1]

    def showquiz(self, q):
        return '\t%s\t%s\t%s' % (q[0], TYPE.lookup(q[1]), CLASS.lookup(q[2]))

    # def packRR(self, name, type, cls, ttl, res):
    #     return self.packname(name) + \
    #         struct.pack('>HHIH', type, cls, ttl, len(res)) + res

    def unpackRR(self, s):
        n = self.unpackname(s)
        r = struct.unpack('>HHIH', s.read(10))
        if r[0] == TYPE.A:
            return n, r[0], r[1], r[2], socket.inet_ntoa(s.read(r[3]))
        elif r[0] == TYPE.CNAME:
            return n, r[0], r[1], r[2], self.unpackname(s)
        elif r[0] == TYPE.MX:
            return n, r[0], r[1], r[2], \
                struct.unpack('>H', s.read(2))[0], self.unpackname(s)
        elif r[0] == TYPE.PTR:
            return n, r[0], r[1], r[2], self.unpackname(s)
        elif r[0] == TYPE.SOA:
            rr = [n, r[0], r[1], r[2], self.unpackname(s), self.unpackname(s)]
            rr.extend(struct.unpack('>IIIII', s.read(20)))
            return tuple(rr)
        else: raise Exception("don't know howto handle type, %s." % str(r))

    def showRR(self, r):
        if r[1] in (TYPE.A, TYPE.CNAME, TYPE.PTR, TYPE.SOA):
            return '\t%s\t%d\t%s\t%s\t%s' % (
                r[0], r[3], CLASS.lookup(r[2]), TYPE.lookup(r[1]), r[4])
        elif r[1] == TYPE.MX:
            return '\t%s\t%d\t%s\t%s\t%s' % (
                r[0], r[3], CLASS.lookup(r[2]), TYPE.lookup(r[1]), r[5])
        else: raise Exception("don't know howto handle type, %s." % str(r))

    def pack(self):
        self.buf = struct.pack(
            '>HHHHHH', self.id, packflag(self.qr, self.opcode, self.authans,
                                         self.truncated, self.rd, self.ra, self.rcode),
            len(self.quiz), len(self.ans), len(self.auth), len(self.ex))
        for i in self.quiz: self.buf += self.packquiz(*i)
        for i in self.ans: self.buf += self.packRR(*i)
        for i in self.auth: self.buf += self.packRR(*i)
        for i in self.ex: self.buf += self.packRR(*i)
        return self.buf

    @classmethod
    def unpack(cls, dt):
        s = cStringIO.StringIO(dt)
        id, flag, lquiz, lans, lauth, lex = struct.unpack('>HHHHHH', s.read(12))
        rec = cls(id, *unpackflag(flag))
        rec.buf = dt
        rec.quiz = [rec.unpackquiz(s) for i in xrange(lquiz)]
        rec.ans = [rec.unpackRR(s) for i in xrange(lans)]
        rec.auth = [rec.unpackRR(s) for i in xrange(lauth)]
        rec.ex = [rec.unpackRR(s) for i in xrange(lex)]
        return rec

def mkquery(*ntlist):
    rec = Record(random.randint(0, 65536), 0, OPCODE.QUERY, 0, 0, 1, 0, 0)
    for name, type in ntlist: rec.quiz.append((name, type, CLASS.IN))
    return rec

def query_by_udp(q, server, sock=None):
    if sock is None: sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.sendto(q, (server, 53))
    return sock.recvfrom(1024)[0]

def query_by_tcp(q, server, stream=None):
    sock = None
    if stream is None:
        sock = socket.socket()
        sock.connect((server, 53))
        stream = sock.makefile()
    try:
        stream.write(struct.pack('>H', len(q)) + q)
        stream.flush()
        d = stream.read(2)
        if len(d) == 0: raise EOFError()
        reply = stream.read(struct.unpack('>H', d)[0])
        if len(reply) == 0: raise EOFError()
        return reply
    finally:
        if sock is not None: sock.close()

def query(name, type=TYPE.A, server='127.0.0.1', protocol='udp'):
    q = mkquery((name, type)).pack()
    func = globals().get('query_by_%s' % protocol)
    if not func: raise Exception('protocol not found')
    return Record.unpack(func(q, server))

def nslookup(name):
    r = query(name)
    return [rdata for name, type, cls, ttl, rdata in r.ans if type == TYPE.A]

########NEW FILE########
__FILENAME__ = netfilter
#!/usr/bin/python
# -*- coding: utf-8 -*-
'''
@date: 2012-09-26
@author: shell.xu
'''
import sys, random, struct, logging
from gevent import socket

logger = logging.getLogger('netfilter')

def get_netaddr(ip, mask):
    return ''.join(map(lambda x, y: chr(ord(x) & ord(y)), ip, mask))

def makemask(num):
    s = 0
    for i in xrange(32):
        s <<= 1
        s |= i<num
    return struct.pack('>L', s)

class NetFilter(object):

    def __init__(self, *filenames):
        self.nets = {}
        for filename in filenames: self.loadfile(filename)

    def loadline(self, line):
        if line.find(' ') != -1:
            addr, mask = line.split(' ', 1)
            addr, mask = socket.inet_aton(addr), socket.inet_aton(mask)
        elif line.find('/') != -1:
            addr, mask = line.split('/', 1)
            addr, mask = socket.inet_aton(addr), makemask(int(mask))
        self.nets.setdefault(mask, set())
        self.nets[mask].add(get_netaddr(addr, mask))

    def load(self, stream):
        for line in stream: self.loadline(line.strip())

    def loadfile(self, filename):
        openfile = open
        if filename.endswith('.gz'):
            import gzip
            openfile = gzip.open
        try:
            with openfile(filename) as fi: self.load(fi)
        except (OSError, IOError): return False

    def save(self, stream):
        r = []
        for mask, addrs in self.nets.iteritems():
            r.extend([(addr, mask) for addr in list(addrs)])
        for addr, mask in sorted(r, key=lambda x: x[0]):
            stream.write('%s %s\n' % (socket.inet_ntoa(addr), socket.inet_ntoa(mask)))

    def savefile(self, filepath):
        openfile = open
        if filepath.endswith('.gz'):
            import gzip
            openfile = gzip.open
        try:
            with openfile(filepath, 'w+') as fo: self.save(fo)
        except (OSError, IOError): return False

    def __contains__(self, addr):
        try: addr = socket.inet_aton(addr)
        except TypeError: pass
        for mask, addrs in self.nets.iteritems():
            if get_netaddr(addr, mask) in addrs: return True
        return False

def main():
    nf = NetFilter(sys.argv[1])
    for i in sys.argv[2:]: print '%s: %s' % (i, i in nf)

if __name__ == '__main__': main()

########NEW FILE########
__FILENAME__ = proxy
#!/usr/bin/python
# -*- coding: utf-8 -*-
'''
@date: 2012-04-27
@author: shell.xu
'''
import os, copy, time, base64, logging
import conn
from gevent import select
from http import *

logger = logging.getLogger('proxy')
VERBOSE = False

def get_proxy_auth(users):
    def all_pass(req): return None
    def proxy_auth(req):
        auth = req.get_header('Proxy-Authorization')
        if auth:
            req.headers = [(k, v) for k, v in req.headers if k != 'Proxy-Authorization']
            username, password = base64.b64decode(auth[6:]).split(':')
            if users.get(username, None) == password: return None
        logging.info('proxy authenticate failed')
        return response_http(407, headers=[('Proxy-Authenticate', 'Basic realm="users"')])
    return proxy_auth if users else all_pass

def parse_target(url):
    r = (url.netloc or url.path).split(':', 1)
    if len(r) > 1: port = int(r[1])
    else: port = 443 if url.scheme.lower() == 'https' else 80
    return r[0], port, url.path + ('?'+url.query if url.query else '')

# WARN: maybe dangerous to ssl
# TODO: timeout
def fdcopy(fd1, fd2):
    fdlist = [fd1, fd2]
    while True:
        for rfd in select.select(fdlist, [], [])[0]:
            try: d = os.read(rfd, BUFSIZE)
            except OSError: d = ''
            if not d: raise EOFError()
            try: os.write(fd2 if rfd == fd1 else fd1, d)
            except OSError: raise EOFError()

def connect(req, sock_factory, timeout=None):
    hostname, port, uri = parse_target(req.url)
    try:
        with sock_factory.socket() as sock:
            sock.connect((hostname, port))
            res = HttpResponse(req.version, 200, 'OK')
            res.send_header(req.stream)
            req.stream.flush()
            fdcopy(req.stream.fileno(), sock.fileno())
    finally: logger.info('%s closed' % req.uri)

def streamcopy(msg, stream1, stream2, tout, hasbody=False):
    iter = msg.read_chunk(stream1, hasbody=hasbody, raw=True).__iter__()
    inf, ouf = tout(iter.next), tout(stream2.write)
    try:
        while True: ouf(inf())
    except StopIteration, err: return

def http(req, sock_factory, timeout=None):
    t = time.time()
    tout = conn.set_timeout(timeout)
    hostname, port, uri = parse_target(req.url)
    reqx = copy.copy(req)
    reqx.uri = uri
    reqx.headers = [(h, v) for h, v in req.headers if not h.startswith('Proxy')]
    with sock_factory.socket() as sock:
        sock.connect((hostname, port))
        stream1 = sock.makefile()

        if VERBOSE: req.debug()
        tout(reqx.send_header)(stream1)
        streamcopy(reqx, req.stream, stream1, tout)
        stream1.flush()

        res = recv_msg(stream1, HttpResponse)
        if VERBOSE: res.debug()
        tout(res.send_header)(req.stream)
        hasbody = req.method.upper() != 'HEAD' and res.code not in CODE_NOBODY
        streamcopy(res, stream1, req.stream, tout, hasbody)
        req.stream.flush()
    res.connection = req.get_header('Proxy-Connection', '').lower() == 'keep-alive' and\
        res.get_header('Connection', 'close').lower() != 'close'
    logger.debug('%s with %d in %0.2f, %s' % (
            req.uri.split('?', 1)[0], res.code, time.time() - t,
            'keep' if res.connection else 'close'))
    return res

########NEW FILE########
__FILENAME__ = serve
#!/usr/bin/python
# -*- coding: utf-8 -*-
'''
@date: 2012-04-26
@author: shell.xu
'''
import time, base64, logging
import socks, proxy, conn, hoh, dnsserver, dofilter, netfilter
from os import path
from urlparse import urlparse
from contextlib import contextmanager
from gevent import dns, socket, Timeout
from http import *

__all__ = ['ProxyServer',]

logger = logging.getLogger('server')

def import_config(cfgs, d=None):
    if d is None: d = {}
    for cfg in reversed(cfgs):
        if not path.exists(cfg): continue
        try:
            with open(path.expanduser(cfg)) as fi:
                eval(compile(fi.read(), cfg, 'exec'), d)
            logger.info('import config %s' % cfg)
        except (OSError, IOError): logger.error('import config')
    return dict([(k, v) for k, v in d.iteritems() if not k.startswith('_')])

def mgr_default(self, req):
    req.read_body()
    return response_http(404, body='Page not found')

def fmt_reqinfo(info):
    req, usesocks, addr, t, name = info
    return '%s %s %s' % (req.method, req.uri.split('?', 1)[0], name)

class ProxyServer(object):
    env = {'socks5': socks.SocksManager, 'http': conn.HttpManager,
           'DomainFilter': dofilter.DomainFilter,
           'NetFilter': netfilter.NetFilter, 'DNSServer': dnsserver.DNSServer,
           'HttpOverHttp': hoh.HttpOverHttp, 'GAE': hoh.GAE}
    srv_urls = {}

    def __init__(self, cfgs):
        self.cfgs, self.dns, self.worklist = cfgs, None, []
        self.loadconfig()

    def ssh2proxy(self, cfg):
        if 'sockport' in cfg:
            return socks.SocksManager(
                '127.0.0.1', cfg['sockport'], max_conn=self.config['max_conn'],
                name='socks5:%s@%s' % (cfg['username'], cfg['sshhost']))
        elif 'listenport' in cfg:
            return conn.HttpManager(
                '127.0.0.1', cfg['listenport'][0], max_conn=self.config['max_conn'],
                name='http:%s@%s' % (cfg['username'], cfg['sshhost']))
        raise Exception('unknown ssh define')
        
    def loadconfig(self):
        self.config = import_config(self.cfgs, self.env)
        self.proxy_auth = proxy.get_proxy_auth(self.config.get('users'))

        self.proxies = self.config.get('proxies', None)
        if self.proxies is None: self.proxies = []
        if self.config.get('max_conn', None):
            self.proxies.extend(map(self.ssh2proxy, self.config['sshs']))
        self.upstream = self.config.get('upstream')

        if self.dns is not None: self.dns.stop()
        self.dns = self.config.get('dnsserver')
        dnsport = self.config.get('dnsport', None)
        if dnsport: self.dns.runserver(dnsport)
        self.dofilter = self.config.get('dofilter')
        self.whitenf = self.config.get('whitenets')
        self.blacknf = self.config.get('blacknets')
        self.direct = conn.DirectManager(self.dns)

        self.func_connect = conn.set_timeout(self.config.get('conn_tout'))(proxy.connect)
        self.func_http = conn.set_timeout(self.config.get('http_tout'))(proxy.http)

    @classmethod
    def register(cls, url):
        def inner(func):
            cls.srv_urls[url] = func
            return func
        return inner

    @contextmanager
    def with_worklist(self, reqinfo):
        self.worklist.append(reqinfo)
        try: yield
        finally: self.worklist.remove(reqinfo)

    def get_conn_mgr(self, direct):
        if direct: return self.direct
        return min(self.proxies, key=lambda x: x.size())

    def usesocks(self, hostname, req):
        if self.dofilter and hostname in self.dofilter:
            return True
        if self.whitenf is not None or self.blacknf is not None:
            addr = self.dns.gethostbyname(hostname)
            if req: req.address = addr
            if addr is None: return False
            logger.debug('hostname: %s, addr: %s' % (hostname, addr))
            if self.whitenf is not None and addr in self.whitenf:
                return True
            if self.blacknf is not None and addr not in self.blacknf:
                return True
        return False

    def do_req(self, req, addr):
        authres = self.proxy_auth(req)
        if authres is not None:
            authres.sendto(req.stream)
            return authres
        reqconn = req.method.upper() == 'CONNECT'

        req.url = urlparse(req.uri)
        if not reqconn and not req.url.netloc:
            logger.info('manager %s' % (req.url.path,))
            res = self.srv_urls.get(req.url.path, mgr_default)(self, req)
            res.sendto(req.stream)
            return res

        if reqconn:
            hostname, func, tout = (
                req.uri, self.func_connect, self.config.get('conn_noac'))
        else:
            hostname, func, tout = (
                req.url.netloc, self.func_http, self.config.get('http_noac'))
        usesocks = self.usesocks(hostname.split(':', 1)[0], req)
        reqinfo = [req, usesocks, addr, time.time(), '']

        # if usesocks and self.upstream:
        if self.upstream:
            reqinfo[4] = self.upstream.name
            with self.with_worklist(reqinfo):
                logger.info(fmt_reqinfo(reqinfo))
                res = self.upstream.handler(req)
                if res is not None:
                    res.sendto(req.stream)
                    req.stream.flush()
                    return res

        reqinfo[4] = 'socks' if usesocks else 'direct'
        with self.with_worklist(reqinfo):
            logger.info(fmt_reqinfo(reqinfo))
            try: return func(req, self.get_conn_mgr(not usesocks), tout)
            except Timeout, err:
                logger.warn('connection timeout: %s' % req.uri)

    def http_handler(self, sock, addr):
        stream = sock.makefile()
        try:
            while self.do_req(recv_msg(stream, HttpRequest), addr): pass
        except (EOFError, socket.error): logger.debug('network error')
        except Exception, err: logger.exception('unknown')
        finally:
            sock.close()
            logger.debug('browser connection closed')

    def final(self): logger.info('system exit')

########NEW FILE########
__FILENAME__ = socks
#!/usr/bin/python
# -*- coding: utf-8 -*-
'''
@date: 2010-06-04
@author: shell.xu
'''
import sys, struct, getopt, logging, conn
from contextlib import contextmanager
from gevent import socket, coros

__all__ = ['SocksManager',]
logger = logging.getLogger('socks')

PROXY_TYPE_SOCKS4 = 1
PROXY_TYPE_SOCKS5 = 2

def fmt_string(data): return chr(len(data)) + data

class GeneralProxyError(socket.error):
    __ERRORS =("success", "invalid data", "not connected", "not available", "bad proxy type", "bad input")
    def __init__(self, id, *params):
        if id in self.__ERRORS: params.insert(0, self.__ERRORS[id])
        super(GeneralProxyError, self).__init__(*params)

class Socks4Error(GeneralProxyError):
    __ERRORS =("request granted", "request rejected or failed", "request rejected because SOCKS server cannot connect to identd on the client", "request rejected because the client program and identd report different user-ids", "unknown error")
    def __init__(self, *params):
        super(Socks4Error, self).__init__(*params)

class Socks5Error(GeneralProxyError):
    __ERRORS =("succeeded", "general SOCKS server failure", "connection not allowed by ruleset", "Network unreachable", "Host unreachable", "Connection refused", "TTL expired", "Command not supported", "Address type not supported", "Unknown error")
    def __init__(self, *params):
        super(Socks5Error, self).__init__(*params)

class Socks5AuthError(GeneralProxyError):
    __ERRORS =("succeeded", "authentication is required",
                "all offered authentication methods were rejected",
                "unknown username or invalid password", "unknown error")
    def __init__(self, *params):
        super(Socks5AuthError, self).__init__(*params)

def socks5_create(sock, proxyaddr, username=None, password=None):
    sock.connect(proxyaddr)
    stream = sock.makefile()

    # hand shake request
    if username is None or password is None:
        stream.write("\x05\x01\x00")
    else: stream.write("\x05\x02\x00\x02")
    stream.flush()
    
    # hand shake response
    chosenauth = stream.read(2)
    if len(chosenauth) == 0: raise EOFError()
    if chosenauth[0] != "\x05": raise GeneralProxyError(1)
    if chosenauth[1] == "\x00": pass
    elif chosenauth[1] == "\x02":
        stream.write('\x01' + fmt_string(username) + fmt_string(password))
        stream.flush()
        authstat = stream.read(2)
        if len(authstat) == 0: raise EOFError()
        if authstat[0] != "\x01": raise GeneralProxyError(1)
        if authstat[1] != "\x00": raise Socks5AuthError(3)
        logger.debug('authenticated with password')
    elif chosenauth[1] == "\xFF": raise Socks5AuthError(2)
    else: raise GeneralProxyError(1)

def socks5_connect(sock, target, rdns=True):
    stream = sock.makefile()
    # connect request
    try: reqaddr = "\x01" + socket.inet_aton(target[0])
    except socket.error:
        if rdns: reqaddr = '\x03' + fmt_string(target[0])
        else: reqaddr = "\x01" + socket.inet_aton(socket.gethostbyname(target[0]))
    s = "\x05\x01\x00" + reqaddr + struct.pack(">H", target[1])
    stream.write(s)
    stream.flush()

    # connect response
    resp = stream.read(4)
    if not resp: raise EOFError()
    if resp[0] != "\x05": raise GeneralProxyError(1)
    if resp[1] != "\x00":
        if ord(resp[1]) <= 8: raise Socks5Error(ord(resp[1]))
        else: raise Socks5Error(9)
    if resp[3] == "\x03": boundaddr = stream.read(stream.read(1))
    elif resp[3] == "\x01": boundaddr = socket.inet_ntoa(stream.read(4))
    else: raise GeneralProxyError(1)
    boundport = struct.unpack(">H", stream.read(2))[0]
    logger.debug('socks connected with %s:%s' % target)
    return boundaddr, boundport

def socks5(proxyaddr, username=None, password=None, rdns=True):
    def reciver(func):
        def creator(family=socket.AF_INET, type=socket.SOCK_STREAM, proto=0):
            sock = func(family, type, proto)
            socks5_create(sock, proxyaddr, username, password)
            def newconn(addr): socks5_connect(sock, addr, rdns)
            sock.connect, sock.connect_ex = newconn, newconn
            return sock
        return creator
    return reciver

class SocksManager(conn.Manager):

    def __init__(self, addr, port, username=None, password=None,
                 rdns=True, max_conn=10, name=None, ssl=False, **kargs):
        super(SocksManager, self).__init__(max_conn, name or 'socks5:%s:%s' % (addr, port))
        if ssl is True: self.creator = conn.ssl_socket()(self.creator)
        elif ssl: self.creator = conn.ssl_socket(ssl)(self.creator)
        self.creator = socks5((addr, port), username, password, rdns)(self.creator)

########NEW FILE########
__FILENAME__ = template
#!/usr/bin/python
# -*- coding: utf-8 -*-
'''
@date: 2010-09-27
@author: shell.xu
'''
import os

class TemplateCode(object):
    def __init__(self): self.deep, self.rslt, self.defs = 0, [], []

    def str(self, s):
        if s: self.rslt.append(u'%swrite(u\'\'\'%s\'\'\')' % (u'\t' * self.deep, s))

    def code(self, s):
        r = self.map_code(s)
        if r: self.rslt.append(r)
    def map_code(self, s):
        s, tab = s.strip(), self.deep
        if s.startswith(u'='): s = u'write(%s)' % s[1:]
        elif s.startswith(u'end'):
            self.deep -= 1
            return
        elif s.startswith(u'for') or s.startswith(u'if'): self.deep += 1
        elif s.startswith(u'el'): tab -= 1
        elif s.startswith(u'def'):
            self.defs.append(s + u'\n')
            return
        elif s.startswith(u'include'):
            self.include(s[8:])
            return
        elif s.startswith(u'import'):
            self.defs.append(s + u'\n')
            return 
        return u'%s%s' % (u'\t' * tab, s)

    def include(self, filepath):
        with open(filepath, 'r') as tfile:
            self.process(tfile.read().decode('utf-8'))

    def process(self, s):
        while True:
            i = s.partition(u'{%')
            if not i[1]: break
            if i[0].strip(): self.str(i[0])
            t = i[2].partition(u'%}')
            if not t[1]: raise Exception('not match')
            self.code(t[0])
            s = t[2]
        self.str(s)

    def get_code(self): return u'\n'.join(self.rslt)

class Template(object):
    '''
    模板对象，用于生成模板
    代码：
        info = {'r': r, 'objs': [(1, 2), (3, 4)]}
        response.append_body(tpl.render(info))
    模板：
        <html><head><title>{%=r.get('a', 'this is title')%}</title></head>
        <body><table><tr><td>col1</td><td>col2</td></tr>
        {%for i in objs:%}<tr><td>{%=i[0]%}</td><td>{%=i[1]%}</td></tr>{%end%}
        </table></body></html>
    '''
    def __init__(self, filepath = None, template = None, env = None):
        '''
        @param filepath: 文件路径，直接从文件中load
        @param template: 字符串，直接编译字符串
        '''
        if not env: env = globals()
        self.tc, self.env = TemplateCode(), env
        if filepath: self.loadfile(filepath)
        elif template: self.loadstr(template)

    def loadfile(self, filepath):
        ''' 从文件中读取字符串编译 '''
        self.modify_time = os.stat(filepath).st_mtime
        self.tc = TemplateCode()
        with open(filepath, 'r') as tfile: self.loadstr(tfile.read())
    def loadstr(self, template):
        ''' 编译字符串成为可执行的内容 '''
        if isinstance(template, str): template = template.decode('utf-8')
        self.tc.process(template)
        self.htmlcode, self.defcodes = compile(self.tc.get_code(), '', 'exec'), {}
        for i in self.tc.defs:
            eval(compile(i, '', 'exec'), self.env, self.defcodes)
    def reload(self, filepath):
        ''' 如果读取文件，测试文件是否更新。 '''
        if not hasattr(self, 'modify_time') or \
                os.stat(filepath).st_mtime > self.modify_time:
            self.loadfile(filepath)

    def render(self, kargs):
        ''' 根据参数渲染模板 '''
        b = []
        kargs['write'] = lambda x: b.append(unicode(x))
        eval(self.htmlcode, self.defcodes, kargs)
        return u''.join(b)

########NEW FILE########
