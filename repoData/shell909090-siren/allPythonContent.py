__FILENAME__ = actions
#!/usr/bin/python
# -*- coding: utf-8 -*-
'''
@date: 2013-06-19
@author: shell.xu
'''
import re, gzip, logging, cStringIO
from os import path
import chardet
from lxml import etree, html
import html_parser, filters, internal
from bases import *

logger = logging.getLogger('action')

class Action(RegNameClsBase):
    lxmlproc = {}
    httpproc = {}
    keyset = set()

    def __init__(self, app, actioncfg):
        self.app = app
        self.lxmls = list(extendlist(
                set_appcfg(app, actioncfg, self.lxmlproc)))
        self.https = set_appcfg(app, actioncfg, self.httpproc)
        if 'url' in actioncfg:
            self.func = self.loadfunc(actioncfg['url'], None)
        if 'result' in actioncfg:
            self.result = app.loadfunc(actioncfg['result'], actioncfg)
        assert self.lxmls or self.https or self.func, 'no handler for match for action'

    def __call__(self, worker, req):
        if hasattr(self, 'func') and self.func(worker, req): return
        resp = self.app.http.do(req)
        if self.https:
            for func in self.https: func(worker, req, resp)
        if self.lxmls:
            resp.encoding = chardet.detect(resp.content)['encoding']
            doc = html.fromstring(resp.text)
            for func in self.lxmls: func(worker, req, doc)
        if hasattr(self, 'result'): self.result(req)

@Action.register('lxmlproc', 'lxml')
def flxml(app, cmdcfg, cfg): return app.loadfunc(cmdcfg, cfg)

@Action.register('lxmlproc')
def parsers(app, cmdcfg, cfg):
    return [mkparser(app, c, cfg) for c in cmdcfg]

def mkparser(app, cmdcfg, cfg):
    env = {'logger': logging.getLogger('*action*')}
    code = ['def proc(worker, req, doc):',]
    html_parser.setup(env, code, app, cmdcfg)
    filters.setup(env, code, app, cmdcfg)
    rslt = {}
    logger.debug('code:\n' + '\n'.join(code))
    eval(compile('\n'.join(code), '*internal compiled*', 'exec'), env, rslt)
    return rslt['proc']

@Action.register('httpproc', 'http')
def fhttp(app, cmdcfg, cfg): return app.loadfunc(cmdcfg, cfg)

@Action.register('httpproc', 'download')
def fdownload(app, cmdcfg, cfg):
    if not cmdcfg: cmdcfg = app.cfg.get('download')
    if cmdcfg: download = app.loadfunc(cmdcfg, cfg)
    else:
        assert 'downdir' in app.cfg, 'no download setting, no downdir'
        downdir = app.cfg['downdir']
        def download(worker, req, resp):
            filepath = path.join(downdir, path.basename(req.url))
            with open(filepath, 'wb') as fo: fo.write(resp.content)
    return download

@Action.register('httpproc')
def sitemap(app, cmdcfg, cfg):
    keys = set(cmdcfg.keys())
    cls = filters.LinkFilter
    assert cls.keyset & keys, "no link processor in sitemap"
    sec = cls(app, cmdcfg)
    cls = filters.TxtFilter
    if cls.keyset & keys: sec = cls(app, cmdcfg, sec)

    def inner(worker, req, resp):
        doc = etree.fromstring(
            gzip.GzipFile(
                fileobj=cStringIO.StringIO(resp.content)).read())
        for loc in doc.xpath('ns:url/ns:loc', namespaces={
                'ns':'http://www.sitemaps.org/schemas/sitemap/0.9'}):
            sec(worker, req, None, loc.text)
    return inner

########NEW FILE########
__FILENAME__ = apps
#!/usr/bin/python
# -*- coding: utf-8 -*-
'''
@date: 2013-06-05
@author: shell.xu
'''
import sys, logging
from os import path
import yaml
import httputils, actions

logger = logging.getLogger('application')

class ParseError(StandardError): pass

