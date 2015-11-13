__FILENAME__ = amqp
#-*- coding: utf-8 -*-
"""
A simple worker with a AMQP consumer.

This example shows how to implement a simple AMQP consumer
based on `Kombu <http://github.com/ask/kombu>`_ and shows you
what different kind of workers you can put to a arbiter
to manage the worker lifetime, event handling and shutdown/reload szenarios.
"""
import sys
import time
import socket
import logging
from pistil.arbiter import Arbiter
from pistil.worker import Worker
from kombu.connection import BrokerConnection
from kombu.messaging import Exchange, Queue, Consumer, Producer


CONNECTION = ('localhost', 'guest', 'default', '/')

log = logging.getLogger(__name__)


class AMQPWorker(Worker):

    queues = [
        {'routing_key': 'test',
         'name': 'test',
         'handler': 'handle_test'
        }
    ]

    _connection = None

    def handle_test(self, body, message):
        log.debug("Handle message: %s" % body)
        message.ack()

    def handle(self):
        log.debug("Start consuming")
        exchange = Exchange('amqp.topic', type='direct', durable=True)
        self._connection = BrokerConnection(*CONNECTION)
        channel = self._connection.channel()

        for entry in self.queues:
            log.debug("prepare to consume %s" % entry['routing_key'])
            queue = Queue(entry['name'], exchange=exchange,
                          routing_key=entry['routing_key'])
            consumer = Consumer(channel, queue)
            consumer.register_callback(getattr(self, entry['handler']))
            consumer.consume()

        log.debug("start consuming...")
        while True:
            try:
                self._connection.drain_events()
            except socket.timeout:
                log.debug("nothing to consume...")
                break
        self._connection.close()

    def run(self):
        while self.alive:
            try:
                self.handle()
            except Exception:
                self.alive = False
                raise

    def handle_quit(self, sig, frame):
        if self._connection is not None:
            self._connection.close()
        self.alive = False

    def handle_exit(self, sig, frame):
        if self._connection is not None:
            self._connection.close()
        self.alive = False
        sys.exit(0)


if __name__ == "__main__":
    conf = {}
    specs = [(AMQPWorker, None, "worker", {}, "test")]
    a = Arbiter(conf, specs)
    a.run()

########NEW FILE########
__FILENAME__ = hello
# -*- coding: utf-8 -
#
# This file is part of pistil released under the MIT license. 
# See the NOTICE for more information.

import time

from pistil.arbiter import Arbiter
from pistil.worker import Worker


class MyWorker(Worker):

    def handle(self):
        print "hello from worker n°%s" % self.pid


if __name__ == "__main__":
    conf = {}
    specs = [(MyWorker, 30, "worker", {}, "test")]
    a = Arbiter(conf, specs)
    a.run()

########NEW FILE########
__FILENAME__ = hello_pool
# -*- coding: utf-8 -
#
# This file is part of pistil released under the MIT license. 
# See the NOTICE for more information.

from pistil.pool import PoolArbiter
from pistil.worker import Worker

class MyWorker(Worker):

    def handle(self):
        print "hello from worker n°%s" % self.pid

if __name__ == "__main__":
    conf = {"num_workers": 3 }
    spec = (MyWorker, 30, "worker", {}, "test",)
    a = PoolArbiter(conf, spec)
    a.run()

########NEW FILE########
__FILENAME__ = multiworker
# -*- coding: utf-8 -
#
# This file is part of pistil released under the MIT license. 
# See the NOTICE for more information.

from pistil.arbiter import Arbiter
from pistil.worker import Worker


class MyWorker(Worker):

    def handle(self): 
        print "hello worker 1 from %s" % self.name

class MyWorker2(Worker):

    def handle(self):
        print "hello worker 2 from %s" % self.name


if __name__ == '__main__':
    conf = {}

    specs = [
        (MyWorker, 30, "worker", {}, "w1"),
        (MyWorker2, 30, "worker", {}, "w2"),
        (MyWorker2, 30, "kill", {}, "w3")
    ]
    # launchh the arbiter
    arbiter = Arbiter(conf, specs)
    arbiter.run()

########NEW FILE########
__FILENAME__ = multiworker2
# -*- coding: utf-8 -
#
# This file is part of pistil released under the MIT license. 
# See the NOTICE for more information.

import time
import urllib2

from pistil.arbiter import Arbiter
from pistil.worker import Worker
from pistil.tcp.sync_worker import TcpSyncWorker
from pistil.tcp.arbiter import TcpArbiter

from http_parser.http import HttpStream
from http_parser.reader import SocketReader

class MyTcpWorker(TcpSyncWorker):

    def handle(self, sock, addr):
        p = HttpStream(SocketReader(sock))

        path = p.path()
        data = "welcome wold"
        sock.send("".join(["HTTP/1.1 200 OK\r\n", 
                        "Content-Type: text/html\r\n",
                        "Content-Length:" + str(len(data)) + "\r\n",
                         "Connection: close\r\n\r\n",
                         data]))


class UrlWorker(Worker):

    def run(self):
        print "ici"
        while self.alive: 
            time.sleep(0.1)
            f = urllib2.urlopen("http://localhost:5000")
            print f.read()
            self.notify() 

class MyPoolArbiter(TcpArbiter):

    def on_init(self, conf):
        TcpArbiter.on_init(self, conf)
        # we return a spec
        return (MyTcpWorker, 30, "worker", {}, "http_welcome",)


if __name__ == '__main__':
    conf = {"num_workers": 3, "address": ("127.0.0.1", 5000)}

    specs = [
        (MyPoolArbiter, 30, "supervisor", {}, "tcp_pool"),
        (UrlWorker, 30, "worker", {}, "grabber")
    ]

    arbiter = Arbiter(conf, specs)
    arbiter.run()





########NEW FILE########
__FILENAME__ = serve_file
# -*- coding: utf-8 -
#
# This file is part of gunicorn released under the MIT license. 
# See the NOTICE for more information.

import mimetypes
import os


from gevent import monkey
monkey.noisy = False
monkey.patch_all()


from http_parser.http import HttpStream
from http_parser.reader import SocketReader

from pistil import util
from pistil.tcp.arbiter import TcpArbiter
from pistil.tcp.gevent_worker import TcpGeventWorker

CURDIR = os.path.dirname(__file__)

try:
    # Python 3.3 has os.sendfile().
    from os import sendfile
except ImportError:
    try:
        from _sendfile import sendfile
    except ImportError:
        sendfile = None

def write_error(sock, status_int, reason, mesg):
    html = textwrap.dedent("""\
    <html>
      <head>
        <title>%(reason)s</title>
      </head>
      <body>
        <h1>%(reason)s</h1>
        %(mesg)s
      </body>
    </html>
    """) % {"reason": reason, "mesg": mesg}

    http = textwrap.dedent("""\
    HTTP/1.1 %s %s\r
    Connection: close\r
    Content-Type: text/html\r
    Content-Length: %d\r
    \r
    %s
    """) % (str(status_int), reason, len(html), html)
    write_nonblock(sock, http)



