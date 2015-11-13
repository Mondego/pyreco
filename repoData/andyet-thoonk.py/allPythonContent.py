__FILENAME__ = createjobs
from thoonk import Pubsub
import cProfile
import time


def testspeed(total=1):
    p = Pubsub(listen=False)
    j = p.job("jobtest")
    start = time.time()
    for x in range(1,total+1):
        j.publish(x)
    tt = time.time() - start
    print tt, total / tt

testspeed(total=40000)

########NEW FILE########
__FILENAME__ = pullfromqueue
import thoonk
ps = thoonk.Pubsub()
q = ps.pyqueue('testpyqueue')
while True:
    value = q.get()
    print value
    print type(value), ":", value
ps.close()

########NEW FILE########
__FILENAME__ = pushtoqueue
import thoonk
ps = thoonk.Pubsub()
q = ps.pyqueue('testpyqueue')

q.put("this is a string")
q.put(set(("this", "is", "a", "set")))
q.put(3.14)
q.put(4)
q.put(u'unicode string')

ps.close()

########NEW FILE########
__FILENAME__ = runjobs
from thoonk import Pubsub
import cProfile
import time
import math
import sys

def runjobs(listen=False):
    p = Pubsub()
    job_channel = p.job("jobtest")
    x = 0
    starttime = time.time()
    while True:
        id, query = job_channel.get()
        #if x%2:
        job_channel.finish(id, query)
        x += 1
        if time.time() > starttime + 1.0:
            print "%d/sec" % x
            x = 0
            starttime = time.time()


runjobs()

########NEW FILE########
__FILENAME__ = test
from thoonk import Pubsub

p = Pubsub()
n = p.feed("test")
id = n.publish("hayyyyyy", id='crap')
print id, n.get_item(id)
q = p.queue("queue_test")
q.publish("whatever")
q.publish("shit ")
q.publish("whatever")
q.publish("whatever")
q.publish("whatever")
while True:
    try:
        print q.get(timeout=1)
    except q.Empty:
        break
print "done"


########NEW FILE########
__FILENAME__ = st
#!/usr/bin/python
from sleekpubsub.pubsub import Pubsub
from sleekpubsub.cli import CLInterface
import cProfile
import time


def testspeed(total=40000):
    p = Pubsub()
    n = p.leaf("speed")
    start = time.time()
    for x in range(1,total):
        n.publish(x, x)
    tt = time.time() - start
    print tt, total / tt

cProfile.run('testspeed()')
#testspeed()

########NEW FILE########
__FILENAME__ = testall
#!/usr/bin/env python
import unittest
import logging
import sys
import os

class testoverall(unittest.TestCase):

    def testModules(self):
        """Testing all modules by compiling them"""
        import compileall
        import re
        if sys.version_info < (3,0):
            self.failUnless(compileall.compile_dir('.' + os.sep + 'thoonk', rx=re.compile('/[.]svn'), quiet=True))
        else:
            self.failUnless(compileall.compile_dir('.' + os.sep + 'thoonk', rx=re.compile('/[.]svn|.*26.*'), quiet=True))

    def    testTabNanny(self):
        """Invoking the tabnanny"""
        import tabnanny
        self.failIf(tabnanny.check("." + os.sep + 'thoonk'))
        #raise "Help!"

    def disabled_testMethodLength(self):
        """Testing for excessive method lengths"""
        import re
        dirs = os.walk(sys.path[0] + os.sep + 'thoonk')
        offenders = []
        for d in dirs:
            if not '.svn' in d[0]:
                for filename in d[2]:
                    if filename.endswith('.py') and d[0].find("template%stemplates" % os.sep) == -1:
                        with open("%s%s%s" % (d[0],os.sep,filename), "r") as fp:
                            cur = None
                            methodline = lineno = methodlen = methodindent = 0
                            for line in fp:
                                indentlevel = re.compile("^[\t ]*").search(line).end()
                                line = line.expandtabs()
                                lineno += 1
                                if line.strip().startswith("def ") or line.strip().startswith("except") or (line.strip() and methodindent > indentlevel) or (line.strip() and methodindent == indentlevel): #new method found or old one ended
                                    if cur: #existing method needs final evaluation
                                        if methodlen > 50 and not cur.strip().startswith("def setupUi"):
                                            offenders.append("Method '%s' on line %s of %s/%s is longer than 50 lines (%s)" % (cur.strip(),methodline,d[0][len(rootp):],filename,methodlen))
                                        methodlen = 0
                                    cur = line
                                    methodindent = indentlevel
                                    methodline = lineno
                                if line and cur and not line.strip().startswith("#") and not (cur.strip().startswith("try:") and methodindent == 0): #if we weren't all whitespace and weren't a comment
                                    methodlen += 1
        self.failIf(offenders,"\n".join(offenders))


if __name__ == '__main__':
    logging.basicConfig(level=100)
    logging.disable(100)
    #this doesn't need to be very clean
    alltests = [unittest.TestLoader().loadTestsFromTestCase(testoverall)]
    rootp = sys.path[0] + os.sep + 'tests'
    dirs = os.walk(rootp)
    for d in dirs:
        if not '.svn' in d[0]:
            for filename in d[2]:
                if filename.startswith('test_') and filename.endswith('.py'):
                    modname = ('tests' + "." + filename)[:-3].replace(os.sep,'.')
                    __import__(modname)
                    #sys.modules[modname].config = moduleconfig
                    try:
                        alltests.append(sys.modules[modname].suite)
                    except:
                        pass
    alltests_suite = unittest.TestSuite(alltests)
    result = unittest.TextTestRunner(verbosity=2).run(alltests_suite)
    print("""<tests xmlns='http://andyet.net/protocol/tests' ran='%s' errors='%s' fails='%s' success='%s' />""" % (result.testsRun, len(result.errors), len(result.failures), result.wasSuccessful()))

########NEW FILE########
__FILENAME__ = test_feed
import thoonk
from thoonk.feeds import Feed
import unittest
from ConfigParser import ConfigParser
import threading

class TestLeaf(unittest.TestCase):

    def setUp(self, *args, **kwargs):
        conf = ConfigParser()
        conf.read('test.cfg')
        if conf.sections() == ['Test']:
            self.ps = thoonk.Thoonk(host=conf.get('Test', 'host'),
                                    port=conf.getint('Test', 'port'),
                                    db=conf.getint('Test', 'db'),
                                    listen=True)
            self.ps.redis.flushdb()
        else:
            print 'No test configuration found in test.cfg'
            exit()
    
    def tearDown(self):
        self.ps.close()
    
    def test_05_basic_retract(self):
        """Test adding and retracting an item."""
        l = self.ps.feed("testfeed")
        self.assertEqual(type(l), Feed)
        l.publish('foo', id='1')
        r = l.get_ids()
        v = l.get_all()
        self.assertEqual(r, ['1'], "Feed results did not match publish: %s." % r)
        self.assertEqual(v, {'1': 'foo'}, "Feed contents did not match publish: %s." % r)
        l.retract('1')
        r = l.get_ids()
        v = l.get_all()
        self.assertEqual(r, [], "Feed results did not match: %s." % r)
        self.assertEqual(v, {}, "Feed contents did not match: %s." % r)

    def test_10_basic_feed(self):
        """Test basic LEAF publish and retrieve."""
        l = self.ps.feed("testfeed")
        l.publish("hi", id='1')
        l.publish("bye", id='2')
        l.publish("thanks", id='3')
        l.publish("you're welcome", id='4')
        r = l.get_ids()
        self.assertEqual(r, ['1', '2', '3', '4'], "Queue results did not match publish: %s." % r)

    def test_20_basic_feed_items(self):
        """Test items match completely."""
        l = self.ps.feed("testfeed")
        l.publish("hi", id='1')
        l.publish("bye", id='2')
        l.publish("thanks", id='3')
        l.publish("you're welcome", id='4')
        r = l.get_ids()
        self.assertEqual(r, ['1', '2', '3', '4'], "Queue results did not match publish: %s" % r)
        c = {}
        for id in r:
            c[id] = l.get_item(id)
        self.assertEqual(c, {'1': 'hi', '3': 'thanks', '2': 'bye', '4': "you're welcome"}, "Queue items did not match publish: %s" % c)

    def test_30_basic_feed_retract(self):
        """Testing item retract items match."""
        l = self.ps.feed("testfeed")
        l.publish("hi", id='1')
        l.publish("bye", id='2')
        l.publish("thanks", id='3')
        l.publish("you're welcome", id='4')
        l.retract('3')
        r = l.get_ids()
        self.assertEqual(r, ['1', '2','4'], "Queue results did not match publish: %s" % r)
        c = {}
        for id in r:
            c[id] = l.get_item(id)
        self.assertEqual(c, {'1': 'hi', '2': 'bye', '4': "you're welcome"}, "Queue items did not match publish: %s" % c)

    def test_40_create_delete(self):
        """Testing feed delete"""
        l = self.ps.feed("test2")
        l.delete_feed()
        

    def test_50_max_length(self):
        """Test feeds with a max length"""
        feed = self.ps.feed('testfeed2', {'max_length': 5})
        feed.publish('item-1', id='1')
        feed.publish('item-2', id='2')
        feed.publish('item-3', id='3')
        feed.publish('item-4', id='4')
        feed.publish('item-5', id='5')
        items = feed.get_all()
        expected = {
            '1': 'item-1',
            '2': 'item-2',
            '3': 'item-3',
            '4': 'item-4',
            '5': 'item-5'
        }
        self.assertEqual(expected, items,
                "Items don't match: %s" % items)

        feed2 = self.ps.feed('testfeed2')
        feed2.publish('item-6', id='6')
        items = feed2.get_all()
        del expected['1']
        expected['6'] = 'item-6'
        self.assertEqual(expected, items,
                "Maxed items don't match: %s" % items)


suite = unittest.TestLoader().loadTestsFromTestCase(TestLeaf)