class Application(object):
    loadfunc_cache = {}

    def __init__(self, filepath):
        self.processors = {}
        self.basedir, self.filename = path.split(filepath)
        if self.basedir not in sys.path: sys.path.append(self.basedir)
        with open(filepath) as fi: self.cfg = yaml.load(fi.read())

        if 'result' in self.cfg:
            self.result = self.loadfunc(self.cfg['result'], None)
        if 'disable_robots' not in self.cfg:
            self.accessible = httputils.accessible
        else: self.accessible = lambda url: True
        if 'interval' in self.cfg:
            self.limit = httputils.SpeedLimit(self.cfg['interval'])
        self.http = httputils.HttpHub(self.cfg)

        for proccfg in self.cfg['patterns']:
            assert 'name' in proccfg, 'without name'
            self.processors[proccfg['name']] = actions.Action(self, proccfg)
        del self.cfg['patterns']

    def __call__(self, worker, req):
        if hasattr(self, 'limit'): self.limit.get(req.url)
        if ':' in req.procname:
            proc = self.loadfunc(req.procname, None)
            assert proc, "unkown python function"
        else:
            assert req.procname in self.processors, "unknown processor name"
            proc = self.processors[req.procname]
        req.result = {}
        proc(worker, req)
        if hasattr(self, 'result'): self.result(req)

    def loadfunc(self, name, cfg):
        if name is None: return None
        modname, funcname = name.split(':')
        if not modname: modname = self.cfg['file']
        if modname == 'internal': mod = internal
        else: mod = __import__(modname)
        creator = getattr(mod, funcname)
        if creator not in self.loadfunc_cache:
            self.loadfunc_cache[creator] = creator(self, cfg)
        return self.loadfunc_cache[creator]

########NEW FILE########
__FILENAME__ = bases
#!/usr/bin/python
# -*- coding: utf-8 -*-
'''
@date: 2013-06-16
@author: shell.xu
'''

def set_cmdcfg(cfg, d):
    keys = set(cfg.keys()) & set(d.keys())
    return [d[key](cfg[key]) for key in keys]

def set_appcfg(app, cfg, d):
    keys = set(cfg.keys()) & set(d.keys())
    return [d[key](app, cfg[key], cfg) for key in keys]

def set_psrcfg(env, code, app, cfg, d):
    keys = set(cfg.keys()) & set(d.keys())
    return [d[key](env, code, app, cfg[key], cfg) for key in keys]

def extendlist(l):
    for i in l:
        if not hasattr(i, '__iter__'): yield i
        else:
            for j in i: yield j

class RegNameClsBase(object):
    @classmethod
    def register(cls, name, funcname=None):
        l = getattr(cls, name)
        def inner(func):
            fn = funcname or func.__name__
            l[fn] = func
            cls.keyset.add(fn)
            return func
        return inner

class RegClsBase(object):
    @classmethod
    def register(cls, funcname=None):
        def inner(func):
            fn = funcname or func.__name__
            cls.regs[fn] = func
            cls.keyset.add(fn)
            return func
        return inner

def register(d, funcname=None):
    def inner(func):
        fn = funcname or func.__name__
        d[fn] = func
        return func
    return inner


########NEW FILE########
__FILENAME__ = filters
#!/usr/bin/python
# -*- coding: utf-8 -*-
'''
@date: 2013-06-07
@author: shell.xu
'''
import re, os, sys, logging, itertools
from urlparse import urljoin
import httputils
from bases import *

logger = logging.getLogger('filters')

txt_filters = {}
links = {}
results = {}

def setup(env, code, app, cmdcfg):
    code.append('    logger.debug("string is coming: " + s)')
    set_psrcfg(env, code, app, cmdcfg, txt_filters)
    code.append('    logger.debug("passed filter")')

    r = set_psrcfg(env, code, app, cmdcfg, links)
    if len(r) > 0:
        code.append('    assert nreq.procname, "dont know which processor to call."')
        code.append('    assert nreq.url, "request without url"')
        code.append("    worker.append(nreq)")

    set_psrcfg(env, code, app, cmdcfg, results)

@register(txt_filters, 'is')
def fis(env, code, app, cmdcfg, cfg):
    env['reis'] = re.compile(cmdcfg)
    code.append('    if not reis.match(s): continue')

@register(txt_filters)
def isnot(env, code, app, cmdcfg, cfg):
    env['reisnot'] = re.compile(cmdcfg)
    code.append('    if reisnot.match(s): continue')

