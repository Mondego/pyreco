__FILENAME__ = dispatch
from twisted.internet import reactor
from twisted.web import client, error, http
from twisted.web.resource import Resource
from hookah import queue
import sys, os

import base64

from hookah import HookahRequest
from hookah import storage, queue

# TODO: Make these configurable
RETRIES = 3
DELAY_MULTIPLIER = 5

def dispatch_request(request):
    key = storage.instance.put(request)
    queue.instance.submit(key)

def post_and_retry(url, data, retry=0, content_type='application/x-www-form-urlencoded'):
    if type(data) is dict:
        print "Posting [%s] to %s with %s" % (retry, url, data)
        data = urllib.urlencode(data)
    else:
        print "Posting [%s] to %s with %s bytes of postdata" % (retry, url, len(data))
    headers = {
        'Content-Type': content_type,
        'Content-Length': str(len(data)),
    }    
    client.getPage(url, method='POST' if len(data) else 'GET', headers=headers, postdata=data if len(data) else None).addCallbacks( \
                    if_success, lambda reason: if_fail(reason, url, data, retry, content_type))

def if_success(page): pass
def if_fail(reason, url, data, retry, content_type):
    if reason.getErrorMessage()[0:3] in ['301', '302', '303']:
        return # Not really a fail
    print reason.getErrorMessage()
    if retry < RETRIES:
        retry += 1
        reactor.callLater(retry * DELAY_MULTIPLIER, post_and_retry, url, data, retry, content_type)

class DispatchResource(Resource):
    isLeaf = True

    def render(self, request):
        url = base64.b64decode(request.postpath[0])
        
        if url:
            headers = {}
            for header in ['content-type', 'content-length']:
                value = request.getHeader(header)
                if value:
                    headers[header] = value
            
            dispatch_request(HookahRequest(url, headers, request.content.read()))
            
            request.setResponseCode(http.ACCEPTED)
            return "202 Scheduled"
        else:
            request.setResponseCode(http.BAD_REQUEST)
            return "400 No destination URL"

if __name__ == '__main__':
    from twisted.web.server import Request
    from cStringIO import StringIO
    class TestRequest(Request):
        postpath = ['aHR0cDovL3Byb2dyaXVtLmNvbT9ibGFo']
        content = StringIO("BLAH")
        
    output = DispatchResource().render(TestRequest({}, True))
    print output
    assert output == 'BLAH'
########NEW FILE########
__FILENAME__ = queue
from twisted.internet import defer, task

import storage

class Consumer(object):

    def __call__(self, key):
        request = storage.instance[key]
        # TODO:  Work
        return defer.succeed("yay")

class Queue(object):

    def submit(self, key):
        """Submit a job by work queue key."""
        raise NotImplementedError

    def finish(self, key):
        """Mark a job as completed."""
        raise NotImplementedError

    def retry(self, key):
        """Retry a job."""
        raise NotImplementedError

    def startConsumers(self, n=5):
        """Start consumers working on the queue."""
        raise NotImplementedError

    def shutDown(self):
        """Shut down the queue."""
        raise NotImplementedError

    @defer.inlineCallbacks
    def doTask(self, c):
        key = yield self.q.get()
        # XXX:  Indicate success/requeue/whatever
        try:
            worked = yield c(key)
            self.finish(key)
        except:
            self.retry(key)

class MemoryQueue(Queue):

    def __init__(self, consumer=Consumer):
        self.q = defer.DeferredQueue()
        self.keepGoing = True
        self.consumer = consumer
        self.cooperator = task.Cooperator()

    def submit(self, key):
        self.q.put(key)

    def finish(self, key):
        del storage.instance[key]

    retry = submit

    def shutDown(self):
        self.keepGoing = False

    def startConsumers(self, n=5):
        def f(c):
            while self.keepGoing:
                yield self.doTask(c)

        for i in range(n):
            self.cooperator.coiterate(f(self.consumer()))

instance = MemoryQueue()


########NEW FILE########
__FILENAME__ = storage
import base64
import cPickle
from collections import deque

class LocalStorage(object):

    MAX_ITEMS = 20

    def __init__(self):
        self._recent = deque()

    def recent(self, n=10):
        return list(self._recent)[0:n]

    def recordLocal(self, ob):
        if len(self._recent) >= self.MAX_ITEMS:
            self._recent.pop()
        self._recent.appendleft(ob)

class MemoryStorage(LocalStorage):

    def __init__(self):
        super(MemoryStorage, self).__init__()
        self._storage = {}
        self._sequence = 0

    def put(self, hookahRequest):
        self._sequence += 1
        self._storage[self._sequence] = hookahRequest
        self.recordLocal(hookahRequest)
        return self._sequence

    def __getitem__(self, key):
        return self._storage[key]

    def __delitem__(self, key):
        del self._storage[key]

