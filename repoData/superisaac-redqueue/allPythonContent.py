__FILENAME__ = client_test
#!/usr/bin/python
####################################################################
#
# All of the deliverable code in REDQUEUE has been dedicated to the
# PUBLIC DOMAIN by the authors.
#
# Author: Zeng Ke  superisaac.ke at gmail dot com
#
####################################################################
import sys, os
import time
import logging
import memcache
logging.basicConfig(stream=sys.stdout)
def get_mc():
    mc = memcache.Client(['127.0.0.1:12345'])
    return mc
mc = get_mc()

def take(key):
    v = mc.get(key)
    if v is not None:
        mc.delete(key)
    return v
    
def clean_queue(key):
    mc.delete(key)
    while True:
        if take(key) is None:
            break

def test_queue():
    #clean_queue('abc/def')
    mc.set('abc/def', 'I')
    mc.set('abc/def', 'really')
    mc.set('abc/def', 'love')
    mc.set('abc/def', 'it')
    assert(take('abc/def') == 'I')
    assert(take('abc/def') == 'really')
    assert(take('abc/def') == 'love')
    assert(take('abc/def') == 'it')
    assert(take('abc/def') is None)
    print 'test queue ok'

def test_timeout():
    clean_queue('abc/def')
    mc.set('abc/def', 'I')
    mc.set('abc/def', 'really', 3) # time out is 3 seconds
    mc.set('abc/def', 'love')
    mc.set('abc/def', 'it')

    time.sleep(5)
    assert(take('abc/def') == 'I')
    assert(take('abc/def') == 'love')
    assert(take('abc/def') == 'it')
    assert(take('abc/def') is None)
    print 'test queue timeout ok'

def test_reservation():
    clean_queue('abc')
    clean_queue('def')
    mc.set('abc', 'I')
    mc.set('abc', 'really')
    mc.set('config:reserv', 1)
    assert(mc.get('abc') == 'I')
    assert(mc.get('abc') is None)
    mc.delete('abc')
    assert(take('abc') == 'really')
    print 'test reservation ok'

def test_reservation_close():
    global mc
    clean_queue('abc')
    mc.set('abc', 'I')
    mc.set('abc', 'love')
    assert(mc.get('abc') == 'I')
    mc.disconnect_all()

    mc = get_mc()
    assert(take('abc') == 'love')
    assert(mc.get('abc') == 'I')
    print 'test reservation on close ok'

def test_server_error():
    """
    use send argument first
    % python client_test.py send
    I
    then kill server and restart server
    % python client_test.py
    love
    % python client_test.py
    I
    % python client_test.py
    love
    ...
    """
    if sys.argv[1:] == ['send']:
        mc.set('xyz', 'I')
        mc.set('xyz', 'love')
        print mc.get('xyz')
    else:
        print mc.get('xyz')

def test_get_multi():
    clean_queue('abc')
    clean_queue('def')
    clean_queue('ghi')
    clean_queue('jkl')
    
    mc.set('def', 'I')
    mc.set('abc', 'love')
    mc.set('ghi', 'it')
    assert(mc.get('def') == 'I')
    #print mc.get_multi(['abc', 'def', 'ghi', 'jkl'])
    assert(mc.get_multi(['abc', 'def', 'ghi', 'jkl']) ==
           {'abc': 'love', 'ghi': 'it'})
    print 'test get multi ok'

def test_delete_multi():
    clean_queue('abc')
    clean_queue('def')
    clean_queue('ghi')
    clean_queue('jkl')

    mc.set('def', 'I')
    mc.set('abc', 'love')
    assert(mc.get('def') == 'I')
    mc.delete_multi(['abc', 'def', 'ghi', 'jkl'])
    assert(mc.get_multi(['abc', 'def', 'ghi', 'jkl']) ==
           {'abc': 'love'})
    
def test_performance():
    for _ in xrange(100):
        for i in xrange(100):
            mc.set('perf', i)
        for i in xrange(100):
            take('perf')

if __name__ == '__main__':
    test_queue()
    test_timeout()
    test_reservation()
    test_reservation_close()
    test_get_multi()
    test_delete_multi()
    test_server_error()
    #test_performance()
    