@register(txt_filters)
def dictreplace(env, code, app, cmdcfg, cfg):
    env['replace_re'] = re.compile(cmdcfg[0])
    env['replace_to'] = cmdcfg[1]
    code.append('    s = replace_to.format(**replace_re.match(s).groupdict())')

@register(txt_filters, 'map')
def fmap(env, code, app, cmdcfg, cfg):
    env['mapfunc'] = app.loadfunc(cmdcfg, cfg)
    code.append('    s = mapfunc(s)')

@register(links)
def call(env, code, app, cmdcfg, cfg):
    env['urljoin'] = urljoin
    env['ReqInfo'] = httputils.ReqInfo
    env['call'] = cmdcfg
    code.append("    if s.startswith('//'): s = 'http:' + s")
    code.append("    url = s if s.startswith('http') else urljoin(req.url, s)")
    code.append("    nreq = ReqInfo(None, url)")
    code.append("    nreq.procname = call")

# TODO:
@register(links)
def params(env, code, app, cmdcfg, cfg):
    pass

@register(links)
def headers(env, code, app, cmdcfg, cfg):
    env['headers'] = cmdcfg
    code.append('    nreq.headers = headers')

@register(links)
def method(env, code, app, cmdcfg, cfg):
    env['method'] = cmdcfg.upper()
    code.append('    nreq.method = method')

@register(results)
def result(env, code, app, cmdcfg, cfg):
    env['result'] = cmdcfg
    code.append('    req.result.setdefault(result, [])')
    code.append('    req.result[result].append(s)')

########NEW FILE########
__FILENAME__ = html_parser
#!/usr/bin/python
# -*- coding: utf-8 -*-
'''
@date: 2013-06-06
@author: shell.xu
'''
import os, logging
from lxml import html
from lxml.cssselect import CSSSelector
from bases import *

logger = logging.getLogger('html')

selectors = {}
to_strings = {}

def setup(env, code, app, cmdcfg):
    r = set_psrcfg(env, code, app, cmdcfg, selectors)
    if len(r) == 0: raise Exception('no html selector')
    if len(r) > 1: raise Exception('more then one html selector')
    code.append("    logger.debug('%s node selected' % str(node))")

    r = set_psrcfg(env, code, app, cmdcfg, to_strings)
    if len(r) == 0: raise Exception('no to string translator')
    if len(r) > 1: raise Exception('more then one translator')
    code.append('    if not s: continue')
    code.append("    logger.debug('node to string: %s' % s)")

@register(selectors)
def css(env, code, app, cmdcfg, cfg):
    env['css'] = CSSSelector(cmdcfg)
    code.append('  for node in css(doc):')

@register(selectors)
def xpath(env, code, app, cmdcfg, cfg):
    env['xpath'] = cmdcfg
    code.append('  for node in doc.xpath(xpath):')

@register(to_strings)
def attr(env, code, app, cmdcfg, cfg):
    env['attr'] = cmdcfg
    code.append('    s = node.get(attr)')

@register(to_strings)
def text(env, code, app, cmdcfg, cfg):
    code.append('    s = unicode(node.text_content())')

@register(to_strings, 'html')
def fhtml(env, code, app, cmdcfg, cfg):
    env['html'] = html
    code.append('    html.tostring(node)')

# TODO: use python not exe
@register(to_strings)
def html2text(env, code, app, cmdcfg, cfg):
    env['os'] = os
    env['html'] = html
    code.append("    fi, fo = os.popen2('html2text -utf8')")
    code.append("    fi.write(html.tostring(node).decode('gbk'))")
    code.append("    fi.close()")
    code.append("    s = fo.read()")

########NEW FILE########
__FILENAME__ = httputils
#!/usr/bin/python
# -*- coding: utf-8 -*-
'''
@date: 2013-06-07
@author: shell.xu
'''
import json, time, logging
from urlparse import urlparse
from robotparser import RobotFileParser
import gevent, requests

logger = logging.getLogger('http')