class HttpWorker(TcpGeventWorker):

    def handle(self, sock, addr):
        p = HttpStream(SocketReader(sock))

        path = p.path()

        if not path or path == "/":
            path = "index.html"
        
        if path.startswith("/"):
            path = path[1:]
        
        real_path = os.path.join(CURDIR, "static", path)

        if os.path.isdir(real_path):
            lines = ["<ul>"]
            for d in os.listdir(real_path):
                fpath = os.path.join(real_path, d)
                lines.append("<li><a href=" + d + ">" + d + "</a>")

            data = "".join(lines)
            resp = "".join(["HTTP/1.1 200 OK\r\n", 
                            "Content-Type: text/html\r\n",
                            "Content-Length:" + str(len(data)) + "\r\n",
                            "Connection: close\r\n\r\n",
                            data])
            sock.sendall(resp)

        elif not os.path.exists(real_path):
            util.write_error(sock, 404, "Not found", real_path + " not found")
        else:
            ctype = mimetypes.guess_type(real_path)[0]

            if ctype.startswith('text') or 'html' in ctype:

                try:
                    f = open(real_path, 'rb')
                    data = f.read()
                    resp = "".join(["HTTP/1.1 200 OK\r\n", 
                                "Content-Type: " + ctype + "\r\n",
                                "Content-Length:" + str(len(data)) + "\r\n",
                                "Connection: close\r\n\r\n",
                                data])
                    sock.sendall(resp)
                finally:
                    f.close()
            else:

                try:
                    f = open(real_path, 'r')
                    clen = int(os.fstat(f.fileno())[6])
                    
                    # send headers
                    sock.send("".join(["HTTP/1.1 200 OK\r\n", 
                                "Content-Type: " + ctype + "\r\n",
                                "Content-Length:" + str(clen) + "\r\n",
                                 "Connection: close\r\n\r\n"]))

                    if not sendfile:
                        while True:
                            data = f.read(4096)
                            if not data:
                                break
                            sock.send(data)
                    else:
                        fileno = f.fileno()
                        sockno = sock.fileno()
                        sent = 0
                        offset = 0
                        nbytes = clen
                        sent += sendfile(sockno, fileno, offset+sent, nbytes-sent)
                        while sent != nbytes:
                            sent += sendfile(sock.fileno(), fileno, offset+sent, nbytes-sent)


                finally:
                    f.close()


def main():
    conf = {"address": ("127.0.0.1", 5000), "debug": True,
            "num_workers": 3}
    spec = (HttpWorker, 30, "send_file", {}, "worker",)
    
    arbiter = TcpArbiter(conf, spec)
    arbiter.run()


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = tcp_hello
# -*- coding: utf-8 -
#
# This file is part of pistil released under the MIT license. 
# See the NOTICE for more information.

from pistil.tcp.sync_worker import TcpSyncWorker
from pistil.tcp.arbiter import TcpArbiter

from http_parser.http import HttpStream
from http_parser.reader import SocketReader

class MyTcpWorker(TcpSyncWorker):

    def handle(self, sock, addr):
        p = HttpStream(SocketReader(sock))

        path = p.path()
        data = "hello world"
        sock.send("".join(["HTTP/1.1 200 OK\r\n", 
                        "Content-Type: text/html\r\n",
                        "Content-Length:" + str(len(data)) + "\r\n",
                         "Connection: close\r\n\r\n",
                         data]))

if __name__ == '__main__':
    conf = {"num_workers": 3}
    spec = (MyTcpWorker, 30, "worker", {}, "worker",)
    
    arbiter = TcpArbiter(conf, spec)

    arbiter.run()


########NEW FILE########
__FILENAME__ = _sendfile
# -*- coding: utf-8 -
#
# This file is part of gunicorn released under the MIT license. 
# See the NOTICE for more information.

import errno
import os
import sys

try:
    import ctypes
    import ctypes.util
except MemoryError:
    # selinux execmem denial
    # https://bugzilla.redhat.com/show_bug.cgi?id=488396
    raise ImportError

SUPPORTED_PLATFORMS = (
        'darwin',
        'freebsd',
        'dragonfly',
        'linux2')

if sys.version_info < (2, 6) or \
        sys.platform not in SUPPORTED_PLATFORMS:
    raise ImportError("sendfile isn't supported on this platform")

_libc = ctypes.CDLL(ctypes.util.find_library("c"), use_errno=True)
_sendfile = _libc.sendfile

def sendfile(fdout, fdin, offset, nbytes):
    if sys.platform == 'darwin':
        _sendfile.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.c_uint64,
                              ctypes.POINTER(ctypes.c_uint64), ctypes.c_voidp,
                              ctypes.c_int]
        _nbytes = ctypes.c_uint64(nbytes)
        result = _sendfile(fdin, fdout, offset, _nbytes, None, 0)
        
        if result == -1:
            e = ctypes.get_errno()
            if e == errno.EAGAIN and _nbytes.value:
                return nbytes.value
            raise OSError(e, os.strerror(e))
        return _nbytes.value
    elif sys.platform in ('freebsd', 'dragonfly',):
        _sendfile.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.c_uint64,
                              ctypes.c_uint64, ctypes.c_voidp,
                              ctypes.POINTER(ctypes.c_uint64), ctypes.c_int]
        _sbytes = ctypes.c_uint64()
        result = _sendfile(fdin, fdout, offset, nbytes, None, _sbytes, 0)
        if result == -1:
            e = ctypes.get_errno()
            if e == errno.EAGAIN and _sbytes.value:
                return _sbytes.value
            raise OSError(e, os.strerror(e))
        return _sbytes.value

    else:
        _sendfile.argtypes = [ctypes.c_int, ctypes.c_int,
                ctypes.POINTER(ctypes.c_uint64), ctypes.c_size_t]

        _offset = ctypes.c_uint64(offset)
        sent = _sendfile(fdout, fdin, _offset, nbytes) 
        if sent == -1:
            e = ctypes.get_errno()
            raise OSError(e, os.strerror(e))
        return sent


########NEW FILE########
__FILENAME__ = arbiter
# -*- coding: utf-8 -
#
# This file is part of pistil released under the MIT license. 
# See the NOTICE for more information.

from __future__ import with_statement

import errno
import logging
import os
import select
import signal
import sys
import time
import traceback

from pistil.errors import HaltServer
from pistil.workertmp import WorkerTmp
from pistil import util
from pistil import __version__, SERVER_SOFTWARE

LOG_LEVELS = {
    "critical": logging.CRITICAL,
    "error": logging.ERROR,
    "warning": logging.WARNING,
    "info": logging.INFO,
    "debug": logging.DEBUG
}

DEFAULT_CONF = dict(
    uid = os.geteuid(),
    gid = os.getegid(),
    umask = 0,
    debug = False,
)


RESTART_WORKERS = ("worker", "supervisor")

log = logging.getLogger(__name__)


logging.basicConfig(format="%(asctime)s [%(process)d] [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S", level=logging.DEBUG)