########NEW FILE########
__FILENAME__ = test_job
import thoonk
import unittest
from ConfigParser import ConfigParser
import threading


class TestJob(unittest.TestCase):

    def setUp(self, *args, **kwargs):
        conf = ConfigParser()
        conf.read('test.cfg')
        if conf.sections() == ['Test']:
            self.ps = thoonk.Thoonk(host=conf.get('Test', 'host'),
                                    port=conf.getint('Test', 'port'),
                                    db=conf.getint('Test', 'db'))
            self.ps.redis.flushdb()
        else:
            print 'No test configuration found in test.cfg'
            exit()

    def tearDown(self):
        self.ps.close()

    def test_10_basic_job(self):
        """Test job publish, retrieve, finish flow"""
        #publisher
        testjob = self.ps.job("testjob")
        self.assertEqual(testjob.get_ids(), [])
        
        id = testjob.put('9.0')
        
        #worker
        id_worker, job_content, cancelled = testjob.get(timeout=3)
        self.assertEqual(job_content, '9.0')
        self.assertEqual(cancelled, 0)
        self.assertEqual(id_worker, id)
        testjob.finish(id_worker)
        
        self.assertEqual(testjob.get_ids(), [])
    
    def test_20_cancel_job(self):
        """Test cancelling a job"""
        j = self.ps.job("testjob")
        #publisher
        id = j.put('9.0')
        #worker claims
        id, job_content, cancelled = j.get()
        self.assertEqual(job_content, '9.0')
        self.assertEqual(cancelled, 0)
        #publisher or worker cancels
        j.cancel(id)
        id2, job_content2, cancelled2 = j.get()
        self.assertEqual(cancelled2, 1)
        self.assertEqual(job_content2, '9.0')
        self.assertEqual(id, id2)
        #cancel the work again
        j.cancel(id)
        # check the cancelled increment again
        id3, job_content3, cancelled3 = j.get()
        self.assertEqual(cancelled3, 2)
        self.assertEqual(job_content3, '9.0')
        self.assertEqual(id, id3)
        #cleanup -- remove the job from the queue
        j.retract(id)
        self.assertEqual(j.get_ids(), [])

    def test_30_no_job(self):
        """Test exception raise when job.get times out"""
        j = self.ps.job("testjob")
        self.assertEqual(j.get_ids(), [])
        self.assertRaises(thoonk.exceptions.Empty, j.get, timeout=1)

class TestJobResult(unittest.TestCase):

    def setUp(self, *args, **kwargs):
        conf = ConfigParser()
        conf.read('test.cfg')
        if conf.sections() == ['Test']:
            self.ps = thoonk.Thoonk(host=conf.get('Test', 'host'),
                                    port=conf.getint('Test', 'port'),
                                    db=conf.getint('Test', 'db'),
                                    listen=True)
            self.ps.redis.flushdb()
        else:
            print 'No test configuration found in test.cfg'
            exit()

    def tearDown(self):
        self.ps.close()
    
    def test_10_job_result(self):
        """Test job result published"""

        create_event = threading.Event()
        def create_handler(name):
            self.assertEqual(name, "testjobresult")
            create_event.set()
        self.ps.register_handler("create", create_handler)

        #publisher
        testjob = self.ps.job("testjobresult")
        self.assertEqual(testjob.get_ids(), [])
        
        # Wait until the create event has been received by the ThoonkListener
        create_event.wait()
        
        id = testjob.put('9.0')
        
        #worker
        id_worker, job_content, cancelled = testjob.get(timeout=3)
        self.assertEqual(job_content, '9.0')
        self.assertEqual(cancelled, 0)
        self.assertEqual(id_worker, id)
        
        result_event = threading.Event()
        def result_handler(name, id, result):
            self.assertEqual(name, "testjobresult")
            self.assertEqual(id, id_worker)
            self.assertEqual(result, "myresult")
            result_event.set()
        
        self.ps.register_handler("finish", result_handler)
        testjob.finish(id_worker, "myresult")
        result_event.wait(1)
        self.assertTrue(result_event.isSet(), "No result received!")
        self.assertEqual(testjob.get_ids(), [])
        self.ps.remove_handler("result", result_handler)
        
#suite = unittest.TestLoader().loadTestsFromTestCase(TestJob)


########NEW FILE########
__FILENAME__ = test_notice
import thoonk
from thoonk.feeds import Feed, Job
import unittest
import time
import redis
from ConfigParser import ConfigParser
import threading

class TestNotice(unittest.TestCase):

    def setUp(self):
        conf = ConfigParser()
        conf.read('test.cfg')
        if conf.sections() == ['Test']:
            redis.Redis(host=conf.get('Test', 'host'),
                        port=conf.getint('Test', 'port'),
                        db=conf.getint('Test', 'db')).flushdb()
            self.ps = thoonk.Thoonk(host=conf.get('Test', 'host'),
                                    port=conf.getint('Test', 'port'),
                                    db=conf.getint('Test', 'db'),
                                    listen=True)
        else:
            print 'No test configuration found in test.cfg'
            exit()

    def tearDown(self):
        self.ps.close()

    "claimed, cancelled, stalled, finished"
    def test_01_feed_notices(self):
        """Test for create, publish, edit, retract and delete notices from feeds"""
        
        """Feed Create Event"""
        create_event = threading.Event()
        def create_handler(feed):
            self.assertEqual(feed, "test_notices")
            create_event.set()
        
        self.ps.register_handler("create", create_handler)
        l = self.ps.feed("test_notices")
        create_event.wait(1)
        self.assertTrue(create_event.isSet(), "Create notice not received")
        self.ps.remove_handler("create", create_handler)
        
        """Feed Publish Event"""
        publish_event = threading.Event()
        ids = [None, None]
        
        def received_handler(feed, item, id):
            self.assertEqual(feed, "test_notices")
            ids[1] = id
            publish_event.set()
        
        self.ps.register_handler('publish', received_handler)
        ids[0] = l.publish('a')
        publish_event.wait(1)

        self.assertTrue(publish_event.isSet(), "Publish notice not received")
        self.assertEqual(ids[1], ids[0])
        self.ps.remove_handler('publish', received_handler)
        
        """Feed Edit Event """
        edit_event = threading.Event()
        def edit_handler(feed, item, id):
            self.assertEqual(feed, "test_notices")
            ids[1] = id
            edit_event.set()

        self.ps.register_handler('edit', edit_handler)
        l.publish('b', id=ids[0])
        edit_event.wait(1)

        self.assertTrue(edit_event.isSet(), "Edit notice not received")
        self.assertEqual(ids[1], ids[0])
        self.ps.remove_handler('edit', edit_handler)
        
        """Feed Retract Event"""
        retract_event = threading.Event()
        def retract_handler(feed, id):
            self.assertEqual(feed, "test_notices")
            ids[1] = id
            retract_event.set()

        self.ps.register_handler('retract', retract_handler)
        l.retract(ids[0])
        retract_event.wait(1)

        self.assertTrue(retract_event.isSet(), "Retract notice not received")
        self.assertEqual(ids[1], ids[0])
        self.ps.remove_handler('retract', retract_handler)
        
        """Feed Delete Event"""
        delete_event = threading.Event()
        def delete_handler(feed):
            self.assertEqual(feed, "test_notices")
            delete_event.set()
        
        self.ps.register_handler("delete", delete_handler)
        l.delete_feed()
        delete_event.wait(1)
        self.assertTrue(delete_event.isSet(), "Delete notice not received")
        self.ps.remove_handler("delete", delete_handler)
    
    
    def skiptest_10_job_notices(self):
        notices_received = [False]
        ids = [None, None]
        
        def publish_handler(feed, item, id):
            self.assertEqual(feed, "testjob")
            ids[-1] = id
            notices_received[-1] = "publish"

        def claimed_handler(feed, id):
            self.assertEqual(feed, "testjob")
            ids[-1] = id
            notices_received[-1] = "claimed"
        
        def cancelled_handler(feed, id):
            self.assertEqual(feed, "testjob")
            ids[-1] = id
            notices_received[-1] = "cancelled"

        def stalled_handler(feed, id):
            self.assertEqual(feed, "testjob")
            ids[-1] = id
            notices_received[-1] = "stalled"
        
        def retried_handler(feed, id):
            self.assertEqual(feed, "testjob")
            ids[-1] = id
            notices_received[-1] = "retried"
        
        def finished_handler(feed, id, result):
            self.assertEqual(feed, "testjob")
            ids[-1] = id
            notices_received[-1] = "finished"
        
        def do_wait():
            i = 0
            while not notices_received[-1] and i < 2:
                i += 1
                time.sleep(0.2)
        
        self.ps.register_handler('publish_notice', publish_handler)
        self.ps.register_handler('claimed_notice', claimed_handler)
        self.ps.register_handler('cancelled_notice', cancelled_handler)
        self.ps.register_handler('stalled_notice', stalled_handler)
        self.ps.register_handler('retried_notice', retried_handler)
        self.ps.register_handler('finished_notice', finished_handler)
        
        j = self.ps.job("testjob")
        self.assertEqual(j.__class__, Job)
        self.assertFalse(notices_received[0])
        
        # create the job
        ids[0] = j.put('b')
        do_wait()
        self.assertEqual(notices_received[0], "publish", "Notice not received")
        self.assertEqual(ids[0], ids[-1])
        
        notices_received.append(False); ids.append(None);
        # claim the job
        id, job, cancelled = j.get()
        self.assertEqual(job, 'b')
        self.assertEqual(cancelled, 0)
        self.assertEqual(ids[0], id)
        do_wait()
        self.assertEqual(notices_received[-1], "claimed", "Claimed notice not received")
        self.assertEqual(ids[0], ids[-1])
        
        notices_received.append(False); ids.append(None);
        # cancel the job
        j.cancel(id)
        do_wait()
        self.assertEqual(notices_received[-1], "cancelled", "Cancelled notice not received")
        self.assertEqual(ids[0], ids[-1])
        
        notices_received.append(False); ids.append(None);
        # get the job again
        id, job, cancelled = j.get()
        self.assertEqual(job, 'b')
        self.assertEqual(cancelled, 1)
        self.assertEqual(ids[0], id)
        do_wait()
        self.assertEqual(notices_received[-1], "claimed", "Claimed notice not received")
        self.assertEqual(ids[0], ids[-1])
        
        notices_received.append(False); ids.append(None);
        # stall the job
        j.stall(id)
        do_wait()
        self.assertEqual(notices_received[-1], "stalled", "Stalled notice not received")
        self.assertEqual(ids[0], ids[-1])
        
        notices_received.append(False); ids.append(None);
        # retry the job
        j.retry(id)
        do_wait()
        self.assertEqual(notices_received[-1], "retried", "Retried notice not received")
        self.assertEqual(ids[0], ids[-1])
        
        notices_received.append(False); ids.append(None);
        # get the job again
        id, job, cancelled = j.get()
        self.assertEqual(job, 'b')
        self.assertEqual(cancelled, 0)
        self.assertEqual(ids[0], id)
        do_wait()
        self.assertEqual(notices_received[-1], "claimed", "Claimed notice not received")
        self.assertEqual(ids[0], ids[-1])
        
        notices_received.append(False); ids.append(None);
        # finish the job
        j.finish(id)
        do_wait()
        self.assertEqual(notices_received[-1], "finished", "Finished notice not received")
        self.assertEqual(ids[0], ids[-1])

        self.ps.remove_handler('publish_notice', publish_handler)
        self.ps.remove_handler('claimed_notice', claimed_handler)
        self.ps.remove_handler('cancelled_notice', cancelled_handler)
        self.ps.remove_handler('stalled_notice', stalled_handler)
        self.ps.remove_handler('retried_notice', retried_handler)
        self.ps.remove_handler('finished_notice', finished_handler)
        
