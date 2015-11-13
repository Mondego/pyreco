__FILENAME__ = slosh
#!/usr/bin/env python
"""

Copyright (c) 2008  Dustin Sallings <dustin@spy.net>
"""

import xml.sax
import xml.sax.saxutils
import cStringIO as StringIO

from twisted.web import server, resource
from twisted.internet import task

class Topic(resource.Resource):

    max_queue_size = 100
    max_id = 1000000000

    def __init__(self, filter=lambda a: a):
        self.last_id = 0
        self.filter = filter
        self.objects=[]
        self.requests=[]
        self.known_sessions={}
        self.formats={'xml': self.__transmit_xml, 'json': self.__transmit_json}
        self.methods = {'GET': self._do_GET, 'POST': self._do_POST}
        l = task.LoopingCall(self.__touch_active_sessions)
        l.start(5, now=False)

    def _do_GET(self, request):
        session = request.getSession()
        if session.uid not in self.known_sessions:
            print "New session: ", session.uid
            self.known_sessions[session.uid] = self.last_id
            session.notifyOnExpire(self.__mk_session_exp_cb(session.uid))
        if not self.__deliver(request):
            self.requests.append(request)
            request.notifyFinish().addBoth(self.__req_finished, request)
        return server.NOT_DONE_YET

    def _do_POST(self, request):
        # Store the object
        filtered = self.filter(request.args)
        if filtered:
            self.objects.append(filtered)
            if len(self.objects) > self.max_queue_size:
                del self.objects[0]
            self.last_id += 1
            if self.last_id > self.max_id:
                self.last_id = 1
            for r in self.requests:
                self.__deliver(r)
        return self.__mk_res(request, 'ok', 'text/plain')

    def render(self, request):
        return self.methods[request.method](request)

    def __since(self, n):
        # If a nonsense ID comes in, scoop them all up.
        if n > self.last_id:
            print "Overriding last ID from %d to %d" % (n, self.last_id - 1)
            n = self.last_id - 1
        f = max(0, self.last_id - n)
        rv = self.objects[0-f:] if self.last_id > n else []
        return rv, self.last_id - n

    def __req_finished(self, whatever, request):
        self.requests.remove(request)

    def __touch_active_sessions(self):
        for r in self.requests:
            r.getSession().touch()

    def __deliver(self, req):
        sid = req.getSession().uid
        since = req.args.get('n')
        if since:
            since=int(since[0])
        else:
            since = self.known_sessions[sid]
        data, oldsize = self.__since(since)
        if data:
            fmt = 'xml'
            if req.path.find(".") > 0:
                fmt=req.path.split(".")[-1]
            self.formats.get(fmt, self.__transmit_xml)(req, data, oldsize)
            req.finish()
        self.known_sessions[sid] = self.last_id
        return data

    def __transmit_xml(self, req, data, oldsize):
        class G(xml.sax.saxutils.XMLGenerator):
            def doElement(self, name, value, attrs={}):
                self.startElement(name, attrs)
                if value is not None:
                    self.characters(value)
                self.endElement(name)

        s=StringIO.StringIO()
        g=G(s, 'utf-8')

        g.startDocument()
        g.startElement("res",
            {'max': str(self.last_id), 'saw': str(oldsize),
                'delivering': str(len(data)) })

        for h in data:
            g.startElement("p", {})
            for k,v in h.iteritems():
                for subv in v:
                    g.doElement(k, subv)
            g.endElement("p")
        g.endElement("res")

        g.endDocument()

        s.seek(0, 0)
        req.write(self.__mk_res(req, s.read(), 'text/xml'))

    def __transmit_json(self, req, data, oldsize):
        import cjson
        jdata=[dict(s) for s in data]
        j=cjson.encode({'max': self.last_id, 'saw': oldsize,
            'delivering': len(data), 'res': jdata})
        req.write(self.__mk_res(req, j, 'text/plain'))

    def __mk_session_exp_cb(self, sid):
        def f():
            print "Expired session", sid
            del self.known_sessions[sid]
        return f

    def __mk_res(self, req, s, t):
        req.setHeader("content-type", t)
        req.setHeader("content-length", str(len(s)))
        return s

class Topics(resource.Resource):

    def getChild(self, path, request):
        t=path.split('/', 1)[0]
        if t.find(".") > 0:
            t=t.split(".", 1)[0]
            topic = self.getChildWithDefault(t, request)
        else:
            topic = Topic()
            self.putChild(t, topic)
            print "Registered new topic", t
        return topic