class Child(object):

    def __init__(self, child_class, timeout, child_type,
            args, name):
        self.child_class= child_class
        self.timeout = timeout
        self.child_type = child_type
        self.args = args
        self.name = name


# chaine init worker:
# (WorkerClass, max_requests, timeout, type, args, name)
# types: supervisor, kill, brutal_kill, worker
# timeout: integer in seconds or None

class Arbiter(object):
    """
    Arbiter maintain the workers processes alive. It launches or
    kills them if needed. It also manages application reloading
    via SIGHUP/USR2.
    """

    _SPECS_BYNAME = {}
    _CHILDREN_SPECS = []

    # A flag indicating if a worker failed to
    # to boot. If a worker process exist with
    # this error code, the arbiter will terminate.
    _WORKER_BOOT_ERROR = 3

    _WORKERS = {}    
    _PIPE = []

    # I love dynamic languages
    _SIG_QUEUE = []
    _SIGNALS = map(
        lambda x: getattr(signal, "SIG%s" % x),
        "HUP QUIT INT TERM USR1 WINCH".split()
    )
    _SIG_NAMES = dict(
        (getattr(signal, name), name[3:].lower()) for name in dir(signal)
        if name[:3] == "SIG" and name[3] != "_"
    )
    
    def __init__(self, args, specs=[], name=None,
            child_type="supervisor", age=0, ppid=0,
            timeout=30):

        # set conf
        conf = DEFAULT_CONF.copy()
        conf.update(args)
        self.conf = conf


        specs.extend(self.on_init(conf))

        for spec in specs:
            c = Child(*spec)
            self._CHILDREN_SPECS.append(c)
            self._SPECS_BYNAME[c.name] = c


        if name is None:
            name =  self.__class__.__name__
        self.name = name
        self.child_type = child_type
        self.age = age
        self.ppid = ppid
        self.timeout = timeout


        self.pid = None
        self.num_children = len(self._CHILDREN_SPECS)
        self.child_age = 0
        self.booted = False
        self.stopping = False
        self.debug =self.conf.get("debug", False)
        self.tmp = WorkerTmp(self.conf)
        
    def on_init(self, args):
        return []


    def on_init_process(self):
        """ method executed when we init a process """
        pass


    def init_process(self):
        """\
        If you override this method in a subclass, the last statement
        in the function should be to call this method with
        super(MyWorkerClass, self).init_process() so that the ``run()``
        loop is initiated.
        """

        # set current pid
        self.pid = os.getpid()
        
        util.set_owner_process(self.conf.get("uid", os.geteuid()),
                self.conf.get("gid", os.getegid()))

        # Reseed the random number generator
        util.seed()

        # prevent fd inheritance
        util.close_on_exec(self.tmp.fileno())

         # init signals
        self.init_signals()

        util._setproctitle("arbiter [%s]" % self.name)
        self.on_init_process()

        log.debug("Arbiter %s booted on %s", self.name, self.pid)
        self.when_ready()
        # Enter main run loop
        self.booted = True
        self.run()
    

    def when_ready(self):
        pass

    def init_signals(self):
        """\
        Initialize master signal handling. Most of the signals
        are queued. Child signals only wake up the master.
        """
        if self._PIPE:
            map(os.close, self._PIPE)
        self._PIPE = pair = os.pipe()
        map(util.set_non_blocking, pair)
        map(util.close_on_exec, pair)
        map(lambda s: signal.signal(s, self.signal), self._SIGNALS)
        signal.signal(signal.SIGCHLD, self.handle_chld)

    def signal(self, sig, frame):
        if len(self._SIG_QUEUE) < 5:
            self._SIG_QUEUE.append(sig)
            self.wakeup()
        else:
            log.warn("Dropping signal: %s", sig)

    def run(self):
        "Main master loop." 
        if not self.booted:
            return self.init_process()

        self.spawn_workers()
        while True:
            try:
                # notfy the master
                self.tmp.notify()
                self.reap_workers()
                sig = self._SIG_QUEUE.pop(0) if len(self._SIG_QUEUE) else None
                if sig is None:
                    self.sleep()
                    self.murder_workers()
                    self.manage_workers()
                    continue
                
                if sig not in self._SIG_NAMES:
                    log.info("Ignoring unknown signal: %s", sig)
                    continue
                
                signame = self._SIG_NAMES.get(sig)
                handler = getattr(self, "handle_%s" % signame, None)
                if not handler:
                    log.error("Unhandled signal: %s", signame)
                    continue
                log.info("Handling signal: %s", signame)
                handler()
                self.tmp.notify()
                self.wakeup()
            except StopIteration:
                self.halt()
            except KeyboardInterrupt:
                self.halt()
            except HaltServer, inst:
                self.halt(reason=inst.reason, exit_status=inst.exit_status)
            except SystemExit:
                raise
            except Exception:
                log.info("Unhandled exception in main loop:\n%s",  
                            traceback.format_exc())
                self.stop(False)
                sys.exit(-1)

    def handle_chld(self, sig, frame):
        "SIGCHLD handling"
        self.wakeup()
        self.reap_workers()
        
    def handle_hup(self):
        """\
        HUP handling.
        - Reload configuration
        - Start the new worker processes with a new configuration
        - Gracefully shutdown the old worker processes
        """
        log.info("Hang up: %s", self.name)
        self.reload()
        
    def handle_quit(self):
        "SIGQUIT handling"
        raise StopIteration
    
    def handle_int(self):
        "SIGINT handling"
        raise StopIteration
    
    def handle_term(self):
        "SIGTERM handling"
        self.stop(False)
        raise StopIteration

    def handle_usr1(self):
        """\
        SIGUSR1 handling.
        Kill all workers by sending them a SIGUSR1
        """
        self.kill_workers(signal.SIGUSR1)
    
    def handle_winch(self):
        "SIGWINCH handling"
        if os.getppid() == 1 or os.getpgrp() != os.getpid():
            log.info("graceful stop of workers")
            self.num_workers = 0
            self.kill_workers(signal.SIGQUIT)
        else:
            log.info("SIGWINCH ignored. Not daemonized")
    
    def wakeup(self):
        """\
        Wake up the arbiter by writing to the _PIPE
        """
        try:
            os.write(self._PIPE[1], '.')
        except IOError, e:
            if e.errno not in [errno.EAGAIN, errno.EINTR]:
                raise
        
                    
    def halt(self, reason=None, exit_status=0):
        """ halt arbiter """
        log.info("Shutting down: %s", self.name)
        if reason is not None:
            log.info("Reason: %s", reason)
        self.stop()
        log.info("See you next")
        sys.exit(exit_status)
        
    def sleep(self):
        """\
        Sleep until _PIPE is readable or we timeout.
        A readable _PIPE means a signal occurred.
        """
        try:
            ready = select.select([self._PIPE[0]], [], [], 1.0)
            if not ready[0]:
                return
            while os.read(self._PIPE[0], 1):
                pass
        except select.error, e:
            if e[0] not in [errno.EAGAIN, errno.EINTR]:
                raise
        except OSError, e:
            if e.errno not in [errno.EAGAIN, errno.EINTR]:
                raise
        except KeyboardInterrupt:
            sys.exit()
            
    
    def on_stop(self, graceful=True):
        """ method used to pass code when the server start """

    def stop(self, graceful=True):
        """\
        Stop workers
        
        :attr graceful: boolean, If True (the default) workers will be
        killed gracefully  (ie. trying to wait for the current connection)
        """
        
        ## pass any actions before we effectively stop
        self.on_stop(graceful=graceful)
        self.stopping = True
        sig = signal.SIGQUIT
        if not graceful:
            sig = signal.SIGTERM
        limit = time.time() + self.timeout
        while True:
            if time.time() >= limit or not self._WORKERS:
                break
            self.kill_workers(sig)
            time.sleep(0.1)
            self.reap_workers()
        self.kill_workers(signal.SIGKILL)   
        self.stopping = False

    def on_reload(self):
        """ method executed on reload """


    def reload(self):
        """ 
        used on HUP
        """
    
        # exec on reload hook
        self.on_reload()

        OLD__WORKERS = self._WORKERS.copy()

        # don't kill
        to_reload = []

        # spawn new workers with new app & conf
        for child in self._CHILDREN_SPECS:
            if child.child_type != "supervisor":
                to_reload.append(child)

        # set new proc_name
        util._setproctitle("arbiter [%s]" % self.name)
        
        # kill old workers
        for wpid, (child, state) in OLD__WORKERS.items():
            if state and child.timeout is not None:
                if child.child_type == "supervisor":
                    # we only reload suprvisors.
                    sig = signal.SIGHUP
                elif child.child_type == "brutal_kill":
                    sig =  signal.SIGTERM
                else:
                    sig =  signal.SIGQUIT
                self.kill_worker(wpid, sig)

        
    def murder_workers(self):
        """\
        Kill unused/idle workers
        """
        for (pid, child_info) in self._WORKERS.items():
            (child, state) = child_info
            if state and child.timeout is not None:
                try:
                    diff = time.time() - os.fstat(child.tmp.fileno()).st_ctime
                    if diff <= child.timeout:
                        continue
                except ValueError:
                    continue
            elif state and child.timeout is None:
                continue

            log.critical("WORKER TIMEOUT (pid:%s)", pid)
            self.kill_worker(pid, signal.SIGKILL)
        
    def reap_workers(self):
        """\
        Reap workers to avoid zombie processes
        """
        try:
            while True:
                wpid, status = os.waitpid(-1, os.WNOHANG)
                if not wpid:
                    break
                
                # A worker said it cannot boot. We'll shutdown
                # to avoid infinite start/stop cycles.
                exitcode = status >> 8
                if exitcode == self._WORKER_BOOT_ERROR:
                    reason = "Worker failed to boot."
                    raise HaltServer(reason, self._WORKER_BOOT_ERROR)
                child_info = self._WORKERS.pop(wpid, None)

                if not child_info:
                    continue

                child, state = child_info
                child.tmp.close()
                if child.child_type in RESTART_WORKERS and not self.stopping:
                    self._WORKERS["<killed %s>"  % id(child)] = (child, 0)
        except OSError, e:
            if e.errno == errno.ECHILD:
                pass
    
    def manage_workers(self):
        """\
        Maintain the number of workers by spawning or killing
        as required.
        """

        for pid, (child, state) in self._WORKERS.items():
            if not state:
                del self._WORKERS[pid]
                self.spawn_child(self._SPECS_BYNAME[child.name])

    def pre_fork(self, worker):
        """ methode executed on prefork """

    def post_fork(self, worker):
        """ method executed after we forked a worker """
            
    def spawn_child(self, child_spec):
        self.child_age += 1
        name = child_spec.name
        child_type = child_spec.child_type

        child_args = self.conf
        child_args.update(child_spec.args)

        try:
            # initialize child class
            child = child_spec.child_class(
                        child_args,
                        name = name,
                        child_type = child_type, 
                        age = self.child_age,
                        ppid = self.pid,
                        timeout = child_spec.timeout)
        except:
            log.info("Unhandled exception while creating '%s':\n%s",  
                            name, traceback.format_exc())
            return


        self.pre_fork(child)
        pid = os.fork()
        if pid != 0:
            self._WORKERS[pid] = (child, 1)
            return

        # Process Child
        worker_pid = os.getpid()
        try:
            util._setproctitle("worker %s [%s]" % (name,  worker_pid))
            log.info("Booting %s (%s) with pid: %s", name,
                    child_type, worker_pid)
            self.post_fork(child)
            child.init_process()
            sys.exit(0)
        except SystemExit:
            raise
        except:
            log.exception("Exception in worker process:")
            if not child.booted:
                sys.exit(self._WORKER_BOOT_ERROR)
            sys.exit(-1)
        finally:
            log.info("Worker exiting (pid: %s)", worker_pid)
            try:
                child.tmp.close()
            except:
                pass

    def spawn_workers(self):
        """\
        Spawn new workers as needed.
        
        This is where a worker process leaves the main loop
        of the master process.
        """
        
        for child in self._CHILDREN_SPECS: 
            self.spawn_child(child)

    def kill_workers(self, sig):
        """\
        Lill all workers with the signal `sig`
        :attr sig: `signal.SIG*` value
        """
        for pid in self._WORKERS.keys():
            self.kill_worker(pid, sig)
                   

    def kill_worker(self, pid, sig):
        """\
        Kill a worker
        
        :attr pid: int, worker pid
        :attr sig: `signal.SIG*` value
         """
        if not isinstance(pid, int):
            return

        try:
            os.kill(pid, sig)
        except OSError, e:
            if e.errno == errno.ESRCH:
                try:
                    (child, info) = self._WORKERS.pop(pid)
                    child.tmp.close()
           
                    if not self.stopping:
                        self._WORKERS["<killed %s>"  % id(child)] = (child, 0)
                    return
                except (KeyError, OSError):
                    return
            raise            