suite = unittest.TestLoader().loadTestsFromTestCase(TestNotice)

########NEW FILE########
__FILENAME__ = test_queue
import thoonk
from thoonk.feeds import Queue
import unittest
from ConfigParser import ConfigParser


class TestQueue(unittest.TestCase):

    def setUp(self):
        conf = ConfigParser()
        conf.read('test.cfg')
        if conf.sections() == ['Test']:
            self.ps = thoonk.Thoonk(host=conf.get('Test', 'host'),
                                    port=conf.getint('Test', 'port'),
                                    db=conf.getint('Test', 'db'))
            self.ps.redis.flushdb()
        else:
            print 'No test configuration found in test.cfg'
            exit()

    def test_basic_queue(self):
        """Test basic QUEUE publish and retrieve."""
        q = self.ps.queue("testqueue")
        self.assertEqual(q.__class__, Queue)
        q.put("10")
        q.put("20")
        q.put("30")
        q.put("40")
        r = []
        for x in range(0,4):
            r.append(q.get(timeout=2))
        self.assertEqual(r, ["10", "20", "30", "40"], "Queue results did not match publish.")

suite = unittest.TestLoader().loadTestsFromTestCase(TestQueue)


########NEW FILE########
__FILENAME__ = test_sorted_feed
import thoonk
from thoonk.feeds import SortedFeed
import unittest
from ConfigParser import ConfigParser


class TestLeaf(unittest.TestCase):
    
    def setUp(self):
        conf = ConfigParser()
        conf.read('test.cfg')
        if conf.sections() == ['Test']:
            self.ps = thoonk.Thoonk(host=conf.get('Test', 'host'),
                                    port=conf.getint('Test', 'port'),
                                    db=conf.getint('Test', 'db'))
            self.ps.redis.flushdb()
        else:
            print 'No test configuration found in test.cfg'
            exit()
    
    def test_10_basic_sorted_feed(self):
        """Test basic sorted feed publish and retrieve."""
        l = self.ps.sorted_feed("sortedfeed")
        self.assertEqual(l.__class__, SortedFeed)
        l.publish("hi")
        l.publish("bye")
        l.publish("thanks")
        l.publish("you're welcome")
        r = l.get_ids()
        v = l.get_items()
        items = {'1': 'hi',
                 '2': 'bye',
                 '3': 'thanks',
                 '4': "you're welcome"}
        self.assertEqual(r, ['1', '2', '3', '4'], "Sorted feed results did not match publish: %s." % r)
        self.assertEqual(v, items, "Sorted feed items don't match: %s" % v)

    def test_20_sorted_feed_before(self):
        """Test addding an item before another item"""
        l = self.ps.sorted_feed("sortedfeed")
        l.publish("hi")
        l.publish("bye")
        l.publish_before('2', 'foo')
        r = l.get_ids()
        self.assertEqual(r, ['1', '3', '2'], "Sorted feed results did not match: %s." % r)

    def test_30_sorted_feed_after(self):
        """Test adding an item after another item"""
        l = self.ps.sorted_feed("sortedfeed")
        l.publish("hi")
        l.publish("bye")
        l.publish_after('1', 'foo')
        r = l.get_ids()
        self.assertEqual(r, ['1', '3', '2'], "Sorted feed results did not match: %s." % r)

    def test_40_sorted_feed_prepend(self):
        """Test addding an item to the front of the sorted feed"""
        l = self.ps.sorted_feed("sortedfeed")
        l.publish("hi")
        l.publish("bye")
        l.prepend('bar')
        r = l.get_ids()
        self.assertEqual(r, ['3', '1', '2'],
                "Sorted feed results don't match: %s" % r)

    def test_50_sorted_feed_edit(self):
        """Test editing an item in a sorted feed"""
        l = self.ps.sorted_feed("sortedfeed")
        l.publish("hi")
        l.publish("bye")
        l.edit('1', 'bar')
        r = l.get_ids()
        v = l.get_item('1')
        vs = l.get_items()
        items = {'1': 'bar',
                 '2': 'bye'}
        self.assertEqual(r, ['1', '2'],
                "Sorted feed results don't match: %s" % r)
        self.assertEqual(v, 'bar', "Items don't match: %s" % v)
        self.assertEqual(vs, items, "Sorted feed items don't match: %s" % vs)

    def test_60_sorted_feed_retract(self):
        """Test retracting an item from a sorted feed"""
        l = self.ps.sorted_feed("sortedfeed")
        l.publish("hi")
        l.publish("bye")
        l.publish("thanks")
        l.publish("you're welcome")
        l.retract('3')
        r = l.get_ids()
        self.assertEqual(r, ['1', '2', '4'],
                "Sorted feed results don't match: %s" % r)

    def test_70_sorted_feed_move_first(self):
        """Test moving items around in the feed."""
        l = self.ps.sorted_feed('sortedfeed')
        l.publish("hi")
        l.publish("bye")
        l.publish("thanks")
        l.publish("you're welcome")
        l.move_first('4')
        r = l.get_ids()
        self.assertEqual(r, ['4', '1', '2', '3'],
                "Sorted feed results don't match: %s" % r)

    def test_71_sorted_feed_move_last(self):
        """Test moving items around in the feed."""
        l = self.ps.sorted_feed('sortedfeed')
        l.publish("hi")
        l.publish("bye")
        l.publish("thanks")
        l.publish("you're welcome")
        l.move_last('2')
        r = l.get_ids()
        self.assertEqual(r, ['1', '3', '4', '2'],
                "Sorted feed results don't match: %s" % r)


    def test_72_sorted_feed_move_before(self):
        """Test moving items around in the feed."""
        l = self.ps.sorted_feed('sortedfeed')
        l.publish("hi")
        l.publish("bye")
        l.publish("thanks")
        l.publish("you're welcome")
        l.move_before('1', '2')
        r = l.get_ids()
        self.assertEqual(r, ['2', '1', '3', '4'],
                "Sorted feed results don't match: %s" % r)

    def test_73_sorted_feed_move_after(self):
        """Test moving items around in the feed."""
        l = self.ps.sorted_feed('sortedfeed')
        l.publish("hi")
        l.publish("bye")
        l.publish("thanks")
        l.publish("you're welcome")
        l.move_after('1', '4')
        r = l.get_ids()
        self.assertEqual(r, ['1', '4', '2', '3'],
                "Sorted feed results don't match: %s" % r)


suite = unittest.TestLoader().loadTestsFromTestCase(TestLeaf)

########NEW FILE########
__FILENAME__ = test_interop
import sys
import thoonk
import time
import unittest
from optparse import OptionParser


CONFIG = {}


class TestInteropDriver(unittest.TestCase):

    """
    """

    def setUp(self):
        self.thoonk = thoonk.Thoonk(CONFIG['host'], CONFIG['port'], CONFIG['db'])
        self.driver_queue= self.thoonk.queue('interop-testing-driver')
        self.follower_queue = self.thoonk.queue('interop-testing-follower')

    def wait(self):
        self.driver_queue.get()

    def proceed(self):
        self.follower_queue.put('token')

    def test_10_feeds(self):
        """Test interop for Feeds -- 1"""
        feed = self.thoonk.feed('interop-test-feed')
        feed.publish('test item', id='1')
        self.proceed()

    def test_11_feeds(self):
        """Test interop for Feeds -- 2"""
        feed = self.thoonk.feed('interop-test-feed')
        self.wait()
        feed.publish('edited item', id='1')
        self.proceed()

    def test_12_feeds(self):
        """Test interop for Feeds -- 3"""
        feed = self.thoonk.feed('interop-test-feed')
        self.wait()
        feed.retract('1')
        self.proceed()

    def test_13_feeds(self):
        """Test interop for Feeds -- 4"""
        feed = self.thoonk.feed('interop-test-feed')
        feed.config = {'max_length': 5}
        self.wait()
        feed.publish('item-1', id='1')
        time.sleep(0.1)
        feed.publish('item-2', id='2')
        time.sleep(0.1)
        feed.publish('item-3', id='3')
        time.sleep(0.1)
        feed.publish('item-4', id='4')
        time.sleep(0.1)
        feed.publish('item-5', id='5')
        time.sleep(0.1)
        self.proceed()

    def test_14_feeds(self):
        """Test interop for Feeds -- 5"""
        feed = self.thoonk.feed('interop-test-feed')
        self.wait()
        feed.publish('item-6', id='6')
        time.sleep(.1)
        self.proceed()

    def test_15_feeds(self):
        """Test interop for Feeds -- 6"""
        feed = self.thoonk.feed('interop-test-feed')
        self.wait()
        feed.publish('edited item-4', id='4')
        self.proceed()

    def test_20_lists(self):
        """Test interop for Lists"""
        pass

    def test_30_queues(self):
        """Test interop for Queues"""
        pass

    def test_40_jobs(self):
        """Test interop for Jobs"""
        pass


