__FILENAME__ = test
import lggr
use_gmail = False

mylggr = lggr.Lggr()
mylggr.add(lggr.ALL, lggr.FilePrinter("~/output.log"))
mylggr.add(lggr.ALL, lggr.StderrPrinter())
mylggr.add(lggr.ALL, lggr.Printer())

if use_gmail:
	g_user = raw_input("Gmail address ('user@gmail.com', not 'user'): ")
	g_pass = raw_input("Gmail password: ")
	mylggr.add(lggr.CRITICAL, lggr.GMailer([g_user], g_user, g_pass))

for level in lggr.ALL:
	print "Level {}:".format(level)
	for log_func in mylggr.config[level]:
		print '\t{}'.format(log_func)

mylggr.debug("Hello, ")
mylggr.info("world!")
mylggr.warning("My name is {}", "Peter")
mylggr.error("Testing some {name} logging", {"name":"ERROR"})

old = mylggr.config['defaultfmt']
mylggr.config['defaultfmt'] = '{asctime} ({levelname}) {logmessage}\nIn {pathname}, line {lineno}:\n{codecontext}'
def outer(a):
	def inner(b):
		def final(c):
			mylggr.critical("Easy as {}, {}, {}!", a, b, c)
		return final
	return inner

outer(1)(2)(3)
outer("a")("b")("c")


mylggr.config['defaultfmt'] = old
mylggr.all("This goes out to all of my friends")
mylggr.multi([lggr.WARNING, lggr.INFO], "This is only going to some of my friends")

mylggr.clear(lggr.CRITICAL)
mylggr.clear(lggr.WARNING)
mylggr.clear(lggr.INFO)

mylggr.info("Testing....")
mylggr.error("Testing {} {} {}", "another", "stupid", "thing")

mylggr.close()
mylggr.log(lggr.ALL, "Help?")

########NEW FILE########
__FILENAME__ = coroutine
# coding: utf-8
import sys
import time
import Queue
import threading
import multiprocessing

def coroutine(func):
    """ Decorator for priming co-routines that use (yield) """
    def wrapper(*args, **kwargs):
        c = func(*args, **kwargs)
        c.next() # prime it for iteration
        return c
    return wrapper

class CoroutineProcess(multiprocessing.Process):
    """ Will run a coroutine in its own process, using the multiprocessing
    library. The coroutine thread runs as a daemon, and is closed automatically
    when it is no longer needed. Because it exposes send and close methods, a
    CoroutineProcess wrapped coroutine can be dropped in for a regular
    coroutine."""

    def __init__(self, target_func):
        multiprocessing.Process.__init__(self)
        self.in_queue = multiprocessing.Queue()
        self.processor = target_func
        self.daemon = True
        # Allows the thread to close correctly
        self.shutdown = multiprocessing.Event()

    def send(self, item):
        if self.shutdown.is_set():
            raise StopIteration
        self.in_queue.put(item)

    def __call__(self, *args, **kwargs):
        # Prime the wrapped coroutine.
        self.processor = self.processor(*args, **kwargs)
        self.processor.next()
        self.start()
        return self

    def run(self): # this is the isolated 'process' being run after start() is called
        try:
            while True:
                item = self.in_queue.get()
                self.processor.send(item) # throws StopIteration if close() has been called
        except StopIteration:
            pass
        self.close()

    def close(self):
        self.processor.close()
        self.shutdown.set()

def coroutine_process(func):
    def wrapper(*args, **kwargs):
        cp = CoroutineProcess(func)
        cp = cp(*args, **kwargs)
        # XXX(todo): use @CoroutineProcess on an individual function, then wrap
        # with @coroutine, too. Don't start until .next().
        return cp
    return wrapper

class CoroutineThread(threading.Thread):
    """ Wrapper for coroutines; runs in their own threads. """
    def __init__(self, target_func):
        threading.Thread.__init__(self) # creates a thread
        self.setDaemon(True)
        self.in_queue = Queue.Queue() # creates a queue for cross-thread communication
        self.processor = target_func # the function to process incoming data
        self.shutdown = threading.Event() # watch for close

    def send(self, item):
        if self.shutdown.isSet():
            raise StopIteration
        self.in_queue.put(item)

    def __call__(self, *args, **kwargs):
        # Prime the wrapped coroutine.
        self.processor = self.processor(*args, **kwargs)
        self.processor.next()
        self.start()
        return self

    def run(self): # this is running in its own thread after it is created
        try:
            while True:
                item = self.in_queue.get()
                if self.shutdown.is_set(): break
                self.processor.send(item)
        except StopIteration:
            pass
        self.shutdown.set()

    def close(self):
        self.shutdown.set()

def coroutine_thread(func):
    def wrapper(*args, **kwargs):
        cp = CoroutineThread(func)
        cp = cp(*args, **kwargs)
        # XXX(todo): use @CoroutineProcess on an individual function, then wrap
        # with @coroutine, too. Don't start until .next().
        return cp
    return wrapper



########NEW FILE########