########NEW FILE########
__FILENAME__ = errors
# -*- coding: utf-8 -
#
# This file is part of pistil released under the MIT license. 
# See the NOTICE for more information.


class HaltServer(Exception):
    def __init__(self, reason, exit_status=1):
        self.reason = reason
        self.exit_status = exit_status
    
    def __str__(self):
        return "<HaltServer %r %d>" % (self.reason, self.exit_status)

########NEW FILE########
__FILENAME__ = pidfile
# -*- coding: utf-8 -
#
# This file is part of pistil released under the MIT license. 
# See the NOTICE for more information.

from __future__ import with_statement

import errno
import os
import tempfile


class Pidfile(object):
    """\
    Manage a PID file. If a specific name is provided
    it and '"%s.oldpid" % name' will be used. Otherwise
    we create a temp file using os.mkstemp.
    """

    def __init__(self, fname):
        self.fname = fname
        self.pid = None
        
    def create(self, pid):
        oldpid = self.validate()
        if oldpid:
            if oldpid == os.getpid():
                return
            raise RuntimeError("Already running on PID %s " \
                "(or pid file '%s' is stale)" % (os.getpid(), self.fname))

        self.pid = pid
        
        # Write pidfile
        fdir = os.path.dirname(self.fname)
        if fdir and not os.path.isdir(fdir):
            raise RuntimeError("%s doesn't exist. Can't create pidfile." % fdir)
        fd, fname = tempfile.mkstemp(dir=fdir)
        os.write(fd, "%s\n" % self.pid)
        if self.fname:
            os.rename(fname, self.fname)
        else:
            self.fname = fname
        os.close(fd)

        # set permissions to -rw-r--r-- 
        os.chmod(self.fname, 420)
        
    def rename(self, path):
        self.unlink()
        self.fname = path
        self.create(self.pid)
        
    def unlink(self):
        """ delete pidfile"""
        try:
            with open(self.fname, "r") as f:
                pid1 =  int(f.read() or 0)

            if pid1 == self.pid:
                os.unlink(self.fname)
        except:
            pass
       
    def validate(self):
        """ Validate pidfile and make it stale if needed"""
        if not self.fname:
            return
        try:
            with open(self.fname, "r") as f:
                wpid = int(f.read() or 0)

                if wpid <= 0:
                    return

                try:
                    os.kill(wpid, 0)
                    return wpid
                except OSError, e:
                    if e[0] == errno.ESRCH:
                        return
                    raise
        except IOError, e:
            if e[0] == errno.ENOENT:
                return
            raise