class TestInteropFollower(unittest.TestCase):

    """
    """

    def setUp(self):
        self.thoonk = thoonk.Thoonk(CONFIG['host'], CONFIG['port'], CONFIG['db'])
        self.driver_queue = self.thoonk.queue('interop-testing-driver')
        self.follower_queue = self.thoonk.queue('interop-testing-follower')

    def tearDown(self):
        self.proceed()

    def proceed(self):
        self.driver_queue.put('token')

    def wait(self):
        self.follower_queue.get()

    def test_10_feeds(self):
        """Test interop for Feeds -- 1"""
        feed = self.thoonk.feed('interop-test-feed')
        self.wait()
        items = feed.get_all()
        self.assertEqual({'1': 'test item'}, items,
                "Items don't match: %s" % items)

    def test_11_feeds(self):
        """Test interop for Feeds -- 2"""
        feed = self.thoonk.feed('interop-test-feed')
        self.wait()
        items = feed.get_all()
        self.assertEqual({'1': 'edited item'}, items,
                "Items don't match: %s" % items)

    def test_12_feeds(self):
        """Test interop for Feeds -- 3"""
        feed = self.thoonk.feed('interop-test-feed')
        self.wait()
        items = feed.get_all()
        self.assertEqual({}, items,
                "Items were not retracted: %s" % items)

    def test_13_feeds(self):
        """Test interop for Feeds -- 4"""
        feed = self.thoonk.feed('interop-test-feed', {'max_length':5})
        self.wait()
        items = feed.get_all()
        ids = feed.get_ids()
        expected = {
            '1': 'item-1',
            '2': 'item-2',
            '3': 'item-3',
            '4': 'item-4',
            '5': 'item-5'
        }
        self.assertEqual(expected, items,
                "Items don't match: %s" % items)
        self.assertEqual(['1','2','3','4','5'], ids,
                "Items not in order: %s" % ids)

    def test_14_feeds(self):
        """Test interop for Feeds -- 5"""
        feed = self.thoonk.feed('interop-test-feed', {'max_length':5})
        self.wait()
        items = feed.get_all()
        ids = feed.get_ids()
        expected = {
            '2': 'item-2',
            '3': 'item-3',
            '4': 'item-4',
            '5': 'item-5',
            '6': 'item-6'
        }
        self.assertEqual(expected, items,
                "Items don't match: %s" % items)
        self.assertEqual(['2','3','4','5','6'], ids,
                "Items not in order: %s" % ids)

    def test_15_feeds(self):
        """Test interop for Feeds -- 6"""
        feed = self.thoonk.feed('interop-test-feed')
        self.wait()
        items = feed.get_all()
        ids = feed.get_ids()
        expected = {
            '3': 'item-3',
            '4': 'edited item-4',
            '5': 'item-5',
            '6': 'item-6'
        }
        self.assertEqual(expected, items,
                "Items don't match: %s" % items)
        self.assertEqual(['3','5','6','4'], ids,
                "Items not in order: %s" % ids)

    def test_20_lists(self):
        """Test interop for Lists"""
        pass

    def test_30_queues(self):
        """Test interop for Queues"""
        pass

    def test_40_jobs(self):
        """Test interop for Jobs"""
        pass


if __name__ == '__main__':
    optp = OptionParser()
    optp.add_option('-s', '--server', help='set Redis host',
                    dest='server', default='localhost')
    optp.add_option('-p', '--port', help='set Redis host',
                    dest='port', default=6379)
    optp.add_option('-d', '--db', help='set Redis db',
                    dest='db', default=10)

    opts, args = optp.parse_args()

    CONFIG['host'] = opts.server
    CONFIG['port'] = opts.port
    CONFIG['db'] = opts.db

    if args[0] == 'driver':
        t = thoonk.Thoonk(opts.server, opts.port, opts.db)
        t.redis.flushdb()
        test_class = TestInteropDriver
    else:
        test_class = TestInteropFollower

    suite = unittest.TestLoader().loadTestsFromTestCase(test_class)
    unittest.TextTestRunner(verbosity=2).run(suite)

########NEW FILE########
__FILENAME__ = cache
"""
    Written by Nathan Fritz and Lance Stout. Copyright 2011 by &yet, LLC.
    Released under the terms of the MIT License
"""

import threading
import uuid
from thoonk.exceptions import FeedDoesNotExist

class FeedCache(object):

    """
    The FeedCache class stores an in-memory version of each
    feed. As there may be multiple systems using
    Thoonk with the same Redis server, and each with its own
    FeedCache instance, each FeedCache has a self.instance
    field to uniquely identify itself.

    Attributes:
        thoonk   -- The main Thoonk object.
        instance -- A hex string for uniquely identifying this
                    FeedCache instance.

    Methods:
        invalidate -- Force a feed's config to be retrieved from
                      Redis instead of in-memory.
    """

    def __init__(self, thoonk):
        """
        Create a new configuration cache.

        Arguments:
            thoonk -- The main Thoonk object.
        """
        self._feeds = {}
        self.thoonk = thoonk
        self.lock = threading.Lock()

    def __getitem__(self, feed):
        """
        Return a feed object for a given feed name.

        Arguments:
            feed -- The name of the requested feed.
        """
        with self.lock:
            if feed not in self._feeds:
                feed_type = self.thoonk.redis.hget('feed.config:%s' % feed, "type")
                if not feed_type:
                    raise FeedDoesNotExist
                self._feeds[feed] = self.thoonk.feedtypes[feed_type](self.thoonk, feed)
            return self._feeds[feed]
    
    def __delitem__(self, feed):
        with self.lock:
            if feed in self._feeds:
                self._feeds[feed].delete()
                del self._feeds[feed]

########NEW FILE########
__FILENAME__ = cli
"""
    Written by Nathan Fritz and Lance Stout. Copyright 2011 by &yet, LLC.
    Released under the terms of the MIT License
"""

import Queue
import cmd
import threading
import traceback
import sys

import thoonk
from thoonk import Thoonk
from thoonk.exceptions import FeedExists


class CLInterface(cmd.Cmd):

    def __init__(self, host='localhost', port=6379, db=0):
        cmd.Cmd.__init__(self)
        self.thoonk = Thoonk(host, port, db)
        self.lthoonk = Thoonk(host, port, db)
        self.intro = 'Thoonk.py v%s Client' % thoonk.__version__
        self.prompt = '>>> '
        self.lthoonk.register_handler('publish_notice', self.publish_notice)
        self.lthoonk.register_handler('retract_notice', self.retract_notice)
        self.lthoonk.register_handler('create_notice', self.create_notice)
        self.lthoonk.register_handler('delete_notice', self.delete_notice)

    def start(self):
        self.thread = threading.Thread(target=self.lthoonk.listen)
        self.thread.daemon = True
        self.thread.start()
        self.lthoonk.listen_ready.wait()
        self.cmdloop()

    def parseline(self, line):
        line = cmd.Cmd.parseline(self, line)
        if line[0] != 'help':
            return (line[0], line[1].split(' '), line[2])
        return line

    def do_EOF(self, line):
        return True

    def do_quit(self, line):
        return True

    def help_quit(self):
        print 'Quit'

    def do_create(self, args):
        try:
            self.thoonk.create_feed(args[0], {})
        except FeedExists:
            print "Feed already exists"

    def help_create(self):
        print 'create [feed name]'
        print 'Create a new feed with the given name'

    def do_publish(self, args):
        self.thoonk[args[0]].publish(" ".join(args[1:]))

    def help_publish(self):
        print 'publish [item contents]'
        print 'Publish a string to the feed (may include spaces)'

    def do_delete(self, args):
        self.thoonk[args[0]].delete_feed()

    def help_delete(self):
        print 'delete [feed name]'
        print 'Delete the given feed'

    def do_retract(self, args):
        self.thoonk[args[0]].retract(args[1])

    def help_retract(self):
        print 'retract [feed name] [item id]'
        print 'Remove an item from a feed.'

    def do_feeds(self, args):
        print self.thoonk.get_feeds()

    def help_feeds(self):
        print 'List existing feeds'

    def do_items(self, args):
        print self.thoonk[args[0]].get_all()

    def help_items(self):
        print 'items [feed name]'
        print 'List items in a given feed.'

    def do_item(self, args):
        if len(args) == 1:
            args.append(None)
        print self.thoonk[args[0]].get_item(args[1])

    def help_item(self):
        print 'item [feed name] [id]'
        print 'Print the contents of a feed item'

    def do_getconfig(self, args):
        print self.thoonk[args[0]].config

    def help_getconfig(self):
        print 'getconfig [feed name]'
        print 'Show the JSON configuration for a feed'

    def do_setconfig(self, args):
        feed = args[0]
        config = ' '.join(args[1:])
        self.thoonk[feed].config = config
        print "Ok."

    def help_setconfig(self):
        print 'setconfig [feed name] [config]'
        print 'Set the configuration for a feed'

    def publish_notice(self, feed, item, id):
        print "\npublish: %s[%s]: %s" % (feed, id, item)

    def retract_notice(self, feed, id):
        print "\nretract: %s[%s]" % (feed, id)

    def create_notice(self, feed):
        print "\ncreated: %s" % feed

    def delete_notice(self, feed):
        print "\ndeleted: %s" % feed

    def finish_notice(self, feed, id, item, result):
        print "\nfinished: %s[%s]: %s -> %s" % (feed, id, item, result)