########NEW FILE########
__FILENAME__ = queue
#!/usr/bin/python
####################################################################
#
# All of the deliverable code in REDQUEUE has been dedicated to the
# PUBLIC DOMAIN by the authors.
#
# Author: Zeng Ke  superisaac.ke at gmail dot com
#
####################################################################
import re, os, sys
import logging
import time
import urllib
from collections import deque

JOURNAL_CAPACITY = 1 #024 * 1024 # 1 mega bytes for each chunk

#TODO: binary log
class Queue(object):
    def __init__(self, key):
        self.key = key
        self._queue = deque()
        self._jfile = None
        self._lent = {}

    def addjournal(self, w):
        pass
    def rotate_journal(self):
        pass

    def give_back(self, prot_id):
        """ Give the elememt borrowed by prot_id back for future calling"""
        timeout, data = self._lent.pop(prot_id)        
        self._queue.appendleft((timeout, data))
        self.addjournal('R %s\r\n' % prot_id)

    def give(self, timeout, data):
        self._queue.appendleft((timeout, data))
        self.addjournal('S %d %d\r\n%s\r\n' % (timeout,
                                           len(data), data))

    def use(self, prot_id):
        """ Mark the element borrowed by prot_id used
        """
        if prot_id in self._lent:
            self.addjournal("U %s\r\n" % prot_id)
            del self._lent[prot_id]
        self.rotate_journal()

    def reserve(self, prot_id):
        """ Reserve an element by prot_id and return it later, or the
        server will recycle it"""
        while True:
            try:
                timeout, data = self._queue.pop()
            except IndexError:
                return None
            self.addjournal('B %s\r\n' % prot_id)

            if timeout > 0 and timeout < time.time():
                continue
            assert prot_id not in self._lent
            self._lent[prot_id] = (timeout, data)
            return timeout, data

    def take(self, prot_id):
        t = self.reserve(prot_id)
        if t is not None:
            self.use(prot_id)
        return t

    def load_from_journal(self, jpath):
        jfile = open(jpath, 'rb')
        lent = {}
        while True:
            line = jfile.readline()
            if not line:
                break
            if line.startswith('B'): # Borrow an item
                _, prot_id = line.split()
                try:
                    data = self._queue.pop()
                    lent[prot_id] = data
                except IndexError:
                    logging.error('Pop from empty stack')
            elif line.startswith('U'):  # Use an item
                _, prot_id = line.split()
                assert prot_id in lent
                del lent[prot_id]
            elif line.startswith('R'):  # Return an item
                _, prot_id = line.split()
                assert prot_id in lent
                t = lent.pop(prot_id)
                self._queue.appendleft(t)
            elif line.startswith('S'):
                t, timeout, lendata = line.split()
                data = jfile.read(int(lendata))
                jfile.read(2) # line break
                self._queue.appendleft((int(timeout),
                                        data))
            else:
                journalging.error('Bad format for journal file %s' % jpath)

        for t in lent.itervalues():
            self._queue.appendleft(t)
        self._lent = {}
        jfile.close()

class ReliableQueue(Queue):
    def addjournal(self, w):
        os.write(self._jfile.fileno(), w)
        self._jfile.flush()

    def addjournal_sync(self, w):
        os.write(self._jfile.fileno(), w)
        self._jfile.flush()
        #os.fdatasync(self._jfile.fileno())
        os.fsync(self._jfile.fileno())
        
    def _journal_file_name(self):
        return os.path.join(self.server.jdir,
                            '%s.log' % urllib.quote_plus(self.key))
    def rotate_journal(self):
        if self._jfile is None:
            self._jfile = open(self._journal_file_name(), 'ab')
        elif (len(self._queue) == 0 and
              len(self._lent) == 0 and
              self._jfile.tell() >= JOURNAL_CAPACITY):
            self._jfile.close()
            curr_journal_fn = self._journal_file_name()
            journal_fn = '%s.%d' % (curr_journal_fn, time.time())
            os.rename(curr_journal_fn, journal_fn)
            logging.info('rotate journal to %s' % journal_fn)
            self._jfile = open(curr_journal_fn, 'ab')