########NEW FILE########
__FILENAME__ = pool
# -*- coding: utf-8 -
#
# This file is part of pistil released under the MIT license. 
# See the NOTICE for more information.

import errno
import os
import signal

from pistil.errors import HaltServer
from pistil.arbiter import Arbiter, Child
from pistil.workertmp import WorkerTmp
from pistil import util

DEFAULT_CONF = dict(
    uid = os.geteuid(),
    gid = os.getegid(),
    umask = 0,
    debug = False,
    num_workers = 1,
)


class PoolArbiter(Arbiter):


    _SIGNALS = map(
        lambda x: getattr(signal, "SIG%s" % x),
        "HUP QUIT INT TERM TTIN TTOU USR1 USR2 WINCH".split()
    )

    def __init__(self, args, spec=(), name=None,
            child_type="supervisor", age=0, ppid=0,
            timeout=30):

        if not isinstance(spec, tuple):
            raise TypeError("spec should be a tuple")

        # set conf
        conf = DEFAULT_CONF.copy()
        conf.update(args)
        self.conf = conf

        # set number of workers
        self.num_workers = conf.get('num_workers', 1)
       
        ret =  self.on_init(conf)
        if not ret: 
            self._SPEC = Child(*spec)
        else:
            self._SPEC = Child(*ret)
        
        if name is None:
            name =  self.__class__.__name__

        self.name = name
        self.child_type = child_type
        self.age = age
        self.ppid = ppid
        self.timeout = timeout


        self.pid = None
        self.child_age = 0
        self.booted = False
        self.stopping = False
        self.debug =self.conf.get("debug", False)
        self.tmp = WorkerTmp(self.conf) 

    def update_proc_title(self):
        util._setproctitle("arbiter [%s running %s workers]" % (self.name,  
            self.num_workers))

    def on_init(self, conf):
        return None

    def on_init_process(self):
        self.update_proc_title()
        
    def handle_ttin(self):
        """\
        SIGTTIN handling.
        Increases the number of workers by one.
        """
        self.num_workers += 1
        self.update_proc_title()
        self.manage_workers()
    
    def handle_ttou(self):
        """\
        SIGTTOU handling.
        Decreases the number of workers by one.
        """
        if self.num_workers <= 1:
            return
        self.num_workers -= 1
        self.update_proc_title()
        self.manage_workers()

    def reload(self):
        """ 
        used on HUP
        """

        # exec on reload hook
        self.on_reload()

        # spawn new workers with new app & conf
        for i in range(self.conf.get("num_workers", 1)):
            self.spawn_child(self._SPEC)
            
        # set new proc_name
        util._setproctitle("master [%s]" % self.name)
        
        # manage workers
        self.manage_workers() 

    def reap_workers(self):
        """\
        Reap workers to avoid zombie processes
        """
        try:
            while True:
                wpid, status = os.waitpid(-1, os.WNOHANG)
                if not wpid:
                    break
                
                # A worker said it cannot boot. We'll shutdown
                # to avoid infinite start/stop cycles.
                exitcode = status >> 8
                if exitcode == self._WORKER_BOOT_ERROR:
                    reason = "Worker failed to boot."
                    raise HaltServer(reason, self._WORKER_BOOT_ERROR)
                child_info = self._WORKERS.pop(wpid, None)

                if not child_info:
                    continue

                child, state = child_info
                child.tmp.close()
        except OSError, e:
            if e.errno == errno.ECHILD:
                pass

    def manage_workers(self):
        """\
        Maintain the number of workers by spawning or killing
        as required.
        """
        if len(self._WORKERS.keys()) < self.num_workers:
            self.spawn_workers()

        workers = self._WORKERS.items()
        workers.sort(key=lambda w: w[1][0].age)
        while len(workers) > self.num_workers:
            (pid, _) = workers.pop(0)
            self.kill_worker(pid, signal.SIGQUIT)

    def spawn_workers(self):
        """\
        Spawn new workers as needed.
        
        This is where a worker process leaves the main loop
        of the master process.
        """
        for i in range(self.num_workers - len(self._WORKERS.keys())):
            self.spawn_child(self._SPEC)
            
    
    def kill_worker(self, pid, sig):
        """\
               Kill a worker

        :attr pid: int, worker pid
        :attr sig: `signal.SIG*` value
         """
        if not isinstance(pid, int):
            return

        try:
            os.kill(pid, sig)
        except OSError, e:
            if e.errno == errno.ESRCH:
                try:
                    (child, info) = self._WORKERS.pop(pid)
                    child.tmp.close()
                    return
                except (KeyError, OSError):
                    return
            raise  

########NEW FILE########
__FILENAME__ = arbiter
# -*- coding: utf-8 -
#
# This file is part of pistil released under the MIT license. 
# See the NOTICE for more information.

import logging
import os

from pistil import util
from pistil.pool import PoolArbiter
from pistil.tcp.sock import create_socket

log = logging.getLogger(__name__)


class TcpArbiter(PoolArbiter):

    _LISTENER = None

    def on_init(self, args):
        self.address = util.parse_address(args.get('address',
            ('127.0.0.1', 8000)))
        if not self._LISTENER:
            self._LISTENER = create_socket(args)

        # we want to pass the socket to the worker.
        self.conf.update({"sock": self._LISTENER})
        

    def when_ready(self):
        log.info("Listening at: %s (%s)", self._LISTENER,
            self.pid)
   
    def on_reexec(self):
        # save the socket file descriptor number in environ to reuse the
        # socket after forking a new master.
        os.environ['PISTIL_FD'] = str(self._LISTENER.fileno())

    def on_stop(self, graceful=True):
        self._LISTENER = None