if __name__ == '__main__':
    CLInterface().start()

########NEW FILE########
__FILENAME__ = exceptions
"""
    Written by Nathan Fritz and Lance Stout. Copyright 2011 by &yet, LLC.
    Released under the terms of the MIT License
"""


class FeedExists(Exception):
    pass

class FeedDoesNotExist(Exception):
    pass

class Empty(Exception):
    pass

class NotListening(Exception):
    pass
########NEW FILE########
__FILENAME__ = feed
"""
    Written by Nathan Fritz and Lance Stout. Copyright 2011 by &yet, LLC.
    Released under the terms of the MIT License
"""

import time
import uuid
try:
    import queue
except ImportError:
    import Queue as queue

from thoonk.exceptions import *
import redis.exceptions

class Feed(object):

    """
    A Thoonk feed is a collection of items ordered by publication date.

    The collection may either be bounded or unbounded in size. A bounded
    feed is created by adding the field 'max_length' to the configuration
    with a value greater than 0.

    Attributes:
        thoonk -- The main Thoonk object.
        redis  -- A Redis connection instance from the Thoonk object.
        feed   -- The name of the feed.

    Redis Keys Used:
        feed.ids:[feed]       -- A sorted set of item IDs.
        feed.items:[feed]     -- A hash table of items keyed by ID.
        feed.publish:[feed]   -- A pubsub channel for publication notices.
        feed.publishes:[feed] -- A counter for number of published items.
        feed.retract:[feed]   -- A pubsub channel for retraction notices.
        feed.config:[feed]    -- A JSON string of configuration data.
        feed.edit:[feed]      -- A pubsub channel for edit notices.

    Thoonk.py Implementation API:
        get_channels  -- Return the standard pubsub channels for this feed.
        event_publish -- Process publication events.
        event_retract -- Process item retraction events.
        delete_feed   -- Delete the feed and its contents.
        get_schemas   -- Return the set of Redis keys used by this feed.

    Thoonk Standard API:
        get_ids  -- Return the IDs of all items in the feed.
        get_item -- Return a single item from the feed given its ID.
        get_all  -- Return all items in the feed.
        publish  -- Publish a new item to the feed, or edit an existing item.
        retract  -- Remove an item from the feed.
    """

    def __init__(self, thoonk, feed):
        """
        Create a new Feed object for a given Thoonk feed.

        Note: More than one Feed objects may be create for the same
              Thoonk feed, and creating a Feed object does not
              automatically generate the Thoonk feed itself.

        Arguments:
            thoonk -- The main Thoonk object.
            feed   -- The name of the feed.
            config -- Optional dictionary of configuration values.
        """
        self.thoonk = thoonk
        self.redis = thoonk.redis
        self.feed = feed

        self.feed_ids = 'feed.ids:%s' % feed
        self.feed_items = 'feed.items:%s' % feed
        self.feed_publish = 'feed.publish:%s' % feed
        self.feed_publishes = 'feed.publishes:%s' % feed
        self.feed_retract = 'feed.retract:%s' % feed
        self.feed_config = 'feed.config:%s' % feed
        self.feed_edit = 'feed.edit:%s' % feed

    # Thoonk.py Implementation API
    # =================================================================

    def get_channels(self):
        """
        Return the Redis key channels for publishing and retracting items.
        """
        return (self.feed_publish, self.feed_retract, self.feed_edit)

    def event_publish(self, id, value):
        """
        Process an item published event.

        Meant to be overridden.

        Arguments:
            id    -- The ID of the published item.
            value -- The content of the published item.
        """
        pass

    def event_retract(self, id):
        """
        Process an item retracted event.

        Meant to be overridden.

        Arguments:
            id -- The ID of the retracted item.
        """
        pass

    def delete_feed(self):
        """Delete the feed and its contents."""
        self.thoonk.delete_feed(self.feed)

    def get_schemas(self):
        """Return the set of Redis keys used exclusively by this feed."""
        return set((self.feed_ids, self.feed_items, self.feed_publish,
                    self.feed_publishes, self.feed_retract, self.feed_config,
                    self.feed_edit))
    
    # Thoonk Standard API
    # =================================================================

    def get_ids(self):
        """Return the set of IDs used by items in the feed."""
        return self.redis.zrange(self.feed_ids, 0, -1)

    def get_item(self, id=None):
        """
        Retrieve a single item from the feed.

        Arguments:
            id -- The ID of the item to retrieve.
        """
        if id is None:
            self.redis.hget(self.feed_items,
                            self.redis.lindex(self.feed_ids, 0))
        else:
            return self.redis.hget(self.feed_items, id)

    def get_all(self):
        """Return all items from the feed."""
        return self.redis.hgetall(self.feed_items)

    def publish(self, item, id=None):
        """
        Publish an item to the feed, or replace an existing item.

        Newly published items will be at the top of the feed, while
        edited items will remain in their original order.

        If the feed has a max length, then the oldest entries will
        be removed to maintain the maximum length.

        Arguments:
            item -- The content of the item to add to the feed.
            id   -- Optional ID to use for the item, if the ID already
                    exists, the existing item will be replaced.
        """
        publish_id = id
        if publish_id is None:
            publish_id = uuid.uuid4().hex
        
        def _publish(pipe):
            max = int(pipe.hget(self.feed_config, "max_length") or 0)
            if max > 0:
                delete_ids = pipe.zrange(self.feed_ids, 0, -max)
                pipe.multi()
                for id in delete_ids:
                    if id != publish_id:
                        pipe.zrem(self.feed_ids, id)
                        pipe.hdel(self.feed_items, id)
                        self.thoonk._publish(self.feed_retract, (id,), pipe)
            else:
                pipe.multi()
            pipe.zadd(self.feed_ids, **{publish_id: time.time()})
            pipe.incr(self.feed_publishes)
            pipe.hset(self.feed_items, publish_id, item)
        
        results = self.redis.transaction(_publish, self.feed_ids)
        
        if results[-3]:
            # If zadd was successful
            self.thoonk._publish(self.feed_publish, (publish_id, item))
        else:
            self.thoonk._publish(self.feed_edit, (publish_id, item))

        return publish_id

    def retract(self, id):
        """
        Remove an item from the feed.

        Arguments:
            id -- The ID value of the item to remove.
        """
        def _retract(pipe):
            if pipe.zrank(self.feed_ids, id) is not None:
                pipe.multi()
                pipe.zrem(self.feed_ids, id)
                pipe.hdel(self.feed_items, id)
                self.thoonk._publish(self.feed_retract, (id,), pipe)
        
        self.redis.transaction(_retract, self.feed_ids)

########NEW FILE########
__FILENAME__ = job
"""
    Written by Nathan Fritz and Lance Stout. Copyright 2011 by &yet, LLC.
    Released under the terms of the MIT License
"""

import time
import uuid

from thoonk.feeds import Queue
from thoonk.feeds.queue import Empty

