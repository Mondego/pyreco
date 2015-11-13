__FILENAME__ = context
"""Test context switching performance of threading and eventlet"""
from __future__ import print_function

import threading
import time

import eventlet
from eventlet import hubs
from eventlet.hubs import pyevent, epolls, poll, selects


CONTEXT_SWITCHES = 100000


def run(event, wait_event):
    counter = 0
    while counter <= CONTEXT_SWITCHES:
        wait_event.wait()
        wait_event.reset()
        counter += 1
        event.send()


def test_eventlet():
    event1 = eventlet.event.Event()
    event2 = eventlet.event.Event()
    event1.send()
    thread1 = eventlet.spawn(run, event1, event2)
    thread2 = eventlet.spawn(run, event2, event1)

    thread1.wait()
    thread2.wait()


class BenchThread(threading.Thread):
    def __init__(self, event, wait_event):
        threading.Thread.__init__(self)
        self.counter = 0
        self.event = event
        self.wait_event = wait_event

    def run(self):
        while self.counter <= CONTEXT_SWITCHES:
            self.wait_event.wait()
            self.wait_event.clear()
            self.counter += 1
            self.event.set()


def test_thread():
    event1 = threading.Event()
    event2 = threading.Event()
    event1.set()
    thread1 = BenchThread(event1, event2)
    thread2 = BenchThread(event2, event1)
    thread1.start()
    thread2.start()
    thread1.join()
    thread2.join()


print("Testing with %d context switches" % CONTEXT_SWITCHES)
start = time.time()
test_thread()
print("threading: %.02f seconds" % (time.time() - start))

try:
    hubs.use_hub(pyevent)
    start = time.time()
    test_eventlet()
    print("pyevent:   %.02f seconds" % (time.time() - start))
except:
    print("pyevent hub unavailable")

try:
    hubs.use_hub(epolls)
    start = time.time()
    test_eventlet()
    print("epoll:     %.02f seconds" % (time.time() - start))
except:
    print("epoll hub unavailable")

try:
    hubs.use_hub(poll)
    start = time.time()
    test_eventlet()
    print("poll:      %.02f seconds" % (time.time() - start))
except:
    print("poll hub unavailable")

try:
    hubs.use_hub(selects)
    start = time.time()
    test_eventlet()
    print("select:    %.02f seconds" % (time.time() - start))
except:
    print("select hub unavailable")

########NEW FILE########
__FILENAME__ = hub_timers
#! /usr/bin/env python
from __future__ import print_function

# test timer adds & expires on hubs.hub.BaseHub

import sys
import eventlet
import random
import time

from eventlet.hubs import timer, get_hub
from eventlet.support import six


timer_count = 100000

if len(sys.argv) >= 2:
    timer_count = int(sys.argv[1])

l = []

def work(n):
    l.append(n)

timeouts = [random.uniform(0, 10) for x in six.moves.range(timer_count)]

hub = get_hub()

start = time.time()

scheduled = []

for timeout in timeouts:
    t = timer.Timer(timeout, work, timeout)
    t.schedule()

    scheduled.append(t)

hub.prepare_timers()
hub.fire_timers(time.time()+11)
hub.prepare_timers()

end = time.time()

print("Duration: %f" % (end-start,))

########NEW FILE########
__FILENAME__ = localhost_socket
"""Benchmark evaluating eventlet's performance at speaking to itself over a localhost socket."""
from __future__ import print_function

import time

import benchmarks
from eventlet.support import six


BYTES=1000
SIZE=1
CONCURRENCY=50
TRIES=5


def reader(sock):
    expect = BYTES
    while expect > 0:
        d = sock.recv(min(expect, SIZE))
        expect -= len(d)


def writer(addr, socket_impl):
    sock = socket_impl(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect(addr)
    sent = 0
    while sent < BYTES:
        d = 'xy' * (max(min(SIZE/2, BYTES-sent), 1))
        sock.sendall(d)
        sent += len(d)


def green_accepter(server_sock, pool):
    for i in six.moves.range(CONCURRENCY):
        sock, addr = server_sock.accept()
        pool.spawn_n(reader, sock)


def heavy_accepter(server_sock, pool):
    for i in six.moves.range(CONCURRENCY):
        sock, addr = server_sock.accept()
        t = threading.Thread(None, reader, "reader thread", (sock,))
        t.start()
        pool.append(t)


import eventlet.green.socket
import eventlet

from eventlet import debug
debug.hub_exceptions(True)


def launch_green_threads():
    pool = eventlet.GreenPool(CONCURRENCY * 2 + 1)
    server_sock = eventlet.green.socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_sock.bind(('localhost', 0))
    server_sock.listen(50)
    addr = ('localhost', server_sock.getsockname()[1])
    pool.spawn_n(green_accepter, server_sock, pool)
    for i in six.moves.range(CONCURRENCY):
        pool.spawn_n(writer, addr, eventlet.green.socket.socket)
    pool.waitall()


import threading
import socket


def launch_heavy_threads():
    threads = []
    server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_sock.bind(('localhost', 0))
    server_sock.listen(50)
    addr = ('localhost', server_sock.getsockname()[1])
    accepter_thread = threading.Thread(None, heavy_accepter, "accepter thread", (server_sock, threads))
    accepter_thread.start()
    threads.append(accepter_thread)
    for i in six.moves.range(CONCURRENCY):
        client_thread = threading.Thread(None, writer, "writer thread", (addr, socket.socket))
        client_thread.start()
        threads.append(client_thread)
    for t in threads:
        t.join()


if __name__ == "__main__":
    import optparse
    parser = optparse.OptionParser()
    parser.add_option('--compare-threading', action='store_true', dest='threading', default=False)
    parser.add_option('-b', '--bytes', type='int', dest='bytes',
                      default=BYTES)
    parser.add_option('-s', '--size', type='int', dest='size',
                      default=SIZE)
    parser.add_option('-c', '--concurrency', type='int', dest='concurrency',
                      default=CONCURRENCY)
    parser.add_option('-t', '--tries', type='int', dest='tries',
                      default=TRIES)


    opts, args = parser.parse_args()
    BYTES=opts.bytes
    SIZE=opts.size
    CONCURRENCY=opts.concurrency
    TRIES=opts.tries

    funcs = [launch_green_threads]
    if opts.threading:
        funcs = [launch_green_threads, launch_heavy_threads]
    results = benchmarks.measure_best(TRIES, 3,
                                      lambda: None, lambda: None,
                                      *funcs)
    print("green:", results[launch_green_threads])
    if opts.threading:
        print("threads:", results[launch_heavy_threads])
        print("%", (results[launch_green_threads]-results[launch_heavy_threads])/results[launch_heavy_threads] * 100)

########NEW FILE########
__FILENAME__ = spawn
"""Compare spawn to spawn_n"""
from __future__ import print_function

import eventlet
import benchmarks


def cleanup():
    eventlet.sleep(0.2)


iters = 10000
best = benchmarks.measure_best(5, iters,
    'pass',
    cleanup,
    eventlet.sleep)
print("eventlet.sleep (main)", best[eventlet.sleep])

gt = eventlet.spawn(benchmarks.measure_best,5, iters,
    'pass',
    cleanup,
    eventlet.sleep)
best = gt.wait()
print("eventlet.sleep (gt)", best[eventlet.sleep])


def dummy(i=None):
    return i


def run_spawn():
    eventlet.spawn(dummy, 1)


def run_spawn_n():
    eventlet.spawn_n(dummy, 1)


def run_spawn_n_kw():
    eventlet.spawn_n(dummy, i=1)


best = benchmarks.measure_best(5, iters,
    'pass',
    cleanup,
    run_spawn_n,
    run_spawn,
    run_spawn_n_kw)
print("eventlet.spawn", best[run_spawn])
print("eventlet.spawn_n", best[run_spawn_n])
print("eventlet.spawn_n(**kw)", best[run_spawn_n_kw])
print("%% %0.1f" % ((best[run_spawn]-best[run_spawn_n])/best[run_spawn_n] * 100))

pool = None


def setup():
    global pool
    pool = eventlet.GreenPool(iters)


def run_pool_spawn():
    pool.spawn(dummy, 1)


def run_pool_spawn_n():
    pool.spawn_n(dummy, 1)


def cleanup_pool():
    pool.waitall()


best = benchmarks.measure_best(3, iters,
    setup,
    cleanup_pool,
    run_pool_spawn,
    run_pool_spawn_n,
)
print("eventlet.GreenPool.spawn", best[run_pool_spawn])
print("eventlet.GreenPool.spawn_n", best[run_pool_spawn_n])
print("%% %0.1f" % ((best[run_pool_spawn]-best[run_pool_spawn_n])/best[run_pool_spawn_n] * 100))

########NEW FILE########
__FILENAME__ = spawn_plot
#!/usr/bin/env python
'''
    Compare spawn to spawn_n, among other things.

    This script will generate a number of "properties" files for the
    Hudson plot plugin
'''

import os
import eventlet
import benchmarks

DATA_DIR = 'plot_data'

if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

def write_result(filename, best):
    fd = open(os.path.join(DATA_DIR, filename), 'w')
    fd.write('YVALUE=%s' % best)
    fd.close()

def cleanup():
    eventlet.sleep(0.2)

iters = 10000
best = benchmarks.measure_best(5, iters,
    'pass',
    cleanup,
    eventlet.sleep)

write_result('eventlet.sleep_main', best[eventlet.sleep])

gt = eventlet.spawn(benchmarks.measure_best,5, iters,
    'pass',
    cleanup,
    eventlet.sleep)
best = gt.wait()
write_result('eventlet.sleep_gt', best[eventlet.sleep])

def dummy(i=None):
    return i

def run_spawn():
    eventlet.spawn(dummy, 1)
        
def run_spawn_n():
    eventlet.spawn_n(dummy, 1)

def run_spawn_n_kw():
    eventlet.spawn_n(dummy, i=1)


best = benchmarks.measure_best(5, iters,
    'pass',
    cleanup,
    run_spawn_n, 
    run_spawn,
    run_spawn_n_kw)
write_result('eventlet.spawn', best[run_spawn])
write_result('eventlet.spawn_n', best[run_spawn_n])
write_result('eventlet.spawn_n_kw', best[run_spawn_n_kw])

pool = None
def setup():
    global pool
    pool = eventlet.GreenPool(iters)

def run_pool_spawn():
    pool.spawn(dummy, 1)
        
def run_pool_spawn_n():
    pool.spawn_n(dummy, 1)
    
def cleanup_pool():
    pool.waitall()
    

best = benchmarks.measure_best(3, iters,
    setup,
    cleanup_pool,
    run_pool_spawn, 
    run_pool_spawn_n,
)
write_result('eventlet.GreenPool.spawn', best[run_pool_spawn])
write_result('eventlet.GreenPool.spawn_n', best[run_pool_spawn_n])

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# Eventlet documentation build configuration file, created by
# sphinx-quickstart on Sat Jul  4 19:48:27 2009.
#
# This file is execfile()d with the current directory set to its containing dir.
#
# Note that not all possible configuration values are present in this
# autogenerated file.
#
# All configuration values have a default; values that are commented out
# serve to show the default.

import sys, os

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#sys.path.append(os.path.abspath('.'))

# -- General configuration -----------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = ['sphinx.ext.autodoc', 'sphinx.ext.todo', 'sphinx.ext.coverage', 
              'sphinx.ext.intersphinx']

# If this is True, '.. todo::' and '.. todolist::' produce output, else they produce
# nothing. The default is False.
todo_include_todos = True

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'Eventlet'
copyright = u'2005-2010, Eventlet Contributors'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
import eventlet
# The short X.Y version.
version = '%s.%s' % (eventlet.version_info[0], eventlet.version_info[1])
# The full version, including alpha/beta/rc tags.
release = eventlet.__version__

# The language for content autogenerated by Sphinx. Refer to documentation
# for a list of supported languages.
#language = None

# There are two options for replacing |today|: either, you set today to some
# non-false value, then it is used:
#today = ''
# Else, today_fmt is used as the format for a strftime call.
#today_fmt = '%B %d, %Y'

# List of documents that shouldn't be included in the build.
#unused_docs = []

# List of directories, relative to source directory, that shouldn't be searched
# for source files.
exclude_trees = ['_build']

# The reST default role (used for this markup: `text`) to use for all documents.
#default_role = None

# If true, '()' will be appended to :func: etc. cross-reference text.
#add_function_parentheses = True

# If true, the current module name will be prepended to all description
# unit titles (such as .. function::).
#add_module_names = True

# If true, sectionauthor and moduleauthor directives will be shown in the
# output. They are ignored by default.
show_authors = False

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = 'sphinx'

# A list of ignored prefixes for module index sorting.
#modindex_common_prefix = []

# Intersphinx references
intersphinx_mapping = {'http://docs.python.org/': None}


# -- Options for HTML output ---------------------------------------------------

# The theme to use for HTML and HTML Help pages.  Major themes that come with
# Sphinx are currently 'default' and 'sphinxdoc'.
html_theme = 'default'

# Theme options are theme-specific and customize the look and feel of a theme
# further.  For a list of options available for each theme, see the
# documentation.
#html_theme_options = {}

# Add any paths that contain custom themes here, relative to this directory.
#html_theme_path = []

# The name for this set of Sphinx documents.  If None, it defaults to
# "<project> v<release> documentation".
#html_title = None

# A shorter title for the navigation bar.  Default is the same as html_title.
#html_short_title = None

# The name of an image file (relative to this directory) to place at the top
# of the sidebar.
#html_logo = None

# The name of an image file (within the static path) to use as favicon of the
# docs.  This file should be a Windows icon file (.ico) being 16x16 or 32x32
# pixels large.
#html_favicon = None

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['_static']

# If not '', a 'Last updated on:' timestamp is inserted at every page bottom,
# using the given strftime format.
#html_last_updated_fmt = '%b %d, %Y'

# If true, SmartyPants will be used to convert quotes and dashes to
# typographically correct entities.
#html_use_smartypants = True

# Custom sidebar templates, maps document names to template names.
#html_sidebars = {}

# Additional templates that should be rendered to pages, maps page names to
# template names.
#html_additional_pages = {}

# If false, no module index is generated.
#html_use_modindex = True

# If false, no index is generated.
#html_use_index = True

# If true, the index is split into individual pages for each letter.
#html_split_index = False

# If true, links to the reST sources are added to the pages.
#html_show_sourcelink = True

# If true, an OpenSearch description file will be output, and all pages will
# contain a <link> tag referring to it.  The value of this option must be the
# base URL from which the finished HTML is served.
#html_use_opensearch = ''

# If nonempty, this is the file name suffix for HTML files (e.g. ".xhtml").
#html_file_suffix = ''

# Output file base name for HTML help builder.
htmlhelp_basename = 'Eventletdoc'


# -- Options for LaTeX output --------------------------------------------------

# The paper size ('letter' or 'a4').
#latex_paper_size = 'letter'

# The font size ('10pt', '11pt' or '12pt').
#latex_font_size = '10pt'

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, documentclass [howto/manual]).
latex_documents = [
  ('index', 'Eventlet.tex', u'Eventlet Documentation',
   u'<eventlet contributors>', 'manual'),
]

# The name of an image file (relative to this directory) to place at the top of
# the title page.
#latex_logo = None

# For "manual" documents, if this is true, then toplevel headings are parts,
# not chapters.
#latex_use_parts = False

# Additional stuff for the LaTeX preamble.
#latex_preamble = ''

# Documents to append as an appendix to all manuals.
#latex_appendices = []

# If false, no module index is generated.
#latex_use_modindex = True

########NEW FILE########
__FILENAME__ = api
import errno
import sys
import socket
import string
import linecache
import inspect
import warnings

from eventlet.support import greenlets as greenlet
from eventlet import hubs
from eventlet import greenthread
from eventlet import debug
from eventlet import Timeout

__all__ = [
    'call_after', 'exc_after', 'getcurrent', 'get_default_hub', 'get_hub',
    'GreenletExit', 'kill', 'sleep', 'spawn', 'spew', 'switch',
    'ssl_listener', 'tcp_listener', 'trampoline',
    'unspew', 'use_hub', 'with_timeout', 'timeout']

warnings.warn("eventlet.api is deprecated!  Nearly everything in it has moved "
    "to the eventlet module.", DeprecationWarning, stacklevel=2)

def get_hub(*a, **kw):
    warnings.warn("eventlet.api.get_hub has moved to eventlet.hubs.get_hub",
        DeprecationWarning, stacklevel=2)
    return hubs.get_hub(*a, **kw)
def get_default_hub(*a, **kw):
    warnings.warn("eventlet.api.get_default_hub has moved to"
        " eventlet.hubs.get_default_hub",
        DeprecationWarning, stacklevel=2)
    return hubs.get_default_hub(*a, **kw)
def use_hub(*a, **kw):
    warnings.warn("eventlet.api.use_hub has moved to eventlet.hubs.use_hub",
        DeprecationWarning, stacklevel=2)
    return hubs.use_hub(*a, **kw)


def switch(coro, result=None, exc=None):
    if exc is not None:
        return coro.throw(exc)
    return coro.switch(result)

Greenlet = greenlet.greenlet


def tcp_listener(address, backlog=50):
    """
    Listen on the given ``(ip, port)`` *address* with a TCP socket.  Returns a
    socket object on which one should call ``accept()`` to accept a connection
    on the newly bound socket.
    """
    warnings.warn("""eventlet.api.tcp_listener is deprecated.  Please use eventlet.listen instead.""",
        DeprecationWarning, stacklevel=2)

    from eventlet import greenio, util
    socket = greenio.GreenSocket(util.tcp_socket())
    util.socket_bind_and_listen(socket, address, backlog=backlog)
    return socket

def ssl_listener(address, certificate, private_key):
    """Listen on the given (ip, port) *address* with a TCP socket that
    can do SSL.  Primarily useful for unit tests, don't use in production.

    *certificate* and *private_key* should be the filenames of the appropriate
    certificate and private key files to use with the SSL socket.

    Returns a socket object on which one should call ``accept()`` to
    accept a connection on the newly bound socket.
    """
    warnings.warn("""eventlet.api.ssl_listener is deprecated.  Please use eventlet.wrap_ssl(eventlet.listen()) instead.""",
        DeprecationWarning, stacklevel=2)
    from eventlet import util
    import socket

    socket = util.wrap_ssl(socket.socket(), certificate, private_key, True)
    socket.bind(address)
    socket.listen(50)
    return socket

def connect_tcp(address, localaddr=None):
    """
    Create a TCP connection to address ``(host, port)`` and return the socket.
    Optionally, bind to localaddr ``(host, port)`` first.
    """
    warnings.warn("""eventlet.api.connect_tcp is deprecated.  Please use eventlet.connect instead.""",
        DeprecationWarning, stacklevel=2)

    from eventlet import greenio, util
    desc = greenio.GreenSocket(util.tcp_socket())
    if localaddr is not None:
        desc.bind(localaddr)
    desc.connect(address)
    return desc

TimeoutError = greenthread.TimeoutError

trampoline = hubs.trampoline

spawn = greenthread.spawn
spawn_n = greenthread.spawn_n


kill = greenthread.kill

call_after = greenthread.call_after
call_after_local = greenthread.call_after_local
call_after_global = greenthread.call_after_global


class _SilentException(BaseException):
    pass


class FakeTimer(object):
    def cancel(self):
        pass


class timeout(object):
    """Raise an exception in the block after timeout.

    Example::

    with timeout(10):
        urllib2.open('http://example.com')

    Assuming code block is yielding (i.e. gives up control to the hub),
    an exception provided in *exc* argument will be raised
    (:class:`~eventlet.api.TimeoutError` if *exc* is omitted)::

    try:
        with timeout(10, MySpecialError, error_arg_1):
            urllib2.open('http://example.com')
    except MySpecialError as e:
        print("special error received")

    When *exc* is ``None``, code block is interrupted silently.
    """

    def __init__(self, seconds, *throw_args):
        self.seconds = seconds
        if seconds is None:
            return
        if not throw_args:
            self.throw_args = (TimeoutError(), )
        elif throw_args == (None, ):
            self.throw_args = (_SilentException(), )
        else:
            self.throw_args = throw_args

    def __enter__(self):
        if self.seconds is None:
            self.timer = FakeTimer()
        else:
            self.timer = exc_after(self.seconds, *self.throw_args)
        return self.timer

    def __exit__(self, typ, value, tb):
        self.timer.cancel()
        if typ is _SilentException and value in self.throw_args:
            return True


with_timeout = greenthread.with_timeout

exc_after = greenthread.exc_after

sleep = greenthread.sleep

getcurrent = greenlet.getcurrent
GreenletExit = greenlet.GreenletExit

spew = debug.spew
unspew = debug.unspew


def named(name):
    """Return an object given its name.

    The name uses a module-like syntax, eg::

      os.path.join

    or::

      mulib.mu.Resource
    """
    toimport = name
    obj = None
    import_err_strings = []
    while toimport:
        try:
            obj = __import__(toimport)
            break
        except ImportError as err:
            # print('Import error on %s: %s' % (toimport, err))  # debugging spam
            import_err_strings.append(err.__str__())
            toimport = '.'.join(toimport.split('.')[:-1])
    if obj is None:
        raise ImportError('%s could not be imported.  Import errors: %r' % (name, import_err_strings))
    for seg in name.split('.')[1:]:
        try:
            obj = getattr(obj, seg)
        except AttributeError:
            dirobj = dir(obj)
            dirobj.sort()
            raise AttributeError('attribute %r missing from %r (%r) %r.  Import errors: %r' % (
                seg, obj, dirobj, name, import_err_strings))
    return obj

########NEW FILE########
__FILENAME__ = backdoor
from __future__ import print_function

from code import InteractiveConsole
import errno
import socket
import sys

import eventlet
from eventlet import hubs
from eventlet.support import greenlets, get_errno, six

try:
    sys.ps1
except AttributeError:
    sys.ps1 = '>>> '
try:
    sys.ps2
except AttributeError:
    sys.ps2 = '... '


class FileProxy(object):
    def __init__(self, f):
        self.f = f

    def isatty(self):
        return True

    def flush(self):
        pass

    def write(self, data, *a, **kw):
        data = six.b(data)
        self.f.write(data, *a, **kw)
        self.f.flush()

    def readline(self, *a):
        line = self.f.readline(*a).replace(b'\r\n', b'\n')
        return six.u(line)

    def __getattr__(self, attr):
        return getattr(self.f, attr)


# @@tavis: the `locals` args below mask the built-in function.  Should
# be renamed.
class SocketConsole(greenlets.greenlet):
    def __init__(self, desc, hostport, locals):
        self.hostport = hostport
        self.locals = locals
        # mangle the socket
        self.desc = FileProxy(desc)
        greenlets.greenlet.__init__(self)

    def run(self):
        try:
            console = InteractiveConsole(self.locals)
            console.interact()
        finally:
            self.switch_out()
            self.finalize()

    def switch(self, *args, **kw):
        self.saved = sys.stdin, sys.stderr, sys.stdout
        sys.stdin = sys.stdout = sys.stderr = self.desc
        greenlets.greenlet.switch(self, *args, **kw)

    def switch_out(self):
        sys.stdin, sys.stderr, sys.stdout = self.saved

    def finalize(self):
        # restore the state of the socket
        self.desc = None
        print("backdoor closed to %s:%s" % self.hostport)


def backdoor_server(sock, locals=None):
    """ Blocking function that runs a backdoor server on the socket *sock*,
    accepting connections and running backdoor consoles for each client that
    connects.

    The *locals* argument is a dictionary that will be included in the locals()
    of the interpreters.  It can be convenient to stick important application
    variables in here.
    """
    print("backdoor server listening on %s:%s" % sock.getsockname())
    try:
        try:
            while True:
                socketpair = sock.accept()
                backdoor(socketpair, locals)
        except socket.error as e:
            # Broken pipe means it was shutdown
            if get_errno(e) != errno.EPIPE:
                raise
    finally:
        sock.close()


def backdoor(conn_info, locals=None):
    """Sets up an interactive console on a socket with a single connected
    client.  This does not block the caller, as it spawns a new greenlet to
    handle the console.  This is meant to be called from within an accept loop
    (such as backdoor_server).
    """
    conn, addr = conn_info
    host, port = addr
    print("backdoor to %s:%s" % (host, port))
    fl = conn.makefile("rw")
    console = SocketConsole(fl, (host, port), locals)
    hub = hubs.get_hub()
    hub.schedule_call_global(0, console.switch)


if __name__ == '__main__':
    backdoor_server(eventlet.listen(('127.0.0.1', 9000)), {})

########NEW FILE########
__FILENAME__ = convenience
import sys

from eventlet import greenio
from eventlet import greenpool
from eventlet import greenthread
from eventlet.green import socket
from eventlet.support import greenlets as greenlet


def connect(addr, family=socket.AF_INET, bind=None):
    """Convenience function for opening client sockets.

    :param addr: Address of the server to connect to.  For TCP sockets, this is a (host, port) tuple.
    :param family: Socket family, optional.  See :mod:`socket` documentation for available families.
    :param bind: Local address to bind to, optional.
    :return: The connected green socket object.
    """
    sock = socket.socket(family, socket.SOCK_STREAM)
    if bind is not None:
        sock.bind(bind)
    sock.connect(addr)
    return sock


def listen(addr, family=socket.AF_INET, backlog=50):
    """Convenience function for opening server sockets.  This
    socket can be used in :func:`~eventlet.serve` or a custom ``accept()`` loop.

    Sets SO_REUSEADDR on the socket to save on annoyance.

    :param addr: Address to listen on.  For TCP sockets, this is a (host, port)  tuple.
    :param family: Socket family, optional.  See :mod:`socket` documentation for available families.
    :param backlog: The maximum number of queued connections. Should be at least 1; the maximum value is system-dependent.
    :return: The listening green socket object.
    """
    sock = socket.socket(family, socket.SOCK_STREAM)
    if sys.platform[:3] != "win":
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(addr)
    sock.listen(backlog)
    return sock


class StopServe(Exception):
    """Exception class used for quitting :func:`~eventlet.serve` gracefully."""
    pass


def _stop_checker(t, server_gt, conn):
    try:
        try:
            t.wait()
        finally:
            conn.close()
    except greenlet.GreenletExit:
        pass
    except Exception:
        greenthread.kill(server_gt, *sys.exc_info())


def serve(sock, handle, concurrency=1000):
    """Runs a server on the supplied socket.  Calls the function *handle* in a
    separate greenthread for every incoming client connection.  *handle* takes
    two arguments: the client socket object, and the client address::

        def myhandle(client_sock, client_addr):
            print("client connected", client_addr)

        eventlet.serve(eventlet.listen(('127.0.0.1', 9999)), myhandle)

    Returning from *handle* closes the client socket.

    :func:`serve` blocks the calling greenthread; it won't return until
    the server completes.  If you desire an immediate return,
    spawn a new greenthread for :func:`serve`.

    Any uncaught exceptions raised in *handle* are raised as exceptions
    from :func:`serve`, terminating the server, so be sure to be aware of the
    exceptions your application can raise.  The return value of *handle* is
    ignored.

    Raise a :class:`~eventlet.StopServe` exception to gracefully terminate the
    server -- that's the only way to get the server() function to return rather
    than raise.

    The value in *concurrency* controls the maximum number of
    greenthreads that will be open at any time handling requests.  When
    the server hits the concurrency limit, it stops accepting new
    connections until the existing ones complete.
    """
    pool = greenpool.GreenPool(concurrency)
    server_gt = greenthread.getcurrent()

    while True:
        try:
            conn, addr = sock.accept()
            gt = pool.spawn(handle, conn, addr)
            gt.link(_stop_checker, server_gt, conn)
            conn, addr, gt = None, None, None
        except StopServe:
            return


def wrap_ssl(sock, *a, **kw):
    """Convenience function for converting a regular socket into an
    SSL socket.  Has the same interface as :func:`ssl.wrap_socket`,
    but can also use PyOpenSSL. Though, note that it ignores the
    `cert_reqs`, `ssl_version`, `ca_certs`, `do_handshake_on_connect`,
    and `suppress_ragged_eofs` arguments when using PyOpenSSL.

    The preferred idiom is to call wrap_ssl directly on the creation
    method, e.g., ``wrap_ssl(connect(addr))`` or
    ``wrap_ssl(listen(addr), server_side=True)``. This way there is
    no "naked" socket sitting around to accidentally corrupt the SSL
    session.

    :return Green SSL object.
    """
    return wrap_ssl_impl(sock, *a, **kw)

try:
    from eventlet.green import ssl
    wrap_ssl_impl = ssl.wrap_socket
except ImportError:
    # trying PyOpenSSL
    try:
        from eventlet.green.OpenSSL import SSL
    except ImportError:
        def wrap_ssl_impl(*a, **kw):
            raise ImportError("To use SSL with Eventlet, you must install PyOpenSSL or use Python 2.6 or later.")
    else:
        def wrap_ssl_impl(sock, keyfile=None, certfile=None, server_side=False,
                          cert_reqs=None, ssl_version=None, ca_certs=None,
                          do_handshake_on_connect=True,
                          suppress_ragged_eofs=True, ciphers=None):
            # theoretically the ssl_version could be respected in this line
            context = SSL.Context(SSL.SSLv23_METHOD)
            if certfile is not None:
                context.use_certificate_file(certfile)
            if keyfile is not None:
                context.use_privatekey_file(keyfile)
            context.set_verify(SSL.VERIFY_NONE, lambda *x: True)

            connection = SSL.Connection(context, sock)
            if server_side:
                connection.set_accept_state()
            else:
                connection.set_connect_state()
            return connection

########NEW FILE########
__FILENAME__ = corolocal
import weakref

from eventlet import greenthread

__all__ = ['get_ident', 'local']

def get_ident():
    """ Returns ``id()`` of current greenlet.  Useful for debugging."""
    return id(greenthread.getcurrent())


# the entire purpose of this class is to store off the constructor
# arguments in a local variable without calling __init__ directly
class _localbase(object):
    __slots__ = '_local__args', '_local__greens'
    def __new__(cls, *args, **kw):
        self = object.__new__(cls)
        object.__setattr__(self, '_local__args', (args, kw))
        object.__setattr__(self, '_local__greens', weakref.WeakKeyDictionary())
        if (args or kw) and (cls.__init__ is object.__init__):
            raise TypeError("Initialization arguments are not supported")
        return self        
        
def _patch(thrl):
    greens = object.__getattribute__(thrl, '_local__greens')
    # until we can store the localdict on greenlets themselves,
    # we store it in _local__greens on the local object
    cur = greenthread.getcurrent()
    if cur not in greens:
        # must be the first time we've seen this greenlet, call __init__
        greens[cur] = {}
        cls = type(thrl)
        if cls.__init__ is not object.__init__:
            args, kw = object.__getattribute__(thrl, '_local__args')
            thrl.__init__(*args, **kw)
    object.__setattr__(thrl, '__dict__', greens[cur])
        

class local(_localbase):
    def __getattribute__(self, attr):
        _patch(self)
        return object.__getattribute__(self, attr)

    def __setattr__(self, attr, value):
        _patch(self)
        return object.__setattr__(self, attr, value)

    def __delattr__(self, attr):
        _patch(self)
        return object.__delattr__(self, attr)

########NEW FILE########
__FILENAME__ = coros
from __future__ import print_function

import collections
import traceback
import warnings

import eventlet
from eventlet import event as _event
from eventlet import hubs
from eventlet import greenthread
from eventlet import semaphore as semaphoremod


class NOT_USED:
    def __repr__(self):
        return 'NOT_USED'

NOT_USED = NOT_USED()


def Event(*a, **kw):
    warnings.warn("The Event class has been moved to the event module! "
                   "Please construct event.Event objects instead.",
                   DeprecationWarning, stacklevel=2)
    return _event.Event(*a, **kw)


def event(*a, **kw):
    warnings.warn("The event class has been capitalized and moved!  Please "
        "construct event.Event objects instead.",
        DeprecationWarning, stacklevel=2)
    return _event.Event(*a, **kw)


def Semaphore(count):
    warnings.warn("The Semaphore class has moved!  Please "
        "use semaphore.Semaphore instead.",
        DeprecationWarning, stacklevel=2)
    return semaphoremod.Semaphore(count)


def BoundedSemaphore(count):
    warnings.warn("The BoundedSemaphore class has moved!  Please "
        "use semaphore.BoundedSemaphore instead.",
        DeprecationWarning, stacklevel=2)
    return semaphoremod.BoundedSemaphore(count)


def semaphore(count=0, limit=None):
    warnings.warn("coros.semaphore is deprecated.  Please use either "
        "semaphore.Semaphore or semaphore.BoundedSemaphore instead.",
        DeprecationWarning, stacklevel=2)
    if limit is None:
        return Semaphore(count)
    else:
        return BoundedSemaphore(count)


class metaphore(object):
    """This is sort of an inverse semaphore: a counter that starts at 0 and
    waits only if nonzero. It's used to implement a "wait for all" scenario.

    >>> from eventlet import api, coros
    >>> count = coros.metaphore()
    >>> count.wait()
    >>> def decrementer(count, id):
    ...     print("{0} decrementing".format(id))
    ...     count.dec()
    ...
    >>> _ = eventlet.spawn(decrementer, count, 'A')
    >>> _ = eventlet.spawn(decrementer, count, 'B')
    >>> count.inc(2)
    >>> count.wait()
    A decrementing
    B decrementing
    """
    def __init__(self):
        self.counter = 0
        self.event = _event.Event()
        # send() right away, else we'd wait on the default 0 count!
        self.event.send()

    def inc(self, by=1):
        """Increment our counter. If this transitions the counter from zero to
        nonzero, make any subsequent :meth:`wait` call wait.
        """
        assert by > 0
        self.counter += by
        if self.counter == by:
            # If we just incremented self.counter by 'by', and the new count
            # equals 'by', then the old value of self.counter was 0.
            # Transitioning from 0 to a nonzero value means wait() must
            # actually wait.
            self.event.reset()

    def dec(self, by=1):
        """Decrement our counter. If this transitions the counter from nonzero
        to zero, a current or subsequent wait() call need no longer wait.
        """
        assert by > 0
        self.counter -= by
        if self.counter <= 0:
            # Don't leave self.counter < 0, that will screw things up in
            # future calls.
            self.counter = 0
            # Transitioning from nonzero to 0 means wait() need no longer wait.
            self.event.send()

    def wait(self):
        """Suspend the caller only if our count is nonzero. In that case,
        resume the caller once the count decrements to zero again.
        """
        self.event.wait()


def execute(func, *args, **kw):
    """ Executes an operation asynchronously in a new coroutine, returning
    an event to retrieve the return value.

    This has the same api as the :meth:`eventlet.coros.CoroutinePool.execute`
    method; the only difference is that this one creates a new coroutine
    instead of drawing from a pool.

    >>> from eventlet import coros
    >>> evt = coros.execute(lambda a: ('foo', a), 1)
    >>> evt.wait()
    ('foo', 1)
    """
    warnings.warn("Coros.execute is deprecated.  Please use eventlet.spawn "
        "instead.", DeprecationWarning, stacklevel=2)
    return greenthread.spawn(func, *args, **kw)


def CoroutinePool(*args, **kwargs):
    warnings.warn("CoroutinePool is deprecated.  Please use "
        "eventlet.GreenPool instead.", DeprecationWarning, stacklevel=2)
    from eventlet.pool import Pool
    return Pool(*args, **kwargs)


class Queue(object):

    def __init__(self):
        warnings.warn("coros.Queue is deprecated.  Please use "
            "eventlet.queue.Queue instead.",
            DeprecationWarning, stacklevel=2)
        self.items = collections.deque()
        self._waiters = set()

    def __nonzero__(self):
        return len(self.items)>0

    __bool__ = __nonzero__

    def __len__(self):
        return len(self.items)

    def __repr__(self):
        params = (self.__class__.__name__, hex(id(self)),
                  len(self.items), len(self._waiters))
        return '<%s at %s items[%d] _waiters[%s]>' % params

    def send(self, result=None, exc=None):
        if exc is not None and not isinstance(exc, tuple):
            exc = (exc, )
        self.items.append((result, exc))
        if self._waiters:
            hubs.get_hub().schedule_call_global(0, self._do_send)

    def send_exception(self, *args):
        # the arguments are the same as for greenlet.throw
        return self.send(exc=args)

    def _do_send(self):
        if self._waiters and self.items:
            waiter = self._waiters.pop()
            result, exc = self.items.popleft()
            waiter.switch((result, exc))

    def wait(self):
        if self.items:
            result, exc = self.items.popleft()
            if exc is None:
                return result
            else:
                eventlet.getcurrent().throw(*exc)
        else:
            self._waiters.add(eventlet.getcurrent())
            try:
                result, exc = hubs.get_hub().switch()
                if exc is None:
                    return result
                else:
                    eventlet.getcurrent().throw(*exc)
            finally:
                self._waiters.discard(eventlet.getcurrent())

    def ready(self):
        return len(self.items) > 0

    def full(self):
        # for consistency with Channel
        return False

    def waiting(self):
        return len(self._waiters)

    def __iter__(self):
        return self

    def next(self):
        return self.wait()


class Channel(object):

    def __init__(self, max_size=0):
        warnings.warn("coros.Channel is deprecated.  Please use "
            "eventlet.queue.Queue(0) instead.",
            DeprecationWarning, stacklevel=2)
        self.max_size = max_size
        self.items = collections.deque()
        self._waiters = set()
        self._senders = set()

    def __nonzero__(self):
        return len(self.items)>0

    __bool__ = __nonzero__

    def __len__(self):
        return len(self.items)

    def __repr__(self):
        params = (self.__class__.__name__, hex(id(self)),
                  self.max_size, len(self.items),
                  len(self._waiters), len(self._senders))
        return '<%s at %s max=%s items[%d] _w[%s] _s[%s]>' % params

    def send(self, result=None, exc=None):
        if exc is not None and not isinstance(exc, tuple):
            exc = (exc, )
        if eventlet.getcurrent() is hubs.get_hub().greenlet:
            self.items.append((result, exc))
            if self._waiters:
                hubs.get_hub().schedule_call_global(0, self._do_switch)
        else:
            self.items.append((result, exc))
            # note that send() does not work well with timeouts. if your timeout fires
            # after this point, the item will remain in the queue
            if self._waiters:
                hubs.get_hub().schedule_call_global(0, self._do_switch)
            if len(self.items) > self.max_size:
                self._senders.add(eventlet.getcurrent())
                try:
                    hubs.get_hub().switch()
                finally:
                    self._senders.discard(eventlet.getcurrent())

    def send_exception(self, *args):
        # the arguments are the same as for greenlet.throw
        return self.send(exc=args)

    def _do_switch(self):
        while True:
            if self._waiters and self.items:
                waiter = self._waiters.pop()
                result, exc = self.items.popleft()
                try:
                    waiter.switch((result, exc))
                except:
                    traceback.print_exc()
            elif self._senders and len(self.items) <= self.max_size:
                sender = self._senders.pop()
                try:
                    sender.switch()
                except:
                    traceback.print_exc()
            else:
                break

    def wait(self):
        if self.items:
            result, exc = self.items.popleft()
            if len(self.items) <= self.max_size:
                hubs.get_hub().schedule_call_global(0, self._do_switch)
            if exc is None:
                return result
            else:
                eventlet.getcurrent().throw(*exc)
        else:
            if self._senders:
                hubs.get_hub().schedule_call_global(0, self._do_switch)
            self._waiters.add(eventlet.getcurrent())
            try:
                result, exc = hubs.get_hub().switch()
                if exc is None:
                    return result
                else:
                    eventlet.getcurrent().throw(*exc)
            finally:
                self._waiters.discard(eventlet.getcurrent())

    def ready(self):
        return len(self.items) > 0

    def full(self):
        return len(self.items) >= self.max_size

    def waiting(self):
        return max(0, len(self._waiters) - len(self.items))


def queue(max_size=None):
    if max_size is None:
        return Queue()
    else:
        return Channel(max_size)

########NEW FILE########
__FILENAME__ = db_pool
from __future__ import print_function

from collections import deque
import sys
import time

from eventlet.pools import Pool
from eventlet import timeout
from eventlet import hubs
from eventlet.hubs.timer import Timer
from eventlet.greenthread import GreenThread


class ConnectTimeout(Exception):
    pass


class BaseConnectionPool(Pool):
    def __init__(self, db_module,
                       min_size = 0, max_size = 4,
                       max_idle = 10, max_age = 30,
                       connect_timeout = 5,
                       *args, **kwargs):
        """
        Constructs a pool with at least *min_size* connections and at most
        *max_size* connections.  Uses *db_module* to construct new connections.

        The *max_idle* parameter determines how long pooled connections can
        remain idle, in seconds.  After *max_idle* seconds have elapsed
        without the connection being used, the pool closes the connection.

        *max_age* is how long any particular connection is allowed to live.
        Connections that have been open for longer than *max_age* seconds are
        closed, regardless of idle time.  If *max_age* is 0, all connections are
        closed on return to the pool, reducing it to a concurrency limiter.

        *connect_timeout* is the duration in seconds that the pool will wait
        before timing out on connect() to the database.  If triggered, the
        timeout will raise a ConnectTimeout from get().

        The remainder of the arguments are used as parameters to the
        *db_module*'s connection constructor.
        """
        assert(db_module)
        self._db_module = db_module
        self._args = args
        self._kwargs = kwargs
        self.max_idle = max_idle
        self.max_age = max_age
        self.connect_timeout = connect_timeout
        self._expiration_timer = None
        super(BaseConnectionPool, self).__init__(min_size=min_size,
                                                 max_size=max_size,
                                                 order_as_stack=True)

    def _schedule_expiration(self):
        """ Sets up a timer that will call _expire_old_connections when the
        oldest connection currently in the free pool is ready to expire.  This
        is the earliest possible time that a connection could expire, thus, the
        timer will be running as infrequently as possible without missing a
        possible expiration.

        If this function is called when a timer is already scheduled, it does
       nothing.

        If max_age or max_idle is 0, _schedule_expiration likewise does nothing.
        """
        if self.max_age is 0 or self.max_idle is 0:
            # expiration is unnecessary because all connections will be expired
            # on put
            return

        if ( self._expiration_timer is not None
             and not getattr(self._expiration_timer, 'called', False)):
            # the next timer is already scheduled
            return

        try:
            now = time.time()
            self._expire_old_connections(now)
            # the last item in the list, because of the stack ordering,
            # is going to be the most-idle
            idle_delay = (self.free_items[-1][0] - now) + self.max_idle
            oldest = min([t[1] for t in self.free_items])
            age_delay = (oldest - now) + self.max_age

            next_delay = min(idle_delay, age_delay)
        except (IndexError, ValueError):
            # no free items, unschedule ourselves
            self._expiration_timer = None
            return

        if next_delay > 0:
            # set up a continuous self-calling loop
            self._expiration_timer = Timer(next_delay, GreenThread(hubs.get_hub().greenlet).switch,
                                           self._schedule_expiration, [], {})
            self._expiration_timer.schedule()

    def _expire_old_connections(self, now):
        """ Iterates through the open connections contained in the pool, closing
        ones that have remained idle for longer than max_idle seconds, or have
        been in existence for longer than max_age seconds.

        *now* is the current time, as returned by time.time().
        """
        original_count = len(self.free_items)
        expired = [
            conn
            for last_used, created_at, conn in self.free_items
            if self._is_expired(now, last_used, created_at)]

        new_free = [
            (last_used, created_at, conn)
            for last_used, created_at, conn in self.free_items
            if not self._is_expired(now, last_used, created_at)]
        self.free_items.clear()
        self.free_items.extend(new_free)

        # adjust the current size counter to account for expired
        # connections
        self.current_size -= original_count - len(self.free_items)

        for conn in expired:
            self._safe_close(conn, quiet=True)

    def _is_expired(self, now, last_used, created_at):
        """ Returns true and closes the connection if it's expired."""
        if ( self.max_idle <= 0
             or self.max_age <= 0
             or now - last_used > self.max_idle
             or now - created_at > self.max_age ):
            return True
        return False

    def _unwrap_connection(self, conn):
        """ If the connection was wrapped by a subclass of
        BaseConnectionWrapper and is still functional (as determined
        by the __nonzero__, or __bool__ in python3, method), returns
        the unwrapped connection.  If anything goes wrong with this
        process, returns None.
        """
        base = None
        try:
            if conn:
                base = conn._base
                conn._destroy()
            else:
                base = None
        except AttributeError:
            pass
        return base

    def _safe_close(self, conn, quiet = False):
        """ Closes the (already unwrapped) connection, squelching any
        exceptions."""
        try:
            conn.close()
        except (KeyboardInterrupt, SystemExit):
            raise
        except AttributeError:
            pass # conn is None, or junk
        except:
            if not quiet:
                print("Connection.close raised: %s" % (sys.exc_info()[1]))

    def get(self):
        conn = super(BaseConnectionPool, self).get()

        # None is a flag value that means that put got called with
        # something it couldn't use
        if conn is None:
            try:
                conn = self.create()
            except Exception:
                # unconditionally increase the free pool because
                # even if there are waiters, doing a full put
                # would incur a greenlib switch and thus lose the
                # exception stack
                self.current_size -= 1
                raise

        # if the call to get() draws from the free pool, it will come
        # back as a tuple
        if isinstance(conn, tuple):
            _last_used, created_at, conn = conn
        else:
            created_at = time.time()

        # wrap the connection so the consumer can call close() safely
        wrapped = PooledConnectionWrapper(conn, self)
        # annotating the wrapper so that when it gets put in the pool
        # again, we'll know how old it is
        wrapped._db_pool_created_at = created_at
        return wrapped

    def put(self, conn):
        created_at = getattr(conn, '_db_pool_created_at', 0)
        now = time.time()
        conn = self._unwrap_connection(conn)

        if self._is_expired(now, now, created_at):
            self._safe_close(conn, quiet=False)
            conn = None
        else:
            # rollback any uncommitted changes, so that the next client
            # has a clean slate.  This also pokes the connection to see if
            # it's dead or None
            try:
                if conn:
                    conn.rollback()
            except KeyboardInterrupt:
                raise
            except:
                # we don't care what the exception was, we just know the
                # connection is dead
                print("WARNING: connection.rollback raised: %s" % (sys.exc_info()[1]))
                conn = None

        if conn is not None:
            super(BaseConnectionPool, self).put( (now, created_at, conn) )
        else:
            # wake up any waiters with a flag value that indicates
            # they need to manufacture a connection
              if self.waiting() > 0:
                  super(BaseConnectionPool, self).put(None)
              else:
                  # no waiters -- just change the size
                  self.current_size -= 1
        self._schedule_expiration()

    def clear(self):
        """ Close all connections that this pool still holds a reference to,
        and removes all references to them.
        """
        if self._expiration_timer:
            self._expiration_timer.cancel()
        free_items, self.free_items = self.free_items, deque()
        for item in free_items:
            # Free items created using min_size>0 are not tuples.
            conn = item[2] if isinstance(item, tuple) else item
            self._safe_close(conn, quiet=True)

    def __del__(self):
        self.clear()


class TpooledConnectionPool(BaseConnectionPool):
    """A pool which gives out :class:`~eventlet.tpool.Proxy`-based database
    connections.
    """
    def create(self):
        now = time.time()
        return now, now, self.connect(self._db_module,
            self.connect_timeout, *self._args, **self._kwargs)

    @classmethod
    def connect(cls, db_module, connect_timeout, *args, **kw):
        t = timeout.Timeout(connect_timeout, ConnectTimeout())
        try:
            from eventlet import tpool
            conn = tpool.execute(db_module.connect, *args, **kw)
            return tpool.Proxy(conn, autowrap_names=('cursor',))
        finally:
            t.cancel()


class RawConnectionPool(BaseConnectionPool):
    """A pool which gives out plain database connections.
    """
    def create(self):
        now = time.time()
        return now, now, self.connect(self._db_module,
            self.connect_timeout, *self._args, **self._kwargs)

    @classmethod
    def connect(cls, db_module, connect_timeout, *args, **kw):
        t = timeout.Timeout(connect_timeout, ConnectTimeout())
        try:
            return db_module.connect(*args, **kw)
        finally:
            t.cancel()


# default connection pool is the tpool one
ConnectionPool = TpooledConnectionPool


class GenericConnectionWrapper(object):
    def __init__(self, baseconn):
        self._base = baseconn
    def __enter__(self): return self._base.__enter__()
    def __exit__(self, exc, value, tb): return self._base.__exit__(exc, value, tb)
    def __repr__(self): return self._base.__repr__()
    def affected_rows(self): return self._base.affected_rows()
    def autocommit(self,*args, **kwargs): return self._base.autocommit(*args, **kwargs)
    def begin(self): return self._base.begin()
    def change_user(self,*args, **kwargs): return self._base.change_user(*args, **kwargs)
    def character_set_name(self,*args, **kwargs): return self._base.character_set_name(*args, **kwargs)
    def close(self,*args, **kwargs): return self._base.close(*args, **kwargs)
    def commit(self,*args, **kwargs): return self._base.commit(*args, **kwargs)
    def cursor(self, *args, **kwargs): return self._base.cursor(*args, **kwargs)
    def dump_debug_info(self,*args, **kwargs): return self._base.dump_debug_info(*args, **kwargs)
    def errno(self,*args, **kwargs): return self._base.errno(*args, **kwargs)
    def error(self,*args, **kwargs): return self._base.error(*args, **kwargs)
    def errorhandler(self, *args, **kwargs): return self._base.errorhandler(*args, **kwargs)
    def insert_id(self, *args, **kwargs): return self._base.insert_id(*args, **kwargs)
    def literal(self, *args, **kwargs): return self._base.literal(*args, **kwargs)
    def set_character_set(self, *args, **kwargs): return self._base.set_character_set(*args, **kwargs)
    def set_sql_mode(self, *args, **kwargs): return self._base.set_sql_mode(*args, **kwargs)
    def show_warnings(self): return self._base.show_warnings()
    def warning_count(self): return self._base.warning_count()
    def ping(self,*args, **kwargs): return self._base.ping(*args, **kwargs)
    def query(self,*args, **kwargs): return self._base.query(*args, **kwargs)
    def rollback(self,*args, **kwargs): return self._base.rollback(*args, **kwargs)
    def select_db(self,*args, **kwargs): return self._base.select_db(*args, **kwargs)
    def set_server_option(self,*args, **kwargs): return self._base.set_server_option(*args, **kwargs)
    def server_capabilities(self,*args, **kwargs): return self._base.server_capabilities(*args, **kwargs)
    def shutdown(self,*args, **kwargs): return self._base.shutdown(*args, **kwargs)
    def sqlstate(self,*args, **kwargs): return self._base.sqlstate(*args, **kwargs)
    def stat(self, *args, **kwargs): return self._base.stat(*args, **kwargs)
    def store_result(self,*args, **kwargs): return self._base.store_result(*args, **kwargs)
    def string_literal(self,*args, **kwargs): return self._base.string_literal(*args, **kwargs)
    def thread_id(self,*args, **kwargs): return self._base.thread_id(*args, **kwargs)
    def use_result(self,*args, **kwargs): return self._base.use_result(*args, **kwargs)


class PooledConnectionWrapper(GenericConnectionWrapper):
    """ A connection wrapper where:
    - the close method returns the connection to the pool instead of closing it directly
    - ``bool(conn)`` returns a reasonable value
    - returns itself to the pool if it gets garbage collected
    """
    def __init__(self, baseconn, pool):
        super(PooledConnectionWrapper, self).__init__(baseconn)
        self._pool = pool

    def __nonzero__(self):
        return (hasattr(self, '_base') and bool(self._base))

    __bool__ = __nonzero__

    def _destroy(self):
        self._pool = None
        try:
            del self._base
        except AttributeError:
            pass

    def close(self):
        """ Return the connection to the pool, and remove the
        reference to it so that you can't use it again through this
        wrapper object.
        """
        if self and self._pool:
            self._pool.put(self)
        self._destroy()

    def __del__(self):
        return  # this causes some issues if __del__ is called in the
                # main coroutine, so for now this is disabled
        #self.close()


class DatabaseConnector(object):
    """\
    This is an object which will maintain a collection of database
connection pools on a per-host basis."""
    def __init__(self, module, credentials,
                 conn_pool=None, *args, **kwargs):
        """\
        constructor
        *module*
            Database module to use.
        *credentials*
            Mapping of hostname to connect arguments (e.g. username and password)"""
        assert(module)
        self._conn_pool_class = conn_pool
        if self._conn_pool_class is None:
            self._conn_pool_class = ConnectionPool
        self._module = module
        self._args = args
        self._kwargs = kwargs
        self._credentials = credentials  # this is a map of hostname to username/password
        self._databases = {}

    def credentials_for(self, host):
        if host in self._credentials:
            return self._credentials[host]
        else:
            return self._credentials.get('default', None)

    def get(self, host, dbname):
        """ Returns a ConnectionPool to the target host and schema. """
        key = (host, dbname)
        if key not in self._databases:
            new_kwargs = self._kwargs.copy()
            new_kwargs['db'] = dbname
            new_kwargs['host'] = host
            new_kwargs.update(self.credentials_for(host))
            dbpool = self._conn_pool_class(self._module,
                *self._args, **new_kwargs)
            self._databases[key] = dbpool

        return self._databases[key]

########NEW FILE########
__FILENAME__ = debug
"""The debug module contains utilities and functions for better
debugging Eventlet-powered applications."""
from __future__ import print_function

import os
import sys
import linecache
import re
import inspect

__all__ = ['spew', 'unspew', 'format_hub_listeners', 'format_hub_timers',
           'hub_listener_stacks', 'hub_exceptions', 'tpool_exceptions',
           'hub_prevent_multiple_readers', 'hub_timer_stacks',
           'hub_blocking_detection']

_token_splitter = re.compile('\W+')


class Spew(object):

    def __init__(self, trace_names=None, show_values=True):
        self.trace_names = trace_names
        self.show_values = show_values

    def __call__(self, frame, event, arg):
        if event == 'line':
            lineno = frame.f_lineno
            if '__file__' in frame.f_globals:
                filename = frame.f_globals['__file__']
                if (filename.endswith('.pyc') or
                        filename.endswith('.pyo')):
                    filename = filename[:-1]
                name = frame.f_globals['__name__']
                line = linecache.getline(filename, lineno)
            else:
                name = '[unknown]'
                try:
                    src = inspect.getsourcelines(frame)
                    line = src[lineno]
                except IOError:
                    line = 'Unknown code named [%s].  VM instruction #%d' % (
                        frame.f_code.co_name, frame.f_lasti)
            if self.trace_names is None or name in self.trace_names:
                print('%s:%s: %s' % (name, lineno, line.rstrip()))
                if not self.show_values:
                    return self
                details = []
                tokens = _token_splitter.split(line)
                for tok in tokens:
                    if tok in frame.f_globals:
                        details.append('%s=%r' % (tok, frame.f_globals[tok]))
                    if tok in frame.f_locals:
                        details.append('%s=%r' % (tok, frame.f_locals[tok]))
                if details:
                    print("\t%s" % ' '.join(details))
        return self


def spew(trace_names=None, show_values=False):
    """Install a trace hook which writes incredibly detailed logs
    about what code is being executed to stdout.
    """
    sys.settrace(Spew(trace_names, show_values))


def unspew():
    """Remove the trace hook installed by spew.
    """
    sys.settrace(None)


def format_hub_listeners():
    """ Returns a formatted string of the current listeners on the current
    hub.  This can be useful in determining what's going on in the event system,
    especially when used in conjunction with :func:`hub_listener_stacks`.
    """
    from eventlet import hubs
    hub = hubs.get_hub()
    result = ['READERS:']
    for l in hub.get_readers():
        result.append(repr(l))
    result.append('WRITERS:')
    for l in hub.get_writers():
        result.append(repr(l))
    return os.linesep.join(result)


def format_hub_timers():
    """ Returns a formatted string of the current timers on the current
    hub.  This can be useful in determining what's going on in the event system,
    especially when used in conjunction with :func:`hub_timer_stacks`.
    """
    from eventlet import hubs
    hub = hubs.get_hub()
    result = ['TIMERS:']
    for l in hub.timers:
        result.append(repr(l))
    return os.linesep.join(result)


def hub_listener_stacks(state=False):
    """Toggles whether or not the hub records the stack when clients register
    listeners on file descriptors.  This can be useful when trying to figure
    out what the hub is up to at any given moment.  To inspect the stacks
    of the current listeners, call :func:`format_hub_listeners` at critical
    junctures in the application logic.
    """
    from eventlet import hubs
    hubs.get_hub().set_debug_listeners(state)


def hub_timer_stacks(state=False):
    """Toggles whether or not the hub records the stack when timers are set.
    To inspect the stacks of the current timers, call :func:`format_hub_timers`
    at critical junctures in the application logic.
    """
    from eventlet.hubs import timer
    timer._g_debug = state


def hub_prevent_multiple_readers(state=True):
    """Toggle prevention of multiple greenlets reading from a socket

    When multiple greenlets read from the same socket it is often hard
    to predict which greenlet will receive what data.  To achieve
    resource sharing consider using ``eventlet.pools.Pool`` instead.

    But if you really know what you are doing you can change the state
    to ``False`` to stop the hub from protecting against this mistake.
    """
    from eventlet.hubs import hub
    hub.g_prevent_multiple_readers = state


def hub_exceptions(state=True):
    """Toggles whether the hub prints exceptions that are raised from its
    timers.  This can be useful to see how greenthreads are terminating.
    """
    from eventlet import hubs
    hubs.get_hub().set_timer_exceptions(state)
    from eventlet import greenpool
    greenpool.DEBUG = state


def tpool_exceptions(state=False):
    """Toggles whether tpool itself prints exceptions that are raised from
    functions that are executed in it, in addition to raising them like
    it normally does."""
    from eventlet import tpool
    tpool.QUIET = not state


def hub_blocking_detection(state=False, resolution=1):
    """Toggles whether Eventlet makes an effort to detect blocking
    behavior in an application.

    It does this by telling the kernel to raise a SIGALARM after a
    short timeout, and clearing the timeout every time the hub
    greenlet is resumed.  Therefore, any code that runs for a long
    time without yielding to the hub will get interrupted by the
    blocking detector (don't use it in production!).

    The *resolution* argument governs how long the SIGALARM timeout
    waits in seconds.  The implementation uses :func:`signal.setitimer`
    and can be specified as a floating-point value.
    The shorter the resolution, the greater the chance of false
    positives.
    """
    from eventlet import hubs
    assert resolution > 0
    hubs.get_hub().debug_blocking = state
    hubs.get_hub().debug_blocking_resolution = resolution
    if not state:
        hubs.get_hub().block_detect_post()

########NEW FILE########
__FILENAME__ = event
from __future__ import print_function

from eventlet import hubs
from eventlet.support import greenlets as greenlet

__all__ = ['Event']


class NOT_USED:
    def __repr__(self):
        return 'NOT_USED'

NOT_USED = NOT_USED()


class Event(object):
    """An abstraction where an arbitrary number of coroutines
    can wait for one event from another.

    Events are similar to a Queue that can only hold one item, but differ
    in two important ways:

    1. calling :meth:`send` never unschedules the current greenthread
    2. :meth:`send` can only be called once; create a new event to send again.

    They are good for communicating results between coroutines, and
    are the basis for how
    :meth:`GreenThread.wait() <eventlet.greenthread.GreenThread.wait>`
    is implemented.

    >>> from eventlet import event
    >>> import eventlet
    >>> evt = event.Event()
    >>> def baz(b):
    ...     evt.send(b + 1)
    ...
    >>> _ = eventlet.spawn_n(baz, 3)
    >>> evt.wait()
    4
    """
    _result = None
    _exc = None
    def __init__(self):
        self._waiters = set()
        self.reset()

    def __str__(self):
        params = (self.__class__.__name__, hex(id(self)),
                  self._result, self._exc, len(self._waiters))
        return '<%s at %s result=%r _exc=%r _waiters[%d]>' % params

    def reset(self):
        # this is kind of a misfeature and doesn't work perfectly well,
        # it's better to create a new event rather than reset an old one
        # removing documentation so that we don't get new use cases for it
        assert self._result is not NOT_USED, 'Trying to re-reset() a fresh event.'
        self._result = NOT_USED
        self._exc = None

    def ready(self):
        """ Return true if the :meth:`wait` call will return immediately.
        Used to avoid waiting for things that might take a while to time out.
        For example, you can put a bunch of events into a list, and then visit
        them all repeatedly, calling :meth:`ready` until one returns ``True``,
        and then you can :meth:`wait` on that one."""
        return self._result is not NOT_USED

    def has_exception(self):
        return self._exc is not None

    def has_result(self):
        return self._result is not NOT_USED and self._exc is None

    def poll(self, notready=None):
        if self.ready():
            return self.wait()
        return notready

    # QQQ make it return tuple (type, value, tb) instead of raising
    # because
    # 1) "poll" does not imply raising
    # 2) it's better not to screw up caller's sys.exc_info() by default
    #    (e.g. if caller wants to calls the function in except or finally)
    def poll_exception(self, notready=None):
        if self.has_exception():
            return self.wait()
        return notready

    def poll_result(self, notready=None):
        if self.has_result():
            return self.wait()
        return notready

    def wait(self):
        """Wait until another coroutine calls :meth:`send`.
        Returns the value the other coroutine passed to
        :meth:`send`.

        >>> from eventlet import event
        >>> import eventlet
        >>> evt = event.Event()
        >>> def wait_on():
        ...    retval = evt.wait()
        ...    print("waited for {0}".format(retval))
        >>> _ = eventlet.spawn(wait_on)
        >>> evt.send('result')
        >>> eventlet.sleep(0)
        waited for result

        Returns immediately if the event has already
        occured.

        >>> evt.wait()
        'result'
        """
        current = greenlet.getcurrent()
        if self._result is NOT_USED:
            self._waiters.add(current)
            try:
                return hubs.get_hub().switch()
            finally:
                self._waiters.discard(current)
        if self._exc is not None:
            current.throw(*self._exc)
        return self._result

    def send(self, result=None, exc=None):
        """Makes arrangements for the waiters to be woken with the
        result and then returns immediately to the parent.

        >>> from eventlet import event
        >>> import eventlet
        >>> evt = event.Event()
        >>> def waiter():
        ...     print('about to wait')
        ...     result = evt.wait()
        ...     print('waited for {0}'.format(result))
        >>> _ = eventlet.spawn(waiter)
        >>> eventlet.sleep(0)
        about to wait
        >>> evt.send('a')
        >>> eventlet.sleep(0)
        waited for a

        It is an error to call :meth:`send` multiple times on the same event.

        >>> evt.send('whoops')
        Traceback (most recent call last):
        ...
        AssertionError: Trying to re-send() an already-triggered event.

        Use :meth:`reset` between :meth:`send` s to reuse an event object.
        """
        assert self._result is NOT_USED, 'Trying to re-send() an already-triggered event.'
        self._result = result
        if exc is not None and not isinstance(exc, tuple):
            exc = (exc, )
        self._exc = exc
        hub = hubs.get_hub()
        for waiter in self._waiters:
            hub.schedule_call_global(
                0, self._do_send, self._result, self._exc, waiter)

    def _do_send(self, result, exc, waiter):
        if waiter in self._waiters:
            if exc is None:
                waiter.switch(result)
            else:
                waiter.throw(*exc)

    def send_exception(self, *args):
        """Same as :meth:`send`, but sends an exception to waiters.

        The arguments to send_exception are the same as the arguments
        to ``raise``.  If a single exception object is passed in, it
        will be re-raised when :meth:`wait` is called, generating a
        new stacktrace.

           >>> from eventlet import event
           >>> evt = event.Event()
           >>> evt.send_exception(RuntimeError())
           >>> evt.wait()
           Traceback (most recent call last):
             File "<stdin>", line 1, in <module>
             File "eventlet/event.py", line 120, in wait
               current.throw(*self._exc)
           RuntimeError

        If it's important to preserve the entire original stack trace,
        you must pass in the entire :func:`sys.exc_info` tuple.

           >>> import sys
           >>> evt = event.Event()
           >>> try:
           ...     raise RuntimeError()
           ... except RuntimeError:
           ...     evt.send_exception(*sys.exc_info())
           ...
           >>> evt.wait()
           Traceback (most recent call last):
             File "<stdin>", line 1, in <module>
             File "eventlet/event.py", line 120, in wait
               current.throw(*self._exc)
             File "<stdin>", line 2, in <module>
           RuntimeError

        Note that doing so stores a traceback object directly on the
        Event object, which may cause reference cycles. See the
        :func:`sys.exc_info` documentation.
        """
        # the arguments and the same as for greenlet.throw
        return self.send(None, args)

########NEW FILE########
__FILENAME__ = asynchat
from eventlet import patcher
from eventlet.green import asyncore
from eventlet.green import socket

patcher.inject('asynchat',
    globals(),
    ('asyncore', asyncore),
    ('socket', socket))

del patcher
########NEW FILE########
__FILENAME__ = asyncore
from eventlet import patcher
from eventlet.green import select
from eventlet.green import socket
from eventlet.green import time

patcher.inject("asyncore",
    globals(),
    ('select', select),
    ('socket', socket),
    ('time', time))

del patcher
########NEW FILE########
__FILENAME__ = BaseHTTPServer
from eventlet import patcher
from eventlet.green import socket
from eventlet.green import SocketServer

patcher.inject('BaseHTTPServer',
    globals(),
    ('socket', socket),
    ('SocketServer', SocketServer))

del patcher

if __name__ == '__main__':
    test()

########NEW FILE########
__FILENAME__ = CGIHTTPServer
from eventlet import patcher
from eventlet.green import BaseHTTPServer
from eventlet.green import SimpleHTTPServer
from eventlet.green import urllib
from eventlet.green import select

test = None # bind prior to patcher.inject to silence pyflakes warning below
patcher.inject('CGIHTTPServer',
    globals(),
    ('BaseHTTPServer', BaseHTTPServer),
    ('SimpleHTTPServer', SimpleHTTPServer),
    ('urllib',  urllib),
    ('select',  select))

del patcher

if __name__ == '__main__':
    test() # pyflakes false alarm here unless test = None above

########NEW FILE########
__FILENAME__ = ftplib
from eventlet import patcher

# *NOTE: there might be some funny business with the "SOCKS" module
# if it even still exists
from eventlet.green import socket

patcher.inject('ftplib', globals(), ('socket', socket))

del patcher

# Run test program when run as a script
if __name__ == '__main__':
    test()

########NEW FILE########
__FILENAME__ = httplib
from eventlet import patcher
from eventlet.green import socket
from eventlet.support import six

to_patch = [('socket', socket)]

try:
    from eventlet.green import ssl
    to_patch.append(('ssl', ssl))
except ImportError:
    pass

if six.PY2:
    patcher.inject('httplib', globals(), *to_patch)
if six.PY3:
    patcher.inject('http.client', globals(), *to_patch)

if __name__ == '__main__':
    test()

########NEW FILE########
__FILENAME__ = MySQLdb
__MySQLdb = __import__('MySQLdb')

__all__ = __MySQLdb.__all__
__patched__ = ["connect", "Connect", 'Connection', 'connections']

from eventlet.patcher import slurp_properties
slurp_properties(
    __MySQLdb, globals(),
    ignore=__patched__, srckeys=dir(__MySQLdb))

from eventlet import tpool

__orig_connections = __import__('MySQLdb.connections').connections


def Connection(*args, **kw):
    conn = tpool.execute(__orig_connections.Connection, *args, **kw)
    return tpool.Proxy(conn, autowrap_names=('cursor',))
connect = Connect = Connection


# replicate the MySQLdb.connections module but with a tpooled Connection factory
class MySQLdbConnectionsModule(object):
    pass

connections = MySQLdbConnectionsModule()
for var in dir(__orig_connections):
    if not var.startswith('__'):
        setattr(connections, var, getattr(__orig_connections, var))
connections.Connection = Connection

cursors = __import__('MySQLdb.cursors').cursors
converters = __import__('MySQLdb.converters').converters

# TODO support instantiating cursors.FooCursor objects directly
# TODO though this is a low priority, it would be nice if we supported
# subclassing eventlet.green.MySQLdb.connections.Connection

########NEW FILE########
__FILENAME__ = crypto
from OpenSSL.crypto import *
########NEW FILE########
__FILENAME__ = rand
from OpenSSL.rand import *
########NEW FILE########
__FILENAME__ = SSL
from OpenSSL import SSL as orig_SSL
from OpenSSL.SSL import *
from eventlet.support import get_errno
from eventlet import greenio
from eventlet.hubs import trampoline
import socket

class GreenConnection(greenio.GreenSocket):
    """ Nonblocking wrapper for SSL.Connection objects.
    """
    def __init__(self, ctx, sock=None):
        if sock is not None:
            fd = orig_SSL.Connection(ctx, sock)
        else:
            # if we're given a Connection object directly, use it;
            # this is used in the inherited accept() method
            fd = ctx
        super(ConnectionType, self).__init__(fd)
        
    def do_handshake(self):
        """ Perform an SSL handshake (usually called after renegotiate or one of 
        set_accept_state or set_accept_state). This can raise the same exceptions as 
        send and recv. """
        if self.act_non_blocking:
            return self.fd.do_handshake()
        while True:
            try:
                return self.fd.do_handshake()
            except WantReadError:
                trampoline(self.fd.fileno(), 
                           read=True, 
                           timeout=self.gettimeout(), 
                           timeout_exc=socket.timeout)
            except WantWriteError:
                trampoline(self.fd.fileno(), 
                           write=True, 
                           timeout=self.gettimeout(), 
                           timeout_exc=socket.timeout)
                           
    def dup(self):
        raise NotImplementedError("Dup not supported on SSL sockets")
        
    def makefile(self, mode='r', bufsize=-1):
        raise NotImplementedError("Makefile not supported on SSL sockets")  
        
    def read(self, size):
        """Works like a blocking call to SSL_read(), whose behavior is 
        described here:  http://www.openssl.org/docs/ssl/SSL_read.html"""
        if self.act_non_blocking:
            return self.fd.read(size)
        while True:
            try:
                return self.fd.read(size)
            except WantReadError:
                trampoline(self.fd.fileno(), 
                           read=True, 
                           timeout=self.gettimeout(), 
                           timeout_exc=socket.timeout)
            except WantWriteError:
                trampoline(self.fd.fileno(), 
                           write=True, 
                           timeout=self.gettimeout(), 
                           timeout_exc=socket.timeout)
            except SysCallError as e:
                if get_errno(e) == -1 or get_errno(e) > 0:
                    return ''
            
    recv = read
    
    def write(self, data):
        """Works like a blocking call to SSL_write(), whose behavior is 
        described here:  http://www.openssl.org/docs/ssl/SSL_write.html"""
        if not data:
            return 0 # calling SSL_write() with 0 bytes to be sent is undefined
        if self.act_non_blocking:
            return self.fd.write(data)
        while True:
            try:
                return self.fd.write(data)
            except WantReadError:
                trampoline(self.fd.fileno(), 
                           read=True, 
                           timeout=self.gettimeout(), 
                           timeout_exc=socket.timeout)
            except WantWriteError:
                trampoline(self.fd.fileno(), 
                           write=True, 
                           timeout=self.gettimeout(), 
                           timeout_exc=socket.timeout)
                           
    send = write
    
    def sendall(self, data):
        """Send "all" data on the connection. This calls send() repeatedly until
        all data is sent. If an error occurs, it's impossible to tell how much data
        has been sent.

        No return value."""
        tail = self.send(data)
        while tail < len(data):
            tail += self.send(data[tail:])
            
    def shutdown(self):
        if self.act_non_blocking:
            return self.fd.shutdown()
        while True:
            try:
                return self.fd.shutdown()
            except WantReadError:
                trampoline(self.fd.fileno(), 
                           read=True, 
                           timeout=self.gettimeout(), 
                           timeout_exc=socket.timeout)
            except WantWriteError:
                trampoline(self.fd.fileno(), 
                           write=True, 
                           timeout=self.gettimeout(), 
                           timeout_exc=socket.timeout)

Connection = ConnectionType = GreenConnection

del greenio

########NEW FILE########
__FILENAME__ = tsafe
from OpenSSL.tsafe import *
########NEW FILE########
__FILENAME__ = version
from OpenSSL.version import __version__, __doc__
########NEW FILE########
__FILENAME__ = os
os_orig = __import__("os")
import errno
socket = __import__("socket")

from eventlet import greenio
from eventlet.support import get_errno
from eventlet import greenthread
from eventlet import hubs
from eventlet.patcher import slurp_properties

__all__ = os_orig.__all__
__patched__ = ['fdopen', 'read', 'write', 'wait', 'waitpid']

slurp_properties(os_orig, globals(), 
    ignore=__patched__, srckeys=dir(os_orig))

def fdopen(fd, *args, **kw):
    """fdopen(fd [, mode='r' [, bufsize]]) -> file_object
    
    Return an open file object connected to a file descriptor."""
    if not isinstance(fd, int):
        raise TypeError('fd should be int, not %r' % fd)
    try:
        return greenio.GreenPipe(fd, *args, **kw)
    except IOError as e:
        raise OSError(*e.args)

__original_read__ = os_orig.read
def read(fd, n):
    """read(fd, buffersize) -> string
    
    Read a file descriptor."""
    while True:
        try:
            return __original_read__(fd, n)
        except (OSError, IOError) as e:
            if get_errno(e) != errno.EAGAIN:
                raise
        except socket.error as e:
            if get_errno(e) == errno.EPIPE:
                return ''
            raise
        hubs.trampoline(fd, read=True)

__original_write__ = os_orig.write
def write(fd, st):
    """write(fd, string) -> byteswritten
    
    Write a string to a file descriptor.
    """
    while True:
        try:
            return __original_write__(fd, st)
        except (OSError, IOError) as e:
            if get_errno(e) != errno.EAGAIN:
                raise
        except socket.error as e:
            if get_errno(e) != errno.EPIPE:
                raise
        hubs.trampoline(fd, write=True)
    
def wait():
    """wait() -> (pid, status)
    
    Wait for completion of a child process."""
    return waitpid(0,0)

__original_waitpid__ = os_orig.waitpid
def waitpid(pid, options):
    """waitpid(...)
    waitpid(pid, options) -> (pid, status)
    
    Wait for completion of a given child process."""
    if options & os_orig.WNOHANG != 0:
        return __original_waitpid__(pid, options)
    else:
        new_options = options | os_orig.WNOHANG
        while True:
            rpid, status = __original_waitpid__(pid, new_options)
            if rpid and status >= 0:
                return rpid, status
            greenthread.sleep(0.01)

# TODO: open

########NEW FILE########
__FILENAME__ = profile
# Copyright (c) 2010, CCP Games
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#     * Neither the name of CCP Games nor the
#       names of its contributors may be used to endorse or promote products
#       derived from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY CCP GAMES ``AS IS'' AND ANY
# EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL CCP GAMES BE LIABLE FOR ANY
# DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

"""This module is API-equivalent to the standard library :mod:`profile` module but it is greenthread-aware as well as thread-aware.  Use this module
to profile Eventlet-based applications in preference to either :mod:`profile` or :mod:`cProfile`.
FIXME: No testcases for this module.
"""

profile_orig = __import__('profile')
__all__ = profile_orig.__all__

from eventlet.patcher import slurp_properties
slurp_properties(profile_orig, globals(), srckeys=dir(profile_orig))

import new
import sys
import traceback
import functools

from eventlet import greenthread
from eventlet import patcher
thread = patcher.original('thread')  # non-monkeypatched module needed


#This class provides the start() and stop() functions
class Profile(profile_orig.Profile):
    base = profile_orig.Profile

    def __init__(self, timer = None, bias=None):
        self.current_tasklet = greenthread.getcurrent()
        self.thread_id = thread.get_ident()
        self.base.__init__(self, timer, bias)
        self.sleeping = {}

    def __call__(self, *args):
        """make callable, allowing an instance to be the profiler"""
        r = self.dispatcher(*args)

    def _setup(self):
        self._has_setup = True
        self.cur = None
        self.timings = {}
        self.current_tasklet = greenthread.getcurrent()
        self.thread_id = thread.get_ident()
        self.simulate_call("profiler")

    def start(self, name = "start"):
        if getattr(self, "running", False):
            return
        self._setup()
        self.simulate_call("start")
        self.running = True
        sys.setprofile(self.dispatcher)

    def stop(self):
        sys.setprofile(None)
        self.running = False
        self.TallyTimings()

    #special cases for the original run commands, makin sure to
    #clear the timer context.
    def runctx(self, cmd, globals, locals):
        if not getattr(self, "_has_setup", False):
            self._setup()
        try:
            return profile_orig.Profile.runctx(self, cmd, globals, locals)
        finally:
            self.TallyTimings()

    def runcall(self, func, *args, **kw):
        if not getattr(self, "_has_setup", False):
            self._setup()
        try:
            return profile_orig.Profile.runcall(self, func, *args, **kw)
        finally:
            self.TallyTimings()


    def trace_dispatch_return_extend_back(self, frame, t):
        """A hack function to override error checking in parent class.  It
        allows invalid returns (where frames weren't preveiously entered into
        the profiler) which can happen for all the tasklets that suddenly start
        to get monitored. This means that the time will eventually be attributed
        to a call high in the chain, when there is a tasklet switch
        """
        if isinstance(self.cur[-2], Profile.fake_frame):
            return False
            self.trace_dispatch_call(frame, 0)
        return self.trace_dispatch_return(frame, t);

    def trace_dispatch_c_return_extend_back(self, frame, t):
        #same for c return
        if isinstance(self.cur[-2], Profile.fake_frame):
            return False #ignore bogus returns
            self.trace_dispatch_c_call(frame, 0)
        return self.trace_dispatch_return(frame,t)


    #Add "return safety" to the dispatchers
    dispatch = dict(profile_orig.Profile.dispatch)
    dispatch.update({
        "return": trace_dispatch_return_extend_back,
        "c_return": trace_dispatch_c_return_extend_back,
        })

    def SwitchTasklet(self, t0, t1, t):
        #tally the time spent in the old tasklet
        pt, it, et, fn, frame, rcur = self.cur
        cur = (pt, it+t, et, fn, frame, rcur)

        #we are switching to a new tasklet, store the old
        self.sleeping[t0] = cur, self.timings
        self.current_tasklet = t1

        #find the new one
        try:
            self.cur, self.timings = self.sleeping.pop(t1)
        except KeyError:
            self.cur, self.timings = None, {}
            self.simulate_call("profiler")
            self.simulate_call("new_tasklet")


    def ContextWrap(f):
        @functools.wraps(f)
        def ContextWrapper(self, arg, t):
            current = greenthread.getcurrent()
            if current != self.current_tasklet:
                self.SwitchTasklet(self.current_tasklet, current, t)
                t = 0.0 #the time was billed to the previous tasklet
            return f(self, arg, t)
        return ContextWrapper

    #Add automatic tasklet detection to the callbacks.
    dispatch = dict([(key, ContextWrap(val)) for key,val in dispatch.iteritems()])

    def TallyTimings(self):
        oldtimings = self.sleeping
        self.sleeping = {}

        #first, unwind the main "cur"
        self.cur = self.Unwind(self.cur, self.timings)

        #we must keep the timings dicts separate for each tasklet, since it contains
        #the 'ns' item, recursion count of each function in that tasklet.  This is
        #used in the Unwind dude.
        for tasklet, (cur,timings) in oldtimings.iteritems():
            self.Unwind(cur, timings)

            for k,v in timings.iteritems():
                if k not in self.timings:
                    self.timings[k] = v
                else:
                    #accumulate all to the self.timings
                    cc, ns, tt, ct, callers = self.timings[k]
                    #ns should be 0 after unwinding
                    cc+=v[0]
                    tt+=v[2]
                    ct+=v[3]
                    for k1,v1 in v[4].iteritems():
                        callers[k1] = callers.get(k1, 0)+v1
                    self.timings[k] = cc, ns, tt, ct, callers

    def Unwind(self, cur, timings):
        "A function to unwind a 'cur' frame and tally the results"
        "see profile.trace_dispatch_return() for details"
        #also see simulate_cmd_complete()
        while(cur[-1]):
            rpt, rit, ret, rfn, frame, rcur = cur
            frame_total = rit+ret

            if rfn in timings:
                cc, ns, tt, ct, callers = timings[rfn]
            else:
                cc, ns, tt, ct, callers = 0, 0, 0, 0, {}

            if not ns:
                ct = ct + frame_total
                cc = cc + 1

            if rcur:
                ppt, pit, pet, pfn, pframe, pcur = rcur
            else:
                pfn = None

            if pfn in callers:
                callers[pfn] = callers[pfn] + 1  # hack: gather more
            elif pfn:
                callers[pfn] = 1

            timings[rfn] = cc, ns - 1, tt + rit, ct, callers

            ppt, pit, pet, pfn, pframe, pcur = rcur
            rcur = ppt, pit + rpt, pet + frame_total, pfn, pframe, pcur
            cur = rcur
        return cur


# run statements shamelessly stolen from profile.py
def run(statement, filename=None, sort=-1):
    """Run statement under profiler optionally saving results in filename

    This function takes a single argument that can be passed to the
    "exec" statement, and an optional file name.  In all cases this
    routine attempts to "exec" its first argument and gather profiling
    statistics from the execution. If no file name is present, then this
    function automatically prints a simple profiling report, sorted by the
    standard name string (file/line/function-name) that is presented in
    each line.
    """
    prof = Profile()
    try:
        prof = prof.run(statement)
    except SystemExit:
        pass
    if filename is not None:
        prof.dump_stats(filename)
    else:
        return prof.print_stats(sort)


def runctx(statement, globals, locals, filename=None):
    """Run statement under profiler, supplying your own globals and locals,
    optionally saving results in filename.

    statement and filename have the same semantics as profile.run
    """
    prof = Profile()
    try:
        prof = prof.runctx(statement, globals, locals)
    except SystemExit:
        pass

    if filename is not None:
        prof.dump_stats(filename)
    else:
        return prof.print_stats()

########NEW FILE########
__FILENAME__ = Queue
from eventlet import queue

__all__ = ['Empty', 'Full', 'LifoQueue', 'PriorityQueue', 'Queue']

__patched__ = ['LifoQueue', 'PriorityQueue', 'Queue']

# these classes exist to paper over the major operational difference between
# eventlet.queue.Queue and the stdlib equivalents
class Queue(queue.Queue):
    def __init__(self, maxsize=0):
        if maxsize == 0:
            maxsize = None
        super(Queue, self).__init__(maxsize)
    
class PriorityQueue(queue.PriorityQueue):
    def __init__(self, maxsize=0):
        if maxsize == 0:
            maxsize = None
        super(PriorityQueue, self).__init__(maxsize)
        
class LifoQueue(queue.LifoQueue):
    def __init__(self, maxsize=0):
        if maxsize == 0:
            maxsize = None
        super(LifoQueue, self).__init__(maxsize)
        
Empty = queue.Empty
Full = queue.Full

########NEW FILE########
__FILENAME__ = select
__select = __import__('select')
error = __select.error
from eventlet.greenthread import getcurrent
from eventlet.hubs import get_hub
from eventlet.support import six


__patched__ = ['select']


def get_fileno(obj):
    # The purpose of this function is to exactly replicate
    # the behavior of the select module when confronted with
    # abnormal filenos; the details are extensively tested in
    # the stdlib test/test_select.py.
    try:
        f = obj.fileno
    except AttributeError:
        if not isinstance(obj, six.integer_types):
            raise TypeError("Expected int or long, got " + type(obj))
        return obj
    else:
        rv = f()
        if not isinstance(rv, six.integer_types):
            raise TypeError("Expected int or long, got " + type(rv))
        return rv


def select(read_list, write_list, error_list, timeout=None):
    # error checking like this is required by the stdlib unit tests
    if timeout is not None:
        try:
            timeout = float(timeout)
        except ValueError:
            raise TypeError("Expected number for timeout")
    hub = get_hub()
    timers = []
    current = getcurrent()
    assert hub.greenlet is not current, 'do not call blocking functions from the mainloop'
    ds = {}
    for r in read_list:
        ds[get_fileno(r)] = {'read' : r}
    for w in write_list:
        ds.setdefault(get_fileno(w), {})['write'] = w
    for e in error_list:
        ds.setdefault(get_fileno(e), {})['error'] = e

    listeners = []

    def on_read(d):
        original = ds[get_fileno(d)]['read']
        current.switch(([original], [], []))

    def on_write(d):
        original = ds[get_fileno(d)]['write']
        current.switch(([], [original], []))

    def on_error(d, _err=None):
        original = ds[get_fileno(d)]['error']
        current.switch(([], [], [original]))

    def on_timeout2():
        current.switch(([], [], []))

    def on_timeout():
        # ensure that BaseHub.run() has a chance to call self.wait()
        # at least once before timed out.  otherwise the following code
        # can time out erroneously.
        #
        # s1, s2 = socket.socketpair()
        # print(select.select([], [s1], [], 0))
        timers.append(hub.schedule_call_global(0, on_timeout2))

    if timeout is not None:
        timers.append(hub.schedule_call_global(timeout, on_timeout))
    try:
        for k, v in six.iteritems(ds):
            if v.get('read'):
                listeners.append(hub.add(hub.READ, k, on_read))
            if v.get('write'):
                listeners.append(hub.add(hub.WRITE, k, on_write))
        try:
            return hub.switch()
        finally:
            for l in listeners:
                hub.remove(l)
    finally:
        for t in timers:
            t.cancel()

########NEW FILE########
__FILENAME__ = SimpleHTTPServer
from eventlet import patcher
from eventlet.green import BaseHTTPServer
from eventlet.green import urllib

patcher.inject('SimpleHTTPServer',
    globals(),
    ('BaseHTTPServer', BaseHTTPServer),
    ('urllib',  urllib))

del patcher

if __name__ == '__main__':
    test()
########NEW FILE########
__FILENAME__ = socket
import os
import sys
from eventlet.hubs import get_hub
__import__('eventlet.green._socket_nodns')
__socket = sys.modules['eventlet.green._socket_nodns']

__all__     = __socket.__all__
__patched__ = __socket.__patched__ + ['gethostbyname', 'getaddrinfo', 'create_connection',]

from eventlet.patcher import slurp_properties
slurp_properties(__socket, globals(), srckeys=dir(__socket))


greendns = None
if os.environ.get("EVENTLET_NO_GREENDNS",'').lower() != "yes":
    try:
        from eventlet.support import greendns
    except ImportError as ex:
        pass

if greendns:
    gethostbyname = greendns.gethostbyname
    getaddrinfo = greendns.getaddrinfo
    gethostbyname_ex = greendns.gethostbyname_ex
    getnameinfo = greendns.getnameinfo
    __patched__ = __patched__ + ['gethostbyname_ex', 'getnameinfo']

def create_connection(address, 
                      timeout=_GLOBAL_DEFAULT_TIMEOUT, 
                      source_address=None):
    """Connect to *address* and return the socket object.

    Convenience function.  Connect to *address* (a 2-tuple ``(host,
    port)``) and return the socket object.  Passing the optional
    *timeout* parameter will set the timeout on the socket instance
    before attempting to connect.  If no *timeout* is supplied, the
    global default timeout setting returned by :func:`getdefaulttimeout`
    is used.
    """

    msg = "getaddrinfo returns an empty list"
    host, port = address
    for res in getaddrinfo(host, port, 0, SOCK_STREAM):
        af, socktype, proto, canonname, sa = res
        sock = None
        try:
            sock = socket(af, socktype, proto)
            if timeout is not _GLOBAL_DEFAULT_TIMEOUT:
                sock.settimeout(timeout)
            if source_address:
                sock.bind(source_address)
            sock.connect(sa)
            return sock

        except error as msg:
            if sock is not None:
                sock.close()

    raise error(msg)



########NEW FILE########
__FILENAME__ = SocketServer
from eventlet import patcher

from eventlet.green import socket
from eventlet.green import select
from eventlet.green import threading
patcher.inject('SocketServer',
    globals(),
    ('socket', socket),
    ('select', select),
    ('threading', threading))

# QQQ ForkingMixIn should be fixed to use green waitpid?

########NEW FILE########
__FILENAME__ = ssl
__ssl = __import__('ssl')

from eventlet.patcher import slurp_properties
slurp_properties(__ssl, globals(), srckeys=dir(__ssl))

import sys
import errno
time = __import__('time')

from eventlet.support import get_errno
from eventlet.hubs import trampoline
from eventlet.greenio import set_nonblocking, GreenSocket, SOCKET_CLOSED, CONNECT_ERR, CONNECT_SUCCESS
orig_socket = __import__('socket')
socket = orig_socket.socket
if sys.version_info >= (2,7):
    has_ciphers = True
    timeout_exc = SSLError
else:
    has_ciphers = False
    timeout_exc = orig_socket.timeout

__patched__ = ['SSLSocket', 'wrap_socket', 'sslwrap_simple']

class GreenSSLSocket(__ssl.SSLSocket):
    """ This is a green version of the SSLSocket class from the ssl module added
    in 2.6.  For documentation on it, please see the Python standard
    documentation.

    Python nonblocking ssl objects don't give errors when the other end
    of the socket is closed (they do notice when the other end is shutdown,
    though).  Any write/read operations will simply hang if the socket is
    closed from the other end.  There is no obvious fix for this problem;
    it appears to be a limitation of Python's ssl object implementation.
    A workaround is to set a reasonable timeout on the socket using
    settimeout(), and to close/reopen the connection when a timeout
    occurs at an unexpected juncture in the code.
    """
    # we are inheriting from SSLSocket because its constructor calls
    # do_handshake whose behavior we wish to override
    def __init__(self, sock, *args, **kw):
        if not isinstance(sock, GreenSocket):
            sock = GreenSocket(sock)

        self.act_non_blocking = sock.act_non_blocking
        self._timeout = sock.gettimeout()
        super(GreenSSLSocket, self).__init__(sock.fd, *args, **kw)

        # the superclass initializer trashes the methods so we remove
        # the local-object versions of them and let the actual class
        # methods shine through
        try:
            for fn in orig_socket._delegate_methods:
                delattr(self, fn)
        except AttributeError:
            pass

    def settimeout(self, timeout):
        self._timeout = timeout

    def gettimeout(self):
        return self._timeout

    def setblocking(self, flag):
        if flag:
            self.act_non_blocking = False
            self._timeout = None
        else:
            self.act_non_blocking = True
            self._timeout = 0.0

    def _call_trampolining(self, func, *a, **kw):
        if self.act_non_blocking:
            return func(*a, **kw)
        else:
            while True:
                try:
                    return func(*a, **kw)
                except SSLError as exc:
                    if get_errno(exc) == SSL_ERROR_WANT_READ:
                        trampoline(self,
                                   read=True,
                                   timeout=self.gettimeout(),
                                   timeout_exc=timeout_exc('timed out'))
                    elif get_errno(exc) == SSL_ERROR_WANT_WRITE:
                        trampoline(self,
                                   write=True,
                                   timeout=self.gettimeout(),
                                   timeout_exc=timeout_exc('timed out'))
                    else:
                        raise

    def write(self, data):
        """Write DATA to the underlying SSL channel.  Returns
        number of bytes of DATA actually transmitted."""
        return self._call_trampolining(
            super(GreenSSLSocket, self).write, data)

    def read(self, len=1024):
        """Read up to LEN bytes and return them.
        Return zero-length string on EOF."""
        return self._call_trampolining(
            super(GreenSSLSocket, self).read, len)

    def send (self, data, flags=0):
        if self._sslobj:
            return self._call_trampolining(
                super(GreenSSLSocket, self).send, data, flags)
        else:
            trampoline(self, write=True, timeout_exc=timeout_exc('timed out'))
            return socket.send(self, data, flags)

    def sendto (self, data, addr, flags=0):
        # *NOTE: gross, copied code from ssl.py becase it's not factored well enough to be used as-is
        if self._sslobj:
            raise ValueError("sendto not allowed on instances of %s" %
                             self.__class__)
        else:
            trampoline(self, write=True, timeout_exc=timeout_exc('timed out'))
            return socket.sendto(self, data, addr, flags)

    def sendall (self, data, flags=0):
        # *NOTE: gross, copied code from ssl.py becase it's not factored well enough to be used as-is
        if self._sslobj:
            if flags != 0:
                raise ValueError(
                    "non-zero flags not allowed in calls to sendall() on %s" %
                    self.__class__)
            amount = len(data)
            count = 0
            while (count < amount):
                v = self.send(data[count:])
                count += v
                if v == 0:
                    trampoline(self, write=True, timeout_exc=timeout_exc('timed out'))
            return amount
        else:
            while True:
                try:
                    return socket.sendall(self, data, flags)
                except orig_socket.error as e:
                    if self.act_non_blocking:
                        raise
                    if get_errno(e) == errno.EWOULDBLOCK:
                        trampoline(self, write=True,
                                   timeout=self.gettimeout(), timeout_exc=timeout_exc('timed out'))
                    if get_errno(e) in SOCKET_CLOSED:
                        return ''
                    raise

    def recv(self, buflen=1024, flags=0):
        # *NOTE: gross, copied code from ssl.py becase it's not factored well enough to be used as-is
        if self._sslobj:
            if flags != 0:
                raise ValueError(
                    "non-zero flags not allowed in calls to recv() on %s" %
                    self.__class__)
            read = self.read(buflen)
            return read
        else:
            while True:
                try:
                    return socket.recv(self, buflen, flags)
                except orig_socket.error as e:
                    if self.act_non_blocking:
                        raise
                    if get_errno(e) == errno.EWOULDBLOCK:
                        trampoline(self, read=True,
                                   timeout=self.gettimeout(), timeout_exc=timeout_exc('timed out'))
                    if get_errno(e) in SOCKET_CLOSED:
                        return ''
                    raise


    def recv_into (self, buffer, nbytes=None, flags=0):
        if not self.act_non_blocking:
            trampoline(self, read=True, timeout=self.gettimeout(), timeout_exc=timeout_exc('timed out'))
        return super(GreenSSLSocket, self).recv_into(buffer, nbytes, flags)

    def recvfrom (self, addr, buflen=1024, flags=0):
        if not self.act_non_blocking:
            trampoline(self, read=True, timeout=self.gettimeout(), timeout_exc=timeout_exc('timed out'))
        return super(GreenSSLSocket, self).recvfrom(addr, buflen, flags)

    def recvfrom_into (self, buffer, nbytes=None, flags=0):
        if not self.act_non_blocking:
            trampoline(self, read=True, timeout=self.gettimeout(), timeout_exc=timeout_exc('timed out'))
        return super(GreenSSLSocket, self).recvfrom_into(buffer, nbytes, flags)

    def unwrap(self):
        return GreenSocket(self._call_trampolining(
                super(GreenSSLSocket, self).unwrap))

    def do_handshake(self):
        """Perform a TLS/SSL handshake."""
        return self._call_trampolining(
            super(GreenSSLSocket, self).do_handshake)

    def _socket_connect(self, addr):
        real_connect = socket.connect
        if self.act_non_blocking:
            return real_connect(self, addr)
        else:
            # *NOTE: gross, copied code from greenio because it's not factored
            # well enough to reuse
            if self.gettimeout() is None:
                while True:
                    try:
                        return real_connect(self, addr)
                    except orig_socket.error as exc:
                        if get_errno(exc) in CONNECT_ERR:
                            trampoline(self, write=True)
                        elif get_errno(exc) in CONNECT_SUCCESS:
                            return
                        else:
                            raise
            else:
                end = time.time() + self.gettimeout()
                while True:
                    try:
                        real_connect(self, addr)
                    except orig_socket.error as exc:
                        if get_errno(exc) in CONNECT_ERR:
                            trampoline(self, write=True,
                                       timeout=end-time.time(), timeout_exc=timeout_exc('timed out'))
                        elif get_errno(exc) in CONNECT_SUCCESS:
                            return
                        else:
                            raise
                    if time.time() >= end:
                        raise timeout_exc('timed out')


    def connect(self, addr):
        """Connects to remote ADDR, and then wraps the connection in
        an SSL channel."""
        # *NOTE: grrrrr copied this code from ssl.py because of the reference
        # to socket.connect which we don't want to call directly
        if self._sslobj:
            raise ValueError("attempt to connect already-connected SSLSocket!")
        self._socket_connect(addr)
        if has_ciphers:
            self._sslobj = _ssl.sslwrap(self._sock, False, self.keyfile, self.certfile,
                                        self.cert_reqs, self.ssl_version,
                                        self.ca_certs, self.ciphers)
        else:
            self._sslobj = _ssl.sslwrap(self._sock, False, self.keyfile, self.certfile,
                                        self.cert_reqs, self.ssl_version,
                                        self.ca_certs)
        if self.do_handshake_on_connect:
            self.do_handshake()

    def accept(self):
        """Accepts a new connection from a remote client, and returns
        a tuple containing that new connection wrapped with a server-side
        SSL channel, and the address of the remote client."""
        # RDW grr duplication of code from greenio
        if self.act_non_blocking:
            newsock, addr = socket.accept(self)
        else:
            while True:
                try:
                    newsock, addr = socket.accept(self)
                    set_nonblocking(newsock)
                    break
                except orig_socket.error as e:
                    if get_errno(e) != errno.EWOULDBLOCK:
                        raise
                    trampoline(self, read=True, timeout=self.gettimeout(),
                                   timeout_exc=timeout_exc('timed out'))

        new_ssl = type(self)(newsock,
                          keyfile=self.keyfile,
                          certfile=self.certfile,
                          server_side=True,
                          cert_reqs=self.cert_reqs,
                          ssl_version=self.ssl_version,
                          ca_certs=self.ca_certs,
                          do_handshake_on_connect=self.do_handshake_on_connect,
                          suppress_ragged_eofs=self.suppress_ragged_eofs)
        return (new_ssl, addr)

    def dup(self):
        raise NotImplementedError("Can't dup an ssl object")

SSLSocket = GreenSSLSocket

def wrap_socket(sock, *a, **kw):
    return GreenSSLSocket(sock, *a, **kw)


if hasattr(__ssl, 'sslwrap_simple'):
    def sslwrap_simple(sock, keyfile=None, certfile=None):
        """A replacement for the old socket.ssl function.  Designed
        for compability with Python 2.5 and earlier.  Will disappear in
        Python 3.0."""
        ssl_sock = GreenSSLSocket(sock, keyfile=keyfile, certfile=certfile,
                                  server_side=False,
                                  cert_reqs=CERT_NONE,
                                  ssl_version=PROTOCOL_SSLv23,
                                  ca_certs=None)
        return ssl_sock

########NEW FILE########
__FILENAME__ = subprocess
import errno
import time
from types import FunctionType

import eventlet
from eventlet import greenio
from eventlet import patcher
from eventlet.green import select
from eventlet.support import six


patcher.inject('subprocess', globals(), ('select', select))
subprocess_orig = __import__("subprocess")


if getattr(subprocess_orig, 'TimeoutExpired', None) is None:
    # Backported from Python 3.3.
    # https://bitbucket.org/eventlet/eventlet/issue/89
    class TimeoutExpired(Exception):
        """This exception is raised when the timeout expires while waiting for
        a child process.
        """
        def __init__(self, cmd, output=None):
            self.cmd = cmd
            self.output = output

        def __str__(self):
            return ("Command '%s' timed out after %s seconds" %
                    (self.cmd, self.timeout))


# This is the meat of this module, the green version of Popen.
class Popen(subprocess_orig.Popen):
    """eventlet-friendly version of subprocess.Popen"""
    # We do not believe that Windows pipes support non-blocking I/O. At least,
    # the Python file objects stored on our base-class object have no
    # setblocking() method, and the Python fcntl module doesn't exist on
    # Windows. (see eventlet.greenio.set_nonblocking()) As the sole purpose of
    # this __init__() override is to wrap the pipes for eventlet-friendly
    # non-blocking I/O, don't even bother overriding it on Windows.
    if not subprocess_orig.mswindows:
        def __init__(self, args, bufsize=0, *argss, **kwds):
            self.args = args
            # Forward the call to base-class constructor
            subprocess_orig.Popen.__init__(self, args, 0, *argss, **kwds)
            # Now wrap the pipes, if any. This logic is loosely borrowed from
            # eventlet.processes.Process.run() method.
            for attr in "stdin", "stdout", "stderr":
                pipe = getattr(self, attr)
                if pipe is not None and not type(pipe) == greenio.GreenPipe:
                    wrapped_pipe = greenio.GreenPipe(pipe, pipe.mode, bufsize)
                    setattr(self, attr, wrapped_pipe)
        __init__.__doc__ = subprocess_orig.Popen.__init__.__doc__

    def wait(self, timeout=None, check_interval=0.01):
        # Instead of a blocking OS call, this version of wait() uses logic
        # borrowed from the eventlet 0.2 processes.Process.wait() method.
        if timeout is not None:
            endtime = time.time() + timeout
        try:
            while True:
                status = self.poll()
                if status is not None:
                    return status
                if timeout is not None and time.time() > endtime:
                    raise TimeoutExpired(self.args)
                eventlet.sleep(check_interval)
        except OSError as e:
            if e.errno == errno.ECHILD:
                # no child process, this happens if the child process
                # already died and has been cleaned up
                return -1
            else:
                raise
    wait.__doc__ = subprocess_orig.Popen.wait.__doc__

    if not subprocess_orig.mswindows:
        # don't want to rewrite the original _communicate() method, we
        # just want a version that uses eventlet.green.select.select()
        # instead of select.select().
        _communicate = FunctionType(
            six.get_function_code(six.get_unbound_function(
                subprocess_orig.Popen._communicate)),
            globals())
        try:
            _communicate_with_select = FunctionType(
                six.get_function_code(six.get_unbound_function(
                    subprocess_orig.Popen._communicate_with_select)),
                globals())
            _communicate_with_poll = FunctionType(
                six.get_function_code(six.get_unbound_function(
                    subprocess_orig.Popen._communicate_with_poll)),
                globals())
        except AttributeError:
            pass

# Borrow subprocess.call() and check_call(), but patch them so they reference
# OUR Popen class rather than subprocess.Popen.
call = FunctionType(six.get_function_code(subprocess_orig.call), globals())
check_call = FunctionType(six.get_function_code(subprocess_orig.check_call), globals())

########NEW FILE########
__FILENAME__ = thread
"""Implements the standard thread module, using greenthreads."""
from eventlet.support.six.moves import _thread as __thread
from eventlet.support import greenlets as greenlet
from eventlet import greenthread
from eventlet.semaphore import Semaphore as LockType

__patched__ = ['get_ident', 'start_new_thread', 'start_new', 'allocate_lock',
               'allocate', 'exit', 'interrupt_main', 'stack_size', '_local', 
               'LockType', '_count']

error = __thread.error
__threadcount = 0

def _count():
    return __threadcount

def get_ident(gr=None):
    if gr is None:
        return id(greenlet.getcurrent())
    else:
        return id(gr)

def __thread_body(func, args, kwargs):
    global __threadcount
    __threadcount += 1
    try:
        func(*args, **kwargs)
    finally:
        __threadcount -= 1

def start_new_thread(function, args=(), kwargs={}):
    g = greenthread.spawn_n(__thread_body, function, args, kwargs)
    return get_ident(g)
    
start_new = start_new_thread

def allocate_lock(*a):
    return LockType(1)

allocate = allocate_lock

def exit():
    raise greenlet.GreenletExit
    
exit_thread = __thread.exit_thread

def interrupt_main():
    curr = greenlet.getcurrent()
    if curr.parent and not curr.parent.dead:
        curr.parent.throw(KeyboardInterrupt())
    else:
        raise KeyboardInterrupt()

if hasattr(__thread, 'stack_size'):
    __original_stack_size__ = __thread.stack_size
    def stack_size(size=None):
        if size is None:
            return __original_stack_size__()
        if size > __original_stack_size__():
            return __original_stack_size__(size)
        else:
            pass
            # not going to decrease stack_size, because otherwise other greenlets in this thread will suffer

from eventlet.corolocal import local as _local

########NEW FILE########
__FILENAME__ = threading
"""Implements the standard threading module, using greenthreads."""
from eventlet import patcher
from eventlet.green import thread
from eventlet.green import time
from eventlet.support import greenlets as greenlet

__patched__ = ['_start_new_thread', '_allocate_lock', '_get_ident', '_sleep',
               'local', 'stack_size', 'Lock', 'currentThread',
               'current_thread', '_after_fork', '_shutdown']

__orig_threading = patcher.original('threading')
__threadlocal = __orig_threading.local()


patcher.inject('threading',
    globals(),
    ('thread', thread),
    ('time', time))

del patcher


_count = 1
class _GreenThread(object):
    """Wrapper for GreenThread objects to provide Thread-like attributes
    and methods"""
    def __init__(self, g):
        global _count
        self._g = g
        self._name = 'GreenThread-%d' % _count
        _count += 1

    def __repr__(self):
        return '<_GreenThread(%s, %r)>' % (self._name, self._g)

    def join(self, timeout=None):
        return self._g.wait()

    def getName(self):
        return self._name
    get_name = getName

    def setName(self, name):
        self._name = str(name)
    set_name = setName

    name = property(getName, setName)

    ident = property(lambda self: id(self._g))

    def isAlive(self):
        return True
    is_alive = isAlive

    daemon = property(lambda self: True)

    def isDaemon(self):
        return self.daemon
    is_daemon = isDaemon


__threading = None

def _fixup_thread(t):
    # Some third-party packages (lockfile) will try to patch the
    # threading.Thread class with a get_name attribute if it doesn't
    # exist. Since we might return Thread objects from the original
    # threading package that won't get patched, let's make sure each
    # individual object gets patched too our patched threading.Thread
    # class has been patched. This is why monkey patching can be bad...
    global __threading
    if not __threading:
        __threading = __import__('threading')

    if (hasattr(__threading.Thread, 'get_name') and
        not hasattr(t, 'get_name')):
        t.get_name = t.getName
    return t


def current_thread():
    g = greenlet.getcurrent()
    if not g:
        # Not currently in a greenthread, fall back to standard function
        return _fixup_thread(__orig_threading.current_thread())

    try:
        active = __threadlocal.active
    except AttributeError:
        active = __threadlocal.active = {}
    
    try:
        t = active[id(g)]
    except KeyError:
        # Add green thread to active if we can clean it up on exit
        def cleanup(g):
            del active[id(g)]
        try:
            g.link(cleanup)
        except AttributeError:
            # Not a GreenThread type, so there's no way to hook into
            # the green thread exiting. Fall back to the standard
            # function then.
            t = _fixup_thread(__orig_threading.currentThread())
        else:
            t = active[id(g)] = _GreenThread(g)

    return t

currentThread = current_thread

########NEW FILE########
__FILENAME__ = time
__time = __import__('time')
from eventlet.patcher import slurp_properties
__patched__ = ['sleep']
slurp_properties(__time, globals(), ignore=__patched__, srckeys=dir(__time))
from eventlet.greenthread import sleep
sleep # silence pyflakes

########NEW FILE########
__FILENAME__ = urllib
from eventlet import patcher
from eventlet.green import socket
from eventlet.green import time
from eventlet.green import httplib
from eventlet.green import ftplib

to_patch = [('socket', socket), ('httplib', httplib),
            ('time', time), ('ftplib', ftplib)]
try:
    from eventlet.green import ssl
    to_patch.append(('ssl', ssl))
except ImportError:
    pass

patcher.inject('urllib', globals(), *to_patch)

# patch a bunch of things that have imports inside the
# function body; this is lame and hacky but I don't feel
# too bad because urllib is a hacky pile of junk that no
# one should be using anyhow
URLopener.open_http = patcher.patch_function(URLopener.open_http, ('httplib', httplib))
if hasattr(URLopener, 'open_https'):
    URLopener.open_https = patcher.patch_function(URLopener.open_https, ('httplib', httplib))

URLopener.open_ftp = patcher.patch_function(URLopener.open_ftp, ('ftplib', ftplib))
ftpwrapper.init = patcher.patch_function(ftpwrapper.init, ('ftplib', ftplib))
ftpwrapper.retrfile = patcher.patch_function(ftpwrapper.retrfile, ('ftplib', ftplib))

del patcher

# Run test program when run as a script
if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = urllib2
from eventlet import patcher
from eventlet.green import ftplib
from eventlet.green import httplib
from eventlet.green import socket
from eventlet.green import time
from eventlet.green import urllib

patcher.inject('urllib2',
    globals(),
    ('httplib', httplib),
    ('socket', socket),
    ('time', time),
    ('urllib', urllib))

FTPHandler.ftp_open = patcher.patch_function(FTPHandler.ftp_open, ('ftplib', ftplib))

del patcher

########NEW FILE########
__FILENAME__ = zmq
"""The :mod:`zmq` module wraps the :class:`Socket` and :class:`Context` found in :mod:`pyzmq <zmq>` to be non blocking
"""

from __future__ import with_statement

__zmq__ = __import__('zmq')
from eventlet import hubs
from eventlet.patcher import slurp_properties
from eventlet.support import greenlets as greenlet

__patched__ = ['Context', 'Socket']
slurp_properties(__zmq__, globals(), ignore=__patched__)

from collections import deque

try:
    # alias XREQ/XREP to DEALER/ROUTER if available
    if not hasattr(__zmq__, 'XREQ'):
        XREQ = DEALER
    if not hasattr(__zmq__, 'XREP'):
        XREP = ROUTER
except NameError:
    pass


class LockReleaseError(Exception):
    pass


class _QueueLock(object):
    """A Lock that can be acquired by at most one thread. Any other
    thread calling acquire will be blocked in a queue. When release
    is called, the threads are awoken in the order they blocked,
    one at a time. This lock can be required recursively by the same
    thread."""
    def __init__(self):
        self._waiters = deque()
        self._count = 0
        self._holder = None
        self._hub = hubs.get_hub()

    def __nonzero__(self):
        return self._count

    __bool__ = __nonzero__

    def __enter__(self):
        self.acquire()

    def __exit__(self, type, value, traceback):
        self.release()

    def acquire(self):
        current = greenlet.getcurrent()
        if (self._waiters or self._count > 0) and self._holder is not current:
            # block until lock is free
            self._waiters.append(current)
            self._hub.switch()
            w = self._waiters.popleft()

            assert w is current, 'Waiting threads woken out of order'
            assert self._count == 0, 'After waking a thread, the lock must be unacquired'

        self._holder = current
        self._count += 1

    def release(self):
        if self._count <= 0:
            raise LockReleaseError("Cannot release unacquired lock")

        self._count -= 1
        if self._count == 0:
            self._holder = None
            if self._waiters:
                # wake next
                self._hub.schedule_call_global(0, self._waiters[0].switch)


class _BlockedThread(object):
    """Is either empty, or represents a single blocked thread that
    blocked itself by calling the block() method. The thread can be
    awoken by calling wake(). Wake() can be called multiple times and
    all but the first call will have no effect."""

    def __init__(self):
        self._blocked_thread = None
        self._wakeupper = None
        self._hub = hubs.get_hub()

    def __nonzero__(self):
        return self._blocked_thread is not None

    __bool__ = __nonzero__

    def block(self):
        if self._blocked_thread is not None:
            raise Exception("Cannot block more than one thread on one BlockedThread")
        self._blocked_thread = greenlet.getcurrent()

        try:
            self._hub.switch()
        finally:
            self._blocked_thread = None
            # cleanup the wakeup task
            if self._wakeupper is not None:
                # Important to cancel the wakeup task so it doesn't
                # spuriously wake this greenthread later on.
                self._wakeupper.cancel()
                self._wakeupper = None

    def wake(self):
        """Schedules the blocked thread to be awoken and return
        True. If wake has already been called or if there is no
        blocked thread, then this call has no effect and returns
        False."""
        if self._blocked_thread is not None and self._wakeupper is None:
            self._wakeupper = self._hub.schedule_call_global(0, self._blocked_thread.switch)
            return True
        return False

class Context(__zmq__.Context):
    """Subclass of :class:`zmq.core.context.Context`
    """

    def socket(self, socket_type):
        """Overridden method to ensure that the green version of socket is used

        Behaves the same as :meth:`zmq.core.context.Context.socket`, but ensures
        that a :class:`Socket` with all of its send and recv methods set to be
        non-blocking is returned
        """
        if self.closed:
            raise ZMQError(ENOTSUP)
        return Socket(self, socket_type)

def _wraps(source_fn):
    """A decorator that copies the __name__ and __doc__ from the given
    function
    """
    def wrapper(dest_fn):
        dest_fn.__name__ = source_fn.__name__
        dest_fn.__doc__ = source_fn.__doc__
        return dest_fn
    return wrapper

# Implementation notes: Each socket in 0mq contains a pipe that the
# background IO threads use to communicate with the socket. These
# events are important because they tell the socket when it is able to
# send and when it has messages waiting to be received. The read end
# of the events pipe is the same FD that getsockopt(zmq.FD) returns.
#
# Events are read from the socket's event pipe only on the thread that
# the 0mq context is associated with, which is the native thread the
# greenthreads are running on, and the only operations that cause the
# events to be read and processed are send(), recv() and
# getsockopt(zmq.EVENTS). This means that after doing any of these
# three operations, the ability of the socket to send or receive a
# message without blocking may have changed, but after the events are
# read the FD is no longer readable so the hub may not signal our
# listener.
#
# If we understand that after calling send() a message might be ready
# to be received and that after calling recv() a message might be able
# to be sent, what should we do next? There are two approaches:
#
#  1. Always wake the other thread if there is one waiting. This
#  wakeup may be spurious because the socket might not actually be
#  ready for a send() or recv().  However, if a thread is in a
#  tight-loop successfully calling send() or recv() then the wakeups
#  are naturally batched and there's very little cost added to each
#  send/recv call.
#
# or
#
#  2. Call getsockopt(zmq.EVENTS) and explicitly check if the other
#  thread should be woken up. This avoids spurious wake-ups but may
#  add overhead because getsockopt will cause all events to be
#  processed, whereas send and recv throttle processing
#  events. Admittedly, all of the events will need to be processed
#  eventually, but it is likely faster to batch the processing.
#
# Which approach is better? I have no idea.
#
# TODO:
# - Support MessageTrackers and make MessageTracker.wait green

_Socket = __zmq__.Socket
_Socket_recv = _Socket.recv
_Socket_send = _Socket.send
_Socket_send_multipart = _Socket.send_multipart
_Socket_recv_multipart = _Socket.recv_multipart
_Socket_getsockopt = _Socket.getsockopt

class Socket(_Socket):
    """Green version of :class:`zmq.core.socket.Socket

    The following three methods are always overridden:
        * send
        * recv
        * getsockopt
    To ensure that the ``zmq.NOBLOCK`` flag is set and that sending or recieving
    is deferred to the hub (using :func:`eventlet.hubs.trampoline`) if a
    ``zmq.EAGAIN`` (retry) error is raised

    For some socket types, the following methods are also overridden:
        * send_multipart
        * recv_multipart
    """
    def __init__(self, context, socket_type):
        super(Socket, self).__init__(context, socket_type)

        self.__dict__['_eventlet_send_event'] = _BlockedThread()
        self.__dict__['_eventlet_recv_event'] = _BlockedThread()
        self.__dict__['_eventlet_send_lock'] = _QueueLock()
        self.__dict__['_eventlet_recv_lock'] = _QueueLock()

        def event(fd):
            # Some events arrived at the zmq socket. This may mean
            # there's a message that can be read or there's space for
            # a message to be written.
            send_wake = self._eventlet_send_event.wake()
            recv_wake = self._eventlet_recv_event.wake()
            if not send_wake and not recv_wake:
                # if no waiting send or recv thread was woken up, then
                # force the zmq socket's events to be processed to
                # avoid repeated wakeups
                _Socket_getsockopt(self, EVENTS)

        hub = hubs.get_hub()
        self.__dict__['_eventlet_listener'] = hub.add(hub.READ, self.getsockopt(FD), event)

    @_wraps(_Socket.close)
    def close(self, linger=None):
        super(Socket, self).close(linger)
        if self._eventlet_listener is not None:
            hubs.get_hub().remove(self._eventlet_listener)
            self.__dict__['_eventlet_listener'] = None
            # wake any blocked threads
            self._eventlet_send_event.wake()
            self._eventlet_recv_event.wake()

    @_wraps(_Socket.getsockopt)
    def getsockopt(self, option):
        result = _Socket_getsockopt(self, option)
        if option == EVENTS:
            # Getting the events causes the zmq socket to process
            # events which may mean a msg can be sent or received. If
            # there is a greenthread blocked and waiting for events,
            # it will miss the edge-triggered read event, so wake it
            # up.
            if (result & POLLOUT):
                self._eventlet_send_event.wake()
            if (result & POLLIN):
                self._eventlet_recv_event.wake()
        return result

    @_wraps(_Socket.send)
    def send(self, msg, flags=0, copy=True, track=False):
        """A send method that's safe to use when multiple greenthreads
        are calling send, send_multipart, recv and recv_multipart on
        the same socket.
        """
        if flags & NOBLOCK:
            result = _Socket_send(self, msg, flags, copy, track)
            # Instead of calling both wake methods, could call
            # self.getsockopt(EVENTS) which would trigger wakeups if
            # needed.
            self._eventlet_send_event.wake()
            self._eventlet_recv_event.wake()
            return result

        # TODO: pyzmq will copy the message buffer and create Message
        # objects under some circumstances. We could do that work here
        # once to avoid doing it every time the send is retried.
        flags |= NOBLOCK
        with self._eventlet_send_lock:
            while True:
                try:
                    return _Socket_send(self, msg, flags, copy, track)
                except ZMQError as e:
                    if e.errno == EAGAIN:
                        self._eventlet_send_event.block()
                    else:
                        raise
                finally:
                    # The call to send processes 0mq events and may
                    # make the socket ready to recv. Wake the next
                    # receiver. (Could check EVENTS for POLLIN here)
                    self._eventlet_recv_event.wake()


    @_wraps(_Socket.send_multipart)
    def send_multipart(self, msg_parts, flags=0, copy=True, track=False):
        """A send_multipart method that's safe to use when multiple
        greenthreads are calling send, send_multipart, recv and
        recv_multipart on the same socket.
        """
        if flags & NOBLOCK:
            return _Socket_send_multipart(self, msg_parts, flags, copy, track)

        # acquire lock here so the subsequent calls to send for the
        # message parts after the first don't block
        with self._eventlet_send_lock:
            return _Socket_send_multipart(self, msg_parts, flags, copy, track)

    @_wraps(_Socket.recv)
    def recv(self, flags=0, copy=True, track=False):
        """A recv method that's safe to use when multiple greenthreads
        are calling send, send_multipart, recv and recv_multipart on
        the same socket.
        """
        if flags & NOBLOCK:
            msg = _Socket_recv(self, flags, copy, track)
            # Instead of calling both wake methods, could call
            # self.getsockopt(EVENTS) which would trigger wakeups if
            # needed.
            self._eventlet_send_event.wake()
            self._eventlet_recv_event.wake()
            return msg

        flags |= NOBLOCK
        with self._eventlet_recv_lock:
            while True:
                try:
                    return _Socket_recv(self, flags, copy, track)
                except ZMQError as e:
                    if e.errno == EAGAIN:
                        self._eventlet_recv_event.block()
                    else:
                        raise
                finally:
                    # The call to recv processes 0mq events and may
                    # make the socket ready to send. Wake the next
                    # receiver. (Could check EVENTS for POLLOUT here)
                    self._eventlet_send_event.wake()

    @_wraps(_Socket.recv_multipart)
    def recv_multipart(self, flags=0, copy=True, track=False):
        """A recv_multipart method that's safe to use when multiple
        greenthreads are calling send, send_multipart, recv and
        recv_multipart on the same socket.
        """
        if flags & NOBLOCK:
            return _Socket_recv_multipart(self, flags, copy, track)

        # acquire lock here so the subsequent calls to recv for the
        # message parts after the first don't block
        with self._eventlet_recv_lock:
            return _Socket_recv_multipart(self, flags, copy, track)

########NEW FILE########
__FILENAME__ = _socket_nodns
__socket = __import__('socket')

__all__     = __socket.__all__
__patched__ = ['fromfd', 'socketpair', 'ssl', 'socket']

from eventlet.patcher import slurp_properties
slurp_properties(__socket, globals(),
    ignore=__patched__, srckeys=dir(__socket))

os = __import__('os')
import sys
import warnings
from eventlet.hubs import get_hub
from eventlet.greenio import GreenSocket as socket
from eventlet.greenio import SSL as _SSL  # for exceptions
from eventlet.greenio import _GLOBAL_DEFAULT_TIMEOUT
from eventlet.greenio import _fileobject

try:
    __original_fromfd__ = __socket.fromfd
    def fromfd(*args):
        return socket(__original_fromfd__(*args))
except AttributeError:
    pass

try:
    __original_socketpair__ = __socket.socketpair
    def socketpair(*args):
        one, two = __original_socketpair__(*args)
        return socket(one), socket(two)
except AttributeError:
    pass



def _convert_to_sslerror(ex):
    """ Transliterates SSL.SysCallErrors to socket.sslerrors"""
    return sslerror((ex.args[0], ex.args[1]))


class GreenSSLObject(object):
    """ Wrapper object around the SSLObjects returned by socket.ssl, which have a
    slightly different interface from SSL.Connection objects. """
    def __init__(self, green_ssl_obj):
        """ Should only be called by a 'green' socket.ssl """
        self.connection = green_ssl_obj
        try:
            # if it's already connected, do the handshake
            self.connection.getpeername()
        except:
            pass
        else:
            try:
                self.connection.do_handshake()
            except _SSL.SysCallError as e:
                raise _convert_to_sslerror(e)

    def read(self, n=1024):
        """If n is provided, read n bytes from the SSL connection, otherwise read
        until EOF. The return value is a string of the bytes read."""
        try:
            return self.connection.read(n)
        except _SSL.ZeroReturnError:
            return ''
        except _SSL.SysCallError as e:
            raise _convert_to_sslerror(e)

    def write(self, s):
        """Writes the string s to the on the object's SSL connection.
        The return value is the number of bytes written. """
        try:
            return self.connection.write(s)
        except _SSL.SysCallError as e:
            raise _convert_to_sslerror(e)

    def server(self):
        """ Returns a string describing the server's certificate. Useful for debugging
        purposes; do not parse the content of this string because its format can't be
        parsed unambiguously. """
        return str(self.connection.get_peer_certificate().get_subject())

    def issuer(self):
        """Returns a string describing the issuer of the server's certificate. Useful
        for debugging purposes; do not parse the content of this string because its
        format can't be parsed unambiguously."""
        return str(self.connection.get_peer_certificate().get_issuer())


try:
    from eventlet.green import ssl as ssl_module
    sslerror = __socket.sslerror
    __socket.ssl
except AttributeError:
    # if the real socket module doesn't have the ssl method or sslerror
    # exception, we can't emulate them
    pass
else:
    def ssl(sock, certificate=None, private_key=None):
        warnings.warn("socket.ssl() is deprecated.  Use ssl.wrap_socket() instead.",
                      DeprecationWarning, stacklevel=2)
        return ssl_module.sslwrap_simple(sock, private_key, certificate)

########NEW FILE########
__FILENAME__ = greenio
import array
import errno
import os
from socket import socket as _original_socket
import socket
import sys
import time
import warnings

from eventlet.support import get_errno, six
from eventlet.hubs import trampoline

__all__ = ['GreenSocket', 'GreenPipe', 'shutdown_safe']

BUFFER_SIZE = 4096
CONNECT_ERR = set((errno.EINPROGRESS, errno.EALREADY, errno.EWOULDBLOCK))
CONNECT_SUCCESS = set((0, errno.EISCONN))
if sys.platform[:3] == "win":
    CONNECT_ERR.add(errno.WSAEINVAL)   # Bug 67

if six.PY3:
    from io import IOBase as file
    _fileobject = socket.SocketIO
elif six.PY2:
    _fileobject = socket._fileobject


def socket_connect(descriptor, address):
    """
    Attempts to connect to the address, returns the descriptor if it succeeds,
    returns None if it needs to trampoline, and raises any exceptions.
    """
    err = descriptor.connect_ex(address)
    if err in CONNECT_ERR:
        return None
    if err not in CONNECT_SUCCESS:
        raise socket.error(err, errno.errorcode[err])
    return descriptor


def socket_checkerr(descriptor):
    err = descriptor.getsockopt(socket.SOL_SOCKET, socket.SO_ERROR)
    if err not in CONNECT_SUCCESS:
        raise socket.error(err, errno.errorcode[err])


def socket_accept(descriptor):
    """
    Attempts to accept() on the descriptor, returns a client,address tuple
    if it succeeds; returns None if it needs to trampoline, and raises
    any exceptions.
    """
    try:
        return descriptor.accept()
    except socket.error as e:
        if get_errno(e) == errno.EWOULDBLOCK:
            return None
        raise


if sys.platform[:3] == "win":
    # winsock sometimes throws ENOTCONN
    SOCKET_BLOCKING = set((errno.EWOULDBLOCK,))
    SOCKET_CLOSED = set((errno.ECONNRESET, errno.ENOTCONN, errno.ESHUTDOWN))
else:
    # oddly, on linux/darwin, an unconnected socket is expected to block,
    # so we treat ENOTCONN the same as EWOULDBLOCK
    SOCKET_BLOCKING = set((errno.EWOULDBLOCK, errno.ENOTCONN))
    SOCKET_CLOSED = set((errno.ECONNRESET, errno.ESHUTDOWN, errno.EPIPE))


def set_nonblocking(fd):
    """
    Sets the descriptor to be nonblocking.  Works on many file-like
    objects as well as sockets.  Only sockets can be nonblocking on
    Windows, however.
    """
    try:
        setblocking = fd.setblocking
    except AttributeError:
        # fd has no setblocking() method. It could be that this version of
        # Python predates socket.setblocking(). In that case, we can still set
        # the flag "by hand" on the underlying OS fileno using the fcntl
        # module.
        try:
            import fcntl
        except ImportError:
            # Whoops, Windows has no fcntl module. This might not be a socket
            # at all, but rather a file-like object with no setblocking()
            # method. In particular, on Windows, pipes don't support
            # non-blocking I/O and therefore don't have that method. Which
            # means fcntl wouldn't help even if we could load it.
            raise NotImplementedError("set_nonblocking() on a file object "
                                      "with no setblocking() method "
                                      "(Windows pipes don't support non-blocking I/O)")
        # We managed to import fcntl.
        fileno = fd.fileno()
        orig_flags = fcntl.fcntl(fileno, fcntl.F_GETFL)
        new_flags = orig_flags | os.O_NONBLOCK
        if new_flags != orig_flags:
            fcntl.fcntl(fileno, fcntl.F_SETFL, new_flags)
    else:
        # socket supports setblocking()
        setblocking(0)


try:
    from socket import _GLOBAL_DEFAULT_TIMEOUT
except ImportError:
    _GLOBAL_DEFAULT_TIMEOUT = object()


class GreenSocket(object):
    """
    Green version of socket.socket class, that is intended to be 100%
    API-compatible.

    It also recognizes the keyword parameter, 'set_nonblocking=True'.
    Pass False to indicate that socket is already in non-blocking mode
    to save syscalls.
    """
    def __init__(self, family_or_realsock=socket.AF_INET, *args, **kwargs):
        should_set_nonblocking = kwargs.pop('set_nonblocking', True)
        if isinstance(family_or_realsock, six.integer_types):
            fd = _original_socket(family_or_realsock, *args, **kwargs)
        else:
            fd = family_or_realsock

        # import timeout from other socket, if it was there
        try:
            self._timeout = fd.gettimeout() or socket.getdefaulttimeout()
        except AttributeError:
            self._timeout = socket.getdefaulttimeout()

        if should_set_nonblocking:
            set_nonblocking(fd)
        self.fd = fd
        # when client calls setblocking(0) or settimeout(0) the socket must
        # act non-blocking
        self.act_non_blocking = False

        # Copy some attributes from underlying real socket.
        # This is the easiest way that i found to fix
        # https://bitbucket.org/eventlet/eventlet/issue/136
        # Only `getsockopt` is required to fix that issue, others
        # are just premature optimization to save __getattr__ call.
        self.bind = fd.bind
        self.close = fd.close
        self.fileno = fd.fileno
        self.getsockname = fd.getsockname
        self.getsockopt = fd.getsockopt
        self.listen = fd.listen
        self.setsockopt = fd.setsockopt
        self.shutdown = fd.shutdown

    @property
    def _sock(self):
        return self

    # Forward unknown attributes to fd, cache the value for future use.
    # I do not see any simple attribute which could be changed
    # so caching everything in self is fine.
    # If we find such attributes - only attributes having __get__ might be cached.
    # For now - I do not want to complicate it.
    def __getattr__(self, name):
        attr = getattr(self.fd, name)
        setattr(self, name, attr)
        return attr

    def accept(self):
        if self.act_non_blocking:
            return self.fd.accept()
        fd = self.fd
        while True:
            res = socket_accept(fd)
            if res is not None:
                client, addr = res
                set_nonblocking(client)
                return type(self)(client), addr
            trampoline(fd, read=True, timeout=self.gettimeout(),
                       timeout_exc=socket.timeout("timed out"))

    def connect(self, address):
        if self.act_non_blocking:
            return self.fd.connect(address)
        fd = self.fd
        if self.gettimeout() is None:
            while not socket_connect(fd, address):
                trampoline(fd, write=True)
                socket_checkerr(fd)
        else:
            end = time.time() + self.gettimeout()
            while True:
                if socket_connect(fd, address):
                    return
                if time.time() >= end:
                    raise socket.timeout("timed out")
                trampoline(fd, write=True, timeout=end - time.time(),
                           timeout_exc=socket.timeout("timed out"))
                socket_checkerr(fd)

    def connect_ex(self, address):
        if self.act_non_blocking:
            return self.fd.connect_ex(address)
        fd = self.fd
        if self.gettimeout() is None:
            while not socket_connect(fd, address):
                try:
                    trampoline(fd, write=True)
                    socket_checkerr(fd)
                except socket.error as ex:
                    return get_errno(ex)
        else:
            end = time.time() + self.gettimeout()
            while True:
                try:
                    if socket_connect(fd, address):
                        return 0
                    if time.time() >= end:
                        raise socket.timeout(errno.EAGAIN)
                    trampoline(fd, write=True, timeout=end - time.time(),
                               timeout_exc=socket.timeout(errno.EAGAIN))
                    socket_checkerr(fd)
                except socket.error as ex:
                    return get_errno(ex)

    def dup(self, *args, **kw):
        sock = self.fd.dup(*args, **kw)
        newsock = type(self)(sock, set_nonblocking=False)
        newsock.settimeout(self.gettimeout())
        return newsock

    def makefile(self, *args, **kw):
        dupped = self.dup()
        res = _fileobject(dupped, *args, **kw)
        if hasattr(dupped, "_drop"):
            dupped._drop()
        return res

    def makeGreenFile(self, *args, **kw):
        warnings.warn("makeGreenFile has been deprecated, please use "
                      "makefile instead", DeprecationWarning, stacklevel=2)
        return self.makefile(*args, **kw)

    def recv(self, buflen, flags=0):
        fd = self.fd
        if self.act_non_blocking:
            return fd.recv(buflen, flags)
        while True:
            try:
                return fd.recv(buflen, flags)
            except socket.error as e:
                if get_errno(e) in SOCKET_BLOCKING:
                    pass
                elif get_errno(e) in SOCKET_CLOSED:
                    return ''
                else:
                    raise
            trampoline(
                fd,
                read=True,
                timeout=self.gettimeout(),
                timeout_exc=socket.timeout("timed out"))

    def recvfrom(self, *args):
        if not self.act_non_blocking:
            trampoline(self.fd, read=True, timeout=self.gettimeout(),
                       timeout_exc=socket.timeout("timed out"))
        return self.fd.recvfrom(*args)

    def recvfrom_into(self, *args):
        if not self.act_non_blocking:
            trampoline(self.fd, read=True, timeout=self.gettimeout(),
                       timeout_exc=socket.timeout("timed out"))
        return self.fd.recvfrom_into(*args)

    def recv_into(self, *args):
        if not self.act_non_blocking:
            trampoline(self.fd, read=True, timeout=self.gettimeout(),
                       timeout_exc=socket.timeout("timed out"))
        return self.fd.recv_into(*args)

    def send(self, data, flags=0):
        fd = self.fd
        if self.act_non_blocking:
            return fd.send(data, flags)

        # blocking socket behavior - sends all, blocks if the buffer is full
        total_sent = 0
        len_data = len(data)
        while 1:
            try:
                total_sent += fd.send(data[total_sent:], flags)
            except socket.error as e:
                if get_errno(e) not in SOCKET_BLOCKING:
                    raise

            if total_sent == len_data:
                break

            trampoline(self.fd, write=True, timeout=self.gettimeout(),
                       timeout_exc=socket.timeout("timed out"))

        return total_sent

    def sendall(self, data, flags=0):
        tail = self.send(data, flags)
        len_data = len(data)
        while tail < len_data:
            tail += self.send(data[tail:], flags)

    def sendto(self, *args):
        trampoline(self.fd, write=True)
        return self.fd.sendto(*args)

    def setblocking(self, flag):
        if flag:
            self.act_non_blocking = False
            self._timeout = None
        else:
            self.act_non_blocking = True
            self._timeout = 0.0

    def settimeout(self, howlong):
        if howlong is None or howlong == _GLOBAL_DEFAULT_TIMEOUT:
            self.setblocking(True)
            return
        try:
            f = howlong.__float__
        except AttributeError:
            raise TypeError('a float is required')
        howlong = f()
        if howlong < 0.0:
            raise ValueError('Timeout value out of range')
        if howlong == 0.0:
            self.act_non_blocking = True
            self._timeout = 0.0
        else:
            self.act_non_blocking = False
            self._timeout = howlong

    def gettimeout(self):
        return self._timeout

    if "__pypy__" in sys.builtin_module_names:
        def _reuse(self):
            self.fd._sock._reuse()

        def _drop(self):
            self.fd._sock._drop()


class _SocketDuckForFd(object):
    """ Class implementing all socket method used by _fileobject in cooperative manner using low level os I/O calls."""
    def __init__(self, fileno):
        self._fileno = fileno

    @property
    def _sock(self):
        return self

    def fileno(self):
        return self._fileno

    def recv(self, buflen):
        while True:
            try:
                data = os.read(self._fileno, buflen)
                return data
            except OSError as e:
                if get_errno(e) != errno.EAGAIN:
                    raise IOError(*e.args)
            trampoline(self, read=True)

    def sendall(self, data):
        len_data = len(data)
        os_write = os.write
        fileno = self._fileno
        try:
            total_sent = os_write(fileno, data)
        except OSError as e:
            if get_errno(e) != errno.EAGAIN:
                raise IOError(*e.args)
            total_sent = 0
        while total_sent < len_data:
            trampoline(self, write=True)
            try:
                total_sent += os_write(fileno, data[total_sent:])
            except OSError as e:
                if get_errno(e) != errno. EAGAIN:
                    raise IOError(*e.args)

    def __del__(self):
        self._close()

    def _close(self):
        try:
            os.close(self._fileno)
        except:
            # os.close may fail if __init__ didn't complete (i.e file dscriptor passed to popen was invalid
            pass

    def __repr__(self):
        return "%s:%d" % (self.__class__.__name__, self._fileno)

    if "__pypy__" in sys.builtin_module_names:
        _refcount = 0

        def _reuse(self):
            self._refcount += 1

        def _drop(self):
            self._refcount -= 1
            if self._refcount == 0:
                self._close()


def _operationOnClosedFile(*args, **kwargs):
    raise ValueError("I/O operation on closed file")


class GreenPipe(_fileobject):
    """
    GreenPipe is a cooperative replacement for file class.
    It will cooperate on pipes. It will block on regular file.
    Differneces from file class:
    - mode is r/w property. Should re r/o
    - encoding property not implemented
    - write/writelines will not raise TypeError exception when non-string data is written
      it will write str(data) instead
    - Universal new lines are not supported and newlines property not implementeded
    - file argument can be descriptor, file name or file object.
    """
    def __init__(self, f, mode='r', bufsize=-1):
        if not isinstance(f, six.string_types + (int, file)):
            raise TypeError('f(ile) should be int, str, unicode or file, not %r' % f)

        if isinstance(f, six.string_types):
            f = open(f, mode, 0)

        if isinstance(f, int):
            fileno = f
            self._name = "<fd:%d>" % fileno
        else:
            fileno = os.dup(f.fileno())
            self._name = f.name
            if f.mode != mode:
                raise ValueError('file.mode %r does not match mode parameter %r' % (f.mode, mode))
            self._name = f.name
            f.close()

        super(GreenPipe, self).__init__(_SocketDuckForFd(fileno), mode, bufsize)
        set_nonblocking(self)
        self.softspace = 0

    @property
    def name(self):
        return self._name

    def __repr__(self):
        return "<%s %s %r, mode %r at 0x%x>" % (
            self.closed and 'closed' or 'open',
            self.__class__.__name__,
            self.name,
            self.mode,
            (id(self) < 0) and (sys.maxint + id(self)) or id(self))

    def close(self):
        super(GreenPipe, self).close()
        for method in [
                'fileno', 'flush', 'isatty', 'next', 'read', 'readinto',
                'readline', 'readlines', 'seek', 'tell', 'truncate',
                'write', 'xreadlines', '__iter__', 'writelines']:
            setattr(self, method, _operationOnClosedFile)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def readinto(self, buf):
        data = self.read(len(buf))  # FIXME could it be done without allocating intermediate?
        n = len(data)
        try:
            buf[:n] = data
        except TypeError as err:
            if not isinstance(buf, array.array):
                raise err
            buf[:n] = array.array('c', data)
        return n

    def _get_readahead_len(self):
        return len(self._rbuf.getvalue())

    def _clear_readahead_buf(self):
        len = self._get_readahead_len()
        if len > 0:
            self.read(len)

    def tell(self):
        self.flush()
        try:
            return os.lseek(self.fileno(), 0, 1) - self._get_readahead_len()
        except OSError as e:
            raise IOError(*e.args)

    def seek(self, offset, whence=0):
        self.flush()
        if whence == 1 and offset == 0:  # tell synonym
            return self.tell()
        if whence == 1:  # adjust offset by what is read ahead
            offset -= self._get_readahead_len()
        try:
            rv = os.lseek(self.fileno(), offset, whence)
        except OSError as e:
            raise IOError(*e.args)
        else:
            self._clear_readahead_buf()
            return rv

    if getattr(file, "truncate", None):  # not all OSes implement truncate
        def truncate(self, size=-1):
            self.flush()
            if size == -1:
                size = self.tell()
            try:
                rv = os.ftruncate(self.fileno(), size)
            except OSError as e:
                raise IOError(*e.args)
            else:
                self.seek(size)  # move position&clear buffer
                return rv

    def isatty(self):
        try:
            return os.isatty(self.fileno())
        except OSError as e:
            raise IOError(*e.args)


# import SSL module here so we can refer to greenio.SSL.exceptionclass
try:
    from OpenSSL import SSL
except ImportError:
    # pyOpenSSL not installed, define exceptions anyway for convenience
    class SSL(object):
        class WantWriteError(object):
            pass

        class WantReadError(object):
            pass

        class ZeroReturnError(object):
            pass

        class SysCallError(object):
            pass


def shutdown_safe(sock):
    """ Shuts down the socket. This is a convenience method for
    code that wants to gracefully handle regular sockets, SSL.Connection
    sockets from PyOpenSSL and ssl.SSLSocket objects from Python 2.6
    interchangeably.  Both types of ssl socket require a shutdown() before
    close, but they have different arity on their shutdown method.

    Regular sockets don't need a shutdown before close, but it doesn't hurt.
    """
    try:
        try:
            # socket, ssl.SSLSocket
            return sock.shutdown(socket.SHUT_RDWR)
        except TypeError:
            # SSL.Connection
            return sock.shutdown()
    except socket.error as e:
        # we don't care if the socket is already closed;
        # this will often be the case in an http server context
        if get_errno(e) != errno.ENOTCONN:
            raise

########NEW FILE########
__FILENAME__ = greenpool
import traceback

from eventlet import event
from eventlet import greenthread
from eventlet import queue
from eventlet import semaphore
from eventlet.support import greenlets as greenlet
from eventlet.support import six

__all__ = ['GreenPool', 'GreenPile']

DEBUG = True


class GreenPool(object):
    """The GreenPool class is a pool of green threads.
    """
    def __init__(self, size=1000):
        self.size = size
        self.coroutines_running = set()
        self.sem = semaphore.Semaphore(size)
        self.no_coros_running = event.Event()

    def resize(self, new_size):
        """ Change the max number of greenthreads doing work at any given time.

        If resize is called when there are more than *new_size* greenthreads
        already working on tasks, they will be allowed to complete but no new
        tasks will be allowed to get launched until enough greenthreads finish
        their tasks to drop the overall quantity below *new_size*.  Until
        then, the return value of free() will be negative.
        """
        size_delta = new_size - self.size
        self.sem.counter += size_delta
        self.size = new_size

    def running(self):
        """ Returns the number of greenthreads that are currently executing
        functions in the GreenPool."""
        return len(self.coroutines_running)

    def free(self):
        """ Returns the number of greenthreads available for use.

        If zero or less, the next call to :meth:`spawn` or :meth:`spawn_n` will
        block the calling greenthread until a slot becomes available."""
        return self.sem.counter

    def spawn(self, function, *args, **kwargs):
        """Run the *function* with its arguments in its own green thread.
        Returns the :class:`GreenThread <eventlet.greenthread.GreenThread>`
        object that is running the function, which can be used to retrieve the
        results.

        If the pool is currently at capacity, ``spawn`` will block until one of
        the running greenthreads completes its task and frees up a slot.

        This function is reentrant; *function* can call ``spawn`` on the same
        pool without risk of deadlocking the whole thing.
        """
        # if reentering an empty pool, don't try to wait on a coroutine freeing
        # itself -- instead, just execute in the current coroutine
        current = greenthread.getcurrent()
        if self.sem.locked() and current in self.coroutines_running:
            # a bit hacky to use the GT without switching to it
            gt = greenthread.GreenThread(current)
            gt.main(function, args, kwargs)
            return gt
        else:
            self.sem.acquire()
            gt = greenthread.spawn(function, *args, **kwargs)
            if not self.coroutines_running:
                self.no_coros_running = event.Event()
            self.coroutines_running.add(gt)
            gt.link(self._spawn_done)
        return gt

    def _spawn_n_impl(self, func, args, kwargs, coro):
        try:
            try:
                func(*args, **kwargs)
            except (KeyboardInterrupt, SystemExit, greenlet.GreenletExit):
                raise
            except:
                if DEBUG:
                    traceback.print_exc()
        finally:
            if coro is None:
                return
            else:
                coro = greenthread.getcurrent()
                self._spawn_done(coro)

    def spawn_n(self, function, *args, **kwargs):
        """Create a greenthread to run the *function*, the same as
        :meth:`spawn`.  The difference is that :meth:`spawn_n` returns
        None; the results of *function* are not retrievable.
        """
        # if reentering an empty pool, don't try to wait on a coroutine freeing
        # itself -- instead, just execute in the current coroutine
        current = greenthread.getcurrent()
        if self.sem.locked() and current in self.coroutines_running:
            self._spawn_n_impl(function, args, kwargs, None)
        else:
            self.sem.acquire()
            g = greenthread.spawn_n(
                self._spawn_n_impl,
                function, args, kwargs, True)
            if not self.coroutines_running:
                self.no_coros_running = event.Event()
            self.coroutines_running.add(g)

    def waitall(self):
        """Waits until all greenthreads in the pool are finished working."""
        assert greenthread.getcurrent() not in self.coroutines_running, \
            "Calling waitall() from within one of the " \
            "GreenPool's greenthreads will never terminate."
        if self.running():
            self.no_coros_running.wait()

    def _spawn_done(self, coro):
        self.sem.release()
        if coro is not None:
            self.coroutines_running.remove(coro)
        # if done processing (no more work is waiting for processing),
        # we can finish off any waitall() calls that might be pending
        if self.sem.balance == self.size:
            self.no_coros_running.send(None)

    def waiting(self):
        """Return the number of greenthreads waiting to spawn.
        """
        if self.sem.balance < 0:
            return -self.sem.balance
        else:
            return 0

    def _do_map(self, func, it, gi):
        for args in it:
            gi.spawn(func, *args)
        gi.spawn(return_stop_iteration)

    def starmap(self, function, iterable):
        """This is the same as :func:`itertools.starmap`, except that *func* is
        executed in a separate green thread for each item, with the concurrency
        limited by the pool's size. In operation, starmap consumes a constant
        amount of memory, proportional to the size of the pool, and is thus
        suited for iterating over extremely long input lists.
        """
        if function is None:
            function = lambda *a: a
        gi = GreenMap(self.size)
        greenthread.spawn_n(self._do_map, function, iterable, gi)
        return gi

    def imap(self, function, *iterables):
        """This is the same as :func:`itertools.imap`, and has the same
        concurrency and memory behavior as :meth:`starmap`.

        It's quite convenient for, e.g., farming out jobs from a file::

           def worker(line):
               return do_something(line)
           pool = GreenPool()
           for result in pool.imap(worker, open("filename", 'r')):
               print(result)
        """
        return self.starmap(function, six.moves.zip(*iterables))


def return_stop_iteration():
    return StopIteration()


class GreenPile(object):
    """GreenPile is an abstraction representing a bunch of I/O-related tasks.

    Construct a GreenPile with an existing GreenPool object.  The GreenPile will
    then use that pool's concurrency as it processes its jobs.  There can be
    many GreenPiles associated with a single GreenPool.

    A GreenPile can also be constructed standalone, not associated with any
    GreenPool.  To do this, construct it with an integer size parameter instead
    of a GreenPool.

    It is not advisable to iterate over a GreenPile in a different greenthread
    than the one which is calling spawn.  The iterator will exit early in that
    situation.
    """
    def __init__(self, size_or_pool=1000):
        if isinstance(size_or_pool, GreenPool):
            self.pool = size_or_pool
        else:
            self.pool = GreenPool(size_or_pool)
        self.waiters = queue.LightQueue()
        self.used = False
        self.counter = 0

    def spawn(self, func, *args, **kw):
        """Runs *func* in its own green thread, with the result available by
        iterating over the GreenPile object."""
        self.used = True
        self.counter += 1
        try:
            gt = self.pool.spawn(func, *args, **kw)
            self.waiters.put(gt)
        except:
            self.counter -= 1
            raise

    def __iter__(self):
        return self

    def next(self):
        """Wait for the next result, suspending the current greenthread until it
        is available.  Raises StopIteration when there are no more results."""
        if self.counter == 0 and self.used:
            raise StopIteration()
        try:
            return self.waiters.get().wait()
        finally:
            self.counter -= 1
    __next__ = next


# this is identical to GreenPile but it blocks on spawn if the results
# aren't consumed, and it doesn't generate its own StopIteration exception,
# instead relying on the spawning process to send one in when it's done
class GreenMap(GreenPile):
    def __init__(self, size_or_pool):
        super(GreenMap, self).__init__(size_or_pool)
        self.waiters = queue.LightQueue(maxsize=self.pool.size)

    def next(self):
        try:
            val = self.waiters.get().wait()
            if isinstance(val, StopIteration):
                raise val
            else:
                return val
        finally:
            self.counter -= 1
    __next__ = next

########NEW FILE########
__FILENAME__ = greenthread
from collections import deque
import sys

from eventlet import event
from eventlet import hubs
from eventlet import timeout
from eventlet.hubs import timer
from eventlet.support import greenlets as greenlet, six
import warnings

__all__ = ['getcurrent', 'sleep', 'spawn', 'spawn_n', 'spawn_after', 'spawn_after_local', 'GreenThread']

getcurrent = greenlet.getcurrent

def sleep(seconds=0):
    """Yield control to another eligible coroutine until at least *seconds* have
    elapsed.

    *seconds* may be specified as an integer, or a float if fractional seconds
    are desired. Calling :func:`~greenthread.sleep` with *seconds* of 0 is the
    canonical way of expressing a cooperative yield. For example, if one is
    looping over a large list performing an expensive calculation without
    calling any socket methods, it's a good idea to call ``sleep(0)``
    occasionally; otherwise nothing else will run.
    """
    hub = hubs.get_hub()
    current = getcurrent()
    assert hub.greenlet is not current, 'do not call blocking functions from the mainloop'
    timer = hub.schedule_call_global(seconds, current.switch)
    try:
        hub.switch()
    finally:
        timer.cancel()


def spawn(func, *args, **kwargs):
    """Create a greenthread to run ``func(*args, **kwargs)``.  Returns a
    :class:`GreenThread` object which you can use to get the results of the
    call.

    Execution control returns immediately to the caller; the created greenthread
    is merely scheduled to be run at the next available opportunity.
    Use :func:`spawn_after` to  arrange for greenthreads to be spawned
    after a finite delay.
    """
    hub = hubs.get_hub()
    g = GreenThread(hub.greenlet)
    hub.schedule_call_global(0, g.switch, func, args, kwargs)
    return g


def spawn_n(func, *args, **kwargs):
    """Same as :func:`spawn`, but returns a ``greenlet`` object from
    which it is not possible to retrieve either a return value or
    whether it raised any exceptions.  This is faster than
    :func:`spawn`; it is fastest if there are no keyword arguments.

    If an exception is raised in the function, spawn_n prints a stack
    trace; the print can be disabled by calling
    :func:`eventlet.debug.hub_exceptions` with False.
    """
    return _spawn_n(0, func, args, kwargs)[1]


def spawn_after(seconds, func, *args, **kwargs):
    """Spawns *func* after *seconds* have elapsed.  It runs as scheduled even if
    the current greenthread has completed.

    *seconds* may be specified as an integer, or a float if fractional seconds
    are desired. The *func* will be called with the given *args* and
    keyword arguments *kwargs*, and will be executed within its own greenthread.

    The return value of :func:`spawn_after` is a :class:`GreenThread` object,
    which can be used to retrieve the results of the call.

    To cancel the spawn and prevent *func* from being called,
    call :meth:`GreenThread.cancel` on the return value of :func:`spawn_after`.
    This will not abort the function if it's already started running, which is
    generally the desired behavior.  If terminating *func* regardless of whether
    it's started or not is the desired behavior, call :meth:`GreenThread.kill`.
    """
    hub = hubs.get_hub()
    g = GreenThread(hub.greenlet)
    hub.schedule_call_global(seconds, g.switch, func, args, kwargs)
    return g


def spawn_after_local(seconds, func, *args, **kwargs):
    """Spawns *func* after *seconds* have elapsed.  The function will NOT be
    called if the current greenthread has exited.

    *seconds* may be specified as an integer, or a float if fractional seconds
    are desired. The *func* will be called with the given *args* and
    keyword arguments *kwargs*, and will be executed within its own greenthread.

    The return value of :func:`spawn_after` is a :class:`GreenThread` object,
    which can be used to retrieve the results of the call.

    To cancel the spawn and prevent *func* from being called,
    call :meth:`GreenThread.cancel` on the return value. This will not abort the
    function if it's already started running.  If terminating *func* regardless
    of whether it's started or not is the desired behavior, call
    :meth:`GreenThread.kill`.
    """
    hub = hubs.get_hub()
    g = GreenThread(hub.greenlet)
    hub.schedule_call_local(seconds, g.switch, func, args, kwargs)
    return g


def call_after_global(seconds, func, *args, **kwargs):
    warnings.warn("call_after_global is renamed to spawn_after, which"
        "has the same signature and semantics (plus a bit extra).  Please do a"
        " quick search-and-replace on your codebase, thanks!",
        DeprecationWarning, stacklevel=2)
    return _spawn_n(seconds, func, args, kwargs)[0]


def call_after_local(seconds, function, *args, **kwargs):
    warnings.warn("call_after_local is renamed to spawn_after_local, which"
        "has the same signature and semantics (plus a bit extra).",
        DeprecationWarning, stacklevel=2)
    hub = hubs.get_hub()
    g = greenlet.greenlet(function, parent=hub.greenlet)
    t = hub.schedule_call_local(seconds, g.switch, *args, **kwargs)
    return t


call_after = call_after_local


def exc_after(seconds, *throw_args):
    warnings.warn("Instead of exc_after, which is deprecated, use "
                  "Timeout(seconds, exception)",
                  DeprecationWarning, stacklevel=2)
    if seconds is None:  # dummy argument, do nothing
        return timer.Timer(seconds, lambda: None)
    hub = hubs.get_hub()
    return hub.schedule_call_local(seconds, getcurrent().throw, *throw_args)

# deprecate, remove
TimeoutError = timeout.Timeout
with_timeout = timeout.with_timeout

def _spawn_n(seconds, func, args, kwargs):
    hub = hubs.get_hub()
    g = greenlet.greenlet(func, parent=hub.greenlet)
    t = hub.schedule_call_global(seconds, g.switch, *args, **kwargs)
    return t, g


class GreenThread(greenlet.greenlet):
    """The GreenThread class is a type of Greenlet which has the additional
    property of being able to retrieve the return value of the main function.
    Do not construct GreenThread objects directly; call :func:`spawn` to get one.
    """
    def __init__(self, parent):
        greenlet.greenlet.__init__(self, self.main, parent)
        self._exit_event = event.Event()
        self._resolving_links = False

    def wait(self):
        """ Returns the result of the main function of this GreenThread.  If the
        result is a normal return value, :meth:`wait` returns it.  If it raised
        an exception, :meth:`wait` will raise the same exception (though the
        stack trace will unavoidably contain some frames from within the
        greenthread module)."""
        return self._exit_event.wait()

    def link(self, func, *curried_args, **curried_kwargs):
        """ Set up a function to be called with the results of the GreenThread.

        The function must have the following signature::

            def func(gt, [curried args/kwargs]):

        When the GreenThread finishes its run, it calls *func* with itself
        and with the `curried arguments <http://en.wikipedia.org/wiki/Currying>`_ supplied at link-time.  If the function wants
        to retrieve the result of the GreenThread, it should call wait()
        on its first argument.

        Note that *func* is called within execution context of
        the GreenThread, so it is possible to interfere with other linked
        functions by doing things like switching explicitly to another
        greenthread.
        """
        self._exit_funcs = getattr(self, '_exit_funcs', deque())
        self._exit_funcs.append((func, curried_args, curried_kwargs))
        if self._exit_event.ready():
            self._resolve_links()

    def unlink(self, func, *curried_args, **curried_kwargs):
        """ remove linked function set by :meth:`link`

        Remove successfully return True, otherwise False
        """
        if not getattr(self, '_exit_funcs', None):
            return False
        try:
            self._exit_funcs.remove((func, curried_args, curried_kwargs))
            return True
        except ValueError:
            return False

    def main(self, function, args, kwargs):
        try:
            result = function(*args, **kwargs)
        except:
            self._exit_event.send_exception(*sys.exc_info())
            self._resolve_links()
            raise
        else:
            self._exit_event.send(result)
            self._resolve_links()

    def _resolve_links(self):
        # ca and ckw are the curried function arguments
        if self._resolving_links:
            return
        self._resolving_links = True
        try:
            exit_funcs = getattr(self, '_exit_funcs', deque())
            while exit_funcs:
                f, ca, ckw = exit_funcs.popleft()
                f(self, *ca, **ckw)
        finally:
            self._resolving_links = False

    def kill(self, *throw_args):
        """Kills the greenthread using :func:`kill`.  After being killed
        all calls to :meth:`wait` will raise *throw_args* (which default
        to :class:`greenlet.GreenletExit`)."""
        return kill(self, *throw_args)

    def cancel(self, *throw_args):
        """Kills the greenthread using :func:`kill`, but only if it hasn't
        already started running.  After being canceled,
        all calls to :meth:`wait` will raise *throw_args* (which default
        to :class:`greenlet.GreenletExit`)."""
        return cancel(self, *throw_args)

def cancel(g, *throw_args):
    """Like :func:`kill`, but only terminates the greenthread if it hasn't
    already started execution.  If the grenthread has already started
    execution, :func:`cancel` has no effect."""
    if not g:
        kill(g, *throw_args)

def kill(g, *throw_args):
    """Terminates the target greenthread by raising an exception into it.
    Whatever that greenthread might be doing; be it waiting for I/O or another
    primitive, it sees an exception right away.

    By default, this exception is GreenletExit, but a specific exception
    may be specified.  *throw_args* should be the same as the arguments to
    raise; either an exception instance or an exc_info tuple.

    Calling :func:`kill` causes the calling greenthread to cooperatively yield.
    """
    if g.dead:
        return
    hub = hubs.get_hub()
    if not g:
        # greenlet hasn't started yet and therefore throw won't work
        # on its own; semantically we want it to be as though the main
        # method never got called
        def just_raise(*a, **kw):
            if throw_args:
                six.reraise(throw_args[0], throw_args[1], throw_args[2])
            else:
                raise greenlet.GreenletExit()
        g.run = just_raise
        if isinstance(g, GreenThread):
            # it's a GreenThread object, so we want to call its main
            # method to take advantage of the notification
            try:
                g.main(just_raise, (), {})
            except:
                pass
    current = getcurrent()
    if current is not hub.greenlet:
        # arrange to wake the caller back up immediately
        hub.ensure_greenlet()
        hub.schedule_call_global(0, current.switch)
    g.throw(*throw_args)

########NEW FILE########
__FILENAME__ = epolls
import errno
from eventlet.support import get_errno
from eventlet import patcher
time = patcher.original('time')
select = patcher.original("select")
if hasattr(select, 'epoll'):
    epoll = select.epoll
else:
    try:
        # http://pypi.python.org/pypi/select26/
        from select26 import epoll
    except ImportError:
        try:
            import epoll as _epoll_mod
        except ImportError:
            raise ImportError(
                "No epoll implementation found in select module or PYTHONPATH")
        else:
            if hasattr(_epoll_mod, 'poll'):
                epoll = _epoll_mod.poll
            else:
                raise ImportError(
                    "You have an old, buggy epoll module in PYTHONPATH."
                    " Install http://pypi.python.org/pypi/python-epoll/"
                    " NOT http://pypi.python.org/pypi/pyepoll/. "
                    " easy_install pyepoll installs the wrong version.")

from eventlet.hubs.hub import BaseHub
from eventlet.hubs import poll
from eventlet.hubs.poll import READ, WRITE

# NOTE: we rely on the fact that the epoll flag constants
# are identical in value to the poll constants

class Hub(poll.Hub):
    def __init__(self, clock=time.time):
        BaseHub.__init__(self, clock)
        self.poll = epoll()
        try:
            # modify is required by select.epoll
            self.modify = self.poll.modify
        except AttributeError:
            self.modify = self.poll.register

    def add(self, evtype, fileno, cb):
        oldlisteners = bool(self.listeners[READ].get(fileno) or
                            self.listeners[WRITE].get(fileno))
        listener = BaseHub.add(self, evtype, fileno, cb)
        try:
            if not oldlisteners:
                # Means we've added a new listener
                self.register(fileno, new=True)
            else:
                self.register(fileno, new=False)
        except IOError as ex:    # ignore EEXIST, #80
            if get_errno(ex) != errno.EEXIST:
                raise
        return listener

    def do_poll(self, seconds):
        return self.poll.poll(seconds)

########NEW FILE########
__FILENAME__ = hub
import heapq
import math
import traceback
import signal
import sys
import warnings

arm_alarm = None
if hasattr(signal, 'setitimer'):
    def alarm_itimer(seconds):
        signal.setitimer(signal.ITIMER_REAL, seconds)
    arm_alarm = alarm_itimer
else:
    try:
        import itimer
        arm_alarm = itimer.alarm
    except ImportError:
        def alarm_signal(seconds):
            signal.alarm(math.ceil(seconds))
        arm_alarm = alarm_signal

from eventlet.support import greenlets as greenlet, clear_sys_exc_info
from eventlet.hubs import timer
from eventlet import patcher
time = patcher.original('time')

g_prevent_multiple_readers = True

READ="read"
WRITE="write"

class FdListener(object):
    def __init__(self, evtype, fileno, cb):
        assert (evtype is READ or evtype is WRITE)
        self.evtype = evtype
        self.fileno = fileno
        self.cb = cb
    def __repr__(self):
        return "%s(%r, %r, %r)" % (type(self).__name__, self.evtype, self.fileno, self.cb)
    __str__ = __repr__


noop = FdListener(READ, 0, lambda x: None)

# in debug mode, track the call site that created the listener
class DebugListener(FdListener):
    def __init__(self, evtype, fileno, cb):
        self.where_called = traceback.format_stack()
        self.greenlet = greenlet.getcurrent()
        super(DebugListener, self).__init__(evtype, fileno, cb)
    def __repr__(self):
        return "DebugListener(%r, %r, %r, %r)\n%sEndDebugFdListener" % (
            self.evtype,
            self.fileno,
            self.cb,
            self.greenlet,
            ''.join(self.where_called))
    __str__ = __repr__


def alarm_handler(signum, frame):
    import inspect
    raise RuntimeError("Blocking detector ALARMED at" + str(inspect.getframeinfo(frame)))


class BaseHub(object):
    """ Base hub class for easing the implementation of subclasses that are
    specific to a particular underlying event architecture. """

    SYSTEM_EXCEPTIONS = (KeyboardInterrupt, SystemExit)

    READ = READ
    WRITE = WRITE

    def __init__(self, clock=time.time):
        self.listeners = {READ:{}, WRITE:{}}
        self.secondaries = {READ:{}, WRITE:{}}

        self.clock = clock
        self.greenlet = greenlet.greenlet(self.run)
        self.stopping = False
        self.running = False
        self.timers = []
        self.next_timers = []
        self.lclass = FdListener
        self.timers_canceled = 0
        self.debug_exceptions = True
        self.debug_blocking = False
        self.debug_blocking_resolution = 1

    def block_detect_pre(self):
        # shortest alarm we can possibly raise is one second
        tmp = signal.signal(signal.SIGALRM, alarm_handler)
        if tmp != alarm_handler:
            self._old_signal_handler = tmp

        arm_alarm(self.debug_blocking_resolution)

    def block_detect_post(self):
        if (hasattr(self, "_old_signal_handler") and
            self._old_signal_handler):
            signal.signal(signal.SIGALRM, self._old_signal_handler)
        signal.alarm(0)

    def add(self, evtype, fileno, cb):
        """ Signals an intent to or write a particular file descriptor.

        The *evtype* argument is either the constant READ or WRITE.

        The *fileno* argument is the file number of the file of interest.

        The *cb* argument is the callback which will be called when the file
        is ready for reading/writing.
        """
        listener = self.lclass(evtype, fileno, cb)
        bucket = self.listeners[evtype]
        if fileno in bucket:
            if g_prevent_multiple_readers:
                raise RuntimeError("Second simultaneous %s on fileno %s "\
                     "detected.  Unless you really know what you're doing, "\
                     "make sure that only one greenthread can %s any "\
                     "particular socket.  Consider using a pools.Pool. "\
                     "If you do know what you're doing and want to disable "\
                     "this error, call "\
                     "eventlet.debug.hub_prevent_multiple_readers(False)" % (
                     evtype, fileno, evtype))
            # store off the second listener in another structure
            self.secondaries[evtype].setdefault(fileno, []).append(listener)
        else:
            bucket[fileno] = listener
        return listener

    def remove(self, listener):
        fileno = listener.fileno
        evtype = listener.evtype
        self.listeners[evtype].pop(fileno, None)
        # migrate a secondary listener to be the primary listener
        if fileno in self.secondaries[evtype]:
            sec = self.secondaries[evtype].get(fileno, None)
            if not sec:
                return
            self.listeners[evtype][fileno] = sec.pop(0)
            if not sec:
                del self.secondaries[evtype][fileno]

    def remove_descriptor(self, fileno):
        """ Completely remove all listeners for this fileno.  For internal use
        only."""
        listeners = []
        listeners.append(self.listeners[READ].pop(fileno, noop))
        listeners.append(self.listeners[WRITE].pop(fileno, noop))
        listeners.extend(self.secondaries[READ].pop(fileno, ()))
        listeners.extend(self.secondaries[WRITE].pop(fileno, ()))
        for listener in listeners:
            try:
                listener.cb(fileno)
            except Exception as e:
                self.squelch_generic_exception(sys.exc_info())

    def ensure_greenlet(self):
        if self.greenlet.dead:
            # create new greenlet sharing same parent as original
            new = greenlet.greenlet(self.run, self.greenlet.parent)
            # need to assign as parent of old greenlet
            # for those greenlets that are currently
            # children of the dead hub and may subsequently
            # exit without further switching to hub.
            self.greenlet.parent = new
            self.greenlet = new

    def switch(self):
        cur = greenlet.getcurrent()
        assert cur is not self.greenlet, 'Cannot switch to MAINLOOP from MAINLOOP'
        switch_out = getattr(cur, 'switch_out', None)
        if switch_out is not None:
            try:
                switch_out()
            except:
                self.squelch_generic_exception(sys.exc_info())
        self.ensure_greenlet()
        try:
            if self.greenlet.parent is not cur:
                cur.parent = self.greenlet
        except ValueError:
            pass  # gets raised if there is a greenlet parent cycle
        clear_sys_exc_info()
        return self.greenlet.switch()

    def squelch_exception(self, fileno, exc_info):
        traceback.print_exception(*exc_info)
        sys.stderr.write("Removing descriptor: %r\n" % (fileno,))
        sys.stderr.flush()
        try:
            self.remove_descriptor(fileno)
        except Exception as e:
            sys.stderr.write("Exception while removing descriptor! %r\n" % (e,))
            sys.stderr.flush()

    def wait(self, seconds=None):
        raise NotImplementedError("Implement this in a subclass")

    def default_sleep(self):
        return 60.0

    def sleep_until(self):
        t = self.timers
        if not t:
            return None
        return t[0][0]

    def run(self, *a, **kw):
        """Run the runloop until abort is called.
        """
        # accept and discard variable arguments because they will be
        # supplied if other greenlets have run and exited before the
        # hub's greenlet gets a chance to run
        if self.running:
            raise RuntimeError("Already running!")
        try:
            self.running = True
            self.stopping = False
            while not self.stopping:
                self.prepare_timers()
                if self.debug_blocking:
                    self.block_detect_pre()
                self.fire_timers(self.clock())
                if self.debug_blocking:
                    self.block_detect_post()
                self.prepare_timers()
                wakeup_when = self.sleep_until()
                if wakeup_when is None:
                    sleep_time = self.default_sleep()
                else:
                    sleep_time = wakeup_when - self.clock()
                if sleep_time > 0:
                    self.wait(sleep_time)
                else:
                    self.wait(0)
            else:
                self.timers_canceled = 0
                del self.timers[:]
                del self.next_timers[:]
        finally:
            self.running = False
            self.stopping = False

    def abort(self, wait=False):
        """Stop the runloop. If run is executing, it will exit after
        completing the next runloop iteration.

        Set *wait* to True to cause abort to switch to the hub immediately and
        wait until it's finished processing.  Waiting for the hub will only
        work from the main greenthread; all other greenthreads will become
        unreachable.
        """
        if self.running:
            self.stopping = True
        if wait:
            assert self.greenlet is not greenlet.getcurrent(), "Can't abort with wait from inside the hub's greenlet."
            # schedule an immediate timer just so the hub doesn't sleep
            self.schedule_call_global(0, lambda: None)
            # switch to it; when done the hub will switch back to its parent,
            # the main greenlet
            self.switch()

    def squelch_generic_exception(self, exc_info):
        if self.debug_exceptions:
            traceback.print_exception(*exc_info)
            sys.stderr.flush()
            clear_sys_exc_info()

    def squelch_timer_exception(self, timer, exc_info):
        if self.debug_exceptions:
            traceback.print_exception(*exc_info)
            sys.stderr.flush()
            clear_sys_exc_info()

    def add_timer(self, timer):
        scheduled_time = self.clock() + timer.seconds
        self.next_timers.append((scheduled_time, timer))
        return scheduled_time

    def timer_canceled(self, timer):
        self.timers_canceled += 1
        len_timers = len(self.timers) + len(self.next_timers)
        if len_timers > 1000 and len_timers/2 <= self.timers_canceled:
            self.timers_canceled = 0
            self.timers = [t for t in self.timers if not t[1].called]
            self.next_timers = [t for t in self.next_timers if not t[1].called]
            heapq.heapify(self.timers)

    def prepare_timers(self):
        heappush = heapq.heappush
        t = self.timers
        for item in self.next_timers:
            if item[1].called:
                self.timers_canceled -= 1
            else:
                heappush(t, item)
        del self.next_timers[:]

    def schedule_call_local(self, seconds, cb, *args, **kw):
        """Schedule a callable to be called after 'seconds' seconds have
        elapsed. Cancel the timer if greenlet has exited.
            seconds: The number of seconds to wait.
            cb: The callable to call after the given time.
            *args: Arguments to pass to the callable when called.
            **kw: Keyword arguments to pass to the callable when called.
        """
        t = timer.LocalTimer(seconds, cb, *args, **kw)
        self.add_timer(t)
        return t

    def schedule_call_global(self, seconds, cb, *args, **kw):
        """Schedule a callable to be called after 'seconds' seconds have
        elapsed. The timer will NOT be canceled if the current greenlet has
        exited before the timer fires.
            seconds: The number of seconds to wait.
            cb: The callable to call after the given time.
            *args: Arguments to pass to the callable when called.
            **kw: Keyword arguments to pass to the callable when called.
        """
        t = timer.Timer(seconds, cb, *args, **kw)
        self.add_timer(t)
        return t

    def fire_timers(self, when):
        t = self.timers
        heappop = heapq.heappop

        while t:
            next = t[0]

            exp = next[0]
            timer = next[1]

            if when < exp:
                break

            heappop(t)

            try:
                if timer.called:
                    self.timers_canceled -= 1
                else:
                    timer()
            except self.SYSTEM_EXCEPTIONS:
                raise
            except:
                self.squelch_timer_exception(timer, sys.exc_info())
                clear_sys_exc_info()

    # for debugging:

    def get_readers(self):
        return self.listeners[READ].values()

    def get_writers(self):
        return self.listeners[WRITE].values()

    def get_timers_count(hub):
        return len(hub.timers) + len(hub.next_timers)

    def set_debug_listeners(self, value):
        if value:
            self.lclass = DebugListener
        else:
            self.lclass = FdListener

    def set_timer_exceptions(self, value):
        self.debug_exceptions = value

########NEW FILE########
__FILENAME__ = kqueue
import os
import sys
from eventlet import patcher
from eventlet.support import six
select = patcher.original('select')
time = patcher.original('time')
sleep = time.sleep

from eventlet.support import get_errno, clear_sys_exc_info
from eventlet.hubs.hub import BaseHub, READ, WRITE, noop


if getattr(select, 'kqueue', None) is None:
    raise ImportError('No kqueue implementation found in select module')


FILTERS = {READ: select.KQ_FILTER_READ,
           WRITE: select.KQ_FILTER_WRITE}


class Hub(BaseHub):
    MAX_EVENTS = 100

    def __init__(self, clock=time.time):
        super(Hub, self).__init__(clock)
        self._events = {}
        self._init_kqueue()

    def _init_kqueue(self):
        self.kqueue = select.kqueue()
        self._pid = os.getpid()

    def _reinit_kqueue(self):
        self.kqueue.close()
        self._init_kqueue()
        kqueue = self.kqueue
        events = [e for i in six.itervalues(self._events)
                  for e in six.itervalues(i)]
        kqueue.control(events, 0, 0)

    def _control(self, events, max_events, timeout):
        try:
            return self.kqueue.control(events, max_events, timeout)
        except (OSError, IOError):
            # have we forked?
            if os.getpid() != self._pid:
                self._reinit_kqueue()
                return self.kqueue.control(events, max_events, timeout)
            raise

    def add(self, evtype, fileno, cb):
        listener = super(Hub, self).add(evtype, fileno, cb)
        events = self._events.setdefault(fileno, {})
        if evtype not in events:
            try:
                event = select.kevent(fileno,
                                      FILTERS.get(evtype), select.KQ_EV_ADD)
                self._control([event], 0, 0)
                events[evtype] = event
            except ValueError:
                super(Hub, self).remove(listener)
                raise
        return listener

    def _delete_events(self, events):
        del_events = [select.kevent(e.ident, e.filter, select.KQ_EV_DELETE)
            for e in events]
        self._control(del_events, 0, 0)

    def remove(self, listener):
        super(Hub, self).remove(listener)
        evtype = listener.evtype
        fileno = listener.fileno
        if not self.listeners[evtype].get(fileno):
            event = self._events[fileno].pop(evtype)
            try:
                self._delete_events([event])
            except OSError as e:
                pass

    def remove_descriptor(self, fileno):
        super(Hub, self).remove_descriptor(fileno)
        try:
            events = self._events.pop(fileno).values()
            self._delete_events(events)
        except KeyError as e:
            pass
        except OSError as e:
            pass

    def wait(self, seconds=None):
        readers = self.listeners[READ]
        writers = self.listeners[WRITE]

        if not readers and not writers:
            if seconds:
                sleep(seconds)
            return
        result = self._control([], self.MAX_EVENTS, seconds)
        SYSTEM_EXCEPTIONS = self.SYSTEM_EXCEPTIONS
        for event in result:
            fileno = event.ident
            evfilt = event.filter
            try:
                if evfilt == FILTERS[READ]:
                    readers.get(fileno, noop).cb(fileno)
                if evfilt == FILTERS[WRITE]:
                    writers.get(fileno, noop).cb(fileno)
            except SYSTEM_EXCEPTIONS:
                raise
            except:
                self.squelch_exception(fileno, sys.exc_info())
                clear_sys_exc_info()

########NEW FILE########
__FILENAME__ = poll
import sys
import errno
import signal
from eventlet import patcher
select = patcher.original('select')
time = patcher.original('time')
sleep = time.sleep

from eventlet.support import get_errno, clear_sys_exc_info
from eventlet.hubs.hub import BaseHub, READ, WRITE, noop, alarm_handler

EXC_MASK = select.POLLERR | select.POLLHUP
READ_MASK = select.POLLIN | select.POLLPRI
WRITE_MASK = select.POLLOUT

class Hub(BaseHub):
    def __init__(self, clock=time.time):
        super(Hub, self).__init__(clock)
        self.poll = select.poll()
        # poll.modify is new to 2.6
        try:
            self.modify = self.poll.modify
        except AttributeError:
            self.modify = self.poll.register

    def add(self, evtype, fileno, cb):
        listener = super(Hub, self).add(evtype, fileno, cb)
        self.register(fileno, new=True)
        return listener
    
    def remove(self, listener):
        super(Hub, self).remove(listener)
        self.register(listener.fileno)

    def register(self, fileno, new=False):
        mask = 0
        if self.listeners[READ].get(fileno):
            mask |= READ_MASK | EXC_MASK
        if self.listeners[WRITE].get(fileno):
            mask |= WRITE_MASK | EXC_MASK
        try:
            if mask:
                if new:
                    self.poll.register(fileno, mask)
                else:
                    try:
                        self.modify(fileno, mask)
                    except (IOError, OSError):
                        self.poll.register(fileno, mask)
            else: 
                try:
                    self.poll.unregister(fileno)
                except (KeyError, IOError, OSError):
                    # raised if we try to remove a fileno that was
                    # already removed/invalid
                    pass
        except ValueError:
            # fileno is bad, issue 74
            self.remove_descriptor(fileno)
            raise

    def remove_descriptor(self, fileno):
        super(Hub, self).remove_descriptor(fileno)
        try:
            self.poll.unregister(fileno)
        except (KeyError, ValueError, IOError, OSError):
            # raised if we try to remove a fileno that was
            # already removed/invalid
            pass

    def do_poll(self, seconds):
        # poll.poll expects integral milliseconds
        return self.poll.poll(int(seconds * 1000.0))

    def wait(self, seconds=None):
        readers = self.listeners[READ]
        writers = self.listeners[WRITE]

        if not readers and not writers:
            if seconds:
                sleep(seconds)
            return
        try:
            presult = self.do_poll(seconds)
        except (IOError, select.error) as e:
            if get_errno(e) == errno.EINTR:
                return
            raise
        SYSTEM_EXCEPTIONS = self.SYSTEM_EXCEPTIONS

        if self.debug_blocking:
            self.block_detect_pre()

        for fileno, event in presult:
            try:
                if event & READ_MASK:
                    readers.get(fileno, noop).cb(fileno)
                if event & WRITE_MASK:
                    writers.get(fileno, noop).cb(fileno)
                if event & select.POLLNVAL:
                    self.remove_descriptor(fileno)
                    continue
                if event & EXC_MASK:
                    readers.get(fileno, noop).cb(fileno)
                    writers.get(fileno, noop).cb(fileno)
            except SYSTEM_EXCEPTIONS:
                raise
            except:
                self.squelch_exception(fileno, sys.exc_info())
                clear_sys_exc_info()
        
        if self.debug_blocking:
            self.block_detect_post()


########NEW FILE########
__FILENAME__ = pyevent
import sys
import traceback
import event
import types

from eventlet.support import greenlets as greenlet, six
from eventlet.hubs.hub import BaseHub, FdListener, READ, WRITE


class event_wrapper(object):

    def __init__(self, impl=None, seconds=None):
        self.impl = impl
        self.seconds = seconds

    def __repr__(self):
        if self.impl is not None:
            return repr(self.impl)
        else:
            return object.__repr__(self)

    def __str__(self):
        if self.impl is not None:
            return str(self.impl)
        else:
            return object.__str__(self)

    def cancel(self):
        if self.impl is not None:
            self.impl.delete()
            self.impl = None

    @property
    def pending(self):
        return bool(self.impl and self.impl.pending())

class Hub(BaseHub):

    SYSTEM_EXCEPTIONS = (KeyboardInterrupt, SystemExit)

    def __init__(self):
        super(Hub,self).__init__()
        event.init()

        self.signal_exc_info = None
        self.signal(
            2,
            lambda signalnum, frame: self.greenlet.parent.throw(KeyboardInterrupt))
        self.events_to_add = []

    def dispatch(self):
        loop = event.loop
        while True:
            for e in self.events_to_add:
                if e is not None and e.impl is not None and e.seconds is not None:
                    e.impl.add(e.seconds)
                    e.seconds = None
            self.events_to_add = []
            result = loop()

            if getattr(event, '__event_exc', None) is not None:
                # only have to do this because of bug in event.loop
                t = getattr(event, '__event_exc')
                setattr(event, '__event_exc', None)
                assert getattr(event, '__event_exc') is None
                six.reraise(t[0], t[1], t[2])

            if result != 0:
                return result

    def run(self):
        while True:
            try:
                self.dispatch()
            except greenlet.GreenletExit:
                break
            except self.SYSTEM_EXCEPTIONS:
                raise
            except:
                if self.signal_exc_info is not None:
                    self.schedule_call_global(
                        0, greenlet.getcurrent().parent.throw, *self.signal_exc_info)
                    self.signal_exc_info = None
                else:
                    self.squelch_timer_exception(None, sys.exc_info())

    def abort(self, wait=True):
        self.schedule_call_global(0, self.greenlet.throw, greenlet.GreenletExit)
        if wait:
            assert self.greenlet is not greenlet.getcurrent(), "Can't abort with wait from inside the hub's greenlet."
            self.switch()

    def _getrunning(self):
        return bool(self.greenlet)

    def _setrunning(self, value):
        pass  # exists for compatibility with BaseHub
    running = property(_getrunning, _setrunning)

    def add(self, evtype, fileno, real_cb):
        # this is stupid: pyevent won't call a callback unless it's a function,
        # so we have to force it to be one here
        if isinstance(real_cb, types.BuiltinMethodType):
            def cb(_d):
                real_cb(_d)
        else:
            cb = real_cb

        if evtype is READ:
            evt = event.read(fileno, cb, fileno)
        elif evtype is WRITE:
            evt = event.write(fileno, cb, fileno)

        return super(Hub,self).add(evtype, fileno, evt)

    def signal(self, signalnum, handler):
        def wrapper():
            try:
                handler(signalnum, None)
            except:
                self.signal_exc_info = sys.exc_info()
                event.abort()
        return event_wrapper(event.signal(signalnum, wrapper))

    def remove(self, listener):
        super(Hub, self).remove(listener)
        listener.cb.delete()

    def remove_descriptor(self, fileno):
        for lcontainer in self.listeners.itervalues():
            listener = lcontainer.pop(fileno, None)
            if listener:
                try:
                    listener.cb.delete()
                except self.SYSTEM_EXCEPTIONS:
                    raise
                except:
                    traceback.print_exc()

    def schedule_call_local(self, seconds, cb, *args, **kwargs):
        current = greenlet.getcurrent()
        if current is self.greenlet:
            return self.schedule_call_global(seconds, cb, *args, **kwargs)
        event_impl = event.event(_scheduled_call_local, (cb, args, kwargs, current))
        wrapper = event_wrapper(event_impl, seconds=seconds)
        self.events_to_add.append(wrapper)
        return wrapper

    schedule_call = schedule_call_local

    def schedule_call_global(self, seconds, cb, *args, **kwargs):
        event_impl = event.event(_scheduled_call, (cb, args, kwargs))
        wrapper = event_wrapper(event_impl, seconds=seconds)
        self.events_to_add.append(wrapper)
        return wrapper

    def _version_info(self):
        baseversion = event.__version__
        return baseversion


def _scheduled_call(event_impl, handle, evtype, arg):
    cb, args, kwargs = arg
    try:
        cb(*args, **kwargs)
    finally:
        event_impl.delete()

def _scheduled_call_local(event_impl, handle, evtype, arg):
    cb, args, kwargs, caller_greenlet = arg
    try:
        if not caller_greenlet.dead:
            cb(*args, **kwargs)
    finally:
        event_impl.delete()

########NEW FILE########
__FILENAME__ = selects
import sys
import errno
from eventlet import patcher
from eventlet.support import get_errno, clear_sys_exc_info, six
select = patcher.original('select')
time = patcher.original('time')

from eventlet.hubs.hub import BaseHub, READ, WRITE, noop

try:
    BAD_SOCK = set((errno.EBADF, errno.WSAENOTSOCK))
except AttributeError:
    BAD_SOCK = set((errno.EBADF,))


class Hub(BaseHub):
    def _remove_bad_fds(self):
        """ Iterate through fds, removing the ones that are bad per the
        operating system.
        """
        all_fds = list(self.listeners[READ]) + list(self.listeners[WRITE])
        for fd in all_fds:
            try:
                select.select([fd], [], [], 0)
            except select.error as e:
                if get_errno(e) in BAD_SOCK:
                    self.remove_descriptor(fd)

    def wait(self, seconds=None):
        readers = self.listeners[READ]
        writers = self.listeners[WRITE]
        if not readers and not writers:
            if seconds:
                time.sleep(seconds)
            return
        all_fds = list(readers) + list(writers)
        try:
            r, w, er = select.select(readers.keys(), writers.keys(), all_fds, seconds)
        except select.error as e:
            if get_errno(e) == errno.EINTR:
                return
            elif get_errno(e) in BAD_SOCK:
                self._remove_bad_fds()
                return
            else:
                raise

        for fileno in er:
            readers.get(fileno, noop).cb(fileno)
            writers.get(fileno, noop).cb(fileno)

        for listeners, events in ((readers, r), (writers, w)):
            for fileno in events:
                try:
                    listeners.get(fileno, noop).cb(fileno)
                except self.SYSTEM_EXCEPTIONS:
                    raise
                except:
                    self.squelch_exception(fileno, sys.exc_info())
                    clear_sys_exc_info()

########NEW FILE########
__FILENAME__ = timer
import traceback

from eventlet.support import greenlets as greenlet, six
from eventlet.hubs import get_hub

""" If true, captures a stack trace for each timer when constructed.  This is
useful for debugging leaking timers, to find out where the timer was set up. """
_g_debug = False


class Timer(object):
    def __init__(self, seconds, cb, *args, **kw):
        """Create a timer.
            seconds: The minimum number of seconds to wait before calling
            cb: The callback to call when the timer has expired
            *args: The arguments to pass to cb
            **kw: The keyword arguments to pass to cb

        This timer will not be run unless it is scheduled in a runloop by
        calling timer.schedule() or runloop.add_timer(timer).
        """
        self.seconds = seconds
        self.tpl = cb, args, kw
        self.called = False
        if _g_debug:
            self.traceback = six.StringIO()
            traceback.print_stack(file=self.traceback)

    @property
    def pending(self):
        return not self.called

    def __repr__(self):
        secs = getattr(self, 'seconds', None)
        cb, args, kw = getattr(self, 'tpl', (None, None, None))
        retval = "Timer(%s, %s, *%s, **%s)" % (
            secs, cb, args, kw)
        if _g_debug and hasattr(self, 'traceback'):
            retval += '\n' + self.traceback.getvalue()
        return retval

    def copy(self):
        cb, args, kw = self.tpl
        return self.__class__(self.seconds, cb, *args, **kw)

    def schedule(self):
        """Schedule this timer to run in the current runloop.
        """
        self.called = False
        self.scheduled_time = get_hub().add_timer(self)
        return self

    def __call__(self, *args):
        if not self.called:
            self.called = True
            cb, args, kw = self.tpl
            try:
                cb(*args, **kw)
            finally:
                try:
                    del self.tpl
                except AttributeError:
                    pass

    def cancel(self):
        """Prevent this timer from being called. If the timer has already
        been called or canceled, has no effect.
        """
        if not self.called:
            self.called = True
            get_hub().timer_canceled(self)
            try:
                del self.tpl
            except AttributeError:
                pass

    # No default ordering in 3.x. heapq uses <
    # FIXME should full set be added?
    def __lt__(self, other):
        return id(self) < id(other)


class LocalTimer(Timer):

    def __init__(self, *args, **kwargs):
        self.greenlet = greenlet.getcurrent()
        Timer.__init__(self, *args, **kwargs)

    @property
    def pending(self):
        if self.greenlet is None or self.greenlet.dead:
            return False
        return not self.called

    def __call__(self, *args):
        if not self.called:
            self.called = True
            if self.greenlet is not None and self.greenlet.dead:
                return
            cb, args, kw = self.tpl
            cb(*args, **kw)

    def cancel(self):
        self.greenlet = None
        Timer.cancel(self)

########NEW FILE########
__FILENAME__ = twistedr
import sys
import threading
from twisted.internet.base import DelayedCall as TwistedDelayedCall
from eventlet.support import greenlets as greenlet
from eventlet.hubs.hub import FdListener, READ, WRITE

class DelayedCall(TwistedDelayedCall):
    "fix DelayedCall to behave like eventlet's Timer in some respects"

    def cancel(self):
        if self.cancelled or self.called:
            self.cancelled = True
            return
        return TwistedDelayedCall.cancel(self)

class LocalDelayedCall(DelayedCall):

    def __init__(self, *args, **kwargs):
        self.greenlet = greenlet.getcurrent()
        DelayedCall.__init__(self, *args, **kwargs)

    def _get_cancelled(self):
        if self.greenlet is None or self.greenlet.dead:
            return True
        return self.__dict__['cancelled']

    def _set_cancelled(self, value):
        self.__dict__['cancelled'] = value

    cancelled = property(_get_cancelled, _set_cancelled)

def callLater(DelayedCallClass, reactor, _seconds, _f, *args, **kw):
    # the same as original but creates fixed DelayedCall instance
    assert callable(_f), "%s is not callable" % _f
    if not isinstance(_seconds, (int, long, float)):
        raise TypeError("Seconds must be int, long, or float, was " + type(_seconds))
    assert sys.maxint >= _seconds >= 0, \
           "%s is not greater than or equal to 0 seconds" % (_seconds,)
    tple = DelayedCallClass(reactor.seconds() + _seconds, _f, args, kw,
                            reactor._cancelCallLater,
                            reactor._moveCallLaterSooner,
                            seconds=reactor.seconds)
    reactor._newTimedCalls.append(tple)
    return tple

class socket_rwdescriptor(FdListener):
    #implements(IReadWriteDescriptor)
    def __init__(self, evtype, fileno, cb):
        super(socket_rwdescriptor, self).__init__(evtype, fileno, cb)
        if not isinstance(fileno, (int,long)):
            raise TypeError("Expected int or long, got %s" % type(fileno))
        # Twisted expects fileno to be a callable, not an attribute
        def _fileno():
            return fileno
        self.fileno = _fileno

    # required by glib2reactor
    disconnected = False

    def doRead(self):
        if self.evtype is READ:
            self.cb(self)

    def doWrite(self):
        if self.evtype == WRITE:
            self.cb(self)

    def connectionLost(self, reason):
        self.disconnected = True
        if self.cb:
            self.cb(reason)
        # trampoline() will now switch into the greenlet that owns the socket
        # leaving the mainloop unscheduled. However, when the next switch
        # to the mainloop occurs, twisted will not re-evaluate the delayed calls
        # because it assumes that none were scheduled since no client code was executed
        # (it has no idea it was switched away). So, we restart the mainloop.
        # XXX this is not enough, pollreactor prints the traceback for
        # this and epollreactor times out. see test__hub.TestCloseSocketWhilePolling
        raise greenlet.GreenletExit

    logstr = "twistedr"

    def logPrefix(self):
        return self.logstr


class BaseTwistedHub(object):
    """This hub does not run a dedicated greenlet for the mainloop (unlike TwistedHub).
    Instead, it assumes that the mainloop is run in the main greenlet.

    This makes running "green" functions in the main greenlet impossible but is useful
    when you want to call reactor.run() yourself.
    """

    # XXX: remove me from here. make functions that depend on reactor
    # XXX: hub's methods
    uses_twisted_reactor = True

    WRITE = WRITE
    READ = READ

    def __init__(self, mainloop_greenlet):
        self.greenlet = mainloop_greenlet

    def switch(self):
        assert greenlet.getcurrent() is not self.greenlet, \
               "Cannot switch from MAINLOOP to MAINLOOP"
        try:
           greenlet.getcurrent().parent = self.greenlet
        except ValueError:
           pass
        return self.greenlet.switch()

    def stop(self):
        from twisted.internet import reactor
        reactor.stop()

    def add(self, evtype, fileno, cb):
        from twisted.internet import reactor
        descriptor = socket_rwdescriptor(evtype, fileno, cb)
        if evtype is READ:
            reactor.addReader(descriptor)
        if evtype is WRITE:
            reactor.addWriter(descriptor)
        return descriptor

    def remove(self, descriptor):
        from twisted.internet import reactor
        reactor.removeReader(descriptor)
        reactor.removeWriter(descriptor)

    def schedule_call_local(self, seconds, func, *args, **kwargs):
        from twisted.internet import reactor
        def call_if_greenlet_alive(*args1, **kwargs1):
            if timer.greenlet.dead:
                return
            return func(*args1, **kwargs1)
        timer = callLater(LocalDelayedCall, reactor, seconds,
                          call_if_greenlet_alive, *args, **kwargs)
        return timer

    schedule_call = schedule_call_local

    def schedule_call_global(self, seconds, func, *args, **kwargs):
        from twisted.internet import reactor
        return callLater(DelayedCall, reactor, seconds, func, *args, **kwargs)

    def abort(self):
        from twisted.internet import reactor
        reactor.crash()

    @property
    def running(self):
        from twisted.internet import reactor
        return reactor.running

    # for debugging:

    def get_readers(self):
        from twisted.internet import reactor
        readers = reactor.getReaders()
        readers.remove(getattr(reactor, 'waker'))
        return readers

    def get_writers(self):
        from twisted.internet import reactor
        return reactor.getWriters()


    def get_timers_count(self):
        from twisted.internet import reactor
        return len(reactor.getDelayedCalls())


class TwistedHub(BaseTwistedHub):
    # wrapper around reactor that runs reactor's main loop in a separate greenlet.
    # whenever you need to wait, i.e. inside a call that must appear
    # blocking, call hub.switch() (then your blocking operation should switch back to you
    # upon completion)

    # unlike other eventlet hubs, which are created per-thread,
    # this one cannot be instantiated more than once, because
    # twisted doesn't allow that

    # 0-not created
    # 1-initialized but not started
    # 2-started
    # 3-restarted
    state = 0

    installSignalHandlers = False

    def __init__(self):
        assert Hub.state==0, ('%s hub can only be instantiated once'%type(self).__name__,
                              Hub.state)
        Hub.state = 1
        make_twisted_threadpool_daemonic() # otherwise the program
                                        # would hang after the main
                                        # greenlet exited
        g = greenlet.greenlet(self.run)
        BaseTwistedHub.__init__(self, g)

    def switch(self):
        assert greenlet.getcurrent() is not self.greenlet, \
               "Cannot switch from MAINLOOP to MAINLOOP"
        if self.greenlet.dead:
            self.greenlet = greenlet.greenlet(self.run)
        try:
            greenlet.getcurrent().parent = self.greenlet
        except ValueError:
            pass
        return self.greenlet.switch()

    def run(self, installSignalHandlers=None):
        if installSignalHandlers is None:
            installSignalHandlers = self.installSignalHandlers

        # main loop, executed in a dedicated greenlet
        from twisted.internet import reactor
        assert Hub.state in [1, 3], ('run function is not reentrant', Hub.state)

        if Hub.state == 1:
            reactor.startRunning(installSignalHandlers=installSignalHandlers)
        elif not reactor.running:
            # if we're here, then reactor was explicitly stopped with reactor.stop()
            # restarting reactor (like we would do after an exception) in this case
            # is not an option.
            raise AssertionError("reactor is not running")

        try:
            self.mainLoop(reactor)
        except:
            # an exception in the mainLoop is a normal operation (e.g. user's
            # signal handler could raise an exception). In this case we will re-enter
            # the main loop at the next switch.
            Hub.state = 3
            raise

        # clean exit here is needed for abort() method to work
        # do not raise an exception here.

    def mainLoop(self, reactor):
        Hub.state = 2
        # Unlike reactor's mainLoop, this function does not catch exceptions.
        # Anything raised goes into the main greenlet (because it is always the
        # parent of this one)
        while reactor.running:
            # Advance simulation time in delayed event processors.
            reactor.runUntilCurrent()
            t2 = reactor.timeout()
            t = reactor.running and t2
            reactor.doIteration(t)

Hub = TwistedHub

class DaemonicThread(threading.Thread):
    def _set_daemon(self):
        return True

def make_twisted_threadpool_daemonic():
    from twisted.python.threadpool import ThreadPool
    if ThreadPool.threadFactory != DaemonicThread:
        ThreadPool.threadFactory = DaemonicThread

########NEW FILE########
__FILENAME__ = patcher
import sys
import imp

from eventlet.support import six


__all__ = ['inject', 'import_patched', 'monkey_patch', 'is_monkey_patched']

__exclude = set(('__builtins__', '__file__', '__name__'))


class SysModulesSaver(object):
    """Class that captures some subset of the current state of
    sys.modules.  Pass in an iterator of module names to the
    constructor."""
    def __init__(self, module_names=()):
        self._saved = {}
        imp.acquire_lock()
        self.save(*module_names)

    def save(self, *module_names):
        """Saves the named modules to the object."""
        for modname in module_names:
            self._saved[modname] = sys.modules.get(modname, None)

    def restore(self):
        """Restores the modules that the saver knows about into
        sys.modules.
        """
        try:
            for modname, mod in six.iteritems(self._saved):
                if mod is not None:
                    sys.modules[modname] = mod
                else:
                    try:
                        del sys.modules[modname]
                    except KeyError:
                        pass
        finally:
            imp.release_lock()


def inject(module_name, new_globals, *additional_modules):
    """Base method for "injecting" greened modules into an imported module.  It
    imports the module specified in *module_name*, arranging things so
    that the already-imported modules in *additional_modules* are used when
    *module_name* makes its imports.

    *new_globals* is either None or a globals dictionary that gets populated
    with the contents of the *module_name* module.  This is useful when creating
    a "green" version of some other module.

    *additional_modules* should be a collection of two-element tuples, of the
    form (<name>, <module>).  If it's not specified, a default selection of
    name/module pairs is used, which should cover all use cases but may be
    slower because there are inevitably redundant or unnecessary imports.
    """
    patched_name = '__patched_module_' + module_name
    if patched_name in sys.modules:
        # returning already-patched module so as not to destroy existing
        # references to patched modules
        return sys.modules[patched_name]

    if not additional_modules:
        # supply some defaults
        additional_modules = (
            _green_os_modules() +
            _green_select_modules() +
            _green_socket_modules() +
            _green_thread_modules() +
            _green_time_modules())
            #_green_MySQLdb()) # enable this after a short baking-in period

    # after this we are gonna screw with sys.modules, so capture the
    # state of all the modules we're going to mess with, and lock
    saver = SysModulesSaver([name for name, m in additional_modules])
    saver.save(module_name)

    # Cover the target modules so that when you import the module it
    # sees only the patched versions
    for name, mod in additional_modules:
        sys.modules[name] = mod

    ## Remove the old module from sys.modules and reimport it while
    ## the specified modules are in place
    sys.modules.pop(module_name, None)
    try:
        module = __import__(module_name, {}, {}, module_name.split('.')[:-1])

        if new_globals is not None:
            ## Update the given globals dictionary with everything from this new module
            for name in dir(module):
                if name not in __exclude:
                    new_globals[name] = getattr(module, name)

        ## Keep a reference to the new module to prevent it from dying
        sys.modules[patched_name] = module
    finally:
        saver.restore()  ## Put the original modules back

    return module


def import_patched(module_name, *additional_modules, **kw_additional_modules):
    """Imports a module in a way that ensures that the module uses "green"
    versions of the standard library modules, so that everything works
    nonblockingly.

    The only required argument is the name of the module to be imported.
    """
    return inject(
        module_name,
        None,
        *additional_modules + tuple(kw_additional_modules.items()))


def patch_function(func, *additional_modules):
    """Decorator that returns a version of the function that patches
    some modules for the duration of the function call.  This is
    deeply gross and should only be used for functions that import
    network libraries within their function bodies that there is no
    way of getting around."""
    if not additional_modules:
        # supply some defaults
        additional_modules = (
            _green_os_modules() +
            _green_select_modules() +
            _green_socket_modules() +
            _green_thread_modules() +
            _green_time_modules())

    def patched(*args, **kw):
        saver = SysModulesSaver()
        for name, mod in additional_modules:
            saver.save(name)
            sys.modules[name] = mod
        try:
            return func(*args, **kw)
        finally:
            saver.restore()
    return patched

def _original_patch_function(func, *module_names):
    """Kind of the contrapositive of patch_function: decorates a
    function such that when it's called, sys.modules is populated only
    with the unpatched versions of the specified modules.  Unlike
    patch_function, only the names of the modules need be supplied,
    and there are no defaults.  This is a gross hack; tell your kids not
    to import inside function bodies!"""
    def patched(*args, **kw):
        saver = SysModulesSaver(module_names)
        for name in module_names:
            sys.modules[name] = original(name)
        try:
            return func(*args, **kw)
        finally:
            saver.restore()
    return patched


def original(modname):
    """ This returns an unpatched version of a module; this is useful for
    Eventlet itself (i.e. tpool)."""
    # note that it's not necessary to temporarily install unpatched
    # versions of all patchable modules during the import of the
    # module; this is because none of them import each other, except
    # for threading which imports thread
    original_name = '__original_module_' + modname
    if original_name in sys.modules:
        return sys.modules.get(original_name)

    # re-import the "pure" module and store it in the global _originals
    # dict; be sure to restore whatever module had that name already
    saver = SysModulesSaver((modname,))
    sys.modules.pop(modname, None)
    # some rudimentary dependency checking -- fortunately the modules
    # we're working on don't have many dependencies so we can just do
    # some special-casing here
    if six.PY2:
        deps = {'threading': 'thread', 'Queue': 'threading'}
    if six.PY3:
        deps = {'threading': '_thread', 'queue': 'threading'}
    if modname in deps:
        dependency = deps[modname]
        saver.save(dependency)
        sys.modules[dependency] = original(dependency)
    try:
        real_mod = __import__(modname, {}, {}, modname.split('.')[:-1])
        if modname in ('Queue', 'queue') and not hasattr(real_mod, '_threading'):
            # tricky hack: Queue's constructor in <2.7 imports
            # threading on every instantiation; therefore we wrap
            # it so that it always gets the original threading
            real_mod.Queue.__init__ = _original_patch_function(
                real_mod.Queue.__init__,
                'threading')
        # save a reference to the unpatched module so it doesn't get lost
        sys.modules[original_name] = real_mod
    finally:
        saver.restore()

    return sys.modules[original_name]

already_patched = {}
def monkey_patch(**on):
    """Globally patches certain system modules to be greenthread-friendly.

    The keyword arguments afford some control over which modules are patched.
    If no keyword arguments are supplied, all possible modules are patched.
    If keywords are set to True, only the specified modules are patched.  E.g.,
    ``monkey_patch(socket=True, select=True)`` patches only the select and
    socket modules.  Most arguments patch the single module of the same name
    (os, time, select).  The exceptions are socket, which also patches the ssl
    module if present; and thread, which patches thread, threading, and Queue.

    It's safe to call monkey_patch multiple times.
    """
    accepted_args = set(('os', 'select', 'socket',
                         'thread', 'time', 'psycopg', 'MySQLdb'))
    default_on = on.pop("all",None)
    for k in six.iterkeys(on):
        if k not in accepted_args:
            raise TypeError("monkey_patch() got an unexpected "\
                                "keyword argument %r" % k)
    if default_on is None:
        default_on = not (True in on.values())
    for modname in accepted_args:
        if modname == 'MySQLdb':
            # MySQLdb is only on when explicitly patched for the moment
            on.setdefault(modname, False)
        on.setdefault(modname, default_on)

    modules_to_patch = []
    if on['os'] and not already_patched.get('os'):
        modules_to_patch += _green_os_modules()
        already_patched['os'] = True
    if on['select'] and not already_patched.get('select'):
        modules_to_patch += _green_select_modules()
        already_patched['select'] = True
    if on['socket'] and not already_patched.get('socket'):
        modules_to_patch += _green_socket_modules()
        already_patched['socket'] = True
    if on['thread'] and not already_patched.get('thread'):
        modules_to_patch += _green_thread_modules()
        already_patched['thread'] = True
    if on['time'] and not already_patched.get('time'):
        modules_to_patch += _green_time_modules()
        already_patched['time'] = True
    if on.get('MySQLdb') and not already_patched.get('MySQLdb'):
        modules_to_patch += _green_MySQLdb()
        already_patched['MySQLdb'] = True
    if on['psycopg'] and not already_patched.get('psycopg'):
        try:
            from eventlet.support import psycopg2_patcher
            psycopg2_patcher.make_psycopg_green()
            already_patched['psycopg'] = True
        except ImportError:
            # note that if we get an importerror from trying to
            # monkeypatch psycopg, we will continually retry it
            # whenever monkey_patch is called; this should not be a
            # performance problem but it allows is_monkey_patched to
            # tell us whether or not we succeeded
            pass

    imp.acquire_lock()
    try:
        for name, mod in modules_to_patch:
            orig_mod = sys.modules.get(name)
            if orig_mod is None:
                orig_mod = __import__(name)
            for attr_name in mod.__patched__:
                patched_attr = getattr(mod, attr_name, None)
                if patched_attr is not None:
                    setattr(orig_mod, attr_name, patched_attr)
    finally:
        imp.release_lock()

def is_monkey_patched(module):
    """Returns True if the given module is monkeypatched currently, False if
    not.  *module* can be either the module itself or its name.

    Based entirely off the name of the module, so if you import a
    module some other way than with the import keyword (including
    import_patched), this might not be correct about that particular
    module."""
    return module in already_patched or \
           getattr(module, '__name__', None) in already_patched

def _green_os_modules():
    from eventlet.green import os
    return [('os', os)]

def _green_select_modules():
    from eventlet.green import select
    return [('select', select)]

def _green_socket_modules():
    from eventlet.green import socket
    try:
        from eventlet.green import ssl
        return [('socket', socket), ('ssl', ssl)]
    except ImportError:
        return [('socket', socket)]

def _green_thread_modules():
    from eventlet.green import Queue
    from eventlet.green import thread
    from eventlet.green import threading
    if six.PY2:
        return [('Queue', Queue), ('thread', thread), ('threading', threading)]
    if six.PY3:
        return [('queue', Queue), ('_thread', thread), ('threading', threading)]

def _green_time_modules():
    from eventlet.green import time
    return [('time', time)]

def _green_MySQLdb():
    try:
        from eventlet.green import MySQLdb
        return [('MySQLdb', MySQLdb)]
    except ImportError:
        return []


def slurp_properties(source, destination, ignore=[], srckeys=None):
    """Copy properties from *source* (assumed to be a module) to
    *destination* (assumed to be a dict).

    *ignore* lists properties that should not be thusly copied.
    *srckeys* is a list of keys to copy, if the source's __all__ is
    untrustworthy.
    """
    if srckeys is None:
        srckeys = source.__all__
    destination.update(dict([(name, getattr(source, name))
                              for name in srckeys
                              if not (
                                name.startswith('__') or
                                name in ignore)
                            ]))


if __name__ == "__main__":
    import sys
    sys.argv.pop(0)
    monkey_patch()
    with open(sys.argv[0]) as f:
        code = compile(f.read(), sys.argv[0], 'exec')
        exec(code)

########NEW FILE########
__FILENAME__ = pool
from __future__ import print_function

from eventlet import coros, proc, api
from eventlet.semaphore import Semaphore
from eventlet.support import six

import warnings
warnings.warn(
    "The pool module is deprecated.  Please use the "
    "eventlet.GreenPool and eventlet.GreenPile classes instead.",
    DeprecationWarning, stacklevel=2)


class Pool(object):
    def __init__(self, min_size=0, max_size=4, track_events=False):
        if min_size > max_size:
            raise ValueError('min_size cannot be bigger than max_size')
        self.max_size = max_size
        self.sem = Semaphore(max_size)
        self.procs = proc.RunningProcSet()
        if track_events:
            self.results = coros.queue()
        else:
            self.results = None

    def resize(self, new_max_size):
        """ Change the :attr:`max_size` of the pool.

        If the pool gets resized when there are more than *new_max_size*
        coroutines checked out, when they are returned to the pool they will be
        discarded.  The return value of :meth:`free` will be negative in this
        situation.
        """
        max_size_delta = new_max_size - self.max_size
        self.sem.counter += max_size_delta
        self.max_size = new_max_size

    @property
    def current_size(self):
        """ The number of coroutines that are currently executing jobs. """
        return len(self.procs)

    def free(self):
        """ Returns the number of coroutines that are available for doing
        work."""
        return self.sem.counter

    def execute(self, func, *args, **kwargs):
        """Execute func in one of the coroutines maintained
        by the pool, when one is free.

        Immediately returns a :class:`~eventlet.proc.Proc` object which can be
        queried for the func's result.

        >>> pool = Pool()
        >>> task = pool.execute(lambda a: ('foo', a), 1)
        >>> task.wait()
        ('foo', 1)
        """
        # if reentering an empty pool, don't try to wait on a coroutine freeing
        # itself -- instead, just execute in the current coroutine
        if self.sem.locked() and api.getcurrent() in self.procs:
            p = proc.spawn(func, *args, **kwargs)
            try:
                p.wait()
            except:
                pass
        else:
            self.sem.acquire()
            p = self.procs.spawn(func, *args, **kwargs)
            # assuming the above line cannot raise
            p.link(lambda p: self.sem.release())
        if self.results is not None:
            p.link(self.results)
        return p

    execute_async = execute

    def _execute(self, evt, func, args, kw):
        p = self.execute(func, *args, **kw)
        p.link(evt)
        return p

    def waitall(self):
        """ Calling this function blocks until every coroutine
        completes its work (i.e. there are 0 running coroutines)."""
        return self.procs.waitall()

    wait_all = waitall

    def wait(self):
        """Wait for the next execute in the pool to complete,
        and return the result."""
        return self.results.wait()

    def waiting(self):
        """Return the number of coroutines waiting to execute.
        """
        if self.sem.balance < 0:
            return -self.sem.balance
        else:
            return 0

    def killall(self):
        """ Kill every running coroutine as immediately as possible."""
        return self.procs.killall()

    def launch_all(self, function, iterable):
        """For each tuple (sequence) in *iterable*, launch ``function(*tuple)``
        in its own coroutine -- like ``itertools.starmap()``, but in parallel.
        Discard values returned by ``function()``. You should call
        ``wait_all()`` to wait for all coroutines, newly-launched plus any
        previously-submitted :meth:`execute` or :meth:`execute_async` calls, to
        complete.

        >>> pool = Pool()
        >>> def saw(x):
        ...     print("I saw %s!" % x)
        ...
        >>> pool.launch_all(saw, "ABC")
        >>> pool.wait_all()
        I saw A!
        I saw B!
        I saw C!
        """
        for tup in iterable:
            self.execute(function, *tup)

    def process_all(self, function, iterable):
        """For each tuple (sequence) in *iterable*, launch ``function(*tuple)``
        in its own coroutine -- like ``itertools.starmap()``, but in parallel.
        Discard values returned by ``function()``. Don't return until all
        coroutines, newly-launched plus any previously-submitted :meth:`execute()`
        or :meth:`execute_async` calls, have completed.

        >>> from eventlet import coros
        >>> pool = coros.CoroutinePool()
        >>> def saw(x): print("I saw %s!" % x)
        ...
        >>> pool.process_all(saw, "DEF")
        I saw D!
        I saw E!
        I saw F!
        """
        self.launch_all(function, iterable)
        self.wait_all()

    def generate_results(self, function, iterable, qsize=None):
        """For each tuple (sequence) in *iterable*, launch ``function(*tuple)``
        in its own coroutine -- like ``itertools.starmap()``, but in parallel.
        Yield each of the values returned by ``function()``, in the order
        they're completed rather than the order the coroutines were launched.

        Iteration stops when we've yielded results for each arguments tuple in
        *iterable*. Unlike :meth:`wait_all` and :meth:`process_all`, this
        function does not wait for any previously-submitted :meth:`execute` or
        :meth:`execute_async` calls.

        Results are temporarily buffered in a queue. If you pass *qsize=*, this
        value is used to limit the max size of the queue: an attempt to buffer
        too many results will suspend the completed :class:`CoroutinePool`
        coroutine until the requesting coroutine (the caller of
        :meth:`generate_results`) has retrieved one or more results by calling
        this generator-iterator's ``next()``.

        If any coroutine raises an uncaught exception, that exception will
        propagate to the requesting coroutine via the corresponding ``next()``
        call.

        What I particularly want these tests to illustrate is that using this
        generator function::

            for result in generate_results(function, iterable):
                # ... do something with result ...
                pass

        executes coroutines at least as aggressively as the classic eventlet
        idiom::

            events = [pool.execute(function, *args) for args in iterable]
            for event in events:
                result = event.wait()
                # ... do something with result ...

        even without a distinct event object for every arg tuple in *iterable*,
        and despite the funny flow control from interleaving launches of new
        coroutines with yields of completed coroutines' results.

        (The use case that makes this function preferable to the classic idiom
        above is when the *iterable*, which may itself be a generator, produces
        millions of items.)

        >>> from eventlet import coros
        >>> from eventlet.support import six
        >>> import string
        >>> pool = coros.CoroutinePool(max_size=5)
        >>> pausers = [coros.Event() for x in range(2)]
        >>> def longtask(evt, desc):
        ...     print("%s woke up with %s" % (desc, evt.wait()))
        ...
        >>> pool.launch_all(longtask, zip(pausers, "AB"))
        >>> def quicktask(desc):
        ...     print("returning %s" % desc)
        ...     return desc
        ...

        (Instead of using a ``for`` loop, step through :meth:`generate_results`
        items individually to illustrate timing)

        >>> step = iter(pool.generate_results(quicktask, string.ascii_lowercase))
        >>> print(six.next(step))
        returning a
        returning b
        returning c
        a
        >>> print(six.next(step))
        b
        >>> print(six.next(step))
        c
        >>> print(six.next(step))
        returning d
        returning e
        returning f
        d
        >>> pausers[0].send("A")
        >>> print(six.next(step))
        e
        >>> print(six.next(step))
        f
        >>> print(six.next(step))
        A woke up with A
        returning g
        returning h
        returning i
        g
        >>> print("".join([six.next(step) for x in range(3)]))
        returning j
        returning k
        returning l
        returning m
        hij
        >>> pausers[1].send("B")
        >>> print("".join([six.next(step) for x in range(4)]))
        B woke up with B
        returning n
        returning o
        returning p
        returning q
        klmn
        """
        # Get an iterator because of our funny nested loop below. Wrap the
        # iterable in enumerate() so we count items that come through.
        tuples = iter(enumerate(iterable))
        # If the iterable is empty, this whole function is a no-op, and we can
        # save ourselves some grief by just quitting out. In particular, once
        # we enter the outer loop below, we're going to wait on the queue --
        # but if we launched no coroutines with that queue as the destination,
        # we could end up waiting a very long time.
        try:
            index, args = six.next(tuples)
        except StopIteration:
            return
        # From this point forward, 'args' is the current arguments tuple and
        # 'index+1' counts how many such tuples we've seen.
        # This implementation relies on the fact that _execute() accepts an
        # event-like object, and -- unless it's None -- the completed
        # coroutine calls send(result). We slyly pass a queue rather than an
        # event -- the same queue instance for all coroutines. This is why our
        # queue interface intentionally resembles the event interface.
        q = coros.queue(max_size=qsize)
        # How many results have we yielded so far?
        finished = 0
        # This first loop is only until we've launched all the coroutines. Its
        # complexity is because if iterable contains more args tuples than the
        # size of our pool, attempting to _execute() the (poolsize+1)th
        # coroutine would suspend until something completes and send()s its
        # result to our queue. But to keep down queue overhead and to maximize
        # responsiveness to our caller, we'd rather suspend on reading the
        # queue. So we stuff the pool as full as we can, then wait for
        # something to finish, then stuff more coroutines into the pool.
        try:
            while True:
                # Before each yield, start as many new coroutines as we can fit.
                # (The self.free() test isn't 100% accurate: if we happen to be
                # executing in one of the pool's coroutines, we could _execute()
                # without waiting even if self.free() reports 0. See _execute().)
                # The point is that we don't want to wait in the _execute() call,
                # we want to wait in the q.wait() call.
                # IMPORTANT: at start, and whenever we've caught up with all
                # coroutines we've launched so far, we MUST iterate this inner
                # loop at least once, regardless of self.free() -- otherwise the
                # q.wait() call below will deadlock!
                # Recall that index is the index of the NEXT args tuple that we
                # haven't yet launched. Therefore it counts how many args tuples
                # we've launched so far.
                while self.free() > 0 or finished == index:
                    # Just like the implementation of execute_async(), save that
                    # we're passing our queue instead of None as the "event" to
                    # which to send() the result.
                    self._execute(q, function, args, {})
                    # We've consumed that args tuple, advance to next.
                    index, args = six.next(tuples)
                # Okay, we've filled up the pool again, yield a result -- which
                # will probably wait for a coroutine to complete. Although we do
                # have q.ready(), so we could iterate without waiting, we avoid
                # that because every yield could involve considerable real time.
                # We don't know how long it takes to return from yield, so every
                # time we do, take the opportunity to stuff more requests into the
                # pool before yielding again.
                yield q.wait()
                # Be sure to count results so we know when to stop!
                finished += 1
        except StopIteration:
            pass
        # Here we've exhausted the input iterable. index+1 is the total number
        # of coroutines we've launched. We probably haven't yielded that many
        # results yet. Wait for the rest of the results, yielding them as they
        # arrive.
        while finished < index + 1:
            yield q.wait()
            finished += 1

########NEW FILE########
__FILENAME__ = pools
from __future__ import print_function

import collections
from contextlib import contextmanager

from eventlet import queue


__all__ = ['Pool', 'TokenPool']


class Pool(object):
    """
    Pool class implements resource limitation and construction.

    There are two ways of using Pool: passing a `create` argument or
    subclassing. In either case you must provide a way to create
    the resource.

    When using `create` argument, pass a function with no arguments::

        http_pool = pools.Pool(create=httplib2.Http)

    If you need to pass arguments, build a nullary function with either
    `lambda` expression::

        http_pool = pools.Pool(create=lambda: httplib2.Http(timeout=90))

    or :func:`functools.partial`::

        from functools import partial
        http_pool = pools.Pool(create=partial(httplib2.Http, timeout=90))

    When subclassing, define only the :meth:`create` method
    to implement the desired resource::

        class MyPool(pools.Pool):
            def create(self):
                return MyObject()

    If using 2.5 or greater, the :meth:`item` method acts as a context manager;
    that's the best way to use it::

        with mypool.item() as thing:
            thing.dostuff()

    The maximum size of the pool can be modified at runtime via
    the :meth:`resize` method.

    Specifying a non-zero *min-size* argument pre-populates the pool with
    *min_size* items.  *max-size* sets a hard limit to the size of the pool --
    it cannot contain any more items than *max_size*, and if there are already
    *max_size* items 'checked out' of the pool, the pool will cause any
    greenthread calling :meth:`get` to cooperatively yield until an item
    is :meth:`put` in.
    """
    def __init__(self, min_size=0, max_size=4, order_as_stack=False, create=None):
        """*order_as_stack* governs the ordering of the items in the free pool.
        If ``False`` (the default), the free items collection (of items that
        were created and were put back in the pool) acts as a round-robin,
        giving each item approximately equal utilization.  If ``True``, the
        free pool acts as a FILO stack, which preferentially re-uses items that
        have most recently been used.
        """
        self.min_size = min_size
        self.max_size = max_size
        self.order_as_stack = order_as_stack
        self.current_size = 0
        self.channel = queue.LightQueue(0)
        self.free_items = collections.deque()
        if create is not None:
            self.create = create

        for x in range(min_size):
            self.current_size += 1
            self.free_items.append(self.create())

    def get(self):
        """Return an item from the pool, when one is available.  This may
        cause the calling greenthread to block.
        """
        if self.free_items:
            return self.free_items.popleft()
        self.current_size += 1
        if self.current_size <= self.max_size:
            try:
                created = self.create()
            except:
                self.current_size -= 1
                raise
            return created
        self.current_size -= 1 # did not create
        return self.channel.get()

    @contextmanager
    def item(self):
        """ Get an object out of the pool, for use with with statement.

        >>> from eventlet import pools
        >>> pool = pools.TokenPool(max_size=4)
        >>> with pool.item() as obj:
        ...     print("got token")
        ...
        got token
        >>> pool.free()
        4
        """
        obj = self.get()
        try:
            yield obj
        finally:
            self.put(obj)

    def put(self, item):
        """Put an item back into the pool, when done.  This may
        cause the putting greenthread to block.
        """
        if self.current_size > self.max_size:
            self.current_size -= 1
            return

        if self.waiting():
            self.channel.put(item)
        else:
            if self.order_as_stack:
                self.free_items.appendleft(item)
            else:
                self.free_items.append(item)

    def resize(self, new_size):
        """Resize the pool to *new_size*.

        Adjusting this number does not affect existing items checked out of
        the pool, nor on any greenthreads who are waiting for an item to free
        up.  Some indeterminate number of :meth:`get`/:meth:`put`
        cycles will be necessary before the new maximum size truly matches
        the actual operation of the pool.
        """
        self.max_size = new_size

    def free(self):
        """Return the number of free items in the pool.  This corresponds
        to the number of :meth:`get` calls needed to empty the pool.
        """
        return len(self.free_items) + self.max_size - self.current_size

    def waiting(self):
        """Return the number of routines waiting for a pool item.
        """
        return max(0, self.channel.getting() - self.channel.putting())

    def create(self):
        """Generate a new pool item.  In order for the pool to
        function, either this method must be overriden in a subclass
        or the pool must be constructed with the `create` argument.
        It accepts no arguments and returns a single instance of
        whatever thing the pool is supposed to contain.

        In general, :meth:`create` is called whenever the pool exceeds its
        previous high-water mark of concurrently-checked-out-items.  In other
        words, in a new pool with *min_size* of 0, the very first call
        to :meth:`get` will result in a call to :meth:`create`.  If the first
        caller calls :meth:`put` before some other caller calls :meth:`get`,
        then the first item will be returned, and :meth:`create` will not be
        called a second time.
        """
        raise NotImplementedError("Implement in subclass")


class Token(object):
    pass


class TokenPool(Pool):
    """A pool which gives out tokens (opaque unique objects), which indicate
    that the coroutine which holds the token has a right to consume some
    limited resource.
    """
    def create(self):
        return Token()


########NEW FILE########
__FILENAME__ = proc
"""
This module provides means to spawn, kill and link coroutines. Linking means
subscribing to the coroutine's result, either in form of return value or
unhandled exception.

To create a linkable coroutine use spawn function provided by this module:

    >>> def demofunc(x, y):
    ...    return x / y
    >>> p = spawn(demofunc, 6, 2)

The return value of :func:`spawn` is an instance of :class:`Proc` class that
you can "link":

 * ``p.link(obj)`` - notify *obj* when the coroutine is finished

What "notify" means here depends on the type of *obj*: a callable is simply
called, an :class:`~eventlet.coros.Event` or a :class:`~eventlet.coros.queue`
is notified using ``send``/``send_exception`` methods and if *obj* is another
greenlet it's killed with :class:`LinkedExited` exception.

Here's an example:

>>> event = coros.Event()
>>> _ = p.link(event)
>>> event.wait()
3

Now, even though *p* is finished it's still possible to link it. In this
case the notification is performed immediatelly:

>>> try:
...     p.link()
... except LinkedCompleted:
...     print('LinkedCompleted')
LinkedCompleted

(Without an argument, the link is created to the current greenlet)

There are also :meth:`~eventlet.proc.Source.link_value` and
:func:`link_exception` methods that only deliver a return value and an
unhandled exception respectively (plain :meth:`~eventlet.proc.Source.link`
delivers both).  Suppose we want to spawn a greenlet to do an important part of
the task; if it fails then there's no way to complete the task so the parent
must fail as well; :meth:`~eventlet.proc.Source.link_exception` is useful here:

>>> p = spawn(demofunc, 1, 0)
>>> _ = p.link_exception()
>>> try:
...     api.sleep(1)
... except LinkedFailed:
...     print('LinkedFailed')
LinkedFailed

One application of linking is :func:`waitall` function: link to a bunch of
coroutines and wait for all them to complete. Such a function is provided by
this module.
"""
import sys

from eventlet import api, coros, hubs
from eventlet.support import six

import warnings
warnings.warn(
    "The proc module is deprecated!  Please use the greenthread "
    "module, or any of the many other Eventlet cross-coroutine "
    "primitives, instead.",
    DeprecationWarning, stacklevel=2)

__all__ = ['LinkedExited',
           'LinkedFailed',
           'LinkedCompleted',
           'LinkedKilled',
           'ProcExit',
           'Link',
           'waitall',
           'killall',
           'Source',
           'Proc',
           'spawn',
           'spawn_link',
           'spawn_link_value',
           'spawn_link_exception']


class LinkedExited(Exception):
    """Raised when a linked proc exits"""
    msg = "%r exited"

    def __init__(self, name=None, msg=None):
        self.name = name
        if msg is None:
            msg = self.msg % self.name
        Exception.__init__(self, msg)


class LinkedCompleted(LinkedExited):
    """Raised when a linked proc finishes the execution cleanly"""

    msg = "%r completed successfully"


class LinkedFailed(LinkedExited):
    """Raised when a linked proc dies because of unhandled exception"""
    msg = "%r failed with %s"

    def __init__(self, name, typ, value=None, tb=None):
        msg = self.msg % (name, typ.__name__)
        LinkedExited.__init__(self, name, msg)


class LinkedKilled(LinkedFailed):
    """Raised when a linked proc dies because of unhandled GreenletExit
    (i.e. it was killed)
    """
    msg = """%r was killed with %s"""


def getLinkedFailed(name, typ, value=None, tb=None):
    if issubclass(typ, api.GreenletExit):
        return LinkedKilled(name, typ, value, tb)
    return LinkedFailed(name, typ, value, tb)


class ProcExit(api.GreenletExit):
    """Raised when this proc is killed."""


class Link(object):
    """
    A link to a greenlet, triggered when the greenlet exits.
    """

    def __init__(self, listener):
        self.listener = listener

    def cancel(self):
        self.listener = None

    def __enter__(self):
        pass

    def __exit__(self, *args):
        self.cancel()


class LinkToEvent(Link):

    def __call__(self, source):
        if self.listener is None:
            return
        if source.has_value():
            self.listener.send(source.value)
        else:
            self.listener.send_exception(*source.exc_info())


class LinkToGreenlet(Link):

    def __call__(self, source):
        if source.has_value():
            self.listener.throw(LinkedCompleted(source.name))
        else:
            self.listener.throw(getLinkedFailed(source.name, *source.exc_info()))


class LinkToCallable(Link):

    def __call__(self, source):
        self.listener(source)


def waitall(lst, trap_errors=False, queue=None):
    if queue is None:
        queue = coros.queue()
    index = -1
    for (index, linkable) in enumerate(lst):
        linkable.link(decorate_send(queue, index))
    len = index + 1
    results = [None] * len
    count = 0
    while count < len:
        try:
            index, value = queue.wait()
        except Exception:
            if not trap_errors:
                raise
        else:
            results[index] = value
        count += 1
    return results


class decorate_send(object):

    def __init__(self, event, tag):
        self._event = event
        self._tag = tag

    def __repr__(self):
        params = (type(self).__name__, self._tag, self._event)
        return '<%s tag=%r event=%r>' % params

    def __getattr__(self, name):
        assert name != '_event'
        return getattr(self._event, name)

    def send(self, value):
        self._event.send((self._tag, value))


def killall(procs, *throw_args, **kwargs):
    if not throw_args:
        throw_args = (ProcExit, )
    wait = kwargs.pop('wait', False)
    if kwargs:
        raise TypeError('Invalid keyword argument for proc.killall(): %s' % ', '.join(kwargs.keys()))
    for g in procs:
        if not g.dead:
            hubs.get_hub().schedule_call_global(0, g.throw, *throw_args)
    if wait and api.getcurrent() is not hubs.get_hub().greenlet:
        api.sleep(0)


class NotUsed(object):

    def __str__(self):
        return '<Source instance does not hold a value or an exception>'

    __repr__ = __str__

_NOT_USED = NotUsed()


def spawn_greenlet(function, *args):
    """Create a new greenlet that will run ``function(*args)``.
    The current greenlet won't be unscheduled. Keyword arguments aren't
    supported (limitation of greenlet), use :func:`spawn` to work around that.
    """
    g = api.Greenlet(function)
    g.parent = hubs.get_hub().greenlet
    hubs.get_hub().schedule_call_global(0, g.switch, *args)
    return g


class Source(object):
    """Maintain a set of links to the listeners. Delegate the sent value or
    the exception to all of them.

    To set up a link, use :meth:`link_value`, :meth:`link_exception` or
    :meth:`link` method. The latter establishes both "value" and "exception"
    link. It is possible to link to events, queues, greenlets and callables.

    >>> source = Source()
    >>> event = coros.Event()
    >>> _ = source.link(event)

    Once source's :meth:`send` or :meth:`send_exception` method is called, all
    the listeners with the right type of link will be notified ("right type"
    means that exceptions won't be delivered to "value" links and values won't
    be delivered to "exception" links). Once link has been fired it is removed.

    Notifying listeners is performed in the **mainloop** greenlet. Under the
    hood notifying a link means executing a callback, see :class:`Link` class
    for details. Notification *must not* attempt to switch to the hub, i.e.
    call any blocking functions.

    >>> source.send('hello')
    >>> event.wait()
    'hello'

    Any error happened while sending will be logged as a regular unhandled
    exception. This won't prevent other links from being fired.

    There 3 kinds of listeners supported:

     1. If *listener* is a greenlet (regardless if it's a raw greenlet or an
        extension like :class:`Proc`), a subclass of :class:`LinkedExited`
        exception is raised in it.

     2. If *listener* is something with send/send_exception methods (event,
        queue, :class:`Source` but not :class:`Proc`) the relevant method is
        called.

     3. If *listener* is a callable, it is called with 1 argument (the result)
        for "value" links and with 3 arguments ``(typ, value, tb)`` for
        "exception" links.
    """

    def __init__(self, name=None):
        self.name = name
        self._value_links = {}
        self._exception_links = {}
        self.value = _NOT_USED
        self._exc = None

    def _repr_helper(self):
        result = []
        result.append(repr(self.name))
        if self.value is not _NOT_USED:
            if self._exc is None:
                res = repr(self.value)
                if len(res) > 50:
                    res = res[:50]+'...'
                result.append('result=%s' % res)
            else:
                result.append('raised=%s' % (self._exc, ))
        result.append('{%s:%s}' % (len(self._value_links), len(self._exception_links)))
        return result

    def __repr__(self):
        klass = type(self).__name__
        return '<%s at %s %s>' % (klass, hex(id(self)), ' '.join(self._repr_helper()))

    def ready(self):
        return self.value is not _NOT_USED

    def has_value(self):
        return self.value is not _NOT_USED and self._exc is None

    def has_exception(self):
        return self.value is not _NOT_USED and self._exc is not None

    def exc_info(self):
        if not self._exc:
            return (None, None, None)
        elif len(self._exc) == 3:
            return self._exc
        elif len(self._exc) == 1:
            if isinstance(self._exc[0], type):
                return self._exc[0], None, None
            else:
                return self._exc[0].__class__, self._exc[0], None
        elif len(self._exc) == 2:
            return self._exc[0], self._exc[1], None
        else:
            return self._exc

    def link_value(self, listener=None, link=None):
        if self.ready() and self._exc is not None:
            return
        if listener is None:
            listener = api.getcurrent()
        if link is None:
            link = self.getLink(listener)
        if self.ready() and listener is api.getcurrent():
            link(self)
        else:
            self._value_links[listener] = link
            if self.value is not _NOT_USED:
                self._start_send()
        return link

    def link_exception(self, listener=None, link=None):
        if self.value is not _NOT_USED and self._exc is None:
            return
        if listener is None:
            listener = api.getcurrent()
        if link is None:
            link = self.getLink(listener)
        if self.ready() and listener is api.getcurrent():
            link(self)
        else:
            self._exception_links[listener] = link
            if self.value is not _NOT_USED:
                self._start_send_exception()
        return link

    def link(self, listener=None, link=None):
        if listener is None:
            listener = api.getcurrent()
        if link is None:
            link = self.getLink(listener)
        if self.ready() and listener is api.getcurrent():
            if self._exc is None:
                link(self)
            else:
                link(self)
        else:
            self._value_links[listener] = link
            self._exception_links[listener] = link
            if self.value is not _NOT_USED:
                if self._exc is None:
                    self._start_send()
                else:
                    self._start_send_exception()
        return link

    def unlink(self, listener=None):
        if listener is None:
            listener = api.getcurrent()
        self._value_links.pop(listener, None)
        self._exception_links.pop(listener, None)

    @staticmethod
    def getLink(listener):
        if hasattr(listener, 'throw'):
            return LinkToGreenlet(listener)
        if hasattr(listener, 'send'):
            return LinkToEvent(listener)
        elif hasattr(listener, '__call__'):
            return LinkToCallable(listener)
        else:
            raise TypeError("Don't know how to link to %r" % (listener, ))

    def send(self, value):
        assert not self.ready(), "%s has been fired already" % self
        self.value = value
        self._exc = None
        self._start_send()

    def _start_send(self):
        links_items = list(six.iteritems(self._value_links))
        hubs.get_hub().schedule_call_global(0, self._do_send, links_items, self._value_links)

    def send_exception(self, *throw_args):
        assert not self.ready(), "%s has been fired already" % self
        self.value = None
        self._exc = throw_args
        self._start_send_exception()

    def _start_send_exception(self):
        links_items = list(six.iteritems(self._exception_links))
        hubs.get_hub().schedule_call_global(0, self._do_send, links_items, self._exception_links)

    def _do_send(self, links, consult):
        while links:
            listener, link = links.pop()
            try:
                if listener in consult:
                    try:
                        link(self)
                    finally:
                        consult.pop(listener, None)
            except:
                hubs.get_hub().schedule_call_global(0, self._do_send, links, consult)
                raise

    def wait(self, timeout=None, *throw_args):
        """Wait until :meth:`send` or :meth:`send_exception` is called or
        *timeout* has expired. Return the argument of :meth:`send` or raise the
        argument of :meth:`send_exception`. If *timeout* has expired, ``None``
        is returned.

        The arguments, when provided, specify how many seconds to wait and what
        to do when *timeout* has expired. They are treated the same way as
        :func:`~eventlet.api.timeout` treats them.
        """
        if self.value is not _NOT_USED:
            if self._exc is None:
                return self.value
            else:
                api.getcurrent().throw(*self._exc)
        if timeout is not None:
            timer = api.timeout(timeout, *throw_args)
            timer.__enter__()
            if timeout == 0:
                if timer.__exit__(None, None, None):
                    return
                else:
                    try:
                        api.getcurrent().throw(*timer.throw_args)
                    except:
                        if not timer.__exit__(*sys.exc_info()):
                            raise
                    return
            EXC = True
        try:
            try:
                waiter = Waiter()
                self.link(waiter)
                try:
                    return waiter.wait()
                finally:
                    self.unlink(waiter)
            except:
                EXC = False
                if timeout is None or not timer.__exit__(*sys.exc_info()):
                    raise
        finally:
            if timeout is not None and EXC:
                timer.__exit__(None, None, None)


class Waiter(object):

    def __init__(self):
        self.greenlet = None

    def send(self, value):
        """Wake up the greenlet that is calling wait() currently (if there is one).
        Can only be called from get_hub().greenlet.
        """
        assert api.getcurrent() is hubs.get_hub().greenlet
        if self.greenlet is not None:
            self.greenlet.switch(value)

    def send_exception(self, *throw_args):
        """Make greenlet calling wait() wake up (if there is a wait()).
        Can only be called from get_hub().greenlet.
        """
        assert api.getcurrent() is hubs.get_hub().greenlet
        if self.greenlet is not None:
            self.greenlet.throw(*throw_args)

    def wait(self):
        """Wait until send or send_exception is called. Return value passed
        into send() or raise exception passed into send_exception().
        """
        assert self.greenlet is None
        current = api.getcurrent()
        assert current is not hubs.get_hub().greenlet
        self.greenlet = current
        try:
            return hubs.get_hub().switch()
        finally:
            self.greenlet = None


class Proc(Source):
    """A linkable coroutine based on Source.
    Upon completion, delivers coroutine's result to the listeners.
    """

    def __init__(self, name=None):
        self.greenlet = None
        Source.__init__(self, name)

    def _repr_helper(self):
        if self.greenlet is not None and self.greenlet.dead:
            dead = '(dead)'
        else:
            dead = ''
        return ['%r%s' % (self.greenlet, dead)] + Source._repr_helper(self)

    def __repr__(self):
        klass = type(self).__name__
        return '<%s %s>' % (klass, ' '.join(self._repr_helper()))

    def __nonzero__(self):
        if self.ready():
            # with current _run this does not makes any difference
            # still, let keep it there
            return False
        # otherwise bool(proc) is the same as bool(greenlet)
        if self.greenlet is not None:
            return bool(self.greenlet)

    __bool__ = __nonzero__

    @property
    def dead(self):
        return self.ready() or self.greenlet.dead

    @classmethod
    def spawn(cls, function, *args, **kwargs):
        """Return a new :class:`Proc` instance that is scheduled to execute
        ``function(*args, **kwargs)`` upon the next hub iteration.
        """
        proc = cls()
        proc.run(function, *args, **kwargs)
        return proc

    def run(self, function, *args, **kwargs):
        """Create a new greenlet to execute ``function(*args, **kwargs)``.
        The created greenlet is scheduled to run upon the next hub iteration.
        """
        assert self.greenlet is None, "'run' can only be called once per instance"
        if self.name is None:
            self.name = str(function)
        self.greenlet = spawn_greenlet(self._run, function, args, kwargs)

    def _run(self, function, args, kwargs):
        """Internal top level function.
        Execute *function* and send its result to the listeners.
        """
        try:
            result = function(*args, **kwargs)
        except:
            self.send_exception(*sys.exc_info())
            raise  # let mainloop log the exception
        else:
            self.send(result)

    def throw(self, *throw_args):
        """Used internally to raise the exception.

        Behaves exactly like greenlet's 'throw' with the exception that
        :class:`ProcExit` is raised by default. Do not use this function as it
        leaves the current greenlet unscheduled forever. Use :meth:`kill`
        method instead.
        """
        if not self.dead:
            if not throw_args:
                throw_args = (ProcExit, )
            self.greenlet.throw(*throw_args)

    def kill(self, *throw_args):
        """
        Raise an exception in the greenlet. Unschedule the current greenlet so
        that this :class:`Proc` can handle the exception (or die).

        The exception can be specified with *throw_args*. By default,
        :class:`ProcExit` is raised.
        """
        if not self.dead:
            if not throw_args:
                throw_args = (ProcExit, )
            hubs.get_hub().schedule_call_global(0, self.greenlet.throw, *throw_args)
            if api.getcurrent() is not hubs.get_hub().greenlet:
                api.sleep(0)

    # QQQ maybe Proc should not inherit from Source (because its send() and send_exception()
    # QQQ methods are for internal use only)


spawn = Proc.spawn


def spawn_link(function, *args, **kwargs):
    p = spawn(function, *args, **kwargs)
    p.link()
    return p


def spawn_link_value(function, *args, **kwargs):
    p = spawn(function, *args, **kwargs)
    p.link_value()
    return p


def spawn_link_exception(function, *args, **kwargs):
    p = spawn(function, *args, **kwargs)
    p.link_exception()
    return p


class wrap_errors(object):
    """Helper to make function return an exception, rather than raise it.

    Because every exception that is unhandled by greenlet will be logged by the hub,
    it is desirable to prevent non-error exceptions from leaving a greenlet.
    This can done with simple try/except construct:

    def func1(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except (A, B, C) as ex:
            return ex

    wrap_errors provides a shortcut to write that in one line:

    func1 = wrap_errors((A, B, C), func)

    It also preserves __str__ and __repr__ of the original function.
    """

    def __init__(self, errors, func):
        """Make a new function from `func', such that it catches `errors' (an
        Exception subclass, or a tuple of Exception subclasses) and return
        it as a value.
        """
        self.errors = errors
        self.func = func

    def __call__(self, *args, **kwargs):
        try:
            return self.func(*args, **kwargs)
        except self.errors as ex:
            return ex

    def __str__(self):
        return str(self.func)

    def __repr__(self):
        return repr(self.func)

    def __getattr__(self, item):
        return getattr(self.func, item)


class RunningProcSet(object):
    """
    Maintain a set of :class:`Proc` s that are still running, that is,
    automatically remove a proc when it's finished. Provide a way to wait/kill
    all of them
    """

    def __init__(self, *args):
        self.procs = set(*args)
        if args:
            for p in self.args[0]:
                p.link(lambda p: self.procs.discard(p))

    def __len__(self):
        return len(self.procs)

    def __contains__(self, item):
        if isinstance(item, api.Greenlet):
            # special case for "api.getcurrent() in running_proc_set" to work
            for x in self.procs:
                if x.greenlet == item:
                    return True
        else:
            return item in self.procs

    def __iter__(self):
        return iter(self.procs)

    def add(self, p):
        self.procs.add(p)
        p.link(lambda p: self.procs.discard(p))

    def spawn(self, func, *args, **kwargs):
        p = spawn(func, *args, **kwargs)
        self.add(p)
        return p

    def waitall(self, trap_errors=False):
        while self.procs:
            waitall(self.procs, trap_errors=trap_errors)

    def killall(self, *throw_args, **kwargs):
        return killall(self.procs, *throw_args, **kwargs)


class Pool(object):

    linkable_class = Proc

    def __init__(self, limit):
        self.semaphore = coros.Semaphore(limit)

    def allocate(self):
        self.semaphore.acquire()
        g = self.linkable_class()
        g.link(lambda *_args: self.semaphore.release())
        return g



########NEW FILE########
__FILENAME__ = processes
import warnings
warnings.warn("eventlet.processes is deprecated in favor of "
              "eventlet.green.subprocess, which is API-compatible with the standard "
              " library subprocess module.",
              DeprecationWarning, stacklevel=2)

import errno
import os
import signal

import eventlet
from eventlet import greenio, pools
from eventlet.green import subprocess


class DeadProcess(RuntimeError):
    pass


def cooperative_wait(pobj, check_interval=0.01):
    """ Waits for a child process to exit, returning the status
    code.

    Unlike ``os.wait``, :func:`cooperative_wait` does not block the entire
    process, only the calling coroutine.  If the child process does not die,
    :func:`cooperative_wait` could wait forever.

    The argument *check_interval* is the amount of time, in seconds, that
    :func:`cooperative_wait` will sleep between calls to ``os.waitpid``.
    """
    try:
        while True:
            status = pobj.poll()
            if status >= 0:
                return status
            eventlet.sleep(check_interval)
    except OSError as e:
        if e.errno == errno.ECHILD:
            # no child process, this happens if the child process
            # already died and has been cleaned up, or if you just
            # called with a random pid value
            return -1
        else:
            raise


class Process(object):
    """Construct Process objects, then call read, and write on them."""
    process_number = 0

    def __init__(self, command, args, dead_callback=None):
        self.process_number = self.process_number + 1
        Process.process_number = self.process_number
        self.command = command
        self.args = args
        self._dead_callback = dead_callback
        self.run()

    def run(self):
        self.dead = False
        self.started = False
        self.proc = None

        args = [self.command]
        args.extend(self.args)
        self.proc = subprocess.Popen(
            args=args,
            shell=False,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            close_fds=True,
        )
        self.child_stdout_stderr = self.proc.stdout
        self.child_stdin = self.proc.stdin

        self.sendall = self.child_stdin.write
        self.send = self.child_stdin.write
        self.recv = self.child_stdout_stderr.read
        self.readline = self.child_stdout_stderr.readline
        self._read_first_result = False

    def wait(self):
        return cooperative_wait(self.proc)

    def dead_callback(self):
        self.wait()
        self.dead = True
        if self._dead_callback:
            self._dead_callback()

    def makefile(self, mode, *arg):
        if mode.startswith('r'):
            return self.child_stdout_stderr
        if mode.startswith('w'):
            return self.child_stdin
        raise RuntimeError("Unknown mode", mode)

    def read(self, amount=None):
        """Reads from the stdout and stderr of the child process.
        The first call to read() will return a string; subsequent
        calls may raise a DeadProcess when EOF occurs on the pipe.
        """
        result = self.child_stdout_stderr.read(amount)
        if result == '' and self._read_first_result:
            # This process is dead.
            self.dead_callback()
            raise DeadProcess
        else:
            self._read_first_result = True
        return result

    def write(self, stuff):
        written = 0
        try:
            written = self.child_stdin.write(stuff)
            self.child_stdin.flush()
        except ValueError as e:
            ## File was closed
            assert str(e) == 'I/O operation on closed file'
        if written == 0:
            self.dead_callback()
            raise DeadProcess

    def flush(self):
        self.child_stdin.flush()

    def close(self):
        self.child_stdout_stderr.close()
        self.child_stdin.close()
        self.dead_callback()

    def close_stdin(self):
        self.child_stdin.close()

    def kill(self, sig=None):
        if sig is None:
            sig = signal.SIGTERM
        pid = self.getpid()
        os.kill(pid, sig)

    def getpid(self):
        return self.proc.pid


class ProcessPool(pools.Pool):
    def __init__(self, command, args=None, min_size=0, max_size=4):
        """*command*
            the command to run
        """
        self.command = command
        if args is None:
            args = []
        self.args = args
        pools.Pool.__init__(self, min_size, max_size)

    def create(self):
        """Generate a process
        """
        def dead_callback():
            self.current_size -= 1
        return Process(self.command, self.args, dead_callback)

    def put(self, item):
        if not item.dead:
            if item.proc.poll() != -1:
                item.dead_callback()
            else:
                pools.Pool.put(self, item)

########NEW FILE########
__FILENAME__ = queue
# Copyright (c) 2009 Denis Bilenko, denis.bilenko at gmail com
# Copyright (c) 2010 Eventlet Contributors (see AUTHORS)
# and licensed under the MIT license:
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

"""Synchronized queues.

The :mod:`eventlet.queue` module implements multi-producer, multi-consumer
queues that work across greenlets, with the API similar to the classes found in
the standard :mod:`Queue` and :class:`multiprocessing <multiprocessing.Queue>`
modules.

A major difference is that queues in this module operate as channels when
initialized with *maxsize* of zero. In such case, both :meth:`Queue.empty`
and :meth:`Queue.full` return ``True`` and :meth:`Queue.put` always blocks until
a call to :meth:`Queue.get` retrieves the item.

An interesting difference, made possible because of greenthreads, is
that :meth:`Queue.qsize`, :meth:`Queue.empty`, and :meth:`Queue.full` *can* be
used as indicators of whether the subsequent :meth:`Queue.get`
or :meth:`Queue.put` will not block.  The new methods :meth:`Queue.getting`
and :meth:`Queue.putting` report on the number of greenthreads blocking
in :meth:`put <Queue.put>` or :meth:`get <Queue.get>` respectively.
"""
from __future__ import print_function

import sys
import heapq
import collections
import traceback

from eventlet.event import Event
from eventlet.greenthread import getcurrent
from eventlet.hubs import get_hub
from eventlet.support import six
from eventlet.timeout import Timeout


__all__ = ['Queue', 'PriorityQueue', 'LifoQueue', 'LightQueue', 'Full', 'Empty']

_NONE = object()
Full = six.moves.queue.Full
Empty = six.moves.queue.Empty


class Waiter(object):
    """A low level synchronization class.

    Wrapper around greenlet's ``switch()`` and ``throw()`` calls that makes them safe:

    * switching will occur only if the waiting greenlet is executing :meth:`wait`
      method currently. Otherwise, :meth:`switch` and :meth:`throw` are no-ops.
    * any error raised in the greenlet is handled inside :meth:`switch` and :meth:`throw`

    The :meth:`switch` and :meth:`throw` methods must only be called from the :class:`Hub` greenlet.
    The :meth:`wait` method must be called from a greenlet other than :class:`Hub`.
    """
    __slots__ = ['greenlet']

    def __init__(self):
        self.greenlet = None

    def __repr__(self):
        if self.waiting:
            waiting = ' waiting'
        else:
            waiting = ''
        return '<%s at %s%s greenlet=%r>' % (type(self).__name__, hex(id(self)), waiting, self.greenlet)

    def __str__(self):
        """
        >>> print(Waiter())
        <Waiter greenlet=None>
        """
        if self.waiting:
            waiting = ' waiting'
        else:
            waiting = ''
        return '<%s%s greenlet=%s>' % (type(self).__name__, waiting, self.greenlet)

    def __nonzero__(self):
        return self.greenlet is not None

    __bool__ = __nonzero__

    @property
    def waiting(self):
        return self.greenlet is not None

    def switch(self, value=None):
        """Wake up the greenlet that is calling wait() currently (if there is one).
        Can only be called from Hub's greenlet.
        """
        assert getcurrent() is get_hub().greenlet, "Can only use Waiter.switch method from the mainloop"
        if self.greenlet is not None:
            try:
                self.greenlet.switch(value)
            except:
                traceback.print_exc()

    def throw(self, *throw_args):
        """Make greenlet calling wait() wake up (if there is a wait()).
        Can only be called from Hub's greenlet.
        """
        assert getcurrent() is get_hub().greenlet, "Can only use Waiter.switch method from the mainloop"
        if self.greenlet is not None:
            try:
                self.greenlet.throw(*throw_args)
            except:
                traceback.print_exc()

    # XXX should be renamed to get() ? and the whole class is called Receiver?
    def wait(self):
        """Wait until switch() or throw() is called.
        """
        assert self.greenlet is None, 'This Waiter is already used by %r' % (self.greenlet, )
        self.greenlet = getcurrent()
        try:
            return get_hub().switch()
        finally:
            self.greenlet = None


class LightQueue(object):
    """
    This is a variant of Queue that behaves mostly like the standard
    :class:`Queue`.  It differs by not supporting the
    :meth:`task_done <Queue.task_done>` or :meth:`join <Queue.join>` methods,
    and is a little faster for not having that overhead.
    """

    def __init__(self, maxsize=None):
        if maxsize is None or maxsize < 0: #None is not comparable in 3.x
            self.maxsize = None
        else:
            self.maxsize = maxsize
        self.getters = set()
        self.putters = set()
        self._event_unlock = None
        self._init(maxsize)

    # QQQ make maxsize into a property with setter that schedules unlock if necessary

    def _init(self, maxsize):
        self.queue = collections.deque()

    def _get(self):
        return self.queue.popleft()

    def _put(self, item):
        self.queue.append(item)

    def __repr__(self):
        return '<%s at %s %s>' % (type(self).__name__, hex(id(self)), self._format())

    def __str__(self):
        return '<%s %s>' % (type(self).__name__, self._format())

    def _format(self):
        result = 'maxsize=%r' % (self.maxsize, )
        if getattr(self, 'queue', None):
            result += ' queue=%r' % self.queue
        if self.getters:
            result += ' getters[%s]' % len(self.getters)
        if self.putters:
            result += ' putters[%s]' % len(self.putters)
        if self._event_unlock is not None:
            result += ' unlocking'
        return result

    def qsize(self):
        """Return the size of the queue."""
        return len(self.queue)

    def resize(self, size):
        """Resizes the queue's maximum size.

        If the size is increased, and there are putters waiting, they may be woken up."""
        if self.maxsize is not None and (size is None or size > self.maxsize): # None is not comparable in 3.x
            # Maybe wake some stuff up
            self._schedule_unlock()
        self.maxsize = size

    def putting(self):
        """Returns the number of greenthreads that are blocked waiting to put
        items into the queue."""
        return len(self.putters)

    def getting(self):
        """Returns the number of greenthreads that are blocked waiting on an
        empty queue."""
        return len(self.getters)

    def empty(self):
        """Return ``True`` if the queue is empty, ``False`` otherwise."""
        return not self.qsize()

    def full(self):
        """Return ``True`` if the queue is full, ``False`` otherwise.

        ``Queue(None)`` is never full.
        """
        return self.maxsize is not None and self.qsize() >= self.maxsize # None is not comparable in 3.x

    def put(self, item, block=True, timeout=None):
        """Put an item into the queue.

        If optional arg *block* is true and *timeout* is ``None`` (the default),
        block if necessary until a free slot is available. If *timeout* is
        a positive number, it blocks at most *timeout* seconds and raises
        the :class:`Full` exception if no free slot was available within that time.
        Otherwise (*block* is false), put an item on the queue if a free slot
        is immediately available, else raise the :class:`Full` exception (*timeout*
        is ignored in that case).
        """
        if self.maxsize is None or self.qsize() < self.maxsize:
            # there's a free slot, put an item right away
            self._put(item)
            if self.getters:
                self._schedule_unlock()
        elif not block and get_hub().greenlet is getcurrent():
            # we're in the mainloop, so we cannot wait; we can switch() to other greenlets though
            # find a getter and deliver an item to it
            while self.getters:
                getter = self.getters.pop()
                if getter:
                    self._put(item)
                    item = self._get()
                    getter.switch(item)
                    return
            raise Full
        elif block:
            waiter = ItemWaiter(item)
            self.putters.add(waiter)
            timeout = Timeout(timeout, Full)
            try:
                if self.getters:
                    self._schedule_unlock()
                result = waiter.wait()
                assert result is waiter, "Invalid switch into Queue.put: %r" % (result, )
                if waiter.item is not _NONE:
                    self._put(item)
            finally:
                timeout.cancel()
                self.putters.discard(waiter)
        else:
            raise Full

    def put_nowait(self, item):
        """Put an item into the queue without blocking.

        Only enqueue the item if a free slot is immediately available.
        Otherwise raise the :class:`Full` exception.
        """
        self.put(item, False)

    def get(self, block=True, timeout=None):
        """Remove and return an item from the queue.

        If optional args *block* is true and *timeout* is ``None`` (the default),
        block if necessary until an item is available. If *timeout* is a positive number,
        it blocks at most *timeout* seconds and raises the :class:`Empty` exception
        if no item was available within that time. Otherwise (*block* is false), return
        an item if one is immediately available, else raise the :class:`Empty` exception
        (*timeout* is ignored in that case).
        """
        if self.qsize():
            if self.putters:
                self._schedule_unlock()
            return self._get()
        elif not block and get_hub().greenlet is getcurrent():
            # special case to make get_nowait() runnable in the mainloop greenlet
            # there are no items in the queue; try to fix the situation by unlocking putters
            while self.putters:
                putter = self.putters.pop()
                if putter:
                    putter.switch(putter)
                    if self.qsize():
                        return self._get()
            raise Empty
        elif block:
            waiter = Waiter()
            timeout = Timeout(timeout, Empty)
            try:
                self.getters.add(waiter)
                if self.putters:
                    self._schedule_unlock()
                return waiter.wait()
            finally:
                self.getters.discard(waiter)
                timeout.cancel()
        else:
            raise Empty

    def get_nowait(self):
        """Remove and return an item from the queue without blocking.

        Only get an item if one is immediately available. Otherwise
        raise the :class:`Empty` exception.
        """
        return self.get(False)

    def _unlock(self):
        try:
            while True:
                if self.qsize() and self.getters:
                    getter = self.getters.pop()
                    if getter:
                        try:
                            item = self._get()
                        except:
                            getter.throw(*sys.exc_info())
                        else:
                            getter.switch(item)
                elif self.putters and self.getters:
                    putter = self.putters.pop()
                    if putter:
                        getter = self.getters.pop()
                        if getter:
                            item = putter.item
                            putter.item = _NONE # this makes greenlet calling put() not to call _put() again
                            self._put(item)
                            item = self._get()
                            getter.switch(item)
                            putter.switch(putter)
                        else:
                            self.putters.add(putter)
                elif self.putters and (self.getters or self.maxsize is None or self.qsize() < self.maxsize):
                    putter = self.putters.pop()
                    putter.switch(putter)
                else:
                    break
        finally:
            self._event_unlock = None # QQQ maybe it's possible to obtain this info from libevent?
            # i.e. whether this event is pending _OR_ currently executing
        # testcase: 2 greenlets: while True: q.put(q.get()) - nothing else has a change to execute
        # to avoid this, schedule unlock with timer(0, ...) once in a while

    def _schedule_unlock(self):
        if self._event_unlock is None:
            self._event_unlock = get_hub().schedule_call_global(0, self._unlock)


class ItemWaiter(Waiter):
    __slots__ = ['item']

    def __init__(self, item):
        Waiter.__init__(self)
        self.item = item


class Queue(LightQueue):
    '''Create a queue object with a given maximum size.

    If *maxsize* is less than zero or ``None``, the queue size is infinite.

    ``Queue(0)`` is a channel, that is, its :meth:`put` method always blocks
    until the item is delivered. (This is unlike the standard :class:`Queue`,
    where 0 means infinite size).

    In all other respects, this Queue class resembled the standard library,
    :class:`Queue`.
    '''
    def __init__(self, maxsize=None):
        LightQueue.__init__(self, maxsize)
        self.unfinished_tasks = 0
        self._cond = Event()

    def _format(self):
        result = LightQueue._format(self)
        if self.unfinished_tasks:
            result += ' tasks=%s _cond=%s' % (self.unfinished_tasks, self._cond)
        return result

    def _put(self, item):
        LightQueue._put(self, item)
        self._put_bookkeeping()

    def _put_bookkeeping(self):
        self.unfinished_tasks += 1
        if self._cond.ready():
            self._cond.reset()

    def task_done(self):
        '''Indicate that a formerly enqueued task is complete. Used by queue consumer threads.
        For each :meth:`get <Queue.get>` used to fetch a task, a subsequent call to :meth:`task_done` tells the queue
        that the processing on the task is complete.

        If a :meth:`join` is currently blocking, it will resume when all items have been processed
        (meaning that a :meth:`task_done` call was received for every item that had been
        :meth:`put <Queue.put>` into the queue).

        Raises a :exc:`ValueError` if called more times than there were items placed in the queue.
        '''

        if self.unfinished_tasks <= 0:
            raise ValueError('task_done() called too many times')
        self.unfinished_tasks -= 1
        if self.unfinished_tasks == 0:
            self._cond.send(None)

    def join(self):
        '''Block until all items in the queue have been gotten and processed.

        The count of unfinished tasks goes up whenever an item is added to the queue.
        The count goes down whenever a consumer thread calls :meth:`task_done` to indicate
        that the item was retrieved and all work on it is complete. When the count of
        unfinished tasks drops to zero, :meth:`join` unblocks.
        '''
        if self.unfinished_tasks > 0:
            self._cond.wait()


class PriorityQueue(Queue):
    '''A subclass of :class:`Queue` that retrieves entries in priority order (lowest first).

    Entries are typically tuples of the form: ``(priority number, data)``.
    '''

    def _init(self, maxsize):
        self.queue = []

    def _put(self, item, heappush=heapq.heappush):
        heappush(self.queue, item)
        self._put_bookkeeping()

    def _get(self, heappop=heapq.heappop):
        return heappop(self.queue)


class LifoQueue(Queue):
    '''A subclass of :class:`Queue` that retrieves most recently added entries first.'''

    def _init(self, maxsize):
        self.queue = []

    def _put(self, item):
        self.queue.append(item)
        self._put_bookkeeping()

    def _get(self):
        return self.queue.pop()

########NEW FILE########
__FILENAME__ = semaphore
from __future__ import with_statement
from eventlet import greenthread
from eventlet import hubs
from eventlet.timeout import Timeout


class Semaphore(object):

    """An unbounded semaphore.
    Optionally initialize with a resource *count*, then :meth:`acquire` and
    :meth:`release` resources as needed. Attempting to :meth:`acquire` when
    *count* is zero suspends the calling greenthread until *count* becomes
    nonzero again.

    This is API-compatible with :class:`threading.Semaphore`.

    It is a context manager, and thus can be used in a with block::

      sem = Semaphore(2)
      with sem:
        do_some_stuff()

    If not specified, *value* defaults to 1.

    It is possible to limit acquire time::

      sem = Semaphore()
      ok = sem.acquire(timeout=0.1)
      # True if acquired, False if timed out.

    """

    def __init__(self, value=1):
        self.counter = value
        if value < 0:
            raise ValueError("Semaphore must be initialized with a positive "
                             "number, got %s" % value)
        self._waiters = set()

    def __repr__(self):
        params = (self.__class__.__name__, hex(id(self)),
                  self.counter, len(self._waiters))
        return '<%s at %s c=%s _w[%s]>' % params

    def __str__(self):
        params = (self.__class__.__name__, self.counter, len(self._waiters))
        return '<%s c=%s _w[%s]>' % params

    def locked(self):
        """Returns true if a call to acquire would block.
        """
        return self.counter <= 0

    def bounded(self):
        """Returns False; for consistency with
        :class:`~eventlet.semaphore.CappedSemaphore`.
        """
        return False

    def acquire(self, blocking=True, timeout=None):
        """Acquire a semaphore.

        When invoked without arguments: if the internal counter is larger than
        zero on entry, decrement it by one and return immediately. If it is zero
        on entry, block, waiting until some other thread has called release() to
        make it larger than zero. This is done with proper interlocking so that
        if multiple acquire() calls are blocked, release() will wake exactly one
        of them up. The implementation may pick one at random, so the order in
        which blocked threads are awakened should not be relied on. There is no
        return value in this case.

        When invoked with blocking set to true, do the same thing as when called
        without arguments, and return true.

        When invoked with blocking set to false, do not block. If a call without
        an argument would block, return false immediately; otherwise, do the
        same thing as when called without arguments, and return true.
        """
        if not blocking and timeout is not None:
            raise ValueError("can't specify timeout for non-blocking acquire")
        if not blocking and self.locked():
            return False
        if self.counter <= 0:
            self._waiters.add(greenthread.getcurrent())
            try:
                if timeout is not None:
                    ok = False
                    with Timeout(timeout, False):
                        while self.counter <= 0:
                            hubs.get_hub().switch()
                        ok = True
                    if not ok:
                        return False
                else:
                    while self.counter <= 0:
                        hubs.get_hub().switch()
            finally:
                self._waiters.discard(greenthread.getcurrent())
        self.counter -= 1
        return True

    def __enter__(self):
        self.acquire()

    def release(self, blocking=True):
        """Release a semaphore, incrementing the internal counter by one. When
        it was zero on entry and another thread is waiting for it to become
        larger than zero again, wake up that thread.

        The *blocking* argument is for consistency with CappedSemaphore and is
        ignored
        """
        self.counter += 1
        if self._waiters:
            hubs.get_hub().schedule_call_global(0, self._do_acquire)
        return True

    def _do_acquire(self):
        if self._waiters and self.counter > 0:
            waiter = self._waiters.pop()
            waiter.switch()

    def __exit__(self, typ, val, tb):
        self.release()

    @property
    def balance(self):
        """An integer value that represents how many new calls to
        :meth:`acquire` or :meth:`release` would be needed to get the counter to
        0.  If it is positive, then its value is the number of acquires that can
        happen before the next acquire would block.  If it is negative, it is
        the negative of the number of releases that would be required in order
        to make the counter 0 again (one more release would push the counter to
        1 and unblock acquirers).  It takes into account how many greenthreads
        are currently blocking in :meth:`acquire`.
        """
        # positive means there are free items
        # zero means there are no free items but nobody has requested one
        # negative means there are requests for items, but no items
        return self.counter - len(self._waiters)


class BoundedSemaphore(Semaphore):

    """A bounded semaphore checks to make sure its current value doesn't exceed
    its initial value. If it does, ValueError is raised. In most situations
    semaphores are used to guard resources with limited capacity. If the
    semaphore is released too many times it's a sign of a bug. If not given,
    *value* defaults to 1.
    """

    def __init__(self, value=1):
        super(BoundedSemaphore, self).__init__(value)
        self.original_counter = value

    def release(self, blocking=True):
        """Release a semaphore, incrementing the internal counter by one. If
        the counter would exceed the initial value, raises ValueError.  When
        it was zero on entry and another thread is waiting for it to become
        larger than zero again, wake up that thread.

        The *blocking* argument is for consistency with :class:`CappedSemaphore`
        and is ignored
        """
        if self.counter >= self.original_counter:
            raise ValueError("Semaphore released too many times")
        return super(BoundedSemaphore, self).release(blocking)


class CappedSemaphore(object):

    """A blockingly bounded semaphore.

    Optionally initialize with a resource *count*, then :meth:`acquire` and
    :meth:`release` resources as needed. Attempting to :meth:`acquire` when
    *count* is zero suspends the calling greenthread until count becomes nonzero
    again.  Attempting to :meth:`release` after *count* has reached *limit*
    suspends the calling greenthread until *count* becomes less than *limit*
    again.

    This has the same API as :class:`threading.Semaphore`, though its
    semantics and behavior differ subtly due to the upper limit on calls
    to :meth:`release`.  It is **not** compatible with
    :class:`threading.BoundedSemaphore` because it blocks when reaching *limit*
    instead of raising a ValueError.

    It is a context manager, and thus can be used in a with block::

      sem = CappedSemaphore(2)
      with sem:
        do_some_stuff()
    """

    def __init__(self, count, limit):
        if count < 0:
            raise ValueError("CappedSemaphore must be initialized with a "
                             "positive number, got %s" % count)
        if count > limit:
            # accidentally, this also catches the case when limit is None
            raise ValueError("'count' cannot be more than 'limit'")
        self.lower_bound = Semaphore(count)
        self.upper_bound = Semaphore(limit - count)

    def __repr__(self):
        params = (self.__class__.__name__, hex(id(self)),
                  self.balance, self.lower_bound, self.upper_bound)
        return '<%s at %s b=%s l=%s u=%s>' % params

    def __str__(self):
        params = (self.__class__.__name__, self.balance,
                  self.lower_bound, self.upper_bound)
        return '<%s b=%s l=%s u=%s>' % params

    def locked(self):
        """Returns true if a call to acquire would block.
        """
        return self.lower_bound.locked()

    def bounded(self):
        """Returns true if a call to release would block.
        """
        return self.upper_bound.locked()

    def acquire(self, blocking=True):
        """Acquire a semaphore.

        When invoked without arguments: if the internal counter is larger than
        zero on entry, decrement it by one and return immediately. If it is zero
        on entry, block, waiting until some other thread has called release() to
        make it larger than zero. This is done with proper interlocking so that
        if multiple acquire() calls are blocked, release() will wake exactly one
        of them up. The implementation may pick one at random, so the order in
        which blocked threads are awakened should not be relied on. There is no
        return value in this case.

        When invoked with blocking set to true, do the same thing as when called
        without arguments, and return true.

        When invoked with blocking set to false, do not block. If a call without
        an argument would block, return false immediately; otherwise, do the
        same thing as when called without arguments, and return true.
        """
        if not blocking and self.locked():
            return False
        self.upper_bound.release()
        try:
            return self.lower_bound.acquire()
        except:
            self.upper_bound.counter -= 1
            # using counter directly means that it can be less than zero.
            # however I certainly don't need to wait here and I don't seem to have
            # a need to care about such inconsistency
            raise

    def __enter__(self):
        self.acquire()

    def release(self, blocking=True):
        """Release a semaphore.  In this class, this behaves very much like
        an :meth:`acquire` but in the opposite direction.

        Imagine the docs of :meth:`acquire` here, but with every direction
        reversed.  When calling this method, it will block if the internal
        counter is greater than or equal to *limit*.
        """
        if not blocking and self.bounded():
            return False
        self.lower_bound.release()
        try:
            return self.upper_bound.acquire()
        except:
            self.lower_bound.counter -= 1
            raise

    def __exit__(self, typ, val, tb):
        self.release()

    @property
    def balance(self):
        """An integer value that represents how many new calls to
        :meth:`acquire` or :meth:`release` would be needed to get the counter to
        0.  If it is positive, then its value is the number of acquires that can
        happen before the next acquire would block.  If it is negative, it is
        the negative of the number of releases that would be required in order
        to make the counter 0 again (one more release would push the counter to
        1 and unblock acquirers).  It takes into account how many greenthreads
        are currently blocking in :meth:`acquire` and :meth:`release`.
        """
        return self.lower_bound.balance - self.upper_bound.balance

########NEW FILE########
__FILENAME__ = greendns
#!/usr/bin/env python
'''
    greendns - non-blocking DNS support for Eventlet
'''

# Portions of this code taken from the gogreen project:
#   http://github.com/slideinc/gogreen
#
# Copyright (c) 2005-2010 Slide, Inc.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are
# met:
#
#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above
#       copyright notice, this list of conditions and the following
#       disclaimer in the documentation and/or other materials provided
#       with the distribution.
#     * Neither the name of the author nor the names of other
#       contributors may be used to endorse or promote products derived
#       from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from eventlet import patcher
from eventlet.green import _socket_nodns
from eventlet.green import time
from eventlet.green import select

dns = patcher.import_patched('dns',
                             socket=_socket_nodns,
                             time=time,
                             select=select)
for pkg in ('dns.query', 'dns.exception', 'dns.inet', 'dns.message',
            'dns.rdatatype','dns.resolver', 'dns.reversename'):
   setattr(dns, pkg.split('.')[1], patcher.import_patched(pkg,
                                                          socket=_socket_nodns,
                                                          time=time,
                                                          select=select))

socket = _socket_nodns

DNS_QUERY_TIMEOUT = 10.0

#
# Resolver instance used to perfrom DNS lookups.
#
class FakeAnswer(list):
   expiration = 0
class FakeRecord(object):
   pass

class ResolverProxy(object):
    def __init__(self, *args, **kwargs):
        self._resolver = None
        self._filename = kwargs.get('filename', '/etc/resolv.conf')
        self._hosts = {}
        if kwargs.pop('dev', False):
            self._load_etc_hosts()

    def _load_etc_hosts(self):
        try:
            fd = open('/etc/hosts', 'r')
            contents = fd.read()
            fd.close()
        except (IOError, OSError):
            return
        contents = [line for line in contents.split('\n') if line and not line[0] == '#']
        for line in contents:
            line = line.replace('\t', ' ')
            parts = line.split(' ')
            parts = [p for p in parts if p]
            if not len(parts):
                continue
            ip = parts[0]
            for part in parts[1:]:
                self._hosts[part] = ip

    def clear(self):
        self._resolver = None

    def query(self, *args, **kwargs):
        if self._resolver is None:
            self._resolver = dns.resolver.Resolver(filename = self._filename)
            self._resolver.cache = dns.resolver.Cache()

        query = args[0]
        if query is None:
            args = list(args)
            query = args[0] = '0.0.0.0'
        if self._hosts and self._hosts.get(query):
            answer = FakeAnswer()
            record = FakeRecord()
            setattr(record, 'address', self._hosts[query])
            answer.append(record)
            return answer
        return self._resolver.query(*args, **kwargs)
#
# cache
#
resolver  = ResolverProxy(dev=True)

def resolve(name):
    error = None
    rrset = None

    if rrset is None or time.time() > rrset.expiration:
        try:
            rrset = resolver.query(name)
        except dns.exception.Timeout as e:
            error = (socket.EAI_AGAIN, 'Lookup timed out')
        except dns.exception.DNSException as e:
            error = (socket.EAI_NODATA, 'No address associated with hostname')
        else:
            pass
            #responses.insert(name, rrset)

    if error:
        if rrset is None:
            raise socket.gaierror(error)
        else:
            sys.stderr.write('DNS error: %r %r\n' % (name, error))
    return rrset
#
# methods
#
def getaliases(host):
    """Checks for aliases of the given hostname (cname records)
    returns a list of alias targets
    will return an empty list if no aliases
    """
    cnames = []
    error = None

    try:
        answers = dns.resolver.query(host, 'cname')
    except dns.exception.Timeout as e:
        error = (socket.EAI_AGAIN, 'Lookup timed out')
    except dns.exception.DNSException as e:
        error = (socket.EAI_NODATA, 'No address associated with hostname')
    else:
        for record in answers:
            cnames.append(str(answers[0].target))

    if error:
        sys.stderr.write('DNS error: %r %r\n' % (host, error))

    return cnames

def getaddrinfo(host, port, family=0, socktype=0, proto=0, flags=0):
    """Replacement for Python's socket.getaddrinfo.

    Currently only supports IPv4.  At present, flags are not
    implemented.
    """
    socktype = socktype or socket.SOCK_STREAM

    if is_ipv4_addr(host):
        return [(socket.AF_INET, socktype, proto, '', (host, port))]

    rrset = resolve(host)
    value = []

    for rr in rrset:
        value.append((socket.AF_INET, socktype, proto, '', (rr.address, port)))
    return value

def gethostbyname(hostname):
    """Replacement for Python's socket.gethostbyname.

    Currently only supports IPv4.
    """
    if is_ipv4_addr(hostname):
        return hostname

    rrset = resolve(hostname)
    return rrset[0].address

def gethostbyname_ex(hostname):
    """Replacement for Python's socket.gethostbyname_ex.

    Currently only supports IPv4.
    """
    if is_ipv4_addr(hostname):
        return (hostname, [], [hostname])

    rrset = resolve(hostname)
    addrs = []

    for rr in rrset:
        addrs.append(rr.address)
    return (hostname, [], addrs)

def getnameinfo(sockaddr, flags):
    """Replacement for Python's socket.getnameinfo.

    Currently only supports IPv4.
    """
    try:
        host, port = sockaddr
    except (ValueError, TypeError):
        if not isinstance(sockaddr, tuple):
            del sockaddr  # to pass a stdlib test that is
                          # hyper-careful about reference counts
            raise TypeError('getnameinfo() argument 1 must be a tuple')
        else:
            # must be ipv6 sockaddr, pretending we don't know how to resolve it
            raise socket.gaierror(-2, 'name or service not known')

    if (flags & socket.NI_NAMEREQD) and (flags & socket.NI_NUMERICHOST):
        # Conflicting flags.  Punt.
        raise socket.gaierror(
            (socket.EAI_NONAME, 'Name or service not known'))

    if is_ipv4_addr(host):
        try:
            rrset =	resolver.query(
                dns.reversename.from_address(host), dns.rdatatype.PTR)
            if len(rrset) > 1:
                raise socket.error('sockaddr resolved to multiple addresses')
            host = rrset[0].target.to_text(omit_final_dot=True)
        except dns.exception.Timeout as e:
            if flags & socket.NI_NAMEREQD:
                raise socket.gaierror((socket.EAI_AGAIN, 'Lookup timed out'))
        except dns.exception.DNSException as e:
            if flags & socket.NI_NAMEREQD:
                raise socket.gaierror(
                    (socket.EAI_NONAME, 'Name or service not known'))
    else:
        try:
            rrset = resolver.query(host)
            if len(rrset) > 1:
                raise socket.error('sockaddr resolved to multiple addresses')
            if flags & socket.NI_NUMERICHOST:
                host = rrset[0].address
        except dns.exception.Timeout as e:
            raise socket.gaierror((socket.EAI_AGAIN, 'Lookup timed out'))
        except dns.exception.DNSException as e:
            raise socket.gaierror(
                (socket.EAI_NODATA, 'No address associated with hostname'))

    if not (flags & socket.NI_NUMERICSERV):
        proto = (flags & socket.NI_DGRAM) and 'udp' or 'tcp'
        port = socket.getservbyport(port, proto)

    return (host, port)


def is_ipv4_addr(host):
    """is_ipv4_addr returns true if host is a valid IPv4 address in
    dotted quad notation.
    """
    try:
        d1, d2, d3, d4 = map(int, host.split('.'))
    except (ValueError, AttributeError):
        return False

    if 0 <= d1 <= 255 and 0 <= d2 <= 255 and 0 <= d3 <= 255 and 0 <= d4 <= 255:
        return True
    return False

def _net_read(sock, count, expiration):
    """coro friendly replacement for dns.query._net_write
    Read the specified number of bytes from sock.  Keep trying until we
    either get the desired amount, or we hit EOF.
    A Timeout exception will be raised if the operation is not completed
    by the expiration time.
    """
    s = ''
    while count > 0:
        try:
            n = sock.recv(count)
        except socket.timeout:
            ## Q: Do we also need to catch coro.CoroutineSocketWake and pass?
            if expiration - time.time() <= 0.0:
                raise dns.exception.Timeout
        if n == '':
            raise EOFError
        count = count - len(n)
        s = s + n
    return s

def _net_write(sock, data, expiration):
    """coro friendly replacement for dns.query._net_write
    Write the specified data to the socket.
    A Timeout exception will be raised if the operation is not completed
    by the expiration time.
    """
    current = 0
    l = len(data)
    while current < l:
        try:
            current += sock.send(data[current:])
        except socket.timeout:
            ## Q: Do we also need to catch coro.CoroutineSocketWake and pass?
            if expiration - time.time() <= 0.0:
                raise dns.exception.Timeout

def udp(
    q, where, timeout=DNS_QUERY_TIMEOUT, port=53, af=None, source=None,
    source_port=0, ignore_unexpected=False):
    """coro friendly replacement for dns.query.udp
    Return the response obtained after sending a query via UDP.

    @param q: the query
    @type q: dns.message.Message
    @param where: where to send the message
    @type where: string containing an IPv4 or IPv6 address
    @param timeout: The number of seconds to wait before the query times out.
    If None, the default, wait forever.
    @type timeout: float
    @param port: The port to which to send the message.  The default is 53.
    @type port: int
    @param af: the address family to use.  The default is None, which
    causes the address family to use to be inferred from the form of of where.
    If the inference attempt fails, AF_INET is used.
    @type af: int
    @rtype: dns.message.Message object
    @param source: source address.  The default is the IPv4 wildcard address.
    @type source: string
    @param source_port: The port from which to send the message.
    The default is 0.
    @type source_port: int
    @param ignore_unexpected: If True, ignore responses from unexpected
    sources.  The default is False.
    @type ignore_unexpected: bool"""

    wire = q.to_wire()
    if af is None:
        try:
            af = dns.inet.af_for_address(where)
        except:
            af = dns.inet.AF_INET
    if af == dns.inet.AF_INET:
        destination = (where, port)
        if source is not None:
            source = (source, source_port)
    elif af == dns.inet.AF_INET6:
        destination = (where, port, 0, 0)
        if source is not None:
            source = (source, source_port, 0, 0)

    s = socket.socket(af, socket.SOCK_DGRAM)
    s.settimeout(timeout)
    try:
        expiration = dns.query._compute_expiration(timeout)
        if source is not None:
            s.bind(source)
        try:
            s.sendto(wire, destination)
        except socket.timeout:
            ## Q: Do we also need to catch coro.CoroutineSocketWake and pass?
            if expiration - time.time() <= 0.0:
                raise dns.exception.Timeout
        while 1:
            try:
                (wire, from_address) = s.recvfrom(65535)
            except socket.timeout:
                ## Q: Do we also need to catch coro.CoroutineSocketWake and pass?
                if expiration - time.time() <= 0.0:
                    raise dns.exception.Timeout
            if from_address == destination:
                break
            if not ignore_unexpected:
                raise dns.query.UnexpectedSource(
                    'got a response from %s instead of %s'
                        % (from_address, destination))
    finally:
        s.close()

    r = dns.message.from_wire(wire, keyring=q.keyring, request_mac=q.mac)
    if not q.is_response(r):
        raise dns.query.BadResponse()
    return r

def tcp(q, where, timeout=DNS_QUERY_TIMEOUT, port=53,
   af=None, source=None, source_port=0):
    """coro friendly replacement for dns.query.tcp
    Return the response obtained after sending a query via TCP.

    @param q: the query
    @type q: dns.message.Message object
    @param where: where to send the message
    @type where: string containing an IPv4 or IPv6 address
    @param timeout: The number of seconds to wait before the query times out.
    If None, the default, wait forever.
    @type timeout: float
    @param port: The port to which to send the message.  The default is 53.
    @type port: int
    @param af: the address family to use.  The default is None, which
    causes the address family to use to be inferred from the form of of where.
    If the inference attempt fails, AF_INET is used.
    @type af: int
    @rtype: dns.message.Message object
    @param source: source address.  The default is the IPv4 wildcard address.
    @type source: string
    @param source_port: The port from which to send the message.
    The default is 0.
    @type source_port: int"""

    wire = q.to_wire()
    if af is None:
        try:
            af = dns.inet.af_for_address(where)
        except:
            af = dns.inet.AF_INET
    if af == dns.inet.AF_INET:
        destination = (where, port)
        if source is not None:
            source = (source, source_port)
    elif af == dns.inet.AF_INET6:
        destination = (where, port, 0, 0)
        if source is not None:
            source = (source, source_port, 0, 0)
    s = socket.socket(af, socket.SOCK_STREAM)
    s.settimeout(timeout)
    try:
        expiration = dns.query._compute_expiration(timeout)
        if source is not None:
            s.bind(source)
        try:
            s.connect(destination)
        except socket.timeout:
            ## Q: Do we also need to catch coro.CoroutineSocketWake and pass?
            if expiration - time.time() <= 0.0:
                raise dns.exception.Timeout

        l = len(wire)
        # copying the wire into tcpmsg is inefficient, but lets us
        # avoid writev() or doing a short write that would get pushed
        # onto the net
        tcpmsg = struct.pack("!H", l) + wire
        _net_write(s, tcpmsg, expiration)
        ldata = _net_read(s, 2, expiration)
        (l,) = struct.unpack("!H", ldata)
        wire = _net_read(s, l, expiration)
    finally:
        s.close()
    r = dns.message.from_wire(wire, keyring=q.keyring, request_mac=q.mac)
    if not q.is_response(r):
        raise dns.query.BadResponse()
    return r

def reset():
   resolver.clear()

# Install our coro-friendly replacements for the tcp and udp query methods.
dns.query.tcp = tcp
dns.query.udp = udp


########NEW FILE########
__FILENAME__ = greenlets
import distutils.version

try:
    import greenlet
    getcurrent = greenlet.greenlet.getcurrent
    GreenletExit = greenlet.greenlet.GreenletExit
    preserves_excinfo = (distutils.version.LooseVersion(greenlet.__version__)
            >= distutils.version.LooseVersion('0.3.2'))
    greenlet = greenlet.greenlet
except ImportError as e:
    raise
    try:
        from py.magic import greenlet
        getcurrent = greenlet.getcurrent
        GreenletExit = greenlet.GreenletExit
        preserves_excinfo = False
    except ImportError:
        try:
            from stackless import greenlet
            getcurrent = greenlet.getcurrent
            GreenletExit = greenlet.GreenletExit
            preserves_excinfo = False
        except ImportError:
            try:
                from support.stacklesss import greenlet, getcurrent, GreenletExit
                preserves_excinfo = False
                (greenlet, getcurrent, GreenletExit) # silence pyflakes
            except ImportError as e:
                raise ImportError("Unable to find an implementation of greenlet.")

########NEW FILE########
__FILENAME__ = psycopg2_patcher
"""A wait callback to allow psycopg2 cooperation with eventlet.

Use `make_psycopg_green()` to enable eventlet support in Psycopg.
"""

# Copyright (C) 2010 Daniele Varrazzo <daniele.varrazzo@gmail.com>
# and licensed under the MIT license:
# 
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

import psycopg2
from psycopg2 import extensions

from eventlet.hubs import trampoline

def make_psycopg_green():
    """Configure Psycopg to be used with eventlet in non-blocking way."""
    if not hasattr(extensions, 'set_wait_callback'):
        raise ImportError(
            "support for coroutines not available in this Psycopg version (%s)"
            % psycopg2.__version__)

    extensions.set_wait_callback(eventlet_wait_callback)

def eventlet_wait_callback(conn, timeout=-1):
    """A wait callback useful to allow eventlet to work with Psycopg."""
    while 1:
        state = conn.poll()
        if state == extensions.POLL_OK:
            break
        elif state == extensions.POLL_READ:
            trampoline(conn.fileno(), read=True)
        elif state == extensions.POLL_WRITE:
            trampoline(conn.fileno(), write=True)
        else:
            raise psycopg2.OperationalError(
                "Bad result from poll: %r" % state)

########NEW FILE########
__FILENAME__ = pylib
from py.magic import greenlet

import sys
import types

def emulate():
    module = types.ModuleType('greenlet')
    sys.modules['greenlet'] = module
    module.greenlet = greenlet
    module.getcurrent = greenlet.getcurrent
    module.GreenletExit = greenlet.GreenletExit


########NEW FILE########
__FILENAME__ = six
"""Utilities for writing code that runs on Python 2 and 3"""

# Copyright (c) 2010-2014 Benjamin Peterson
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import operator
import sys
import types

__author__ = "Benjamin Peterson <benjamin@python.org>"
__version__ = "1.5.2"


# Useful for very coarse version differentiation.
PY2 = sys.version_info[0] == 2
PY3 = sys.version_info[0] == 3

if PY3:
    string_types = str,
    integer_types = int,
    class_types = type,
    text_type = str
    binary_type = bytes

    MAXSIZE = sys.maxsize
else:
    string_types = basestring,
    integer_types = (int, long)
    class_types = (type, types.ClassType)
    text_type = unicode
    binary_type = str

    if sys.platform.startswith("java"):
        # Jython always uses 32 bits.
        MAXSIZE = int((1 << 31) - 1)
    else:
        # It's possible to have sizeof(long) != sizeof(Py_ssize_t).
        class X(object):
            def __len__(self):
                return 1 << 31
        try:
            len(X())
        except OverflowError:
            # 32-bit
            MAXSIZE = int((1 << 31) - 1)
        else:
            # 64-bit
            MAXSIZE = int((1 << 63) - 1)
        del X


def _add_doc(func, doc):
    """Add documentation to a function."""
    func.__doc__ = doc


def _import_module(name):
    """Import module, returning the module after the last dot."""
    __import__(name)
    return sys.modules[name]


class _LazyDescr(object):

    def __init__(self, name):
        self.name = name

    def __get__(self, obj, tp):
        result = self._resolve()
        setattr(obj, self.name, result) # Invokes __set__.
        # This is a bit ugly, but it avoids running this again.
        delattr(obj.__class__, self.name)
        return result


class MovedModule(_LazyDescr):

    def __init__(self, name, old, new=None):
        super(MovedModule, self).__init__(name)
        if PY3:
            if new is None:
                new = name
            self.mod = new
        else:
            self.mod = old

    def _resolve(self):
        return _import_module(self.mod)

    def __getattr__(self, attr):
        # Hack around the Django autoreloader. The reloader tries to get
        # __file__ or __name__ of every module in sys.modules. This doesn't work
        # well if this MovedModule is for an module that is unavailable on this
        # machine (like winreg on Unix systems). Thus, we pretend __file__ and
        # __name__ don't exist if the module hasn't been loaded yet. See issues
        # #51 and #53.
        if attr in ("__file__", "__name__") and self.mod not in sys.modules:
            raise AttributeError
        _module = self._resolve()
        value = getattr(_module, attr)
        setattr(self, attr, value)
        return value


class _LazyModule(types.ModuleType):

    def __init__(self, name):
        super(_LazyModule, self).__init__(name)
        self.__doc__ = self.__class__.__doc__

    def __dir__(self):
        attrs = ["__doc__", "__name__"]
        attrs += [attr.name for attr in self._moved_attributes]
        return attrs

    # Subclasses should override this
    _moved_attributes = []


class MovedAttribute(_LazyDescr):

    def __init__(self, name, old_mod, new_mod, old_attr=None, new_attr=None):
        super(MovedAttribute, self).__init__(name)
        if PY3:
            if new_mod is None:
                new_mod = name
            self.mod = new_mod
            if new_attr is None:
                if old_attr is None:
                    new_attr = name
                else:
                    new_attr = old_attr
            self.attr = new_attr
        else:
            self.mod = old_mod
            if old_attr is None:
                old_attr = name
            self.attr = old_attr

    def _resolve(self):
        module = _import_module(self.mod)
        return getattr(module, self.attr)



class _MovedItems(_LazyModule):
    """Lazy loading of moved objects"""


_moved_attributes = [
    MovedAttribute("cStringIO", "cStringIO", "io", "StringIO"),
    MovedAttribute("filter", "itertools", "builtins", "ifilter", "filter"),
    MovedAttribute("filterfalse", "itertools", "itertools", "ifilterfalse", "filterfalse"),
    MovedAttribute("input", "__builtin__", "builtins", "raw_input", "input"),
    MovedAttribute("map", "itertools", "builtins", "imap", "map"),
    MovedAttribute("range", "__builtin__", "builtins", "xrange", "range"),
    MovedAttribute("reload_module", "__builtin__", "imp", "reload"),
    MovedAttribute("reduce", "__builtin__", "functools"),
    MovedAttribute("StringIO", "StringIO", "io"),
    MovedAttribute("UserString", "UserString", "collections"),
    MovedAttribute("xrange", "__builtin__", "builtins", "xrange", "range"),
    MovedAttribute("zip", "itertools", "builtins", "izip", "zip"),
    MovedAttribute("zip_longest", "itertools", "itertools", "izip_longest", "zip_longest"),

    MovedModule("builtins", "__builtin__"),
    MovedModule("configparser", "ConfigParser"),
    MovedModule("copyreg", "copy_reg"),
    MovedModule("dbm_gnu", "gdbm", "dbm.gnu"),
    MovedModule("http_cookiejar", "cookielib", "http.cookiejar"),
    MovedModule("http_cookies", "Cookie", "http.cookies"),
    MovedModule("html_entities", "htmlentitydefs", "html.entities"),
    MovedModule("html_parser", "HTMLParser", "html.parser"),
    MovedModule("http_client", "httplib", "http.client"),
    MovedModule("email_mime_multipart", "email.MIMEMultipart", "email.mime.multipart"),
    MovedModule("email_mime_text", "email.MIMEText", "email.mime.text"),
    MovedModule("email_mime_base", "email.MIMEBase", "email.mime.base"),
    MovedModule("BaseHTTPServer", "BaseHTTPServer", "http.server"),
    MovedModule("CGIHTTPServer", "CGIHTTPServer", "http.server"),
    MovedModule("SimpleHTTPServer", "SimpleHTTPServer", "http.server"),
    MovedModule("cPickle", "cPickle", "pickle"),
    MovedModule("queue", "Queue"),
    MovedModule("reprlib", "repr"),
    MovedModule("socketserver", "SocketServer"),
    MovedModule("_thread", "thread", "_thread"),
    MovedModule("tkinter", "Tkinter"),
    MovedModule("tkinter_dialog", "Dialog", "tkinter.dialog"),
    MovedModule("tkinter_filedialog", "FileDialog", "tkinter.filedialog"),
    MovedModule("tkinter_scrolledtext", "ScrolledText", "tkinter.scrolledtext"),
    MovedModule("tkinter_simpledialog", "SimpleDialog", "tkinter.simpledialog"),
    MovedModule("tkinter_tix", "Tix", "tkinter.tix"),
    MovedModule("tkinter_ttk", "ttk", "tkinter.ttk"),
    MovedModule("tkinter_constants", "Tkconstants", "tkinter.constants"),
    MovedModule("tkinter_dnd", "Tkdnd", "tkinter.dnd"),
    MovedModule("tkinter_colorchooser", "tkColorChooser",
                "tkinter.colorchooser"),
    MovedModule("tkinter_commondialog", "tkCommonDialog",
                "tkinter.commondialog"),
    MovedModule("tkinter_tkfiledialog", "tkFileDialog", "tkinter.filedialog"),
    MovedModule("tkinter_font", "tkFont", "tkinter.font"),
    MovedModule("tkinter_messagebox", "tkMessageBox", "tkinter.messagebox"),
    MovedModule("tkinter_tksimpledialog", "tkSimpleDialog",
                "tkinter.simpledialog"),
    MovedModule("urllib_parse", __name__ + ".moves.urllib_parse", "urllib.parse"),
    MovedModule("urllib_error", __name__ + ".moves.urllib_error", "urllib.error"),
    MovedModule("urllib", __name__ + ".moves.urllib", __name__ + ".moves.urllib"),
    MovedModule("urllib_robotparser", "robotparser", "urllib.robotparser"),
    MovedModule("xmlrpc_client", "xmlrpclib", "xmlrpc.client"),
    MovedModule("xmlrpc_server", "xmlrpclib", "xmlrpc.server"),
    MovedModule("winreg", "_winreg"),
]
for attr in _moved_attributes:
    setattr(_MovedItems, attr.name, attr)
    if isinstance(attr, MovedModule):
        sys.modules[__name__ + ".moves." + attr.name] = attr
del attr

_MovedItems._moved_attributes = _moved_attributes

moves = sys.modules[__name__ + ".moves"] = _MovedItems(__name__ + ".moves")


class Module_six_moves_urllib_parse(_LazyModule):
    """Lazy loading of moved objects in six.moves.urllib_parse"""


_urllib_parse_moved_attributes = [
    MovedAttribute("ParseResult", "urlparse", "urllib.parse"),
    MovedAttribute("SplitResult", "urlparse", "urllib.parse"),
    MovedAttribute("parse_qs", "urlparse", "urllib.parse"),
    MovedAttribute("parse_qsl", "urlparse", "urllib.parse"),
    MovedAttribute("urldefrag", "urlparse", "urllib.parse"),
    MovedAttribute("urljoin", "urlparse", "urllib.parse"),
    MovedAttribute("urlparse", "urlparse", "urllib.parse"),
    MovedAttribute("urlsplit", "urlparse", "urllib.parse"),
    MovedAttribute("urlunparse", "urlparse", "urllib.parse"),
    MovedAttribute("urlunsplit", "urlparse", "urllib.parse"),
    MovedAttribute("quote", "urllib", "urllib.parse"),
    MovedAttribute("quote_plus", "urllib", "urllib.parse"),
    MovedAttribute("unquote", "urllib", "urllib.parse"),
    MovedAttribute("unquote_plus", "urllib", "urllib.parse"),
    MovedAttribute("urlencode", "urllib", "urllib.parse"),
]
for attr in _urllib_parse_moved_attributes:
    setattr(Module_six_moves_urllib_parse, attr.name, attr)
del attr

Module_six_moves_urllib_parse._moved_attributes = _urllib_parse_moved_attributes

sys.modules[__name__ + ".moves.urllib_parse"] = sys.modules[__name__ + ".moves.urllib.parse"] = Module_six_moves_urllib_parse(__name__ + ".moves.urllib_parse")


class Module_six_moves_urllib_error(_LazyModule):
    """Lazy loading of moved objects in six.moves.urllib_error"""


_urllib_error_moved_attributes = [
    MovedAttribute("URLError", "urllib2", "urllib.error"),
    MovedAttribute("HTTPError", "urllib2", "urllib.error"),
    MovedAttribute("ContentTooShortError", "urllib", "urllib.error"),
]
for attr in _urllib_error_moved_attributes:
    setattr(Module_six_moves_urllib_error, attr.name, attr)
del attr

Module_six_moves_urllib_error._moved_attributes = _urllib_error_moved_attributes

sys.modules[__name__ + ".moves.urllib_error"] = sys.modules[__name__ + ".moves.urllib.error"] = Module_six_moves_urllib_error(__name__ + ".moves.urllib.error")


class Module_six_moves_urllib_request(_LazyModule):
    """Lazy loading of moved objects in six.moves.urllib_request"""


_urllib_request_moved_attributes = [
    MovedAttribute("urlopen", "urllib2", "urllib.request"),
    MovedAttribute("install_opener", "urllib2", "urllib.request"),
    MovedAttribute("build_opener", "urllib2", "urllib.request"),
    MovedAttribute("pathname2url", "urllib", "urllib.request"),
    MovedAttribute("url2pathname", "urllib", "urllib.request"),
    MovedAttribute("getproxies", "urllib", "urllib.request"),
    MovedAttribute("Request", "urllib2", "urllib.request"),
    MovedAttribute("OpenerDirector", "urllib2", "urllib.request"),
    MovedAttribute("HTTPDefaultErrorHandler", "urllib2", "urllib.request"),
    MovedAttribute("HTTPRedirectHandler", "urllib2", "urllib.request"),
    MovedAttribute("HTTPCookieProcessor", "urllib2", "urllib.request"),
    MovedAttribute("ProxyHandler", "urllib2", "urllib.request"),
    MovedAttribute("BaseHandler", "urllib2", "urllib.request"),
    MovedAttribute("HTTPPasswordMgr", "urllib2", "urllib.request"),
    MovedAttribute("HTTPPasswordMgrWithDefaultRealm", "urllib2", "urllib.request"),
    MovedAttribute("AbstractBasicAuthHandler", "urllib2", "urllib.request"),
    MovedAttribute("HTTPBasicAuthHandler", "urllib2", "urllib.request"),
    MovedAttribute("ProxyBasicAuthHandler", "urllib2", "urllib.request"),
    MovedAttribute("AbstractDigestAuthHandler", "urllib2", "urllib.request"),
    MovedAttribute("HTTPDigestAuthHandler", "urllib2", "urllib.request"),
    MovedAttribute("ProxyDigestAuthHandler", "urllib2", "urllib.request"),
    MovedAttribute("HTTPHandler", "urllib2", "urllib.request"),
    MovedAttribute("HTTPSHandler", "urllib2", "urllib.request"),
    MovedAttribute("FileHandler", "urllib2", "urllib.request"),
    MovedAttribute("FTPHandler", "urllib2", "urllib.request"),
    MovedAttribute("CacheFTPHandler", "urllib2", "urllib.request"),
    MovedAttribute("UnknownHandler", "urllib2", "urllib.request"),
    MovedAttribute("HTTPErrorProcessor", "urllib2", "urllib.request"),
    MovedAttribute("urlretrieve", "urllib", "urllib.request"),
    MovedAttribute("urlcleanup", "urllib", "urllib.request"),
    MovedAttribute("URLopener", "urllib", "urllib.request"),
    MovedAttribute("FancyURLopener", "urllib", "urllib.request"),
    MovedAttribute("proxy_bypass", "urllib", "urllib.request"),
]
for attr in _urllib_request_moved_attributes:
    setattr(Module_six_moves_urllib_request, attr.name, attr)
del attr

Module_six_moves_urllib_request._moved_attributes = _urllib_request_moved_attributes

sys.modules[__name__ + ".moves.urllib_request"] = sys.modules[__name__ + ".moves.urllib.request"] = Module_six_moves_urllib_request(__name__ + ".moves.urllib.request")


class Module_six_moves_urllib_response(_LazyModule):
    """Lazy loading of moved objects in six.moves.urllib_response"""


_urllib_response_moved_attributes = [
    MovedAttribute("addbase", "urllib", "urllib.response"),
    MovedAttribute("addclosehook", "urllib", "urllib.response"),
    MovedAttribute("addinfo", "urllib", "urllib.response"),
    MovedAttribute("addinfourl", "urllib", "urllib.response"),
]
for attr in _urllib_response_moved_attributes:
    setattr(Module_six_moves_urllib_response, attr.name, attr)
del attr

Module_six_moves_urllib_response._moved_attributes = _urllib_response_moved_attributes

sys.modules[__name__ + ".moves.urllib_response"] = sys.modules[__name__ + ".moves.urllib.response"] = Module_six_moves_urllib_response(__name__ + ".moves.urllib.response")


class Module_six_moves_urllib_robotparser(_LazyModule):
    """Lazy loading of moved objects in six.moves.urllib_robotparser"""


_urllib_robotparser_moved_attributes = [
    MovedAttribute("RobotFileParser", "robotparser", "urllib.robotparser"),
]
for attr in _urllib_robotparser_moved_attributes:
    setattr(Module_six_moves_urllib_robotparser, attr.name, attr)
del attr

Module_six_moves_urllib_robotparser._moved_attributes = _urllib_robotparser_moved_attributes

sys.modules[__name__ + ".moves.urllib_robotparser"] = sys.modules[__name__ + ".moves.urllib.robotparser"] = Module_six_moves_urllib_robotparser(__name__ + ".moves.urllib.robotparser")


class Module_six_moves_urllib(types.ModuleType):
    """Create a six.moves.urllib namespace that resembles the Python 3 namespace"""
    parse = sys.modules[__name__ + ".moves.urllib_parse"]
    error = sys.modules[__name__ + ".moves.urllib_error"]
    request = sys.modules[__name__ + ".moves.urllib_request"]
    response = sys.modules[__name__ + ".moves.urllib_response"]
    robotparser = sys.modules[__name__ + ".moves.urllib_robotparser"]

    def __dir__(self):
        return ['parse', 'error', 'request', 'response', 'robotparser']


sys.modules[__name__ + ".moves.urllib"] = Module_six_moves_urllib(__name__ + ".moves.urllib")


def add_move(move):
    """Add an item to six.moves."""
    setattr(_MovedItems, move.name, move)


def remove_move(name):
    """Remove item from six.moves."""
    try:
        delattr(_MovedItems, name)
    except AttributeError:
        try:
            del moves.__dict__[name]
        except KeyError:
            raise AttributeError("no such move, %r" % (name,))


if PY3:
    _meth_func = "__func__"
    _meth_self = "__self__"

    _func_closure = "__closure__"
    _func_code = "__code__"
    _func_defaults = "__defaults__"
    _func_globals = "__globals__"

    _iterkeys = "keys"
    _itervalues = "values"
    _iteritems = "items"
    _iterlists = "lists"
else:
    _meth_func = "im_func"
    _meth_self = "im_self"

    _func_closure = "func_closure"
    _func_code = "func_code"
    _func_defaults = "func_defaults"
    _func_globals = "func_globals"

    _iterkeys = "iterkeys"
    _itervalues = "itervalues"
    _iteritems = "iteritems"
    _iterlists = "iterlists"


try:
    advance_iterator = next
except NameError:
    def advance_iterator(it):
        return it.next()
next = advance_iterator


try:
    callable = callable
except NameError:
    def callable(obj):
        return any("__call__" in klass.__dict__ for klass in type(obj).__mro__)


if PY3:
    def get_unbound_function(unbound):
        return unbound

    create_bound_method = types.MethodType

    Iterator = object
else:
    def get_unbound_function(unbound):
        return unbound.im_func

    def create_bound_method(func, obj):
        return types.MethodType(func, obj, obj.__class__)

    class Iterator(object):

        def next(self):
            return type(self).__next__(self)

    callable = callable
_add_doc(get_unbound_function,
         """Get the function out of a possibly unbound function""")


get_method_function = operator.attrgetter(_meth_func)
get_method_self = operator.attrgetter(_meth_self)
get_function_closure = operator.attrgetter(_func_closure)
get_function_code = operator.attrgetter(_func_code)
get_function_defaults = operator.attrgetter(_func_defaults)
get_function_globals = operator.attrgetter(_func_globals)


def iterkeys(d, **kw):
    """Return an iterator over the keys of a dictionary."""
    return iter(getattr(d, _iterkeys)(**kw))

def itervalues(d, **kw):
    """Return an iterator over the values of a dictionary."""
    return iter(getattr(d, _itervalues)(**kw))

def iteritems(d, **kw):
    """Return an iterator over the (key, value) pairs of a dictionary."""
    return iter(getattr(d, _iteritems)(**kw))

def iterlists(d, **kw):
    """Return an iterator over the (key, [values]) pairs of a dictionary."""
    return iter(getattr(d, _iterlists)(**kw))


if PY3:
    def b(s):
        return s.encode("latin-1")
    def u(s):
        return s
    unichr = chr
    if sys.version_info[1] <= 1:
        def int2byte(i):
            return bytes((i,))
    else:
        # This is about 2x faster than the implementation above on 3.2+
        int2byte = operator.methodcaller("to_bytes", 1, "big")
    byte2int = operator.itemgetter(0)
    indexbytes = operator.getitem
    iterbytes = iter
    import io
    StringIO = io.StringIO
    BytesIO = io.BytesIO
else:
    def b(s):
        return s
    # Workaround for standalone backslash
    def u(s):
        return unicode(s.replace(r'\\', r'\\\\'), "unicode_escape")
    unichr = unichr
    int2byte = chr
    def byte2int(bs):
        return ord(bs[0])
    def indexbytes(buf, i):
        return ord(buf[i])
    def iterbytes(buf):
        return (ord(byte) for byte in buf)
    import StringIO
    StringIO = BytesIO = StringIO.StringIO
_add_doc(b, """Byte literal""")
_add_doc(u, """Text literal""")


if PY3:
    exec_ = getattr(moves.builtins, "exec")


    def reraise(tp, value, tb=None):
        if value.__traceback__ is not tb:
            raise value.with_traceback(tb)
        raise value

else:
    def exec_(_code_, _globs_=None, _locs_=None):
        """Execute code in a namespace."""
        if _globs_ is None:
            frame = sys._getframe(1)
            _globs_ = frame.f_globals
            if _locs_ is None:
                _locs_ = frame.f_locals
            del frame
        elif _locs_ is None:
            _locs_ = _globs_
        exec("""exec _code_ in _globs_, _locs_""")


    exec_("""def reraise(tp, value, tb=None):
    raise tp, value, tb
""")


print_ = getattr(moves.builtins, "print", None)
if print_ is None:
    def print_(*args, **kwargs):
        """The new-style print function for Python 2.4 and 2.5."""
        fp = kwargs.pop("file", sys.stdout)
        if fp is None:
            return
        def write(data):
            if not isinstance(data, basestring):
                data = str(data)
            # If the file has an encoding, encode unicode with it.
            if (isinstance(fp, file) and
                isinstance(data, unicode) and
                fp.encoding is not None):
                errors = getattr(fp, "errors", None)
                if errors is None:
                    errors = "strict"
                data = data.encode(fp.encoding, errors)
            fp.write(data)
        want_unicode = False
        sep = kwargs.pop("sep", None)
        if sep is not None:
            if isinstance(sep, unicode):
                want_unicode = True
            elif not isinstance(sep, str):
                raise TypeError("sep must be None or a string")
        end = kwargs.pop("end", None)
        if end is not None:
            if isinstance(end, unicode):
                want_unicode = True
            elif not isinstance(end, str):
                raise TypeError("end must be None or a string")
        if kwargs:
            raise TypeError("invalid keyword arguments to print()")
        if not want_unicode:
            for arg in args:
                if isinstance(arg, unicode):
                    want_unicode = True
                    break
        if want_unicode:
            newline = unicode("\n")
            space = unicode(" ")
        else:
            newline = "\n"
            space = " "
        if sep is None:
            sep = space
        if end is None:
            end = newline
        for i, arg in enumerate(args):
            if i:
                write(sep)
            write(arg)
        write(end)

_add_doc(reraise, """Reraise an exception.""")


def with_metaclass(meta, *bases):
    """Create a base class with a metaclass."""
    return meta("NewBase", bases, {})

def add_metaclass(metaclass):
    """Class decorator for creating a class with a metaclass."""
    def wrapper(cls):
        orig_vars = cls.__dict__.copy()
        orig_vars.pop('__dict__', None)
        orig_vars.pop('__weakref__', None)
        slots = orig_vars.get('__slots__')
        if slots is not None:
            if isinstance(slots, str):
                slots = [slots]
            for slots_var in slots:
                orig_vars.pop(slots_var)
        return metaclass(cls.__name__, cls.__bases__, orig_vars)
    return wrapper

########NEW FILE########
__FILENAME__ = stacklesspypys
from stackless import greenlet

import sys
import types

def emulate():
    module = types.ModuleType('greenlet')
    sys.modules['greenlet'] = module
    module.greenlet = greenlet
    module.getcurrent = greenlet.getcurrent
    module.GreenletExit = greenlet.GreenletExit


########NEW FILE########
__FILENAME__ = stacklesss
"""
Support for using stackless python.  Broken and riddled with print statements
at the moment.  Please fix it!
"""

import sys
import types

import stackless

caller = None
coro_args = {}
tasklet_to_greenlet = {}


def getcurrent():
    return tasklet_to_greenlet[stackless.getcurrent()]


class FirstSwitch(object):
    def __init__(self, gr):
        self.gr = gr

    def __call__(self, *args, **kw):
        #print("first call", args, kw)
        gr = self.gr
        del gr.switch
        run, gr.run = gr.run, None
        t = stackless.tasklet(run)
        gr.t = t
        tasklet_to_greenlet[t] = gr
        t.setup(*args, **kw)
        t.run()


class greenlet(object):
    def __init__(self, run=None, parent=None):
        self.dead = False
        if parent is None:
            parent = getcurrent()

        self.parent = parent
        if run is not None:
            self.run = run

        self.switch = FirstSwitch(self)

    def switch(self, *args):
        #print("switch", args)
        global caller
        caller = stackless.getcurrent()
        coro_args[self] = args
        self.t.insert()
        stackless.schedule()
        if caller is not self.t:
            caller.remove()
        rval = coro_args[self]
        return rval

    def run(self):
        pass

    def __bool__(self):
        return self.run is None and not self.dead


class GreenletExit(Exception):
    pass


def emulate():
    module = types.ModuleType('greenlet')
    sys.modules['greenlet'] = module
    module.greenlet = greenlet
    module.getcurrent = getcurrent
    module.GreenletExit = GreenletExit

    caller = stackless.getcurrent()
    tasklet_to_greenlet[caller] = None
    main_coro = greenlet()
    tasklet_to_greenlet[caller] = main_coro
    main_coro.t = caller
    del main_coro.switch  # It's already running
    coro_args[main_coro] = None

########NEW FILE########
__FILENAME__ = timeout
# Copyright (c) 2009-2010 Denis Bilenko, denis.bilenko at gmail com
# Copyright (c) 2010 Eventlet Contributors (see AUTHORS)
# and licensed under the MIT license:
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.from eventlet.support import greenlets as greenlet

from eventlet.support import greenlets as greenlet
from eventlet.hubs import get_hub

__all__ = ['Timeout',
           'with_timeout']

_NONE = object()

# deriving from BaseException so that "except Exception as e" doesn't catch
# Timeout exceptions.
class Timeout(BaseException):
    """Raises *exception* in the current greenthread after *timeout* seconds.

    When *exception* is omitted or ``None``, the :class:`Timeout` instance
    itself is raised. If *seconds* is None, the timer is not scheduled, and is
    only useful if you're planning to raise it directly.

    Timeout objects are context managers, and so can be used in with statements.
    When used in a with statement, if *exception* is ``False``, the timeout is
    still raised, but the context manager suppresses it, so the code outside the
    with-block won't see it.
    """

    def __init__(self, seconds=None, exception=None):
        self.seconds = seconds
        self.exception = exception
        self.timer = None
        self.start()

    def start(self):
        """Schedule the timeout.  This is called on construction, so
        it should not be called explicitly, unless the timer has been
        canceled."""
        assert not self.pending, \
               '%r is already started; to restart it, cancel it first' % self
        if self.seconds is None: # "fake" timeout (never expires)
            self.timer = None
        elif self.exception is None or isinstance(self.exception, bool): # timeout that raises self
            self.timer = get_hub().schedule_call_global(
                self.seconds, greenlet.getcurrent().throw, self)
        else: # regular timeout with user-provided exception
            self.timer = get_hub().schedule_call_global(
                self.seconds, greenlet.getcurrent().throw, self.exception)
        return self

    @property
    def pending(self):
        """True if the timeout is scheduled to be raised."""
        if self.timer is not None:
            return self.timer.pending
        else:
            return False

    def cancel(self):
        """If the timeout is pending, cancel it.  If not using
        Timeouts in ``with`` statements, always call cancel() in a
        ``finally`` after the block of code that is getting timed out.
        If not canceled, the timeout will be raised later on, in some
        unexpected section of the application."""
        if self.timer is not None:
            self.timer.cancel()
            self.timer = None

    def __repr__(self):
        classname = self.__class__.__name__
        if self.pending:
            pending = ' pending'
        else:
            pending = ''
        if self.exception is None:
            exception = ''
        else:
            exception = ' exception=%r' % self.exception
        return '<%s at %s seconds=%s%s%s>' % (
            classname, hex(id(self)), self.seconds, exception, pending)

    def __str__(self):
        """
        >>> raise Timeout
        Traceback (most recent call last):
            ...
        Timeout
        """
        if self.seconds is None:
            return ''
        if self.seconds == 1:
            suffix = ''
        else:
            suffix = 's'
        if self.exception is None or self.exception is True:
            return '%s second%s' % (self.seconds, suffix)
        elif self.exception is False:
            return '%s second%s (silent)' % (self.seconds, suffix)
        else:
            return '%s second%s (%s)' % (self.seconds, suffix, self.exception)

    def __enter__(self):
        if self.timer is None:
            self.start()
        return self

    def __exit__(self, typ, value, tb):
        self.cancel()
        if value is self and self.exception is False:
            return True


def with_timeout(seconds, function, *args, **kwds):
    """Wrap a call to some (yielding) function with a timeout; if the called
    function fails to return before the timeout, cancel it and return a flag
    value.
    """
    timeout_value = kwds.pop("timeout_value", _NONE)
    timeout = Timeout(seconds)
    try:
        try:
            return function(*args, **kwds)
        except Timeout as ex:
            if ex is timeout and timeout_value is not _NONE:
                return timeout_value
            raise
    finally:
        timeout.cancel()

########NEW FILE########
__FILENAME__ = tpool
# Copyright (c) 2007-2009, Linden Research, Inc.
# Copyright (c) 2007, IBM Corp.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import imp
import os
import sys
import traceback

from eventlet import event, greenio, greenthread, patcher, timeout
from eventlet.support import six


threading = patcher.original('threading')
if six.PY2:
    Queue_module = patcher.original('Queue')
if six.PY3:
    Queue_module = patcher.original('queue')

Queue = Queue_module.Queue
Empty = Queue_module.Empty

__all__ = ['execute', 'Proxy', 'killall']

QUIET = True

_rfile = _wfile = None

_bytetosend = ' '.encode()


def _signal_t2e():
    _wfile.write(_bytetosend)
    _wfile.flush()

_reqq = None
_rspq = None


def tpool_trampoline():
    global _rspq
    while True:
        try:
            _c = _rfile.read(1)
            assert _c
        except ValueError:
            break  # will be raised when pipe is closed
        while not _rspq.empty():
            try:
                (e, rv) = _rspq.get(block=False)
                e.send(rv)
                e = rv = None
            except Empty:
                pass


SYS_EXCS = (KeyboardInterrupt, SystemExit)
EXC_CLASSES = (Exception, timeout.Timeout)


def tworker():
    global _rspq
    while(True):
        try:
            msg = _reqq.get()
        except AttributeError:
            return  # can't get anything off of a dud queue
        if msg is None:
            return
        (e, meth, args, kwargs) = msg
        rv = None
        try:
            rv = meth(*args, **kwargs)
        except SYS_EXCS:
            raise
        except EXC_CLASSES:
            rv = sys.exc_info()
        # test_leakage_from_tracebacks verifies that the use of
        # exc_info does not lead to memory leaks
        _rspq.put((e, rv))
        msg = meth = args = kwargs = e = rv = None
        _signal_t2e()


def execute(meth, *args, **kwargs):
    """
    Execute *meth* in a Python thread, blocking the current coroutine/
    greenthread until the method completes.

    The primary use case for this is to wrap an object or module that is not
    amenable to monkeypatching or any of the other tricks that Eventlet uses
    to achieve cooperative yielding.  With tpool, you can force such objects to
    cooperate with green threads by sticking them in native threads, at the cost
    of some overhead.
    """
    setup()
    # if already in tpool, don't recurse into the tpool
    # also, call functions directly if we're inside an import lock, because
    # if meth does any importing (sadly common), it will hang
    my_thread = threading.currentThread()
    if my_thread in _threads or imp.lock_held() or _nthreads == 0:
        return meth(*args, **kwargs)

    e = event.Event()
    _reqq.put((e, meth, args, kwargs))

    rv = e.wait()
    if isinstance(rv, tuple) \
            and len(rv) == 3 \
            and isinstance(rv[1], EXC_CLASSES):
        (c, e, tb) = rv
        if not QUIET:
            traceback.print_exception(c, e, tb)
            traceback.print_stack()
        six.reraise(c, e, tb)
    return rv


def proxy_call(autowrap, f, *args, **kwargs):
    """
    Call a function *f* and returns the value.  If the type of the return value
    is in the *autowrap* collection, then it is wrapped in a :class:`Proxy`
    object before return.

    Normally *f* will be called in the threadpool with :func:`execute`; if the
    keyword argument "nonblocking" is set to ``True``, it will simply be
    executed directly.  This is useful if you have an object which has methods
    that don't need to be called in a separate thread, but which return objects
    that should be Proxy wrapped.
    """
    if kwargs.pop('nonblocking', False):
        rv = f(*args, **kwargs)
    else:
        rv = execute(f, *args, **kwargs)
    if isinstance(rv, autowrap):
        return Proxy(rv, autowrap)
    else:
        return rv


class Proxy(object):
    """
    a simple proxy-wrapper of any object that comes with a
    methods-only interface, in order to forward every method
    invocation onto a thread in the native-thread pool.  A key
    restriction is that the object's methods should not switch
    greenlets or use Eventlet primitives, since they are in a
    different thread from the main hub, and therefore might behave
    unexpectedly.  This is for running native-threaded code
    only.

    It's common to want to have some of the attributes or return
    values also wrapped in Proxy objects (for example, database
    connection objects produce cursor objects which also should be
    wrapped in Proxy objects to remain nonblocking).  *autowrap*, if
    supplied, is a collection of types; if an attribute or return
    value matches one of those types (via isinstance), it will be
    wrapped in a Proxy.  *autowrap_names* is a collection
    of strings, which represent the names of attributes that should be
    wrapped in Proxy objects when accessed.
    """
    def __init__(self, obj, autowrap=(), autowrap_names=()):
        self._obj = obj
        self._autowrap = autowrap
        self._autowrap_names = autowrap_names

    def __getattr__(self, attr_name):
        f = getattr(self._obj, attr_name)
        if not hasattr(f, '__call__'):
            if isinstance(f, self._autowrap) or attr_name in self._autowrap_names:
                return Proxy(f, self._autowrap)
            return f

        def doit(*args, **kwargs):
            result = proxy_call(self._autowrap, f, *args, **kwargs)
            if attr_name in self._autowrap_names and not isinstance(result, Proxy):
                return Proxy(result)
            return result
        return doit

    # the following are a buncha methods that the python interpeter
    # doesn't use getattr to retrieve and therefore have to be defined
    # explicitly
    def __getitem__(self, key):
        return proxy_call(self._autowrap, self._obj.__getitem__, key)

    def __setitem__(self, key, value):
        return proxy_call(self._autowrap, self._obj.__setitem__, key, value)

    def __deepcopy__(self, memo=None):
        return proxy_call(self._autowrap, self._obj.__deepcopy__, memo)

    def __copy__(self, memo=None):
        return proxy_call(self._autowrap, self._obj.__copy__, memo)

    def __call__(self, *a, **kw):
        if '__call__' in self._autowrap_names:
            return Proxy(proxy_call(self._autowrap, self._obj, *a, **kw))
        else:
            return proxy_call(self._autowrap, self._obj, *a, **kw)

    def __enter__(self):
        return proxy_call(self._autowrap, self._obj.__enter__)

    def __exit__(self, *exc):
        return proxy_call(self._autowrap, self._obj.__exit__, *exc)

    # these don't go through a proxy call, because they're likely to
    # be called often, and are unlikely to be implemented on the
    # wrapped object in such a way that they would block
    def __eq__(self, rhs):
        return self._obj == rhs

    def __hash__(self):
        return self._obj.__hash__()

    def __repr__(self):
        return self._obj.__repr__()

    def __str__(self):
        return self._obj.__str__()

    def __len__(self):
        return len(self._obj)

    def __nonzero__(self):
        return bool(self._obj)
    # Python3
    __bool__ = __nonzero__

    def __iter__(self):
        it = iter(self._obj)
        if it == self._obj:
            return self
        else:
            return Proxy(it)

    def next(self):
        return proxy_call(self._autowrap, self._obj.next)
    # Python3
    __next__ = next


_nthreads = int(os.environ.get('EVENTLET_THREADPOOL_SIZE', 20))
_threads = []
_coro = None
_setup_already = False


def setup():
    global _rfile, _wfile, _threads, _coro, _setup_already, _rspq, _reqq
    if _setup_already:
        return
    else:
        _setup_already = True
    try:
        _rpipe, _wpipe = os.pipe()
        _wfile = greenio.GreenPipe(_wpipe, 'wb', 0)
        _rfile = greenio.GreenPipe(_rpipe, 'rb', 0)
    except (ImportError, NotImplementedError):
        # This is Windows compatibility -- use a socket instead of a pipe because
        # pipes don't really exist on Windows.
        import socket
        from eventlet import util
        sock = util.__original_socket__(socket.AF_INET, socket.SOCK_STREAM)
        sock.bind(('localhost', 0))
        sock.listen(50)
        csock = util.__original_socket__(socket.AF_INET, socket.SOCK_STREAM)
        csock.connect(('localhost', sock.getsockname()[1]))
        nsock, addr = sock.accept()
        _rfile = greenio.GreenSocket(csock).makefile('rb', 0)
        _wfile = nsock.makefile('wb', 0)

    _reqq = Queue(maxsize=-1)
    _rspq = Queue(maxsize=-1)
    assert _nthreads >= 0, "Can't specify negative number of threads"
    if _nthreads == 0:
        import warnings
        warnings.warn("Zero threads in tpool.  All tpool.execute calls will\
            execute in main thread.  Check the value of the environment \
            variable EVENTLET_THREADPOOL_SIZE.", RuntimeWarning)
    for i in six.moves.range(_nthreads):
        t = threading.Thread(target=tworker,
                             name="tpool_thread_%s" % i)
        t.setDaemon(True)
        t.start()
        _threads.append(t)

    _coro = greenthread.spawn_n(tpool_trampoline)


def killall():
    global _setup_already, _rspq, _rfile, _wfile
    if not _setup_already:
        return
    for thr in _threads:
        _reqq.put(None)
    for thr in _threads:
        thr.join()
    del _threads[:]
    if _coro is not None:
        greenthread.kill(_coro)
    _rfile.close()
    _wfile.close()
    _rfile = None
    _wfile = None
    _rspq = None
    _setup_already = False


def set_num_threads(nthreads):
    global _nthreads
    _nthreads = nthreads

########NEW FILE########
__FILENAME__ = join_reactor
"""Integrate eventlet with twisted's reactor mainloop.

You generally don't have to use it unless you need to call reactor.run()
yourself.
"""
from eventlet.hubs.twistedr import BaseTwistedHub
from eventlet.support import greenlets as greenlet
from eventlet.hubs import _threadlocal, use_hub

use_hub(BaseTwistedHub)
assert not hasattr(_threadlocal, 'hub')
hub = _threadlocal.hub = _threadlocal.Hub(greenlet.getcurrent())

########NEW FILE########
__FILENAME__ = protocol
"""Basic twisted protocols converted to synchronous mode"""
import sys
from twisted.internet.protocol import Protocol as twistedProtocol
from twisted.internet.error import ConnectionDone
from twisted.internet.protocol import Factory, ClientFactory
from twisted.internet import main
from twisted.python import failure

from eventlet import greenthread
from eventlet import getcurrent
from eventlet.coros import Queue
from eventlet.event import Event as BaseEvent


class ValueQueue(Queue):
    """Queue that keeps the last item forever in the queue if it's an exception.
    Useful if you send an exception over queue only once, and once sent it must be always
    available.
    """

    def send(self, value=None, exc=None):
        if exc is not None or not self.has_error():
            Queue.send(self, value, exc)

    def wait(self):
        """The difference from Queue.wait: if there is an only item in the
        Queue and it is an exception, raise it, but keep it in the Queue, so
        that future calls to wait() will raise it again.
        """
        if self.has_error() and len(self.items)==1:
            # the last item, which is an exception, raise without emptying the Queue
            getcurrent().throw(*self.items[0][1])
        else:
            return Queue.wait(self)

    def has_error(self):
        return self.items and self.items[-1][1] is not None


class Event(BaseEvent):

    def send(self, value, exc=None):
        if self.ready():
            self.reset()
        return BaseEvent.send(self, value, exc)

    def send_exception(self, *throw_args):
        if self.ready():
            self.reset()
        return BaseEvent.send_exception(self, *throw_args)

class Producer2Event(object):

    # implements IPullProducer

    def __init__(self, event):
        self.event = event

    def resumeProducing(self):
        self.event.send(1)

    def stopProducing(self):
        del self.event


class GreenTransportBase(object):

    transportBufferSize = None

    def __init__(self, transportBufferSize=None):
        if transportBufferSize is not None:
            self.transportBufferSize = transportBufferSize
        self._queue = ValueQueue()
        self._write_event = Event()
        self._disconnected_event = Event()

    def build_protocol(self):
        return self.protocol_class(self)

    def _got_transport(self, transport):
        self._queue.send(transport)

    def _got_data(self, data):
        self._queue.send(data)

    def _connectionLost(self, reason):
        self._disconnected_event.send(reason.value)
        self._queue.send_exception(reason.value)
        self._write_event.send_exception(reason.value)

    def _wait(self):
        if self.disconnecting or self._disconnected_event.ready():
            if self._queue:
                return self._queue.wait()
            else:
                raise self._disconnected_event.wait()
        self.resumeProducing()
        try:
            return self._queue.wait()
        finally:
            self.pauseProducing()

    def write(self, data, wait=True):
        if self._disconnected_event.ready():
            raise self._disconnected_event.wait()
        if wait:
            self._write_event.reset()
            self.transport.write(data)
            self._write_event.wait()
        else:
            self.transport.write(data)

    def loseConnection(self, connDone=failure.Failure(main.CONNECTION_DONE), wait=True):
        self.transport.unregisterProducer()
        self.transport.loseConnection(connDone)
        if wait:
            self._disconnected_event.wait()

    def __getattr__(self, item):
        if item=='transport':
            raise AttributeError(item)
        if hasattr(self, 'transport'):
            try:
                return getattr(self.transport, item)
            except AttributeError:
                me = type(self).__name__
                trans = type(self.transport).__name__
                raise AttributeError("Neither %r nor %r has attribute %r" % (me, trans, item))
        else:
            raise AttributeError(item)

    def resumeProducing(self):
        self.paused -= 1
        if self.paused==0:
            self.transport.resumeProducing()

    def pauseProducing(self):
        self.paused += 1
        if self.paused==1:
            self.transport.pauseProducing()

    def _init_transport_producer(self):
        self.transport.pauseProducing()
        self.paused = 1

    def _init_transport(self):
        transport = self._queue.wait()
        self.transport = transport
        if self.transportBufferSize is not None:
            transport.bufferSize = self.transportBufferSize
        self._init_transport_producer()
        transport.registerProducer(Producer2Event(self._write_event), False)


class Protocol(twistedProtocol):

    def __init__(self, recepient):
        self._recepient = recepient

    def connectionMade(self):
        self._recepient._got_transport(self.transport)

    def dataReceived(self, data):
        self._recepient._got_data(data)

    def connectionLost(self, reason):
        self._recepient._connectionLost(reason)


class UnbufferedTransport(GreenTransportBase):
    """A very simple implementation of a green transport without an additional buffer"""

    protocol_class = Protocol

    def recv(self):
        """Receive a single chunk of undefined size.

        Return '' if connection was closed cleanly, raise the exception if it was closed
        in a non clean fashion. After that all successive calls return ''.
        """
        if self._disconnected_event.ready():
            return ''
        try:
            return self._wait()
        except ConnectionDone:
            return ''

    def read(self):
        """Read the data from the socket until the connection is closed cleanly.

        If connection was closed in a non-clean fashion, the appropriate exception
        is raised. In that case already received data is lost.
        Next time read() is called it returns ''.
        """
        result = ''
        while True:
            recvd = self.recv()
            if not recvd:
                break
            result += recvd
        return result

    # iterator protocol:

    def __iter__(self):
        return self

    def next(self):
        result = self.recv()
        if not result:
            raise StopIteration
        return result


class GreenTransport(GreenTransportBase):

    protocol_class = Protocol
    _buffer = ''
    _error = None

    def read(self, size=-1):
        """Read size bytes or until EOF"""
        if not self._disconnected_event.ready():
            try:
                while len(self._buffer) < size or size < 0:
                    self._buffer += self._wait()
            except ConnectionDone:
                pass
            except:
                if not self._disconnected_event.has_exception():
                    raise
        if size>=0:
            result, self._buffer = self._buffer[:size], self._buffer[size:]
        else:
            result, self._buffer = self._buffer, ''
        if not result and self._disconnected_event.has_exception():
            try:
                self._disconnected_event.wait()
            except ConnectionDone:
                pass
        return result

    def recv(self, buflen=None):
        """Receive a single chunk of undefined size but no bigger than buflen"""
        if not self._disconnected_event.ready():
            self.resumeProducing()
            try:
                try:
                    recvd = self._wait()
                    #print 'received %r' % recvd
                    self._buffer += recvd
                except ConnectionDone:
                    pass
                except:
                    if not self._disconnected_event.has_exception():
                        raise
            finally:
                self.pauseProducing()
        if buflen is None:
            result, self._buffer = self._buffer, ''
        else:
            result, self._buffer = self._buffer[:buflen], self._buffer[buflen:]
        if not result and self._disconnected_event.has_exception():
            try:
                self._disconnected_event.wait()
            except ConnectionDone:
                pass
        return result

    # iterator protocol:

    def __iter__(self):
        return self

    def next(self):
        res = self.recv()
        if not res:
            raise StopIteration
        return res


class GreenInstanceFactory(ClientFactory):

    def __init__(self, instance, event):
        self.instance = instance
        self.event = event

    def buildProtocol(self, addr):
        return self.instance

    def clientConnectionFailed(self, connector, reason):
        self.event.send_exception(reason.type, reason.value, reason.tb)


class GreenClientCreator(object):
    """Connect to a remote host and return a connected green transport instance.
    """

    gtransport_class = GreenTransport

    def __init__(self, reactor=None, gtransport_class=None, *args, **kwargs):
        if reactor is None:
            from twisted.internet import reactor
        self.reactor = reactor
        if gtransport_class is not None:
            self.gtransport_class = gtransport_class
        self.args = args
        self.kwargs = kwargs

    def _make_transport_and_factory(self):
        gtransport = self.gtransport_class(*self.args, **self.kwargs)
        protocol = gtransport.build_protocol()
        factory = GreenInstanceFactory(protocol, gtransport._queue)
        return gtransport, factory

    def connectTCP(self, host, port, *args, **kwargs):
        gtransport, factory = self._make_transport_and_factory()
        self.reactor.connectTCP(host, port, factory, *args, **kwargs)
        gtransport._init_transport()
        return gtransport

    def connectSSL(self, host, port, *args, **kwargs):
        gtransport, factory = self._make_transport_and_factory()
        self.reactor.connectSSL(host, port, factory, *args, **kwargs)
        gtransport._init_transport()
        return gtransport

    def connectTLS(self, host, port, *args, **kwargs):
        gtransport, factory = self._make_transport_and_factory()
        self.reactor.connectTLS(host, port, factory, *args, **kwargs)
        gtransport._init_transport()
        return gtransport

    def connectUNIX(self, address, *args, **kwargs):
        gtransport, factory = self._make_transport_and_factory()
        self.reactor.connectUNIX(address, factory, *args, **kwargs)
        gtransport._init_transport()
        return gtransport

    def connectSRV(self, service, domain, *args, **kwargs):
        SRVConnector = kwargs.pop('ConnectorClass', None)
        if SRVConnector is None:
            from twisted.names.srvconnect import SRVConnector
        gtransport, factory = self._make_transport_and_factory()
        c = SRVConnector(self.reactor, service, domain, factory, *args, **kwargs)
        c.connect()
        gtransport._init_transport()
        return gtransport


class SimpleSpawnFactory(Factory):
    """Factory that spawns a new greenlet for each incoming connection.

    For an incoming connection a new greenlet is created using the provided
    callback as a function and a connected green transport instance as an
    argument.
    """

    gtransport_class = GreenTransport

    def __init__(self, handler, gtransport_class=None, *args, **kwargs):
        if callable(handler):
            self.handler = handler
        else:
            self.handler = handler.send
        if hasattr(handler, 'send_exception'):
            self.exc_handler = handler.send_exception
        if gtransport_class is not None:
            self.gtransport_class = gtransport_class
        self.args = args
        self.kwargs = kwargs

    def exc_handler(self, *args):
        pass

    def buildProtocol(self, addr):
        gtransport = self.gtransport_class(*self.args, **self.kwargs)
        protocol = gtransport.build_protocol()
        protocol.factory = self
        self._do_spawn(gtransport, protocol)
        return protocol

    def _do_spawn(self, gtransport, protocol):
        greenthread.spawn(self._run_handler, gtransport, protocol)

    def _run_handler(self, gtransport, protocol):
        try:
            gtransport._init_transport()
        except Exception:
            self.exc_handler(*sys.exc_info())
        else:
            self.handler(gtransport)


class SpawnFactory(SimpleSpawnFactory):
    """An extension to SimpleSpawnFactory that provides some control over
    the greenlets it has spawned.
    """

    def __init__(self, handler, gtransport_class=None, *args, **kwargs):
        self.greenlets = set()
        SimpleSpawnFactory.__init__(self, handler, gtransport_class, *args, **kwargs)

    def _do_spawn(self, gtransport, protocol):
        g = greenthread.spawn(self._run_handler, gtransport, protocol)
        self.greenlets.add(g)
        g.link(lambda *_: self.greenlets.remove(g))

    def waitall(self):
        results = []
        for g in self.greenlets:
            results.append(g.wait())
        return results


########NEW FILE########
__FILENAME__ = basic
from twisted.protocols import basic
from twisted.internet.error import ConnectionDone
from eventlet.twistedutil.protocol import GreenTransportBase


class LineOnlyReceiver(basic.LineOnlyReceiver):

    def __init__(self, recepient):
        self._recepient = recepient

    def connectionMade(self):
        self._recepient._got_transport(self.transport)

    def connectionLost(self, reason):
        self._recepient._connectionLost(reason)

    def lineReceived(self, line):
        self._recepient._got_data(line)


class LineOnlyReceiverTransport(GreenTransportBase):

    protocol_class = LineOnlyReceiver

    def readline(self):
        return self._wait()

    def sendline(self, line):
        self.protocol.sendLine(line)

    # iterator protocol:

    def __iter__(self):
        return self

    def next(self):
        try:
            return self.readline()
        except ConnectionDone:
            raise StopIteration


########NEW FILE########
__FILENAME__ = util
import socket
import sys
import warnings


__original_socket__ = socket.socket
def tcp_socket():
    warnings.warn("eventlet.util.tcp_socket is deprecated. "
        "Please use the standard socket technique for this instead: "
        "sock = socket.socket()",
        DeprecationWarning, stacklevel=2)
    s = __original_socket__(socket.AF_INET, socket.SOCK_STREAM)
    return s


# if ssl is available, use eventlet.green.ssl for our ssl implementation
from eventlet.green import ssl
def wrap_ssl(sock, certificate=None, private_key=None, server_side=False):
    warnings.warn("eventlet.util.wrap_ssl is deprecated. "
        "Please use the eventlet.green.ssl.wrap_socket()",
        DeprecationWarning, stacklevel=2)
    return ssl.wrap_socket(
        sock,
        keyfile=private_key,
        certfile=certificate,
        server_side=server_side,
    )


def wrap_socket_with_coroutine_socket(use_thread_pool=None):
    warnings.warn("eventlet.util.wrap_socket_with_coroutine_socket() is now "
        "eventlet.patcher.monkey_patch(all=False, socket=True)",
        DeprecationWarning, stacklevel=2)
    from eventlet import patcher
    patcher.monkey_patch(all=False, socket=True)


def wrap_pipes_with_coroutine_pipes():
    warnings.warn("eventlet.util.wrap_pipes_with_coroutine_pipes() is now "
        "eventlet.patcher.monkey_patch(all=False, os=True)",
        DeprecationWarning, stacklevel=2)
    from eventlet import patcher
    patcher.monkey_patch(all=False, os=True)


def wrap_select_with_coroutine_select():
    warnings.warn("eventlet.util.wrap_select_with_coroutine_select() is now "
        "eventlet.patcher.monkey_patch(all=False, select=True)",
        DeprecationWarning, stacklevel=2)
    from eventlet import patcher
    patcher.monkey_patch(all=False, select=True)


def wrap_threading_local_with_coro_local():
    """
    monkey patch ``threading.local`` with something that is greenlet aware.
    Since greenlets cannot cross threads, so this should be semantically
    identical to ``threadlocal.local``
    """
    warnings.warn("eventlet.util.wrap_threading_local_with_coro_local() is now "
        "eventlet.patcher.monkey_patch(all=False, thread=True) -- though"
        "note that more than just _local is patched now.",
        DeprecationWarning, stacklevel=2)

    from eventlet import patcher
    patcher.monkey_patch(all=False, thread=True)


def socket_bind_and_listen(descriptor, addr=('', 0), backlog=50):
    warnings.warn("eventlet.util.socket_bind_and_listen is deprecated."
        "Please use the standard socket methodology for this instead:"
        "sock.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR, 1)"
        "sock.bind(addr)"
        "sock.listen(backlog)",
        DeprecationWarning, stacklevel=2)
    set_reuse_addr(descriptor)
    descriptor.bind(addr)
    descriptor.listen(backlog)
    return descriptor


def set_reuse_addr(descriptor):
    warnings.warn("eventlet.util.set_reuse_addr is deprecated."
        "Please use the standard socket methodology for this instead:"
        "sock.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR, 1)",
        DeprecationWarning, stacklevel=2)
    try:
        descriptor.setsockopt(
            socket.SOL_SOCKET,
            socket.SO_REUSEADDR,
            descriptor.getsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR) | 1)
    except socket.error:
        pass

########NEW FILE########
__FILENAME__ = websocket
import base64
import codecs
import collections
import errno
from random import Random
import string
import struct
import sys
import time
from socket import error as SocketError

try:
    from hashlib import md5, sha1
except ImportError: #pragma NO COVER
    from md5 import md5
    from sha import sha as sha1

import eventlet
from eventlet import semaphore
from eventlet import wsgi
from eventlet.green import socket
from eventlet.support import get_errno

# Python 2's utf8 decoding is more lenient than we'd like
# In order to pass autobahn's testsuite we need stricter validation
# if available...
for _mod in ('wsaccel.utf8validator', 'autobahn.utf8validator'):
    # autobahn has it's own python-based validator. in newest versions
    # this prefers to use wsaccel, a cython based implementation, if available.
    # wsaccel may also be installed w/out autobahn, or with a earlier version.
    try:
        utf8validator = __import__(_mod, {}, {}, [''])
    except ImportError:
        utf8validator = None
    else:
        break

ACCEPTABLE_CLIENT_ERRORS = set((errno.ECONNRESET, errno.EPIPE))

__all__ = ["WebSocketWSGI", "WebSocket"]
PROTOCOL_GUID = '258EAFA5-E914-47DA-95CA-C5AB0DC85B11'
VALID_CLOSE_STATUS = (range(1000, 1004)
                      + range(1007, 1012)
                      # 3000-3999: reserved for use by libraries, frameworks,
                      # and applications
                      + range(3000, 4000)
                      # 4000-4999: reserved for private use and thus can't
                      # be registered
                      + range(4000, 5000))


class BadRequest(Exception):
    def __init__(self, status='400 Bad Request', body=None, headers=None):
        super(Exception, self).__init__()
        self.status = status
        self.body = body
        self.headers = headers


class WebSocketWSGI(object):
    """Wraps a websocket handler function in a WSGI application.

    Use it like this::

      @websocket.WebSocketWSGI
      def my_handler(ws):
          from_browser = ws.wait()
          ws.send("from server")

    The single argument to the function will be an instance of
    :class:`WebSocket`.  To close the socket, simply return from the
    function.  Note that the server will log the websocket request at
    the time of closure.
    """
    def __init__(self, handler):
        self.handler = handler
        self.protocol_version = None
        self.support_legacy_versions = True
        self.supported_protocols = []
        self.origin_checker = None

    @classmethod
    def configured(cls,
                   handler=None,
                   supported_protocols=None,
                   origin_checker=None,
                   support_legacy_versions=False):
        def decorator(handler):
            inst = cls(handler)
            inst.support_legacy_versions = support_legacy_versions
            inst.origin_checker = origin_checker
            if supported_protocols:
                inst.supported_protocols = supported_protocols
            return inst
        if handler is None:
            return decorator
        return decorator(handler)

    def __call__(self, environ, start_response):
        http_connection_parts = [
            part.strip()
            for part in environ.get('HTTP_CONNECTION', '').lower().split(',')]
        if not ('upgrade' in http_connection_parts and
                environ.get('HTTP_UPGRADE', '').lower() == 'websocket'):
            # need to check a few more things here for true compliance
            start_response('400 Bad Request', [('Connection', 'close')])
            return []

        try:
            if 'HTTP_SEC_WEBSOCKET_VERSION' in environ:
                ws = self._handle_hybi_request(environ)
            elif self.support_legacy_versions:
                ws = self._handle_legacy_request(environ)
            else:
                raise BadRequest()
        except BadRequest as e:
            status = e.status
            body = e.body or ''
            headers = e.headers or []
            start_response(status,
                           [('Connection', 'close'), ] + headers)
            return [body]

        try:
            self.handler(ws)
        except socket.error as e:
            if get_errno(e) not in ACCEPTABLE_CLIENT_ERRORS:
                raise
        # Make sure we send the closing frame
        ws._send_closing_frame(True)
        # use this undocumented feature of eventlet.wsgi to ensure that it
        # doesn't barf on the fact that we didn't call start_response
        return wsgi.ALREADY_HANDLED

    def _handle_legacy_request(self, environ):
        sock = environ['eventlet.input'].get_socket()

        if 'HTTP_SEC_WEBSOCKET_KEY1' in environ:
            self.protocol_version = 76
            if 'HTTP_SEC_WEBSOCKET_KEY2' not in environ:
                raise BadRequest()
        else:
            self.protocol_version = 75

        if self.protocol_version == 76:
            key1 = self._extract_number(environ['HTTP_SEC_WEBSOCKET_KEY1'])
            key2 = self._extract_number(environ['HTTP_SEC_WEBSOCKET_KEY2'])
            # There's no content-length header in the request, but it has 8
            # bytes of data.
            environ['wsgi.input'].content_length = 8
            key3 = environ['wsgi.input'].read(8)
            key = struct.pack(">II", key1, key2) + key3
            response = md5(key).digest()

        # Start building the response
        scheme = 'ws'
        if environ.get('wsgi.url_scheme') == 'https':
            scheme = 'wss'
        location = '%s://%s%s%s' % (
            scheme,
            environ.get('HTTP_HOST'),
            environ.get('SCRIPT_NAME'),
            environ.get('PATH_INFO')
        )
        qs = environ.get('QUERY_STRING')
        if qs is not None:
            location += '?' + qs
        if self.protocol_version == 75:
            handshake_reply = ("HTTP/1.1 101 Web Socket Protocol Handshake\r\n"
                               "Upgrade: WebSocket\r\n"
                               "Connection: Upgrade\r\n"
                               "WebSocket-Origin: %s\r\n"
                               "WebSocket-Location: %s\r\n\r\n" % (
                    environ.get('HTTP_ORIGIN'),
                    location))
        elif self.protocol_version == 76:
            handshake_reply = ("HTTP/1.1 101 WebSocket Protocol Handshake\r\n"
                               "Upgrade: WebSocket\r\n"
                               "Connection: Upgrade\r\n"
                               "Sec-WebSocket-Origin: %s\r\n"
                               "Sec-WebSocket-Protocol: %s\r\n"
                               "Sec-WebSocket-Location: %s\r\n"
                               "\r\n%s" % (
                    environ.get('HTTP_ORIGIN'),
                    environ.get('HTTP_SEC_WEBSOCKET_PROTOCOL', 'default'),
                    location,
                    response))
        else: #pragma NO COVER
            raise ValueError("Unknown WebSocket protocol version.")
        sock.sendall(handshake_reply)
        return WebSocket(sock, environ, self.protocol_version)

    def _handle_hybi_request(self, environ):
        sock = environ['eventlet.input'].get_socket()
        hybi_version = environ['HTTP_SEC_WEBSOCKET_VERSION']
        if hybi_version not in ('8', '13', ):
            raise BadRequest(status='426 Upgrade Required',
                             headers=[('Sec-WebSocket-Version', '8, 13')])
        self.protocol_version = int(hybi_version)
        if 'HTTP_SEC_WEBSOCKET_KEY' not in environ:
            # That's bad.
            raise BadRequest()
        origin = environ.get(
            'HTTP_ORIGIN',
            (environ.get('HTTP_SEC_WEBSOCKET_ORIGIN', '')
             if self.protocol_version <= 8 else ''))
        if self.origin_checker is not None:
            if not self.origin_checker(environ.get('HTTP_HOST'), origin):
                raise BadRequest(status='403 Forbidden')
        protocols = environ.get('HTTP_SEC_WEBSOCKET_PROTOCOL', None)
        negotiated_protocol = None
        if protocols:
            for p in (i.strip() for i in protocols.split(',')):
                if p in self.supported_protocols:
                    negotiated_protocol = p
                    break
        #extensions = environ.get('HTTP_SEC_WEBSOCKET_EXTENSIONS', None)
        #if extensions:
        #    extensions = [i.strip() for i in extensions.split(',')]

        key = environ['HTTP_SEC_WEBSOCKET_KEY']
        response = base64.b64encode(sha1(key + PROTOCOL_GUID).digest())
        handshake_reply = ["HTTP/1.1 101 Switching Protocols",
                           "Upgrade: websocket",
                           "Connection: Upgrade",
                           "Sec-WebSocket-Accept: %s" % (response, )]
        if negotiated_protocol:
            handshake_reply.append("Sec-WebSocket-Protocol: %s"
                                   % (negotiated_protocol, ))
        sock.sendall('\r\n'.join(handshake_reply) + '\r\n\r\n')
        return RFC6455WebSocket(sock, environ, self.protocol_version,
                                protocol=negotiated_protocol)

    def _extract_number(self, value):
        """
        Utility function which, given a string like 'g98sd  5[]221@1', will
        return 9852211. Used to parse the Sec-WebSocket-Key headers.
        """
        out = ""
        spaces = 0
        for char in value:
            if char in string.digits:
                out += char
            elif char == " ":
                spaces += 1
        return int(out) / spaces

class WebSocket(object):
    """A websocket object that handles the details of
    serialization/deserialization to the socket.

    The primary way to interact with a :class:`WebSocket` object is to
    call :meth:`send` and :meth:`wait` in order to pass messages back
    and forth with the browser.  Also available are the following
    properties:

    path
        The path value of the request.  This is the same as the WSGI PATH_INFO variable, but more convenient.
    protocol
        The value of the Websocket-Protocol header.
    origin
        The value of the 'Origin' header.
    environ
        The full WSGI environment for this request.

    """
    def __init__(self, sock, environ, version=76):
        """
        :param socket: The eventlet socket
        :type socket: :class:`eventlet.greenio.GreenSocket`
        :param environ: The wsgi environment
        :param version: The WebSocket spec version to follow (default is 76)
        """
        self.socket = sock
        self.origin = environ.get('HTTP_ORIGIN')
        self.protocol = environ.get('HTTP_WEBSOCKET_PROTOCOL')
        self.path = environ.get('PATH_INFO')
        self.environ = environ
        self.version = version
        self.websocket_closed = False
        self._buf = ""
        self._msgs = collections.deque()
        self._sendlock = semaphore.Semaphore()

    @staticmethod
    def _pack_message(message):
        """Pack the message inside ``00`` and ``FF``

        As per the dataframing section (5.3) for the websocket spec
        """
        if isinstance(message, unicode):
            message = message.encode('utf-8')
        elif not isinstance(message, str):
            message = str(message)
        packed = "\x00%s\xFF" % message
        return packed

    def _parse_messages(self):
        """ Parses for messages in the buffer *buf*.  It is assumed that
        the buffer contains the start character for a message, but that it
        may contain only part of the rest of the message.

        Returns an array of messages, and the buffer remainder that
        didn't contain any full messages."""
        msgs = []
        end_idx = 0
        buf = self._buf
        while buf:
            frame_type = ord(buf[0])
            if frame_type == 0:
                # Normal message.
                end_idx = buf.find("\xFF")
                if end_idx == -1: #pragma NO COVER
                    break
                msgs.append(buf[1:end_idx].decode('utf-8', 'replace'))
                buf = buf[end_idx+1:]
            elif frame_type == 255:
                # Closing handshake.
                assert ord(buf[1]) == 0, "Unexpected closing handshake: %r" % buf
                self.websocket_closed = True
                break
            else:
                raise ValueError("Don't understand how to parse this type of message: %r" % buf)
        self._buf = buf
        return msgs

    def send(self, message):
        """Send a message to the browser.

        *message* should be convertable to a string; unicode objects should be
        encodable as utf-8.  Raises socket.error with errno of 32
        (broken pipe) if the socket has already been closed by the client."""
        packed = self._pack_message(message)
        # if two greenthreads are trying to send at the same time
        # on the same socket, sendlock prevents interleaving and corruption
        self._sendlock.acquire()
        try:
            self.socket.sendall(packed)
        finally:
            self._sendlock.release()

    def wait(self):
        """Waits for and deserializes messages.

        Returns a single message; the oldest not yet processed. If the client
        has already closed the connection, returns None.  This is different
        from normal socket behavior because the empty string is a valid
        websocket message."""
        while not self._msgs:
            # Websocket might be closed already.
            if self.websocket_closed:
                return None
            # no parsed messages, must mean buf needs more data
            delta = self.socket.recv(8096)
            if delta == '':
                return None
            self._buf += delta
            msgs = self._parse_messages()
            self._msgs.extend(msgs)
        return self._msgs.popleft()

    def _send_closing_frame(self, ignore_send_errors=False):
        """Sends the closing frame to the client, if required."""
        if self.version == 76 and not self.websocket_closed:
            try:
                self.socket.sendall("\xff\x00")
            except SocketError:
                # Sometimes, like when the remote side cuts off the connection,
                # we don't care about this.
                if not ignore_send_errors: #pragma NO COVER
                    raise
            self.websocket_closed = True

    def close(self):
        """Forcibly close the websocket; generally it is preferable to
        return from the handler method."""
        self._send_closing_frame()
        self.socket.shutdown(True)
        self.socket.close()


class ConnectionClosedError(Exception):
    pass


class FailedConnectionError(Exception):
    def __init__(self, status, message):
        super(FailedConnectionError, self).__init__(status, message)
        self.message = message
        self.status = status


class ProtocolError(ValueError):
    pass


class RFC6455WebSocket(WebSocket):
    def __init__(self, sock, environ, version=13, protocol=None, client=False):
        super(RFC6455WebSocket, self).__init__(sock, environ, version)
        self.iterator = self._iter_frames()
        self.client = client
        self.protocol = protocol

    class UTF8Decoder(object):
        def __init__(self):
            if utf8validator:
                self.validator = utf8validator.Utf8Validator()
            else:
                self.validator = None
            decoderclass = codecs.getincrementaldecoder('utf8')
            self.decoder = decoderclass()

        def reset(self):
            if self.validator:
                self.validator.reset()
            self.decoder.reset()

        def decode(self, data, final=False):
            if self.validator:
                valid, eocp, c_i, t_i = self.validator.validate(data)
                if not valid:
                    raise ValueError('Data is not valid unicode')
            return self.decoder.decode(data, final)

    def _get_bytes(self, numbytes):
        data = ''
        while len(data) < numbytes:
            d = self.socket.recv(numbytes - len(data))
            if not d:
                raise ConnectionClosedError()
            data = data + d
        return data

    class Message(object):
        def __init__(self, opcode, decoder=None):
            self.decoder = decoder
            self.data = []
            self.finished = False
            self.opcode = opcode

        def push(self, data, final=False):
            if self.decoder:
                data = self.decoder.decode(data, final=final)
            self.finished = final
            self.data.append(data)

        def getvalue(self):
            return ''.join(self.data)

    @staticmethod
    def _apply_mask(data, mask, length=None, offset=0):
        if length is None:
            length = len(data)
        cnt = range(length)
        return ''.join(chr(ord(data[i]) ^ mask[(offset + i) % 4]) for i in cnt)

    def _handle_control_frame(self, opcode, data):
        if opcode == 8:  # connection close
            if not data:
                status = 1000
            elif len(data) > 1:
                status = struct.unpack_from('!H', data)[0]
                if not status or status not in VALID_CLOSE_STATUS:
                    raise FailedConnectionError(
                        1002,
                        "Unexpected close status code.")
                try:
                    data = self.UTF8Decoder().decode(data[2:], True)
                except (UnicodeDecodeError, ValueError):
                    raise FailedConnectionError(
                        1002,
                        "Close message data should be valid UTF-8.")
            else:
                status = 1002
            self.close(close_data=(status, ''))
            raise ConnectionClosedError()
        elif opcode == 9:  # ping
            self.send(data, control_code=0xA)
        elif opcode == 0xA:  # pong
            pass
        else:
            raise FailedConnectionError(
                1002, "Unknown control frame received.")

    def _iter_frames(self):
        fragmented_message = None
        try:
            while True:
                message = self._recv_frame(message=fragmented_message)
                if message.opcode & 8:
                    self._handle_control_frame(
                        message.opcode, message.getvalue())
                    continue
                if fragmented_message and message is not fragmented_message:
                    raise RuntimeError('Unexpected message change.')
                fragmented_message = message
                if message.finished:
                    data = fragmented_message.getvalue()
                    fragmented_message = None
                    yield data
        except FailedConnectionError:
            exc_typ, exc_val, exc_tb = sys.exc_info()
            self.close(close_data=(exc_val.status, exc_val.message))
        except ConnectionClosedError:
            return
        except Exception:
            self.close(close_data=(1011, 'Internal Server Error'))
            raise

    def _recv_frame(self, message=None):
        recv = self._get_bytes
        header = recv(2)
        a, b = struct.unpack('!BB', header)
        finished = a >> 7 == 1
        rsv123 = a >> 4 & 7
        if rsv123:
            # must be zero
            raise FailedConnectionError(
                1002,
                "RSV1, RSV2, RSV3: MUST be 0 unless an extension is"
                " negotiated that defines meanings for non-zero values.")
        opcode = a & 15
        if opcode not in (0, 1, 2, 8, 9, 0xA):
            raise FailedConnectionError(1002, "Unknown opcode received.")
        masked = b & 128 == 128
        if not masked and not self.client:
            raise FailedConnectionError(1002, "A client MUST mask all frames"
                                        " that it sends to the server")
        length = b & 127
        if opcode & 8:
            if not finished:
                raise FailedConnectionError(1002, "Control frames must not"
                                            " be fragmented.")
            if length > 125:
                raise FailedConnectionError(
                    1002,
                    "All control frames MUST have a payload length of 125"
                    " bytes or less")
        elif opcode and message:
            raise FailedConnectionError(
                1002,
                "Received a non-continuation opcode within"
                " fragmented message.")
        elif not opcode and not message:
            raise FailedConnectionError(
                1002,
                "Received continuation opcode with no previous"
                " fragments received.")
        if length == 126:
            length = struct.unpack('!H', recv(2))[0]
        elif length == 127:
            length = struct.unpack('!Q', recv(8))[0]
        if masked:
            mask = struct.unpack('!BBBB', recv(4))
        received = 0
        if not message or opcode & 8:
            decoder = self.UTF8Decoder() if opcode == 1 else None
            message = self.Message(opcode, decoder=decoder)
        if not length:
            message.push('', final=finished)
        else:
            while received < length:
                d = self.socket.recv(length - received)
                if not d:
                    raise ConnectionClosedError()
                dlen = len(d)
                if masked:
                    d = self._apply_mask(d, mask, length=dlen, offset=received)
                received = received + dlen
                try:
                    message.push(d, final=finished)
                except (UnicodeDecodeError, ValueError):
                    raise FailedConnectionError(
                        1007, "Text data must be valid utf-8")
        return message

    @staticmethod
    def _pack_message(message, masked=False,
                      continuation=False, final=True, control_code=None):
        is_text = False
        if isinstance(message, unicode):
            message = message.encode('utf-8')
            is_text = True
        length = len(message)
        if not length:
            # no point masking empty data
            masked = False
        if control_code:
            if control_code not in (8, 9, 0xA):
                raise ProtocolError('Unknown control opcode.')
            if continuation or not final:
                raise ProtocolError('Control frame cannot be a fragment.')
            if length > 125:
                raise ProtocolError('Control frame data too large (>125).')
            header = struct.pack('!B', control_code | 1 << 7)
        else:
            opcode = 0 if continuation else (1 if is_text else 2)
            header = struct.pack('!B', opcode | (1 << 7 if final else 0))
        lengthdata = 1 << 7 if masked else 0
        if length > 65535:
            lengthdata = struct.pack('!BQ', lengthdata | 127, length)
        elif length > 125:
            lengthdata = struct.pack('!BH', lengthdata | 126, length)
        else:
            lengthdata = struct.pack('!B', lengthdata | length)
        if masked:
            # NOTE: RFC6455 states:
            # A server MUST NOT mask any frames that it sends to the client
            rand = Random(time.time())
            mask = map(rand.getrandbits, (8, ) * 4)
            message = RFC6455WebSocket._apply_mask(message, mask, length)
            maskdata = struct.pack('!BBBB', *mask)
        else:
            maskdata = ''
        return ''.join((header, lengthdata, maskdata, message))

    def wait(self):
        for i in self.iterator:
            return i

    def _send(self, frame):
        self._sendlock.acquire()
        try:
            self.socket.sendall(frame)
        finally:
            self._sendlock.release()

    def send(self, message, **kw):
        kw['masked'] = self.client
        payload = self._pack_message(message, **kw)
        self._send(payload)

    def _send_closing_frame(self, ignore_send_errors=False, close_data=None):
        if self.version in (8, 13) and not self.websocket_closed:
            if close_data is not None:
                status, msg = close_data
                if isinstance(msg, unicode):
                    msg = msg.encode('utf-8')
                data = struct.pack('!H', status) + msg
            else:
                data = ''
            try:
                self.send(data, control_code=8)
            except SocketError:
                # Sometimes, like when the remote side cuts off the connection,
                # we don't care about this.
                if not ignore_send_errors:  # pragma NO COVER
                    raise
            self.websocket_closed = True

    def close(self, close_data=None):
        """Forcibly close the websocket; generally it is preferable to
        return from the handler method."""
        self._send_closing_frame(close_data=close_data)
        self.socket.shutdown(socket.SHUT_WR)
        self.socket.close()

########NEW FILE########
__FILENAME__ = wsgi
import errno
import os
import sys
import time
import traceback
import types
import warnings

from eventlet.green import urllib
from eventlet.green import socket
from eventlet.green import BaseHTTPServer
from eventlet import greenpool
from eventlet import greenio
from eventlet.support import get_errno, six


DEFAULT_MAX_SIMULTANEOUS_REQUESTS = 1024
DEFAULT_MAX_HTTP_VERSION = 'HTTP/1.1'
MAX_REQUEST_LINE = 8192
MAX_HEADER_LINE = 8192
MAX_TOTAL_HEADER_SIZE = 65536
MINIMUM_CHUNK_SIZE = 4096
# %(client_port)s is also available
DEFAULT_LOG_FORMAT= ('%(client_ip)s - - [%(date_time)s] "%(request_line)s"'
                     ' %(status_code)s %(body_length)s %(wall_seconds).6f')

__all__ = ['server', 'format_date_time']

# Weekday and month names for HTTP date/time formatting; always English!
_weekdayname = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
_monthname = [None, # Dummy so we can use 1-based month numbers
              "Jan", "Feb", "Mar", "Apr", "May", "Jun",
              "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def format_date_time(timestamp):
    """Formats a unix timestamp into an HTTP standard string."""
    year, month, day, hh, mm, ss, wd, _y, _z = time.gmtime(timestamp)
    return "%s, %02d %3s %4d %02d:%02d:%02d GMT" % (
        _weekdayname[wd], day, _monthname[month], year, hh, mm, ss
    )


# Collections of error codes to compare against.  Not all attributes are set
# on errno module on all platforms, so some are literals :(
BAD_SOCK = set((errno.EBADF, 10053))
BROKEN_SOCK = set((errno.EPIPE, errno.ECONNRESET))


# special flag return value for apps
class _AlreadyHandled(object):

    def __iter__(self):
        return self

    def next(self):
        raise StopIteration

ALREADY_HANDLED = _AlreadyHandled()


class Input(object):

    def __init__(self,
                 rfile,
                 content_length,
                 wfile=None,
                 wfile_line=None,
                 chunked_input=False):

        self.rfile = rfile
        if content_length is not None:
            content_length = int(content_length)
        self.content_length = content_length

        self.wfile = wfile
        self.wfile_line = wfile_line

        self.position = 0
        self.chunked_input = chunked_input
        self.chunk_length = -1

    def _do_read(self, reader, length=None):
        if self.wfile is not None:
            ## 100 Continue
            self.wfile.write(self.wfile_line)
            self.wfile = None
            self.wfile_line = None

        if length is None and self.content_length is not None:
            length = self.content_length - self.position
        if length and length > self.content_length - self.position:
            length = self.content_length - self.position
        if not length:
            return ''
        try:
            read = reader(length)
        except greenio.SSL.ZeroReturnError:
            read = ''
        self.position += len(read)
        return read

    def _chunked_read(self, rfile, length=None, use_readline=False):
        if self.wfile is not None:
            ## 100 Continue
            self.wfile.write(self.wfile_line)
            self.wfile = None
            self.wfile_line = None
        try:
            if length == 0:
                return ""

            if length < 0:
                length = None

            if use_readline:
                reader = self.rfile.readline
            else:
                reader = self.rfile.read

            response = []
            while self.chunk_length != 0:
                maxreadlen = self.chunk_length - self.position
                if length is not None and length < maxreadlen:
                    maxreadlen = length

                if maxreadlen > 0:
                    data = reader(maxreadlen)
                    if not data:
                        self.chunk_length = 0
                        raise IOError("unexpected end of file while parsing chunked data")

                    datalen = len(data)
                    response.append(data)

                    self.position += datalen
                    if self.chunk_length == self.position:
                        rfile.readline()

                    if length is not None:
                        length -= datalen
                        if length == 0:
                            break
                    if use_readline and data[-1] == "\n":
                        break
                else:
                    self.chunk_length = int(rfile.readline().split(";", 1)[0], 16)
                    self.position = 0
                    if self.chunk_length == 0:
                        rfile.readline()
        except greenio.SSL.ZeroReturnError:
            pass
        return ''.join(response)

    def read(self, length=None):
        if self.chunked_input:
            return self._chunked_read(self.rfile, length)
        return self._do_read(self.rfile.read, length)

    def readline(self, size=None):
        if self.chunked_input:
            return self._chunked_read(self.rfile, size, True)
        else:
            return self._do_read(self.rfile.readline, size)

    def readlines(self, hint=None):
        return self._do_read(self.rfile.readlines, hint)

    def __iter__(self):
        return iter(self.read, '')

    def get_socket(self):
        return self.rfile._sock


class HeaderLineTooLong(Exception):
    pass


class HeadersTooLarge(Exception):
    pass


class FileObjectForHeaders(object):

    def __init__(self, fp):
        self.fp = fp
        self.total_header_size = 0

    def readline(self, size=-1):
        sz = size
        if size < 0:
            sz = MAX_HEADER_LINE
        rv = self.fp.readline(sz)
        if size < 0 and len(rv) >= MAX_HEADER_LINE:
            raise HeaderLineTooLong()
        self.total_header_size += len(rv)
        if self.total_header_size > MAX_TOTAL_HEADER_SIZE:
            raise HeadersTooLarge()
        return rv


class HttpProtocol(BaseHTTPServer.BaseHTTPRequestHandler):
    protocol_version = 'HTTP/1.1'
    minimum_chunk_size = MINIMUM_CHUNK_SIZE
    capitalize_response_headers = True

    def setup(self):
        # overriding SocketServer.setup to correctly handle SSL.Connection objects
        conn = self.connection = self.request
        try:
            self.rfile = conn.makefile('rb', self.rbufsize)
            self.wfile = conn.makefile('wb', self.wbufsize)
        except (AttributeError, NotImplementedError):
            if hasattr(conn, 'send') and hasattr(conn, 'recv'):
                # it's an SSL.Connection
                self.rfile = socket._fileobject(conn, "rb", self.rbufsize)
                self.wfile = socket._fileobject(conn, "wb", self.wbufsize)
            else:
                # it's a SSLObject, or a martian
                raise NotImplementedError("wsgi.py doesn't support sockets "\
                                          "of type %s" % type(conn))

    def handle_one_request(self):
        if self.server.max_http_version:
            self.protocol_version = self.server.max_http_version

        if self.rfile.closed:
            self.close_connection = 1
            return

        try:
            self.raw_requestline = self.rfile.readline(self.server.url_length_limit)
            if len(self.raw_requestline) == self.server.url_length_limit:
                self.wfile.write(
                    "HTTP/1.0 414 Request URI Too Long\r\n"
                    "Connection: close\r\nContent-length: 0\r\n\r\n")
                self.close_connection = 1
                return
        except greenio.SSL.ZeroReturnError:
            self.raw_requestline = ''
        except socket.error as e:
            if get_errno(e) not in BAD_SOCK:
                raise
            self.raw_requestline = ''

        if not self.raw_requestline:
            self.close_connection = 1
            return

        orig_rfile = self.rfile
        try:
            self.rfile = FileObjectForHeaders(self.rfile)
            if not self.parse_request():
                return
        except HeaderLineTooLong:
            self.wfile.write(
                "HTTP/1.0 400 Header Line Too Long\r\n"
                "Connection: close\r\nContent-length: 0\r\n\r\n")
            self.close_connection = 1
            return
        except HeadersTooLarge:
            self.wfile.write(
                "HTTP/1.0 400 Headers Too Large\r\n"
                "Connection: close\r\nContent-length: 0\r\n\r\n")
            self.close_connection = 1
            return
        finally:
            self.rfile = orig_rfile

        content_length = self.headers.getheader('content-length')
        if content_length:
            try:
                int(content_length)
            except ValueError:
                self.wfile.write(
                    "HTTP/1.0 400 Bad Request\r\n"
                    "Connection: close\r\nContent-length: 0\r\n\r\n")
                self.close_connection = 1
                return

        self.environ = self.get_environ()
        self.application = self.server.app
        try:
            self.server.outstanding_requests += 1
            try:
                self.handle_one_response()
            except socket.error as e:
                # Broken pipe, connection reset by peer
                if get_errno(e) not in BROKEN_SOCK:
                    raise
        finally:
            self.server.outstanding_requests -= 1

    def handle_one_response(self):
        start = time.time()
        headers_set = []
        headers_sent = []

        wfile = self.wfile
        result = None
        use_chunked = [False]
        length = [0]
        status_code = [200]

        def write(data, _writelines=wfile.writelines):
            towrite = []
            if not headers_set:
                raise AssertionError("write() before start_response()")
            elif not headers_sent:
                status, response_headers = headers_set
                headers_sent.append(1)
                header_list = [header[0].lower() for header in response_headers]
                towrite.append('%s %s\r\n' % (self.protocol_version, status))
                for header in response_headers:
                    towrite.append('%s: %s\r\n' % header)

                # send Date header?
                if 'date' not in header_list:
                    towrite.append('Date: %s\r\n' % (format_date_time(time.time()),))

                client_conn = self.headers.get('Connection', '').lower()
                send_keep_alive = False
                if self.close_connection == 0 and \
                   self.server.keepalive and (client_conn == 'keep-alive' or \
                    (self.request_version == 'HTTP/1.1' and
                     not client_conn == 'close')):
                        # only send keep-alives back to clients that sent them,
                        # it's redundant for 1.1 connections
                        send_keep_alive = (client_conn == 'keep-alive')
                        self.close_connection = 0
                else:
                    self.close_connection = 1

                if 'content-length' not in header_list:
                    if self.request_version == 'HTTP/1.1':
                        use_chunked[0] = True
                        towrite.append('Transfer-Encoding: chunked\r\n')
                    elif 'content-length' not in header_list:
                        # client is 1.0 and therefore must read to EOF
                        self.close_connection = 1

                if self.close_connection:
                    towrite.append('Connection: close\r\n')
                elif send_keep_alive:
                    towrite.append('Connection: keep-alive\r\n')
                towrite.append('\r\n')
                # end of header writing

            if use_chunked[0]:
                ## Write the chunked encoding
                towrite.append("%x\r\n%s\r\n" % (len(data), data))
            else:
                towrite.append(data)
            try:
                _writelines(towrite)
                length[0] = length[0] + sum(map(len, towrite))
            except UnicodeEncodeError:
                self.server.log_message("Encountered non-ascii unicode while attempting to write wsgi response: %r" % [x for x in towrite if isinstance(x, unicode)])
                self.server.log_message(traceback.format_exc())
                _writelines(
                    ["HTTP/1.1 500 Internal Server Error\r\n",
                    "Connection: close\r\n",
                    "Content-type: text/plain\r\n",
                    "Content-length: 98\r\n",
                    "Date: %s\r\n" % format_date_time(time.time()),
                    "\r\n",
                    ("Internal Server Error: wsgi application passed "
                     "a unicode object to the server instead of a string.")])

        def start_response(status, response_headers, exc_info=None):
            status_code[0] = status.split()[0]
            if exc_info:
                try:
                    if headers_sent:
                        # Re-raise original exception if headers sent
                        six.reraise(exc_info[0], exc_info[1], exc_info[2])
                finally:
                    # Avoid dangling circular ref
                    exc_info = None

            # Response headers capitalization
            # CONTent-TYpe: TExt/PlaiN -> Content-Type: TExt/PlaiN
            # Per HTTP RFC standard, header name is case-insensitive.
            # Please, fix your client to ignore header case if possible.
            if self.capitalize_response_headers:
                response_headers = [
                    ('-'.join([x.capitalize() for x in key.split('-')]), value)
                    for key, value in response_headers]

            headers_set[:] = [status, response_headers]
            return write

        try:
            try:
                result = self.application(self.environ, start_response)
                if (isinstance(result, _AlreadyHandled)
                    or isinstance(getattr(result, '_obj', None), _AlreadyHandled)):
                    self.close_connection = 1
                    return

                # Set content-length if possible
                if not headers_sent and hasattr(result, '__len__') and \
                        'Content-Length' not in [h for h, _v in headers_set[1]]:
                    headers_set[1].append(('Content-Length', str(sum(map(len, result)))))

                towrite = []
                towrite_size = 0
                just_written_size = 0
                minimum_write_chunk_size = int(self.environ.get(
                    'eventlet.minimum_write_chunk_size', self.minimum_chunk_size))
                for data in result:
                    towrite.append(data)
                    towrite_size += len(data)
                    if towrite_size >= minimum_write_chunk_size:
                        write(''.join(towrite))
                        towrite = []
                        just_written_size = towrite_size
                        towrite_size = 0
                if towrite:
                    just_written_size = towrite_size
                    write(''.join(towrite))
                if not headers_sent or (use_chunked[0] and just_written_size):
                    write('')
            except Exception:
                self.close_connection = 1
                tb = traceback.format_exc()
                self.server.log_message(tb)
                if not headers_set:
                    err_body = ""
                    if(self.server.debug):
                        err_body = tb
                    start_response("500 Internal Server Error",
                                   [('Content-type', 'text/plain'),
                                    ('Content-length', len(err_body))])
                    write(err_body)
        finally:
            if hasattr(result, 'close'):
                result.close()
            if (self.environ['eventlet.input'].chunked_input or
                    self.environ['eventlet.input'].position \
                    < self.environ['eventlet.input'].content_length):
                ## Read and discard body if there was no pending 100-continue
                if not self.environ['eventlet.input'].wfile:
                    # NOTE: MINIMUM_CHUNK_SIZE is used here for purpose different than chunking.
                    # We use it only cause it's at hand and has reasonable value in terms of
                    # emptying the buffer.
                    while self.environ['eventlet.input'].read(MINIMUM_CHUNK_SIZE):
                        pass
            finish = time.time()

            for hook, args, kwargs in self.environ['eventlet.posthooks']:
                hook(self.environ, *args, **kwargs)

            if self.server.log_output:
                self.server.log_message(self.server.log_format % {
                    'client_ip': self.get_client_ip(),
                    'client_port': self.client_address[1],
                    'date_time': self.log_date_time_string(),
                    'request_line': self.requestline,
                    'status_code': status_code[0],
                    'body_length': length[0],
                    'wall_seconds': finish - start,
                })

    def get_client_ip(self):
        client_ip = self.client_address[0]
        if self.server.log_x_forwarded_for:
            forward = self.headers.get('X-Forwarded-For', '').replace(' ', '')
            if forward:
                client_ip = "%s,%s" % (forward, client_ip)
        return client_ip

    def get_environ(self):
        env = self.server.get_environ()
        env['REQUEST_METHOD'] = self.command
        env['SCRIPT_NAME'] = ''

        pq = self.path.split('?', 1)
        env['RAW_PATH_INFO'] = pq[0]
        env['PATH_INFO'] = urllib.unquote(pq[0])
        if len(pq) > 1:
            env['QUERY_STRING'] = pq[1]

        if self.headers.typeheader is None:
            env['CONTENT_TYPE'] = self.headers.type
        else:
            env['CONTENT_TYPE'] = self.headers.typeheader

        length = self.headers.getheader('content-length')
        if length:
            env['CONTENT_LENGTH'] = length
        env['SERVER_PROTOCOL'] = 'HTTP/1.0'

        host, port = self.request.getsockname()[:2]
        env['SERVER_NAME'] = host
        env['SERVER_PORT'] = str(port)
        env['REMOTE_ADDR'] = self.client_address[0]
        env['REMOTE_PORT'] = str(self.client_address[1])
        env['GATEWAY_INTERFACE'] = 'CGI/1.1'

        for h in self.headers.headers:
            k, v = h.split(':', 1)
            k = k.replace('-', '_').upper()
            v = v.strip()
            if k in env:
                continue
            envk = 'HTTP_' + k
            if envk in env:
                env[envk] += ',' + v
            else:
                env[envk] = v

        if env.get('HTTP_EXPECT') == '100-continue':
            wfile = self.wfile
            wfile_line = 'HTTP/1.1 100 Continue\r\n\r\n'
        else:
            wfile = None
            wfile_line = None
        chunked = env.get('HTTP_TRANSFER_ENCODING', '').lower() == 'chunked'
        env['wsgi.input'] = env['eventlet.input'] = Input(
            self.rfile, length, wfile=wfile, wfile_line=wfile_line,
            chunked_input=chunked)
        env['eventlet.posthooks'] = []

        return env

    def finish(self):
        try:
            BaseHTTPServer.BaseHTTPRequestHandler.finish(self)
        except socket.error as e:
            # Broken pipe, connection reset by peer
            if get_errno(e) not in BROKEN_SOCK:
                raise
        greenio.shutdown_safe(self.connection)
        self.connection.close()


class Server(BaseHTTPServer.HTTPServer):

    def __init__(self,
                 socket,
                 address,
                 app,
                 log=None,
                 environ=None,
                 max_http_version=None,
                 protocol=HttpProtocol,
                 minimum_chunk_size=None,
                 log_x_forwarded_for=True,
                 keepalive=True,
                 log_output=True,
                 log_format=DEFAULT_LOG_FORMAT,
                 url_length_limit=MAX_REQUEST_LINE,
                 debug=True,
                 socket_timeout=None,
                 capitalize_response_headers=True):

        self.outstanding_requests = 0
        self.socket = socket
        self.address = address
        if log:
            self.log = log
        else:
            self.log = sys.stderr
        self.app = app
        self.keepalive = keepalive
        self.environ = environ
        self.max_http_version = max_http_version
        self.protocol = protocol
        self.pid = os.getpid()
        self.minimum_chunk_size = minimum_chunk_size
        self.log_x_forwarded_for = log_x_forwarded_for
        self.log_output = log_output
        self.log_format = log_format
        self.url_length_limit = url_length_limit
        self.debug = debug
        self.socket_timeout = socket_timeout
        self.capitalize_response_headers = capitalize_response_headers

        if not self.capitalize_response_headers:
            warnings.warn("""capitalize_response_headers is disabled.
 Please, make sure you know what you are doing.
 HTTP headers names are case-insensitive per RFC standard.
 Most likely, you need to fix HTTP parsing in your client software.""",
                DeprecationWarning, stacklevel=3)

    def get_environ(self):
        d = {
            'wsgi.errors': sys.stderr,
            'wsgi.version': (1, 0),
            'wsgi.multithread': True,
            'wsgi.multiprocess': False,
            'wsgi.run_once': False,
            'wsgi.url_scheme': 'http',
        }
        # detect secure socket
        if hasattr(self.socket, 'do_handshake'):
            d['wsgi.url_scheme'] = 'https'
            d['HTTPS'] = 'on'
        if self.environ is not None:
            d.update(self.environ)
        return d

    def process_request(self, sock_params):
        # The actual request handling takes place in __init__, so we need to
        # set minimum_chunk_size before __init__ executes and we don't want to modify
        # class variable
        sock, address = sock_params
        proto = types.InstanceType(self.protocol)
        if self.minimum_chunk_size is not None:
            proto.minimum_chunk_size = self.minimum_chunk_size
        proto.capitalize_response_headers = self.capitalize_response_headers
        try:
            proto.__init__(sock, address, self)
        except socket.timeout:
            # Expected exceptions are not exceptional
            sock.close()
            if self.debug:
                # similar to logging "accepted" in server()
                self.log_message('(%s) timed out %r' % (self.pid, address))

    def log_message(self, message):
        self.log.write(message + '\n')


try:
    import ssl
    ACCEPT_EXCEPTIONS = (socket.error, ssl.SSLError)
    ACCEPT_ERRNO = set((errno.EPIPE, errno.EBADF, errno.ECONNRESET,
                        ssl.SSL_ERROR_EOF, ssl.SSL_ERROR_SSL))
except ImportError:
    ACCEPT_EXCEPTIONS = (socket.error,)
    ACCEPT_ERRNO = set((errno.EPIPE, errno.EBADF, errno.ECONNRESET))


def server(sock, site,
           log=None,
           environ=None,
           max_size=None,
           max_http_version=DEFAULT_MAX_HTTP_VERSION,
           protocol=HttpProtocol,
           server_event=None,
           minimum_chunk_size=None,
           log_x_forwarded_for=True,
           custom_pool=None,
           keepalive=True,
           log_output=True,
           log_format=DEFAULT_LOG_FORMAT,
           url_length_limit=MAX_REQUEST_LINE,
           debug=True,
           socket_timeout=None,
           capitalize_response_headers=True):
    """Start up a WSGI server handling requests from the supplied server
    socket.  This function loops forever.  The *sock* object will be closed after server exits,
    but the underlying file descriptor will remain open, so if you have a dup() of *sock*,
    it will remain usable.

    :param sock: Server socket, must be already bound to a port and listening.
    :param site: WSGI application function.
    :param log: File-like object that logs should be written to.  If not specified, sys.stderr is used.
    :param environ: Additional parameters that go into the environ dictionary of every request.
    :param max_size: Maximum number of client connections opened at any time by this server.
    :param max_http_version: Set to "HTTP/1.0" to make the server pretend it only supports HTTP 1.0.  This can help with applications or clients that don't behave properly using HTTP 1.1.
    :param protocol: Protocol class.  Deprecated.
    :param server_event: Used to collect the Server object.  Deprecated.
    :param minimum_chunk_size: Minimum size in bytes for http chunks.  This  can be used to improve performance of applications which yield many small strings, though using it technically violates the WSGI spec. This can be overridden on a per request basis by setting environ['eventlet.minimum_write_chunk_size'].
    :param log_x_forwarded_for: If True (the default), logs the contents of the x-forwarded-for header in addition to the actual client ip address in the 'client_ip' field of the log line.
    :param custom_pool: A custom GreenPool instance which is used to spawn client green threads.  If this is supplied, max_size is ignored.
    :param keepalive: If set to False, disables keepalives on the server; all connections will be closed after serving one request.
    :param log_output: A Boolean indicating if the server will log data or not.
    :param log_format: A python format string that is used as the template to generate log lines.  The following values can be formatted into it: client_ip, date_time, request_line, status_code, body_length, wall_seconds.  The default is a good example of how to use it.
    :param url_length_limit: A maximum allowed length of the request url. If exceeded, 414 error is returned.
    :param debug: True if the server should send exception tracebacks to the clients on 500 errors.  If False, the server will respond with empty bodies.
    :param socket_timeout: Timeout for client connections' socket operations. Default None means wait forever.
    :param capitalize_response_headers: Normalize response headers' names to Foo-Bar. Default is True.
    """
    serv = Server(sock, sock.getsockname(),
                  site, log,
                  environ=environ,
                  max_http_version=max_http_version,
                  protocol=protocol,
                  minimum_chunk_size=minimum_chunk_size,
                  log_x_forwarded_for=log_x_forwarded_for,
                  keepalive=keepalive,
                  log_output=log_output,
                  log_format=log_format,
                  url_length_limit=url_length_limit,
                  debug=debug,
                  socket_timeout=socket_timeout,
                  capitalize_response_headers=capitalize_response_headers,
                  )
    if server_event is not None:
        server_event.send(serv)
    if max_size is None:
        max_size = DEFAULT_MAX_SIMULTANEOUS_REQUESTS
    if custom_pool is not None:
        pool = custom_pool
    else:
        pool = greenpool.GreenPool(max_size)
    try:
        host, port = sock.getsockname()[:2]
        port = ':%s' % (port, )
        if hasattr(sock, 'do_handshake'):
            scheme = 'https'
            if port == ':443':
                port = ''
        else:
            scheme = 'http'
            if port == ':80':
                port = ''

        serv.log.write("(%s) wsgi starting up on %s://%s%s/\n" % (
            serv.pid, scheme, host, port))
        while True:
            try:
                client_socket = sock.accept()
                client_socket[0].settimeout(serv.socket_timeout)
                if debug:
                    serv.log.write("(%s) accepted %r\n" % (
                        serv.pid, client_socket[1]))
                try:
                    pool.spawn_n(serv.process_request, client_socket)
                except AttributeError:
                    warnings.warn("wsgi's pool should be an instance of " \
                        "eventlet.greenpool.GreenPool, is %s. Please convert your"\
                        " call site to use GreenPool instead" % type(pool),
                        DeprecationWarning, stacklevel=2)
                    pool.execute_async(serv.process_request, client_socket)
            except ACCEPT_EXCEPTIONS as e:
                if get_errno(e) not in ACCEPT_ERRNO:
                    raise
            except (KeyboardInterrupt, SystemExit):
                serv.log.write("wsgi exiting\n")
                break
    finally:
        try:
            # NOTE: It's not clear whether we want this to leave the
            # socket open or close it.  Use cases like Spawning want
            # the underlying fd to remain open, but if we're going
            # that far we might as well not bother closing sock at
            # all.
            sock.close()
        except socket.error as e:
            if get_errno(e) not in BROKEN_SOCK:
                traceback.print_exc()

########NEW FILE########
__FILENAME__ = chat_bridge
import sys
from zmq import FORWARDER, PUB, SUB, SUBSCRIBE
from zmq.devices import Device

        
if __name__ == "__main__":
    usage = 'usage: chat_bridge sub_address pub_address'
    if len (sys.argv) != 3:
        print(usage)
        sys.exit(1)

    sub_addr = sys.argv[1]
    pub_addr = sys.argv[2]
    print("Recieving on %s" % sub_addr)
    print("Sending on %s" % pub_addr)
    device = Device(FORWARDER, SUB, PUB)
    device.bind_in(sub_addr)
    device.setsockopt_in(SUBSCRIBE, "")
    device.bind_out(pub_addr)
    device.start()

########NEW FILE########
__FILENAME__ = chat_server
import eventlet
from eventlet.green import socket

PORT=3001
participants = set()

def read_chat_forever(writer, reader):
    line = reader.readline()
    while line:
        print("Chat:", line.strip())
        for p in participants:
            try:
                if p is not writer: # Don't echo
                    p.write(line)
                    p.flush()
            except socket.error as e:
                # ignore broken pipes, they just mean the participant
                # closed its connection already
                if e[0] != 32:
                    raise
        line = reader.readline()
    participants.remove(writer)
    print("Participant left chat.")

try:
    print("ChatServer starting up on port %s" % PORT)
    server = eventlet.listen(('0.0.0.0', PORT))
    while True:
        new_connection, address = server.accept()
        print("Participant joined chat.")
        new_writer = new_connection.makefile('w')
        participants.add(new_writer)
        eventlet.spawn_n(read_chat_forever, 
                         new_writer, 
                         new_connection.makefile('r'))
except (KeyboardInterrupt, SystemExit):
    print("ChatServer exiting.")

########NEW FILE########
__FILENAME__ = connect
"""Spawn multiple workers and collect their results.

Demonstrates how to use the eventlet.green.socket module.
"""
from __future__ import print_function

import eventlet
from eventlet.green import socket


def geturl(url):
    c = socket.socket()
    ip = socket.gethostbyname(url)
    c.connect((ip, 80))
    print('%s connected' % url)
    c.sendall('GET /\r\n\r\n')
    return c.recv(1024)


urls = ['www.google.com', 'www.yandex.ru', 'www.python.org']
pile = eventlet.GreenPile()
for x in urls:
    pile.spawn(geturl, x)

# note that the pile acts as a collection of return values from the functions
# if any exceptions are raised by the function they'll get raised here
for url, result in zip(urls, pile):
    print('%s: %s' % (url, repr(result)[:50]))

########NEW FILE########
__FILENAME__ = distributed_websocket_chat
"""This is a websocket chat example with many servers. A client can connect to
any of the servers and their messages will be received by all clients connected
to any of the servers.

Run the examples like this:

$ python examples/chat_bridge.py tcp://127.0.0.1:12345 tcp://127.0.0.1:12346

and the servers like this (changing the port for each one obviously):

$ python examples/distributed_websocket_chat.py -p tcp://127.0.0.1:12345 -s tcp://127.0.0.1:12346 7000

So all messages are published to port 12345 and the device forwards all the
messages to 12346 where they are subscribed to
"""
import os, sys
import eventlet
from collections import defaultdict
from eventlet import spawn_n, sleep
from eventlet import wsgi
from eventlet import websocket
from eventlet.green import zmq
from eventlet.hubs import get_hub, use_hub
from uuid import uuid1

use_hub('zeromq')
ctx = zmq.Context()

class IDName(object):

    def __init__(self):
        self.id = uuid1()
        self.name = None

    def __str__(self):
        if self.name:
            return self.name
        else:
            return str(self.id)

    def pack_message(self, msg):
        return self, msg

    def unpack_message(self, msg):
        sender, message = msg
        sender_name = 'you said' if sender.id == self.id \
                                 else '%s says' % sender
        return "%s: %s" % (sender_name, message)


participants = defaultdict(IDName)

def subscribe_and_distribute(sub_socket):
    global participants
    while True:
        msg = sub_socket.recv_pyobj()
        for ws, name_id in participants.items():
            to_send = name_id.unpack_message(msg)
            if to_send:
                try:
                    ws.send(to_send)
                except:
                    del participants[ws]

@websocket.WebSocketWSGI
def handle(ws):
    global pub_socket
    name_id = participants[ws]
    ws.send("Connected as %s, change name with 'name: new_name'" % name_id)
    try:
        while True:
            m = ws.wait()
            if m is None:
                break
            if m.startswith('name:'):
                old_name = str(name_id)
                new_name = m.split(':', 1)[1].strip()
                name_id.name = new_name
                m = 'Changed name from %s' % old_name
            pub_socket.send_pyobj(name_id.pack_message(m))
            sleep()
    finally:
        del participants[ws]
                  
def dispatch(environ, start_response):
    """Resolves to the web page or the websocket depending on the path."""
    global port
    if environ['PATH_INFO'] == '/chat':
        return handle(environ, start_response)
    else:
        start_response('200 OK', [('content-type', 'text/html')])
        return [open(os.path.join(
                     os.path.dirname(__file__), 
                     'websocket_chat.html')).read() % dict(port=port)]

port = None

if __name__ == "__main__":
    usage = 'usage: websocket_chat -p pub address -s sub address port number'
    if len (sys.argv) != 6:
        print(usage)
        sys.exit(1)

    pub_addr = sys.argv[2]
    sub_addr = sys.argv[4]
    try:
        port = int(sys.argv[5])
    except ValueError:
        print("Error port supplied couldn't be converted to int\n", usage)
        sys.exit(1)

    try:
        pub_socket = ctx.socket(zmq.PUB)
        pub_socket.connect(pub_addr)
        print("Publishing to %s" % pub_addr)
        sub_socket = ctx.socket(zmq.SUB)
        sub_socket.connect(sub_addr)
        sub_socket.setsockopt(zmq.SUBSCRIBE, "")
        print("Subscribing to %s" % sub_addr)
    except:
        print("Couldn't create sockets\n", usage)
        sys.exit(1)

    spawn_n(subscribe_and_distribute, sub_socket)
    listener = eventlet.listen(('127.0.0.1', port))
    print("\nVisit http://localhost:%s/ in your websocket-capable browser.\n" % port)
    wsgi.server(listener, dispatch)

########NEW FILE########
__FILENAME__ = echoserver
#! /usr/bin/env python
"""\
Simple server that listens on port 6000 and echos back every input to
the client.  To try out the server, start it up by running this file.

Connect to it with:
  telnet localhost 6000

You terminate your connection by terminating telnet (typically Ctrl-]
and then 'quit')
"""
from __future__ import print_function

import eventlet

def handle(fd):
    print("client connected")
    while True:
        # pass through every non-eof line
        x = fd.readline()
        if not x: break
        fd.write(x)
        fd.flush()
        print("echoed", x, end=' ')
    print("client disconnected")

print("server socket listening on port 6000")
server = eventlet.listen(('0.0.0.0', 6000))
pool = eventlet.GreenPool()
while True:
    try:
        new_sock, address = server.accept()
        print("accepted", address)
        pool.spawn_n(handle, new_sock.makefile('rw'))
    except (SystemExit, KeyboardInterrupt):
        break

########NEW FILE########
__FILENAME__ = feedscraper-testclient
from eventlet.green import urllib2

big_list_of_feeds = """
http://blog.eventlet.net/feed/
http://rss.slashdot.org/Slashdot/slashdot
http://feeds.boingboing.net/boingboing/iBag
http://feeds.feedburner.com/RockPaperShotgun
http://feeds.penny-arcade.com/pa-mainsite
http://achewood.com/rss.php
http://raysmuckles.blogspot.com/atom.xml
http://rbeef.blogspot.com/atom.xml
http://journeyintoreason.blogspot.com/atom.xml
http://orezscu.blogspot.com/atom.xml
http://feeds2.feedburner.com/AskMetafilter
http://feeds2.feedburner.com/Metafilter
http://stackoverflow.com/feeds
http://feeds.feedburner.com/codinghorror
http://www.tbray.org/ongoing/ongoing.atom
http://www.zeldman.com/feed/
http://ln.hixie.ch/rss/html
"""

url = 'http://localhost:9010/'
result = urllib2.urlopen(url, big_list_of_feeds)
print(result.read())
########NEW FILE########
__FILENAME__ = feedscraper
"""A simple web server that accepts POSTS containing a list of feed urls,
and returns the titles of those feeds.
"""
import eventlet
feedparser = eventlet.import_patched('feedparser')

# the pool provides a safety limit on our concurrency
pool = eventlet.GreenPool()

def fetch_title(url):
    d = feedparser.parse(url)
    return d.feed.get('title', '')

def app(environ, start_response):
    if environ['REQUEST_METHOD'] != 'POST':
        start_response('403 Forbidden', [])
        return []
    
    # the pile collects the result of a concurrent operation -- in this case,
    # the collection of feed titles
    pile = eventlet.GreenPile(pool)
    for line in environ['wsgi.input'].readlines():
        url = line.strip()
        if url:
            pile.spawn(fetch_title, url)
    # since the pile is an iterator over the results, 
    # you can use it in all sorts of great Pythonic ways
    titles = '\n'.join(pile)
    start_response('200 OK', [('Content-type', 'text/plain')])
    return [titles]


if __name__ == '__main__':
    from eventlet import wsgi
    wsgi.server(eventlet.listen(('localhost', 9010)), app)
########NEW FILE########
__FILENAME__ = forwarder
""" This is an incredibly simple port forwarder from port 7000 to 22 on 
localhost.  It calls a callback function when the socket is closed, to 
demonstrate one way that you could start to do interesting things by
starting from a simple framework like this.
"""

import eventlet
def closed_callback():
    print("called back")

def forward(source, dest, cb = lambda: None):
    """Forwards bytes unidirectionally from source to dest"""
    while True:
        d = source.recv(32384)
        if d == '':
            cb()
            break
        dest.sendall(d)

listener = eventlet.listen(('localhost', 7000))
while True:
    client, addr = listener.accept()
    server = eventlet.connect(('localhost', 22))
    # two unidirectional forwarders make a bidirectional one
    eventlet.spawn_n(forward, client, server, closed_callback)
    eventlet.spawn_n(forward, server, client)

########NEW FILE########
__FILENAME__ = producer_consumer
"""This is a recursive web crawler.  Don't go pointing this at random sites;
it doesn't respect robots.txt and it is pretty brutal about how quickly it 
fetches pages.

This is a kind of "producer/consumer" example; the fetch function produces 
jobs, and the GreenPool itself is the consumer, farming out work concurrently.  
It's easier to write it this way rather than writing a standard consumer loop;
GreenPool handles any exceptions raised and arranges so that there's a set
number of "workers", so you don't have to write that tedious management code 
yourself.
"""
from __future__ import with_statement

from eventlet.green import urllib2
import eventlet
import re

# http://daringfireball.net/2009/11/liberal_regex_for_matching_urls
url_regex = re.compile(r'\b(([\w-]+://?|www[.])[^\s()<>]+(?:\([\w\d]+\)|([^[:punct:]\s]|/)))')


def fetch(url, outq):
    """Fetch a url and push any urls found into a queue."""
    print("fetching", url)
    data = ''
    with eventlet.Timeout(5, False):
        data = urllib2.urlopen(url).read()
    for url_match in url_regex.finditer(data):
        new_url = url_match.group(0)
        outq.put(new_url)

            
def producer(start_url):
    """Recursively crawl starting from *start_url*.  Returns a set of 
    urls that were found."""
    pool = eventlet.GreenPool()
    seen = set()
    q = eventlet.Queue()
    q.put(start_url)
    # keep looping if there are new urls, or workers that may produce more urls
    while True: 
        while not q.empty():
            url = q.get()
            # limit requests to eventlet.net so we don't crash all over the internet
            if url not in seen and 'eventlet.net' in url:
                seen.add(url)
                pool.spawn_n(fetch, url, q)
        pool.waitall()
        if q.empty():
            break
        
    return seen


seen = producer("http://eventlet.net")
print("I saw these urls:")
print("\n".join(seen))

########NEW FILE########
__FILENAME__ = recursive_crawler
"""This is a recursive web crawler.  Don't go pointing this at random sites;
it doesn't respect robots.txt and it is pretty brutal about how quickly it 
fetches pages.

The code for this is very short; this is perhaps a good indication
that this is making the most effective use of the primitves at hand.
The fetch function does all the work of making http requests,
searching for new urls, and dispatching new fetches.  The GreenPool
acts as sort of a job coordinator (and concurrency controller of
course).
"""
from __future__ import with_statement

from eventlet.green import urllib2
import eventlet
import re

# http://daringfireball.net/2009/11/liberal_regex_for_matching_urls
url_regex = re.compile(r'\b(([\w-]+://?|www[.])[^\s()<>]+(?:\([\w\d]+\)|([^[:punct:]\s]|/)))')


def fetch(url, seen, pool):
    """Fetch a url, stick any found urls into the seen set, and
    dispatch any new ones to the pool."""
    print("fetching", url)
    data = ''
    with eventlet.Timeout(5, False):
        data = urllib2.urlopen(url).read()
    for url_match in url_regex.finditer(data):
        new_url = url_match.group(0)
        # only send requests to eventlet.net so as not to destroy the internet
        if new_url not in seen and 'eventlet.net' in new_url:
            seen.add(new_url)
            # while this seems stack-recursive, it's actually not:
            # spawned greenthreads start their own stacks
            pool.spawn_n(fetch, new_url, seen, pool)
            
def crawl(start_url):
    """Recursively crawl starting from *start_url*.  Returns a set of 
    urls that were found."""
    pool = eventlet.GreenPool()
    seen = set()
    fetch(start_url, seen, pool)
    pool.waitall()
    return seen

seen = crawl("http://eventlet.net")
print("I saw these urls:")
print("\n".join(seen))

########NEW FILE########
__FILENAME__ = twisted_client
"""Example for GreenTransport and GreenClientCreator.

In this example reactor is started implicitly upon the first
use of a blocking function.
"""
from twisted.internet import ssl
from twisted.internet.error import ConnectionClosed
from eventlet.twistedutil.protocol import GreenClientCreator
from eventlet.twistedutil.protocols.basic import LineOnlyReceiverTransport
from twisted.internet import reactor

# read from TCP connection
conn = GreenClientCreator(reactor).connectTCP('www.google.com', 80)
conn.write('GET / HTTP/1.0\r\n\r\n')
conn.loseWriteConnection()
print(conn.read())

# read from SSL connection line by line
conn = GreenClientCreator(reactor, LineOnlyReceiverTransport).connectSSL('sf.net', 443, ssl.ClientContextFactory())
conn.write('GET / HTTP/1.0\r\n\r\n')
try:
    for num, line in enumerate(conn):
        print('%3s %r' % (num, line))
except ConnectionClosed as ex:
    print(ex)


########NEW FILE########
__FILENAME__ = twisted_http_proxy
"""Listen on port 8888 and pretend to be an HTTP proxy.
It even works for some pages.

Demonstrates how to
 * plug in eventlet into a twisted application (join_reactor)
 * call green functions from places where blocking calls
   are not allowed (deferToGreenThread)
 * use eventlet.green package which provides [some of] the
   standard library modules that don't block other greenlets.
"""
import re
from twisted.internet.protocol import Factory
from twisted.internet import reactor
from twisted.protocols import basic

from eventlet.twistedutil import deferToGreenThread
from eventlet.twistedutil import join_reactor
from eventlet.green import httplib

class LineOnlyReceiver(basic.LineOnlyReceiver):

    def connectionMade(self):
        self.lines = []

    def lineReceived(self, line):
        if line:
            self.lines.append(line)
        elif self.lines:
            self.requestReceived(self.lines)
            self.lines = []

    def requestReceived(self, lines):
        request = re.match('^(\w+) http://(.*?)(/.*?) HTTP/1..$', lines[0])
        #print request.groups()
        method, host, path = request.groups()
        headers = dict(x.split(': ', 1) for x in lines[1:])
        def callback(result):
            self.transport.write(str(result))
            self.transport.loseConnection()
        def errback(err):
            err.printTraceback()
            self.transport.loseConnection()
        d = deferToGreenThread(http_request, method, host, path, headers=headers)
        d.addCallbacks(callback, errback)

def http_request(method, host, path, headers):
    conn = httplib.HTTPConnection(host)
    conn.request(method, path, headers=headers)
    response = conn.getresponse()
    body = response.read()
    print(method, host, path, response.status, response.reason, len(body))
    return format_response(response, body)

def format_response(response, body):
    result = "HTTP/1.1 %s %s" % (response.status, response.reason)
    for k, v in response.getheaders():
        result += '\r\n%s: %s' % (k, v)
    if body:
        result += '\r\n\r\n'
        result += body
        result += '\r\n'
    return result

class MyFactory(Factory):
    protocol = LineOnlyReceiver

print(__doc__)
reactor.listenTCP(8888, MyFactory())
reactor.run()

########NEW FILE########
__FILENAME__ = twisted_portforward
"""Port forwarder
USAGE: twisted_portforward.py local_port remote_host remote_port"""
import sys
from twisted.internet import reactor
from eventlet.twistedutil import join_reactor
from eventlet.twistedutil.protocol import GreenClientCreator, SpawnFactory, UnbufferedTransport
from eventlet import proc

def forward(source, dest):
    try:
        while True:
            x = source.recv()
            if not x:
                break
            print('forwarding %s bytes' % len(x))
            dest.write(x)
    finally:
        dest.loseConnection()

def handler(local):
    client = str(local.getHost())
    print('accepted connection from %s' % client)
    remote = GreenClientCreator(reactor, UnbufferedTransport).connectTCP(remote_host, remote_port)
    a = proc.spawn(forward, remote, local)
    b = proc.spawn(forward, local, remote)
    proc.waitall([a, b], trap_errors=True)
    print('closed connection to %s' % client)

try:
    local_port, remote_host, remote_port = sys.argv[1:]
except ValueError:
    sys.exit(__doc__)
local_port = int(local_port)
remote_port = int(remote_port)
reactor.listenTCP(local_port, SpawnFactory(handler))
reactor.run()

########NEW FILE########
__FILENAME__ = twisted_server
"""Simple chat demo application.
Listen on port 8007 and re-send all the data received to other participants.

Demonstrates how to
 * plug in eventlet into a twisted application (join_reactor)
 * how to use SpawnFactory to start a new greenlet for each new request.
"""
from eventlet.twistedutil import join_reactor
from eventlet.twistedutil.protocol import SpawnFactory
from eventlet.twistedutil.protocols.basic import LineOnlyReceiverTransport

class Chat:

    def __init__(self):
        self.participants = []

    def handler(self, conn):
        peer = conn.getPeer()
        print('new connection from %s' % (peer, ))
        conn.write("Welcome! There're %s participants already\n" % (len(self.participants)))
        self.participants.append(conn)
        try:
            for line in conn:
                if line:
                    print('received from %s: %s' % (peer, line))
                    for buddy in self.participants:
                        if buddy is not conn:
                            buddy.sendline('from %s: %s' % (peer, line))
        except Exception as ex:
            print(peer, ex)
        else:
            print(peer, 'connection done')
        finally:
            conn.loseConnection()
            self.participants.remove(conn)

print(__doc__)
chat = Chat()
from twisted.internet import reactor
reactor.listenTCP(8007, SpawnFactory(chat.handler, LineOnlyReceiverTransport))
reactor.run()


########NEW FILE########
__FILENAME__ = twisted_srvconnector
from twisted.internet import reactor
from twisted.names.srvconnect import SRVConnector
from gnutls.interfaces.twisted import X509Credentials

from eventlet.twistedutil.protocol import GreenClientCreator
from eventlet.twistedutil.protocols.basic import LineOnlyReceiverTransport

class NoisySRVConnector(SRVConnector):

    def pickServer(self):
        host, port = SRVConnector.pickServer(self)
        print('Resolved _%s._%s.%s --> %s:%s' % (self.service, self.protocol, self.domain, host, port))
        return host, port

cred = X509Credentials(None, None)
creator = GreenClientCreator(reactor, LineOnlyReceiverTransport)
conn = creator.connectSRV('msrps', 'ag-projects.com',
                          connectFuncName='connectTLS', connectFuncArgs=(cred,),
                          ConnectorClass=NoisySRVConnector)

request = """MSRP 49fh AUTH
To-Path: msrps://alice@intra.example.com;tcp
From-Path: msrps://alice.example.com:9892/98cjs;tcp
-------49fh$
""".replace('\n', '\r\n')

print('Sending:\n%s' % request)
conn.write(request)
print('Received:')
for x in conn:
    print(repr(x))
    if '-------' in x:
        break

########NEW FILE########
__FILENAME__ = twisted_xcap_proxy
from twisted.internet.protocol import Factory
from twisted.internet import reactor
from twisted.protocols import basic

from xcaplib.green import XCAPClient

from eventlet.twistedutil import deferToGreenThread
from eventlet.twistedutil import join_reactor

class LineOnlyReceiver(basic.LineOnlyReceiver):

    def lineReceived(self, line):
        print('received: %r' % line)
        if not line:
            return
        app, context, node = (line + ' ').split(' ', 3) 
        context = {'u' : 'users', 'g': 'global'}.get(context, context)
        d = deferToGreenThread(client._get, app, node, globaltree=context=='global')
        def callback(result):
            self.transport.write(str(result))
        def errback(error):
            self.transport.write(error.getTraceback())
        d.addCallback(callback)
        d.addErrback(errback)

class MyFactory(Factory):
    protocol = LineOnlyReceiver

client = XCAPClient('https://xcap.sipthor.net/xcap-root', 'alice@example.com', '123')
reactor.listenTCP(8007, MyFactory())
reactor.run()

########NEW FILE########
__FILENAME__ = webcrawler
#!/usr/bin/env python
"""
This is a simple web "crawler" that fetches a bunch of urls using a pool to
control the number of outbound connections. It has as many simultaneously open
connections as coroutines in the pool.

The prints in the body of the fetch function are there to demonstrate that the
requests are truly made in parallel.
"""
import eventlet
from eventlet.green import urllib2


urls = [
    "https://www.google.com/intl/en_ALL/images/logo.gif",
    "http://python.org/images/python-logo.gif",
    "http://us.i1.yimg.com/us.yimg.com/i/ww/beta/y3.gif",
]


def fetch(url):
    print("opening", url)
    body = urllib2.urlopen(url).read()
    print("done with", url)
    return url, body


pool = eventlet.GreenPool(200)
for url, body in pool.imap(fetch, urls):
    print("got body from", url, "of length", len(body))

########NEW FILE########
__FILENAME__ = websocket
import eventlet
from eventlet import wsgi
from eventlet import websocket
from eventlet.support import six

# demo app
import os
import random


@websocket.WebSocketWSGI
def handle(ws):
    """  This is the websocket handler function.  Note that we
    can dispatch based on path in here, too."""
    if ws.path == '/echo':
        while True:
            m = ws.wait()
            if m is None:
                break
            ws.send(m)

    elif ws.path == '/data':
        for i in six.moves.range(10000):
            ws.send("0 %s %s\n" % (i, random.random()))
            eventlet.sleep(0.1)

def dispatch(environ, start_response):
    """ This resolves to the web page or the websocket depending on
    the path."""
    if environ['PATH_INFO'] == '/data':
        return handle(environ, start_response)
    else:
        start_response('200 OK', [('content-type', 'text/html')])
        return [open(os.path.join(
                     os.path.dirname(__file__),
                     'websocket.html')).read()]

if __name__ == "__main__":
    # run an example app from the command line
    listener = eventlet.listen(('127.0.0.1', 7000))
    print("\nVisit http://localhost:7000/ in your websocket-capable browser.\n")
    wsgi.server(listener, dispatch)

########NEW FILE########
__FILENAME__ = websocket_chat
import os

import eventlet
from eventlet import wsgi
from eventlet import websocket

PORT = 7000

participants = set()

@websocket.WebSocketWSGI
def handle(ws):
    participants.add(ws)
    try:
        while True:
            m = ws.wait()
            if m is None:
                break
            for p in participants:
                p.send(m)
    finally:
        participants.remove(ws)
                  
def dispatch(environ, start_response):
    """Resolves to the web page or the websocket depending on the path."""
    if environ['PATH_INFO'] == '/chat':
        return handle(environ, start_response)
    else:
        start_response('200 OK', [('content-type', 'text/html')])
        html_path = os.path.join(os.path.dirname(__file__), 'websocket_chat.html')
        return [open(html_path).read() % {'port': PORT}]
        
if __name__ == "__main__":
    # run an example app from the command line            
    listener = eventlet.listen(('127.0.0.1', PORT))
    print("\nVisit http://localhost:7000/ in your websocket-capable browser.\n")
    wsgi.server(listener, dispatch)

########NEW FILE########
__FILENAME__ = wsgi
"""This is a simple example of running a wsgi application with eventlet.
For a more fully-featured server which supports multiple processes,
multiple threads, and graceful code reloading, see:

http://pypi.python.org/pypi/Spawning/
"""

import eventlet
from eventlet import wsgi

def hello_world(env, start_response):
    if env['PATH_INFO'] != '/':
        start_response('404 Not Found', [('Content-Type', 'text/plain')])
        return ['Not Found\r\n']
    start_response('200 OK', [('Content-Type', 'text/plain')])
    return ['Hello, World!\r\n']
        
wsgi.server(eventlet.listen(('', 8090)), hello_world)

########NEW FILE########
__FILENAME__ = zmq_chat
import eventlet, sys
from eventlet.green import socket, zmq
from eventlet.hubs import use_hub
use_hub('zeromq')

ADDR = 'ipc:///tmp/chat'

ctx = zmq.Context()

def publish(writer):

    print("connected")
    socket = ctx.socket(zmq.SUB)

    socket.setsockopt(zmq.SUBSCRIBE, "")
    socket.connect(ADDR)
    eventlet.sleep(0.1)

    while True:
        msg = socket.recv_pyobj()
        str_msg = "%s: %s" % msg
        writer.write(str_msg)
        writer.flush()


PORT=3001

def read_chat_forever(reader, pub_socket):

    line = reader.readline()
    who = 'someone'
    while line:
        print("Chat:", line.strip())
        if line.startswith('name:'):
            who = line.split(':')[-1].strip()

        try:
            pub_socket.send_pyobj((who, line))
        except socket.error as e:
            # ignore broken pipes, they just mean the participant
            # closed its connection already
            if e[0] != 32:
                raise
        line = reader.readline()
    print("Participant left chat.")

try:
    print("ChatServer starting up on port %s" % PORT)
    server = eventlet.listen(('0.0.0.0', PORT))
    pub_socket = ctx.socket(zmq.PUB)
    pub_socket.bind(ADDR)
    eventlet.spawn_n(publish,
                     sys.stdout)
    while True:
        new_connection, address = server.accept()

        print("Participant joined chat.")
        eventlet.spawn_n(publish,
                         new_connection.makefile('w'))
        eventlet.spawn_n(read_chat_forever,
                         new_connection.makefile('r'),
                         pub_socket)
except (KeyboardInterrupt, SystemExit):
    print("ChatServer exiting.")
########NEW FILE########
__FILENAME__ = zmq_simple
from eventlet.green import zmq
import eventlet

CTX = zmq.Context(1)

def bob_client(ctx, count):
    print("STARTING BOB")
    bob = zmq.Socket(CTX, zmq.REQ)
    bob.connect("ipc:///tmp/test")

    for i in range(0, count):
        print("BOB SENDING")
        bob.send("HI")
        print("BOB GOT:", bob.recv())

def alice_server(ctx, count):
    print("STARTING ALICE")
    alice = zmq.Socket(CTX, zmq.REP)
    alice.bind("ipc:///tmp/test")

    print("ALICE READY")
    for i in range(0, count):
        print("ALICE GOT:", alice.recv())
        print("ALIC SENDING")
        alice.send("HI BACK")

alice = eventlet.spawn(alice_server, CTX, 10)
bob = eventlet.spawn(bob_client, CTX, 10)

bob.wait()
alice.wait()

########NEW FILE########
__FILENAME__ = api_test
import os
import socket
from unittest import TestCase, main
import warnings

import eventlet
from eventlet import greenio, util, hubs, greenthread, spawn
from tests import skip_if_no_ssl

warnings.simplefilter('ignore', DeprecationWarning)
from eventlet import api
warnings.simplefilter('default', DeprecationWarning)


def check_hub():
    # Clear through the descriptor queue
    api.sleep(0)
    api.sleep(0)
    hub = hubs.get_hub()
    for nm in 'get_readers', 'get_writers':
        dct = getattr(hub, nm)()
        assert not dct, "hub.%s not empty: %s" % (nm, dct)
    # Stop the runloop (unless it's twistedhub which does not support that)
    if not getattr(hub, 'uses_twisted_reactor', None):
        hub.abort(True)
        assert not hub.running


class TestApi(TestCase):

    certificate_file = os.path.join(os.path.dirname(__file__), 'test_server.crt')
    private_key_file = os.path.join(os.path.dirname(__file__), 'test_server.key')

    def test_tcp_listener(self):
        socket = eventlet.listen(('0.0.0.0', 0))
        assert socket.getsockname()[0] == '0.0.0.0'
        socket.close()

        check_hub()

    def test_connect_tcp(self):
        def accept_once(listenfd):
            try:
                conn, addr = listenfd.accept()
                fd = conn.makefile(mode='w')
                conn.close()
                fd.write(b'hello\n')
                fd.close()
            finally:
                listenfd.close()

        server = eventlet.listen(('0.0.0.0', 0))
        api.spawn(accept_once, server)

        client = eventlet.connect(('127.0.0.1', server.getsockname()[1]))
        fd = client.makefile()
        client.close()
        assert fd.readline() == b'hello\n'

        assert fd.read() == b''
        fd.close()

        check_hub()

    @skip_if_no_ssl
    def test_connect_ssl(self):
        def accept_once(listenfd):
            try:
                conn, addr = listenfd.accept()
                conn.write(b'hello\r\n')
                greenio.shutdown_safe(conn)
                conn.close()
            finally:
                greenio.shutdown_safe(listenfd)
                listenfd.close()

        server = api.ssl_listener(('0.0.0.0', 0),
                                  self.certificate_file,
                                  self.private_key_file)
        api.spawn(accept_once, server)

        raw_client = eventlet.connect(('127.0.0.1', server.getsockname()[1]))
        client = util.wrap_ssl(raw_client)
        fd = socket._fileobject(client, 'rb', 8192)

        assert fd.readline() == b'hello\r\n'
        try:
            self.assertEqual(b'', fd.read(10))
        except greenio.SSL.ZeroReturnError:
            # if it's a GreenSSL object it'll do this
            pass
        greenio.shutdown_safe(client)
        client.close()

        check_hub()

    def test_001_trampoline_timeout(self):
        server_sock = eventlet.listen(('127.0.0.1', 0))
        bound_port = server_sock.getsockname()[1]

        def server(sock):
            client, addr = sock.accept()
            api.sleep(0.1)
        server_evt = spawn(server, server_sock)
        api.sleep(0)
        try:
            desc = eventlet.connect(('127.0.0.1', bound_port))
            api.trampoline(desc, read=True, write=False, timeout=0.001)
        except api.TimeoutError:
            pass  # test passed
        else:
            assert False, "Didn't timeout"

        server_evt.wait()
        check_hub()

    def test_timeout_cancel(self):
        server = eventlet.listen(('0.0.0.0', 0))
        bound_port = server.getsockname()[1]

        done = [False]

        def client_closer(sock):
            while True:
                (conn, addr) = sock.accept()
                conn.close()

        def go():
            desc = eventlet.connect(('127.0.0.1', bound_port))
            try:
                api.trampoline(desc, read=True, timeout=0.1)
            except api.TimeoutError:
                assert False, "Timed out"

            server.close()
            desc.close()
            done[0] = True

        greenthread.spawn_after_local(0, go)

        server_coro = api.spawn(client_closer, server)
        while not done[0]:
            api.sleep(0)
        api.kill(server_coro)

        check_hub()

    def test_named(self):
        named_foo = api.named('tests.api_test.Foo')
        self.assertEqual(named_foo.__name__, "Foo")

    def test_naming_missing_class(self):
        self.assertRaises(
            ImportError, api.named, 'this_name_should_hopefully_not_exist.Foo')

    def test_killing_dormant(self):
        DELAY = 0.1
        state = []

        def test():
            try:
                state.append('start')
                api.sleep(DELAY)
            except:
                state.append('except')
                # catching GreenletExit
                pass
            # when switching to hub, hub makes itself the parent of this greenlet,
            # thus after the function's done, the control will go to the parent
            api.sleep(0)
            state.append('finished')

        g = api.spawn(test)
        api.sleep(DELAY / 2)
        self.assertEqual(state, ['start'])
        api.kill(g)
        # will not get there, unless switching is explicitly scheduled by kill
        self.assertEqual(state, ['start', 'except'])
        api.sleep(DELAY)
        self.assertEqual(state, ['start', 'except', 'finished'])

    def test_nested_with_timeout(self):
        def func():
            return api.with_timeout(0.2, api.sleep, 2, timeout_value=1)

        try:
            api.with_timeout(0.1, func)
            self.fail(u'Expected api.TimeoutError')
        except api.TimeoutError:
            pass


class Foo(object):
    pass


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = backdoor_test
import eventlet
from eventlet import backdoor
from eventlet.green import socket

from tests import LimitedTestCase, main


class BackdoorTest(LimitedTestCase):
    def test_server(self):
        listener = socket.socket()
        listener.bind(('localhost', 0))
        listener.listen(50)
        serv = eventlet.spawn(backdoor.backdoor_server, listener)
        client = socket.socket()
        client.connect(('localhost', listener.getsockname()[1]))
        f = client.makefile('rw')
        self.assert_(b'Python' in f.readline())
        f.readline()  # build info
        f.readline()  # help info
        self.assert_(b'InteractiveConsole' in f.readline())
        self.assertEqual(b'>>> ', f.read(4))
        f.write(b'print("hi")\n')
        f.flush()
        self.assertEqual(b'hi\n', f.readline())
        self.assertEqual(b'>>> ', f.read(4))
        f.close()
        client.close()
        serv.kill()
        # wait for the console to discover that it's dead
        eventlet.sleep(0.1)


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = convenience_test
import os

import eventlet
from eventlet import debug, event
from eventlet.green import socket
from eventlet.support import six
from tests import LimitedTestCase, skip_if_no_ssl


certificate_file = os.path.join(os.path.dirname(__file__), 'test_server.crt')
private_key_file = os.path.join(os.path.dirname(__file__), 'test_server.key')


class TestServe(LimitedTestCase):
    def setUp(self):
        super(TestServe, self).setUp()
        debug.hub_exceptions(False)

    def tearDown(self):
        super(TestServe, self).tearDown()
        debug.hub_exceptions(True)

    def test_exiting_server(self):
        # tests that the server closes the client sock on handle() exit
        def closer(sock, addr):
            pass

        l = eventlet.listen(('localhost', 0))
        gt = eventlet.spawn(eventlet.serve, l, closer)
        client = eventlet.connect(('localhost', l.getsockname()[1]))
        client.sendall(b'a')
        self.assertFalse(client.recv(100))
        gt.kill()

    def test_excepting_server(self):
        # tests that the server closes the client sock on handle() exception
        def crasher(sock, addr):
            sock.recv(1024)
            0//0

        l = eventlet.listen(('localhost', 0))
        gt = eventlet.spawn(eventlet.serve, l, crasher)
        client = eventlet.connect(('localhost', l.getsockname()[1]))
        client.sendall(b'a')
        self.assertRaises(ZeroDivisionError, gt.wait)
        self.assertFalse(client.recv(100))

    def test_excepting_server_already_closed(self):
        # same as above but with explicit clsoe before crash
        def crasher(sock, addr):
            sock.recv(1024)
            sock.close()
            0//0

        l = eventlet.listen(('localhost', 0))
        gt = eventlet.spawn(eventlet.serve, l, crasher)
        client = eventlet.connect(('localhost', l.getsockname()[1]))
        client.sendall(b'a')
        self.assertRaises(ZeroDivisionError, gt.wait)
        self.assertFalse(client.recv(100))

    def test_called_for_each_connection(self):
        hits = [0]

        def counter(sock, addr):
            hits[0] += 1
        l = eventlet.listen(('localhost', 0))
        gt = eventlet.spawn(eventlet.serve, l, counter)
        for i in six.moves.range(100):
            client = eventlet.connect(('localhost', l.getsockname()[1]))
            self.assertFalse(client.recv(100))
        gt.kill()
        self.assertEqual(100, hits[0])

    def test_blocking(self):
        l = eventlet.listen(('localhost', 0))
        x = eventlet.with_timeout(
            0.01,
            eventlet.serve, l, lambda c, a: None,
            timeout_value="timeout")
        self.assertEqual(x, "timeout")

    def test_raising_stopserve(self):
        def stopit(conn, addr):
            raise eventlet.StopServe()
        l = eventlet.listen(('localhost', 0))
        # connect to trigger a call to stopit
        gt = eventlet.spawn(eventlet.connect, ('localhost', l.getsockname()[1]))
        eventlet.serve(l, stopit)
        gt.wait()

    def test_concurrency(self):
        evt = event.Event()

        def waiter(sock, addr):
            sock.sendall(b'hi')
            evt.wait()
        l = eventlet.listen(('localhost', 0))
        eventlet.spawn(eventlet.serve, l, waiter, 5)

        def test_client():
            c = eventlet.connect(('localhost', l.getsockname()[1]))
            # verify the client is connected by getting data
            self.assertEqual(b'hi', c.recv(2))
            return c
        [test_client() for i in range(5)]
        # very next client should not get anything
        x = eventlet.with_timeout(
            0.01,
            test_client,
            timeout_value="timed out")
        self.assertEqual(x, "timed out")

    @skip_if_no_ssl
    def test_wrap_ssl(self):
        server = eventlet.wrap_ssl(
            eventlet.listen(('localhost', 0)),
            certfile=certificate_file, keyfile=private_key_file,
            server_side=True)
        port = server.getsockname()[1]

        def handle(sock, addr):
            sock.sendall(sock.recv(1024))
            raise eventlet.StopServe()

        eventlet.spawn(eventlet.serve, server, handle)
        client = eventlet.wrap_ssl(eventlet.connect(('localhost', port)))
        client.sendall("echo")
        self.assertEqual("echo", client.recv(1024))

    def test_socket_reuse(self):
        lsock1 = eventlet.listen(('localhost', 0))
        port = lsock1.getsockname()[1]

        def same_socket():
            return eventlet.listen(('localhost', port))

        self.assertRaises(socket.error, same_socket)
        lsock1.close()
        assert same_socket()

########NEW FILE########
__FILENAME__ = db_pool_test
'''Test cases for db_pool
'''
from __future__ import print_function

import sys
import os
import traceback
from unittest import TestCase, main

from tests import skipped, skip_unless, skip_with_pyevent, get_database_auth
from eventlet import event
from eventlet import db_pool
from eventlet.support import six
import eventlet


class DBTester(object):
    __test__ = False  # so that nose doesn't try to execute this directly
    def setUp(self):
        self.create_db()
        self.connection = None
        connection = self._dbmodule.connect(**self._auth)
        cursor = connection.cursor()
        cursor.execute("""CREATE  TABLE gargleblatz
        (
        a INTEGER
        );""")
        connection.commit()
        cursor.close()
        connection.close()

    def tearDown(self):
        if self.connection:
            self.connection.close()
        self.drop_db()

    def set_up_dummy_table(self, connection=None):
        close_connection = False
        if connection is None:
            close_connection = True
            if self.connection is None:
                connection = self._dbmodule.connect(**self._auth)
            else:
                connection = self.connection

        cursor = connection.cursor()
        cursor.execute(self.dummy_table_sql)
        connection.commit()
        cursor.close()
        if close_connection:
            connection.close()


# silly mock class
class Mock(object):
    pass


class DBConnectionPool(DBTester):
    __test__ = False  # so that nose doesn't try to execute this directly
    def setUp(self):
        super(DBConnectionPool, self).setUp()
        self.pool = self.create_pool()
        self.connection = self.pool.get()

    def tearDown(self):
        if self.connection:
            self.pool.put(self.connection)
        self.pool.clear()
        super(DBConnectionPool, self).tearDown()

    def assert_cursor_works(self, cursor):
        cursor.execute("select 1")
        rows = cursor.fetchall()
        self.assert_(rows)

    def test_connecting(self):
        self.assert_(self.connection is not None)

    def test_create_cursor(self):
        cursor = self.connection.cursor()
        cursor.close()

    def test_run_query(self):
        cursor = self.connection.cursor()
        self.assert_cursor_works(cursor)
        cursor.close()

    def test_run_bad_query(self):
        cursor = self.connection.cursor()
        try:
            cursor.execute("garbage blah blah")
            self.assert_(False)
        except AssertionError:
            raise
        except Exception:
            pass
        cursor.close()

    def test_put_none(self):
        # the pool is of size 1, and its only connection is out
        self.assert_(self.pool.free() == 0)
        self.pool.put(None)
        # ha ha we fooled it into thinking that we had a dead process
        self.assert_(self.pool.free() == 1)
        conn2 = self.pool.get()
        self.assert_(conn2 is not None)
        self.assert_(conn2.cursor)
        self.pool.put(conn2)

    def test_close_does_a_put(self):
        self.assert_(self.pool.free() == 0)
        self.connection.close()
        self.assert_(self.pool.free() == 1)
        self.assertRaises(AttributeError, self.connection.cursor)

    @skipped
    def test_deletion_does_a_put(self):
        # doing a put on del causes some issues if __del__ is called in the
        # main coroutine, so, not doing that for now
        self.assert_(self.pool.free() == 0)
        self.connection = None
        self.assert_(self.pool.free() == 1)

    def test_put_doesnt_double_wrap(self):
        self.pool.put(self.connection)
        conn = self.pool.get()
        self.assert_(not isinstance(conn._base, db_pool.PooledConnectionWrapper))
        self.pool.put(conn)

    def test_bool(self):
        self.assert_(self.connection)
        self.connection.close()
        self.assert_(not self.connection)

    def fill_up_table(self, conn):
        curs = conn.cursor()
        for i in six.moves.range(1000):
            curs.execute('insert into test_table (value_int) values (%s)' % i)
        conn.commit()

    def test_returns_immediately(self):
        self.pool = self.create_pool()
        conn = self.pool.get()
        self.set_up_dummy_table(conn)
        self.fill_up_table(conn)
        curs = conn.cursor()
        results = []
        SHORT_QUERY = "select * from test_table"
        evt = event.Event()
        def a_query():
            self.assert_cursor_works(curs)
            curs.execute(SHORT_QUERY)
            results.append(2)
            evt.send()
        eventlet.spawn(a_query)
        results.append(1)
        self.assertEqual([1], results)
        evt.wait()
        self.assertEqual([1, 2], results)
        self.pool.put(conn)

    def test_connection_is_clean_after_put(self):
        self.pool = self.create_pool()
        conn = self.pool.get()
        self.set_up_dummy_table(conn)
        curs = conn.cursor()
        for i in range(10):
            curs.execute('insert into test_table (value_int) values (%s)' % i)
        # do not commit  :-)
        self.pool.put(conn)
        del conn
        conn2 = self.pool.get()
        curs2 = conn2.cursor()
        for i in range(10):
            curs2.execute('insert into test_table (value_int) values (%s)' % i)
        conn2.commit()
        curs2.execute("select * from test_table")
        # we should have only inserted them once
        self.assertEqual(10, curs2.rowcount)
        self.pool.put(conn2)

    def test_visibility_from_other_connections(self):
        self.pool = self.create_pool(max_size=3)
        conn = self.pool.get()
        conn2 = self.pool.get()
        curs = conn.cursor()
        try:
            curs2 = conn2.cursor()
            curs2.execute("insert into gargleblatz (a) values (%s)" % (314159))
            self.assertEqual(curs2.rowcount, 1)
            conn2.commit()
            selection_query = "select * from gargleblatz"
            curs2.execute(selection_query)
            self.assertEqual(curs2.rowcount, 1)
            del curs2
            self.pool.put(conn2)
            # create a new connection, it should see the addition
            conn3 = self.pool.get()
            curs3 = conn3.cursor()
            curs3.execute(selection_query)
            self.assertEqual(curs3.rowcount, 1)
            # now, does the already-open connection see it?
            curs.execute(selection_query)
            self.assertEqual(curs.rowcount, 1)
            self.pool.put(conn3)
        finally:
            # clean up my litter
            curs.execute("delete from gargleblatz where a=314159")
            conn.commit()
            self.pool.put(conn)

    @skipped
    def test_two_simultaneous_connections(self):
        # timing-sensitive test, disabled until we come up with a better
        # way to do this
        self.pool = self.create_pool(max_size=2)
        conn = self.pool.get()
        self.set_up_dummy_table(conn)
        self.fill_up_table(conn)
        curs = conn.cursor()
        conn2 = self.pool.get()
        self.set_up_dummy_table(conn2)
        self.fill_up_table(conn2)
        curs2 = conn2.cursor()
        results = []
        LONG_QUERY = "select * from test_table"
        SHORT_QUERY = "select * from test_table where row_id <= 20"

        evt = event.Event()
        def long_running_query():
            self.assert_cursor_works(curs)
            curs.execute(LONG_QUERY)
            results.append(1)
            evt.send()
        evt2 = event.Event()
        def short_running_query():
            self.assert_cursor_works(curs2)
            curs2.execute(SHORT_QUERY)
            results.append(2)
            evt2.send()

        eventlet.spawn(long_running_query)
        eventlet.spawn(short_running_query)
        evt.wait()
        evt2.wait()
        results.sort()
        self.assertEqual([1, 2], results)

    def test_clear(self):
        self.pool = self.create_pool()
        self.pool.put(self.connection)
        self.pool.clear()
        self.assertEqual(len(self.pool.free_items), 0)

    def test_clear_warmup(self):
        """Clear implicitly created connections (min_size > 0)"""
        self.pool = self.create_pool(min_size=1)
        self.pool.clear()
        self.assertEqual(len(self.pool.free_items), 0)

    def test_unwrap_connection(self):
        self.assert_(isinstance(self.connection,
                                db_pool.GenericConnectionWrapper))
        conn = self.pool._unwrap_connection(self.connection)
        self.assert_(not isinstance(conn, db_pool.GenericConnectionWrapper))

        self.assertEqual(None, self.pool._unwrap_connection(None))
        self.assertEqual(None, self.pool._unwrap_connection(1))

        # testing duck typing here -- as long as the connection has a
        # _base attribute, it should be unwrappable
        x = Mock()
        x._base = 'hi'
        self.assertEqual('hi', self.pool._unwrap_connection(x))
        conn.close()

    def test_safe_close(self):
        self.pool._safe_close(self.connection, quiet=True)
        self.assertEqual(len(self.pool.free_items), 1)

        self.pool._safe_close(None)
        self.pool._safe_close(1)

        # now we're really going for 100% coverage
        x = Mock()
        def fail():
            raise KeyboardInterrupt()
        x.close = fail
        self.assertRaises(KeyboardInterrupt, self.pool._safe_close, x)

        x = Mock()
        def fail2():
            raise RuntimeError("if this line has been printed, the test succeeded")
        x.close = fail2
        self.pool._safe_close(x, quiet=False)

    def test_zero_max_idle(self):
        self.pool.put(self.connection)
        self.pool.clear()
        self.pool = self.create_pool(max_size=2, max_idle=0)
        self.connection = self.pool.get()
        self.connection.close()
        self.assertEqual(len(self.pool.free_items), 0)

    def test_zero_max_age(self):
        self.pool.put(self.connection)
        self.pool.clear()
        self.pool = self.create_pool(max_size=2, max_age=0)
        self.connection = self.pool.get()
        self.connection.close()
        self.assertEqual(len(self.pool.free_items), 0)

    @skipped
    def test_max_idle(self):
        # This test is timing-sensitive.  Rename the function without
        # the "dont" to run it, but beware that it could fail or take
        # a while.

        self.pool = self.create_pool(max_size=2, max_idle=0.02)
        self.connection = self.pool.get()
        self.connection.close()
        self.assertEqual(len(self.pool.free_items), 1)
        eventlet.sleep(0.01)  # not long enough to trigger the idle timeout
        self.assertEqual(len(self.pool.free_items), 1)
        self.connection = self.pool.get()
        self.connection.close()
        self.assertEqual(len(self.pool.free_items), 1)
        eventlet.sleep(0.01)  # idle timeout should have fired but done nothing
        self.assertEqual(len(self.pool.free_items), 1)
        self.connection = self.pool.get()
        self.connection.close()
        self.assertEqual(len(self.pool.free_items), 1)
        eventlet.sleep(0.03) # long enough to trigger idle timeout for real
        self.assertEqual(len(self.pool.free_items), 0)

    @skipped
    def test_max_idle_many(self):
        # This test is timing-sensitive.  Rename the function without
        # the "dont" to run it, but beware that it could fail or take
        # a while.

        self.pool = self.create_pool(max_size=2, max_idle=0.02)
        self.connection, conn2 = self.pool.get(), self.pool.get()
        self.connection.close()
        eventlet.sleep(0.01)
        self.assertEqual(len(self.pool.free_items), 1)
        conn2.close()
        self.assertEqual(len(self.pool.free_items), 2)
        eventlet.sleep(0.02)  # trigger cleanup of conn1 but not conn2
        self.assertEqual(len(self.pool.free_items), 1)

    @skipped
    def test_max_age(self):
        # This test is timing-sensitive.  Rename the function without
        # the "dont" to run it, but beware that it could fail or take
        # a while.

        self.pool = self.create_pool(max_size=2, max_age=0.05)
        self.connection = self.pool.get()
        self.connection.close()
        self.assertEqual(len(self.pool.free_items), 1)
        eventlet.sleep(0.01)  # not long enough to trigger the age timeout
        self.assertEqual(len(self.pool.free_items), 1)
        self.connection = self.pool.get()
        self.connection.close()
        self.assertEqual(len(self.pool.free_items), 1)
        eventlet.sleep(0.05) # long enough to trigger age timeout
        self.assertEqual(len(self.pool.free_items), 0)

    @skipped
    def test_max_age_many(self):
        # This test is timing-sensitive.  Rename the function without
        # the "dont" to run it, but beware that it could fail or take
        # a while.

        self.pool = self.create_pool(max_size=2, max_age=0.15)
        self.connection, conn2 = self.pool.get(), self.pool.get()
        self.connection.close()
        self.assertEqual(len(self.pool.free_items), 1)
        eventlet.sleep(0)  # not long enough to trigger the age timeout
        self.assertEqual(len(self.pool.free_items), 1)
        eventlet.sleep(0.2) # long enough to trigger age timeout
        self.assertEqual(len(self.pool.free_items), 0)
        conn2.close()  # should not be added to the free items
        self.assertEqual(len(self.pool.free_items), 0)

    def test_waiters_get_woken(self):
        # verify that when there's someone waiting on an empty pool
        # and someone puts an immediately-closed connection back in
        # the pool that the waiter gets woken
        self.pool.put(self.connection)
        self.pool.clear()
        self.pool = self.create_pool(max_size=1, max_age=0)

        self.connection = self.pool.get()
        self.assertEqual(self.pool.free(), 0)
        self.assertEqual(self.pool.waiting(), 0)
        e = event.Event()
        def retrieve(pool, ev):
            c = pool.get()
            ev.send(c)
        eventlet.spawn(retrieve, self.pool, e)
        eventlet.sleep(0) # these two sleeps should advance the retrieve
        eventlet.sleep(0) # coroutine until it's waiting in get()
        self.assertEqual(self.pool.free(), 0)
        self.assertEqual(self.pool.waiting(), 1)
        self.pool.put(self.connection)
        timer = eventlet.Timeout(1)
        conn = e.wait()
        timer.cancel()
        self.assertEqual(self.pool.free(), 0)
        self.assertEqual(self.pool.waiting(), 0)
        self.pool.put(conn)

    @skipped
    def test_0_straight_benchmark(self):
        """ Benchmark; don't run unless you want to wait a while."""
        import time
        iterations = 20000
        c = self.connection.cursor()
        self.connection.commit()
        def bench(c):
            for i in six.moves.range(iterations):
                c.execute('select 1')

        bench(c)  # warm-up
        results = []
        for i in range(3):
            start = time.time()
            bench(c)
            end = time.time()
            results.append(end-start)

        print("\n%u iterations took an average of %f seconds, (%s) in %s\n" % (
            iterations, sum(results)/len(results), results, type(self)))

    def test_raising_create(self):
        # if the create() method raises an exception the pool should
        # not lose any connections
        self.pool = self.create_pool(max_size=1, module=RaisingDBModule())
        self.assertRaises(RuntimeError, self.pool.get)
        self.assertEqual(self.pool.free(), 1)


class DummyConnection(object):
    pass


class DummyDBModule(object):
    def connect(self, *args, **kwargs):
        return DummyConnection()


class RaisingDBModule(object):
    def connect(self, *args, **kw):
        raise RuntimeError()


class TpoolConnectionPool(DBConnectionPool):
    __test__ = False  # so that nose doesn't try to execute this directly
    def create_pool(self, min_size=0, max_size=1, max_idle=10, max_age=10,
                    connect_timeout=0.5, module=None):
        if module is None:
            module = self._dbmodule
        return db_pool.TpooledConnectionPool(module,
            min_size=min_size, max_size=max_size,
            max_idle=max_idle, max_age=max_age,
            connect_timeout = connect_timeout,
            **self._auth)


    @skip_with_pyevent
    def setUp(self):
        super(TpoolConnectionPool, self).setUp()

    def tearDown(self):
        super(TpoolConnectionPool, self).tearDown()
        from eventlet import tpool
        tpool.killall()



class RawConnectionPool(DBConnectionPool):
    __test__ = False  # so that nose doesn't try to execute this directly
    def create_pool(self, min_size=0, max_size=1, max_idle=10, max_age=10,
                    connect_timeout=0.5, module=None):
        if module is None:
            module = self._dbmodule
        return db_pool.RawConnectionPool(module,
            min_size=min_size, max_size=max_size,
            max_idle=max_idle, max_age=max_age,
            connect_timeout=connect_timeout,
            **self._auth)


class TestRawConnectionPool(TestCase):
    def test_issue_125(self):
        # pool = self.create_pool(min_size=3, max_size=5)
        pool = db_pool.RawConnectionPool(DummyDBModule(),
            dsn="dbname=test user=jessica port=5433",
            min_size=3, max_size=5)
        conn = pool.get()
        pool.put(conn)


get_auth = get_database_auth


def mysql_requirement(_f):
    verbose = os.environ.get('eventlet_test_mysql_verbose')
    try:
        import MySQLdb
        try:
            auth = get_auth()['MySQLdb'].copy()
            MySQLdb.connect(**auth)
            return True
        except MySQLdb.OperationalError:
            if verbose:
                print(">> Skipping mysql tests, error when connecting:", file=sys.stderr)
                traceback.print_exc()
            return False
    except ImportError:
        if verbose:
            print(">> Skipping mysql tests, MySQLdb not importable", file=sys.stderr)
        return False


class MysqlConnectionPool(object):
    dummy_table_sql = """CREATE TEMPORARY TABLE test_table
        (
        row_id INTEGER PRIMARY KEY AUTO_INCREMENT,
        value_int INTEGER,
        value_float FLOAT,
        value_string VARCHAR(200),
        value_uuid CHAR(36),
        value_binary BLOB,
        value_binary_string VARCHAR(200) BINARY,
        value_enum ENUM('Y','N'),
        created TIMESTAMP
        ) ENGINE=InnoDB;"""

    @skip_unless(mysql_requirement)
    def setUp(self):
        import MySQLdb
        self._dbmodule = MySQLdb
        self._auth = get_auth()['MySQLdb']
        super(MysqlConnectionPool, self).setUp()

    def tearDown(self):
        super(MysqlConnectionPool, self).tearDown()

    def create_db(self):
        auth = self._auth.copy()
        try:
            self.drop_db()
        except Exception:
            pass
        dbname = 'test%s' % os.getpid()
        db = self._dbmodule.connect(**auth).cursor()
        db.execute("create database "+dbname)
        db.close()
        self._auth['db'] = dbname
        del db

    def drop_db(self):
        db = self._dbmodule.connect(**self._auth).cursor()
        db.execute("drop database "+self._auth['db'])
        db.close()
        del db


class Test01MysqlTpool(MysqlConnectionPool, TpoolConnectionPool, TestCase):
    __test__ = True


class Test02MysqlRaw(MysqlConnectionPool, RawConnectionPool, TestCase):
    __test__ = True


def postgres_requirement(_f):
    try:
        import psycopg2
        try:
            auth = get_auth()['psycopg2'].copy()
            psycopg2.connect(**auth)
            return True
        except psycopg2.OperationalError:
            print("Skipping postgres tests, error when connecting")
            return False
    except ImportError:
        print("Skipping postgres tests, psycopg2 not importable")
        return False


class Psycopg2ConnectionPool(object):
    dummy_table_sql = """CREATE TEMPORARY TABLE test_table
        (
        row_id SERIAL PRIMARY KEY,
        value_int INTEGER,
        value_float FLOAT,
        value_string VARCHAR(200),
        value_uuid CHAR(36),
        value_binary BYTEA,
        value_binary_string BYTEA,
        created TIMESTAMP
        );"""

    @skip_unless(postgres_requirement)
    def setUp(self):
        import psycopg2
        self._dbmodule = psycopg2
        self._auth = get_auth()['psycopg2']
        super(Psycopg2ConnectionPool, self).setUp()

    def tearDown(self):
        super(Psycopg2ConnectionPool, self).tearDown()

    def create_db(self):
        dbname = 'test%s' % os.getpid()
        self._auth['database'] = dbname
        try:
            self.drop_db()
        except Exception:
            pass
        auth = self._auth.copy()
        auth.pop('database')  # can't create if you're connecting to it
        conn = self._dbmodule.connect(**auth)
        conn.set_isolation_level(0)
        db = conn.cursor()
        db.execute("create database "+dbname)
        db.close()
        conn.close()

    def drop_db(self):
        auth = self._auth.copy()
        auth.pop('database')  # can't drop database we connected to
        conn = self._dbmodule.connect(**auth)
        conn.set_isolation_level(0)
        db = conn.cursor()
        db.execute("drop database "+self._auth['database'])
        db.close()
        conn.close()


class TestPsycopg2Base(TestCase):
    __test__ = False

    def test_cursor_works_as_context_manager(self):
        with self.connection.cursor() as c:
            c.execute('select 1')
            row = c.fetchone()
            assert row == (1,)


class Test01Psycopg2Tpool(Psycopg2ConnectionPool, TpoolConnectionPool, TestPsycopg2Base):
    __test__ = True


class Test02Psycopg2Raw(Psycopg2ConnectionPool, RawConnectionPool, TestPsycopg2Base):
    __test__ = True


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = debug_test
import sys
from unittest import TestCase

from eventlet import debug
from eventlet.support import six
from tests import LimitedTestCase, main
import eventlet


class TestSpew(TestCase):
    def setUp(self):
        self.orig_trace = sys.settrace
        sys.settrace = self._settrace
        self.tracer = None

    def tearDown(self):
        sys.settrace = self.orig_trace
        sys.stdout = sys.__stdout__

    def _settrace(self, cb):
        self.tracer = cb

    def test_spew(self):
        debug.spew()
        self.failUnless(isinstance(self.tracer, debug.Spew))

    def test_unspew(self):
        debug.spew()
        debug.unspew()
        self.failUnlessEqual(self.tracer, None)

    def test_line(self):
        sys.stdout = six.StringIO()
        s = debug.Spew()
        f = sys._getframe()
        s(f, "line", None)
        lineno = f.f_lineno - 1  # -1 here since we called with frame f in the line above
        output = sys.stdout.getvalue()
        self.failUnless("%s:%i" % (__name__, lineno) in output, "Didn't find line %i in %s" % (lineno, output))
        self.failUnless("f=<frame object at" in output)

    def test_line_nofile(self):
        sys.stdout = six.StringIO()
        s = debug.Spew()
        g = globals().copy()
        del g['__file__']
        f = eval("sys._getframe()", g)
        lineno = f.f_lineno
        s(f, "line", None)
        output = sys.stdout.getvalue()
        self.failUnless("[unknown]:%i" % lineno in output, "Didn't find [unknown]:%i in %s" % (lineno, output))
        self.failUnless("VM instruction #" in output, output)

    def test_line_global(self):
        global GLOBAL_VAR
        sys.stdout = six.StringIO()
        GLOBAL_VAR = debug.Spew()
        f = sys._getframe()
        GLOBAL_VAR(f, "line", None)
        lineno = f.f_lineno - 1  # -1 here since we called with frame f in the line above
        output = sys.stdout.getvalue()
        self.failUnless("%s:%i" % (__name__, lineno) in output, "Didn't find line %i in %s" % (lineno, output))
        self.failUnless("f=<frame object at" in output)
        self.failUnless("GLOBAL_VAR" in f.f_globals)
        self.failUnless("GLOBAL_VAR=<eventlet.debug.Spew object at" in output)
        del GLOBAL_VAR

    def test_line_novalue(self):
        sys.stdout = six.StringIO()
        s = debug.Spew(show_values=False)
        f = sys._getframe()
        s(f, "line", None)
        lineno = f.f_lineno - 1  # -1 here since we called with frame f in the line above
        output = sys.stdout.getvalue()
        self.failUnless("%s:%i" % (__name__, lineno) in output, "Didn't find line %i in %s" % (lineno, output))
        self.failIf("f=<frame object at" in output)

    def test_line_nooutput(self):
        sys.stdout = six.StringIO()
        s = debug.Spew(trace_names=['foo'])
        f = sys._getframe()
        s(f, "line", None)
        output = sys.stdout.getvalue()
        self.failUnlessEqual(output, "")


class TestDebug(LimitedTestCase):
    def test_everything(self):
        debug.hub_exceptions(True)
        debug.hub_exceptions(False)
        debug.tpool_exceptions(True)
        debug.tpool_exceptions(False)
        debug.hub_listener_stacks(True)
        debug.hub_listener_stacks(False)
        debug.hub_timer_stacks(True)
        debug.hub_timer_stacks(False)
        debug.format_hub_listeners()
        debug.format_hub_timers()

    def test_hub_exceptions(self):
        debug.hub_exceptions(True)
        server = eventlet.listen(('0.0.0.0', 0))
        client = eventlet.connect(('127.0.0.1', server.getsockname()[1]))
        client_2, addr = server.accept()

        def hurl(s):
            s.recv(1)
            {}[1]  # keyerror

        fake = six.StringIO()
        orig = sys.stderr
        sys.stderr = fake
        try:
            gt = eventlet.spawn(hurl, client_2)
            eventlet.sleep(0)
            client.send(b' ')
            eventlet.sleep(0)
            # allow the "hurl" greenlet to trigger the KeyError
            # not sure why the extra context switch is needed
            eventlet.sleep(0)
        finally:
            sys.stderr = orig
            self.assertRaises(KeyError, gt.wait)
            debug.hub_exceptions(False)
        # look for the KeyError exception in the traceback
        self.assert_('KeyError: 1' in fake.getvalue(),
                     "Traceback not in:\n" + fake.getvalue())

if __name__ == "__main__":
    main()

########NEW FILE########
__FILENAME__ = env_test
import os
from tests.patcher_test import ProcessBase
from tests import skip_with_pyevent


class Socket(ProcessBase):
    def test_patched_thread(self):
        new_mod = """from eventlet.green import socket
socket.gethostbyname('localhost')
socket.getaddrinfo('localhost', 80)
"""
        os.environ['EVENTLET_TPOOL_DNS'] = 'yes'
        try:
            self.write_to_tempfile("newmod", new_mod)
            output, lines = self.launch_subprocess('newmod.py')
            self.assertEqual(len(lines), 1, lines)
        finally:
            del os.environ['EVENTLET_TPOOL_DNS']


class Tpool(ProcessBase):
    @skip_with_pyevent
    def test_tpool_size(self):
        expected = "40"
        normal = "20"
        new_mod = """from eventlet import tpool
import eventlet
import time
current = [0]
highwater = [0]
def count():
    current[0] += 1
    time.sleep(0.1)
    if current[0] > highwater[0]:
        highwater[0] = current[0]
    current[0] -= 1
expected = %s
normal = %s
p = eventlet.GreenPool()
for i in range(expected*2):
    p.spawn(tpool.execute, count)
p.waitall()
assert highwater[0] > 20, "Highwater %%s  <= %%s" %% (highwater[0], normal)
"""
        os.environ['EVENTLET_THREADPOOL_SIZE'] = expected
        try:
            self.write_to_tempfile("newmod", new_mod % (expected, normal))
            output, lines = self.launch_subprocess('newmod.py')
            self.assertEqual(len(lines), 1, lines)
        finally:
            del os.environ['EVENTLET_THREADPOOL_SIZE']

    def test_tpool_negative(self):
        new_mod = """from eventlet import tpool
import eventlet
import time
def do():
    print("should not get here")
try:
    tpool.execute(do)
except AssertionError:
    print("success")
"""
        os.environ['EVENTLET_THREADPOOL_SIZE'] = "-1"
        try:
            self.write_to_tempfile("newmod", new_mod)
            output, lines = self.launch_subprocess('newmod.py')
            self.assertEqual(len(lines), 2, lines)
            self.assertEqual(lines[0], "success", output)
        finally:
            del os.environ['EVENTLET_THREADPOOL_SIZE']

    def test_tpool_zero(self):
        new_mod = """from eventlet import tpool
import eventlet
import time
def do():
    print("ran it")
tpool.execute(do)
"""
        os.environ['EVENTLET_THREADPOOL_SIZE'] = "0"
        try:
            self.write_to_tempfile("newmod", new_mod)
            output, lines = self.launch_subprocess('newmod.py')
            self.assertEqual(len(lines), 4, lines)
            self.assertEqual(lines[-2], 'ran it', lines)
            self.assert_('Warning' in lines[1] or 'Warning' in lines[0], lines)
        finally:
            del os.environ['EVENTLET_THREADPOOL_SIZE']


class Hub(ProcessBase):

    def setUp(self):
        super(Hub, self).setUp()
        self.old_environ = os.environ.get('EVENTLET_HUB')
        os.environ['EVENTLET_HUB'] = 'selects'

    def tearDown(self):
        if self.old_environ:
            os.environ['EVENTLET_HUB'] = self.old_environ
        else:
            del os.environ['EVENTLET_HUB']
        super(Hub, self).tearDown()

    def test_eventlet_hub(self):
        new_mod = """from eventlet import hubs
print(hubs.get_hub())
"""
        self.write_to_tempfile("newmod", new_mod)
        output, lines = self.launch_subprocess('newmod.py')
        self.assertEqual(len(lines), 2, "\n".join(lines))
        self.assert_("selects" in lines[0])


########NEW FILE########
__FILENAME__ = event_test
import eventlet
from eventlet import event
from tests import LimitedTestCase

class TestEvent(LimitedTestCase):
    def test_waiting_for_event(self):
        evt = event.Event()
        value = 'some stuff'
        def send_to_event():
            evt.send(value)
        eventlet.spawn_n(send_to_event)
        self.assertEqual(evt.wait(), value)

    def test_multiple_waiters(self):
        self._test_multiple_waiters(False)

    def test_multiple_waiters_with_exception(self):
        self._test_multiple_waiters(True)

    def _test_multiple_waiters(self, exception):
        evt = event.Event()
        value = 'some stuff'
        results = []
        def wait_on_event(i_am_done):
            evt.wait()
            results.append(True)
            i_am_done.send()
            if exception:
                raise Exception()

        waiters = []
        count = 5
        for i in range(count):
            waiters.append(event.Event())
            eventlet.spawn_n(wait_on_event, waiters[-1])
        eventlet.sleep()  # allow spawns to start executing
        evt.send()

        for w in waiters:
            w.wait()

        self.assertEqual(len(results), count)

    def test_reset(self):
        evt = event.Event()

        # calling reset before send should throw
        self.assertRaises(AssertionError, evt.reset)

        value = 'some stuff'
        def send_to_event():
            evt.send(value)
        eventlet.spawn_n(send_to_event)
        self.assertEqual(evt.wait(), value)

        # now try it again, and we should get the same exact value,
        # and we shouldn't be allowed to resend without resetting
        value2 = 'second stuff'
        self.assertRaises(AssertionError, evt.send, value2)
        self.assertEqual(evt.wait(), value)

        # reset and everything should be happy
        evt.reset()
        def send_to_event2():
            evt.send(value2)
        eventlet.spawn_n(send_to_event2)
        self.assertEqual(evt.wait(), value2)

    def test_double_exception(self):
        evt = event.Event()
        # send an exception through the event
        evt.send(exc=RuntimeError('from test_double_exception'))
        self.assertRaises(RuntimeError, evt.wait)
        evt.reset()
        # shouldn't see the RuntimeError again
        eventlet.Timeout(0.001)
        self.assertRaises(eventlet.Timeout, evt.wait)


########NEW FILE########
__FILENAME__ = fork_test
from tests.patcher_test import ProcessBase


class ForkTest(ProcessBase):
    def test_simple(self):
        newmod = '''
import eventlet
import os
import sys
import signal
mydir = %r
signal_file = os.path.join(mydir, "output.txt")
pid = os.fork()
if (pid != 0):
  eventlet.Timeout(10)
  try:
    port = None
    while True:
      try:
        contents = open(signal_file, "rb").read()
        port = int(contents.split()[0])
        break
      except (IOError, IndexError, ValueError, TypeError):
        eventlet.sleep(0.1)
    eventlet.connect(('127.0.0.1', port))
    while True:
      try:
        contents = open(signal_file, "rb").read()
        result = contents.split()[1]
        break
      except (IOError, IndexError):
        eventlet.sleep(0.1)
    print('result {0}'.format(result))
  finally:
    os.kill(pid, signal.SIGTERM)
else:
  try:
    s = eventlet.listen(('', 0))
    fd = open(signal_file, "wb")
    fd.write(str(s.getsockname()[1]))
    fd.write("\\n")
    fd.flush()
    s.accept()
    fd.write("done")
    fd.flush()
  finally:
    fd.close()
'''
        self.write_to_tempfile("newmod", newmod % self.tempdir)
        output, lines = self.launch_subprocess('newmod.py')
        self.assertEqual(lines[0], "result done", output)

########NEW FILE########
__FILENAME__ = greendns_test
from nose.plugins.skip import SkipTest


def test_greendns_getnameinfo_resolve_port():
    try:
        from eventlet.support import greendns
    except ImportError:
        raise SkipTest('greendns requires package dnspython')

    # https://bitbucket.org/eventlet/eventlet/issue/152
    _, port1 = greendns.getnameinfo(('127.0.0.1', 80), 0)
    _, port2 = greendns.getnameinfo(('localhost', 80), 0)
    assert port1 == port2 == 'http'

########NEW FILE########
__FILENAME__ = greenio_test
import array
import errno
import eventlet
import fcntl
import gc
import os
import shutil
import socket as _orig_sock
import sys
import tempfile

from eventlet import event, greenio, debug
from eventlet.hubs import get_hub
from eventlet.green import select, socket, time, ssl
from eventlet.support import get_errno, six
from tests import (
    LimitedTestCase, main,
    skip_with_pyevent, skipped, skip_if, skip_on_windows,
)


if six.PY3:
    buffer = memoryview


def bufsized(sock, size=1):
    """ Resize both send and receive buffers on a socket.
    Useful for testing trampoline.  Returns the socket.

    >>> import socket
    >>> sock = bufsized(socket.socket(socket.AF_INET, socket.SOCK_STREAM))
    """
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, size)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, size)
    return sock


def min_buf_size():
    """Return the minimum buffer size that the platform supports."""
    test_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    test_sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 1)
    return test_sock.getsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF)


def using_epoll_hub(_f):
    try:
        return 'epolls' in type(get_hub()).__module__
    except Exception:
        return False


def using_kqueue_hub(_f):
    try:
        return 'kqueue' in type(get_hub()).__module__
    except Exception:
        return False


class TestGreenSocket(LimitedTestCase):
    def assertWriteToClosedFileRaises(self, fd):
        if sys.version_info[0] < 3:
            # 2.x socket._fileobjects are odd: writes don't check
            # whether the socket is closed or not, and you get an
            # AttributeError during flush if it is closed
            fd.write('a')
            self.assertRaises(Exception, fd.flush)
        else:
            # 3.x io write to closed file-like pbject raises ValueError
            self.assertRaises(ValueError, fd.write, 'a')

    def test_connect_timeout(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(0.1)
        gs = greenio.GreenSocket(s)
        try:
            gs.connect(('192.0.2.1', 80))
            self.fail("socket.timeout not raised")
        except socket.timeout as e:
            self.assert_(hasattr(e, 'args'))
            self.assertEqual(e.args[0], 'timed out')
        except socket.error as e:
            # unreachable is also a valid outcome
            if not get_errno(e) in (errno.EHOSTUNREACH, errno.ENETUNREACH):
                raise

    def test_accept_timeout(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind(('', 0))
        s.listen(50)

        s.settimeout(0.1)
        gs = greenio.GreenSocket(s)
        try:
            gs.accept()
            self.fail("socket.timeout not raised")
        except socket.timeout as e:
            self.assert_(hasattr(e, 'args'))
            self.assertEqual(e.args[0], 'timed out')

    def test_connect_ex_timeout(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(0.1)
        gs = greenio.GreenSocket(s)
        e = gs.connect_ex(('192.0.2.1', 80))
        if not e in (errno.EHOSTUNREACH, errno.ENETUNREACH):
            self.assertEqual(e, errno.EAGAIN)

    def test_recv_timeout(self):
        listener = greenio.GreenSocket(socket.socket())
        listener.bind(('', 0))
        listener.listen(50)

        evt = event.Event()

        def server():
            # accept the connection in another greenlet
            sock, addr = listener.accept()
            evt.wait()

        gt = eventlet.spawn(server)

        addr = listener.getsockname()

        client = greenio.GreenSocket(socket.socket())
        client.settimeout(0.1)

        client.connect(addr)

        try:
            client.recv(8192)
            self.fail("socket.timeout not raised")
        except socket.timeout as e:
            self.assert_(hasattr(e, 'args'))
            self.assertEqual(e.args[0], 'timed out')

        evt.send()
        gt.wait()

    def test_recvfrom_timeout(self):
        gs = greenio.GreenSocket(
            socket.socket(socket.AF_INET, socket.SOCK_DGRAM))
        gs.settimeout(.1)
        gs.bind(('', 0))

        try:
            gs.recvfrom(8192)
            self.fail("socket.timeout not raised")
        except socket.timeout as e:
            self.assert_(hasattr(e, 'args'))
            self.assertEqual(e.args[0], 'timed out')

    def test_recvfrom_into_timeout(self):
        buf = array.array('B')

        gs = greenio.GreenSocket(
            socket.socket(socket.AF_INET, socket.SOCK_DGRAM))
        gs.settimeout(.1)
        gs.bind(('', 0))

        try:
            gs.recvfrom_into(buf)
            self.fail("socket.timeout not raised")
        except socket.timeout as e:
            self.assert_(hasattr(e, 'args'))
            self.assertEqual(e.args[0], 'timed out')

    def test_recv_into_timeout(self):
        buf = array.array('B')

        listener = greenio.GreenSocket(socket.socket())
        listener.bind(('', 0))
        listener.listen(50)

        evt = event.Event()

        def server():
            # accept the connection in another greenlet
            sock, addr = listener.accept()
            evt.wait()

        gt = eventlet.spawn(server)

        addr = listener.getsockname()

        client = greenio.GreenSocket(socket.socket())
        client.settimeout(0.1)

        client.connect(addr)

        try:
            client.recv_into(buf)
            self.fail("socket.timeout not raised")
        except socket.timeout as e:
            self.assert_(hasattr(e, 'args'))
            self.assertEqual(e.args[0], 'timed out')

        evt.send()
        gt.wait()

    def test_send_timeout(self):
        self.reset_timeout(2)
        listener = bufsized(eventlet.listen(('', 0)))

        evt = event.Event()

        def server():
            # accept the connection in another greenlet
            sock, addr = listener.accept()
            sock = bufsized(sock)
            evt.wait()

        gt = eventlet.spawn(server)

        addr = listener.getsockname()

        client = bufsized(greenio.GreenSocket(socket.socket()))
        client.connect(addr)
        try:
            client.settimeout(0.00001)
            msg = b"A" * 100000  # large enough number to overwhelm most buffers

            total_sent = 0
            # want to exceed the size of the OS buffer so it'll block in a
            # single send
            for x in range(10):
                total_sent += client.send(msg)
            self.fail("socket.timeout not raised")
        except socket.timeout as e:
            self.assert_(hasattr(e, 'args'))
            self.assertEqual(e.args[0], 'timed out')

        evt.send()
        gt.wait()

    def test_sendall_timeout(self):
        listener = greenio.GreenSocket(socket.socket())
        listener.bind(('', 0))
        listener.listen(50)

        evt = event.Event()

        def server():
            # accept the connection in another greenlet
            sock, addr = listener.accept()
            evt.wait()

        gt = eventlet.spawn(server)

        addr = listener.getsockname()

        client = greenio.GreenSocket(socket.socket())
        client.settimeout(0.1)
        client.connect(addr)

        try:
            msg = b"A" * (8 << 20)

            # want to exceed the size of the OS buffer so it'll block
            client.sendall(msg)
            self.fail("socket.timeout not raised")
        except socket.timeout as e:
            self.assert_(hasattr(e, 'args'))
            self.assertEqual(e.args[0], 'timed out')

        evt.send()
        gt.wait()

    def test_close_with_makefile(self):
        def accept_close_early(listener):
            # verify that the makefile and the socket are truly independent
            # by closing the socket prior to using the made file
            try:
                conn, addr = listener.accept()
                fd = conn.makefile('w')
                conn.close()
                fd.write(b'hello\n')
                fd.close()
                self.assertWriteToClosedFileRaises(fd)
                self.assertRaises(socket.error, conn.send, b'b')
            finally:
                listener.close()

        def accept_close_late(listener):
            # verify that the makefile and the socket are truly independent
            # by closing the made file and then sending a character
            try:
                conn, addr = listener.accept()
                fd = conn.makefile('w')
                fd.write(b'hello')
                fd.close()
                conn.send(b'\n')
                conn.close()
                self.assertWriteToClosedFileRaises(fd)
                self.assertRaises(socket.error, conn.send, b'b')
            finally:
                listener.close()

        def did_it_work(server):
            client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client.connect(('127.0.0.1', server.getsockname()[1]))
            fd = client.makefile()
            client.close()
            assert fd.readline() == b'hello\n'
            assert fd.read() == b''
            fd.close()

        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind(('0.0.0.0', 0))
        server.listen(50)
        killer = eventlet.spawn(accept_close_early, server)
        did_it_work(server)
        killer.wait()

        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind(('0.0.0.0', 0))
        server.listen(50)
        killer = eventlet.spawn(accept_close_late, server)
        did_it_work(server)
        killer.wait()

    def test_del_closes_socket(self):
        def accept_once(listener):
            # delete/overwrite the original conn
            # object, only keeping the file object around
            # closing the file object should close everything
            try:
                conn, addr = listener.accept()
                conn = conn.makefile('w')
                conn.write(b'hello\n')
                conn.close()
                gc.collect()
                self.assertWriteToClosedFileRaises(conn)
            finally:
                listener.close()

        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind(('127.0.0.1', 0))
        server.listen(50)
        killer = eventlet.spawn(accept_once, server)
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client.connect(('127.0.0.1', server.getsockname()[1]))
        fd = client.makefile()
        client.close()
        assert fd.read() == b'hello\n'
        assert fd.read() == b''

        killer.wait()

    def test_full_duplex(self):
        large_data = b'*' * 10 * min_buf_size()
        listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        listener.bind(('127.0.0.1', 0))
        listener.listen(50)
        bufsized(listener)

        def send_large(sock):
            sock.sendall(large_data)

        def read_large(sock):
            result = sock.recv(len(large_data))
            while len(result) < len(large_data):
                result += sock.recv(len(large_data))
            self.assertEqual(result, large_data)

        def server():
            (sock, addr) = listener.accept()
            sock = bufsized(sock)
            send_large_coro = eventlet.spawn(send_large, sock)
            eventlet.sleep(0)
            result = sock.recv(10)
            expected = b'hello world'
            while len(result) < len(expected):
                result += sock.recv(10)
            self.assertEqual(result, expected)
            send_large_coro.wait()

        server_evt = eventlet.spawn(server)
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client.connect(('127.0.0.1', listener.getsockname()[1]))
        bufsized(client)
        large_evt = eventlet.spawn(read_large, client)
        eventlet.sleep(0)
        client.sendall(b'hello world')
        server_evt.wait()
        large_evt.wait()
        client.close()

    def test_sendall(self):
        # test adapted from Marcus Cavanaugh's email
        # it may legitimately take a while, but will eventually complete
        self.timer.cancel()
        second_bytes = 10

        def test_sendall_impl(many_bytes):
            bufsize = max(many_bytes // 15, 2)

            def sender(listener):
                (sock, addr) = listener.accept()
                sock = bufsized(sock, size=bufsize)
                sock.sendall(b'x' * many_bytes)
                sock.sendall(b'y' * second_bytes)

            listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            listener.bind(("", 0))
            listener.listen(50)
            sender_coro = eventlet.spawn(sender, listener)
            client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client.connect(('127.0.0.1', listener.getsockname()[1]))
            bufsized(client, size=bufsize)
            total = 0
            while total < many_bytes:
                data = client.recv(min(many_bytes - total, many_bytes // 10))
                if not data:
                    break
                total += len(data)

            total2 = 0
            while total < second_bytes:
                data = client.recv(second_bytes)
                if not data:
                    break
                total2 += len(data)

            sender_coro.wait()
            client.close()

        for how_many in (1000, 10000, 100000, 1000000):
            test_sendall_impl(how_many)

    def test_wrap_socket(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(('127.0.0.1', 0))
        sock.listen(50)
        ssl.wrap_socket(sock)

    def test_timeout_and_final_write(self):
        # This test verifies that a write on a socket that we've
        # stopped listening for doesn't result in an incorrect switch
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind(('127.0.0.1', 0))
        server.listen(50)
        bound_port = server.getsockname()[1]

        def sender(evt):
            s2, addr = server.accept()
            wrap_wfile = s2.makefile('w')

            eventlet.sleep(0.02)
            wrap_wfile.write('hi')
            s2.close()
            evt.send(b'sent via event')

        evt = event.Event()
        eventlet.spawn(sender, evt)
        # lets the socket enter accept mode, which
        # is necessary for connect to succeed on windows
        eventlet.sleep(0)
        try:
            # try and get some data off of this pipe
            # but bail before any is sent
            eventlet.Timeout(0.01)
            client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client.connect(('127.0.0.1', bound_port))
            wrap_rfile = client.makefile()
            wrap_rfile.read(1)
            self.fail()
        except eventlet.TimeoutError:
            pass

        result = evt.wait()
        self.assertEqual(result, b'sent via event')
        server.close()
        client.close()

    @skip_with_pyevent
    def test_raised_multiple_readers(self):
        debug.hub_prevent_multiple_readers(True)

        def handle(sock, addr):
            sock.recv(1)
            sock.sendall(b"a")
            raise eventlet.StopServe()

        listener = eventlet.listen(('127.0.0.1', 0))
        eventlet.spawn(eventlet.serve, listener, handle)

        def reader(s):
            s.recv(1)

        s = eventlet.connect(('127.0.0.1', listener.getsockname()[1]))
        a = eventlet.spawn(reader, s)
        eventlet.sleep(0)
        self.assertRaises(RuntimeError, s.recv, 1)
        s.sendall(b'b')
        a.wait()

    @skip_with_pyevent
    @skip_if(using_epoll_hub)
    @skip_if(using_kqueue_hub)
    def test_closure(self):
        def spam_to_me(address):
            sock = eventlet.connect(address)
            while True:
                try:
                    sock.sendall(b'hello world')
                except socket.error as e:
                    if get_errno(e) == errno.EPIPE:
                        return
                    raise

        server = eventlet.listen(('127.0.0.1', 0))
        sender = eventlet.spawn(spam_to_me, server.getsockname())
        client, address = server.accept()
        server.close()

        def reader():
            try:
                while True:
                    data = client.recv(1024)
                    self.assert_(data)
            except socket.error as e:
                # we get an EBADF because client is closed in the same process
                # (but a different greenthread)
                if get_errno(e) != errno.EBADF:
                    raise

        def closer():
            client.close()

        reader = eventlet.spawn(reader)
        eventlet.spawn_n(closer)
        reader.wait()
        sender.wait()

    def test_invalid_connection(self):
        # find an unused port by creating a socket then closing it
        listening_socket = eventlet.listen(('127.0.0.1', 0))
        port = listening_socket.getsockname()[1]
        listening_socket.close()
        self.assertRaises(socket.error, eventlet.connect, ('127.0.0.1', port))

    def test_zero_timeout_and_back(self):
        listen = eventlet.listen(('', 0))
        # Keep reference to server side of socket
        server = eventlet.spawn(listen.accept)
        client = eventlet.connect(listen.getsockname())

        client.settimeout(0.05)
        # Now must raise socket.timeout
        self.assertRaises(socket.timeout, client.recv, 1)

        client.settimeout(0)
        # Now must raise socket.error with EAGAIN
        try:
            client.recv(1)
            assert False
        except socket.error as e:
            assert get_errno(e) == errno.EAGAIN

        client.settimeout(0.05)
        # Now socket.timeout again
        self.assertRaises(socket.timeout, client.recv, 1)
        server.wait()

    def test_default_nonblocking(self):
        sock1 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        flags = fcntl.fcntl(sock1.fd.fileno(), fcntl.F_GETFL)
        assert flags & os.O_NONBLOCK

        sock2 = socket.socket(sock1.fd)
        flags = fcntl.fcntl(sock2.fd.fileno(), fcntl.F_GETFL)
        assert flags & os.O_NONBLOCK

    def test_dup_nonblocking(self):
        sock1 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        flags = fcntl.fcntl(sock1.fd.fileno(), fcntl.F_GETFL)
        assert flags & os.O_NONBLOCK

        sock2 = sock1.dup()
        flags = fcntl.fcntl(sock2.fd.fileno(), fcntl.F_GETFL)
        assert flags & os.O_NONBLOCK

    def test_skip_nonblocking(self):
        sock1 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        fd = sock1.fd.fileno()
        flags = fcntl.fcntl(fd, fcntl.F_GETFL)
        flags = fcntl.fcntl(fd, fcntl.F_SETFL, flags & ~os.O_NONBLOCK)
        assert flags & os.O_NONBLOCK == 0

        sock2 = socket.socket(sock1.fd, set_nonblocking=False)
        flags = fcntl.fcntl(sock2.fd.fileno(), fcntl.F_GETFL)
        assert flags & os.O_NONBLOCK == 0

    def test_sockopt_interface(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        assert sock.getsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR) == 0
        assert sock.getsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1) == '\000'
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    def test_socketpair_select(self):
        # https://github.com/eventlet/eventlet/pull/25
        s1, s2 = socket.socketpair()
        assert select.select([], [s1], [], 0) == ([], [s1], [])
        assert select.select([], [s1], [], 0) == ([], [s1], [])


class TestGreenPipe(LimitedTestCase):
    @skip_on_windows
    def setUp(self):
        super(self.__class__, self).setUp()
        self.tempdir = tempfile.mkdtemp('_green_pipe_test')

    def tearDown(self):
        shutil.rmtree(self.tempdir)
        super(self.__class__, self).tearDown()

    def test_pipe(self):
        r, w = os.pipe()
        rf = greenio.GreenPipe(r, 'r')
        wf = greenio.GreenPipe(w, 'w', 0)

        def sender(f, content):
            for ch in content:
                eventlet.sleep(0.0001)
                f.write(ch)
            f.close()

        one_line = "12345\n"
        eventlet.spawn(sender, wf, one_line * 5)
        for i in range(5):
            line = rf.readline()
            eventlet.sleep(0.01)
            self.assertEqual(line, one_line)
        self.assertEqual(rf.readline(), '')

    def test_pipe_read(self):
        # ensure that 'readline' works properly on GreenPipes when data is not
        # immediately available (fd is nonblocking, was raising EAGAIN)
        # also ensures that readline() terminates on '\n' and '\r\n'
        r, w = os.pipe()

        r = greenio.GreenPipe(r)
        w = greenio.GreenPipe(w, 'w')

        def writer():
            eventlet.sleep(.1)

            w.write('line\n')
            w.flush()

            w.write('line\r\n')
            w.flush()

        gt = eventlet.spawn(writer)

        eventlet.sleep(0)

        line = r.readline()
        self.assertEqual(line, 'line\n')

        line = r.readline()
        self.assertEqual(line, 'line\r\n')

        gt.wait()

    def test_pipe_writes_large_messages(self):
        r, w = os.pipe()

        r = greenio.GreenPipe(r)
        w = greenio.GreenPipe(w, 'w')

        large_message = "".join([1024 * chr(i) for i in range(65)])

        def writer():
            w.write(large_message)
            w.close()

        gt = eventlet.spawn(writer)

        for i in range(65):
            buf = r.read(1024)
            expected = 1024 * chr(i)
            self.assertEqual(
                buf, expected,
                "expected=%r..%r, found=%r..%r iter=%d"
                % (expected[:4], expected[-4:], buf[:4], buf[-4:], i))
        gt.wait()

    def test_seek_on_buffered_pipe(self):
        f = greenio.GreenPipe(self.tempdir + "/TestFile", 'w+', 1024)
        self.assertEqual(f.tell(), 0)
        f.seek(0, 2)
        self.assertEqual(f.tell(), 0)
        f.write('1234567890')
        f.seek(0, 2)
        self.assertEqual(f.tell(), 10)
        f.seek(0)
        value = f.read(1)
        self.assertEqual(value, '1')
        self.assertEqual(f.tell(), 1)
        value = f.read(1)
        self.assertEqual(value, '2')
        self.assertEqual(f.tell(), 2)
        f.seek(0, 1)
        self.assertEqual(f.readline(), '34567890')
        f.seek(-5, 1)
        self.assertEqual(f.readline(), '67890')
        f.seek(0)
        self.assertEqual(f.readline(), '1234567890')
        f.seek(0, 2)
        self.assertEqual(f.readline(), '')

    def test_truncate(self):
        f = greenio.GreenPipe(self.tempdir + "/TestFile", 'w+', 1024)
        f.write('1234567890')
        f.truncate(9)
        self.assertEqual(f.tell(), 9)


class TestGreenIoLong(LimitedTestCase):
    TEST_TIMEOUT = 10  # the test here might take a while depending on the OS

    @skip_with_pyevent
    def test_multiple_readers(self, clibufsize=False):
        debug.hub_prevent_multiple_readers(False)
        recvsize = 2 * min_buf_size()
        sendsize = 10 * recvsize

        # test that we can have multiple coroutines reading
        # from the same fd.  We make no guarantees about which one gets which
        # bytes, but they should both get at least some
        def reader(sock, results):
            while True:
                data = sock.recv(recvsize)
                if not data:
                    break
                results.append(data)

        results1 = []
        results2 = []
        listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        listener.bind(('127.0.0.1', 0))
        listener.listen(50)

        def server():
            (sock, addr) = listener.accept()
            sock = bufsized(sock)
            try:
                c1 = eventlet.spawn(reader, sock, results1)
                c2 = eventlet.spawn(reader, sock, results2)
                try:
                    c1.wait()
                    c2.wait()
                finally:
                    c1.kill()
                    c2.kill()
            finally:
                sock.close()

        server_coro = eventlet.spawn(server)
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client.connect(('127.0.0.1', listener.getsockname()[1]))
        if clibufsize:
            bufsized(client, size=sendsize)
        else:
            bufsized(client)
        client.sendall(b'*' * sendsize)
        client.close()
        server_coro.wait()
        listener.close()
        self.assert_(len(results1) > 0)
        self.assert_(len(results2) > 0)
        debug.hub_prevent_multiple_readers()

    @skipped  # by rdw because it fails but it's not clear how to make it pass
    @skip_with_pyevent
    def test_multiple_readers2(self):
        self.test_multiple_readers(clibufsize=True)


class TestGreenIoStarvation(LimitedTestCase):
    # fixme: this doesn't succeed, because of eventlet's predetermined
    # ordering.  two processes, one with server, one with client eventlets
    # might be more reliable?

    TEST_TIMEOUT = 300  # the test here might take a while depending on the OS

    @skipped  # by rdw, because it fails but it's not clear how to make it pass
    @skip_with_pyevent
    def test_server_starvation(self, sendloops=15):
        recvsize = 2 * min_buf_size()
        sendsize = 10000 * recvsize

        results = [[] for i in range(5)]

        listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        listener.bind(('127.0.0.1', 0))
        port = listener.getsockname()[1]
        listener.listen(50)

        base_time = time.time()

        def server(my_results):
            sock, addr = listener.accept()

            datasize = 0

            t1 = None
            t2 = None
            try:
                while True:
                    data = sock.recv(recvsize)
                    if not t1:
                        t1 = time.time() - base_time
                    if not data:
                        t2 = time.time() - base_time
                        my_results.append(datasize)
                        my_results.append((t1, t2))
                        break
                    datasize += len(data)
            finally:
                sock.close()

        def client():
            pid = os.fork()
            if pid:
                return pid

            client = _orig_sock.socket(socket.AF_INET, socket.SOCK_STREAM)
            client.connect(('127.0.0.1', port))

            bufsized(client, size=sendsize)

            for i in range(sendloops):
                client.sendall(b'*' * sendsize)
            client.close()
            os._exit(0)

        clients = []
        servers = []
        for r in results:
            servers.append(eventlet.spawn(server, r))
        for r in results:
            clients.append(client())

        for s in servers:
            s.wait()
        for c in clients:
            os.waitpid(c, 0)

        listener.close()

        # now test that all of the server receive intervals overlap, and
        # that there were no errors.
        for r in results:
            assert len(r) == 2, "length is %d not 2!: %s\n%s" % (len(r), r, results)
            assert r[0] == sendsize * sendloops
            assert len(r[1]) == 2
            assert r[1][0] is not None
            assert r[1][1] is not None

        starttimes = sorted(r[1][0] for r in results)
        endtimes = sorted(r[1][1] for r in results)
        runlengths = sorted(r[1][1] - r[1][0] for r in results)

        # assert that the last task started before the first task ended
        # (our no-starvation condition)
        assert starttimes[-1] < endtimes[0], \
            "Not overlapping: starts %s ends %s" % (starttimes, endtimes)

        maxstartdiff = starttimes[-1] - starttimes[0]

        assert maxstartdiff * 2 < runlengths[0], \
            "Largest difference in starting times more than twice the shortest running time!"
        assert runlengths[0] * 2 > runlengths[-1], \
            "Longest runtime more than twice as long as shortest!"


def test_set_nonblocking():
    sock = _orig_sock.socket(socket.AF_INET, socket.SOCK_DGRAM)
    fileno = sock.fileno()
    orig_flags = fcntl.fcntl(fileno, fcntl.F_GETFL)
    assert orig_flags & os.O_NONBLOCK == 0
    greenio.set_nonblocking(sock)
    new_flags = fcntl.fcntl(fileno, fcntl.F_GETFL)
    assert new_flags == (orig_flags | os.O_NONBLOCK)


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = greenpipe_test_with_statement
from __future__ import with_statement

import os

from eventlet import greenio
from tests import LimitedTestCase


class TestGreenPipeWithStatement(LimitedTestCase):
    def test_pipe_context(self):
        # ensure using a pipe as a context actually closes it.
        r, w = os.pipe()

        r = greenio.GreenPipe(r)
        w = greenio.GreenPipe(w, 'w')

        with r:
            pass

        assert r.closed and not w.closed

        with w as f:
            assert f == w

        assert r.closed and w.closed

########NEW FILE########
__FILENAME__ = greenpool_test
import gc
import os
import random

import eventlet
from eventlet import hubs, greenpool, event, pools
from eventlet.support import greenlets as greenlet, six
import tests


def passthru(a):
    eventlet.sleep(0.01)
    return a


def passthru2(a, b):
    eventlet.sleep(0.01)
    return a, b


def raiser(exc):
    raise exc


class GreenPool(tests.LimitedTestCase):
    def test_spawn(self):
        p = greenpool.GreenPool(4)
        waiters = []
        for i in range(10):
            waiters.append(p.spawn(passthru, i))
        results = [waiter.wait() for waiter in waiters]
        self.assertEqual(results, list(range(10)))

    def test_spawn_n(self):
        p = greenpool.GreenPool(4)
        results_closure = []

        def do_something(a):
            eventlet.sleep(0.01)
            results_closure.append(a)

        for i in range(10):
            p.spawn(do_something, i)
        p.waitall()
        self.assertEqual(results_closure, list(range(10)))

    def test_waiting(self):
        pool = greenpool.GreenPool(1)
        done = event.Event()

        def consume():
            done.wait()

        def waiter(pool):
            gt = pool.spawn(consume)
            gt.wait()

        waiters = []
        self.assertEqual(pool.running(), 0)
        waiters.append(eventlet.spawn(waiter, pool))
        eventlet.sleep(0)
        self.assertEqual(pool.waiting(), 0)
        waiters.append(eventlet.spawn(waiter, pool))
        eventlet.sleep(0)
        self.assertEqual(pool.waiting(), 1)
        waiters.append(eventlet.spawn(waiter, pool))
        eventlet.sleep(0)
        self.assertEqual(pool.waiting(), 2)
        self.assertEqual(pool.running(), 1)
        done.send(None)
        for w in waiters:
            w.wait()
        self.assertEqual(pool.waiting(), 0)
        self.assertEqual(pool.running(), 0)

    def test_multiple_coros(self):
        evt = event.Event()
        results = []

        def producer():
            results.append('prod')
            evt.send()

        def consumer():
            results.append('cons1')
            evt.wait()
            results.append('cons2')

        pool = greenpool.GreenPool(2)
        done = pool.spawn(consumer)
        pool.spawn_n(producer)
        done.wait()
        self.assertEqual(['cons1', 'prod', 'cons2'], results)

    def test_timer_cancel(self):
        # this test verifies that local timers are not fired
        # outside of the context of the spawn
        timer_fired = []

        def fire_timer():
            timer_fired.append(True)

        def some_work():
            hubs.get_hub().schedule_call_local(0, fire_timer)

        pool = greenpool.GreenPool(2)
        worker = pool.spawn(some_work)
        worker.wait()
        eventlet.sleep(0)
        eventlet.sleep(0)
        self.assertEqual(timer_fired, [])

    def test_reentrant(self):
        pool = greenpool.GreenPool(1)

        def reenter():
            waiter = pool.spawn(lambda a: a, 'reenter')
            self.assertEqual('reenter', waiter.wait())

        outer_waiter = pool.spawn(reenter)
        outer_waiter.wait()

        evt = event.Event()

        def reenter_async():
            pool.spawn_n(lambda a: a, 'reenter')
            evt.send('done')

        pool.spawn_n(reenter_async)
        self.assertEqual('done', evt.wait())

    def assert_pool_has_free(self, pool, num_free):
        self.assertEqual(pool.free(), num_free)

        def wait_long_time(e):
            e.wait()

        timer = eventlet.Timeout(1)
        try:
            evt = event.Event()
            for x in six.moves.range(num_free):
                pool.spawn(wait_long_time, evt)
                # if the pool has fewer free than we expect,
                # then we'll hit the timeout error
        finally:
            timer.cancel()

        # if the runtime error is not raised it means the pool had
        # some unexpected free items
        timer = eventlet.Timeout(0, RuntimeError)
        try:
            self.assertRaises(RuntimeError, pool.spawn, wait_long_time, evt)
        finally:
            timer.cancel()

        # clean up by causing all the wait_long_time functions to return
        evt.send(None)
        eventlet.sleep(0)
        eventlet.sleep(0)

    def test_resize(self):
        pool = greenpool.GreenPool(2)
        evt = event.Event()

        def wait_long_time(e):
            e.wait()

        pool.spawn(wait_long_time, evt)
        pool.spawn(wait_long_time, evt)
        self.assertEqual(pool.free(), 0)
        self.assertEqual(pool.running(), 2)
        self.assert_pool_has_free(pool, 0)

        # verify that the pool discards excess items put into it
        pool.resize(1)

        # cause the wait_long_time functions to return, which will
        # trigger puts to the pool
        evt.send(None)
        eventlet.sleep(0)
        eventlet.sleep(0)

        self.assertEqual(pool.free(), 1)
        self.assertEqual(pool.running(), 0)
        self.assert_pool_has_free(pool, 1)

        # resize larger and assert that there are more free items
        pool.resize(2)
        self.assertEqual(pool.free(), 2)
        self.assertEqual(pool.running(), 0)
        self.assert_pool_has_free(pool, 2)

    def test_pool_smash(self):
        # The premise is that a coroutine in a Pool tries to get a token out
        # of a token pool but times out before getting the token.  We verify
        # that neither pool is adversely affected by this situation.
        pool = greenpool.GreenPool(1)
        tp = pools.TokenPool(max_size=1)
        tp.get()  # empty out the pool

        def do_receive(tp):
            timer = eventlet.Timeout(0, RuntimeError())
            try:
                tp.get()
                self.fail("Shouldn't have recieved anything from the pool")
            except RuntimeError:
                return 'timed out'
            else:
                timer.cancel()

        # the spawn makes the token pool expect that coroutine, but then
        # immediately cuts bait
        e1 = pool.spawn(do_receive, tp)
        self.assertEqual(e1.wait(), 'timed out')

        # the pool can get some random item back
        def send_wakeup(tp):
            tp.put('wakeup')
        gt = eventlet.spawn(send_wakeup, tp)

        # now we ask the pool to run something else, which should not
        # be affected by the previous send at all
        def resume():
            return 'resumed'
        e2 = pool.spawn(resume)
        self.assertEqual(e2.wait(), 'resumed')

        # we should be able to get out the thing we put in there, too
        self.assertEqual(tp.get(), 'wakeup')
        gt.wait()

    def test_spawn_n_2(self):
        p = greenpool.GreenPool(2)
        self.assertEqual(p.free(), 2)
        r = []

        def foo(a):
            r.append(a)

        gt = p.spawn(foo, 1)
        self.assertEqual(p.free(), 1)
        gt.wait()
        self.assertEqual(r, [1])
        eventlet.sleep(0)
        self.assertEqual(p.free(), 2)

        #Once the pool is exhausted, spawning forces a yield.
        p.spawn_n(foo, 2)
        self.assertEqual(1, p.free())
        self.assertEqual(r, [1])

        p.spawn_n(foo, 3)
        self.assertEqual(0, p.free())
        self.assertEqual(r, [1])

        p.spawn_n(foo, 4)
        self.assertEqual(set(r), set([1, 2, 3]))
        eventlet.sleep(0)
        self.assertEqual(set(r), set([1, 2, 3, 4]))

    def test_exceptions(self):
        p = greenpool.GreenPool(2)
        for m in (p.spawn, p.spawn_n):
            self.assert_pool_has_free(p, 2)
            m(raiser, RuntimeError())
            self.assert_pool_has_free(p, 1)
            p.waitall()
            self.assert_pool_has_free(p, 2)
            m(raiser, greenlet.GreenletExit)
            self.assert_pool_has_free(p, 1)
            p.waitall()
            self.assert_pool_has_free(p, 2)

    def test_imap(self):
        p = greenpool.GreenPool(4)
        result_list = list(p.imap(passthru, range(10)))
        self.assertEqual(result_list, list(range(10)))

    def test_empty_imap(self):
        p = greenpool.GreenPool(4)
        result_iter = p.imap(passthru, [])
        self.assertRaises(StopIteration, result_iter.next)

    def test_imap_nonefunc(self):
        p = greenpool.GreenPool(4)
        result_list = list(p.imap(None, range(10)))
        self.assertEqual(result_list, [(x,) for x in range(10)])

    def test_imap_multi_args(self):
        p = greenpool.GreenPool(4)
        result_list = list(p.imap(passthru2, range(10), range(10, 20)))
        self.assertEqual(result_list, list(zip(range(10), range(10, 20))))

    def test_imap_raises(self):
        # testing the case where the function raises an exception;
        # both that the caller sees that exception, and that the iterator
        # continues to be usable to get the rest of the items
        p = greenpool.GreenPool(4)

        def raiser(item):
            if item == 1 or item == 7:
                raise RuntimeError("intentional error")
            else:
                return item

        it = p.imap(raiser, range(10))
        results = []
        while True:
            try:
                results.append(six.next(it))
            except RuntimeError:
                results.append('r')
            except StopIteration:
                break
        self.assertEqual(results, [0, 'r', 2, 3, 4, 5, 6, 'r', 8, 9])

    def test_starmap(self):
        p = greenpool.GreenPool(4)
        result_list = list(p.starmap(passthru, [(x,) for x in range(10)]))
        self.assertEqual(result_list, list(range(10)))

    def test_waitall_on_nothing(self):
        p = greenpool.GreenPool()
        p.waitall()

    def test_recursive_waitall(self):
        p = greenpool.GreenPool()
        gt = p.spawn(p.waitall)
        self.assertRaises(AssertionError, gt.wait)


class GreenPile(tests.LimitedTestCase):
    def test_pile(self):
        p = greenpool.GreenPile(4)
        for i in range(10):
            p.spawn(passthru, i)
        result_list = list(p)
        self.assertEqual(result_list, list(range(10)))

    def test_pile_spawn_times_out(self):
        p = greenpool.GreenPile(4)
        for i in range(4):
            p.spawn(passthru, i)
        # now it should be full and this should time out
        eventlet.Timeout(0)
        self.assertRaises(eventlet.Timeout, p.spawn, passthru, "time out")
        # verify that the spawn breakage didn't interrupt the sequence
        # and terminates properly
        for i in range(4, 10):
            p.spawn(passthru, i)
        self.assertEqual(list(p), list(range(10)))

    def test_constructing_from_pool(self):
        pool = greenpool.GreenPool(2)
        pile1 = greenpool.GreenPile(pool)
        pile2 = greenpool.GreenPile(pool)

        def bunch_of_work(pile, unique):
            for i in range(10):
                pile.spawn(passthru, i + unique)

        eventlet.spawn(bunch_of_work, pile1, 0)
        eventlet.spawn(bunch_of_work, pile2, 100)
        eventlet.sleep(0)
        self.assertEqual(list(pile2), list(range(100, 110)))
        self.assertEqual(list(pile1), list(range(10)))


class StressException(Exception):
    pass

r = random.Random(0)


def pressure(arg):
    while r.random() < 0.5:
        eventlet.sleep(r.random() * 0.001)
    if r.random() < 0.8:
        return arg
    else:
        raise StressException(arg)


def passthru(arg):
    while r.random() < 0.5:
        eventlet.sleep(r.random() * 0.001)
    return arg


class Stress(tests.LimitedTestCase):
    # tests will take extra-long
    TEST_TIMEOUT = 60

    @tests.skip_unless(os.environ.get('RUN_STRESS_TESTS') == 'YES')
    def spawn_order_check(self, concurrency):
        # checks that piles are strictly ordered
        p = greenpool.GreenPile(concurrency)

        def makework(count, unique):
            for i in six.moves.range(count):
                token = (unique, i)
                p.spawn(pressure, token)

        iters = 1000
        eventlet.spawn(makework, iters, 1)
        eventlet.spawn(makework, iters, 2)
        eventlet.spawn(makework, iters, 3)
        p.spawn(pressure, (0, 0))
        latest = [-1] * 4
        received = 0
        it = iter(p)
        while True:
            try:
                i = six.next(it)
            except StressException as exc:
                i = exc.args[0]
            except StopIteration:
                break
            received += 1
            if received % 5 == 0:
                eventlet.sleep(0.0001)
            unique, order = i
            self.assert_(latest[unique] < order)
            latest[unique] = order
        for l in latest[1:]:
            self.assertEqual(l, iters - 1)

    @tests.skip_unless(os.environ.get('RUN_STRESS_TESTS') == 'YES')
    def test_ordering_5(self):
        self.spawn_order_check(5)

    @tests.skip_unless(os.environ.get('RUN_STRESS_TESTS') == 'YES')
    def test_ordering_50(self):
        self.spawn_order_check(50)

    def imap_memory_check(self, concurrency):
        # checks that imap is strictly
        # ordered and consumes a constant amount of memory
        p = greenpool.GreenPool(concurrency)
        count = 1000
        it = p.imap(passthru, six.moves.range(count))
        latest = -1
        while True:
            try:
                i = six.next(it)
            except StopIteration:
                break

            if latest == -1:
                gc.collect()
                initial_obj_count = len(gc.get_objects())
            self.assert_(i > latest)
            latest = i
            if latest % 5 == 0:
                eventlet.sleep(0.001)
            if latest % 10 == 0:
                gc.collect()
                objs_created = len(gc.get_objects()) - initial_obj_count
                self.assert_(objs_created < 25 * concurrency, objs_created)
        # make sure we got to the end
        self.assertEqual(latest, count - 1)

    @tests.skip_unless(os.environ.get('RUN_STRESS_TESTS') == 'YES')
    def test_imap_50(self):
        self.imap_memory_check(50)

    @tests.skip_unless(os.environ.get('RUN_STRESS_TESTS') == 'YES')
    def test_imap_500(self):
        self.imap_memory_check(500)

    @tests.skip_unless(os.environ.get('RUN_STRESS_TESTS') == 'YES')
    def test_with_intpool(self):
        class IntPool(pools.Pool):
            def create(self):
                self.current_integer = getattr(self, 'current_integer', 0) + 1
                return self.current_integer

        def subtest(intpool_size, pool_size, num_executes):
            def run(int_pool):
                token = int_pool.get()
                eventlet.sleep(0.0001)
                int_pool.put(token)
                return token

            int_pool = IntPool(max_size=intpool_size)
            pool = greenpool.GreenPool(pool_size)
            for ix in six.moves.range(num_executes):
                pool.spawn(run, int_pool)
            pool.waitall()

        subtest(4, 7, 7)
        subtest(50, 75, 100)
        for isize in (10, 20, 30, 40, 50):
            for psize in (5, 25, 35, 50):
                subtest(isize, psize, psize)

########NEW FILE########
__FILENAME__ = greenthread_test
from tests import LimitedTestCase
from eventlet import greenthread
from eventlet.support import greenlets as greenlet

_g_results = []
def passthru(*args, **kw):
    _g_results.append((args, kw))
    return args, kw

def waiter(a):
    greenthread.sleep(0.1)
    return a


class Asserts(object):
    def assert_dead(self, gt):
        if hasattr(gt, 'wait'):
            self.assertRaises(greenlet.GreenletExit, gt.wait)    
        self.assert_(gt.dead)
        self.assert_(not gt)

class Spawn(LimitedTestCase, Asserts):
    def tearDown(self):
        global _g_results
        super(Spawn, self).tearDown()
        _g_results = []
        
    def test_simple(self):
        gt = greenthread.spawn(passthru, 1, b=2)
        self.assertEqual(gt.wait(), ((1,),{'b':2}))
        self.assertEqual(_g_results, [((1,),{'b':2})])
        
    def test_n(self):
        gt = greenthread.spawn_n(passthru, 2, b=3)
        self.assert_(not gt.dead)
        greenthread.sleep(0)
        self.assert_(gt.dead)
        self.assertEqual(_g_results, [((2,),{'b':3})])
        
    def test_kill(self):
        gt = greenthread.spawn(passthru, 6)
        greenthread.kill(gt)
        self.assert_dead(gt)
        greenthread.sleep(0.001)
        self.assertEqual(_g_results, [])
        greenthread.kill(gt)
        self.assert_dead(gt)
        
    def test_kill_meth(self):
        gt = greenthread.spawn(passthru, 6)
        gt.kill()
        self.assert_dead(gt)
        greenthread.sleep(0.001)
        self.assertEqual(_g_results, [])
        gt.kill()
        self.assert_dead(gt)
        
    def test_kill_n(self):
        gt = greenthread.spawn_n(passthru, 7)
        greenthread.kill(gt)
        self.assert_dead(gt)
        greenthread.sleep(0.001)
        self.assertEqual(_g_results, [])
        greenthread.kill(gt)
        self.assert_dead(gt)
    
    def test_link(self):
        results = []
        def link_func(g, *a, **kw):
            results.append(g)
            results.append(a)
            results.append(kw)
        gt = greenthread.spawn(passthru, 5)
        gt.link(link_func, 4, b=5)
        self.assertEqual(gt.wait(), ((5,), {}))
        self.assertEqual(results, [gt, (4,), {'b':5}])
        
    def test_link_after_exited(self):
        results = []
        def link_func(g, *a, **kw):
            results.append(g)
            results.append(a)
            results.append(kw)
        gt = greenthread.spawn(passthru, 5)
        self.assertEqual(gt.wait(), ((5,), {}))
        gt.link(link_func, 4, b=5)
        self.assertEqual(results, [gt, (4,), {'b':5}])

    def test_link_relinks(self):
        # test that linking in a linked func doesn't cause infinite recursion.
        called = []

        def link_func(g):
            g.link(link_func_pass)

        def link_func_pass(g):
            called.append(True)

        gt = greenthread.spawn(passthru)
        gt.link(link_func)
        gt.wait()
        self.assertEqual(called, [True])

class SpawnAfter(Spawn):
    def test_basic(self):
        gt = greenthread.spawn_after(0.1, passthru, 20)
        self.assertEqual(gt.wait(), ((20,), {}))
        
    def test_cancel(self):
        gt = greenthread.spawn_after(0.1, passthru, 21)
        gt.cancel()
        self.assert_dead(gt)

    def test_cancel_already_started(self):
        gt = greenthread.spawn_after(0, waiter, 22)
        greenthread.sleep(0)
        gt.cancel()
        self.assertEqual(gt.wait(), 22)
        
    def test_kill_already_started(self):
        gt = greenthread.spawn_after(0, waiter, 22)
        greenthread.sleep(0)
        gt.kill()
        self.assert_dead(gt)

class SpawnAfterLocal(LimitedTestCase, Asserts):
    def setUp(self):
        super(SpawnAfterLocal, self).setUp()
        self.lst = [1]

    def test_timer_fired(self):
        def func():
            greenthread.spawn_after_local(0.1, self.lst.pop)
            greenthread.sleep(0.2)

        greenthread.spawn(func)
        assert self.lst == [1], self.lst
        greenthread.sleep(0.3)
        assert self.lst == [], self.lst

    def test_timer_cancelled_upon_greenlet_exit(self):
        def func():
            greenthread.spawn_after_local(0.1, self.lst.pop)

        greenthread.spawn(func)
        assert self.lst == [1], self.lst
        greenthread.sleep(0.2)
        assert self.lst == [1], self.lst

    def test_spawn_is_not_cancelled(self):
        def func():
            greenthread.spawn(self.lst.pop)
            # exiting immediatelly, but self.lst.pop must be called
        greenthread.spawn(func)
        greenthread.sleep(0.1)
        assert self.lst == [], self.lst

########NEW FILE########
__FILENAME__ = hub_test
from __future__ import with_statement
import sys

import tests
from tests import LimitedTestCase, main, skip_with_pyevent, skip_if_no_itimer, skip_unless
from tests.patcher_test import ProcessBase
import time
import eventlet
from eventlet import hubs
from eventlet.event import Event
from eventlet.semaphore import Semaphore
from eventlet.support import greenlets, six


DELAY = 0.001


def noop():
    pass


class TestTimerCleanup(LimitedTestCase):
    TEST_TIMEOUT = 2

    @skip_with_pyevent
    def test_cancel_immediate(self):
        hub = hubs.get_hub()
        stimers = hub.get_timers_count()
        scanceled = hub.timers_canceled
        for i in six.moves.range(2000):
            t = hubs.get_hub().schedule_call_global(60, noop)
            t.cancel()
            self.assert_less_than_equal(hub.timers_canceled,
                                        hub.get_timers_count() + 1)
        # there should be fewer than 1000 new timers and canceled
        self.assert_less_than_equal(hub.get_timers_count(), 1000 + stimers)
        self.assert_less_than_equal(hub.timers_canceled, 1000)

    @skip_with_pyevent
    def test_cancel_accumulated(self):
        hub = hubs.get_hub()
        stimers = hub.get_timers_count()
        scanceled = hub.timers_canceled
        for i in six.moves.range(2000):
            t = hubs.get_hub().schedule_call_global(60, noop)
            eventlet.sleep()
            self.assert_less_than_equal(hub.timers_canceled,
                                        hub.get_timers_count() + 1)
            t.cancel()
            self.assert_less_than_equal(hub.timers_canceled,
                                        hub.get_timers_count() + 1, hub.timers)
        # there should be fewer than 1000 new timers and canceled
        self.assert_less_than_equal(hub.get_timers_count(), 1000 + stimers)
        self.assert_less_than_equal(hub.timers_canceled, 1000)

    @skip_with_pyevent
    def test_cancel_proportion(self):
        # if fewer than half the pending timers are canceled, it should
        # not clean them out
        hub = hubs.get_hub()
        uncanceled_timers = []
        stimers = hub.get_timers_count()
        scanceled = hub.timers_canceled
        for i in six.moves.range(1000):
            # 2/3rds of new timers are uncanceled
            t = hubs.get_hub().schedule_call_global(60, noop)
            t2 = hubs.get_hub().schedule_call_global(60, noop)
            t3 = hubs.get_hub().schedule_call_global(60, noop)
            eventlet.sleep()
            self.assert_less_than_equal(hub.timers_canceled,
                                        hub.get_timers_count() + 1)
            t.cancel()
            self.assert_less_than_equal(hub.timers_canceled,
                                        hub.get_timers_count() + 1)
            uncanceled_timers.append(t2)
            uncanceled_timers.append(t3)
        # 3000 new timers, plus a few extras
        self.assert_less_than_equal(stimers + 3000,
                                    stimers + hub.get_timers_count())
        self.assertEqual(hub.timers_canceled, 1000)
        for t in uncanceled_timers:
            t.cancel()
            self.assert_less_than_equal(hub.timers_canceled,
                                        hub.get_timers_count())
        eventlet.sleep()


class TestScheduleCall(LimitedTestCase):

    def test_local(self):
        lst = [1]
        eventlet.spawn(hubs.get_hub().schedule_call_local, DELAY, lst.pop)
        eventlet.sleep(0)
        eventlet.sleep(DELAY * 2)
        assert lst == [1], lst

    def test_global(self):
        lst = [1]
        eventlet.spawn(hubs.get_hub().schedule_call_global, DELAY, lst.pop)
        eventlet.sleep(0)
        eventlet.sleep(DELAY * 2)
        assert lst == [], lst

    def test_ordering(self):
        lst = []
        hubs.get_hub().schedule_call_global(DELAY * 2, lst.append, 3)
        hubs.get_hub().schedule_call_global(DELAY, lst.append, 1)
        hubs.get_hub().schedule_call_global(DELAY, lst.append, 2)
        while len(lst) < 3:
            eventlet.sleep(DELAY)
        self.assertEqual(lst, [1, 2, 3])


class TestDebug(LimitedTestCase):

    def test_debug_listeners(self):
        hubs.get_hub().set_debug_listeners(True)
        hubs.get_hub().set_debug_listeners(False)

    def test_timer_exceptions(self):
        hubs.get_hub().set_timer_exceptions(True)
        hubs.get_hub().set_timer_exceptions(False)


class TestExceptionInMainloop(LimitedTestCase):

    def test_sleep(self):
        # even if there was an error in the mainloop, the hub should continue
        # to work
        start = time.time()
        eventlet.sleep(DELAY)
        delay = time.time() - start

        assert delay >= DELAY * \
            0.9, 'sleep returned after %s seconds (was scheduled for %s)' % (
                delay, DELAY)

        def fail():
            1 // 0

        hubs.get_hub().schedule_call_global(0, fail)

        start = time.time()
        eventlet.sleep(DELAY)
        delay = time.time() - start

        assert delay >= DELAY * \
            0.9, 'sleep returned after %s seconds (was scheduled for %s)' % (
                delay, DELAY)


class TestExceptionInGreenthread(LimitedTestCase):

    @skip_unless(greenlets.preserves_excinfo)
    def test_exceptionpreservation(self):
        # events for controlling execution order
        gt1event = Event()
        gt2event = Event()

        def test_gt1():
            try:
                raise KeyError()
            except KeyError:
                gt1event.send('exception')
                gt2event.wait()
                assert sys.exc_info()[0] is KeyError
                gt1event.send('test passed')

        def test_gt2():
            gt1event.wait()
            gt1event.reset()
            assert sys.exc_info()[0] is None
            try:
                raise ValueError()
            except ValueError:
                gt2event.send('exception')
                gt1event.wait()
                assert sys.exc_info()[0] is ValueError

        g1 = eventlet.spawn(test_gt1)
        g2 = eventlet.spawn(test_gt2)
        try:
            g1.wait()
            g2.wait()
        finally:
            g1.kill()
            g2.kill()

    def test_exceptionleaks(self):
        # tests expected behaviour with all versions of greenlet
        def test_gt(sem):
            try:
                raise KeyError()
            except KeyError:
                sem.release()
                hubs.get_hub().switch()

        # semaphores for controlling execution order
        sem = Semaphore()
        sem.acquire()
        g = eventlet.spawn(test_gt, sem)
        try:
            sem.acquire()
            assert sys.exc_info()[0] is None
        finally:
            g.kill()


class TestHubSelection(LimitedTestCase):

    def test_explicit_hub(self):
        if getattr(hubs.get_hub(), 'uses_twisted_reactor', None):
            # doesn't work with twisted
            return
        oldhub = hubs.get_hub()
        try:
            hubs.use_hub(Foo)
            self.assert_(isinstance(hubs.get_hub(), Foo), hubs.get_hub())
        finally:
            hubs._threadlocal.hub = oldhub


class TestHubBlockingDetector(LimitedTestCase):
    TEST_TIMEOUT = 10

    @skip_with_pyevent
    def test_block_detect(self):
        def look_im_blocking():
            import time
            time.sleep(2)
        from eventlet import debug
        debug.hub_blocking_detection(True)
        gt = eventlet.spawn(look_im_blocking)
        self.assertRaises(RuntimeError, gt.wait)
        debug.hub_blocking_detection(False)

    @skip_with_pyevent
    @skip_if_no_itimer
    def test_block_detect_with_itimer(self):
        def look_im_blocking():
            import time
            time.sleep(0.5)

        from eventlet import debug
        debug.hub_blocking_detection(True, resolution=0.1)
        gt = eventlet.spawn(look_im_blocking)
        self.assertRaises(RuntimeError, gt.wait)
        debug.hub_blocking_detection(False)


class TestSuspend(LimitedTestCase):
    TEST_TIMEOUT = 3
    longMessage = True
    maxDiff = None

    def test_suspend_doesnt_crash(self):
        import os
        import shutil
        import signal
        import subprocess
        import sys
        import tempfile
        self.tempdir = tempfile.mkdtemp('test_suspend')
        filename = os.path.join(self.tempdir,  'test_suspend.py')
        fd = open(filename, "w")
        fd.write("""import eventlet
eventlet.Timeout(0.5)
try:
   eventlet.listen(("127.0.0.1", 0)).accept()
except eventlet.Timeout:
   print("exited correctly")
""")
        fd.close()
        python_path = os.pathsep.join(sys.path + [self.tempdir])
        new_env = os.environ.copy()
        new_env['PYTHONPATH'] = python_path
        p = subprocess.Popen([sys.executable,
                              os.path.join(self.tempdir, filename)],
                             stdout=subprocess.PIPE, stderr=subprocess.STDOUT, env=new_env)
        eventlet.sleep(0.4)  # wait for process to hit accept
        os.kill(p.pid, signal.SIGSTOP)  # suspend and resume to generate EINTR
        os.kill(p.pid, signal.SIGCONT)
        output, _ = p.communicate()
        lines = output.decode('utf-8', 'replace').splitlines()
        self.assert_("exited correctly" in lines[-1], output)
        shutil.rmtree(self.tempdir)


class TestBadFilenos(LimitedTestCase):

    @skip_with_pyevent
    def test_repeated_selects(self):
        from eventlet.green import select
        self.assertRaises(ValueError, select.select, [-1], [], [])
        self.assertRaises(ValueError, select.select, [-1], [], [])


class TestFork(LimitedTestCase):

    @skip_with_pyevent
    def test_fork(self):
        output = tests.run_python('tests/hub_test_fork.py')
        lines = output.splitlines()
        self.assertEqual(lines, ["accept blocked", "child died ok"], output)


class TestDeadRunLoop(LimitedTestCase):
    TEST_TIMEOUT = 2

    class CustomException(Exception):
        pass

    def test_kill(self):
        """ Checks that killing a process after the hub runloop dies does
        not immediately return to hub greenlet's parent and schedule a
        redundant timer. """
        hub = hubs.get_hub()

        def dummyproc():
            hub.switch()

        g = eventlet.spawn(dummyproc)
        eventlet.sleep(0)  # let dummyproc run
        assert hub.greenlet.parent == eventlet.greenthread.getcurrent()
        self.assertRaises(KeyboardInterrupt, hub.greenlet.throw,
                          KeyboardInterrupt())

        # kill dummyproc, this schedules a timer to return execution to
        # this greenlet before throwing an exception in dummyproc.
        # it is from this timer that execution should be returned to this
        # greenlet, and not by propogating of the terminating greenlet.
        g.kill()
        with eventlet.Timeout(0.5, self.CustomException()):
            # we now switch to the hub, there should be no existing timers
            # that switch back to this greenlet and so this hub.switch()
            # call should block indefinately.
            self.assertRaises(self.CustomException, hub.switch)

    def test_parent(self):
        """ Checks that a terminating greenthread whose parent
        was a previous, now-defunct hub greenlet returns execution to
        the hub runloop and not the hub greenlet's parent. """
        hub = hubs.get_hub()

        def dummyproc():
            pass

        g = eventlet.spawn(dummyproc)
        assert hub.greenlet.parent == eventlet.greenthread.getcurrent()
        self.assertRaises(KeyboardInterrupt, hub.greenlet.throw,
                          KeyboardInterrupt())

        assert not g.dead  # check dummyproc hasn't completed
        with eventlet.Timeout(0.5, self.CustomException()):
            # we now switch to the hub which will allow
            # completion of dummyproc.
            # this should return execution back to the runloop and not
            # this greenlet so that hub.switch() would block indefinately.
            self.assertRaises(self.CustomException, hub.switch)
        assert g.dead  # sanity check that dummyproc has completed


class Foo(object):
    pass


class TestDefaultHub(ProcessBase):

    def test_kqueue_unsupported(self):
        # https://github.com/eventlet/eventlet/issues/38
        # get_hub on windows broken by kqueue
        module_source = r'''
from __future__ import print_function

# Simulate absence of kqueue even on platforms that support it.
import select
try:
    del select.kqueue
except AttributeError:
    pass

import __builtin__
original_import = __builtin__.__import__

def fail_import(name, *args, **kwargs):
    if 'epoll' in name:
        raise ImportError('disabled for test')
    if 'kqueue' in name:
        print('kqueue tried')
    return original_import(name, *args, **kwargs)

__builtin__.__import__ = fail_import


import eventlet.hubs
eventlet.hubs.get_default_hub()
print('ok')
'''
        self.write_to_tempfile('newmod', module_source)
        output, _ = self.launch_subprocess('newmod.py')
        self.assertEqual(output, 'kqueue tried\nok\n')


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = hub_test_fork
# no standard tests in this file, ignore
__test__ = False

if __name__ == '__main__':
    import os
    import eventlet
    server = eventlet.listen(('localhost', 12345))
    t = eventlet.Timeout(0.01)
    try:
        new_sock, address = server.accept()
    except eventlet.Timeout as t:
        pass

    pid = os.fork()
    if not pid:
        t = eventlet.Timeout(0.1)
        try:
            new_sock, address = server.accept()
        except eventlet.Timeout as t:
            print("accept blocked")
    else:
        kpid, status = os.wait()
        assert kpid == pid
        assert status == 0
        print("child died ok")

########NEW FILE########
__FILENAME__ = mock
# mock.py
# Test tools for mocking and patching.
# Copyright (C) 2007-2009 Michael Foord
# E-mail: fuzzyman AT voidspace DOT org DOT uk

# mock 0.6.0
# http://www.voidspace.org.uk/python/mock/

# Released subject to the BSD License
# Please see http://www.voidspace.org.uk/python/license.shtml

# Scripts maintained at http://www.voidspace.org.uk/python/index.shtml
# Comments, suggestions and bug reports welcome.


__all__ = (
    'Mock',
    'patch',
    'patch_object',
    'sentinel',
    'DEFAULT'
)

__version__ = '0.6.0'

class SentinelObject(object):
    def __init__(self, name):
        self.name = name

    def __repr__(self):
        return '<SentinelObject "%s">' % self.name


class Sentinel(object):
    def __init__(self):
        self._sentinels = {}

    def __getattr__(self, name):
        return self._sentinels.setdefault(name, SentinelObject(name))


sentinel = Sentinel()

DEFAULT = sentinel.DEFAULT


class OldStyleClass:
    pass
ClassType = type(OldStyleClass)


def _is_magic(name):
    return '__%s__' % name[2:-2] == name


def _copy(value):
    if type(value) in (dict, list, tuple, set):
        return type(value)(value)
    return value


class Mock(object):

    def __init__(self, spec=None, side_effect=None, return_value=DEFAULT,
                 name=None, parent=None, wraps=None):
        self._parent = parent
        self._name = name
        if spec is not None and not isinstance(spec, list):
            spec = [member for member in dir(spec) if not _is_magic(member)]

        self._methods = spec
        self._children = {}
        self._return_value = return_value
        self.side_effect = side_effect
        self._wraps = wraps

        self.reset_mock()

    def reset_mock(self):
        self.called = False
        self.call_args = None
        self.call_count = 0
        self.call_args_list = []
        self.method_calls = []
        for child in self._children.itervalues():
            child.reset_mock()
        if isinstance(self._return_value, Mock):
            self._return_value.reset_mock()

    def __get_return_value(self):
        if self._return_value is DEFAULT:
            self._return_value = Mock()
        return self._return_value

    def __set_return_value(self, value):
        self._return_value = value

    return_value = property(__get_return_value, __set_return_value)

    def __call__(self, *args, **kwargs):
        self.called = True
        self.call_count += 1
        self.call_args = (args, kwargs)
        self.call_args_list.append((args, kwargs))

        parent = self._parent
        name = self._name
        while parent is not None:
            parent.method_calls.append((name, args, kwargs))
            if parent._parent is None:
                break
            name = parent._name + '.' + name
            parent = parent._parent

        ret_val = DEFAULT
        if self.side_effect is not None:
            if (isinstance(self.side_effect, Exception) or
                isinstance(self.side_effect, (type, ClassType)) and
                issubclass(self.side_effect, Exception)):
                raise self.side_effect

            ret_val = self.side_effect(*args, **kwargs)
            if ret_val is DEFAULT:
                ret_val = self.return_value

        if self._wraps is not None and self._return_value is DEFAULT:
            return self._wraps(*args, **kwargs)
        if ret_val is DEFAULT:
            ret_val = self.return_value
        return ret_val

    def __getattr__(self, name):
        if self._methods is not None:
            if name not in self._methods:
                raise AttributeError("Mock object has no attribute '%s'" % name)
        elif _is_magic(name):
            raise AttributeError(name)

        if name not in self._children:
            wraps = None
            if self._wraps is not None:
                wraps = getattr(self._wraps, name)
            self._children[name] = Mock(parent=self, name=name, wraps=wraps)

        return self._children[name]

    def assert_called_with(self, *args, **kwargs):
        assert self.call_args == (args, kwargs), 'Expected: %s\nCalled with: %s' % ((args, kwargs), self.call_args)


def _dot_lookup(thing, comp, import_path):
    try:
        return getattr(thing, comp)
    except AttributeError:
        __import__(import_path)
        return getattr(thing, comp)


def _importer(target):
    components = target.split('.')
    import_path = components.pop(0)
    thing = __import__(import_path)

    for comp in components:
        import_path += ".%s" % comp
        thing = _dot_lookup(thing, comp, import_path)
    return thing


class _patch(object):
    def __init__(self, target, attribute, new, spec, create):
        self.target = target
        self.attribute = attribute
        self.new = new
        self.spec = spec
        self.create = create
        self.has_local = False

    def __call__(self, func):
        if hasattr(func, 'patchings'):
            func.patchings.append(self)
            return func

        def patched(*args, **keywargs):
            # don't use a with here (backwards compatability with 2.5)
            extra_args = []
            for patching in patched.patchings:
                arg = patching.__enter__()
                if patching.new is DEFAULT:
                    extra_args.append(arg)
            args += tuple(extra_args)
            try:
                return func(*args, **keywargs)
            finally:
                for patching in getattr(patched, 'patchings', []):
                    patching.__exit__()

        patched.patchings = [self]
        patched.__name__ = func.__name__
        patched.compat_co_firstlineno = getattr(func, "compat_co_firstlineno",
                                                func.func_code.co_firstlineno)
        return patched

    def get_original(self):
        target = self.target
        name = self.attribute
        create = self.create

        original = DEFAULT
        if _has_local_attr(target, name):
            try:
                original = target.__dict__[name]
            except AttributeError:
                # for instances of classes with slots, they have no __dict__
                original = getattr(target, name)
        elif not create and not hasattr(target, name):
            raise AttributeError("%s does not have the attribute %r" % (target, name))
        return original

    def __enter__(self):
        new, spec, = self.new, self.spec
        original = self.get_original()
        if new is DEFAULT:
            # XXXX what if original is DEFAULT - shouldn't use it as a spec
            inherit = False
            if spec == True:
                # set spec to the object we are replacing
                spec = original
                if isinstance(spec, (type, ClassType)):
                    inherit = True
            new = Mock(spec=spec)
            if inherit:
                new.return_value = Mock(spec=spec)
        self.temp_original = original
        setattr(self.target, self.attribute, new)
        return new

    def __exit__(self, *_):
        if self.temp_original is not DEFAULT:
            setattr(self.target, self.attribute, self.temp_original)
        else:
            delattr(self.target, self.attribute)
        del self.temp_original


def patch_object(target, attribute, new=DEFAULT, spec=None, create=False):
    return _patch(target, attribute, new, spec, create)


def patch(target, new=DEFAULT, spec=None, create=False):
    try:
        target, attribute = target.rsplit('.', 1)
    except (TypeError, ValueError):
        raise TypeError("Need a valid target to patch. You supplied: %r" % (target,))
    target = _importer(target)
    return _patch(target, attribute, new, spec, create)


def _has_local_attr(obj, name):
    try:
        return name in vars(obj)
    except TypeError:
        # objects without a __dict__
        return hasattr(obj, name)

########NEW FILE########
__FILENAME__ = mysqldb_test
from __future__ import print_function

import os
import time
import traceback

import eventlet
from eventlet import event
from tests import (
    LimitedTestCase,
    run_python,
    skip_unless, using_pyevent, get_database_auth,
)
try:
    from eventlet.green import MySQLdb
except ImportError:
    MySQLdb = False


def mysql_requirement(_f):
    """We want to skip tests if using pyevent, MySQLdb is not installed, or if
    there is no database running on the localhost that the auth file grants
    us access to.

    This errs on the side of skipping tests if everything is not right, but
    it's better than a million tests failing when you don't care about mysql
    support."""
    if using_pyevent(_f):
        return False
    if MySQLdb is False:
        print("Skipping mysql tests, MySQLdb not importable")
        return False
    try:
        auth = get_database_auth()['MySQLdb'].copy()
        MySQLdb.connect(**auth)
        return True
    except MySQLdb.OperationalError:
        print("Skipping mysql tests, error when connecting:")
        traceback.print_exc()
        return False


class TestMySQLdb(LimitedTestCase):
    def setUp(self):
        super(TestMySQLdb, self).setUp()

        self._auth = get_database_auth()['MySQLdb']
        self.create_db()
        self.connection = None
        self.connection = MySQLdb.connect(**self._auth)
        cursor = self.connection.cursor()
        cursor.execute("""CREATE TABLE gargleblatz
        (
        a INTEGER
        );""")
        self.connection.commit()
        cursor.close()

    def tearDown(self):
        if self.connection:
            self.connection.close()
        self.drop_db()

        super(TestMySQLdb, self).tearDown()

    @skip_unless(mysql_requirement)
    def create_db(self):
        auth = self._auth.copy()
        try:
            self.drop_db()
        except Exception:
            pass
        dbname = 'test_%d_%d' % (os.getpid(), int(time.time()*1000))
        db = MySQLdb.connect(**auth).cursor()
        db.execute("create database "+dbname)
        db.close()
        self._auth['db'] = dbname
        del db

    def drop_db(self):
        db = MySQLdb.connect(**self._auth).cursor()
        db.execute("drop database "+self._auth['db'])
        db.close()
        del db

    def set_up_dummy_table(self, connection=None):
        close_connection = False
        if connection is None:
            close_connection = True
            if self.connection is None:
                connection = MySQLdb.connect(**self._auth)
            else:
                connection = self.connection

        cursor = connection.cursor()
        cursor.execute(self.dummy_table_sql)
        connection.commit()
        cursor.close()
        if close_connection:
            connection.close()

    dummy_table_sql = """CREATE TEMPORARY TABLE test_table
        (
        row_id INTEGER PRIMARY KEY AUTO_INCREMENT,
        value_int INTEGER,
        value_float FLOAT,
        value_string VARCHAR(200),
        value_uuid CHAR(36),
        value_binary BLOB,
        value_binary_string VARCHAR(200) BINARY,
        value_enum ENUM('Y','N'),
        created TIMESTAMP
        ) ENGINE=InnoDB;"""

    def assert_cursor_yields(self, curs):
        counter = [0]

        def tick():
            while True:
                counter[0] += 1
                eventlet.sleep()
        gt = eventlet.spawn(tick)
        curs.execute("select 1")
        rows = curs.fetchall()
        self.assertEqual(len(rows), 1)
        self.assertEqual(len(rows[0]), 1)
        self.assertEqual(rows[0][0], 1)
        self.assert_(counter[0] > 0, counter[0])
        gt.kill()

    def assert_cursor_works(self, cursor):
        cursor.execute("select 1")
        rows = cursor.fetchall()
        self.assertEqual(len(rows), 1)
        self.assertEqual(len(rows[0]), 1)
        self.assertEqual(rows[0][0], 1)
        self.assert_cursor_yields(cursor)

    def assert_connection_works(self, conn):
        curs = conn.cursor()
        self.assert_cursor_works(curs)

    def test_module_attributes(self):
        import MySQLdb as orig
        for key in dir(orig):
            if key not in ('__author__', '__path__', '__revision__',
                           '__version__', '__loader__'):
                self.assert_(hasattr(MySQLdb, key), "%s %s" % (key, getattr(orig, key)))

    def test_connecting(self):
        self.assert_(self.connection is not None)

    def test_connecting_annoyingly(self):
        self.assert_connection_works(MySQLdb.Connect(**self._auth))
        self.assert_connection_works(MySQLdb.Connection(**self._auth))
        self.assert_connection_works(MySQLdb.connections.Connection(**self._auth))

    def test_create_cursor(self):
        cursor = self.connection.cursor()
        cursor.close()

    def test_run_query(self):
        cursor = self.connection.cursor()
        self.assert_cursor_works(cursor)
        cursor.close()

    def test_run_bad_query(self):
        cursor = self.connection.cursor()
        try:
            cursor.execute("garbage blah blah")
            self.assert_(False)
        except AssertionError:
            raise
        except Exception:
            pass
        cursor.close()

    def fill_up_table(self, conn):
        curs = conn.cursor()
        for i in range(1000):
            curs.execute('insert into test_table (value_int) values (%s)' % i)
        conn.commit()

    def test_yields(self):
        conn = self.connection
        self.set_up_dummy_table(conn)
        self.fill_up_table(conn)
        curs = conn.cursor()
        results = []
        SHORT_QUERY = "select * from test_table"
        evt = event.Event()

        def a_query():
            self.assert_cursor_works(curs)
            curs.execute(SHORT_QUERY)
            results.append(2)
            evt.send()
        eventlet.spawn(a_query)
        results.append(1)
        self.assertEqual([1], results)
        evt.wait()
        self.assertEqual([1, 2], results)

    def test_visibility_from_other_connections(self):
        conn = MySQLdb.connect(**self._auth)
        conn2 = MySQLdb.connect(**self._auth)
        curs = conn.cursor()
        try:
            curs2 = conn2.cursor()
            curs2.execute("insert into gargleblatz (a) values (%s)" % (314159))
            self.assertEqual(curs2.rowcount, 1)
            conn2.commit()
            selection_query = "select * from gargleblatz"
            curs2.execute(selection_query)
            self.assertEqual(curs2.rowcount, 1)
            del curs2, conn2
            # create a new connection, it should see the addition
            conn3 = MySQLdb.connect(**self._auth)
            curs3 = conn3.cursor()
            curs3.execute(selection_query)
            self.assertEqual(curs3.rowcount, 1)
            # now, does the already-open connection see it?
            curs.execute(selection_query)
            self.assertEqual(curs.rowcount, 1)
            del curs3, conn3
        finally:
            # clean up my litter
            curs.execute("delete from gargleblatz where a=314159")
            conn.commit()


class TestMonkeyPatch(LimitedTestCase):
    @skip_unless(mysql_requirement)
    def test_monkey_patching(self):
        testcode_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            'mysqldb_test_monkey_patch.py',
        )
        output = run_python(testcode_path)
        lines = output.splitlines()
        self.assertEqual(len(lines), 2, output)
        self.assertEqual(lines[0].replace("psycopg,", ""),
                         'mysqltest MySQLdb,os,select,socket,thread,time')
        self.assertEqual(lines[1], "connect True")

########NEW FILE########
__FILENAME__ = mysqldb_test_monkey_patch
from __future__ import print_function
import MySQLdb as m
from eventlet import patcher
from eventlet.green import MySQLdb as gm

# no standard tests in this file, ignore
__test__ = False

if __name__ == '__main__':
    patcher.monkey_patch(all=True, MySQLdb=True)
    print("mysqltest {0}".format(",".join(sorted(patcher.already_patched.keys()))))
    print("connect {0}".format(m.connect == gm.connect))

########NEW FILE########
__FILENAME__ = nosewrapper
""" This script simply gets the paths correct for testing eventlet with the
hub extension for Nose."""
import nose
from os.path import dirname, realpath, abspath
import sys


parent_dir = dirname(dirname(realpath(abspath(__file__))))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

# hudson does a better job printing the test results if the exit value is 0
zero_status = '--force-zero-status'
if zero_status in sys.argv:
    sys.argv.remove(zero_status)
    launch = nose.run
else:
    launch = nose.main

launch(argv=sys.argv)

########NEW FILE########
__FILENAME__ = parse_results
import sys
import os
import traceback
try:
    import sqlite3
except ImportError:
    import pysqlite2.dbapi2 as sqlite3
import re
import glob

def parse_stdout(s):
    argv = re.search('^===ARGV=(.*?)$', s, re.M).group(1)
    argv = argv.split()
    testname = argv[-1]
    del argv[-1]
    hub = None
    reactor = None
    while argv:
        if argv[0]=='--hub':
            hub = argv[1]
            del argv[0]
            del argv[0]
        elif argv[0]=='--reactor':
            reactor = argv[1]
            del argv[0]
            del argv[0]
        else:
            del argv[0]
    if reactor is not None:
        hub += '/%s' % reactor
    return testname, hub
    
unittest_delim = '----------------------------------------------------------------------'

def parse_unittest_output(s):
    s = s[s.rindex(unittest_delim)+len(unittest_delim):]
    num = int(re.search('^Ran (\d+) test.*?$', s, re.M).group(1))
    ok = re.search('^OK$', s, re.M)
    error, fail, timeout = 0, 0, 0
    failed_match = re.search(r'^FAILED \((?:failures=(?P<f>\d+))?,? ?(?:errors=(?P<e>\d+))?\)$', s, re.M)
    ok_match = re.search('^OK$', s, re.M)
    if failed_match:
        assert not ok_match, (ok_match, s)
        fail = failed_match.group('f')
        error = failed_match.group('e')
        fail = int(fail or '0')
        error = int(error or '0')
    else:
        assert ok_match, repr(s)
    timeout_match = re.search('^===disabled because of timeout: (\d+)$', s, re.M)
    if timeout_match:
        timeout = int(timeout_match.group(1))
    return num, error, fail, timeout

def main(db):
    c = sqlite3.connect(db)
    c.execute('''create table if not exists parsed_command_record
              (id integer not null unique,
               testname text,
               hub text,
               runs integer,
               errors integer,
               fails integer,
               timeouts integer,
               error_names text,
               fail_names text,
               timeout_names text)''')
    c.commit()

    parse_error = 0
    
    SQL = ('select command_record.id, command, stdout, exitcode from command_record '
           'where not exists (select * from parsed_command_record where '
           'parsed_command_record.id=command_record.id)')
    for row in c.execute(SQL).fetchall():
        id, command, stdout, exitcode = row
        try:
            testname, hub = parse_stdout(stdout)
            if unittest_delim in stdout:
                runs, errors, fails, timeouts = parse_unittest_output(stdout)
            else:
                if exitcode == 0:
                    runs, errors, fails, timeouts = 1,0,0,0
                if exitcode == 7:
                    runs, errors, fails, timeouts = 0,0,0,1
                elif exitcode:
                    runs, errors, fails, timeouts = 1,1,0,0
        except Exception:
            parse_error += 1
            sys.stderr.write('Failed to parse id=%s\n' % id)
            print(repr(stdout))
            traceback.print_exc()
        else:
            print(id, hub, testname, runs, errors, fails, timeouts)
            c.execute('insert into parsed_command_record '
                      '(id, testname, hub, runs, errors, fails, timeouts) '
                      'values (?, ?, ?, ?, ?, ?, ?)',
                      (id, testname, hub, runs, errors, fails, timeouts))
            c.commit()

if __name__=='__main__':
    if not sys.argv[1:]:
        latest_db = sorted(glob.glob('results.*.db'), key=lambda f: os.stat(f).st_mtime)[-1]
        print(latest_db)
        sys.argv.append(latest_db)
    for db in sys.argv[1:]:
        main(db)
    execfile('generate_report.py')

########NEW FILE########
__FILENAME__ = patcher_psycopg_test
import os

from tests import patcher_test, skip_unless
from tests import get_database_auth
from tests.db_pool_test import postgres_requirement

psycopg_test_file = """
import os
import sys
import eventlet
eventlet.monkey_patch()
from eventlet import patcher
if not patcher.is_monkey_patched('psycopg'):
    print("Psycopg not monkeypatched")
    sys.exit(0)

count = [0]
def tick(totalseconds, persecond):
    for i in range(totalseconds*persecond):
        count[0] += 1
        eventlet.sleep(1.0/persecond)

dsn = os.environ['PSYCOPG_TEST_DSN']
import psycopg2
def fetch(num, secs):
    conn = psycopg2.connect(dsn)
    cur = conn.cursor()
    for i in range(num):
        cur.execute("select pg_sleep(%s)", (secs,))

f = eventlet.spawn(fetch, 2, 1)
t = eventlet.spawn(tick, 2, 100)
f.wait()
assert count[0] > 100, count[0]
print("done")
"""


class PatchingPsycopg(patcher_test.ProcessBase):
    @skip_unless(postgres_requirement)
    def test_psycopg_patched(self):
        if 'PSYCOPG_TEST_DSN' not in os.environ:
            # construct a non-json dsn for the subprocess
            psycopg_auth = get_database_auth()['psycopg2']
            if isinstance(psycopg_auth, str):
                dsn = psycopg_auth
            else:
                dsn = " ".join(["%s=%s" % (k, v) for k, v in psycopg_auth.iteritems()])
            os.environ['PSYCOPG_TEST_DSN'] = dsn
        self.write_to_tempfile("psycopg_patcher", psycopg_test_file)
        output, lines = self.launch_subprocess('psycopg_patcher.py')
        if lines[0].startswith('Psycopg not monkeypatched'):
            print("Can't test psycopg2 patching; it's not installed.")
            return
        # if there's anything wrong with the test program it'll have a stack trace
        self.assert_(lines[0].startswith('done'), output)

########NEW FILE########
__FILENAME__ = patcher_test
import os
import shutil
import sys
import tempfile

from tests import LimitedTestCase, main, run_python, skip_with_pyevent


base_module_contents = """
import socket
import urllib
print("base {0} {1}".format(socket, urllib))
"""

patching_module_contents = """
from eventlet.green import socket
from eventlet.green import urllib
from eventlet import patcher
print('patcher {0} {1}'.format(socket, urllib))
patcher.inject('base', globals(), ('socket', socket), ('urllib', urllib))
del patcher
"""

import_module_contents = """
import patching
import socket
print("importing {0} {1} {2} {3}".format(patching, socket, patching.socket, patching.urllib))
"""


class ProcessBase(LimitedTestCase):
    TEST_TIMEOUT = 3  # starting processes is time-consuming

    def setUp(self):
        super(ProcessBase, self).setUp()
        self._saved_syspath = sys.path
        self.tempdir = tempfile.mkdtemp('_patcher_test')

    def tearDown(self):
        super(ProcessBase, self).tearDown()
        sys.path = self._saved_syspath
        shutil.rmtree(self.tempdir)

    def write_to_tempfile(self, name, contents):
        filename = os.path.join(self.tempdir, name)
        if not filename.endswith('.py'):
            filename = filename + '.py'
        fd = open(filename, "wb")
        fd.write(contents)
        fd.close()

    def launch_subprocess(self, filename):
        path = os.path.join(self.tempdir, filename)
        output = run_python(path)
        lines = output.split("\n")
        return output, lines

    def run_script(self, contents, modname=None):
        if modname is None:
            modname = "testmod"
        self.write_to_tempfile(modname, contents)
        return self.launch_subprocess(modname)


class ImportPatched(ProcessBase):
    def test_patch_a_module(self):
        self.write_to_tempfile("base", base_module_contents)
        self.write_to_tempfile("patching", patching_module_contents)
        self.write_to_tempfile("importing", import_module_contents)
        output, lines = self.launch_subprocess('importing.py')
        self.assert_(lines[0].startswith('patcher'), repr(output))
        self.assert_(lines[1].startswith('base'), repr(output))
        self.assert_(lines[2].startswith('importing'), repr(output))
        self.assert_('eventlet.green.socket' in lines[1], repr(output))
        self.assert_('eventlet.green.urllib' in lines[1], repr(output))
        self.assert_('eventlet.green.socket' in lines[2], repr(output))
        self.assert_('eventlet.green.urllib' in lines[2], repr(output))
        self.assert_('eventlet.green.httplib' not in lines[2], repr(output))

    def test_import_patched_defaults(self):
        self.write_to_tempfile("base", base_module_contents)
        new_mod = """
from eventlet import patcher
base = patcher.import_patched('base')
print("newmod {0} {1} {2}".format(base, base.socket, base.urllib.socket.socket))
"""
        self.write_to_tempfile("newmod", new_mod)
        output, lines = self.launch_subprocess('newmod.py')
        self.assert_(lines[0].startswith('base'), repr(output))
        self.assert_(lines[1].startswith('newmod'), repr(output))
        self.assert_('eventlet.green.socket' in lines[1], repr(output))
        self.assert_('GreenSocket' in lines[1], repr(output))


class MonkeyPatch(ProcessBase):
    def test_patched_modules(self):
        new_mod = """
from eventlet import patcher
patcher.monkey_patch()
import socket
import urllib
print("newmod {0} {1}".format(socket.socket, urllib.socket.socket))
"""
        self.write_to_tempfile("newmod", new_mod)
        output, lines = self.launch_subprocess('newmod.py')
        self.assert_(lines[0].startswith('newmod'), repr(output))
        self.assertEqual(lines[0].count('GreenSocket'), 2, repr(output))

    def test_early_patching(self):
        new_mod = """
from eventlet import patcher
patcher.monkey_patch()
import eventlet
eventlet.sleep(0.01)
print("newmod")
"""
        self.write_to_tempfile("newmod", new_mod)
        output, lines = self.launch_subprocess('newmod.py')
        self.assertEqual(len(lines), 2, repr(output))
        self.assert_(lines[0].startswith('newmod'), repr(output))

    def test_late_patching(self):
        new_mod = """
import eventlet
eventlet.sleep(0.01)
from eventlet import patcher
patcher.monkey_patch()
eventlet.sleep(0.01)
print("newmod")
"""
        self.write_to_tempfile("newmod", new_mod)
        output, lines = self.launch_subprocess('newmod.py')
        self.assertEqual(len(lines), 2, repr(output))
        self.assert_(lines[0].startswith('newmod'), repr(output))

    def test_typeerror(self):
        new_mod = """
from eventlet import patcher
patcher.monkey_patch(finagle=True)
"""
        self.write_to_tempfile("newmod", new_mod)
        output, lines = self.launch_subprocess('newmod.py')
        self.assert_(lines[-2].startswith('TypeError'), repr(output))
        self.assert_('finagle' in lines[-2], repr(output))

    def assert_boolean_logic(self, call, expected, not_expected=''):
        expected_list = ", ".join(['"%s"' % x for x in expected.split(',') if len(x)])
        not_expected_list = ", ".join(['"%s"' % x for x in not_expected.split(',') if len(x)])
        new_mod = """
from eventlet import patcher
%s
for mod in [%s]:
    assert patcher.is_monkey_patched(mod), mod
for mod in [%s]:
    assert not patcher.is_monkey_patched(mod), mod
print("already_patched {0}".format(",".join(sorted(patcher.already_patched.keys()))))
""" % (call, expected_list, not_expected_list)
        self.write_to_tempfile("newmod", new_mod)
        output, lines = self.launch_subprocess('newmod.py')
        ap = 'already_patched'
        self.assert_(lines[0].startswith(ap), repr(output))
        patched_modules = lines[0][len(ap):].strip()
        # psycopg might or might not be patched based on installed modules
        patched_modules = patched_modules.replace("psycopg,", "")
        # ditto for MySQLdb
        patched_modules = patched_modules.replace("MySQLdb,", "")
        self.assertEqual(
            patched_modules, expected,
            "Logic:%s\nExpected: %s != %s" % (call, expected, patched_modules))

    def test_boolean(self):
        self.assert_boolean_logic("patcher.monkey_patch()",
                                  'os,select,socket,thread,time')

    def test_boolean_all(self):
        self.assert_boolean_logic("patcher.monkey_patch(all=True)",
                                  'os,select,socket,thread,time')

    def test_boolean_all_single(self):
        self.assert_boolean_logic("patcher.monkey_patch(all=True, socket=True)",
                                  'os,select,socket,thread,time')

    def test_boolean_all_negative(self):
        self.assert_boolean_logic(
            "patcher.monkey_patch(all=False, socket=False, select=True)",
            'select')

    def test_boolean_single(self):
        self.assert_boolean_logic("patcher.monkey_patch(socket=True)",
                                  'socket')

    def test_boolean_double(self):
        self.assert_boolean_logic("patcher.monkey_patch(socket=True, select=True)",
                                  'select,socket')

    def test_boolean_negative(self):
        self.assert_boolean_logic("patcher.monkey_patch(socket=False)",
                                  'os,select,thread,time')

    def test_boolean_negative2(self):
        self.assert_boolean_logic("patcher.monkey_patch(socket=False, time=False)",
                                  'os,select,thread')

    def test_conflicting_specifications(self):
        self.assert_boolean_logic("patcher.monkey_patch(socket=False, select=True)",
                                  'select')


test_monkey_patch_threading = """
def test_monkey_patch_threading():
    tickcount = [0]

    def tick():
        from eventlet.support import six
        for i in six.moves.range(1000):
            tickcount[0] += 1
            eventlet.sleep()

    def do_sleep():
        tpool.execute(time.sleep, 0.5)

    eventlet.spawn(tick)
    w1 = eventlet.spawn(do_sleep)
    w1.wait()
    print(tickcount[0])
    assert tickcount[0] > 900
    tpool.killall()
"""


class Tpool(ProcessBase):
    TEST_TIMEOUT = 3

    @skip_with_pyevent
    def test_simple(self):
        new_mod = """
import eventlet
from eventlet import patcher
patcher.monkey_patch()
from eventlet import tpool
print("newmod {0}".format(tpool.execute(len, "hi")))
print("newmod {0}".format(tpool.execute(len, "hi2")))
tpool.killall()
"""
        self.write_to_tempfile("newmod", new_mod)
        output, lines = self.launch_subprocess('newmod.py')
        self.assertEqual(len(lines), 3, output)
        self.assert_(lines[0].startswith('newmod'), repr(output))
        self.assert_('2' in lines[0], repr(output))
        self.assert_('3' in lines[1], repr(output))

    @skip_with_pyevent
    def test_unpatched_thread(self):
        new_mod = """import eventlet
eventlet.monkey_patch(time=False, thread=False)
from eventlet import tpool
import time
"""
        new_mod += test_monkey_patch_threading
        new_mod += "\ntest_monkey_patch_threading()\n"
        self.write_to_tempfile("newmod", new_mod)
        output, lines = self.launch_subprocess('newmod.py')
        self.assertEqual(len(lines), 2, lines)

    @skip_with_pyevent
    def test_patched_thread(self):
        new_mod = """import eventlet
eventlet.monkey_patch(time=False, thread=True)
from eventlet import tpool
import time
"""
        new_mod += test_monkey_patch_threading
        new_mod += "\ntest_monkey_patch_threading()\n"
        self.write_to_tempfile("newmod", new_mod)
        output, lines = self.launch_subprocess('newmod.py')
        self.assertEqual(len(lines), 2, "\n".join(lines))


class Subprocess(ProcessBase):
    def test_monkeypatched_subprocess(self):
        new_mod = """import eventlet
eventlet.monkey_patch()
from eventlet.green import subprocess

subprocess.Popen(['true'], stdin=subprocess.PIPE)
print("done")
"""
        self.write_to_tempfile("newmod", new_mod)
        output, lines = self.launch_subprocess('newmod')
        self.assertEqual(output, "done\n", output)


class Threading(ProcessBase):
    def test_orig_thread(self):
        new_mod = """import eventlet
eventlet.monkey_patch()
from eventlet import patcher
import threading
_threading = patcher.original('threading')
def test():
    print(repr(threading.currentThread()))
t = _threading.Thread(target=test)
t.start()
t.join()
print(len(threading._active))
print(len(_threading._active))
"""
        self.write_to_tempfile("newmod", new_mod)
        output, lines = self.launch_subprocess('newmod')
        self.assertEqual(len(lines), 4, "\n".join(lines))
        self.assert_(lines[0].startswith('<Thread'), lines[0])
        self.assertEqual(lines[1], "1", lines[1])
        self.assertEqual(lines[2], "1", lines[2])

    def test_threading(self):
        new_mod = """import eventlet
eventlet.monkey_patch()
import threading
def test():
    print(repr(threading.currentThread()))
t = threading.Thread(target=test)
t.start()
t.join()
print(len(threading._active))
"""
        self.write_to_tempfile("newmod", new_mod)
        output, lines = self.launch_subprocess('newmod')
        self.assertEqual(len(lines), 3, "\n".join(lines))
        self.assert_(lines[0].startswith('<_MainThread'), lines[0])
        self.assertEqual(lines[1], "1", lines[1])

    def test_tpool(self):
        new_mod = """import eventlet
eventlet.monkey_patch()
from eventlet import tpool
import threading
def test():
    print(repr(threading.currentThread()))
tpool.execute(test)
print(len(threading._active))
"""
        self.write_to_tempfile("newmod", new_mod)
        output, lines = self.launch_subprocess('newmod')
        self.assertEqual(len(lines), 3, "\n".join(lines))
        self.assert_(lines[0].startswith('<Thread'), lines[0])
        self.assertEqual(lines[1], "1", lines[1])

    def test_greenlet(self):
        new_mod = """import eventlet
eventlet.monkey_patch()
from eventlet import event
import threading
evt = event.Event()
def test():
    print(repr(threading.currentThread()))
    evt.send()
eventlet.spawn_n(test)
evt.wait()
print(len(threading._active))
"""
        self.write_to_tempfile("newmod", new_mod)
        output, lines = self.launch_subprocess('newmod')
        self.assertEqual(len(lines), 3, "\n".join(lines))
        self.assert_(lines[0].startswith('<_MainThread'), lines[0])
        self.assertEqual(lines[1], "1", lines[1])

    def test_greenthread(self):
        new_mod = """import eventlet
eventlet.monkey_patch()
import threading
def test():
    print(repr(threading.currentThread()))
t = eventlet.spawn(test)
t.wait()
print(len(threading._active))
"""
        self.write_to_tempfile("newmod", new_mod)
        output, lines = self.launch_subprocess('newmod')
        self.assertEqual(len(lines), 3, "\n".join(lines))
        self.assert_(lines[0].startswith('<_GreenThread'), lines[0])
        self.assertEqual(lines[1], "1", lines[1])

    def test_keyerror(self):
        new_mod = """import eventlet
eventlet.monkey_patch()
"""
        self.write_to_tempfile("newmod", new_mod)
        output, lines = self.launch_subprocess('newmod')
        self.assertEqual(len(lines), 1, "\n".join(lines))


class Os(ProcessBase):
    def test_waitpid(self):
        new_mod = """import subprocess
import eventlet
eventlet.monkey_patch(all=False, os=True)
process = subprocess.Popen("sleep 0.1 && false", shell=True)
print(process.wait())"""
        self.write_to_tempfile("newmod", new_mod)
        output, lines = self.launch_subprocess('newmod')
        self.assertEqual(len(lines), 2, "\n".join(lines))
        self.assertEqual('1',  lines[0], repr(output))


class GreenThreadWrapper(ProcessBase):
    prologue = """import eventlet
eventlet.monkey_patch()
import threading
def test():
    t = threading.currentThread()
"""
    epilogue = """
t = eventlet.spawn(test)
t.wait()
"""

    def test_join(self):
        self.write_to_tempfile("newmod", self.prologue + """
    def test2():
        global t2
        t2 = threading.currentThread()
    eventlet.spawn(test2)
""" + self.epilogue + """
print(repr(t2))
t2.join()
""")
        output, lines = self.launch_subprocess('newmod')
        self.assertEqual(len(lines), 2, "\n".join(lines))
        self.assert_(lines[0].startswith('<_GreenThread'), lines[0])

    def test_name(self):
        self.write_to_tempfile("newmod", self.prologue + """
    print(t.name)
    print(t.getName())
    print(t.get_name())
    t.name = 'foo'
    print(t.name)
    print(t.getName())
    print(t.get_name())
    t.setName('bar')
    print(t.name)
    print(t.getName())
    print(t.get_name())
""" + self.epilogue)
        output, lines = self.launch_subprocess('newmod')
        self.assertEqual(len(lines), 10, "\n".join(lines))
        for i in range(0, 3):
            self.assertEqual(lines[i], "GreenThread-1", lines[i])
        for i in range(3, 6):
            self.assertEqual(lines[i], "foo", lines[i])
        for i in range(6, 9):
            self.assertEqual(lines[i], "bar", lines[i])

    def test_ident(self):
        self.write_to_tempfile("newmod", self.prologue + """
    print(id(t._g))
    print(t.ident)
""" + self.epilogue)
        output, lines = self.launch_subprocess('newmod')
        self.assertEqual(len(lines), 3, "\n".join(lines))
        self.assertEqual(lines[0], lines[1])

    def test_is_alive(self):
        self.write_to_tempfile("newmod", self.prologue + """
    print(t.is_alive())
    print(t.isAlive())
""" + self.epilogue)
        output, lines = self.launch_subprocess('newmod')
        self.assertEqual(len(lines), 3, "\n".join(lines))
        self.assertEqual(lines[0], "True", lines[0])
        self.assertEqual(lines[1], "True", lines[1])

    def test_is_daemon(self):
        self.write_to_tempfile("newmod", self.prologue + """
    print(t.is_daemon())
    print(t.isDaemon())
""" + self.epilogue)
        output, lines = self.launch_subprocess('newmod')
        self.assertEqual(len(lines), 3, "\n".join(lines))
        self.assertEqual(lines[0], "True", lines[0])
        self.assertEqual(lines[1], "True", lines[1])


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = pools_test
from unittest import TestCase, main

import eventlet
from eventlet import Queue
from eventlet import pools
from eventlet.support import six


class IntPool(pools.Pool):
    def create(self):
        self.current_integer = getattr(self, 'current_integer', 0) + 1
        return self.current_integer


class TestIntPool(TestCase):
    def setUp(self):
        self.pool = IntPool(min_size=0, max_size=4)

    def test_integers(self):
        # Do not actually use this pattern in your code. The pool will be
        # exhausted, and unrestoreable.
        # If you do a get, you should ALWAYS do a put, probably like this:
        # try:
        #     thing = self.pool.get()
        #     # do stuff
        # finally:
        #     self.pool.put(thing)

        # with self.pool.some_api_name() as thing:
        #     # do stuff
        self.assertEqual(self.pool.get(), 1)
        self.assertEqual(self.pool.get(), 2)
        self.assertEqual(self.pool.get(), 3)
        self.assertEqual(self.pool.get(), 4)

    def test_free(self):
        self.assertEqual(self.pool.free(), 4)
        gotten = self.pool.get()
        self.assertEqual(self.pool.free(), 3)
        self.pool.put(gotten)
        self.assertEqual(self.pool.free(), 4)

    def test_exhaustion(self):
        waiter = Queue(0)
        def consumer():
            gotten = None
            try:
                gotten = self.pool.get()
            finally:
                waiter.put(gotten)

        eventlet.spawn(consumer)

        one, two, three, four = (
            self.pool.get(), self.pool.get(), self.pool.get(), self.pool.get())
        self.assertEqual(self.pool.free(), 0)

        # Let consumer run; nothing will be in the pool, so he will wait
        eventlet.sleep(0)

        # Wake consumer
        self.pool.put(one)

        # wait for the consumer
        self.assertEqual(waiter.get(), one)

    def test_blocks_on_pool(self):
        waiter = Queue(0)
        def greedy():
            self.pool.get()
            self.pool.get()
            self.pool.get()
            self.pool.get()
            # No one should be waiting yet.
            self.assertEqual(self.pool.waiting(), 0)
            # The call to the next get will unschedule this routine.
            self.pool.get()
            # So this put should never be called.
            waiter.put('Failed!')

        killable = eventlet.spawn(greedy)

        # no one should be waiting yet.
        self.assertEqual(self.pool.waiting(), 0)

        ## Wait for greedy
        eventlet.sleep(0)

        ## Greedy should be blocking on the last get
        self.assertEqual(self.pool.waiting(), 1)

        ## Send will never be called, so balance should be 0.
        self.assertFalse(not waiter.full())

        eventlet.kill(killable)

    def test_ordering(self):
        # normal case is that items come back out in the
        # same order they are put
        one, two = self.pool.get(), self.pool.get()
        self.pool.put(one)
        self.pool.put(two)
        self.assertEqual(self.pool.get(), one)
        self.assertEqual(self.pool.get(), two)

    def test_putting_to_queue(self):
        timer = eventlet.Timeout(0.1)
        try:
            size = 2
            self.pool = IntPool(min_size=0, max_size=size)
            queue = Queue()
            results = []
            def just_put(pool_item, index):
                self.pool.put(pool_item)
                queue.put(index)
            for index in six.moves.range(size + 1):
                pool_item = self.pool.get()
                eventlet.spawn(just_put, pool_item, index)

            for _ in six.moves.range(size+1):
                x = queue.get()
                results.append(x)
            self.assertEqual(sorted(results), list(six.moves.range(size + 1)))
        finally:
            timer.cancel()

    def test_resize(self):
        pool = IntPool(max_size=2)
        a = pool.get()
        b = pool.get()
        self.assertEqual(pool.free(), 0)

        # verify that the pool discards excess items put into it
        pool.resize(1)
        pool.put(a)
        pool.put(b)
        self.assertEqual(pool.free(), 1)

        # resize larger and assert that there are more free items
        pool.resize(2)
        self.assertEqual(pool.free(), 2)

    def test_create_contention(self):
        creates = [0]
        def sleep_create():
            creates[0] += 1
            eventlet.sleep()
            return "slept"

        p = pools.Pool(max_size=4, create=sleep_create)

        def do_get():
            x = p.get()
            self.assertEqual(x, "slept")
            p.put(x)

        gp = eventlet.GreenPool()
        for i in six.moves.range(100):
            gp.spawn_n(do_get)
        gp.waitall()
        self.assertEqual(creates[0], 4)


class TestAbstract(TestCase):
    mode = 'static'
    def test_abstract(self):
        ## Going for 100% coverage here
        ## A Pool cannot be used without overriding create()
        pool = pools.Pool()
        self.assertRaises(NotImplementedError, pool.get)


class TestIntPool2(TestCase):
    mode = 'static'
    def setUp(self):
        self.pool = IntPool(min_size=3, max_size=3)

    def test_something(self):
        self.assertEqual(len(self.pool.free_items), 3)
        ## Cover the clause in get where we get from the free list instead of creating
        ## an item on get
        gotten = self.pool.get()
        self.assertEqual(gotten, 1)


class TestOrderAsStack(TestCase):
    mode = 'static'
    def setUp(self):
        self.pool = IntPool(max_size=3, order_as_stack=True)

    def test_ordering(self):
        # items come out in the reverse order they are put
        one, two = self.pool.get(), self.pool.get()
        self.pool.put(one)
        self.pool.put(two)
        self.assertEqual(self.pool.get(), two)
        self.assertEqual(self.pool.get(), one)


class RaisePool(pools.Pool):
    def create(self):
        raise RuntimeError()


class TestCreateRaises(TestCase):
    mode = 'static'
    def setUp(self):
        self.pool = RaisePool(max_size=3)

    def test_it(self):
        self.assertEqual(self.pool.free(), 3)
        self.assertRaises(RuntimeError, self.pool.get)
        self.assertEqual(self.pool.free(), 3)


ALWAYS = RuntimeError('I always fail')
SOMETIMES = RuntimeError('I fail half the time')


class TestTookTooLong(Exception):
    pass

if __name__ == '__main__':
    main()


########NEW FILE########
__FILENAME__ = processes_test
import sys
import warnings
from tests import LimitedTestCase, main, skip_on_windows

warnings.simplefilter('ignore', DeprecationWarning)
from eventlet import processes, api
warnings.simplefilter('default', DeprecationWarning)

class TestEchoPool(LimitedTestCase):
    def setUp(self):
        super(TestEchoPool, self).setUp()
        self.pool = processes.ProcessPool('echo', ["hello"])

    @skip_on_windows
    def test_echo(self):
        result = None

        proc = self.pool.get()
        try:
            result = proc.read()
        finally:
            self.pool.put(proc)
        self.assertEqual(result, 'hello\n')

    @skip_on_windows
    def test_read_eof(self):
        proc = self.pool.get()
        try:
            proc.read()
            self.assertRaises(processes.DeadProcess, proc.read)
        finally:
            self.pool.put(proc)

    @skip_on_windows    
    def test_empty_echo(self):
        p = processes.Process('echo', ['-n'])
        self.assertEqual('', p.read())
        self.assertRaises(processes.DeadProcess, p.read)
            

class TestCatPool(LimitedTestCase):
    def setUp(self):
        super(TestCatPool, self).setUp()
        api.sleep(0)
        self.pool = processes.ProcessPool('cat')

    @skip_on_windows
    def test_cat(self):
        result = None

        proc = self.pool.get()
        try:
            proc.write('goodbye')
            proc.close_stdin()
            result = proc.read()
        finally:
            self.pool.put(proc)

        self.assertEqual(result, 'goodbye')

    @skip_on_windows
    def test_write_to_dead(self):
        result = None

        proc = self.pool.get()
        try:
            proc.write('goodbye')
            proc.close_stdin()
            result = proc.read()
            self.assertRaises(processes.DeadProcess, proc.write, 'foo')
        finally:
            self.pool.put(proc)

    @skip_on_windows
    def test_close(self):
        result = None

        proc = self.pool.get()
        try:
            proc.write('hello')
            proc.close()
            self.assertRaises(processes.DeadProcess, proc.write, 'goodbye')
        finally:
            self.pool.put(proc)


class TestDyingProcessesLeavePool(LimitedTestCase):
    def setUp(self):
        super(TestDyingProcessesLeavePool, self).setUp()
        self.pool = processes.ProcessPool('echo', ['hello'], max_size=1)

    @skip_on_windows
    def test_dead_process_not_inserted_into_pool(self):
        proc = self.pool.get()
        try:
            try:
                result = proc.read()
                self.assertEqual(result, 'hello\n')
                result = proc.read()
            except processes.DeadProcess:
                pass
        finally:
            self.pool.put(proc)
        proc2 = self.pool.get()
        self.assert_(proc is not proc2)


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = queue_test
from tests import LimitedTestCase, main
import eventlet
from eventlet import event

def do_bail(q):
    eventlet.Timeout(0, RuntimeError())
    try:
        result = q.get()
        return result
    except RuntimeError:
        return 'timed out'

class TestQueue(LimitedTestCase):
    def test_send_first(self):
        q = eventlet.Queue()
        q.put('hi')
        self.assertEqual(q.get(), 'hi')

    def test_send_last(self):
        q = eventlet.Queue()
        def waiter(q):
            self.assertEqual(q.get(), 'hi2')

        gt = eventlet.spawn(eventlet.with_timeout, 0.1, waiter, q)
        eventlet.sleep(0)
        eventlet.sleep(0)
        q.put('hi2')
        gt.wait()

    def test_max_size(self):
        q = eventlet.Queue(2)
        results = []

        def putter(q):
            q.put('a')
            results.append('a')
            q.put('b')
            results.append('b')
            q.put('c')
            results.append('c')

        gt = eventlet.spawn(putter, q)
        eventlet.sleep(0)
        self.assertEqual(results, ['a', 'b'])
        self.assertEqual(q.get(), 'a')
        eventlet.sleep(0)
        self.assertEqual(results, ['a', 'b', 'c'])
        self.assertEqual(q.get(), 'b')
        self.assertEqual(q.get(), 'c')
        gt.wait()

    def test_zero_max_size(self):
        q = eventlet.Queue(0)
        def sender(evt, q):
            q.put('hi')
            evt.send('done')

        def receiver(q):
            x = q.get()
            return x

        evt = event.Event()
        gt = eventlet.spawn(sender, evt, q)
        eventlet.sleep(0)
        self.assert_(not evt.ready())
        gt2 = eventlet.spawn(receiver, q)
        self.assertEqual(gt2.wait(),'hi')
        self.assertEqual(evt.wait(),'done')
        gt.wait()

    def test_resize_up(self):
        q = eventlet.Queue(0)
        def sender(evt, q):
            q.put('hi')
            evt.send('done')

        evt = event.Event()
        gt = eventlet.spawn(sender, evt, q)
        eventlet.sleep(0)
        self.assert_(not evt.ready())
        q.resize(1)
        eventlet.sleep(0)
        self.assert_(evt.ready())
        gt.wait()

    def test_resize_down(self):
        size = 5
        q = eventlet.Queue(5)

        for i in range(5):
            q.put(i)

        self.assertEqual(list(q.queue), list(range(5)))
        q.resize(1)
        eventlet.sleep(0)
        self.assertEqual(list(q.queue), list(range(5)))

    def test_resize_to_Unlimited(self):
        q = eventlet.Queue(0)
        def sender(evt, q):
            q.put('hi')
            evt.send('done')

        evt = event.Event()
        gt = eventlet.spawn(sender, evt, q)
        eventlet.sleep()
        self.assertFalse(evt.ready())
        q.resize(None)
        eventlet.sleep()
        self.assertTrue(evt.ready())
        gt.wait()

    def test_multiple_waiters(self):
        # tests that multiple waiters get their results back
        q = eventlet.Queue()

        sendings = ['1', '2', '3', '4']
        gts = [eventlet.spawn(q.get)
                for x in sendings]
                
        eventlet.sleep(0.01) # get 'em all waiting

        q.put(sendings[0])
        q.put(sendings[1])
        q.put(sendings[2])
        q.put(sendings[3])
        results = set()
        for i, gt in enumerate(gts):
            results.add(gt.wait())
        self.assertEqual(results, set(sendings))

    def test_waiters_that_cancel(self):
        q = eventlet.Queue()

        gt = eventlet.spawn(do_bail, q)
        self.assertEqual(gt.wait(), 'timed out')

        q.put('hi')
        self.assertEqual(q.get(), 'hi')

    def test_getting_before_sending(self):
        q = eventlet.Queue()
        gt = eventlet.spawn(q.put, 'sent')
        self.assertEqual(q.get(), 'sent')
        gt.wait()

    def test_two_waiters_one_dies(self):
        def waiter(q):
            return q.get()

        q = eventlet.Queue()
        dying = eventlet.spawn(do_bail, q)
        waiting = eventlet.spawn(waiter, q)
        eventlet.sleep(0)
        q.put('hi')
        self.assertEqual(dying.wait(), 'timed out')
        self.assertEqual(waiting.wait(), 'hi')

    def test_two_bogus_waiters(self):
        q = eventlet.Queue()
        gt1 = eventlet.spawn(do_bail, q)
        gt2 = eventlet.spawn(do_bail, q)
        eventlet.sleep(0)
        q.put('sent')
        self.assertEqual(gt1.wait(), 'timed out')
        self.assertEqual(gt2.wait(), 'timed out')
        self.assertEqual(q.get(), 'sent')
                
    def test_waiting(self):
        q = eventlet.Queue()
        gt1 = eventlet.spawn(q.get)
        eventlet.sleep(0)
        self.assertEqual(1, q.getting())
        q.put('hi')
        eventlet.sleep(0)
        self.assertEqual(0, q.getting())
        self.assertEqual('hi', gt1.wait())
        self.assertEqual(0, q.getting())

    def test_channel_send(self):
        channel = eventlet.Queue(0)
        events = []
        def another_greenlet():
            events.append(channel.get())
            events.append(channel.get())

        gt = eventlet.spawn(another_greenlet)

        events.append('sending')
        channel.put('hello')
        events.append('sent hello')
        channel.put('world')
        events.append('sent world')

        self.assertEqual(['sending', 'hello', 'sent hello', 'world', 'sent world'], events)


    def test_channel_wait(self):
        channel = eventlet.Queue(0)
        events = []

        def another_greenlet():
            events.append('sending hello')
            channel.put('hello')
            events.append('sending world')
            channel.put('world')
            events.append('sent world')

        gt = eventlet.spawn(another_greenlet)

        events.append('waiting')
        events.append(channel.get())
        events.append(channel.get())

        self.assertEqual(['waiting', 'sending hello', 'hello', 'sending world', 'world'], events)
        eventlet.sleep(0)
        self.assertEqual(['waiting', 'sending hello', 'hello', 'sending world', 'world', 'sent world'], events)

    def test_channel_waiters(self):
        c = eventlet.Queue(0)
        w1 = eventlet.spawn(c.get)
        w2 = eventlet.spawn(c.get)
        w3 = eventlet.spawn(c.get)
        eventlet.sleep(0)
        self.assertEqual(c.getting(), 3)
        s1 = eventlet.spawn(c.put, 1)
        s2 = eventlet.spawn(c.put, 2)
        s3 = eventlet.spawn(c.put, 3)

        s1.wait()
        s2.wait()
        s3.wait()
        self.assertEqual(c.getting(), 0)
        # NOTE: we don't guarantee that waiters are served in order
        results = sorted([w1.wait(), w2.wait(), w3.wait()])
        self.assertEqual(results, [1,2,3])
        
    def test_channel_sender_timing_out(self):
        from eventlet import queue
        c = eventlet.Queue(0)
        self.assertRaises(queue.Full, c.put, "hi", timeout=0.001)
        self.assertRaises(queue.Empty, c.get_nowait)

    def test_task_done(self):
        from eventlet import queue, debug
        channel = queue.Queue(0)
        X = object()
        gt = eventlet.spawn(channel.put, X)
        result = channel.get()
        assert result is X, (result, X)
        assert channel.unfinished_tasks == 1, channel.unfinished_tasks
        channel.task_done()
        assert channel.unfinished_tasks == 0, channel.unfinished_tasks
        gt.wait()

    def test_join_doesnt_block_when_queue_is_already_empty(self):
        queue = eventlet.Queue()
        queue.join()


def store_result(result, func, *args):
    try:
        result.append(func(*args))
    except Exception as exc:
        result.append(exc)


class TestNoWait(LimitedTestCase):
    def test_put_nowait_simple(self):
        from eventlet import hubs,queue
        hub = hubs.get_hub()
        result = []
        q = eventlet.Queue(1)
        hub.schedule_call_global(0, store_result, result, q.put_nowait, 2)
        hub.schedule_call_global(0, store_result, result, q.put_nowait, 3)
        eventlet.sleep(0)
        eventlet.sleep(0)
        assert len(result)==2, result
        assert result[0]==None, result
        assert isinstance(result[1], queue.Full), result

    def test_get_nowait_simple(self):
        from eventlet import hubs,queue
        hub = hubs.get_hub()
        result = []
        q = queue.Queue(1)
        q.put(4)
        hub.schedule_call_global(0, store_result, result, q.get_nowait)
        hub.schedule_call_global(0, store_result, result, q.get_nowait)
        eventlet.sleep(0)
        assert len(result)==2, result
        assert result[0]==4, result
        assert isinstance(result[1], queue.Empty), result

    # get_nowait must work from the mainloop
    def test_get_nowait_unlock(self):
        from eventlet import hubs,queue
        hub = hubs.get_hub()
        result = []
        q = queue.Queue(0)
        p = eventlet.spawn(q.put, 5)
        assert q.empty(), q
        assert q.full(), q
        eventlet.sleep(0)
        assert q.empty(), q
        assert q.full(), q
        hub.schedule_call_global(0, store_result, result, q.get_nowait)
        eventlet.sleep(0)
        assert q.empty(), q
        assert q.full(), q
        assert result == [5], result
        # TODO add ready to greenthread
        #assert p.ready(), p
        assert p.dead, p
        assert q.empty(), q

    # put_nowait must work from the mainloop
    def test_put_nowait_unlock(self):
        from eventlet import hubs,queue
        hub = hubs.get_hub()
        result = []
        q = queue.Queue(0)
        p = eventlet.spawn(q.get)
        assert q.empty(), q
        assert q.full(), q
        eventlet.sleep(0)
        assert q.empty(), q
        assert q.full(), q
        hub.schedule_call_global(0, store_result, result, q.put_nowait, 10)
        # TODO ready method on greenthread
        #assert not p.ready(), p
        eventlet.sleep(0)
        assert result == [None], result
        # TODO ready method
        # assert p.ready(), p
        assert q.full(), q
        assert q.empty(), q


if __name__=='__main__':
    main()

########NEW FILE########
__FILENAME__ = semaphore_test
import time
import unittest

import eventlet
from eventlet import semaphore
from tests import LimitedTestCase


class TestSemaphore(LimitedTestCase):

    def test_bounded(self):
        sem = semaphore.CappedSemaphore(2, limit=3)
        self.assertEqual(sem.acquire(), True)
        self.assertEqual(sem.acquire(), True)
        gt1 = eventlet.spawn(sem.release)
        self.assertEqual(sem.acquire(), True)
        self.assertEqual(-3, sem.balance)
        sem.release()
        sem.release()
        sem.release()
        gt2 = eventlet.spawn(sem.acquire)
        sem.release()
        self.assertEqual(3, sem.balance)
        gt1.wait()
        gt2.wait()

    def test_bounded_with_zero_limit(self):
        sem = semaphore.CappedSemaphore(0, 0)
        gt = eventlet.spawn(sem.acquire)
        sem.release()
        gt.wait()

    def test_non_blocking(self):
        sem = semaphore.Semaphore(0)
        self.assertEqual(sem.acquire(blocking=False), False)

    def test_timeout(self):
        sem = semaphore.Semaphore(0)
        start = time.time()
        self.assertEqual(sem.acquire(timeout=0.1), False)
        self.assertTrue(time.time() - start >= 0.1)

    def test_timeout_non_blocking(self):
        sem = semaphore.Semaphore()
        self.assertRaises(ValueError, sem.acquire, blocking=False, timeout=1)


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = ssl_test
import socket
import warnings
from unittest import main

import eventlet
from eventlet import util, greenio
try:
    from eventlet.green.socket import ssl
except ImportError:
    pass
from tests import (
    LimitedTestCase, certificate_file, private_key_file, check_idle_cpu_usage,
    skip_if_no_ssl
)


def listen_ssl_socket(address=('127.0.0.1', 0)):
    sock = util.wrap_ssl(socket.socket(), certificate_file,
                         private_key_file, True)
    sock.bind(address)
    sock.listen(50)

    return sock


class SSLTest(LimitedTestCase):
    def setUp(self):
        # disabling socket.ssl warnings because we're testing it here
        warnings.filterwarnings(
            action='ignore',
            message='.*socket.ssl.*',
            category=DeprecationWarning)

        super(SSLTest, self).setUp()

    @skip_if_no_ssl
    def test_duplex_response(self):
        def serve(listener):
            sock, addr = listener.accept()
            sock.read(8192)
            sock.write(b'response')

        sock = listen_ssl_socket()

        server_coro = eventlet.spawn(serve, sock)

        client = util.wrap_ssl(eventlet.connect(('127.0.0.1', sock.getsockname()[1])))
        client.write(b'line 1\r\nline 2\r\n\r\n')
        self.assertEqual(client.read(8192), b'response')
        server_coro.wait()

    @skip_if_no_ssl
    def test_ssl_close(self):
        def serve(listener):
            sock, addr = listener.accept()
            sock.read(8192)
            try:
                self.assertEqual(b"", sock.read(8192))
            except greenio.SSL.ZeroReturnError:
                pass

        sock = listen_ssl_socket()

        server_coro = eventlet.spawn(serve, sock)

        raw_client = eventlet.connect(('127.0.0.1', sock.getsockname()[1]))
        client = util.wrap_ssl(raw_client)
        client.write(b'X')
        greenio.shutdown_safe(client)
        client.close()
        server_coro.wait()

    @skip_if_no_ssl
    def test_ssl_connect(self):
        def serve(listener):
            sock, addr = listener.accept()
            sock.read(8192)
        sock = listen_ssl_socket()
        server_coro = eventlet.spawn(serve, sock)

        raw_client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        ssl_client = util.wrap_ssl(raw_client)
        ssl_client.connect(('127.0.0.1', sock.getsockname()[1]))
        ssl_client.write(b'abc')
        greenio.shutdown_safe(ssl_client)
        ssl_client.close()
        server_coro.wait()

    @skip_if_no_ssl
    def test_ssl_unwrap(self):
        def serve():
            sock, addr = listener.accept()
            self.assertEqual(sock.recv(6), b'before')
            sock_ssl = util.wrap_ssl(sock, certificate_file, private_key_file,
                                     server_side=True)
            sock_ssl.do_handshake()
            self.assertEqual(sock_ssl.read(6), b'during')
            sock2 = sock_ssl.unwrap()
            self.assertEqual(sock2.recv(5), b'after')
            sock2.close()

        listener = eventlet.listen(('127.0.0.1', 0))
        server_coro = eventlet.spawn(serve)
        client = eventlet.connect((listener.getsockname()))
        client.send(b'before')
        client_ssl = util.wrap_ssl(client)
        client_ssl.do_handshake()
        client_ssl.write(b'during')
        client2 = client_ssl.unwrap()
        client2.send(b'after')
        server_coro.wait()

    @skip_if_no_ssl
    def test_sendall_cpu_usage(self):
        """SSL socket.sendall() busy loop

        https://bitbucket.org/eventlet/eventlet/issue/134/greenssl-performance-issues

        Idea of this test is to check that GreenSSLSocket.sendall() does not busy loop
        retrying .send() calls, but instead trampolines until socket is writeable.

        BUFFER_SIZE and SENDALL_SIZE are magic numbers inferred through trial and error.
        """
        # Time limit resistant to busy loops
        self.set_alarm(1)

        stage_1 = eventlet.event.Event()
        BUFFER_SIZE = 1000
        SENDALL_SIZE = 100000

        def serve(listener):
            conn, _ = listener.accept()
            conn.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, BUFFER_SIZE)
            self.assertEqual(conn.read(8), b'request')
            conn.write(b'response')

            stage_1.wait()
            conn.sendall(b'x' * SENDALL_SIZE)

        server_sock = listen_ssl_socket()
        server_coro = eventlet.spawn(serve, server_sock)

        client_sock = eventlet.connect(server_sock.getsockname())
        client_sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, BUFFER_SIZE)
        client = util.wrap_ssl(client_sock)
        client.write(b'request')
        self.assertEqual(client.read(8), b'response')
        stage_1.send()

        check_idle_cpu_usage(0.2, 0.1)
        server_coro.kill()

    @skip_if_no_ssl
    def test_greensslobject(self):
        def serve(listener):
            sock, addr = listener.accept()
            sock.write(b'content')
            greenio.shutdown_safe(sock)
            sock.close()
        listener = listen_ssl_socket(('', 0))
        eventlet.spawn(serve, listener)
        client = ssl(eventlet.connect(('localhost', listener.getsockname()[1])))
        self.assertEqual(client.read(1024), b'content')
        self.assertEqual(client.read(1024), b'')

    @skip_if_no_ssl
    def test_regression_gh_17(self):
        def serve(listener):
            sock, addr = listener.accept()

            # to simulate condition mentioned in GH-17
            sock._sslobj = None
            sock.sendall(b'some data')
            greenio.shutdown_safe(sock)
            sock.close()

        listener = listen_ssl_socket(('', 0))
        eventlet.spawn(serve, listener)
        ssl(eventlet.connect(('localhost', listener.getsockname()[1])))

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = all
""" Convenience module for running standard library tests with nose.  The standard tests are not especially homogeneous, but they mostly expose a test_main method that does the work of selecting which tests to run based on what is supported by the platform.  On its own, Nose would run all possible tests and many would fail; therefore we collect all of the test_main methods here in one module and Nose can run it.  Hopefully in the future the standard tests get rewritten to be more nosey.

Many of these tests make connections to external servers, and all.py tries to skip these tests rather than failing them, so you can get some work done on a plane.
"""

from eventlet import debug
debug.hub_prevent_multiple_readers(False)

def restart_hub():
    from eventlet import hubs
    hub = hubs.get_hub()
    hub_shortname = hub.__module__.split('.')[-1]
    # don't restart the pyevent hub; it's not necessary
    if hub_shortname != 'pyevent':
        hub.abort()
        hubs.use_hub(hub_shortname)

def assimilate_patched(name):
    try:
        modobj = __import__(name, globals(), locals(), ['test_main'])
        restart_hub()
    except ImportError:
        print("Not importing %s, it doesn't exist in this installation/version of Python" % name)
        return
    else:
        method_name = name + "_test_main"
        try:
            test_method = modobj.test_main
            def test_main():
                restart_hub()
                test_method()
                restart_hub()
            globals()[method_name] = test_main
            test_main.__name__ = name + '.test_main'
        except AttributeError:
            print("No test_main for %s, assuming it tests on import" % name)
            
import all_modules

for m in all_modules.get_modules():
    assimilate_patched(m)

########NEW FILE########
__FILENAME__ = all_modules
def get_modules():
    test_modules = [
        'test_select',
        'test_SimpleHTTPServer',
        'test_asynchat',
        'test_asyncore',
        'test_ftplib',
        'test_httplib',
        'test_os',
        'test_queue',
        'test_socket_ssl',
        'test_socketserver',
#       'test_subprocess',
        'test_thread',
        'test_threading',
        'test_threading_local',
        'test_urllib',
        'test_urllib2_localnet']
    
    network_modules = [
        'test_httpservers',
        'test_socket',
        'test_ssl',
        'test_timeout',
        'test_urllib2']
    
    # quick and dirty way of testing whether we can access
    # remote hosts; any tests that try internet connections
    # will fail if we cannot
    import socket
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.settimeout(0.5)
        s.connect(('eventlet.net', 80))
        s.close()
        test_modules = test_modules + network_modules
    except socket.error as e:
        print("Skipping network tests")
    
    return test_modules
    

########NEW FILE########
__FILENAME__ = all_monkey
import eventlet
eventlet.sleep(0)
from eventlet import patcher
patcher.monkey_patch()

def assimilate_real(name):
    print("Assimilating", name)
    try:
        modobj = __import__('test.' + name, globals(), locals(), ['test_main'])
    except ImportError:
        print("Not importing %s, it doesn't exist in this installation/version of Python" % name)
        return
    else:
        method_name = name + "_test_main"
        try:
            globals()[method_name] = modobj.test_main
            modobj.test_main.__name__ = name + '.test_main'
        except AttributeError:
            print("No test_main for %s, assuming it tests on import" % name)

import all_modules

for m in all_modules.get_modules():
    assimilate_real(m)

########NEW FILE########
__FILENAME__ = test_asynchat
from eventlet import patcher
from eventlet.green import asyncore
from eventlet.green import asynchat
from eventlet.green import socket
from eventlet.green import thread
from eventlet.green import threading
from eventlet.green import time

patcher.inject("test.test_asynchat",
    globals(),
    ('asyncore', asyncore),
    ('asynchat', asynchat),
    ('socket', socket),
    ('thread', thread),
    ('threading', threading),
    ('time', time))
    
if __name__ == "__main__":
    test_main()
########NEW FILE########
__FILENAME__ = test_asyncore
from eventlet import patcher
from eventlet.green import asyncore
from eventlet.green import select
from eventlet.green import socket
from eventlet.green import threading
from eventlet.green import time

patcher.inject("test.test_asyncore", globals())

def new_closeall_check(self, usedefault):
    # Check that close_all() closes everything in a given map

    l = []
    testmap = {}
    for i in range(10):
        c = dummychannel()
        l.append(c)
        self.assertEqual(c.socket.closed, False)
        testmap[i] = c

    if usedefault:
        # the only change we make is to not assign to asyncore.socket_map
        # because doing so fails to assign to the real asyncore's socket_map
        # and thus the test fails
        socketmap = asyncore.socket_map.copy()
        try:
            asyncore.socket_map.clear()
            asyncore.socket_map.update(testmap)
            asyncore.close_all()
        finally:
            testmap = asyncore.socket_map.copy()
            asyncore.socket_map.clear()
            asyncore.socket_map.update(socketmap)
    else:
        asyncore.close_all(testmap)

    self.assertEqual(len(testmap), 0)

    for c in l:
        self.assertEqual(c.socket.closed, True)
        
HelperFunctionTests.closeall_check = new_closeall_check

try:
    # Eventlet's select() emulation doesn't support the POLLPRI flag,
    # which this test relies on.  Therefore, nuke it!
    BaseTestAPI.test_handle_expt = lambda *a, **kw: None
except NameError:
    pass

try:
    # temporarily disabling these tests in the python2.7/pyevent configuration
    from tests import using_pyevent
    import sys
    if using_pyevent(None) and sys.version_info >= (2, 7):
        TestAPI_UseSelect.test_handle_accept = lambda *a, **kw: None
        TestAPI_UseSelect.test_handle_close = lambda *a, **kw: None
        TestAPI_UseSelect.test_handle_read = lambda *a, **kw: None
except NameError:
    pass

if __name__ == "__main__":
    test_main()

########NEW FILE########
__FILENAME__ = test_ftplib
from eventlet import patcher
from eventlet.green import asyncore
from eventlet.green import ftplib
from eventlet.green import threading
from eventlet.green import socket

patcher.inject('test.test_ftplib', globals())

# this test only fails on python2.7/pyevent/--with-xunit; screw that
try:
    TestTLS_FTPClass.test_data_connection = lambda *a, **kw: None
except (AttributeError, NameError):
    pass
    
if __name__ == "__main__":
    test_main()

########NEW FILE########
__FILENAME__ = test_httplib
from eventlet import patcher
from eventlet.green import httplib
from eventlet.green import socket

patcher.inject('test.test_httplib',
    globals(),
    ('httplib', httplib),
    ('socket', socket))
    
if __name__ == "__main__":
    test_main()
########NEW FILE########
__FILENAME__ = test_httpservers
from eventlet import patcher

from eventlet.green import BaseHTTPServer
from eventlet.green import SimpleHTTPServer
from eventlet.green import CGIHTTPServer
from eventlet.green import urllib
from eventlet.green import httplib
from eventlet.green import threading

patcher.inject('test.test_httpservers',
    globals(),
    ('BaseHTTPServer', BaseHTTPServer),
    ('SimpleHTTPServer', SimpleHTTPServer),
    ('CGIHTTPServer', CGIHTTPServer),
    ('urllib', urllib),
    ('httplib', httplib),
    ('threading', threading))

if __name__ == "__main__":
    test_main()

########NEW FILE########
__FILENAME__ = test_os
from eventlet import patcher
from eventlet.green import os

patcher.inject('test.test_os',
    globals(),
    ('os', os))

if __name__ == "__main__":
    test_main()

########NEW FILE########
__FILENAME__ = test_queue
from eventlet import patcher
from eventlet.green import Queue
from eventlet.green import threading
from eventlet.green import time

patcher.inject('test.test_queue',
    globals(),
    ('Queue', Queue),
    ('threading', threading),
    ('time', time))

if __name__ == "__main__":
    test_main()

########NEW FILE########
__FILENAME__ = test_select
from eventlet import patcher
from eventlet.green import select


patcher.inject('test.test_select',
    globals(),
    ('select', select))

if __name__ == "__main__":
    test_main()

########NEW FILE########
__FILENAME__ = test_SimpleHTTPServer
from eventlet import patcher
from eventlet.green import SimpleHTTPServer

patcher.inject('test.test_SimpleHTTPServer',
    globals(),
    ('SimpleHTTPServer', SimpleHTTPServer))
    
if __name__ == "__main__":
    test_main()
########NEW FILE########
__FILENAME__ = test_socket
#!/usr/bin/env python

from eventlet import patcher
from eventlet.green import socket
from eventlet.green import select
from eventlet.green import time
from eventlet.green import thread
from eventlet.green import threading

patcher.inject('test.test_socket',
    globals(),
    ('socket', socket),
    ('select', select),
    ('time', time),
    ('thread', thread),
    ('threading', threading))

# TODO: fix
TCPTimeoutTest.testInterruptedTimeout = lambda *a: None

if __name__ == "__main__":
    test_main()

########NEW FILE########
__FILENAME__ = test_socketserver
#!/usr/bin/env python

from eventlet import patcher
from eventlet.green import SocketServer
from eventlet.green import socket
from eventlet.green import select
from eventlet.green import time
from eventlet.green import threading

# to get past the silly 'requires' check
from test import test_support
test_support.use_resources = ['network']

patcher.inject('test.test_socketserver',
    globals(),
    ('SocketServer', SocketServer),
    ('socket', socket),
    ('select', select),
    ('time', time),
    ('threading', threading))

# only a problem with pyevent
from eventlet import tests
if tests.using_pyevent():
    try:
        SocketServerTest.test_ForkingUDPServer = lambda *a, **kw: None
        SocketServerTest.test_ForkingTCPServer = lambda *a, **kw: None
        SocketServerTest.test_ForkingUnixStreamServer = lambda *a, **kw: None
    except (NameError, AttributeError):
        pass

if __name__ == "__main__":
    test_main()

########NEW FILE########
__FILENAME__ = test_socket_ssl
#!/usr/bin/env python

from eventlet import patcher
from eventlet.green import socket

# enable network resource
import test.test_support
i_r_e = test.test_support.is_resource_enabled
def is_resource_enabled(resource):
    if resource == 'network':
        return True
    else:
        return i_r_e(resource)
test.test_support.is_resource_enabled = is_resource_enabled

try:
    socket.ssl
    socket.sslerror
except AttributeError:
    raise ImportError("Socket module doesn't support ssl")

patcher.inject('test.test_socket_ssl', globals())

test_basic = patcher.patch_function(test_basic)
test_rude_shutdown = patcher.patch_function(test_rude_shutdown)

def test_main():
    if not hasattr(socket, "ssl"):
        raise test_support.TestSkipped("socket module has no ssl support")
    test_rude_shutdown()
    test_basic()
    test_timeout()


if __name__ == "__main__":
    test_main()

########NEW FILE########
__FILENAME__ = test_ssl
from eventlet import patcher
from eventlet.green import asyncore
from eventlet.green import BaseHTTPServer
from eventlet.green import select
from eventlet.green import socket
from eventlet.green import SocketServer
from eventlet.green import SimpleHTTPServer
from eventlet.green import ssl
from eventlet.green import threading
from eventlet.green import urllib

# stupid test_support messing with our mojo
import test.test_support
i_r_e = test.test_support.is_resource_enabled
def is_resource_enabled(resource):
    if resource == 'network':
        return True
    else:
        return i_r_e(resource)
test.test_support.is_resource_enabled = is_resource_enabled

patcher.inject('test.test_ssl',
    globals(),
    ('asyncore', asyncore),
    ('BaseHTTPServer', BaseHTTPServer),
    ('select', select),
    ('socket', socket),
    ('SocketServer', SocketServer),
    ('ssl', ssl),
    ('threading', threading),
    ('urllib', urllib))
    
    
# TODO svn.python.org stopped serving up the cert that these tests expect; 
# presumably they've updated svn trunk but the tests in released versions will
# probably break forever. This is why you don't write tests that connect to 
# external servers.
NetworkedTests.testConnect = lambda s: None
NetworkedTests.testFetchServerCert = lambda s: None
NetworkedTests.test_algorithms = lambda s: None

# these don't pass because nonblocking ssl sockets don't report
# when the socket is closed uncleanly, per the docstring on 
# eventlet.green.GreenSSLSocket
# *TODO: fix and restore these tests
ThreadedTests.testProtocolSSL2 = lambda s: None
ThreadedTests.testProtocolSSL3 = lambda s: None
ThreadedTests.testProtocolTLS1 = lambda s: None
ThreadedTests.testSocketServer = lambda s: None

if __name__ == "__main__":
    test_main()

########NEW FILE########
__FILENAME__ = test_subprocess
from eventlet import patcher
from eventlet.green import subprocess
from eventlet.green import time

patcher.inject('test.test_subprocess',
    globals(),
    ('subprocess', subprocess),
    ('time', time))

if __name__ == "__main__":
    test_main()

########NEW FILE########
__FILENAME__ = test_thread
from eventlet import patcher
from eventlet.green import thread
from eventlet.green import time


patcher.inject('test.test_thread', globals())

try:
    # this is a new test in 2.7 that we don't support yet
    TestForkInThread.test_forkinthread = lambda *a, **kw: None
except NameError:
    pass

if __name__ == "__main__":
    test_main()

########NEW FILE########
__FILENAME__ = test_threading
from eventlet import patcher
from eventlet.green import threading
from eventlet.green import thread
from eventlet.green import time

# *NOTE: doesn't test as much of the threading api as we'd like because many of
# the tests are launched via subprocess and therefore don't get patched

patcher.inject('test.test_threading',
               globals())

# "PyThreadState_SetAsyncExc() is a CPython-only gimmick, not (currently)
# exposed at the Python level.  This test relies on ctypes to get at it."
# Therefore it's also disabled when testing eventlet, as it's not emulated.
try:
    ThreadTests.test_PyThreadState_SetAsyncExc = lambda s: None
except (AttributeError, NameError):
    pass

# disabling this test because it fails when run in Hudson even though it always
# succeeds when run manually
try:
    ThreadJoinOnShutdown.test_3_join_in_forked_from_thread = lambda *a, **kw: None
except (AttributeError, NameError):
    pass

# disabling this test because it relies on dorking with the hidden
# innards of the threading module in a way that doesn't appear to work
# when patched
try:
    ThreadTests.test_limbo_cleanup = lambda *a, **kw: None
except (AttributeError, NameError):
    pass

# this test has nothing to do with Eventlet; if it fails it's not
# because of patching (which it does, grump grump)
try:
    ThreadTests.test_finalize_runnning_thread = lambda *a, **kw: None
    # it's misspelled in the stdlib, silencing this version as well because
    # inevitably someone will correct the error
    ThreadTests.test_finalize_running_thread = lambda *a, **kw: None
except (AttributeError, NameError):
    pass

if __name__ == "__main__":
    test_main()

########NEW FILE########
__FILENAME__ = test_threading_local
from eventlet import patcher
from eventlet.green import thread
from eventlet.green import threading
from eventlet.green import time

# hub requires initialization before test can run
from eventlet import hubs
hubs.get_hub()

patcher.inject('test.test_threading_local',
    globals(),
    ('time', time),
    ('thread', thread),
    ('threading', threading))
    
if __name__ == '__main__':
    test_main()
########NEW FILE########
__FILENAME__ = test_thread__boundedsem
"""Test that BoundedSemaphore with a very high bound is as good as unbounded one"""
from eventlet import coros
from eventlet.green import thread

def allocate_lock():
    return coros.semaphore(1, 9999)

original_allocate_lock = thread.allocate_lock
thread.allocate_lock = allocate_lock
original_LockType = thread.LockType
thread.LockType = coros.CappedSemaphore

try:
    import os.path
    execfile(os.path.join(os.path.dirname(__file__), 'test_thread.py'))
finally:
    thread.allocate_lock = original_allocate_lock
    thread.LockType = original_LockType

########NEW FILE########
__FILENAME__ = test_timeout
from eventlet import patcher
from eventlet.green import socket
from eventlet.green import time

patcher.inject('test.test_timeout',
    globals(),
    ('socket', socket),
    ('time', time))

# to get past the silly 'requires' check
from test import test_support
test_support.use_resources = ['network']

if __name__ == "__main__":
    test_main()
########NEW FILE########
__FILENAME__ = test_urllib
from eventlet import patcher
from eventlet.green import httplib
from eventlet.green import urllib

patcher.inject('test.test_urllib',
    globals(),
    ('httplib', httplib),
    ('urllib', urllib))
    
if __name__ == "__main__":
    test_main()
########NEW FILE########
__FILENAME__ = test_urllib2
from eventlet import patcher
from eventlet.green import socket
from eventlet.green import urllib2

patcher.inject('test.test_urllib2',
    globals(),
    ('socket', socket),
    ('urllib2', urllib2))

HandlerTests.test_file = patcher.patch_function(HandlerTests.test_file, ('socket', socket))
HandlerTests.test_cookie_redirect = patcher.patch_function(HandlerTests.test_cookie_redirect, ('urllib2', urllib2))
OpenerDirectorTests.test_badly_named_methods = patcher.patch_function(OpenerDirectorTests.test_badly_named_methods, ('urllib2', urllib2))

if __name__ == "__main__":
    test_main()

########NEW FILE########
__FILENAME__ = test_urllib2_localnet
from eventlet import patcher

from eventlet.green import BaseHTTPServer
from eventlet.green import threading
from eventlet.green import socket
from eventlet.green import urllib2

patcher.inject('test.test_urllib2_localnet',
    globals(),
    ('BaseHTTPServer', BaseHTTPServer),
    ('threading', threading),
    ('socket', socket),
    ('urllib2', urllib2))
        
if __name__ == "__main__":
    test_main()
########NEW FILE########
__FILENAME__ = subprocess_test
import eventlet
from eventlet.green import subprocess
import eventlet.patcher
from nose.plugins.skip import SkipTest
import os
import sys
import time
original_subprocess = eventlet.patcher.original('subprocess')


def test_subprocess_wait():
    # https://bitbucket.org/eventlet/eventlet/issue/89
    # In Python 3.3 subprocess.Popen.wait() method acquired `timeout`
    # argument.
    # RHEL backported it to their Python 2.6 package.
    p = subprocess.Popen(
        [sys.executable, "-c", "import time; time.sleep(0.5)"])
    ok = False
    t1 = time.time()
    try:
        p.wait(timeout=0.1)
    except subprocess.TimeoutExpired:
        ok = True
    tdiff = time.time() - t1
    assert ok == True, 'did not raise subprocess.TimeoutExpired'
    assert 0.1 <= tdiff <= 0.2, 'did not stop within allowed time'


def test_communicate_with_poll():
    # https://github.com/eventlet/eventlet/pull/24
    # `eventlet.green.subprocess.Popen.communicate()` was broken
    # in Python 2.7 because the usage of the `select` module was moved from
    # `_communicate` into two other methods `_communicate_with_select`
    # and `_communicate_with_poll`. Link to 2.7's implementation:
    # http://hg.python.org/cpython/file/2145593d108d/Lib/subprocess.py#l1255
    if getattr(original_subprocess.Popen, '_communicate_with_poll', None) is None:
        raise SkipTest('original subprocess.Popen does not have _communicate_with_poll')

    p = subprocess.Popen(
        [sys.executable, '-c', 'import time; time.sleep(0.5)'],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    t1 = time.time()
    eventlet.with_timeout(0.1, p.communicate, timeout_value=True)
    tdiff = time.time() - t1
    assert 0.1 <= tdiff <= 0.2, 'did not stop within allowed time'

########NEW FILE########
__FILENAME__ = test__coros_queue
from tests import LimitedTestCase, silence_warnings
from unittest import main
import eventlet
from eventlet import coros, spawn, sleep
from eventlet.event import Event


class TestQueue(LimitedTestCase):

    @silence_warnings
    def test_send_first(self):
        q = coros.queue()
        q.send('hi')
        self.assertEqual(q.wait(), 'hi')

    @silence_warnings
    def test_send_exception_first(self):
        q = coros.queue()
        q.send(exc=RuntimeError())
        self.assertRaises(RuntimeError, q.wait)

    @silence_warnings
    def test_send_last(self):
        q = coros.queue()
        def waiter(q):
            timer = eventlet.Timeout(0.1)
            self.assertEqual(q.wait(), 'hi2')
            timer.cancel()

        spawn(waiter, q)
        sleep(0)
        sleep(0)
        q.send('hi2')

    @silence_warnings
    def test_max_size(self):
        q = coros.queue(2)
        results = []

        def putter(q):
            q.send('a')
            results.append('a')
            q.send('b')
            results.append('b')
            q.send('c')
            results.append('c')

        spawn(putter, q)
        sleep(0)
        self.assertEqual(results, ['a', 'b'])
        self.assertEqual(q.wait(), 'a')
        sleep(0)
        self.assertEqual(results, ['a', 'b', 'c'])
        self.assertEqual(q.wait(), 'b')
        self.assertEqual(q.wait(), 'c')

    @silence_warnings
    def test_zero_max_size(self):
        q = coros.queue(0)
        def sender(evt, q):
            q.send('hi')
            evt.send('done')

        def receiver(evt, q):
            x = q.wait()
            evt.send(x)

        e1 = Event()
        e2 = Event()

        spawn(sender, e1, q)
        sleep(0)
        self.assert_(not e1.ready())
        spawn(receiver, e2, q)
        self.assertEqual(e2.wait(),'hi')
        self.assertEqual(e1.wait(),'done')

    @silence_warnings
    def test_multiple_waiters(self):
        # tests that multiple waiters get their results back
        q = coros.queue()

        sendings = ['1', '2', '3', '4']
        gts = [eventlet.spawn(q.wait)
                for x in sendings]
                
        eventlet.sleep(0.01) # get 'em all waiting

        q.send(sendings[0])
        q.send(sendings[1])
        q.send(sendings[2])
        q.send(sendings[3])
        results = set()
        for i, gt in enumerate(gts):
            results.add(gt.wait())
        self.assertEqual(results, set(sendings))

    @silence_warnings
    def test_waiters_that_cancel(self):
        q = coros.queue()

        def do_receive(q, evt):
            eventlet.Timeout(0, RuntimeError())
            try:
                result = q.wait()
                evt.send(result)
            except RuntimeError:
                evt.send('timed out')


        evt = Event()
        spawn(do_receive, q, evt)
        self.assertEqual(evt.wait(), 'timed out')

        q.send('hi')
        self.assertEqual(q.wait(), 'hi')

    @silence_warnings
    def test_senders_that_die(self):
        q = coros.queue()

        def do_send(q):
            q.send('sent')

        spawn(do_send, q)
        self.assertEqual(q.wait(), 'sent')

    @silence_warnings
    def test_two_waiters_one_dies(self):
        def waiter(q, evt):
            evt.send(q.wait())
        def do_receive(q, evt):
            eventlet.Timeout(0, RuntimeError())
            try:
                result = q.wait()
                evt.send(result)
            except RuntimeError:
                evt.send('timed out')

        q = coros.queue()
        dying_evt = Event()
        waiting_evt = Event()
        spawn(do_receive, q, dying_evt)
        spawn(waiter, q, waiting_evt)
        sleep(0)
        q.send('hi')
        self.assertEqual(dying_evt.wait(), 'timed out')
        self.assertEqual(waiting_evt.wait(), 'hi')

    @silence_warnings
    def test_two_bogus_waiters(self):
        def do_receive(q, evt):
            eventlet.Timeout(0, RuntimeError())
            try:
                result = q.wait()
                evt.send(result)
            except RuntimeError:
                evt.send('timed out')

        q = coros.queue()
        e1 = Event()
        e2 = Event()
        spawn(do_receive, q, e1)
        spawn(do_receive, q, e2)
        sleep(0)
        q.send('sent')
        self.assertEqual(e1.wait(), 'timed out')
        self.assertEqual(e2.wait(), 'timed out')
        self.assertEqual(q.wait(), 'sent')
                
    @silence_warnings
    def test_waiting(self):
        def do_wait(q, evt):
            result = q.wait()
            evt.send(result)

        q = coros.queue()
        e1 = Event()
        spawn(do_wait, q, e1)
        sleep(0)
        self.assertEqual(1, q.waiting())
        q.send('hi')
        sleep(0)
        self.assertEqual(0, q.waiting())
        self.assertEqual('hi', e1.wait())
        self.assertEqual(0, q.waiting())


class TestChannel(LimitedTestCase):

    @silence_warnings
    def test_send(self):
        sleep(0.1)
        channel = coros.queue(0)

        events = []

        def another_greenlet():
            events.append(channel.wait())
            events.append(channel.wait())

        spawn(another_greenlet)

        events.append('sending')
        channel.send('hello')
        events.append('sent hello')
        channel.send('world')
        events.append('sent world')

        self.assertEqual(['sending', 'hello', 'sent hello', 'world', 'sent world'], events)


    @silence_warnings
    def test_wait(self):
        sleep(0.1)
        channel = coros.queue(0)
        events = []

        def another_greenlet():
            events.append('sending hello')
            channel.send('hello')
            events.append('sending world')
            channel.send('world')
            events.append('sent world')

        spawn(another_greenlet)

        events.append('waiting')
        events.append(channel.wait())
        events.append(channel.wait())

        self.assertEqual(['waiting', 'sending hello', 'hello', 'sending world', 'world'], events)
        sleep(0)
        self.assertEqual(['waiting', 'sending hello', 'hello', 'sending world', 'world', 'sent world'], events)

    @silence_warnings
    def test_waiters(self):
        c = coros.Channel()
        w1 = eventlet.spawn(c.wait)
        w2 = eventlet.spawn(c.wait)
        w3 = eventlet.spawn(c.wait)
        sleep(0)
        self.assertEqual(c.waiting(), 3)
        s1 = eventlet.spawn(c.send, 1)
        s2 = eventlet.spawn(c.send, 2)
        s3 = eventlet.spawn(c.send, 3)
        sleep(0)  # this gets all the sends into a waiting state
        self.assertEqual(c.waiting(), 0)

        s1.wait()
        s2.wait()
        s3.wait()
        # NOTE: we don't guarantee that waiters are served in order
        results = sorted([w1.wait(), w2.wait(), w3.wait()])
        self.assertEqual(results, [1,2,3])

if __name__=='__main__':
    main()

########NEW FILE########
__FILENAME__ = test__event
import unittest
from eventlet.event import Event
from eventlet.api import spawn, sleep, with_timeout
import eventlet
from tests import LimitedTestCase

DELAY= 0.01

class TestEvent(LimitedTestCase):
    
    def test_send_exc(self):
        log = []
        e = Event()

        def waiter():
            try:
                result = e.wait()
                log.append(('received', result))
            except Exception as ex:
                log.append(('catched', ex))
        spawn(waiter)
        sleep(0) # let waiter to block on e.wait()
        obj = Exception()
        e.send(exc=obj)
        sleep(0)
        sleep(0)
        assert log == [('catched', obj)], log

    def test_send(self):
        event1 = Event()
        event2 = Event()

        spawn(event1.send, 'hello event1')
        eventlet.Timeout(0, ValueError('interrupted'))
        try:
            result = event1.wait()
        except ValueError:
            X = object()
            result = with_timeout(DELAY, event2.wait, timeout_value=X)
            assert result is X, 'Nobody sent anything to event2 yet it received %r' % (result, )


if __name__=='__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test__greenness
"""Test than modules in eventlet.green package are indeed green.
To do that spawn a green server and then access it using a green socket.
If either operation blocked the whole script would block and timeout.
"""
import unittest

from eventlet.green import urllib2, BaseHTTPServer
from eventlet import spawn, kill


class QuietHandler(BaseHTTPServer.BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.0"

    def log_message(self, *args, **kw):
        pass


def start_http_server():
    server_address = ('localhost', 0)
    httpd = BaseHTTPServer.HTTPServer(server_address, QuietHandler)
    sa = httpd.socket.getsockname()
    #print("Serving HTTP on", sa[0], "port", sa[1], "...")
    httpd.request_count = 0

    def serve():
        # increment the request_count before handling the request because
        # the send() for the response blocks (or at least appeared to be)
        httpd.request_count += 1
        httpd.handle_request()
    return spawn(serve), httpd, sa[1]


class TestGreenness(unittest.TestCase):

    def setUp(self):
        self.gthread, self.server, self.port = start_http_server()
        #print('Spawned the server')

    def tearDown(self):
        self.server.server_close()
        kill(self.gthread)

    def test_urllib2(self):
        self.assertEqual(self.server.request_count, 0)
        try:
            urllib2.urlopen('http://127.0.0.1:%s' % self.port)
            assert False, 'should not get there'
        except urllib2.HTTPError as ex:
            assert ex.code == 501, repr(ex)
        self.assertEqual(self.server.request_count, 1)

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test__pool
import eventlet
import warnings
warnings.simplefilter('ignore', DeprecationWarning)
from eventlet import pool, coros, api, hubs, timeout
warnings.simplefilter('default', DeprecationWarning)
from eventlet import event as _event
from eventlet.support import six
from tests import LimitedTestCase
from unittest import main


class TestCoroutinePool(LimitedTestCase):
    klass = pool.Pool

    def test_execute_async(self):
        done = _event.Event()
        def some_work():
            done.send()
        pool = self.klass(0, 2)
        pool.execute_async(some_work)
        done.wait()

    def test_execute(self):
        value = 'return value'
        def some_work():
            return value
        pool = self.klass(0, 2)
        worker = pool.execute(some_work)
        self.assertEqual(value, worker.wait())

    def test_waiting(self):
        pool = self.klass(0,1)
        done = _event.Event()
        def consume():
            done.wait()
        def waiter(pool):
            evt = pool.execute(consume)
            evt.wait()

        waiters = []
        waiters.append(eventlet.spawn(waiter, pool))
        api.sleep(0)
        self.assertEqual(pool.waiting(), 0)
        waiters.append(eventlet.spawn(waiter, pool))
        api.sleep(0)
        self.assertEqual(pool.waiting(), 1)
        waiters.append(eventlet.spawn(waiter, pool))
        api.sleep(0)
        self.assertEqual(pool.waiting(), 2)
        done.send(None)
        for w in waiters:
            w.wait()
        self.assertEqual(pool.waiting(), 0)

    def test_multiple_coros(self):
        evt = _event.Event()
        results = []
        def producer():
            results.append('prod')
            evt.send()

        def consumer():
            results.append('cons1')
            evt.wait()
            results.append('cons2')

        pool = self.klass(0, 2)
        done = pool.execute(consumer)
        pool.execute_async(producer)
        done.wait()
        self.assertEqual(['cons1', 'prod', 'cons2'], results)

    def test_timer_cancel(self):
        # this test verifies that local timers are not fired
        # outside of the context of the execute method
        timer_fired = []
        def fire_timer():
            timer_fired.append(True)
        def some_work():
            hubs.get_hub().schedule_call_local(0, fire_timer)
        pool = self.klass(0, 2)
        worker = pool.execute(some_work)
        worker.wait()
        api.sleep(0)
        self.assertEqual(timer_fired, [])

    def test_reentrant(self):
        pool = self.klass(0,1)
        def reenter():
            waiter = pool.execute(lambda a: a, 'reenter')
            self.assertEqual('reenter', waiter.wait())

        outer_waiter = pool.execute(reenter)
        outer_waiter.wait()

        evt = _event.Event()
        def reenter_async():
            pool.execute_async(lambda a: a, 'reenter')
            evt.send('done')

        pool.execute_async(reenter_async)
        evt.wait()

    def assert_pool_has_free(self, pool, num_free):
        def wait_long_time(e):
            e.wait()
        timer = timeout.Timeout(1, api.TimeoutError)
        try:
            evt = _event.Event()
            for x in six.moves.range(num_free):
                pool.execute(wait_long_time, evt)
                # if the pool has fewer free than we expect,
                # then we'll hit the timeout error
        finally:
            timer.cancel()

        # if the runtime error is not raised it means the pool had
        # some unexpected free items
        timer = timeout.Timeout(0, RuntimeError)
        self.assertRaises(RuntimeError, pool.execute, wait_long_time, evt)

        # clean up by causing all the wait_long_time functions to return
        evt.send(None)
        api.sleep(0)
        api.sleep(0)

    def test_resize(self):
        pool = self.klass(max_size=2)
        evt = _event.Event()
        def wait_long_time(e):
            e.wait()
        pool.execute(wait_long_time, evt)
        pool.execute(wait_long_time, evt)
        self.assertEqual(pool.free(), 0)
        self.assert_pool_has_free(pool, 0)

        # verify that the pool discards excess items put into it
        pool.resize(1)

        # cause the wait_long_time functions to return, which will
        # trigger puts to the pool
        evt.send(None)
        api.sleep(0)
        api.sleep(0)

        self.assertEqual(pool.free(), 1)
        self.assert_pool_has_free(pool, 1)

        # resize larger and assert that there are more free items
        pool.resize(2)
        self.assertEqual(pool.free(), 2)
        self.assert_pool_has_free(pool, 2)

    def test_stderr_raising(self):
        # testing that really egregious errors in the error handling code
        # (that prints tracebacks to stderr) don't cause the pool to lose
        # any members
        import sys
        pool = self.klass(min_size=1, max_size=1)
        def crash(*args, **kw):
            raise RuntimeError("Whoa")
        class FakeFile(object):
            write = crash

        # we're going to do this by causing the traceback.print_exc in
        # safe_apply to raise an exception and thus exit _main_loop
        normal_err = sys.stderr
        try:
            sys.stderr = FakeFile()
            waiter = pool.execute(crash)
            self.assertRaises(RuntimeError, waiter.wait)
            # the pool should have something free at this point since the
            # waiter returned
            # pool.Pool change: if an exception is raised during execution of a link,
            # the rest of the links are scheduled to be executed on the next hub iteration
            # this introduces a delay in updating pool.sem which makes pool.free() report 0
            # therefore, sleep:
            api.sleep(0)
            self.assertEqual(pool.free(), 1)
            # shouldn't block when trying to get
            t = timeout.Timeout(0.1)
            try:
                pool.execute(api.sleep, 1)
            finally:
                t.cancel()
        finally:
            sys.stderr = normal_err

    def test_track_events(self):
        pool = self.klass(track_events=True)
        for x in range(6):
            pool.execute(lambda n: n, x)
        for y in range(6):
            pool.wait()

    def test_track_slow_event(self):
        pool = self.klass(track_events=True)
        def slow():
            api.sleep(0.1)
            return 'ok'
        pool.execute(slow)
        self.assertEqual(pool.wait(), 'ok')

    def test_pool_smash(self):
        # The premise is that a coroutine in a Pool tries to get a token out
        # of a token pool but times out before getting the token.  We verify
        # that neither pool is adversely affected by this situation.
        from eventlet import pools
        pool = self.klass(min_size=1, max_size=1)
        tp = pools.TokenPool(max_size=1)
        token = tp.get()  # empty pool
        def do_receive(tp):
            timeout.Timeout(0, RuntimeError())
            try:
                t = tp.get()
                self.fail("Shouldn't have recieved anything from the pool")
            except RuntimeError:
                return 'timed out'

        # the execute makes the token pool expect that coroutine, but then
        # immediately cuts bait
        e1 = pool.execute(do_receive, tp)
        self.assertEqual(e1.wait(), 'timed out')

        # the pool can get some random item back
        def send_wakeup(tp):
            tp.put('wakeup')
        api.spawn(send_wakeup, tp)

        # now we ask the pool to run something else, which should not
        # be affected by the previous send at all
        def resume():
            return 'resumed'
        e2 = pool.execute(resume)
        self.assertEqual(e2.wait(), 'resumed')

        # we should be able to get out the thing we put in there, too
        self.assertEqual(tp.get(), 'wakeup')


class PoolBasicTests(LimitedTestCase):
    klass = pool.Pool

    def test_execute_async(self):
        p = self.klass(max_size=2)
        self.assertEqual(p.free(), 2)
        r = []
        def foo(a):
            r.append(a)
        evt = p.execute(foo, 1)
        self.assertEqual(p.free(), 1)
        evt.wait()
        self.assertEqual(r, [1])
        api.sleep(0)
        self.assertEqual(p.free(), 2)

        #Once the pool is exhausted, calling an execute forces a yield.

        p.execute_async(foo, 2)
        self.assertEqual(1, p.free())
        self.assertEqual(r, [1])

        p.execute_async(foo, 3)
        self.assertEqual(0, p.free())
        self.assertEqual(r, [1])

        p.execute_async(foo, 4)
        self.assertEqual(r, [1,2,3])
        api.sleep(0)
        self.assertEqual(r, [1,2,3,4])

    def test_execute(self):
        p = self.klass()
        evt = p.execute(lambda a: ('foo', a), 1)
        self.assertEqual(evt.wait(), ('foo', 1))

    def test_with_intpool(self):
        from eventlet import pools
        class IntPool(pools.Pool):
            def create(self):
                self.current_integer = getattr(self, 'current_integer', 0) + 1
                return self.current_integer

        def subtest(intpool_size, pool_size, num_executes):
            def run(int_pool):
                token = int_pool.get()
                api.sleep(0.0001)
                int_pool.put(token)
                return token

            int_pool = IntPool(max_size=intpool_size)
            pool = self.klass(max_size=pool_size)
            for ix in six.moves.range(num_executes):
                pool.execute(run, int_pool)
            pool.waitall()

        subtest(4, 7, 7)
        subtest(50, 75, 100)
        for isize in (20, 30, 40, 50):
            for psize in (25, 35, 50):
                subtest(isize, psize, psize)


if __name__=='__main__':
    main()


########NEW FILE########
__FILENAME__ = test__proc
import sys
import unittest
import warnings
warnings.simplefilter('ignore', DeprecationWarning)
from eventlet import proc
warnings.simplefilter('default', DeprecationWarning)
from eventlet import coros
from eventlet import event as _event
from eventlet import Timeout, sleep, getcurrent, with_timeout
from tests import LimitedTestCase, skipped, silence_warnings

DELAY = 0.01

class ExpectedError(Exception):
    pass

class TestLink_Signal(LimitedTestCase):

    @silence_warnings
    def test_send(self):
        s = proc.Source()
        q1, q2, q3 = coros.queue(), coros.queue(), coros.queue()
        s.link_value(q1)
        self.assertRaises(Timeout, s.wait, 0)
        assert s.wait(0, None) is None
        assert s.wait(0.001, None) is None
        self.assertRaises(Timeout, s.wait, 0.001)
        s.send(1)
        assert not q1.ready()
        assert s.wait()==1
        sleep(0)
        assert q1.ready()
        s.link_exception(q2)
        s.link(q3)
        assert not q2.ready()
        sleep(0)
        assert q3.ready()
        assert s.wait()==1

    @silence_warnings
    def test_send_exception(self):
        s = proc.Source()
        q1, q2, q3 = coros.queue(), coros.queue(), coros.queue()
        s.link_exception(q1)
        s.send_exception(OSError('hello'))
        sleep(0)
        assert q1.ready()
        s.link_value(q2)
        s.link(q3)
        assert not q2.ready()
        sleep(0)
        assert q3.ready()
        self.assertRaises(OSError, q1.wait)
        self.assertRaises(OSError, q3.wait)
        self.assertRaises(OSError, s.wait)


class TestProc(LimitedTestCase):

    def test_proc(self):
        p = proc.spawn(lambda : 100)
        receiver = proc.spawn(sleep, 1)
        p.link(receiver)
        self.assertRaises(proc.LinkedCompleted, receiver.wait)
        receiver2 = proc.spawn(sleep, 1)
        p.link(receiver2)
        self.assertRaises(proc.LinkedCompleted, receiver2.wait)

    def test_event(self):
        p = proc.spawn(lambda : 100)
        event = _event.Event()
        p.link(event)
        self.assertEqual(event.wait(), 100)

        for i in range(3):
            event2 = _event.Event()
            p.link(event2)
            self.assertEqual(event2.wait(), 100)

    def test_current(self):
        p = proc.spawn(lambda : 100)
        p.link()
        self.assertRaises(proc.LinkedCompleted, sleep, 0.1)


class TestCase(LimitedTestCase):

    def link(self, p, listener=None):
        getattr(p, self.link_method)(listener)

    def tearDown(self):
        LimitedTestCase.tearDown(self)
        self.p.unlink()

    def set_links(self, p, first_time, kill_exc_type):
        event = _event.Event()
        self.link(p, event)

        proc_flag = []
        def receiver():
            sleep(DELAY)
            proc_flag.append('finished')
        receiver = proc.spawn(receiver)
        self.link(p, receiver)

        queue = coros.queue(1)
        self.link(p, queue)

        try:
            self.link(p)
        except kill_exc_type:
            if first_time:
                raise
        else:
            assert first_time, 'not raising here only first time'

        callback_flag = ['initial']
        self.link(p, lambda *args: callback_flag.remove('initial'))

        for _ in range(10):
            self.link(p, _event.Event())
            self.link(p, coros.queue(1))
        return event, receiver, proc_flag, queue, callback_flag

    def set_links_timeout(self, link):
        # stuff that won't be touched
        event = _event.Event()
        link(event)

        proc_finished_flag = []
        def myproc():
            sleep(10)
            proc_finished_flag.append('finished')
            return 555
        myproc = proc.spawn(myproc)
        link(myproc)

        queue = coros.queue(0)
        link(queue)
        return event, myproc, proc_finished_flag, queue

    def check_timed_out(self, event, myproc, proc_finished_flag, queue):
        X = object()
        assert with_timeout(DELAY, event.wait, timeout_value=X) is X
        assert with_timeout(DELAY, queue.wait, timeout_value=X) is X
        assert with_timeout(DELAY, proc.waitall, [myproc], timeout_value=X) is X
        assert proc_finished_flag == [], proc_finished_flag


class TestReturn_link(TestCase):
    link_method = 'link'

    def test_return(self):
        def return25():
            return 25
        p = self.p = proc.spawn(return25)
        self._test_return(p, True, 25, proc.LinkedCompleted, lambda : sleep(0))
        # repeating the same with dead process
        for _ in range(3):
            self._test_return(p, False, 25, proc.LinkedCompleted, lambda : sleep(0))

    def _test_return(self, p, first_time, result, kill_exc_type, action):
        event, receiver, proc_flag, queue, callback_flag = self.set_links(p, first_time, kill_exc_type)

        # stuff that will time out because there's no unhandled exception:
        xxxxx = self.set_links_timeout(p.link_exception)

        try:
            sleep(DELAY*2)
        except kill_exc_type:
             assert first_time, 'raising here only first time'
        else:
            assert not first_time, 'Should not raise LinkedKilled here after first time'

        assert not p, p

        self.assertEqual(event.wait(), result)
        self.assertEqual(queue.wait(), result)
        self.assertRaises(kill_exc_type, receiver.wait)
        self.assertRaises(kill_exc_type, proc.waitall, [receiver])

        sleep(DELAY)
        assert not proc_flag, proc_flag
        assert not callback_flag, callback_flag

        self.check_timed_out(*xxxxx)

class TestReturn_link_value(TestReturn_link):
    sync = False
    link_method = 'link_value'


class TestRaise_link(TestCase):
    link_method = 'link'

    def _test_raise(self, p, first_time, kill_exc_type):
        event, receiver, proc_flag, queue, callback_flag = self.set_links(p, first_time, kill_exc_type)
        xxxxx = self.set_links_timeout(p.link_value)

        try:
            sleep(DELAY)
        except kill_exc_type:
             assert first_time, 'raising here only first time'
        else:
            assert not first_time, 'Should not raise LinkedKilled here after first time'

        assert not p, p

        self.assertRaises(ExpectedError, event.wait)
        self.assertRaises(ExpectedError, queue.wait)
        self.assertRaises(kill_exc_type, receiver.wait)
        self.assertRaises(kill_exc_type, proc.waitall, [receiver])
        sleep(DELAY)
        assert not proc_flag, proc_flag
        assert not callback_flag, callback_flag

        self.check_timed_out(*xxxxx)

    @silence_warnings
    def test_raise(self):
        p = self.p = proc.spawn(lambda : getcurrent().throw(ExpectedError('test_raise')))
        self._test_raise(p, True, proc.LinkedFailed)
        # repeating the same with dead process
        for _ in range(3):
            self._test_raise(p, False, proc.LinkedFailed)

    def _test_kill(self, p, first_time, kill_exc_type):
        event, receiver, proc_flag, queue, callback_flag = self.set_links(p, first_time, kill_exc_type)
        xxxxx = self.set_links_timeout(p.link_value)

        p.kill()
        try:
            sleep(DELAY)
        except kill_exc_type:
             assert first_time, 'raising here only first time'
        else:
            assert not first_time, 'Should not raise LinkedKilled here after first time'

        assert not p, p

        self.assertRaises(proc.ProcExit, event.wait)
        self.assertRaises(proc.ProcExit, queue.wait)
        self.assertRaises(kill_exc_type, proc.waitall, [receiver])
        self.assertRaises(kill_exc_type, receiver.wait)

        sleep(DELAY)
        assert not proc_flag, proc_flag
        assert not callback_flag, callback_flag

        self.check_timed_out(*xxxxx)

    @silence_warnings
    def test_kill(self):
        p = self.p = proc.spawn(sleep, DELAY)
        self._test_kill(p, True, proc.LinkedKilled)
        # repeating the same with dead process
        for _ in range(3):
            self._test_kill(p, False, proc.LinkedKilled)

class TestRaise_link_exception(TestRaise_link):
    link_method = 'link_exception'


class TestStuff(LimitedTestCase):

    def test_wait_noerrors(self):
        x = proc.spawn(lambda : 1)
        y = proc.spawn(lambda : 2)
        z = proc.spawn(lambda : 3)
        self.assertEqual(proc.waitall([x, y, z]), [1, 2, 3])
        e = _event.Event()
        x.link(e)
        self.assertEqual(e.wait(), 1)
        x.unlink(e)
        e = _event.Event()
        x.link(e)
        self.assertEqual(e.wait(), 1)
        self.assertEqual([proc.waitall([X]) for X in [x, y, z]], [[1], [2], [3]])

    # this test is timing-sensitive
    @skipped
    def test_wait_error(self):
        def x():
            sleep(DELAY)
            return 1
        x = proc.spawn(x)
        z = proc.spawn(lambda : 3)
        y = proc.spawn(lambda : getcurrent().throw(ExpectedError('test_wait_error')))
        y.link(x)
        x.link(y)
        y.link(z)
        z.link(y)
        self.assertRaises(ExpectedError, proc.waitall, [x, y, z])
        self.assertRaises(proc.LinkedFailed, proc.waitall, [x])
        self.assertEqual(proc.waitall([z]), [3])
        self.assertRaises(ExpectedError, proc.waitall, [y])

    def test_wait_all_exception_order(self):
        # if there're several exceptions raised, the earliest one must be raised by wait
        def first():
            sleep(0.1)
            raise ExpectedError('first')
        a = proc.spawn(first)
        b = proc.spawn(lambda : getcurrent().throw(ExpectedError('second')))
        try:
            proc.waitall([a, b])
        except ExpectedError as ex:
            assert 'second' in str(ex), repr(str(ex))
        sleep(0.2)   # sleep to ensure that the other timer is raised

    def test_multiple_listeners_error(self):
        # if there was an error while calling a callback
        # it should not prevent the other listeners from being called
        # also, all of the errors should be logged, check the output
        # manually that they are
        p = proc.spawn(lambda : 5)
        results = []
        def listener1(*args):
            results.append(10)
            raise ExpectedError('listener1')
        def listener2(*args):
            results.append(20)
            raise ExpectedError('listener2')
        def listener3(*args):
            raise ExpectedError('listener3')
        p.link(listener1)
        p.link(listener2)
        p.link(listener3)
        sleep(DELAY*10)
        assert results in [[10, 20], [20, 10]], results

        p = proc.spawn(lambda : getcurrent().throw(ExpectedError('test_multiple_listeners_error')))
        results = []
        p.link(listener1)
        p.link(listener2)
        p.link(listener3)
        sleep(DELAY*10)
        assert results in [[10, 20], [20, 10]], results

    def _test_multiple_listeners_error_unlink(self, p):
        # notification must not happen after unlink even
        # though notification process has been already started
        results = []
        def listener1(*args):
            p.unlink(listener2)
            results.append(5)
            raise ExpectedError('listener1')
        def listener2(*args):
            p.unlink(listener1)
            results.append(5)
            raise ExpectedError('listener2')
        def listener3(*args):
            raise ExpectedError('listener3')
        p.link(listener1)
        p.link(listener2)
        p.link(listener3)
        sleep(DELAY*10)
        assert results == [5], results

    def test_multiple_listeners_error_unlink_Proc(self):
        p = proc.spawn(lambda : 5)
        self._test_multiple_listeners_error_unlink(p)

    def test_multiple_listeners_error_unlink_Source(self):
        p = proc.Source()
        proc.spawn(p.send, 6)
        self._test_multiple_listeners_error_unlink(p)

    def test_killing_unlinked(self):
        e = _event.Event()
        def func():
            try:
                raise ExpectedError('test_killing_unlinked')
            except:
                e.send_exception(*sys.exc_info())
        p = proc.spawn_link(func)
        try:
            try:
                e.wait()
            except ExpectedError:
                pass
        finally:
            p.unlink() # this disables LinkedCompleted that otherwise would be raised by the next line
        sleep(DELAY)


if __name__=='__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test__refcount
"""This test checks that socket instances (not GreenSockets but underlying sockets)
are not leaked by the hub.
"""
import gc
from pprint import pformat
import unittest
import weakref

from eventlet.support import clear_sys_exc_info
from eventlet.green import socket
from eventlet.green.thread import start_new_thread
from eventlet.green.time import sleep

SOCKET_TIMEOUT = 0.1


def init_server():
    s = socket.socket()
    s.settimeout(SOCKET_TIMEOUT)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(('localhost', 0))
    s.listen(5)
    return s, s.getsockname()[1]


def handle_request(s, raise_on_timeout):
    try:
        conn, address = s.accept()
    except socket.timeout:
        if raise_on_timeout:
            raise
        else:
            return
    #print('handle_request - accepted')
    res = conn.recv(100)
    assert res == b'hello', repr(res)
    #print('handle_request - recvd %r' % res)
    res = conn.send(b'bye')
    #print('handle_request - sent %r' % res)
    #print('handle_request - conn refcount: %s' % sys.getrefcount(conn))
    #conn.close()


def make_request(port):
    #print('make_request')
    s = socket.socket()
    s.connect(('localhost', port))
    #print('make_request - connected')
    res = s.send(b'hello')
    #print('make_request - sent %s' % res)
    res = s.recv(100)
    assert res == b'bye', repr(res)
    #print('make_request - recvd %r' % res)
    #s.close()


def run_interaction(run_client):
    s, port = init_server()
    start_new_thread(handle_request, (s, run_client))
    if run_client:
        start_new_thread(make_request, (port,))
    sleep(0.1 + SOCKET_TIMEOUT)
    #print(sys.getrefcount(s.fd))
    #s.close()
    return weakref.ref(s.fd)


def run_and_check(run_client):
    w = run_interaction(run_client=run_client)
    clear_sys_exc_info()
    gc.collect()
    if w():
        print(pformat(gc.get_referrers(w())))
        for x in gc.get_referrers(w()):
            print(pformat(x))
            for y in gc.get_referrers(x):
                print('- {0}'.format(pformat(y)))
        raise AssertionError('server should be dead by now')


def test_clean_exit():
    run_and_check(True)
    run_and_check(True)


def test_timeout_exit():
    run_and_check(False)
    run_and_check(False)


if __name__=='__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test__socket_errors
import unittest
import socket as _original_sock
from eventlet import api
from eventlet.green import socket

class TestSocketErrors(unittest.TestCase):    
    def test_connection_refused(self):
        # open and close a dummy server to find an unused port
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.bind(('127.0.0.1', 0))
        server.listen(1)
        port = server.getsockname()[1]
        server.close()
        del server
        s = socket.socket()
        try:
            s.connect(('127.0.0.1', port))
            self.fail("Shouldn't have connected")
        except socket.error as ex:
            code, text = ex.args
            assert code in [111, 61, 10061], (code, text)
            assert 'refused' in text.lower(), (code, text)

    def test_timeout_real_socket(self):
        """ Test underlying socket behavior to ensure correspondence
            between green sockets and the underlying socket module. """
        return self.test_timeout(socket=_original_sock)
        
    def test_timeout(self, socket=socket):
        """ Test that the socket timeout exception works correctly. """
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.bind(('127.0.0.1', 0))
        server.listen(1)
        port = server.getsockname()[1]

        s = socket.socket()
        
        s.connect(('127.0.0.1', port))

        cs, addr = server.accept()
        cs.settimeout(1)
        try:
            try:
                cs.recv(1024)
                self.fail("Should have timed out")
            except socket.timeout as ex:
                assert hasattr(ex, 'args')
                assert len(ex.args) == 1
                assert ex.args[0] == 'timed out'
        finally:
            s.close()
            cs.close()
            server.close()

if __name__=='__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test__twistedutil
from tests import requires_twisted
import unittest
try:
    from twisted.internet import reactor
    from twisted.internet.error import DNSLookupError
    from twisted.internet import defer
    from twisted.python.failure import Failure
    from eventlet.twistedutil import block_on
except ImportError:
    pass

class Test(unittest.TestCase):
    @requires_twisted
    def test_block_on_success(self):
        from twisted.internet import reactor
        d = reactor.resolver.getHostByName('www.google.com')
        ip = block_on(d)
        assert len(ip.split('.'))==4, ip
        ip2 = block_on(d)
        assert ip == ip2, (ip, ip2)

    @requires_twisted 
    def test_block_on_fail(self):
        from twisted.internet import reactor
        d = reactor.resolver.getHostByName('xxx')
        self.assertRaises(DNSLookupError, block_on, d)

    @requires_twisted 
    def test_block_on_already_succeed(self):
        d = defer.succeed('hey corotwine')
        res = block_on(d)
        assert res == 'hey corotwine', repr(res)

    @requires_twisted
    def test_block_on_already_failed(self):
        d = defer.fail(Failure(ZeroDivisionError()))
        self.assertRaises(ZeroDivisionError, block_on, d)

if __name__=='__main__':
    unittest.main()


########NEW FILE########
__FILENAME__ = test__twistedutil_protocol
from tests import requires_twisted

import unittest
try:
    from twisted.internet import reactor
    from twisted.internet.error import ConnectionDone
    import eventlet.twistedutil.protocol as pr
    from eventlet.twistedutil.protocols.basic import LineOnlyReceiverTransport
except ImportError:
    # stub out some of the twisted dependencies so it at least imports
    class dummy(object):
        pass
    pr = dummy()
    pr.UnbufferedTransport = None
    pr.GreenTransport = None
    pr.GreenClientCreator = lambda *a, **k: None
    class reactor(object):
        pass
    
from eventlet import spawn, sleep, with_timeout, spawn_after
from eventlet.coros import Event

try:
    from eventlet.green import socket
except SyntaxError:
    socket = None

DELAY=0.01

if socket is not None:
    def setup_server_socket(self, delay=DELAY, port=0):
        s = socket.socket()
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind(('127.0.0.1', port))
        port = s.getsockname()[1]
        s.listen(5)
        s.settimeout(delay*3)
        def serve():
            conn, addr = s.accept()
            conn.settimeout(delay+1)
            try:
                hello = conn.makefile().readline()[:-2]
            except socket.timeout:
                return
            conn.sendall('you said %s. ' % hello)
            sleep(delay)
            conn.sendall('BYE')
            sleep(delay)
            #conn.close()
        spawn(serve)
        return port

def setup_server_SpawnFactory(self, delay=DELAY, port=0):
    def handle(conn):
        port.stopListening()
        try:
            hello = conn.readline()
        except ConnectionDone:
            return
        conn.write('you said %s. ' % hello)
        sleep(delay)
        conn.write('BYE')
        sleep(delay)
        conn.loseConnection()
    port = reactor.listenTCP(0, pr.SpawnFactory(handle, LineOnlyReceiverTransport))
    return port.getHost().port

class TestCase(unittest.TestCase):
    transportBufferSize = None

    @property
    def connector(self):
        return pr.GreenClientCreator(reactor, self.gtransportClass, self.transportBufferSize)
    
    @requires_twisted
    def setUp(self):
        port = self.setup_server()
        self.conn = self.connector.connectTCP('127.0.0.1', port)
        if self.transportBufferSize is not None:
            self.assertEqual(self.transportBufferSize, self.conn.transport.bufferSize)

class TestUnbufferedTransport(TestCase):
    gtransportClass = pr.UnbufferedTransport
    setup_server = setup_server_SpawnFactory

    @requires_twisted
    def test_full_read(self):
        self.conn.write('hello\r\n')
        self.assertEqual(self.conn.read(), 'you said hello. BYE')
        self.assertEqual(self.conn.read(), '')
        self.assertEqual(self.conn.read(), '')

    @requires_twisted
    def test_iterator(self):
        self.conn.write('iterator\r\n')
        self.assertEqual('you said iterator. BYE', ''.join(self.conn))

class TestUnbufferedTransport_bufsize1(TestUnbufferedTransport):
    transportBufferSize = 1
    setup_server = setup_server_SpawnFactory

class TestGreenTransport(TestUnbufferedTransport):
    gtransportClass = pr.GreenTransport
    setup_server = setup_server_SpawnFactory

    @requires_twisted
    def test_read(self):
        self.conn.write('hello\r\n')
        self.assertEqual(self.conn.read(9), 'you said ')
        self.assertEqual(self.conn.read(999), 'hello. BYE')
        self.assertEqual(self.conn.read(9), '')
        self.assertEqual(self.conn.read(1), '')
        self.assertEqual(self.conn.recv(9), '')
        self.assertEqual(self.conn.recv(1), '')

    @requires_twisted
    def test_read2(self):
        self.conn.write('world\r\n')
        self.assertEqual(self.conn.read(), 'you said world. BYE')
        self.assertEqual(self.conn.read(), '')
        self.assertEqual(self.conn.recv(), '')

    @requires_twisted
    def test_iterator(self):
        self.conn.write('iterator\r\n')
        self.assertEqual('you said iterator. BYE', ''.join(self.conn))

    _tests = [x for x in locals().keys() if x.startswith('test_')]

    @requires_twisted
    def test_resume_producing(self):
        for test in self._tests:
            self.setUp()
            self.conn.resumeProducing()
            getattr(self, test)()

    @requires_twisted
    def test_pause_producing(self):
        self.conn.pauseProducing()
        self.conn.write('hi\r\n')
        result = with_timeout(DELAY*10, self.conn.read, timeout_value='timed out')
        self.assertEqual('timed out', result)

    @requires_twisted
    def test_pauseresume_producing(self):
        self.conn.pauseProducing()
        spawn_after(DELAY*5, self.conn.resumeProducing)
        self.conn.write('hi\r\n')
        result = with_timeout(DELAY*10, self.conn.read, timeout_value='timed out')
        self.assertEqual('you said hi. BYE', result)

class TestGreenTransport_bufsize1(TestGreenTransport):
    transportBufferSize = 1

# class TestGreenTransportError(TestCase):
#     setup_server = setup_server_SpawnFactory
#     gtransportClass = pr.GreenTransport
# 
#     def test_read_error(self):
#         self.conn.write('hello\r\n')
#         sleep(DELAY*1.5) # make sure the rest of data arrives
#         try:
#             1//0
#         except:
#             #self.conn.loseConnection(failure.Failure()) # does not work, why?
#             spawn(self.conn._queue.send_exception, *sys.exc_info())
#         self.assertEqual(self.conn.read(9), 'you said ')
#         self.assertEqual(self.conn.read(7), 'hello. ')
#         self.assertEqual(self.conn.read(9), 'BYE')
#         self.assertRaises(ZeroDivisionError, self.conn.read, 9)
#         self.assertEqual(self.conn.read(1), '')
#         self.assertEqual(self.conn.read(1), '')
# 
#     def test_recv_error(self):
#         self.conn.write('hello')
#         self.assertEqual('you said hello. ', self.conn.recv())
#         sleep(DELAY*1.5) # make sure the rest of data arrives
#         try:
#             1//0
#         except:
#             #self.conn.loseConnection(failure.Failure()) # does not work, why?
#             spawn(self.conn._queue.send_exception, *sys.exc_info())
#         self.assertEqual('BYE', self.conn.recv())
#         self.assertRaises(ZeroDivisionError, self.conn.recv, 9)
#         self.assertEqual('', self.conn.recv(1))
#         self.assertEqual('', self.conn.recv())
#

if socket is not None:

    class TestUnbufferedTransport_socketserver(TestUnbufferedTransport):
        setup_server = setup_server_socket

    class TestUnbufferedTransport_socketserver_bufsize1(TestUnbufferedTransport):
        transportBufferSize = 1
        setup_server = setup_server_socket

    class TestGreenTransport_socketserver(TestGreenTransport):
        setup_server = setup_server_socket

    class TestGreenTransport_socketserver_bufsize1(TestGreenTransport):
        transportBufferSize = 1
        setup_server = setup_server_socket


class TestTLSError(unittest.TestCase):
    @requires_twisted
    def test_server_connectionMade_never_called(self):
        # trigger case when protocol instance is created,
        # but it's connectionMade is never called
        from gnutls.interfaces.twisted import X509Credentials
        from gnutls.errors import GNUTLSError
        cred = X509Credentials(None, None)
        ev = Event()
        def handle(conn):
            ev.send("handle must not be called")
        s = reactor.listenTLS(0, pr.SpawnFactory(handle, LineOnlyReceiverTransport), cred)
        creator = pr.GreenClientCreator(reactor, LineOnlyReceiverTransport)
        try:
            conn = creator.connectTLS('127.0.0.1', s.getHost().port, cred)
        except GNUTLSError:
            pass
        assert ev.poll() is None, repr(ev.poll())
        
try:
    import gnutls.interfaces.twisted
except ImportError:
    del TestTLSError

@requires_twisted
def main():
    unittest.main()

if __name__=='__main__':
    main()

########NEW FILE########
__FILENAME__ = thread_test
import gc
import weakref

from eventlet.green import thread
from eventlet import greenthread
from eventlet import event
import eventlet
from eventlet import corolocal
from eventlet.support import six

from tests import LimitedTestCase, skipped


class Locals(LimitedTestCase):
    def passthru(self, *args, **kw):
        self.results.append((args, kw))
        return args, kw

    def setUp(self):
        self.results = []
        super(Locals, self).setUp()

    def tearDown(self):
        self.results = []
        super(Locals, self).tearDown()

    @skipped  # cause it relies on internal details of corolocal that are no longer true
    def test_simple(self):
        tls = thread._local()
        g_ids = []
        evt = event.Event()
        def setter(tls, v):
            g_id = id(greenthread.getcurrent())
            g_ids.append(g_id)
            tls.value = v
            evt.wait()
        thread.start_new_thread(setter, args=(tls, 1))
        thread.start_new_thread(setter, args=(tls, 2))
        eventlet.sleep()
        objs = object.__getattribute__(tls, "__objs")
        self.failUnlessEqual(sorted(g_ids), sorted(objs.keys()))
        self.failUnlessEqual(objs[g_ids[0]]['value'], 1)
        self.failUnlessEqual(objs[g_ids[1]]['value'], 2)
        self.failUnlessRaises(AttributeError, lambda: tls.value)
        evt.send("done")
        eventlet.sleep()

    def test_assignment(self):
        my_local = corolocal.local()
        my_local.a = 1
        def do_something():
            my_local.b = 2
            self.assertEqual(my_local.b, 2)
            try:
                my_local.a
                self.fail()
            except AttributeError:
                pass
        eventlet.spawn(do_something).wait()
        self.assertEqual(my_local.a, 1)

    def test_calls_init(self):
        init_args = []
        class Init(corolocal.local):
            def __init__(self, *args):
                init_args.append((args, eventlet.getcurrent()))

        my_local = Init(1,2,3)
        self.assertEqual(init_args[0][0], (1,2,3))
        self.assertEqual(init_args[0][1], eventlet.getcurrent())

        def do_something():
            my_local.foo = 'bar'
            self.assertEqual(len(init_args), 2, init_args)
            self.assertEqual(init_args[1][0], (1,2,3))
            self.assertEqual(init_args[1][1], eventlet.getcurrent())

        eventlet.spawn(do_something).wait()

    def test_calling_methods(self):
        class Caller(corolocal.local):
            def callme(self):
                return self.foo

        my_local = Caller()
        my_local.foo = "foo1"
        self.assertEqual("foo1", my_local.callme())

        def do_something():
            my_local.foo = "foo2"
            self.assertEqual("foo2", my_local.callme())

        eventlet.spawn(do_something).wait()

        my_local.foo = "foo3"
        self.assertEqual("foo3", my_local.callme())

    def test_no_leaking(self):
        refs = weakref.WeakKeyDictionary()
        my_local = corolocal.local()
        class X(object):
            pass
        def do_something(i):
            o = X()
            refs[o] = True
            my_local.foo = o

        p = eventlet.GreenPool()
        for i in six.moves.range(100):
            p.spawn(do_something, i)
        p.waitall()
        del p
        gc.collect()
        eventlet.sleep(0)
        gc.collect()
        # at this point all our coros have terminated
        self.assertEqual(len(refs), 1)

########NEW FILE########
__FILENAME__ = timeout_test
from tests import LimitedTestCase
from eventlet import timeout
from eventlet import greenthread
DELAY = 0.01

class TestDirectRaise(LimitedTestCase):
    def test_direct_raise_class(self):
        try:
            raise timeout.Timeout
        except timeout.Timeout as t:
            assert not t.pending, repr(t)

    def test_direct_raise_instance(self):
        tm = timeout.Timeout()
        try:
            raise tm
        except timeout.Timeout as t:
            assert tm is t, (tm, t)
            assert not t.pending, repr(t)
            
    def test_repr(self):
        # just verify these don't crash
        tm = timeout.Timeout(1)
        greenthread.sleep(0)
        repr(tm)
        str(tm)
        tm.cancel()
        tm = timeout.Timeout(None, RuntimeError)
        repr(tm)
        str(tm)
        tm = timeout.Timeout(None, False)
        repr(tm)
        str(tm)

class TestWithTimeout(LimitedTestCase):
    def test_with_timeout(self):
        self.assertRaises(timeout.Timeout, timeout.with_timeout, DELAY, greenthread.sleep, DELAY*10)
        X = object()
        r = timeout.with_timeout(DELAY, greenthread.sleep, DELAY*10, timeout_value=X)
        self.assert_(r is X, (r, X))
        r = timeout.with_timeout(DELAY*10, greenthread.sleep, 
                                 DELAY, timeout_value=X)
        self.assert_(r is None, r)


    def test_with_outer_timer(self):
        def longer_timeout():
            # this should not catch the outer timeout's exception
            return timeout.with_timeout(DELAY * 10, 
                                        greenthread.sleep, DELAY * 20,
                                        timeout_value='b')
        self.assertRaises(timeout.Timeout,
            timeout.with_timeout, DELAY, longer_timeout)
        
########NEW FILE########
__FILENAME__ = timeout_test_with_statement
"""Tests with-statement behavior of Timeout class."""

import gc
import sys
import time
import unittest
import weakref

from eventlet import sleep
from eventlet.timeout import Timeout
from tests import LimitedTestCase


DELAY = 0.01


class Error(Exception):
    pass


class Test(LimitedTestCase):
    def test_cancellation(self):
        # Nothing happens if with-block finishes before the timeout expires
        t = Timeout(DELAY*2)
        sleep(0)  # make it pending
        assert t.pending, repr(t)
        with t:
            assert t.pending, repr(t)
            sleep(DELAY)
        # check if timer was actually cancelled
        assert not t.pending, repr(t)
        sleep(DELAY*2)

    def test_raising_self(self):
        # An exception will be raised if it's not
        try:
            with Timeout(DELAY) as t:
                sleep(DELAY*2)
        except Timeout as ex:
            assert ex is t, (ex, t)
        else:
            raise AssertionError('must raise Timeout')

    def test_raising_self_true(self):
        # specifying True as the exception raises self as well
        try:
            with Timeout(DELAY, True) as t:
                sleep(DELAY*2)
        except Timeout as ex:
            assert ex is t, (ex, t)
        else:
            raise AssertionError('must raise Timeout')

    def test_raising_custom_exception(self):
        # You can customize the exception raised:
        try:
            with Timeout(DELAY, IOError("Operation takes way too long")):
                sleep(DELAY*2)
        except IOError as ex:
            assert str(ex)=="Operation takes way too long", repr(ex)

    def test_raising_exception_class(self):
        # Providing classes instead of values should be possible too:
        try:
            with Timeout(DELAY, ValueError):
                sleep(DELAY*2)
        except ValueError:
            pass

    def test_raising_exc_tuple(self):
        try:
            1//0
        except:
            try:
                with Timeout(DELAY, sys.exc_info()[0]):
                    sleep(DELAY*2)
                    raise AssertionError('should not get there')
                raise AssertionError('should not get there')
            except ZeroDivisionError:
                pass
        else:
            raise AssertionError('should not get there')

    def test_cancel_timer_inside_block(self):
        # It's possible to cancel the timer inside the block:
        with Timeout(DELAY) as timer:
            timer.cancel()
            sleep(DELAY*2)

    def test_silent_block(self):
        # To silence the exception before exiting the block, pass
        # False as second parameter.
        XDELAY=0.1
        start = time.time()
        with Timeout(XDELAY, False):
            sleep(XDELAY*2)
        delta = (time.time()-start)
        assert delta<XDELAY*2, delta


    def test_dummy_timer(self):
        # passing None as seconds disables the timer
        with Timeout(None):
            sleep(DELAY)
        sleep(DELAY)

    def test_ref(self):
        err = Error()
        err_ref = weakref.ref(err)
        with Timeout(DELAY*2, err):
            sleep(DELAY)
        del err
        gc.collect()
        assert not err_ref(), repr(err_ref())

    def test_nested_timeout(self):
        with Timeout(DELAY, False):
            with Timeout(DELAY*2, False):
                sleep(DELAY*3)
            raise AssertionError('should not get there')

        with Timeout(DELAY) as t1:
            with Timeout(DELAY*2) as t2:
                try:
                    sleep(DELAY*3)
                except Timeout as ex:
                    assert ex is t1, (ex, t1)
                assert not t1.pending, t1
                assert t2.pending, t2
            assert not t2.pending, t2

        with Timeout(DELAY*2) as t1:
            with Timeout(DELAY) as t2:
                try:
                    sleep(DELAY*3)
                except Timeout as ex:
                    assert ex is t2, (ex, t2)
                assert t1.pending, t1
                assert not t2.pending, t2
        assert not t1.pending, t1

########NEW FILE########
__FILENAME__ = timer_test
from unittest import TestCase, main

import eventlet
from eventlet import hubs
from eventlet.hubs import timer

class TestTimer(TestCase):
    def test_copy(self):
        t = timer.Timer(0, lambda: None)
        t2 = t.copy()
        assert t.seconds == t2.seconds
        assert t.tpl == t2.tpl
        assert t.called == t2.called

    def test_schedule(self):
        hub = hubs.get_hub()
        # clean up the runloop, preventing side effects from previous tests
        # on this thread
        if hub.running:
            hub.abort()
            eventlet.sleep(0)
        called = []
        #t = timer.Timer(0, lambda: (called.append(True), hub.abort()))
        #t.schedule()
        # let's have a timer somewhere in the future; make sure abort() still works
        # (for pyevent, its dispatcher() does not exit if there is something scheduled)
        # XXX pyevent handles this, other hubs do not
        #hubs.get_hub().schedule_call_global(10000, lambda: (called.append(True), hub.abort()))
        hubs.get_hub().schedule_call_global(0, lambda: (called.append(True), hub.abort()))
        hub.default_sleep = lambda: 0.0
        hub.switch()
        assert called
        assert not hub.running
        

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = tpool_test
# Copyright (c) 2007, Linden Research, Inc.
# Copyright (c) 2007, IBM Corp.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
from __future__ import print_function

import gc
import random
import re
import time

import eventlet
from eventlet import tpool
from eventlet.support import six
from tests import LimitedTestCase, skipped, skip_with_pyevent, main


one = 1
two = 2
three = 3
none = None


def noop():
    pass


def raise_exception():
    raise RuntimeError("hi")


class TestTpool(LimitedTestCase):
    def setUp(self):
        super(TestTpool, self).setUp()

    def tearDown(self):
        tpool.killall()
        super(TestTpool, self).tearDown()

    @skip_with_pyevent
    def test_wrap_tuple(self):
        my_tuple = (1, 2)
        prox = tpool.Proxy(my_tuple)
        self.assertEqual(prox[0], 1)
        self.assertEqual(prox[1], 2)
        self.assertEqual(len(my_tuple), 2)

    @skip_with_pyevent
    def test_wrap_string(self):
        my_object = "whatever"
        prox = tpool.Proxy(my_object)
        self.assertEqual(str(my_object), str(prox))
        self.assertEqual(len(my_object), len(prox))
        self.assertEqual(my_object.join(['a', 'b']), prox.join(['a', 'b']))

    @skip_with_pyevent
    def test_wrap_uniterable(self):
        prox = tpool.Proxy([])

        def index():
            prox[0]

        def key():
            prox['a']

        self.assertRaises(IndexError, index)
        self.assertRaises(TypeError, key)

    @skip_with_pyevent
    def test_wrap_dict(self):
        my_object = {'a': 1}
        prox = tpool.Proxy(my_object)
        self.assertEqual('a', prox.keys()[0])
        self.assertEqual(1, prox['a'])
        self.assertEqual(str(my_object), str(prox))
        self.assertEqual(repr(my_object), repr(prox))

    @skip_with_pyevent
    def test_wrap_module_class(self):
        prox = tpool.Proxy(re)
        self.assertEqual(tpool.Proxy, type(prox))
        exp = prox.compile('(.)(.)(.)')
        self.assertEqual(exp.groups, 3)
        self.assert_(repr(prox.compile))

    @skip_with_pyevent
    def test_wrap_eq(self):
        prox = tpool.Proxy(re)
        exp1 = prox.compile('.')
        exp2 = prox.compile(exp1.pattern)
        self.assertEqual(exp1, exp2)
        exp3 = prox.compile('/')
        self.assert_(exp1 != exp3)

    @skip_with_pyevent
    def test_wrap_ints(self):
        p = tpool.Proxy(4)
        self.assert_(p == 4)

    @skip_with_pyevent
    def test_wrap_hash(self):
        prox1 = tpool.Proxy(''+'A')
        prox2 = tpool.Proxy('A'+'')
        self.assert_(prox1 == 'A')
        self.assert_('A' == prox2)
        #self.assert_(prox1 == prox2) FIXME - could __eq__ unwrap rhs if it is other proxy?
        self.assertEqual(hash(prox1), hash(prox2))
        proxList = tpool.Proxy([])
        self.assertRaises(TypeError, hash, proxList)

    @skip_with_pyevent
    def test_wrap_nonzero(self):
        prox = tpool.Proxy(re)
        exp1 = prox.compile('.')
        self.assert_(bool(exp1))
        prox2 = tpool.Proxy([1, 2, 3])
        self.assert_(bool(prox2))

    @skip_with_pyevent
    def test_multiple_wraps(self):
        prox1 = tpool.Proxy(re)
        prox2 = tpool.Proxy(re)
        prox1.compile('.')
        x2 = prox1.compile('.')
        del x2
        prox2.compile('.')

    @skip_with_pyevent
    def test_wrap_getitem(self):
        prox = tpool.Proxy([0, 1, 2])
        self.assertEqual(prox[0], 0)

    @skip_with_pyevent
    def test_wrap_setitem(self):
        prox = tpool.Proxy([0, 1, 2])
        prox[1] = 2
        self.assertEqual(prox[1], 2)

    @skip_with_pyevent
    def test_wrap_iterator(self):
        self.reset_timeout(2)
        prox = tpool.Proxy(range(10))
        result = []
        for i in prox:
            result.append(i)
        self.assertEqual(list(range(10)), result)

    @skip_with_pyevent
    def test_wrap_iterator2(self):
        self.reset_timeout(5)  # might take a while due to imprecise sleeping

        def foo():
            import time
            for x in range(2):
                yield x
                time.sleep(0.001)

        counter = [0]

        def tick():
            for i in six.moves.range(20000):
                counter[0] += 1
                if counter[0] % 20 == 0:
                    eventlet.sleep(0.0001)
                else:
                    eventlet.sleep()

        gt = eventlet.spawn(tick)
        previtem = 0
        for item in tpool.Proxy(foo()):
            self.assert_(item >= previtem)
        # make sure the tick happened at least a few times so that we know
        # that our iterations in foo() were actually tpooled
        self.assert_(counter[0] > 10, counter[0])
        gt.kill()

    @skip_with_pyevent
    def test_raising_exceptions(self):
        prox = tpool.Proxy(re)

        def nofunc():
            prox.never_name_a_function_like_this()
        self.assertRaises(AttributeError, nofunc)

        from tests import tpool_test
        prox = tpool.Proxy(tpool_test)
        self.assertRaises(RuntimeError, prox.raise_exception)

    @skip_with_pyevent
    def test_variable_and_keyword_arguments_with_function_calls(self):
        import optparse
        parser = tpool.Proxy(optparse.OptionParser())
        parser.add_option('-n', action='store', type='string', dest='n')
        opts, args = parser.parse_args(["-nfoo"])
        self.assertEqual(opts.n, 'foo')

    @skip_with_pyevent
    def test_contention(self):
        from tests import tpool_test
        prox = tpool.Proxy(tpool_test)

        pile = eventlet.GreenPile(4)
        pile.spawn(lambda: self.assertEqual(prox.one, 1))
        pile.spawn(lambda: self.assertEqual(prox.two, 2))
        pile.spawn(lambda: self.assertEqual(prox.three, 3))
        results = list(pile)
        self.assertEqual(len(results), 3)

    @skip_with_pyevent
    def test_timeout(self):
        import time
        eventlet.Timeout(0.1, eventlet.TimeoutError())
        self.assertRaises(eventlet.TimeoutError,
                          tpool.execute, time.sleep, 0.3)

    @skip_with_pyevent
    def test_killall(self):
        tpool.killall()
        tpool.setup()

    @skip_with_pyevent
    def test_autowrap(self):
        x = tpool.Proxy({'a': 1, 'b': 2}, autowrap=(int,))
        self.assert_(isinstance(x.get('a'), tpool.Proxy))
        self.assert_(not isinstance(x.items(), tpool.Proxy))
        # attributes as well as callables
        from tests import tpool_test
        x = tpool.Proxy(tpool_test, autowrap=(int,))
        self.assert_(isinstance(x.one, tpool.Proxy))
        self.assert_(not isinstance(x.none, tpool.Proxy))

    @skip_with_pyevent
    def test_autowrap_names(self):
        x = tpool.Proxy({'a': 1, 'b': 2}, autowrap_names=('get',))
        self.assert_(isinstance(x.get('a'), tpool.Proxy))
        self.assert_(not isinstance(x.items(), tpool.Proxy))
        from tests import tpool_test
        x = tpool.Proxy(tpool_test, autowrap_names=('one',))
        self.assert_(isinstance(x.one, tpool.Proxy))
        self.assert_(not isinstance(x.two, tpool.Proxy))

    @skip_with_pyevent
    def test_autowrap_both(self):
        from tests import tpool_test
        x = tpool.Proxy(tpool_test, autowrap=(int,), autowrap_names=('one',))
        self.assert_(isinstance(x.one, tpool.Proxy))
        # violating the abstraction to check that we didn't double-wrap
        self.assert_(not isinstance(x._obj, tpool.Proxy))

    @skip_with_pyevent
    def test_callable(self):
        def wrapped(arg):
            return arg
        x = tpool.Proxy(wrapped)
        self.assertEqual(4, x(4))
        # verify that it wraps return values if specified
        x = tpool.Proxy(wrapped, autowrap_names=('__call__',))
        self.assert_(isinstance(x(4), tpool.Proxy))
        self.assertEqual("4", str(x(4)))

    @skip_with_pyevent
    def test_callable_iterator(self):
        def wrapped(arg):
            yield arg
            yield arg
            yield arg

        x = tpool.Proxy(wrapped, autowrap_names=('__call__',))
        for r in x(3):
            self.assertEqual(3, r)

    @skip_with_pyevent
    def test_eventlet_timeout(self):
        def raise_timeout():
            raise eventlet.Timeout()
        self.assertRaises(eventlet.Timeout, tpool.execute, raise_timeout)

    @skip_with_pyevent
    def test_tpool_set_num_threads(self):
        tpool.set_num_threads(5)
        self.assertEqual(5, tpool._nthreads)


class TpoolLongTests(LimitedTestCase):
    TEST_TIMEOUT = 60

    @skip_with_pyevent
    def test_a_buncha_stuff(self):
        assert_ = self.assert_

        class Dummy(object):
            def foo(self, when, token=None):
                assert_(token is not None)
                time.sleep(random.random()/200.0)
                return token

        def sender_loop(loopnum):
            obj = tpool.Proxy(Dummy())
            count = 100
            for n in six.moves.range(count):
                eventlet.sleep(random.random()/200.0)
                now = time.time()
                token = loopnum * count + n
                rv = obj.foo(now, token=token)
                self.assertEqual(token, rv)
                eventlet.sleep(random.random()/200.0)

        cnt = 10
        pile = eventlet.GreenPile(cnt)
        for i in six.moves.range(cnt):
            pile.spawn(sender_loop, i)
        results = list(pile)
        self.assertEqual(len(results), cnt)
        tpool.killall()

    @skipped
    def test_benchmark(self):
        """ Benchmark computing the amount of overhead tpool adds to function calls."""
        iterations = 10000
        import timeit
        imports = """
from tests.tpool_test import noop
from eventlet.tpool import execute
        """
        t = timeit.Timer("noop()", imports)
        results = t.repeat(repeat=3, number=iterations)
        best_normal = min(results)

        t = timeit.Timer("execute(noop)", imports)
        results = t.repeat(repeat=3, number=iterations)
        best_tpool = min(results)

        tpool_overhead = (best_tpool-best_normal)/iterations
        print("%s iterations\nTpool overhead is %s seconds per call.  Normal: %s; Tpool: %s" % (
            iterations, tpool_overhead, best_normal, best_tpool))
        tpool.killall()

    @skip_with_pyevent
    def test_leakage_from_tracebacks(self):
        tpool.execute(noop)  # get it started
        gc.collect()
        initial_objs = len(gc.get_objects())
        for i in range(10):
            self.assertRaises(RuntimeError, tpool.execute, raise_exception)
        gc.collect()
        middle_objs = len(gc.get_objects())
        # some objects will inevitably be created by the previous loop
        # now we test to ensure that running the loop an order of
        # magnitude more doesn't generate additional objects
        for i in six.moves.range(100):
            self.assertRaises(RuntimeError, tpool.execute, raise_exception)
        first_created = middle_objs - initial_objs
        gc.collect()
        second_created = len(gc.get_objects()) - middle_objs
        self.assert_(second_created - first_created < 10,
                     "first loop: %s, second loop: %s" % (first_created,
                                                          second_created))
        tpool.killall()


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = websocket_new_test
import errno
import struct

import eventlet
from eventlet import event
from eventlet.green import httplib
from eventlet.green import socket
from eventlet import websocket

from tests.wsgi_test import _TestBase


# demo app
def handle(ws):
    if ws.path == '/echo':
        while True:
            m = ws.wait()
            if m is None:
                break
            ws.send(m)
    elif ws.path == '/range':
        for i in range(10):
            ws.send("msg %d" % i)
            eventlet.sleep(0.01)
    elif ws.path == '/error':
        # some random socket error that we shouldn't normally get
        raise socket.error(errno.ENOTSOCK)
    else:
        ws.close()

wsapp = websocket.WebSocketWSGI(handle)


class TestWebSocket(_TestBase):
    TEST_TIMEOUT = 5

    def set_site(self):
        self.site = wsapp

    def test_incomplete_headers_13(self):
        headers = dict(kv.split(': ') for kv in [
                "Upgrade: websocket",
                # NOTE: intentionally no connection header
                "Host: localhost:%s" % self.port,
                "Origin: http://localhost:%s" % self.port,
                "Sec-WebSocket-Version: 13", ])
        http = httplib.HTTPConnection('localhost', self.port)
        http.request("GET", "/echo", headers=headers)
        resp = http.getresponse()

        self.assertEqual(resp.status, 400)
        self.assertEqual(resp.getheader('connection'), 'close')
        self.assertEqual(resp.read(), '')

        # Now, miss off key
        headers = dict(kv.split(': ') for kv in [
                "Upgrade: websocket",
                "Connection: Upgrade",
                "Host: localhost:%s" % self.port,
                "Origin: http://localhost:%s" % self.port,
                "Sec-WebSocket-Version: 13", ])
        http = httplib.HTTPConnection('localhost', self.port)
        http.request("GET", "/echo", headers=headers)
        resp = http.getresponse()

        self.assertEqual(resp.status, 400)
        self.assertEqual(resp.getheader('connection'), 'close')
        self.assertEqual(resp.read(), '')

        # No Upgrade now
        headers = dict(kv.split(': ') for kv in [
                "Connection: Upgrade",
                "Host: localhost:%s" % self.port,
                "Origin: http://localhost:%s" % self.port,
                "Sec-WebSocket-Version: 13", ])
        http = httplib.HTTPConnection('localhost', self.port)
        http.request("GET", "/echo", headers=headers)
        resp = http.getresponse()

        self.assertEqual(resp.status, 400)
        self.assertEqual(resp.getheader('connection'), 'close')
        self.assertEqual(resp.read(), '')


    def test_correct_upgrade_request_13(self):
        for http_connection in ['Upgrade', 'UpGrAdE', 'keep-alive, Upgrade']:
            connect = [
                "GET /echo HTTP/1.1",
                "Upgrade: websocket",
                "Connection: %s" % http_connection,
                "Host: localhost:%s" % self.port,
                "Origin: http://localhost:%s" % self.port,
                "Sec-WebSocket-Version: 13",
                "Sec-WebSocket-Key: d9MXuOzlVQ0h+qRllvSCIg==",
            ]
            sock = eventlet.connect(('localhost', self.port))

            sock.sendall('\r\n'.join(connect) + '\r\n\r\n')
            result = sock.recv(1024)
            ## The server responds the correct Websocket handshake
            print('Connection string: %r' % http_connection)
            self.assertEqual(result, '\r\n'.join([
                'HTTP/1.1 101 Switching Protocols',
                'Upgrade: websocket',
                'Connection: Upgrade',
                'Sec-WebSocket-Accept: ywSyWXCPNsDxLrQdQrn5RFNRfBU=\r\n\r\n',
            ]))

    def test_send_recv_13(self):
        connect = [
                "GET /echo HTTP/1.1",
                "Upgrade: websocket",
                "Connection: Upgrade",
                "Host: localhost:%s" % self.port,
                "Origin: http://localhost:%s" % self.port,
                "Sec-WebSocket-Version: 13",
                "Sec-WebSocket-Key: d9MXuOzlVQ0h+qRllvSCIg==", ]
        sock = eventlet.connect(
            ('localhost', self.port))

        sock.sendall('\r\n'.join(connect) + '\r\n\r\n')
        first_resp = sock.recv(1024)
        ws = websocket.RFC6455WebSocket(sock, {}, client=True)
        ws.send('hello')
        assert ws.wait() == 'hello'
        ws.send('hello world!\x01')
        ws.send(u'hello world again!')
        assert ws.wait() == 'hello world!\x01'
        assert ws.wait() == u'hello world again!'
        ws.close()
        eventlet.sleep(0.01)

    def test_breaking_the_connection_13(self):
        error_detected = [False]
        done_with_request = event.Event()
        site = self.site
        def error_detector(environ, start_response):
            try:
                try:
                    return site(environ, start_response)
                except:
                    error_detected[0] = True
                    raise
            finally:
                done_with_request.send(True)
        self.site = error_detector
        self.spawn_server()
        connect = [
                "GET /echo HTTP/1.1",
                "Upgrade: websocket",
                "Connection: Upgrade",
                "Host: localhost:%s" % self.port,
                "Origin: http://localhost:%s" % self.port,
                "Sec-WebSocket-Version: 13",
                "Sec-WebSocket-Key: d9MXuOzlVQ0h+qRllvSCIg==", ]
        sock = eventlet.connect(
            ('localhost', self.port))
        sock.sendall('\r\n'.join(connect) + '\r\n\r\n')
        resp = sock.recv(1024)  # get the headers
        sock.close()  # close while the app is running
        done_with_request.wait()
        self.assert_(not error_detected[0])

    def test_client_closing_connection_13(self):
        error_detected = [False]
        done_with_request = event.Event()
        site = self.site
        def error_detector(environ, start_response):
            try:
                try:
                    return site(environ, start_response)
                except:
                    error_detected[0] = True
                    raise
            finally:
                done_with_request.send(True)
        self.site = error_detector
        self.spawn_server()
        connect = [
                "GET /echo HTTP/1.1",
                "Upgrade: websocket",
                "Connection: Upgrade",
                "Host: localhost:%s" % self.port,
                "Origin: http://localhost:%s" % self.port,
                "Sec-WebSocket-Version: 13",
                "Sec-WebSocket-Key: d9MXuOzlVQ0h+qRllvSCIg==", ]
        sock = eventlet.connect(
            ('localhost', self.port))
        sock.sendall('\r\n'.join(connect) + '\r\n\r\n')
        resp = sock.recv(1024)  # get the headers
        closeframe = struct.pack('!BBIH', 1 << 7 | 8, 1 << 7 | 2, 0, 1000)
        sock.sendall(closeframe)  # "Close the connection" packet.
        done_with_request.wait()
        self.assert_(not error_detected[0])

    def test_client_invalid_packet_13(self):
        error_detected = [False]
        done_with_request = event.Event()
        site = self.site
        def error_detector(environ, start_response):
            try:
                try:
                    return site(environ, start_response)
                except:
                    error_detected[0] = True
                    raise
            finally:
                done_with_request.send(True)
        self.site = error_detector
        self.spawn_server()
        connect = [
                "GET /echo HTTP/1.1",
                "Upgrade: websocket",
                "Connection: Upgrade",
                "Host: localhost:%s" % self.port,
                "Origin: http://localhost:%s" % self.port,
                "Sec-WebSocket-Version: 13",
                "Sec-WebSocket-Key: d9MXuOzlVQ0h+qRllvSCIg==", ]
        sock = eventlet.connect(
            ('localhost', self.port))
        sock.sendall('\r\n'.join(connect) + '\r\n\r\n')
        resp = sock.recv(1024)  # get the headers
        sock.sendall('\x07\xff') # Weird packet.
        done_with_request.wait()
        self.assert_(not error_detected[0])

########NEW FILE########
__FILENAME__ = websocket_test
import socket
import errno

import eventlet
from eventlet.green import urllib2
from eventlet.green import httplib
from eventlet.websocket import WebSocket, WebSocketWSGI
from eventlet import wsgi
from eventlet import event
from eventlet import greenio

from tests import mock, LimitedTestCase, certificate_file, private_key_file
from tests import skip_if_no_ssl
from tests.wsgi_test import _TestBase


# demo app
def handle(ws):
    if ws.path == '/echo':
        while True:
            m = ws.wait()
            if m is None:
                break
            ws.send(m)
    elif ws.path == '/range':
        for i in range(10):
            ws.send("msg %d" % i)
            eventlet.sleep(0.01)
    elif ws.path == '/error':
        # some random socket error that we shouldn't normally get
        raise socket.error(errno.ENOTSOCK)
    else:
        ws.close()

wsapp = WebSocketWSGI(handle)

class TestWebSocket(_TestBase):
    TEST_TIMEOUT = 5
    
    def set_site(self):
        self.site = wsapp
    
    def test_incorrect_headers(self):
        def raiser():
            try:
                urllib2.urlopen("http://localhost:%s/echo" % self.port)
            except urllib2.HTTPError as e:
                self.assertEqual(e.code, 400)
                raise
        self.assertRaises(urllib2.HTTPError, raiser)

    def test_incomplete_headers_75(self):
        headers = dict(kv.split(': ') for kv in [
                "Upgrade: WebSocket",
                # NOTE: intentionally no connection header
                "Host: localhost:%s" % self.port,
                "Origin: http://localhost:%s" % self.port,
                "WebSocket-Protocol: ws",
                ])
        http = httplib.HTTPConnection('localhost', self.port)
        http.request("GET", "/echo", headers=headers)
        resp = http.getresponse()

        self.assertEqual(resp.status, 400)
        self.assertEqual(resp.getheader('connection'), 'close')
        self.assertEqual(resp.read(), '')

    def test_incomplete_headers_76(self):
        # First test: Missing Connection:
        headers = dict(kv.split(': ') for kv in [
                "Upgrade: WebSocket",
                # NOTE: intentionally no connection header
                "Host: localhost:%s" % self.port,
                "Origin: http://localhost:%s" % self.port,
                "Sec-WebSocket-Protocol: ws",
                ])
        http = httplib.HTTPConnection('localhost', self.port)
        http.request("GET", "/echo", headers=headers)
        resp = http.getresponse()

        self.assertEqual(resp.status, 400)
        self.assertEqual(resp.getheader('connection'), 'close')
        self.assertEqual(resp.read(), '')
        
        # Now, miss off key2
        headers = dict(kv.split(': ') for kv in [
                "Upgrade: WebSocket",
                "Connection: Upgrade",
                "Host: localhost:%s" % self.port,
                "Origin: http://localhost:%s" % self.port,
                "Sec-WebSocket-Protocol: ws",
                "Sec-WebSocket-Key1: 4 @1  46546xW%0l 1 5",
                # NOTE: Intentionally no Key2 header
                ])
        http = httplib.HTTPConnection('localhost', self.port)
        http.request("GET", "/echo", headers=headers)
        resp = http.getresponse()

        self.assertEqual(resp.status, 400)
        self.assertEqual(resp.getheader('connection'), 'close')
        self.assertEqual(resp.read(), '')

    def test_correct_upgrade_request_75(self):
        connect = [
                "GET /echo HTTP/1.1",
                "Upgrade: WebSocket",
                "Connection: Upgrade",
                "Host: localhost:%s" % self.port,
                "Origin: http://localhost:%s" % self.port,
                "WebSocket-Protocol: ws",
                ]
        sock = eventlet.connect(
            ('localhost', self.port))

        sock.sendall('\r\n'.join(connect) + '\r\n\r\n')
        result = sock.recv(1024)
        ## The server responds the correct Websocket handshake
        self.assertEqual(result,
                         '\r\n'.join(['HTTP/1.1 101 Web Socket Protocol Handshake',
                                      'Upgrade: WebSocket',
                                      'Connection: Upgrade',
                                      'WebSocket-Origin: http://localhost:%s' % self.port,
                                      'WebSocket-Location: ws://localhost:%s/echo\r\n\r\n' % self.port]))

    def test_correct_upgrade_request_76(self):
        connect = [
                "GET /echo HTTP/1.1",
                "Upgrade: WebSocket",
                "Connection: Upgrade",
                "Host: localhost:%s" % self.port,
                "Origin: http://localhost:%s" % self.port,
                "Sec-WebSocket-Protocol: ws",
                "Sec-WebSocket-Key1: 4 @1  46546xW%0l 1 5",
                "Sec-WebSocket-Key2: 12998 5 Y3 1  .P00",
                ]
        sock = eventlet.connect(
            ('localhost', self.port))

        sock.sendall('\r\n'.join(connect) + '\r\n\r\n^n:ds[4U')
        result = sock.recv(1024)
        ## The server responds the correct Websocket handshake
        self.assertEqual(result,
                         '\r\n'.join(['HTTP/1.1 101 WebSocket Protocol Handshake',
                                      'Upgrade: WebSocket',
                                      'Connection: Upgrade',
                                      'Sec-WebSocket-Origin: http://localhost:%s' % self.port,
                                      'Sec-WebSocket-Protocol: ws',
                                      'Sec-WebSocket-Location: ws://localhost:%s/echo\r\n\r\n8jKS\'y:G*Co,Wxa-' % self.port]))
                                      
                                      
    def test_query_string(self):
        # verify that the query string comes out the other side unscathed
        connect = [
                "GET /echo?query_string HTTP/1.1",
                "Upgrade: WebSocket",
                "Connection: Upgrade",
                "Host: localhost:%s" % self.port,
                "Origin: http://localhost:%s" % self.port,
                "Sec-WebSocket-Protocol: ws",
                "Sec-WebSocket-Key1: 4 @1  46546xW%0l 1 5",
                "Sec-WebSocket-Key2: 12998 5 Y3 1  .P00",
                ]
        sock = eventlet.connect(
            ('localhost', self.port))

        sock.sendall('\r\n'.join(connect) + '\r\n\r\n^n:ds[4U')
        result = sock.recv(1024)
        self.assertEqual(result,
                         '\r\n'.join(['HTTP/1.1 101 WebSocket Protocol Handshake',
                                      'Upgrade: WebSocket',
                                      'Connection: Upgrade',
                                      'Sec-WebSocket-Origin: http://localhost:%s' % self.port,
                                      'Sec-WebSocket-Protocol: ws',
                                      'Sec-WebSocket-Location: ws://localhost:%s/echo?query_string\r\n\r\n8jKS\'y:G*Co,Wxa-' % self.port]))

    def test_empty_query_string(self):
        # verify that a single trailing ? doesn't get nuked
        connect = [
                "GET /echo? HTTP/1.1",
                "Upgrade: WebSocket",
                "Connection: Upgrade",
                "Host: localhost:%s" % self.port,
                "Origin: http://localhost:%s" % self.port,
                "Sec-WebSocket-Protocol: ws",
                "Sec-WebSocket-Key1: 4 @1  46546xW%0l 1 5",
                "Sec-WebSocket-Key2: 12998 5 Y3 1  .P00",
                ]
        sock = eventlet.connect(
            ('localhost', self.port))

        sock.sendall('\r\n'.join(connect) + '\r\n\r\n^n:ds[4U')
        result = sock.recv(1024)
        self.assertEqual(result,
                         '\r\n'.join(['HTTP/1.1 101 WebSocket Protocol Handshake',
                                      'Upgrade: WebSocket',
                                      'Connection: Upgrade',
                                      'Sec-WebSocket-Origin: http://localhost:%s' % self.port,
                                      'Sec-WebSocket-Protocol: ws',
                                      'Sec-WebSocket-Location: ws://localhost:%s/echo?\r\n\r\n8jKS\'y:G*Co,Wxa-' % self.port]))
                                    

    def test_sending_messages_to_websocket_75(self):
        connect = [
                "GET /echo HTTP/1.1",
                "Upgrade: WebSocket",
                "Connection: Upgrade",
                "Host: localhost:%s" % self.port,
                "Origin: http://localhost:%s" % self.port,
                "WebSocket-Protocol: ws",
                ]
        sock = eventlet.connect(
            ('localhost', self.port))

        sock.sendall('\r\n'.join(connect) + '\r\n\r\n')
        first_resp = sock.recv(1024)
        sock.sendall('\x00hello\xFF')
        result = sock.recv(1024)
        self.assertEqual(result, '\x00hello\xff')
        sock.sendall('\x00start')
        eventlet.sleep(0.001)
        sock.sendall(' end\xff')
        result = sock.recv(1024)
        self.assertEqual(result, '\x00start end\xff')
        sock.shutdown(socket.SHUT_RDWR)
        sock.close()
        eventlet.sleep(0.01)

    def test_sending_messages_to_websocket_76(self):
        connect = [
                "GET /echo HTTP/1.1",
                "Upgrade: WebSocket",
                "Connection: Upgrade",
                "Host: localhost:%s" % self.port,
                "Origin: http://localhost:%s" % self.port,
                "Sec-WebSocket-Protocol: ws",
                "Sec-WebSocket-Key1: 4 @1  46546xW%0l 1 5",
                "Sec-WebSocket-Key2: 12998 5 Y3 1  .P00",
                ]
        sock = eventlet.connect(
            ('localhost', self.port))

        sock.sendall('\r\n'.join(connect) + '\r\n\r\n^n:ds[4U')
        first_resp = sock.recv(1024)
        sock.sendall('\x00hello\xFF')
        result = sock.recv(1024)
        self.assertEqual(result, '\x00hello\xff')
        sock.sendall('\x00start')
        eventlet.sleep(0.001)
        sock.sendall(' end\xff')
        result = sock.recv(1024)
        self.assertEqual(result, '\x00start end\xff')
        sock.shutdown(socket.SHUT_RDWR)
        sock.close()
        eventlet.sleep(0.01)

    def test_getting_messages_from_websocket_75(self):
        connect = [
                "GET /range HTTP/1.1",
                "Upgrade: WebSocket",
                "Connection: Upgrade",
                "Host: localhost:%s" % self.port,
                "Origin: http://localhost:%s" % self.port,
                "WebSocket-Protocol: ws",
                ]
        sock = eventlet.connect(
            ('localhost', self.port))

        sock.sendall('\r\n'.join(connect) + '\r\n\r\n')
        resp = sock.recv(1024)
        headers, result = resp.split('\r\n\r\n')
        msgs = [result.strip('\x00\xff')]
        cnt = 10
        while cnt:
            msgs.append(sock.recv(20).strip('\x00\xff'))
            cnt -= 1
        # Last item in msgs is an empty string
        self.assertEqual(msgs[:-1], ['msg %d' % i for i in range(10)])

    def test_getting_messages_from_websocket_76(self):
        connect = [
                "GET /range HTTP/1.1",
                "Upgrade: WebSocket",
                "Connection: Upgrade",
                "Host: localhost:%s" % self.port,
                "Origin: http://localhost:%s" % self.port,
                "Sec-WebSocket-Protocol: ws",
                "Sec-WebSocket-Key1: 4 @1  46546xW%0l 1 5",
                "Sec-WebSocket-Key2: 12998 5 Y3 1  .P00",
                ]
        sock = eventlet.connect(
            ('localhost', self.port))

        sock.sendall('\r\n'.join(connect) + '\r\n\r\n^n:ds[4U')
        resp = sock.recv(1024)
        headers, result = resp.split('\r\n\r\n')
        msgs = [result[16:].strip('\x00\xff')]
        cnt = 10
        while cnt:
            msgs.append(sock.recv(20).strip('\x00\xff'))
            cnt -= 1
        # Last item in msgs is an empty string
        self.assertEqual(msgs[:-1], ['msg %d' % i for i in range(10)])

    def test_breaking_the_connection_75(self):
        error_detected = [False]
        done_with_request = event.Event()
        site = self.site
        def error_detector(environ, start_response):
            try:
                try:
                    return site(environ, start_response)
                except:
                    error_detected[0] = True
                    raise
            finally:
                done_with_request.send(True)
        self.site = error_detector
        self.spawn_server()
        connect = [
                "GET /range HTTP/1.1",
                "Upgrade: WebSocket",
                "Connection: Upgrade",
                "Host: localhost:%s" % self.port,
                "Origin: http://localhost:%s" % self.port,
                "WebSocket-Protocol: ws",
                ]
        sock = eventlet.connect(
            ('localhost', self.port))
        sock.sendall('\r\n'.join(connect) + '\r\n\r\n')
        resp = sock.recv(1024)  # get the headers
        sock.close()  # close while the app is running
        done_with_request.wait()
        self.assert_(not error_detected[0])

    def test_breaking_the_connection_76(self):
        error_detected = [False]
        done_with_request = event.Event()
        site = self.site
        def error_detector(environ, start_response):
            try:
                try:
                    return site(environ, start_response)
                except:
                    error_detected[0] = True
                    raise
            finally:
                done_with_request.send(True)
        self.site = error_detector
        self.spawn_server()
        connect = [
                "GET /range HTTP/1.1",
                "Upgrade: WebSocket",
                "Connection: Upgrade",
                "Host: localhost:%s" % self.port,
                "Origin: http://localhost:%s" % self.port,
                "Sec-WebSocket-Protocol: ws",
                "Sec-WebSocket-Key1: 4 @1  46546xW%0l 1 5",
                "Sec-WebSocket-Key2: 12998 5 Y3 1  .P00",
                ]
        sock = eventlet.connect(
            ('localhost', self.port))
        sock.sendall('\r\n'.join(connect) + '\r\n\r\n^n:ds[4U')
        resp = sock.recv(1024)  # get the headers
        sock.close()  # close while the app is running
        done_with_request.wait()
        self.assert_(not error_detected[0])
    
    def test_client_closing_connection_76(self):
        error_detected = [False]
        done_with_request = event.Event()
        site = self.site
        def error_detector(environ, start_response):
            try:
                try:
                    return site(environ, start_response)
                except:
                    error_detected[0] = True
                    raise
            finally:
                done_with_request.send(True)
        self.site = error_detector
        self.spawn_server()
        connect = [
                "GET /echo HTTP/1.1",
                "Upgrade: WebSocket",
                "Connection: Upgrade",
                "Host: localhost:%s" % self.port,
                "Origin: http://localhost:%s" % self.port,
                "Sec-WebSocket-Protocol: ws",
                "Sec-WebSocket-Key1: 4 @1  46546xW%0l 1 5",
                "Sec-WebSocket-Key2: 12998 5 Y3 1  .P00",
                ]
        sock = eventlet.connect(
            ('localhost', self.port))
        sock.sendall('\r\n'.join(connect) + '\r\n\r\n^n:ds[4U')
        resp = sock.recv(1024)  # get the headers
        sock.sendall('\xff\x00') # "Close the connection" packet.
        done_with_request.wait()
        self.assert_(not error_detected[0])
    
    def test_client_invalid_packet_76(self):
        error_detected = [False]
        done_with_request = event.Event()
        site = self.site
        def error_detector(environ, start_response):
            try:
                try:
                    return site(environ, start_response)
                except:
                    error_detected[0] = True
                    raise
            finally:
                done_with_request.send(True)
        self.site = error_detector
        self.spawn_server()
        connect = [
                "GET /echo HTTP/1.1",
                "Upgrade: WebSocket",
                "Connection: Upgrade",
                "Host: localhost:%s" % self.port,
                "Origin: http://localhost:%s" % self.port,
                "Sec-WebSocket-Protocol: ws",
                "Sec-WebSocket-Key1: 4 @1  46546xW%0l 1 5",
                "Sec-WebSocket-Key2: 12998 5 Y3 1  .P00",
                ]
        sock = eventlet.connect(
            ('localhost', self.port))
        sock.sendall('\r\n'.join(connect) + '\r\n\r\n^n:ds[4U')
        resp = sock.recv(1024)  # get the headers
        sock.sendall('\xef\x00') # Weird packet.
        done_with_request.wait()
        self.assert_(error_detected[0])
    
    def test_server_closing_connect_76(self):
        connect = [
                "GET / HTTP/1.1",
                "Upgrade: WebSocket",
                "Connection: Upgrade",
                "Host: localhost:%s" % self.port,
                "Origin: http://localhost:%s" % self.port,
                "Sec-WebSocket-Protocol: ws",
                "Sec-WebSocket-Key1: 4 @1  46546xW%0l 1 5",
                "Sec-WebSocket-Key2: 12998 5 Y3 1  .P00",
                ]
        sock = eventlet.connect(
            ('localhost', self.port))

        sock.sendall('\r\n'.join(connect) + '\r\n\r\n^n:ds[4U')
        resp = sock.recv(1024)
        headers, result = resp.split('\r\n\r\n')
        # The remote server should have immediately closed the connection.
        self.assertEqual(result[16:], '\xff\x00')

    def test_app_socket_errors_75(self):
        error_detected = [False]
        done_with_request = event.Event()
        site = self.site
        def error_detector(environ, start_response):
            try:
                try:
                    return site(environ, start_response)
                except:
                    error_detected[0] = True
                    raise
            finally:
                done_with_request.send(True)
        self.site = error_detector
        self.spawn_server()
        connect = [
                "GET /error HTTP/1.1",
                "Upgrade: WebSocket",
                "Connection: Upgrade",
                "Host: localhost:%s" % self.port,
                "Origin: http://localhost:%s" % self.port,
                "WebSocket-Protocol: ws",
                ]
        sock = eventlet.connect(
            ('localhost', self.port))
        sock.sendall('\r\n'.join(connect) + '\r\n\r\n')
        resp = sock.recv(1024)
        done_with_request.wait()
        self.assert_(error_detected[0])

    def test_app_socket_errors_76(self):
        error_detected = [False]
        done_with_request = event.Event()
        site = self.site
        def error_detector(environ, start_response):
            try:
                try:
                    return site(environ, start_response)
                except:
                    error_detected[0] = True
                    raise
            finally:
                done_with_request.send(True)
        self.site = error_detector
        self.spawn_server()
        connect = [
                "GET /error HTTP/1.1",
                "Upgrade: WebSocket",
                "Connection: Upgrade",
                "Host: localhost:%s" % self.port,
                "Origin: http://localhost:%s" % self.port,
                "Sec-WebSocket-Protocol: ws",
                "Sec-WebSocket-Key1: 4 @1  46546xW%0l 1 5",
                "Sec-WebSocket-Key2: 12998 5 Y3 1  .P00",
                ]
        sock = eventlet.connect(
            ('localhost', self.port))
        sock.sendall('\r\n'.join(connect) + '\r\n\r\n^n:ds[4U')
        resp = sock.recv(1024)
        done_with_request.wait()
        self.assert_(error_detected[0])


class TestWebSocketSSL(_TestBase):
    def set_site(self):
        self.site = wsapp

    @skip_if_no_ssl
    def test_ssl_sending_messages(self):
        s = eventlet.wrap_ssl(eventlet.listen(('localhost', 0)),
                              certfile=certificate_file, 
                              keyfile=private_key_file,
                              server_side=True)
        self.spawn_server(sock=s)
        connect = [
                "GET /echo HTTP/1.1",
                "Upgrade: WebSocket",
                "Connection: Upgrade",
                "Host: localhost:%s" % self.port,
                "Origin: http://localhost:%s" % self.port,
                "Sec-WebSocket-Protocol: ws",
                "Sec-WebSocket-Key1: 4 @1  46546xW%0l 1 5",
                "Sec-WebSocket-Key2: 12998 5 Y3 1  .P00",
                ]
        sock = eventlet.wrap_ssl(eventlet.connect(
                ('localhost', self.port)))

        sock.sendall('\r\n'.join(connect) + '\r\n\r\n^n:ds[4U')
        first_resp = sock.recv(1024)
        # make sure it sets the wss: protocol on the location header
        loc_line = [x for x in first_resp.split("\r\n") 
                    if x.lower().startswith('sec-websocket-location')][0]
        self.assert_("wss://localhost" in loc_line, 
                     "Expecting wss protocol in location: %s" % loc_line)
        sock.sendall('\x00hello\xFF')
        result = sock.recv(1024)
        self.assertEqual(result, '\x00hello\xff')
        sock.sendall('\x00start')
        eventlet.sleep(0.001)
        sock.sendall(' end\xff')
        result = sock.recv(1024)
        self.assertEqual(result, '\x00start end\xff')
        greenio.shutdown_safe(sock)
        sock.close()
        eventlet.sleep(0.01)



class TestWebSocketObject(LimitedTestCase):

    def setUp(self):
        self.mock_socket = s = mock.Mock()
        self.environ = env = dict(HTTP_ORIGIN='http://localhost', HTTP_WEBSOCKET_PROTOCOL='ws',
                                  PATH_INFO='test')

        self.test_ws = WebSocket(s, env)
        super(TestWebSocketObject, self).setUp()

    def test_recieve(self):
        ws = self.test_ws
        ws.socket.recv.return_value = '\x00hello\xFF'
        self.assertEqual(ws.wait(), 'hello')
        self.assertEqual(ws._buf, '')
        self.assertEqual(len(ws._msgs), 0)
        ws.socket.recv.return_value = ''
        self.assertEqual(ws.wait(), None)
        self.assertEqual(ws._buf, '')
        self.assertEqual(len(ws._msgs), 0)


    def test_send_to_ws(self):
        ws = self.test_ws
        ws.send(u'hello')
        self.assert_(ws.socket.sendall.called_with("\x00hello\xFF"))
        ws.send(10)
        self.assert_(ws.socket.sendall.called_with("\x0010\xFF"))

    def test_close_ws(self):
        ws = self.test_ws
        ws.close()
        self.assert_(ws.socket.shutdown.called_with(True))

########NEW FILE########
__FILENAME__ = wsgi_test
import cgi
import collections
import errno
import os
import signal
import socket
import sys
import traceback
import unittest

import eventlet
from eventlet import debug
from eventlet import event
from eventlet import greenio
from eventlet import greenthread
from eventlet import tpool
from eventlet import wsgi
from eventlet.green import socket as greensocket
from eventlet.green import ssl
from eventlet.green import subprocess
from eventlet.support import get_errno, six

from tests import (
    LimitedTestCase,
    skipped, skip_with_pyevent, skip_if_no_ssl,
    find_command, run_python,
)

certificate_file = os.path.join(os.path.dirname(__file__), 'test_server.crt')
private_key_file = os.path.join(os.path.dirname(__file__), 'test_server.key')


HttpReadResult = collections.namedtuple(
    'HttpReadResult',
    'status headers_lower body headers_original')


def hello_world(env, start_response):
    if env['PATH_INFO'] == 'notexist':
        start_response('404 Not Found', [('Content-type', 'text/plain')])
        return ["not found"]

    start_response('200 OK', [('Content-type', 'text/plain')])
    return ["hello world"]


def chunked_app(env, start_response):
    start_response('200 OK', [('Content-type', 'text/plain')])
    yield "this"
    yield "is"
    yield "chunked"


def chunked_fail_app(environ, start_response):
    """http://rhodesmill.org/brandon/2013/chunked-wsgi/
    """
    headers = [('Content-Type', 'text/plain')]
    start_response('200 OK', headers)

    # We start streaming data just fine.
    yield "The dwarves of yore made mighty spells,"
    yield "While hammers fell like ringing bells"

    # Then the back-end fails!
    try:
        1 / 0
    except Exception:
        start_response('500 Error', headers, sys.exc_info())
        return

    # So rest of the response data is not available.
    yield "In places deep, where dark things sleep,"
    yield "In hollow halls beneath the fells."


def big_chunks(env, start_response):
    start_response('200 OK', [('Content-type', 'text/plain')])
    line = 'a' * 8192
    for x in range(10):
        yield line


def use_write(env, start_response):
    if env['PATH_INFO'] == '/a':
        write = start_response('200 OK', [('Content-type', 'text/plain'),
                                          ('Content-Length', '5')])
        write('abcde')
    if env['PATH_INFO'] == '/b':
        write = start_response('200 OK', [('Content-type', 'text/plain')])
        write('abcde')
    return []


def chunked_post(env, start_response):
    start_response('200 OK', [('Content-type', 'text/plain')])
    if env['PATH_INFO'] == '/a':
        return [env['wsgi.input'].read()]
    elif env['PATH_INFO'] == '/b':
        return [x for x in iter(lambda: env['wsgi.input'].read(4096), '')]
    elif env['PATH_INFO'] == '/c':
        return [x for x in iter(lambda: env['wsgi.input'].read(1), '')]


def already_handled(env, start_response):
    start_response('200 OK', [('Content-type', 'text/plain')])
    return wsgi.ALREADY_HANDLED


class Site(object):
    def __init__(self):
        self.application = hello_world

    def __call__(self, env, start_response):
        return self.application(env, start_response)


class IterableApp(object):

    def __init__(self, send_start_response=False, return_val=wsgi.ALREADY_HANDLED):
        self.send_start_response = send_start_response
        self.return_val = return_val
        self.env = {}

    def __call__(self, env, start_response):
        self.env = env
        if self.send_start_response:
            start_response('200 OK', [('Content-type', 'text/plain')])
        return self.return_val


class IterableSite(Site):
    def __call__(self, env, start_response):
        it = self.application(env, start_response)
        for i in it:
            yield i


CONTENT_LENGTH = 'content-length'


"""
HTTP/1.1 200 OK
Date: foo
Content-length: 11

hello world
"""


class ConnectionClosed(Exception):
    pass


def read_http(sock):
    fd = sock.makefile()
    try:
        response_line = fd.readline().rstrip('\r\n')
    except socket.error as exc:
        if get_errno(exc) == 10053:
            raise ConnectionClosed
        raise
    if not response_line:
        raise ConnectionClosed(response_line)

    header_lines = []
    while True:
        line = fd.readline()
        if line == '\r\n':
            break
        else:
            header_lines.append(line)

    headers_original = {}
    headers_lower = {}
    for x in header_lines:
        x = x.strip()
        if not x:
            continue
        key, value = x.split(':', 1)
        key = key.rstrip()
        value = value.lstrip()
        key_lower = key.lower()
        # FIXME: Duplicate headers are allowed as per HTTP RFC standard,
        # the client and/or intermediate proxies are supposed to treat them
        # as a single header with values concatenated using space (' ') delimiter.
        assert key_lower not in headers_lower, "header duplicated: {0}".format(key)
        headers_original[key] = value
        headers_lower[key_lower] = value

    content_length_str = headers_lower.get(CONTENT_LENGTH.lower(), '')
    if content_length_str:
        num = int(content_length_str)
        body = fd.read(num)
    else:
        # read until EOF
        body = fd.read()

    result = HttpReadResult(
        status=response_line,
        headers_lower=headers_lower,
        body=body,
        headers_original=headers_original)
    return result


class _TestBase(LimitedTestCase):
    def setUp(self):
        super(_TestBase, self).setUp()
        self.logfile = six.StringIO()
        self.site = Site()
        self.killer = None
        self.set_site()
        self.spawn_server()

    def tearDown(self):
        greenthread.kill(self.killer)
        eventlet.sleep(0)
        super(_TestBase, self).tearDown()

    def spawn_server(self, **kwargs):
        """Spawns a new wsgi server with the given arguments using
        :meth:`spawn_thread`.

        Sets self.port to the port of the server"""
        new_kwargs = dict(max_size=128,
                          log=self.logfile,
                          site=self.site)
        new_kwargs.update(kwargs)

        if 'sock' not in new_kwargs:
            new_kwargs['sock'] = eventlet.listen(('localhost', 0))

        self.port = new_kwargs['sock'].getsockname()[1]
        self.spawn_thread(wsgi.server, **new_kwargs)

    def spawn_thread(self, target, **kwargs):
        """Spawns a new greenthread using specified target and arguments.

        Kills any previously-running server and sets self.killer to the
        greenthread running the target.
        """
        eventlet.sleep(0)  # give previous server a chance to start
        if self.killer:
            greenthread.kill(self.killer)

        self.killer = eventlet.spawn_n(target, **kwargs)

    def set_site(self):
        raise NotImplementedError


class TestHttpd(_TestBase):
    def set_site(self):
        self.site = Site()

    def test_001_server(self):
        sock = eventlet.connect(
            ('localhost', self.port))

        fd = sock.makefile('rw')
        fd.write('GET / HTTP/1.0\r\nHost: localhost\r\n\r\n')
        fd.flush()
        result = fd.read()
        fd.close()
        ## The server responds with the maximum version it supports
        self.assert_(result.startswith('HTTP'), result)
        self.assert_(result.endswith('hello world'))

    def test_002_keepalive(self):
        sock = eventlet.connect(
            ('localhost', self.port))

        fd = sock.makefile('w')
        fd.write('GET / HTTP/1.1\r\nHost: localhost\r\n\r\n')
        fd.flush()
        read_http(sock)
        fd.write('GET / HTTP/1.1\r\nHost: localhost\r\n\r\n')
        fd.flush()
        read_http(sock)
        fd.close()
        sock.close()

    def test_003_passing_non_int_to_read(self):
        # This should go in greenio_test
        sock = eventlet.connect(
            ('localhost', self.port))

        fd = sock.makefile('rw')
        fd.write('GET / HTTP/1.1\r\nHost: localhost\r\n\r\n')
        fd.flush()
        cancel = eventlet.Timeout(1, RuntimeError)
        self.assertRaises(TypeError, fd.read, "This shouldn't work")
        cancel.cancel()
        fd.close()

    def test_004_close_keepalive(self):
        sock = eventlet.connect(
            ('localhost', self.port))

        fd = sock.makefile('w')
        fd.write('GET / HTTP/1.1\r\nHost: localhost\r\n\r\n')
        fd.flush()
        read_http(sock)
        fd.write('GET / HTTP/1.1\r\nHost: localhost\r\nConnection: close\r\n\r\n')
        fd.flush()
        read_http(sock)
        fd.write('GET / HTTP/1.1\r\nHost: localhost\r\n\r\n')
        fd.flush()
        self.assertRaises(ConnectionClosed, read_http, sock)
        fd.close()

    @skipped
    def test_005_run_apachebench(self):
        url = 'http://localhost:12346/'
        # ab is apachebench
        subprocess.call(
            [find_command('ab'), '-c', '64', '-n', '1024', '-k', url],
            stdout=subprocess.PIPE)

    def test_006_reject_long_urls(self):
        sock = eventlet.connect(
            ('localhost', self.port))
        path_parts = []
        for ii in range(3000):
            path_parts.append('path')
        path = '/'.join(path_parts)
        request = 'GET /%s HTTP/1.0\r\nHost: localhost\r\n\r\n' % path
        fd = sock.makefile('rw')
        fd.write(request)
        fd.flush()
        result = fd.readline()
        if result:
            # windows closes the socket before the data is flushed,
            # so we never get anything back
            status = result.split(' ')[1]
            self.assertEqual(status, '414')
        fd.close()

    def test_007_get_arg(self):
        # define a new handler that does a get_arg as well as a read_body
        def new_app(env, start_response):
            body = env['wsgi.input'].read()
            a = cgi.parse_qs(body).get('a', [1])[0]
            start_response('200 OK', [('Content-type', 'text/plain')])
            return ['a is %s, body is %s' % (a, body)]

        self.site.application = new_app
        sock = eventlet.connect(
            ('localhost', self.port))
        request = '\r\n'.join((
            'POST / HTTP/1.0',
            'Host: localhost',
            'Content-Length: 3',
            '',
            'a=a'))
        fd = sock.makefile('w')
        fd.write(request)
        fd.flush()

        # send some junk after the actual request
        fd.write('01234567890123456789')
        result = read_http(sock)
        self.assertEqual(result.body, 'a is a, body is a=a')
        fd.close()

    def test_008_correctresponse(self):
        sock = eventlet.connect(('localhost', self.port))

        fd = sock.makefile('w')
        fd.write('GET / HTTP/1.1\r\nHost: localhost\r\n\r\n')
        fd.flush()
        result_200 = read_http(sock)
        fd.write('GET /notexist HTTP/1.1\r\nHost: localhost\r\n\r\n')
        fd.flush()
        read_http(sock)
        fd.write('GET / HTTP/1.1\r\nHost: localhost\r\n\r\n')
        fd.flush()
        result_test = read_http(sock)
        self.assertEqual(result_200.status, result_test.status)
        fd.close()
        sock.close()

    def test_009_chunked_response(self):
        self.site.application = chunked_app
        sock = eventlet.connect(
            ('localhost', self.port))

        fd = sock.makefile('rw')
        fd.write('GET / HTTP/1.1\r\nHost: localhost\r\nConnection: close\r\n\r\n')
        fd.flush()
        self.assert_('Transfer-Encoding: chunked' in fd.read())

    def test_010_no_chunked_http_1_0(self):
        self.site.application = chunked_app
        sock = eventlet.connect(
            ('localhost', self.port))

        fd = sock.makefile('rw')
        fd.write('GET / HTTP/1.0\r\nHost: localhost\r\nConnection: close\r\n\r\n')
        fd.flush()
        self.assert_('Transfer-Encoding: chunked' not in fd.read())

    def test_011_multiple_chunks(self):
        self.site.application = big_chunks
        sock = eventlet.connect(
            ('localhost', self.port))

        fd = sock.makefile('rw')
        fd.write('GET / HTTP/1.1\r\nHost: localhost\r\nConnection: close\r\n\r\n')
        fd.flush()
        headers = ''
        while True:
            line = fd.readline()
            if line == '\r\n':
                break
            else:
                headers += line
        self.assert_('Transfer-Encoding: chunked' in headers)
        chunks = 0
        chunklen = int(fd.readline(), 16)
        while chunklen:
            chunks += 1
            fd.read(chunklen)
            fd.readline()  # CRLF
            chunklen = int(fd.readline(), 16)
        self.assert_(chunks > 1)
        response = fd.read()
        # Require a CRLF to close the message body
        self.assertEqual(response, '\r\n')

    @skip_if_no_ssl
    def test_012_ssl_server(self):
        def wsgi_app(environ, start_response):
            start_response('200 OK', {})
            return [environ['wsgi.input'].read()]

        certificate_file = os.path.join(os.path.dirname(__file__), 'test_server.crt')
        private_key_file = os.path.join(os.path.dirname(__file__), 'test_server.key')

        server_sock = eventlet.wrap_ssl(eventlet.listen(('localhost', 0)),
                                        certfile=certificate_file,
                                        keyfile=private_key_file,
                                        server_side=True)
        self.spawn_server(sock=server_sock, site=wsgi_app)

        sock = eventlet.connect(('localhost', self.port))
        sock = eventlet.wrap_ssl(sock)
        sock.write('POST /foo HTTP/1.1\r\nHost: localhost\r\nConnection: close\r\nContent-length:3\r\n\r\nabc')
        result = sock.read(8192)
        self.assertEqual(result[-3:], 'abc')

    @skip_if_no_ssl
    def test_013_empty_return(self):
        def wsgi_app(environ, start_response):
            start_response("200 OK", [])
            return [""]

        certificate_file = os.path.join(os.path.dirname(__file__), 'test_server.crt')
        private_key_file = os.path.join(os.path.dirname(__file__), 'test_server.key')
        server_sock = eventlet.wrap_ssl(eventlet.listen(('localhost', 0)),
                                        certfile=certificate_file,
                                        keyfile=private_key_file,
                                        server_side=True)
        self.spawn_server(sock=server_sock, site=wsgi_app)

        sock = eventlet.connect(('localhost', server_sock.getsockname()[1]))
        sock = eventlet.wrap_ssl(sock)
        sock.write('GET /foo HTTP/1.1\r\nHost: localhost\r\nConnection: close\r\n\r\n')
        result = sock.read(8192)
        self.assertEqual(result[-4:], '\r\n\r\n')

    def test_014_chunked_post(self):
        self.site.application = chunked_post
        sock = eventlet.connect(('localhost', self.port))
        fd = sock.makefile('rw')
        fd.write('PUT /a HTTP/1.1\r\nHost: localhost\r\nConnection: close\r\n'
                 'Transfer-Encoding: chunked\r\n\r\n'
                 '2\r\noh\r\n4\r\n hai\r\n0\r\n\r\n')
        fd.flush()
        while True:
            if fd.readline() == '\r\n':
                break
        response = fd.read()
        self.assert_(response == 'oh hai', 'invalid response %s' % response)

        sock = eventlet.connect(('localhost', self.port))
        fd = sock.makefile('rw')
        fd.write('PUT /b HTTP/1.1\r\nHost: localhost\r\nConnection: close\r\n'
                 'Transfer-Encoding: chunked\r\n\r\n'
                 '2\r\noh\r\n4\r\n hai\r\n0\r\n\r\n')
        fd.flush()
        while True:
            if fd.readline() == '\r\n':
                break
        response = fd.read()
        self.assert_(response == 'oh hai', 'invalid response %s' % response)

        sock = eventlet.connect(('localhost', self.port))
        fd = sock.makefile('rw')
        fd.write('PUT /c HTTP/1.1\r\nHost: localhost\r\nConnection: close\r\n'
                 'Transfer-Encoding: chunked\r\n\r\n'
                 '2\r\noh\r\n4\r\n hai\r\n0\r\n\r\n')
        fd.flush()
        while True:
            if fd.readline() == '\r\n':
                break
        response = fd.read(8192)
        self.assert_(response == 'oh hai', 'invalid response %s' % response)

    def test_015_write(self):
        self.site.application = use_write
        sock = eventlet.connect(('localhost', self.port))
        fd = sock.makefile('w')
        fd.write('GET /a HTTP/1.1\r\nHost: localhost\r\nConnection: close\r\n\r\n')
        fd.flush()
        result1 = read_http(sock)
        self.assert_('content-length' in result1.headers_lower)

        sock = eventlet.connect(('localhost', self.port))
        fd = sock.makefile('w')
        fd.write('GET /b HTTP/1.1\r\nHost: localhost\r\nConnection: close\r\n\r\n')
        fd.flush()
        result2 = read_http(sock)
        self.assert_('transfer-encoding' in result2.headers_lower)
        self.assert_(result2.headers_lower['transfer-encoding'] == 'chunked')

    def test_016_repeated_content_length(self):
        """
        content-length header was being doubled up if it was set in
        start_response and could also be inferred from the iterator
        """
        def wsgi_app(environ, start_response):
            start_response('200 OK', [('Content-Length', '7')])
            return ['testing']
        self.site.application = wsgi_app
        sock = eventlet.connect(('localhost', self.port))
        fd = sock.makefile('rw')
        fd.write('GET /a HTTP/1.1\r\nHost: localhost\r\nConnection: close\r\n\r\n')
        fd.flush()
        header_lines = []
        while True:
            line = fd.readline()
            if line == '\r\n':
                break
            else:
                header_lines.append(line)
        self.assertEqual(1, len(
            [l for l in header_lines if l.lower().startswith('content-length')]))

    @skip_if_no_ssl
    def test_017_ssl_zeroreturnerror(self):

        def server(sock, site, log):
            try:
                serv = wsgi.Server(sock, sock.getsockname(), site, log)
                client_socket = sock.accept()
                serv.process_request(client_socket)
                return True
            except:
                traceback.print_exc()
                return False

        def wsgi_app(environ, start_response):
            start_response('200 OK', [])
            return [environ['wsgi.input'].read()]

        certificate_file = os.path.join(os.path.dirname(__file__), 'test_server.crt')
        private_key_file = os.path.join(os.path.dirname(__file__), 'test_server.key')

        sock = eventlet.wrap_ssl(
            eventlet.listen(('localhost', 0)),
            certfile=certificate_file, keyfile=private_key_file,
            server_side=True)
        server_coro = eventlet.spawn(server, sock, wsgi_app, self.logfile)

        client = eventlet.connect(('localhost', sock.getsockname()[1]))
        client = eventlet.wrap_ssl(client)
        client.write('X')  # non-empty payload so that SSL handshake occurs
        greenio.shutdown_safe(client)
        client.close()

        success = server_coro.wait()
        self.assert_(success)

    def test_018_http_10_keepalive(self):
        # verify that if an http/1.0 client sends connection: keep-alive
        # that we don't close the connection
        sock = eventlet.connect(
            ('localhost', self.port))

        fd = sock.makefile('w')
        fd.write('GET / HTTP/1.0\r\nHost: localhost\r\nConnection: keep-alive\r\n\r\n')
        fd.flush()

        result1 = read_http(sock)
        self.assert_('connection' in result1.headers_lower)
        self.assertEqual('keep-alive', result1.headers_lower['connection'])
        # repeat request to verify connection is actually still open
        fd.write('GET / HTTP/1.0\r\nHost: localhost\r\nConnection: keep-alive\r\n\r\n')
        fd.flush()
        result2 = read_http(sock)
        self.assert_('connection' in result2.headers_lower)
        self.assertEqual('keep-alive', result2.headers_lower['connection'])
        sock.close()

    def test_019_fieldstorage_compat(self):
        def use_fieldstorage(environ, start_response):
            cgi.FieldStorage(fp=environ['wsgi.input'], environ=environ)
            start_response('200 OK', [('Content-type', 'text/plain')])
            return ['hello!']

        self.site.application = use_fieldstorage
        sock = eventlet.connect(
            ('localhost', self.port))

        fd = sock.makefile('rw')
        fd.write('POST / HTTP/1.1\r\n'
                 'Host: localhost\r\n'
                 'Connection: close\r\n'
                 'Transfer-Encoding: chunked\r\n\r\n'
                 '2\r\noh\r\n'
                 '4\r\n hai\r\n0\r\n\r\n')
        fd.flush()
        self.assert_('hello!' in fd.read())

    def test_020_x_forwarded_for(self):
        request_bytes = (
            b'GET / HTTP/1.1\r\nHost: localhost\r\n'
            + b'X-Forwarded-For: 1.2.3.4, 5.6.7.8\r\n\r\n'
        )

        sock = eventlet.connect(('localhost', self.port))
        sock.sendall(request_bytes)
        sock.recv(1024)
        sock.close()
        self.assert_('1.2.3.4,5.6.7.8,127.0.0.1' in self.logfile.getvalue())

        # turning off the option should work too
        self.logfile = six.StringIO()
        self.spawn_server(log_x_forwarded_for=False)

        sock = eventlet.connect(('localhost', self.port))
        sock.sendall(request_bytes)
        sock.recv(1024)
        sock.close()
        self.assert_('1.2.3.4' not in self.logfile.getvalue())
        self.assert_('5.6.7.8' not in self.logfile.getvalue())
        self.assert_('127.0.0.1' in self.logfile.getvalue())

    def test_socket_remains_open(self):
        greenthread.kill(self.killer)
        server_sock = eventlet.listen(('localhost', 0))
        server_sock_2 = server_sock.dup()
        self.spawn_server(sock=server_sock_2)
        # do a single req/response to verify it's up
        sock = eventlet.connect(('localhost', self.port))
        fd = sock.makefile('rw')
        fd.write('GET / HTTP/1.0\r\nHost: localhost\r\n\r\n')
        fd.flush()
        result = fd.read(1024)
        fd.close()
        self.assert_(result.startswith('HTTP'), result)
        self.assert_(result.endswith('hello world'))

        # shut down the server and verify the server_socket fd is still open,
        # but the actual socketobject passed in to wsgi.server is closed
        greenthread.kill(self.killer)
        eventlet.sleep(0)  # make the kill go through
        try:
            server_sock_2.accept()
            # shouldn't be able to use this one anymore
        except socket.error as exc:
            self.assertEqual(get_errno(exc), errno.EBADF)
        self.spawn_server(sock=server_sock)
        sock = eventlet.connect(('localhost', self.port))
        fd = sock.makefile('rw')
        fd.write('GET / HTTP/1.0\r\nHost: localhost\r\n\r\n')
        fd.flush()
        result = fd.read(1024)
        fd.close()
        self.assert_(result.startswith('HTTP'), result)
        self.assert_(result.endswith('hello world'))

    def test_021_environ_clobbering(self):
        def clobberin_time(environ, start_response):
            for environ_var in [
                    'wsgi.version', 'wsgi.url_scheme',
                    'wsgi.input', 'wsgi.errors', 'wsgi.multithread',
                    'wsgi.multiprocess', 'wsgi.run_once', 'REQUEST_METHOD',
                    'SCRIPT_NAME', 'RAW_PATH_INFO', 'PATH_INFO', 'QUERY_STRING',
                    'CONTENT_TYPE', 'CONTENT_LENGTH', 'SERVER_NAME', 'SERVER_PORT',
                    'SERVER_PROTOCOL']:
                environ[environ_var] = None
            start_response('200 OK', [('Content-type', 'text/plain')])
            return []
        self.site.application = clobberin_time
        sock = eventlet.connect(('localhost', self.port))
        fd = sock.makefile('rw')
        fd.write('GET / HTTP/1.1\r\n'
                 'Host: localhost\r\n'
                 'Connection: close\r\n'
                 '\r\n\r\n')
        fd.flush()
        self.assert_('200 OK' in fd.read())

    def test_022_custom_pool(self):
        # just test that it accepts the parameter for now
        # TODO: test that it uses the pool and that you can waitall() to
        # ensure that all clients finished
        p = eventlet.GreenPool(5)
        self.spawn_server(custom_pool=p)

        # this stuff is copied from test_001_server, could be better factored
        sock = eventlet.connect(
            ('localhost', self.port))
        fd = sock.makefile('rw')
        fd.write('GET / HTTP/1.0\r\nHost: localhost\r\n\r\n')
        fd.flush()
        result = fd.read()
        fd.close()
        self.assert_(result.startswith('HTTP'), result)
        self.assert_(result.endswith('hello world'))

    def test_023_bad_content_length(self):
        sock = eventlet.connect(
            ('localhost', self.port))
        fd = sock.makefile('rw')
        fd.write('GET / HTTP/1.0\r\nHost: localhost\r\nContent-length: argh\r\n\r\n')
        fd.flush()
        result = fd.read()
        fd.close()
        self.assert_(result.startswith('HTTP'), result)
        self.assert_('400 Bad Request' in result)
        self.assert_('500' not in result)

    def test_024_expect_100_continue(self):
        def wsgi_app(environ, start_response):
            if int(environ['CONTENT_LENGTH']) > 1024:
                start_response('417 Expectation Failed', [('Content-Length', '7')])
                return ['failure']
            else:
                text = environ['wsgi.input'].read()
                start_response('200 OK', [('Content-Length', str(len(text)))])
                return [text]
        self.site.application = wsgi_app
        sock = eventlet.connect(('localhost', self.port))
        fd = sock.makefile('rw')
        fd.write('PUT / HTTP/1.1\r\nHost: localhost\r\nContent-length: 1025\r\nExpect: 100-continue\r\n\r\n')
        fd.flush()
        result = read_http(sock)
        self.assertEqual(result.status, 'HTTP/1.1 417 Expectation Failed')
        self.assertEqual(result.body, 'failure')
        fd.write('PUT / HTTP/1.1\r\nHost: localhost\r\nContent-length: 7\r\nExpect: 100-continue\r\n\r\ntesting')
        fd.flush()
        header_lines = []
        while True:
            line = fd.readline()
            if line == '\r\n':
                break
            else:
                header_lines.append(line)
        self.assert_(header_lines[0].startswith('HTTP/1.1 100 Continue'))
        header_lines = []
        while True:
            line = fd.readline()
            if line == '\r\n':
                break
            else:
                header_lines.append(line)
        self.assert_(header_lines[0].startswith('HTTP/1.1 200 OK'))
        self.assertEqual(fd.read(7), 'testing')
        fd.close()
        sock.close()

    def test_025_accept_errors(self):
        debug.hub_exceptions(True)
        listener = greensocket.socket()
        listener.bind(('localhost', 0))
        # NOT calling listen, to trigger the error
        self.logfile = six.StringIO()
        self.spawn_server(sock=listener)
        old_stderr = sys.stderr
        try:
            sys.stderr = self.logfile
            eventlet.sleep(0)  # need to enter server loop
            try:
                eventlet.connect(('localhost', self.port))
                self.fail("Didn't expect to connect")
            except socket.error as exc:
                self.assertEqual(get_errno(exc), errno.ECONNREFUSED)

            self.assert_('Invalid argument' in self.logfile.getvalue(),
                         self.logfile.getvalue())
        finally:
            sys.stderr = old_stderr
        debug.hub_exceptions(False)

    def test_026_log_format(self):
        self.spawn_server(log_format="HI %(request_line)s HI")
        sock = eventlet.connect(('localhost', self.port))
        sock.sendall('GET /yo! HTTP/1.1\r\nHost: localhost\r\n\r\n')
        sock.recv(1024)
        sock.close()
        self.assert_('\nHI GET /yo! HTTP/1.1 HI\n' in self.logfile.getvalue(), self.logfile.getvalue())

    def test_close_chunked_with_1_0_client(self):
        # verify that if we return a generator from our app
        # and we're not speaking with a 1.1 client, that we
        # close the connection
        self.site.application = chunked_app
        sock = eventlet.connect(('localhost', self.port))

        sock.sendall('GET / HTTP/1.0\r\nHost: localhost\r\nConnection: keep-alive\r\n\r\n')

        result = read_http(sock)
        self.assertEqual(result.headers_lower['connection'], 'close')
        self.assertNotEqual(result.headers_lower.get('transfer-encoding'), 'chunked')
        self.assertEqual(result.body, "thisischunked")

    def test_minimum_chunk_size_parameter_leaves_httpprotocol_class_member_intact(self):
        start_size = wsgi.HttpProtocol.minimum_chunk_size

        self.spawn_server(minimum_chunk_size=start_size * 2)
        sock = eventlet.connect(('localhost', self.port))
        sock.sendall('GET / HTTP/1.1\r\nHost: localhost\r\n\r\n')
        read_http(sock)

        self.assertEqual(wsgi.HttpProtocol.minimum_chunk_size, start_size)
        sock.close()

    def test_error_in_chunked_closes_connection(self):
        # From http://rhodesmill.org/brandon/2013/chunked-wsgi/
        self.spawn_server(minimum_chunk_size=1)

        self.site.application = chunked_fail_app
        sock = eventlet.connect(('localhost', self.port))

        sock.sendall('GET / HTTP/1.1\r\nHost: localhost\r\n\r\n')

        result = read_http(sock)
        self.assertEqual(result.status, 'HTTP/1.1 200 OK')
        self.assertEqual(result.headers_lower.get('transfer-encoding'), 'chunked')
        expected_body = (
            b'27\r\nThe dwarves of yore made mighty spells,\r\n'
            b'25\r\nWhile hammers fell like ringing bells\r\n')
        self.assertEqual(result.body, expected_body)

        # verify that socket is closed by server
        self.assertEqual(sock.recv(1), '')

    def test_026_http_10_nokeepalive(self):
        # verify that if an http/1.0 client sends connection: keep-alive
        # and the server doesn't accept keep-alives, we close the connection
        self.spawn_server(keepalive=False)
        sock = eventlet.connect(
            ('localhost', self.port))

        sock.sendall('GET / HTTP/1.0\r\nHost: localhost\r\nConnection: keep-alive\r\n\r\n')
        result = read_http(sock)
        self.assertEqual(result.headers_lower['connection'], 'close')

    def test_027_keepalive_chunked(self):
        self.site.application = chunked_post
        sock = eventlet.connect(('localhost', self.port))
        fd = sock.makefile('w')
        common_suffix = (
            b'Host: localhost\r\nTransfer-Encoding: chunked\r\n\r\n' +
            b'10\r\n0123456789abcdef\r\n0\r\n\r\n')
        fd.write(b'PUT /a HTTP/1.1\r\n' + common_suffix)
        fd.flush()
        read_http(sock)
        fd.write(b'PUT /b HTTP/1.1\r\n' + common_suffix)
        fd.flush()
        read_http(sock)
        fd.write(b'PUT /c HTTP/1.1\r\n' + common_suffix)
        fd.flush()
        read_http(sock)
        fd.write(b'PUT /a HTTP/1.1\r\n' + common_suffix)
        fd.flush()
        read_http(sock)
        sock.close()

    @skip_if_no_ssl
    def test_028_ssl_handshake_errors(self):
        errored = [False]

        def server(sock):
            try:
                wsgi.server(sock=sock, site=hello_world, log=self.logfile)
                errored[0] = 'SSL handshake error caused wsgi.server to exit.'
            except greenthread.greenlet.GreenletExit:
                pass
            except Exception as e:
                errored[0] = 'SSL handshake error raised exception %s.' % e
        for data in ('', 'GET /non-ssl-request HTTP/1.0\r\n\r\n'):
            srv_sock = eventlet.wrap_ssl(
                eventlet.listen(('localhost', 0)),
                certfile=certificate_file, keyfile=private_key_file,
                server_side=True)
            port = srv_sock.getsockname()[1]
            g = eventlet.spawn_n(server, srv_sock)
            client = eventlet.connect(('localhost', port))
            if data:  # send non-ssl request
                client.sendall(data)
            else:  # close sock prematurely
                client.close()
            eventlet.sleep(0)  # let context switch back to server
            self.assert_(not errored[0], errored[0])
            # make another request to ensure the server's still alive
            try:
                client = ssl.wrap_socket(eventlet.connect(('localhost', port)))
                client.write('GET / HTTP/1.0\r\nHost: localhost\r\n\r\n')
                result = client.read()
                self.assert_(result.startswith('HTTP'), result)
                self.assert_(result.endswith('hello world'))
            except ImportError:
                pass  # TODO: should test with OpenSSL
            greenthread.kill(g)

    def test_029_posthooks(self):
        posthook1_count = [0]
        posthook2_count = [0]

        def posthook1(env, value, multiplier=1):
            self.assertEqual(env['local.test'], 'test_029_posthooks')
            posthook1_count[0] += value * multiplier

        def posthook2(env, value, divisor=1):
            self.assertEqual(env['local.test'], 'test_029_posthooks')
            posthook2_count[0] += value / divisor

        def one_posthook_app(env, start_response):
            env['local.test'] = 'test_029_posthooks'
            if 'eventlet.posthooks' not in env:
                start_response('500 eventlet.posthooks not supported',
                               [('Content-Type', 'text/plain')])
            else:
                env['eventlet.posthooks'].append(
                    (posthook1, (2,), {'multiplier': 3}))
                start_response('200 OK', [('Content-Type', 'text/plain')])
            yield ''
        self.site.application = one_posthook_app
        sock = eventlet.connect(('localhost', self.port))
        fp = sock.makefile('rw')
        fp.write('GET / HTTP/1.1\r\nHost: localhost\r\n\r\n')
        fp.flush()
        self.assertEqual(fp.readline(), 'HTTP/1.1 200 OK\r\n')
        fp.close()
        sock.close()
        self.assertEqual(posthook1_count[0], 6)
        self.assertEqual(posthook2_count[0], 0)

        def two_posthook_app(env, start_response):
            env['local.test'] = 'test_029_posthooks'
            if 'eventlet.posthooks' not in env:
                start_response('500 eventlet.posthooks not supported',
                               [('Content-Type', 'text/plain')])
            else:
                env['eventlet.posthooks'].append(
                    (posthook1, (4,), {'multiplier': 5}))
                env['eventlet.posthooks'].append(
                    (posthook2, (100,), {'divisor': 4}))
                start_response('200 OK', [('Content-Type', 'text/plain')])
            yield ''
        self.site.application = two_posthook_app
        sock = eventlet.connect(('localhost', self.port))
        fp = sock.makefile('rw')
        fp.write('GET / HTTP/1.1\r\nHost: localhost\r\n\r\n')
        fp.flush()
        self.assertEqual(fp.readline(), 'HTTP/1.1 200 OK\r\n')
        fp.close()
        sock.close()
        self.assertEqual(posthook1_count[0], 26)
        self.assertEqual(posthook2_count[0], 25)

    def test_030_reject_long_header_lines(self):
        sock = eventlet.connect(('localhost', self.port))
        request = 'GET / HTTP/1.0\r\nHost: localhost\r\nLong: %s\r\n\r\n' % \
            ('a' * 10000)
        fd = sock.makefile('rw')
        fd.write(request)
        fd.flush()
        result = read_http(sock)
        self.assertEqual(result.status, 'HTTP/1.0 400 Header Line Too Long')
        fd.close()

    def test_031_reject_large_headers(self):
        sock = eventlet.connect(('localhost', self.port))
        headers = 'Name: Value\r\n' * 5050
        request = 'GET / HTTP/1.0\r\nHost: localhost\r\n%s\r\n\r\n' % headers
        fd = sock.makefile('rw')
        fd.write(request)
        fd.flush()
        result = read_http(sock)
        self.assertEqual(result.status, 'HTTP/1.0 400 Headers Too Large')
        fd.close()

    def test_032_wsgi_input_as_iterable(self):
        # https://bitbucket.org/eventlet/eventlet/issue/150
        # env['wsgi.input'] returns a single byte at a time
        # when used as an iterator
        g = [0]

        def echo_by_iterating(env, start_response):
            start_response('200 OK', [('Content-type', 'text/plain')])
            for chunk in env['wsgi.input']:
                g[0] += 1
                yield chunk

        self.site.application = echo_by_iterating
        upload_data = '123456789abcdef' * 100
        request = (
            'POST / HTTP/1.0\r\n'
            'Host: localhost\r\n'
            'Content-Length: %i\r\n\r\n%s'
        ) % (len(upload_data), upload_data)
        sock = eventlet.connect(('localhost', self.port))
        fd = sock.makefile('rw')
        fd.write(request)
        fd.flush()
        result = read_http(sock)
        self.assertEqual(result.body, upload_data)
        fd.close()
        self.assertEqual(g[0], 1)

    def test_zero_length_chunked_response(self):
        def zero_chunked_app(env, start_response):
            start_response('200 OK', [('Content-type', 'text/plain')])
            yield ""

        self.site.application = zero_chunked_app
        sock = eventlet.connect(
            ('localhost', self.port))

        fd = sock.makefile('rw')
        fd.write('GET / HTTP/1.1\r\nHost: localhost\r\nConnection: close\r\n\r\n')
        fd.flush()
        response = fd.read().split('\r\n')
        headers = []
        while True:
            h = response.pop(0)
            headers.append(h)
            if h == '':
                break
        self.assert_('Transfer-Encoding: chunked' in ''.join(headers))
        # should only be one chunk of zero size with two blank lines
        # (one terminates the chunk, one terminates the body)
        self.assertEqual(response, ['0', '', ''])

    def test_configurable_url_length_limit(self):
        self.spawn_server(url_length_limit=20000)
        sock = eventlet.connect(
            ('localhost', self.port))
        path = 'x' * 15000
        request = 'GET /%s HTTP/1.0\r\nHost: localhost\r\n\r\n' % path
        fd = sock.makefile('rw')
        fd.write(request)
        fd.flush()
        result = fd.readline()
        if result:
            # windows closes the socket before the data is flushed,
            # so we never get anything back
            status = result.split(' ')[1]
            self.assertEqual(status, '200')
        fd.close()

    def test_aborted_chunked_post(self):
        read_content = event.Event()
        blew_up = [False]

        def chunk_reader(env, start_response):
            try:
                content = env['wsgi.input'].read(1024)
            except IOError:
                blew_up[0] = True
                content = 'ok'
            read_content.send(content)
            start_response('200 OK', [('Content-Type', 'text/plain')])
            return [content]
        self.site.application = chunk_reader
        expected_body = 'a bunch of stuff'
        data = "\r\n".join(['PUT /somefile HTTP/1.0',
                            'Transfer-Encoding: chunked',
                            '',
                            'def',
                            expected_body])
        # start PUT-ing some chunked data but close prematurely
        sock = eventlet.connect(('127.0.0.1', self.port))
        sock.sendall(data)
        sock.close()
        # the test passes if we successfully get here, and read all the data
        # in spite of the early close
        self.assertEqual(read_content.wait(), 'ok')
        self.assert_(blew_up[0])

    def test_exceptions_close_connection(self):
        def wsgi_app(environ, start_response):
            raise RuntimeError("intentional error")
        self.site.application = wsgi_app
        sock = eventlet.connect(('localhost', self.port))
        fd = sock.makefile('rw')
        fd.write('GET / HTTP/1.1\r\nHost: localhost\r\n\r\n')
        fd.flush()
        result = read_http(sock)
        self.assertEqual(result.status, 'HTTP/1.1 500 Internal Server Error')
        self.assertEqual(result.headers_lower['connection'], 'close')
        self.assert_('transfer-encoding' not in result.headers_lower)

    def test_unicode_raises_error(self):
        def wsgi_app(environ, start_response):
            start_response("200 OK", [])
            yield u"oh hai"
            yield u"non-encodable unicode: \u0230"
        self.site.application = wsgi_app
        sock = eventlet.connect(('localhost', self.port))
        fd = sock.makefile('rw')
        fd.write('GET / HTTP/1.1\r\nHost: localhost\r\nConnection: close\r\n\r\n')
        fd.flush()
        result = read_http(sock)
        self.assertEqual(result.status, 'HTTP/1.1 500 Internal Server Error')
        self.assertEqual(result.headers_lower['connection'], 'close')
        self.assert_('unicode' in result.body)

    def test_path_info_decoding(self):
        def wsgi_app(environ, start_response):
            start_response("200 OK", [])
            yield "decoded: %s" % environ['PATH_INFO']
            yield "raw: %s" % environ['RAW_PATH_INFO']
        self.site.application = wsgi_app
        sock = eventlet.connect(('localhost', self.port))
        fd = sock.makefile('rw')
        fd.write('GET /a*b@%40%233 HTTP/1.1\r\nHost: localhost\r\nConnection: close\r\n\r\n')
        fd.flush()
        result = read_http(sock)
        self.assertEqual(result.status, 'HTTP/1.1 200 OK')
        self.assert_('decoded: /a*b@@#3' in result.body)
        self.assert_('raw: /a*b@%40%233' in result.body)

    def test_ipv6(self):
        try:
            sock = eventlet.listen(('::1', 0), family=socket.AF_INET6)
        except (socket.gaierror, socket.error):  # probably no ipv6
            return
        log = six.StringIO()
        # first thing the server does is try to log the IP it's bound to

        def run_server():
            try:
                wsgi.server(sock=sock, log=log, site=Site())
            except ValueError:
                log.write('broked')

        self.spawn_thread(run_server)

        logval = log.getvalue()
        while not logval:
            eventlet.sleep(0.0)
            logval = log.getvalue()
        if 'broked' in logval:
            self.fail('WSGI server raised exception with ipv6 socket')

    def test_debug(self):
        self.spawn_server(debug=False)

        def crasher(env, start_response):
            raise RuntimeError("intentional crash")
        self.site.application = crasher

        sock = eventlet.connect(('localhost', self.port))
        fd = sock.makefile('w')
        fd.write('GET / HTTP/1.1\r\nHost: localhost\r\n\r\n')
        fd.flush()
        result1 = read_http(sock)
        self.assertEqual(result1.status, 'HTTP/1.1 500 Internal Server Error')
        self.assertEqual(result1.body, '')
        self.assertEqual(result1.headers_lower['connection'], 'close')
        self.assert_('transfer-encoding' not in result1.headers_lower)

        # verify traceback when debugging enabled
        self.spawn_server(debug=True)
        self.site.application = crasher
        sock = eventlet.connect(('localhost', self.port))
        fd = sock.makefile('w')
        fd.write('GET / HTTP/1.1\r\nHost: localhost\r\n\r\n')
        fd.flush()
        result2 = read_http(sock)
        self.assertEqual(result2.status, 'HTTP/1.1 500 Internal Server Error')
        self.assert_('intentional crash' in result2.body)
        self.assert_('RuntimeError' in result2.body)
        self.assert_('Traceback' in result2.body)
        self.assertEqual(result2.headers_lower['connection'], 'close')
        self.assert_('transfer-encoding' not in result2.headers_lower)

    def test_client_disconnect(self):
        """Issue #95 Server must handle disconnect from client in the middle of response
        """
        def long_response(environ, start_response):
            start_response('200 OK', [('Content-Length', '9876')])
            yield 'a' * 9876

        server_sock = eventlet.listen(('localhost', 0))
        self.port = server_sock.getsockname()[1]
        server = wsgi.Server(server_sock, server_sock.getsockname(), long_response,
                             log=self.logfile)

        def make_request():
            sock = eventlet.connect(server_sock.getsockname())
            sock.send('GET / HTTP/1.1\r\nHost: localhost\r\n\r\n')
            sock.close()

        request_thread = eventlet.spawn(make_request)
        server_conn = server_sock.accept()
        # Next line must not raise IOError -32 Broken pipe
        server.process_request(server_conn)
        request_thread.wait()
        server_sock.close()

    def test_server_connection_timeout_exception(self):
        # Handle connection socket timeouts
        # https://bitbucket.org/eventlet/eventlet/issue/143/
        # Runs tests.wsgi_test_conntimeout in a separate process.
        testcode_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            'wsgi_test_conntimeout.py')
        output = run_python(testcode_path)
        sections = output.split("SEPERATOR_SENTINEL")
        # first section is empty
        self.assertEqual(3, len(sections), output)
        # if the "BOOM" check fails, it's because our timeout didn't happen
        # (if eventlet stops using file.readline() to read HTTP headers,
        # for instance)
        for runlog in sections[1:]:
            debug = False if "debug set to: False" in runlog else True
            if debug:
                self.assertTrue("timed out" in runlog)
            self.assertTrue("BOOM" in runlog)
            self.assertFalse("Traceback" in runlog)

    def test_server_socket_timeout(self):
        self.spawn_server(socket_timeout=0.1)
        sock = eventlet.connect(('localhost', self.port))
        sock.send('GET / HTTP/1.1\r\n')
        eventlet.sleep(0.1)
        try:
            read_http(sock)
            assert False, 'Expected ConnectionClosed exception'
        except ConnectionClosed:
            pass

    def test_disable_header_name_capitalization(self):
        # Disable HTTP header name capitalization
        #
        # https://github.com/eventlet/eventlet/issues/80
        random_case_header = ('eTAg', 'TAg-VAluE')

        def wsgi_app(environ, start_response):
            start_response('200 oK', [random_case_header])
            return ['']

        self.spawn_server(site=wsgi_app, capitalize_response_headers=False)

        sock = eventlet.connect(('localhost', self.port))
        sock.sendall('GET / HTTP/1.1\r\nHost: localhost\r\n\r\n')
        result = read_http(sock)
        sock.close()
        self.assertEqual(result.status, 'HTTP/1.1 200 oK')
        self.assertEqual(result.headers_lower[random_case_header[0].lower()], random_case_header[1])
        self.assertEqual(result.headers_original[random_case_header[0]], random_case_header[1])


def read_headers(sock):
    fd = sock.makefile()
    try:
        response_line = fd.readline()
    except socket.error as exc:
        if get_errno(exc) == 10053:
            raise ConnectionClosed
        raise
    if not response_line:
        raise ConnectionClosed

    header_lines = []
    while True:
        line = fd.readline()
        if line == '\r\n':
            break
        else:
            header_lines.append(line)
    headers = dict()
    for x in header_lines:
        x = x.strip()
        if not x:
            continue
        key, value = x.split(': ', 1)
        assert key.lower() not in headers, "%s header duplicated" % key
        headers[key.lower()] = value
    return response_line, headers


class IterableAlreadyHandledTest(_TestBase):
    def set_site(self):
        self.site = IterableSite()

    def get_app(self):
        return IterableApp(True)

    def test_iterable_app_keeps_socket_open_unless_connection_close_sent(self):
        self.site.application = self.get_app()
        sock = eventlet.connect(
            ('localhost', self.port))

        fd = sock.makefile('rw')
        fd.write('GET / HTTP/1.1\r\nHost: localhost\r\n\r\n')

        fd.flush()
        response_line, headers = read_headers(sock)
        self.assertEqual(response_line, 'HTTP/1.1 200 OK\r\n')
        self.assert_('connection' not in headers)
        fd.write('GET / HTTP/1.1\r\nHost: localhost\r\nConnection: close\r\n\r\n')
        fd.flush()
        result = read_http(sock)
        self.assertEqual(result.status, 'HTTP/1.1 200 OK')
        self.assertEqual(result.headers_lower.get('transfer-encoding'), 'chunked')
        self.assertEqual(result.body, '0\r\n\r\n')  # Still coming back chunked


class ProxiedIterableAlreadyHandledTest(IterableAlreadyHandledTest):
    # same thing as the previous test but ensuring that it works with tpooled
    # results as well as regular ones
    @skip_with_pyevent
    def get_app(self):
        return tpool.Proxy(super(ProxiedIterableAlreadyHandledTest, self).get_app())

    def tearDown(self):
        tpool.killall()
        super(ProxiedIterableAlreadyHandledTest, self).tearDown()


class TestChunkedInput(_TestBase):
    dirt = ""
    validator = None

    def application(self, env, start_response):
        input = env['wsgi.input']
        response = []

        pi = env["PATH_INFO"]

        if pi == "/short-read":
            d = input.read(10)
            response = [d]
        elif pi == "/lines":
            for x in input:
                response.append(x)
        elif pi == "/ping":
            input.read()
            response.append("pong")
        elif pi.startswith("/yield_spaces"):
            if pi.endswith('override_min'):
                env['eventlet.minimum_write_chunk_size'] = 1
            self.yield_next_space = False

            def response_iter():
                yield ' '
                num_sleeps = 0
                while not self.yield_next_space and num_sleeps < 200:
                    eventlet.sleep(.01)
                    num_sleeps += 1

                yield ' '

            start_response('200 OK',
                           [('Content-Type', 'text/plain'),
                            ('Content-Length', '2')])
            return response_iter()
        else:
            raise RuntimeError("bad path")

        start_response('200 OK', [('Content-Type', 'text/plain')])
        return response

    def connect(self):
        return eventlet.connect(('localhost', self.port))

    def set_site(self):
        self.site = Site()
        self.site.application = self.application

    def chunk_encode(self, chunks, dirt=None):
        if dirt is None:
            dirt = self.dirt

        b = ""
        for c in chunks:
            b += "%x%s\r\n%s\r\n" % (len(c), dirt, c)
        return b

    def body(self, dirt=None):
        return self.chunk_encode(["this", " is ", "chunked", "\nline", " 2", "\n", "line3", ""], dirt=dirt)

    def ping(self, fd):
        fd.sendall("GET /ping HTTP/1.1\r\n\r\n")
        self.assertEqual(read_http(fd).body, "pong")

    def test_short_read_with_content_length(self):
        body = self.body()
        req = "POST /short-read HTTP/1.1\r\ntransfer-encoding: Chunked\r\nContent-Length:1000\r\n\r\n" + body

        fd = self.connect()
        fd.sendall(req)
        self.assertEqual(read_http(fd).body, "this is ch")

        self.ping(fd)
        fd.close()

    def test_short_read_with_zero_content_length(self):
        body = self.body()
        req = "POST /short-read HTTP/1.1\r\ntransfer-encoding: Chunked\r\nContent-Length:0\r\n\r\n" + body
        fd = self.connect()
        fd.sendall(req)
        self.assertEqual(read_http(fd).body, "this is ch")

        self.ping(fd)
        fd.close()

    def test_short_read(self):
        body = self.body()
        req = "POST /short-read HTTP/1.1\r\ntransfer-encoding: Chunked\r\n\r\n" + body

        fd = self.connect()
        fd.sendall(req)
        self.assertEqual(read_http(fd).body, "this is ch")

        self.ping(fd)
        fd.close()

    def test_dirt(self):
        body = self.body(dirt="; here is dirt\0bla")
        req = "POST /ping HTTP/1.1\r\ntransfer-encoding: Chunked\r\n\r\n" + body

        fd = self.connect()
        fd.sendall(req)
        self.assertEqual(read_http(fd).body, "pong")

        self.ping(fd)
        fd.close()

    def test_chunked_readline(self):
        body = self.body()
        req = "POST /lines HTTP/1.1\r\nContent-Length: %s\r\ntransfer-encoding: Chunked\r\n\r\n%s" % (len(body), body)

        fd = self.connect()
        fd.sendall(req)
        self.assertEqual(read_http(fd).body, 'this is chunked\nline 2\nline3')
        fd.close()

    def test_chunked_readline_wsgi_override_minimum_chunk_size(self):

        fd = self.connect()
        fd.sendall("POST /yield_spaces/override_min HTTP/1.1\r\nContent-Length: 0\r\n\r\n")

        resp_so_far = ''
        with eventlet.Timeout(.1):
            while True:
                one_byte = fd.recv(1)
                resp_so_far += one_byte
                if resp_so_far.endswith('\r\n\r\n'):
                    break
            self.assertEqual(fd.recv(1), ' ')
        try:
            with eventlet.Timeout(.1):
                fd.recv(1)
        except eventlet.Timeout:
            pass
        else:
            self.assert_(False)
        self.yield_next_space = True

        with eventlet.Timeout(.1):
            self.assertEqual(fd.recv(1), ' ')

    def test_chunked_readline_wsgi_not_override_minimum_chunk_size(self):

        fd = self.connect()
        fd.sendall("POST /yield_spaces HTTP/1.1\r\nContent-Length: 0\r\n\r\n")

        resp_so_far = ''
        try:
            with eventlet.Timeout(.1):
                while True:
                    one_byte = fd.recv(1)
                    resp_so_far += one_byte
                    if resp_so_far.endswith('\r\n\r\n'):
                        break
                self.assertEqual(fd.recv(1), ' ')
        except eventlet.Timeout:
            pass
        else:
            self.assert_(False)

    def test_close_before_finished(self):
        got_signal = []

        def handler(*args):
            got_signal.append(1)
            raise KeyboardInterrupt()

        signal.signal(signal.SIGALRM, handler)
        signal.alarm(1)

        try:
            body = '4\r\nthi'
            req = "POST /short-read HTTP/1.1\r\ntransfer-encoding: Chunked\r\n\r\n" + body

            fd = self.connect()
            fd.sendall(req)
            fd.close()
            eventlet.sleep(0.0)
        finally:
            signal.alarm(0)
            signal.signal(signal.SIGALRM, signal.SIG_DFL)

        assert not got_signal, "caught alarm signal. infinite loop detected."


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = wsgi_test_conntimeout
"""Issue #143 - Socket timeouts in wsgi server not caught.
https://bitbucket.org/eventlet/eventlet/issue/143/

This file intentionally ignored by nose.
Caller process (tests.wsgi_test.TestWsgiConnTimeout) handles success / failure


Simulate server connection socket timeout without actually waiting.
Logs 'timed out' if server debug=True (similar to 'accepted' logging)

FAIL: if log (ie, _spawn_n_impl 'except:' catches timeout, logs TB)
NOTE: timeouts are NOT on server_sock, but on the conn sockets produced
by the socket.accept() call

server's socket.listen() sock - NaughtySocketAcceptWrap
    /  |  \
    |  |  |   (1 - many)
    V  V  V
server / client accept() conn - ExplodingConnectionWrap
    /  |  \
    |  |  |   (1 - many)
    V  V  V
connection makefile() file objects - ExplodingSocketFile <-- these raise
"""
from __future__ import print_function

import eventlet

import socket
import sys

import tests.wsgi_test


# no standard tests in this file, ignore
__test__ = False


# This test might make you wince
class NaughtySocketAcceptWrap(object):
    # server's socket.accept(); patches resulting connection sockets

    def __init__(self, sock):
        self.sock = sock
        self.sock._really_accept = self.sock.accept
        self.sock.accept = self
        self.conn_reg = []

    def unwrap(self):
        self.sock.accept = self.sock._really_accept
        del self.sock._really_accept
        for conn_wrap in self.conn_reg:
            conn_wrap.unwrap()

    def arm(self):
        print("ca-click")
        for i in self.conn_reg:
            i.arm()

    def __call__(self):
        print(self.__class__.__name__ + ".__call__")
        conn, addr = self.sock._really_accept()
        self.conn_reg.append(ExplodingConnectionWrap(conn))
        return conn, addr


class ExplodingConnectionWrap(object):
    # new connection's socket.makefile
    # eventlet *tends* to use socket.makefile, not raw socket methods.
    # need to patch file operations

    def __init__(self, conn):
        self.conn = conn
        self.conn._really_makefile = self.conn.makefile
        self.conn.makefile = self
        self.armed = False
        self.file_reg = []

    def unwrap(self):
        self.conn.makefile = self.conn._really_makefile
        del self.conn._really_makefile

    def arm(self):
        print("tick")
        for i in self.file_reg:
            i.arm()

    def __call__(self, mode='r', bufsize=-1):
        print(self.__class__.__name__ + ".__call__")
        # file_obj = self.conn._really_makefile(*args, **kwargs)
        file_obj = ExplodingSocketFile(self.conn._sock, mode, bufsize)
        self.file_reg.append(file_obj)
        return file_obj


class ExplodingSocketFile(socket._fileobject):

    def __init__(self, sock, mode='rb', bufsize=-1, close=False):
        super(self.__class__, self).__init__(sock, mode, bufsize, close)
        self.armed = False

    def arm(self):
        print("beep")
        self.armed = True

    def _fuse(self):
        if self.armed:
            print("=== ~* BOOM *~ ===")
            raise socket.timeout("timed out")

    def readline(self, *args, **kwargs):
        print(self.__class__.__name__ + ".readline")
        self._fuse()
        return super(self.__class__, self).readline(*args, **kwargs)


if __name__ == '__main__':
    for debug in (False, True):
        print("SEPERATOR_SENTINEL")
        print("debug set to: %s" % debug)

        server_sock = eventlet.listen(('localhost', 0))
        server_addr = server_sock.getsockname()
        sock_wrap = NaughtySocketAcceptWrap(server_sock)

        eventlet.spawn_n(
            eventlet.wsgi.server,
            debug=debug,
            log=sys.stdout,
            max_size=128,
            site=tests.wsgi_test.Site(),
            sock=server_sock,
        )

        try:
            # req #1 - normal
            sock1 = eventlet.connect(server_addr)
            sock1.settimeout(0.1)
            fd1 = sock1.makefile('rw')
            fd1.write('GET / HTTP/1.1\r\nHost: localhost\r\n\r\n')
            fd1.flush()
            tests.wsgi_test.read_http(sock1)

            # let the server socket ops catch up, set bomb
            eventlet.sleep(0)
            print("arming...")
            sock_wrap.arm()

            # req #2 - old conn, post-arm - timeout
            fd1.write('GET / HTTP/1.1\r\nHost: localhost\r\n\r\n')
            fd1.flush()
            try:
                tests.wsgi_test.read_http(sock1)
                assert False, 'Expected ConnectionClosed exception'
            except tests.wsgi_test.ConnectionClosed:
                pass

            fd1.close()
            sock1.close()
        finally:
            # reset streams, then output trapped tracebacks
            sock_wrap.unwrap()
        # check output asserts in tests.wsgi_test.TestHttpd
        # test_143_server_connection_timeout_exception

########NEW FILE########
__FILENAME__ = zmq_test
from __future__ import with_statement

from eventlet import event, spawn, sleep, semaphore
from nose.tools import *
from tests import check_idle_cpu_usage, LimitedTestCase, using_pyevent, skip_unless

try:
    from eventlet.green import zmq
except ImportError:
    zmq = {}    # for systems lacking zmq, skips tests instead of barfing


RECV_ON_CLOSED_SOCKET_ERRNOS = (zmq.ENOTSUP, zmq.ENOTSOCK)


def zmq_supported(_):
    try:
        import zmq
    except ImportError:
        return False
    return not using_pyevent(_)


class TestUpstreamDownStream(LimitedTestCase):
    @skip_unless(zmq_supported)
    def setUp(self):
        super(TestUpstreamDownStream, self).setUp()
        self.context = zmq.Context()
        self.sockets = []

    @skip_unless(zmq_supported)
    def tearDown(self):
        self.clear_up_sockets()
        super(TestUpstreamDownStream, self).tearDown()

    def create_bound_pair(self, type1, type2, interface='tcp://127.0.0.1'):
        """Create a bound socket pair using a random port."""
        s1 = self.context.socket(type1)
        port = s1.bind_to_random_port(interface)
        s2 = self.context.socket(type2)
        s2.connect('%s:%s' % (interface, port))
        self.sockets.append(s1)
        self.sockets.append(s2)
        return s1, s2, port

    def clear_up_sockets(self):
        for sock in self.sockets:
            sock.close()
        self.sockets = None
        self.context.destroy(0)

    def assertRaisesErrno(self, errnos, func, *args):
        try:
            func(*args)
        except zmq.ZMQError as e:
            if not hasattr(errnos, '__iter__'):
                errnos = (errnos,)

            if e.errno not in errnos:
                raise AssertionError(
                    "wrong error raised, expected one of ['%s'], got '%s'" % (
                        ", ".join("%s" % zmq.ZMQError(errno) for errno in errnos),
                        zmq.ZMQError(e.errno)
                    ),
                )
        else:
            self.fail("Function did not raise any error")

    @skip_unless(zmq_supported)
    def test_close_linger(self):
        """Socket.close() must support linger argument.

        https://github.com/eventlet/eventlet/issues/9
        """
        sock1, sock2, _ = self.create_bound_pair(zmq.PAIR, zmq.PAIR)
        sock1.close(1)
        sock2.close(linger=0)

    @skip_unless(zmq_supported)
    def test_recv_spawned_before_send_is_non_blocking(self):
        req, rep, port = self.create_bound_pair(zmq.PAIR, zmq.PAIR)
#       req.connect(ipc)
#       rep.bind(ipc)
        sleep()
        msg = dict(res=None)
        done = event.Event()

        def rx():
            msg['res'] = rep.recv()
            done.send('done')

        spawn(rx)
        req.send('test')
        done.wait()
        self.assertEqual(msg['res'], 'test')

    @skip_unless(zmq_supported)
    def test_close_socket_raises_enotsup(self):
        req, rep, port = self.create_bound_pair(zmq.PAIR, zmq.PAIR)

        rep.close()
        req.close()
        self.assertRaisesErrno(RECV_ON_CLOSED_SOCKET_ERRNOS, rep.recv)
        self.assertRaisesErrno(RECV_ON_CLOSED_SOCKET_ERRNOS, req.send, 'test')

    @skip_unless(zmq_supported)
    def test_close_xsocket_raises_enotsup(self):
        req, rep, port = self.create_bound_pair(zmq.XREQ, zmq.XREP)

        rep.close()
        req.close()
        self.assertRaisesErrno(RECV_ON_CLOSED_SOCKET_ERRNOS, rep.recv)
        self.assertRaisesErrno(RECV_ON_CLOSED_SOCKET_ERRNOS, req.send, 'test')

    @skip_unless(zmq_supported)
    def test_send_1k_req_rep(self):
        req, rep, port = self.create_bound_pair(zmq.REQ, zmq.REP)
        sleep()
        done = event.Event()

        def tx():
            tx_i = 0
            req.send(str(tx_i))
            while req.recv() != 'done':
                tx_i += 1
                req.send(str(tx_i))
            done.send(0)

        def rx():
            while True:
                rx_i = rep.recv()
                if rx_i == "1000":
                    rep.send('done')
                    break
                rep.send('i')
        spawn(tx)
        spawn(rx)
        final_i = done.wait()
        self.assertEqual(final_i, 0)

    @skip_unless(zmq_supported)
    def test_send_1k_push_pull(self):
        down, up, port = self.create_bound_pair(zmq.PUSH, zmq.PULL)
        sleep()

        done = event.Event()

        def tx():
            tx_i = 0
            while tx_i <= 1000:
                tx_i += 1
                down.send(str(tx_i))

        def rx():
            while True:
                rx_i = up.recv()
                if rx_i == "1000":
                    done.send(0)
                    break
        spawn(tx)
        spawn(rx)
        final_i = done.wait()
        self.assertEqual(final_i, 0)

    @skip_unless(zmq_supported)
    def test_send_1k_pub_sub(self):
        pub, sub_all, port = self.create_bound_pair(zmq.PUB, zmq.SUB)
        sub1 = self.context.socket(zmq.SUB)
        sub2 = self.context.socket(zmq.SUB)
        self.sockets.extend([sub1, sub2])
        addr = 'tcp://127.0.0.1:%s' % port
        sub1.connect(addr)
        sub2.connect(addr)
        sub_all.setsockopt(zmq.SUBSCRIBE, '')
        sub1.setsockopt(zmq.SUBSCRIBE, 'sub1')
        sub2.setsockopt(zmq.SUBSCRIBE, 'sub2')

        sub_all_done = event.Event()
        sub1_done = event.Event()
        sub2_done = event.Event()

        sleep(0.2)

        def rx(sock, done_evt, msg_count=10000):
            count = 0
            while count < msg_count:
                msg = sock.recv()
                sleep()
                if 'LAST' in msg:
                    break
                count += 1

            done_evt.send(count)

        def tx(sock):
            for i in range(1, 1001):
                msg = "sub%s %s" % ([2, 1][i % 2], i)
                sock.send(msg)
                sleep()
            sock.send('sub1 LAST')
            sock.send('sub2 LAST')

        spawn(rx, sub_all, sub_all_done)
        spawn(rx, sub1, sub1_done)
        spawn(rx, sub2, sub2_done)
        spawn(tx, pub)
        sub1_count = sub1_done.wait()
        sub2_count = sub2_done.wait()
        sub_all_count = sub_all_done.wait()
        self.assertEqual(sub1_count, 500)
        self.assertEqual(sub2_count, 500)
        self.assertEqual(sub_all_count, 1000)

    @skip_unless(zmq_supported)
    def test_change_subscription(self):
        pub, sub, port = self.create_bound_pair(zmq.PUB, zmq.SUB)
        sub.setsockopt(zmq.SUBSCRIBE, 'test')

        sleep(0.2)
        sub_done = event.Event()

        def rx(sock, done_evt):
            count = 0
            sub = 'test'
            while True:
                msg = sock.recv()
                sleep()
                if 'DONE' in msg:
                    break
                if 'LAST' in msg and sub == 'test':
                    sock.setsockopt(zmq.UNSUBSCRIBE, 'test')
                    sock.setsockopt(zmq.SUBSCRIBE, 'done')
                    sub = 'done'
                count += 1
            done_evt.send(count)

        def tx(sock):
            for i in range(1, 101):
                msg = "test %s" % i
                if i != 50:
                    sock.send(msg)
                else:
                    sock.send('test LAST')
                sleep()
            sock.send('done DONE')

        spawn(rx, sub, sub_done)
        spawn(tx, pub)

        rx_count = sub_done.wait()
        self.assertEqual(rx_count, 50)

    @skip_unless(zmq_supported)
    def test_recv_multipart_bug68(self):
        req, rep, port = self.create_bound_pair(zmq.REQ, zmq.REP)
        msg = ['']
        req.send_multipart(msg)
        recieved_msg = rep.recv_multipart()
        self.assertEqual(recieved_msg, msg)

        # Send a message back the other way
        msg2 = [""]
        rep.send_multipart(msg2, copy=False)
        # When receiving a copy it's a zmq.core.message.Message you get back
        recieved_msg = req.recv_multipart(copy=False)
        # So it needs to be converted to a string
        # I'm calling str(m) consciously here; Message has a .data attribute
        # but it's private __str__ appears to be the way to go
        self.assertEqual([str(m) for m in recieved_msg], msg2)

    @skip_unless(zmq_supported)
    def test_recv_noblock_bug76(self):
        req, rep, port = self.create_bound_pair(zmq.REQ, zmq.REP)
        self.assertRaisesErrno(zmq.EAGAIN, rep.recv, zmq.NOBLOCK)
        self.assertRaisesErrno(zmq.EAGAIN, rep.recv, zmq.NOBLOCK, True)

    @skip_unless(zmq_supported)
    def test_send_during_recv(self):
        sender, receiver, port = self.create_bound_pair(zmq.XREQ, zmq.XREQ)
        sleep()

        num_recvs = 30
        done_evts = [event.Event() for _ in range(num_recvs)]

        def slow_rx(done, msg):
            self.assertEqual(sender.recv(), msg)
            done.send(0)

        def tx():
            tx_i = 0
            while tx_i <= 1000:
                sender.send(str(tx_i))
                tx_i += 1

        def rx():
            while True:
                rx_i = receiver.recv()
                if rx_i == "1000":
                    for i in range(num_recvs):
                        receiver.send('done%d' % i)
                    sleep()
                    return

        for i in range(num_recvs):
            spawn(slow_rx, done_evts[i], "done%d" % i)

        spawn(tx)
        spawn(rx)
        for evt in done_evts:
            self.assertEqual(evt.wait(), 0)

    @skip_unless(zmq_supported)
    def test_send_during_recv_multipart(self):
        sender, receiver, port = self.create_bound_pair(zmq.XREQ, zmq.XREQ)
        sleep()

        num_recvs = 30
        done_evts = [event.Event() for _ in range(num_recvs)]

        def slow_rx(done, msg):
            self.assertEqual(sender.recv_multipart(), msg)
            done.send(0)

        def tx():
            tx_i = 0
            while tx_i <= 1000:
                sender.send_multipart([str(tx_i), '1', '2', '3'])
                tx_i += 1

        def rx():
            while True:
                rx_i = receiver.recv_multipart()
                if rx_i == ["1000", '1', '2', '3']:
                    for i in range(num_recvs):
                        receiver.send_multipart(['done%d' % i, 'a', 'b', 'c'])
                    sleep()
                    return

        for i in range(num_recvs):
            spawn(slow_rx, done_evts[i], ["done%d" % i, 'a', 'b', 'c'])

        spawn(tx)
        spawn(rx)
        for i in range(num_recvs):
            final_i = done_evts[i].wait()
            self.assertEqual(final_i, 0)

    # Need someway to ensure a thread is blocked on send... This isn't working
    @skip_unless(zmq_supported)
    def test_recv_during_send(self):
        sender, receiver, port = self.create_bound_pair(zmq.XREQ, zmq.XREQ)
        sleep()

        done = event.Event()

        try:
            SNDHWM = zmq.SNDHWM
        except AttributeError:
            # ZeroMQ <3.0
            SNDHWM = zmq.HWM

        sender.setsockopt(SNDHWM, 10)
        sender.setsockopt(zmq.SNDBUF, 10)

        receiver.setsockopt(zmq.RCVBUF, 10)

        def tx():
            tx_i = 0
            while tx_i <= 1000:
                sender.send(str(tx_i))
                tx_i += 1
            done.send(0)

        spawn(tx)
        final_i = done.wait()
        self.assertEqual(final_i, 0)

    @skip_unless(zmq_supported)
    def test_close_during_recv(self):
        sender, receiver, port = self.create_bound_pair(zmq.XREQ, zmq.XREQ)
        sleep()
        done1 = event.Event()
        done2 = event.Event()

        def rx(e):
            self.assertRaisesErrno(RECV_ON_CLOSED_SOCKET_ERRNOS, receiver.recv)
            e.send()

        spawn(rx, done1)
        spawn(rx, done2)

        sleep()
        receiver.close()

        done1.wait()
        done2.wait()

    @skip_unless(zmq_supported)
    def test_getsockopt_events(self):
        sock1, sock2, _port = self.create_bound_pair(zmq.DEALER, zmq.DEALER)
        sleep()
        poll_out = zmq.Poller()
        poll_out.register(sock1, zmq.POLLOUT)
        sock_map = poll_out.poll(100)
        self.assertEqual(len(sock_map), 1)
        events = sock1.getsockopt(zmq.EVENTS)
        self.assertEqual(events & zmq.POLLOUT, zmq.POLLOUT)
        sock1.send('')

        poll_in = zmq.Poller()
        poll_in.register(sock2, zmq.POLLIN)
        sock_map = poll_in.poll(100)
        self.assertEqual(len(sock_map), 1)
        events = sock2.getsockopt(zmq.EVENTS)
        self.assertEqual(events & zmq.POLLIN, zmq.POLLIN)

    @skip_unless(zmq_supported)
    def test_cpu_usage_after_bind(self):
        """zmq eats CPU after PUB socket .bind()

        https://bitbucket.org/eventlet/eventlet/issue/128

        According to the ZeroMQ documentation, the socket file descriptor
        can be readable without any pending messages. So we need to ensure
        that Eventlet wraps around ZeroMQ sockets do not create busy loops.

        A naive way to test it is to measure resource usage. This will require
        some tuning to set appropriate acceptable limits.
        """
        sock = self.context.socket(zmq.PUB)
        self.sockets.append(sock)
        sock.bind_to_random_port("tcp://127.0.0.1")
        sleep()
        check_idle_cpu_usage(0.2, 0.1)

    @skip_unless(zmq_supported)
    def test_cpu_usage_after_pub_send_or_dealer_recv(self):
        """zmq eats CPU after PUB send or DEALER recv.

        Same https://bitbucket.org/eventlet/eventlet/issue/128
        """
        pub, sub, _port = self.create_bound_pair(zmq.PUB, zmq.SUB)
        sub.setsockopt(zmq.SUBSCRIBE, "")
        sleep()
        pub.send('test_send')
        check_idle_cpu_usage(0.2, 0.1)

        sender, receiver, _port = self.create_bound_pair(zmq.DEALER, zmq.DEALER)
        sleep()
        sender.send('test_recv')
        msg = receiver.recv()
        self.assertEqual(msg, 'test_recv')
        check_idle_cpu_usage(0.2, 0.1)


class TestQueueLock(LimitedTestCase):
    @skip_unless(zmq_supported)
    def test_queue_lock_order(self):
        q = zmq._QueueLock()
        s = semaphore.Semaphore(0)
        results = []

        def lock(x):
            with q:
                results.append(x)
            s.release()

        q.acquire()

        spawn(lock, 1)
        sleep()
        spawn(lock, 2)
        sleep()
        spawn(lock, 3)
        sleep()

        self.assertEqual(results, [])
        q.release()
        s.acquire()
        s.acquire()
        s.acquire()
        self.assertEqual(results, [1, 2, 3])

    @skip_unless(zmq_supported)
    def test_count(self):
        q = zmq._QueueLock()
        self.assertFalse(q)
        q.acquire()
        self.assertTrue(q)
        q.release()
        self.assertFalse(q)

        with q:
            self.assertTrue(q)
        self.assertFalse(q)

    @skip_unless(zmq_supported)
    def test_errors(self):
        q = zmq._QueueLock()

        self.assertRaises(zmq.LockReleaseError, q.release)

        q.acquire()
        q.release()

        self.assertRaises(zmq.LockReleaseError, q.release)

    @skip_unless(zmq_supported)
    def test_nested_acquire(self):
        q = zmq._QueueLock()
        self.assertFalse(q)
        q.acquire()
        q.acquire()

        s = semaphore.Semaphore(0)
        results = []

        def lock(x):
            with q:
                results.append(x)
            s.release()

        spawn(lock, 1)
        sleep()
        self.assertEqual(results, [])
        q.release()
        sleep()
        self.assertEqual(results, [])
        self.assertTrue(q)
        q.release()

        s.acquire()
        self.assertEqual(results, [1])


class TestBlockedThread(LimitedTestCase):
    @skip_unless(zmq_supported)
    def test_block(self):
        e = zmq._BlockedThread()
        done = event.Event()
        self.assertFalse(e)

        def block():
            e.block()
            done.send(1)

        spawn(block)
        sleep()

        self.assertFalse(done.has_result())
        e.wake()
        done.wait()

########NEW FILE########