########NEW FILE########
__FILENAME__ = gevent_worker
# -*- coding: utf-8 -
#
# This file is part of pistil released under the MIT license. 
# See the NOTICE for more information.

from __future__ import with_statement

import os
import sys
import logging
log = logging.getLogger(__name__)

try:
    import gevent
except ImportError:
    raise RuntimeError("You need gevent installed to use this worker.")


from gevent.pool import Pool
from gevent.server import StreamServer

from pistil import util
from pistil.tcp.sync_worker import TcpSyncWorker 

# workaround on osx, disable kqueue
if sys.platform == "darwin":
    os.environ['EVENT_NOKQUEUE'] = "1"


class PStreamServer(StreamServer):
    def __init__(self, listener, handle, spawn='default', worker=None):
        StreamServer.__init__(self, listener, spawn=spawn)
        self.handle_func = handle
        self.worker = worker

    def stop(self, timeout=None):
        super(PStreamServer, self).stop(timeout=timeout)

    def handle(self, sock, addr):
        self.handle_func(sock, addr)


class TcpGeventWorker(TcpSyncWorker):

    def on_init(self, conf):
        self.worker_connections = conf.get("worker_connections", 
                10000)
        self.pool = Pool(self.worker_connections)

    def run(self):
        self.socket.setblocking(1)
        
        # start gevent stream server
        server = PStreamServer(self.socket, self.handle, spawn=self.pool,
                worker=self)
        server.start()

        try:
            while self.alive:
                self.notify()
                if self.ppid != os.getppid():
                    log.info("Parent changed, shutting down: %s", self)
                    break
        
                gevent.sleep(1.0)
                
        except KeyboardInterrupt:
            pass

        try:
            # Try to stop connections until timeout
            self.notify()
            server.stop(timeout=self.timeout)
        except:
            pass


    if hasattr(gevent.core, 'dns_shutdown'):

        def init_process(self):
            #gevent 0.13 and older doesn't reinitialize dns for us after forking
            #here's the workaround
            gevent.core.dns_shutdown(fail_requests=1)
            gevent.core.dns_init()
            super(TcpGeventWorker, self).init_process()


########NEW FILE########
__FILENAME__ = sock
# -*- coding: utf-8 -
#
# This file is part of gunicorn released under the MIT license. 
# See the NOTICE for more information.

import errno
import logging
import os
import socket
import sys
import time

from pistil import util

log = logging.getLogger(__name__)

class BaseSocket(object):
    
    def __init__(self, conf, fd=None):
        self.conf = conf
        self.address = util.parse_address(conf.get('address',
            ('127.0.0.1', 8000)))
        if fd is None:
            sock = socket.socket(self.FAMILY, socket.SOCK_STREAM)
        else:
            sock = socket.fromfd(fd, self.FAMILY, socket.SOCK_STREAM)
        self.sock = self.set_options(sock, bound=(fd is not None))
    
    def __str__(self, name):
        return "<socket %d>" % self.sock.fileno()
    
    def __getattr__(self, name):
        return getattr(self.sock, name)
    
    def set_options(self, sock, bound=False):
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        if not bound:
            self.bind(sock)
        sock.setblocking(0)
        sock.listen(self.conf.get('backlog', 2048))
        return sock
        
    def bind(self, sock):
        sock.bind(self.address)
        
    def close(self):
        try:
            self.sock.close()
        except socket.error, e:
            log.info("Error while closing socket %s", str(e))
        time.sleep(0.3)
        del self.sock

class TCPSocket(BaseSocket):
    
    FAMILY = socket.AF_INET
    
    def __str__(self):
        return "http://%s:%d" % self.sock.getsockname()
    
    def set_options(self, sock, bound=False):
        sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        return super(TCPSocket, self).set_options(sock, bound=bound)

class TCP6Socket(TCPSocket):

    FAMILY = socket.AF_INET6

    def __str__(self):
        (host, port, fl, sc) = self.sock.getsockname()
        return "http://[%s]:%d" % (host, port)

class UnixSocket(BaseSocket):
    
    FAMILY = socket.AF_UNIX
    
    def __init__(self, conf, fd=None):
        if fd is None:
            try:
                os.remove(conf.address)
            except OSError:
                pass
        super(UnixSocket, self).__init__(conf, fd=fd)
    
    def __str__(self):
        return "unix:%s" % self.address
        
    def bind(self, sock):
        old_umask = os.umask(self.conf.get("umask", 0))
        sock.bind(self.address)
        util.chown(self.address, self.conf.get("uid", os.geteuid()),
                self.conf.get("gid", os.getegid()))
        os.umask(old_umask)
        
    def close(self):
        super(UnixSocket, self).close()
        os.unlink(self.address)

def create_socket(conf):
    """
    Create a new socket for the given address. If the
    address is a tuple, a TCP socket is created. If it
    is a string, a Unix socket is created. Otherwise
    a TypeError is raised.
    """
    # get it only once
    addr = conf.get("address", ('127.0.0.1', 8000))
    
    if isinstance(addr, tuple):
        if util.is_ipv6(addr[0]):
            sock_type = TCP6Socket
        else:
            sock_type = TCPSocket
    elif isinstance(addr, basestring):
        sock_type = UnixSocket
    else:
        raise TypeError("Unable to create socket from: %r" % addr)

    if 'PISTIL_FD' in os.environ:
        fd = int(os.environ.pop('PISTIL_FD'))
        try:
            return sock_type(conf, fd=fd)
        except socket.error, e:
            if e[0] == errno.ENOTCONN:
                log.error("PISTIL_FD should refer to an open socket.")
            else:
                raise

    # If we fail to create a socket from GUNICORN_FD
    # we fall through and try and open the socket
    # normally.
    
    for i in range(5):
        try:
            return sock_type(conf)
        except socket.error, e:
            if e[0] == errno.EADDRINUSE:
                log.error("Connection in use: %s", str(addr))
            if e[0] == errno.EADDRNOTAVAIL:
                log.error("Invalid address: %s", str(addr))
                sys.exit(1)
            if i < 5:
                log.error("Retrying in 1 second.")
                time.sleep(1)
          
    log.error("Can't connect to %s", str(addr))
    sys.exit(1)


########NEW FILE########
__FILENAME__ = sync_worker
# -*- coding: utf-8 -
#
# This file is part of pistil released under the MIT license. 
# See the NOTICE for more information.

import errno
import logging
import os
import select
import socket


from pistil import util
from pistil.worker import Worker


log = logging.getLogger(__name__)