class Job(Queue):

    """
    A Thoonk Job is a queue which does not completely remove items
    from the queue until a task completion notice is received.

    Job Item Lifecycle:
        - A job is created using self.put() with the data for the job.
        - The job is moved to a claimed state when a worker retrieves
          the job data from the queue.
        - The worker performs any processing required, and calls
          self.finish() with the job's result data.
        - The job is marked as finished and removed from the queue.

    Alternative: Job Cancellation
        - After a worker has claimed a job, it calls self.cancel() with
          the job's ID, possibly because of an error or lack of required
          resources.
        - The job is moved from a claimed state back to the queue.

    Alternative: Job Stalling
        - A call to self.stall() with the job ID is made.
        - The job is moved out of the queue and into a stalled state. While
          stalled, the job will not be dispatched.
        - A call to self.retry() with the job ID is made.
        - The job is moved out of the stalled state and back into the queue.

    Alternative: Job Deletion
        - A call to self.retract() with the job ID is made.
        - The job item is completely removed from the queue and any
          other job states.

    Redis Keys Used:
        feed.published:[feed] -- A time sorted set of queued jobs.
        feed.cancelled:[feed] -- A hash table of cancelled jobs.
        feed.claimed:[feed]   -- A hash table of claimed jobs.
        feed.stalled:[feed]   -- A hash table of stalled jobs.
        feed.running:[feed]   -- A hash table of running jobs.
        feed.publishes:[feed] -- A count of the number of jobs published
        feed.finishes:[feed]  -- A count of the number of jobs finished
        job.finish:[feed]    -- A pubsub channel for job results

    Thoonk.py Implementation API:
        get_schemas   -- Return the set of Redis keys used by this feed.

    Thoonk Standard API:
        cancel      -- Move a job from a claimed state back into the queue.
        finish      -- Mark a job as completed and store the results.
        get         -- Retrieve the next job from the queue.
        get_ids     -- Return IDs of all jobs in the queue.
        get_result  -- Retrieve the result of a job.
        maintenance -- Perform periodic house cleaning.
        put         -- Add a new job to the queue.
        retract     -- Completely remove a job from use.
        retry       -- Resume execution of a stalled job.
        stall       -- Pause execution of a queued job.
    """

    def __init__(self, thoonk, feed):
        """
        Create a new Job queue object for a given Thoonk feed.

        Note: More than one Job queue objects may be create for
              the same Thoonk feed, and creating a Job queue object
              does not automatically generate the Thoonk feed itself.

        Arguments:
            thoonk -- The main Thoonk object.
            feed   -- The name of the feed.
            config -- Optional dictionary of configuration values.
        """
        Queue.__init__(self, thoonk, feed)

        self.feed_publishes = 'feed.publishes:%s' % feed
        self.feed_published = 'feed.published:%s' % feed
        self.feed_cancelled = 'feed.cancelled:%s' % feed
        self.feed_retried = 'feed.retried:%s' % feed
        self.feed_finishes = 'feed.finishes:%s' % feed
        self.feed_claimed = 'feed.claimed:%s' % feed
        self.feed_stalled = 'feed.stalled:%s' % feed
        self.feed_running = 'feed.running:%s' % feed
        
        self.job_finish = 'job.finish:%s' % feed        

    def get_channels(self):
        return (self.feed_publishes, self.feed_claimed, self.feed_stalled,
            self.feed_finishes, self.feed_cancelled, self.feed_retried,
            self.job_finish)

    def get_schemas(self):
        """Return the set of Redis keys used exclusively by this feed."""
        schema = set((self.feed_claimed,
                      self.feed_stalled,
                      self.feed_running,
                      self.feed_publishes,
                      self.feed_cancelled))
        return schema.union(Queue.get_schemas(self))

    def get_ids(self):
        """Return the set of IDs used by jobs in the queue."""
        return self.redis.hkeys(self.feed_items)

    def retract(self, id):
        """
        Completely remove a job from use.

        Arguments:
            id -- The ID of the job to remove.
        """
        def _retract(pipe):
            if pipe.hexists(self.feed_items, id):
                pipe.multi()
                pipe.hdel(self.feed_items, id)
                pipe.hdel(self.feed_cancelled, id)
                pipe.zrem(self.feed_published, id)
                pipe.srem(self.feed_stalled, id)
                pipe.zrem(self.feed_claimed, id)
                pipe.lrem(self.feed_ids, 1, id)
        
        self.redis.transaction(_retract, self.feed_items)

    def put(self, item, priority=False):
        """
        Add a new job to the queue.

        (Same as self.publish())

        Arguments:
            item     -- The content to add to the queue (string).
            priority -- Optional priority; if equal to True then
                        the item will be inserted at the head of the
                        queue instead of the end.
        """
        id = uuid.uuid4().hex
        pipe = self.redis.pipeline()

        if priority:
            pipe.rpush(self.feed_ids, id)
        else:
            pipe.lpush(self.feed_ids, id)
        pipe.incr(self.feed_publishes)
        pipe.hset(self.feed_items, id, item)
        pipe.zadd(self.feed_published, **{id: int(time.time()*1000)})

        results = pipe.execute()

        if results[-1]:
            # If zadd was successful
            self.thoonk._publish(self.feed_publishes, (id, item))
        else:
            self.thoonk._publish(self.feed_edit, (id, item))

        return id

    def get(self, timeout=0):
        """
        Retrieve the next job from the queue.

        Raises an Empty exception if the request times out.

        Arguments:
            timeout -- Optional time in seconds to wait before
                       raising an exception.
        
        Returns:
            id      -- The id of the job
            job     -- The job content
            cancelled -- The number of times the job has been cancelled
        """
        id = self.redis.brpop(self.feed_ids, timeout)
        if id is None:
            raise Empty
        id = id[1]

        pipe = self.redis.pipeline()
        pipe.zadd(self.feed_claimed, **{id: int(time.time()*1000)})
        pipe.hget(self.feed_items, id)
        pipe.hget(self.feed_cancelled, id)
        result = pipe.execute()
        
        self.thoonk._publish(self.feed_claimed, (id,))

        return id, result[1], 0 if result[2] is None else int(result[2])

    def get_failure_count(self, id):
        return int(self.redis.hget(self.feed_cancelled, id) or 0)
    
    NO_RESULT = []
    def finish(self, id, result=NO_RESULT):
        """
        Mark a job as completed, and store any results.

        Arguments:
            id      -- The ID of the completed job.
            result  -- The result data from the job. (should be a string!)
        """
        def _finish(pipe):
            if pipe.zrank(self.feed_claimed, id) is None:
                return # raise exception?
            pipe.multi()
            pipe.zrem(self.feed_claimed, id)
            pipe.hdel(self.feed_cancelled, id)
            pipe.zrem(self.feed_published, id)
            pipe.incr(self.feed_finishes)
            if result is not self.NO_RESULT:
                self.thoonk._publish(self.job_finish, (id, result), pipe)
            pipe.hdel(self.feed_items, id)
        
        self.redis.transaction(_finish, self.feed_claimed)

    def cancel(self, id):
        """
        Move a claimed job back to the queue.

        Arguments:
            id -- The ID of the job to cancel.
        """
        def _cancel(pipe):
            if self.redis.zrank(self.feed_claimed, id) is None:
                return # raise exception?
            pipe.multi()
            pipe.hincrby(self.feed_cancelled, id, 1)
            pipe.lpush(self.feed_ids, id)
            pipe.zrem(self.feed_claimed, id)
        
        self.redis.transaction(_cancel, self.feed_claimed)

    def stall(self, id):
        """
        Move a job out of the queue in order to pause processing.

        While stalled, a job will not be dispatched to requesting workers.

        Arguments:
            id -- The ID of the job to pause.
        """
        def _stall(pipe):
            if pipe.zrank(self.feed_claimed, id) is None:
                return # raise exception?
            pipe.multi()
            pipe.zrem(self.feed_claimed, id)
            pipe.hdel(self.feed_cancelled, id)
            pipe.sadd(self.feed_stalled, id)
            pipe.zrem(self.feed_published, id)
        
        self.redis.transaction(_stall, self.feed_claimed)

    def retry(self, id):
        """
        Move a job from a stalled state back into the job queue.

        Arguments:
            id -- The ID of the job to resume.
        """
        def _retry(pipe):
            if pipe.sismember(self.feed_stalled, id) is None:
                return # raise exception?
            pipe.multi()
            pipe.srem(self.feed_stalled, id)
            pipe.lpush(self.feed_ids, id)
            pipe.zadd(self.feed_published, **{id: time.time()})
        
        results = self.redis.transaction(_retry, self.feed_stalled)
        if not results[0]:
            return # raise exception?

    def maintenance(self):
        """
        Perform periodic house cleaning.

        Fix any inconsistencies such as jobs that are not in any state, etc,
        that can be caused by software crashes and other unexpected events.

        Expected use is to create a maintenance thread for periodically
        calling this method.
        """
        pipe = self.redis.pipeline()
        pipe.hkeys(self.feed_items)
        pipe.lrange(self.feed_ids, 0, -1)
        pipe.zrange(self.feed_claimed, 0, -1)
        pipe.stall = pipe.smembers(self.feed_stalled)

        keys, avail, claim, stall = pipe.execute()

        unaccounted = [key for key in keys if (key not in avail and \
                                               key not in claim and \
                                               key not in stall)]
        for key in unaccounted:
            self.redis.lpush(self.feed_ids, key)

########NEW FILE########
__FILENAME__ = pyqueue
import cPickle

from thoonk.exceptions import *
from thoonk.feeds import Queue


class PythonQueue(Queue):

    """
    A Thoonk.py addition, the PythonQueue class behaves the
    same as a normal Thoonk queue, except it pickles/unpickles
    items as needed.

    Thoonk.py Implementation API:
        put -- Add a Python object to the queue.
        get -- Retrieve a Python object from the queue.
    """

    def put(self, item, priority=None):
        """
        Add a new item to the queue.

        The item will be pickled before insertion into the queue.

        (Same as self.publish())

        Arguments:
            item     -- The content to add to the queue.
            priority -- Optional priority; if equal to self.HIGH then
                        the item will be inserted at the head of the
                        queue instead of the end.
        """
        item = cPickle.dumps(item)
        return Queue.put(self, item, priority)

    def get(self, timeout=0):
        """
        Retrieve the next item from the queue.

        Raises a self.Empty exception if the request times out.

        The item will be unpickled before returning.

        Arguments:
            timeout -- Optional time in seconds to wait before
                       raising an exception.
        """
        value = Queue.get(self, timeout)
        return cPickle.loads(value)

########NEW FILE########
__FILENAME__ = queue
"""
    Written by Nathan Fritz and Lance Stout. Copyright 2011 by &yet, LLC.
    Released under the terms of the MIT License
"""

import uuid

from thoonk.exceptions import Empty
from thoonk.feeds import Feed

class Queue(Feed):

    """
    A Thoonk queue is a typical FIFO structure, but with an
    optional priority override for inserting to the head
    of the queue.

    Thoonk Standard API:
        publish -- Alias for put()
        put     -- Add an item to the queue, with optional priority.
        get     -- Retrieve the next item from the queue.
    """

    def publish(self, item, priority=False):
        """
        Add a new item to the queue.

        (Same as self.put())

        Arguments:
            item     -- The content to add to the queue.
            priority -- Optional priority; if equal to True then
                        the item will be inserted at the head of the
                        queue instead of the end.
        """
        self.put(item, priority)

    def put(self, item, priority=False):
        """
        Add a new item to the queue.

        (Same as self.publish())

        Arguments:
            item     -- The content to add to the queue (string).
            priority -- Optional priority; if equal to True then
                        the item will be inserted at the head of the
                        queue instead of the end.
        """
        id = uuid.uuid4().hex
        pipe = self.redis.pipeline()

        if priority:
            pipe.rpush(self.feed_ids, id)
            pipe.hset(self.feed_items, id, item)
            pipe.incr(self.feed_publishes % self.feed)
        else:
            pipe.lpush(self.feed_ids, id)
            pipe.hset(self.feed_items, id, item)
            pipe.incr(self.feed_publishes)

        pipe.execute()
        return id

    def get(self, timeout=0):
        """
        Retrieve the next item from the queue.

        Raises an Empty exception if the request times out.

        Arguments:
            timeout -- Optional time in seconds to wait before
                       raising an exception.
        """
        result = self.redis.brpop(self.feed_ids, timeout)
        if result is None:
            raise Empty

        id = result[1]
        pipe = self.redis.pipeline()
        pipe.hget(self.feed_items, id)
        pipe.hdel(self.feed_items, id)
        results = pipe.execute()

        return results[0]

    def get_ids(self):
        """Return the set of IDs used by jobs in the queue."""
        return self.redis.lrange(self.feed_ids, 0, -1)

########NEW FILE########
__FILENAME__ = sorted_feed
"""
    Written by Nathan Fritz and Lance Stout. Copyright 2011 by &yet, LLC.
    Released under the terms of the MIT License
"""