class ReqInfo(object):

    def __init__(self, procname, url, params=None, headers=None, body=None, method='GET'):
        self.procname, self.url, self.params = procname, url, params
        self.headers, self.body, self.method = headers, body, method

    @classmethod
    def unpack(cls, s): return cls(**json.loads(s))
    def pack(self):
        return json.dumps({
                'procname': self.procname, 'url': self.url, 'params': self.params,
                'headers': self.headers, 'body': self.body, 'method': self.method})

class SpeedLimit(object):

    def __init__(self, interval):
        self.last, self.interval = None, interval

    def get(self, url):
        if self.last is None:
            self.last = time.time()
            return
        while (self.last + self.interval) > time.time():
            gevent.sleep(self.last + self.interval - time.time() + 0.1)
        self.last = time.time()

robots_cache = {}

def accessible(url):
    u = urlparse(url)
    if u.netloc not in robots_cache:
        resp = requests.get('http://%s/robots.txt' % u.netloc)
        rp = RobotFileParser()
        rp.parse(resp.content.splitlines())
        robots_cache[u.netloc] = rp
    return robots_cache[u.netloc].can_fetch('*', url)

class HttpHub(object):
    sessions = {}

    def __init__(self, cfg):
        self.cfg = cfg
        self.timeout = cfg.get('timeout')
        self.headers = cfg.get('headers')

    def do(self, req):
        u = urlparse(req.url)
        if u.netloc not in self.sessions:
            sess = requests.Session()
            sess.headers = self.headers
            self.sessions[u.netloc] = sess
        sess = self.sessions[u.netloc]
        return sess.request(
            req.method or 'GET', req.url, data=req.body,
            headers=req.headers, timeout=self.timeout)

########NEW FILE########
__FILENAME__ = internal
#!/usr/bin/python
# -*- coding: utf-8 -*-
'''
@date: 2013-06-11
@author: shell.xu
'''
import sys

def debug(app, cfg):
    if 'debugfile' in app.cfg:
        debugfile = open(app.cfg['debugfile'], 'w')
    else: debugfile = sys.stdout
    def inner(req):
        print >>debugfile, 'req:', req.url
        for k, v in req.result.iteritems():
            print >>debugfile, 'key:', k
            print >>debugfile, 'value:', v
            print >>debugfile
        print >>debugfile
    return inner

########NEW FILE########
__FILENAME__ = worker
#!/usr/bin/python
# -*- coding: utf-8 -*-
'''
@date: 2013-06-02
@author: shell.xu
'''
import time, logging
import gevent.queue, gevent.pool, beanstalkc
import httputils

logger = logging.getLogger('worker')

class GeventWorker(object):

    def __init__(self, app, size=1):
        self.pool = gevent.pool.Pool(size)
        self.queue = gevent.queue.JoinableQueue()
        self.done = set()
        self.app = app

    def start(self):
        self.pool.spawn(self.run)
        self.pool.join()

    def run(self):
        while not self.queue.empty():
            reqsrc = self.queue.get()
            if reqsrc is None: return
            if not self.queue.empty() and self.pool.free_count() > 0:
                self.pool.spawn(self.run)
            req = httputils.ReqInfo.unpack(reqsrc)
            # FIXME: doing
            if req.url in self.done: continue
            else: self.done.add(req.url)
            logger.info('get: ' + req.url)
            self.app(self, req)
            self.queue.task_done()

    def append(self, req):
        if req.url in self.done: return
        if not self.app.accessible(req.url):
            logger.info('%s not accessible for robots.txt.' % req.url)
            return
        if req.headers and 'headers' in self.app.cfg:
            h = self.app.cfg['headers'].copy()
            h.update(req.headers)
            req.headers = h
        self.queue.put(req.pack())
        logger.info('put: ' + str(req.url))

class BeanstalkWorker(object):

    # put done to redis
    def __init__(self, app, name, host, port, timeout=1):
        self.queue = beanstalkc.Connection(host=host, port=port)
        self.queue.watch(name)
        self.queue.use(name)
        self.name, self.app, self.timeout = name, app, timeout

    def run(self):
        while True:
            job = self.queue.reserve(timeout=self.timeout)
            if job is None: return
            req = ReqInfo.unpack(job.body)
            logger.info('get: ' + req)
            self.app(self, req)
            job.delete()

    def append(self, req):
        if not self.app.accessible(url):
            logger.info('%s not accessible for robots.txt.' % req.url)
        if req.headers and 'headers' in self.app.cfg:
            h = self.app.cfg['headers'].copy()
            h.update(req.headers)
            req.headers = h
        self.queue.put(req.pack())
        logger.info('put: ' + str(req.url))