########NEW FILE########
__FILENAME__ = reflect
#!/usr/bin/env python
"""
Stream updates from one slosh instance to one or more others.

Copyright (c) 2008  Dustin Sallings <dustin@spy.net>
"""

import sys
import urllib

from twisted.internet import reactor, task, error
from twisted.web import client, sux

# The transformation function will receive a sequence of pairs and should
# return a new sequence of pairs.
def identityTransform(s):
    return s

class Post(object):

    def __init__(self, transformer):
        self.pairs = []
        self.transformer = transformer

    def add(self, key, data):
        self.pairs.append((key, data))

    # items is called by urllib.urlencode, the results of which will be posted
    def items(self):
        return self.transformer(self.pairs)

    def __repr__(self):
        return "<Post %s>" % (', '.join([k + "=" + v for (k,v) in self.pairs]))

class Emitter(sux.XMLParser):

    def __init__(self, urls, transformer):
        self.urls = urls
        self.transformer = transformer
        self.connectionMade()
        self.currentEntry=None
        self.data = []
        self.depth = 0

    def write(self, b):
        self.dataReceived(b)

    def close(self):
        self.connectionLost(error.ConnectionDone())

    def open(self):
        pass

    def read(self):
        return None

    def gotTagStart(self, name, attrs):
        self.depth += 1
        self.data = []
        if self.depth == 2:
            assert self.currentEntry is None
            self.currentEntry = Post(self.transformer)

    def gotTagEnd(self, name):
        self.depth -= 1
        if self.currentEntry:
            if self.depth == 1:
                self.emit()
                self.currentEntry = None
            else:
                self.currentEntry.add(name, ''.join(self.data).decode('utf8'))

    def gotText(self, data):
        self.data.append(data)

    def gotEntityReference(self, data):
        e = {'quot': '"', 'lt': '&lt;', 'gt': '&gt;', 'amp': '&amp;'}
        if e.has_key(data):
            self.data.append(e[data])
        else:
            print "Unhandled entity reference: ", data

    def emit(self):
        h = {'Content-Type': 'application/x-www-form-urlencoded'}
        params = urllib.urlencode(self.currentEntry)
        for url in self.urls:
            client.getPage(url, method='POST', postdata=params, headers=h)

class ReflectionClient(object):

    cookies = {}

    def __init__(self, urlin, urlsout, transformer=identityTransform):
        self.urlin = urlin
        self.urlsout = urlsout
        self.transformer = transformer

        self.scheme, self.host, self.port, self.path = client._parse(urlin)

    def cb(self, factory):
        def f(data):
            self.cookies = factory.cookies
        return f

    def logError(self, e):
        print e

    def __call__(self):
        # Stolen cookie code since the web API is inconsistent...
        headers={}
        l=[]
        for cookie, cookval in self.cookies.items():
            l.append('%s=%s' % (cookie, cookval))
        headers['Cookie'] = '; '.join(l)

        factory = client.HTTPDownloader(self.urlin,
            Emitter(self.urlsout, self.transformer), headers=headers)
        reactor.connectTCP(self.host, self.port, factory)
        factory.deferred.addCallback(self.cb(factory))
        factory.deferred.addErrback(self.logError)
        return factory.deferred

def startReflector(urlin, urlsout, transformer=identityTransform):
    lc = task.LoopingCall(ReflectionClient(urlin, urlsout, transformer))
    lc.start(0)

if __name__ == '__main__':
    startReflector(sys.argv[1], sys.argv[2:])
    reactor.run()

########NEW FILE########
__FILENAME__ = stream
#!/usr/bin/env python
"""
Log slosh output.

Copyright (c) 2008  Dustin Sallings <dustin@spy.net>
"""

import sys

from twisted.internet import reactor, task
from twisted.web import client

cookies = {}

def cb(factory):
    def f(data):
        global cookies
        cookies = factory.cookies
        print data
    return f

def getPage(url):
    factory = client.HTTPClientFactory(url, cookies=cookies)
    scheme, host, port, path = client._parse(url)
    reactor.connectTCP(host, port, factory)
    factory.deferred.addCallback(cb(factory))
    return factory.deferred

lc = task.LoopingCall(getPage, sys.argv[1])
lc.start(0)

reactor.run()

########NEW FILE########