from thoonk.feeds import Feed

class SortedFeed(Feed):

    """
    A Thoonk sorted feed is a manually ordered collection of items.

    Redis Keys Used:
        feed.idincr:[feed]  -- A counter for ID values.
        feed.publish:[feed] -- A channel for publishing item position
                               change events.

    Thoonk.py Implementation API:
        get_channels -- Return the standard pubsub channels for this feed.
        get_schemas  -- Return the set of Redis keys used by this feed.

    Thoonk Standard API:
        append    -- Append an item to the end of the feed.
        edit      -- Edit an item in-place.
        get_all   -- Return all items in the feed.
        get_ids   -- Return the IDs of all items in the feed.
        get_item  -- Return a single item from the feed given its ID.
        prepend   -- Add an item to the beginning of the feed.
        retract   -- Remove an item from the feed.
        publish   -- Add an item to the end of the feed.
        publish_after  -- Add an item immediately before an existing item.
        publish_before -- Add an item immediately after an existing item.
    """

    def __init__(self, thoonk, feed):
        """
        Create a new SortedFeed object for a given Thoonk feed.

        Note: More than one SortedFeed objects may be create for the same
              Thoonk feed, and creating a SortedFeed object does not
              automatically generate the Thoonk feed itself.

        Arguments:
            thoonk -- The main Thoonk object.
            feed   -- The name of the feed.
            config -- Optional dictionary of configuration values.

        """
        Feed.__init__(self, thoonk, feed)

        self.feed_id_incr = 'feed.idincr:%s' % feed
        self.feed_position = 'feed.position:%s' % feed

    def get_channels(self):
        """
        Return the Redis key channels for publishing and retracting items.
        """
        return (self.feed_publish, self.feed_retract, self.feed_position)

    def get_schemas(self):
        """Return the set of Redis keys used exclusively by this feed."""
        schema = set((self.feed_id_incr,))
        return schema.union(Feed.get_schemas(self))

    def append(self, item):
        """
        Add an item to the end of the feed.

        (Same as publish)

        Arguments:
            item -- The item contents to add.
        """
        return self.publish(item)

    def prepend(self, item):
        """
        Add an item to the beginning of the feed.

        Arguments:
            item -- The item contents to add.
        """
        id = self.redis.incr(self.feed_id_incr)
        pipe = self.redis.pipeline()
        pipe.lpush(self.feed_ids, id)
        pipe.incr(self.feed_publishes)
        pipe.hset(self.feed_items, id, item)
        self.thoonk._publish(self.feed_publish, (str(id), item), pipe)
        self.thoonk._publish(self.feed_position, (str(id), 'begin:'), pipe)
        pipe.execute()
        return id

    def __insert(self, item, rel_id, method):
        """
        Insert an item into the feed, either before or after an
        existing item.

        Arguments:
            item   -- The item contents to insert.
            rel_id -- The ID of an existing item.
            method -- Either 'BEFORE' or 'AFTER', and indicates
                      where the item will be inserted in relation
                      to rel_id.
        """
        id = self.redis.incr(self.feed_id_incr)
        if method == 'BEFORE':
            pos_rel_id = ':%s' % rel_id
        else:
            pos_rel_id = '%s:' % rel_id
        
        def _insert(pipe):
            if not pipe.hexists(self.feed_items, rel_id):
                return # raise exception?
            pipe.multi()
            pipe.linsert(self.feed_ids, method, rel_id, id)
            pipe.hset(self.feed_items, id, item)
            self.thoonk._publish(self.feed_publish, (str(id), item), pipe)
            self.thoonk._publish(self.feed_position, (str(id), pos_rel_id), pipe)
        
        self.redis.transaction(_insert, self.feed_items)
        return id

    def publish(self, item):
        """
        Add an item to the end of the feed.

        (Same as append)

        Arguments:
            item -- The item contens to add.
        """
        id = self.redis.incr(self.feed_id_incr)
        pipe = self.redis.pipeline()
        pipe.rpush(self.feed_ids, id)
        pipe.incr(self.feed_publishes)
        pipe.hset(self.feed_items, id, item)
        self.thoonk._publish(self.feed_publish, (str(id), item), pipe)
        self.thoonk._publish(self.feed_position, (str(id), ':end'), pipe)
        pipe.execute()
        return id

    def edit(self, id, item):
        """
        Modify an item in-place in the feed.

        Arguments:
            id   -- The ID value of the item to edit.
            item -- The new contents of the item.
        """
        def _edit(pipe):
            if not pipe.hexists(self.feed_items, id):
                return # raise exception?
            pipe.multi()
            pipe.hset(self.feed_items, id, item)
            pipe.incr(self.feed_publishes)
            pipe.publish(self.feed_publish, '%s\x00%s' % (id, item))
        
        self.redis.transaction(_edit, self.feed_items)

    def publish_before(self, before_id, item):
        """
        Add an item immediately before an existing item.

        Arguments:
            before_id -- ID of the item to insert before.
            item      -- The item contents to add.
        """
        return self.__insert(item, before_id, 'BEFORE')

    def publish_after(self, after_id, item):
        """
        Add an item immediately after an existing item.

        Arguments:
            after_id -- ID of the item to insert after.
            item     -- The item contents to add.
        """
        return self.__insert(item, after_id, 'AFTER')

    def move(self, rel_position, id):
        """
        Move an existing item to before or after an existing item.

        Specifying the new location for the item is done by:

            :42    -- Move before existing item ID 42.
            42:    -- Move after existing item ID 42.
            begin: -- Move to beginning of the feed.
            :end   -- Move to the end of the feed.

        Arguments:
            rel_position -- A formatted ID to move before/after.
            id           -- The ID of the item to move.
        """
        if rel_position[0] == ':':
            dir = 'BEFORE'
            rel_id = rel_position[1:]
        elif rel_position[-1] == ':':
            dir = 'AFTER'
            rel_id = rel_position[:-1]
        else:
            raise ValueError('Relative ID formatted incorrectly')
        
        def _move(pipe):
            if not pipe.hexists(self.feed_items, id):
                return
            if rel_id not in ['begin', 'end'] and \
               not pipe.hexists(self.feed_items, rel_id):
                return
            pipe.multi()
            pipe.lrem(self.feed_ids, 1, id)
            if rel_id == 'begin':
                pipe.lpush(self.feed_ids, id)
            elif rel_id == 'end':
                pipe.rpush(self.feed_ids, id)
            else:
                pipe.linsert(self.feed_ids, dir, rel_id, id)

            pipe.publish(self.feed_position,
                         '%s\x00%s' % (id, rel_position))
        
        self.redis.transaction(_move, self.feed_items)

    def move_before(self, rel_id, id):
        """
        Move an existing item to before an existing item.

        Arguments:
            rel_id -- An existing item ID.
            id     -- The ID of the item to move.
        """
        self.move(':%s' % rel_id, id)

    def move_after(self, rel_id, id):
        """
        Move an existing item to after an existing item.

        Arguments:
            rel_id -- An existing item ID.
            id     -- The ID of the item to move.
        """
        self.move('%s:' % rel_id, id)

    def move_first(self, id):
        """
        Move an existing item to the start of the feed.

        Arguments:
            id     -- The ID of the item to move.
        """
        self.move('begin:', id)

    def move_last(self, id):
        """
        Move an existing item to the end of the feed.

        Arguments:
            id     -- The ID of the item to move.
        """
        self.move(':end', id)

    def retract(self, id):
        """
        Remove an item from the feed.

        Arguments:
            id -- The ID value of the item to remove.
        """
        def _retract(pipe):
            if pipe.hexists(self.feed_items, id):
                pipe.multi()
                pipe.lrem(self.feed_ids, 1, id)
                pipe.hdel(self.feed_items, id)
                pipe.publish(self.feed_retract, id)
        
        self.redis.transaction(_retract, self.feed_items)

    def get_ids(self):
        """Return the set of IDs used by items in the feed."""
        return self.redis.lrange(self.feed_ids, 0, -1)

    def get_item(self, id):
        """
        Retrieve a single item from the feed.

        Arguments:
            id -- The ID of the item to retrieve.
        """
        return self.redis.hget(self.feed_items, id)

    def get_items(self):
        """Return all items from the feed."""
        return self.redis.hgetall(self.feed_items)

########NEW FILE########
__FILENAME__ = pubsub
"""
    Written by Nathan Fritz and Lance Stout. Copyright 2011 by &yet, LLC.
    Released under the terms of the MIT License
"""

import redis
import threading
import uuid

from thoonk import feeds, cache
from thoonk.exceptions import FeedExists, FeedDoesNotExist, NotListening