class InlineStorage(LocalStorage):

    def __init__(self):
        super(InlineStorage, self).__init__()
        self._recent = deque()

    def put(self, hookaRequest):
        self.recordLocal(hookaRequest)
        return base64.encodestring(cPickle.dumps(hookaRequest))

    def __getitem__(self, key):
        return cPickle.loads(base64.decodestring(key))

    def __delitem__(self, key):
        pass

instance = MemoryStorage()


########NEW FILE########
__FILENAME__ = test_queue
from hookah import queue, storage
from time import sleep
from twisted.trial import unittest
from twisted.internet import defer

class MockConsumer(object):

    def __init__(self, i=1):
        self.d = defer.Deferred()
        self.i = i

    def __call__(self, key):
        self.i -= 1
        if self.i == 0:
            self.d.callback(key)
        return defer.succeed("yay")

class TestQueue(unittest.TestCase):

    def setUp(self):
        self.c = MockConsumer()
        self.q = queue.MemoryQueue(consumer=lambda: self.c)
        self.q.startConsumers(1)

    def testOneJob(self):
        k = storage.instance.put('Test Thing')
        self.q.submit(k)

        print "Checking..."
        self.c.d.addBoth(lambda x: self.q.shutDown())
        return self.c.d

    def verifyMissing(self, *keys):
        for k in keys:
            try:
                self.storage.instance[k]
                self.fail("Found unexpected key", k)
            except KeyError:
                pass

    def testTwoJobs(self):
        k1 = storage.instance.put('Test Thing 1')
        self.q.submit(k1)
        k2 = storage.instance.put('Test Thing 2')
        self.q.submit(k2)


        self.c.d.addCallback(lambda x: self.verifyMissing(k1, k2))
        self.c.d.addBoth(lambda x: self.q.shutDown())
        return self.c.d

########NEW FILE########
__FILENAME__ = test_storage
from twisted.trial import unittest

from hookah import storage

class BaseStorageTest(object):

    storageFactory = None
    deletionMeaningful = True

    def setUp(self):
        self.s = self.storageFactory()

        self.oneKey = self.s.put("one")
        self.twoKey = self.s.put("two")

    def testGet(self):
        self.assertEquals("one", self.s[self.oneKey])
        self.assertEquals("two", self.s[self.twoKey])

    def testDelete(self):
        self.assertEquals("one", self.s[self.oneKey])
        self.assertEquals("two", self.s[self.twoKey])

        del self.s[self.oneKey]
        self.assertEquals("two", self.s[self.twoKey])

        try:
            v = self.s[self.oneKey]
            if self.deletionMeaningful:
                self.fail("Expected failure, got " + v)
        except KeyError:
            pass

    def testRecent(self):
        self.assertEquals(['two', 'one'], self.s.recent())
        self.assertEquals(['two'], self.s.recent(1))

class MemoryStorageTest(BaseStorageTest, unittest.TestCase):

    storageFactory = storage.MemoryStorage

class InlineStorageTest(BaseStorageTest, unittest.TestCase):

    storageFactory = storage.InlineStorage
    deletionMeaningful = False

########NEW FILE########
__FILENAME__ = web
from twisted.python.util import sibpath
from twisted.web import client, error, http, static
from twisted.web.resource import Resource
from twisted.internet import task




class HookahResource(Resource):
    isLeaf = False
    
    def getChild(self, name, request):
        if name == '':
            return self
        return Resource.getChild(self, name, request)

    def render(self, request):
        path = '/'.join(request.prepath)
        
        if path in ['favicon.ico', 'robots.txt']:
            return

        return ''

    @classmethod
    def setup(cls):
        r = cls()
        from hookah import dispatch
        r.putChild('dispatch', dispatch.DispatchResource())
        return r

########NEW FILE########
__FILENAME__ = hookah_plugin
from zope.interface import implements

from twisted.python import usage
from twisted.plugin import IPlugin
from twisted.application.service import IServiceMaker
from twisted.application import internet
from twisted.web.server import Site

from hookah.web import HookahResource


class Options(usage.Options):
    optParameters = [["port", "p", 8080, "The port number to listen on."]]


class HookahMaker(object):
    implements(IServiceMaker, IPlugin)
    tapname = "hookah"
    description = "Yeah. Hookah."
    options = Options

    def makeService(self, options):
        """
        Construct a TCPServer from a factory defined in myproject.
        """
        return internet.TCPServer(int(options["port"]), Site(HookahResource.setup()))

serviceMaker = HookahMaker()

########NEW FILE########