class TcpSyncWorker(Worker):

    def on_init_process(self):
        self.socket = self.conf.get('sock')
        self.address = self.socket.getsockname()
        util.close_on_exec(self.socket)
        
    def run(self):
        self.socket.setblocking(0)

        while self.alive:
            self.notify()

            # Accept a connection. If we get an error telling us
            # that no connection is waiting we fall down to the
            # select which is where we'll wait for a bit for new
            # workers to come give us some love.
            try:
                client, addr = self.socket.accept()
                client.setblocking(1)
                util.close_on_exec(client)
                self.handle(client, addr)

                # Keep processing clients until no one is waiting. This
                # prevents the need to select() for every client that we
                # process.
                continue

            except socket.error, e:
                if e[0] not in (errno.EAGAIN, errno.ECONNABORTED):
                    raise

            # If our parent changed then we shut down.
            if self.ppid != os.getppid():
                log.info("Parent changed, shutting down: %s", self)
                return
            
            try:
                self.notify()
                ret = select.select([self.socket], [], self._PIPE,
                        self.timeout / 2.0)
                if ret[0]:
                    continue
            except select.error, e:
                if e[0] == errno.EINTR:
                    continue
                if e[0] == errno.EBADF:
                    if self.nr < 0:
                        continue
                    else:
                        return
                raise

    def handle(self, client, addr):
        raise NotImplementedError

########NEW FILE########
__FILENAME__ = util
# -*- coding: utf-8 -
#
# This file is part of gunicorn released under the MIT license. 
# See the NOTICE for more information.


try:
    import ctypes
except MemoryError:
    # selinux execmem denial
    # https://bugzilla.redhat.com/show_bug.cgi?id=488396
    ctypes = None
except ImportError:
    # Python on Solaris compiled with Sun Studio doesn't have ctypes
    ctypes = None

import fcntl
import os
import pkg_resources
import random
import resource
import socket
import sys
import textwrap
import time


MAXFD = 1024
if (hasattr(os, "devnull")):
   REDIRECT_TO = os.devnull
else:
   REDIRECT_TO = "/dev/null"

timeout_default = object()

CHUNK_SIZE = (16 * 1024)

MAX_BODY = 1024 * 132