class Thoonk(object):

    """
    Thoonk provides a set of additional, high level datatypes with feed-like
    behaviour (feeds, queues, sorted feeds, job queues) to Redis. A default
    Thoonk instance will provide four feed types:
      feed       -- A simple list of entries sorted by publish date. May be
                    either bounded or bounded in size.
      queue      -- A feed that provides FIFO behaviour. Once an item is
                    pulled from the queue, it is removed.
      job        -- Similar to a queue, but an item is not removed from the
                    queue after it has been request until a job complete
                    notice is received.
      sorted feed -- Similar to a normal feed, except that the ordering of
                     items is not limited to publish date, and can be
                     manually adjusted.

    Thoonk.py also provides an additional pyqueue feed type which behaves
    identically to a queue, except that it pickles/unpickles Python
    datatypes automatically.

    The core Thoonk class provides infrastructure for creating and
    managing feeds.

    Attributes:
        db           -- The Redis database number.
        feeds        -- A set of known feed names.
        feedtypes    -- A dictionary mapping feed type names to their
                        implementation classes.
        handlers     -- A dictionary mapping event names to event handlers.
        host         -- The Redis server host.
        listen_ready -- A thread event indicating when the listening
                        Redis connection is ready.
        listening    -- A flag indicating if this Thoonk instance is for
                        listening to publish events.
        lredis       -- A Redis connection for listening to publish events.
        port         -- The Redis server port.
        redis        -- The Redis connection instance.

    Methods:
        close             -- Terminate the listening Redis connection.
        create_feed       -- Create a new feed using a given type and config.
        create_notice     -- Execute handlers for feed creation event.
        delete_feed       -- Remove an existing feed.
        delete_notice     -- Execute handlers for feed deletion event.
        feed_exists       -- Determine if a feed has already been created.
        get_feeds         -- Return the set of active feeds.
        listen            -- Start the listening Redis connection.
        publish_notice    -- Execute handlers for item publish event.
        register_feedtype -- Make a new feed type available for use.
        register_handler  -- Assign a function as an event handler.
        retract_notice    -- Execute handlers for item retraction event.
        set_config        -- Set the configuration for a given feed.
    """

    def __init__(self, host='localhost', port=6379, db=0, listen=False):
        """
        Start a new Thoonk instance for creating and managing feeds.

        Arguments:
            host   -- The Redis server name.
            port   -- Port for connecting to the Redis server.
            db     -- The Redis database to use.
            listen -- Flag indicating if this Thoonk instance should listen
                      for feed events and relevant event handlers. Defaults
                      to False.
        """
        self.host = host
        self.port = port
        self.db = db
        self.redis = redis.StrictRedis(host=self.host, port=self.port, db=self.db)
        self._feeds = cache.FeedCache(self)
        self.instance = uuid.uuid4().hex

        self.feedtypes = {}

        self.listening = listen
        self.listener = None

        self.feed_publish = 'feed.publish:%s'
        self.feed_retract = 'feed.retract:%s'
        self.feed_config = 'feed.config:%s'

        self.register_feedtype(u'feed', feeds.Feed)
        self.register_feedtype(u'queue', feeds.Queue)
        self.register_feedtype(u'job', feeds.Job)
        self.register_feedtype(u'pyqueue', feeds.PythonQueue)
        self.register_feedtype(u'sorted_feed', feeds.SortedFeed)

        if listen:
            self.listener = ThoonkListener(self)
            self.listener.start()
            self.listener.ready.wait()

    def _publish(self, schema, items=[], pipe=None):
        """
        A shortcut method to publish items separated by \x00.

        Arguments:
            schema -- The key to publish the items to.
            items  -- A tuple or list of items to publish.
            pipe   -- A redis pipeline to use to publish the item using.
                      Note: it is up to the caller to execute the pipe after
                      publishing
        """
        if pipe:
            pipe.publish(schema, "\x00".join(items))
        else:
            self.redis.publish(schema, "\x00".join(items))

    def register_feedtype(self, feedtype, klass):
        """
        Make a new feed type availabe for use.

        New instances of the feed can be created by using:
            self.<feedtype>()

        For example: self.pyqueue() or self.job().

        Arguments:
            feedtype -- The name of the feed type.
            klass    -- The implementation class for the type.
        """
        self.feedtypes[feedtype] = klass

        def startclass(feed, config=None):
            """
            Instantiate a new feed on demand.

            Arguments:
                feed -- The name of the new feed.
                config -- A dictionary of configuration values.

            Returns: Feed of type <feedtype>.
            """
            if config is None:
                config = {}
            config['type'] = feedtype
            try:
                self.create_feed(feed, config)
            except FeedExists:
                pass
            return self._feeds[feed]


        setattr(self, feedtype, startclass)

    def register_handler(self, name, handler):
        """
        Register a function to respond to feed events.

        Event types:
            - create_notice
            - delete_notice
            - publish_notice
            - retract_notice
            - position_notice

        Arguments:
            name    -- The name of the feed event.
            handler -- The function for handling the event.
        """
        if self.listener:
            self.listener.register_handler(name, handler)
        else:
            raise NotListening

    def remove_handler(self, name, handler):
        """
        Unregister a function that was registered via register_handler

        Arguments:
            name    -- The name of the feed event.
            handler -- The function for handling the event.
        """
        if self.listener:
            self.listener.remove_handler(name, handler)
        else:
            raise NotListening

    def create_feed(self, feed, config):
        """
        Create a new feed with a given configuration.

        The configuration is a dict, and should include a 'type'
        entry with the class of the feed type implementation.

        Arguments:
            feed   -- The name of the new feed.
            config -- A dictionary of configuration values.
        """
        if not self.redis.sadd("feeds", feed):
            raise FeedExists
        self.set_config(feed, config, True)

    def delete_feed(self, feed):
        """
        Delete a given feed.

        Arguments:
            feed -- The name of the feed.
        """
        feed_instance = self._feeds[feed]

        def _delete_feed(pipe):
            if not pipe.sismember('feeds', feed):
                raise FeedDoesNotExist
            pipe.multi()
            pipe.srem("feeds", feed)
            for key in feed_instance.get_schemas():
                pipe.delete(key)
            self._publish('delfeed', (feed, self.instance), pipe)

        self.redis.transaction(_delete_feed, 'feeds')

    def set_config(self, feed, config, new_feed=False):
        """
        Set the configuration for a given feed.

        Arguments:
            feed   -- The name of the feed.
            config -- A dictionary of configuration values.
        """
        if not self.feed_exists(feed):
            raise FeedDoesNotExist
        if u'type' not in config:
            config[u'type'] = u'feed'
        pipe = self.redis.pipeline()
        for k, v in config.iteritems():
            pipe.hset('feed.config:' + feed, k, v)
        pipe.execute()
        if new_feed:
            self._publish('newfeed', (feed, self.instance))
        self._publish('conffeed', (feed, self.instance))

    def get_feed_names(self):
        """
        Return the set of known feeds.

        Returns: set
        """
        return self.redis.smembers('feeds') or set()

    def feed_exists(self, feed):
        """
        Check if a given feed exists.

        Arguments:
            feed -- The name of the feed.
        """
        return self.redis.sismember('feeds', feed)

    def close(self):
        """Terminate the listening Redis connection."""
        if self.listening:
            self.redis.publish(self.listener._finish_channel, "")
            self.listener.finished.wait()
        self.redis.connection_pool.disconnect()


class ThoonkListener(threading.Thread):

    def __init__(self, thoonk, *args, **kwargs):
        threading.Thread.__init__(self, *args, **kwargs)
        self.lock = threading.Lock()
        self.handlers = {}
        self.thoonk = thoonk
        self.ready = threading.Event()
        self.redis = redis.StrictRedis(host=thoonk.host, port=thoonk.port, db=thoonk.db)
        self.finished = threading.Event()
        self.instance = thoonk.instance
        self._finish_channel = "listenerclose_%s" % self.instance
        self._pubsub = None
        self.daemon = True

    def finish(self):
        self.redis.publish(self._finish_channel, "")

    def run(self):
        """
        Listen for feed creation and manipulation events and execute
        relevant event handlers. Specifically, listen for:
            - Feed creations
            - Feed deletions
            - Configuration changes
            - Item publications.
            - Item retractions.
        """
        # listener redis object
        self._pubsub = self.redis.pubsub()
        # subscribe to feed activities channel
        self._pubsub.subscribe((self._finish_channel, 'newfeed', 'delfeed', 'conffeed'))

        # subscribe to exist feeds retract and publish
        for feed in self.redis.smembers("feeds"):
            self._pubsub.subscribe(self.thoonk._feeds[feed].get_channels())

        self.ready.set()
        for event in self._pubsub.listen():
            type = event.pop("type")
            if event["channel"] == self._finish_channel:
                if self._pubsub.subscription_count:
                    self._pubsub.unsubscribe()
            elif type == 'message':
                self._handle_message(**event)
            elif type == 'pmessage':
                self._handle_pmessage(**event)

        self.finished.set()

    def _handle_message(self, channel, data, pattern=None):
        if channel == 'newfeed':
            #feed created event
            name, _ = data.split('\x00')
            self._pubsub.subscribe(("feed.publish:"+name, "feed.edit:"+name,
                "feed.retract:"+name, "feed.position:"+name, "job.finish:"+name))
            self.emit("create", name)

        elif channel == 'delfeed':
            #feed destroyed event
            name, _ = data.split('\x00')
            try:
                del self._feeds[name]
            except:
                pass
            self.emit("delete", name)

        elif channel == 'conffeed':
            feed, _ = data.split('\x00', 1)
            self.emit("config:"+feed, None)

        elif channel.startswith('feed.publish'):
            #feed publish event
            id, item = data.split('\x00', 1)
            self.emit("publish", channel.split(':', 1)[-1], item, id)

        elif channel.startswith('feed.edit'):
            #feed publish event
            id, item = data.split('\x00', 1)
            self.emit("edit", channel.split(':', 1)[-1], item, id)

        elif channel.startswith('feed.retract'):
            self.emit("retract", channel.split(':', 1)[-1], data)

        elif channel.startswith('feed.position'):
            id, rel_id = data.split('\x00', 1)
            self.emit("position", channel.split(':', 1)[-1], id, rel_id)

        elif channel.startswith('job.finish'):
            id, result = data.split('\x00', 1)
            self.emit("finish", channel.split(':', 1)[-1], id, result)

    def emit(self, event, *args):
        with self.lock:
            for handler in self.handlers.get(event, []):
                handler(*args)

    def register_handler(self, name, handler):
        """
        Register a function to respond to feed events.

        Event types:
            - create_notice
            - delete_notice
            - publish_notice
            - retract_notice
            - position_notice

        Arguments:
            name    -- The name of the feed event.
            handler -- The function for handling the event.
        """
        with self.lock:
            if name not in self.handlers:
                self.handlers[name] = []
            self.handlers[name].append(handler)

    def remove_handler(self, name, handler):
        """
        Unregister a function that was registered via register_handler

        Arguments:
            name    -- The name of the feed event.
            handler -- The function for handling the event.
        """
        with self.lock:
            try:
                self.handlers[name].remove(handler)
            except (KeyError, ValueError):
                pass

########NEW FILE########