class QueueFactory(object):
    queue_class = Queue
    def __init__(self, jdir):
        self.queue_collection = {}
        self.jdir = jdir

    def get_queue(self, key, auto_create=True):
        if key not in self.queue_collection and auto_create:
            q = self.queue_class(key)
            q.server = self
            q.rotate_journal()
            self.queue_collection[key] = q            
        return self.queue_collection.get(key)

    def scan_journals(self):
        logging.info('Sanning journals ...')
        for fn in os.listdir(self.jdir):
            m = re.search(r'\.log$', fn)
            if m:
                key = fn[:m.start()]
                ukey = urllib.unquote_plus(key)
                logging.info('Restoring queue %s ...' % ukey)
                queue = self.get_queue(ukey)
                queue.load_from_journal(os.path.join(self.jdir,
                                                 '%s.log' % key))
        logging.info('Redqueue is ready to serve.')

########NEW FILE########
__FILENAME__ = server
#!/usr/bin/python
####################################################################
#
# All of the deliverable code in REDQUEUE has been dedicated to the
# PUBLIC DOMAIN by the authors.
#
# Author: Zeng Ke  superisaac.ke at gmail dot com
#
####################################################################
import re, os, sys
import socket
import logging
import time

from tornado import iostream
from tornado import ioloop

from redqueue.queue import QueueFactory, Queue, ReliableQueue

class MemcacheServer(object):
    def __init__(self, logdir, reliable='no'):
        self.queue_factory = QueueFactory(logdir)
        if reliable in ('yes', 'sync'):
            self.queue_factory.queue_class = ReliableQueue
            if reliable == 'sync':
                ReliableQueue.addlog = ReliableQueue.addlog_sync
        else:
            self.queue_factory.queue_class = Queue
        self.watchers = {}

    def notify(self, key):
        if key in self.watchers:
            ioloop.IOLoop.instance().add_callback(self.watchers[key].check)

    def handle_accept(self, fd, events):
        conn, addr = self._sock.accept()
        p = MemcacheProtocol(iostream.IOStream(conn))
        p.server = self

    def start(self, host, port):
        self.queue_factory.scan_journals()
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM, 0)
        self._sock.setblocking(0)
        self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._sock.bind((host, port))
        self._sock.listen(128)
        ioloop.IOLoop.instance().add_handler(self._sock.fileno(),
                                             self.handle_accept,
                                             ioloop.IOLoop.READ)
class MemcacheProtocol(object):
    def __init__(self, stream):
        self.protocol_id = str(id(self))
        self.stream = stream
        self.stream.set_close_callback(self._return_data)
        self.route = {
            'get': self.handle_get,
            'gets': self.handle_gets,
            'set': self.handle_set,
            'delete': self.handle_delete}
        self.wait_for_line()
        self.resved_keys = set()

    def use_key(self, key=None):
        """ Mark all reserved keys or the specified key as used """
        if key is None:
            for k in self.resved_keys:
                self.server.queue_factory.get_queue(k).use(self.protocol_id)
            self.resved_keys = set()
        elif key in self.resved_keys:
            self.server.queue_factory.get_queue(key).use(self.protocol_id)
            self.resved_keys.remove(key)

    def _return_data(self):
        for key in self.resved_keys:
            self.server.queue_factory.get_queue(key).give_back(self.protocol_id)
        self.resved_keys = set()

    def wait_for_line(self):
        self.stream.read_until('\r\n', self.line_received)

    def line_received(self, line):
        args = line.split()
        data_required = self.route.get(args[0].lower(),
                                       self.handle_unknown)(*args[1:])
        if not data_required:
            self.wait_for_line()

    def handle_unknown(self, *args):
        self.stream.write("CLIENT_ERROR bad command line format\r\n")

    def handle_set(self, key, flags, exptime, bytes, *args):
        bytes = int(bytes)
        exptime = int(exptime)
        if exptime > 0:
            exptime = time.time() + exptime
        def on_set_data(data):
            data = data[:-2]
            q = self.server.queue_factory.get_queue(key)
            q.give(exptime, data)
            self.stream.write('STORED\r\n')
            self.wait_for_line()
            self.server.notify(key)
        self.stream.read_bytes(bytes + 2, on_set_data)
        return True

    def _get_data(self, key):
        if key in self.resved_keys:
            return None
        q = self.server.queue_factory.get_queue(key, auto_create=False)
        t = None
        if q:
            t = q.reserve(prot_id=self.protocol_id)
        if t:
            self.resved_keys.add(key)
            return t[1] # t is a tuple of (timeout, data)

    def handle_get(self, *keys):
        for key in keys:
            data  = self._get_data(key)
            if data:
                self.stream.write('VALUE %s 0 %d\r\n%s\r\n' % (key, len(data), data))
        self.stream.write('END\r\n')
        
    def handle_gets(self, *keys):
        """ Gets here is like a poll(), return the first non-empty queue
        number, so that a client can wait several queues.
        """
        for key in keys:
            data = self._get_data(key)
            if data:
                self.stream.write('VALUE %s 0 %d\r\n%s\r\n' % (key, len(data), data))
                break
        self.stream.write('END\r\n')
                
    def handle_delete(self, key, *args):
        if key in self.resved_keys:
            self.use_key(key)
            self.stream.write('DLETED\r\n')
        else:
            self.stream.write('NOT_DELETED\r\n')