weekdayname = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
monthname = [None,
             'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
             'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

# Server and Date aren't technically hop-by-hop
# headers, but they are in the purview of the
# origin server which the WSGI spec says we should
# act like. So we drop them and add our own.
#
# In the future, concatenation server header values
# might be better, but nothing else does it and
# dropping them is easier.
hop_headers = set("""
    connection keep-alive proxy-authenticate proxy-authorization
    te trailers transfer-encoding upgrade
    server date
    """.split())
            
try:
    from setproctitle import setproctitle
    def _setproctitle(title):
        setproctitle(title) 
except ImportError:
    def _setproctitle(title):
        return

def load_worker_class(uri):
    if uri.startswith("egg:"):
        # uses entry points
        entry_str = uri.split("egg:")[1]
        try:
            dist, name = entry_str.rsplit("#",1)
        except ValueError:
            dist = entry_str
            name = "sync"

        return pkg_resources.load_entry_point(dist, "gunicorn.workers", name)
    else:
        components = uri.split('.')
        if len(components) == 1:
            try:
                if uri.startswith("#"):
                    uri = uri[1:]
                return pkg_resources.load_entry_point("gunicorn", 
                            "gunicorn.workers", uri)
            except ImportError: 
                raise RuntimeError("arbiter uri invalid or not found")
        klass = components.pop(-1)
        mod = __import__('.'.join(components))
        for comp in components[1:]:
            mod = getattr(mod, comp)
        return getattr(mod, klass)

def set_owner_process(uid,gid):
    """ set user and group of workers processes """
    if gid:
        try:
            os.setgid(gid)
        except OverflowError:
            if not ctypes:
                raise
            # versions of python < 2.6.2 don't manage unsigned int for
            # groups like on osx or fedora
            os.setgid(-ctypes.c_int(-gid).value)
            
    if uid:
        os.setuid(uid)
        
def chown(path, uid, gid):
    try:
        os.chown(path, uid, gid)
    except OverflowError:
        if not ctypes:
            raise
        os.chown(path, uid, -ctypes.c_int(-gid).value)


def is_ipv6(addr):
    try:
        socket.inet_pton(socket.AF_INET6, addr)
    except socket.error: # not a valid address
        return False
    return True
        
def parse_address(netloc, default_port=8000):
    if isinstance(netloc, tuple):
        return netloc

    if netloc.startswith("unix:"):
        return netloc.split("unix:")[1]

    # get host
    if '[' in netloc and ']' in netloc:
        host = netloc.split(']')[0][1:].lower()
    elif ':' in netloc:
        host = netloc.split(':')[0].lower()
    elif netloc == "":
        host = "0.0.0.0"
    else:
        host = netloc.lower()
    
    #get port
    netloc = netloc.split(']')[-1]
    if ":" in netloc:
        port = netloc.split(':', 1)[1]
        if not port.isdigit():
            raise RuntimeError("%r is not a valid port number." % port)
        port = int(port)
    else:
        port = default_port 
    return (host, port)
    
def get_maxfd():
    maxfd = resource.getrlimit(resource.RLIMIT_NOFILE)[1]
    if (maxfd == resource.RLIM_INFINITY):
        maxfd = MAXFD
    return maxfd

def close_on_exec(fd):
    flags = fcntl.fcntl(fd, fcntl.F_GETFD)
    flags |= fcntl.FD_CLOEXEC
    fcntl.fcntl(fd, fcntl.F_SETFD, flags)
    
def set_non_blocking(fd):
    flags = fcntl.fcntl(fd, fcntl.F_GETFL) | os.O_NONBLOCK
    fcntl.fcntl(fd, fcntl.F_SETFL, flags)

def close(sock):
    try:
        sock.close()
    except socket.error:
        pass

def write_chunk(sock, data):
    chunk = "".join(("%X\r\n" % len(data), data, "\r\n"))
    sock.sendall(chunk)
    
def write(sock, data, chunked=False):
    if chunked:
        return write_chunk(sock, data)
    sock.sendall(data)

def write_nonblock(sock, data, chunked=False):
    timeout = sock.gettimeout()
    if timeout != 0.0:
        try:
            sock.setblocking(0)
            return write(sock, data, chunked)
        finally:
            sock.setblocking(1)
    else:
        return write(sock, data, chunked)
    
def writelines(sock, lines, chunked=False):
    for line in list(lines):
        write(sock, line, chunked)

def write_error(sock, status_int, reason, mesg):
    html = textwrap.dedent("""\
    <html>
      <head>
        <title>%(reason)s</title>
      </head>
      <body>
        <h1>%(reason)s</h1>
        %(mesg)s
      </body>
    </html>
    """) % {"reason": reason, "mesg": mesg}

    http = textwrap.dedent("""\
    HTTP/1.1 %s %s\r
    Connection: close\r
    Content-Type: text/html\r
    Content-Length: %d\r
    \r
    %s
    """) % (str(status_int), reason, len(html), html)
    write_nonblock(sock, http)

def normalize_name(name):
    return  "-".join([w.lower().capitalize() for w in name.split("-")])
    
def import_app(module):
    parts = module.split(":", 1)
    if len(parts) == 1:
        module, obj = module, "application"
    else:
        module, obj = parts[0], parts[1]

    try:
        __import__(module)
    except ImportError:
        if module.endswith(".py") and os.path.exists(module):
            raise ImportError("Failed to find application, did "
                "you mean '%s:%s'?" % (module.rsplit(".",1)[0], obj))
        else:
            raise

    mod = sys.modules[module]
    app = eval(obj, mod.__dict__)
    if app is None:
        raise ImportError("Failed to find application object: %r" % obj)
    if not callable(app):
        raise TypeError("Application object must be callable.")
    return app

def http_date(timestamp=None):
    """Return the current date and time formatted for a message header."""
    if timestamp is None:
        timestamp = time.time()
    year, month, day, hh, mm, ss, wd, y, z = time.gmtime(timestamp)
    s = "%s, %02d %3s %4d %02d:%02d:%02d GMT" % (
            weekdayname[wd],
            day, monthname[month], year,
            hh, mm, ss)
    return s
    
def to_bytestring(s):
    """ convert to bytestring an unicode """
    if not isinstance(s, basestring):
        return s
    if isinstance(s, unicode):
        return s.encode('utf-8')
    else:
        return s

def is_hoppish(header):
    return header.lower().strip() in hop_headers

def daemonize():
    """\
    Standard daemonization of a process.
    http://www.svbug.com/documentation/comp.unix.programmer-FAQ/faq_2.html#SEC16
    """
    if not 'GUNICORN_FD' in os.environ:
        if os.fork():
            os._exit(0)
        os.setsid()

        if os.fork():
            os._exit(0)
        
        os.umask(0)
        maxfd = get_maxfd()

        # Iterate through and close all file descriptors.
        for fd in range(0, maxfd):
            try:
                os.close(fd)
            except OSError:	# ERROR, fd wasn't open to begin with (ignored)
                pass
        
        os.open(REDIRECT_TO, os.O_RDWR)
        os.dup2(0, 1)
        os.dup2(0, 2)

def seed():
    try:
        random.seed(os.urandom(64))
    except NotImplementedError:
        random.seed(random.random())


class _Missing(object):

    def __repr__(self):
        return 'no value'

    def __reduce__(self):
        return '_missing'

_missing = _Missing()

class cached_property(object):
    
    def __init__(self, func, name=None, doc=None):
        self.__name__ = name or func.__name__
        self.__module__ = func.__module__
        self.__doc__ = doc or func.__doc__
        self.func = func

    def __get__(self, obj, type=None):
        if obj is None:
            return self
        value = obj.__dict__.get(self.__name__, _missing)
        if value is _missing:
            value = self.func(obj)
            obj.__dict__[self.__name__] = value
        return value

########NEW FILE########
__FILENAME__ = worker
# -*- coding: utf-8 -
#
# This file is part of pistil released under the MIT license. 
# See the NOTICE for more information.

from __future__ import with_statement

import logging
import os
import signal
import sys
import time
import traceback


from pistil import util
from pistil.workertmp import WorkerTmp

log = logging.getLogger(__name__)

class Worker(object):
    
    _SIGNALS = map(
        lambda x: getattr(signal, "SIG%s" % x),
        "HUP QUIT INT TERM USR1 USR2 WINCH CHLD".split()
    )
    
    _PIPE = []


    def __init__(self, conf, name=None, child_type="worker", 
            age=0, ppid=0, timeout=30):

        if name is None:
            name =  self.__class__.__name__
        self.name = name

        self.child_type = child_type
        self.age = age
        self.ppid = ppid
        self.timeout = timeout
        self.conf = conf


        # initialize
        self.booted = False
        self.alive = True
        self.debug =self.conf.get("debug", False)
        self.tmp = WorkerTmp(self.conf)

        self.on_init(self.conf)

    def on_init(self, conf):
        pass


    def pid(self):
        return os.getpid()
    pid = util.cached_property(pid)

    def notify(self):
        """\
        Your worker subclass must arrange to have this method called
        once every ``self.timeout`` seconds. If you fail in accomplishing
        this task, the master process will murder your workers.
        """
        self.tmp.notify()

    
    def handle(self):
        raise NotImplementedError

    def run(self):
        """\
        This is the mainloop of a worker process. You should override
        this method in a subclass to provide the intended behaviour
        for your particular evil schemes.
        """
        while True:
            self.notify()
            self.handle()
            time.sleep(0.1)

    def on_init_process(self):
        """ method executed when we init a process """
        pass

    def init_process(self):
        """\
        If you override this method in a subclass, the last statement
        in the function should be to call this method with
        super(MyWorkerClass, self).init_process() so that the ``run()``
        loop is initiated.
        """
        util.set_owner_process(self.conf.get("uid", os.geteuid()),
                self.conf.get("gid", os.getegid()))

        # Reseed the random number generator
        util.seed()

        # For waking ourselves up
        self._PIPE = os.pipe()
        map(util.set_non_blocking, self._PIPE)
        map(util.close_on_exec, self._PIPE)
        
        # Prevent fd inherientence
        util.close_on_exec(self.tmp.fileno())
        self.init_signals()
        
        self.on_init_process()

        # Enter main run loop
        self.booted = True
        self.run()

    def init_signals(self):
        map(lambda s: signal.signal(s, signal.SIG_DFL), self._SIGNALS)
        signal.signal(signal.SIGQUIT, self.handle_quit)
        signal.signal(signal.SIGTERM, self.handle_exit)
        signal.signal(signal.SIGINT, self.handle_exit)
        signal.signal(signal.SIGWINCH, self.handle_winch)
            
    def handle_quit(self, sig, frame):
        self.alive = False

    def handle_exit(self, sig, frame):
        self.alive = False
        sys.exit(0)
        
    def handle_winch(self, sig, fname):
        # Ignore SIGWINCH in worker. Fixes a crash on OpenBSD.
        return

########NEW FILE########
__FILENAME__ = workertmp
# -*- coding: utf-8 -
#
# This file is part of pistil released under the MIT license. 
# See the NOTICE for more information.

import os
import tempfile

from pistil import util

class WorkerTmp(object):

    def __init__(self, cfg):
        old_umask = os.umask(cfg.get("umask", 0))
        fd, name = tempfile.mkstemp(prefix="wgunicorn-")
        
        # allows the process to write to the file
        util.chown(name, cfg.get("uid", os.geteuid()), cfg.get("gid",
            os.getegid()))
        os.umask(old_umask)

        # unlink the file so we don't leak tempory files
        try:
            os.unlink(name)
            self._tmp = os.fdopen(fd, 'w+b', 1)
        except:
            os.close(fd)
            raise

        self.spinner = 0

    def notify(self): 
        try:
            self.spinner = (self.spinner+1) % 2
            os.fchmod(self._tmp.fileno(), self.spinner)
        except AttributeError:
            # python < 2.6
            self._tmp.truncate(0)
            os.write(self._tmp.fileno(), "X")

    def fileno(self):
        return self._tmp.fileno()
       
    def close(self):
        return self._tmp.close()

########NEW FILE########