########NEW FILE########
__FILENAME__ = __main__
#!/usr/bin/python
# -*- coding: utf-8 -*-
'''
@date: 2013-06-24
@author: shell.xu
'''
import sys, pprint, getopt, logging
import beanstalkc
import gevent, gevent.pool, gevent.monkey
import apps, httputils, worker

optlist, args = getopt.getopt(sys.argv[1:], 'f:hH:l:p:q:s:t:')
optdict = dict(optlist)

def queue_init(func):
    def inner(args):
        host = optdict.get('-H', 'localhost')
        port = optdict.get('-p', '11300')
        queue = beanstalkc.Connection(host=host, port=int(port))
    return lambda args: func(queue, args)

@queue_init
def list(queue, args):
    print queue.tubes()

@queue_init
def stats(queue, args):
    name = optdict.get('-q')
    if name is not None:
        pprint.pprint(queue.stats_tube(name))
    else: pprint.pprint(queue.stats())

@queue_init
def add(queue, args):
    name = optdict.get('-q')
    if name: queue.use(name)
    funcname = optdict.get('-f', 'main')
    for url in args:
        queue.put(httputils.ReqInfo(funcname, url).pack())
        print 'put:', url

@queue_init
def drop(args):
    def inner(name):
        queue.use(name)
        queue.watch(name)
        while True:
            job = queue.reserve(timeout=1)
            if job is None: break
            job.delete()
    if '-q' in optdict: inner(optdict['-q'])
    else:
        for name in args: inner(name)

def initlog(lv, logfile=None):
    rootlog = logging.getLogger()
    if logfile: handler = logging.FileHandler(logfile)
    else: handler = logging.StreamHandler()
    handler.setFormatter(
        logging.Formatter(
            '%(asctime)s,%(msecs)03d %(name)s[%(levelname)s]: %(message)s',
            '%H:%M:%S'))
    rootlog.addHandler(handler)
    rootlog.setLevel(getattr(logging, lv))

def run(args):
    gevent.monkey.patch_all()
    initlog(optdict.get('-l', 'INFO'))
    funcname = optdict.get('-f', 'main')
    size = int(optdict.get('-s', '1'))

    app = apps.Application(args[0])
    url = app.cfg['start'] if len(args) < 2 else args[1]
    w = worker.GeventWorker(app, size)
    w.append(httputils.ReqInfo(funcname, url))
    w.start()

def runworker(args):
    gevent.monkey.patch_all()
    initlog(optdict.get('-l', 'INFO'))

    app = apps.Application(args[0])
    size = int(optdict.get('-s', '100'))
    pool = gevent.pool.Pool(size)
    for n in xrange(size):
        pool.spawn(worker.BeanstalkWorker(
                app, optdict['-q'], optdict.get('-H', 'localhost'),
                optdict.get('-p', '11300'), int(optdict.get('-t', '10'))).run)
    pool.join()

cmds=['list', 'stats', 'add', 'drop', 'run', 'runworker']
def main():
    '''
    -f: function name
    -h: help
    -H: hostname
    -l: log level, DEBUG default
    -p: port
    -q: queue
    -s: worker number, 1 default
    -t: timeout
    cmds: '''
    if '-h' in optdict or not args or args[0] not in cmds:
        print main.__doc__ + ' '.join(cmds)
        return
    globals()[args[0]](args[1:])

if __name__ == '__main__': main()

########NEW FILE########
__FILENAME__ = novel
#!/usr/bin/python
# -*- coding: utf-8 -*-
'''
@date: 2013-06-05
@author: shell.xu
'''
import os, sys

def result(app, cfg):
    filename = cfg.get('output')
    if not filename: filename = app.cfg.get('output', 'output.txt')
    outfile = open(filename, 'w')
    def inner(req):
        outfile.write('\n%s\n\n' % req.result['title'][0].encode('utf-8'))
        outfile.write('\n%s\n\n' % str(req.result['content'][0]))
    return inner

########NEW FILE########