Server = MemcacheServer

########NEW FILE########
__FILENAME__ = task
import random
import time
import logging
import urllib

try:
    import json
except ImportError:
    import simplejson as json
    
from tornado import ioloop
from tornado.httpclient import AsyncHTTPClient

class Task(object):
    """ A task runner that periodically check a key to fetch and
    execute new tasks"""    
    key = None
    def __init__(self, server):
        self.server = server
        self.queue_factory = server.queue_factory
        self.prot_id = 'task:%s' % id(self)

    def watch(self):
        assert self.key, 'Task key must be set'
        self.server.watchers[self.key] = self

    def unwatch(self):
        watcher = self.server.watchers.get(self.key)
        if watcher == self:
            del self.server.watchers[self.key]

    def check(self):
        q = self.queue_factory.get_queue(self.key)
        t = q.take(self.prot_id)
        if t is not None:
            _, data = t
            if data:
                data = json.loads(data)
            try:
                self.on_data(data)
            except Exception, e:
                logging.error('Task(%s) error %s' % (self.__class__.__name__, e),
                              exc_info=True)

    def on_data(self, data):
        """ The callback when a task with data comes."""
        raise NotImplemented

class URLFetchTask(Task):
    """ Fetch an url, currently only HTTP scheme is supported.
    """
    key = 'task:url'
    def on_data(self, data):
        if isinstance(data, basestring):
            url = data
            delay = 0
            method = 'GET'
        else: # data should be a dictionary
            url = data['url']
            delay = data.get('delay', 0)
            method = data.get('method', 'GET')
            
        def handle_response(response):
            if response.error:
                logging.error('Error %s while fetch url %s' % (response.error,
                                                               url))
            else:
                logging.info('URL %s fetched.' % url)

        def fetch_url(url):
            logging.info('Fetching url %s' % url)
            http_client = AsyncHTTPClient()
            if method == 'POST':
                postdata = urllib.urlencode(data.get('body', {}))
            else:
                postdata = None
            http_client.fetch(url, handle_response,
                              method=method, body=postdata)

        if delay:
            ioloop.IOLoop.instance().add_timeout(time.time() + delay,
                                                 lambda: fetch_url(url))
        else:
            fetch_url(url)


runnable_tasks = [URLFetchTask]

def run_all(server):
    for task_cls in runnable_tasks:
        task = task_cls(server)
        task.watch()


########NEW FILE########
__FILENAME__ = redqueue_server
#!/usr/bin/python
####################################################################
#
# All of the deliverable code in REDQUEUE has been dedicated to the
# PUBLIC DOMAIN by the authors.
#
# Author: Zeng Ke  superisaac.ke at gmail dot com
#
####################################################################
import re, os, sys
import logging

from tornado import ioloop
import tornado.options
from tornado.options import define, options
from redqueue.server import Server
from redqueue import task

define('host', default="0.0.0.0", help="The binded ip host")
define('port', default=11211, type=int, help='The port to be listened')
define('jdir', default='journal', help='The directory to put journals')
define('reliable', default='yes', help='Store data to log files, options: (no, yes, sync)')
define('logfile', default='', help='Place where logging rows(info, debug, ...) are put.')

def main():
    tornado.options.parse_command_line()
    if options.logfile:
        logging.basicConfig(filename=options.logfile, level=logging.DEBUG)

    if not os.path.isdir(options.jdir):
        logging.error('Log directory %s does not exist.' % options.jdir)
        sys.exit(1)
    server = Server(options.jdir, options.reliable)
    server.start(options.host, options.port)
    task.run_all(server)
    ioloop.IOLoop.instance().start()

if __name__ == '__main__':
    main()

########NEW FILE########
